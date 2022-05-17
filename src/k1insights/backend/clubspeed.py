################################################################################
#                               K1 Data Insights                               #
#   Capture K1 results to find hidden trends; pls don't call it data science   #
#                            (C) 2022, Jeremy Brown                            #
#                Released under Prosperity Public License 3.0.0                #
################################################################################

from __future__ import annotations

from asyncio import sleep
from base64 import b64decode, b64encode
from collections.abc import Coroutine, Iterator, ValuesView
from datetime import date, datetime
from html.parser import HTMLParser
from logging import Logger
from sqlite3 import Connection
from typing import Any, NoReturn, TypedDict, TypeVar, cast
from uuid import uuid4

from aiohttp import ClientSession, TCPConnector
from aioitertools.asyncio import gather_iter
from pytz import utc

from k1insights.common.constants import (
    LOCATIONS,
    MAX_CONCURRENT_TASKS,
    MAX_POOL_SIZE,
    FullSession,
    HeatData,
    HeatSession,
    K1Location,
)
from k1insights.common.db import K1DB


class BasicSession(TypedDict):
    location: str
    heat_id: int
    kart: int
    time: datetime


class HistoryData(TypedDict, total=False):
    name: str
    sessions: dict[str, list[BasicSession]]


class RacerData(TypedDict, total=False):
    rid: int
    name: str
    sessions: list[FullSession]


class WinConditions:
    BEST_LAP = 0
    POSITION = 1


class RaceTypes:
    STANDARD = 0
    JUNIOR = 1
    QUALIFIER = 2
    PRACTICE = 3
    FINAL = 4
    GRID_RACE = 5
    DRIFT = 6
    BALL_CHALLENGE = 7


class HistoryParser(HTMLParser):
    def __init__(self, loc_data: K1Location):
        super().__init__()
        self._tz = loc_data["tz"]
        self._location = loc_data["location"]
        self._display_name = ""
        self._sessions: list[BasicSession] = []

        self._getting_name = False
        self._getting_heat = False
        self._curr_col = 0
        self._curr_heat: int | None = None
        self._curr_kart: int | None = None
        self._curr_time: datetime | None = None

    @property
    def data(self) -> HistoryData:
        return {
            "name": self._display_name,
            "sessions": {
                self._location: self._sessions,
            },
        }

    @property
    def display_name(self) -> str:
        return self._display_name

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v for (k, v) in attrs if v is not None}

        if attr_dict.get("id") == "lblRacerName" and tag == "span":
            self._getting_name = True

        elif attr_dict.get("class") == "Normal" and tag == "tr":
            self._getting_heat = True

        elif self._getting_heat and tag == "td":
            self._curr_col += 1

        elif self._getting_heat and tag == "a":
            self._curr_heat = int(attr_dict["href"].split("=")[-1])

    def handle_endtag(self, tag: str) -> None:
        if self._getting_name and tag == "span":
            self._getting_name = False

        if self._getting_heat and tag == "tr":
            if (
                self._curr_heat is not None
                and self._curr_kart is not None
                and self._curr_time is not None
            ):
                self._sessions.append(
                    {
                        "location": self._location,
                        "heat_id": self._curr_heat,
                        "kart": self._curr_kart,
                        "time": self._curr_time,
                    }
                )

            self._curr_kart = None
            self._curr_heat = None
            self._curr_time = None
            self._curr_col = 0
            self._getting_heat = False

    def handle_data(self, data: str) -> None:
        if self._getting_name:
            self._display_name = data

        elif self._curr_col == 1:
            self._curr_kart = int(data.split()[-1])

        elif self._curr_col == 2:
            dt = datetime.strptime(data.strip(), "%m/%d/%Y %I:%M %p")
            self._curr_time = self._tz.localize(dt).astimezone(utc)


