import argparse

from lib.application import constants
from lib.application.base_parser import BaseParser

class ServerParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.final_parser = argparse.ArgumentParser(parents=[self.parser])
        self.final_parser.add_argument("-s", "--storage", default=constants.DEFAULT_STORAGE_PATH, help=f"Storage directory path. Default: {constants.DEFAULT_STORAGE_PATH}")

    def parse(self):
        return self.final_parser.parse_args()