"""Self-check for the vending machine and the base materials (SPEC-v3.5 §4.3): the rules in machine.toml,
crafting.toml and engine/machine.py, proved without a model.

    uv run python -m engine.check_machine

Scripted minds only, in a temp folder of its own; a few seconds."""
import asyncio
import json
import tempfile

from . import actions, body, craft, director, machine, order, wants, world
from .check import at, engine, scripted
from .tick import Engine
from .world import LONG_AGO, generate_room

SIX = ["wood", "stone", "metal", "clay", "fibre", "sand"]


def thing(eng, room, name, kind, material, owner, days=0.0, **more):
    """A made thing standing in a room, as things.make leaves one, last touched `days` world days ago."""
    h, cfg = eng.house, eng.cfg
    h["n"]["thing"] += 1
    tick = h["tick"] - round(days * cfg["ticks_per_day"])
    room["objects"][name] = o = {"pos": world.free_tile(h, cfg, room, [5, 4]), "made": {
        "id": h["n"]["thing"], "recipe": {"name": name, "kind": kind, "material": material, "color": "blue", "size": 2, "purpose": "a check"},
        "by": owner, "owner": owner, "tick": tick, "bits": [], "uses": 0, "ups": 0, "used_at": tick, "heirloom": None, "behavior": None}}
    o.update(more)
    return o


def moments(h, kind):
    return [m["text"] for m in h["moments"] if m["kind"] == kind]


