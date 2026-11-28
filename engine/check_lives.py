"""Self-check for SPEC-v4.2 §1 (lives) and §2 (death with a cause), helper A, with stub minds in a temporary house:
the stages' thresholds and the forty-day span; the elder's migration; grief and "old and slow"; for each cause of death
the four rules, the stub forcing it (a death without a world day of visible decline does not happen; tending, bringing
in, stepping in or eating prevents it; the hob who could have and did not remembers so; the cause is on the stone, in
the record, and in a belief of whoever saw); the floor; the remedy and bad food; nursing by the body; the rates as
configured; and [lives] off and [deaths] off each leaving their data unchanged across a stub day.

    uv run python -m engine.check_lives"""
import asyncio
import os
import tempfile

from . import tick as _engine   # noqa: F401 (the engine first)
from . import conflict, contracts as K, cook, health, life, memories, needs, outdoors, pond, world
from .check_brain4 import calm, config as config4, grow
from .tick import Engine, Mind, stub_brains
from .world import generate_room, new_pet


def config(lives=True, deaths=True, day=1800):
    cfg = config4(True)   # (v4.0's parts on, the stub brain)
    cfg["spirit"]["on"] = True
    for part in K.PARTS:
        cfg[part]["on"] = False   # (only A's parts: the others have their own checks)
    cfg["lives"]["on"], cfg["deaths"]["on"] = lives, deaths
    cfg["clock"]["day_seconds"] = day
    return world.derive(cfg)


def to(eng, day, hour):
    """The house's clock to this hour of this day; time passes for everyone (nothing is shifted)."""
    h, cfg = eng.house, eng.cfg
    tick = round(((day - 1) * 24 + hour - 8) * cfg["ticks_per_hour"])
    assert tick >= h["tick"], "the clock only goes forward"
    h["tick"], h["clock"] = tick, world.clock(cfg, tick)
    h["weather"], h["next_event"] = "clear", 10 ** 9


def night(eng, day):
    """The small hours of this day: the night's catching and the day's course (health.daily)."""
    to(eng, day, health.NIGHT_HOUR + 0.5)
    health.daily(eng.house, eng.cfg)


def hob(eng, name, stage="adult", room=None, parent=None, **temper):
    h, cfg = eng.house, eng.cfg
    room = room or next(r for r in h["rooms"].values() if r["type"] == "nursery")
    pet = new_pet(h, cfg, room["id"], world.free_tile(h, cfg, room, [3, 3]), parent=parent and parent["id"])
    if parent:
        parent["children"].append(pet["id"])
    life.hatch(h, cfg, pet)
    grow(h, pet, stage)
    pet.update(name=name, mood=calm(h))
    pet["temper"].update({g: 0.5 for g in pet["temper"]}, **temper)
    eng.minds[pet["id"]] = Mind(eng, pet)
    return pet


async def house(d, cfg, rooms=("pond", "attic", "garden")):
    """A house with its founder hatched, and these rooms found beside the nursery and the hub."""
    eng = Engine(cfg, d, stub_brains)
    p0 = eng.new_lineage()
    p0["laid"] = -10 ** 6
    await eng.tick()
    h = eng.house
    grow(h, p0, "adult")
    p0.update(name="Oya", mood=calm(h))
    p0["temper"].update({g: 0.5 for g in p0["temper"]})
    free = [r for r, x in sorted(h["rooms"].items()) if not x["type"]]
    for kind, rid in zip(rooms, free):
        generate_room(h, cfg, rid, kind)
    if "garden" in rooms:
        outdoors.migrate(h, cfg)
    return eng, p0


def room(eng, kind):
    return next(r for r in eng.house["rooms"].values() if r["type"] == kind)


def place(eng, pets, kind):
    r = room(eng, kind) if isinstance(kind, str) else kind
    for p in pets:
        p["room"], p["pos"], p["sleep"] = r["id"], world.free_tile(eng.house, eng.cfg, r, [4, 4]), None


def heavy(p, kind):
    return [m for m in p.get("memories", []) if m["kind"] == kind and m["weight"] >= 4]


