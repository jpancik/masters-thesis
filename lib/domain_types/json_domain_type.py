from lib.article_url_retrievers.regex_parser import RegexParserArgs
from lib.domain_types.domain_type import DomainType


class JsonDomainType(DomainType):
    def __init__(self, name, data_dict):
        self.name = name
        self.data_dict = data_dict

    def get_name(self):
        return self.name

    def has_rss(self):
        return 'rss_url' in self.data_dict and self.data_dict['rss_url']

    def get_rss_url(self):
        return self.data_dict['rss_url'] if 'rss_url' in self.data_dict else None

    def use_regex_parser_for_article_urls(self):
        return self.data_dict['use_regex_parser'] if 'use_regex_parser' in self.data_dict else False

    def get_regex_parser_args(self):
        return RegexParserArgs(
            self.data_dict['possible_sources'],
            self.data_dict['regex'],
            self.data_dict['domain_prefix'] if 'domain_prefix' in self.data_dict else None,
            self.data_dict['parse_date'] if 'parse_date' in self.data_dict else False)

    def get_article_urls(self):
        raise NotImplemented

    @classmethod
    def get_json_domain_types(cls, loaded_json):
        out = []

        for domain, data in loaded_json.items():
            out.append(cls(domain, data))

        return out
