"""The checked action set (SPEC §2): the only way a pet changes the house. Every action is checked against the
world before it happens and again when the pet gets there; what it does is decided here, not by the pet."""
import re

from . import feel, genome, life, things
from .world import (BACK, LONG_AGO, add_event, beside, dist, free_tile, generate_room, here, label, moment, power_on,
                    relation, ticks, witness)

PLACES = {"the middle": (0.5, 0.5), "the north wall": (0.5, 0.0), "the south wall": (0.5, 1.0),
          "the west wall": (0.0, 0.5), "the east wall": (1.0, 0.5)}
SOURCES = ("lived", "seen")


def norm(s):
    s = re.sub(r"\s+", " ", s.strip().lower()) if isinstance(s, str) else ""
    return re.sub(r"^(the|my|your|a|an) ", "", s)


def clean(text, limit):
    return re.sub(r"\s+", " ", str(text)).strip()[:limit]


def belief(text):
    """A belief as it is kept: at most 220 characters, ending on a whole sentence or word."""
    return life.last_sentence(clean(text, 260), 220)


def filled(v):
    return isinstance(v, str) and bool(v.strip())


def handle(house, me, other):
    """What `me` calls `other` in an action: its name, or "your mother", or "the little one"."""
    rel = relation(house, me, other)
    return other["name"] or ("your " + rel if rel else "the little one")


def place(cfg, name):
    fx, fy = PLACES[name]
    return [round(fx * (cfg["W"] - 1)), round(fy * (cfg["H"] - 1))]


def find(house, pet, name):
    """What a name in an action points at, in the room the pet is in: (kind, the thing itself) or (None, None)."""
    n, room = norm(name), house["rooms"][pet["room"]]
    if n in room["objects"]:
        return "thing", n
    for p in here(house, pet):
        if norm(handle(house, pet, p)) == n:
            return "pet", p
    for c in house["creatures"]:
        if c["room"] == room["id"] and c["kind"] == n:
            return "creature", c
    spots = [s for s in room["spots"] if s["ready"] and s["bit"] == n]
    if spots:
        return "bit", min(spots, key=lambda s: dist(s["pos"], pet["pos"]))
    eggs = [p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] == "egg"]
    if n == "egg" and eggs:
        return "egg", min(eggs, key=lambda p: dist(p["pos"], pet["pos"]))
    if n.replace(" door", "") in room["doors"]:
        return "door", n.replace(" door", "")
    if n == "visitor":
        return "visitor", None
    if "the " + n in PLACES or n == "here":
        return "place", pet["pos"] if n == "here" else None
    return None, None


def pos_of(house, cfg, pet, name):
    kind, ref = find(house, pet, name)
    room = house["rooms"][pet["room"]]
    if kind == "thing":
        return room["objects"][ref]["pos"]
    if kind in ("pet", "creature", "bit", "egg"):
        return ref["pos"]
    if kind == "door":
        return list(house["door_tiles"][ref])
    if kind == "place":
        return ref or place(cfg, "the " + norm(name))
    return None


def movable(cfg, o):
    if "made" in o:
        return not things.prop(cfg, o).get("fixed")
    return bool(o.get("fix", {}).get("movable"))


def others_things(house, pet, room):
    """Made things here that belong to another living pet."""
    return [n for n, o in things.made(room).items() if not things.free_to_change(house, pet, o)]


def changeable(house, pet, room):
    return [n for n, o in things.made(room).items() if things.free_to_change(house, pet, o) and not o["made"].get("heirloom")]


def allowed(house, cfg, pet, mem):
    """What it can do right now: what its stage has unlocked, less what the moment rules out. Limits are met in
    the world, not listed as numbers (§3.2): no room to carry, nobody here to give to, the house is full."""
    room = house["rooms"][pet["room"]]
    others, crs = here(house, pet, awake=True), [c for c in house["creatures"] if c["room"] == room["id"]]
    bits = any(s["ready"] for s in room["spots"])
    mine, free = things.mine(house, pet, room), changeable(house, pet, room)
    kids = [c for c in pet["children"] if house["pets"].get(c, {}).get("stage", "dead") != "dead"]
    eggs = any(p["room"] == room["id"] and p["stage"] == "egg" for p in house["pets"].values())
    can = {
        "gather": bits and len(pet["carrying"]) < cfg["make"]["carry"], "drop": bool(pet["carrying"]),
        "make": (bool(pet["carrying"]) or bits) and len(things.made(room)) < cfg["make"]["crowded"],
        "unmake": bool(free), "combine": len(free) > 1, "teach": bool(mine),
        "give": bool(others or crs) and bool(pet["carrying"] or mine or bits),
        "show": bool(others) and bool(room["objects"]), "follow": bool(others or crs), "nuzzle": bool(others) or eggs,
        "accept": bool(pet["offers"]), "take": bool(others_things(house, pet, room)), "chase": bool(crs),
        "tell": bool(others), "lay_egg": life.can_lay(house, cfg, pet) is None,
        "bequeath": bool(kids) and bool(mine), "revise_belief": bool(mem.active()),
        "write_belief": True, "arrange": any(movable(cfg, o) for o in room["objects"].values()) or eggs,
    }
    return [a for a in life.actions_of(pet["stage"]) if can.get(a, True)]


