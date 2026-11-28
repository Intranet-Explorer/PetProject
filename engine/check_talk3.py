"""Self-check for SPEC-v5.3 §5 and §7 (helper C), on stub houses with v5.3 on: a talk runs three rounds (each round
asked with the lines so far and what each now knows), leaves a thread on both that the next meeting takes as its
subject and picks up; the stub sometimes goes on and now and then to three; a hob with an urgent job says no; a
subject is never the same twice running between two hobs; a third hob listening has a line a round and its minds; the
stage rule (a child takes a gather job, a youngling a job of urgency 4, never nursing); a gather aim damps leisure and
is let go when its bit lies nowhere it knows; only a hob that could lay names an egg; [talk3] off is v5.1's talk.
    uv run python -m engine.check_talk3"""
import asyncio
import os
import tempfile

import engine.tick  # noqa: F401  (first, as when any module is run alone)
from . import contracts as K
from . import jobs, planner, scenes, talk
from .check_brain4 import hob, house
from .check_spirit_talk import Model


def v53(cfg, on=True):
    for part in ("v5", "items", "spirit", "memory2", "talk2", "jobs", "deficits"):
        cfg[part]["on"] = True
    cfg["talk3"]["on"] = on


async def pair(d, on=True):
    eng, a = await house(d)
    v53(eng.cfg, on)
    eng.cfg["talk3"]["third"] = 0.0
    b = hob(eng, eng.house["rooms"][a["room"]], [3, 3])
    a["name"], b["name"] = "Antonia", "Brody"
    return eng, a, b


async def once(eng, a, b, brain=None):
    """One conversation from a to b through talk.start and talk.apply. Returns (what start kept, the record)."""
    m = eng.minds[a["id"]]
    real, m.brain = m.brain, brain or m.brain
    for p in eng.house["pets"].values():
        p["talking"] = None
    try:
        talk.start(eng, a, b, talk.rnd(eng.house, "check", eng.house["tick"], a["id"]))
        t = eng.talking.pop()
        return t, talk.apply(eng, t, await t["fut"])
    finally:
        m.brain = real


def reply(go_a, go_b, n=1, why="I want to know where the box went"):
    side = lambda k: {"wants": "to be heard", "holds": "nothing much", "knows": "the other has been to the meadow %d" % k, "remember": ""}
    return {"minds": {"Antonia": side(n), "Brody": side(n)},
            "lines": ["Round %d, line %d: the frame by the willow is up, and it took two trips for reed." % (n, i) for i in range(4)],
            "came_of": [{"what": "news", "by": "Antonia", "about": "", "detail": ""}],
            "after": {"Antonia": {"mood": "content", "toward": "same"}, "Brody": {"mood": "content", "toward": "same"}},
            "ask_visitor": {"who": "", "q": ""},
            "go_on": {"Antonia": {"go_on": go_a, "why": why}, "Brody": {"go_on": go_b, "why": "I've said what I had to" if go_b == "no" else why}}}


