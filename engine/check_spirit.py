"""SPEC-v4.2 §0.1 item 4: one check with everything on. The live profile (the first check to run live's
configuration), the stub brain, a house of seven hobs from hatchling to elder in two families, three world days
through the whole engine: no traceback, and the Lab's Spirit numbers are not nothing (memories the model wrote, a hook
acted on, a talk that left `knows`, a happening chosen). Then the same days with [spirit] off: none of v4.2's data
appears (v4.0.6's house).

    uv run python -m engine.check_spirit
"""
import asyncio
import logging
import os
import tempfile

from . import contracts as K
from . import tick as _tick  # noqa: F401  (the engine first: a module run alone)
from .check_brain4 import calm, grow
from .tick import Engine, Mind, stub_brains
from .world import alive, generate_room, load_config, new_pet

DAYS = 3
# what v4.2 writes on a hob and in the house: none of it while [spirit] is off
PET_KEYS = ("self", "last_self", "drive", "flaw", "voice", "secret", "visitor_theory", "leave", "beliefs_due", "secret_due", "span_add", "old", "taught", "hooked")
HOUSE_KEYS = ("spirit", "happening", "happenings", "tales")


class Tracebacks(logging.Handler):
    def __init__(self):
        super().__init__(logging.ERROR)
        self.seen = []

    def emit(self, r):
        if r.exc_info or r.levelno >= logging.ERROR:
            self.seen.append(self.format(r))


def config(spirit=True, v5=False):
    cfg = load_config(profile="live")
    cfg["v5"]["on"] = v5
    cfg["weather"]["real"] = False
    cfg["stub"]["enabled"] = True
    cfg["clock"]["turbo"] = True
    cfg["spirit"]["on"] = spirit
    if spirit:
        cfg["stage"]["quiet"] = 0.0   # (the stub's narrator then always chooses something: "a happening chosen" in three nights)
    return cfg


def hob(eng, room, stage, family, pos):
    h, cfg = eng.house, eng.cfg
    pet = new_pet(h, cfg, room["id"], list(pos), family=family)
    from . import life
    life.hatch(h, cfg, pet)
    grow(h, pet, stage)
    pet["mood"] = calm(h)
    pet["name"] = pet["name"] or "Hob%s" % pet["id"]
    eng.minds[pet["id"]] = Mind(eng, pet)
    return pet


async def house(d, cfg):
    eng = Engine(cfg, d, stub_brains)
    p0 = eng.new_lineage()
    p0["laid"] = -10 ** 6
    await eng.tick()
    h = eng.house
    grow(h, p0, "elder")
    p0.update(name="Spoon", mood=calm(h))
    room = h["rooms"][p0["room"]]
    for kind in ("workshop", "garden"):
        rid = next(r for r, x in sorted(h["rooms"].items()) if not x["type"] and r in room["doors"].values())
        generate_room(h, cfg, rid, kind)
        p0["rooms"][rid] = h["tick"] - 10 ** 4
    for i, (stage, fam) in enumerate((("adult", 1), ("adult", 2), ("youngling", 2), ("child", 1), ("child", 2), ("hatchling", 1))):
        hob(eng, room, stage, fam, [1 + i, 4])
    # what v4.0's hobs carry on live, that v4.2 must read past (the rehearsal's first fault: the craft hints, dicts,
    # read as the visitor's words)
    p0["hints"] = [{"bit": "wax", "how": "melt", "tick": 1}, {"bit": "clay", "how": "warm", "tick": 2}]
    return eng


async def run(d, cfg):
    eng = await house(d, cfg)
    h = eng.house
    tb = Tracebacks()
    logging.getLogger().addHandler(tb)
    try:
        # a hooked belief on one hob, so the day has something to act on (the stub's reflections give more by night)
        if K.on(cfg, "hooks"):
            from . import hooks
            p = next(p for p in alive(h) if p["stage"] == "adult")
            garden = next(r for r, x in h["rooms"].items() if x["type"] == "garden")
            p["rooms"][garden] = h["tick"]
            hooks.believe(eng, p, "the garden is no place for me", {"name": "avoid_place", "arg": h["rooms"][garden]["name"], "when": ""}, "lived")
        for _ in range(DAYS * cfg["ticks_per_day"]):
            await eng.tick()
        await asyncio.sleep(0)
    finally:
        logging.getLogger().removeHandler(tb)
    return eng, tb.seen


async def on(d):
    cfg = config(True)
    eng, seen = await run(d, cfg)
    h = eng.house
    assert not seen, "no traceback with everything on: %d, the first:\n%s" % (len(seen), seen[0])
    assert all(K.on(cfg, p) for p in K.PARTS)
    from . import lab4
    S = lab4.spirit(eng)
    mems = [m for p in alive(h) for m in p.get("memories", [])]
    model = [m for m in mems if K.memory(m)["by"] == "model"]
    acted, knows = K.since(h, "acted", 0), K.since(h, "knows", 0)
    chosen = [x for x in h.get("happenings", []) if K.happening(x)["name"] != "nothing"]
    assert model, "memories the model wrote (%d memories, none the model's)" % len(mems)
    assert acted, "a hook acted on"
    assert knows, "a talk that left knows lines"
    assert chosen, "a happening chosen (%s)" % h.get("happenings")
    assert S, "the Lab's Spirit section"
    print("spirit: %d world days with everything on, no traceback; %d of %d memories the model's, %d hooks acted on, %d talks with knows, happenings: %s"
          % (DAYS, len(model), len(mems), len(acted), len(knows), ", ".join(K.happening(x)["name"] for x in h.get("happenings", []))))
    return eng


