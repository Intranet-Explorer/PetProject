"""Self-check for SPEC-v4.0 §8 (the brain), §9 (the body), §6.2 (housekeeping) and §11's trimmed firsts (helper D):
each kind of thought is asked when it should be and not otherwise; packets stay under the ceiling; replies validate
against their schemas; the budget's priority order; aims are worked on by the body; each trait's behaviours fire for
a hob at that pole and not at the other (§13.1); housekeeping falls in a stub run; the switches turn it all off.
    uv run python -m engine.check_brain4"""
import asyncio
import os
import tempfile

from . import body, brain4, character, feats, firsts, life, memories, opinions, planner, sleep, world
from .brains import model
from .check import at
from .tick import Engine, Mind, stub_brains
from .world import generate_room, new_pet

HOUSEKEEPING = {"tidy", "take out", "load the train", "feed the machine", "clear scrap", "put_away", "take_out", "machine_feed", "ask_train", "hang"}


def valid(schema, v, path="reply"):
    """A small JSON-schema check (the parts brains/model.py uses). Returns the first problem, or None."""
    if "anyOf" in schema:
        return None if any(valid(s, v, path) is None for s in schema["anyOf"]) else "%s matches none of its shapes: %r" % (path, v)
    if "const" in schema and v != schema["const"]:
        return "%s is not %r" % (path, schema["const"])
    if "enum" in schema and v not in schema["enum"]:
        return "%s: %r is not one of %s" % (path, v, schema["enum"][:8])
    t = schema.get("type")
    if t == "object":
        if not isinstance(v, dict):
            return "%s is not an object" % path
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in v:
                return "%s lacks %s" % (path, k)
        if schema.get("additionalProperties") is False and set(v) - set(props):
            return "%s has more than it may: %s" % (path, set(v) - set(props))
        return next((e for k, x in v.items() if k in props for e in [valid(props[k], x, path + "." + k)] if e), None)
    if t == "array":
        if not isinstance(v, list) or not schema.get("minItems", 0) <= len(v) <= schema.get("maxItems", 10 ** 6):
            return "%s is not a list of the right length: %r" % (path, v)
        return next((e for i, x in enumerate(v) for e in [valid(schema.get("items", {}), x, "%s[%d]" % (path, i))] if e), None)
    if t == "string" and not (isinstance(v, str) and schema.get("minLength", 0) <= len(v) <= schema.get("maxLength", 10 ** 6)):
        return "%s is not a string of the right length: %r" % (path, v)
    if t == "integer" and not (isinstance(v, int) and schema.get("minimum", -10 ** 9) <= v <= schema.get("maximum", 10 ** 9)):
        return "%s is not a whole number in range: %r" % (path, v)
    return None


def config(on=True):
    cfg = world.load_config()
    cfg["weather"]["real"] = False
    cfg["stub"]["enabled"] = True
    for part in ("traits", "needs4", "opinions", "talk", "ladder", "health", "brain4", "planner", "visitor4"):
        cfg[part]["on"] = on
    return cfg


def calm(h):
    return {"mood": "content", "since": h["tick"], "until": h["tick"] + 10 ** 6, "why": "", "strength": 0.0}


def grow(h, pet, stage):
    pet.update(stage=stage, laid=h["tick"] - 10 ** 5)
    for s in world.STAGES[1:world.STAGES.index(stage) + 1]:
        pet["stage_at"].setdefault(s, h["tick"] - 10 ** 4)


def hob(eng, room, pos, family=1, stage="adult", **temper):
    """A hatched hob of this stage, with these genes (0..1)."""
    h, cfg = eng.house, eng.cfg
    pet = new_pet(h, cfg, room["id"], list(pos), family=family)
    life.hatch(h, cfg, pet)
    grow(h, pet, stage)
    pet["temper"].update({g: 0.5 for g in pet["temper"]})
    pet["temper"].update(temper)
    pet["mood"] = calm(h)
    eng.minds[pet["id"]] = Mind(eng, pet)
    return pet


