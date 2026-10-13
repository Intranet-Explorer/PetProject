"""Making by discovery (SPEC-v3.4 §3): bits change when something is done to them in the right place, joined things
can do what neither did, a few kinds take a material that has to be found out first, tools open the next thing, and
food is grown. Every rule is data (crafting.toml) and none of it is told to a pet: it tries, is told what came of
it, and what it found out is a recipe it knows, can pass on, and can lose. Skills (§2.2) are kept here too, since
practice at making is what most of them are for."""
import tomllib

from . import things
from .world import add_event, days as world_days, dist, label, moment, rnd

DONE = {"soak": "soaked", "warm": "warmed", "melt": "melted", "dry": "dried", "press": "pressed", "weave": "woven", "carve": "carved",
        "grind": "ground", "plant": "planted"}
NOWHERE = {"soak": "there is no water here to soak it in", "warm": "there is nothing warm enough here", "melt": "there is no heat here to melt it",
           "dry": "the air here is not dry enough: somewhere high under the roof might be", "press": "there is nothing heavy here to press it under",
           "weave": "you need a bench to weave at", "carve": "you need a bench to carve at",
           "grind": "the floor here is too soft to grind on: a stone floor would do", "plant": "there is no bed or pot of earth here to plant in"}
SKILLS = {   # how each feels as it grows: never a number (§2.2)
    "making": ["", "your paws are getting used to making", "your paws are surer at the bench", "your paws know making well"],
    "mending": ["", "you have mended a thing or two", "you are a fair hand at mending", "there is little you could not mend"],
    "tidying": ["", "you are getting quicker at putting things straight", "you put a room straight quickly", "a room falls into order under your paws"],
    "music": ["", "a tune stays with you a little better", "you hold a tune well", "you carry a tune true"],
    "tending": ["", "you are getting a feel for growing things", "growing things do well under your paws", "you know what a growing thing needs"],
    "reading": ["", "the small writing is a little easier", "you read the small writing well", "the book gives up what it knows to you"],
}


def load(cfg, directory):
    """crafting.toml, laid into the config: the materials become bits like any other (never grown by a room, never
    delivered), and each property that can emerge becomes a property like those in materials.toml."""
    C = cfg["craft"] = tomllib.loads((directory / "crafting.toml").read_text())
    C["rules"] = {(r["bit"], r["how"]): r for r in C.get("rule", [])}
    for name, m in C.get("material", {}).items():
        like = cfg["house"]["bits"].get(m.get("like"), {})
        cfg["house"]["bits"][name] = {"can": list(m["can"]), "looks": like.get("looks", {"shape": "blob", "color": "grey"}), "late": "crafting", "made": True}
    C["meets"] = {}
    for e in C.get("emerge", []):
        cfg["materials"][e["name"]] = dict(e["gives"], emerged=[e["a"], e["b"]])
        C["meets"][frozenset((e["a"], e["b"]))] = e
    return cfg


# ---- skills ----

def skill(cfg, pet, name):
    """How practised it is: 0 not at all, 1 some, 2 a good deal, 3 very."""
    return sum(pet.get("skill", {}).get(name, 0) >= n for n in cfg["skills"]["steps"])


def practise(house, cfg, pet, name, by=1.0):
    """It did the thing once more. When that takes it up a step it is told so, in words; and a young one of its own
    that is watching picks up a little."""
    s = pet.setdefault("skill", {})
    was = skill(cfg, pet, name)
    s[name] = round(s.get(name, 0) + by, 2)
    if skill(cfg, pet, name) > was:
        add_event(house, pet, SKILLS[name][skill(cfg, pet, name)])
    if by >= 1 and was >= 2:
        for kid in house["pets"].values():
            if kid.get("parent") == pet["id"] and kid["room"] == pet["room"] and kid["stage"] in ("hatchling", "child", "youngling") and not kid["sleep"]:
                kid.setdefault("skill", {})[name] = round(kid.get("skill", {}).get(name, 0) + cfg["skills"]["watched"], 2)


def skills_line(cfg, pet):
    return "; ".join(SKILLS[n][skill(cfg, pet, n)] for n in SKILLS if skill(cfg, pet, n))


