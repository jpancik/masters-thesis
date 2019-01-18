import argparse
import json
import os
import re
import traceback
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

        cur.execute('SELECT a.id, a.website_domain, a.url, a.title, a.publication_date, r.filename '
                    'FROM article_metadata a '
                    'JOIN article_raw_html r ON r.article_metadata_id = a.id '
                    'WHERE a.website_domain = \'www.svetkolemnas.info\' LIMIT 10 OFFSET 0')
                    #'WHERE a.website_domain = \'www.vlasteneckenoviny.cz\' LIMIT 10 OFFSET 0')
                    #'WHERE a.website_domain = \'www.zvedavec.org\' LIMIT 10 OFFSET 0')
                    #'WHERE a.website_domain = \'nwoo.org\' LIMIT 10 OFFSET 0')
                    #'WHERE a.website_domain = \'parlamentnilisty.cz\' LIMIT 10 OFFSET 0')
        articles_raw_data = cur.fetchall()
        for index, (id, website_domain, url, title, publication_date, filename) in enumerate(articles_raw_data):
            print('(%s/%s) Started processing: %s from %s.' % (index + 1, len(articles_raw_data), filename, url))
            if website_domain not in self.domain_types:
                print('(%s/%s) Unsupported website domain: %s for article with id %s.'
                      % (index + 1, len(articles_raw_data), website_domain, id))
                continue
            domain_type = self.domain_types[website_domain]

            try:
                with open(filename, 'r') as file:
                    html_extractor = HtmlExtractor(domain_type, file, self.args.debug)

                    out = {
                        'title': html_extractor.get_title(),
                        'author': html_extractor.get_author(),
                        'publication_date': str(html_extractor.get_date()),
                        'prerex': html_extractor.get_prerex(),
                        'keywords': html_extractor.get_keywords(),
                        'article_content': html_extractor.get_article_content()
                    }

                    print(json.dumps(out, indent=4, ensure_ascii=False))

                print('(%s/%s) Finished processing: %s from %s.' % (index + 1, len(articles_raw_data), filename, url))
            except Exception as e:
                print('(%s/%s) Error processing %s from %s with message: %s.'
                      % (index + 1, len(articles_raw_data), filename, url, e))
                traceback.print_exc()

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
