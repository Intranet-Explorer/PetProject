"""The tick (SPEC §7): perceive, act, apply, drift and hidden rules, score, log.

    uv run python -m engine.tick --ticks 3000    # headless run with the twin, prints a summary
"""
import argparse
import json
import re
import tempfile
from collections import Counter, deque
from pathlib import Path

from . import actions, log, rules
from .memory import Memory
from .world import NEEDS, add_event, clock, dist, load_config, near, new_world

RECENT_SHOWN = 4
NOVELTY_MAX, NOVELTY_RECHARGE = 4.0, 15   # curiosity for doing something; ticks per point regained


def perceive(w, cfg, mem):
    """The perception packet: compact plain text, identical in structure for every brain.
    Visitor presence is never stated (§14); only what the visitor did since the last turn."""
    pet, objs, tick = w["pet"], w["objects"], w["tick"]
    nearest = min(objs, key=lambda o: dist(pet["pos"], objs[o]["pos"]))
    trend = pet["trend"]
    needs = ", ".join("%s %d%s" % (n, round(pet["needs"][n]),
                                   " (falling)" if trend.get(n, 0) <= -1 else " (rising)" if trend.get(n, 0) >= 1 else "")
                      for n in NEEDS)
    visible = " · ".join("%s%s (%d,%d)" % (n, " (%s)" % o["state"] if "state" in o else "", *o["pos"])
                         for n, o in objs.items())
    recent = "  ".join("[t%d] %s" % (t, e) for t, e in w["events"][-RECENT_SHOWN:]) or "nothing yet"
    visitor = "; ".join(e[len("visitor "):] for t, e in w["events"] if t == tick and e.startswith("visitor "))
    beliefs = "".join("\n  %s: %s" % (b["id"], b["statement"]) for b in mem.top()) or " none yet"
    return (
        "time: %s (tick %d)\n" % (clock(cfg, tick)["phase"], tick)
        + "you are at: (%d,%d)%s\n" % (*pet["pos"], ", near " + nearest if near(w, nearest) else "")
        + "needs: %s\n" % needs
        + "visible: %s\n" % visible
        + "recent: %s\n" % recent
        + "visitor: %s\n" % (visitor or "nothing new")
        + "your beliefs:%s\n" % beliefs
        + "stage: %s. allowed actions: %s\n" % (pet["stage"], ", ".join(actions.STAGE_ACTIONS[pet["stage"]]))
    )


UP = re.compile(r"\b(up|ris|rais|increas|higher|more|restor|improv|recover|boost|gain|replenish|better)|\+")
DOWN = re.compile(r"\b(down|drop|fall|lower|decreas|less|drain|los|reduc|declin|worse)|(?<![a-z0-9])[-−]")
SAME = re.compile(r"\b(stay|same|unchanged|stabl|steady|no change)")
STATE_WORDS = {
    "lamp": ("lamp|light", {"on": r"\bon\b", "off": r"\boff\b"}),
    "bowl": ("bowl", {"full": r"full|filled", "empty": r"empty"}),
    "music box": ("music", {"playing": r"play|start", "silent": r"silen|stop|quiet"}),
    "window": ("window", {"open": r"open", "closed": r"clos|shut"}),
}


def direction(s):
    if SAME.search(s):
        return 0
    up, down = UP.search(s), DOWN.search(s)
    if not (up or down):
        return None
    return 1 if up and (not down or up.start() < down.start()) else -1


def score(expect, deltas, w):
    """Score an expectation against what happened: (correct | wrong | unscorable, the need it named)."""
    if not isinstance(expect, str):
        return "unscorable", None
    s = expect.lower()
    named = sorted((m.start(), n) for n in NEEDS for m in [re.search(r"\b%s\b" % n, s)] if m)
    if named:
        # ponytail: only the first need named is scored; "energy up, comfort down" counts on energy alone.
        start, need = named[0]
        d = direction(s[start:named[1][0] if len(named) > 1 else len(s)])
        d = direction(s) if d is None else d
        if d is not None:
            actual = (deltas[need] >= 0.5) - (deltas[need] <= -0.5)   # under half a point is "the same"
            return ("correct" if d == actual else "wrong"), need
    for name, (alias, states) in STATE_WORDS.items():
        if re.search(alias, s):
            for state, word in states.items():
                if re.search(word, s):
                    return ("correct" if w["objects"][name]["state"] == state else "wrong"), None
    m = re.search(r"\b(?:near|next to|beside|at|to|by)\s+(?:the\s+)?(%s)\b" % "|".join(w["objects"]), s)
    if m:
        return ("correct" if near(w, m.group(1)) else "wrong"), None
    return "unscorable", None


def drift(w):
    """What every tick does to the needs, before the hidden rules."""
    cozy = near(w, "bed") or near(w, "blanket")
    cold = w["objects"]["window"]["state"] == "open" and w["clock"]["phase"] == "night"
    return {"energy": -0.2, "comfort": -0.1 + 0.3 * cozy - 0.5 * cold, "curiosity": -0.3}


