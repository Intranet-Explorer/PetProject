"""What the house does to a pet from moment to moment, and what the pet can feel of it.

One list serves both: every standing effect carries the words for how it feels, so nothing can act on a pet
that the pet has no way to notice (FINDINGS: pressure it cannot perceive produces a stuck pet)."""
from . import genes, things
from . import build
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
    out.append(effect("drift", "comfort", D["comfort"] * pet["needs"]["comfort"] / 50, None, False))   # SPEC-v3.5.4 §2: like interest, ease wears off the more of it there is
    # Interest wears off faster the keener it is. A flat rate has no middle: a pet that earns a little less than
    # it loses sits at the bottom for life, and one that earns a little more sits at the top (both showcase runs).
    out.append(effect("drift", "curiosity", D["curiosity"] * pet["needs"]["curiosity"] / 50, None, False))
    bored = feel_level(pet, "curiosity") - 2   # boredom is the one lack a snug room cannot answer, so it has to cost something
    if bored > 0 and pet["needs"]["comfort"] > E["restless_to"]:   # it makes a pet uncomfortable, never miserable: misery dulls interest, and that would be a trap
        out.append(effect("restless", "comfort", E["restless"] * bored, "you have sat with the same things too long to be easy", False))
    snug = next((n for n, o in objs.items() if o.get("fix", {}).get("cozy") and dist(pet["pos"], o["pos"]) <= 1), None)
    if snug:
        out.append(effect("cozy", "comfort", E["cozy"], "it is snug here by the %s" % snug, False))

    # company (§7.4) settles toward what the company at hand gives: another pet in the room lifts it as far as
    # `presence_to`, a creature it has fed as far as `friend_to`, any creature `creature_to`, and alone it sinks to
    # `alone_to`. Above that it slips, sooner for a sociable pet and faster the more there is of it. Closeness past
    # what presence gives slips at `together` wherever the pet is (the rest has to pass between them: a word, a gift,
    # a lean), so going off alone never keeps it better than staying; below that, being alone wears at `alone`.
    # (Third run: alone kept closeness twelve times better than staying, and a fed beetle kept the founder at 97.)
    others, C, have = here(house, pet), cfg["effects"]["company"], pet["needs"]["company"]
    about = [cr for cr in house["creatures"] if cr["room"] == pet["room"]]
    visited = house.get("visitor_room") == pet["room"] and (house["tick"] - house["visitor_last"]) * cfg["clock"]["tick_seconds"] <= 30
    fed, P = any(pet["trust"].get(cr["kind"], 0) >= 1 for cr in about), C["presence_to"]
    to, lift = ((P, C["near"] if any(dist(pet["pos"], o["pos"]) <= 3 for o in others) else C["room"]) if others
                else (P, C["visitor"]) if visited
                else (C["friend_to"], C["friend"]) if fed else (C["creature_to"], C["creature"]) if about else (C["alone_to"], 0.0))
    if have < to:
        out.append(effect("company", "company", lift, None, False))
    else:   # each rate is the one halfway up its stretch: `together` between presence and full, `alone` between alone and presence
        slip = C["together"] * max(0.0, have - P) / ((100 - P) / 2) + C["alone"] * (min(have, P) - to) / ((P - C["alone_to"]) / 2)
        out.append(effect("company", "company", slip * (0.5 + T["sociable"]), None, False))

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
    # A rule can drift and change sign (§6.5), so what it feels like follows the number, not the room's name.
    rule = lambda key, default=0.0: things.room_rule(cfg, room, key, default)
    if kind == "cellar" and night:
        out.append(effect("cellar", "comfort", rule("cold_night"), "the cellar's cold gets into you" if rule("cold_night") < 0 else "the cellar's still air is easy on you tonight"))
    if kind == "attic" and sunny(house) and "sun shaft" in objs and dist(pet["pos"], objs["sun shaft"]["pos"]) <= 1:
        out.append(effect("attic", "comfort", rule("sun"), "the sun shaft is warm on you" if rule("sun") >= 0 else "the sun shaft is harsh on you"))
    if kind == "greenhouse" and c["phase"] == "day":
        out.append(effect("greenhouse", "comfort", rule("warm_day"), "the warm air under the glass settles on you" if rule("warm_day") >= 0 else "the air under the glass is close and stuffy"))
    if kind == "garden" and house["weather"] == "rain":
        out.append(effect("garden", "comfort", rule("fresh"), "the smell of rain on the soil eases you" if rule("fresh") >= 0 else "the wet soil smells sour and wears on you"))
    if kind == "pond":
        out.append(effect("pond", "energy", 0.0, "the water makes a slow sound that slows you down with it" if rule("rest", 1.0) >= 1 else "the water's sound keeps you from settling"))
    if kind == "storeroom" and not things.light_on(house, cfg, room):
        out.append(effect("storeroom", "curiosity", 0.0, "it is too dark in here to see things well" if rule("dark", 0.5) < 1 else "your eyes have got used to the dark in here"))
    for d, rid in neighbours(house, pet["room"]).items():   # the music room's sounds reach next door
        other = house["rooms"][rid]
        if other["type"] == "music" and other.get("sounding_until", 0) > house["tick"]:
            linger = things.room_rule(cfg, other, "linger", 0.3)
            out.append(effect("music", "curiosity", linger, "sounds drift in from the music room" if linger >= 0 else "sounds from the music room grate on you"))

    # weather and season (§6.4)
    W = R["weather"]
    sheltered = kind in ("cellar", "storeroom")
    warm_by = bool(things.near(house, cfg, pet, "near")) or any(t["tag"] in ("cozy", "attic", "greenhouse") for t in out)
    cold = (R["seasons"][c["season"]]["cold"] if night else 0.0) + (W["snow_cold"] if house["weather"] == "snow" else 0.0)
    from . import season; cold = season.cold(house, cfg, pet, room, cold, out)   # SPEC-v3.5 §5: the season's own cold, and what a warm thing is by day
    cold = build.felt(house, cfg, pet, room, out, cold)   # SPEC-v3.5 §4: a room lined against the cold lets less of it in (and a painted room is felt)
    cold = genes.fur(pet, cold, out)   # SPEC-v3.5 §2.3: thick fur keeps the worst of it off (and of the cellar's): after the season's own, so of that too
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
    # SPEC-v3.3 §2.1, §3.1: a mess wears on an orderly pet and a tidy room eases it; the visitor's music is felt
    from . import order
    tidy, mess = (T.get("orderly", 0.5) - 0.5) * 2, order.clutter(house, cfg, room)
    if tidy > 0 and mess != 1 and things.made(room):
        out.append(effect("clutter", "comfort", cfg["order"]["mess" if mess == 2 else "tidy"] * tidy, None, False))
    dj = (house.get("dj") or {}).get("music")
    if dj and dj.get("mood") and dj["scope"] in ("house", room["id"]):
        for need, rate in cfg["music"].get(dj["mood"], {}).items():
            out.append(effect("music", need, rate, "the visitor is playing %s music" % dj["mood"], False))
        if not cfg["music"].get(dj["mood"]):
            out.append(effect("music", "comfort", 0.0, "the visitor is playing %s music" % dj["mood"], False))
    from . import radio
    st = radio.playing(house, cfg, room["id"])   # SPEC-v3.5.1 §5: their radio's station, felt as the visitor's music is
    if st:
        for need, rate in cfg["music"].get(st["mood"], {}).items():
            out.append(effect("radio", need, rate, "the radio is playing something %s" % st["sound"], False))
    return out


