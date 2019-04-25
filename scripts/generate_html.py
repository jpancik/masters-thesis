import argparse
import json
from datetime import datetime
import os
import re
import sys
import shutil


class GenerateHtml:
    INDEX_PAGE_FILENAME = 'index.html'
    CRAWLER_STATUS_FILENAME = 'crawler_status.html'
    ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_ALL_TIME = 'plagiarism_by_articles_all_time.html'
    ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_ALL_TIME = 'plagiarism_by_words_all_time.html'
    ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_TWO_WEEKS = 'plagiarism_by_articles_two_weeks.html'
    ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_TWO_WEEKS = 'plagiarism_by_words_two_weeks.html'
    ANALYSIS_HYPERLINKS_ALL_TIME = 'hyperlinks_all_time.html'
    ANALYSIS_KEYWORDS_TERMS = 'keywords_terms.html'
    ANALYSIS_KEYWORDS_PER_DOMAIN = 'keywords_per_domain.html'
    ANALYSIS_TRENDS = 'trends.html'

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
        shutil.copy2('files/html_templates/directed_graph.js', os.path.join(self.args.output, 'directed_graph.js'))

        self._prepare_crawler_status_page()
        self._prepare_analysis_plagiarism_page()
        self._prepare_analysis_hyperlinks_page()
        self._prepare_analysis_keywords_terms()
        self._prepare_analysis_keywords_per_domain()
        self._prepare_analysis_trends()

        # Create index page as last, if any of the previous fail, we shouldn't update date generated.
        self._prepare_index_page()

    def _prepare_index_page(self):
        html_file_path = os.path.join(self.args.output, self.INDEX_PAGE_FILENAME)

        with open(html_file_path, 'w') as html_file:
            html_file.write(self._load_template('files/html_templates/index.html', {
                'date': datetime.now().strftime('%c')
            }, active_tab='home'))

    def _prepare_crawler_status_page(self):
        html_file_path = os.path.join(self.args.output, self.CRAWLER_STATUS_FILENAME)

        shutil.copy2('files/html_templates/crawler_status.js', os.path.join(self.args.output, 'crawler_status.js'))

        with open('data/corpus_info.json', 'r') as corpus_info_file:
            corpus_info = json.load(corpus_info_file)

        with open(html_file_path, 'w') as html_file, open('data/watchdog_output.json', 'r') as watchdog_json:
            html_file.write(self._load_template('files/html_templates/crawler_status.html', {
                'watchdog_json': watchdog_json.read(),
                'corpus_info_compiled_at': corpus_info['compiled'],
                'corpus_info_documents': '{:,}'.format(int(corpus_info['sizes']['doccount'])),
                'corpus_info_sentences': '{:,}'.format(int(corpus_info['sizes']['sentcount'])),
                'corpus_info_tokens': '{:,}'.format(int(corpus_info['sizes']['tokencount'])),
            }, active_tab='status'))

    def _prepare_analysis_plagiarism_page(self):
        by_articles_file_path_all_time = os.path.join(self.args.output, self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_ALL_TIME)
        by_words_file_path_all_time = os.path.join(self.args.output, self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_ALL_TIME)
        by_articles_file_path_two_weeks = os.path.join(self.args.output, self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_TWO_WEEKS)
        by_words_file_path_two_weeks = os.path.join(self.args.output, self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_TWO_WEEKS)

        shutil.copy2('data/analysis/plagiarism/plagiarism_all_time.json', os.path.join(self.args.output, 'plagiarism_all_time.json'))
        shutil.copy2('data/analysis/plagiarism/plagiarism_two_weeks.json', os.path.join(self.args.output, 'plagiarism_two_weeks.json'))

        with open(by_articles_file_path_all_time, 'w') as html_file,\
                open('data/analysis/plagiarism/plagiarism_graph_by_articles_all_time.json', 'r') as graph_json:
            html_file.write(self._load_template('files/html_templates/plagiarism.html', {
                'graph_json': graph_json.read(),
                'type_selector':
                    'by articles all time | '
                    '<a href="%s">by words all time</a> | '
                    '<a href="%s">JSON data all time</a> | '
                    '<a href="%s">by articles 2 weeks</a> | '
                    '<a href="%s">by words 2 weeks</a> | '
                    '<a href="%s">JSON data 2 weeks</a>'
                    % (self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_ALL_TIME,
                       'plagiarism_all_time.json',
                       self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_TWO_WEEKS,
                       self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_TWO_WEEKS,
                       'plagiarism_two_weeks.json')
            }, active_tab='dropdown'))

        with open(by_words_file_path_all_time, 'w') as html_file,\
                open('data/analysis/plagiarism/plagiarism_graph_by_words_all_time.json', 'r') as graph_json:
            html_file.write(self._load_template('files/html_templates/plagiarism.html', {
                'graph_json': graph_json.read(),
                'type_selector':
                    '<a href="%s">by articles all time</a> | '
                    'by words all time | '
                    '<a href="%s">JSON data all time</a> | '
                    '<a href="%s">by articles 2 weeks</a> | '
                    '<a href="%s">by words 2 weeks</a> | '
                    '<a href="%s">JSON data 2 weeks</a>'
                    % (self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_ALL_TIME,
                       'plagiarism_all_time.json',
                       self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_TWO_WEEKS,
                       self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_TWO_WEEKS,
                       'plagiarism_two_weeks.json'
                       )
            }, active_tab='dropdown'))

        with open(by_articles_file_path_two_weeks, 'w') as html_file,\
                open('data/analysis/plagiarism/plagiarism_graph_by_articles_two_weeks.json', 'r') as graph_json:
            html_file.write(self._load_template('files/html_templates/plagiarism.html', {
                'graph_json': graph_json.read(),
                'type_selector':
                    '<a href="%s">by articles all time</a> | '
                    '<a href="%s">by words all time</a> | '
                    '<a href="%s">JSON data all time</a> | '
                    'by articles 2 weeks | '
                    '<a href="%s">by words 2 weeks</a> | '
                    '<a href="%s">JSON data 2 weeks</a>'
                    % (self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_ALL_TIME,
                       self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_ALL_TIME,
                       'plagiarism_all_time.json',
                       self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_TWO_WEEKS,
                       'plagiarism_two_weeks.json')
            }, active_tab='dropdown'))

        with open(by_words_file_path_two_weeks, 'w') as html_file,\
                open('data/analysis/plagiarism/plagiarism_graph_by_words_two_weeks.json', 'r') as graph_json:
            html_file.write(self._load_template('files/html_templates/plagiarism.html', {
                'graph_json': graph_json.read(),
                'type_selector':
                    '<a href="%s">by articles all time</a> | '
                    '<a href="%s">by words all time</a> | '
                    '<a href="%s">JSON data all time</a> | '
                    '<a href="%s">by articles 2 weeks</a> | '
                    'by words 2 weeks | '
                    '<a href="%s">JSON data 2 weeks</a>'
                    % (self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_ALL_TIME,
                       self.ANALYSIS_PLAGIARISM_BY_WORDS_PAGE_FILENAME_ALL_TIME,
                       'plagiarism_all_time.json',
                       self.ANALYSIS_PLAGIARISM_BY_ARTICLES_PAGE_FILENAME_TWO_WEEKS,
                       'plagiarism_two_weeks.json')
            }, active_tab='dropdown'))

    def _prepare_analysis_hyperlinks_page(self):
        hyperlinks_file_path_all_time = os.path.join(self.args.output, self.ANALYSIS_HYPERLINKS_ALL_TIME)

        shutil.copy2('data/analysis/hyperlinks/data_all_time.json', os.path.join(self.args.output, 'data_all_time.json'))

        with open(hyperlinks_file_path_all_time, 'w') as html_file,\
                open('data/analysis/hyperlinks/graph_all_time.json', 'r') as graph_json:
            html_file.write(self._load_template('files/html_templates/hyperlinks.html', {
                'graph_json': graph_json.read(),
                'type_selector':
                    'graph | '
                    '<a href="%s">JSON data</a> '
                    % ('data_all_time.json')
            }, active_tab='dropdown'))


    def _prepare_analysis_keywords_terms(self):
        keywords_terms_html_file_path = os.path.join(self.args.output, self.ANALYSIS_KEYWORDS_TERMS)

        shutil.copy2('data/analysis/keywords.json', os.path.join(self.args.output, 'keywords.json'))
        shutil.copy2('data/analysis/terms.json', os.path.join(self.args.output, 'terms.json'))

        with open(keywords_terms_html_file_path, 'w') as html_file,\
                open('data/analysis/keywords.json', 'r') as keywords_json,\
                open('data/analysis/terms.json', 'r') as terms_json:
            html_file.write(self._load_template('files/html_templates/keywords_terms.html', {
                'keywords_json': keywords_json.read(),
                'terms_json': terms_json.read(),
                'type_selector':
                    '<a href="%s">keywords JSON</a> | '
                    '<a href="%s">terms JSON</a>'
                    % ('keywords.json', 'terms.json')
            }, active_tab='dropdown'))

    def _prepare_analysis_keywords_per_domain(self):
        keywords_per_domain_html_file_path = os.path.join(self.args.output, self.ANALYSIS_KEYWORDS_PER_DOMAIN)

        shutil.copy2('data/analysis/keywords_per_domain.json', os.path.join(self.args.output, 'keywords_per_domain.json'))
        shutil.copy2('files/html_templates/d3cloud.js', os.path.join(self.args.output, 'd3cloud.js'))

        with open(keywords_per_domain_html_file_path, 'w') as html_file, \
                open('data/analysis/keywords_per_domain.json', 'r') as keywords_json:
            html_file.write(self._load_template('files/html_templates/keywords_per_domain.html', {
                'keywords_json': keywords_json.read(),
                'type_selector': '<a href="%s">keywords per domain JSON</a>' % ('keywords_per_domain.json')
            }, active_tab='dropdown'))

    def _prepare_analysis_trends(self):
        trends_html_file_path = os.path.join(self.args.output, self.ANALYSIS_TRENDS)

        shutil.copy2('data/analysis/trends.json', os.path.join(self.args.output, 'trends.json'))

        with open(trends_html_file_path, 'w') as html_file, \
                open('data/analysis/trends.json', 'r') as trends_json:
            html_file.write(self._load_template('files/html_templates/trends.html', {
                'trends_json': trends_json.read(),
                'type_selector': '<a href="%s">trends JSON</a>' % 'trends.json'
            }, active_tab='dropdown'))

    @staticmethod
    def _load_template(filename, args_dict, active_tab=None):
        with open(filename, 'r') as html_file:
            content = html_file.read()

        with open('files/html_templates/header.html', 'r') as header_file:
            header_content = header_file.read()

            if active_tab:
                tags = {
                    'home': '{{homeActive}}',
                    'status': '{{crawlerStatusActive}}',
                    'dropdown': '{{dropdownActive}}'
                }

                for key, tag in tags.items():
                    if active_tab == key:
                        header_content = header_content.replace(tag, 'active')
                    else:
                        header_content = header_content.replace(tag, '')

            content = content.replace('{{header}}', header_content)

        for tag in re.findall('{{([^}]+)}}', content):
            if tag in args_dict:
                content = content.replace('{{%s}}' % tag, args_dict[tag])

        return content


if __name__ == '__main__':
    generate_html = GenerateHtml()
    generate_html.run()
