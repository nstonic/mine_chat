import asyncio

from _socket import gaierror


class InvalidToken(Exception):
    def __str__(self):
        return 'Проверьте токен. сервер его не узнал'


def retry_on_network_error(func):
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await func(*args, **kwargs)
            except (ConnectionError, gaierror):
                await asyncio.sleep(5)
                continue
    return wrapper
