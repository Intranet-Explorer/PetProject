"""SPEC-v5.0 §1.2-1.6 (helper A): the sixteen verbs, each with its resolver, and using a thing by them: `apply`
replaces things.use while [items] is on (on5); `mend` and `refill` are a broken thing mended and an empty one filled.

`apply` checks what every verb checks (the item isn't broken, what it runs on isn't empty: the failure in the world's
words), hands the use to the verb's resolver, and then, for a use that did something, wears it by its class, spends
one of what it runs on, and counts the verb. A resolver does its verb's change to the world and returns (words, fx,
key) as things.use did; key None is a use that came to nothing, and wears and spends nothing. launch and bind are
reached by v5.1's parts (a tube with a spring, a cord). The nature tags stay as a small bonus (§1.4): half of what
things.use gave for the thing's stuff."""
from . import contracts as K
from . import craft, items, order, things
from .world import add_event, dist, label, moment, neighbours, power_on, rnd, ticks

NATURE = 0.5   # §1.4: what a thing's stuff gave when used (materials.toml `use`), now a bonus beside its verb's effect


def apply(house, cfg, pet, name, verb=None, target=None):
    """API5: using a thing (by a verb, else its strongest): (words, fx, key), as things.use was. A made thing with no
    verbs (a keepsake, food) is used as it always was (things.use); so is an invented thing whose use has a way of its
    own (invent.used: an instrument plays, a pourer waters), which then wears as any use does."""
    room = house["rooms"][pet["room"]]
    o = room["objects"][name]
    it = items.of(house, cfg, o, name, room)
    if it is None or (not it["verbs"] and verb is None):
        return things.use(house, cfg, pet, name) if "made" in o else ("you tried to use the %s; nothing came of it" % name, {}, None)
    verb = verb or max(it["verbs"], key=lambda v: (it["verbs"][v], -K.VERBS.index(v)))
    if verb not in it["verbs"]:
        return "you tried to %s with the %s; it isn't for that: %s" % (verb, name, "; ".join(K.VERB_WORDS[v] for v in it["verbs"]) or "it does nothing"), {}, None
    if it["state"]["broken"]:
        return "you tried the %s; %s" % (name, items.broke_words(it)), {}, None
    if not K.works(it, verb):
        return "you tried the %s; it's empty" % name, {}, None
    from . import invent
    own = invent.used(house, cfg, pet, room, name) if "made" in o else None
    words, fx, key = own or RESOLVE[verb](house, cfg, pet, room, name, o, it, target)
    if key is None:
        return words, fx, key
    if "made" in o:
        o["made"]["touched"] = o["made"]["used_at"] = house["tick"]
        if not own:
            for n, v in things.prop(cfg, o).get("use", {}).items():
                fx[n] = fx.get(n, 0) + v * NATURE
    return words + spent(house, cfg, pet, it, verb), fx, key


def spent(house, cfg, pet, it, verb):
    """After a use that did something: one of what it runs on spent, its wear, the count. Returns words to add."""
    ch = it["state"]["charge"]
    m = next((m for m in sorted(ch) if ch[m] > 0), None)
    if m:
        ch[m] -= 1
    K.count(house, "verbs", verb)
    if items.wear(house, cfg, it):
        add_event(house, pet, "the %s broke as you used it: %s" % (it["name"], items.broke_words(it)))
        return "; and with that it broke: %s" % items.broke_words(it)
    return "; now it's empty" if m and not any(ch.values()) else ""


def worn(house, cfg, pet, room, name, verb=None):
    """craft.wear calls this while [items] is on: a tool used at its work (a carver at the bench, the hammer at a
    build, a rod at the pond) wears, spends and counts as a use of its strongest verb."""
    it = items.of(house, cfg, room["objects"][name], name, room)
    if it and it["verbs"] and not it["state"]["broken"]:
        spent(house, cfg, pet, it, verb if verb in it["verbs"] else max(it["verbs"], key=it["verbs"].get))


# ---- the resolvers: (house, cfg, pet, room, name, o, it, target) -> (words, fx, key) ----

def r_hold(house, cfg, pet, room, name, o, it, target):
    if target:
        said = items.put(house, cfg, pet, target, name)
        return said, {}, "hold" if said.startswith("you put") else None
    inside = [n for n, x in room["objects"].items() if x.get("on") == name] + sorted({s["bit"] for s in room["spots"] if s.get("on") == name})
    return ("you looked in the %s: %s" % (name, ", ".join(inside[:6]) if inside else "it's empty")), {}, None


