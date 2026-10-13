"""Wants (SPEC-v3.4 §2.1): up to three concrete, short-lived things a pet wants, made by the engine from where it is,
what it has and has not done, and what it is like. No model is asked. Its mind is told them in plain words and may
take one up or leave them all; its body leans toward whatever serves one. A want is met when the world shows it is
(the room is known, the bit has been held, the thing has been tried): that is felt, seen, and written down, and
another takes its place. One left alone for a world day fades."""
import re

from . import craft, order, things
from .world import LONG_AGO, add_event, days as world_days, label, moment, relation, rnd

GROUPS = {"door": "know", "creature": "know", "bit": "know", "try": "know", "word": "know", "look": "know",
          "store": "better", "glow": "better", "warm": "better", "useless": "better", "tool": "better", "window": "better",
          "comfort": "someone", "toy": "someone", "tell": "someone", "game": "someone",
          "recipe": "family", "song": "family", "finer": "skill"}
# which temperament leans toward which kind of want (§2.1): gene -> the wants it weights up
LEANS = {"curious": ("bit", "try", "word", "door", "creature", "look"), "bold": ("door", "creature"), "orderly": ("store", "glow", "warm", "useless", "tool", "window"),
         "sociable": ("comfort", "toy", "tell"), "playful": ("toy", "game"), "patient": ("recipe", "song", "finer")}
TRY = {"soak": "what water does to %s", "warm": "what warmth does to %s", "melt": "what heat does to %s", "dry": "what becomes of %s left to dry",
       "press": "what becomes of %s under something heavy", "weave": "what comes of weaving %s", "carve": "what could be carved out of %s",
       "grind": "what grinding does to %s", "plant": "whether %s would grow in the earth"}
RAIN = re.compile(r"\b(rain|drizzle|showers?|thunderstorms?|snow)\b", re.I)


ONE = ("pebble", "seed", "leaf", "petal", "feather", "shell", "bead", "reed", "bell", "vine", "quill", "berry", "bean", "stone", "tile", "brick", "block", "cake")


def a(bit):
    """A bit with its article: "a reed", "an ink block"; stuff has none ("clay", "wicker")."""
    return "%s %s" % ("an" if bit[0] in "aeiou" else "a", bit) if bit.split()[-1] in ONE else bit


def held(pet):
    """Every bit it has ever had in its paws."""
    return {b for bits in pet.get("gathered", {}).values() for b in bits} | set(pet.get("carrying", [])) | {v for v in pet.get("tried", {}).values() if isinstance(v, str)}


def door_words(house, pet, rid, d):
    return "the %s door%s" % (d, "" if rid == pet["room"] else " of %s" % house["rooms"][rid]["name"])


def book_room(house):
    return next((r["id"] for r in house["rooms"].values() if r["type"] and any(o.get("fix", {}).get("book") for o in r["objects"].values())), None)


