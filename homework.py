from http import HTTPStatus
import logging
import os
import sys
import time

from dotenv import load_dotenv
from telegram import Bot
import requests

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = ''

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

STATUS_CHANGED_MESSAGE = 'Изменился статус проверки работы "{name}". {verdict}'

RESPONSE_INFO = 'Response from API: {response}'
VERDICT_INFO = 'Verdict: {verdict}'

BASE_ERROR_MESSAGE = ('An error occured when processing request to API: '
                      '{message}')
BOT_RESPONSE_MESSAGE = 'Received the following response from the bot: {data}'
BOT_ERROR_MESSAGE = 'An error occured when sending a message to bot: {message}'

TYPE_ERROR_MESSAGE = '{obj} is a {type}, when {expected_type} was expected'
KEY_ERROR_MESSAGE = '{obj} does not have a key {key}'
NO_VERDICT_MESSAGE = 'Received unrecognized status: {status}'
TOKENS_MISSING_MESSAGE = 'The following tokens are missing: {tokens}'
CONNECTION_ERROR_MESSAGE = ('Connection error. '
                            'The following requst was sent:\n'
                            '{url}\n{headers}\n{params}')
HTTP_ERROR_MESSAGE = ('The server responded with status code '
                      '[{response_code}]\n'
                      'The following requst was sent:\n'
                      '{url}\n{headers}\n{params}')
HTTP_DENIED_MESSAGE = ('The server refused to provide requested data '
                       'with an answer [{code}]\n'
                       'It might be due to the following errors: '
                       '{errors}\n'
                       'The following requst was sent:\n'
                       '{url}\n{headers}\n{params}')

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Send a message to my chat."""
    api_response = bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logging.info(BOT_RESPONSE_MESSAGE.format(data=api_response))


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
        raise IOError(
            CONNECTION_ERROR_MESSAGE.format(
                error=error, **request_data
            )
        )
    response_code = response.status_code
    response_data = response.json()
    if 'error' in response_data or 'code' in response_data:
        errors = response_data.get('error')
        code = response_data.get('code')
        raise IOError(
            HTTP_DENIED_MESSAGE.format(
                code=code, errors=errors, **request_data
            )
        )
    if response_code != HTTPStatus.OK:
        raise IOError(
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
    status = homework.get('status')
    name = homework['homework_name']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            NO_VERDICT_MESSAGE.format(status=status)
        )
    verdict = HOMEWORK_VERDICTS.get(status)
    return STATUS_CHANGED_MESSAGE.format(name=name, verdict=verdict)


def check_tokens():
    """Check that all the required tokens are in place."""
    tokens = {
        'practicum token': PRACTICUM_TOKEN,
        'telegram token': TELEGRAM_TOKEN,
        'chat ID': TELEGRAM_CHAT_ID,
    }
    if not all(tokens.values()):
        missing = set()
        for name, token in tokens.items():
            if not token:
                missing.add(name)
        logging.critical(TOKENS_MISSING_MESSAGE.format(tokens=missing))
        return False
    return True


def main():
    """Program's entry point."""
    str_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.FileHandler(__file__ + '.log', 'w')

    logging.basicConfig(
        level=logging.INFO,
        handlers=[str_handler, file_handler],
        format=(
            '%(asctime)s.%(msecs)03d\t%(levelname)s\t'
            '%(funcName)s :: line %(lineno)s\t%(message)s'
        ),
        datefmt=r'%d.%m %H:%M:%S'
    )

    if not check_tokens():
        raise NameError('Tokens missing')
    bot = Bot(token=TELEGRAM_TOKEN)
    last_message = ''
    current_timestamp = int(time.time())

    while True:
        message = None
        try:
            response = get_api_answer(current_timestamp)
            logging.debug(RESPONSE_INFO.format(response=response))
            homeworks = check_response(response)
            if not homeworks:
                continue
            message = parse_status(homeworks[0])
            logging.debug(VERDICT_INFO.format(verdict=message))
        except Exception as error:
            message = str(error)
            logging.error(BASE_ERROR_MESSAGE.format(message=message))
        finally:
            if message and message != last_message:
                try:
                    send_message(bot, message)
                except Exception as error:
                    logging.exception(BOT_ERROR_MESSAGE.format(message=error))
                else:
                    current_timestamp = response.get(
                        'current_date', current_timestamp)
                    last_message = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
