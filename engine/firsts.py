"""Firsts, bests, a life's ambition, and being noticed (SPEC-v3.5.4 §6, §7, §9, §10 first half).

A first is judged by what was done, never by what anything is called: the kind and nature of a made thing, the
process done to a bit, the tool used, the room gone into, the passage read. Each is a key ("kind:bowl",
"make:bowl|soft", "process:clay|warm", "tool:hammer", "room:r21", "read:moss"), and the house keeps who did each
first in the house and in each family (house["new"]), and each pet what it has done (pet["firsts"]). An old house is
seeded once from its history, so a bowl made last week is not a first today.

A best is kept per pet (pet["bests"]): its finest made thing, its surest skill, the biggest thing it helped build,
the most firsts in a day. A child is born with its line's (pet["elders"]) and beating one is a big moment.

An ambition (pet["ambition"]) is something a pet means to do in its life, kept as a key the engine can see done,
with the words it was given in. None of it reaches a mind as a number. Tunables are in config.toml [drive]."""
import re

from . import craft, feats, hub, things
from .build import and_, find
from .world import add_event, label, moment, rnd

RANK = {None: 0, "own": 1, "family": 2, "house": 3}
PAST = {"weave": "wove"}   # (craft.DONE has the participle; "woven" will not do as a past)
CATS = ("thing", "skill", "built", "firsts")
FINE = ["", "well made", "finely made", "made with a master's paws"]
# what each best is called on the pet's page (the page is the visitor's: it may count)
PRACTISED = ["a little practised", "somewhat practised", "practised", "very practised"]
BEST_PAGE = {"thing": "Finest thing made", "skill": "Surest skill", "built": "Biggest thing helped build", "firsts": "Most firsts in a day"}


# ---- what the house has done ----

def state(house, cfg):
    """house["new"]: {"house": {key: {pet, tick}}, "family": {family: {key: {pet, tick}}}}, seeded once from history."""
    if "new" not in house:
        house["new"] = {"house": {}, "family": {}}
        seed(house, cfg)
    return house["new"]


def fam_of(house, pet):
    return str(hub.family_of(house, pet))


def level(house, cfg, pet, key):
    """How new this would be if this pet did it now: "house", "family", "own" or None."""
    N = state(house, cfg)
    if key not in N["house"]:
        return "house"
    if key not in N["family"].get(fam_of(house, pet), {}):
        return "family"
    return "own" if key not in pet.get("firsts", {}) else None


def mark(house, cfg, pet, key, tick, pid=None):
    """It has been done, by this pet (or, from history, by someone the house no longer knows)."""
    N, pid = state(house, cfg), pet["id"] if pet else pid
    N["house"].setdefault(key, {"pet": pid, "tick": tick})
    if pet:
        N["family"].setdefault(fam_of(house, pet), {}).setdefault(key, {"pet": pid, "tick": tick})
        pet.setdefault("firsts", {}).setdefault(key, tick)


def made_keys(recipe):
    return ["kind:%s" % recipe.get("kind"), "make:%s|%s" % (recipe.get("kind"), recipe.get("material"))]


