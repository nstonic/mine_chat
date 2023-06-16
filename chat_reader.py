import argparse
import asyncio
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
        async with aiofiles.open(to_file, mode='a', errors='ignore', encoding='utf8') as file:
            await file.write(f'[{receiving_time}] {message_text}')


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
    args = parser.parse_args()
    asyncio.run(listen_chat(
        host=args.host,
        port=args.port,
        to_file=args.to_file,
    ))


if __name__ == '__main__':
    main()
