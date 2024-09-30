import os

# Ссылка на Google таблицу
GOOGLE_SHEET_ID = '1F8wvyOAr8CKUNYbrRcyDWhpVmN66lBHv1wmrQl5bhUQ'  # Замените на ваш ID таблицы

# Диапазон для получения категорий
CATEGORY_RANGE = 'Инфо!A2:A'

# Путь к файлу с учетными данными
CREDENTIALS_FILE = 'credentials.json'

TELEGRAM_BOT_TOKEN = '7208144254:AAFlfsPMukGH5OX0NX0yzJph6Qk0JGGA-Ns'

# Конфигурации для Flask
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DEBUG = True
    GOOGLE_SHEET_ID = GOOGLE_SHEET_ID
    CATEGORY_RANGE = CATEGORY_RANGE
    CREDENTIALS_FILE = CREDENTIALS_FILE
