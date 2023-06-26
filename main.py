import argparse
import asyncio
from asyncio import StreamWriter
from datetime import datetime
from typing import NoReturn

import aiofiles
from environs import Env

import gui


async def save_messages(saving_history_queue: asyncio.Queue, filepath: str):
    while True:
        messages_line = await saving_history_queue.get()
        async with aiofiles.open(filepath, mode='a', errors='ignore', encoding='utf8') as file:
            await file.write(messages_line + '\n')


async def read_msgs(
        messages_queue: asyncio.Queue,
        saving_history_queue: asyncio.Queue,
        host: str,
        port: int
) -> NoReturn:
    reader, writer = await asyncio.open_connection(host, port)
    while True:
        message = await reader.read(512)
        if message_text := message.decode(errors='ignore').strip():
            receiving_time = datetime.now().strftime('%d.%m.%Y %H:%M')
            message_line = f'[{receiving_time}] {message_text}'
            messages_queue.put_nowait(message_line)
            saving_history_queue.put_nowait(message_line)


async def submit_messages(writer: StreamWriter, sending_queue: asyncio.Queue) -> None:
    while True:
        message = await sending_queue.get()
        message = message.replace('\n', ' ')
        writer.write(f'{message}\n\n'.encode(errors='ignore'))
        await writer.drain()
        # sending_time = datetime.now().strftime('%d.%m.%Y %H:%M')
        # logging.debug(f'Sending message [{sending_time}] {message}')


async def authorise(writer: StreamWriter, token: str, ) -> None:
    writer.write(f'{token}\n'.encode(errors='ignore'))
    await writer.drain()


async def handle_sending_msg(
        host: str,
        sending_port: str,
        token: str,
        sending_queue: asyncio.Queue
) -> NoReturn:
    reader, writer = await asyncio.open_connection(host, sending_port)
    try:
        while True:
            response = await reader.read(512)
            response_text = response.decode(errors='ignore')
            if 'Enter your personal hash' in response_text:
                await authorise(writer, token)
            elif 'Post your message below' in response_text:
                await submit_messages(writer, sending_queue)
            else:
                print(response_text)
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    args = get_args()
    # logging.basicConfig(
    #     level=logging.DEBUG,
    #     filename=args.log_filename
    # )
    # logging.disable(args.log_off)

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    saving_history_queue = asyncio.Queue()

    await asyncio.gather(
        save_messages(saving_history_queue, args.history_file),
        read_msgs(messages_queue, saving_history_queue, args.host, args.reading_port),
        gui.draw(messages_queue, sending_queue, status_updates_queue, args.history_file),
        handle_sending_msg(args.host, args.sending_port, args.token, sending_queue)
    )


def get_args():
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--host',
        default=env('HOST', 'minechat.dvmn.org'),
        help='Host address'
    )
    parser.add_argument(
        '--reading_port',
        type=int,
        default=env.int('READING_PORT', 5000),
        help='Port for reading chat'
    )
    parser.add_argument(
        '--sending_port',
        type=int,
        default=env.int('SENDING_PORT', 5050),
        help='Port for sending messages'
    )
    parser.add_argument(
        '--token',
        default=env('TOKEN', None),
        help='Host port'
    )
    parser.add_argument(
        '--history_file',
        default=env('HISTORY_FILE', 'history.txt'),
        help='File path for saving chat history'
    )
    # parser.add_argument(
    #     '--log_off',
    #     action='store_false',
    #     help='Disable logging'
    # )
    # parser.add_argument(
    #     '--log_filename',
    #     default=env('LOG_FILENAME', default='chat.log'),
    #     help='Set log file name'
    # )
    args = parser.parse_args()
    # args.log_off = args.log_off or env.bool('LOG_OFF', default=False)
    return args


if __name__ == '__main__':
    asyncio.run(main())
