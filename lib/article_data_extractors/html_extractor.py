import re
from datetime import datetime

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

    def get_date(self):
        date_format = self.domain_type.get_date_format()
        parsed = self.get_attribute_with_regex(
            'date',
            self.domain_type.get_date_selector(),
            self.domain_type.get_date_regex())
        return datetime.strptime(parsed, date_format) if date_format else parsed

    def get_prerex(self):
        return self.get_attribute_with_regex(
            'prerex',
            self.domain_type.get_prerex_selector(),
            self.domain_type.get_prerex_regex())

    def get_keywords(self):
        return self.get_attribute_with_regex(
            'keywords',
            self.domain_type.get_keywords_selector(),
            self.domain_type.get_keywords_regex())

    def get_article(self):
        selector = self.domain_type.get_article_content_selector()
        self.log_debug('Using selector "%s" to extract %s.' % (selector, 'article'))
        article = self.soup.select(selector)
        #print(article)

        selected = ''.join([str(a) for a in article])
        # print(selected)
        article_soup = BeautifulSoup(selected, 'html.parser')
        #print(article_soup)
        for selector_to_remove in self.domain_type.get_article_remove_selectors():
            removed = [x.extract() for x in article_soup.select(selector_to_remove)]
            self.log_debug('Selector to remove %s removed: "%s".' % (selector_to_remove, removed))
        # print(article_soup)

        text = article_soup.get_text()
        # print(text)
        text_no_tabs_and_new_lines = text.replace('\n', ' ').replace('\t', ' ').replace(str(chr(160)), ' ')
        remove_spaces_regex = re.compile(r'([ ][ ]+)', flags=re.MULTILINE)
        text_processed = remove_spaces_regex.sub(' ', text_no_tabs_and_new_lines)
        return text_processed

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


