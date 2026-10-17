"""The rail (SPEC-v3.5.12 §3): a little train the Works builds, running from the machine room through every room on a
track, carrying things to the store and back. Three cars: the engine in front, the cart in the middle (what it
carries), the tram at the back (one hob can ride). Like the sweeper it is a creature, not a pet: it never thinks and
asks no model. It waits and rings its bell for a hob on the track, stops at each room's platform once a round, and
sleeps in its depot by the Works at night. director.creatures moves it; the numbers are in house.toml [rail]."""
import heapq

from . import order, things, works
from .world import add_event, dist, free_tile, label, moment, rnd

DEPOT = "rhub"   # the machine room
COMPASS = {(0, 1): "south", (1, 1): "south-east", (1, 0): "east", (1, -1): "north-east", (0, -1): "north", (-1, -1): "north-west", (-1, 0): "west", (-1, 1): "south-west"}
FLIP = {v: COMPASS[(-k[0], -k[1])] for k, v in COMPASS.items()}


def R(cfg):
    return cfg["house"]["rail"]


def train(house):
    return next((c for c in house["creatures"] if c["kind"] == "train"), None)


# ---- the route and the track ----

def route(house, cfg):
    """One round, room by room: the order in house.toml [rail] (by room type) when every step of it goes through a door
    of this house and it reaches every found room, else a walk out and back along every branch of the found rooms."""
    rooms = house["rooms"]
    by_type = {r["type"]: rid for rid, r in rooms.items() if r["type"]}
    want = [by_type.get(t) for t in R(cfg)["route"]]
    if all(want) and all(b in rooms[a]["doors"].values() for a, b in zip(want, want[1:])) and set(want) == set(by_type.values()):
        return want
    out, seen = [DEPOT], {DEPOT}

    def walk(rid):   # ponytail: depth first over a spanning tree; a loop in the house is ridden as two branches
        for d in sorted(rooms[rid]["doors"]):
            nxt = rooms[rid]["doors"][d]
            if nxt not in seen and rooms[nxt]["type"]:
                seen.add(nxt)
                out.append(nxt)
                walk(nxt)
                out.append(rid)
    walk(DEPOT)
    return out


def door_to(house, a, b):
    return next(d for d, x in house["rooms"][a]["doors"].items() if x == b)


def legs(house, rooms):
    """[{room, in, out, stop}]: each pass through a room, the door it comes in by and the one it leaves by (None at the
    depot), and whether it stops there: the first time a round comes to a room, and at the depot at the end."""
    out, stopped = [], set()
    for i, rid in enumerate(rooms):
        last = i == len(rooms) - 1
        out.append({"room": rid, "in": door_to(house, rid, rooms[i - 1]) if i else None, "out": None if last else door_to(house, rid, rooms[i + 1]),
                    "stop": (rid not in stopped and i > 0) or last})
        if i:
            stopped.add(rid)
    return out


def blocked(house, cfg, room):
    """Tiles the track may not cross: fixtures, the layout's furniture, and water."""
    out = {tuple(o["pos"]) for o in room["objects"].values() if "fix" in o and not o.get("wall") and not o.get("on") and not o["fix"].get("platform")}
    out |= {tuple(t) for t in room.get("blocked", [])} | {tuple(o["pos"]) for o in room["objects"].values() if "memorial" in o}
    if (house.get("resting") or {}).get("room") == room["id"]:   # (nor through the resting place)
        out |= {tuple(t) for t in house["resting"]["tiles"]}
    for o in room["objects"].values():
        out |= {tuple(t) for t in o.get("fix", {}).get("water", [])}
    return out


def cost(cfg, t):
    """Along a wall is cheap (the track runs along walls), across the middle dearer."""
    x, y, W, H = t[0], t[1], cfg["W"], cfg["H"]
    ring = min(x, y, W - 1 - x, H - 1 - y)
    return 1.0 if ring == 1 else 1.4 if ring == 0 else 2.0