async def rounds(d):
    """§5.1, §5.2: three rounds through the model's path, a thread left on both, picked up at the next meeting."""
    eng, a, b = await pair(d)
    h = eng.house
    m = Model(reply("yes", "yes", 1), reply("yes", "yes", 2), reply("yes", "no", 3))
    t, rec = await once(eng, a, b, m)
    assert rec and len(rec["rounds"]) == 3 and [len(x) for x in rec["rounds"]] == [4, 4, 4] and len(rec["lines"]) == 12, rec
    assert [x["who"] for x in rec["lines"]][3:6] == [b["id"], a["id"], b["id"]], "turns go on from round to round"
    assert len(m.asked) == 3 and "go_on" in m.asked[0]["schema"]["properties"] and "Example 5" in m.asked[0]["prompt"]
    assert "So far they have said:" in m.asked[1]["prompt"] and "Round 1, line 3" in m.asked[1]["prompt"] and "the other has been to the meadow 1" in m.asked[1]["prompt"]
    assert "Round 2, line 0" in m.asked[2]["prompt"], "each round is asked with the lines so far"
    assert rec["go_on"][-1]["Brody"]["go_on"] == "no" and rec["third"] is None
    th = rec["thread"]
    assert th and th["by"] == a["id"] and th["question"] == "I want to know where the box went", th
    assert talk.threads(h, a, b) and talk.threads(h, b, a) and talk.threads(h, b)[0]["with"] == a["id"], "the thread is on both"
    assert any(x.get("kind") == "thread" and "where the box went" in x["text"] for x in a["memories"]), "a thread is a memory with content"
    assert [x["n"] for x in K.events53(h, "round")] == [2, 3] and K.counts(h)["rounds"] == {"3": 1} and K.counts(h)["threads"] == {"left": 1}
    assert any("the other has been to the meadow 3" in x["text"] for x in b["memories"]), "what each came to know in a later round is kept"
    assert "wants to talk more about %s" % th["subject"] in talk.on_mind(h, eng.cfg, a, b), "it is on the mind of the one who wanted more"
    h["tick"] += 50
    m2 = Model(reply("no", "no"))
    t2, rec2 = await once(eng, a, b, m2)
    assert rec2["subject"] == th["subject"] and "they left this open: Antonia wanted to go on (I want to know where the box went)" in m2.asked[0]["prompt"], m2.asked[0]["prompt"][-900:]
    assert not talk.threads(h, a) and not talk.threads(h, b) and rec2["thread"] is None and len(rec2["rounds"]) == 1, "picked up, and left closed"
    assert K.counts(h)["threads"] == {"left": 1, "picked": 1} and scenes.thread(h), "the rehearsal's scene is found"
    # a hob with an urgent job (urgency 4) says no whatever the reply says
    dd = K.deficit({"kind": "leak", "where": a["room"], "urgency": 4})
    jobs.board(h)["deficits"].append(dd)
    jobs.board(h)["jobs"].append(dict(K.job({"id": "j", "deficit": dd["id"], "kind": "leak", "steps": [{"do": "use", "where": a["room"]}], "taker": a["id"], "state": "taken"})))
    assert talk.go_on(h, eng.cfg, reply("yes", "yes"), a, b)["Antonia"] == {"go_on": "no", "why": "I've something urgent to see to"}
    assert talk.go_on(h, eng.cfg, {}, a, b)["Brody"]["go_on"] == "no", "a reply with no go_on goes no further"
    # a round costs each a quarter-hour of its day: talk.tick holds them talking till then
    jobs.board(h)["jobs"].clear()
    for p in h["pets"].values():
        p["talking"] = None
    real, eng.minds[a["id"]].brain = eng.minds[a["id"]].brain, Model(reply("yes", "yes", 1), reply("yes", "no", 2))
    talk.start(eng, a, b, talk.rnd(h, "check", h["tick"], a["id"]))
    await eng.talking[-1]["fut"]
    eng.minds[a["id"]].brain, t0 = real, eng.talking[-1]["tick"]
    talk.tick(eng)
    assert a["talking"]["until"] == t0 + 2 * talk.hours(eng.cfg, eng.cfg["talk3"]["round_hours"]) and not talk.free(eng, a), a["talking"]


async def stub(d):
    """The stub goes on sometimes, now and then to three; a subject is never the same twice running between two hobs
    (but a thread picked up); habits, projects and perceptions are subjects in plain words."""
    eng, a, b = await pair(d)
    h = eng.house
    a["habits"] = [K.habit({"name": "praise", "target": b["id"]})]
    b["habits"] = [K.habit({"name": "tend", "target": "plots"})]
    h.setdefault("v5", {})["projects"] = {"p1": K.project({"id": "p1", "kind": "shelter", "owners": [a["id"]], "state": "under way"})}
    h["v5"]["marks"] = {"m1": K.mark({"id": "m1", "kind": "moved", "by": "nobody", "room": a["room"], "words": "the small hammer is not where it was", "seen": [b["id"]]})}
    subs = talk.subject(h, eng.cfg, a, b, talk.rnd(h, "x"))
    got = {k: f(h, eng.cfg, a, b) for k, f in talk.SUBJECT53.items()}
    assert set(got) == set(K.SUBJECTS53) and subs
    assert got["habit"] == ["Antonia praising everyone's work", "Brody tending the plots"] and got["project"] == ["Antonia's shelter"], got
    assert got["perception"] == ["the small hammer is not where it was"], got
    seq, n = [], {1: 0, 2: 0, 3: 0}
    for i in range(60):
        h["tick"] += 7
        t, rec = await once(eng, a, b)
        assert rec, "the stub's talk is in shape"
        n[len(rec["rounds"])] += 1
        seq.append((rec["subject"], bool(t.get("thread"))))
    assert n[1] and n[2] and n[3], n
    for (s0, _), (s1, picked) in zip(seq, seq[1:]):
        assert s1 != s0 or not s1 or picked, "the same subject twice running: %s" % s1
    assert sum(p for _, p in seq) and K.counts(h)["threads"].get("picked"), "a thread is picked up in the stub's talks too"
    assert sum(1 for x in K.events53(h, "round") if x["n"] == 3) == n[3]


