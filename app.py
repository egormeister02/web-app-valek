import json
import requests
from flask import Flask, render_template, request, jsonify
import datetime
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config import Config

TELEGRAM_BOT_TOKEN = '7208144254:AAFlfsPMukGH5OX0NX0yzJph6Qk0JGGA-Ns'

app = Flask(__name__)
app.config.from_object(Config)

def get_google_sheets_service():
    creds = Credentials.from_service_account_file(app.config['CREDENTIALS_FILE'])
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    return sheet

import requests

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # URL для открытия мини-приложения
    mini_app_url = f"https://46.8.230.15.nip.io/form?chat_id={chat_id}"
    
    # Кнопка для мини-приложения
    inline_keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Открыть мини-приложение",
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
    
    response = requests.post(url, json=payload)
    
    # Проверка на успешность запроса
    if response.status_code != 200:
        print(f"Failed to send message. Status code: {response.status_code}")
        print(f"Response: {response.text}")


def get_categories():
    sheet = get_google_sheets_service()
    result = sheet.values().get(spreadsheetId=app.config['GOOGLE_SHEET_ID'],
                                range=app.config['CATEGORY_RANGE']).execute()
    categories = result.get('values', [])
    return [item[0] for item in categories if item]

def add_transaction(date, category, type, amount):
    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')
    values = [[formatted_date, category, type, amount]]
    body = {'values': values}
    '''
    sheet.values().append(spreadsheetId=app.config['GOOGLE_SHEET_ID'],
                          range='Траты!D:G',
                          valueInputOption='USER_ENTERED',
                          body=body).execute()
    '''
    return f"\n{formatted_date} \n{category} \n{type} \n{amount}"

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
    app.run()