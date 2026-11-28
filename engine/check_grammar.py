"""Self-check for SPEC-v5.1 §1-§3, §9-§10 (helper A, the parser): every catalog kind parses to its v5.0 verbs within
0.2; a tube alone throws nothing; a blade on a handle strikes; a refused material is refused in words naming what
would do; a reed tube won't take a metal spring and a wooden one will, and throws; a thing beyond the hob's tier + 1
is refused with the knowledge sentence; launch and bind resolve on a stub house; [grammar] off gives v5.0's verbs
exactly; the migration on a small house writes its report. Stub houses only.
    uv run python -m engine.check_grammar"""
import asyncio
import os
import tempfile
from pathlib import Path

from . import contracts as K
from . import grammar as G, items, verbs
from .check_brain4 import hob, house
from .check_contracts import grammar as catalog
from .check_machine import thing


def parser(cfg):
    P = lambda *xs, **kw: G.parse(cfg, list(xs), **kw)
    catalog(True)   # (check_contracts: every recipe parses to v5.0's verbs within 0.2, but what it says changes on purpose)
    t = P("tube of reed")
    assert t["ok"] and "launch" not in t["verbs"] and any(u["verb"] == "launch" for u in t["unmet"]), "a tube alone throws nothing: %s" % t
    assert "strike" in P("blade of metal", "handle of wood")["verbs"] and "strike" not in P("blade of metal")["verbs"], "a blade strikes only on a handle"
    r = P("blade of fluff")
    assert r["refusal"] == "material" and r["words"].startswith("a blade can't be made of fluff: ") and r["words"].endswith(" would"), r
    alts = r["words"].split(": ")[1][:-len(" would")].replace(" or ", ", ").split(", ")
    assert 2 <= len(alts) <= 3 and all(G.made_of(G.data(), "blade", m) for m in alts), "the alternatives named are what a blade can be made of: %s" % alts
    r = P("tube of reed", "spring of metal")
    assert r["refusal"] == "with" and r["words"].startswith("a reed tube won't take a metal spring: ") and not r["ok"], r
    r = P("tube of wood", "spring of metal")
    assert r["ok"] and r["verbs"]["launch"] > 0.5 and r["tier"] == 2, r
    r = P("bulb of glass", "wire of wire", "cell of zinc", tier=2)
    assert r["refusal"] == "tier" and r["words"] == K.REFUSE["tier"], r
    assert P("bulb of glass", "wire of wire", "cell of zinc", tier=3)["verbs"].get("light"), "at tier 3 a hob may make a tier-4 thing"
    r = P("lens of glass", tier=1)
    assert r["refusal"] == "needs" and r["words"] == "a lens wants a flame or a wick before it can light", r
    assert P("lens of glass")["refusal"] is None, "the catalog's lens is a keepsake, no refusal"
    assert P("blade of metal", have=["wood"])["words"] == "there's no metal in the house"
    assert P("spring of brass", have=[])["refusal"] == "material" and P("piston of steel", "boiler of steel", "flame of oil", have=["oil"])["words"].endswith(K.MACHINE)
    assert P()["refusal"] == "empty" and P("wing of wood")["refusal"] == "unknown"
    w = P("box of wood", "casing of plank")
    assert w["wear"] == 0.5 and P("box of wood")["wear"] == 1.0, "a casing halves the wear"
    print("grammar: a tube alone throws nothing; a blade on a handle strikes; \"%s\"; \"%s\"; \"%s\""
          % (P("blade of fluff")["words"], P("tube of reed", "spring of metal")["words"], P("lens of glass", tier=1)["words"]))


def on51(cfg, on=True):
    cfg["v5"]["on"] = cfg["items"]["on"] = True
    cfg["grammar"]["on"] = on


