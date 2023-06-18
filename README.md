# Подключаемся к подпольному чату

Скрипт для чтения и отправки сообщений в чат minecraft

## Как установить

- Для работы скрипта нужен Python версии не ниже 3.8.
- Установите зависимости: `pip install -r requirements.txt`

## Как запустить

Все аргументы запуска скриптов можно заменить настройкой в переменных окружения.

### Для чтения чата запустите скрипт

```bash
python chat_reader.py [--host HOST] [--port PORT] [--to_file TO_FILE] [--log_off] [--log_filename LOG_FILENAME]
```

| Аргумент       | Описание                                            |    По умолчанию     | Переменная окружения  |
|----------------|-----------------------------------------------------|:-------------------:|:---------------------:|
| `host`         | Адрес хоста                                         |  minechat.dvmn.org  |         HOST          |
| `port`         | Порт хоста                                          |        5000         |         PORT          |
| `to_file`      | Имя файла, в который будет сохраняться история чата |    minechat.txt     |        TO_FILE        |
| `log_off`      | Отключение логирования                              |        False        |        LOG_OFF        |
| `log_filename` | Имя файла для сохранения логов                      |      chat.log       |     LOG_FILENAME      |

### Для отправки сообщения запустите скрипт:

```bash
python chat_writer.py [--nickname NICKNAME] [--host HOST] [--port PORT] [--log_off] [--log_filename LOG_FILENAME] message
```


| Аргумент        | Описание                                                     |   По умолчанию    | Переменная окружения  |
|-----------------|--------------------------------------------------------------|:-----------------:|:---------------------:|
| `message`       | **Обязательный аргумент**. Сообщение для отправки            |                   |                       |
| `host`          | Адрес хоста                                                  | minechat.dvmn.org |         HOST          |
| `port`          | Порт хоста                                                   |       5050        |         PORT          |
| `nickname`      | Никнейм для регистрации, если пользователь е зарегистрирован |                   |        NICKNAME       |
| `log_off`       | Отключение логирования                                       |       False       |        LOG_OFF        |
| `log_filename`  | Имя файла для сохранения логов                               |     chat.log      |     LOG_FILENAME      |


# Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).