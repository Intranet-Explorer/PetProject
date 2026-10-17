"""The store (SPEC-v3.5.12 §1-2): the storeroom becomes the house's store, one place where everything kept but not in
use lives, sorted by kind on shelves, racks and crates along its walls (house.toml [store]); every other room keeps
what it is for (house.toml [rooms.*] `belongs`), what is in use, and a hob's sleeping things, and the rest goes to
the store by the train (rail.py). The hobs load it; the train carries it; the store's shelves take it by kind. A box
holding things counts as one thing; what is in it goes with it."""
from . import order, things
from .world import add_event, days as world_days, dist, free_tile, label, moment

RID = "r00"   # the storeroom


def is_store(room):
    return room["type"] == "storeroom"


def S(cfg):
    return cfg["house"]["store"]


def kind(o):
    return o["made"]["recipe"].get("kind") if "made" in o else None


def lay(house, cfg):
    """The store's shelves along the storeroom's walls (on load: safe to call again)."""
    from . import world
    room = house["rooms"].get(RID)
    if not room or not room["type"]:
        return
    for f in S(cfg)["shelf"]:
        if f["name"] not in room["objects"]:
            room["objects"][f["name"]] = world.fixture({k: v for k, v in f.items() if k != "keeps"})
            for n, o in room["objects"].items():   # nothing is left standing where a shelf now stands
                if n != f["name"] and "fix" not in o and not o.get("on") and not o.get("wall") and o["pos"] == f["pos"]:
                    o["pos"] = free_tile(house, cfg, room, o["pos"], n)


def shelf_for(house, cfg, room, o, but=None):
    """The store fixture this thing goes on: the one that keeps its kind and has room, else the one that keeps
    anything ("*"), else any store fixture here with room; or None when the store is full."""
    left = order.stores(cfg, room)
    k = kind(o)
    light = bool("made" in o and things.prop(cfg, o).get("light")) and k != "charm"
    for f in S(cfg)["shelf"]:
        if f["name"] != but and left.get(f["name"], 0) > 0 and (k in f["keeps"] or (light and "light" in f["keeps"])):
            return f["name"]
    for f in S(cfg)["shelf"]:
        if f["name"] != but and left.get(f["name"], 0) > 0 and "*" in f["keeps"]:
            return f["name"]
    return next((n for n, k_ in left.items() if k_ > 0 and n != but and not room["objects"][n].get("fix", {}).get("platform") and "made" not in room["objects"][n]), None)


def shelved(cfg, room, name):
    """Is this thing on one of the store's own fixtures (not in a box someone made, not on the platform)?"""
    o = room["objects"][name]
    on = room["objects"].get(o.get("on") or "")
    return bool(is_store(room) and on and "fix" in on and not on["fix"].get("platform") and not order.keeps(on))


def special(house, o):
    """Never sent to the Works from the store: firsts, heirlooms, titled things, gifts, the visitor's starred and named."""
    return order.meant(house, o) or bool(o["made"]["recipe"].get("title"))


def make_room(house, cfg, room):
    """The store is full: the oldest thing on its shelves nobody has used in `full_days`, that is not special, goes to
    the Works as scrap. True if one went."""
    from . import works
    old = [(order.last_touch(o), n) for n, o in things.made(room).items() if shelved(cfg, room, n) and not special(house, o)
           and world_days(cfg, order.last_touch(o), house["tick"]) >= S(cfg)["full_days"]]
    if not old:
        return False
    n = min(old)[1]
    o = room["objects"].pop(n)
    things.gone(house, o, n, "sent from the full store to the Works as scrap", room)
    works.fed(house, cfg, None, o)
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": "train", "room": room["id"], "pet": None, "what": "the full store sent %s to the Works" % n})
    return True


def put(house, cfg, room, name, o, by=None):
    """A thing onto its shelf in the store. False when there is no room even after the oldest has gone to the Works."""
    shelf = shelf_for(house, cfg, room, o)
    if not shelf and make_room(house, cfg, room):
        shelf = shelf_for(house, cfg, room, o)
    if not shelf:
        return False
    o.pop("wall", None)
    o.update(on=shelf, pos=list(room["objects"][shelf]["pos"]), kept=house["tick"])
    o["home"] = {"room": room["id"], "on": shelf}
    room["objects"][name] = o
    owner = house["pets"].get(o["made"]["owner"])
    if owner and owner["stage"] not in ("egg", "dead") and owner["id"] != by:
        add_event(house, owner, "your %s was put away in the store, %s the %s" % (name, "in" if order.inside(cfg, room["objects"][shelf]) else "on", shelf))
    return True


