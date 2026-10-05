import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
