from datetime import datetime
from time import mktime

import feedparser

from lib.articles_url_gatherer_domain_types.articles_url_gatherer_domain_type import DomainType


class RssParser:

    @staticmethod
    def get_article_metadata(domain_type: DomainType):
        if not domain_type.has_rss():
            raise AssertionError('Domain type does not have an RSS feed.')

        parsed_feed = feedparser.parse(domain_type.get_rss_url())

        articles = []
        for item in parsed_feed['entries']:
            article = dict()

            if 'title' in item:
                article['title'] = item['title']

            if 'link' in item:
                article['link'] = item['link']

            if 'published_parsed' in item:
                article['published_parsed'] = datetime.fromtimestamp(mktime(item['published_parsed']))

            articles.append(article)

        return articles
