from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
from sys import exit

from k1stats.common.db import K1DB


def main(args: list[str] | None = None) -> None:
    parser = ArgumentParser(
        prog="k1-create-db",
        description="Creates database to store K1 race data",
        epilog="Released under version 3.0.0 of the Prosperity Public License",
    )

    parser.add_argument(
        "dest",
        type=Path,
        help="gzipped rstats logfile",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        dest="overwrite",
        help="gzipped rstats logfile",
    )

    parsed: Namespace = parser.parse_args(args)

    success = False

    if parsed.overwrite or not parsed.dest.exists():
        parsed.dest.unlink(missing_ok=True)
        K1DB.create_db(parsed.dest)
        print("Database successfully created, remember this environment variable:")
        print(f"K1_DATA_DB={parsed.dest.absolute()}")
        success = True
    else:
        print(f"Not overwriting {parsed.dest.absolute()}; delete the file or use '-f'")

    exit(0 if success else 1)
