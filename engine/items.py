"""SPEC-v5.0 §1, §6 (helper A): every thing in the house is an item (contracts.item), with verbs from kinds.toml.

The item is a layer over the objects the house already has, not a replacement of them (the lead, DECISIONS Part 43):
its record lives at o["item"] on each made thing (o["made"]) and on each fixture kinds.toml gives an entry. Bits stay
in room["spots"]; `bits` reads them as stacks. An item's id is its made thing's id; a fixture's "fx:<room id>:<name>";
a bit stack's "bit:<room id>:<x>,<y>:<bit>".

Who owns what (one writer each; the owner's review, 20 October 2026):
  o["item"] owns   verbs, class, tier, quality, and all of state: wear, broken, charge, holds, on, lit. Written here
                   and in verbs.py only; a reader asks the item (`of`).
    holds          what made things are put on or in a container. `place` is the one writer of a thing's placement:
                   it writes the container's holds and the thing's o["on"] together (o["on"] is the mirror the v4
                   readers read; every v4 writer of it goes through `place`). A thing that leaves the room by another
                   way (eaten, taken apart, carried off) is dropped from holds by `sync`. Bits put by in a container
                   are not in holds: they stay spots, and a stack's `where` names the container.
    on, lit        a light's switch: `switch` writes them and o["state"] (the v4 mirror) together.
  o["made"] keeps  uses, ups, heirloom, star, title and name, and stays the writer of owner and maker (give, inherit,
                   theft, bequest write `made`). made.uses is the v4 count; item.state.wear is the wear.
  mirrors          the item's owner, maker, made, name, heirloom, star and where are read from made and the object by
                   `of` on every read and by `sync` every tick, and never written back.

What a verb does when it is used is engine/verbs.py's; what an item gives a room just by being there (light at
night, heat, cover on a sleeper) is read here (`strength`, `covered`) by whoever needs it. Switch: [items] on (on5)."""
import re
from collections import Counter

from . import contracts as K
from . import order, things
from .world import days as world_days, dist, free_tile, label, moment, power_on

WHO = "fx:"   # a fixture's id begins so


def T(cfg):
    return cfg["items5"]


def table(house, cfg, kind):
    """§1.3 (verbs, class, charge, parts, tier) for a made thing's kind: the catalog's; an invented kind's by its use
    and then by what the old design judge recorded it works at (the strongest strength a verb wins); a kind that is
    neither by a catalog kind (or one of a kind's `words`) in its name, the last word first ("simple hammer" is a
    hammer); else a keepsake. SPEC-v5.1 §3, with [grammar] on: the verbs and the tier are the parser's, of the kind's
    recipe (grammar.recipe); the class and the charge stay kinds.toml's (an invented kind's charge is its recipe's)."""
    e = T(cfg)["kind"].get(kind)
    inv = (house.get("invented") or {}).get(kind)
    if (e or inv) and K.on51(cfg, "grammar"):
        from . import grammar
        r = grammar.recipe(house, cfg, kind)
        if e:
            return r["verbs"], e.get("class", "plain"), dict(e.get("charge", {})), r["parts"], r["tier"]
        ch = next((c for c, x in T(cfg)["charge"].items() if r["charge"] in x["from"]), None) if r["charge"] else None
        return r["verbs"], "plain" if r["verbs"] else "keepsake", {ch: cfg["grammar"]["charge_full"]} if ch else {}, r["parts"], r["tier"]
    if e:
        return dict(e.get("verbs", {})), e.get("class", "plain"), dict(e.get("charge", {})), [], 0
    if inv:
        v = dict(T(cfg)["invented"]["use"].get(inv.get("use"), {}).get("verbs", {}))   # (v5.1: a use is {parts, verbs})
        for w in inv.get("works") or []:
            for verb, s in T(cfg)["invented"]["works"].get(w, {}).items():
                v[verb] = max(v.get(verb, 0), s)
        return v, "plain" if v else "keepsake", {}, [], 0
    for w in reversed(re.findall(r"[a-z]+", str(kind or "").lower())):
        k = w if w in T(cfg)["kind"] else next((k for k in T(cfg)["kind"] if w in cfg["kinds"].get(k, {}).get("words", ())), None)
        if k:
            return table(house, cfg, k)
    return {}, "keepsake", {}, [], 0


