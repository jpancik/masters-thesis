from lib.article_url_retrievers.regex_parser import RegexParserArgs
from lib.domain_types.domain_type import DomainType


class SvetkolemnasInfo(DomainType):
    def has_rss(self):
        return False

    def use_regex_parser_for_article_urls(self):
        return True

    def get_regex_parser_args(self):
        return RegexParserArgs(
            ['http://www.svetkolemnas.info/'],
            r'^/novinky/',
            'http://www.svetkolemnas.info/'
        )