def r_carry(house, cfg, pet, room, name, o, it, target):
    """§1.4: a carry tool makes tidying one trip: every loose bit here into what keeps things, at once."""
    loose, space = order.loose_bits(room), {n: k for n, k in order.bit_room(cfg, room).items() if k > 0 and n != name}
    if not loose:
        return "you looked about with the %s; nothing lies here to carry off" % name, {}, None
    if not space:
        return "there's nowhere here to carry the bits to: %s" % order.NOWHERE, {}, None
    took = {}
    for s in loose:
        to = next((n for n, k in space.items() if k > 0), None)
        if not to:
            break
        s["on"], s["pos"], space[to] = to, list(room["objects"][to]["pos"]), space[to] - 1
        took.setdefault(to, []).append(s)
    from . import season
    for to, ss in took.items():
        season.stored(house, cfg, pet, room, ss, to)
    craft.practise(house, cfg, pet, "tidying")
    return "with the %s you gathered up %d loose bits in one trip and put them %s" % (name, sum(map(len, took.values())), " and ".join(order.into(cfg, room, t) for t in took)), {}, "carry"


def r_cover(house, cfg, pet, room, name, o, it, target):
    s = K.works(it, "cover")
    return "you settled under the %s; it's warm" % name if s >= 0.5 else "you settled on the %s; it's softer than the floor" % name, {"comfort": 4.0 * s}, "cover " + it["kind"]


def r_light(house, cfg, pet, room, name, o, it, target):
    if it["state"]["on"]:   # (putting a light out is no use of it: nothing is spent)
        items.switch(o, it, False)
        return "you put out the %s" % name, {}, None
    if not it["state"]["charge"] and not power_on(house):
        return "you tried the %s; nothing happens, it stays dark" % name, {}, None
    items.switch(o, it, True)
    return "you lit the %s; the room is light" % name, {}, "light " + it["kind"]


def r_heat(house, cfg, pet, room, name, o, it, target):
    return "you fed the fire in the %s, and warmth spread through %s" % (name, room["name"]), {"comfort": 3.0 * K.works(it, "heat")}, "heat"


def r_pour(house, cfg, pet, room, name, o, it, target):
    planted = [n for n, x in room["objects"].items() if x.get("planted") and not x["planted"].get("wilted") and x["planted"]["grow"] < 1]
    if not planted:
        return "you tipped the %s; nothing here wanted water" % name, {}, None
    for n in planted:
        craft.water(house, cfg, pet, room, n)
    return "you poured water from the %s on what is planted here (%s)" % (name, ", ".join(planted)), {}, "pour"


def process(house, cfg, pet, how, bit):
    """A verb that is a process on a bit it carries (a cut is a carve, a dig or a grow a planting): craft's own, so
    the place, the skill and what comes of it are as they were."""
    a = {"type": "process", "how": how, "what": bit}
    why = craft.check_process(a, house, cfg, pet, lambda s: s)
    return (why, {}, None) if why else craft.process(house, cfg, pet, a, lambda s: s)


def r_cut(house, cfg, pet, room, name, o, it, target):
    if target in pet["carrying"]:
        return process(house, cfg, pet, "carve", target)
    return "you tried the edge of the %s; it's sharp, and there's nothing in your paws to cut" % name, {}, None


def r_strike(house, cfg, pet, room, name, o, it, target):
    if target and target in room["objects"] and target != name:
        said, ok = mend(house, cfg, pet, target)
        return said, {"energy": -cfg["make"]["effort"]} if ok else {}, "strike" if ok else None
    return "you knocked the %s against the floor; it rang, and nothing came of it" % name, {}, None


def r_dig(house, cfg, pet, room, name, o, it, target):
    if target in pet["carrying"]:
        return process(house, cfg, pet, "plant", target)
    return "you scraped at the ground with the %s; there's nothing in your paws to plant" % name, {}, None


r_grow = r_dig


