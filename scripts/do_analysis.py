import argparse
import json
import math
import os
import re
import sys
import ntpath
import traceback
import urllib
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests

from lib import util, webtrack_logger
from lib.crawler_db import connector
from lib.plagiarism_detector.plagiarism_detector import PlagiarismDetector
from lib.plagiarism_detector.plagiarism_output_processor import PlagiarismOutputProcessor
from lib.webtrack_logger import log
from scripts.create_corpus import CreateCorpus
from scripts.create_preverticals import CreatePreverticals


class DoAnalysis:
    CORPUS_INFO_OUTPUT_JSON_DATA = 'data/corpus_info.json'

    VERTICAL_FILES_FOLDER = CreatePreverticals.VERTICAL_FILES_FOLDER
    NGRAM_FILES_FOLDER = CreateCorpus.NGRAM_FILES_FOLDER
    PLAGIARISM_FOLDER = 'data/analysis/plagiarism/'
    PLAGIARISM_OUTPUT_DUPLICATE_POSITIONS = os.path.join(PLAGIARISM_FOLDER, 'duplicates_output')
    PLAGIARISM_OUTPUT_PLAGIATES = os.path.join(PLAGIARISM_FOLDER, 'plagiates_output')
    PLAGIARISM_OUTPUT_PLAGIARISM_HTML = os.path.join(PLAGIARISM_FOLDER, 'plagiarism_debug')
    PLAGIARISM_OUTPUT_PLAGIARISM_JSON = os.path.join(PLAGIARISM_FOLDER, 'plagiarism')
    PLAGIARISM_OUTPUT_JSON_GRAPH_BY_ARTICLES = os.path.join(PLAGIARISM_FOLDER, 'plagiarism_graph_by_articles')
    PLAGIARISM_OUTPUT_JSON_GRAPH_BY_WORDS = os.path.join(PLAGIARISM_FOLDER, 'plagiarism_graph_by_words')

    HYPERLINKS_FOLDER = 'data/analysis/hyperlinks/'
    HYPERLINKS_OUTPUT_JSON_GRAPH = os.path.join(HYPERLINKS_FOLDER, 'graph_all_time.json')
    HYPERLINKS_OUTPUT_JSON_DATA = os.path.join(HYPERLINKS_FOLDER, 'data_all_time.json')
    HYPERLINKS_GRAPH_LINK_THRESHOLD = 1

    KEYWORDS_PER_DOMAIN_OUTPUT_JSON_DATA = 'data/analysis/keywords_terms_per_domain.json'
    TRENDS_OUTPUT_JSON_DATA = 'data/analysis/trends.json'

    WORK_TYPES = [
        'all',
        'corpus_info',
        'plagiates',
        'hyperlinks',
        'keywords_terms',
        'trends'
    ]

    def __init__(self):
        self.args = self.parse_commandline()
        webtrack_logger.setup_logging()
        self.db_con = connector.get_db_connection()

    def parse_commandline(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('--type', type=str, choices=self.WORK_TYPES, required=True,
                            help='Type of scrape work to perform')
        return parser.parse_args()

    def run(self):
        do_all = self.args.type == 'all'

        if self.args.type == 'corpus_info' or do_all:
            self.get_corpus_info()
        if self.args.type == 'plagiates' or do_all:
            self.find_plagiates()
        if self.args.type == 'hyperlinks' or do_all:
            self.analyze_hyperlinks()
        if self.args.type == 'keywords_terms' or do_all:
            self.keywords_terms_per_domain()
        if self.args.type == 'trends' or do_all:
            self.trends()

        self._close_db_connection()

    def get_corpus_info(self):
        username, api_key = self._read_api_key()

        params = {
            'corpname': 'preloaded/dezinfo',
            'format': 'json'
        }
        url_query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        url_query += '&username=%s' % username
        url_query += '&api_key=%s' % api_key
        corpus_info_url_base = 'https://ske.fi.muni.cz/bonito/api.cgi/corp_info?'

        try:
            url = '%s%s' % (corpus_info_url_base, url_query)
            response = requests.get(url, timeout=120)

            with open(self.CORPUS_INFO_OUTPUT_JSON_DATA, 'w') as corpus_info_file:
                corpus_info_file.write(response.text)

            log.info('Finished retrieving corpus info through API.')
        except Exception as e:
            log.error('Error getting corpus info through API with message %s.' % e)

    def find_plagiates(self):
        if not os.path.isdir(self.NGRAM_FILES_FOLDER):
            log.error('Folder %s with n-grams not found.' % self.NGRAM_FILES_FOLDER)
            return
        if not os.path.isdir(self.VERTICAL_FILES_FOLDER):
            log.error('Folder %s with vertical files not found.' % self.VERTICAL_FILES_FOLDER)
            return

        if not os.path.isdir(self.PLAGIARISM_FOLDER):
            os.makedirs(self.PLAGIARISM_FOLDER)

        input_ngrams_files = []
        input_vertical_files = []
        for file_name in os.listdir(self.VERTICAL_FILES_FOLDER):
            vertical_file_path = os.path.join(self.VERTICAL_FILES_FOLDER, file_name)
            ngrams_file_path = os.path.join(self.NGRAM_FILES_FOLDER, file_name.replace('.vert', '.ngr'))

            if (os.path.isfile(vertical_file_path)
                    and vertical_file_path.endswith('.vert')
                    and os.path.exists(ngrams_file_path)):
                log.info(
                    'Found vertical file %s and matching n-grams file %s.' % (vertical_file_path, ngrams_file_path))
                input_ngrams_files.append(ngrams_file_path)
                input_vertical_files.append(vertical_file_path)

        # Two weeks.
        two_weeks_ago_datetime = datetime.today() - timedelta(days=14)
        two_weeks_ngrams = list(filter(
            lambda filepath: datetime.strptime(ntpath.basename(filepath).replace('.ngr', ''), '%Y-%m-%d') >= two_weeks_ago_datetime, input_ngrams_files))
        two_weeks_vertical_files = list(filter(
            lambda filepath: datetime.strptime(ntpath.basename(filepath).replace('.vert', ''), '%Y-%m-%d') >= two_weeks_ago_datetime, input_vertical_files))

        suffixes = [
            '_all_time',
            '_two_weeks'
        ]
        input_ngrams = [
            input_ngrams_files,
            two_weeks_ngrams
        ]
        input_verticals = [
            input_vertical_files,
            two_weeks_vertical_files
        ]
        for i in range(2):
            output_file_path_duplicate_position_all_time = '%s%s' % (self.PLAGIARISM_OUTPUT_DUPLICATE_POSITIONS, suffixes[i])
            output_file_path_plagiates_all_time = '%s%s' % (self.PLAGIARISM_OUTPUT_PLAGIATES, suffixes[i])

            log.info('Running plagiarism detector on %s.' % suffixes[i])
            plagiarism_detector = PlagiarismDetector(
                input_ngrams[i],
                output_file_duplicate_positions=output_file_path_duplicate_position_all_time,
                output_file_plagiates=output_file_path_plagiates_all_time)
            plagiarism_detector.run()

            log.info('Processing plagiarism detector output on %s.' % suffixes[i])
            plagiarism_output_processor = PlagiarismOutputProcessor(
                output_file_path_duplicate_position_all_time,
                output_file_path_plagiates_all_time,
                input_verticals[i],
                '%s%s.html' % (self.PLAGIARISM_OUTPUT_PLAGIARISM_HTML, suffixes[i]),
                '%s%s.json' % (self.PLAGIARISM_OUTPUT_PLAGIARISM_JSON, suffixes[i]),
                '%s%s.json' % (self.PLAGIARISM_OUTPUT_JSON_GRAPH_BY_ARTICLES, suffixes[i]),
                '%s%s.json' % (self.PLAGIARISM_OUTPUT_JSON_GRAPH_BY_WORDS, suffixes[i]),
                'doc', 'dbid', 's',
                use_threshold=(i == 0)
            )
            plagiarism_output_processor.run()

    def analyze_hyperlinks(self):
        if not os.path.isdir(self.HYPERLINKS_FOLDER):
            os.makedirs(self.HYPERLINKS_FOLDER)

        cur = self.db_con.cursor()

        log.info('Retrieving all processed articles.')
        cur.execute('SELECT a.id, a.url, d.filename FROM article_processed_data d '
                    'JOIN article_metadata a ON a.id = d.article_metadata_id')
        rows = cur.fetchall()
        log.info('Finished retrieving all processed articles.')

        log.info('Loading hyperlinks from processed JSON files.')

        # id_by_url: (netloc, path) : (article_id, article_url)
        id_by_url = dict()
        # hyperlinks_by_id: (article_id, article_url) : [hyperlinks]
        hyperlinks_in_files = dict()

        for index, (article_id, article_url, article_filename) in enumerate(rows):
            if os.path.exists(article_filename):
                with open(article_filename, 'r') as json_file:
                    data = json.load(json_file)

                    if 'language' in data and data['language'] != 'cs':
                        continue

                    if 'hyperlinks' in data:
                        hyperlinks_in_files[(article_id, article_url)] = data['hyperlinks']
                    else:
                        hyperlinks_in_files[(article_id, article_url)] = []

                    parsed_url = urlparse(article_url)
                    id_by_url[(parsed_url.netloc, parsed_url.path)] = (article_id, article_url)

            if index % int(len(rows)/10) == 0 and math.ceil(index/len(rows) * 100.0) != 100:
                print('%.0f%%' % math.ceil(index/len(rows) * 100.0), end='....', file=sys.stderr)
                sys.stderr.flush()
        print('', file=sys.stderr)
        log.info('Finished loading hyperlinks from processed JSON files.')

        log.info('Analyzing hyperlinks...')
        # raw_data: source_url: [reference_urls]
        raw_data = dict()
        links = dict()
        for index, ((article_id, article_url), hyperlinks) in enumerate(hyperlinks_in_files.items()):
            for hyperlink in hyperlinks:
                parsed_url = urlparse(hyperlink)
                key = (parsed_url.netloc, parsed_url.path)

                if key in id_by_url:
                    source_netloc = urlparse(article_url).netloc
                    target_article_url = id_by_url[key][1]
                    target_netloc = urlparse(target_article_url).netloc
                    if source_netloc != target_netloc:
                        link_key = (source_netloc, target_netloc)
                        if link_key in links:
                            links[link_key] += 1
                        else:
                            links[link_key] = 1

                        if article_url not in raw_data:
                            raw_data[article_url] = [target_article_url]
                        else:
                            raw_data[article_url].append(target_article_url)

            if index % int(len(hyperlinks_in_files)/10) == 0 and math.ceil(index/len(hyperlinks_in_files) * 100.0) != 100:
                print('%.0f%%' % math.ceil(index/len(hyperlinks_in_files) * 100.0), end='....', file=sys.stderr)
                sys.stderr.flush()
        print('', file=sys.stderr)
        log.info('Finished analyzing hyperlinks.')

        with open(self.HYPERLINKS_OUTPUT_JSON_DATA, 'w') as output_file:
            output_file.write(json.dumps(raw_data, ensure_ascii=False))

        graph_json_data = {
            'nodes': [],
            'links': []
        }
        domains = set()
        for (source, target), count in links.items():
            if count >= self.HYPERLINKS_GRAPH_LINK_THRESHOLD:
                domains.add(source)
                domains.add(target)
                graph_json_data['links'].append({
                    'value': count,
                    'source': source,
                    'target': target
                })

        colors = util.get_spaced_colors(len(domains))
        graph_json_data['nodes'] = [{
                'domain': x,
                'name': x,
                'id': x,
                'color': colors[index]
            }
            for (index, x) in enumerate(domains)]

        graph_json_data['links'].sort(key=lambda val: (val['source'], -val['value']))

        with open(self.HYPERLINKS_OUTPUT_JSON_GRAPH, 'w') as output_file:
            output_file.write(json.dumps(graph_json_data, ensure_ascii=False))

        if cur:
            cur.close()

    def keywords_terms_per_domain(self):
        subcorpuses_list = self._get_subcorpuses()
        keywords_terms_data = {}

        for subcorpus_name in subcorpuses_list:
            params = {
                'corpname': 'preloaded/dezinfo',
                'ref_corpname': 'preloaded/cztenten15_0',
                'usesubcorp': subcorpus_name,
                'simple_n': '1',
                'max_keywords': '100',
                'alnum': '0',
                'onealpha': '1',
                'minfreq': '1',
                'format': 'json',
                'attr': 'word',
            }

            keywords_url_base = 'https://ske.fi.muni.cz/bonito/api.cgi/extract_keywords?'
            keywords_response = self._send_api_request(keywords_url_base, params)
            keywords_json = json.loads(keywords_response.text)
            if 'keywords' in keywords_json:
                keywords_terms_data[subcorpus_name] = {
                    'keywords': keywords_json['keywords']
                }
            else:
                log.warning('Key keywords is missing from retrieved JSON.')
            log.info('Finished retrieving keywords through API for subcorpus %s.' % subcorpus_name)

        for subcorpus_name in subcorpuses_list:
            params = {
                'corpname': 'preloaded/dezinfo',
                'ref_corpname': 'preloaded/cztenten15_0_sample',
                'usesubcorp': subcorpus_name,
                'simple_n': '1',
                'max_terms': '100',
                'alnum': '0',
                'onealpha': '1',
                'minfreq': '1',
                'format': 'json',
                'attr': 'word',
            }
            terms_url_base = 'https://ske.fi.muni.cz/bonito/api.cgi/extract_terms?'
            terms_response = self._send_api_request(terms_url_base, params)
            terms_json = json.loads(terms_response.text)
            if 'terms' in terms_json:
                keywords_terms_data[subcorpus_name]['terms'] = terms_json['terms']
            else:
                log.warning('Key terms is missing from retrieved JSON.')
            log.info('Finished retrieving terms through API for subcorpus %s.' % subcorpus_name)

        with open(self.KEYWORDS_PER_DOMAIN_OUTPUT_JSON_DATA, 'w') as keywords_terms_file:
            keywords_terms_file.write(json.dumps(keywords_terms_data))

    def trends(self):
        subcorpuses_list = self._get_subcorpuses()
        trends_data = {}

        for subcorpus_name in subcorpuses_list:
            params = {
                'corpname': 'preloaded/dezinfo',
                'usesubcorp': subcorpus_name,
                'reload': '',
                'structattr': 'doc.yearmonth',
                'trends_attr': 'word',
                'trends_method': 'mkts_all',
                'trends_maxp': '0.1',
                'trends_sort_by': 't',
                'trends_minfreq': '2',
                'trends_re': '',
                'filter_nonwords': '0',
                'filter_capitalized': '0',
                'format': 'json'
            }
            trends_url_base = 'https://ske.fi.muni.cz/bonito/api.cgi/trends?'
            trends_response = self._send_api_request(trends_url_base, params)
            trends_data[subcorpus_name] = json.loads(trends_response.text)
            log.info('Finished retrieving trends through API for subcorpus %s.' % subcorpus_name)

        with open(self.TRENDS_OUTPUT_JSON_DATA, 'w') as trends_file:
            trends_file.write(json.dumps(trends_data))

        log.info('Finished retrieving trends through API.')

    @staticmethod
    def _read_api_key():
        with open('files/ske_api_key', 'r') as api_key_file:
            content = api_key_file.read()
            username, api_key = content.split(' ')
        return username.strip(), api_key.strip()

    def _send_api_request(self, url_base, params):
        username, api_key = self._read_api_key()

        url_query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        url_query += '&username=%s' % username
        url_query += '&api_key=%s' % api_key

        try:
            url = '%s%s' % (url_base, url_query)
            log.info(url)
            response = requests.get(url, timeout=120)
            return response
        except Exception as e:
            log.error('Error getting %s through API with message %s.' % (url, e))

    def _get_subcorpuses(self):
        subcorpuses_list = []
        with open('files/compilecorp_config/dezinfo_subcdef.txt', 'r') as subcorpora_definitions:
            raw_file = subcorpora_definitions.read()
            for match in re.finditer(r'^=(.*)$', raw_file, re.MULTILINE):
                subcorpuses_list.append(match.group(1))
        return subcorpuses_list

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    do_analysis = DoAnalysis()
    do_analysis.run()
