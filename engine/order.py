"""Order (SPEC-v3.3 §2): places to keep things, homes for things, and how much of a mess a room is. A thing put on
a shelf or in a chest is still the same thing, in the same room, doing whatever it does; it only stops lying on the
floor. Tidying is real: it moves things, and a thing put in the same place twice has a home there."""
from . import things
from .world import add_event, days as world_days, dist, free_tile, label, moment, taken, ticks

MESS = ["everything here has its place", "a few things lie about", "this room is a mess"]
NOWHERE = "there's nowhere left to put things here: a shelf, a box, a basket or a chest would be somewhere to keep them"
BOX = 10 ** 6   # a keepsake box has no limit


def cap(cfg, o):
    """How many things this can hold: a fixture with a surface, or a made thing of a kind that keeps things."""
    if "made" in o:   # (SPEC-v3.4 §3.4: one built with a hammer is sturdier, and holds two more)
        return cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("store", 0) + (2 if o["made"].get("sturdy") and cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("store") else 0)
    return o.get("fix", {}).get("store", 0)


def held(room, name):
    return [n for n, o in room["objects"].items() if o.get("on") == name]


def keeps(o):
    """Whose keepsake box this is: the id of the one who died, or None for anything else."""
    return o.get("fix", {}).get("keepsake")


def stores(cfg, room):
    """{name: places left} for everything here that keeps things. (Not a keepsake box: it is for one pet's things.)"""
    return {n: cap(cfg, o) - len(held(room, n)) for n, o in room["objects"].items() if cap(cfg, o) and not keeps(o)}


def can_hang(cfg, o):
    return "made" in o and bool(cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("hangs")) and not o.get("wall")


def settled(cfg, room, o):
    """Is a made thing somewhere other than lying on the floor (13 October 2026: clutter is what a person looking in
    sees): on or in something, on the wall, an heirloom by its stone, or furniture the room uses (somewhere to keep
    things, something to sit on or grow things in, something too heavy to be anywhere else)? Anything else on the
    floor is clutter, however neatly it lies, unless it is one of the few things of a corner (`corners`)."""
    return bool(o.get("on") or o.get("wall") or cap(cfg, o) or things.prop(cfg, o).get("fixed") or o.get("planted")
                or cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("furniture")
                or (o["made"].get("heirloom") and o.get("home", {}).get("pos") and dist(o["home"]["pos"], o["pos"]) <= 1))


def loose(house, cfg, room):
    """The made things lying about on the floor."""
    put = {n for names in corners(house, cfg, room).values() for n in names}
    return [n for n, o in things.made(room).items() if n not in put and not settled(cfg, room, o)]


def loose_bits(room):
    """Dropped bits lying on the floor (not the ones a room grows, and not the ones put away in something)."""
    return [s for s in room["spots"] if s["loose"] and not s.get("on")]


def count(house, cfg, room):
    """What a person sees lying about: every made thing on the floor that is not furniture the room uses or one of
    the few things of a corner, and every loose bit."""
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
    return {n: cfg["order"]["bits"] - sum(1 for s in room["spots"] if s.get("on") == n) for n, o in room["objects"].items() if cap(cfg, o) and not keeps(o)}


def inside(cfg, o):
    """Does this keep things out of sight (a chest, a crate, a basket) rather than on show (a shelf)?"""
    return bool(o.get("fix", {}).get("inside") or cfg["kinds"].get(o.get("made", {}).get("recipe", {}).get("kind"), {}).get("inside"))


def into(cfg, room, store):
    return "%s the %s" % ("in" if inside(cfg, room["objects"][store]) else "on", store)


def last_touch(o):
    """The tick someone last used, moved or made it."""
    return max(o["made"].get("touched", 0), o["made"].get("used_at", 0), o["made"]["tick"], o.get("kept", 0))


def floor_count(house, cfg, room):
    """SPEC-v3.5.4 §1, as v3.5.5 counts it: the made things lying loose on a room's floor (`loose`), not its furniture,
    its boxes and baskets, its statues or its sculptures."""
    return sum(1 for n in loose(house, cfg, room) if not statue(n, room["objects"][n]) and room["objects"][n]["made"]["recipe"].get("kind") != "sculpture")


