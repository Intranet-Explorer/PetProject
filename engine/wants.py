"""Wants (SPEC-v3.4 §2.1): up to three concrete, short-lived things a pet wants, made by the engine from where it is,
what it has and has not done, and what it is like. No model is asked. Its mind is told them in plain words and may
take one up or leave them all; its body leans toward whatever serves one. A want is met when the world shows it is
(the room is known, the bit has been held, the thing has been tried): that is felt, seen, and written down, and
another takes its place. One left alone for a world day fades."""
import re

from . import craft, genes, invent, order, things
from . import season
from . import build
from . import machine
from . import hub
from .world import LONG_AGO, ONE, a, add_event, arrived, days as world_days, label, moment, relation, rnd

GROUPS = {"door": "know", "creature": "know", "bit": "know", "try": "know", "word": "know", "look": "know",
          "store": "better", "glow": "better", "warm": "better", "useless": "better", "tool": "better", "window": "better",
          "comfort": "someone", "toy": "someone", "tell": "someone", "game": "someone",
          "recipe": "family", "song": "family", "finer": "skill", "get": "get", "plant": "tend", "pick": "tend", "keep": "tend", "join": "skill"}
# which temperament leans toward which kind of want (§2.1): gene -> the wants it weights up
LEANS = {"curious": ("bit", "try", "word", "door", "creature", "look"), "bold": ("door", "creature"), "orderly": ("store", "glow", "warm", "useless", "tool", "window", "keep"),
         "sociable": ("comfort", "toy", "tell"), "playful": ("toy", "game"), "patient": ("recipe", "song", "finer")}
TRY = {"soak": "what water does to %s", "warm": "what warmth does to %s", "melt": "what heat does to %s", "dry": "what becomes of %s left to dry",
       "press": "what becomes of %s under something heavy", "weave": "what comes of weaving %s", "carve": "what could be carved out of %s",
       "grind": "what grinding does to %s", "plant": "whether %s would grow in the earth"}
GROUPS.update(build="build", paint="build", name="family")   # (name: SPEC-v3.5.1 §4, the founder's statue)   # SPEC-v3.5 §4: to build what a room lacks, and to paint it (engine/build.py)
LEANS.update(orderly=LEANS["orderly"] + ("build",), playful=LEANS["playful"] + ("paint",))
RAIN = re.compile(r"\b(rain|drizzle|showers?|thunderstorms?|snow)\b", re.I)


STEP = ("get", "try", "plant")   # wants that are a bit carried to where something is done to it: its body does these the same way
some = a   # SPEC-v3.5.8 §3: never "some clay": "clay", "a seed"


def named(cfg, pet):
    """What its wants name that it has not got (13 October 2026: a want that names a thing leads to a want to get
    it): [(the bit, the want that names it)]. What a tool it wants is made of, once it has been told or has read
    it; what a parent knew how to make. ponytail: one step deep; a thing made of a thing made of a thing is found
    when the first step is in its paws and something else names the next."""
    C, out = cfg["craft"], []
    for w in pet.get("wants", []):
        if w["what"] == "tool" and w["tool"] in pet.get("takes", []):
            out += [(alt, w["key"]) for g in C["needs"][w["tool"]] if not any(x in pet["carrying"] for x in g.split("|")) for alt in g.split("|")]
        elif w["what"] == "recipe" and "|" in w["recipe"] and not w["recipe"].endswith("|plant"):
            out.append((C["rules"][tuple(w["recipe"].split("|"))]["gives"], w["key"]))
    return [(bit, key) for bit, key in out if bit not in pet["carrying"]]


def held(pet):
    """Every bit it has ever had in its paws."""
    return {b for bits in pet.get("gathered", {}).values() for b in bits} | set(pet.get("carrying", [])) | {v for v in pet.get("tried", {}).values() if isinstance(v, str)}


def door_words(house, pet, rid, d):
    return "the %s door%s" % (d, "" if rid == pet["room"] else " of %s" % house["rooms"][rid]["name"])


