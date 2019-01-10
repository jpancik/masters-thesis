import feedparser

from lib.domain_types.domain_type import DomainType


class RssParser(object):

    @staticmethod
    def get_article_urls(domain_type: DomainType):
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
                article['published_parsed'] = item['published_parsed']

            articles.append(article)

        return articles
