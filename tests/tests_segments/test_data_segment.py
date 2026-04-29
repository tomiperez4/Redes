import unittest
from lib.segments.data_segment import DataSegment

class TestDataSegment(unittest.TestCase):

    def test_roundtrip(self):
        seg = DataSegment(5, b"hola", 1)

        raw = seg.to_bytes()
        parsed = DataSegment.from_bytes(raw)

        self.assertEqual(parsed.seq, 5)
        self.assertEqual(parsed.data, b"hola")
        self.assertEqual(parsed.mf, 1)

    def test_empty_payload(self):
        seg = DataSegment(0, b"", 0)

        parsed = DataSegment.from_bytes(seg.to_bytes())

        self.assertEqual(parsed.data, b"")


if __name__ == "__main__":
    unittest.main()