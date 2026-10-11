"""The checked action set (SPEC §2): the only way a pet changes the house. Every action is checked against the
world before it happens and again when the pet gets there; what it does is decided here, not by the pet."""
import re

from . import book, feel, genome, life, order, songs, things, walls
from .world import (BACK, LONG_AGO, add_event, arrived, beside, dist, family, free_tile, generate_room, here, knows, label, moment,
                    power_on, relation, ticks, witness)

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
    if not knows(me, other):   # of the other family, and not yet someone it knows (SPEC-v3.1 §7.2)
        return "a stranger"
    rel = relation(house, me, other)
    return (other["name"] or ("your " + rel if rel else label(other))) + (", of the other family" if family(me) != family(other) else "")


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
        if c["room"] == room["id"] and n in (c["kind"], (c.get("name") or "").lower()):
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


def heirlooms(house, pet, room):
    """Things here that were left to this pet (§5.3). They are still marked as the giver's, and can be left on."""
    return [n for n, o in things.made(room).items() if pet["id"] in (o["made"].get("heirloom") or {}).get("to", [])]


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
    pets_of_mine = [c for c in house["creatures"] if c.get("tame") == pet["id"]]
    can = {
        "gather": bits and len(pet["carrying"]) < cfg["make"]["carry"], "drop": bool(pet["carrying"]),
        "make": (bool(pet["carrying"]) or bits) and len(things.on_floor(room)) < cfg["make"]["crowded"],
        "unmake": bool(free), "combine": len(free) > 1, "teach": bool(mine),
        "give": bool(others or crs) and bool(pet["carrying"] or mine or bits),
        "show": bool(others) and bool(room["objects"]), "follow": bool(others or crs),
        # one already close to someone feels no need to: close by how it feels, or because they leaned together not long ago
        "nuzzle": (feel.level(pet, "company") >= 1 and any(not leaned(house, cfg, pet, o) for o in others)) or eggs,
        "accept": bool(pet["offers"]), "take": bool(others_things(house, pet, room)), "chase": bool(crs),
        "tell": bool(others), "lay_egg": life.can_lay(house, cfg, pet) is None,
        "bequeath": bool(kids) and bool(mine or heirlooms(house, pet, room) or pet.get("songs")), "revise_belief": bool(mem.active()),
        # SPEC-v3.1: each appears only when it could be done now (§8)
        "write": walls.tool(cfg, pet) is not None, "scrub": bool(walls.marks(room)),
        "sing": bool(pet.get("songs")), "teach_song": bool(pet.get("songs")) and bool(others),
        "call": any(c["room"] != room["id"] or dist(c["pos"], pet["pos"]) > 2 for c in pets_of_mine),
        "name": bool(nameable(house, pet)),
        "ask_book": any(o.get("fix", {}).get("book") for o in room["objects"].values()) and book.check_ask({"question": "?"}, house, cfg, pet, filled) is None,
        "write_belief": True, "arrange": any(movable(cfg, o) for o in room["objects"].values()) or eggs,
    }
    # SPEC-v3.3 §2.2: keeping things. Open to any pet old enough to arrange things.
    movable_things = [n for n, o in things.made(room).items() if order.may_move(house, pet, o)]
    can["put_away"] = any(k > 0 for k in order.stores(cfg, room).values()) and any(not room["objects"][n].get("on") and not order.cap(cfg, room["objects"][n]) for n in movable_things)
    can["take_out"] = any(room["objects"][n].get("on") for n in movable_things)
    can["hang"] = bool(things.wall_slot(house, room)) and any(order.can_hang(cfg, room["objects"][n]) for n in movable_things)
    extra = [a for a in ("put_away", "take_out", "hang") if "arrange" in life.unlocked(house, pet["stage"])] + (["take_name"] if offered(pet) else [])
    if offered(pet):   # only while the visitor has offered it a name it has not taken
        can["take_name"] = True
    return [a for a in life.unlocked(house, pet["stage"]) + extra if can.get(a, True)]


