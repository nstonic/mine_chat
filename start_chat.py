import argparse
import asyncio
import logging

from environs import Env

import gui
from mine_chat import MineChat, QueueLoggerHandler

queue_logger = logging.getLogger('Queue_logger')


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
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    chat = MineChat(
        host=args.host,
        reading_port=args.reading_port,
        sending_port=args.sending_port,
        token=args.token,
        history_file=args.history_file
    )
    queue_logger.setLevel(
        level=logging.DEBUG
    )
    queue_logger.setLevel(logging.DEBUG)
    queue_logger.addHandler(QueueLoggerHandler(
        queue=chat.watchdog_queue
    ))
    asyncio.run(gui.draw(chat))


if __name__ == '__main__':
    main()
