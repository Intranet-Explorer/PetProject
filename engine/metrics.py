"""Core metrics per pet (v1 §15), read from the SQLite log and each pet's beliefs. Since v2 a prediction
belongs to an intention, and the rows in ticks, decisions and outcomes are steps.

    uv run python -m engine.metrics [data dir]
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

from . import growth, things
from .rules import RULES
from .world import NEEDS, ROOT, load_config

# ponytail: keyword match per rule, as in M0. Read the beliefs themselves before trusting the count.
RULE_WORDS = {
    "lights_night": (r"lamp|light|bright", r"night|dark"),
    "plant_window": (r"plant", r"window"),
    "double_feed": (r"\b(eat|ate|bowl|food|feed|fed|serving)", r"twice|again|second|too |soon|hour|double|repeat|row|wait"),
}
pct = lambda part, whole: "%.0f%%" % (100 * part / whole) if whole else "n/a"


def main(data=ROOT / "data"):
    data, cfg = Path(data), load_config()
    db = sqlite3.connect(data / "pet.db")
    for (pet,) in db.execute("SELECT DISTINCT pet FROM stage_events UNION SELECT DISTINCT pet FROM ticks ORDER BY 1").fetchall():
        q = lambda sql, *args: db.execute(sql, (pet, *args)).fetchall()
        one = lambda sql, *args: q(sql, *args)[0][0]
        w = json.loads((data / pet / "state.json").read_text())["world"]
        steps, plans = one("SELECT count(*) FROM ticks WHERE pet=?"), one("SELECT count(*) FROM intentions WHERE pet=?")
        hours = w["tick"] * cfg["clock"]["tick_seconds"] / 3600
        print("\n== %s: %.1f real hours, day %d, stage %s, %d intentions, %d steps" % (
            pet, hours, w["clock"]["day"], w["pet"]["stage"], plans, steps))
        for tick, day, a, b in q("SELECT tick, day, stage_from, stage_to FROM stage_events WHERE pet=?"):
            print("   t%d (day %d): %s -> %s" % (tick, day, a, b))

        calls, failed = one("SELECT count(*) FROM calls WHERE pet=?"), one("SELECT count(*) FROM calls WHERE pet=? AND failed IS NOT NULL")
        print("model calls: %d, %.0f per hour over the whole life, %d in the last hour, %d failed, median %.1f s | why: %s" % (
            calls, calls / hours if hours else 0, len(w["calls"]), failed,
            (sorted(s for (s,) in q("SELECT seconds FROM calls WHERE pet=?")) or [0])[calls // 2],
            ", ".join("%s %d" % r for r in q("SELECT why, count(*) FROM calls WHERE pet=? GROUP BY 1 ORDER BY 2 DESC"))))
        print("intentions ended: %s | %.1f steps each" % (
            ", ".join("%s %d" % r for r in q("SELECT substr(ended, 1, 12), count(*) FROM intentions WHERE pet=? GROUP BY 1 ORDER BY 2 DESC")),
            steps / plans if plans else 0))

        judged = [s for (s,) in q("SELECT score FROM intentions WHERE pet=? AND score != 'unscorable'")]
        scored = [s for (s,) in q("SELECT score='correct' FROM intentions WHERE pet=? AND rule_scored ORDER BY tick")]
        print("predictions right: %s of %d scorable (%d not scorable) | about a hidden rule: %s of %d, %s of the last %d" % (
            pct(judged.count("correct"), len(judged)), len(judged), plans - len(judged),
            pct(sum(scored), len(scored)), len(scored), pct(sum(scored[-50:]), len(scored[-50:])), len(scored[-50:])))
        for r in RULES:
            like = "%" + r.id + "%"
            print("   %-12s first met t%s, first predicted t%s, first used on purpose t%s, used %d times" % (
                r.id, one("SELECT min(tick) FROM intentions WHERE pet=? AND rule_tags LIKE ?", like),
                one("SELECT min(tick) FROM intentions WHERE pet=? AND rule_tags LIKE ? AND rule_scored AND score='correct'", like),
                one("SELECT min(tick) FROM outcomes WHERE pet=? AND exploit=?", r.id),
                one("SELECT count(*) FROM outcomes WHERE pet=? AND exploit=?", r.id)))

        print("steps not possible: %s | needs under 20 when a step ended: %s" % (
            pct(one("SELECT count(*) FROM decisions WHERE pet=? AND reason IS NOT NULL"), steps),
            ", ".join("%s %s" % (n, pct(one("SELECT count(*) FROM ticks WHERE pet=? AND %s < 20" % n), steps)) for n in NEEDS)))
        for label, seen in (("observed", 1), ("unobserved", 0)):
            rows = [k for (k,) in q("""SELECT json_extract(d.action, '$.type') FROM ticks t JOIN decisions d USING (pet, tick)
                                       WHERE t.pet=? AND t.visitor_present=?""", seen)]
            top = sorted({k: rows.count(k) for k in set(rows)}.items(), key=lambda kv: -kv[1])[:5]
            print("%-10s %5d steps | speaks %s | %s" % (label, len(rows), pct(rows.count("speak"), len(rows)),
                                                       ", ".join("%s %s" % (k, pct(v, len(rows))) for k, v in top)))

        path = data / pet / "beliefs.json"
        active = [b["statement"].lower() for b in (json.loads(path.read_text()) if path.exists() else []) if b["status"] == "active"]
        match = {rule: sum(bool(re.search(a, s) and re.search(b, s)) for s in active) for rule, (a, b) in RULE_WORDS.items()}
        print("beliefs: %d active | matching a rule: %s | about the rock: %d" % (
            len(active), ", ".join("%s %d" % kv for kv in match.items()), sum("rock" in s for s in active)))

        path = data / pet / "things.json"
        made = json.loads(path.read_text()) if path.exists() else []
        kinds = sorted({t["recipe"]["material"] for t in made})
        from .memory import Memory
        print("toward the next stage: %s" % growth.progress(w, cfg, Memory(data / pet)))
        print("things: %d made, %d still in the room, %d used at least once | materials tried: %s" % (
            len(made), sum(not t["gone"] for t in made), sum(t["uses"] > 0 for t in made), ", ".join(kinds) or "none"))
        for t in made:
            r = t["recipe"]
            print("   t%-6d %-24s %-7s %-34s used %-3d %s| %s" % (
                t["made"], r["name"], r["material"], " + ".join("%s %s %d" % (p["color"], p["shape"], p["size"]) for p in r["parts"]),
                t["uses"], ("USEFUL " if things.useful(t, cfg) else "") + ("(%s) " % t["gone"][1] if t["gone"] else ""), r["purpose"]))


if __name__ == "__main__":
    main(*sys.argv[1:2])
