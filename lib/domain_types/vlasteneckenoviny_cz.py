import re

import requests
from bs4 import BeautifulSoup

from lib.domain_types.domain_type import DomainType


class VlasteneckenovinyCz(DomainType):
    def has_rss(self):
        return False

    def get_article_urls(self):
        possible_sources = []

        for i in range(30):
            possible_sources.append('http://www.vlasteneckenoviny.cz/?paged=%s' % i)

        possible_articles = set()

        for url in possible_sources:
            response = requests.get(url)

            if response.status_code == 200:
                content = response.text
                soup = BeautifulSoup(content, 'html.parser')

                for link in soup.find_all('a'):
                    possible_articles.add(link.get('href'))
            else:
                pass

        article_regex = re.compile(r'^http://www\.vlasteneckenoviny\.cz/\?p=\d+$')

        article_urls = []
        for url in possible_articles:
            match = article_regex.match(url)
            if match:
                article_urls.append({
                    'link': url
                })

        return article_urls
