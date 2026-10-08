"""The loop (SPEC-v2 §3). The engine ticks every couple of seconds and carries out the pet's current intention
one step at a time; the model is asked for a new intention only when there is a reason to think.
Sleep (v1 §9) pauses all of it.

    uv run python -m engine.tick --minutes 240    # a headless life with the scripted twin, prints a summary
"""
import argparse
import asyncio
import json
import logging
import re
import tempfile
import time
from collections import Counter, deque
from pathlib import Path

from . import actions, genome, growth, log, rules, sleep, things
from .memory import Memory
from .world import NEEDS, add_event, clock, dist, load_config, moment, near, new_world, ticks

RECENT, RECALLED, RECALL_RANGE = 6, 4, 2    # retrieval (v1 §8): the latest events, plus older ones about things close by
NOVELTY_MAX, NOVELTY_SECONDS = 4.0, 150     # curiosity for doing something; real seconds per point regained
FRESH_SECONDS = 600                         # a made thing gives its full curiosity only if left alone this long (§4)
WEAR, WEAR_FLOOR = 0.8, 0.1                 # each repeat of the same thing is worth this much of the last, down to a floor.
# Without wear the ten starting objects kept curiosity at 100 for good, and the V2.3 life made two things in 2.4 hours:
# it had no reason to invent. With it, the lasting source of novelty is making something new (§4).
URGENT = {"visitor", "woke", "hatched", "low"}   # news that does not wait for min_think_seconds
DELTA = re.compile(r"(energy|comfort|curiosity) ([+-][\d.]+)")


def changes(deltas):
    return ", ".join("%s %+.1f" % nd for nd in deltas.items() if abs(nd[1]) >= 0.05)


def compress(events):
    """Runs of the same event become one entry: "[t440-449] you observed x10; curiosity -3.0"."""
    groups = []
    for t, text in events:
        head, sums = text.split(";")[0], {n: float(d) for n, d in DELTA.findall(text)}
        if groups and groups[-1]["head"] == head:
            g = groups[-1]
            g["t1"], g["n"] = t, g["n"] + 1
            for n, d in sums.items():
                g["sums"][n] = g["sums"].get(n, 0.0) + d
        else:
            groups.append({"t0": t, "t1": t, "head": head, "n": 1, "sums": sums})
    return ["%s %s%s%s" % ("[t%d]" % g["t0"] if g["n"] == 1 else "[t%d-%d]" % (g["t0"], g["t1"]), g["head"],
                           " x%d" % g["n"] if g["n"] > 1 else "", "; " + changes(g["sums"]) if changes(g["sums"]) else "")
            for g in groups]


