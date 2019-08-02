import argparse
import json
import math
import os
import sys
from datetime import datetime
from xml.sax.saxutils import quoteattr

from lib import webtrack_logger
from lib.crawler_db import connector
from lib.webtrack_logger import log


class CreatePreverticals:
    VERTICAL_FILES_FOLDER = 'data/vertical_files/'
    PRE_VERTICAL_FILES_FOLDER = '%sprevertical/' % VERTICAL_FILES_FOLDER

    def __init__(self):
        self.args = self.parse_commandline()
        webtrack_logger.setup_logging()

        if not self.args.pipeline:
            self.db_con = connector.get_db_connection()
        else:
            self.db_con = None

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('-p', '--pipeline', action='store_true', default=False, help='Run script in pipeline mode.')
        parser.add_argument('-a', '--all', action='store_true', default=False, help='Create pre-vertical file from all articles.')
        parser.add_argument('--dont-skip', action='store_true', default=False, help='Do not skip recreating existing pvert files.')
        return parser.parse_args()

    def run(self):
        cur = self.db_con.cursor()

        if self.args.pipeline:
            parsed_data = []
            for line in sys.stdin:
                data = json.loads(line)
                parsed_data.append(data)

            for data in parsed_data:
                self.print_to_vertical(
                    sys.stdout,
                    -1,
                    data['url'] if 'url' in data else None,
                    data['title'] if 'title' in data else None,
                    data['author'] if 'author' in data else None,
                    data['publication_date'] if 'publication_date' in data else None,
                    data['perex'] if 'perex' in data else None,
                    data['article_content'] if 'article_content' in data else None)
        elif self.args.all:
            cur.execute('SELECT m.id, m.url, d.filename FROM article_processed_data d '
                        'JOIN article_metadata m ON m.id = d.article_metadata_id')
            article_processed_data_rows = cur.fetchall()
            self.create_vertical('all_articles.pvert', article_processed_data_rows)
        else:
            cur.execute('SELECT DATE(a.created_at) FROM article_processed_data a GROUP BY DATE(a.created_at)')
            dates = cur.fetchall()
            for date in dates:
                date_parsed = datetime.strptime(date[0], '%Y-%m-%d')
                file_name = '%s-%s-%s.pvert' % (date_parsed.year, date_parsed.month, date_parsed.day)
                if os.path.exists('%s/%s' % (self.PRE_VERTICAL_FILES_FOLDER, file_name)) and not self.args.dont_skip:
                    log.info('Skipping "%s" because it already exists.' % file_name)
                    continue

                cur.execute('SELECT m.id, m.url, d.filename FROM article_processed_data d '
                            'JOIN article_metadata m ON m.id = d.article_metadata_id '
                            'WHERE DATE(d.created_at) = ?', date)
                article_processed_data_rows = cur.fetchall()
                self.create_vertical(file_name, article_processed_data_rows)

        if cur:
            cur.close()
        self._close_db_connection()

    def create_vertical(self, file_name, article_processed_data_rows):
        if not self.args.dry_run:
            if not os.path.isdir(self.PRE_VERTICAL_FILES_FOLDER):
                os.makedirs(self.PRE_VERTICAL_FILES_FOLDER)

        output_filename = '%s%s' % (self.PRE_VERTICAL_FILES_FOLDER, file_name)
        output_file = None
        if not self.args.dry_run:
            output_file = open(output_filename, 'w')

        total_count = len(article_processed_data_rows)
        log.info('Started processing %s articles into vertical file "%s".' % (total_count, output_filename))

        for index, (article_metadata_id, article_url, filename) in enumerate(article_processed_data_rows):
            if not os.path.exists(filename):
                log.info('Filename %s does not exist.' % filename)

            with open(filename, 'r') as file:
                data = json.load(file)
                self.print_to_vertical(
                    output_file,
                    article_metadata_id,
                    article_url,
                    data['title'] if 'title' in data else None,
                    data['author'] if 'author' in data else None,
                    data['publication_date'] if 'publication_date' in data else None,
                    data['perex'] if 'perex' in data else None,
                    data['language'] if 'language' in data else None,
                    data['article_content'] if 'article_content' in data else None)

            if index != 0 and index % ((int(total_count / 100.0)) * 10) == 0:
                log.info('Finished processing %.0f%% articles.' % (index / float(total_count) * 100.0))

        if output_file:
            output_file.close()

    @staticmethod
    def print_to_vertical(
            output_file, article_metadata_id, article_url,
            title, author, publication_date, perex, language, article_content):

        output_file.write('<doc')
        output_file.write(' dbid=%s' % quoteattr(str(article_metadata_id)))
        output_file.write(' url=%s' % quoteattr(article_url))
        if title:
            output_file.write(' title=%s' % quoteattr(title))
        if author:
            output_file.write(' author=%s' % quoteattr(author))
        if publication_date:
            parsed_date = datetime.strptime(publication_date, '%Y-%m-%d %H:%M:%S')
            output_file.write(' date=%s' % quoteattr(publication_date))
            output_file.write(' yearmonth=%s' % quoteattr(parsed_date.strftime('%Y%m')))
            output_file.write(' yearq=%s' % quoteattr('%s%s' % (parsed_date.year, math.ceil(parsed_date.month / 3.0))))
        if language:
            output_file.write(' language=%s' % quoteattr(language))
        output_file.write('>\n')

        if perex:
            stripped_perex = perex.strip()
            output_file.write('<p perex="1">\n')
            output_file.write(stripped_perex)
            output_file.write('\n</p>\n')

        if article_content:
            splitted = article_content.split('\n')

            for paragraph in splitted:
                stripped = paragraph.strip()

                if stripped:
                    output_file.write('<p>\n')
                    output_file.write(stripped)
                    output_file.write('\n</p>\n')

        output_file.write('</doc>\n\n')

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    create_preverticals = CreatePreverticals()
    create_preverticals.run()
