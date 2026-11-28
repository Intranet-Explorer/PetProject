"""Self-check for SPEC-v4.2 §8 (the director), §9 (the visitor as a character) and §10.3 (tales), helper D, with stub
minds in a temporary house: the director never picks two hard happenings in a row and never a hard one under the floor,
and a name it was not offered is nothing; every happening on the menu lands (a moment, a memory for everyone awake,
today's record) and kills nobody; a stub day asks the narrator once at midnight, foreshadows at dusk and lands at
dawn; absence is noticed at two world days by the hobs whose theory has him in it, the director may choose "gone" at
four, and his return is a moment; a note on a wall reaches the hob it names (and an aim of it), and the director's
letter brings an unread one; the visitor's tend moves a sickness back a stage after his hour, a remedy two; a theory
starts from kin's and moves with what he does; at a death the last words are spoken and a tale written, and an elder
tells it to a little one of another family in the evening, with its hook believed; and [stage], [visitor5] and
[memory2] off each leave their data unchanged across a stub day.

    uv run python -m engine.check_stage"""
import asyncio
import os
import tempfile

from . import tick as _engine   # noqa: F401 (the engine first)
from . import body, contracts as K, director, health, planner, stage, story, visitor, walls, world
from .check_brain4 import config as config4
from .check_lives import hob, house, place, room, to
from .check_machine import thing
from .check_talk import settle

MINE = ("stage", "visitor5", "memory2")


def config(off=()):
    cfg = config4(True)
    cfg["spirit"]["on"] = True
    for part in K.PARTS:
        cfg[part]["on"] = part not in ("drives", "talk2") + tuple(off)   # (C's parts have their own checks)
    cfg["clock"]["day_seconds"] = 1800
    return world.derive(cfg)


async def rules(d):
    """§8.3: what is offered, and what a reply may make of it."""
    cfg = config()
    eng, p0 = await house(d, cfg)
    h = eng.house
    for n in ("Ada", "Bo", "Cy", "Di"):
        hob(eng, n)
    day = h["clock"]["day"] + 1
    assert set(stage.offered(h, cfg, day)) >= {"nothing", "storm", "leak", "power_cut"}
    h["happenings"] = [K.happening({"name": "storm", "day": day - 1})]
    got = stage.offered(h, cfg, day)
    assert not any(K.HAPPENINGS[n] for n in got) and "dream" in got, "never two hard happenings in a row: %s" % got
    hap = stage.take(h, cfg, {"name": "leak", "target": "Ada", "why": "x"}, got, day)
    assert hap["name"] == "nothing" and h["coming"] == [hap], "a name it was not offered is nothing"
    h["happenings"] = []
    hap = stage.take(h, cfg, {"name": "storm", "target": "Ada", "why": "the wind had words for Ada"}, stage.offered(h, cfg, day), day)
    assert hap["name"] == "storm" and hap["target"] == next(p["id"] for p in h["pets"].values() if p.get("name") == "Ada") and K.since(h, "happening", 0)
    assert "storm" not in stage.offered(h, cfg, day + 1), "a cooldown, and a hard one just had"
    for p in [p for p in h["pets"].values() if p["stage"] != "egg"][3:]:
        p["stage"] = "dead"
    assert world.alive(h) and stage.life.floor(h, cfg)
    h["happenings"] = []
    assert not any(K.HAPPENINGS[n] for n in stage.offered(h, cfg, day)), "nothing hard while the house is under the floor"
    text, ctx = stage.packet(h, cfg, stage.offered(h, cfg, day))
    assert not any(ch.isdigit() for ch in text), "the narrator is told no numbers"
    await settle(eng)

    # the stub narrator, night after night: never two hard ones in a row, and never one under the floor
    eng, p0 = await house(d + "/n", cfg)
    h = eng.house
    for n in ("Ada", "Bo", "Cy", "Di"):
        hob(eng, n)
    seq = []
    for day in range(2, 40):
        to(eng, day, 24.5)
        if day == 30:
            for p in [p for p in h["pets"].values() if p["stage"] not in ("egg", "dead")][3:]:
                p["stage"] = "dead"   # (under the floor from here on)
        hap = await stage.choose(eng)
        seq.append(hap)
        to(eng, day + 1, 9)
        stage.land(h, cfg, h["coming"].pop())
    names = [x["name"] for x in seq]
    assert all(not (a["hard"] and b["hard"]) for a, b in zip(seq, seq[1:])), names
    assert not any(x["hard"] for x in seq[28:]), "under the floor: %s" % names[28:]
    assert names.count("nothing") >= len(names) // 3 and len(set(names)) >= 5, names
    assert all(p["stage"] != "dead" for p in h["pets"].values() if p.get("name") in ("Oya", "Ada", "Bo")), "nothing killed"
    print("stage: never two hard happenings in a row, none under the floor; most nights nothing (%d of %d)" % (names.count("nothing"), len(names)))
    await settle(eng)


