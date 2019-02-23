import argparse
import csv
import os
import sys
import traceback
from datetime import datetime

import psycopg2
import requests

from scripts.gather_articles_metadata import GatherArticlesMetadata


class DownloadArticles:
    FOLDER_PREFIX = 'data/raw_articles/'

    def __init__(self):
        self.args = self.parse_commandline()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('--id', type=int, default=None, help='Specify id of article to download.')
        parser.add_argument('-p', '--pipeline', action='store_true', default=False, help='Run script in pipeline mode.')
        return parser.parse_args()

    def run(self):
        domain_types = GatherArticlesMetadata._init_domain_types()
        cur = None
        folder_name = '/tmp/'

        if self.args.pipeline:
            input = []
            for line in sys.stdin:
                if line.startswith('OUTPUT:'):
                    print('Downloading article: %s.' % line[:-1], file=sys.stderr)
                    input.append(line)

            result = csv.reader(input)

            articles_metadata = []
            for _, website_domain_name, url, title, publication_date in list(result):
                articles_metadata.append((-1, website_domain_name, url, title, publication_date))
        else:
            cur = self.db_con.cursor()

            current_date = datetime.now()
            folder_name = '%s%s-%02d-%02d_%02d-%02d-%02d' % (
                self.FOLDER_PREFIX,
                current_date.year,
                current_date.month,
                current_date.day,
                current_date.hour,
                current_date.minute,
                current_date.second)

            if not self.args.dry_run:
                if not os.path.isdir(folder_name):
                    os.makedirs(folder_name)

            if self.args.id:
                cur.execute('SELECT a.id, a.website_domain, a.url, a.title, a.publication_date FROM article_metadata a '
                            'WHERE a.id = %s', (self.args.id, ))
            else:
                cur.execute('SELECT a.id, a.website_domain, a.url, a.title, a.publication_date FROM article_metadata a '
                            'LEFT OUTER JOIN article_raw_html r ON r.article_metadata_id = a.id '
                            'WHERE r.article_metadata_id IS NULL')
            articles_metadata = cur.fetchall()
        for index, (id, website_domain_name, url, title, publication_date) in enumerate(articles_metadata):
            filename = '%s_%s.html' % (id, website_domain_name.replace('/', '-'))
            full_path = os.path.join(folder_name, filename)

            try:
                response = requests.get(url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
                })
                for domain_type in domain_types:
                    if domain_type.get_name() == website_domain_name:
                        response.encoding = domain_type.get_encoding()
                        break

                if self.args.dry_run:
                    print(response.text)
                    print(response.encoding)
                    print(full_path)
                elif self.args.pipeline:
                    self._pipeline_out_downloaded_articles(website_domain_name, url, title, publication_date, response.text)
                else:
                    with open(full_path, 'w') as file:
                        file.write(response.text)

                    cur.execute(
                        'INSERT INTO article_raw_html (article_metadata_id, filename) VALUES (%s, %s)',
                        (id, full_path))
                    self.db_con.commit()
                print('(%s/%s) Finished downloading: %s.' % (index + 1, len(articles_metadata), url))
            except Exception as e:
                traceback.print_exc()
                print('(%s/%s) Error downloading: %s with message %s.' % (index + 1, len(articles_metadata), url, e))

        if cur:
            cur.close()
        self._close_db_connection()

    @staticmethod
    def _pipeline_out_downloaded_articles(website_domain, url, title, publication_date, article_raw_html):
        writer = csv.writer(sys.stdout)
        writer.writerow(
               ('OUTPUT:',
                website_domain,
                url,
                title, publication_date))
        print(article_raw_html)
        if not article_raw_html.endswith('</html>'):
            print('</html>')

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    download_articles = DownloadArticles()
    download_articles.run()