def r_catch(house, cfg, pet, room, name, o, it, target):
    """§1.4 catch is fishing: one cast where there is water (the pond's own odds, as with a rod)."""
    from . import pond
    if room["type"] != "pond" or not pond.water(room):
        return "you held out the %s; there's no water here to fish in, and nothing to catch" % name, {}, None
    c = pond.roll(house, cfg, pet, True, False)
    craft.practise(house, cfg, pet, "fishing", 1.0 if c else 0.4)
    if not c or not c.get("bit"):
        return "you cast the %s into the water and waited; nothing came" % name, {}, "catch"
    if c.get("fish"):
        pond.state(house)["stock"] = round((pond.state(house)["stock"] or 0) - 1, 3)
    craft.give(house, cfg, pet, room, c["bit"])
    moment(house, "catch", "%s caught %s with the %s" % (label(pet), pond.things_a(c["what"]), name), pet["id"], room["id"])
    return "you cast the %s into the water and brought up %s" % (name, pond.things_a(c["what"])), {"curiosity": cfg["craft"]["knowing"]["lift"]}, "catch"


def r_mend(house, cfg, pet, room, name, o, it, target):
    if not target or target not in room["objects"]:
        return "the %s is for mending; there's nothing named to mend" % name, {}, None
    said, ok = mend(house, cfg, pet, target, part=name)
    return said, {"energy": -cfg["make"]["effort"]} if ok else {}, "mend" if ok else None


def r_signal(house, cfg, pet, room, name, o, it, target):
    """§1.4 signal is heard in the next rooms and is a notable."""
    room["sounding_until"] = house["tick"] + ticks(cfg, 60)
    heard = 0
    for rid in [room["id"]] + list(neighbours(house, room["id"]).values()):
        for p in house["pets"].values():
            if p["room"] == rid and p is not pet and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                add_event(house, p, "%s sounded the %s%s" % (label(pet), name, "" if rid == room["id"] else " in %s; you heard it through the wall" % room["name"]))
                heard += 1
    moment(house, "signal", "%s sounded the %s in %s" % (label(pet), name, room["name"]), pet["id"], room["id"])
    return "you sounded the %s; %s" % (name, "it carried through the house" if heard else "nobody was about to hear it"), {"curiosity": 1.0}, "signal"


def r_move(house, cfg, pet, room, name, o, it, target):
    return "you went over the %s and back; it holds" % name, {}, "move"


def r_launch(house, cfg, pet, room, name, o, it, target):
    """SPEC-v5.1 §3: a shot thrown at a thing or a creature (never a hob: v5.5) in this room or the next. What it
    throws is its charge (spent after, as any use's), else a pebble, a seed, a nut or a berry from its paws. A hit
    roll by its strength; then the shot's own verb on what it hit: it strikes (wears a thing, sends a creature off),
    or the launcher's net catches (a creature is carried out of the house)."""
    from . import director
    shot = None if it["state"]["charge"] else next((b for b in pet["carrying"] if b in K.CHARGE_LAUNCH), None)
    if not it["state"]["charge"] and not shot:
        return "you have nothing to throw with the %s: it takes %s" % (name, " or ".join(K.CHARGE_LAUNCH[:3])), {}, None
    rooms = [room] + [house["rooms"][r] for r in neighbours(house, room["id"]).values()]
    hob = next((p for p in house["pets"].values() if target and target in (p["id"], p.get("name"), label(p)) and p["stage"] not in ("egg", "dead")), None)
    if hob:
        return "you lowered the %s: you won't throw at %s" % (name, label(hob)), {}, None
    cr = next((c for r in rooms for c in house["creatures"] if c["room"] == r["id"] and (target in (c["kind"], c.get("name"), c["id"]) if target else not c.get("tame"))), None)
    at = None if cr else next(((r, target) for r in rooms if target and target in r["objects"] and target != name), None)
    if not cr and not at:
        return "you aimed the %s about; there was nothing %s to throw at" % (name, "called %s" % target if target else "here"), {}, None
    if shot:
        pet["carrying"].remove(shot)
    what = "a " + shot if shot else "a shot"   # (pebble, seed, nut, berry: none begins with a vowel)
    far = (cr["room"] if cr else at[0]["id"]) != room["id"]
    G = cfg["grammar"]
    if rnd(house, "launch", pet["id"], house["tick"]).random() >= G["hit"] + G["by_strength"] * K.works(it, "launch") - G["next_room"] * far:
        return "you threw %s from the %s at %s; it missed" % (what, name, director.called(cr, True) if cr else "the " + at[1]), {}, "launch"
    caught = any(p["part"] == "net" for p in it.get("parts") or [])
    if cr:
        if caught and not cr.get("tame"):
            director.leave(house, cr, "was caught in %s's net and carried out" % label(pet))
            return "the net from the %s fell over %s, and you carried it out of the house" % (name, director.called(cr, True)), {"curiosity": 1.0}, "launch"
        fled = director.chased(house, cfg, cr, pet)
        return "%s from the %s struck %s; %s" % (what.capitalize(), name, director.called(cr, True), "it fled" if "fled" in fled or "door" in fled else "it ran off"), {"curiosity": 1.0}, "launch"
    r, n = at
    t = items.of(house, cfg, r["objects"][n], n, r)
    broke = bool(t) and not caught and items.wear(house, cfg, t)
    return "%s from the %s %s the %s%s" % (what.capitalize(), name, "dropped over" if caught else "struck", n, ", and it broke" if broke else ""), {}, "launch"


