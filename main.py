import asyncio
from datetime import datetime

import aiofiles as aiofiles


async def listen_chat():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)

    while True:
        message = await reader.read(100)
        async with aiofiles.open('minechat.txt', mode='a', errors='ignore') as file:
            receiving_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            await file.write(f'[{receiving_time}] {message.decode(errors="ignore")}')


if __name__ == '__main__':
    asyncio.run(listen_chat())
