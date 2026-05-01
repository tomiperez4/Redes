class RdtSocket:
    def __init__(self, socket, log):
        self.socket = socket
        self.log = log


    def connect(self, address):
        retry_attempts = 0

        while retry_attempts < MAX_RETRIES:
            try:
                self.log.info("Sending handshake request to server")
                self.socket.sendto(h_packet.to_bytes(), address)
                raw_data, addr = self.skt.recvfrom(BUFFER_SIZE)
                response = Segment.from_bytes(raw_data)

                if response.is_handshake_response_segment():
                    self.log.info("Received handshake response from server")
                    return self.server_dir[0], response.get_port(), response.get_size()

                if response.is_handshake_error_segment():
                    self.log.error("Received handshake error from server. Aborting")
                    self.skt.close()
                    return None

            except socket.timeout:
                retry_attempts += 1
                self.log.warning(f"Handshake response from server not received. Attempt {retry_attempts}/5")
            except Exception as error:
                self.log.error(f"Unexpected error: {error}")

        self.log.error("Aborting. Max retries reached.")
        self.skt.close()
        return None
