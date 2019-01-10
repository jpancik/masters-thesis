from lib.article_url_retrievers.regex_parser import RegexParserArgs
from lib.domain_types.domain_type import DomainType


class LajkitCz(DomainType):
    def has_rss(self):
        return False

    def use_regex_parser_for_article_urls(self):
        return True

    def get_regex_parser_args(self):
        possible_sources = []

        for i in range(15):
            possible_sources.append('https://www.lajkit.cz/itemlist?limit=10&start=%s' % (i*10))

        return RegexParserArgs(
            possible_sources,
            r'^/[^/]*/item/[^/]*$',
            'https://www.lajkit.cz/')
