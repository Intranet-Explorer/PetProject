"""What the house does to a pet from moment to moment, and what the pet can feel of it.

One list serves both: every standing effect carries the words for how it feels, so nothing can act on a pet
that the pet has no way to notice (FINDINGS: pressure it cannot perceive produces a stuck pet)."""
from . import things
from .feel import level as feel_level
from .world import dist, here, neighbours, power_on, sunny

NO_HARSH_LIGHT = ("cellar", "storeroom")   # lights cost no comfort underground or in the dark store (§6.1)


def effect(tag, need, rate, feel, hidden=True):
    return {"tag": tag, "need": need, "rate": rate, "feel": feel, "hidden": hidden}


def effects(house, cfg, pet):
    """Everything acting on a pet right now, as rates per 10 s. `hidden` marks the physics it is never told."""
    room, c, M, R = house["rooms"][pet["room"]], house["clock"], cfg["materials"], cfg["house"]
    kind, objs, out = room["type"], room["objects"], []
    elder, T = pet["stage"] == "elder", pet["temper"]

    # the plain wearing-down of being alive
    E, D = cfg["effects"], cfg["effects"]["drift"]
    out.append(effect("drift", "energy", D["energy"] * (1.5 if elder else 1) * (1.3 if pet["weak"] else 1), None, False))
    out.append(effect("drift", "comfort", D["comfort"], None, False))
    out.append(effect("drift", "curiosity", D["curiosity"], None, False))
    snug = next((n for n, o in objs.items() if o.get("fix", {}).get("cozy") and dist(pet["pos"], o["pos"]) <= 1), None)
    if snug:
        out.append(effect("cozy", "comfort", E["cozy"], "it is snug here by the %s" % snug, False))

    # company (§7.4): rises near others, falls slowly alone; a sociable pet loses it faster
    others, C = here(house, pet), cfg["effects"]["company"]
    about = [cr for cr in house["creatures"] if cr["room"] == pet["room"]]
    visited = house.get("visitor_room") == pet["room"] and (house["tick"] - house["visitor_last"]) * cfg["clock"]["tick_seconds"] <= 30
    if others:
        close = any(dist(pet["pos"], o["pos"]) <= 3 for o in others)
        out.append(effect("company", "company", C["near"] if close else C["room"], None, False))
    elif about:
        fed = any(pet["trust"].get(cr["kind"], 0) >= 1 for cr in about)
        out.append(effect("company", "company", C["friend"] if fed else C["creature"], None, False))
    elif visited:
        out.append(effect("company", "company", C["visitor"], None, False))
    else:
        out.append(effect("company", "company", C["alone"] * (0.5 + T["sociable"]), None, False))

    # the v2 rules, now physics for anything that gives light (§5 of v2)
    night = c["phase"] == "night"
    if night and kind not in NO_HARSH_LIGHT and things.light_on(house, cfg, room):
        shade = things.near(house, cfg, pet, "shade")
        if shade:   # a dark thing's work is the harm it keeps off
            out.append(dict(effect("dark", "comfort", 0.0, "the %s beside you keeps the light off you" % shade[0]),
                            thing=shade[0], credit=-M["rules"]["lights_night"]))
        else:
            out.append(effect("lights_night", "comfort", M["rules"]["lights_night"], "the light in the room is harsh on you"))
    for o in objs.values():
        if o.get("fix", {}).get("window") and o.get("state") == "open" and night:
            out.append(effect("window", "comfort", E["open_window"], "cold air is coming in at the open window", False))
            break
    if kind == "nursery" and c["phase"] == "day" and "plant" in objs and "window" in objs \
            and dist(objs["plant"]["pos"], objs["window"]["pos"]) <= 2:
        out.append(effect("plant_window", "comfort", M["rules"]["plant_window"], "the air in the room feels fresh"))

    strongest = {}   # several things of a kind do not add up: five warm things are no warmer to stand by than the warmest
    for tag, need, rate, name, feel in things.standing(house, cfg, pet):
        if abs(rate) > abs(strongest.get((tag, need), (0,))[0]):
            strongest[(tag, need)] = (rate, name, feel)
    for (tag, need), (rate, name, feel) in strongest.items():
        out.append(dict(effect(tag, need, rate, feel), thing=name))

    # each room's own rule (§6.1)
    rule = lambda key, default=0.0: things.room_rule(cfg, room, key, default)
    if kind == "cellar" and night:
        out.append(effect("cellar", "comfort", rule("cold_night"), "the cellar's cold gets into you"))
    if kind == "attic" and sunny(house) and "sun shaft" in objs and dist(pet["pos"], objs["sun shaft"]["pos"]) <= 1:
        out.append(effect("attic", "comfort", rule("sun"), "the sun shaft is warm on you"))
    if kind == "greenhouse" and c["phase"] == "day":
        out.append(effect("greenhouse", "comfort", rule("warm_day"), "the warm air under the glass settles on you"))
    if kind == "garden" and house["weather"] == "rain":
        out.append(effect("garden", "comfort", rule("fresh"), "the smell of rain on the soil eases you"))
    if kind == "pond":
        out.append(effect("pond", "energy", 0.0, "the water makes a slow sound that slows you down with it"))
    if kind == "storeroom" and not things.light_on(house, cfg, room):
        out.append(effect("storeroom", "curiosity", 0.0, "it is too dark in here to see things well"))
    for d, rid in neighbours(house, pet["room"]).items():   # the music room's sounds reach next door
        other = house["rooms"][rid]
        if other["type"] == "music" and other.get("sounding_until", 0) > house["tick"]:
            out.append(effect("music", "curiosity", things.room_rule(cfg, other, "linger", 0.3), "sounds drift in from the music room"))

    # weather and season (§6.4)
    W = R["weather"]
    sheltered = kind in ("cellar", "storeroom")
    warm_by = bool(things.near(house, cfg, pet, "near")) or any(t["tag"] in ("cozy", "attic", "greenhouse") for t in out)
    cold = (R["seasons"][c["season"]]["cold"] if night else 0.0) + (W["snow_cold"] if house["weather"] == "snow" else 0.0)
    if cold and not (kind == "greenhouse" and c["phase"] == "day"):
        out.append(effect("cold", "comfort", cold * (0.4 if warm_by else 1.0), "the cold gets into you"))
    if house["weather"] == "storm" and not sheltered and not any(dist(pet["pos"], o["pos"]) <= 3 for o in others):
        out.append(effect("storm", "comfort", W["storm"], "the storm outside unsettles you"))
    if house["weather"] == "heat" and c["phase"] == "day" and kind not in ("cellar", "pond"):
        out.append(effect("heat", "energy", W["heat"], "the heat makes you heavy"))
    if room["wet_until"] > house["tick"]:
        out.append(effect("leak", "comfort", R["events"]["leak"], "the floor here is wet"))
    if room["cold_until"] > house["tick"]:
        out.append(effect("draught", "comfort", R["events"]["draught"], "a cold draught runs through the room"))
    if not power_on(house) and night:
        out.append(effect("power", "comfort", 0.0, "every light in the house has gone dark"))
    return out


def senses(house, cfg, pet, acting=None):
    """What it notices right now: the feel of each thing acting on it, and of its own body (§3, §4.1)."""
    from . import life
    felt = [e["feel"] for e in (acting if acting is not None else effects(house, cfg, pet)) if e["feel"]]
    felt += life.body_feels(house, cfg, pet)
    room = house["rooms"][pet["room"]]
    if len(things.made(room)) >= cfg["make"]["crowded"]:
        felt.append("this room is crowded with made things")
    if pet["spring"]:
        felt.append("there is a spring in your step")
    if feel_level(pet, "comfort") >= 2 and not any("snug" in f for f in felt):   # unease points at what would ease it
        cozy = [n for n, o in room["objects"].items() if o.get("fix", {}).get("cozy")]
        if cozy:
            felt.append("the %s looks like somewhere you could settle" % cozy[0])
    return list(dict.fromkeys(felt))
