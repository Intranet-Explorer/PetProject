"""Self-check for SPEC-v5.0 §2-§4 (helper B: deficits, jobs, trade), §7's: each detector fires on a stub house set up
for it and closes when it is fixed; the board dedups and keeps `since`; a closing is a moment credited to the job's
taker; a stub day where every deficit present gets a taker whose character fits it, nothing is made for nothing, and
each hob's idle share is under 10%; a loner takes no job in a crowded room; a job left untouched goes free; a job's
make step makes its kind (counted for the job); the trade (nothing free, a buy spends, a sale earns, restock still
comes, the Works' house store fills the priced stock and a hob without scrap can't take from it); and each part off
is v4.2.2's. Stub houses only.
    uv run python -m engine.check_jobs"""
import asyncio
import logging
import os
import tempfile

from . import contracts as K
from . import body, deficits, director, health, items, jobs, machine, outdoors, planner, things, trade, works, world
from .check_brain4 import calm, hob, house
from .check_machine import thing
from .check_spirit import Tracebacks
from .world import generate_room


def v5(cfg, on=True, **parts):
    cfg["v5"]["on"] = on
    for p in K.PARTS5:
        cfg[p]["on"] = parts.get(p, True)
    cfg["deficits"]["every"] = 1


def opened(h):
    return {d["id"]: d for d in deficits.board(h)["deficits"]}


def kinds(h):
    return {d["kind"] for d in deficits.board(h)["deficits"]}


def room_of_type(eng, kind):
    h, cfg = eng.house, eng.cfg
    r = next((x for x in h["rooms"].values() if x["type"] == kind), None)
    if r:
        return r
    rid = next(r for r, x in sorted(h["rooms"].items()) if not x["type"] and any(h["rooms"][d]["type"] for d in x["doors"].values()))
    generate_room(h, cfg, rid, kind)
    for p in h["pets"].values():
        p["rooms"][rid] = h["tick"]
    return h["rooms"][rid]


def machine_room(eng):
    """The storeroom and the machine room behind it (hub.migrate), found."""
    from . import hub
    h, cfg = eng.house, eng.cfg
    room_of_type(eng, "storeroom")
    hub.migrate(h, cfg)
    if not h["rooms"][hub.RID]["type"]:
        generate_room(h, cfg, hub.RID, "hub")
    for p in h["pets"].values():
        p["rooms"][hub.RID] = h["tick"]
    machine.state(h, cfg)
    return machine.found(h)


def bare(h, cfg, room):
    """No made thing and no fixture item that covers, heats or lights (a room to set a deficit up in)."""
    for n in [n for n, it in items.objects(h, cfg, room) if set(it["verbs"]) & {"cover", "heat", "light"}]:
        room["objects"].pop(n)


