"""SPEC-v5.3 §6: the five scenarios (and the orphan and the thread), found in the plain facts the modules record
(contracts.event53), never written as rules. The lead's: the rehearsal's gate and the Lab's counters.

find(house) -> {scene: [what happened, in words]}; missing(house) -> {scene: the first ingredient that never
happened, in words}: for a scene that did not occur, which rule was missing.
"""
from . import contracts as K


def _ev(house, what, since):
    return K.events53(house, what, since)


def _name(house, pid):
    p = house["pets"].get(pid) or {}
    return p.get("name") or pid or "?"


def _drive(house, pid):
    d = (house["pets"].get(pid) or {}).get("drive")
    return K.drive(d)["name"] if d else ""


def _habits(house, pid):
    return {K.habit(h)["name"] for h in (house["pets"].get(pid) or {}).get("habits") or []}


def _kin(house, a, b):
    """Parent, child or sibling (a shared parent)."""
    pa, pb = house["pets"].get(a) or {}, house["pets"].get(b) or {}
    par = lambda p: {x for x in (p.get("parents") or [p.get("parent")]) if x}
    return a in par(pb) or b in par(pa) or bool(par(pa) & par(pb))


def _day(house):
    return house.get("ticks_per_day") or 1800


def pile(house, since=0):
    """§6.1 a collect pile another hob counts as mess, moves, and is resented for by its owner."""
    out = []
    moved = _ev(house, "moved", since)
    resent = _ev(house, "resent", since)
    for m in _ev(house, "mess", since):
        mv = next((x for x in moved if x["pet"] == m["pet"] and x.get("owner") == m.get("owner") and x["tick"] >= m["tick"]), None)
        if not mv:
            continue
        r = next((x for x in resent if x["pet"] == m.get("owner") and x.get("against") == m["pet"] and x["tick"] >= mv["tick"]), None)
        if r:
            out.append("%s counted %s's pile as mess and moved it; %s resented it (%s)" % (_name(house, m["pet"]), _name(house, m["owner"]), _name(house, m["owner"]), r.get("cause")))
    return out


def hoard(house, since=0):
    """§6.2 a take habit builds a hoard that is found, and opinions of it fall."""
    out = []
    thieves = {x["pet"] for x in _ev(house, "taken", since)}
    ops = _ev(house, "opinion", since) + [dict(x, about=x.get("against")) for x in _ev(house, "resent", since)]
    for f in _ev(house, "found", since):
        t = f.get("owner")
        if t not in thieves:
            continue
        fell = [x for x in ops if x.get("about") == t and x["tick"] >= f["tick"] and (x.get("delta") is None or x["delta"] < 0)]
        if fell:
            out.append("%s found %s's hoard; %d opinions of %s fell" % (_name(house, f["pet"]), _name(house, t), len(fell), _name(house, t)))
    return out


