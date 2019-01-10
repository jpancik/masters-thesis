from lib.domain_types.domain_type import DomainType


class KrajskelistyCz(DomainType):
    def has_rss(self):
        return True

    def get_rss_url(self):
        return 'http://www.krajskelisty.cz/export/rss.xml'

