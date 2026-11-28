"""SPEC-v4.2 §0.1 items 1-2: the shapes are total (any input, never a raise, defaults filled), the new reply fields are
required in the schemas, the one gate is the only gate, every closed list is covered by every table that consumes it,
and each merged helper's module offers what contracts.API says it does.

A table's coverage is checked once its helper is merged (contracts.BUILT); `--all` checks every one (check_spirit
and the lead's last run). A name added without its consumers fails here, not in the night.

    uv run python -m engine.check_contracts [--all]
"""
import importlib
import re
import sys
from pathlib import Path

from . import contracts as K
from .talk import valid

ROOT = Path(__file__).resolve().parent.parent
JUNK = [None, 0, 3.5, "", "x" * 999, [], [1, 2], {}, {"name": 7}, {"text": None, "weight": "9"}, {"name": "avoid_place"},
        {"name": "avoid_place", "arg": "the cellar"}, {"kind": "react", "about": [None, "p1"], "what": [None, "Clay"]}, True]


def shapes():
    """Every record maker takes anything and gives its whole shape back."""
    makers = {K.memory: ("text", "tick", "weight", "about", "where", "what", "kind", "by"), K.happening: ("name", "target", "why", "day", "hard"),
              K.tale: ("id", "family", "about", "name", "cause", "words", "last_words", "self_line", "hook", "tick", "told"),
              K.drive: ("name", "target", "since", "changed"), K.flaw: ("name", "asked"), K.voice: ("style", "cares"),
              K.secret: ("kind", "text", "about", "tick", "found"), K.self_page: K.SELF}
    for f, keys in makers.items():
        for x in JUNK:
            out = f(x)
            assert isinstance(out, dict) and set(keys) <= set(out), "%s(%r) has its whole shape" % (f.__name__, x)
    for x in JUNK:
        h = K.hook(x)
        assert h is None or (h["name"] in K.HOOKS and h["arg"]), "hook(%r) is a hook or None" % (x,)
        b = K.belief_extra({"id": "b", "statement": "s", "hook": x})
        assert {"hook", "truth", "doubted", "tested", "acted"} <= set(b)
    assert K.hook({"name": "avoid_place", "arg": "the cellar"}) == {"name": "avoid_place", "arg": "the cellar", "when": ""}
    assert K.hook({"name": "none", "arg": "x"}) is None, "the model's none is no hook"
    assert K.memory({"kind": "talk", "text": "a", "by": "model"})["by"] == "model" and K.memory({"kind": "talk", "text": "a"})["by"] == "engine", "the writer says who wrote it"
    assert K.memory({"weight": 9})["weight"] == 5 and K.memory({"weight": -2})["weight"] == 1
    assert K.happening({"name": "storm"})["hard"] and not K.happening({"name": "dream"})["hard"] and K.happening({"name": "flood"})["name"] == "nothing"
    assert K.self_page(["a", "b", "c", "d", "e"])["what I fear"] == "d"
    for f, keys in ((K.item, ("id", "kind", "parts", "verbs", "tier", "class", "state", "owner", "maker", "made", "quality", "name", "heirloom", "star", "where")),
                    (K.deficit, ("id", "kind", "where", "who", "urgency", "fixers", "since", "closed", "by")),
                    (K.job, ("id", "deficit", "kind", "steps", "taker", "since", "touched", "state")), (K.board, ("deficits", "jobs", "closed", "tick"))):
        for x in JUNK + [{"state": 5, "where": "r00", "verbs": {"fly": 1, "cut": 9}, "steps": [{"do": "fly"}, {"do": "use", "verb": "cut"}]}]:
            out = f(x)
            assert isinstance(out, dict) and set(keys) <= set(out), "v5: %s(%r) has its whole shape" % (f.__name__, x)
    it = K.item({"verbs": {"light": 0.8, "fly": 1}, "state": {"charge": {"oil": 0}}})
    assert it["verbs"] == {"light": 0.8} and K.works(it, "light") == 0 and K.works(dict(it, state={"charge": {"oil": 2}}), "light") == 0.8
    assert K.works({"verbs": {"cut": 0.7}, "state": {"broken": True}}, "cut") == 0, "a broken thing does nothing"
    assert K.item({"where": {"in": "i9", "room": "r00"}})["where"] == {"in": "i9"} and K.item({"material": "reed", "n": 3})["n"] == 3
    assert K.deficit({"kind": "cold", "where": "r21"})["id"] == "cold|r21|" and K.deficit({"kind": "cold", "urgency": 9})["urgency"] == 4
    h = {"clock": {"day": 3}}
    K.count(h, "verbs", "light", 2)
    assert K.counts(h)["verbs"] == {"light": 2} and set(K.counts(h)) == set(K.COUNTS + K.COUNTS51 + K.COUNTS53)
    for f, keys in ((K.part, ("name", "verbs", "needs", "with", "materials", "tier", "role", "icon", "draw", "wear", "words")),
                    (K.material, ("name", "tier", "source", "from", "at", "class", "quality")),
                    (K.recipe, ("key", "kind", "parts", "charge", "tier", "verbs", "by", "how", "for", "tick", "sprite")),
                    (K.parsed, ("ok", "verbs", "tier", "wear", "unmet", "refusal", "words", "part", "material")),
                    (K.knowledge, ("since", "from", "of", "by")), (K.read, ("tick", "question", "title", "text", "links", "source", "chain", "kinds"))):
        for x in JUNK + [{"verbs": {"fly": 1, "cut": 9}, "needs": {"cut": ["handle", ["wire", "cell"]], "fly": ["x"]}, "tier": 9, "from": "taught by Ada", "links": list("abcdefg")}]:
            out = f(x)
            assert isinstance(out, dict) and set(keys) <= set(out), "v5.1: %s(%r) has its whole shape" % (f.__name__, x)
    assert K.part({"needs": {"light": [["wire", "cell"], "flame"]}})["needs"]["light"] == [("wire", "cell"), ("flame",)]
    assert K.parts_of(["flame of oil", {"part": "Shade", "material": "glass"}, "junk", 3]) == [{"part": "flame", "material": "oil"}, {"part": "shade", "material": "glass"}]
    assert K.knowledge({"from": "taught by Pansy"})["from"] == "taught" and K.knowledge({"from": "inherited"})["from"] == "told" and K.knowledge({"from": "read"})["of"]
    assert not K.parsed({"verbs": {"cut": 0.5}, "refusal": "tier", "words": "x"})["ok"] and K.parsed({"verbs": {"cut": 0.5}})["ok"] and not K.parsed({})["ok"]
    assert K.read({"links": list("abcdefg")})["links"] == list("abcde")
    assert K.invent({"name": "none", "parts": [{"part": "tube"}]}) is None and K.invent({"name": "x", "parts": []}) is None and K.invent(None) is None
    assert K.invent({"name": "pebble thrower", "parts": [{"part": "tube", "material": "wood"}], "charge": "none"})["charge"] is None
    assert K.item({"tier": 3})["tier"] == 3 and K.item({"tier": 9})["tier"] == 4
    K.count(h, "invent", "proposed")
    assert K.counts(h)["invent"] == {"proposed": 1} and set(K.COUNTS51) <= set(K.counts(h))
    assert K.voice_line({"style": "grumbly", "cares": "the book"}) == K.STYLES["grumbly"] + "; cares about the book"
    assert set(K.voice({"register": "terse", "samples": ["x"]})) == {"style", "cares"}, "v4.2.2 §2: style and cares and nothing else"
    for f, keys in ((K.habit, ("name", "verb", "target", "place", "pace", "from", "why", "since", "count", "last", "fading")),
                    (K.mark, ("id", "kind", "by", "room", "pos", "what", "item", "n", "tick", "last", "seen", "found", "gone", "words")),
                    (K.project, ("id", "goal", "kind", "build", "site", "steps", "stock", "owners", "names", "progress", "since", "touched", "state", "why", "steps_by", "fixture")),
                    (K.site, ("id", "kind", "room", "tiles", "name", "project", "stage", "since", "decay")),
                    (K.thread, ("with", "subject", "question", "by", "tick", "picked"))):
        for x in JUNK + [{"place": {"room": "r00", "pos": (1, 2)}, "pos": [1], "steps": [{"do": "fly"}, {"do": "gather", "what": "reed", "n": 12}], "stock": {"reed": "3"},
                          "tiles": [[1, 2], [3]], "owners": ["p1", None], "names": ["p0"], "kind": "zz"}]:
            out = f(x)
            assert isinstance(out, dict) and set(keys) <= set(out), "v5.3: %s(%r) has its whole shape" % (f.__name__, x)
    pj = K.project({"owners": ["p1"], "names": ["p0"], "steps": [{"do": "clear", "done": True}, {"do": "gather", "what": "reed", "n": 12}, {"do": "fly"}]})
    assert pj["names"] == ["p0", "p1"] and len(pj["steps"]) == 2 and pj["progress"] == 0.5 and pj["state"] == "planned", "v5.3 §2.4: the names it has had; progress from its steps"
    assert K.habit({"name": "collect", "verb": "carry", "place": {"room": "r00", "pos": (1, 2)}})["place"] == {"room": "r00", "pos": [1, 2]} and K.habit("zz")["name"] == K.HABITS[0]
    assert K.proposal({"kind": "none"}) is None and K.proposal({"kind": "build"}) is None and K.proposal({"kind": "shelter", "why": "quiet"})["goal"] == "quiet"
    assert K.go_on({"go_on": {"Ada": {"go_on": "yes", "why": "the box"}}}, ["Ada", "Bo"]) == {"Ada": {"go_on": "yes", "why": "the box"}, "Bo": {"go_on": "no", "why": ""}}, "a side missing says no"
    h53 = {"tick": 5, "clock": {"day": 1}}
    K.event53(h53, "praise", pet="p1", to="p2", pride=0.1)
    assert K.events53(h53, "praise") == [{"pet": "p1", "to": "p2", "pride": 0.1, "tick": 5}] and K.events53(h53, "taken") == []
    K.count(h53, "rounds", 3)
    assert K.counts(h53)["rounds"] == {"3": 1} and set(K.COUNTS53) <= set(K.counts(h53))
    print("contracts: every shape is total")


