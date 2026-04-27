DEFAULT_LOGFILE = "app.log"

class Logger:
    def __init__(self, prefix, verbose=False, quiet=False, file_name=DEFAULT_LOGFILE):
        self.verbose = verbose
        self.quiet = quiet
        self.prefix = prefix
        self.file_name = file_name

        if self.quiet:
            self.verbose = False

    @staticmethod
    def write_file(message, file_name):
        with open(file_name, "a") as f:
            f.write(message + "\n")

    def debug(self, message):
        msg = f"[DEBUG] {self.prefix} - {message}"
        if self.verbose:
            print(msg)
        self.write_file(msg, self.file_name)

    def info(self, message):
        msg = f"[INFO] {self.prefix} - {message}"
        if not self.quiet:
            print(msg)
        self.write_file(msg, self.file_name)

    def error(self, message):
        msg = f"[ERROR] {self.prefix} - {message}"
        print(msg)
        self.write_file(msg, self.file_name)