import argparse
import json
import os
import sys
from xml.sax.saxutils import quoteattr

import psycopg2


class CreateVertical:
    VERTICAL_FILES_FOLDER = 'data/vertical_files/pre_vertical/'

    def __init__(self):
        self.args = self.parse_commandline()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

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

        if self.args.all:
            cur.execute('SELECT * FROM article_processed_data')
            article_processed_data_rows = cur.fetchall()
            self.create_vertical('all_articles.pvert', article_processed_data_rows)
        else:
            cur.execute('SELECT DATE(a.created_at) FROM article_processed_data a GROUP BY DATE(a.created_at)')
            dates = cur.fetchall()
            for date in dates:
                file_name = '%s-%s-%s.pvert' % (date[0].year, date[0].month, date[0].day)
                if os.path.exists('%s/%s' % (self.VERTICAL_FILES_FOLDER, file_name)) and not self.args.dont_skip:
                    print('Skipping "%s" because it already exists.' % file_name, file=sys.stderr)
                    continue

                cur.execute('SELECT * FROM article_processed_data d WHERE DATE(d.created_at) = %s', date)
                article_processed_data_rows = cur.fetchall()
                self.create_vertical(file_name, article_processed_data_rows)

        if cur:
            cur.close()
        self._close_db_connection()

    def create_vertical(self, file_name, article_processed_data_rows):
        if not self.args.dry_run:
            if not os.path.isdir(self.VERTICAL_FILES_FOLDER):
                os.makedirs(self.VERTICAL_FILES_FOLDER)

        output_filename = '%s%s' % (self.VERTICAL_FILES_FOLDER, file_name)
        output_file = None
        if not self.args.dry_run:
            output_file = open(output_filename, 'w')

        total_count = len(article_processed_data_rows)
        print('Started processing %s articles into vertical file "%s".' % (total_count, output_filename),
              file=sys.stderr)

        for index, (id, website_domain_name, article_metadata_id, article_processing_summary_id, filename,
                    created_at) in enumerate(article_processed_data_rows):
            if not os.path.exists(filename):
                print('Filename %s does not exist.' % filename, file=sys.stderr)

            with open(filename, 'r') as file:
                data = json.load(file)
                self.print_to_vertical(
                    output_file,
                    article_metadata_id,
                    website_domain_name,
                    data['title'] if 'title' in data else None,
                    data['author'] if 'author' in data else None,
                    data['publication_date'] if 'publication_date' in data else None,
                    data['perex'] if 'perex' in data else None,
                    data['article_content'] if 'article_content' in data else None)

            if index != 0 and index % ((int(total_count / 100.0)) * 10) == 0:
                print('Finished processing %.0f%% articles.' % (index / float(total_count) * 100.0), file=sys.stderr)

        if output_file:
            output_file.close()

    def print_to_vertical(
            self, output_file, article_metadata_id, website_domain_name,
            title, author, publication_date, perex, article_content):

        output_file.write('<doc')
        output_file.write(' id=%s' % quoteattr(str(article_metadata_id)))
        output_file.write(' domain=%s' % quoteattr(website_domain_name))
        if title:
            output_file.write(' title=%s' % quoteattr(title))
        if author:
            output_file.write(' author=%s' % quoteattr(author))
        if publication_date:
            output_file.write(' date=%s' % quoteattr(publication_date))
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
    create_vertical = CreateVertical()
    create_vertical.run()
