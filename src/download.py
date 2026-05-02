from lib.application.client_parser import ClientParser
from lib.constants.protocol_constants import PROTOCOL_STOP_AND_WAIT, PROTOCOL_GO_BACK_N
from lib.client.download_client import DownloadClient

if __name__ == "__main__":
    parser = ClientParser(is_upload=False)
    args = parser.parse()
    protocol_id = PROTOCOL_STOP_AND_WAIT if args.protocol == 'sw' else PROTOCOL_GO_BACK_N
    client = DownloadClient(
        args.host,
        args.port,
        args.verbose,
        args.quiet,
        protocol_id,
        args.dst,
        args.name)
    client.run_process()
