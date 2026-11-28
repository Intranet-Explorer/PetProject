"""Machines (SPEC-v3.6b §1): the kiln, the loom, the millstone, the forge and anvil, and the stove. Each is a building
project (building.toml, `machine`), built once in the house, one of each. Once one stands its process (crafting.toml)
is done there every time: a hob sets a load going and can go, and what comes out waits in the machine's tray (bits
beside it, marked with its name) for whoever wants it; a full tray waits to be emptied. A hob comes to want a machine
by failing at what it does (a rule with `fails`), or from the needs list once what it takes can be had. Machines
wear like anything built, are mended with the hammer, and rest at night; little ones keep back from the hot ones.
Cooking, the stove's own, is engine/cook.py. No model is asked: a mind may `process` at a machine like anywhere, and
a body works one by itself (`work a machine`, building.toml). The vending machine is engine/machine.py."""
import re
from collections import Counter

from . import build, craft
from .world import LONG_AGO, a, add_event, free_tile, label, moment, rnd, ticks

LITTLE = ("hatchling", "child", "youngling")   # (keep back from the kiln, the forge and the stove)
KEEP = 4                  # a body takes a load from the vending machine's stock only while more than this many are left
WANTED_DAYS, OFFERED_DAYS = 3, 2   # how long failing at what a machine does, or being offered one, keeps it wanted


def projects(cfg):
    """{key: project} for the building projects that are machines."""
    return {k: P for k, P in cfg["build"]["project"].items() if P.get("machine")}


def processes(cfg):
    """The processes that are done at a machine."""
    return {P["machine"]["process"] for P in projects(cfg).values()}


def key_of(o):
    """The machine this object is, built (sound or worn), or None."""
    k = (o.get("fix", {}).get("built") or {}).get("project")
    return k if build.PROJECT.get(k, {}).get("machine") else None


def standing(house, key):
    """(room, name, object) of this machine, begun or built, or None."""
    for r in house["rooms"].values():
        if r["type"]:
            n, o = build.find(r, key)
            if o:
                return r, n, o
    return None


def built(house, key):
    s = standing(house, key)
    return s if s and "site" not in s[2] else None


def at(room, how):
    """(name, object, its machine) of the sound machine in this room that does this process, or None."""
    for n, o in room["objects"].items():
        k = key_of(o)
        if k and build.sound(o) and build.PROJECT[k]["machine"]["process"] == how:
            return n, o, build.PROJECT[k]["machine"]
    return None


def tray(room, name):
    return [s for s in room["spots"] if s.get("machine") == name]


def night(house):
    return house["clock"]["phase"] == "night"


# ---- a load (craft.process calls in here for a machine's process) ----

def check(house, cfg, pet, room, how):
    """Why this machine cannot take a load from this hob now, or None (craft.check_process asks, once it is here)."""
    m = at(room, how)
    if not m:
        return None
    n, o, M = m
    if M.get("hot") and pet["stage"] in LITTLE:
        return "the %s is hot: little ones keep back from it" % n
    if night(house):
        return "the %s is banked for the night; it rests till morning" % n
    if o.get("run"):
        return "the %s is busy %s %s; it will be done soon" % (n, M["doing"], o["run"]["bit"])
    if how == "cook" and (o.get("pot") or {}).get("servings"):
        return "there is %s in the pot on the %s still: it wants eating first" % (o["pot"]["dish"], n)
    if how != "cook" and len(tray(room, n)) >= M["hold"]:
        return "the %s's tray is full: what it made wants taking first" % n
    return None


def failed(house, cfg, pet, rule):
    """A rule with `fails` did not give: what it is told, and the machine it wants now if the house has none."""
    key, s = rule["fails"], built(house, rule["fails"])
    if not s:
        pet.setdefault("wants_machine", {})[key] = house["tick"]
        return rule.get("fail") or rule["says"]
    return "%s; the %s in %s would do it" % (rule.get("fail") or rule["says"], s[1], s[0]["name"])


def fails(house, pet, rule):
    """Does this try fail: a rule that only fails, or one that gives now and then (`chance`) and not this time?"""
    if not rule.get("fails"):
        return False
    return not rule.get("gives") or rnd(house, "chance", pet["id"], house["tick"]).random() >= rule.get("chance", 0.0)


def needed(house):
    """The bits the things being built in the house still want."""
    out = set()
    for r in house["rooms"].values():
        for o in r["objects"].values() if r["type"] else ():
            if "site" in o:
                out |= set(build.missing(build.PROJECT[o["site"]["project"]], o))
    return out


