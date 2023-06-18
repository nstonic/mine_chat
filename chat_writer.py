import argparse
import asyncio
import json
import logging
from asyncio import StreamWriter
from datetime import datetime
from functools import partial
from typing import NoReturn, Callable, Optional

from aioconsole import ainput
from environs import Env


async def submit_message(
        writer: StreamWriter,
        message: str
) -> NoReturn:
    message = message.replace('\n', ' ')
    writer.write(f'{message}\n\n'.encode(errors='ignore'))
    await writer.drain()
    sending_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    logging.debug(f'Sending message [{sending_time}] {message}')
    print('Сообщение отправлено')
    writer.close()
    await writer.wait_closed()
    exit()


async def register(
        writer: StreamWriter,
        nickname: str = None
) -> None:
    if not nickname:
        nickname = await ainput('Введите никнейм для регистрации:')
    nickname = nickname.replace('\n', ' ')
    writer.write(f'{nickname}\n'.encode(errors='ignore'))
    await writer.drain()


async def authorise(
        writer: StreamWriter,
        chat_token: str,
) -> None:
    writer.write(f'{chat_token}\n'.encode(errors='ignore'))
    await writer.drain()


async def print_unknown_token() -> None:
    print('Неизвестный токен.')


async def print_new_token(token: str) -> None:
    print(f'Ваш новый токен: {token}\nСохраните его в файле .env')


def get_action_func(
        answer: str,
        writer: StreamWriter,
        message: str,
        chat_token: str,
        nickname: str
) -> Optional[Callable]:
    if 'Enter preferred nickname below' in answer:
        return partial(register, writer=writer, nickname=nickname)
    if 'Enter your personal hash' in answer:
        return partial(authorise, writer=writer, chat_token=chat_token)
    if 'Post your message below' in answer:
        return partial(submit_message, writer=writer, message=message)

    try:
        answer_obj = json.loads(answer)
    except json.decoder.JSONDecodeError:
        return
    else:
        if answer_obj is None:
            return print_unknown_token
        elif token := answer_obj.get('account_hash'):
            return partial(print_new_token, token=token)


async def send_message(
        host: str,
        port: int,
        chat_token: str,
        message: str,
        nickname: str
) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        while True:
            answer = await reader.read(512)
            if action := get_action_func(
                    answer.decode(errors='ignore'),
                    writer,
                    message,
                    chat_token,
                    nickname
            ):
                await action()
    finally:
        writer.close()
        await writer.wait_closed()


def main():
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'message',
        help='Message for sending'
    )
    parser.add_argument(
        '--nickname',
        default=env('NICKNAME', default=None),
        help='Nickname for registration'
    )
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

    asyncio.run(send_message(
        host=args.host,
        port=args.port,
        chat_token=env('CHAT_TOKEN', default=None),
        message=args.message,
        nickname=args.nickname
    ))


if __name__ == '__main__':
    main()