class HeatParser(HTMLParser):
    def __init__(self, loc_data: K1Location):
        super().__init__()
        self._tz = loc_data["tz"]
        self._curr_heat = cast(int, None)
        self._heat_type = cast(int, None)
        self._win_cond = cast(int, None)
        self._heat_time = cast(datetime, None)
        self._track = 1
        self._sessions: dict[str, HeatSession] = {}
        self._curr_racer: HeatSession = {}
        self._top_racer_mod = 0

        self._getting_racer_name = False
        self._getting_lap = False
        self._getting_laps = False
        self._getting_type = False
        self._getting_win_cond = False
        self._getting_time = False
        self._getting_racer_info = False
        self._getting_name = False
        self._prep_for_score = False
        self._getting_score = False
        self._getting_pos = False

    @property
    def data(self) -> HeatData:
        return {
            "heat_id": self._curr_heat,
            "race_type": self._heat_type,
            "win_cond": self._win_cond,
            "time": self._heat_time,
            "track": self._track,
            "sessions": [
                {
                    "name": name,
                    "rid": data["rid"],
                    "pos": data["pos"],
                    "score": data["score"],
                    "lap_data": data["lap_data"],
                }
                for (name, data) in self._sessions.items()
            ],
        }

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v for (k, v) in attrs if v is not None}

        if tag == "span":
            if attr_dict.get("id") == "lblRaceType":
                self._getting_type = True

            elif attr_dict.get("id") == "lblWinnerBy":
                self._getting_win_cond = True

            elif attr_dict.get("id") == "lblDate":
                self._getting_time = True

            elif self._prep_for_score:
                self._getting_score = True

        elif tag == "tr":
            if attr_dict.get("class") in ("RegularRow", "RegularRowAlt"):
                self._getting_racer_info = True

            elif attr_dict.get("class") in ("Top3WinnersRow", "Top3WinnersRowAlt"):
                self._getting_racer_info = True
                self._top_racer_mod = (self._top_racer_mod + 1) % 3

            elif attr_dict.get("class") in ("LapTimesRow", "LapTimesRowAlt"):
                self._getting_lap = True

        elif tag == "td":
            if attr_dict.get("class") == "RPM":
                self._prep_for_score = True

            if attr_dict.get("class") == "Position":
                self._getting_pos = True

        elif self._getting_racer_info and tag == "a":
            self._curr_racer["rid"] = int(
                b64decode(attr_dict["href"].split("=", 1)[-1])
            )
            self._getting_name = True

        elif attr_dict.get("class") == "LapTimes" and tag == "table":
            self._getting_laps = True

        elif self._getting_laps and tag == "thead":
            self._getting_racer_name = True

        elif tag == "form":
            self._curr_heat = int(attr_dict["action"].split("=")[-1])

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            if self._getting_type:
                self._getting_type = False

            elif self._getting_win_cond:
                self._getting_win_cond = False

            elif self._getting_time:
                self._getting_time = False

            elif self._getting_score:
                self._getting_score = False

        elif tag == "tr":
            if self._getting_racer_info and self._top_racer_mod == 0:
                name = self._curr_racer.pop("name")
                self._sessions[name] = self._curr_racer
                self._curr_racer = {}
                self._getting_racer_info = False

            elif self._getting_lap:
                self._getting_lap = False

        elif self._getting_name and tag == "a":
            self._getting_name = False

        elif tag == "td":
            if self._prep_for_score:
                self._prep_for_score = False

            elif self._getting_pos:
                self._getting_pos = False

        elif self._getting_racer_name and tag == "thead":
            self._getting_racer_name = False

        elif self._getting_laps and tag == "table":
            self._getting_laps = False

    def handle_data(self, data: str) -> None:
        if self._getting_type:
            if data == ".STANDARD Race.":
                self._heat_type = RaceTypes.STANDARD

            elif data == ".JUNIOR Race.":
                self._heat_type = RaceTypes.JUNIOR

            elif data == "DRIFT Race":
                self._heat_type = RaceTypes.DRIFT

            elif data == "BALL CHALLENGE":
                self._heat_type = RaceTypes.BALL_CHALLENGE

            elif data == "GRID Race":
                self._heat_type = RaceTypes.GRID_RACE

            elif data.endswith("Practice"):
                self._heat_type = RaceTypes.PRACTICE

            elif data.endswith("Qualifier"):
                self._heat_type = RaceTypes.QUALIFIER

            elif data.endswith("Final"):
                self._heat_type = RaceTypes.FINAL

            else:
                raise ValueError(f"Unknown race type: {data}")

        elif self._getting_win_cond:
            if data == "Best Lap":
                self._win_cond = WinConditions.BEST_LAP

            elif data == "Position":
                self._win_cond = WinConditions.POSITION

            else:
                raise ValueError(f"Unknown win condition: {data}")

        elif self._getting_pos:
            if data == "Heat Winner:":
                self._curr_racer["pos"] = 1

            elif data == "2nd Place:":
                self._curr_racer["pos"] = 2

            elif data == "3rd Place:":
                self._curr_racer["pos"] = 3

            else:
                self._curr_racer["pos"] = int(data)

        elif self._getting_time:
            dt = datetime.strptime(data.strip(), "%m/%d/%Y %I:%M %p")
            self._heat_time = self._tz.localize(dt).astimezone(utc)

        elif self._getting_name:
            self._curr_racer["name"] = data

        elif self._getting_score:
            self._curr_racer["score"] = int(data)

        elif self._getting_racer_name:
            self._curr_racer = self._sessions[data]

        elif self._getting_lap and len(data) > 3:
            str_lap, str_pos = data.split()
            lap = float(str_lap)
            pos = int(str_pos[1:-1])
            self._curr_racer.setdefault("lap_data", []).append((lap, pos))


