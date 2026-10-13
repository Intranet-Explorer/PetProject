"""Self-check for SPEC-v3.5 §2 and §3 (bodies that evolve, things the pets invent): stub minds, its own temp folder.

    uv run python -m engine.check_bodies
"""
import asyncio
import json
import random
import tempfile
from pathlib import Path

from . import actions, craft, director, genes, genome, invent, mind, order, physics, sleep, things, wants
from .check import at, do, engine, load_config, scripted
from .genome import PLANS, RANGES, SLOTS, START
from .tick import Engine
from .world import alive, family, new_pet

RECORD = {"name", "a", "parts", "size", "from", "props", "does", "wall", "hangs", "store", "sound", "glow", "by", "tick"}   # the brief's record


def bodies():
    """§2.1, §2.2: every slot inherits and mutates within its bounds; the rates are the spec's."""
    rng, n, big, small, plans = random.Random(35), 6000, 0, 0, 0
    g, anc, moved, kept, seen = dict(START), [], {s: 0 for s in SLOTS}, {s: 0 for s in SLOTS}, {s: set() for s in SLOTS}
    for _ in range(n):
        c, new = genes.child(g, rng, anc)
        assert set(c) == set(START) and c["marks"] == [] and c["plan"] in PLANS and c["pattern"] in genome.PATTERNS, c
        assert all(lo <= c[k] <= hi for k, (lo, hi) in RANGES.items()) and 0 <= c["hue"] < 360, "the numbers keep to their ranges: %s" % c
        for s, values in SLOTS.items():
            assert c[s] in values, "a slot holds one of its own values: %s %s" % (s, c[s])
            step = abs(values.index(c[s]) - values.index(g[s]))
            first = s in genes.PARTS and g[s] == values[0] and c[s] != values[0] and all(a[s] == values[0] for a in anc)
            if new and new["slot"] == s:
                assert new == {"slot": s, "from": g[s], "to": c[s]} and (step >= 2 or first), "the rare thing is two steps away, or a part nobody in the line had: %s" % new
            else:
                assert step <= 1 and not first, "a small step is to a neighbouring value, and never to a part new to the line: %s %s -> %s" % (s, g[s], c[s])
            moved[s], kept[s] = moved[s] + (step > 0), kept[s] + (step == 0)
            seen[s].add(c[s])
        assert not new or new["slot"] != "plan" or (new["from"] == g["plan"] != c["plan"] == new["to"]), new
        assert new or c["plan"] == g["plan"], "a plan changes only as the rare thing"
        big, plans, small = big + bool(new), plans + bool(new and new["slot"] == "plan"), small + any(c[s] != g[s] for s in SLOTS if not new or new["slot"] != s)
        g, anc = c, ([g] + anc)[:40]
    assert all(kept[s] > 10 * moved[s] > 0 for s in SLOTS), "every slot is inherited, and now and then moves: %s %s" % (kept, moved)
    assert all(seen[s] == set(v) for s, v in SLOTS.items()), "every value of every slot can be reached: %s" % seen
    assert 1 / 16 < big / n < 1 / 9, "something new at about 1 birth in 12: 1 in %.1f" % (n / big)
    assert 1 / 60 < plans / n < 1 / 28, "a new body plan at about 1 birth in 40: 1 in %.1f" % (n / plans)
    assert genes.mix("spots", "stripes", rng) == "broken stripes" and genes.mix("gradient", "patch", rng) == "faded patch" and genes.mix("plain", "patch", rng) == "patch" \
        and genes.mix("broken stripes", "patch", rng) in ("spots", "stripes"), "patterns combine by the table, and a combined one comes apart"
    m = genes.measure({1: dict(START, ears="round", tail="stub"), 2: dict(START, head="horns", mouth="wide")}, 80, show=False)
    assert m["births"] == 80 and m["big"] <= 80 / 6 and min(m["apart"]) >= 2, "the stub run of §7.2: %s" % m
    old = {"roundness": 0.3, "stretch": 1.3, "wobble": 0.1, "hue": 200, "saturation": 0.5, "pattern": "speckle", "pattern_density": 0.5, "eye_size": 0.5, "eye_spacing": 0.5, "limbs": 3, "marks": ["a small notch"]}
    assert "pattern of spots" in genome.describe(old) and "no ears or tail" in genome.describe(old), "a body from before v3.5 is still described: %s" % genome.describe(old)
    assert "limbs" not in genes.child(old, rng)[0] and genes.child(old, rng)[0]["pattern"] in genome.PATTERNS, "and its child is a whole body of the new kind"
    told = genome.describe(dict(START, ears="long", tail="fluffy", whiskers="yes", fur="thick", plan="tall"))
    assert all(w in told for w in ("long ears", "a fluffy tail", "whiskers", "thick fur", "a tall, thin body")), "the mirror speaks of the new parts: %s" % told
    assert all(genes.has(g, "curled") != genes.has(g, "stretched") for g in (START, old, dict(START, plan="long"))), "every body has something it does for its pet"


