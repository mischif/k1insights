from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

from flask import g, render_template
from flask.views import View

from k1stats.common.constants import LOCATION_LOOKBACK_DAYS, K1Location
from k1stats.common.db import K1DB


class LocationView(View):
    methods = ["GET"]

    def dispatch_request(self, **kwargs: dict[str, Any]) -> str:
        loc = cast(K1Location, kwargs["loc"])
        loc_str = loc["location"]
        url_loc = loc_str.replace(" ", "_").lower()
        then = datetime.utcnow().date() - timedelta(days=LOCATION_LOOKBACK_DAYS)
        times = {}
        all_karts: set[int] = set()

        for track in range(1, loc["tracks"] + 1):
            track_times = K1DB.location_ftd(g.db, loc_str, then, track)
            times[track] = track_times

            for day_times in track_times.values():
                all_karts.update(cast(dict[int, float], day_times).keys())

        ctx = {
            "records": times,
            "all_karts": all_karts,
            "url_loc": url_loc,
            "location": loc_str,
        }
        return render_template("location.html", **ctx)
