from lib.application.client_parser import ClientParser
from lib.constants.protocol_constants import PROTOCOL_STOP_AND_WAIT, PROTOCOL_GO_BACK_N
from lib.client.upload_client import UploadClient

if __name__ == "__main__":
    parser = ClientParser(is_upload=True)
    args = parser.parse()
    protocol_id = PROTOCOL_STOP_AND_WAIT if args.protocol == 'sw' else PROTOCOL_GO_BACK_N
    client = UploadClient(
        args.host,
        args.port,
        args.verbose,
        args.quiet,
        protocol_id,
        args.src,
        args.name)
    client.run_process()
