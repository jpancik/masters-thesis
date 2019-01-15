from lib.articles_processor_domain_type.articles_processor_domain_type import DomainType


class JsonDomainType(DomainType):
    def __init__(self, name, data_dict):
        self.name = name
        self.data_dict = data_dict

    def get_name(self):
        return self.name

    def get_title_selector(self):
        return self.get_or_return_none('title')

    def get_title_regex(self):
        return self.get_or_return_none('title_regex')

    def get_author_selector(self):
        return self.get_or_return_none('author')

    def get_author_regex(self):
        return self.get_or_return_none('author_regex')

    def get_date_selector(self):
        return self.get_or_return_none('date')

    def get_date_regex(self):
        return self.get_or_return_none('date_regex')

    def get_prerex_selector(self):
        return self.get_or_return_none('prerex')

    def get_prerex_regex(self):
        return self.get_or_return_none('prerex_regex')

    def get_keywords_selector(self):
        return self.get_or_return_none('keywords')

    def get_keywords_regex(self):
        return self.get_or_return_none('keywords_regex')

    def get_article_content_selector(self):
        return self.get_or_return_none('article')

    def get_article_remove_selectors(self):
        return self.get_or_return_none('article_remove_selectors')

    def get_or_return_none(self, key):
        return self.data_dict[key] if key in self.data_dict else None

    @classmethod
    def get_json_domain_types(cls, loaded_json):
        out = {}

        for domain, data in loaded_json.items():
            out[domain] = cls(domain, data)

        return out
