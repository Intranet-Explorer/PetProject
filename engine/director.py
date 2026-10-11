"""What the house does on its own (SPEC-v3 §6.4, §6.5): the day's weather, the seasons, storms and power
cuts, the events nobody caused, and the small creatures. All of it scripted; no model is ever asked."""
from . import genome, songs, things, walls
from .world import (LONG_AGO, add_event, alive, arrived, bit_kinds, clock, dist, family, free_tile, hours, in_room, label, moment,
                    new_pet, power_on, rnd, ticks, weather_of)

SKY = {"clear": "the sky has cleared", "cloudy": "the sky has gone grey", "rain": "it has started to rain",
       "storm": "a storm has come up", "snow": "it has started to snow", "heat": "the air has turned hot and still"}


def awake_pets(house, room=None):
    return [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead") and not p["sleep"] and (room is None or p["room"] == room)]


def tell_all(house, text, news="event", room=None):
    for p in awake_pets(house, room):
        add_event(house, p, text)
        p["news"].append(news)


def note(house, kind, room, detail):
    """An event, for the log and the view."""
    house["events"].append({"tick": house["tick"], "day": house["clock"]["day"], "kind": kind, "room": room, "detail": detail})
    del house["events"][:-60]
    house.setdefault("fresh_events", []).append(house["events"][-1])


# ---- the clock: runs every tick, awake or asleep ----

def begin(house, cfg):
    was = house["clock"]
    house["clock"] = c = clock(cfg, house["tick"])
    if c["day"] != was["day"] or house["tick"] == 0:
        new_day(house, cfg, was)
    if c["phase"] != was["phase"] and c["phase"] == "day":   # dawn: meals are set out again
        for room in found(house):
            for o in room["objects"].values():
                if "meal" in o.get("fix", {}):
                    o["servings"], o["state"] = o["fix"]["meal"], "full"
    if house.get("power_was_out") and power_on(house):
        house["power_was_out"] = False
        tell_all(house, "the lights that went dark can be lit again")
        note(house, "power back", None, "")
        moment(house, "power back", "the power came back")
    if house["tick"] % hours(cfg, 1) == 0:
        hourly(house, cfg)
    if house["tick"] % ticks(cfg, 10) == 0:
        events(house, cfg)
        arrivals(house, cfg)
    creatures(house, cfg)


def found(house):
    return [r for r in house["rooms"].values() if r["type"]]


def new_day(house, cfg, was):
    c = house["clock"]
    sky = weather_of(house, cfg, c["day"])
    if sky != house["weather"]:
        house["weather"] = sky
        tell_all(house, SKY[sky], "phase")
    if c["season"] != was["season"]:
        tell_all(house, "the season has turned: it is %s" % c["season"], "phase")
        moment(house, "season", "%s has come" % c["season"])
    if sky == "storm":
        moment(house, "storm", "a storm came over the house")
        r = rnd(house, "storm", c["day"])
        if r.random() < cfg["house"]["weather"]["storm_power_cut"]:   # some time in the dark hours, so night and light come apart
            house["storm_cut"] = house["tick"] + hours(cfg, r.uniform(*cfg["house"]["weather"]["storm_cut_hours"]))


def power_cut(house, cfg, hrs, why):
    """Every lamp and every bright thing goes dark for a while (§6.4). Nobody in the house chose it."""
    house["power_out_until"], house["power_was_out"] = house["tick"] + hours(cfg, hrs), True
    tell_all(house, "every light in the house went dark at once")
    moment(house, "power", "the power went out" + (" in the storm" if why == "storm" else ""))
    note(house, "power cut", None, why)


def hourly(house, cfg):
    """Slow things: bits come back, plants grow, things left lying change, a draught lets go."""
    c, H = house["clock"], cfg["house"]
    season = H["seasons"][c["season"]]
    for room in found(house):
        for s in room["spots"]:
            if not s["ready"] and s["back"] is not None and s["back"] <= house["tick"]:
                s["ready"], s["back"] = True, None
                if s["pos"] in [o["pos"] for o in room["objects"].values()]:
                    s["pos"] = free_tile(house, cfg, room, s["pos"])
        rule = lambda k, d: things.room_rule(cfg, room, k, d)
        for o in room["objects"].values():
            if o.get("fix", {}).get("plant") and o["state"] != "ripe":
                rate = season["growth"] * (rule("growth", 1.0) if room["type"] == "greenhouse" else 1.0)
                if room["type"] == "garden" and house["weather"] == "rain":
                    rate *= rule("rain_growth", 2.0)
                if room["type"] == "greenhouse":
                    rate = max(rate, 0.8)   # warm under glass even in winter
                o["grow"] = round(o["grow"] + rate / (24 * H["rules"]["garden"]["ripe_days"]), 3)
                if o["grow"] >= 1:
                    o["state"] = "ripe"
            if o.get("fix", {}).get("sun"):   # the attic's shaft of sun crosses the floor with the hour
                span = season["sunset"] - season["sunrise"]
                o["pos"] = [max(1, min(cfg["W"] - 2, round(1 + (cfg["W"] - 3) * (c["hour"] - season["sunrise"]) / span))), o["pos"][1]]
    things.upkeep(house, cfg)
    walls.fade(house, cfg)
    house["shut"] = {k: t for k, t in house["shut"].items() if t > house["tick"]}
    if house.get("storm_cut") and house["storm_cut"] <= house["tick"]:
        house["storm_cut"] = None
        if house["weather"] == "storm":
            power_cut(house, cfg, rnd(house, "cut", house["tick"]).uniform(*H["events"]["power_cut_hours"]), "storm")


# ---- events (§6.5): more often when the house has gone quiet, less in a crisis ----

def events(house, cfg):
    E, tick = cfg["house"]["events"], house["tick"]
    if house.get("leak_due") and house["leak_due"]["at"] <= tick:
        leak(house, cfg, house["rooms"][house.pop("leak_due")["room"]])
    if house["next_event"] is None:
        house["next_event"] = tick + hours(cfg, E["every_hours"] * 0.5)
    L = house["lineage"]
    if L and not L["drift"] and tick >= L["drift_at"] and len(found(house)) > 1:
        drift(house, cfg)
    if tick < house["next_event"] or not awake_pets(house):
        return
    r = rnd(house, "event", tick)
    crisis = any(p["needs"]["comfort"] < E["crisis_below"] or p["needs"]["energy"] < E["crisis_below"] or p["weak"] for p in awake_pets(house))
    quiet = tick - house["last_moment"] >= hours(cfg, E["quiet_hours"])
    house["next_event"] = tick + hours(cfg, E["every_hours"] * (0.5 if quiet else 2.0 if crisis else 1.0) * r.uniform(0.6, 1.4))
    if crisis:
        return
    kinds = dict(E["kinds"])
    if cfg["visitor"]["surprises"]:
        kinds["surprise"] = 2
    kind = r.choices(list(kinds), weights=list(kinds.values()))[0]
    rooms = found(house)
    lived_in = [x for x in rooms if any(p["room"] == x["id"] for p in awake_pets(house))] or rooms
    room = r.choice(lived_in)
    if kind == "power_cut":
        if power_on(house):
            power_cut(house, cfg, r.uniform(*E["power_cut_hours"]), "on its own")
    elif kind == "leak":
        mouse = next((cr for cr in house["creatures"] if cr["kind"] == "mouse" and cr.get("tame") and cr["room"] == room["id"]), None)
        if mouse:   # a tame mouse senses it first (SPEC-v3.1 §4.2): the water comes a minute after it squeaks
            seen(house, cfg, mouse, "%s squeaks and runs up and down by the wall; something is coming" % called(mouse, True))
            house["leak_due"] = {"room": room["id"], "at": tick + ticks(cfg, 60)}
        else:
            leak(house, cfg, room)
    elif kind == "draught":
        room["cold_until"] = tick + hours(cfg, r.uniform(*E["draught_hours"]))
        d = r.choice(list(room["doors"]))
        house["shut"]["%s|%s" % (room["id"], d)] = room["cold_until"]
        house["shut"]["%s|%s" % (room["doors"][d], {"north": "south", "south": "north", "west": "east", "east": "west"}[d])] = room["cold_until"]
        tell_all(house, "a draught blew the %s door shut; the room has gone cold" % d, room=room["id"])
        moment(house, "draught", "a draught shut the %s door of %s" % (d, room["name"]), None, room["id"])
        note(house, "draught", room["id"], d)
    elif kind == "delivery":
        store = next((x for x in rooms if x["type"] == "storeroom"), room)
        bits = [r.choice(bit_kinds(house, cfg)) for _ in range(E["delivery_bits"])]
        things.drop_bits(house, cfg, store, [cfg["W"] // 2, cfg["H"] // 2], bits)
        for p in awake_pets(house):
            add_event(house, p, "a crate of bits has appeared here" if p["room"] == store["id"] else "something heavy was set down somewhere in the house")
            p["news"].append("event")
        moment(house, "delivery", "a crate of bits turned up in %s: %s" % (store["name"], ", ".join(bits)), None, store["id"])
        note(house, "delivery", store["id"], ", ".join(bits))
    elif kind == "lost_thing":
        owned = [(x, n) for x in rooms for n, o in things.made(x).items()
                 if o["made"]["owner"] in house["pets"] and house["pets"][o["made"]["owner"]]["stage"] != "dead"
                 and not things.prop(cfg, o).get("fixed") and not o.get("wall")]
        others = lambda x: [y for y in rooms if y["id"] != x["id"]]
        owned = [(x, n) for x, n in owned if others(x)]
        if owned:
            frm, n = r.choice(owned)
            to = r.choice(others(frm))
            o = frm["objects"].pop(n)
            o["pos"] = free_tile(house, cfg, to, [r.randrange(cfg["W"]), r.randrange(cfg["H"])])
            to["objects"][n] = o
            for m in [m for m in frm.get("marks", []) if m["on"] == n]:   # what is written on a thing goes where the thing goes
                frm["marks"].remove(m)
                to.setdefault("marks", []).append(m)
            owner = house["pets"][o["made"]["owner"]]
            owner["lost"].append({"name": n, "by": None, "room": frm["id"]})
            if owner["room"] == frm["id"] and not owner["sleep"]:
                add_event(house, owner, "your %s is not where it was" % n)
                owner["news"].append("event")
                owner["lost"].pop()
            moment(house, "lost", "%s's %s, '%s', went missing from %s and is in %s" % (label(owner), o["made"]["recipe"].get("kind", "thing"), n, frm["name"], to["name"]), owner["id"], to["id"])
            note(house, "lost thing", to["id"], n)
    elif kind == "surprise":
        bit = r.choice(bit_kinds(house, cfg))
        things.drop_bits(house, cfg, room, [cfg["W"] // 2, cfg["H"] // 2], [bit])
        tell_all(house, "the visitor left some %s on the floor" % bit, "visitor", room["id"])
        note(house, "surprise", room["id"], bit + " (the director's, in the visitor's name)")


def leak(house, cfg, room):
    r, E = rnd(house, "leak", house["tick"]), cfg["house"]["events"]
    room["wet_until"] = house["tick"] + hours(cfg, r.uniform(*E["leak_hours"]))
    for n, o in things.made(room).items():   # the water shifts what is lying about
        if not things.prop(cfg, o).get("fixed") and r.random() < 0.5:
            o["pos"] = free_tile(house, cfg, room, [r.randrange(cfg["W"]), r.randrange(cfg["H"])], n)
    tell_all(house, "water is coming in; the floor is wet and some things have shifted", room=room["id"])
    moment(house, "leak", "water came into %s" % room["name"], None, room["id"])
    note(house, "leak", room["id"], "")


def drift(house, cfg):
    known = cfg["house"]["events"]["drift_known_days"] * cfg["ticks_per_day"]   # long enough for someone to have learned the old rule
    rooms = [x for x in found(house) if x["type"] in cfg["house"]["drifts"] and not x.get("drift") and house["tick"] - x["found"] >= known]
    if not rooms:
        return
    room = rnd(house, "drift", house["lineage"]["id"]).choice(rooms)
    room["drift"] = dict(cfg["house"]["drifts"][room["type"]])
    house["lineage"]["drift"] = {"room": room["id"], "type": room["type"], "rule": room["drift"], "tick": house["tick"]}
    note(house, "rule drift", room["id"], "%s: %s" % (room["type"], room["drift"]))   # logged; the pets are not told
    moment(house, "drift", "something about %s is not as it was" % room["name"], None, room["id"])


# ---- small creatures (§6.5) ----

DOING = {"moth": "circling the light", "beetle": "trundling along", "mouse": "watching from a corner", "bird": "hopping about"}


def creatures(house, cfg):
    C, tick, c = cfg["house"]["creatures"], house["tick"], house["clock"]
    if tick % ticks(cfg, 60) == 0:
        arrive(house, cfg)
    taming = arrived(house, "taming")
    for cr in list(house["creatures"]):
        room = house["rooms"][cr["room"]]
        pets = awake_pets(house, cr["room"])
        kind, r = cr["kind"], rnd(house, "cr", cr["id"], tick)
        if taming:
            trust(house, cfg, cr, pets)
            if aged(house, cfg, cr):
                continue
        owner = house["pets"].get(cr.get("tame"))
        if tick >= cr["until"] and not owner:
            leave(house, cr, "went away")
            continue
        if tick % 2:
            continue
        goal = None
        if owner:   # one pet's animal (SPEC-v3.1 §4): it keeps close, goes where its pet goes, and does its kind's small service
            goal = kept(house, cfg, cr, owner, r)
        elif kind == "moth":
            lights = [o for o in room["objects"].values() if lit(cfg, o)] if power_on(house) else []
            if not lights or c["phase"] == "day":
                leave(house, cr, "flew off when the light went")
                continue
            light = min(lights, key=lambda o: dist(o["pos"], cr["pos"]))
            a = (tick // 2) % 8   # round and round the light
            ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)][a]
            goal, cr["doing"] = [light["pos"][0] + ring[0], light["pos"][1] + ring[1]], "circling the light"
            for n, o in things.made(room).items():   # it eats at soft things left by its light (§6.5)
                if o["made"]["recipe"]["material"] == "soft" and dist(o["pos"], light["pos"]) <= 2 and not tame_moth_of(house, room):
                    o["made"]["mothed"] = o["made"].get("mothed", 0) + 2
                    if o["made"]["mothed"] >= hours(cfg, C["moth"]["eats_hours"]) and not o["made"].get("eaten"):
                        o["made"]["eaten"] = True
                        seen(house, cfg, cr, "the moth has been eating at the %s" % n)
        elif kind == "beetle":
            if cr.get("carry") is None:
                spots = [s for s in room["spots"] if s["ready"] and s["loose"]] or [s for s in room["spots"] if s["ready"]]
                near = [s for s in spots if dist(s["pos"], cr["pos"]) <= 1]
                if near and r.random() < C["beetle"]["carry_chance"]:
                    s = near[0]
                    cr["carry"] = s["bit"]
                    if s["loose"]:
                        room["spots"].remove(s)
                    else:
                        s["ready"], s["back"] = False, tick + hours(cfg, cfg["house"]["rooms"][room["type"]]["regrow_hours"])
                    cr["doing"] = "carrying some %s" % s["bit"]
                    seen(house, cfg, cr, "the beetle picked up some %s" % s["bit"])
            if tick % ticks(cfg, 120) == 0 and room["doors"] and r.random() < 0.6:   # it wanders from room to room
                d = r.choice([d for d, rid in room["doors"].items() if house["rooms"][rid]["type"]] or [None])
                if d:
                    seen(house, cfg, cr, "the beetle went out under the %s door" % d)
                    cr["room"], cr["pos"] = room["doors"][d], list(house["door_tiles"][{"north": "south", "south": "north", "west": "east", "east": "west"}[d]])
                    if cr.get("carry") and r.random() < 0.7:
                        things.drop_bits(house, cfg, house["rooms"][cr["room"]], cr["pos"], [cr["carry"]])
                        cr["carry"], cr["doing"] = None, "trundling along"
                    continue
            if c["phase"] == "night":
                cr["doing"], goal = "asleep under the edge of things", cr["nest"]
            else:
                goal = cr.get("goal")
                if not goal or goal == cr["pos"]:
                    goal = cr["goal"] = [r.randrange(cfg["W"]), r.randrange(cfg["H"])]
        elif kind == "mouse":
            sweet = [(n, o) for n, o in things.made(room).items() if things.prop(cfg, o).get("food") and not o["made"].get("heirloom")]
            moving = [p for p in pets if p["plan"] and p["plan"]["left"] is None]   # a pet on the move
            friend = max(pets, key=lambda p: cr["fed"].get(p["id"], 0), default=None)
            shy = C["mouse"]["shy"]
            scared = [p for p in moving if dist(p["pos"], cr["pos"]) <= shy * (0.5 + p["temper"]["bold"]) and cr["fed"].get(p["id"], 0) < C["mouse"]["trust_to_wait"]]
            if scared:
                p = scared[0]
                goal = [0 if p["pos"][0] > cfg["W"] // 2 else cfg["W"] - 1, 0 if p["pos"][1] > cfg["H"] // 2 else cfg["H"] - 1]
                cr["doing"] = "keeping well away"
            elif sweet and not pets:
                n, o = sweet[0]
                goal = o["pos"]
                if dist(cr["pos"], o["pos"]) <= 1:   # it steals sweet things nobody is watching
                    del room["objects"][n]
                    things.gone(house, o, n, "stolen by the mouse")
                    owner = house["pets"].get(o["made"]["owner"])
                    if owner and owner["stage"] != "dead":
                        owner["lost"].append({"name": n, "by": None, "room": room["id"]})
                    moment(house, "mouse", "the mouse made off with %s, '%s'" % (things.a_thing(cfg, o["made"]["recipe"]), n), None, room["id"])
                    house.setdefault("fresh_creatures", []).append({"tick": tick, "kind": "mouse", "room": room["id"], "pet": None, "what": "stole " + n})
            elif friend and (cr["fed"].get(friend["id"], 0) >= C["mouse"]["trust_to_wait"] or lingers(cfg, cr, friend)):
                goal, cr["doing"] = friend["pos"], "waiting near %s" % label(friend)
            elif friend and not moving:
                still = [p for p in pets if not p["plan"] or p["plan"]["left"] is not None]
                if still:   # it comes closer to pets that stay still
                    p = still[0]
                    goal = p["pos"] if dist(p["pos"], cr["pos"]) > 2 else None
                    cr["doing"] = "creeping closer" if goal else "sitting quite near, watching"
            else:
                cr["doing"] = "nosing about"
                goal = cr.get("goal")
                if not goal or goal == cr["pos"]:
                    goal = cr["goal"] = [r.randrange(cfg["W"]), r.randrange(cfg["H"])]
        elif kind == "bird":
            if not c["morning"] and c["phase"] != "day":
                leave(house, cr, "flew off at dusk")
                continue
            cr["doing"] = "singing" if c["morning"] else "hopping about, pecking"
            goal = cr.get("goal")
            if (not goal or goal == cr["pos"]) and r.random() < 0.3:
                goal = cr["goal"] = [r.randrange(cfg["W"]), r.randrange(cfg["H"])]
        if taming and not owner and kind != "mouse":   # the first sign of trust: it lingers by a pet that has fed it
            near = next((p for p in pets if lingers(cfg, cr, p)), None)
            if near and dist(near["pos"], cr["pos"]) > 2:
                goal, cr["doing"] = near["pos"], "lingering near %s" % label(near)
        if goal and in_room(cfg, goal) and goal != cr["pos"]:
            cr["pos"] = [p + (g > p) - (g < p) for p, g in zip(cr["pos"], goal)]


def lit(cfg, o):
    if "made" in o:
        return (o.get("state") == "on" and things.prop(cfg, o).get("light")) or bool(things.doing(cfg, o).get("light"))
    return o.get("state") == "on" and "light" in o.get("fix", {})


def seen(house, cfg, cr, text):
    """Something a creature did, as the pets in the room saw it."""
    for p in awake_pets(house, cr["room"]):
        add_event(house, p, text)


def arrive(house, cfg):
    """Now and then a creature turns up where it would: a moth to a light at night, a bird to the garden in the
    morning, the mouse in the darkest room, a beetle anywhere."""
    C, c, tick = cfg["house"]["creatures"], house["clock"], house["tick"]
    if len(house["creatures"]) >= (cfg["taming"]["creatures"] if arrived(house, "taming") else cfg["house"]["house"]["creatures"]):
        return
    r = rnd(house, "arrive", tick)
    have = {cr["kind"] for cr in house["creatures"] if not cr.get("tame")}   # one wild one of each kind (SPEC-v3.1 §4.3)
    rooms = found(house)
    options = []
    if c["phase"] == "night" and power_on(house):
        options += [("moth", x) for x in rooms if any(lit(cfg, o) for o in x["objects"].values())]
    if c["morning"]:
        options += [("bird", x) for x in rooms if x["type"] == "garden"]
    dark = [x for x in rooms if x["type"] in ("cellar", "storeroom")] or rooms
    options += [("mouse", r.choice(dark)), ("beetle", r.choice(rooms))]
    options = [(k, x) for k, x in options if k not in have]
    if not options or r.random() > cfg["house"]["house"]["creature_chance"]:
        return
    kind, room = r.choice(options)
    house["n"]["creature"] += 1
    pos = free_tile(house, cfg, room, [r.randrange(cfg["W"]), r.randrange(cfg["H"])])
    stay = C[kind]["stay_hours"]
    born(house, cfg, kind, room, pos, stay)
    seen(house, cfg, house["creatures"][-1], "a %s has come in" % kind)
    house.setdefault("fresh_creatures", []).append({"tick": tick, "kind": kind, "room": room["id"], "pet": None, "what": "arrived"})


def born(house, cfg, kind, room, pos, stay):
    house["n"]["creature"] += 1
    house["creatures"].append({"id": "c%d" % house["n"]["creature"], "kind": kind, "room": room["id"], "pos": list(pos), "nest": list(pos),
                               "doing": DOING[kind], "since": house["tick"], "until": house["tick"] + hours(cfg, stay), "fed": {}, "carry": None,
                               "trust": {}, "tame": None, "name": None})
    return house["creatures"][-1]


def leave(house, cr, how):
    for p in awake_pets(house, cr["room"]):
        add_event(house, p, "%s %s" % (called(cr, True), how))
    house["creatures"].remove(cr)
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": cr["room"], "pet": None, "what": how})


def fed(house, cfg, cr, pet, bit):
    """A pet gave a creature a bit (§6.5). The mouse likes seeds, the moth soft things, the bird seeds; the beetle carries anything off."""
    likes = cfg["house"]["creatures"][cr["kind"]]["likes"]
    liked = likes == "anything" or bit in likes
    cr["fed"][pet["id"]] = cr["fed"].get(pet["id"], 0) + (1 if liked else 0)
    if liked and arrived(house, "taming"):
        trusts(cr, pet, cfg["taming"]["fed"])
        tameness(house, cfg, cr)
    pet["trust"][cr["kind"]] = pet["trust"].get(cr["kind"], 0) + (1 if liked else 0)
    pet["met"][cr["kind"]] = pet["met"].get(cr["kind"], 0) + 1
    cr["until"] = max(cr["until"], house["tick"] + hours(cfg, 24))   # a fed creature stays about
    if cr["kind"] == "beetle":
        cr["carry"], cr["doing"] = bit, "carrying some " + bit
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": cr["room"], "pet": pet["id"], "what": "fed " + bit})
    n = cr["fed"][pet["id"]]
    if liked and n == cfg["house"]["creatures"]["mouse"]["trust_to_wait"]:
        moment(house, "befriended", "the %s has started waiting for %s" % (cr["kind"], label(pet)), pet["id"], cr["room"])
    if not liked:
        things.drop_bits(house, cfg, house["rooms"][cr["room"]], cr["pos"], [bit])
        return "you held out the %s to the %s; it sniffed at it and left it lying" % (bit, cr["kind"])
    return "the %s took the %s from you%s" % (cr["kind"], bit, " and stayed close" if n >= 2 else " and backed off to eat it")


def chased(house, cfg, cr, pet):
    pet["met"][cr["kind"]] = pet["met"].get(cr["kind"], 0) + 1
    pet["trust"][cr["kind"]] = max(0, pet["trust"].get(cr["kind"], 0) - 1)
    cr["fed"][pet["id"]] = max(0, cr["fed"].get(pet["id"], 0) - 1)
    if arrived(house, "taming"):
        trusts(cr, pet, cfg["taming"]["chased"])
        tameness(house, cfg, cr)
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": cr["room"], "pet": pet["id"], "what": "chased"})
    if cr.get("tame"):   # one's own animal does not leave the house for it; it only thinks the worse of whoever ran at it
        cr["pos"] = [cfg["W"] - 1 if pet["pos"][0] < cfg["W"] // 2 else 0, cfg["H"] - 1 if pet["pos"][1] < cfg["H"] // 2 else 0]
        return "you ran at %s; it shot away to the far corner and watches you from there" % called(cr, True)
    room = house["rooms"][cr["room"]]
    ways = [rid for rid in room["doors"].values() if house["rooms"][rid]["type"]]
    if cr["kind"] in ("moth", "bird") or not ways:
        leave(house, cr, "fled from %s" % label(pet))
        return "you ran at the %s and it fled out of sight" % cr["kind"]
    cr["room"], cr["pos"] = rnd(house, "flee", house["tick"]).choice(ways), [cfg["W"] // 2, cfg["H"] // 2]
    return "you ran at the %s and it shot out through a door" % cr["kind"]


def startle(house, cfg, room, pet):
    """Something loud was used: the bird goes, the mouse hides (§6.5)."""
    for cr in [c for c in house["creatures"] if c["room"] == room["id"]]:
        if arrived(house, "taming"):
            trusts(cr, pet, cfg["taming"]["noise"])
        if cr.get("tame"):
            continue   # its own pet's noise it puts up with, at a price
        if cr["kind"] == "bird":
            leave(house, cr, "took fright at the noise and flew off")
        elif cr["kind"] == "mouse":
            cr["pos"], cr["doing"] = [cfg["W"] - 1, 0], "hiding from the noise"


# ---- taming (SPEC-v3.1 §4): trust is the creature's, per pet, and nobody is shown it ----

def called(cr, the=False):
    """A creature as it is spoken of: "the mouse", or by the name its pet gave it."""
    return cr.get("name") or ("the " if the else "a ") + cr["kind"]


def trusts(cr, pet, by):
    t = cr.setdefault("trust", {})
    t[pet["id"]] = round(max(0.0, t.get(pet["id"], 0.0) + by), 3)


def lingers(cfg, cr, pet):
    return cr.get("trust", {}).get(pet["id"], 0) >= cfg["taming"]["tame_at"] / 3


def tame_moth_of(house, room):
    """A tame moth leaves the soft things in its pet's room alone (§4.2)."""
    return any(c["kind"] == "moth" and c.get("tame") and c["room"] == room["id"] for c in house["creatures"])


def trust(house, cfg, cr, pets):
    """Each tick: staying still near it and keeping close to it build trust; rushing about beside it loses some."""
    T, per = cfg["taming"], cfg["clock"]["tick_seconds"] / 60
    for p in pets:
        if dist(p["pos"], cr["pos"]) > 3:
            continue
        moving = bool(p["plan"]) and p["plan"]["left"] is None
        if p.get("following") == cr["id"]:
            trusts(cr, p, T["follow_per_minute"] * per)
        elif moving and p.get("spring"):
            trusts(cr, p, T["rush_per_minute"] * per)
        elif not moving:
            trusts(cr, p, T["still_per_minute"] * per)
    tameness(house, cfg, cr)


def tameness(house, cfg, cr):
    """It becomes one pet's animal when it trusts that pet enough, and stops being so if the trust goes."""
    T, t = cfg["taming"], cr.setdefault("trust", {})
    owner = house["pets"].get(cr.get("tame"))
    if owner and owner["stage"] == "dead":   # it outlives its pet and stays with the children (§4 Why)
        kin = [house["pets"][c] for c in owner["children"] if house["pets"].get(c, {}).get("stage") not in (None, "dead", "egg")] \
            or [p for p in house["pets"].values() if family(p) == family(owner) and p["stage"] not in ("dead", "egg")]
        heir = max(kin, key=lambda p: t.get(p["id"], 0), default=None)
        cr["tame"] = heir["id"] if heir else None
        if heir:
            t[heir["id"]] = max(t.get(heir["id"], 0), T["tame_at"])
            add_event(house, heir, "%s, that was your %s's, stays by you now" % (called(cr, True), owner["word"]))
            heir.setdefault("animals", []).append({"id": cr["id"], "kind": cr["kind"], "name": cr.get("name"), "since": house["tick"], "from": owner["id"]})
            moment(house, "tamed", "%s stays with %s now" % (called(cr, True), label(heir)), heir["id"], heir["room"])
        return
    if owner and t.get(owner["id"], 0) < T["tame_at"] / 2:
        cr["tame"] = None
        add_event(house, owner, "%s no longer comes to you" % called(cr, True))
        moment(house, "untamed", "%s has gone wild again" % called(cr, True), owner["id"], cr["room"])
        return
    if not owner and t:
        pid = max(t, key=t.get)
        pet = house["pets"].get(pid)
        if t[pid] >= T["tame_at"] and pet and pet["stage"] not in ("dead", "egg"):
            cr["tame"] = pid
            pet.setdefault("animals", []).append({"id": cr["id"], "kind": cr["kind"], "name": cr.get("name"), "since": house["tick"]})
            add_event(house, pet, "the %s does not run from you any more; it stays by you, and comes when you call. You could give it a name" % cr["kind"])
            pet["news"].append("event")
            moment(house, "tamed", "the %s has become %s's" % (cr["kind"], label(pet)), pid, cr["room"])
            house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": cr["room"], "pet": pid, "what": "tamed"})


def aged(house, cfg, cr):
    """Creatures have lifespans now (§4.3). A tame one has young once, and when it dies its pet is told. True if it died."""
    T = cfg["taming"]
    span = T["lifespan_days"][cr["kind"]] * cfg["ticks_per_day"]
    age = house["tick"] - cr["since"]
    owner = house["pets"].get(cr.get("tame"))
    if owner and not cr.get("young") and age >= span * T["young_at"] and len(house["creatures"]) < T["creatures"]:
        cr["young"] = True
        room = house["rooms"][cr["room"]]
        kid = born(house, cfg, cr["kind"], room, free_tile(house, cfg, room, cr["pos"]), cfg["house"]["creatures"][cr["kind"]]["stay_hours"])
        kid["trust"] = {p["id"]: round(cr["trust"].get(p["id"], 0) / 2, 3) for p in house["pets"].values()
                        if family(p) == family(owner) and p["stage"] != "dead" and cr["trust"].get(p["id"])}
        kid["parent"] = cr["id"]
        tell_all(house, "%s has a young one with it now" % called(cr, True), room=room["id"])
        moment(house, "young", "%s has had a young one" % called(cr, True), owner["id"], room["id"])
        house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": room["id"], "pet": owner["id"], "what": "had young"})
    if age < span or not (owner or cr.get("trust")):
        return False
    house["creatures"].remove(cr)
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": cr["room"], "pet": cr.get("tame"), "what": "died"})
    if owner:
        add_event(house, owner, "%s, your %s, has died; it was old" % (cr["name"], cr["kind"]) if cr.get("name") else "your %s has died; it was old" % cr["kind"])
        owner["news"].append("event")
        for n, v in cfg["effects"]["tame_died"].items():
            owner["needs"][n] = min(100.0, max(0.0, owner["needs"][n] + v))
        for a in owner.get("animals", []):
            if a["id"] == cr["id"]:
                a.update(died=house["tick"], name=cr.get("name"))
        moment(house, "creature died", "%s's %s%s has died" % (label(owner), cr["kind"], " " + cr["name"] if cr.get("name") else ""), owner["id"], cr["room"])
    else:
        for p in awake_pets(house, cr["room"]):
            add_event(house, p, "the %s lies still and does not move again" % cr["kind"])
    return True


def kept(house, cfg, cr, owner, r):
    """What a tame creature does this tick. Returns where it is heading."""
    kind, c, tick, name = cr["kind"], house["clock"], house["tick"], called(cr, True)
    cr["until"] = max(cr["until"], tick + hours(cfg, 24))
    if owner["room"] != cr["room"]:   # it goes where its pet goes
        if owner["stage"] == "egg" or not house["rooms"][owner["room"]]["type"]:
            return None
        door = next((d for d, rid in house["rooms"][owner["room"]]["doors"].items() if rid == cr["room"]), None)
        cr["room"] = owner["room"]
        cr["pos"] = list(house["door_tiles"][door]) if door else free_tile(house, cfg, house["rooms"][owner["room"]], owner["pos"])
        if not owner["sleep"]:
            add_event(house, owner, "%s has come after you" % name)
        return owner["pos"]
    day = c["day"]
    if owner["sleep"] or c["phase"] == "night":
        cr["doing"] = "asleep beside %s" % label(owner)
    else:
        cr["doing"] = "keeping close to %s" % label(owner)
        if kind == "mouse":
            if weather_of(house, cfg, day + 1) == "storm" and c["hour"] >= 20 and cr.get("warned") != day:   # it feels a storm before the pets can
                cr["warned"] = day
                add_event(house, owner, "%s squeaks and will not settle; something is coming in the weather" % name)
            if cr.get("fetched") != day and c["hour"] >= 12 and r.random() < 0.02:
                cr["fetched"] = day
                things.drop_bits(house, cfg, house["rooms"][cr["room"]], owner["pos"], [r.choice(["seed", "petal"])])
                add_event(house, owner, "%s drops something sweet at your feet" % name)
        elif kind == "beetle" and cr.get("fetched") != day and c["hour"] >= 10 and r.random() < 0.02:
            others = sorted({s["bit"] for x in found(house) if x["id"] != cr["room"] for s in x["spots"] if s["ready"]})
            if others:
                cr["fetched"] = day
                bit = r.choice(others)
                things.drop_bits(house, cfg, house["rooms"][cr["room"]], owner["pos"], [bit])
                add_event(house, owner, "%s comes trundling up with some %s from another room and leaves it by you" % (name, bit))
        elif kind == "bird" and c["morning"] and cr.get("sang") != day:
            cr["sang"] = day
            sid = next((x["id"] for x in songs.book(house).values() if x["by"] == "bird"), None) or songs.add(house, "the bird's song", songs.BIRD, "bird", how="the bird", fam=0)
            cr["doing"] = "singing"
            songs.heard(house, cfg, house["rooms"][cr["room"]], sid, cr["id"], lambda p: "%s sings by %s:" % (name, "you" if p is owner else label(owner)))
    return owner["pos"] if dist(owner["pos"], cr["pos"]) > 1 else None


def come(house, cfg, cr, pet):
    """`call`: its animal comes to it from wherever it is in the house."""
    room = house["rooms"][pet["room"]]
    if cr["room"] != room["id"]:
        cr["room"] = room["id"]
    cr["pos"] = free_tile(house, cfg, room, pet["pos"])
    cr["doing"] = "keeping close to %s" % label(pet)
    return "you called, and %s came to you" % called(cr, True)


# ---- arrivals (SPEC-v3.1 §1): each discovery once, counted in world days from the day v3.1 came ----

ORDER = ["writing", "songs", "taming", "radio", "book", "strangers"]


def arrivals(house, cfg):
    v, A = house.get("v31"), cfg["arrivals"]
    if not v or not house["lineage"] or house["lineage"]["ended"] is not None:
        return
    for rid, name, fix in [w for w in v.get("waiting", []) if house["rooms"][w[0]]["type"]]:   # its room has been found since
        v["waiting"].remove([rid, name, fix])
        house["rooms"][rid]["objects"][name] = {"pos": free_tile(house, cfg, house["rooms"][rid], [cfg["W"] // 2, cfg["H"] // 2]), **fix}
    box = house["rooms"].get(v.get("box_again") or "", None)
    if box and house["clock"]["phase"] == "night" and house["tick"] >= v["box_next"] and awake_pets(house, box["id"]):
        v["box_next"] = house["tick"] + cfg["ticks_per_day"] // 2   # it plays again on later nights until someone has heard it
        if songs.music_box(house, cfg, box):
            v["box_again"] = None
    if not awake_pets(house):
        return
    days = (house["tick"] - v["at"]) / cfg["ticks_per_day"]
    for i, name in enumerate(ORDER):
        if name in v["arrived"]:
            continue
        due = 0.05 * i if A["force"] else A[name]
        if days < due or (name == "strangers" and not A["force"] and max(p["gen"] for p in house["pets"].values()) < A["strangers_generations"]):
            return
        if ARRIVE[name](house, cfg):
            v["arrived"][name] = house["tick"]
            note(house, "arrival", None, name)
        return   # one at a time, in order (§1 Why)


def storeroom(house):
    return next((x for x in found(house) if x["type"] == "storeroom"), None)


def put_or_wait(house, cfg, kind, name, fix, fallback=None):
    """Put a new object in the room of that kind; if nobody has found that room yet it waits there (§1)."""
    from .world import room_type
    room = next((x for x in found(house) if x["type"] == kind), None) or fallback
    if room:
        room["objects"][name] = {"pos": free_tile(house, cfg, room, [cfg["W"] // 2, cfg["H"] // 2]), **fix}
        return room
    rid = next((r for r in house["rooms"] if not house["rooms"][r]["type"] and room_type(house, r) == kind), None)
    if rid:
        house["v31"].setdefault("waiting", []).append([rid, name, fix])
    return None


def arrive_writing(house, cfg):
    room = storeroom(house) or house["rooms"][house["start"]]
    things.drop_bits(house, cfg, room, [cfg["W"] // 2, cfg["H"] // 2], ["chalk"] * 3)
    for p in awake_pets(house):
        add_event(house, p, "a crate has appeared here; in it are sticks of something white that leaves a mark on what it touches" if p["room"] == room["id"]
                  else "something was set down somewhere in the house")
        p["news"].append("event")
    moment(house, "arrival writing", "a crate turned up in %s with sticks of chalk in it" % room["name"], None, room["id"])
    return True


def arrive_songs(house, cfg):
    box, v, A = next((x for x in found(house) if "music box" in x["objects"]), None), house["v31"], cfg["arrivals"]
    overdue = (house["tick"] - v["at"]) / cfg["ticks_per_day"] >= (0.05 if A["force"] else A["songs"]) + 1.5
    if not box or (house["clock"]["phase"] != "night" and not overdue):   # "one night"; by day only if no night has found anyone awake
        return False
    learned = songs.music_box(house, cfg, box)
    house["v31"].update(box_again=None if learned else box["id"], box_next=house["tick"] + cfg["ticks_per_day"] // 2)
    for p in awake_pets(house):
        if p["room"] != box["id"]:
            add_event(house, p, "somewhere in the house a small tune plays, and stops")
    moment(house, "arrival songs", "in the night the music box played a tune by itself", None, box["id"])
    return True


def arrive_taming(house, cfg):
    for cr in house["creatures"]:
        cr.setdefault("trust", {p: float(n) * cfg["taming"]["fed"] for p, n in cr.get("fed", {}).items()})
        cr.setdefault("tame", None)
        cr.setdefault("name", None)
    moment(house, "arrival taming", "the small creatures of the house have begun to take notice of who is kind to them")
    return True


def arrive_radio(house, cfg):
    room = put_or_wait(house, cfg, "storeroom", "dial box", {"fix": {"radio": True, "movable": True, "states": ["off", "on"]}, "state": "off"},
                       house["rooms"][house["start"]])
    for p in awake_pets(house):
        add_event(house, p, "a crate has appeared here; in it is a small box with a dial on its front" if room and p["room"] == room["id"]
                  else "something was set down somewhere in the house")
        p["news"].append("event")
    moment(house, "arrival radio", "a crate turned up in %s with a small box in it; the box has a dial" % (room["name"] if room else "a room nobody has found"), None, room and room["id"])
    return True


def arrive_book(house, cfg):
    from . import book
    if not book.available(cfg):   # until the encyclopedia is installed the book is too faded to read, and stays away (§6.2)
        return False
    attic = next((x for x in found(house) if x["type"] == "attic"), None)
    room = put_or_wait(house, cfg, "attic", "heavy book", {"fix": {"book": True}}, None if attic else storeroom(house) or house["rooms"][house["start"]])
    from .world import layout
    layout(cfg, room)   # it stands where that room's layout has a place for it
    for p in awake_pets(house, room["id"]):
        add_event(house, p, "there is a heavy book here that was not here before, too heavy to move; its pages are full of small writing")
        p["news"].append("event")
    moment(house, "arrival book", "a heavy book has turned up in %s" % room["name"], None, room["id"])
    return True


def arrive_strangers(house, cfg):
    """A foundling egg, with no words from anyone (§7.1): the start of a second family."""
    rooms = found(house)
    if len(alive(house)) >= cfg["strangers"]["population"]:
        return False
    homes = [house["rooms"][p["room"]]["cell"] for p in alive(house)]
    far = max(rooms, key=lambda x: (min(abs(x["cell"][0] - c[0]) + abs(x["cell"][1] - c[1]) for c in homes), x["id"]))
    rng = rnd(house, "foundling", house["tick"])
    body = dict(genome.START, hue=rng.randrange(360), pattern=rng.choice(genome.PATTERNS), limbs=rng.randrange(5),
                **{k: round(rng.uniform(*v), 2) for k, v in genome.RANGES.items()})
    egg = new_pet(house, cfg, far["id"], free_tile(house, cfg, far, [cfg["W"] // 2, cfg["H"] // 2]), genome=body, family=2)
    for p in awake_pets(house, far["id"]):
        add_event(house, p, "there is an egg here that nobody you know laid")
        p["news"].append("event")
    moment(house, "arrival strangers", "an egg that is nobody's has appeared in %s" % far["name"], egg["id"], far["id"])
    return True


ARRIVE = {"writing": arrive_writing, "songs": arrive_songs, "taming": arrive_taming, "radio": arrive_radio, "book": arrive_book,
          "strangers": arrive_strangers}


# ---- the window to the real world (§6.6): optional, off by default, and never a pet's doing ----

def real_kind(current):
    """Open-Meteo's current weather as one of the house's kinds (WMO weather codes)."""
    code, temp = current.get("weather_code", 0), current.get("temperature_2m", 15)
    if code >= 95:
        return "storm"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if 51 <= code <= 82:
        return "rain"
    if code in (2, 3, 45, 48):
        return "cloudy"
    return "heat" if temp >= 30 else "clear"


def real_weather(house, kind):
    """Use the sky outside for today. If the fetch failed there is nothing to call this with, and the
    house's own weather carries on."""
    house["real_weather"] = {"day": house["clock"]["day"], "kind": kind}
    if kind != house["weather"]:
        house["weather"] = kind
        tell_all(house, SKY[kind], "phase")
        if kind == "storm":
            moment(house, "storm", "a storm came over the house")