def path(cfg, frm, to, bad):
    """The cheapest 4-neighbour way from one tile to another round `bad`, as a list of tiles, or None."""
    frm, to = tuple(frm), tuple(to)
    best, queue = {frm: (0, None)}, [(0, frm)]
    while queue:
        c, t = heapq.heappop(queue)
        if t == to:
            out = []
            while t:
                out.append(list(t))
                t = best[t][1]
            return out[::-1]
        if c > best[t][0]:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (t[0] + dx, t[1] + dy)
            if 0 <= n[0] < cfg["W"] and 0 <= n[1] < cfg["H"] and (n not in bad or n == to):
                nc = c + cost(cfg, n)
                if nc < best.get(n, (1e9,))[0]:
                    best[n] = (nc, t)
                    heapq.heappush(queue, (nc, n))
    return None


def plan_room(house, cfg, room, doors):
    """Where the platform goes and how the track reaches it from each door it uses: (platform, {door: [door tile ..
    platform]}). The branches share only the platform, and each is long enough for the whole train to stand on it
    clear of its door; a dead end's platform is at the end of its one branch, against the buffer."""
    D, doors, need = house["door_tiles"], sorted(doors), R(cfg)["clear"]
    for bad in (blocked(house, cfg, room), set()):   # (a room it cannot thread through its fixtures: over them, as a last resort)
        bad = (bad - {(D[d][0] + dx, D[d][1] + dy) for d in doors for dx in (-1, 0, 1) for dy in (-1, 0, 1)})   # the doorway itself is never blocked
        bad |= {tuple(D[d]) for d in room["doors"] if d not in doors}   # (nor through a door it does not use)
        got = plan_round(cfg, D, room, doors, need, bad)
        if got[0]:
            return got
    return None, {}


def plan_round(cfg, D, room, doors, need, bad):
    """The best platform and arms round `bad`: as long as `need` if it can be, shorter if not."""
    for long in (need, 3, 1):
        best = None
        for x in range(1, cfg["W"] - 1):
            for y in range(1, cfg["H"] - 1):
                p = (x, y)
                if p in bad or any(dist(p, D[d]) < 2 for d in room["doors"]):
                    continue
                arms, used, total = {}, set(), 0.0
                for d in doors:
                    way = path(cfg, D[d], p, (bad | used) - {p})
                    if not way or len(way) < long + 1:
                        break
                    arms[d], used = way, used | {tuple(t) for t in way}
                    total += sum(cost(cfg, t) for t in way)
                else:
                    total += 2.0 * (min(x, y, cfg["W"] - 1 - x, cfg["H"] - 1 - y) != 1)   # (a platform along a wall)
                    if len(doors) == 1:
                        total = abs(len(arms[doors[0]]) - need - 2) + 0.1 * total   # a dead end: just long enough
                    if best is None or total < best[0]:
                        best = (total, list(p), arms)
        if best:
            return best[1], best[2]
    return None, {}


def lay(house, cfg):
    """The track, laid (on the day the Works builds it, and again at the depot each morning, in case something has
    been built where it ran), and a platform in every room."""
    from . import world
    rooms = route(house, cfg)
    L = legs(house, rooms)
    uses = {}
    for leg in L:
        uses.setdefault(leg["room"], set()).update(d for d in (leg["in"], leg["out"]) if d)
    rail = house.setdefault("rail", {"built": house["tick"], "rounds": 0, "asked": [], "done": {"loaded": 0, "delivered": 0, "stops": 0}})
    rail.update(depot=DEPOT, route=rooms, legs=L)
    old, rail["rooms"] = rail.get("rooms", {}), {}
    for rid, doors in uses.items():
        room = house["rooms"][rid]
        p, arms = plan_room(house, cfg, room, doors)
        if not p:
            continue
        track = {tuple(t) for a in arms.values() for t in a}
        bad = blocked(house, cfg, room) | track
        side = next((t for t in ([p[0] + dx, p[1] + dy] for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)))
                     if 0 <= t[0] < cfg["W"] and 0 <= t[1] < cfg["H"] and tuple(t) not in bad), list(p))
        rail["rooms"][rid] = {"track": list(arms.values()), "arms": arms, "platform": p, "side": side, "buffer": len(doors) == 1, "due": old.get(rid, {}).get("due")}
        if "platform" not in room["objects"]:
            room["objects"]["platform"] = world.fixture({"name": "platform", "pos": p, "platform": True, "store": R(cfg)["platform_holds"], **({"depot": True} if rid == DEPOT else {})})
        room["objects"]["platform"]["pos"] = list(p)
        for n, o in room["objects"].items():   # nothing made is left standing on the track
            if "made" in o and not o.get("on") and not o.get("wall") and tuple(o["pos"]) in track:
                o["pos"] = free_tile(house, cfg, room, o["pos"], n)
    return rail