def entry(house, cfg, o, name):
    """(verbs, class, charge when full, parts, tier) for a made thing or a fixture, or None when it is not an item: a
    fixture with no entry, a site still being built, a stone. A built project's fixture does something only once built
    and sound. A fixture keeps kinds.toml's hand verbs and has no parts (SPEC-v5.1: the house's, not a recipe)."""
    if "made" in o:
        return table(house, cfg, o["made"]["recipe"].get("kind"))
    if "fix" not in o or "site" in o:
        return None
    if "project5" in o["fix"]:   # SPEC-v5.3 §2.3: a finished project does what its kind becomes (projects.finish)
        return dict(o["fix"].get("verbs5") or {}), "fixture", {}, [], 0
    b = o["fix"].get("built")
    e = T(cfg)["fixture"].get(b["project"] if b else name)
    if e is None:
        return None
    from . import build
    return (dict(e.get("verbs", {})) if not b or build.sound(o) else {}), e.get("class", "fixture"), dict(e.get("charge", {})), [], 0


def ident(room, name, o):
    return str(o["made"]["id"]) if "made" in o else "%s%s:%s" % (WHO, room["id"] if room else "", name)


def room_of(house, name, o):
    return next((r for r in house["rooms"].values() if r["type"] and r["objects"].get(name) is o), None) if name else None


def of(house, cfg, o, name=None, room=None):
    """API5: a made thing's or a fixture's item, made on first sight and kept at o["item"]; None for a thing that is
    not one. `room` (the room it is in) saves looking for it."""
    e = entry(house, cfg, o, name)
    if e is None:
        return None
    verbs, cls, full, parts, tier = e
    room = room or room_of(house, name, o)
    if not K.on51(cfg, "grammar"):
        tier = (o.get("item") or {}).get("tier", 0)
    old, m = o.get("item"), o.get("made") or {}
    if old is None:   # first sight: what the item owns is seeded from the object as it stands, once
        on = o.get("state") == "on" and "light" in verbs
        old = {"tier": 0, "quality": min(1.0, (m.get("fine") or 0) / 3),
               "state": {"wear": 0.0, "broken": False, "charge": full, "on": on, "lit": on,
                         "holds": [ident(room, n, x) for n, x in room["objects"].items() if x.get("on") == name] if room and name else []}}
    it = K.item(dict(mirrors(o, name, m), id=ident(room, name, o), kind=m["recipe"].get("kind") if m else name, verbs=verbs, tier=tier, parts=parts,
                     quality=old.get("quality", 0), state=old.get("state"), where=where_of(room, o), **{"class": cls}))
    if old.get("broke") is not None:   # (the tick it broke: a thing broken and unmended long enough is scrap, `tick`)
        it["broke"] = old["broke"]
    if o.get("item") is old and isinstance(old.get("state"), dict):   # (refreshed in place: whoever holds the item, or its state, holds this one)
        old["state"].clear()
        old["state"].update(it.pop("state"))
        it["state"] = old["state"]
        old.clear()
        old.update(it)
        return old
    o["item"] = it
    return it


def where_of(room, o):
    box = room["objects"].get(o.get("on") or "") if room else None
    return {"in": ident(room, o["on"], box)} if box is not None else {"room": room["id"] if room else None, "pos": list(o.get("pos") or [0, 0])}


def mirrors(o, name, m):
    """What the item mirrors from its made thing (never written back)."""
    return {"owner": m.get("owner"), "maker": m.get("by"), "made": m.get("tick"), "name": (m["recipe"].get("title") or name) if m else name,
            "heirloom": m.get("heirloom"), "star": m.get("star") is not None}


