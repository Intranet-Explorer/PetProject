"""Self-check for SPEC-v5.0 §1 and §6 (helper A, items): a use adds wear; past 1.0 a thing breaks and its verb fails
in words; a mend needs the part (and the hammer for a tool) and fixes it; a charge runs out and a refill fills it; a
container holds and its owner guards it, and its holds and its things' placement agree; a cool jar slows spoiling;
heat, cover and a lit light do what §1.4 says; a broken thing unmended three days is scrap; the migration on a copy of
the live house (read-only on the original), twice, gives the same house, and its clear-out is counted; with [v5]
off a stub day leaves no item or scrap keys and things.use is used as before. Stub houses, and the live copy.
    uv run python -m engine.check_items"""
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from . import contracts as K
from . import actions, health, invent, items, physics, things, verbs, world
from .check_brain4 import hob, house
from .check_machine import thing

LIVE = Path(os.environ.get("PET_LIVE_HOUSE") or Path(__file__).resolve().parent.parent / "data" / "house.json")   # (a worktree has no data/: name the live house)


def v5(cfg, on=True):
    cfg["v5"]["on"] = on
    cfg["items"]["on"] = True
    cfg["grammar"]["on"] = False   # (v5.0's check, on kinds.toml's hand verbs; the parser's is engine.check_grammar)


