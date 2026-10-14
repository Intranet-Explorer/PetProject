"""SPEC-v3.5.4 §0: the drive bars, from a house's own log (read only).

    uv run python -m engine.bars DATA_DIR [--since TICK] [--until TICK]

Real time is the live clock's (a tick is 4 real seconds). Curiosity and crowding come from `bars.jsonl` in the data
folder when a sampler wrote one (sample()), else from the logged steps and the house as it stands now."""
import argparse
import json
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .world import load_config

DOORS = {"go next door", "peek next door", "explore a doorway", "wander", "go"}   # going, peeking, wandering (§0)
DONT = re.compile(r"^\W*(do not|don't|wait|attend|rest|lie|stay|hold|keep still|be still|let|not\b|never|avoid|refrain|listen|watch the|notice|sit)", re.I)
STOP = set("a an the and or of to in on at for with by from as is are was were be it its this that these those you your we our i my me "
           "not do does did so but if then than when what which who into out up down over under about all any some no".split())


def words(t):
    return {w for w in re.findall(r"[a-z']+", (t or "").lower()) if w not in STOP and len(w) > 2}


def sample(house, cfg, path):
    """One line of what the bars need that the log does not keep: each waking pet's curiosity and comfort, and the made
    things on each room's floor. The copy's sampler calls this every world minute or so."""
    from . import feel, order
    pets = {p["id"]: {"cur": round(p["needs"]["curiosity"], 1), "com": round(p["needs"]["comfort"], 1), "bored": feel.level(p, "curiosity") >= 2, "room": p["room"]}
            for p in house["pets"].values() if p["stage"] not in ("egg", "dead") and not p["sleep"]}
    floors = {r["id"]: order.floor_count(cfg, r) for r in house["rooms"].values() if r["type"]}
    with open(path, "a") as f:
        f.write(json.dumps({"tick": house["tick"], "pets": pets, "floors": floors}) + "\n")


