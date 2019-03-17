import sys


class PlagiarismDetector:
    OUTPUT_FILE_PATH_DUPLICATE_POSITIONS = 'data/analysis/duplicates_output'
    OUTPUT_FILE_PATH_PLAGIATES = 'data/analysis/plagiates_output'

    def __init__(self, input_ngram_files,
                 doc_dup_sent_count=10, sent_dup_ngr_ratio=0.67, doc_dup_ngr_ratio=0.25,
                 output_file_duplicate_positions=None,
                 output_file_plagiates=None):
        self.input_ngram_files = input_ngram_files
        self.output_file_duplicate_positions = output_file_duplicate_positions if output_file_duplicate_positions else self.OUTPUT_FILE_PATH_DUPLICATE_POSITIONS
        self.output_file_plagiates = output_file_plagiates if output_file_plagiates else self.OUTPUT_FILE_PATH_PLAGIATES
        self.doc_dup_sent_count = doc_dup_sent_count
        self.sent_dup_ngr_ratio = sent_dup_ngr_ratio
        self.doc_dup_ngr_ratio = doc_dup_ngr_ratio

    def run(self):
        shingle_index, ngram_counter = {}, 0
        for doc_hash_file in self.input_ngram_files:
            with open(doc_hash_file) as fp:
                for sent_line in fp:
                    doc_id, doc_sent_id, sent_token_shingles = self.get_sentence_shingles(sent_line)
                    for token_offset, token_shingle_hash in enumerate(sent_token_shingles):
                        if token_shingle_hash not in shingle_index:
                            #keep the first shingle occurrence only
                            shingle_index[token_shingle_hash] = (doc_id, doc_sent_id, token_offset)
                        ngram_counter += 1

        print('%d n-grams (%d unique) read' % (ngram_counter, len(shingle_index)), file=sys.stderr)

        result_dup_doc_ids, result_dup_shingle_positions, result_dup_info = [], [], []

        doc_count = dup_doc_count = 0
        prev_doc_id, doc_dup_shingle_positions = None, []
        doc_sent_count = doc_dup_sent_count = doc_shingle_count = doc_dup_shingle_count = 0
        for input_vert_file in self.input_ngram_files:
            with open(input_vert_file, 'r') as vert_file:
                for sent_line in vert_file:
                    doc_id, doc_sent_id, sent_token_shingles = self.get_sentence_shingles(sent_line)
                    #document level -- decide if the previous document is a plagiarism
                    if doc_id != prev_doc_id:
                        if prev_doc_id:
                            if self.check_document_duplicate(
                                    result_dup_doc_ids, result_dup_shingle_positions, result_dup_info,
                                    prev_doc_id, doc_dup_sent_count, doc_shingle_count,
                                    doc_dup_shingle_count, doc_dup_shingle_positions):
                                dup_doc_count += 1
                        prev_doc_id, doc_dup_shingle_positions = doc_id, []
                        doc_sent_count = doc_dup_sent_count = doc_shingle_count = doc_dup_shingle_count = 0
                        doc_count += 1
                    doc_sent_count += 1
                    doc_shingle_count += len(sent_token_shingles)
                    #sentence level -- compare shingles
                    sent_dup_shingle_count = 0
                    for token_offset, token_shingle_hash in enumerate(sent_token_shingles):
                        try:
                            src_doc_id, src_doc_sent_id, src_token_offset = shingle_index[token_shingle_hash]
                        except KeyError:
                            continue #no duplicate found
                        if doc_id == src_doc_id:
                            continue #found in the same document => not a duplicate
                        #duplicate shingle in another document found
                        doc_dup_shingle_positions.append((doc_id, doc_sent_id, token_offset,
                            src_doc_id, src_doc_sent_id, src_token_offset))
                        sent_dup_shingle_count += 1
                        doc_dup_shingle_count += 1
                    #duplicate sentence shingle ratio over the threshold => duplicate sentence
                    if float(sent_dup_shingle_count) / len(sent_token_shingles) >= self.sent_dup_ngr_ratio:
                        doc_dup_sent_count += 1
        if prev_doc_id: #the last document
            if self.check_document_duplicate(
                    result_dup_doc_ids, result_dup_shingle_positions, result_dup_info,
                    prev_doc_id, doc_dup_sent_count, doc_shingle_count,
                    doc_dup_shingle_count, doc_dup_shingle_positions):
                dup_doc_count += 1

        with open(self.output_file_duplicate_positions, 'w') as fp:
            for dup_shingle_position in result_dup_shingle_positions:
                fp.write('%s\n' % '\t'.join(map(str, dup_shingle_position)))
        with open(self.output_file_plagiates, 'w') as fp:
            for dup_info in result_dup_info:
                fp.write('%s\n' % '\t'.join(dup_info))
        print('%d/%d candidate documents found' % (dup_doc_count, doc_count), file=sys.stderr)

    @staticmethod
    def get_sentence_shingles(sent_line):
        doc_id, doc_sent_id, sent_token_shingles_s = sent_line.split('\t', 2)
        doc_sent_id = int(doc_sent_id)
        sent_token_shingles = map(int, sent_token_shingles_s.split('\t'))
        return doc_id, doc_sent_id, list(sent_token_shingles)

    def check_document_duplicate(self,
            result_dup_doc_ids, result_dup_shingle_positions, result_dup_info,
            doc_id, doc_dup_sent_count, doc_shingle_count, doc_dup_shingle_count,
            doc_dup_shingle_positions):
        # duplicate sentence count over the threshold => duplicate document
        # duplicate document shingle ratio over the threshold => duplicate document
        dup_shingle_ratio = float(doc_dup_shingle_count) / doc_shingle_count
        if doc_dup_sent_count >= self.doc_dup_sent_count \
                or dup_shingle_ratio >= self.doc_dup_ngr_ratio:
            result_dup_doc_ids.append(doc_id)
            result_dup_shingle_positions.extend(doc_dup_shingle_positions)
            result_dup_info.append((doc_id, str(doc_dup_sent_count), '%.2f' % dup_shingle_ratio))
            return True
