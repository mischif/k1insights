from datetime import datetime, timedelta
from os import environ
from pathlib import Path
from random import randint
from unittest.mock import Mock

import pytest

from pytz import utc

from k1insights.backend.clubspeed import RaceTypes, WinConditions
from k1insights.common.db import K1DB


@pytest.mark.parametrize("scenario", ["bad-db", "bad-tegridy", "bad-fk", "good"])
def test_connect(scenario, test_db):
    mock_logger = Mock()

    if scenario == "bad-db":
        p = Path(__file__).parents[1] / "data" / "ball.html"
    elif scenario == "bad-tegridy":
        p = Path(__file__).parents[1] / "data" / "bad_tegridy.db"
    elif scenario == "bad-fk":
        p = Path(__file__).parents[1] / "data" / "bad_fk.db"
    elif scenario == "good":
        p = Path(environ["K1_DATA_DB"])

    result = K1DB.connect(mock_logger, p)

    if scenario != "good":
        assert result is None

        if scenario == "bad-db":
            mock_logger.error.assert_called_once_with(
                "K1_DATA_DB does not contain path to valid database"
            )
        elif scenario == "bad-tegridy":
            mock_logger.error.assert_called_once_with(
                "Database failed integrity checks"
            )
        elif scenario == "bad-fk":
            mock_logger.error.assert_called_once_with(
                "Database failed foreign key checks"
            )
    else:
        assert result is not None
        mock_logger.error.assert_not_called()


def test_add_racer(blank_db):
    K1DB.add_racer(blank_db, 1, "Racer 1")
    K1DB.add_racer(blank_db, 2, "Racer 2", True, True)
    K1DB.add_racer(blank_db, 1, "Racer 1", True, True)

    racer_1 = blank_db.execute("select * from racers where rid = 1").fetchone()
    assert not racer_1["fast"]
    assert not racer_1["follow"]
    assert 2 == blank_db.execute("select count(*) from racers").fetchone()[0]


@pytest.mark.parametrize("scenario", ["single", "multiple", "bad"])
def test_add_heats(scenario, blank_db):
    now = datetime.now(utc).replace(microsecond=0)
    yday = now - timedelta(days=1)

    if scenario == "single":
        heats = {
            "location": "Atlanta",
            "track": 1,
            "race_type": RaceTypes.STANDARD,
            "win_cond": WinConditions.BEST_LAP,
            "time": now,
        }
    elif scenario == "multiple":
        heats = [
            {
                "location": "Atlanta",
                "track": 1,
                "race_type": RaceTypes.STANDARD,
                "win_cond": WinConditions.BEST_LAP,
                "time": now,
            },
            {
                "location": "Atlanta",
                "track": 1,
                "race_type": RaceTypes.JUNIOR,
                "win_cond": WinConditions.BEST_LAP,
                "time": yday,
            },
            {
                "location": "Atlanta",
                "track": 1,
                "race_type": RaceTypes.FINAL,
                "win_cond": WinConditions.POSITION,
                "time": now,
            },
        ]
    elif scenario == "bad":
        heats = None

    if scenario == "bad":
        with pytest.raises(ValueError):
            K1DB.add_heats(blank_db, heats)
    else:
        K1DB.add_heats(blank_db, heats)

        heat_1 = blank_db.execute(
            "select * from heats where runtime = ?", (now,)
        ).fetchone()
        assert RaceTypes.STANDARD == heat_1["type"]
        assert WinConditions.BEST_LAP == heat_1["wincond"]

        heat_count = blank_db.execute("select count(*) from heats").fetchone()[0]
        assert heat_count == 1 if scenario == "single" else 2


@pytest.mark.parametrize("scenario", ["single", "multiple", "bad"])
def test_add_sessions(scenario, blank_db):
    now = datetime.now(utc).replace(microsecond=0)

    if scenario == "single":
        sessions = {
            "rid": 1,
            "pos": 1,
            "kart": 1,
            "track": 1,
            "score": 1206,
            "time": now,
            "location": "Atlanta",
            "times": [(22.47, 1), (23.456, 1), (22.68, 1)],
        }
    elif scenario == "multiple":
        sessions = [
            {
                "rid": 1,
                "pos": 1,
                "kart": 1,
                "track": 1,
                "score": 1206,
                "time": now,
                "location": "Atlanta",
                "times": [(22.47, 1), (23.456, 1), (22.68, 1)],
            },
            {
                "rid": 2,
                "pos": 2,
                "kart": 2,
                "track": 1,
                "score": 1202,
                "time": now,
                "location": "Atlanta",
                "times": [(23.241, 2), (34.567, 2), (23.116, 2)],
            },
            {
                "rid": 1,
                "pos": 1,
                "kart": 3,
                "track": 1,
                "score": 1210,
                "time": now,
                "location": "Atlanta",
                "times": [(23.123, 1), (34.234, 1), (45.345, 1)],
            },
        ]
    elif scenario == "bad":
        sessions = None

    heat = {
        "location": "Atlanta",
        "track": 1,
        "race_type": RaceTypes.STANDARD,
        "win_cond": WinConditions.BEST_LAP,
        "time": now,
    }
    K1DB.add_heats(blank_db, heat)
    K1DB.add_racer(blank_db, 1, "Racer 1")
    K1DB.add_racer(blank_db, 2, "Racer 2")

    if scenario == "bad":
        with pytest.raises(ValueError):
            K1DB.add_sessions(blank_db, sessions)
    else:
        K1DB.add_sessions(blank_db, sessions)

        sess_1 = blank_db.execute(
            "select * from sessions where hid = 1 and rid = 1"
        ).fetchone()
        assert 1 == sess_1["kart"]
        assert 22.47 == sess_1["lap_1"]

        sess_count = blank_db.execute("select count(*) from sessions").fetchone()[0]
        assert sess_count == 1 if scenario == "single" else 2


@pytest.mark.parametrize("scenario", ["date", "kart"])
def test_location_ftd(scenario, test_db):
    then = datetime.now(utc).replace(microsecond=0) - timedelta(days=3)

    if scenario == "date":
        now = datetime.now(utc).replace(microsecond=0)
        today = now.date()

        all_results = K1DB.location_ftd(test_db, "Atlanta", then)
        today_results = all_results[today]

        sessions = test_db.execute(
            "select * from heats natural join sessions where runtime >= ?", (today,)
        ).fetchall()
        for session in sessions:
            assert K1DB.get_best_lap(session) >= today_results[session["kart"]]

    elif scenario == "kart":
        results = sessions = None

        while True:
            kart = randint(1, 10)
            results = K1DB.location_ftd(test_db, "Atlanta", then, kart=kart)
            if len(results) > 1:
                sessions = test_db.execute(
                    "select * from heats natural join sessions where kart = ?", (kart,)
                ).fetchall()
                break

        for session in sessions:
            assert K1DB.get_best_lap(session) >= results[session["runtime"].date()]