def place(house, cfg, room, name, o, to=None):
    """The one writer of where a thing is put: o["on"] and, while [items] is on, the holds of the container it leaves
    and of the one it goes on or in, together. `to` None takes it off what it was on. `room` is the room the
    containers stand in (where it was, for a thing on its way out)."""
    was = o.pop("on", None)
    if to:
        o["on"] = to
    if not K.on5(cfg, "items") or not room or was == to:
        return
    me = ident(room, name, o)
    for c, add in ((was, False), (to, True)):
        box = room["objects"].get(c or "")
        it = box is not None and of(house, cfg, box, c, room)
        if it:
            h = [i for i in it["state"]["holds"] if i != me]
            it["state"]["holds"] = h + [me] if add else h


def switch(o, it, on):
    """A light's switch: the item's on and lit, and o["state"] (the v4 mirror), together."""
    it["state"]["on"] = it["state"]["lit"] = on
    o["state"] = "on" if on else "off"


def sync(house, cfg):
    """Every tick while [items] is on: each item's mirrors refreshed from its made thing and object (so owner and maker
    agree after a gift, an inheritance, a theft), and what has left a container by a way that is not `place` (eaten,
    taken apart, carried off with the room's things) dropped from its holds."""
    if not K.on5(cfg, "items"):
        return
    for r in house["rooms"].values():
        if not r["type"]:
            continue
        for n, o in list(r["objects"].items()):   # (what was on a thing that has left the room is on the floor now: v5.1's bind made made things holders)
            if o.get("on") and o["on"] not in r["objects"]:
                place(house, cfg, r, n, o, None)
        here = {}
        for n, o in r["objects"].items():
            if o.get("on"):
                here.setdefault(o["on"], set()).add(ident(r, n, o))
        for n, o in list(r["objects"].items()):
            if "made" in o and "item" not in o:   # (a thing made since: its item now, so every made thing has one)
                of(house, cfg, o, n, r)
            it = o.get("item")
            if it:
                it.update(mirrors(o, n, o.get("made") or {}), where=where_of(r, o))
                if it["state"]["holds"]:
                    it["state"]["holds"] = [i for i in it["state"]["holds"] if i in here.get(n, ())]


def objects(house, cfg, room):
    """[(name, item)] for every item standing in a room (not its bits)."""
    room = house["rooms"][room] if isinstance(room, str) else room
    return [(n, it) for n, o in list(room["objects"].items()) for it in [of(house, cfg, o, n, room)] if it]


def bits(house, cfg, room):
    """API5: the room's loose bits as stacks, one item for each tile and kind, `n` the count (bits it grows are not
    items; what waits in a machine's tray is the machine's)."""
    room = house["rooms"][room] if isinstance(room, str) else room
    food, stacks = set(cfg["seasons"]["food"]["bits"]), {}
    for s in room["spots"]:
        if s.get("loose") and s.get("ready", True) and not s.get("machine"):
            k = (s["bit"], tuple(s["pos"]))
            stacks.setdefault(k, [0, s.get("on")])[0] += 1
    out = []
    for (bit, pos), (n, on) in sorted(stacks.items()):
        box = room["objects"].get(on or "")
        out.append(K.item({"id": "bit:%s:%d,%d:%s" % (room["id"], pos[0], pos[1], bit), "kind": bit, "material": bit, "n": n, "class": "food" if bit in food else "plain",
                           "where": {"in": ident(room, on, box)} if box is not None else {"room": room["id"], "pos": list(pos)}}))
    return out


def everything(house, cfg):
    """API5: [(room id, name, item)] for every item in the house, bit stacks included (a stack's name is its id)."""
    return [(r["id"], n, it) for r in house["rooms"].values() if r["type"] for n, it in objects(house, cfg, r) + [(b["id"], b) for b in bits(house, cfg, r)]]


