from abc import ABCMeta, abstractmethod

class DomainType:
    __metaclass__ = ABCMeta

    def get_name(self):
        return self.__class__.__name__
