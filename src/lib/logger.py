'''
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

'''
import logging
import threading

DEFAULT_LOGFILE = "app.log"


class Logger:
    _configured_loggers = {}
    _lock = threading.Lock()

    @staticmethod
    def clear_session_logs(files):
        for f in files:
            with open(f, 'w') as _:
                pass

    def __init__(self, prefix, verbose=False, quiet=False, _internal_logger=None, log_file=DEFAULT_LOGFILE):
        self.prefix = prefix
        self.verbose = verbose
        self.quiet = quiet

        with Logger._lock:
            if log_file not in Logger._configured_loggers:
                logger = logging.getLogger(log_file)
                logger.setLevel(logging.DEBUG)

                handler = logging.FileHandler(log_file, mode='a')
                fmt = logging.Formatter('%(asctime)s - [%(prefix)s] - %(levelname)s - %(message)s')
                handler.setFormatter(fmt)
                logger.addHandler(handler)

                if self.verbose:
                    logger.addHandler(logging.StreamHandler())

                Logger._configured_loggers[log_file] = logger
                Logger._initialized = True

        base_logger = Logger._configured_loggers[log_file]
        self.adapter = logging.LoggerAdapter(base_logger, {'prefix': self.prefix})

    def clone(self, new_prefix):
        """Crea una copia con un nuevo prefijo, manteniendo la configuración."""
        # Pasamos el logger interno para que todos compartan el mismo canal
        return Logger(new_prefix, self.verbose, self.quiet, self.adapter.logger)

    def debug(self, message):
        if self.verbose and not self.quiet:
            self.adapter.debug(message)

    def info(self, message):
        if not self.quiet:
            self.adapter.info(message)

    def error(self, message):
        # El error siempre se loguea
        self.adapter.error(message)