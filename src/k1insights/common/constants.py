################################################################################
#                               K1 Data Insights                               #
#   Capture K1 results to find hidden trends; pls don't call it data science   #
#                            (C) 2022, Jeremy Brown                            #
#                Released under Prosperity Public License 3.0.0                #
################################################################################

from __future__ import annotations

from datetime import datetime
from os import environ
from pathlib import Path
from typing import TypedDict

from pytz import timezone
from pytz.tzinfo import BaseTzInfo


def __getattr__(name: str) -> Path:
    if name == "DB_PATH":
        if "K1_DATA_DB" not in environ:
            raise RuntimeError("K1_DATA_DB not defined")

        elif not Path(environ["K1_DATA_DB"]).is_file():
            raise ValueError("K1_DATA_DB does not point to file")

        else:
            return Path(environ["K1_DATA_DB"]).absolute()

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


KART_LOOKBACK_DAYS = int(environ.get("K1_KART_LOOKBACK", 14))
LOCATION_LOOKBACK_DAYS = int(environ.get("K1_LOCATION_LOOKBACK", 7))
USER_LOOKBACK_DAYS = int(environ.get("K1_USER_LOOKBACK", 30))

MAX_POOL_SIZE = int(environ.get("K1_POOL_SIZE", 100))
MAX_CONCURRENT_TASKS = int(environ.get("K1_TASK_LIMIT", 10))

LOCATIONS: dict[str, K1Location] = {
    "atlanta": {
        "location": "Atlanta",
        "subdomain": "k1atlanta",
        "tracks": 1,
        "tz": timezone("US/Eastern"),
    },
}


class K1Location(TypedDict):
    location: str
    subdomain: str
    tracks: int
    tz: BaseTzInfo


class HeatSession(TypedDict, total=False):
    name: str
    rid: int
    pos: int
    score: int
    lap_data: list[tuple[float, int]]


class HeatData(TypedDict, total=False):
    heat_id: int
    race_type: int
    win_cond: int
    time: datetime
    track: int
    sessions: list[HeatSession]
    location: str


class FullSession(TypedDict, total=False):
    hid: int
    rid: int
    location: str
    track: int
    time: datetime
    race_type: int
    win_cond: int
    kart: int
    score: int
    pos: int
    times: list[tuple[float, int]]
