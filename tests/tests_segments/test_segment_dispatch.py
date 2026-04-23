import unittest
import socket

from lib.transport.segments.segment import (
    Segment,
    TYPE_ACK,
    TYPE_DATA,
    TYPE_HANDSHAKE_REQUEST,
    TYPE_HANDSHAKE_RESPONSE,
)

from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.handshake_request_segment import HandshakeRequestSegment
from lib.transport.segments.handshake_response_segment import HandshakeResponseSegment


class TestSegmentDispatch(unittest.TestCase):

    def test_dispatch_ack(self):
        seg = AckSegment(ack=5)
        raw = seg.to_bytes()

        parsed = Segment.from_bytes(raw)

        self.assertIsInstance(parsed, AckSegment)
        self.assertEqual(parsed.ack, 5)

    def test_dispatch_data(self):
        seg = DataSegment(seq=1, data=b"hola", mf=1)
        raw = seg.to_bytes()

        parsed = Segment.from_bytes(raw)

        self.assertIsInstance(parsed, DataSegment)
        self.assertEqual(parsed.seq, 1)
        self.assertEqual(parsed.data, b"hola")
        self.assertEqual(parsed.mf, 1)

    def test_dispatch_handshake_request(self):
        host = socket.inet_aton("127.0.0.1")

        seg = HandshakeRequestSegment(
            operation=1,
            protocol=0,
            port=8080,
            host=host,
            filename="file.txt"
        )

        raw = seg.to_bytes()
        parsed = Segment.from_bytes(raw)

        self.assertIsInstance(parsed, HandshakeRequestSegment)
        self.assertEqual(parsed.port, 8080)
        self.assertEqual(parsed.filename, "file.txt")

    def test_dispatch_handshake_response(self):
        seg = HandshakeResponseSegment(port=9090)

        raw = seg.to_bytes()
        parsed = Segment.from_bytes(raw)

        self.assertIsInstance(parsed, HandshakeResponseSegment)
        self.assertEqual(parsed.port, 9090)

    def test_empty_data(self):
        with self.assertRaises(ValueError):
            Segment.from_bytes(b"")

    def test_unknown_type(self):
        raw = b"\xFF" + b"\x00" * 10

        with self.assertRaises(ValueError):
            Segment.from_bytes(raw)


if __name__ == "__main__":
    unittest.main()