async def house(d, on=True):
    """A house with its founder grown, a workshop and a garden found."""
    cfg = config(on)
    eng = Engine(cfg, d, stub_brains)
    p0 = eng.new_lineage()
    p0["laid"] = -10 ** 6
    await eng.tick()
    h = eng.house
    grow(h, p0, "adult")
    p0.update(name="Oya", mood=calm(h))
    p0["temper"].update({g: 0.5 for g in p0["temper"]})
    for kind in ("workshop", "garden"):
        rid = next(r for r, x in sorted(h["rooms"].items()) if not x["type"] and r in h["rooms"][p0["room"]]["doors"].values())
        generate_room(h, cfg, rid, kind)
        p0["rooms"][rid] = h["tick"] - 10 ** 4
    at(eng, 10)
    return eng, p0


def thing(eng, room, name, owner, pos, kind="cup", material="hard"):
    from .check_machine import thing as made
    made(eng, room, name, kind, material, owner)
    room["objects"][name]["pos"] = list(pos)
    room["objects"][name].pop("on", None)
    return room["objects"][name]


async def thoughts(d):
    """§8.1: when each kind is asked; §8.2 the packets; the replies against their schemas; §8.3 the budget."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    room = h["rooms"][pet["room"]]
    kid = hob(eng, room, [3, 3])
    pet["last_call"] = h["tick"]
    # the morning plan, once a day on waking; nothing else starts a thought
    assert m.wants_thought() == "plan", "a hob that has not planned today plans"
    m.think("plan")
    await asyncio.sleep(0)
    await m.thought
    m.adopt()
    assert 2 <= len(pet["aims"]) <= 3 and all(a["kind"] in planner.KINDS for a in pet["aims"]), pet["aims"]
    assert pet["planned"] == h["clock"]["day"] and m.wants_thought() is None, "one plan a day"
    pet["news"] += ["phase", "bored", "need"]
    pet["ready"], pet["plan"] = h["tick"], None
    pet["carrying"] = ["clay", "wood"]
    body.state(pet)["laid"] = list(pet["carrying"])
    h["tick"] += 1
    assert m.wants_thought() is None, "'ready to make' and 'something changed' start no thought"
    assert pet["plan"] and pet["plan"]["steps"] and pet["plan"]["steps"][0]["type"] == "make" and pet["plan"]["why"] == "ready to make", \
        "the body makes what is laid out by itself: %s" % pet["plan"]
    # a reaction: an insult waits for the gap between reactions; a death does not wait
    brain4.notable(h, cfg, pet, "insulted", "the second one sneered at you", [kid["id"]])
    assert m.wants_thought() is None, "a reaction waits its turn"
    pet["last_call"] -= world.hours(cfg, cfg["brain4"]["react_gap_hours"])
    assert m.wants_thought() == "react", "and then it reacts"
    pet["last_call"] = h["tick"] - world.ticks(cfg, cfg["brain4"]["urgent_seconds"])
    brain4.notable(h, cfg, pet, "death", "the third one died", [kid["id"]])
    assert pet["notable"][0]["kind"] == "death" and m.wants_thought() == "react", "a death goes first, and waits for nothing"
    m.think("react")
    await m.thought
    m.adopt()
    assert character.mood(pet) == "sad", "a death leaves it sad (the stub's feeling): %s" % pet.get("mood")
    pet["reacts"] = [h["clock"]["day"], cfg["brain4"]["reacts_per_day"]]
    pet["last_call"] -= world.hours(cfg, 2)
    assert m.wants_thought() is None, "no more than so many reactions a day"
    pet["reacts"] = None
    # SPEC-v5.1 §4.5: no design thought, even at the bench with stuff to hand
    pet["last_call"], pet["notable"] = h["tick"] - world.hours(cfg, 2), []
    shop = next(r for r in h["rooms"].values() if r["type"] == "workshop")
    pet["room"], pet["pos"], pet["carrying"] = shop["id"], [2, 2], ["clay", "wood"]
    assert m.wants_thought() is None and "design" not in brain4.PRIORITY, "designing is gone"
    pet["room"] = room["id"]
    # the evening reflection is the night's one call
    calls = lambda: dict(eng.db.execute("SELECT kind, count(*) FROM calls GROUP BY 1").fetchall())
    before = calls()
    pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
    await sleep.night(m)
    after = calls()
    assert after.get("reflect", 0) == before.get("reflect", 0) + 1 and after.get("night", 0) == before.get("night", 0), (before, after)
    assert pet["last_night"]["dream"] and not pet["aims"], "a diary line; tomorrow's aims are the morning's"
    pet["sleep"] = None
    # §8.2 the packets, with a hob's head full: fifty memories, opinions of everyone, a long day
    for i in range(50):
        memories.add(h, cfg, pet, "a long memory number %d about the pond and the kiln and the many things that happened on that day" % i, 3, [kid["id"]])
    m.today = [[h["tick"], "[day, nursery] something happened that was long enough to count, number %d" % i, i % 7] for i in range(300)]
    sizes = {}
    for kind, (text, ctx) in {"plan": brain4.plan_packet(h, cfg, pet, m.mem), "react": brain4.react_packet(h, cfg, pet, m.mem, {"kind": "insulted", "text": "x", "about": [kid["id"]], "tick": h["tick"]}),
                              "reflect": brain4.reflect_packet(m)}.items():
        whole = model.prompt4(kind, text, ctx)
        sizes[kind] = (len(text), len(whole))
        assert len(whole) <= cfg["brain4"]["packet_chars"], "the %s packet and its reply's form stay under the ceiling: %d" % (kind, len(whole))
        reply = await m.brain.think4(kind, text, ctx)
        problem = valid(model.schema4(kind, ctx), reply)
        assert problem is None, "the stub's %s reply fits its schema: %s" % (kind, problem)
    # a reply that names what is not there is refused by its schema
    text, ctx = brain4.plan_packet(h, cfg, pet, m.mem)
    assert valid(model.schema4("plan", ctx), {"thought": "", "aims": [{"text": "x", "why": "y", "kind": "fly", "target": ""}] * 2, "seek": [], "avoid": [], "steps": []}), "a kind of aim nobody offered"
    # §8.3 the budget: deaths and hurts first, then the visitor, conversations, plans, reflections
    order, gate = [], asyncio.Event()

    async def hold():
        await gate.wait()

    def job(name):
        async def run():
            order.append(name)
        return run
    first = eng.sched.submit(-1, hold)
    futs = [eng.sched.submit(brain4.PRIORITY[k], job(k)) for k in ("reflect", "plan", "talk", "visitor", "react hurt", "react death")]
    gate.set()
    await asyncio.gather(first, *futs)
    assert order == ["react hurt", "react death", "visitor", "talk", "plan", "reflect"] or order == ["react death", "react hurt", "visitor", "talk", "plan", "reflect"], order
    # while the model is over its budget only a death, a hurt or the visitor is thought about, and a reflection is skipped
    real, eng.over_budget = eng.over_budget, lambda: True
    m.brain.instant = False
    try:
        pet["planned"], pet["notable"], pet["last_call"] = None, [], h["tick"] - world.hours(cfg, 3)
        assert m.wants_thought() is None, "no plan while the model is busy"
        brain4.notable(h, cfg, pet, "hurt", "you are badly hurt")
        assert m.wants_thought() == "react", "but a hurt is reacted to"
        n = calls().get("reflect", 0)
        pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
        await sleep.night(m)
        assert calls().get("reflect", 0) == n and pet["last_night"]["dream"], "a dropped reflection costs little"
        pet["sleep"] = None
    finally:
        eng.over_budget, m.brain.instant = real, True
    assert len(h.get("busy", [])) >= 4, "every call counts toward the guard on eggs"
    return sizes


async def aims(d):
    """§9: an aim is worked on by the body: it goes where the aim is and does it, and the aim is done."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    garden = next(r for r in h["rooms"].values() if r["type"] == "garden")
    friend = hob(eng, garden, [4, 4])
    friend["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": True}   # (it stays put, asleep, in the garden)
    pet["planned"], pet["notable"], pet["moment_seen"] = h["clock"]["day"], [], 10 ** 9
    pet["aims"] = [{"text": "be with the second one", "why": "", "kind": "be with", "target": friend["id"], "since": h["tick"], "done": False}]
    pet["last_call"] = h["tick"]
    A, t = cfg["activities"]["sit with kin"], {"who": friend["id"]}
    assert planner.adjust(h, cfg, pet, "sit with kin", A, t) > planner.adjust(h, cfg, pet, "sit on", cfg["activities"]["sit on"], {"what": "rug"}) + 2, "the aim's work outweighs sitting about"
    assert planner.toward(h, cfg, pet), "the way to the aim's room is known"
    friend["sleep"] = None
    for _ in range(world.hours(cfg, 3)):
        await eng.tick()
        friend["room"], friend["pos"], friend["sleep"] = garden["id"], [4, 4], None
        if pet["aims"][0].get("done"):
            break
    assert pet["room"] == garden["id"] and pet["aims"][0].get("done"), "it went to the garden and spent the while with it: %s %s" % (pet["room"], pet["aims"])


