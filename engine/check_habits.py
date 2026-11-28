"""Self-check for SPEC-v5.3 §1, §4 and §9's habits (helper B), on stub houses with v5.3 on: a collect hob's pile, that a
fussy hob counts as mess and moves, and its owner resents; a take hob's hoard, the owner missing its thing and
suspecting, the hoard found and opinions of the hoarder falling; a praise hob raising pride and an envious hob
resenting it; a habit fading; a child copying its parent and a tale leaving one; the draw, the plan packet's line and
block, the migration's report; [habits] off leaves the house as v5.1's.
    uv run python -m engine.check_habits"""
import asyncio
import os
import tempfile

from . import brain4, habits, opinions, order, planner, world
from . import contracts as K
from .check_brain4 import hob, house
from .check_machine import thing


def on53(cfg, on=True):
    cfg["v5"]["on"] = cfg["items"]["on"] = True
    cfg["spirit"]["on"] = cfg["memory2"]["on"] = True
    cfg["habits"]["on"] = on


def hourly(eng):
    """Move the clock to the next world hour's first tick and run the habits' tick."""
    h, n = eng.house, max(1, round(eng.cfg["ticks_per_hour"]))
    h["tick"] += (-h["tick"]) % n or n
    habits.tick(h, eng.cfg)


def give(eng, pet, name, target, place=None, **more):
    h = eng.house
    pet["habits"] = habits.of(pet) + [K.habit(dict({"name": name, "verb": habits.TEMPLATES[name]["verb"], "target": target, "place": place,
                                                    "pace": habits.TEMPLATES[name]["pace"], "since": h["tick"]}, **more))]
    pet["habit_drawn"] = h["tick"]
    return pet["habits"][-1]


def ev(h, what, **match):
    return [e for e in K.events53(h, what) if all(e.get(k) == v for k, v in match.items())]


