import argparse
import json
import os
import traceback

import psycopg2

from lib.article_data_extractors.html_extractor import HtmlExtractor
from lib.articles_processor_domain_type.articles_processor_domain_type import DomainType
from lib.articles_processor_domain_type.json_domain_type import JsonDomainType


class ProcessArticles:
    RAW_HTML_FOLDER_PREFIX = 'data/raw_articles/'
    PROCESSED_HTML_FOLDER_PREFIX = 'data/processed_articles/'

    def __init__(self):
        self.args = self.parse_commandline()
        self.domain_types = self._init_domain_types()
        self.db_con = psycopg2.connect("dbname=crawlerdb user=jurajpancik")

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--debug', action='store_true', default=False, help='Debug HTML parsing.')
        parser.add_argument('--domain', type=str, default=None, help='Specify domain to gather.')
        parser.add_argument('--limit', type=int, default=None, help='Specify limit of how many articles to process.')
        parser.add_argument('--sql-conditions', type=str, default=None, help='Specify custom SQL conditions. (a is article_metadata and r is article_raw_html, e.g. "AND a.id = 15")')
        parser.add_argument('--dry-run', action='store_true', default=False, help='Don\'t store output and print it to stdout.')
        parser.add_argument('--process-new', action='store_true', default=False, help='Process only new articles.')
        parser.add_argument('--begin-id', type=int, default=None, help='Specify begin id of articles to process.')
        parser.add_argument('--end-id', type=int, default=None, help='Specify end if of articles to process.')
        return parser.parse_args()

    def run(self):
        cur = self.db_con.cursor()
        sql_query, article_begin_id = self._construct_query(cur)
        print('Executing query "%s".' % sql_query)

        cur.execute(sql_query)
        articles_raw_data = cur.fetchall()
        processed_articles_count = 0
        processed_articles_last_id = 0
        for index, (id, website_domain, url, title, publication_date, filename, created_at) in enumerate(
                articles_raw_data):
            print('(%s/%s) Started processing: %s from %s.' % (index + 1, len(articles_raw_data), filename, url))
            if website_domain not in self.domain_types:
                print('(%s/%s) Unsupported website domain: %s for article with id %s.'
                      % (index + 1, len(articles_raw_data), website_domain, id))
                continue
            domain_type = self.domain_types[website_domain]

            try:
                with open(filename, 'r') as file:
                    html_extractor = HtmlExtractor(domain_type, file, created_at, self.args.debug)

                    out = dict()

                    article_title = html_extractor.get_title()
                    if article_title:
                        out['title'] = article_title

                    article_author = html_extractor.get_author()
                    if article_author:
                        out['author'] = article_author

                    article_publication_date = html_extractor.get_date()
                    if article_publication_date:
                        out['publication_date'] = str(article_publication_date)

                    article_perex = html_extractor.get_perex()
                    if article_perex:
                        out['perex'] = article_perex

                    article_keywords = html_extractor.get_keywords()
                    if article_keywords:
                        out['keywords'] = article_keywords

                    article_content =  html_extractor.get_article_content()
                    if article_content:
                        out['article_content'] = article_content

                    json_data = json.dumps(out, indent=4, ensure_ascii=False)
                    if self.args.dry_run:
                        print(json_data)
                    else:
                        self._store_processed_article(id, domain_type, json_data)

                processed_articles_count += 1
                processed_articles_last_id = id
                print('(%s/%s) Finished processing: %s from %s.' % (index + 1, len(articles_raw_data), filename, url))
            except Exception as e:
                print('(%s/%s) Error processing %s from %s with message: %s.'
                      % (index + 1, len(articles_raw_data), filename, url, e))
                traceback.print_exc()

        if self.args.process_new:
            cur.execute('INSERT INTO article_processing_summary(total_articles_processed_count, start_article_id, end_article_id) VALUES (%s, %s, %s)',
                        (processed_articles_count, article_begin_id, processed_articles_last_id))
            self.db_con.commit()

        cur.close()
        self._close_db_connection()

    def _construct_query(self, cur):
        # ONLY FOR DEBUGGING
        names = ['parlamentnilisty.cz', 'nwoo.org', 'www.zvedavec.org',
                 'www.vlasteneckenoviny.cz', 'www.svetkolemnas.info', 'www.skrytapravda.cz',
                 'www.securitymagazin.cz', 'www.rukojmi.cz', 'www.prvnizpravy.cz',
                 'www.protiproud.cz', 'www.nejvic-info.cz', 'www.mikan.cz',
                 'www.lajkit.cz', 'www.krajskelisty.cz', 'www.isstras.eu/cs',
                 'www.freepub.cz', 'www.freeglobe.cz', 'www.euserver.cz',
                 'www.euportal.cz', 'www.eportal.cz', 'www.czechfreepress.cz',
                 'www.ctusi.info', 'www.casopis-sifra.cz', 'www.bezpolitickekorektnosti.cz',
                 'www.alternativnimagazin.cz', 'wertyzreport.cz', 'veksvetla.cz',
                 'tadesco.cz', 'svobodnenoviny.eu', 'stredoevropan.cz',
                 'stalo-se.cz', 'proevropu.com', 'procproto.cz',
                 'pravyprostor.cz', 'pravdive.eu', 'outsidermedia.cz',
                 'www.halonoviny.cz', 'orgo-net.blogspot.com', 'news.e-republika.cz',
                 'morezprav.cz', 'megazine.cz', 'jackings.net',
                 'ipribeh.cz', 'instory.cz', 'farmazdravi.cz',
                 'www.eurasia24.cz', 'cz.sputniknews.com', 'ceskozdrave.cz',
                 'ceskoaktualne.cz', 'aeronet.cz', 'ac24.cz',
                 'www.duchdoby.cz', 'zpravy.dt24.cz', 'e-republika.cz',
                 'www.eurabia.cz', 'eurodenik.cz', 'eurozpravy.cz',
                 'leva-net.webnode.cz', 'www.necenzurujeme.cz', 'www.novaburzoazie.com',
                 'vasevec.parlamentnilisty.cz'
             ]
        name_index = len(names) - 1
        debugging_domain = names[name_index]

        begin_id = None
        end_id = None
        if self.args.process_new:
            cur.execute('SELECT s.end_article_id FROM article_processing_summary s ORDER BY s.end_id DESC LIMIT 1')
            row = cur.fetchone()
            if row:
                begin_id = row[0] + 1
            else:
                begin_id = 0
        begin_id = self.args.begin_id if self.args.begin_id else begin_id
        end_id = self.args.end_id if self.args.end_id else end_id

        base_query = (
            'SELECT a.id, a.website_domain, a.url, a.title, a.publication_date, r.filename, r.created_at '
            'FROM article_metadata a '
            'JOIN article_raw_html r ON r.article_metadata_id = a.id '
            'WHERE 1=1%s'
        )
        sql_conditions = ' AND a.website_domain = \'%s\'' % self.args.domain if self.args.domain else ' AND a.website_domain = \'%s\'' % debugging_domain
        sql_conditions += ' AND a.id >= %s' % begin_id if begin_id else ''
        sql_conditions += ' AND a.id <= %s' % end_id if end_id else ''
        sql_conditions += self.args.sql_conditions if self.args.sql_conditions else ''
        sql_conditions += ' LIMIT %s' % self.args.limit if self.args.limit else ''

        return base_query % sql_conditions, begin_id

    def _store_processed_article(self, id, domain_type: DomainType, json_data):
        folder_name = os.path.join(self.PROCESSED_HTML_FOLDER_PREFIX, domain_type.get_name())

        if not os.path.isdir(folder_name):
            os.makedirs(folder_name)

        filename = '%s_%s.json' % (id, domain_type.get_name().replace('/', '-'))
        full_path = os.path.join(folder_name, filename)

        with open(full_path, 'w') as file:
            file.write(json_data)

    def _init_domain_types(self):
        out = dict()

        with open('data/website_article_format_descriptions.json', 'r') as file:
            json_data = json.load(file)
            out.update(JsonDomainType.get_json_domain_types(json_data))

        return out

    def _close_db_connection(self):
        if self.db_con:
            self.db_con.close()


if __name__ == '__main__':
    process_articles = ProcessArticles()
    process_articles.run()