def schemas():
    """The new fields are required in each schema, and a reply that has them keeps to it; defaults() fills every one."""
    base = lambda: {"type": "object", "properties": {"thought": {"type": "string"}}, "required": ["thought"], "additionalProperties": False}
    for kind, args in (("react", ()), ("talk", (["Ada", "Bo"],)), ("reflect", (True, True)), ("plan", ())):
        s = K.add_fields(base(), K.FIELDS[kind](*args))
        assert set(K.FIELDS[kind](*args)) <= set(s["required"]), "%s: the new fields are required" % kind
    s = K.add_fields(base(), K.reflect_fields())
    good = {"thought": "", "remember": ["the clay is in the storeroom"], "learned": {"text": "the pond is cold", "hook": {"name": "avoid_place", "arg": "pond room", "when": ""}},
            "self": {k.replace(" ", "_"): "line" for k in K.SELF}, "visitor": "the visitor feeds us"}
    assert valid(good, s), "a reflect reply with the new fields keeps to its schema"
    assert not valid({"thought": ""}, s), "a reflect reply without them does not"
    t = K.add_fields(base(), K.talk_fields(["Ada", "Bo"]))
    side = {"wants": "w", "holds": "h", "knows": "k", "remember": ""}
    assert valid({"thought": "", "minds": {"Ada": side, "Bo": side}}, t) and not valid({"thought": "", "minds": {"Ada": side}}, t)
    for kind in ("react", "reflect", "talk", "plan"):
        for x in JUNK + [{"remember": 5, "self": "x", "learned": 3, "minds": []}]:
            r, missed = K.defaults(kind, x if not isinstance(x, dict) else dict(x), names=["Ada", "Bo"], old_self=["old"] * 5, old_theory="it feeds us")
            if isinstance(x, dict):
                if kind == "react":
                    assert isinstance(r["remember"], str)
                if kind == "reflect":
                    assert isinstance(r["remember"], list) and set(r["self"]) == set(K.SELF) and isinstance(r["learned"], dict) and r["visitor"]
                if kind == "talk":
                    assert set(r["minds"]) == {"Ada", "Bo"}
    r, missed = K.defaults("reflect", {"learned": "a sentence", "self": {"who_I_am": "new"}}, old_self=["a", "b", "c", "d", "e"], old_theory="t")
    assert r["learned"] == {"text": "a sentence", "hook": None} and r["self"]["who I am"] == "new" and r["self"]["what I fear"] == "d", "a line left out stays as it was"
    assert "remember" in missed and "visitor" in missed and r["visitor"] == "t"
    inv = K.invent_schema(["tube", "spring", "handle"], ["wood", "metal", "pebble"])
    good = {"name": "pebble thrower", "for": "the beetles", "parts": [{"part": "tube", "material": "wood"}, {"part": "spring", "material": "metal"}], "charge": "pebble",
            "how": "a wooden tube with a metal spring behind it throws pebbles"}
    assert valid(good, inv) and not valid(dict(good, parts=[{"part": "wing", "material": "wood"}]), inv) and not valid(dict(good, charge=None), inv), "v5.1 §4.2: invent is constrained"
    g = K.add_fields(base(), K.talk_round_fields(["Ada", "Bo"]))
    assert valid({"thought": "", "go_on": {"Ada": {"go_on": "yes", "why": "w"}, "Bo": {"go_on": "no", "why": "done"}}}, g) and not valid({"thought": "", "go_on": {"Ada": {"go_on": "maybe", "why": "w"}}}, g), "v5.3 §5.1"
    ps = K.project_schema()
    assert valid({"kind": "shelter", "site": "by the willow", "why": "quiet", "goal": "a shelter"}, ps) and valid({"kind": "none", "site": "", "why": "", "goal": ""}, ps) and not valid({"kind": "build", "site": "", "why": "", "goal": ""}, ps)
    print("contracts: the new fields are required, and defaulted where a reply lacks them")


