import requests
from bs4 import BeautifulSoup

import re
from datetime import datetime

main_url = "https://kz.birds.watch/"
main_page = requests.get(main_url)

soup = BeautifulSoup(main_page.content, 'lxml')
news_div = soup.find('section', class_='orta').find('a', recursive=False).find_next_sibling()
the_latest_p = news_div.find('p')
date_tag = the_latest_p.find(string=re.compile('^\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]).$'))
today = datetime.today().strftime('%Y-%m-%d')
date_from_page = date_tag.text.strip('.')
link_tags = the_latest_p.find_all('a', href=True)
for tag in link_tags:
    link = tag['href']
    bird_url = main_url+link
    bird_page = requests.get(bird_url)

pass

