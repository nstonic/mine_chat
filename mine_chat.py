import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime
from enum import Enum
from tkinter import messagebox
from typing import NoReturn

import aiofiles

queue_logger = logging.getLogger('Queue_logger')


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
        self.watchdog_queue = asyncio.Queue()

        self._listener = None
        self._reader = None
        self._writer = None

    async def run(self) -> NoReturn:
        await asyncio.gather(
            self.watch_for_connection(),
            self.listen_chat(),
            self.sending_msgs(),
            self.save_msgs()
        )

    @property
    def history_file(self):
        return self._history_file

    async def authorise(self) -> None:
        self._writer.write(f'{self._token}\n'.encode(errors='ignore'))
        await self._writer.drain()
        queue_logger.debug('Connection is alive. Source: Sending authorization token')

    def check_auth(self, response_text: str) -> None:
        json_raw, *_ = response_text.split('\n')
        with suppress(json.decoder.JSONDecodeError):
            response_obj = json.loads(json_raw)
            if response_obj is None:
                queue_logger.debug('Connection is alive. Source: Invalid token')
                raise InvalidToken
            elif nickname := response_obj.get('nickname'):
                queue_logger.debug('Connection is alive. Source: Authorization done')
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
                await self.read_msgs()
            finally:
                writer.close()
                await writer.wait_closed()

    async def read_msgs(self) -> None:
        while True:
            message = await self._listener.read(512)
            self.status_updates_queue.put_nowait(
                ReadConnectionStateChanged.ESTABLISHED
            )
            if message_text := message.decode(errors='ignore').strip():
                receiving_time = datetime.now().strftime('%d.%m.%y %H:%M:%S')
                message_line = f'[{receiving_time}] {message_text}'
                self.messages_queue.put_nowait(message_line)
                self.saving_history_queue.put_nowait(message_line)
                queue_logger.debug('Connection is alive. Source: Message received')

    async def save_msgs(self) -> NoReturn:
        while True:
            messages_line = await self.saving_history_queue.get()
            async with aiofiles.open(self._history_file, mode='a', errors='ignore', encoding='utf8') as file:
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
            finally:
                self._writer.close()
                await self._writer.wait_closed()

    async def submit_msgs(self) -> NoReturn:
        while True:
            message = await self.sending_queue.get()
            message = message.replace('\n', ' ')
            self._writer.write(f'{message}\n\n'.encode(errors='ignore'))
            await self._writer.drain()
            queue_logger.debug('Connection is alive. Source: Message sent')

    async def watch_for_connection(self):
        while True:
            try:
                async with asyncio.timeout(2):
                    log = await self.watchdog_queue.get()
                    print(log)
            except TimeoutError:
                queue_logger.debug('Timeout error')
                log = await self.watchdog_queue.get()
                print(log)


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


class QueueLoggerHandler(logging.Handler):

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue
        self.formatter = logging.Formatter(fmt='[%(asctime)s] %(message)s')

    def emit(self, record):
        self.queue.put_nowait(
            self.format(record)
        )
