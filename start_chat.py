import argparse
from _tkinter import TclError

from anyio import run
from anyio._backends._asyncio import ExceptionGroup
from environs import Env

from gui import draw, TkAppClosed
from mine_chat import MineChat


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
    try:
        run(draw, chat)
    except (ExceptionGroup, TclError, KeyboardInterrupt):
        pass
    finally:
        raise TkAppClosed


if __name__ == '__main__':
    main()
