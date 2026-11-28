"""Self-check for SPEC-v5.1 §4, §7, §8 (helper C), §10's invention and sprite lines: a stub hob proposes "a tube of
reed with a spring of metal" and is refused in words (reed won't take a metal spring), a memory tagged with the part
and the material and a reaction that shows it the grammar; told, it proposes wood and is accepted; the job runs and the
thing exists with launch, a charge, a first and a known recipe; the second of it is routine; three refusals in a day
make the want fade; the plan packet carries the grammar only when the hob may make, within its size; an invention
queues its sprite call (mocked: PixelLab is not asked) and records the sprite when it lands, the compositor drawing it
meanwhile; the Lab's Grammar section, the header and the cards read it; and with [grammar] off it is v5.0's. Stub houses
only (the view's half is view/check-invent.ts).
    uv run python -m engine.check_invention"""
import asyncio
import os
import stat
import sys
import tempfile
from pathlib import Path

from . import contracts as K
from . import brain4, grammar, invention, items, jobs, lab4, pages
from .brains import model
from .brains.stub import Stub
from .check_brain4 import house

TUBE = {"name": "pebble thrower", "for": "the beetles", "parts": [{"part": "tube", "material": "reed"}, {"part": "spring", "material": "metal"}],
        "charge": "pebble", "how": "a spring behind the tube throws a pebble at what is there"}


def on(cfg, grammar_on=True, sprites=False):
    cfg["v5"]["on"] = True
    for p in K.PARTS5:
        cfg[p]["on"] = True
    cfg["grammar"]["on"], cfg["knowledge"]["on"], cfg["sprites2"]["on"] = grammar_on, True, sprites


def tier1(house_, cfg):
    """A catalog kind of tier 1, for a hob to know (its tier is then 1: it may invent up to 2)."""
    return next(k for k in sorted(cfg["items5"]["kind"]) if grammar.key_tier(house_, cfg, K.key_of(k)) == 1)


