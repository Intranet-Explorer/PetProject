"""Order (SPEC-v3.3 §2): places to keep things, homes for things, and how much of a mess a room is. A thing put on
a shelf or in a chest is still the same thing, in the same room, doing whatever it does; it only stops lying on the
floor. Tidying is real: it moves things, and a thing put in the same place twice has a home there."""
from . import things
from .world import add_event, days as world_days, dist, free_tile, label, moment

MESS = ["everything here has its place", "a few things lie about", "this room is a mess"]
NOWHERE = "there's nowhere left to put things here: a shelf, a box, a basket or a chest would be somewhere to keep them"


def cap(cfg, o):
    """How many things this can hold: a fixture with a surface, or a made thing of a kind that keeps things."""
    if "made" in o:
        return cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("store", 0)
    return o.get("fix", {}).get("store", 0)


def held(room, name):
    return [n for n, o in room["objects"].items() if o.get("on") == name]


def stores(cfg, room):
    """{name: places left} for everything here that keeps things."""
    return {n: cap(cfg, o) - len(held(room, n)) for n, o in room["objects"].items() if cap(cfg, o)}


def can_hang(cfg, o):
    return "made" in o and bool(cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("hangs")) and not o.get("wall")


def settled(cfg, room, o):
    """Is a made thing where a person looking in would say it belongs: on or in something, on the wall, one of a
    corner of things of its sort, an heirloom by its stone, itself a place to keep things, or too heavy to be
    anywhere else? Anything else on the floor is clutter, however neatly it lies (12 October 2026: "out of the
    way" was a kind of tidy nobody could see)."""
    return bool(o.get("on") or o.get("wall") or cap(cfg, o) or things.prop(cfg, o).get("fixed")
                or (o["made"].get("heirloom") and o.get("home", {}).get("pos") and dist(o["home"]["pos"], o["pos"]) <= 1)
                or any(list(o["pos"]) in a["tiles"] for a in room.get("areas", [])))


def loose(house, cfg, room):
    """The made things lying about on the floor."""
    return [n for n, o in things.made(room).items() if not settled(cfg, room, o)]


def loose_bits(room):
    """Dropped bits lying on the floor (not the ones a room grows, and not the ones put away in something)."""
    return [s for s in room["spots"] if s["loose"] and not s.get("on")]


def count(house, cfg, room):
    """What a person sees lying about: every made thing on the floor that is not put away, hung up or part of a
    corner, and every loose bit."""
    return len(loose(house, cfg, room)) + len(loose_bits(room))


def clutter(house, cfg, room):
    """0 tidy, 1 a few things about, 2 a mess."""
    n, O = count(house, cfg, room), cfg["order"]
    return 0 if n <= O["tidy_below"] else 1 if n <= O["mess_above"] else 2


def full(cfg, room):
    """Is there nowhere left here to put things away: nothing that keeps things, none of it with room for another
    thing, or bits on the floor and none of it with room for a bit?"""
    return not any(k > 0 for k in stores(cfg, room).values()) or (bool(loose_bits(room)) and not any(k > 0 for k in bit_room(cfg, room).values()))


def bit_room(cfg, room):
    """{name: loose bits it can still take} for everything here that keeps things: bits go in beside the things."""
    return {n: cfg["order"]["bits"] - sum(1 for s in room["spots"] if s.get("on") == n) for n, o in room["objects"].items() if cap(cfg, o)}


def into(cfg, room, store):
    o = room["objects"][store]
    inside = o.get("fix", {}).get("inside") or cfg["kinds"].get(o.get("made", {}).get("recipe", {}).get("kind"), {}).get("inside")
    return "%s the %s" % ("in" if inside else "on", store)


def last_touch(o):
    """The tick someone last used, moved or made it."""
    return max(o["made"].get("touched", 0), o["made"].get("used_at", 0), o["made"]["tick"], o.get("kept", 0))


def old(house, cfg, room, name):
    """Forgotten: a made thing nobody has touched for `old_days`, that is not an heirloom, not put away on anything,
    and not itself a place where things are kept."""
    o = room["objects"][name]
    return not o["made"].get("heirloom") and not o.get("on") and not cap(cfg, o) \
        and world_days(cfg, last_touch(o), house["tick"]) >= cfg["order"]["old_days"]


def storeroom(house):
    return next((r for r in house["rooms"].values() if r["type"] == "storeroom"), None)