def candidates(house, cfg, pet):
    """Everything it could want just now: [{what, key, text, done, weight, ...}]. `done`: the same thing said as met."""
    out, rooms, tick = [], house["rooms"], house["tick"]
    known = [rooms[r] for r in pet["rooms"] if rooms[r]["type"]]
    here, kin = rooms[pet["room"]], [p for p in house["pets"].values() if p["id"] != pet["id"] and p["stage"] not in ("egg", "dead") and relation(house, pet, p)]
    add = lambda what, key, text, done, weight=1.0, **more: out.append(dict(more, what=what, key="%s:%s" % (what, key), text=text, done=done, weight=weight))
    # to know: a door it has not been through, a creature it has not been near, a bit it has never held, a thing it has not tried, a word
    for r in known:
        for d, to in r["doors"].items():
            if to not in pet["rooms"] and house["shut"].get("%s|%s" % (r["id"], d), LONG_AGO) <= tick:
                add("door", to, "you want to know what is behind %s" % door_words(house, pet, r["id"], d), "found out what was behind %s" % door_words(house, pet, r["id"], d),
                    1.4 if r is here else 1.0, room=to, frm=r["id"], door=d)
    for c in house["creatures"]:
        if c["room"] in pet["rooms"] and not pet["met"].get(c["kind"]) and not c.get("tame"):
            add("creature", c["kind"], "you want a closer look at the %s" % c["kind"], "got close to the %s" % c["kind"], kind=c["kind"], n0=0)
    looked = pet.get("looked", [])
    new = sorted(((o["made"]["tick"], n, r) for r in known for n, o in things.made(r).items() if o["made"]["by"] != pet["id"] and n not in looked and not o.get("on")
                  and house["pets"].get(o["made"]["by"], {}).get("stage", "dead") != "dead"), reverse=True)[:2]
    for _, n, r in new:   # a thing someone else has made that it has not looked at closely
        add("look", n, "you want a closer look at the %s that %s made" % (n, label(house["pets"][r["objects"][n]["made"]["by"]])), "had a close look at the %s" % n, 0.7, thing=n, room=r["id"])
    had = held(pet)
    grown = {s["bit"]: r["id"] for r in reversed(known) for s in r["spots"] if s["ready"] and not s.get("on")}
    grown.update({s["bit"]: here["id"] for s in here["spots"] if s["ready"] and not s.get("on")})
    for bit, rid in grown.items():
        if bit not in had:
            add("bit", bit, "you want to know what %s is like in your paws%s" % (a(bit), "" if rid == here["id"] else " (there is some in %s)" % rooms[rid]["name"]),
                "held %s for the first time" % a(bit), bit=bit, room=rid)
    tried, C = pet.get("tried", {}), cfg["craft"]
    hinted = {(h["bit"], h["how"]) for h in pet.get("hints", [])}
    for bit in sorted(set(pet["carrying"]) | (had & set(grown)) | {b for b, _ in hinted}):
        for how in craft.DONE:
            key = "%s|%s" % (bit, how)
            rule = how == "plant" and bit in C["grow"] or (bit, how) in C["rules"]
            if key in tried or (how == "plant" and bit not in C["grow"]) or craft.skill(cfg, pet, "making") < C["process"].get(how, {}).get("skill", 0):
                continue
            where = craft.places(house, cfg, pet, how)
            if where and (bit in pet["carrying"] or bit in grown):
                # what was read about comes first; then what would give the stuff of a tool it has found it lacks (it is not told that it would)
                gives = C["rules"].get((bit, how), {}).get("gives")
                toward = any(gives in g.split("|") for t in pet.get("lacks", {}) if t not in house.get("firsts", {}) for g in C["needs"][t])
                add("try", key, "you want to find out " + TRY[how] % a(bit), "found out " + TRY[how] % a(bit),
                    (4.0 if (bit, how) in hinted else 3.0 if toward else 1.6 if rule else 0.5) * (1.3 if bit in pet["carrying"] else 1.0), bit=bit, how=how, room=where[0], bit_room=grown.get(bit))
    for w in pet.get("unknown", [])[-3:]:
        book = book_room(house)
        hint = "" if not book or pet.get("asked") else "; the heavy book in %s might know" % rooms[book]["name"]
        add("word", w, 'you want to know what "%s" is: the box said it%s' % (w, hint), 'asked what "%s" is' % w, 1.2, word=w, room=book if book in pet["rooms"] else None)
    # to make better: somewhere to keep things, a light that is not harsh, a warm thing for a cold room, a thing that did nothing, a tool it lacked
    for r in known:
        if r.get("mess") == 2 and order.full(cfg, r):
            add("store", r["id"], "you want somewhere to keep things in %s" % r["name"], "has somewhere to keep things in %s now" % r["name"], 1.2, room=r["id"])
    night = house["clock"]["phase"] == "night"
    if night and things.light_on(house, cfg, here, harsh=True) and here["type"] not in ("cellar", "storeroom") and not gentle(cfg, here):
        add("glow", here["id"], "you want a light for %s that is not harsh at night" % here["name"], "has a light in %s that is not harsh at night" % here["name"], 1.3, room=here["id"])
    if night and here["type"] in cfg["wants"]["cold_rooms"] and not warm(cfg, here):
        add("warm", here["id"], "you want something that keeps %s warm at night" % here["name"], "has something that keeps %s warm at night" % here["name"], 1.2, room=here["id"])
    for r in known:
        for n, o in things.made(r).items():
            if o["made"]["owner"] == pet["id"] and o["made"]["uses"] >= 3 and not o["made"]["ups"] and not o["made"].get("behavior") and not order.cap(cfg, o) \
                    and not craft.gated(cfg, o["made"]["recipe"].get("kind")):
                add("useless", n, "you want your %s to be good for something" % n, "made the %s into something that is good for something" % n, 0.6, thing=n, room=r["id"])
    for tool, at in pet.get("lacks", {}).items():
        if world_days(cfg, at, tick) < 2 and tool not in house.get("firsts", {}):
            add("tool", tool, "you want to " + C["tool"][tool]["want"], "has a tool: " + a(tool), 2.5, tool=tool)
    box = [b for b in pet.get("box", []) if world_days(cfg, b["tick"], tick) < 0.4]
    if any("forecast" in b["text"].lower() and RAIN.search(b["text"].split("Tomorrow")[0]) for b in box) and house["weather"] not in ("rain", "storm"):
        for r in known:
            for n, o in r["objects"].items():
                if o.get("fix", {}).get("window") and o.get("state") == "open":
                    add("window", "%s|%s" % (r["id"], n), "the box said rain is coming: you want the %s in %s shut before it does" % (n, r["name"]),
                        "shut the %s in %s before the rain" % (n, r["name"]), 2.0, room=r["id"], thing=n)
    # for someone: kin who is not at ease, a young one with nothing to play with, something heard that wants telling, a game
    for p in kin:
        if not p["sleep"] and p["needs"]["comfort"] < cfg["wants"]["uneasy_below"]:
            add("comfort", p["id"], "you want to bring %s something, who is not at ease" % label(p), "brought %s something" % label(p), 1.2, who=p["id"])
        if p["stage"] in ("hatchling", "child") and not any(o["made"]["owner"] == p["id"] and things.prop(cfg, o).get("use", {}).get("curiosity") for r in known for o in things.made(r).values()):
            add("toy", p["id"], "you want %s to have something of its own to play with" % label(p), "gave %s something to play with" % label(p), 1.2, who=p["id"])
        if not p["sleep"] and p["room"] == pet["room"] and any("toy" in o.get("fix", {}) or o.get("made", {}).get("recipe", {}).get("kind") == "ball" for o in here["objects"].values()):
            add("game", p["id"], "you want a game with %s" % label(p), "had a game with %s" % label(p), 0.8, who=p["id"])
    if box and kin and pet.get("told_box", LONG_AGO) < box[-1]["tick"]:
        add("tell", str(box[-1]["tick"]), "you want to tell someone what the box said", "told someone what the box said", 1.3, at=box[-1]["tick"])
    # of the family: what a parent knew, a song of theirs
    parent = house["pets"].get(pet.get("parent") or "")
    for key in (parent or {}).get("recipes", {}):
        if key not in pet.get("recipes", {}) and not key.startswith("kind:"):
            what = C["meets"][frozenset(key.split("+"))]["name"] + " things" if "+" in key else "a planted thing grow" if key.endswith("|plant") else C["rules"][tuple(key.split("|"))]["gives"]
            add("recipe", key, "your %s knew how to make %s; you want to find out how" % (relation(house, pet, parent) or "parent", what),
                "found out how to make %s, as its parent knew" % what, 1.4, recipe=key)
    mine = {e["id"] for e in pet.get("songs", [])}
    for p in kin:
        for e in p.get("songs", [])[:2]:
            song = house.get("songs", {}).get(e["id"]) if isinstance(house.get("songs"), dict) else None
            if e["id"] not in mine and song:
                add("song", e["id"], 'you want to learn the song %s sings, "%s"' % (label(p), song["name"]), 'learned the song "%s"' % song["name"], 0.9, song=e["id"])
                break
    # to get better: something finer than the last thing of a kind it made
    last = pet.get("last_made")
    if last and pet.get("made", 0) >= 2:
        add("finer", last["kind"], "you want to make something finer than your last %s" % last["kind"], "made a finer %s than its last" % last["kind"], 1.0, kind=last["kind"], at=last["tick"])
    return out


