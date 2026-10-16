"""The vending machine (SPEC-v3.5 §4.3): a fixture of the storeroom that hands out the six base materials (two a
world day to each pet, free, of its choosing) and takes made things and bits back for a material in return. Its
stock is the house's, limited, topped up a little every morning and by the visitor. What it holds and what it gives
for what is data (machine.toml; the materials and what can be done to them are in crafting.toml). No model is asked:
a mind may take from it or feed it when it stands in its room, a body does both by itself for the sake of a want, and
the other modules call in here with a line each."""
import tomllib
from collections import Counter

from . import craft, order, things, works
from .world import a as a_bit
from .world import LONG_AGO, add_event, beside, days as world_days, dist, free_tile, label, moment, ticks

ACTIONS = ("machine_take", "machine_feed")   # what a mind can decide, at the machine
DOS = ("vend", "feed")                       # what a body does by itself (activities.toml)
GROUPS = {"peek": "machine", "feed": "machine"}   # the wants that are the machine's own (wants.py)
ORDERLY, SERVED, ONE = ("feed",), ("peek", "feed"), ("plank", "plate")
BUSY = {"machine_take": "getting something from the machine", "machine_feed": "feeding the machine"}
WRITTEN = {   # how a mind is told of the two (brains/model.py)
    "machine_take": '{"type": "machine_take", "what": one of the materials the machine holds} (it drops into your paws; the machine gives you two a day)',
    "machine_feed": '{"type": "machine_feed", "what": a made thing here that is yours to give up, or "bits" (three of the bits you carry), "for": the material you want back for it} (the machine keeps what it is fed)',
}
COUNT = ["nothing more", "one more", "two", "three", "four"]


def load(cfg, directory):
    """machine.toml, laid into the config; its two steps take their time and their signs like any other."""
    T = tomllib.loads((directory / "machine.toml").read_text())
    cfg["machine"] = dict(T["machine"], returns=T["returns"])
    cfg["steps"].update(T["steps"])
    cfg["signs"].update(T["signs"])
    return cfg


def state(house, cfg):
    """The machine's stock: the house's own, whichever room it stands in. ponytail: one stock for the house, so two
    storerooms would share it; a stock on each fixture is the upgrade."""
    M = cfg["machine"]
    return house.setdefault("machine", {"stock": {m: M["start"] for m in M["materials"]}, "used": LONG_AGO})


def spot(room):
    """The machine in this room: its name, or None."""
    return next((n for n, o in (room.get("objects") or {}).items() if o.get("fix", {}).get("machine")), None)


def found(house):
    """The room the machine stands in, if anyone has found it."""
    return next((r for r in house["rooms"].values() if r["type"] and spot(r)), None)


def known(house, pet):
    """The rooms it has been in."""
    return [house["rooms"][r] for r in pet["rooms"] if house["rooms"].get(r, {}).get("type")]


def home(house, pet):
    """The room with the machine, if this pet has been there."""
    return next((r for r in known(house, pet) if spot(r)), None)


def left(house, cfg, pet):
    """How many more it will give this pet today."""
    d = pet.get("machine") or {}
    return cfg["machine"]["free"] - (d.get("took", 0) if d.get("day") == house["clock"]["day"] else 0)


def has(house, cfg, pet, bit):
    """Is this something the machine could give it: one of its materials, in stock, in a room it knows?"""
    return state(house, cfg)["stock"].get(bit, 0) > 0 and home(house, pet) is not None


def light(house, cfg):
    """Its lights are up for a little while after it gives, takes or is stocked (the view draws `fix.<name>.lit`)."""
    return "lit" if house["tick"] - state(house, cfg)["used"] <= ticks(cfg, cfg["machine"]["lit_seconds"]) else None


def view(house, cfg):
    """For the page: what it holds and how much it can, or None while nobody has found it."""
    room = found(house)
    return {"stock": state(house, cfg)["stock"], "limit": cfg["machine"]["limit"], "materials": cfg["machine"]["materials"], "room": room["id"]} if room else None


def listed(names):
    return ", ".join(names[:-1]) + (" and " if names[1:] else "") + names[-1] if names else "nothing"


# ---- stock: the morning delivery, and the visitor ----

def fill(house, cfg, what, n):
    """Put up to n of a material in, never past its limit. Returns how many went in."""
    S, M = state(house, cfg), cfg["machine"]
    put = max(0, min(n, M["limit"] - S["stock"].get(what, 0)))
    S["stock"][what] = S["stock"].get(what, 0) + put
    return put