def way(house, pet):
    """The door from where it is toward the nearest mess it knows of, through rooms it knows: a door, or None."""
    rooms, seen, queue = house["rooms"], {pet["room"]}, [(pet["room"], None)]
    while queue:
        rid, first = queue.pop(0)
        if first and rooms[rid].get("mess") == 2:
            return first
        for d, to in rooms[rid]["doors"].items():
            if to in pet["rooms"] and to not in seen and rooms[to]["type"]:
                seen.add(to)
                queue.append((to, first or d))
    return None


def may_move(house, pet, o):
    """Its own things, nobody's, the dead's, and its young children's: tidying is not taking."""
    return things.free_to_change(house, pet, o) or house["pets"].get(o["made"]["owner"], {}).get("parent") == pet["id"]


def corner(house, cfg, room, name):
    """A tile beside the others of its sort, where three or more together are a corner (`areas`): or None, when
    there are not enough of them here, it stands with them already, or there is no room beside them."""
    o = room["objects"][name]
    kinds = next((ks for ks in KEEP.values() if o["made"]["recipe"].get("kind") in ks), None)
    group = [x for n, x in things.made(room).items() if n != name and kinds and x["made"]["recipe"].get("kind") in kinds and not x.get("wall") and not x.get("on")]
    if len(group) < 2:
        return None
    best = max(group, key=lambda a: sum(dist(a["pos"], x["pos"]) <= 2 for x in group))
    if dist(o["pos"], best["pos"]) <= 2:
        return None
    tile = free_tile(house, cfg, room, best["pos"], name)
    return tile if dist(tile, best["pos"]) <= 2 else None


def place_for(house, cfg, pet, room, name):
    """Where a thing belongs: its home if it has one here, the wall if it hangs, beside the others of its sort if
    they make a corner, else the nearest place that keeps things and has room. ("on", storage), ("wall", slot) or
    ("at", tile); None when there is nowhere, and then it is left where it lies."""
    o = room["objects"][name]
    home, left = o.get("home"), stores(cfg, room)
    if home and home.get("room") == room["id"]:
        if home.get("on") and left.get(home["on"], 0) > 0:
            return "on", home["on"]
        if home.get("pos") and o["made"].get("heirloom") and dist(home["pos"], o["pos"]) > 1:
            return "at", free_tile(house, cfg, room, home["pos"], name)
    if can_hang(cfg, o) and things.wall_slot(house, room):
        return "wall", things.wall_slot(house, room)
    beside = corner(house, cfg, room, name)
    if beside:
        return "at", beside
    free = [n for n, k in left.items() if k > 0 and n != name]
    if free:
        return "on", min(free, key=lambda n: dist(room["objects"][n]["pos"], o["pos"]))
    return None


def job(house, cfg, pet, room):
    """Something for a tidy pet to do here, the nearest of: a loose thing with somewhere to go, a forgotten thing
    to carry off to the storeroom, a pawful of loose bits to put in something. {what, job: [kind, name, how,
    place], pos}, or None when there is nothing it may move or nowhere to put it."""
    out, objs, sr = [], room["objects"], storeroom(house)
    for n in loose(house, cfg, room):   # anyone may put anyone's thing in its place here: it stays its owner's, in the same room
        where = place_for(house, cfg, pet, room, n)
        if where:
            out.append({"what": n, "job": ["thing", n, where[0], where[1]], "pos": objs[n]["pos"]})
    if sr:   # until the storeroom has been found there is nowhere for old things to go
        got = {j["what"] for j in out}
        out += [{"what": n, "job": ["old", n, "away", sr["id"]], "pos": o["pos"]} for n, o in things.made(room).items()
                if n not in got and may_move(house, pet, o) and (old(house, cfg, room, n) or (room is sr and not settled(cfg, room, o)))]   # in the storeroom itself, whatever lies about is put by
    bits, space = loose_bits(room), {n: k for n, k in bit_room(cfg, room).items() if k > 0}
    if bits and space:
        first = min(bits, key=lambda s: dist(s["pos"], pet["pos"]))
        out.append({"what": "loose bits" if len(bits) > 1 else "loose %s" % first["bit"], "pos": first["pos"],
                    "job": ["bits", None, "on", min(space, key=lambda n: dist(objs[n]["pos"], first["pos"]))]})
    return min(out, key=lambda j: dist(j["pos"], pet["pos"]), default=None)