async def dies(eng, pet, cause):
    """It dies by the engine's own path, and is buried: the cause as its key, its words on the stone and the record."""
    got = life.due(eng.house, eng.cfg, pet)
    assert got == cause, "%s dies of %s, not %s" % (pet["name"], cause, got)
    eng.kill(pet, got)
    words = pet["cause_words"]
    assert pet["cause"] == cause and words and eng.house["moments"][-1]["text"].startswith("%s %s" % (pet["name"], words)) or \
        any(m["kind"] == "death" and words in m["text"] for m in eng.house["moments"][-12:]), "the moment carries the words"
    eng.bury(pet)
    stone = next(o for r in eng.house["rooms"].values() for o in r.get("objects", {}).values() if (o.get("memorial") or {}).get("pet") == pet["id"])
    assert words in stone["memorial"]["text"] and stone["memorial"]["cause"] == cause, stone["memorial"]
    assert pet["life"]["cause"] == cause and pet["life"]["cause_words"] == words, "the life record carries it (and the bury keeps it)"
    return words


def stages(cfg, off):
    L, G = life.numbers(cfg)
    assert (G["child"], G["youngling"], G["adult"], L["adult_days"], L["lifespan_days"]) == (3, 8, 14, 19, 40), "§1.1's forty-day life"
    assert life.numbers(off) == (off["life"], off["growth"]), "[lives] off: [life] and [growth] as they are"
    print("lives: forty days in five stages; off, the profile's own")


async def thresholds(d):
    cfg = config()
    eng, p0 = await house(d, cfg, ())
    h, tpd = eng.house, cfg["ticks_per_day"]
    p = hob(eng, "Wen", "hatchling")
    for stage, at, nxt in (("hatchling", 3, "child"), ("child", 8, "youngling"), ("youngling", 14, "adult")):
        p["stage"], p["born"] = stage, h["tick"] - round((at - 0.05) * tpd)
        assert life.earned(h, cfg, p) is None, "not yet %s at day %.2f" % (nxt, at - 0.05)
        p["born"] = h["tick"] - at * tpd
        assert life.earned(h, cfg, p) == nxt, "%s at day %d" % (nxt, at)
    p["stage"], p["stage_at"]["adult"] = "adult", h["tick"] - 19 * tpd
    assert life.earned(h, cfg, p) == "elder", "elder after nineteen adult days"
    p["well"], p["temper"]["hardy"] = [0, 0], 0.5
    assert abs(life.span(cfg, p) - 40) < 1e-6, "an ordinary life is forty days"
    print("lives: the thresholds hold (3, 8, 14; elder after 19 adult days)")


async def migration(d):
    """§1.4 on a house that lived by the base's 24-day lives: each living hob reckoned again, an elder kept an elder."""
    cfg = config()
    eng, p0 = await house(d, cfg, ())
    h, tpd = eng.house, cfg["ticks_per_day"]
    old = config(lives=False)
    e, a, c = hob(eng, "Elm", "elder"), hob(eng, "Ash", "adult"), hob(eng, "Cob", "child")
    for p, age in ((e, 16), (a, 9), (c, 3.5), (p0, 2)):
        p["born"], p["well"] = h["tick"] - round(age * tpd), [0, 0]
    start = old["growth"]["adult"] + old["life"]["adult_days"]   # 13: an elder from here, of a 24-day life
    f = (16 - start) / (life.span(old, e) - start)
    for k in ("v42_lives", "v42_deaths"):   # (a house made with spirit on is marked migrated at birth: this one plays an old house)
        h["migrated"].pop(k, None)
    lines = life.migrate(h, cfg)
    assert len(lines) == 4 and all(any(n in l for l in lines) for n in ("Elm", "Ash", "Cob", "Oya")), lines
    assert e["stage"] == "elder" and "stays an elder" in next(l for l in lines if "Elm" in l), "an elder stays an elder"
    left = life.span(cfg, e) - life.days(h, cfg, e)
    want = (40 - 33) * (1 - f)
    assert abs(left - max(want, cfg["lives"]["old_days"] + 1)) < 0.05 and left > 1, "its span re-drawn as far through an elder's days (%.2f left)" % left
    assert a["stage"] == "youngling" and "adult" not in a["stage_at"] and "youngling" in next(l for l in lines if "Ash" in l), "a nine-day adult is a youngling now: %s %s %s" % (a["stage"], a["stage_at"], lines)
    assert c["stage"] == "child" and p0["stage"] == "hatchling", "by days lived under the new thresholds"
    assert life.migrate(h, cfg) == [] and h["migrated"]["v42_lives"], "once a house"
    print("lives: the migration reckons every living hob again and keeps an elder an elder (%s)" % "; ".join(lines))


