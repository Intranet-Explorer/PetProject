"""Self-check for SPEC-v4.2's memory and mind (helper B): §3.2 the staggered sunrise, §3.4-3.6 the packet's shape (its
order, the need suffix gone, each line once), §3.5 refusals in the world's terms that teach the house, §4 memories with
tags found by the situation, the self-page, what a talk leaves, §5 belief hooks (they move the planner, are inherited,
come from teaching; teaching can be refused), §10 the reflection's new fields, and a reply missing every new field
still a thought, counted. Each of [memory2], [selfpage] and [hooks] off leaves its data unchanged over a stub day.
    uv run python -m engine.check_mind"""
import asyncio
import json
import os
import tempfile

from . import actions, brain4, check_brain4 as B4, contracts as K, feel, hooks, memories, pages, planner, sleep, things, visitor, world
from . import self as self_page
from .brains import model
from .tick import Mind
from .world import generate_room, label


def spirit(cfg, **parts):
    cfg["spirit"]["on"] = True
    for p, v in parts.items():
        cfg[p]["on"] = v
    return cfg


async def house(d, **parts):
    real = B4.config

    def config(on=True):
        return spirit(real(on), **parts)
    B4.config = config
    try:
        eng, p0 = await B4.house(d)
    finally:
        B4.config = real
    return eng, p0


def retrieval(eng, pet):
    """§4.2: a memory tagged with the moment ranks over a heavier one that is not; §4.1 the engine tags a line; v4.0's
    callers (n fifth) still work."""
    h, cfg = eng.house, eng.cfg
    other = B4.hob(eng, h["rooms"][pet["room"]], [3, 3])
    other["name"] = "Wen"
    pet["memories"] = []
    heavy = memories.remember(h, cfg, pet, "a long grey day of nothing much", 4, "day")
    light = memories.remember(h, cfg, pet, "Wen showed me the clay by the kiln", 2, "talk")
    assert other["id"] in light["about"] and "clay" in light["what"] and heavy["about"] == [], light
    top = memories.relevant(h, cfg, pet, about=[other["id"]], what=["clay"], n=1)
    assert top and top[0] is light, "the tagged memory over the heavier untagged one: %s" % top
    assert memories.relevant(h, cfg, pet, n=1)[0] is heavy, "with nothing in play, the heavier"
    assert len(memories.relevant(h, cfg, pet, [other["id"]], 2)) == 2, "v4.0's callers give n fifth"
    assert memories.remember(h, cfg, pet, "Wen showed me the clay by the kiln", 3, "talk") is light and light["weight"] == 3 and len(pet["memories"]) == 2, "kept once"
    assert memories.shared(h, cfg, pet, other, 1)[0] is light, "a memory of one about the other is a shared subject"
    # §4.3 what a talk leaves (C's talk.py calls it), from a hand-made record
    rec = {"minds": {label(pet): {"wants": "to be liked", "holds": "that I broke the cup", "knows": "Wen is afraid of the cellar", "remember": "we sat by the pond"},
                     "Wen": {"wants": "the clay", "holds": "", "knows": "Oya is kind to the little ones", "remember": ""}}}
    assert memories.from_talk(h, cfg, rec, {label(pet): pet["id"], "Wen": other["id"]}) == 2
    k = next(m for m in pet["memories"] if m["kind"] == "knows")
    assert k["weight"] == 3 and other["id"] in k["about"] and k["by"] == "model", k
    assert any(m["kind"] == "subtext" and m["weight"] == 2 for m in other["memories"]) and K.since(h, "knows", -10 ** 9), "wants and holds at weight 2, and the ledger"
    print("mind: a tagged memory ranks over a heavier untagged one; a talk leaves its knows lines")


