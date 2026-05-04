import os
from lib.constants.socket_constants import BUFFER_SIZE
from lib.transport.rdt import ReliableProtocol

class FileManager:
    def __init__(self, protocol: ReliableProtocol, log, shutdown_event=None):
        self.protocol = protocol
        self.log = log
        self.shutdown_event = shutdown_event

    def send_file(self, path):
        try:
            with open(path, "rb") as file:
                while True and (self.shutdown_event is None or not self.shutdown_event.is_set()):
                    chunk = file.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    if self.protocol.send(chunk) == 1:
                        return

            if self.shutdown_event is not None and not self.shutdown_event.is_set():
                self.log.info("File transfer complete. Sending Finished segment")

            self.protocol.close()
            return

        except KeyboardInterrupt:
            self.log.info("File transfer interrupted")
            self.protocol.close()
        except Exception as error:
            self.log.error(f"Transfer failed: {error}")
            raise

    def receive_file(self, output_path):
        temp_file = output_path + ".tmp"

        try:
            with open(temp_file, "wb") as output_file:
                while True and (self.shutdown_event is None or not self.shutdown_event.is_set()):
                    chunk = self.protocol.recv()
                    if chunk is None:
                        break
                    output_file.write(chunk)

            if self.shutdown_event is not None and not self.shutdown_event.is_set():
                self.log.info("File transfer complete")
                os.rename(temp_file, output_path)
                return

            self.log.info("File transfer interrupted")
            self.protocol.close()
            if os.path.exists(temp_file):
                os.remove(temp_file)

        except Exception as error:
            self.log.error(f"File transfer failed: {error}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
