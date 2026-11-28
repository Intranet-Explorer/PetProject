"""Outdoors: the yard and the meadow (SPEC-v3.6c §4). Two places south of the house, each the size of a room with no
walls: the yard through a gate in the garden's south wall, the meadow west of the yard. They are hung on once, like
the machine room (migrate), and are found at once: the map shows them and the gate is new.

The weather is the house's own (clock, season, weather), and it is real out there. Hobs go out by day in fair
weather; the gate is shut at dusk, on a day of storm and in the coldest weather, and whoever is out comes in (their
body heads for the gate; any still out an hour later is in by the fire all the same). A little one goes out only
with a grown hob out there or by the gate, and comes in when none is. Forage grows on the ground like any room's bits
and regrows; a bit dropped outdoors weathers away in a day; what is left out goes in with the evening tidy (floors.py).
Creatures come by day (a rabbit, a squirrel, a hedgehog, butterflies, birds) and an owl at dusk; they have no minds.
In the meadow a hob can fish in the stream by paw. The rail stays indoors and the sweeper does not go out.
Switch: [outdoors] on (off: the gate stays shut and nobody goes out)."""
from . import feel
from .world import BACK, add_event, dist, free_tile, generate_room, hours, label, moment, rnd, ticks

YARD, MEADOW = "ryard", "rmeadow"
OUT = (YARD, MEADOW)
GATE = "south"   # the garden's south wall
FAIR = ("clear", "heat", "cloudy")
GROWN = ("youngling", "adult", "elder")
DAY_KINDS = ("rabbit", "squirrel", "hedgehog", "butterfly")
DOING = {"rabbit": "nibbling the grass", "squirrel": "darting about with something in its cheeks", "hedgehog": "snuffling through the leaves",
         "butterfly": "flitting over the flowers", "owl": "watching from a post", "bird": "hopping about, pecking"}


def O(cfg):
    return cfg.get("outdoors", {})


def is_out(rid):
    return rid in OUT


def garden(house):
    """The garden: where the gate is (once there is one)."""
    y = house["rooms"].get(YARD)
    return house["rooms"][y["doors"][BACK[GATE]]] if y else next((r for r in house["rooms"].values() if r.get("type") == "garden"), None)


def gate_room(house):
    y = house["rooms"].get(YARD)
    return y["doors"][BACK[GATE]] if y else None


def usable(house, cfg):
    """Is the outdoors there and switched on (the yard a place to build in, to go out to)?"""
    return YARD in house["rooms"] and bool(O(cfg).get("on"))


def switched_on(house):
    """The same, from the house alone (the gate says "shut" only while the outdoors is switched off)."""
    return YARD in house["rooms"] and (house.get("outdoors") or {}).get("why") != "shut"


def migrate(house, cfg):
    """Once, on any house whose garden has a free south wall: the yard behind the gate and the meadow beside it. Not
    while [outdoors] is switched off."""
    if YARD in house["rooms"] or "yard" not in cfg["house"]["rooms"] or not O(cfg).get("on"):
        return False
    g = garden(house)
    if not g:
        return False
    gx, gy = g["cell"]
    cells = {tuple(r["cell"]) for r in house["rooms"].values()}
    side = "west" if (gx - 1, gy + 1) not in cells else "east"   # (the meadow is west of the yard where there is room)
    if GATE in g["doors"] or (gx, gy + 1) in cells or (gx + (-1 if side == "west" else 1), gy + 1) in cells:
        return False
    house["rooms"][YARD] = {"id": YARD, "cell": [gx, gy + 1], "doors": {BACK[GATE]: g["id"], side: MEADOW}, "type": None}
    house["rooms"][MEADOW] = {"id": MEADOW, "cell": [gx + (-1 if side == "west" else 1), gy + 1], "doors": {BACK[side]: YARD}, "type": None}
    g["doors"][GATE] = YARD
    for rid, kind in ((YARD, "yard"), (MEADOW, "meadow")):
        house.setdefault("plan", {})[rid] = kind
        room = generate_room(house, cfg, rid, kind)
        room["outdoor"] = True
    from . import spotlight
    spotlight.queue(house, cfg, "outdoors", "THE YARD", "the yard and the meadow, outside the garden gate", YARD)   # SPEC-v3.6c §3: a new outdoor place
    moment(house, "outdoors", "a gate has appeared in the garden's south wall: beyond it, a yard, and a meadow with a stream", None, g["id"])
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead"):
            add_event(house, p, "there is a gate in the garden's south wall now, and outside it a yard and a meadow: grass, a stream, trees, open sky")
            p["news"].append("event")
    return True


