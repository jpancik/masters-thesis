import sys, re

from lib import util


class NgramsGenerator:
    def __init__(self, input_file, output_file, doc_struct, doc_id, sent_struct, ngram_length=7):
        self.input_file = input_file
        self.output_file = output_file
        self.doc_struct = doc_struct
        self.doc_id_re = re.compile(' %s="([^"]+)"' % doc_id)
        self.sent_start_re = re.compile('<%s[ >]' % sent_struct)
        self.sent_end_re = re.compile('</%s>' % sent_struct)
        self.ngram_length = ngram_length

    def generate(self):
        doc_counter = sent_counter = ngram_counter = 0
        for doc in util.read_big_structures(self.input_file, self.doc_struct):
            doc_counter += 1
            doc_lines = doc.split('\n')

            # Simulate "cut -f 1" here:
            cut_result = []
            for line in doc_lines:
                cut_result.append(line.split('\t', 1)[0])
            doc_lines = cut_result
            # Continue.

            try:
                doc_id = self.doc_id_re.search(doc_lines[0]).group(1)
            except AttributeError:
                print('%s\n' % doc[:100], file=sys.stderr)
                raise
            sent_tokens, in_sent, doc_sent_id = [], False, 0
            for line in doc_lines:
                if in_sent:
                    if self.sent_end_re.match(line):
                        sent_token_shingles = self.get_sentence_shingles(sent_tokens)
                        if sent_token_shingles:
                            self.output_file.write('%s\t%d\t%s\n' %
                                (doc_id, doc_sent_id, '\t'.join(map(str, sent_token_shingles))))
                            ngram_counter += len(sent_token_shingles)
                        sent_counter += 1
                        doc_sent_id += 1
                        sent_tokens, in_sent = [], False
                    elif line and line[0] != '<':
                        sent_tokens.append(line.rstrip())
                elif self.sent_start_re.match(line):
                    sent_token_shingles = self.get_sentence_shingles(sent_tokens)
                    if sent_token_shingles:
                        self.output_file.write('%s\t%d\t%s\n' %
                            (doc_id, doc_sent_id, '\t'.join(map(str, sent_token_shingles))))
                        ngram_counter += len(sent_token_shingles)
                    sent_tokens, in_sent = [], True
        print(
            'Ngrams Generator: %d documents, %d sentences, %d %d-grams processed'
            % (doc_counter, sent_counter, ngram_counter, self.ngram_length),
            file=sys.stderr)

    def get_sentence_shingles(self, sent_tokens):
        shingle_hashes = []
        for token_pos in range(len(sent_tokens) - self.ngram_length + 1):
            shingle = sent_tokens[token_pos:token_pos + self.ngram_length]
            shingle_hashes.append(hash('\t'.join(shingle)))
        return shingle_hashes