def unload(house, cfg, tr, room):
    """At the store: what the cart brought for it goes onto the right shelves; what does not fit stays in the cart."""
    from . import rail
    took = [h for h in tr["held"] if h["to"] == RID and not h.get("asked")]
    went = []
    for h in took:
        if put(house, cfg, room, h["name"], h["o"]):
            for m in h["o"].pop("marks", []):
                room.setdefault("marks", []).append(m)
            tr["held"].remove(h)
            went.append(h["name"])
    if went:
        rail.log(house, room["id"], "put away in the store: %s" % ", ".join(went))
        rail.seen(house, room["id"], "%s unloaded %d things into the store" % (rail.called(tr), len(went)))
        house["rail"]["done"]["stored"] = house["rail"]["done"].get("stored", 0) + len(went)


def fetch(house, cfg, tr, room):
    """What a hob has asked for from the store goes into the cart, for the room it asked in."""
    from . import rail
    for a in [a for a in house["rail"]["asked"] if not a.get("loaded")]:
        if a["name"] not in room["objects"] or len(tr["held"]) >= rail.R(cfg)["cart_holds"]:
            continue
        o = room["objects"].pop(a["name"])
        for k in ("on", "home"):
            o.pop(k, None)
        if a["room"] == room["id"]:   # asked for here, in the store itself: handed over at once
            room["objects"][a["name"]] = dict(o, pos=free_tile(house, cfg, room, house["rail"]["rooms"][room["id"]]["platform"]))
            house["rail"]["asked"].remove(a)
            continue
        tr["held"].append({"name": a["name"], "o": o, "to": a["room"], "from": room["id"], "asked": a["pet"]})
        a["loaded"] = house["tick"]
        rail.log(house, room["id"], "took %s from the store for %s" % (a["name"], house["rooms"][a["room"]]["name"]), a["pet"])


def where(house, cfg, room, name):
    """Where a made thing is, in plain words, for its card and the Things tab: ("in the store, on the lamp shelf",
    stored?)."""
    o, objs = room["objects"][name], room["objects"]
    on = objs.get(o.get("on")) if o.get("on") else None
    if on is not None:
        if order.keeps(on):
            dead = house["pets"].get(order.keeps(on))
            return "in %s keepsake box%s" % ("%s's" % label(dead) if dead else "a", ", on the %s in %s" % (on["on"], room["name"]) if on.get("on") else " in %s" % room["name"]), False
        if on.get("fix", {}).get("platform"):
            return "on the platform in %s, for the train" % room["name"], False
        if shelved(cfg, room, name):
            return "in the store, %s the %s" % ("in" if order.inside(cfg, on) else "on", o["on"]), True
        return "%s the %s in %s" % ("in" if order.inside(cfg, on) else "on", o["on"], room["name"]), False
    if o.get("wall"):
        return "on the wall of %s" % room["name"], False
    return "on the floor of %s" % room["name"], False


# ---- asking for a thing ----

def stock(house, cfg):
    """{kind: [names]} of what is on the store's shelves."""
    room = house["rooms"].get(RID)
    out = {}
    for n, o in things.made(room).items() if room and room["type"] else ():
        if shelved(cfg, room, n):
            out.setdefault(kind(o), []).append(n)
    return out


def find(house, cfg, what):
    """The stored thing a hob means by `what`: its name, or a thing of that kind (the one used last)."""
    room = house["rooms"].get(RID)
    if not room or not room["type"] or not what:
        return None
    asked = {a["name"] for a in (house.get("rail") or {}).get("asked", [])}
    if what in room["objects"] and shelved(cfg, room, what) and what not in asked:
        return what
    of = [n for n in stock(house, cfg).get(what.split()[-1], []) + stock(house, cfg).get(what, []) if n not in asked]
    return max(of, key=lambda n: order.last_touch(room["objects"][n]), default=None)


def ask(house, cfg, pet, what):
    """It asks the train to bring a thing from the store to its room's platform. Returns what it is told."""
    name = find(house, cfg, what)
    house["rail"]["asked"].append({"pet": pet["id"], "name": name, "room": pet["room"], "tick": house["tick"]})
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": "train", "room": pet["room"], "pet": pet["id"], "what": "asked for %s" % name})
    return "you asked the train to bring the %s from the store; it will set it down by the platform here on its next round" % name


def stock_words(house, cfg, n=6):
    """A line of what the store holds, the most of a kind first ("cushions, lamps, a hammer")."""
    s = sorted(stock(house, cfg).items(), key=lambda kv: -len(kv[1]))
    return ", ".join(("%ss" % k if len(v) > 1 else "a %s" % k) for k, v in s[:n] if k)


