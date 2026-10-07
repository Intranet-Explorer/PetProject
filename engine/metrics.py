"""Core metrics per pet (SPEC §15), read from the SQLite log and each pet's beliefs.

    uv run python -m engine.metrics
"""
import json
import re
import sqlite3

from .rules import RULES
from .world import NEEDS, ROOT

# ponytail: keyword match per rule, as in M0. Read the beliefs themselves before trusting the count.
RULE_WORDS = {
    "lamp_night": (r"lamp|light", r"night|dark"),
    "plant_window": (r"plant", r"window"),
    "double_feed": (r"\b(eat|ate|bowl|food|feed|fed|serving)", r"twice|again|second|too |soon|hour|double|repeat|row|wait"),
}
pct = lambda part, whole: "%.0f%%" % (100 * part / whole) if whole else "n/a"


def main(data=ROOT / "data"):
    db = sqlite3.connect(data / "pet.db")
    for (pet,) in db.execute("SELECT DISTINCT pet FROM ticks ORDER BY pet").fetchall():
        q = lambda sql, *args: db.execute(sql, (pet, *args)).fetchall()
        one = lambda sql, *args: q(sql, *args)[0][0]
        ticks = one("SELECT count(*) FROM ticks WHERE pet=?")
        print("\n== %s: %d waking ticks, day %d, stage %s" % (
            pet, ticks, one("SELECT max(day) FROM ticks WHERE pet=?"),
            one("SELECT stage FROM ticks WHERE pet=? ORDER BY tick DESC LIMIT 1")))
        for tick, day, a, b, acc, used in q("SELECT tick, day, stage_from, stage_to, accuracy, exploits FROM stage_events WHERE pet=?"):
            print("   t%d (day %d): %s -> %s, accuracy %s, exploits %s" % (tick, day, a, b, acc, used))

        scored = [s for (s,) in q("SELECT score='correct' FROM outcomes WHERE pet=? AND rule_scored ORDER BY tick")]
        print("rule-tagged accuracy: %s over all %d, %s over the last 50" % (
            pct(sum(scored), len(scored)), len(scored), pct(sum(scored[-50:]), len(scored[-50:]))))
        for r in RULES:
            like = "%" + r.id + "%"
            print("   %-12s first seen t%s, first predicted t%s, first exploited t%s, exploited %d times" % (
                r.id, one("SELECT min(tick) FROM outcomes WHERE pet=? AND rule_tags LIKE ?", like),
                one("SELECT min(tick) FROM outcomes WHERE pet=? AND rule_tags LIKE ? AND rule_scored AND score='correct'", like),
                one("SELECT min(tick) FROM outcomes WHERE pet=? AND exploit=?", r.id),
                one("SELECT count(*) FROM outcomes WHERE pet=? AND exploit=?", r.id)))

        print("invalid-action rate: %s" % pct(one("SELECT count(*) FROM decisions WHERE pet=? AND reason IS NOT NULL"), ticks))
        print("time in distress: " + ", ".join(
            "%s %s" % (n, pct(one("SELECT count(*) FROM ticks WHERE pet=? AND %s < 20" % n), ticks)) for n in NEEDS))

        for label, seen in (("observed", 1), ("unobserved", 0)):
            rows = q("""SELECT json_extract(d.action, '$.type'), o.score FROM ticks t
                        JOIN decisions d USING (pet, tick) JOIN outcomes o USING (pet, tick)
                        WHERE t.pet=? AND t.visitor_present=?""", seen)
            mix = {}
            for kind, _ in rows:
                mix[kind] = mix.get(kind, 0) + 1
            judged = [s for _, s in rows if s != "unscorable"]
            top = ", ".join("%s %s" % (k, pct(v, len(rows))) for k, v in sorted(mix.items(), key=lambda kv: -kv[1])[:4])
            print("%-10s %6d ticks | speaks %s | all-prediction accuracy %s | %s" % (
                label, len(rows), pct(mix.get("speak", 0), len(rows)), pct(judged.count("correct"), len(judged)), top))

        path = data / pet / "beliefs.json"
        active = [b["statement"].lower() for b in (json.loads(path.read_text()) if path.exists() else []) if b["status"] == "active"]
        match = {rule: sum(bool(re.search(a, s) and re.search(b, s)) for s in active) for rule, (a, b) in RULE_WORDS.items()}
        print("beliefs: %d active | matching a rule: %s | about the rock: %d" % (
            len(active), ", ".join("%s %d" % kv for kv in match.items()), sum("rock" in s for s in active)))


if __name__ == "__main__":
    main()
