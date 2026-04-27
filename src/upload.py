from lib.application.client_parser import ClientParser
from lib.transport.segments.constants import *
from lib.client.upload_client import UploadClient

if __name__ == "__main__":
    parser = ClientParser(is_upload=True)
    args = parser.parse()
    protocol_id = SW_PROTOCOL_ID if args.protocol == 'sw' else GBN_PROTOCOL_ID
    client = UploadClient(args.host, args.port, args.verbose, args.quiet, protocol_id, args.src, args.name)
    client.run_process()
