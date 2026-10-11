"""How alive is the house (SPEC-v3.3 §0, §8)? The §0 numbers, per pet per world day, from a house's own log.

    uv run python -m engine.alive DATA_DIR [--since TICK]                    # measure what its log already holds
    uv run python -m engine.alive DATA_DIR --stub DAYS [--profile v31check]  # first live it on with stub brains (a COPY only)

Everything is counted in watching time on the live clock (config.live.toml: a tick is 4 real seconds), whatever
clock the house was run on, since that is the clock Tyler watches."""
import argparse
import asyncio
import sqlite3
import time
from collections import Counter
from pathlib import Path

from .world import load_config

WINDOW, STILL, THINGS, PASSIVE = 300, 30, 5, 0.25   # §0: any 5 minutes, 30 seconds, 5 different things, under a quarter


def measure(data, since=0, show=True):
    """{(pet, day): {things, windows_ok, still, on_tile, passive, awake}} and the house's calls per live hour."""
    live = load_config(profile="live")
    real = live["clock"]["tick_seconds"] * live["pace"]   # watching seconds per tick
    per_day, win = live["ticks_per_day"], round(WINDOW / real)
    db = sqlite3.connect("file:%s?mode=ro" % next(Path(data).glob("lineage-*/lineage.db")), uri=True)
    rows = db.execute("SELECT pet, tick_from, tick_to, what, passive, by, still, rest, x, y FROM doing WHERE tick_to > ? ORDER BY pet, tick_to, tick_from", (since,)).fetchall()
    out, by_pet = {}, {}
    for r in rows:
        by_pet.setdefault(r[0], []).append(r)
    for pet, rs in by_pet.items():
        first, last = max(since, min(r[1] for r in rs)), max(r[2] for r in rs)
        what, passive, asleep = {}, set(), set()
        for _, a, b, w, pas, by, still, rest, x, y in rs:
            for t in range(max(a, first), b + 1):   # (the tick it finished on is part of it)
                what[t] = w if by != "body" or still else "(on its way)"   # a thing it set out to do and never began is only walking
                (asleep if by == "sleep" else passive if pas else set()).add(t)
        for day in range(first // per_day, last // per_day + 1):
            lo, hi = max(first, day * per_day), min(last, (day + 1) * per_day)
            awake = [t for t in range(lo, hi) if t not in asleep]
            if len(awake) < win:
                continue
            counts = [len({what.get(t) for t in range(s, s + win)} - {None}) for s in range(lo, hi - win, 5)
                      if not any(t in asleep for t in (s, s + win // 2, s + win - 1))]
            if not counts:
                continue   # never five minutes awake together that day: nothing to measure
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
                               "awake": len(awake) * real / 60, "nothing": idle * real, "top": Counter(what[t] for t in awake if t in what).most_common(4)}
    span = db.execute("SELECT min(tick), max(tick) FROM calls WHERE tick > ?", (since,)).fetchone()
    calls = {}
    if span[0] is not None and span[1] > span[0]:
        hours = (span[1] - max(since, span[0])) * real / 3600
        for pet, kind, n in db.execute("SELECT pet, kind, count(*) FROM calls WHERE tick > ? GROUP BY 1, 2", (since,)):
            calls[(pet, kind)] = n / hours
    steps = dict(db.execute("SELECT action, count(*) FROM steps WHERE tick > ? GROUP BY 1", (since,)).fetchall())
    nuzzle = (steps.get("nuzzle", 0) + steps.get("accept", 0)) / max(1, sum(steps.values()))
    names = dict(db.execute("SELECT pet, coalesce(name, pet) FROM pets"))
    if show:
        print("%-10s %4s %7s %8s %7s %8s %8s %7s  %s" % ("pet", "day", "things", "windows", "still", "on tile", "passive", "awake", "mostly"))
        for (pet, day), m in sorted(out.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            ok = m["things"] >= THINGS and m["still"] <= STILL and m["passive"] < PASSIVE
            print("%-10s %4d %7d %7.0f%% %6.0fs %7.0fs %7.0f%% %6.0fm  %s %s" % (
                (names.get(pet) or pet)[:10], day + 1, m["things"], 100 * m["windows_ok"], m["still"], m["on_tile"], 100 * m["passive"], m["awake"],
                "ok  " if ok else "FAIL", ", ".join("%s %d" % (w, n) for w, n in m["top"])))
        print("model calls per live hour:", ", ".join("%s %s %.1f" % (names.get(p) or p, k, n) for (p, k), n in sorted(calls.items())) or "none")
        print("nuzzle and accept: %.0f%% of %d decided steps" % (100 * nuzzle, sum(steps.values())))
    return out, calls, nuzzle


def passes(out):
    """Does every pet on every day meet §0's three body numbers?"""
    return bool(out) and all(m["things"] >= THINGS and m["still"] <= STILL and m["passive"] < PASSIVE for m in out.values())


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
