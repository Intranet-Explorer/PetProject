"""Things the pets invent (SPEC-v3.5 §3). Whenever two things are joined in a way the house has not seen, a new kind
is born. If what they make fits a use (view/assets/uses.json: a base part and what is added to it) it is that use,
has only those parts, and does what the use does: a stick with a flame is a light that goes where its carrier goes.
If it fits none it is a curio: the base of the sturdier or larger thing with the other's signature part on a free
spot, and nothing but what its materials did. The pet names it; the house keeps the kind (house["invented"]) with
its parts, and it is a recipe like any other: known by its maker, handed on, lost when nobody living knows it,
found again by whoever joins the same two things. Part names, spots and limits are data (view/assets/parts.json);
the view draws from the same record. No model is asked anything here."""
import itertools
import json
from pathlib import Path

from . import craft, firsts, things
from .world import LONG_AGO, add_event, bit_kinds, clock, free_tile, hours, label, moment, rnd, ticks, weather_of

ART = Path(__file__).parent.parent / "view" / "assets"
P, USES = json.loads((ART / "parts.json").read_text()), json.loads((ART / "uses.json").read_text())["uses"]
PART, RULES = P["thing"], P["rules"]


# ---- composition (§3.0, §3.2, §3.4) ----

def kind_parts(cfg, kind):
    """(base part, signature part) of a kind: the catalog's, or an invented kind's own. None if it has none."""
    k, e = cfg["kinds"].get(kind) or {}, P["kinds"].get(kind)
    got = (k["base"], k["signature"]) if k.get("invented") else (e["base"], e["signature"]) if e else None
    return got if got and all(p in PART for p in got) else None


def place(base, tops):
    """A spot of the base for each part added, in order: the first in the part's own list that the base has free,
    or that a part already there carries (a flame stands in a fork). [spot, ...], or None if one has nowhere to go.
    (The view's preview and engine.check_parts place them the same way.)"""
    taken, out = {}, []
    for t in tops:
        at = next((s for s in PART[t]["on"] if s in PART[base]["spots"] and (s not in taken or s in PART[taken[s]].get("carries", []))), None)
        if at is None:
            return None
        taken[at] = t
        out.append(at)
    return out


def look(part, at, r):
    return {"part": part, "at": at, "material": r["material"], "color": r.get("color", "grey")}


def put(base, x, tops):
    """The parts of a thing: x's base, and these [(part, the recipe it came from)] where they go. None if they do not."""
    spots = place(base, [t for t, _ in tops])
    return spots and ([look(base, None, x)] + [look(t, s, r) for (t, r), s in zip(tops, spots)])[:RULES["max_parts"]]


def useful(cfg, x, y, uses=None):
    """(the use, its parts) of a thing built on x with y's signature part (x, y: two recipes), or None. It fits a
    use when its base is one of the use's and there is a part for each thing the use adds, y's among them; it has
    those parts and no others, but for one the use says it may also carry (if there is a spot for it). The first
    use in the file that fits is the one (`uses`: only these)."""
    a, b = kind_parts(cfg, x.get("kind")), kind_parts(cfg, y.get("kind"))
    if not a or not b:
        return None
    base, have = a[0], [(b[1], y), (a[1], x)]   # what there is to add: the other thing's part, and the base's own
    for name, U in USES.items():
        if base not in U["base"] or (uses and name not in uses):
            continue
        for order in itertools.permutations(range(len(have)), len(U["add"])) if len(U["add"]) <= len(have) else ():
            if 0 not in order or not all(have[i][0] in options for i, options in zip(order, U["add"])):
                continue
            tops = [have[i] for i in order]
            may = [h for i, h in enumerate(have) if i not in order and h[0] in U.get("may", []) and h[0] not in [t for t, _ in tops]]
            parts = put(base, x, may + tops) or put(base, x, tops)   # (what it may carry goes on first: the flame stands in the fork)
            if parts:
                return name, parts
    return None


def curio(cfg, x, y):
    """The parts of a thing that fits no use, built on x with y's signature part: x's base, x's own signature part,
    then y's, so both halves can be told. Where the two are the same part, or there is no spot left for the third,
    x gives up its own; y's is never left off. None for a kind that has no parts, or a part with nowhere to go."""
    a, b = kind_parts(cfg, x.get("kind")), kind_parts(cfg, y.get("kind"))
    if not a or not b:
        return None
    (base, own), given = a, b[1]
    return (put(base, x, [(own, x), (given, y)]) if own != given else None) or put(base, x, [(given, y)])


