from lib.domain_types.domain_type import DomainType


class HalonovinyCz(DomainType):
    def has_rss(self):
        return True

    def get_rss_url(self):
        return 'http://www.halonoviny.cz/articles/newsfeed.rss'
