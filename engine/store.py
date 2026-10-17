"""The store (SPEC-v3.5.12 §1-2): the storeroom becomes the house's store, one place where everything kept but not in
use lives, sorted by kind on shelves, racks and crates along its walls; every other room keeps what it is for. The
train (rail.py) carries things between them."""
from . import order, things

RID = "r00"   # the storeroom


def is_store(room):
    return room["type"] == "storeroom"


def where(house, cfg, room, name):
    """Where a made thing is, in plain words, for its card and the Things tab: ("in the store, on the lamp shelf",
    stored?)."""
    o, objs = room["objects"][name], room["objects"]
    on = objs.get(o.get("on")) if o.get("on") else None
    if on is not None:
        if order.keeps(on):
            dead = house["pets"].get(order.keeps(on))
            shelf = objs.get(on.get("on")) if on.get("on") else None
            return "in %s keepsake box%s" % ("%s's" % things.label(dead) if dead else "a", ", on the %s in %s" % (on["on"], room["name"]) if shelf else " in %s" % room["name"]), False
        if on.get("fix", {}).get("platform"):
            return "on the platform in %s, for the car" % room["name"], False
        if is_store(room) and on.get("fix", {}).get("shelf"):
            return "in the store, %s the %s" % ("in" if order.inside(cfg, on) else "on", o["on"]), True
        return "%s the %s in %s" % ("in" if order.inside(cfg, on) else "on", o["on"], room["name"]), False
    if o.get("wall"):
        return "on the wall of %s" % room["name"], False
    return "on the floor of %s" % room["name"], False