def seed(house, cfg):
    """Once, for a house lived in before v3.5.4: everything it has done, from what is left of it. Made things still
    about and gone, what each pet has made and tried and found out, the recipes the house knows, the tools it has
    made, the rooms found and gone into, what was read. (Things made and gone before the house kept a note of them
    are not here: the first of those again is a first.)"""
    P = house["pets"]
    did = lambda pid, key, tick: mark(house, cfg, P.get(pid or ""), key, tick or 0, pid)
    rooms = [r for r in house["rooms"].values() if r.get("type")]
    for r in rooms:
        for o in things.made(r).values():
            for k in made_keys(o["made"]["recipe"]):
                did(o["made"]["by"], k, o["made"]["tick"])
        did(r.get("by"), "room:" + r["id"], r.get("found"))
    for g in house.get("gone_things", []):
        for k in made_keys(g["recipe"]):
            did(g["by"], k, g["made"])
    for key, rec in house.get("recipes", {}).items():
        if "+" not in key:   # ("kind:trowel" is a made kind as it is; a joining is no key here)
            did(rec.get("by"), ("process:" if "|" in key else "") + key, rec.get("tick"))
    for tool, tick in house.get("firsts", {}).items():
        did(None, "tool:" + tool, tick)
    for p in P.values():
        for pair in p.get("made_kinds", []):
            for k in made_keys(dict(zip(("kind", "material"), pair.split("|")))):
                did(p["id"], k, 0)
        for key, got in p.get("tried", {}).items():
            if got:
                did(p["id"], "process:" + key, 0)
        for rid, tick in p.get("rooms", {}).items():
            did(p["id"], "room:" + rid, tick)
        for r in p.get("read", []):
            did(p["id"], "read:" + r["title"].lower(), r["tick"])
    names = {label(p): p["id"] for p in P.values()}
    for m in house.get("moments", []):
        hit = m["kind"] == "read" and re.search(r" and read about (.+)$", m["text"])
        if hit:
            did(m["pet"] or names.get(m["text"].split(" asked ")[0]), "read:" + hit.group(1).lower(), m["tick"])
    for p in P.values():   # its bests, from what is left of what it did
        for o in [o for r in rooms for o in things.made(r).values() if o["made"]["by"] == p["id"]]:
            keep_best(p, "thing", quality(cfg, o), thing_words(cfg, o), house["tick"])
        top = top_skill(p)
        if top:
            keep_best(p, "skill", top[1], top[0], house["tick"], name=top[0])
    for r in rooms:
        for o in r["objects"].values():
            b = o.get("fix", {}).get("built")
            if b and b.get("project") in cfg.get("build", {}).get("project", {}):
                for pid in b.get("paws", []):
                    if pid in P:
                        keep_best(P[pid], "built", bigness(cfg, b["project"]), cfg["build"]["project"][b["project"]]["a"] + " " + b["project"], b["at"])
    for p in sorted(P.values(), key=lambda p: int(p["id"][1:]) if p["id"][1:].isdigit() else 0):
        if p.get("parent") in P and "elders" not in p:
            inherit(house, cfg, p)
            for cat, e in p["elders"].items():   # (what it had already beaten before anyone kept count is not beaten again)
                v = (p.get("skill") or {}).get(e.get("name"), 0) if cat == "skill" else p.get("bests", {}).get(cat, {}).get("v", 0)
                if v > e["v"]:
                    e["beaten"] = house["tick"]


# ---- words for a key ----

def words(house, cfg, key):
    """{base, did, ever, noun}: "warm clay", "warmed clay", "warmed clay", "fired clay". `noun` may be None."""
    from . import wants
    sort, what = key.split(":", 1)
    if sort in ("kind", "make"):
        kind, _, material = what.partition("|")
        a = things.a_thing(cfg, {"kind": kind, "material": material}, bool(material))
        return {"base": "make " + a, "did": "made " + a, "ever": "made " + a, "noun": a.split(" ", 1)[1]}
    if sort == "process":
        bit, how = what.split("|")
        gives = cfg["craft"]["rules"].get((bit, how), {}).get("gives")
        part, bit = craft.DONE.get(how, how), wants.a(bit)
        return {"base": "%s %s" % (how, bit), "did": "%s %s" % (PAST.get(how, part), bit), "ever": "%s %s" % (part, bit), "noun": gives}
    if sort == "tool":
        a = cfg["kinds"].get(what, {}).get("a", "a")
        return {"base": "use %s %s" % (a, what), "did": "used %s %s" % (a, what), "ever": "used %s %s" % (a, what), "noun": None}
    if sort == "room":
        name = house["rooms"].get(what, {}).get("name") or "a room nobody knew"
        return {"base": "go into " + name, "did": "went into " + name, "ever": "gone into " + name, "noun": None}
    return {"base": "read about " + what, "did": "read about " + what, "ever": "read about " + what, "noun": None}


def said(lvl, w, who, you=False):
    """A first in words: "Open Stone made the first bowl in the house" (or, `you`, "you made the first bowl in your
    family"); its own: "Grey Light warmed clay for the first time"."""
    if lvl == "own":
        return "%s %s for the first time" % (who, w["did"])
    where = "in the house" if lvl == "house" else "in your family" if you else "in its family"
    if w["noun"]:
        return "%s made the first %s %s" % (who, w["noun"], where)
    return "%s %s the first %s to have %s" % (who, "were" if you else "was", "in the house" if lvl == "house" else "of your family" if you else "of its family", w["ever"])