def book_room(house):
    """Where to go to look something up: the machine room's screens once they are found and lit (SPEC-v3.5.1 §3:
    several can read there at once, and sooner again), else wherever the heavy book is."""
    lit = arrived(house, "book")
    rooms = [r for r in house["rooms"].values() if r["type"] and any(o.get("fix", {}).get("book") and (lit or not o["fix"].get("terminal")) for o in r.get("objects", {}).values())]
    return next((r["id"] for r in sorted(rooms, key=lambda r: not any(o.get("fix", {}).get("terminal") for o in r["objects"].values()))), None)


def book_words(house, rid):
    return "the screens in %s" % house["rooms"][rid]["name"] if any(o.get("fix", {}).get("terminal") for o in house["rooms"][rid]["objects"].values()) \
        else "the heavy book in %s" % house["rooms"][rid]["name"]


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
    via = machine.source(house, cfg, pet, known, grown)   # SPEC-v3.5 §4.3: a base material that is not lying about, or is short, is to be had from the machine
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
    # to get what another want names (13 October 2026): it lies about somewhere, or something it can reach becomes it
    mine = {w["key"] for w in pet.get("wants", [])}
    for bit, parent in named(cfg, pet) + build.named(house, cfg, pet):   # (SPEC-v3.5 §4: and a material that has to be made, a hammer's makings, a dye)
        if bit in grown:
            add("get", bit, "you want %s%s" % (some(bit), "" if grown[bit] == here["id"] else " (there is some in %s)" % rooms[grown[bit]]["name"]),
                "has %s now" % some(bit), 4.0, bit=bit, gives=bit, room=grown[bit], parent=parent)
        for (src, how), rule in C["rules"].items():
            key = "%s|%s" % (src, how)
            where = craft.places(house, cfg, pet, how)
            if rule.get("gives") != bit or not where or not (src in pet["carrying"] or src in grown) or "try:" + key in mine \
                    or craft.skill(cfg, pet, "making") < C["process"].get(how, {}).get("skill", 0):
                continue
            knows = isinstance(tried.get(key), str)   # what it has found out it sets about; what it has not, it wants to find out
            needs = C["process"].get(how, {}).get("tool")   # (what takes a tool nobody has comes a long way after what can be done now)
            add("get", key, "you want to %s %s, for the %s" % (how, some(src), bit) if knows else "you want to find out " + TRY[how] % a(src),
                "has %s now" % some(bit), (5.0 if knows else 4.0) * (0.2 if needs and not craft.tool_for(house, cfg, pet, needs) else 1.0), bit=src, how=how, gives=bit, room=where[0], bit_room=grown.get(src), parent=parent)
    stepped = {c["key"][4:] for c in out if c["what"] == "get"}
    out[:] = [c for c in out if c["what"] != "try" or c["key"][4:] not in stepped]   # (the same thing is not wanted twice over)
    machine.wants(house, cfg, pet, known, out, add, via)   # SPEC-v3.5 §4.3: to see what the machine has; to feed it what is spare
    for w in pet.get("unknown", [])[-3:]:
        book = book_room(house)
        hint = "" if not book or pet.get("asked") else "; %s might know" % book_words(house, book)
        why = "you have been close to one" if w in pet["met"] else "the box said it"
        add("word", w, 'you want to know what %s is: %s%s' % ("a " + w if w in pet["met"] else '"%s"' % w, why, hint), 'asked what "%s" is' % w, 1.2, word=w, room=book if book in pet["rooms"] else None)
    # to tend (13 October 2026): bare earth and a seed to be had, and it wants to plant (one who tends, most); something ripe, and it wants to pick it
    seeds = [b for b in C["grow"] if b in pet["carrying"]] + [b for b in C["grow"] if b in grown]
    digs = craft.tool_for(house, cfg, pet, "trowel") or craft.by_paw(house, pet) < C["growing"]["paw_plants"]
    for r in known:
        for n, o in r["objects"].items():
            p, at = o.get("planted"), "the %s in %s" % (n, r["name"])
            if seeds and digs and craft.plantable(cfg, n, o) and not season.dormant(house, cfg, r):   # (SPEC-v3.5 §5: not in earth asleep under snow)
                add("plant", "%s|%s" % (r["id"], n), "the earth of %s is bare: you want to plant %s there" % (at, a(seeds[0])), "planted %s in the %s" % (a(seeds[0]), n),
                    1.5 * (1 + craft.skill(cfg, pet, "tending")), bit=seeds[0], how="plant", room=r["id"], thing=n, bit_room=grown.get(seeds[0]))
            elif p and p["grow"] >= 1 and not p.get("wilted"):
                add("pick", "%s|%s" % (r["id"], n), "what grows in %s is ripe: you want to pick it, and eat of it or leave some for the others" % at,
                    "picked what was ripe in the %s" % n, 1.5, room=r["id"], thing=n, at=p["at"])
    season.wants(house, cfg, pet, known, add)   # SPEC-v3.5 §5: in autumn, food lying loose is wanted put by before winter
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
            book = book_room(house)   # (13 October 2026) what a tool takes is said when making one fails; until then the book is where to look
            one = "%s %s" % ("an" if tool[0] in "aeiou" else "a", tool)
            takes = "; you carry what %s takes: you could make one now" % one if tool in pet.get("takes", []) and not craft.lacking(cfg, tool, pet["carrying"]) else \
                "; %s takes %s" % (one, craft.takes(cfg, tool)) if tool in pet.get("takes", []) else \
                "; %s might know what one is made of" % book_words(house, book) if book and not asked_of(pet, tool) else ""
            add("tool", tool, "you want to " + C["tool"][tool]["want"] + takes, "has a tool: " + a(tool), 2.5, tool=tool)
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
    invent.want(house, cfg, pet, add)   # SPEC-v3.5 §3: two things here that nobody has joined before
    build.candidates(house, cfg, pet, add, known)   # SPEC-v3.5 §4: to build what a room lacks, to mend what was built, to paint
    hub.candidates(house, cfg, pet, add, known)   # SPEC-v3.5.1 §4: to name the founder's statue
    return out