async def run(d):
    cfg = world.load_config()
    cfg["weather"]["real"] = False
    C, M, bits = cfg["craft"], cfg["machine"], cfg["house"]["bits"]

    # ---- the six base materials: bits like any other, with what the spec says of each, and their rules in the processes ----
    assert M["materials"] == SIX and all(m in bits for m in SIX), "the machine holds the six base materials, and each is a bit"
    assert {"hard"} <= set(bits["wood"]["can"]) and {"hard", "heavy"} <= set(bits["stone"]["can"]) and {"hard", "noisy"} <= set(bits["metal"]["can"])
    assert "soft" in bits["clay"]["can"] and "hard" not in bits["clay"]["can"] and "hard" in bits["fired clay"]["can"], "clay is soft until it is warmed"
    assert "heavy" in bits["sand"]["can"] and "soft" in bits["fibre"]["can"]
    gives = lambda bit, how: C["rules"].get((bit, how), {}).get("gives")
    for (bit, how), want in {("wood", "carve"): "carved wood", ("wood", "grind"): "plank", ("stone", "grind"): "sharp stone", ("stone", "press"): "grit",
                             ("metal", "warm"): "warm metal", ("warm metal", "press"): "metal plate", ("clay", "warm"): "fired clay",
                             ("fibre", "weave"): "cord", ("fibre", "press"): "felt", ("sand", "press"): "packed sand"}.items():
        assert gives(bit, how) == want, "%s, %s, gives %s (not %s)" % (bit, craft.DONE[how], want, gives(bit, how))
    made_of, grew = set(SIX), True
    while grew:   # everything that comes of the six, however many steps on
        new = {r["gives"] for (bit, _), r in C["rules"].items() if bit in made_of and r.get("gives")} - made_of
        made_of, grew = made_of | new, bool(new)
    mine = [(bit, how) for (bit, how) in C["rules"] if bit in made_of]
    assert len(mine) >= 15 + 6, "the base materials have their rules: %d" % len(mine)   # (some fifteen new ones, beside those wood, clay and sand had)
    for (bit, how), r in C["rules"].items():
        assert bit in bits and how in C["process"] and (r.get("spoils") or r["gives"] in bits), "the rule %s|%s names what exists" % (bit, how)
    for name, m in C["material"].items():
        assert set(m["can"]) <= {p for p, v in cfg["materials"].items() if isinstance(v, dict) and "says" in v}, "%s can only be what a thing can be" % name
    assert not craft.lacking(cfg, "hammer", ["stone", "plank", "cord"]) and not craft.lacking(cfg, "carver", ["sharp stone"]), "tools can be made of what comes of them"

    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    at(eng, 10)
    pet.update(stage="adult", name="Lean")
    pet["stage_at"]["adult"] = h["tick"]
    mem = eng.minds[pet["id"]].mem
    nursery = h["rooms"][pet["room"]]
    sr = generate_room(h, cfg, next(iter(nursery["doors"].values())), "storeroom")   # the storeroom, next door to the nursery
    cellar = generate_room(h, cfg, next(rid for rid, x in h["rooms"].items() if not x["type"]), "cellar")
    shop = generate_room(h, cfg, next(rid for rid, x in h["rooms"].items() if not x["type"]), "workshop")
    name = machine.spot(sr)
    assert name == "vending machine" and sr["objects"][name]["pos"] == cfg["layouts"]["storeroom"]["fixtures"][name]["pos"], "the machine stands in the storeroom, where its layout puts it"
    assert sr["objects"][name]["pos"] not in [list(t) for t in h["door_tiles"].values()] and "machine" in actions.fixture_says(sr["objects"][name]["fix"])
    S = machine.state(h, cfg)
    assert S["stock"] == {m: M["start"] for m in SIX} and M["start"] <= M["limit"] and 10 <= M["limit"] <= 14, "about twelve of each"

    def go(room, carrying=()):
        pet.update(room=room["id"], pos=[5, 4], carrying=list(carrying), sleep=None)
        pet["rooms"][room["id"]] = h["tick"]
        pet["needs"]["energy"] = 80.0

    def act(a):
        why = actions.check(a, h, cfg, pet, mem)
        return why, (None if why else actions.apply(h, cfg, pet, a, mem)[0])

    # the rules work in the processes, where each can be done: grinding on the cellar's floor, pressing under its barrel, weaving at the bench, warming by a lit lamp
    go(cellar, ["stone", "wood", "sand"])
    for bit, how, got in (("stone", "grind", "sharp stone"), ("wood", "grind", "plank"), ("sand", "press", "packed sand")):
        why, said = act({"type": "process", "what": bit, "how": how})
        assert not why and got in pet["carrying"] and bit not in pet["carrying"], "%s %s: %s %s" % (bit, how, why, pet["carrying"])
    go(shop, ["fibre", "fibre"])
    why, said = act({"type": "process", "what": "fibre", "how": "weave"})
    assert not why and pet["carrying"] == ["cord"], "two strands of fibre weave into a cord: %s %s" % (why, pet["carrying"])
    go(nursery, ["metal", "clay"])
    nursery["objects"]["lamp"]["state"] = "on"
    for bit, got in (("metal", "warm metal"), ("clay", "fired clay")):
        why, said = act({"type": "process", "what": bit, "how": "warm"})
        assert not why and got in pet["carrying"], "%s warmed: %s %s" % (bit, why, pet["carrying"])
    assert "it might be pressed" in C["rules"][("metal", "warm")]["hint"]
    go(cellar, ["warm metal"])
    why, said = act({"type": "process", "what": "warm metal", "how": "press"})
    assert not why and pet["carrying"] == ["metal plate"], "warm, the metal bends: %s" % why

    # ---- it gives: two a world day to each pet, of its choosing, and no third; only at the machine ----
    go(nursery)
    assert not set(machine.ACTIONS) & set(actions.allowed(h, cfg, pet, mem)) and actions.check({"type": "machine_take", "what": "clay"}, h, cfg, pet, mem) == "there is no machine here"
    go(sr)
    assert set(machine.ACTIONS) & set(actions.offered_to_mind(h, cfg, pet, mem)) == {"machine_take"}, "at the machine a mind may take from it (and feed it when it has something to feed)"
    assert actions.destination(h, cfg, pet, {"type": "machine_take", "what": "clay"}) is not None, "it walks over to the machine"
    n = len(h.get("acts", []))
    why, said = act({"type": "machine_take", "what": "clay"})
    assert not why and pet["carrying"] == ["clay"] and S["stock"]["clay"] == M["start"] - 1 and moments(h, "machine") == ["Lean took clay from the machine"], (why, said)
    assert machine.light(h, cfg) == "lit" and "one more" in said, "its lights come up, and it says what is left for the day: %s" % said
    why, said = act({"type": "machine_take", "what": "stone"})
    assert not why and pet["carrying"] == ["clay", "stone"] and "stone" in wants.held(pet)
    why, said = act({"type": "machine_take", "what": "wood"})
    assert why and "today" in why and pet["carrying"] == ["clay", "stone"] and S["stock"]["wood"] == M["start"], "no third: %s" % why
    assert "machine_take" not in actions.allowed(h, cfg, pet, mem) and machine.takeable(h, cfg, pet) == []
    assert actions.check({"type": "machine_take", "what": "petal"}, h, cfg, pet, mem) == "the machine does not hold that"
    h["tick"] += 20
    assert machine.light(h, cfg) is None, "and its lights go down again"
    at(eng, 10, h["clock"]["day"] + 1)
    assert machine.left(h, cfg, pet) == M["free"] == 2 and not actions.check({"type": "machine_take", "what": "wood"}, h, cfg, pet, mem), "the next day it gives again"

    # ---- its stock runs out, and the morning's delivery puts a little back, never past its limit ----
    S["stock"].update(sand=1, wood=M["limit"])
    go(sr)
    why, said = act({"type": "machine_take", "what": "sand"})
    assert not why and S["stock"]["sand"] == 0
    why = actions.check({"type": "machine_take", "what": "sand"}, h, cfg, pet, mem)
    assert why == "the machine has no sand left" and "sand" not in machine.takeable(h, cfg, pet) and "sand" not in machine.sense(h, cfg, pet)[0].split(";")[0]
    was = dict(h["clock"])
    h["clock"] = dict(was, phase="night")   # dawn, as the clock sees it: the meals are set out, and the delivery comes
    director.begin(h, cfg)
    assert S["stock"]["sand"] == M["restock"] > 0 and S["stock"]["wood"] == M["limit"] and S["stock"]["clay"] == M["start"] - 1 + min(1, M["restock"]), S["stock"]
    assert len(moments(h, "stocked")) == 1 and "morning delivery" in moments(h, "stocked")[0] and "sand" in moments(h, "stocked")[0]
    director.begin(h, cfg)
    assert len(moments(h, "stocked")) == 1, "once a morning"

    # ---- it takes back: what a thing is like decides what it offers; one for a thing, one for three bits ----
    go(sr)
    me = pet["id"]
    for kind, material, back in (("nest", "soft", ["fibre"]), ("charm", "hard", ["wood", "stone"]), ("bell", "noisy", ["metal"]), ("cushion", "snug", ["fibre", "clay", "sand"][:1]),
                                 ("lamp", "bright", ["clay", "sand"]), ("glimmer-whatsit", "noisy", ["metal"]), ("curio", "sweet", ["clay", "sand"])):
        thing(eng, sr, kind + " one", kind, material, me)   # (the last two: kinds the catalog has never heard of, as an invented one is)
        assert machine.offers(h, cfg, pet, sr, kind + " one") == back, "%s %s gives %s, not %s" % (material, kind, back, machine.offers(h, cfg, pet, sr, kind + " one"))
    assert machine.gives(cfg, ["no such nature"]) == ["clay", "sand"] and machine.gives(cfg, []) == ["clay", "sand"], "anything else gives clay or sand"
    h["invented"] = {"night fork": {"name": "night fork", "props": ["hard", "bright"], "parts": [{"part": "stick", "material": "hard"}, {"part": "cloth", "material": "soft"}]}}
    thing(eng, sr, "fork", "night fork", "glowing", me)
    assert machine.offers(h, cfg, pet, sr, "fork") == ["wood", "stone", "fibre"], "an invented thing gives for what it and its parts are like: %s" % machine.offers(h, cfg, pet, sr, "fork")
    assert "machine_feed" in actions.allowed(h, cfg, pet, mem) and machine.ctx(h, cfg, pet)["feed"]["nest one"] == ["fibre"]
    stock, n_gone = dict(S["stock"]), len(h["gone_things"])
    pet["carrying"] = []
    why = actions.check({"type": "machine_feed", "what": "nest one", "for": "metal"}, h, cfg, pet, mem)
    assert why == "for that the machine offers fibre", why
    why, said = act({"type": "machine_feed", "what": "nest one", "for": "fibre"})
    assert not why and "nest one" not in sr["objects"] and pet["carrying"] == ["fibre"] and S["stock"] == stock, "one thing in, one material out, and its stock as it was: %s" % why
    assert moments(h, "fed") == ["Lean fed a soft nest to the machine for fibre"] and h["gone_things"][-1]["gone"][1] == "fed to the machine" and len(h["gone_things"]) == n_gone + 1
    assert machine.left(h, cfg, pet) == 1, "what it gives back is not one of the day's two"
    for what in ("glimmer-whatsit one", "curio one", "fork"):   # none of them a kind of the catalog
        why, said = act({"type": "machine_feed", "what": what, "for": machine.offers(h, cfg, pet, sr, what)[0]})
        assert not why and what not in sr["objects"], "a thing of an unknown kind is fed like any other: %s" % why
    assert "a noisy glimmer-whatsit" in moments(h, "fed")[1] and pet["carrying"] == ["fibre", "metal", "clay"], (moments(h, "fed"), pet["carrying"])
    pet["carrying"] = ["petal", "pebble"]
    why = actions.check({"type": "machine_feed", "what": "bits", "for": "stone"}, h, cfg, pet, mem)
    assert why and "three" in why, "two bits are not enough: %s" % why
    pet["carrying"] = ["fluff", "pebble", "bell"]
    assert machine.offers(h, cfg, pet, sr, "bits") == ["fibre", "wood", "stone", "metal"]
    why, said = act({"type": "machine_feed", "what": "bits", "for": "metal"})
    assert not why and pet["carrying"] == ["metal"] and moments(h, "fed")[-1] == "Lean fed three bits to the machine for metal", "three bits in, one out: %s %s" % (why, pet["carrying"])

    # ---- what it never takes: an heirloom, a memorial stone, anything in a keepsake box, another living pet's thing without its leave ----
    other = world.new_pet(h, cfg, sr["id"], [6, 5], name="Sven")
    other["laid"] = -10 ** 6
    await eng.tick()
    go(sr)
    assert other["stage"] == "hatchling" and other["id"] in eng.minds
    thing(eng, sr, "keepsake", "charm", "hard", me)["made"]["heirloom"] = {"from": "p0", "to": [me], "tick": 0, "line": ["p0"]}
    sr["objects"]["stone for old"] = {"pos": [6, 6], "memorial": {"pet": "p0", "text": "Old lived here"}}
    h["pets"]["p0"] = {"id": "p0", "name": "Old", "stage": "dead", "died": 0, "buried": True, "room": sr["id"], "children": [], "parent": None, "gen": 0, "lineage": 1, "laid": 0, "family": 1}
    order.give_box(h, cfg, sr, "stone for old")
    thing(eng, sr, "old hat", "cushion", "soft", "p0", on="keepsake box for old")
    thing(eng, sr, "old shoe", "cushion", "soft", "p0")
    thing(eng, sr, "svens bell", "bell", "noisy", other["id"])
    for what, word in (("keepsake", "heirloom"), ("stone for old", "stone"), ("old hat", "keepsake box"), ("svens bell", "leave"), ("vending machine", "only takes"), ("no such thing", "not here")):
        why = actions.check({"type": "machine_feed", "what": what, "for": "fibre"}, h, cfg, pet, mem)
        assert why and word in why and what not in machine.feedable(h, cfg, pet, sr), "%s is refused: %s" % (what, why)
    assert set(machine.feedable(h, cfg, pet, sr)) == {"charm one", "bell one", "cushion one", "lamp one", "old shoe"}, "what it would take from this pet: its own, and what the dead left lying: %s" % sorted(machine.feedable(h, cfg, pet, sr))
    assert "svens bell" in machine.feedable(h, cfg, other, sr) and "bell one" not in machine.feedable(h, cfg, other, sr), "each its own"
    actions.offer(h, cfg, other, pet, {"kind": "give", "what": "svens bell", "bit": False})   # its owner holds it out: that is leave
    pet["carrying"] = []
    why, said = act({"type": "machine_feed", "what": "svens bell", "for": "metal"})
    assert not why and "svens bell" not in sr["objects"] and not pet["offers"] and any("fed your svens bell" in e for _, e in other["events"]), "with its owner's leave it is taken, and the owner is told: %s" % why
    for what in ("keepsake", "old hat", "stone for old", "keepsake box for old", "charm one", "bell one", "cushion one", "lamp one", "old shoe"):
        sr["objects"].pop(what)
    del h["pets"]["p0"]

    # ---- the visitor stocks it, up to its limit, from whichever room is on screen; whoever is in its room is told ----
    S["stock"].update(metal=3, clay=M["limit"])
    pet["inbox"], pet["news"] = [], []
    n = len(moments(h, "stocked"))
    assert actions.visit(h, cfg, {"type": "stock", "what": "metal", "n": 2, "room": nursery["id"]}) is None and S["stock"]["metal"] == 5
    assert pet["inbox"] == ["the visitor put metal in the machine"] and "visitor" in pet["news"] and moments(h, "stocked")[n:] == ["the visitor put metal in the machine"]
    assert actions.visit(h, cfg, {"type": "stock", "what": "clay"}) == "the machine holds all the clay it can" and S["stock"]["clay"] == M["limit"]
    assert actions.visit(h, cfg, {"type": "stock", "what": "petal"}) == "the machine does not hold that"
    assert actions.visit(h, cfg, {"type": "stock", "what": "metal", "n": 99}) is None and S["stock"]["metal"] == M["limit"], "never past its limit"
    S["stock"].update(wood=0, sand=4)
    assert actions.visit(h, cfg, {"type": "stock", "what": "all"}) is None and set(S["stock"].values()) == {M["limit"]} and actions.visit(h, cfg, {"type": "stock", "what": "all"}) == "the machine is full"
    assert machine.view(h, cfg) == {"stock": S["stock"], "limit": M["limit"], "materials": SIX, "room": sr["id"]}

    # ---- wants: the machine is where a base material is to be had when none lies about; a spare thing is wanted fed; little in its paws, it wants to look ----
    at(eng, 10, h["clock"]["day"] + 1)
    go(nursery)
    pet.update(wants=[], wanted={}, gathered={}, tried={}, rooms={nursery["id"]: 0, sr["id"]: 0, cellar["id"]: 0})
    for r in (nursery, sr, cellar):
        r["spots"] = [s for s in r["spots"] if s["bit"] not in SIX and not s["loose"]]
    cands = {c["key"]: c for c in wants.candidates(h, cfg, pet)}
    assert cands["bit:stone"]["room"] == sr["id"] and "the machine in the storeroom has some" in cands["bit:stone"]["text"], cands.get("bit:stone")
    assert cands["peek:%d" % h["clock"]["day"]]["room"] == sr["id"], "with little in its paws it wants to see what the machine has"
    pet.update(wants=[{"what": "tool", "key": "tool:hammer", "text": "", "done": "", "tool": "hammer", "since": h["tick"]}], takes=["hammer"], lacks={"hammer": h["tick"]}, tried={"stone|grind": "sharp stone"})
    cands = {c["key"]: c for c in wants.candidates(h, cfg, pet)}
    assert cands["get:wood"]["text"] == "you want some wood from the machine in the storeroom" and cands["get:wood"]["room"] == sr["id"], "a want that names a material leads to the machine: %s" % cands.get("get:wood")
    step = cands["get:stone|grind"]
    assert step["bit_room"] == sr["id"] and step["room"] == cellar["id"] and step["text"] == "you want to grind a stone, for the sharp stone", "and to what the material becomes: %s" % step
    get = dict(cands["get:wood"], since=h["tick"])
    get.pop("weight")
    pet["wants"].append(get)
    assert wants.possible(h, cfg, pet, get) and sr["id"] in wants.lean(h, cfg, pet)["rooms"], "its body makes for the machine's room"
    nursery["spots"].append({"bit": "wood", "pos": [3, 3], "ready": True, "back": None, "loose": False})
    nursery["spots"].append({"bit": "wood", "pos": [3, 4], "ready": True, "back": None, "loose": False})
    assert "the machine" not in {c["key"]: c for c in wants.candidates(h, cfg, pet)}["get:wood"]["text"] and wants.lean(h, cfg, pet)["gather"] == {"wood"}, "what lies about is picked up, not fetched from the machine"
    nursery["spots"] = [s for s in nursery["spots"] if s["bit"] != "wood"]
    S["stock"]["wood"] = 0
    assert "get:wood" not in {c["key"] for c in wants.candidates(h, cfg, pet)} and not wants.possible(h, cfg, pet, get), "an empty machine is no source"
    S["stock"]["wood"] = 5
    pet["machine"] = {"day": h["clock"]["day"], "took": M["free"]}
    assert "get:wood" not in {c["key"] for c in wants.candidates(h, cfg, pet)} and "peek:%d" % h["clock"]["day"] not in {c["key"] for c in wants.candidates(h, cfg, pet)}, "nor one that has given it its two"
    pet.update(machine={}, wants=[], lacks={})
    assert "feed" in wants.LEANS["orderly"] and {"peek", "feed"} <= set(wants.SERVED), "the orderly lean toward feeding it, and a body can serve both"
    thing(eng, nursery, "old charm", "charm", "bright", me, days=M["spare_days"] + 0.5)
    thing(eng, nursery, "new charm", "charm", "bright", me, days=0.2)
    thing(eng, nursery, "old heirloom", "charm", "bright", me, days=9)["made"]["heirloom"] = {"from": "p0", "to": [me], "tick": 0, "line": []}
    thing(eng, nursery, "its charm", "charm", "bright", other["id"], days=9)
    cands = {c["key"]: c for c in wants.candidates(h, cfg, pet)}
    assert [k for k in cands if k.startswith("feed:")] == ["feed:old charm"] and "nobody has touched your old charm" in cands["feed:old charm"]["text"], "a thing of its own nobody has touched in days: %s" % [k for k in cands if k.startswith("feed:")]
    for n in ("old charm", "old heirloom", "its charm"):
        nursery["objects"].pop(n)
    for i in range(M["spare_kind"] - 1):
        thing(eng, nursery, "nest %d" % i, "nest", "soft", other["id"], days=0.2)
    assert not [k for k in {c["key"] for c in wants.candidates(h, cfg, pet)} if k.startswith("feed:")], "a new thing is not spare"
    thing(eng, nursery, "third nest", "nest", "soft", me, days=0.5)
    cands = {c["key"]: c for c in wants.candidates(h, cfg, pet)}
    assert "feed:third nest" in cands and "more nests in the nursery than anyone needs" in cands["feed:third nest"]["text"], "a room's third nest: %s" % [k for k in cands if k.startswith("feed:")]
    for n in ("nest 0", "nest 1", "new charm"):
        nursery["objects"].pop(n)
    for i, b in enumerate(["pebble", "pebble", "wax"]):
        nursery["spots"].append({"bit": b, "pos": [2 + i, 6], "ready": True, "back": None, "loose": True, "since": h["tick"]})
    assert "feed:bits" in {c["key"] for c in wants.candidates(h, cfg, pet)}, "three loose bits lying about are wanted fed too"
    nursery["spots"] = [s for s in nursery["spots"] if not s["loose"]]

    # ---- a body does both by itself: it goes to the machine and takes what a want of its is about ... ----
    mind, A = eng.minds[me], cfg["activities"]
    go(sr)
    pet["wants"] = [{"what": "bit", "key": "bit:sand", "text": "", "done": "held sand for the first time", "bit": "sand", "room": sr["id"], "since": h["tick"]}]
    assert wants.lean(h, cfg, pet)["vend"] == ("sand", "bit:sand")
    t = body.targets(h, cfg, pet, mem, "take from the machine", A["take from the machine"])
    assert [x["what"] for x in t] == ["sand"] and t[0]["bonus"] > cfg["body"]["want"] and not body.targets(h, cfg, pet, mem, "look in the machine", A["look in the machine"])
    n, was = len(moments(h, "machine")), S["stock"]["sand"]
    for _ in range(200):
        await eng.tick()
        if "Lean took sand from the machine" in moments(h, "machine")[n:]:   # (the other one's body may well be at the machine too)
            break
    assert "Lean took sand from the machine" in moments(h, "machine")[n:] and "sand" in pet["carrying"] and S["stock"]["sand"] < was, "its body took what it wanted from the machine: %s" % moments(h, "machine")[n:]
    assert any(a["type"] == "machine_take" and a["what"] == "sand" and a["pet"] == me and a["ok"] for a in h["acts"]), "and the page is told, so the machine lights and the sand drops into its paws"
    # ... and carries a spare thing to it from the next room, and feeds it in
    go(nursery)
    pet.update(machine={})
    o = nursery["objects"]["third nest"]
    o["kept"] = LONG_AGO
    pet["wants"] = [{"what": "feed", "key": "feed:third nest", "text": "", "done": "fed the third nest to the machine", "thing": "third nest", "room": nursery["id"], "since": h["tick"]}]
    t = body.targets(h, cfg, pet, mem, "feed the machine", A["feed the machine"])
    assert [x["what"] for x in t] == ["third nest"] and t[0]["door"] in nursery["doors"] and t[0]["to"] == list(h["door_tiles"][t[0]["door"]]), "first to the door on the way: %s" % t
    n = len(moments(h, "fed"))
    for _ in range(400):
        await eng.tick()
        if "Lean fed a soft nest to the machine for fibre" in moments(h, "fed")[n:]:
            break
    assert "Lean fed a soft nest to the machine for fibre" in moments(h, "fed")[n:] and pet["room"] == sr["id"] and "fibre" in pet["carrying"], "its body carried it to the machine and fed it: %s in %s" % (moments(h, "fed")[n:], pet["room"])
    assert not any(n == "third nest" for r in h["rooms"].values() if r["type"] for n in r["objects"]) and any(a["type"] == "machine_feed" and a["what"] == "third nest" and a["to"] == "fibre" for a in h["acts"])
    for _ in range(12):
        await eng.tick()
    assert not any(w["what"] == "feed" and w.get("thing") == "third nest" for w in pet["wants"]) and any("fed the third nest" in m for m in moments(h, "want")), "and the want is met"
    # the scripted brain of the long runs can use both actions
    from .brains.stub import Stub
    go(sr)
    thing(eng, sr, "drum one", "drum", "noisy", me)
    pet.update(machine={}, carrying=[])
    from . import mind as minds
    packet, c = minds.perceive(h, cfg, pet, mem)
    assert set(machine.ACTIONS) <= set(c["allowed"]) and c["machine"] == machine.ctx(h, cfg, pet) and "drum one" in c["machine"]["feed"]
    line = next(l for l in packet.split("\n") if l.startswith("you notice"))
    assert "the machine here holds wood, stone, metal, clay, fibre and sand; it will give you two today" in line and len(machine.sense(h, cfg, pet)[0]) < 150, "a mind at the machine is told of it in a line: %s" % line
    stub = Stub(cfg)
    a, b = stub.step("machine_take", c, packet), stub.step("machine_feed", c, packet)
    assert not actions.check(a, h, cfg, pet, mem) and not actions.check(b, h, cfg, pet, mem), (a, b)
    from .brains import model
    said = json.dumps(model.schema(c)) + model.prompt(packet, c)
    assert all(x in model.WRITTEN and '"%s"' % x in said for x in machine.ACTIONS) and '"drum one"' in said, "and the model's reply is held to what the machine offers"
    go(nursery)
    assert minds.perceive(h, cfg, pet, mem)[1]["machine"] is None and "the machine" not in minds.perceive(h, cfg, pet, mem)[0].split("you can:")[0].split("you notice")[1].split("\n")[0], "away from it nothing is added to its packet"
    eng.close()

    # ---- an old saved house gains the machine on load, and loads without error: one whose storeroom was found before there was one ----
    old = json.loads((eng.path).read_text())
    rid = next(rid for rid, r in old["rooms"].items() if r["type"] == "storeroom")
    del old["rooms"][rid]["objects"]["vending machine"]
    del old["machine"]
    old["rooms"][rid]["objects"]["left here"] = {"pos": [7, 1], "made": dict(old["rooms"][rid]["objects"]["drum one"]["made"])}
    for p in old["pets"].values():
        p.pop("machine", None)
        p.pop("fed", None)
    eng.path.write_text(json.dumps(old))
    again = Engine(cfg, d + "/a", scripted)
    room = again.house["rooms"][rid]
    assert machine.spot(room) == "vending machine" and room["objects"]["vending machine"]["pos"] == [8, 0] and again.house["machine"]["stock"] == {m: M["start"] for m in SIX}, "the machine comes to a house already lived in"
    assert "left here" in room["objects"] and room["objects"]["left here"]["pos"] != room["objects"]["vending machine"]["pos"]
    for _ in range(30):
        await again.tick()
    assert machine.view(again.house, cfg)["room"] == rid
    again.close()
    # ... and one whose storeroom nobody has found yet: nothing to gain until it is, and then it is there
    fresh, _ = engine(cfg, d + "/b")
    assert machine.view(fresh.house, cfg) is None and machine.found(fresh.house) is None and actions.visit(fresh.house, cfg, {"type": "stock", "what": "wood"}) == "nobody has found the machine yet"
    director.begin(fresh.house, cfg)
    fresh.close()
    back = Engine(cfg, d + "/b", scripted)
    assert "machine" not in back.house or machine.found(back.house) is None
    assert machine.spot(generate_room(back.house, cfg, next(rid for rid, x in back.house["rooms"].items() if not x["type"]), "storeroom")) == "vending machine"
    back.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))
    print("machine check passed")


if __name__ == "__main__":
    main()
