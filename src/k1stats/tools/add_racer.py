from argparse import Action, ArgumentParser
from asyncio import run
from datetime import date, datetime
from logging import getLogger
from sys import exit

from pytz import utc

from k1stats.backend.clubspeed import get_racer_data
from k1stats.common.constants import DB_PATH
from k1stats.common.db import K1DB


START_OF_LAST_YEAR = datetime(date.today().year - 1, 1, 1, tzinfo=utc)


class GetHistoryCutoff(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            setattr(
                namespace, self.dest, datetime.fromisoformat(values).replace(tzinfo=utc)
            )
        except ValueError:
            parser.error("Value must be valid ISO 8601 date string")


def main(args=None):
    parser = ArgumentParser(
        prog="k1-add-racer",
        description="Manually add data for K1 racer",
        epilog="Released under version 3.0.0 of the Prosperity Public License",
    )

    parser.add_argument(
        "id",
        type=int,
        help="gzipped rstats logfile",
    )

    parser.add_argument(
        "-f",
        "--fast",
        action="store_true",
        help="gzipped rstats logfile",
    )

    parser.add_argument(
        "-t",
        "--track",
        action="store_true",
        help="gzipped rstats logfile",
    )

    parser.add_argument(
        "-s",
        "--start",
        action=GetHistoryCutoff,
        default=START_OF_LAST_YEAR,
        help="gzipped rstats logfile",
    )

    args = parser.parse_args(args)
    logger = getLogger(__name__)
    success = False

    db = K1DB.connect(logger, DB_PATH)

    if db is not None:
        data = run(get_racer_data(logger, args.id, args.start))

        if data:
            K1DB.add_racer(db, data["id"], data["name"], args.fast, args.track)
            K1DB.add_heats(db, data["sessions"])
            K1DB.add_sessions(db, data["sessions"])
            success = True

    K1DB.close(db)
    exit(0 if success else 1)
