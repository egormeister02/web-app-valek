import json
import asyncio
import aiohttp
import logging
from quart import Quart, render_template, request, jsonify
import datetime
from google.oauth2.service_account import Credentials
from gspread_asyncio import AsyncioGspreadClientManager
from config import Config

app = Quart(__name__)
app.config.from_object(Config)

# Логирование
logging.basicConfig(
    level=logging.INFO,  # Измените на DEBUG для более детализированных логов
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Функция для получения учетных данных Google
def get_google_creds():
    scopes = ['https://www.googleapis.com/auth/spreadsheets']  # OAuth-область для Google Sheets
    return Credentials.from_service_account_file(app.config['CREDENTIALS_FILE'], scopes=scopes)

# Асинхронная функция для получения Google Sheets
async def get_google_sheets_service():
    agcm = AsyncioGspreadClientManager(get_google_creds)
    return await agcm.authorize()

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

# Асинхронная функция для получения категорий
async def get_categories():
    try:
        logging.info("Получение списка категорий из Google Sheets")
        sheet = await get_google_sheets_service()
        spreadsheet = await sheet.open_by_key(app.config['GOOGLE_SHEET_ID'])
        
        # Метод worksheet не является асинхронным
        worksheet = spreadsheet.worksheet(app.config['CATEGORY_RANGE'])
        categories = await worksheet.get_all_values()
        logging.debug(f"Получены категории: {categories}")
        
        return [item[0] for item in categories if item]
    
    except Exception as e:
        logging.error(f"Ошибка при получении категорий: {e}")
        return []

# Асинхронная функция для добавления транзакции
async def add_transaction(date, category, type, amount):
    try:
        logging.info(f"Добавление транзакции: дата={date}, категория={category}, тип={type}, сумма={amount}")
        
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')
        
        values = [[formatted_date, category, type, amount]]
        body = {'values': values}
        
        sheet = await get_google_sheets_service()
        spreadsheet = await sheet.open_by_key(app.config['GOOGLE_SHEET_ID'])
        worksheet = spreadsheet.worksheet('Траты')
        
        # Получаем последнюю заполненную строку
        all_values = worksheet.get_all_values()
        last_row = len(all_values) + 1
        
        # Обновление данных в таблице
        await worksheet.update(f'D{last_row}:G{last_row}', values)
        
        logging.info(f"Транзакция добавлена успешно в строку: {last_row}")
        return f"{formatted_date}\n{category}\n{type}\n{amount}"
    
    except Exception as e:
        logging.error(f"Ошибка при добавлении транзакции: {e}")
        return None

@app.route('/form', methods=['GET', 'POST'])
async def form():
    if request.method == 'POST':
        form_data = await request.form
        chat_id = form_data.get('chat_id')
        date = form_data.get('date')
        category = form_data.get('category')
        type = form_data.get('type')
        amount = form_data.get('amount')

        operation = await add_transaction(date, category, type, amount)
        await send_telegram_message(chat_id, operation)
        
        return jsonify(message=operation)

    chat_id = request.args.get('chat_id')
    categories = await get_categories()
    return await render_template('form.html', categories=categories, chat_id=chat_id, datetime=datetime)

if __name__ == '__main__':
    app.run()