async def invents(d):
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    on(cfg)
    pet["knows"] = {K.key_of(tier1(h, cfg)): K.knowledge({"from": "made", "since": h["tick"]})}
    pet["carrying"] = ["reed", "wood", "metal", "pebble"]
    assert grammar.tier(h, cfg, pet) == 1

    # refused in words: a memory with the part and the material, the words counted, a reaction
    words, ok = invention.propose(h, cfg, pet, TUBE)
    said = words
    assert not ok and words.startswith("a reed tube won't take a metal spring: wood"), words
    mem = pet["memories"][-1]
    assert mem["kind"] == "refused" and {"tube", "reed"} <= set(mem["what"]) and words in mem["text"], mem
    c = K.counts(h)
    assert c["invent"] == {"proposed": 1} and c["refused"] == {words: 1}, c
    assert pet["notable"][0]["kind"] == "refused" and words in pet["notable"][0]["text"]

    # the reaction is shown the grammar and what it was told; the stub tries again as the words say; accepted, a job
    e = dict(pet["notable"][0])
    packet, ctx = brain4.react_packet(h, cfg, pet, m.mem, e)
    assert "How things are made" in packet and "tube" in packet and ctx["invent51"] and ctx["refused51"]["words"] == words
    assert "invent" in model.schema4("react", ctx)["properties"]["do"]["anyOf"][0]["properties"]
    assert len(model.prompt4("react", packet, ctx)) <= cfg["brain4"]["packet_chars"], len(model.prompt4("react", packet, ctx))
    pet["last_call"] = -10 ** 6
    m.think("react")
    await m.thought
    m.adopt()
    j = jobs.of(h, pet)
    assert j and j.get("invent") and j["invent"]["parts"][0] == {"part": "tube", "material": "wood"}, j
    kind = j["invent"]["kind"]
    assert kind == "pebble thrower" and pet["inventing"] == kind and K.counts(h)["invent"] == {"proposed": 2, "accepted": 1}
    assert [s["do"] for s in j["steps"]] == ["gather", "gather", "gather", "make"], j["steps"]
    station = j["steps"][-1]["where"]

    # the job runs: the bits in its paws, at the station it is made; the new kind with launch and a charge, a first, known
    for _ in range(3):
        jobs.tick(eng)
    assert jobs.step(j)["do"] == "make" and kind not in h.get("invented", {}), "it is made at its station, not before"
    pet["room"] = station
    jobs.tick(eng)
    rec = h["invented"][kind]
    assert j["state"] == "done" and pet.get("inventing") is None
    assert rec["verbs"].get("launch") and rec["charge"] == "pebble" and rec["by"] == pet["id"] and rec["how"] == TUBE["how"] and rec["for"] == TUBE["for"]
    assert rec["tier"] == 2 and rec["sprite"] is None and rec["draw"][0]["at"] is None and K.recipe(rec)["key"] == K.key_of(kind)
    room = h["rooms"][station]
    name, o = next((n, o) for n, o in room["objects"].items() if (o.get("made") or {}).get("recipe", {}).get("kind") == kind)
    it = items.of(h, cfg, o, name, room)
    assert it["verbs"].get("launch") and it["state"]["charge"] == {"shot": cfg["grammar"]["charge_full"]}, it
    assert o["made"].get("first"), "the first of a kind is a first"
    assert K.knowledge(pet["knows"][K.key_of(kind)])["from"] == "made" and "kind:" + kind in pet["recipes"]
    assert not set(pet["carrying"]) & {"wood", "metal", "pebble"}, "the bits went into it"
    assert cfg["kinds"][kind]["invented"] and cfg["kinds"][kind]["everyday"] == kind
    c = K.counts(h)
    assert c["made_by"] == {"invention": 1} and c["sprites"] == {"composited": 1}, c

    # the second of the same invention is routine: the same kind, made by its recipe
    pet["carrying"] += ["wood", "metal", "pebble"]
    words, ok = invention.propose(h, cfg, pet, dict(TUBE, parts=[{"part": "tube", "material": "wood"}, {"part": "spring", "material": "metal"}], name="other thrower"))
    j2 = jobs.of(h, pet)
    assert ok and j2["invent"]["kind"] == kind and j2["invent"]["again"], words
    for _ in range(4):
        h["tick"] += 1
        jobs.tick(eng)
    assert j2["state"] == "done" and len(h["invented"]) == 1, (j2, pet["room"], pet["carrying"], K.counts(h)["made_by"])
    assert len(h["invented"]) == 1 and K.counts(h)["made_by"] == {"invention": 1, "recipe": 1}

    # the card, the board, the Lab
    v = lab4.recipe_view(h, cfg, kind)
    assert [p["part"] for p in v["parts"]] == ["tube", "spring"] and v["parts"][0]["draw"] and v["materials"] == ["wood", "metal", "pebble"]
    assert v["invented"]["by_id"] == pet["id"] and v["invented"]["how"] == TUBE["how"] and v["knows"] == [pet["name"] or v["knows"][0]] and "it throws things" in v["does"]
    g = lab4.grammar(eng)
    assert g["invent"] == {"proposed": 3, "accepted": 2, "refused": 1} and g["refused"][0]["n"] == 1 and g["made_by"] == {"recipe": 1, "invention": 1}
    assert g["sprites"]["composited"] == 1 and g["pets"][0]["recipes"] == 2 and g["recipes"]["house"] == 2
    h.setdefault("v5", {})["tier"] = {str(h["clock"]["day"] - 1): 1, str(h["clock"]["day"]): 2}
    h["v5"]["tier_fall"] = {"words": "nobody left knows the forge", "tick": h["tick"]}
    assert lab4.header(h, cfg) == {"tier": "the house knows mechanisms", "fall": "nobody left knows the forge"}
    assert [x["tier"] for x in lab4.grammar(eng)["tier"]] == [1, 2]
    from . import knowledge
    card = knowledge.card(h, cfg, pet)   # (B's, which the pet page sends as knows51)
    assert card["tier_words"] == "mechanisms" and K.key_of(kind) in [r["key"] for r in card["recipes"]]
    print("invention: \"%s\"; told, it made the %s of wood: it throws, holds six shots, is a first, and its maker knows how" % (said, kind))
    return eng, pet


