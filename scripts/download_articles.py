import argparse
import csv
import os
import sys
import traceback
from datetime import datetime

import requests
from pebble import ProcessPool

from lib import webtrack_logger
from lib.crawler_db import connector
from lib.webtrack_logger import log
from scripts.gather_articles_metadata import GatherArticlesMetadata


class DownloadArticles:
    FOLDER_PREFIX = 'data/raw_articles/'

    def __init__(self):
        self.args = self.parse_commandline()
        webtrack_logger.setup_logging()
        self.db_con = connector.get_db_connection()

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('--id', type=int, default=None, help='Specify id of article to download.')
        parser.add_argument('--domain', type=str, default=None, help='Specify domain of articles to download.')
        parser.add_argument('-p', '--pipeline', action='store_true', default=False, help='Run script in pipeline mode.')
        parser.add_argument('--processes', type=int, default=16, help='Specify number of processes for the pool.')
        parser.add_argument('--config', type=str, default='files/website_article_urls_descriptions.json', help='Specify path to the articles urls JSON configuration file.')
        return parser.parse_args()

    def run(self):
        domain_types = GatherArticlesMetadata._init_domain_types(self.args.config)
        cur = None
        folder_name = '/tmp/'

        if self.args.pipeline:
            input = []
            for line in sys.stdin:
                if line.startswith('OUTPUT:'):
                    log.info('Downloading article: %s.' % line[:-1])
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
                cur.execute('SELECT a.id, a.website_domain, a.url, a.title, a.publication_date, r.filename '
                            'FROM article_metadata a '
                            'LEFT JOIN article_raw_html r ON r.article_metadata_id = a.id '
                            'WHERE a.id = %s', (self.args.id, ))
            elif self.args.domain:
                cur.execute('SELECT a.id, a.website_domain, a.url, a.title, a.publication_date, r.filename '
                            'FROM article_metadata a '
                            'LEFT JOIN article_raw_html r ON r.article_metadata_id = a.id '
                            'WHERE a.website_domain = %s', (self.args.domain,))
            else:
                cur.execute('SELECT a.id, a.website_domain, a.url, a.title, a.publication_date, r.filename '
                            'FROM article_metadata a '
                            'LEFT OUTER JOIN article_raw_html r ON r.article_metadata_id = a.id '
                            'WHERE r.article_metadata_id IS NULL')
            articles_metadata = cur.fetchall()

        input_data = []
        for index, article_metadata in enumerate(articles_metadata):
            id, website_domain_name, url, title, publication_date, stored_path = article_metadata

            if not stored_path:
                filename = '%s_%s.html' % (id, website_domain_name.replace('/', '-'))
                full_path = os.path.join(folder_name, filename)
            else:
                full_path = stored_path

            input_data.append((index + 1, len(articles_metadata), full_path, domain_types, article_metadata))

        with ProcessPool(max_workers=self.args.processes) as pool:
            future = pool.map(self._download_article, input_data, timeout=180)

            iterator = future.result()
            while True:
                try:
                    index, total_count, file_path, metadata, response = next(iterator)
                    if file_path is None or metadata is None or response is None:
                        continue

                    id, website_domain_name, url, title, publication_date, stored_path = metadata

                    if self.args.dry_run:
                        print(response.text)
                        print(response.encoding)
                        print(file_path)
                    elif self.args.pipeline:
                        self._pipeline_out_downloaded_articles(website_domain_name, url, title, publication_date,
                                                               response.text)
                    else:
                        with open(file_path, 'w') as file:
                            file.write(response.text)

                        if not stored_path:
                            cur.execute(
                                'INSERT INTO article_raw_html (article_metadata_id, filename) VALUES (%s, %s)',
                                (id, file_path))
                            self.db_con.commit()
                        log.info('(%s/%s) Stored response in %s.' % (index, total_count, file_path))
                except StopIteration:
                    break
                except TimeoutError as error:
                    log.info('Function took longer than 180 seconds.')

        if cur:
            cur.close()
        self._close_db_connection()

    @staticmethod
    def _download_article(input_data):
        index, total_count, file_path, domain_types, article_metadata = input_data
        id, website_domain_name, url, title, publication_date, stored_path = article_metadata

        try:
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
            })

            for domain_type in domain_types:
                if domain_type.get_name() == website_domain_name and domain_type.get_encoding():
                    response.encoding = domain_type.get_encoding()
                    break

            log.info('(%s/%s) Finished downloading: %s.' % (index, total_count, url))
            return index, total_count, file_path, article_metadata, response
        except Exception as e:
            traceback.print_exc()
            log.info('(%s/%s) Error downloading: %s with message %s.' % (index, total_count, url, e))
            return None, None, None, None, None

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
