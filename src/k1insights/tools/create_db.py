################################################################################
#                               K1 Data Insights                               #
#   Capture K1 results to find hidden trends; pls don't call it data science   #
#                            (C) 2022, Jeremy Brown                            #
#                Released under Prosperity Public License 3.0.0                #
################################################################################

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from logging import INFO, StreamHandler, getLogger
from pathlib import Path
from sys import exit, stdout

from k1insights.common.db import K1DB


def main(args: list[str] | None = None) -> None:
    parser = ArgumentParser(
        prog="k1-create-db",
        description="Creates database to store K1 race data",
        epilog="Released under Prosperity Public License 3.0.0",
    )

    parser.add_argument(
        "dest",
        type=Path,
        help="Destination of new db file",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        dest="overwrite",
        help="Toggle to overwrite existing file when creating database",
    )

    parsed: Namespace = parser.parse_args(args)
    logger = getLogger(__name__)
    logger.addHandler(StreamHandler(stdout))
    logger.setLevel(INFO)

    success = False

    if parsed.overwrite or not parsed.dest.exists():
        parsed.dest.unlink(missing_ok=True)
        K1DB.create_db(parsed.dest)
        logger.info(
            "Database successfully created, remember this environment variable:"
        )
        logger.info("K1_DATA_DB=%s", parsed.dest.absolute())
        success = True
    else:
        logger.warning(
            f"Not overwriting {parsed.dest.absolute()}; delete the file or use '-f'"
        )

    exit(0 if success else 1)
