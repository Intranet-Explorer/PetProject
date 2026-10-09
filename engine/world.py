"""The house (SPEC-v3 §6): one JSON-able dict holding every room, pet, creature and the weather.
Everything else is functions over it. The world is data; pets act only through the checked action set."""
import random
import tomllib
from pathlib import Path

from .genome import START

ROOT = Path(__file__).parent.parent
NEEDS = ("energy", "comfort", "curiosity", "company")
STAGES = ("egg", "hatchling", "child", "youngling", "adult", "elder")
GENES = ("curious", "sensitive", "sociable", "bold", "patient", "playful", "fertile", "hardy")
DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
BACK = {"north": "south", "south": "north", "west": "east", "east": "west"}
LONG_AGO = -10**7


def merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path=ROOT / "config.toml", profile=None):
    """config.toml with the materials and the house beside it; a profile (config.<name>.toml) is laid over the top."""
    path = Path(path)
    cfg = tomllib.loads(path.read_text())
    cfg["materials"] = tomllib.loads((path.parent / "materials.toml").read_text())
    cfg["house"] = tomllib.loads((path.parent / "house.toml").read_text())
    if profile:
        merge(cfg, tomllib.loads((path.parent / ("config.%s.toml" % profile)).read_text()))
    cfg["profile"] = profile
    return derive(cfg)


def derive(cfg):
    """The numbers that follow from the clock. Call again after changing cfg["clock"]."""
    cfg["ticks_per_day"] = round(cfg["clock"]["day_seconds"] / cfg["clock"]["tick_seconds"])
    cfg["ticks_per_hour"] = cfg["ticks_per_day"] / 24
    cfg["dt"] = cfg["clock"]["tick_seconds"] / 10   # standing rates are written per 10 s
    cfg["W"], cfg["H"] = cfg["house"]["house"]["room_size"]
    return cfg


def ticks(cfg, seconds):
    return max(1, round(seconds / cfg["clock"]["tick_seconds"]))


def hours(cfg, n):
    """World hours as ticks."""
    return max(1, round(n * cfg["ticks_per_hour"]))


def rnd(house, *key):
    """Randomness with no state to save: the same house, moment and question always give the same answer,
    so a restart changes nothing and a house can be rebuilt from its seed (§6.1)."""
    return random.Random("|".join(str(k) for k in (house["seed"],) + key))


# ---- time, season, weather ----

