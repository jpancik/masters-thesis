from abc import ABCMeta, abstractmethod


class DomainType:
    __metaclass__ = ABCMeta

    def get_name(self):
        return self.__class__.__name__

    def get_title_selector(self):
        return None

    def get_title_regex(self):
        return None

    def get_author_selector(self):
        return None

    def get_author_regex(self):
        return None

    def get_date_selector(self):
        return None

    def get_date_regex(self):
        return None

    def get_date_format(self):
        return None

    def get_prerex_selector(self):
        return None

    def get_prerex_regex(self):
        return None

    def get_keywords_selector(self):
        return None

    def get_keywords_regex(self):
        return None

    def get_article_content_selector(self):
        return None

    def get_article_remove_selectors(self):
        return None
