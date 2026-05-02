import os
from lib.application.server_parser import ServerParser
from lib.server.server import Server
from lib.logger import Logger
from lib.constants.log_file_constants import *


def main():
    parser = ServerParser()
    args = parser.parse()
    Logger.clear_session_logs([SERVER_LOG_FILE, CLIENTS_LOG_FILE])
    log = Logger("SERVER", SERVER_LOG_FILE, args.verbose, args.quiet)
    storage_path = args.storage
    if not os.path.exists(storage_path):
        try:
            os.makedirs(storage_path)
            log.debug(f"Storage directory created: {storage_path}")
        except OSError as error:
            log.error(f"Failed to create storage directory: {error}")
            return
    server = Server(host=args.host, port=args.port, workers=5,
                    storage_path=storage_path, log=log)

    try:
        log.info(f"Starting server on {args.host}:{args.port}")
        server.start()
    except Exception as error:
        log.error(
            f"Failed to start server on {
                args.host}:{
                args.port}: {error}")


if __name__ == "__main__":
    main()