def asked_of(pet, tool):
    """Has it looked in the book for what this tool is made of (or been told)?"""
    return tool in pet.get("takes", []) or tool in pet.get("asked_tool", [])


def reads(house, pet):
    """Is it old enough to read the book (and has the book come)? A hatchling is not."""
    from . import life
    return "ask_book" in life.unlocked(house, pet["stage"])


def elders(house, pet):
    """Who one too young to read could ask: the elders that are up, or with no elder the grown ones."""
    up = [p for p in house["pets"].values() if p is not pet and not p["sleep"] and p["stage"] in ("elder", "adult")]
    return [p for p in up if p["stage"] == "elder"] or up


def may_try(house, pet, tool):
    """May its mind try to make a tool it has not the stuff for? (Trying says what is missing.) Not before it has
    been to the book about it (13 October 2026), unless there is no book it can get to."""
    return asked_of(pet, tool) or book_room(house) not in pet["rooms"] or not reads(house, pet)


def question(house, cfg, pet, w):
    """What it could ask the book for the sake of this want, if it has not asked that already: a word, how a tool
    is made, the bit it wants to try something on, the thing a parent knew how to make."""
    t, C = w["what"], cfg["craft"]
    if t in ("build", "paint"):   # SPEC-v3.5 §4.1: how a hammer is made, when that is what the thing it is building waits on
        return build.question(house, cfg, pet, w)
    q = "what is %s" % w["word"] if t == "word" else "how do you %s" % C["tool"][w["tool"]]["want"] if t == "tool" and not asked_of(pet, w["tool"]) else \
        "what is %s" % w["bit"] if t == "try" or (t == "get" and w["text"].startswith("you want to find out")) else \
        "what is %s" % C["rules"][tuple(w["recipe"].split("|"))]["gives"] if t == "recipe" and "|" in w["recipe"] and not w["recipe"].endswith("|plant") else None
    return q if q and q not in pet.get("asked", []) else None


def gentle(cfg, room):
    return any(things.prop(cfg, o).get("shade") or things.prop(cfg, o).get("gentle") for o in things.made(room).values())


def warm(cfg, room):
    return any(things.prop(cfg, o).get("near", {}).get("night", {}).get("comfort", 0) > 0 for o in things.made(room).values())