def perceive(w, cfg, mem):
    """The perception packet: compact plain text, identical in structure for every brain. No line says what
    the pet is, and visitor presence is never stated (v1 §14); only what the visitor did."""
    pet, objs, tick, plan = w["pet"], w["objects"], w["tick"], w["plan"]
    nearest = min(objs, key=lambda o: dist(pet["pos"], objs[o]["pos"]))
    trend = pet["trend"]
    needs = ", ".join("%s %d%s" % (n, round(pet["needs"][n]),
                                   " (falling)" if trend.get(n, 0) <= -1 else " (rising)" if trend.get(n, 0) >= 1 else "")
                      for n in NEEDS)
    visible = " · ".join("%s%s (%d,%d)" % (n, " (%s)" % o["state"] if "state" in o else "", *o["pos"])
                         for n, o in objs.items())
    since = "".join("\n  " + e for t, e in w["events"] if t > w["seen"]) or " nothing"
    older = compress([e for e in w["events"] if e[0] <= w["seen"]])
    close = [n for n, o in objs.items() if dist(pet["pos"], o["pos"]) <= RECALL_RANGE]
    recalled = [g for g in older[:-RECENT] if any(n in g for n in close)][-RECALLED:]
    doing = "%s, step %d of %d" % (plan["intention"], plan["i"] + 1, len(plan["steps"])) if plan else "nothing"
    beliefs = "".join("\n  %s: %s" % (b["id"], b["statement"]) for b in mem.top()) or " none yet"
    mine = "".join("\n  %s (%d,%d): %s" % (n, *objs[n]["pos"], objs[n]["made"]["recipe"]["purpose"]) for n in things.own(w))
    room = "room: %s walls, %s floor\n" % (w["room"]["wall"], w["room"]["floor"]) if w["room"]["wall"] else ""
    most, materials = things.allowed(pet["stage"])
    return (
        "time: %s (tick %d)\n" % (clock(cfg, tick)["phase"], tick)
        + "you are at: (%d,%d)%s\n" % (*pet["pos"], ", near " + nearest if near(w, nearest) else "")
        + "needs (100 is fully met): %s\n" % needs
        + ("you feel: %s\n" % things.senses(w, cfg, [r.id for r in rules.fired(w, cfg, standing=True)]) if cfg["senses"]["enabled"] else "")
        + "visible: %s\n" % visible
        + room
        + "you are doing: %s\n" % doing
        + "since you last thought:%s\n" % since
        + "recent: %s\n" % ("  ".join(recalled + older[-RECENT:]) or "nothing yet")
        + "visitor: %s\n" % ("; ".join(w["inbox"]) or "nothing new")
        + "your things:%s\n" % (mine or " none yet")
        + "making: up to %d parts; materials: %s; you have made %d of the %d the room holds\n" % (
            most, ", ".join(materials), len(things.own(w)), cfg["make"]["item_cap"])
        + "your beliefs:%s\n" % beliefs
        + "stage: %s. allowed actions: %s\n" % (pet["stage"], ", ".join(actions.STAGE_ACTIONS[pet["stage"]]))
    )


UP = re.compile(r"\b(up|ris|rais|increas|higher|more|restor|improv|recover|boost|gain|replenish|better)|\+")
DOWN = re.compile(r"\b(down|drop|fall|lower|decreas|less|drain|los|reduc|declin|worse)|(?<![a-z0-9])[-−]")
SAME = re.compile(r"\b(stay|same|unchanged|stabl|stabil|steady|no change)")
STATE_WORDS = {
    "lamp": ("lamp|light", {"on": r"\bon\b", "off": r"\boff\b"}),
    "bowl": ("bowl", {"full": r"full|filled", "half": r"half", "empty": r"empty"}),
    "music box": ("music", {"playing": r"play|start", "silent": r"silen|stop|quiet"}),
    "window": ("window", {"open": r"open", "closed": r"clos|shut"}),
}


def direction(s):
    """+1, -1 or 0 for whichever direction word comes first ("rises or holds steady" is a rise); None if none."""
    found = [(m.start(), d) for d, m in ((1, UP.search(s)), (-1, DOWN.search(s)), (0, SAME.search(s))) if m]
    return min(found)[1] if found else None


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


def begin_tick(w, cfg):
    """Move the world's clock to the current tick. Runs whether the pet is awake or asleep."""
    w["clock"] = clock(cfg, w["tick"])
    if w["tick"] % cfg["ticks_per_day"] == round(22 * cfg["ticks_per_hour"]):   # 06:00, so an unvisited pet still eats
        w["objects"]["bowl"]["state"] = "full"
        add_event(w, "morning came; the bowl is full")


def describe(w):
    """The room in a few words, as it was when an outcome was decided. The day's journal is condensed from these."""
    pet, objs = w["pet"], w["objects"]
    nearest = min(objs, key=lambda o: dist(pet["pos"], objs[o]["pos"]))
    return ", ".join("%s %s" % (n, o["state"]) for n, o in objs.items() if "state" in o) + \
        "; at (%d,%d)%s" % (*pet["pos"], " near " + nearest if near(w, nearest) else "")