# SPEC-v3.3 §1: what the body does by itself. The mind is no longer offered these; it sets a focus instead.
BODY_ONLY = ("observe", "rest", "move", "follow")


def offered_to_mind(house, cfg, pet, mem):
    """What its mind can decide to do now: everything it can do, less what its body does without being asked."""
    can = allowed(house, cfg, pet, mem)
    return [a for a in can if a not in BODY_ONLY] if cfg["body"]["on"] else can


def nameable(house, pet):
    """What it could give a name to here: an animal of its own that has none, or an egg that is nobody's (§4.1, §7.1)."""
    out = [c["kind"] for c in house["creatures"] if c.get("tame") == pet["id"] and c["room"] == pet["room"] and not c.get("name")]
    if any(p["room"] == pet["room"] and p["stage"] == "egg" and not p["parent"] and not p["name"] for p in house["pets"].values()):
        out.append("egg")
    return out


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
    if t in ("put_away", "take_out", "hang"):
        return order.check(a, house, cfg, pet, norm)
    if t == "take_name":
        if not offered(pet):
            return "nobody has offered you a name"
        return "there is already one called that in the house" if name_taken(house, pet, pet["called"]) else None
    if t not in life.unlocked(house, pet["stage"]):
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
        if norm(a.get("near")) == norm(a.get("object")):
            return "it cannot be put beside itself"
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
        if tk == "creature" and what in things.mine(house, pet, room):   # it is theirs and it is here: the reason is the creature
            return "the %s only takes small things you are carrying" % tr["kind"]
        return "you can only give what you carry or a thing of yours that is here"
    if t == "show":
        tk, tr = find(house, pet, a.get("to"))
        if norm(a.get("what")) not in room["objects"]:
            return "that is not here"
        return None if tk == "pet" and not tr["sleep"] else "there is nobody awake like that here"
    if t == "follow":
        return None if kind in ("pet", "creature") else "there is nobody like that here"
    if t == "nuzzle":
        if kind == "pet" and leaned(house, cfg, pet, ref):
            return "you leaned together not long ago and are close still"
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
        name = clean(a.get("name") or "", 16).strip().lower()
        if name and any((p["name"] or "").lower() == name for p in life.alive(house)):   # two Twines at once: nobody could tell who "Twine said" meant
            return "there is already one called that in the house: another name, or leave it to them"
        return life.can_lay(house, cfg, pet) or (None if filled(a.get("message")) else "the egg needs your words")
    if t == "bequeath":
        if norm(a.get("what")) not in room["objects"] and songs.known(house, pet, a.get("what") or ""):   # a song can be left too (SPEC-v3.1 §3.4)
            return None if life.heirs(house, pet, a.get("to")) else "there is no child of yours to leave it to"
        return life.check_bequeath(a, house, cfg, pet, norm)
    if t == "write":
        return walls.check_write(a, house, cfg, pet, norm, filled)
    if t == "scrub":
        return None if walls.find(room, norm, a.get("what")) else "there are no such words here"
    if t == "compose":
        if not filled(a.get("name")):
            return "the song needs a name"
        return None if songs.parse(a.get("notes"), cfg) else "that is not a tune"
    if t in ("sing", "teach_song"):
        if not songs.known(house, pet, a.get("song") or ""):
            return "you do not know a song by that name"
        tk, tr = find(house, pet, a.get("to")) if filled(a.get("to")) else (None, None)
        if t == "sing":
            return None if not filled(a.get("to")) or tk in ("pet", "egg") else "there is nobody like that here"
        return None if tk == "pet" and not tr["sleep"] else "there is nobody awake like that here"
    if t == "call":
        return None if tame(house, pet, a.get("who")) else "nothing of yours answers to that"
    if t == "name":
        what = norm(a.get("what"))
        if not filled(a.get("name")):
            return "no name"
        if what == "egg":
            return None if "egg" in nameable(house, pet) else "there is no egg here that wants a name"
        cr = tame(house, pet, what)
        return None if cr and cr["room"] == room["id"] else "you can only name an animal of your own that is here"
    if t == "ask_book":
        return book.check_ask(a, house, cfg, pet, filled)
    if t == "write_belief":
        if not filled(a.get("statement")):
            return "nothing to write"
        return None if len(mem.active()) < cfg["beliefs"]["max_active"] else "you hold too many beliefs; revise or discard one first"
    if t == "revise_belief":
        return None if mem.is_active(a.get("id")) and filled(a.get("statement")) else "there is no such belief"
    return "unknown action"


