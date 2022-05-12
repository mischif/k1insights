from __future__ import annotations

from argparse import Action, ArgumentParser, Namespace
from asyncio import run
from collections.abc import Sequence
from datetime import date, datetime
from logging import getLogger
from sys import exit
from typing import Any, cast

from pytz import utc

from k1stats.backend.clubspeed import get_racer_data
from k1stats.common.constants import DB_PATH
from k1stats.common.db import K1DB

START_OF_LAST_YEAR = datetime(date.today().year - 1, 1, 1, tzinfo=utc)


class GetHistoryCutoff(Action):
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        try:
            start_time = datetime.fromisoformat(cast(str, values)).replace(tzinfo=utc)
            setattr(namespace, self.dest, start_time)
        except ValueError:
            parser.error("Value must be valid ISO 8601 date string")


def main(args: list[str] | None = None) -> None:
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

    parsed: Namespace = parser.parse_args(args)
    logger = getLogger(__name__)
    success = False

    db = K1DB.connect(logger, DB_PATH)

    if db is not None:
        data = run(get_racer_data(logger, parsed.id, parsed.start))

        if data:
            K1DB.add_racer(db, data["rid"], data["name"], parsed.fast, parsed.track)
            K1DB.add_heats(db, data["sessions"])
            K1DB.add_sessions(db, data["sessions"])
            success = True

        K1DB.close(db)

    exit(0 if success else 1)
