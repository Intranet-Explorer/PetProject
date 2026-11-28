"""Floors that stay clear (SPEC-v3.6c §1). The middle of every room is kept clear: a made thing is set down on a shelf,
in a box or on a table, else on a free tile against a wall, never in the middle; only what is for the middle (a rug,
a table, a statue on its plinth) stands there. Whatever ends up in the middle, whoever or whatever put it there, is
moved to the nearest good spot on the same tick (order.upkeep runs this), so nothing else has to remember. After dusk,
what was left out that day goes to the store: one line in the story. The layout check (once, in the clear-out) moves
built things that stand in the middle to the nearest wall, unless they are for the middle. Switch: [clearout] floors."""
from . import items, order, things
from .world import DIRS, dist, moment, taken

FOR_MIDDLE = {"rug", "table"}   # made kinds placed in the middle on purpose
BUILT_MIDDLE = {"table", "statue", "foundling's statue", "bed frame"}   # building projects that are for the middle (a table, a bed; statues on their plinths)


def on(cfg):
    return cfg.get("clearout", {}).get("floors", False)


def middle(cfg, pos):
    """Is this tile in the middle of a room: two or more tiles from every wall? (A room is 12 x 8: the middle is the
    8 x 4 tiles at its heart; the ring of two tiles round it is "against a wall".)"""
    return 2 <= pos[0] <= cfg["W"] - 3 and 2 <= pos[1] <= cfg["H"] - 3


def door_path(house, cfg, room):
    """The tiles kept open at each door: the doorway, the tile in from it, and the two beside it along the wall."""
    out = []
    for d in room["doors"]:
        x, y = house["door_tiles"][d]
        dx, dy = DIRS[d]
        out += [[x, y], [x - dx, y - dy], [x + dy, y + dx], [x - dy, y - dx]]
    return out


def for_middle(cfg, o):
    if "made" in o:
        return o["made"]["recipe"].get("kind") in FOR_MIDDLE
    return ((o.get("fix", {}).get("built") or {}).get("project") in BUILT_MIDDLE) or "memorial" in o


def spot(house, cfg, room, near, but=None):
    """The nearest free tile against a wall (the ring next to it first, then the one inside it), off the doors' paths,
    or None when there is none."""
    used = taken(house, room, but) + door_path(house, cfg, room)
    tiles = [[x, y] for x in range(cfg["W"]) for y in range(cfg["H"]) if not middle(cfg, [x, y]) and [x, y] not in used]
    return min(tiles, key=lambda t: (not order.edge(cfg, t), dist(t, near), abs(t[0] - near[0]) + abs(t[1] - near[1])), default=None)


def put_down(house, cfg, room, name, o, near):
    """Set a made thing down at its nearest good spot: something here that keeps things and has room (not if it keeps
    things itself), else a free tile against a wall. False when there is nowhere, and it stays where it is."""
    if not order.cap(cfg, o):
        left = {n: k for n, k in order.stores(cfg, room).items() if k > 0 and n != name}
        near_store = min(left, key=lambda n: dist(room["objects"][n]["pos"], near), default=None)
        if near_store and dist(room["objects"][near_store]["pos"], near) <= 3:
            items.place(house, cfg, room, name, o, near_store)
            o["pos"] = list(room["objects"][near_store]["pos"])
            return True
    t = spot(house, cfg, room, near, name)
    if t is None:
        return False
    o["pos"] = t
    return True


def keep_clear(house, cfg):
    """Every made thing standing in the middle of a room, but what is for the middle, goes to its nearest good spot."""
    if not on(cfg):
        return
    for room in house["rooms"].values():
        if not room["type"]:
            continue
        for n, o in list(things.on_floor(room).items()):
            if middle(cfg, o["pos"]) and not for_middle(cfg, o):
                put_down(house, cfg, room, n, o, o["pos"])


def in_middle(house, cfg):
    """{room name: [made things standing in its middle that are not for it]}: the bar (SPEC-v3.6c §0)."""
    return {r["name"]: [n for n, o in things.on_floor(r).items() if middle(cfg, o["pos"]) and not for_middle(cfg, o)]
            for r in house["rooms"].values() if r["type"]}


def loose(house, cfg):
    """Made things lying loose on floors outside the store, house-wide: on the floor (not on a wall, not on or in
    anything), and not furniture or a box standing there. The bar: at most 30."""
    from . import store
    return sum(1 for r in house["rooms"].values() if r["type"] and not store.is_store(r) for o in things.on_floor(r).values()
               if not cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("furniture") and not order.cap(cfg, o))


# ---- the evening tidy ----

def left_out(house, cfg, room):
    """What was left out in this room: made things on the floor that the room does not keep for itself (store.stays,
    but a thing used today is no reason to stay out for the night). Outdoors, everything made that does not stand there."""
    from . import store
    out = []
    for n, o in things.on_floor(room).items():
        why = store.stays(house, cfg, room, n)
        if room.get("outdoor"):
            if why != "furniture" and not o["made"].get("design", {}).get("big"):
                out.append(n)
        elif why in (None, "in use") and not order.cap(cfg, o):
            out.append(n)
    return out


def tidy(house, cfg):
    """After dusk, once a day: what was left out goes to the store (the train takes it; what the store has no room for
    makes room as the store always does). One line in the story, not one per thing."""
    from . import rail, store
    if not on(cfg) or house["clock"]["phase"] != "dusk" or house.get("tidied") == house["clock"]["day"]:
        return
    house["tidied"] = house["clock"]["day"]
    shop = house["rooms"].get(store.RID)
    if not shop or not shop["type"]:
        return
    went = 0
    for room in house["rooms"].values():
        if not room["type"] or store.is_store(room):
            continue
        for n in left_out(house, cfg, room):
            o = room["objects"].pop(n)
            items.place(house, cfg, room, n, o)
            if store.put(house, cfg, shop, n, o):
                o["moved"] = {"tick": house["tick"], "from": room["id"], "why": "the evening tidy"}
                went += 1
            else:
                room["objects"][n] = o   # (the store is full even after making room: it stays out tonight)
    if went:
        moment(house, "tidy", "the house was tidied for the night: %d things put away in the store" % went, None, store.RID)
        if house.get("rail") and rail.train(house):
            rail.log(house, store.RID, "the evening tidy: %d things to the store" % went)


# ---- the layout check (once, in the clear-out) ----

def layout_check(house, cfg, room):
    """Built things that stand in the middle move to the nearest wall, unless they are for the middle; machines and what
    is fixed in place stay. Returns the names moved."""
    from . import build, machines
    moved = []
    for n, o in room["objects"].items():
        rec = (o.get("fix") or {}).get("built")
        P = build.PROJECT.get(rec.get("project"), {}) if rec else {}
        if not rec or "pos" not in o or o.get("wall") or not middle(cfg, o["pos"]) or for_middle(cfg, o) or machines.key_of(o) or P.get("exact") or P.get("on") or P.get("wall"):
            continue
        t = spot(house, cfg, room, o["pos"], n)
        if t:
            o["pos"] = t
            moved.append(n)
    return moved
