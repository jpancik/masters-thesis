import json
import sys, re
from datetime import datetime
from urllib.parse import urlparse


class PlagiarismOutputProcessor:
    GRAPH_LINK_BY_ARTICLES_THRESHOLD = 5
    GRAPH_LINK_BY_WORDS_THRESHOLD = 500

    def __init__(self, dup_pos_file, plag_id_file, input_vertical_files,
                 output_html_file_path, output_json_file_path,
                 output_json_graph_by_articles_file_path,
                 output_json_graph_by_words_file_path,
                 doc_struct, doc_id, sent_struct,
                 use_threshold=True, n=7, min_source_ngrs=10, plagiate_threshold_word_ratio=0.25):
        self.dup_pos_file = dup_pos_file
        self.plag_id_file = plag_id_file
        self.input_vertical_files = input_vertical_files
        self.doc_struct = doc_struct
        self.doc_id = doc_id
        self.sent_struct = sent_struct
        self.use_threshold = use_threshold
        self.n = n
        self.min_source_ngrs = min_source_ngrs
        self.plagiate_threshold_word_ratio = plagiate_threshold_word_ratio
        self.output_html_file_path = output_html_file_path
        self.output_json_file_path = output_json_file_path
        self.output_json_graph_by_articles_file_path = output_json_graph_by_articles_file_path
        self.output_json_graph_by_words_file_path = output_json_graph_by_words_file_path

    @staticmethod
    def read_big_structures(fp, structure_tag, buffer_size=10000000):
        structure_start_re = re.compile('^<%s[ >]' % structure_tag, re.M)
        buffer_ = ''
        while True:
            new_data = fp.read(buffer_size)
            if not new_data:
                break
            buffer_ += new_data
            starting_positions = [m.start() for m in structure_start_re.finditer(buffer_)]
            if starting_positions == []:
                continue
            for i in range(len(starting_positions) - 1):
                start = starting_positions[i]
                end = starting_positions[i + 1]
                yield buffer_[start:end]
            buffer_ = buffer_[starting_positions[-1]:]
        if buffer_ != '':
            yield buffer_

    def run(self):
        doc_id_re = re.compile(' %s="([^"]+)"' % self.doc_id)
        doc_url_re = re.compile(' %s="([^"]+)"' % 'url')
        doc_date_re = re.compile(' %s="([^"]+)"' % 'date')
        sent_start_re = re.compile('<%s[ >]' % self.sent_struct)
        sent_end_re = re.compile('</%s>' % self.sent_struct)
        doc_attrs_re = re.compile(' ([^=]+)="([^"]+)"')

        #read duplicate document properties
        dup_doc_info = {}
        with open(self.plag_id_file) as fp:
            for line in fp:
                dup_doc_id, doc_dup_sent_count, dup_shingle_ratio = line.split('\t')
                dup_doc_info[dup_doc_id] = (int(doc_dup_sent_count), float(dup_shingle_ratio))

        #read duplicate positions
        duplicate_ranges, source_ranges_all, dup_doc_ids = {}, {}, set()
        dup_pos_counter = 0
        with open(self.dup_pos_file) as fp:
            for line in fp:
                dup_doc_id, dup_doc_sent_id, dup_token_offset, \
                    src_doc_id, src_doc_sent_id, src_token_offset = line.split('\t')
                dup_doc_sent_id, dup_token_offset = int(dup_doc_sent_id), int(dup_token_offset)
                src_doc_sent_id, src_token_offset = int(src_doc_sent_id), int(src_token_offset)
                dup_doc_ids.add(dup_doc_id)
                dup_pos_counter += 1
                #determine ranges of duplicate positions in duplicate documents and related sources
                try:
                    duplicate_ranges[dup_doc_id][(dup_doc_sent_id, dup_token_offset)] = src_doc_id
                except KeyError:
                    duplicate_ranges[dup_doc_id] = {(dup_doc_sent_id, dup_token_offset): src_doc_id}
                try:
                    source_ranges_all[src_doc_id][dup_doc_id].add((src_doc_sent_id, src_token_offset))
                except KeyError:
                    try:
                        source_ranges_all[src_doc_id][dup_doc_id] = {(src_doc_sent_id, src_token_offset)}
                    except KeyError:
                        source_ranges_all[src_doc_id] = {dup_doc_id: {(src_doc_sent_id, src_token_offset)}}

        #determine major sources of duplicate documents
        src_doc_ids_of_dup_docs, source_ranges, doc_ids_required = {}, {}, set()
        for src_doc_id, dup_docs in source_ranges_all.items():
            for dup_doc_id, dup_doc_positions in dup_docs.items():
                if len(dup_doc_positions) >= self.min_source_ngrs:
                    try:
                        source_ranges[src_doc_id][dup_doc_id] = dup_doc_positions
                    except KeyError:
                        source_ranges[src_doc_id] = {dup_doc_id: dup_doc_positions}
                    try:
                        src_doc_ids_of_dup_docs[dup_doc_id].add(src_doc_id)
                    except KeyError:
                        src_doc_ids_of_dup_docs[dup_doc_id] = {src_doc_id}
                    doc_ids_required.add(src_doc_id)
        doc_ids_required.update(dup_doc_ids)

        print(
            '%d duplicate positions read, %d major sources determined' % (dup_pos_counter, len(source_ranges)),
            file=sys.stderr)

        id_to_doc_attrs_map = dict()

        #read source documents (only the required)
        doc_counter, doc_sentences, doc_attrs = 0, {}, {}
        for vertical_file_path in self.input_vertical_files:
            with open(vertical_file_path, 'r') as vertical_file:
                for raw_doc in self.read_big_structures(vertical_file, self.doc_struct):
                    # Simulate "cut -f 1" here:
                    doc_lines = raw_doc.split('\n')
                    cut_result = []
                    for line in doc_lines:
                        cut_result.append(line.split('\t', 1)[0])
                    doc = '\n'.join(cut_result)
                    # Continue.

                    doc_counter += 1

                    doc_header, doc_body = doc.split('\n', 1)
                    try:
                        doc_id = doc_id_re.search(doc_header).group(1)
                        doc_url = doc_url_re.search(doc_header).group(1)
                        doc_date = doc_date_re.search(doc_header)
                        if doc_date:
                            doc_date = doc_date.group(1)
                        id_to_doc_attrs_map[doc_id] = {
                            'domain': urlparse(doc_url).netloc,
                            'url': doc_url,
                            'date': doc_date
                        }
                    except AttributeError:
                        print('%s' % doc_header, file=sys.stderr)
                        raise
                    if not doc_id in doc_ids_required:
                        continue
                    this_doc_sentences = doc_sentences[doc_id] = []
                    doc_attrs[doc_id] = doc_attrs_re.findall(doc_header)
                    sent_words, in_sent, doc_sent_id = [], False, 0
                    for line in doc_body.split('\n'):
                        if in_sent:
                            if sent_end_re.match(line):
                                if sent_words:
                                    this_doc_sentences.append(sent_words)
                                sent_words, in_sent = [], False
                            elif line and line[0] != '<':
                                sent_words.append(line.rstrip())
                        elif sent_start_re.match(line):
                            if sent_words:
                                this_doc_sentences.append(sent_words)
                            sent_words, in_sent = [], True

        print('%d source documents read' % doc_counter, file=sys.stderr)

        self._write_html_output(
            dup_doc_ids, src_doc_ids_of_dup_docs, id_to_doc_attrs_map,
            doc_sentences, duplicate_ranges, doc_attrs, dup_doc_info, source_ranges)
        plagiates = self._write_json_output(
            dup_doc_ids, src_doc_ids_of_dup_docs, id_to_doc_attrs_map,
            doc_sentences, duplicate_ranges, doc_attrs, dup_doc_info, source_ranges)
        self._write_graph_jsons(plagiates, id_to_doc_attrs_map)

    def _write_html_output(
            self, dup_doc_ids, src_doc_ids_of_dup_docs, id_to_doc_attrs_map,
            doc_sentences, duplicate_ranges, doc_attrs, dup_doc_info, source_ranges):
        with open(self.output_html_file_path, 'w') as html_file:
            #print source and duplicate documents, mark duplicate positions
            dup_doc_len = len(dup_doc_ids)
            html_file.write('''<!doctype html>\n\n<html>\n<head>
            <title>%d plagiarism candidates found</title><style>
            h2 {margin: 6px 0; padding-top: 2px; border-top: 10px solid #099;}\nh3 {margin: 6px 0;}
            div.panel {float: left; width: 45%%; margin-right: 0.5em;}
            div.doc {margin-bottom: 0.5em; padding: 4px 1em; background-color: #dff;
                border: 2px solid #099; border-radius: 25px;}
            div.txt {margin: 10px 0;}\ndiv.clear {clear: both;}\np {margin: 2px 0;}
            table {border-collapse: collapse; border: 1px solid #099;}
            th, td {padding: 6px; border: 1px solid #099; text-align: left;}
            .dup0 {background-color: #ff4d4d;}\n.dup1 {background-color: #4d4dff;}
            .dup2 {background-color: #4dff4d;}\n.dup3 {background-color: #ff4dff;}
            .dup4 {background-color: #ffa64d;}\n.dup-1 {background-color: #ffff4d;}
            </style>\n</head>\n<body>\n<h1>%d plagiarism candidates found</h1>\n''' %
                (dup_doc_len, dup_doc_len))
            for dup_doc_id_i, dup_doc_id in enumerate(sorted(dup_doc_ids)):
                #headers
                src_doc_ids = sorted(src_doc_ids_of_dup_docs.get(dup_doc_id, []))

                # Remove same domains:
                src_doc_ids = list(
                    filter(
                        lambda src_doc_id: id_to_doc_attrs_map[dup_doc_id]['domain'] != id_to_doc_attrs_map[src_doc_id][
                            'domain'], src_doc_ids))
                if not src_doc_ids:
                    continue

                html_file.write('<h2>(%d) Plagiarism candidate: %s, Possible major sources: %s</h2>\n' %
                    (dup_doc_id_i + 1, dup_doc_id, ', '.join(src_doc_ids) if src_doc_ids else 'none'))

                #document comparison -- duplicate document content with duplicate positions marked

                # This is a copy of the marking code to count the words.
                dup_doc_total_word_count = 0
                dup_doc_plagiated_word_count = 0
                for doc_sent_id, sent_words in enumerate(doc_sentences[dup_doc_id]):
                    marked_sentence, marked_range_end = [], -1
                    plagiates = False
                    for word_offset, word in enumerate(sent_words):
                        src_doc_id = duplicate_ranges[dup_doc_id].get((doc_sent_id, word_offset))
                        if src_doc_id in src_doc_ids and src_doc_id:  # range start
                            if marked_range_end < word_offset:
                                plagiates = True
                            marked_range_end = word_offset + self.n - 1
                        if plagiates:
                            dup_doc_plagiated_word_count += 1
                        dup_doc_total_word_count += 1
                        if marked_range_end == word_offset:  # range end
                            plagiates = False
                # Up to here.

                dup_doc_attrs = doc_attrs[dup_doc_id] + \
                    [('Duplicate sentence count', '%d' % dup_doc_info[dup_doc_id][0]),
                     ('Duplicate %d-gram ratio' % self.n, '%.2f' % dup_doc_info[dup_doc_id][1]),
                     ('Website domain', id_to_doc_attrs_map[dup_doc_id]['domain']),
                     ('Total words count', dup_doc_total_word_count),
                     ('Total plagiated words count', dup_doc_plagiated_word_count),
                     ('Ratio plagiated words / total words', '%.2f' % (dup_doc_plagiated_word_count/dup_doc_total_word_count)),]
                attrs_s = '\n'.join(('<tr><th>%s</th><td>%s</td></tr>' % x for x in dup_doc_attrs))
                marked_doc_content = ['<h3>Plagiarism candidate: %s</h3>\n<table>\n%s\n</table>\n'
                    '<div class="txt">' % (dup_doc_id, attrs_s)]
                doc_duplicate_ranges = duplicate_ranges[dup_doc_id]
                for doc_sent_id, sent_words in enumerate(doc_sentences[dup_doc_id]):
                    marked_sentence, marked_range_end = [], -1
                    for word_offset, word in enumerate(sent_words):
                        src_doc_id = doc_duplicate_ranges.get((doc_sent_id, word_offset))
                        if src_doc_id in src_doc_ids and src_doc_id: #range start
                            if marked_range_end < word_offset:
                                try:
                                    src_doc_id_i = src_doc_ids.index(src_doc_id)
                                except ValueError:
                                    src_doc_id_i = -1
                                marked_sentence.append('<span class="dup%d">' % src_doc_id_i)
                            marked_range_end = word_offset + self.n - 1
                        marked_sentence.append(word)
                        if marked_range_end == word_offset: #range end
                            marked_sentence.append('</span>')
                    marked_doc_content.append('<p>%s</p>' % ' '.join(marked_sentence))
                marked_doc_content.append('</div>')
                html_file.write('<div class="panel doc">\n%s\n</div>\n' % '\n'.join(marked_doc_content))
                #document comparison -- source document content with source positions marked
                marked_doc_content = []
                for src_doc_id_i, src_doc_id in enumerate(src_doc_ids):
                    doc_source_ranges = source_ranges[src_doc_id][dup_doc_id]

                    # This is a copy of the marking code to count the words.
                    src_doc_total_word_count = 0
                    src_doc_plagiated_word_count = 0
                    for doc_sent_id, sent_words in enumerate(doc_sentences[src_doc_id]):
                        marked_sentence, marked_range_end = [], -1
                        plagiates = False
                        for word_offset, word in enumerate(sent_words):
                            if (doc_sent_id, word_offset) in doc_source_ranges: #range start
                                if marked_range_end < word_offset:
                                    plagiates = True
                                marked_range_end = word_offset + self.n - 1
                            if plagiates:
                                src_doc_plagiated_word_count += 1
                            src_doc_total_word_count += 1
                            if marked_range_end == word_offset: #range end
                                plagiates = False
                    # Up to here.

                    src_doc_attrs = doc_attrs[src_doc_id] + \
                                    [('Website domain', id_to_doc_attrs_map[src_doc_id]['domain']),
                                     ('Total words count', src_doc_total_word_count),
                                     ('Total plagiated words count', src_doc_plagiated_word_count),
                                     ('Ratio plagiated words / total words',
                                      '%.2f' % (src_doc_plagiated_word_count / src_doc_total_word_count)),]
                    attrs_s = '\n'.join(('<tr><th>%s</th><td>%s</td></tr>' % x for x in src_doc_attrs))
                    marked_doc_content.append('<div class="doc">\n<h3>Source document: %s '
                        '<span class="dup%d">%s</span></h3>\n<table>\n%s\n</table>\n<div class="txt">' %
                        (src_doc_id, src_doc_id_i, '&nbsp;' * 3, attrs_s))
                    for doc_sent_id, sent_words in enumerate(doc_sentences[src_doc_id]):
                        marked_sentence, marked_range_end = [], -1
                        for word_offset, word in enumerate(sent_words):
                            if (doc_sent_id, word_offset) in doc_source_ranges: #range start
                                if marked_range_end < word_offset:
                                    marked_sentence.append('<span class="dup%d">' % src_doc_id_i)
                                marked_range_end = word_offset + self.n - 1
                            marked_sentence.append(word)
                            if marked_range_end == word_offset: #range end
                                marked_sentence.append('</span>')
                        marked_doc_content.append('<p>%s</p>' % ' '.join(marked_sentence))
                    marked_doc_content.append('</div>\n</div>')
                html_file.write('<div class="panel">\n%s\n</div>\n' % '\n'.join(marked_doc_content))
                html_file.write('<div class="clear"></div>\n')
            html_file.write('</body>\n</html>\n')
            print('%d candidate documents visualised' % dup_doc_len, file=sys.stderr)

    def _write_json_output(self, dup_doc_ids, src_doc_ids_of_dup_docs, id_to_doc_attrs_map,
            doc_sentences, duplicate_ranges, doc_attrs, dup_doc_info, source_ranges):
        plagiates = []

        for dup_doc_id_i, dup_doc_id in enumerate(sorted(dup_doc_ids)):
            # headers
            src_doc_ids = sorted(src_doc_ids_of_dup_docs.get(dup_doc_id, []))

            # Remove same domains:
            src_doc_ids = list(
                filter(
                    lambda src_doc_id: id_to_doc_attrs_map[dup_doc_id]['domain'] != id_to_doc_attrs_map[src_doc_id][
                        'domain'], src_doc_ids))
            if not src_doc_ids:
                continue

            plagiate_info = dict()
            plagiate_info['dbid'] = dup_doc_id
            plagiate_info['url'] = id_to_doc_attrs_map[dup_doc_id]['url']
            plagiate_info['date'] = id_to_doc_attrs_map[dup_doc_id]['date']

            dup_doc_total_word_count = 0
            dup_doc_plagiated_word_count = 0
            for doc_sent_id, sent_words in enumerate(doc_sentences[dup_doc_id]):
                marked_sentence, marked_range_end = [], -1
                plagiated_words = False
                for word_offset, word in enumerate(sent_words):
                    src_doc_id = duplicate_ranges[dup_doc_id].get((doc_sent_id, word_offset))
                    if src_doc_id in src_doc_ids and src_doc_id:  # range start
                        if marked_range_end < word_offset:
                            plagiated_words = True
                        marked_range_end = word_offset + self.n - 1
                    if plagiated_words:
                        dup_doc_plagiated_word_count += 1
                    dup_doc_total_word_count += 1
                    if marked_range_end == word_offset:  # range end
                        plagiated_words = False

            plagiate_info['total_words_count'] = dup_doc_total_word_count
            plagiate_info['plagiated_words_count'] = dup_doc_plagiated_word_count
            plagiate_info['source_articles'] = []

            for src_doc_id_i, src_doc_id in enumerate(src_doc_ids):
                article_info = dict()
                article_info['dbid'] = src_doc_id
                article_info['url'] = id_to_doc_attrs_map[src_doc_id]['url']
                article_info['date'] = id_to_doc_attrs_map[src_doc_id]['date']

                doc_source_ranges = source_ranges[src_doc_id][dup_doc_id]

                src_doc_total_word_count = 0
                src_doc_plagiated_word_count = 0
                for doc_sent_id, sent_words in enumerate(doc_sentences[src_doc_id]):
                    marked_sentence, marked_range_end = [], -1
                    plagiated_words = False
                    for word_offset, word in enumerate(sent_words):
                        if (doc_sent_id, word_offset) in doc_source_ranges:  # range start
                            if marked_range_end < word_offset:
                                plagiated_words = True
                            marked_range_end = word_offset + self.n - 1
                        if plagiated_words:
                            src_doc_plagiated_word_count += 1
                        src_doc_total_word_count += 1
                        if marked_range_end == word_offset:  # range end
                            plagiated_words = False

                article_info['total_words_count'] = src_doc_total_word_count
                article_info['plagiated_words_count'] = src_doc_plagiated_word_count

                plagiate_info['source_articles'].append(article_info)

            plagiates.append(plagiate_info)

        # Now we have a list of {plagiate_article, [source_articles]}, but we need to verify it's not the other way
        # around i.e. source_articles are actually sourcing from plagiate_article. We can use date information for that.
        checked_plagiates = []
        for plagiate in plagiates:
            parsed_plagiate_date = datetime.strptime(plagiate['date'], '%Y-%m-%d %H:%M:%S') if plagiate['date'] else None

            parsed_oldest_source_date = None
            for source in plagiate['source_articles']:
                parsed_source_date = datetime.strptime(source['date'], '%Y-%m-%d %H:%M:%S') if source['date'] else None
                if parsed_source_date and parsed_oldest_source_date:
                    parsed_oldest_source_date = min(parsed_oldest_source_date, parsed_source_date)
                elif parsed_source_date:
                    parsed_oldest_source_date = parsed_source_date

            if parsed_plagiate_date and parsed_oldest_source_date and parsed_plagiate_date < parsed_oldest_source_date:
                # We found a case when it's other way around.
                for source in plagiate['source_articles']:
                    new_source = {
                        'dbid': plagiate['dbid'],
                        'url': plagiate['url'],
                        'date': plagiate['date'],
                        'total_words_count': plagiate['total_words_count'],
                        'plagiated_words_count': plagiate['plagiated_words_count']
                    }

                    new_plagiate = {
                        'dbid': source['dbid'],
                        'url': source['url'],
                        'date': source['date'],
                        'total_words_count': source['total_words_count'],
                        'plagiated_words_count': source['plagiated_words_count'],
                        'source_articles': [new_source]
                    }
                    checked_plagiates.append(new_plagiate)
            else:
                checked_plagiates.append(plagiate)
        plagiates = checked_plagiates

        # Remove cases where plagiates are not above % treshold.
        plagiates = list(filter(
            lambda plagiate: (plagiate['plagiated_words_count']/plagiate['total_words_count']) > self.plagiate_threshold_word_ratio,
            plagiates))

        with open(self.output_json_file_path, 'w') as json_file:
            json_file.write(json.dumps(plagiates, indent=4, ensure_ascii=False))

        return plagiates

    def _write_graph_jsons(self, plagiates, id_to_doc_attrs_map):
        # Graph with number of articles taken from other domain.
        domains = set()
        links_by_article = dict()
        links_by_words = dict()

        for plagiate in plagiates:
            plagiate_domain = urlparse(plagiate['url']).netloc
            domains.add(plagiate_domain)

            for source in plagiate['source_articles']:
                source_domain = urlparse(source['url']).netloc
                domains.add(source_domain)

                key = (source_domain, plagiate_domain)
                if key in links_by_article:
                    links_by_article[key] += 1
                else:
                    links_by_article[key] = 1

                key = (source_domain, plagiate_domain)
                if key in links_by_words:
                    links_by_words[key] += source['plagiated_words_count']
                else:
                    links_by_words[key] = source['plagiated_words_count']

        # Compute statistics.
        article_count_per_domain = dict()
        for article_id, doc_attrs in id_to_doc_attrs_map.items():
            domain = doc_attrs['domain']
            if domain in article_count_per_domain:
                article_count_per_domain[domain] += 1
            else:
                article_count_per_domain[domain] = 1

        plagiated_article_count_per_domain = dict()
        for plagiate in plagiates:
            plagiate_domain = urlparse(plagiate['url']).netloc
            if plagiate_domain in plagiated_article_count_per_domain:
                plagiated_article_count_per_domain[plagiate_domain] += 1
            else:
                plagiated_article_count_per_domain[plagiate_domain] = 1

        main_source_per_domain = dict()
        for (source_domain, plagiate_domain), count in links_by_article.items():
            if plagiate_domain not in main_source_per_domain:
                main_source_per_domain[plagiate_domain] = (source_domain, count)
            else:
                current_source_domain, current_count = main_source_per_domain[plagiate_domain]
                if current_count < count:
                    main_source_per_domain[plagiate_domain] = (source_domain, count)

        plagiates_statistics = []
        for domain, article_count in article_count_per_domain.items():
            ratio = 'N/A'
            plagiated_count = 'N/A'
            if domain in plagiated_article_count_per_domain:
                plagiated_count = plagiated_article_count_per_domain[domain]
                ratio = '%.2f' % ((plagiated_count/article_count) * 100.0)
            main_source = 'N/A'
            if domain in main_source_per_domain:
                main_source = main_source_per_domain[domain]

            plagiates_statistics.append((domain, article_count, plagiated_count, ratio, main_source))

        # Sort by ratio.
        plagiates_statistics.sort(key=lambda x: -(float(x[3]) if x[3] != 'N/A' else -0.01))
        # End of statistics.

        json_data = {
            'nodes': [],
            'links': [],
            'statistics': plagiates_statistics,
        }

        colors = self.get_spaced_colors(len(domains))
        for index, domain in enumerate(domains):
            json_data['nodes'].append({
                'domain': domain,
                'name': domain,
                'id': domain,
                'color': '#%02x%02x%02x' % colors[index]
            })

        for (source_domain, plagiate_domain), count in links_by_article.items():
            if count >= self.GRAPH_LINK_BY_ARTICLES_THRESHOLD or not self.use_threshold:
                json_data['links'].append({
                    'value': count,
                    'source': source_domain,
                    'target': plagiate_domain
                })

        with open(self.output_json_graph_by_articles_file_path, 'w') as json_file:
            json_file.write(json.dumps(json_data, indent=4))

        json_data['links'] = []
        for (source_domain, plagiate_domain), count in links_by_words.items():
            if count >= self.GRAPH_LINK_BY_WORDS_THRESHOLD or not self.use_threshold:
                json_data['links'].append({
                    'value': count,
                    'source': source_domain,
                    'target': plagiate_domain
                })

        with open(self.output_json_graph_by_words_file_path, 'w') as json_file:
            json_file.write(json.dumps(json_data, indent=4))

    # Source: https://www.quora.com/How-do-I-generate-n-visually-distinct-RGB-colours-in-Python
    @staticmethod
    def get_spaced_colors(n):
        max_value = 255**3
        interval = int(max_value / n)
        colors = [hex(I)[2:].zfill(6) for I in range(0, max_value, interval)]

        return [(int(i[:2], 16), int(i[2:4], 16), int(i[4:], 16)) for i in colors]
