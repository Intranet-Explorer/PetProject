"""A resting place (SPEC-v3.5.12 §4): the stones of the dead stand together in a quiet corner of the garden, family by
family, and their keepsake boxes stand on their family's memory shelf in the attic. A house lived in before is moved
once, by the hobs over the first world day after it comes (every move is a moment); from then on a new stone goes to
the resting place and a new keepsake box to its family's shelf. Numbers in house.toml [resting]."""
from . import order
from .world import add_event, family, free_tile, label, moment

BOX = order.BOX


def R(cfg):
    return cfg["house"]["resting"]


def room_of(house, kind):
    return next((r for r in house["rooms"].values() if r["type"] == kind), None)


def tiles(house, cfg):
    """The resting place's tiles in the garden (laid once, kept in house["resting"]), or []."""
    rest = house.get("resting")
    if rest:
        return rest["tiles"]
    g = room_of(house, "garden")
    if not g:
        return []
    L = cfg.get("layouts", {}).get("garden") or {}
    grows = {tuple(t) for ts in (L.get("bit_spots") or {}).values() for t in ts} | {tuple(s["pos"]) for s in g["spots"] if not s["loose"]}
    bad = {tuple(o["pos"]) for o in g["objects"].values() if "fix" in o and not o.get("wall")} | {tuple(t) for t in g.get("blocked", [])} | grows
    bad |= {tuple(house["door_tiles"][d]) for d in g["doors"]}
    x0, y0, x1, y1 = R(cfg)["corner"]
    out = [[x, y] for y in range(y1, y0 - 1, -1) for x in range(x0, x1 + 1) if (x, y) not in bad]
    house["resting"] = {"room": g["id"], "tiles": out, "moving": [], "began": None}
    return out


def founder(house, fam):
    return min((p for p in house["pets"].values() if family(p) == fam), key=lambda p: (p["parent"] is not None, p["born"] or 0), default=None)


def shelf(house, cfg, fam):
    """Its family's memory shelf in the attic, put up the first time it is needed: (room, name), or (None, None)."""
    from . import world
    a = room_of(house, "attic")
    if not a:
        return None, None
    f = founder(house, fam)
    name = ("memory shelf for %s's family" % label(f)).lower() if f else "memory shelf"
    if name not in a["objects"]:
        spots = R(cfg)["shelves"]
        used = {tuple(o["pos"]) for o in a["objects"].values() if o.get("fix", {}).get("memory")}
        pos = next((p for p in spots if tuple(p) not in used), spots[-1])
        a["objects"][name] = world.fixture({"name": name, "pos": pos, "store": BOX, "inside": False, "memory": label(f) if f else "the family",
                                            "art": "family memory shelf with candles and keepsake boxes"})
        for n, o in a["objects"].items():   # nothing is left standing where the shelf now stands
            if n != name and "fix" not in o and not o.get("on") and not o.get("wall") and o["pos"] == list(pos):
                o["pos"] = free_tile(house, cfg, a, o["pos"], n)
    return a, name


def at_rest(house, room, name):
    """Is this stone in the resting place, or this keepsake box on a memory shelf?"""
    o = room["objects"][name]
    if "memorial" in o:
        rest = house.get("resting") or {}
        return room["id"] == rest.get("room") and o["pos"] in rest.get("tiles", [])
    return bool(order.keeps(o)) and room["type"] == "attic" and bool(room["objects"].get(o.get("on") or "", {}).get("fix", {}).get("memory"))


def stone_tile(house, cfg, fam):
    """A free tile in the resting place, beside its family's other stones if it has any."""
    g = house["rooms"][house["resting"]["room"]]
    taken = {tuple(o["pos"]) for o in g["objects"].values() if not o.get("on") and not o.get("wall")}
    free = [t for t in tiles(house, cfg) if tuple(t) not in taken]
    kin = [o["pos"] for o in g["objects"].values() if "memorial" in o and family(house["pets"].get(o["memorial"]["pet"]) or {}) == fam]
    if not free:
        return free_tile(house, cfg, g, tiles(house, cfg)[0] if tiles(house, cfg) else [2, 5])
    return min(free, key=lambda t: (min((abs(t[0] - k[0]) + abs(t[1] - k[1]) for k in kin), default=0), free.index(t)))


def free_name(room, name):
    """`name`, or, when something there is already called that (two of the dead shared a name), "the other ..." and
    then "another ..." (never a number)."""
    for n in [name] + ["the other " + name, "another " + name] + ["%s %s" % (w, name) for w in ("an older", "a quieter", "a smaller", "a far")]:
        if n not in room["objects"]:
            return n
    return name + ", again"


def move_stone(house, cfg, room, name):
    """A stone to the resting place: (garden, its name there)."""
    o = room["objects"].pop(name)
    g = house["rooms"][house["resting"]["room"]]
    dead = house["pets"].get(o["memorial"]["pet"]) or {}
    o["pos"] = stone_tile(house, cfg, family(dead))
    new = free_name(g, name)
    g["objects"][new] = o
    for m in [m for m in room.get("marks", []) if m["on"] == name]:   # what is written on it goes with it
        room["marks"].remove(m)
        g.setdefault("marks", []).append(dict(m, on=new))
    return g, new


