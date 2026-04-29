from lib.segments.data_segment import DataSegment

BUFFER_SIZE = 1024
MAX_PACKET_SIZE = BUFFER_SIZE + DataSegment.HEADER_SIZE
TIMEOUT = 0.5  # Este es el de GBN inicialmente, el de SW era 0.1, probamos si asi funciona y unificamos timeout