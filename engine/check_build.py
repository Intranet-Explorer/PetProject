"""Self-check for building that lasts and decorating (SPEC-v3.5 §4, §7.1): engine/build.py and building.toml.

    uv run python -m engine.check_build

Stub minds only (a scripted brain that waits), in a temporary house. A want to build comes from the room; the body
carries what the thing takes and sets it in place, binds a hammer when it has the makings, and works on it in
spells; two go faster than one; what stands is a fixture with its builders' names that changes its room, is there
after a save and a load and after the family that built it, wears, and is mended. A dye is made, paint goes on in
the painter's coat's pattern, is felt as home by its family and as a little strange by another, and fades."""
import asyncio
import json
import tempfile
from pathlib import Path

from . import actions, body, build, craft, director, order, physics, things, wants, world
from .check import at, engine, scripted
from .tick import Engine, Mind
from .world import LONG_AGO, generate_room

BASE = ("wood", "stone", "metal", "clay", "fibre", "sand")   # SPEC-v3.5 §4.3: what the machine in the storeroom gives


def grown(h, pet, stage="adult"):
    pet.update(stage=stage, born=h["tick"], sleep=None)
    pet["stage_at"].update({s: h["tick"] for s in ("hatchling", "child", "youngling", "adult")})
    pet["needs"].update(energy=90.0, comfort=80.0, company=80.0, curiosity=60.0)
    return pet


def room(h, cfg, pet, kind):
    """A room of this kind, found, and known to the pet."""
    r = next((r for r in h["rooms"].values() if r["type"] == kind), None) or generate_room(h, cfg, next(r["id"] for r in h["rooms"].values() if not r["type"]), kind)
    pet["rooms"][r["id"]] = h["tick"]
    return r


def cand(h, cfg, pet, key):
    return next((c for c in wants.candidates(h, cfg, pet) if c["key"] == key), None)


def put_up(h, cfg, pet, r, key):
    """A thing built outright, as the body would have done it over a day: begun, everything set in place, the last spell of work done."""
    name, o = build.begin(h, cfg, pet, r, key)
    o["site"]["placed"], o["site"]["paws"] = dict(cfg["build"]["project"][key]["needs"]), {pet["id"]: 3}
    build.stand(h, cfg, pet, r, name)
    return name, r["objects"][name]


async def until(eng, done, most):
    for n in range(most):
        if done():
            return n
        await eng.tick()
    return most if done() else None