def move_box(house, cfg, room, name):
    """A keepsake box, with what is in it, onto its family's memory shelf in the attic."""
    box = room["objects"][name]
    dead = house["pets"].get(order.keeps(box)) or {}
    a, sh = shelf(house, cfg, family(dead))
    if not a:
        return None, None
    inside = [n for n, o in room["objects"].items() if o.get("on") == name]
    room["objects"].pop(name)
    box.update(on=sh, pos=list(a["objects"][sh]["pos"]))
    new = free_name(a, name)
    a["objects"][new] = box
    for n in inside:
        o = room["objects"].pop(n)
        o["pos"], o["on"] = list(box["pos"]), new
        if o.get("home", {}).get("on") == name:
            o["home"] = {"room": a["id"], "on": new}
        a["objects"][n] = o
        for m in [m for m in room.get("marks", []) if m["on"] == n]:
            room["marks"].remove(m)
            a.setdefault("marks", []).append(m)
    for s in [s for s in room["spots"] if s.get("on") == name]:
        room["spots"].remove(s)
        a["spots"].append(dict(s, pos=list(box["pos"]), on=new))
    return a, new


def migrate(house, cfg):
    """On load: once, the moving of every stone and keepsake box that is not yet at rest is set going (`tick` carries
    it out over the first world day)."""
    if not R(cfg)["on"] or not room_of(house, "garden") or not room_of(house, "attic"):
        return
    tiles(house, cfg)
    rest = house["resting"]
    if rest.get("began") is not None:
        return
    rest["began"] = house["tick"]
    rest["moving"] = [[r["id"], n] for r in house["rooms"].values() if r["type"] for n, o in r["objects"].items()
                      if ("memorial" in o or order.keeps(o)) and not at_rest(house, r, n)]
    rest["moving"].sort(key=lambda m: ("keepsake" in m[1], m[1].replace("keepsake box for ", "").replace("stone for ", "")))
    if rest["moving"]:
        moment(house, "resting", "the family began to carry the stones of their dead to a quiet corner of the garden, and their keepsake boxes up to the attic", None, rest["room"])


def carrier(house, dead_id, rid):
    """Who carries it: a living, awake hob of the dead one's family, in that room first; else anyone awake."""
    dead = house["pets"].get(dead_id) or {}
    up = [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead", "hatchling") and not p["sleep"] and not p.get("riding")]
    return min(up, key=lambda p: (family(p) != family(dead), p["room"] != rid, p["id"]), default=None)


def tick(house, cfg):
    """Over the first world day, one stone or box at a time, each carried by a hob of the family if one is awake."""
    rest = house.get("resting")
    if not rest or not rest.get("moving"):
        return
    every = max(R(cfg)["least_ticks"], int(cfg["ticks_per_day"] * R(cfg)["over_days"] / max(1, len(rest["moving"]) + rest.get("moved", 0))))
    if house["tick"] - rest.get("last", rest["began"]) < every:
        return
    rid, name = rest["moving"][0]
    room = house["rooms"].get(rid)
    if not room or name not in room["objects"] or at_rest(house, room, name):
        rest["moving"].pop(0)
        return
    o = room["objects"][name]
    dead_id = o["memorial"]["pet"] if "memorial" in o else order.keeps(o)
    who = carrier(house, dead_id, rid)
    late = house["tick"] - rest["began"] >= cfg["ticks_per_day"] * R(cfg)["over_days"]
    if not who and not late:
        return   # (at night it waits for morning, unless the day is over: then the house sees it done)
    dead = house["pets"].get(dead_id) or {}
    kin = who and family(who) == family(dead)
    by = "%s and the family" % label(who) if kin else label(who) if who else "the family"
    if "memorial" in o:
        to, new = move_stone(house, cfg, room, name)
        text = "%s carried %s's stone to the garden, to rest with the others" % (by, label(dead))
    else:
        to, new = move_box(house, cfg, room, name)
        text = "%s carried %s's keepsake box up to the memory shelf in the attic" % (by, label(dead))
    rest["moving"].pop(0)
    rest["last"], rest["moved"] = house["tick"], rest.get("moved", 0) + 1
    if not to:
        return
    moment(house, "resting", text, who["id"] if who else None, to["id"])
    if who:
        add_event(house, who, "you helped carry %s's %s to %s" % (label(dead), "stone" if "memorial" in o else "keepsake box", "the resting place in the garden" if "memorial" in o else "the memory shelf in the attic"))
    if not rest["moving"]:
        for p in house["pets"].values():
            if p["stage"] not in ("egg", "dead"):
                add_event(house, p, "the stones of the family's dead stand together now in a quiet corner of the garden, and their keepsake boxes on a shelf in the attic")
        moment(house, "resting", "the stones of the dead all stand together now in the garden, and their keepsake boxes on the memory shelves in the attic", None, rest["room"])


def bury(house, cfg, room, stone):
    """A new stone goes straight to the resting place (once there is one), and its keepsake box onto the shelf."""
    if not R(cfg)["on"] or not house.get("resting") or not room_of(house, "attic"):
        order.give_box(house, cfg, room, stone)
        return
    g, stone = move_stone(house, cfg, room, stone)
    order.give_box(house, cfg, g, stone)
    box = order.box_of(house, g["objects"][stone]["memorial"]["pet"])
    if box:
        move_box(house, cfg, box[0], box[1])