def from_history(cfg, pet):
    """A pet that lived before skills has them from what it has done (§7.5): the things it made count as making, the
    songs it knows as music, what it has read as reading."""
    pet.setdefault("skill", {"making": float(pet.get("made", 0)), "music": float(2 * len(pet.get("songs", []))), "reading": float(len(pet.get("read", [])))})


# ---- where a thing can be done ----

def place(house, cfg, room, how):
    """Where in this room this can be done: (the thing to do it at, where that stands), ("", None) for anywhere in
    the room, or None if it cannot be done here."""
    from .world import power_on
    objs = room["objects"]
    if how == "plant":
        return next(((n, o["pos"]) for n, o in objs.items() if plantable(cfg, n, o)), None)
    at = cfg["craft"]["process"][how]["at"]
    if room["type"] in at.get("rooms", []):
        return "", None
    keys, day = at.get("fixtures", []), house["clock"]["phase"] != "night"
    for n, o in objs.items():
        fix, lit = o.get("fix", {}), o.get("state") == "on" and power_on(house)
        if "made" in o:
            if ("lit" in keys and lit and things.prop(cfg, o).get("light")) or (at.get("heavy") and things.prop(cfg, o).get("fixed")):
                return n, o["pos"]
        elif n in at.get("names", []) or any(k in fix for k in keys if k not in ("lit", "sun")) or ("sun" in keys and fix.get("sun") and day) \
                or ("lit" in keys and lit and "light" in fix):
            return n, o["pos"]
    return None


def places(house, cfg, pet, how):
    """The rooms it knows where this can be done, this one first."""
    return [rid for rid in [pet["room"]] + [r for r in pet["rooms"] if r != pet["room"]]
            if house["rooms"][rid]["type"] and place(house, cfg, house["rooms"][rid], how) is not None]


# ---- tools ----

def lasts(cfg, o):
    """How many uses a tool is good for before it needs mending: more from a practised maker."""
    return round(cfg["craft"]["tool"][o["made"]["recipe"]["kind"]]["uses"] * (1 + 0.5 * o["made"].get("fine", 0)))


def tool_here(house, cfg, room, kind):
    """A tool of this kind in the room that still works: its name, or None. (A tool is used where it lies: nobody
    carries one, and anyone may use it.)"""
    return next((n for n, o in things.made(room).items() if o["made"]["recipe"].get("kind") == kind and o["made"].get("wear", 0) < lasts(cfg, o)), None)


def tool_for(house, cfg, pet, kind):
    """(room, name) of a tool of this kind that still works: here, else in any room it knows. One that is elsewhere
    is fetched when it is used. ponytail: it comes by itself as the pet sets to work; walking it through the house is
    the upgrade."""
    rooms = [house["rooms"][pet["room"]]] + [house["rooms"][r] for r in pet["rooms"] if r != pet["room"] and house["rooms"][r]["type"]]
    return next(((r, n) for r in rooms for n, o in things.made(r).items() if o["made"]["recipe"].get("kind") == kind and o["made"].get("wear", 0) < lasts(cfg, o)), None)


def fetch(house, cfg, pet, kind):
    """The tool, in this room: (its name, where it was fetched from or "")."""
    from .world import free_tile
    room, (at, name) = house["rooms"][pet["room"]], tool_for(house, cfg, pet, kind)
    if at is room:
        return name, ""
    o = at["objects"].pop(name)
    for k in ("on", "wall", "home", "places"):
        o.pop(k, None)
    o["pos"], o["kept"] = free_tile(house, cfg, room, pet["pos"]), house["tick"]
    room["objects"][name] = o
    return name, at["name"]


def wear(house, cfg, pet, room, name):
    o = room["objects"][name]
    o["made"]["wear"] = o["made"].get("wear", 0) + 1
    o["made"]["touched"] = house["tick"]
    if o["made"]["wear"] >= lasts(cfg, o):
        add_event(house, pet, "the %s has worn with use: it will do no more until it is mended" % name)


def check_mend(a, house, cfg, pet, norm):
    room = house["rooms"][pet["room"]]
    o = room["objects"].get(norm(a.get("target")))
    if not o or "made" not in o:
        return "that is not a made thing here"
    m = o["made"]
    if not (m.get("wear") or m.get("damp") or m.get("dusty") or m.get("eaten")):
        return "there is nothing wrong with it"
    if not tool_here(house, cfg, room, "hammer") and skill(cfg, pet, "mending") < 1 and skill(cfg, pet, "making") < 2:
        return cfg["craft"]["tool"]["hammer"]["without"]
    return None


