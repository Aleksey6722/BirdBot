import telebot
import os
import csv
from sqlalchemy import exc

from models import session, Bird, User, UserBird, Region
TOKEN = os.getenv('BIRDS_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)


def checking_csv(csv_file_dir):
    with open(csv_file_dir, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            scientific_name = row.get('Scientific Name')
            if not scientific_name:
                return False
        return True


def database_filling(message, csv_file):
    user = session.query(User).filter(User.chat_id == message.chat.id).first()
    if not user:
        new_user = User(name=message.chat.first_name, chat_id=message.chat.id)
        session.add(new_user)
        session.commit()
        with open(csv_file, 'r', encoding='UTF-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                scientific_name = row.get('Scientific Name')
                new_bird = Bird(scientific_name=scientific_name)
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
                query = session.query(Bird.scientific_name).join(UserBird).join(User).filter(
                    User.chat_id == message.chat.id).all()
                if (scientific_name,) in query:
                    continue
                else:
                    identical = False
                    new_birds.append(scientific_name+'\n')
                    new_bird = Bird(scientific_name=scientific_name)
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


@bot.message_handler(content_types=['document'])
def get_csv(message):
    file_name = message.document.file_name
    if file_name.split('.')[1] != 'csv':
        bot.send_message(message.chat.id, 'Неверный формат файла. Отправьте файл CSV')
        return
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    csv_file_dir = os.path.join(os.curdir, 'temp', file_name)
    with open(csv_file_dir, 'wb') as file:
        file.write(downloaded_file)
    if not checking_csv(csv_file_dir):
        bot.send_message(message.chat.id, 'Файл не соответствует образцу')
        os.remove(csv_file_dir)
        return
    database_filling(message, csv_file_dir)
    os.remove(csv_file_dir)


@bot.message_handler(commands=['setregion'])
def set_name(message):
    bot.send_message(message.chat.id, 'Введите название района поиска')
    bot.register_next_step_handler(message, callback=name_validate)


def name_validate(message):
    if len(message.text) > 200:
        bot.send_message(message.chat.id, 'Название района должно быть не более 100 символов')
        set_name(message)
        return
    user = session.query(User).filter(User.chat_id == message.chat.id).first()
    if not user:
        user = User(name=message.chat.first_name, chat_id=message.chat.id)
        session.add(user)
        session.commit()
    region = Region(name=message.text, user_id=user.id)
    session.add(region)
    try:
        session.commit()
        get_coords(message, region)
    except exc.IntegrityError:
        session.rollback()
        bot.send_message(message.chat.id, f'Район "{message.text}" уже существует. '
                                          f'Для удаления введите команду /getregions ')


def get_coords(message, region):
    bot.send_message(message.chat.id, 'Введите через точку с запятой координаты центра района поиска (широта; долгота)')
    bot.register_next_step_handler(message, callback=coords_validate, region=region)


def coords_validate(message, region):
    try:
        latitude = message.text.split(';')[0].strip()
        longitude = message.text.split(';')[1].strip()
        latitude = float(latitude)
        longitude = float(longitude)
        region.latitude = latitude
        region.longitude = longitude
        session.add(region)
        session.commit()
        bot.send_message(message.chat.id, 'Введите радиус в метрах')
        bot.register_next_step_handler(message, callback=radius_validate, region=region)
    except:
        bot.send_message(message.chat.id, 'Введены некорректные значения. Попробуйте ещё раз')
        bot.register_next_step_handler(message, callback=coords_validate, region=region)


def radius_validate(message, region):
    try:
        radius = int(message.text)
        region.radius = radius
        session.add(region)
        session.commit()
        bot.send_message(message.chat.id, f'Регион "{region.name}" создан!')
    except:
        bot.send_message(message.chat.id, 'Введены некорректные значения. Попробуйте ещё раз')
        bot.register_next_step_handler(message, callback=radius_validate, region=region)


bot.infinity_polling()
