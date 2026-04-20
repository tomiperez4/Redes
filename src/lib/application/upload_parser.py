from abc import abstractmethod
from src.lib.application.base_parser import BaseParser

class UploadParser(BaseParser):
    @abstractmethod
    def parse(self, file: bytes):
        return "Hi"

