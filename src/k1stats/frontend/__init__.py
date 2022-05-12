from __future__ import annotations

from pathlib import Path

from flask import Flask, abort, g
from werkzeug.routing import BaseConverter

from k1stats.common.constants import DB_PATH, LOCATIONS, K1Location
from k1stats.common.db import K1DB
from k1stats.frontend.index import IndexView
from k1stats.frontend.kart import KartView
from k1stats.frontend.location import LocationView


class LocationConverter(BaseConverter):
    def to_python(self, value: str) -> K1Location:
        if value in LOCATIONS:
            return LOCATIONS[value]
        else:
            abort(404, f"{value} is not a valid K1 location")


app = Flask(
    __name__.split(".")[0],
    static_folder=str(Path(__file__).parent / "static"),
    template_folder=str(Path(__file__).parent / "templates"),
)
app.url_map.converters["location"] = LocationConverter
app.add_url_rule("/", view_func=IndexView.as_view("render_index"))
app.add_url_rule(
    "/locations/<location:loc>", view_func=LocationView.as_view("render_location")
)
app.add_url_rule(
    "/locations/<location:loc>/karts/<int:kart>",
    view_func=KartView.as_view("render_kart"),
)


@app.before_request
def get_db() -> None:
    g.db = K1DB.connect(app.logger, DB_PATH)


@app.teardown_request
def close_db(exc: BaseException | None) -> None:
    K1DB.close(g.db)