def crowded(house, cfg, room):
    """SPEC-v3.5.4 §1: so many made things on the floor that the room feels cluttered (no longer a bar to making)."""
    return floor_count(house, cfg, room) >= cfg["make"]["crowded"]


def statue(name, o):
    """A statue stays (SPEC-v3.5.4 §1): one built, or a made thing that is one by its name or kind."""
    return "statue" in name or "statue" in (o.get("made", {}).get("recipe", {}).get("kind") or "") or bool(o.get("fix", {}).get("built"))


def clutter_of(house, cfg, room):
    """SPEC-v3.5.4 §1: in a crowded room, the old things that could go (to the machine, or a keepsake box), oldest
    first. What stays: heirlooms, statues, things the visitor named or starred, what is kept in a box or on anything, things on
    a wall, a place to keep things with anything in it (an empty one can go), what is too heavy to move, anything used
    in the last world day (put away or moved is not used), and the newest thing each pet made."""
    if not crowded(house, cfg, room):
        return []
    newest = {}
    for r in house["rooms"].values():
        for o in things.made(r).values() if r["type"] else ():
            newest[o["made"]["by"]] = max(newest.get(o["made"]["by"], 0), o["made"]["tick"])
    used = lambda o: max(o["made"].get("touched", 0), o["made"].get("used_at", 0), o["made"]["tick"])
    objs = room["objects"]
    # what is in an ordinary box goes too (not what is in a keepsake box): emptied, the box itself can go. The box with
    # least in it is emptied first.
    out = [((len(held(room, o["on"])) if o.get("on") else 0, used(o)), n) for n, o in things.made(room).items()
           if (not o.get("on") and not o.get("wall") or o.get("on") in objs and cap(cfg, objs[o["on"]]) and not keeps(objs[o["on"]]))
           and not o["made"].get("heirloom") and not o["made"].get("called") and not o["made"].get("star") and not keeps(o) and not held(room, n) and not statue(n, o)
           and not things.prop(cfg, o).get("fixed") and not o.get("planted") and newest.get(o["made"]["by"]) != o["made"]["tick"]
           and world_days(cfg, used(o), house["tick"]) >= cfg["make"]["clutter_days"]]
    return [n for _, n in sorted(out)]


_FIRSTS = {}


def firsts_of(house):
    """{(maker, tick made)} of the things that were a first in the house or the family (SPEC-v3.5.4 feats; a thing
    made from v3.5.8 on also says so itself)."""
    L, memo = house.get("feats", {}).get("list", []), _FIRSTS
    if memo.get("n") != (id(L), len(L)):   # (rebuilt when the feats grow)
        memo.update(n=(id(L), len(L)), set={(f["pet"], f["tick"]) for f in L if f["kind"] == "first" and f.get("level") in ("house", "family")
                                   and f.get("key", "").partition(":")[0] in ("kind", "make")})
    return memo["set"]


def kept(house, cfg, room, name):
    """SPEC-v3.5.8 §4: a made thing kept for meaning, never scrap: an heirloom, a statue, a first, a gift, a thing
    the visitor named or starred, or anything in a keepsake box."""
    o = room["objects"][name]
    m = o["made"]
    return bool(m.get("heirloom") or m.get("called") or m.get("star") is not None or m.get("first") or (m["by"], m["tick"]) in firsts_of(house)
                or m["by"] != m["owner"] or statue(name, o) or keeps(o) or (o.get("on") and keeps(room["objects"].get(o["on"], {}))))