def composing():
    """§3.4: a composition never has more than three parts, never uses a spot the base has not, never stacks two flames."""
    cfg, P = load_config(), invent.P
    assert set(cfg["kinds"]) <= set(P["kinds"]), "every kind in the catalog has a base and a signature part: %s" % (set(cfg["kinds"]) - set(P["kinds"]))
    made = 0
    for a in cfg["kinds"]:
        for b in cfg["kinds"]:
            for emerged in (False, True):
                parts = invent.compose(cfg, {"kind": a, "material": "hard", "color": "grey"}, {"kind": b, "material": "soft", "color": "red"}, emerged)
                if parts is None:
                    continue
                made += 1
                base, tops = parts[0], parts[1:]
                assert 2 <= len(parts) <= P["rules"]["max_parts"] and base["at"] is None and P["thing"][base["part"]]["role"] == "base", (a, b, parts)
                assert all(t["at"] in P["thing"][base["part"]]["spots"] and t["at"] in P["thing"][t["part"]]["on"] for t in tops), "a part sits only on a spot that is there and takes it: %s" % parts
                assert len({t["at"] for t in tops}) == len(tops), "no two parts on one spot: %s" % parts
                assert all(sum(t["part"] == p for t in parts) <= 1 for p in P["rules"]["no_stack"]), "two flames or two blades do not stack: %s" % parts
                assert base["material"] == "hard" and parts[-1]["material"] == "soft" and parts[-1]["part"] == P["kinds"][b]["signature"], "each part is of the thing it came from: %s" % parts
                assert emerged or (len(parts) == 3 or not any(v["base"] == base["part"] and v["signature"] == tops[0]["part"] for v in P["kinds"].values())), "what the catalog already has is not new: %s %s" % (a, b)
    assert made > 500, "most pairs of kinds can be put together: %d" % made
    assert invent.compose(cfg, {"kind": "candle", "material": "bright"}, {"kind": "lamp", "material": "warm"}) is None, "two flames on one stick is a candle, not a new thing"
    assert invent.compose(cfg, {"kind": "nope", "material": "hard"}, {"kind": "lamp", "material": "warm"}) is None