async def grief_and_age(d):
    cfg = config()
    eng, p0 = await house(d, cfg, ())
    h, tpd = eng.house, cfg["ticks_per_day"]
    e = hob(eng, "Elm", "elder")
    kid = hob(eng, "Kit", "child", parent=e)
    e["born"], e["well"] = h["tick"] - 30 * tpd, [50.0 * 10 ** 6, 10 ** 6]   # (a life lived middling: one more tick moves its span nowhere)
    span = life.span(cfg, e)
    assert life.grieve(h, cfg, kid) == [e] and abs(life.span(cfg, e) - (span - cfg["lives"]["grief_days"])) < 1e-6, "an elder loses grief_days at its child's death"
    assert life.grieve(h, cfg, kid) == [] and abs(life.span(cfg, e) - (span - 4)) < 1e-6, "once a death"
    e["born"] = h["tick"] - round((life.span(cfg, e) - 2) * tpd)
    energy = e["needs"]["energy"]
    life.wear(h, cfg, e)
    assert e["old"] and e["needs"]["energy"] < energy and any("old and slow" in f for f in life.body_feels(h, cfg, e)), "old and slow, and sooner tired"
    print("lives: an elder grieves its child's death once, and is old and slow in its last days")


async def causes(d):
    """Each cause's four rules, with the stub forcing it."""
    cfg = config()
    W = cfg["deaths"]
    W.update(worsen=1.0, untended_hurt=1.0, fall_chance=1.0, cold_night=0.0, catch=0.0)
    eng, p0 = await house(d, cfg)
    h, tpd = eng.house, cfg["ticks_per_day"]
    kin = [hob(eng, n, "adult", parent=p0) for n in ("Ada", "Bo", "Cy", "Di", "Ed", "Fen")]
    ada, bo, cy, di, ed, fen = kin
    sleepy = lambda: [p.update(sleep=None) for p in h["pets"].values()]
    place(eng, [p0] + kin, "nursery")
    day = h["clock"]["day"]

    # ---- sickness: foreshadowed (no death before a world day of it), preventable (tended), remembered ----
    health.sicken(h, cfg, ada, "a cold night without a bed")
    health.sicken(h, cfg, bo, "a cold night without a bed")
    ada["death_due"] = "sickness"
    assert life.due(h, cfg, ada) is None and "death_due" not in ada, "no death before its decline has shown a world day"
    for n in (1, 2):
        night(eng, day + n)
        health.tend(h, cfg, bo, p0, "nurse")
    assert health.stage_of(ada) == "gravely ill" and not bo.get("sick"), "untended it moves on; tended it is well (%s, %s)" % (ada.get("sick"), bo.get("sick"))
    assert K.since(h, "nursed", 0) and K.since(h, "nursed", 0)[-1]["by"] == p0["id"], "each tending is in the ledger"
    assert "nursed_me" in [c["cause"] for c in bo["opinions"][p0["id"]]["causes"]], "nursed_me fires"
    night(eng, day + 3)
    sleepy()
    words = await dies(eng, ada, "sickness")
    assert words == "died of a sickness, untended"
    could = [p for p in h["pets"].values() if heavy(p, "could have")]
    assert len(could) == 1 and could[0]["id"] not in (ada.get("nursed_by") or {}) and heavy(could[0], "could have")[-1]["about"] == [ada["id"]], "the one who could have and did not remembers (weight 4)"
    assert all(any("Ada" in b["text"] for b in p.get("beliefs_due", [])) for p in kin[1:]), "whoever saw it comes to believe something of it"
    day += 3

    # ---- injury: badly hurt and untended a day becomes sickness; tended, it does not ----
    health.hurt(h, cfg, cy, "badly hurt", "a check")
    health.hurt(h, cfg, di, "badly hurt", "a check")
    health.tend(h, cfg, di, p0, "nurse")
    night(eng, day + 1)
    assert (cy.get("sick") or {}).get("cause") == "injury" and not di.get("sick"), "untended a day the hurt turns to sickness; tended it does not"
    for n in (2, 3, 4):
        night(eng, day + n)
    assert health.declined(h, cfg, cy, "injury") and h["tick"] - cy["decline"]["injury"] >= 3 * tpd, "its decline showed from the hurt"
    sleepy()
    assert await dies(eng, cy, "injury") == "died of a hurt that was never tended"
    day += 4

    # ---- bad food: ill at once, believed by the eater and whoever saw; tended, it passes ----
    assert len([c for c in pond.P(cfg)["catch"] if c.get("poison")]) == 2, "two poisonous catches"
    health.poisoned(h, cfg, di, "red-finned fish")
    assert health.stage_of(di) == "ill" and di["sick"]["cause"] == "bad food" and any(m["kind"] == "poisoned" for m in h["moments"][-3:])
    assert {"name": "avoid_thing", "arg": "red-finned fish", "when": ""} in [b["hook"] for b in di["beliefs_due"]] and any(
        b["hook"] and b["hook"]["arg"] == "red-finned fish" and b["truth"] for b in ed["beliefs_due"]), "the eater and whoever saw believe it"
    health.poisoned(h, cfg, ed, "red-finned fish")
    for n in (1, 2):
        health.tend(h, cfg, ed, p0, "nurse")
        night(eng, day + n)
    assert life.due(h, cfg, di) == "bad food" and health.stage_of(ed) in (None, "unwell"), (health.stage_of(ed))
    sleepy()
    assert await dies(eng, di, "bad food") == "died of the red-finned fish it ate"
    day += 2

    # ---- exposure: a bitter night out is unwell by morning, ill after a second; brought in and tended, it passes ----
    h["cold_snap"] = h["tick"] + 30 * tpd
    meadow = h["rooms"][outdoors.MEADOW]
    place(eng, [ed, fen], meadow)
    ed["sick"] = None
    night(eng, day + 1)
    assert health.stage_of(ed) == "unwell" and ed["sick"]["cause"] == "exposure" and health.stage_of(fen) == "unwell"
    place(eng, [fen], "nursery")
    health.tend(h, cfg, fen, p0, "nurse")
    night(eng, day + 2)
    assert health.stage_of(ed) == "ill" and not fen.get("sick"), "a second night out: ill; brought in and tended: well"
    night(eng, day + 3)
    night(eng, day + 4)
    assert life.due(h, cfg, ed) == "exposure"
    await dies(eng, ed, "exposure")
    day += 4
    del h["cold_snap"]

    # ---- the floor: under it nothing but old age kills (Oya, Bo, Fen and two more) ----
    gil, hal = hob(eng, "Gil", "adult", parent=p0), hob(eng, "Hal", "adult", parent=p0)
    place(eng, [p0, bo, fen, gil, hal], "nursery")
    assert not life.floor(h, cfg)
    print("deaths: sickness, injury, bad food and exposure each foreshadowed, preventable and remembered on the stone")
    return eng, day


