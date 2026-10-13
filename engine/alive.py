"""How alive is the house (SPEC-v3.3 §0, §8; SPEC-v3.4 §0; SPEC-v3.5 §0)? The §0 numbers, per pet per world day, from a house's own log.

    uv run python -m engine.alive DATA_DIR [--since TICK]                    # measure what its log already holds
    uv run python -m engine.alive DATA_DIR --stub DAYS [--profile v31check]  # first live it on with stub brains (a COPY only)

Everything is counted in watching time on the live clock (config.live.toml: a tick is 4 real seconds), whatever
clock the house was run on, since that is the clock Tyler watches."""
import argparse
import asyncio
import json
import sqlite3
import time
from collections import Counter
from pathlib import Path

from .world import load_config

WINDOW, STILL, THINGS, PASSIVE = 300, 30, 5, 0.25   # v3.3 §0: any 5 minutes, 30 seconds, 5 different things, under a quarter
HANDLED, WALKED = 3, 15   # v3.4 §0: in any 5 minutes, 3 different things handled (fidgets and looking do not count) and 15 tiles walked


def measure(data, since=0, show=True):
    """{(pet, day): {handled, walked, still, ...}} and the house's calls per live hour.
    v3.4: `handled`, `walked` are the fewest in any five minutes awake (`*_ok`: the share of five-minute windows that
    meet the bar); a log from before v3.4 has neither, and they read as None."""
    live = load_config(profile="live")
    real = live["clock"]["tick_seconds"] * live["pace"]   # watching seconds per tick
    per_day, win = live["ticks_per_day"], round(WINDOW / real)
    db = sqlite3.connect("file:%s?mode=ro" % next(Path(data).glob("lineage-*/lineage.db")), uri=True)
    new = {"thing", "walked"} <= {r[1] for r in db.execute("PRAGMA table_info(doing)")}
    rows = db.execute("SELECT pet, tick_from, tick_to, what, passive, by, still, rest, x, y, %s FROM doing WHERE tick_to > ? ORDER BY pet, tick_to, tick_from" % ("thing, walked" if new else "NULL, NULL"), (since,)).fetchall()
    out, by_pet = {}, {}
    for r in rows:
        by_pet.setdefault(r[0], []).append(r)
    for pet, rs in by_pet.items():
        first, last = max(since, min(r[1] for r in rs)), max(r[2] for r in rs)
        what, passive, asleep, held, steps = {}, set(), set(), {}, {}
        for _, a, b, w, pas, by, still, rest, x, y, thing, walked in rs:
            for t in range(max(a, first), b + 1):   # (the tick it finished on is part of it)
                what[t] = w if by != "body" or still else "(on its way)"   # a thing it set out to do and never began is only walking
                (asleep if by == "sleep" else passive if pas else set()).add(t)
            if thing and b >= first:
                held.setdefault(b, set()).add(thing)   # handled on the tick it was done
            for t in range(max(a, first), b + 1) if walked else ():   # the steps it took in doing it, spread over the time it took
                steps[t] = steps.get(t, 0) + walked / (b + 1 - max(a, first))
        for day in range(first // per_day, last // per_day + 1):
            lo, hi = max(first, day * per_day), min(last, (day + 1) * per_day)
            awake = [t for t in range(lo, hi) if t not in asleep]
            if len(awake) < win:
                continue
            starts = [s for s in range(lo, hi - win, 5) if not any(t in asleep for t in (s, s + win // 2, s + win - 1))]
            counts = [len({what.get(t) for t in range(s, s + win)} - {None}) for s in starts]
            if not counts:
                continue   # never five minutes awake together that day: nothing to measure
            n_held = [len(set().union(*(held.get(t, ()) for t in range(s, s + win)))) for s in starts] if new else None
            n_walk = [sum(steps.get(t, 0) for t in range(s, s + win)) for s in starts] if new else None
            # standing still: one thing done on one spot, not in a resting pose; and the longest it kept to one tile
            # (several things in a row without a step between) while not resting
            mine = [r for r in rs if lo <= r[2] <= hi and r[5] != "sleep"]
            one = max((r[6] or 0 for r in mine if not r[7]), default=0)
            idle = sum(1 for t in awake if t not in what)   # awake with nothing logged at all
            tile, run, at = 0, 0, None
            for r in mine:
                walked = (r[2] - r[1]) - (r[6] or 0) > 0
                run = 0 if (r[7] or walked or (r[8], r[9]) != at) else run
                run, at = (0 if r[7] else run + (r[6] or 0)), (r[8], r[9])
                tile = max(tile, run)
            out[(pet, day)] = {"things": min(counts, default=0), "windows_ok": sum(c >= THINGS for c in counts) / max(1, len(counts)),
                               "still": one * real, "on_tile": tile * real, "passive": sum(1 for t in awake if t in passive) / len(awake),
                               "awake": len(awake) * real / 60, "nothing": idle * real, "top": Counter(what[t] for t in awake if t in what).most_common(4),
                               "handled": min(n_held) if new else None, "handled_ok": sum(c >= HANDLED for c in n_held) / len(n_held) if new else None,
                               "walked": min(n_walk) if new else None, "walked_ok": sum(c >= WALKED for c in n_walk) / len(n_walk) if new else None,
                               "typical": (sorted(n_held)[len(n_held) // 2], sorted(n_walk)[len(n_walk) // 2]) if new else None}
    span = db.execute("SELECT min(tick), max(tick) FROM calls WHERE tick > ?", (since,)).fetchone()
    calls = {}
    if span[0] is not None and span[1] > span[0]:
        hours = (span[1] - max(since, span[0])) * real / 3600
        for pet, kind, n in db.execute("SELECT pet, kind, count(*) FROM calls WHERE tick > ? GROUP BY 1, 2", (since,)):
            calls[(pet, kind)] = n / hours
    steps = dict(db.execute("SELECT kind, count(*) FROM steps WHERE tick > ? GROUP BY 1", (since,)).fetchall())
    nuzzle = (steps.get("nuzzle", 0) + steps.get("accept", 0)) / max(1, sum(steps.values()))
    names = dict(db.execute("SELECT pet, coalesce(name, pet) FROM pets"))
    if show:
        # v3.4 §0, per pet per world day: the fewest things handled and tiles walked in any five minutes awake (and how many of the
        # five-minute windows meet the bar; the usual window), the longest stood in one spot outside a resting pose
        print("%-10s %4s  %-13s %-13s %6s %7s %7s  %s" % ("pet", "day", "handled (ok)", "walked (ok)", "still", "usual", "awake", "mostly"))
        for (pet, day), m in sorted(out.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            if m["handled"] is None:
                continue
            print("%-10s %4d  %3d (%3.0f%%)    %3.0f (%3.0f%%)    %5.0fs %3d/%-3.0f %6.0fm  %s %s" % (
                (names.get(pet) or pet)[:10], day + 1, m["handled"], 100 * m["handled_ok"], m["walked"], 100 * m["walked_ok"], m["still"], m["typical"][0], m["typical"][1], m["awake"],
                "ok  " if one_passes(m) else "FAIL", ", ".join("%s %d" % (w, n) for w, n in m["top"])))
        print("thoughts per pet per world day:", ", ".join("%s %.0f" % (names.get(p) or p, n * per_day * real / 3600) for (p, k), n in sorted(calls.items()) if k == "act") or "none")
        print("model calls per live hour:", ", ".join("%s %s %.1f" % (names.get(p) or p, k, n) for (p, k), n in sorted(calls.items())) or "none")
        print("nuzzle and accept: %.0f%% of %d decided steps" % (100 * nuzzle, sum(steps.values())))
    return out, calls, nuzzle


def purpose(data, since=0, show=True):
    """SPEC-v3.4 §0, the rest of it, by world day from a house's own log: wants fulfilled by each pet, things made that
    repeat a kind and material their maker had made before, discoveries, the first tool, food the family grew and
    ate, questions put to the book, and whether anything the box said turned up in a thought, a question or a telling.
    Returns {day: {...}}."""
    import re
    db = sqlite3.connect("file:%s?mode=ro" % next(Path(data).glob("lineage-*/lineage.db")), uri=True)
    house = json.loads((Path(data) / "house.json").read_text())
    names = dict(db.execute("SELECT pet, coalesce(name, pet) FROM pets"))
    names.update({i: p.get("name") or i for i, p in house["pets"].items()})
    day_of = {t: d for t, d in db.execute("SELECT tick, day FROM moments WHERE tick > ?", (since,))}
    days = sorted(set(day_of.values()))
    if not days:
        return {}
    edges = {d: min(t for t, x in day_of.items() if x == d) for d in days}   # the first thing noted each world day: near enough its start
    day_at = lambda tick: max((d for d in days if edges[d] <= tick), default=days[0])
    out = {d: {"wants": Counter(), "made": 0, "repeats": 0, "discoveries": [], "tools": [], "harvests": [], "asked": [], "radio": []} for d in days}
    for d, kind, text, pet in db.execute("SELECT day, kind, text, pet FROM moments WHERE tick > ? ORDER BY tick", (since,)):
        if kind == "want":
            out[d]["wants"][names.get(pet, pet)] += 1
        elif kind in ("discovery", "tool", "harvest"):
            out[d][{"discovery": "discoveries", "tool": "tools", "harvest": "harvests"}[kind]].append(text)
    seen = {}   # (pet, kind, material) made before, all its life
    for pet, tick, action in db.execute("SELECT pet, tick, action FROM steps WHERE kind = 'make' AND (reason IS NULL OR reason = '') ORDER BY tick"):
        r = (json.loads(action).get("recipe") or {})
        key = (pet, r.get("kind"), r.get("material"))
        if tick > since:
            out[day_at(tick)]["made"] += 1
            out[day_at(tick)]["repeats"] += key in seen
        seen[key] = True
    for pet, tick, q, title in db.execute("SELECT pet, tick, question, title FROM library WHERE tick > ?", (since,)):
        out[day_at(tick)]["asked"].append("%s asked \"%s\"%s" % (names.get(pet, pet), q, " and read about %s" % title if title else " and found nothing"))
    long = lambda text: set(re.findall(r"[a-z]{7,}", (text or "").lower()))
    said = {}
    for tick, text in db.execute("SELECT tick, text FROM radio WHERE tick > ?", (since,)):
        said.setdefault(day_at(tick), set()).update(long(text))
    box = re.compile(r"\b(the box|the radio|box said|forecast)\b", re.I)
    for d in days:
        lo, hi = edges[d], min([edges[x] for x in days if x > d] or [10**9])
        heard = said.get(d, set()) | said.get(d - 1, set())
        for what, rows in (("thought", db.execute("SELECT pet, thought FROM intentions WHERE tick > ? AND tick <= ?", (lo, hi)).fetchall()),
                           ("question", db.execute("SELECT pet, question FROM library WHERE tick > ? AND tick <= ?", (lo, hi)).fetchall()),
                           ("telling", db.execute("SELECT from_pet, text FROM social WHERE kind IN ('tell', 'speak') AND tick > ? AND tick <= ?", (lo, hi)).fetchall())):
            for pet, text in rows:
                words = long(text) & heard
                if box.search(text or "") or (what == "question" and words) or len(words) >= 2:
                    out[d]["radio"].append("%s (%s): %s" % (names.get(pet, pet), what, (text or "")[:110]))
    if show:
        print("by world day: wants fulfilled per pet; things made (repeats of a kind and material); discoveries; tools; grown and eaten; book asked; the box in a thought, question or telling")
        for d in days:
            m = out[d]
            print("  day %d: wants %s | made %d (%d repeats) | discoveries %d | tools %d | harvests %d | book %d | radio %d" % (
                d, ", ".join("%s %d" % kv for kv in sorted(m["wants"].items())) or "none", m["made"], m["repeats"], len(m["discoveries"]), len(m["tools"]), len(m["harvests"]), len(m["asked"]), len(m["radio"])))
        for title, key in (("discoveries", "discoveries"), ("tools", "tools"), ("grown and eaten", "harvests"), ("the book", "asked"), ("the box, taken up", "radio")):
            lines = ["day %d: %s" % (d, t) for d in days for t in out[d][key]]
            if lines:
                print(title + ":")
                for line in lines[:40]:
                    print("   " + line[:200])
    return out


def bodies(data, since=0, show=True):
    """SPEC-v3.5 §0, by world day from a house's own log: the kinds invented (and their names), the body-trait sense
    lines each pet felt (a pet is counted on the days it did anything; the same trait is noted once a world hour at
    most), and the births, with those that brought something new. Returns {day: {invented, traits, born, new}}."""
    db = sqlite3.connect("file:%s?mode=ro" % next(Path(data).glob("lineage-*/lineage.db")), uri=True)
    house = json.loads((Path(data) / "house.json").read_text())
    names = dict(db.execute("SELECT pet, coalesce(name, pet) FROM pets"))
    names.update({i: p.get("name") or i for i, p in house["pets"].items()})
    out = {}
    day = lambda d: out.setdefault(d, {"invented": [], "traits": {}, "born": 0, "new": []})
    for d, kind, text in db.execute("SELECT day, kind, text FROM moments WHERE tick > ? AND kind IN ('invented', 'mutation', 'hatched') ORDER BY tick", (since,)):
        if kind == "hatched":
            day(d)["born"] += 1
        else:
            day(d)["invented" if kind == "invented" else "new"].append(text)
    for d, pet in db.execute("SELECT DISTINCT day, pet FROM steps WHERE tick > ? UNION SELECT DISTINCT day, pet FROM sleeps WHERE tick > ?", (since, since)):
        day(d)["traits"].setdefault(names.get(pet, pet), {})
    if db.execute("SELECT count(*) FROM sqlite_master WHERE name = 'traits'").fetchone()[0]:   # (a log from before v3.5 has no such table)
        for d, pet, trait, n in db.execute("SELECT day, pet, trait, count(*) FROM traits WHERE tick > ? GROUP BY 1, 2, 3", (since,)):
            day(d)["traits"].setdefault(names.get(pet, pet), {})[trait] = n
    if show and out:
        print("by world day: kinds invented (the bar: at least 1); body-trait lines felt by each pet (the bar: at least 1 each); births, and those with something new (about 1 in 12)")
        for d in sorted(out):
            m = out[d]
            print("  day %d: invented %d%s | traits %s | births %d%s" % (
                d, len(m["invented"]), " (%s)" % "; ".join(t.split(" invented the ")[-1].split(":")[0] for t in m["invented"]) if m["invented"] else "",
                ", ".join("%s %d%s" % (p, sum(t.values()), " (%s)" % ", ".join("%s %d" % kv for kv in sorted(t.items())) if t else " NONE") for p, t in sorted(m["traits"].items())) or "nobody about",
                m["born"], " (%d new: %s)" % (len(m["new"]), "; ".join(m["new"])) if m["new"] else ""))
        born, new = sum(m["born"] for m in out.values()), sum(len(m["new"]) for m in out.values())
        print("  in all: %d kinds invented over %d days (%d with a use, the rest curios); %d births, %d with something new%s" % (
            sum(len(m["invented"]) for m in out.values()), len(out), sum(1 for v in house.get("invented", {}).values() if v["tick"] > since and v["use"] != "curio"), born, new, " (1 in %.1f)" % (born / new) if new else ""))
        for name, v in house.get("invented", {}).items():
            if v["tick"] > since:
                print("   %s %s (%s): %s joined with %s; %s; %s" % (v["a"], name, v["use"], *v["from"], " + ".join("%s %s%s" % (p["material"], p["part"], " on its " + p["at"] if p["at"] else "") for p in v["parts"]), v["does"]))
    return out


def clutter(data, since=0, show=True):
    """What lay about in each room at each world hour since `since` (the house notes it: director.hourly): {room: [n, ...]}.
    Tidying that works shows as numbers that fall over a world day and stay down."""
    house = json.loads((Path(data) / "house.json").read_text())
    rows = [(t, c) for t, c in house.get("clutter", []) if t > since]
    out = {r["name"]: [c.get(rid) for _, c in rows] for rid, r in house["rooms"].items() if r["type"]}
    if show and rows:
        print("things and bits lying about, by world hour (oldest first; . = not found yet):")
        for name, ns in out.items():
            print("  %-16s %s" % (name[4:] if name.startswith("the ") else name, " ".join("%2s" % ("." if n is None else n) for n in ns)))
    return out


def one_passes(m):
    return m["handled"] is not None and m["handled"] >= HANDLED and m["walked"] >= WALKED and m["still"] <= STILL


def passes(out):
    """Does every pet on every day meet SPEC-v3.4 §0's three body numbers: in any five minutes at least three things
    handled and fifteen tiles walked, and never thirty seconds in one spot outside a resting pose?"""
    return bool(out) and all(one_passes(m) for m in out.values())


async def stub(data, days, profile):
    from .tick import Engine, stub_brains
    cfg = load_config(profile=profile)
    cfg["stub"] = dict(cfg["stub"], paced=True)   # a stub answers at once: have it think as often as a pet would
    eng = Engine(cfg, data, stub_brains)
    start, slow, t0 = eng.house["tick"], 0.0, time.monotonic()
    for _ in range(round(days * cfg["ticks_per_day"])):
        t = time.monotonic()
        await eng.tick()
        slow = max(slow, time.monotonic() - t)
    n = eng.house["tick"] - start
    eng.save()
    eng.close()
    pets = sum(1 for p in eng.house["pets"].values() if p["stage"] not in ("egg", "dead"))
    print("%d ticks with %d pets: %.2f ms a tick, the slowest %.0f ms" % (n, pets, 1000 * (time.monotonic() - t0) / n, 1000 * slow))
    return start


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--since", type=int, default=0)
    ap.add_argument("--stub", type=float, default=0, help="world days to live on with stub brains first (a COPY only)")
    ap.add_argument("--profile", default="v31check")
    a = ap.parse_args()
    since = asyncio.run(stub(a.data, a.stub, a.profile)) if a.stub else a.since
    measure(a.data, since)
    purpose(a.data, since)
    bodies(a.data, since)
    clutter(a.data, since)