def gentle(cfg, room):
    return any(things.prop(cfg, o).get("shade") or things.prop(cfg, o).get("gentle") for o in things.made(room).values())


def warm(cfg, room):
    return any(things.prop(cfg, o).get("near", {}).get("night", {}).get("comfort", 0) > 0 for o in things.made(room).values())


def met(house, cfg, pet, w):
    """Is this want met, as the world stands?"""
    t, rooms = w["what"], house["rooms"]
    if t == "door":
        return w["room"] in pet["rooms"]
    if t == "creature":
        return pet["met"].get(w["kind"], 0) > 0
    if t == "bit":
        return w["bit"] in held(pet)
    if t == "try":
        return w["key"][4:] in pet.get("tried", {})
    if t == "word":
        return any(w["word"] in q for q in pet.get("asked", []))
    if t == "look":
        return w["thing"] in pet.get("looked", []) or w["thing"] not in rooms[w["room"]]["objects"]
    if t == "store":
        return not order.full(cfg, rooms[w["room"]])
    if t == "glow":
        return gentle(cfg, rooms[w["room"]])
    if t == "warm":
        return warm(cfg, rooms[w["room"]])
    if t == "useless":
        o = rooms[w["room"]]["objects"].get(w["thing"])
        return not o or "made" not in o or bool(o["made"]["ups"] or o["made"].get("behavior"))
    if t == "tool":
        return any(o["made"]["recipe"].get("kind") == w["tool"] for r in rooms.values() if r["type"] for o in things.made(r).values())
    if t == "window":
        return rooms[w["room"]]["objects"].get(w["thing"], {}).get("state") == "closed"
    if t in ("comfort", "toy"):
        g = pet.get("gave") or {}
        return g.get("tick", LONG_AGO) > w["since"] and g.get("to") == w["who"]
    if t == "game":
        return pet.get("played_with", {}).get(w["who"], LONG_AGO) > w["since"]
    if t == "tell":
        return (pet.get("said") or {}).get("tick", LONG_AGO) > w["since"] and bool((pet.get("said") or {}).get("to"))
    if t == "recipe":
        return w["recipe"] in pet.get("recipes", {})
    if t == "song":
        return any(e["id"] == w["song"] for e in pet.get("songs", []))
    if t == "finer":
        last = pet.get("last_made") or {}
        return last.get("tick", LONG_AGO) > w["since"] and last.get("kind") == w["kind"] and bool(last.get("new"))
    return False