def r_bind(house, cfg, pet, room, name, o, it, target):
    """SPEC-v5.1 §3: two things bound into one, a bundle: the second set on the first (items.place: they go
    together; taking it out unbinds it). `target` is "X and Y", or one thing, bound to what stands beside it. A hob
    is never bound (V5-DESIGN §9's harm rules are v5.5's)."""
    if any(target and target in (p.get("name"), label(p), p["id"]) for p in house["pets"].values()):
        return "you put the %s away: you won't tie anyone up" % name, {}, None
    names = [n.strip() for n in str(target or "").split(" and ")] if target else []
    ok = lambda n: n in room["objects"] and n != name and "made" in room["objects"][n] and not room["objects"][n].get("on") and things.free_to_change(house, pet, room["objects"][n])
    two = [n for n in names if ok(n)][:2]
    if len(two) == 1:
        p0 = room["objects"][two[0]]["pos"]
        two += [n for n in sorted(room["objects"]) if n not in two and ok(n) and dist(room["objects"][n].get("pos") or [99, 99], p0) <= 1][:1]
    if len(two) < 2:
        return "you held out the %s; there aren't two things of yours here to bind together" % name, {}, None
    a, b = two
    items.place(house, cfg, room, b, room["objects"][b], a)
    room["objects"][b]["made"]["bound"] = {"to": a, "with": name, "tick": house["tick"]}
    return "you bound the %s to the %s with the %s: they go together now" % (b, a, name), {}, "bind"


RESOLVE = {"hold": r_hold, "carry": r_carry, "cover": r_cover, "light": r_light, "heat": r_heat, "pour": r_pour, "cut": r_cut, "strike": r_strike,
           "dig": r_dig, "catch": r_catch, "mend": r_mend, "grow": r_grow, "signal": r_signal, "move": r_move, "launch": r_launch, "bind": r_bind}


# ---- §1.5 mending ----

# What a part of each family is (the lead's table); a thing's family is its stuff's (its bits'), else its nature's.
PARTS = {"soft": ("cloth", "felt", "string", "fluff"), "wood": ("wood",), "stone": ("pebble", "clay"), "metal": ("metal", "wire"), "glass": ("sand",)}
FAMILY = {**{b: "soft" for b in ("cloth", "felt", "string", "fluff", "feather", "moss", "leaf", "petal", "fibre", "rope", "vine cord", "wet cloth", "netting", "wicker")},
          **{b: "wood" for b in ("wood", "carved wood", "reed", "supple reed", "dry reed", "waterlogged wood", "charcoal", "tinder")},
          **{b: "stone" for b in ("pebble", "clay", "fired clay", "clay tile", "shell", "chalk", "mud brick", "fired brick", "mud", "sharp stone", "shell dust", "chalk dust")},
          **{b: "metal" for b in ("metal", "wire", "nail", "blade", "hinge", "chain", "hook", "spring")},
          **{b: "glass" for b in ("glass", "sand", "bead", "amber", "clear wax", "wax")}}
NATURE_FAMILY = {"soft": "soft", "bouncy": "soft", "quiet": "soft", "fragrant": "soft", "dark": "soft", "sweet": "soft", "warm": "wood", "hard": "wood",
                 "cool": "stone", "heavy": "stone", "noisy": "metal", "springy": "metal", "bright": "glass", "glassy": "glass"}


def family(o):
    """A thing's material family, for the part that mends it: its first bit with one, else its nature's; a fixture's wood."""
    m = o.get("made")
    if not m:
        return "wood"
    return next((FAMILY[b] for b in m.get("bits") or [] if b in FAMILY), NATURE_FAMILY.get(m["recipe"].get("material"), "wood"))


