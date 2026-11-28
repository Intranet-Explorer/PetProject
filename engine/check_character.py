"""Self-check for SPEC-v4.0 §13.1, helper A's part: each pole's behaviours are in the data and fire for a hob at that
pole, not the other; moods come, fade and swing with `sensitive`; hunger, safety and pride move as §2 says, and
starving can kill; opinions move only from recorded causes, clamped, and light ones fade; gossip is weighted by trust,
a sly teller may invent, and a lie found out costs trust; memories fade but heavy ones don't; bonds form and break,
and two-parent eggs take genes from both; the migration gives every living hob traits, opinions and memories, once and
silently. And each switch off brings back v3.6c's behaviour for its part.
    uv run python -m engine.check_character [a copy of a data directory, to migrate and report on]"""
import asyncio
import random
import sys
import tempfile

from . import actions, bonds, character, conflict, life, memories, migrate4, needs, opinions, talk, world
from .check import at, engine, load_config
from .world import GENES, new_pet


def v4(on=True):
    cfg = load_config()
    for part in ("traits", "needs4", "opinions"):
        cfg[part]["on"] = on
    cfg["weather"]["real"] = False
    return cfg


def hob(eng, room=None, stage="adult", **temper):
    h = eng.house
    p = new_pet(h, eng.cfg, room or next(iter(h["pets"].values()))["room"], [2 + len(h["pets"]) % 8, 3], family=1)
    p.update(stage=stage, born=h["tick"] - eng.cfg["ticks_per_day"], laid=h["tick"] - eng.cfg["ticks_per_day"] - 10)
    p["stage_at"].update({s: p["born"] for s in ("hatchling", "child", "youngling", "adult", "elder")})
    p["temper"].update({character.GENE.get(a, a): (v + 1) / 2 for a, v in temper.items()})
    from .tick import Mind
    eng.minds[p["id"]] = Mind(eng, p)
    return p


def old_temper_of(parent, rng, cfg):
    """v3.6c's temper_of, to prove the draws of the nine old genes stay as they were."""
    old = GENES[:9]
    t = {g: round(min(1.0, max(0.0, parent.get(g, 0.5) + rng.gauss(0, cfg["life"]["temper_sigma"]))), 2) for g in old}
    if rng.random() < cfg["life"]["temper_jump"]:
        g = rng.choice(old)
        t[g] = round(min(1.0, max(0.0, t[g] + rng.choice([-1, 1]) * rng.uniform(0.2, 0.35))), 2)
    return t


