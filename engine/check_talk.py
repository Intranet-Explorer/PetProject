"""Self-check for SPEC-v4.0 §5 and §6.1 (helper B): conversations keep to their schema (stub replies validated against
it, and a model's reply taken through the same path), their effects are the engine's and clamped to named causes,
promised gifts become aims and are given or broken, help, lessons, trade, gossip and gatherings do what they say,
little ones babble, enemies snub, the budget and the pairing rules hold, and with [talk] off nothing of it runs.
    uv run python -m engine.check_talk"""
import asyncio
import json
import logging
import os
import re
import tempfile

import engine.tick  # noqa: F401  (first, as when any module is run alone)
from . import character, conflict, memories, opinions, talk, visitor
from .check import Script, at, engine, load_config
from .world import alive, new_pet

CALLS = {"move": [], "mem": [], "gossip": []}


def record():
    """Every opinion move, memory and piece of gossip, as it goes through (helper A's functions, or the skeleton's)."""
    if getattr(opinions.move, "recorded", False):
        return
    move, add, gossip = opinions.move, memories.add, opinions.gossip

    def m(house, cfg, pet, other, cause, why, **kw):
        CALLS["move"].append((pet["id"], other if isinstance(other, str) else other["id"], cause))
        return move(house, cfg, pet, other, cause, why, **kw)

    def a(house, cfg, pet, text, weight, about=(), kind=""):
        CALLS["mem"].append((pet["id"], text, weight, tuple(about), kind))
        return add(house, cfg, pet, text, weight, about, kind)

    def g(house, cfg, teller, listener, about, said, true=True):
        CALLS["gossip"].append((teller["id"], listener["id"], about, said, true))
        return gossip(house, cfg, teller, listener, about, said, true)
    m.recorded = True
    opinions.move, memories.add, opinions.gossip = m, a, g


def liking(pet, other, n):
    """Set an opinion straight into the house, as helper A keeps it."""
    pet.setdefault("opinions", {})[other["id"]] = dict(opinions.of(pet, other["id"]), liking=n)


def temper(pet, **axes):
    """Traits by their axes (-1..1), as genes."""
    for axis, v in axes.items():
        pet["temper"][character.GENE.get(axis, axis)] = (v + 1) / 2


async def house_of(d, n=3, **on):
    cfg = load_config()
    for part in ("talk", "visitor4", "traits", "opinions", "needs4", "ladder"):   # (helper A's and C's parts too: talk calls them)
        cfg[part]["on"] = True
    for k, v in on.items():
        cfg[k]["on"] = v
    cfg["weather"]["real"] = False
    eng, first = engine(cfg, d)
    h = eng.house
    for _ in range(n - 1):
        new_pet(h, cfg, first["room"], [3, 3], parent=first["id"])["laid"] = -10**6
    for _ in range(3):
        await eng.tick()
    at(eng, 10)
    pets = sorted(alive(h), key=lambda p: p["id"])
    for p in pets:
        p.update(stage="adult", sleep=None)
        p["stage_at"]["adult"] = h["tick"]
    h["moments"] = []   # (no hatching to celebrate unless a check asks for one)
    return eng, pets


def killing(eng, killer, witnesses=()):
    """A killing in the engine's own shape (conflict.killed, then life.die), of a hob made for it (19 October 2026: the
    checks wrote one by hand, with a "known": True the engine never makes)."""
    from . import life
    h, cfg = eng.house, eng.cfg
    dead = new_pet(h, cfg, killer["room"], [4, 4])
    dead.update(stage="adult", name="Dun", laid=-10**6)
    k = conflict.killed(h, cfg, killer, dead, [w["id"] for w in witnesses])
    life.die(h, cfg, dead, "violence")
    return k


async def settle(eng):
    """Let every call in flight finish before the house is closed."""
    while eng.busy():
        await asyncio.sleep(0)
    eng.close()


def reply(a, b, *came, lines=("Hello.", "Hello to you."), after=("same", "same"), mood=("content", "content")):
    A, B = talk.label(a), talk.label(b)
    return {"lines": list(lines), "came_of": [dict({"by": A, "about": "", "detail": ""}, **c) for c in came] or [{"what": "nothing", "by": A, "about": "", "detail": ""}],
            "after": {A: {"mood": mood[0], "toward": after[0]}, B: {"mood": mood[1], "toward": after[1]}}, "ask_visitor": {"who": "", "q": ""}}


def put(eng, a, b, rep):
    """Take a reply in as if it had come back from the brain."""
    return talk.apply(eng, {"a": a["id"], "b": b["id"], "room": a["room"], "schema": talk.schema(eng.house, a, b), "tick": eng.house["tick"]}, rep)


class Heard(logging.Handler):
    """The WARNING lines said while it is open."""
    def __enter__(self):
        self.lines = []
        logging.getLogger().addHandler(self)
        return self.lines

    def __exit__(self, *_):
        logging.getLogger().removeHandler(self)

    def emit(self, record):
        if record.levelno >= logging.WARNING:
            self.lines.append(record.getMessage())


