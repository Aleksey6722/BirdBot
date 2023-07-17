import telebot
import os
import csv

TOKEN = os.getenv('BIRDS_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)


def checking_csv(path):
    example = ['Row #', 'Taxon Order', 'Category', 'Common Name', 'Scientific Name', 'Count', 'Location', 'S/P',
               'Date', 'LocID', 'SubID', 'Exotic', 'Countable']
    with open(path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        first_row = next(reader)
        return False if first_row != example else True



@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Hello')


@bot.message_handler(content_types=['document'])
def get_csv(message):
    if message.document.mime_type != 'text/csv':
        bot.send_message(message.chat.id, 'Неверный формат файла. Отправьте файл CSV')
        return
    file_name = message.document.file_name
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    path = os.path.join(os.curdir, 'temp', file_name)
    with open(path, 'wb') as file:
        file.write(downloaded_file)
    if checking_csv(path):
        bot.send_message(message.chat.id, 'Файл принят!')
    else:
        bot.send_message(message.chat.id, 'Файл не соответствует образцу')



bot.infinity_polling()
