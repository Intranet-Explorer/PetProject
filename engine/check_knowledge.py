"""Self-check for SPEC-v5.1 §5, §6 and §9's knowledge half (helper B): making requires knowing; study at tier - 1
gives the recipe and at tier - 2 knowing-of; a tale carries a recipe; teaching is an aim that teaches; the house's tier
rises and falls with deaths, and the page says so; a read writes a memory with tags, keeps its links, and a curious hob
reads on from one (a chain of three is a first); each of the six question sources produces a want; known_of marks a
kind; the migration's report; [knowledge] and [book2] off give v5.0's behaviour. Stub houses, no encyclopedia.
    uv run python -m engine.check_knowledge"""
import asyncio
import os
import tempfile
from pathlib import Path

from . import book, contracts as K, grammar, knowledge, planner, story, things, wants
from .check_brain4 import hob, house
from .check_machine import thing

PAGES = {"what is a millstone": ("Millstone", "A millstone is a stone used to grind grain between two stones. Millstones are made of stone.", ["Grain", "Mill (grinding)", "Stone"]),
         "grain": ("Grain", "Grain is the seed of grasses that people eat.", ["Wheat", "Seed"]),
         "wheat": ("Wheat", "Wheat is a grass grown for its grain.", ["Bread", "Flour"]),
         "lantern": ("Lantern", "A lantern is a light that can be carried, with a candle or a flame of oil under glass.", ["Candle", "Glass"])}


def on51(cfg, know=True, book2=True):
    cfg["v5"]["on"] = cfg["items"]["on"] = True
    cfg["knowledge"]["on"], cfg["book2"]["on"] = know, book2
    cfg["spirit"]["on"] = cfg["memory2"]["on"] = True


def fake_book():
    """The encyclopedia, faked: PAGES by question, their links kept as book.read keeps them."""
    def lookup(cfg, q):
        got = PAGES.get(q.lower())
        if got:
            book.LINKS[got[0]] = got[2]
        return got[:2] if got else None
    book.lookup, book.available, book.entry = lookup, lambda cfg: True, lambda cfg, q: None


def ask(eng, pet, q):
    return book.ask(eng.house, eng.cfg, pet, {"question": q}, lambda t, n: str(t)[:n])


