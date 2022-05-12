from datetime import datetime
from unittest.mock import patch

import pytest


@pytest.mark.parametrize("scenario", ["bad-start", "good-start", "no-start"])
@patch("k1stats.tools.add_racer.exit")
@patch("k1stats.tools.add_racer.K1DB")
@patch("k1stats.tools.add_racer.get_racer_data")
@patch("k1stats.tools.add_racer.getLogger")
def test_main(mock_logger, mock_get_data, mock_k1db, mock_exit, scenario, blank_db):
    from k1stats.tools.add_racer import main

    args = ["123"]

    if scenario == "bad-start":
        args.extend(["-s", "1234-56-78", "-f"])

    elif scenario == "good-start":
        args.extend(["-s", "2022-04-20", "-t"])
        mock_get_data.return_value = None

    else:
        mock_get_data.return_value = {
            "sessions": [
                {
                    "kart": 1,
                    "location": "Atlanta",
                    "pos": 1,
                    "score": 1212,
                    "time": datetime(2022, 1, 1),
                    "times": [
                        (36.173, 5),
                        (37.703, 11),
                        (45.985, 11),
                        (27.234, 4),
                        (24.194, 1),
                    ],
                    "track": 1,
                    "type": 0,
                    "win_cond": 0,
                },
                {
                    "kart": 2,
                    "location": "Atlanta",
                    "pos": 2,
                    "score": 1234,
                    "time": datetime(2022, 1, 2),
                    "times": [
                        (52.668, 4),
                        (24.421, 1),
                        (24.963, 2),
                        (24.06, 2),
                        (24.711, 2),
                    ],
                    "track": 1,
                    "type": 0,
                    "win_cond": 0,
                },
            ],
            "id": 123,
            "name": "Test Racer",
        }

    try:
        main(args)
    except SystemExit:
        if scenario == "bad-start":
            pass
        else:
            raise

    if scenario == "good-start":
        mock_exit.assert_called_once_with(1)
    elif scenario == "no-start":
        mock_exit.assert_called_once_with(0)
