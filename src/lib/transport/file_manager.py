import os

from lib.common import BUFFER_SIZE
from lib.transport.rdt import ReliableProtocol


class FileManager:
    """
    Handles file transfer over a reliable protocol.
    """

    def __init__(self, protocol: ReliableProtocol, log, shutdown_event=None):
        """
        Initializes the file manager.
        'shutdown_event' indicates an optional event that causes the transfer to stop.
        """
        self.protocol = protocol
        self.log = log
        self.shutdown_event = shutdown_event

    def send_file(self, path):
        """
        Sends a file by reading it in chunks and uses the specified protocol.
        """
        try:
            with open(path, "rb") as file:
                while True and (
                    self.shutdown_event is None or not self.shutdown_event.is_set()
                ):
                    chunk = file.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    if self.protocol.send(chunk) == 1:
                        return

            if self.shutdown_event is None or not self.shutdown_event.is_set():
                self.log.info("File transfer complete. Sending FINISHED segment")

            self.protocol.close()
            return

        except KeyboardInterrupt:
            self.log.info("File transfer interrupted")
            self.protocol.close()
        except Exception as error:
            self.log.error(f"Transfer failed: {error}")
            raise

    def receive_file(self, output_path, file_size):
        """
        Receives a file and writes it to disk.
        Data is received in chunks and written to a temporary file.
        If the transfer completes successfully, the temp file is renamed.
        """
        temp_file = output_path + ".tmp"

        try:
            with open(temp_file, "wb") as output_file:
                while True and (
                    self.shutdown_event is None or not self.shutdown_event.is_set()
                ):
                    chunk = self.protocol.recv()
                    if chunk is None:
                        break
                    output_file.write(chunk)

            actual_file_size = os.path.getsize(temp_file)

            if (
                self.shutdown_event is None or not self.shutdown_event.is_set()
            ) and actual_file_size == file_size:
                self.log.info("File transfer complete")
                os.rename(temp_file, output_path)
                return

            self.log.info("File transfer interrupted")
            if os.path.exists(temp_file):
                os.remove(temp_file)

        except KeyboardInterrupt:
            self.__handle_transfer_interrupt(temp_file)

        except Exception as error:
            self.log.error(f"File transfer failed: {error}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def __handle_transfer_interrupt(self, temp_file):
        """
        Handles interruption during file transfer.

        Cleans up temporary file and closes protocol.
        """
        self.log.info("File transfer interrupted")
        self.protocol.close()
        if os.path.exists(temp_file):
            os.remove(temp_file)
