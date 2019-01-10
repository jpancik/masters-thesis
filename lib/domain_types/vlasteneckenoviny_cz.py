from lib.article_url_retrievers.regex_parser import RegexParserArgs
from lib.domain_types.domain_type import DomainType


class VlasteneckenovinyCz(DomainType):
    def has_rss(self):
        return False

    def use_regex_parser_for_article_urls(self):
        return True

    def get_regex_parser_args(self):
        possible_sources = []

        for i in range(30):
            possible_sources.append('http://www.vlasteneckenoviny.cz/?paged=%s' % i)

        return RegexParserArgs(
            possible_sources,
            r'^http://www\.vlasteneckenoviny\.cz/\?p=\d+$'
        )
