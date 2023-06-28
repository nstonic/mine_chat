import tkinter as tk
import asyncio
from contextlib import suppress
from functools import partial
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import aiofiles
from anyio import create_task_group

from mine_chat import ReadConnectionStateChanged, SendingConnectionStateChanged, NicknameReceived, MineChat
from errors import InvalidToken


class TkAppClosed(Exception):
    pass


def process_input_text(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def update_conversation_history(panel, messages_queue, history_filepath):
    with suppress(FileNotFoundError):
        async with aiofiles.open(history_filepath, mode='r', errors='ignore', encoding='utf8') as file:
            history = await file.read()
            panel.insert('insert', history.strip())
    while True:
        msg = await messages_queue.get()

        panel['state'] = 'normal'
        if panel.index('end-1c') != '1.0':
            panel.insert('end', '\n')
        panel.insert('end', msg)
        panel.yview(tk.END)
        panel['state'] = 'disabled'


async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, read_label, write_label = status_labels

    read_label['text'] = f'Чтение: нет соединения'
    write_label['text'] = f'Отправка: нет соединения'
    nickname_label['text'] = f'Имя пользователя: неизвестно'

    while True:
        msg = await status_updates_queue.get()
        if isinstance(msg, ReadConnectionStateChanged):
            read_label['text'] = f'Чтение: {msg}'

        if isinstance(msg, SendingConnectionStateChanged):
            write_label['text'] = f'Отправка: {msg}'

        if isinstance(msg, NicknameReceived):
            nickname_label['text'] = f'Имя пользователя: {msg.nickname}'


async def update_label(text_label, input_field, queue):
    while True:
        token = await queue.get()
        text_label['text'] = 'Ваш новый токен.\nСохраните эту строку в файле .env и перезапустите программу'
        input_field.insert(0, f'TOKEN = "{token}"')


def create_status_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side='bottom', fill=tk.X)

    connections_frame = tk.Frame(status_frame)
    connections_frame.pack(side='left')

    nickname_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    nickname_label.pack(side='top', fill=tk.X)

    status_read_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_read_label.pack(side='top', fill=tk.X)

    status_write_label = tk.Label(connections_frame, height=1, fg='grey', font='arial 10', anchor='w')
    status_write_label.pack(side='top', fill=tk.X)

    return nickname_label, status_read_label, status_write_label


def on_closing(window):
    window.destroy()
    raise TkAppClosed


async def draw_register_window(chat: MineChat, title: str):
    register_window = tk.Tk()
    register_window.title(title)
    register_window.geometry('500x100')
    on_closing_func = partial(on_closing, register_window)
    register_window.protocol('WM_DELETE_WINDOW', on_closing_func)

    text_label = ttk.Label(register_window, font='arial 10')
    text_label.pack(expand=True)
    text_label['text'] = 'Похоже вы еще не зарегистрированы в чате.\n' \
                         'Введите никнейм для регистрации нового пользователя'

    nickname_input_frame = tk.Frame(register_window)
    nickname_input_frame.pack(side='bottom', fill=tk.X)
    nickname_input_field = tk.Entry(nickname_input_frame)
    nickname_input_field.pack(side='left', fill=tk.X, expand=True)
    nickname_input_field.bind('<Return>', lambda event: process_input_text(nickname_input_field, chat.nickname_queue))
    send_button = tk.Button(nickname_input_frame)
    send_button['text'] = 'Отправить'
    send_button['command'] = lambda: process_input_text(nickname_input_field, chat.nickname_queue)
    send_button.pack(side='left')
    async with create_task_group() as tg:
        tg.start_soon(update_tk, register_window)
        tg.start_soon(update_label, text_label, nickname_input_field, chat.show_token_queue)


async def draw_main(chat: MineChat):
    root = tk.Tk()

    root.title('Чат Майнкрафтера')

    root_frame = tk.Frame()
    root_frame.pack(fill='both', expand=True)

    status_labels = create_status_panel(root_frame)

    msg_input_frame = tk.Frame(root_frame)
    msg_input_frame.pack(side='bottom', fill=tk.X)

    msg_input_field = tk.Entry(msg_input_frame)
    msg_input_field.pack(side='left', fill=tk.X, expand=True)

    msg_input_field.bind('<Return>', lambda event: process_input_text(msg_input_field, chat.sending_queue))

    send_button = tk.Button(msg_input_frame)
    send_button['text'] = 'Отправить'
    send_button['command'] = lambda: process_input_text(msg_input_field, chat.sending_queue)
    send_button.pack(side='left')

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side='top', fill='both', expand=True)

    try:
        async with create_task_group() as tg:
            tg.start_soon(chat.run)
            tg.start_soon(update_tk, root_frame)
            tg.start_soon(update_conversation_history, conversation_panel, chat.messages_queue, chat.history_file)
            tg.start_soon(update_status_panel, status_labels, chat.status_updates_queue)
    except InvalidToken as ex:
        root.destroy()
        async with create_task_group() as tg:
            tg.start_soon(chat.register_new_user)
            tg.start_soon(draw_register_window, chat, str(ex))