def senses(house, cfg, pet, acting=None):
    """What it notices right now: the feel of each thing acting on it, and of its own body (§3, §4.1)."""
    from . import life
    felt = [e["feel"] for e in (acting if acting is not None else effects(house, cfg, pet)) if e["feel"]]
    felt += life.body_feels(house, cfg, pet)
    room = house["rooms"][pet["room"]]
    from . import order
    if order.crowded(house, cfg, room):   # SPEC-v3.5.4 §1: untidy, not a reason to stop making
        felt.append("this room is cluttered with old things; some could go to the machine, or into a box")
    from . import order
    mess = order.clutter(house, cfg, room)   # SPEC-v3.3 §2.1: clutter is felt, by those who mind it
    if mess == 2 or (mess == 0 and pet["temper"].get("orderly", 0.5) > 0.6 and things.made(room)):
        felt.append(order.MESS[mess])
    if mess == 2 and order.full(cfg, room):   # so a mind can choose to make somewhere (12 October 2026)
        felt.append(order.NOWHERE)
    if pet["spring"]:
        felt.append("there is a spring in your step")
    felt += drawn(house, cfg, pet, room, felt)
    return list(dict.fromkeys(felt))


def drawn(house, cfg, pet, room, felt):
    """What a lack draws its eye to (§3: "drawn to something"). One thing per need that is running short, the
    nearest that would answer it. It is a pull, not an instruction: the pet still has to find out what it does."""
    objs, out = room["objects"], []
    near = lambda names: min(names, key=lambda n: dist(pet["pos"], objs[n]["pos"]), default=None)
    fix = lambda key: [n for n, o in objs.items() if key in o.get("fix", {})]
    made = lambda key: [n for n, o in things.made(room).items() if key in things.prop(cfg, o)]
    if feel_level(pet, "comfort") >= 2 and not any("snug" in f for f in felt):
        soft = near([n for n in made("use") if things.prop(cfg, objs[n]).get("need") == "comfort"] + fix("soft"))
        cozy = near(fix("cozy"))
        if soft:
            out.append("the %s looks soft enough to sink into" % soft)
        elif cozy:
            out.append("the %s looks like somewhere you could settle" % cozy)
    if feel_level(pet, "energy") >= 2:
        food = near([n for n in fix("meal") if objs[n]["servings"]] + [n for n in fix("plant") if objs[n]["state"] == "ripe"] + made("food"))
        bed = near(fix("rest"))
        if food:
            out.append("you can smell something to eat: the %s" % food)
        if bed:
            out.append("the %s looks like a good place to rest" % bed)
    if feel_level(pet, "curiosity") >= 2:   # bored: the door it has never been through, if this room has one
        new = [d for d, rid in room["doors"].items() if rid not in pet["rooms"] and house["shut"].get("%s|%s" % (room["id"], d), 0) <= house["tick"]]
        if new:
            out.append("the %s door is one you have never been through" % new[0])
        else:   # none here: the nearest room it knows that still has one, and which way that is
            seen, queue = {room["id"]}, [(rid, d) for d, rid in room["doors"].items() if rid in pet["rooms"]]
            while queue:
                rid, way = queue.pop(0)
                if rid in seen:
                    continue
                seen.add(rid)
                there = house["rooms"][rid]
                if any(x not in pet["rooms"] and house["shut"].get("%s|%s" % (rid, d), 0) <= house["tick"] for d, x in there["doors"].items()):
                    out.append("you keep thinking of %s, through the %s door: there is a door there you have never tried" % (there["name"], way))
                    break
                queue += [(x, way) for x in there["doors"].values() if x in pet["rooms"]]
    # the pull between a parent and its young, while they are young: the one thing that brings kin back together
    from .actions import handle
    small = ("egg", "hatchling", "child")
    for kid in (house["pets"].get(c) for c in pet["children"]):
        if kid and kid["stage"] in small and kid["room"] != pet["room"]:
            where = house["rooms"][kid["room"]]["name"] if kid["room"] in pet["rooms"] else "somewhere else"
            out.append("you think of %s, in %s without you" % ("your egg" if kid["stage"] == "egg" else handle(house, pet, kid), where))
            break
    parent = house["pets"].get(pet["parent"])
    if pet["stage"] in small and parent and parent["stage"] != "dead" and parent["room"] != pet["room"]:
        out.append("you want %s; they are not here" % handle(house, pet, parent))
    if feel_level(pet, "company") >= 2:
        others = here(house, pet)
        stones = [n for n, o in objs.items() if "memorial" in o]
        if others:
            out.append("you want to be near " + handle(house, pet, others[0]))
        elif stones:
            out.append("the %s draws you" % near(stones))
        elif any(c["room"] == room["id"] for c in house["creatures"]):
            out.append("the %s is company of a kind" % next(c["kind"] for c in house["creatures"] if c["room"] == room["id"]))
    return out
