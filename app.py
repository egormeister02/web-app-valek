import json
import requests
from flask import Flask, render_template, request, jsonify
import datetime
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config import Config
import logging
import threading
import time
import gc
gc.collect()


TELEGRAM_BOT_TOKEN = '7208144254:AAFlfsPMukGH5OX0NX0yzJph6Qk0JGGA-Ns'

app = Flask(__name__)
app.config.from_object(Config)

# Глобальная переменная для кэша категорий
categories_cache = []
last_updated = 0  # Время последнего обновления кэша
CACHE_DURATION = 600  # Время кэширования в секундах (например, 5 минут)
cache_update_event = threading.Event()

def get_google_sheets_service():
    creds = Credentials.from_service_account_file(app.config['CREDENTIALS_FILE'])
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    return sheet

def update_categories_cache():
    global categories_cache, last_updated
    while True:
        # Если было получено событие остановки (Timeout), выходим из цикла
        if cache_update_event.wait(timeout=CACHE_DURATION):
            logging.info("Поток обновления кэша категорий завершен.")
            break
        
        try:
            sheet = get_google_sheets_service()
            result = sheet.values().get(spreadsheetId=app.config['GOOGLE_SHEET_ID'],
                                        range=app.config['CATEGORY_RANGE']).execute()
            categories_cache = [item[0] for item in result.get('values', []) if item]
            last_updated = time.time()
            logging.info("Кэш категорий обновлен.")
        except Exception as e:
            logging.error(f"Ошибка при обновлении кэша категорий: {e}")


def get_categories():
    return categories_cache


def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # URL для открытия мини-приложения
    mini_app_url = f"https://95.182.98.91.nip.io/form?chat_id={chat_id}"
    
    # Кнопка для мини-приложения
    inline_keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Добавить запись",
                    "web_app": {
                        "url": mini_app_url
                    }
                }
            ]
        ]
    }
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': inline_keyboard
    }
    
    response = requests.post(url, json=payload, timeout=10)  # Тайм-аут 10 секунд
    
    # Проверка на успешность запроса
    if response.status_code != 200:
        print(f"Failed to send message. Status code: {response.status_code}")
        print(f"Response: {response.text}")


# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логгирования
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

def get_last_filled_row(sheet, spreadsheet_id, range_name):
    # Получение всех данных из указанного диапазона
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    
    # Определение последней заполненной строки
    if values:
        return len(values)  # Последняя заполненная строка в диапазоне
    else:
        return 0  # Если данных нет, возвращаем 0

from googleapiclient.errors import HttpError

def add_transaction(date, category, type, amount):
    try:
        # Логирование начала работы функции
        logging.info(f"Добавление транзакции: дата={date}, категория={category}, тип={type}, сумма={amount}")
        
        # Преобразование даты
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')
        logging.info(f"Форматированная дата: {formatted_date}")
        
        # Формирование данных для записи
        values = [[formatted_date, category, type, amount]]
        body = {'values': values}
        
        # Получение доступа к Google Sheets API
        sheet = get_google_sheets_service()
        spreadsheet_id = app.config['GOOGLE_SHEET_ID']
        
        # Определение последней заполненной строки в диапазоне D:G
        last_row = get_last_filled_row(sheet, spreadsheet_id, 'Траты!D:G')
        next_row = last_row + 1
        
        # Обновление данных в диапазоне D:G
        result = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=f'Траты!D{next_row}:G{next_row}',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        # Логирование результата
        logging.info(f"Ответ от API: {result}")
        
        # Извлечение диапазона добавленных данных
        updated_range = result.get('updatedRange')
        if updated_range:
            logging.info(f"Данные успешно добавлены в диапазон: {updated_range}")
        else:
            logging.warning("Не удалось получить диапазон добавленных данных.")
    
    except HttpError as error:
        # Логирование ошибок Google API
        logging.error(f"Ошибка Google API: {error}")
    
        
    
    except Exception as e:
        # Логирование ошибок
        logging.error(f"Ошибка при добавлении транзакции: {e}")

    return f"{formatted_date}\n{category}\n{type}\n{amount}"



@app.route('/form', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        # Получаем chat_id из тела POST-запроса
        chat_id = request.form.get('chat_id')
        date = request.form.get('date')
        category = request.form.get('category')
        type = request.form.get('type')
        amount = request.form.get('amount')

        # Добавляем транзакцию
        operation = add_transaction(date, category, type, amount)
        
        # Отправляем результат в Telegram
        send_telegram_message(chat_id, operation)
        
        return jsonify(message=operation)
    
    # Загружаем категории и передаем chat_id
    chat_id = request.args.get('chat_id')
    categories = get_categories()
    return render_template('form.html', categories=categories, chat_id=chat_id, datetime=datetime)


if __name__ == '__main__':
    # Запускаем поток обновления кэша категорий
    cache_update_thread = threading.Thread(target=update_categories_cache, daemon=True)
    cache_update_thread.start()

    try:
        # Запускаем приложение Flask
        app.run()
    finally:
        # Завершаем поток обновления кэша при завершении приложения
        cache_update_event.set()  # Сигнализируем потоку завершиться
        cache_update_thread.join()  # Дожидаемся завершения потока