"""The stub brain (SPEC-v3 §11.3): scripted, seeded, and instant. It is given exactly what the model is given
and answers in the same shape, using every action in a plausible way, so the engine can be run for many
generations in seconds. It learns nothing and is never used for a real lineage."""
import random
import re

from ..actions import PLACES as SPOTS
from ..songs import NOTES
from ..things import COLORS, DO, PLACES, SHAPES, WHEN

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
        if t in ("observe", "rest"):
            return {"type": t}
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
            return {"type": t, "wall": pick(COLORS), "floor": pick(COLORS)}
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
                "name": c["nameable"]}
        return bool(need.get(t, True))

    async def act(self, packet, ctx):
        r, used = self.rng, self.s["used"]
        can = [a for a in ctx["allowed"] if self.usable(a, ctx)]
        feels = (re.search(r"you feel: (.*)", packet) or [None, ""])[1]
        steps = []
        if "accept" in can and r.random() < 0.8:
            steps.append("accept")
        elif "exhausted" in feels or ("tired" in feels and "a bit tired" not in feels):
            steps += ["rest", "rest"]
        elif "lay_egg" in can and r.random() < 0.5:
            steps.append("lay_egg")
        elif "make" in can and r.random() < 0.4:
            steps.append("make")
        while len(steps) < 2:   # otherwise mostly whatever it has done least, so every action gets its turn
            rare = sorted(can, key=lambda a: (used.get(a, 0), r.random()))
            steps.append(rare[0] if r.random() < 0.6 else r.choice(can))
        for a in steps:
            used[a] = used.get(a, 0) + 1
        ease = "more rested" if steps[0] == "rest" else r.choice(["more at ease", "more interested", "less alone", "a little more tired"])
        return {"thought": "I am %s; I will %s." % (feels.split(";")[0] or "here", steps[0].replace("_", " ")),
                "intention": " then ".join(s.replace("_", " ") for s in steps), "steps": [self.step(a, ctx, packet) for a in steps],
                "expect": "I will feel " + ease}

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