def scrap(house, cfg, room, name, newest=None):
    """SPEC-v3.5.8 §4: why a made thing is scrap, or None. A pet keeps only its few newest charms; the rest are scrap,
    on a shelf, a wall or the floor. Any other made thing nobody has used in `scrap_days` is scrap too. Never what is
    kept (above), a tool, a place things are kept in, what has things in it, what is planted, what is too heavy to
    move, a lit light, or a bed-thing where someone sleeps. `newest`: {owner: ticks of its newest charms}, if known."""
    o, M = room["objects"][name], cfg["make"]
    if "made" not in o or kept(house, cfg, room, name) or held(room, name) or o.get("planted") or cap(cfg, o) or things.prop(cfg, o).get("fixed"):
        return None
    kind = o["made"]["recipe"].get("kind")
    if kind in cfg["craft"]["tool"] or cfg["kinds"].get(kind, {}).get("tool") or (o.get("state") == "on" and things.prop(cfg, o).get("light")):
        return None
    if kind in KEEP["sleeping corner"] and any(p.get("sleeps_in") == room["id"] and dist(p.get("sleeps_at") or p["pos"], o["pos"]) <= 1
                                               for p in house["pets"].values() if p["stage"] not in ("egg", "dead")):
        return None
    if kind == "charm":
        newest = newest if newest is not None else newest_charms(house, cfg)
        return "charm" if o["made"]["tick"] not in newest.get(o["made"]["owner"], ()) else None
    return "unused" if world_days(cfg, last_touch(o), house["tick"]) >= M["scrap_days"] else None


def newest_charms(house, cfg):
    """{owner: the ticks its newest `charms` charms were made}."""
    out = {}
    for r in house["rooms"].values():
        for o in things.made(r).values() if r["type"] else ():
            if o["made"]["recipe"].get("kind") == "charm":
                out.setdefault(o["made"]["owner"], []).append(o["made"]["tick"])
    return {k: set(sorted(v)[-cfg["make"]["charms"]:]) for k, v in out.items()}


def scraps(house, cfg, room):
    """The scrap in a room, charms first, then the longest untouched: [(why, name)]."""
    newest = newest_charms(house, cfg)
    out = [(why, n) for n in things.made(room) for why in [scrap(house, cfg, room, n, newest)] if why]
    return sorted(out, key=lambda x: (x[0] != "charm", last_touch(room["objects"][x[1]])))


def old(house, cfg, room, name):
    """Left lying: a made thing nobody has touched for `old_days`, that is not an heirloom, not up on a wall, not put
    away on anything, not itself a place where things are kept, and not too heavy to be moved."""
    o = room["objects"][name]
    return not o["made"].get("heirloom") and not o.get("on") and not o.get("wall") and not cap(cfg, o) and not things.prop(cfg, o).get("fixed") \
        and world_days(cfg, last_touch(o), house["tick"]) >= cfg["order"]["old_days"]


def box_of(house, pid):
    """(room, name) of the keepsake box of someone who has died, or None while it has none."""
    return next(((r, n) for r in house["rooms"].values() if r["type"] for n, o in r.get("objects", {}).items() if keeps(o) == pid), None)


def give_box(house, cfg, room, stone):
    """A keepsake box beside a memorial stone (12 October 2026): what the one it is for left lying about is kept in
    it. It has no limit, what is in it is put away like anything on a shelf, and it can be taken out again."""
    if not box_of(house, room["objects"][stone]["memorial"]["pet"]):
        room["objects"][stone.replace("stone for", "keepsake box for", 1)] = {
            "pos": free_tile(house, cfg, room, room["objects"][stone]["pos"]), "fix": {"store": BOX, "inside": True, "keepsake": room["objects"][stone]["memorial"]["pet"]}}


def into_box(house, room, name):
    """A made thing goes into its dead owner's keepsake box, wherever in the house that is. False if there is none."""
    o = room["objects"][name]
    to, box = box_of(house, o["made"]["owner"]) or (None, None)
    if not to or (to is not room and name in to["objects"]):
        return False
    del room["objects"][name]
    for k in ("wall", "tidy", "home", "places"):
        o.pop(k, None)
    o["on"], o["pos"] = box, list(to["objects"][box]["pos"])   # being put by is not being wanted: it stays as long untouched as it was
    to["objects"][name] = o
    for m in [m for m in room.get("marks", []) if m["on"] == name] if room is not to else []:   # what is written on a thing goes where the thing goes
        room["marks"].remove(m)
        to.setdefault("marks", []).append(m)
    return True