async def pile(d):
    """§6.1's facts: a pile grows (each go through planner.check), a fussy hob counts it as mess, tidies it away (as the
    tidy routine does), and its owner resents the mover."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on53(cfg)
    room = h["rooms"][p0["room"]]
    brody = hob(eng, room, [2, 2], orderly=0.0)
    brody.update(name="Brody", sleeps_in=room["id"])
    hb = give(eng, brody, "collect", "sticks", {"room": room["id"], "pos": [1, 1]})
    for i in range(4):
        brody["carrying"] = ["wood"]
        a = habits.give(h, cfg, brody)
        assert a and a["habit"] == "collect" and a.get("carry") == "wood" and a["target"] == room["id"], a
        brody["aims"] = [a]
        planner.check(h, cfg, brody)   # (its clock starts: an aim not yet begun is not done)
        planner.check(h, cfg, brody)
        assert a["done"] and "wood" not in brody["carrying"], "the go is done through planner.check: %s" % a
        hb["last"] -= 10 ** 6   # (due again at once)
    m = habits.marks(h, room["id"])[0]
    assert m["kind"] == "pile" and m["n"] == 4 and hb["count"] == 4 and len(habits.pile_spots(room, m["id"])) == 4
    assert [1, 1] in world.taken(h, room), "a pile's tile is taken"
    assert not any(s.get("pile") and s["ready"] for s in room["spots"]), "nobody gathers from another's pile"
    assert "Brody's stick pile fills" in m["words"] and len(ev(h, "habit", pet=brody["id"], habit="collect")) == 4 and K.counts(h)["habit"]["collect"] == 4
    p0.update(name="Pansy", voice={"style": "fussy", "cares": ""})
    p0["temper"]["orderly"] = 1.0
    hourly(eng)
    assert ev(h, "noticed", pet=p0["id"], mark=m["id"]) and ev(h, "mess", pet=p0["id"], mark=m["id"], owner=brody["id"]), "the fussy count a pile as mess"
    assert any("stick pile" in x["text"] for x in p0["memories"]), "and remember it, a memory with tags"
    assert habits.seen(h, cfg, p0) and "stick pile" in habits.block(h, cfg, p0)
    thing(eng, room, "basket", "basket", "soft", p0["id"])
    job = order.job(h, cfg, p0, room)
    assert job and job["job"][0] == "bits", job
    was = opinions.of(brody, p0["id"])["liking"]
    while habits.pile_spots(room, m["id"]):
        order.do_job(h, cfg, p0, room, order.job(h, cfg, p0, room)["job"])
    assert m["gone"] is not None and ev(h, "moved", pet=p0["id"], owner=brody["id"], mark=m["id"])
    assert ev(h, "resent", pet=brody["id"], against=p0["id"], cause="pile") and opinions.of(brody, p0["id"])["liking"] < was, "the owner resents the mover"
    assert len(ev(h, "resent", pet=brody["id"])) == 1, "once a while, however many pawfuls"
    print("habits: a pile grows a go at a time; the fussy count it as mess and move it; its owner resents it")
    return eng


async def hoard(d):
    """§6.2's facts: a thief takes while unseen to its box; the owner misses it and suspects; the hoard is found, a
    moment; the finders think the hoarder dishonest; the owner has its thing back."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on53(cfg)
    a_id = p0["room"]
    b_id = next(r for r in sorted(h["rooms"]) if h["rooms"][r]["type"] and r != a_id)
    A, B = h["rooms"][a_id], h["rooms"][b_id]
    p0.update(name="Pansy")
    lev = hob(eng, A, [3, 3], honest=0.0, generous=0.0)
    lev.update(name="Lev", sleeps_in=b_id, flaw=K.flaw({"name": "greedy"}))
    lev["rooms"][b_id] = h["tick"]
    thing(eng, B, "box", "box", "hard", lev["id"])
    bead = thing(eng, A, "glass bead", "bead", "glassy", p0["id"])
    give(eng, lev, "take", "shiny")
    assert habits.weight(habits.TEMPLATES["take"], habits.keys_of(h, cfg, lev)) > 0, "greedy and sly draw take"
    p0["sleep"] = True
    habits.tick(h, cfg)
    assert "glass bead" in B["objects"] and bead["on"] == "box" and bead["taken"]["by"] == lev["id"], "taken unseen to its box"
    assert ev(h, "taken", pet=lev["id"], owner=p0["id"], thing="glass bead", seen=False)
    hm = next(m for m in habits.marks(h, b_id) if m["kind"] == "hoard")
    assert "Lev keeps a box" in hm["words"] and hm["n"] == 1
    p0["sleep"] = False
    h["tick"] += 3
    p0["rooms"][a_id] = h["tick"]
    hourly(eng)
    assert ev(h, "missed", pet=p0["id"], thing="glass bead", suspect=lev["id"]), "the owner misses it and suspects whoever was there last"
    assert any("glass bead" in x["text"] and lev["id"] in x["about"] for x in p0["memories"]), "a memory with content, for gossip"
    assert any(e["kind"] == "missed" for e in p0.get("notable", [])), "the react packet's event"
    liking = opinions.of(p0, lev["id"])["liking"]
    p0["room"], p0["pos"] = b_id, [4, 4]
    hourly(eng)
    assert hm["found"] is not None and ev(h, "found", pet=p0["id"], owner=lev["id"], mark=hm["id"])
    assert any(m_["kind"] == "hoard found" and "glass bead" in m_["text"] for m_ in h["moments"]), "a moment, and the page's banner"
    assert ev(h, "opinion", pet=p0["id"], about=lev["id"], cause="dishonest") and opinions.of(p0, lev["id"])["liking"] < liking
    assert not bead.get("on") and not bead.get("taken"), "its own thing back"
    assert any(e["kind"] == "found" and "inside" in e["text"] for e in p0.get("notable", [])), "found, as an event: what was inside"
    print("habits: taken unseen to a box; missed and suspected; the hoard found, a banner; the hoarder thought dishonest")


