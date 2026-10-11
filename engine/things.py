"""Things and the bits they are made from (SPEC-v2 §4, SPEC-v3 §6.2, §6.3). A pet gathers bits, makes a thing
from them, and the thing takes one property its bits allow. What the thing then does is decided here, from
materials.toml; the purpose the pet writes changes nothing. Taking a thing apart gives the bits back."""
import re

from .world import LONG_AGO, add_event, dist, free_tile, hours, label, moment, sunny

SHAPES = ["circle", "square", "triangle", "blob", "bar", "dot", "ring", "star"]
COLORS = ["red", "orange", "yellow", "green", "teal", "blue", "purple", "pink", "brown", "white", "grey", "black"]
PLACES = ["center", "top", "bottom", "left", "right"]
WHEN = ["day", "night", "dusk", "visitor", "touched", "alone", "pet_resting"]
DO = ["glow", "dim", "hum", "bounce", "move_toward_pet", "move_away"] + ["change_color:" + c for c in COLORS]
# hidden effects of things that tag a prediction as being about the physics: tag -> the need it moves
TAG_NEED = {"warm": "comfort", "cool": "comfort", "quiet": "energy", "noisy": "energy", "fragrant": "comfort",
            "glassy": "curiosity", "hum": "curiosity", "bounce": "curiosity", "yours": "comfort"}


def props(cfg):
    return [p for p, v in cfg["materials"].items() if isinstance(v, dict) and "says" in v]


def made(room):
    return {n: o for n, o in room["objects"].items() if "made" in o}


def mine(house, pet, room=None):
    """The things in the room that are this pet's."""
    room = room or house["rooms"][pet["room"]]
    return [n for n, o in made(room).items() if o["made"]["owner"] == pet["id"]]


def free_to_change(house, pet, o):
    """A pet may take apart or combine its own things, a dead pet's, and things nobody owns (§7.3)."""
    owner = o["made"]["owner"]
    return owner in (pet["id"], None) or house["pets"].get(owner, {"stage": "dead"})["stage"] == "dead"


def prop(cfg, o):
    return cfg["materials"][o["made"]["recipe"]["material"]]


def doing(cfg, o):
    """What a taught thing is doing right now: the properties of its behavior while its "when" holds."""
    b = o["made"].get("behavior")
    return cfg["materials"]["behaviors"][b["do"].split(":")[0]] if b and o.get("active") else {}


SIZES = ["small", "medium", "large"]


def size(o):
    r = o["made"]["recipe"]
    return r.get("size") or max((p["size"] for p in r.get("parts") or []), default=2)


def as_size(v):
    """A recipe's size as 1 to 3, from the word or the number; None if it is neither."""
    return SIZES.index(v) + 1 if v in SIZES else v if v in (1, 2, 3) else None


def kinds_for(cfg, material):
    """The kinds a thing of this material can be (SPEC-v3.2 §3.1): every kind that does not rule it out."""
    return [k for k, v in cfg["kinds"].items() if material not in v.get("not", [])]


def a_thing(cfg, recipe, material=False):
    """A made thing in plain words: "a blue cushion", "a soft blue cushion"."""
    kind = recipe.get("kind") or "thing"
    words = ([recipe["material"]] if material else []) + ([recipe["color"]] if recipe.get("color") else []) + [kind]
    return "%s %s" % ("an" if words[0][0] in "aeiou" else "a", " ".join(words))


def from_parts(cfg, recipe):
    """What a thing made before v3.2 is, as a kind (§3.2): (kind, colour, size) from its parts and material, by the
    table in view/assets/kinds-from-parts.json. Its largest part decides; many parts make a mobile or a sculpture."""
    T, parts, material = cfg["from_parts"], recipe.get("parts") or [], recipe.get("material")
    if not parts:
        return "sculpture", "grey", 2
    main = max(parts, key=lambda p: p["size"])
    shapes = {p["shape"] for p in parts}
    if len(parts) >= 3:
        kind = T["many"]["then"] if material in T["many"]["hanging"] else T["many"]["else"]
    elif len(shapes) == 2 and material in T.get("pair", {}):
        kind = T["pair"][material]
    else:
        kind = T["material"].get(material, {}).get(main["shape"]) or T["shape"].get(main["shape"], "sculpture")
    if kind not in cfg["kinds"] or material in cfg["kinds"][kind].get("not", []) or cfg["kinds"][kind].get("wall"):
        kind = next((k for k in (T["shape"].get(main["shape"]), "sculpture") if k in cfg["kinds"]), next(iter(cfg["kinds"])))
    return kind, main["color"], main["size"]


