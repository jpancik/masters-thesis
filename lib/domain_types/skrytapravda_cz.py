from lib.domain_types.domain_type import DomainType


class SkrytapravdaCz(DomainType):
    def has_rss(self):
        return True

    def get_rss_url(self):
        return 'http://www.skrytapravda.cz/component/ninjarsssyndicator/?feed_id=1&format=raw'
