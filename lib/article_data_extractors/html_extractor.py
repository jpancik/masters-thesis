import re
from datetime import datetime

from bs4 import BeautifulSoup

from lib.articles_processor_domain_type.json_domain_type import JsonDomainType, SelectorInfo


class HtmlExtractor:
    def __init__(self, domain_type: JsonDomainType, file, debug):
        self.domain_type = domain_type
        self.soup = BeautifulSoup(file, 'html.parser')
        self.debug = debug

    def log_debug(self, msg):
        if self.debug:
            print(msg)

    def get_title(self):
        selector_info = self.domain_type.get_attribute_selector_info('title')
        return self.get_attribute_with_selector_info(selector_info) if selector_info else None

    def get_author(self):
        selector_info = self.domain_type.get_attribute_selector_info('author')
        return self.get_attribute_with_selector_info(selector_info) if selector_info else None

    def get_date(self):
        selector_info = self.domain_type.get_attribute_selector_info('date')
        if not selector_info:
            return None

        date_format = selector_info.get_extra('date_format')
        parsed = self.get_attribute_with_selector_info(selector_info)
        return datetime.strptime(parsed, date_format) if date_format else parsed

    def get_prerex(self):
        selector_info = self.domain_type.get_attribute_selector_info('prerex')
        return self.get_attribute_with_selector_info(selector_info) if selector_info else None

    def get_keywords(self):
        selector_info = self.domain_type.get_attribute_selector_info('keywords')
        found = self.get_attribute_with_selector_info(selector_info) if selector_info else None

        if not found:
            return None

        found = found.replace('\n', '').replace('\t', '')
        remove_spaces_regex = re.compile(r'([ ][ ]+)', flags=re.MULTILINE)
        text_processed = remove_spaces_regex.sub(' ', found)
        return text_processed.strip()

    def get_article_content(self):
        selector = self.domain_type.get_article_content_selector()
        if not selector:
            return None

        self.log_debug('Using selector "%s" to extract %s.' % (selector, 'article'))
        article = self.soup.select(selector)
        #print(article)

        selected = ''.join([str(a) for a in article])
        # print(selected)
        article_soup = BeautifulSoup(selected, 'html.parser')
        #print(article_soup)
        remove_selectors = self.domain_type.get_article_remove_selectors()
        if remove_selectors:
            for selector_to_remove in remove_selectors:
                removed = [x.extract() for x in article_soup.select(selector_to_remove)]
                self.log_debug('Selector to remove %s removed: "%s".' % (selector_to_remove, removed))
        # print(article_soup)

        text = article_soup.get_text()
        # print(text)
        text_no_tabs_and_new_lines = text.replace('\n', ' ').replace('\t', ' ').replace(str(chr(160)), ' ')
        remove_spaces_regex = re.compile(r'([ ][ ]+)', flags=re.MULTILINE)
        text_processed = remove_spaces_regex.sub(' ', text_no_tabs_and_new_lines)
        return text_processed.strip()

    def get_attribute_with_selector_info(self, selector_info: SelectorInfo):
        if not selector_info:
            return None

        attribute_name = selector_info.get_name()
        selector = selector_info.get_selector()
        self.log_debug('Using selector "%s" to extract %s.' % (selector, attribute_name))
        if not selector:
            return None

        selected_tags = self.soup.select(selector)
        regex_raw_html = selector_info.get_regex_raw_html()
        text = None
        if regex_raw_html:
            self.log_debug('Using raw regex html "%s" on %s.' % (regex_raw_html, attribute_name))
            for tag in selected_tags:
                match = re.search(regex_raw_html, str(tag), flags=re.MULTILINE)
                if match:
                    self.log_debug('Raw regex match is "%s" on %s.' % (match, attribute_name))
                    text = match.group(1)
                    break
        else:
            select_index = 0
            if select_index < len(selected_tags):
                self.log_debug('Extracted %s "%s".'
                               % (attribute_name, selected_tags[select_index]))
                text = selected_tags[select_index].get_text()
            else:
                self.log_debug('Select index is out of bounds.')
                text = None

        regex_text = selector_info.get_regex_text()
        if text and regex_text:
            self.log_debug('Using text regex "%s" on %s.' % (regex_text, attribute_name))
            match = re.search(regex_text, text, flags=re.MULTILINE)
            if match:
                self.log_debug('Text regex match is "%s" on %s.' % (match, attribute_name))
                text = match.group(1)

        return text