class Pet:
    """One pet's life: its own copy of the world, a brain, memory, and running metrics."""

    def __init__(self, pet_id, cfg, brain, data_dir, db=None):
        self.id, self.cfg, self.brain, self.db = pet_id, cfg, brain, db
        self.dir = Path(data_dir) / pet_id
        self.mem = Memory(self.dir, db, pet_id)
        self.state_path = self.dir / "state.json"
        saved = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.world = saved.get("world") or new_world(cfg)
        self.world["thinking"] = None                                    # a thought in flight does not survive a restart
        self.brain.s = saved.get("brain") or self.brain.s
        self.journal = deque(saved.get("journal", []), maxlen=40)        # what the Lab tab shows: steps and intentions
        self.window = deque(saved.get("window", []), maxlen=cfg["lab"]["window"])   # latest hidden-rule scores
        self.series = saved.get("series", [])                            # [tick, rolling accuracy]
        self.today = saved.get("today", [])                              # [tick, journal line, salience] since waking
        self.thought = self.night = None                                 # the model call / night's work in flight
        self.present = self.dirty = False
        self.remember_self()

    # ---- records ----

    def accuracy(self):
        return round(100 * sum(self.window) / len(self.window)) if self.window else None

    def remember_self(self):
        me = self.world["pet"]
        self.mem.update_self(stage=me["stage"], name=me["name"], genome=me["genome"],
                             description=genome.describe(me["genome"]))

    def log_body(self, cause, reason=""):
        self.remember_self()
        if self.db:
            w = self.world
            self.db.execute("INSERT INTO genomes VALUES (?,?,?,?,?,?)",
                            (self.id, w["tick"], w["clock"]["day"], json.dumps(w["pet"]["genome"]), cause, reason))
            self.db.commit()

    def note(self, rec):
        self.journal.append(rec)
        self.mem.journal(rec)
        self.dirty = True

    def save(self):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"world": self.world, "brain": self.brain.s, "journal": list(self.journal),
                                   "window": list(self.window), "series": self.series, "today": self.today}))
        tmp.replace(self.state_path)
        self.dirty = False

    # ---- growth ----

    def grow(self, morning=False):
        w, stage = self.world, growth.earned(self.world, self.cfg, self.mem, morning)
        if not stage:
            return
        old, w["pet"]["stage"] = w["pet"]["stage"], stage
        (most, mats), (had, old_mats) = things.allowed(stage), things.allowed(old)
        new = [a for a in actions.STAGE_ACTIONS[stage] if a not in actions.STAGE_ACTIONS[old]] + \
            (["things of up to %d parts" % most] if most > had else []) + ["the %s material" % m for m in mats if m not in old_mats]
        add_event(w, ("you hatched; you can do things now: " if old == "egg" else "you feel bigger; you can do new things: ") + ", ".join(new))
        moment(w, "it hatched" if old == "egg" else "it is now a " + stage.capitalize())
        w["news"].append("hatched")
        self.note({"pet": self.id, "tick": w["tick"], "type": "stage", "from": old, "to": stage})
        self.remember_self()
        if self.db:
            self.db.execute("INSERT INTO stage_events VALUES (?,?,?,?,?,?,?)",
                            (self.id, w["tick"], w["clock"]["day"], old, stage, self.accuracy(), json.dumps(w["exploits"])))
            self.db.commit()

    # ---- the mind: when to think, and what comes back ----

    def wants_thought(self):
        """Why the model should be asked now, or None (SPEC-v2 §3)."""
        w, c = self.world, self.cfg["clock"]
        quiet = (w["tick"] - w["last_call"]) * c["tick_seconds"]
        if URGENT & set(w["news"]) and quiet >= c["urgent_seconds"]:
            return "something happened"
        if quiet < (0 if getattr(self.brain, "instant", False) else c["min_think_seconds"]):
            return None
        if not w["plan"]:
            return "nothing to do"
        if w["news"]:
            return "something changed"
        return "a long quiet" if quiet >= c["max_idle_seconds"] else None

    def think(self, why):
        w = self.world
        packet = perceive(w, self.cfg, self.mem)
        self.today += [[w["tick"], "[t%d] %s | visitor %s" % (w["tick"], w["clock"]["phase"], v), 99] for v in w["inbox"]]
        w["inbox"], w["news"], w["seen"], w["last_call"], w["thinking"] = [], [], w["tick"], w["tick"], why
        self.asked = time.monotonic()
        self.thought = asyncio.create_task(self.brain.act(packet))

    def adopt(self):
        """Take the model's reply as the new intention. Until it arrives the pet stands idle."""
        w = self.world
        try:
            turn = self.thought.result()
        except Exception:
            logging.exception("thought failed for %s", self.id)
            turn = "model unreachable"
        why, w["thinking"], self.thought = w["thinking"], None, None
        failed = turn if isinstance(turn, str) else actions.check_plan(turn)
        hour = ticks(self.cfg, 3600)
        w["calls"] = [t for t in w["calls"] if t > w["tick"] - hour] + [w["tick"]]
        if self.db:
            self.db.execute("INSERT INTO calls VALUES (?,?,?,?,?)",
                            (self.id, w["tick"], why, round(time.monotonic() - self.asked, 2), failed))
            self.db.commit()
        if failed:   # whatever it was doing carries on; it is asked again after min_think_seconds
            self.note({"pet": self.id, "tick": w["tick"], "type": "no_intention", "reason": failed, "why": why})
            return
        if w["plan"]:
            self.end_plan("interrupted")
        w["plan"] = {
            "thought": actions.clean(str(turn.get("thought", "")), 300), "intention": actions.clean(turn["intention"], 120),
            "steps": turn["steps"], "expect": actions.clean(turn["expect"], 200), "why": why,
            "i": 0, "left": None,                       # the step it is on; ticks left doing it (None while walking there)
            "started": w["tick"], "needs0": dict(w["pet"]["needs"]), "tags": [],
            "step_needs0": None, "step_tags": [],
        }
        self.dirty = True

    def end_plan(self, ended):
        """The intention is over: score what it expected against what happened across the whole of it."""
        w = self.world
        plan, needs = w["plan"], w["pet"]["needs"]
        deltas = {n: round(needs[n] - plan["needs0"][n], 1) for n in NEEDS}
        result, need = score(plan["expect"], deltas, w)
        # Only predictions about a need a hidden rule moved count as hidden-rule predictions, and only when
        # the need had room to move: at 0 or 100 a correct prediction would look wrong.
        hidden = {r.id: r.need for r in rules.RULES} | things.TAG_NEED
        moved = {hidden[t] for t in plan["tags"]} - {n for n in NEEDS if not 0.0 < needs[n] < 100.0}
        rec = {
            "type": "intention", "pet": self.id, "tick": w["tick"], "started": plan["started"],
            "day": w["clock"]["day"], "phase": w["clock"]["phase"], "why": plan["why"], "thought": plan["thought"],
            "intention": plan["intention"], "steps": plan["steps"], "expect": plan["expect"], "ended": ended,
            "deltas": deltas, "score": result, "rule_tags": plan["tags"],
            "rule_scored": result != "unscorable" and need in moved, "visitor_present": self.present,
        }
        if rec["rule_scored"]:
            self.window.append(result == "correct")
            self.series.append([w["tick"], self.accuracy()])
            del self.series[:-600]
        w["plan"], w["last_plan"] = None, {"intention": plan["intention"], "ended": ended, "score": result}
        self.note(rec)
        if self.db:
            log.record_intention(self.db, rec)

    # ---- the body: carrying a step out ----

    def advance(self):
        """One tick of the current step: walk one tile toward where it happens, or spend a tick doing it."""
        w = self.world
        plan, pet = w["plan"], w["pet"]
        a = plan["steps"][plan["i"]]
        if plan["left"] is None:
            if plan["step_needs0"] is None:   # the step begins
                plan["step_needs0"], plan["step_tags"], plan["step_began"] = dict(pet["needs"]), [], w["tick"]
                if actions.check(a, w, self.mem, self.cfg):
                    return self.finish_step(a)
            goal = actions.destination(w, a)
            if goal and pet["pos"] != goal:   # one tile a tick, so it is seen walking
                pet["pos"] = [p + (g > p) - (g < p) for p, g in zip(pet["pos"], goal)]
                return
            plan["left"] = ticks(self.cfg, self.cfg["steps"][a["type"]])
        plan["left"] -= 1
        if plan["left"] <= 0:
            self.finish_step(a)

    def finish_step(self, a):
        """The step happens now (or turns out not to be possible), and is written down."""
        w = self.world
        plan, pet = w["plan"], w["pet"]
        reason = actions.check(a, w, self.mem, self.cfg)   # checked again: the room may have changed while it walked
        text, used, fired, quality = "nothing happened", None, [], []
        arrived = dict(pet["needs"])   # before the step itself does anything
        thing = actions.norm(a.get("target")) if a["type"] == "use" else None
        thing = thing if thing and "made" in w["objects"].get(thing, {}) else None
        for_need = lambda n: things.material(w, self.cfg, n).get("need")   # the need a thing's material is for
        thing_need = for_need(thing) if thing else None
        if not reason:
            was = {"needs": dict(pet["needs"]), "bowl": w["objects"]["bowl"]["state"],
                   "plant_by_window": growth.plant_by_window(w)}
            text, fx, key = actions.apply(w, a, self.mem, self.cfg)
            if a["type"] == "rest":   # the action table says what 10 s of rest gives; what is next to it can change that
                per_10s, quality, share = things.rest(w, self.cfg, fx["energy"])
                fx = {"energy": per_10s * self.cfg["steps"]["rest"] / 10}
                for n, v in share.items():   # what resting beside it added or took away counts as an occasion of use
                    self.mem.thing_used(n, {"energy": round(v * self.cfg["steps"]["rest"] / 10, 1)}, for_need(n))
            if key:
                idle = (w["tick"] - w["seen_at"].get(key, -10**6)) * self.cfg["clock"]["tick_seconds"]
                wear = max(WEAR_FLOOR, WEAR ** w["times"].get(key, 0))
                fresh = min(1.0, idle / FRESH_SECONDS) if thing else 1.0   # a made thing also needs leaving alone a while
                fx["curiosity"] = (fx.get("curiosity", 0) * fresh + min(NOVELTY_MAX, idle / NOVELTY_SECONDS)) * wear
                w["seen_at"][key], w["times"][key] = w["tick"], w["times"].get(key, 0) + 1
            fired = rules.fired(w, self.cfg, standing=False)
            for r in fired:   # the rule decides what the action gives, in place of the usual
                fx[r.need] = r.value(self.cfg)
            for n in NEEDS:
                pet["needs"][n] = min(100.0, max(0.0, pet["needs"][n] + fx.get(n, 0)))
            used = growth.exploit(w, self.cfg, a, was)
            if used:
                w["exploits"][used] += 1
            name = re.search(r"\bmy name is ([A-Za-z][\w' -]{0,29})", a.get("text", "") if a["type"] == "speak" else "", re.I)
            if name:
                pet["name"] = name.group(1).strip()
                self.mem.update_self(name=pet["name"], named_at=w["tick"])
                moment(w, "it named itself " + pet["name"])
        else:
            text = "you could not %s (%s)" % (actions.words(a), reason)
        tags = list(dict.fromkeys(plan["step_tags"] + [r.id for r in fired] + quality))
        plan["tags"] += [t for t in tags if t not in plan["tags"]]
        # What the step did is told apart from what was happening anyway while it took place, so a long step
        # under a lit lamp does not read as "resting costs comfort".
        deltas = {n: round(pet["needs"][n] - plan["step_needs0"][n], 1) for n in NEEDS}
        own = {n: round(pet["needs"][n] - arrived[n], 1) for n in NEEDS}
        if thing and not reason:
            self.mem.thing_used(thing, own, thing_need)   # engine truth, for the Things tab and for growth (§6)
        for n, (need, total) in plan.pop("near", {}).items():   # things that worked on it just by being near
            if abs(total) >= 0.2 and n in w["objects"]:
                self.mem.thing_used(n, {need: round(total, 1)}, for_need(n))
        meanwhile = {n: d for n in NEEDS if abs(d := round(arrived[n] - plan["step_needs0"][n], 1)) >= 0.5}
        took = (w["tick"] - plan["step_began"] + 1) * self.cfg["clock"]["tick_seconds"]
        told = text + ("; " + changes(own) if changes(own) else "") + (
            "; in the %d s that took, apart from it: %s" % (took, changes(meanwhile)) if meanwhile else "")
        add_event(w, told)
        rec = {
            "type": "step", "pet": self.id, "tick": w["tick"], "day": w["clock"]["day"], "phase": w["clock"]["phase"],
            "stage": pet["stage"], "pos": list(pet["pos"]), "context": describe(w), "intention": plan["intention"],
            "step": plan["i"] + 1, "of": len(plan["steps"]), "action": a, "reason": reason, "feedback": text,
            "deltas": deltas, "own": own, "meanwhile": meanwhile,
            "needs": {n: round(v, 1) for n, v in pet["needs"].items()},
            "rule_tags": tags, "exploit": used, "visitor_present": self.present,
        }
        self.today.append([w["tick"], "[t%d] %s | %s | %s" % (w["tick"], rec["phase"], rec["context"], told),
                           max(abs(d) for d in deltas.values())])
        del self.today[:-800]
        self.note(rec)
        if self.db:
            log.record(self.db, rec)
        plan["i"], plan["left"], plan["step_needs0"] = plan["i"] + 1, None, None
        if reason:
            self.end_plan("not possible: " + reason)
        elif plan["i"] == len(plan["steps"]):
            self.end_plan("done")

    # ---- one tick ----

    def live(self):
        """What a waking tick does to the needs: drift and the standing hidden rules, at their per-10 s rates."""
        w, dt = self.world, self.cfg["dt"]
        needs, base, fired = w["pet"]["needs"], drift(w), rules.fired(w, self.cfg, standing=True)
        near_things = things.nearby(w, self.cfg)
        felt = [(r.id, r.need, r.value(self.cfg)) for r in fired] + [t[:3] for t in near_things]   # rules, then materials
        if w["clock"]["phase"] == "night" and things.light_on(w, self.cfg):   # a dark thing's work is the harm it prevents
            near_things += [("dark", "comfort", -self.cfg["materials"]["rules"]["lights_night"], n) for n in things.close(w, self.cfg, "shade")]
        if w["plan"] and w["plan"]["step_needs0"] is not None:
            for _, need, per_10s, n in near_things:
                got = w["plan"].setdefault("near", {}).setdefault(n, [need, 0.0])
                got[1] += per_10s * dt
        rate = {n: base[n] + sum(v for _, need, v in felt if need == n) for n in NEEDS}
        for n in NEEDS:
            needs[n] = min(100.0, max(0.0, needs[n] + rate[n] * dt))
        w["pet"]["trend"] = rate
        if w["plan"]:
            seen = w["plan"]["step_tags" if w["plan"]["step_needs0"] is not None else "tags"]
            seen += [tag for tag in dict.fromkeys(t for t, _, _ in felt) if tag not in seen]

    def notice(self, before):
        """Things that are reasons to think again (SPEC-v2 §3): a need crossing 30 or 80, a change of phase."""
        w = self.world
        for n in NEEDS:
            now = w["pet"]["needs"][n]
            if before[n] >= 30 > now or before[n] < 80 <= now:
                add_event(w, "%s %s" % (n, "fell below 30" if now < 30 else "rose above 80"))
                w["news"].append("low" if now < 30 else "need")   # running low cannot wait; feeling full can
        if w["clock"]["phase"] != w["phase_seen"]:
            w["phase_seen"] = w["clock"]["phase"]
            add_event(w, "it became " + w["phase_seen"])
            w["news"].append("phase")
        mark = genome.update_marks(w, self.cfg)
        if mark:
            moment(w, "it now has " + mark)
            self.note({"pet": self.id, "tick": w["tick"], "type": "mark", "mark": mark})
            self.log_body("mark: " + mark)

    async def tick(self, visitor_present=False):
        await asyncio.sleep(0)   # let a finished thought or night's work land
        w, self.present = self.world, visitor_present
        begin_tick(w, self.cfg)
        things.behave(w, self.cfg, self.cfg["clock"]["tick_seconds"])   # taught things act every tick, awake or asleep (§7)
        if w["pet"]["stage"] == "egg":
            self.grow()          # an egg is dormant: no model call, and nothing in the room reaches its needs
        elif w["sleep"] or (not self.thought and sleep.should_sleep(w, self.cfg)):
            self.sleep_tick()
        else:
            before = dict(w["pet"]["needs"])
            self.live()
            if self.thought:
                if self.thought.done():
                    self.adopt()
            elif w["plan"]:
                self.advance()
            self.notice(before)
            why = None if self.thought else self.wants_thought()
            if why:
                self.think(why)
        w["tick"] += 1
        if self.dirty or w["tick"] % 5 == 0:   # every tick would be a lot of disk for a two-second clock
            self.save()

    def sleep_tick(self):
        """Asleep: the clock moves and energy returns, but the pet does nothing (v1 §9)."""
        w = self.world
        if not w["sleep"]:
            if w["plan"]:
                self.end_plan("interrupted")
            w["sleep"] = {"since": w["tick"], "day": w["clock"]["day"], "done": False}
            self.dirty = True
        if not w["sleep"]["done"] and self.night is None:
            self.night = asyncio.create_task(sleep.night(self))
        needs = w["pet"]["needs"]
        needs["energy"] = min(100.0, needs["energy"] + self.cfg["sleep"]["restore_per_10s"] * self.cfg["dt"])
        if w["sleep"]["done"] and w["clock"]["phase"] != "night":
            dream = w["last_night"]["dream"]
            w["events"] = []   # the reset: only journal, beliefs and self carry into the new day
            add_event(w, "you woke up" + ('. you remember thinking: "%s"' % dream if dream else ""))
            w["news"].append("woke")
            w["sleep"], w["phase_seen"], self.night, self.today, self.dirty = None, w["clock"]["phase"], None, [], True
            self.grow(morning=True)   # stages are earned, and checked each morning (§6)


