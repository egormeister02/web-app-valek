from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    chat_id = update.message.chat_id

    url = f"https://46.8.230.15.nip.io/form?chat_id={chat_id}"
    # Создаем кнопку для запуска мини-приложения в WebView
    keyboard = [
        [InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url=url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение пользователю с кнопкой
    await context.bot.send_message(chat_id, "Запуск мини-приложения", reply_markup=reply_markup)

# Создаем экземпляр приложения
application = Application.builder().token("7208144254:AAFlfsPMukGH5OX0NX0yzJph6Qk0JGGA-Ns").build()

# Добавляем обработчик команды /start
application.add_handler(CommandHandler("start", start))

# Запускаем бота
application.run_polling()
