from lib.domain_types.domain_type import DomainType


class PrvnizpravyCz(DomainType):
    def has_rss(self):
        return True

    def get_rss_url(self):
        return 'http://www.prvnizpravy.cz/repository/rss/zpravy_all_cs.xml'
