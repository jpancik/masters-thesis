import argparse
import csv
import json
import sys
from concurrent.futures import TimeoutError

from pebble import ProcessPool

from lib.articles_url_gatherer_domain_types.json_domain_type import JsonDomainType
from lib.articles_url_retrievers.regex_parser import RegexParser
from lib.articles_url_retrievers.rss_parser import RssParser
from lib.crawler_db import connector


class GatherArticlesMetadata:
    def __init__(self):
        self.args = self.parse_commandline()
        self.domain_types = self._init_domain_types(self.args.config)

        self.db_con = connector.get_db_connection()


    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--domain', type=str, default=None, help='Only gather article urls for specified domain.')
        parser.add_argument('--processes', type=int, default=16, help='Specify number of processes for the pool.')
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Doesn\'t store results into DB and instead it prints them to stdout.')
        parser.add_argument('-p', '--pipeline', action='store_true', default=False, help='Run script in pipeline mode.')
        parser.add_argument('--config', type=str, default='files/website_article_urls_descriptions.json', help='Specify path to the articles urls JSON configuration file.')
        return parser.parse_args()

    def run(self):
        allowed_domains = None
        if self.args.domain:
            allowed_domains = [self.args.domain]
        if self.args.pipeline:
            allowed_domains = []
            for line in sys.stdin:
                allowed_domains.append(line[:-1])
            print('Gathering article metadata for domains %s.' % allowed_domains, file=sys.stderr)

        domain_types_to_process = []
        for domain_type in self.domain_types:
            if allowed_domains is not None and domain_type.get_name() not in allowed_domains:
                continue

            domain_types_to_process.append(domain_type)

        with ProcessPool(max_workers=self.args.processes) as pool:
            future = pool.map(self._gather_articles_metadata, domain_types_to_process, timeout=180)

            iterator = future.result()
            while True:
                try:
                    domain_type, articles_metadata = next(iterator)

                    if self.args.dry_run:
                        import pprint
                        pprint.pprint(articles_metadata)
                        uploaded_count = 0
                    elif self.args.pipeline:
                        self._pipeline_out_articles(domain_type, articles_metadata)
                        uploaded_count = 0
                    else:
                        uploaded_count = self._upload_articles(domain_type, articles_metadata)

                    print('%s: Number of articles uploaded/retrieved: %s/%s.'
                          % (domain_type.get_name(), uploaded_count, len(articles_metadata)), file=sys.stderr)
                except StopIteration:
                    break
                except TimeoutError as error:
                    print('Function took longer than 180 seconds.', file=sys.stderr)

        self._close_db_connection()

    @staticmethod
    def _gather_articles_metadata(domain_type):
        print('Gathering for: %s' % domain_type.get_name(), file=sys.stderr)

        if domain_type.has_rss():
            articles_metadata = RssParser.get_article_metadata(domain_type)
        elif domain_type.use_regex_parser_for_article_urls():
            articles_metadata = RegexParser.get_article_metadata(domain_type)
        else:
            articles_metadata = domain_type.get_article_metadata()

        return domain_type, articles_metadata

    @staticmethod
    def _pipeline_out_articles(domain_type, articles_metadata):
        writer = csv.writer(sys.stdout)
        for metadata in articles_metadata:
            writer.writerow(
                   ('OUTPUT:',
                    domain_type.get_name(),
                    metadata['link'],
                    metadata['title'] if 'title' in metadata else None,
                    metadata['published_parsed'] if 'published_parsed' in metadata else None))

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
    def _init_domain_types(path_to_config):
        out = []

        with open(path_to_config, 'r') as file:
            json_data = json.load(file)
            out += JsonDomainType.get_json_domain_types(json_data)

        return out

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    gather_articles_metadata = GatherArticlesMetadata()
    gather_articles_metadata.run()