def to_kind(cfg, recipe):
    """Turn an old recipe into a new one in place. Returns the mapping made, for the log, or None if it already has a kind."""
    if recipe.get("kind"):
        return None
    was = "%s %s" % (recipe.get("material"), "+".join(sorted(p["shape"] for p in recipe.get("parts") or [])) or "nothing")
    recipe["kind"], recipe["color"], recipe["size"] = from_parts(cfg, recipe)
    recipe.pop("parts", None)
    return "%s -> %s" % (was, recipe["kind"])


def wall_slot(house, room):
    """A free place on the wall for a thing that hangs (a picture, a mirror, a shelf), or None."""
    used = [o["pos"] for o in room["objects"].values() if o.get("wall")]
    return next((list(t) for t in room.get("wall_slots", [[2, 0], [5, 0], [9, 0]]) if list(t) not in used), None)


def whose(house, pet, o):
    """Whose a thing is, as this pet would say it (§3.3): yours, your mother's, Pip's, a gift, found."""
    m = o["made"]
    heir = m.get("heirloom")
    if heir and (pet["id"] in heir["to"]):
        giver = house["pets"].get(heir["from"])
        return "left to you by %s" % (who_s(house, pet, giver) if giver else "someone before you")
    if m["owner"] == pet["id"]:
        return "yours"
    if m["owner"] in house["pets"]:
        return who_s(house, pet, house["pets"][m["owner"]]) + "'s"
    return {"visitor": "a gift from the visitor", "director": "a gift from the visitor"}.get(m["by"], "found here")


def who_s(house, pet, other):
    from .world import relation
    rel = relation(house, pet, other)
    return "your %s" % rel if rel else label(other)


COUNT = ["", "", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]


def unique_name(house, cfg, name):
    """Two pets may both make a "soft nest": the second becomes "soft nest two". A made thing never takes the
    name of anything else in the house (a fixture, a stone, a bit, a pet), or it would replace or hide it."""
    taken = {n for r in house["rooms"].values() if r["type"] for n in r["objects"]}
    taken |= {f["name"] for r in cfg["house"]["rooms"].values() for f in r["fixtures"]} | set(cfg["house"]["bits"])
    taken |= {(p["name"] or "").lower() for p in house["pets"].values()} | {"egg", "visitor", "here", "the little one", "middle"}
    taken |= {label(p).lower().replace("the ", "", 1) for p in house["pets"].values()}   # nor the label of a pet that has no name
    taken |= {k for c in ("moth", "beetle", "mouse", "bird") for k in (c,)} | {d + " door" for d in ("north", "south", "east", "west")}
    if name.startswith("stone for"):
        name = "a " + name
    while True:
        n = house["names"][name] = house["names"].get(name, 0) + 1
        out = name if n == 1 else "%s %s" % (name, COUNT[n] if n < len(COUNT) else "number %d" % n)
        if out not in taken:
            return out