def scene(eng, pet, room, what):
    """The moment that calls for a behaviour; returns (who else is in it, what is there)."""
    h, cfg = eng.house, eng.cfg
    pet.update(room=room["id"], pos=[5, 4], carrying=[], stash=0, glow=None, b4={}, mood=calm(h))
    pet["needs"].update(hunger=80.0, energy=80.0, comfort=80.0)
    pet["times"] = {}
    others = []
    bowl = next(n for n, o in room["objects"].items() if "meal" in o.get("fix", {}))
    room["objects"][bowl]["servings"] = 2
    mk = lambda name, owner, pos: thing(eng, room, name, owner, pos)
    if what == "b:hide":
        o = hob(eng, room, [7, 6], family=2)
        o["rooms"][room["id"]] = h["tick"]
        others.append(o)
    elif what in ("b:new", "b:poke", "b:pocket"):
        o = hob(eng, h["rooms"][next(iter(room["doors"].values()))], [3, 3], family=1)
        mk("cup of %s" % what, o["id"], [8, 2])
    elif what == "b:leave":
        pet["carrying"] = ["feather"]
    elif what in ("b:share", "b:wait", "b:push", "b:lecture", "b:pat"):
        o = hob(eng, room, [8, 6], stage="child" if what in ("b:lecture", "b:pat") else "adult")
        o["needs"]["hunger"] = 5.0
        o["needs"]["comfort"] = 5.0
        others.append(o)
        if what in ("b:wait", "b:push"):
            pet["needs"]["hunger"] = 30.0
            body.state(o)["now"] = {"do": "eat", "name": "eat", "what": bowl, "began": h["tick"]}
        if what == "b:lecture":
            body.state(o)["now"] = {"do": "play", "name": "play", "what": "ball", "began": h["tick"]}
    elif what == "b:serving":
        pet["needs"]["hunger"] = 30.0
    elif what == "b:stash":
        pass
    elif what == "b:known":
        pet["times"]["use " + bowl] = 9
    elif what in ("b:follow", "b:sneer"):
        o = hob(eng, room, [10, 6])
        pet["opinions"] = {o["id"]: dict(opinions.of(pet, o["id"]), liking=6 if what == "b:follow" else -6)}
        others.append(o)
    elif what == "b:alone":
        others += [hob(eng, room, [2, 6]), hob(eng, room, [3, 6])]
        pet["rooms"][room["id"]] = h["tick"] - 10 ** 4
        for rid in room["doors"].values():
            generate_room(h, cfg, rid)
            pet["rooms"][rid] = h["tick"] - 10 ** 4
    elif what == "b:return":
        o = hob(eng, room, [3, 3])
        mk("cup of b:return", o["id"], [8, 2])["pocketed"] = {"by": o["id"], "tick": h["tick"], "from": [8, 3]}
        o["sleep"] = {"since": h["tick"], "day": 1, "done": True}
    elif what == "b:prank":
        o = hob(eng, room, [9, 5])
        o["sleep"] = {"since": h["tick"], "day": 1, "done": True}
        others.append(o)
    elif what == "b:strut":
        pet["glow"] = {"size": 3, "why": "you made the first kiln in the house", "since": h["tick"], "until": h["tick"] + 1000}
    elif what == "b:sunbeam":
        h["clock"]["phase"], h["weather"] = "day", "clear"
    return others