def find(house, cfg, verb=None, kind=None, owner=None, room=None, working=True):
    """API5: [(room id, name, item)] that can do `verb` (working: now, not broken, not empty), of a kind, an owner's, in a room."""
    rid = room["id"] if isinstance(room, dict) else room
    rooms = [house["rooms"][rid]] if rid else [r for r in house["rooms"].values() if r["type"]]
    out = []
    for r in rooms:
        for n, it in objects(house, cfg, r) + ([(b["id"], b) for b in bits(house, cfg, r)] if verb is None else []):
            if (kind is None or it["kind"] == kind) and (owner is None or it["owner"] == owner) and (not working or not it["state"]["broken"]) \
                    and (verb is None or (K.works(it, verb) if working else verb in it["verbs"])):
                out.append((r["id"], n, it))
    return out


def best(house, cfg, room, verb, lit_only=False):
    """(name, item) of the strongest working item at a verb in a room, or (None, None)."""
    n, it = max(((n, it) for n, it in objects(house, cfg, room) if K.works(it, verb) and (not lit_only or lit(house, it))),
                key=lambda x: K.works(x[1], verb), default=(None, None))
    return n, it


def lit(house, it):
    """Is it lit now: switched on, and, for what runs on the house's power (no charge), the power on (a cut: things.light_on)."""
    return it["state"]["lit"] and (bool(it["state"]["charge"]) or power_on(house))


def strength(house, cfg, room, verb, lit_only=False):
    """API5: the strongest working item at a verb in a room (0 for none). `lit_only`: only what is lit now (a light)."""
    n, it = best(house, cfg, room, verb, lit_only)
    return K.works(it, verb) if n else 0.0


def covered(house, cfg, pet):
    """API5: 0..1, the cover on a hob where it lies: the strongest working thing with cover beside it (its bed's, a
    blanket's), on the floor (not put away, not on a wall)."""
    room = house["rooms"][pet["room"]]
    return max((K.works(it, "cover") for n, o in list(room["objects"].items()) if not o.get("on") and not o.get("wall") and dist(o.get("pos") or [99, 99], pet["pos"]) <= 1
                for it in [of(house, cfg, o, n, room)] if it), default=0.0)


def usable(cfg, o):
    """A tool as craft.py finds one: not broken, not empty (while [items] is on; a thing not yet seen as an item is)."""
    s = (o.get("item") or {}).get("state")
    return not (K.on5(cfg, "items") and s and (s.get("broken") or (s.get("charge") and not any(s["charge"].values()))))


BROKE = {"tool": "the handle's split", "glass": "the glass has cracked", "soft": "it's worn through", "fixture": "it's broken"}


def broke_words(it):
    return BROKE.get("fixture" if it["id"].startswith(WHO) else it["class"], "it's come apart")


def wear(house, cfg, it, uses=1):
    """API5 §1.5: a use's wear by its class ([items] wear; a fixture's slowest). Past 1.0 it is broken: True when this
    use broke it (counted, by kind)."""
    s = it["state"]
    if s["broken"]:
        return False
    W = cfg["items"]["wear"]
    f = min((K.grammar_data()["part"].get(p["part"], {}).get("wear", 1.0) for p in it.get("parts") or []), default=1.0) if K.on51(cfg, "grammar") else 1.0   # (SPEC-v5.1: a casing halves it)
    s["wear"] = round(min(1.5, s["wear"] + W.get("fixture" if it["id"].startswith(WHO) else it["class"], W["plain"]) * f * uses), 4)
    if s["wear"] <= 1.0:
        return False
    s["broken"], it["broke"] = True, house["tick"]
    K.count(house, "broke", it["kind"])
    return True


def scrap_value(cfg, it):
    """API5 §4.1: a bit 1 (a stack, one each); a broken thing 1; a keepsake with no verbs 1; a made thing 2-6 by its
    tier and quality."""
    if "n" in it:
        return it["n"]
    if it["state"]["broken"] or not it["verbs"]:
        return 1
    return min(6, 2 + 2 * it["tier"] + round(3 * it["quality"]))


# ---- §1.7 containers ----

def guard(house, pet, room, container):
    """A container's owner guards what is in it: the words when it is another living hob's, else None."""
    o = room["objects"].get(container) or {}
    owner = house["pets"].get((o.get("made") or {}).get("owner") or "")
    if owner and owner is not pet and owner["stage"] not in ("egg", "dead"):
        return "the %s is %s's and it's shut" % (container, label(owner))
    return None