def clean_name(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w' -]", "", text.lower())).strip()[:24] if isinstance(text, str) else ""


def spot_for(house, cfg, pet, near):
    """Where a thing goes: beside what was named, or beside the pet."""
    room = house["rooms"][pet["room"]]
    target = room["objects"].get(near)
    return free_tile(house, cfg, room, target["pos"] if target else pet["pos"])


# ---- making from stuff ----

def to_pick_up(house, cfg, pet, recipe):
    """The bit lying here that this recipe still needs: one that can be the material, if nothing carried can."""
    room, bits = house["rooms"][pet["room"]], cfg["house"]["bits"]
    if any(recipe.get("material") in bits[b]["can"] for b in pet["carrying"]) or len(pet["carrying"]) >= cfg["make"]["carry"]:
        return []
    spots = sorted((s for s in room["spots"] if s["ready"]), key=lambda s: dist(s["pos"], pet["pos"]))
    return [s for s in spots if recipe.get("material") in bits[s["bit"]]["can"]][:1]


def check_make(a, house, cfg, pet):
    """SPEC-v3.2 §3.1: a thing is a kind from the catalog, in a material its bits allow, a colour and a size."""
    r, room = a.get("recipe"), house["rooms"][pet["room"]]
    if not isinstance(r, dict) or r.get("kind") not in cfg["kinds"]:
        return "no recipe"
    carrying = pet["carrying"] + [s["bit"] for s in to_pick_up(house, cfg, pet, r)]
    allowed = {p for b in carrying for p in cfg["house"]["bits"][b]["can"]}
    if not carrying:
        return "you have nothing to make it from"
    if r.get("material") not in allowed:
        return "nothing here can be made %s" % r.get("material")
    kind = cfg["kinds"][r["kind"]]
    if r["material"] in kind.get("not", []):
        return "%s %s cannot be %s" % (kind.get("a", "a"), r["kind"], r["material"])
    if r.get("color") not in COLORS or not as_size(r.get("size", 2)):
        return "it needs a colour and a size"
    if as_size(r.get("size", 2)) > cfg["make"]["parts"].get(pet["stage"], 0):
        return "you are not big enough yet to make something that large"
    if not clean_name(r.get("name")) or not isinstance(r.get("purpose"), str):
        return "it needs a name and a purpose"
    if len(made(room)) >= cfg["make"]["crowded"]:
        return "this room is too crowded for another thing"
    if kind.get("wall") and not wall_slot(house, room):
        return "there is no free place on the wall here to hang it"
    if pet["needs"]["energy"] < cfg["make"]["tired"]:
        return "you are too tired to make anything"
    return None


def make(house, cfg, pet, a, clean):
    r, room = a["recipe"], house["rooms"][pet["room"]]
    want, n = r["material"], 1   # one bit goes into a thing: the one that gives it its nature
    picked = to_pick_up(house, cfg, pet, r)
    for spot in picked:   # what it was short of, it picks up from the floor on the way
        pet["carrying"].append(spot["bit"])
        if spot["loose"]:
            room["spots"].remove(spot)
        else:
            spot["ready"], spot["back"] = False, house["tick"] + hours(cfg, cfg["house"]["rooms"][room["type"]]["regrow_hours"])
    # one bit per part: the one that gives the property first, then whatever else is carried
    order = sorted(pet["carrying"], key=lambda b: want not in cfg["house"]["bits"][b]["can"])
    used, pet["carrying"] = order[:n], order[n:]
    name = unique_name(house, cfg, clean_name(r["name"]))
    recipe = {"name": name, "kind": r["kind"], "material": want, "color": r["color"], "size": as_size(r.get("size", 2)), "purpose": clean(r["purpose"], 80)}
    house["n"]["thing"] += 1
    hangs = cfg["kinds"][r["kind"]].get("wall")
    o = {"pos": wall_slot(house, room) if hangs else spot_for(house, cfg, pet, a.get("near")), **({"wall": True} if hangs else {}),
         "made": {"id": house["n"]["thing"], "recipe": recipe, "by": pet["id"], "owner": pet["id"], "tick": house["tick"],
                  "bits": used, "uses": 0, "ups": 0, "used_at": house["tick"], "heirloom": None, "behavior": None}}
    if cfg["materials"][want].get("light"):
        o["state"] = "on"
    room["objects"][name] = o
    pet["made"] += 1
    moment(house, "made", "%s made %s it calls '%s'" % (label(pet), a_thing(cfg, recipe), name), pet["id"], room["id"])   # §6: the kind, then the name
    how = "out of what you carried" if not picked else "from %s" % " and ".join(sorted(set(used)))
    # Novelty goes by kind and wears; a thing like one it made lately is no longer new (§3.3).
    return "you made %s and called it %s, %s%s" % (a_thing(cfg, recipe), name, how, "; it hangs on the wall" if hangs else ""), {"energy": -(cfg["make"]["effort"] + n)}, "make " + want


def drop_bits(house, cfg, room, pos, bits):
    """Loose bits on the floor. A room only holds so many: past that the oldest is swept away."""
    for b in bits:
        room["spots"].append({"bit": b, "pos": free_tile(house, cfg, room, pos), "ready": True, "back": None, "loose": True})
    loose = [s for s in room["spots"] if s["loose"]]
    for s in loose[:-cfg["make"]["loose_bits"]]:
        room["spots"].remove(s)


def unmake(house, cfg, pet, name):
    room = house["rooms"][pet["room"]]
    o = room["objects"].pop(name)
    drop_bits(house, cfg, room, pet["pos"] if o.get("wall") else o["pos"], o["made"]["bits"])   # the stuff comes back; no energy does (§6.3)
    gone(house, o, name, "taken apart", room)
    whose = "its" if o["made"]["owner"] == pet["id"] else "a"
    moment(house, "unmade", "%s took apart %s %s, '%s'" % (label(pet), whose, o["made"]["recipe"].get("kind", "thing"), name), pet["id"], room["id"])
    return "you took apart %s; what it was made of lies where it stood" % name, {}, None


def gone(house, o, name, how, room=None):
    """Keep a short note of a thing that no longer exists, for the Things tab and the life records. What was written
    on it goes with it (SPEC-v3.1 §2: an inscription on a thing is the thing's)."""
    for r in [room] if room else [x for x in house["rooms"].values() if x["type"]]:
        for m in [m for m in r.get("marks", []) if m["on"] == name]:
            r["marks"].remove(m)
            house.setdefault("fresh_marks", []).append({"id": m["id"], "tick": house["tick"], "room": r["id"], "place": m["on"], "text": m["text"],
                                                        "by": m["by"], "medium": m["medium"], "what": "gone with the thing", "actor": None})
    house.setdefault("gone_things", []).append(
        {"name": name, "recipe": o["made"]["recipe"], "by": o["made"]["by"], "owner": o["made"]["owner"],
         "uses": o["made"]["uses"], "ups": o["made"]["ups"], "made": o["made"]["tick"], "gone": [house["tick"], how]})
    del house["gone_things"][:-200]


def check_combine(a, house, cfg, pet, norm):
    room = house["rooms"][pet["room"]]
    x, y, r = norm(a.get("a")), norm(a.get("b")), a.get("recipe")
    things = made(room)
    if x not in things or y not in things or x == y:
        return "you can only combine two different things that are here"
    if not (free_to_change(house, pet, things[x]) and free_to_change(house, pet, things[y])):
        return "one of those belongs to someone else"
    if things[x]["made"].get("heirloom") or things[y]["made"].get("heirloom"):
        return "an heirloom cannot be remade"
    if not isinstance(r, dict) or not isinstance(r.get("purpose"), str) or not clean_name(r.get("name")):
        return "it needs a name and a purpose"
    if r.get("material") not in {things[n]["made"]["recipe"]["material"] for n in (x, y)}:
        return "it has to keep the nature of one of the two"
    if pet["needs"]["energy"] < cfg["make"]["tired"]:
        return "you are too tired to do that"
    return None


def combine(house, cfg, pet, a, clean, norm):
    room = house["rooms"][pet["room"]]
    x, y, r = norm(a["a"]), norm(a["b"]), a["recipe"]
    olds = [room["objects"].pop(n) for n in (x, y)]
    for n, o in zip((x, y), olds):
        gone(house, o, n, "combined", room)
    name = unique_name(house, cfg, clean_name(r["name"]))
    kept = next(o for o in olds if o["made"]["recipe"]["material"] == r["material"])["made"]["recipe"]   # the one whose nature it keeps
    kind = joined(cfg, [o["made"]["recipe"] for o in olds], r["material"])
    recipe = {"name": name, "kind": kind, "material": r["material"], "color": kept.get("color", "grey"), "size": max(size(o) for o in olds),
              "purpose": clean(r["purpose"], 80)}
    house["n"]["thing"] += 1
    hangs = cfg["kinds"][kind].get("wall")
    o = {"pos": (wall_slot(house, room) or olds[0]["pos"]) if hangs else next((x["pos"] for x in olds if not x.get("wall")), pet["pos"]),
         **({"wall": True} if hangs and wall_slot(house, room) else {}),
         "made": {"id": house["n"]["thing"], "recipe": recipe, "by": pet["id"], "owner": pet["id"], "tick": house["tick"],
                  "bits": [b for old in olds for b in old["made"]["bits"]][:6], "uses": 0, "ups": 0, "used_at": house["tick"],
                  "heirloom": None, "behavior": None, "from": [x, y]}}
    if cfg["materials"][r["material"]].get("light"):
        o["state"] = "on"
    room["objects"][name] = o
    pet["made"] += 1
    effort = (cfg["make"]["effort"] + 1) * (room_rule(cfg, room, "combine", 1.0) if room["type"] == "workshop" else 1.0)   # easier at a bench (§6.1)
    was = [a_thing(cfg, {"kind": old["made"]["recipe"].get("kind")}) for old in olds]
    moment(house, "made", "%s joined %s and %s into %s it calls '%s'" % (label(pet), was[0], was[1], a_thing(cfg, {"kind": kind}), name), pet["id"], room["id"])
    return "you joined %s and %s into %s and called it %s" % (x, y, a_thing(cfg, recipe), name), {"energy": -effort}, "combine " + r["material"]


def joined(cfg, recipes, material):
    """What two things make together (SPEC-v3.2 §3.1): two of a kind stay that kind; otherwise the more complex of the
    two kinds, and for two different kinds as complex as each other a mobile (of stuff that hangs and moves) or a
    sculpture. If the kind that comes out cannot be of the material kept, a sculpture: anything can be one."""
    K, a, b = cfg["kinds"], recipes[0].get("kind"), recipes[1].get("kind")
    rank = lambda k: K.get(k, {}).get("rank", 1)
    if a == b:
        kind = a
    elif rank(a) != rank(b):
        kind = max((a, b), key=rank)
    else:
        many = cfg["from_parts"]["many"]
        kind = many["then"] if material in many["hanging"] else many["else"]
    return kind if kind in K and material not in K[kind].get("not", []) else "sculpture" if "sculpture" in K else kind


def room_rule(cfg, room, key, default=None):
    """A number from the room's own rule, as it stands now: a rule can drift once in a lineage (§6.5)."""
    drift = room.get("drift") or {}
    if key in drift:
        return drift[key]
    return cfg["house"]["rules"].get(room["type"], {}).get(key, default)


# ---- using a made thing ----

def use(house, cfg, pet, name):
    """What using a made thing does. Returns (what the pet is told, need effects, novelty key or None)."""
    room = house["rooms"][pet["room"]]
    o, m = room["objects"][name], prop(cfg, room["objects"][name])
    kind = "use a %s thing" % o["made"]["recipe"]["material"]
    o["made"]["touched"], was_dusty = house["tick"], o["made"].pop("dusty", False)
    o["made"]["used_at"] = house["tick"]
    fx = {n: v * (size(o) / 2 if m.get("by_size") else 1) for n, v in m.get("use", {}).items()}
    note = ""
    if o["made"].get("damp") or o["made"].get("eaten"):   # a damp or moth-eaten soft thing gives half
        fx = {n: v / 2 for n, v in fx.items()}
        note = "; it is damp" if o["made"].get("damp") else "; something has been eating at it"
    if was_dusty:                                          # the attic's dust: half, and a sneeze
        fx = {n: v / 2 for n, v in fx.items()}
        note += "; dust flew up and made you sneeze"
    if room["type"] == "workshop" and m.get("loud"):       # noisy things are louder in the workshop
        fx = {n: v * room_rule(cfg, room, "loud", 1.0) for n, v in fx.items()}
    if m.get("light"):
        o["state"] = "off" if o["state"] == "on" else "on"
        return "you switched %s %s" % (name, o["state"]), fx, kind
    if m.get("food") and o["made"].get("heirloom"):
        return "you cannot bring yourself to eat the %s; it was left to someone" % name, {}, None
    if m.get("food"):
        del room["objects"][name]
        pet["prev_eat"], pet["last_eat"] = pet.get("last_eat", LONG_AGO), house["tick"]
        gone(house, o, name, "eaten")
        moment(house, "ate", "%s ate %s, '%s'" % (label(pet), a_thing(cfg, o["made"]["recipe"]), name), pet["id"], room["id"])
        return "you ate " + name, fx, kind
    if m.get("spring_steps"):
        pet["spring"] = m["spring_steps"]
        return "you used %s and there is a spring in your step%s" % (name, note), fx, kind
    if not fx:
        return "you tried to use the %s; nothing came of it%s" % (name, note), fx, None
    return "you used %s%s" % (name, note), fx, kind


def useful(made_rec, cfg):
    """§6 of v2: on most of at least `useful_uses` occasions the thing raised the need its property is for."""
    need = cfg["materials"][made_rec["recipe"]["material"]].get("need")
    return bool(need) and made_rec["uses"] >= cfg["growth"]["useful_uses"] and made_rec["ups"] * 2 > made_rec["uses"]


def occasion(house, cfg, o, name, change):
    """Engine truth about what a thing did to a pet on one occasion. Its maker is credited when it turns useful."""
    m = o["made"]
    need = prop(cfg, o).get("need")
    m["uses"] += 1
    m["ups"] += change.get(need, 0) > 0
    maker = house["pets"].get(m["by"])
    if maker and m["id"] not in maker["useful"] and useful(m, cfg):
        maker["useful"].append(m["id"])


# ---- what things do just by being there ----

def near(house, cfg, pet, key, reach=1):
    room = house["rooms"][pet["room"]]
    return [n for n, o in made(room).items() if dist(pet["pos"], o["pos"]) <= reach and (key in prop(cfg, o) or key in doing(cfg, o))]


def light_on(house, cfg, room):
    """Any light lit in the room: a lamp, a bright thing, a thing taught to glow. A power cut takes them all (§6.4)."""
    from .world import power_on
    if not power_on(house):
        return False
    for o in room["objects"].values():
        if "made" in o:
            if (o.get("state") == "on" and prop(cfg, o).get("light")) or doing(cfg, o).get("light"):
                return True
        elif o.get("state") == "on" and "light" in o.get("fix", {}):
            return True
    return False


def standing(house, cfg, pet):
    """Standing effects of the things around a pet: [(tag, need, rate per 10 s, thing name, what it feels like)]."""
    room, phase, out = house["rooms"][pet["room"]], house["clock"]["phase"], []
    for n, o in made(room).items():
        p, d, close = prop(cfg, o), doing(cfg, o), dist(pet["pos"], o["pos"]) <= 1
        material = o["made"]["recipe"]["material"]
        if close and "near" in p:
            for need, rate in p["near"].get(phase, {}).items():
                out.append((material, need, rate, n, "the %s beside you feels %s" % (n, "pleasant" if rate > 0 else "unpleasant")))
        if close and "near" in d:
            for need, rate in d["near"].items():
                out.append((o["made"]["behavior"]["do"], need, rate, n, "the %s beside you is doing something that holds your eye" % n))
        if "scent" in p:   # fragrant: the whole room, fading as this pet gets used to it (§6.3)
            fresh = p.get("fades", 0.85) ** pet["scent"].get(n, 0)
            if fresh > 0.15:
                out.append(("fragrant", "comfort", p["scent"] * fresh, n, "the room smells sweet from the %s" % n))
        if close and "sun" in p and sunny(house) and (room.get("type") in ("garden", "greenhouse", "attic", "pond") or any(
                "window" in x.get("fix", {}) for x in room["objects"].values())):
            for need, rate in p["sun"].items():
                out.append(("glassy", need, rate, n, "the %s scatters the sunlight" % n))
        kept = house["tick"] - o["made"]["tick"] >= cfg["ticks_per_day"]
        if close and kept and o["made"]["owner"] == pet["id"] and not any(t[0] == "yours" for t in out):
            out.append(("yours", "comfort", cfg["effects"]["yours"], n, "the %s feels like yours" % n))   # kept things pay (§3.3)
    return out


def rest(house, cfg, pet, energy):
    """Resting next to a noisy or a quiet thing: (energy per 10 s, tags, {thing: what it added per 10 s})."""
    room, tags, share = house["rooms"][pet["room"]], [], {}
    for n in near(house, cfg, pet, "rest_near"):
        o = room["objects"][n]
        by = prop(cfg, o).get("rest_near") or doing(cfg, o)["rest_near"]
        if room["type"] == "workshop":
            by = by / room_rule(cfg, room, "loud", 1.0)
        share[n], energy, tags = energy * (by - 1), energy * by, tags + ["noisy" if "rest_near" in prop(cfg, o) else "hum"]
    for n in near(house, cfg, pet, "rest_bonus"):
        bonus = prop(cfg, room["objects"][n])["rest_bonus"]
        share[n], energy, tags = bonus, energy + bonus, tags + ["quiet"]
    return energy, sorted(set(tags)), share


# ---- teaching (SPEC-v2 §7) ----

def check_teach(a, house, cfg, pet, norm):
    name, b = norm(a.get("target")), a.get("behavior")
    if name not in mine(house, pet):
        return "you can only teach your own things"
    if not isinstance(b, dict) or b.get("when") not in WHEN or b.get("do") not in DO:
        return "unknown behavior"
    taught = [n for r in house["rooms"].values() if r["type"] for n, o in made(r).items()
              if o["made"]["owner"] == pet["id"] and o["made"].get("behavior")]
    if name not in taught and len(taught) >= cfg["growth"]["taught_max"]:
        return "you cannot keep that many things taught at once"
    return None


def teach(house, pet, a, name):
    b = {"when": a["behavior"]["when"], "do": a["behavior"]["do"]}
    house["rooms"][pet["room"]]["objects"][name]["made"]["behavior"] = b
    moment(house, "taught", "%s taught the %s to %s when %s" % (
        label(pet), name, b["do"].replace("_", " ").replace(":", " to "), b["when"].replace("_", " ")), pet["id"], pet["room"])
    return "you taught %s: when %s, %s" % (name, b["when"].replace("_", " "), b["do"].replace("_", " ")), {}, "teach"


def behave(house, cfg):
    """Run every taught thing for one tick: decide whether its "when" holds, and move the ones that move."""
    seconds = cfg["clock"]["tick_seconds"]
    for room in house["rooms"].values():
        if not room["type"]:
            continue
        pets = [p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] not in ("egg", "dead")]
        for n, o in made(room).items():
            b = o["made"].get("behavior")
            if not b:
                continue
            owner = next((p for p in pets if p["id"] == o["made"]["owner"]), pets[0] if pets else None)
            resting = bool(owner and (owner["sleep"] or (owner["plan"] and owner["plan"]["left"] is not None
                                                         and owner["plan"]["steps"][owner["plan"]["i"]].get("type") == "rest")))
            o["active"] = {
                "day": house["clock"]["phase"] == "day", "night": house["clock"]["phase"] == "night", "dusk": house["clock"]["phase"] == "dusk",
                "visitor": (house["tick"] - house["visitor_last"]) * seconds <= 60,
                "touched": (house["tick"] - o["made"].get("touched", LONG_AGO)) * seconds <= 20,
                "alone": not owner or dist(owner["pos"], o["pos"]) > 3, "pet_resting": resting,
            }[b["when"]]
            step = doing(cfg, o).get("step")
            if step and owner and house["tick"] % 2 == 0 and (dist(owner["pos"], o["pos"]) > 1 if step > 0 else True):
                from .world import in_room, taken
                used = taken(house, room, n) + [p["pos"] for p in pets]
                options = [[o["pos"][0] + dx, o["pos"][1] + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
                options = [t for t in options if in_room(cfg, t) and t not in used]
                best = (min if step > 0 else max)(options, key=lambda t: dist(t, owner["pos"]), default=None)
                if best and (dist(best, owner["pos"]) - dist(o["pos"], owner["pos"])) * step < 0:
                    o["pos"] = best


# ---- upkeep: what time does to things left lying (§6.1's local rules) ----

def upkeep(house, cfg):
    """Once a world hour: damp in the cellar, dust in the attic, things in the pond's water float away."""
    for room in house["rooms"].values():
        if not room["type"]:
            continue
        water = [t for o in room["objects"].values() for t in o.get("fix", {}).get("water", [])]
        for n, o in list(made(room).items()):
            m, idle = o["made"], house["tick"] - o["made"]["used_at"]
            if room["type"] == "cellar" and "use" in prop(cfg, o) and idle >= hours(cfg, room_rule(cfg, room, "damp_hours", 16)):
                m["damp"] = True
            elif room["type"] != "cellar" and m.get("damp") and idle < hours(cfg, 4):
                m.pop("damp")   # used somewhere dry, it dries out
            if room["type"] == "attic" and idle >= room_rule(cfg, room, "dust_days", 2) * cfg["ticks_per_day"]:
                m["dusty"] = True
            if o["pos"] in water and not prop(cfg, o).get("fixed"):   # it floats away to some other room (§6.1)
                found = [r for r in house["rooms"].values() if r["type"] and r["id"] != room["id"]]
                if found:
                    from .world import rnd
                    to = rnd(house, "float", m["id"], house["tick"]).choice(found)
                    del room["objects"][n]
                    o["pos"] = free_tile(house, cfg, to, [cfg["W"] // 2, cfg["H"] // 2])
                    to["objects"][n] = o
                    owner = house["pets"].get(m["owner"])
                    if owner and owner["stage"] != "dead":
                        add_event(house, owner, "your %s is not where you left it" % n)
                    moment(house, "floated", "the %s floated out of %s and turned up in %s" % (n, room["name"], to["name"]), None, to["id"])