def words(a):
    t = a.get("type", "?")
    obj = a.get("target") or a.get("what") or a.get("to") or a.get("who") or a.get("object") or a.get("door") or ""
    if t == "make":
        obj = (a.get("recipe") or {}).get("name", "")
    return ("%s %s" % (t.replace("_", " "), obj)).strip()


# ---- checking ----

def check(a, house, cfg, pet, mem):
    """None if the action can happen now, else why not, in words the pet can use."""
    t, room = a.get("type"), house["rooms"][pet["room"]]
    if t not in life.actions_of(pet["stage"]):
        return "you cannot do that yet"
    kind, ref = find(house, pet, a.get("target") or a.get("what") or a.get("who") or a.get("object") or a.get("to"))
    o = room["objects"].get(ref) if kind == "thing" else None
    if t in ("observe", "rest", "speak"):
        return None if t != "speak" or filled(a.get("text")) else "nothing to say"
    if t == "look":
        return None if kind else "that is not here"
    if t == "move":
        return None if kind else "that is not here"
    if t == "go":
        d = norm(a.get("door")).replace(" door", "")
        if d not in room["doors"]:
            return "there is no door that way"
        return "that door is stuck shut" if house["shut"].get("%s|%s" % (room["id"], d), LONG_AGO) > house["tick"] else None
    if t == "use":
        return None if o is not None else "that is not here"
    if t == "gather":
        if len(pet["carrying"]) >= cfg["make"]["carry"]:
            return "you cannot carry any more"
        return None if kind == "bit" else "there is none of that lying here"
    if t == "drop":
        return None if norm(a.get("what")) in pet["carrying"] else "you are not carrying that"
    if t == "make":
        near = a.get("near")
        if filled(near) and norm(near) != "here" and find(house, pet, near)[0] is None:
            return "that is not here"
        return things.check_make(a, house, cfg, pet)
    if t == "unmake":
        if o is None or "made" not in o:
            return "that is not a made thing here"
        if o["made"].get("heirloom"):
            return "an heirloom cannot be taken apart"
        return None if things.free_to_change(house, pet, o) else "that belongs to someone else"
    if t == "arrange":
        if kind == "egg":
            ok = ref["parent"] == pet["id"]
        else:
            ok = o is not None and movable(cfg, o)
        if not ok:
            return "that cannot be moved"
        return None if find(house, pet, a.get("near"))[0] else "there is no such place to put it"
    if t == "combine":
        return things.check_combine(a, house, cfg, pet, norm)
    if t == "paint":
        return None if a.get("wall") in things.COLORS and a.get("floor") in things.COLORS else "unknown color"
    if t == "teach":
        return things.check_teach(a, house, cfg, pet, norm)
    if t == "give":
        what, (tk, tr) = norm(a.get("what")), find(house, pet, a.get("to"))
        if tk not in ("pet", "creature"):
            return "there is nobody like that here"
        if tk == "pet" and tr["sleep"]:
            return "they are asleep"
        if what in pet["carrying"]:
            return None
        if tk == "pet" and what in things.mine(house, pet, room):
            return None
        if find(house, pet, what)[0] == "bit" and len(pet["carrying"]) < cfg["make"]["carry"]:
            return None   # something lying here: it picks it up to give
        return "you can only give what you carry or a thing of yours that is here"
    if t == "show":
        tk, tr = find(house, pet, a.get("to"))
        if norm(a.get("what")) not in room["objects"]:
            return "that is not here"
        return None if tk == "pet" and not tr["sleep"] else "there is nobody awake like that here"
    if t == "follow":
        return None if kind in ("pet", "creature") else "there is nobody like that here"
    if t == "nuzzle":
        return None if kind in ("pet", "egg") else "there is nobody like that here"
    if t == "accept":
        return None if offer_from(house, pet, a.get("from")) else "nothing is being offered to you by them"
    if t == "take":
        if o is None or "made" not in o or things.free_to_change(house, pet, o):
            return "there is nothing of someone else's by that name here"
        return "an heirloom cannot be taken" if o["made"].get("heirloom") else None
    if t == "chase":
        return None if kind == "creature" else "there is no such creature here"
    if t == "tell":
        if not filled(a.get("text")):
            return "nothing to tell"
        return None if kind == "pet" and not ref["sleep"] else "there is nobody awake like that here"
    if t == "lay_egg":
        return life.can_lay(house, cfg, pet) or (None if filled(a.get("message")) else "the egg needs your words")
    if t == "bequeath":
        return life.check_bequeath(a, house, cfg, pet, norm)
    if t == "write_belief":
        if not filled(a.get("statement")):
            return "nothing to write"
        return None if len(mem.active()) < cfg["beliefs"]["max_active"] else "you hold too many beliefs; revise or discard one first"
    if t == "revise_belief":
        return None if mem.is_active(a.get("id")) and filled(a.get("statement")) else "there is no such belief"
    return "unknown action"