async def praise(d):
    """§6.4's facts: praise raises the other's pride; an envious hob here resents the praised one."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on53(cfg)
    room = h["rooms"][p0["room"]]
    sunny = hob(eng, room, [2, 2], kind=1.0)
    sunny.update(name="Sol", voice={"style": "sunny", "cares": ""})
    envious = hob(eng, room, [6, 6])
    envious.update(name="Wen", flaw=K.flaw({"name": "envious"}))
    give(eng, sunny, "praise", "")
    p0["last_made"] = {"tick": h["tick"], "name": "cup"}
    p0["needs"]["pride"] = 40.0
    hourly(eng)
    pr = ev(h, "praise", pet=sunny["id"], to=p0["id"])
    assert pr and pr[0]["pride"] > 0 and p0["needs"]["pride"] > 40, "pride rises"
    assert ev(h, "resent", pet=envious["id"], against=p0["id"], cause="praise") and ev(h, "opinion", pet=envious["id"], about=p0["id"], cause="envy")
    hourly(eng)
    assert len(ev(h, "praise", pet=sunny["id"])) == 1, "once a day"
    print("habits: praise raises another's pride, once a day; the envious resent it")


async def lives(d):
    """Fading, copying, a tale's habit, the draw, the packet, the migration; and a stub run with it all on."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on53(cfg)
    room = h["rooms"][p0["room"]]
    day = cfg["ticks_per_day"]
    hb = give(eng, p0, "watch", "")
    hb["last"] = h["tick"] - 8 * day
    habits.fade(h, cfg, p0)
    assert hb["fading"] and not habits.live(p0) and habits.give(h, cfg, p0) is None, "a week without a go: it fades"
    h["tick"] += 8 * day
    habits.fade(h, cfg, p0)
    assert not habits.of(p0), "and a fortnight: gone"
    kid = hob(eng, room, [3, 3], stage="child")
    kid["parent"] = p0["id"]
    hb = give(eng, p0, "collect", "pebbles", {"room": room["id"], "pos": [1, 1]})
    d0 = h["clock"]["day"]
    for i in range(cfg["habits"]["copy_days"]):
        h["clock"]["day"] = d0 + i
        habits.went(h, cfg, p0, hb, "a go")
    assert habits.find(kid, "collect") and habits.find(kid, "collect")["from"] == "parent", "a child that sees it daily for a week copies it"
    h["clock"]["day"] = d0
    kid2 = hob(eng, room, [4, 4], stage="child")
    dead = hob(eng, room, [5, 5], stage="elder")
    give(eng, dead, "mark", "wall")
    dead["stage"] = "dead"
    assert habits.told(h, cfg, kid2, {"about": dead["id"]})["from"] == "tale", "a tale leaves the dead one's habit"
    yo = hob(eng, room, [6, 6], stage="youngling")
    yo["temper"]["orderly"] = 1.0
    got = habits.draw(h, cfg, yo, 2)
    assert len(got) == 2 and all(habits.weight(habits.TEMPLATES[x["name"]], habits.keys_of(h, cfg, yo)) > 0 for x in got)
    assert all(x["name"] != "take" for x in got), "take needs greed and slyness"
    assert habits.line(h, cfg, yo).startswith("your habits: you tend to ")
    packet, ctx = brain4.plan_packet(h, cfg, yo, eng.minds[yo["id"]].mem)
    assert "your habits: you tend to" in packet, packet
    assert set(habits.ACT) == set(habits.SEEN) == set(K.HABITS)
    old = hob(eng, room, [7, 7], stage="adult")
    h.get("migrated", {}).pop("v53_habits", None)
    lines = habits.migrate(h, cfg)
    assert habits.of(old) and any(world.label(old) in l for l in lines) and habits.migrate(h, cfg) == []
    for l in lines:
        print("habits: migration: %s" % l)
    for _ in range(400):
        await eng.tick()
    assert not [k for k in eng.step_errors if "habits" in k], eng.step_errors
    print("habits: fading, copying, a tale's habit, the draw, the plan packet's line, the migration; 400 stub ticks on")


async def off(d):
    """[habits] off: no habits, no marks, no events, nothing in the packet (v5.1's house)."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on53(cfg, False)
    room = h["rooms"][p0["room"]]
    yo = hob(eng, room, [6, 6], stage="youngling")
    for _ in range(300):
        await eng.tick()
    assert not any(p.get("habits") or p.get("habit_drawn") for p in h["pets"].values())
    assert not (h.get("v5") or {}).get("marks") and not (h.get("v5") or {}).get("events53") and "v53_habits" not in h.get("migrated", {})
    assert habits.line(h, cfg, yo) == "" and habits.migrate(h, cfg) == [] and habits.draw(h, cfg, yo) == []
    packet, _ = brain4.plan_packet(h, cfg, yo, eng.minds[yo["id"]].mem)
    assert "your habits" not in packet and "about the house" not in packet
    print("habits: [habits] off: no habits, no marks, no events, nothing in the packet (300 stub ticks)")


def main():
    base = os.environ.get("PET_SCRATCH")
    with tempfile.TemporaryDirectory(dir=base) as d:
        asyncio.run(pile(d + "/p"))
        asyncio.run(hoard(d + "/h"))
        asyncio.run(praise(d + "/r"))
        asyncio.run(lives(d + "/l"))
        asyncio.run(off(d + "/o"))
    print("check_habits: all passed")


if __name__ == "__main__":
    main()
