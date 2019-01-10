import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from lib.domain_types.domain_type import DomainType


class WithformCz(DomainType):
    def has_rss(self):
        return False

    def get_article_urls(self):
        possible_sources = []

        for i in range(15):
            possible_sources.append('http://www.withform.cz/page/%s/' % i)

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

        article_regex = re.compile(r'^http://www\.withform.cz/(\d{4})/(\d{2})/(\d{2})/[^/]*/$')

        article_urls = []
        for url in possible_articles:
            match = article_regex.match(url)
            if match:
                year, month, day = match.group(1), match.group(2), match.group(3)
                date = datetime.strptime('%s %s %s' % (year, month, day), '%Y %m %d')

                article_urls.append({
                    'link': url,
                    'published_parsed': date
                })

        return article_urls