class FakeModel(Script):
    """A brain that is not instant, so the model's path is taken; its chat answers with the stub's reply as text."""
    instant = False

    def __init__(self, eng):
        super().__init__()
        self.eng, self.asked = eng, []

    def chat(self, prompt, schema=None, think=False, max_tokens=None, temperature=0.7, kind="act"):
        self.asked.append((kind, prompt, schema))
        names = list(schema["properties"]["after"]["properties"])
        pets = {talk.label(p): p for p in alive(self.eng.house)}
        return "```json\n" + json.dumps(talk.stub_reply(self.eng.house, self.eng.cfg, pets[names[0]], pets[names[1]], talk.rnd(self.eng.house, "fake"))) + "\n```"


async def run(d):
    record()
    eng, (a, b, c) = await house_of(d + "/a")
    h, cfg = eng.house, eng.cfg
    a["name"], b["name"], c["name"] = "Ada", "Bram", "Cole"

    # ---- the schema, and replies held to it ----
    S = talk.schema(h, a, b)
    for traits in ({}, {"kind": -1, "generous": -1, "honest": -1}, {"kind": 1, "generous": 1, "social": 1, "playful": 1, "brave": -1}):
        temper(a, **traits)
        for n in (-8, -3, 0, 6):
            liking(a, b, n)
            rep = talk.stub_reply(h, cfg, a, b, talk.rnd(h, "x", n))
            assert talk.valid(rep, S), rep
    liking(a, b, 0)
    temper(a, kind=0, generous=0, honest=0, social=0, playful=0, brave=0)
    bad = reply(a, b)
    assert talk.valid(bad, S)
    for broken in (dict(bad, lines=["a"] * 7), dict(bad, lines=["x" * 141, "y"]), dict(bad, came_of=[{"what": "fight", "by": "Ada", "about": "", "detail": ""}]),
                   dict(bad, after={"Ada": bad["after"]["Ada"]}), dict(bad, extra=1), dict(bad, came_of=[dict(bad["came_of"][0], by="Zed")])):
        assert not talk.valid(broken, S), broken
    with Heard() as heard:
        assert put(eng, a, b, dict(bad, lines=["only one"])) is None and h["talks_failed"] == 1, "a reply out of shape is dropped"
        put(eng, a, b, "invalid json: Ada and Bram talked about the weather for a long time and then" + "x" * 200)
    assert h["talks_failed"] == 2 and [x["pets"] for x in h["failed_talks"]] == [[a["id"], b["id"]]] * 2 and len(h["failed_talks"][-1]["reply"]) == 120, h["failed_talks"]
    assert len(heard) == 2 and all("talks_failed" in x and a["id"] in x and "kind talk" in x for x in heard) and "only one" in heard[0], "(19 October 2026) and said, with the start of the reply"
    packet = talk.packet_of(h, cfg, a, b)
    assert len(packet) <= cfg["talk"]["packet_most"] and "Ada" in packet and "Bram" in packet and "voice:" in packet, packet
    assert not re.search(r"\d", packet), "no numbers in a packet: %s" % re.findall(r".{20}\d.{20}", packet)
    # (19 October 2026) trimmed per hob, then memories, on-mind and news go; the instructions are never cut (they were)
    for p, o in ((a, b), (b, a)):
        for i in range(30):
            memories.add(h, cfg, p, "%s and I spent a long day by the river among the reeds, and it rained the whole time, day %s" % (talk.label(o), "x" * i), 4, about=(o["id"],))
        p["quirks"] = ["hums long songs about everything it sees in the garden and the cellar and the attic"] * 2
        conflict.grudge(h, cfg, p["id"], o["id"], "it took the best seat by the stove and would not move however nicely it was asked")
    tail = "leave both empty for none)}"
    full = talk.packet_of(h, cfg, a, b)
    lines = full.split("\n")
    assert full.endswith(tail) and len(full) <= cfg["talk"]["packet_most"], full[-200:]
    assert [len(x.split(" | ")) for x in lines if x.startswith("- remembers: ")] == [3, 3] and all(len(x.split("; ")) <= 6 for x in lines if x.startswith("- on its mind: ")), full
    keep, cfg["talk"]["packet_most"] = cfg["talk"]["packet_most"], 1800
    small = talk.packet_of(h, cfg, a, b)
    assert small.endswith(tail) and len(small) <= 1800 and "remembers" not in small and "Ada (adult" in small, small
    cfg["talk"]["packet_most"], a["memories"], b["memories"], h["grievances"] = keep, [], [], []

    # ---- a conversation happens, through the engine's queue, in the contract's shape ----
    for p in (a, b, c):
        p["room"] = a["room"]
    talk.aim(h, a, "make a cup for the shelf", "a check", "make", None)
    for _ in range(round(cfg["ticks_per_hour"] * 3)):
        await eng.tick()
        if h.get("talks"):
            break
    for _ in range(3):
        await eng.tick()
    assert h.get("talks"), "two hobs together with something on their minds talk"
    t = h["talks"][0]
    assert set(t) >= {"n", "tick", "room", "a", "b", "lines", "came_of", "after"} and 2 <= len(t["lines"]) <= 6 and set(t["after"]) == {t["a"], t["b"]}, t
    assert [x["who"] for x in t["lines"]] == [t["a"], t["b"]] * (len(t["lines"]) // 2) + [t["a"]] * (len(t["lines"]) % 2), "they take turns"
    assert all(len(x["text"].split()) <= 20 for x in t["lines"])
    m = next(m for m in h["moments"] if m["kind"] == "talk")
    assert m["lines"] == t["lines"] and m["came_of"] == t["came_of"], "a moment of kind talk, with its lines and what came of it"
    eng.flush()
    back = [dict(zip(("n", "tick", "day", "hour", "kind", "text", "pet", "room"), r)) for r in eng.db.execute("SELECT n, tick, day, hour, kind, text, pet, room FROM moments WHERE kind='talk'")]
    assert talk.attach(h, back)[0]["lines"] == t["lines"], "and read back from the log for the story"
    assert eng.db.execute("SELECT count(*) FROM calls WHERE kind='talk'").fetchone()[0] >= 1, "one call of kind talk"
    assert talk.recent(h, 300), "the snapshot's recent talks"

    # ---- never the same two again within a world hour, unless something new happened ----
    pair = (h["pets"][t["a"]], h["pets"][t["b"]])
    key = "|".join(sorted((t["a"], t["b"])))
    h["talked"][key] = h["tick"]
    for p in pair:
        p["talking"] = None
    assert not any({x[1]["id"], x[2]["id"]} == set(key.split("|")) for x in talk.pairs(eng)), "not again within the hour"
    h["tick"] += 1
    conflict.grudge(h, cfg, t["a"], t["b"], "it took my seat")
    assert any({x[1]["id"], x[2]["id"]} == set(key.split("|")) for x in talk.pairs(eng)), "unless something new happened between them"
    h["grievances"] = []
    h["talked"][key] = h["tick"] - talk.hours(cfg, 1) - 1
    assert any({x[1]["id"], x[2]["id"]} == set(key.split("|")) for x in talk.pairs(eng)), "and after an hour, again"

    # ---- the budget: per_day a world day, fewer while the model is busy ----
    N = cfg["talk"]["per_day"]
    assert talk.budget(h, cfg) == N
    h["busy"] = [[h["tick"], cfg["ticks_per_hour"] * cfg["clock"]["tick_seconds"] * cfg["pace"] * 0.7]]
    assert talk.budget(h, cfg) == N // 2
    h["busy"] = [[h["tick"], cfg["ticks_per_hour"] * cfg["clock"]["tick_seconds"] * cfg["pace"] * 0.9]]
    assert talk.budget(h, cfg) == 1
    h["busy"] = []
    h["talks"] += [{"n": 0, "tick": h["tick"], "room": a["room"], "a": a["id"], "b": "p99", "lines": [], "came_of": [], "after": {}}] * N
    assert all(a not in x[1:] for x in talk.pairs(eng)), "a hob that has had its day's talks has no more"
    h["talks"][-1]["came_of"] = ["snub"]
    assert any(a in x[1:] for x in talk.pairs(eng)), "a snub doesn't count against the day's talks"
    h["talks"] = h["talks"][:-N]

    # ---- the effects: the engine's, by named causes ----
    h["grievances"], CALLS["move"][:] = [], []
    for p in (a, b, c):
        p["aims"], p["carrying"] = [], []
    # a promised gift becomes an aim; it is held out when they are together and it has something; else it is broken
    put(eng, a, b, reply(a, b, {"what": "gift promised", "detail": "a shiny shell"}, after=("warmer", "warmer")))
    g = a["aims"][-1]
    assert g["kind"] == "give" and g["target"] == b["id"] and not g["done"], a["aims"]
    a["carrying"] = ["shell"]
    h["tick"] += 10 - h["tick"] % 10
    talk.keep_promises(h, cfg)
    assert g["done"] and any(o["from"] == a["id"] and o["what"] == "shell" for o in b["offers"]), "the promise is kept: the shell held out"
    put(eng, c, b, reply(c, b, {"what": "gift promised", "detail": "a berry"}))
    h["tick"] += talk.hours(cfg, 24 * cfg["talk"]["promise_days"]) + 10 - (talk.hours(cfg, 24 * cfg["talk"]["promise_days"]) % 10)
    talk.keep_promises(h, cfg)
    assert c["aims"][-1]["done"] == "broken" and (b["id"], c["id"], "broke_promise") in CALLS["move"], "a promise not kept is broken"
    assert talk.grievances(h, b["id"], c["id"]), "and a broken promise is a reason on the ladder"
    # an insult is rung 2 (helper C's step and moment; the insulted one has a reason); a threat a reason both ways
    h["grievances"], CALLS["move"][:] = [], []
    rec = put(eng, a, b, reply(a, b, {"what": "insult", "detail": "you are slow"}, after=("cooler", "cooler")))
    gi = talk.grievances(h, a["id"], b["id"])[0]
    assert gi["rung"] == 2 and talk.grievances(h, b["id"], a["id"]), h["grievances"]
    assert (b["id"], a["id"], "insult") in CALLS["move"] and any(x[0] == b["id"] and x[2] == 4 and x[4] == "talk" for x in CALLS["mem"]), "remembered heavily"
    assert [x for x in CALLS["move"] if x[:2] == (b["id"], a["id"])] == [(b["id"], a["id"], "insult")], "one move for the pair: the cause, not the cause and 'cooler' too"
    assert rec["after"][a["id"]]["liking"] == -1 and any(m["kind"] == "insult" for m in h["moments"])
    h["grievances"] = []
    put(eng, b, a, reply(b, a, {"what": "threat", "detail": "watch yourself"}))
    assert talk.grievances(h, b["id"], a["id"]) and talk.grievances(h, a["id"], b["id"]) and (a["id"], b["id"], "threatened_me") in CALLS["move"]
    # an apology goes to whoever holds the grievance (helper C decides): a kind one takes it before long
    temper(a, kind=1)
    temper(b, kind=1)
    for i in range(20):
        h["tick"] += 1
        put(eng, a, b, reply(a, b, {"what": "apology"}))
        if not conflict.between(h, a["id"], b["id"]):
            break
    assert not conflict.between(h, a["id"], b["id"]) and any(m["kind"] == "making up" for m in h["moments"]), "made up: closed both ways"
    g = conflict.grudge(h, cfg, c["id"], a["id"], "it broke my cup")
    g["rung"] = 8
    temper(c, kind=-1)
    for i in range(5):
        h["tick"] += 1
        put(eng, a, c, reply(a, c, {"what": "apology"}))
    assert talk.grievances(h, c["id"], a["id"]), "a prickly hob far up the ladder doesn't take it"
    h["grievances"] = []
    # help: taken on as an aim by a willing hob; a prickly one that dislikes the asker refuses
    temper(b, kind=1)
    put(eng, a, b, reply(a, b, {"what": "help asked", "detail": "carry the clay to the kiln"}))
    assert b["aims"][-1]["kind"] == "help" and b["aims"][-1]["target"] == a["id"] and "clay" in b["aims"][-1]["text"], b["aims"]
    liking(c, a, -6)
    n = len(c["aims"])
    put(eng, a, c, reply(a, c, {"what": "help asked", "detail": "hold the other end"}))
    assert len(c["aims"]) == n and (a["id"], c["id"], "ignored_me") in CALLS["move"], "refused"
    liking(c, a, 0)
    # a lesson: a recipe passes; without one, a skill
    a["recipes"] = {"kind:cup": {"tick": 0, "from": "found"}}
    c["recipes"] = {}
    put(eng, a, c, reply(a, c, {"what": "lesson"}))
    assert "kind:cup" in c["recipes"] and (c["id"], a["id"], "taught_me") in CALLS["move"], "the recipe passes in the telling"
    a["skill"], c["skill"] = {"fishing": 60.0}, {}
    put(eng, a, c, reply(a, c, {"what": "lesson"}))
    assert c["skill"].get("fishing", 0) == cfg["talk"]["teach_skill"] and memories.skill(c, "fishing") > 0, c["skill"]
    # gossip goes through opinions.gossip; a sly hob's may be invented
    liking(a, c, 6)
    put(eng, a, b, reply(a, b, {"what": "gossip", "about": "Cole"}))
    assert CALLS["gossip"][-1][:3] == (a["id"], b["id"], c["id"]) and CALLS["gossip"][-1][4], CALLS["gossip"]
    temper(a, honest=-1)
    for i in range(12):
        h["tick"] += 1
        put(eng, a, b, reply(a, b, {"what": "gossip", "about": "Cole"}))
    assert any(not x[4] and x[3] < 0 for x in CALLS["gossip"]), "a sly hob's gossip is sometimes false"
    temper(a, honest=0)
    # trade: fair, one for one; a sly bargainer swindles
    a["carrying"], b["carrying"] = ["hook"], ["fish"]
    put(eng, a, b, reply(a, b, {"what": "trade"}))
    assert a["carrying"] == ["fish"] and b["carrying"] == ["hook"], "fair"
    temper(a, honest=-1)
    for i in range(20):
        a["carrying"], b["carrying"] = ["pebble"], ["fish"]
        h["tick"] += 1
        put(eng, a, b, reply(a, b, {"what": "trade"}))
        if not b["carrying"]:
            break
    assert not b["carrying"] and "fish" in a["carrying"] and talk.grievances(h, b["id"], a["id"]) and (b["id"], a["id"], "lied_to_me") in CALLS["move"], "a swindle: the fish gone, nothing back, a grievance"
    temper(a, honest=0)
    # a plan becomes an aim for both
    put(eng, a, b, reply(a, b, {"what": "plan", "detail": "build a kiln together"}))
    assert a["aims"][-1]["kind"] == b["aims"][-1]["kind"] == "plan" and a["aims"][-1]["target"] == b["id"]
    # "stay with me": a close bond, only between friends both ways
    liking(a, b, 1)
    liking(b, a, 1)
    assert put(eng, a, b, reply(a, b, {"what": "close bond"}))["came_of"] == ["nothing"] and talk.bonds.kind(h, a["id"], b["id"]) != "close"
    liking(a, b, 8)
    liking(b, a, 8)
    assert b["parent"] == a["id"] and opinions.kin(h, a, b)
    put(eng, a, b, reply(a, b, {"what": "close bond"}))   # (19 October 2026: parent and child bonded, and laid two-parent eggs)
    assert talk.bonds.kind(h, a["id"], b["id"]) == "friend" and not talk.bonds.close(h, a) and talk.bonds.parents(h, cfg, a) is None, "kin are friends, never bonded"
    b["parent"] = None   # (strangers, for a moment)
    put(eng, a, b, reply(a, b, {"what": "close bond"}))
    assert talk.bonds.kind(h, a["id"], b["id"]) == "close", "a close bond, formed in a conversation"
    b["parent"], h["bonds"] = a["id"], []
    # a lie found out when the one lied to talks with the one it was about
    h["lies"] = [{"tick": h["tick"], "teller": c["id"], "listener": a["id"], "about": b["id"], "said": -6}]
    cfg["talk"]["lie_found"] = 1.0
    put(eng, a, b, reply(a, b))
    assert not h["lies"] and (a["id"], c["id"], "lied_to_me") in CALLS["move"], "found out"
    # justice: what a hob says the family should do with a killer counts as its vote (helper C)
    killing(eng, c, (a,))
    assert any("what to do about Cole" in x for x in talk.on_mind(h, cfg, a, b))
    put(eng, a, b, reply(a, b, {"what": "justice", "about": "Cole", "detail": "drive out"}))
    assert h["killings"][-1]["votes"][a["id"]] == "driven out", h["killings"][-1]
    h["killings"] = []
    # a gathering, started by a social hob, for a birth; the solitary slip away; those who came remember it
    temper(a, social=1)
    temper(b, social=0.5)
    temper(c, social=-1)
    talk.moment(h, "hatched", "Dot hatched", b["id"], b["room"])
    put(eng, a, b, reply(a, b, {"what": "gathering"}))
    G = h["gathering"]
    assert G and G["kind"] == "celebration" and a["id"] in G["who"] and c["id"] not in G["who"] and b["aims"][-1]["kind"] == "gather", G
    h["tick"] = G["until"]
    talk.gathering_tick(h, cfg)
    assert h["gathering"] is None and set(h["gatherings"][-1]["came"]) >= {a["id"], b["id"]} and any(x[4] == "gathering" for x in CALLS["mem"])
    temper(a, social=0)
    temper(c, social=0)
    # a solitary hob starts none
    temper(c, social=-1)
    assert put(eng, c, b, reply(c, b, {"what": "gathering"}))["came_of"] == ["nothing"]
    # little ones babble, and their threats come to nothing
    b["stage"] = "hatchling"
    n = len(h["grievances"])
    rec = put(eng, b, a, reply(b, a, {"what": "threat"}, lines=("I will get you, you wait and see.", "Oh, will you?")))
    assert rec["lines"][0]["text"] != "I will get you, you wait and see." and len(h["grievances"]) == n and rec["came_of"] == ["nothing"], rec
    b["stage"] = "adult"
    # every move was by a named cause, and at most one for the talk itself a pair
    assert {x[2] for x in CALLS["move"]} <= set(talk.CAUSES) | {"gossip", "kin", "family_says"}, {x[2] for x in CALLS["move"]} - set(talk.CAUSES)
    missing = (set(talk.CAUSES) | set(visitor.CAUSES)) - set(opinions.DATA["causes"])   # (helper A's data: each cause has its amounts there)
    assert not missing, "causes B uses that opinions.toml lacks: %s" % sorted(missing)
    # clamped: a cause moves an opinion by its amount in opinions.toml, however the talk went
    liking(b, a, 0)
    before = opinions.of(b, a["id"])["liking"]
    put(eng, a, b, reply(a, b, {"what": "insult"}, {"what": "insult"}, {"what": "insult"}, after=("cooler", "cooler")))
    assert before - opinions.of(b, a["id"])["liking"] <= 3 * abs(opinions.DATA["causes"]["insult"]["liking"]), "no more than the causes' amounts"
    assert opinions.of(b, a["id"])["causes"][-1]["cause"] == "insult", "and every change has its cause"
    h["grievances"] = []
    liking(b, a, 0)

    # ---- the want to talk (19 October 2026): none just after a real talk, it grows, sooner for a sociable hob; babble and snubs don't feed it ----
    keep, h["talks"] = h["talks"], []
    temper(a, social=0)
    temper(b, social=0)
    assert talk.want(h, cfg, a) == 1.5, "never talked: it wants to"
    h["talks"] = [{"n": 0, "tick": h["tick"], "room": a["room"], "a": a["id"], "b": b["id"], "lines": [], "came_of": [], "after": {}}]
    assert talk.want(h, cfg, a) == 0 and all(x[0] == 0 for x in talk.pairs(eng) if {x[1]["id"], x[2]["id"]} == {a["id"], b["id"]})
    H = talk.hours(cfg, cfg["talk"]["want_hours"])
    h["tick"] += H
    assert abs(talk.want(h, cfg, a) - 1) < 1e-9
    temper(a, social=1)
    assert talk.want(h, cfg, a) == 1.5, "a sociable hob wants company sooner"
    temper(a, social=0)
    h["talks"][-1]["came_of"] = ["snub"]
    assert talk.want(h, cfg, a) == 1.5, "a snub is no conversation"
    h["talks"][-1]["came_of"], b["stage"] = [], "hatchling"
    assert talk.want(h, cfg, a) == 1.5 and talk.want(h, cfg, b) == 1, "babble doesn't feed a grown hob's want, but a little one's"
    b["stage"], h["tick"] = "adult", h["tick"] - H
    cfg["talk"]["want"] = False
    assert talk.want(h, cfg, a) == 1, "off: as before"
    cfg["talk"]["want"], h["talks"] = True, keep

    # ---- a small dislike (19 October 2026): no turning away, and they talk as often as anyone ----
    liking(b, a, -1)
    assert -1 > cfg["talk"]["snub_below"] and talk.weight(h, a, b, cfg) > 0.3, "liking -1 is no reason to turn away"
    liking(b, a, 0)

    # ---- enemies snub: no call, one rung ----
    liking(b, a, -5)
    temper(b, kind=-1)
    calls = eng.db.execute("SELECT count(*) FROM calls").fetchone()[0]
    rec = talk.start(eng, a, b, talk.rnd(h, "snub"))
    assert rec["came_of"] == ["snub"] and talk.grievances(h, b["id"], a["id"])[0]["rung"] == 1 and (a["id"], b["id"], "ignored_me") in CALLS["move"]
    assert rec in h["snubs"] and rec not in h["talks"] and rec in talk.recent(h, 10), "(19 October 2026) kept apart from the talks; the page still sees it"
    assert any(m["kind"] == "snub" for m in h["moments"])
    await asyncio.sleep(0)
    assert eng.db.execute("SELECT count(*) FROM calls").fetchone()[0] == calls, "a snub needs no thought"
    liking(b, a, 0)
    temper(b, kind=0)

    # ---- the model's path: the prompt and schema handed to chat, its text parsed and taken in ----
    for p in (a, b):
        p["talking"] = None
    m = eng.minds[a["id"]]
    real, m.brain = m.brain, FakeModel(eng)
    h["talks"] = []
    talk.start(eng, a, b, talk.rnd(h, "model"))
    for _ in range(3):
        await asyncio.sleep(0.05)
        await eng.tick()
    kind, prompt, schema = m.brain.asked[0]
    assert kind == "talk" and "Write their conversation" in prompt and schema["properties"]["lines"]["maxItems"] == 6, kind
    assert h["talks"] and h["talks"][-1]["a"] == a["id"], "the model's reply, parsed from its text, is taken in"
    m.brain = real

    # ---- 19 October 2026: two hobs with one name; gossip about a hob that died between the ask and the reply ----
    b["name"] = a["name"]
    rep = talk.stub_reply(h, cfg, a, b, talk.rnd(h, "twins"))
    assert talk.valid(rep, talk.schema(h, a, b)) and set(put(eng, a, b, rep)["after"]) == {a["id"], b["id"]}, "one name, two hobs: taken in by their ids"
    b["name"] = "Bram"
    until = h["tick"] + talk.hours(cfg, 1)
    a["talking"], b["talking"] = {"with": b["id"], "until": until}, {"with": a["id"], "until": until}
    fut = asyncio.get_running_loop().create_future()
    fut.set_result(reply(a, b, {"what": "gossip", "about": "Cole"}, after=("warmer", "warmer")))
    eng.talking.append({"fut": fut, "a": a["id"], "b": b["id"], "room": a["room"], "schema": talk.schema(h, a, b), "tick": h["tick"]})
    n, ngossip = len(h["talks"]), len(CALLS["gossip"])
    eng.kill(c, "old age")
    talk.tick(eng)
    assert len(h["talks"]) == n + 1 and h["talks"][-1]["lines"] and not a["talking"] and not b["talking"], "the talk is kept, and they are free again"
    assert len(CALLS["gossip"]) == ngossip and c["stage"] == "dead", "gossip about the dead moves nothing"
    return eng


async def examples(d):
    """Three conversations from the stub, as they come out of the engine."""
    eng, (a, b, c) = await house_of(d + "/ex")
    h, cfg = eng.house, eng.cfg
    a["name"], b["name"], c["name"] = "Ada", "Bram", "Cole"
    temper(a, generous=1, kind=1, social=1, playful=1)
    temper(b, kind=-1, generous=-1, honest=-1)
    temper(c, curious=1, brave=-1)
    a["recipes"] = {"kind:cup": {"tick": 0, "from": "found"}}
    b["carrying"], c["carrying"] = ["hook"], ["fish"]
    liking(b, c, -4)
    out = []
    for x, y, seed in ((a, c, "e1"), (b, c, "e2"), (c, a, "e3")):
        for p in (x, y):
            p["talking"] = None
        if x is b:
            temper(x, kind=-0.5)
            character.set_mood(h, cfg, x, "angry", "a check")
            liking(c, b, 1)
        talk.start(eng, x, y, talk.rnd(h, seed))
        for _ in range(2):
            await asyncio.sleep(0)
            await eng.tick()
        t = h["talks"][-1]
        out.append(t)
    return eng, out


def show(t, h):
    name = lambda pid: talk.label(h["pets"][pid])
    print("  %s and %s:" % (name(t["a"]), name(t["b"])))
    for x in t["lines"]:
        print('    %s: "%s"' % (name(x["who"]), x["text"]))
    print("    came of it: %s; the engine: %s; after: %s" % (", ".join(t["came_of"]), "; ".join(t.get("did", [])) or "-",
          ", ".join("%s %s (%+d)" % (name(k), v["mood"], v["liking"]) for k, v in t["after"].items())))


async def off(d):
    """[talk] off: v3.6c's house: no conversations, no calls of kind talk, nothing added to the house."""
    eng, (a, b, c) = await house_of(d + "/off", talk=False)
    h, cfg = eng.house, eng.cfg
    talk.aim(h, a, "make a cup", "a check", "make", None)
    for _ in range(round(cfg["ticks_per_hour"] * 4)):
        await eng.tick()
    assert not h.get("talks") and "talked" not in h and not getattr(eng, "talking", None), "off: nobody talks"
    assert eng.db.execute("SELECT count(*) FROM calls WHERE kind='talk'").fetchone()[0] == 0
    assert talk.tick(eng) is None
    await settle(eng)


def names_and_babes():
    """18 October 2026: a line never keeps its speaker's name in front; two little ones' babble changes nothing."""
    a, b = {"id": "p1", "name": "Bogna"}, {"id": "p2", "name": "Wen"}
    assert talk.unnamed("Bogna: Bogna: Align the leaves.", (a, b)) == "Align the leaves."
    assert talk.unnamed("Wen: mm-da", (a, b)) == "mm-da" and talk.unnamed("Look: a leaf", (a, b)) == "Look: a leaf"


async def plain(d):
    """SPEC-v4.2.2 plain speech (spirit on): the stub's talk packet has §1's prompt with the four examples, its angle
    brackets filled, and none of the old register's words; a talk whose lines don't answer each other is asked once more
    (one such pair is let through) and counted, and a purple one counted; the voice card is style and cares and nothing
    else; the reflection's packet and the self-page migration carry §3's example."""
    from . import brain4, check_brain4 as B4, check_mind as M, contracts as K, drives
    from . import self as self_page
    from .check_spirit_talk import Model, talk_once
    eng, a = await M.house(d)
    h, cfg = eng.house, eng.cfg
    b = B4.hob(eng, h["rooms"][a["room"]], [3, 3])
    b["name"] = "Wen"
    for p in (a, b):
        B4.grow(h, p, "adult")
    packet = talk.packet2(h, cfg, a, b, "the lights went out")
    for x in ("Two neighbours in a small house, talking.", "Each line answers the line before it", "What's between them right now: the lights went out.",
              "Example 1 (a favour, a grumble):", "Example 2 (news, with content):", "Example 3 (a child and a grown hob):", "Example 4 (something underneath):",
              "  Wren: Sipho. Sipho! Have you seen the small hammer?", "  Lio: Leave it, Tam. Do you want a cup or not? I made four.",
              "%s wants from this talk: fill in. %s won't say: fill in (its secret" % (talk.label(a), talk.label(a)), "Wen wants: fill in. Wen won't say: fill in."):
        assert x in packet, x
    assert re.search(r"taking turns, \d lines in all", packet) and "<" not in packet, "the engine fills every angle bracket"
    assert len(packet) <= cfg["talk"]["packet_most"], len(packet)
    old = ("small household spirit", "your ways", "what you care about", "the house could use", "a feeling from", "as in: \"")
    e = {"kind": "insulted", "text": "Wen sneered at you", "about": [b["id"]], "tick": h["tick"]}
    for text in (packet, brain4.react_packet(h, cfg, a, eng.minds[a["id"]].mem, e)[0], brain4.plan_packet(h, cfg, a, eng.minds[a["id"]].mem)[0]):
        assert not [w for w in old if w in text], [w for w in old if w in text]
    assert set(a["voice"]) == {"style", "cares"} and a["voice"]["style"] in K.STYLES, a["voice"]
    assert "how you talk: " + K.STYLES[a["voice"]["style"]] in brain4.plan_packet(h, cfg, a, eng.minds[a["id"]].mem)[0]
    # §6 the exchange check: two pairs that don't answer, and it is asked once more, reminded; one is let through; purple counted
    full = talk.stub_reply2(h, cfg, a, b, talk.rnd(h, "f"), "the lights went out")
    assert talk.monologue(full["lines"], a, b) < 2, ("the stub's own talk answers itself", full["lines"])
    mono = dict(full, lines=["The kettle is boiling.", "Clouds drift over the hills.", "Seven beans remain.", "Lanterns glow softly."])
    assert talk.monologue(mono["lines"], a, b) == 3
    brain = Model(mono, full)
    rec = await talk_once(eng, a, b, brain)
    assert len(brain.asked) == 2 and brain.asked[1]["prompt"].endswith(talk.AGAIN) and len(K.since(h, "monologue", 0)) == 1, brain.asked
    assert [x["text"] for x in rec["lines"]] == full["lines"][:len(rec["lines"])], "the second reply is taken"
    one = dict(full, lines=["Have you seen the kettle?", "The kettle is on the stove.", "Lanterns glow softly.", "Lanterns? You lit them at the hour?"])
    brain = Model(one)
    rec = await talk_once(eng, a, b, brain)
    assert len(brain.asked) == 1 and len(K.since(h, "monologue", 0)) == 1 and rec, "one pair is let through"
    assert K.since(h, "purple", 0)[-1]["why"] == "the hour", K.since(h, "purple", 0)
    assert talk.purple(["x" * 201, "y" * 201]) == "long lines" and not talk.purple(["x" * 201, "Fine."])
    # §3 the self-page: the example in the reflection's packet, and the migration's one call a grown hob
    text, _ = brain4.reflect_packet(eng.minds[a["id"]])
    assert self_page.PLAIN in text and "what I owe: I owe Antonia more patience." in text
    page = {k.replace(" ", "_"): "I'm %s, line %d." % (talk.label(a), i) for i, k in enumerate(K.SELF)}
    real, eng.minds[a["id"]].brain = eng.minds[a["id"]].brain, Model({"self": page})
    asked = eng.minds[a["id"]].brain
    h["migrated"].pop("v422_self", None)
    lines = await self_page.rewrite(eng)
    eng.minds[a["id"]].brain = real
    assert a["self"]["who I am"] == page["who_I_am"] and self_page.PLAIN in asked.asked[0]["prompt"] and any(talk.label(a) + ":" in l for l in lines), lines
    assert await self_page.rewrite(eng) == [], "once a house"
    assert len(K.self_page({"who I am": "x" * 400})["who I am"]) == 320 and "Each line under thirty words." in self_page.PLAIN, "v4.2.3: a line keeps 320 characters"
    # v4.2.3 each living hob's beliefs in plain words, one call a hob; hook and id kept; once a house
    mem = eng.minds[a["id"]].mem
    bid = mem.write("The hinge is a wound I will not close, a door I open onto the hour.", h["tick"], hook={"name": "avoid_place", "arg": "workshop", "when": ""})
    from . import hooks
    hooks.mirror(a, mem)
    held = [b["id"] for b in mem.active()]
    real, eng.minds[a["id"]].brain = eng.minds[a["id"]].brain, Model({i: "I haven't finished the hinge and it bothers me." if i == bid else "" for i in held})
    asked = eng.minds[a["id"]].brain
    h["migrated"].pop("v423_beliefs", None)
    said = await self_page.plain_beliefs(eng)
    eng.minds[a["id"]].brain = real
    b = next(b for b in mem.active() if b["id"] == bid)
    assert b["statement"] == "I haven't finished the hinge and it bothers me." and b["hook"]["name"] == "avoid_place", b
    assert any(x["id"] == bid and x["text"] == b["statement"] for x in a["hooked"]) and "thirty words" in asked.asked[0]["prompt"] and "was: The hinge" in said[0], said
    assert await self_page.plain_beliefs(eng) == [], "once a house"
    print("plain speech: the four examples and no old words; a monologue asked again, one pair let through; purple counted; the self-page's example")
    print("  " + lines[0].replace("\n", "\n  "))
    await settle(eng)


async def main():
    names_and_babes()
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:   # (anywhere: PET_SCRATCH when set, else the system's)
        await settle(await run(d))
        print("conversations: schema, effects, promises, help, lessons, trade, gossip, gatherings, snubs, budget, pairing: ok")
        await off(d)
        print("[talk] off: no conversations: ok")
        await plain(d + "/plain")
        eng, exs = await examples(d)
        print("three conversations from the stub:")
        for t in exs:
            show(t, eng.house)
        await settle(eng)


if __name__ == "__main__":
    asyncio.run(main())
    print("check_talk passed")