def keep(house, cfg):
    """Every hour (12 October 2026, in place of the storeroom and wearing out: nothing made wears out): what someone
    who has died left lying about, untouched for `old_days`, goes into the keepsake box by its stone. The living's
    things stay where they are however long untouched, things on walls stay up, and no heirloom is moved."""
    went = {}
    for room in [r for r in house["rooms"].values() if r["type"]]:
        clutter = clutter_of(house, cfg, room)
        for n, o in list(things.made(room).items()):
            if (old(house, cfg, room, n) or n in clutter) and into_box(house, room, n):   # (SPEC-v3.5.4 §1: and sooner from a cluttered room)
                went.setdefault(o["made"]["owner"], []).append(n)
        room["areas"] = areas(house, cfg, room)
    for pid, names in went.items():
        to, box = box_of(house, pid)
        moment(house, "kept", "what %s left lying about went into the %s: %s" % (label(house["pets"][pid]), box, ", ".join(names[:4]) + (" and %d more" % (len(names) - 4) if len(names) > 4 else "")), None, to["id"])


def way(house, cfg, pet):
    """The door from where it is toward the nearest mess it knows of where there is something it could put away,
    through rooms it knows: a door, or None. (A mess with nowhere left to put things is no reason to go: two of
    those used to send a tidying pet back and forth between them.)"""
    rooms, seen, queue = house["rooms"], {pet["room"]}, [(pet["room"], None)]
    while queue:
        rid, first = queue.pop(0)
        if first and rooms[rid].get("mess") == 2 and job(house, cfg, pet, rooms[rid]):
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
    """A tile where this thing would be one of a corner (`corners`) that still has room for it: or None, when there
    is no such corner here, it is full, or there is no free tile by it. (A thing whose home is a shelf or a box
    belongs there, not in a corner.)"""
    o, floor = room["objects"][name], things.on_floor(room)
    area = next((a for a, ks in KEEP.items() if o["made"]["recipe"].get("kind") in ks), None)
    if not area or o.get("home"):
        return None
    now = corners(house, cfg, room).get(area, [])
    if area == "sleeping corner":   # against a wall, one bed-thing for each pet who sleeps here
        if len(now) >= min(MOST, sleepers(house, room)):
            return None
        used, by = taken(house, room, name), floor[now[0]]["pos"] if now else o["pos"]
        tiles = [[x, y] for x in range(cfg["W"]) for y in range(cfg["H"]) if edge(cfg, [x, y]) and [x, y] not in used and (not now or dist([x, y], by) <= 2)]
        return min(tiles, key=lambda t: (dist(t, by), t), default=None)
    group = [n for n, x in floor.items() if n != name and x["made"]["recipe"].get("kind") in KEEP[area] and not x.get("home")]
    if len(group) < 2:
        return None
    best = now[0] if now else max(group, key=lambda a: sum(dist(floor[a]["pos"], floor[x]["pos"]) <= 2 for x in group))
    if len(now) >= MOST or dist(o["pos"], floor[best]["pos"]) <= 2:
        return None
    tile = free_tile(house, cfg, room, floor[best]["pos"], name)
    return tile if dist(tile, floor[best]["pos"]) <= 2 else None


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
            tile = free_tile(house, cfg, room, home["pos"], name)
            if dist(home["pos"], tile) <= 1:   # (no free tile by its stone: it is put somewhere else rather than moved about for ever)
                return "at", tile
    box = box_of(house, o["made"]["owner"])
    if box and box[0] is room and not o["made"].get("heirloom"):   # what someone who died left, out of its box in the room the box stands in (SPEC-v3.4: a body may take it out to look at): back in it
        return "on", box[1]
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
    """Something for a tidy pet to do here, the nearer of: a loose thing with somewhere to go, a pawful of loose
    bits to put in something. {what, job: [kind, name, how, place], pos}, or None when there is nowhere to put
    anything."""
    out, objs = [], room["objects"]
    fresh = house["tick"] - ticks(cfg, cfg["order"]["just_out_seconds"])   # what has only just been taken out, brought over or rolled across is left a while
    clear = [n for n in clutter_of(house, cfg, room) if not objs[n].get("on")]   # SPEC-v3.5.4 §1: a crowded room's old things go into a box or onto a shelf here, by whoever is about
    # ponytail: only into what keeps things in this room; a crowded room with none of it free waits for the machine (its owners), boxes elsewhere if that falls short
    for n in [n for n in loose(house, cfg, room) + [n for n in clear if n not in loose(house, cfg, room)] if objs[n].get("kept", -10 ** 9) <= fresh]:   # anyone may put anyone's thing in its place here: it stays its owner's, in the same room
        where = place_for(house, cfg, pet, room, n)
        if where:
            out.append({"what": n, "job": ["thing", n, where[0], where[1]], "pos": objs[n]["pos"], "bonus": cfg["order"]["clear_pull"] if n in clear else 0.0})
    bits, space = loose_bits(room), {n: k for n, k in bit_room(cfg, room).items() if k > 0}
    if bits and space:
        first = min(bits, key=lambda s: dist(s["pos"], pet["pos"]))
        out.append({"what": "loose bits" if len(bits) > 1 else "loose %s" % first["bit"], "pos": first["pos"],
                    "job": ["bits", None, "on", min(space, key=lambda n: dist(objs[n]["pos"], first["pos"]))]})
    back = lambda j: j["job"][0] == "thing" and bool(objs[j["job"][1]].get("home", {}).get("on") or (j["job"][2] == "on" and keeps(objs[j["job"][3]])))
    return min(out, key=lambda j: (not back(j), dist(j["pos"], pet["pos"])), default=None)   # what has a home on a shelf or in a box, or belongs in a keepsake box, goes back first


