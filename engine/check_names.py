"""Self-check for hob names (SPEC-v3.5.8 §2, §7.1): names.toml and engine/names.py, proved without a model.

    uv run python -m engine.check_names

Scripted minds only, in a temp folder of its own; a few seconds."""
import asyncio
import tempfile

from . import actions, life, names, world
from .check import engine


async def run(d):
    cfg = world.load_config()
    cfg["weather"]["real"] = False
    N = cfg["names"]
    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    pet.update(stage="adult", name="Garry", sleep=None, eggs=0)
    pet["temper"]["fertile"] = 1.0
    mem = eng.minds[pet["id"]].mem

    # ---- the rules ----
    assert len(N["bank"]) >= 2000, "thousands of names in the bank: %d" % len(N["bank"])
    bad = {n: names.check(h, cfg, n) for n in N["bank"] if names.check(h, cfg, n) and n != "Garry"}
    assert not bad, "every name in the bank is a name: %s" % bad
    assert all(names.rules(h, cfg, n) is None for n in N["life"].values()), "and every name a word of its life becomes"
    for n in ("Rain Rest", "Open Hand", "Grey Light II", "Open Hour", "Second One", "Lights Fall", "Rainrest", "Open-Hand", "Little Hum", "Quiet",
              "Soft Stop", "Xkcdq", "Bartholomew Wobbleworth", "Pim2", "Garry"):
        assert names.check(h, cfg, n), "not a name: %s" % n
    for n in ("Pim", "Odo", "Clementine", "Bartholomew", "Mothball", "Sir Pebbleworth", "Juniper", "Biscuit", "Orion", "Tamsin", "Wobble", "Garry II"):
        assert names.check(h, cfg, n) is None, "a name: %s (%s)" % (n, names.check(h, cfg, n))
    assert "light" in names.family_words(h, cfg) and names.check(h, cfg, "Zappa") is None
    other = world.new_pet(h, cfg, pet["room"], [2, 2], name="Bobo Zappa")
    assert names.check(h, cfg, "Zappa"), "a hob's two-word name is the family's words from then on"
    del h["pets"][other["id"]]

    # ---- the family's sound: it drifts, and stays recognisable ----
    for fam in range(1, 7):
        s1, drifted = names.sound(h, fam, 1), False
        for gen in range(1, 9):
            s = names.sound(h, fam, gen)
            assert s["cons"][0] == s1["cons"][0] and s["vowels"][0] == s1["vowels"][0], "a family keeps its flavour"
            drifted |= s != s1
            r = world.rnd(h, "test", fam, gen)
            assert all(names.in_sound(s, r).lower().startswith(s1["cons"][0]) for _ in range(5))
        assert drifted, "and drifts a little, generation by generation: %s" % fam
        assert str(fam) in h["sounds"], "kept in the house"

    # ---- five offers from five sources ----
    pet["name_finds"] = [{"name": "Aquila", "why": "from the screen, in a page about Eagle", "tick": h["tick"]}]
    gran = world.new_pet(h, cfg, pet["room"], [1, 1], name="Odo")
    gran.update(stage="dead", children=[pet["id"]])
    pet["parent"], pet["met"] = gran["id"], {"moth": 3}
    offs = names.offers(h, cfg, pet)
    assert [o["source"] for o in offs] == ["screens", "bank", "sound", "honour", "life"], offs
    assert offs[0]["name"] == "Aquila" and offs[3]["name"] == "Odo II" and "Odo" in offs[3]["why"], offs
    assert len({o["name"] for o in offs}) == 5 and all(names.check(h, cfg, o["name"]) is None for o in offs)
    assert offs == names.offers(h, cfg, pet), "the same hob at the same tick: the same names"
    new = names.offers(h, cfg, pet, for_family=3)
    assert len(new) == 5 and new[3]["source"] == "bank", "a new family has nobody to honour: the bank fills in"
    line = names.line(h, cfg, pet)
    assert line.startswith("names you could give your egg: Aquila (from the screen") and line.endswith("not a phrase")

    # ---- no living duplicate: an honoured name is numbered, and a name taken is not offered again ----
    gran["stage"] = "elder"
    for t in range(40):
        offs = names.offers(h, cfg, pet, tick=h["tick"] + t * 97)
        assert not any(names.living(h, o["name"]) for o in offs), offs
        assert "Odo" not in [o["name"] for o in offs]
    gran["stage"] = "dead"

    # ---- a phrase becomes a by-name; a name is taken ----
    pet["last_call"] = h["tick"]
    first = names.offers(h, cfg, pet, tick=h["tick"])[0]["name"]
    text, _, _ = life.lay_egg(h, cfg, pet, {"message": "Keep warm.", "name": "Rain Rest"}, actions.clean)
    egg = h["pets"][pet["children"][-1]]
    assert egg["name"] == first and egg["byname"] == "Rain Rest", egg
    assert '"Rain Rest" is made of your family\'s words, not a name, so the egg is called %s' % first in text, text
    life.lay_egg(h, cfg, pet, {"message": "Keep warm.", "name": "Juniper"}, actions.clean)
    egg = h["pets"][pet["children"][-1]]
    assert egg["name"] == "Juniper" and "byname" not in egg
    found = world.new_pet(h, cfg, pet["room"], [3, 3], family=2)
    h["v31"]["arrived"]["taming"] = h["tick"]
    a = {"type": "name", "what": "egg", "name": "Open Hand"}
    assert actions.check(a, h, cfg, pet, mem) is None, actions.check(a, h, cfg, pet, mem)
    said = actions.apply(h, cfg, pet, a, mem)[0]
    assert found["byname"] == "Open Hand" and found["name"] != "Open Hand" and names.rules(h, cfg, found["name"]) is None and found["name"] in said

    # ---- naming itself: a real name, or nothing (the visitor's always wins) ----
    kid = h["pets"][pet["children"][0]]
    kid.update(stage="hatchling", name=None, born=h["tick"])
    actions.speak(h, cfg, kid, {"type": "speak", "text": "My name is Dusk."}, None)
    assert kid["name"] is None, "a family word is not a name it can take"
    actions.speak(h, cfg, kid, {"type": "speak", "text": "My name is Wobble."}, None)
    assert kid["name"] == "Wobble"
    kid.update(called="Rain Rest")
    actions.speak(h, cfg, kid, {"type": "speak", "text": "I am Rain Rest."}, None)
    assert kid["name"] == "Rain Rest", "the visitor's name wins"

    # ---- the screens: real names from a page ----
    text = ("Eagles are large birds of prey. Most belong to the genus Aquila, and live in Africa and Eurasia. The word comes from Latin. "
            "Some nest in rosemary and thyme. Rain falls.")
    got = names.found_in(h, cfg, "Eagle", text)
    assert {"Aquila", "Africa", "Eurasia", "Rosemary", "Thyme"} <= set(got) and "Latin" not in got and "Rain" not in got and "Eagles" not in got, got
    pet["eggs"] = 0
    assert names.wanted(h, cfg, pet) == "your egg"
    pet["eggs"], found["name"] = life.fertility(pet), None
    assert names.wanted(h, cfg, pet) == "the egg that is nobody's"
    found["name"] = "Basil"
    assert names.wanted(h, cfg, pet) is None, "no egg to come, and none that wants a name"
    eng.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))
    print("names check passed")


if __name__ == "__main__":
    main()
