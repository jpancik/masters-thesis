import argparse
import os
import sys

from lib.plagiarism_detector.plagiarism_detector import PlagiarismDetector
from lib.plagiarism_detector.plagiarism_output_processor import PlagiarismOutputProcessor
from scripts.create_corpus import CreateCorpus
from scripts.create_preverticals import CreatePreverticals


class DoAnalysis:
    VERTICAL_FILES_FOLDER = CreatePreverticals.VERTICAL_FILES_FOLDER
    NGRAM_FILES_FOLDER = CreateCorpus.NGRAM_FILES_FOLDER
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

        print('Running plagiarism detector.', file=sys.stderr)
        plagiarism_detector = PlagiarismDetector(input_ngrams_files)
        plagiarism_detector.run()

        print('Processing plagiarism detector output.', file=sys.stderr)
        plagiarism_output_processor = PlagiarismOutputProcessor(
            PlagiarismDetector.OUTPUT_FILE_PATH_DUPLICATE_POSITIONS,
            PlagiarismDetector.OUTPUT_FILE_PATH_PLAGIATES,
            input_vertical_files,
            'doc', 'dbid', 's'
        )
        plagiarism_output_processor.run()


if __name__ == '__main__':
    do_analysis = DoAnalysis()
    do_analysis.run()