def why_shut(house, cfg):
    """Why the gate is shut just now, or None when it is open."""
    if not O(cfg).get("on"):
        return "shut"
    c = house["clock"]
    if c["phase"] == "night":
        return "night"
    if c["phase"] == "dusk":
        return "dusk"
    if house["weather"] == "storm":
        return "storm"
    if c["season"] == "winter" and house["weather"] == "snow":
        return "cold"
    if house["weather"] not in FAIR:
        return "rain" if house["weather"] == "rain" else "weather"
    return None


SHUT = {"night": "it is night: the garden gate is shut", "dusk": "dusk is falling: the garden gate is shut for the night, and everyone outside comes in",
        "storm": "a storm is coming: the garden gate is shut, and everyone outside comes in", "cold": "it is bitterly cold: the garden gate is shut",
        "rain": "it is raining: the garden gate is shut until it clears", "weather": "the weather has turned: the garden gate is shut", "shut": "the garden gate is shut"}


def gate(house, cfg):
    """Open or shut the gate as the day and the weather say; everyone near is told when it changes."""
    g = garden(house)
    if not g or YARD not in house["rooms"]:
        return
    why = why_shut(house, cfg)
    st = house.setdefault("outdoors", {"open": False, "why": "shut"})
    key = "%s|%s" % (g["id"], GATE)
    if why:
        house["shut"][key] = house["tick"] + 10 ** 6   # (lifted here, never by a draught letting go)
    else:
        house["shut"].pop(key, None)
    was, st["why"] = st["open"], why
    st["open"] = not why
    if was == st["open"]:
        return
    text = "the garden gate stands open: it is a fine day outside" if st["open"] else SHUT[why]
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead") and (p["room"] in OUT or p["room"] == g["id"]):
            add_event(house, p, text)
            p["news"].append("event")


def grown_near(house, pet):
    """Is a grown hob out there, or in the garden by the gate, awake?"""
    return any(p is not pet and p["stage"] in GROWN and not p["sleep"] and (p["room"] in OUT or p["room"] == gate_room(house)) for p in house["pets"].values())


def barred(house, cfg, pet, rid, d):
    """Why this hob may not go through this door just now (actions.check, body), or None."""
    from . import conflict
    if pet.get("outcast") and conflict.on(cfg) and rid in OUT and house["rooms"][rid]["doors"].get(d) not in OUT:   # SPEC-v4.0 §7.4
        return "you were driven out of the house"
    if rid in OUT and staying_out(house, cfg, pet) and (house["rooms"][rid]["doors"].get(d) not in OUT or rid == shelter_room(house, cfg, pet)):
        return "you mean to sleep out under your shelter tonight"
    if d == GATE and rid == gate_room(house):
        why = why_shut(house, cfg)
        if why:
            return SHUT[why].split(":")[0] + ": the gate is shut" if why != "shut" else "the gate is shut"
        if pet["stage"] not in GROWN and not grown_near(house, pet):
            return "a little one goes out only with a grown one nearby"
    return None