def board(lvl, w, who):
    where = "THE HOUSE" if lvl == "house" else "THE FAMILY"
    line = "FIRST %s IN %s" % (w["noun"], where) if w["noun"] else "FIRST IN %s TO HAVE %s" % (where, w["ever"])
    return ("%s: %s" % (line, who)).upper()


# ---- doing something for the first time (§6) ----

def first(house, cfg, pet, keys):
    """This pet did each of these keys. The newest of them (at the highest level, the first given on a tie) is
    rewarded, all are marked. Returns what an onlooker would have seen ("make the first bowl in the house") or None."""
    if not pet or pet["stage"] in ("egg", "dead"):
        return None
    D, tick, who = cfg["drive"], house["tick"], label(pet)
    levels = [(level(house, cfg, pet, k), k) for k in keys]
    for lvl, k in levels:
        aimed(house, cfg, pet, "first", k, lvl)
        mark(house, cfg, pet, k, tick)
    lvl, key = max(levels, key=lambda x: RANK[x[0]])
    if not lvl:
        return None
    day = house["clock"]["day"]
    t = pet.get("firsts_today") or [day, 0]
    if t[0] != day:
        t = [day, 0]
    worth = D["first_glow"][lvl] * D["first_fade"] ** t[1]   # each further first in a day gives less
    pet["firsts_today"] = [day, t[1] + 1]
    w = words(house, cfg, key)
    you = said(lvl, w, "you", True)
    if worth >= D["first_least"]:
        feats.glow(house, cfg, pet, round(min(3, max(1, worth))), you)
    if lvl != "own" or (worth >= D["first_least"] and key.split(":")[0] not in ("room", "read")):   # (going into a room and reading are moments already)
        feats.record(house, cfg, "first", pet["id"], said(lvl, w, who), board=board(lvl, w, who) if lvl != "own" else None,
                     room=pet["room"], level=lvl, key=key, you=you)
    in_a_day(house, cfg, pet, t[1] + 1)
    if lvl == "own":
        return None
    where = "in the house" if lvl == "house" else "in its family"
    return "%s make the first %s %s" % (who, w["noun"], where) if w["noun"] else "%s %s, the first time anyone %s had" % (who, w["base"], where)


def made(house, cfg, pet, o, room):
    """Hook (things.make, things.combine, invent.make): a thing was made. Firsts, bests, and who saw it."""
    seen = [best(house, cfg, pet, "thing", quality(cfg, o), thing_words(cfg, o), o["made"]["recipe"]["kind"]), first(house, cfg, pet, made_keys(o["made"]["recipe"]))]
    if any(seen):
        noticed(house, cfg, pet, *seen)
    elif o["made"].get("fine", 0) >= cfg["drive"]["fine_thing"]:   # a fine thing, when it was nothing more: seen, but not a feat, and once a day by each onlooker
        noticed(house, cfg, pet, "%s make %s" % (label(pet), thing_words(cfg, o)), plain=True)


def processed(house, cfg, pet, bit, how):
    """Hook (craft.process): something was done to a bit and something came of it."""
    noticed(house, cfg, pet, first(house, cfg, pet, ["process:%s|%s" % (bit, how)]))


def used(house, cfg, pet, kind):
    """Hook (craft.wear): a tool was used."""
    noticed(house, cfg, pet, first(house, cfg, pet, ["tool:" + kind]))


def entered(house, cfg, pet, room):
    """Hook (actions.go): it went into a room."""
    first(house, cfg, pet, ["room:" + room["id"]])


def read(house, cfg, pet, title):
    """Hook (book.ask): it read a passage."""
    first(house, cfg, pet, ["read:" + title.lower()])


# ---- bests (§7) ----

def quality(cfg, o):
    """How fine a made thing is, as the house already rates one: the maker's practice when it made it (`fine`, 0 to
    3, things.make), its size (1 to 3: a practised maker's are bigger), built sturdy with a hammer, how complex its kind
    is (`rank`, 1 to 3: a sculpture over a cup), and whether its nature or its kind is one the house found out by
    joining (an emerged property, an invented kind). Summed: a practised maker soon makes everything as fine and as big
    as it can, so a finer thing than its parent's is a harder, newer thing, not only a later one."""
    m, r = o["made"], o["made"]["recipe"]
    K = cfg["kinds"].get(r.get("kind"), {})
    return m.get("fine", 0) + things.size(o) + bool(m.get("sturdy")) + K.get("rank", 1) + bool(cfg["materials"].get(r.get("material"), {}).get("emerged") or K.get("invented"))


