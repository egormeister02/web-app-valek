import json
import asyncio
import aiohttp
import logging
from quart import Quart, render_template, request, jsonify
import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import Config

app = Quart(__name__)
app.config.from_object(Config)

# Глобальная переменная для кэширования категорий
category_cache = []

# Очередь для фоновых задач
transaction_queue = asyncio.Queue()

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Функция для получения учетных данных Google
def get_google_creds():
    creds = Credentials.from_service_account_file(app.config['CREDENTIALS_FILE'])
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()

# Асинхронная задача для обновления кэша каждые 10 минут
async def update_category_cache():
    global category_cache
    while True:
        try:
            logging.info("Обновление кэша категорий из Google Sheets")
            
            sheet = get_google_creds()
            result = sheet.values().get(spreadsheetId=app.config['GOOGLE_SHEET_ID'],
                                        range=app.config['CATEGORY_RANGE']).execute()
            
            categories = result.get('values', [])
            category_cache = [item[0] for item in categories if item]
            
            logging.info(f"Кэш категорий обновлен: {category_cache}")
        except Exception as e:
            logging.error(f"Ошибка при обновлении кэша категорий: {e}")

        # Ждем 10 минут перед следующим обновлением
        await asyncio.sleep(600)

# Асинхронная функция для записи транзакций в Google Sheets
async def process_transaction_queue():
    while True:
        transaction = await transaction_queue.get()  # Ожидаем новую задачу
        try:
            date, category, type, amount, chat_id = transaction
            logging.info(f"Добавление транзакции: дата={date}, категория={category}, тип={type}, сумма={amount}")

            # Преобразование даты
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')

            values = [[formatted_date, category, type, amount]]
            
            sheet = get_google_creds()
            last_row = sheet.values().get(spreadsheetId=app.config['GOOGLE_SHEET_ID'], range='Траты!D:G').execute()
            next_row = len(last_row.get('values', [])) + 1

            result = sheet.values().update(
                spreadsheetId=app.config['GOOGLE_SHEET_ID'],
                range=f'Траты!D{next_row}:G{next_row}',
                valueInputOption='USER_ENTERED',
                body={'values': values}
            ).execute()
            
            logging.info(f"Транзакция успешно добавлена: {result}")
            
            await send_telegram_message(chat_id, f"{formatted_date}\n{category}\n{type}\n{amount}")

        except Exception as e:
            logging.error(f"Ошибка при добавлении транзакции: {e}")
            await send_telegram_message(chat_id, f"Ошибка при добавлении транзакции\n{formatted_date}\n{category}\n{type}\n{amount}")

        transaction_queue.task_done()  # Помечаем задачу как выполненную

# Функция для получения категорий из кэша
def get_categories():
    return category_cache

# Асинхронная функция для отправки сообщений в Telegram
async def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{app.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
    mini_app_url = f"https://95.182.98.91.nip.io/form?chat_id={chat_id}"
    
    inline_keyboard = {
        "inline_keyboard": [
            [{"text": "Добавить запись", "web_app": {"url": mini_app_url}}]
        ]
    }
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': inline_keyboard
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                logging.error(f"Failed to send message. Status code: {response.status}")
                logging.error(f"Response: {await response.text()}")

# Асинхронная функция для добавления транзакции в очередь
async def add_transaction_to_queue(date, category, type, amount, chat_id):
    await transaction_queue.put((date, category, type, amount, chat_id))  # Добавляем транзакцию в очередь
    logging.info(f"Транзакция добавлена в очередь: {date}, {category}, {type}, {amount}")

@app.route('/form', methods=['GET', 'POST'])
async def form():
    if request.method == 'POST':
        form_data = await request.form
        chat_id = form_data.get('chat_id')
        date = form_data.get('date')
        category = form_data.get('category')
        type = form_data.get('type')
        amount = form_data.get('amount')

        # Добавляем транзакцию в очередь (асинхронно)
        asyncio.create_task(add_transaction_to_queue(date, category, type, amount, chat_id))  # "Fire and forget"
        
        # Мгновенно возвращаем ответ
        return jsonify(message="Транзакция добавлена в очередь, скоро будет обработана.")

    chat_id = request.args.get('chat_id')
    categories = get_categories()  # Получаем категории из кэша
    return await render_template('form.html', categories=categories, chat_id=chat_id, datetime=datetime)


# Запуск фоновых задач для обновления кэша и обработки транзакций
@app.before_serving
async def start_background_tasks():
    app.add_background_task(update_category_cache)
    app.add_background_task(process_transaction_queue)

if __name__ == '__main__':
    app.run()