def put(house, cfg, pet, name, container):
    """API5: a thing here, or a bit it carries, into a container it can reach. Returns what it is told."""
    room = house["rooms"][pet["room"]]
    c = room["objects"].get(container)
    if c is None or not order.cap(cfg, c):
        return "there is no %s here to put things in" % container
    no = guard(house, pet, room, container)
    if no:
        return no
    if name in pet["carrying"]:
        if order.bit_room(cfg, room).get(container, 0) <= 0:
            return "the %s is full" % container
        pet["carrying"].remove(name)
        room["spots"].append({"bit": name, "pos": list(c["pos"]), "ready": True, "back": None, "loose": True, "on": container, "since": house["tick"]})
        return "you put the %s %s" % (name, order.into(cfg, room, container))
    o = room["objects"].get(name)
    if not o or "made" not in o or name == container:
        return "there is no %s here to put away" % name
    if order.stores(cfg, room).get(container, 0) <= 0:
        return "the %s is full" % container
    return "you put the %s %s" % (name, order.put(house, cfg, pet, room, name, "on", container))


def take_out(house, cfg, pet, container, item_id):
    """API5: a thing (by its id or name) or one bit of a stack (by the stack's id or the bit) out of a container here."""
    room = house["rooms"][pet["room"]]
    no = guard(house, pet, room, container)
    if no:
        return no
    for n, o in room["objects"].items():
        if o.get("on") == container and item_id in (n, ident(room, n, o)):
            if "made" in o and not order.may_move(house, pet, o):
                return "the %s is someone else's" % n
            place(house, cfg, room, n, o)
            o["kept"], o["pos"] = house["tick"], free_tile(house, cfg, room, pet["pos"], n)
            o.setdefault("home", {"room": room["id"], "on": container})
            return "you took the %s out of the %s" % (n, container)
    s = next((s for s in room["spots"] if s.get("on") == container and (item_id == s["bit"] or (item_id.startswith("bit:") and item_id.endswith(":" + s["bit"])))), None)
    if s:
        from . import craft
        room["spots"].remove(s)
        craft.give(house, cfg, pet, room, s["bit"])
        return "you took a %s out of the %s" % (s["bit"], container)
    return "there is no such thing in the %s" % container


def stored_in(house, cfg, room, s, cls):
    """Is this bit (a spot) put by in a container of this class (cool: food keeps; store: the mouse can't get at it)?"""
    box = room["objects"].get(s.get("on") or "")
    it = box and of(house, cfg, box, s["on"], room)
    return bool(it) and it["class"] == cls and not it["state"]["broken"]


# ---- §1.5 a broken thing left unmended ----

def tick(house, cfg):
    """Once a world hour: a made thing broken and left unmended `[items] scrap_after_days` world days goes to the Works
    as scrap (works.scrap), with a moment."""
    if not K.on5(cfg, "items") or house["tick"] % max(1, round(cfg["ticks_per_hour"])):
        return
    from . import works
    for r in [r for r in house["rooms"].values() if r["type"]]:
        for n, o in list(things.made(r).items()):
            it = o.get("item") or {}
            if (it.get("state") or {}).get("broken") and world_days(cfg, it.get("broke", house["tick"]), house["tick"]) >= cfg["items"]["scrap_after_days"]:
                works.scrap(house, cfg, r, n, "broken and never mended: scrap for the Works")
                moment(house, "scrap", "the %s lay broken %d days and nobody mended it: it went to the Works as scrap" % (n, cfg["items"]["scrap_after_days"]), o["made"]["owner"], r["id"])


# ---- §6 the migration ----

