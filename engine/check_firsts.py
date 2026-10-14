"""Self-check for drive's firsts, bests, ambitions and being noticed (SPEC-v3.5.4 §6, §7, §9, §10 first half),
proved without a model.

    uv run python -m engine.check_firsts

Scripted minds only, in a temp folder of its own; a few seconds."""
import asyncio
import tempfile

from . import actions, feats, firsts, life, sleep, world
from .check import at, engine
from .tick import Mind
from .world import generate_room, new_pet


def feat(h, kind, n0):
    return [f for f in h.get("feats", {}).get("list", []) if f["kind"] == kind and f["n"] > n0]


async def run(d):
    cfg = world.load_config()
    cfg["weather"]["real"] = False
    D = cfg["drive"]
    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    at(eng, 10)
    pet.update(stage="adult", name="Open Hand", word="mother")
    pet["stage_at"]["adult"] = h["tick"]
    room = h["rooms"][pet["room"]]
    shop = generate_room(h, cfg, next(rid for rid, x in h["rooms"].items() if not x["type"]), "workshop")
    mem = eng.minds[pet["id"]].mem
    N = firsts.state(h, cfg)
    assert "kind:bowl" not in N["house"] and pet["room"] and "room:" + pet["room"] in N["house"], "a new house is seeded with what it has: the room it began in, no bowl"

    def make(p, kind, name, material="hard", carry=("wood", "wood"), size="small"):
        p.update(carrying=list(carry), sleep=None)
        p["needs"]["energy"] = 90.0
        a = {"type": "make", "recipe": {"name": name, "kind": kind, "material": material, "color": "blue", "size": size, "purpose": "a check"}, "near": "here"}
        why = actions.check(a, h, cfg, p, eng.minds[p["id"]].mem if p["id"] in eng.minds else mem)
        assert not why, "%s cannot make a %s: %s" % (label(p), kind, why)
        return actions.apply(h, cfg, p, a, eng.minds[p["id"]].mem if p["id"] in eng.minds else mem)[0]

    label = world.label
    n0 = h.get("feats", {}).get("n", 0)

    # ---- §6 a first is judged by what a thing is, never its name; three levels; the board and the moment ----
    make(pet, "bowl", "Moon Cup")
    f = feat(h, "first", n0)
    assert len(f) == 1 and f[0]["level"] == "house" and f[0]["key"] == "kind:bowl", "the first bowl in the house: %s" % f
    assert f[0]["text"] == "Open Hand made the first bowl in the house" and f[0]["board"] == "FIRST BOWL IN THE HOUSE: OPEN HAND", f[0]
    assert pet["glow"]["size"] == D["first_glow"]["house"] and "first bowl in the house" in pet["glow"]["why"], pet["glow"]
    assert any(m["kind"] == "first" and m["text"] == f[0]["text"] for m in h["moments"]), "and it is a moment"
    n1 = h["feats"]["n"]
    make(pet, "bowl", "Something Else Entirely")
    assert not feat(h, "first", n1), "the same kind in the same nature with another name is no first: %s" % feat(h, "first", n1)
    make(pet, "bowl", "Warm One", "warm", ("wood", "wood"))
    f = feat(h, "first", n1)
    assert len(f) == 1 and f[0]["key"] == "make:bowl|warm" and f[0]["text"] == "Open Hand made the first warm bowl in the house", "a bowl of another nature is a smaller first: %s" % f

    other = new_pet(h, cfg, room["id"], [3, 3], family=2)
    other.update(stage="adult", name="Stranger", laid=-10**6, born=h["tick"])
    kid = new_pet(h, cfg, shop["id"], [3, 3], parent=pet["id"], family=1)
    kid.update(stage="adult", name="Open Stone", laid=-10**6, born=h["tick"])
    pet["children"].append(kid["id"])
    for p in (other, kid):
        p["stage_at"]["adult"] = h["tick"]
        eng.minds[p["id"]] = Mind(eng, p)
    for _ in range(2):
        await eng.tick()
    n2 = h["feats"]["n"]
    make(other, "bowl", "Theirs")
    f = feat(h, "first", n2)
    assert f and f[0]["level"] == "family" and f[0]["board"] == "FIRST BOWL IN THE FAMILY: STRANGER" and other["glow"]["size"] == D["first_glow"]["family"], "the first bowl in another family: %s" % f
    n3 = h["feats"]["n"]
    make(kid, "bowl", "Mine Too")
    f = feat(h, "first", n3)
    assert f and f[0]["level"] == "own" and f[0]["board"] is None and f[0]["text"] == "Open Stone made a bowl for the first time" and kid["glow"]["size"] == 1, \
        "its own first, not the family's: %s" % f
    # (the same first is a first of its own only once)
    n4 = h["feats"]["n"]
    make(kid, "bowl", "Mine Again")
    assert not feat(h, "first", n4)

    # ---- §6 each further first in a day gives less, and at last nothing ----
    kid["firsts_today"], sizes = [h["clock"]["day"], 0], []
    for t in ("moss", "clay", "rain", "wood", "snow"):
        kid.pop("glow", None)
        firsts.first(h, cfg, kid, ["read:" + t])
        sizes.append(feats.shine(cfg, h, kid.get("glow")))
    assert sizes[0] == 3 and sizes[1] >= 1 and sizes[0] > sizes[1] >= sizes[2] and sizes[-1] == 0, "a house first is very proud, each further one less, then nothing: %s" % sizes
    reached = [r for r in ("moss", "clay", "rain", "wood", "snow") if "read:" + r in N["house"]]
    assert len(reached) == 5, "every first is kept, rewarded or not"

    # ---- the packet: its firsts, what nobody has done that is within reach ----
    text = firsts.lines(h, cfg, kid)
    assert "lately: you were the first in the house to have read about snow" in text, "the packet carries the family's and the house's newest firsts: %s" % text
    kid.update(carrying=["clay"], room=room["id"])
    assert "nobody in the house has ever" in firsts.lines(h, cfg, kid) or not any(b == "clay" for b, _ in cfg["craft"]["rules"]), firsts.lines(h, cfg, kid)
    assert not any(c.isdigit() for c in text), "no numbers: %s" % text

    # ---- §7 bests: a child is born knowing its parent's, and beating one is a big moment; equalling is nothing ----
    assert pet["bests"]["thing"]["v"] >= 1 and "bowl" in pet["bests"]["thing"]["words"]
    pet["needs"]["energy"] = 90.0
    life.lay_egg(h, cfg, pet, {"message": "Make what nobody has made."}, actions.clean)
    egg = h["pets"][pet["children"][-1]]
    egg["laid"] = -10**6
    await eng.tick()   # (it hatches)
    E = egg["elders"]
    assert E["thing"]["by"] == pet["id"] and E["thing"]["who"] == "Open Hand" and E["thing"]["v"] == pet["bests"]["thing"]["v"], "born knowing its parent's bests: %s" % E
    assert "a best of your family's to beat: Open Hand's finest thing" in firsts.lines(h, cfg, egg), firsts.lines(h, cfg, egg)
    # (the egg grows up at once, for the check, and makes a bowl just like its parent's: equal, nothing; then a finer thing)
    egg.update(stage="adult", name="Open Leaf", sleep=None, room=room["id"], pos=[4, 4])
    egg["stage_at"]["adult"] = h["tick"]
    egg["skill"] = {"making": 0.0}
    for _ in range(2):
        await eng.tick()
    n5 = h["feats"]["n"]
    make(egg, "bowl", "Like Mother's")
    assert not feat(h, "best", n5) and not E["thing"].get("beaten"), "equalling a parent's best is nothing: %s" % feat(h, "best", n5)
    egg["skill"] = {"making": 40.0}   # (very practised: what it makes is finer and bigger)
    make(egg, "mobile", "Far Finer", "hard", ("wood", "wood"))
    b = feat(h, "best", n5)
    assert b and b[0]["text"] == "Open Leaf made a finer mobile than Open Hand ever did" and b[0]["board"] == "A FINER MOBILE THAN OPEN HAND EVER MADE: OPEN LEAF", "beating a parent's best: %s" % b
    assert egg["glow"]["size"] == D["best_elder_glow"] and E["thing"]["beaten"], egg["glow"]
    n6 = h["feats"]["n"]
    make(egg, "mobile", "Finer Still", "hard", ("wood", "wood"))
    assert not feat(h, "best", n6), "beaten once is beaten: a parent's best is not a moment twice"

    # ---- §10 whoever is awake in the room sees it; the maker is glad of it ----
    assert egg["room"] == pet["room"] == other["room"]
    seen = [e for t, e in pet["events"] if e.startswith("you saw Open Leaf make a finer mobile than Open Hand ever did")]
    assert seen and [e for t, e in other["events"] if e.startswith("you saw Open Leaf")], "an onlooker is told what it saw: %s" % pet["events"][-4:]
    nb = [f for f in feat(h, "noticed", n5) if f["pet"] == egg["id"]]
    assert nb and "Open Hand" in nb[0]["text"] and "Stranger" in nb[0]["text"], "the maker was seen, by name: %s" % nb
    assert any("saw what you did" in e for t, e in egg["events"]), "and the maker is told it was seen"
    n7 = h["feats"]["n"]
    pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
    egg["skill"] = {"making": 40.0}
    had = len(pet["events"])
    make(egg, "cup", "Seen Once")
    assert len(pet["events"]) == had and any(e.startswith("you saw Open Leaf make the first cup") for t, e in other["events"]), "asleep, it sees nothing; awake, it does"
    pet["sleep"] = None

    # ---- §9 an ambition: taken at hatching (no model), always in the packet, reached by what it does, heard by its child ----
    A = egg["ambition"]
    assert A and A["text"] and A["kind"] in ("first", "build", "skill", "best") and "your ambition for your life: " + A["text"] in firsts.lines(h, cfg, egg), "taken at hatching: %s" % A
    firsts.take(h, cfg, kid, {"kind": "first", "key": "kind:box", "level": "own", "text": "make a box"})
    kid["room"] = room["id"]
    n8 = h["feats"]["n"]
    make(kid, "box", "My Box")
    a = feat(h, "ambition", n8)
    assert a and a[0]["text"] == "Open Stone did what it meant to do in its life: make a box" and a[0]["board"] and kid["ambition"]["done"] and kid["glow"]["size"] == D["ambition_glow"], a
    kid["needs"]["energy"] = 90.0
    life.lay_egg(h, cfg, kid, {"message": "Keep going."}, actions.clean)
    grand = h["pets"][kid["children"][-1]]
    assert any(t["kind"] == "ambition" and "make a box, and did it" in t["text"] for t in grand["told"]), "its child hears of it: %s" % grand["told"]
    grand["laid"] = -10**6
    await eng.tick()
    assert "set out in life to make a box, and did it" in firsts.lines(h, cfg, grand)
    assert grand["elders"]["thing"]["who"] in ("Open Stone", "Open Hand"), "the line's best, a parent's or an ancestor's: %s" % grand["elders"]

    # ---- §9 at night: a living pet with none is offered some and takes one; one that can no longer be done may change once ----
    pet.pop("ambition", None)
    offer = firsts.offer(h, cfg, pet)
    assert "\n  1. " in offer and "none yet" in offer, offer
    m = eng.minds[pet["id"]]
    m.brain.reply = {"dream": "a day", "changes": [], "ambition": {"pick": 2, "words": "make a thing nobody has made"}}
    pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
    await sleep.night(m)
    text, asks = m.brain.nights[-1]
    assert "ambition" in asks and "none yet" in text, asks
    assert pet["ambition"]["text"] == "make a thing nobody has made" and pet["ambition"]["plain"] and not pet["ambition"]["changed"], pet["ambition"]
    pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
    await sleep.night(m)
    assert "ambition" not in m.brain.nights[-1][1], "not asked again while it can be done"
    firsts.take(h, cfg, pet, {"kind": "first", "key": "kind:sculpture", "level": "house", "text": "be the first in the house to make a sculpture"})
    pet["ambition"]["changed"] = False
    firsts.mark(h, cfg, other, "kind:sculpture", h["tick"])
    assert "no longer be done" in firsts.offer(h, cfg, pet)
    firsts.took(h, cfg, pet, {"pick": 1})
    assert pet["ambition"]["changed"] and pet["ambition"]["key"] != "kind:sculpture" and firsts.offer(h, cfg, pet) == "", "changed once, and not again"

    # ---- an old house: its history is what has been done ----
    old = {"seed": 1, "tick": 500, "clock": h["clock"], "rooms": {"r1": {"id": "r1", "type": "attic", "by": "p1", "found": 3, "objects": {
        "Old Cup": {"made": {"recipe": {"kind": "cup", "material": "hard"}, "by": "p1", "tick": 10, "fine": 3}}}}},
        "gone_things": [{"recipe": {"kind": "vase", "material": "soft"}, "by": "p2", "made": 20}],
        "recipes": {"clay|warm": {"by": "p2", "tick": 30}}, "firsts": {"hammer": 40}, "moments": [],
        "pets": {"p1": {"id": "p1", "stage": "dead", "children": ["p2"], "family": 1, "rooms": {}, "name": "Old"},
                 "p2": {"id": "p2", "stage": "adult", "parent": "p1", "children": [], "family": 1, "rooms": {"r1": 3}, "name": "Young",
                        "tried": {"clay|warm": "fired clay"}, "made_kinds": ["vase|soft"], "skill": {"making": 4.0}}}}
    S = firsts.state(old, cfg)
    for k in ("kind:cup", "make:cup|hard", "kind:vase", "process:clay|warm", "tool:hammer", "room:r1"):
        assert k in S["house"], "seeded: %s" % k
    assert firsts.level(old, cfg, old["pets"]["p2"], "kind:cup") == "own" and firsts.level(old, cfg, old["pets"]["p2"], "kind:vase") is None
    assert old["pets"]["p2"]["elders"]["thing"]["who"] == "Old" and old["pets"]["p1"]["bests"]["thing"]["v"] > 0, "the bests of what is left"

    # ---- the pet's page: its ambition, its bests and its family's ----
    pg = firsts.page(h, cfg, egg)
    assert pg["ambition"]["text"] and [b for b in pg["own"] if b["what"] == "Finest thing made" and "mobile" in b["text"]] and pg["family"], pg


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))
    print("firsts check passed")


if __name__ == "__main__":
    main()
