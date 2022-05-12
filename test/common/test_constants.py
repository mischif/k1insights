import pytest


@pytest.mark.parametrize("scenario", ["no-path", "bad-path", "good-path"])
def test_db_path(scenario, tmp_path, monkeypatch):
    db_path = tmp_path.joinpath("test.db")

    if scenario != "no-path":
        monkeypatch.setenv("K1_DATA_DB", str(db_path.absolute()))

    if scenario == "good-path":
        db_path.touch()

    if scenario == "no-path":
        with pytest.raises(RuntimeError):
            from k1stats.common.constants import DB_PATH
    elif scenario == "bad-path":
        with pytest.raises(ValueError):
            from k1stats.common.constants import DB_PATH
    else:
        from k1stats.common.constants import DB_PATH

        assert db_path.absolute() == DB_PATH