def thing_words(cfg, o):
    """"a large soft bowl, finely made"."""
    r, fine = o["made"]["recipe"], o["made"].get("fine", 0)
    a = things.a_thing(cfg, {"kind": r.get("kind"), "material": r.get("material")}, True)
    return ("a large " + a.split(" ", 1)[1] if things.size(o) == 3 else a) + (", " + FINE[fine] if fine else "")


def top_skill(pet):
    """(its surest skill, how practised) or None."""
    s = pet.get("skill") or {}
    return max(s.items(), key=lambda kv: kv[1]) if s and max(s.values()) > 0 else None


def bigness(cfg, project):
    return sum(cfg["build"]["project"][project].get("needs", {}).values())


def keep_best(pet, cat, v, words_, tick, **more):
    B = pet.setdefault("bests", {})
    if cat not in B or v > B[cat]["v"]:
        B[cat] = {"v": v, "words": words_, "tick": tick, **more}


BEAT = {   # (beating an elder's best: the moment, what the pet is told, the board)
    "thing": ("%(who)s made a finer %(kind)s than %(elder)s ever did", "you made a finer %(kind)s than %(elder)s ever did", "A FINER %(kind)s THAN %(elder)s EVER MADE: %(who)s"),
    "skill": ("%(who)s is surer at %(kind)s than %(elder)s ever was", "you are surer at %(kind)s than %(elder)s ever was", "SURER AT %(kind)s THAN %(elder)s: %(who)s"),
    "built": ("%(who)s helped build a bigger thing than %(elder)s ever did: %(kind)s", "you helped build a bigger thing than %(elder)s ever did",
              "%(kind)s, BIGGER THAN %(elder)s EVER BUILT: %(who)s"),
    "firsts": ("%(who)s did more new things in a day than %(elder)s ever did", "you have done more new things today than %(elder)s ever did in a day",
               "MORE FIRSTS IN A DAY THAN %(elder)s: %(who)s"),
}
OWN = {"thing": "you made the finest thing you have ever made", "skill": "you are surer at %s than you have ever been",
       "built": "you helped build the biggest thing you ever have", "firsts": "you have done more new things today than on any day before"}


def best(house, cfg, pet, cat, v, words_, kind, **more):
    """It did something that may beat a best: its line's (pet["elders"], a big moment, once) or its own (a small
    glow). Equalling one is nothing. Returns what an onlooker would have seen, or None."""
    D, tick, who = cfg["drive"], house["tick"], label(pet)
    mine, old = pet.get("bests", {}).get(cat), pet.get("elders", {}).get(cat)
    out = None
    if old and not old.get("beaten") and v > old["v"] and (cat != "skill" or more.get("name") == old.get("name")):
        old["beaten"] = tick
        t = {"who": who, "elder": old["who"], "kind": kind}
        feats.glow(house, cfg, pet, D["best_elder_glow"], BEAT[cat][1] % t)
        feats.record(house, cfg, "best", pet["id"], BEAT[cat][0] % t, board=(BEAT[cat][2] % t).upper(), room=pet["room"], cat=cat, elder=old["by"])
        aimed(house, cfg, pet, "best", cat)
        out = (BEAT[cat][0] % t).replace(who + " made", who + " make")
    elif mine and v > mine["v"] and (cat != "skill" or step(cfg, v) > step(cfg, mine["v"])):
        feats.glow(house, cfg, pet, D["best_own_glow"], OWN[cat] % kind if "%s" in OWN[cat] else OWN[cat])
        out = "%s make the finest thing it has ever made" % who if cat == "thing" else None
    keep_best(pet, cat, v, words_, tick, **more)
    return out


def step(cfg, v):
    return sum(v >= n for n in cfg["skills"]["steps"])