def mend(house, cfg, pet, a, norm):
    room, name = house["rooms"][pet["room"]], norm(a["target"])
    m, hammer = room["objects"][name]["made"], tool_here(house, cfg, room, "hammer")
    for k in ("wear", "damp", "dusty", "eaten"):
        m.pop(k, None)
    m["touched"] = house["tick"]
    if hammer and hammer != name:
        wear(house, cfg, pet, room, hammer)
    practise(house, cfg, pet, "mending")
    moment(house, "made", "%s mended the %s" % (label(pet), name), pet["id"], room["id"])
    return "you mended the %s%s; it is as good as it was" % (name, " with the hammer" if hammer and hammer != name else ""), {"energy": -cfg["make"]["effort"]}, "mend"


# ---- recipes: what a pet has found out (§3.3) ----

def words(cfg, key):
    """A recipe in plain words."""
    C = cfg["craft"]
    if key.startswith("kind:"):
        k = key[5:]
        return "%s %s can be made of %s" % (cfg["kinds"].get(k, {}).get("a", "a"), k, " and ".join(g.split("|")[0] for g in C["needs"][k]))
    if "+" in key:
        e = C["meets"][frozenset(key.split("+"))]
        return "something %s joined with something %s makes a thing that is %s: %s" % (e["a"], e["b"], e["name"], e["says"])
    bit, how = key.split("|")
    if how == "plant":
        return "a %s planted in earth grows" % bit
    return "%s, %s, makes %s" % (bit, DONE[how], C["rules"][(bit, how)]["gives"])


def learn(house, cfg, pet, key, src="found"):
    """It knows this now. Returns "first" (nobody in the house had found it), "again" (it had been lost), "own" (new
    to it, known to others) or None (it knew). What is found for the first time, or found again, is a moment."""
    known, R = pet.setdefault("recipes", {}), house.setdefault("recipes", {})
    if key in known:
        return None
    known[key] = {"tick": house["tick"], "from": src}
    rec = R.get(key)
    if rec and "lost" not in rec:
        return "own"
    if src != "found":   # (handed on while it was still known is the usual way; a recipe cannot come back by being told by nobody)
        R.setdefault(key, {"by": pet["id"], "tick": house["tick"]}).pop("lost", None)
        return "own"
    if rec:
        del rec["lost"]
        found(house, pet, "%s found again what nobody living knew: %s" % (label(pet), words(cfg, key)))
        return "again"
    R[key] = {"by": pet["id"], "tick": house["tick"]}
    found(house, pet, "%s found out that %s" % (label(pet), words(cfg, key)))
    return "first"


def found(house, pet, text, kind="discovery"):
    """Something found out: a moment, and a burst over the one who found it (numbered, so the page plays it once)."""
    moment(house, kind, text, pet["id"], pet["room"])
    burst(house, pet, "find", text)


def burst(house, pet, kind, text):
    house["n"]["burst"] = house["n"].get("burst", 0) + 1
    house.setdefault("bursts", []).append({"n": house["n"]["burst"], "tick": house["tick"], "pet": pet["id"], "room": pet["room"], "kind": kind, "text": text})
    del house["bursts"][:-20]


def lost(house, cfg):
    """A recipe nobody alive knows is lost (the things made with it stay). Said once, when the last who knew it dies."""
    living = [p for p in house["pets"].values() if p["stage"] not in ("dead",)]
    for key, rec in house.get("recipes", {}).items():
        if "lost" not in rec and not any(key in p.get("recipes", {}) for p in living):
            rec["lost"] = house["tick"]
            moment(house, "forgotten", "nobody living knows any more that %s" % words(cfg, key), None, None)


def inherit(house, cfg, child):
    """A child starts out knowing some of what its parent knew: each recipe as likely as not."""
    parent = house["pets"].get(child.get("parent") or "")
    r = rnd(house, "recipes", child["id"])
    for key in sorted((parent or {}).get("recipes", {})):
        if r.random() < cfg["craft"]["knowing"]["inherited"]:
            child.setdefault("recipes", {})[key] = {"tick": house["tick"], "from": "inherited"}
            house.setdefault("recipes", {}).setdefault(key, {"by": parent["id"], "tick": house["tick"]}).pop("lost", None)


