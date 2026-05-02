import logging
import threading
import sys


class Logger:
    _configured_loggers = {}
    _lock = threading.Lock()

    @staticmethod
    def clear_session_logs(files):
        for f in files:
            with open(f, 'w') as _:
                pass

    def __init__(self, prefix, log_file, verbose=False, quiet=False):
        self.prefix = prefix
        self.verbose = verbose
        self.quiet = quiet
        self.log_file = log_file

        with Logger._lock:
            if log_file not in Logger._configured_loggers:
                logger = logging.getLogger(log_file)
                logger.setLevel(logging.DEBUG)

                handler = logging.FileHandler(log_file, mode='a')
                handler.setLevel(logging.DEBUG)
                fmt = logging.Formatter(
                    '%(asctime)s - [%(prefix)s] - %(levelname)s - %(message)s')
                handler.setFormatter(fmt)
                logger.addHandler(handler)

                if not self.quiet:
                    console_handler = logging.StreamHandler(sys.stdout)
                    console_fmt = logging.Formatter(
                        '[%(levelname)s] [%(prefix)s] %(message)s')
                    console_handler.setFormatter(console_fmt)

                    if self.verbose:
                        console_handler.setLevel(logging.DEBUG)
                    else:
                        console_handler.setLevel(logging.INFO)

                    logger.addHandler(console_handler)

                Logger._configured_loggers[log_file] = logger
                Logger._initialized = True

        base_logger = Logger._configured_loggers[log_file]
        self.adapter = logging.LoggerAdapter(
            base_logger, {'prefix': self.prefix})

    def clone(self, new_prefix):
        return Logger(new_prefix, self.log_file, self.verbose, self.quiet)

    def debug(self, message):
        if self.verbose and not self.quiet:
            self.adapter.debug(message)

    def info(self, message):
        if not self.quiet:
            self.adapter.info(message)

    def warning(self, message):
        self.adapter.warning(message)

    def error(self, message):
        self.adapter.error(message)