def made(house):
    """What the machines have made, all told: Counter of product."""
    out = Counter()
    for r in house["rooms"].values():
        for o in r["objects"].values() if r["type"] else ():
            out.update(o.get("output", {}))
    return out


def pick(house, cfg, pet, rule):
    """What one load comes out as, where it could be more than one thing: what is wanted (a thing being built takes
    it, or a want of its own names it), else what the house has made least of (SPEC-v3.6b §3: no new habits)."""
    from .contracts import on5
    opts = [rule["gives"]] + rule.get("also", []) + (rule.get("also5", []) if on5(cfg, "items") else [])   # (SPEC-v5.0 §1.6: the mill's oil)
    if len(opts) == 1:
        return opts[0]
    need, mine, n = needed(house), {w.get("gives") for w in pet.get("wants", [])} | {w.get("bit") for w in pet.get("wants", [])}, made(house)
    return min(opts, key=lambda b: (b not in need and b not in mine, n[b], opts.index(b)))


def start(house, cfg, pet, room, how, bit, gives, **more):
    """The load is in: the machine works on it for its run, and the hob may go. Returns what it is told."""
    n, o, M = at(room, how)
    o["run"] = {"bit": bit, "gives": gives, "by": pet["id"], "at": house["tick"], "done": house["tick"] + ticks(cfg, M["run"]), **more}
    o["runs"] = o.get("runs", 0) + 1
    house.setdefault("machine_runs", []).append([house["tick"], key_of(o), pet["id"], bit, gives])
    del house["machine_runs"][:-1000]
    moment(house, "machine", "%s set %s %s %s" % (label(pet), bit, M["doing"], M["at"]), pet["id"], room["id"])
    from . import spotlight
    spotlight.tried(house, cfg, key_of(o), pet)   # SPEC-v3.6c §3: it has tried the new machine
    mins = max(1, round(M["run"] / 60))
    return "it will be ready in about %s minute%s; you can go and come back" % (mins, "" if mins == 1 else "s")


def tick(house, cfg):
    """Every tick (engine/tick.py): a load whose time is up comes out."""
    t = house["tick"]
    for room in house["rooms"].values():
        for n, o in list(room["objects"].items()) if room["type"] else ():
            if o.get("run") and t >= o["run"]["done"]:
                done(house, cfg, room, n, o)


def done(house, cfg, room, name, o):
    """What a load came out as: into the tray (a bit beside the machine, marked with its name), and whoever set it
    going is told; the stove's is a pot (cook.done)."""
    r, M = o.pop("run"), build.PROJECT[key_of(o)]["machine"]
    o["warm"], pet = house["tick"], house["pets"].get(r["by"])
    if M["process"] == "cook":
        from . import cook
        return cook.done(house, cfg, room, name, o, r, pet)
    at_ = next((s["pos"] for s in tray(room, name)), None) or free_tile(house, cfg, room, o["pos"])   # (one crate: everything in the tray on one tile beside it)
    room["spots"].append({"bit": r["gives"], "pos": list(at_), "ready": True, "back": None, "loose": True, "since": house["tick"], "machine": name})
    o.setdefault("output", {})[r["gives"]] = o.get("output", {}).get(r["gives"], 0) + 1
    if pet and pet["stage"] not in ("egg", "dead"):
        pet["got"] = [r["gives"], house["tick"]]   # (a want to get it is met: wants.met)
        add_event(house, pet, "the %s you set %s %s is done: %s waits in its tray" % (r["bit"], M["doing"], M["at"], a(r["gives"])))


# ---- wanting one (build.py: when = "machine"; things.better: the needs list) ----

def wanted(house, cfg, pet, key):
    """A machine is wanted by a hob that failed at what it does lately, or was offered it lately, while the house has
    none (one of each)."""
    if standing(house, key) or not reachable(house, cfg, pet, projects(cfg)[key]):   # (no stove wanted while nothing can make its fired bricks)
        return False
    t, day = house["tick"], cfg["ticks_per_day"]
    from . import spotlight
    if spotlight.on(house, key):   # SPEC-v3.6c §3: while the kiln is in the spotlight, everyone wants it built
        return True
    return t - pet.get("wants_machine", {}).get(key, LONG_AGO) < WANTED_DAYS * day or t - pet.get("offered", {}).get("machine:" + key, LONG_AGO) < OFFERED_DAYS * day


