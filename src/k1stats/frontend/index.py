from __future__ import annotations

from flask import render_template
from flask.views import View

from k1stats.common.constants import LOCATIONS


class IndexView(View):
    methods = ["GET"]

    def dispatch_request(self) -> str:
        ctx = {
            "locations": sorted(
                (loc["location"], url_loc) for (url_loc, loc) in LOCATIONS.items()
            )
        }
        return render_template("index.html", **ctx)
