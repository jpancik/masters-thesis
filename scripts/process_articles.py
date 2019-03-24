import argparse
import csv
import json
import os
import sys
import traceback
from datetime import datetime

from lib.article_data_extractors.html_extractor import HtmlExtractor
from lib.articles_processor_domain_type.articles_processor_domain_type import DomainType
from lib.articles_processor_domain_type.json_domain_type import JsonDomainType
from lib.crawler_db import connector
from scripts.download_articles import DownloadArticles


class ProcessArticles:
    RAW_HTML_FOLDER_PREFIX = DownloadArticles.FOLDER_PREFIX
    PROCESSED_HTML_FOLDER_PREFIX = 'data/processed_articles/'

    def __init__(self):
        self.args = self.parse_commandline()
        self.domain_types = self._init_domain_types(self.args.config)
        self.db_con = connector.get_db_connection()

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--debug', action='store_true', default=False, help='Debug HTML parsing.')
        parser.add_argument('--domain', type=str, default=None, help='Specify domain to gather.')
        parser.add_argument('--limit', type=int, default=None, help='Specify limit of how many articles to process per domain.')
        parser.add_argument('--sql-conditions', type=str, default=None, help='Specify custom SQL conditions. (a is article_metadata and r is article_raw_html, e.g. "AND a.id = 15")')
        parser.add_argument('--dry-run', action='store_true', default=False, help='Don\'t store output and print it to stdout.')
        parser.add_argument('--manual', action='store_true', default=False, help='Process articles manually.')
        parser.add_argument('--begin-id', type=int, default=None, help='Specify begin id of articles to process.')
        parser.add_argument('--end-id', type=int, default=None, help='Specify end if of articles to process.')
        parser.add_argument('--skip-hyperlinks', action='store_true', default=False, help='Don\'t gather all hyperlinks from article.')
        parser.add_argument('-p', '--pipeline', action='store_true', default=False, help='Run script in pipeline mode.')
        parser.add_argument('--config', type=str, default='files/website_article_format_descriptions.json', help='Specify path to the articles format JSON configuration file.')
        return parser.parse_args()

    def run(self):
        cur = self.db_con.cursor()

        if self.args.pipeline:
            input_articles_data = []
            capturing_article = False
            current_article_metadata = None
            current_article_html = []

            for line in sys.stdin:
                if capturing_article:
                    current_article_html.append(line)
                    if line.endswith('</html>\n'):
                        print('Captured article: %s with %s lines'
                              % (current_article_metadata, len(current_article_html)), file=sys.stderr)
                        input_articles_data.append((current_article_metadata, ''.join(current_article_html)))

                        capturing_article = False
                        current_article_metadata = None
                        current_article_html = []
                else:
                    if line.startswith('OUTPUT:'):
                        capturing_article = True
                        current_article_metadata = list(csv.reader([line]))[0]

            for ((_, website_domain_name, url, title, publication_date), article_raw_html) in input_articles_data:
                to_process = [
                    ((-1, url, title, publication_date, datetime.now()), article_raw_html)
                ]

                domain_type = self.domain_types[website_domain_name]
                if not domain_type:
                    continue

                (processed_articles,
                 processed_articles_count,
                 processed_articles_last_id,
                 empty_title_count,
                 empty_author_count,
                 empty_publication_date_count,
                 empty_perex_count,
                 empty_keywords_count,
                 empty_article_content_count) = self._process_article(domain_type, to_process)

                json_data = processed_articles[0]
                json_data['url'] = url
                print(json.dumps(json_data, ensure_ascii=False))
        else:
            for website_domain_name, domain_type in self.domain_types.items():
                if self.args.domain is not None and self.args.domain != website_domain_name:
                    continue

                sql_query, article_begin_id = self._construct_query(cur, website_domain_name)
                print('Executing query "%s".' % sql_query, file=sys.stderr)

                cur.execute(sql_query)
                article_rows = cur.fetchall()

                to_process = []
                for id, url, title, publication_date, filename, created_at in article_rows:
                    with open(filename, 'r') as file:
                        to_process.append(((id, url, title, publication_date, created_at), file.read()))

                (processed_articles,
                 processed_articles_count,
                 processed_articles_last_id,
                 empty_title_count,
                 empty_author_count,
                 empty_publication_date_count,
                 empty_perex_count,
                 empty_keywords_count,
                 empty_article_content_count) = self._process_article(domain_type, to_process)

                if not self.args.manual and not self.args.dry_run and processed_articles_count > 0:
                    cur.execute('INSERT INTO article_processing_summary'
                                '(website_domain, empty_title_count, empty_author_count, empty_publication_date_count, '
                                'empty_perex_count, empty_keywords_count, empty_article_content_count, '
                                'total_articles_processed_count, start_article_id, end_article_id) '
                                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id',
                                (website_domain_name, empty_title_count, empty_author_count, empty_publication_date_count,
                                 empty_perex_count, empty_keywords_count, empty_article_content_count,
                                 processed_articles_count, article_begin_id, processed_articles_last_id))
                    processing_summary_id = cur.fetchone()[0]

                    for article_metadata_id, file_path in processed_articles:
                        cur.execute('INSERT INTO article_processed_data'
                                    '(website_domain, article_metadata_id, article_processing_summary_id, filename) '
                                    'VALUES (%s, %s, %s, %s)',
                                    (website_domain_name, article_metadata_id, processing_summary_id, file_path))

                    self.db_con.commit()

        cur.close()
        self._close_db_connection()

    def _process_article(self, domain_type, articles_raw_data):
        processed_articles_count = 0
        processed_articles_last_id = 0
        empty_title_count = 0
        empty_author_count = 0
        empty_publication_date_count = 0
        empty_perex_count = 0
        empty_keywords_count = 0
        empty_article_content_count = 0
        processed_articles = []
        for index, ((id, url, title, publication_date, created_at), article_html) in enumerate(articles_raw_data):
            print('(%s/%s) Started processing article from %s.' % (index + 1, len(articles_raw_data), url),
                  file=sys.stderr)

            try:
                html_extractor = HtmlExtractor(domain_type, article_html, url, created_at, self.args.debug)

                article_hyperlinks = html_extractor.get_all_hyperlinks()
                article_title = html_extractor.get_title()
                article_author = html_extractor.get_author()
                article_publication_date = html_extractor.get_date()
                article_perex = html_extractor.get_perex()
                article_keywords = html_extractor.get_keywords()
                article_content = html_extractor.get_article_content()

                out = dict()
                if title or article_title:
                    out['title'] = title if title else article_title
                if article_author:
                    out['author'] = article_author
                if publication_date or article_publication_date:
                    out['publication_date'] = \
                        str(publication_date) if publication_date else str(article_publication_date)
                if article_perex:
                    out['perex'] = article_perex
                if article_keywords:
                    out['keywords'] = article_keywords
                if article_content:
                    out['article_content'] = article_content
                if article_hyperlinks and not self.args.skip_hyperlinks:
                    out['hyperlinks'] = article_hyperlinks

                if self.args.dry_run:
                    json_data = json.dumps(out, indent=4, ensure_ascii=False)
                    print(json_data)
                elif self.args.pipeline:
                    processed_articles.append(out)
                else:
                    json_data = json.dumps(out, indent=4, ensure_ascii=False)
                    file_path = self._store_processed_article(id, domain_type, json_data)
                    processed_articles.append((id, file_path))

                if not (title or article_title):
                    empty_title_count += 1
                if not article_author:
                    empty_author_count += 1
                if not (publication_date or article_publication_date):
                    empty_publication_date_count += 1
                if not article_perex:
                    empty_perex_count += 1
                if not article_keywords:
                    empty_keywords_count += 1
                if not article_content:
                    empty_article_content_count += 1

                processed_articles_count += 1
                processed_articles_last_id = id
                print('(%s/%s) Finished processing article from %s.' % (index + 1, len(articles_raw_data), url),
                      file=sys.stderr)
            except Exception as e:
                print('(%s/%s) Error processing article from %s with message: %s.'
                      % (index + 1, len(articles_raw_data), url, e),
                      file=sys.stderr)
                traceback.print_exc()

        return (processed_articles, processed_articles_count, processed_articles_last_id, empty_title_count,
                empty_author_count, empty_publication_date_count, empty_perex_count, empty_keywords_count,
                empty_article_content_count)


    def _construct_query(self, cur, domain):
        begin_id = None
        end_id = None
        if not self.args.manual:
            cur.execute(
                ('SELECT s.end_article_id '
                 'FROM article_processing_summary s '
                 'WHERE s.website_domain=%s '
                 'ORDER BY s.end_article_id DESC LIMIT 1'), (domain,))
            row = cur.fetchone()
            if row:
                begin_id = row[0] + 1
            else:
                begin_id = 0
        begin_id = self.args.begin_id if self.args.begin_id else begin_id
        end_id = self.args.end_id if self.args.end_id else end_id

        base_query = (
            'SELECT a.id, a.url, a.title, a.publication_date, r.filename, r.created_at '
            'FROM article_metadata a '
            'JOIN article_raw_html r ON r.article_metadata_id = a.id '
            'WHERE 1=1%s'
        )
        sql_conditions = ' AND a.website_domain = \'%s\'' % domain
        sql_conditions += ' AND a.id >= %s' % begin_id if begin_id else ''
        sql_conditions += ' AND a.id <= %s' % end_id if end_id else ''
        sql_conditions += self.args.sql_conditions if self.args.sql_conditions else ''
        sql_conditions += ' LIMIT %s' % self.args.limit if self.args.limit else ''

        return base_query % sql_conditions, begin_id

    def _store_processed_article(self, id, domain_type: DomainType, json_data):
        folder_name = os.path.join(self.PROCESSED_HTML_FOLDER_PREFIX, domain_type.get_name())

        if not os.path.isdir(folder_name):
            os.makedirs(folder_name)

        filename = '%s_%s.json' % (id, domain_type.get_name().replace('/', '-'))
        full_path = os.path.join(folder_name, filename)

        with open(full_path, 'w') as file:
            file.write(json_data)
        return full_path

    @staticmethod
    def _init_domain_types(path_to_config):
        out = dict()

        with open(path_to_config, 'r') as file:
            json_data = json.load(file)
            out.update(JsonDomainType.get_json_domain_types(json_data))

        return out

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    process_articles = ProcessArticles()
    process_articles.run()
