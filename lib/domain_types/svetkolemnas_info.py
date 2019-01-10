import re

import requests
from bs4 import BeautifulSoup

from lib.domain_types.domain_type import DomainType


class SvetkolemnasInfo(DomainType):
    def has_rss(self):
        return False

    def get_article_urls(self):
        possible_sources = []

        possible_sources.append('http://www.svetkolemnas.info/')

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

        article_regex = re.compile(r'^/novinky/')

        article_urls = []
        for url in possible_articles:
            match = article_regex.match(url)
            if match:
                article_urls.append({
                    'link': 'http://www.svetkolemnas.info%s' % url
                })

        return article_urls
