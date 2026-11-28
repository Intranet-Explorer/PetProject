"""Self-check for SPEC-v3.5.12 §6.1: the route reaches every room and reverses at the dead ends; the train stops,
waits for hobs and never stands across a door; what is put on it arrives on the right shelf; what is asked for is
delivered; the room caps hold; nothing kept is lost; a new death puts the stone in the resting place and the box on
its family's shelf in the attic. And SPEC-v5.3.2 §2: the same again with [wallrail] on, the train through the walls.
    uv run python -m engine.check_rail"""
import asyncio
import tempfile

from . import life, order, rail, resting, store, things
from .check import at, engine, load_config
from .check_machine import thing
from .world import generate_room


def run_train(h, cfg, tr, ticks, seen=None):
    """Step the train alone (the house's clock moving with it), noting each stop and where its cars stood."""
    for _ in range(ticks):
        h["tick"] += 1
        rail.step(h, cfg, tr)
        if seen is not None and tr["stopped"] and tr.get("arrived") == h["tick"]:
            seen.append((tr["room"], [dict(c) for c in tr["cars"] if c]))


async def run(d):
    cfg = load_config()
    cfg["weather"]["real"] = False
    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    for rid in list(h["rooms"]):
        generate_room(h, cfg, rid)
    from . import hub
    hub.migrate(h, cfg)
    at(eng, 9)
    store.lay(h, cfg)
    resting.migrate(h, cfg)
    pet.update(name="Pim", stage="adult")

    # ---- the route: every room, out and back along the dead ends ----
    rail.make(h, cfg)
    tr, R = rail.train(h), h["rail"]
    rooms = {rid for rid, r in h["rooms"].items() if r["type"]}
    assert tr and set(R["route"]) == rooms and set(R["rooms"]) == rooms, (R["route"], rooms)
    for leg in R["legs"][1:-1]:
        if len(h["rooms"][leg["room"]]["doors"]) == 1 or leg["in"] == leg["out"]:
            assert leg["in"] == leg["out"] and R["rooms"][leg["room"]]["buffer"], "a dead end is ridden in and backed out of: %s" % leg
    assert sum(leg["stop"] for leg in R["legs"]) == len(rooms), "one stop a room a round (the depot at the end)"
    for rid, x in R["rooms"].items():
        room, cells = h["rooms"][rid], [tuple(t) for a in x["arms"].values() for t in a[1:-1]]
        assert len(cells) == len(set(cells)), "the arms share only the platform: %s" % rid
        assert all(len(a) >= cfg["house"]["rail"]["clear"] + 1 for a in x["arms"].values()), "long enough to stand clear of a door: %s" % rid
        fixed = {tuple(o["pos"]) for o in room["objects"].values() if "fix" in o and not o.get("wall") and not o.get("on") and not o["fix"].get("platform")}
        assert not set(cells) & fixed, "the track never crosses a fixture: %s %s" % (rid, set(cells) & fixed)

    # ---- a round: it stops in every room, and never across a door ----
    seen = []
    run_train(h, cfg, tr, 500, seen)
    doors = {tuple(t) for t in h["door_tiles"].values()}
    assert {r for r, _ in seen} == rooms, "it stopped in every room: %s" % sorted({r for r, _ in seen})
    assert all(tuple(c["pos"]) not in doors for _, cs in seen for c in cs), "never stopped across a door: %s" % seen
    assert h["rail"]["rounds"] >= 1 and any(c["what"] == "finished a round" for c in h["fresh_creatures"])

    # ---- a hob on the track: it waits, rings, and the hob steps aside ----
    while not (not tr["stopped"] and tr["path"] and len(tr["path"]) > 3 and tr["room"] == rail.train(h)["room"]):
        run_train(h, cfg, tr, 1)
    room = h["rooms"][tr["room"]]
    pet["room"], pet["pos"], pet["sleep"] = room["id"], list(tr["path"][0]), None
    was = list(tr["trail"][0][1])
    run_train(h, cfg, tr, 1)
    assert tr["trail"][0][1] == was and tr["bell"] == h["tick"] and "waiting" in tr["doing"], "it stops short and rings: %s" % tr["doing"]
    run_train(h, cfg, tr, cfg["house"]["rail"]["wait_ticks"] + 2)
    assert tuple(pet["pos"]) not in rail.on_track(h, room["id"]) and tr["trail"][0][1] != was, "the hob stepped aside and the train went on"

    # ---- what is put on it arrives on the right shelf ----
    while not (tr["stopped"] and tr["room"] not in (store.RID, R["depot"])):
        run_train(h, cfg, tr, 1)
    room = h["rooms"][tr["room"]]
    pet["room"], pet["pos"] = room["id"], list(R["rooms"][room["id"]]["platform"])
    thing(eng, room, "blue cushion", "cushion", "soft", None, days=5)
    thing(eng, room, "keep box", "box", "hard", None, days=5)
    thing(eng, room, "old bell", "bell", "noisy", None, days=5, on="keep box")
    assert "blue cushion" in store.out_of_place(h, cfg, room) or store.belongs(cfg, room).get("cushion"), "an old cushion goes, unless the room keeps it"
    assert "old bell" not in store.out_of_place(h, cfg, room) and "keep box" in store.out_of_place(h, cfg, room), "a box with something in it counts as one"
    assert rail.put_on(h, cfg, pet, room, "blue cushion") and rail.put_on(h, cfg, pet, room, "keep box"), "into the cart while it stands here"
    assert {"blue cushion", "keep box", "old bell"} <= set(tr["cargo"]), tr["cargo"]
    run_train(h, cfg, tr, 400)
    S = h["rooms"][store.RID]
    assert S["objects"].get("blue cushion", {}).get("on") == "cushion shelf" and S["objects"]["old bell"]["on"] == "cubbies", "on the right shelves"
    assert store.where(h, cfg, S, "blue cushion") == ("in the store, on the cushion shelf", True)
    # ... and left on the platform, it is collected
    while not (tr["stopped"] and tr["room"] not in (store.RID, R["depot"])):
        run_train(h, cfg, tr, 1)
    while tr["stopped"]:
        run_train(h, cfg, tr, 1)
    room = h["rooms"][tr["room"]]
    pet["room"] = room["id"]
    thing(eng, room, "felt lamp", "lamp", "warm", None, days=5)
    assert rail.put_on(h, cfg, pet, room, "felt lamp") == "on the platform, for the train" and room["objects"]["felt lamp"]["on"] == "platform"
    run_train(h, cfg, tr, 700)
    assert S["objects"].get("felt lamp", {}).get("on") == "lamp shelf", "collected from the platform and shelved"

    # ---- asked for, it is delivered ----
    while not (tr["stopped"] and tr["room"] not in (store.RID, R["depot"])):
        run_train(h, cfg, tr, 1)
    room = h["rooms"][tr["room"]]
    pet["room"], pet["plan"] = room["id"], None
    assert "ask_train" in rail.offered(h, cfg, pet, room) and "lamp" in rail.ctx(h, cfg, pet)
    said = rail.apply({"type": "ask_train", "what": "lamp"}, h, cfg, pet, lambda x: x)[0]
    assert "felt lamp" in said and not rail.offered(h, cfg, pet, room), "one thing asked at a time"
    run_train(h, cfg, tr, 900)
    assert "felt lamp" in room["objects"] and not room["objects"]["felt lamp"].get("on") and h["rail"]["done"]["delivered"] >= 1, "brought to the platform where it was asked for"
    assert any("brought the felt lamp you asked for" in e for _, e in pet["events"])

    # ---- room caps: what the room is for stays, up to its count; the rest goes ----
    music = next(r for r in h["rooms"].values() if r["type"] == "music")
    for i in range(6):
        thing(eng, music, "drum %s" % "abcdef"[i], "drum", "noisy", None, days=3 + i)
    goes = store.out_of_place(h, cfg, music)
    assert sum(n.startswith("drum") for n in goes) == 6 - cfg["house"]["rooms"]["music"]["belongs"]["drum"], goes
    fresh = thing(eng, music, "new drum", "drum", "noisy", None, days=0.2)
    heir = thing(eng, music, "old flute", "flute", "noisy", None, days=9)
    heir["made"]["heirloom"] = {"from": "x"}
    assert "new drum" not in store.out_of_place(h, cfg, music) and "old flute" not in store.out_of_place(h, cfg, music), "in use, and heirlooms, stay"

    # ---- nothing kept is lost: the store full, only the oldest thing that is not special goes to the Works ----
    titled = thing(eng, S, "titled cushion", "cushion", "soft", None, days=30, on="cushion shelf")
    titled["made"]["recipe"]["title"] = "Grandmother's Rest"
    plain = thing(eng, S, "plain cushion", "cushion", "soft", None, days=29, on="cushion shelf")
    for x in (titled, plain):   # (long untouched: this house began at tick 0)
        x["made"]["touched"] = x["kept"] = x["made"]["tick"]
    for n, x in S["objects"].items():   # every shelf full
        if "fix" in x and x["fix"].get("store") and not x["fix"].get("keepsake"):
            x["fix"]["store"] = len(order.held(S, n))
    o = thing(eng, music, "late cushion", "cushion", "soft", None, days=5)
    music["objects"].pop("late cushion")
    assert store.put(h, cfg, S, "late cushion", o), "the store full, room is made"
    assert "titled cushion" in S["objects"] and "plain cushion" not in S["objects"], "the oldest plain thing went to the Works; the titled one stays"
    assert any(g["name"] == "plain cushion" and "full store" in g["gone"][1] for g in h["gone_things"]), "and it is listed as gone"

    # ---- a room still over its cap when the train stops: the car takes what is over it (none of what is kept) ----
    green = next(r for r in h["rooms"].values() if r["type"] == "greenhouse")
    tr["held"] = []
    for i in range(9):
        thing(eng, green, "old pot %s" % "abcdefghi"[i], "box", "hard", None, days=6 + i)
    kept = thing(eng, green, "old pot j", "box", "hard", None, days=20)
    kept["made"]["heirloom"] = {"from": "x"}
    while not (tr["stopped"] and tr["room"] == green["id"] and tr.get("arrived") == h["tick"]):
        run_train(h, cfg, tr, 1)
    assert len(store.out_of_place(h, cfg, green)) <= cfg["house"]["store"]["cap"] and "old pot j" in green["objects"], store.out_of_place(h, cfg, green)
    assert any("too much lay about" in m["text"] for m in h["moments"]), "and the story says so"
    from . import actions
    pet.update(room=tr["room"], pos=list(tr["pos"]), carrying=["pebble"], sleep=None)
    assert "does not take things from your paws" in (actions.check({"type": "give", "what": "pebble", "to": "train"}, h, cfg, pet, eng.minds[pet["id"]].mem) or ""), "nothing is fed to the train"

    # ---- a new death: the stone to the resting place, the box to its family's shelf ----
    dead = dict(pet, id="p999", name="Odo", stage="dead", died=h["tick"], born=h["tick"] - 1000, buried=False, room=music["id"], pos=[5, 4])
    h["pets"]["p999"] = dead
    life.bury(h, cfg, dead)
    g = h["rooms"][h["resting"]["room"]]
    stone = next((n for n, o in g["objects"].items() if o.get("memorial", {}).get("pet") == "p999"), None)
    assert stone and g["objects"][stone]["pos"] in h["resting"]["tiles"], "the stone stands in the resting place"
    room, box = order.box_of(h, "p999")
    assert room["type"] == "attic" and room["objects"][room["objects"][box]["on"]]["fix"].get("memory"), "the box is on its family's memory shelf"
    print("rail check passed")