FOCUS = ("tidy", "be with", "explore", "make", "rest", "tend", "project", "play", "stay near")


def check_plan(turn, pet):
    """Shape only: what it wants to be about (SPEC-v3.3 §1.2: a focus, in its own words and as a kind the body can
    use) and the things it has decided to do, which may be none. Whether each is possible is checked when it is
    carried out. A reply with an `intention` and no focus is still taken (the scripted brains of the checks)."""
    focus = turn.get("focus") if isinstance(turn, dict) else None
    if isinstance(focus, dict) and (focus.get("type") not in FOCUS or not filled(focus.get("words"))):
        return "the reply had no usable focus"
    if not isinstance(turn, dict) or not (filled(turn.get("intention")) or isinstance(focus, dict)) or not filled(turn.get("expect")):
        return "the reply was not an intention"
    steps = turn.get("steps")
    if not isinstance(steps, list) or not (0 if focus else 1) <= len(steps) <= 5 or not all(isinstance(s, dict) and filled(s.get("type")) for s in steps):
        return "the reply had no usable steps"
    return None


def tame(house, pet, name):
    """The animal of its own that a name points at: by its kind or by the name it was given."""
    n = norm(name)
    return next((c for c in house["creatures"] if c.get("tame") == pet["id"] and n in (c["kind"], (c.get("name") or "").lower())), None)


def leaned(house, cfg, pet, other):
    """Have these two leaned together lately? (SPEC-v3.2 §9.) v3 stopped the nuzzle loop by not offering a lean to a
    pet that already felt close; once closeness was made to settle in the middle (part 12) nobody ever felt close, and
    accept, lean back, accept came round again. What a lean leaves behind is now remembered between the two of them."""
    return house["tick"] - pet.get("leaned", {}).get(other["id"], LONG_AGO) < cfg["effects"]["nuzzle_again_hours"] * cfg["ticks_per_hour"]


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
            "combine": "a", "bequeath": "what", "make": "near", "write": "on", "sing": "to", "teach_song": "to", "name": "what",
            "put_away": "what", "take_out": "what", "hang": "what"}.get(t)
    if t == "ask_book":
        at = next((o["pos"] for o in house["rooms"][pet["room"]]["objects"].values() if o.get("fix", {}).get("book")), None)
        return None if at is None or dist(pet["pos"], at) <= 1 else beside(cfg, at, pet["pos"])
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
        parts = "%s, %s" % (things.a_thing(cfg, m["recipe"]), things.SIZES[things.size(o) - 1])
        worn = "; it is damp" * bool(m.get("damp")) + "; it is dusty" * bool(m.get("dusty")) + "; something has been eating at it" * bool(m.get("eaten"))
        heir = m.get("heirloom")
        return "%s (%s): %s; it is %s; made for: %s%s%s" % (
            name, things.whose(house, pet, o), parts, m["recipe"]["material"], m["recipe"]["purpose"], worn,
            "; it is an heirloom" if heir else "")
    fix, state = o.get("fix", {}), o.get("state")
    hint = fixture_says(fix)
    if fix.get("plant"):
        state = "ripe" if o["state"] == "ripe" else "nearly ripe" if o["grow"] > 0.7 else "growing"
    return "%s%s: %s" % (name, " (%s)" % state if state else "", hint)


