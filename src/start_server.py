import os
from lib.application.server_parser import ServerParser
from lib.server.server import Server

def main():
    parser = ServerParser()
    args = parser.parse()

    storage_path = args.storage
    if not os.path.exists(storage_path):
        try:
            os.makedirs(storage_path)
            if args.verbose:
                print(f"[DEBUG] Storage directory path created: {storage_path}")
        except OSError as error:
            print(f"[ERROR] Failed to create storage directory path: {error}")
            return
    server = Server(host=args.host, port=args.port, workers= 5,
                    storage=storage_path, verbose=args.verbose, quiet=args.quiet)

    try:
        server.start()
    except Exception as error:
        print(f"[ERROR] Unexpected error: {error}")

if __name__ == "__main__":
    main()