def pass_on(house, cfg, teller, listener, how="told"):
    """One thing the teller knows and the listener does not goes with the telling (or the watching): the newest.
    Returns the words that were handed on, or ""."""
    new = [k for k in teller.get("recipes", {}) if k not in listener.get("recipes", {})]
    if not new or listener["stage"] in ("egg", "dead"):
        return ""
    key = max(new, key=lambda k: teller["recipes"][k]["tick"])
    learn(house, cfg, listener, key, "%s by %s" % (how, label(teller)))
    return words(cfg, key)


def recipe_lines(cfg, pet, most=6):
    known = sorted(pet.get("recipes", {}).items(), key=lambda kv: -kv[1]["tick"])
    return [words(cfg, k).split(":")[0] for k, _ in known[:most]]


# ---- processes (§3.1) ----

def to_hand(pet, room, bit):
    """How many of this bit it has in its paws or lying ready here."""
    return pet["carrying"].count(bit) + sum(1 for s in room["spots"] if s["ready"] and s["bit"] == bit and not s.get("on"))


def check_process(a, house, cfg, pet, norm):
    room, C = house["rooms"][pet["room"]], cfg["craft"]
    how, bit = norm(a.get("how")), norm(a.get("what"))
    if how not in DONE:
        return "there is no such way of changing a thing"
    if bit not in cfg["house"]["bits"]:
        return "that is not a thing to do it to"
    P = C["process"].get(how, {})
    have, need = to_hand(pet, room, bit), 2 if P.get("pair") else 1
    if have < need:
        return "you have no %s to hand" % bit if not have else "it takes two of them, and there is only one %s to hand" % bit
    if place(house, cfg, room, how) is None:
        return NOWHERE[how]
    tool = P.get("tool")   # (13 October 2026: a seed can be planted by paw; a trowel makes it better, not possible)
    if tool and not tool_for(house, cfg, pet, tool):
        pet.setdefault("lacks", {})[tool] = house["tick"]   # (felt as a want: wants.py)
        return C["tool"][tool]["without"]
    if how == "plant" and bit in C["grow"] and not tool_for(house, cfg, pet, "trowel") and by_paw(house, pet) >= C["growing"]["paw_plants"]:
        pet.setdefault("lacks", {})["trowel"] = house["tick"]
        return "your paws are sore from digging: what you planted by paw has to come up before you can plant again; something to dig with would do more"
    if skill(cfg, pet, "making") < P.get("skill", 0):
        return "your paws are not sure enough for that yet"
    if how == "plant" and bit not in C["grow"]:
        return "that would not grow"
    if pet["needs"]["energy"] < cfg["make"]["tired"]:
        return "you are too tired for that"
    return None


def take(house, cfg, pet, room, bit, n):
    """Take n of a bit from its paws first, then from the floor. Returns how many came from its paws."""
    from .world import hours
    had = min(n, pet["carrying"].count(bit))
    for _ in range(had):
        pet["carrying"].remove(bit)
    for s in sorted((s for s in room["spots"] if s["ready"] and s["bit"] == bit and not s.get("on")), key=lambda s: dist(s["pos"], pet["pos"]))[:n - had]:
        if s["loose"]:
            room["spots"].remove(s)
        else:
            s["ready"], s["back"] = False, house["tick"] + hours(cfg, cfg["house"]["rooms"][room["type"]]["regrow_hours"])
    return had


def give(house, cfg, pet, room, bit):
    """A bit into its paws, or onto the floor beside it if its arms are full."""
    if len(pet["carrying"]) < cfg["make"]["carry"]:
        pet["carrying"].append(bit)
    else:
        things.drop_bits(house, cfg, room, pet["pos"], [bit])


