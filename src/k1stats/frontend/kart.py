from datetime import datetime, timedelta

from flask import g, render_template
from flask.views import View

from k1stats.common.constants import KART_LOOKBACK_DAYS
from k1stats.common.db import K1DB


class KartView(View):
    methods = ["GET"]

    def dispatch_request(self, loc, kart):
        loc_str = loc["location"]
        url_loc = loc_str.replace(" ", "_").lower()
        then = datetime.utcnow().date() - timedelta(days=KART_LOOKBACK_DAYS)
        times = {}

        for track in range(1, loc["tracks"] + 1):
            track_times = K1DB.location_ftd(g.db, loc_str, then, track, kart)
            times[track] = track_times

        ctx = {"records": times, "url_loc": url_loc, "location": loc_str, "kart": kart}
        return render_template("kart.html", **ctx)