async def off(d):
    cfg = config(False)
    eng, seen = await run(d, cfg)
    h = eng.house
    assert not seen, "no traceback with [spirit] off: %s" % seen[:1]
    assert not any(k in h for k in HOUSE_KEYS), "[spirit] off: the house has none of v4.2's data (%s)" % [k for k in HOUSE_KEYS if k in h]
    for p in h["pets"].values():
        bad = [k for k in PET_KEYS if p.get(k)]
        assert not bad, "[spirit] off: %s has %s" % (p.get("name"), bad)
        assert all(K.memory(m)["by"] == "engine" for m in p.get("memories", [])), "[spirit] off: no memory is the model's"
    print("spirit: with [spirit] off, %d world days and none of v4.2's data" % DAYS)


def agree(h):
    """SPEC-v5.0, the layer's seam (DECISIONS Part 43): an item's owner and maker are mirrors of its made thing's, so on
    every object that carries both they agree. Returns how many were looked at."""
    n = 0
    for r in h["rooms"].values():
        for name, o in r.get("objects", {}).items():   # (an unfound room has none)
            if "item" in o and "made" in o:
                it, m = o["item"], o["made"]
                assert (it["owner"], it["maker"]) == (m.get("owner") or None, m.get("by") or None), "%s in %s: the item says %s, the made thing %s" % (
                    name, r["id"], (it["owner"], it["maker"]), (m.get("owner"), m.get("by")))
                n += 1
    return n


async def v5_on(d):
    """SPEC-v5.0 §7 everything-on: v4.2 and v5.0 together, three world days: no traceback; every made thing an item;
    owner and maker agree between the item and its made thing on every object, after the days' giving and dying."""
    cfg = config(True, v5=True)
    eng, seen = await run(d, cfg)
    h = eng.house
    assert not seen, "no traceback with [v5] on: %d, the first:\n%s" % (len(seen), seen[0])
    assert all(K.on5(cfg, p) for p in K.PARTS5)
    made = sum("made" in o for r in h["rooms"].values() for o in r.get("objects", {}).values())
    n = agree(h)
    assert made and n == made, "every made thing is an item (%d of %d)" % (n, made)
    print("spirit: %d world days with [v5] on too, no traceback; %d items, owner and maker agree on every one" % (DAYS, n))
    return eng


async def v5_off(d):
    """[v5] off (spirit on): none of v5.0's data appears."""
    cfg = config(True, v5=False)
    eng, seen = await run(d, cfg)
    h = eng.house
    assert not seen and "v5" not in h, "[v5] off: no house['v5'] (%s)" % seen[:1]
    assert not any("item" in o for r in h["rooms"].values() for o in r.get("objects", {}).values()), "[v5] off: no item on any object"
    assert not any("scrap" in p for p in h["pets"].values()), "[v5] off: no hob has scrap"
    print("spirit: with [v5] off, %d world days and none of v5.0's data" % DAYS)


async def seams(d):
    """Seams the lead closed at the merge (§0.1 item 7): the visitor's question finds a secret (D's visitor, C's drives),
    and a dishonest hob lies the first time it is asked in a day."""
    from . import visitor
    from .check_brain4 import house as house4, hob as hob4
    eng, p0 = await house4(d)
    cfg, h = eng.cfg, eng.house
    cfg["spirit"]["on"] = True
    wen = hob4(eng, h["rooms"][p0["room"]], [3, 3])
    wen["name"] = "Wen"
    p0["secret"] = K.secret({"kind": "broken", "text": "I broke Wen's blue bowl and hid the pieces", "about": wen["id"], "tick": 1})
    p0["flaw"] = {"name": "dishonest", "asked": -99}
    assert not visitor.asked_after(h, cfg, p0, "how are you?") and not visitor.asked_after(h, cfg, p0, "did you see Wen today.")
    assert not visitor.asked_after(h, cfg, p0, "what happened to Wen's bowl?") and not p0["secret"]["found"], "a dishonest hob lies once"
    assert visitor.asked_after(h, cfg, p0, "what happened to the blue bowl?") and p0["secret"]["found"] and K.since(h, "secret found", 0)
    print("spirit: the visitor's question finds a secret it touches; a dishonest hob lies the first time it is asked in a day")


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(on(d + "/on"))
        asyncio.run(off(d + "/off"))
        asyncio.run(seams(d + "/seams"))
        asyncio.run(v5_on(d + "/v5"))
        asyncio.run(v5_off(d + "/v5off"))
    print("check_spirit: all passed")


if __name__ == "__main__":
    main()
