from pox.core import core

log = core.getLogger()

RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RESET  = "\033[0m"


def log_color(color, msg):
    log.info(f"{color}{msg}{RESET}")