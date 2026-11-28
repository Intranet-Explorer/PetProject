"""SPEC-v4.2 §0 and §0.1 item 6: the rehearsal. A copy of live's data/, the migration run on it and reported, then
forty world days in turbo with every v4.2 switch on (the live profile), and a report: deaths by cause, tracebacks,
failed thoughts and talks, and the Lab's Spirit numbers at the end. Never on data/ itself.

    uv run python -m engine.rehearse --to ../PetProject-tests/v4.2 [--days 40] [--model-migration] [--fresh]

SPEC-v5.0 §0, §7 (--v5): the same, with [v5] on: v5.0's migration too (items by kind before and after, the
clear-out), the first board, and at the end idle share, jobs by taker, deficits opened and closed, made for what, the
scrap flow, and items broken and mended, summed over the days.

    uv run python -m engine.rehearse --to ../PetProject-tests/v5.0 --days 10 --v5

The forty days are the stub brain's (forty world days of the real model would be a day of its time): the engine, the
deaths, the director's rules and the ledger are the real ones; the failed-thought and failed-talk rates of a stub are
not the model's, so the migration, which asks the model for the voice cards, can be run on the real model
(--model-migration) and its calls are reported apart.
"""
import argparse
import asyncio
import json
import logging
import shutil
import sqlite3
import time
from collections import Counter
from pathlib import Path

from . import contracts as K
from .tick import Engine, model_brains, stub_brains
from .world import alive, load_config

ROOT = Path(__file__).resolve().parent.parent