async def third(d):
    """§5.4 a third hob awake in the room listens, with one line a round, and its minds (three-way knows)."""
    eng, a, b = await pair(d)
    h, cfg = eng.house, eng.cfg
    c = hob(eng, h["rooms"][a["room"]], [4, 4])
    c["name"] = "Cai"
    cfg["talk3"]["third"] = 1.0
    t, rec = await once(eng, a, b)
    assert rec["third"] == c["id"] and t["third_name"] == "Cai", rec
    mine = [x for x in rec["lines"] if x["who"] == c["id"]]
    assert len(mine) == len(rec["rounds"]) and all(x[-1]["who"] == c["id"] for x in rec["rounds"]), "one line a round, the listener's"
    assert "Cai" in rec["minds"] and K.counts(h)["third"] == {c["id"]: len(mine)} and K.events53(h, "third")[0]["pet"] == c["id"]
    assert any(x.get("kind") == "knows" and a["id"] in x.get("about", []) for x in c["memories"]), "the listener came to know something"
    assert "Cai is in the room too, listening" in talk.packet2(h, cfg, a, b, "", c) and "third_line" in talk.schema2(h, cfg, a, b, c)["properties"]


async def stages(d):
    """§7: a child takes a gather job (and a mess job), never making or mending; a youngling any job but nursing, even
    an urgent one; a hatchling none. With [jobs] stages off, v5.0's rule."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    v53(cfg)
    room = h["rooms"][p0["room"]]
    kid, young, baby = hob(eng, room, [2, 3], stage="child"), hob(eng, room, [3, 3], stage="youngling"), hob(eng, room, [4, 3], stage="hatchling")
    B = jobs.board(h)
    for k, u in (("works_goal", 3), ("mess", 4)):
        dd = K.deficit({"kind": k, "where": room["id"], "urgency": u})
        B["deficits"].append(dd)
        B["jobs"].append(jobs.plan(h, cfg, dd))
    gather, mess = B["jobs"]
    assert gather and [s["do"] for s in gather["steps"]] == ["gather", "gather", "gather", "use"] and mess
    leak = K.job({"id": "leak#1", "deficit": "leak||", "kind": "leak", "steps": [{"do": "gather", "what": "wax", "where": room["id"]}, {"do": "use", "where": room["id"]}]})
    sick = K.job({"id": "sick#1", "deficit": "sick_untended||x", "kind": "sick_untended", "steps": [{"do": "use"}]})
    assert jobs.free_hob(h, cfg, kid) and not jobs.free_hob(h, cfg, baby)
    assert jobs.may(h, cfg, kid, gather) and jobs.may(h, cfg, kid, mess) and not jobs.may(h, cfg, kid, leak) and not jobs.may(h, cfg, baby, gather)
    assert jobs.may(h, cfg, young, mess) and jobs.may(h, cfg, young, leak) and not jobs.may(h, cfg, young, sick)
    assert jobs.take(h, cfg, kid, gather) and gather["taker"] == kid["id"] and kid["job_aim"]["kind"] == "gather", "a child takes a gather job"
    assert jobs.take(h, cfg, young, mess) and mess["taker"] == young["id"], "a youngling takes an urgent job"
    cfg["jobs"]["stages"] = False
    assert not jobs.free_hob(h, cfg, kid) and not jobs.may(h, cfg, kid, gather) and not jobs.may(h, cfg, young, mess), "off: v5.0's rule"


async def gathering(d):
    """§7: a hob with a gather aim doesn't sit: the leisure set damped to [jobs] leisure while it is open; a bit that
    lies nowhere it knows lets the aim go, blocked, in words; one it can reach stays."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    v53(cfg)
    p0["job_fit"] = False
    p0["aims"] = [{"kind": "gather", "text": "gather some seed", "target": "seed", "since": h["tick"], "done": None, "why": ""}]
    A = cfg["activities"]["sit on"]
    assert jobs.weigh(h, cfg, p0, "sit on", A, {}, 1.0) == 1.0 - (1 - cfg["jobs"]["leisure"]), "the leisure set damped"
    assert jobs.weigh(h, cfg, p0, "gather", A, {}, 1.0) == 1.0
    jobs.release(h, cfg, p0)
    assert not p0["aims"][0].get("failed"), "seed lies in the garden it knows: the aim stays"
    L = {"rooms": set(), "gather": set(), "look": set()}
    planner.lean(h, cfg, p0, L)
    assert "seed" in L["gather"], "the plan's gather aim leads to its bit"
    p0["aims"] = [{"kind": "gather", "text": "gather some glass", "target": "glass", "since": h["tick"], "done": None, "why": ""}]
    jobs.release(h, cfg, p0)
    a = p0["aims"][0]
    assert a["failed"] == h["tick"] and a["blocked"] == "there's no glass in the rooms you know" and any("let it go for now" in e for _, e in p0["events"]), a
    cfg["jobs"]["stages"] = False
    p0["aims"] = [{"kind": "gather", "text": "gather some seed", "target": "seed", "since": h["tick"], "done": None, "why": ""}]
    assert jobs.weigh(h, cfg, p0, "sit on", A, {}, 1.0) == 1.0, "off: v5.1's leisure"