def check_plan(turn, pet):
    """Shape only: an intention of steps. Whether each step is possible is checked when it is carried out."""
    if not isinstance(turn, dict) or not filled(turn.get("intention")) or not filled(turn.get("expect")):
        return "the reply was not an intention"
    steps = turn.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 5 or not all(isinstance(s, dict) and filled(s.get("type")) for s in steps):
        return "the reply had no usable steps"
    return None


def offer_from(house, pet, name):
    n = norm(name)
    for off in pet["offers"]:
        giver = house["pets"].get(off["from"])
        if giver and giver["stage"] != "dead" and giver["room"] == pet["room"] and norm(handle(house, pet, giver)) == n:
            return off
    return None


def destination(house, cfg, pet, a):
    """The tile it walks to before the step happens, or None if it happens where it stands."""
    t = a["type"]
    name = {"use": "target", "unmake": "target", "teach": "target", "take": "what", "gather": "what", "move": "to",
            "give": "to", "nuzzle": "who", "tell": "to", "chase": "who", "accept": "from", "arrange": "object",
            "combine": "a", "bequeath": "what", "make": "near"}.get(t)
    if t == "go":
        d = norm(a.get("door")).replace(" door", "")
        return list(house["door_tiles"][d]) if d in house["rooms"][pet["room"]]["doors"] else None
    if not name or not filled(a.get(name)) or norm(a[name]) == "here":
        return None
    at = pos_of(house, cfg, pet, a[name])
    if at is None:
        return None
    if find(house, pet, a[name])[0] in ("place", "door"):
        return at
    return None if dist(pet["pos"], at) <= 1 else beside(cfg, at, pet["pos"])


# ---- doing ----

def describe_thing(house, cfg, pet, name):
    room = house["rooms"][pet["room"]]
    o = room["objects"][name]
    if "memorial" in o:
        return o["memorial"]["text"]
    if "made" in o:
        m = o["made"]
        parts = ", ".join("a %s %s %s" % (["small", "medium", "large"][p["size"] - 1], p["color"], p["shape"]) for p in m["recipe"]["parts"])
        worn = "; it is damp" * bool(m.get("damp")) + "; it is dusty" * bool(m.get("dusty")) + "; something has been eating at it" * bool(m.get("eaten"))
        heir = m.get("heirloom")
        return "%s (%s): %s; it is %s; made for: %s%s%s" % (
            name, things.whose(house, pet, o), parts, m["recipe"]["material"], m["recipe"]["purpose"], worn,
            "; it is an heirloom" if heir else "")
    fix, state = o.get("fix", {}), o.get("state")
    hint = ("a light" if "light" in fix else "something to eat from" if "meal" in fix else "a place to rest" if "rest" in fix
            else "soft to lie on" if "soft" in fix else "something to play with" if "toy" in fix
            else "something growing" if fix.get("plant") else "you could see yourself in it" if fix.get("mirror")
            else "you can see outside through it" if fix.get("window") else "water; things put in it drift off" if "water" in fix
            else "a warm patch of light on the floor" if fix.get("sun")
            else "it can be set " + " or ".join(fix["states"]) if "states" in fix else "a bench to work at" if fix.get("bench") else "it is just there")
    if fix.get("plant"):
        state = "ripe" if o["state"] == "ripe" else "nearly ripe" if o["grow"] > 0.7 else "growing"
    return "%s%s: %s" % (name, " (%s)" % state if state else "", hint)


