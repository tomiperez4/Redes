import argparse

from lib.application import constants
from lib.application.base_parser import BaseParser

class ClientParser(BaseParser):
    def __init__(self, is_upload=True):
        super().__init__()
        self.final_parser = argparse.ArgumentParser(parents=[self.parser])

        if is_upload:
            self.final_parser.add_argument("-s", "--src", default=constants.DEFAULT_UPLOAD_FILEPATH, help=f"Source file path. Default: {constants.DEFAULT_UPLOAD_FILEPATH}")
        else:
            self.final_parser.add_argument("-d", "--dst", default=constants.DEFAULT_DOWNLOAD_FILEPATH, help=f"Destination path. Default: {constants.DEFAULT_DOWNLOAD_FILEPATH}")

        self.final_parser.add_argument("-n", "--name", default=constants.DEFAULT_FILENAME, help=f"File name. Default: {constants.DEFAULT_FILENAME}")
        self.final_parser.add_argument("-r", "--protocol", choices=['sw', 'gbn'], default=constants.DEFAULT_PROTOCOL, help=f"Protocol. Default: {constants.DEFAULT_PROTOCOL}")

    def parse(self):
        return self.final_parser.parse_args()