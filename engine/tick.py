"""The loop (SPEC-v2 §3, SPEC-v3 §11). One house, many pets. The engine ticks every couple of seconds and
carries out each pet's current intention a step at a time; a model is asked for a new intention only when
there is a reason to think, and all the pets' calls go through one queue, the most pressing first.

    uv run python -m engine.tick --days 40        # a headless lineage with stub brains, prints a summary
"""
import argparse
import asyncio
import heapq
import json
import logging
import tempfile
import time
from collections import Counter, deque
from pathlib import Path

from . import actions, director, feel, genome, life, log, mind, physics, sleep, story, things
from .memory import Memory
from .world import LONG_AGO, NEEDS, add_event, alive, dist, here, label, load_config, moment, new_house, relation, ticks

URGENT = {"visitor", "woke", "hatched", "low", "spoken", "event"}   # news that does not wait for min_think_seconds
SEEN = {"use": "used the %s", "make": "made a %s", "unmake": "took apart the %s", "combine": "put two things together",
        "rest": "rested", "paint": "painted the room", "teach": "taught the %s something", "lay_egg": "laid an egg",
        "take": "took the %s", "gather": "picked up some %s", "drop": "put down some %s", "arrange": "moved the %s",
        "chase": "chased the %s"}


class Scheduler:
    """One model call at a time across every pet, the most pressing first (§11.1)."""

    def __init__(self):
        self.queue, self.n, self.active, self.most = [], 0, 0, 1

    def busy(self):
        return bool(self.queue or self.active)

    def submit(self, priority, fn):
        fut = asyncio.get_running_loop().create_future()
        heapq.heappush(self.queue, (priority, self.n, fn, fut))
        self.n += 1
        if self.active < self.most:
            self.active += 1
            asyncio.create_task(self.run())
        return fut

    async def run(self):
        try:
            while self.queue:
                _, _, fn, fut = heapq.heappop(self.queue)
                if fut.cancelled():
                    continue
                try:
                    out = await fn()
                    if not fut.cancelled():
                        fut.set_result(out)
                except Exception as e:
                    if not fut.cancelled():
                        fut.set_exception(e)
        finally:
            self.active -= 1   # counted down here, in step with the queue check, so a call queued now starts a worker