SERVED = ("door", "creature", "bit", "look", "try", "game", "word")   # the wants its body can do something about without being told


def possible(house, cfg, pet, w):
    """Can this still be had? (The bit it was about may have been used up, the creature gone, the thing taken apart.)"""
    t, rooms = w["what"], [house["rooms"][r] for r in pet["rooms"] if house["rooms"][r]["type"]]
    lying = lambda bit: any(s["bit"] == bit and s["ready"] and not s.get("on") for r in rooms for s in r["spots"])
    if t == "bit":
        return lying(w["bit"])
    if t == "try":
        return w["bit"] in pet["carrying"] or lying(w["bit"])
    if t == "creature":
        return any(c["kind"] == w["kind"] for c in house["creatures"])
    if t in ("game", "comfort", "toy"):
        return house["pets"].get(w["who"], {}).get("stage", "dead") not in ("egg", "dead")
    return True


def refresh(house, cfg, pet):
    """Once every few ticks for each pet awake: wants that are met are fulfilled, old ones fade, and new ones come
    up to three, no two of a kind, weighted by what the pet is like."""
    W, tick = cfg["wants"], house["tick"]
    hear(house, cfg, pet)
    wants = pet.setdefault("wants", [])
    for w in list(wants):
        try:
            done = met(house, cfg, pet, w)
        except (KeyError, TypeError):   # (what it was about is gone from the house)
            done, w["gone"] = False, True
        if done:
            fulfil(house, cfg, pet, w)
        elif w.get("gone") or not possible(house, cfg, pet, w) or world_days(cfg, w["since"], tick) >= W["fade_days"]:
            wants.remove(w)
            pet.setdefault("wanted", {})[w["key"]] = tick
    if len(wants) >= W["most"]:
        return
    wanted, T, r = pet.setdefault("wanted", {}), pet["temper"], rnd(house, "wants", pet["id"], tick)
    have, groups = {w["key"] for w in wants}, [GROUPS[w["what"]] for w in wants]
    cands = []
    for c in candidates(house, cfg, pet):
        if c["key"] in have or world_days(cfg, wanted.get(c["key"], LONG_AGO), tick) < W["again_days"]:
            continue
        try:
            if met(house, cfg, pet, dict(c, since=tick)):
                continue
        except (KeyError, TypeError):
            continue
        lean = 1.0 + sum((T.get(g, 0.5) - 0.5) * 2 for g, kinds in LEANS.items() if c["what"] in kinds)
        recent = sum(1 for k, at in wanted.items() if k.split(":")[0] == c["what"] and world_days(cfg, at, tick) < 1)   # the kinds it has just had come up less
        cands.append((c["weight"] * max(0.2, lean) / (1 + 0.5 * recent) * r.uniform(0.6, 1.4), c))
    ranked = sorted(cands, key=lambda x: -x[0])
    if not any(w["what"] in SERVED for w in wants):   # one of the three is always something its body can do something about, if there is any such thing
        ranked.sort(key=lambda x: x[1]["what"] not in SERVED)
        ranked = ranked[:1] + sorted(ranked[1:], key=lambda x: -x[0])
    for _, c in ranked:
        if len(wants) >= W["most"]:
            break
        if GROUPS[c["what"]] in groups and (c["what"] in [w["what"] for w in wants] or groups.count(GROUPS[c["what"]]) >= 2):
            continue   # (no two of one kind, and never all three of one sort: no single kind of want crowds out the rest)
        c.pop("weight")
        wants.append(dict(c, since=tick))
        groups.append(GROUPS[c["what"]])
    if len(wanted) > 60:
        for k in sorted(wanted, key=wanted.get)[:20]:
            del wanted[k]


