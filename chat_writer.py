import argparse
import asyncio
import json
import logging
from asyncio import StreamWriter
from datetime import datetime
from functools import partial
from typing import NoReturn, Callable, Optional

from environs import Env


async def submit_message(writer: StreamWriter, message: str) -> bool:
    message = message.replace('\n', ' ')
    writer.write(f'{message}\n\n'.encode(errors='ignore'))
    await writer.drain()
    sending_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    logging.debug(f'Sending message [{sending_time}] {message}')
    print('Сообщение отправлено')
    return True


async def register(writer: StreamWriter, nickname: str = None) -> None:
    if nickname:
        print(f'Регистрируемся под ником: {nickname}')
    else:
        nickname = input('Введите никнейм для регистрации:')
    nickname = nickname.replace('\n', ' ')
    writer.write(f'{nickname}\n'.encode(errors='ignore'))
    await writer.drain()


async def authorise(writer: StreamWriter, chat_token: str, ) -> None:
    writer.write(f'{chat_token}\n'.encode(errors='ignore'))
    await writer.drain()


def print_report(response: str) -> None:
    try:
        response_obj = json.loads(response)
    except json.decoder.JSONDecodeError:
        return
    else:
        if response_obj is None:
            print('Неизвестный токен.')
        elif token := response_obj.get('account_hash'):
            print(f'Ваш токен: {token}\nСохраните его в файле .env')


def get_action_func(
        response: str,
        message: str,
        chat_token: str,
        nickname: str
) -> Optional[Callable]:
    if 'Enter preferred nickname below' in response:
        return partial(register, nickname=nickname)
    if 'Enter your personal hash' in response:
        return partial(authorise, chat_token=chat_token)
    if 'Post your message below' in response:
        return partial(submit_message, message=message)


async def send_message(
        host: str,
        port: int,
        chat_token: str,
        message: str,
        nickname: str
) -> NoReturn:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        while True:
            response = await reader.read(512)
            response = response.decode(errors='ignore')
            action = get_action_func(
                response,
                message,
                chat_token,
                nickname
            )
            if action:
                message_sent = await action(writer=writer)
                if message_sent:
                    break
            else:
                print_report(response)
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