def morning(house, cfg):
    """director.begin calls this at dawn: the delivery puts a little of everything in, up to its limit."""
    room = found(house)
    if not room:
        return
    put = {m: fill(house, cfg, m, cfg["machine"]["restock"]) for m in cfg["machine"]["materials"]}
    put = {m: n for m, n in put.items() if n}
    if put:
        state(house, cfg)["used"] = house["tick"]
        moment(house, "stocked", "the morning delivery put %s in the machine" % listed(["%d %s" % (n, m) for m, n in put.items()]), None, room["id"])
        for p in house["pets"].values():
            if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                add_event(house, p, "the machine rattled: the morning delivery has put more in it")


def stock(house, cfg, cmd):
    """The visitor's "Stock the machine" (actions.visit): a material of their choice, or "all", up to its limit.
    Whoever is awake in its room is told. Returns an error string, or None."""
    room, M = found(house), cfg["machine"]
    what = cmd.get("what")
    if not room:
        return "nobody has found the machine yet"
    if what != "all" and what not in M["materials"]:
        return "the machine does not hold that"
    n = cmd.get("n", 1)
    put = sum(fill(house, cfg, m, M["limit"] if what == "all" else n if type(n) is int else 1) for m in (M["materials"] if what == "all" else [what]))
    if not put:
        return "the machine is full" if what == "all" else "the machine holds all the %s it can" % what
    said = "the visitor filled the machine" if what == "all" else "the visitor put %s in the machine" % what
    house["visitor_last"], state(house, cfg)["used"] = house["tick"], house["tick"]
    moment(house, "stocked", said, None, room["id"])
    for p in house["pets"].values():
        if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
            p["inbox"].append(said)
            p["news"].append("visitor")
    return None


def migrate(house, cfg):
    """A house lived in before the machine gains it on load (tick.alive_migration): the fixture in every storeroom
    already found, where the layout puts it, and its stock."""
    from . import world
    for room in [r for r in house["rooms"].values() if r["type"]]:
        new = [f for f in cfg["house"]["rooms"][room["type"]]["fixtures"] if f.get("machine") and f["name"] not in room["objects"]]
        for f in new:
            room["objects"][f["name"]] = world.fixture(f)
        if new:
            world.layout(cfg, room)
            world.settle(house, cfg, room)
    if found(house):
        state(house, cfg)


# ---- what it takes, and what it gives for it ----

def gives(cfg, props):
    """The materials it offers for something of these natures: soft gives fibre, hard wood or stone, noisy metal."""
    R = cfg["machine"]["returns"]
    return list(dict.fromkeys(m for p in props for m in R.get(p, []))) or list(R["other"])


def nature(house, cfg, o):
    """What a made thing is like: its material, the two that met in it if it came of a joining, and for a kind the
    house invented (not in the catalog) what its record and its parts say. Nothing here needs the kind to be known."""
    r = o["made"]["recipe"]
    inv = (house.get("invented") or {}).get(r.get("kind")) or {}
    mat = cfg["materials"].get(r.get("material"))
    met = mat.get("emerged", []) if isinstance(mat, dict) else []
    return [p for p in [r.get("material"), *met, *(inv.get("props") or []), *(x.get("material") for x in inv.get("parts") or [])] if p]


def offers(house, cfg, pet, room, what):
    """What it would give this pet for `what`: a made thing here, or "bits" (what it carries)."""
    if what == "bits":
        return gives(cfg, [p for b in pet["carrying"][:cfg["machine"]["bits"]] for p in cfg["house"]["bits"].get(b, {}).get("can", [])])
    return gives(cfg, nature(house, cfg, room["objects"][what]))


def leave(pet, name, o):
    """Has its owner given this pet leave: is the owner holding it out to it? ponytail: leave is an offer of the
    thing; asking for leave is the upgrade."""
    return next((off for off in pet.get("offers", []) if off["from"] == o["made"]["owner"] and off["kind"] == "give" and off.get("what") == name and not off.get("bit")), None)


def refuses(house, cfg, pet, room, name):
    """Why the machine will not take this from this pet, or None. Never an heirloom, a starred thing, a memorial
    stone, anything in a keepsake box, or what belongs to another living pet without that pet's leave."""
    o = room["objects"].get(name)
    if not o:
        return "that is not here"
    if "memorial" in o:
        return "the machine will not take a stone that stands for someone"
    if "made" not in o:
        return "the machine only takes made things and bits"
    if o["made"].get("heirloom"):
        return "the machine will not take an heirloom"
    if order.statue(name, o):   # SPEC-v3.5.4 §1
        return "the machine will not take a statue"
    if o["made"].get("star") is not None:   # SPEC-v3.5.4 §10
        return "the machine will not take a thing the visitor gave a star"
    if o.get("on") and order.keeps(room["objects"].get(o["on"], {})):
        return "the machine will not take what is kept in a keepsake box"
    if not things.free_to_change(house, pet, o) and not leave(pet, name, o):
        return "that belongs to someone else: the machine will not take it without their leave"
    if order.held(room, name) or o.get("planted"):
        return "there are things in it still"
    return None