def leg_tiles(rail, leg):
    """The tiles a pass goes over: in from its door to the platform, then out to the next door."""
    arms = rail["rooms"][leg["room"]]["arms"]
    tin = list(arms[leg["in"]]) if leg["in"] else [rail["rooms"][leg["room"]]["platform"]]
    return tin + (list(reversed(arms[leg["out"]]))[1:] if leg["out"] else [])


def on_track(house, rid):
    return {tuple(t) for a in (house.get("rail") or {}).get("rooms", {}).get(rid, {}).get("track", []) for t in a}


# ---- the train ----

def make(house, cfg):
    """The Works has built the rail: the track is laid, and the train rolls out of the machine room to its depot."""
    if train(house):
        return
    rail = lay(house, cfg)
    if DEPOT not in rail["rooms"]:
        return
    p = rail["rooms"][DEPOT]["platform"]
    house["n"]["creature"] += 1
    tr = {"id": "c%d" % house["n"]["creature"], "kind": "train", "room": DEPOT, "pos": list(p), "nest": list(p),
          "doing": "standing at its platform by the Works", "since": house["tick"], "until": house["tick"] + 10 ** 9,
          "fed": {}, "carry": None, "trust": {}, "tame": None, "name": None, "held": [],
          "trail": [[DEPOT, list(p)]], "lead": "engine", "cars": [], "moving": False, "lid": "closed", "bell": house["tick"],
          "asleep": False, "rider": None, "load": 0, "cargo": [], "speed": R(cfg)["speed"],
          "leg": len(rail["legs"]) - 1, "path": [], "wait": house["tick"] + R(cfg)["stop_ticks"], "blocked": 0, "stopped": True, "left": -1}
    house["creatures"].append(tr)
    cars(tr)
    moment(house, "rail", "the Works laid a track through the house, and a little train puffed out of the machine room", None, DEPOT)


def called(tr):
    return tr.get("name") or "the train"


def cars(tr):
    """Where each car is, from the trail its leading car has left: two tiles apart, engine, cart, tram, each facing
    the way it goes (backwards while the engine pushes)."""
    t, out = tr["trail"], []
    for k in (0, 2, 4):
        if k >= len(t):
            out.append(None)
            continue
        here = t[k]
        newer = t[k - 1] if k and t[k - 1][0] == here[0] else None
        older = t[k + 1] if k + 1 < len(t) and t[k + 1][0] == here[0] else None
        a, b = (here[1], newer[1]) if newer else (older[1], here[1]) if older else (here[1], here[1])
        go = COMPASS.get((max(-1, min(1, b[0] - a[0])), max(-1, min(1, b[1] - a[1]))))
        was = next((c["dir"] for c in tr.get("cars") or [] if c and c.get("k") == k), "east")
        out.append({"room": here[0], "pos": list(here[1]), "dir": (go if tr["lead"] == "engine" else FLIP[go]) if go else was, "k": k})
    if tr["lead"] == "tram":   # backing out: the tram goes first
        out = out[::-1]
    tr["cars"], tr["room"], tr["pos"] = out, t[0][0], list(t[0][1])
    tr["cargo"], tr["load"] = [h.get("name") or h["bit"] for h in tr["held"]], len(tr["held"])
    return out


def seen(house, rid, text, but=None):
    for p in house["pets"].values():
        if p["room"] == rid and p["stage"] not in ("egg", "dead") and not p["sleep"] and p["id"] != but and not p.get("riding"):
            add_event(house, p, text)


def log(house, room, what, pet=None):
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": "train", "room": room, "pet": pet, "what": what})


