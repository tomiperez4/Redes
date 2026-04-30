from lib.transport.segments.segment import Segment

BUFFER_SIZE = 1024
MAX_PACKET_SIZE = BUFFER_SIZE + Segment.HEADER_SIZE
TIMEOUT = 1  # Este es el de GBN inicialmente, el de SW era 0.1, probamos si asi funciona y unificamos timeout