def do_job(house, cfg, pet, room, job):
    """Carry out what `job` found. Returns where it went, in the pet's words, or "" if it could no longer be done."""
    kind, name, how, place = job
    if kind == "bits":
        took = sorted((s for s in loose_bits(room) if not name or s["bit"] in name), key=lambda s: dist(s["pos"], pet["pos"]))[:max(0, min(cfg["order"]["pawful"], bit_room(cfg, room).get(place, 0)))]   # (`name`: only these bits; SPEC-v3.5 §5, food put by)
        for s in took:
            s["on"], s["pos"] = place, list(room["objects"][place]["pos"])
        from . import season
        season.stored(house, cfg, pet, room, took, place)   # SPEC-v3.5 §5: food put away in something is put by, and keeps
        return into(cfg, room, place) if took else ""
    o = room["objects"].get(name)
    if not o or "made" not in o or o.get("on"):
        return ""
    if how == "on" and (place not in room["objects"] or (stores(cfg, room).get(place, 0) <= 0 and not keeps(room["objects"][place]))):
        return ""
    said, owner = put(house, cfg, pet, room, name, how, place), house["pets"].get(o["made"]["owner"])
    if owner and owner is not pet and owner["stage"] != "dead":
        add_event(house, owner, "your %s was put %s" % (name, said))
    return said


def stow(cfg, room, bits):
    """Bits put straight into whatever keeps things here, crates and the like first. Returns those nothing had room for."""
    left = []
    for b in bits:
        space = sorted((n for n, k in bit_room(cfg, room).items() if k > 0), key=lambda n: not inside(cfg, room["objects"][n]))
        if space:
            room["spots"].append({"bit": b, "pos": list(room["objects"][space[0]]["pos"]), "ready": True, "back": None, "loose": True, "on": space[0]})
        else:
            left.append(b)
    return left


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
        said = "by its stone" if o["made"].get("heirloom") else "in the sleeping corner" if o["made"]["recipe"].get("kind") in KEEP["sleeping corner"] else "with the others like it"
    room["areas"] = areas(house, cfg, room)
    return said


def check(a, house, cfg, pet, norm):
    """put_away, take_out, hang: None if it can happen now, else why not."""
    room, t = house["rooms"][pet["room"]], a.get("type")
    name = norm(a.get("what"))
    o = room["objects"].get(name)
    if not o or "made" not in o:
        return "that is not a made thing here"
    if t == "take_out":   # taking out is taking: its own, nobody's, the dead's (so anything in a keepsake box), its children's
        return "that belongs to someone else" if not may_move(house, pet, o) else None if o.get("on") else "it is not put away"
    if t == "hang":
        if not cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("hangs"):
            return "that is not a thing to hang up"
        return None if not o.get("wall") and things.wall_slot(house, room) else "there is no free place on the wall here"
    where = norm(a.get("where"))
    if where not in room["objects"] or not cap(cfg, room["objects"][where]) or where == name:
        return "there is nowhere like that here to keep things"
    if keeps(room["objects"][where]):
        return None if o["made"]["owner"] == keeps(room["objects"][where]) else "that box is only for what the one it is for left behind"
    return None if stores(cfg, room)[where] > 0 else "the %s is full" % where


