import asyncio

from _socket import gaierror

from anyio import ExceptionGroup


class InvalidToken(Exception):
    pass


def retry_on_network_error(func):
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await func(*args, **kwargs)
            except (ConnectionError, gaierror, ExceptionGroup):
                await asyncio.sleep(5)
                continue

    return wrapper
