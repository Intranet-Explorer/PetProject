"""Order (SPEC-v3.3 §2): places to keep things, homes for things, and how much of a mess a room is. A thing put on
a shelf or in a chest is still the same thing, in the same room, doing whatever it does; it only stops lying on the
floor. Tidying is real: it moves things, and a thing put in the same place twice has a home there."""
from . import things
from .world import dist, free_tile, label, moment

MESS = ["everything here has its place", "a few things lie about", "this room is a mess"]


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


def settled(cfg, o):
    """Is a made thing where it belongs: on something, on the wall, in its home, set straight by someone, itself a
    place to keep things, or too heavy to be anywhere else?"""
    return bool(o.get("on") or o.get("wall") or o.get("tidy") or cap(cfg, o) or things.prop(cfg, o).get("fixed")
                or (o.get("home") and o["home"].get("pos") == o["pos"]))


def loose(house, cfg, room):
    """The made things lying about on the floor."""
    return [n for n, o in things.made(room).items() if not settled(cfg, o)]


def clutter(house, cfg, room):
    """0 tidy, 1 a few things about, 2 a mess: what lies loose (made things and dropped bits) against a room's size."""
    n = len(loose(house, cfg, room)) + sum(1 for s in room["spots"] if s["loose"] and s["ready"] and not s.get("tidy")) / 2
    O = cfg["order"]
    return 0 if n <= O["tidy_below"] else 1 if n <= O["mess_above"] else 2


def may_move(house, pet, o):
    """Its own things, nobody's, the dead's, and its young children's: tidying is not taking."""
    return things.free_to_change(house, pet, o) or house["pets"].get(o["made"]["owner"], {}).get("parent") == pet["id"]


def place_for(house, cfg, pet, room, name):
    """Where a thing belongs: its home if it has one here, else the nearest place that keeps things and has room,
    else a tile beside others like it along the wall. Returns ("on", storage) or ("at", tile), or None."""
    o = room["objects"][name]
    home, left = o.get("home"), stores(cfg, room)
    if home and home.get("room") == room["id"]:
        if home.get("on") and left.get(home["on"], 0) > 0:
            return "on", home["on"]
        if home.get("pos") and home["pos"] != o["pos"]:
            return "at", free_tile(house, cfg, room, home["pos"], name)
    if can_hang(cfg, o) and things.wall_slot(house, room):
        return "wall", things.wall_slot(house, room)
    free = [n for n, k in left.items() if k > 0 and n != name]
    if free:
        return "on", min(free, key=lambda n: dist(room["objects"][n]["pos"], o["pos"]))
    like = [x for n, x in things.made(room).items() if n != name and settled(cfg, x) and not x.get("on") and not x.get("wall")
            and x["made"]["recipe"].get("kind") == o["made"]["recipe"].get("kind")]
    near = min(like, key=lambda x: dist(x["pos"], o["pos"]))["pos"] if like else [o["pos"][0], 0 if o["pos"][1] < cfg["H"] / 2 else cfg["H"] - 1]
    return "at", free_tile(house, cfg, room, near, name)


def job(house, cfg, pet, room):
    """Something for a tidy pet to do here: (the thing, where it goes), or None when there is nothing loose it may move."""
    mine = [n for n in loose(house, cfg, room) if may_move(house, pet, room["objects"][n])]
    if not mine:
        return None
    name = min(mine, key=lambda n: dist(room["objects"][n]["pos"], pet["pos"]))
    where = place_for(house, cfg, pet, room, name)
    return (name, where) if where else None


def remember(o, room, how, where):
    """A thing put in the same place twice has a home there (§2.3)."""
    key = "%s|%s" % (how, where if how == "on" else "%d,%d" % tuple(where))
    seen = o.setdefault("places", {})
    seen[key] = seen.get(key, 0) + 1
    if seen[key] >= 2 and not (o["made"].get("heirloom") and o.get("home")):
        o["home"] = {"room": room["id"], **({"on": where} if how == "on" else {"pos": list(where)})}


def put(house, cfg, pet, room, name, how, where):
    """Put a thing in its place. Returns how the pet would say where it went."""
    o = room["objects"][name]
    o.pop("on", None)
    o.pop("tidy", None)
    if how == "on":
        o["on"], o["pos"] = where, list(room["objects"][where]["pos"])
        said = "on the %s" % where if not cfg["kinds"].get(room["objects"][where].get("made", {}).get("recipe", {}).get("kind"), {}).get("inside") \
            and not room["objects"][where].get("fix", {}).get("inside") else "in the %s" % where
    elif how == "wall":
        o["wall"], o["pos"] = True, list(where)
        said = "up on the wall"
    else:
        o["pos"], o["tidy"] = list(where), house["tick"]
        said = "in its place" if o.get("home", {}).get("pos") == list(where) else "out of the way"
    if how != "wall":
        remember(o, room, how, where)
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
        was = o.pop("on")
        o["pos"] = free_tile(house, cfg, room, pet["pos"], name)
        return "you took the %s down from the %s" % (name, was), {}, None
    if t == "hang":
        said = put(house, cfg, pet, room, name, "wall", things.wall_slot(house, room))
        return "you hung the %s %s" % (name, said), {}, "put away"
    said = put(house, cfg, pet, room, name, "on", norm(a["where"]))
    return "you put the %s %s" % (name, said), {}, "put away"


def moved(o):
    """A thing carried off somewhere else is no longer on its shelf."""
    o.pop("on", None)
    o.pop("tidy", None)


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