def step(house, cfg, tr):
    """Every tick: asleep in its depot, stopped at a platform, or on its way, `speed` tiles a tick."""
    C, tick, rail = R(cfg), house["tick"], house.get("rail")
    if not rail or not rail.get("legs"):
        return
    if tr["asleep"]:
        if house["clock"]["phase"] == "night":
            return
        tr["asleep"], tr["wait"] = False, tick + C["stop_ticks"]
        seen(house, DEPOT, "%s woke in its depot with a puff of steam" % called(tr))
    rider_off(house, cfg, tr)
    if tr["stopped"]:
        if tick < tr["wait"]:
            return
        if tr["leg"] == len(rail["legs"]) - 1:   # at the depot: a new round, or, at night, sleep (it has done its last)
            if house["clock"]["phase"] == "night":
                tr.update(asleep=True, doing="asleep in its depot by the Works", lid="closed", moving=False)
                return
            if tr.get("laid_on") != house["clock"]["day"]:   # the first round of the day: the track looked over, and the day's allowance aboard
                lay(house, cfg)
                tr["laid_on"] = house["clock"]["day"]
                allowance(house, cfg, tr)
            tr["leg"], tr["path"], tr["left"] = 0, leg_tiles(rail, rail["legs"][0])[1:], -1
        tr.update(stopped=False, lid="closed", moving=True)
        tr["doing"] = "pulling away from the platform in %s, puffing" % house["rooms"][tr["room"]]["name"]
        seen(house, tr["room"], "%s closed its cart and puffed away from the platform" % called(tr))
    for _ in range(tr["speed"]):
        if not advance(house, cfg, tr):
            break
    cars(tr)
    ride(house, tr)


def advance(house, cfg, tr):
    """One tile on. False when it has stopped, or waits for someone on the track."""
    rail = house["rail"]
    if not tr["path"]:
        nxt = tr["leg"] + 1   # through the door into the next room
        if nxt >= len(rail["legs"]) or rail["legs"][nxt]["room"] not in rail["rooms"]:
            return arrive(house, cfg, tr)
        tr["leg"], tr["path"] = nxt, leg_tiles(rail, rail["legs"][nxt])
    leg = rail["legs"][tr["leg"]]
    room, t = house["rooms"][leg["room"]], tr["path"][0]
    if blocker(house, cfg, tr, room, t):
        return False
    tr["blocked"] = 0
    if len(tr["trail"]) > 1 and tr["trail"][1] == [room["id"], t]:   # it backs out the way it came, the engine pushing (a dead end)
        tr["trail"] = tr["trail"][:5][::-1]   # (the five tiles the cars stand on: the last car leads now)
        tr["lead"] = "tram" if tr["lead"] == "engine" else "engine"
        while tr["path"] and [room["id"], tr["path"][0]] in tr["trail"]:
            tr["path"].pop(0)
        return True
    tr["path"].pop(0)
    tr["trail"].insert(0, [room["id"], list(t)])
    del tr["trail"][9:]
    for n, o in room["objects"].items():   # something left on the track is nudged off it
        if "made" in o and not o.get("on") and not o.get("wall") and o["pos"] == list(t):
            o["pos"] = free_tile(house, cfg, room, t, n)
    if leg["stop"] and list(t) == rail["rooms"][leg["room"]]["platform"] and tr["left"] != tr["leg"]:
        return arrive(house, cfg, tr)
    tr["doing"] = "puffing through %s" % room["name"]
    return True


def blocker(house, cfg, tr, room, t):
    """Someone on the track just ahead: it waits, ringing its bell; a hob that stays put steps aside."""
    ahead = [list(t)] + [list(x) for x in tr["path"][1:2]]
    p = next((p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] != "dead" and not p.get("riding") and list(p["pos"]) in ahead), None)
    if not p:
        return False
    tr["blocked"] += 1
    tr["bell"], tr["doing"] = house["tick"], "waiting, ringing its bell at %s on the track" % label(p)
    if tr["blocked"] == 1:
        add_event(house, p, "%s stopped just short of you and rang its bell: you are on its track" % called(tr))
    if tr["blocked"] >= R(cfg)["wait_ticks"] and p["stage"] != "egg":
        track = on_track(house, room["id"])
        free = [x for x in ([p["pos"][0] + dx, p["pos"][1] + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)) if 0 <= x[0] < cfg["W"] and 0 <= x[1] < cfg["H"] and tuple(x) not in track]
        if free:
            p["pos"] = min(free, key=lambda x: dist(x, p["pos"]))
            add_event(house, p, "you stepped off the track, and %s rolled by" % called(tr))
            log(house, room["id"], "waited for %s on the track" % label(p), p["id"])
    return True


