"""Self-check for the Works, the board and the visitor's star (SPEC-v3.5.4 §8, §11, §10): works.toml, engine/works.py
and engine/board.py, proved without a model.

    uv run python -m engine.check_works

Scripted minds only, in a temp folder of its own; a few seconds."""
import asyncio
import re
import tempfile

from . import actions, board, feats, hub, machine, wants, works, world
from .check import at, engine, scripted
from .check_machine import thing
from .tick import Engine
from .world import generate_room


async def run(d):
    cfg = world.load_config()
    cfg["weather"]["real"] = False
    W, D = cfg["works"], cfg["drive"]
    costs = [b["scrap"] for b in W["build"] if not b.get("sweeper") and not b.get("rail") and not b.get("dock")]   # (SPEC-v3.5.8 §4.2: the sweeper is next, whatever it costs; SPEC-v3.5.12 §3: so is the rail; SPEC-v3.6a §1: and the dock)
    assert W["build"][0]["what"] == "a lamp for the cellar" and costs == sorted(costs), "cheapest first, the lamp for the cellar first"
    for b in W["build"]:
        assert sum(k in b for k in ("fixture", "machine", "material", "sweeper", "rail", "dock")) == 1, "each does one thing: %s" % b["what"]
        assert all(k in cfg["machine"] for k in b.get("machine", {})) and b.get("material", "wood") in cfg["house"]["bits"], b
        assert not b.get("material") or b["material"] not in cfg["machine"]["materials"], "a new material, not one it holds"

    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    at(eng, 10, 6)   # (well into the house's life, so that what was made days ago was made after it began)
    pet.update(stage="adult", name="Lean", sleep=None)
    mem = eng.minds[pet["id"]].mem
    hb = generate_room(h, cfg, hub.RID, by=pet["id"])
    cellar = generate_room(h, cfg, next(rid for rid, x in h["rooms"].items() if not x["type"]), "cellar")
    music = generate_room(h, cfg, next(rid for rid, x in h["rooms"].items() if not x["type"]), "music")
    S = works.state(h, cfg)

    def go(p, room, carrying=()):
        p.update(room=room["id"], pos=[2, 2], carrying=list(carrying), sleep=None)
        p["rooms"][room["id"]] = h["tick"]

    def feed(what, back=None):
        a = {"type": "machine_feed", "what": what}
        a["for"] = back or machine.offers(h, cfg, pet, hb, what)[0]
        why = actions.check(a, h, cfg, pet, mem)
        assert not why, why
        return actions.apply(h, cfg, pet, a, mem)

    # ---- §8 the goal, said in words ----
    go(pet, hb)
    assert works.goal(h, cfg)["what"] == "a lamp for the cellar" and works.view(h, cfg)["line"] == "THE WORKS NEEDS %d SCRAP: A LAMP FOR THE CELLAR" % costs[0]
    said = machine.sense(h, cfg, pet)[-1]
    assert "lamp for the cellar" in said and "nothing in it yet" in said and not re.search(r"\d", said), "the packet at the machine says the goal, never a number: %s" % said

    # ---- the meter fills from feeding: an old made thing, and three bits ----
    thing(eng, hb, "old cup", "cup", "hard", pet["id"], days=2)
    text, fx, _ = feed("old cup")
    assert S["have"] == W["works"]["thing"] and S["fed"] == {pet["id"]: 1}, S
    assert "the Works took it as scrap for a lamp for the cellar" in text and fx == cfg["build"]["build"]["lift"], "rewarded like a paw in a build: %s %s" % (text, fx)
    go(pet, hb, ["fluff", "pebble", "wax"])
    feed("bits")
    assert S["have"] == W["works"]["thing"] + W["works"]["bits"], "three bits are scrap too"

    # ---- the same thing counts once ----
    have = S["have"]
    again = thing(eng, hb, "old cup again", "cup", "hard", pet["id"], days=2)
    again["made"]["id"] = S["counted"][0]   # (the same thing, back again)
    text, fx, _ = feed("old cup again")
    assert S["have"] == have and "Works" not in text and fx == {}, "a thing fed twice counts once"

    # ---- no loop: a thing made of what the machine just gave, fed straight back, is no scrap ----
    pet["machine"] = {}
    go(pet, hb)
    take = {"type": "machine_take", "what": "clay"}
    assert not actions.check(take, h, cfg, pet, mem)
    actions.apply(h, cfg, pet, take, mem)
    thing(eng, hb, "new bowl", "bowl", "hard", pet["id"], days=0)
    text, fx, _ = feed("new bowl")
    assert S["have"] == have and fx == {} and "clay" in pet["carrying"], "fresh from the machine and straight back: nothing for the Works, so nothing goes round"
    assert works.counts(h, cfg, thing(eng, hb, "aged bowl", "bowl", "hard", pet["id"], days=W["works"]["age_hours"] / 24 + 0.01)), "once it has lain a while it is scrap"
    del hb["objects"]["aged bowl"]

    # ---- pets feel it: the want to feed a spare thing is the Works' too; nearly full, an old thing of its own is wanted for it ----
    thing(eng, hb, "spare jug", "charm", "hard", pet["id"], days=3)
    c = [x for x in wants.candidates(h, cfg, pet) if x["key"] == "feed:spare jug"]
    assert c and "the Works wants scrap for a lamp for the cellar" in c[0]["text"], "a spare thing is wanted for the Works: %s" % c
    del hb["objects"]["spare jug"]
    thing(eng, hb, "kept jug", "charm", "hard", pet["id"], days=1.5)
    thing(eng, hb, "newest jug", "charm", "hard", pet["id"], days=1.2)
    S["have"] = costs[0] - 1
    assert works.nearly(h, cfg) and "nearly full" in works.full(h, cfg)
    c = [x for x in wants.candidates(h, cfg, pet) if x["what"] == "feed" and x.get("thing") not in (None, "bits")]
    assert [x["thing"] for x in c] == ["kept jug"] and "the Works is nearly full: it wants scrap for a lamp for the cellar; your old kept jug" in c[0]["text"], \
        "nearly full, an old thing of its own (not the newest it made) is wanted for it: %s" % c

    # ---- a full meter builds the next thing, with its effect, and names who fed it ----
    other = world.new_pet(h, cfg, hub.RID, [8, 4])
    other.update(stage="adult", born=h["tick"], sleep=None, name="Rain")
    S["fed"][other["id"]], S["have"] = 9, costs[0] - 1   # (whoever fed it most is named first)
    text, fx, _ = feed("kept jug")
    assert "has built a lamp for the cellar" in text and S["goal"] == 1 and S["have"] == 0 and S["fed"] == {}, text
    lamp = cellar["objects"].get("lamp")
    assert lamp and lamp["state"] == "on" and lamp["fix"].get("light") == "on" and lamp["pos"] == W["build"][0]["fixture"]["pos"], "the lamp stands in the cellar, lit: %s" % lamp
    assert any(f["name"] == "lamp" for f in cfg["house"]["rooms"]["cellar"]["fixtures"]), "and any cellar found later has it too"
    f = h["feats"]["list"][-1]
    assert f["kind"] == "works" and f["text"] == "The Works built a lamp for the cellar, fed by Rain and Lean" and f["board"].startswith("THE WORKS BUILT A LAMP FOR THE CELLAR: "), f
    assert set(f["pets"]) == {pet["id"], other["id"]} and any(m["kind"] == "works" for m in h["moments"])
    assert pet["glow"]["size"] == other["glow"]["size"] == 2 and "it has built a lamp for the cellar" in other["glow"]["why"], "everyone who fed it is proud"
    works.lay(h, cfg)
    assert sum(1 for n in cellar["objects"] if n == "lamp") == 1 and sum(1 for f in cfg["house"]["rooms"]["cellar"]["fixtures"] if f["name"] == "lamp") == 1, "laid once"
    assert works.goal(h, cfg)["what"] == "a shelf for the music room"
    for i in (1, 2, 3):   # the shelf, a bigger delivery, and wax in the machine
        S["have"] = works.goal(h, cfg)["scrap"] - 1
        thing(eng, hb, "filler %d" % i, "cup", "hard", pet["id"], days=2)
        feed("filler %d" % i)
    assert music["objects"]["shelf"]["fix"]["store"] == 4 and cfg["machine"]["restock"] == 3, "a shelf in the music room; a bigger morning delivery"
    assert "wax" in cfg["machine"]["materials"] and machine.state(h, cfg)["stock"]["wax"] > 0 and "wax" in machine.takeable(h, cfg, other), "and wax to be had from the machine"
    S["have"] = works.goal(h, cfg)["scrap"]   # full, but nobody feeds it again: it builds when the house is loaded
    eng.save()
    eng.close()
    cfg2 = world.load_config()
    cfg2["weather"]["real"] = False
    assert "wax" not in cfg2["machine"]["materials"]
    back = Engine(cfg2, d + "/a", scripted)
    assert "wax" in cfg2["machine"]["materials"] and cfg2["machine"]["restock"] == 3 and any(f["name"] == "lamp" for f in cfg2["house"]["rooms"]["cellar"]["fixtures"]), \
        "what it built stays built when the house is loaded again"
    assert "lamp" in back.house["rooms"][cellar["id"]]["objects"] and works.goal(back.house, cfg2)["what"] == W["build"][5]["what"], "a full goal built on load"
    assert works.state(back.house, cfg2)["built"][-1]["what"] == W["build"][4]["what"] and works.state(back.house, cfg2)["have"] == 0
    back.close()

    # ---- §11 the board: everyone gets a turn ----
    eng, pet = engine(cfg, d + "/b")
    h = eng.house
    at(eng, 10, 6)
    hb = generate_room(h, cfg, hub.RID)
    pets = [pet] + [world.new_pet(h, cfg, hub.RID, [3 + i, 4]) for i in range(4)]
    for i, p in enumerate(pets):
        p.update(stage="child" if i == 2 else "adult", name="P%d" % i, sleep=None, room=hub.RID, pos=[3 + i, 4], born=h["tick"])
        p["rooms"][hub.RID] = h["tick"]
    feats.record(h, cfg, "first", pets[4]["id"], "P4 made the first pot", board="FIRST POT IN THE HOUSE: P4")
    feats.record(h, cfg, "first", pets[3]["id"], "P3 made the first cup", board="FIRST CUP IN THE HOUSE: P3")
    h["tick"] += round(cfg["ticks_per_hour"])
    feats.record(h, cfg, "first", pets[2]["id"], "P2 made the first jug", board="FIRST JUG IN THE HOUSE: P2")
    feats.record(h, cfg, "best", pets[1]["id"], "P1 made a finer bowl", board="FINEST BOWL: P1")
    for k in ("rug", "cap", "net", "kite"):
        h["tick"] += 1
        feats.record(h, cfg, "first", pets[0]["id"], "P0 made the first %s" % k, board="FIRST %s IN THE HOUSE: P0" % k.upper())
    seen, turns = [], []
    for _ in range(6):
        L = board.lines(h, cfg)
        up = [x for x in L if x["kind"] != "works"]
        named = [p for x in up for p in x["pets"]]
        assert L[0]["kind"] == "works" and L[0]["meter"] == [0, costs[0]], "the Works' goal and its meter first"
        assert len(up) == D["board_rows"] and len(named) == len(set(named)), "one line to a pet: %s" % [x["text"] for x in up]
        turns.append({house_name(h, p) for p in named})
        seen += named
        h["tick"] += round(cfg["ticks_per_hour"] * D["board_hours"])
    assert set(seen) == {p["id"] for p in pets}, "everyone gets a turn: %s" % turns
    assert "P2" in turns[0] and "P4" not in turns[0], "the young are favoured over the older feats: %s" % turns
    assert all(sum(p in t for t in turns) < len(turns) for p in ("P0", "P1", "P2", "P3", "P4")), "nobody is always up, not the one with most feats, not the young one: %s" % turns

    # ---- pets read it: their own name is pride; someone else's, a nudge ----
    h["board"]["hour"] = None
    up = board.lines(h, cfg)
    mine = next(x for x in up if pets[0]["id"] in x["pets"])
    for p in pets:
        p["events"].clear()
        p.pop("glow", None)
        p.pop("sign", None)
    hub.read_sign(h, cfg, pets[0])
    assert pets[0].get("glow") and pets[0]["glow"]["size"] == 1 and pets[0]["glow"]["why"] == "your name is on the board for the %s" % mine["text"].split(":")[0].lower(), pets[0].get("glow")
    assert any(e.startswith("the board on the wall says") for _, e in pets[0]["events"])
    hub.read_sign(h, cfg, pets[0])
    reader = next(p for p in pets[1:] if not any(p["id"] in x["pets"] for x in up))
    hub.read_sign(h, cfg, reader)
    nudge = [e for _, e in reader["events"] if "on the board for" in e]
    assert not reader.get("glow") and len(nudge) == 1 and nudge[0].endswith("you could do something no one has done"), reader["events"]
    n = len(pets[0]["events"])
    hub.read_sign(h, cfg, pets[0])
    assert len(pets[0]["events"]) == n, "what it has read it does not read again"

    # ---- §10 the visitor's star reaches the maker, asleep or awake; a dead maker's thing can have one too ----
    maker = pets[1]
    cup = thing(eng, hb, "blue cup", "cup", "hard", maker["id"], days=1)
    maker["sleep"] = {"since": h["tick"]}
    maker.pop("glow", None)
    assert board.star(h, cfg, str(cup["made"]["id"])) is None and cup["made"]["star"] == h["tick"]
    assert board.star(h, cfg, str(cup["made"]["id"])) == "it has a star already" and board.star(h, cfg, "nope") == "there is no such thing about the house"
    f = h["feats"]["list"][-1]
    assert f["kind"] == "star" and f["pet"] == maker["id"] and f["board"] == "A STAR FROM THE VISITOR: P1'S BLUE CUP" and h["moments"][-1]["kind"] == "star", f
    hub.tick(h, cfg)
    assert not maker.get("glow"), "asleep, it does not feel it yet"
    maker["sleep"] = None
    hub.tick(h, cfg)
    assert maker["glow"]["size"] == 2 and maker["glow"]["why"] == "the visitor gave your blue cup a star" and not maker.get("starred"), "the maker feels it when it is awake"
    assert any("the visitor gave your blue cup a star" in e for _, e in maker["events"])
    h["board"]["hour"] = None
    assert any(x["kind"] == "star" for x in board.lines(h, cfg)), "the star is on the board"
    assert machine.refuses(h, cfg, maker, hb, "blue cup") == "the machine will not take a thing the visitor gave a star"
    dead = pets[3]
    dead["stage"] = "dead"
    jug = thing(eng, hb, "old jug", "charm", "hard", dead["id"], days=5)
    dead.pop("glow", None)
    assert board.star(h, cfg, str(jug["made"]["id"])) is None and jug["made"]["star"] and not dead.get("starred") and not dead.get("glow"), "a dead maker's thing can have a star"
    # what the Works built is a feat on the board like any other, read like any other
    feats.record(h, cfg, "works", None, "The Works built a lamp for the cellar, fed by P4", board="THE WORKS BUILT A LAMP FOR THE CELLAR: P4", pets=[pets[4]["id"]],
                 **{"for": "feeding the Works for a lamp for the cellar"})
    pets[4].update(glow=None, sign={"day": None, "n": 0})
    hub.read_sign(h, cfg, pets[4])
    assert pets[4]["glow"]["why"] == "your name is on the board for feeding the Works for a lamp for the cellar", pets[4]["glow"]
    eng.close()


def house_name(h, pid):
    return h["pets"][pid]["name"]


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))
    print("works check passed")


if __name__ == "__main__":
    main()
