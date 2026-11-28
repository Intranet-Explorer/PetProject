"""Self-check for SPEC-v5.3 §2, §3, §9 (helper A: projects and sites): on a stub house with v5.3's projects on, a hob
whose drive is "to leave the house" builds a shelter in the meadow over several days, sleeps there and comes in for
food, while two hobs who keep each other company finish a joint project; the plan's `project` names a planned one and
validates against its schema; an orphan is taken up by kin and carries both names; a falling-out splits a joint one;
an abandoned one's stock is freed and its site decays; build.py's builds are projects; the migration reports each
hob's first project; and with [projects] off nothing of it is in the house.
    uv run python -m engine.check_projects"""
import asyncio
import os
import tempfile

from . import contracts as K
from . import brain4, build, outdoors, pages, projects
from .brains import model
from .check import at
from .check_brain4 import calm, config, grow, hob, valid
from .check_jobs import v5
from .tick import Engine, stub_brains
from .world import generate_room

KEYS = ("project53", "proj53_day", "slept_out53", "project_next")


def config53(on=True):
    cfg = config(True)
    cfg["clock"]["tick_seconds"] = 8   # (a shorter world day in ticks: the days a shelter takes run in a minute or two)
    cfg["ticks_per_day"] = round(cfg["clock"]["day_seconds"] / 8)
    cfg["ticks_per_hour"] = cfg["ticks_per_day"] / 24
    v5(cfg)
    cfg["projects"]["on"] = on
    cfg["ladder"]["on"] = False   # (a falling-out is checked by itself, below)
    return cfg


async def house53(d, on=True):
    """A house with its founder grown, a workshop, a garden, and the yard and meadow behind the gate, all known."""
    cfg = config53(on)
    eng = Engine(cfg, d, stub_brains)
    p0 = eng.new_lineage()
    p0["laid"] = -10 ** 6
    await eng.tick()
    h = eng.house
    grow(h, p0, "adult")
    p0.update(name="Antonia", mood=calm(h))
    for kind in ("workshop", "garden"):
        rid = next(r for r, x in sorted(h["rooms"].items()) if not x["type"] and r in h["rooms"][p0["room"]]["doors"].values())
        generate_room(h, cfg, rid, kind)
    garden = next(r for r in h["rooms"].values() if r["type"] == "garden")
    if not outdoors.migrate(h, cfg):   # (the garden needs a free south wall: another garden where there is one)
        for r in sorted(h["rooms"].values(), key=lambda r: r["id"]):
            if not r["type"] and any(h["rooms"][x]["type"] for x in r["doors"].values()):
                garden["type"] = None
                generate_room(h, cfg, r["id"], "garden")
                if outdoors.migrate(h, cfg):
                    break
    assert outdoors.YARD in h["rooms"], "the yard and the meadow are there"
    at(eng, 10)
    return eng, p0


def knows_all(h):
    for p in h["pets"].values():
        p["rooms"].update({rid: h["tick"] for rid, x in h["rooms"].items() if x["type"]})


