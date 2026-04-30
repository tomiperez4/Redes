import unittest
from transport.segments.ack_segment import AckSegment


class TestAckSegment(unittest.TestCase):

    def test_roundtrip(self):
        seg = AckSegment(10)

        raw = seg.to_bytes()
        parsed = AckSegment.from_bytes(raw)

        self.assertEqual(parsed.ack, 10)


if __name__ == "__main__":
    unittest.main()