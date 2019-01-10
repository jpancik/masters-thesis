from lib.domain_types.domain_type import DomainType


class NwooOrg(DomainType):
    def has_rss(self):
        return True

    def get_rss_url(self):
        return 'http://www.nwoo.org/feed/'
