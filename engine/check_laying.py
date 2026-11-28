"""Self-check for laying as the body's (engine/laying.py, 20 October 2026) and the young elders' re-stage (life.migrate):
a stub adult with eggs left lays within two world days through the whole engine, by its "lay" aim; with
`[population] lay` off no lay aim is ever given; an elder younger than the new adult day is re-staged once, an old one
is not. Stub houses only.
    uv run python -m engine.check_laying"""
import asyncio
import os
import tempfile

from . import contracts as K
from . import actions, life, world
from .check_brain4 import hob, house


async def lays(d, on=True):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    cfg["population"]["lay"] = on
    cfg["population"]["on"] = False   # (no founder egg: the egg here is the adult's)
    pet["eggs"] = 0
    pet["temper"]["fertile"] = 1.0
    given, first = None, h["tick"]
    can = actions.allowed   # (the stub lays whenever it may; the live model almost never did: the egg here must be the body's)
    actions.allowed = lambda *a: [x for x in can(*a) if x != "lay_egg"]
    for _ in range(2 * cfg["ticks_per_day"]):
        await eng.tick()
        a = next((a for a in pet.get("aims") or [] if a["kind"] == "lay"), None)
        given = given or (a and h["tick"])
        if pet["eggs"]:
            break
    await asyncio.sleep(0)
    actions.allowed = can
    if not on:
        assert not given and not pet.get("fertile_since"), "[population] lay off: no lay aim, nothing kept"
        print("laying: off, no lay aim in two world days")
        return
    assert pet["eggs"] == 1, "a stub adult with eggs left lays within two world days (aim given at %s)" % given
    egg = h["pets"][pet["children"][-1]]
    assert egg["stage"] == "egg" and egg["told"] and egg["told"][0]["text"], egg["told"]
    assert any(a["kind"] == "lay" and a.get("done") for a in pet["aims"]), "by its lay aim"
    print("laying: the adult laid on world day %.1f, its lay aim given on day %.1f; the egg was told \"%s\""
          % (world.days(cfg, first, h["tick"]), world.days(cfg, first, given), egg["told"][0]["text"][:60]))


async def young_elders(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    cfg["spirit"]["on"] = True
    assert K.on(cfg, "lives")
    day = cfg["ticks_per_day"]
    old = hob(eng, h["rooms"][pet["room"]], [3, 3], stage="elder")
    young = hob(eng, h["rooms"][pet["room"]], [4, 3], stage="elder")
    old["born"], young["born"] = h["tick"] - 36 * day, h["tick"] - 12 * day
    young["span_add"] = -27.0
    h.setdefault("migrated", {}).update(v42_lives=1, v42_deaths=1)   # (migrated before: as live was)
    h["migrated"].pop("v42_young_elders", None)
    lines = life.migrate(h, cfg)
    assert young["stage"] == "youngling" and "span_add" not in young and "elder" not in young["stage_at"], (young["stage"], young.get("span_add"))
    assert old["stage"] == "elder", "an elder old under the new life stays one"
    assert len(lines) == 1 and "youngling (was elder), day 12 of about" in lines[0], lines
    assert not life.migrate(h, cfg), "once per house"
    print("laying: %s" % lines[0])


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(young_elders(d + "/y"))
        asyncio.run(lays(d + "/l"))
        asyncio.run(lays(d + "/o", on=False))
    print("check_laying: all passed")


if __name__ == "__main__":
    main()