def clock(cfg, tick):
    """Life in the house starts at 08:00 on day 1 of spring."""
    at = 8 + tick / cfg["ticks_per_hour"]
    day, hour = 1 + int(at // 24), at % 24
    names = list(cfg["house"]["seasons"])
    span = cfg["house"]["house"]["season_days"]
    season = names[((day - 1) // span) % len(names)]
    s = cfg["house"]["seasons"][season]
    phase = "day" if s["sunrise"] <= hour < s["sunset"] else "dusk" if s["sunset"] <= hour < s["sunset"] + 2.5 else "night"
    return {"hour": round(hour, 2), "day": day, "phase": phase, "season": season,
            "morning": s["sunrise"] <= hour < s["sunrise"] + 3, "year": 1 + (day - 1) // (span * len(names))}


def weather_of(house, cfg, day):
    """One kind of weather per day, drawn from the season's mix (§6.4), unless the real sky is being used."""
    real = house.get("real_weather")
    if real and real.get("day") == day:
        return real["kind"]
    names = list(cfg["house"]["seasons"])
    season = names[((day - 1) // cfg["house"]["house"]["season_days"]) % len(names)]
    mix = cfg["house"]["seasons"][season]["weather"]
    return rnd(house, "weather", day).choices(list(mix), weights=list(mix.values()))[0]


def sunny(house):
    return house["clock"]["phase"] == "day" and house["weather"] in ("clear", "heat")


def power_on(house):
    return house["tick"] >= house["power_out_until"]


# ---- geometry ----

def dist(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def in_room(cfg, t):
    return (isinstance(t, list) and len(t) == 2 and all(type(v) is int for v in t)
            and 0 <= t[0] < cfg["W"] and 0 <= t[1] < cfg["H"])


def taken(house, room, but=None):
    """Tiles with something on them: objects, bits lying about, door thresholds, eggs, water."""
    tiles = [o["pos"] for n, o in room["objects"].items() if n != but]
    tiles += [s["pos"] for s in room["spots"] if s["ready"]]
    tiles += [p["pos"] for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] == "egg"]
    tiles += [list(house["door_tiles"][d]) for d in room["doors"]]
    for o in room["objects"].values():
        tiles += o.get("fix", {}).get("water", [])
    return tiles


def free_tile(house, cfg, room, near, but=None):
    """The tile asked for if nothing is on it, else the nearest free one."""
    used = taken(house, room, but)
    tiles = [[x, y] for x in range(cfg["W"]) for y in range(cfg["H"]) if [x, y] not in used]
    return min(tiles, key=lambda t: (dist(t, near), abs(t[0] - near[0]) + abs(t[1] - near[1])), default=list(near))


def beside(cfg, pos, frm):
    """The tile next to pos that is nearest to frm."""
    tiles = [[pos[0] + dx, pos[1] + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
             if (dx or dy) and 0 <= pos[0] + dx < cfg["W"] and 0 <= pos[1] + dy < cfg["H"]]
    return min(tiles, key=lambda t: dist(t, frm))


# ---- building the house ----

def door_plan(cfg, seed):
    """Which rooms are joined by doors. Fixed when the house is made; what lies behind a door is not decided
    until someone walks through it (§6.1). A random spanning tree over the grid, then a couple of extra doors."""
    gx, gy = cfg["house"]["house"]["grid"]
    most, rng = cfg["house"]["house"]["max_doors"], random.Random("%s|doors" % seed)
    rid = lambda x, y: "r%d%d" % (x, y)
    doors = {rid(x, y): {} for x in range(gx) for y in range(gy)}
    start = (gx // 2, gy // 2)
    seen, frontier = {start}, [start]

    def link(a, d, b):
        doors[rid(*a)][d], doors[rid(*b)][BACK[d]] = rid(*b), rid(*a)

    while frontier:
        cell = frontier[rng.randrange(len(frontier))]
        ways = [(d, (cell[0] + dx, cell[1] + dy)) for d, (dx, dy) in DIRS.items()
                if 0 <= cell[0] + dx < gx and 0 <= cell[1] + dy < gy and (cell[0] + dx, cell[1] + dy) not in seen]
        if not ways or len(doors[rid(*cell)]) >= most:
            frontier.remove(cell)
            continue
        d, nxt = rng.choice(ways)
        link(cell, d, nxt)
        seen.add(nxt)
        frontier.append(nxt)
    for x in range(gx):       # if the cap on doors boxed a cell in, join it to any neighbour all the same
        for y in range(gy):
            for d, (dx, dy) in DIRS.items():
                n = (x + dx, y + dy)
                if (x, y) not in seen and n in seen:
                    link((x, y), d, n)
                    seen.add((x, y))
    for _ in range(2):        # a loop or two, so the house is not a tree
        x, y = rng.randrange(gx), rng.randrange(gy)
        for d, (dx, dy) in DIRS.items():
            n = (x + dx, y + dy)
            if 0 <= n[0] < gx and 0 <= n[1] < gy and d not in doors[rid(x, y)] \
                    and len(doors[rid(x, y)]) < most and len(doors[rid(*n)]) < most:
                link((x, y), d, n)
                break
    return doors, rid(*start)


def new_house(cfg, seed=None):
    seed = cfg["house"]["house"]["seed"] if seed is None else seed
    doors, start = door_plan(cfg, seed)
    house = {
        "seed": seed, "tick": 0, "clock": clock(cfg, 0), "weather": "clear", "start": start,
        "door_tiles": cfg["house"]["house"]["doors"],
        "rooms": {rid: {"id": rid, "cell": [int(rid[1]), int(rid[2])], "doors": d, "type": None} for rid, d in doors.items()},
        "pets": {}, "creatures": [], "moments": [], "fresh_moments": [],
        "n": {"pet": 0, "thing": 0, "lineage": 0, "moment": 0, "creature": 0},
        "lineage": None,                    # {"id", "started", "ended", "founder", "drift"}
        "power_out_until": LONG_AGO, "events": [], "next_event": None, "last_moment": 0,
        "visitor_last": LONG_AGO, "visitor_room": None, "chronicle": [], "unused_types": [], "calls": [], "said": [],
        "claims": [], "gone_things": [], "fresh_events": [], "fresh_creatures": [],
        "shut": {},                         # "room|direction" -> the tick a draught lets go of that door
        "names": {},                        # every thing's name ever used -> how many times, so names stay unique
    }
    types = [t for t in cfg["house"]["rooms"] if t != "nursery"]
    rnd(house, "types").shuffle(types)
    house["unused_types"] = types
    house["weather"] = weather_of(house, cfg, 1)
    generate_room(house, cfg, start, "nursery")
    return house


def room_type(house, rid):
    """What kind of room lies at this place in the house. Which type goes where is fixed by the house's seed
    from the start (so a door can smell of what is behind it); the room itself is not made until someone
    walks in (§6.1)."""
    room = house["rooms"][rid]
    if room["type"]:
        return room["type"]
    if "plan" not in house:
        blank = sorted(r for r, x in house["rooms"].items() if not x["type"])
        house["plan"] = dict(zip(blank, house["unused_types"] + ["storeroom"] * len(blank)))
    return house["plan"][rid]


def generate_room(house, cfg, rid, kind=None, by=None):
    """Make a room, the first time it is needed. Seeded, so the same house grows the same way."""
    room = house["rooms"][rid]
    if room["type"]:
        return room
    kind = kind or room_type(house, rid)
    house.get("plan", {}).pop(rid, None)
    spec, rng = cfg["house"]["rooms"][kind], rnd(house, "room", rid)
    room.update(type=kind, name=spec["name"], found=house["tick"], by=by, objects={}, spots=[],
                paint={"wall": None, "floor": None}, wet_until=LONG_AGO, cold_until=LONG_AGO, drift=None)
    for f in spec["fixtures"]:
        o = {"pos": list(f["pos"]), "fix": {k: v for k, v in f.items() if k not in ("name", "pos")}}
        if "light" in f:
            o["state"] = f["light"]
        elif "states" in f:
            o["state"] = f["states"][0]
        elif "meal" in f:
            o["state"], o["servings"] = "full", f["meal"]
        elif f.get("plant"):
            o["grow"], o["state"] = round(rng.uniform(0.2, 0.7), 2), "growing"
        elif f.get("window"):
            o["state"] = "closed"
        room["objects"][f["name"]] = o
    kinds = spec["bits"]
    if kinds == "any":
        kinds = {b: 1 for b in rng.sample(sorted(cfg["house"]["bits"]), 4)}
    for bit, n in kinds.items():
        for _ in range(n):
            spot = free_tile(house, cfg, room, [rng.randrange(cfg["W"]), rng.randrange(cfg["H"])])
            room["spots"].append({"bit": bit, "pos": spot, "ready": True, "back": None, "loose": False})
    return room


def neighbours(house, rid):
    """The rooms next door that someone has already found: {direction: room id}."""
    return {d: r for d, r in house["rooms"][rid]["doors"].items() if house["rooms"][r]["type"]}


# ---- pets ----

def new_temper(rng):
    return {g: round(rng.uniform(0.25, 0.75), 2) for g in GENES}


def new_pet(house, cfg, room, pos, genome=None, temper=None, parent=None, name=None, told=None):
    """An egg. Everything a pet is, in one dict; its beliefs and journal live in its own folder."""
    house["n"]["pet"] += 1
    pid = "p%d" % house["n"]["pet"]
    rng = rnd(house, "pet", pid)
    mother = house["pets"].get(parent)
    pet = {
        "id": pid, "name": name, "lineage": house["lineage"]["id"], "gen": mother["gen"] + 1 if mother else 1,
        "parent": parent, "children": [], "word": rng.choice(["mother", "mother", "father", "father", "parent"]),
        "room": room, "pos": list(pos), "stage": "egg", "laid": house["tick"], "born": None, "died": None, "cause": None,
        "stage_at": {"egg": house["tick"]},
        "needs": {"energy": 70.0, "comfort": 60.0, "curiosity": 60.0, "company": 55.0},
        "trend": {}, "said": None, "genome": dict(genome or START, marks=list((genome or START).get("marks", []))),
        "temper": temper or new_temper(rng), "eggs": 0, "carrying": [], "useful": [], "made": 0,
        "plan": None, "last_plan": None, "thinking": None, "news": [], "seen": -1, "last_call": LONG_AGO, "calls": [],
        "events": [], "inbox": [], "offers": [], "heard": {}, "lost": [], "gathered": {}, "called": "", "seen_at": {}, "times": {}, "scent": {},
        "told": told or [],                   # what others told it: [{"by", "who", "kind", "text", "tick"}]
        "message": [],                        # every version of its own message to its children: [{"tick", "text"}]
        "project": None, "projects": [],      # {"text", "since"}, and the finished or abandoned ones
        "rooms": {}, "known": {}, "met": {},  # rooms it has been in, pets it knows, creatures it has met
        "sleep": None, "last_night": None, "diary": [], "portraits": [], "bodies": {},
        "well": [0.0, 0], "low_since": None, "weak": False, "lost_days": 0.0, "span": None,
        "phase_seen": house["clock"]["phase"], "following": None, "spring": 0, "near_window": 0.0,
        "reviewed": [], "exploits": {}, "last_words": None, "life": None, "trust": {}, "meter": [0, 0],
    }
    house["pets"][pid] = pet
    if mother:
        mother["children"].append(pid)
    return pet


def alive(house):
    return [p for p in house["pets"].values() if p["stage"] != "dead"]


def here(house, pet, awake=False):
    """The other living, hatched pets in the same room."""
    return [p for p in house["pets"].values() if p["room"] == pet["room"] and p["id"] != pet["id"]
            and p["stage"] not in ("egg", "dead") and not (awake and p["sleep"])]


def label(pet):
    return pet["name"] or "the little one"


KIN = {"mother": ("daughter", "sister", "grandmother", "granddaughter"), "father": ("son", "brother", "grandfather", "grandson"),
       "parent": ("child", "sibling", "grandparent", "grandchild")}


def relation(house, me, other):
    """What `other` is to `me`, in the word a pet would use: mother, son, sister, grandmother, or nothing."""
    pets = house["pets"]
    child, sibling, grand, grandchild = KIN[other["word"]]
    if me["parent"] == other["id"]:
        return other["word"]
    if other["parent"] == me["id"]:
        return child
    if me["parent"] and me["parent"] == other["parent"]:
        return sibling
    if me["parent"] and pets.get(me["parent"], {}).get("parent") == other["id"]:
        return grand
    if other["parent"] and pets.get(other["parent"], {}).get("parent") == me["id"]:
        return grandchild
    return None


def who(house, me, other):
    """How `me` would name `other`: "Pip, your mother", "your mother", "Sol"."""
    rel, name = relation(house, me, other), other["name"]
    if rel and name:
        return "%s, your %s" % (name, rel)
    return "your %s" % rel if rel else label(other)


# ---- what happened, for the pets and for the story ----

def add_event(house, pet, text):
    """Into one pet's own memory of what happened to it."""
    pet["events"].append([house["tick"], text])
    del pet["events"][:-120]


def witness(house, pet, text):
    """What `pet` just did, as the others awake in the room saw it (§7.1)."""
    for other in here(house, pet, awake=True):
        add_event(house, other, text)


def moment(house, kind, text, pet=None, room=None):
    """Something worth seeing (§9.1): one line, with what it is about."""
    house["n"]["moment"] += 1
    m = {"n": house["n"]["moment"], "tick": house["tick"], "day": house["clock"]["day"], "hour": house["clock"]["hour"],
         "kind": kind, "text": text, "pet": pet, "room": room}
    house["moments"].append(m)
    del house["moments"][:-400]
    house["last_moment"] = house["tick"]
    house["fresh_moments"].append(m)   # drained by the logger
