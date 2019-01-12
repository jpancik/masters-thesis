import argparse
import json

from lib.article_url_retrievers.regex_parser import RegexParser
from lib.article_url_retrievers.rss_parser import RssParser
from lib.domain_types.json_domain_type import JsonDomainType


class GatherArticleUrls:
    def __init__(self):
        self.args = self.parse_commandline()
        self.domain_types = self._init_domain_type()

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        return parser.parse_args()

    def run(self):
        with open('data/website_article_urls_descriptions.json', 'r') as file:
            json_data = json.load(file)
            self.domain_types += JsonDomainType.get_json_domain_types(json_data)

        for domain_type in self.domain_types:
            # if domain_type.get_name() != 'ipribeh.cz':
            #     continue

            print('Gathering for: %s' % domain_type.get_name())

            if domain_type.has_rss():
                article_urls = RssParser.get_article_urls(domain_type)

                import pprint
                pprint.pprint(article_urls)
                print('Size retrieved: %s.' % len(article_urls))
            else:
                if domain_type.use_regex_parser_for_article_urls():
                    article_urls = RegexParser.get_article_urls(domain_type)
                else:
                    article_urls = domain_type.get_article_urls()

                import pprint
                pprint.pprint(article_urls)
                print('Size retrieved: %s.' % len(article_urls))

    def _init_domain_type(self):
        return []


if __name__ == '__main__':
    gather_article_urls = GatherArticleUrls()
    gather_article_urls.run()