def in_a_day(house, cfg, pet, n):
    """Its most firsts in a day: its own best is beaten only past an earlier day's (today's count grows as it goes)."""
    day, mine, old = house["clock"]["day"], pet.get("bests", {}).get("firsts"), pet.get("elders", {}).get("firsts")
    if mine and mine.get("day") == day and not (old and not old.get("beaten") and n > old["v"]):
        mine["v"] = max(mine["v"], n)
        return
    best(house, cfg, pet, "firsts", n, "new things in one day", "", day=day)


def built(house, cfg, paws, project):
    """Hook (build.stand): it stands; whoever had a paw in it may have helped build its biggest thing."""
    a = "%s %s" % (cfg["build"]["project"][project]["a"], project)
    for pid in paws:
        p = house["pets"].get(pid)
        if p and p["stage"] not in ("egg", "dead"):
            best(house, cfg, p, "built", bigness(cfg, project), a, a)
            aimed(house, cfg, p, "build", project)


def hourly(house, cfg):
    """Hook (director.hourly): a skill grown past a best, and an ambition to grow sure at something."""
    for p in house["pets"].values():
        if p["stage"] in ("egg", "dead"):
            continue
        for name, v in sorted((p.get("skill") or {}).items(), key=lambda kv: -kv[1]):
            old = p.get("elders", {}).get("skill")
            if old and old.get("name") == name and not old.get("beaten") and v > old["v"]:
                best(house, cfg, p, "skill", v, name, name, name=name)
        top = top_skill(p)
        if top:
            best(house, cfg, p, "skill", top[1], top[0], top[0], name=top[0])
        A = p.get("ambition")
        if A and A["kind"] == "skill" and craft.skill(cfg, p, A["key"]) >= cfg["drive"]["ambition_skill"]:
            aimed(house, cfg, p, "skill", A["key"])


def inherit(house, cfg, child):
    """A child is born knowing its line's bests: for each, the higher of its parent's own and what the parent was
    born knowing."""
    parent = house["pets"].get(child.get("parent") or "")
    if not parent:
        return
    E = child["elders"] = {}
    for cat in CATS:
        mine = parent.get("bests", {}).get(cat)
        have = [dict(mine, by=parent["id"], who=label(parent)) if mine else None, parent.get("elders", {}).get(cat)]
        have = [dict(h, beaten=None) for h in have if h]
        if have:
            E[cat] = max(have, key=lambda h: h["v"])


def best_lines(cfg, B):
    """A pet's bests in words, for its page: [{what, text, by?}]."""
    out = []
    for cat in CATS:
        b = B.get(cat)
        if b and b["v"]:
            text = b["words"] if cat != "skill" else "%s (%s)" % (b["words"], PRACTISED[step(cfg, b["v"])])
            if cat == "firsts":
                text = "%d %s" % (b["v"], "new thing in one day" if b["v"] == 1 else "new things in one day")
            out.append({"what": BEST_PAGE[cat], "text": text, "by": b.get("by")})
    return out


def page(house, cfg, pet):
    """For the pet's page (pages.pet_page): its ambition, its bests, and its family's (the best of everyone in it)."""
    fam, fb = fam_of(house, pet), {}
    for p in house["pets"].values():
        if fam_of(house, p) == fam:
            for cat, b in p.get("bests", {}).items():
                if b["v"] and (cat not in fb or b["v"] > fb[cat]["v"]):
                    fb[cat] = dict(b, by=p["id"])
    A = pet.get("ambition")
    return {"ambition": A and {"text": A["text"], "done": A.get("done_day")}, "own": best_lines(cfg, pet.get("bests", {})), "family": best_lines(cfg, fb)}


# ---- being noticed (§10, first half) ----

