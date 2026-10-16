"""Self-check for SPEC-v3.5.8 §3, §4 (engine/check_names.py checks §2's hob names): things are called what they are,
never numbered and never "some X"; a charm with a use is filed as what it is; a pet keeps its few newest charms and
what means something, and the rest is scrap; the spring clean comes once; scrap fed gives a base material back about
every three; the sweeper sweeps up scrap and loose bits, leaves what is kept, and brings them to the Works.
    uv run python -m engine.check_hobs"""
import asyncio
import re
import tempfile

from . import hub, machine, order, sweeper, things, wants, works, world
from .check import at, do, engine, load_config
from .check_machine import thing
from .world import generate_room

NUMBERS = re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|number)\b")


async def run(d):
    cfg = load_config()   # (the body still, so the steps below are the mind's)
    cfg["make"]["own_names"], cfg["weather"]["real"] = False, False
    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    pet.update(name="Pim")
    room = h["rooms"][pet["room"]]

    # ---- §3: bits and stuff are plain ----
    assert wants.some("clay") == "clay" and world.a("seed") == "a seed" and world.a("ink block") == "an ink block", "never 'some clay'"

    # ---- §3: a thing's everyday name is its kind and one telling word, never a number ----
    names = []
    for i in range(30):
        r = {"kind": "cushion", "material": "soft", "color": things.COLORS[i % 3], "size": 1 + i % 3}
        n = things.everyday(h, cfg, r, ["felt"], pet, room)
        room["objects"][n] = {"pos": [1, 1], "made": {"recipe": dict(r, name=n)}}
        names.append(n)
    assert names[:2] == ["felt cushion", "soft cushion"] and len(set(names)) == 30, names
    assert all(len(n.split()) <= 3 and not NUMBERS.search(n) and not n.startswith("some ") for n in names), names
    for n in names:
        del room["objects"][n]
    assert things.everyday(h, cfg, {"kind": "nest", "material": "soft", "color": "red", "size": 2}, ["fluff"], pet, room, "soft nest") == "soft nest", \
        "an honest name its maker gave stands"

    # ---- §3.1: honest kinds ----
    honest = lambda name, material="cool", purpose="": things.honest(cfg, {"kind": "charm", "name": name, "material": material, "purpose": purpose})
    assert honest("pressed clay tile") == "tile" and honest("father's tinder knot", "dark") == "tinder bundle" and honest("cellar draught stop", "hard") == "draught stopper"
    assert honest("leak seal patch", "hard") == "patch" and honest("rain stone charm three") == "charm" and honest("stone knife", "hard") == "charm", "never a tool by its name"
    assert honest("little thing", "soft", "to sit on by the fire") == "charm" and honest("small one", "soft", "a cushion for the cold floor") == "cushion"
    assert things.honest(cfg, {"kind": "bowl", "name": "rain tile", "material": "hard"}) == "bowl", "only a charm is refiled"

    # ---- §3: made by a mind: the everyday name, its own name as a title, and what is kept for its card ----
    pet["carrying"], pet["needs"]["energy"] = ["fluff"], 80.0
    r = await do(eng, pet, {"type": "observe"},
                 {"type": "make", "recipe": {"name": "Rain Rest Charm Three", "kind": "charm", "material": "soft", "color": "white", "size": "small",
                                             "purpose": "to keep"}, "near": "here"})
    made = {n: o for n, o in things.made(room).items() if o["made"]["by"] == pet["id"]}
    (n, o), = made.items()
    assert not r[1]["reason"] and n == "fluff charm" and o["made"]["recipe"]["title"] == "Rain Rest Charm Three", (r, made)
    assert o["made"]["how"] and o["made"]["made_in"] == room["name"] and o["made"]["bits"] == ["fluff"] and o["made"]["users"] == {}, o["made"]
    assert "Rain Rest Charm Three" in h["moments"][-1]["text"] or any("which it calls 'Rain Rest Charm Three'" in m["text"] for m in h["moments"][-3:])
    r = await do(eng, pet, {"type": "look", "target": "Rain Rest Charm Three"})
    assert not r[0]["reason"], "a pet may call its thing by its title: %s" % r
    things.used_by(h, o, pet)
    assert o["made"]["users"] == {pet["id"]: 1}, "who uses it"

    # ---- §4: what is kept, and what is scrap ----
    at(eng, 10, 6)   # (well into the house's life, so that what was made days ago was made after it began)
    for i in range(5):
        thing(eng, room, "charm %s" % "abcde"[i], "charm", "soft", pet["id"], days=5 - i)
    newest = order.newest_charms(h, cfg)
    scrap = {n for why, n in order.scraps(h, cfg, room)}
    assert scrap == {"charm a", "charm b"} and len(newest[pet["id"]]) == 3, "its three newest stay (and the fluff charm was a first): %s" % scrap
    thing(eng, room, "heir charm", "charm", "soft", pet["id"], days=9, on=None)["made"]["heirloom"] = {"from": "p0", "to": [pet["id"]], "tick": 0, "line": []}
    thing(eng, room, "starred charm", "charm", "soft", pet["id"], days=9)["made"]["star"] = 1
    thing(eng, room, "first charm", "charm", "soft", pet["id"], days=9)["made"]["first"] = True
    room["objects"]["keepsake box for Odo"] = {"pos": [8, 2], "fix": {"store": order.BOX, "inside": True, "keepsake": "p0"}}
    thing(eng, room, "boxed charm", "charm", "soft", pet["id"], days=9, on="keepsake box for Odo")
    thing(eng, room, "old cushion", "cushion", "soft", pet["id"], days=cfg["make"]["scrap_days"] + 1)
    thing(eng, room, "new cushion", "cushion", "soft", pet["id"], days=1)
    scrap = {n for why, n in order.scraps(h, cfg, room)}
    assert not scrap & {"heir charm", "starred charm", "first charm", "boxed charm", "new cushion"} and "old cushion" in scrap, scrap
    assert order.scraps(h, cfg, room)[0][0] == "charm", "charms first"

    # ---- §4: the spring clean comes once, and the old charms are wanted fed ----
    assert not works.spring(h, cfg), "a new house has no spring clean"
    del h["spring_clean"]
    works.spring_clean(h, cfg)
    works.spring_clean(h, cfg)
    assert sum(m["kind"] == "spring" for m in h["moments"]) == 1 and works.spring(h, cfg) and "spring clean" in pet["events"][-1][1]

    # ---- §4.1: scrap fed gives a base material back, about one for three ----
    hb = generate_room(h, cfg, hub.RID, by=pet["id"])
    machine.migrate(h, cfg)
    for i, n in enumerate(["charm a", "charm b", "old cushion"]):
        things.gone(h, room["objects"].pop(n), n, "fed to the machine", room)
        h["gone_things"][-1]["bits"] = ["clay"]
        said = machine.scrap_back(h, cfg, pet, hb, [n])
        assert bool(said) == (i == 2), (i, said)
    assert "a piece of clay" in said and "clay" in pet["carrying"] + [s["bit"] for s in hb["spots"]], said

    # ---- §4.2: the sweeper sweeps up scrap and loose bits, leaves what is kept, and brings it to the Works ----
    sweeper.make(h, cfg)
    sweeper.make(h, cfg)
    sw, = [c for c in h["creatures"] if c["kind"] == "sweeper"]
    assert sw["docked"] and sweeper.DOCK in hb["objects"], sw
    thing(eng, hb, "junk charm", "charm", "soft", pet["id"], days=9)
    thing(eng, hb, "kept charm", "charm", "soft", pet["id"], days=9)["made"]["heirloom"] = {"from": "p0", "to": [pet["id"]], "tick": 0, "line": []}
    things.drop_bits(h, cfg, hb, [6, 6], ["wood"])
    have = works.state(h, cfg)["have"]
    sw["charged"] = -10 ** 6
    at(eng, 11, 6)
    for _ in range(round(cfg["ticks_per_hour"] * 4)):   # (out for its round, then home)
        h["tick"] += 1
        sweeper.step(h, cfg, sw)
    gone = [g["name"] for g in h["gone_things"] if "sweeper" in g["gone"][1]]
    assert "junk charm" in gone and "kept charm" in hb["objects"] and not order.loose_bits(hb), (gone, sw)
    assert works.state(h, cfg)["have"] > have or works.state(h, cfg)["built"], "what it brings counts as scrap"
    assert any(m["kind"] == "sweeper" and "brought" in m["text"] for m in h["moments"]), "it goes in the story"
    print("hobs check passed")


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))


if __name__ == "__main__":
    main()
