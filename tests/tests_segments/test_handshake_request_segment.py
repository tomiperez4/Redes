import unittest
import socket
from transport.segments.handshake_request_segment import HandshakeRequestSegment


class TestHandshakeRequest(unittest.TestCase):

    def test_roundtrip(self):
        host = socket.inet_aton("127.0.0.1")

        seg = HandshakeRequestSegment(
            operation=1,
            protocol=0,
            port=8080,
            host=host,
            filename="file.txt"
        )

        raw = seg.to_bytes()
        parsed = HandshakeRequestSegment.from_bytes(raw)

        self.assertEqual(parsed.operation, 1)
        self.assertEqual(parsed.protocol, 0)
        self.assertEqual(parsed.port, 8080)
        self.assertEqual(parsed.host, host)
        self.assertEqual(parsed.filename, "file.txt")

    def test_empty_filename(self):
        host = socket.inet_aton("127.0.0.1")

        seg = HandshakeRequestSegment(
            operation=0,
            protocol=1,
            port=1234,
            host=host,
            filename=""
        )

        parsed = HandshakeRequestSegment.from_bytes(seg.to_bytes())

        self.assertIsNone(parsed.filename)

    def test_invalid_type(self):
        import struct

        # tipo incorrecto 99
        raw = struct.pack("!B B B H 4s", 99, 0, 0, 1234, socket.inet_aton("127.0.0.1"))

        with self.assertRaises(ValueError):
            HandshakeRequestSegment.from_bytes(raw)


if __name__ == "__main__":
    unittest.main()