async def lands(d):
    """Every happening on the menu lands, and is recorded (§8.4)."""
    cfg = config()
    eng, p0 = await house(d, cfg, ("pond", "attic", "garden", "storeroom"))
    h = eng.house
    ada, bo = hob(eng, "Ada"), hob(eng, "Bo")
    nursery = room(eng, "nursery")
    place(eng, [p0, ada, bo], nursery)
    to(eng, 3, 9)
    store = room(eng, "storeroom")
    food = cfg["seasons"]["food"]["bits"][0]
    seen = {}
    for name in K.HAPPENINGS:
        if name == "nothing":
            continue
        thing(eng, nursery, "ada's cup %s" % name, "cup", "hard", ada["id"])
        store["spots"].append({"bit": food, "pos": [3, 3], "ready": True, "loose": True, "back": None, "on": "a plank shelf"})
        if name == "letter":
            walls.visitor(h, cfg, room(eng, "attic"), "Bo, the clay is in the storeroom", "north wall")
        if name == "power_cut":
            h["power_out_until"] = 0   # (the storm may have taken it already)
        n0, mems = len(h["moments"]), len(ada.get("memories", []))
        line = stage.land(h, cfg, K.happening({"name": name, "target": ada["id"], "why": "the narrator's line", "day": h["clock"]["day"]}))
        assert line and h["happening"]["name"] == name and stage.today(h)["name"] == name, (name, line)
        assert any(m["kind"] == "happening" and "the narrator's line" in m["text"] for m in h["moments"][n0:]), name
        assert any(m["kind"] == "happening" and m["text"] == line and m["weight"] == 3 for m in bo["memories"]), "a memory for everyone awake"
        seen[name] = line
    assert ("worst of it" in seen["storm"] or "soaked through" in seen["storm"]) and h["weather"] == "heat", seen["storm"]
    assert any(s.get("spoiled") for s in store["spots"]) and h.get("cold_snap", 0) > h["tick"] and h["power_out_until"] > h["tick"]
    assert "went missing" in seen["missing"] and sum(n.startswith("ada's cup") for n in nursery["objects"]) == len(seen) - 1, "a thing went missing"
    assert any(p.get("founder") and p["stage"] == "egg" for p in h["pets"].values()), "a stranger's egg"
    assert any("in a dream" in b["text"] for p in (ada, p0, bo) for b in p.get("beliefs_due", [])), "a dream leaves a belief to take up"
    assert any(c.get("trust", {}).get(ada["id"]) for c in h["creatures"]), "a creature took to Ada"
    assert "letter" in seen and any("in a letter that came by the train" in e[1] for e in bo["events"]), "the letter came"
    assert "he has gone" in ada["visitor_theory"] or "he has gone" in bo["visitor_theory"]
    assert all(p["stage"] != "dead" for p in (p0, ada, bo)), "a happening kills nobody"
    assert set(seen) == set(K.HAPPENINGS) - {"nothing"} == set(stage.EFFECTS) - {"nothing"}
    print("stage: every happening lands: a moment, a memory for everyone awake, today's record")
    await settle(eng)