async def main():
    cfg = world.load_config()
    cfg["wants"]["most"] = 1          # (one want at a time, so the check's pet is about the thing being checked)
    cfg["house"]["events"]["kinds"] = {"delivery": 1}
    B, S, PJ = cfg["build"], cfg["build"]["build"], cfg["build"]["project"]
    art = Path(__file__).parent.parent / "view" / "assets" / "sprites.json"
    sprites = json.loads(art.read_text()) if art.exists() else None

    # ---- the data holds together ----
    assert 10 <= len(PJ) <= 14, "about ten projects"
    for key, P in PJ.items():
        assert P["when"] in build.WHEN and P["sessions"] >= 3 and 2 <= sum(P["needs"].values()) <= 5, "a project names a real cause, and takes a few pieces: %s" % key
        assert P["rooms"] == "any" or all(t in cfg["house"]["rooms"] for t in P["rooms"]), key
        assert P.get("fix") or P.get("rules") or P.get("proof") or P.get("bits"), "every project changes its room: %s" % key
        assert not sprites or "fix.built." + key in sprites, "and has a picture: %s" % key
        assert all(b in BASE or any(r.get("gives") == b and src in BASE for (src, how), r in cfg["craft"]["rules"].items()) for b in P["needs"]), \
            "a project is made of the six base materials, or of what one process makes of one (a want leads one step deep): %s" % key
    assert all(d in cfg["house"]["bits"] and (not sprites or "bit." + d in sprites) for d in B["paint"]["dyes"]), "every dye is a bit with a picture"
    assert not sprites or all(n in sprites for n in ("fix.site", "fix.site.half", "fix.site.wall", "fix.site.wall.half", "grows.lily")), "a thing under way has its pictures"
    assert all(a["do"] == "build" and a["mode"] in ("place", "work", "mend", "hammer", "paint") for a in B["activities"].values()) and "build" in cfg["activities"]

    with tempfile.TemporaryDirectory() as d:
        eng, pet = engine(cfg, d + "/a")
        h = eng.house
        at(eng, 9)
        await eng.tick()
        grown(h, pet)
        pet["name"] = "Lean"
        shop = room(h, cfg, pet, "workshop")
        pet["room"], pet["pos"] = shop["id"], [6, 4]
        pet["wants"] = []

        # ---- a want to build comes from the room ----
        key = "build:%s|bench" % shop["id"]
        c = cand(h, cfg, pet, key)
        assert c and "nowhere to sit" in c["text"] and "wood" in c["text"] and "hammer" in c["text"], "a room with nowhere to sit gives the want to build a bench: %s" % c
        nur = h["rooms"][h["start"]]
        assert not cand(h, cfg, pet, "build:%s|bench" % nur["id"]), "a room with a bed does not"
        assert not cand(h, cfg, pet, "build:%s|big shelf" % shop["id"])
        shop["mess"] = 2
        assert "crowded" in cand(h, cfg, pet, "build:%s|big shelf" % shop["id"])["text"], "a crowded floor gives the want to build a big shelf"
        shop["mess"] = 0
        assert not cand(h, cfg, pet, "build:%s|draught curtain" % shop["id"])
        shop["cold_until"] = h["tick"] + 5
        build.hourly(h, cfg)
        shop["cold_until"] = LONG_AGO
        assert "stop the cold coming in" in cand(h, cfg, pet, "build:%s|draught curtain" % shop["id"])["text"], "a draught gives the want to stop the cold coming in"
        shop.pop("draught")
        egg = world.new_pet(h, cfg, shop["id"], [2, 2])
        assert not [c for c in wants.candidates(h, cfg, egg) if c["what"] in ("build", "paint")] if egg["stage"] != "egg" else True

        # ---- the body carries what it takes and sets it in place: the first of it marks the place ----
        pet["wants"] = [dict({k: v for k, v in c.items() if k != "weight"}, since=h["tick"])]
        find = lambda: build.find(shop, "bench")[1]
        n = await until(eng, lambda: find() and not build.missing(PJ["bench"], find()), 500)
        assert n is not None, "its body carried two pieces of wood to the place and set them down: %s, %s" % (find(), pet["carrying"])
        name, o = build.find(shop, "bench")
        assert name == "bench" and o["fix"] == {"site": "bench"} and o["state"] == "being built" and o["site"]["placed"] == {"wood": 2}
        assert any(m["kind"] == "project" and m["text"] == "Lean began a bench in the workshop" for m in h["moments"]), "beginning one is a moment"
        v = {}
        build.view(h, cfg, shop, name, o, v)
        assert v["build"]["sprite"] == "fix.site" and v["build"]["title"] == "a bench" and o["state"] == "being built" and v["build"]["progress"] == 0, "under way it is drawn as a thing under way: %s" % v
        assert "being built" in actions.fixture_says(o["fix"])

        # ---- nobody has a hammer: the want leads to one (the book, its makings, and its paws bind it) ----
        wants.refresh(h, cfg, pet)
        w = pet["wants"][0]
        assert w["key"] == key and "nobody has a hammer" in w["text"] and "hammer" in pet["lacks"], "with everything in place it waits on a hammer, and says so: %s" % w["text"]
        assert build.question(h, cfg, pet, w) == "how do you make something to knock things together with", "it would ask the book how one is made"
        assert not [x for x in body.targets(h, cfg, pet, None, "build", cfg["activities"]["build"])], "and there is no working on it without one"
        pet["takes"] = ["hammer"]   # (it has read the book's page)
        assert build.question(h, cfg, pet, w) is None
        assert build.chain(h, cfg, pet, w), "the hammer is what it waits on"
        pet["carrying"] = ["pebble"]
        named = [b for b, k in build.named(h, cfg, pet) if k == key]
        assert "vine cord" in named and "rope" in named and "pebble" not in named, "what a hammer takes that has to be made first becomes a step: %s" % named
        pet["carrying"] = ["pebble", "wood", "vine cord"]
        wants.refresh(h, cfg, pet)
        assert "you could make one now" in pet["wants"][0]["text"]
        made = lambda: craft.tool_here(h, cfg, shop, "hammer")
        assert await until(eng, made, 200) is not None, "with a hammer's makings in its paws, and its mind not taking it up, its body binds one: %s" % pet["carrying"]
        assert any(m["kind"] == "tool" for m in h["moments"]) and pet["carrying"] == []

        # ---- spells of work progress it; two together go faster and are company ----
        assert await until(eng, lambda: o["site"]["work"] >= 1, 200) is not None, "with a hammer its body works on it"
        m1, A = eng.minds[pet["id"]], cfg["activities"]["build"]
        now = {"what": name, "job": None, "where": None, "name": "build"}
        o["site"]["last"] = {}
        w0 = o["site"]["work"]
        assert build.finish(m1, now, A)[1] and o["site"]["work"] == w0 + 1.0, "a spell of work alone counts for one"
        mate = grown(h, world.new_pet(h, cfg, shop["id"], [5, 4]), "adult")
        mate["name"] = "Sven"
        eng.minds[mate["id"]] = Mind(eng, mate)
        o["site"]["last"] = {mate["id"]: h["tick"]}   # (Sven was hammering at it a moment ago)
        pet["needs"]["company"] = mate["needs"]["company"] = 50.0
        o["site"]["paws"][mate["id"]] = 1
        w0 = o["site"]["work"]
        told, done = build.finish(m1, now, A)
        assert done and o["site"]["work"] == round(w0 + S["together"], 2) and S["together"] > 1 and "side by side with Sven" in told, "with another at it too it counts for more: %s" % told
        assert pet["needs"]["company"] > 50 and mate["needs"]["company"] > 50, "working side by side is being with someone"
        assert not body.targets(h, cfg, mate, None, "build", A), "its paws rest between two spells"
        o["site"]["last"].pop(mate["id"])
        assert [t for t in body.targets(h, cfg, mate, None, "build", A) if t["what"] == name], "anyone in the room may lend a paw"
        v = {}
        build.view(h, cfg, shop, name, o, v)
        assert v["build"]["sprite"] == "fix.site.half" and 0.4 <= v["build"]["progress"] < 1, "half built, it is drawn half built: %s" % v

        # ---- it is finished: a fixture with its builders' names, a moment, a want met ----
        hammer = made()
        wear0 = shop["objects"][hammer]["made"]["wear"]
        while "site" in o:
            assert build.finish(m1, now, A)[1]
        b = o["fix"]["built"]
        assert o["fix"]["rest"] == 2.5 and b["names"] == ["Lean", "Sven"] and "state" not in o and shop["objects"][hammer]["made"]["wear"] > wear0, "it stands, and the hammer has worn a little: %s" % o
        assert any(m["kind"] == "built" and m["text"] == "Lean and Sven built a bench in the workshop" for m in h["moments"]), [m["text"] for m in h["moments"] if m["kind"] == "built"]
        v = {}
        build.view(h, cfg, shop, name, o, v)
        assert v["build"] == {"sprite": "fix.built.bench", "title": "the bench Lean and Sven built", "flat": False, "glow": False, "worn": False, "at": b["at"]}, v
        assert "Lean and Sven built it" in v["says"] and "Lean and Sven built it" in actions.describe_thing(h, cfg, pet, name)
        had = pet.get("fulfilled", 0)
        wants.refresh(h, cfg, pet)
        assert pet.get("fulfilled", 0) == had + 1 and any(m["kind"] == "want" and m["text"] == "Lean built a bench in the workshop" for m in h["moments"]), "whoever wanted it and had a paw in it has what it wanted"
        assert not cand(h, cfg, pet, key), "and the room no longer lacks it"
        text, fx, _ = actions.use(h, cfg, pet, name)
        assert fx.get("energy", 0) > 0 and any(t["what"] == name for t in body.targets(h, cfg, pet, None, "sit on", cfg["activities"]["sit on"])), "a bench is somewhere to rest: %s" % text

        # ---- each finished thing really changes its room ----
        cellar = room(h, cfg, pet, "cellar")
        pet["room"], pet["pos"] = cellar["id"], [5, 5]
        at(eng, 23)
        cold = lambda: [e for e in physics.effects(h, cfg, pet) if e["tag"] == "cellar"][0]
        assert cold()["rate"] < 0 and things.room_rule(cfg, cellar, "cold_night") < 0, "the cellar is cold at night"
        # (what it takes that lies in no room it knows is named, so a step to get it can follow: here, from clay under something heavy)
        lining, lo = build.begin(h, cfg, pet, cellar, "wall lining")
        pet["wants"], pet["carrying"] = [dict({k: v for k, v in cand(h, cfg, pet, "build:%s|wall lining" % cellar["id"]).items() if k != "weight"}, since=h["tick"])], []
        assert ("clay tile", pet["wants"][0]["key"]) in build.named(h, cfg, pet) and ("fibre", pet["wants"][0]["key"]) in build.named(h, cfg, pet), build.named(h, cfg, pet)
        step = [c for c in wants.candidates(h, cfg, pet) if c["what"] == "get" and c.get("gives") == "clay tile"]
        assert step and step[0]["bit"] == "clay" and step[0]["how"] == "press" and step[0]["parent"] == pet["wants"][0]["key"], "a material it lacks leads to a step to get it: %s" % step
        lo["site"]["placed"], lo["site"]["paws"], pet["wants"] = dict(PJ["wall lining"]["needs"]), {pet["id"]: 3}, []
        build.stand(h, cfg, pet, cellar, lining)
        lo = cellar["objects"][lining]
        assert lo["wall"] and things.room_rule(cfg, cellar, "cold_night") == 0 and cold()["rate"] == 0 and "easy" in cold()["feel"], "lined, the cellar is not cold: %s" % cold()
        out = []
        assert build.felt(h, cfg, pet, cellar, out, -0.3) == -0.3 * PJ["wall lining"]["cold"] and "keeps most of the cold out" in out[-1]["feel"], "and winter's cold gets in less"
        assert build.felt(h, cfg, pet, shop, [], -0.3) == -0.3
        green = room(h, cfg, pet, "greenhouse")
        vines = lambda: sum(1 for s in green["spots"] if s["bit"] == "vine")
        was = vines()
        put_up(h, cfg, pet, green, "trellis")
        assert vines() == was + PJ["trellis"]["bits"]["vine"], "a trellis gives more vines"
        shop["mess"] = 2
        shelf, so = put_up(h, cfg, pet, shop, "big shelf")
        assert order.stores(cfg, shop)[shelf] == 8 and not order.full(cfg, shop), "a big shelf keeps eight things"
        patch, _ = put_up(h, cfg, pet, shop, "roof patch")
        director.leak(h, cfg, shop)
        assert shop["wet_until"] <= h["tick"] and any(m["kind"] == "held" for m in h["moments"]), "a roof patch keeps the leak out"
        director.leak(h, cfg, cellar)
        assert cellar["wet_until"] > h["tick"], "... of its own room only"
        cellar["wet_until"] = LONG_AGO
        assert not build.proof(h, cfg, shop, "draught")
        put_up(h, cfg, pet, shop, "draught curtain")
        assert build.proof(h, cfg, shop, "draught"), "a draught curtain keeps the draught out"
        attic = room(h, cfg, pet, "attic")
        assert craft.place(h, cfg, attic, "weave") is None
        put_up(h, cfg, pet, attic, "table")
        assert craft.place(h, cfg, attic, "weave")[0] == "table", "a table is somewhere to weave"
        box, bo = put_up(h, cfg, pet, nur, "window box")
        assert box == "window box" and bo["wall"] and craft.plantable(cfg, box, bo) and bo["pos"] == nur["objects"]["window"]["pos"], "a window box under the window can be planted in"
        pond = room(h, cfg, pet, "pond")
        assert not any(s["bit"] == "lily" for s in pond["spots"])
        bridge, bro = put_up(h, cfg, pet, pond, "pond bridge")
        water = next(o["fix"]["water"] for o in pond["objects"].values() if "water" in o.get("fix", {}))
        assert [s["pos"] for s in pond["spots"] if s["bit"] == "lily"] == PJ["pond bridge"]["spots"] and all(t in water for t in PJ["pond bridge"]["spots"]), \
            "a bridge opens a spot out on the water that was not there before"
        assert cfg["craft"]["rules"][("lily", "press")]["gives"] == "blue dye" and "lily" not in world.bit_kinds(h, cfg), "what grows there is found nowhere else"
        niche, no = put_up(h, cfg, pet, cellar, "lamp niche")
        pet["pos"] = [no["pos"][0], 1]
        assert any(e["tag"] == "cozy" and niche in e["feel"] for e in physics.effects(h, cfg, pet)) and not things.light_on(h, cfg, cellar, harsh=True), "a lamp niche is a comfort to be by, and no harsh light"
        h["creatures"].append({"id": "c1", "kind": "mouse", "room": nur["id"], "pos": [3, 3], "tame": pet["id"], "trust": {pet["id"]: 3.1}, "name": None, "doing": "", "born": h["tick"]})
        assert cand(h, cfg, pet, "build:%s|hutch" % pet["room"]), "a tamed creature gives the want to build it a hutch"
        put_up(h, cfg, pet, cellar, "hutch")
        build.hourly(h, cfg)
        assert h["creatures"][-1]["trust"][pet["id"]] >= cfg["taming"]["tame_at"] * 0.75, "with a hutch a tamed creature does not go wild"
        h["creatures"].pop()
        pet["sleeps_in"] = green["id"]
        assert cand(h, cfg, pet, "build:%s|bed frame" % green["id"]) and not cand(h, cfg, pet, "build:%s|bed frame" % nur["id"]), "sleeping on a floor gives the want to build a bed frame"
        assert build.under_way(h) == 0

        # ---- it is there after a save and a load, and after the family that built it ----
        eng.save()
        eng.close()
        eng = Engine(cfg, d + "/a", scripted)
        h = eng.house
        pet, shop, cellar = h["pets"][pet["id"]], h["rooms"][shop["id"]], h["rooms"][cellar["id"]]
        o = shop["objects"]["bench"]
        assert o["fix"]["built"]["names"] == ["Lean", "Sven"] and things.room_rule(cfg, cellar, "cold_night") == 0, "what was built is there after a restart, and still does what it did"
        for p in [p for p in h["pets"].values() if p["stage"] not in ("egg", "dead")]:
            eng.kill(p, "old age")
        for p in [p for p in list(h["pets"].values()) if p["stage"] == "egg"]:
            del h["pets"][p["id"]]
        heir = eng.new_lineage()
        heir["laid"] = -10**6
        await eng.tick()
        grown(h, heir)
        heir["rooms"][shop["id"]] = heir["rooms"][cellar["id"]] = h["tick"]
        assert h["lineage"]["id"] == 2 and shop["objects"]["bench"]["fix"]["rest"] == 2.5 and "Lean and Sven built it" in actions.fixture_says(shop["objects"]["bench"]["fix"]), \
            "the next family finds the bench, with its builders' names on it"
        assert not cand(h, cfg, heir, "build:%s|bench" % shop["id"]) and things.room_rule(cfg, cellar, "cold_night") == 0

        # ---- it wears, and is mended with the hammer ----
        h["tick"] += round((S["wear_days"] + 0.1) * cfg["ticks_per_day"])
        build.hourly(h, cfg)
        o, lo = shop["objects"]["bench"], cellar["objects"]["wall lining"]
        assert o["state"] == "worn" and "rest" not in o["fix"] and o["fix"]["built"]["off"] == {"rest": 2.5, "cozy": True}, "after long enough a built thing has worn, and is no comfort: %s" % o
        assert things.room_rule(cfg, cellar, "cold_night") < 0 and build.felt(h, cfg, heir, cellar, [], -0.3) == -0.3, "a worn lining lets the cold back in"
        assert shop["objects"]["big shelf"]["fix"]["store"] == 8, "(a worn shelf still holds what is on it)"
        c = cand(h, cfg, heir, "build:%s|bench" % shop["id"])
        assert c and "has worn" in c["text"] and any(m["kind"] == "worn" for m in h["moments"]), "and the room gives the want to mend it"
        heir["room"], heir["pos"], heir["name"] = shop["id"], [6, 4], "Moss"
        A = cfg["activities"]["mend what was built"]
        hammer = craft.tool_here(h, cfg, shop, "hammer")
        shop["objects"][hammer]["made"]["wear"] = 10**6
        assert not body.targets(h, cfg, heir, None, "mend what was built", A), "not without a hammer that works"
        shop["objects"][hammer]["made"]["wear"] = 0
        heir["wants"] = [dict({k: v for k, v in c.items() if k != "weight"}, since=h["tick"])]
        t = body.targets(h, cfg, heir, None, "mend what was built", A)
        assert t and t[0]["what"] in ("bench", "big shelf", "roof patch", "draught curtain"), t
        assert build.finish(eng.minds[heir["id"]], {"what": "bench", "job": None, "name": "mend what was built"}, A)[1]
        assert "state" not in o and o["fix"]["rest"] == 2.5 and heir["id"] in o["fix"]["built"]["paws"] and o["fix"]["built"]["names"] == ["Lean", "Sven"], "mended, it is as it was, and still theirs who built it"
        wants.refresh(h, cfg, heir)
        assert any(m["kind"] == "want" and m["text"] == "Moss mended the bench in the workshop" for m in h["moments"]) and any(m["kind"] == "mended" for m in h["moments"])
        build.mend(h, cfg, heir, cellar, "wall lining")
        assert things.room_rule(cfg, cellar, "cold_night") == 0

        # ---- decorating: a dye is made, found out like any process ----
        pet = heir
        pet["genome"]["pattern"], pet["genome"]["hue"] = "stripes", 200
        assert "paint" not in actions.allowed(h, cfg, pet, eng.minds[pet["id"]].mem), "without a dye there is no painting"
        assert actions.check({"type": "paint", "where": "wall", "pattern": "dots"}, h, cfg, pet, None) == "you have no colour to paint with: it takes a dye"
        pet["carrying"] = ["berry"]
        a = {"type": "process", "what": "berry", "how": "press"}
        assert actions.check(a, h, cfg, pet, None) is None, actions.check(a, h, cfg, pet, None)
        text, _, _ = actions.apply(h, cfg, pet, a, None)
        assert pet["carrying"] == ["red dye"] and "berry|press" in pet["recipes"] and "red" in text, "a berry pressed gives a red dye: %s" % text
        for bit, how, dye in (("leaf", "soak", "green dye"), ("charcoal", "grind", "black dye"), ("petal", "soak", "petal dye")):
            assert cfg["craft"]["rules"][(bit, how)]["gives"] == dye and dye in B["paint"]["dyes"]

        # ---- paint goes on: a wall, the floor, a rug; in the coat's pattern by itself; and is felt ----
        assert "paint" in actions.allowed(h, cfg, pet, eng.minds[pet["id"]].mem)
        c = cand(h, cfg, pet, "paint:%s" % shop["id"])
        assert c and "you carry red dye" in c["text"], "a pet wants the room it lives in to look like its family's: %s" % c
        t = body.targets(h, cfg, pet, None, "paint", cfg["activities"]["paint"])
        assert t and t[0]["job"][1] in ("wall", "floor"), "with a dye in its paws its body would paint: %s" % t
        text = build.finish(eng.minds[pet["id"]], dict(t[0], name="paint"), cfg["activities"]["paint"])[0]
        p = shop["painted"][0]
        assert pet["carrying"] == [] and p["color"] == "red" and p["pattern"] == "stripes" and p["hue"] == 200 and p["family"] == 1 and p["name"] == "Moss", "its paws paint in its coat's pattern, with its coat's colour through it: %s (%s)" % (p, text)
        assert any(m["kind"] == "painted" and "in red stripes" in m["text"] for m in h["moments"]), [m["text"] for m in h["moments"] if m["kind"] == "painted"]
        pet["carrying"] = ["green dye", "petal dye"]
        assert actions.check({"type": "paint", "where": "ceiling", "pattern": "dots"}, h, cfg, pet, None) == "there is no such place here to paint"
        assert actions.check({"type": "paint", "where": "floor", "pattern": "zigzag"}, h, cfg, pet, None) == "there is no such pattern"
        text, fx, _ = actions.apply(h, cfg, pet, {"type": "paint", "where": "floor", "pattern": "dots"}, None)
        assert [(q["where"], q["color"], q["pattern"]) for q in shop["painted"]] == [(p["where"], "red", "stripes"), ("floor", "green", "dots")] or p["where"] == "floor", "its mind paints where and how it chooses: %s" % shop["painted"]
        music = room(h, cfg, pet, "music")
        pet["room"], pet["pos"] = music["id"], [5, 5]
        assert build.rugs(cfg, music) == ["rug"]
        actions.apply(h, cfg, pet, {"type": "paint", "where": "rug", "pattern": "like your coat"}, None)
        assert music["painted"] == [dict(music["painted"][0], where="rug", at="rug", color="pink", pattern="stripes")] and pet["carrying"] == [], "a rug can be painted: %s" % music["painted"]
        wants.refresh(h, cfg, pet)
        feel = lambda who: next((e for e in physics.effects(h, cfg, who) if e["tag"] == "painted"), None)
        stranger = grown(h, world.new_pet(h, cfg, music["id"], [3, 3], family=2))
        assert feel(pet)["rate"] > 0 and "feels like home" in feel(pet)["feel"], "a painted room is homely to the family that painted it"
        assert -0.1 < feel(stranger)["rate"] < 0 and "a little strange" in feel(stranger)["feel"], "and only a little strange to a stranger: %s" % feel(stranger)
        assert any("feels like home" in s for s in physics.senses(h, cfg, pet)), "it is among what it notices"
        stranger["carrying"] = ["black dye"]
        assert not body.targets(h, cfg, stranger, None, "paint", cfg["activities"]["paint"]) or body.targets(h, cfg, stranger, None, "paint", cfg["activities"]["paint"])[0]["job"][1] != "rug", "a body does not paint over another's fresh paint"

        # ---- paint fades unless it is done again ----
        fade = round(B["paint"]["fade_days"] * cfg["ticks_per_day"])
        h["tick"] += fade // 2
        assert 0.45 <= build.strength(h, cfg, music["painted"][0]) <= 0.55 and build.painted(h, cfg, music)[0]["strength"] == round(build.strength(h, cfg, music["painted"][0]), 2)
        pet["carrying"] = ["red dye"]
        t = body.targets(h, cfg, pet, None, "paint", cfg["activities"]["paint"])
        build.finish(eng.minds[pet["id"]], dict(t[0], name="paint"), cfg["activities"]["paint"])
        fresh = [q for q in music["painted"] if build.strength(h, cfg, q) == 1.0]
        assert len(fresh) == 1 and len(music["painted"]) == 2 - (fresh[0]["where"] == "rug"), "done again it is fresh: %s" % music["painted"]
        h["tick"] += fade // 2 + 10
        build.hourly(h, cfg)
        assert music["painted"] == fresh and feel(pet), "what was not done again has faded away"
        h["tick"] += fade
        build.hourly(h, cfg)
        assert music["painted"] == [] and feel(pet) is None and feel(stranger) is None, "and in the end all of it, and nothing of it is felt"

        # ---- a house from before all this loads, and nothing in it is the worse ----
        raw = json.loads((Path(d) / "a" / "house.json").read_text())
        for r in raw["rooms"].values():
            for k in ("painted", "rules", "leaked", "draught"):
                r.pop(k, None)
            for n in [n for n, o in r.get("objects", {}).items() if build.record(o)]:
                del r["objects"][n]
            r["spots"] = [s for s in r.get("spots", []) if "built" not in s]
        eng.close()
        (Path(d) / "old").mkdir()
        (Path(d) / "old" / "house.json").write_text(json.dumps(raw))
        old = Engine(cfg, d + "/old", scripted)
        for _ in range(30):
            await old.tick()
        assert all(physics.effects(old.house, cfg, p) is not None for p in old.house["pets"].values() if p["stage"] not in ("egg", "dead"))
        old.close()
    print("build check passed")


if __name__ == "__main__":
    asyncio.run(main())