def process(house, cfg, pet, a, norm):
    """`process`: do something to a bit and see what comes of it. Returns (what it is told, effects, novelty key)."""
    room, C = house["rooms"][pet["room"]], cfg["craft"]
    how, bit = norm(a["how"]), norm(a["what"])
    key, P = "%s|%s" % (bit, how), C["process"].get(how, {})
    tool = P.get("tool") or ("trowel" if how == "plant" and tool_for(house, cfg, pet, "trowel") else None)
    fetched = ""
    if tool:
        name, frm = fetch(house, cfg, pet, tool)
        fetched = "you fetched the %s from %s; " % (name, frm) if frm else ""
        wear(house, cfg, pet, room, name)
    tried = pet.setdefault("tried", {})
    if how == "plant":
        name, _ = place(house, cfg, room, how)
        take(house, cfg, pet, room, bit, 1)
        room["objects"][name]["planted"] = {"what": bit, "at": house["tick"], "grow": 0.0, "watered": house["tick"], "by": pet["id"], "stage": "planted", **({} if tool else {"paw": True})}
        tried[key] = "planted"
        practise(house, cfg, pet, "tending")
        new = learn(house, cfg, pet, key)
        moment(house, "planted", "%s planted a %s in the %s" % (label(pet), bit, name), pet["id"], room["id"])
        if not tool:   # by paw: a shallow hole, so it comes up slowly, and one at a time; wanting something to dig with starts here
            pet.setdefault("lacks", {})["trowel"] = house["tick"]
            return "you scraped a shallow hole in the %s with your paws and planted the %s; it will want water, and will come up slowly: something to dig with would plant it deeper" % (name, bit), \
                {"curiosity": C["knowing"]["lift"] if new else 0.0}, "plant" if new else None
        return "%syou dug a hole in the %s with the trowel and planted the %s; it will want water" % (fetched, name, bit), {"curiosity": C["knowing"]["lift"] if new else 0.0}, "plant" if new else None
    rule = C["rules"].get((bit, how))
    if not rule:
        tried[key] = None
        return P["nothing"].format(bit=bit), {}, None
    take(house, cfg, pet, room, bit, 2 if P.get("pair") else 1)
    practise(house, cfg, pet, "making", 0.5)
    if rule.get("spoils"):
        tried[key] = False
        return rule["says"], {}, None
    give(house, cfg, pet, room, rule["gives"])
    tried[key], pet["got"] = rule["gives"], [rule["gives"], house["tick"]]
    new = learn(house, cfg, pet, key)
    for kid in [p for p in house["pets"].values() if p.get("parent") == pet["id"] and p["room"] == pet["room"] and p["stage"] not in ("egg", "dead") and not p["sleep"]]:
        if learn(house, cfg, kid, key, "watching %s" % label(pet)):   # a young one watching picks it up
            add_event(house, kid, "you watched and saw how: %s" % words(cfg, key))
    opens = [k for k, groups in C["needs"].items() if any(rule["gives"] in g.split("|") for g in groups) and not lacking(cfg, k, pet["carrying"])]
    text = "%s%s; you have %s now" % (fetched, rule["says"], rule["gives"])
    if new and rule.get("hint"):
        text += "; " + rule["hint"]
    if new and opens:
        text += "; with this you could make %s %s" % (cfg["kinds"].get(opens[0], {}).get("a", "a"), opens[0])
    return text, {"curiosity": C["knowing"]["lift"] if new else 0.0}, "found " + key if new else None


# ---- kinds that take a material found out first (§3.1), and tools (§3.4) ----

def lacking(cfg, kind, bits):
    """What a kind takes that is not among these bits: [] if it can be made of them."""
    return [g.split("|")[0] for g in cfg["craft"].get("needs", {}).get(kind, []) if not any(alt in bits for alt in g.split("|"))]


def takes(cfg, kind, bits=()):
    """What a kind is made of that is not among these bits, in words: "fired clay or carved wood", "wood or carved
    wood, and rope or vine cord"."""
    return ", and ".join(" or ".join(g.split("|")) for g in cfg["craft"].get("needs", {}).get(kind, []) if not any(alt in bits for alt in g.split("|")))


def by_paw(house, pet):
    """How many things it planted by paw are still coming up."""
    return sum(1 for r in house["rooms"].values() if r["type"] for o in r["objects"].values()
               if o.get("planted") and o["planted"].get("paw") and o["planted"].get("by") == pet["id"] and o["planted"]["grow"] < 1 and not o["planted"].get("wilted") and not o["planted"].get("dormant"))


def gated(cfg, kind):
    return kind in cfg["craft"].get("needs", {})


