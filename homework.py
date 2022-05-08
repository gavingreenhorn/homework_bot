from http import HTTPStatus
import logging
import os
import time

from dotenv import load_dotenv
import requests
from telegram import Bot


load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAD_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

TYPE_ERROR_MSG = '{obj} is a {type}, when {expected_type} was expected'
KEY_ERROR_MSG = '{obj} does not have a key {key}'
TOKEN_MISSING_MSG = '{0} is missing'
CONNECTION_ERROR_MSG = ('Connection error occured while trying to '
                        'connect to {endpoint}:\n {error_data}')
HTTP_ERROR_MSG = ('The server responded with status code [{response_code}]\n'
                  'The following requst was sent:\n')
HTTP_DENIED_MSG = ('The server refused to provide requested data '
                   'with an answer [{code}]\n'
                   'It might be due to the following errors: '
                   '{errors}\n')

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logname = __file__ + '.log'
logging.basicConfig(
    level=logging.INFO,
    filename=logname,
    filemode='w',
    format=(
        '%(asctime)s.%(msecs)03d\t%(levelname)s\t'
        '%(name)s :: %(funcName)s :: line %(lineno)s\t%(message)s'
    ),
    datefmt=r'%d.%m %H:%M:%S'
)


def send_message(bot, message):
    """Send a message to my chat."""
    api_response = bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logging.info(api_response)


def get_api_answer(current_timestamp):
    """Query the API for homework updates."""
    payload = {'from_date': current_timestamp}
    request_data = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': payload,
    }
    data_as_string = '\n'.join(f'{k}: {v}' for k, v in request_data.items())
    try:
        response = requests.get(**request_data)
    except requests.exceptions.ConnectionError as error:
        raise requests.exceptions.ConnectionError(
            CONNECTION_ERROR_MSG.format(
                endpoint=ENDPOINT, error_data=str(error)
            )
        )
    response_code = response.status_code
    try:
        response_data = response.json()
    except ValueError:
        pass
    else:
        if 'error' in response_data or 'code' in response_data:
            errors = response_data.get('error')
            code = response_data.get('code')
            raise requests.exceptions.HTTPError(
                HTTP_DENIED_MSG.format(
                    code=code,
                    errors=errors
                )
            )
    if response_code != HTTPStatus.OK:
        raise requests.exceptions.HTTPError(
            HTTP_ERROR_MSG.format(response_code=response_code)
            + data_as_string
        )
    return response.json()


def check_response(response):
    """Check that the response data is correct."""
    if not isinstance(response, dict):
        raise TypeError(
            TYPE_ERROR_MSG.format(
                obj='"response"', type=type(response),
                expected_type='dictionary'
            )
        )
    elif 'homeworks' not in response:
        raise KeyError(
            KEY_ERROR_MSG.format(obj='"response"', key='"homeworks"')
        )
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            TYPE_ERROR_MSG.format(
                obj='"homeworks"', type=type(homeworks),
                expected_type='list'
            )
        )
    return homeworks


def parse_status(homework):
    """Check that homework data is complete."""
    status = homework.get('status')
    name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS.get(status)
    if status not in HOMEWORK_VERDICTS:
        raise KeyError(
            KEY_ERROR_MSG.format(obj='verdicts', key=status)
        )
    return f'Изменился статус проверки работы "{name}". {verdict}'


def check_tokens():
    """Check that all the required tokens are in place."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Program's entry point."""
    if not check_tokens():
        message = 'One or more tokens are missing:\n'
        if not PRACTICUM_TOKEN:
            message += TOKEN_MISSING_MSG.format('practicum token')
        elif not TELEGRAM_TOKEN:
            message += TOKEN_MISSING_MSG.format('telegram token')
        else:
            message += TOKEN_MISSING_MSG.format('chat ID')
        logging.critical(message)
        raise NameError(message)

    bot = Bot(token=TELEGRAM_TOKEN)
    last_message = ''
    current_timestamp = int(time.time())

    while True:
        message = None
        try:
            response = get_api_answer(current_timestamp)
            logging.info(response)
            homeworks = check_response(response)
            current_timestamp = response.get('current_date', current_timestamp)
            if not homeworks:
                continue
            homework = homeworks[0]
            message = parse_status(homework)
        except Exception as error:
            message = str(error)
            logging.error(message)
        finally:
            if message and message != last_message:
                last_message = message
                try:
                    send_message(bot, message)
                except Exception as error:
                    logging.exception(error)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