def measure(data, since, until):
    data = Path(data)
    live = load_config(profile="live")
    real = live["clock"]["tick_seconds"] * live["pace"]          # watching seconds per tick
    hour, day = live["ticks_per_hour"], live["ticks_per_day"]
    db = sqlite3.connect("file:%s?mode=ro" % next(data.glob("lineage-*/lineage.db")), uri=True)
    house = json.loads((data / "house.json").read_text())
    until = until or house["tick"]
    days = (until - since) / day
    out = {"window": "ticks %d to %d (%.2f world days)" % (since, until, days)}
    samples = [s for s in (json.loads(l) for l in open(data / "bars.jsonl")) if since <= s["tick"] <= until] if (data / "bars.jsonl").exists() else []

    # curiosity, median while awake
    if samples:
        cur = [p["cur"] for s in samples for p in s["pets"].values()]
        com = [p["com"] for s in samples for p in s["pets"].values()]
    else:
        rows = [json.loads(r[0]) for r in db.execute("SELECT needs FROM steps WHERE tick BETWEEN ? AND ?", (since, until))]
        cur, com = [n["curiosity"] for n in rows], [n["comfort"] for n in rows]
    out["curiosity median"] = "%.0f%%" % statistics.median(cur) if cur else None
    out["comfort median"] = "%.0f%%" % statistics.median(com) if com else None

    # a bored pet does something new within a world hour: goes into a room it has not been in for `stale_hours`, reads
    # or asks, makes a kind it has not made in a world day, finds something out, or does a first
    if samples:
        moves = defaultdict(list)   # pet -> [(tick, room)]
        for pet, b, room in db.execute("SELECT pet, tick_to, room FROM doing WHERE tick_to BETWEEN ? AND ? ORDER BY tick_to", (since - day, until + hour)):
            if not moves[pet] or moves[pet][-1][1] != room:
                moves[pet].append((b, room))
        news = defaultdict(list)
        made = defaultdict(list)
        for pet, t, kind, text in db.execute("SELECT pet, tick, kind, text FROM moments WHERE tick BETWEEN ? AND ?", (since - day, until + hour)):
            if kind in ("read", "discovery", "invented", "tool", "first", "room", "entered", "planted"):
                news[pet].append(t)
            elif kind == "made":
                k = re.search(r" made (?:an? )?(?:\w+ )?(\w[\w ]*?) it calls", text)
                made[pet].append((t, k.group(1) if k else text))
        for pet, ms in made.items():
            for i, (t, k) in enumerate(ms):
                if not any(k == k2 and t - t2 < day for t2, k2 in ms[:i]):
                    news[pet].append(t)
        for pet, mv in moves.items():
            for i, (t, room) in enumerate(mv):
                if not any(r2 == room and t - t2 < live["body"]["stale_hours"] * hour for t2, r2 in mv[:i]) and i:
                    news[pet].append(t)
        onsets, did = 0, 0
        was = {}
        for s in samples:
            for pet, p in s["pets"].items():
                if p["bored"] and not was.get(pet):
                    onsets += 1
                    did += any(s["tick"] <= t <= s["tick"] + hour for t in news[pet])
                was[pet] = p["bored"]
        out["bored, then something new within a world hour"] = "%d of %d times" % (did, onsets)

    # thoughts only because nothing else is going on
    why = Counter(r[0] for r in db.execute("SELECT why FROM calls WHERE kind='act' AND tick BETWEEN ? AND ?", (since, until)))
    acts = sum(why.values())
    out["thoughts from 'nothing to do'"] = "%.0f%% of %d" % (100 * why["nothing to do"] / acts, acts) if acts else None

    # rooms: stays, bounces, doors
    rows = db.execute("SELECT pet, tick_from, tick_to, what, room FROM doing WHERE tick_to BETWEEN ? AND ? ORDER BY pet, tick_to", (since, until)).fetchall()
    stays, changes, back, door_t, awake_t = [], 0, 0, 0, 0
    per = defaultdict(list)
    for r in rows:
        per[r[0]].append(r)
    for pet, rs in per.items():
        visits = []   # [room, arrived, left]
        for _, a, b, what, room in rs:
            if what == "asleep":
                visits.append([None, b, b])
                continue
            awake_t += b - a
            door_t += (b - a) if what in DOORS else 0
            if not visits or visits[-1][0] != room:
                if visits:
                    visits[-1][2] = b
                visits.append([room, b, b])
            else:
                visits[-1][2] = b
        awake = [v for v in visits if v[0]]
        for i in range(1, len(visits)):
            if visits[i][0] and visits[i - 1][0] and visits[i][0] != visits[i - 1][0]:
                changes += 1
                if i >= 2 and visits[i - 2][0] == visits[i][0] and visits[i - 1][2] - visits[i - 1][1] <= 360 / real:
                    back += 1
        stays += [(v[2] - v[1]) * real for v in awake[1:-1]]   # (the first and last visits are cut by the window)
    out["stay in a room, median"] = "%.1f real min (%d stays)" % (statistics.median(stays) / 60, len(stays)) if stays else None
    out["straight back within 6 min"] = "%.0f%% of %d room changes" % (100 * back / changes, changes) if changes else None
    out["waking time at doors"] = "%.0f%%" % (100 * door_t / awake_t) if awake_t else None

    # crowding
    cap = live["make"]["crowded"]
    if samples:
        run, worst = defaultdict(int), defaultdict(int)
        last = since
        for s in samples:
            for r, n in s["floors"].items():
                run[r] = run[r] + (s["tick"] - last) if n >= cap else 0
                worst[r] = max(worst[r], run[r])
            last = s["tick"]
        over = {r: round(t / hour, 1) for r, t in worst.items() if t > hour}
        out["rooms at the cap over a world hour"] = "%d %s" % (len(over), over or "")
    else:
        from . import order
        full = {r["name"]: order.floor_count(live, r) for r in house["rooms"].values() if r["type"] and order.floor_count(live, r) >= cap}
        out["rooms at the cap now"] = "%d %s" % (len(full), full)

    # "no room to make"
    told = 0   # (a prompt carries no tick: each pet's last prompts, as many as it was asked in the window, if the window runs to now)
    for p in data.glob("lineage-*/p*/training.jsonl"):
        n = db.execute("SELECT count(*) FROM calls WHERE pet=? AND tick BETWEEN ? AND ?", (p.parent.name, since, until)).fetchone()[0]
        lines = p.read_text().splitlines()[-n:] if n and until >= house["tick"] else []
        told += sum("no room to make" in l or "too crowded for another" in l for l in lines)
    told += db.execute("SELECT count(*) FROM steps WHERE tick BETWEEN ? AND ? AND feedback LIKE '%too crowded%'", (since, until)).fetchone()[0]
    out["'no room to make' told"] = told

    # what was made
    made = [(o["made"]["tick"], o["made"]["recipe"].get("kind")) for r in house["rooms"].values() for o in (r.get("objects") or {}).values() if "made" in o]
    made += [(g["made"], g["recipe"].get("kind")) for g in house.get("gone_things", [])]
    made = [(t, k) for t, k in made if since <= t <= until]
    kinds = Counter(k for _, k in made)
    out["things made"] = len(made)
    out["charms among them"] = "%.0f%%" % (100 * kinds["charm"] / len(made)) if made else None
    by_day = defaultdict(set)
    for t, k in made:
        by_day[int((t - since) // day)].add(k)
    out["kinds made per world day"] = {d: len(k) for d, k in sorted(by_day.items())}
    out["kinds"] = dict(kinds.most_common())

    # firsts, the Works
    feats = [f for f in (house.get("feats") or {}).get("list", []) if since <= f["tick"] <= until]
    fk = Counter(f["kind"] for f in feats)
    out["feats"] = dict(fk)
    out["firsts (house/family/own)"] = dict(Counter(f.get("level") for f in feats if f["kind"] == "first"))
    out["works built"] = [f["text"] for f in feats if f["kind"] == "works"]

    # projects
    living = [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")]
    out["projects"] = {p["name"] or p["id"]: (p.get("project") or {}).get("text") for p in living}
    out["projects that are a don't"] = sum(bool(DONT.search((p.get("project") or {}).get("text") or "")) for p in living)

    # messages: the words a new one shares with its parent's message, and with the pet's own last version
    shared = []
    for pet, tick, text in db.execute("SELECT pet, tick, text FROM messages WHERE kind='message' AND tick BETWEEN ? AND ?", (since, until)):
        parent = (house["pets"].get(pet) or {}).get("parent")
        last = lambda who: (db.execute("SELECT text FROM messages WHERE pet=? AND kind IN ('message','last words') AND tick<? ORDER BY tick DESC LIMIT 1", (who, tick)).fetchone() or [""])[0]
        w = words(text) or {""}
        shared.append("%s: parent's %.0f%%, its own last %.0f%%" % (pet, 100 * len(w & words(last(parent))) / len(w), 100 * len(w & words(last(pet))) / len(w)))
    out["messages: share of words from the parent's / its own last"] = shared

    # model calls per pet per world day
    pets_awake = len({r[0] for r in rows}) or 1
    calls = db.execute("SELECT count(*) FROM calls WHERE tick BETWEEN ? AND ?", (since, until)).fetchone()[0]
    out["model calls per pet per world day"] = round(calls / pets_awake / max(days, 1e-9), 1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--since", type=int, default=0)
    ap.add_argument("--until", type=int, default=0)
    a = ap.parse_args()
    for k, v in measure(a.data, a.since, a.until).items():
        print("%-46s %s" % (k, v))
