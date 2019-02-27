import argparse
import json
import os
import sys
from xml.sax.saxutils import quoteattr

import psycopg2


class CreateVertical:
    VERTICAL_FILES_FOLDER = 'data/vertical_files/'

    def __init__(self):
        self.args = self.parse_commandline()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('-p', '--pipeline', action='store_true', default=False, help='Run script in pipeline mode.')
        return parser.parse_args()

    def run(self):
        if not self.args.dry_run:
            if not os.path.isdir(self.VERTICAL_FILES_FOLDER):
                os.makedirs(self.VERTICAL_FILES_FOLDER)

        output_filename = '%s%s' % (self.VERTICAL_FILES_FOLDER, 'output.vert')
        output_file = None
        if not self.args.dry_run:
            output_file = open(output_filename, 'w')
        cur = self.db_con.cursor()

        cur.execute('SELECT * FROM article_processed_data')
        article_processed_data_rows = cur.fetchall()

        total_count = len(article_processed_data_rows)
        print('Started processing %s articles into vertical file "%s".' % (total_count, output_filename), file=sys.stderr)

        for index, (id, website_domain_name, article_metadata_id, article_processing_summary_id, filename,
             created_at) in enumerate(article_processed_data_rows):
            if not os.path.exists(filename):
                print('Filename %s does not exist.' % filename, file=sys.stderr)

            with open(filename, 'r') as file:
                data = json.load(file)
                self.print_to_vertical(
                    output_file,
                    article_metadata_id,
                    data['title'] if 'title' in data else None,
                    data['author'] if 'author' in data else None,
                    data['publication_date'] if 'publication_date' in data else None,
                    data['perex'] if 'perex' in data else None,
                    data['article_content'] if 'article_content' in data else None)

            if index != 0 and index % ((int(total_count/100.0)) * 10) == 0:
                print('Finished processing %.0f%% articles.' % (index/float(total_count)*100.0))

            if index >= 100:
                break

        if output_file:
            output_file.close()
        if cur:
            cur.close()
        self._close_db_connection()

    def print_to_vertical(
            self, output_file, article_metadata_id, title, author, publication_date, perex, article_content):

        output_file.write('<doc')
        output_file.write(' id=%s' % quoteattr(str(article_metadata_id)))
        if title:
            output_file.write(' title=%s' % quoteattr(title))
        if author:
            output_file.write(' author=%s' % quoteattr(author))
        if publication_date:
            output_file.write(' date=%s' % quoteattr(publication_date))
        if perex:
            output_file.write(' perex=%s' % quoteattr(perex))
        output_file.write('>\n')

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