async def falls_and_floor(eng, day):
    h, cfg, tpd = eng.house, eng.cfg, eng.cfg["ticks_per_day"]
    P = h["pets"]
    living = sorted((p for p in P.values() if p["stage"] not in ("egg", "dead")), key=lambda p: p["id"])
    p0, bo, fen, gil, hal = living[:5]
    pond_room = room(eng, "pond")
    conflict.C(cfg)["coming_down"]["step_in"] = 0.0

    async def shove(a, b, seen=()):
        place(eng, [a, b], pond_room)
        place(eng, list(seen), pond_room)
        for p in P.values():
            if p not in (a, b) and p not in seen and p["room"] == pond_room["id"]:
                place(eng, [p], "nursery")
        sc = conflict.force(h, cfg, a["id"], b["id"], 5)
        h["tick"] = sc["until"]
        conflict.scuffles(h, cfg)
        return sc

    # ---- manslaughter (v5.3.1): a hob's first shove by an edge is a near-fall; a later one, its grievance open, may kill;
    # a fall unseen is a secret; seen, an accident to judge ----
    g = conflict.grudge(h, cfg, gil["id"], hal["id"], "it took my cup")
    bo.update(stage="adult", sleep=None, flaw=K.flaw("fearful"))
    sc = await shove(gil, hal, seen=[bo])
    assert "nearly went over at the pond" in sc["outcome"] and hal["stage"] != "dead" and "death_due" not in hal, "the first is a near-fall: %s" % sc
    assert any(m["kind"] == "near fall" for m in h["moments"]), "a moment, and the page's banner"
    assert heavy(gil, "fall")[-1]["weight"] == 4 and any(m["weight"] == 4 and gil["id"] in m.get("about", []) for m in hal["memories"]), "a weight-4 memory for both"
    assert gil["id"] in bo.get("wary_of", []) and conflict.wary(h, bo, pond_room["id"]), "the fearful keep away from the shover near edges"
    h["grievances"].remove(g)
    place(eng, [gil, hal], pond_room)
    assert conflict.fall(h, cfg, gil, hal, __import__("random").Random(0), []) is None and "death_due" not in hal, "no fall with no grievance open"
    g = conflict.grudge(h, cfg, gil["id"], hal["id"], "it took my cup again")
    to(eng, day + 2, 12)
    sc = await shove(gil, hal)
    assert "fell at the pond when Gil shoved it" in sc["outcome"] and hal["death_due"] == "manslaughter", sc
    assert gil["secret_due"][-1]["kind"] == "fall" and heavy(gil, "fall")[-1]["weight"] == 5, "the shover: a secret and a memory of weight 5"
    assert not any(k["dead"] == hal["id"] for k in conflict.killings(h)), "unseen, it is no killing"
    await dies(eng, hal, "manslaughter")
    ivy = hob(eng, "Ivy", "adult", parent=p0)
    g = conflict.grudge(h, cfg, gil["id"], ivy["id"], "it mocked me")
    g["history"].append([h["tick"] - 2 * tpd, 3, "Gil hid Ivy's cup"])
    bo.update(stage="adult", sleep=None)
    sc = await shove(gil, ivy, seen=[bo])
    k = next(k for k in conflict.killings(h) if k["dead"] == ivy["id"])
    assert k["accident"] and k["witnesses"] == [bo["id"]] and k["verdict"] is None, "a seen fall is a killing to be judged, an accident"
    await dies(eng, ivy, "manslaughter")
    assert heavy(bo, "could have"), "the one who saw it and did not step in remembers"
    assert any(b["hook"] == {"name": "avoid_place", "arg": pond_room["name"], "when": ""} for b in bo["beliefs_due"]), "whoever saw believes the place is dangerous"

    # ---- killing: rung 8 needs no decline; under the floor a fight stops at a shove ----
    jo = hob(eng, "Jo", "adult", parent=p0)
    place(eng, [gil, jo], "nursery")
    conflict.grudge(h, cfg, gil["id"], jo["id"], "a check")
    sc = conflict.force(h, cfg, gil["id"], jo["id"], 8)
    h["tick"] = sc["until"]
    conflict.scuffles(h, cfg)
    assert jo["death_words"] == "was killed by Gil"
    words = await dies(eng, jo, "killing")
    assert words == "was killed by Gil"
    assert not life.floor(h, cfg), "four alive: no floor yet"
    fen["born"], fen["well"], fen["lost_days"] = h["tick"] - 60 * tpd, [0, 0], 0
    assert await dies(eng, fen, "old age") == "died of old age"
    living = [p for p in P.values() if p["stage"] not in ("egg", "dead")]
    assert len(living) < cfg["deaths"]["floor"] and life.floor(h, cfg), [p["name"] for p in living]
    a, b = living[0], living[1]
    place(eng, [a, b], "nursery")
    g = conflict.grudge(h, cfg, a["id"], b["id"], "a check")
    assert conflict.why_not(h, cfg, dict(g, vengeance=True), a, b, 6) == "floor", "under the floor no fight"
    sc = conflict.force(h, cfg, a["id"], b["id"], 8)
    h["tick"] = sc["until"]
    conflict.scuffles(h, cfg)
    assert "shoved" in sc["outcome"] and b["stage"] != "dead" and not b.get("death_due"), "a forced killing stops at a shove (%s)" % sc["outcome"]
    health.sicken(h, cfg, b, "a check", level="gravely ill")
    b["decline"]["sickness"] = h["tick"] - 5 * tpd
    b["sick"]["grave"] = h["tick"] - 2 * tpd
    night(eng, h["clock"]["day"] + 1)
    assert not b.get("death_due") and health.stage_of(b) == "gravely ill", "a sickness lingers"
    b["death_due"] = "sickness"
    assert life.due(h, cfg, b) is None, "and no death under the floor"
    b["born"], b["well"], b["lost_days"] = h["tick"] - 60 * tpd, [0, 0], 0
    assert life.due(h, cfg, b) == "old age", "but old age"
    print("deaths: a fall at the pond needs a feud a day old, is a secret unseen and an accident seen; a killing; the floor holds")


