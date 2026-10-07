"""The scripted twin (SPEC §12): a fair baseline that learns by counting, with no language model.
It reads the same perception packet as the model pet and nothing else."""
import random
import re

from ..actions import MOVABLE, USABLE
from ..world import H, NEEDS, W

EVENT = re.compile(r"\[t(\d+)\] ((?:you |nothing happened)[^\[]*)")
DELTA = re.compile(r"(energy|comfort|curiosity) ([+-][\d.]+)")
STEADY = 0.5   # mean change under this is "stays the same", matching the engine's scorer


def parse(packet):
    """Perception text -> features."""
    line = dict(l.split(": ", 1) for l in packet.splitlines() if ": " in l and not l.startswith(" "))
    own = EVENT.findall(line["recent"])
    return {
        "phase": line["time"].split()[0],
        "tick": int(re.search(r"tick (\d+)", line["time"]).group(1)),
        "needs": {n: int(v) for n, v in re.findall(r"(energy|comfort|curiosity) (\d+)", line["needs"])},
        "objects": [o.split(" (")[0] for o in line["visible"].split(" · ")],
        "allowed": line["stage"].split("allowed actions: ")[1].split(", "),
        "last": {"tick": int(own[-1][0]), "deltas": {n: float(d) for n, d in DELTA.findall(own[-1][1])}} if own else None,
    }


class Twin:
    def __init__(self, cfg, seed=0):
        self.explore, self.min_obs = cfg["twin"]["explore"], cfg["twin"]["belief_min_obs"]
        self.rng = random.Random(seed)
        # counts: "action|target|phase" -> {"n": observations, need: [sum, times up, times down]}
        self.s = {"counts": {}, "last": None, "written": []}

    def learn(self, f):
        last, seen = self.s["last"], f["last"]
        if not (last and seen and seen["tick"] == last["tick"]):
            return
        c = self.s["counts"].setdefault(last["key"], {"n": 0, **{n: [0.0, 0, 0] for n in NEEDS}})
        c["n"] += 1
        for n in NEEDS:
            d = seen["deltas"].get(n, 0.0)
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

    async def act(self, packet):
        f = parse(packet)
        self.learn(f)
        phase, allowed = f["phase"], f["allowed"]
        need = min(f["needs"], key=f["needs"].get)
        options = [{"type": "observe"}, {"type": "rest"}]
        options += [{"type": t, "target": o} for t in ("look", "move") for o in f["objects"]]
        options += [{"type": "use", "target": o} for o in USABLE]
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
        return {"thought": thought, "action": action,
                "expect": "%s %s" % (need, "goes up" if m >= STEADY else "goes down" if m <= -STEADY else "stays the same")}