def one_gate():
    """No module reads a v4.2 part's `on` but through contracts.on (so [spirit] off reaches every one)."""
    bad = []
    pat = re.compile(r"""cfg(?:\.get\(|\[)["'](%s)["'](?:\s*,\s*\{\})?[\])]+\s*(?:\.get\(|\[)["']on["']""" % "|".join(K.PARTS + ("spirit",)))
    for f in sorted((ROOT / "engine").rglob("*.py")):
        if f.name in ("contracts.py", "check_contracts.py") or f.name.startswith("check_"):
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if pat.search(line):
                bad.append("%s:%d" % (f.relative_to(ROOT), i))
    assert not bad, "a v4.2 part's switch read past contracts.on: %s" % bad
    pat = re.compile(r"""cfg(?:\.get\(|\[)["'](%s)["'](?:\s*,\s*\{\})?[\])]+\s*(?:\.get\(|\[)["']on["']""" % "|".join(K.PARTS5 + ("v5",)))
    bad = ["%s:%d" % (f.relative_to(ROOT), i) for f in sorted((ROOT / "engine").rglob("*.py")) if f.name != "contracts.py" and not f.name.startswith("check_")
           for i, line in enumerate(f.read_text().splitlines(), 1) if pat.search(line)]
    assert not bad, "a v5 part's switch read past contracts.on5: %s" % bad
    pat = re.compile(r"""cfg(?:\.get\(|\[)["'](%s)["'](?:\s*,\s*\{\})?[\])]+\s*(?:\.get\(|\[)["']on["']""" % "|".join(K.PARTS51))
    bad = ["%s:%d" % (f.relative_to(ROOT), i) for f in sorted((ROOT / "engine").rglob("*.py")) if f.name != "contracts.py" and not f.name.startswith("check_")
           for i, line in enumerate(f.read_text().splitlines(), 1) if pat.search(line)]
    assert not bad, "a v5.1 part's switch read past contracts.on51: %s" % bad
    pat = re.compile(r"""cfg(?:\.get\(|\[)["'](%s)["'](?:\s*,\s*\{\})?[\])]+\s*(?:\.get\(|\[)["']on["']""" % "|".join(K.PARTS53))
    bad = ["%s:%d" % (f.relative_to(ROOT), i) for f in sorted((ROOT / "engine").rglob("*.py")) if f.name != "contracts.py" and not f.name.startswith("check_")
           for i, line in enumerate(f.read_text().splitlines(), 1) if pat.search(line)]
    assert not bad, "a v5.3 part's switch read past contracts.on53: %s" % bad
    print("contracts: every v4.2 switch is read through contracts.on, every v5 one through on5, every v5.1 one through on51, every v5.3 one through on53")


