"""SPEC-v4.0 §4 opinions of every hob and of the visitor, moved only by remembered causes. Switch: [opinions] on.

pet["opinions"][other_id | "visitor"] = {"liking": -10..10, "trust", "fear", "respect": 0..10, "causes": [the last 20:
{"tick", "cause", "why", "d"}], "fixed": {axis: the part from heavy causes, which does not fade}, "since": tick}.
Only `move` changes them, by a cause in opinions.toml; gossip's arithmetic is here too (talk.py decides when)."""
import tomllib

from .world import ROOT, alive, days, label, relation, rnd

DATA = tomllib.loads((ROOT / "opinions.toml").read_text())
AXES = ("liking", "trust", "fear", "respect")
RANGE = {"liking": (-10, 10), "trust": (0, 10), "fear": (0, 10), "respect": (0, 10)}
NEUTRAL = DATA["neutral"]


def on(cfg):
    return bool(cfg.get("opinions", {}).get("on"))


ON = True   # (19 October 2026) the switch as the house last ticked (`tick`): `of` has no cfg, and every gate read saved opinions while off
# ponytail: one switch for the whole process (the engine runs one house); a cfg argument on `of` if two houses ever share one


def of(pet, other_id):
    if not ON:
        return dict(NEUTRAL, causes=[])
    return (pet.get("opinions") or {}).get(other_id) or dict(NEUTRAL, causes=[])


def pid(x):
    return x if isinstance(x, str) else x["id"]


def kin(house, pet, other):
    """Family by blood: parent, child, sibling, grandparent, grandchild, or one of an egg's two parents."""
    if relation(house, pet, other) or relation(house, other, pet):
        return True
    return bool(set(pet.get("parents") or []) & set(other.get("parents") or [])) or other["id"] in (pet.get("parents") or []) \
        or pet["id"] in (other.get("parents") or [])


def entry(house, cfg, pet, other_id):
    """Its opinion of `other_id`, made at first meeting: neutral, nudged by kinship and by what its family thinks."""
    ops = pet.setdefault("opinions", {})
    if other_id in ops:
        return ops[other_id]
    ops[other_id] = dict(NEUTRAL, causes=[], fixed={}, since=house["tick"])
    other = house["pets"].get(other_id)
    if other and kin(house, pet, other):
        move(house, cfg, pet, other_id, "kin", "%s is my own family" % label(other))
    elif other:
        fam = [p for p in house["pets"].values() if p is not pet and p["stage"] != "dead" and other_id in (p.get("opinions") or {})
               and kin(house, pet, p)]
        if fam:
            d = {a: (sum(p["opinions"][other_id][a] for p in fam) / len(fam) - NEUTRAL[a]) * 0.4 for a in AXES}
            move(house, cfg, pet, other_id, "family_says", "my family's feeling about %s" % label(other), d=d)
    return ops[other_id]


def clamp(a, v):
    lo, hi = RANGE[a]
    return round(min(hi, max(lo, v)), 2)


def move(house, cfg, pet, other_id, cause, why, d=None, remember=True):
    """The one way an opinion changes: by a cause from opinions.toml (its amounts, or `d` clamped to their size).
    Records the cause; heavy ones don't fade; may leave a memory, a mood, and pride or safety. Returns the change."""
    if not on(cfg) or pet["stage"] in ("egg", "dead"):
        return None
    other_id = pid(other_id)
    if other_id == pet["id"]:
        return None
    C = DATA["causes"][cause]   # (an unknown cause is a mistake in the caller: it fails loudly, in the guarded tick)
    o = entry(house, cfg, pet, other_id)
    size = {a: abs(C.get(a, 0)) for a in AXES}
    want = {a: C.get(a, 0) for a in AXES} if d is None else {a: max(-size[a], min(size[a], d.get(a, 0))) for a in AXES}
    done = {}
    for a, v in want.items():
        if v:
            was = o[a]
            o[a] = clamp(a, was + v)
            if o[a] != was:
                done[a] = round(o[a] - was, 2)
    heavy = C.get("heavy") or C.get("memory", 0) >= 4
    if heavy:
        for a, v in done.items():
            o.setdefault("fixed", {})[a] = round(o["fixed"].get(a, 0) + v, 2)
    o["causes"] = (o["causes"] + [{"tick": house["tick"], "cause": cause, "why": why, "d": done}])[-20:]
    from . import character, memories, needs
    if remember and C.get("memory"):
        memories.add(house, cfg, pet, why, C["memory"], [other_id], cause)
    if C.get("mood"):
        character.set_mood(house, cfg, pet, C["mood"], why)
    for need in ("pride", "safety"):
        if C.get(need):
            from . import sheet
            less = cfg["sheet"]["sneer_pride"] if sheet.on(cfg) and cause == "laughed_at_me" and need == "pride" else 1.0   # (24 November 2026: a sneer in passing stings; it does not flatten)
            needs.lift(house, cfg, pet, need, C[need] * less)
    return done


