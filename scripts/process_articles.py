import argparse
import os
import re
from datetime import datetime

import psycopg2
import requests
from bs4 import BeautifulSoup


class ProcessArticles:
    FOLDER_PREFIX = 'data/raw_articles/'

    def __init__(self):
        self.args = self.parse_commandline()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--debug', action='store_true', default=False, help='Debug HTML parsing.')
        return parser.parse_args()

    def run(self):
        cur = self.db_con.cursor()

        cur.execute('SELECT a.id, a.website_domain, a.title, a.publication_date, r.filename FROM article_metadata a '
                    'JOIN article_raw_html r ON r.article_metadata_id = a.id '
                    'WHERE a.website_domain = \'parlamentnilisty.cz\'')
        articles_raw_data = cur.fetchall()
        for index, (id, website_domain, title, publication_date, filename) in enumerate(articles_raw_data):
            try:
                with open(filename, 'r') as file:
                    soup = BeautifulSoup(file, 'html.parser')

                    # title = soup.select('article.detail section.article-header h1')
                    # print(title)
                    #
                    # author = soup.select('#main article section section.section-inarticle')
                    # print(author)

                    article = soup.select('#main div:nth-child(2) div div article section.article-content')
                    #print(article)

                    selected = ''.join([str(a) for a in article])
                    # print(selected)
                    article_soup = BeautifulSoup(selected, 'html.parser')
                    #print(article_soup)
                    [x.extract() for x in article_soup.select('div.related-article')]
                    [x.extract() for x in article_soup.select('a')]
                    [x.extract() for x in article_soup.select('script')]
                    [x.extract() for x in article_soup.select('div.well')]
                    [x.extract() for x in article_soup.select('h2')]
                    [x.extract() for x in article_soup.select('div.poll-percent')]
                    # print(article_soup)

                    text = article_soup.get_text()
                    # print(text)
                    text_no_tabs_and_new_lines = text.replace('\n', ' ').replace('\t', ' ').replace(str(chr(160)), ' ')
                    remove_spaces_regex = re.compile(r'([ ][ ]+)', flags=re.MULTILINE)
                    text_processed = remove_spaces_regex.sub(' ', text_no_tabs_and_new_lines)
                    print(text_processed)


                print('(%s/%s) Finished processing: %s.' % (index + 1, len(articles_raw_data), filename))
            except Exception as e:
                print('(%s/%s) Error processing %s with message: %s.' % (index + 1, len(articles_raw_data), filename, e))

        cur.close()
        self._close_db_connection()

    @staticmethod
    def clean_scripts_styles(raw_html):
        cleaned_html_scripts = re.sub(r'<script((?!</script>).|\n)*</script>', '', raw_html)
        cleaned_html_styles = re.sub(r'<style((?!</style>).|\n)*</style>', '', cleaned_html_scripts)
        return cleaned_html_styles

    @staticmethod
    def clean_html_from_tags(raw_html):
        cleaned_tags = re.sub(r'<.*?>', ' ', ProcessArticles.clean_scripts_styles(raw_html))
        return re.sub(r'&nbsp;', ' ', cleaned_tags)

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    process_articles = ProcessArticles()
    process_articles.run()
