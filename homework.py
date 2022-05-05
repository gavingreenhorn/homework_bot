import os
import sys
import time
import logging

import requests
from dotenv import load_dotenv
from telegram import Bot

import exceptions


load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAD_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def get_logger(logger_name):
    """Sets up a logger for when the module is called directly."""
    logger = logging.getLogger(logger_name)
    logger.setLevel('DEBUG')

    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d\t%(levelname)s\t%(message)s',
        datefmt=r'%d/%m %H:%M:%S'
    )

    info_handler = logging.FileHandler(
        filename='mainlog.log',
        mode='w',
        encoding='utf-8'
    )
    info_handler.setLevel('INFO')
    info_handler.setFormatter(formatter)
    exc_handler = logging.StreamHandler(stream=sys.stderr)
    exc_handler.setLevel('ERROR')
    exc_handler.setFormatter(formatter)

    logger.addHandler(info_handler)
    logger.addHandler(exc_handler)

    return logger


def send_message(bot, message):
    """Send a message to my chat."""
    api_response = bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.info(api_response)


def get_api_answer(current_timestamp):
    """Query the API for homework updates."""
    timestamp = current_timestamp or int(time.time())
    payload = {'from_date': timestamp}
    response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    if response.status_code != 200:
        raise exceptions.MoCk_HtTp_ErRoR
    return response.json()


def check_response(response):
    """Check that the response data is correct."""
    try:
        homeworks = response['homeworks']
        current_timestamp = response['current_date']
    except KeyError as error:
        raise exceptions.IncorrectResponseError(
            'Response does not contain %s' % str(error)
        )
    if not isinstance(homeworks, list):
        raise exceptions.IncorrectResponseError('Homeworks is not a list')
    return homeworks, current_timestamp


def parse_status(homework):
    """Check that homework data is complete."""
    if isinstance(homework, list):
        homework = homework[0]
    try:
        homework_status = homework['status']
    except KeyError as error:
        raise exceptions.IncorrectResponseError(
            'Homework does not contain %s' % str(error)
        )
    homework_name = homework['homework_name']
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise exceptions.UnknownReviewStatus
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Check that all the required tokens are in place."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN


def main():
    """Program's entry point."""
    current_timestamp = int(time.time())

    if check_tokens():
        bot = Bot(token=TELEGRAM_TOKEN)
    else:
        message = 'One or both of the tokens missing!'
        logger.critical(message)
        raise exceptions.TokensMissingError(message)

    while True:
        message = None
        try:
            response = get_api_answer(current_timestamp)
            logger.info(response)
            homeworks, current_timestamp = check_response(response)
            if not homeworks:
                continue
            homework = max(homeworks, key=lambda x: x.get('id'))
            message = parse_status(homework)
        except requests.exceptions.ConnectionError as error:
            message = 'Network error occured: (%s)' % str(error)
            logger.error(message)
        except requests.exceptions.HTTPError as error:
            message = 'Unable to connect to API: (%s)' % str(error)
            logger.error(message)
        except Exception as error:
            message = error.message
            logger.error(message)
        finally:
            if message:
                send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    global logger
    logger = get_logger('your_logger')
    main()
