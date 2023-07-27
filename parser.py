import requests
from bs4 import BeautifulSoup
import json

import re
from datetime import datetime

main_url = "https://kz.birds.watch/"
headers = {"Accept-Language": "ru"}
main_page = requests.get(main_url, headers=headers)



def get_bird_info(bird_page):
    soup = BeautifulSoup(bird_page.content, 'lxml')
    h1 = soup.find('h1')
    latin_name = h1.find_next_sibling().text.split('(')[0].strip()
    location_script = soup.find_all('script')[14].text
    coords = location_script.partition('setView([')[2].partition(']')[0]
    latitude = coords.split(',')[0]
    longitude = coords.split(',')[1]
    return {
            'scientific_name': latin_name,
            'latitude': latitude,
            'longitude': longitude
            }


soup = BeautifulSoup(main_page.content, 'lxml')
news_div = soup.find('section', class_='orta').find('a', recursive=False).find_next_sibling()
the_latest_p = news_div.find('p')
date_tag = the_latest_p.find(string=re.compile('^\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]).$'))
today = datetime.today().strftime('%Y-%m-%d')
date_from_page = date_tag.text.strip('.')
link_tags = the_latest_p.find_all('a', href=True)
result = []
for tag in link_tags:
    link = tag['href']
    rus_name = tag.text
    bird_url = main_url+link
    bird_page = requests.get(bird_url, headers=headers)
    info = get_bird_info(bird_page)
    result.append({'common_name': rus_name,
                   'scientific_name': info.get('scientific_name'),
                   'latitude': info.get('latitude'),
                   'longitude': info.get('longitude'),
                   'url': bird_url})
d=result
pass