def fulfil(house, cfg, pet, w):
    """A want is met: a lift, a burst over it, a moment; and room for another."""
    from .actions import bump
    pet["wants"].remove(w)
    pet.setdefault("wanted", {})[w["key"]] = house["tick"]
    pet["fulfilled"] = pet.get("fulfilled", 0) + 1
    felt = "something settled in you" if GROUPS[w["what"]] == "know" else "you feel proud"
    add_event(house, pet, "%s, as you wanted: %s" % (w["done"].replace("its ", "your "), felt))
    bump(pet, cfg, dict(cfg["wants"]["lift"]))
    text = "%s %s" % (label(pet), w["done"])
    moment(house, "want", text, pet["id"], pet["room"])
    craft.burst(house, pet, "want", text)
    if w["what"] == "window":
        pet["prepared"] = {"tick": house["tick"], "thing": w["thing"]}
    if w["what"] == "tell":
        pet["told_box"] = house["tick"]
    if w["what"] == "try" and pet.get("hints"):
        pet["hints"] = [h for h in pet["hints"] if "%s|%s" % (h["bit"], h["how"]) != w["key"][4:]]


def hear(house, cfg, pet):
    """What the box has said since it last took stock: one word of it that it has never heard before stays with it as
    a thing to wonder about (§4.2); and if it shut a window for the rain, the rain coming is felt (§4.2)."""
    from .actions import bump
    seen, words = pet.get("box_seen", LONG_AGO), pet.setdefault("words", [])
    for b in [b for b in pet.get("box", []) if b["tick"] > seen]:
        heard = [w for w in re.findall(r"[a-z]{6,}", b["text"].lower()) if w not in words]
        if max(map(len, heard), default=0) >= 8 and not b["text"].startswith("The forecast"):   # (a long word: short ones are mostly ones it only seems not to know)
            pet["unknown"] = (pet.get("unknown", []) + [max(heard, key=len)])[-4:]
        words += [w for w in dict.fromkeys(heard)]
        pet["box_seen"] = b["tick"]
    del words[:-500]
    p = pet.get("prepared")
    if p and house["weather"] in ("rain", "storm") and world_days(cfg, p["tick"], house["tick"]) < 1:
        add_event(house, pet, "the rain came and the %s was shut: your things stayed dry" % p["thing"])
        bump(pet, cfg, {"comfort": cfg["wants"]["lift"].get("comfort", 0)})
        pet["prepared"] = None