def come_in(house, cfg, pet):
    """Must this hob come in now: it is out, and the gate is shut, or it is little and no grown hob is out there? Not
    one whose own shelter stands here (SPEC-v5.3 §3), unless it is awake and hungry: it comes in for food."""
    if pet["room"] not in OUT or pet["stage"] in ("egg", "dead"):
        return False
    from . import conflict
    if pet.get("outcast") and conflict.on(cfg) and O(cfg).get("on"):   # SPEC-v4.0 §7.4: an outcast lives out there
        return False
    if staying_out(house, cfg, pet):
        return False
    return bool(why_shut(house, cfg)) or (pet["stage"] not in GROWN and not any(p["room"] in OUT and p["stage"] in GROWN and not p["sleep"] for p in house["pets"].values()))


def exposed(house, cfg, pet):
    """SPEC-v4.2 §2.6 (health.daily asks, in the small hours): is it out under the sky through a bitter night: in
    winter, a cold snap, snow or a storm? An outcast lives out here (come_in), so its winter is the hard one; the
    visitor's step-in lets one in."""
    c = house["clock"]
    return unsheltered(house, cfg, pet) and c["phase"] == "night" and (c["season"] == "winter" or house["weather"] in ("snow", "storm")
                                                             or house.get("cold_snap", -1) > house["tick"])


def staying_out(house, cfg, pet):
    """SPEC-v5.3 §3: a hob whose own shelter stands outdoors, out at dusk or by night, stays out to sleep under it,
    unless it is awake and hungry: then it comes in for food."""
    if not is_out(pet["room"]) or not O(cfg).get("on") or house["clock"]["phase"] == "day":
        return False
    from . import projects
    sh = projects.sheltered(house, cfg, pet)
    return bool(sh and is_out(sh[0])) and (bool(pet["sleep"]) or not ("hunger" in pet["needs"] and feel.level(pet, "hunger") >= 2))


def shelter_room(house, cfg, pet):
    from . import projects
    return (projects.sheltered(house, cfg, pet) or [None])[0]


def unsheltered(house, cfg, pet):
    """Out under the open sky, with no shelter of its own here (SPEC-v5.3 §3: exposure is for the unsheltered)."""
    if not is_out(pet["room"]):
        return False
    from . import projects
    s = projects.sheltered(house, cfg, pet)
    return not (s and s[0] == pet["room"])


# SPEC-v5.3 §3 (helper A): plots in each of the yard and the meadow (five each since v5.3.1) (contracts.PLOTS), named by what is beside
# them, and two landmarks the model can name: a willow in the meadow, a standing stone by the pond
PLOT_AT = {YARD: (("by the shade tree", [3, 1]), ("by the fire pit", [8, 5]), ("by the fence", [2, 6]), ("by the woodpile", [9, 3]), ("by the shed", [8, 7])),
           MEADOW: (("by the willow", [9, 4]), ("by the stream", [5, 6]), ("in the long grass", [4, 3]), ("by the boulder", [7, 3]), ("by the bramble", [10, 1]))}
LANDMARKS = (("rmeadow", "willow", [10, 3], "an old willow leaning over the long grass, its branches trailing"),
             ("pond", "standing stone", [1, 1], "a grey standing stone at the water's edge, older than the house"))


def plots(house, cfg=None):
    """API53: the yard's and the meadow's plots (contracts.site, kind "plot"), made once each room is there, and the
    landmarks. [site()]."""
    from . import contracts as K
    from .world import fixture
    S = house.setdefault("v5", {}).setdefault("sites", {})
    for rid, n in K.PLOTS.items():
        room = house["rooms"].get(rid)
        if not room or not room.get("type"):
            continue
        for i, (name, at) in enumerate(PLOT_AT[rid][:n]):
            if "%s:%d" % (rid, i) in S:   # (v5.3.1: a house made with three an area gains the rest)
                continue
            t = free_tile(house, cfg, room, at) if cfg else list(at)
            S["%s:%d" % (rid, i)] = K.site({"id": "%s:%d" % (rid, i), "kind": "plot", "room": rid, "tiles": [t], "name": name, "since": house["tick"]})
    for where, name, at, says in LANDMARKS:
        room = house["rooms"].get(where) if where in house["rooms"] else next((r for r in house["rooms"].values() if r.get("type") == where), None)
        if room and room.get("type") and name not in room["objects"]:
            room["objects"][name] = fixture({"name": name, "pos": free_tile(house, cfg, room, at) if cfg else at, "says": says, "landmark": True})
    return [s for s in S.values() if s["kind"] == "plot"]


