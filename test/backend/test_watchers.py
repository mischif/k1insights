from unittest.mock import patch

import pytest

from k1stats.common.constants import LOCATIONS


@pytest.mark.asyncio
@patch("k1stats.backend.watchers.create_task_group")
async def test_start_watchers(mock_task_group, blank_db):
    from k1stats.backend.watchers import start_watchers

    mock_task_group.return_value.__aenter__.return_value = mock_task_group

    await start_watchers()

    for loc in LOCATIONS.values():
        assert any(
            [c.args[2] == loc for c in mock_task_group.start_soon.call_args_list]
        )


@pytest.mark.parametrize("debug", [True, False])
@patch("k1stats.backend.watchers.run")
def test_main(mock_run, debug, blank_db):
    from k1stats.backend.watchers import main, start_watchers

    args = ["-d"] if debug else []

    main(args)

    mock_run.assert_called_once_with(start_watchers, backend_options={"debug": debug})