def hinted(house, cfg, pet, title, text):
    """What it has just read may point at something to try (§4.1): a hint, never a recipe. Returns the words of the
    hint, or ""."""
    low = ("%s %s" % (title, text)).lower()
    for h in cfg["craft"].get("hint", []):
        key = "%s|%s" % (h["bit"], h["how"])
        if all(any(alt in low for alt in m.split("|")) for m in h["match"]) and key not in pet.get("tried", {}) and not any(x["bit"] == h["bit"] and x["how"] == h["how"] for x in pet.get("hints", [])):
            pet["hints"] = (pet.get("hints", []) + [{"bit": h["bit"], "how": h["how"], "tick": house["tick"]}])[-4:]
            return "it makes you want to find out " + TRY[h["how"]] % a(h["bit"])
    return ""


def lines(pet):
    return [w["text"] for w in pet.get("wants", [])]


def lean(house, cfg, pet):
    """What its body leans toward for the sake of its wants: {rooms: the rooms to make for, doors: doors not yet
    tried that it may now go through, gather: bits to pick up, creatures: kinds to get close to, place: (how, bit,
    want) to carry a bit to in this room, play: who to play with}."""
    out = {"rooms": set(), "doors": set(), "gather": set(), "creatures": set(), "place": None, "play": set(), "look": set()}
    here = pet["room"]
    for w in pet.get("wants", []):
        t = w["what"]
        if t == "door":
            out["doors" if w["frm"] == here else "rooms"].add(w["door"] if w["frm"] == here else w["frm"])
        elif t == "creature":
            where = next((c["room"] for c in house["creatures"] if c["kind"] == w["kind"]), None)
            (out["creatures"].add(w["kind"]) if where == here else out["rooms"].add(where) if where in pet["rooms"] else None)
        elif t == "bit":
            (out["gather"].add(w["bit"]) if any(s["bit"] == w["bit"] and s["ready"] for s in house["rooms"][here]["spots"]) else out["rooms"].add(w["room"]))
        elif t == "try":
            need = 2 if cfg["craft"]["process"].get(w["how"], {}).get("pair") else 1
            if craft.to_hand(pet, house["rooms"][here], w["bit"]) < need and pet["carrying"].count(w["bit"]) < need:
                (out["gather"].add(w["bit"]) if any(s["bit"] == w["bit"] and s["ready"] for s in house["rooms"][here]["spots"]) else out["rooms"].add(w.get("bit_room")))
            elif pet["carrying"].count(w["bit"]) < need:
                out["gather"].add(w["bit"])
            elif craft.place(house, cfg, house["rooms"][here], w["how"]) is not None:
                out["place"] = out["place"] or (w["how"], w["bit"], w["key"])
            else:
                out["rooms"].add(w["room"])
        elif t == "word":   # where the book is now (it can be carried): over to it, and its mind may ask (or, left long enough, it leafs through by itself)
            book = book_room(house)
            if book == here:
                out["place"] = out["place"] or ("ask", w["word"], w["key"])
            elif book in pet["rooms"]:
                out["rooms"].add(book)
        elif t in ("store", "glow", "warm", "window") and w.get("room") and w["room"] != here:
            out["rooms"].add(w["room"])
        elif t == "game":
            out["play"].add(w["who"])
        elif t == "look":
            (out["look"].add(w["thing"]) if w["room"] == here else out["rooms"].add(w["room"]))
    out["rooms"].discard(None)
    out["rooms"].discard(here)
    return out
