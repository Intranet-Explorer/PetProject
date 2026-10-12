"""The house (SPEC-v3 §6): one JSON-able dict holding every room, pet, creature and the weather.
Everything else is functions over it. The world is data; pets act only through the checked action set."""
import json
import random
import tomllib
from pathlib import Path

from .genome import START

ROOT = Path(__file__).parent.parent
NEEDS = ("energy", "comfort", "curiosity", "company")
STAGES = ("egg", "hatchling", "child", "youngling", "adult", "elder")
GENES = ("curious", "sensitive", "sociable", "bold", "patient", "playful", "fertile", "hardy", "orderly")   # orderly: SPEC-v3.3 §2.4, last so the older draws stay as they were
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
    # SPEC-v3.2: the art is data (view/assets/README.md). The engine reads the part of it that is rules: the catalog of
    # kinds a thing can be, how a thing made before kinds becomes one, and each room type's layout (where its fixtures
    # stand, which floor tiles furniture takes up, where a thing can hang on the wall).
    art = path.parent / "view" / "assets"
    read = lambda f, default: json.loads((art / f).read_text()) if (art / f).exists() else default
    cfg["kinds"] = read("kinds.json", {"sculpture": {"rank": 3, "wall": False, "not": [], "a": "a"}})
    cfg["from_parts"] = read("kinds-from-parts.json", {"shape": {}, "material": {}, "many": {"hanging": [], "then": "sculpture", "else": "sculpture"}, "pair": {}})
    cfg["activities"] = tomllib.loads((path.parent / "activities.toml").read_text())   # SPEC-v3.3 §1.1: what a body does by itself
    cfg["layouts"] = {f.stem: json.loads(f.read_text()) for f in sorted((art / "rooms").glob("*.json"))} if (art / "rooms").exists() else {}
    return derive(cfg)


def derive(cfg):
    """The numbers that follow from the clock. Call again after changing cfg["clock"]."""
    cfg["ticks_per_day"] = round(cfg["clock"]["day_seconds"] / cfg["clock"]["tick_seconds"])
    cfg["ticks_per_hour"] = cfg["ticks_per_day"] / 24
    cfg["dt"] = cfg["clock"]["tick_seconds"] / 10   # standing rates are written per 10 s
    # real seconds per world second on a live clock: a house whose world day is `day_seconds` can be watched at
    # another speed (`real_day_seconds`) without anything in the world changing length
    cfg["pace"] = cfg["clock"].get("real_day_seconds", cfg["clock"]["day_seconds"]) / cfg["clock"]["day_seconds"]
    cfg["W"], cfg["H"] = cfg["house"]["house"]["room_size"]
    from . import feel   # the words module keeps its thresholds as plain names; they come from here
    feel.STEPS, feel.SHIFT, feel.TREND = cfg["feel"]["steps"], cfg["feel"]["gene_shift"], cfg["feel"]["trend"]
    return cfg


def ticks(cfg, seconds):
    return max(1, round(seconds / cfg["clock"]["tick_seconds"]))


def wt(cfg, tick):
    """A tick as it counts toward the world's days. A house whose day was made longer (the live house went from one
    real hour to two on 12 October 2026) counts each tick before the change for more, so the clock, the date and
    everyone's age carry on from where they were."""
    s = cfg.get("shift")   # ponytail: one change of day length per house; a second needs a list of these
    return tick + min(tick, s["until"]) * s["by"] if s else tick


def days(cfg, since, tick):
    """World days from one tick to another."""
    return (wt(cfg, tick) - wt(cfg, since)) / cfg["ticks_per_day"]


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
    at = 8 + wt(cfg, tick) / cfg["ticks_per_hour"]
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
    tiles = [o["pos"] for n, o in room["objects"].items() if n != but and not o.get("wall") and not o.get("on")]   # what hangs on a wall or sits on a shelf takes no floor
    tiles += room.get("blocked", [])   # the layout's furniture (SPEC-v3.2 §4)
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


def fixture(f, rng=None):
    """A fixture as it stands in a room when the room is new, from its line in house.toml."""
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
    return o


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
        room["objects"][f["name"]] = fixture(f, rng)
    kinds = spec["bits"]
    if kinds == "any":
        kinds = {b: 1 for b in rng.sample(sorted(b for b, v in cfg["house"]["bits"].items() if not v.get("late")), 4)}
    layout(cfg, room)
    for bit, n in kinds.items():
        for _ in range(n):
            spot = free_tile(house, cfg, room, [rng.randrange(cfg["W"]), rng.randrange(cfg["H"])])
            room["spots"].append({"bit": bit, "pos": spot, "ready": True, "back": None, "loose": False})
    return room


def arrived(house, what):
    """Has this discovery come to the house yet (SPEC-v3.1 §1)?"""
    return what in house.get("v31", {}).get("arrived", {})


def bit_kinds(house, cfg):
    """The bits that can turn up by themselves: all of them but the ones whose discovery has not come yet."""
    return sorted(b for b, v in cfg["house"]["bits"].items() if not v.get("late") or arrived(house, v["late"]))