# ---- at a platform ----

def arrive(house, cfg, tr):
    """At the platform: the bell, the lid open, and what it brings, takes and leaves here."""
    from . import store
    C, rail, tick = R(cfg), house["rail"], house["tick"]
    rid = rail["legs"][tr["leg"]]["room"]
    room = house["rooms"][rid]
    tr.update(stopped=True, moving=False, lid="open", bell=tick, wait=tick + C["stop_ticks"], left=tr["leg"], arrived=tick)
    tr["doing"] = "stopped at the platform in %s, its cart open" % room["name"]
    rail["done"]["stops"] += 1
    log(house, rid, "stopped at the platform")
    seen(house, rid, "%s rang its bell and stopped at the platform here, its cart open" % called(tr))
    if tr["rider"]:
        tr["ride"]["stops"] -= 1
    deliver(house, cfg, tr, room)
    hand_out(house, cfg, tr, room)
    collect(house, cfg, tr, room)
    if store.is_store(room):
        store.unload(house, cfg, tr, room)
        store.fetch(house, cfg, tr, room)
    if rid == rail["depot"]:
        to_works(house, cfg, tr, room)
        back_in(house, cfg, tr)
        rail["rounds"] = rail.get("rounds", 0) + 1
        log(house, rid, "finished a round")
    cars(tr)
    return False


def collect(house, cfg, tr, room):
    """What the hobs have left on the platform for it goes into the cart. And (18 October 2026, v3.5.12's day: the
    greenhouse kept 9 where the cap is 6, for nobody was there when the train stopped) in a room still over its cap,
    the car takes what is over it, the longest untouched first: never what is kept, in use, or a fixed thing."""
    from . import store
    for n in order.held(room, "platform"):
        if len(tr["held"]) >= R(cfg)["cart_holds"]:
            break
        load(house, cfg, tr, room, n, None)
    if store.is_store(room) or room["id"] == house["rail"]["depot"]:
        return
    over = store.out_of_place(house, cfg, room)
    took = []
    for n in sorted(over, key=lambda n: room["objects"][n]["made"].get("touched", room["objects"][n]["made"]["tick"]))[:max(0, len(over) - store.S(cfg)["cap"])]:
        if len(tr["held"]) >= R(cfg)["cart_holds"] - 1 or n not in room["objects"] or order.kept(house, cfg, room, n):
            continue
        load(house, cfg, tr, room, n, None)
        took.append(n)
    if took:
        moment(house, "rail", "the train's cart took %s from %s, where too much lay about" % (", ".join(took), room["name"]), None, room["id"])


def load(house, cfg, tr, room, name, pet):
    """A thing into the cart: to the Works if it is scrap, else to the store (or where it was asked for). A box goes
    with what is in it, each to its own shelf."""
    from . import store
    for n in order.held(room, name):
        if len(tr["held"]) < R(cfg)["cart_holds"] - 1:
            load(house, cfg, tr, room, n, pet)
    to = room["objects"][name].pop("deliver", None) or (house["rail"]["depot"] if order.scrap(house, cfg, room, name) else store.RID)
    o = room["objects"].pop(name)
    o.pop("on", None)
    for m in [m for m in room.get("marks", []) if m["on"] == name]:   # what is written on it goes with it
        room["marks"].remove(m)
        o.setdefault("marks", []).append(m)
    tr["held"].append({"name": name, "o": o, "to": to, "from": room["id"], "by": pet["id"] if pet else o.get("put_by")})
    if pet or o.pop("put_by", None):
        house["rail"]["done"]["loaded"] += 1
    log(house, room["id"], "loaded %s%s" % (name, " for the Works" if to == house["rail"]["depot"] else ""), pet["id"] if pet else None)
    cars(tr)