def apply(house, cfg, pet, a, mem):
    """Carry out an action that passed its check. Returns (what the pet is told, need effects, novelty key).
    Effects may carry "tags" (hidden physics that fired) and "scale" (a room's rule on what it is worth)."""
    t, room, E = a["type"], house["rooms"][pet["room"]], cfg["effects"]
    name = label(pet)
    if t == "observe":
        return "you watched the room for a while", dict(E["observe"]), "observe " + room["type"]
    if t == "rest":
        return "you rested", {"energy": E["rest_per_10s"]}, None
    if t == "move":
        return "you went over to " + norm(a["to"]), {}, None
    if t == "look":
        return look(house, cfg, pet, a)
    if t == "go":
        return go(house, cfg, pet, norm(a["door"]).replace(" door", ""))
    if t == "speak":
        return speak(house, cfg, pet, a, mem)
    if t == "use":
        return use(house, cfg, pet, norm(a["target"]))
    if t == "gather":
        spot = find(house, pet, a["what"])[1]
        pet["carrying"].append(spot["bit"])
        if spot["loose"]:
            room["spots"].remove(spot)
        else:
            spot["ready"], spot["back"] = False, house["tick"] + round(cfg["house"]["rooms"][room["type"]]["regrow_hours"] * cfg["ticks_per_hour"])
        can = cfg["house"]["bits"][spot["bit"]]["can"]
        return "you picked up some %s; it feels like it could become something %s" % (spot["bit"], " or ".join(can)), dict(E["gather"]), "gather " + spot["bit"]
    if t == "drop":
        bit = norm(a["what"])
        pet["carrying"].remove(bit)
        things.drop_bits(house, cfg, room, pet["pos"], [bit])
        return "you put the %s down" % bit, {}, None
    if t == "make":
        return things.make(house, cfg, pet, a, clean)
    if t == "unmake":
        return things.unmake(house, cfg, pet, norm(a["target"]))
    if t == "arrange":
        kind, ref = find(house, pet, a["object"])
        to = pos_of(house, cfg, pet, a["near"])
        if kind == "egg":
            ref["pos"] = free_tile(house, cfg, room, to)
            return "you moved the egg", {}, None
        o = room["objects"][ref]
        o["pos"] = free_tile(house, cfg, room, to, ref)
        return "you moved %s over by %s" % (ref, norm(a["near"])), {}, "arrange"
    if t == "combine":
        return things.combine(house, cfg, pet, a, clean, norm)
    if t == "paint":
        room["paint"] = {"wall": a["wall"], "floor": a["floor"]}
        moment(house, "painted", "%s painted %s: %s walls, %s floor" % (name, room["name"], a["wall"], a["floor"]), pet["id"], room["id"])
        return "you painted the walls %s and the floor %s" % (a["wall"], a["floor"]), {"energy": -2.0}, "paint"
    if t == "teach":
        return things.teach(house, pet, a, norm(a["target"]))
    if t == "give":
        return give(house, cfg, pet, a)
    if t == "show":
        other, what = find(house, pet, a["to"])[1], norm(a["what"])
        add_event(house, other, "%s showed you the %s: %s" % (handle(house, other, pet), what, describe_thing(house, cfg, other, what)))
        other["news"].append("spoken")
        bump(other, cfg, {"curiosity": E["show"]["curiosity"], "company": 1.0})
        return "you showed the %s to %s" % (what, handle(house, pet, other)), {"company": 1.0}, "show"
    if t == "follow":
        kind, ref = find(house, pet, a["who"])
        pet["following"] = ref["id"]
        return "you kept close to %s" % (handle(house, pet, ref) if kind == "pet" else "the " + ref["kind"]), {}, "follow " + (ref.get("kind") or "pet")
    if t == "nuzzle":
        kind, other = find(house, pet, a["who"])
        if kind == "egg":
            return "you pressed yourself against the egg; it is warm", {"company": 3.0, "comfort": 1.0}, "nuzzle egg"
        offer(house, cfg, pet, other, {"kind": "nuzzle"})
        return "you leaned toward %s; it is up to them now" % handle(house, pet, other), {}, None
    if t == "accept":
        return accept(house, cfg, pet, offer_from(house, pet, a["from"]))
    if t == "take":
        what = norm(a["what"])
        o = room["objects"][what]
        owner = house["pets"][o["made"]["owner"]]
        o["made"]["owner"], o["pos"] = pet["id"], free_tile(house, cfg, room, pet["pos"], what)
        if owner["room"] == room["id"] and not owner["sleep"]:
            add_event(house, owner, "%s took your %s" % (handle(house, owner, pet), what))
            owner["news"].append("spoken")
        else:
            owner.setdefault("lost", []).append({"name": what, "by": pet["id"], "room": room["id"]})
        moment(house, "took", "%s took the %s from %s" % (name, what, label(owner)), pet["id"], room["id"])
        return "you took the %s; it is yours now" % what, {}, "take"
    if t == "chase":
        from . import director
        c = find(house, pet, a["who"])[1]
        text = director.chased(house, cfg, c, pet)
        return text, dict(E["chase"]), "chase " + c["kind"]
    if t == "tell":
        other, text = find(house, pet, a["to"])[1], life.last_sentence(clean(a["text"], 440), 400)
        other["told"].insert(0, {"by": pet["id"], "who": handle(house, other, pet), "kind": "tell", "text": text, "tick": house["tick"]})
        del other["told"][6:]
        keep_parent_word(other)
        add_event(house, other, '%s told you something to keep: "%s"' % (handle(house, other, pet), text))
        other["news"].append("spoken")
        bump(other, cfg, {"company": E["spoken_to"]})
        house.setdefault("said", []).append({"tick": house["tick"], "from": pet["id"], "to": other["id"], "kind": "tell", "text": text})
        moment(house, "told", "%s told %s something to keep" % (name, label(other)), pet["id"], room["id"])
        return "you told %s what you wanted them to keep" % handle(house, pet, other), {"company": 2.0}, "tell"
    if t == "lay_egg":
        return life.lay_egg(house, cfg, pet, a, clean)
    if t == "bequeath":
        return life.bequeath(house, cfg, pet, a, norm)
    if t == "write_belief":
        source = a.get("source") if a.get("source") in SOURCES or str(a.get("source", "")).startswith("told by ") else "lived"
        bid = mem.write(belief(a["statement"]), house["tick"], source)
        return "you wrote belief " + bid, {}, None
    if t == "revise_belief":
        text = belief(a["statement"])
        if text.lower() == "discard":
            moment(house, "discarded", "%s gave up a belief: %s" % (name, next(b["statement"] for b in mem.beliefs if b["id"] == a["id"])), pet["id"], room["id"])
        mem.revise(a["id"], text, house["tick"])
        return "you %s belief %s" % ("discarded" if text.lower() == "discard" else "revised", a["id"]), {}, None
    raise ValueError(t)