def reachable(house, cfg, pet, P):
    """Can what it takes be had: base materials, or what a process this hob knows a place for gives."""
    base = set(cfg["machine"]["materials"])
    return all(b in base or any(r.get("gives") == b and craft.places(house, cfg, pet, how) for (_, how), r in cfg["craft"]["rules"].items()) for b in P["needs"])


def toward(house, cfg, pet, rule):
    """Would failing at this lead to a machine the house has not got and could build? (wants.py weights the try up:
    baking clay by the pipe is how the kiln, and everything after it, begins.)"""
    k = rule.get("fails")
    return bool(k) and not standing(house, k) and reachable(house, cfg, pet, projects(cfg)[k])


def offers(house, cfg, pet):
    """things.better asks this: the machines the house has none of that it could build now, as (key, line). The kiln
    once a hob has failed to bake clay without one, or (18 October 2026: the chain should not wait on one failed bake)
    once anyone in the house has tried firing clay, or set out to learn how."""
    out = []
    for k, P in projects(cfg).items():
        if standing(house, k) or not reachable(house, cfg, pet, P) or (k == "kiln" and "kiln" not in pet.get("wants_machine", {}) and not firing(house)):
            continue
        out.append(("machine:" + k, "%s %s, which the house has none of: it takes %s, and a hammer" % (P["a"], k, build.some(P["needs"]))))
    return out


def firing(house):
    """Has a hob of the house tried baking clay or mud, or taken up a project to learn how clay is fired?"""
    return any(p["stage"] not in ("egg", "dead") and (any(k.split("|")[0] in ("clay", "mud", "mud brick") and k.endswith("|warm") for k in p.get("tried", {}))
               or re.search(r"\bfir(e|ed|ing)\b|\bkiln\b|\bbake", ((p.get("project") or {}).get("text") or "").lower()) and "clay" in ((p.get("project") or {}).get("text") or "").lower())
               for p in house["pets"].values())


def stood(house, cfg, pet, room, name, key):
    """build.stand calls this when a machine stands: the house's first of its kind is a banner and a line on the board."""
    from . import feats
    names = build.and_([label(house["pets"][p]) for p in room["objects"][name]["fix"]["built"]["paws"] if p in house["pets"]])
    text = "the first %s in the house: %s built it" % (key, names)
    craft.burst(house, pet, "machine", text)
    from . import spotlight
    spotlight.built(house, cfg, room, name, key)   # SPEC-v3.6c §3: something new in the house
    feats.record(house, cfg, "first", pet["id"], text, board="THE FIRST %s: %s" % (key.upper(), names.upper()), room=room["id"])


# ---- a body at a machine (body.py, `work a machine`) ----

def source(house, cfg, pet, room, bit):
    """Where a load of this bit can come from just now: its paws, the room, the vending machine's stock, or None."""
    from . import machine
    if bit in pet["carrying"]:
        return "paws"
    if any(s["bit"] == bit and s["ready"] and not s.get("on") and not s.get("machine") for s in room["spots"]):
        return "room"
    if bit in cfg["machine"]["materials"] and machine.found(house) and machine.state(house, cfg)["stock"].get(bit, 0) > KEEP:
        return "stock"
    return None


def targets(house, cfg, pet, A, near):
    """A machine here that is free, and a load it knows how to put in and can get: the one a thing being built wants
    first, then what is in its paws, then what lies about, then the stock; of those, what the house has made least of."""
    room, W = house["rooms"][pet["room"]], cfg["body"]["want"]
    if night(house) or pet["needs"]["energy"] < cfg["make"]["tired"]:
        return []
    need, n_made, known, out = needed(house), made(house), pet.get("recipes", {}), []
    for n, o in room["objects"].items():
        k = key_of(o)
        if not k or not build.sound(o):
            continue
        M = build.PROJECT[k]["machine"]
        how, tool = M["process"], cfg["craft"]["process"][M["process"]].get("tool")
        if check(house, cfg, pet, room, how) or (tool and not craft.tool_for(house, cfg, pet, tool)):
            continue
        if how == "cook":
            from . import cook
            t = cook.target(house, cfg, pet, room)
            if t:
                out.append({"what": n, "how": how, "goal": near(o["pos"]), "where": "cooking %s %s" % (t[1], M["at"]), "job": [how, t[0], "paws", t[1]], "bonus": W * t[2]})
            continue
        loads = []   # (what it knows first; what it has not tried yet after, to find out: a machine standing there is an invitation)
        for (bit, h), rule in cfg["craft"]["rules"].items():
            key = "%s|%s" % (bit, how)
            src = source(house, cfg, pet, room, bit) if h == how and rule.get("gives") and (key in known or key not in pet.get("tried", {})) else None
            if src:
                gives = [rule["gives"]] + rule.get("also", [])
                loads.append((not any(g in need for g in gives), key not in known, ("paws", "room", "stock").index(src), min(n_made[g] for g in gives), bit, src))
        if loads:
            first = min(loads)
            out.append({"what": n, "how": how, "goal": near(o["pos"]), "where": "%s %s %s" % (M["doing"], first[4], M["at"]), "job": [how, first[4], first[5], None],
                        "bonus": W * 1.5 if not first[0] else 0.0})
    return out