def sturdier(cfg, olds):
    """The two things, the sturdier or larger first: its base is the base."""
    weight = lambda o: (things.size(o), bool(o["made"].get("sturdy")), cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("rank", 1))
    return sorted(olds, key=weight, reverse=True)


def built(cfg, olds):
    """(the use or "curio", the parts, the base thing's recipe, the other's) for two things joined, or None if
    they cannot be put together at all. The uses are tried in the file's order (the plainest, a keepsake, is
    last), each on the sturdier thing's base and then on the other's; a curio is built on the sturdier's."""
    x, y = [o["made"]["recipe"] for o in sturdier(cfg, olds)]
    for use in USES:
        for a, b in ((x, y), (y, x)):
            got = useful(cfg, a, b, [use])
            if got:
                return got[0], got[1], a, b
    return next((("curio", parts, a, b) for a, b in ((x, y), (y, x)) for parts in [curio(cfg, a, b)] if parts), None)


def key_of(recipes):
    """The recipe of an invention: the two kinds, each in its material, whichever way round."""
    return "+".join(sorted("%s/%s" % (r.get("kind"), r["material"]) for r in recipes))


# ---- what it does (§3.0, §3.2): from the engine's rules ----

def plus(a, b):
    """Two properties together: what each does, and where they say different things of the same matter, the second."""
    out = dict(a)
    for k, v in b.items():
        out[k] = plus(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def effect(cfg, o):
    """The rule of the use a made thing has (uses.json `effect`): {} for a curio, a catalog kind, a fixture."""
    return cfg["kinds"].get(o.get("made", {}).get("recipe", {}).get("kind"), {}).get("effect") or {}


def prop(cfg, rec):
    """What a thing of an invented kind does by the rules for materials: the properties of both its halves, the
    nature it kept winning where they differ; where two properties met (v3.4 §3.2), what emerged, which is
    neither; and over that what its use gives it."""
    M, out = cfg["materials"], {}
    for p in [rec["material"]] if M[rec["material"]].get("emerged") else [p for p in rec["props"] if p != rec["material"]] + [rec["material"]]:
        out = plus(out, M[p])
    return plus(out, USES.get(rec["use"], {}).get("effect", {}).get("prop", {}))


def does(cfg, rec, base):
    """One short sentence of what it does: its use's, or for a curio the house's own words for what its materials
    do; and what its base lets it do."""
    met = cfg["materials"][rec["material"]].get("emerged")
    says = [cfg["craft"]["meets"][frozenset(met)]["says"]] if met else [cfg["materials"][p]["says"].split(";")[0].split(":")[0] for p in rec["props"]]
    says = [USES[rec["use"]]["does"]] if rec["use"] in USES else [s for s in says if not s.startswith("nothing")] or ["it just sits there"]
    return "; ".join(says + ["it hangs on the wall"] * bool(base.get("wall")) + ["it can be hung up"] * bool(base.get("hangs")))


def as_kind(cfg, rec):
    """An invented kind as the catalog would have it, so everything that asks what a kind is gets an answer: where
    it goes, what it holds, what it is built on, and what it does."""
    base, E = cfg["kinds"].get(rec["from"][0], {}), USES.get(rec["use"], {}).get("effect", {})
    return {"invented": True, "a": rec["a"], "not": [], "rank": min(3, base.get("rank", 1) + 1), "wall": rec["wall"], "hangs": rec["hangs"], "store": rec["store"],
            "inside": bool(rec["store"] and (base.get("inside") or E.get("inside"))), "furniture": bool(base.get("furniture")), "from": rec["from"],
            "base": rec["parts"][0]["part"], "signature": rec["parts"][-1]["part"], "prop": prop(cfg, rec), "effect": E,
            **({"counts": E["tool"]} if E.get("tool") else {}), **({"plantable": True} if E.get("plantable") else {})}


def install(house, cfg):
    """A house's own kinds, laid into the catalog it runs on (when it is opened, and as each is invented).
    ponytail: one house to a config; two houses run on one config in one process would see each other's kinds in the
    catalog (never offered: `offered` goes by the house), and a per-house catalog is the way out."""
    for name, rec in house.get("invented", {}).items():
        cfg["kinds"][name] = as_kind(cfg, rec)


# ---- a new kind is born (§3.1) ----

def today(house, cfg):
    return sum(1 for v in house.get("invented", {}).values() if clock(cfg, v["tick"])["day"] == house["clock"]["day"])


def born(house, cfg, pet, olds, r, meets):
    """Two things are being joined (things.combine). The name of the invented kind that comes of it: a new one,
    whenever the house has not seen these two joined; the one it made before, when it has. None (the larger kind,
    as before v3.5) only past the day's limit, or for a thing of a kind that has no parts."""
    pet["joined"] = house["tick"]
    recs, inv = [o["made"]["recipe"] for o in olds], house.setdefault("invented", {})
    key, made = key_of(recs), built(cfg, olds)
    again = next((n for n, v in inv.items() if v["key"] == key), None)
    if again:   # ... and whoever did it knows how now (if nobody living did, it is found again)
        craft.learn(house, cfg, pet, "kind:" + again)
        if meets:   # (where nothing emerged, it is told what kind it is as the joining is: things.combine)
            add_event(house, pet, said(house, again, True))
        return again
    if not made or today(house, cfg) >= cfg["invent"]["per_day"]:
        return None
    use, parts, x, y = made
    taken = set(cfg["kinds"]) | set(inv) | set(cfg["house"]["bits"]) | {f["name"] for t in cfg["house"]["rooms"].values() for f in t["fixtures"]}
    first = things.clean_name(r.get("name")) or "thing"
    name = next(n for n in [first] + ["%s %s" % (first, c) for c in things.COUNT[2:]] + ["%s %d" % (first, house["tick"])] if n not in taken)
    base, E = cfg["kinds"].get(x.get("kind"), {}), USES.get(use, {}).get("effect", {})
    rec = inv[name] = {"name": name, "a": "an" if name[0] in "aeiou" else "a", "use": use, "parts": parts,
                       "size": "large" if base.get("furniture") or max(things.size(o) for o in olds) >= 3 else "small", "from": [x.get("kind"), y.get("kind")],
                       "props": list(dict.fromkeys([x["material"], y["material"]] + ([meets["name"]] if meets else []))),
                       "material": meets["name"] if meets else r["material"], "wall": bool(base.get("wall")), "hangs": bool(base.get("hangs")),
                       "store": max(base.get("store", 0), E.get("store", 0)), "by": pet["id"], "tick": house["tick"], "key": key}
    does_ = prop(cfg, rec)
    # ponytail: parts.json says which parts sound, not how loud: the part given first, then the base's own, then the
    # base. A `loud` number on each part is the upgrade.
    sound = next((PART[p["part"]]["sound"] for p in parts[:0:-1] + parts[:1] if PART[p["part"]].get("sound")), None)
    rec.update(does=does(cfg, rec, base), sound=sound if does_.get("loud") else None, glow=bool(does_.get("light")))
    cfg["kinds"][name] = as_kind(cfg, rec)
    pet.setdefault("recipes", {})["kind:" + name] = {"tick": house["tick"], "from": "found"}
    house.setdefault("recipes", {})["kind:" + name] = {"by": pet["id"], "tick": house["tick"]}
    if E.get("tool"):   # (a cutter is the house's carver: nobody goes on wanting one)
        house.setdefault("firsts", {}).setdefault(E["tool"], house["tick"])
    craft.found(house, pet, "%s invented the %s: %s" % (label(pet), name, " ".join(r["purpose"].split())[:80] or rec["does"]), "invented")
    if meets:
        add_event(house, pet, said(house, name, True))
    return name


def said(house, name, emerged=False):
    """What the pet is told of the kind that came of its joining, or "" if nothing did. `emerged`: it has been told
    already that the thing does what neither part did."""
    rec = house.get("invented", {}).get(name)
    if not rec:
        return ""
    if rec["tick"] != house["tick"]:
        return "it is %s %s, like the one %s first made" % (rec["a"], name, label(house["pets"][rec["by"]]) if rec["by"] in house["pets"] else "someone")
    new = "nobody in the house has made the like of the %s" % name
    if not USES.get(rec["use"], {}).get("effect"):   # a curio does what its halves did and no more; a keepsake is for keeping
        kept = " (a thing to keep)" * (rec["use"] != "curio")
        return "%s: it is a new kind of thing%s, and you know how it is made" % (new, kept) if emerged else "nothing new came of it but the thing itself%s: %s, and you know how it is made" % (kept, new)
    return "%s: it is a new kind of thing (%s), and you know how it is made" % (new, USES[rec["use"]]["does"])


def words(cfg, kind):
    """The recipe in plain words (craft.words)."""
    frm = cfg["kinds"].get(kind, {}).get("from")
    one = lambda k: "%s %s" % (cfg["kinds"].get(k, {}).get("a", "a"), k)
    return "%s can be made by joining %s and %s" % (one(kind), one(frm[0]), one(frm[1])) if frm else "%s can be made" % one(kind)


# ---- made again from its recipe (§3.3) ----

def stuff(cfg, rec, carrying):
    """The bits it carries that an invented kind is made of: one for the nature of each of its two halves. None if it lacks any."""
    need = [p for p in rec["props"] if not cfg["materials"][p].get("emerged")]
    for order in itertools.permutations(need):
        left, used = list(carrying), []
        for m in order:
            b = next((b for b in left if m in cfg["house"]["bits"][b]["can"]), None)
            if b is None:
                break
            left.remove(b)
            used.append(b)
        else:
            return used
    return None


def knows(house, pet, kind):
    return kind in house.get("invented", {}) and "kind:" + kind in pet.get("recipes", {})


def offered(house, cfg, pet, kinds):
    """The kinds a mind is offered to make, by material (mind.perceive): an invented kind only to one who knows its
    recipe and carries what it is made of, under the first of its halves' natures that is within reach."""
    out = {m: [k for k in ks if not cfg["kinds"].get(k, {}).get("invented")] for m, ks in kinds.items()}
    for name, rec in house.get("invented", {}).items():
        m = next((p for p in rec["props"] if p in out), None)
        if m and knows(house, pet, name) and stuff(cfg, rec, pet["carrying"]) is not None:
            out[m].append(name)
    return out


def check_make(a, house, cfg, pet):
    r, room = a["recipe"], house["rooms"][pet["room"]]
    rec, one = house.get("invented", {}).get(r["kind"]), "%s %s" % (cfg["kinds"][r["kind"]].get("a", "a"), r["kind"])
    if not knows(house, pet, r["kind"]):
        return "you do not know how %s is made" % one
    if stuff(cfg, rec, pet["carrying"]) is None:
        return "you have not got what %s is made of" % one
    if not things.clean_name(r.get("name")) or not isinstance(r.get("purpose"), str):
        return "it needs a name and a purpose"
    if len(things.on_floor(room)) >= cfg["make"]["crowded"] and not rec["store"]:
        return "this room is too crowded for another thing, unless it is something to keep things in"
    if rec["wall"] and not things.wall_slot(house, room):
        return "there is no free place on the wall here to hang it"
    if pet["needs"]["energy"] < cfg["make"]["tired"]:
        return "you are too tired to make anything"
    return None


def make(house, cfg, pet, a, clean):
    """One more of a kind the house invented, from its recipe: the same parts, of the same natures."""
    r, room = a["recipe"], house["rooms"][pet["room"]]
    rec = house["invented"][r["kind"]]
    used = stuff(cfg, rec, pet["carrying"])
    for b in used:
        pet["carrying"].remove(b)
    name = things.unique_name(house, cfg, things.clean_name(r["name"]))
    recipe = {"name": name, "kind": rec["name"], "material": rec["material"], "color": r["color"] if r.get("color") in things.COLORS else rec["parts"][0]["color"],
              "size": 3 if rec["size"] == "large" else min(things.as_size(r.get("size", 2)) or 2, 2), "purpose": clean(r["purpose"], 80)}
    house["n"]["thing"] += 1
    o = {"pos": things.wall_slot(house, room) if rec["wall"] else things.spot_for(house, cfg, pet, a.get("near")), **({"wall": True} if rec["wall"] else {}),
         "made": {"id": house["n"]["thing"], "recipe": recipe, "by": pet["id"], "owner": pet["id"], "tick": house["tick"], "bits": used, "uses": 0, "ups": 0,
                  "used_at": house["tick"], "heirloom": None, "behavior": None, "fine": craft.skill(cfg, pet, "making")}}
    if things.prop(cfg, o).get("light"):
        o["state"] = "on"
    room["objects"][name] = o
    pet["made"] += 1
    pet["last_made"] = {"tick": house["tick"], "kind": rec["name"], "material": rec["material"], "new": False}
    pet.setdefault("made_at", []).append([house["tick"], "%s|%s" % (rec["name"], rec["material"])])
    craft.practise(house, cfg, pet, "making")
    moment(house, "made", "%s made %s it calls '%s'" % (label(pet), things.a_thing(cfg, recipe), name), pet["id"], room["id"])
    firsts.made(house, cfg, pet, o, room)   # SPEC-v3.5.4 §6, §7, §10
    return "you made %s and called it %s, from %s, the way you know%s" % (things.a_thing(cfg, recipe), name, " and ".join(sorted(set(used))), "; it hangs on the wall" if rec["wall"] else ""), \
        {"energy": -(cfg["make"]["effort"] + len(used))}, "make " + rec["material"]


# ---- what a use does in the house (§3.0), each by a rule the house already had ----

def used(house, cfg, pet, room, name):
    """A pet uses a thing whose use has something of its own to do (things.use): (what it is told, effects, novelty
    key), or None for the ordinary way of using a thing."""
    from . import songs
    from .actions import bump, handle
    o, tick = room["objects"][name], house["tick"]
    E = effect(cfg, o)
    if not E:
        return None
    planted = [n for n, x in room["objects"].items() if x.get("planted") and not x["planted"].get("wilted") and x["planted"]["grow"] < 1]
    if E.get("waters") and planted:   # a pourer: water carried to everything planted here
        for n in planted:
            craft.water(house, cfg, pet, room, n)
        return "you carried water round in the %s: what is planted here has had its drink (%s)" % (name, ", ".join(planted)), {}, "tend"
    known = max(pet.get("songs", []), key=lambda e: e.get("last", e["since"]), default=None)
    if E.get("plays") and known and known["id"] in songs.book(house):   # an instrument: a tune it knows, heard and picked up like a song sung
        s = songs.book(house)[known["id"]]
        known["last"] = tick
        craft.practise(house, cfg, pet, "music", 0.5)
        songs.heard(house, cfg, room, known["id"], pet["id"], lambda p: "you hear %s playing the %s:" % (handle(house, p, pet), name))
        room["sounding_until"] = tick + ticks(cfg, 90)
        return 'you played "%s" on the %s: %s' % (s["name"], name, songs.sound(s["notes"])), dict(things.prop(cfg, o).get("use", {})), "play " + songs.root(house, known["id"])
    R = E.get("reaches")
    if R and room["type"] == R["room"] and room.get("shelf", 0) <= tick:   # a reacher: what lies on the high shelf, now and then
        bit = rnd(house, "shelf", room["id"], tick).choice(bit_kinds(house, cfg))
        room["shelf"] = tick + hours(cfg, R["hours"])
        craft.give(house, cfg, pet, room, bit)
        pet["got"] = [bit, tick]
        return "you hooked something down from the high shelf with the %s, where no paw reaches: some %s" % (name, bit), {"curiosity": cfg["craft"]["knowing"]["lift"]}, "reach"
    S = E.get("sails")
    if S and room["type"] == S["room"]:   # a boat, on the water
        return "you set the %s on the water and watched it go where the pond took it" % name, {"curiosity": S["curiosity"]}, "sail " + name
    if E.get("rolls"):   # a rolling toy: it rings as it goes, and kin here are drawn to it
        room["sounding_until"] = tick + ticks(cfg, 30)
        for p in house["pets"].values():
            if p["room"] == room["id"] and p["id"] != pet["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                add_event(house, p, "%s set the %s rolling: it rings as it goes, and you want to go after it" % (handle(house, p, pet), name))
                bump(p, cfg, {"curiosity": E["rolls"]["curiosity"]})
                pet.setdefault("played_with", {})[p["id"]] = tick
        return "you set the %s rolling, and it rang as it went" % name, dict(things.prop(cfg, o).get("use", {})), "roll " + name
    return None


def follow(house, cfg, room, name, o):
    """A thing that goes where its owner goes (a carried light, a cart): from this room to the one its owner is in,
    with whatever is kept on it. Not while it is put away, hung up or left to someone, nor while its owner sleeps."""
    owner = house["pets"].get(o["made"]["owner"])
    if not owner or owner["stage"] in ("egg", "dead") or owner["sleep"] or owner["room"] == room["id"] or o.get("on") or o.get("wall") or o["made"].get("heirloom"):
        return
    to = house["rooms"][owner["room"]]
    for n in [name] + [n for n, x in room["objects"].items() if x.get("on") == name]:
        to["objects"][n] = room["objects"].pop(n)
    for s in [s for s in room["spots"] if s.get("on") == name]:
        room["spots"].remove(s)
        to["spots"].append(s)
    for k in ("home", "places"):
        o.pop(k, None)
    o["pos"] = free_tile(house, cfg, to, owner["pos"], name)
    for x in [x for x in list(to["objects"].values()) + to["spots"] if x.get("on") == name]:
        x["pos"] = list(o["pos"])
    add_event(house, owner, "your %s came in with you" % name)


def tick(house, cfg):
    """Each tick (Engine.tick): what invented things do by themselves. A thing that follows goes after its owner;
    by the hour a chime sounds in wind and rain, and in the garden tells whoever is there tomorrow's weather, once a
    day; creatures stay by a feeder, come to trust whoever set it out, and now and then one is drawn to it."""
    from . import director
    if not any(k in USES.get(v["use"], {}).get("effect", {}) for v in house.get("invented", {}).values() for k in ("follows", "wind", "feeds")):
        return   # (nothing in the house does anything by itself)
    hourly, now = house["tick"] % max(1, round(cfg["ticks_per_hour"])) == 0, house["tick"]
    for room in [r for r in house["rooms"].values() if r["type"]]:
        for name, o in list(things.made(room).items()):
            E = effect(cfg, o)
            if E.get("follows") and name in room["objects"]:
                follow(house, cfg, room, name, o)
            if not hourly:
                continue
            awake = [p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]]
            if E.get("wind") and room["type"] == "garden":
                if house["weather"] in E["wind"]:
                    room["sounding_until"] = now + ticks(cfg, 60)
                if awake and o["made"].get("told") != house["clock"]["day"]:
                    o["made"]["told"] = house["clock"]["day"]
                    sky = weather_of(house, cfg, house["clock"]["day"] + 1)
                    for p in awake:
                        add_event(house, p, "the %s moves in the air in a way you are coming to know: %s" % (name, {
                            "rain": "rain tomorrow", "storm": "a storm tomorrow", "snow": "snow tomorrow", "heat": "a hot, still day tomorrow"}.get(sky, "fair weather tomorrow")))
            F, owner = E.get("feeds"), house["pets"].get(o["made"]["owner"])
            if F:
                wild = [c for c in house["creatures"] if not c.get("tame")]
                r = rnd(house, "feeder", o["made"]["id"], now)
                if not any(c["room"] == room["id"] for c in wild) and wild and r.random() < F["drawn"]:
                    c = r.choice(wild)
                    c["room"], c["pos"] = room["id"], free_tile(house, cfg, room, o["pos"])
                    director.seen(house, cfg, c, "a %s has come in, to the %s" % (c["kind"], name))
                for c in [c for c in wild if c["room"] == room["id"]]:
                    c["until"] = max(c["until"], now + hours(cfg, F["hours"]))
                    if owner and owner["stage"] not in ("egg", "dead") and director.arrived(house, "taming"):
                        director.trusts(c, owner, cfg["taming"]["fed"] * F["trust"])
                        director.tameness(house, cfg, c)


# ---- what makes inventing come up (§0: at least one a world day), without telling anyone what to make ----

def want(house, cfg, pet, add):
    """One thing to want (wants.candidates): two things here that it may join, which nobody in the house has joined
    before and which together would be good for something (they fit a use: it is not told which). It wants to find
    out what would come of them; what it is called, and whether it joins them at all, is its mind's to say."""
    from . import life, order
    room = house["rooms"][pet["room"]]
    if "combine" not in life.actions_of(pet["stage"]) or today(house, cfg) >= cfg["invent"]["per_day"]:
        return
    free = [(n, o) for n, o in things.made(room).items() if things.free_to_change(house, pet, o) and not o["made"].get("heirloom") and not order.cap(cfg, o)
            and not cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("tool")]
    seen = {v["key"] for v in house.get("invented", {}).values()}
    for (n1, a), (n2, b) in itertools.combinations(free, 2):
        made = built(cfg, [a, b]) if key_of([a["made"]["recipe"], b["made"]["recipe"]]) not in seen else None
        if made and made[0] != "curio":
            mine = lambda o: "your" if o["made"]["owner"] == pet["id"] else "the"
            return add("join", "%s|%s" % tuple(sorted((n1, n2))), "you want to find out what would come of joining %s %s and %s %s into one thing: something tells you they would be good for more together" % (mine(a), n1, mine(b), n2),
                       "found out what comes of joining two things", cfg["invent"]["want"], a=n1, b=n2, room=room["id"])


def want_met(house, pet, w):
    """Has it joined two things since it began to want to? (If the two are no longer there, the want is gone: KeyError.)"""
    objs = house["rooms"][w["room"]]["objects"]
    return pet.get("joined", LONG_AGO) > w["since"] or not (objs[w["a"]] and objs[w["b"]])