def do_job(house, cfg, pet, room, job):
    """Carry out what `job` found. Returns where it went, in the pet's words, or "" if it could no longer be done."""
    kind, name, how, place = job
    if kind == "bits":
        took = sorted(loose_bits(room), key=lambda s: dist(s["pos"], pet["pos"]))[:max(0, min(cfg["order"]["pawful"], bit_room(cfg, room).get(place, 0)))]
        for s in took:
            s["on"], s["pos"] = place, list(room["objects"][place]["pos"])
        return into(cfg, room, place) if took else ""
    o = room["objects"].get(name)
    if not o or "made" not in o or o.get("on"):
        return ""
    if kind == "old":
        return set_aside(house, cfg, pet, room, name)
    if how == "on" and (place not in room["objects"] or stores(cfg, room).get(place, 0) <= 0):
        return ""
    said, owner = put(house, cfg, pet, room, name, how, place), house["pets"].get(o["made"]["owner"])
    if owner and owner is not pet and owner["stage"] != "dead":
        add_event(house, owner, "your %s was put %s" % (name, said))
    return said


def wear_out(house, cfg, room, name):
    """A thing long forgotten falls apart. What it was made of goes into whatever keeps things there, if any has room."""
    o = room["objects"].pop(name)
    for b in o["made"]["bits"]:
        space = [n for n, k in bit_room(cfg, room).items() if k > 0]
        if space:
            room["spots"].append({"bit": b, "pos": list(room["objects"][space[0]]["pos"]), "ready": True, "back": None, "loose": True, "on": space[0]})
    things.gone(house, o, name, "worn out", room)
    moment(house, "unmade", "the %s '%s', long forgotten, wore out and went back to bits" % (o["made"]["recipe"].get("kind", "thing"), name), None, room["id"])


def set_aside(house, cfg, pet, room, name):
    """An old thing leaves for the storeroom (12 October 2026: nothing ever left, and the dead's things piled up).
    It goes onto whatever keeps things there. When none of that has room, whichever has gone longest untouched, of
    it and what the storeroom keeps (heirlooms apart), wears out and goes back to bits. Returns the pet's words.
    ponytail: the thing goes there by itself once the pet has picked it up; walking it through the house is the upgrade."""
    sr, o = storeroom(house), room["objects"][name]
    space = [n for n, k in stores(cfg, sr).items() if k > 0 and n != name]
    if not space:
        kept = [n for n, x in things.made(sr).items() if x.get("on") and not x["made"].get("heirloom")]
        worst = min(kept + [name], key=lambda n: last_touch((room if n == name else sr)["objects"][n]))
        wear_out(house, cfg, room if worst == name else sr, worst)
        if worst == name:
            return "down for the last time: it had worn out, and went back to bits"
        space = [n for n, k in stores(cfg, sr).items() if k > 0 and n != name]
    del room["objects"][name]
    for k in ("wall", "tidy", "home", "places"):
        o.pop(k, None)
    o["on"], o["pos"] = space[0], list(sr["objects"][space[0]]["pos"])   # being carried off is not being wanted: it stays as long forgotten as it was
    sr["objects"][name] = o
    for m in [m for m in room.get("marks", []) if m["on"] == name] if room is not sr else []:   # what is written on a thing goes where the thing goes
        room["marks"].remove(m)
        sr.setdefault("marks", []).append(m)
    owner = house["pets"].get(o["made"]["owner"])
    if owner and owner is not pet and owner["stage"] != "dead":
        add_event(house, owner, "your %s was put away in the storeroom" % name)
    return "away in the storeroom" if room is not sr else into(cfg, sr, space[0])


def remember(o, room, where):
    """A thing put away in the same place twice has a home there (§2.3)."""
    seen = o.setdefault("places", {})
    seen["on|" + where] = seen.get("on|" + where, 0) + 1
    if seen["on|" + where] >= 2 and not (o["made"].get("heirloom") and o.get("home")):
        o["home"] = {"room": room["id"], "on": where}


def put(house, cfg, pet, room, name, how, where):
    """Put a thing in its place. Returns how the pet would say where it went."""
    o = room["objects"][name]
    o.pop("on", None)
    o["kept"] = house["tick"]
    if how == "on":
        o["on"], o["pos"] = where, list(room["objects"][where]["pos"])
        said = into(cfg, room, where)
        remember(o, room, where)
    elif how == "wall":
        o["wall"], o["pos"] = True, list(where)
        said = "up on the wall"
    else:
        o["pos"] = list(where)
        said = "by its stone" if o["made"].get("heirloom") else "with the others like it"
    room["areas"] = areas(house, cfg, room)
    return said


