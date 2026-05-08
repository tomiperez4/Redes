# tests/test_segments.py

import pytest

from lib.transport.segments.segment import Segment
from lib.transport.segments.data_segment import DataSegment
from lib.transport.segments.ack_segment import AckSegment
from lib.transport.segments.finished_segment import FinishedSegment
from lib.transport.segments.syn_segment import SynSegment
from lib.transport.segments.synack import SynackSegment

from lib.transport.segments.constants import (
    ACK_FLAG,
    SYN_FLAG,
    FIN_FLAG,
    SYN_ACK_FLAG,
)

# =========================================================
# ACK SEGMENT
# =========================================================


def test_ack_segment_fields():
    seg = AckSegment(7)

    assert seg.seq == 7
    assert seg.get_ack_number() == 7
    assert seg.get_flags() == ACK_FLAG
    assert seg.get_payload() == b""
    assert seg.is_ack_segment()


def test_ack_segment_serialization():
    seg = AckSegment(5)

    raw = seg.to_bytes()
    parsed = Segment.from_bytes(raw)

    assert isinstance(parsed, AckSegment)
    assert parsed.seq == 5
    assert parsed.is_ack_segment()


# =========================================================
# DATA SEGMENT
# =========================================================


def test_data_segment_fields():
    payload = b"hello"
    seg = DataSegment(3, payload)

    assert seg.seq == 3
    assert seg.get_payload() == payload
    assert seg.get_flags() == 0
    assert seg.is_data_segment()


def test_data_segment_serialization():
    payload = b"network-data"
    seg = DataSegment(1, payload)

    raw = seg.to_bytes()
    parsed = Segment.from_bytes(raw)

    assert isinstance(parsed, DataSegment)
    assert parsed.seq == 1
    assert parsed.get_payload() == payload
    assert parsed.is_data_segment()


# =========================================================
# FINISHED SEGMENT
# =========================================================


def test_finished_segment_fields():
    seg = FinishedSegment(9)

    assert seg.seq == 9
    assert seg.get_flags() == FIN_FLAG
    assert seg.get_payload() == b""
    assert seg.is_finished_segment()


def test_finished_segment_serialization():
    seg = FinishedSegment(2)

    raw = seg.to_bytes()
    parsed = Segment.from_bytes(raw)

    assert isinstance(parsed, FinishedSegment)
    assert parsed.seq == 2
    assert parsed.is_finished_segment()


# =========================================================
# SYN SEGMENT
# =========================================================


def test_syn_segment_fields():
    seg = SynSegment(protocol=1, seq=4)

    assert seg.seq == 4
    assert seg.get_protocol() == 1
    assert seg.get_flags() == SYN_FLAG
    assert seg.is_syn_segment()


def test_syn_segment_serialization():
    seg = SynSegment(protocol=2, seq=8)

    raw = seg.to_bytes()
    parsed = Segment.from_bytes(raw)

    assert isinstance(parsed, SynSegment)
    assert parsed.seq == 8
    assert parsed.get_protocol() == 2
    assert parsed.is_syn_segment()


# =========================================================
# SYNACK SEGMENT
# =========================================================


def test_synack_segment_fields():
    seg = SynackSegment(port=9090, seq=1)

    assert seg.seq == 1
    assert seg.get_port() == 9090
    assert seg.get_flags() == SYN_ACK_FLAG
    assert seg.is_synack_segment()


def test_synack_segment_serialization():
    seg = SynackSegment(port=8080, seq=6)

    raw = seg.to_bytes()
    parsed = Segment.from_bytes(raw)

    assert isinstance(parsed, SynackSegment)
    assert parsed.seq == 6
    assert parsed.get_port() == 8080
    assert parsed.is_synack_segment()


# =========================================================
# SEGMENT BASE CLASS
# =========================================================


def test_segment_from_bytes_with_short_data():
    with pytest.raises(ValueError):
        Segment.from_bytes(b"\x01")


def test_default_helpers_are_false():
    seg = DataSegment(0, b"abc")

    assert not seg.is_ack_segment()
    assert not seg.is_syn_segment()
    assert not seg.is_synack_segment()
    assert not seg.is_finished_segment()