def noticed(house, cfg, pet, *seen, plain=False):
    """Whoever is awake in the room saw it: each is told what it saw (each feat once: it is told as it happens), and
    the maker that it was seen (a little pride, a little company). `plain`: only a fine thing, which an onlooker
    remarks on once a day for each maker, and which is not a feat."""
    seen, day = [s for s in seen if s], house["clock"]["day"]
    if not seen:
        return
    them = [p for p in house["pets"].values() if p["id"] != pet["id"] and p["room"] == pet["room"] and p["stage"] not in ("egg", "dead") and not p["sleep"]
            and not (plain and p.get("saw", {}).get(pet["id"]) == day)]
    if not them:
        return
    for p in them:
        for s in seen:
            add_event(house, p, "you saw " + s)
        p["needs"]["company"] = min(100.0, p["needs"]["company"] + cfg["drive"]["notice_company"])
    names = and_([label(p) for p in them])
    feats.glow(house, cfg, pet, cfg["drive"]["noticed_glow"], "%s saw what you did" % names)
    pet["needs"]["company"] = min(100.0, pet["needs"]["company"] + cfg["drive"]["notice_company"])
    if plain:
        for p in them:
            p.setdefault("saw", {})[pet["id"]] = day
        return
    feats.record(house, cfg, "noticed", pet["id"], "%s saw %s" % (names, seen[0]), room=pet["room"], by=[p["id"] for p in them])


# ---- a life's ambition (§9) ----

def candidates(house, cfg, pet):
    """What it could take as its ambition, in plain words, each a thing the engine can see done: its parent's
    unreached ambition and unfinished wants, firsts its family or the house has not reached, what it is good at,
    a best of its line's to beat."""
    out, N, mine = [], state(house, cfg), pet.get("firsts", {})
    fam = N["family"].get(fam_of(house, pet), {})
    # (only one can be first: a first another living pet means to be is not offered)
    taken = {p["ambition"]["key"] for p in house["pets"].values() if p is not pet and p["stage"] not in ("egg", "dead") and (p.get("ambition") or {}).get("level") in ("house", "family")}
    add = lambda kind, key, text, **more: out.append(dict(more, kind=kind, key=key, text=text)) if not any(c["key"] == key for c in out) and key not in taken else None
    parent = house["pets"].get(pet.get("parent") or "")
    if parent:
        A = parent.get("ambition")
        if A and not A.get("done") and parent["stage"] == "dead" and not unreachable(house, cfg, pet, A):   # (taking up what a parent who has died did not finish)
            add(A["kind"], A["key"], A.get("plain") or A["text"], **{k: A[k] for k in ("level", "room") if k in A})
        for w in parent.get("wants", []):
            what, key = w["key"].split(":", 1)
            if what == "tool" and "kind:" + key not in mine:
                add("first", "kind:" + key, "make %s %s" % (cfg["kinds"].get(key, {}).get("a", "a"), key), level="own")
            elif what == "build" and "|" in key and key.split("|")[1] in cfg.get("build", {}).get("project", {}):
                rid, project = key.split("|")
                if rid in house["rooms"] and not build_done(house, rid, project):
                    add("build", project, "build %s %s in %s" % (cfg["build"]["project"][project]["a"], project, house["rooms"][rid]["name"]), room=rid)
    r = rnd(house, "ambition", pet["id"], house["clock"]["day"])
    gettable = {b for b, v in cfg["house"]["bits"].items() if not v.get("made")} | {k.split("|")[0] for k in N["house"] if k.startswith("process:")} \
        | {cfg["craft"]["rules"].get(tuple(k[8:].split("|")), {}).get("gives") for k in N["house"] if k.startswith("process:")}
    rules = sorted("process:%s|%s" % bh for bh, rule in cfg["craft"]["rules"].items() if not rule.get("spoils") and bh[0] in gettable and bh[1] in craft.DONE)
    kinds = sorted("kind:" + k for k, v in cfg["kinds"].items() if not v.get("invented") and all(any(a in gettable for a in g.split("|")) for g in cfg["craft"].get("needs", {}).get(k, [])))
    for lvl, done in (("house", N["house"]), ("family", fam)):
        for pool in (rules, kinds):
            left = [k for k in pool if k not in done and k not in taken]
            if left:
                k = r.choice(left)
                add("first", k, "be the first %s to %s" % ("in the house" if lvl == "house" else "of your family", words(house, cfg, k)["base"]), level=lvl)
    top = top_skill(pet) or top_skill(parent or {})
    if top and craft.skill(cfg, pet, top[0]) < cfg["drive"]["ambition_skill"]:
        add("skill", top[0], "grow very sure at %s" % top[0])
    for cat in ("thing", "built"):
        e = pet.get("elders", {}).get(cat)
        if e and not e.get("beaten"):
            add("best", cat, "make a finer thing than %s ever did" % e["who"] if cat == "thing" else "help build a bigger thing than %s ever did" % e["who"])
    return out


