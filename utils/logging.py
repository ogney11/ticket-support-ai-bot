import logging
import sys


def setup_logging(level: str = "INFO"):
    numeric = getattr(logging, level.upper(), None)
    if not isinstance(numeric, int):
        numeric = logging.INFO

    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("asyncmy").setLevel(logging.WARNING)
    return logging.getLogger("ticket_bot")


logger = logging.getLogger("ticket_bot")