def loading(house, cfg, room):
    """Where a thing for the train is carried here: (the train, its cart's tile) while it stands at the platform with
    room in its cart, else (None, the platform) while the platform has room; (None, None) where there is no platform."""
    rail = house.get("rail")
    if not rail or room["id"] not in rail["rooms"]:
        return None, None
    tr = train(house)
    cart = next((c for c in (tr or {}).get("cars") or [] if c and c.get("k") == 2), None)
    if tr and tr["stopped"] and cart and cart["room"] == room["id"] and len(tr["held"]) < R(cfg)["cart_holds"]:
        return tr, cart["pos"]
    if len(order.held(room, "platform")) >= R(cfg)["platform_holds"]:
        return None, None
    return None, rail["rooms"][room["id"]]["platform"]


def put_on(house, cfg, pet, room, name):
    """A hob puts a thing into the train's cart (it stands here) or on the platform for it. Where it went, or ""."""
    tr, at = loading(house, cfg, room)
    o = room["objects"].get(name)
    if not at or not o or "made" not in o or o.get("on") == "platform" or order.keeps(room["objects"].get(o.get("on") or "", {})):
        return ""
    o.pop("on", None)   # (taken down from a shelf here, or out of a box)
    owner = house["pets"].get(o["made"]["owner"])
    if tr:
        load(house, cfg, tr, room, name, pet)
        said = "into the cart of %s" % called(tr)
    else:
        o.update(on="platform", pos=list(at), kept=house["tick"], put_by=pet["id"])
        log(house, room["id"], "%s put %s on the platform" % (label(pet), name), pet["id"])
        said = "on the platform, for the train"
    if owner and owner is not pet and owner["stage"] not in ("egg", "dead"):
        add_event(house, owner, "your %s was put %s, to go to the store" % (name, said))
    return said


def drop(house, cfg, tr, h, room, near):
    """A thing out of the cart, onto the floor by the platform."""
    o = h["o"]
    o["pos"], o["kept"] = free_tile(house, cfg, room, near), house["tick"]
    for m in o.pop("marks", []):
        room.setdefault("marks", []).append(m)
    room["objects"][h["name"]] = o
    tr["held"].remove(h)


def deliver(house, cfg, tr, room):
    """What was asked for in this room is set down by the platform for whoever asked."""
    p = house["rail"]["rooms"][room["id"]]["platform"]
    for h in [h for h in tr["held"] if h["to"] == room["id"] and h.get("asked")]:
        drop(house, cfg, tr, h, room, p)
        h["o"]["made"]["touched"] = house["tick"]   # (brought to be used: in use)
        who = house["pets"].get(h["asked"])
        house["rail"]["done"]["delivered"] += 1
        house["rail"]["asked"] = [a for a in house["rail"]["asked"] if a["name"] != h["name"]]
        log(house, room["id"], "brought %s for %s" % (h["name"], label(who) if who else "someone"), who["id"] if who else None)
        moment(house, "rail", "%s brought %s to %s%s" % (called(tr).capitalize() if not tr.get("name") else tr["name"], things.a_thing(cfg, h["o"]["made"]["recipe"]),
                                                       room["name"], " for %s" % label(who) if who else ""), who["id"] if who else None, room["id"])
        if who and who["stage"] not in ("egg", "dead"):
            add_event(house, who, "%s brought the %s you asked for to %s; it is by the platform" % (called(tr), h["name"], room["name"]))


def allowance(house, cfg, tr):
    """SPEC-v3.5.12 §3: the Works' daily allowance, delivered round the house: one of the machine's materials aboard
    for each hob who has not had all it gets from the machine today (the one the machine holds most of)."""
    from . import machine
    S = machine.state(house, cfg)
    for p in house["pets"].values():
        if p["stage"] in ("egg", "dead") or machine.left(house, cfg, p) <= 0 or len(tr["held"]) >= R(cfg)["cart_holds"]:
            continue
        m = max((m for m in cfg["machine"]["materials"] if S["stock"].get(m, 0) > 0), key=lambda m: S["stock"][m], default=None)
        if m:
            S["stock"][m] -= 1
            tr["held"].append({"bit": m, "for": p["id"], "to": "hand"})
    if any(h.get("bit") for h in tr["held"]):
        log(house, DEPOT, "took the day's allowance from the machine: %d" % sum(1 for h in tr["held"] if h.get("bit")))