def a_thing(cfg, recipe):
    """A fed thing in the story's words: "a soft nest" (the kind may be one the catalog has never heard of)."""
    words = "%s %s" % (recipe.get("material") or "", recipe.get("kind") or "thing")
    return "%s %s" % ("an" if words.strip()[0] in "aeiou" else "a", words.strip())


def got(house, cfg, pet, room, what):
    """What the machine gives is in its paws (beside it, if its arms are full), and it has held it now."""
    craft.give(house, cfg, pet, room, what)
    pet["got"] = [what, house["tick"]]
    if what not in pet["gathered"].setdefault(room["id"], []):
        pet["gathered"][room["id"]].append(what)


def take(house, cfg, pet, what):
    """One of a material out of the machine into its paws (beside it, if its arms are full)."""
    S, room = state(house, cfg), house["rooms"][pet["room"]]
    S["stock"][what] -= 1
    S["used"] = house["tick"]
    pet["machine"] = {"day": house["clock"]["day"], "took": cfg["machine"]["free"] - left(house, cfg, pet) + 1, "seen": house["tick"]}
    got(house, cfg, pet, room, what)
    moment(house, "machine", "%s took %s from the machine" % (label(pet), what), pet["id"], room["id"])
    more = left(house, cfg, pet)
    return "the machine clunked and dropped %s into your paws; it will give you %s today" % (a_bit(what), COUNT[more] if 0 <= more < len(COUNT) else "more"), dict(cfg["effects"]["gather"]), "machine " + what


def feed(house, cfg, pet, what, back, keep=False):
    """A made thing here, or three of the bits it carries, into the machine, and one of `back` out: into its paws
    (the stock does not change: what goes in is what comes out, as something else), or, when it has no use for it
    (`keep`: a body feeding the machine only to be rid of the thing), left in the machine for whoever comes next."""
    S, room, M, o = state(house, cfg), house["rooms"][pet["room"]], cfg["machine"], None
    if what == "bits":
        fed, said = pet["carrying"][:M["bits"]], "three bits"
        del pet["carrying"][:M["bits"]]
        told = "you fed %s to the machine" % listed(fed)
    else:
        o = room["objects"].pop(what)
        off, owner = leave(pet, what, o), house["pets"].get(o["made"]["owner"])
        if off:
            pet["offers"].remove(off)
        if owner and owner is not pet and owner["stage"] != "dead":
            add_event(house, owner, "%s fed your %s to the machine" % (label(pet), what))
        things.gone(house, o, what, "fed to the machine", room)
        said, told = a_thing(cfg, o["made"]["recipe"]), "you fed %s to the machine" % (what if what.startswith("the ") else "the " + what)
    S["used"], pet["fed"] = house["tick"], {"tick": house["tick"], "what": what, "day": house["clock"]["day"], "n": (pet.get("fed") or {}).get("n", 0) + 1}
    pet.setdefault("machine", {})["seen"] = house["tick"]
    scrap, fx = works.fed(house, cfg, pet, o)   # SPEC-v3.5.4 §8: scrap for the Works, and what helping fill it is worth
    if keep:
        fill(house, cfg, back, 1)
        moment(house, "fed", "%s fed %s to the machine and left the %s in it" % (label(pet), said, back), pet["id"], room["id"])
        return "%s; it whirred and clunked, and you left the %s it made of it in the machine%s" % (told, back, scrap), fx, "machine feed"
    got(house, cfg, pet, room, back)
    moment(house, "fed", "%s fed %s to the machine for %s" % (label(pet), said, back), pet["id"], room["id"])
    return "%s; it whirred, clunked, and dropped %s into your paws%s" % (told, a_bit(back), scrap), fx, "machine feed"


