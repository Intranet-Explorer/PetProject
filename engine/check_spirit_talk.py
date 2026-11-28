"""Self-check for SPEC-v4.2 §6 (character) and §7 (talk with subtext), helper C: a stub hatchling is given a drive, a
flaw against it and a voice card; the drive and flaw move the planner, a hot hob climbs faster, "to be loved by one"
finds its one, a drive changes once after a betrayal; secrets are kept from what nobody saw and come out in talk; the
migration gives every living hob a drive, a flaw, a voice and (for a liar) a secret, once; a talk has a subject and
each side's minds, which become memories; a reply without wants/holds/knows is failed and asked again, and defaulted
and counted if the second lacks them too; a hatchling learns a word; [drives] and [talk2] off each leave their data
unchanged over a stub day.
    uv run python -m engine.check_spirit_talk"""
import asyncio
import json
import os
import tempfile

from . import brain4, check_brain4 as B4, check_mind as M, contracts as K, drives, memories, opinions, planner, talk
from .world import label, moment


class Model:
    """A brain that is not instant: its chat answers from a list (a voice card, or talk replies), and records what it was asked."""
    instant = False

    def __init__(self, *answers):
        self.answers, self.asked = list(answers), []

    def chat(self, prompt, schema=None, think=False, max_tokens=None, temperature=0.7, kind="act"):
        self.asked.append({"kind": kind, "prompt": prompt, "schema": schema, "think": think})
        return json.dumps(self.answers.pop(0))


async def talk_once(eng, a, b, brain=None):
    """One conversation from a to b, through talk.start and talk.apply (with `brain` as a's for it). Returns the record."""
    m = eng.minds[a["id"]]
    real, m.brain = m.brain, brain or m.brain
    a["talking"] = b["talking"] = None
    try:
        talk.start(eng, a, b, talk.rnd(eng.house, "check", eng.house["tick"], a["id"]))
        t = eng.talking.pop()
        return talk.apply(eng, t, await t["fut"])
    finally:
        m.brain = real


