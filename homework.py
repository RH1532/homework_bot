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

ENVIRONMENT_VARIABLES = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID'
]

MISSING_TOKEN = 'Отсутсвует переменная окружения: {tokens}'
REVIEW_VERDICT = 'Изменился статус проверки работы "{name}". {verdict}'
MESSAGE_SEND = 'Сообщение {message} отправлено'
RESPONSE_TYPE = 'Неверный тип данных response: {response}'
HOMEWORK_TYPE = 'Неверный тип данных homeworks: {homeworks}'
REVIEW_STATUS = 'Некорректный статус проверки: {status}'
PROGRAM_CRASH = 'Сбой в работе программы: {error}'
KEY_MISSING = 'Отсутсвует ключ "homework_name"'
KEY_ERROR = 'Ошибка ключа "homeworks"'
MESSAGE_ERROR = 'Ошибка при отправке сообщения'
ENDPOINT_ERROR = 'Ошибка соединения: {status_code}'
RESPONSE_ERROR = 'Ошибка соединения: {error}'


def check_tokens():
    """Проверка переменных окружения."""
    missing_variables = []
    for name in ENVIRONMENT_VARIABLES:
        if globals()[name] is None:
            missing_variables.append(name)
    if len(missing_variables) > 0:
        logging.critical(MISSING_TOKEN.format(tokens=missing_variables))
        raise KeyError


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(MESSAGE_SEND.format(message=message))
    except Exception:
        logging.exception(MESSAGE_ERROR.format(
            message=message,
            error=Exception
        ))
        raise MessageError


def get_api_answer(timestamp):
    """Запрос к API."""
    parameters = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={'from_date': timestamp}
    )
    try:
        response = requests.get(**parameters)
    except Exception:
        raise ConnectionError(RESPONSE_ERROR.format(error=Exception))
    if response.status_code != 200:
        raise EndpointError(ENDPOINT_ERROR.format(
            status_code=response.status_code
        ))
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(RESPONSE_TYPE.format(response=type(response)))
    if 'homeworks' not in response:
        raise KeyError(KEY_ERROR)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(HOMEWORK_TYPE.format(homeworks=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Выводл информации о ревью."""
    if 'homework_name' not in homework:
        raise KeyError(KEY_MISSING)
    status = homework['status']
    if status in HOMEWORK_VERDICTS:
        return REVIEW_VERDICT.format(
            name=homework['homework_name'],
            verdict=HOMEWORK_VERDICTS[status]
        )
    raise ValueError(REVIEW_STATUS.format(status=status))


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks):
                message = parse_status(homeworks[0])
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
                timestamp = response.get('current_date') or timestamp
        except Exception as error:
            message = PROGRAM_CRASH.format(error=error)
            logging.error(message)
            if message != last_message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(lineno)d, %(message)s',
        handlers=[
            logging.FileHandler(__file__ + '.log'),
            logging.StreamHandler()
        ]
    )
    main()