async def run(d):
    # ---- §1 the data: ten axes, each pole's behaviours, moods, values, quirks ----
    D = character.DATA
    assert set(D["axes"]) == set(character.AXES) and GENES[-4:] == ("generous", "honest", "ambitious", "kind")
    for a, x in D["axes"].items():
        assert len(x["words"]) == 2 and len(x["plus"]) >= 3 and len(x["minus"]) >= 3, "each pole of %s has its behaviours" % a
    assert set(D["moods"]) == set(character.MOODS) and len(D["values"]) == 9 and len(D["quirks"]) >= 55
    for spec in list(D["values"].values()) + list(D["quirks"].values()):
        assert all(s[:-1] in character.AXES and s[-1] in "+-" for s in spec), spec
    plus, minus = {"temper": {}}, {"temper": {}}
    for a in character.AXES:
        plus["temper"][character.GENE.get(a, a)], minus["temper"][character.GENE.get(a, a)] = 0.95, 0.05
    for b, (a, sign) in character.BEHAVIOURS.items():
        at_pole, other = (plus, minus) if sign > 0 else (minus, plus)
        assert character.does(at_pole, b) > 0.8 and character.does(other, b) == 0, "%s fires at its pole only" % b
        assert character.does({"temper": {}}, b) == 0, "and not in the middle"
    assert character.words(plus).startswith("very brave") and "timid" in character.words(minus) and "greedy" in character.words(minus)

    cfg = v4()
    eng, first = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    at(eng, 10)
    first.update(stage="adult", name="Oya")
    first["stage_at"]["adult"] = h["tick"]

    # ---- temper: the old genes draw as v3.6c did; the jump keeps surprises; two parents give from both ----
    cfg_off = v4(False)
    for seed in range(40):
        a, b = life.temper_of(first["temper"], random.Random(seed), cfg_off), old_temper_of(first["temper"], random.Random(seed), cfg_off)
        assert {g: a[g] for g in GENES[:9]} == b, "with the traits off, the nine old genes are drawn exactly as before"
        assert set(a) == set(GENES)
    lo, hi = {g: 0.05 for g in GENES}, {g: 0.95 for g in GENES}
    kids = [life.temper_of(lo, random.Random(s), cfg, hi) for s in range(20)]
    assert all(any(k[g] < 0.4 for k in kids) and any(k[g] > 0.6 for k in kids) for g in GENES), "a child's temper takes from both parents"
    jumped = sum(any(abs(k[g] - (0.05 if k[g] < 0.5 else 0.95)) > 0.18 for g in GENES) for k in kids)
    assert jumped, "temper_jump still moves a gene a long way now and then"

    # ---- §1.2-1.3 quirks, values, moods ----
    a = hob(eng, sensitive=1.0, kind=0.9, social=0.8)
    a["temper"]["sensitive"] = 1.0
    b = hob(eng, kind=-0.9, generous=-0.9)
    b["temper"]["sensitive"] = 0.0
    await eng.tick()
    for p in (a, b):
        assert 1 <= len(p["quirks"]) <= 2 and len(p["values"]) == 2 and len(set(p["values"])) == 2 and p["mood"]["mood"]
    assert character.set_mood(h, cfg, a, "angry", "Brask broke my cup") and character.set_mood(h, cfg, b, "angry", "Brask broke my cup")
    assert a["mood"]["until"] - a["mood"]["since"] > b["mood"]["until"] - b["mood"]["since"], "a sensitive hob's mood lasts longer"
    assert character.mood_weight(a, "ladder") > character.mood_weight(b, "ladder") > 1, "and swings harder; angry climbs the ladder"
    assert not character.set_mood(h, cfg, a, "content", "nothing much"), "a weaker mood does not push a stronger one aside"
    q = character.hours(cfg, 0.25)
    h["tick"] = a["mood"]["until"] + (q - a["mood"]["until"] % q) % q
    character.tick(h, cfg)
    assert a["mood"]["mood"] != "angry" and a["mood"]["why"] != "Brask broke my cup", "moods fade"
    assert character.mood_weight(b, "nothing") == 1.0

    # ---- §2 needs: hunger from food, energy from sleep and rest; safety; pride; starving ----
    assert {"hunger", "safety", "pride"} <= set(a["needs"]) and needs.feel(a) and all(isinstance(f, str) for f in needs.feel(a))
    room = h["rooms"][a["room"]]
    bowl = next(n for n, o in room["objects"].items() if "meal" in o.get("fix", {}))
    room["objects"][bowl]["servings"] = 3
    a["needs"].update(hunger=30.0, energy=40.0)
    a["last_eat"] = world.LONG_AGO
    text, fx, _ = actions.use(h, cfg, a, bowl)
    assert a["needs"]["hunger"] == 30.0 + cfg["effects"]["eat"]["energy"] * cfg["needs4"]["food"] and "energy" not in fx, "food fills hunger, not energy"
    assert needs.appetite(cfg, a) == "hunger"
    attic = world.generate_room(h, cfg, next(r for r, x in sorted(h["rooms"].items()) if not x["type"]), "attic")
    alone = hob(eng, room=attic["id"])
    with_others = needs.safe_target(h, cfg, a)
    assert with_others > needs.safe_target(h, cfg, alone), "others nearby make a hob feel safer"
    h["weather"] = "storm"
    assert needs.safe_target(h, cfg, alone) < with_others - 20, "a storm alone frightens"
    h["weather"] = "clear"
    pride = a["needs"]["pride"]
    world.moment(h, "best", "%s made the best cup the house has seen" % world.label(a), a["id"], a["room"])
    needs.tick(h, cfg)
    assert a["needs"]["pride"] > pride, "a best makes a hob proud"
    opinions.move(h, cfg, a, b["id"], "praised_me", "Brask praised my cup")
    assert a["needs"]["pride"] > pride + 9, "praise too"
    alone["needs"]["hunger"] = 0.0
    needs.tick(h, cfg)
    assert alone["starving"] == h["tick"] and alone["weak"] and life.due(h, cfg, alone) is None
    alone["starving"] = h["tick"] - round((cfg["needs4"]["starve_days"] + 1) * cfg["ticks_per_day"])
    assert life.due(h, cfg, alone) == "starvation", "starving long enough kills"
    alone["needs"]["hunger"] = 60.0
    needs.tick(h, cfg)
    assert alone["starving"] is None

    # ---- §4 opinions: only from recorded causes, clamped, light ones fade, heavy ones stay ----
    for p in (a, b):
        p.pop("opinions", None)
    try:
        opinions.move(h, cfg, a, b["id"], "because i said so", "nothing")
        raise AssertionError("an opinion moves only by a cause in opinions.toml")
    except KeyError:
        pass
    opinions.move(h, cfg, a, b["id"], "gift", "Brask gave me a cup")
    opinions.move(h, cfg, a, b["id"], "took_my_thing", "Brask took my rope")
    opinions.move(h, cfg, a, b["id"], "insult", "Brask laughed at my song", d={"liking": -50, "respect": -50})
    o = opinions.of(a, b["id"])
    assert o["liking"] == 2 - 4 - 3 and o["respect"] == 4 and o["trust"] == 5 + 1 - 3, "the amounts in data; a caller's are clamped to them: %s" % o
    for x in opinions.AXES:
        assert abs(o[x] - opinions.NEUTRAL[x] - sum(c["d"].get(x, 0) for c in o["causes"])) < 1e-6, "every change is in its causes"
    assert [c["cause"] for c in o["causes"]] == ["gift", "took_my_thing", "insult"] and all(c["why"] and c["tick"] is not None for c in o["causes"])
    assert any("Brask took my rope" == m["text"] and m["weight"] == 4 for m in a["memories"]), "a cause leaves its memory"
    for _ in range(40):
        opinions.fade(h, cfg, a, 0.2)
    o = opinions.of(a, b["id"])
    assert abs(o["liking"] - (-4)) < 0.05 and abs(o["trust"] - (5 - 3)) < 0.05, "light feelings fade; the theft (a heavy memory) does not: %s" % o
    for _ in range(50):
        opinions.move(h, cfg, a, b["id"], "beat_me", "Brask beat me")
    o = opinions.of(a, b["id"])
    assert o["liking"] == -10 and o["fear"] == 10 and len(o["causes"]) == 20, "clamped, and the last 20 causes kept"
    # the engine's own sites: a gift taken, a nuzzle ignored, eating from one pot
    c = hob(eng)
    c["carrying"] = ["feather"]
    actions.offer(h, cfg, c, a, {"kind": "give", "what": "feather", "bit": True})
    actions.accept(h, cfg, a, a["offers"][-1])
    assert opinions.of(a, c["id"])["causes"][-1]["cause"] == "gift" and opinions.of(c, a["id"])["causes"][-1]["cause"] == "gift_taken"
    actions.offer(h, cfg, c, b, {"kind": "nuzzle"})
    b["offers"][-1]["tick"] -= 10**6
    actions.lapse(h, cfg, b)
    assert opinions.of(c, b["id"])["causes"][-1]["cause"] == "ignored_me", "a nuzzle ignored is felt"

    # ---- gossip: weighted by trust; a sly teller may invent; a lie found out costs trust ----
    t1, t2, about, ear = hob(eng, honest=0.9), hob(eng, honest=-1.0), hob(eng), hob(eng)
    opinions.move(h, cfg, ear, t1["id"], "kept_promise", "t1 kept its word")
    opinions.move(h, cfg, ear, t2["id"], "lied_to_me", "t2 lied")
    moved1 = opinions.gossip(h, cfg, t1, ear, about["id"], -8)["liking"]
    ear["opinions"][about["id"]].update(liking=0.0)
    moved2 = opinions.gossip(h, cfg, t2, ear, about["id"], -8)["liking"]
    assert moved1 < moved2 < 0, "gossip moves a listener more the more it trusts the teller (%s, %s)" % (moved1, moved2)
    said = []
    for i in range(60):
        h["tick"] += 1
        said.append(opinions.say(h, cfg, t2, about["id"]))
    assert any(not true for _, true in said) and all(true for _, true in (opinions.say(h, cfg, t1, about["id"]) for _ in range(30))), "only the sly invent"
    opinions.gossip(h, cfg, t2, ear, about["id"], -7, true=False)
    trust = opinions.of(ear, t2["id"])["trust"]
    opinions.found_out(h, cfg, h["lies"][-1])
    assert opinions.of(ear, t2["id"])["trust"] < trust and opinions.of(ear, t2["id"])["causes"][-1]["cause"] == "lied_to_me"
    # first impressions: kin start warm, a stranger as the family sees it
    kid = hob(eng, stage="child")
    kid["parent"] = a["id"]
    a["children"].append(kid["id"])
    opinions.entry(h, cfg, kid, a["id"])
    assert opinions.of(kid, a["id"])["liking"] >= 4 and opinions.of(kid, a["id"])["causes"][0]["cause"] == "kin", "kin start warm"
    opinions.entry(h, cfg, kid, b["id"])
    assert opinions.of(kid, b["id"])["liking"] < 0 and opinions.of(kid, b["id"])["causes"][0]["cause"] == "family_says", "a first impression from family"

    # ---- §3 memories and skills ----
    m0 = len(kid.get("memories", []))
    memories.add(h, cfg, kid, "my mother died", 5, [a["id"]], "death")
    for i in range(70):
        memories.add(h, cfg, kid, "a small thing %d" % i, 1)
    assert len(kid["memories"]) == 50 and any(m["text"] == "my mother died" for m in kid["memories"]), "50 kept, the lightest go first"
    assert memories.relevant(h, cfg, kid, [a["id"]], 3)[-1]["text"] == "my mother died" or any(m["text"] == "my mother died" for m in memories.relevant(h, cfg, kid, [a["id"]], 3))
    h["tick"] += 10 * cfg["ticks_per_day"]
    memories.trim(h, cfg, kid)
    assert [m["text"] for m in kid["memories"]] == ["my mother died"], "light memories fade over days; heavy ones never"
    # (19 October 2026) at most 20 of the 50 weigh 4 or 5; weight 4 fades a point in 10 days, 5 never
    kid["memories"] = []
    for i in range(60):
        memories.add(h, cfg, kid, "a thing %d" % i, i % 5 + 1)
    ws = [m["weight"] for m in kid["memories"]]
    assert len(ws) == 50 and sum(w >= 4 for w in ws) == 20 and ws.count(5) == 12, "50 kept, 20 heavy, the heaviest first: %s" % ws
    h["tick"] += 20 * cfg["ticks_per_day"]
    memories.trim(h, cfg, kid)
    assert [m["weight"] for m in kid["memories"]].count(4) == 8, "a weight-4 memory is still there after 20 days"
    h["tick"] += 20 * cfg["ticks_per_day"]
    memories.trim(h, cfg, kid)
    assert [m["weight"] for m in kid["memories"]] == [5] * 12, "and gone after 40; weight 5 stays"
    a["skill"] = {"making": 138.6, "fishing": 12.2, "tending": 8.5}
    s = memories.skills(a)
    assert set(s) == set(memories.SKILLS) and 8 < s["crafting"] <= 10 and 2 < s["fishing"] < 4 and s["healing"] == 0, s
    memories.practise(h, cfg, a, "healing", 30)
    assert memories.skill(a, "healing") == 5.0

    # ---- §6.3 bonds: derived kinds; close bonds form and break; two-parent eggs ----
    x, y = hob(eng), hob(eng)
    for _ in range(4):
        opinions.move(h, cfg, x, y["id"], "nursed_me", "y nursed me"), opinions.move(h, cfg, y, x["id"], "nursed_me", "x nursed me")
    assert bonds.kind(h, x, y) == "friend" and bonds.kind(h, a, b) == "enemy"
    x["ambition"] = y["ambition"] = {"key": "kind:kiln", "done": None}
    x["temper"]["ambitious"] = y["temper"]["ambitious"] = 0.9
    assert bonds.kind(h, a, kid) is None and bonds.rivals(x, y)
    for _ in range(3):
        opinions.move(h, cfg, x, y["id"], "helped_me", "y helped me"), opinions.move(h, cfg, y, x["id"], "helped_me", "x helped me")
    assert bonds.qualifies(h, x, y)
    h["tick"] -= h["tick"] % round(cfg["ticks_per_hour"])
    opinions.tick(h, cfg)
    assert bonds.kind(h, x, y) == "close" and bonds.close(h, y) == x["id"] and any(m["kind"] == "bond" for m in h["moments"]), "a close bond forms"
    assert not bonds.form(h, cfg, x, a, "again"), "one close bond each"
    x["genome"] = dict(x["genome"], hue=10, size=0.6)
    y["genome"] = dict(y["genome"], hue=300, size=1.4)
    for gene in GENES:
        x["temper"][gene], y["temper"][gene] = 0.05, 0.95
    x["eggs"] = 0
    x["temper"]["fertile"] = 1.0
    eggs = []
    for i in range(6):
        life.lay_egg(h, cfg, x, {"message": "Be well.", "name": "Pip%d" % i}, actions.clean)
        eggs.append(h["pets"][x["children"][-1]])
    for e in eggs:
        assert e["parents"] == [x["id"], y["id"]] and e["id"] in y["children"] and e["parent"] == x["id"]
    assert any(e["temper"]["curious"] > 0.5 for e in eggs) and any(e["temper"]["curious"] < 0.5 for e in eggs), "temper from both"
    blends = [bonds.blend(dict(x["genome"], a1=1, a2=1, a3=1, a4=1), dict(y["genome"], a1=2, a2=2, a3=2, a4=2), random.Random(s)) for s in range(10)]
    assert any(g["a1"] == 1 for g in blends) and any(g["a1"] == 2 for g in blends), "the body from both"
    e = eggs[0]
    e["laid"] = -10**6
    life.hatch(h, cfg, e)
    assert any("hatched" in ev for _, ev in y["events"]), "both parents hear it hatch"
    assert opinions.kin(h, e, y) and e.get("quirks")
    opinions.move(h, cfg, x, y["id"], "talked_harshly", "y snapped at me", d={"liking": -10})
    for _ in range(12):
        opinions.move(h, cfg, x, y["id"], "insult", "y insulted me")
    opinions.tick(h, cfg)
    assert not bonds.close(h, x) and any(m["kind"] == "bond broken" for m in h["moments"]), "and breaks"
    bonds.form(h, cfg, a, c, "stay with me")
    c["stage"] = "dead"
    opinions.tick(h, cfg)
    assert not bonds.close(h, a), "a death ends a close bond"

    # ---- §12 the migration: every living hob gets traits, opinions, memories; once; silently ----
    eng2, f2 = engine(v4(False), d + "/m")
    h2, cfg2 = eng2.house, eng2.cfg
    for _ in range(3):
        await eng2.tick()
    pets = [f2] + [hob(eng2, stage=s) for s in ("adult", "elder", "youngling", "child")]
    for p in pets:
        for g in GENES[9:]:
            p["temper"].pop(g, None)
        p["stage"] = p["stage"] if p is not f2 else "adult"
    f2["name"], pets[1]["name"] = "Ada", "Bel"
    h2["said"] = [{"tick": 5, "from": pets[1]["id"], "to": f2["id"], "kind": "give", "reply": True}] * 3 + [{"tick": 6, "from": f2["id"], "to": pets[1]["id"], "kind": "nuzzle ignored"}]
    world.moment(h2, "gift", "Bel gave Ada a cup", f2["id"], f2["room"])
    world.moment(h2, "first", "Ada was the first in the house to make a cup", f2["id"], f2["room"])
    pets[3]["parent"] = f2["id"]
    f2["children"].append(pets[3]["id"])
    n_moments = h2["n"]["moment"]
    migrate4.run(h2, cfg2)
    assert not h2.get("v4"), "nothing migrates while its switch is off"
    cfg2 = v4()
    opinions.ON = character.ON = True   # (as the house's next tick with them on would have it: until then they read as off)
    migrate4.run(h2, cfg2)
    for p in pets:
        assert all(g in p["temper"] for g in GENES) and len(p["values"]) == 2 and p["quirks"] and p["mood"]["mood"] in character.MOODS
        assert {q["id"] for q in pets if q is not p} | {"visitor"} <= set(p["opinions"]), "an opinion of every living hob and the visitor"
        assert all(c_["cause"] in opinions.DATA["causes"] for o in p["opinions"].values() for c_ in o["causes"])
        assert {"hunger", "safety", "pride"} <= set(p["needs"])
    assert f2["memories"] and opinions.of(f2, pets[1]["id"])["liking"] > 0 and opinions.of(f2, pets[3]["id"])["liking"] >= 4, "gifts warm; kin start warm"
    assert any("Bel gave me a cup" == m["text"] for m in f2["memories"]), [m["text"] for m in f2["memories"]]
    rank = sorted(pets[:3], key=lambda p: p["temper"]["generous"])
    assert h2["n"]["moment"] == n_moments, "the migration is silent"
    import copy
    before = copy.deepcopy(h2["pets"])
    migrate4.run(h2, cfg2)
    assert h2["pets"] == before, "and runs once"

    # ---- the switches off: v3.6c's behaviour for each part ----
    off = v4(False)
    eng3, p3 = engine(off, d + "/off")
    h3 = eng3.house
    for _ in range(3):
        await eng3.tick()
    at(eng3, 10)
    p3.update(stage="adult")
    p3["stage_at"]["adult"] = h3["tick"]
    q3 = hob(eng3)
    for _ in range(round(off["ticks_per_hour"]) + 5):
        await eng3.tick()
    for p in (p3, q3):
        assert set(p["needs"]) == set(world.NEEDS) and not p.get("opinions") and not p.get("memories") and "quirks" not in p, "nothing new appears"
    room3 = h3["rooms"][p3["room"]]
    bowl3 = next(n for n, o in room3["objects"].items() if "meal" in o.get("fix", {}))
    room3["objects"][bowl3]["servings"] = 3
    p3["last_eat"] = world.LONG_AGO
    _, fx, _ = actions.use(h3, off, p3, bowl3)
    assert fx.get("energy") == off["effects"]["eat"]["energy"] and needs.appetite(off, p3) == "energy", "needs4 off: food gives energy again"
    assert "hungry" not in __import__("engine.feel", fromlist=["x"]).feelings(p3) and "hunger" not in needs.feel(p3)
    assert opinions.move(h3, off, p3, q3["id"], "gift", "a gift") is None and not memories.add(h3, off, p3, "x", 3) and bonds.parents(h3, off, p3) is None
    assert not character.set_mood(h3, off, p3, "angry", "x") and character.mood_weight(p3, "ladder") == 1.0, "traits off: no moods"
    # (19 October 2026) and a saved opinion or a trait reaches no gate: not the ladder, a snub, who talks, nor the packet
    p3["opinions"] = {q3["id"]: dict(opinions.NEUTRAL, liking=-10, causes=[], fixed={}, since=0)}
    p3["temper"].update(kind=0.0, honest=0.0, generous=0.0)
    p3.update(quirks=["hums when it works"], values=["beauty", "family"])
    g3 = {"by": p3["id"], "against": q3["id"], "since": 0, "fresh": h3["tick"], "rung": 2, "history": []}
    assert opinions.of(p3, q3["id"])["liking"] == 0 and character.trait(p3, "kind") == 0.0
    assert conflict.why_not(h3, off, g3, p3, q3, 3) == "liking", "the ladder sees no dislike and no prickliness"
    assert talk.weight(h3, q3, p3, off) >= 1.5 and "nothing much" in talk.packet_of(h3, off, q3, p3), "they talk as anyone would"
    packet = talk.packet_of(h3, off, q3, p3)
    assert not any(w in packet for w in ("character:", "quirks:", "cares most about", "hums when it works")), packet
    eng3.talking = []   # (talk.tick's, when talk is on)
    assert not isinstance(talk.start(eng3, q3, p3, world.rnd(h3, "snub off")), dict), "no snub"
    await eng3.tick()
    a["needs"]["hunger"] = 50.0
    needs.tick(h, off)
    assert set(a["needs"]) == set(world.NEEDS) and a["needs4"]["hunger"] == 50.0, "needs4 switched off on a running house: put aside"
    needs.tick(h, cfg)
    assert a["needs"]["hunger"] < 50.01 and "safety" in a["needs"], "... and back when on"
    character.tick(h, off)
    assert character.mood(a) == "content"

    # ---- 18 October 2026, two days of v4.0 on live: moods that last, talks between grown hobs, a foundling's name ----
    m = hob(eng, stage="adult")
    character.give_character(h, cfg, m)
    h["tick"] = (h["tick"] // world.hours(cfg, 0.25) + 1) * world.hours(cfg, 0.25)
    character.tick(h, cfg)
    assert m["mood"]["until"] > h["tick"] and m["mood"]["why"], "a mood from the needs lasts a while, and says why: %s" % m["mood"]
    grown2, little = hob(eng, stage="adult"), hob(eng, stage="hatchling")
    assert talk.weight(h, m, grown2, cfg) > talk.weight(h, m, little, cfg) > talk.weight(h, little, hob(eng, stage="hatchling"), cfg), "two grown hobs talk first, babble last"
    stray = world.new_pet(h, cfg, m["room"], [3, 3])
    stray["founder"] = True   # (an egg that turned up by itself, as life.founder makes)
    life.hatch(h, cfg, stray)
    assert stray["name"] and any(x["kind"] == "named" and x["pet"] == stray["id"] for x in h["moments"]), "a foundling hatches with a name"


def report(path):
    """Migrate a copy of a data directory (never the live one) and say what each living hob woke up as."""
    from .check import scripted
    from .tick import Engine
    assert "/PetProject/data" not in str(path), "only ever a copy"
    eng = Engine(world.load_config(profile="live"), path, scripted)
    h = eng.house
    for p in world.alive(h):
        if p["stage"] == "egg":
            continue
        ops = sorted(p["opinions"].items(), key=lambda kv: -kv[1]["liking"])
        print("%s (%s): %s | quirks %s | values %s | mood %s" % (world.label(p), p["stage"], character.words(p), p["quirks"], p["values"], p["mood"]["mood"]))
        print("   likes most: %s; least: %s; %d memories, e.g. %s" % (", ".join("%s %+.1f" % (world.label(h["pets"][k]) if k in h["pets"] else k, v["liking"]) for k, v in ops[:2]),
              "%s %+.1f" % (world.label(h["pets"][ops[-1][0]]) if ops[-1][0] in h["pets"] else ops[-1][0], ops[-1][1]["liking"]), len(p["memories"]), p["memories"][-1]["text"][:80]))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))
    if len(sys.argv) > 1:
        report(sys.argv[1])
    print("character check passed")
