"""Things the pets invent (SPEC-v3.5 §3). Two things joined can be a kind nobody drew: the sturdier or larger gives its
base, the other its signature part on a spot the base has free, and what the new thing does is what both did (or
what emerged where they met), never what the picture shows. The pet names it; the house keeps the kind
(house["invented"]) with its parts, and it is a recipe like any other: known by its maker, handed on, lost when
nobody living knows it, found again by whoever joins the same two things. The part names, spots and limits are
data (view/assets/parts.json); the view draws from the same record. No model is asked anything here."""
import itertools
import json
from pathlib import Path

from . import craft, things
from .world import LONG_AGO, add_event, clock, label, moment

P = json.loads((Path(__file__).parent.parent / "view" / "assets" / "parts.json").read_text())
PART, RULES = P["thing"], P["rules"]


# ---- composition (§3.2, §3.4) ----

def kind_parts(cfg, kind):
    """(base part, signature part) of a kind: the catalog's, or an invented kind's own. None if it has none."""
    k, e = cfg["kinds"].get(kind) or {}, P["kinds"].get(kind)
    return (k["base"], k["signature"]) if k.get("invented") else (e["base"], e["signature"]) if e else None


def fit(base, tops):
    """A spot of the base for each top part, one that takes it and no two on one spot: [spot, ...], or None."""
    def place(i, used):
        if i == len(tops):
            return []
        for s in PART[base]["spots"]:
            rest = place(i + 1, used | {s}) if s in PART[tops[i]]["on"] and s not in used else None
            if rest is not None:
                return [s] + rest
        return None
    return place(0, frozenset())


def compose(cfg, x, y, emerged=False):
    """The parts of a thing built on x with y's signature part (x, y: two recipes): [{part, at, material, color}],
    or None if it cannot be put together, or would only be something the catalog already has. At most three parts;
    a part sits only on a spot the base has and the part can take; a second flame or blade is left off."""
    a, b = kind_parts(cfg, x.get("kind")), kind_parts(cfg, y.get("kind"))
    if not a or not b or a[0] not in PART or any(t not in PART for t in (a[1], b[1])):
        return None
    (base, own), given = a, b[1]
    if own == given and not emerged:
        return None   # the same part twice over shows nothing new
    tops = [(given, y)] if own == given and own in RULES["no_stack"] else [(own, x), (given, y)]
    spots = fit(base, [t for t, _ in tops])
    if spots is None and len(tops) > 1:   # no room for both: the base gives up its own part for the other's
        tops = tops[1:]
        spots = fit(base, [given])
    if spots is None or (len(tops) == 1 and not emerged and any(v["base"] == base and v["signature"] == given for v in P["kinds"].values())):
        return None
    look = lambda part, at, r: {"part": part, "at": at, "material": r["material"], "color": r.get("color", "grey")}
    return ([look(base, None, x)] + [look(t, s, r) for (t, r), s in zip(tops, spots)])[:RULES["max_parts"]]


def sturdier(cfg, olds):
    """The two things, the sturdier or larger first: its base is the base."""
    weight = lambda o: (things.size(o), bool(o["made"].get("sturdy")), cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("rank", 1))
    return sorted(olds, key=weight, reverse=True)


def built(cfg, olds, emerged=False):
    """(the parts, the base thing's recipe, the other's) for two things joined, or None."""
    x, y = [o["made"]["recipe"] for o in sturdier(cfg, olds)]
    return next(((parts, a, b) for a, b in ((x, y), (y, x)) for parts in [compose(cfg, a, b, emerged)] if parts), None)


def key_of(recipes):
    """The recipe of an invention: the two kinds, each in its material, whichever way round."""
    return "+".join(sorted("%s/%s" % (r.get("kind"), r["material"]) for r in recipes))


# ---- what it does (§3.2): from the engine's rules ----