def ts_has(path, names, where):
    """Each name appears as a quoted key or string in a view source file."""
    text = (ROOT / path).read_text() if (ROOT / path).exists() else ""
    return {n for n in names if re.search(r"""["'`]%s["'`]|\b%s\s*:""" % (re.escape(n), re.escape(n).replace(" ", "_")), text)}


def coverage(all_):
    """(helper, what, the names it must cover, what it covers): each consumer of a closed list."""
    from . import body, machines, world
    cfg = world.load_config()
    T = [("lead", "the body's carry table covers every machine process (KeyError: 'mill')", machines.processes(cfg), lambda: set(body.TO))]

    def mod(name):
        try:
            return importlib.import_module(name)
        except ImportError:
            return None

    attr = lambda m, a: (lambda: set(getattr(mod(m), a, {}) or {}))
    T += [("B", "planner.AIM covers every aim kind (4,802 dropped intentions)", set(K.AIM_KINDS), attr("engine.planner", "AIM")),
          ("B", "brain4.DAY says every new aim kind in words", set(K.AIMS_NEW), attr("engine.brain4", "DAY")),
          ("B", "hooks.SCORE scores every hook", set(K.HOOKS), attr("engine.hooks", "SCORE")),
          ("A", "life.CAUSE_WORDS words every cause of death", set(K.CAUSES), attr("engine.life", "CAUSE_WORDS")),
          ("A", "health.FEEL words every stage of sickness", set(K.SICK), attr("engine.health", "FEEL")),
          ("A", "health.FORESHADOW shows every cause but old age before it can happen", set(K.CAUSES) - {"old age", "killing"}, attr("engine.health", "FORESHADOW")),
          ("C", "drives.SERVES scores every drive", set(K.DRIVES), attr("engine.drives", "SERVES")),
          ("C", "drives.FLAW_SCORE scores every flaw", set(K.FLAWS), attr("engine.drives", "FLAW_SCORE")),
          ("D", "stage.EFFECTS lands every happening", set(K.HAPPENINGS), attr("engine.stage", "EFFECTS")),
          ("D", "visitor.TOOLS has every tool", set(K.VISITOR_TOOLS), attr("engine.visitor", "TOOLS")),
          ("E", "the Lab's cause table covers every cause", set(K.CAUSES), attr("engine.lab4", "CAUSES")),
          ("E", "the Lab reads every line of the ledger", set(K.LEDGER), lambda: ts_has("engine/lab4.py", K.LEDGER, "ledger")),
          ("E", "the view's banner table covers every v4.2 moment", set(K.MOMENTS), lambda: ts_has("view/src/banner.ts", K.MOMENTS, "banner")),
          ("E", "the view's decline table covers every stage of sickness", set(K.SICK), lambda: ts_has("view/src/pet.ts", K.SICK, "decline") | ts_has("view/src/px/actors.ts", K.SICK, "decline")),
          ("E", "the view's visitor panel has every tool", set(K.VISITOR_TOOLS), lambda: ts_has("view/src/visitorpanel.ts", K.VISITOR_TOOLS, "tools"))]
    # SPEC-v5.0 (the lead's kinds.toml, then A, B, C)
    import tomllib
    KT = tomllib.loads((ROOT / "kinds.toml").read_text())
    ents = list(KT["kind"].values()) + list(KT["fixture"].values())
    T += [("lead", "kinds.toml has every kind (§1.3)", set(cfg["kinds"]), lambda: set(KT["kind"])),
          ("lead", "kinds.toml's verbs are verbs", {v for e in ents for v in e.get("verbs", {})}, lambda: set(K.VERBS)),
          ("lead", "kinds.toml's classes are classes", {e.get("class", "plain") for e in ents}, lambda: set(K.CLASSES)),
          ("lead", "kinds.toml's charges are charges, each with what fills it", {c for e in ents for c in e.get("charge", {})} | set(K.CHARGES), lambda: set(KT["charge"])),
          ("lead", "kinds.toml gives every invented use its verbs", set(K.INVENTED_USES), lambda: set(KT["invented"]["use"])),
          ("lead", "the verbs a kind gives are reachable this phase", {v for e in ents for v in e.get("verbs", {})}, lambda: set(K.REACHABLE)),
          ("A5", "verbs.RESOLVE resolves every verb (§1.2)", set(K.VERBS), attr("engine.verbs", "RESOLVE")),
          ("B5", "deficits.DETECT detects every deficit (§2.1)", set(K.DEFICITS), attr("engine.deficits", "DETECT")),
          ("B5", "jobs.FIT fits a hob to every deficit (§3.2)", set(K.DEFICITS), attr("engine.jobs", "FIT")),
          ("C5", "the Lab's Jobs section has a row for every deficit", set(K.DEFICITS), lambda: ts_has("engine/lab4.py", K.DEFICITS, "jobs")),
          ("C5", "the Lab reads every v5 counter", set(K.COUNTS), lambda: ts_has("engine/lab4.py", K.COUNTS, "counts"))]
    # SPEC-v5.1 (B, C)
    T += [("B51", "planner.AIM covers every v5.1 aim kind", set(K.AIMS51), attr("engine.planner", "AIM")),
          ("B51", "book.ASK asks a question from every source (§6.3)", set(K.QUESTIONS) - {"own"}, attr("engine.book", "ASK")),
          ("C51", "brain4.DAY says every v5.1 aim kind in words", set(K.AIMS51), attr("engine.brain4", "DAY")),
          ("C51", "the Lab reads every v5.1 counter", set(K.COUNTS51), lambda: ts_has("engine/lab4.py", K.COUNTS51, "counts"))]
    # SPEC-v5.3 (the lead's habits.toml and projects.toml, then A, B, C)
    HT, PT = tomllib.loads(K.HABIT_FILE.read_text()), tomllib.loads(K.PROJECT_FILE.read_text())
    keys = {k for h in HT["habit"].values() for k in list(h.get("weight", {})) + h.get("need", [])}
    axes = {a + s for a in ("brave", "tidy", "generous", "curious", "social", "honest", "patient", "playful", "ambitious", "kind") for s in "+-"}
    good = axes | {"base", "drive:unmet", "stage:grieving", "belief:hook"} | {"flaw:" + f for f in K.FLAWS} | {"drive:" + d for d in K.DRIVES} | {"style:" + x for x in K.STYLES} | {"stage:" + x for x in K.STAGES}
    steps = {str(x).split(":")[0] for e in PT["kind"].values() for x in e["steps"]}
    T += [("lead", "habits.toml has every habit template (§1.2)", set(K.HABITS), lambda: set(HT["habit"])),
          ("lead", "habits.toml's draw keys are traits, flaws, drives, styles and stages", keys, lambda: good),
          ("lead", "habits.toml's marks are marks and its verbs verbs", {h["leaves"] for h in HT["habit"].values() if h["leaves"]} | {h["verb"] for h in HT["habit"].values() if h["verb"]}, lambda: set(K.MARKS) | set(K.VERBS)),
          ("lead", "habits.toml's bit classes are bits", {b for bs in HT["class"].values() for b in bs}, lambda: set(tomllib.loads((ROOT / "house.toml").read_text())["bits"])),
          ("lead", "projects.toml has every project kind (§2.2)", set(K.PROJECT_KINDS), lambda: set(PT["kind"])),
          ("lead", "projects.toml's steps are steps the body can do", steps, lambda: set(K.PROJECT_STEPS)),
          ("lead", "projects.toml's drives are drives, its verbs verbs, its sites sites", {d for e in PT["kind"].values() for d in e["drives"]} | {v for e in PT["kind"].values() for v in e["becomes"] if v != "sleep"} | {e["site"] for e in PT["kind"].values()},
           lambda: set(K.DRIVES) | set(K.VERBS) | set(K.SITE_KINDS)),
          ("A53", "projects.STEP does every project step (§2.1)", set(K.PROJECT_STEPS), attr("engine.projects", "STEP")),
          ("A53", "the view draws every project kind's site at every stage (§2.3)", set(K.PROJECT_KINDS) | set(K.SITE_STAGES), lambda: ts_has("view/src/sites.ts", set(K.PROJECT_KINDS) | set(K.SITE_STAGES), "sites")),
          ("B53", "habits.ACT gives every habit a planner activity (§1.2)", set(K.HABITS), attr("engine.habits", "ACT")),
          ("B53", "habits.SEEN gives every habit a perception line (§1.3)", set(K.HABITS), attr("engine.habits", "SEEN")),
          ("B53", "the view draws every mark that stands (§1.4)", {"pile", "hoard", "mark"}, lambda: ts_has("view/src/sites.ts", ("pile", "hoard", "mark"), "marks")),
          ("C53", "talk.SUBJECT53 draws a subject from every source (§5.5)", set(K.SUBJECTS53), attr("engine.talk", "SUBJECT53")),
          ("C53", "the Lab reads every v5.3 counter and event (§8)", set(K.COUNTS53) | set(K.EVENTS53), lambda: ts_has("engine/lab4.py", set(K.COUNTS53) | set(K.EVENTS53), "life")),
          ("C53", "the Lab shows every scene (§6, §8)", set(K.SCENES), lambda: ts_has("engine/lab4.py", K.SCENES, "scenes"))]
    n = 0
    for who, what, need, have in T:
        if who.endswith("53"):
            if not all_ and who[0] not in K.BUILT53:
                continue
        elif who.endswith("51"):
            if not all_ and who[0] not in K.BUILT51:
                continue
        elif who.endswith("5") and not all_ and who[0] not in K.BUILT5:
            continue
        elif who != "lead" and not who.endswith("5") and not all_ and who not in K.BUILT:
            continue
        missing = sorted(set(need) - have())
        assert not missing, "%s: missing %s" % (what, missing)
        n += 1
    print("contracts: %d consumer tables cover their lists (%s)" % (n, "all" if all_ else "the merged helpers': %s" % (sorted(K.BUILT) or "none yet")))


