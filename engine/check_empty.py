"""Self-check for the empty house (v5.3.2, engine/emptyhouse.py): off, nothing happens; on, the data folder is copied
first and a failed copy clears nothing; every made thing (a keepsake too), every thing the hobs built (a statue too)
and every fixture the Works built for a room goes and the Works' list begins again; the fixtures the house was drawn
with, the stones, what the Works did for the machine and what the visitor set down stay; each made thing is fed to
the Works once and never again;
projects under way or blocked are planned again; the machine is full and gives `free` a hob a day for `free_days`.
    uv run python -m engine.check_empty"""
import asyncio
import copy
import logging
import os
import tempfile
import tomllib
from pathlib import Path

import engine.tick  # noqa: F401  (first, as when any module is run alone)
from . import contracts as K
from . import emptyhouse, hub, machine, projects, things, visitor, works
from .check_machine import thing
from .check_talk import house_of, settle
from .world import fixture, generate_room


def furnish(eng, a, b, c):
    """A house with something of every sort in it: made things (one on a shelf, one the visitor's), a bed and a kiln
    the hobs built, a thing under way, a project's nook, a statue, a stone, and a project under way."""
    h, cfg = eng.house, eng.cfg
    for rid in list(h["rooms"]):
        generate_room(h, cfg, rid)
    hub.migrate(h, cfg)
    machine.migrate(h, cfg)
    room = h["rooms"][a["room"]]
    shelf = next((n for n, o in room["objects"].items() if o.get("fix", {}).get("store")), None)
    thing(eng, room, "blue cup", "cup", "hard", a["id"], days=3)
    thing(eng, room, "old charm", "charm", "hard", b["id"], days=3, **({"on": shelf} if shelf else {}))
    assert visitor.use(eng, "place", {"room": room["id"], "pos": [3, 3], "kind": "lantern"})[0]
    built = lambda key: {"project": key, "by": a["id"], "names": ["Ada"], "paws": [a["id"]], "at": h["tick"], "began": h["tick"]}
    room["objects"]["bed frame"] = {"pos": [2, 5], "fix": {"rest": 3.0, "cozy": True, "built": built("bed frame")}}
    room["objects"]["kiln"] = {"pos": [8, 5], "fix": {"kiln": True, "built": built("kiln")}, "runs": 0, "warm": 0, "output": []}
    room["objects"]["bench"] = {"pos": [5, 6], "fix": {"site": "bench"}, "state": "being built",
                                "site": {"project": "bench", "by": a["id"], "at": h["tick"], "placed": {}, "work": 0.0, "paws": {}, "last": {}}}
    room["objects"]["Ada's nook"] = {"pos": [9, 2], "fix": {"project5": "p1", "verbs5": {}, "cozy": False, "says": "a nook; Ada built it"}}
    room["objects"]["statue"] = {"pos": [6, 2], "fix": {"cozy": True, "built": built("statue")}, "statue": {"family": 1}}
    room["objects"]["stone for pip"] = {"pos": [10, 5], "memorial": {"pet": c["id"]}}
    room["objects"]["keepsake box for pip"] = {"pos": [10, 5], "on": "stone for pip", "fix": {"keepsake": c["id"], "store": 3, "inside": True}}
    thing(eng, room, "pip's ring", "ring", "hard", c["id"], days=9, on="keepsake box for pip")
    room.setdefault("spots", []).append({"bit": "ash", "pos": [8, 6], "ready": True, "back": None, "loose": False, "built": "kiln"})
    h["n"]["thing"] += 1   # (and a made thing and a bit riding in a creature, as the train's cart and a sweeper carry them)
    ride = {"pos": [0, 0], "made": {"id": h["n"]["thing"], "recipe": {"name": "red bowl", "kind": "bowl", "material": "hard", "color": "red", "size": 2, "purpose": "a check"},
                                    "by": b["id"], "owner": b["id"], "tick": 0, "bits": [], "uses": 0, "ups": 0, "used_at": 0, "heirloom": None, "behavior": None}}
    h["creatures"].append({"id": "c-check", "kind": "sweeper", "room": room["id"], "pos": [1, 1], "doing": "", "held": [{"name": "red bowl", "o": ride}, {"bit": "reed"}]})
    W = works.state(h, cfg)   # (the Works has built a fixture for this room's type, one for the machine, and is on its third goal)
    fx = next(x for x in cfg["works"]["build"] if x.get("fixture"))
    up = next(x for x in cfg["works"]["build"] if x.get("machine"))
    room["type"] = fx["fixture"]["room"]
    W["built"] += [{"what": fx["what"], "tick": 0, "by": []}, {"what": up["what"], "tick": 0, "by": []}]
    W.update(goal=2, have=1)
    works.lay(h, cfg)
    assert fx["fixture"]["name"] in room["objects"], "the Works' fixture stands in its room"
    S = projects.store(h)
    S["p1"] = K.project({"id": "p1", "goal": "a nook", "kind": "shelter", "steps": [{"do": "build"}], "owners": [a["id"]], "since": h["tick"], "state": "done", "why": "a check"})
    S["p1"]["fixture"] = "Ada's nook"
    S["p2"] = K.project({"id": "p2", "goal": "a shelter", "kind": "shelter", "steps": [{"do": "gather", "what": "wood", "n": 4}, {"do": "build"}],
                         "owners": [b["id"]], "since": h["tick"], "state": "under way", "why": "a check"})
    S["p2"]["steps"][0].update(got=4, done=True, by=[b["id"]])
    S["p2"].update(stock={"wood": 4}, progress=0.5)
    S["p3"] = K.project({"id": "p3", "goal": "a bridge", "kind": "shelter", "steps": [{"do": "build"}], "owners": [a["id"]], "since": h["tick"], "state": "blocked", "why": "a check"})
    projects.setbacks(h)["p3"] = "no stone"
    return room