# ---- what each room keeps ----

def belongs(cfg, room):
    """{kind: how many} this room keeps of things made for it: its type's list, one cushion for each seat, one light
    when it has none of its own."""
    out = dict(cfg["house"]["rooms"][room["type"]].get("belongs", {}))
    seats = sum(1 for o in room["objects"].values() if "rest" in o.get("fix", {}))
    out["cushion"] = max(out.get("cushion", 0), seats)
    if not any("light" in o.get("fix", {}) for o in room["objects"].values()):
        out["lamp"] = max(out.get("lamp", 0), 1)
    return out


def stays(house, cfg, room, name):
    """Why a made thing stays where it is in its room, or None: it goes to the store. What stays: furniture, what is too
    heavy or planted, statues, what is on a wall, what the visitor named or starred, heirlooms, a keepsake box and
    what is in it, what is in a box (a box holding things counts as one, and what is in it goes with it), what is used in
    the last world day, a hob's sleeping things by where it sleeps, and what the room is for, up to `belongs`."""
    o, objs = room["objects"][name], room["objects"]
    m, k = o["made"], kind(o)
    on = objs.get(o.get("on") or "")
    if on is not None and (order.keeps(on) or "made" in on):
        return "in a box"
    if on is not None and on.get("fix", {}).get("platform"):
        return None
    if cfg["kinds"].get(k, {}).get("furniture") or things.prop(cfg, o).get("fixed") or o.get("planted") or order.statue(name, o) or k == "sculpture":
        return "furniture"
    if o.get("wall") or m.get("called") or m.get("star") is not None or m.get("heirloom") or order.keeps(o):
        return "kept here"
    if world_days(cfg, max(m.get("touched", m["tick"]), m.get("used_at", m["tick"]), m["tick"]), house["tick"]) < 1:
        return "in use"
    if k in order.KEEP["sleeping corner"] and any(p["stage"] not in ("egg", "dead") and p.get("sleeps_in") == room["id"] and dist(p.get("sleeps_at") or p["pos"], o["pos"]) <= 1
                                                 for p in house["pets"].values()):
        if name in sleeping(house, room):
            return "sleeping"
    want = belongs(cfg, room).get(k, 0)
    if want and name in sorted((n for n, x in things.made(room).items() if kind(x) == k and (not x.get("on") or "fix" in objs.get(x["on"], {}))),
                               key=lambda n: -order.last_touch(objs[n]))[:want]:
        return "belongs"
    return None


def sleeping(house, room):
    """A hob's sleeping things: the one or two bed-things nearest where each sleeper lies."""
    out = set()
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead") and p.get("sleeps_in") == room["id"]:
            at = p.get("sleeps_at") or p["pos"]
            beds = sorted((dist(o["pos"], at), n) for n, o in things.made(room).items() if kind(o) in order.KEEP["sleeping corner"] and not o.get("on") and dist(o["pos"], at) <= 1)
            out |= {n for _, n in beds[:2]}
    return out


def out_of_place(house, cfg, room):
    """The made things in this room that go to the store (or, scrap, to the Works), longest untouched first."""
    if not room["type"] or is_store(room):
        return []
    out = [(order.last_touch(o), n) for n, o in things.made(room).items() if not stays(house, cfg, room, n) and not (o.get("on") == "platform")]
    return [n for _, n in sorted(out)]


def to_shelve(house, cfg, room):
    """In the store: made things not yet on its shelves (lying about, in boxes someone made), to be put away; a box
    once what is in it is out."""
    if not is_store(room):
        return []
    return [n for n, o in things.made(room).items() if not shelved(cfg, room, n) and not order.held(room, n) and not order.keeps(o)
            and not (room["objects"].get(o.get("on") or "", {}).get("fix", {}).get("keepsake")) and not o.get("wall") and not cfg["kinds"].get(kind(o), {}).get("furniture")
            and not order.statue(n, o)]


# ---- the bars ----

def on_view(house, cfg):
    """Made things on view: everything but what is on the store's shelves, in a box (made or keepsake), or in the cart."""
    out = 0
    for r in house["rooms"].values():
        for n, o in things.made(r).items() if r["type"] else ():
            on = r["objects"].get(o.get("on") or "")
            if shelved(cfg, r, n) or (on is not None and (order.keeps(on) or order.inside(cfg, on))):
                continue
            out += 1
    return out


def loose_counts(house, cfg):
    """{room name: made things there that are out of place}, the storeroom excepted."""
    return {r["name"]: len(out_of_place(house, cfg, r)) for r in house["rooms"].values() if r["type"] and not is_store(r)}