async def eggs(d):
    """§7 (v4.2.2's leftover): with v5.3 on only a hob that could lay names an egg, its own or one that is nobody's; off,
    any hob in the room may name a nobody's egg, as before."""
    from . import actions, life, names
    from .world import new_pet
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    v53(cfg)
    room = h["rooms"][p0["room"]]
    egg = new_pet(h, cfg, room["id"], [5, 5])
    egg.update(parent=None, name=None)
    kid = hob(eng, room, [2, 3], stage="child")
    p0["eggs"] = 0
    assert "egg" in actions.nameable(h, p0, cfg) and names.wanted(h, cfg, p0) == "your egg"
    assert "egg" not in actions.nameable(h, kid, cfg), "a child can't lay, and names no egg"
    p0["eggs"] = life.fertility(p0)
    assert "egg" not in actions.nameable(h, p0, cfg) and names.wanted(h, cfg, p0) is None, "nor one with no egg left in it"
    cfg["talk3"]["on"] = cfg["habits"]["on"] = cfg["projects"]["on"] = False
    assert "egg" in actions.nameable(h, kid, cfg) and names.wanted(h, cfg, p0) == "the egg that is nobody's", "off: as before"


async def off(d):
    """[talk3] off: v5.1's talk, its record, its prompt and its schema; no threads, no rounds."""
    eng, a, b = await pair(d, on=False)
    t, rec = await once(eng, a, b)
    assert set(rec) == {"n", "tick", "room", "a", "b", "lines", "came_of", "after", "did", "subject", "minds"}, set(rec)
    assert "go_on" not in t["schema"]["properties"] and "third" not in t and not a.get("threads") and not K.events53(eng.house, "round")
    assert "Example 5" not in talk.packet2(eng.house, eng.cfg, a, b, "") and "Short lines, most under fifteen words." in talk.TALK
    assert "Example 5" in talk.TALK53 and "two or three sentences" in talk.TALK53


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        for name, fn in (("rounds", rounds), ("stub", stub), ("third", third), ("stages", stages), ("gathering", gathering), ("eggs", eggs), ("off", off)):
            asyncio.run(fn("%s/%s" % (d, name)))
            print("  %s ok" % name)
    print("check_talk3: all passed")


if __name__ == "__main__":
    main()