def hand_out(house, cfg, tr, room):
    """Whoever's allowance is aboard and is here, awake, gets it: one of today's from the machine."""
    from . import machine
    for h in [h for h in tr["held"] if h.get("bit")]:
        p = house["pets"].get(h["for"])
        if not p or p["room"] != room["id"] or p["sleep"] or p["stage"] in ("egg", "dead") or machine.left(house, cfg, p) <= 0:
            continue
        tr["held"].remove(h)
        p["machine"] = {"day": house["clock"]["day"], "took": cfg["machine"]["free"] - machine.left(house, cfg, p) + 1, "seen": house["tick"]}
        machine.got(house, cfg, p, room, h["bit"])
        add_event(house, p, "%s brought you %s from the machine: one of today's" % (called(tr), h["bit"]))
        log(house, room["id"], "brought %s from the machine for %s" % (h["bit"], label(p)), p["id"])


def back_in(house, cfg, tr):
    """What it could not hand out goes back into the machine."""
    from . import machine
    for h in [h for h in tr["held"] if h.get("bit")]:
        tr["held"].remove(h)
        machine.state(house, cfg)["stock"][h["bit"]] = machine.state(house, cfg)["stock"].get(h["bit"], 0) + 1


def to_works(house, cfg, tr, room):
    """At the depot: the scrap in the cart goes to the Works (as if fed to it, by nobody)."""
    took = [h for h in tr["held"] if h["to"] == house["rail"]["depot"]]
    for h in took:
        tr["held"].remove(h)
        things.gone(house, h["o"], h["name"], "carried to the Works by the train", room)
        works.fed(house, cfg, None, h["o"])
    if took:
        log(house, room["id"], "brought %d things to the Works" % len(took))
        seen(house, room["id"], "%s tipped %d old things from its cart into the Works" % (called(tr), len(took)))


# ---- riding ----

def tram(tr):
    return next((c for c in tr.get("cars") or [] if c and c.get("k") == 4), None)


def board(house, cfg, tr, pet):
    """A hob climbs into the tram: a little one for a stop or two, as play; an old one to save its legs to a far room."""
    if tr["rider"] or not tr["stopped"] or not R(cfg)["rides"] or not tram(tr) or tram(tr)["room"] != pet["room"]:
        return False
    r = rnd(house, "ride", pet["id"], house["tick"])
    tr["rider"], tr["ride"] = pet["id"], {"stops": r.randint(1, 2) if pet["stage"] in ("hatchling", "child") else r.randint(2, 4), "from": pet["room"], "at": house["tick"]}
    pet["riding"] = tr["id"]
    log(house, pet["room"], "%s climbed into the tram" % label(pet), pet["id"])
    return True


def ride(house, tr):
    p, t = house["pets"].get(tr["rider"] or ""), tram(tr)
    if p and t:
        p["room"], p["pos"] = t["room"], list(t["pos"])
        p.setdefault("rooms", {})[t["room"]] = house["tick"]


def rider_off(house, cfg, tr, force=False):
    """The rider gets down at a stop once its stops are up; and at once, wherever the tram is, when its mind has
    something to do (riding is the body's, not a thought), when it falls asleep, or when it can no longer ride."""
    from . import world
    p = house["pets"].get(tr["rider"] or "")
    if not p:
        tr["rider"] = None
        return
    up = tr["stopped"] and tr["ride"]["stops"] <= 0
    if not (force or up or world.busy(p) or p["stage"] == "dead" or p["sleep"]):
        return
    room = house["rooms"][p["room"]]
    p["pos"] = free_tile(house, cfg, room, p["pos"])
    p.pop("riding", None)
    tr["rider"] = None
    add_event(house, p, "you climbed down from the tram in %s" % room["name"])
    log(house, room["id"], "%s rode the train to %s" % (label(p), room["name"]), p["id"])
    if tr["ride"]["from"] != room["id"]:
        moment(house, "rail", "%s rode the train to %s" % (label(p), room["name"]), p["id"], room["id"])


# ---- for the view ----