def fixture_says(fix):
    """What a piece of the house is, in a few words: said to a pet that looks at it, and to the visitor who points at it."""
    return ("its pages are full of small writing; it could be asked a question" if fix.get("book") else "a small box with a dial; it can be turned on or off" if fix.get("radio")
            else "a light" if "light" in fix else "something to eat from" if "meal" in fix else "a place to rest" if "rest" in fix
            else "soft to lie on" if "soft" in fix else "something to play with" if "toy" in fix
            else "something growing" if fix.get("plant") else "you could see yourself in it" if fix.get("mirror")
            else "you can see outside through it" if fix.get("window") else "water; things put in it drift off" if "water" in fix
            else "a warm patch of light on the floor" if fix.get("sun")
            else "it can be set " + " or ".join(fix["states"]) if "states" in fix else "a bench to work at" if fix.get("bench") else "it is just there")


def apply(house, cfg, pet, a, mem):
    """Carry out an action that passed its check. Returns (what the pet is told, need effects, novelty key).
    Effects may carry "tags" (hidden physics that fired) and "scale" (a room's rule on what it is worth)."""
    t, room, E = a["type"], house["rooms"][pet["room"]], cfg["effects"]
    name = label(pet)
    if t in ("put_away", "take_out", "hang"):
        return order.do(a, house, cfg, pet, norm)
    if t == "take_name":
        named(house, pet, mem, pet["called"].strip())
        return "you took the name %s; it is yours now" % pet["name"], {}, None
    if t == "observe":
        return "you watched the room for a while", dict(E["observe"]), "observe " + room["type"]
    if t == "rest":
        return "you rested", {"energy": E["rest_per_10s"]}, None
    if t == "move":
        to = norm(a["to"])
        return "you went over to " + ("the " + to if "the " + to in PLACES or find(house, pet, to)[0] in ("thing", "bit", "creature") else a["to"].strip()), {}, None
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
        water = room["objects"].get(norm(a["near"]), {}).get("fix", {}).get("water")
        if water and "made" in o:   # the pond's own rule (§6.1): what is set on the water floats away
            o["pos"] = list(min((t for t in water if not any(x["pos"] == t for x in room["objects"].values())), key=lambda t: dist(t, pet["pos"]), default=water[0]))
            return "you set %s on the water" % ref, {}, "arrange"
        o["pos"] = free_tile(house, cfg, room, to, ref)
        order.moved(o)
        return "you moved %s over by %s" % (ref, norm(a["near"])), {}, "arrange"
    if t == "combine":
        return things.combine(house, cfg, pet, a, clean, norm)
    if t == "paint":
        room["paint"] = {"wall": a["wall"], "floor": a["floor"]}
        moment(house, "painted", "%s painted %s: %s walls, %s floor" % (name, room["name"], a["wall"], a["floor"]), pet["id"], room["id"])
        return "you painted the walls %s and the floor %s" % (a["wall"], a["floor"]), dict(E["paint"]), "paint"
    if t == "teach":
        return things.teach(house, pet, a, norm(a["target"]))
    if t == "give":
        return give(house, cfg, pet, a)
    if t == "show":
        other, what = find(house, pet, a["to"])[1], norm(a["what"])
        add_event(house, other, "%s showed you the %s: %s" % (handle(house, other, pet), what, describe_thing(house, cfg, other, what)))
        other["news"].append("spoken")
        bump(other, cfg, E["show"])
        return "you showed the %s to %s" % (what, handle(house, pet, other)), {"company": E["show"]["company"]}, "show"
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
        order.moved(o)
        if owner["room"] == room["id"] and not owner["sleep"]:
            add_event(house, owner, "%s took your %s" % (handle(house, owner, pet), what))
            owner["news"].append("spoken")
        else:
            owner.setdefault("lost", []).append({"name": what, "by": pet["id"], "room": room["id"]})
        moment(house, "took", "%s took %s, '%s', from %s" % (name, things.a_thing(cfg, o["made"]["recipe"]), what, label(owner)), pet["id"], room["id"])
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
        again = said_before(pet, other, text)
        bump(other, cfg, {"company": 0.0 if again else E["spoken_to"]})
        house.setdefault("said", []).append({"tick": house["tick"], "from": pet["id"], "to": other["id"], "kind": "tell", "text": text})
        moment(house, "told", "%s told %s something to keep" % (name, label(other)), pet["id"], room["id"])
        return "you told %s what you wanted them to keep%s" % (handle(house, pet, other), AGAIN if again else ""), {} if again else {"company": E["said_to"]}, "tell"
    if t == "lay_egg":
        return life.lay_egg(house, cfg, pet, a, clean)
    if t == "bequeath":
        if norm(a["what"]) not in room["objects"]:
            return songs.leave(house, cfg, pet, life.heirs(house, pet, a.get("to")), a["what"])
        return life.bequeath(house, cfg, pet, a, norm)
    if t == "write":
        return walls.write(house, cfg, pet, a, clean, norm)
    if t == "scrub":
        return walls.scrub(house, cfg, pet, a, norm)
    if t == "compose":
        return songs.compose(house, cfg, pet, a, clean)
    if t == "sing":
        return songs.sing(house, cfg, pet, a, find, handle, bump)
    if t == "teach_song":
        return songs.teach(house, cfg, pet, a, find, handle)
    if t == "call":
        from . import director
        return director.come(house, cfg, tame(house, pet, a["who"]), pet), {}, None
    if t == "name":
        new = clean(a["name"], 16)
        if norm(a["what"]) == "egg":
            egg = next(p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] == "egg" and not p["parent"] and not p["name"])
            if any((p["name"] or "").lower() == new.lower() for p in life.alive(house)):
                return "there is already one called that in the house", {}, None
            egg["name"] = new
            moment(house, "named", "%s named the egg that is nobody's %s" % (name, new), pet["id"], room["id"])
            return "you named the egg %s" % new, {}, "name"
        cr = tame(house, pet, a["what"])
        cr["name"] = new
        for an in pet.get("animals", []):
            if an["id"] == cr["id"]:
                an["name"] = new
        witness(house, pet, "%s calls the %s %s" % (name, cr["kind"], new))
        moment(house, "named", "%s named the %s %s" % (name, cr["kind"], new), pet["id"], room["id"])
        return "you named the %s %s" % (cr["kind"], new), {}, "name"
    if t == "ask_book":
        return book.ask(house, cfg, pet, a, clean)
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


