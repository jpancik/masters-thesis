from abc import ABCMeta, abstractmethod


class DomainType:

    __metaclass__ = ABCMeta

    @abstractmethod
    def has_rss(self):
        raise NotImplemented

    def get_rss_url(self):
        raise NotImplemented

    def use_regex_parser_for_article_urls(self):
        return False

    def get_regex_parser_args(self):
        raise NotImplemented

    def get_article_urls(self):
        raise NotImplemented