ParserType = TypeVar("ParserType", HeatParser, HistoryParser)


async def fetch_and_parse(
    logger: Logger,
    session: ClientSession,
    parser_class: type[ParserType],
    loc_data: K1Location,
    url: str,
) -> ParserType | None:
    result = None
    parser = parser_class(loc_data)

    async with session.get(url) as res:
        if res.status != 200:
            logger.error("Fetching URL returned bad status code: %s", res.status)
            logger.debug("Source URL: %s", url)
        else:
            res_page = await res.text()
            try:
                parser.feed(res_page)
            except KeyError:
                if "Server Error" in res_page:
                    logger.error("K1 could not provide valid response for URL %s", url)
                else:
                    logger.exception("Failed to parse response for URL %s", url)
            except Exception:
                logger.exception("Failed to parse response for URL %s", url)
            else:
                result = parser

    return result


async def get_racer_history(
    logger: Logger,
    session: ClientSession,
    rid: int,
    after: date,
    locs: str | list[K1Location] | ValuesView[K1Location] = LOCATIONS.values(),
) -> HistoryData:
    result: HistoryData = {}
    b64 = b64encode(str(rid).encode()).decode()
    url_base = (
        "https://{subd}.clubspeedtiming.com/sp_center/RacerHistory.aspx?CustID={b64_id}"
    )

    if isinstance(locs, str):
        url_loc = locs.replace(" ", "_").lower()

        if url_loc in LOCATIONS:
            locs = [LOCATIONS[url_loc]]
        else:
            raise ValueError("Location not recognized")

    elif not isinstance(locs, type(LOCATIONS.values())):
        raise ValueError("Invalid K1 location")

    loc_data_tasks: Iterator[Coroutine[Any, Any, HistoryParser | None]] = (
        fetch_and_parse(
            logger,
            session,
            HistoryParser,
            loc,
            url_base.format(subd=loc["subdomain"], b64_id=b64),
        )
        for loc in locs
    )
    loc_parsers: list[HistoryParser | None] = await gather_iter(
        loc_data_tasks, limit=MAX_CONCURRENT_TASKS
    )

    for parser in filter(None, loc_parsers):
        result.setdefault("name", parser.data["name"])
        result.setdefault("sessions", {}).update(
            {
                loc: [s for s in sessions if s["time"] > after]
                for loc, sessions in parser.data["sessions"].items()
            }
        )

    return result


async def get_heat_info(
    logger: Logger, session: ClientSession, loc: K1Location, heats: int | list[int]
) -> dict[str, dict[int, HeatData]]:
    result: dict[str, dict[int, HeatData]] = {loc["location"]: {}}
    url_base = (
        "https://{subd}.clubspeedtiming.com/sp_center/HeatDetails.aspx?HeatNo={heat}"
    )

    if isinstance(heats, int):
        heats = [heats]

    heat_data_tasks: Iterator[Coroutine[Any, Any, HeatParser | None]] = (
        fetch_and_parse(
            logger,
            session,
            HeatParser,
            loc,
            url_base.format(subd=loc["subdomain"], heat=h),
        )
        for h in heats
    )
    heat_parsers: list[HeatParser | None] = await gather_iter(
        heat_data_tasks, limit=MAX_CONCURRENT_TASKS
    )

    for parser in filter(None, heat_parsers):
        heat_data = parser.data
        heat_id = heat_data.pop("heat_id")
        result[loc["location"]][heat_id] = heat_data

    return result