def offered(pet):
    """Has the visitor offered it a name that is not (yet) its own?"""
    c = (pet.get("called") or "").strip()
    return bool(c) and c.lower() != (pet["name"] or "").lower()


def takes(pet, text):
    """Does what it just said take the name it was offered? "My name is Garry", "I am Garry", "I'm Garry", "call me
    Garry", "yes, Garry". Saying the name some other way ("I am not Garry", "who is Garry?") does not."""
    c = (pet.get("called") or "").strip()
    return offered(pet) and bool(re.search(r"\b(my name is|name is|i am|i'm|call me|called|yes,?|i will be|i'll be)\s+%s\b" % re.escape(c), str(text), re.I))


def name_taken(house, pet, name):
    return any((p["name"] or "").lower() == name.strip().lower() for p in life.alive(house) if p is not pet)


def named(house, pet, mem, new):
    """A pet has a name from now on: one it took from the visitor, or one it gave itself."""
    was, took = label(pet), new.lower() == (pet.get("called") or "").strip().lower()
    pet["name"] = new
    pet["named"] = {"tick": house["tick"], "by": "visitor" if took else "itself"}   # for the visitor's card: it took the name
    if mem:
        mem.update_self(name=new, named_at=house["tick"])
    moment(house, "named", "%s took the name %s" % (was, new) if took else "%s named itself %s" % (was, new), pet["id"], pet["room"])


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
        add_event(house, pet, lost.get("text") or "your %s is gone%s" % (lost["name"], "; %s has it" % handle(house, pet, taker) if taker else ""))
        pet["lost"].remove(lost)
    if first and not fresh:
        moment(house, "entered", "%s went into %s for the first time" % (label(pet), to["name"]), pet["id"], to["id"])
    spec = cfg["house"]["rooms"][to["type"]]
    text = "you went through the %s door into %s: %s" % (d, to["name"], spec["feel"]) if first else "you went through the %s door into %s" % (d, to["name"])
    return text, {"curiosity": cfg["effects"]["new_room"]} if first else {}, "go " + to["type"]


