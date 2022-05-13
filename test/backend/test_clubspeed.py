from asyncio import CancelledError
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from aiohttp import ClientResponse, ClientSession
from pytz import utc

from k1stats.backend.clubspeed import (
    HeatParser,
    HistoryParser,
    RaceTypes,
    WinConditions,
    fetch_and_parse,
    get_heat_info,
    get_racer_data,
    get_racer_history,
    watch_location,
)
from k1stats.common.constants import LOCATIONS


@pytest.mark.asyncio
@pytest.mark.parametrize("return_code", [200, 404])
async def test_fetch_and_parse(return_code, blank_db):
    mock_logger = Mock()
    mock_parser = Mock()
    mock_parser.return_value = mock_parser
    mock_session = AsyncMock(spec=ClientSession)

    mock_session.get.return_value.__aenter__.return_value.status = return_code

    result = await fetch_and_parse(
        mock_logger, mock_session, mock_parser, None, "http://example.com"
    )

    if return_code == 200:
        assert result is mock_parser
    else:
        assert result is None
        mock_logger.error.assert_called_once_with(
            "Got bad status code fetching URL: %s", return_code
        )
        mock_logger.debug.assert_called_once_with(
            "Source URL: %s", "http://example.com"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("location", [None, "atl", "atlanta", 1])
@patch("k1stats.backend.clubspeed.gather_iter", new_callable=AsyncMock)
@patch("k1stats.backend.clubspeed.fetch_and_parse")
async def test_get_racer_history(
    mock_fetch_and_parse, mock_gather_iter, blank_db, location
):
    now = datetime.now()
    then = now - timedelta(hours=12)
    yday = now - timedelta(days=1)
    mock_logger = Mock()
    mock_session = Mock()
    loc1_parser = Mock()
    loc2_parser = Mock()

    loc1_parser.data = {
        "name": "Test Racer",
        "sessions": {
            "Location 1": [
                {
                    "location": "Location 1",
                    "heat_id": 1,
                    "kart": 1,
                    "time": now,
                },
                {
                    "location": "Location 1",
                    "heat_id": 2,
                    "kart": 2,
                    "time": yday,
                },
            ]
        },
    }

    loc2_parser.data = {
        "name": "Test Racer",
        "sessions": {
            "Location 2": [
                {
                    "location": "Location 2",
                    "heat_id": 1,
                    "kart": 1,
                    "time": yday,
                },
                {
                    "location": "Location 2",
                    "heat_id": 2,
                    "kart": 2,
                    "time": now,
                },
            ]
        },
    }
    mock_gather_iter.return_value = [
        loc1_parser,
        loc2_parser,
        *(None for _ in range(len(LOCATIONS) - 2)),
    ]

    if location not in (None, "atlanta"):
        with pytest.raises(ValueError):
            await get_racer_history(mock_logger, mock_session, 123, then, location)
    else:
        if location == "atlanta":
            result = await get_racer_history(
                mock_logger, mock_session, 123, then, location
            )
        else:
            result = await get_racer_history(mock_logger, mock_session, 123, then)

        assert "Test Racer" == result["name"]
        assert 2 == len(result["sessions"])
        assert 1 == len(result["sessions"]["Location 1"])
        assert 1 == len(result["sessions"]["Location 2"])
        assert 1 == result["sessions"]["Location 1"][0]["heat_id"]
        assert 2 == result["sessions"]["Location 2"][0]["heat_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("heats", [1, [1, 2]])
@patch("k1stats.backend.clubspeed.gather_iter", new_callable=AsyncMock)
@patch("k1stats.backend.clubspeed.fetch_and_parse")
async def test_get_heat_info(mock_fetch_and_parse, mock_gather_iter, heats, blank_db):
    mock_logger = Mock()
    mock_session = Mock()

    heat1_parser = Mock()
    heat1_parser.data = {
        "heat_id": 1,
        "race_type": RaceTypes.STANDARD,
        "win_cond": WinConditions.BEST_LAP,
        "time": datetime.now(),
        "track": 1,
        "sessions": [
            {
                "name": "Racer 1",
                "rid": 1,
                "pos": 1,
                "score": 12,
                "lap_data": [
                    (50.81, 2),
                    (23.15, 1),
                    (22.99, 1),
                ],
            },
            {
                "name": "Racer 2",
                "rid": 2,
                "pos": 2,
                "score": 10,
                "lap_data": [
                    (45.19, 1),
                    (23.77, 2),
                    (24.01, 2),
                ],
            },
        ],
    }

    heat2_parser = Mock()
    heat2_parser.data = {
        "heat_id": 2,
        "race_type": RaceTypes.JUNIOR,
        "win_cond": WinConditions.BEST_LAP,
        "time": datetime.now(),
        "track": 1,
        "sessions": [
            {
                "name": "Racer 3",
                "rid": 3,
                "pos": 1,
                "score": 12,
                "lap_data": [
                    (50.81, 2),
                    (23.15, 1),
                    (22.99, 1),
                ],
            },
            {
                "name": "Racer 4",
                "rid": 4,
                "pos": 2,
                "score": 10,
                "lap_data": [
                    (45.19, 1),
                    (23.77, 2),
                    (24.01, 2),
                ],
            },
        ],
    }

    if isinstance(heats, int):
        mock_gather_iter.return_value = [heat1_parser]
    else:
        mock_gather_iter.return_value = [heat1_parser, None, heat2_parser]

    result = await get_heat_info(mock_logger, mock_session, LOCATIONS["atlanta"], heats)

    assert RaceTypes.STANDARD == result["Atlanta"][1]["race_type"]

    if isinstance(heats, int):
        assert 1 == len(result["Atlanta"])
    else:
        assert 2 == len(result["Atlanta"])
        assert RaceTypes.JUNIOR == result["Atlanta"][2]["race_type"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "got_history, got_heat_data", [[False, False], [True, False], [True, True]]
)
@patch("k1stats.backend.clubspeed.LOCATIONS", {"location_1": {}, "location_2": {}})
@patch("k1stats.backend.clubspeed.get_heat_info")
@patch("k1stats.backend.clubspeed.get_racer_history")
@patch("k1stats.backend.clubspeed.ClientSession")
async def test_get_racer_data(
    mock_session, mock_get_history, mock_get_info, got_history, got_heat_data, blank_db
):
    mock_logger = Mock()
    now = datetime.now()

    if got_history:
        mock_get_history.return_value = {
            "name": "Test Racer",
            "sessions": {
                "Location 1": [
                    {
                        "location": "Location 1",
                        "heat_id": 1,
                        "kart": 1,
                        "time": now,
                    }
                ],
                "Location 2": [
                    {
                        "location": "Location 2",
                        "heat_id": 1,
                        "kart": 2,
                        "time": now,
                    }
                ],
            },
        }
    else:
        mock_get_history.return_value = {}

    if got_heat_data:
        loc1_data = {
            "Location 1": {
                1: {
                    "heat_id": 1,
                    "race_type": RaceTypes.STANDARD,
                    "win_cond": WinConditions.BEST_LAP,
                    "time": now,
                    "track": 1,
                    "sessions": [
                        {
                            "name": "Test Racer",
                            "rid": 123,
                            "pos": 1,
                            "score": 12,
                            "lap_data": [
                                (50.81, 2),
                                (23.15, 1),
                                (22.99, 1),
                            ],
                        },
                        {
                            "name": "Racer 2",
                            "rid": 246,
                            "pos": 2,
                            "score": 10,
                            "lap_data": [
                                (45.19, 1),
                                (23.77, 2),
                                (24.01, 2),
                            ],
                        },
                    ],
                }
            }
        }

        loc2_data = {
            "Location 2": {
                1: {
                    "heat_id": 1,
                    "race_type": RaceTypes.DRIFT,
                    "win_cond": WinConditions.BEST_LAP,
                    "time": now,
                    "track": 1,
                    "sessions": [
                        {
                            "name": "Test Racer",
                            "rid": 123,
                            "pos": 1,
                            "score": 12,
                            "lap_data": [
                                (49.17, 2),
                                (68.28, 1),
                                (37.90, 1),
                            ],
                        },
                        {
                            "name": "Racer 3",
                            "rid": 369,
                            "pos": 2,
                            "score": 10,
                            "lap_data": [
                                (45.19, 1),
                                (23.77, 2),
                                (24.01, 2),
                            ],
                        },
                    ],
                }
            }
        }

        mock_get_info.side_effect = [loc1_data, loc2_data]
    else:
        mock_get_info.side_effect = [None, None]

    result = await get_racer_data(mock_logger, 123, now)

    if not got_history:
        assert {} == result
    else:
        assert "Test Racer" == result["name"]
        assert 123 == result["rid"]

        if not got_heat_data:
            assert "sessions" not in result
        else:
            assert 2 == len(result["sessions"])
            assert (
                1
                == [s for s in result["sessions"] if s["location"] == "Location 1"][0][
                    "kart"
                ]
            )
            assert (
                2
                == [s for s in result["sessions"] if s["location"] == "Location 2"][0][
                    "kart"
                ]
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "good_response, race_running, new_race",
    [
        [False, False, False],
        [True, True, True],
        [True, False, False],
        [True, False, True],
    ],
)
@patch("k1stats.backend.clubspeed.sleep", side_effect=CancelledError)
@patch("k1stats.backend.clubspeed.K1DB")
@patch("k1stats.backend.clubspeed.get_heat_info")
@patch("k1stats.backend.clubspeed.ClientSession", spec=ClientSession)
async def test_watch_location(
    mock_session,
    mock_get_info,
    mock_k1db,
    mock_sleep,
    good_response,
    race_running,
    new_race,
    blank_db,
):
    mock_logger = Mock()
    now = datetime.now().replace(microsecond=0)
    loc = LOCATIONS["atlanta"]

    mock_response = Mock(spec=ClientResponse)
    mock_ctx_man = AsyncMock(spec=ClientSession)
    mock_ctx_man.post.return_value.__aenter__.return_value = mock_response
    mock_session.return_value.__aenter__.return_value = mock_ctx_man

    if good_response:
        mock_response.status = 200
        mock_response.json.return_value = {
            "MessageId": 42,
            "TransportData": {
                "Groups": ["SP_Center.ScoreBoardHub.1"],
                "LongPollDelay": 0,
            },
            "Messages": [
                {
                    "Hub": "SP_Center.ScoreBoardHub",
                    "Method": "refreshGrid",
                    "Args": [
                        {
                            "RaceRunning": race_running,
                            "Winby": "By Best Lap Time",
                            "LapsLeft": "1 Laps Left",
                            "HeatTypeName": ".STANDARD Race.",
                            "Winners": [],
                            "ScoreboardData": [
                                {
                                    "CustID": "1",
                                    "HeatNo": "69" if new_race else "-1",
                                    "RacerName": "Racer 1",
                                    "AutoNo": "11",
                                    "AMBTime": "339224934",
                                    "LTime": "23.456",
                                    "LapNum": "2",
                                    "BestLTime": "22.47",
                                    "Position": "1",
                                    "GapToLeader": "-",
                                    "HeatRanking": None,
                                    "LastPassedTime": "5/10/2022 9:39:02 PM",
                                    "DlTime": "12:00:22 AM",
                                    "DBestLTime": "12:00:22 AM",
                                    "TimeSinceLastPassed": "-",
                                    "PenaltyFlags": "0",
                                },
                                {
                                    "CustID": "2",
                                    "HeatNo": "69" if new_race else "-1",
                                    "RacerName": "Racer 2",
                                    "AutoNo": "22",
                                    "AMBTime": "339204556",
                                    "LTime": "34.567",
                                    "LapNum": "2",
                                    "BestLTime": "23.241",
                                    "Position": "2",
                                    "GapToLeader": "0.771",
                                    "HeatRanking": None,
                                    "LastPassedTime": "5/10/2022 9:38:42 PM",
                                    "DlTime": "12:00:23 AM",
                                    "DBestLTime": "12:00:23 AM",
                                    "TimeSinceLastPassed": "-",
                                    "PenaltyFlags": "0",
                                },
                                {
                                    "CustID": "3",
                                    "HeatNo": "69" if new_race else "-1",
                                    "RacerName": "Racer 3",
                                    "AutoNo": "33",
                                    "AMBTime": "339211088",
                                    "LTime": "45.678",
                                    "LapNum": "2",
                                    "BestLTime": "23.645",
                                    "Position": "3",
                                    "GapToLeader": "1.175",
                                    "HeatRanking": None,
                                    "LastPassedTime": "5/10/2022 9:38:49 PM",
                                    "DlTime": "12:00:23 AM",
                                    "DBestLTime": "12:00:23 AM",
                                    "TimeSinceLastPassed": "-",
                                    "PenaltyFlags": "0",
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        if not race_running:
            mock_response.json.return_value["Messages"][0]["Args"][0][
                "LapsLeft"
            ] = "Race finished!!"
            mock_response.json.return_value["Messages"][0]["Args"][0]["Winners"] = [
                {
                    "CustImage": "http://127.0.0.1/CustomerPictures/default.jpg",
                    "KartNo": "11",
                    "RacerName": "Racer 1",
                    "BestLap": "22.47",
                    "Laps": "3",
                    "TrackRecord": "22.47",
                },
                {
                    "CustImage": "http://127.0.0.1/CustomerPictures/default.jpg",
                    "KartNo": "22",
                    "RacerName": "Racer 2",
                    "BestLap": "23.241",
                    "Laps": "3",
                    "TrackRecord": "23.241",
                },
                {
                    "CustImage": "http://127.0.0.1/CustomerPictures/default.jpg",
                    "KartNo": "33",
                    "RacerName": "Racer 3",
                    "BestLap": "23.645",
                    "Laps": "3",
                    "TrackRecord": "23.645",
                },
            ]

            mock_get_info.return_value = {
                "Atlanta": {
                    69: {
                        "heat_id": 1,
                        "race_type": RaceTypes.STANDARD,
                        "win_cond": WinConditions.BEST_LAP,
                        "time": now,
                        "track": 1,
                        "sessions": [
                            {
                                "name": "Racer 1",
                                "rid": 1,
                                "pos": 1,
                                "score": 10,
                                "lap_data": [
                                    (22.47, 1),
                                    (23.456, 1),
                                    (22.68, 1),
                                ],
                            },
                            {
                                "name": "Racer 2",
                                "rid": 2,
                                "pos": 2,
                                "score": 4,
                                "lap_data": [
                                    (23.241, 2),
                                    (34.567, 2),
                                    (23.116, 2),
                                ],
                            },
                            {
                                "name": "Racer 2",
                                "rid": 3,
                                "pos": 3,
                                "score": 2,
                                "lap_data": [
                                    (23.645, 3),
                                    (45.678, 3),
                                    (23.405, 3),
                                ],
                            },
                        ],
                    }
                }
            }

    else:
        mock_response.status = 500
        mock_response.json.return_value = None

    try:
        await watch_location(mock_logger, loc, None)
    except CancelledError:
        pass

    if not good_response:
        mock_logger.error.assert_called_once_with(
            "Got %s error watching for %s data", 500, loc["location"]
        )
        mock_get_info.assert_not_called()
        mock_k1db.add_heats.assert_not_called()
        mock_k1db.add_sessions.assert_not_called()

    elif race_running or not new_race:
        mock_get_info.assert_not_called()
        mock_k1db.add_heats.assert_not_called()
        mock_k1db.add_sessions.assert_not_called()

    else:
        mock_logger.debug.assert_any_call(
            "%s race beginning at %s UTC has finished", loc["location"], now.time()
        )
        mock_logger.debug.assert_any_call(
            "Saved data for %s %s race", now.time(), loc["location"]
        )
        mock_k1db.add_heats.assert_called_once_with(
            None,
            {
                "location": loc["location"],
                "track": 1,
                "time": now,
                "race_type": RaceTypes.STANDARD,
                "win_cond": WinConditions.BEST_LAP,
            },
        )

        mock_k1db.add_sessions.assert_called_once_with(
            None,
            [
                {
                    "rid": 1,
                    "location": loc["location"],
                    "track": 1,
                    "time": now,
                    "kart": 11,
                    "score": 10,
                    "pos": 1,
                    "times": [(22.47, 1), (23.456, 1), (22.68, 1)],
                },
                {
                    "rid": 2,
                    "location": loc["location"],
                    "track": 1,
                    "time": now,
                    "kart": 22,
                    "score": 4,
                    "pos": 2,
                    "times": [(23.241, 2), (34.567, 2), (23.116, 2)],
                },
                {
                    "rid": 3,
                    "location": loc["location"],
                    "track": 1,
                    "time": now,
                    "kart": 33,
                    "score": 2,
                    "pos": 3,
                    "times": [(23.645, 3), (45.678, 3), (23.405, 3)],
                },
            ],
        )

        for i in range(1, 4):
            mock_k1db.add_racer.assert_any_call(None, i, f"Racer {i}")


def test_history_parser(blank_db):
    hist_path = Path(__file__).parents[1].joinpath("data", "history.html")

    parser = HistoryParser(LOCATIONS["atlanta"])
    parser.feed(hist_path.read_text())
    result = parser.data

    assert "Jeremy Brown" == parser.display_name
    assert 451 == len(result["sessions"]["Atlanta"])
    assert {
        "heat_id": 159218,
        "kart": 25,
        "location": "Atlanta",
        "time": datetime(2022, 4, 28, 1, 30, tzinfo=utc),
    } == result["sessions"]["Atlanta"][0]


@pytest.mark.parametrize(
    "heat_type",
    [
        "standard",
        "junior",
        "drift",
        "ball",
        "grid",
        "practice",
        "qual",
        "final",
        "unk_type",
        "unk_cond",
    ],
)
def test_heat_parser(heat_type, blank_db):
    heat_path = Path(__file__).parents[1].joinpath("data", f"{heat_type}.html")
    parser = HeatParser(LOCATIONS["atlanta"])

    if heat_type not in ("unk_type", "unk_cond"):
        parser.feed(heat_path.read_text())
        result = parser.data

        if heat_type == "qual":
            assert 147204 == result["heat_id"]
            assert WinConditions.BEST_LAP == result["win_cond"]
            assert datetime(2021, 9, 5, 23, 10, tzinfo=utc) == result["time"]
            assert 1 == result["track"]
            assert 5 == len(result["sessions"])
            assert RaceTypes.QUALIFIER == result["race_type"]

        elif heat_type == "standard":
            assert RaceTypes.STANDARD == result["race_type"]

        elif heat_type == "junior":
            assert RaceTypes.JUNIOR == result["race_type"]

        elif heat_type == "drift":
            assert RaceTypes.DRIFT == result["race_type"]

        elif heat_type == "ball":
            assert RaceTypes.BALL_CHALLENGE == result["race_type"]

        elif heat_type == "grid":
            assert RaceTypes.GRID_RACE == result["race_type"]

        elif heat_type == "practice":
            assert RaceTypes.PRACTICE == result["race_type"]

        elif heat_type == "final":
            assert RaceTypes.FINAL == result["race_type"]

    else:
        with pytest.raises(ValueError):
            parser.feed(heat_path.read_text())