def keep_parent_word(pet):
    """A parent's message and last words are never pushed out by what others tell it (§5.2: for life)."""
    pet["told"].sort(key=lambda m: m["kind"] == "tell")


def bump(pet, cfg, fx):
    for n, v in fx.items():
        pet["needs"][n] = min(100.0, max(0.0, pet["needs"][n] + v))


def look(house, cfg, pet, a):
    kind, ref = find(house, pet, a["target"])
    room, fx = house["rooms"][pet["room"]], dict(cfg["effects"]["look"])
    if room["type"] == "storeroom" and not things.light_on(house, cfg, room):
        fx["scale"], fx["tags"] = things.room_rule(cfg, room, "dark", 0.5), ["storeroom"]
    if kind == "thing":
        o = room["objects"][ref]
        if o.get("fix", {}).get("mirror"):
            return "in the mirror you see yourself: " + genome.describe(pet["genome"]), fx, "look mirror"
        key = "look a %s thing" % o["made"]["recipe"]["material"] if "made" in o else "look " + ref
        return "you looked at " + describe_thing(house, cfg, pet, ref), fx, key
    if kind == "pet":
        return "you looked at %s: %s; seems %s" % (handle(house, pet, ref), genome.describe(ref["genome"]), feel.seems(ref)), fx, "look pet " + ref["id"]
    if kind == "creature":
        pet["met"][ref["kind"]] = pet["met"].get(ref["kind"], 0) + 1
        return "you watched the %s: %s" % (ref["kind"], ref["doing"]), fx, "look " + ref["kind"]
    if kind == "bit":
        return "you looked at the %s; something made from it could be %s" % (ref["bit"], " or ".join(cfg["house"]["bits"][ref["bit"]]["can"])), fx, "look " + ref["bit"]
    if kind == "egg":
        mine = ref["parent"] == pet["id"]
        return "you looked at %s egg; now and then something moves inside it" % ("your" if mine else "the"), fx, "look egg"
    if kind == "door":
        to = house["rooms"][room["doors"][ref]]
        known = to["id"] in pet["rooms"]
        return "you looked at the %s door; %s" % (ref, "it leads to " + to["name"] if known else "you have not been through it"), fx, "look door " + ref
    if kind == "visitor":
        near = (house["tick"] - house["visitor_last"]) * cfg["clock"]["tick_seconds"] <= 60 and house.get("visitor_room") == room["id"]
        return "you looked up; " + ("something big is close, watching" if near else "there is no one there"), fx, "look visitor"
    return "you looked at " + norm(a["target"]), fx, None