async def detectors(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    cfg["spirit"]["on"] = cfg["deaths"]["on"] = cfg["health"]["on"] = True
    shop = room_of_type(eng, "workshop")
    bare(h, cfg, shop)
    look = lambda: (deficits.tick(h, cfg), kinds(h))[1]
    seen = {}

    def fires(kind, setup, fix, **who):
        setup()
        ks = look()
        assert kind in ks, "%s fires: %s" % (kind, sorted(ks))
        x = next(x for x in deficits.board(h)["deficits"] if x["kind"] == kind and all(x[k] == v for k, v in who.items()))
        seen[kind] = x["words"]
        assert not any(c.isdigit() for c in x["words"]), x["words"]
        fix()
        look()
        assert x["id"] not in opened(h), "%s closes when fixed" % kind
    # cold: autumn, a sleeper in a bare room; a blanket by it
    pet.update(sleeps_in=shop["id"], sleeps_at=[3, 3])
    h["clock"]["season"] = "autumn"
    fires("cold", lambda: None, lambda: thing(eng, shop, "wool blanket", "blanket", "soft", pet["id"]).update(pos=[3, 4]))
    # no_bed: no bed at its place; a bed-mat
    fires("no_bed", lambda: None, lambda: thing(eng, shop, "reed mat", "bed-mat", "soft", pet["id"]).update(pos=[4, 3]), who=pet["id"])
    # dark: its room has no light; a lamp
    fires("dark", lambda: None, lambda: thing(eng, shop, "clay lamp", "lamp", "bright", pet["id"]))
    # mess: loose bits past mess_at
    def litter():
        for i in range(cfg["deficits"]["mess_at"] + 1):
            shop["spots"].append({"bit": "pebble", "pos": [1 + i % 9, 7], "ready": True, "back": None, "loose": True, "since": h["tick"]})
    fires("mess", litter, lambda: shop.update(spots=[s for s in shop["spots"] if not s.get("loose")]))
    # leak
    fires("leak", lambda: shop.update(wet_until=h["tick"] + 999), lambda: shop.update(wet_until=h["tick"]))
    # food_low, then food put by
    F = cfg["seasons"]["food"]["bits"]
    for r in deficits.rooms(h):
        r["spots"] = [s for s in r["spots"] if s["bit"] not in F]
        for o in r["objects"].values():
            o.pop("servings", None) if "meal" in o.get("fix", {}) else None
    fires("food_low", lambda: None, lambda: shop["spots"].extend({"bit": "berry", "pos": [8, 1], "ready": True, "back": None, "loose": False, "since": 0} for _ in range(2 * len(deficits.living(h)))))
    # food_spoiling: berries on a shelf a day from spoiling; into a jar
    thing(eng, shop, "pine shelf", "shelf", "hard", pet["id"])
    jar = thing(eng, shop, "clay jar", "jar", "cool", pet["id"])
    old = h["tick"] - (cfg["deaths"]["spoil_days"] - 1) * cfg["ticks_per_day"] - 1
    shop["spots"].append({"bit": "berry", "pos": [5, 5], "ready": True, "back": None, "loose": True, "on": "pine shelf", "since": old, "put": old})
    fires("food_spoiling", lambda: None, lambda: [s.update(on="clay jar", pos=list(jar["pos"])) for s in shop["spots"] if s.get("on") == "pine shelf"])
    # mouse: in the stores
    store = room_of_type(eng, "storeroom")
    fires("mouse", lambda: director.born(h, cfg, "mouse", store, [3, 3], 30), lambda: h["creatures"].clear())
    # sick_untended: ill; nursed
    other = hob(eng, shop, [6, 6])
    other["sick"] = {"level": "unwell", "since": h["tick"]}
    fires("sick_untended", lambda: None, lambda: health.tend(h, cfg, other, pet), who=other["id"])
    # broken: a lantern past its wear; mended
    lamp = shop["objects"]["clay lamp"]
    it = items.of(h, cfg, lamp, "clay lamp", shop)
    fires("broken", lambda: it["state"].update(broken=True, wear=1.1), lambda: it["state"].update(broken=False, wear=0.0))
    # works_goal: the Works has a goal; none
    machine_room(eng)
    assert machine.found(h), "a machine room"
    keep = dict(cfg["works"])
    fires("works_goal", lambda: None, lambda: cfg.update(works=dict(keep, build=[], forever=None)))
    cfg["works"] = keep
    # gate_shut: a storm a day long, someone wants out; then fair
    outdoors.migrate(h, cfg)
    cfg["outdoors"]["on"] = True
    pet["drive"] = K.drive({"name": "to leave the house"})
    h["v5"]["gate_shut"] = h["tick"] - cfg["ticks_per_day"] - 1
    h["clock"]["phase"], h["weather"] = "day", "storm"
    fires("gate_shut", lambda: None, lambda: h.update(weather="clear"))
    # own_box, own_tool: a grown hob with none; given one
    fires("own_box", lambda: None, lambda: thing(eng, shop, "oak box", "box", "hard", other["id"]), who=other["id"])
    other["skill"] = {"tending": 50}
    fires("own_tool", lambda: None, lambda: thing(eng, shop, "clay trowel", "trowel", "hard", other["id"]), who=other["id"])
    # own_light: awake at night in an unlit room, owning no light
    h["clock"]["phase"] = "night"
    other["room"], other["sleep"] = store["id"], False
    for n, x in list(store["objects"].items()):
        if (items.of(h, cfg, x, n, store) or {}).get("verbs", {}).get("light"):
            store["objects"].pop(n)
    fires("own_light", lambda: None, lambda: thing(eng, shop, "tin lamp", "lamp", "bright", other["id"]), who=other["id"])
    assert set(seen) == set(K.DEFICITS), set(K.DEFICITS) - set(seen)
    print("deficits: every detector fires on a house set up for it and closes when it is fixed:")
    for k, w in seen.items():
        print("  %s: \"%s\"" % (k, w))
    # dedup: the same thing seen twice is one deficit, its since kept, opened once
    h["clock"]["phase"] = "day"
    shop["wet_until"] = h["tick"] + 999
    look()
    since, n = opened(h)["leak|%s|" % shop["id"]]["since"], K.counts(h)["opened"]["leak"]
    h["tick"] += 5
    look()
    assert opened(h)["leak|%s|" % shop["id"]]["since"] == since and K.counts(h)["opened"]["leak"] == n and len([x for x in opened(h) if x.startswith("leak")]) == 1
    # a closing is credited to its job's taker: "the leak in the workshop is mended: Oya's patch"
    opened(h)["leak|%s|" % shop["id"]].update(by=pet["id"], thing="%s's patch" % world.label(pet))
    shop["wet_until"] = h["tick"]
    look()
    c = deficits.board(h)["closed"][-1]
    assert c["by"] == pet["id"] and c["words"] == "the leak in %s is mended: %s's patch" % (shop["name"], world.label(pet)), c
    assert any(m["kind"] == "fixed" and m["text"] == c["words"] for m in h["moments"])
    print("deficits: one leak seen twice is one deficit, since kept; closed, \"%s\"" % c["words"])


async def characters(d):
    """Hobs of plain characters: a tidy one, a brave one, a kind one, a loner; deficits that suit each."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    room = h["rooms"][p0["room"]]
    p0["temper"].update(orderly=0.5, bold=0.5)
    tidy = hob(eng, room, [2, 5], orderly=1.0, bold=0.3, kind=0.5)
    brave = hob(eng, room, [4, 5], orderly=0.3, bold=1.0, kind=0.5)
    kind_ = hob(eng, room, [6, 5], orderly=0.3, bold=0.3, kind=1.0)
    for p, n in ((tidy, "Tidy"), (brave, "Brave"), (kind_, "Kind")):
        p["name"], p["rooms"] = n, dict(p0["rooms"])
    return eng, p0, room, tidy, brave, kind_


async def stub_day(d):
    """A stub world day with deficits present: each gets a taker whose character fits; nothing made for nothing; idle
    share under 10% for every hob."""
    eng, p0, room, tidy, brave, kind_ = await characters(d)
    h, cfg = eng.house, eng.cfg
    shop = room_of_type(eng, "workshop")
    for i in range(cfg["deficits"]["mess_at"] + 3):
        shop["spots"].append({"bit": "pebble", "pos": [1 + i % 9, 7], "ready": True, "back": None, "loose": True, "since": h["tick"]})
    thing(eng, shop, "pine shelf", "shelf", "hard", None)
    thing(eng, shop, "reed broom", "broom", "soft", None)
    store = room_of_type(eng, "storeroom")
    machine_room(eng)   # (the Works wants scrap: a trip to sell to the machine)
    director.born(h, cfg, "mouse", store, [3, 3], 9999)
    thing(eng, store, "brass bell", "bell", "noisy", None)
    room["wet_until"] = h["tick"] + 10 ** 6
    thing(eng, shop, "felt patch", "patch", "soft", None)
    for p in h["pets"].values():   # (a house lived in a while: every hob knows every room found)
        p["rooms"].update({rid: h["tick"] for rid, x in h["rooms"].items() if x["type"]})
    took, was = [], jobs.take

    def take(house_, cfg_, pet, j):
        ok = was(house_, cfg_, pet, j)
        if ok:
            took.append((pet["name"], j["kind"], round(jobs.fit(house_, cfg_, pet, j), 2)))
        return ok
    jobs.take = take
    tb = Tracebacks()
    logging.getLogger().addHandler(tb)
    try:
        present, sat, planned = set(), {}, set()
        for i in range(cfg["ticks_per_day"]):
            await eng.tick()
            if i % 10 == 0 and h["clock"]["phase"] == "day":   # (every deficit seen open in the day, while the hobs are up)
                present |= {d_["kind"] for d_ in deficits.board(h)["deficits"] if h["tick"] - d_["since"] >= jobs.hours(cfg, 1)}   # (open an hour: not one the body put right by itself first)
                planned |= {j_["kind"] for j_ in deficits.board(h)["jobs"] if not j_.get("invent")}   # (SPEC-v5.1: with [knowledge] on, a wrong whose fixer nobody can make has no job;
                # an invention made for a wrong is its inventor's, taken without jobs.take: not a job waiting for a taker)
            for p in h["pets"].values():   # (and, beside the Lab's idle, the ticks in leisure with a job of its own)
                if p.get("job_aim") and not p["sleep"] and (body.state(p)["now"] or {}).get("name") in jobs.LEISURE:
                    sat[p["name"]] = sat.get(p["name"], 0) + 1
        await asyncio.sleep(0)
    finally:
        jobs.take = was
        logging.getLogger().removeHandler(tb)
    assert not tb.seen, tb.seen[0]
    assert not getattr(eng, "step_errors", {}), eng.step_errors
    C = {}
    for day in list((h.get("v5") or {}).get("counts", {})):
        for k, v in K.counts(h, int(day)).items():
            for s, n in v.items():
                C.setdefault(k, {})[s] = C.get(k, {}).get(s, 0) + n
    by = {}
    for who, kind, f in took:
        by.setdefault(kind, []).append((who, f))
    missing = (present & planned) - set(by)
    assert not missing, "every deficit open an hour with a job got a taker: %s not (taken: %s)" % (missing, sorted(by))
    for kind, ws in by.items():
        assert all(f > 0 for _, f in ws), "every taker fits its job: %s %s" % (kind, ws)
    assert by["leak"][0][0] in ("Brave", "Oya") and by["mouse"][0][0] in ("Brave", "Oya"), "the brave go first to the leak and the mouse: %s" % by
    made = C.get("made_for", {})
    assert not made.get("nothing"), "nothing is made for nothing: %s" % made
    idle = {p["name"]: (C.get("idle", {}).get(p["id"], 0), C.get("awake", {}).get(p["id"], 0)) for p in h["pets"].values() if p["stage"] not in ("egg", "dead")}
    assert all(i < 0.1 * max(1, a) for i, a in idle.values()), "idle share under 10%%: %s" % idle
    print("jobs: a stub day; deficits present: %s" % ", ".join(sorted(present)))
    print("jobs: taken: %s" % "; ".join("%s by %s" % (k, ", ".join("%s (fit %.1f)" % w for w in ws)) for k, ws in sorted(by.items())))
    print("jobs: closed today: %s" % ("; ".join(c["words"] for c in deficits.board(h)["closed"]) or "none"))
    print("jobs: made for: %s; idle share: %s" % (made or "nothing made", ", ".join("%s %.1f%%" % (n, 100.0 * i / max(1, a)) for n, (i, a) in sorted(idle.items()))))
    print("jobs: (in leisure with a job of its own, its job waiting: %s)" % ", ".join("%s %.1f%%" % (n, 100.0 * sat.get(n, 0) / max(1, a)) for n, (_, a) in sorted(idle.items())))
    print("jobs: scrap earned %s, spent %s" % (C.get("scrap_earned", {}), C.get("scrap_spent", {})))


async def loner(d):
    """A loner halves a job in a room with others in it: with take_at between, it takes the job alone, not crowded."""
    eng, p0, room, tidy, brave, kind_ = await characters(d)
    h, cfg = eng.house, eng.cfg
    shop = room_of_type(eng, "workshop")
    for p in h["pets"].values():
        p["sleep"] = False
    lone = hob(eng, shop, [3, 3], orderly=1.0, sociable=0.0)
    lone["name"] = "Lone"
    for i in range(cfg["deficits"]["mess_at"] + 1):
        shop["spots"].append({"bit": "pebble", "pos": [1 + i % 9, 7], "ready": True, "back": None, "loose": True, "since": h["tick"]})
    deficits.tick(h, cfg)
    B = deficits.board(h)
    B["deficits"] = [x for x in B["deficits"] if x["kind"] == "mess"]   # (the one job, so nothing else draws it)
    for p in (p0, tidy, brave, kind_):
        p["refused5"] = {"day": h["clock"]["day"], "ids": ["mess|%s|" % shop["id"]]}
        p["room"] = room["id"]
    jobs.tick(eng)
    j = next(j for j in deficits.board(h)["jobs"] if j["kind"] == "mess")
    alone = jobs.score(h, cfg, lone, j)
    if j["taker"]:
        jobs.leave(h, lone, j)
    for p in (tidy, brave):
        p["room"], p["pos"] = shop["id"], [5, 5]
    crowded = jobs.score(h, cfg, lone, j)
    assert crowded <= alone / 2 + 1e-9, (alone, crowded)   # (halved; less again if others are at work there)
    cfg["jobs"]["take_at"] = (alone + crowded) / 2
    jobs.tick(eng)
    assert j["taker"] is None, "a loner takes no job in a crowded room"
    for p in (tidy, brave):
        p["room"] = room["id"]
    jobs.tick(eng)
    assert j["taker"] == lone["id"], "and takes it alone"
    print("jobs: a loner's job in a room with two others scores half (%.2f, alone %.2f): it waits till they go" % (crowded, alone))
    # untouched a world hour of its working day, the job is free again
    world_at = lambda hr: __import__("engine.check", fromlist=["at"]).at(eng, hr)
    world_at(10)
    j["touched"] = h["tick"]
    lone["room"] = room["id"]
    j["steps"] = [{"do": "use", "what": None, "where": shop["id"], "verb": None, "done": False}]
    j.pop("item", None)
    h["tick"] += jobs.hours(cfg, cfg["jobs"]["free_after_hours"]) + 1
    h["clock"] = world.clock(cfg, h["tick"])
    lone["refused5"] = {"day": h["clock"]["day"], "ids": [j["deficit"]]}
    jobs.tick(eng)
    assert j["taker"] is None and j["state"] == "open" and not lone.get("job_aim") and any("you left it undone" in e for _, e in lone["events"]), j
    print("jobs: a job its taker left untouched a world hour is free again")


async def making(d):
    """A job's make step: the body gathers, lays out, makes the job's kind; counted as made for a job. A make with no
    reason is not made."""
    eng, p0, room, tidy, brave, kind_ = await characters(d)
    h, cfg = eng.house, eng.cfg
    shop = room_of_type(eng, "workshop")
    bare(h, cfg, shop)
    kind_.update(sleeps_in=shop["id"], sleeps_at=[3, 3])
    h["clock"]["season"] = "autumn"
    deficits.tick(h, cfg)
    d_ = next(x for x in deficits.board(h)["deficits"] if x["kind"] == "cold")
    j = jobs.plan(h, cfg, d_)
    assert j and [s["do"] for s in j["steps"]][-2:] == ["make", "use"] and j["thing"] in ("blanket", "rug", "cushion"), j
    mind = eng.minds[kind_["id"]]
    kind_["carrying"] = ["fluff", "fluff"]
    kind_["room"], kind_["pos"] = shop["id"], [5, 5]
    j = jobs.plan(h, cfg, d_, kind_)
    deficits.board(h)["jobs"] = [j]
    assert jobs.take(h, cfg, kind_, j) and jobs.step(j)["do"] == "make", j["steps"]
    assert planner.current(kind_)["kind"] == "make" and planner.current(kind_)["job"] == j["id"]
    planner.focus(h, cfg, kind_)
    kind_["ready"] = h["tick"]
    assert planner.make(mind), "the job's kind is made"
    for _ in range(40):
        mind.tick()
        if (kind_.get("last_made") or {}).get("kind") == j["thing"]:
            break
    assert (kind_.get("last_made") or {}).get("kind") == j["thing"], kind_.get("last_made")
    jobs.counted(h, cfg, kind_)
    jobs.advance(h, cfg, kind_, j)
    assert K.counts(h)["made_for"].get("job") == 1 and j.get("item") and jobs.step(j) is None or jobs.step(j)["do"] == "use"
    print("jobs: a cold room's job: %s; made for the job: %s" % (" -> ".join("%s %s" % (s["do"], s["what"] or "") for s in j["steps"]), j["item"]))
    # no reason, no make
    tidy["carrying"], tidy["aims"] = ["fluff", "fluff"], [{"kind": "make", "text": "make something", "since": h["tick"], "target": None}]
    tidy["ready"] = h["tick"]
    assert not planner.make(eng.minds[tidy["id"]]), "a make aim that says nothing of what it is for makes nothing"
    tidy["aims"][0]["for"] = "a gift"
    tidy["ready"] = h["tick"]
    assert planner.make(eng.minds[tidy["id"]]) and tidy["make_for"] == "plan"
    print("jobs: a make aim with no reason makes nothing; one \"for a gift\" does, counted for the plan")


async def trading(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    machine_room(eng)
    at = machine_room(eng)
    pet["room"], pet["rooms"][at["id"]] = at["id"], h["tick"]
    pet["scrap"] = 0
    assert machine.left(h, cfg, pet) == 0 and machine.takeable(h, cfg, pet) == []
    assert machine.check({"type": "machine_take", "what": "wood"}, h, cfg, pet, lambda s: s), "nothing free"
    said, ok = trade.buy(h, cfg, pet, "wood")
    assert not ok and "no scrap" in said, said
    pet["carrying"] = ["pebble", "pebble"]
    said, ok = trade.sell(h, cfg, pet, "pebble")
    assert ok and pet["scrap"] == 1 and K.counts(h)["scrap_earned"][pet["id"]] == 1, said
    thing(eng, at, "blue cup", "cup", "hard", pet["id"])
    said, ok = trade.sell(h, cfg, pet, "blue cup")
    assert ok and pet["scrap"] > 2 and "blue cup" not in at["objects"], said
    wood = machine.state(h, cfg)["stock"]["wood"]
    have = pet["scrap"]
    said, ok = trade.buy(h, cfg, pet, "wood")
    assert ok and pet["scrap"] == have - 1 and machine.state(h, cfg)["stock"]["wood"] == wood - 1 and "wood" in pet["carrying"] and K.counts(h)["scrap_spent"][pet["id"]] == 1, said
    pet["scrap"] = 1
    said, ok = trade.buy(h, cfg, pet, "metal")
    assert not ok and "too little scrap" in said, "metal is three"
    print("trade: nothing free; a pebble sold for one, a cup for more; wood bought for one (\"%s\"); metal is dearer" % said)
    S = machine.state(h, cfg)["stock"]
    for m in S:
        S[m] = 0
    machine.morning(h, cfg)
    assert all(S[m] == cfg["machine"]["restock"] for m in cfg["machine"]["materials"]), "restock still comes"
    for m in S:
        S[m] = 0
    W = works.state(h, cfg)
    W["built"] = [{"what": b["what"], "tick": 0, "by": []} for b in cfg["works"]["build"]]
    W["have"] = cfg["works"]["forever"]["scrap"] - 1
    pet["scrap"] = 0
    pet["carrying"] = ["pebble", "pebble", "pebble"]
    for _ in range(3):
        trade.sell(h, cfg, pet, "pebble")
    assert all(S[m] == cfg["works"]["forever"]["stock"] for m in cfg["machine"]["materials"]), ("the house store fills the stock", S)
    pet["scrap"] = 0
    assert not trade.buy(h, cfg, pet, "clay")[1] and S["clay"] == cfg["works"]["forever"]["stock"], "and a hob without scrap takes none of it"
    print("trade: restock comes; three pebbles sold fill the Works' house store into the machine's priced stock; a hob without scrap gets none")
    # [trade] off: free again, and the house store fills as it did
    cfg["trade"]["on"] = False
    assert machine.left(h, cfg, pet) == cfg["machine"]["free"]
    for m in S:
        S[m] = 0
    W["have"] = cfg["works"]["forever"]["scrap"] - 1
    pet["carrying"] = ["pebble", "pebble", "pebble"]
    machine.feed(h, cfg, pet, "bits", "wood", keep=True)
    assert all(S[m] >= cfg["works"]["forever"]["stock"] for m in cfg["machine"]["materials"]), S
    assert machine.take(h, cfg, pet, "clay")[0].startswith("the machine clunked"), "free, as before"
    print("trade: off, the machine gives two a day free and the house store fills it as before")


async def nursing(d):
    """One job a deficit (21 October 2026: Brody's sick_untended was made twice, at urgency 4); a sick hob nobody
    nurses: every grown hob is asked plainly, not again at the same gravity, again when it is worse, and the question
    waits out the night; no is kept by both (weight 4) and seen by the house; yes takes the job; the reaction's packet
    asks and its schema wants yes or no; [jobs] ask_nurse off, nobody is asked."""
    from . import brain4, memories
    from .brains import model
    eng, oya = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    cfg["spirit"]["on"] = cfg["deaths"]["on"] = cfg["health"]["on"] = True
    cfg["jobs"]["take_at"] = 99   # (nobody takes it of itself: the question is what is checked)
    shop = room_of_type(eng, "workshop")
    lev, brody = hob(eng, shop, [2, 2]), hob(eng, shop, [6, 6])
    lev["name"], brody["name"] = "Lev", "Brody"
    brody["sick"] = {"level": "unwell", "since": h["tick"]}

    def tick():
        h["tick"] += 1
        h["clock"] = world.clock(cfg, h["tick"])
        deficits.tick(h, cfg)
        jobs.tick(eng)
        return [j for j in deficits.board(h)["jobs"] if j["kind"] == "sick_untended"]

    tick()
    js = tick()
    assert len(js) == 1, "one job a deficit at urgency 4: %s" % js
    deficits.board(h)["jobs"].append(dict(js[0], id=js[0]["id"] + "x"))
    assert len(tick()) == 1, "a second copy on the board is dropped"
    asked = lambda p: [e for e in p.get("notable") or [] if e["kind"] == "nurse"]
    assert asked(oya) and asked(lev) and not asked(brody), "every grown hob is asked"
    assert asked(oya)[0]["text"] == "Brody is ill in %s; you and Lev are the grown hobs who can nurse it" % shop["name"], asked(oya)[0]["text"]
    d0 = next(x for x in deficits.board(h)["deficits"] if x["kind"] == "sick_untended")
    assert d0["words"] == "Brody is ill in %s and nobody has looked in" % shop["name"], d0["words"]
    packet, ctx = brain4.react_packet(h, cfg, oya, eng.minds[oya["id"]].mem, asked(oya)[0])
    assert "Will you go and nurse Brody? (nurse: yes or no)" in packet and model.schema4("react", ctx)["properties"]["nurse"] == {"enum": ["yes", "no"]}, packet
    brain4.vigil(oya)
    assert asked(oya), "being asked to nurse waits out the night"
    oya["notable"], lev["notable"] = [], []
    tick()
    assert not asked(oya) and not asked(lev), "not asked again while no worse"
    health.worse(h, cfg, brody)
    tick()
    assert asked(oya) and asked(lev), "asked again when it is worse"
    jobs.nurse_answer(h, cfg, oya, asked(oya)[0], False)
    mine = [m for m in oya["memories"] if m["text"] == "I left Brody lying there"]
    his = [m for m in brody["memories"] if m["text"].startswith("Oya left me lying there")]
    assert mine and mine[0]["weight"] == 4 and his and his[0]["weight"] == 4, (oya["memories"][-2:], brody["memories"][-2:])
    assert any(m["kind"] == "would not nurse" and m["text"] == "Oya would not nurse Brody" for m in h["moments"]), "the house sees it"
    lev["sleep"] = None
    jobs.nurse_answer(h, cfg, lev, asked(lev)[0], True)
    assert tick()[0]["taker"] == lev["id"] or any(a["kind"] == "nurse" and a["target"] == brody["id"] for a in lev.get("aims") or []), "yes: it sees to Brody"
    cfg["jobs"]["ask_nurse"] = False
    brody.pop("nurse_asked5", None)
    oya["notable"], lev["notable"] = [], []
    for j in deficits.board(h)["jobs"]:
        j.update(taker=None, state="open")
    tick()
    assert not asked(oya) and not asked(lev), "ask_nurse off: nobody is asked"
    print("jobs: one job a deficit; a sick hob nobody nurses: every grown hob asked (\"%s\"), again when worse; no is kept by both and seen" % d0["words"])


async def off(d):
    """Each part off is v4.2.2's: no board without [deficits]; without [jobs] the old make and offers, no job aims;
    [v5] off, nothing at all."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg, deficits=False)
    for _ in range(30):
        await eng.tick()
    assert not deficits.board(h)["deficits"] and not deficits.board(h)["jobs"], "deficits off: no board"
    v5(cfg, jobs=False)
    shop = room_of_type(eng, "workshop")
    for i in range(cfg["deficits"]["mess_at"] + 3):
        shop["spots"].append({"bit": "pebble", "pos": [1 + i % 9, 7], "ready": True, "back": None, "loose": True, "since": h["tick"]})
    for _ in range(30):
        await eng.tick()
    assert deficits.board(h)["deficits"] and not deficits.board(h)["jobs"] and not any(p.get("job_aim") for p in h["pets"].values()), "jobs off: deficits but no jobs"
    assert things.better(h, cfg, pet), "jobs off: the house's offers, as before"
    v5(cfg, on=False)
    eng2, pet2 = await house(d + "x")
    for _ in range(60):
        await eng2.tick()
    assert "v5" not in eng2.house and not any(k in p for p in eng2.house["pets"].values() for k in ("job_aim", "job_fit", "scrap", "answer5")), "[v5] off: nothing"
    print("jobs: deficits off, no board; jobs off, deficits but no jobs and the old offers; [v5] off, none of it")


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(detectors(d + "/det"))
        asyncio.run(trading(d + "/trade"))
        asyncio.run(making(d + "/make"))
        asyncio.run(loner(d + "/lone"))
        asyncio.run(nursing(d + "/nurse"))
        asyncio.run(off(d + "/off"))
        asyncio.run(stub_day(d + "/day"))
    print("check_jobs: all passed")


if __name__ == "__main__":
    main()