async def starving_and_neglect(d):
    cfg = config()
    eng, p0 = await house(d, cfg, ())
    h, tpd = eng.house, cfg["ticks_per_day"]
    kin = [hob(eng, n, "adult", parent=p0) for n in ("Ada", "Bo", "Cy", "Di")]
    ada, bo = kin[:2]
    needs.tick(h, cfg)   # (hunger, safety and pride, as a waking house has them)
    ada["needs"]["hunger"] = bo["needs"]["hunger"] = 0.0
    needs.tick(h, cfg)
    assert ada["starving"] == h["tick"] and ada["decline"]["starvation"] == h["tick"], "starving shows"
    h["tick"] += round(cfg["needs4"]["starve_days"] * tpd) + 1
    bo["needs"]["hunger"] = 60.0
    needs.tick(h, cfg)
    assert not bo.get("starving") and "starvation" not in bo.get("decline", {}) and life.due(h, cfg, bo) is None, "fed, it does not starve"
    ada["needs"]["hunger"] = 0.0
    await dies(eng, ada, "starvation")
    assert any(heavy(p, "could have") and "food" in heavy(p, "could have")[-1]["text"] for p in kin[1:] + [p0])
    cy = kin[2]
    cy.update(lost_days=3.0, weak=False)
    cy["born"] = h["tick"] - round((life.span(cfg, cy) + 0.1) * tpd)
    assert life.due(h, cfg, cy) == "old age", "neglect not foreshadowed is its span's end"
    cy.update(weak=True, decline={"neglect": h["tick"] - tpd // 2})
    assert life.due(h, cfg, cy) == "old age", "weak only half a day: not yet neglect"
    cy["decline"]["neglect"] = h["tick"] - tpd
    assert life.due(h, cfg, cy) == "neglect", "weak a world day, it is neglect"
    print("deaths: starvation and neglect show a world day first, and eating prevents starving")


async def remedy_and_food(d):
    cfg = config()
    eng, p0 = await house(d, cfg, ("cellar", "garden"))
    h = eng.house
    off = config(deaths=False)
    assert ("petal", "press") not in off["craft"]["rules"] and "moss broth" not in cook.D(off) and "remedy" not in off["house"]["bits"], "off: no remedy, no broth"
    health.install(cfg)
    assert cfg["craft"]["rules"][("petal", "press")]["gives"] == "remedy" and "moss broth" in cook.D(cfg) and ("moss", "cook") in cfg["craft"]["rules"]
    kin = [hob(eng, n, "adult", parent=p0) for n in ("Ada", "Bo", "Cy")]
    ada, bo, cy = kin
    health.sicken(h, cfg, ada, "a check", level="gravely ill")
    assert health.tend(h, cfg, ada, bo, "remedy") == "unwell", "a remedy moves it back two stages"
    health.sicken(h, cfg, cy, "a check", level="ill")
    cy["carrying"].append("remedy")
    health.nursing(h, cfg)
    assert not cy.get("sick") and "remedy" not in cy["carrying"], "a sick hob with a remedy takes it"
    # spoiled food on a shelf (not in a keeper); the cellar's broth; a pot made of either sickens
    nursery = room(eng, "nursery")
    shelf = next(n for n, o in nursery["objects"].items() if o.get("fix", {}).get("store")) if any(o.get("fix", {}).get("store") for o in nursery["objects"].values()) else None
    spot = {"bit": "bean", "pos": [1, 1], "ready": True, "back": None, "loose": True, "on": shelf or "shelf", "put": h["tick"] - 4 * cfg["ticks_per_day"]}
    nursery["spots"].append(spot)
    assert health.spoil(h, cfg) >= 1 and spot["spoiled"], "food put by past spoil_days spoils"
    assert cook.take_in(h, cfg, ada, nursery, "bean") == {"what": "spoiled bean", "level": "unwell"}
    fresh = dict(spot, put=h["tick"], spoiled=None)
    fresh.pop("spoiled")
    nursery["spots"].append(fresh)
    assert health.spoil(h, cfg, nursery, early=True) == 1 and fresh["spoiled"], "the director's sickness in the food: a shelf spoils early"
    stove = {"pot": {"n": 1, "dish": "moss broth", "servings": 2, "of": 2, "by": ada["id"], "title": None, "from": ["moss"], "recipe_by": None,
                     "at": h["tick"], "keeps": h["tick"] + 10 ** 6, "ate": {}, "bad": {"what": "moss broth", "level": "ill"}}}
    bo["sick"], bo["last_eat"] = None, -10 ** 6
    cook.eat(h, cfg, bo, nursery, "stove", stove)
    assert health.stage_of(bo) == "ill" and bo["sick"]["what"] == "moss broth", "the cellar's broth makes the eater ill at once"
    print("deaths: the remedy (off: none) moves a sickness back two; shelf food spoils; bad food in the pot sickens")


async def nursing(d):
    """The body's `nurse`: a grown hob beside a sick one sits with it, and that is a day's tending."""
    cfg = config()
    cfg["deaths"]["worsen"] = 0.0
    eng, p0 = await house(d, cfg, ())
    h = eng.house
    kin = [hob(eng, n, "adult", parent=p0, kind=0.9) for n in ("Ada", "Bo", "Cy")]
    ada = kin[0]
    place(eng, [p0] + kin, "nursery")
    to(eng, h["clock"]["day"], 10)
    health.sicken(h, cfg, ada, "a check", level="ill")
    assert health.patients(h, cfg, p0)[0][0] is ada and not health.patients(h, config(deaths=False), p0), "a patient for a grown hob; none with [deaths] off"
    for _ in range(600):
        await eng.tick()
        if K.since(h, "nursed", 0):
            break
    rec = K.since(h, "nursed", 0)
    assert rec and rec[0]["pet"] == ada["id"] and rec[0]["how"] == "nurse" and health.stage_of(ada) == "unwell", "a hob's nurse tends it (%s)" % rec
    print("deaths: a grown hob's body nurses a sick one beside it, and it is better for it (%s)" % h["pets"][rec[0]["by"]]["name"])


def rates(cfg):
    """§2 "rare": no cause's chance as configured is more than twice its target, on a 7-hob house living forty days.
    Expected deaths of each cause a world day, under the assumptions in words beside it (the rehearsal measures)."""
    W, hobs, life_days = cfg["deaths"], 7, cfg["lives"]["lifespan_days"]
    deaths_a_day = hobs / life_days
    untended = 0.2   # the share of sicknesses nobody nurses through to the end (a house with grown hobs and the planner's nurse)
    catches = pond.P(cfg)["catch"]
    common = [c for c in catches if c["tier"] == "common"]
    poison_share = sum(c.get("weight", 1) for c in common if c.get("poison")) / sum(c.get("weight", 1) for c in common)
    got = {"sickness": hobs * (W["cold_night"] * 0.5 * 0.25 * 1.1 + W["catch"] * 0.01) * untended,   # half the nights cold, a quarter in a cold room with no bed; a bed shared with a sick hob one night in a hundred
           "injury": hobs * 0.01 * W["untended_hurt"] * untended,   # badly hurt one day in a hundred
           "bad food": 0.5 * poison_share * untended,   # half a raw or cooked fish a day
           "manslaughter": 0.1 * (2 / 12) * W["fall_chance"]}   # a shove a house in ten days, two rooms of twelve
    for cause, n in got.items():
        target = W["rates"][cause] * deaths_a_day
        assert n <= 2 * target, "%s: %.4f a day as configured, its target %.4f" % (cause, n, target)
    print("deaths: as configured, no cause runs more than twice its target (%s)" % ", ".join("%s %.4f" % kv for kv in got.items()))


LIVES_KEYS = ("span_add", "old", "grieved")
DEATHS_KEYS = ("decline", "cause_words", "death_words", "shoved_by", "tainted")
DEATHS_HOUSE = ("health_day", "health_last", "cold_snap", "deaths_installed")


async def off_day(d, part):
    """One part off (spirit on): a stub day of the house, and its data never appears."""
    cfg = config(lives=part != "lives", deaths=part != "deaths")
    eng, p0 = await house(d, cfg)
    h = eng.house
    kin = [hob(eng, n, "adult", parent=p0) for n in ("Ada", "Bo", "Cy", "Di")]
    e = hob(eng, "Elm", "elder")
    e["stage_at"]["elder"] = h["tick"]
    health.sicken(h, cfg, kin[0], "a check")
    if part == "deaths":
        health.hurt(h, cfg, kin[1], "badly hurt", "a check")
    for _ in range(cfg["ticks_per_day"]):
        await eng.tick()
    assert not h.get("migrated", {}).get("v42_" + part)
    for p in h["pets"].values():
        keys = LIVES_KEYS if part == "lives" else DEATHS_KEYS
        assert not any(k in p for k in keys), "%s off: %s has none of %s" % (part, p["name"], [k for k in keys if k in p])
        if part == "deaths":
            assert not (p.get("sick") or {}).get("cause") and "tended" not in (p.get("hurt") or {}) and p.get("cause") in (None, "violence", "sickness", "starvation", "neglect", "old age")
    if part == "deaths":
        assert not any(k in h for k in DEATHS_HOUSE) and not (h.get("spirit") or {}).get("nursed") and ("petal", "press") not in cfg["craft"]["rules"]
        assert not any(s.get("spoiled") or "put" in s for r in h["rooms"].values() for s in r.get("spots", []))
    print("lives: [%s] off, a stub day leaves its data unchanged" % part)


async def checks(root):
    cfg, off = config(), config(lives=False)
    stages(cfg, off)
    rates(cfg)
    await thresholds(root + "/t")
    await migration(root + "/m")
    await grief_and_age(root + "/g")
    eng, day = await causes(root + "/c")
    await falls_and_floor(eng, day)
    await starving_and_neglect(root + "/s")
    await remedy_and_food(root + "/r")
    await nursing(root + "/n")
    await off_day(root + "/ol", "lives")
    await off_day(root + "/od", "deaths")
    assert set(K.CAUSES) <= set(life.CAUSE_WORDS) and set(K.SICK) <= set(health.FEEL) and set(K.CAUSES) - {"old age", "killing"} <= set(health.FORESHADOW)
    for f in K.API["A"]["engine.life"]:
        assert callable(getattr(life, f))
    for f in K.API["A"]["engine.health"]:
        assert callable(getattr(health, f))


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(checks(d))
    print("check_lives: all passed")


if __name__ == "__main__":
    main()
