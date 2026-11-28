"""Self-check for SPEC-v4.0.5 §3 (the lineage, helper B): a founder egg of a family is that family's child (§3.1); the
living orphans made before that are re-parented once (§3.2); laying is favoured over finding (§3.3). Stub houses only.
    uv run python -m engine.check_lineage"""
import asyncio
import os
import tempfile

from . import life, migrate4, world
from .check_brain4 import hob, house


def hour(h, cfg):
    """On to the next world hour (founder looks once an hour), with the model idle."""
    h["tick"] = (h["tick"] // world.hours(cfg, 1) + 1) * world.hours(cfg, 1)
    h["busy"] = []


def room_for_a_day(h, cfg):
    """The house has had room, and no egg laid, for longer than found_hours."""
    long = world.hours(cfg, cfg["population"]["found_hours"]) + 1
    h["room_since"] = h["tick"] - long
    for p in h["pets"].values():
        p["laid"] = min(p["laid"], h["tick"] - long)


async def founder_is_kin(d):
    """§3.1: a lone adult, no eggs left in it; the egg that turns up is its child. A new family's founder is not."""
    eng, kin = await house(d)
    h, cfg = eng.house, eng.cfg
    cfg["craft"]["knowing"]["inherited"] = 1.0
    kin["eggs"] = life.fertility(kin)
    kin["message"] = [{"tick": h["tick"], "text": "Keep the kiln warm."}]
    kin["ambition"] = {"text": "make a kiln", "plain": "make a kiln", "done": h["tick"]}
    kin["recipes"] = {"cup|clay": {"tick": h["tick"], "from": "found"}}
    room_for_a_day(h, cfg)
    hour(h, cfg)
    egg = life.founder(h, cfg)
    assert egg, "an egg turns up for a lone family"
    assert egg["founder"] and egg["parent"] == kin["id"] and egg["gen"] == kin["gen"] + 1 and egg["id"] in kin["children"], \
        (egg["parent"], egg["gen"], kin["children"])
    assert any(t["kind"] == "message" and t["by"] == kin["id"] and t["text"] == "Keep the kiln warm." for t in egg["told"]), egg["told"]
    assert any(t["kind"] == "ambition" and t["by"] == kin["id"] for t in egg["told"]), "firsts.laid: it hears of its kin's ambition"
    assert h["moments"][-1]["text"].endswith("one of %s's family" % world.label(kin)), h["moments"][-1]
    life.hatch(h, cfg, egg)
    said = [e for _, e in egg["events"]]
    assert "you came to %s's family as an egg nobody laid" % world.label(kin) in said and "no one left you any words" not in said, said
    assert "cup|clay" in egg.get("recipes", {}), "craft.inherit: it knows what its kin knew"
    assert not any("the egg you laid" in e for _, e in kin["events"]), "its kin did not lay it, and is not told so"
    # a kin with no message: nothing told, still its child
    eng2, kin2 = await house(d + "2")
    h2, cfg2 = eng2.house, eng2.cfg
    kin2["eggs"] = life.fertility(kin2)
    room_for_a_day(h2, cfg2)
    hour(h2, cfg2)
    egg2 = life.founder(h2, cfg2)
    assert egg2["parent"] == kin2["id"] and not [t for t in egg2["told"] if t["kind"] == "message"], egg2["told"]
    # a new family: no lone family, fewer than `families`
    other = hob(eng2, h2["rooms"][kin2["room"]], [3, 3])
    other["eggs"] = life.fertility(other)
    life.hatch(h2, cfg2, egg2)
    egg2.update(stage="adult", eggs=3)
    room_for_a_day(h2, cfg2)
    hour(h2, cfg2)
    new = life.founder(h2, cfg2)
    assert new and new["parent"] is None and new["gen"] == 1 and new["family"] != world.family(kin2), (new["parent"], new["gen"], new["family"])
    life.hatch(h2, cfg2, new)
    assert "no one left you any words" in [e for _, e in new["events"]], "a new family's founder is told nothing, as before"


async def little_kin(d):
    """A hatchling or a child is never a parent: a grown kin is preferred; with only a little one, the egg is its
    sibling (its parent's child, or, for a family's first, nobody's, of its generation)."""
    eng, first = await house(d)
    h, cfg = eng.house, eng.cfg
    cfg["population"]["families"] = 1
    first["stage"] = "child"   # (the lowest id, and little)
    grown = hob(eng, h["rooms"][first["room"]], [3, 3])
    grown["eggs"] = life.fertility(grown)
    room_for_a_day(h, cfg)
    hour(h, cfg)
    egg = life.founder(h, cfg)
    assert egg["parent"] == grown["id"] and egg["kin"] == grown["id"], (egg["parent"], egg.get("kin"))
    # a lone little one with no parent: a sibling, nobody's
    eng2, lone = await house(d + "2")
    h2, cfg2 = eng2.house, eng2.cfg
    lone["stage"] = "hatchling"
    room_for_a_day(h2, cfg2)
    hour(h2, cfg2)
    egg2 = life.founder(h2, cfg2)
    assert egg2["parent"] is None and egg2["gen"] == lone["gen"] and egg2["kin"] == lone["id"] and not lone["children"], (egg2["parent"], egg2["gen"])
    life.hatch(h2, cfg2, egg2)
    assert "you came to %s's family as an egg nobody laid" % world.label(lone) in [e for _, e in egg2["events"]]
    # a lone little one with a (dead) parent: the egg is that parent's child too
    gone = hob(eng2, h2["rooms"][lone["room"]], [5, 5])
    gone.update(stage="dead", message=[{"tick": 0, "text": "Mind the pond."}])
    lone.update(parent=gone["id"], gen=gone["gen"] + 1)
    gone["children"].append(lone["id"])
    egg2["stage"] = "dead"
    room_for_a_day(h2, cfg2)
    hour(h2, cfg2)
    egg3 = life.founder(h2, cfg2)
    assert egg3["parent"] == gone["id"] and egg3["gen"] == lone["gen"] and egg3["id"] in gone["children"] and egg3["told"][0]["text"] == "Mind the pond.", \
        (egg3["parent"], egg3["gen"], egg3["told"])


async def orphans(d):
    """§3.2: two founder eggs made before §3.1 (parent None, gen 1) with their moments are re-parented; a third with no
    moment is left alone; the first of a new family is untouched; and it runs once."""
    eng, kin = await house(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][kin["room"]]
    kin["eggs"] = life.fertility(kin)
    cfg["population"]["families"] = 1   # (so the second egg is of the smallest family too, not a new one)
    made = []
    for _ in range(2):
        room_for_a_day(h, cfg)
        hour(h, cfg)
        egg = life.founder(h, cfg)
        life.hatch(h, cfg, egg)
        made.append(egg)
    a, b = made
    assert a["parent"] == b["parent"] == kin["id"], (a["parent"], b["parent"])
    eng.flush()
    sib = hob(eng, room, [6, 6], family=8)   # a founder whose kin was a hatchling with no parent when its egg turned up
    sib["founder"], little = True, hob(eng, room, [7, 7], family=8)
    little["stage_at"]["adult"] = h["tick"] + 10
    world.moment(h, "egg", "an egg has turned up in the nursery, one of %s's family" % world.label(little), sib["id"], room["id"])
    stray = hob(eng, room, [4, 4])   # a founder of family 1 with no moment of its egg
    stray["founder"] = True
    first = hob(eng, room, [5, 5], family=7)   # the first of a new family, and one of its own
    first["founder"] = True
    world.moment(h, "egg", "an egg has turned up in the nursery, the first of a new family", first["id"], room["id"])
    eng.flush()
    for p in (a, b):   # as they were made before 19 October 2026
        p.update(parent=None, gen=1)
    kin["children"] = []
    h.pop("migrated", None)
    migrate4.orphans(h, eng.db)
    assert a["parent"] == kin["id"] and a["gen"] == kin["gen"] + 1 and b["parent"] == kin["id"] and {a["id"], b["id"]} <= set(kin["children"]), \
        (a["parent"], b["parent"], kin["children"])
    assert stray["parent"] is None and stray["gen"] == 1 and first["parent"] is None, "no moment, or a new family: left alone"
    assert sib["parent"] is None and sib["gen"] == little["gen"] and sib["kin"] == little["id"] and not little["children"], (sib["parent"], sib["gen"])
    assert h["migrated"]["orphans"]["parents"] == {a["id"]: kin["id"], b["id"]: kin["id"]} and h["migrated"]["orphans"]["siblings"] == {sib["id"]: little["id"]}, h["migrated"]
    a["parent"] = None
    migrate4.orphans(h, eng.db)
    assert a["parent"] is None, "once per house"


async def laying_first(d):
    """§3.3: at most - 1 with a fertile adult, no egg turns up for a day and the adult can lay; once nobody can, one does."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    Pop = cfg["population"]
    room = h["rooms"][pet["room"]]
    pet["needs"]["energy"] = 95.0
    for i in range(Pop["most"] - 2):
        o = hob(eng, room, [2 + i, 6], family=1 if i < 2 else 2)
        o["eggs"] = life.fertility(o)
    assert len(world.alive(h)) == Pop["most"] - 1
    hour(h, cfg)
    assert life.founder(h, cfg) is None   # (starts the house's clock of having room)
    for _ in range(Pop["found_hours"] + 2):
        hour(h, cfg)
        assert life.founder(h, cfg) is None, "no egg turns up while a grown hob could lay"
    assert life.can_lay(h, cfg, pet) is None, life.can_lay(h, cfg, pet)
    pet["eggs"] = life.fertility(pet)
    hour(h, cfg)
    assert life.founder(h, cfg), "nobody can lay and the house has had room a day: an egg turns up"


async def hold_runs_out(d):
    """20 October 2026 (a departure from §3.3): the hold lasts `hold_days` of room with no egg; then an egg turns up though
    a grown hob could lay. And a hob alone never holds one off."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    Pop = cfg["population"]
    hob(eng, h["rooms"][pet["room"]], [2, 6])
    hour(h, cfg)
    assert life.founder(h, cfg) is None
    n = 1
    while life.founder(h, cfg) is None:
        hour(h, cfg)
        n += 1
        assert n <= 24 * Pop["hold_days"] + 1, "two grown hobs with eggs in them, and no egg after %d hours of room" % n
    assert n >= 24 * Pop["hold_days"], "the hold stood its days (%d hours)" % n
    eng2, lone = await house(d + "2")
    h2, cfg2 = eng2.house, eng2.cfg
    assert life.can_lay(h2, cfg2, lone) in (None, "you are too tired to lay an egg") and len(world.alive(h2)) == 1
    hour(h2, cfg2)
    life.founder(h2, cfg2)
    for _ in range(Pop["found_hours"]):
        hour(h2, cfg2)
        egg = life.founder(h2, cfg2)
        if egg:
            break
    assert egg, "a lone grown hob with eggs in it does not hold off the founder egg"


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(founder_is_kin(d + "/k"))
        asyncio.run(little_kin(d + "/y"))
        asyncio.run(orphans(d + "/o"))
        asyncio.run(laying_first(d + "/l"))
        asyncio.run(hold_runs_out(d + "/h"))
    print("lineage check passed")


if __name__ == "__main__":
    main()
