from lib.domain_types.domain_type import DomainType


class ParlamentnilistyCz(DomainType):
    def has_rss(self):
        return True

    def get_rss_url(self):
        return 'https://www.parlamentnilisty.cz/export/rss.aspx'