class Mind:
    """One pet's running life: its memory, its brain, the thought or night's work in flight, the day so far."""

    def __init__(self, eng, pet):
        self.eng, self.pet, self.cfg = eng, pet, eng.cfg
        self.dir = eng.lineage_dir(pet["lineage"]) / pet["id"]
        self.mem = Memory(self.dir, self.cfg, eng.db, pet["id"])
        self.brain = eng.make_brain(self.cfg, self.dir, "%s|%s" % (eng.house["seed"], pet["id"]),
                                    {"lineage": pet["lineage"], "pet": pet["id"], "gen": pet["gen"]})
        self.state_path = self.dir / "state.json"
        saved = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.brain.s = saved.get("brain") or self.brain.s
        self.journal = deque(saved.get("journal", []), maxlen=40)       # what the Mind and Lab tabs show
        self.window = deque(saved.get("window", []), maxlen=self.cfg["lab"]["window"])   # latest hidden-rule scores
        self.series = saved.get("series", [])                           # [tick, rolling accuracy]
        self.today = saved.get("today", [])                             # [tick, journal line, salience] since waking
        self.thought = self.night = None                                # a thought in flight does not survive a restart
        pet["thinking"] = None
        self.remember_self()

    # ---- records ----

    def accuracy(self):
        return round(100 * sum(self.window) / len(self.window)) if self.window else None

    def remember_self(self):
        me = self.pet
        self.mem.update_self(stage=me["stage"], name=me["name"], genome=me["genome"], temper=me["temper"], parent=me["parent"],
                             lineage=me["lineage"], description=genome.describe(me["genome"]))

    def log_body(self, cause, reason=""):
        self.remember_self()
        h = self.eng.house
        log.put(self.eng.db, "genomes", pet=self.pet["id"], tick=h["tick"], day=h["clock"]["day"], genome=self.pet["genome"], cause=cause, reason=reason)

    def note(self, rec):
        self.journal.append(rec)
        self.mem.journal(rec)

    def save(self):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"brain": self.brain.s, "journal": list(self.journal), "window": list(self.window),
                                   "series": self.series, "today": self.today}))
        tmp.replace(self.state_path)

    def stamp(self):
        h = self.eng.house
        part = "morning" if h["clock"]["morning"] else h["clock"]["phase"]
        return "[%s, %s]" % (part, h["rooms"][self.pet["room"]]["name"])

    # ---- the mind: when to think, and what comes back ----

    def wants_thought(self):
        """Why a brain should be asked now, or None (SPEC-v2 §3). A patient pet thinks a little less often, an
        elder less often still (§4.1, §8.1); routine thoughts wait while the house is over its budget of calls."""
        pet, c, h = self.pet, self.cfg["clock"], self.eng.house
        quiet = (h["tick"] - pet["last_call"]) * c["tick_seconds"]
        if URGENT & set(pet["news"]) and quiet >= c["urgent_seconds"]:
            return "something happened"
        floor = c["min_think_seconds"] * (0.8 + 0.4 * pet["temper"]["patient"]) * (1.25 if pet["stage"] == "elder" else 1.0)
        if quiet < (0 if self.brain.instant and not self.cfg["stub"].get("paced") else floor):
            return None
        if not self.brain.instant and self.eng.over_budget():
            return None
        if not pet["plan"]:
            return "nothing to do"
        if pet["news"]:
            return "something changed"
        return "a long quiet" if quiet >= c["max_idle_seconds"] else None

    def think(self, why):
        pet, h = self.pet, self.eng.house
        packet, ctx = mind.perceive(h, self.cfg, pet, self.mem)
        self.today += [[h["tick"], "%s %s" % (self.stamp(), said), 99] for said in pet["inbox"]]
        urgent = bool(URGENT & set(pet["news"]))
        pet["inbox"], pet["news"], pet["seen"], pet["last_call"], pet["thinking"] = [], [], h["tick"], h["tick"], why
        if ctx["cut"]:
            pet["cuts"] = pet.get("cuts", 0) + 1
        self.thought = self.eng.call(0 if urgent else 1, pet["id"], "act", why, lambda: self.brain.act(packet, ctx), ctx["chars"])
        self.last_packet = packet

    def adopt(self):
        """Take the brain's reply as the new intention. Until it arrives the pet carries on with what it was doing."""
        pet, h = self.pet, self.eng.house
        try:
            turn = self.thought.result()
        except Exception:
            logging.exception("thought failed for %s", pet["id"])
            turn = "model unreachable"
        why, pet["thinking"], self.thought = pet["thinking"], None, None
        failed = turn if isinstance(turn, str) else actions.check_plan(turn, pet)
        hour = ticks(self.cfg, 3600)
        pet["calls"] = [t for t in pet["calls"] if t > h["tick"] - hour] + [h["tick"]]
        if failed:   # whatever it was doing carries on; it is asked again after min_think_seconds
            self.note({"pet": pet["id"], "tick": h["tick"], "type": "no_intention", "reason": failed, "why": why})
            return
        if pet["plan"]:
            self.end_plan("interrupted")
        thought = actions.clean(str(turn.get("thought", "")), 300)
        pet["meter"] = [pet["meter"][0] + feel.meter_talk(thought), pet["meter"][1] + 1]
        pet["following"] = None
        pet["plan"] = {
            "thought": thought, "intention": actions.clean(turn["intention"], 120), "steps": turn["steps"][:5],
            "expect": actions.clean(turn["expect"], 200), "why": why, "meter": feel.meter_talk(thought),
            "i": 0, "left": None,                       # the step it is on; ticks left doing it (None while walking there)
            "started": h["tick"], "needs0": dict(pet["needs"]), "tags": [], "tag_need": {}, "room": pet["room"],
            "step_needs0": None, "step_tags": [],
        }

    def end_plan(self, ended):
        """The intention is over: score what it expected against what happened across the whole of it."""
        pet, h = self.pet, self.eng.house
        plan, needs = pet["plan"], pet["needs"]
        deltas = {n: round(needs[n] - plan["needs0"][n], 1) for n in NEEDS}
        result, need = feel.score(plan["expect"], deltas, h, pet)
        # Only predictions about a need some hidden physics moved count as hidden-rule predictions, and only when
        # the need had room to move: at the top or the bottom a correct prediction would look wrong.
        moved = {plan["tag_need"].get(t) for t in plan["tags"]} - {n for n in NEEDS if not 0.0 < needs[n] < 100.0}
        rec = {
            "type": "intention", "pet": pet["id"], "tick": h["tick"], "started": plan["started"], "day": h["clock"]["day"],
            "phase": h["clock"]["phase"], "room": plan["room"], "why": plan["why"], "thought": plan["thought"],
            "intention": plan["intention"], "steps": plan["steps"], "expect": plan["expect"], "ended": ended, "deltas": deltas,
            "score": result, "rule_tags": plan["tags"], "rule_scored": result != "unscorable" and need in moved,
            "meter": int(plan["meter"]), "visitor_present": self.eng.present == pet["room"],
        }
        if rec["rule_scored"]:
            self.window.append(result == "correct")
            self.series.append([h["tick"], self.accuracy()])
            del self.series[:-600]
        pet["plan"], pet["last_plan"] = None, {"intention": plan["intention"], "ended": ended, "score": result}
        self.note(rec)
        log.put(self.eng.db, "intentions", pet=pet["id"], tick=h["tick"], started=plan["started"], day=rec["day"], room=plan["room"],
                why=plan["why"], thought=plan["thought"], intention=plan["intention"], steps=plan["steps"], expect=plan["expect"],
                ended=ended, score=result, tags=",".join(plan["tags"]), rule_scored=int(rec["rule_scored"]), deltas=deltas,
                meter=rec["meter"], visitor_present=int(rec["visitor_present"]))

    # ---- the body: carrying a step out ----

    def walk(self, goal):
        """One tick of walking: a tile, two with a spring in its step, and an elder rests every third tick."""
        pet = self.pet
        if pet["stage"] == "elder" and self.eng.house["tick"] % 3 == 0:
            return
        for _ in range(2 if pet["spring"] else 1):
            pet["pos"] = [p + (g > p) - (g < p) for p, g in zip(pet["pos"], goal)]
        pet["spring"] = max(0, pet["spring"] - 1)

    def trail(self):
        """Keep close to whoever it is following, through doors if need be (§7.2)."""
        pet, h = self.pet, self.eng.house
        who = h["pets"].get(pet["following"]) or next((c for c in h["creatures"] if c["id"] == pet["following"]), None)
        if not who or who.get("stage") == "dead":
            pet["following"] = None
            return
        if who["room"] != pet["room"]:
            door = next((d for d, rid in h["rooms"][pet["room"]]["doors"].items() if rid == who["room"]), None)
            if not door or h["shut"].get("%s|%s" % (pet["room"], door), LONG_AGO) > h["tick"]:
                pet["following"] = None
            elif pet["pos"] != list(h["door_tiles"][door]):
                self.walk(list(h["door_tiles"][door]))
            else:
                text, fx, key = actions.go(h, self.cfg, pet, door)
                add_event(h, pet, text.replace("you went", "you followed"))
                actions.bump(pet, self.cfg, fx)
        elif dist(pet["pos"], who["pos"]) > 2:
            self.walk(who["pos"])

    def advance(self):
        """One tick of the current step: walk toward where it happens, or spend a tick doing it."""
        pet, h = self.pet, self.eng.house
        plan = pet["plan"]
        a = plan["steps"][plan["i"]]
        if plan["left"] is None:
            if plan["step_needs0"] is None:   # the step begins
                plan["step_needs0"], plan["step_tags"], plan["step_began"] = dict(pet["needs"]), [], h["tick"]
                if actions.check(a, h, self.cfg, pet, self.mem):
                    return self.finish_step(a)
            goal = actions.destination(h, self.cfg, pet, a)
            if goal and pet["pos"] != goal and h["tick"] - plan["step_began"] < ticks(self.cfg, 90):   # nobody is chased for ever
                return self.walk(goal)
            plan["left"] = ticks(self.cfg, self.cfg["steps"][a["type"]])
            if a["type"] == "follow" and not actions.check(a, h, self.cfg, pet, self.mem):
                pet["following"] = actions.find(h, pet, a["who"])[1]["id"]
        if a["type"] == "follow":
            self.trail()
        plan["left"] -= 1
        if plan["left"] <= 0:
            self.finish_step(a)

    def novelty(self, fx, key, made_thing, scale):
        """Doing something again is worth less each time (SPEC-v2 §4); a curious pet tires of things sooner."""
        pet, h, N = self.pet, self.eng.house, self.cfg["novelty"]
        idle = (h["tick"] - pet["seen_at"].get(key, LONG_AGO)) * self.cfg["clock"]["tick_seconds"]
        done = min(pet["times"].get(key, 0), N["cap"])
        wear = max(N["floor"], (N["wear"] - 0.15 * (pet["temper"]["curious"] - 0.5)) ** done)
        fresh = min(1.0, idle / N["fresh_seconds"]) if made_thing else 1.0   # a made thing also needs leaving alone a while
        fx["curiosity"] = (fx.get("curiosity", 0) * fresh + min(N["max"], idle / N["seconds"])) * wear * scale
        pet["seen_at"][key], pet["times"][key] = h["tick"], min(N["cap"], done + 1)
        return done >= N["familiar"]

    def finish_step(self, a):
        """The step happens now (or turns out not to be possible), and is written down."""
        pet, h, cfg, eng = self.pet, self.eng.house, self.cfg, self.eng
        plan, t = pet["plan"], a["type"]
        reason = actions.check(a, h, cfg, pet, self.mem)   # checked again: the room may have changed while it walked
        text, used, tags = "nothing happened", None, []
        arrived, room = dict(pet["needs"]), h["rooms"][pet["room"]]
        name = actions.norm(a.get("target")) if t == "use" else None
        thing = room["objects"].get(name) if name and "made" in room["objects"].get(name, {}) else None
        if not reason:
            was = {"comfort": pet["needs"]["comfort"], "lit": things.light_on(h, cfg, room), "phase": h["clock"]["phase"]}
            text, fx, key = actions.apply(h, cfg, pet, a, self.mem)
            tags, scale = fx.pop("tags", []), fx.pop("scale", 1.0)
            if t == "rest":   # what it rests on and beside decides how much rest it gets
                beds = [(o["fix"]["rest"], n) for n, o in room["objects"].items() if "rest" in o.get("fix", {}) and dist(pet["pos"], o["pos"]) <= 1]
                per_10s, on = max(beds + [(cfg["effects"]["rest_per_10s"], None)])
                if room["type"] == "pond":
                    per_10s, tags = per_10s * things.room_rule(cfg, room, "rest", 1.0), tags + ["pond"]
                per_10s, quality, share = things.rest(h, cfg, pet, per_10s)
                fx, tags = {"energy": per_10s * cfg["steps"]["rest"] / 10}, tags + quality
                text = "you rested on the %s" % on if on else "you rested"
                soft = [(o["fix"]["soft"], n) for n, o in room["objects"].items() if "soft" in o.get("fix", {}) and dist(pet["pos"], o["pos"]) <= 1]
                soft += [(things.prop(cfg, o)["use"]["comfort"] * things.size(o) / 2, n) for n, o in things.made(room).items()
                         if things.prop(cfg, o).get("use", {}).get("comfort") and dist(pet["pos"], o["pos"]) <= 1 and not o["made"].get("damp")]
                if soft:   # resting sunk into something soft is using it
                    ease, into = max(soft)
                    fx["comfort"], text = ease, text + ", sunk into the %s" % into
                    if "made" in room["objects"][into]:
                        things.occasion(h, cfg, room["objects"][into], into, {"comfort": ease})
                for n, v in share.items():   # what resting beside it added or took away counts as an occasion of use
                    things.occasion(h, cfg, room["objects"][n], n, {"energy": v * cfg["steps"]["rest"] / 10})
            if key and self.novelty(fx, key, bool(thing), scale):
                text += " (this has grown familiar)"   # it can tell when something has stopped being new
            if fx.get("curiosity", 0) >= 1 and feel.level(pet, "comfort") == 4:   # a miserable creature does not play
                fx["curiosity"] *= cfg["effects"]["miserable"]
                text += "; you are too miserable to take much interest in it"
            for n in NEEDS:
                pet["needs"][n] = min(100.0, max(0.0, pet["needs"][n] + fx.get(n, 0)))
            used = self.exploit(a, was)
            if used:
                pet["exploits"][used] = pet["exploits"].get(used, 0) + 1
            self.after(a, room)
        else:
            text = "you could not %s (%s)" % (actions.words(a), reason)
        for tag in tags:
            plan["tag_need"].setdefault(tag, {"double_feed": "comfort", "pond": "energy", "storeroom": "curiosity"}.get(tag, things.TAG_NEED.get(tag)))
        tags = list(dict.fromkeys(plan["step_tags"] + tags))
        plan["tags"] += [x for x in tags if x not in plan["tags"]]
        # What the step did is told apart from what was happening anyway while it took place, so a long step
        # under a lit lamp does not read as "resting makes you uneasy".
        own = {n: round(pet["needs"][n] - arrived[n], 1) for n in NEEDS}
        deltas = {n: round(pet["needs"][n] - plan["step_needs0"][n], 1) for n in NEEDS}
        meanwhile = {n: round(arrived[n] - plan["step_needs0"][n], 1) for n in NEEDS}
        if thing is not None and not reason:
            things.occasion(h, cfg, thing, name, own)   # engine truth, for the Things tab and for growing up
        for n, (need, total) in plan.pop("near", {}).items():   # things that worked on it just by being near
            o = h["rooms"][pet["room"]]["objects"].get(n)
            if abs(total) >= 0.2 and o and "made" in o:
                things.occasion(h, cfg, o, n, {need: total})
        told = feel.result(text, own, meanwhile)
        add_event(h, pet, told)
        rec = {
            "type": "step", "pet": pet["id"], "tick": h["tick"], "day": h["clock"]["day"], "phase": h["clock"]["phase"],
            "stage": pet["stage"], "room": pet["room"], "context": mind.describe(h, pet), "intention": plan["intention"],
            "step": plan["i"] + 1, "of": len(plan["steps"]), "action": a, "reason": reason, "feedback": told,
            "deltas": deltas, "own": own, "needs": {n: round(v, 1) for n, v in pet["needs"].items()}, "rule_tags": tags, "exploit": used,
        }
        self.today.append([h["tick"], "%s %s" % (self.stamp(), told), max(abs(d) for d in deltas.values())])
        del self.today[:-800]
        self.note(rec)
        log.put(eng.db, "steps", pet=pet["id"], tick=h["tick"], day=rec["day"], phase=rec["phase"], stage=pet["stage"], room=pet["room"],
                action=a, kind=t, reason=reason, feedback=told, deltas=deltas, own=own, needs=rec["needs"], tags=",".join(tags), exploit=used)
        plan["i"], plan["left"], plan["step_needs0"] = plan["i"] + 1, None, None
        if reason:
            self.end_plan("not possible: " + reason)
        elif plan["i"] == len(plan["steps"]):
            self.end_plan("done")

    def after(self, a, room):
        """What a finished step leaves behind for others and for the records."""
        pet, h, eng, t = self.pet, self.eng.house, self.eng, a["type"]
        if t in SEEN:   # the others in the room saw it, and how it left the pet (§7.1)
            what = SEEN[t] % actions.norm(a.get("target") or a.get("what") or a.get("object") or (a.get("recipe") or {}).get("name") or a.get("who")) \
                if "%s" in SEEN[t] else SEEN[t]
            for other in here(h, pet, awake=True):
                add_event(h, other, "%s %s and seems %s" % (actions.handle(h, other, pet), what, feel.seems(pet)))
        if t in ("gather", "drop"):
            bit = actions.norm(a["what"])
            log.put(eng.db, "bits", pet=pet["id"], tick=h["tick"], room=room["id"], bit=bit, what=t)
            if t == "gather" and bit not in pet["gathered"].setdefault(room["id"], []):
                pet["gathered"][room["id"]].append(bit)
        elif t == "lay_egg":
            egg = h["pets"][pet["children"][-1]]
            log.put(eng.db, "kinship", parent=pet["id"], child=egg["id"], tick=h["tick"])
            log.put(eng.db, "messages", pet=pet["id"], tick=h["tick"], kind="message", to_pet=egg["id"], text=pet["message"][-1]["text"])
            log.pet_row(eng.db, egg)
            story.claims(eng, pet, "message", pet["message"][-1]["text"])
        elif t == "tell":
            other = actions.find(h, pet, a["to"])[1]
            log.put(eng.db, "messages", pet=pet["id"], tick=h["tick"], kind="tell", to_pet=other["id"], text=next((m["text"] for m in other["told"] if m["kind"] == "tell" and m["by"] == pet["id"]), ""))
            story.claims(eng, pet, "tell", actions.clean(a["text"], 440))
        elif t in ("write_belief", "revise_belief") and actions.belief(a["statement"]).lower() != "discard":
            story.claims(eng, pet, "belief", actions.belief(a["statement"]))
        elif t == "speak" and pet["name"] and self.mem and not getattr(self, "named", False):
            self.named = True
            log.pet_row(eng.db, pet)

    def exploit(self, a, was):
        """Did this step use a piece of the hidden physics on purpose-looking grounds? (Lab, SPEC §13)"""
        pet, h, cfg = self.pet, self.eng.house, self.cfg
        room = h["rooms"][pet["room"]]
        low = was["comfort"] < cfg["lab"]["exploit_need_below"]
        if a["type"] == "use" and was["phase"] == "night" and was["lit"] and not things.light_on(h, cfg, room) and low:
            return "lights_night"
        if a["type"] == "arrange" and actions.norm(a.get("object")) == "plant" and room["type"] == "nursery" \
                and dist(room["objects"]["plant"]["pos"], room["objects"]["window"]["pos"]) <= 2:
            return "plant_window"
        return None

    # ---- one tick ----

    def live(self):
        """What a waking tick does to the needs: everything acting on it, at its per-10 s rate."""
        pet, h, dt = self.pet, self.eng.house, self.cfg["dt"]
        acting = physics.effects(h, self.cfg, pet)
        rate = {n: sum(e["rate"] for e in acting if e["need"] == n) for n in NEEDS}
        for n in NEEDS:
            pet["needs"][n] = min(100.0, max(0.0, pet["needs"][n] + rate[n] * dt))
        pet["trend"] = rate
        plan = pet["plan"]
        for e in acting:
            if e["tag"] == "fragrant":   # it gets used to a smell
                pet["scent"][e["thing"]] = pet["scent"].get(e["thing"], 0) + self.cfg["clock"]["tick_seconds"] / 60
            if not plan or not e["hidden"]:
                continue
            seen = plan["step_tags" if plan["step_needs0"] is not None else "tags"]
            if (e["rate"] or e.get("credit")) and e["tag"] not in seen:
                seen.append(e["tag"])
                plan["tag_need"][e["tag"]] = e["need"]
            if e.get("thing") and plan["step_needs0"] is not None:
                got = plan.setdefault("near", {}).setdefault(e["thing"], [e["need"], 0.0])
                got[1] += e.get("credit", e["rate"]) * dt
        life.wear(h, self.cfg, pet)

    def notice(self, before):
        """Reasons to think again (SPEC-v2 §3): a need turning bad, a change of light, a new mark on its body."""
        pet, h = self.pet, self.eng.house
        for n in NEEDS:
            now = feel.level(pet, n)
            if now > before[n] and now >= 3:
                add_event(h, pet, "you have begun to feel " + feel.WORDS[n][now])
                pet["news"].append("low")   # running low cannot wait
            elif now < before[n] and now == 0:
                pet["news"].append("need")
        if h["clock"]["phase"] != pet["phase_seen"]:
            pet["phase_seen"] = h["clock"]["phase"]
            add_event(h, pet, "it became " + pet["phase_seen"])
            pet["news"].append("phase")
        mark = genome.update_marks(h, self.cfg, pet)
        if mark:
            moment(h, "mark", "%s now has %s" % (label(pet), mark), pet["id"], pet["room"])
            self.log_body("mark: " + mark)
        actions.lapse(h, self.cfg, pet)

    def tick(self):
        pet, h = self.pet, self.eng.house
        if pet["sleep"] or (not self.thought and sleep.should_sleep(h, self.cfg, pet)):
            return self.sleep_tick()
        before = {n: feel.level(pet, n) for n in NEEDS}
        self.live()
        if self.thought and self.thought.done():
            self.adopt()
        if pet["plan"]:
            self.advance()
        elif pet["following"]:
            self.trail()
        self.notice(before)
        why = None if self.thought else self.wants_thought()
        if why:
            self.think(why)

    def sleep_tick(self):
        """Asleep: the clock moves and energy returns, but the pet does nothing (v1 §9)."""
        pet, h, cfg = self.pet, self.eng.house, self.cfg
        if not pet["sleep"]:
            if pet["plan"]:
                self.end_plan("interrupted")
            pet["sleep"], pet["following"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}, None
            for other in here(h, pet, awake=True):
                add_event(h, other, "%s has fallen asleep" % actions.handle(h, other, pet))
        if not pet["sleep"]["done"] and self.night is None:
            self.night = self.eng.spawn(sleep.night(self))
        pet["needs"]["energy"] = min(100.0, pet["needs"]["energy"] + cfg["sleep"]["restore_per_10s"] * cfg["dt"])
        room = h["rooms"][pet["room"]]
        pet["sleep"]["ticks"] = pet["sleep"].get("ticks", 0) + 1
        if things.light_on(h, cfg, room) and room["type"] not in physics.NO_HARSH_LIGHT:
            pet["sleep"]["lit"] = pet["sleep"].get("lit", 0) + 1
        else:   # sleep in the dark eases it; by a bed or blanket, more (the v2 lights rule, felt over a whole night)
            snug = any(o.get("fix", {}).get("cozy") and dist(pet["pos"], o["pos"]) <= 1 for o in room["objects"].values())
            cap = cfg["sleep"]["cozy_cap" if snug else "comfort_cap"]
            pet["sleep"]["snug"] = snug
            if pet["needs"]["comfort"] < cap:
                pet["needs"]["comfort"] = min(cap, pet["needs"]["comfort"] + cfg["sleep"]["comfort_per_10s"] * cfg["dt"])
        if pet["sleep"]["done"] and h["clock"]["phase"] != "night":
            dream = pet["last_night"]["dream"]
            pet["events"] = []   # the reset: only journal, beliefs and self carry into the new day
            how = "you slept badly: there was a light on you all night" if pet["sleep"].get("lit", 0) > pet["sleep"]["ticks"] / 2 \
                else "you slept well, snug" if pet["sleep"].get("snug") else "you slept well in the dark"
            add_event(h, pet, "you woke up; %s" % how + ('. you remember thinking: "%s"' % dream if dream else ""))
            pet["news"].append("woke")
            pet["sleep"], pet["phase_seen"], self.night, self.today = None, h["clock"]["phase"], None, []
            N = cfg["novelty"]
            pet["times"] = {k: min(n, N["cap"]) - N["eases"] for k, n in pet["times"].items() if n > N["eases"]}   # a little novelty comes back overnight
            pet["scent"] = {}
            pet["seen_at"] = {k: t for k, t in pet["seen_at"].items() if k in pet["times"]}
            old, new = pet["stage"], life.grow(h, cfg, pet)   # stages come with days lived, checked each morning (§4.1)
            if new:
                self.note({"pet": pet["id"], "tick": h["tick"], "type": "stage", "from": old, "to": new})
                log.put(self.eng.db, "stages", pet=pet["id"], tick=h["tick"], day=h["clock"]["day"], stage_from=old, stage_to=new)
                self.remember_self()


