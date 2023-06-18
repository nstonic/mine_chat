import argparse
import asyncio
import logging
from datetime import datetime
from typing import NoReturn

import aiofiles as aiofiles
from environs import Env


async def listen_chat(host: str, port: int, to_file: str) -> NoReturn:
    reader, writer = await asyncio.open_connection(host, port)

    while True:
        message = await reader.read(512)
        receiving_time = datetime.now().strftime('%d.%m.%Y %H:%M')
        message_text = message.decode(errors='ignore')
        message_line = f'[{receiving_time}] {message_text}'
        print(message_line, end='')
        async with aiofiles.open(to_file, mode='a', errors='ignore', encoding='utf8') as file:
            logging.debug(message_line)
            await file.write(message_line)


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
        default=env.int('PORT', 5000),
        help='Host port'
    )
    parser.add_argument(
        '--to_file',
        default=env('TO_FILE', 'minechat.txt'),
        help='File name to save chat history'
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
    asyncio.run(listen_chat(
        host=args.host,
        port=args.port,
        to_file=args.to_file,
    ))


if __name__ == '__main__':
    main()