async def a_day(d):
    """A stub day: asked once at midnight, foreshadowed at dusk if it has an omen, landed at dawn."""
    cfg = config()
    cfg["stage"]["quiet"] = 0.0   # (the stub always chooses something)
    eng, p0 = await house(d, cfg)
    h = eng.house
    for n in ("Ada", "Bo", "Cy"):
        hob(eng, n)
    for _ in range(round(cfg["ticks_per_day"] * 1.1)):
        await eng.tick()
    assert h["director"]["asked"] == 2 and [x["day"] for x in h["coming"]] == [3] and K.since(h, "happening", 0), h.get("director")
    assert eng.db.execute("SELECT count(*) FROM calls WHERE kind='director'").fetchone()[0] == 1, "one call a day"
    nxt = h["coming"][0]
    stage.MENU[nxt["name"]]["omen"] = stage.MENU[nxt["name"]]["omen"] or "something is coming"
    while h["clock"]["phase"] != "day" or h["clock"]["day"] < 3:
        await eng.tick()
    assert h["director"]["omen"] == 3 and any(m["kind"] == "omen" for m in h["moments"]), "foreshadowed at dusk"
    assert 3 not in [x["day"] for x in h["coming"]] and h["happening"]["day"] == 3, "landed at dawn"
    assert not [k for k in eng.step_errors if k.startswith("stage")], eng.step_errors
    print("stage: a stub day asks once at midnight, foreshadows at dusk, lands at dawn (%s)" % h["happening"]["name"])
    await settle(eng)