def met(house, cfg, pet, w):
    """Is this want met, as the world stands?"""
    t, rooms = w["what"], house["rooms"]
    if t in ("build", "paint"):   # SPEC-v3.5 §4
        return build.met(house, cfg, pet, w)
    if t in machine.GROUPS:   # SPEC-v3.5 §4.3
        return machine.met(house, cfg, pet, w)
    if t == "door":
        return w["room"] in pet["rooms"]
    if t == "creature":
        return pet["met"].get(w["kind"], 0) > 0
    if t == "bit":
        return w["bit"] in held(pet)
    if t == "try":
        return w["key"][4:] in pet.get("tried", {})
    if t == "get":   # in its paws; or it has come of what it did since, and lies beside it (its arms were full)
        got = pet.get("got") or [None, LONG_AGO]
        return w["gives"] in pet["carrying"] or (got[0] == w["gives"] and got[1] >= w["since"])
    if t == "plant":
        p = rooms[w["room"]]["objects"][w["thing"]].get("planted") or {}
        return p.get("by") == pet["id"] and p.get("at", LONG_AGO) >= w["since"]
    if t == "pick":
        return (pet.get("picked") or {}).get("tick", LONG_AGO) >= w["since"] and pet["picked"]["thing"] == w["thing"]
    if t == "keep":
        return season.kept(pet, w)
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
        return any(craft.tool_kind(cfg, o) == w["tool"] for r in rooms.values() if r["type"] for o in things.made(r).values())
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
    if t == "join":
        return invent.want_met(house, pet, w)
    if t == "name":   # SPEC-v3.5.1 §4
        return not hub.unnamed(house, pet, house["rooms"][w["room"]])
    if t == "finer":
        last = pet.get("last_made") or {}
        return last.get("tick", LONG_AGO) > w["since"] and last.get("kind") == w["kind"] and bool(last.get("new"))
    return False


SERVED = ("door", "creature", "bit", "look", "try", "game", "word", "get", "plant", "pick", "keep")   # (and "tool", as far as the book: lean)   # the wants its body can do something about without being told

SERVED += ("build",)   # SPEC-v3.5 §4
GROUPS.update(machine.GROUPS); LEANS["orderly"] += machine.ORDERLY; SERVED += machine.SERVED; ONE += machine.ONE   # SPEC-v3.5 §4.3: the machine's own wants


