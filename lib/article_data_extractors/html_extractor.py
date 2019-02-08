import re
import traceback
from datetime import datetime

from bs4 import BeautifulSoup

from lib.articles_processor_domain_type.json_domain_type import JsonDomainType, SelectorInfo


class HtmlExtractor:
    def __init__(self, domain_type: JsonDomainType, file, parsed_at, debug):
        self.domain_type = domain_type
        self.soup = BeautifulSoup(file, 'html.parser')
        self.parsed_at = parsed_at
        self.debug = debug

    def _log_debug(self, msg):
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

        parsed = self.get_attribute_with_selector_info(selector_info)
        if not parsed:
            return None

        replace = selector_info.get_extra('replace')
        if replace:
            for r in replace:
                new = r.get('new')
                if new:
                    new = self.parsed_at.strftime(new)
                    old = r.get('old')
                    self._log_debug('Replacing "%s" with "%s" in date.' % (old, new))
                    parsed = parsed.replace(old, new)

        date_format = selector_info.get_extra('date_format')
        try:
            return datetime.strptime(parsed, date_format) if date_format else parsed
        except Exception as e:
            traceback.print_exc()
            return parsed

    def get_perex(self):
        selector_info = self.domain_type.get_attribute_selector_info('perex')
        return self.get_attribute_with_selector_info(selector_info) if selector_info else None

    def get_keywords(self):
        selector_info = self.domain_type.get_attribute_selector_info('keywords')
        return self.get_attribute_with_selector_info(selector_info) if selector_info else None

    def get_article_content(self):
        selector = self.domain_type.get_article_content_selector()
        if not selector:
            return None

        self._log_debug('Using selector "%s" to extract %s.' % (selector, 'article'))
        article = self.soup.select(selector)
        #print(article)

        #print(article_soup)
        remove_selectors = [
            'style', 'script'
        ]
        if self.domain_type.get_article_remove_selectors():
            remove_selectors.extend(self.domain_type.get_article_remove_selectors())
        if remove_selectors:
            for a in article:
                for selector_to_remove in remove_selectors:
                    removed = [x.extract() for x in a.select(selector_to_remove)]
                    self._log_debug('Selector to remove %s removed: "%s".' % (selector_to_remove, removed))
        self._log_debug(article)

        text = ' '.join([a.get_text() for a in article])
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
        self._log_debug('Using selector "%s" to extract %s.' % (selector, attribute_name))
        if not selector:
            return None

        selected_tags = self.soup.select(selector)
        regex_raw_html = selector_info.get_regex_raw_html()
        text = None
        if regex_raw_html:
            self._log_debug('Using raw regex html "%s" on %s with text "%s".'
                            % (regex_raw_html, attribute_name, [str(tag) for tag in selected_tags]))
            for tag in selected_tags:
                match = re.search(regex_raw_html, str(tag), flags=re.MULTILINE)
                if match:
                    self._log_debug('Raw regex match is "%s" on %s.' % (match, attribute_name))
                    text = match.group(1)
                    break
        else:
            select_index = 0
            if select_index < len(selected_tags):
                self._log_debug('Extracted %s "%s".'
                                % (attribute_name, selected_tags[select_index]))
                text = selected_tags[select_index].get_text()
            else:
                self._log_debug('Select index is out of bounds.')
                text = None

        regex_text = selector_info.get_regex_text()
        if text and regex_text:
            self._log_debug('Using text regex "%s" on %s with text "%s".' % (regex_text, attribute_name, text))
            match = re.search(regex_text, text, flags=re.MULTILINE)
            if match:
                self._log_debug('Text regex match is "%s" on %s.' % (match, attribute_name))
                text = match.group(1)

        if text:
            text_no_tabs_and_new_lines = text.replace('\n', ' ').replace('\t', ' ').replace(str(chr(160)), ' ')
            remove_spaces_regex = re.compile(r'([ ][ ]+)', flags=re.MULTILINE)
            text_processed = remove_spaces_regex.sub(' ', text_no_tabs_and_new_lines)
            return text_processed.strip()
        else:
            return None
