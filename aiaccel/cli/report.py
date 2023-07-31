import os
from argparse import ArgumentParser
from logging import StreamHandler, getLogger

from aiaccel.cli import CsvWriter
from aiaccel.config import load_config

logger = getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
logger.addHandler(StreamHandler())


def main() -> None:  # pragma: no cover
    """Parses command line options and reports the result."""
    parser = ArgumentParser()
    parser.add_argument("--config", "-c", type=str, default="config.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    csv_writer = CsvWriter(config)
    csv_writer.create()


if __name__ == "__main__":  # pragma: no cover
    main()
