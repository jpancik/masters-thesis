from lib.articles_processor_domain_type.articles_processor_domain_type import DomainType


class SelectorInfo:
    def __init__(self, name, dict):
        self.name = name
        self.dict = dict

    def get_name(self):
        return self.name

    def get_selector(self):
        return self.dict.get('selector')

    def get_regex_raw_html(self):
        return self.dict.get('regex_raw_html')

    def get_regex_text(self):
        return self.dict.get('regex_text')

    def get_extra(self, key):
        return self.dict.get(key)


class JsonDomainType(DomainType):
    def __init__(self, name, data_dict):
        self.name = name
        self.data_dict = data_dict

    def get_name(self):
        return self.name

    def get_attribute_selector_info(self, attribute_name) -> SelectorInfo:
        return SelectorInfo(attribute_name, self.data_dict[attribute_name]) if attribute_name in self.data_dict else None

    def get_article_content_selector(self):
        dict = self.data_dict.get('article')
        return dict.get('selector') if dict else None

    def get_article_remove_selectors(self):
        dict = self.data_dict.get('article')
        return dict.get('remove_selectors') if dict else None

    def get_article_remove_regexes(self):
        dict = self.data_dict.get('article')
        return dict.get('remove_regexes') if dict else None

    @classmethod
    def get_json_domain_types(cls, loaded_json):
        out = {}

        for domain, data in loaded_json.items():
            out[domain] = cls(domain, data)

        return out