async def main():
    from .brains.twin import Twin
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=240, help="real minutes of life to run through")
    args = ap.parse_args()
    cfg = load_config()
    with tempfile.TemporaryDirectory() as d:
        pet = Pet("twin", cfg, Twin(cfg), d, log.open_db(Path(d) / "pet.db"))
        n, distress, asleep = ticks(cfg, args.minutes * 60), Counter(), 0
        for i in range(n):
            # A scripted visitor so every rule gets exercised: two feeds close together, plant to the window.
            if i % ticks(cfg, 2400) in (0, ticks(cfg, 60)):
                actions.visit(pet.world, {"type": "feed"})
            if i == ticks(cfg, 1500):
                actions.visit(pet.world, {"type": "place", "object": "plant", "tile": [1, 4]})
            await pet.tick()
            asleep += bool(pet.world["sleep"])
            distress.update(k for k, v in pet.world["pet"]["needs"].items() if v < 20)
        db = pet.db
        print("%d minutes = %.1f world days, %d%% asleep, stage %s" % (
            args.minutes, n / cfg["ticks_per_day"], 100 * asleep / n, pet.world["pet"]["stage"]))
        print("steps:", dict(db.execute("SELECT json_extract(action, '$.type'), count(*) FROM decisions GROUP BY 1").fetchall()),
              "| not possible:", db.execute("SELECT count(*) FROM decisions WHERE reason IS NOT NULL").fetchone()[0])
        print("intentions:", dict(db.execute("SELECT score, count(*) FROM intentions GROUP BY 1").fetchall()),
              "| ended:", dict(db.execute("SELECT substr(ended, 1, 12), count(*) FROM intentions GROUP BY 1").fetchall()))
        print("hidden rules met:", dict(Counter(t for (tags,) in db.execute("SELECT rule_tags FROM intentions") for t in tags.split(",") if t)))
        print("hidden-rule accuracy (rolling %d):" % cfg["lab"]["window"], pet.accuracy(), "% over", len(pet.series), "scored")
        print("share of ticks in distress:", {k: "%.0f%%" % (100 * distress[k] / n) for k in NEEDS})
        print("beliefs:", [b["statement"] for b in pet.mem.active()][:6])
        print("last packet:\n" + perceive(pet.world, cfg, pet.mem))


if __name__ == "__main__":
    asyncio.run(main())