def shelter(house, since=0):
    """§6.3 a hob with to leave or to be left alone builds a shelter outdoors over several days, sleeps there, and comes
    in for food."""
    out, day = [], _day(house)
    projects = (house.get("v5") or {}).get("projects") or {}
    steps = _ev(house, "step", since)
    for d in _ev(house, "project", since):
        if d.get("kind") != "shelter" or d.get("state") != "done":
            continue
        owners = d.get("owners") or (K.project(projects.get(d.get("project"))).get("owners") if d.get("project") in projects else [])
        for o in owners:
            if _drive(house, o) not in ("to leave the house", "to be left alone"):
                continue
            days = {x["tick"] // day for x in steps if x.get("project") == d.get("project")}
            slept = next((x for x in _ev(house, "slept_out", since) if x["pet"] == o), None)
            came = slept and next((x for x in _ev(house, "came_in", since) if x["pet"] == o and x["tick"] >= slept["tick"]), None)
            if len(days) >= 2 and slept and came:
                out.append("%s built a shelter over %d days, slept there, and came in for %s" % (_name(house, o), len(days), came.get("why") or "food"))
    return out


def praise(house, since=0):
    """§6.4 praise raises another's pride, and an envious hob resents it (within a world day)."""
    out, day = [], _day(house)
    resent = _ev(house, "resent", since)
    for p in _ev(house, "praise", since):
        if not (p.get("pride") or 0) > 0:
            continue
        r = next((x for x in resent if x["pet"] not in (p["pet"],) and x.get("against") in (p["pet"], p.get("to")) and p["tick"] <= x["tick"] <= p["tick"] + day), None)
        if r:
            out.append("%s praised %s; %s resented it (%s)" % (_name(house, p["pet"]), _name(house, p.get("to")), _name(house, r["pet"]), r.get("cause")))
    return out


def joint(house, since=0):
    """§6.5 two keep-company hobs finish a joint project and bond."""
    out = []
    projects = (house.get("v5") or {}).get("projects") or {}
    bonds = _ev(house, "bond", since)
    for d in _ev(house, "project", since):
        owners = d.get("owners") or []
        if d.get("state") != "done" or len(owners) < 2:
            continue
        a, b = owners[:2]
        if not ("keep company" in _habits(house, a) or "keep company" in _habits(house, b)):
            continue
        began = K.project(projects.get(d.get("project"))).get("since", 0) if d.get("project") in projects else 0
        if any({x.get("a"), x.get("b")} == {a, b} and x["tick"] >= began for x in bonds):
            out.append("%s and %s finished %s together and grew close" % (_name(house, a), _name(house, b), d.get("kind")))
    return out


def orphan(house, since=0):
    """§6 plus: an orphaned project taken up by kin."""
    return ["%s took up %s's %s" % (_name(house, x["pet"]), _name(house, x.get("was")), x.get("kind") or "project")
            for x in _ev(house, "taken_up", since) if x.get("was") and _kin(house, x["pet"], x["was"])]


def thread(house, since=0):
    """§6 plus: a talk runs to three rounds and leaves a thread that is picked up."""
    out = []
    pair = lambda x: frozenset((x.get("a"), x.get("b")))
    threes = [x for x in _ev(house, "round", since) if (x.get("n") or 0) >= 3]
    left = [x for x in _ev(house, "thread", since) if not x.get("picked")]
    picked = [x for x in _ev(house, "thread", since) if x.get("picked")]
    for t in threes:
        lt = next((x for x in left if pair(x) == pair(t) and x["tick"] >= t["tick"]), None)
        pk = lt and next((x for x in picked if pair(x) == pair(t) and x["tick"] > lt["tick"]), None)
        if pk:
            out.append("%s and %s talked three rounds and picked it up again (%s)" % (_name(house, t["a"]), _name(house, t["b"]), lt.get("subject")))
    return out


FIND = {"pile": pile, "hoard": hoard, "shelter": shelter, "praise": praise, "joint": joint, "orphan": orphan, "thread": thread}

# for a scene that did not occur: its ingredients in order, each (event kind, a test, the rule it stands for)
NEEDS = {"pile": [("habit", lambda x: x.get("habit") == "collect", "a collect habit's go"), ("marked", lambda x: x.get("kind") == "pile", "a pile left"),
                  ("mess", None, "a pile counted as mess"), ("moved", None, "another's pile moved"), ("resent", None, "the owner resenting the one who moved it")],
         "hoard": [("taken", None, "a take"), ("marked", lambda x: x.get("kind") == "hoard", "a hoard"), ("found", None, "a hoard found"), ("opinion", None, "opinions moved by it")],
         "shelter": [("project", lambda x: x.get("kind") == "shelter", "a shelter begun"), ("step", None, "a project step"),
                     ("project", lambda x: x.get("kind") == "shelter" and x.get("state") == "done", "a shelter finished"),
                     ("slept_out", None, "a night under its own cover"), ("came_in", None, "coming in from the shelter")],
         "praise": [("praise", None, "praise given"), ("praise", lambda x: (x.get("pride") or 0) > 0, "pride raised by it"), ("resent", None, "envy resented")],
         "joint": [("habit", lambda x: x.get("habit") == "keep company", "a keep-company go"), ("project", lambda x: len(x.get("owners") or []) >= 2, "a joint project"),
                   ("project", lambda x: len(x.get("owners") or []) >= 2 and x.get("state") == "done", "a joint project finished"), ("bond", None, "a bond rising")],
         "orphan": [("project", lambda x: x.get("state") == "orphaned", "an orphaned project"), ("taken_up", None, "an orphan taken up")],
         "thread": [("round", lambda x: (x.get("n") or 0) >= 2, "a second round"), ("round", lambda x: (x.get("n") or 0) >= 3, "a third round"),
                    ("thread", lambda x: not x.get("picked"), "a thread left"), ("thread", lambda x: x.get("picked"), "a thread picked up")]}


def find(house, since=0, tpd=None):
    """{scene: [what happened, in words]} since a tick. `tpd`: the config's ticks a world day (for "over several days")."""
    house = dict(house, ticks_per_day=tpd or house.get("ticks_per_day"))
    return {s: FIND[s](house, since) for s in K.SCENES}


def missing(house, since=0, tpd=None):
    """{scene: words} for each scene that did not occur: the first ingredient never recorded, or that each was but
    never in one line (the rule joining them is missing)."""
    out = {}
    for s, got in find(house, since, tpd).items():
        if got:
            continue
        lack = next((why for what, ok, why in NEEDS[s] if not any(ok is None or ok(x) for x in _ev(house, what, since))), None)
        out[s] = "never: %s" % lack if lack else "each part happened, never together"
    return out
