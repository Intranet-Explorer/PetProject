"""Self-check for SPEC-v3.6c §6.1: the clear-out keeps everything kept and never touches a stone, a memory shelf, a
machine or what is in use; nothing is ever set down in a room's middle; the population grows to seven and waits while
the model is busy; a season for something new starts, ranks its wants and ends; hobs go out by day and come in at dusk
and before storms; little ones go out only with a grown hob; outdoor bits regrow and nothing piles up.
    uv run python -m engine.check_v36c"""
import asyncio
import tempfile

from . import clearout, director, floors, life, order, outdoors, spotlight, store, things, wants
from .check import at, engine, load_config
from .check_build import put_up
from .check_machine import thing
from .world import generate_room, new_pet


async def run(d):
    cfg = load_config()
    cfg["weather"]["real"] = False
    cfg["packet"]["trim"] = cfg["clearout"]["floors"] = True   # (the older checks run with these off ...)
    cfg["population"] = dict(__import__("engine.world", fromlist=["x"]).load_config()["population"])   # (... and with v3's four, no guard, no founder egg)
    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    at(eng, 10)
    pet.update(stage="adult", name="Oya")
    nursery = h["rooms"][pet["room"]]
    rooms = {}
    for kind in ("storeroom", "workshop", "garden", "attic", "cellar"):
        rid = next(r for r, x in sorted(h["rooms"].items()) if not x["type"] and (kind != "garden" or x["cell"][1] == 2))
        rooms[kind] = generate_room(h, cfg, rid, kind)
    shop, garden, attic = rooms["workshop"], rooms["garden"], rooms["attic"]
    store.lay(h, cfg)
    names = iter(range(1, 999))

    def mk(room, kind, material):
        name = "%s %d" % (kind, next(names))
        thing(eng, room, name, kind, material, pet["id"])
        return name

    # ---- nothing is ever set down in the middle of a room ----
    n = mk(attic, "cup", "hard")
    attic["objects"][n]["pos"] = [5, 3]
    assert floors.middle(cfg, [5, 3]) and not floors.middle(cfg, [1, 3]) and not floors.middle(cfg, [5, 6])
    order.upkeep(h, cfg)
    o = attic["objects"][n]
    assert o.get("on") or not floors.middle(cfg, o["pos"]), "a thing in the middle goes to its nearest good spot: %s" % o
    rug = mk(attic, "rug", "soft")
    attic["objects"][rug]["pos"] = [6, 3]
    order.upkeep(h, cfg)
    assert attic["objects"][rug]["pos"] == [6, 3], "a rug is for the middle"
    assert not any(floors.in_middle(h, cfg).values()), floors.in_middle(h, cfg)
    box = mk(attic, "crate", "hard")
    attic["objects"][box]["pos"] = [1, 4]
    cup2 = mk(attic, "cup", "hard")
    attic["objects"][cup2]["pos"] = [3, 4]
    order.upkeep(h, cfg)
    assert attic["objects"][cup2].get("on") == box, "a box near by with room comes before a tile by the wall: %s" % attic["objects"][cup2]
    assert all(t not in [p for p in floors.door_path(h, cfg, attic)] for t in [floors.spot(h, cfg, attic, [7, 4])]), "and never in a doorway's path"

    # ---- the clear-out keeps everything kept; never a stone, a memory shelf, a machine or what is in use ----
    at(eng, 10, h["clock"]["day"] + 2)
    keep = mk(attic, "bowl", "hard")
    attic["objects"][keep]["made"]["first"] = True
    charm = mk(attic, "charm", "hard")
    used = mk(attic, "spoon", "hard")
    for x in (keep, charm, cup2):
        attic["objects"][x]["made"]["touched"] = attic["objects"][x]["made"]["tick"] = attic["objects"][x]["made"]["used_at"] = h["tick"] - 2 * cfg["ticks_per_day"]
    attic["objects"]["stone for Pip"] = {"pos": [2, 7], "memorial": {"pet": "p99"}}
    attic["objects"]["memory shelf"] = {"pos": [10, 0], "fix": {"memory": True, "store": 6}}
    kiln, _ = put_up(h, cfg, pet, shop, "kiln")
    pet["plan"] = {"steps": [{"type": "use", "target": used}], "i": 0, "intention": "use it"}
    h.pop("clearout", None)   # (a new house had nothing to clear when it was made)
    clearout.migrate(h, cfg)
    p = h["clearout"]["plan"]
    assert p[attic["id"]].get(keep) == "store" and p[attic["id"]].get(charm) == "works", p[attic["id"]]
    for x in ("stone for Pip", "memory shelf", used, rug):
        assert x not in p[attic["id"]], "%s stays" % x
    assert kiln not in p[shop["id"]], "a machine stays"
    pet["plan"] = None
    h["tick"] = h["clearout"]["until"]
    clearout.tick(h, cfg)
    assert h["clearout"]["done"] and keep not in attic["objects"] and any(keep == n for n in things.made(h["rooms"][store.RID])), "the kept bowl is in the store"
    assert not any(g["name"] == keep for g in h.get("gone_things", [])), "nothing kept is lost"
    assert any(g["name"] == charm for g in h.get("gone_things", [])), "the old charm went to the Works"
    assert any(m["kind"] == "clearout done" and "to the store" in m["text"] for m in h["moments"]), "and the story says so"
    assert "stone for Pip" in attic["objects"] and "memory shelf" in attic["objects"] and kiln in shop["objects"] and used in attic["objects"]

    # ---- seasons for new things ----
    spotlight.migrate(h, cfg)   # (a new house has had it since it was made)
    st = h["spotlights"]
    assert [s["key"] for s in st["on"]][:1] == ["kiln"] and not any(s["key"] == "designing" for s in st["on"] + st["queue"]), st   # (SPEC-v5.1 §4.5: designing has no season)
    w = {"what": "build", "project": "kiln", "key": "build:x|kiln"}
    assert spotlight.boost(h, cfg, w) == cfg["spotlight"]["boost"] and spotlight.boost(h, cfg, {"what": "plant"}) == 1.0, "its wants rank above routine ones"
    assert any(m["kind"] == "spotlight" and "kiln" in m["text"] for m in h["moments"]), "announced"
    other = new_pet(h, cfg, nursery["id"], [3, 3])
    other.update(stage="adult", laid=-10 ** 6, born=0)
    spotlight.tried(h, cfg, "kiln", pet)
    assert spotlight.on(h, "kiln")
    spotlight.tried(h, cfg, "kiln", other)
    assert not spotlight.on(h, "kiln"), "two have tried it: it ends"
    spotlight.queue(h, cfg, "mill", "THE MILL", "the mill", nursery["id"], None)   # (the place designing's season had)
    assert any("something new" in e for _, e in pet["events"]) and "event" in other["news"], "something new: every hob is told"
    spotlight.queue(h, cfg, "loom", "THE LOOM", "the loom", nursery["id"], None)
    assert len(st["on"]) == cfg["spotlight"]["most"] and any(s["key"] == "loom" for s in st["queue"]), "two at once at most: the loom waits its turn"
    assert len(st["on"]) <= cfg["spotlight"]["most"]
    h["tick"] += round(cfg["spotlight"]["days"] * cfg["ticks_per_day"]) + 1
    spotlight.tick(h, cfg)
    assert all(s["ended"] for s in st["done"]), "three world days at most"

    # ---- outdoors ----
    assert outdoors.migrate(h, cfg), "the yard and the meadow are hung on behind the garden"
    yard, meadow = h["rooms"]["ryard"], h["rooms"]["rmeadow"]
    assert yard["outdoor"] and meadow["outdoor"] and garden["doors"]["south"] == "ryard" and yard["doors"]["north"] == garden["id"]
    at(eng, 11)
    h["weather"] = "clear"
    outdoors.gate(h, cfg)
    pet.update(room=garden["id"], pos=[7, 6], sleep=None)
    assert h["outdoors"]["open"] and outdoors.barred(h, cfg, pet, garden["id"], "south") is None, "by day, in fair weather, the gate is open"
    kid = new_pet(h, cfg, garden["id"], [6, 6])
    kid.update(stage="child", laid=-10 ** 6, born=0, sleep=None)
    pet.update(room=nursery["id"])
    other.update(room=nursery["id"])
    assert outdoors.barred(h, cfg, kid, garden["id"], "south"), "a little one does not go out alone"
    pet.update(room="ryard", pos=[7, 1])
    assert outdoors.barred(h, cfg, kid, garden["id"], "south") is None, "with a grown one out there, it may"
    kid.update(room="ryard", pos=[6, 1])
    outdoors.tick(h, cfg)
    assert not outdoors.come_in(h, cfg, kid) and any(s["key"] == "outdoors" and pet["id"] in s["tried"] for s in st["on"] + st["done"] + st["queue"]) or not st["on"]
    pet.update(room=nursery["id"])
    assert outdoors.come_in(h, cfg, kid), "no grown one out there: the little one comes in"
    pet.update(room="ryard")
    h["weather"] = "storm"
    outdoors.gate(h, cfg)
    assert not h["outdoors"]["open"] and outdoors.come_in(h, cfg, pet) and outdoors.barred(h, cfg, other, garden["id"], "south"), "a storm: the gate shuts and everyone comes in"
    out = {"rooms": set(), "doors": set()}
    outdoors.lean(h, cfg, pet, out)
    assert out["rooms"] == {garden["id"]}, "its body heads for the gate"
    h["weather"] = "clear"
    at(eng, 21)
    outdoors.tick(h, cfg)
    h["tick"] += outdoors.hours(cfg, cfg["outdoors"]["in_hours"]) + 1
    outdoors.tick(h, cfg)
    assert pet["room"] == garden["id"] and kid["room"] == garden["id"], "at dusk everyone out is in before long"
    assert h["clock"]["phase"] in ("dusk", "night") and not h["outdoors"]["open"]

    # ---- outdoor bits regrow; nothing piles up ----
    s = next(s for s in yard["spots"] if s["ready"])
    s["ready"], s["back"] = False, h["tick"] + 5
    h["tick"] += 6
    director.hourly(h, cfg)
    assert s["ready"], "forage grows back"
    yard["spots"].append({"bit": "pebble", "pos": [3, 3], "ready": True, "back": None, "loose": True, "since": h["tick"] - cfg["ticks_per_day"] - 1})
    outdoors.weather_away(h, cfg)
    assert not any(s["bit"] == "pebble" for s in yard["spots"]), "a bit dropped outdoors weathers away in a day"
    left = mk(yard, "ball", "bouncy")
    at(eng, 19, h["clock"]["day"] + 1)
    h.pop("tidied", None)
    floors.tidy(h, cfg)
    assert left not in yard["objects"] and any(left == n for n in things.made(h["rooms"][store.RID])) and any(m["kind"] == "tidy" for m in h["moments"]), \
        "what is left out goes in with the evening tidy, in one line"

    # ---- the trimmed thought ----
    from . import mind
    from .brains import model
    pet.update(room=attic["id"], sleep=None)
    pet["stage_at"].setdefault("adult", h["tick"])
    for i in range(30):
        mk(attic, "cup", "hard")
    mem = eng.minds[pet["id"]].mem
    cfg["body"]["on"] = True   # (as on the live house: the short steps are the body's reply)
    cfg["packet"]["trim"] = False
    full, fctx = mind.perceive(h, cfg, pet, mem)
    cfg["packet"]["trim"] = True
    short, sctx = mind.perceive(h, cfg, pet, mem)
    assert "you can:" in full and "you can:" not in short and "more things further off" in short, "the nearest few things, and no 'you can' line"
    assert len(model.prompt(short, sctx)) < 0.7 * len(model.prompt(full, fctx)), (len(model.prompt(short, sctx)), len(model.prompt(full, fctx)))
    sch = model.schema(sctx)
    assert sch["properties"]["thought"]["maxLength"] == cfg["packet"]["reply_thought"] and sch["properties"]["expect"]["maxLength"] == cfg["packet"]["reply_expect"], "and a shorter reply"
    assert set(sctx["things"]) == set(fctx["things"]), "every thing here can still be named in a step"
    cfg["body"]["on"] = False

    # ---- seven hobs, and a guard on the model ----
    Pop = cfg["population"]
    for p in list(h["pets"].values()):
        p["family"] = 1
    while len(life.alive(h)) < Pop["most"] - 1:
        x = new_pet(h, cfg, nursery["id"], [2, 2], family=2)
        x.update(stage="adult", laid=-10 ** 6, born=0)
    assert not life.full(h, cfg, pet), "room for a seventh"
    h["busy"] = [[h["tick"], cfg["ticks_per_hour"] * cfg["clock"]["tick_seconds"] * cfg.get("pace", 1) * 0.9]]
    assert life.full(h, cfg, pet), "the model busy more than 85% of the last world hour: no egg"
    assert life.founder(h, cfg) is None
    h["busy"] = []
    h["room_since"] = h["tick"] - life.hours(cfg, Pop["found_hours"]) - 1
    for p in h["pets"].values():
        p["laid"] = min(p["laid"], h["tick"] - life.hours(cfg, Pop["found_hours"]) - 1)
        p["eggs"] = 3   # (19 October 2026: an egg turns up only when no grown hob has one left in it; engine/check_lineage.py)
    h["tick"] = (h["tick"] // life.hours(cfg, 1) + 1) * life.hours(cfg, 1)
    egg = life.founder(h, cfg)
    assert egg and egg["stage"] == "egg" and len(life.alive(h)) == Pop["most"], "an egg turns up: seven"
    assert life.full(h, cfg, pet) and life.founder(h, cfg) is None, "and then the house is full"
    # ---- every switch turns its part fully off (REVIEW-code.md) ----
    from . import design
    spotlight.queue(h, cfg, "stove", "THE STOVE", "the stove", nursery["id"], None)
    on_now = [s["key"] for s in st["on"]]
    assert on_now, st
    cfg["spotlight"]["on"] = False
    spotlight.tick(h, cfg)
    assert not any(spotlight.on(h, k) for k in on_now) and spotlight.boost(h, cfg, {"what": "build", "project": on_now[0]}) == 1.0 \
        and spotlight.near(h, cfg, pet) is None, "seasons off: nothing is in season, whatever was"
    tried_before = [list(s["tried"]) for s in st["on"]]
    spotlight.tried(h, cfg, on_now[0], other)
    assert [list(s["tried"]) for s in st["on"]] == tried_before, "and nothing counts as tried"
    cfg["spotlight"]["on"] = True
    spotlight.tick(h, cfg)
    assert spotlight.on(h, st["on"][0]["key"]), "on again, the seasons go on"
    cfg["outdoors"]["on"] = False
    h["creatures"].append({"id": "cx", "kind": "rabbit", "room": "ryard", "pos": [3, 3], "nest": [3, 3], "doing": "", "since": 0, "until": 10 ** 9, "fed": {}, "carry": None, "trust": {}, "tame": None, "name": None})
    st["on"].append({"key": "outdoors", "title": "T", "what": "the yard", "room": "ryard", "thing": None, "after": None, "since": h["tick"], "until": h["tick"] + 10, "tried": [], "ended": None})
    pet.update(room="ryard", pos=[5, 3], sleep=None)
    at(eng, 11)
    h["weather"] = "clear"
    outdoors.tick(h, cfg)
    assert not h["outdoors"]["open"] and outdoors.barred(h, cfg, other, garden["id"], "south") and outdoors.come_in(h, cfg, pet), "outdoors off: the gate stays shut, and whoever is out comes in"
    assert not any(c["room"] in outdoors.OUT for c in h["creatures"]) and not spotlight.on(h, "outdoors"), "no creatures out there, and the yard's season is over"
    fresh = {"rooms": {"r22": {"type": "garden", "cell": [2, 2], "doors": {}}}}
    assert not outdoors.migrate(fresh, cfg), "and a house without a yard is not given one"
    cfg["outdoors"]["on"] = True
    pet.update(room=nursery["id"])
    h["clearout"] = {"at": h["tick"], "until": h["tick"], "done": None, "to_store": 0, "to_works": 0, "plan": {attic["id"]: {}}, "moved": {}, "planned": {}}
    cfg["clearout"]["on"] = False
    clearout.tick(h, cfg)
    assert not h["clearout"]["done"], "clear-out off: one under way stands still"
    cfg["clearout"]["on"] = True
    clearout.tick(h, cfg)
    assert h["clearout"]["done"], "and on again, it finishes"
    cfg["design"]["on"] = False
    assert design.buy_back(h, cfg, {"id": 1}) == "buying back is switched off", "[design] off: no buying back"
    cfg["design"]["on"] = True

    # ---- a house step that throws is skipped for the tick, and the clock goes on (REVIEW-code.md) ----
    real = spotlight.tick

    def broken(house, cfg):
        raise RuntimeError("a broken step")
    spotlight.tick = broken
    try:
        t0 = h["tick"]
        await eng.tick()
        await eng.tick()
        assert h["tick"] == t0 + 2 and eng.step_errors["spotlight.tick"][0] == t0, "a step that throws is logged and skipped, and the tick advances"
    finally:
        spotlight.tick = real
    lone = [p for p in life.alive(h) if p["family"] == 1]
    print("v3.6c: clear-out %s; spotlights %s; gate %s; population %d" % ({k: h["clearout"][k] for k in ("to_store", "to_works")},
          [s["key"] for s in st["done"]], h["outdoors"], len(life.alive(h))))


def main():
    with tempfile.TemporaryDirectory(dir=__import__("os").environ.get("PET_SCRATCH")) as d:   # (anywhere: PET_SCRATCH when set, else the system's)
        asyncio.run(run(d))
    print("v3.6c check passed")


if __name__ == "__main__":
    main()
