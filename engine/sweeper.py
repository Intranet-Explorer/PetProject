"""The sweeper (SPEC-v3.5.8 §4.2): a small robot vacuum the Works builds. It is a creature, not a pet: it never thinks
and asks no model. It roams the house a room at a time picking up loose junk (scrap things lying on a floor, dropped
bits) and brings it back to the Works, where it counts as scrap; it never takes anything kept, held, put away, or
lying where someone sleeps. It bumps and turns, blinks green when full, charges on its dock by the Works, and a pet
using the thing it is heading for shoos it off. director.creatures moves it; the numbers are in house.toml
[creatures.sweeper]."""
from . import order, things, works
from .world import BACK, a, add_event, dist, free_tile, hours, in_room, label, moment, rnd

DOCK = "sweeper dock"


def make(house, cfg, n=1):
    """The Works has built it: its dock by the machine, and the sweeper on it, until there are `n` of them (the
    second shares the dock)."""
    from . import hub, world
    room = house["rooms"].get(hub.RID)
    if not room or sum(c["kind"] == "sweeper" for c in house["creatures"]) >= n:
        return
    if DOCK not in room["objects"]:
        room["objects"][DOCK] = world.fixture({"name": DOCK, "pos": free_tile(house, cfg, room, [2, cfg["H"] - 2]), "dock": True})
    at = room["objects"][DOCK]["pos"]
    house["n"]["creature"] += 1
    house["creatures"].append({"id": "c%d" % house["n"]["creature"], "kind": "sweeper", "room": room["id"], "pos": list(at), "nest": list(at),
                               "doing": "charging on its dock", "since": house["tick"], "until": house["tick"] + 10 ** 9, "fed": {}, "carry": None,
                               "trust": {}, "tame": None, "name": None, "held": [], "load": 0, "full": False, "docked": True,
                               "charged": house["tick"], "swept": {}, "shooed": {}, "goal": None})
    moment(house, "sweeper", "the Works built %s: it whirred off its dock to clean the house" % ("another sweeper" if n > 1 else "a sweeper"), None, room["id"])


def junk(house, cfg, room):
    """What it would pick up here, nearest first is the caller's: [(pos, name of a scrap thing or None, the bit spot or None)]."""
    out = [(o["pos"], n, None) for why, n in order.scraps(house, cfg, room) for o in [room["objects"][n]] if not o.get("on") and not o.get("wall")]
    out += [(s["pos"], None, s) for s in room["spots"] if s["loose"] and s["ready"] and not s.get("on")]
    return out


def way(house, frm, to):
    """The first door from room `frm` toward room `to`, through found rooms, or None."""
    rooms, seen, queue = house["rooms"], {frm}, [(frm, None)]
    while queue:
        rid, first = queue.pop(0)
        if rid == to:
            return first
        for d, nxt in rooms[rid]["doors"].items():
            if nxt not in seen and rooms[nxt]["type"]:
                seen.add(nxt)
                queue.append((nxt, first or d))
    return None