def go(house, cfg, pet, d):
    """Through a door. What is behind one is decided the first time anyone goes through (§6.1)."""
    room = house["rooms"][pet["room"]]
    to = house["rooms"][room["doors"][d]]
    fresh = not to["type"]
    if fresh:
        generate_room(house, cfg, to["id"], by=pet["id"])
        moment(house, "room", "%s found %s" % (label(pet), to["name"]), pet["id"], to["id"])
    witness(house, pet, "%s went out through the %s door" % (label(pet), d))
    first = to["id"] not in pet["rooms"]
    pet["room"], pet["pos"] = to["id"], list(house["door_tiles"][BACK[d]])
    pet["rooms"][to["id"]] = house["tick"]
    pet["scent"] = {}
    witness(house, pet, "%s came in through the %s door" % (label(pet), BACK[d]))
    pet["news"].append("arrived")
    for lost in [l for l in pet.get("lost", []) if l["room"] == to["id"]]:
        taker = house["pets"].get(lost["by"])
        add_event(house, pet, "your %s is gone%s" % (lost["name"], "; %s has it" % handle(house, pet, taker) if taker else ""))
        pet["lost"].remove(lost)
    if first and not fresh:
        moment(house, "entered", "%s went into %s for the first time" % (label(pet), to["name"]), pet["id"], to["id"])
    spec = cfg["house"]["rooms"][to["type"]]
    text = "you went through the %s door into %s: %s" % (d, to["name"], spec["feel"]) if first else "you went through the %s door into %s" % (d, to["name"])
    return text, {"curiosity": cfg["effects"]["new_room"]} if first else {}, "go " + to["type"]


def speak(house, cfg, pet, a, mem):
    text, room = clean(a["text"], 160), house["rooms"][pet["room"]]
    kind, other = find(house, pet, a.get("to")) if filled(a.get("to")) else (None, None)
    pet["said"] = {"text": text, "tick": house["tick"], "to": other["id"] if kind == "pet" else "visitor" if kind == "visitor" else None}
    rec = {"tick": house["tick"], "from": pet["id"], "to": pet["said"]["to"], "kind": "speak", "text": text}
    for p in here(house, pet, awake=True):
        if kind == "pet" and p is other:
            p["inbox"].append('%s said to you: "%s"' % (handle(house, p, pet), text))
            p["news"].append("spoken")
            bump(p, cfg, {"company": cfg["effects"]["spoken_to"]})
            if (house["tick"] - pet["heard"].get(p["id"], LONG_AGO)) * cfg["clock"]["tick_seconds"] <= cfg["effects"]["reply_seconds"]:
                rec["reply"] = True               # it is answering something they said to it not long ago
                del pet["heard"][p["id"]]
            p["heard"][pet["id"]] = house["tick"]
        else:
            add_event(house, p, '%s said%s: "%s"' % (handle(house, p, pet), " to " + handle(house, p, other) if kind == "pet" else "", text))
    house.setdefault("said", []).append(rec)
    if not pet.get("spoke"):
        pet["spoke"] = True
        moment(house, "words", '%s spoke for the first time: "%s"' % (label(pet), text), pet["id"], room["id"])
    name = re.search(r"\bmy name is ([A-Za-z][\w'-]{0,15})", text, re.I)
    if name and (not pet["name"] or name.group(1).strip().lower() == pet.get("called", "").lower()):
        pet["name"] = name.group(1).strip()
        mem.update_self(name=pet["name"], named_at=house["tick"])
        moment(house, "named", "the little one named itself " + pet["name"], pet["id"], room["id"])
    fx = dict(cfg["effects"]["speak"])
    if kind == "pet":
        fx["company"] = 2.0
    return 'you said%s: "%s"' % (" to " + handle(house, pet, other) if kind == "pet" else "", text), fx, "speak"