async def character(d):
    eng, p0 = await M.house(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][p0["room"]]
    kid = B4.hob(eng, room, [3, 3], stage="hatchling")
    # §6.1-6.4 drawn at hatching: a drive, a flaw against it, the engine's voice card (v4.2.2 §2: never the model's)
    assert kid["drive"]["name"] in K.DRIVES and kid["flaw"]["name"] in K.FLAWS, (kid.get("drive"), kid.get("flaw"))
    assert kid["flaw"]["name"] in drives.character.DATA["drives"][kid["drive"]["name"]]["flaws"], "the flaw is one against its drive"
    v = kid["voice"]
    assert set(v) == {"style", "cares"} and v["style"] in K.STYLES and v["cares"] == drives.character.DATA["voice"]["cares"][kid["drive"]["name"]], v
    assert drives.line(kid).startswith("what you want most: %s; what you've done about it so far: nothing yet; your flaw: " % kid["drive"]["name"]), drives.line(kid)
    assert brain4.drive_line(cfg, kid) == drives.line(kid), "brain4's packets read drives.line"
    # no model is asked for a voice, even a real one (v4.2.2 §2)
    real, eng.minds[kid["id"]].brain = eng.minds[kid["id"]].brain, Model({})
    asked = eng.minds[kid["id"]].brain
    talk.tick(eng)
    await asyncio.sleep(0)
    eng.minds[kid["id"]].brain = real
    assert kid["voice"] == v and not any(x["kind"] == "voice" for x in asked.asked), "the card is the engine's"
    # the react packet says how it talks in the style's one line, and no sample lines
    kid["voice"] = K.voice({"style": "grumbly", "cares": "the book"})
    e = {"kind": "insulted", "text": "%s sneered at you" % label(p0), "about": [p0["id"]], "tick": h["tick"]}
    B4.grow(h, kid, "adult")
    text, _ = brain4.react_packet(h, cfg, kid, eng.minds[kid["id"]].mem, e)
    assert "how you talk: " + K.STYLES["grumbly"] + "; cares about the book" in text and '" / "' not in text, text[:600]
    # the planner: what serves the drive, and what the flaw pulls at
    kid["drive"], kid["flaw"] = K.drive({"name": "to leave the house"}), K.flaw({"name": "lazy"})
    go = next(n for n, a in cfg["activities"].items() if a["do"] == "go")
    nap = next(n for n, a in cfg["activities"].items() if a["do"] == "nap")
    without = dict(kid, drive=None, flaw=None)
    for name, more in ((go, cfg["drives"]["serve"]), (nap, cfg["drives"]["flaw"])):
        A = cfg["activities"][name]
        diff = planner.adjust(h, cfg, kid, name, A, {}) - planner.adjust(h, cfg, without, name, A, {})
        assert abs(diff - more) < 1e-9, (name, diff)
    # a hot hob climbs faster: a roll that misses a snub's chance lands within a hot hob's
    from . import conflict
    p0["mood"] = kid["mood"] = B4.calm(h)
    opinions.entry(h, cfg, kid, p0["id"])["liking"] = -5
    g = conflict.grudge(h, cfg, kid["id"], p0["id"], "a check")
    g["since"] = g["last_act"] = h["tick"] - 10 ** 6
    chance = conflict.C(cfg)["rung"][0]["chance"] * (conflict.C(cfg)["ladder"]["night"] if h["clock"]["phase"] == "night" else 1)
    roll, conflict.rnd = conflict.rnd, lambda *k: type("R", (), {"random": lambda self: chance * (1 + drives.HOT) / 2})()
    try:
        assert conflict.climb(h, cfg, g) is None, "not hot: the roll misses"
        kid["flaw"] = K.flaw({"name": "hot"})
        assert conflict.climb(h, cfg, g) is not None and g["rung"] == 1, "hot: the same roll takes the rung"
    finally:
        conflict.rnd = roll
    conflict.close(h, cfg, g, "a check")
    # an envious hob resents another's first
    kid["flaw"] = K.flaw({"name": "envious"})
    memories.new_moments(h, "drives")
    moment(h, "first", "%s made the first cup" % label(p0), p0["id"], p0["room"])
    drives.tick(eng)
    assert opinions.of(kid, p0["id"])["causes"][-1]["cause"] == "envy"
    # "to be loved by one": its one at the youngling stage, and a love it has never said is its secret
    kid["drive"] = K.drive({"name": "to be loved by one"})
    kid["stage"] = "youngling"
    opinions.entry(h, cfg, kid, p0["id"])["liking"] = 8
    drives.standing(h, cfg, kid)
    assert kid["drive"]["target"] == p0["id"] and kid["secret"]["kind"] == "feeling" and label(p0) in kid["secret"]["text"], (kid["drive"], kid.get("secret"))
    kid["stage"] = "adult"
    # a secret left by another part (A's fall) is taken up only when it has none
    K.secret_later(kid, "fall", "I shoved someone", tick=h["tick"])
    talk.tick(eng)
    assert kid["secret"]["kind"] == "feeling" and not kid.get("secret_due"), "one secret at a time"
    # a drive changes once, in the reflection, after a betrayal
    opinions.move(h, cfg, kid, p0["id"], "lied_to_me", "%s lied to me" % label(p0))
    assert drives.shaken(h, cfg, kid, h["tick"]) == "%s lied to me" % label(p0)
    assert drives.reconsider(h, cfg, kid, "I am for keeping the little ones safe, now") == "to keep the family safe" and kid["drive"]["changed"]
    assert drives.shaken(h, cfg, kid, h["tick"]) == "" and drives.reconsider(h, cfg, kid, "to be left alone") is None, "once a life"
    m = eng.minds[kid["id"]]
    kid["drive"] = K.drive({"name": "to be remembered"})
    text, ctx = brain4.reflect_packet(m)
    assert ctx["shaken"] and "what you are for may not be what it was" in text and "you keep something to yourself: I love" in text, text[-800:]
    print("character: drive, flaw and voice at hatching; the planner, the one, a secret, a drive changed once")
    return eng


