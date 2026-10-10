"""What the house does on its own (SPEC-v3 §6.4, §6.5): the day's weather, the seasons, storms and power
cuts, the events nobody caused, and the small creatures. All of it scripted; no model is ever asked."""
from . import things
from .world import (LONG_AGO, add_event, alive, clock, dist, free_tile, hours, in_room, label, moment, power_on, rnd,
                    ticks, weather_of)

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
    if house["tick"] % hours(cfg, 1) == 0:
        hourly(house, cfg)
    if house["tick"] % ticks(cfg, 10) == 0:
        events(house, cfg)
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
    house["shut"] = {k: t for k, t in house["shut"].items() if t > house["tick"]}
    if house.get("storm_cut") and house["storm_cut"] <= house["tick"]:
        house["storm_cut"] = None
        if house["weather"] == "storm":
            power_cut(house, cfg, rnd(house, "cut", house["tick"]).uniform(*H["events"]["power_cut_hours"]), "storm")


# ---- events (§6.5): more often when the house has gone quiet, less in a crisis ----

def events(house, cfg):
    E, tick = cfg["house"]["events"], house["tick"]
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
        room["wet_until"] = tick + hours(cfg, r.uniform(*E["leak_hours"]))
        for n, o in things.made(room).items():   # the water shifts what is lying about
            if not things.prop(cfg, o).get("fixed") and r.random() < 0.5:
                o["pos"] = free_tile(house, cfg, room, [r.randrange(cfg["W"]), r.randrange(cfg["H"])], n)
        tell_all(house, "water is coming in; the floor is wet and some things have shifted", room=room["id"])
        moment(house, "leak", "water came into %s" % room["name"], None, room["id"])
        note(house, "leak", room["id"], "")
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
        bits = [r.choice(sorted(cfg["house"]["bits"])) for _ in range(E["delivery_bits"])]
        things.drop_bits(house, cfg, store, [cfg["W"] // 2, cfg["H"] // 2], bits)
        for p in awake_pets(house):
            add_event(house, p, "a crate of bits has appeared here" if p["room"] == store["id"] else "something heavy was set down somewhere in the house")
            p["news"].append("event")
        moment(house, "delivery", "a crate of bits turned up in %s: %s" % (store["name"], ", ".join(bits)), None, store["id"])
        note(house, "delivery", store["id"], ", ".join(bits))
    elif kind == "lost_thing":
        owned = [(x, n) for x in rooms for n, o in things.made(x).items()
                 if o["made"]["owner"] in house["pets"] and house["pets"][o["made"]["owner"]]["stage"] != "dead"
                 and not things.prop(cfg, o).get("fixed")]
        others = lambda x: [y for y in rooms if y["id"] != x["id"]]
        owned = [(x, n) for x, n in owned if others(x)]
        if owned:
            frm, n = r.choice(owned)
            to = r.choice(others(frm))
            o = frm["objects"].pop(n)
            o["pos"] = free_tile(house, cfg, to, [r.randrange(cfg["W"]), r.randrange(cfg["H"])])
            to["objects"][n] = o
            owner = house["pets"][o["made"]["owner"]]
            owner["lost"].append({"name": n, "by": None, "room": frm["id"]})
            if owner["room"] == frm["id"] and not owner["sleep"]:
                add_event(house, owner, "your %s is not where it was" % n)
                owner["news"].append("event")
                owner["lost"].pop()
            moment(house, "lost", "%s's %s went missing from %s and is in %s" % (label(owner), n, frm["name"], to["name"]), owner["id"], to["id"])
            note(house, "lost thing", to["id"], n)
    elif kind == "surprise":
        bit = r.choice(sorted(cfg["house"]["bits"]))
        things.drop_bits(house, cfg, room, [cfg["W"] // 2, cfg["H"] // 2], [bit])
        tell_all(house, "the visitor left some %s on the floor" % bit, "visitor", room["id"])
        note(house, "surprise", room["id"], bit + " (the director's, in the visitor's name)")


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
    for cr in list(house["creatures"]):
        room = house["rooms"][cr["room"]]
        pets = awake_pets(house, cr["room"])
        kind, r = cr["kind"], rnd(house, "cr", cr["id"], tick)
        if tick >= cr["until"]:
            leave(house, cr, "went away")
            continue
        if tick % 2:
            continue
        goal = None
        if kind == "moth":
            lights = [o for o in room["objects"].values() if lit(cfg, o)] if power_on(house) else []
            if not lights or c["phase"] == "day":
                leave(house, cr, "flew off when the light went")
                continue
            light = min(lights, key=lambda o: dist(o["pos"], cr["pos"]))
            a = (tick // 2) % 8   # round and round the light
            ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)][a]
            goal, cr["doing"] = [light["pos"][0] + ring[0], light["pos"][1] + ring[1]], "circling the light"
            for n, o in things.made(room).items():   # it eats at soft things left by its light (§6.5)
                if o["made"]["recipe"]["material"] == "soft" and dist(o["pos"], light["pos"]) <= 2:
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
                    moment(house, "mouse", "the mouse made off with the %s" % n, None, room["id"])
                    house.setdefault("fresh_creatures", []).append({"tick": tick, "kind": "mouse", "room": room["id"], "pet": None, "what": "stole " + n})
            elif friend and cr["fed"].get(friend["id"], 0) >= C["mouse"]["trust_to_wait"]:
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
    if len(house["creatures"]) >= cfg["house"]["house"]["creatures"]:
        return
    r = rnd(house, "arrive", tick)
    have = {cr["kind"] for cr in house["creatures"]}
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
    house["creatures"].append({"id": "c%d" % house["n"]["creature"], "kind": kind, "room": room["id"], "pos": pos, "nest": list(pos),
                               "doing": DOING[kind], "since": tick, "until": tick + hours(cfg, stay), "fed": {}, "carry": None})
    seen(house, cfg, house["creatures"][-1], "a %s has come in" % kind)
    house.setdefault("fresh_creatures", []).append({"tick": tick, "kind": kind, "room": room["id"], "pet": None, "what": "arrived"})


def leave(house, cr, how):
    for p in awake_pets(house, cr["room"]):
        add_event(house, p, "the %s %s" % (cr["kind"], how))
    house["creatures"].remove(cr)
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": cr["room"], "pet": None, "what": how})


def fed(house, cfg, cr, pet, bit):
    """A pet gave a creature a bit (§6.5). The mouse likes seeds, the moth soft things, the bird seeds; the beetle carries anything off."""
    likes = cfg["house"]["creatures"][cr["kind"]]["likes"]
    liked = likes == "anything" or bit in likes
    cr["fed"][pet["id"]] = cr["fed"].get(pet["id"], 0) + (1 if liked else 0)
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
    house.setdefault("fresh_creatures", []).append({"tick": house["tick"], "kind": cr["kind"], "room": cr["room"], "pet": pet["id"], "what": "chased"})
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
        if cr["kind"] == "bird":
            leave(house, cr, "took fright at the noise and flew off")
        elif cr["kind"] == "mouse":
            cr["pos"], cr["doing"] = [cfg["W"] - 1, 0], "hiding from the noise"


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
