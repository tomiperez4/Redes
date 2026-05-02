import os
from constants.socket_constants import BUFFER_SIZE
from lib.transport.rdt import ReliableProtocol


class FileManager:
    def __init__(self, protocol: ReliableProtocol, log):
        self.protocol = protocol
        self.log = log

    def send_file(self, path):
        try:
            with open(path, "rb") as file:
                while True:
                    chunk = file.read(BUFFER_SIZE)

                    if not chunk:
                        return
                    self.protocol.send(chunk)
        except Exception as error:
            self.log.error(f"Transfer failed: {error}")
            raise

    def receive_file(self, output_path):
        temp_file = output_path + ".tmp"

        try:
            with open(temp_file, "wb") as output_file:
                while True:
                    chunk = self.protocol.recv()
                    output_file.write(chunk)

        except Exception as error:
            self.log.error(f"File transfer failed: {error}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