def api(all_):
    n = 0
    for who, mods in K.API.items():
        if not all_ and who not in K.BUILT:
            continue
        for m, fns in mods.items():
            mod = importlib.import_module(m)
            for f in fns:
                assert callable(getattr(mod, f, None)), "helper %s: %s.%s is there (%s)" % (who, m, f, fns[f])
                n += 1
    for who, mods in K.API5.items():
        if not all_ and who not in K.BUILT5:
            continue
        for m, fns in mods.items():
            mod = importlib.import_module(m)
            for f in fns:
                assert getattr(mod, f, None) is not None, "v5 helper %s: %s.%s is there (%s)" % (who, m, f, fns[f])
                n += 1
    for who, mods in K.API51.items():
        if not all_ and who not in K.BUILT51:
            continue
        for m, fns in mods.items():
            mod = importlib.import_module(m)
            for f in fns:
                assert getattr(mod, f, None) is not None, "v5.1 helper %s: %s.%s is there (%s)" % (who, m, f, fns[f])
                n += 1
    for who, mods in K.API53.items():
        if not all_ and who not in K.BUILT53:
            continue
        for m, fns in mods.items():
            mod = importlib.import_module(m)
            for f in fns:
                assert getattr(mod, f, None) is not None, "v5.3 helper %s: %s.%s is there (%s)" % (who, m, f, fns[f])
                n += 1
    print("contracts: %d functions of the merged helpers' API are there" % n)


