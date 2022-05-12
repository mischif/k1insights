from datetime import datetime
from functools import partial
from operator import itemgetter
from sqlite3 import PARSE_DECLTYPES, DatabaseError, Row, connect, register_converter


class K1DB:

    session_times = itemgetter(*(f"lap_{i}" for i in range(1, 51)))
    get_best_lap = partial(lambda s: min(filter(None, K1DB.session_times(s))))

    @staticmethod
    def make_timestamp(ts):
        return datetime.fromisoformat(ts.decode())

    @staticmethod
    def connect(logger, db_path):
        result = None
        db = connect(db_path, detect_types=PARSE_DECLTYPES)

        if db is not None:
            try:
                tegridy = db.execute("PRAGMA integrity_check").fetchone()[0]
                fk = db.execute("PRAGMA foreign_key_check").fetchone()
            except DatabaseError:
                logger.error("K1_DATA_DB does not contain path to valid database")
            else:
                if tegridy != "ok":
                    logger.error("Database failed integrity checks")
                elif fk is not None:
                    logger.error("Database failed foreign key checks")
                else:
                    db.row_factory = Row
                    db.execute("PRAGMA foreign_keys = true")
                    result = db
        return result

    @staticmethod
    def close(db):
        db.execute("PRAGMA optimize")
        db.close()

    @staticmethod
    def add_racer(db, racer_id, name, is_fast=False, follow=False):
        with db:
            db.execute(
                """
                INSERT OR IGNORE
                INTO racers
                VALUES (?, ?, ?, ?)
                """,
                (racer_id, name, is_fast, follow),
            )

    @staticmethod
    def add_heats(db, data):
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError("Provide data as dict or list of dicts")

        with db:
            db.executemany(
                """
                INSERT OR IGNORE
                INTO heats (location, track, runtime, type, wincond)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (h["location"], h["track"], h["time"], h["type"], h["win_cond"])
                    for h in data
                ),
            )

    @staticmethod
    def add_sessions(db, data):
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError("Provide data as dict or list of dicts")

        with db:
            for session in data:
                hid = db.execute(
                    """
                    SELECT hid FROM heats
                    WHERE location = ? AND track = ? AND runtime = ?
                    """,
                    (session["location"], session["track"], session["time"]),
                ).fetchone()["hid"]

                session["hid"] = hid

            db.executemany(
                """
                INSERT OR IGNORE
                INTO sessions
                VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
                )
                """,
                (
                    (
                        s["hid"],
                        s["id"],
                        s["pos"],
                        s["kart"],
                        s["score"],
                        *(t[0] for t in s["times"]),
                        *(None for _ in range(50 - len(s["times"]))),
                    )
                    for s in data
                ),
            )

    # @staticmethod
    # def last_heats(db):
    #   result = {}

    #   with db:
    #       for heat in db.execute(
    #           """
    #           SELECT location, track, runtime
    #           FROM heats
    #           GROUP BY location, track
    #           ORDER BY runtime DESC
    #           """).fetchall():
    #           loc = result.setdefault(heat["location"], {})
    #           loc[heat["track"]] = heat["runtime"]

    #   return result

    @staticmethod
    def location_ftd(db, loc, since, track=1, kart=None):
        result = {}

        with db:
            for session in db.execute(
                """
                SELECT *
                FROM heats NATURAL JOIN sessions
                WHERE location = ? AND track = ? AND runtime >= ?
                """,
                (loc, track, since),
            ).fetchall():

                best_lap = K1DB.get_best_lap(session)

                if kart is None:
                    heat_date = result.setdefault(session["runtime"].date(), {})
                    curr_best = heat_date.get(session["kart"], 300)

                    if best_lap < curr_best:
                        heat_date[session["kart"]] = best_lap

                elif session["kart"] == kart:
                    curr_best = result.get(session["runtime"].date(), 300)

                    if best_lap < curr_best:
                        result[session["runtime"].date()] = best_lap

        return result

    @staticmethod
    def create_db(dest):
        db = connect(dest)
        db.executescript(
            """
            CREATE TABLE racers (
                rid INTEGER PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                fast INTEGER NOT NULL,
                follow INTEGER NOT NULL,
                CHECK (
                LENGTH(name) > 0
                AND fast BETWEEN 0 AND 1
                AND follow BETWEEN 0 AND 1
                ));

            CREATE TABLE heats (
                hid INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                location TEXT NOT NULL,
                track INTEGER NOT NULL,
                runtime TIMESTAMP NOT NULL,
                type INTEGER NOT NULL,
                wincond INTEGER NOT NULL,
                CHECK (
                LENGTH(location) > 0
                AND track >= 1
                AND type >= 0
                AND wincond >= 0
                ));

            CREATE UNIQUE INDEX idx_heats_kart_hist ON heats (location,
                                                              track,
                                                              runtime DESC);

            CREATE TABLE sessions (
                hid REFERENCES heats (hid),
                rid REFERENCES racers (rid),
                position INTEGER NOT NULL,
                kart INTEGER NOT NULL,
                end_score INTEGER NOT NULL,
                lap_1 REAL, lap_2 REAL, lap_3 REAL, lap_4 REAL, lap_5 REAL,
                lap_6 REAL, lap_7 REAL, lap_8 REAL, lap_9 REAL, lap_10 REAL,
                lap_11 REAL, lap_12 REAL, lap_13 REAL, lap_14 REAL, lap_15 REAL,
                lap_16 REAL, lap_17 REAL, lap_18 REAL, lap_19 REAL, lap_20 REAL,
                lap_21 REAL, lap_22 REAL, lap_23 REAL, lap_24 REAL, lap_25 REAL,
                lap_26 REAL, lap_27 REAL, lap_28 REAL, lap_29 REAL, lap_30 REAL,
                lap_31 REAL, lap_32 REAL, lap_33 REAL, lap_34 REAL, lap_35 REAL,
                lap_36 REAL, lap_37 REAL, lap_38 REAL, lap_39 REAL, lap_40 REAL,
                lap_41 REAL, lap_42 REAL, lap_43 REAL, lap_44 REAL, lap_45 REAL,
                lap_46 REAL, lap_47 REAL, lap_48 REAL, lap_49 REAL, lap_50 REAL,
                PRIMARY KEY (rid, hid),
                CHECK (
                position >= 1
                AND kart >= 1
                AND end_score >= 1200
                ));

            CREATE INDEX idx_sessions_kart_hist ON sessions (hid, kart);
            """
        )

        K1DB.close(db)


register_converter("timestamp", K1DB.make_timestamp)