def lean(house, cfg, pet, out):
    """wants.lean: a hob that must come in heads for the garden, and nowhere else."""
    if come_in(house, cfg, pet):
        out["rooms"] = {YARD if pet["room"] == MEADOW else gate_room(house)}
        out["doors"] = set()


def bring_in(house, cfg, pet, why):
    """Carried in (or walked in by the hand) to just inside the gate."""
    g = garden(house)
    pet["room"], pet["pos"], pet["plan"] = g["id"], free_tile(house, cfg, g, house["door_tiles"][GATE]), None
    pet["rooms"][g["id"]] = house["tick"]
    add_event(house, pet, "you came in through the garden gate: %s" % why)
    moment(house, "came in", "%s came in from outside: %s" % (label(pet), why), pet["id"], g["id"])


def tick(house, cfg):
    """Every tick: the gate; whoever must come in and has not after a while; who has been out (the spotlight); every
    so often, creatures, and bits dropped outdoors weathering away."""
    from . import spotlight
    if YARD not in house["rooms"] or not house["rooms"][YARD].get("type"):
        if house["tick"] % ticks(cfg, 60) == 0:   # (a new house: once its garden is found)
            migrate(house, cfg)
        return
    gate(house, cfg)
    st = house["outdoors"]
    if not O(cfg).get("on"):   # switched off: the gate stays shut, the outdoors' season is over, and nothing lives out there
        for s in [s for k in ("on", "queue") for s in (house.get("spotlights") or {}).get(k, []) if s["key"] == "outdoors"]:
            for k in ("on", "queue"):
                if s in house["spotlights"][k]:
                    house["spotlights"][k].remove(s)
            s["ended"] = house["tick"]
            house["spotlights"]["done"].append(s)
        for cr in [cr for cr in house["creatures"] if cr["room"] in OUT]:
            house["creatures"].remove(cr)
    pit = house["rooms"][YARD]["objects"].get("fire pit")
    if pit:   # (the fire burns while anyone is out in the yard)
        pit["state"] = "on" if any(p["room"] == YARD and p["stage"] not in ("egg", "dead") for p in house["pets"].values()) else "off"
    late = hours(cfg, O(cfg).get("in_hours", 0.5))
    for p in house["pets"].values():
        if p["stage"] in ("egg", "dead"):
            continue
        if p["room"] in OUT:
            if p["id"] not in _tried(house):
                spotlight.tried(house, cfg, "outdoors", p)
            if come_in(house, cfg, p):
                since = p.setdefault("must_in", house["tick"])
                if house["tick"] - since >= late or p["sleep"] or house["clock"]["phase"] == "night":
                    bring_in(house, cfg, p, "it was getting dark" if st.get("why") in ("dusk", "night") else "a storm was coming" if st.get("why") == "storm"
                             else "it was too cold to stay out" if st.get("why") == "cold" else "the weather had turned" if st.get("why") else "there was no grown one out with you")
                    p.pop("must_in", None)
            else:
                p.pop("must_in", None)
        else:
            p.pop("must_in", None)
    if house["tick"] % ticks(cfg, 60) == 0:
        if O(cfg).get("on"):
            creatures(house, cfg)
        weather_away(house, cfg)


def _tried(house):
    return {pid for s in (house.get("spotlights") or {}).get("on", []) if s["key"] == "outdoors" for pid in s["tried"]}


def weather_away(house, cfg):
    """A bit dropped outdoors (not one that grows there) is gone after a world day."""
    for rid in OUT:
        room = house["rooms"][rid]
        room["spots"] = [s for s in room["spots"] if not (s["loose"] and not s.get("on") and house["tick"] - s.get("since", house["tick"]) > cfg["ticks_per_day"])]


