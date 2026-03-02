import logging


def configure_logging(level: str = "INFO", debug: bool = False) -> None:
    effective_level = "DEBUG" if debug else level.upper()
    logging.basicConfig(
        level=getattr(logging, effective_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
