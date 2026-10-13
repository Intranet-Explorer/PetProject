"""Seasons that matter (SPEC-v3.5 §5). The world clock already turned the seasons (world.clock, house.toml); here is
what each one asks of the house: spring's flowers and seeds, summer's heat on warm things, autumn's leaves and heavy
harvest, winter's sleeping garden and colder rooms; and food, which keeps put away in something and goes bad lying
loose. Every rule is data (seasons.toml, laid over house.toml's season tables) and no model is ever asked. The other
modules call in here with one line each."""
import tomllib

from . import order
from .world import LONG_AGO, add_event, clock, dist, free_tile, label, merge, moment, rnd, season_of


def load(cfg, directory):
    """seasons.toml, laid into the config: each season's table over house.toml's, the seasons' own bits among the
    bits (never grown by a room all year, never delivered), and the few words each season asks into feel.py."""
    S = cfg["seasons"] = tomllib.loads((directory / "seasons.toml").read_text())
    merge(cfg["house"]["seasons"], {s: S.get(s, {}) for s in cfg["house"]["seasons"]})
    for name, b in S.get("bit", {}).items():
        cfg["house"]["bits"][name] = dict(b, late="season")
    force = cfg.setdefault("season", {}).setdefault("force", "")
    if force and force not in cfg["house"]["seasons"]:
        raise ValueError("[season] force = %r is not a season: %s" % (force, ", ".join(cfg["house"]["seasons"])))
    from . import feel   # (the words module keeps what it says as plain names, as world.derive gives it its thresholds)
    feel.SEASONS = {s: v.get("needs", "") for s, v in cfg["house"]["seasons"].items()}
    return cfg


def settle(house, cfg):
    """When a house is opened. One whose seasons have been made longer (the live house went from 6 world days to 42)
    keeps its place in the year: as far through the same season as it was, by a number of world days laid on its
    clock from then on (`season_off`). And a season that is not the one the house was left in (one forced for a
    test, or let go again) has turned: said once, as the clock would say it."""
    H, off = cfg["house"]["house"], house.get("season_off", 0)
    span, was = H["season_days"], house.get("season_days") or H.get("was_season_days", H["season_days"])
    if was != span and house["tick"]:
        day = clock(cfg, house["tick"])["day"] - 1
        off = house["season_off"] = round((day + off) * span / was) - day
    house["season_days"], cfg["season_off"] = span, off
    left, house["clock"]["season"] = house["clock"]["season"], season_of(cfg, house["clock"]["day"])
    if house["tick"] and left != house["clock"]["season"]:
        moment(house, "season", "%s has come" % house["clock"]["season"])
        for p in house["pets"].values():
            if p["stage"] not in ("egg", "dead") and not p["sleep"]:
                add_event(house, p, "the season has turned: it is %s" % house["clock"]["season"])
                p["news"].append("phase")


def rule(house, cfg, key, default=None):
    """What this season says about something (seasons.toml)."""
    return cfg["house"]["seasons"][house["clock"]["season"]].get(key, default)


def open_air(cfg, room):
    """Under the open sky: outdoors, and no glass over it."""
    spec = cfg["house"]["rooms"][room["type"]]
    return bool(spec.get("outdoors")) and not spec.get("glass")


# ---- growing: winter's sleep, autumn's harvest ----

def dormant(house, cfg, room):
    """Does nothing planted here grow just now: under the open sky, in a season when the ground sleeps?"""
    return bool(rule(house, cfg, "dormant")) and open_air(cfg, room)


def asleep(house, cfg, room, name, p):
    """craft.grow asks this of everything planted, every world hour: is it lying asleep under the snow? Then it
    neither grows nor wilts (and whoever planted it is told, once); when the season lets go it grows on."""
    who = house["pets"].get(p.get("by") or "")
    if not dormant(house, cfg, room) or p["grow"] >= 1 or p.get("wilted"):
        if p.pop("dormant", None) and who and who["stage"] != "dead" and p["grow"] < 1:
            add_event(house, who, "the snow has gone from the %s: what you planted there is growing again" % name)
        return False
    p["watered"] = house["tick"]   # (under snow it does not dry out)
    if not p.get("dormant"):
        p["dormant"] = True
        if who and who["stage"] != "dead":
            add_event(house, who, "what you planted in the %s lies asleep under the snow: it will not grow until spring" % name)
    return True


def harvest(house, cfg, gives):
    """craft.use_planted asks this of what a ripe plant gives: in autumn there is more of each food."""
    more = rule(house, cfg, "harvest", 0)
    return gives + [b for b in dict.fromkeys(gives) if b in cfg["seasons"]["food"]["bits"] for _ in range(more)]


# ---- cold and warmth ----