def possible(house, cfg, pet, w):
    """Can this still be had? (The bit it was about may have been used up, the creature gone, the thing taken apart.)"""
    t, rooms = w["what"], [house["rooms"][r] for r in pet["rooms"] if house["rooms"][r]["type"]]
    lying = lambda bit: any(s["bit"] == bit and s["ready"] and not s.get("on") for r in rooms for s in r["spots"]) or machine.has(house, cfg, pet, bit)   # (SPEC-v3.5 §4.3: or in the machine)
    if t in ("build", "paint"):   # SPEC-v3.5 §4
        return build.possible(house, cfg, pet, w)
    if t in machine.GROUPS:
        return machine.possible(house, cfg, pet, w)
    if t == "bit":
        return lying(w["bit"])
    if t == "try":
        return w["bit"] in pet["carrying"] or lying(w["bit"])
    if t == "get":   # (a step toward another want: gone when that one is)
        return (w["bit"] in pet["carrying"] or lying(w["bit"])) and any(x["key"] == w["parent"] for x in pet["wants"])
    if t == "plant":
        o = house["rooms"][w["room"]]["objects"][w["thing"]]
        return (craft.plantable(cfg, w["thing"], o) or (o.get("planted") or {}).get("by") == pet["id"]) and (w["bit"] in pet["carrying"] or lying(w["bit"]))
    if t == "pick":
        p = house["rooms"][w["room"]]["objects"][w["thing"]].get("planted") or {}
        return p.get("at") == w["at"] and not p.get("wilted") or (pet.get("picked") or {}).get("tick", LONG_AGO) >= w["since"]
    if t == "creature":
        return any(c["kind"] == w["kind"] for c in house["creatures"])
    if t == "keep":
        return bool(season.loose_food(cfg, house["rooms"][w["room"]]))
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
        if done and w["what"] == "get" and not any(x["key"] == w["parent"] for x in wants):
            wants.remove(w)   # (what it was a step toward was met by the same deed: that is the one that is felt and written down)
        elif done:
            fulfil(house, cfg, pet, w)
        elif w.get("gone") or not possible(house, cfg, pet, w) or world_days(cfg, w.get("touched", w["since"]), tick) >= W["fade_days"]:
            wants.remove(w)
            pet.setdefault("wanted", {})[w["key"]] = tick
    count = lambda: sum(w["what"] != "get" for w in wants)   # (a step toward another want is not one of the three)
    wanted, T, r = pet.setdefault("wanted", {}), pet["temper"], rnd(house, "wants", pet["id"], tick)
    have, groups = {w["key"] for w in wants}, [GROUPS[w["what"]] for w in wants]
    cands = []
    fresh = candidates(house, cfg, pet)
    for w in wants:   # (what a want says follows what it now knows: "a carver takes sharp stone or fired clay")
        w["text"] = next((c["text"] for c in fresh if c["key"] == w["key"]), w["text"])
    for c in fresh:
        if c["key"] in have or (c["what"] != "get" and world_days(cfg, wanted.get(c["key"], LONG_AGO), tick) < W["again_days"]):
            continue
        try:
            if met(house, cfg, pet, dict(c, since=tick)):
                continue
        except (KeyError, TypeError):
            continue
        lean = (1.0 + sum((T.get(g, 0.5) - 0.5) * 2 for g, kinds in LEANS.items() if c["what"] in kinds)) * genes.whiskers(pet, c)   # (SPEC-v3.5 §2.3: whiskers notice bits and creatures sooner)
        recent = sum(1 for k, at in wanted.items() if k.split(":")[0] == c["what"] and world_days(cfg, at, tick) < 1)   # the kinds it has just had come up less
        cands.append((c["weight"] * max(0.2, lean) / (1 + 0.5 * recent) * r.uniform(0.6, 1.4), c))
    ranked = sorted(cands, key=lambda x: -x[0])
    if not any(w["what"] in SERVED for w in wants):   # one of the three is always something its body can do something about, if there is any such thing
        ranked.sort(key=lambda x: x[1]["what"] not in SERVED)
        ranked = ranked[:1] + sorted(ranked[1:], key=lambda x: -x[0])
    for _, c in ranked:
        if count() >= W["most"] and c["what"] != "get":
            continue
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
    for x in pet["wants"]:
        if x["key"] == w.get("parent"):
            x["touched"] = house["tick"]   # (a want being worked toward is not one left alone)
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
        # 13 October 2026: a thing it could picture (picturable.txt), not the longest word: "association" and
        # "subsequently" are nothing to wonder about, and the book has nothing to show for them
        heard = [w for w in dict.fromkeys(filter(None, (noun(cfg, w) for w in re.findall(r"[a-z]{3,}", b["text"].lower())))) if w not in words]
        if heard:   # (the forecast too: frost, thunder)
            pet["unknown"] = (pet.get("unknown", []) + heard[:1])[-4:]
        words += heard
        pet["box_seen"] = b["tick"]
    # a creature it has been close to is a thing to wonder about too: one a world day
    new = next((k for k, n in pet["met"].items() if n and k not in words), None)
    if new and pet.get("creature_word") != house["clock"]["day"]:
        pet["unknown"], pet["creature_word"] = (pet.get("unknown", []) + [new])[-4:], house["clock"]["day"]
        words.append(new)
    del words[:-500]
    p = pet.get("prepared")
    if p and house["weather"] in ("rain", "storm") and world_days(cfg, p["tick"], house["tick"]) < 1:
        add_event(house, pet, "the rain came and the %s was shut: your things stayed dry" % p["thing"])
        bump(pet, cfg, {"comfort": cfg["wants"]["lift"].get("comfort", 0)})
        pet["prepared"] = None