async def poles(d):
    """§13.1: each pole's behaviours fire for a hob at that pole and not for one at the other; what each does."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    room = h["rooms"][pet["room"]]
    near = lambda pos: None
    fired = {}
    for name, A in cfg["activities"].items():
        if not A.get("behaviour") or not A.get("pole"):
            continue
        (axis, sign), = A["pole"].items()
        gene = character.GENE.get(axis, axis)
        got = {}
        for pole in (sign, -sign):
            for p in [p for p in list(h["pets"].values()) if p is not pet and p["stage"] != "dead"]:
                p["room"] = "nowhere"   # (each scene starts with the room to itself)
            others = scene(eng, pet, room, A["do"])
            pet["temper"][gene] = 0.95 if pole > 0 else 0.05
            got[pole] = body.targets(h, cfg, pet, m.mem, name, A)
            if pole == sign and got[pole]:
                now = dict(got[pole][0], name=name, do=A["do"], since=h["tick"], began=h["tick"])
                told, done = planner.finish(m, now, A)
                assert done, "%s is done when its moment is there: %s" % (name, now)
            pet["temper"][gene] = 0.5
            for o in others:
                o["room"] = "nowhere"
        assert got[sign] and not got[-sign], "%s (%s %s) fires at its pole and not at the other: %s / %s" % (name, axis, "+" if sign > 0 else "-", got[sign], got[-sign])
        fired[name] = "%s%s" % (axis, "+" if sign > 0 else "-")
    # tidy +: others' things put away (with a grumble); in the middle, only its own; messy, nothing
    for p in [p for p in h["pets"].values() if p is not pet]:
        p["room"] = "nowhere"
    owner = hob(eng, room, [2, 2])
    owner["temper"]["orderly"] = 0.05
    pet.update(room=room["id"], pos=[5, 4])
    room["spots"] = [sp for sp in room["spots"] if not sp["loose"]]
    for n in [n for n, o in room["objects"].items() if "made" in o]:
        del room["objects"][n]
    thing(eng, room, "dropped cup", owner["id"], [6, 6])
    T = cfg["activities"]["tidy"]
    who = lambda g: (pet["temper"].update(orderly=g), [t["what"] for t in body.targets(h, cfg, pet, m.mem, "tidy", T)])[1]
    assert "dropped cup" in who(0.95) and "dropped cup" not in who(0.5) and not who(0.05), "only a tidy hob puts others' things away"
    pet["temper"]["orderly"] = 0.95
    planner.tidied(h, cfg, pet, room, "dropped cup")
    assert any(mo["kind"] == "scold" for mo in h["moments"][-3:]), "and scolds the messy owner"
    pet["temper"]["orderly"] = 0.5
    return fired


async def stub_day(d, on):
    """Half a world day of five grown hobs in a cluttered house, by the stub brains: the share of waking time spent on housekeeping."""
    eng, pet = await house(d, on=on)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][pet["room"]]
    for i, g in enumerate((0.2, 0.5, 0.5, 0.8)):
        hob(eng, room, [2 + 2 * i, 5], orderly=g, curious=0.6)
    for i in range(10):
        thing(eng, room, "thing %d" % i, list(h["pets"])[i % 4], [1 + i, 2 if i % 2 else 7])
    for _ in range(cfg["ticks_per_day"] // 2):
        await eng.tick()
    rows = eng.db.execute("SELECT what, sum(tick_to - tick_from) FROM doing WHERE what != 'asleep' GROUP BY 1").fetchall()
    awake = sum(n for _, n in rows) or 1
    calls = dict(eng.db.execute("SELECT kind, count(*) FROM calls GROUP BY 1").fetchall())
    behaviours = sum(n for w, n in rows if cfg["activities"].get(w, {}).get("behaviour"))
    return 100.0 * sum(n for w, n in rows if w in HOUSEKEEPING) / awake, calls, behaviours


async def talk_aims(d):
    """19 October 2026 (a night of v4.0 on live: 4,802 ticks failed on an aim of kind "plan", 2,279 on the loom): every kind
    of aim talk gives a hob is worked on and judged without error, and every machine's process has a place to carry to."""
    from . import body, machines
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    other = next((p for p in h["pets"].values() if p is not pet and p["stage"] not in ("egg", "dead")), pet)
    for kind, target in (("plan", other["id"]), ("give", other["id"]), ("help", other["id"]), ("gather", pet["room"]), ("something new", None)):
        pet["aims"] = [{"text": "a talk's aim", "why": "we talked", "kind": kind, "target": target, "since": h["tick"], "done": None}]
        planner.check(h, cfg, pet)
        planner.adjust(h, cfg, pet, "sit with kin", cfg["activities"]["sit with kin"], {"who": other["id"]})
    pet["aims"] = [{"text": "go to the gathering", "why": "x", "kind": "gather", "target": pet["room"], "since": h["tick"], "done": None}]
    planner.check(h, cfg, pet)
    assert pet["aims"][0].get("done"), "a gathering's aim is met by being in its room"
    assert machines.processes(cfg) <= set(body.TO), "every machine's process has a place a bit is carried to"