def speak(house, cfg, pet, a, mem):
    text, room = life.last_sentence(clean(a["text"], 170), 140), house["rooms"][pet["room"]]
    kind, other = find(house, pet, a.get("to")) if filled(a.get("to")) else (None, None)
    pet["said"] = {"text": text, "tick": house["tick"], "to": other["id"] if kind == "pet" else "visitor" if kind == "visitor" else None}
    rec = {"tick": house["tick"], "from": pet["id"], "to": pet["said"]["to"], "kind": "speak", "text": text}
    again = kind == "pet" and said_before(pet, other, text)
    for p in here(house, pet, awake=True):
        if kind == "pet" and p is other:
            p["inbox"].append('%s said to you: "%s"' % (handle(house, p, pet), text))
            p["news"].append("spoken")
            bump(p, cfg, {"company": 0.0 if again else cfg["effects"]["spoken_to"]})
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
    own = re.search(r"\bmy name is ([A-Za-z][\w'-]{0,15})", text, re.I)
    new = pet["called"].strip() if takes(pet, text) else own.group(1).strip() if own and not pet["name"] else None
    if new and not name_taken(house, pet, new):
        named(house, pet, mem, new)
    fx = dict(cfg["effects"]["speak"])
    if kind == "pet" and not again:
        fx["company"] = cfg["effects"]["said_to"]
    return 'you said%s: "%s"%s' % (" to " + handle(house, pet, other) if kind == "pet" else "", text, AGAIN if again else ""), fx, "speak"


AGAIN = "; you have said as much to them before, and it lands flat"


def said_before(pet, other, text):
    """Has it said much the same to this one already? Words wear out like any other ease (as a nuzzle does)."""
    from .story import alike, content
    words, past = content(text, True), pet.setdefault("said_to", {}).setdefault(other["id"], [])
    again = any(alike(words, set(w)) >= 0.8 for w in past)
    past.append(sorted(words))
    del past[:-12]
    return again


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
    if fix.get("radio"):   # SPEC-v3.1 §5.1: switched on, it speaks before long
        o["state"] = "on" if o["state"] == "off" else "off"
        if o["state"] == "on":
            house.setdefault("radio", {"next": 0, "told": [], "said": []})["next"] = house["tick"] + ticks(cfg, 20)
        return "you turned the dial on the %s; %s" % (name, "it crackles, and a hum comes out of it" if o["state"] == "on" else "it goes quiet"), {}, "use " + name
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
        return "you played with the %s" % name, {"curiosity": fix["toy"], **E["play"]}, "use " + name
    if "rest" in fix:
        return "you lay on the %s a moment" % name, {"energy": fix["rest"] * 1.5}, "use " + name
    if fix.get("mirror"):
        return "in the mirror you see yourself: " + genome.describe(pet["genome"]), {}, "look mirror"
    return "you tried to use the %s; nothing came of it" % name, {}, None


