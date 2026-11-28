"""The great clear-out (SPEC-v3.6c §1): a one-time house event on the deploy that brings it, like the spring clean and
the pond spreading. The hobs are told, the story says so, and over about half a world day the train works through
the house: at each stop its cart takes what the plan sends from that room, to the store (kept things, and useful
things in good condition a room doesn't need) or to the Works as scrap (everything else: old charms nobody counts,
worn things, curios with no use, duplicates the store has enough of). What stays: furniture, fixtures, built things,
machines and their trays, the stones and memory shelves, what a hob is holding or using, and what a room is for up to
its cap. Nothing kept is lost. Built things that stand in the middle of a room move to the nearest wall (the layout
check, floors.py). At the end the story has one summary line. Switch: [clearout] on."""
from collections import Counter

from . import craft, floors, items, order, store, things
from .world import add_event, days as world_days, moment


def C(cfg):
    return cfg.get("clearout", {})


def active(house):
    c = house.get("clearout")
    return bool(c and not c.get("done"))


def why_stays(house, cfg, room, name):
    """Why a made thing stays where it is in the clear-out, or None: it goes."""
    o = room["objects"][name]
    if o.get("on") == "platform":
        return None
    why = store.stays(house, cfg, room, name)
    if why == "in use":   # (in the clear-out, "in use" is what was touched in the last few world hours, not the last day)
        return why if world_days(cfg, order.last_touch(o), house["tick"]) * 24 < C(cfg)["use_hours"] else None
    if why:
        return why
    if any(p.get("plan") and name in str(p["plan"]) or name in str((p.get("body") or {}).get("now") or "") for p in house["pets"].values() if p["stage"] not in ("egg", "dead") and p["room"] == room["id"]):
        return "in use"
    return None


def kept(house, o):
    """Kept things go to the store, never to the Works: firsts, heirlooms, titled things, gifts, the visitor's starred
    and named, finds from the pond, designs and inventions of the house's own."""
    m = o["made"]
    return store.special(house, o) or bool(m.get("found") or m.get("design"))


def good(cfg, o):
    """Useful and in good condition: not a charm, not a curio with no use, not worn past half its life."""
    k = o["made"]["recipe"].get("kind")
    if k == "charm" or (cfg["kinds"].get(k, {}).get("invented") and not cfg["kinds"][k].get("effect")):
        return False
    return craft.tool_kind(cfg, o) not in cfg["craft"]["tool"] or o["made"].get("wear", 0) < craft.lasts(cfg, o) / 2


def plan(house, cfg):
    """{room id: {name: "store"|"works"}} for every room, and the store's own shelves thinned to fit: kept things first,
    then the newest useful things up to `per_kind` of a kind in the store, the rest scrap."""
    shop = house["rooms"].get(store.RID)
    room_of = {}
    cands = []   # (room, name, o)
    for r in house["rooms"].values():
        if not r["type"] or store.is_store(r):
            continue
        for n in list(things.made(r)):
            if not why_stays(house, cfg, r, n) and not order.held(r, n):
                cands.append((r, n, r["objects"][n]))
    shelved = [(shop, n, o) for n, o in things.made(shop).items() if store.shelved(cfg, shop, n)] if shop and shop["type"] else []
    room_of.update({r["id"]: {} for r in house["rooms"].values() if r["type"]})
    room_cap = sum(order.cap(cfg, o) for o in shop["objects"].values() if "fix" in o) if shop and shop["type"] else 0
    room_cap = min(room_cap, C(cfg)["store_most"])
    kinds, total = Counter(), 0
    # kept things first (never scrap), then useful things newest first, up to per_kind of a kind
    everything = sorted(shelved + cands, key=lambda x: (not kept(house, x[2]), -order.last_touch(x[2])))
    for r, n, o in everything:
        k = o["made"]["recipe"].get("kind")
        if kept(house, o) or (good(cfg, o) and kinds[k] < C(cfg)["per_kind"] and total < room_cap):
            kinds[k] += 1
            total += 1
            if r is not shop:
                room_of[r["id"]][n] = "store"
        else:
            room_of[r["id"]][n] = "works"
    return room_of


