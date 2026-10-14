"""The hub (SPEC-v3.5.1): the machine room. A tenth room hung on the outside of the storeroom and found like any
other; the vending machine and the radio move into it, three screens there read the book's encyclopedia, a lit sign
on its wall runs the time, the forecast and the house's own news, and each family may raise a statue of its founder
in the middle of it. No model is asked for any of it."""
from .world import BACK, DIRS, LONG_AGO, add_event, label, moment, room_type

RID = "rhub"
KIND = "hub"
# a moment's kind -> what the sign calls it, and the little picture it shows first (SPEC-v3.5.1 §2)
HEADLINES = {"invented": ("invention", "star"), "discovery": ("discovery", "star"), "hatched": ("birth", None), "death": ("death", None),
             "built": ("built", None), "statue": ("statue", "star"), "room": ("found", None)}
ANIM = {"clear": "sun", "heat": "sun", "cloudy": "cloud", "rain": "rain", "storm": "rain", "snow": "snow"}
SAID = {"clear": "clear skies", "heat": "a hot day", "cloudy": "cloud", "rain": "rain", "storm": "a storm", "snow": "snow"}


def found(house):
    r = house["rooms"].get(RID)
    return r if r and r["type"] else None


def migrate(house, cfg):
    """Any house, new or lived in, gains the hub once: a door on the outside of the storeroom (north if it can,
    else west, east, south) to a room nobody has been in. The machine leaves the storeroom for it there and then;
    whoever is in the storeroom sees the door where it stood."""
    if RID in house["rooms"] or KIND not in cfg["house"]["rooms"]:
        return False
    for rid in sorted(house["rooms"]):   # (so the plan of what lies behind each door is drawn before the hub joins it)
        room_type(house, rid)
    store = next((rid for rid in sorted(house["rooms"]) if room_type(house, rid) == "storeroom"), None)
    if not store:
        return False
    cells = {tuple(r["cell"]) for r in house["rooms"].values()}
    x, y = house["rooms"][store]["cell"]
    d = next(d for d in ("north", "west", "east", "south") if (x + DIRS[d][0], y + DIRS[d][1]) not in cells and d not in house["rooms"][store]["doors"])
    house["rooms"][RID] = {"id": RID, "cell": [x + DIRS[d][0], y + DIRS[d][1]], "doors": {BACK[d]: store}, "type": None}
    house["rooms"][store]["doors"][d] = RID
    house.setdefault("plan", {})[RID] = KIND
    room = house["rooms"][store]
    if room["type"]:
        gone = [n for n, o in room["objects"].items() if o.get("fix", {}).get("machine")]
        for n in gone:
            del room["objects"][n]
        if gone:
            moment(house, "moved", "the vending machine has gone from %s; there is a new door in its %s wall, and a hum behind it" % (room["name"], d), None, store)
            for p in house["pets"].values():
                if p["room"] == store and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                    add_event(house, p, "the machine is gone from here; where it stood there is a door you have never seen, and a hum behind it")
    return True


def arrived(house, cfg, room):
    """The hub has just been walked into (world.generate_room): the radio comes to it from wherever it stands."""
    settle_radio(house, cfg)


