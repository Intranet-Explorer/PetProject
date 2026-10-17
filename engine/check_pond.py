"""Self-check for SPEC-v3.6a §8.1: the pond spreads without covering a door, the track or the platform, and what
stood in the water moves to its edge with nothing lost; hobs walk round the water; fishing follows the odds in
pond.toml by paw, with a rod and from the dock; the stock runs low and comes back; the pond freezes in deep winter
and a hole can be cut; finds are new things and rare ones are kept; a rod can be made and wears out; every everyday
kind can be made and has its use; a refusing family does not fish.
    uv run python -m engine.check_pond"""
import asyncio
import tempfile

from . import body, craft, hub, order, pond, rail, store, things
from .check import at, engine, load_config
from .check_machine import thing
from .world import generate_room

OLD = [[4, 3], [5, 3], [6, 3], [4, 4], [5, 4], [6, 4], [5, 5], [6, 5]]


class Mem:   # a mind's beliefs, as pond.refuses reads them
    def __init__(self, *said):
        self.said = [{"statement": s} for s in said]

    def active(self):
        return self.said


async def run(d):
    cfg = load_config()
    cfg["weather"]["real"] = False
    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    for rid in list(h["rooms"]):
        generate_room(h, cfg, rid)
    hub.migrate(h, cfg)
    at(eng, 10)
    store.lay(h, cfg)
    pet.update(name="Pim", stage="adult", sleep=None)
    P = cfg["pond"]
    room = pond.room_of(h, cfg)
    assert room, "a house has a pond room"

    # ---- the spread: an old small pond grows; what stood in the new water moves to its edge; nothing is lost ----
    pool = next(o for o in room["objects"].values() if "water" in o.get("fix", {}))
    pool["fix"]["water"] = [list(t) for t in OLD]
    room["objects"]["pond bridge"] = {"pos": [5, 4], "fix": {"built": {"project": "pond bridge"}}}
    room["objects"]["reed basket"]["pos"] = [8, 2]
    room["objects"]["shell bowl"] = thing(eng, room, "shell bowl", "bowl", "hard", pet["id"], days=1, pos=[4, 1])
    room["objects"]["reed toy"] = thing(eng, room, "reed toy", "ball", "springy", pet["id"], days=1, pos=[8, 2], on="reed basket")
    room["spots"].append({"bit": "shell", "pos": [7, 2], "ready": True, "back": None, "loose": False})
    rail.make(h, cfg)
    before = {n for n in room["objects"]}
    h["pond"] = None
    h.pop("pond")
    pond.spread(h, cfg)
    wet = {tuple(t) for t in P["pond"]["water"]}
    assert sorted(map(tuple, pool["fix"]["water"])) == sorted(wet), "the water is laid"
    assert set(room["objects"]) >= before, "nothing is lost"
    assert room["objects"]["pond bridge"]["pos"] == P["pond"]["bridge"][0], "the hobs' bridge lies across the neck"
    for n, o in room["objects"].items():
        if n not in ("pond bridge",) and o is not pool and not o.get("wall") and not o.get("on"):
            assert tuple(o["pos"]) not in wet, "nothing stands in the water: %s %s" % (n, o["pos"])
    assert room["objects"]["reed toy"]["pos"] == room["objects"]["reed basket"]["pos"], "what was in the basket went with it"
    assert all(tuple(s["pos"]) not in wet for s in room["spots"]), "no bits under the water"
    doors = {tuple(h["door_tiles"][d]) for d in room["doors"]}
    assert not wet & doors, "no door is under water"
    track = {tuple(t) for t in rail.on_track(h, room["id"])}
    assert not wet & track and tuple(h["rail"]["rooms"][room["id"]]["platform"]) not in wet, "the track and the platform stay dry"
    assert any(m["kind"] == "pond" and P["pond"]["spread"] in m["text"] for m in h["moments"]), "the story says so"
    assert any(P["pond"]["spread"] in e for _, e in pet["events"]), "and every hob is told"
    n_moments = len(h["moments"])
    pond.spread(h, cfg)
    assert len(h["moments"]) == n_moments, "once"

    # ---- hobs walk round the water: from the west door to the east door without a wet step ----
    pet["room"], pet["pos"] = room["id"], list(h["door_tiles"]["west"])
    goal, path = list(h["door_tiles"]["east"]), []
    for _ in range(40):
        pet["pos"] = pond.step(h, cfg, room, pet["pos"], goal)
        path.append(tuple(pet["pos"]))
        if pet["pos"] == goal:
            break
    assert pet["pos"] == goal and not set(path) & pond.wet(h, cfg, room), "round the water: %s" % path
    assert pond.step(h, cfg, room, [6, 1], [6, 4]) == [6, 2], "over the bridge"

    # ---- fishing: by paw, only common things, about one try in four ----
    pet["pos"] = [1, 3]
    A = cfg["activities"]["fish"]
    t = pond.targets(h, cfg, pet, Mem(), room, A)
    assert t and t[0]["where"] == "at the water's edge" and not t[0]["fish"]["rod"], t
    N, S = 4000, pond.state(h)
    rolls = []
    for i in range(N):
        S["stock"] = 12.0
        h["tick"] += 1
        rolls.append(pond.roll(h, cfg, pet, None, False))
    got = [c for c in rolls if c]
    assert abs(len(got) / N - P["odds"]["paw"]) < 0.03 and {c["tier"] for c in got} == {"common"}, (len(got) / N, {c["tier"] for c in got})
    # ... with a rod: about one in two, uncommon things too, but nothing rare off the dock
    rolls = []
    for i in range(N):
        S["stock"] = 12.0
        h["tick"] += 1
        rolls.append(pond.roll(h, cfg, pet, ("x", "rod"), False))
    got = [c for c in rolls if c]
    tiers = {k: sum(c["tier"] == k for c in got) / len(got) for k in ("common", "uncommon", "rare", "very rare")}
    assert abs(len(got) / N - P["odds"]["rod"]) < 0.03 and 0.1 < tiers["uncommon"] < 0.25 and tiers["rare"] == tiers["very rare"] == 0, tiers
    # ... from the dock with a rod: rare things, and now and then the very rare one
    rolls = []
    for i in range(N * 3):
        S["stock"] = 12.0
        h["tick"] += 1
        rolls.append(pond.roll(h, cfg, pet, ("x", "rod"), True))
    got = [c for c in rolls if c]
    tiers = {k: sum(c["tier"] == k for c in got) / len(got) for k in ("common", "uncommon", "rare", "very rare")}
    assert 0.015 < tiers["rare"] < 0.05 and 0 < tiers["very rare"] < 0.02, tiers
    # ... a fished-out pond gives no fish, and a thin one worse odds
    S["stock"] = 0.0
    assert not any(c and c.get("fish") for c in (pond.roll(h, cfg, pet, ("x", "rod"), False) for _ in range(300) if not h.update(tick=h["tick"] + 1))), "no fish in an empty pond"

    # ---- a catch lands: a fish in the paws, one fewer in the pond; the stock comes back over a world day ----
    m = eng.minds[pet["id"]]
    S["stock"] = 5.0
    pet["carrying"] = []
    now = {"fish": {"spot": [1, 3], "line": [2, 3], "rod": False, "catch": {"tier": "common", "what": "small fish", "bit": "fish", "fish": True}}, "of": 10, "where": "at the water's edge"}
    pet["needs"]["energy"] = 100
    told, fx, key = pond.landed(m, now)
    assert "small fish" in told and pet["carrying"] == ["fish"] and S["stock"] == 4.0 and S["today"][1] >= 1, (told, pet["carrying"], S)
    assert any(c["what"] == "small fish" for c in S["catches"]) and craft.skill(cfg, pet, "fishing") == 0 and pet["skill"]["fishing"] > 0
    S["stock"] = 0.0
    for _ in range(24):
        pond.hourly(h, cfg)
    assert S["stock"] == P["fish"]["most"], "full again in a world day: %s" % S["stock"]
    # ... a fish carried a world day goes off
    pet["caught_at"] = h["tick"] - cfg["ticks_per_day"]
    pond.hourly(h, cfg)
    assert "fish" not in pet["carrying"], "gone off"
    # ... eaten raw when hungry, unless the hob is too timid to eat it raw
    pet["needs"]["energy"] = 5
    pet["temper"]["bold"] = 0.8
    now["fish"]["catch"] = {"tier": "common", "what": "small fish", "bit": "fish", "fish": True}
    told, fx, key = pond.landed(m, now)
    assert "ate the fish raw" in told and fx.get("energy") == P["eat"]["fish"]["energy"], told
    assert h["pond_eaten"][-1][1] == pet["id"]

    # ---- the dock: built by the Works; fished from its end with a rod ----
    pond.build_dock(h, cfg, new=True)
    assert S["dock"]["end"] == P["dock"]["end"] and not any(tuple(t) in pond.wet(h, cfg, room) for t in S["dock"]["tiles"]), "walkable"
    rod = thing(eng, room, "fishing rod", "rod", "springy", pet["id"], days=1, pos=[10, 6])
    t = pond.targets(h, cfg, pet, Mem(), room, A)
    assert t and t[0]["where"] == "from the dock" and t[0]["fish"]["rod"] and t[0]["goal"] == S["dock"]["end"], t

    # ---- finds: new things, "from the pond"; a rare one kept for good, with a title and a line on the board ----
    pet["needs"]["energy"] = 100
    now = {"fish": {"spot": [3, 3], "line": [3, 2], "rod": True, "dock": True, "catch": next(dict(c) for c in P["catch"] if c["what"] == "lens")}, "of": 10, "where": "from the dock"}
    things_before = len(things.made(room))
    told, fx, key = pond.landed(m, now)
    lens = next(n for n, o in things.made(room).items() if o["made"]["recipe"]["kind"] == "lens")
    o = room["objects"][lens]
    assert len(things.made(room)) == things_before + 1 and o["made"]["found"]["from"] == "pond" and o["made"]["recipe"].get("title"), o
    assert order.kept(h, cfg, room, lens) and not order.scrap(h, cfg, room, lens), "kept, never scrap"
    assert h["feats"]["list"][-1]["kind"] == "find" and h["feats"]["list"][-1]["board"], h["feats"]["list"][-1]
    assert rod["made"].get("wear") == 1, "the rod wears with use"
    # ... the note in a bottle
    now["fish"]["catch"] = next(dict(c) for c in P["catch"] if c["tier"] == "very rare")
    told, fx, key = pond.landed(m, now)
    note = next(o for o in things.made(room).values() if o["made"]["recipe"]["kind"] == "note bottle")
    assert note["made"]["note"] in P["note"]["says"] and note["made"]["note"] in told and "A NOTE IN A BOTTLE" in h["feats"]["list"][-1]["board"]
    # ... the rod wears out
    rod["made"]["wear"] = craft.lasts(cfg, rod)
    assert not craft.tool_for(h, cfg, pet, "rod"), "worn out, it is no rod until mended"

    # ---- a rod can be made from a stick, string and a hook; everyday kinds can be made and have their uses ----
    pet["room"], pet["pos"] = room["id"], [10, 5]
    clean = lambda s, n=80: (s or "")[:n]
    for kind, K in cfg["kinds"].items():
        if K.get("invented") or kind in ("charm",):
            continue
        needs = [g.split("|")[0] for g in cfg["craft"].get("needs", {}).get(kind, [])]
        pet["carrying"] = needs + ["wood", "pebble", "fluff", "string", "wax", "shell"]
        mat = next((p for b in pet["carrying"] for p in cfg["house"]["bits"][b]["can"] if p not in K.get("not", [])), None)
        a = {"type": "make", "recipe": {"kind": kind, "material": mat, "color": "blue", "size": 1, "name": "Tester", "purpose": "a check"}}
        why = things.check_make(a, h, cfg, pet)
        if K.get("found"):
            assert why and "one might turn up" in why, "%s is only ever found: %s" % (kind, why)
            assert kind not in things.kinds_for(cfg, mat or "hard")
        elif kind in ("fork", "spoon", "knife", "plate", "kettle", "stick", "tube", "brush", "broom", "bucket", "torch", "needle", "wheel", "hook", "spring", "rod"):
            assert why is None, "%s can be made: %s" % (kind, why)
    pet["carrying"] = ["wood", "string", "hook"]
    a = {"type": "make", "recipe": {"kind": "rod", "material": "springy", "color": "brown", "size": 1, "name": "Long Line", "purpose": "to fish"}}
    assert things.check_make(a, h, cfg, pet) is None
    pet["carrying"] = ["wood", "string"]
    assert things.check_make(a, h, cfg, pet), "no rod without a hook (or wire)"
    knife = thing(eng, room, "little knife", "knife", "hard", pet["id"], days=1)
    assert craft.tool_kind(cfg, knife) == "carver", "a knife counts as a carver"
    torch = thing(eng, room, "torch", "torch", "warm", pet["id"], days=1)
    assert things.gives_light(cfg, torch), "a torch is a light"
    needs = {k for k, _, _ in things.room_needs(h, cfg, room)}
    assert "bucket" in needs, "the pond room could use a bucket"
    thing(eng, room, "pail", "bucket", "hard", pet["id"], days=1)
    assert any(ok(o) for k, ok, _ in things.room_needs(h, cfg, room) if k == "bucket" for o in room["objects"].values()), "and a bucket meets it"
    pet.pop("paw_fished", None)
    for r in h["rooms"].values():
        for n in [n for n, o in things.made(r).items() if o["made"]["recipe"]["kind"] == "rod"]:
            r["objects"].pop(n)
    assert not any("fish with" in line for line in things.better(h, cfg, pet)), "no rod offered before it has fished by paw"
    pet["paw_fished"], pet["offered"], lines = 2, {}, []
    for _ in range(8):
        lines += things.better(h, cfg, pet, mark=True)
        h["tick"] += cfg["ticks_per_day"]
    assert any("fish with" in line for line in lines), "once it has fished by paw, a rod is offered: %s" % lines

    # ---- the pond freezes in the coldest weeks; a hole is cut; fewer catches ----
    S["dock"] = None
    h["clock"]["season"] = "winter"
    span = cfg["house"]["house"]["season_days"]
    h["clock"]["day"] = round(span * 3.5) + 1 - cfg.get("season_off", 0)   # the middle of winter
    assert pond.frozen(h, cfg)
    pond.hourly(h, cfg)
    assert S["frozen"] and not pond.wet(h, cfg, room), "frozen over: the hobs can walk on the ice"
    t = pond.targets(h, cfg, pet, Mem(), room, A)
    assert t and t[0]["fish"].get("cut"), "a hole is cut first"
    told, fx, key = pond.landed(m, {"fish": t[0]["fish"], "of": 6})
    assert S["holes"] and pond.wet(h, cfg, room) == {tuple(S["holes"][0])}, "the hole is open water"
    t = pond.targets(h, cfg, pet, Mem(), room, A)
    assert t and t[0]["where"] == "through the hole in the ice" and t[0]["fish"]["line"] == S["holes"][0], t
    h["clock"]["season"] = "spring"
    pond.hourly(h, cfg)
    assert not S["frozen"] and not S["holes"]

    # ---- a refusing family does not fish ----
    assert not pond.targets(h, cfg, pet, Mem("We should never take the fish from the pond; let them be."), room, A)
    assert pond.targets(h, cfg, pet, Mem("The fish in the pond are good to eat."), room, A)
    # ... and fishing does not take over its day
    pet["fished"] = [h["clock"]["day"], cfg["pond"]["time"]["share"] * cfg["ticks_per_day"]]
    assert not pond.targets(h, cfg, pet, Mem(), room, A), "enough fishing for one day"

    # ---- the dock's place on the Works' list: next once the rail is built, after the goal being filled now ----
    from . import works
    W, L = works.state(h, cfg), cfg["works"]["build"]
    rail_at = next(i for i, b in enumerate(L) if b.get("rail"))
    W.update(goal=rail_at + 1, have=30, fed={}, front=None, built=[{"what": b["what"], "tick": 0, "by": []} for b in L[:rail_at + 1]])
    S["dock"] = None
    filling = works.goal(h, cfg)
    works.check(h, cfg)
    assert works.goal(h, cfg) is filling and W["have"] == 30, "what has been fed to the goal now is not lost to the dock"
    works.built(h, cfg, filling)
    assert works.goal(h, cfg)["what"] == "a dock for the pond", "then the dock is next: %s" % works.goal(h, cfg)
    after = L[W["goal"]]["what"]
    works.built(h, cfg, works.goal(h, cfg))
    assert S["dock"] and works.goal(h, cfg)["what"] == after, "built, and the list goes on where it was"

    # ---- the page gets the pond ----
    v = pond.view(h, cfg)
    assert v["room"] == room["id"] and len(v["water"]) == len(wet) and v["says"] in ("plenty of fish", "some fish", "fished thin")
    print("pond check passed")


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))


if __name__ == "__main__":
    main()