async def hooked(d):
    """§5.1: a hook moves the planner's score; a parent's hooked belief is its hatchling's, told, and acted on; §5.2 acted
    against it is tested; the Mind page shows the hook."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    room = h["rooms"][pet["room"]]
    door, rid = next(iter(room["doors"].items()))
    generate_room(h, cfg, rid)
    target, A = {"what": door}, cfg["activities"]["go"] if "go" in cfg["activities"] else next(a for a in cfg["activities"].values() if a["do"] == "go")
    name = next(n for n, a in cfg["activities"].items() if a["do"] == "go")
    before = planner.adjust(h, cfg, pet, name, A, target)
    bid = hooks.believe(eng, pet, "the %s is no place for me" % h["rooms"][rid]["name"], {"name": "avoid_place", "arg": h["rooms"][rid]["name"]}, "seen", True)
    assert bid and pet["hooked"] and pet["hooked"][0]["hook"]["name"] == "avoid_place"
    after = planner.adjust(h, cfg, pet, name, A, target)
    assert abs(after - before - cfg["hooks"]["avoid_place"]) < 1e-9, "the hook moves the score by [hooks] avoid_place: %s -> %s" % (before, after)
    assert pet["pressed"] == {bid: -1}
    planner.did(h, pet, {"name": "sit on", "do": "seat", "what": "rug", "since": h["tick"]}, True)
    assert m.mem.beliefs[-1]["hook"]["name"] == "avoid_place" and any(x["kind"] == "belief acted" for x in h["moments"]) and K.since(h, "acted", -10 ** 9), "kept away: acted on, a moment"
    # inheritance: an egg of its own hatches knowing it
    kid = world.new_pet(h, cfg, pet["room"], [4, 4], family=pet["family"])
    kid.update(parent=pet["id"])
    eng.minds[kid["id"]] = km = Mind(eng, kid)
    from . import life
    life.hatch(h, cfg, kid)
    assert kid.get("beliefs_due"), "its parent's hooked belief is left for it"
    hooks.due(eng, kid)
    told = next(b for b in km.mem.active() if b.get("hook"))
    assert told["hook"]["name"] == "avoid_place" and told["source"].startswith("told by") and told["truth"] is True and kid["hooked"], told
    kroom = h["rooms"][kid["room"]]
    kd = next(d for d, r in kroom["doors"].items() if r == rid) if rid in kroom["doors"].values() else door
    assert planner.adjust(h, cfg, kid, name, A, {"what": kd}) < planner.adjust(h, cfg, dict(kid, hooked=[]), name, A, {"what": kd}), "the child acts on it without knowing why"
    # tested: a model-set hook acted against, three times
    b2 = hooks.believe(eng, pet, "the rug is bad", {"name": "avoid_thing", "arg": "rug"}, "lived")
    for _ in range(cfg["hooks"]["tested"]):
        pet["pressed"] = {b2: -1}
        hooks.verdict(h, pet, {"name": "sit on", "do": "seat", "what": "rug"})
    hooks.due(eng, pet)
    assert brain4.tested(cfg, pet, 0) and next(b for b in m.mem.active() if b["id"] == b2)["tested"] == cfg["hooks"]["tested"], "tested, and told at night"
    text, ctx = brain4.reflect_packet(m)
    assert "look at it again" in text and "review" in ctx["asks"]
    words = pages.hook_words(told["hook"])
    assert "keeps away from" in words
    print("mind: a hook moves the planner (%+.1f), is inherited told, acted on, tested" % (after - before))


async def teaching(d):
    """§5.3 teach's three paths: a recipe is tomorrow's first aim, a skill a card line, a hint a belief with a hook; §5.4
    a proud hob doubts it; §5.6 an answer that says where to go is an aim; §5.5 a suggestion taken an aim from the visitor."""
    eng, pet = await house(d)
    h, cfg = eng.house, eng.cfg
    pet["recipes"] = {}
    key = next(k for k in cfg["craft"]["needs"] if not cfg["kinds"].get(k, {}).get("found"))
    ok, _ = visitor.t_teach(eng, pet, {"what": "kind:" + key}, None)
    assert ok and pet["aims_next"][-1]["kind"] == "make" and key in pet["aims_next"][-1]["text"] and pet["taught_recipe"]["kind"] == key, pet.get("aims_next")
    ok, _ = visitor.t_teach(eng, pet, {"what": "fishing"}, None)
    card = pages.pet_page(eng, pet["id"], lambda p: eng.minds[p["id"]].mem.beliefs)["pet"]
    assert ok and card["spirit"]["taught"] == "taught: fishing", card.get("spirit")
    pet["needs"]["pride"] = 10
    ok, _ = visitor.t_teach(eng, pet, {"what": "stay away from the cellar at night"}, None)
    b = next(b for b in eng.minds[pet["id"]].mem.active() if b.get("hook"))
    assert ok and b["hook"] == {"name": "avoid_place", "arg": "the cellar", "when": ""} and b["source"] == "told by the visitor" and not b["doubted"], b
    ok, _ = visitor.t_teach(eng, pet, {"what": "sing to the egg"}, None)
    assert any((x.get("hook") or {}).get("name") == "do_at" for x in eng.minds[pet["id"]].mem.active())
    ok, _ = visitor.t_teach(eng, pet, {"what": "the moon is made of cheese"}, None)
    assert pet["visitor_hints"] == ["the moon is made of cheese"], "a hint with no hook goes into tomorrow's plan"
    proud = B4.hob(eng, h["rooms"][pet["room"]], [2, 2])
    proud["needs"]["pride"] = 95
    visitor.t_teach(eng, proud, {"what": "the red fish is bad"}, None)
    pb = next(b for b in eng.minds[proud["id"]].mem.active() if b.get("hook"))
    assert pb["hook"]["name"] == "avoid_thing" and pb["doubted"] and pb["truth"] is None, pb
    assert any("isn't sure about that" in x["text"] for x in h["moments"]), "the page says so"
    assert hooks.score(h, cfg, proud, "eat", {"what": "fish"}) == 0.0, "a doubted belief does not act"
    q = {"n": 1, "pet": pet["id"], "q": "where is the book?", "tick": h["tick"], "kind": "question"}
    visitor.state(h)["inbox"].append(q)
    visitor.t_answer(eng, pet, {"text": "look in the cellar"}, q)
    a = pet["aims_next"][-1]
    assert a["from"] == "answer" and a["kind"] in ("explore", "learn") and a["why"] == "where is the book?", a
    visitor.t_suggest(eng, pet, {"text": "make a bowl for the little ones"}, None)
    m = eng.minds[pet["id"]]
    pet["planned"], pet["notable"], pet["last_call"] = None, [], h["tick"] - world.hours(cfg, 3)
    text, ctx = brain4.plan_packet(h, cfg, pet, m.mem)
    assert "before anything, today you mean to" in text and "the visitor told you: the moon is made of cheese" in text and "the visitor would like you to" in text, text
    m.think("plan")
    await m.thought
    m.adopt()
    froms = [a.get("from") for a in pet["aims"]]
    assert "taught" in froms and "visitor" in froms and pet["aims"][0]["from"] == "taught", pet["aims"]
    print("mind: teach's three paths (aim, card line, hooked belief), doubt, answers and suggestions as aims")


async def packets(d):
    """§3.4, §4.5: the order of a packet; the need suffix gone; §3.6 each line once; the stagger; refusals in the
    world's terms (§3.5); a reply without the new fields is still a thought, and counted."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    other = B4.hob(eng, h["rooms"][pet["room"]], [3, 3])
    memories.remember(h, cfg, pet, "%s sat with me by the window" % label(other), 3, "talk")
    text, ctx = brain4.plan_packet(h, cfg, pet, m.mem)
    marks = ["how you see yourself:", "you are %s, an adult hob" % label(pet), "with you:", "how you feel:", "what you remember that bears on this:", "the house could use", "what a day can hold", "Choose two or three"]
    at = [text.find(x) for x in marks]
    seen = [i for i in at if i >= 0]
    assert seen == sorted(seen) and all(i >= 0 for n, i in enumerate(at) if marks[n] != "the house could use"), (at, text)
    assert text.startswith("how you see yourself:"), "the self-page is the first block"
    whole = model.prompt4("plan", text, ctx)
    assert len(whole) <= cfg["brain4"]["packet_chars"], len(whole)
    # the suffix: gone from the packet, said once when a band is crossed
    said = feel.result("you rested", {"energy": 20}, {"curiosity": -5})
    assert "not from that" in said and brain4.plain(said) == "you rested", brain4.plain(said)
    from . import body
    body.state(pet)["since"] = [said, said, "you played with the ball; not from that but from the hour and the place, you grew a little more bored"]
    e = {"kind": "spoken", "text": "%s said to you: the kiln is warm" % label(other), "about": [other["id"]], "tick": h["tick"]}
    text, ctx = brain4.react_packet(h, cfg, pet, m.mem, e)
    assert "not from that" not in text and "a lot more rested" not in text and text.count("you rested") == 1, text
    pet["bands"] = {n: feel.level(pet, n) for n in pet["needs"]}
    assert brain4.feelings(h, cfg, pet).count("you feel") == 1, "no band crossed: no need said"
    pet["needs"]["energy"] = 5
    assert "exhausted" in brain4.feelings(h, cfg, pet) and "exhausted" not in brain4.feelings(h, cfg, pet), "said once, when it crosses"
    # §3.6: an aim twice is said once
    pet["aims"] = [{"text": "make a cup", "kind": "make", "since": None}] * 2
    text, _ = brain4.react_packet(h, cfg, pet, m.mem, e)
    assert text.count("make a cup") == 1
    # §3.2: the eldest plans first at sunrise
    B4.at(eng, cfg["sleep"]["wake_hour"])
    other["born"], pet["born"] = h["tick"] - 10, h["tick"] - 1000
    for p in h["pets"].values():
        p["sleep"] = None
    assert brain4.turn_to_plan(h, cfg, pet) and not brain4.turn_to_plan(h, cfg, other), "the eldest first"
    B4.at(eng, cfg["sleep"]["wake_hour"] + 0.99)
    assert brain4.turn_to_plan(h, cfg, other), "every one within the hour"
    # §3.5 a refusal in the world's terms, a memory with its tag
    store = next((r for r in h["rooms"].values() if r["type"] and r["id"] != pet["room"]), None)
    store["spots"].append({"bit": "clay", "pos": [3, 3], "ready": True})
    pet["rooms"][store["id"]] = h["tick"]
    steps, why = actions.stand_in(h, cfg, pet, {"type": "look", "target": "clay"})
    assert not steps and why == "the clay is in %s; you are in %s" % (store["name"], h["rooms"][pet["room"]]["name"]), why
    mem = next(x for x in pet["memories"] if x["text"] == why)
    assert mem["weight"] == 1 and mem["where"] == store["id"] and "clay" in mem["what"] and K.since(h, "refusal", -10 ** 9), mem
    pet["carrying"] = ["pebble"]
    why = actions.check({"type": "make", "near": "here", "recipe": {"kind": "ball", "material": "bouncy", "color": "red", "size": "small", "name": "b", "purpose": "p"}}, h, cfg, pet, m.mem)
    assert why.startswith("nothing you carry can be made bouncy; bouncy things are made from") and any(x["text"] == why and "bouncy" in x["what"] for x in pet["memories"]), why
    # §0.1 item 5: a reply with none of the new fields is a thought, defaulted, and counted
    pet["aims"], pet["notable"] = [], []

    async def old(kind, text, ctx):
        return {"thought": "hm", "feel": "content", "do": {"kind": "nothing", "who": "", "text": ""}, "steps": []} if kind == "react" else {"diary": "a day", "opinions": []}
    m.brain.think4 = old
    brain4.notable(h, cfg, pet, "insulted", "%s sneered at you" % label(other), [other["id"]])
    m.think("react")
    await m.thought
    m.adopt()
    assert pet["plan"] and K.since(h, "missed", -10 ** 9)[-1]["fields"] == ["remember"], "a react without remember is still a thought"
    pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
    await sleep.night(m)
    miss = K.since(h, "missed", -10 ** 9)[-1]
    assert miss["kind"] == "reflect" and {"remember", "self", "visitor"} <= set(miss["fields"]) and pet["last_night"]["dream"] == "a day", miss
    assert not pet.get("self") and self_page.wants_first(pet), "the self-page stays as it was, still to be written"
    print("mind: the packet's order, no need suffix, each line once, the stagger, refusals that teach, old replies counted")