def cold(house, cfg, pet, room, cold, out):
    """physics.effects asks this, with the cold of the hour and everything else acting on the pet so far (`out`).
    Returns the cold with the season's own laid on (winter: cold rooms are colder, day and night). A warm thing
    beside it by day is worse in summer and a comfort in winter. And what the season does here that a pet could not
    otherwise notice is given words (no rate): the sleeping garden, food that will not keep."""
    S, feels = cfg["house"]["seasons"][house["clock"]["season"]], []
    by = S.get("warm_day", 1.0)
    for e in out if by != 1.0 and house["clock"]["phase"] == "day" else ():
        if e["tag"] == "warm" and e["need"] == "comfort" and e["rate"] < 0 and e.get("thing"):
            e["rate"], e["feel"] = e["rate"] * by, S["warm_says"].format(thing=e["thing"])
    if dormant(house, cfg, room):
        feels.append("snow lies over %s: nothing planted out here grows until spring" % room["name"])
    food = loose_food(cfg, room)
    if food:
        feels.append("the %s lying loose here will go bad: put away in something it would keep" % food[0]["bit"])
    out += [{"tag": "season", "need": "comfort", "rate": 0.0, "feel": f, "hidden": False} for f in feels]
    return cold + S.get("cold_rooms", {}).get(room["type"], 0.0)


# ---- every world hour: the season's own bits, and food going bad ----

def loose_food(cfg, room):
    """Food lying on the floor here: not what is put away in something."""
    return [s for s in room["spots"] if s["loose"] and s["ready"] and not s.get("on") and s["bit"] in cfg["seasons"]["food"]["bits"]]


def hourly(house, cfg):
    """director.hourly calls this. Under the open sky the season's own bits lie about while it lasts (spring's
    flowers and seeds, autumn's fallen leaves: picked up, they come back like anything a room grows) and go when it
    goes. Food left lying on a floor goes bad, slower in the cold: a moment, and what is left is nothing to eat."""
    name, F = house["clock"]["season"], cfg["seasons"]["food"]
    for room in [r for r in house["rooms"].values() if r["type"]]:
        if open_air(cfg, room):
            room["spots"][:] = [s for s in room["spots"] if s.get("season", name) == name]
            for bit, n in rule(house, cfg, "garden", {}).items():
                for i in range(n - sum(1 for s in room["spots"] if s.get("season") and s["bit"] == bit)):
                    r = rnd(house, "season", room["id"], bit, house["tick"], i)
                    room["spots"].append({"bit": bit, "pos": free_tile(house, cfg, room, [r.randrange(1, cfg["W"] - 1), r.randrange(1, cfg["H"] - 1)]),
                                          "ready": True, "back": None, "loose": False, "season": name})
        slow = rule(house, cfg, "spoil", 1.0) * (F["cold"] if room["type"] in F["cold_rooms"] else 1.0)
        for s in loose_food(cfg, room):
            s["spoil"] = round(s.get("spoil", 0.0) + slow / (24 * F["days"]), 4)
            if s["spoil"] >= 1:
                moment(house, "spoiled", "a %s left lying in %s went bad" % (s["bit"], room["name"]), None, room["id"])
                for p in house["pets"].values():
                    if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                        add_event(house, p, "the %s left lying here has gone bad" % s["bit"])
                del s["spoil"]
                s.update(bit=F["becomes"], since=house["tick"])


# ---- putting food by: a want in autumn, and a body that can meet it as it tidies ----

def space(cfg, room):
    """What here could take a loose bit: {name: how many}."""
    return {n: k for n, k in order.bit_room(cfg, room).items() if k > 0}


def wants(house, cfg, pet, known, add):
    """wants.candidates asks this: in a season for putting by, food lying loose in a room it knows is something to
    want put away before winter; where nothing has room for it, something to keep it in."""
    for r in known if rule(house, cfg, "stores") else ():
        food = loose_food(cfg, r)
        if food:
            lying = "the %s lying in %s" % (food[0]["bit"], r["name"])
            add("keep", r["id"], "winter is coming: you want %s put by in something, where it will keep" % lying if space(cfg, r) else
                "winter is coming and %s will not keep: you want something there to put it by in, a basket or a box" % lying, "put food by for the winter", 1.6, room=r["id"])


def kept(pet, w):
    """Is the want to put food by met: has it put some by since?"""
    return (pet.get("stored") or {}).get("tick", LONG_AGO) >= w["since"]


def job(house, cfg, pet, room):
    """body asks this before any other tidying: it wants the food here put by, and there is somewhere for it: a
    pawful of it, into what keeps things out of sight if anything does. A job as order.job gives them, or None."""
    food, room_for = loose_food(cfg, room), space(cfg, room)
    if not food or not room_for or not any(w["what"] == "keep" and w["room"] == room["id"] for w in pet.get("wants", [])):
        return None
    first, objs = min(food, key=lambda s: dist(s["pos"], pet["pos"])), room["objects"]
    place = min(room_for, key=lambda n: (not order.inside(cfg, objs[n]), dist(objs[n]["pos"], first["pos"])))
    return {"what": "loose %s" % first["bit"], "pos": first["pos"], "job": ["bits", cfg["seasons"]["food"]["bits"], "on", place], "bonus": cfg["body"]["want"]}


def stored(house, cfg, pet, room, took, place):
    """order.do_job calls this with the loose bits it has just put away in something: any food among them is put by
    (a moment, and the one who did it has met a want to)."""
    food = [s["bit"] for s in took if s["bit"] in cfg["seasons"]["food"]["bits"]]
    if food:
        for s in took:
            s.pop("spoil", None)
        pet["stored"] = {"tick": house["tick"], "room": room["id"]}
        moment(house, "stored", "%s put food by %s: %s" % (label(pet), order.into(cfg, room, place), ", ".join(food)), pet["id"], room["id"])