async def traits(d):
    """§2.3: each trait does something in the house, and is felt as a line, and noted."""
    cfg = load_config()
    cfg["life"]["egg_minutes"] = 0.1
    eng, pet = engine(cfg, d + "/traits")
    h = eng.house
    for _ in range(5):
        await eng.tick()
    m, plain = eng.minds[pet["id"]], dict(pet["genome"])
    assert set(START) <= set(plain) and not genome.parts(plain), "a founder is plain"
    assert any(e.startswith("your body is plain and smooth") for _, e in pet["events"]) and pet["body_day"] == h["clock"]["day"], "on the day it hatches it sees its own body: %s" % pet["events"]
    noted = lambda t: [x for x in h.get("fresh_traits", []) if x["trait"] == t] or eng.db.execute("SELECT count(*) FROM traits WHERE pet = ? AND trait = ?", (pet["id"], t)).fetchone()[0]
    # thick fur: the cellar's cold and the season's wear on it less, and it feels its fur do it
    room = h["rooms"][pet["room"]]
    was = room["type"]
    room["type"] = "cellar"
    at(eng, 2)
    h["clock"]["season"] = "winter"
    cold = lambda: {e["tag"]: e["rate"] for e in physics.effects(h, cfg, pet) if e["tag"] in ("cellar", "cold")}
    bare = cold()
    pet["genome"]["fur"] = "thick"
    furred = cold()
    assert bare["cellar"] < 0 and bare["cold"] < 0 and furred["cellar"] == bare["cellar"] * genes.T["fur"]["cold"] and abs(furred["cold"] - bare["cold"] * genes.T["fur"]["cold"]) < 1e-9, "thick fur: %s -> %s" % (bare, furred)
    packet = mind.perceive(h, cfg, pet, m.mem)[0]
    assert genes.T["fur"]["cellar"] in packet and genes.T["fur"]["feel"] in packet and noted("fur"), "and it is felt, in words"
    pet["genome"].update(fur="thin", tail="fluffy", ears="long")
    assert cold() == furred, "a fluffy tail and long ears together are as good as thick fur"
    pet["genome"].update(plain)
    room["type"] = was
    assert not any(e.get("trait") for e in physics.effects(h, cfg, pet)) and not any("fur" in s for s in physics.senses(h, cfg, pet)), "a plain pet has no fur to feel"
    # long ears: what is said next door is heard, word for word; a plain pet hears a voice
    at(eng, 12)
    other = new_pet(h, cfg, room["id"], [3, 3], genome=dict(START), family=1)
    other.update(stage="adult", born=h["tick"], name="Bo", stage_at=dict(other["stage_at"], adult=h["tick"]))
    eng.minds[other["id"]] = type(m)(eng, other)
    door, next_id = next((d_, r) for d_, r in room["doors"].items())
    actions.go(h, cfg, other, door)
    assert other["room"] == next_id and h["rooms"][next_id]["type"], "(the room next door is found by going there)"
    actions.speak(h, cfg, other, {"text": "the pond is the place to sleep"}, eng.minds[other["id"]].mem)
    h["tick"] += 1
    genes.live(h, cfg, pet)
    assert not any("pond is the place" in e for _, e in pet["events"]), "a plain pet does not catch words through a wall"
    pet["genome"]["ears"] = "long"
    pet["body_at"] = h["tick"] - 1
    genes.live(h, cfg, pet)
    assert any("long ears" in e and "the pond is the place to sleep" in e for _, e in pet["events"]) and noted("ears"), "long ears hear speech from the next room: %s" % pet["events"][-2:]
    h.setdefault("radio", {}).setdefault("said", []).append({"tick": h["tick"], "room": next_id, "source": "news", "text": "ships came in at noon"})
    h["tick"] += 1
    genes.live(h, cfg, pet)
    assert pet["box"][0]["text"] == "ships came in at noon" and any("the box" in e and "ships came in" in e for _, e in pet["events"]), "and the box"
    pet["genome"].update(plain)
    # long legs walk faster
    def walked(feet, n=20):
        pet["genome"]["feet"], pet["pos"], pet["walked"], pet["spring"] = feet, [1, 1], 0, 0
        for _ in range(n):
            h["tick"] += 1
            m.walk([1 + 2 * n, 1])
        return pet["walked"]
    slow, fast = walked("nubs"), walked("legs")
    assert fast == slow * 1.5, "long legs cover half as much again: %d against %d" % (fast, slow)
    genes.live(h, cfg, pet)
    assert any(genes.T["legs"]["feel"] in e for _, e in pet["events"]) and noted("legs"), "and it feels its legs carry it"
    pet["genome"].update(plain)
    pet["pos"] = [5, 5]
    # a dark coat: the moth takes no notice of it
    moth = director.born(h, cfg, "moth", room, [5, 6], 10)
    assert not genes.unseen(h, cfg, moth, pet)
    pet["genome"]["shade"] = "dark"
    assert genes.unseen(h, cfg, moth, pet) and any(genes.T["dark"]["feel"] in e for _, e in pet["events"]) and noted("dark"), "the moth ignores a dark coat"
    mouse = director.born(h, cfg, "mouse", room, [5, 6], 10)
    assert not genes.unseen(h, cfg, mouse, pet), "(only the moth)"
    h["creatures"][:] = []
    pet["genome"].update(plain)
    # whiskers: bits and creatures are noticed sooner, so those wants come more often
    assert genes.whiskers(pet, {"what": "bit"}) == 1.0
    pet["genome"]["whiskers"] = "yes"
    assert genes.whiskers(pet, {"what": "bit"}) > 1 and genes.whiskers(pet, {"what": "creature"}) > 1 and genes.whiskers(pet, {"what": "door"}) == 1.0
    pet["wants"] = [{"what": "bit", "key": "bit:moss", "bit": "moss", "since": h["tick"], "text": "x", "done": "y"}]
    h["tick"] += 1
    genes.live(h, cfg, pet)
    assert any("whiskers" in e and "moss" in e for _, e in pet["events"]) and noted("whiskers"), "and it feels its whiskers find it"
    pet["genome"].update(plain)
    pet["wants"] = []
    # small: the corner behind the gap under the storeroom shelves, which only it can reach
    room["type"], room["objects"]["shelves"] = "storeroom", {"pos": [6, 5], "fix": {"store": 6}}
    pet["carrying"] = []
    genes.live(h, cfg, pet)
    assert not pet["carrying"] and not genes.senses(h, cfg, pet, []), "one of an ordinary size does not fit"
    pet["genome"]["size"] = 0.85
    pet["pos"] = [1, 1]
    assert genes.senses(h, cfg, pet, []) == [genes.T["small"]["feel"]], "a small one sees the gap"
    pet["pos"] = [5, 5]
    genes.live(h, cfg, pet)
    assert len(pet["carrying"]) == 1 and any("squeezed through the gap" in e for _, e in pet["events"]) and noted("small"), "and comes back with what lay there"
    genes.live(h, cfg, pet)
    assert len(pet["carrying"]) == 1 and not genes.senses(h, cfg, pet, []), "the corner is bare for a while after"
    del room["objects"]["shelves"]
    room["type"] = was
    pet["genome"].update(plain)
    # every body: once a day, on waking, it sees itself and feels how it slept
    pet["news"], pet["events"], pet["needs"]["comfort"], pet["body_day"] = ["woke"], [], 50.0, None
    genes.live(h, cfg, pet)
    assert pet["events"][0][1].startswith("your body is plain and smooth") and genes.T["curled"]["feel"] in pet["events"][1][1] and pet["needs"]["comfort"] == 50.0 + genes.T["curled"]["comfort"] and noted("curled")
    genes.live(h, cfg, pet)
    assert len(pet["events"]) == 2, "once a day"
    kid = dict(other, id="kid", parent=pet["id"], genome=dict(START, ears="long", tail="fluffy"), events=[], news=["woke"], spring=0)
    pet["genome"].update(ears="long", tail="fluffy")
    h["pets"]["kid"] = kid
    assert genes.own(h, kid) == "you have long ears and a fluffy tail, like your %s" % pet["word"], genes.own(h, kid)
    pet["genome"].update(plain)
    assert genes.own(h, kid) == "you have long ears and a fluffy tail; your %s had no long ears or fluffy tail" % pet["word"], genes.own(h, kid)
    kid["genome"].update(plan="long", roundness=0.3)
    genes.live(h, cfg, kid)
    assert kid["spring"] == genes.T["stretched"]["spring"] and genes.T["stretched"]["feel"] in kid["events"][1][1], "a long body sleeps stretched out, and wakes ready to run"
    del h["pets"]["kid"]
    # birth: the egg's body is its parent's with a slot or two moved; the rare thing is kept on it and is a moment when it hatches
    was_new, genes.R["new"], genes.R["plan"] = genes.R["new"], 1.0, 0.0
    try:
        pet.update(stage="adult", eggs=0)
        pet["needs"].update(energy=95, comfort=80)
        pet["stage_at"]["adult"] = h["tick"]
        r = await do(eng, pet, {"type": "lay_egg", "name": "Sol", "message": "Rest where it is quiet."})
        egg = h["pets"][pet["children"][-1]]
        mut = egg.get("mutation")
        assert not r[0]["reason"] and mut and set(mut) == {"slot", "from", "to"} and egg["genome"][mut["slot"]] == mut["to"] != pet["genome"][mut["slot"]] == mut["from"], "the rare thing is on the egg: %s" % mut
    finally:
        genes.R["new"], genes.R["plan"] = was_new, 0.025
    for _ in range(40):
        await eng.tick()
    assert egg["stage"] == "hatchling" and [x["text"] for x in h["moments"] if x["kind"] == "mutation" and x["pet"] == egg["id"]], "and what hatched is a moment: %s" % h["moments"][-3:]
    # bodies no longer drift in the night: a young one is not asked anything about its body, a grown one only draws itself
    for p in (egg, pet):
        body, mm = json.dumps(p["genome"]), eng.minds[p["id"]]
        p["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
        await sleep.night(mm)
        assert json.dumps(p["genome"]) == body and p["sleep"]["done"] and p["last_night"]["body"] == "", "a night leaves a body as it was"
        p["sleep"] = None
    calls = dict(eng.db.execute("SELECT pet, count(*) FROM calls WHERE kind = 'body' GROUP BY 1"))
    assert calls == {pet["id"]: 1} and pet["portraits"], "one call for the grown pet's picture of itself, none for the hatchling: %s" % calls
    pet["stage"], sat = "adult", pet["genome"]["saturation"]
    pet["stage_at"]["adult"] = h["tick"] - round(cfg["life"]["adult_days"] * cfg["ticks_per_day"]) - 1
    from . import life
    assert life.grow(h, cfg, pet) == "elder" and pet["genome"]["saturation"] < sat, "an elder greys a little"
    eng.close()


async def inventing(d):
    """§3: a new kind is registered, does what both parts did, is made again from its recipe, repeated, lost and found."""
    cfg = load_config()
    cfg["life"]["egg_minutes"] = 0.1
    eng, po = engine(cfg, d + "/invent")
    h = eng.house
    for _ in range(5):
        await eng.tick()
    po.update(stage="adult", name="Po", stage_at=dict(po["stage_at"], adult=h["tick"]))
    m, room = eng.minds[po["id"]], h["rooms"][po["room"]]
    bit = lambda nature: next(b for b, v in sorted(cfg["house"]["bits"].items()) if nature in v["can"] and not v.get("late"))

    def act(a):
        po["needs"]["energy"], h["tick"] = 90.0, h["tick"] + 1
        why = actions.check(a, h, cfg, po, m.mem)
        return (why, None) if why else (None, actions.apply(h, cfg, po, a, m.mem))

    def thing(name, kind, nature, color="yellow"):
        po["carrying"] = [bit(nature)]
        why, got = act({"type": "make", "recipe": {"name": name, "kind": kind, "material": nature, "color": color, "size": "small", "purpose": "a part"}, "near": "here"})
        assert not why, why
    thing("glow", "jar", "bright")
    thing("ring", "bell", "noisy", "blue")
    packet, ctx = mind.perceive(h, cfg, po, m.mem)
    wants.refresh(h, cfg, po)
    assert any(w["what"] == "join" and "glow" in w["text"] and "ring" in w["text"] for w in wants.candidates(h, cfg, po)), "two things that could be joined into something new are a thing to want"
    why, got = act({"type": "combine", "a": "glow", "b": "ring", "recipe": {"name": "ringing light", "material": "noisy", "purpose": "a light to call the others to"}})
    rec, o = h["invented"].get("ringing light"), room["objects"]["ringing light"]
    assert not why and rec and RECORD <= set(rec) and rec["by"] == po["id"] and rec["tick"] == h["tick"] and rec["from"] == ["jar", "bell"], "the house registers the kind: %s %s" % (why, rec)
    assert o["made"]["recipe"]["kind"] == "ringing light" and "ringing light" not in json.loads((Path(__file__).parent.parent / "view" / "assets" / "kinds.json").read_text())
    assert [(p["part"], p["at"], p["material"], p["color"]) for p in rec["parts"]] == [("bowl", None, "bright", "yellow"), ("lid", "top", "bright", "yellow"), ("bell dome", "inside", "noisy", "blue")], rec["parts"]
    assert rec["props"] == ["bright", "noisy", "signalling"] and rec["glow"] and rec["sound"] == "ring" and rec["size"] == "small" and not rec["wall"] and rec["a"] == "a", rec
    p = things.prop(cfg, o)
    assert p["light"] and p["loud"] and p["far"] and o["state"] == "on" and things.light_on(h, cfg, room) and rec["does"] == cfg["craft"]["meets"][frozenset(("bright", "noisy"))]["says"], "what emerged where they met is what it does: %s" % p
    assert [x["text"] for x in h["moments"] if x["kind"] == "invented"] == ["Po invented the ringing light: a light to call the others to"], h["moments"][-3:]
    assert "neither part did" in got[0] and any("new kind of thing" in e for _, e in po["events"][-3:]) and "kind:ringing light" in po["recipes"] and h["recipes"]["kind:ringing light"]["by"] == po["id"], got
    assert craft.words(cfg, "kind:ringing light") == "a ringing light can be made by joining a jar and a bell" and "a ringing light can be made" in mind.perceive(h, cfg, po, m.mem)[0]
    # ... and everywhere a kind is looked up, it is a kind: said, kept, used, joined on, taken apart
    packet = mind.perceive(h, cfg, po, m.mem)[0]
    assert "ringing light (a yellow ringing light; yours" in packet or "ringing light (a blue ringing light; yours" in packet, packet
    assert order.cap(cfg, o) == 0 and not order.can_hang(cfg, o) and order.clutter(h, cfg, room) is not None and "ringing light" in actions.describe_thing(h, cfg, po, "ringing light")
    why, got = act({"type": "use", "target": "ringing light"})
    assert not why and o["state"] == "off", got
    from . import story
    assert any(t["name"] == "ringing light" for t in story.made_by(h, po)) and story.now(h, cfg)
    # made again from its recipe, by one who knows it and carries the stuff of both parts
    po["carrying"] = [bit("bright")]
    assert "ringing light" not in sum(mind.perceive(h, cfg, po, m.mem)[1]["kinds"].values(), []), "not with half of what it is made of"
    po["carrying"] = [bit("bright"), bit("noisy")]
    offered = mind.perceive(h, cfg, po, m.mem)[1]["kinds"]
    assert "ringing light" in offered["bright"] and "ringing light" not in offered["noisy"], "it is offered once, to one who knows how: %s" % offered
    again = {"type": "make", "recipe": {"name": "second light", "kind": "ringing light", "material": "bright", "color": "red", "size": "small", "purpose": "one for the cellar"}, "near": "here"}
    why, got = act(again)
    two = room["objects"]["second light"]
    assert not why and two["made"]["recipe"]["kind"] == "ringing light" and two["made"]["recipe"]["material"] == "signalling" and po["carrying"] == [] and things.prop(cfg, two)["light"] and len(h["invented"]) == 1, "made again from its recipe: %s %s" % (why, got)
    # a joining that only repeats the invention makes that kind, whatever it is called; two of a kind stay that kind
    thing("glow b", "jar", "bright")
    thing("ring b", "bell", "noisy")
    why, got = act({"type": "combine", "a": "ring b", "b": "glow b", "recipe": {"name": "dinner bell", "material": "bright", "purpose": "to say the food is ready"}})
    assert not why and room["objects"]["dinner bell"]["made"]["recipe"]["kind"] == "ringing light" and len(h["invented"]) == 1 and any("like the one Po first made" in e for _, e in po["events"][-3:]), (got, po["events"][-3:], list(h["invented"]))
    thing("soft a", "cushion", "soft")
    thing("soft b", "cushion", "soft")
    why, got = act({"type": "combine", "a": "soft a", "b": "soft b", "recipe": {"name": "big pile", "material": "soft", "purpose": "to fall into"}})
    assert not why and "nothing new came of it" in got[0] and room["objects"]["big pile"]["made"]["recipe"]["kind"] == "cushion" and len(h["invented"]) == 1, got
    # a name that is one of the parts', or a kind already, is no new kind; nor past the day's limit
    for n in list(things.made(room)):
        if n not in ("ringing light", "second light"):
            del room["objects"][n]
    thing("taper", "lamp", "warm")
    thing("ding", "bell", "noisy")
    why, got = act({"type": "combine", "a": "taper", "b": "ding", "recipe": {"name": "bell", "material": "noisy", "purpose": "to ring by the fire"}})
    assert not why and len(h["invented"]) == 1 and "nothing new" in got[0], "a bell is a bell: %s" % (got,)
    thing("taper b", "lamp", "warm")
    thing("ding b", "bell", "noisy")
    cfg["invent"]["per_day"] = 1
    why, got = act({"type": "combine", "a": "taper b", "b": "ding b", "recipe": {"name": "hearth bell", "material": "noisy", "purpose": "to ring by the fire"}})
    assert not why and len(h["invented"]) == 1, "no more new kinds than the day's limit"
    cfg["invent"]["per_day"] = 20
    thing("taper c", "lamp", "warm")
    thing("ding c", "bell", "noisy")
    why, got = act({"type": "combine", "a": "taper c", "b": "ding c", "recipe": {"name": "night bell", "material": "noisy", "purpose": "to ring by the fire"}})
    seat, sp = h["invented"]["night bell"], things.prop(cfg, room["objects"]["night bell"])
    assert not why and len(h["invented"]) == 2 and seat["props"] == ["warm", "noisy"] and seat["sound"] == "ring" and not seat["glow"] and "new kind of thing" in got[0], (seat, got)
    assert [(p["part"], p["at"]) for p in seat["parts"]] == [("stick", None), ("bell dome", "tip")], "no room on a stick for a flame and a bell: the base gives up its own part: %s" % seat["parts"]
    assert sp["loud"] and sp["near"]["night"]["comfort"] > 0 and sp["use"]["curiosity"] > 0 and sp["need"] == "curiosity" and "curiosity when used" in seat["does"], "where nothing emerged it does what both parts did: %s" % sp
    # where two properties meet, what emerged is what it does (v3.4), and it is a new kind
    for n in list(things.made(room)):
        if n not in ("ringing light", "second light"):
            del room["objects"][n]
    thing("glim", "sculpture", "bright")
    po["carrying"] = [next(b for b, v in sorted(cfg["house"]["bits"].items()) if "dark" in v["can"])]
    assert not act({"type": "make", "recipe": {"name": "murk", "kind": "sculpture", "material": "dark", "color": "black", "size": "small", "purpose": "a part"}, "near": "here"})[0]
    why, got = act({"type": "combine", "a": "glim", "b": "murk", "recipe": {"name": "soft glow", "material": "bright", "purpose": "a kind light"}})
    glow = h["invented"]["soft glow"]
    assert not why and "neither part did" in got[0] and glow["props"][-1] == "glowing" and glow["glow"] and things.prop(cfg, room["objects"]["soft glow"]).get("gentle") and len(glow["parts"]) <= 3, glow
    # lost: when nobody living knows the recipe the things stay, and nobody can make more; joined again, it is found again
    kid = dict(po, id="kid", parent=po["id"], recipes={}, carrying=[bit("bright"), bit("noisy")])
    assert "do not know how" in invent.check_make(again, h, cfg, kid) and "ringing light" not in sum(invent.offered(h, cfg, kid, {"bright": ["jar"], "noisy": []}).values(), [])
    assert craft.pass_on(h, cfg, dict(po, recipes={"kind:ringing light": po["recipes"]["kind:ringing light"]}), kid) == "a ringing light can be made by joining a jar and a bell" \
        and "ringing light" in invent.offered(h, cfg, kid, {"bright": [], "noisy": []})["bright"], "it is taught like any other recipe"
    po["recipes"] = {}
    craft.lost(h, cfg)
    assert "lost" in h["recipes"]["kind:ringing light"] and any(x["kind"] == "forgotten" and "ringing light" in x["text"] for x in h["moments"][-12:]), "what nobody living knows is lost"
    po["carrying"] = [bit("bright"), bit("noisy")]
    assert "ringing light" in room["objects"] and things.prop(cfg, room["objects"]["second light"])["loud"], "the things made from it stay, and still do what they did"
    assert "do not know how" in actions.check(again, h, cfg, po, m.mem) and "ringing light" not in sum(mind.perceive(h, cfg, po, m.mem)[1]["kinds"].values(), []), "but nobody can make more"
    thing("glow c", "jar", "bright")
    thing("ring c", "bell", "noisy")
    why, got = act({"type": "combine", "a": "glow c", "b": "ring c", "recipe": {"name": "found light", "material": "noisy", "purpose": "to see and be heard"}})
    assert not why and "lost" not in h["recipes"]["kind:ringing light"] and "kind:ringing light" in po["recipes"] and room["objects"]["found light"]["made"]["recipe"]["kind"] == "ringing light" \
        and any("found again" in x["text"] and "ringing light" in x["text"] for x in h["moments"][-4:]), "until it is found again: %s" % h["moments"][-3:]
    po["carrying"] = [bit("bright"), bit("noisy")]
    assert not actions.check(again, h, cfg, po, m.mem)
    # the house keeps its kinds across a restart, on a config that has never heard of them
    for _ in range(3):
        await eng.tick()
    eng.save()
    eng.close()
    cfg2 = load_config()
    assert "ringing light" not in cfg2["kinds"]
    e2 = Engine(cfg2, d + "/invent", scripted)
    r2 = e2.house["rooms"][po["room"]]
    assert cfg2["kinds"]["ringing light"]["invented"] and things.prop(cfg2, r2["objects"]["second light"])["light"] and order.cap(cfg2, r2["objects"]["second light"]) == 0
    for _ in range(20):
        await e2.tick()
    e2.close()


async def old_house(d):
    """§2.4: a house saved before v3.5 loads, and its living are given their parts once; two families differ in two slots or more."""
    cfg = load_config()
    cfg["life"]["egg_minutes"] = 0.1
    eng, ma = engine(cfg, d + "/old")
    h = eng.house
    for _ in range(5):
        await eng.tick()
    h.setdefault("v31", {}).setdefault("arrived", {})["strangers"] = 0
    assert director.arrive_strangers(h, cfg)
    fo = next(p for p in h["pets"].values() if family(p) == 2)
    assert len(genes.apart_in([ma["genome"]], [fo["genome"]])) >= 2, "a stranger's egg can be told from the family of the house"
    kid = new_pet(h, cfg, ma["room"], [2, 2], genome=dict(ma["genome"]), parent=ma["id"])
    gone = new_pet(h, cfg, ma["room"], [2, 3], genome=dict(ma["genome"]), parent=ma["id"])
    gone.update(stage="dead", died=h["tick"], buried=True, stage_before="adult", cause="old age")
    for i, p in enumerate(h["pets"].values()):   # as they were saved before v3.5: no slots, the old names for patterns, limbs
        p["genome"] = {"roundness": 0.3 + 0.1 * i, "stretch": 1.1, "wobble": 0.2, "hue": 40 * i, "saturation": 0.6, "pattern": ["speckle", "stripe", "patch", "plain"][i % 4],
                       "pattern_density": 0.3, "eye_size": 0.5, "eye_spacing": 0.4, "limbs": i, "marks": ["a small notch"] if i == 0 else []}
    for k in ("v35", "invented"):
        h.pop(k, None)
    eng.save()
    eng.db.execute("DROP TABLE traits")
    eng.close()
    e2 = Engine(load_config(), d + "/old", scripted)
    h2 = e2.house
    living = [p for p in alive(h2)]
    assert "v35" in h2 and len(living) == 3 and all(set(START) <= set(p["genome"]) and p["genome"]["plan"] == "blob" and p["genome"]["size"] == 1.0 for p in living), "everyone living, and each egg, has its slots"
    assert all(p["genome"]["pattern"] in genome.PATTERNS for p in h2["pets"].values()) and "plan" not in h2["pets"][gone["id"]]["genome"], "patterns have their new names; the dead are otherwise left as they were"
    a, b = [[p["genome"] for p in living if family(p) == f] for f in (1, 2)]
    assert len(a) == 2 and len(genes.apart_in(a, b)) >= 2 and a[0]["marks"] == ["a small notch"], "the two families differ in two slots at least: %s" % genes.apart_in(a, b)
    assert all(sum(p["genome"][s] != v[0] for s, v in SLOTS.items()) <= 3 for p in living), "mostly plain: nobody looks much different in the morning"
    assert all(a[0][s] == a[1][s] for s in h2["v35"]["families"]["1"]) and [p["genome"]["feet"] for p in h2["pets"].values() if p["stage"] != "dead"] == ["nubs", "nubs", "paws"], "a family shares its parts; feet come from the limbs it had"
    assert e2.db.execute("SELECT count(*) FROM genomes WHERE cause LIKE 'v3.5%'").fetchone()[0] == len(e2.minds) and e2.db.execute("SELECT count(*) FROM traits").fetchone()[0] == 0
    for _ in range(30):
        await e2.tick()
    was = json.dumps([p["genome"] for p in h2["pets"].values()])
    e2.save()
    e2.close()
    e3 = Engine(load_config(), d + "/old", scripted)
    assert json.dumps([p["genome"] for p in e3.house["pets"].values()]) == was, "once"
    look = Engine(load_config(), d + "/old", scripted, readonly=True)
    assert look.house["v35"] == h2["v35"]
    e3.close()


async def run():
    bodies()
    composing()
    with tempfile.TemporaryDirectory() as d:
        await traits(d)
        await inventing(d)
        await old_house(d)


def main():
    asyncio.run(run())
    print("bodies check passed")


if __name__ == "__main__":
    main()