async def night(d):
    """§10.2: the reflection writes up to three memories (weight 4, the model's), the self-page, a belief with its hook,
    the theory of the visitor, an old hob's bequest; a little one's page is the engine's, from its kin."""
    eng, pet = await house(d)
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    kid = B4.hob(eng, h["rooms"][pet["room"]], [3, 3], stage="child")
    kid["parent"] = pet["id"]
    assert self_page.page(h, cfg, kid)["who I am"].endswith("%s's family" % label(pet)), self_page.page(h, cfg, kid)
    from . import life
    from .brains.stub import Stub
    for n in range(3):
        brain4.jot(m, "you made a bowl of clay", 5)
        pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
        if n == 2:   # (in its last days)
            pet["born"] = h["tick"] - round((life.span(cfg, pet) - 1) * cfg["ticks_per_day"])
        await sleep.night(m)
        pet["sleep"] = None
    mine = [x for x in pet["memories"] if x.get("by") == "model" and x["kind"] == "reflect"]
    assert mine and all(x["weight"] == 4 for x in mine), pet["memories"][-5:]
    assert pet["self"] and pet["self_by"] == "model" and pet["last_self"]["page"] == pet["self"] and pet.get("visitor_theory"), (pet.get("self"), pet.get("visitor_theory"))
    hooked = {s: K.hook(hk) for s, hk in Stub.HOOKED}
    held = [b for b in m.mem.active() if b["statement"] in hooked]
    assert held and all(K.hook(b.get("hook")) == hooked[b["statement"]] for b in held), "what it learned carries the hook the reply gave it"
    assert pet.get("leave") and pet["leave"]["last_words"], "an old hob says what it would leave, and to whom"
    text, ctx = brain4.plan_packet(h, cfg, pet, m.mem)
    assert "  what I fear: " in text, "its own page is the first block tomorrow"
    # each kind's packet with its reply's form under the ceiling, and the stub's reply in its schema (the new fields required)
    e = {"kind": "insulted", "text": "%s sneered at you" % label(kid), "about": [kid["id"]], "tick": h["tick"]}
    for _ in range(40):
        memories.remember(h, cfg, pet, "a long memory about %s and the pond and the kiln, number %d" % (label(kid), _), 3, "talk")
    for kind, (text, ctx) in {"plan": brain4.plan_packet(h, cfg, pet, m.mem), "react": brain4.react_packet(h, cfg, pet, m.mem, e), "reflect": brain4.reflect_packet(m)}.items():
        assert len(model.prompt4(kind, text, ctx)) <= cfg["brain4"]["packet_chars"], (kind, len(model.prompt4(kind, text, ctx)))
        shape = model.schema4(kind, ctx)
        assert B4.valid(shape, await m.brain.think4(kind, text, ctx)) is None and set(K.FIELDS[kind]() if kind != "reflect" else K.reflect_fields(ctx["flaw"], ctx["old"])) <= set(shape["required"]), kind
    print("mind: the night writes memories, the self-page, a hooked belief, the theory")