def layout(cfg, room):
    """Lay a room out as its layout file says (SPEC-v3.2 §4): which floor tiles the scenery's furniture takes, where
    things can hang, and where each fixture stands. A fixture nobody could have moved goes to its tile; one that can
    be moved is left wherever it has been put. Safe to call again whenever the layouts change."""
    L = cfg.get("layouts", {}).get(room["type"]) or {}
    room["blocked"] = [list(t) for t in L.get("blocked", [])]
    room["wall_slots"] = [list(t) for t in L.get("wall_slots", [[2, 0], [5, 0], [9, 0]])]
    for name, f in (L.get("fixtures") or {}).items():
        o = room["objects"].get(name)
        if o and "fix" in o and "pos" in f and not o["fix"].get("movable") and not o["fix"].get("sun"):
            o["pos"] = list(f["pos"])
        if o and "fix" in o and f.get("wall"):   # a window, a mirror, a lantern on its hook: it hangs, and takes no floor
            o["wall"] = True


def settle(house, cfg, room):
    """After a layout has been laid over a room that was already lived in: nothing made, lying about or standing
    is left on a tile the furniture now takes, and bits that have a proper place in this room lie there."""
    L = cfg.get("layouts", {}).get(room["type"]) or {}
    fixed = [o["pos"] for o in room["objects"].values() if "fix" in o]
    bad = lambda pos: list(pos) in room.get("blocked", []) or list(pos) in fixed
    for n, o in room["objects"].items():
        if "fix" not in o and not o.get("wall") and bad(o["pos"]):
            o["pos"] = free_tile(house, cfg, room, o["pos"], n)
    for s in room["spots"]:
        places = [list(t) for t in (L.get("bit_spots") or {}).get(s["bit"], [])]
        if places and not s["loose"] and s["pos"] not in places:
            s["pos"] = next((t for t in places if t not in taken(house, room)), s["pos"])
        if bad(s["pos"]):
            s["pos"] = free_tile(house, cfg, room, s["pos"])
    for p in house["pets"].values():
        if p["room"] == room["id"] and p["stage"] != "dead" and bad(p["pos"]) and list(p["pos"]) in room.get("blocked", []):
            p["pos"] = free_tile(house, cfg, room, p["pos"])


# SPEC-v3.2 §6: stages in plain words, for whoever is watching. The pets are told nothing new.
STAGE_WORD = {"egg": "egg", "hatchling": "little one", "child": "little one", "youngling": "young one", "adult": "grown", "elder": "old one"}


def a_stage(stage):
    """A stage in a sentence: "a little one", "a grown one", "an old one"."""
    word = STAGE_WORD.get(stage, stage)
    return "%s %s" % ("an" if word[0] in "aeiou" else "a", word if word.endswith("one") or word == "egg" else word + " one")


def neighbours(house, rid):
    """The rooms next door that someone has already found: {direction: room id}."""
    return {d: r for d, r in house["rooms"][rid]["doors"].items() if house["rooms"][r]["type"]}


# ---- pets ----

def new_temper(rng):
    return {g: round(rng.uniform(0.25, 0.75), 2) for g in GENES}


def new_pet(house, cfg, room, pos, genome=None, temper=None, parent=None, name=None, told=None, family=None):
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
        # SPEC-v3.1: which family it is of, the songs it knows, what it has read, what the box last said in its hearing,
        # how long it has spent with each pet of another family, and how many times its piece of chalk has written
        "family": family or (mother["family"] if mother and "family" in mother else 1), "songs": [], "read": [], "box": [],
        "with": {}, "knows": [], "chalked": 0, "animals": [],
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


def family(pet):
    return pet.get("family", 1)


def knows(pet, other):
    """Is `other` someone it knows: one of its own family, or a stranger it has spent long enough beside (§7.2)?"""
    return family(pet) == family(other) or other["id"] in pet.get("knows", [])


ORDINAL = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
           "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth"]
TENS = {20: ("twentieth", "twenty"), 30: ("thirtieth", "thirty"), 40: ("fortieth", "forty"), 50: ("fiftieth", "fifty"), 60: ("sixtieth", "sixty"),
        70: ("seventieth", "seventy"), 80: ("eightieth", "eighty"), 90: ("ninetieth", "ninety")}


def ordinal(n):
    """first, second ... ninety-ninth, in words: nothing a pet is shown has a figure in it."""
    if n < 20:
        return ORDINAL[n]
    if n < 100:
        whole, part = TENS[n // 10 * 10]
        return whole if n % 10 == 0 else "%s-%s" % (part, ORDINAL[n % 10])
    return "latest"


def label(pet):
    """A pet's name, or for one that has none a label that is its own: "the first one", "the third one", by the order
    they came into the house. (They were all "the little one", and "the little one told the little one something"
    said nothing.)"""
    n = int(pet["id"][1:]) if pet["id"][1:].isdigit() else 0
    return pet["name"] or ("the %s one" % ordinal(n) if n else "the little one")


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


def busy(p):
    """Is it carrying out something it decided? Once the last of that is done its thought stays with it, idle, until
    it thinks again, and its body carries on (SPEC-v3.3 §1)."""
    return bool(p.get("plan")) and not p["plan"].get("idle")


def moving(p):
    """Is it on the move right now: walking to something it decided, or to something its body is about?"""
    now = (p.get("body") or {}).get("now")
    return p["plan"]["left"] is None if busy(p) else bool(now) and now.get("began") is None


def moment(house, kind, text, pet=None, room=None):
    """Something worth seeing (§9.1): one line, with what it is about."""
    house["n"]["moment"] += 1
    m = {"n": house["n"]["moment"], "tick": house["tick"], "day": house["clock"]["day"], "hour": house["clock"]["hour"],
         "kind": kind, "text": text, "pet": pet, "room": room}
    house["moments"].append(m)
    del house["moments"][:-400]
    house["last_moment"] = house["tick"]
    house["fresh_moments"].append(m)   # drained by the logger
