import telebot
from telebot import types
import os
import csv
import schedule
import time

from sqlalchemy import exc
import haversine

from models import session, Bird, User, UserBird, Region
from webparser import parse_birds_website



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
    if len(message.text) > 100:
        bot.send_message(message.chat.id, 'Название района должно быть не более 100 символов')
        set_name(message)
        return
    user = session.query(User).filter(User.chat_id == message.chat.id).first()
    if not user:
        user = User(name=message.chat.first_name, chat_id=message.chat.id)
        session.add(user)
        session.commit()
    region = session.query(Region).filter(Region.name == message.text).filter(Region.user_id == user.id).first()
    if region:
        bot.send_message(message.chat.id, f'Район "{message.text}" уже существует. '
                                          f'Для удаления введите команду /getregions ')
        return
    region = Region(name=message.text, user_id=user.id)
    get_coords(message, region)


def get_coords(message, region):
    bot.send_message(message.chat.id, 'Введите через точку с запятой координаты центра района поиска (широта; долгота)')
    bot.register_next_step_handler(message, callback=coords_validate, region=region)


def coords_validate(message, region):
    try:
        latitude = message.text.split(';')[0].strip()
        longitude = message.text.split(';')[1].strip()
        latitude = float(latitude)
        longitude = float(longitude)
        if not(-90 < latitude < 90):
            raise ValueError
        if not(-180 < longitude < 180):
            raise ValueError
        region.latitude = latitude
        region.longitude = longitude
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


@bot.message_handler(commands=['getregions'])
def get_region(message):
    user = session.query(User).filter(User.chat_id == message.chat.id).first()
    regions = session.query(Region).join(User).filter(Region.user_id == user.id).all()
    if len(regions) != 0:
        for region in regions:
            markup = types.InlineKeyboardMarkup()
            msg = f'Район "{region.name}"'
            del_btn = types.InlineKeyboardButton('Удалить', callback_data='del,'+str(region.user_id)+','+
                                                                          str(region.name))
            markup.add(del_btn)
            bot.send_message(message.chat.id, msg)
            bot.send_location(message.chat.id, region.latitude, region.longitude, horizontal_accuracy=1500,
                              reply_markup=markup)

    else:
        bot.send_message(message.chat.id, 'У Вас нет ни одного района для отслеживания. Введите команду'
                                          '/setregion для создания.')


@bot.callback_query_handler(func=lambda callback: callback.data.split(',')[0] == 'del')
def delete_region(callback):
    user_id = callback.data.split(',')[1]
    region_name = callback.data.split(',')[2]
    session.query(Region).filter(Region.user_id == user_id).filter(Region.name == region_name).delete()
    session.commit()
    bot.send_message(callback.message.chat.id, 'Уведомление удалено!')


def sending_notice():
    count_sended = 0
    regions = session.query(Region).all()
    if not regions:
        return
    parsing_result = parse_birds_website()
    for region in regions:
        birds_in_region = []
        for bird in parsing_result:
            bird_point = float(bird.get('latitude')), float(bird.get('longitude'))
            region_point = float(region.latitude),  float(region.longitude)
            dist = haversine.haversine(bird_point, region_point)*1000
            if dist <= region.radius:
                birds_in_region.append(bird)
        if len(birds_in_region) != 0:
            users_list = session.query(Bird.scientific_name).join(UserBird).filter(
                UserBird.user_id == region.user_id).all()
            names_of_userbirds = [bird[0] for bird in users_list]
            filtered_list = list(filter(lambda x: x.get('scientific_name') not in names_of_userbirds, birds_in_region))
            if len(filtered_list) != 0:
                user = session.query(User).filter(User.id == region.user_id).first()
                bot.send_message(user.chat_id, f'В районе "{region.name}" замечены птицы:\n\n')
                count_sended += 1
                for bird in filtered_list:
                    msg = bird.get('scientific_name')+'\n'+bird.get('url')+'\n\n'
                    if count_sended % 50 == 0:
                        time.sleep(1)
                    bot.send_message(user.chat_id, msg)
                    count_sended += 1



sending_notice()
# schedule.every(1).minute.do(bot.send_message(message.chat.id, str(parse_birds_website())))
bot.infinity_polling()
