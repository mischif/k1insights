import sys

from datetime import datetime, timedelta
from random import sample, uniform

import pytest

from pytz import utc

from k1stats.backend.clubspeed import RaceTypes, WinConditions
from k1stats.common.db import K1DB


@pytest.fixture()
def blank_db(tmp_path, monkeypatch):
    db_path = tmp_path.joinpath("test.db")
    monkeypatch.setenv("K1_DATA_DB", str(db_path))
    K1DB.create_db(db_path)
    db = K1DB.connect(None, db_path)
    yield db
    K1DB.close(db)
    sys.modules.pop("k1stats.common.constants", None)


@pytest.fixture()
def test_db(blank_db):
    now = datetime.now(utc).replace(hour=16, microsecond=0)
    then = now - timedelta(hours=2)
    yday = now - timedelta(days=1)
    ereyday = now - timedelta(days=2)
    sessions = []
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
            "race_type": RaceTypes.STANDARD,
            "win_cond": WinConditions.BEST_LAP,
            "time": then,
        },
        {
            "location": "Atlanta",
            "track": 1,
            "race_type": RaceTypes.STANDARD,
            "win_cond": WinConditions.BEST_LAP,
            "time": yday,
        },
        {
            "location": "Atlanta",
            "track": 1,
            "race_type": RaceTypes.STANDARD,
            "win_cond": WinConditions.BEST_LAP,
            "time": ereyday,
        },
    ]

    for heat in heats:
        lap_times = []
        heat_sessions = [
            {
                "track": 1,
                "score": 1200,
                "time": heat["time"],
                "location": "Atlanta",
            },
            {
                "track": 1,
                "score": 1200,
                "time": heat["time"],
                "location": "Atlanta",
            },
            {
                "track": 1,
                "score": 1200,
                "time": heat["time"],
                "location": "Atlanta",
            },
            {
                "track": 1,
                "score": 1200,
                "time": heat["time"],
                "location": "Atlanta",
            },
            {
                "track": 1,
                "score": 1200,
                "time": heat["time"],
                "location": "Atlanta",
            },
        ]

        raw_times = [
            [round(uniform(22, 28), 3) for _ in range(3)]
            for _ in range(len(heat_sessions))
        ]
        min_times = [30 for _ in range(len(heat_sessions))]

        for laps in zip(*raw_times):
            for idx, lap in enumerate(laps):
                if lap < min_times[idx]:
                    min_times[idx] = lap

            temp = {v: k for k, v in enumerate(sorted(min_times))}
            cur_pos = list(map(temp.get, min_times))
            lap_times.append(list(zip(laps, cur_pos)))

        lap_times = list(zip(*lap_times))
        racers = sample(range(1, 11), len(heat_sessions))
        karts = sample(range(1, 11), len(heat_sessions))
        for idx, data in enumerate(zip(racers, karts, lap_times)):
            heat_sessions[idx]["rid"] = data[0]
            heat_sessions[idx]["kart"] = data[1]
            heat_sessions[idx]["times"] = [(t[0], t[1] + 1) for t in data[2]]
            heat_sessions[idx]["pos"] = data[2][-1][1] + 1

        sessions.extend(heat_sessions)

    K1DB.add_racer(blank_db, 1, "Racer 1")
    K1DB.add_racer(blank_db, 2, "Racer 2")
    K1DB.add_racer(blank_db, 3, "Racer 3")
    K1DB.add_racer(blank_db, 4, "Racer 4")
    K1DB.add_racer(blank_db, 5, "Racer 5")
    K1DB.add_racer(blank_db, 6, "Racer 6")
    K1DB.add_racer(blank_db, 7, "Racer 7")
    K1DB.add_racer(blank_db, 8, "Racer 8")
    K1DB.add_racer(blank_db, 9, "Racer 9")
    K1DB.add_racer(blank_db, 10, "Racer 10")
    K1DB.add_heats(blank_db, heats)
    K1DB.add_sessions(blank_db, sessions)
    return blank_db


@pytest.fixture()
def test_client(test_db):
    from k1stats.frontend import app

    app.testing = True
    return app.test_client()