async def visitor5(d):
    """§9: theory, absence, notes, tend and remedy."""
    cfg = config()
    eng, p0 = await house(d, cfg, ("pond", "attic", "garden"))
    h, use = eng.house, lambda tool, **b: visitor.use(eng, tool, b)
    ada, bo, kid = hob(eng, "Ada", parent=p0), hob(eng, "Bo"), hob(eng, "Kit", "child")
    nursery = room(eng, "nursery")
    place(eng, [p0, ada, bo, kid], nursery)
    p0["visitor_theory"] = "the visitor made the house"
    bo["visitor_theory"] = "there is no visitor, things just come"
    to(eng, 2, 10)
    h["tick"] -= h["tick"] % 10
    visitor.tick(eng)
    assert ada["visitor_theory"] == "the visitor made the house" and kid["visitor_theory"], "a theory starts from kin's"
    assert visitor.question(ada) == "Is it you who made the house?" and visitor.question(bo) == "Is anyone there?", visitor.question(ada)
    assert visitor.question({"visitor_theory": "the visitor is the one who feeds us"}) == "Are you the one who feeds us?"

    # ---- absence: two days, a notable for those whose theory has him in it; four, the director may say he has gone ----
    to(eng, 4, 11)
    h["tick"] -= h["tick"] % 10
    visitor.tick(eng)
    told = lambda p: any(e["kind"] == "visitor" and "not been felt" in e["text"] for e in p.get("notable", []))
    assert told(ada) and not told(bo), "absence noticed by those whose theory has him in it"
    assert "he has not come for days" in ada["visitor_theory"] and h["visitor"]["away"]["noted"]
    assert "visitor_gone" not in stage.offered(h, cfg, h["clock"]["day"] + 1)
    to(eng, 6, 12)
    assert "visitor_gone" in stage.offered(h, cfg, h["clock"]["day"] + 1), "four days: the director may choose it"
    assert use("praise", pet=ada["id"], about="the cup")[0] and "he was pleased with me" in ada["visitor_theory"], "what he does moves the theory"
    h["tick"] += 10 - h["tick"] % 10
    visitor.tick(eng)
    assert any(m["kind"] == "visitor back" for m in h["moments"]) and not h["visitor"]["away"]["noted"], "his return is a moment"

    # ---- notes: to the hob it names (and an aim of it); to the house, read by whoever is there ----
    walls.visitor(h, cfg, nursery, "Ada, look in the attic", "north wall")
    walls.visitor(h, cfg, nursery, "the pond is cold at night", "south wall")
    h["tick"] += 10
    visitor.tick(eng)
    assert any('the visitor wrote to you on the north wall: "Ada, look in the attic"' in e[1] for e in ada["events"])
    assert not any("look in the attic" in e[1] for e in bo["events"]) and any("the pond is cold" in e[1] for e in bo["events"]), "a note to Ada is Ada's"
    assert any(a.get("from") == "note" and a["target"] == room(eng, "attic")["id"] for a in ada.get("aims_next", [])), ada.get("aims_next")
    far = room(eng, "pond")
    walls.visitor(h, cfg, far, "Bo: the fish are biting", "north wall")
    assert visitor.unread(h) and "letter" in stage.makings(h, cfg) and stage.makings(h, cfg)["letter"]
    assert visitor.deliver(h, cfg, bo["id"]) and not visitor.unread(h) and any("came by the train" in e[1] for e in bo["events"])

    # ---- tend: a world hour beside it, then a stage back; a remedy two ----
    assert not use("tend", pet=ada["id"])[0], "nobody to tend"
    health.sicken(h, cfg, ada, "a check", level="ill")
    ok, said = use("tend", pet=ada["id"])
    assert ok and ada["id"] in h["visitor"]["tend"] and not use("tend", pet=ada["id"])[0], said
    h["tick"] += 10 - h["tick"] % 10
    visitor.tick(eng)
    assert health.stage_of(ada) == "ill", "not before his hour is up"
    h["tick"] += round(cfg["ticks_per_hour"]) + 10 - (h["tick"] + round(cfg["ticks_per_hour"])) % 10
    visitor.tick(eng)
    assert health.stage_of(ada) == "unwell" and ada["id"] not in h["visitor"]["tend"], health.stage_of(ada)
    assert any(r["by"] == "visitor" and r["pet"] == ada["id"] for r in K.since(h, "nursed", 0)) and "sat with me" in ada["visitor_theory"]
    assert any("visitor" in m.get("about", []) and "looked after me" in m["text"] for m in ada["memories"]), "nursed_me toward the visitor"
    health.sicken(h, cfg, bo, "a check", level="ill")
    assert not use("remedy", pet=bo["id"])[0], "the house has no remedy"
    kid["carrying"].append(health.REMEDY)
    assert use("remedy", pet=bo["id"])[0] and health.stage_of(bo) is None and health.REMEDY not in kid["carrying"], "a remedy: two stages back"
    print("visitor: a theory from kin's, moved by what he does; absence noticed and a return; notes; tend and remedy")
    await settle(eng)


