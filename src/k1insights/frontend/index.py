################################################################################
#                               K1 Data Insights                               #
#   Capture K1 results to find hidden trends; pls don't call it data science   #
#                            (C) 2022, Jeremy Brown                            #
#                Released under Prosperity Public License 3.0.0                #
################################################################################

from __future__ import annotations

from flask import render_template
from flask.views import View

from k1insights.common.constants import LOCATIONS


class IndexView(View):
    methods = ["GET"]

    def dispatch_request(self) -> str:
        ctx = {
            "locations": sorted(
                (loc["location"], url_loc) for (url_loc, loc) in LOCATIONS.items()
            )
        }
        return render_template("index.html", **ctx)
