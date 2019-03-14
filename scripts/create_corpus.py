import argparse
import os
import subprocess
import sys

from scripts.create_preverticals import CreatePreverticals


class CreateCorpus:
    VERTICAL_FILES_FOLDER = CreatePreverticals.VERTICAL_FILES_FOLDER
    PRE_VERTICAL_FILES_FOLDER = CreatePreverticals.PRE_VERTICAL_FILES_FOLDER
    CONCATENATED_VERTICAL_FILE_PATH = os.path.join(VERTICAL_FILES_FOLDER, 'combined.vert')

    def __init__(self):
        self.args = self.parse_commandline()

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Don\'t store output and print it to stdout.')
        parser.add_argument('--dont-skip', action='store_true', default=False, help='Do not skip recreating existing vert files.')
        parser.add_argument('--debug', action='store_true', default=False, help='Fake output of shell commands.')
        return parser.parse_args()

    def run(self):
        if not os.path.isdir(self.PRE_VERTICAL_FILES_FOLDER):
            print('Path for pre-verticals does not exist %s.' % self.PRE_VERTICAL_FILES_FOLDER, file=sys.stderr)
            return

        env_with_py2 = os.environ.copy()
        env_with_py2['PATH'] = '/usr/bin:' + env_with_py2['PATH']

        for file_name in os.listdir(self.PRE_VERTICAL_FILES_FOLDER):
            pre_vertical_file_path = os.path.join(self.PRE_VERTICAL_FILES_FOLDER, file_name)
            vertical_file_path = os.path.join(self.VERTICAL_FILES_FOLDER, file_name.replace('.pvert', '.vert'))
            if os.path.isfile(pre_vertical_file_path) and (not os.path.exists(vertical_file_path) or self.args.dont_skip):
                # Process .pvert file into .vert using "cat *.pvert | /opt/majka_pipe/majka-czech.sh > *.vert".
                print('Processing pre-vertical %s file into %s.' % (pre_vertical_file_path, vertical_file_path), file=sys.stderr)

                # This can be easily multihreaded via:
                # https://stackoverflow.com/questions/15107714/wait-process-until-all-subprocess-finish
                cat_process = subprocess.Popen(['cat', pre_vertical_file_path], stdout=subprocess.PIPE)
                with open(vertical_file_path, 'w') as vertical_file:
                    if self.args.debug:
                        tee_process = subprocess.Popen(['tee'], stdin=cat_process.stdout, stdout=vertical_file)
                        tee_process.wait()
                    else:
                        compilecorp_process = subprocess.Popen(
                            ['/opt/majka_pipe/majka-czech.sh'],
                            stdin=cat_process.stdout, stdout=vertical_file, env=env_with_py2)
                        compilecorp_process.wait()
            else:
                print('Skipping already existing pre-vertical file %s.' % (pre_vertical_file_path))

        # print('Creating a combined vertical file into %s.' % self.CONCATENATED_VERTICAL_FILE_PATH)
        # with open(self.CONCATENATED_VERTICAL_FILE_PATH, 'w') as concatenated_vert_file:
        #     for file_name in os.listdir(self.VERTICAL_FILES_FOLDER):
        #         vertical_file_path = os.path.join(self.VERTICAL_FILES_FOLDER, file_name)
        #
        #         if (vertical_file_path != self.CONCATENATED_VERTICAL_FILE_PATH
        #                 and os.path.isfile(vertical_file_path)
        #                 and vertical_file_path.endswith('.vert')):
        #             print('Concatenating file %s.' % vertical_file_path)
        #             with open(vertical_file_path, 'r') as vertical_file:
        #                 for line in vertical_file:
        #                     concatenated_vert_file.write(line)

        print('Running compilecorp')
        if not self.args.debug:
            compilecorp_process = subprocess.Popen(
                ['compilecorp', '/home/xpancik2/masters-thesis/files/compilecorp_config/dezinfo'], env=env_with_py2)
            compilecorp_process.wait()


if __name__ == '__main__':
    create_corpus = CreateCorpus()
    create_corpus.run()
