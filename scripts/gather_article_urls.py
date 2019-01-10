import argparse

from lib.domain_types.nwoo_org import NwooOrg
from lib.domain_types.parlamentnilisty_cz import ParlamentnilistyCz
from lib.domain_types.prvnizpravy_cz import PrvnizpravyCz
from lib.domain_types.rukojmi_cz import RukojmiCz
from lib.domain_types.securitymagazin_cz import SecuritymagazinCz
from lib.domain_types.skrytapravda_cz import SkrytapravdaCz
from lib.domain_types.svetkolemnas_info import SvetkolemnasInfo
from lib.domain_types.vlasteneckenoviny_cz import VlasteneckenovinyCz
from lib.domain_types.withform_cz import WithformCz
from lib.domain_types.zvedavec_org import ZvedavecOrg
from lib.rss_parser import RssParser


class GatherArticleUrls(object):
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
            PrvnizpravyCz(),
        ]


if __name__ == '__main__':
    gather_article_urls = GatherArticleUrls()
    gather_article_urls.run()
