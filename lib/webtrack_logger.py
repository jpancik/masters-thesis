import sys
import logging

log = logging.getLogger(__name__)


def setup_logging(logfile=None, verbose=False):
    standard_log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s[%(funcName)s:%(lineno)s] - %(levelname)s - %(message)s")

    handler = logging.FileHandler(logfile) if logfile else logging.StreamHandler(sys.stderr)

    level = logging.DEBUG if verbose else logging.INFO

    handler.setLevel(level)
    handler.setFormatter(standard_log_formatter)

    logging.root.addHandler(handler)
    logging.root.setLevel(level)

    log.debug("Starting up logging.")
