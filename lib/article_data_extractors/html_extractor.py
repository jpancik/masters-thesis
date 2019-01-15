import re

from bs4 import BeautifulSoup

from lib.articles_processor_domain_type.articles_processor_domain_type import DomainType


class HtmlExtractor:
    def __init__(self, domain_type: DomainType, file, debug):
        self.domain_type = domain_type
        self.soup = BeautifulSoup(file, 'html.parser')
        self.debug = debug

    def log_debug(self, msg):
        if self.debug:
            print(msg)

    def get_title(self):
        return self.get_attribute_with_regex(
            'title',
            self.domain_type.get_title_selector(),
            self.domain_type.get_title_regex())

    def get_author(self):
        return self.get_attribute_with_regex(
            'author',
            self.domain_type.get_author_selector(),
            self.domain_type.get_author_regex())

    def get_attribute_with_regex(self, attribute_name, selector, regex, select_index=0):
        self.log_debug('Using selector "%s" to extract %s.' % (selector, attribute_name))
        if not selector:
            return None

        selected_tags = self.soup.select(selector)
        if regex:
            self.log_debug('Using regex "%s" on %s.' % (regex, attribute_name))
            for tag in selected_tags:
                match = re.search(regex, str(tag), flags=re.MULTILINE)
                if match:
                    self.log_debug('Regex match is "%s" on %s.' % (match, attribute_name))
                    return match.group(1)
            return None
        else:
            if select_index < len(selected_tags):
                self.log_debug('Extracted %s "%s".'
                               % (attribute_name, selected_tags[select_index].get_text()))
                return selected_tags[select_index].get_text()
            else:
                self.log_debug('Select index is out of bounds.')
                return None