async def run_wall(d):
    """SPEC-v5.3.2 §2: the same train with its track in the wall instead of over the floor: a platform against a wall,
    a portal in that wall, nothing laid on a floor tile and nothing crossing a doorway; the cart, the loading, the
    stops and what is asked for are exactly as they were. ([wallrail] rides on [v5], so both go on here.)"""
    cfg = load_config()
    cfg["weather"]["real"] = False
    cfg["v5"]["on"] = True
    cfg["wallrail"]["on"] = True
    eng, pet = engine(cfg, d + "/w")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    for rid in list(h["rooms"]):
        generate_room(h, cfg, rid)
    from . import hub
    hub.migrate(h, cfg)
    at(eng, 9)
    store.lay(h, cfg)
    resting.migrate(h, cfg)
    pet.update(name="Pim", stage="adult")

    # ---- the route and the lay: rooms joined by portals, no track on the floor, nothing across a doorway ----
    rail.make(h, cfg)
    tr, R = rail.train(h), h["rail"]
    rooms = {rid for rid, r in h["rooms"].items() if r["type"]}
    assert tr and set(R["route"]) == rooms and set(R["rooms"]) == rooms, (R["route"], rooms)
    assert all(l["in"] is None and l["out"] is None for l in R["legs"]), "a pass through a room goes through no door: %s" % R["legs"]
    assert sum(leg["stop"] for leg in R["legs"]) == len(rooms), "one stop a room a round (the depot at the end)"
    assert set(R.get("walls", {})) == set(R["rooms"]), "every room on the route has a wall, and only that: %s" % sorted(R["rooms"])
    doors = {tuple(t) for t in h["door_tiles"].values()}
    W, H = cfg["W"], cfg["H"]
    for rid, x in R["rooms"].items():
        room, p, po = h["rooms"][rid], x["platform"], x["portal"]
        assert len(x["track"]) == 1 and x["buffer"], "one dead-end branch a room, with its buffer: %s" % rid
        arm = x["track"][0]
        assert arm[0] == po["pos"] and arm[-1] == p and 2 <= len(arm) <= cfg["wallrail"]["branch"], "the branch runs from the portal to the platform, and is short: %s %s" % (rid, arm)
        assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(arm, arm[1:])), "tile to tile: %s" % arm
        e = po["pos"]
        assert (e[0] in (0, W - 1)) != (e[1] in (0, H - 1)), "the portal is in a wall and in no corner: %s %s" % (rid, e)
        assert {"north": e[1] == 0, "south": e[1] == H - 1, "west": e[0] == 0, "east": e[0] == W - 1}[po["wall"]], "and the wall is named for it: %s" % po
        assert all(0 < t[0] < W - 1 and 0 < t[1] < H - 1 for t in arm[1:]), "the rest of the branch is in from the walls: %s" % arm
        own = {tuple(h["door_tiles"][d]) for d in room["doors"]}
        assert not {tuple(t) for t in arm} & own, "nothing of it lies in one of the room's doorways: %s" % rid
        fixed = {tuple(o["pos"]) for o in room["objects"].values() if "fix" in o and not o.get("wall") and not o.get("on") and not o["fix"].get("platform")}
        assert not {tuple(t) for t in arm} & fixed, "the branch runs clear of the fixtures: %s" % rid
        assert room["objects"]["platform"]["pos"] == p, "the platform is the fixture it says it is: %s" % rid
        st = x["strip"]
        assert st and x["side"] == st[0] and all(0 < t[0] < W - 1 and 0 < t[1] < H - 1 for t in st), "the platform's slabs are on the floor, the first of them its side: %s %s" % (rid, st)
        assert all(any(abs(t[0] - a[0]) + abs(t[1] - a[1]) == 1 for a in arm[1:]) for t in st) and not {tuple(t) for t in st} & ({tuple(t) for t in arm} | fixed | own), \
            "each beside the track, on no track, fixture or doorway: %s %s" % (rid, st)
    same = [x for x in R["rooms"].values() if x["portal"]["wall"] == cfg["wallrail"]["wall"] and x["portal"]["pos"][1] == cfg["wallrail"]["rows"][0]]
    assert len(same) * 2 >= len(R["rooms"]), "the station is in the same place in most rooms: %d of %d" % (len(same), len(R["rooms"]))
    assert all(len(x["track"][0]) == cfg["wallrail"]["branch"] and len({t[1] for t in x["track"][0]}) == 1 and len(x["strip"]) == cfg["wallrail"]["branch"] - 1 for x in same), "and there it is the same station: straight in, with its whole strip"

    # ---- one crossing: into the portal here, inside the wall for `portal_ticks`, out at the next room's platform ----
    while not tr.get("inwall"):
        run_train(h, cfg, tr, 1)
    hold = (tr["room"], list(tr["pos"]))   # (it went in standing at this room's platform, and has not moved since)
    nxt = R["legs"][tr["leg"] + 1]["room"]
    for _ in range(max(1, int(cfg["wallrail"]["portal_ticks"])) - 1):   # ([wallrail] is a top-level part, like the others)
        run_train(h, cfg, tr, 1)
        assert (tr["room"], tr["pos"]) == hold and tr.get("inwall"), "inside the wall it crosses no tile at all: %s" % tr["doing"]
        assert tr["cars"] == [None, None, None], "and nothing of it is seen in any room"
    run_train(h, cfg, tr, 1)
    mouth = R["rooms"][nxt]["portal"]["pos"]
    assert tr["room"] == nxt and not tr.get("inwall") and tr["pos"] == R["rooms"][nxt]["platform"], "it comes out at the next room's platform: %s" % tr["pos"]
    arm = R["rooms"][nxt]["track"][0]
    assert [t for _, t in tr["trail"]][:len(arm)] == arm[::-1][:5] and tr["trail"][-1][1] in (list(mouth), arm[max(0, len(arm) - 5)]), \
        "the whole train stands along the branch, the engine at the platform, the rest back toward the mouth: %s" % tr["trail"]
    assert all(c and tuple(c["pos"]) in {tuple(t) for t in arm} for c in tr["cars"]), "every car on the branch: %s" % tr["cars"]
    assert next(c for c in tr["cars"] if c and c.get("k") == 2)["room"] == nxt, "the cart is aboard in this room, where loading() looks"

    # ---- a round: it stops in every room, and never across a door ----
    seen = []
    run_train(h, cfg, tr, 900, seen)
    assert {r for r, _ in seen} == rooms, "it stopped in every room: %s" % sorted({r for r, _ in seen})
    assert all(tuple(c["pos"]) not in {tuple(h["door_tiles"][d]) for d in h["rooms"][r]["doors"]} for r, cs in seen for c in cs), "never stopped across one of the room's doors: %s" % seen
    assert h["rail"]["rounds"] >= 1 and any(c["what"] == "finished a round" for c in h["fresh_creatures"])

    # ---- what is put on it arrives on the right shelf ----
    while not (tr["stopped"] and tr["room"] not in (store.RID, R["depot"])):
        run_train(h, cfg, tr, 1)
    room = h["rooms"][tr["room"]]
    pet["room"], pet["pos"] = room["id"], list(R["rooms"][room["id"]]["platform"])
    thing(eng, room, "blue cushion", "cushion", "soft", None, days=5)
    assert rail.put_on(h, cfg, pet, room, "blue cushion"), "into the cart while it stands here"
    assert "blue cushion" in tr["cargo"], tr["cargo"]
    run_train(h, cfg, tr, 500)
    S = h["rooms"][store.RID]
    assert S["objects"].get("blue cushion", {}).get("on") == "cushion shelf", "carried to the store and shelved"
    # ... and left on the platform, it is collected
    while not (tr["stopped"] and tr["room"] not in (store.RID, R["depot"])):
        run_train(h, cfg, tr, 1)
    while tr["stopped"]:
        run_train(h, cfg, tr, 1)
    room = h["rooms"][tr["room"]]
    pet["room"] = room["id"]
    thing(eng, room, "felt lamp", "lamp", "warm", None, days=5)
    assert rail.put_on(h, cfg, pet, room, "felt lamp") == "on the platform, for the train" and room["objects"]["felt lamp"]["on"] == "platform"
    run_train(h, cfg, tr, 700)
    assert S["objects"].get("felt lamp", {}).get("on") == "lamp shelf", "collected from the platform and shelved"

    # ---- asked for, it is delivered ----
    while not (tr["stopped"] and tr["room"] not in (store.RID, R["depot"])):
        run_train(h, cfg, tr, 1)
    room = h["rooms"][tr["room"]]
    pet["room"], pet["plan"] = room["id"], None
    assert "ask_train" in rail.offered(h, cfg, pet, room) and "lamp" in rail.ctx(h, cfg, pet)
    said = rail.apply({"type": "ask_train", "what": "lamp"}, h, cfg, pet, lambda x: x)[0]
    assert "felt lamp" in said and not rail.offered(h, cfg, pet, room), "one thing asked at a time"
    run_train(h, cfg, tr, 900)
    assert "felt lamp" in room["objects"] and not room["objects"]["felt lamp"].get("on") and h["rail"]["done"]["delivered"] >= 1, \
        "brought to the platform where it was asked for"
    assert any("brought the felt lamp you asked for" in e for _, e in pet["events"])

    # ---- a house whose train was out on the floor's track when the walls took it (23 November 2026: every hob's tick
    # failed in rail.eta, its leg past the end of the wall's shorter round) ----
    R = h["rail"]
    R.pop("walled")
    tr.update(leg=len(R["legs"]) + 5, path=[[3, 3], [4, 3]], stopped=False, asleep=False)
    rail.lay(h, cfg)
    assert tr["leg"] == len(R["legs"]) - 1 and tr["path"] == [] and tr["room"] == R["legs"][-1]["room"] and tr["pos"] == R["rooms"][tr["room"]]["platform"], \
        "it stands at the depot's end of the round: %s" % {k: tr[k] for k in ("leg", "path", "room", "pos")}
    assert set(rail.eta(h, cfg)) == set(R["rooms"]), "and every platform has its next stop"
    leg = tr["leg"]
    rail.lay(h, cfg)
    assert tr["leg"] == leg, "a start after that leaves the train where it is"
    cfg["wallrail"]["on"] = False
    rail.lay(h, cfg)
    assert "walls" not in h["rail"] and all(x["track"] for x in h["rail"]["rooms"].values()), "switched off, the floor's rail is laid again"
    print("wall rail check passed")


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))
        asyncio.run(run_wall(d))


if __name__ == "__main__":
    main()