def migrate(house, cfg):
    """On the deploy that brings it, once: the plan, the layout check, and the hobs told."""
    if not C(cfg).get("on") or "clearout" in house:
        return
    p = plan(house, cfg)
    if not any(p.values()):   # (a new house, or one with nothing about: nothing to clear, and nothing said)
        house["clearout"] = {"at": house["tick"], "until": house["tick"], "done": house["tick"], "to_store": 0, "to_works": 0, "plan": {}, "moved": {}, "planned": {}}
        return
    moved = {r["name"]: floors.layout_check(house, cfg, r) for r in house["rooms"].values() if r["type"]} if floors.on(cfg) else {}
    house["clearout"] = {"at": house["tick"], "until": house["tick"] + round(C(cfg)["days"] * cfg["ticks_per_day"]), "done": None,
                         "to_store": 0, "to_works": 0, "plan": p, "moved": {k: v for k, v in moved.items() if v},
                         "planned": {"store": sum(1 for x in p.values() for v in x.values() if v == "store"),
                                     "works": sum(1 for x in p.values() for v in x.values() if v == "works")}}
    moment(house, "clearout", "The great clear-out: the train goes through the house, kept things to the store and the rest to the Works as scrap",
           None, store.RID)
    for pet in house["pets"].values():
        if pet["stage"] not in ("egg", "dead"):
            add_event(house, pet, "it is the great clear-out: the train is going through the house, taking what nobody keeps to the store or the Works. "
                                  "What you hold or use stays, and so does everything that means something; from now on things are set down against the walls, "
                                  "and the middle of every room stays clear")
            pet["news"].append("event")


def collect(house, cfg, tr, room):
    """rail.collect calls this at each stop while the clear-out is on: the cart takes this room's share of the plan."""
    from . import rail
    if not active(house) or not C(cfg).get("on"):   # (switched off: a clear-out under way stops where it is)
        return
    c = house["clearout"]
    mine = c["plan"].get(room["id"], {})
    took = []
    for n, to in list(mine.items()):
        if len(tr["held"]) >= C(cfg)["cart_holds"]:
            break
        mine.pop(n)
        o = room["objects"].get(n)
        if o is None or "made" not in o or (to == "store" and store.is_store(room)):
            continue
        if to == "works" and store.is_store(room):   # (the store's own shelves thinned: straight into the cart)
            pass
        elif why_stays(house, cfg, room, n):   # (picked up or put to use since the plan was made)
            continue
        o["deliver"] = house["rail"]["depot"] if to == "works" else store.RID
        rail.load(house, cfg, tr, room, n, None)
        took.append(n)
        c["to_works" if to == "works" else "to_store"] += 1
    if took:
        rail.log(house, room["id"], "the clear-out: loaded %d things" % len(took))


def tick(house, cfg):
    """At its end, whatever the train did not get to is carried straight where the plan sends it, and the story says
    what was done."""
    from . import works
    if not active(house) or not C(cfg).get("on"):
        return
    c = house["clearout"]
    if house["tick"] < c["until"] and any(c["plan"].values()):
        return
    shop = house["rooms"].get(store.RID)
    for rid, mine in c["plan"].items():
        room = house["rooms"][rid]
        for n, to in list(mine.items()):
            o = room["objects"].get(n)
            if o is None or "made" not in o or (to == "store" and store.is_store(room)) or (not store.is_store(room) and why_stays(house, cfg, room, n)):
                continue
            room["objects"].pop(n)
            items.place(house, cfg, room, n, o)
            if to == "store" and shop and store.put(house, cfg, shop, n, o):
                c["to_store"] += 1
            else:
                things.gone(house, o, n, "sent to the Works as scrap in the great clear-out", room)
                works.fed(house, cfg, None, o)
                c["to_works"] += 1
        mine.clear()
    c["done"] = house["tick"]
    moment(house, "clearout done", "the house was cleared out: %d things to the store, %d to the Works" % (c["to_store"], c["to_works"]), None, store.RID)