async def tales(d):
    """§10.3: last words and a tale at a death; an elder tells it in the evening, across families, with its hook."""
    cfg = config()
    eng, p0 = await house(d, cfg, ("pond", "attic", "garden"))
    h = eng.house
    elder, ada, bo = hob(eng, "Elm", "elder"), hob(eng, "Ada"), hob(eng, "Bo")
    kit = hob(eng, "Kit", "child")
    ada["family"] = elder["family"] = 1
    kit["family"] = 2
    nursery = room(eng, "nursery")
    place(eng, [p0, elder, ada, bo, kit], nursery)
    ada["leave"] = {"what": "my cup", "to": "Kit", "last_words": "Keep away from the red fish."}
    health.poisoned(h, cfg, ada, "red-finned fish", level="gravely ill")
    eng.kill(ada, "bad food")
    t = h["tales"][-1]
    assert t["about"] == ada["id"] and t["last_words"] == "Keep away from the red fish." and t["cause"] == "bad food" and t["hook"] == {"name": "avoid_thing", "arg": "red-finned fish", "when": ""}
    assert any('as it died: "Keep away from the red fish."' in e[1] for e in kit["events"]) and ada["said"]["text"] == t["last_words"], "the last words are spoken"
    assert t == K.tale(t), "a contracts.tale"
    for kind in ("adult", "child"):   # (not before the evening, and not by one who is not old)
        assert not story.tell_targets(h, cfg, bo if kind == "adult" else elder, lambda pos: None) or kind == "child"
    to(eng, 3, 20.5)
    m, A = eng.minds[elder["id"]], cfg["activities"]["tell"]
    got = body.targets(h, cfg, elder, m.mem, "tell", A)
    assert got and got[0]["who"] == kit["id"], got
    did, done = planner.finish(m, dict(got[0], name="tell", do=A["do"], since=h["tick"], began=h["tick"]), A)
    assert done and "the tale of Ada" in did and kit["id"] in t["told"], did
    assert any(x["kind"] == "tale" and x["weight"] == 3 and "Ada" in x["text"] for x in kit["memories"])
    assert any(b["hook"] == t["hook"] and b["source"] == "told by Elm" for b in eng.minds[kit["id"]].mem.active()), "the hook believed"
    assert K.since(h, "told", 0) and any(x["kind"] == "tale" and "crossed" in x["text"] for x in h["moments"]), "told across families"
    assert not body.targets(h, cfg, elder, m.mem, "tell", A), "once a day, and once to each"
    assert "b:tell" in planner.AIM["tell"][0]
    print("tales: last words spoken at a death, a tale written; an elder tells it to another family's child, its hook believed")
    await settle(eng)


async def off_day(d, part):
    """One of D's parts off (spirit on): a stub day of the house, and its data never appears."""
    cfg = config(off=(part,))
    eng, p0 = await house(d, cfg, ("pond", "attic", "garden"))
    h = eng.house
    ada, bo, kit = hob(eng, "Ada", parent=p0), hob(eng, "Bo"), hob(eng, "Kit", "child")
    walls.visitor(h, cfg, h["rooms"][ada["room"]], "Ada, look in the attic", "north wall")
    health.sicken(h, cfg, bo, "a check", level="ill")
    tend = visitor.use(eng, "tend", {"pet": bo["id"]})
    for _ in range(round(cfg["ticks_per_day"] * 1.2)):
        await eng.tick()
    if part == "stage":
        assert not any(k in h for k in ("director", "happening", "happenings", "coming")) and not K.since(h, "happening", 0)
        assert "power_cut" in cfg["house"]["events"]["kinds"] and eng.db.execute("SELECT count(*) FROM calls WHERE kind='director'").fetchone()[0] == 0
    if part == "visitor5":
        assert not tend[0] and not any(k in h["visitor"] for k in ("away", "tend")), h["visitor"].keys()
        assert not any(k in p for p in h["pets"].values() for k in ("visitor_theory", "watched_day", "asked_day"))
        assert not any(k in m for r in h["rooms"].values() for m in r.get("marks", []) for k in ("to", "read"))
    if part == "memory2":
        eng.kill(ada, "old age")
        assert "tales" not in h and not K.since(h, "told", 0)
    print("stage: [%s] off, a stub day leaves its data unchanged" % part)
    await settle(eng)


async def checks(root):
    assert set(K.HAPPENINGS) <= set(stage.EFFECTS) and set(K.HAPPENINGS) <= set(stage.MENU) and set(K.VISITOR_TOOLS) <= set(visitor.TOOLS)
    for m, fns in K.API["D"].items():
        mod = __import__(m, fromlist=["x"])
        assert all(callable(getattr(mod, f, None)) for f in fns), m
    assert all(MENU["cooldown"] <= 7 for MENU in stage.MENU.values()), "the house keeps a week of happenings"
    await rules(root + "/r")
    await lands(root + "/l")
    await a_day(root + "/a")
    await visitor5(root + "/v")
    await tales(root + "/t")
    for part in MINE:
        await off_day(root + "/o" + part, part)


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(checks(d))
    print("check_stage: all passed")


if __name__ == "__main__":
    main()
