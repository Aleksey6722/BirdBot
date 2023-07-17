import telebot
import os

TOKEN = os.getenv('BIRDS_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    x = 1
    bot.send_message(message.chat.id, 'Hello')


bot.infinity_polling()