async def get_racer_data(logger: Logger, racer_id: int, after: datetime) -> RacerData:
    result: RacerData = {}
    async with ClientSession(connector=TCPConnector(limit=MAX_POOL_SIZE)) as session:
        history = await get_racer_history(logger, session, racer_id, after)
        if history:
            heats_by_location = {}
            result["rid"] = racer_id
            result["name"] = history["name"]

            heat_data_tasks = []
            for location, session_list in history["sessions"].items():
                loc = LOCATIONS[location.replace(" ", "_").lower()]
                heats = [s["heat_id"] for s in session_list]
                heat_data_tasks.append(get_heat_info(logger, session, loc, heats))
            heat_data: list[dict[str, dict[int, HeatData]]] = await gather_iter(
                heat_data_tasks, limit=MAX_CONCURRENT_TASKS
            )

            for data in filter(None, heat_data):
                heats_by_location.update(data)

            for location, session_list in history["sessions"].items():
                for hist_session in session_list:
                    heat = heats_by_location.get(location, {}).get(
                        hist_session["heat_id"], {}
                    )
                    try:
                        heat_session = next(
                            filter(
                                lambda s: s["rid"] == racer_id, heat.get("sessions", [])
                            )
                        )
                    except Exception:
                        pass
                    else:
                        result.setdefault("sessions", []).append(
                            {
                                "rid": racer_id,
                                "location": location,
                                "track": heat["track"],
                                "time": hist_session["time"],
                                "race_type": heat["race_type"],
                                "win_cond": heat["win_cond"],
                                "kart": hist_session["kart"],
                                "score": heat_session["score"],
                                "pos": heat_session["pos"],
                                "times": heat_session["lap_data"],
                            }
                        )
    return result


async def watch_location(logger: Logger, loc: K1Location, db: Connection) -> NoReturn:
    params = {
        "clientId": str(uuid4()),
        "groups": "SP_Center.ScoreBoardHub.1",
        "messageId": 1,
    }

    url = f"https://{loc['subdomain']}.clubspeedtiming.com/SP_Center/signalr"
    last_heat = -1

    async with ClientSession(connector=TCPConnector(limit=MAX_POOL_SIZE)) as session:
        logger.info("Started %s live data fetcher", loc["location"])

        while True:
            heat: HeatData = {}
            sessions: list[FullSession] = []
            all_msgs = []
            heat_num = last_heat
            async with session.post(url, data=params) as res:
                if res.status != 200:
                    logger.error(
                        "Got %s error watching for %s data", res.status, loc["location"]
                    )
                else:
                    res_data = await res.json()
                    params["messageId"] = res_data["MessageId"]
                    all_msgs = res_data["Messages"]

            for msg in all_msgs:
                data = msg["Args"][0]

                if data["ScoreboardData"]:
                    heat_num = int(data["ScoreboardData"][0]["HeatNo"])

                if not (data["RaceRunning"] or heat_num == last_heat):
                    raw_heat = await get_heat_info(logger, session, loc, heat_num)
                    heat_data = raw_heat[loc["location"]].get(heat_num, {})

                    if heat_data:
                        last_heat = heat_num
                        all_sessions = heat_data["sessions"]
                        heat = {
                            "location": loc["location"],
                            "track": heat_data["track"],
                            "time": heat_data["time"],
                            "race_type": heat_data["race_type"],
                            "win_cond": heat_data["win_cond"],
                        }

                        logger.debug(
                            "Got data for %s %s heat",
                            heat["location"],
                            heat["time"].time(),
                        )

                    for racer in data["ScoreboardData"]:
                        racer_id = int(racer["CustID"])
                        K1DB.add_racer(db, racer_id, racer["RacerName"])

                        def _get_session(
                            sessions: list[HeatSession],
                        ) -> HeatSession | None:
                            result = None
                            for session in sessions:
                                if session["rid"] == racer_id:
                                    result = session
                                    break
                            return result

                        sess = _get_session(all_sessions)
                        if sess is not None:
                            sessions.append(
                                {
                                    "rid": racer_id,
                                    "location": loc["location"],
                                    "track": heat_data["track"],
                                    "time": heat_data["time"],
                                    "kart": int(racer["AutoNo"]),
                                    "score": sess["score"],
                                    "pos": sess["pos"],
                                    "times": sess["lap_data"],
                                }
                            )

                    if heat and sessions:
                        K1DB.add_heats(db, heat)
                        K1DB.add_sessions(db, sessions)

                        logger.info(
                            "Saved all data for %s race beginning at %s UTC",
                            heat["location"],
                            heat["time"].time(),
                        )
                    break

            await sleep(10)