def settle_radio(house, cfg):
    """The pets' radio stands in the hub once it is found, and stays there (SPEC-v3.5.1 §5)."""
    from . import world
    hub = found(house)
    if not hub:
        return
    for r in house["rooms"].values():
        for n, o in list((r.get("objects") or {}).items()) if r["type"] and r is not hub else ():
            if o.get("fix", {}).get("radio") and not o["fix"].get("visitor"):
                del r["objects"][n]
                o["fix"].pop("movable", None)
                o["pos"] = list(((cfg.get("layouts", {}).get(KIND) or {}).get("fixtures", {}).get(n) or {}).get("pos") or world.free_tile(house, cfg, hub, [10, 2]))
                hub["objects"][n] = o
                for p in house["pets"].values():
                    if p["room"] == r["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                        add_event(house, p, "the %s is gone from here" % n)


# ---- the lit sign (§2) ----

def headline(house, m):
    """A moment worth the sign: kept for it, newest last (world.moment calls this)."""
    k = HEADLINES.get(m["kind"])
    if not k:
        return
    t = house.setdefault("ticker", {"n": 0, "lines": []})
    t["n"] += 1
    text = m["text"][:1].upper() + m["text"][1:]
    t["lines"] = (t["lines"] + [{"n": t["n"], "tick": m["tick"], "kind": k[0], "text": text if len(text) <= 90 else text[:87].rsplit(" ", 1)[0] + "...", "anim": k[1]}])[-8:]


def forecast(house, cfg):
    from .world import weather_of
    kind = weather_of(house, cfg, house["clock"]["day"] + 1)
    return {"text": "Tomorrow: %s" % SAID.get(kind, kind), "anim": ANIM.get(kind, "cloud"), "kind": kind}


def ticker(house, cfg):
    """For the page: what the sign runs. The time it draws from the clock itself."""
    f = forecast(house, cfg)
    cold = house["clock"]["phase"] == "night" and cfg["house"]["seasons"][house["clock"]["season"]]["cold"] < 0
    return {"room": RID if found(house) else None, "forecast": {"text": f["text"], "anim": f["anim"]}, "cold": cold,
            "headlines": house.get("ticker", {}).get("lines", [])}


def read_sign(house, cfg, pet):
    """A pet awake in the hub reads the sign (physics, once a tick): tomorrow's weather once a day, and each headline
    once. It is told, not woken: what it read waits for its next thought."""
    hub = found(house)
    if not hub or pet["room"] != RID or pet["sleep"] or pet["stage"] in ("egg", "dead", "hatchling") \
            or not any(o.get("fix", {}).get("sign") for o in hub["objects"].values()):
        return
    seen = pet.setdefault("sign", {"day": None, "n": 0})
    if seen["day"] != house["clock"]["day"]:
        seen["day"] = house["clock"]["day"]
        add_event(house, pet, 'the lit sign on the wall runs: "%s"' % forecast(house, cfg)["text"])
    new = [l for l in house.get("ticker", {}).get("lines", []) if l["n"] > seen["n"]]
    for l in new[-2:]:
        add_event(house, pet, 'the lit sign on the wall runs: "%s"' % l["text"])
    if new:
        seen["n"] = new[-1]["n"]


# ---- the screens (§3) ----

def book_at(house, cfg, room, pet):
    """(name, tile) of what in this room it would read from: a screen nobody else is at, else the heavy book; or
    (None, None). A screen is someone's while they stand at it or for a world hour after their last question."""
    busy = {n for n, o in room["objects"].items() if o.get("screen") and o["screen"]["pet"] != pet["id"]
            and house["tick"] - o["screen"]["tick"] < cfg["ticks_per_hour"]}
    books = [(n, o["pos"]) for n, o in room["objects"].items() if o.get("fix", {}).get("book") and n not in busy]
    mine = [b for b in books if (room["objects"][b[0]].get("screen") or {}).get("pet") == pet["id"]]
    return (mine or books or [(None, None)])[0]


def heavy(o):
    """The heavy book itself, which can be carried: not a screen."""
    return o.get("fix", {}).get("book") and not o["fix"].get("terminal")


def wait_hours(cfg, room):
    return cfg["book"]["terminal_hours"] if any(o.get("fix", {}).get("terminal") for o in room["objects"].values()) else cfg["book"]["per_hours"]


def show(house, cfg, pet, room, q, found_):
    """What it asked and read is up on the glass of the screen it used, for Tyler to read."""
    name, _ = book_at(house, cfg, room, pet)
    o = room["objects"].get(name)
    if o and o["fix"].get("terminal"):
        o["screen"] = {"pet": pet["id"], "asked": q, "title": found_[0] if found_ else None, "text": found_[1] if found_ else None, "tick": house["tick"]}


# ---- the founder's statue (§4) ----

def founder(house, fam):
    """The first of a family: the earliest pet with no parent whose family (its own, or its first child's) is this."""
    for p in sorted(house["pets"].values(), key=lambda p: int(p["id"][1:])):
        kid = house["pets"].get((p.get("children") or [None])[0] or "")
        if not p.get("parent") and p.get("family", kid.get("family", 1) if kid else 1) == fam:
            return p
    return None


def honours(house, cfg, pet, P):
    """Does this pet want this statue begun: the eldest living of the family it honours, its founder dead."""
    fam, f = P["honours"], founder(house, P["honours"])
    kin = [p for p in house["pets"].values() if p.get("family", 1) == fam and p["stage"] not in ("egg", "dead")]
    return bool(f and f["stage"] == "dead" and pet.get("family", 1) == fam and pet is min(kin, key=lambda p: (p["laid"], p["id"])))


def begun(house, cfg, room, name, o, P):
    """Whose statue it is; and nothing made is left lying on its plinth."""
    from .world import free_tile
    o["statue"] = {"of": founder(house, P["honours"])["id"], "family": P["honours"]}
    for n, t in room["objects"].items():
        if n != name and "made" in t and t["pos"] == o["pos"] and not t.get("wall") and not t.get("on"):
            t["pos"] = free_tile(house, cfg, room, t["pos"], n)


def last_words(pet, data_dir=None):
    """What it last told its children: on it, or in its life.json once its record has been put away."""
    if pet.get("last_words"):
        return pet["last_words"]
    import json
    from pathlib import Path
    f = Path(data_dir or ".") / ("lineage-%s" % pet.get("lineage", 1)) / pet["id"] / "life.json"
    try:
        return json.loads(f.read_text()).get("last_words")
    except (OSError, ValueError):
        return None


def stood(house, cfg, pet, room, name, o):
    """It stands: a moment, the sign, and the family's want to give it a name, if its founder never had one."""
    s = o["statue"]
    f = house["pets"][s["of"]]
    s["name"] = f["name"]
    moment(house, "statue", "the statue of %s stands in %s" % (f["name"] or "the first one", room["name"]), pet["id"], room["id"])


def statue_view(house, cfg, o, v, data_dir=None):
    s = o.get("statue")
    if s:
        f = house["pets"].get(s["of"], {})
        v["statue"] = dict(s, genome=f.get("genome"), stage="elder", words=last_words(f, data_dir) if f else None)


def unnamed(house, pet, room=None):
    """A statue of its family's founder that stands with no name on it, in the room it is in: its name, or None."""
    room = room or house["rooms"][pet["room"]]
    return next((n for n, o in room["objects"].items() if o.get("statue") and o.get("fix", {}).get("built") and not o["statue"].get("name")
                 and o["statue"]["family"] == pet.get("family", 1)), None)


def name_it(house, cfg, pet, name):
    room = house["rooms"][pet["room"]]
    o = room["objects"][unnamed(house, pet)]
    o["statue"]["name"], o["statue"]["named_by"] = name, pet["id"]
    moment(house, "statue", "%s cut a name on the statue of the first one: %s" % (label(pet), name), pet["id"], room["id"])
    return "you cut a name into the statue's plaque: %s" % name


def candidates(house, cfg, pet, add, known):
    """The want to name the statue (wants.candidates)."""
    for r in known:
        for n, o in r["objects"].items():
            if o.get("statue") and o.get("fix", {}).get("built") and not o["statue"].get("name") and o["statue"]["family"] == pet.get("family", 1) and pet["stage"] in ("adult", "elder"):
                add("name", "statue|" + r["id"], "the statue of the first of your family stands in %s with no name on its plaque: you want to give the first one a name" % r["name"],
                    "named the statue of the first one", 3.0, room=r["id"])
