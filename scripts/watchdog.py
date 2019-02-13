import argparse

import psycopg2

from scripts.process_articles import ProcessArticles


class DownloadArticles:
    def __init__(self):
        self.args = self.parse_commandline()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--threshold', type=float, default=0.3, help='Specify threshold for warnings.')
        parser.add_argument('--threshold-articles', type=float, default=0.0, help='Specify threshold for warnings for article contents.')
        return parser.parse_args()

    def run(self):
        domain_types = ProcessArticles._init_domain_types()

        cur = self.db_con.cursor()

        print('Checking article gathering summaries for possible errors.')
        cur.execute(
            'SELECT s.website_domain, s.total_articles_count FROM article_metadata_gathering_summary s '
            'WHERE DATE(s.created_at) = (SELECT MAX(DATE(s.created_at)) FROM article_metadata_gathering_summary s);')
        article_metadata_gathering_summaries = cur.fetchall()

        faulty = 0
        for website_domain, total_articles_count in article_metadata_gathering_summaries:
            if total_articles_count == 0:
                faulty += 1
                print('Error: No articles found for domain %s.' % website_domain)
        print('Checked %s domains and found %s possible errors.' % (len(article_metadata_gathering_summaries), faulty))

        print('Checking article processing summaries for possible errors.')
        cur.execute(
            'SELECT website_domain, empty_title_count, empty_author_count, empty_publication_date_count, '
            'empty_perex_count, empty_keywords_count, empty_article_content_count, total_articles_processed_count '
            'FROM article_processing_summary s '
            'WHERE DATE(s.created_at) = (SELECT MAX(DATE(s.created_at)) FROM article_processing_summary s);')
        article_processing_summaries = cur.fetchall()

        for (website_domain, empty_title_count, empty_author_count, empty_publication_date_count, empty_perex_count,
             empty_keywords_count, empty_article_content_count,
             total_articles_processed_count) in article_processing_summaries:
            if website_domain not in domain_types:
                print('Warning: Unknown website_domain %s.' % website_domain)
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
                        print('Warning: %s has %.0f%% %s empty.' % (website_domain, percentage * 100, message_text))

            percentage = float(empty_article_content_count) / float(total_articles_processed_count)
            if percentage > self.args.threshold_articles:
                print('Warning: %s has %.0f%% %s empty.' % (website_domain, percentage * 100, 'articles'))


        cur.close()
        self._close_db_connection()

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    download_articles = DownloadArticles()
    download_articles.run()
