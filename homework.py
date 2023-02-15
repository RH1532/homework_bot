import os

import time

import requests

import telegram

from dotenv import load_dotenv

import logging

load_dotenv()


logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w'
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        logging.critical('Отсутсвует переменная окружения')
        return False


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение {message} отправлено')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')
        raise Exception


def get_api_answer(timestamp):
    """Запрос к API."""
    timestamp = timestamp or int(time.time())
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        logging.error(f'Ошибка подключения: {error}')
        raise Exception
    if response.status_code != 200:
        logging.error('Ошибка подключения')
        raise Exception
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        logging.error('Неверный тип данных')
        raise TypeError
    if 'homeworks' not in response:
        logging.error('Ошибка ключа')
        raise KeyError
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        logging.error('Неверный тип данных')
        raise TypeError
    return homeworks


def parse_status(homework):
    """Выводл информации о ревью."""
    if 'homework_name' not in homework:
        logging.error('Неверный ключ')
        raise KeyError
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error('Некорректный статус проверки: {homework_status}')
        raise Exception


def main():
    """Основная логика работы бота."""
    #if not check_tokens():
    #    raise Exception('Отсутсвует переменная окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            send_message(bot, response)
            homework = check_response(response)
            send_message(bot, homework)
            message = parse_status(homework[0])
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            #send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