async def firsts_trim(d):
    """§11: only the firsts that matter go on the board (and the page's banner reads `matters`)."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    seen = len(h["moments"])
    firsts.first(h, cfg, pet, ["read:moss"])   # a first in the house, but nothing that matters: felt, not told (18 October 2026)
    assert not h.get("feats", {}).get("list") and len(h["moments"]) == seen, "a first that does not matter makes no feat and no moment"
    firsts.first(h, cfg, pet, ["kind:kiln"])
    f = h["feats"]["list"][-1]
    assert f["board"] and f["matters"] and h["moments"][-1]["matters"] is True, f
    feats.record(h, cfg, "first", pet["id"], "the first dish", board="THE FIRST DISH")
    assert h["feats"]["list"][-1]["board"] and h["moments"][-1]["matters"], "a dish, a machine, a design matter where they are recorded"
    assert "matters" not in eng.db.execute("SELECT * FROM moments LIMIT 1").description, "(the log's moments keep their columns)"
    cfg["brain4"]["on"] = False
    firsts.first(h, cfg, pet, ["read:fern"])
    f = h["feats"]["list"][-1]
    assert f["board"] and "matters" not in f and "matters" not in h["moments"][-1], "off: every first in the house goes on the board, as in v3.6c"


async def off(d):
    """The switches: [brain4] off is v3.6c's per-action thought; [planner] off is v3.6c's body."""
    eng, pet = await house(d, on=True)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    cfg["brain4"]["on"] = False
    pet["last_call"], pet["news"] = h["tick"] - 10 ** 4, ["phase"]
    assert m.wants_thought() == "something changed", "brain4 off: the old reasons to think"
    m.think("something changed")
    await m.thought
    m.adopt()
    assert eng.db.execute("SELECT count(*) FROM calls WHERE kind='act'").fetchone()[0] == 1 and not pet.get("aims"), "and the old act"
    cfg["planner"]["on"] = False
    calls = []
    real = planner.adjust
    planner.adjust = lambda *a: calls.append(a) or 0.0
    try:
        for _ in range(200):
            await eng.tick()
            now = body.state(pet)["now"] or {}
            assert not cfg["activities"].get(now.get("name"), {}).get("behaviour"), "planner off: no behaviour"
    finally:
        planner.adjust = real
    assert not calls, "planner off: the score is v3.6c's"
    assert body.planner_ok(cfg, "load the train", cfg["activities"]["load the train"]), "planner off: the house's chores are the hobs' again"
    T = cfg["activities"]["tidy"]
    other = hob(eng, h["rooms"][pet["room"]], [2, 2])
    thing(eng, h["rooms"][pet["room"]], "their cup", other["id"], [6, 6])
    pet["temper"]["orderly"] = 0.05
    assert any(t["what"] == "their cup" for t in body.targets(h, cfg, pet, m.mem, "tidy", T)), "planner off: anyone tidies anyone's things"


# ---- SPEC-v4.0.5 §4 (19 October 2026): the brain and the body, fixed ----

async def aim_clock(d):
    """§4.1: an aim's clock starts when it becomes current and runs only in the hours for aims and free time."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    pet["aims"] = [brain4.aim_of(h, {}, {"text": "catch a fish, the %s" % n, "kind": "fish", "target": ""}) for n in ("first", "second", "third")]
    assert all(a["since"] is None for a in pet["aims"]), "no clock runs at the plan"
    walk = lambda lo, hi: [(at(eng, lo + i / 10), planner.check(h, cfg, pet)) for i in range(round((hi - lo) * 10) + 1)]
    walk(8, 12.5)
    first, second, third = pet["aims"]
    assert not any(a.get("failed") for a in pet["aims"]) and first["since"] is not None and second["since"] is None and third["since"] is None, pet["aims"]
    walk(12.5, 14.9)
    assert not first.get("failed"), "lunch is not aim time: 5.9 hours of it by 14:54"
    walk(14.9, 15.2)
    assert first.get("failed") and not second.get("failed") and second["since"] is not None and third["since"] is None, pet["aims"]


