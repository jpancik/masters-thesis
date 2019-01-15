from abc import ABCMeta, abstractmethod


class DomainType:
    __metaclass__ = ABCMeta

    def get_name(self):
        return self.__class__.__name__

    @abstractmethod
    def has_rss(self):
        raise NotImplemented

    def get_rss_url(self):
        raise NotImplemented

    def use_regex_parser_for_article_urls(self):
        return False

    def get_regex_parser_args(self):
        raise NotImplemented

    def get_articles_metadata(self):
        raise NotImplemented