def noun(cfg, word):
    """The thing this word names, if it is one a pet could picture ("ships" -> "ship"), else None."""
    return next((w for w in (word, word[:-1] if word.endswith("s") else "", word[:-2] if word.endswith("es") else "", word[:-3] + "y" if word.endswith("ies") else "")
                 if w in cfg.get("picturable", ())), None)


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
    out = {"rooms": set(), "doors": set(), "gather": set(), "creatures": set(), "place": None, "play": set(), "look": set(), "pick": set(), "ask": None}
    here, book = pet["room"], book_room(house)
    young = not reads(house, pet)
    waits = hub.wait_hours(cfg, house["rooms"][book]) if book else cfg["book"]["per_hours"]   # (less long, at a screen)
    rested = not young and house["tick"] - pet.get("asked_at", LONG_AGO) >= waits * cfg["ticks_per_hour"]   # (its eyes are up to the small writing again)
    for w in sorted(pet.get("wants", []), key=lambda w: w["what"] != "get"):   # (a step toward another want comes first)
        t = w["what"]
        q = question(house, cfg, pet, w) if rested or young else None
        if q and young:   # too young to read: it goes to the nearest elder instead, to ask out loud; once for each thing it wants to know
            if q not in pet.get("asked_aloud", []):
                old = elders(house, pet)
                near = next((p for p in old if p["room"] == here), None)
                if near:
                    out["ask"] = out["ask"] or ("ask", q, w["key"], near["id"])
                else:
                    out["rooms"] |= {p["room"] for p in old if p["room"] in pet["rooms"]}
        elif q and any(o.get("fix", {}).get("book") for o in house["rooms"][here]["objects"].values()):   # (13 October 2026) a book is in the room and might know: it is drawn over to it
            out["ask"] = out["ask"] or ("ask", q, w["key"])
        elif q and t in ("word", "tool") and book in pet["rooms"]:   # ... and for a word or a tool it goes to where the book is
            out["rooms"].add(book)
        if t == "door":
            out["doors" if w["frm"] == here else "rooms"].add(w["door"] if w["frm"] == here else w["frm"])
        elif t == "creature":
            where = next((c["room"] for c in house["creatures"] if c["kind"] == w["kind"]), None)
            (out["creatures"].add(w["kind"]) if where == here else out["rooms"].add(where) if where in pet["rooms"] else None)
        elif t == "bit":
            (out["gather"].add(w["bit"]) if any(s["bit"] == w["bit"] and s["ready"] for s in house["rooms"][here]["spots"]) else out["rooms"].add(w["room"]))
        elif t == "get" and not w.get("how"):
            (out["gather"].add(w["bit"]) if any(s["bit"] == w["bit"] and s["ready"] for s in house["rooms"][here]["spots"]) else out["rooms"].add(w["room"]))
        elif t == "pick":
            (out["pick"].add(w["thing"]) if w["room"] == here else out["rooms"].add(w["room"]))
        elif t in STEP:
            need = 2 if cfg["craft"]["process"].get(w["how"], {}).get("pair") else 1
            if craft.to_hand(pet, house["rooms"][here], w["bit"]) < need and pet["carrying"].count(w["bit"]) < need:
                (out["gather"].add(w["bit"]) if any(s["bit"] == w["bit"] and s["ready"] for s in house["rooms"][here]["spots"]) else out["rooms"].add(w.get("bit_room")))
            elif pet["carrying"].count(w["bit"]) < need:
                out["gather"].add(w["bit"])
            elif craft.place(house, cfg, house["rooms"][here], w["how"]) is not None and (t != "plant" or w["room"] == here):
                out["place"] = out["place"] or (w["how"], w["bit"], w["key"])
            else:
                out["rooms"].add(w["room"])
        elif t in ("store", "glow", "warm", "window", "keep") and w.get("room") and w["room"] != here:
            out["rooms"].add(w["room"])
        elif t == "game":
            out["play"].add(w["who"])
        elif t == "look":
            (out["look"].add(w["thing"]) if w["room"] == here else out["rooms"].add(w["room"]))
        elif t in ("build", "paint"):   # SPEC-v3.5 §4: the bits it takes, the room it is in, the book about a hammer
            build.lean(house, cfg, pet, w, out)
    machine.lean(house, cfg, pet, out)   # SPEC-v3.5 §4.3: `vend`, `feed`, and the way to the machine
    out["rooms"].discard(None)
    out["rooms"].discard(here)
    return out
