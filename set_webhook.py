import requests
TELEGRAM_BOT_TOKEN = '7208144254:AAFlfsPMukGH5OX0NX0yzJph6Qk0JGGA-Ns'
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/'
webhook_url = 'https://46.8.230.15.nip.io/webhook'
response = requests.get(f'{TELEGRAM_API_URL}setWebhook?url={webhook_url}')
print(response.json())

