"""The lineage's event log (SPEC §15, SPEC-v3 §11.1): one SQLite file per lineage, append-only.
Everything the Lab, the story and the showcase's evidence are read from."""
import contextvars
import json
import sqlite3

HTTP = contextvars.ContextVar("http", default=None)   # the HTTP calls of the thought being made, for its rows in `calls` (Engine.call; brains/model.py)

SCHEMA = """
CREATE TABLE IF NOT EXISTS pets (pet TEXT PRIMARY KEY, name TEXT, parent TEXT, gen INT, laid INT, born INT, died INT,
    cause TEXT, genome TEXT, temper TEXT, record TEXT);
CREATE TABLE IF NOT EXISTS kinship (parent TEXT, child TEXT, tick INT);
CREATE TABLE IF NOT EXISTS messages (pet TEXT, tick INT, kind TEXT, to_pet TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS claims (claim INT, pet TEXT, tick INT, kind TEXT, text TEXT, relation TEXT, truth TEXT, gen INT);
CREATE TABLE IF NOT EXISTS rooms (room TEXT, type TEXT, tick INT, by TEXT, seed TEXT);
CREATE TABLE IF NOT EXISTS bits (pet TEXT, tick INT, room TEXT, bit TEXT, what TEXT);
CREATE TABLE IF NOT EXISTS events (tick INT, day INT, kind TEXT, room TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS creatures (tick INT, kind TEXT, room TEXT, pet TEXT, what TEXT);
CREATE TABLE IF NOT EXISTS moments (n INT, tick INT, day INT, hour REAL, kind TEXT, text TEXT, pet TEXT, room TEXT);
CREATE TABLE IF NOT EXISTS steps (pet TEXT, tick INT, day INT, phase TEXT, stage TEXT, room TEXT, action TEXT, kind TEXT,
    reason TEXT, feedback TEXT, deltas TEXT, own TEXT, needs TEXT, tags TEXT, exploit TEXT);
CREATE TABLE IF NOT EXISTS intentions (pet TEXT, tick INT, started INT, day INT, room TEXT, why TEXT, thought TEXT,
    intention TEXT, steps TEXT, expect TEXT, ended TEXT, score TEXT, tags TEXT, rule_scored INT, deltas TEXT,
    meter INT, visitor_present INT);
CREATE TABLE IF NOT EXISTS calls (pet TEXT, tick INT, kind TEXT, why TEXT, seconds REAL, failed TEXT, chars INT,
    http INT, finish TEXT, prompt_tokens INT, completion_tokens INT, wait REAL);
    -- one row per HTTP call (http: 1 to 4 within the thought), or one for a thought that made none (a stub);
    -- the thought's last row carries its verdict (failed) and how long it waited for its turn (wait). REVIEW-v4.0.4 C4, §8
CREATE TABLE IF NOT EXISTS beliefs (pet TEXT, tick INT, belief TEXT, op TEXT, statement TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS sleeps (pet TEXT, tick INT, day INT, dream TEXT, changes TEXT, review TEXT, project TEXT);
CREATE TABLE IF NOT EXISTS genomes (pet TEXT, tick INT, day INT, genome TEXT, cause TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS stages (pet TEXT, tick INT, day INT, stage_from TEXT, stage_to TEXT);
CREATE TABLE IF NOT EXISTS social (tick INT, from_pet TEXT, to_pet TEXT, kind TEXT, text TEXT, reply INT);
CREATE TABLE IF NOT EXISTS chronicle (day INT, summary TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS inscriptions (id INT, tick INT, room TEXT, place TEXT, text TEXT, by TEXT, medium TEXT, what TEXT, actor TEXT);
CREATE TABLE IF NOT EXISTS songs (id TEXT, tick INT, name TEXT, notes TEXT, by TEXT, parent TEXT, how TEXT, family INT);
CREATE TABLE IF NOT EXISTS radio (tick INT, room TEXT, source TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS library (pet TEXT, tick INT, question TEXT, title TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS doing (pet TEXT, tick_from INT, tick_to INT, what TEXT, passive INT, by TEXT, text TEXT,
                                  still INT, rest INT, room TEXT, x INT, y INT, thing TEXT, walked INT);
    -- still: the ticks of it spent in one place; rest: in a resting pose; thing: what it handled (v3.4); walked: tiles walked since the row before
CREATE TABLE IF NOT EXISTS traits (pet TEXT, tick INT, day INT, trait TEXT, text TEXT);   -- SPEC-v3.5 §2.3: a body trait felt (the same one once a world hour at most)
CREATE INDEX IF NOT EXISTS doing_pet ON doing (pet, tick_from);
CREATE INDEX IF NOT EXISTS steps_pet ON steps (pet, tick);
CREATE INDEX IF NOT EXISTS intentions_pet ON intentions (pet, tick);
"""


def open_db(path, readonly=False):
    """`readonly`: a finished run opened to be looked at. Its log is not written, not even to add a table.
    (19 October 2026, REVIEW-v4.0.4 A2: write-ahead logging, so the Lab, a script or sqlite3 can read the log while the
    engine writes it, and a wait of five seconds for a lock rather than "database is locked".)"""
    if readonly:
        db = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        db.execute("PRAGMA busy_timeout=5000")
        return db
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.executescript(SCHEMA)
    for table, cols in (("doing", ("thing TEXT", "walked INT")),   # a log begun before SPEC-v3.4 gets its two new columns
                        ("calls", ("http INT", "finish TEXT", "prompt_tokens INT", "completion_tokens INT", "wait REAL"))):   # ... and before v4.0.6, five
        have = {r[1] for r in db.execute("PRAGMA table_info(%s)" % table)}
        for col in cols:
            if col.split()[0] not in have:
                db.execute("ALTER TABLE %s ADD COLUMN %s" % (table, col))
    return db


def put(db, table, **row):
    """Append one row. Dicts and lists are stored as JSON. The caller commits (once a tick)."""
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in row.values()]
    db.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join(row), ",".join("?" * len(row))), vals)


def pet_row(db, pet, record=None):
    """The one row per pet that is kept up to date: who it is, when it lived, and at the end its life record."""
    db.execute("INSERT OR REPLACE INTO pets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
               (pet["id"], pet["name"], pet["parent"], pet["gen"], pet["laid"], pet["born"], pet["died"], pet["cause"],
                json.dumps(pet["genome"]), json.dumps(pet["temper"]), json.dumps(record) if record else None))