def build_done(house, rid, project):
    _, o = find(house["rooms"][rid], project)
    return bool(o and o.get("fix", {}).get("built"))


def unreachable(house, cfg, pet, A):
    """Someone else got there first, or it has been built without it."""
    N = state(house, cfg)
    if A["kind"] == "first" and A.get("level") in ("house", "family"):
        by = N["house"].get(A["key"]) if A["level"] == "house" else N["family"].get(fam_of(house, pet), {}).get(A["key"])
        return bool(by) and by["pet"] != pet["id"]
    if A["kind"] == "build" and A.get("room") in house["rooms"]:
        return build_done(house, A["room"], A["key"])
    return False


def take(house, cfg, pet, c, text=None):
    """It means to do this with its life."""
    was = pet.get("ambition")
    pet["ambition"] = dict(c, plain=c["text"], text=text or c["text"], since=house["tick"], done=None, changed=bool(was))
    moment(house, "ambition", "%s means to %s in its life" % (label(pet), pet["ambition"]["text"]) if not was else
           "%s gave up meaning to %s, and means now to %s" % (label(pet), was["text"], pet["ambition"]["text"]), pet["id"], pet["room"])


def aimed(house, cfg, pet, kind, key, lvl=None):
    """Did that reach its ambition? Then it is one of the biggest moments of its life, and its children hear of it."""
    A = pet.get("ambition")
    if not A or A.get("done") or A["kind"] != kind or A["key"] != key:
        return
    if kind == "first" and (lvl is None or RANK[lvl] < RANK[A.get("level", "own")]):   # (done before, or someone else was first)
        return
    A["done"], A["done_day"] = house["tick"], house["clock"]["day"]
    who = label(pet)
    feats.glow(house, cfg, pet, cfg["drive"]["ambition_glow"], "you have done what you meant to do with your life: %s" % A["text"])
    feats.record(house, cfg, "ambition", pet["id"], "%s did what it meant to do in its life: %s" % (who, A["text"]),
                 board="%s DID WHAT IT SET OUT TO DO: %s" % (who.upper(), A["plain"].upper()), room=pet["room"])
    for c in pet.get("children", []):
        kid = house["pets"].get(c)
        if kid and kid["stage"] != "dead":
            tell(house, pet, kid)


def tell(house, pet, kid):
    """The child hears it (the legacy): in what it was told, beside its parent's message."""
    A = pet.get("ambition")
    if A and A.get("done") and not any(t["kind"] == "ambition" and t["by"] == pet["id"] for t in kid["told"]):
        kid["told"].append({"by": pet["id"], "who": pet["word"], "kind": "ambition", "text": "set out in life to %s, and did it" % A["text"], "tick": house["tick"]})
        if kid["stage"] != "egg":
            add_event(house, kid, "your %s did what it set out to do in its life: %s" % (pet["word"], A["text"]))


def laid(house, cfg, pet, egg):
    """Hook (life.lay_egg): an egg hears of an ambition already reached."""
    tell(house, pet, egg)


def hatched(house, cfg, pet):
    """Hook (life.hatch): born knowing its line's bests, and with an ambition the engine picks for it (no model is
    asked at hatching)."""
    state(house, cfg)
    inherit(house, cfg, pet)
    cs = candidates(house, cfg, pet)
    if cs and not pet.get("ambition"):
        take(house, cfg, pet, rnd(house, "hatched ambition", pet["id"]).choice(cs[:cfg["drive"]["ambition_offers"]]))


def offer(house, cfg, pet):
    """At night (sleep.night): the words that offer it an ambition, when it has none or its own can no longer be
    reached and it has not changed it before; "" when there is nothing to ask."""
    A = pet.get("ambition")
    if pet["stage"] in ("egg", "dead") or (A and (A.get("done") or A.get("changed") or not unreachable(house, cfg, pet, A))):
        pet.pop("ambition_offer", None)
        return ""
    cs = pet["ambition_offer"] = candidates(house, cfg, pet)[:cfg["drive"]["ambition_offers"]]
    if not cs:
        return ""
    head = ("\nyour ambition for your life: %s; it can no longer be done. You may change it, once in your life; 0 keeps it:" % A["text"] if A else
            "\nyour ambition for your life: none yet. Take one, to keep all your life: something you mean to do, and can finish. You could:")
    return head + "".join("\n  %d. %s" % (i, c["text"]) for i, c in enumerate(cs, 1)) + "\n"