async def migration(d):
    eng, p0 = await M.house(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][p0["room"]]
    hobs = [p0] + [B4.hob(eng, room, [2 + 2 * i, 4]) for i in range(3)]
    for p in hobs:
        for k in ("drive", "flaw", "voice", "secret"):
            p.pop(k, None)
    h["migrated"].pop("v42_drives", None)
    h["lies"] = [{"tick": h["tick"], "teller": hobs[1]["id"], "listener": hobs[2]["id"], "about": hobs[3]["id"], "said": -6}]
    lines = await drives.migrate(eng)
    assert len(lines) == len([p for p in h["pets"].values() if p["stage"] not in ("egg", "dead")]), lines
    for p in hobs:
        assert p["drive"]["name"] in K.DRIVES and p["flaw"]["name"] in K.FLAWS and p["voice"]["style"] in K.STYLES, p["id"]
    assert hobs[1]["secret"]["kind"] == "lie" and not hobs[2].get("secret"), "a liar keeps a secret, the others none"
    assert any(label(hobs[1]) in l and "not true" in l for l in lines) and all(any("voice: " + w in l for w in K.STYLES.values()) for l in lines), lines
    assert await drives.migrate(eng) == [], "once a house"
    # v4.2.2 §2: a v4.2 card (register, samples) is drawn again under the eight styles, once a house, no model asked
    hobs[1]["voice"] = {"register": "terse", "returns_to": "x", "overuses": "first", "samples": ["a", "b", "c"]}
    h["migrated"].pop("v422_voice", None)
    again = drives.restyle(h, cfg)
    assert set(hobs[1]["voice"]) == {"style", "cares"} and any(label(hobs[1]) + ": " + hobs[1]["voice"]["style"] in l for l in again), again
    assert drives.restyle(h, cfg) == [], "once a house"
    for l in lines:
        print("  " + l)
    print("migration: every living hob has a drive, a flaw and a voice, and the liar a secret; once")


