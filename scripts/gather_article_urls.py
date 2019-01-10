import argparse

from lib.article_url_retrievers.regex_parser import RegexParser
from lib.domain_types.ozonyx_cz import OzonyxCz
from lib.domain_types.protiproud_cz import ProtiproudCz
from lib.article_url_retrievers.rss_parser import RssParser


class GatherArticleUrls:
    def __init__(self):
        self.args = self.parse_commandline()
        self.domain_types = self._init_domain_type()

    @staticmethod
    def parse_commandline():
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        return parser.parse_args()

    def run(self):
        for domain_type in self.domain_types:
            print('Gathering for: %s' % domain_type.__class__.__name__)

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
        return [
            # ParlamentnilistyCz(),
            # NwooOrg(),
            # ZvedavecOrg(),
            # WithformCz(),
            # VlasteneckenovinyCz(),
            # SvetkolemnasInfo(),
            # SkrytapravdaCz(),
            # SecuritymagazinCz(),
            # RukojmiCz(),
            # PrvnizpravyCz(),
            ProtiproudCz(),
            OzonyxCz(),
        ]


if __name__ == '__main__':
    gather_article_urls = GatherArticleUrls()
    gather_article_urls.run()