async def run(d):
    eng, (a, b, c) = await house_of(d + "/e", v5=True, items=True, projects=True, trade=True)
    h, cfg = eng.house, eng.cfg
    a["name"], b["name"] = "Ada", "Bram"
    room = furnish(eng, a, b, c)
    data = Path(d) / "e"
    fx = next(x for x in cfg["works"]["build"] if x.get("fixture"))
    up = next(x for x in cfg["works"]["build"] if x.get("machine"))
    authored = sorted(n for n, o in room["objects"].items() if "fix" in o and not emptyhouse.hob_built(o) and n != fx["fixture"]["name"])
    drawn = tomllib.loads((Path(__file__).parent.parent / "house.toml").read_text())["rooms"]
    assert not [x["what"] for x in cfg["works"]["build"] if x.get("fixture") and x["fixture"]["name"] in [f["name"] for f in drawn[x["fixture"]["room"]]["fixtures"]]], \
        "no fixture of the Works shares a name with one its room was drawn with (clear_works takes it by name)"
    was = copy.deepcopy(h["rooms"])

    # ---- off: nothing at all ----
    assert emptyhouse.migrate(h, cfg, data) == [] and "empty_house" not in h and h["rooms"] == was, "[empty_house] off clears nothing"
    assert emptyhouse.allowance(h, cfg) is None and machine.free(h, cfg) == 0, "and the machine gives what it gave ([trade] on: nothing free)"

    # ---- on, but the copy fails: the house is as it was, and it will be tried again ----
    cfg["empty_house"]["on"] = True

    def no_copy(*_):
        raise OSError("disk full")
    assert emptyhouse.migrate(h, cfg, data, copy=no_copy) == [] and "empty_house" not in h and h["rooms"] == was, "no copy, no clearing"

    # ---- on: the copy first, then the clearing ----
    fed = []
    real = works.fed
    works.fed = lambda house, cfg_, pet, o=None: (fed.append(works.key(o)), real(house, cfg_, pet, o))[1]
    try:
        lines = emptyhouse.migrate(h, cfg, data)
        S = h["empty_house"]
        kept = Path(S["backup"])
        assert lines and kept.is_dir() and kept.parent == data.parent and kept.name.startswith("e.bak-day"), "the data folder is copied beside itself: %s" % kept
        made = things.made(room)
        assert list(made) and all(o["made"]["by"] == "visitor" for o in made.values()), "only what the visitor set down is left of the made things: %s" % list(made)
        for gone in ("blue cup", "old charm", "pip's ring", "bed frame", "kiln", "bench", "Ada's nook", "statue", fx["fixture"]["name"]):
            assert gone not in room["objects"], "%s is cleared" % gone
        assert all(n in room["objects"] for n in authored), "every authored fixture stays: %s" % [n for n in authored if n not in room["objects"]]
        assert "stone for pip" in room["objects"] and "keepsake box for pip" in room["objects"], "the stone and its (empty) box stay"
        Wk = works.state(h, cfg)
        assert S["works"] == [fx["what"]] and [b["what"] for b in Wk["built"] if b["what"] in (fx["what"], up["what"])] == [up["what"]], "the Works' fixture is off its list; what it did for the machine stays"
        assert works.goal(h, cfg)["what"] == fx["what"] and Wk["have"] == 0, "and its list begins again from the top with an empty meter: %s" % works.goal(h, cfg)["what"]
        assert fx["fixture"]["name"] not in [f["name"] for f in cfg["house"]["rooms"][fx["fixture"]["room"]]["fixtures"]], "nor is it laid again at the next start"
        works.lay(h, cfg)
        assert fx["fixture"]["name"] not in room["objects"], "works.lay does not bring it back"
        assert next(c for c in h["creatures"] if c["id"] == "c-check")["held"] == [{"bit": "reed"}], "a made thing riding in a sweeper goes; a bit rides on"
        assert not any(s.get("built") == "kiln" for s in room["spots"]), "what the room grew for the kiln goes with it"
        assert {g["name"] for g in h["gone_things"]} >= {"blue cup", "old charm"}, "the Things tab keeps a note of each"
        assert S["made"] == 4 and len(S["built"]) == 5 and len(fed) == 4 and len(set(fed)) == 4 and sorted(map(str, fed)) == sorted(S["fed"]), "fed once each: %s" % fed
        P = projects.store(h)
        assert P["p1"]["state"] == "done" and P["p1"]["fixture"] is None, "a finished project is history; its fixture is gone"
        assert P["p2"]["state"] == "planned" and not P["p2"]["steps"][0]["done"] and P["p2"]["stock"] == {} and P["p2"]["progress"] == 0.0, "under way: planned again, nothing gathered"
        assert P["p3"]["state"] == "planned" and "p3" not in projects.setbacks(h), "blocked: planned again"
        M = cfg["machine"]
        assert all(machine.state(h, cfg)["stock"][m] == M["limit"] for m in M["materials"]), "the machine is full"
        assert any("emptied" in e[1] for e in a["events"]), "the hobs are told"

        # ---- never twice: a second start does nothing, and a thing fed once is never fed again ----
        again = copy.deepcopy(h["rooms"])
        assert emptyhouse.migrate(h, cfg, data) == [] and h["rooms"] == again and len(fed) == 4, "once a house"
        o = thing(eng, room, "blue cup", "cup", "hard", a["id"], days=3)
        o["made"]["id"] = int(S["fed"][0])
        assert not emptyhouse.feed(h, cfg, S, o) and len(fed) == 4, "a key already fed is not fed again"
        room["objects"].pop("blue cup")
    finally:
        works.fed = real

    # ---- the allowance: `free` a hob a world day for `free_days`, whatever [trade] says, then as configured ----
    E = cfg["empty_house"]
    assert machine.free(h, cfg) == E["free"] == machine.left(h, cfg, a), "it gives freely at first"
    machine.take(h, cfg, a, M["materials"][0])
    assert machine.left(h, cfg, a) == E["free"] - 1, "and counts what it gave today: %s" % a["machine"]
    h["tick"] += round(E["free_days"] * cfg["ticks_per_day"])
    assert emptyhouse.allowance(h, cfg) is None and machine.free(h, cfg) == 0, "after that, [trade] on: nothing free again"
    cfg["trade"]["on"] = False
    assert machine.free(h, cfg) == M["free"], "and with [trade] off, [machine] free"

    # ---- it still runs: a world hour and more with what the visitor set down in the room, and nothing fails ----
    errors = []
    grab = logging.Handler(level=logging.ERROR)
    grab.emit = lambda r: errors.append(r.getMessage())
    logging.getLogger().addHandler(grab)
    try:
        for kind in sorted(cfg["items5"]["kind"]):   # every kind he can place is a thing the engine can live with
            assert visitor.nature(cfg, kind) in cfg["materials"], "%s: %s is no nature" % (kind, visitor.nature(cfg, kind))
        h["creatures"] = [c for c in h["creatures"] if c["id"] != "c-check"]
        for _ in range(40):
            await eng.tick()
    finally:
        logging.getLogger().removeHandler(grab)
    assert not errors, "the house ticks on without a failure: %s" % errors[:3]
    return eng


async def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        await settle(await run(d))


if __name__ == "__main__":
    asyncio.run(main())
    print("check_empty passed")
