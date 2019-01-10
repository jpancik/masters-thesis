from lib.domain_types.domain_type import DomainType


class ZvedavecOrg(DomainType):
    def has_rss(self):
        return True

    def get_rss_url(self):
        return 'http://www.zvedavec.org/zvedavec_rdf_100.xml'
