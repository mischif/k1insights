from unittest.mock import patch

import pytest

from k1insights.tools.create_db import main


@pytest.mark.parametrize(
    "exists, overwrite", [[False, False], [True, False], [True, True]]
)
@patch("k1insights.tools.create_db.exit")
def test_main(mock_exit, exists, overwrite, tmp_path):
    dest_path = tmp_path.joinpath("test_create_db.db")

    if exists:
        dest_path.touch()

    args = [str(dest_path.absolute())]

    if overwrite:
        args.append("-f")

    main(args)

    assert dest_path.is_file()

    if not exists or overwrite:
        assert dest_path.stat().st_size > 0
        mock_exit.assert_called_once_with(0)

    elif exists and not overwrite:
        assert dest_path.stat().st_size == 0
        mock_exit.assert_called_once_with(1)
