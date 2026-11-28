"""Self-check for SPEC-v4.0 §10 (helper B): every visitor tool works and is remembered (a memory, the hob's opinion of
the visitor moved for a cause, the log the panel shows, a moment for the story); talking is one call of kind
"visitor" and its answer comes back over the state; answers become beliefs; doubters come round when spoken to or
when they see a gift appear; hobs in hard times ask for help; and with [visitor4] off the tools do nothing and the
old toolbar still works.
    uv run python -m engine.check_visitor"""
import asyncio
import os
import tempfile

import engine.tick  # noqa: F401  (first, as when any module is run alone)
from . import actions, conflict, store, talk, visitor
from .check_machine import thing
from .check_talk import CALLS, house_of, killing, record, settle, temper
from .world import generate_room


def remembered(pid, cause, kind="visitor"):
    return any(x[0] == pid and "visitor" in x[3] for x in CALLS["mem"]) and (pid, "visitor", cause) in CALLS["move"]


async def run(d):
    record()
    eng, (a, b, c) = await house_of(d + "/v")
    h, cfg = eng.house, eng.cfg
    a["name"], b["name"], c["name"] = "Ada", "Bram", "Cole"
    use = lambda tool, **body: visitor.use(eng, tool, body)

    # ---- talk: one call of kind "visitor"; the answer comes back, is said, and is remembered ----
    ok, said = use("talk", pet=a["id"], text="Well done, Ada, that cup is lovely")
    assert ok and "listening" in said, said
    assert h["visitor"]["log"][-1] == {"tick": h["tick"], "tool": "talk", "pet": a["id"], "text": "Well done, Ada, that cup is lovely", "said": None}
    for _ in range(3):
        await asyncio.sleep(0)
        await eng.tick()
    x = h["visitor"]["log"][-1]
    assert x["said"] and a["said"]["to"] == "visitor" and a["said"]["text"] == x["said"], x
    assert remembered(a["id"], "talked_kindly"), "kind words warm it"
    assert eng.db.execute("SELECT count(*) FROM calls WHERE kind='visitor'").fetchone()[0] == 1
    use("talk", pet=b["id"], text="you are useless and lazy")
    for _ in range(3):
        await asyncio.sleep(0)
        await eng.tick()
    assert remembered(b["id"], "talked_harshly"), "harsh words hurt"
    assert not use("talk", pet=a["id"], text="   ")[0] and not use("talk", pet="p999", text="hi")[0]
    a["sleep"] = {"since": h["tick"], "day": 1, "done": False}
    assert not use("talk", pet=a["id"], text="hi")[0], "a sleeping hob doesn't answer"
    a["sleep"] = None
    S = visitor.reply_schema()
    assert talk.valid(visitor.stub_answer(a, "hello"), S) and not talk.valid({"says": "x"}, S)

    # ---- answer: a question in the inbox; the answer becomes a belief it holds ----
    c["believes"] = True
    q = visitor.ask(h, cfg, c, "What is beyond the meadow?")
    assert q and visitor.ask(h, cfg, c, "And the stars?") is None, "one waiting question a hob"
    ok, _ = use("answer", n=q["n"], text="The woods, and a river.")
    assert ok and q["answer"] == "The woods, and a river." and remembered(c["id"], "told_me")
    assert any("The woods, and a river." in bl["statement"] and bl["source"] == "told by the visitor" for bl in eng.minds[c["id"]].mem.active())
    assert not use("answer", n=q["n"], text="again")[0], "answered once"
    assert visitor.ask(h, cfg, c, "what is beyond the meadow") is None and visitor.ask(h, cfg, c, "What is beyond the meadow, then?") is None, \
        "(19 October 2026) not the same question again within a world day, answered or not"
    h["tick"] += talk.hours(cfg, 24)
    q2 = visitor.ask(h, cfg, c, "What is beyond the meadow?")
    assert q2 and visitor.ask(h, cfg, a, "What is beyond the meadow?"), "a day on, or another hob, it may"
    for x in (q2, h["visitor"]["inbox"][-1]):
        x["answer"] = "the woods"

    # ---- teach: a recipe, a skill, or a hint; learned freely ----
    key = "kind:" + sorted(cfg["craft"]["needs"])[0]
    assert use("teach", pet=b["id"], what=key)[0] and key in b["recipes"] and remembered(b["id"], "taught_me")
    assert not use("teach", pet=b["id"], what=key)[0], "it knows that already"
    use("teach", pet=b["id"], what="music")
    assert b["skill"]["music"] >= cfg["visitor4"]["teach_skill"] and talk.memories.skill(b, "music") > 0
    use("teach", pet=b["id"], what="clay goes hard in the kiln")
    assert any("clay goes hard" in bl["statement"] for bl in eng.minds[b["id"]].mem.active())

    # ---- praise and scold: pride, the deed more or less likely, and a greedy prickly one resents it ----
    a["needs"]["pride"] = 50.0
    use("praise", pet=a["id"], about="the cup")
    assert a["praised"]["the cup"] == 1 and a["needs"]["pride"] > 50 and remembered(a["id"], "praised_me")
    temper(b, kind=-1, generous=-1)
    use("scold", pet=b["id"], about="taking the fish")
    assert b["praised"]["taking the fish"] == -1 and remembered(b["id"], "scolded_me")
    assert any(x[0] == b["id"] and "wasn't fair" in x[1] for x in CALLS["mem"]), "it resents you"
    for i in range(25):   # (19 October 2026) what it was praised for: the last twenty
        visitor.praise_scold(eng, a, {"about": "deed %d" % i}, True)
    assert len(a["praised"]) == 20 and "the cup" not in a["praised"] and list(a["praised"])[-1] == "deed 24", a["praised"]

    # ---- give: a bit into its paws with a sparkle; a thing from the store; a doubter sees it and believes ----
    a["carrying"], c["believes"] = [], False
    assert use("give", pet=a["id"], what="berry")[0] and a["carrying"] == ["berry"] and h["bursts"][-1]["kind"] == "sparkle"
    assert remembered(a["id"], "gift") and c["believes"], "something only you could do, seen"
    if not h["rooms"][store.RID]["type"]:
        generate_room(h, cfg, store.RID, "storeroom")
    store.lay(h, cfg)
    src = h["rooms"][store.RID]
    thing(eng, src, "blue cup", "cup", "hard", None)
    store.put(h, cfg, src, "blue cup", src["objects"]["blue cup"])
    if store.find(h, cfg, "blue cup"):
        assert use("give", pet=a["id"], what="blue cup")[0] and "blue cup" in h["rooms"][a["room"]]["objects"] and "blue cup" not in src["objects"]
        assert h["rooms"][a["room"]]["objects"]["blue cup"]["made"]["owner"] == a["id"]
    assert not use("give", pet=a["id"], what="moon")[0]

    # ---- suggest: for the morning plan, with its trust in you ----
    assert use("suggest", pet=c["id"], text="fire the kiln")[0] and c["suggested"][-1]["text"] == "fire the kiln" and "trust" in c["suggested"][-1]
    assert remembered(c["id"], "spoke_to")

    # ---- step in: protect for a day, stop a fight, judge; the whole house remembers ----
    assert use("stepin", pet=c["id"], how="protect")[0] and h["visitor"]["protect"][c["id"]] > h["tick"] and remembered(c["id"], "protected_me")
    assert not use("stepin", pet=a["id"], how="stop")[0], "no fight to stop"
    sc = conflict.force(h, cfg, a["id"], b["id"], 5)
    assert use("stepin", pet=a["id"], how="stop")[0] and sc["stopped"] == "visitor", "they freeze and back off"
    assert remembered(b["id"], "stepped_in") and remembered(a["id"], "stepped_in")
    assert not use("stepin", pet=b["id"], how="shun")[0], "no killer to judge"
    killing(eng, b, (c,))
    n = len(CALLS["mem"])
    assert use("stepin", pet=b["id"], how="shun")[0] and b["shunned"] == h["tick"] and (b["id"], "visitor", "scolded_me") in CALLS["move"]
    assert {x[0] for x in CALLS["mem"][n:]} >= {a["id"], b["id"], c["id"]}, "the whole house remembers"
    assert any(m["kind"] == "justice" for m in h["moments"])
    assert use("stepin", pet=b["id"], how="pardon")[0] and not b["shunned"] and (b["id"], "visitor", "stepped_in") in CALLS["move"]
    assert not use("stepin", pet=b["id"], how="smite")[0]
    h["tick"] += talk.hours(cfg, cfg["visitor4"]["protect_hours"]) + 1
    visitor.tick(eng)
    assert c["id"] not in h["visitor"]["protect"], "protection lasts a day"

    # ---- SPEC-v5.3.2 §1: place and remove: any kind of thing, the visitor's, with its kind's verbs ----
    room = h["rooms"][a["room"]]
    a["sleep"] = None
    ok, said = use("place", room=room["id"], pos=[3, 3], kind="lantern")
    assert ok, said
    mine = [(n, o) for n, o in room["objects"].items() if o.get("made", {}).get("by") == "visitor"]
    assert len(mine) == 1, "one thing placed, and it is the visitor's: %s" % mine
    name, o = mine[0]
    assert o["pos"] == [3, 3] and o["made"]["owner"] == "visitor", "it stands on the tile he clicked: %s" % o
    assert o["item"]["verbs"], "a placed thing has its kind's verbs: %s" % o.get("item")
    assert any("appeared" in e[1] and "who put it there" in e[1] for e in a["events"]), "the hobs awake are told: %s" % a["events"][-2:]
    assert not use("place", room=room["id"], pos=[3, 4], kind="unobtainium")[0], "a kind that is not in kinds.toml is refused"
    ok, said = use("remove", room=room["id"], name=name)
    assert ok and name not in room["objects"], said
    assert any("took it away" in e[1] for e in a["events"]), "they are told it went: %s" % a["events"][-2:]
    use("place", room=room["id"], pos=[4, 4], kind="cup")
    his = next(n for n, o in room["objects"].items() if o.get("made", {}).get("by") == "visitor")
    room["objects"][his]["made"]["owner"] = a["id"]   # (he gave it away: he placed it, so he can still take it back)
    assert use("remove", room=room["id"], name=his)[0], "what the visitor placed is his to take back, even as a gift"
    hers = [(r["id"], n, o) for r in h["rooms"].values() if r["type"] for n, o in r["objects"].items()
            if "made" in o and o["made"].get("by") != "visitor"]
    if hers:   # (a thing a hob made is not his to take away)
        assert not use("remove", room=hers[0][0], name=hers[0][1])[0], "%s is a hob's, not the visitor's" % hers[0][1]
    assert not use("remove", room=room["id"], name="no such thing")[0], "what is not there is refused in words"

    # ---- every tool left a line in the log the panel shows ----
    assert {x["tool"] for x in h["visitor"]["log"]} == set(visitor.TOOLS) - set(visitor.TOOLS5), {x["tool"] for x in h["visitor"]["log"]}   # (SPEC-v4.2's tend and remedy: check_stage)
    assert all(set(x) == {"tick", "tool", "pet", "text", "said"} for x in h["visitor"]["log"])
    sec = visitor.section(eng, a["id"])
    assert sec["log"] and sec["believes"] is True and "skills" in sec["can_teach"]

    # ---- belief in the visitor (§10.1): the cautious and the sly may doubt; spoken to, they believe ----
    for p in (a, b, c):
        p.pop("believes", None)
    temper(c, curious=-1, honest=-1)
    temper(a, curious=1, honest=1)
    cfg["visitor4"]["doubt"] = 1.0
    h["tick"] += 10 - h["tick"] % 10
    visitor.tick(eng)
    assert c["believes"] is False and a["believes"] is True, (c["believes"], a["believes"])
    assert visitor.ask(h, cfg, c, "Is anyone there?") is None, "a doubter asks you nothing"
    for i in range(30):   # a believer it trusts may bring it round in talk
        c.setdefault("opinions", {})[a["id"]] = dict(talk.opinions.of(c, a["id"]), trust=9)
        visitor.spread(h, cfg, a, c, talk.rnd(h, "spread", i))
        if c["believes"]:
            break
    assert c["believes"], "doubt fades in talk"
    c["believes"], a["believes"] = False, True   # (19 October 2026) and spreads, to one the visitor has never dealt with, whatever else it remembers
    a["memories"] = [{"tick": h["tick"], "text": "a day by the river %s" % ("x" * i), "weight": 3, "about": [b["id"]], "kind": ""} for i in range(10)]
    for i in range(30):
        a.setdefault("opinions", {})[c["id"]] = dict(talk.opinions.of(a, c["id"]), trust=10)
        c["opinions"][a["id"]] = dict(talk.opinions.of(c, a["id"]), trust=0)
        visitor.spread(h, cfg, c, a, talk.rnd(h, "doubt", i))
        if a["believes"] is False:
            break
    assert a["believes"] is False, "doubt spreads"
    a["believes"], c["believes"] = True, True
    c["believes"] = False
    use("talk", pet=c["id"], text="I am here")
    assert c["believes"] is True, "spoken to, it believes"
    for _ in range(2):   # (its answer comes back)
        await asyncio.sleep(0)
        await eng.tick()

    # ---- 19 October 2026: a lasting limp alone is no hard time (it pleaded "I'm hurt" every day for life) ----
    b.update(hurt={"level": None, "since": 0, "lasting": "limp", "left": 0}, sick=None, believes=True, sleep=None)
    b["needs"].update(hunger=80.0, comfort=80.0)
    h["tick"] += 10 - h["tick"] % 10
    visitor.tick(eng)
    assert not [x for x in h["visitor"]["inbox"] if x["pet"] == b["id"] and x["kind"] == "help"] and "hurt" not in visitor.plea(b), "a limp pleads nothing"
    assert "in hard times" not in talk.on_mind(h, cfg, b, a), "and is no hard time on its mind"
    b["hurt"] = None

    # ---- hard times: a hob that believes asks for help, in its own voice, once a day at most ----
    a["needs"]["hunger"] = 10.0
    h["tick"] += 10 - h["tick"] % 10
    visitor.tick(eng)
    pleas = [x for x in h["visitor"]["inbox"] if x["pet"] == a["id"] and x["kind"] == "help"]
    assert len(pleas) == 1 and "hungry" in pleas[0]["q"], pleas
    h["tick"] += 10
    visitor.tick(eng)
    assert len([x for x in h["visitor"]["inbox"] if x["pet"] == a["id"] and x["kind"] == "help"]) == 1
    # ---- 19 October 2026 (a dead hob's questions could not be answered): a question goes with the hob who asked it ----
    plea = pleas[0]
    a["stage"] = "dead"
    visitor.tick(eng)
    assert plea.get("gone") and visitor.use(eng, "answer", {"n": plea["n"], "text": "yes"})[0] is False, "a dead hob's question is closed"
    a["stage"] = "adult"
    # ---- 19 October 2026: what the visitor said just before a restart is asked again, once, and answered ----
    a["sleep"] = None
    use("talk", pet=a["id"], text="hello again")
    eng.visitor_calls.clear()   # (a restart: the thought in flight is lost)
    entry = h["visitor"]["log"][-1]
    for _ in range(3):
        visitor.tick(eng)
        await asyncio.sleep(0)
        await eng.tick()
    assert entry.get("again") and entry["said"], "the lost answer was asked again, and came: %s" % entry
    return eng


async def off(d):
    """[visitor4] off: the tools say so and change nothing; no house state; the old toolbar still works."""
    eng, (a, b, c) = await house_of(d + "/off", visitor4=False)
    h, cfg = eng.house, eng.cfg
    for tool in visitor.TOOLS:
        ok, said = visitor.use(eng, tool, {"pet": a["id"], "text": "hello", "what": "berry", "how": "protect", "n": 1})
        assert not ok and "off" in said
    for _ in range(30):
        await eng.tick()
    assert "visitor" not in h and "believes" not in a and not any("visitor" in m.get("about", []) for p in (a, b, c) for m in p.get("memories", [])), \
        "nothing of the visitor's tools runs"
    assert actions.visit(h, cfg, {"room": a["room"], "type": "talk", "text": "hello"}) is None and any("hello" in x for x in a["inbox"]), "the old toolbar"
    await settle(eng)


async def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:   # (anywhere: PET_SCRATCH when set, else the system's)
        await settle(await run(d))
        print("the visitor's tools: talk, answer, teach, praise, scold, give, suggest, step in; belief; hard times: ok")
        await off(d)
        print("[visitor4] off: the old toolbar only: ok")


if __name__ == "__main__":
    asyncio.run(main())
    print("check_visitor passed")