def lists():
    """The closed lists are what other modules already use, where they overlap."""
    from . import planner, visitor, world
    assert K.STAGES == world.STAGES
    assert set(K.AIMS_V4) == set(planner.AIM) - set(K.AIMS_NEW) - (set(K.AIMS51) - set(K.AIMS_V4)), "AIMS_V4 is v4.0's planner.AIM (a new kind goes in AIMS_NEW, or v5.1's AIMS51)"
    assert set(visitor.TOOLS) <= set(K.VISITOR_TOOLS)
    for cause in K.OLD_CAUSE.values():
        assert cause in K.DEATHS
    for x in K.OLD_SICK.values():
        assert x in K.SICK
    print("contracts: the closed lists agree with the engine's where they overlap")


def budget():
    """§3.1, §3.3 (the lead's numbers, DECISIONS Part 42): under the live profile a plan thinks "medium" in 3000 tokens,
    a reflection "medium" in 3500, a talk "low" in 3500, a reaction not at all; each at its own warmth; a thinking
    reply cut off is asked again with thinking off in the same room. With [spirit] off, v4.0.6's: none of it."""
    import asyncio
    import json
    import tempfile
    from .brains import model
    from .world import load_config
    cfg = load_config(profile="live")
    assert K.thinking(cfg, "plan") == ("medium", 3000, 0.6) and K.thinking(cfg, "reflect") == ("medium", 3500, 0.7)
    assert K.thinking(cfg, "talk") == ("none", 2000, 0.7) and K.thinking(cfg, "react") == (False, cfg["model"]["max_tokens"], 0.7)
    with tempfile.TemporaryDirectory() as d:
        brain, sent, answers = model.Model(cfg, d, {"pet": "check"}), [], []

        def post(body, timeout):
            sent.append(json.loads(json.dumps(body)))
            content, finish = answers.pop(0)
            return {"choices": [{"message": {"content": content}, "finish_reason": finish}], "usage": {"prompt_tokens": 9, "completion_tokens": 9}}
        brain.post = post
        answers[:] = [("{}", "length"), ('{"thought": ""}', "stop")]
        ctx = {"allowed": [], "aim_kinds": ["make"], "targets": [], "hobs": []}
        asyncio.run(brain.think4("plan", "a packet", ctx))
        assert (sent[0]["reasoning_effort"], sent[0]["max_tokens"], sent[0]["temperature"]) == ("medium", 3000, 0.6), sent[0]
        assert (sent[1]["reasoning_effort"], sent[1]["max_tokens"]) == ("none", 3000), "a thinking plan cut off is asked again with thinking off"
    cfg["spirit"]["on"] = False
    assert K.thinking(cfg, "talk") == (False, cfg["talk"]["max_tokens"], 0.8), "off: v4.0.6's talk"
    print("contracts: the model's budget is the lead's, and off is v4.0.6's")


