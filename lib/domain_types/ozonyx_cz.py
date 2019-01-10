from lib.article_url_retrievers.regex_parser import RegexParserArgs
from lib.domain_types.domain_type import DomainType


class OzonyxCz(DomainType):
    def has_rss(self):
        return False

    def use_regex_parser_for_article_urls(self):
        return True

    def get_regex_parser_args(self):
        possible_sources = []

        for i in range(15):
            possible_sources.append('http://www.ozonyx.cz/index.php/page/%s/' % i)

        return RegexParserArgs(
            possible_sources,
            r'^http://www\.ozonyx\.cz/index\.php/(\d{4})/(\d{2})/(\d{2})/[^/]*/$',
            None,
            True)