async def resolve(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    on51(cfg)
    room = h["rooms"][pet["room"]]
    h.setdefault("invented", {})["pebble thrower"] = {"name": "pebble thrower", "a": "a", "use": "curio", "parts": [{"part": "tube", "material": "wood"}, {"part": "spring", "material": "metal"}],
                                                      "charge": "pebble", "by": pet["id"], "tick": h["tick"], "how": "a spring behind a tube throws pebbles", "for": "the mouse"}
    o = thing(eng, room, "thrower", "pebble thrower", "hard", pet["id"])
    it = items.of(h, cfg, o, "thrower", room)
    assert it["verbs"]["launch"] > 0.5 and it["tier"] == 2 and it["state"]["charge"] == {"shot": cfg["grammar"]["charge_full"]} and [p["part"] for p in it["parts"]] == ["tube", "spring"], it
    cfg["grammar"]["hit"] = 1.0
    h["creatures"].append({"id": "cm", "kind": "mouse", "room": room["id"], "pos": [3, 3], "nest": [3, 3], "doing": "", "since": 0, "until": 10 ** 9, "fed": {}, "carry": None, "trust": {}, "tame": None, "name": None})
    said, _, key = verbs.apply(h, cfg, pet, "thrower", "launch", "mouse")
    assert key == "launch" and "struck the mouse" in said and it["state"]["charge"]["shot"] == cfg["grammar"]["charge_full"] - 1, said
    assert not any(c["id"] == "cm" and c["room"] == room["id"] for c in h["creatures"]), "struck, the mouse is off"
    other = hob(eng, room, (4, 4))
    other["name"] = "Pim"
    said, _, key = verbs.apply(h, cfg, pet, "thrower", "launch", "Pim")
    assert key is None and "won't throw at Pim" in said, said
    it["state"]["charge"]["shot"] = 0
    said, _, key = verbs.apply(h, cfg, pet, "thrower", "launch", "mouse")
    assert key is None and said.endswith("it's empty"), said
    h["invented"]["pea shooter"] = dict(h["invented"]["pebble thrower"], name="pea shooter", charge=None)
    thing(eng, room, "shooter", "pea shooter", "hard", pet["id"])
    pot = thing(eng, room, "pot", "jar", "hard", pet["id"])
    said, _, key = verbs.apply(h, cfg, pet, "shooter", "launch", "pot")
    assert key is None and "nothing to throw" in said, said
    pet["carrying"] = ["pebble"]
    said, _, key = verbs.apply(h, cfg, pet, "shooter", "launch", "pot")
    assert key == "launch" and said.startswith("A pebble from the shooter struck the pot") and not pet["carrying"] and items.of(h, cfg, pot, "pot", room)["state"]["wear"] > 0, said
    print("grammar: launch: \"%s\"; a hob is never a target; empty is \"it's empty\"" % said)
    rope = thing(eng, room, "rope", "rope", "soft", pet["id"])
    assert items.of(h, cfg, rope, "rope", room)["verbs"].get("bind"), "rope binds (kinds.toml's `new`)"
    thing(eng, room, "cup a", "cup", "hard", pet["id"])
    thing(eng, room, "cup b", "cup", "hard", pet["id"])
    said, _, key = verbs.apply(h, cfg, pet, "rope", "bind", "Pim")
    assert key is None and "won't tie anyone up" in said, said
    said, _, key = verbs.apply(h, cfg, pet, "rope", "bind", "cup a and cup b")
    a = items.of(h, cfg, room["objects"]["cup a"], "cup a", room)
    assert key == "bind" and room["objects"]["cup b"]["on"] == "cup a" and str(room["objects"]["cup b"]["made"]["id"]) in a["state"]["holds"], said
    room["objects"].pop("cup a")   # (the bundle's base eaten, fed or carried off by a way that isn't `place`)
    items.sync(h, cfg)
    assert "on" not in room["objects"]["cup b"], "what was on a thing that left the room is on the floor (the rehearsal's KeyError: 'lamp shelf')"
    print("grammar: bind: \"%s\"" % said)
    box = dict(K.item({"id": "1", "kind": "box", "class": "store", "parts": [{"part": "box", "material": "wood"}, {"part": "casing", "material": "plank"}]}))
    bare = dict(K.item({"id": "2", "kind": "box", "class": "store", "parts": [{"part": "box", "material": "wood"}]}))
    items.wear(h, cfg, box)
    items.wear(h, cfg, bare)
    assert abs(box["state"]["wear"] * 2 - bare["state"]["wear"]) < 1e-9, (box["state"], bare["state"])
    # [grammar] off: v5.0's verbs exactly, no parts
    on51(cfg, False)
    for k, e in cfg["items5"]["kind"].items():
        v, _, _, ps, t = items.table(h, cfg, k)
        assert v == dict(e.get("verbs", {})) and ps == [] and t == 0, k
    lamp = thing(eng, room, "lamp", "lantern", "bright", pet["id"])
    assert items.of(h, cfg, lamp, "lamp", room)["verbs"] == {"light": 0.8} and lamp["item"]["parts"] == []
    on51(cfg)
    assert items.of(h, cfg, lamp, "lamp", room)["verbs"] == G.recipe(h, cfg, "lantern")["verbs"] and lamp["item"]["parts"], "and on again, the parser's"
    print("grammar: [grammar] off gives kinds.toml's hand verbs for all %d kinds, and no parts" % len(cfg["items5"]["kind"]))
    return eng, pet


async def migration(d):
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    on51(cfg)
    room = h["rooms"][pet["room"]]
    h.setdefault("migrated", {}).pop("v51_parts", None)
    look = [{"part": "flame", "at": None, "material": "hard", "color": "grey", "stuff": "wax"}, {"part": "lens", "at": "top", "material": "glassy", "color": "grey", "stuff": "glass"}]
    dud = {"name": "flap lamp", "a": "a", "use": "design", "design": True, "parts": look, "design_parts": [{"part": "flame", "material": "wax"}, {"part": "lens", "material": "glass"}, {"part": "jetpack", "material": "springy"}],
           "effects": ["light", "lift"], "works": [], "for": "light", "how": "", "size": "small", "by": pet["id"], "tick": 0, "key": "design:1"}
    h["design_kinds"] = {"flap lamp": dud, "gone thing": dict(dud, name="gone thing")}
    h.setdefault("invented", {})["springer"] = {"name": "springer", "a": "a", "use": "design", "design": True, "parts": [{"part": "tube", "material": "hard"}],
                                                "design_parts": [{"part": "tube", "material": "wood"}, {"part": "spring", "material": "springy"}], "effects": ["catch"], "works": ["catch"], "size": "small",
                                                "by": pet["id"], "tick": 0, "verbs": {"catch": 0.5}}
    thing(eng, room, "flapper", "flap lamp", "hard", pet["id"])
    items.of(h, cfg, room["objects"]["flapper"], "flapper", room)
    pet["design"] = {"name": "a plan"}
    pet.setdefault("wants", []).append({"what": "design", "key": "design:need|light", "text": "x", "done": "y", "since": 0})
    eng.items_migration()
    lines = eng.migration51
    report = Path(eng.dir) / "migration-v5.1.txt"
    assert report.exists() and "SPEC-v5.1 migration" in report.read_text(), "the report is written beside the house"
    n = len(cfg["items5"]["kind"])
    assert lines[0] == "parts: %d of %d catalog kinds have a recipe" % (n, n), lines
    assert "design_kinds" not in h and "flap lamp" in h["invented"] and "gone thing" not in h["invented"], "the duds go; one with a thing standing stays, invented"
    fl = items.of(h, cfg, room["objects"]["flapper"], "flapper", room)
    assert fl["verbs"].get("light") and [p["part"] for p in fl["parts"]] == ["flame", "lens"], "a dud's thing does what its parts do now: %s" % fl
    assert G.recipe(h, cfg, "springer")["parts"] == [{"part": "tube", "material": "wood"}, {"part": "spring", "material": "reed"}], "a class is a material of it"
    assert any("springer" in l and "catch" in l for l in lines), "a kind whose verbs move is listed, verb by verb: %s" % lines
    assert pet["design"] is None and not any(w["what"] == "design" for w in pet["wants"]) and any("changed verbs" in l for l in lines)
    assert eng.items_migration() == [] and eng.migration51 == [], "once a house"
    for l in lines:
        print("grammar: migration: %s" % l)


def tiers(cfg):
    """the owner (21 October 2026): a part's tier is the lower of its own and its material's; a wooden hinge is no mechanism."""
    from . import grammar
    h = {"invented": {}}
    assert grammar.parse(cfg, ["hinge of wood"])["tier"] == 0 and grammar.parse(cfg, ["hinge of metal"])["tier"] == 2
    assert grammar.key_tier(h, cfg, "kind:chest") == 1 and grammar.key_tier(h, cfg, "kind:key") == 2 and grammar.key_tier(h, cfg, "metal|forge") == 0
    print("grammar: a wooden hinge is tier 0, a chest tier 1 (its lid), a metal key tier 2; a process recipe reaches nothing")


def main():
    from . import world
    parser(world.load_config())
    tiers(world.load_config())
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(resolve(d + "/r"))
        asyncio.run(migration(d + "/m"))
    print("check_grammar: all passed")


if __name__ == "__main__":
    main()
