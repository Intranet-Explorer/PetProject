"""The Lab's numbers (SPEC §15, SPEC-v3 §11.4), read from the lineage's log and the live house.

    uv run python -m engine.metrics [data dir]      # prints them for the lineage in that folder
"""
import json
import sqlite3
import sys
from pathlib import Path

from . import life, story
from .feel import meter_talk
from .world import NEEDS, ROOT, days as world_days, label, load_config, ticks


def pet_lab(db, house, cfg, pet, beliefs):
    pid = pet["id"]
    q = lambda sql, *a: db.execute(sql, (pid, *a)).fetchall()
    one = lambda sql, *a: q(sql, *a)[0][0]
    plans, steps = one("SELECT count(*) FROM intentions WHERE pet=?"), one("SELECT count(*) FROM steps WHERE pet=?")
    born = pet["born"] or 0
    first_day = born + cfg["ticks_per_day"]
    scored = [s for (s,) in q("SELECT score='correct' FROM intentions WHERE pet=? AND rule_scored ORDER BY tick")]
    judged = [s for (s,) in q("SELECT score FROM intentions WHERE pet=? AND score != 'unscorable'")]
    secs = sorted(s for (s,) in q("SELECT seconds FROM calls WHERE pet=? AND kind='act'"))
    end = pet["died"] if pet["died"] is not None else house["tick"]
    hours = max(1e-9, (end - born) * cfg["clock"]["tick_seconds"] / 3600)
    calls = one("SELECT count(*) FROM calls WHERE pet=?")
    return {
        "id": pid, "name": label(pet), "gen": pet["gen"], "stage": pet["stage"], "cause": pet["cause"],
        "days": round(world_days(cfg, born, end), 1) if pet["born"] is not None else 0,
        "intentions": plans, "steps": steps,
        "meter_all": story.meter_share(db, pid)[0], "meter_after_day1": story.meter_share(db, pid, first_day)[0],
        "meter_beliefs": round(100 * sum(meter_talk(b["statement"]) for b in beliefs) / len(beliefs), 1) if beliefs else None,
        "predictions_right": round(100 * judged.count("correct") / len(judged)) if judged else None, "scorable": len(judged),
        "rule_right": round(100 * sum(scored) / len(scored)) if scored else None, "rule_scored": len(scored),
        "rule_right_recent": round(100 * sum(scored[-50:]) / len(scored[-50:])) if scored else None,
        "not_possible": round(100 * one("SELECT count(*) FROM steps WHERE pet=? AND reason IS NOT NULL") / steps) if steps else None,
        "actions": dict(q("SELECT kind, count(*) FROM steps WHERE pet=? GROUP BY 1 ORDER BY 2 DESC")),
        "calls": calls, "calls_per_hour": round(calls / hours, 1), "calls_last_hour": len(pet.get("calls", [])),
        "call_seconds": secs[len(secs) // 2] if secs else None, "failed": one("SELECT count(*) FROM calls WHERE pet=? AND failed IS NOT NULL"),
        "why": dict(q("SELECT why, count(*) FROM calls WHERE pet=? AND kind='act' GROUP BY 1 ORDER BY 2 DESC")),
        "wellbeing": round(life.wellbeing(pet)) if "well" in pet else (pet.get("life") or {}).get("wellbeing"),
        "exploits": dict(q("SELECT exploit, count(*) FROM steps WHERE pet=? AND exploit IS NOT NULL GROUP BY 1")),
        "rooms": [r for (r,) in q("SELECT DISTINCT room FROM steps WHERE pet=?")],
        "creatures": dict(db.execute("SELECT kind || ': ' || CASE WHEN what LIKE 'fed%' THEN 'fed' ELSE what END, count(*) FROM creatures WHERE pet=? GROUP BY 1", (pid,)).fetchall()),
        "social": dict(db.execute("SELECT kind, count(*) FROM social WHERE from_pet=? GROUP BY 1", (pid,)).fetchall()),
        "replies": db.execute("SELECT count(*) FROM social WHERE from_pet=? AND reply=1", (pid,)).fetchone()[0],
        "low": {n: round(100 * one("SELECT count(*) FROM steps WHERE pet=? AND json_extract(needs, '$.%s') < 20" % n) / steps) if steps else None for n in NEEDS},
        "temper": pet["temper"], "useful": len(pet.get("useful", [])), "made": pet.get("made", 0),
    }


def lab(db, house, cfg, beliefs_of):
    """Everything the Lab tab shows. `beliefs_of(pet)` returns a pet's beliefs, living or dead."""
    lin = house["lineage"]["id"] if house["lineage"] else None
    pets = sorted((p for p in house["pets"].values() if p["lineage"] == lin), key=lambda p: p["laid"])
    hour = ticks(cfg, 3600)
    return {
        "pets": [pet_lab(db, house, cfg, p, beliefs_of(p)) for p in pets if p["stage"] != "egg"][-12:],
        "calls_last_hour": sum(t > house["tick"] - hour for t in house["calls"]), "budget": cfg["model"]["calls_per_hour"],
        "calls_by_kind": dict(db.execute("SELECT kind, count(*) FROM calls GROUP BY 1").fetchall()),
        "v25": {"meter_thoughts": 43.0, "meter_beliefs": 57.9},   # the last v2 life by today's pattern (25.2 by the one of its day, data.v2.5/baseline/meter-talk.json)
        "temper": [{"id": p["id"], "name": label(p), "gen": p["gen"], "temper": p["temper"]} for p in pets],
        "claims": [{"id": c["id"], "text": c["text"], "first": c["first"], "pets": c["pets"], "gens": c["gens"], "forms": c["forms"],
                    "truth": c["truth"]} for c in sorted(house["claims"], key=lambda c: (-len(c["gens"]), -len(c["pets"]), c["id"]))[:30]],
        "claim_rows": dict(db.execute("SELECT relation, count(*) FROM claims GROUP BY 1").fetchall()),
        "rooms": [{"room": r, "type": t, "tick": k, "by": by} for r, t, k, by in db.execute("SELECT room, type, tick, by FROM rooms ORDER BY tick")],
        "events": dict(db.execute("SELECT kind, count(*) FROM events GROUP BY 1").fetchall()),
        "drift": house["lineage"]["drift"] if house["lineage"] else None,
        "deaths": [{"name": label(p), "cause": p["cause"], "days": (p.get("life") or {}).get("days")} for p in pets if p["stage"] == "dead"],
    }


def main(data=ROOT / "data", profile=None):
    data = Path(data)
    house = json.loads((data / "house.json").read_text())
    cfg = load_config(profile=profile or house.get("profile"))
    d = data / ("lineage-%d" % house["lineage"]["id"])
    db = sqlite3.connect(d / "lineage.db")

    def beliefs_of(p):
        path = data / ("lineage-%d" % p["lineage"]) / p["id"] / "beliefs.json"
        return json.loads(path.read_text()) if path.exists() else []
    out = lab(db, house, cfg, beliefs_of)
    print("day %d, %s; lineage %d; calls in the last hour %d of %d" % (house["clock"]["day"], house["clock"]["season"], house["lineage"]["id"], out["calls_last_hour"], out["budget"]))
    for p in out["pets"]:
        print("\n== %s (%s, gen %d): %s, %s days%s" % (p["name"], p["id"], p["gen"], p["stage"], p["days"], ", died of " + p["cause"] if p["cause"] else ""))
        print("   thoughts %d, steps %d (%s%% not possible) | calls %d, %.1f/hour, median %s s, %d failed" % (
            p["intentions"], p["steps"], p["not_possible"], p["calls"], p["calls_per_hour"], p["call_seconds"], p["failed"]))
        print("   meter-talk: %s%% of thoughts (%s%% after day 1), %s%% of beliefs  [v2.5: 43.0%% and 57.9%%]" % (p["meter_all"], p["meter_after_day1"], p["meter_beliefs"]))
        print("   predictions right %s%% of %d | about hidden physics %s%% of %d" % (p["predictions_right"], p["scorable"], p["rule_right"], p["rule_scored"]))
        print("   wellbeing %s | useful things %d of %d made | rooms %d | creatures %s | social %s, %d replies" % (
            p["wellbeing"], p["useful"], p["made"], len(p["rooms"]), p["creatures"], p["social"], p["replies"]))
        print("   actions: %s" % ", ".join("%s %d" % kv for kv in p["actions"].items()))
        print("   temperament: %s" % ", ".join("%s %.2f" % kv for kv in p["temper"].items()))
    print("\nrooms: %s" % ", ".join("%s (%s)" % (r["type"], r["by"]) for r in out["rooms"]))
    print("events: %s | drift: %s" % (out["events"], out["drift"]))
    print("claims: %s" % out["claim_rows"])
    for c in out["claims"][:10]:
        print("   [%d generations, %d pets, %s] %s" % (len(c["gens"]), len(c["pets"]), c["truth"] or "unchecked", c["text"]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
