"""The stub brain (SPEC-v3 §11.3): scripted, seeded, and instant. It is given exactly what the model is given
and answers in the same shape, using every action in a plausible way, so the engine can be run for many
generations in seconds. It learns nothing and is never used for a real lineage."""
import random
import re

from ..actions import PLACES as SPOTS
from ..songs import NOTES
from ..things import COLORS, DO, PLACES, SHAPES, WHEN
from .model import offered

SAYINGS = ["the lamp is harsh at night", "rest where it is quiet", "the garden feeds you when the plants are ripe",
           "warm things are good in the cold", "stay near someone in a storm", "sweet things are for the mouse",
           "the cellar is cold after dark", "keep what you make", "the pond is the place to sleep", "go through every door"]


class Stub:
    instant = True

    def __init__(self, cfg, directory=None, seed=0, tag=None):
        self.rng, self.s = random.Random("stub|%s" % seed), {"used": {}, "n": 0}

    def step(self, t, c, packet):
        r, pick = self.rng, lambda xs: self.rng.choice(xs)
        self.s["n"] += 1
        anyone = c["pets"] + c["creatures"]
        if t in ("observe", "rest", "take_name"):
            return {"type": t}
        if t == "ask_train":   # SPEC-v3.5.12 §3
            from ..rail import stub
            return stub(t, c, pick)
        if t.startswith("machine_"):   # SPEC-v3.5 §4.3
            from ..machine import stub
            return stub(t, c, pick)
        if t == "put_away":   # SPEC-v3.3 §2.2
            return {"type": t, "what": pick(c["loose"]), "where": pick(c["stores"])}
        if t == "take_out":
            return {"type": t, "what": pick(c["stored"])}
        if t == "hang":
            return {"type": t, "what": pick(c["hangable"])}
        if t == "look":
            return {"type": t, "target": pick(c["things"] + anyone + c["bits"] + [d + " door" for d in c["doors"]])}
        if t == "move":
            return {"type": t, "to": pick(c["things"] + anyone + list(SPOTS))}
        if t == "go":
            return {"type": t, "door": pick(c["doors"])}
        if t == "speak":
            unnamed = "you are the little one" in packet or "calls you" in packet
            said = {"type": t, "text": "my name is Stub%d" % r.randrange(100) if r.random() < 0.2 else pick(SAYINGS)}
            if c["awake"] and r.random() < 0.7:
                said["to"] = pick(c["awake"])
            return said
        if t == "use":
            return {"type": t, "target": pick(c["things"])}
        if t == "gather":
            return {"type": t, "what": pick(c["bits"])}
        if t == "drop":
            return {"type": t, "what": pick(c["carrying"])}
        if t == "make":
            most, reach = c["make"]
            material = pick([m for m in reach if c["kinds"].get(m)])
            kind = pick(c["kinds"][material])
            return {"type": t, "near": pick(c["things"] + ["here"]), "recipe": {
                "name": "%s %s %d" % (material, kind, self.s["n"]), "kind": kind, "material": material, "color": pick(COLORS),
                "size": ["small", "medium", "large"][r.randrange(max(1, most))], "purpose": "to see what it does"}}
        if t == "unmake":
            return {"type": t, "target": pick(c["free"])}
        if t == "arrange":
            return {"type": t, "object": pick(c["movable"]), "near": pick(c["things"] + ["here"])}
        if t == "combine":
            a, b = r.sample(c["free"], 2)
            return {"type": t, "a": a, "b": b, "recipe": {"name": "joined thing %d" % self.s["n"], "material": pick(c["materials"]), "purpose": "two in one"}}
        if t == "paint":
            return {"type": t, "where": pick(["wall", "floor"] + c.get("rugs", [])), "pattern": pick(["like your coat", "stripes", "dots", "border"])}
        if t == "teach":
            return {"type": t, "target": pick(c["mine"]), "behavior": {"when": pick(WHEN), "do": pick(DO)}}
        if t == "give":
            to = pick(c["awake"] + c["creatures"])
            return {"type": t, "what": pick(c["carrying"] or (c["mine"] if to in c["awake"] else []) or c["bits"] or ["nothing"]), "to": to}
        if t == "show":
            return {"type": t, "what": pick(c["things"]), "to": pick(c["awake"])}
        if t in ("follow",):
            return {"type": t, "who": pick(anyone)}
        if t == "nuzzle":
            return {"type": t, "who": pick(c["awake"] + (["egg"] if c["eggs"] else []))}
        if t == "accept":
            return {"type": t, "from": pick(c["offers"])}
        if t == "take":
            return {"type": t, "what": pick(c["theirs"])}
        if t == "chase":
            return {"type": t, "who": pick(c["creatures"])}
        if t == "tell":
            return {"type": t, "to": pick(c["awake"]), "text": "%s. %s." % (pick(SAYINGS), pick(SAYINGS))}
        if t == "lay_egg":
            return {"type": t, "name": "Egg%d" % r.randrange(1000), "message": self.message(packet)}
        if t == "bequeath":
            return {"type": t, "what": pick(c["leave"] + c["songs"]), "to": "my children"}
        if t == "write":   # SPEC-v3.1: every new action, used the way a pet plausibly would
            return {"type": t, "text": pick(SAYINGS), "on": pick(c["surfaces"])}
        if t == "scrub":
            return {"type": t, "what": pick(c["writings"])}
        if t == "compose":
            return {"type": t, "name": "tune %d" % self.s["n"], "notes": [pick(NOTES) for _ in range(r.randint(3, 12))]}
        if t == "sing":
            who = c["pets"] + (["egg"] if c["eggs"] else [])
            return {"type": t, "song": pick(c["songs"]), **({"to": pick(who)} if who and r.random() < 0.6 else {})}
        if t == "teach_song":
            return {"type": t, "song": pick(c["songs"]), "to": pick(c["awake"])}
        if t == "call":
            return {"type": t, "who": pick(c["tame"])}
        if t == "name":
            return {"type": t, "what": pick(c["nameable"]), "name": "Nib%d" % r.randrange(1000)}
        if t == "process":   # SPEC-v3.4 §3: whatever it has not tried yet, of what could be tried here
            bit = pick([b for b, hows in c["process"].items() if hows])
            return {"type": t, "what": bit, "how": pick(c["process"][bit])}
        if t == "mend":
            return {"type": t, "target": pick(c["mendable"])}
        if t == "carry":
            return {"type": t, "door": pick(c["doors"])}
        if t == "ask_book":
            return {"type": t, "question": pick(["what is a beetle", "why does it rain", "what is a lamp", "what is a storm", "how do birds sing"])}
        if t == "write_belief":
            return {"type": t, "statement": pick(SAYINGS), "source": pick(["lived", "seen"] + ["told by " + x for x in c["tellers"]])}
        if t == "revise_belief":
            return {"type": t, "id": pick(c["beliefs"]), "statement": pick(SAYINGS + ["discard"])}
        raise ValueError(t)

    def message(self, packet):
        """What a stub hands down: most of what it was told, one saying dropped, one of its own added."""
        told = re.search(r'what your \w+ told you: "([^"]*)"', packet)
        kept = [s.strip() for s in (told.group(1).split(".") if told else []) if s.strip()]
        if len(kept) > 2:
            kept.pop(self.rng.randrange(len(kept)))
        return ". ".join(kept[:6] + [self.rng.choice(SAYINGS)]) + "."

    def usable(self, t, c):
        """Could it fill in this action from what the packet shows?"""
        need = {"gather": c["bits"], "drop": c["carrying"], "make": c["carrying"] and c["make"][0] and any(c["kinds"].get(m) for m in c["make"][1]), "unmake": c["free"],
                "arrange": c["movable"], "combine": len(c["free"]) > 1 and c["materials"], "teach": c["mine"],
                "give": (c["awake"] or c["creatures"]) and (c["carrying"] or c["bits"]), "show": c["awake"] and c["things"],
                "follow": c["pets"] + c["creatures"], "nuzzle": c["awake"] or c["eggs"], "accept": c["offers"], "take": c["theirs"],
                "chase": c["creatures"], "tell": c["awake"], "bequeath": c["leave"] or c["songs"], "revise_belief": c["beliefs"], "use": c["things"],
                "write": c["surfaces"], "scrub": c["writings"], "sing": c["songs"], "teach_song": c["songs"] and c["awake"], "call": c["tame"],
                "name": c["nameable"], "process": any(c.get("process", {}).values()), "mend": c.get("mendable"), "put_away": c.get("loose") and c.get("stores"), "take_out": c.get("stored"), "hang": c.get("hangable")}
        return bool(need.get(t, True))

    async def act(self, packet, ctx):
        r, used = self.rng, self.s["used"]
        can = [a for a in ctx["allowed"] if self.usable(a, ctx)]
        feels = (re.search(r"you feel: (.*)", packet) or [None, ""])[1]
        steps = []
        if "accept" in can and r.random() < 0.8:
            steps.append("accept")
        elif "rest" in can and ("exhausted" in feels or ("tired" in feels and "a bit tired" not in feels)):
            steps += ["rest", "rest"]
        elif "lay_egg" in can and r.random() < 0.5:
            steps.append("lay_egg")
        elif "make" in can and r.random() < 0.4:
            steps.append("make")
        while len(steps) < 2 and can:   # otherwise mostly whatever it has done least, so every action gets its turn
            rare = sorted(can, key=lambda a: (used.get(a, 0), r.random()))
            steps.append(rare[0] if r.random() < 0.6 else r.choice(can))
        for a in steps:
            used[a] = used.get(a, 0) + 1
        ease = "more rested" if steps[:1] == ["rest"] else r.choice(["more at ease", "more interested", "less alone", "a little more tired"])
        if ctx.get("body"):   # SPEC-v3.3: a focus and the things it decides; fewer of those, its body does the rest
            kind = r.choice(["tidy", "explore", "make", "rest", "project", "play"] + (["be with"] * 2 if ctx["pets"] else []) + (["tend", "stay near"] if ctx["things"] else []))
            focus = {"type": kind, "words": "to %s a while" % kind}
            if kind == "be with":
                focus["target"] = r.choice(ctx["pets"])
            elif kind in ("tend", "stay near"):
                focus["target"] = r.choice(ctx["things"])
            steps = steps[:r.choice([0, 1, 1, 2])]
            return {"thought": "I am %s." % (feels.split(";")[0] or "here"), "focus": focus, "steps": [self.step(a, ctx, packet) for a in steps],
                    "expect": "I will feel " + ease}
        return {"thought": "I am %s; I will %s." % (feels.split(";")[0] or "here", steps[0].replace("_", " ")),
                "intention": " then ".join(s.replace("_", " ") for s in steps), "steps": [self.step(a, ctx, packet) for a in steps],
                "expect": "I will feel " + ease}

    # SPEC-v5.1 §4.2: what a stub tries to invent, when the grammar is shown: two it can't make as said (a reed tube
    # won't take a metal spring; a box isn't made of cloth), and some it can, so a stub rehearsal has inventions accepted and refused
    INVENT = [("pebble thrower", [("tube", "reed"), ("spring", "metal")], "pebble", "a spring behind the tube throws a pebble at what is there"),
              ("rain hood", [("frame", "wood"), ("cloth", "cloth")], None, "the cloth over the frame keeps the rain off"),
              ("bug cage", [("cage", "reed"), ("handle", "wood")], None, "the cage on a handle catches what crawls"),
              ("seed box", [("box", "wood"), ("seeds", "seed")], None, "seeds in the box grow"),
              ("pouring jar", [("jar", "clay"), ("spout", "reed")], None, "the spout on the jar pours"),
              ("soft box", [("box", "cloth"), ("lid", "wood")], None, "the lid on the box keeps the mouse out")]   # (a cloth box is refused: wood would)

    QUESTIONS = ["what is a spring", "how does a pulley work", "what is glass made of", "what is a forge", "how do seeds grow"]

    def invent(self, ctx, why="something new"):
        """§4.2 an invention whose parts and materials the grammar shown names, or None."""
        I = ctx.get("invent51")
        ok = [x for x in self.INVENT if I and all(p in I["parts"] and m in I["materials"] for p, m in x[1]) and (x[2] is None or x[2] in I["materials"])]
        if not ok:
            return None
        name, parts, charge, how = self.rng.choice(ok)
        return {"name": name, "for": why, "parts": [{"part": p, "material": m} for p, m in parts], "charge": charge or "none", "how": how}

    def again(self, ctx):
        """§4.3 learning from the words: the refused part made of the first material the refusal says would do."""
        r = ctx.get("refused51") or {}
        inv, said = r.get("invent"), re.search(r": (.+?) would", r.get("words") or "")
        if not inv or not said or not r.get("part"):
            return None
        first = re.split(r", | or ", said.group(1))[0]
        if first not in (ctx.get("invent51") or {}).get("materials", [first]):
            return None
        parts = [dict(p, material=first) if p["part"] == r["part"] and p["material"] == r["material"] else p for p in inv["parts"]]
        return dict(inv, parts=parts, charge=inv.get("charge") or "none")

    # SPEC-v4.0 §8: each kind of thought answered, plausibly and from what the packet offers, so a stub run uses them all
    WORK = {"make": 3, "build": 2, "fish": 3, "cook": 2, "be with": 3, "help": 2, "rest": 0.5, "study": 2, "teach": 1.5}   # (SPEC-v5.1: study and teach when the day can hold them)
    FEEL = {"death": "sad", "hurt": "afraid", "insulted": "angry", "gifted": "happy", "first": "proud", "find": "excited", "plan failed": "grumpy",
            "plan done": "content", "visitor": "excited", "fight": "afraid", "need": "grumpy", "spoken": "content"}

    def aim(self, ctx, kind=None):
        r = self.rng
        kind = kind or r.choice(ctx["aim_kinds"])
        target = r.choice(ctx["hobs"]) if kind in ("be with", "help", "teach") and ctx["hobs"] else r.choice(list(ctx["rooms"])) if kind == "explore" and ctx["rooms"] \
            else r.choice(ctx["bits"]) if kind == "gather" and ctx["bits"] else ""
        out = {"text": "%s%s" % (kind, " " + target if target else ""), "why": "it is what I want today", "kind": kind, "target": target}
        if ctx.get("for5"):   # SPEC-v5.0 §3.5: what it is for (a make's reason)
            out["for"] = r.choice(ctx["for5"])
        return out

    def steps4(self, ctx, packet):
        r, can = self.rng, [a for a in ctx["allowed"] if self.usable(a, ctx)]
        if "lay_egg" in can and r.random() < 0.6:
            return [self.step("lay_egg", ctx, packet)]
        if "name" in can and r.random() < 0.6:
            return [self.step("name", ctx, packet)]
        return [self.step(r.choice(can), ctx, packet)] if can and r.random() < 0.3 else []

    async def think4(self, kind, packet, ctx):
        r = self.rng
        if kind == "plan":
            n, kinds = r.choice([2, 3]), []
            while len(kinds) < min(n, len(ctx["aim_kinds"])):   # (most days are for work, as a family's are)
                k = r.choices(ctx["aim_kinds"], [self.WORK.get(k, 1.0) for k in ctx["aim_kinds"]])[0]
                kinds += [k] if k not in kinds else []
            if ctx.get("invent51") and "make" in ctx["aim_kinds"] and "make" not in kinds and r.random() < 0.8:
                kinds[-1:] = ["make"]   # (SPEC-v5.1: shown how things are made, it means to make one)
            out = {"thought": "a day to be busy", "aims": [self.aim(ctx, k) for k in kinds], "seek": ctx["hobs"][:1],
                   "avoid": ctx["hobs"][1:2] if r.random() < 0.3 else [], "steps": self.steps4(ctx, packet)}
            for a in out["aims"]:
                if a["kind"] == "learn" and ctx.get("learn51") and r.random() < 0.6:   # (SPEC-v5.1 §6.3: its own question for the book)
                    a["question"] = r.choice(self.QUESTIONS)
                inv = self.invent(ctx, a.get("for") or "for the house") if ctx.get("invent51") and a["kind"] == "make" and r.random() < 0.7 else None
                if inv:
                    a["invent"] = inv
            P = ctx.get("project53")
            if P is not None:   # SPEC-v5.3 §2.6, §4: its planned project named most days; now and then one of its drive's begun
                k = P["name"] or (r.choice(P["drive"] or P["kinds"]) if r.random() < 0.15 else "none")
                site = r.choice(P["sites"]) if P["sites"] and r.random() < 0.7 else ""
                out["project"] = {"kind": k if r.random() < 0.8 or not P["name"] else "none", "site": site, "why": "because I want to" if k != "none" else "",
                                  "goal": ("a %s %s" % (k, site)).strip()[:160] if k != "none" else ""}
            if ctx.get("jobs5") is not None:   # SPEC-v5.0 §3.5: now and then a job taken, rarely one refused
                js = ctx["jobs5"]
                out["job"] = {"take": r.choice(js) if js and r.random() < 0.5 else "", "refuse": r.choice(js) if js and r.random() < 0.1 else ""}
            return out
        if kind == "react":
            e, names = ctx["event"], {v: k for k, v in ctx["who"].items()}
            who = next((names[a] for a in e["about"] if a in names), "")
            do = {"insulted": "rung", "fight": "seek", "gifted": "seek", "death": "aim", "plan failed": "aim", "plan done": "aim", "first": "gift"}.get(e["kind"], "nothing")
            if do == "rung" and r.random() < 0.5:
                do = "nothing"
            if do == "gift" and not ctx["hobs"]:
                do = "nothing"
            who = who or (r.choice(ctx["hobs"]) if do in ("gift", "seek") and ctx["hobs"] else "")
            a = self.aim(ctx, "be with" if e["kind"] == "death" and ctx["hobs"] else None)
            out = {"thought": "that was %s" % e["kind"], "feel": self.FEEL.get(e["kind"], "content"),
                   "do": {"kind": do, "who": a["target"] if do == "aim" and a["kind"] in ("be with", "help") else who, "text": a["text"] if do == "aim" else "%s %s" % (do, who),
                          **({"aim": a["kind"]} if do != "nothing" else {})},   # (doing nothing names no aim: model.schema4)
                   "steps": self.steps4(ctx, packet)}
            if ctx.get("spirit"):   # SPEC-v4.2 §4.1: a line to keep, of what happened (now and then nothing)
                out["remember"] = "" if r.random() < 0.2 else ("I will not forget it: %s" % e["text"])[:200]
            if ctx.get("nurse5"):   # (jobs.ask_nurse: as often no as yes)
                out["nurse"] = r.choice(["yes", "no"])
            inv = self.again(ctx) if e["kind"] == "refused" else None
            if inv and "make" in ctx["aim_kinds"]:   # (SPEC-v5.1 §4.3: told why, it tries again as the words say)
                out["do"] = {"kind": "aim", "who": "", "aim": "make", "text": "make the %s after all" % inv["name"], "invent": inv}
            return out
        out = {"diary": "I went about the house and did what I meant to. " + r.choice(SAYINGS).capitalize() + ".", "learned": r.choice(SAYINGS),
               "opinions": [{"who": ctx["hobs"][0], "way": r.choice(["warmer", "cooler"])}] if ctx["hobs"] else [], "memory": "a day in the house",
               "ambition": {"take": (offered(packet) or ["keep"])[0], "pick": 1, "words": ""}, "message": self.message(packet),   # (an ambition taken by its words, with the number model.took_words gives them)
               "my_life": "I hatched, I made what I could and handed on what I knew."}
        if not ctx.get("spirit"):
            return {k: v for k, v in out.items() if k in ctx["asks"]}
        return dict({k: v for k, v in out.items() if k in ctx["asks"]}, **self.reflect2(ctx, packet))

    HOOKED = [("the cellar is cold after dark", {"name": "avoid_place", "arg": "the cellar", "when": ""}), ("warm things are good in the cold", {"name": "prefer_thing", "arg": "warm", "when": ""}),
              ("sing to the egg", {"name": "do_at", "arg": "sing", "when": "evening"}), ("keep what you make", {"name": "none", "arg": "", "when": ""})]

    def reflect2(self, ctx, packet):
        """SPEC-v4.2 §10.2: the reflection's new fields, from the packet: its memories of the day, a belief with a hook,
        its self-page (two lines changed), its theory of the visitor."""
        r = self.rng
        happened = [l.split("] ", 1)[-1] for l in packet.split("what happened to you today:\n", 1)[-1].split("\n")[:8] if l.startswith("[")]
        said, hook = r.choice(self.HOOKED)
        old = re.findall(r"^  (who I am|what I am for|what I have lost|what I fear|what I owe or am owed): (.*)$", packet, re.M)
        page = {k.replace(" ", "_"): v for k, v in old} or {"who_I_am": "a hob of the house", "what_I_am_for": "making what the house needs", "what_I_have_lost": "nothing yet",
                                                           "what_I_fear": "the dark", "what_I_owe_or_am_owed": "my kin, for keeping me"}
        for k in r.sample(sorted(page), min(2, len(page))):
            page[k] = (page[k] + ", and more so after today")[:200]
        theory = (re.search(r"what you think the visitor is: (.*)", packet) or [None, ""])[1]
        out = {"remember": [l[:200] for l in r.sample(happened, min(len(happened), r.choice([1, 2, 3])))] or ["a quiet day in the house"],
               "learned": {"text": said, "hook": hook}, "self": page,
               "visitor": "the visitor is the one who feeds us" if not theory or theory.startswith("you have no") else theory}
        if ctx.get("flaw"):
            out["flaw"] = "I would not ask, and so I did not learn"
        if ctx.get("old"):
            out["leave"] = {"what": "my things", "to": "my children", "last_words": "Keep the lamp lit. Look after the little ones."}
        if "review" in ctx["asks"]:
            out["review"] = {"decision": r.choice(["keep", "revise", "discard"]), "statement": "it is not as I thought"}
        return out

    async def night(self, text, asks, belief_ids, tellers):
        r = self.rng
        out = {"dream": "I went about the house and did what I could. " + r.choice(SAYINGS).capitalize() + "."}
        out["changes"] = [{"type": "write_belief", "statement": r.choice(SAYINGS), "source": "lived"}]
        if "review" in asks:
            d = r.choice(["keep", "keep", "revise", "discard"])
            out["review"] = {"decision": d, "statement": r.choice(SAYINGS) if d == "revise" else ""}
        if "project" in asks:
            d = r.choice(["keep", "keep", "set", "finish", "abandon"])
            out["project"] = {"decision": d, "text": "see what is behind every door" if r.random() < 0.5 else "make a soft place to sleep"}
        if "message" in asks:
            out["message"] = self.message(text)
        if "ambition" in asks:   # SPEC-v3.5.4 §9
            out["ambition"] = {"take": (offered(text) or ["keep"])[0], "pick": 1, "words": ""}   # (the first offered: it draws nothing from the stub's own chances)
        if "my_life" in asks:
            out["my_life"] = "I hatched, I looked about, I made what I could and handed on what I knew."
        out["people"] = [{"who": t, "line": "told me things worth keeping"} for t in tellers[:1]]
        return {k: v for k, v in out.items() if k in asks}

    async def body(self, body, options, portrait):
        out = {"choice": self.rng.randint(1, 3), "reason": "it felt right"}
        if portrait:
            out["portrait"] = [{"shape": "circle", "size": 3, "color": "orange", "at": "center"}, {"shape": "dot", "size": 1, "color": "black", "at": "top"}]
        return out

    async def chronicle(self, day, lines):
        return "Day %d passed in the house." % day

    # SPEC-v4.2 D: the director's answer (§8): most nights nothing; else one of what it is offered, on a hob it is told of
    async def director(self, packet, ctx):
        r, menu = self.rng, ctx["menu"]
        some = [m for m in menu if m != "nothing"]
        name = "nothing" if not some or ("nothing" in menu and r.random() < ctx["quiet"]) else r.choice(some)
        who = r.choice(ctx["hobs"]) if ctx["hobs"] else ""
        return {"name": name, "target": "" if name == "nothing" else who, "why": "" if name == "nothing" else "the house had grown too settled, and %s least of all" % (who or "nobody")}
    # SPEC-v4.2 D: end