def plus(a, b):
    """Two properties together: what each does, and where they say different things of the same matter, the second."""
    out = dict(a)
    for k, v in b.items():
        out[k] = plus(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def prop(cfg, rec):
    """What a thing of an invented kind does: the properties of both its parts, the nature it kept winning where
    they differ; where two properties met (v3.4 §3.2), what emerged, which is neither."""
    M, out = cfg["materials"], {}
    if M[rec["material"]].get("emerged"):
        return M[rec["material"]]
    for p in [p for p in rec["props"] if p != rec["material"]] + [rec["material"]]:
        out = plus(out, M[p])
    return out


def does(cfg, rec, base):
    """One short sentence of what it does, in the house's own words for each property, and what its base lets it do."""
    met = cfg["materials"][rec["material"]].get("emerged")
    says = [cfg["craft"]["meets"][frozenset(met)]["says"]] if met else [cfg["materials"][p]["says"].split(";")[0].split(":")[0] for p in rec["props"]]
    says = [s for s in says if not s.startswith("nothing")] or ["it just sits there"]
    return "; ".join(says + ["it hangs on the wall"] * bool(base.get("wall")) + ["it can be hung up"] * bool(base.get("hangs")) + ["it holds things"] * bool(base.get("store")))


def as_kind(cfg, rec):
    """An invented kind as the catalog would have it, so everything that asks what a kind is gets an answer: where
    it goes, what it holds, what it is built on, and what it does."""
    base = cfg["kinds"].get(rec["from"][0], {})
    return {"invented": True, "a": rec["a"], "not": [], "rank": min(3, base.get("rank", 1) + 1), "wall": rec["wall"], "hangs": rec["hangs"], "store": rec["store"],
            "inside": bool(rec["store"] and base.get("inside")), "furniture": bool(base.get("furniture")), "from": rec["from"],
            "base": rec["parts"][0]["part"], "signature": rec["parts"][-1]["part"], "prop": prop(cfg, rec)}


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
    """Two things are being joined (things.combine). The name of the invented kind that comes of it, or None for the
    larger kind as before. New: a recipe the house has not seen, and either something emerged or the mind's name and
    purpose are neither part's. A joining that only repeats one of the house's inventions makes that kind."""
    pet["joined"] = house["tick"]
    recs, inv = [o["made"]["recipe"] for o in olds], house.setdefault("invented", {})
    key, name, purpose = key_of(recs), things.clean_name(r.get("name")), r["purpose"].strip().lower()
    again = next((n for n, v in inv.items() if v["key"] == key), None)
    made = None if again else built(cfg, olds, bool(meets))
    props = list(dict.fromkeys([x["material"] for x in made[1:]] + ([meets["name"]] if meets else []))) if made else []
    again = again or next((n for n, v in inv.items() if made and [(p["part"], p["at"]) for p in v["parts"]] == [(p["part"], p["at"]) for p in made[0]] and v["props"] == props), None)
    if again:   # ... and whoever did it knows how now (if nobody living did, it is found again)
        craft.learn(house, cfg, pet, "kind:" + again)
        if meets:   # (where nothing emerged, it is told what kind it is as the joining is: things.combine)
            add_event(house, pet, said(house, again))
        return again
    taken = set(cfg["kinds"]) | set(inv) | set(cfg["house"]["bits"]) | {x.get("kind") for x in recs} | {x["name"] for x in recs}
    own = name and name not in taken and purpose and purpose not in [x.get("purpose", "").strip().lower() for x in recs]
    if not made or not name or name in taken or not (meets or own) or (recs[0].get("kind") == recs[1].get("kind") and not meets) or today(house, cfg) >= cfg["invent"]["per_day"]:
        return None
    parts, x, y = made
    base = cfg["kinds"].get(x.get("kind"), {})
    rec = inv[name] = {"name": name, "a": "an" if name[0] in "aeiou" else "a", "parts": parts,
                       "size": "large" if base.get("furniture") or max(things.size(o) for o in olds) >= 3 else "small", "from": [x.get("kind"), y.get("kind")],
                       "props": props, "material": meets["name"] if meets else r["material"], "wall": bool(base.get("wall")), "hangs": bool(base.get("hangs")),
                       "store": base.get("store", 0), "by": pet["id"], "tick": house["tick"], "key": key}
    does_ = prop(cfg, rec)
    # ponytail: parts.json says which parts sound, not how loud: the part given first, then the base's own, then the
    # base. A `loud` number on each part is the upgrade.
    sound = next((PART[p["part"]]["sound"] for p in parts[:0:-1] + parts[:1] if PART[p["part"]].get("sound")), None)
    rec.update(does=does(cfg, rec, base), sound=sound if does_.get("loud") else None, glow=bool(does_.get("light")))
    cfg["kinds"][name] = as_kind(cfg, rec)
    pet.setdefault("recipes", {})["kind:" + name] = {"tick": house["tick"], "from": "found"}
    house.setdefault("recipes", {})["kind:" + name] = {"by": pet["id"], "tick": house["tick"]}
    craft.found(house, pet, "%s invented the %s: %s" % (label(pet), name, " ".join(r["purpose"].split())[:80]), "invented")
    if meets:
        add_event(house, pet, said(house, name))
    return name


def said(house, name):
    """What the pet is told of the kind that came of its joining, or "" if nothing did."""
    rec = house.get("invented", {}).get(name)
    if not rec:
        return ""
    if rec["tick"] == house["tick"]:
        return "nobody in the house has made the like of the %s: it is a new kind of thing (%s), and you know how it is made" % (name, rec["does"])
    return "it is %s %s, like the one %s first made" % (rec["a"], name, label(house["pets"][rec["by"]]) if rec["by"] in house["pets"] else "someone")


def words(cfg, kind):
    """The recipe in plain words (craft.words)."""
    frm = cfg["kinds"].get(kind, {}).get("from")
    one = lambda k: "%s %s" % (cfg["kinds"].get(k, {}).get("a", "a"), k)
    return "%s can be made by joining %s and %s" % (one(kind), one(frm[0]), one(frm[1])) if frm else "%s can be made" % one(kind)


# ---- made again from its recipe (§3.3) ----

def stuff(cfg, rec, carrying):
    """The bits it carries that an invented kind is made of: one for the nature of each of its parts. None if it lacks any."""
    need = list(dict.fromkeys(p["material"] for p in rec["parts"]))
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
    recipe and carries what it is made of, under the first of its parts' natures that is within reach."""
    out = {m: [k for k in ks if not cfg["kinds"].get(k, {}).get("invented")] for m, ks in kinds.items()}
    for name, rec in house.get("invented", {}).items():
        m = next((p["material"] for p in rec["parts"] if p["material"] in out), None)
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
    return "you made %s and called it %s, from %s, the way you know%s" % (things.a_thing(cfg, recipe), name, " and ".join(sorted(set(used))), "; it hangs on the wall" if rec["wall"] else ""), \
        {"energy": -(cfg["make"]["effort"] + len(used))}, "make " + rec["material"]


# ---- what makes inventing come up (§0: at least one a world day), without telling anyone what to make ----

def want(house, cfg, pet, add):
    """One thing to want (wants.candidates): two things here that it may join, which nobody in the house has joined
    before and which would go together. It wants to find out what would come of them; what, and what it is called
    and for, is its mind's to say."""
    from . import life, order
    room = house["rooms"][pet["room"]]
    if "combine" not in life.actions_of(pet["stage"]) or today(house, cfg) >= cfg["invent"]["per_day"]:
        return
    free = [(n, o) for n, o in things.made(room).items() if things.free_to_change(house, pet, o) and not o["made"].get("heirloom") and not order.cap(cfg, o)
            and not cfg["kinds"].get(o["made"]["recipe"].get("kind"), {}).get("tool")]
    seen = {v["key"] for v in house.get("invented", {}).values()}
    for (n1, a), (n2, b) in itertools.combinations(free, 2):
        ra, rb = a["made"]["recipe"], b["made"]["recipe"]
        if ra.get("kind") != rb.get("kind") and key_of([ra, rb]) not in seen and built(cfg, [a, b]):
            mine = lambda o: "your" if o["made"]["owner"] == pet["id"] else "the"
            return add("join", "%s|%s" % tuple(sorted((n1, n2))), "you want to find out what would come of joining %s %s and %s %s into one thing" % (mine(a), n1, mine(b), n2),
                       "found out what comes of joining two things", cfg["invent"]["want"], a=n1, b=n2, room=room["id"])


def want_met(house, pet, w):
    """Has it joined two things since it began to want to? (If the two are no longer there, the want is gone: KeyError.)"""
    objs = house["rooms"][w["room"]]["objects"]
    return pet.get("joined", LONG_AGO) > w["since"] or not (objs[w["a"]] and objs[w["b"]])