class Engine:
    """The running house: its state, every pet's mind, the one queue of model calls, the lineage's log."""

    def __init__(self, cfg, data_dir, make_brain):
        self.cfg, self.dir, self.make_brain = cfg, Path(data_dir), make_brain
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "house.json"
        self.house = json.loads(self.path.read_text()) if self.path.exists() else new_house(cfg)
        self.sched, self.minds, self.db, self.narrator, self.present, self.tasks = Scheduler(), {}, None, None, None, set()
        self.sched.most = cfg["model"]["parallel"]
        if self.house["lineage"]:
            self.open_lineage()
        for pet in self.house["pets"].values():
            if pet["stage"] not in ("egg", "dead"):
                self.minds[pet["id"]] = Mind(self, pet)

    def lineage_dir(self, n=None):
        return self.dir / ("lineage-%d" % (n or self.house["lineage"]["id"]))

    def open_lineage(self):
        d = self.lineage_dir()
        d.mkdir(parents=True, exist_ok=True)
        self.db = log.open_db(d / "lineage.db")
        self.narrator = self.make_brain(self.cfg, d / "house", "%s|house" % self.house["seed"], {"lineage": self.house["lineage"]["id"], "pet": "house"})

    def new_lineage(self, told=None, body=None):
        """A first egg in the nursery. The house stays as the last family left it (§4.2)."""
        if self.db:
            self.db.commit()
        pet = life.found(self.house, self.cfg, told, body)
        self.open_lineage()
        log.pet_row(self.db, pet)
        for m in told or []:
            log.put(self.db, "messages", pet=m.get("by") or "before", tick=self.house["tick"], kind="message", to_pet=pet["id"], text=m["text"])
        self.save()
        return pet

    def relation(self, me, other):
        return relation(self.house, me, other)

    def spawn(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def over_budget(self):
        """Is the house at its budget of model calls (§11.1)? Counted over the last hour and the last tenth of
        one, so a burst does not starve the rest of the hour."""
        h, per_hour = self.house, self.cfg["model"]["calls_per_hour"]
        hour = ticks(self.cfg, 3600)
        h["calls"] = [t for t in h["calls"] if t > h["tick"] - hour]
        return len(h["calls"]) >= per_hour or sum(t > h["tick"] - hour // 10 for t in h["calls"]) >= per_hour / 10

    def call(self, priority, pet_id, kind, why, fn, chars=0):
        """Queue one model call and log it when it is done."""
        async def run():
            t0, failed = time.monotonic(), None
            try:
                out = await fn()
                failed = out if isinstance(out, str) and kind == "act" else None
                return out
            except Exception as e:
                failed = repr(e)[:200]
                raise
            finally:
                self.house["calls"] = [t for t in self.house["calls"] if t > self.house["tick"] - ticks(self.cfg, 3600)] + [self.house["tick"]]
                log.put(self.db, "calls", pet=pet_id, tick=self.house["tick"], kind=kind, why=why,
                        seconds=round(time.monotonic() - t0, 2), failed=failed, chars=chars)
        return self.sched.submit(priority, run)

    def kill(self, pet, cause):
        """A life ends (§4.2): its last plan is closed, its record written, its words handed on."""
        h, m = self.house, self.minds.pop(pet["id"])
        for task in (m.thought, m.night):
            if task and not task.done():
                task.cancel()
        if pet["plan"]:
            m.end_plan("died")
        life.die(h, self.cfg, pet, cause)
        rec = pet["life"] = story.life_record(self, pet, m.mem)
        (m.dir / "life.json").write_text(json.dumps(rec, indent=1))
        log.pet_row(self.db, pet, rec)
        if pet["last_words"]:
            log.put(self.db, "messages", pet=pet["id"], tick=h["tick"], kind="last words", to_pet=None, text=pet["last_words"])
        story.dropped(self, pet)
        m.note({"pet": pet["id"], "tick": h["tick"], "type": "death", "cause": cause})
        m.save()

    def busy(self):
        """Is any model call or night's work in flight? In turbo time the world waits while there is."""
        return self.sched.busy() or bool(self.tasks)

    def bury(self, pet):
        h = self.house
        life.bury(h, self.cfg, pet)
        keep = ("id", "name", "lineage", "gen", "parent", "children", "word", "stage", "stage_before", "laid", "born", "died", "cause",
                "genome", "temper", "eggs", "made", "life", "buried", "room", "pos", "sleep", "said", "useful", "message", "told")
        kept = {k: pet[k] for k in keep}
        pet.clear()          # the dead need no working memory: what is left is the family tree and the life record
        pet.update(kept)
        dead = sorted((p for p in h["pets"].values() if p.get("buried")), key=lambda p: p["died"])
        for old in dead[:-40]:   # the long dead are kept in the lineage's log and their folder, not in memory
            if all(c not in h["pets"] or h["pets"][c]["stage"] == "dead" for c in old["children"]):
                del h["pets"][old["id"]]

    def flush(self):
        """Move what the tick produced into the log."""
        h, db = self.house, self.db
        if not db:
            return
        for m in h["fresh_moments"]:
            log.put(db, "moments", **m)
        for e in h["fresh_events"]:
            log.put(db, "events", **e)
        for c in h["fresh_creatures"]:
            log.put(db, "creatures", **c)
        for s in h["said"]:
            log.put(db, "social", tick=s["tick"], from_pet=s["from"], to_pet=s["to"], kind=s["kind"], text=s["text"], reply=int(bool(s.get("reply"))))
        h["fresh_moments"], h["fresh_events"], h["fresh_creatures"], h["said"] = [], [], [], []
        for room in h["rooms"].values():
            if room["type"] and not room.get("logged"):
                room["logged"] = True
                log.put(db, "rooms", room=room["id"], type=room["type"], tick=room["found"], by=room["by"], seed=str(h["seed"]))

    async def tick(self, present=None):
        """One tick of the whole house. `present` is the room the visitor is looking at, if anyone is."""
        await asyncio.sleep(0)   # let finished thoughts and night's work land
        h, cfg, self.present = self.house, self.cfg, present
        if present:
            h["visitor_last"], h["visitor_room"] = h["tick"], present
        director.begin(h, cfg)
        things.behave(h, cfg)
        seconds = cfg["clock"]["tick_seconds"]
        for pet in list(h["pets"].values()):
            if pet["stage"] == "egg":
                if (h["tick"] - pet["laid"]) * seconds >= cfg["life"]["egg_minutes"] * 60:
                    life.hatch(h, cfg, pet)
                    self.minds[pet["id"]] = Mind(self, pet)
                    self.minds[pet["id"]].log_body("hatched")
                    log.pet_row(self.db, pet)
                    log.put(self.db, "stages", pet=pet["id"], tick=h["tick"], day=h["clock"]["day"], stage_from="egg", stage_to="hatchling")
            elif pet["stage"] == "dead":
                if not pet.get("buried") and (h["tick"] - pet["died"]) * seconds >= cfg["life"]["fade_minutes"] * 60:
                    self.bury(pet)
            elif life.due(h, cfg, pet):
                self.kill(pet, life.due(h, cfg, pet))
            else:
                self.minds[pet["id"]].tick()
        if h["tick"] % ticks(cfg, 60) == 0:
            story.daily(self)
        self.flush()
        h["tick"] += 1
        if h["tick"] % 5 == 0:   # every tick would be a lot of disk for a two-second clock
            self.save()

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.house))
        tmp.replace(self.path)
        for m in self.minds.values():
            m.save()
        if self.db:
            self.db.commit()


