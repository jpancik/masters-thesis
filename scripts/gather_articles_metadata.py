import argparse
import json
from concurrent.futures import TimeoutError

import psycopg2
from pebble import ProcessPool

from lib.articles_url_gatherer_domain_types.json_domain_type import JsonDomainType
from lib.articles_url_retrievers.regex_parser import RegexParser
from lib.articles_url_retrievers.rss_parser import RssParser


class GatherArticlesMetadata:
    def __init__(self):
        self.args = self.parse_commandline()
        self.domain_types = self._init_domain_types()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--domain', type=str, default=None, help='Only gather article urls for specified domain.')
        parser.add_argument('--processes', type=int, default=16, help='Specify number of processes for the pool.')
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Doesn\'t store results into DB and instead it prints them to stdout.')
        return parser.parse_args()

    def run(self):
        with ProcessPool(max_workers=self.args.processes) as pool:
            domain_types_to_process = []
            for domain_type in self.domain_types:
                if self.args.domain and domain_type.get_name() != self.args.domain:
                    continue

                domain_types_to_process.append(domain_type)

            future = pool.map(self._gather_articles_metadata, domain_types_to_process, timeout=180)

            iterator = future.result()
            while True:
                try:
                    domain_type, articles_metadata = next(iterator)

                    if self.args.dry_run:
                        import pprint
                        pprint.pprint(articles_metadata)
                        uploaded_count = 0
                    else:
                        uploaded_count = self._upload_articles(domain_type, articles_metadata)

                    print('%s: Number of articles uploaded/retrieved: %s/%s.'
                          % (domain_type.get_name(), uploaded_count, len(articles_metadata)))
                except StopIteration:
                    break
                except TimeoutError as error:
                    print("Function took longer than %d seconds." % error.args[1])

        self._close_db_connection()

    @staticmethod
    def _gather_articles_metadata(domain_type):
        print('Gathering for: %s' % domain_type.get_name())

        if domain_type.has_rss():
            articles_metadata = RssParser.get_article_metadata(domain_type)
        elif domain_type.use_regex_parser_for_article_urls():
            articles_metadata = RegexParser.get_article_metadata(domain_type)
        else:
            articles_metadata = domain_type.get_article_metadata()

        return domain_type, articles_metadata


    def _upload_articles(self, domain_type, articles_metadata):
        cur = self.db_con.cursor()

        uploaded_count = 0

        for metadata in articles_metadata:
            cur.execute('SELECT COUNT(*) FROM article_metadata a WHERE a.url = %s', (metadata['link'],))

            if cur.fetchone()[0] == 0:
                uploaded_count += 1

                cur.execute(
                    'INSERT INTO article_metadata (website_domain, url, title, publication_date) VALUES (%s, %s, %s, %s)',
                    (domain_type.get_name(),
                     metadata['link'],
                     metadata['title'] if 'title' in metadata else None,
                     metadata['published_parsed'] if 'published_parsed' in metadata else None))

        cur.execute(
            'INSERT INTO article_metadata_gathering_summary (website_domain, total_articles_count, new_articles_count) VALUES (%s, %s, %s)',
            (domain_type.get_name(), len(articles_metadata), uploaded_count)
        )

        self.db_con.commit()
        cur.close()
        return uploaded_count

    @staticmethod
    def _init_domain_types():
        out = []

        with open('data/website_article_urls_descriptions.json', 'r') as file:
            json_data = json.load(file)
            out += JsonDomainType.get_json_domain_types(json_data)

        return out

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    gather_articles_metadata = GatherArticlesMetadata()
    gather_articles_metadata.run()
