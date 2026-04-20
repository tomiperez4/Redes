from abc import abstractmethod, ABC


class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw: bytes): pass