async def fades(d):
    """Three refusals of the same invention in a day: the want fades, no grammar again today."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    on(cfg)
    pet["aims"] = [{"text": "make something for the beetles", "why": "", "kind": "make", "target": None, "since": None, "done": False, "made0": 0, "for": "the beetles"}]
    packet, ctx = brain4.plan_packet(h, cfg, pet, m.mem)
    size = len(model.prompt4("plan", packet, ctx))
    assert "How things are made" in packet and ctx["invent51"], "a hob with a make aim is shown the grammar"
    assert "invent" in model.schema4("plan", ctx)["properties"]["aims"]["items"]["properties"]
    assert len(model.prompt4("plan", packet, ctx)) <= cfg["brain4"]["packet_chars"]
    inv = Stub(cfg).invent(ctx)
    assert inv and all(p["part"] in ctx["invent51"]["parts"] for p in inv["parts"]), inv
    for _ in range(3):
        invention.propose(h, cfg, pet, TUBE)
    assert pet["invent_off"] == h["clock"]["day"] and pet["aims"][0]["failed"] and not invention.may(h, cfg, pet)
    assert sum(e["kind"] == "refused" for e in pet["notable"]) == 1, "one reaction (the same within the half hour), and the third given up on"
    packet, ctx = brain4.plan_packet(h, cfg, pet, m.mem)
    assert "How things are made" not in packet and "invent51" not in ctx
    pet["aims"], pet["invent_off"], pet["wants"] = [], None, []
    jobs.board(h)["deficits"] = []
    assert invention.may(h, cfg, pet), "its own make for the day not yet made: the plan may choose a make aim, so the grammar"
    pet["own_made"] = [h["clock"]["day"], cfg["jobs"]["own_make_per_day"]]
    assert not invention.may(h, cfg, pet), "nothing to make for, and its own make made: no grammar"
    print("invention: three refusals in a day and the want fades; the grammar is in the plan only when it may make (%d of %d characters)"
          % (size, cfg["brain4"]["packet_chars"]))


async def sprites(d):
    """§7.2: an invention queues its sprite call (a mock script for PixelLab's); the record says nothing until it lands
    (the compositor draws it meanwhile), then the sprite's folder, which the snapshot sends."""
    eng, pet = await invents(d + "/a")
    h, cfg = eng.house, eng.cfg
    kind = next(iter(h["invented"]))
    own = Path(d) / "own"
    mock = Path(d) / "invent.py"
    mock.write_text("import os, sys\nfrom pathlib import Path\nd = Path(os.environ['PET_MOCK_OWN']) / sys.argv[2]\nd.mkdir(parents=True)\n"
                    "(d / '16.png').write_bytes(b'png')\n(d / '24.png').write_bytes(b'png')\nPath(os.environ['PET_MOCK_OWN'], 'asked').write_text(sys.argv[1])\n")
    mock.chmod(mock.stat().st_mode | stat.S_IEXEC)
    script, owned = invention.SCRIPT, invention.OWN
    invention.SCRIPT, invention.OWN = mock, own
    os.environ["PET_MOCK_OWN"] = str(own)
    try:
        cfg["sprites2"]["on"] = False
        assert invention.sprite(h, cfg, kind) is None, "[sprites2] off: no call, composited"
        cfg["sprites2"]["on"] = True
        t = invention.sprite(h, cfg, kind)
        assert t is not None and h["invented"][kind]["sprite"] is None, "queued: the compositor draws it until it lands"
        t.join(60)
        assert h["invented"][kind]["sprite"] is None, "recorded on the engine's thread"
        invention.tick(h, cfg)
        hsh = invention.recipe_hash(h["invented"][kind])
        assert h["invented"][kind]["sprite"] == "own/invented/%s" % hsh and K.counts(h)["sprites"]["generated"] == 1
        assert "tube of wood" in (own / "asked").read_text() and (own / hsh / "16.png").exists()
        assert lab4.recipe_view(h, cfg, kind)["sprite"] == "own/invented/%s" % hsh
        invention.SCRIPT = Path(d) / "missing.py"
        assert invention.sprite(h, cfg, kind) is None, "no script: no call"
    finally:
        invention.SCRIPT, invention.OWN = script, owned
        os.environ.pop("PET_MOCK_OWN", None)
    print("invention: a sprite call queued and landed (mocked), recorded as %s" % h["invented"][kind]["sprite"])


async def needs(d):
    """§8 the board: a wrong whose make step lacks knowing, or a material, says so ("needs: wax, which nobody has")."""
    from .check_jobs import bare
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    on(cfg)
    cfg["trade"]["on"] = False
    pet["carrying"] = []
    for r in h["rooms"].values():
        if r["type"]:
            r["spots"] = []
            bare(h, cfg, r)
    k = jobs.makeable(h, cfg, ("light",), None)[0]
    assert jobs.lacking(h, cfg, None, k) == "someone who knows how to make %s %s" % (cfg["kinds"][k].get("a", "a"), k), "blocked by knowledge"
    for p in h["pets"].values():
        p["knows"] = {K.key_of(x): K.knowledge({"from": "made"}) for x in jobs.makeable(h, cfg, ("light",), None)}
    first = jobs.lacking(h, cfg, None, k)
    assert first.endswith(", which nobody has"), first
    first = first[:-len(", which nobody has")]
    B = jobs.board(h)
    B["deficits"].append(K.deficit({"kind": "dark", "where": pet["room"], "since": h["tick"], "words": "the room is dark at night"}))
    B["jobs"] = []
    jobs.tick(eng)
    did = B["deficits"][-1]["id"]
    assert not any(j["deficit"] == did for j in B["jobs"]) and jobs.needs(h)[did] == "%s, which nobody has" % first
    assert pages.board_view(h)["deficits"][-1]["needs"] == jobs.needs(h)[did]
    print("invention: the board says what a make step lacks: needs %s" % jobs.needs(h)[did])


async def off(d):
    """[grammar] off is v5.0: no grammar, no invent, no counting; jobs pick by the hand verbs."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    on(cfg, grammar_on=False)
    pet["aims"] = [{"text": "make something", "why": "", "kind": "make", "target": None, "since": None, "done": False, "made0": 0}]
    packet, ctx = brain4.plan_packet(h, cfg, pet, m.mem)
    assert "How things are made" not in packet and "invent51" not in ctx and "invent" not in model.prompt4("plan", packet, ctx)
    assert "invent" not in model.schema4("plan", ctx)["properties"]["aims"]["items"]["properties"]
    assert invention.propose(h, cfg, pet, TUBE) == ("", False) and not any(K.counts(h)[k] for k in K.COUNTS51)
    T = items.T(cfg)["kind"]
    assert jobs.verbs_of(h, cfg, "lantern") == T["lantern"]["verbs"], "the hand verbs"
    assert "needs" not in (h.get("v5") or {}) or not h["v5"]["needs"]
    print("invention: [grammar] off is v5.0's: no grammar shown, nothing invented, the hand verbs")


async def waits(d):
    """the owner's fix (21 October 2026): an accepted invention is never dropped. A gather step that finds nothing blocks it,
    in words on the board ("needs wood; the garden has none"); it goes on when the wood is back; let go, it is set
    aside, blocked, and still on the board."""
    from . import machine
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    on(cfg)
    pet["knows"] = {K.key_of(tier1(h, cfg)): K.knowledge({"from": "made", "since": h["tick"]})}
    pet["carrying"] = ["metal", "pebble"]
    machine.state(h, cfg)["stock"]["wood"] = 0
    strip = lambda: [r.update(spots=[x for x in r["spots"] if x["bit"] != "wood"]) for r in h["rooms"].values() if r["type"]]
    strip()
    room = h["rooms"][pet["room"]]
    room["spots"].append({"bit": "wood", "pos": list(pet["pos"]), "ready": True})
    words, ok = invention.propose(h, cfg, pet, dict(TUBE, parts=[{"part": "tube", "material": "wood"}, {"part": "spring", "material": "metal"}]))
    j = jobs.of(h, pet)
    assert ok and j and jobs.step(j) == {"do": "gather", "what": "wood", "where": room["id"], "verb": None, "done": False}, (words, j and j["steps"])
    strip()
    jobs.tick(eng)
    assert j in jobs.board(h)["jobs"] and j["state"] == "taken" and j["blocked"] == "needs wood; %s has none" % room["name"], j.get("blocked")
    assert jobs.of(h, pet) is None and not pet.get("inventing") and j["deficit"].startswith("invent|")
    row = next(x for x in pages.board_view(h)["jobs"] if x.get("invent"))
    assert row["blocked"] == j["blocked"], row
    room["spots"].append({"bit": "wood", "pos": list(pet["pos"]), "ready": True})
    h["tick"] += 10 - h["tick"] % 10
    jobs.tick(eng)
    assert not j.get("blocked") and pet["inventing"] == j["invent"]["kind"] and jobs.of(h, pet) is j, "the wood is back: it goes on"
    jobs.leave(h, pet, j)   # (as the untouched hour, or a new invention, lets it go)
    assert j in jobs.board(h)["jobs"] and j["blocked"] == "set aside for now" and j["state"] == "taken", "let go, it waits"
    jobs.tick(eng)
    assert not j.get("blocked") and j in jobs.board(h)["jobs"], "and it is taken up again while its inventor is free"
    print("invention: \"%s\" waits on the board, goes on when the wood is back, and is set aside, never dropped" % "needs wood; %s has none" % room["name"])


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(invents(d + "/i"))
        asyncio.run(waits(d + "/w"))
        asyncio.run(fades(d + "/f"))
        asyncio.run(sprites(d + "/s"))
        asyncio.run(needs(d + "/n"))
        asyncio.run(off(d + "/o"))
    print("check_invention: all passed")


if __name__ == "__main__":
    sys.exit(main())
