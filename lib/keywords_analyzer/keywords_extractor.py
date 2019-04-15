import json
import os
import re
import sys
from urllib.parse import urlparse

from lib import util


class KeywordsPerDomainExtractor:
    KEYWORDS_COUNT_THRESHOLD = 5
    KEYWORDS_LENGTH_THRESHOLD = 3
    PREFIX_BLACKLIST = ['twitter', 'facebook']

    def __init__(self, input_vertical_files,
                 output_file_keywords=None):
        self.input_vertical_files = input_vertical_files
        self.output_file_keywords = output_file_keywords

    def run(self):
        ref_freq_file_path = 'data/czes2_lemma_freq.tsv'
        if not os.path.exists(ref_freq_file_path):
            print('Could not find file %s with reference lemma frequencies.' % (ref_freq_file_path), file=sys.stderr)
            return

        doc_url_re = re.compile(' %s="([^"]+)"' % 'url')
        doc_struct = 'doc'

        # (netloc, dict(word, count))
        words_per_domain = dict()
        # (netloc, count)
        words_count_per_domain = dict()
        for vertical_file_path in self.input_vertical_files:
            print('Loading vertical file %s.' % vertical_file_path, file=sys.stderr)
            with open(vertical_file_path, 'r') as vertical_file:
                for raw_doc in util.read_big_structures(vertical_file, doc_struct):
                    doc_header, doc_body = raw_doc.split('\n', 1)
                    doc_url = doc_url_re.search(doc_header).group(1)
                    doc_netloc = urlparse(doc_url).netloc

                    # Simulate "cut -f 2" here, we want lemmas.
                    doc_lines = doc_body.split('\n')
                    cut_result = []
                    for line in doc_lines:
                        splitted = line.split('\t', 2)
                        cut_result.append(splitted[len(splitted) - 2])
                    doc_lines = cut_result
                    # Continue.

                    for word in doc_lines:
                        if word == '.' or word == ',' or not word.isalpha():
                            continue

                        if doc_netloc not in words_per_domain:
                            words_per_domain[doc_netloc] = dict()

                        if word in words_per_domain[doc_netloc]:
                            words_per_domain[doc_netloc][word] += 1
                        else:
                            words_per_domain[doc_netloc][word] = 1

                        if doc_netloc in words_count_per_domain:
                            words_count_per_domain[doc_netloc] += 1
                        else:
                            words_count_per_domain[doc_netloc] = 1
            print('Loaded vertical file.', file=sys.stderr)

        # Remove words that appear too infrequently.
        for website_domain, words_count in words_per_domain.items():
            to_remove = []
            removed_words = 0

            for word, count in words_count.items():
                if count < self.KEYWORDS_COUNT_THRESHOLD or len(word) <= self.KEYWORDS_LENGTH_THRESHOLD:
                    to_remove.append(word)
                    removed_words += count
                else:
                    for blacklisted_prefix in self.PREFIX_BLACKLIST:
                        if word.lower().startswith(blacklisted_prefix):
                            to_remove.append(word)
                            removed_words += count
                            break

            for word_to_remove in to_remove:
                del words_count[word_to_remove]
            words_count_per_domain[website_domain] -= removed_words

        print('Loading reference frequencies from %s.' % ref_freq_file_path, file=sys.stderr)
        # (word, count)
        reference_words_count = dict()
        refernece_words_total_count = 0
        with open(ref_freq_file_path, 'r') as ref_freq_file:
            for line in ref_freq_file:
                id, word, count = line.split('\t')
                reference_words_count[word] = int(count)
                refernece_words_total_count += int(count)
        print('Loaded reference frequencies.', file=sys.stderr)

        # (netloc, [(word, ratio])
        word_ratio_per_website_domain = dict()
        for website_domain, words_count in words_per_domain.items():
            for word, count in words_count.items():
                if word not in reference_words_count:
                    # print('%s not found' % word)
                    continue

                ratio_dezinfo = count/words_count_per_domain[website_domain]
                ratio_reference = reference_words_count[word]/refernece_words_total_count
                if ratio_dezinfo > 5 * ratio_reference:
                    if website_domain not in word_ratio_per_website_domain:
                        word_ratio_per_website_domain[website_domain] = []

                    word_ratio_per_website_domain[website_domain].append((word, (ratio_dezinfo/ratio_reference), count))

        # (website_domain, [(keyword, ratio, count)]
        output = dict()
        for website_domain, ratios_list in word_ratio_per_website_domain.items():
            ratios_list.sort(key=lambda x: -x[1])

            output[website_domain] = []
            for (keyword, ratio, count) in ratios_list[0:100]:
                output[website_domain].append({
                    'keyword': keyword,
                    'ratio': ratio,
                    'count': count
                })

        with open(self.output_file_keywords, 'w') as output_file:
            output_file.write(json.dumps(output, indent=4))