def do(a, house, cfg, pet, norm):
    room, t, name = house["rooms"][pet["room"]], a["type"], norm(a["what"])
    o = room["objects"][name]
    if t == "take_out":
        was, o["kept"] = o.pop("on"), house["tick"]
        o["pos"] = free_tile(house, cfg, room, pet["pos"], name)
        if not o.get("home"):   # where it was kept is where it belongs: out, it lies about until it is put back
            o["home"] = {"room": room["id"], "on": was}
        return "you took the %s down from the %s" % (name, was), {}, None
    said = put(house, cfg, pet, room, name, "wall", things.wall_slot(house, room)) if t == "hang" else put(house, cfg, pet, room, name, "on", norm(a["where"]))
    things.noted(house, pet, o, "set down")   # SPEC-v3.5.8: what it had in mind as it put it there
    owner = house["pets"].get(o["made"]["owner"])
    if owner and owner is not pet and owner["stage"] != "dead":   # anyone may put anyone's thing in its place here, as a body does (do_job); its owner is told
        add_event(house, owner, "your %s was put %s" % (name, said))
    return "you %s the %s %s" % ("hung" if t == "hang" else "put", name, said), {}, "put away"


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


KEEP = {"sleeping corner": ("cushion", "blanket", "nest", "bed-mat"), "music corner": ("bell", "drum", "flute", "wind chime"),
        "lamp corner": ("candle", "lantern", "lamp")}
MOST = 4   # a corner is never more than this many tiles: it does not swallow the room


def sleepers(house, room):
    """How many of the living sleep here: each where it last lay down to sleep."""
    return sum(1 for p in house["pets"].values() if p["stage"] not in ("egg", "dead") and p.get("sleeps_in") == room["id"])


def edge(cfg, pos):
    """Is this tile against a wall?"""
    return pos[0] in (0, cfg["W"] - 1) or pos[1] in (0, cfg["H"] - 1)


def corners(house, cfg, room):
    """{corner: [things]}, the one the rest stand round first (13 October 2026: a corner used to grow until it was
    the room). A corner is at most MOST things, each on its own tile. Three or more instruments or lights standing
    together are one. A sleeping corner is against a wall and holds one bed-thing for each pet who sleeps here; a
    room nobody sleeps in has none. Whatever else of the sort stands about is clutter, to be stacked away. A thing
    with a home (a shelf, a box, an heirloom's place by its stone) is never one of a corner: it belongs there."""
    out, floor = {}, things.on_floor(room)
    for area, kinds in KEEP.items():
        bed = area == "sleeping corner"
        most = min(MOST, sleepers(house, room)) if bed else MOST
        group = [n for n, o in floor.items() if o["made"]["recipe"].get("kind") in kinds and not o.get("home") and (not bed or edge(cfg, o["pos"]))]
        near = lambda n: sorted((m for m in group if dist(floor[m]["pos"], floor[n]["pos"]) <= 2), key=lambda m: dist(floor[m]["pos"], floor[n]["pos"]))[:most]
        best = max((near(n) for n in group), key=len, default=[])
        if most and len(best) >= (1 if bed else 3):
            out[area] = best
    return out


def areas(house, cfg, room):
    """Name the places a room has grown (§2.3): its corners, any shelf of heirlooms, and a bench in use. [{name,
    tiles}] for the view's faint tint and the hover cards; recomputed now and then."""
    made = things.made(room)
    out = [{"name": area, "tiles": [list(made[n]["pos"]) for n in names]} for area, names in corners(house, cfg, room).items()]
    for store in {o.get("on") for o in made.values() if o.get("on") and o["made"].get("heirloom")}:
        out.append({"name": "keepsake shelf", "tiles": [list(room["objects"][store]["pos"])], "on": store})
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