def lacks(house, cfg, pet, name, part=None):
    """Why it can't mend this now, in the world's words, or None: (the part, the hammer, the hammer's name or None)."""
    room = house["rooms"][pet["room"]]
    o = room["objects"].get(name)
    it = o and items.of(house, cfg, o, name, room)
    if not it:
        return "there is no %s here to mend" % name, None, None
    if not it["state"]["broken"] and it["state"]["wear"] < 0.5:
        return "there is nothing wrong with the %s" % name, None, None
    fam = family(o)
    have = next((b for b in pet["carrying"] if b in PARTS[fam]), None) if not part else None
    patch = part or next((n for n, x in room["objects"].items() if n != name and "made" in x and K.works(items.of(house, cfg, x, n, room) or {}, "mend")
                          and items.T(cfg)["kind"].get(x["made"]["recipe"].get("kind"), {}).get("used_up")), None)   # (a patch or a tile is a part for anything)
    if not have and not patch:
        return "you'd need %s to mend the %s" % (" or ".join("a bit of " + p for p in PARTS[fam]), name), None, None
    hammer = next((n for _, n, _ in items.find(house, cfg, verb="strike", room=room) if n != name), None)
    if it["class"] == "tool" and not hammer:
        return "you'd need a hammer to mend the %s" % name, None, None
    return None, have or patch, hammer


def mend(house, cfg, pet, name, part=None):
    """API5 §1.5: a broken (or worn) item mended with a part of its material family that it carries, or a patch or a
    tile here (used up), and for a tool the hammer (any working thing that strikes, here): wear 0, not broken.
    Returns (words, ok)."""
    why, use, hammer = lacks(house, cfg, pet, name, part)
    if why:
        return why, False
    room = house["rooms"][pet["room"]]
    o = room["objects"][name]
    it = items.of(house, cfg, o, name, room)
    if use in pet["carrying"]:
        pet["carrying"].remove(use)
    elif items.T(cfg)["kind"].get(room["objects"][use]["made"]["recipe"].get("kind"), {}).get("used_up"):
        things.gone(house, room["objects"].pop(use), use, "used up mending the %s" % name, room)
    else:   # (a needle: a mending tool, not used up)
        spent(house, cfg, pet, items.of(house, cfg, room["objects"][use], use, room), "mend")
    it["state"].update(wear=0.0, broken=False)
    it.pop("broke", None)
    if "made" in o:
        o["made"].pop("wear", None)   # (the v3.4 tool's own wear goes with it: craft.lasts)
        o["made"]["touched"] = house["tick"]
    if hammer:
        spent(house, cfg, pet, items.of(house, cfg, room["objects"][hammer], hammer, room), "strike")
    K.count(house, "mended", it["kind"])
    K.count(house, "verbs", "mend")
    craft.practise(house, cfg, pet, "mending")
    moment(house, "made", "%s mended the %s" % (label(pet), name), pet["id"], room["id"])
    return "you mended the %s with the %s%s; it is as good as it was" % (name, use, " and the %s" % hammer if hammer else ""), True


# ---- §1.6 refilling ----

def refill(house, cfg, pet, name):
    """API5: what it runs on, poured in from a bit it carries ([charge]: which bits, how many uses each). (words, ok)"""
    room = house["rooms"][pet["room"]]
    o = room["objects"].get(name)
    e = o and items.entry(house, cfg, o, name)
    if not e or not e[2]:
        return "the %s doesn't take anything" % name, False
    it, C = items.of(house, cfg, o, name, room), items.T(cfg)["charge"]
    ch, full = it["state"]["charge"], e[2]
    low = [m for m in sorted(full) if ch.get(m, 0) < full[m]]
    if not low:
        return "the %s is full" % name, False
    for m in low:
        bit = next((b for b in pet["carrying"] if b in C[m]["from"]), None)
        if bit:
            pet["carrying"].remove(bit)
            ch[m] = min(full[m], ch.get(m, 0) + C[m]["per_bit"])
            K.count(house, "verbs", "pour")
            if "made" in o:
                o["made"]["touched"] = house["tick"]
            return "you put the %s into the %s; it's %s" % (bit, name, "full" if ch[m] >= full[m] else "fuller"), True
    m = low[0]
    return "you have nothing to fill the %s with: it takes %s" % (name, " or ".join(C[m]["from"][:3])), False