def fade(house, cfg, pet, share):
    """Light feelings drift back toward neutral; the part from heavy causes stays."""
    for o in (pet.get("opinions") or {}).values():
        for a in AXES:
            rest = NEUTRAL[a] + o.get("fixed", {}).get(a, 0)
            k = share * DATA["fading"].get("small_per_day", DATA["fading"]["per_day"]) / DATA["fading"]["per_day"] if a == "liking" and -3 <= o[a] < rest else share
            o[a] = clamp(a, o[a] + (rest - o[a]) * k)


# ---- gossip (§4): talk.py decides who tells whom; the arithmetic is here ----

def say(house, cfg, teller, about_id):
    """What `teller` would say it thinks of `about_id`: (liking it says, true?). A sly hob may invent, running the other down."""
    from . import character
    real = of(teller, about_id)["liking"]
    sly = -character.trait(teller, "honest") if character.on(cfg) else 0.0
    r = rnd(house, "say", teller["id"], about_id, house["tick"])
    if sly > 0.2 and r.random() < sly * DATA["gossip"]["lie_chance"]:
        return clamp("liking", min(real, 0) - r.randint(4, 7)), False
    return real, True


def gossip(house, cfg, teller, listener, about_id, said_liking, true=True):
    """`listener` hears `teller` say what it thinks of `about_id`: its own opinion moves a little toward that, weighted by
    its trust in the teller. A lie is remembered by the house, to be found out (`tick`)."""
    if not on(cfg) or about_id in (listener["id"], teller["id"]):
        return None
    trust = of(listener, teller["id"])["trust"] / 10
    have = entry(house, cfg, listener, about_id)["liking"]
    d = {"liking": (said_liking - have) * DATA["gossip"]["pull"] * trust}
    who = "the visitor" if about_id == "visitor" else label(house["pets"][about_id]) if about_id in house["pets"] else about_id
    done = move(house, cfg, listener, about_id, "gossip", "%s told me what they think of %s" % (label(teller), who), d=d, remember=False)
    if not true:
        house["lies"] = (house.get("lies", []) + [{"tick": house["tick"], "teller": teller["id"], "listener": listener["id"],
                                                   "about": about_id, "said": said_liking}])[-100:]
    return done


def found_out(house, cfg, lie):
    """A lie found out: trust in the teller drops."""
    teller, listener = house["pets"].get(lie["teller"]), house["pets"].get(lie["listener"])
    house["lies"] = [x for x in house.get("lies", []) if x is not lie]
    if teller and listener:
        about = house["pets"].get(lie["about"])
        move(house, cfg, listener, teller["id"], "lied_to_me", "%s lied to me about %s" % (label(teller), label(about) if about else "the visitor"))


# ---- each tick ----

def tick(house, cfg):
    global ON
    ON = on(cfg)
    if not ON:
        return
    from . import bonds, memories
    memories.tick(house, cfg)
    hour = max(1, round(cfg["ticks_per_hour"]))
    if house["tick"] % hour:
        return
    pets = [p for p in alive(house) if p["stage"] != "egg"]
    for p in pets:   # first meetings: everyone in the room, and the visitor
        entry(house, cfg, p, "visitor")
        for q in pets:
            if q is not p and q["room"] == p["room"]:
                entry(house, cfg, p, q["id"])
        fade(house, cfg, p, DATA["fading"]["per_day"] / 24)
    if house["tick"] % (hour * 24) == 0:   # once a world day: lies come out
        for lie in list(house.get("lies", [])):
            r = rnd(house, "found", lie["teller"], lie["listener"], lie["tick"], house["tick"])
            if r.random() < DATA["gossip"]["found_per_day"]:
                found_out(house, cfg, lie)
            elif days(cfg, lie["tick"], house["tick"]) > 6:
                house["lies"].remove(lie)   # (never found out: it drops out of the house's reckoning)
    bonds.tick(house, cfg)
