import argparse
from lib.application import constants

class BaseParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(add_help=False)
        self.parser.add_argument("-H", "--host", default=constants.DEFAULT_HOST, help=f"Server IP Address. Default: {constants.DEFAULT_HOST}")
        self.parser.add_argument("-p", "--port", type=int, default=constants.DEFAULT_PORT, help=f"Server port. Default: {constants.DEFAULT_PORT}")
        exclusive_params = self.parser.add_mutually_exclusive_group()
        exclusive_params.add_argument("-v", "--verbose", action="store_true", help="Increase verbosity")
        exclusive_params.add_argument("-q", "--quiet", action="store_true", help="Decrease verbosity")