import argparse
import os
import sys

from lib.plagiarism_detector.plagiarism_detector import PlagiarismDetector
from lib.plagiarism_detector.plagiarism_output_processor import PlagiarismOutputProcessor
from scripts.create_corpus import CreateCorpus
from scripts.create_preverticals import CreatePreverticals


class DoAnalysis:
    OUTPUT_FILE_PATH_DUPLICATE_POSITIONS = 'data/analysis/plagiarism/duplicates_output'
    OUTPUT_FILE_PATH_PLAGIATES = 'data/analysis/plagiarism/plagiates_output'
    OUTPUT_FILE_PATH_PLAGIARISM_HTML = 'data/analysis/plagiarism/plagiarism_debug'
    OUTPUT_FILE_PATH_PLAGIARISM_JSON = 'data/analysis/plagiarism/plagiarism'
    OUTPUT_FILE_PATH_JSON_GRAPH_BY_ARTICLES = 'data/analysis/plagiarism/plagiarism_graph_by_articles'
    OUTPUT_FILE_PATH_JSON_GRAPH_BY_WORDS = 'data/analysis/plagiarism/plagiarism_graph_by_words'

    VERTICAL_FILES_FOLDER = CreatePreverticals.VERTICAL_FILES_FOLDER
    NGRAM_FILES_FOLDER = CreateCorpus.NGRAM_FILES_FOLDER
    ANALYSIS_PLAGIARISM_FOLDER = 'data/analysis/plagiarism'
    WORK_TYPES = [
        'plagiates'
    ]

    def __init__(self):
        self.args = self.parse_commandline()

    def parse_commandline(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('--work-type', type=str, choices=self.WORK_TYPES, required=True,
                            help='Type of scrape work to perform')
        return parser.parse_args()

    def run(self):
        if self.args.work_type == 'plagiates':
            self.find_plagiates()

    def find_plagiates(self):
        if not os.path.isdir(self.NGRAM_FILES_FOLDER):
            print('Folder %s with n-grams not found.' % self.NGRAM_FILES_FOLDER, file=sys.stderr)
            return
        if not os.path.isdir(self.VERTICAL_FILES_FOLDER):
            print('Folder %s with vertical files not found.' % self.VERTICAL_FILES_FOLDER, file=sys.stderr)
            return

        if not os.path.isdir(self.ANALYSIS_PLAGIARISM_FOLDER):
            os.makedirs(self.ANALYSIS_PLAGIARISM_FOLDER)

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

        output_file_path_duplicate_position_all_time = '%s%s' % (self.OUTPUT_FILE_PATH_DUPLICATE_POSITIONS, '_all_time')
        output_file_path_plagiates_all_time = '%s%s' % (self.OUTPUT_FILE_PATH_PLAGIATES, '_all_time')

        print('Running plagiarism detector.', file=sys.stderr)
        plagiarism_detector = PlagiarismDetector(
            input_ngrams_files,
            output_file_duplicate_positions=output_file_path_duplicate_position_all_time,
            output_file_plagiates=output_file_path_plagiates_all_time)
        plagiarism_detector.run()

        print('Processing plagiarism detector output.', file=sys.stderr)
        plagiarism_output_processor = PlagiarismOutputProcessor(
            output_file_path_duplicate_position_all_time,
            output_file_path_plagiates_all_time,
            input_vertical_files,
            '%s%s.html' % (self.OUTPUT_FILE_PATH_PLAGIARISM_HTML, '_all_time'),
            '%s%s.json' % (self.OUTPUT_FILE_PATH_PLAGIARISM_JSON, '_all_time'),
            '%s%s.json' % (self.OUTPUT_FILE_PATH_JSON_GRAPH_BY_ARTICLES, '_all_time'),
            '%s%s.json' % (self.OUTPUT_FILE_PATH_JSON_GRAPH_BY_WORDS, '_all_time'),
            'doc', 'dbid', 's'
        )
        plagiarism_output_processor.run()


if __name__ == '__main__':
    do_analysis = DoAnalysis()
    do_analysis.run()