class Count(logging.Handler):
    """Every logged traceback and warning, counted by its first line."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.tb, self.warn = Counter(), Counter()

    def emit(self, r):
        msg = r.getMessage().split("\n")[0][:120]
        (self.tb if r.exc_info else self.warn)[msg] += 1


def copy(src, dest):
    """data/ to dest/data: every file, and each SQLite log through its own backup (a running house's WAL included)."""
    if dest.exists():
        raise SystemExit("%s is there already: --fresh to replace it" % dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("lineage.db", "lineage.db-wal", "lineage.db-shm", "server.log*", "model.busy"))
    for db in src.rglob("lineage.db"):
        if db.stat().st_size:
            out = dest / db.relative_to(src)
            with sqlite3.connect("file:%s?mode=ro" % db, uri=True) as a, sqlite3.connect(out) as b:
                a.backup(b)


def thoughts(eng, since):
    """Thoughts and talks asked since `since`, and how many failed (a thought's last row carries its verdict)."""
    rows = eng.db.execute("SELECT kind, failed FROM calls WHERE tick >= ? AND wait IS NOT NULL", (since,)).fetchall()
    by = Counter(k for k, _ in rows)
    bad = Counter(k for k, f in rows if f)
    return {k: {"asked": by[k], "failed": bad[k]} for k in sorted(by)}


def v5_report(h, first_board, start, tpd):
    """SPEC-v5.0's numbers over the rehearsal's days (contracts.counts, summed), and the first and last boards."""
    days = range(h["clock"]["day"] - round((h["tick"] - start) / tpd), h["clock"]["day"] + 1)
    total = {k: Counter() for k in K.COUNTS}
    for d in days:
        for k in K.COUNTS:   # (v5.0's: counts() also has v5.1's, which v51_report sums)
            total[k].update(K.counts(h, d)[k])
    names = {p["id"]: p.get("name") or p["id"] for p in h["pets"].values()}
    by = lambda c: {names.get(k, k): v for k, v in c.most_common()}
    idle = {names.get(p, p): round(total["idle"][p] / total["awake"][p], 3) for p in total["awake"] if total["awake"][p]}
    B = (h.get("v5") or {}).get("board") or {}
    return {"idle_share": idle, "idle_share_house": round(sum(total["idle"].values()) / max(1, sum(total["awake"].values())), 3),
            "jobs_by_taker": by(total["taken"]), "jobs_by_kind": dict(total["taken_kind"]), "deficits_opened": dict(total["opened"]),
            "deficits_closed": dict(total["closed"]), "made_for": dict(total["made_for"]), "scrap_earned": by(total["scrap_earned"]),
            "scrap_spent": by(total["scrap_spent"]), "broke": dict(total["broke"]), "mended": dict(total["mended"]), "verbs": dict(total["verbs"]),
            "scrap_now": {names[p["id"]]: p.get("scrap", 0) for p in alive(h)}, "first_board": first_board,
            "last_board": {"deficits": [(d.get("kind"), d.get("words")) for d in B.get("deficits", [])], "jobs": [(j.get("words"), names.get(j.get("taker"), j.get("taker"))) for j in B.get("jobs", [])]},
            "counted_days": len(days)}


def v51_report(eng, start, tpd, out):
    """SPEC-v5.1's numbers (the owner's list for the rehearsal, 21 October 2026): the migration's report (parts coverage of
    every kind, the verb mismatches against kinds.toml), the house's tier over the days, what each hob knows, inventions
    proposed / accepted / refused with the refusal words, things made by recipe or invention, reads by source."""
    from . import grammar
    h, cfg = eng.house, eng.cfg
    days = range(h["clock"]["day"] - round((h["tick"] - start) / tpd), h["clock"]["day"] + 1)
    total = {k: Counter() for k in K.COUNTS51}
    for d in days:
        for k in K.COUNTS51:
            total[k].update(K.counts(h, d)[k])
    names = {p["id"]: p.get("name") or p["id"] for p in h["pets"].values()}
    knows = {}
    for p in alive(h):
        ks = p.get("knows") if isinstance(p.get("knows"), dict) else {}
        knows[names[p["id"]]] = {"tier": grammar.tier(h, cfg, p), "recipes": sorted(k for k, v in ks.items() if not K.knowledge(v)["of"]),
                                 "knowing_of": sorted(k for k, v in ks.items() if K.knowledge(v)["of"])}
    mig = out / "data" / "migration-v5.1.txt"
    new = {k: {f: r.get(f) for f in ("parts", "verbs", "tier", "by", "how", "for", "charge", "sprite")} for k, r in (h.get("invented") or {}).items() if (r.get("tick") or 0) >= start and r.get("how")}
    return {"migration": mig.read_text().splitlines() if mig.exists() else [], "house_tier": grammar.house_tier(h, cfg), "tier_by_day": dict((h.get("v5") or {}).get("tier") or {}),
            "tier_fall": (h.get("v5") or {}).get("tier_fall"), "knows": knows,
            "invent": dict(total["invent"]), "refused": dict(total["refused"].most_common()), "made_by": dict(total["made_by"]),
            "studied": {names.get(k, k): v for k, v in total["studied"].items()}, "taught": {names.get(k, k): v for k, v in total["taught"].items()},
            "reads_by_source": dict(total["read"]), "chains": {names.get(k, k): v for k, v in total["chain"].items()}, "sprites": dict(total["sprites"]),
            "invented": new, "questions": dict((h.get("v5") or {}).get("questions51") or {}),
            "inventions_waiting": [{"what": j.get("words"), "blocked": j.get("blocked"), "by": names.get(j.get("taker"), j.get("taker"))}
                                   for j in ((h.get("v5") or {}).get("board") or {}).get("jobs", []) if j.get("invent")]}


def v53_report(eng, start, tpd, out):
    """SPEC-v5.3 §6, §8: the scenes found (scenes.py) and, for each that wasn't, the missing rule; idle share with the
    reading hour out (house and per hob); habits by hob; projects by state and kind; marks; talks by rounds; threads."""
    from . import scenes
    h = eng.house
    days = range(h["clock"]["day"] - round((h["tick"] - start) / tpd), h["clock"]["day"] + 1)
    total = {k: Counter() for k in K.COUNTS + K.COUNTS53}
    for d in days:
        c = K.counts(h, d)
        for k in total:
            total[k].update(c[k])
    names = {p["id"]: p.get("name") or p["id"] for p in h["pets"].values()}
    idle_key = "idle53" if total["idle53"] else "idle"
    idle = {names.get(p, p): round(total[idle_key][p] / total["awake"][p], 3) for p in total["awake"] if total["awake"][p]}
    V = h.get("v5") or {}
    projects = [K.project(x) for x in (V.get("projects") or {}).values()]
    found = scenes.find(h, start, tpd)
    return {"scenes": {s: len(v) for s, v in found.items()}, "scene_examples": {s: v[:3] for s, v in found.items()}, "missing": scenes.missing(h, start, tpd),
            "idle_key": idle_key, "idle_share": idle, "idle_share_house": round(sum(total[idle_key].values()) / max(1, sum(total["awake"].values())), 3),
            "over_15": sorted(n for n, v in idle.items() if v > 0.15),
            "habits": {names[p["id"]]: [(K.habit(x)["name"], K.habit(x)["target"], K.habit(x)["count"]) for x in p.get("habits") or []] for p in alive(h)},
            "habit_goes": dict(total["habit"]), "marks": dict(total["marks"]), "noticed": dict(total["noticed"]),
            "projects_by_state": dict(Counter(p["state"] for p in projects)), "projects_by_kind": dict(Counter(p["kind"] for p in projects)),
            "projects": [(p["kind"], p["state"], [names.get(o, o) for o in p["owners"]], round(p["progress"], 2), p["goal"]) for p in projects],
            "project_changes": dict(total["projects"]), "steps": {names.get(k, k): v for k, v in total["steps"].items()},
            "talk_rounds": dict(total["rounds"]), "threads": dict(total["threads"]), "third": {names.get(k, k): v for k, v in total["third"].items()},
            "events": {k: len(K.events53(h, k, start)) for k in K.EVENTS53}, "counted_days": len(days),
            # v5.3.1: what the hobs hatched in the rehearsal drew, by template (their drawn habits, not those picked up later)
            "draws": dict(Counter(K.habit(x)["name"] for p in h["pets"].values() if (p.get("born") or -1) >= start
                                  for x in p.get("habits") or [] if K.habit(x)["from"] not in ("tale", "parent")).most_common()),
            "drawn_by": {names[p["id"]]: [K.habit(x)["name"] for x in p.get("habits") or [] if K.habit(x)["from"] not in ("tale", "parent")]
                         for p in h["pets"].values() if (p.get("born") or -1) >= start and p.get("habits")}}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True)
    ap.add_argument("--days", type=float, default=40)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--model-migration", action="store_true")
    ap.add_argument("--v5", action="store_true")
    ap.add_argument("--v51", action="store_true")
    ap.add_argument("--v53", action="store_true")   # SPEC-v5.3: habits, projects, talk3 on (implies --v51); §6's scenes
    ap.add_argument("--from", dest="src", default=str(ROOT / "data"))   # (a worktree has no data/: the live checkout's, copied read-only)   # SPEC-v5.1: the grammar, knowledge and the book on (implies --v5)
    a = ap.parse_args()
    a.v51 = a.v51 or a.v53
    a.v5 = a.v5 or a.v51
    out = Path(a.to).resolve()
    assert ROOT / "data" not in (out, *out.parents) and Path(a.src).resolve() not in (out, *out.parents), "never on data/ itself"
    if a.fresh and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(out / "rehearsal.log")])
    seen = Count()
    logging.getLogger().addHandler(seen)
    copy(Path(a.src), out / "data")
    report = {"started": time.strftime("%Y-%m-%d %H:%M"), "days": a.days}

    cfg = load_config(profile="live")
    cfg["clock"]["turbo"] = True
    assert K.on(cfg) and all(K.on(cfg, p) for p in K.PARTS), "the live profile has every v4.2 part on"
    if a.v5:
        cfg["v5"].update(on=True)
        assert all(K.on5(cfg, p) for p in K.PARTS5), "every v5.0 part on"
    if a.v51:
        assert all(K.on51(cfg, p) for p in ("grammar", "knowledge", "book2")), "the v5.1 parts on ([sprites2] stays the owner's)"
    if a.v53:
        assert all(K.on53(cfg, p) for p in K.PARTS53) and cfg["jobs"].get("stages"), "every v5.3 part on"

    # the migration, on the restart as on live (§1.4, §6.5)
    t0 = time.monotonic()
    eng = Engine(cfg, out / "data", model_brains if a.model_migration else stub_brains)
    report["migration"] = await eng.spirit_migration()
    report["migration_seconds"] = round(time.monotonic() - t0, 1)
    report["migration_calls"] = thoughts(eng, eng.house["tick"])
    if a.v5:   # (SPEC-v5.0 §6: as the engine runs it, at the first tick with [items] on)
        report["migration_v5"] = eng.items_migration()
    eng.close()

    # forty world days in turbo, the stub's
    eng = Engine(cfg, out / "data", stub_brains)
    idle_why = {}
    if a.v51:   # (21 October 2026: what a hob held in each idle tick, to test whether a blocked job keeps its taker idle)
        from . import body, jobs, planner
        was = jobs.counted

        def counted(house, cfg_, p):
            before = K.counts(house)["idle"].get(p["id"], 0)
            was(house, cfg_, p)
            if K.counts(house)["idle"].get(p["id"], 0) > before:
                blocked = any(j.get("invent") and j.get("blocked") and j["taker"] == p["id"] for j in jobs.board(house)["jobs"])
                a_ = planner.current(p) or {}
                why = "%s; aim %s%s; doing %s" % ("holds a blocked invention" if blocked else "no blocked invention", a_.get("kind"),
                                                 " (a question)" if a_.get("from") == "question" else "", (body.state(p)["now"] or {}).get("name"))
                idle_why.setdefault(p.get("name") or p["id"], Counter())[why] += 1
        jobs.counted = counted
    start, t0, tpd = eng.house["tick"], time.monotonic(), cfg["ticks_per_day"]
    before = {p["id"] for p in alive(eng.house)}
    first_board = None
    kept = {}   # (the counters keep fourteen days; a forty-day rehearsal keeps every one here)
    for i in range(round(a.days * tpd)):
        await eng.tick()
        if a.v5 and first_board is None and (eng.house.get("v5") or {}).get("board", {}).get("deficits"):
            first_board = json.loads(json.dumps(eng.house["v5"]["board"]))   # (the first scan's board, as it stood)
        if i % 300 == 0:
            eng.save()
        if i % tpd == 0:
            kept.update(json.loads(json.dumps((eng.house.get("v5") or {}).get("counts") or {})))
            logging.info("rehearsal: day %d of %d, %d alive, %.0f s", i // tpd, a.days, len(alive(eng.house)), time.monotonic() - t0)
        if eng.house["lineage"]["ended"] is not None:
            logging.warning("rehearsal: the family died out at tick %d", eng.house["tick"])
            break
    eng.save()
    h = eng.house
    if kept:   # (after the last save: only the reports read the days the house let go)
        h.setdefault("v5", {})["counts"] = {**kept, **(h["v5"].get("counts") or {})}
    dead = [p for p in h["pets"].values() if p["stage"] == "dead" and (p.get("died") or 0) >= start]
    causes = Counter(K.OLD_CAUSE.get(p.get("cause"), p.get("cause")) for p in dead)
    n, D = len(dead), cfg["deaths"]["rates"]
    report.update(seconds=round(time.monotonic() - t0), ticks=h["tick"] - start, alive_before=len(before), alive_after=len(alive(h)),
                  hatched=sum(1 for p in h["pets"].values() if (p.get("born") or -1) >= start),
                  deaths={c: {"n": causes[c], "share": round(causes[c] / n, 3) if n else 0, "target": D.get(c), "over_double": bool(n and D.get(c) and causes[c] / n > 2 * D[c] and causes[c] > 1)} for c in K.CAUSES},
                  died=[{"name": p.get("name"), "stage": p.get("stage_before"), "cause": p.get("cause"), "words": p.get("cause_words"), "day": round((p["died"] - start) / tpd, 1)} for p in dead],
                  tracebacks=sum(seen.tb.values()), traceback_kinds=seen.tb.most_common(10), warnings=seen.warn.most_common(10),
                  step_errors={k: v[1] for k, v in getattr(eng, "step_errors", {}).items()},
                  thoughts=thoughts(eng, start))
    from . import lab4
    report["spirit"] = lab4.spirit(eng)
    if a.v5:
        report["v5"] = v5_report(h, first_board, start, tpd)
    if a.v51:
        report["v51"] = v51_report(eng, start, tpd, out)
        report["v51"]["idle_why"] = {n: dict(c.most_common(12)) for n, c in idle_why.items()}
    if a.v53:
        report["v53"] = v53_report(eng, start, tpd, out)
    eng.close()
    (out / "rehearsal.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: report[k] for k in ("seconds", "ticks", "alive_before", "alive_after", "hatched", "tracebacks", "deaths")}, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