def seen(house, cr, text):
    for p in house["pets"].values():
        if p["room"] == cr["room"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
            add_event(house, p, text)


def through(house, cfg, cr, d):
    """Out through door `d` into the next room."""
    seen(house, cr, "%s trundled out through the %s door" % (called(cr), d))
    cr["room"], cr["pos"], cr["goal"] = house["rooms"][cr["room"]]["doors"][d], list(house["door_tiles"][BACK[d]]), None
    seen(house, cr, "%s trundled in through the %s door, humming" % (called(cr), BACK[d]))


def called(cr):
    return cr.get("name") or "the sweeper"


def step(house, cfg, cr):
    """Every other tick: charge, go home full, or sweep the room it is in and move on."""
    from . import body, hub
    C, tick, room = cfg["house"]["creatures"]["sweeper"], house["tick"], house["rooms"][cr["room"]]
    r = rnd(house, "sweep", cr["id"], tick)
    home = house["rooms"].get(hub.RID)
    if not home or DOCK not in home["objects"]:
        return
    dock = home["objects"][DOCK]["pos"]
    if cr["docked"]:   # charging; at night it stays on its dock
        if house["clock"]["phase"] == "night" or tick - cr["charged"] < hours(cfg, C["charge_hours"]):
            cr["doing"] = "charging on its dock"
            return
        cr["docked"], cr["out"] = False, tick
        seen(house, cr, "%s blinked awake and rolled off its dock" % called(cr))
    full = len(cr["held"]) >= C["holds"] or tick - cr.get("out", tick) >= hours(cfg, C["round_hours"]) or house["clock"]["phase"] == "night"
    cr["full"] = len(cr["held"]) >= C["holds"]
    if full:   # back to the Works with what it has
        if cr["room"] != home["id"]:
            d = way(house, cr["room"], home["id"])
            cr["doing"] = "heading back to the Works, full" if cr["full"] else "heading back to its dock"
            return move(house, cfg, cr, house["door_tiles"][d], lambda: through(house, cfg, cr, d)) if d else None
        cr["doing"] = "heading for its dock"
        return move(house, cfg, cr, dock, lambda: unload(house, cfg, cr, home))
    here = [(dist(pos, cr["pos"]), i, pos, n, s) for i, (pos, n, s) in enumerate(junk(house, cfg, room))
            if cr["shooed"].get(n or "", 0) <= tick]
    if here:
        _, _, pos, n, s = min(here)
        user = next((p for p in house["pets"].values() if p["room"] == room["id"] and n and p["stage"] not in ("egg", "dead") and not p["sleep"]
                     and ((body.state(p)["now"] or {}).get("what") == n or dist(p["pos"], pos) <= 1)), None)
        if user:   # someone is using it, or right by it: shooed off
            cr["shooed"][n] = tick + hours(cfg, C["shooed_hours"])
            cr["goal"], cr["doing"] = None, "shooed off by %s" % label(user)
            add_event(house, user, "%s came bumping toward the %s; you shooed it away" % (called(cr), n))
            house.setdefault("fresh_creatures", []).append({"tick": tick, "kind": "sweeper", "room": room["id"], "pet": user["id"], "what": "shooed from " + n})
            return
        cr["doing"] = "sweeping toward the %s" % (n or s["bit"])
        return move(house, cfg, cr, pos, lambda: pick(house, cfg, cr, room, n, s))
    cr["swept"][room["id"]] = tick   # nothing left here: on to the room swept longest ago
    doors = [(cr["swept"].get(rid, 0), r.random(), d) for d, rid in room["doors"].items() if house["rooms"][rid]["type"]]
    if doors:
        d = min(doors)[2]
        cr["doing"] = "bumping along toward the %s door" % d
        move(house, cfg, cr, house["door_tiles"][d], lambda: through(house, cfg, cr, d))


def move(house, cfg, cr, goal, then):
    """One tile toward `goal` (bumping round what is in the way); `then` once there."""
    if dist(cr["pos"], goal) <= 0 or (cr["pos"] == list(goal)):
        return then()
    nxt = [p + (g > p) - (g < p) for p, g in zip(cr["pos"], goal)]
    if not in_room(cfg, nxt):
        return then()
    cr["pos"] = nxt
    if cr["pos"] == list(goal):
        then()


def pick(house, cfg, cr, room, name, spot):
    """It sucks up a scrap thing or a loose bit where it stands."""
    if name and name in room["objects"] and order.scrap(house, cfg, room, name) and not room["objects"][name].get("on"):
        o = room["objects"].pop(name)
        cr["held"].append({"name": name, "o": o})
        for m in [m for m in room.get("marks", []) if m["on"] == name]:
            room["marks"].remove(m)
        seen(house, cr, "%s whirred up the %s" % (called(cr), name))
        owner = house["pets"].get(o["made"]["owner"])
        if owner and owner["stage"] not in ("egg", "dead") and owner["room"] != room["id"]:
            add_event(house, owner, "%s swept up your old %s from %s" % (called(cr), name, room["name"]))
    elif spot and spot in room["spots"]:
        room["spots"].remove(spot)
        cr["held"].append({"bit": spot["bit"]})
        seen(house, cr, "%s whirred up %s" % (called(cr), a(spot["bit"])))
    cr["load"], cr["goal"] = len(cr["held"]), None


def unload(house, cfg, cr, home):
    """At its dock: what it brought counts as scrap for the Works (a made thing as one, three bits as one)."""
    made = [h for h in cr["held"] if "o" in h]
    bits = [h["bit"] for h in cr["held"] if "bit" in h]
    for h in made:
        things.gone(house, h["o"], h["name"], "swept up and fed to the Works by the sweeper", home)
        works.fed(house, cfg, None, h["o"])
    for _ in range(len(bits) // cfg["machine"]["bits"]):
        works.fed(house, cfg, None, None)
    leftover = bits[len(bits) // cfg["machine"]["bits"] * cfg["machine"]["bits"]:]
    if leftover:   # (a bit or two too few to count go back in with the stock)
        from . import machine
        for b in leftover:
            if b in cfg["machine"]["materials"]:
                machine.fill(house, cfg, b, 1)
    if cr["held"]:
        S = house.setdefault("sweeper", {"things": 0, "bits": 0, "trips": 0})
        S["things"], S["bits"], S["trips"] = S["things"] + len(made), S["bits"] + len(bits), S["trips"] + 1
        what = ", ".join([h["name"] for h in made][:3]) + (" and %d more" % (len(made) - 3) if len(made) > 3 else "")
        moment(house, "sweeper", "%s brought %s to the Works" % (called(cr).capitalize() if not cr.get("name") else cr["name"],
                                                                   " and ".join(filter(None, [what, "%d loose bits" % len(bits) if bits else ""]))), None, home["id"])
        seen(house, cr, "%s tipped what it had swept up into the Works" % called(cr))
    cr["held"], cr["load"], cr["full"], cr["docked"], cr["charged"] = [], 0, False, True, house["tick"]
    cr["doing"] = "charging on its dock"
