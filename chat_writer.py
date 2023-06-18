import argparse
import asyncio
import json
import logging
from asyncio import StreamWriter, StreamReader
from datetime import datetime
from typing import NoReturn

from aioconsole import ainput
from environs import Env


async def submit_message(writer: StreamWriter) -> NoReturn:
    message = await ainput('Введите сообщение:')
    message = message.replace('\n', ' ')
    writer.write(f'{message}\n\n'.encode(errors='ignore'))
    await writer.drain()
    sending_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    logging.debug(f'Sending message [{sending_time}] {message}')
    print('Сообщение отправлено')


async def register(reader: StreamReader, writer: StreamWriter) -> None:
    nickname = await ainput('Введите никнейм для регистрации:')
    nickname = nickname.replace('\n', ' ')
    writer.write(f'{nickname}\n'.encode(errors='ignore'))
    await writer.drain()
    answer = await reader.read(512)
    token = json.loads(answer.decode(errors='ignore')).get('account_hash')
    print(f'Ваш новый токен: {token}\nСохраните его в файле .env')


async def authorise(reader: StreamReader, writer: StreamWriter, chat_token: str) -> None:
    answer = await reader.read(512)
    if 'Enter your personal hash' in answer.decode(errors='ignore'):
        writer.write(f'{chat_token}\n'.encode(errors='ignore'))
        await writer.drain()
        answer = await reader.read(512)
        if json.loads(answer.decode(errors='ignore')) is None:
            await reader.read(512)
            print('Неизвестный токен.', end='')
            await register(reader, writer)


async def start_chat(host: str, port: int, chat_token: str) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    await authorise(reader, writer, chat_token)
    try:
        while True:
            await submit_message(writer)
    finally:
        writer.close()
        await writer.wait_closed()


def main():
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--host',
        default=env('HOST', 'minechat.dvmn.org'),
        help='Host address'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=env.int('PORT', 5050),
        help='Host port'
    )
    parser.add_argument(
        '--log_off',
        action='store_false',
        help='Disable logging'
    )
    parser.add_argument(
        '--log_filename',
        default=env('LOG_FILENAME', default='server.log'),
        help='Set log file name'
    )
    args = parser.parse_args()

    logging.disable(
        args.log_off or env.bool('LOG_OFF', default=False)
    )

    logging.basicConfig(
        level=logging.DEBUG,
        filename=args.log_filename
    )

    asyncio.run(start_chat(
        host=args.host,
        port=args.port,
        chat_token=env('CHAT_TOKEN')
    ))


if __name__ == '__main__':
    main()
