import argparse
import json
import os
import re
from datetime import datetime

import psycopg2
import requests
from bs4 import BeautifulSoup

from lib.article_data_extractors.html_extractor import HtmlExtractor
from lib.articles_processor_domain_type.json_domain_type import JsonDomainType


class ProcessArticles:
    FOLDER_PREFIX = 'data/raw_articles/'

    def __init__(self):
        self.args = self.parse_commandline()
        self.domain_types = self._init_domain_types()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--debug', action='store_true', default=False, help='Debug HTML parsing.')
        return parser.parse_args()

    def run(self):
        with open('data/website_article_format_descriptions.json', 'r') as file:
            json_data = json.load(file)
            self.domain_types.update(JsonDomainType.get_json_domain_types(json_data))

        cur = self.db_con.cursor()

        cur.execute('SELECT a.id, a.website_domain, a.title, a.publication_date, r.filename FROM article_metadata a '
                    'JOIN article_raw_html r ON r.article_metadata_id = a.id '
                    'WHERE a.website_domain = \'parlamentnilisty.cz\' LIMIT 5 OFFSET 0')
        articles_raw_data = cur.fetchall()
        for index, (id, website_domain, title, publication_date, filename) in enumerate(articles_raw_data):
            if website_domain not in self.domain_types:
                print('(%s/%s) Unsupported website domain: %s for article with id %s.'
                      % (index + 1, len(articles_raw_data), website_domain, id))
                continue
            domain_type = self.domain_types[website_domain]

            try:
                with open(filename, 'r') as file:
                    html_extractor = HtmlExtractor(domain_type, file, self.args.debug)
                    # print(html_extractor.get_title())
                    # print(html_extractor.get_author())
                    # print(html_extractor.get_date())
                    # print(html_extractor.get_prerex())
                    # print(html_extractor.get_keywords())
                    print(html_extractor.get_article())

                    # soup = BeautifulSoup(file, 'html.parser')
                    #
                    # # title = soup.select('article.detail section.article-header h1')
                    # # print(title)
                    # #
                    # # author = soup.select('#main article section section.section-inarticle')
                    # # print(author)
                    #
                    # article = soup.select('#main div:nth-child(2) div div article section.article-content')
                    # #print(article)
                    #
                    # selected = ''.join([str(a) for a in article])
                    # # print(selected)
                    # article_soup = BeautifulSoup(selected, 'html.parser')
                    # #print(article_soup)
                    # [x.extract() for x in article_soup.select('div.related-article')]
                    # [x.extract() for x in article_soup.select('a')]
                    # [x.extract() for x in article_soup.select('script')]
                    # [x.extract() for x in article_soup.select('div.well')]
                    # [x.extract() for x in article_soup.select('h2')]
                    # [x.extract() for x in article_soup.select('div.poll-percent')]
                    # # print(article_soup)
                    #
                    # text = article_soup.get_text()
                    # # print(text)
                    # text_no_tabs_and_new_lines = text.replace('\n', ' ').replace('\t', ' ').replace(str(chr(160)), ' ')
                    # remove_spaces_regex = re.compile(r'([ ][ ]+)', flags=re.MULTILINE)
                    # text_processed = remove_spaces_regex.sub(' ', text_no_tabs_and_new_lines)
                    # print(text_processed)


                print('(%s/%s) Finished processing: %s.' % (index + 1, len(articles_raw_data), filename))
            except Exception as e:
                print('(%s/%s) Error processing %s with message: %s.' % (index + 1, len(articles_raw_data), filename, e))

        cur.close()
        self._close_db_connection()

    def _init_domain_types(self):
        return dict()

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    process_articles = ProcessArticles()
    process_articles.run()
