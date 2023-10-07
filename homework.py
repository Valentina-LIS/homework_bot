import logging
import os
import sys
import time
from http import HTTPStatus
import telegram
import requests
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACT_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logging.critical('Отсутствуют обязательные переменные окружения.')
    return False


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Бот отправил сообщение: "{message}"')
    except telegram.error.TelegramError as error:
        logging.error('Сбой при отправке сообщения.', error)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    try:
        payload = {'from_date': timestamp}
        homeworks = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        logging.debug('Отправка запроса к API.')
        if homeworks.status_code != HTTPStatus.OK:
            logging.error('Эдпоинт недоступен.')
            raise Exception('Эдпоинт недоступен.')
        return homeworks.json()
    except requests.RequestException as error:
        logging.error('Возникла ошибка подключения.', error)
    except Exception as error:
        logging.error('Ошибка при подключении к эдпоинту.', error)
        raise Exception('Ошибка при подключении к эдпоинту.', error)


def check_response(response):
    """Проверяет ответ API на соответствие с документацией."""
    if not isinstance(response, dict):
        logging.error('Ответ API не соответствует документации.')
        raise TypeError('Ответ API не соответствует документации.')
    elif 'homeworks' not in response:
        logging.error('Отсутствует ключ "homeworks" в ответе API.')
        raise KeyError('Отсутствует ключ "homeworks" в ответе API.')
    elif not isinstance(response['homeworks'], list):
        logging.error('Неверный тип данных для homeworks')
        raise TypeError('Неверный тип данных для homeworks')
    return response.get('homeworks')


def parse_status(homework):
    """Получает статус домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        if homework_status not in HOMEWORK_VERDICTS:
            logging.error(
                f'Статус {homework_status} невозможно обработать'
            )
            raise Exception(
                'Неожиданный статус домашней работы в ответе API'
            )
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError('Ключ "homework_name" отсутствует в ответе API.'):
        logging.error('Ключ "homework_name" отсутствует в ответе API.')
    except Exception as error:
        logging.error(f'Ошибка при извлечении информации о работе: {error}')
        raise


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        raise SystemExit('Программа принудительно остановлена.')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get("current_date")
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if message:
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)])
    main()