async def uses(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    room = h["rooms"][pet["room"]]
    lamp = thing(eng, room, "glass lantern", "lantern", "bright", pet["id"])
    lamp["state"] = "off"
    it = items.of(h, cfg, lamp, "glass lantern", room)
    assert it["verbs"] == {"light": 0.8} and it["class"] == "glass" and it["state"]["charge"] == {"oil": 6} and it["owner"] == pet["id"], it
    said, fx, key = verbs.apply(h, cfg, pet, "glass lantern")
    assert key and "lit" in said and it["state"]["lit"] and lamp["state"] == "on" and abs(it["state"]["wear"] - 0.03) < 1e-9 and it["state"]["charge"]["oil"] == 5, (said, it["state"])
    assert things.light_on(h, cfg, room) and items.strength(h, cfg, room, "light", True) == 0.8
    assert K.counts(h)["verbs"]["light"] == 1
    said, _, key = verbs.apply(h, cfg, pet, "glass lantern")
    assert key is None and "put out" in said and not it["state"]["lit"] and it["state"]["charge"]["oil"] == 5, "putting it out spends nothing"
    print("items: a use adds wear (%.2f) and spends one of six oil; putting it out spends nothing" % 0.03)
    # §1.6 a charge runs out; a refill fills it
    for _ in range(5):
        verbs.apply(h, cfg, pet, "glass lantern")
        items.switch(lamp, it, False)
    said, _, key = verbs.apply(h, cfg, pet, "glass lantern")
    assert key is None and said.endswith("it's empty") and not K.works(it, "light"), said
    assert not things.light_on(h, cfg, room) or not lamp["state"] == "on"
    pet["carrying"] = ["seed"]
    said, ok = verbs.refill(h, cfg, pet, "glass lantern")
    assert not ok and "it takes oil" in said, said
    pet["carrying"] = ["oil"]
    said, ok = verbs.refill(h, cfg, pet, "glass lantern")
    assert ok and it["state"]["charge"]["oil"] == 3 and not pet["carrying"] and K.works(it, "light"), (said, it["state"])
    print("items: six lightings empty the lantern (\"%s\"); a bit of oil poured in is three more" % "you tried the glass lantern; it's empty")
    # §1.5 past 1.0 it breaks; its verb fails in words
    it["state"]["wear"] = 0.99
    said, _, key = verbs.apply(h, cfg, pet, "glass lantern")
    assert it["state"]["broken"] and "it broke: the glass has cracked" in said and K.counts(h)["broke"]["lantern"] == 1, said
    items.switch(lamp, it, False)
    said, _, key = verbs.apply(h, cfg, pet, "glass lantern")
    assert key is None and said == "you tried the glass lantern; the glass has cracked", said
    assert K.works(it, "light") == 0 and not items.usable(cfg, lamp)
    print("items: past 1.0 it broke; then \"%s\"" % said)
    # a tool's mend needs the part and the hammer
    knife = thing(eng, room, "iron knife", "knife", "hard", pet["id"])
    knife["made"]["bits"] = ["metal"]
    kn = items.of(h, cfg, knife, "iron knife", room)
    kn["state"].update(wear=1.2, broken=True)
    pet["carrying"] = ["wood"]
    said, ok = verbs.mend(h, cfg, pet, "iron knife")
    assert not ok and "a bit of metal or a bit of wire" in said, said
    pet["carrying"] = ["wire"]
    said, ok = verbs.mend(h, cfg, pet, "iron knife")
    assert not ok and "hammer" in said, said
    thing(eng, room, "hammer", "hammer", "hard", pet["id"])
    said, ok = verbs.mend(h, cfg, pet, "iron knife")
    assert ok and not kn["state"]["broken"] and kn["state"]["wear"] == 0 and not pet["carrying"] and K.counts(h)["mended"]["knife"] == 1, said
    assert items.of(h, cfg, room["objects"]["hammer"], "hammer", room)["state"]["wear"] > 0, "the hammer wore"
    print("items: a broken knife takes a bit of metal or wire and the hammer: \"%s\"" % said)
    # §1.4 cover, heat, light at night
    h["clock"]["phase"] = "night"
    blanket = thing(eng, room, "wool blanket", "blanket", "soft", pet["id"])
    blanket["pos"] = list(pet["pos"])
    pet["sleep"] = True
    assert items.covered(h, cfg, pet) == 0.8
    assert any(e["tag"] == "cover" for e in physics.effects(h, cfg, pet)), "a sleeper under a blanket at night is warm"
    pet["sleep"] = False
    print("items: a sleeper under the blanket has cover %.1f, and is warm at night" % items.covered(h, cfg, pet))
    return eng, pet


async def containers(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    room = h["rooms"][pet["room"]]
    other = hob(eng, room, [pet["pos"][0] + 1, pet["pos"][1]])
    other["name"] = "Antonia"
    thing(eng, room, "oak chest", "chest", "hard", other["id"])
    cup = thing(eng, room, "red cup", "cup", "hard", None)   # (nobody's: anyone may move it, but not into or out of another's chest)
    said = items.put(h, cfg, pet, "red cup", "oak chest")
    assert said == "the oak chest is Antonia's and it's shut" and "on" not in cup, said
    said = items.put(h, cfg, other, "red cup", "oak chest")
    chest = items.of(h, cfg, room["objects"]["oak chest"], "oak chest", room)
    assert said.startswith("you put the red cup") and cup["on"] == "oak chest" and chest["state"]["holds"] == [str(cup["made"]["id"])], (said, chest["state"])
    assert items.of(h, cfg, cup, "red cup", room)["where"] == {"in": str(room["objects"]["oak chest"]["made"]["id"])}
    from . import order
    assert order.check({"type": "take_out", "what": "red cup"}, h, cfg, pet, lambda s: s) == "the oak chest is Antonia's and it's shut"
    said = items.take_out(h, cfg, pet, "oak chest", str(cup["made"]["id"]))
    assert said == "the oak chest is Antonia's and it's shut" and cup.get("on") == "oak chest", said
    said = items.take_out(h, cfg, other, "oak chest", "red cup")
    assert "took the red cup out" in said and "on" not in cup and chest["state"]["holds"] == [], (said, chest["state"])
    # holds and placement agree, whoever moves it (order.put, the evening's v4 paths, a thing eaten)
    order.put(h, cfg, other, room, "red cup", "on", "oak chest")
    assert chest["state"]["holds"] == [str(cup["made"]["id"])]
    order.moved(cup, h["tick"], h, cfg, room, "red cup")
    assert chest["state"]["holds"] == [] and "on" not in cup
    order.put(h, cfg, other, room, "red cup", "on", "oak chest")
    del room["objects"]["red cup"]
    items.sync(h, cfg)
    assert chest["state"]["holds"] == [], "a thing gone from the room is gone from what held it"
    print("items: the oak chest is Antonia's: nobody else puts in or takes out (\"the oak chest is Antonia's and it's shut\"); its holds follow every move")
    # a store keeps the mouse out; a carry tool tidies in one trip
    from . import director
    treat = thing(eng, room, "honey treat", "treat", "sweet", other["id"])
    order.put(h, cfg, other, room, "honey treat", "on", "oak chest")
    assert director.shut_in(h, cfg, room, treat)
    for i in range(5):
        room["spots"].append({"bit": "pebble", "pos": [1 + i, 6], "ready": True, "back": None, "loose": True, "since": h["tick"]})
    thing(eng, room, "reed broom", "broom", "soft", pet["id"])
    loose = len(order.loose_bits(room))
    said, _, key = verbs.apply(h, cfg, pet, "reed broom")
    assert key == "carry" and not order.loose_bits(room) and "%d loose bits in one trip" % loose in said, said
    print("items: a treat in the chest is shut in from the mouse; \"%s\"" % said)


async def spoiling(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    cfg["spirit"]["on"] = cfg["deaths"]["on"] = cfg["health"]["on"] = True
    assert health.deaths(cfg)
    room = h["rooms"][pet["room"]]
    thing(eng, room, "clay jar", "jar", "cool", pet["id"])
    thing(eng, room, "pine shelf", "shelf", "hard", pet["id"])
    for on in ("clay jar", "pine shelf"):
        room["spots"].append({"bit": "berry", "pos": list(room["objects"][on]["pos"]), "ready": True, "back": None, "loose": True, "on": on, "since": h["tick"], "put": h["tick"]})
    days = cfg["deaths"]["spoil_days"] * cfg["ticks_per_day"]
    h["tick"] += days + 1
    health.spoil(h, cfg, room)
    jar, shelf = [next(s for s in room["spots"] if s.get("on") == on) for on in ("clay jar", "pine shelf")]
    assert shelf.get("spoiled") and not jar.get("spoiled"), "past spoil_days the shelf's berry has spoiled, the jar's not"
    h["tick"] += days
    health.spoil(h, cfg, room)
    assert jar.get("spoiled"), "at twice spoil_days the jar's has"
    print("items: a berry in the cool jar keeps twice as long as one on the shelf (%s world days)" % (2 * cfg["deaths"]["spoil_days"]))
    # §1.5 a broken thing unmended three days is scrap
    cup = thing(eng, room, "old cup", "cup", "hard", pet["id"])
    it = items.of(h, cfg, cup, "old cup", room)
    it["state"].update(wear=1.1, broken=True)
    it["broke"] = h["tick"]
    h["tick"] += cfg["items"]["scrap_after_days"] * cfg["ticks_per_day"]
    h["tick"] += -h["tick"] % round(cfg["ticks_per_hour"])   # (looked at on the hour)
    items.tick(h, cfg)
    assert "old cup" not in room["objects"] and h["gone_things"][-1]["name"] == "old cup" and "never mended" in h["gone_things"][-1]["gone"][1]
    assert any(m["kind"] == "scrap" and "old cup" in m["text"] for m in h["moments"])
    print("items: a cup broken %d days and never mended went to the Works as scrap" % cfg["items"]["scrap_after_days"])


def migration(d):
    if not LIVE.exists():
        print("items: no live house here to migrate a copy of (skipped)")
        return
    shutil.copy(LIVE, Path(d) / "house.json")   # (the original is only read)
    cfg = world.load_config(profile="live")
    v5(cfg)
    out = []
    for runs in (1, 2):
        h = json.loads((Path(d) / "house.json").read_text())
        invent.install(h, cfg)
        lines = items.migrate(h, cfg)
        if runs == 2:
            assert items.migrate(h, cfg) == [], "once a house"
        out.append((json.dumps(h, sort_keys=True), lines))
    assert out[0] == out[1], "the migration run twice gives the same house"
    h = json.loads(out[0][0])
    assert all("item" in o for r in h["rooms"].values() if r["type"] for o in r["objects"].values() if "made" in o)
    assert all("scrap" in p for p in h["pets"].values())
    for l in out[0][1]:
        print("items: migration (live copy): %s" % l)
    print("items: the migration on a copy of the live house, run twice, gives the same house")


async def off(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    assert not K.on5(cfg, "items")
    room = h["rooms"][pet["room"]]
    thing(eng, room, "blue cushion", "cushion", "soft", pet["id"])
    was, seen = verbs.apply, []
    verbs.apply = lambda *a, **k: seen.append(a)
    try:
        said, fx, key = actions.use(h, cfg, pet, "blue cushion")
        for _ in range(cfg["ticks_per_day"]):
            await eng.tick()
    finally:
        verbs.apply = was
    await asyncio.sleep(0)
    assert not seen and fx.get("comfort") and said.startswith("you used"), "off: things.use, as before"
    assert not any("item" in o for r in h["rooms"].values() if r["type"] for o in r["objects"].values()), "off: no item keys"
    assert not any("scrap" in p for p in h["pets"].values()) and "v50_items" not in h.get("migrated", {})
    print("items: off, a stub day leaves no item or scrap keys, and a use is things.use's (\"%s\")" % said)


async def on_day(d):
    """[v5] on: a stub day through the whole engine migrates once, raises nothing, and every item's mirrors agree."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    v5(cfg)
    room = h["rooms"][pet["room"]]
    thing(eng, room, "blue cushion", "cushion", "soft", pet["id"])
    for _ in range(cfg["ticks_per_day"]):
        await eng.tick()
    await asyncio.sleep(0)
    assert h["migrated"].get("v50_items") and (Path(d) / "migration-v5.0.txt").exists()
    assert not getattr(eng, "step_errors", {}), eng.step_errors
    bad = [(n, o["item"]["owner"], o["made"]["owner"]) for r in h["rooms"].values() if r["type"] for n, o in r["objects"].items()
           if "item" in o and "made" in o and (o["item"]["owner"] != o["made"]["owner"] or o["item"]["maker"] != o["made"]["by"])]
    assert not bad, bad
    for r in [r for r in h["rooms"].values() if r["type"]]:
        for n, o in r["objects"].items():
            if "item" in o:
                inside = sorted(items.ident(r, x, y) for x, y in r["objects"].items() if y.get("on") == n)
                assert sorted(o["item"]["state"]["holds"]) == inside or not inside and not o["item"]["state"]["holds"], (n, o["item"]["state"]["holds"], inside)
    print("items: on, a stub day migrates once, raises nothing, and owner, maker and holds agree on every item")


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(uses(d + "/u"))
        asyncio.run(containers(d + "/c"))
        asyncio.run(spoiling(d + "/s"))
        os.makedirs(d + "/m")
        migration(d + "/m")
        asyncio.run(off(d + "/o"))
        asyncio.run(on_day(d + "/d"))
    print("check_items: all passed")


if __name__ == "__main__":
    main()
