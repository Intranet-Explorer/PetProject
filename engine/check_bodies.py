"""Self-check for SPEC-v3.5 §2 and §3 (bodies that evolve, things the pets invent): stub minds, its own temp folder.

    uv run python -m engine.check_bodies
"""
import asyncio
import json
import random
import tempfile
from pathlib import Path

from . import actions, craft, director, genes, genome, invent, mind, order, physics, sleep, songs, things, wants
from .check import at, do, engine, load_config, scripted
from .genome import PLANS, RANGES, SLOTS, START
from .tick import Engine
from .world import alive, family, new_pet

RECORD = {"name", "a", "use", "parts", "size", "from", "props", "does", "wall", "hangs", "store", "sound", "glow", "by", "tick"}   # the brief's record


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
    """§3.0, §3.4: any two kinds go together. What fits a use has the use's parts and no others; what fits none is a
    curio with both halves; never more than three parts, never a spot the base has not, never two flames (the art's
    own validator, check_parts.problems, says so of every one)."""
    from .check_parts import problems
    cfg, P, U = load_config(), invent.P, invent.USES
    assert set(cfg["kinds"]) <= set(P["kinds"]), "every kind in the catalog has a base and a signature part: %s" % (set(cfg["kinds"]) - set(P["kinds"]))
    reached, whole = set(), 0
    thing = lambda k, m: {"made": {"recipe": {"kind": k, "material": m, "color": "grey", "size": 1}}}
    for a in cfg["kinds"]:
        for b in cfg["kinds"]:
            got = invent.built(cfg, [thing(a, "hard"), thing(b, "soft")])
            assert got, "any two things can be joined: %s and %s" % (a, b)
            use, ps, x, y = got
            (base, own), given = P["kinds"][x["kind"]], P["kinds"][y["kind"]]["signature"]
            base, own = P["kinds"][x["kind"]]["base"], P["kinds"][x["kind"]]["signature"]
            names = [t["part"] for t in ps[1:]]
            assert not problems(P, ps) and 2 <= len(ps) <= P["rules"]["max_parts"] and ps[0]["part"] == base and ps[0]["material"] == x["material"], "%s + %s: %s %s" % (a, b, ps, problems(P, ps))
            assert all(t["material"] == (y if t["part"] == given and (t["part"] != own or t is ps[-1]) else x)["material"] for t in ps[1:]), "each part is of the thing it came from: %s" % ps
            if use == "curio":
                assert names[-1] == given and names in ([own, given], [given]), "a curio is its base-giver's base and own part, then the other's; the other's is never left off: %s + %s: %s" % (a, b, ps)
                assert len(ps) == 3 or own == given or invent.place(base, [own, given]) is None, "and it has both unless they are one part or there is no room: %s" % ps
                assert not invent.useful(cfg, x, y) and not invent.useful(cfg, y, x), "what fits a use is not a curio"
                whole += len(ps) == 3
            else:
                reached.add(use)
                adds = names[-len(U[use]["add"]):]
                assert base in U[use]["base"] and all(n in options for n, options in zip(adds, U[use]["add"])) and all(n in U[use].get("may", []) for n in names[:-len(adds)]) and given in adds, \
                    "a use has its base and the parts it adds (the other thing's among them), and no others: %s %s" % (use, ps)
    assert reached == set(U), "every use can be reached by joining two things a pet can make: %s" % (set(U) - reached)
    assert whole > 400, "most curios show both halves: %d" % whole
    assert invent.useful(cfg, {"kind": "jar", "material": "hard"}, {"kind": "bowl", "material": "hard"}) is None, "a base's own part alone is no new use: the other thing must give something"
    assert invent.curio(cfg, {"kind": "nope", "material": "hard"}, {"kind": "lamp", "material": "warm"}) is None
    assert invent.place("stick", ["tines", "flame"]) == ["tip", "tip"] and invent.place("stick", ["flame", "blade"]) is None, "a flame stands in a fork; nothing else shares a spot"
    assert all(set(v) >= {"base", "add", "does", "effect"} for v in U.values()), "every use says what it is built of and what it does"


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
    """§3: joining two things in a way the house has not seen makes a kind: a use with its effect if it fits one, a
    curio if not. It is made again from its recipe, repeated, capped by the day, lost and found."""
    cfg, U = load_config(), invent.USES
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

    def thing(name, kind, nature, color="yellow"):   # a made thing, set down beside it (some kinds take stuff a check has no need to find)
        h["n"]["thing"] += 1
        room["objects"][name] = {"pos": [4, 4], "made": {"id": h["n"]["thing"], "recipe": {"name": name, "kind": kind, "material": nature, "color": color, "size": 1, "purpose": "a part"},
                                                         "by": po["id"], "owner": po["id"], "tick": h["tick"], "bits": [b for b, v in sorted(cfg["house"]["bits"].items()) if nature in v["can"]][:1], "uses": 0, "ups": 0, "used_at": h["tick"], "heirloom": None, "behavior": None}}

    def join(a, ka, na, b, kb, nb, name, purpose="to see what comes of it", keep=None):
        thing(a, ka, na)
        thing(b, kb, nb, "blue")
        why, got = act({"type": "combine", "a": a, "b": b, "recipe": {"name": name, "material": keep or nb, "purpose": purpose}})
        assert not why, why
        o = next(o for n, o in room["objects"].items() if n.startswith(name))
        return h["invented"].get(o["made"]["recipe"]["kind"]), o, got

    def clear():
        for n in list(things.made(room)):
            del room["objects"][n]
    # a jar and a bell: a bowl with a bell dome in it is an instrument, whatever it is called
    thing("glow", "jar", "bright")
    thing("ring", "bell", "noisy", "blue")
    wants.refresh(h, cfg, po)
    hint = [w["text"] for w in wants.candidates(h, cfg, po) if w["what"] == "join"]
    assert hint and "glow" in hint[0] and "ring" in hint[0] and "instrument" not in hint[0], "two things that would fit a use are a thing to want, and it is not told what: %s" % hint
    why, got = act({"type": "combine", "a": "glow", "b": "ring", "recipe": {"name": "ringing light", "material": "noisy", "purpose": "a light to call the others to"}})
    rec, o = h["invented"].get("ringing light"), room["objects"]["ringing light"]
    assert not why and rec and RECORD <= set(rec) and rec["by"] == po["id"] and rec["tick"] == h["tick"] and rec["from"] == ["jar", "bell"], "the house registers the kind: %s %s" % (why, rec)
    assert o["made"]["recipe"]["kind"] == "ringing light" and "ringing light" not in json.loads((Path(__file__).parent.parent / "view" / "assets" / "kinds.json").read_text())
    assert rec["use"] == "instrument" and rec["does"] == U["instrument"]["does"], "it fits a use, and that is what it does: %s" % rec
    assert [(p["part"], p["at"], p["material"], p["color"]) for p in rec["parts"]] == [("bowl", None, "bright", "yellow"), ("bell dome", "top", "noisy", "blue")], "its parts are the base and what the use adds, no more: %s" % rec["parts"]
    assert rec["props"] == ["bright", "noisy", "signalling"] and rec["glow"] and rec["sound"] == "ring" and rec["size"] == "small" and not rec["wall"] and rec["a"] == "a", rec
    p = things.prop(cfg, o)
    assert p["light"] and p["loud"] and p["far"] and o["state"] == "on" and things.light_on(h, cfg, room), "what emerged where its materials met still holds (v3.4): %s" % p
    assert [x["text"] for x in h["moments"] if x["kind"] == "invented"] == ["Po invented the ringing light: a light to call the others to"], h["moments"][-3:]
    assert "neither part did" in got[0] and any("new kind of thing (%s)" % U["instrument"]["does"] in e for _, e in po["events"][-3:]) and "kind:ringing light" in po["recipes"] and h["recipes"]["kind:ringing light"]["by"] == po["id"], got
    assert craft.words(cfg, "kind:ringing light") == "a ringing light can be made by joining a jar and a bell" and "a ringing light can be made" in mind.perceive(h, cfg, po, m.mem)[0]
    # ... an instrument plays: a tune its player knows, which whoever hears it picks up like a song sung
    kid = new_pet(h, cfg, room["id"], [5, 5], genome=dict(START), parent=po["id"])
    kid.update(stage="child", born=h["tick"], name="Bo")
    sid = songs.add(h, "the lamp song", [[songs.PITCH[0], 0], [songs.PITCH[2], 1]], po["id"])
    songs.keep(h, cfg, po, sid)
    why, got = act({"type": "use", "target": "ringing light"})
    assert not why and 'you played "the lamp song" on the ringing light' in got[0] and kid["songs"] and any("playing the ringing light" in e for _, e in kid["events"]), "an instrument plays, and is learned from: %s" % (got,)
    # ... and everywhere a kind is looked up, it is a kind: said, kept, joined on, in the story
    packet = mind.perceive(h, cfg, po, m.mem)[0]
    assert "ringing light (a blue harp; yours" in packet, packet
    assert order.cap(cfg, o) == 0 and not order.can_hang(cfg, o) and order.clutter(h, cfg, room) is not None and "ringing light" in actions.describe_thing(h, cfg, po, "ringing light")
    from . import story
    assert any(t["name"] == "ringing light" for t in story.made_by(h, po)) and story.now(h, cfg)
    # made again from its recipe, by one who knows it and carries the stuff of both halves
    po["carrying"] = [bit("bright")]
    assert "ringing light" not in sum(mind.perceive(h, cfg, po, m.mem)[1]["kinds"].values(), []), "not with half of what it is made of"
    po["carrying"] = [bit("bright"), bit("noisy")]
    offered = mind.perceive(h, cfg, po, m.mem)[1]["kinds"]
    assert "ringing light" in offered["bright"] and "ringing light" not in offered["noisy"], "it is offered once, to one who knows how: %s" % offered
    again = {"type": "make", "recipe": {"name": "second light", "kind": "ringing light", "material": "bright", "color": "red", "size": "small", "purpose": "one for the cellar"}, "near": "here"}
    why, got = act(again)
    two = room["objects"]["second light"]
    assert not why and two["made"]["recipe"]["kind"] == "ringing light" and two["made"]["recipe"]["material"] == "signalling" and po["carrying"] == [] and things.prop(cfg, two)["light"] and len(h["invented"]) == 1, "made again from its recipe: %s %s" % (why, got)
    # a joining that only repeats the invention makes that kind, whatever it is called
    rec2, o2, got = join("ring b", "bell", "noisy", "glow b", "jar", "bright", "dinner bell", "to say the food is ready")
    assert o2["made"]["recipe"]["kind"] == "ringing light" and len(h["invented"]) == 1 and any("like the one Po first made" in e for _, e in po["events"][-3:]), got
    # what fits no use is a curio: a new kind all the same, with both halves' parts, its materials' properties, and no effect of its own
    cur, o3, got = join("rag baby", "doll", "soft", "ding", "bell", "noisy", "bell doll", "to ring when hugged")
    assert cur["use"] == "curio" and cur["name"] == "bell doll" and [(p["part"], p["at"], p["material"]) for p in cur["parts"]] == [("bundle", None, "soft"), ("cloth", "side", "soft"), ("bell dome", "tip", "noisy")], cur
    cp = things.prop(cfg, o3)
    assert invent.effect(cfg, o3) == {} and cp["use"] == {"comfort": 4.0, "curiosity": 3.0, "energy": -1.0} and cp["loud"] and cur["sound"] == "ring" and "comfort when used" in cur["does"], "a curio does what its two halves did, and no more: %s" % cp
    assert "nothing new came of it but the thing itself" in got[0] and any(x["text"] == "Po invented the bell doll: to ring when hugged" for x in h["moments"][-6:]) and "kind:bell doll" in po["recipes"], got
    assert invent.used(h, cfg, po, room, "bell doll") is None
    thing("rag baby b", "doll", "hard")
    thing("ding x", "bell", "hard")
    assert not any(w["what"] == "join" and "rag baby b" in w["text"] for w in wants.candidates(h, cfg, po)), "two things that would only make a curio are nothing to want: that is its mind's to think of"
    same, o4, got = join("soft a", "cushion", "soft", "soft b", "cushion", "soft", "big pile", "to fall into")
    assert same["use"] == "curio" and o4["made"]["recipe"]["kind"] == "big pile" and [q["part"] for q in same["parts"]] == ["cushion", "pad"] and len(h["invented"]) == 3, "two of a kind joined are a new kind too: %s" % same
    # a name that is a kind's already is told apart; past the day's limit a joining makes the larger kind, as before
    clear()
    taken, o5, got = join("taper", "lamp", "warm", "ding b", "bell", "noisy", "bell", "to ring by the fire")
    assert taken["name"] == "bell two" and o5["made"]["recipe"]["kind"] == "bell two" and cfg["kinds"]["bell"].get("invented") is None, taken
    cfg["invent"]["per_day"] = len(h["invented"])
    none, o6, got = join("taper b", "lamp", "warm", "ding c", "bell", "hard", "hearth bell", "to ring by the fire")
    assert none is None and o6["made"]["recipe"]["kind"] == "lamp" and "nothing new came of it" in got[0], "no more new kinds than the day's limit: %s" % o6["made"]["recipe"]
    cfg["invent"]["per_day"] = 20
    # each use does what it is for, by a rule the house already had
    clear()
    lit, o, got = join("pipe", "flute", "hard", "wick", "lamp", "warm", "night stick", "a light to carry", keep="hard")
    assert lit["use"] == "carried light" and [q["part"] for q in lit["parts"]] == ["stick", "flame"] and things.prop(cfg, o)["light"] and lit["glow"] and o["state"] == "on" and U["carried light"]["does"] in got[0], (lit, got)
    door = next(iter(room["doors"]))
    actions.go(h, cfg, po, door)
    there = h["rooms"][po["room"]]
    invent.tick(h, cfg)
    assert "night stick" in there["objects"] and "night stick" not in room["objects"] and things.light_on(h, cfg, there) and any("night stick came in with you" in e for _, e in po["events"]), "a carried light goes where its carrier goes"
    cart, oc, got = None, None, None
    po.update(room=room["id"], pos=[5, 5])
    invent.tick(h, cfg)
    assert "night stick" in room["objects"], "and back"
    cart, oc, got = join("crate a", "crate", "hard", "spinner", "spinning top", "bouncy", "wagon", keep="hard")
    thing("load", "cushion", "soft")
    room["objects"]["load"]["on"] = "wagon"
    assert cart["use"] == "cart" and order.cap(cfg, oc) >= 4 and order.held(room, "wagon") == ["load"], cart
    po.update(room=there["id"])
    invent.tick(h, cfg)
    assert "wagon" in there["objects"] and there["objects"]["load"]["on"] == "wagon" and there["objects"]["load"]["pos"] == there["objects"]["wagon"]["pos"], "a cart goes with its owner, and what is on it with it"
    po.update(room=room["id"], pos=[5, 5])
    invent.tick(h, cfg)
    clear()
    soft, o, got = join("looking glass", "mirror", "glassy", "mat", "rug", "soft", "moon glass", keep="glassy")
    only = {"objects": {"moon glass": o}}
    assert soft["use"] == "soft light" and soft["glow"] and [q["part"] for q in soft["parts"]] == ["frame", "gem", "cloth"] and soft["wall"] and o.get("wall") and things.light_on(h, cfg, only) and not things.light_on(h, cfg, only, harsh=True) and wants.gentle(cfg, only), "a soft light lights a room at night without harshness: %s" % soft
    clear()
    cut, o, got = join("pipe b", "flute", "hard", "edge", "carver", "hard", "whittler")
    assert cut["use"] == "cutter" and craft.tool_here(h, cfg, room, "carver") == "whittler" and craft.lasts(cfg, o) > 0 and "carver" in h["firsts"] and craft.tool_here(h, cfg, room, "trowel") is None, "a cutter counts as a carver"
    po["carrying"] = ["wood"]
    assert not actions.check({"type": "process", "what": "wood", "how": "carve"}, h, cfg, po, m.mem) or "bench" in actions.check({"type": "process", "what": "wood", "how": "carve"}, h, cfg, po, m.mem)
    po["carrying"] = []
    clear()
    pour, o, got = join("dish", "bowl", "hard", "mug", "cup", "hard", "rain bringer")
    room["objects"]["herb patch"] = {"pos": [8, 6], "fix": {"plant": True}, "grow": 0.0, "state": "growing", "planted": {"what": "seed", "at": 0, "grow": 0.3, "watered": 0, "by": po["id"], "stage": "sprout"}}
    why, got = act({"type": "use", "target": "rain bringer"})
    assert pour["use"] == "pourer" and not why and "carried water" in got[0] and room["objects"]["herb patch"]["planted"]["watered"] == h["tick"], "a pourer carries water to what is planted: %s" % (got,)
    del room["objects"]["herb patch"]
    clear()
    keep, o, got = join("dish b", "bowl", "hard", "pot", "jar", "hard", "larder")
    assert keep["use"] == "keeper" and keep["store"] == 3 and order.cap(cfg, o) == 3 and order.inside(cfg, o) and "larder" in order.stores(cfg, room), "a keeper keeps things, put away inside it: %s" % keep
    plant, o, got = join("dish c", "bowl", "hard", "posy", "vase", "cool", "sill garden", keep="hard")
    assert plant["use"] == "planter" and craft.plantable(cfg, "sill garden", o) and not craft.plantable(cfg, "larder", room["objects"]["larder"]), "a planter can be planted in"
    clear()
    reach, o, got = join("pipe c", "flute", "hard", "peg", "wall hook", "hard", "long arm")
    was, room["type"], po["carrying"] = room["type"], "attic", []
    why, got = act({"type": "use", "target": "long arm"})
    assert reach["use"] == "reacher" and not why and "high shelf" in got[0] and len(po["carrying"]) == 1 and invent.used(h, cfg, po, room, "long arm") is None, "a reacher brings down what is on the attic's high shelf, now and then: %s" % (got,)
    room["type"] = "pond"
    boat, o, got = join("puck", "ball", "bouncy", "throw", "blanket", "soft", "leaf boat", keep="bouncy")
    room["objects"]["pond"] = {"pos": [1, 6], "fix": {"water": [[1, 6]]}}
    o["pos"] = [1, 6]
    things.upkeep(h, cfg)
    why, got = act({"type": "use", "target": "leaf boat"})
    assert boat["use"] == "boat" and "leaf boat" in room["objects"] and not why and "on the water" in got[0] and got[1]["curiosity"] > 0, "a boat floats on the pond, and is a toy: %s" % (got,)
    del room["objects"]["pond"]
    room["type"] = was
    clear()
    roll, o, got = join("puck b", "ball", "bouncy", "ding d", "bell", "hard", "chase me", keep="bouncy")
    kid["events"], kid["sleep"] = [], None
    why, got = act({"type": "use", "target": "chase me"})
    assert roll["use"] == "rolling toy" and not why and "rang as it went" in got[0] and any("you want to go after it" in e for _, e in kid["events"]) and po["played_with"][kid["id"]] == h["tick"], "a rolling toy rings and draws kin to play: %s" % (got,)
    token, o, got = join("ding e", "bell", "hard", "figure", "sculpture", "hard", "ma's ring")
    assert token["use"] == "keepsake" and [q["part"] for q in token["parts"]] == ["ring", "gem"] and invent.effect(cfg, o) == {} and invent.used(h, cfg, po, room, "ma's ring") is None, "a keepsake has no use but meaning: %s" % token
    # the uses whose parts no catalog kind gives yet do their work as soon as a kind is of them
    clear()
    def of(use, name, room_=None):
        h["invented"][name] = {"name": name, "a": "a", "use": use, "parts": [{"part": U[use]["base"][0], "at": None, "material": "hard", "color": "grey"}], "size": "small", "from": ["sculpture", "sculpture"],
                               "props": ["hard"], "material": "hard", "wall": False, "hangs": False, "store": 0, "by": po["id"], "tick": 0, "key": "check/" + use, "does": U[use]["does"], "sound": None, "glow": False}
        invent.install(h, cfg)
        thing(name, name, "hard")
        return room["objects"][name]
    assert craft.tool_here(h, cfg, room, "trowel") is None
    of("digger", "mole paw")
    assert craft.tool_here(h, cfg, room, "trowel") == "mole paw", "a digger counts as a trowel"
    assert things.prop(cfg, of("seat or bed", "deep chair"))["rest_bonus"] >= 2.0 and "deep chair" in things.near(h, cfg, dict(po, pos=[4, 4]), "rest_bonus"), "a seat or bed gives better rest"
    chime, room["type"], h["weather"] = of("chime", "wind teller"), "garden", "storm"
    h["tick"] = round(round(h["tick"] / cfg["ticks_per_hour"] + 1) * cfg["ticks_per_hour"])
    po["events"] = []
    while h["tick"] % max(1, round(cfg["ticks_per_hour"])):
        h["tick"] += 1
    invent.tick(h, cfg)
    assert room["sounding_until"] > h["tick"] and any("wind teller" in e and "tomorrow" in e for _, e in po["events"]), "a chime sounds in the wind, and in the garden tells the weather: %s" % po["events"]
    room["type"], h["weather"] = was, "clear"
    of("feeder", "seed dish")
    h.setdefault("v31", {}).setdefault("arrived", {})["taming"] = 0
    mouse = director.born(h, cfg, "mouse", room, [5, 6], 1)
    until = mouse["until"]
    invent.tick(h, cfg)
    assert mouse["until"] > until and mouse["trust"].get(po["id"], 0) > 0, "creatures stay by a feeder and come to trust whoever set it out"
    h["creatures"][:] = []
    for n in ("mole paw", "deep chair", "wind teller", "seed dish"):
        del h["invented"][n], cfg["kinds"][n], room["objects"][n]
    # lost: when nobody living knows the recipe the things stay, and nobody can make more; joined again, it is found again
    thing("ringing light", "ringing light", "signalling")
    thing("second light", "ringing light", "signalling")
    learner = dict(po, id="learner", parent=po["id"], recipes={}, carrying=[bit("bright"), bit("noisy")])
    assert "do not know how" in invent.check_make(again, h, cfg, learner) and "ringing light" not in sum(invent.offered(h, cfg, learner, {"bright": ["jar"], "noisy": []}).values(), [])
    assert craft.pass_on(h, cfg, dict(po, recipes={"kind:ringing light": po["recipes"]["kind:ringing light"]}), learner) == "a ringing light can be made by joining a jar and a bell" \
        and "ringing light" in invent.offered(h, cfg, learner, {"bright": [], "noisy": []})["bright"], "it is taught like any other recipe"
    po["recipes"] = {}
    craft.lost(h, cfg)
    assert "lost" in h["recipes"]["kind:ringing light"] and any(x["kind"] == "forgotten" and "ringing light" in x["text"] for x in h["moments"][-40:]), "what nobody living knows is lost"
    po["carrying"] = [bit("bright"), bit("noisy")]
    assert "ringing light" in room["objects"] and things.prop(cfg, room["objects"]["second light"])["loud"], "the things made from it stay, and still do what they did"
    assert "do not know how" in actions.check(again, h, cfg, po, m.mem) and "ringing light" not in sum(mind.perceive(h, cfg, po, m.mem)[1]["kinds"].values(), []), "but nobody can make more"
    n = len(h["invented"])
    found, o, got = join("glow c", "jar", "bright", "ring c", "bell", "noisy", "found light", "to see and be heard")
    assert len(h["invented"]) == n and "lost" not in h["recipes"]["kind:ringing light"] and "kind:ringing light" in po["recipes"] and o["made"]["recipe"]["kind"] == "ringing light" \
        and any("found again" in x["text"] and "ringing light" in x["text"] for x in h["moments"][-4:]), "until it is found again: %s" % h["moments"][-3:]
    po["carrying"] = [bit("bright"), bit("noisy")]
    assert not actions.check(again, h, cfg, po, m.mem)
    # the house keeps its kinds across a restart, on a config that has never heard of them
    del h["pets"][kid["id"]]
    po["children"].remove(kid["id"])
    for _ in range(3):
        await eng.tick()
    eng.save()
    eng.close()
    cfg2 = load_config()
    assert "ringing light" not in cfg2["kinds"]
    e2 = Engine(cfg2, d + "/invent", scripted)
    r2 = e2.house["rooms"][room["id"]]
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
