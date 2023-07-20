import telebot
import os
import csv
from sqlalchemy import exc

from models import session, Bird, User, UserBird
TOKEN = os.getenv('BIRDS_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)


def checking_csv(csv_file):
    example = ['Row #', 'Taxon Order', 'Category', 'Common Name', 'Scientific Name', 'Count', 'Location', 'S/P',
               'Date', 'LocID', 'SubID', 'Exotic', 'Countable']
    with open(csv_file, 'r') as csv_file:
        reader = csv.reader(csv_file)
        first_row = next(reader)
        return first_row == example


def database_filling(message, csv_file):
    user = session.query(User).filter(User.chat_id == message.chat.id).first()
    if not user:
        new_user = User(name=message.chat.first_name, chat_id=message.chat.id)
        session.add(new_user)
        session.commit()
        with open(csv_file, 'r', encoding='UTF-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                common_name = row.get('Common Name')
                scientific_name = row.get('Scientific Name')
                new_bird = Bird(common_name=common_name, scientific_name=scientific_name)
                session.add(new_bird)
                try:
                    session.commit()
                    bird_id = new_bird.id
                except exc.IntegrityError:
                    session.rollback()
                    bird_id = session.query(Bird).filter(Bird.scientific_name == scientific_name).first().id
                userbird = UserBird(user_id=new_user.id, bird_id=bird_id)
                session.add(userbird)
                session.commit()
        bot.send_message(message.chat.id, 'Список птиц создан')
    else:
        with open(csv_file, 'r', encoding='UTF-8') as csv_file:
            reader = csv.DictReader(csv_file)
            identical = True
            new_birds = []
            for row in reader:
                scientific_name = row.get('Scientific Name')
                common_name = row.get('Common Name')
                query = session.query(Bird.common_name,
                                      Bird.scientific_name).join(UserBird).join(User).filter(
                    User.chat_id == message.chat.id).all()
                if (common_name, scientific_name) in query:
                    continue
                else:
                    identical = False
                    new_birds.append(common_name+'\n')
                    new_bird = Bird(common_name=common_name, scientific_name=scientific_name)
                    session.add(new_bird)
                    try:
                        session.commit()
                        bird_id = new_bird.id
                    except exc.IntegrityError:
                        session.rollback()
                        bird_id = session.query(Bird).filter(Bird.scientific_name == scientific_name).first().id
                    new_userbird = UserBird(user_id=user.id, bird_id=bird_id)
                    session.add(new_userbird)
                    session.commit()
        if identical:
            msg = 'Ваш список птиц не изменился'
        else:
            msg = f'Список птиц изменён. Добавлены:\n'
            for x in new_birds:
                msg += x
        bot.send_message(message.chat.id, msg)


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
    csv_file = os.path.join(os.curdir, 'temp', file_name)
    with open(csv_file, 'wb') as file:
        file.write(downloaded_file)
    if not checking_csv(csv_file):
        bot.send_message(message.chat.id, 'Файл не соответствует образцу')
        return
    database_filling(message, csv_file)


bot.infinity_polling()