def eta(house, cfg):
    """{room: tick it next stops there}, walked forward from where the train is; None for all while it sleeps."""
    tr, rail = train(house), house.get("rail")
    if not tr or not rail or not rail.get("legs"):
        return {}
    if tr["asleep"]:
        return {rid: None for rid in rail["rooms"]}
    C, L, t = R(cfg), rail["legs"], float(house["tick"])
    out, i = {}, tr["leg"]
    if tr["stopped"]:
        out[L[i]["room"]] = house["tick"]
        t += max(0, tr["wait"] - house["tick"])
    else:
        t += len(tr["path"]) / tr["speed"]
        if L[i]["stop"] and tr["left"] != i:
            out[L[i]["room"]] = int(t)   # (near enough: its platform is on the way)
            t += C["stop_ticks"]
    for _ in range(2 * len(L)):
        i = (i + 1) % len(L)
        t += (len(leg_tiles(rail, L[i])) - (1 if i == 0 else 0)) / tr["speed"]
        if L[i]["stop"]:
            out.setdefault(L[i]["room"], int(t))
            t += C["stop_ticks"]
    return out


def view(house, cfg):
    rail = house.get("rail")
    if not rail:
        return None
    due = eta(house, cfg)
    return {"built": rail["built"], "depot": rail["depot"], "route": rail["route"],
            "rooms": {rid: {k: v for k, v in x.items() if k != "arms"} | {"due": due.get(rid)} for rid, x in rail["rooms"].items()}}


def cart_view(house, cfg):
    tr = train(house)
    return [{"name": h.get("name") or h["bit"], "made": h["o"].get("made") if "o" in h else None, "to": h["to"]} for h in tr["held"]] if tr else []


# ---- asking the train (a mind's step) ----

ACTIONS = ("ask_train",)
BUSY = {"ask_train": "asking the train for something from the store"}
WRITTEN = {"ask_train": '{"type": "ask_train", "what": something kept in the store} (the train brings it from the store and sets it down by the platform here on its next round)'}


def ctx(house, cfg, pet):
    """What it could ask the train for: the kinds on the store's shelves (most first), or None."""
    from . import store
    if "ask_train" not in offered(house, cfg, pet, house["rooms"][pet["room"]]):
        return None
    return [k for k, v in sorted(store.stock(house, cfg).items(), key=lambda kv: -len(kv[1])) if k][:10]


def offered(house, cfg, pet, room):
    """Only once the rail is built, at a room's platform away from the store, one thing asked at a time."""
    from . import store
    rail = house.get("rail")
    if not rail or room["id"] not in rail["rooms"] or store.is_store(room) or any(a["pet"] == pet["id"] for a in rail["asked"]):
        return []
    return ["ask_train"] if store.stock(house, cfg) else []


def schema(c, one):
    return {"ask_train": [one("ask_train", what={"enum": c["train"]})] if c.get("train") else []}


def stub(t, c, pick):
    return {"type": t, "what": pick(c["train"])}


def check(a, house, cfg, pet, norm):
    from . import store
    if "ask_train" not in offered(house, cfg, pet, house["rooms"][pet["room"]]):
        return "there is no train to ask here"
    return None if store.find(house, cfg, norm(a.get("what"))) else "there is nothing like that in the store"


def apply(a, house, cfg, pet, norm):
    from . import store
    return store.ask(house, cfg, pet, store.find(house, cfg, norm(a.get("what")))), {}, "ask the train"


def sense(house, cfg, pet):
    """A line or two for its packet: riding, the train here or when it is next due, and what it could ask for."""
    from . import store
    rail, tr = house.get("rail"), train(house)
    if not rail or not tr:
        return []
    if pet.get("riding"):
        return ["you are riding in the tram at the back of %s, through the house" % called(tr)]
    out, rid = [], pet["room"]
    if rid in rail["rooms"]:
        if tr["stopped"] and tr["room"] == rid:
            out.append("%s is stopped at the platform here, its cart open: you could put things in it for the store" % called(tr))
        else:
            due = eta(house, cfg).get(rid)
            hrs = (due - house["tick"]) / cfg["ticks_per_hour"] if due else None
            out.append("%s comes through here on its rounds and stops at the platform; %s" % (
                called(tr), "it sleeps in its depot by the Works until morning" if due is None else "it is due soon" if hrs < 1 else "it is due in an hour or two" if hrs < 3 else "it will be a while"))
    if ctx(house, cfg, pet):
        out.append("in the store: %s; the train can bring you one" % store.stock_words(house, cfg))
    return out