def scrap_back(house, cfg, pet, room, fed):
    """SPEC-v3.5.8 §4.1: scrap fed to the Works is broken down by what it was made of, and about every `scrap_back`
    pieces one base material comes back, into the paws of whoever fed it. What it was told, to add on."""
    M, S = cfg["machine"], pet.setdefault("scrap", {"n": 0, "of": []})
    gone = {g["name"]: g for g in house.get("gone_things", [])[-len(fed) - 4:]}
    for n in fed:
        g = gone.get(n)
        bits = (g or {}).get("bits") or []
        base = next((b for b in bits if b in M["materials"]), None) or next(iter(gives(cfg, [g["recipe"].get("material")] if g else [])), "wood")
        S["n"], S["of"] = S["n"] + 1, (S["of"] + [base])[-6:]
    if S["n"] < M["scrap_back"]:
        return ""
    back = Counter(S["of"]).most_common(1)[0][0]
    S["n"], S["of"] = S["n"] - M["scrap_back"], []
    got(house, cfg, pet, room, back)
    moment(house, "fed", "the Works broke down what %s fed it and gave it %s" % (label(pet), a_bit(back)), pet["id"], room["id"])
    return "; the Works broke down the scrap you have fed it and gave you %s" % ("a piece of " + back if back in ("wood", "stone", "metal", "clay") else a_bit(back))


# ---- a mind at the machine (actions.py, mind.py, the brains) ----

def feedable(house, cfg, pet, room):
    """{what it could feed the machine now: the materials it would get to choose from}."""
    out = {n: offers(house, cfg, pet, room, n) for n in things.made(room) if not refuses(house, cfg, pet, room, n)}
    if len(pet["carrying"]) >= cfg["machine"]["bits"]:
        out["bits"] = offers(house, cfg, pet, room, "bits")
    return out


def takeable(house, cfg, pet):
    S = state(house, cfg)
    return [m for m in cfg["machine"]["materials"] if S["stock"].get(m, 0) > 0] if left(house, cfg, pet) > 0 else []


def offered(house, cfg, pet, room):
    """The machine's actions a mind can take now: only in its room, and only what could be done."""
    if not spot(room):
        return []
    return (["machine_take"] if takeable(house, cfg, pet) else []) + (["machine_feed"] if feedable(house, cfg, pet, room) else [])


def ctx(house, cfg, pet):
    """What the two actions can name, for a brain's reply to be held to."""
    room = house["rooms"][pet["room"]]
    return {"take": takeable(house, cfg, pet), "feed": feedable(house, cfg, pet, room)} if spot(room) else None


def sense(house, cfg, pet):
    """One line for the packet, only in the machine's room: what it holds, and what it will do for this pet."""
    if not spot(house["rooms"][pet["room"]]):
        return []
    S, more = state(house, cfg), max(0, left(house, cfg, pet))
    return ["the machine here holds %s; it will give you %s today; fed a made thing, or three bits, it gives one back"
            % (listed([m for m in cfg["machine"]["materials"] if S["stock"].get(m, 0) > 0]), COUNT[more] if more < len(COUNT) else "more")] + works.sense(house, cfg, pet)   # SPEC-v3.5.4 §8


def schema(c, one):
    """The two actions as a brain may write them (brains/model.py): only what the packet's machine really offers."""
    m = c.get("machine") or {}
    return {"machine_take": [one("machine_take", what={"enum": m["take"]})] if m.get("take") else [],
            "machine_feed": [one("machine_feed", what={"const": w}, **{"for": {"enum": back}}) for w, back in (m.get("feed") or {}).items()]}


def stub(t, c, pick):
    """The scripted brain's use of the two."""
    m = c["machine"]
    if t == "machine_take":
        return {"type": t, "what": pick(m["take"])}
    what = pick(sorted(m["feed"]))
    return {"type": t, "what": what, "for": pick(m["feed"][what])}


def check(a, house, cfg, pet, norm):
    """None if the action can happen now, else why not."""
    room, M, S = house["rooms"][pet["room"]], cfg["machine"], state(house, cfg)
    what = norm(a.get("what"))
    if not spot(room):
        return "there is no machine here"
    if a.get("type") == "machine_take":
        if what not in M["materials"]:
            return "the machine does not hold that"
        if S["stock"].get(what, 0) <= 0:
            return "the machine has no %s left" % what
        return None if left(house, cfg, pet) > 0 else "the machine gives you nothing more today; something fed to it would get you one back"
    if what == "bits":
        if len(pet["carrying"]) < M["bits"]:
            return "the machine takes three bits for one thing back, and you do not carry three"
    else:
        why = refuses(house, cfg, pet, room, what)
        if why:
            return why
    back = offers(house, cfg, pet, room, what)
    return None if norm(a.get("for")) in back else "for that the machine offers %s" % " or ".join(back)


def apply(a, house, cfg, pet, norm):
    return take(house, cfg, pet, norm(a["what"])) if a["type"] == "machine_take" else feed(house, cfg, pet, norm(a["what"]), norm(a["for"]), bool(a.get("leave")))


def destination(house, cfg, pet):
    """Where it stands to use the machine: beside it."""
    room = house["rooms"][pet["room"]]
    at = room["objects"][spot(room)]["pos"] if spot(room) else None
    return None if not at or dist(pet["pos"], at) <= 1 else beside(cfg, at, pet["pos"])


