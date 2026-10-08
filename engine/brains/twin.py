"""The scripted twin (v1 §12): a baseline that learns by counting, with no language model. Off by default
since v2 (SPEC-v2 §10). It reads the same perception packet as the model pet and nothing else, and still
decides one action at a time: each of its intentions is a single step."""
import random
import re

from ..actions import MOVABLE
from ..world import H, NEEDS, W

DELTA = re.compile(r"(energy|comfort|curiosity) ([+-][\d.]+)")
STEADY = 0.5   # mean change under this is "stays the same", matching the engine's scorer


def parse(packet):
    """Perception text -> features."""
    line = dict(l.split(": ", 1) for l in packet.splitlines() if ": " in l and not l.startswith(" "))
    block = packet.split("since you last thought:")[1].split("\nrecent:")[0]
    own = [l for l in block.splitlines() if l.startswith("  you ")]   # what its last action did
    return {
        "phase": line["time"].split()[0],
        "tick": int(re.search(r"tick (\d+)", line["time"]).group(1)),
        "needs": {n: int(v) for n, v in re.findall(r"(energy|comfort|curiosity) (\d+)", line["needs (100 is fully met)"])},
        "objects": [o.split(" (")[0] for o in line["visible"].split(" · ")],
        "allowed": line["stage"].split("allowed actions: ")[1].split(", "),
        "last": {n: sum(float(d) for m, d in DELTA.findall(own[-1]) if m == n) for n in NEEDS} if own else None,
    }


class Twin:
    instant = True   # it answers at once, so it is not held to min_think_seconds

    def __init__(self, cfg, seed=0):
        self.explore, self.min_obs = cfg["twin"]["explore"], cfg["twin"]["belief_min_obs"]
        self.rng = random.Random(seed)
        # counts: "action|target|phase" -> {"n": observations, need: [sum, times up, times down]}
        self.s = {"counts": {}, "last": None, "written": []}

    def learn(self, f):
        last, seen = self.s["last"], f["last"]
        if not last or seen is None:
            return
        c = self.s["counts"].setdefault(last["key"], {"n": 0, **{n: [0.0, 0, 0] for n in NEEDS}})
        c["n"] += 1
        for n in NEEDS:
            d = seen.get(n, 0.0)
            c[n][0] += d
            c[n][1] += d > 0
            c[n][2] += d < 0

    def mean(self, key, need):
        c = self.s["counts"].get(key)
        return c[need][0] / c["n"] if c else 0.0   # untried counts as neutral, so it gets tried

    def due_belief(self):
        """A templated belief for the first combination seen often enough with a consistent, real effect."""
        if len(self.s["written"]) >= 20:
            return None
        for key, c in self.s["counts"].items():
            for n in NEEDS:
                total, ups, downs = c[n]
                if (c["n"] >= self.min_obs and c["n"] in (ups, downs) and abs(total / c["n"]) >= STEADY
                        and key + "|" + n not in self.s["written"]):
                    self.s["written"].append(key + "|" + n)
                    action, target, phase = key.split("|")
                    return "%s at %s %s %s" % ((action + " " + target).strip(), phase, "raises" if ups else "lowers", n)
        return None

    async def consolidate(self, journal, beliefs):
        return []   # it writes its templated beliefs while awake

    async def dream(self, journal):
        return ""

    async def choose_body(self, body, options):
        return self.rng.randrange(len(options)), "picked at random"

    async def act(self, packet):
        f = parse(packet)
        self.learn(f)
        phase, allowed = f["phase"], f["allowed"]
        need = min(f["needs"], key=f["needs"].get)
        options = [{"type": "observe"}, {"type": "rest"}]
        options += [{"type": t, "target": o} for t in ("look", "move", "use") for o in f["objects"]]
        options += [{"type": "arrange", "object": o, "tile": [self.rng.randrange(W), self.rng.randrange(H)]}
                    for o in MOVABLE]
        options = [a for a in options if a["type"] in allowed]
        key = lambda a: "%s|%s|%s" % (a["type"], a.get("target") or a.get("object") or "", phase)
        statement = self.due_belief() if "write_belief" in allowed else None
        if statement:
            action, thought = {"type": "write_belief", "statement": statement}, "seen this often enough to write it down"
        elif self.rng.random() < self.explore:
            action, thought = self.rng.choice(options), "trying something at random"
        else:
            best = max(self.mean(key(a), need) for a in options)
            action = self.rng.choice([a for a in options if self.mean(key(a), need) == best])
            thought = "%s is lowest; this has done best for it at %s" % (need, phase)
        m = self.mean(key(action), need)
        self.s["last"] = {"tick": f["tick"], "key": key(action)}
        return {"thought": thought, "intention": " ".join(str(v) for v in action.values())[:60], "steps": [action],
                "expect": "%s %s" % (need, "goes up" if m >= STEADY else "goes down" if m <= -STEADY else "stays the same")}
