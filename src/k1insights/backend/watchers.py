################################################################################
#                               K1 Data Insights                               #
#   Capture K1 results to find hidden trends; pls don't call it data science   #
#                            (C) 2022, Jeremy Brown                            #
#                Released under Prosperity Public License 3.0.0                #
################################################################################

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from logging import DEBUG, INFO, LogRecord, StreamHandler, getLogger
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue
from sys import stdout

from anyio import create_task_group, run

from k1insights.backend.clubspeed import watch_location
from k1insights.common.constants import DB_PATH, LOCATIONS
from k1insights.common.db import K1DB


LOG = getLogger(__name__)


async def start_watchers() -> None:
    db = K1DB.connect(LOG, DB_PATH)

    if db is not None:
        async with create_task_group() as nursery:
            for loc in LOCATIONS.values():
                nursery.start_soon(
                    watch_location, LOG, loc, db, name=f"{loc['location']}"
                )

        K1DB.close(db)


def main(args: list[str] | None = None) -> None:
    parser = ArgumentParser(
        prog="k1-start-backend",
        description="Start data fetching tasks",
        epilog="Released under version 3.0.0 of the Prosperity Public License",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Display debug logs",
    )
    parsed: Namespace = parser.parse_args(args)

    log_queue: SimpleQueue[LogRecord] = SimpleQueue()
    q_hdlr = QueueHandler(log_queue)
    stdout_hdlr = StreamHandler(stdout)

    service_logger = getLogger(__name__.split(".")[0])
    service_logger.addHandler(q_hdlr)
    service_logger.setLevel(DEBUG if parsed.debug else INFO)

    lstnr = QueueListener(log_queue, stdout_hdlr)
    lstnr.start()

    run(start_watchers, backend_options={"debug": parsed.debug})