async def talking(d):
    eng, p0 = await M.house(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][p0["room"]]
    a, b = p0, B4.hob(eng, room, [3, 3])
    b["name"] = "Wen"
    cfg["talk"]["lie_found"] = 0.0   # (the secret stays kept until it is let out below)
    memories.remember(h, cfg, a, "Wen and I found a feather by the pond", 3, "found")
    drives.keep_secret(h, cfg, a, "broken", "I broke the blue cup and hid the pieces", b["id"])
    # the packet and the schema
    subj = talk.subject(h, cfg, a, b, talk.rnd(h, "s"))
    assert "feather" in subj, subj
    packet, shape = talk.packet2(h, cfg, a, b, subj), talk.schema2(h, cfg, a, b)
    assert len(packet) <= cfg["talk"]["packet_most"] and "What's between them right now: %s." % subj in packet and "Wen and I found" not in subj, (subj, packet)
    assert "a secret it won't tell: I broke the blue cup" in packet and "- talks: " in packet, packet
    assert list(shape["properties"])[0] == "minds" and "minds" in shape["required"] and shape["properties"]["lines"]["minItems"] == cfg["talk2"]["lines"][0]
    rep = talk.stub_reply2(h, cfg, a, b, talk.rnd(h, "x"), subj)
    assert talk.valid(rep, shape), json.dumps(rep)[:400]
    # a talk through the engine: a subject, each side's minds (the secret in what it holds), and they become memories
    rec = await talk_once(eng, a, b)
    assert rec["subject"] and set(rec["minds"]) == {label(a), "Wen"} and "I broke the blue cup" in rec["minds"][label(a)]["holds"], rec
    assert cfg["talk2"]["lines"][0] <= len(rec["lines"]) <= cfg["talk2"]["lines"][1]
    assert any(m["kind"] == "knows" and b["id"] in m["about"] for m in a["memories"]) and any(m["kind"] == "knows" and a["id"] in m["about"] for m in b["memories"])
    assert K.since(h, "knows", rec["tick"]), "the ledger has the talk's knows lines"
    assert "what it already knows of Wen" in talk.packet2(h, cfg, a, b, ""), "the next talk starts from what it knows"
    # a reply without wants/holds/knows is failed and asked again, with thinking; the second is taken in
    full = talk.stub_reply2(h, cfg, a, b, talk.rnd(h, "y"), subj)
    bare = {k: v for k, v in full.items() if k != "minds"}
    n = h.get("talks_failed", 0)
    brain = Model(bare, full)
    rec = await talk_once(eng, a, b, brain)
    assert h["talks_failed"] == n + 1 and len(brain.asked) == 2 and brain.asked[1]["think"], (h["talks_failed"], brain.asked)
    assert rec and rec["minds"]["Wen"]["knows"] == full["minds"]["Wen"]["knows"], "the retry's minds are kept"
    # ... and if the second lacks them too, the talk goes on with the defaults, counted
    brain = Model(bare, dict(bare, minds={label(a): {"wants": "", "holds": "", "knows": "", "remember": ""}}))
    rec = await talk_once(eng, a, b, brain)
    assert h["talks_failed"] == n + 2 and rec and rec["lines"] and K.since(h, "missed", rec["tick"])[-1]["kind"] == "talk", "defaulted and counted"
    assert "I broke the blue cup" in rec["minds"][label(a)]["holds"], "the secret is in what it holds, whatever the reply"
    # a secret comes out in talk (the lie mechanism, for every secret)
    cfg["talk"]["lie_found"] = 1.0
    rec = await talk_once(eng, a, b)
    assert a["secret"]["found"] is not None and any(x["kind"] == "secret found" for x in h["moments"]) and K.since(h, "secret found", rec["tick"]), a["secret"]
    assert any(m["kind"] == "secret found" and a["id"] in m["about"] for m in b["memories"])
    # a gossip lie, told and unseen, is the teller's secret
    c = B4.hob(eng, room, [5, 5])
    say, opinions.say = opinions.say, lambda *x: (-6, False)
    try:
        talk.effect(h, cfg, "gossip", b, a, c, "", {"came_of": []}, lambda *x: None, [], set(), talk.rnd(h, "g"))
    finally:
        opinions.say = say
    assert b["secret"]["kind"] == "lie" and b["secret"]["about"] == a["id"] and label(c) in b["secret"]["text"] and not b["secret"]["found"], b.get("secret")
    # §7.6 a hatchling learns a word a day from whoever talks to it
    baby = B4.hob(eng, room, [6, 6], stage="hatchling")
    rec = await talk_once(eng, a, baby)
    assert len(baby.get("learned_words", [])) == 1 and baby["word_day"] == h["clock"]["day"], (baby.get("learned_words"), rec["lines"])
    await talk_once(eng, a, baby)
    assert len(baby["learned_words"]) == 1, "one a day"
    print("talk: a subject and each side's minds, kept as memories; a reply without them failed and asked again; a secret out; a word learned")
    print('  e.g. %s' % " / ".join('%s: "%s"' % (label(h["pets"][x["who"]]), x["text"]) for x in h["talks"][-3]["lines"]))


def switches(d):
    """[drives] and [talk2] each off (spirit on): their data never appears over a stub day; on, it does."""
    h, pets, _ = asyncio.run(M.stub_day(d + "/on"))
    assert all(p.get("drive") and p.get("flaw") and p.get("voice") for p in pets), "on: every hob has its character"
    talks = h.get("talks", [])
    assert all("minds" in t and "subject" in t for t in talks), "on: every talk has its subtext"
    h, pets, _ = asyncio.run(M.stub_day(d + "/d", drives=False))
    assert not any(k in p for p in pets for k in ("drive", "flaw", "voice", "secret", "voice_due", "for_drive", "secret_due")), "[drives] off: no character"
    h, pets, _ = asyncio.run(M.stub_day(d + "/t", talk2=False))
    assert not any("minds" in t or "subject" in t for t in h.get("talks", [])), "[talk2] off: v4.0.6's talks"
    assert not any(m.get("kind") in ("knows", "subtext") for p in pets for m in p.get("memories", [])) and not any("learned_words" in p for p in pets)
    print("switches: [drives] and [talk2] each off leave their data unchanged (%d talks with subtext when on)" % len(talks))


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        asyncio.run(character(d + "/c"))
        asyncio.run(migration(d + "/m"))
        asyncio.run(talking(d + "/t"))
        switches(d + "/s")
    print("check_spirit_talk: all passed")


if __name__ == "__main__":
    main()
