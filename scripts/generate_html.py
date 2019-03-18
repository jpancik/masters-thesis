import argparse
from datetime import datetime
import os
import re
import sys
import shutil


class GenerateHtml:
    INDEX_PAGE_FILENAME = 'index.html'
    ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME = 'plagiarism_by_articles.html'
    ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME = 'plagiarism_by_words.html'

    def __init__(self):
        self.args = self.parse_commandline()

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('--output', type=str, default='data/html/', help='Specify path where to put HTML files.')
        return parser.parse_args()

    def run(self):
        if not os.path.isdir(self.args.output):
            os.makedirs(self.args.output)

        shutil.copy2('files/html_templates/style.css', os.path.join(self.args.output, 'style.css'))

        self._prepare_index_page()
        self._prepare_analysis_plagiarism_page()

    def _prepare_index_page(self):
        html_file_path = os.path.join(self.args.output, self.INDEX_PAGE_FILENAME)

        with open(html_file_path, 'w') as html_file:
            html_file.write(self._load_template('files/html_templates/index.html', {
                'date': datetime.now().strftime('%c')
            }))

    def _prepare_analysis_plagiarism_page(self):
        by_articles_file_path = os.path.join(self.args.output, self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME)
        by_words_file_path = os.path.join(self.args.output, self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME)

        shutil.copy2('files/html_templates/plagiarism.js', os.path.join(self.args.output, 'plagiarism.js'))

        with open(by_articles_file_path, 'w') as html_file,\
                open('data/analysis/plagiarism/plagiarism_graph_1.json', 'r') as graph_json:
            html_file.write(self._load_template('files/html_templates/plagiarism.html', {
                'graph_json': graph_json.read(),
                'type_selector': 'by articles | <a href="%s">by words</a>' % self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME
            }))

        with open(by_words_file_path, 'w') as html_file,\
                open('data/analysis/plagiarism/plagiarism_graph_1.json', 'r') as graph_json:
            html_file.write(self._load_template('files/html_templates/plagiarism.html', {
                'graph_json': graph_json.read(),
                'type_selector': '<a href="%s">by articles</a> | by words' % self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME
            }))

    @staticmethod
    def _load_template(filename, args_dict):
        with open(filename, 'r') as html_file:
            content = html_file.read()

        with open('files/html_templates/header.html', 'r') as header_file:
            content = content.replace('{{header}}', header_file.read())

        for tag in re.findall('{{([^}]+)}}', content):
            if tag in args_dict:
                print('Replacing %s tag.' % (tag), file=sys.stderr)
                content = content.replace('{{%s}}' % tag, args_dict[tag])

        return content


if __name__ == '__main__':
    generate_html = GenerateHtml()
    generate_html.run()
