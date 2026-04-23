import unittest
from lib.transport.segments.handshake_response_segment import HandshakeResponseSegment


class TestHandshakeResponse(unittest.TestCase):

    def test_roundtrip(self):
        seg = HandshakeResponseSegment(port=9090)

        raw = seg.to_bytes()
        parsed = HandshakeResponseSegment.from_bytes(raw)

        self.assertEqual(parsed.port, 9090)

    def test_invalid_type(self):
        import struct

        raw = struct.pack("!B H", 99, 8080)

        with self.assertRaises(ValueError):
            HandshakeResponseSegment.from_bytes(raw)

    def test_incomplete_data(self):
        raw = b"\x03"  # falta el puerto

        with self.assertRaises(ValueError):
            HandshakeResponseSegment.from_bytes(raw)


if __name__ == "__main__":
    unittest.main()