def spend(cfg, kind, carrying):
    """Take what the kind is made of out of what is carried. Returns the bits used."""
    used = []
    for g in cfg["craft"].get("needs", {}).get(kind, []):
        b = next((alt for alt in g.split("|") if alt in carrying), None)
        if b:
            carrying.remove(b)
            used.append(b)
    return used


def first_of(house, cfg, pet, kind):
    """The first of a kind that had to be found out, or of a tool: a moment, and a recipe its maker knows."""
    firsts = house.setdefault("firsts", {})
    if not gated(cfg, kind):
        return
    learn(house, cfg, pet, "kind:" + kind) if kind not in firsts else pet.setdefault("recipes", {}).setdefault("kind:" + kind, {"tick": house["tick"], "from": "found"})
    if kind not in firsts:
        firsts[kind] = house["tick"]
        if kind in cfg["craft"]["tool"]:
            found(house, pet, "the first %s in the house: %s made a tool" % (kind, label(pet)), "tool")


# ---- joining two things (§3.2) ----

def meet(cfg, a, b):
    """What comes of joining a thing of one property with a thing of another: the table's entry, or None."""
    return cfg["craft"]["meets"].get(frozenset((a, b))) if a != b else None


def joined(house, cfg, pet, e):
    """Two things were joined and something new came of it. Returns what the pet is told."""
    key = "+".join(sorted((e["a"], e["b"])))
    new = learn(house, cfg, pet, key)
    if new == "first" and e["name"] == "glowing":
        moment(house, "discovery", "the first soft glow in the house", pet["id"], pet["room"])
    return "this does something neither part did: %s. You could name it for what it does now" % e["says"]


# ---- growing food (§3.5) ----

def plantable(cfg, name, o):
    """A bed or a pot of earth with nothing in it."""
    bed = "fix" in o and name in cfg["craft"]["growing"]["beds"]
    return (bed or o.get("made", {}).get("recipe", {}).get("kind") == "plant pot") and not o.get("planted") and not o.get("on")


def stage(p):
    return "ripe" if p["grow"] >= 1 else "leaves" if p["grow"] >= 0.5 else "sprout" if p["grow"] >= 0.15 else "planted"


GREW = {"sprout": "what you planted in the %s has come up: a pale shoot", "leaves": "the seedling you planted in the %s has two leaves now",
        "ripe": "what you planted in the %s is ripe: it can be picked"}


def water(house, cfg, pet, room, name):
    """Tending a planted thing: it is watered, and whoever does it gets a little better at it."""
    p = room["objects"][name]["planted"]
    p["watered"] = house["tick"]
    p["grow"] = round(min(1.0, p["grow"] + cfg["body"]["tend_grow"] * (1 + skill(cfg, pet, "tending")) * (not p.get("dormant"))), 3)   # (asleep under snow, it does not grow for being tended: season.py)
    practise(house, cfg, pet, "tending", 0.25)


def grow(house, cfg):
    """Every world hour: what is planted grows (faster watered, by rain outdoors or by someone tending it), says so
    to whoever planted it as it comes on, and wilts if it is left dry."""
    from .season import asleep
    G, H = cfg["craft"]["growing"], cfg["house"]
    season = H["seasons"][house["clock"]["season"]]
    for room in [r for r in house["rooms"].values() if r["type"]]:
        rule = lambda k, d: things.room_rule(cfg, room, k, d)
        for name, o in room["objects"].items():
            p = o.get("planted")
            if not p:
                if "fix" in o and o["fix"].get("plant"):
                    o["grow"], o["state"] = 0.0, "bare"
                continue
            if asleep(house, cfg, room, name, p):   # SPEC-v3.5 §5: in winter what is planted outdoors neither grows nor wilts
                continue
            if room["type"] == "garden" and house["weather"] in ("rain", "storm"):
                p["watered"] = house["tick"]
            dry = world_days(cfg, p["watered"], house["tick"])
            if p["grow"] < 1 and not p.get("wilted"):
                if dry >= G["wilt_days"]:
                    p["wilted"] = True
                    who = house["pets"].get(p.get("by") or "")
                    if who and who["stage"] != "dead":
                        add_event(house, who, "what you planted in the %s has wilted for want of water" % name)
                else:
                    rate = season["growth"] * (rule("growth", 1.0) if room["type"] == "greenhouse" else 1.0)
                    if room["type"] == "greenhouse":
                        rate = max(rate, 0.8)   # warm under glass even in winter
                    elif room["type"] == "garden" and house["clock"]["phase"] == "night" and season["growth"] < 0.8:
                        rate *= G["cold"]       # a cold night outdoors
                    was = stage(p)
                    rate *= G["paw"] if p.get("paw") else 1.0   # planted by paw, in a shallow hole
                    p["grow"] = round(min(1.0, p["grow"] + rate * (G["tended"] if dry * 24 <= G["water_hours"] else G["untended"]) / (24 * cfg["craft"]["grow"][p["what"]]["days"])), 3)
                    who = house["pets"].get(p.get("by") or "")
                    if stage(p) != was and who and who["stage"] != "dead":
                        add_event(house, who, GREW[stage(p)] % name)
            p["stage"] = stage(p)
            if "fix" in o:   # (a bed's own picture goes by these)
                o["grow"], o["state"] = p["grow"], "ripe" if p["grow"] >= 1 else "growing"


