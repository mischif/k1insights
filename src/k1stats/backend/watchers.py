from argparse import ArgumentParser
from logging import DEBUG, INFO, StreamHandler, getLogger
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue

from anyio import create_task_group, run

from k1stats.backend.clubspeed import watch_location
from k1stats.common.constants import DB_PATH, LOCATIONS
from k1stats.common.db import K1DB


LOG = getLogger(__name__)


async def start_watchers():
    db = K1DB.connect(LOG, DB_PATH)

    async with create_task_group() as nursery:
        for loc in LOCATIONS.values():
            nursery.start_soon(watch_location, LOG, loc, db, name=f"{loc['location']}")

    K1DB.close(db)


def main(args=None):
    parser = ArgumentParser(
        prog="k1-start-backend",
        description="Start data fetching tasks",
        epilog="Released under version 3.0.0 of the Prosperity Public License",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="gzipped rstats logfile",
    )
    args = parser.parse_args(args)

    log_queue = SimpleQueue()
    q_hdlr = QueueHandler(log_queue)
    stdout_hdlr = StreamHandler()

    service_logger = getLogger(__name__.split(".")[0])
    service_logger.addHandler(q_hdlr)
    service_logger.setLevel(DEBUG if args.debug else INFO)

    lstnr = QueueListener(log_queue, stdout_hdlr)
    lstnr.start()

    run(start_watchers, backend_options={"debug": args.debug})
