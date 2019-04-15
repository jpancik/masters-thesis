import argparse
import json
import math
import os
import sys
import ntpath
import traceback
import urllib
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests

from lib.crawler_db import connector
from lib.keywords_analyzer.keywords_extractor import KeywordsPerDomainExtractor
from lib.plagiarism_detector.plagiarism_detector import PlagiarismDetector
from lib.plagiarism_detector.plagiarism_output_processor import PlagiarismOutputProcessor
from scripts.create_corpus import CreateCorpus
from scripts.create_preverticals import CreatePreverticals


class DoAnalysis:
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
    HYPERLINKS_GRAPH_LINK_THRESHOLD = 5

    KEYWORDS_OUTPUT_JSON_DATA = 'data/analysis/keywords.json'
    TERMS_OUTPUT_JSON_DATA = 'data/analysis/terms.json'

    WORK_TYPES = [
        'all',
        'plagiates',
        'hyperlinks',
        'keywords+terms',
        'keywords_per_domain'
    ]

    def __init__(self):
        self.args = self.parse_commandline()
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

        if self.args.type == 'plagiates' or do_all:
            self.find_plagiates()
        if self.args.type == 'hyperlinks' or do_all:
            self.analyze_hyperlinks()
        if self.args.type == 'keywords+terms' or do_all:
            self.analyze_keywords_and_terms()
        if self.args.type == 'keywords_per_domain' or do_all:
            self.analyze_keywords_per_domain()

        self._close_db_connection()

    def find_plagiates(self):
        if not os.path.isdir(self.NGRAM_FILES_FOLDER):
            print('Folder %s with n-grams not found.' % self.NGRAM_FILES_FOLDER, file=sys.stderr)
            return
        if not os.path.isdir(self.VERTICAL_FILES_FOLDER):
            print('Folder %s with vertical files not found.' % self.VERTICAL_FILES_FOLDER, file=sys.stderr)
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
                print(
                    'Found vertical file %s and matching n-grams file %s.' % (vertical_file_path, ngrams_file_path),
                    file=sys.stderr)
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

            print('Running plagiarism detector on %s.' % suffixes[i], file=sys.stderr)
            plagiarism_detector = PlagiarismDetector(
                input_ngrams[i],
                output_file_duplicate_positions=output_file_path_duplicate_position_all_time,
                output_file_plagiates=output_file_path_plagiates_all_time)
            plagiarism_detector.run()

            print('Processing plagiarism detector output on %s.' % suffixes[i], file=sys.stderr)
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

        print('Retrieving all processed articles.', file=sys.stderr)
        cur.execute('SELECT a.id, a.url, d.filename FROM article_processed_data d '
                    'JOIN article_metadata a ON a.id = d.article_metadata_id')
        rows = cur.fetchall()
        print('Finished retrieving all processed articles.', file=sys.stderr)

        print('Loading hyperlinks from processed JSON files.', file=sys.stderr)

        # id_by_url: (netloc, path) : (article_id, article_url)
        id_by_url = dict()
        # hyperlinks_by_id: (article_id, article_url) : [hyperlinks]
        hyperlinks_in_files = dict()

        for index, (article_id, article_url, article_filename) in enumerate(rows):
            if os.path.exists(article_filename):
                with open(article_filename, 'r') as json_file:
                    data = json.load(json_file)

                    if 'hyperlinks' in data:
                        hyperlinks_in_files[(article_id, article_url)] = data['hyperlinks']
                    else:
                        hyperlinks_in_files[(article_id, article_url)] = []

                    parsed_url = urlparse(article_url)
                    id_by_url[(parsed_url.netloc, parsed_url.path)] = (article_id, article_url)

            if index % int(len(rows)/10) == 0 and math.ceil(index/len(rows) * 100.0) != 100:
                print('%.0f%%' % math.ceil(index/len(rows) * 100.0), end='....', file=sys.stderr)
                sys.stderr.flush()
        print('\nFinished loading hyperlinks from processed JSON files.', file=sys.stderr)

        print('Analyzing hyperlinks...', file=sys.stderr)
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
        print('\nFinished analyzing hyperlinks.', file=sys.stderr)

        with open(self.HYPERLINKS_OUTPUT_JSON_DATA, 'w') as output_file:
            output_file.write(json.dumps(raw_data, indent=4, ensure_ascii=False))

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

        colors = PlagiarismOutputProcessor.get_spaced_colors(len(domains))
        graph_json_data['nodes'] = [{
                'domain': x,
                'name': x,
                'id': x,
                'color': '#%02x%02x%02x' % colors[index]
            }
            for (index, x) in enumerate(domains)]

        graph_json_data['links'].sort(key=lambda val: (val['source'], -val['value']))

        with open(self.HYPERLINKS_OUTPUT_JSON_GRAPH, 'w') as output_file:
            output_file.write(json.dumps(graph_json_data, indent=4, ensure_ascii=False))

        if cur:
            cur.close()

    def analyze_keywords_and_terms(self):
        with open('files/ske_api_key', 'r') as api_key_file:
            content = api_key_file.read()
            username, api_key = content.split(' ')

        params = {
            'corpname': 'preloaded/dezinfo',
            'ref_corpname': 'preloaded/czes2',
            'simple_n': '1',
            'max_terms': '100',
            'max_keywords': '250',
            'alnum': '0',
            'onealpha': '1',
            'minfreq': '1',
            'format': 'json',
            'attr': 'lemma',
        }
        url_query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        url_query += '&username=%s' % username
        url_query += '&api_key=%s' % api_key
        keywords_url_base = 'https://ske.fi.muni.cz/bonito/api.cgi/extract_keywords?'

        try:
            url = '%s%s' % (keywords_url_base, url_query)
            response = requests.get(url, timeout=120)

            with open(self.KEYWORDS_OUTPUT_JSON_DATA, 'w') as keywords_file:
                keywords_file.write(response.text)

            print('Finished retrieving keywords through API.', file=sys.stderr)
        except Exception as e:
            traceback.print_exc()
            print('Error getting keywords through API with message %s.' % e, file=sys.stderr)

        terms_url_base = 'https://ske.fi.muni.cz/bonito/api.cgi/extract_terms?'
        params['ref_corpname'] = 'preloaded/cztenten12_8_sample'
        url_query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        try:
            response = requests.get('%s%s' % (terms_url_base, url_query), timeout=120)

            with open(self.TERMS_OUTPUT_JSON_DATA, 'w') as terms_file:
                terms_file.write(response.text)

            print('Finished retrieving terms through API.', file=sys.stderr)
        except Exception as e:
            traceback.print_exc()
            print('Error getting terms through API with message %s.' % e, file=sys.stderr)

    def analyze_keywords_per_domain(self):
        if not os.path.isdir(self.VERTICAL_FILES_FOLDER):
            print('Folder %s with vertical files not found.' % self.VERTICAL_FILES_FOLDER, file=sys.stderr)
            return

        input_vertical_files = []
        for file_name in os.listdir(self.VERTICAL_FILES_FOLDER):
            vertical_file_path = os.path.join(self.VERTICAL_FILES_FOLDER, file_name)

            if os.path.isfile(vertical_file_path) and vertical_file_path.endswith('.vert'):
                print('Found vertical file %s.' % (vertical_file_path), file=sys.stderr)
                input_vertical_files.append(vertical_file_path)

        keywords_extractor = KeywordsPerDomainExtractor(
            input_vertical_files,
            'data/analysis/keywords_per_domain.json'
        )
        keywords_extractor.run()


    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    do_analysis = DoAnalysis()
    do_analysis.run()