def offer(house, cfg, pet, other, what):
    other["offers"] = [o for o in other["offers"] if not (o["from"] == pet["id"] and o["kind"] == what["kind"])]
    other["offers"].append(dict(what, **{"from": pet["id"], "tick": house["tick"]}))
    other["news"].append("offer")   # a reason to think again, not an alarm: answering offers at once made nuzzling a loop


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
        gain = {}
        near = 1.0 if knows(pet, giver) and knows(giver, pet) else cfg["strangers"]["nuzzle"]   # a stranger's lean is worth less (SPEC-v3.1 §7.2)
        for a, b in ((pet, giver), (giver, pet)):   # closeness with the same one eases less each time, until a night has passed
            key = "nuzzle " + b["id"]
            n = a["times"].get(key, 0)
            gain[a["id"]] = {k: v * near * max(0.1, E["nuzzle_wear"] ** n) for k, v in E["nuzzle"].items()}
            a["times"][key], a["seen_at"][key] = min(cfg["novelty"]["cap"], n + 1), house["tick"]
        bump(giver, cfg, gain[giver["id"]])
        pet.setdefault("leaned", {})[giver["id"]] = giver.setdefault("leaned", {})[pet["id"]] = house["tick"]
        add_event(house, giver, "%s leaned back against you" % handle(house, giver, pet))
        giver["news"].append("answer")
        house.setdefault("said", []).append(rec)
        pair, today = "|".join(sorted((giver["id"], pet["id"]))), house["clock"]["day"]
        if house.setdefault("nuzzled", {}).get(pair) != today:   # a moment the first time in a day, not every time
            house["nuzzled"] = {k: d for k, d in house["nuzzled"].items() if d == today} | {pair: today}
            moment(house, "nuzzle", "%s and %s nuzzled" % (label(giver), label(pet)), pet["id"], room["id"])
        # said once, when it turns: told after every lean it became a law the pets recited (third run: on 65 to 81% of leans)
        worn = pet["times"]["nuzzle " + giver["id"]] == cfg["novelty"]["familiar"] + 1
        return "you leaned against %s%s" % (handle(house, pet, giver), "; it is familiar now, and eases you less" if worn else ""), gain[pet["id"]], None
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
        order.moved(o)
    add_event(house, giver, "%s took the %s you offered" % (handle(house, giver, pet), what))
    giver["news"].append("answer")
    bump(giver, cfg, {"company": E["gift"]})
    house.setdefault("said", []).append(rec)
    given = "some " + what if off["bit"] else "%s, '%s'" % (things.a_thing(cfg, room["objects"][what]["made"]["recipe"]), what)
    moment(house, "gift", "%s gave %s %s" % (label(giver), label(pet), given), pet["id"], room["id"])
    return "you took the %s from %s" % (what, handle(house, pet, giver)), {"company": E["gift"]}, "gift"


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
        if p and p["room"] == rid and p["stage"] == "egg" and not p["parent"] and not p["name"]:   # a foundling can be named by the visitor (§7.1)
            if any((x["name"] or "").lower() == new.lower() for x in life.alive(house)):
                return "there is already one called that"
            p["name"] = new
            moment(house, "named", "the visitor named the egg that is nobody's %s" % new, p["id"], rid)
        elif p and p["room"] == rid and p["stage"] not in ("egg", "dead"):
            p["inbox"].append("the visitor calls you %s; the name is yours if you take it" % new)
            p["news"].append("visitor")
            p["called"] = new
        elif cmd.get("object") in things.made(room):
            room["objects"][cmd["object"]]["made"]["called"] = new
            tell("the visitor calls the %s '%s'" % (cmd["object"], new))
        else:
            return "nothing here to name"
    elif t == "write":   # SPEC-v3.1 §2.3
        if not filled(cmd.get("text")):
            return "nothing to write"
        m = walls.visitor(house, cfg, room, life.last_sentence(clean(cmd["text"], 100), cfg["writing"]["max_chars"]), cmd.get("on"))
        tell("the visitor wrote something on the %s" % m["on"])
    elif t == "radio_off":   # the mute switch (§5.3): off in the house, not just quiet in the view
        from . import radio
        radio.off(house)
    elif t == "radio":   # SPEC-v3.3 §3.2: their radio once they have one, the visitor's own before that
        from . import radio
        radio.visitor(house, cfg, room, bool(cmd.get("on")), cmd.get("plays"))
    elif t == "music":   # SPEC-v3.3 §3.1: the visitor's music, in this room or through the house, or off
        mood = cmd.get("mood")
        if mood in (None, "", "off"):
            house["dj"] = dict(house.get("dj") or {}, music=None)
        elif mood in cfg["music"]["tunes"]:
            house["dj"] = dict(house.get("dj") or {}, music={"mood": mood, "scope": "house" if cmd.get("scope") == "house" else rid, "since": house["tick"]})
            for p in house["pets"].values():
                if p["stage"] not in ("egg", "dead") and not p["sleep"] and (cmd.get("scope") == "house" or p["room"] == rid):
                    add_event(house, p, "the visitor has begun to play %s music" % mood)
        else:
            return "no such music"
    else:
        return "unknown visitor action"
    return None