async def lost_plan(d):
    """§4.2: a plan whose reply is lost is asked again after the gap, three times a day at most; a lost reaction, and
    one in flight at a restart, is asked again."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    gap = world.hours(cfg, cfg["brain4"]["react_gap_hours"])
    asked = []

    async def lost(kind, text, ctx):
        asked.append(kind)
        return None
    m.brain.think4 = lost
    pet["notable"] = []
    for n in range(3):
        assert m.wants_thought() == "plan", "plan, try %d" % (n + 1)
        m.think("plan")
        await asyncio.sleep(0)
        await m.thought
        m.adopt()
        assert pet.get("planned") != h["clock"]["day"] and m.wants_thought() is None, "not planned, and not asked again at once"
        pet["last_call"] -= gap
    assert m.wants_thought() != "plan" and asked == ["plan"] * 3, "three lost plans: no more today: %s" % asked
    # a reaction: its event is asked about again
    brain4.notable(h, cfg, pet, "insulted", "the second one sneered at you")
    m.think("react")
    await m.thought
    m.adopt()
    assert pet["notable"] and pet["notable"][0]["text"] == "the second one sneered at you", pet.get("notable")
    # a reaction in flight at a restart
    m.think("react")
    assert pet["thinking"] == "react" and not pet["notable"]
    Mind(eng, pet)
    assert pet["notable"] and pet["notable"][0]["text"] == "the second one sneered at you" and not pet["thinking"], pet.get("notable")


async def spoken(d):
    """§4.3: what is said to a hob reaches its reaction, not what it said itself."""
    from . import actions
    eng, a = await house(d)
    h, cfg = eng.house, eng.cfg
    b = hob(eng, h["rooms"][a["room"]], [a["pos"][0] + 1, a["pos"][1]])
    b["name"], mb = "Bo", eng.minds[b["id"]]
    told = actions.speak(h, cfg, b, {"text": "My paws are cold", "to": actions.handle(h, b, a)}, mb.mem)[0]
    world.add_event(h, b, told)   # (its own "you said to Oya", as tick.Mind.finish_step tells it)
    b["news"], b["notable"] = [], []
    brain4.scan(h, cfg, b)
    actions.speak(h, cfg, a, {"text": "The kiln is warm today", "to": actions.handle(h, a, b)}, eng.minds[a["id"]].mem)
    brain4.scan(h, cfg, b)
    e = next(e for e in b["notable"] if e["kind"] == "spoken")
    text, _ = brain4.react_packet(h, cfg, b, mb.mem, e)
    assert "The kiln is warm today" in text and "My paws are cold" not in text, text
    brain4.vigil(b)
    assert not b["notable"], "the night lets go of what it did not react to"


async def laid_bits(d):
    """§4.4: bits laid out that come to nothing are put down; the hob is not left standing by them."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    pet.update(planned=h["clock"]["day"], aims=[], notable=[], carrying=["clay", "wood"], ready=h["tick"])
    body.state(pet)["laid"] = list(pet["carrying"])
    cfg["make"]["same"] = 0   # (every making is refused: "you have made ... not another yet")
    for _ in range(world.hours(cfg, 1)):
        await eng.tick()
        if not pet["carrying"] and body.anchor(h, pet) is None:
            break
    assert not pet["carrying"] and body.anchor(h, pet) is None and not body.state(pet).get("laid"), (pet["carrying"], body.state(pet).get("laid"))