# ---- wants (wants.py calls each of these with one line) ----

def source(house, cfg, pet, known, grown):
    """candidates asks this: the machine is where a base material is to be had when it is not lying about, or is
    short, in the rooms this pet knows: it is laid into `grown` (bit -> the machine's room), so every want that is
    about a bit can be about one of these. Returns the materials it is the source of."""
    at, M = home(house, pet), cfg["machine"]
    if not at or left(house, cfg, pet) <= 0:
        return set()
    S, here = state(house, cfg), house["rooms"][pet["room"]]
    lying = Counter(s["bit"] for r in known for s in r["spots"] if s["ready"] and not s.get("on"))
    via = {m for m in M["materials"] if S["stock"].get(m, 0) > 0 and lying[m] < M["short"] and not any(s["bit"] == m and s["ready"] and not s.get("on") for s in here["spots"])}
    grown.update({m: at["id"] for m in via})
    return via


def holds(house, pet, name):
    """The room it knows that a thing is in, or None."""
    return next((r for r in known(house, pet) if name in r["objects"]), None)


def spare(house, cfg, pet, room):
    """Its own things here that are spare. Lying about: nobody has touched it for `spare_days`, or the room has
    `spare_kind` or more of the kind and this one has lain a while. Put away on or in something: nobody has touched
    it for `stored_days` (one such a day from each pet: shelves are thinned, not emptied). The longest untouched
    first. (Never a tool, something that keeps things, what hangs on a wall, what the machine refuses, or what has
    only just been put down.) [(last touched, name, why: "old", "kept", or the kind there are too many of)]"""
    M, out = cfg["machine"], []
    fresh, loose = house["tick"] - ticks(cfg, cfg["order"]["just_out_seconds"]), set(order.loose(house, cfg, room))
    kinds = Counter(o["made"]["recipe"].get("kind") for o in things.made(room).values())
    today = (pet.get("fed") or {}).get("day") == house["clock"]["day"]
    clutter = order.clutter_of(house, cfg, room)   # SPEC-v3.5.4 §1: a cluttered room's old things, its own or nobody's, can go
    scrap = [(why, n) for why, n in order.scraps(house, cfg, room) if things.free_to_change(house, pet, room["objects"][n]) and not refuses(house, cfg, pet, room, n)
             and room["objects"][n].get("kept", LONG_AGO) <= fresh]   # SPEC-v3.5.8 §4: its old charms, and what nobody uses, are scrap for the Works
    out += [(order.last_touch(room["objects"][n]), n, "scrap " + why) for why, n in scrap]
    clutter = [n for n in clutter if n not in dict((n, 1) for _, n in scrap)]
    out += [(order.last_touch(room["objects"][n]), n, "clutter") for n in clutter
            if things.free_to_change(house, pet, room["objects"][n]) and room["objects"][n]["made"]["recipe"].get("kind") not in cfg["craft"]["tool"]
            and not refuses(house, cfg, pet, room, n) and room["objects"][n].get("kept", LONG_AGO) <= fresh]
    for n, o in things.made(room).items():
        if n in clutter or any(n == x for _, x in scrap):
            continue
        kind, kept = o["made"]["recipe"].get("kind"), bool(o.get("on")) and not o.get("wall")
        if not (n in loose or kept) or o["made"]["owner"] != pet["id"] or kind in cfg["craft"]["tool"] or order.cap(cfg, o) or o.get("kept", LONG_AGO) > fresh \
                or refuses(house, cfg, pet, room, n):
            continue
        idle = world_days(cfg, order.last_touch(o), house["tick"])
        why = ("kept" if idle >= M["stored_days"] and not today else None) if kept else "old" if idle >= M["spare_days"] else kind if kinds[kind] >= M["spare_kind"] and idle >= M["spare_kind_days"] else None
        if why:
            out.append((order.last_touch(o), n, why))
    return sorted(out)


