import requests
from bs4 import BeautifulSoup

url = "https://kz.birds.watch/"
main_page = requests.get(url)

soup = BeautifulSoup(main_page.text, 'lxml')
# box = soup.find('b', string="what's new?")
box = soup.find('section', class_='orta').find('a', recursive=False).previous_sibling
print(box)
pass