async def stub_day(d, **parts):
    """A third of a stub day with spirit on: (its memories, beliefs.json, the hobs) for the switches' checks."""
    eng, pet = await house(d, **parts)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][pet["room"]]
    for i in range(3):
        B4.hob(eng, room, [2 + 3 * i, 5])
    for _ in range(cfg["ticks_per_day"] // 3):
        await eng.tick()
    for m in list(eng.minds.values()):
        m.pet["sleep"] = {"since": h["tick"], "day": h["clock"]["day"], "done": False}
        await sleep.night(m)
    beliefs = [b for m in eng.minds.values() for b in m.mem.beliefs]
    return h, [p for p in h["pets"].values() if p["stage"] not in ("egg", "dead")], beliefs


def switches(d):
    """Each part off (spirit on) leaves its data unchanged: [memory2] no tagged or model-written memory; [selfpage] no
    page; [hooks] no hook on any belief and nothing for the planner."""
    h, pets, beliefs = asyncio.run(stub_day(d + "/all"))
    assert any(m.get("by") == "model" for p in pets for m in p["memories"]), "with everything on, model-written memories"
    assert all(p.get("self") for p in pets) and K.since(h, "acted", -10 ** 9) is not None
    _, pets, _ = asyncio.run(stub_day(d + "/m", memory2=False))
    assert not any("by" in m or "what" in m for p in pets for m in p.get("memories", [])), "[memory2] off: v4.0.6's memories"
    _, pets, _ = asyncio.run(stub_day(d + "/s", selfpage=False))
    assert not any(p.get("self") or p.get("last_self") for p in pets), "[selfpage] off: no page"
    _, pets, beliefs = asyncio.run(stub_day(d + "/h", hooks=False))
    assert not any(p.get("hooked") or p.get("aims_next") or p.get("pressed") for p in pets) and not any("hook" in b for b in beliefs), "[hooks] off: no hooks"
    print("mind: [memory2], [selfpage] and [hooks] each off leave their data unchanged")


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        eng, pet = asyncio.run(house(d + "/r"))
        retrieval(eng, pet)
        asyncio.run(hooked(d + "/h"))
        asyncio.run(teaching(d + "/t"))
        asyncio.run(packets(d + "/p"))
        asyncio.run(night(d + "/n"))
        switches(d + "/s")
    print("check_mind: all passed")


if __name__ == "__main__":
    main()
