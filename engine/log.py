"""SQLite event log (SPEC §15). Append-only; one row per pet per waking tick, per sleep, per body, per stage."""
import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS ticks (pet TEXT, tick INT, day INT, phase TEXT, energy REAL, comfort REAL,
    curiosity REAL, x INT, y INT, stage TEXT, visitor_present INT);
CREATE TABLE IF NOT EXISTS decisions (pet TEXT, tick INT, thought TEXT, action TEXT, expect TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS outcomes (pet TEXT, tick INT, feedback TEXT, d_energy REAL, d_comfort REAL,
    d_curiosity REAL, score TEXT, rule_tags TEXT, rule_scored INT, exploit TEXT);
CREATE TABLE IF NOT EXISTS beliefs_history (pet TEXT, tick INT, belief TEXT, op TEXT, statement TEXT);
CREATE TABLE IF NOT EXISTS sleeps (pet TEXT, tick INT, day INT, dream TEXT, changes TEXT);
CREATE TABLE IF NOT EXISTS genomes (pet TEXT, tick INT, day INT, genome TEXT, cause TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS stage_events (pet TEXT, tick INT, day INT, stage_from TEXT, stage_to TEXT,
    accuracy INT, exploits TEXT);
"""


def open_db(path):
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    return db


def record(db, r):
    """Store one journal record (see tick.step) across the three per-tick tables."""
    n, d = r["needs"], r["deltas"]
    key = (r["pet"], r["tick"])
    db.execute("INSERT INTO ticks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
               key + (r["day"], r["phase"], n["energy"], n["comfort"], n["curiosity"], r["pos"][0], r["pos"][1],
                      r["stage"], int(r["visitor_present"])))
    db.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?)",
               key + (r["thought"], json.dumps(r["action"]), r["expect"], r["reason"]))
    db.execute("INSERT INTO outcomes VALUES (?,?,?,?,?,?,?,?,?,?)",
               key + (r["feedback"], d["energy"], d["comfort"], d["curiosity"], r["score"],
                      ",".join(r["rule_tags"]), int(r["rule_scored"]), r["exploit"]))
    db.commit()
