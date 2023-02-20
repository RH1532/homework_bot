import logging
import os
import requests
import telegram
import time

from dotenv import load_dotenv

load_dotenv()


class MessageError(Exception):
    """Ошибка отправки сообщения."""

    pass


class EndpointError(Exception):
    """Ошибка endpoint."""

    pass


class ConnectionError(Exception):
    """Ошибка сети."""

    pass


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

REVIEW_VERDICT = 'Изменился статус проверки работы "{name}". {verdict}'
MESSAGE_SEND = 'Сообщение {message} отправлено'
RESPONE_TYPE = 'Неверный тип данных: {response}'
HOMEWORK_TYPE = 'Неверный тип данных: {homeworks}'
REVIEW_STATUS = 'Некорректный статус проверки: {status}'
PROGRAM_CRASH = 'Сбой в работе программы: {error}'


def check_tokens():
    """Проверка переменных окружения."""
    for name in ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']:
        if globals()[name] is None:
            logging.critical('Отсутсвует переменная окружения')
            raise KeyError


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(MESSAGE_SEND.format(message=message))
    except Exception:
        logging.exception('Ошибка при отправке сообщения')
        raise MessageError


def get_api_answer(timestamp):
    """Запрос к API."""
    payload = {'from_date': timestamp}
    parameters = dict(url=ENDPOINT, headers=HEADERS, params=payload)
    try:
        response = requests.get(**parameters)
    except requests.exceptions.RequestException:
        raise telegram.TelegramError(**parameters)
    if response.status_code != 200:
        raise EndpointError
    try:
        return response.json()
    except Exception:
        raise Exception


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(RESPONE_TYPE.format(response=type(response)))
    if 'homeworks' not in response:
        raise KeyError('Ошибка ключа "homeworks"')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(HOMEWORK_TYPE.format(homeworks=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Выводл информации о ревью."""
    if 'homework_name' not in homework:
        raise KeyError('Неверный ключ "homework_name"')
    name = homework['homework_name']
    status = homework['status']
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[status]
        return REVIEW_VERDICT.format(name=name, verdict=verdict)
    else:
        raise KeyError(REVIEW_STATUS.format(status=status))


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 1549962000
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) > 0:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                timestamp = response.get('current_date')
        except Exception as error:
            logging.error(PROGRAM_CRASH.format(error=error))
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(lineno)d',
        filename=__file__ + '.log',
        filemode='w'
    )
    main()