def use(house, cfg, pet, name):
    room, E = house["rooms"][pet["room"]], cfg["effects"]
    o = room["objects"][name]
    if "memorial" in o:
        kin = house["pets"].get(o["memorial"]["pet"])
        own = bool(kin) and (relation(house, pet, kin) is not None)
        return "you touched the stone; " + o["memorial"]["text"], dict(cfg["effects"]["stone"]) if own else {}, "use memorial"
    if "made" in o:
        text, fx, key = things.use(house, cfg, pet, name)
        if things.prop(cfg, o).get("loud") and room["type"] == "music":
            room["sounding_until"] = house["tick"] + ticks(cfg, 90)
        if things.prop(cfg, o).get("food") and (house["tick"] - pet.get("prev_eat", LONG_AGO)) * cfg["clock"]["tick_seconds"] <= E["double_feed_seconds"]:
            fx = {"comfort": cfg["materials"]["rules"]["double_feed"], "tags": ["double_feed"]}
        if things.prop(cfg, o).get("loud"):
            from . import director
            director.startle(house, cfg, room, pet)
        return text, fx, key
    fix = o.get("fix", {})
    if "light" in fix:
        if not power_on(house):
            return "you tried the %s; nothing happens, it stays dark" % name, {}, None
        o["state"] = "off" if o["state"] == "on" else "on"
        return "you switched the %s %s" % (name, o["state"]), {}, "use " + name
    if "states" in fix:
        o["state"] = fix["states"][(fix["states"].index(o["state"]) + 1) % len(fix["states"])]
        return "the %s is now %s" % (name, o["state"]), {}, "use " + name
    if fix.get("window"):
        o["state"] = "open" if o["state"] == "closed" else "closed"
        return "you pushed the %s %s" % (name, o["state"]), {}, "use " + name
    if "meal" in fix or (fix.get("plant") and o["state"] == "ripe"):
        if "meal" in fix:
            if not o["servings"]:
                return "the %s is empty" % name, {}, None
            o["servings"] -= 1
            o["state"] = "empty" if not o["servings"] else "half" if o["servings"] < fix["meal"] else "full"
            fx = dict(E["eat"])
        else:
            o["state"], o["grow"] = "growing", 0.0
            fx = dict(E["ripe"])
        soon = (house["tick"] - pet.get("last_eat", LONG_AGO)) * cfg["clock"]["tick_seconds"] <= E["double_feed_seconds"]
        pet["prev_eat"], pet["last_eat"] = pet.get("last_eat", LONG_AGO), house["tick"]
        if soon:   # the v2 rule: a second meal on top of the first sits badly
            return "you ate from the %s; it sits heavy on top of the last meal" % name, {"comfort": cfg["materials"]["rules"]["double_feed"], "tags": ["double_feed"]}, "eat"
        return "you ate from the %s" % name, fx, "eat"
    if fix.get("plant"):
        return "the %s is not ready to eat yet" % name, {}, "use " + name
    if "soft" in fix:
        return "you settled into the %s" % name, {"comfort": fix["soft"]}, "use " + name
    if "toy" in fix:
        if fix.get("loud"):
            from . import director
            room["sounding_until"] = house["tick"] + ticks(cfg, 90)
            director.startle(house, cfg, room, pet)
        return "you played with the %s" % name, {"curiosity": fix["toy"], "energy": -0.5}, "use " + name
    if "rest" in fix:
        return "you lay on the %s a moment" % name, {"energy": fix["rest"] * 1.5}, "use " + name
    if fix.get("mirror"):
        return "in the mirror you see yourself: " + genome.describe(pet["genome"]), {}, "look mirror"
    return "you tried to use the %s; nothing came of it" % name, {}, None


def offer(house, cfg, pet, other, what):
    other["offers"] = [o for o in other["offers"] if not (o["from"] == pet["id"] and o["kind"] == what["kind"])]
    other["offers"].append(dict(what, **{"from": pet["id"], "tick": house["tick"]}))
    other["news"].append("spoken")


def give(house, cfg, pet, a):
    what, (kind, other) = norm(a["what"]), find(house, pet, a["to"])
    room = house["rooms"][pet["room"]]
    if what not in pet["carrying"] and what not in things.mine(house, pet, room):   # a bit lying here is picked up on the way
        spot = find(house, pet, what)[1]
        pet["carrying"].append(spot["bit"])
        if spot["loose"]:
            room["spots"].remove(spot)
        else:
            spot["ready"], spot["back"] = False, house["tick"] + round(cfg["house"]["rooms"][room["type"]]["regrow_hours"] * cfg["ticks_per_hour"])
    if kind == "creature":
        from . import director
        pet["carrying"].remove(what)
        return director.fed(house, cfg, other, pet, what), dict(cfg["effects"]["feed_creature"]), "feed " + other["kind"]
    offer(house, cfg, pet, other, {"kind": "give", "what": what, "bit": what in pet["carrying"]})
    return "you held out the %s to %s; it is up to them now" % (what, handle(house, pet, other)), {}, None


def accept(house, cfg, pet, off):
    giver, room, E = house["pets"][off["from"]], house["rooms"][pet["room"]], cfg["effects"]
    pet["offers"].remove(off)
    rec = {"tick": house["tick"], "from": giver["id"], "to": pet["id"], "kind": off["kind"], "text": off.get("what", ""), "reply": True}
    if off["kind"] == "nuzzle":
        bump(giver, cfg, E["nuzzle"])
        add_event(house, giver, "%s leaned back against you" % handle(house, giver, pet))
        giver["news"].append("event")
        house.setdefault("said", []).append(rec)
        moment(house, "nuzzle", "%s and %s nuzzled" % (label(giver), label(pet)), pet["id"], room["id"])
        return "you leaned against %s" % handle(house, pet, giver), dict(E["nuzzle"]), "nuzzle"
    what = off["what"]
    if off["bit"]:
        if what not in giver["carrying"]:
            return "%s no longer has the %s" % (handle(house, pet, giver), what), {}, None
        giver["carrying"].remove(what)
        if len(pet["carrying"]) < cfg["make"]["carry"]:
            pet["carrying"].append(what)
        else:
            things.drop_bits(house, cfg, room, pet["pos"], [what])
    else:
        o = room["objects"].get(what)
        if not o or o.get("made", {}).get("owner") != giver["id"]:
            return "the %s is no longer %s's to give" % (what, handle(house, pet, giver)), {}, None
        o["made"]["owner"], o["pos"] = pet["id"], free_tile(house, cfg, room, pet["pos"], what)
    add_event(house, giver, "%s took the %s you offered" % (handle(house, giver, pet), what))
    giver["news"].append("event")
    bump(giver, cfg, {"company": 3.0})
    house.setdefault("said", []).append(rec)
    moment(house, "gift", "%s gave %s %s" % (label(giver), label(pet), ("some " if off["bit"] else "the ") + what), pet["id"], room["id"])
    return "you took the %s from %s" % (what, handle(house, pet, giver)), {"company": 3.0}, "gift"