def lay(h, room, bits):
    """Beds of these bits growing in a room (not loose on the floor: that is mess, and tidied away)."""
    for bit, n in bits.items():
        for i in range(n):
            room["spots"].append({"bit": bit, "pos": [1 + i % 10, 1 + (len(room["spots"]) // 10) % 6], "ready": True, "back": None, "loose": False})


async def hermit(d):
    """§6.3, §2.5: Antonia (to leave the house) builds a shelter in the meadow over several days, sleeps there and comes
    in for food; Cass and Dov, who keep each other company, finish a joint project taking turns."""
    eng, ant = await house53(d)
    h, cfg = eng.house, eng.cfg
    cfg["projects"]["steps_per_day"] = 2
    room = h["rooms"][ant["room"]]
    cass, dov = hob(eng, room, [3, 3]), hob(eng, room, [5, 3])
    cass["name"], dov["name"] = "Cass", "Dov"
    cass["habits"] = [K.habit({"name": "keep company", "target": dov["id"]})]
    dov["habits"] = [K.habit({"name": "keep company", "target": cass["id"]})]
    ant["drive"] = K.drive({"name": "to leave the house", "since": 0})
    for p in (ant, cass, dov):
        p.pop("project53", None)
    knows_all(h)
    garden = next(r for r in h["rooms"].values() if r["type"] == "garden")
    lay(h, garden, {"reed": 14, "wood": 22, "stone": 12})
    pr = projects.draw(h, cfg, ant)
    assert pr and pr["kind"] == "shelter" and pr["state"] == "planned" and not pr["site"], "her first project, from her drive: a shelter, planned, no site yet: %s" % pr
    assert "say what it is and where" in projects.line(h, cfg, ant), projects.line(h, cfg, ant)
    words, ok = projects.propose(h, cfg, ant, {"kind": "shelter", "site": "by the willow", "why": "for when the house is too loud", "goal": "a shelter by the willow"})
    assert ok and pr["goal"] == "a shelter by the willow" and pr.get("where") == "by the willow" and not projects.site_of(h, pr), "the model names it, and where; v5.3.1: no plot held until its first step: %s %s" % (words, pr)
    m = eng.minds[ant["id"]]
    text, ctx = brain4.plan_packet(h, cfg, ant, m.mem)
    assert "your shelter" in text and ctx.get("project53"), "the plan packet says its project"
    reply = await m.brain.think4("plan", text, ctx)
    assert "project" in reply and valid(model.schema4("plan", ctx), reply) is None, valid(model.schema4("plan", ctx), reply)
    assert valid(model.schema4("plan", ctx), dict(reply, project={"kind": "build", "site": "", "why": "", "goal": ""})), "a build.py build is never proposed"
    done_at, hungry_at = None, None
    for i in range(cfg["ticks_per_day"] * 9):
        h["weather"] = "clear"
        if pr["state"] == "done" and done_at is None:
            done_at = h["clock"]["day"]
        if K.events53(h, "slept_out") and hungry_at is None and h["clock"]["phase"] == "day" and not ant["sleep"]:
            hungry_at = h["tick"]
            if "hunger" in ant["needs"]:
                ant["needs"]["hunger"] = 5.0   # (morning, and hungry: it comes in for food)
        await eng.tick()
        if K.events53(h, "came_in"):
            break
    steps = [s for s in K.events53(h, "step") if s["project"] == pr["id"]]
    assert pr["state"] == "done", "the shelter is finished: %s (%s)" % (projects.words(h, pr), h["v5"].get("setbacks"))
    site = projects.site_of(h, pr)
    assert site and site["name"] == "by the willow" and site["room"] == outdoors.MEADOW, "built where it said: %s" % site
    assert len({cfg_day(cfg, s["tick"]) for s in steps}) >= 3, "over several days: %s" % sorted({cfg_day(cfg, s["tick"]) for s in steps})
    fix = h["rooms"][outdoors.MEADOW]["objects"].get(pr["fixture"] or "")
    from . import items
    it = items.of(h, cfg, fix, pr["fixture"], h["rooms"][outdoors.MEADOW]) if fix else None
    assert it and K.works(it, "cover") and K.works(it, "heat") and fix["fix"]["cozy"], "a fixture with its kind's verbs: %s" % it
    assert projects.sheltered(h, cfg, ant)[0] == outdoors.MEADOW, "it may sleep there"
    out = K.events53(h, "slept_out")
    assert out and out[0]["pet"] == ant["id"], "she slept out under it (done on day %s, now day %s %s, in %s)" % (done_at, h["clock"]["day"], h["clock"]["hour"], ant["room"])
    came_ = K.events53(h, "came_in")
    assert came_ and came_[0]["pet"] == ant["id"], "and came in by day"
    joint = next((x for x in projects.store(h).values() if set(x["owners"]) == {cass["id"], dov["id"]} and not projects.mirror(x)), None)   # (not a build.py build they both had a paw in)
    assert joint and joint["state"] == "done", "the keep-company pair's joint project is finished: %s (%s; habits %s, %s)" % (
        joint and projects.words(h, joint), joint and joint["steps"], cass.get("habits"), dov.get("habits"))
    assert all(joint["steps_by"].get(x, 0) > 0 for x in (cass["id"], dov["id"])), "both took steps: %s" % joint["steps_by"]
    assert any(c == "worked_together" for c in [c[0] if isinstance(c, (list, tuple)) else c.get("cause") if isinstance(c, dict) else c for c in cass["opinions"][dov["id"]]["causes"]]), "worked_together fired: %s" % cass["opinions"][dov["id"]]["causes"]
    rows = pages.board_view(h)["projects"]
    assert projects.words(h, pr) == "Antonia's shelter stands finished by the willow in the meadow", projects.words(h, pr)
    assert {r["id"] for r in rows} >= {x["id"] for x in projects.store(h).values() if x["state"] in projects.OPEN}, "every open project is on the board: %s" % rows
    print("projects: Antonia's shelter finished on day %s (steps on days %s); slept out %s, came in %s; %s" % (
        done_at, sorted({cfg_day(cfg, s["tick"]) for s in steps}), len(out), came_[0]["why"], projects.words(h, joint)))
    return eng


def cfg_day(cfg, tick):
    return 1 + int((8 + tick / cfg["ticks_per_hour"]) // 24)


async def orphans(d):
    """§2.4: an owner's death orphans its project, said in words; a stranger may not take it up, kin may, and the finished
    thing carries both names. §2.5 a falling-out. Abandonment frees the stock; the site decays."""
    eng, ant = await house53(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][ant["room"]]
    kid, stranger = hob(eng, room, [3, 3], stage="youngling"), hob(eng, room, [5, 3])
    kid["name"], stranger["name"] = "Pip", "Wren"
    kid["parents"] = [ant["id"]]
    for p in (kid, stranger):
        projects.store(h).pop((projects.of(h, p) or {}).get("id"), None)
        p["project53"] = 0
    knows_all(h)
    pr = projects.begin(h, cfg, ant, "shelter", goal="a shelter in the meadow", site="the meadow")
    projects.claim(h, cfg, ant, pr, pr.get("where") or "")   # (v5.3.1: a plot is taken as its first step begins)
    pr["steps"][0]["done"] = True
    pr["progress"] = 0.4
    pr["stock"] = {"reed": 5}
    eng.kill(ant, "old age")
    assert pr["state"] == "orphaned" and pr["owners"] == [], pr
    said = projects.words(h, pr)
    assert said.startswith("Antonia's shelter stands") and "in the meadow" in said, said
    assert any(r["state"] == "orphaned" and r["words"] == said for r in pages.board_view(h)["projects"]), "on the board in words"
    assert not projects.take_up(h, cfg, stranger, pr["id"]), "not one who was nothing to her"
    assert projects.take_up(h, cfg, kid, pr["id"]) and pr["owners"] == [kid["id"]] and K.events53(h, "taken_up")[-1]["was"] == ant["id"]
    for s in pr["steps"]:
        s["done"] = True
    projects.finish(h, cfg, kid, pr)
    assert pr["fixture"] and "Antonia" in pr["fixture"] and "Pip" in pr["fixture"], "the finished thing carries both names: %s" % pr["fixture"]
    # §2.5 a falling-out: the stock halved, the project with the one who did more
    j = projects.joint(h, cfg, kid, stranger)
    assert j and set(j["owners"]) == {kid["id"], stranger["id"]}
    j["stock"], j["steps_by"] = {"wood": 6}, {stranger["id"]: 2, kid["id"]: 1}
    projects.claim(h, cfg, kid, j)
    j["steps"][0]["done"] = True   # (v5.3.1: its plot is held once its first step is done)
    h.setdefault("grievances", []).append({"by": kid["id"], "against": stranger["id"], "why": "x", "since": h["tick"], "rung": 1, "history": []})
    projects.falling_out(h, cfg, j)
    assert j["owners"] == [stranger["id"]] and j["stock"] == {"wood": 3}, "split: %s %s" % (j["owners"], j["stock"])
    h["grievances"].clear()
    # §2.4 abandoned: no step for abandon_days; the stock laid out free; the site decays over a season, then is free
    site = projects.site_of(h, j)
    spots = len(h["rooms"][site["room"]]["spots"])
    j["touched"] = h["tick"] - cfg["ticks_per_day"] * (cfg["projects"]["abandon_days"] + 1)
    h["v5"]["projects_day"] = None
    projects.tick(h, cfg)
    assert j["state"] == "abandoned" and not j["stock"] and len(h["rooms"][site["room"]]["spots"]) == spots + 3 and site["stage"] == "decaying", (j, site)
    assert site["project"] is None and not j["site"], "v5.3.1: abandoned frees the plot at once; the ruin stays on it: %s" % site
    site["since"] = h["tick"] - cfg["ticks_per_day"] * cfg["projects"]["decay_days"]
    projects.decay(h, cfg)
    assert site["stage"] == "bare" and site["project"] is None, "decayed to nothing: %s" % site
    print("projects: orphaned (%s), taken up by kin (%s); a falling-out split it; abandoned and decayed" % (said, pr["fixture"]))


async def migration(d):
    """§9: once a house: the plots, a first project for each youngling and older whose drive maps to one, and build.py's
    under-way builds as projects with their builders as owners (shown on the board the same way)."""
    eng, ant = await house53(d)
    h, cfg = eng.house, eng.cfg
    shop = next(r for r in h["rooms"].values() if r["type"] == "workshop")
    ant["drive"] = K.drive({"name": "to leave the house", "since": 0})
    ant.pop("project53", None)
    projects.store(h).clear()
    name, o = build.begin(h, cfg, ant, shop, next(k for k, P in cfg["build"]["project"].items() if P["rooms"] == "any" or "workshop" in P["rooms"]))
    o["site"]["paws"][ant["id"]] = 1
    h["migrated"].pop("v53_projects", None)
    lines = projects.migrate(h, cfg)
    assert any(l.startswith("plots: ") and "by the willow in the meadow" in l for l in lines), lines
    assert any(l.startswith("Antonia: a shelter") for l in lines), lines
    b = projects.store(h).get("build:%s|%s" % (shop["id"], name))
    assert b and b["kind"] in ("build", "statue") and b["owners"] == [ant["id"]] and b["site"], "build.py's build is a project: %s" % b
    assert projects.migrate(h, cfg) == [], "once a house"
    assert {"willow", "standing stone"} & set(h["rooms"][outdoors.MEADOW]["objects"]) == {"willow"}, "the willow"
    print("projects: migration: %s" % "; ".join(lines))


async def off(d):
    """[projects] off: nothing of it in the house, a hob, or its aims."""
    eng, ant = await house53(d, on=False)
    h, cfg = eng.house, eng.cfg
    ant["drive"] = K.drive({"name": "to leave the house", "since": 0})
    for _ in range(cfg["ticks_per_day"] // 3):
        h["weather"] = "clear"
        await eng.tick()
    V = h.get("v5") or {}
    assert not any(k in V for k in ("projects", "sites", "setbacks", "projects_day", "project_n", "bond_seen")), sorted(V)
    assert not any(k in p for p in h["pets"].values() for k in KEYS), "no hob keys"
    assert not any(str((p.get("job_aim") or {}).get("job") or "").startswith("project:") for p in h["pets"].values())
    assert not any(x in r.get("objects", {}) for r in h["rooms"].values() for x in ("willow", "standing stone")), "no landmarks"
    mig = os.path.join(d, "migration-v5.3.txt")   # (the habits' half may be there: it is [habits]')
    assert "v53_projects" not in h.get("migrated", {}) and not (os.path.exists(mig) and "project" in open(mig).read().lower())
    text, ctx = brain4.plan_packet(h, cfg, ant, eng.minds[ant["id"]].mem)
    assert "project53" not in ctx and "project" not in model.schema4("plan", ctx)["properties"], "no project in the plan"
    print("projects: [projects] off: nothing of it in the house")


def main():
    base = os.environ.get("PET_SCRATCH")
    with tempfile.TemporaryDirectory(dir=base) as d:
        asyncio.run(off(d + "/off"))
        asyncio.run(migration(d + "/mig"))
        asyncio.run(orphans(d + "/orph"))
        asyncio.run(hermit(d + "/hermit"))
    print("check_projects: all passed")


if __name__ == "__main__":
    main()