def wants(house, cfg, pet, known, out, add, via):
    """candidates asks this, after everything about bits: a want the machine is the source for says so ("you want
    some clay from the machine in the storeroom"); a pet with nothing in its paws to make anything of wants to see
    what the machine has; and a spare thing of its own is wanted fed to it (the orderly lean that way)."""
    at, M = home(house, pet), cfg["machine"]
    if not at:
        return
    from .wants import a, some
    for c in out:
        bit = c.get("bit")
        if bit in via and (c.get("bit_room") if c.get("how") else c.get("room")) == at["id"]:
            if c["what"] == "get" and not c.get("how"):
                c["text"] = "you want %s from the machine in %s" % (some(bit), at["name"])
            elif c["what"] == "bit":
                c["text"] = "you want to know what %s is like in your paws (the machine in %s has some)" % (a(bit), at["name"])
    if len(pet["carrying"]) <= 1 and left(house, cfg, pet) > 0 and any(state(house, cfg)["stock"].values()):
        add("peek", str(house["clock"]["day"]), "you have little in your paws to make anything of: you want to see what the machine in %s has" % at["name"],
            "went to see what the machine had", M["peek_weight"], room=at["id"])
    named = {w.get("bit") for w in pet.get("wants", [])}
    mess = max(known, key=lambda r: len(order.loose_bits(r)))   # loose bits are fed three for one: where most of them lie (not while it carries a bit a want of its is about)
    if len(order.loose_bits(mess)) >= M["bits"] and not named & set(pet["carrying"]):
        add("feed", "bits %d" % (pet.get("fed") or {}).get("n", 0), "loose bits lie about in %s: you want to feed three of them to the machine%s" % (mess["name"], "" if at is mess else " in " + at["name"]),
            "fed three loose bits to the machine", M["feed_weight"] * (1.0 if mess is at else M["bits_weight"]), thing="bits", room=mess["id"])
    spares = sorted(((not why.startswith("scrap"), why != "clutter", why == "kept", t, n, why, r) for r in known for t, n, why in spare(house, cfg, pet, r)), key=lambda x: x[:5])[:2]   # scrap and clutter first, then what lies about, then what is put away
    for *_, n, why, r in spares:
        mine = "your" if r["objects"][n]["made"]["owner"] == pet["id"] else "the"
        if why.startswith("scrap"):   # SPEC-v3.5.8 §4
            text = "you have charms enough, and your old %s in %s is one too many" % (n, r["name"]) if why == "scrap charm" and mine == "your" else \
                "nobody keeps the %s in %s for anything" % (n, r["name"]) if why == "scrap charm" else "nobody has used %s %s in %s for days" % (mine, n, r["name"])
            add("feed", n, "%s: it could go to the Works%s as scrap, and the Works gives something back for scrap" % (text, "" if at is r else " in " + at["name"]),
                "fed the %s to the Works" % n, M["feed_weight"] * M["scrap_weight"] * (M["spring_weight"] if works.spring(house, cfg) else 1.0), thing=n, room=r["id"])
            continue
        if why == "clutter":   # SPEC-v3.5.4 §1
            add("feed", n, "%s is cluttered with old things: you want to take %s %s to the machine%s" % (r["name"], mine, n, "" if at is r else " in " + at["name"]),
                "fed the %s to the machine" % n, M["feed_weight"] * M["clutter_weight"], thing=n, room=r["id"])
            continue
        text = "nobody has touched your %s in %s for days" % (n, r["name"]) if why == "old" else "there are more %ss in %s than anyone needs" % (why, r["name"]) if why != "kept" else \
            "your %s has been %s in %s for days, and nobody has touched it" % (n, order.into(cfg, r, r["objects"][n]["on"]), r["name"])
        add("feed", n, "%s: you want to feed %s to the machine%s" % (text, "it" if why in ("old", "kept") else "your " + n, "" if at is r else " in " + at["name"]),
            "fed the %s to the machine" % n, M["feed_weight"] * (M["stored_weight"] if why == "kept" else 1.5 if r.get("mess") == 2 else 1.0), thing=n, room=r["id"])
    works.wants(house, cfg, pet, known, out, add)   # SPEC-v3.5.4 §8: the Works wants scrap


def met(house, cfg, pet, w):
    """Is a want of the machine's own met?"""
    if w["what"] == "peek":
        return (pet.get("machine") or {}).get("seen", LONG_AGO) >= w["since"]
    fed = pet.get("fed") or {}
    return fed.get("what") == w["thing"] and fed.get("tick", LONG_AGO) >= w["since"]


def possible(house, cfg, pet, w):
    """Can it still be had? The machine is where it was; the thing is still somewhere it knows, and still its to feed."""
    if not home(house, pet):
        return False
    if w["what"] == "peek":
        return True
    if w["thing"] == "bits":
        return len(pet["carrying"]) >= cfg["machine"]["bits"] or any(order.loose_bits(r) for r in known(house, pet))
    room = holds(house, pet, w["thing"])
    return bool(room) and refuses(house, cfg, pet, room, w["thing"]) is None


