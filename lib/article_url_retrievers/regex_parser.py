import re
import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from lib.domain_types.domain_type import DomainType


class RegexParserArgs:
    def __init__(self,
                 possible_sources: [str],
                 regex: str,
                 domain_prefix: str = None,
                 parse_date: bool = False):
        self.possible_sources = possible_sources
        self.regex = regex
        self.domain_prefix = domain_prefix
        self.parse_date = parse_date


class RegexParser:
    @staticmethod
    def get_article_urls(domain_type: DomainType):
        if not domain_type.use_regex_parser_for_article_urls():
            raise AssertionError('Domain type should not use regex parser.')

        regex_parser_args = domain_type.get_regex_parser_args()

        possible_articles = set()

        for url in regex_parser_args.possible_sources:
            response = requests.get(url)

            if response.status_code == 200:
                content = response.text
                soup = BeautifulSoup(content, 'html.parser')

                for link in soup.find_all('a'):
                    possible_articles.add(link.get('href'))

        article_regex = re.compile(regex_parser_args.regex)

        article_urls = []
        for url in possible_articles:
            if url:
                match = article_regex.match(url)
                if match:
                    article_url = dict()

                    if regex_parser_args.domain_prefix:
                        article_url['link'] = urllib.parse.urljoin(regex_parser_args.domain_prefix, url)
                    else:
                        article_url['link'] = url

                    if regex_parser_args.parse_date:
                        year, month, day = match.group(1), match.group(2), match.group(3)
                        date = datetime.strptime('%s %s %s' % (year, month, day), '%Y %m %d')
                        article_url['published_parsed'] = date

                    article_urls.append(article_url)

        return article_urls
