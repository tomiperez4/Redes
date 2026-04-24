DEFAULT_LOGFILE = "app.log"

class Logger:
    def __init__(self, prefix, verbose=False, quiet=False):
        self.verbose = verbose
        self.quiet = quiet
        self.prefix = prefix

        if self.quiet:
            self.verbose = False

    @staticmethod
    def write_file(message):
        with open(DEFAULT_LOGFILE, "a") as f:
            f.write(message + "\n")

    def debug(self, message):
        msg = f"[DEBUG] {self.prefix} - {message}"
        if self.verbose:
            print(msg)
        self.write_file(msg)

    def info(self, message):
        msg = f"[INFO] {self.prefix} - {message}"
        if not self.quiet:
            print(msg)
        self.write_file(msg)

    def error(self, message):
        msg = f"[ERROR] {self.prefix} - {message}"
        print(msg)
        self.write_file(msg)