def lean(house, cfg, pet, out):
    """wants.lean asks this last: what its body leans toward for the machine's sake. `vend`: (the material to take,
    or None to see what there is; the want) when it stands in the machine's room; `feed`: (the thing, the want) when
    the thing is in the room with it; and the rooms to make for otherwise."""
    out["vend"] = out["feed"] = None
    at = home(house, pet)
    if not at:
        return
    here, S, M = house["rooms"][pet["room"]], state(house, cfg), cfg["machine"]
    ready = lambda r, bit: any(s["bit"] == bit and s["ready"] and not s.get("on") for s in r["spots"])
    for w in sorted(pet.get("wants", []), key=lambda w: w["what"] != "get"):
        t, bit = w["what"], w.get("bit")
        if t == "peek":
            if at is here:
                out["vend"] = out["vend"] or (None, w["key"])
            else:
                out["rooms"].add(at["id"])
        elif t == "feed" and w["thing"] == "bits":   # three in its paws, then to the machine
            lying = [r for r in [here] + known(house, pet) if order.loose_bits(r)]
            if len(pet["carrying"]) >= M["bits"] and at is here:
                out["feed"] = out["feed"] or ("bits", w["key"])
            elif len(pet["carrying"]) >= M["bits"]:
                out["rooms"].add(at["id"])
            elif lying and lying[0] is here:
                out["gather"] |= {s["bit"] for s in order.loose_bits(here)}
            elif lying:
                out["rooms"].add(lying[0]["id"])
        elif t == "feed":
            room = holds(house, pet, w["thing"])
            if room is here:
                out["feed"] = out["feed"] or (w["thing"], w["key"])
            elif room:
                out["rooms"].add(room["id"])
        elif bit in M["materials"] and t in ("bit", "get", "try", "plant"):
            need = 2 if cfg["craft"]["process"].get(w.get("how"), {}).get("pair") else 1
            if pet["carrying"].count(bit) >= need or S["stock"].get(bit, 0) <= 0 or left(house, cfg, pet) <= 0 or ready(here, bit):
                continue   # it has it, the machine cannot give it, or it lies here to be picked up
            if at is here:
                out["vend"] = out["vend"] or (bit, w["key"])
            elif not any(ready(r, bit) for r in known(house, pet)):
                out["rooms"].add(at["id"])


# ---- a body at the machine (body.py; the activities are in activities.toml) ----

def choose(house, cfg, pet, back):
    """Which of the materials on offer its body takes: one a want of its names, one it has never held, else the one
    there is most of."""
    S, had = state(house, cfg), wants_held(pet)
    return min(back, key=lambda m: (not wanted(pet, m), m in had, -S["stock"].get(m, 0)))


def wanted(pet, bit):
    return any(w.get("bit") == bit or w.get("gives") == bit for w in pet.get("wants", []))


def wants_held(pet):
    from .wants import held
    return held(pet)


def targets(house, cfg, pet, A, near):
    """What its body could do at the machine right now, for the sake of a want: [{what, goal, ...}], or []."""
    from . import body, wants as wants_
    L, W, room = wants_.lean(house, cfg, pet), cfg["body"]["want"] * 1.5, house["rooms"][pet["room"]]
    name = spot(room)
    if A["do"] == "vend":
        v = L["vend"]
        if not v or not name or bool(A.get("peek")) != (v[0] is None):
            return []
        return [{"what": v[0] or name, "want": v[1], "goal": near(room["objects"][name]["pos"]), "bonus": W}]
    f = L["feed"]
    if f and f[0] == "bits":
        return [{"what": "bits", "want": f[1], "goal": near(room["objects"][name]["pos"]), "bonus": W}] if name else []
    o = room["objects"].get(f[0]) if f else None
    if not o or any((body.state(p)["now"] or {}).get("what") == f[0] for p in house["pets"].values() if p is not pet and p["room"] == pet["room"] and p["stage"] not in ("egg", "dead")):
        return []   # (nothing to feed, or someone has it in their paws)
    door = None if name else body.way_to(house, pet, {home(house, pet)["id"]})
    if not name and (not door or house["shut"].get("%s|%s" % (room["id"], door), LONG_AGO) > house["tick"]):
        return []
    to = beside(cfg, room["objects"][name]["pos"], o["pos"]) if name else list(house["door_tiles"][door])   # to the machine; or to the door on the way to it
    return [{"what": f[0], "want": f[1], "door": door, "goal": near(o["pos"]), "to": to, "bonus": W}]