def migrate(house, cfg):
    """API5 §6, once a house (house["migrated"]["v50_items"]): every made thing and every fixture with an entry gets
    its item; the invented kinds their verbs; every hob scrap 0; then the clear-out: made things with no verbs and no
    star, no title, no heirloom, unused `[items] clear_unused_days` world days, go to the Works as scrap in one go
    (what lies in a dead hob's keepsake box stays: it is the house's memory of it; fuel and food are spent, not kept,
    and stay). Returns the report's lines."""
    done = house.setdefault("migrated", {})
    if done.get("v50_items"):
        return []
    from . import works
    rooms = [r for r in house["rooms"].values() if r["type"]]
    kinds = lambda: Counter(o["made"]["recipe"].get("kind") for r in rooms for o in things.made(r).values())
    classes = lambda: Counter(o["item"]["class"] for r in rooms for o in things.made(r).values())
    before = kinds()
    for r in rooms:
        objects(house, cfg, r)
    cls_before, fixtures = classes(), sum(1 for r in rooms for o in r["objects"].values() if "item" in o and "made" not in o)
    inv = house.get("invented") or {}
    for k, rec in inv.items():
        rec["verbs"] = table(house, cfg, k)[0]
    for p in house["pets"].values():
        if isinstance(p.get("scrap"), dict):   # (v3.5.8's count of scrap fed to the Works had the key: machine.scrap_back keeps it as scrap_back)
            p["scrap_back"] = p.pop("scrap")
        p.setdefault("scrap", 0)
    cut, went, kept = cfg["items"]["clear_unused_days"], [], Counter()
    built = len(works.state(house, cfg)["built"])
    for r in rooms:
        for n, o in sorted(things.made(r).items()):
            m, box = o["made"], r["objects"].get(o.get("on") or "")
            if o["item"]["verbs"]:
                continue
            e = T(cfg)["kind"].get(m["recipe"].get("kind"), {})
            why = ("fuel or food" if e.get("fuel") or e.get("class") == "food" else "starred" if m.get("star") is not None else "titled" if m["recipe"].get("title") else "an heirloom" if m.get("heirloom")
                   else "in a keepsake box" if box is not None and order.keeps(box)
                   else "used lately" if world_days(cfg, max(m.get("used_at") or 0, m.get("touched") or 0, m["tick"]), house["tick"]) < cut else None)
            if why:
                kept[why] += 1
                continue
            works.scrap(house, cfg, r, n, "cleared out to the Works as scrap: it did nothing, and nobody had used it in %d days (v5.0)" % cut)
            went.append(n)
    if went:
        moment(house, "tidy", "the great sort: %d things that did nothing and nobody used went to the Works as scrap" % len(went), None, None)
    done["v50_items"] = house["tick"]
    after = kinds()
    words = lambda c: ", ".join("%s %d" % kv for kv in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))
    cat = lambda c: words(Counter({k: n for k, n in c.items() if k in T(cfg)["kind"]})) + "; other kinds %d" % sum(n for k, n in c.items() if k not in T(cfg)["kind"])
    took = {k: (before[k], after.get(k, 0)) for k in before if before[k] != after.get(k, 0)}
    return ["made things before: %d; by kind: %s" % (sum(before.values()), cat(before)),
            "made things after: %d; by kind: %s" % (sum(after.values()), cat(after)),
            "by class before: %s" % words(cls_before), "by class after: %s" % words(classes()),
            "the clear-out took: %s" % (", ".join("%s %d->%d" % (k, a, b) for k, (a, b) in sorted(took.items(), key=lambda kv: kv[1][1] - kv[1][0])) or "nothing"),
            "the clear-out: %d went to the Works as scrap, %d stayed (%d with verbs; of those with none, %s)"
            % (len(went), sum(after.values()), sum(after.values()) - sum(kept.values()), words(kept) or "none"),
            "fixtures that are items: %d; invented kinds given verbs: %d of %d (the rest keepsakes)" % (fixtures, sum(1 for v in inv.values() if v["verbs"]), len(inv)),
            "every hob's scrap: 0 (%d hobs)" % len(house["pets"])]\
        + ["the Works, fed the scrap, built: %s" % ", ".join(b["what"] for b in works.state(house, cfg)["built"][built:])] * (len(works.state(house, cfg)["built"]) > built)