def lapse(house, cfg, pet):
    """Offers nobody took fade, and the one who offered feels it."""
    for off in [o for o in pet["offers"] if (house["tick"] - o["tick"]) * cfg["clock"]["tick_seconds"] > cfg["effects"]["offer_seconds"]]:
        pet["offers"].remove(off)
        giver = house["pets"].get(off["from"])
        if giver and giver["stage"] != "dead":
            add_event(house, giver, "%s did not %s" % (handle(house, giver, pet), "lean back" if off["kind"] == "nuzzle" else "take the %s" % off["what"]))
            house.setdefault("said", []).append({"tick": house["tick"], "from": giver["id"], "to": pet["id"], "kind": off["kind"] + " ignored", "text": off.get("what", "")})


# ---- the visitor (§7.5): acts only in the room being looked at ----

def visit(house, cfg, cmd):
    """What the visitor did. Returns an error string, or None."""
    rid, t = cmd.get("room"), cmd.get("type")
    room = house["rooms"].get(rid)
    if not room or not room["type"]:
        return "no such room"
    house["visitor_last"], house["visitor_room"] = house["tick"], rid
    pets = [p for p in house["pets"].values() if p["room"] == rid and p["stage"] not in ("egg", "dead")]

    def tell(text, company=0.0):
        for p in pets:
            if not p["sleep"]:
                p["inbox"].append(text)
                p["news"].append("visitor")
                bump(p, cfg, {"company": company})

    if t == "feed":
        meals = [o for o in room["objects"].values() if "meal" in o.get("fix", {})]
        if not meals:
            return "there is nothing to fill in this room"
        for o in meals:
            o["servings"], o["state"] = o["fix"]["meal"], "full"
        tell("the visitor filled the bowl", 1.0)
    elif t == "talk":
        if not filled(cmd.get("text")):
            return "nothing to say"
        tell('the visitor said: "%s"' % clean(cmd["text"], 200), cfg["effects"]["visitor_talk"])
    elif t == "give":
        bit = cmd.get("bit")
        if bit not in cfg["house"]["bits"]:
            return "unknown bit"
        things.drop_bits(house, cfg, room, [cfg["W"] // 2, cfg["H"] // 2], [bit])
        tell("the visitor left some %s on the floor" % bit, 1.0)
    elif t == "place":
        o, tile = room["objects"].get(cmd.get("object")), cmd.get("tile")
        from .world import in_room
        if not o or "memorial" in o or not in_room(cfg, tile):
            return "cannot place that there"
        o["pos"] = free_tile(house, cfg, room, tile, cmd["object"])
        tell("the visitor moved the " + cmd["object"])
    elif t == "poke":
        p = house["pets"].get(cmd.get("pet"))
        if not p or p["room"] != rid or p["stage"] in ("egg", "dead"):
            return "no such pet here"
        p["inbox"].append("the visitor poked you")
        p["news"].append("visitor")
    elif t == "window":
        wins = [o for o in room["objects"].values() if o.get("fix", {}).get("window")]
        if not wins:
            return "this room has no window"
        for o in wins:
            o["state"] = "open" if o["state"] == "closed" else "closed"
        tell("the visitor pushed the window " + wins[0]["state"])
    elif t == "name":
        new = clean(cmd.get("name", ""), 16)
        if not new:
            return "no name"
        p = house["pets"].get(cmd.get("pet"))
        if p and p["room"] == rid and p["stage"] not in ("egg", "dead"):
            p["inbox"].append('the visitor calls you %s (say "my name is %s" if you want the name)' % (new, new) if not p["name"]
                              else "the visitor calls you %s" % new)
            p["news"].append("visitor")
            p["called"] = new
        elif cmd.get("object") in things.made(room):
            room["objects"][cmd["object"]]["made"]["called"] = new
            tell("the visitor calls the %s '%s'" % (cmd["object"], new))
        else:
            return "nothing here to name"
    else:
        return "unknown visitor action"
    return None