def finish(mind, now):
    """The load goes in: fetched from the stock first if that is where it was to come from. Returns (what it is told
    it did, or None; whether anything was done)."""
    from . import actions, machine
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    how, bit, src, dish = now["job"]
    fetched = ""
    if src == "stock":
        S = machine.state(h, cfg)
        if S["stock"].get(bit, 0) <= KEEP:
            return None, False
        S["stock"][bit] -= 1
        S["used"] = h["tick"]
        pet["carrying"].append(bit)
        moment(h, "machine", "%s took %s from the machine's stock for the %s" % (label(pet), bit, now["what"]), pet["id"], pet["room"])
        fetched = "fetched %s from the machine's stock; " % a(bit)
    act = {"type": "process", "what": bit, "how": how, **({"dish": dish} if dish else {})}
    why = actions.check(act, h, cfg, pet, mind.mem)
    if why:
        return (fetched + why if fetched else None), bool(fetched)
    text, fx, _ = actions.apply(h, cfg, pet, act, mind.mem)
    actions.bump(pet, cfg, {k: v for k, v in fx.items() if k in pet["needs"]})
    return fetched + text.replace("you ", "", 1), True


# ---- for the page (server.room_view; CONTRACT) ----

def view(house, cfg, room, name, o, v):
    """A built machine's state, for the page: v["machine"]."""
    k = key_of(o)
    if not k:
        return
    M, r, t = build.PROJECT[k]["machine"], o.get("run"), house["tick"]
    sec = cfg["clock"]["tick_seconds"]
    worn = bool(o["fix"]["built"].get("worn"))
    left = max(0, (r["done"] - t) * sec) if r else 0
    tr = Counter(s["bit"] for s in tray(room, name))
    v["machine"] = {"kind": k, "state": "worn" if worn else "working" if r else "cold", "doing": "%s %s" % (M["doing"], r["bit"]) if r else None,
                    "left": left, "makes": r["gives"] if r else None, "tray": dict(tr), "made": dict(o.get("output", {})), "runs": o.get("runs", 0),
                    "hot": bool(M.get("hot")), "glow": bool(r) or t - o.get("warm", LONG_AGO) <= cfg["ticks_per_hour"],
                    "by": o["fix"]["built"]["names"], "led": led(house, cfg, k, M, o, r, left, worn), "pot": None}
    if k == "stove":
        from . import cook
        v["machine"]["pot"] = cook.view(house, cfg, room, o)


def led(house, cfg, k, M, o, r, left, worn):
    word = M["led"]
    if worn:
        return "%s: WORN" % word
    if r:
        what = r.get("dish") or r["bit"]
        return "%s: %s %s · %d MIN" % (word, M["doing"].upper(), what.upper(), max(1, round(left / 60)))
    pot = o.get("pot") or {}
    if pot.get("servings"):
        return "%s: %s · %d SERVING%s" % (word, pot["dish"].upper(), pot["servings"], "" if pot["servings"] == 1 else "S")
    return "%s: %s" % (word, "RESTING" if night(house) else "COLD" if M.get("hot") else "STILL")


def views(house, cfg):
    """snapshot.machines: [{room, name, kind, state, led}]."""
    out = []
    for r in house["rooms"].values():
        for n, o in r["objects"].items() if r["type"] else ():
            if key_of(o):
                v = {}
                view(house, cfg, r, n, o, v)
                out.append({"room": r["id"], "name": n, "kind": v["machine"]["kind"], "state": v["machine"]["state"], "led": v["machine"]["led"]})
    return out
