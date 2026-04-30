import unittest
from transport.segments.finished_segment import FinishedSegment
from transport.segments.segment import TYPE_FINISHED


class TestFinishedSegment(unittest.TestCase):

    def test_roundtrip(self):
        seg = FinishedSegment()

        raw = seg.to_bytes()
        parsed = FinishedSegment.from_bytes(raw)

        self.assertTrue(parsed.is_finished())

    def test_bytes_content(self):
        seg = FinishedSegment()

        raw = seg.to_bytes()

        self.assertEqual(raw, bytes([TYPE_FINISHED]))
        self.assertEqual(len(raw), 1)


if __name__ == "__main__":
    unittest.main()