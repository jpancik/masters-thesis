import argparse
import os
import subprocess
import sys

from scripts.create_preverticals import CreatePreverticals


class CreateCorpus:
    VERTICAL_FILES_FOLDER = CreatePreverticals.VERTICAL_FILES_FOLDER
    PRE_VERTICAL_FILES_FOLDER = CreatePreverticals.PRE_VERTICAL_FILES_FOLDER

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

        for file_name in os.listdir(self.PRE_VERTICAL_FILES_FOLDER):
            pre_vertical_file_path = os.path.join(self.PRE_VERTICAL_FILES_FOLDER, file_name)
            vertical_file_path = os.path.join(self.VERTICAL_FILES_FOLDER, file_name.replace('.pvert', '.vert'))
            if os.path.isfile(pre_vertical_file_path) and (not os.path.exists(vertical_file_path) or self.args.dont_skip):
                # Process .pvert file into .vert using "cat *.pvert | /opt/majka_pipe/majka-czech.sh > *.vert".
                print('Processing pre-vertical %s file into %s.' % (pre_vertical_file_path, vertical_file_path), file=sys.stderr)

                cat_process = subprocess.Popen(['cat', pre_vertical_file_path], stdout=subprocess.PIPE)
                with open(vertical_file_path, 'w') as vertical_file:
                    if self.args.debug:
                        tee_process = subprocess.Popen(['tee'], stdin=cat_process.stdout, stdout=vertical_file)
                        tee_process.wait()
                    else:
                        env_with_py2 = os.environ.copy()
                        env_with_py2['PATH'] = '/usr/bin:' + env_with_py2['PATH']
                        majka_pipe_process = subprocess.Popen(
                            ['/opt/majka_pipe/majka-czech.sh'],
                            stdin=cat_process.stdout, stdout=vertical_file, stderr=sys.stderr, env=env_with_py2)
                        majka_pipe_process.wait()
            else:
                print('Skipping already existing pre-vertical file %s.' % (pre_vertical_file_path))



if __name__ == '__main__':
    create_corpus = CreateCorpus()
    create_corpus.run()
