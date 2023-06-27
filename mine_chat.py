import asyncio
import json
from contextlib import suppress
from datetime import datetime
from enum import Enum
from tkinter import messagebox
from typing import NoReturn

import aiofiles


class MineChat:

    def __init__(
            self,
            host: str,
            reading_port: int,
            sending_port: int,
            token: str,
            history_file: str,
    ):
        self.history_file = history_file
        self._host = host
        self._listening_port = reading_port
        self._sending_port = sending_port
        self._token = token

        self.messages_queue = asyncio.Queue()
        self.sending_queue = asyncio.Queue()
        self.status_updates_queue = asyncio.Queue()
        self.saving_history_queue = asyncio.Queue()

        self._listener = None
        self._writer = None
        self._reader = None

    async def run(self) -> NoReturn:
        await asyncio.gather(
            self.save_msgs(),
            self.listen_chat(),
            self.sending_msgs()
        )

    async def authorise(self) -> None:
        self._writer.write(f'{self._token}\n'.encode(errors='ignore'))
        await self._writer.drain()

    def check_auth(self, response_text: str) -> None:
        json_raw, *_ = response_text.split('\n')
        with suppress(json.decoder.JSONDecodeError):
            response_obj = json.loads(json_raw)
            if response_obj is None:
                raise InvalidToken
            elif nickname := response_obj.get('nickname'):
                self.status_updates_queue.put_nowait(
                    NicknameReceived(nickname)
                )

    async def handle_server_responses(self) -> NoReturn:
        waiting_for_auth_result = False
        while True:
            response = await self._reader.read(512)
            response_text = response.decode(errors='ignore')
            if not response_text.strip():
                continue
            self.status_updates_queue.put_nowait(
                SendingConnectionStateChanged.ESTABLISHED
            )
            if waiting_for_auth_result:
                self.check_auth(response_text)
                waiting_for_auth_result = False
            if 'Enter your personal hash' in response_text:
                await self.authorise()
                waiting_for_auth_result = True
            if 'Post your message below' in response_text:
                await self.submit_msgs()

    async def listen_chat(self) -> NoReturn:
        while True:
            self.status_updates_queue.put_nowait(
                ReadConnectionStateChanged.INITIATED
            )
            self._listener, writer = await asyncio.open_connection(self._host, self._listening_port)
            try:
                while True:
                    await self.read_msgs()
            except ConnectionError:
                self.status_updates_queue.put_nowait(
                    ReadConnectionStateChanged.CLOSED
                )
                await asyncio.sleep(5)
            finally:
                writer.close()
                await writer.wait_closed()

    async def read_msgs(self) -> None:
        message = await self._listener.read(512)
        self.status_updates_queue.put_nowait(
            ReadConnectionStateChanged.ESTABLISHED
        )
        if message_text := message.decode(errors='ignore').strip():
            receiving_time = datetime.now().strftime('%d.%m.%Y %H:%M')
            message_line = f'[{receiving_time}] {message_text}'
            self.messages_queue.put_nowait(message_line)
            self.saving_history_queue.put_nowait(message_line)

    async def save_msgs(self) -> NoReturn:
        while True:
            messages_line = await self.saving_history_queue.get()
            async with aiofiles.open(self.history_file, mode='a', errors='ignore', encoding='utf8') as file:
                await file.write(messages_line + '\n')

    async def sending_msgs(self) -> NoReturn:
        while True:
            self.status_updates_queue.put_nowait(
                SendingConnectionStateChanged.INITIATED
            )
            self._reader, self._writer = await asyncio.open_connection(self._host, self._sending_port)
            try:
                await self.handle_server_responses()
            except InvalidToken as ex:
                self.status_updates_queue.put_nowait(
                    SendingConnectionStateChanged.CLOSED
                )
                messagebox.showerror('Неверный токен', str(ex))
                break
            except ConnectionError:
                self.status_updates_queue.put_nowait(
                    SendingConnectionStateChanged.CLOSED
                )
                await asyncio.sleep(5)
            finally:
                self._writer.close()
                await self._writer.wait_closed()

    async def submit_msgs(self) -> NoReturn:
        while True:
            message = await self.sending_queue.get()
            message = message.replace('\n', ' ')
            self._writer.write(f'{message}\n\n'.encode(errors='ignore'))
            await self._writer.drain()


class InvalidToken(Exception):
    def __str__(self):
        return 'Проверьте токен. сервер его не узнал'


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
