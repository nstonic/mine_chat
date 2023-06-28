import asyncio
import json
from asyncio import StreamReader, StreamWriter
from contextlib import suppress
from datetime import datetime
from enum import Enum
from json import JSONDecodeError
from typing import NoReturn, Optional

import aiofiles
from anyio import create_task_group

from errors import InvalidToken, retry_on_network_error


class MineChat:

    def __init__(
            self,
            host: str,
            reading_port: int,
            sending_port: int,
            token: str,
            history_file: str,
    ):
        self._history_file = history_file
        self._host = host
        self._listening_port = reading_port
        self._sending_port = sending_port
        self._token = token

        self.messages_queue = asyncio.Queue()
        self.saving_history_queue = asyncio.Queue()
        self.sending_queue = asyncio.Queue()
        self.status_updates_queue = asyncio.Queue()
        self.nickname_queue = asyncio.Queue()
        self.show_token_queue = asyncio.Queue()
        self.watchdog_queue = asyncio.Queue()

        self._listener: Optional[StreamReader] = None
        self._reader: Optional[StreamReader] = None
        self._sender: Optional[StreamWriter] = None

    async def run(self) -> NoReturn:
        async with create_task_group() as tg:
            tg.start_soon(self.handle_connection)

    async def register_new_user(self):
        self._token = ''
        await self.log_on()

    @property
    def history_file(self):
        return self._history_file

    async def send_nickname(self) -> None:
        nickname = await self.nickname_queue.get()
        self._sender.write(f'{nickname}\n'.encode(errors='ignore'))
        await self._sender.drain()

    async def authorise(self) -> None:
        self._sender.write(f'{self._token}\n'.encode(errors='ignore'))
        await self._sender.drain()
        self.watchdog_queue.put_nowait(True)

    def check_auth(self, response_text: str) -> Optional[bool]:
        with suppress(JSONDecodeError):
            response_obj = json.loads(response_text)
            if response_obj is None:
                self.watchdog_queue.put_nowait(True)
                raise InvalidToken('Неверный токен')
            elif nickname := response_obj.get('nickname'):
                if not self._token:
                    self._token = response_obj.get('account_hash')
                    self.show_token_queue.put_nowait(self._token)
                self.watchdog_queue.put_nowait(True)
                self.status_updates_queue.put_nowait(
                    NicknameReceived(nickname)
                )
                return True

    @retry_on_network_error
    async def handle_connection(self):
        self.status_updates_queue.put_nowait(
            ReadConnectionStateChanged.INITIATED
        )
        self.status_updates_queue.put_nowait(
            SendingConnectionStateChanged.INITIATED
        )
        self._listener, _ = await asyncio.open_connection(self._host, self._listening_port)
        self._reader, self._sender = await asyncio.open_connection(self._host, self._sending_port)

        if await self.log_on():
            self.status_updates_queue.put_nowait(
                SendingConnectionStateChanged.ESTABLISHED
            )
            async with create_task_group() as tg:
                tg.start_soon(self.listen_chat)
                tg.start_soon(self.save_msgs)
                tg.start_soon(self.send_msgs)
                tg.start_soon(self.ping_pong)
                tg.start_soon(self.watch_for_connection)

    async def listen_chat(self) -> NoReturn:
        while True:
            message = await self._listener.read(512)
            if message:
                self.watchdog_queue.put_nowait(True)
                self.status_updates_queue.put_nowait(
                    ReadConnectionStateChanged.ESTABLISHED
                )
            else:
                break
            if message_text := message.decode(errors='ignore').strip():
                receiving_time = datetime.now().strftime('%d.%m.%y %H:%M:%S')
                message_line = f'[{receiving_time}] {message_text}'
                self.messages_queue.put_nowait(message_line)
                self.saving_history_queue.put_nowait(message_line)

    async def log_on(self) -> bool:
        if self._token is None:
            raise InvalidToken('Отсутствует токен')
        waiting_for_auth_result = False
        while True:
            response = await self._reader.readline()
            response_text = response.decode(errors='ignore')
            self.status_updates_queue.put_nowait(
                SendingConnectionStateChanged.ESTABLISHED
            )
            if waiting_for_auth_result:
                if self.check_auth(response_text):
                    waiting_for_auth_result = False
            if 'Enter your personal hash' in response_text:
                await self.authorise()
                waiting_for_auth_result = True
            if 'Enter preferred nickname below' in response_text:
                await self.send_nickname()
                waiting_for_auth_result = True
            if 'Post your message below' in response_text:
                return True

    async def ping_pong(self) -> NoReturn:
        while True:
            self.sending_queue.put_nowait('')
            await self._reader.readline()
            self.watchdog_queue.put_nowait(True)
            await asyncio.sleep(2)

    async def save_msgs(self) -> NoReturn:
        while True:
            messages_line = await self.saving_history_queue.get()
            async with aiofiles.open(self._history_file, mode='a', errors='ignore', encoding='utf8') as file:
                await file.write(messages_line + '\n')

    async def send_msgs(self) -> NoReturn:
        while True:
            message = await self.sending_queue.get()
            message = message.replace('\n', ' ')
            self._sender.write(f'{message}\n\n'.encode(errors='ignore'))
            await self._sender.drain()
            self.watchdog_queue.put_nowait(True)

    async def watch_for_connection(self):
        while True:
            try:
                async with asyncio.timeout(3):
                    await self.watchdog_queue.get()
            except TimeoutError:
                self.status_updates_queue.put_nowait(
                    SendingConnectionStateChanged.CLOSED
                )
                self.status_updates_queue.put_nowait(
                    ReadConnectionStateChanged.CLOSED
                )
                raise ConnectionError


class ReadConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname
