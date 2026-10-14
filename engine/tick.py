"""The loop (SPEC-v2 §3, SPEC-v3 §11). One house, many pets. The engine ticks every couple of seconds and
carries out each pet's current intention a step at a time; a model is asked for a new intention only when
there is a reason to think, and all the pets' calls go through one queue, the most pressing first.

    uv run python -m engine.tick --days 40        # a headless lineage with stub brains, prints a summary
"""
import argparse
import asyncio
import hashlib
import heapq
import json
import logging
import os
import tempfile
import time
from collections import Counter, deque
from pathlib import Path

from . import actions, body, craft, director, feel, genes, genome, hub, invent, life, log, mind, order, physics, radio, sleep, story, things, wants, world
from .memory import Memory
from .world import LONG_AGO, NEEDS, add_event, alive, dist, family, here, hours, label, load_config, moment, new_house, relation, ticks

URGENT = {"visitor", "woke", "hatched", "low", "spoken", "event"}   # news that does not wait for min_think_seconds
SEEN = {"use": "used the %s", "make": "made a %s", "unmake": "took apart the %s", "combine": "put two things together",
        "rest": "rested", "paint": "painted the room", "teach": "taught the %s something", "lay_egg": "laid an egg",
        "take": "took the %s", "gather": "picked up some %s", "drop": "put down some %s", "arrange": "moved the %s",
        "chase": "chased the %s", "compose": "made up a tune", "ask_book": "bent over the book a while", "call": "called out for something"}


class Scheduler:
    """One model call at a time across every pet, the most pressing first (§11.1)."""

    def __init__(self, mark=None, yield_to=None):
        """`mark`: a file kept while this house has a thought waiting or in flight. `yield_to`: another house's such
        file: while it is there this house holds its own calls back, so a copy on the same model waits its turn
        behind the living family (13 October 2026). A call already in flight is not stopped."""
        self.queue, self.n, self.active, self.most, self.mark, self.yield_to = [], 0, 0, 1, mark, yield_to
        self.note()

    def busy(self):
        return bool(self.queue or self.active)

    def note(self):
        try:
            if self.mark:
                self.mark.touch() if self.busy() else self.mark.unlink(missing_ok=True)
        except OSError:
            pass

    async def wait_turn(self, most=120.0):
        """Hold back while the other house is busy; at most two minutes, and not for a mark left by one that has stopped."""
        t0 = time.monotonic()
        while self.yield_to and time.monotonic() - t0 < most:
            try:
                if time.time() - self.yield_to.stat().st_mtime > 660:
                    return
            except OSError:
                return
            await asyncio.sleep(0.5)

    def submit(self, priority, fn):
        fut = asyncio.get_running_loop().create_future()
        heapq.heappush(self.queue, (priority, self.n, fn, fut))
        self.n += 1
        if self.active < self.most:
            self.active += 1
            asyncio.create_task(self.run())
        self.note()
        return fut

    async def run(self):
        try:
            while self.queue:
                _, _, fn, fut = heapq.heappop(self.queue)
                if fut.cancelled():
                    continue
                await self.wait_turn()
                self.note()
                try:
                    out = await fn()
                    if not fut.cancelled():
                        fut.set_result(out)
                except Exception as e:
                    if not fut.cancelled():
                        fut.set_exception(e)
        finally:
            self.active -= 1   # counted down here, in step with the queue check, so a call queued now starts a worker
            self.note()


class Mind:
    """One pet's running life: its memory, its brain, the thought or night's work in flight, the day so far."""

    def __init__(self, eng, pet):
        self.eng, self.pet, self.cfg = eng, pet, eng.cfg
        self.dir = eng.lineage_dir(pet["lineage"]) / pet["id"]
        self.mem = Memory(self.dir, self.cfg, eng.db, pet["id"], readonly=eng.readonly)
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
        if self.eng.readonly:
            return
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
        floor = c["min_think_seconds"] * (1 - c["patient_spread"] / 2 + c["patient_spread"] * pet["temper"]["patient"]) * (c["elder_think"] if pet["stage"] == "elder" else 1.0)
        # SPEC-v3.3: its body has everything laid out to make something: it thinks now, not at its usual time. What that
        # saves is owed back before the thought after, so it thinks no more often than it did.
        if pet.get("ready") and quiet >= c["urgent_seconds"] and not world.busy(pet) and (self.brain.instant or not self.eng.over_budget()):
            pet["think_owed"] = max(0.0, floor - quiet)
            return "ready to make"
        floor += pet.get("think_owed", 0.0)
        if quiet < (0 if self.brain.instant and not self.cfg["stub"].get("paced") else floor):
            return None
        if not self.brain.instant and self.eng.over_budget():
            return None
        if not world.busy(pet):
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
        pet["ready"] = None
        if why not in ("ready to make", "something happened"):   # (what a thought brought forward saved is paid back by the next one in its turn)
            pet["think_owed"] = 0.0
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
            self.end_plan("interrupted" if world.busy(pet) else "done")
        thought = life.last_sentence(actions.clean(str(turn.get("thought", "")), 340), 300)   # whole sentences: these are what is read
        pet["meter"] = [pet["meter"][0] + feel.meter_talk(thought), pet["meter"][1] + 1]
        pet["following"] = None
        focus = turn.get("focus")
        if isinstance(focus, dict):   # SPEC-v3.3 §1.2: what it wants to be about until it thinks again; its body keeps at it
            on = actions.find(h, pet, focus.get("target")) if actions.filled(focus.get("target")) else (None, None)
            pet["focus"] = {"type": focus["type"], "words": actions.clean(focus["words"], 120), "since": h["tick"],
                            "who": on[1]["id"] if on[0] == "pet" else None, "what": on[1] if on[0] == "thing" else None}
        now = body.state(pet)["now"]
        if now and turn["steps"]:   # what it has decided comes first: whatever its body was at ends here (a thing it had already begun on is done; one it was still on its way to is dropped)
            body.finish(self, now, cut=not body.begun(pet, now))
        pet["plan"] = {
            "thought": thought, "intention": actions.clean(turn.get("intention") or focus["words"], 120), "steps": turn["steps"][:5],
            "expect": life.last_sentence(actions.clean(turn["expect"], 230), 200), "why": why, "meter": feel.meter_talk(thought),
            "i": 0, "left": None,                       # the step it is on; ticks left doing it (None while walking there)
            "started": h["tick"], "needs0": dict(pet["needs"]), "tags": [], "tag_need": {}, "room": pet["room"],
            "step_needs0": None, "step_tags": [],
        }
        if not pet["plan"]["steps"]:   # nothing decided this time but what to be about: its body carries on
            pet["plan"]["idle"] = True
        body.state(pet)["last_still"] = True   # whatever it decided was done where it stood: its body moves next

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
        for _ in range((2 if pet["spring"] else 1) + genes.stride(self.eng.house, pet)):   # (SPEC-v3.5 §2.3: long legs walk faster)
            was, pet["pos"] = pet["pos"], [p + (g > p) - (g < p) for p, g in zip(pet["pos"], goal)]
            pet["walked"] = pet.get("walked", 0) + (pet["pos"] != was)   # tiles walked, all its life (SPEC-v3.4 §0)
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
            if goal and pet["pos"] != goal and h["tick"] - plan["step_began"] < ticks(self.cfg, self.cfg["clock"]["walk_seconds"]):   # nobody is chased for ever
                return self.walk(goal)
            plan["left"], plan["step_at"] = ticks(self.cfg, self.cfg["steps"][a["type"]]), h["tick"]
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
        act = story.act_of(h, pet, a)   # for whoever is watching (SPEC-v3.2 §5.2): what it was about, before it happens
        arrived, room = dict(pet["needs"]), h["rooms"][pet["room"]]
        name = actions.norm(a.get("target")) if t == "use" else None
        thing = room["objects"].get(name) if name and "made" in room["objects"].get(name, {}) else None
        if not reason:
            was = {"comfort": pet["needs"]["comfort"], "lit": things.light_on(h, cfg, room), "phase": h["clock"]["phase"]}
            text, fx, key = actions.apply(h, cfg, pet, a, self.mem)
            tags, scale = fx.pop("tags", []), fx.pop("scale", 1.0)
            if t == "rest":   # what it rests on and beside decides how much rest it gets
                beds = [(o["fix"]["rest"], n) for n, o in room["objects"].items() if "rest" in o.get("fix", {}) and dist(pet["pos"], o["pos"]) <= 1]
                per_10s, on = max(beds + [(cfg["effects"]["rest_per_10s"], None)], key=lambda b: b[0])
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
        story.acted(h, cfg, pet, act, not reason)
        eng.did(pet, plan.get("step_began", h["tick"]), h["tick"], t, t in ("rest", "look", "observe"), "mind", "" if reason else told[:120],
                still=h["tick"] - plan.get("step_at", h["tick"]), rest=t == "rest",
                thing=None if reason or t not in HANDLES else str(a.get(HANDLES[t]) or (a.get("recipe") or {}).get("name") or "") or None)
        b = body.state(pet)   # a decided look counts toward how much of its time goes on resting and looking, like the body's own
        b["idle"] = (b["idle"] + [int(t in ("rest", "look", "observe"))] * min(60, h["tick"] - plan.get("step_began", h["tick"]) + 1))[-cfg["body"]["window_ticks"]:]
        if reason:
            self.end_plan("not possible: " + reason)
        elif plan["i"] == len(plan["steps"]) and cfg["body"]["on"]:
            plan["idle"] = True   # the thought stays with it, and what it expected is weighed when it next thinks (SPEC-v3.3 §1.2)
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
        elif t == "write":   # SPEC-v3.1 §2.2: a saying can move between messages and walls
            story.claims(eng, pet, "writing", actions.clean(a["text"], self.cfg["writing"]["max_chars"]))
        elif t == "ask_book" and pet.get("read") and pet["read"][0]["tick"] == h["tick"]:
            story.claims(eng, pet, "book", pet["read"][0]["text"])
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
        for other in here(h, pet, awake=True):   # time beside one of another family makes a stranger someone it knows (SPEC-v3.1 §7.2)
            if family(other) != family(pet) and other["id"] not in pet.setdefault("knows", []):
                spent = pet.setdefault("with", {})
                spent[other["id"]] = spent.get(other["id"], 0) + 1
                if spent[other["id"]] >= hours(self.cfg, self.cfg["strangers"]["familiar_hours"]):
                    pet["knows"].append(other["id"])
                    add_event(h, pet, "the stranger is no stranger now: you know %s" % actions.handle(h, pet, other))

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
        genes.live(h, self.cfg, pet)   # SPEC-v3.5 §2.3: what its body does for it, and how that feels
        if self.thought and self.thought.done():
            self.adopt()
        if world.busy(pet):
            self.advance()
        if h["tick"] % self.cfg["wants"]["every_ticks"] == 0:   # SPEC-v3.4 §2.1: what it wants, looked over: met, faded, and what comes next
            wants.refresh(h, self.cfg, pet)
        if self.cfg["body"]["on"] and not world.busy(pet):   # (also on the tick its last decided step ends)
            body.tick(self)   # SPEC-v3.3 §1: between the things it decides, its body is never doing nothing
        elif pet["following"] and not world.busy(pet):
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
                self.end_plan("interrupted" if world.busy(pet) else "done")
            pet["sleep"], pet["following"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}, None
            pet["sleeps_in"] = pet["room"]   # where it sleeps: a room's sleeping corner holds one bed-thing for each who does (order.corners)
            if body.state(pet)["now"]:
                body.finish(self, body.state(pet)["now"], cut=True)
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
            for text in pet.pop("on_wake", []):   # what happened round it while it slept, that it would find on waking
                add_event(h, pet, text)
            pet["news"].append("woke")
            self.eng.did(pet, pet["sleep"]["since"], h["tick"], "asleep", True, "sleep", "", still=h["tick"] - pet["sleep"]["since"], rest=True)
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


# the steps a mind decides in which a thing is picked up, used, carried, put away or made with (SPEC-v3.4 §0), and where the step names it
HANDLES = {"use": "target", "gather": "what", "drop": "what", "make": "name", "unmake": "target", "combine": "a", "arrange": "object", "put_away": "what",
           "take_out": "what", "hang": "what", "give": "what", "take": "what", "teach": "target", "show": "what", "process": "what", "mend": "target"}


class Engine:
    """The running house: its state, every pet's mind, the one queue of model calls, the lineage's log."""

    def __init__(self, cfg, data_dir, make_brain, readonly=False):
        """`readonly`: open a house only to look at it (an archived run, PET_PAUSED). It is brought up to date in memory
        so the view can draw it, and nothing of it is written back: not the house, not a pet's files, not its log."""
        self.cfg, self.dir, self.make_brain, self.readonly = cfg, Path(data_dir), make_brain, readonly
        if not readonly:
            self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "house.json"
        self.house = json.loads(self.path.read_text()) if self.path.exists() else new_house(cfg)
        before = round(cfg["clock"].get("was_day_seconds", cfg["clock"]["day_seconds"]) / cfg["clock"]["tick_seconds"])   # the day this profile's houses had, if it has been made longer
        if "profile" in self.house and self.house["profile"] != cfg.get("profile"):
            # a house may move to a profile that keeps its world clock (turbo to live): its logs still read the same
            was = load_config(profile=self.house["profile"])
            if was["clock"]["tick_seconds"] != cfg["clock"]["tick_seconds"] or was["ticks_per_day"] not in (cfg["ticks_per_day"], before):
                raise ValueError("this house was made with profile %r; start it with PET_PROFILE=%s" % (self.house["profile"], self.house["profile"] or ""))
        # a house whose day has been made longer keeps its clock and its ages (world.wt): the change is noted once, here
        was = self.house.get("day_ticks") or before
        if was != cfg["ticks_per_day"] and self.house["tick"]:
            if self.house.get("shift"):
                raise ValueError("this house has changed the length of its day once already")
            self.house["shift"] = {"until": self.house["tick"], "by": cfg["ticks_per_day"] / was - 1}
        self.house["day_ticks"], cfg["shift"] = cfg["ticks_per_day"], self.house.get("shift")
        from . import season
        season.settle(self.house, cfg)   # SPEC-v3.5 §5: a house whose seasons were made longer keeps the season it is in; a forced season is said
        self.house["profile"] = cfg.get("profile")   # so the Lab and the showcase script read the logs on the same clock
        # SPEC-v3.1 comes to a house that is already lived in: the discoveries are counted from this tick, and everyone
        # in it is given the few things a pet now carries. Nothing else about the house or the family is touched.
        self.house.setdefault("v31", {"at": self.house["tick"], "arrived": {}})
        for pet in self.house["pets"].values():
            if pet["stage"] != "dead":
                for k, v in (("family", 1), ("songs", []), ("read", []), ("box", []), ("with", {}), ("knows", []), ("chalked", 0), ("animals", [])):
                    pet.setdefault(k, v)
        self.radio_song = None   # SPEC-v3.5.1 §5: the song the station is playing, kept fresh by the server
        invent.install(self.house, cfg)   # SPEC-v3.5 §3: the kinds this house invented are kinds here
        self.to_kinds()
        if not readonly:
            self.alive_migration()
        if not readonly and "unstuck_all" not in self.house and self.house.setdefault("unstuck_all", self.house["tick"]) is not None and self.db:
            # once, for doors that came free before anyone was told when they do: every door a draught ever shut that is
            # free now is told to whoever is in the room on either side (Quiet's was shut five world days before this)
            back = {"north": "south", "south": "north", "west": "east", "east": "west"}
            for rid, d in self.db.execute("SELECT DISTINCT room, detail FROM events WHERE kind='draught'").fetchall():
                room = self.house["rooms"].get(rid)
                if room and d in room.get("doors", {}):
                    for key in ("%s|%s" % (rid, d), "%s|%s" % (room["doors"][d], back[d])):
                        if self.house["shut"].get(key, LONG_AGO) <= self.house["tick"]:
                            director.unstuck(self.house, key)

    def to_kinds(self):
        """SPEC-v3.2 §3.2, §4: every thing made before kinds becomes the nearest kind, once (names, owners, materials,
        effects and heirloom histories are untouched), and every room is laid out as its layout file says."""
        h, cfg, mapped = self.house, self.cfg, Counter()
        recipes = [o["made"]["recipe"] for r in h["rooms"].values() if r["type"] for o in things.made(r).values()]
        recipes += [g["recipe"] for g in h.get("gone_things", [])]
        recipes += [t["recipe"] for p in h["pets"].values() for t in ((p.get("life") or {}).get("things") or [])]
        for r in recipes:
            was = things.to_kind(cfg, r)
            if was:
                mapped[was] += 1
        laid = hashlib.sha1(json.dumps(cfg.get("layouts", {}), sort_keys=True).encode()).hexdigest()[:12]
        if h.setdefault("v32", {"at": h["tick"]}).get("layouts") != laid:   # once, and again only if a layout file has changed
            h["v32"]["layouts"] = laid
            for room in h["rooms"].values():
                if room["type"]:
                    world.layout(cfg, room)
                    world.settle(h, cfg, room)
        if mapped:
            h["v32"]["kinds"] = dict(mapped)
            logging.info("v3.2: %d things became kinds: %s", sum(mapped.values()), dict(mapped))
        other = os.environ.get("PET_YIELD_TO")   # (a copy run beside the living family: the path of the family's data/model.busy)
        self.sched, self.minds, self.db, self.narrator, self.present, self.tasks = Scheduler(None if self.readonly else self.dir / "model.busy", Path(other) if other else None), {}, None, None, None, set()
        self.sched.most = cfg["model"]["parallel"]
        if self.house["lineage"]:
            self.open_lineage()
        for pet in self.house["pets"].values():
            if pet["stage"] not in ("egg", "dead"):
                self.minds[pet["id"]] = Mind(self, pet)
                # a pet that has already said yes to the name it was offered has it ("Yes, I am Garry" used not to count)
                if not pet["name"] and self.said_yes(pet) and not actions.name_taken(self.house, pet, pet["called"]) and not self.readonly:
                    actions.named(self.house, pet, self.minds[pet["id"]].mem, pet["called"].strip())

    def did(self, pet, start, end, what, passive, by, text, still=0, rest=False, thing=None):
        """What a pet was doing from one tick to another, for whoever measures how alive the house is (SPEC-v3.3 §0, §8;
        SPEC-v3.4 §0): each thing its body did, each thing its mind decided, each sleep; what it handled in doing it
        (`thing`), and how many tiles it walked since the last of these was written."""
        walked, pet["walk_logged"] = pet.get("walked", 0) - pet.get("walk_logged", 0), pet.get("walked", 0)
        if self.db and not self.readonly:
            log.put(self.db, "doing", pet=pet["id"], tick_from=start, tick_to=end, what=what, passive=int(bool(passive)), by=by, text=text,
                    still=still, rest=int(bool(rest)), room=pet["room"], x=pet["pos"][0], y=pet["pos"][1], thing=thing, walked=walked)

    def alive_migration(self):
        """SPEC-v3.3 comes to a house already lived in: everyone gets the orderly gene (drawn from the house's seed and
        its own number, as its other genes were), fixtures that keep things are given their room, and an heirloom gets
        a home by the stone or the bed."""
        h, cfg = self.house, self.cfg
        for pet in h["pets"].values():
            if "orderly" not in pet.get("temper", {}) and pet["stage"] != "dead":
                pet["temper"]["orderly"] = round(world.rnd(h, "orderly", pet["id"]).uniform(0.25, 0.75), 2)
        caps = {f["name"]: f["store"] for r in cfg["house"]["rooms"].values() for f in r["fixtures"] if f.get("store")}
        inside = {f["name"] for r in cfg["house"]["rooms"].values() for f in r["fixtures"] if f.get("inside")}
        for room in h["rooms"].values():
            if not room["type"]:
                continue
            # 12 October 2026: every room has somewhere that fits it to keep things. A room found before then is given
            # what its kind of room now starts with; whatever stood on that tile steps aside.
            new = [f for f in cfg["house"]["rooms"][room["type"]]["fixtures"] if f.get("store") and f["name"] not in room["objects"]]
            for f in new:
                room["objects"][f["name"]] = world.fixture(f)
            if new:
                world.layout(cfg, room)
                world.settle(h, cfg, room)
            for o in things.made(room).values():   # "out of the way" is no longer a place: a spot on the floor is not a home, except an heirloom's
                o.pop("tidy", None)
                if o.get("home", {}).get("pos") and not o["made"].get("heirloom"):
                    del o["home"]
                    o.pop("places", None)
            for n, o in room["objects"].items():
                if "fix" in o and n in caps and o["fix"].get("store") != caps[n]:
                    o["fix"]["store"] = caps[n]
                    if n in inside:
                        o["fix"]["inside"] = True
                if "made" in o and o["made"].get("heirloom") and not o.get("home"):
                    order.heirloom_home(h, cfg, room, o)
            for stone in [n for n, o in room["objects"].items() if "memorial" in o]:   # 12 October 2026: everyone who has a stone has a keepsake box beside it
                order.give_box(h, cfg, room, stone)
        self.unwear()
        self.v341()
        if genes.migrate(h, cfg):   # SPEC-v3.5 §2.4 comes to a house already lived in, once: everyone living gets their parts
            for m in self.minds.values():
                m.log_body("v3.5: parts")
        from . import machine
        hub.migrate(h, cfg)   # SPEC-v3.5.1: a house lived in before the machine room gains it: the machine leaves the storeroom for it
        machine.migrate(h, cfg)   # SPEC-v3.5 §4.3: a house lived in before the vending machine gains it
        hub.settle_radio(h, cfg)
        for pet in h["pets"].values():   # 13 October 2026: what it has made lately is counted over three world days, from the things themselves
            if "made_at" not in pet and pet["stage"] not in ("egg", "dead"):
                pet["made_at"] = sorted([o["made"]["tick"], "%s|%s" % (o["made"]["recipe"].get("kind"), o["made"]["recipe"].get("material"))]
                                        for r in h["rooms"].values() if r["type"] for o in things.made(r).values() if o["made"]["by"] == pet["id"])
                pet.pop("made_today", None)
        if "v34" not in h:   # SPEC-v3.4 §7.5 comes to a house already lived in, once
            h["v34"] = {"at": h["tick"]}
            for pet in h["pets"].values():   # skills from what each has done; no recipes: discovery starts fresh
                if pet["stage"] not in ("egg", "dead"):
                    craft.from_history(cfg, pet)
            for room in h["rooms"].values():
                if not room["type"]:
                    continue
                for n, o in room["objects"].items():   # what was growing in the house's beds goes on growing, as if planted; after it is picked a bed is bare until someone plants it
                    if "fix" in o and o["fix"].get("plant") and "planted" not in o:
                        o["planted"] = {"what": "seed", "at": h["tick"], "grow": float(o.get("grow") or 0.0), "watered": h["tick"], "by": None, "stage": "planted"}
                want = cfg["house"]["rooms"][room["type"]]["bits"]   # a room that now grows a bit it did not (seed, in the greenhouse) gets the places for it
                for bit, n in (want.items() if isinstance(want, dict) else ()):
                    for _ in range(n - sum(1 for s in room["spots"] if s["bit"] == bit and not s["loose"])):
                        r = world.rnd(h, "v34", room["id"], bit, len(room["spots"]))
                        room["spots"].append({"bit": bit, "pos": world.free_tile(h, cfg, room, [r.randrange(1, cfg["W"] - 1), r.randrange(1, cfg["H"] - 1)]), "ready": True, "back": None, "loose": False})

    def v341(self):
        """13 October 2026, once: each pet sleeps where it last slept (a sleeping corner holds one bed-thing for each
        who sleeps there); what was taken out of a keepsake box and left on the floor is back in it; and words from
        the box that are nothing a pet could picture are no longer wondered about."""
        h, cfg = self.house, self.cfg
        if "v341" in h:
            return
        h["v341"] = {"at": h["tick"], "boxed": []}
        last = {r[0]: r[1] for r in self.db.execute("SELECT pet, room, max(tick_to) FROM doing WHERE what = 'asleep' GROUP BY pet")} if self.db else {}
        for pet in h["pets"].values():
            if pet["stage"] in ("egg", "dead"):
                continue
            pet.setdefault("sleeps_in", pet["room"] if pet["sleep"] else last.get(pet["id"]))
            pet["unknown"] = [w for w in pet.get("unknown", []) if w in cfg["picturable"]]
            pet["wants"] = [w for w in pet.get("wants", []) if w["what"] != "word" or w["word"] in cfg["picturable"]]
        for room in [r for r in h["rooms"].values() if r["type"]]:
            for n, o in list(things.on_floor(room).items()):
                box = order.box_of(h, o["made"]["owner"])
                if box and not o["made"].get("heirloom") and o.get("home", {}).get("on") == box[1] and order.into_box(h, room, n):
                    h["v341"]["boxed"].append([n, box[1], box[0]["id"]])
        for room in [r for r in h["rooms"].values() if r["type"]]:
            room["areas"], room["mess"] = order.areas(h, cfg, room), order.clutter(h, cfg, room)
        for box, rid in dict.fromkeys((b, rid) for _, b, rid in h["v341"]["boxed"]):
            moment(h, "kept", "what had been taken out of the %s and left lying is back in it: %s" % (box, ", ".join(n for n, b, _ in h["v341"]["boxed"] if b == box)), None, rid)

    def unwear(self):
        """12 October 2026: for one waking day old things were carried to a storeroom that was full, and wore out
        there. Nothing made wears out any more, and what did is put back from the copy of the house taken just before
        (order.restore_from, a folder beside this house's data): a living pet's thing where it was, on its wall or its
        shelf if that is still free, and the dead's in their keepsake boxes. What was carried to the storeroom that
        day and still lies there untouched goes back the same way. Once; a house with no such copy is left alone."""
        h, cfg = self.house, self.cfg
        src = self.dir.resolve().parent / cfg["order"]["restore_from"] / "house.json"
        if "unworn" in h or not src.exists():
            return
        was, h["unworn"] = json.loads(src.read_text()), []
        if (was["seed"], was["lineage"].get("id")) != (h["seed"], h["lineage"].get("id")):
            return
        then = {n: (rid, o) for rid, r in was["rooms"].items() if r["type"] for n, o in r["objects"].items() if "made" in o}
        now = {n: r for r in h["rooms"].values() if r["type"] for n in r["objects"]}
        back = [g["name"] for g in h.get("gone_things", []) if g["gone"][1] == "worn out" and g["name"] in then and g["name"] not in now]
        back += [n for n, r in now.items() if r["type"] == "storeroom" and n in then and then[n][0] != r["id"] and r["objects"][n].get("on")
                 and order.last_touch(r["objects"][n]) == order.last_touch(then[n][1])]
        for n in back:
            (rid, o), owner = then[n], h["pets"].get(then[n][1]["made"]["owner"])
            room = h["rooms"][rid]
            if n in now:
                del now[n]["objects"][n]
            left = order.stores(cfg, room)
            room["objects"][n] = o
            if owner and owner["stage"] == "dead" and order.into_box(h, room, n):
                where = "in the %s" % o["on"]
            else:
                if o.get("wall") and any(x.get("wall") and x["pos"] == o["pos"] for k, x in room["objects"].items() if k != n):
                    del o["wall"]
                if o.get("on") and left.get(o["on"], 0) <= 0:
                    del o["on"]
                if not o.get("wall") and not o.get("on"):
                    o["pos"] = world.free_tile(h, cfg, room, o["pos"], n)
                where = "%s in %s" % ("on the wall" if o.get("wall") else "on the %s" % o["on"] if o.get("on") else "on the floor", room["name"])
                if owner and owner["stage"] != "dead":
                    add_event(h, owner, "your %s is back %s" % (n, where))
            h["unworn"].append([n, o["made"]["owner"], where])
            logging.info("put back: %s (%s's) %s", n, o["made"]["owner"], where)
        h["gone_things"] = [g for g in h.get("gone_things", []) if g["name"] not in back]
        if back:
            boxed = sum(1 for x in h["unworn"] if "keepsake box" in x[2])
            moment(h, "kept", "%d things that had worn out or been carried off are back: %d where they were, %d in keepsake boxes" % (len(back), len(back) - boxed, boxed), None, None)

    def said_yes(self, pet):
        """Has it lately said yes to the name it was offered? Its last words, and the last few things it said, from the log."""
        said = [pet["said"]["text"]] if pet.get("said") else []
        if self.db and actions.offered(pet):
            said += [r[0] for r in self.db.execute("SELECT text FROM social WHERE from_pet=? AND kind='speak' ORDER BY tick DESC LIMIT 12", (pet["id"],))]
        return any(actions.takes(pet, t) for t in said)

    def lineage_dir(self, n=None):
        return self.dir / ("lineage-%d" % (n or self.house["lineage"]["id"]))

    def open_lineage(self):
        d = self.lineage_dir()
        if not self.readonly:
            d.mkdir(parents=True, exist_ok=True)
        self.db = log.open_db(d / "lineage.db", self.readonly)
        self.narrator = self.make_brain(self.cfg, d / "house", "%s|house" % self.house["seed"], {"lineage": self.house["lineage"]["id"], "pet": "house"})

    def new_lineage(self, told=None, body=None):
        """A first egg in the nursery. The house stays as the last family left it (§4.2)."""
        if self.db:
            self.db.commit()
            self.db.close()
        pet = life.found(self.house, self.cfg, told, body)
        self.open_lineage()
        log.pet_row(self.db, pet)
        for m in told or []:
            log.put(self.db, "messages", pet=m.get("by") or "before", tick=self.house["tick"], kind="message", to_pet=pet["id"], text=m["text"])
            story.claims(self, {"id": "before", "gen": 0, "lineage": pet["lineage"], "room": pet["room"]}, "message", m["text"])
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
        hour = ticks(self.cfg, 3600 / self.cfg["pace"])   # a real hour: the budget is the Mac's, not the world's
        h["calls"] = [t for t in h["calls"] if t > h["tick"] - hour]
        waiting = len(self.sched.queue) + self.sched.active   # asked for but not yet answered: they will count too
        return len(h["calls"]) + waiting >= per_hour or sum(t > h["tick"] - hour // 10 for t in h["calls"]) + waiting >= per_hour / 10

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
                self.house["calls"] = [t for t in self.house["calls"] if t > self.house["tick"] - ticks(self.cfg, 3600 / self.cfg["pace"])] + [self.house["tick"]]
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
        for m in h.pop("fresh_marks", []):      # SPEC-v3.1: every inscription, song, word from the box and passage read
            log.put(db, "inscriptions", **m)
        for s in h.pop("fresh_songs", []):
            log.put(db, "songs", id=s["id"], tick=s["tick"], name=s["name"], notes=s["notes"], by=s["by"], parent=s["from"], how=s["how"], family=s["family"])
        for r in h.pop("fresh_radio", []):
            log.put(db, "radio", **r)
        for r in h.pop("fresh_reads", []):
            log.put(db, "library", **r)
        for t in h.pop("fresh_traits", []):     # SPEC-v3.5 §2.3: each body trait felt
            log.put(db, "traits", **t)
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
        order.upkeep(h, cfg)
        director.begin(h, cfg)
        things.behave(h, cfg)
        invent.tick(h, cfg)   # SPEC-v3.5 §3.0: what an invented thing does by itself (a carried light goes with its owner)
        radio.tick(h, cfg, self.radio_song)
        hub.tick(h, cfg)   # SPEC-v3.5.1: whoever is in the machine room reads its lit sign; the eldest wants the founder's statue
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
                try:
                    self.minds[pet["id"]].tick()
                except Exception:   # one pet's bad step must not stop the clock for everyone (the tick would be retried for ever)
                    logging.exception("tick failed for %s; its intention is dropped", pet["id"])
                    pet["plan"], pet["following"] = None, None
        if h["tick"] % ticks(cfg, 60) == 0:
            story.daily(self)
        self.flush()
        h["tick"] += 1
        if h["tick"] % 5 == 0:   # every tick would be a lot of disk for a two-second clock
            self.save()

    def close(self):
        """Stop: drop work in flight (a thought does not survive a restart), save, and let go of the log."""
        for task in list(self.tasks):
            task.cancel()
        self.sched.queue.clear()
        self.save()
        if self.db:
            self.db.close()
            self.db = None

    def save(self):
        if self.readonly:
            return
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