async def learn_day(d):
    """§4.5: a "learn" aim is done by a close look at a thing with a title."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][pet["room"]]
    thing(eng, room, "the tale of the pond", pet["id"], [9, 6])["made"]["recipe"]["title"] = "The Tale of the Pond"
    assert "learn" in planner.feasible(h, cfg, pet)
    pet.update(planned=h["clock"]["day"], notable=[], aims=[brain4.aim_of(h, {}, {"text": "learn what the tale says", "kind": "learn", "target": ""})])
    for _ in range(world.hours(cfg, 4)):
        await eng.tick()
        if pet["aims"][0].get("done"):
            break
    assert pet["aims"][0].get("done"), (pet["aims"], pet.get("did4", [])[-5:])


async def reflect_day(d):
    """§4.6: the evening reflection sees the day: the talks and the body's activities, at most 40 lines."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][pet["room"]]
    for i in range(2):
        hob(eng, room, [3 + 3 * i, 6])
    for _ in range(cfg["ticks_per_day"] // 3):
        await eng.tick()
    talked = next((m for m in reversed(h["moments"]) if m["kind"] == "talk"), None)
    assert talked, "a talk in a third of a stub day"
    m = eng.minds[talked["pets"][0]]
    text, _ = brain4.reflect_packet(m)
    did = {A["did"].split("{")[0].strip() for A in cfg["activities"].values() if A.get("did")} - {""}
    assert "talked:" in text and any(x in text for x in did), text
    assert len(m.today) <= 40, len(m.today)


async def beliefs(d):
    """§4.7: a hob full of beliefs lets the longest unused go for what it learned today; §4.8 a packet is cut at a line's end."""
    eng, pet = await house(d)
    h, m = eng.house, eng.minds[pet["id"]]
    for i in range(m.mem.max):
        m.mem.write("belief number %d about the kiln and the pond" % i, h["tick"] + i)
    first = m.mem.active()[0]["id"]
    pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
    await brain4.reflect(m)
    held = m.mem.active()
    assert len(held) == m.mem.max and first not in [b["id"] for b in held] and len(m.mem.beliefs) == m.mem.max + 1, [b["statement"] for b in held]
    assert any(r.get("type") == "belief retired" and r["belief"] == first for r in m.journal), "said in its journal"
    assert brain4.fit(["one two three", "four five six"], 20, []) == "one two three\n", "cut at a line's end"


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:   # (anywhere: PET_SCRATCH when set, else the system's)
        sizes = asyncio.run(thoughts(d + "/t"))
        asyncio.run(aims(d + "/a"))
        fired = asyncio.run(poles(d + "/p"))
        asyncio.run(firsts_trim(d + "/f"))
        asyncio.run(talk_aims(d + "/t"))
        asyncio.run(off(d + "/o"))
        for n, check in enumerate((aim_clock, lost_plan, spoken, laid_bits, learn_day, reflect_day, beliefs)):   # SPEC-v4.0.5 §4
            asyncio.run(check(d + "/v%d" % n))
        was, c_off, _ = asyncio.run(stub_day(d + "/s0", False))
        now, c_on, b = asyncio.run(stub_day(d + "/s1", True))
    assert now < was, "housekeeping falls: %.1f%% -> %.1f%%" % (was, now)
    assert not c_on.get("act") and not c_off.get("plan") and b, (c_off, c_on, b)
    print("packets (packet, with its reply's form) in chars:", sizes)
    print("behaviours at their poles:", fired)
    print("half a stub day: housekeeping %.1f%% -> %.1f%%; calls %s -> %s" % (was, now, c_off, c_on))
    print("brain4 check passed")


if __name__ == "__main__":
    main()