def check(a, house, cfg, pet, norm):
    """put_away, take_out, hang: None if it can happen now, else why not."""
    room, t = house["rooms"][pet["room"]], a.get("type")
    name = norm(a.get("what"))
    o = room["objects"].get(name)
    if not o or "made" not in o:
        return "that is not a made thing here"
    if not may_move(house, pet, o):
        return "that belongs to someone else"
    if t == "take_out":
        return None if o.get("on") else "it is not put away"
    if t == "hang":
        if not cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("hangs"):
            return "that is not a thing to hang up"
        return None if not o.get("wall") and things.wall_slot(house, room) else "there is no free place on the wall here"
    where = norm(a.get("where"))
    if where not in room["objects"] or not cap(cfg, room["objects"][where]) or where == name:
        return "there is nowhere like that here to keep things"
    return None if stores(cfg, room)[where] > 0 else "the %s is full" % where


def do(a, house, cfg, pet, norm):
    room, t, name = house["rooms"][pet["room"]], a["type"], norm(a["what"])
    o = room["objects"][name]
    if t == "take_out":
        was, o["kept"] = o.pop("on"), house["tick"]
        o["pos"] = free_tile(house, cfg, room, pet["pos"], name)
        return "you took the %s down from the %s" % (name, was), {}, None
    if t == "hang":
        said = put(house, cfg, pet, room, name, "wall", things.wall_slot(house, room))
        return "you hung the %s %s" % (name, said), {}, "put away"
    said = put(house, cfg, pet, room, name, "on", norm(a["where"]))
    return "you put the %s %s" % (name, said), {}, "put away"


def moved(o, tick):
    """A thing carried off somewhere else is no longer on its shelf; and someone has had it in their paws."""
    o.pop("on", None)
    o["kept"] = tick


def upkeep(house, cfg):
    """Whatever happens to a shelf happens to what is on it: moved, its things go with it; gone (taken apart, joined
    into something, carried off), they are on the floor again. Run every tick, so nothing else has to remember."""
    for room in house["rooms"].values():
        for n, o in room["objects"].items() if room["type"] else ():
            store = room["objects"].get(o.get("on"))
            if "on" in o and (store is None or not cap(cfg, store)):
                del o["on"]
                o["pos"] = free_tile(house, cfg, room, o["pos"], n)
            elif "on" in o and o["pos"] != store["pos"]:
                o["pos"] = list(store["pos"])
        for s in room["spots"] if room["type"] else ():   # the bits put away in something go the same way
            store = room["objects"].get(s.get("on"))
            if "on" in s and (store is None or not cap(cfg, store)):
                del s["on"]
                s["pos"] = free_tile(house, cfg, room, s["pos"])
            elif "on" in s and s["pos"] != store["pos"]:
                s["pos"] = list(store["pos"])


KEEP = {"sleeping corner": ("cushion", "blanket", "nest", "bed-mat", "rug", "doll"), "music corner": ("bell", "drum", "flute", "wind chime"),
        "lamp corner": ("candle", "lantern", "lamp"), "keepsake shelf": ()}


def areas(house, cfg, room):
    """Name the places a room has grown (§2.3): where three or more things of a sort stand together, and any shelf
    of heirlooms. [{name, tiles}] for the view's faint tint and the hover cards; recomputed now and then."""
    out, made = [], things.made(room)
    for area, kinds in KEEP.items():
        if not kinds:
            for store in {o.get("on") for o in made.values() if o.get("on") and o["made"].get("heirloom")}:
                out.append({"name": "keepsake shelf", "tiles": [list(room["objects"][store]["pos"])], "on": store})
            continue
        group = [o for o in made.values() if o["made"]["recipe"].get("kind") in kinds and not o.get("wall")]
        best = max(([x["pos"] for x in group if dist(x["pos"], o["pos"]) <= 2] for o in group), key=len, default=[])
        if len(best) >= 3:
            out.append({"name": area, "tiles": [list(t) for t in dict.fromkeys(map(tuple, best))]})
    bench = next((n for n, o in room["objects"].items() if o.get("fix", {}).get("bench")), None)
    if bench and (held(room, bench) or sum(1 for s in room["spots"] if dist(s["pos"], room["objects"][bench]["pos"]) <= 2) >= 2):
        out.append({"name": "making bench", "tiles": [list(room["objects"][bench]["pos"])], "on": bench})
    return out


def heirloom_home(house, cfg, room, o):
    """An heirloom's home is by the family's stone if there is one here, else by the bed (§2.3)."""
    spot = next((x["pos"] for x in room["objects"].values() if "memorial" in x), None) \
        or next((x["pos"] for x in room["objects"].values() if "rest" in x.get("fix", {})), None)
    if spot:
        o["home"] = {"room": room["id"], "pos": free_tile(house, cfg, room, spot)}
