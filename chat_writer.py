import argparse
import asyncio
import logging
from datetime import datetime

from environs import Env


async def send_message(host: str, port: int, chat_token: str, message_text: str) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    answer = await reader.read(512)
    if 'Enter your personal hash' in answer.decode(errors='ignore'):
        writer.write(f'{chat_token}\n'.encode())
        await writer.drain()
    writer.write(f'{message_text}\n\n'.encode())
    await writer.drain()
    sending_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    logging.debug(f'[{sending_time}] {message_text}')
    writer.close()
    await writer.wait_closed()
    return


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
        '--message',
        help='Message for sending'
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
            message_text=args.message,
            chat_token=env('CHAT_TOKEN')
        ))


if __name__ == '__main__':
    main()
