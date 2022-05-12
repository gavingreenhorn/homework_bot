from http import HTTPStatus
import logging
import os
import sys
import time

from dotenv import load_dotenv
from telegram import Bot
import requests

from bot_exceptions import HTTPRequestError, ServiceDeniedError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAD_ID')
TOKEN_NAMES = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

STATUS_CHANGED_MESSAGE = 'Изменился статус проверки работы "{name}". {verdict}'

RESPONSE_INFO = 'Response from API: {response}'
VERDICT_INFO = 'Verdict: {verdict}'

BASE_ERROR_MESSAGE = ('An error occured when processing request to API:\n'
                      '{error}')
BOT_ERROR_MESSAGE = ('An error occured when sending a message to the bot:\n'
                     '{error}'
                     'The following message was sent to the bot:\n{message}')
TYPE_ERROR_MESSAGE = '{obj} is a {type}, when {expected_type} was expected'
KEY_ERROR_MESSAGE = '{obj} does not have a key {key}'
NO_VERDICT_MESSAGE = 'Received unrecognized status: {status}'
TOKENS_MISSING_MESSAGE = 'One or more tokens are missing'
TOKENS_LOGGING_MESSAGE = 'The following tokens are missing: {tokens}'
CONNECTION_ERROR_MESSAGE = ('Connection error. '
                            'The following requst was sent:\n'
                            'url: {url}\nheaders: {headers}\n'
                            'params: {params}')
HTTP_ERROR_MESSAGE = ('The server responded with status code '
                      '[{response_code}]\n'
                      'The following requst was sent:\n'
                      'url: {url}\nheaders: {headers}\nparams: {params}')
HTTP_DENIED_MESSAGE = ('The server refused to provide requested data:\n'
                       'Code: [{code}]\n'
                       'Errors: {errors}\n'
                       'The following requst was sent:\n'
                       'url: {url}\nheaders: {headers}\nparams: {params}') 

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Send a message to my chat."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        logging.exception(
            BOT_ERROR_MESSAGE.format(error=error, message=message)
        )
        return False
    return True


def get_api_answer(current_timestamp):
    """Query the API for homework updates."""
    request_data = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp},
    }
    try:
        response = requests.get(**request_data)
    except requests.exceptions.ConnectionError as error:
        raise ConnectionError(
            CONNECTION_ERROR_MESSAGE.format(
                error=error, **request_data
            )
        )
    response_code = response.status_code
    response_data = response.json()
    if 'error' in response_data or 'code' in response_data:
        errors = response_data.get('error')
        code = response_data.get('code')
        raise ServiceDeniedError(
            HTTP_DENIED_MESSAGE.format(
                code=code, errors=errors, **request_data
            )
        )
    if response_code != HTTPStatus.OK:
        raise HTTPRequestError(
            HTTP_ERROR_MESSAGE.format(
                response_code=response_code, **request_data
            )
        )
    return response_data


def check_response(response):
    """Check that the response data is correct."""
    if not isinstance(response, dict):
        raise TypeError(
            TYPE_ERROR_MESSAGE.format(
                obj='"response"', type=type(response),
                expected_type='dictionary'
            )
        )
    if 'homeworks' not in response:
        raise KeyError(
            KEY_ERROR_MESSAGE.format(obj='"response"', key='"homeworks"')
        )
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            TYPE_ERROR_MESSAGE.format(
                obj='"homeworks"', type=type(homeworks),
                expected_type='list'
            )
        )
    return homeworks


def parse_status(homework):
    """Check that homework data is complete."""
    status = homework['status']
    name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            NO_VERDICT_MESSAGE.format(status=status)
        )
    return STATUS_CHANGED_MESSAGE.format(
        name=name,
        verdict=HOMEWORK_VERDICTS[status]
    )


def check_tokens():
    """Check that all the required tokens are in place."""
    missing = [name for name in TOKEN_NAMES if not globals()[name]]
    if missing:
        logging.critical(TOKENS_LOGGING_MESSAGE.format(tokens=missing))
        return False
    return True


def main():
    """Program's entry point."""
    if not check_tokens():
        raise NameError(TOKENS_MISSING_MESSAGE)
    bot = Bot(token=TELEGRAM_TOKEN)
    last_message = None
    last_homework = None
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            logging.debug(RESPONSE_INFO.format(response=response))
            homeworks = check_response(response)
            if not homeworks:
                continue
            homework = homeworks[0]
            message = parse_status(homework)
            logging.debug(VERDICT_INFO.format(verdict=message))

            if last_message and homework['id'] != last_homework:
                message = last_message
            elif message == last_message:
                continue
            if send_message(bot, message):
                last_message = message
                last_homework = homework['id']
                current_timestamp = response.get(
                    'current_date', current_timestamp
                )

        except Exception as error:
            message = BASE_ERROR_MESSAGE.format(error=error)
            logging.error(message)
            if message != last_message and send_message(bot, message):
                last_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(__file__ + '.log', 'w')
        ],
        format=(
            '%(asctime)s.%(msecs)03d\t%(levelname)s\t'
            '%(funcName)s :: line %(lineno)s\t%(message)s'
        ),
        datefmt=r'%d.%m %H:%M:%S'
    )
    main()
