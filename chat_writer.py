import argparse
import asyncio

from environs import Env


async def send_message(host: str, port: int, chat_token: str, message_text: str) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    answer = await reader.read(512)
    if 'Enter your personal hash' in answer.decode(errors='ignore'):
        writer.write(f'{chat_token}\n'.encode())
        await writer.drain()
    writer.write(f'{message_text}\n\n'.encode())
    await writer.drain()
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
    args = parser.parse_args()
    asyncio.run(send_message(
        host=args.host,
        port=args.port,
        message_text=args.message,
        chat_token=env('CHAT_TOKEN')
    ))


if __name__ == '__main__':
    main()