async def making(d):
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on51(cfg)
    lantern = {"type": "make", "recipe": {"kind": "lantern", "material": "bright", "color": "blue", "size": 1, "name": "a lantern", "purpose": "light"}}
    p0["carrying"] = ["wax", "glass"]
    assert grammar.recipe(h, cfg, "lantern")["tier"] == 1 and not knowledge.can_make(h, cfg, p0, "lantern")
    assert things.check_make(lantern, h, cfg, p0) == knowledge.unknown(cfg, "lantern"), "make requires knowing"
    assert knowledge.can_make(h, cfg, p0, "bowl"), "a tier-0 kind is made by paw without knowing ([knowledge] free_tier)"
    assert knowledge.offered(h, cfg, p0, {"bright": ["lantern", "bowl"]}) == {"bright": ["bowl"]}, "and only what it knows is offered"
    p0["inventing"] = "lantern"
    assert knowledge.can_make(h, cfg, p0, "lantern"), "or what it is inventing now"
    p0.pop("inventing")
    assert knowledge.learn(h, cfg, p0, K.key_of("lantern"), "read", of=True) and not knowledge.can_make(h, cfg, p0, "lantern"), "knowing-of is not the recipe"
    assert knowledge.learn(h, cfg, p0, K.key_of("lantern"), "taught") and knowledge.can_make(h, cfg, p0, "lantern")
    assert things.check_make(lantern, h, cfg, p0) != knowledge.unknown(cfg, "lantern")
    assert not knowledge.learn(h, cfg, p0, K.key_of("lantern"), "read", of=True), "knowing-of over a recipe is nothing new"
    from . import craft
    craft.learn(h, cfg, p0, "clay|fire", "taught by Wen")
    assert knowledge.knows(h, p0, "clay|fire")["from"] == "taught", "a writer of v4's recipes learns the key too"
    print("knowledge: \"%s\"; a tier-0 kind is free, knowing-of isn't the recipe, inventing it is leave" % knowledge.unknown(cfg, "lantern"))

    # §5.3 study, through the planner's activity
    shop = next(r for r in h["rooms"].values() if r["type"] == "workshop")
    p0["room"], p0["pos"] = shop["id"], [5, 3]
    p0["knows"] = {}
    thing(eng, shop, "tin lamp", "lantern", "bright", None)
    thing(eng, shop, "old key", "key", "hard", None)["made"]["fine"] = 3
    p0["aims"] = [{"kind": "study", "text": K.AIM_WORDS51["study"], "target": None, "since": h["tick"], "done": None}]
    A, near = cfg["activities"]["study"], lambda pos: list(pos)
    got = planner.targets(h, cfg, p0, eng.minds[p0["id"]].mem, "study", A, near)
    assert got and got[0]["what"] in ("tin lamp", "old key"), got
    hour = cfg["ticks_per_hour"]
    told, ok = planner.finish(eng.minds[p0["id"]], {"what": "tin lamp", "since": h["tick"] - hour // 3}, A)
    assert ok and "turned the tin lamp over" in told and not knowledge.knows(h, p0, "kind:lantern"), "a while at it is not yet an hour"
    told, ok = planner.finish(eng.minds[p0["id"]], {"what": "tin lamp", "since": h["tick"] - hour}, A)
    k = knowledge.knows(h, p0, "kind:lantern")
    assert ok and k and not k["of"] and k["from"] == "studied" and "worked out how a lantern is made" in told, "study at tier - 1 gives the recipe: %s" % told
    assert planner.aim_done(h, cfg, p0, p0["aims"][0]), "the study aim is done"
    told, ok = planner.finish(eng.minds[p0["id"]], {"what": "old key", "since": h["tick"] - round(hour * 0.45)}, A)
    k = knowledge.knows(h, p0, "kind:key")
    assert grammar.recipe(h, cfg, "key")["tier"] == 2 and k and not k["of"], "a fine thing teaches sooner (and at tier 1 a tier-2 key is within reach): %s" % told
    p0["knows"].pop("kind:lantern")
    p0["knows"].pop("kind:key")
    thing(eng, shop, "old key 2", "key", "hard", None)
    assert knowledge.would(h, cfg, p0, shop["objects"]["old key 2"]) == "of", "at tier - 2, only that it exists"
    words, ok = knowledge.study(h, cfg, p0, "old key 2")
    assert ok and knowledge.knows(h, p0, "kind:key")["of"] and "not how to make one" in words
    assert K.counts(h)["studied"].get(p0["id"]) == 3
    print("knowledge: study at tier - 1: \"%s\"; at tier - 2: \"%s\"" % (told, words))
    return eng, p0


async def tales_and_tiers(d):
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on51(cfg)
    room = h["rooms"][p0["room"]]
    p0["knows"] = {}
    smith = hob(eng, room, [3, 3], stage="adult")
    smith["name"] = "Bram"
    smith["knows"] = {"kind:key": K.knowledge({"from": "made"}), "kind:cup": K.knowledge({"from": "made"})}   # (a metal key is tier 2: the tier is a kind's parts', each the lower of the part's and its material's)
    knowledge.tick(h, cfg)
    days = h["v5"]["tier"]
    assert days[str(h["clock"]["day"])] == 2 and knowledge.words(h, cfg) == "the house knows mechanisms", "the house's tier is its best hob's: %s" % days
    smith.update(stage="dead", cause="old age")
    knowledge.tick(h, cfg)
    assert days[str(h["clock"]["day"])] == 0 and h["v5"]["tier_fall"]["words"] == "nobody left knows the forge"
    assert knowledge.words(h, cfg) == "the house knows found things; nobody left knows the forge", knowledge.words(h, cfg)
    p0["knows"]["kind:lantern"] = K.knowledge({"from": "taught"})   # (a flame under a shade: tier 1)
    knowledge.tick(h, cfg)
    assert days[str(h["clock"]["day"])] == 1, "and rises again"
    p0["knows"]["metal|forge"] = K.knowledge({"from": "made"})
    knowledge.tick(h, cfg)
    assert days[str(h["clock"]["day"])] == 1, "a process recipe reaches no tier (21 October 2026)"
    print("knowledge: the tier rises and falls: \"%s\"" % knowledge.words(h, cfg))
    # The owner (21 October 2026): knowing-of never fades; it ends with the hob
    knowledge.learn(h, cfg, p0, "kind:kettle", "read", of=True)
    for _ in range(10):
        h["clock"]["day"] += 1
        knowledge.tick(h, cfg)
    assert knowledge.knows(h, p0, "kind:kettle")["of"], "knowing-of ten days on"
    assert not knowledge.learn(h, cfg, p0, "kind:kettle", "read", of=True) and knowledge.knows(h, p0, "kind:kettle")["of"], "read again, still knowing-of"

    # a tale carries what the dead one knew how to make
    t = story.tale(h, cfg, smith)
    knowledge.tick(h, cfg)
    assert h["tale_recipes"][t["id"]] == "kind:key" and t == K.tale(t), "the recipe nobody living knows, beside the tale (its shape kept)"
    elder = hob(eng, room, [4, 4], stage="elder")
    kid = hob(eng, room, [5, 4], stage="child")
    elder["family"] = kid["family"] = smith["family"] = p0.get("family", 1)
    did = story.tell(eng, elder)
    k = knowledge.knows(h, kid, "kind:key")
    heard = next(m["text"] for m in kid["memories"] if m["kind"] == "tale")
    assert did and "Bram knew how to make a key" in heard and k and k["from"] == "told" and k["by"] == smith["id"], "a tale carries a recipe: %s" % heard
    print("knowledge: a tale carries a recipe: \"%s\"" % heard)

    # teach: an elder whose child lacks a recipe the house uses
    elder["knows"] = {"kind:cup": K.knowledge({"from": "made"})}
    kid["parent"] = elder["id"]
    thing(eng, room, "the blue cup", "cup", "hard", elder["id"])
    h["tick"] += cfg["ticks_per_hour"] - h["tick"] % cfg["ticks_per_hour"]
    knowledge.tick(h, cfg)
    a = next(a for a in elder["aims"] if a["kind"] == "teach")
    assert a["target"] == kid["id"] and a["key"] == "kind:cup" and "teach" in planner.feasible(h, cfg, elder), a
    knowledge.done(h, cfg, elder, a)
    k = knowledge.knows(h, kid, "kind:cup")
    assert k and k["from"] == "taught" and k["by"] == elder["id"] and "kind:cup" in kid["recipes"] and K.counts(h)["taught"].get(elder["id"]) == 1
    print("knowledge: an elder's teach aim: \"%s\", and it teaches" % a["text"])


async def reading(d):
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on51(cfg)
    fake_book()
    p0["temper"]["curious"] = 1.0
    r = ask(eng, p0, "what is a millstone")
    rec = p0["read"][0]
    assert rec == K.read(rec) and rec["links"] == ["Grain", "Mill (grinding)", "Stone"] and rec["source"] == "own" and rec["chain"] == 0, rec
    m = next(m for m in p0["memories"] if m["kind"] == "read")
    assert m["weight"] == 3 and m["text"] == "I read that a millstone is a stone used to grind grain between two stones." and {"millstone", "stone"} <= set(m["what"]), m
    print("book: a read is a memory: \"%s\" %s" % (m["text"], m["what"]))
    q, key = book.next_read(h, cfg, p0)
    assert (q, key) == ("Grain", "on:Grain"), "a curious hob reads on from a link of the last passage"
    ask(eng, p0, q)
    q, _ = book.next_read(h, cfg, p0)
    ask(eng, p0, q)
    assert [x["chain"] for x in p0["read"][:3]] == [2, 1, 0] and p0["read"][0]["title"] == "Wheat"
    assert K.counts(h)["read"] == {"own": 1, "on": 2} and K.counts(h)["chain"] == {p0["id"]: 1}
    assert "chain:three" in p0["firsts"], "a chain of three is a first"
    assert book.next_read(h, cfg, p0) == (None, None), "and there it stops ([book2] chain_most)"
    p0["temper"]["curious"] = 0.0
    p0["read"].insert(0, dict(p0["read"][0], chain=0))
    assert book.next_read(h, cfg, p0) == (None, None), "one not curious doesn't read on"
    p0["drive"] = {"name": "to know everything in the book"}
    assert book.next_read(h, cfg, p0)[0] == "Bread", "unless its drive is the book"
    p0["aims"] = [{"kind": "learn", "text": "find out what a kiln is in the book", "target": None, "since": h["tick"], "done": None}]
    assert book.next_read(h, cfg, p0) == ("what a kiln is", "learn:what a kiln is"), "a learn aim's own question first"
    print("book: links kept, read on from Millstone to Grain to Wheat, a chain of three a first")

    ask(eng, p0, "lantern")
    k = knowledge.knows(h, p0, "kind:lantern")
    assert k and k["of"] and k["from"] == "read" and p0["read"][0]["kinds"] == ["lantern"] and "lantern" in book.known_of(cfg)["lantern"]
    assert "Lantern" in book.known_of(cfg) or "lantern" in book.known_of(cfg)
    print("book: known_of marks a kind: reading \"Lantern\" knows of %s" % p0["read"][0]["kinds"])

    # §6.3 the six sources, each a want of kind "word" with the engine's question
    from . import visitor
    other = hob(eng, h["rooms"][p0["room"]], [2, 2], stage="adult")
    other["family"] = p0.get("family", 1)

    def want(src):
        c = [c for c in wants.candidates(h, cfg, p0) if c["what"] == "word" and c.get("source") == src]
        assert c and c[0]["question"] and wants.question(h, cfg, p0, c[0]) == c[0]["question"], "a %s question is a want: %s" % (src, p0.get("questions"))
        p0["questions"] = []
        return c[0]["question"]
    asked = {}
    p0["questions"] = []
    w = {"what": "bit", "bit": "reed", "key": "bit:reed", "text": "x", "done": "held a reed for the first time", "since": h["tick"]}
    p0["wants"] = [w]
    wants.fulfil(h, cfg, p0, w)
    asked["material"] = want("material")
    other["cause"] = "sickness"
    book.died(h, cfg, other)
    asked["death"] = want("death")
    book.wonder(h, cfg, p0, "happening", book.HAPPENED["storm"])
    asked["happening"] = want("happening")
    p0["met"]["beetle"] = 1
    p0["words"] = [w_ for w_ in p0.get("words", []) if w_ != "beetle"]
    p0["creature_word"] = None
    wants.hear(h, cfg, p0)
    asked["first_seen"] = want("first_seen")
    cfg["picturable"] = set(cfg.get("picturable", ())) | {"kettle"}
    book.heard(h, cfg, p0, "Wen keeps a kettle by the stove")
    asked["heard"] = want("heard")
    visitor.t_answer(eng, p0, {"text": "go and find out in the book"}, {"q": "Why is the sky blue?"})
    asked["visitor"] = want("visitor")
    assert set(asked) == set(K.QUESTIONS) - {"own"} == set(book.ASK)
    print("book: six sources, six questions: %s" % asked)
    # The owner's fix (21 October 2026): a question from life is a want past the three and the day's rule, one at a time,
    # and its learn aim comes before the job's step, so it reaches a screen
    from . import planner
    most, cfg["wants"]["most"] = cfg["wants"]["most"], 0   # (the cap reached: no other want comes)
    p0["wants"], p0["wanted"] = [], {}
    p0["job_aim"] = {"kind": "job", "text": "a job", "target": None, "since": h["tick"], "done": False, "job": "j"}
    book.wonder(h, cfg, p0, "happening", "a flood")
    book.wonder(h, cfg, p0, "death", "a fever")
    wants.refresh(h, cfg, p0)
    for a_ in p0["aims"]:
        a_["ready"] = True   # (as when it knows a screen and its eyes are rested)
    life_ = [w for w in p0["wants"] if w["what"] == "word" and w.get("source") not in (None, "own")]
    assert len(life_) == 1 and len(p0["wants"]) == 1, "one life question, past the cap: %s" % [w["what"] for w in p0["wants"]]
    a = planner.current(p0)
    assert a["kind"] == "learn" and a["from"] == "question" and a["question"] == life_[0]["question"], "its learn aim before the job's step: %s" % a
    wants.refresh(h, cfg, p0)
    assert sum(1 for w in p0["wants"] if w["what"] == "word" and w.get("source") not in (None, "own")) == 1 and sum(a_.get("from") == "question" for a_ in p0["aims"]) == 1
    h["tick"] += cfg["ticks_per_day"] + 1   # (a question from life older than a world day closes, read or not)
    wants.refresh(h, cfg, p0)
    assert not any(w["what"] == "word" and w.get("question") == a["question"] for w in p0["wants"]) and a.get("failed"), ("a day on, it is let go", [(w["what"], w.get("question"), w["since"]) for w in p0["wants"]], a, h["tick"], p0.get("questions"))
    assert h["v5"]["questions51"].get("aged out", 0) >= 1 and h["v5"]["questions51"]["raised"] >= 2
    p0.pop("job_aim")
    p0["wants"], p0["aims"], p0["questions"], cfg["wants"]["most"] = [], [], [], most
    print("book: a question from life is a want past the three, its learn aim ahead of the job: %s" % a["question"])
    ask(eng, p0, "what is a millstone")


async def migration(d):
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on51(cfg)
    cfg["grammar"]["on"] = True
    h.setdefault("migrated", {}).pop("v51_knows", None)
    p0["knows"] = ["p9"]
    knowledge.mine(p0)
    assert p0["knows"] == {} and "p9" in p0["met_hobs"], "v3.1's strangers it knew move to met_hobs"
    p0["times"]["kind cup"] = 2
    p0["recipes"] = {"clay|fire": {"tick": 0, "from": "found"}, "kind:hammer": {"tick": 0, "from": "taught by Wen"}, "dish:bean soup": {"tick": 0, "from": "found"}}
    eng.items_migration()
    lines = eng.migration51k
    assert knowledge.knows(h, p0, "kind:cup")["from"] == "made" and knowledge.knows(h, p0, "kind:hammer")["from"] == "taught" and knowledge.knows(h, p0, "clay|fire")
    assert not knowledge.knows(h, p0, "dish:bean soup"), "a dish is v4's alone"
    assert lines[0] == "knowledge: the house's tier is 0 (the house knows found things)" and any("tier 0: 3 recipes" in l for l in lines), lines   # (a cup and a hammer are tier-0 parts; clay|fire reaches nothing)
    assert "SPEC-v5.1 migration (knowledge)" in (Path(eng.dir) / "migration-v5.1.txt").read_text()
    eng.items_migration()
    assert eng.migration51k == [], "once a house"
    for l in lines:
        print("knowledge: migration: %s" % l)


async def off(d):
    """[knowledge] and [book2] off: v5.0's behaviour (anyone makes anything; the book as v4's)."""
    eng, p0 = await house(d)
    h, cfg = eng.house, eng.cfg
    on51(cfg, know=False, book2=False)
    fake_book()
    p0["temper"]["curious"] = 1.0
    assert knowledge.can_make(h, cfg, p0, "lantern") and knowledge.offered(h, cfg, p0, {"x": ["lantern"]}) == {"x": ["lantern"]}
    assert not knowledge.learn(h, cfg, p0, "kind:cup", "made") and knowledge.migrate(h, cfg) == []
    knowledge.tick(h, cfg)
    assert "tier" not in h.get("v5", {}) and not {"teach", "study"} & set(planner.feasible(h, cfg, p0))
    ask(eng, p0, "what is a millstone")
    assert set(p0["read"][0]) == {"tick", "question", "title", "text"} and not any(m["kind"] == "read" for m in p0.get("memories", []))
    assert book.wonder(h, cfg, p0, "death", "old age") is None and book.next_read(h, cfg, p0) == (None, None)
    for _ in range(300):
        await eng.tick()
    assert not any(isinstance(p.get("knows"), dict) and p["knows"] or p.get("questions") or p.get("study") for p in h["pets"].values()), "nothing of it"
    assert "tier" not in h.get("v5", {}) and "tale_recipes" not in h
    print("knowledge: [knowledge] and [book2] off: anyone makes anything, reads are v4's, no questions, no tiers (300 stub ticks)")


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        lookup, available, entry = book.lookup, book.available, book.entry
        try:
            asyncio.run(making(d + "/m"))
            asyncio.run(tales_and_tiers(d + "/t"))
            asyncio.run(reading(d + "/r"))
            asyncio.run(migration(d + "/g"))
            asyncio.run(off(d + "/o"))
        finally:
            book.lookup, book.available, book.entry = lookup, available, entry
    print("check_knowledge: all passed")


if __name__ == "__main__":
    main()