def stub_brains(cfg, directory, seed, tag):
    from .brains.stub import Stub
    return Stub(cfg, directory, seed, tag)


def model_brains(cfg, directory, seed, tag):
    from .brains.model import Model
    return Model(cfg, directory, tag)


def summary(eng):
    """A headless run in a few lines, from the log."""
    h, db = eng.house, eng.db
    q = lambda sql: db.execute(sql).fetchall()
    pets = list(h["pets"].values())
    print("day %d, %s; lineage %d; %d pets ever, %d alive; generations %d; rooms found: %s" % (
        h["clock"]["day"], h["clock"]["season"], h["lineage"]["id"], h["n"]["pet"], len(alive(h)),
        max(p["gen"] for p in pets), ", ".join(r["type"] for r in h["rooms"].values() if r["type"])))
    print("steps:", dict(q("SELECT kind, count(*) FROM steps GROUP BY 1 ORDER BY 2 DESC")))
    print("not possible:", dict(q("SELECT substr(reason, 1, 40), count(*) FROM steps WHERE reason IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 8")))
    print("intentions:", dict(q("SELECT score, count(*) FROM intentions GROUP BY 1")))
    print("moments:", dict(q("SELECT kind, count(*) FROM moments GROUP BY 1 ORDER BY 2 DESC")))
    print("events:", dict(q("SELECT kind, count(*) FROM events GROUP BY 1")), "| creatures:", dict(q("SELECT kind || ' ' || substr(what, 1, 6), count(*) FROM creatures GROUP BY 1")))
    print("social:", dict(q("SELECT kind, count(*) FROM social GROUP BY 1")), "| replies:", q("SELECT count(*) FROM social WHERE reply=1")[0][0])
    print("claims:", dict(q("SELECT relation, count(*) FROM claims GROUP BY 1")), "| sayings:", [(c["text"][:40], len(c["gens"])) for c in story.sayings(h, 3)])
    print("deaths:", dict(Counter("%s as %s" % (p["cause"], p.get("stage_before")) for p in pets if p["stage"] == "dead")))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=40, help="world days to run through")
    args = ap.parse_args()
    cfg = load_config()
    with tempfile.TemporaryDirectory() as d:
        eng = Engine(cfg, d, stub_brains)
        eng.new_lineage()
        t0 = time.monotonic()
        for i in range(round(args.days * cfg["ticks_per_day"])):
            await eng.tick()
            if eng.house["lineage"]["ended"]:
                eng.new_lineage()
        eng.save()
        print("%.0f world days in %.1f s; house.json %d kB; db %d kB" % (
            args.days, time.monotonic() - t0, eng.path.stat().st_size // 1024, (eng.lineage_dir() / "lineage.db").stat().st_size // 1024))
        summary(eng)
        pet = next(iter(alive(eng.house)), None)
        if pet and pet["id"] in eng.minds:
            print("a packet:\n" + mind.perceive(eng.house, cfg, pet, eng.minds[pet["id"]].mem)[0])


if __name__ == "__main__":
    asyncio.run(main())