def took(house, cfg, pet, reply):
    """What the night chose: one of those offered, maybe in its own words. One is taken if it has none."""
    from .actions import clean
    from .life import last_sentence
    cs = pet.pop("ambition_offer", None)
    if not cs:
        return
    reply = reply if isinstance(reply, dict) else {}
    try:
        pick = int(reply.get("pick", 0))
    except (TypeError, ValueError):
        pick = 0
    if not 1 <= pick <= len(cs):
        if pet.get("ambition"):
            return
        pick = 1
    text = last_sentence(clean(reply.get("words") or "", 140), 120).strip() or None
    take(house, cfg, pet, cs[pick - 1], text)


# ---- the packet (mind.perceive) ----

def lines(house, cfg, pet):
    """A short section: its ambition, the newest firsts in its family and the house, one or two things nobody in
    the house has done that are within its reach, a best of its line's to beat, and an ambition its parent reached."""
    out, D, tick = [], cfg["drive"], house["tick"]
    A = pet.get("ambition")
    if A:
        out.append("your ambition for your life: %s%s" % (A["text"], " (you have done it)" if A.get("done") else ""))
    fam = fam_of(house, pet)
    since = tick - D["recent_days"] * cfg["ticks_per_day"]
    ours = lambda f: f["pet"] in house["pets"] and fam_of(house, house["pets"][f["pet"]]) == fam
    recent = [f for f in reversed(house.get("feats", {}).get("list", [])) if f["tick"] >= since and
              ((f["kind"] == "first" and f.get("level") == "house") or (f["kind"] in ("first", "best") and f.get("level") != "own" and ours(f)))][:2]
    if recent:
        out.append("lately: " + "; ".join(f.get("you") if f["pet"] == pet["id"] and f.get("you") else f["text"] for f in recent))
    reach = within_reach(house, cfg, pet)
    if reach:
        out.append("nobody in the house has ever " + ", or ".join(reach))
    E = pet.get("elders", {})
    cat = next((c for c in ("thing", "built", "skill") if c in E and not E[c].get("beaten")), None)
    if cat:
        e = E[cat]
        out.append("a best of your family's to beat: " + ("%s's finest thing, %s" % (e["who"], e["words"]) if cat == "thing" else
                                                          "%s helped build %s" % (e["who"], e["words"]) if cat == "built" else "how sure %s was at %s" % (e["who"], e["words"])))
    for t in [t for t in pet.get("told", []) if t["kind"] == "ambition"][:1]:
        out.append("your %s %s" % (t["who"], t["text"]))
    return "\n".join(out)


def within_reach(house, cfg, pet):
    """At most two things nobody in the house has done that it could do now: a process on a bit it has to hand
    that can be done in a room it knows, a kind it has the stuff for, a door nobody has been through."""
    N, room, out = state(house, cfg), house["rooms"][pet["room"]], []
    hand = set(pet["carrying"]) | {s["bit"] for s in room["spots"] if s["ready"] and not s.get("on")}
    for (bit, how), rule in sorted(cfg["craft"]["rules"].items()):
        if bit in hand and how in craft.DONE and not rule.get("spoils") and "process:%s|%s" % (bit, how) not in N["house"] and craft.places(house, cfg, pet, how):
            out.append(words(house, cfg, "process:%s|%s" % (bit, how))["ever"])
            break
    allowed = {p for b in pet["carrying"] for p in cfg["house"]["bits"][b]["can"]}
    for k, v in sorted(cfg["kinds"].items()):
        if pet["carrying"] and "kind:" + k not in N["house"] and not v.get("invented") and not craft.lacking(cfg, k, pet["carrying"]) and allowed - set(v.get("not", [])):
            out.append(words(house, cfg, "kind:" + k)["ever"])
            break
    if len(out) < 2:
        door = next((d for d, rid in sorted(room["doors"].items()) if not house["rooms"][rid]["type"]), None)
        if door:
            out.append("been through the %s door here" % door)
    return out[:2]