def finish(mind, now):
    """The activity is over: its body takes from the machine, feeds it, or carries the thing a room nearer to it.
    Returns (what it did in a few words or None if nothing came of it, effects, novelty key, the act for the view)."""
    from . import actions, story
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    room, M = h["rooms"][pet["room"]], cfg["machine"]
    if now["do"] == "vend":
        peek = bool(cfg["activities"][now["name"]].get("peek"))
        if not spot(room):
            return None, {}, None, None
        if peek:
            pet.setdefault("machine", {})["seen"] = h["tick"]
        can = [m for m in takeable(h, cfg, pet) if wanted(pet, m) or m not in wants_held(pet)]   # (having looked, it takes what a want of its is about, or what it has never held; else nothing)
        what = (choose(h, cfg, pet, can) if can else None) if peek else now["what"]
        a = {"type": "machine_take", "what": what}
        if not what or actions.check(a, h, cfg, pet, mind.mem):
            add_event(h, pet, "you looked over the machine: it holds %s" % listed([m for m in M["materials"] if state(h, cfg)["stock"].get(m, 0) > 0]))
            return ("looked over what the machine holds" if peek else None), {}, None, None
        if len(pet["carrying"]) >= cfg["make"]["carry"]:   # room in its arms: the first thing it carries that no want of its is about
            keep = {w.get("bit") for w in pet.get("wants", [])}
            put = next((x for x in pet["carrying"] if x not in keep), pet["carrying"][0])
            pet["carrying"].remove(put)
            things.drop_bits(h, cfg, room, pet["pos"], [put])
        act = story.act_of(h, pet, a)
        text, fx, key = actions.apply(h, cfg, pet, a, mind.mem)
        add_event(h, pet, text)
        return "took %s from the machine" % a_bit(what), fx, key, act
    name = now["what"]
    if name != "bits" and (name not in room["objects"] or refuses(h, cfg, pet, room, name)):
        return None, {}, None, None
    if name == "bits" and (not spot(room) or len(pet["carrying"]) < M["bits"]):
        return None, {}, None, None
    if spot(room):   # what it gives back it takes if a want of its is about that, or it has never held it; else it is left in the machine, where it is short
        back, S = offers(h, cfg, pet, room, name), state(h, cfg)
        mine = [m for m in back if wanted(pet, m) or m not in wants_held(pet)]
        a = {"type": "machine_feed", "what": name, "for": choose(h, cfg, pet, mine) if mine else min(back, key=lambda m: S["stock"].get(m, 0)), "leave": not mine}
        act = dict(story.act_of(h, pet, a), to=a["for"] if mine else None)
        text, fx, key = actions.apply(h, cfg, pet, a, mind.mem)
        more = [n for n, o in list(room["objects"].items()) if o.get("haul") == pet["id"] and not refuses(h, cfg, pet, room, n)]   # SPEC-v3.5.8 §4: what it carried along with it
        for n in more:
            feed(h, cfg, pet, n, min(offers(h, cfg, pet, room, n), key=lambda m: S["stock"].get(m, 0)), True)
        text += scrap_back(h, cfg, pet, room, ([] if name == "bits" or mine else [name]) + more)   # (a thing it fed for something of its choosing is paid for already)
        add_event(h, pet, text)
        return "fed %s to the machine%s" % ("three bits" if name == "bits" else listed([name] + more) if more else name if name.startswith("the ") else "the " + name,
                                            " for %s" % a_bit(a["for"]) if mine else ""), fx, key, act
    door = now.get("door")   # the machine is elsewhere: it and the thing go through the door toward it, and the thing is set down there
    if door not in room["doors"] or actions.check({"type": "go", "door": door}, h, cfg, pet, mind.mem):
        return None, {}, None, None
    along = [n for n, o in room["objects"].items() if o.get("haul") == pet["id"] and n != name]   # SPEC-v3.5.8 §4: a few at a time
    along += [n for why, n in order.scraps(h, cfg, room) if n != name and n not in along and things.free_to_change(h, pet, room["objects"][n])
              and not refuses(h, cfg, pet, room, n)][:cfg["make"]["haul"] - 1 - len(along)]
    moving = [(n, room["objects"].pop(n)) for n in [name] + along]
    text, fx, key = actions.go(h, cfg, pet, door)
    to = h["rooms"][pet["room"]]
    for n, o in moving:
        for k in ("on", "wall", "home", "places"):
            o.pop(k, None)
        o["pos"], o["kept"] = free_tile(h, cfg, to, pet["pos"], n), h["tick"]
        if n != name:
            o["haul"] = pet["id"]
        to["objects"][n] = o
        for m in [m for m in room.get("marks", []) if m["on"] == n]:   # what is written on a thing goes where the thing goes
            room["marks"].remove(m)
            to.setdefault("marks", []).append(m)
    said = listed([n for n, _ in moving]) if along else "the " + name
    add_event(h, pet, "you carried %s into %s, on the way to the machine" % (said, to["name"]))
    return "carried %s into %s" % (said, to["name"]), fx, key, None