def creatures(house, cfg):
    """Once a world minute: by day now and then a rabbit, a squirrel, a hedgehog, a butterfly or a bird turns up in the
    yard or the meadow (one of each at most), an owl at dusk; they wander; by night only the owl stays, until dawn."""
    from . import director
    c, r = house["clock"], rnd(house, "outdoor creatures", house["tick"])
    here = [cr for cr in house["creatures"] if cr["room"] in OUT]
    for cr in here:
        if cr["kind"] in DAY_KINDS and c["phase"] != "day":
            director.leave(house, cr, "went off into the long grass")
            continue
        if cr["kind"] == "owl" and c["phase"] == "day":
            director.leave(house, cr, "flew off into the trees")
            continue
        cr["doing"] = DOING.get(cr["kind"], cr["doing"])
        if r.random() < 0.5:
            cr["goal"] = [r.randrange(cfg["W"]), r.randrange(cfg["H"] - 1)]
    have = {cr["kind"] for cr in here}
    kinds = [k for k in (DAY_KINDS + ("bird",) if c["phase"] == "day" else ("owl",) if c["phase"] == "dusk" else ()) if k not in have]
    if not kinds or len(here) >= O(cfg).get("creatures", 4) or r.random() > O(cfg).get("creature_chance", 0.15):
        return
    kind = r.choice(kinds)
    room = house["rooms"][r.choice(OUT)]
    cr = director.born(house, cfg, kind, room, free_tile(house, cfg, room, [r.randrange(cfg["W"]), r.randrange(cfg["H"] - 1)]), cfg["house"]["creatures"][kind]["stay_hours"])
    cr["doing"] = DOING[kind]
    director.seen(house, cfg, cr, "a %s has come into %s" % (kind, room["name"]))
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": kind, "room": room["id"], "pet": None, "what": "arrived"})


# ---- fishing in the stream (by paw only; the pond stays the place for rods and finds) ----

def stream_targets(house, cfg, pet, room):
    """pond.targets for the meadow: a tile on the bank by the stream; by paw only, a small fish now and then."""
    from . import pond
    water = pond.water(room)
    if not water or pet["stage"] in ("egg", "hatchling") or house["clock"]["phase"] == "night":
        return []
    taken_ = {tuple(p["pos"]) for p in house["pets"].values() if p["room"] == room["id"] and p is not pet and p["stage"] != "dead"}
    bank = [[x, y - 1] for x, y in water if [x, y - 1] not in water and (x, y - 1) not in taken_]
    if not bank:
        return []
    at = min(bank, key=lambda t: dist(t, pet["pos"]))
    lo, hi = pond.P(cfg)["time"]["paw"]
    got = rnd(house, "stream", pet["id"], house["tick"]).random() < O(cfg).get("stream_fish", 0.3)
    return [{"what": "pond", "goal": None if pet["pos"] == at else at, "where": "by the stream", "bonus": 0.2,
             "fish": {"spot": at, "line": [at[0], at[1] + 1], "rod": False, "stream": True, "catch": {"what": "small fish", "bit": "fish", "fish": True, "tier": "common"} if got else None},
             "seconds": (lo, hi)}]


def stream_finish(house, cfg, pet, room, F):
    """pond.finish for the stream: a small fish into its paws, or nothing. (The pond's own stock and catches are not
    the stream's.)"""
    from . import craft
    c = F.get("catch")
    craft.practise(house, cfg, pet, "fishing", 1.0 if c else 0.4)
    if not c:
        return "you sat a while by the stream with a paw in the water; the little fish darted away", {}, None
    craft.give(house, cfg, pet, room, c["bit"])
    moment(house, "catch", "%s caught a small fish in the stream" % label(pet), pet["id"], room["id"])
    return "you caught a small fish in the stream with your paw", {}, "fish"