def grammar(all_):
    """SPEC-v5.1 §0: every part has verbs (or says in words what it is for), materials, a tier and an icon cell; every
    material a tier and a source; every verb a part that gives it; every part a line of the grammar; every catalog kind
    and invented use a recipe of real parts of fitting materials, which (once A's parser is merged) parses to the verbs
    kinds.toml gave it in v5.0 within 0.2, but for the verbs it says v5.1 changes on purpose (`new`, `gone`)."""
    import tomllib
    raw = tomllib.loads(K.GRAMMAR_FILE.read_text())
    D = K.grammar_data()
    P, M = D["part"], D["material"]
    names = set(P) | set(M) | set(K.MAT_CLASSES) | {"charge"}
    cells = next((d for d in (ROOT / "assets-incoming/pixellab/cells", ROOT.parent / "PetProject/assets-incoming/pixellab/cells") if d.exists()), None)
    import json
    thing = json.loads((ROOT / "view/assets/parts.json").read_text())
    assert "v5_pending" not in thing, "parts.json has no pending parts: parts.toml is the registry"
    thing = thing["thing"]
    assert not sorted(n for n, p in P.items() if p["draw"] not in thing), "every part draws as a parts.json part: %s" % sorted((n, p["draw"]) for n, p in P.items() if p["draw"] not in thing)
    for n, p in P.items():
        r = raw["part"][n]
        assert "verbs" in r and set(r["verbs"]) <= set(K.VERBS), "part %s: verbs are verbs" % n
        assert p["verbs"] or p["words"], "part %s: no verbs, so its words say what it is for" % n
        assert p["materials"] and all(m in M or m in K.MAT_CLASSES for m in p["materials"]), "part %s: its materials are materials (%s)" % (n, p["materials"])
        assert isinstance(r.get("tier"), int) and 0 <= r["tier"] <= 4 and r.get("role") in K.ROLES, "part %s: a tier and a role" % n
        assert re.fullmatch(r"[a-z0-9]+/\d\d-[a-z0-9-]+", p["icon"]), "part %s: an icon cell (%r)" % (n, p["icon"])
        assert not cells or (cells / (p["icon"] + ".png")).exists(), "part %s: its icon %s is a PixelLab cell" % (n, p["icon"])
        assert set(p["needs"]) <= set(p["verbs"]) and all(x in names for alts in p["needs"].values() for a in alts for x in a), "part %s: needs name real things" % n
        assert all(o in P and all(m in M for m in ms) for o, ms in p["with"].items()), "part %s: `with` names parts and materials" % n
    for n, m in M.items():
        r = raw["material"][n]
        assert isinstance(r.get("tier"), int) and r.get("source") in K.SOURCES and r.get("class") in K.MAT_CLASSES and 0.5 <= r.get("quality", 0) <= 1, "material %s: tier, source, class, quality" % n
        assert m["source"] != "worked" or (m["from"] and m["at"]), "material %s: worked from what, where" % n
    house, craft = tomllib.loads((ROOT / "house.toml").read_text()), tomllib.loads((ROOT / "crafting.toml").read_text())
    missing = sorted((set(house["bits"]) | set(craft["material"]) | {r["gives"] for r in craft["rule"] if r.get("gives")}) - set(M))
    assert not missing, "every bit and crafted material has a tier: %s" % missing
    assert set(K.VERBS) <= {v for p in P.values() for v in p["verbs"]}, "every verb is given by a part: %s" % sorted(set(K.VERBS) - {v for p in P.values() for v in p["verbs"]})
    lined = {x for line in D["line"] for x in line["parts"]}
    assert lined <= set(P) and set(P) <= lined, "every part has a line of the grammar, and every line names parts: %s" % sorted(set(P) ^ lined)
    assert all(D["line"][i]["parts"] for i in range(len(D["line"]))) and len(K.grammar(4).splitlines()) <= 40
    assert "tube" in K.grammar(0) and "bulb" not in K.grammar(0) and "boiler" not in K.grammar(1) and "boiler" in K.grammar(2), "a hob sees its tier + 1"
    KT = tomllib.loads((ROOT / "kinds.toml").read_text())
    recs = [("kind", k, e) for k, e in KT["kind"].items()] + [("use", u, e) for u, e in KT["invented"]["use"].items()]
    for what, k, e in recs:
        ps = K.parts_of(e.get("parts"))
        assert "parts" in e and len(ps) == len(e["parts"]) and (ps or k == "design"), "%s %s: a recipe in parts" % (what, k)
        for x in ps:
            assert x["part"] in P and x["material"] in M, "%s %s: %s of %s is a part of a material" % (what, k, x["part"], x["material"])
            assert x["material"] in P[x["part"]]["materials"] or M[x["material"]]["class"] in P[x["part"]]["materials"], "%s %s: %s can be made of %s" % (what, k, x["part"], x["material"])
    n = 0
    if all_ or "A" in K.BUILT51:
        from . import grammar as G, world
        cfg = world.load_config()
        bad = []
        for what, k, e in recs:
            if not e.get("parts"):
                continue
            got = G.parse(cfg, K.parts_of(e["parts"]), charge=next(iter(e.get("charge") or {}), None))
            was, skip = e.get("verbs") or {}, set(e.get("new", [])) | set(e.get("gone", []))
            off = {v: (got["verbs"].get(v, 0), was.get(v, 0)) for v in set(got["verbs"]) | set(was) if v not in skip and abs(got["verbs"].get(v, 0) - was.get(v, 0)) > 0.2 + 1e-9}
            if off or got["refusal"]:
                bad.append("%s %s: %s %s" % (what, k, off, got["words"]))
            n += 1
        assert not bad, "the catalog parses to v5.0's verbs within 0.2: %s" % bad
    print("contracts: %d parts, %d materials, %d lines; %d recipes%s" % (len(P), len(M), len(D["line"]), len(recs),
                                                                      ", %d parsed to v5.0's verbs" % n if n else " (parsed once A is merged)"))


def main():
    all_ = "--all" in sys.argv
    shapes()
    schemas()
    lists()
    one_gate()
    coverage(all_)
    api(all_)
    grammar(all_)
    budget()
    print("check_contracts: all passed")


if __name__ == "__main__":
    main()
