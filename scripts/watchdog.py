import argparse
import json
import sys

from lib import webtrack_logger
from lib.crawler_db import connector
from lib.webtrack_logger import log
from scripts.process_articles import ProcessArticles


class Watchdog:
    WATCHDOG_OUTPUT_FILE_PATH = 'data/watchdog_output.json'

    def __init__(self):
        self.args = self.parse_commandline()
        webtrack_logger.setup_logging()
        self.db_con = connector.get_db_connection()

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--threshold', type=float, default=0.3, help='Specify threshold for warnings.')
        parser.add_argument('--threshold-articles', type=float, default=0.0, help='Specify threshold for warnings for article contents.')
        parser.add_argument('--config', type=str, default='files/website_article_format_descriptions.json', help='Specify path to the articles format JSON configuration file.')
        return parser.parse_args()

    def run(self):
        domain_types = ProcessArticles._init_domain_types(self.args.config)

        cur = self.db_con.cursor()

        log.info('Checking article gathering summaries for possible errors.')
        cur.execute(
            'SELECT s.website_domain, s.total_articles_count, s.created_at FROM article_metadata_gathering_summary s '
            'WHERE DATE(s.created_at) = (SELECT MAX(DATE(s.created_at)) FROM article_metadata_gathering_summary s);')
        article_metadata_gathering_summaries = cur.fetchall()

        no_articles_found = []
        faulty = 0
        for website_domain, total_articles_count, created_at in article_metadata_gathering_summaries:
            if total_articles_count == 0:
                faulty += 1
                log.warning('No articles found for domain %s.' % website_domain)
                no_articles_found.append({
                    'created_at': str(created_at),
                    'website_domain': website_domain
                })
        log.info(
            'Checked %s domains and found %s possible errors.' % (len(article_metadata_gathering_summaries), faulty))

        log.info('Checking article processing summaries for possible errors.')
        cur.execute(
            'SELECT website_domain, empty_title_count, empty_author_count, empty_publication_date_count, '
            'empty_perex_count, empty_keywords_count, empty_article_content_count, total_articles_processed_count, created_at '
            'FROM article_processing_summary s '
            'WHERE DATE(s.created_at) = (SELECT MAX(DATE(s.created_at)) FROM article_processing_summary s);')
        article_processing_summaries = cur.fetchall()

        processing_problems = []
        for (website_domain, empty_title_count, empty_author_count, empty_publication_date_count, empty_perex_count,
             empty_keywords_count, empty_article_content_count,
             total_articles_processed_count, created_at) in article_processing_summaries:
            if website_domain not in domain_types:
                log.warning('Unknown website_domain %s.' % website_domain)
                continue

            domain = domain_types[website_domain]
            check_tuples = [
                ('title', empty_title_count, 'titles'),
                ('author', empty_author_count, 'authors'),
                ('date', empty_publication_date_count, 'dates'),
                ('perex', empty_perex_count, 'perexes'),
                ('keywords', empty_keywords_count, 'keywords'),
            ]

            for name, empty_count, message_text in check_tuples:
                if domain.get_attribute_selector_info(name):
                    percentage = float(empty_count) / float(total_articles_processed_count)
                    if percentage > self.args.threshold:
                        log.warning('%s has %.0f%% of %s empty.' % (website_domain, percentage * 100, message_text))
                        processing_problems.append({
                            'created_at': str(created_at),
                            'website_domain': website_domain,
                            'text': '%.0f%% of %s empty.' % (percentage * 100, message_text)
                        })

            percentage = float(empty_article_content_count) / float(total_articles_processed_count)
            if percentage > self.args.threshold_articles:
                log.warning('Warning: %s has %.0f%% of %s empty.' % (website_domain, percentage * 100, 'articles'))
                processing_problems.append({
                    'created_at': str(created_at),
                    'website_domain': website_domain,
                    'text': '%.0f%% of articles empty.' % (percentage * 100)
                })

        cur.execute('SELECT DATE(a.created_at), COUNT(*) FROM article_metadata a '
                    'GROUP BY DATE(a.created_at) '
                    'ORDER BY DATE(a.created_at) DESC LIMIT 10;')
        articles_count_per_day = []
        for date, count in cur.fetchall():
            articles_count_per_day.append({
                'date': str(date),
                'count': count
            })

        cur.execute('SELECT a.website_domain, COUNT(*) FROM article_metadata a '
                    'GROUP BY a.website_domain;')
        website_domains_article_counts = dict()
        for website_domain, count in cur.fetchall():
            website_domains_article_counts[website_domain] = count

        cur.execute('SELECT MIN(a.created_at) FROM article_metadata_gathering_summary a;')
        gathering_started_at = cur.fetchone()

        cur.close()
        self._close_db_connection()

        no_articles_found.sort(key=lambda x: x['website_domain'])
        processing_problems.sort(key=lambda x: x['website_domain'])
        with open(self.WATCHDOG_OUTPUT_FILE_PATH, 'w') as file:
            file.write(json.dumps({
                'no_articles_found': no_articles_found,
                'processing_problems': processing_problems,
                'articles_count_per_day': articles_count_per_day,
                'website_domains_article_counts': website_domains_article_counts,
                'gathering_started_at': str(gathering_started_at[0].strftime('%B %-d, %Y'))
            }, indent=4, ensure_ascii=False))

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    watchdog = Watchdog()
    watchdog.run()