def use_planted(house, cfg, pet, room, name):
    """Using a bed or a pot with something in it: ripe, it is picked (one of what it gives is eaten there and then
    by a pet with any appetite, the rest lies beside it); wilted, it is pulled up; otherwise it is watered."""
    o = room["objects"][name]
    p, E = o["planted"], cfg["effects"]
    if p.get("wilted"):
        del o["planted"]
        return "you pulled the wilted plant out of the %s; the earth is bare again" % name, {}, None
    if p["grow"] < 1 and p.get("dormant"):   # SPEC-v3.5 §5
        return "what is planted in the %s lies asleep under the snow: there is nothing to do for it until spring" % name, {}, None
    if p["grow"] < 1:
        water(house, cfg, pet, room, name)
        return "you watered what is growing in the %s" % name, {}, "tend"
    gives = [b for b, n in cfg["craft"]["grow"][p["what"]]["gives"] for _ in range(n + (b != "seed" and skill(cfg, pet, "tending") >= 2))]
    from . import season
    gives = season.harvest(house, cfg, gives)   # SPEC-v3.5 §5: in autumn the harvest is plentiful
    del o["planted"]
    if "fix" in o:
        o["grow"], o["state"] = 0.0, "bare"
    planter = house["pets"].get(p.get("by") or "")
    food = next((b for b in gives if "sweet" in cfg["house"]["bits"][b]["can"] and b != "seed"), None)
    fx, ate = {}, ""
    pet["picked"] = {"tick": house["tick"], "thing": name}
    if food and (house["tick"] - pet.get("last_eat", -10**9)) * cfg["clock"]["tick_seconds"] <= E["double_feed_seconds"]:
        food, ate = None, "; you have only just eaten, so all of it is there for the others"   # (13 October 2026: picked to eat or to share)
    if food:
        gives.remove(food)
        fx = dict(E["ripe"])
        soon = (house["tick"] - pet.get("last_eat", -10**9)) * cfg["clock"]["tick_seconds"] <= E["double_feed_seconds"]
        pet["prev_eat"], pet["last_eat"] = pet.get("last_eat", -10**9), house["tick"]
        if soon:
            fx = {"comfort": cfg["materials"]["rules"]["double_feed"], "tags": ["double_feed"]}
        elif planter:
            fx["comfort"] = fx.get("comfort", 0) + cfg["craft"]["growing"]["grown_lift"]
        ate = " and ate a %s%s" % (food, "; it sits heavy on top of the last meal" if soon else ": food the family grew" if planter else "")
    things.drop_bits(house, cfg, room, o["pos"], gives)
    if planter:   # (what the house had growing before anyone planted is not the family's doing)
        house.setdefault("harvests", []).append([house["tick"], pet["id"], planter["id"], name])
        del house["harvests"][:-50]
        moment(house, "harvest", "%s picked what %s planted in the %s%s" % (label(pet), "it had" if planter is pet else label(planter) + " had", name, ", and ate of it" if food else ""), pet["id"], room["id"])
    return "you picked what was ripe in the %s%s; beside it now: %s" % (name, ate, ", ".join(gives) or "nothing"), fx, "harvest"
