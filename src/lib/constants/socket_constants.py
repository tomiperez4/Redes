from lib.transport.segments.segment import Segment

BUFFER_SIZE = 1024
MAX_PACKET_SIZE = BUFFER_SIZE + Segment.HEADER_SIZE
TIMEOUT = 1
