from argparse import ArgumentParser
from pathlib import Path
from sys import exit

from k1stats.common.db import K1DB


def main(args=None):
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

    args = parser.parse_args(args)

    success = False

    if args.overwrite or not args.dest.exists():
        args.dest.unlink(missing_ok=True)
        K1DB.create_db(args.dest)
        print("Database successfully created, remember this environment variable:")
        print(f"K1_DATA_DB={args.dest.absolute()}")
        success = True
    else:
        print(f"Not overwriting {args.dest.absolute()}; delete the file or use '-f'")

    exit(0 if success else 1)