def step(w, cfg, turn, mem, visitor_present=False, pet_id=""):
    """One tick for one pet. `turn` is the brain's reply (a dict, or None if it was not valid JSON).
    Returns the journal record."""
    tick, pet = w["tick"], w["pet"]
    w["clock"] = clock(cfg, tick)
    before = dict(pet["needs"])
    reason = "invalid json" if turn is None else actions.check(turn, w, mem)
    turn = turn if isinstance(turn, dict) else {}
    fx, text = {}, "nothing happened"
    if not reason:
        text, fx, key = actions.apply(w, turn["action"], mem)
        if key:
            gained = min(NOVELTY_MAX, (tick - w["seen"].get(key, -10**6)) / NOVELTY_RECHARGE)
            fx["curiosity"] = fx.get("curiosity", 0) + gained
            w["seen"][key] = tick
    base, fired = drift(w), rules.fired(w, cfg)
    for n in NEEDS:
        change = fx.get(n, 0) + base[n] + sum(r.delta for r in fired if r.need == n)
        pet["needs"][n] = min(100.0, max(0.0, before[n] + change))
    deltas = {n: round(pet["needs"][n] - before[n], 1) for n in NEEDS}
    pet["trend"] = deltas
    result, need = score(turn.get("expect"), deltas, w)
    add_event(w, text + "".join("; " * (i == 0) + ", " * (i > 0) + "%s %+.1f" % nd
                                for i, nd in enumerate((n, d) for n, d in deltas.items() if d)))
    rec = {
        "pet": pet_id, "tick": tick, "day": w["clock"]["day"], "phase": w["clock"]["phase"],
        "stage": pet["stage"], "pos": list(pet["pos"]),
        "before": {n: round(v, 1) for n, v in before.items()},
        "needs": {n: round(v, 1) for n, v in pet["needs"].items()},
        "thought": str(turn.get("thought", ""))[:300], "action": turn.get("action"),
        "expect": str(turn.get("expect", ""))[:200], "reason": reason, "feedback": text, "deltas": deltas,
        "score": result,
        "rule_tags": [r.id for r in fired],
        # Only predictions about a need a hidden rule just moved count toward growth (§10).
        "rule_scored": result != "unscorable" and need in {r.need for r in fired},
        "visitor_present": visitor_present,
    }
    w["tick"] += 1
    return rec


class Pet:
    """One pet's life: its own copy of the world, a brain, memory, and running metrics."""

    def __init__(self, pet_id, cfg, brain, data_dir, db=None):
        self.id, self.cfg, self.brain, self.db = pet_id, cfg, brain, db
        self.dir = Path(data_dir) / pet_id
        self.mem = Memory(self.dir, db, pet_id)
        self.state_path = self.dir / "state.json"
        saved = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.world = saved.get("world") or new_world(cfg)
        self.brain.s = saved.get("brain") or self.brain.s
        self.journal = deque(saved.get("journal", []), maxlen=30)        # what the view shows
        self.window = deque(saved.get("window", []), maxlen=50)          # last 50 rule-scored results
        self.series = saved.get("series", [])                            # [tick, rolling accuracy]

    def accuracy(self):
        return round(100 * sum(self.window) / len(self.window)) if self.window else None

    def tick(self, visitor_present=False):
        turn = self.brain.act(perceive(self.world, self.cfg, self.mem))
        rec = step(self.world, self.cfg, turn, self.mem, visitor_present, self.id)
        if rec["rule_scored"]:
            self.window.append(rec["score"] == "correct")
            self.series.append([rec["tick"], self.accuracy()])
            del self.series[:-600]
        self.journal.append(rec)
        self.mem.journal(rec)
        if self.db:
            log.record(self.db, rec)
        self.save()
        return rec

    def save(self):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"world": self.world, "brain": self.brain.s, "journal": list(self.journal),
                                   "window": list(self.window), "series": self.series}))
        tmp.replace(self.state_path)


def main():
    from .brains.twin import Twin
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=3000)
    args = ap.parse_args()
    cfg = load_config()
    with tempfile.TemporaryDirectory() as d:
        pet = Pet("twin", cfg, Twin(cfg), d, log.open_db(Path(d) / "pet.db"))
        tags, scores, reasons, distress = Counter(), Counter(), Counter(), Counter()
        for i in range(args.ticks):
            # A scripted visitor so every rule gets exercised: two feeds close together, plant to the window.
            if i % 240 in (0, 6):
                actions.visit(pet.world, {"type": "feed"})
            if i == 150:
                actions.visit(pet.world, {"type": "place", "object": "plant", "tile": [1, 4]})
            rec = pet.tick()
            tags.update(rec["rule_tags"])
            scores[rec["score"]] += 1
            reasons[rec["reason"]] += 1
            distress.update(n for n, v in rec["needs"].items() if v < 20)
        print("ticks %d = %.1f world days" % (args.ticks, args.ticks / cfg["ticks_per_day"]))
        print("rule fired on ticks:", dict(tags))
        print("scores:", dict(scores), "| rejected:", {k: v for k, v in reasons.items() if k})
        print("rule-tagged accuracy (rolling 50):", pet.accuracy(), "% over", len(pet.series), "scored")
        print("share of ticks in distress:", {n: "%.0f%%" % (100 * distress[n] / args.ticks) for n in NEEDS})
        print("beliefs:")
        for b in pet.mem.active():
            print("  %s [t%d] %s" % (b["id"], b["created"], b["statement"]))
        print("last packet:\n" + perceive(pet.world, cfg, pet.mem))


if __name__ == "__main__":
    main()
