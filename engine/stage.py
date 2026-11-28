"""SPEC-v4.2 §8 the director (helper D): once a world day, at midnight, one model call (the house's narrator, kind
"director") chooses what tomorrow brings from a bounded menu (stage.toml), or nothing, which is most nights. It is told
the last seven days of the chronicle, who is alive (stage, drive, a secret kept or not, bonds and grudges, in words),
the season and tomorrow's sky, who died of what lately, and the menu; it answers one happening, its target (a hob or a
room) and one plain sentence of why (SPEC-v4.2.2 §4: as a neighbour would say it). It is told no numbers.

The rules (§8.3) are the engine's, not the model's: only what may come is offered (never two hard happenings in a row,
none hard while the house is under the floor, none before its cooldown, none whose makings are not in the house), and
nothing kills: each happening leaves a condition (§2 decides the rest). A happening is foreshadowed at dusk the
evening before where that makes sense (`omen`), and lands at dawn (EFFECTS): a moment "happening" (the morning's
banner, the chronicle's line), a memory of weight 3 for every hob awake, `house["happening"]` (today's) and
`house["happenings"]` (the week's), contracts.happening records both, and a line in the ledger.

The old `director.events` keeps the small things; with [stage] on its power cuts and leaks, and a storm's power cut,
come only from here. Switch: [stage] on (contracts.on). house["director"] = {"asked": the day it last asked, "omen":
the day it last foreshadowed, "sky": [day, weather] the director's own sky for a day}; house["coming"]: the choices
waiting for their dawn (tomorrow's, and for a few hours after midnight, today's too)."""
import asyncio
import logging
import re
import tomllib
from pathlib import Path

from . import contracts as K
from . import director, health, hooks, life, memories, things
from .world import a as a_bit, add_event, alive, bit_kinds, days as world_days, family, free_tile, hours, label, moment, new_pet, rnd, weather_of

MENU = tomllib.loads((Path(__file__).resolve().parent.parent / "stage.toml").read_text())
AGO = ("yesterday", "two days ago", "three days ago", "four days ago", "five days ago", "six days ago", "a week ago")


def on(cfg):
    return K.on(cfg, "stage")


def today(house):
    """Today's happening, or None."""
    h = house.get("happening")
    return K.happening(h) if isinstance(h, dict) and h.get("day") == house["clock"]["day"] else None


def S(house):
    return house.setdefault("director", {"asked": None, "omen": None, "sky": None})


def sky(house):
    """The director's own weather for today, or None (director.real_weather leaves it be)."""
    s = (house.get("director") or {}).get("sky")
    return s[1] if s and s[0] == house["clock"]["day"] else None


# ---- what may come ----

def living(house):
    return sorted((p for p in alive(house) if p["stage"] != "egg"), key=lambda p: p["id"])


def shelf_rooms(house, cfg):
    F = cfg.get("seasons", {}).get("food", {}).get("bits", {})
    return [r for r in director.found(house) if any(s["bit"] in F and s.get("on") and not s.get("spoiled") and not health.keeps(cfg, r, s["on"]) for s in r["spots"])]


def owned(house):
    """Made things a living hob owns that could go missing (not fixed, not on a wall, not outdoors)."""
    return [(x, n) for x in director.found(house) if not x.get("outdoor") for n, o in things.made(x).items()
            if house["pets"].get(o["made"]["owner"], {}).get("stage") not in (None, "dead", "egg") and not o.get("wall")]


def makings(house, cfg):
    """Each happening's makings: can it come in the house as it is?"""
    from . import visitor
    season, pop = house["clock"]["season"], cfg.get("population", {})
    v5 = K.on(cfg, "visitor5") and visitor.on(cfg)
    return {"nothing": True, "storm": True, "buried": any(r["type"] == "garden" for r in director.found(house)),
            "stranger_egg": len(alive(house)) < pop.get("most", 7) and not any(p["stage"] == "egg" for p in alive(house)),
            "bad_food": health.deaths(cfg) and bool(shelf_rooms(house, cfg)), "missing": bool(owned(house)),
            "cold_snap": health.deaths(cfg) and season not in ("winter",), "heat_wave": season in ("spring", "summer"),
            "leak": True, "power_cut": True, "letter": v5 and bool(visitor.unread(house)), "dream": any(p["stage"] != "hatchling" for p in living(house)),
            "train": True, "creature": True, "visitor_gone": v5 and visitor.away(house, cfg) >= cfg["visitor5"]["gone_days"]}


def offered(house, cfg, day):
    """The names the narrator may choose from for `day`: §8.3's rules, cooldowns and makings."""
    week = [x for x in house.get("happenings") or [] if x["day"] < day]
    last_hard = bool(week) and week[-1]["hard"]   # (the day before's: the week is kept in day order)
    can = makings(house, cfg)
    out = []
    for name, hard in K.HAPPENINGS.items():
        if not can.get(name) or (hard and (last_hard or life.floor(house, cfg))):
            continue
        if name != "nothing" and any(x["name"] == name and day - x["day"] < MENU[name]["cooldown"] for x in week):
            continue
        out.append(name)
    return out


# ---- the call ----

def unnumbered(text):
    """No numbers for the narrator either: "12 days old" and the like go."""
    text = re.sub(r",? *\b\d+(\.\d+)? (world )?(days?|hours?)( old)?", "", text or "")
    return re.sub(r"\s{2,}", " ", re.sub(r"\b\d+(\.\d+)?\b", "", text)).strip()


def who_line(house, p):
    from . import bonds
    bits = ["%s, %s %s" % (label(p), "an" if p["stage"][0] in "aeiou" else "a", p["stage"])]
    if p.get("drive"):
        bits.append("wants " + K.drive(p["drive"])["name"])
    if p.get("secret") and not K.secret(p["secret"])["found"]:
        bits.append("keeps something to itself")
    close = house["pets"].get(bonds.close(house, p) or "")
    if close and close["stage"] not in ("egg", "dead"):
        bits.append("close to %s" % label(close))
    grudges = [house["pets"][g["against"]] for g in house.get("grievances", []) if g["by"] == p["id"] and g["against"] in house["pets"]]
    if grudges:
        bits.append("holds a grudge against %s" % " and ".join(label(x) for x in grudges[:2]))
    ill = health.stage_of(p) or (p.get("hurt") or {}).get("level")
    if ill:
        bits.append("is %s" % ill)
    return "; ".join(bits)


def packet(house, cfg, menu):
    """What the narrator is told (§8.1), and the stub's context."""
    from . import hub, visitor
    day, c = house["clock"]["day"], house["clock"]
    days = [e for e in house.get("chronicle", []) if day - 8 < e["day"] < day][-cfg["stage"]["chronicle_days"]:]
    told = ["%s: %s" % (AGO[min(6, day - 1 - e["day"])], unnumbered(e.get("text") or "; ".join(e["lines"][-6:]) or e["summary"])) for e in days]
    dead = [p for p in house["pets"].values() if p["stage"] == "dead" and p.get("died") is not None and world_days(cfg, p["died"], house["tick"]) <= 7]
    hobs = living(house)
    lines = ["You decide what happens tomorrow in a house of hobs, who live, make things, grow old and die. Each night you pick from a short "
             "menu. Most nights nothing happens, and that is right: pick something only when the house could do with it, and never to kill: "
             "what you pick makes trouble or something to wonder at, never a death.",
             "The last days, as the house's chronicle tells them:\n" + ("\n".join(told) or "nothing written yet"),
             "Who is alive:\n" + "\n".join(who_line(house, p) for p in hobs),
             "It is %s. Tomorrow's sky looks to be %s." % (c["season"], hub.SAID.get(weather_of(house, cfg, day + 1), "fair"))]
    if dead:
        lines.append("Lately: " + "; ".join("%s %s" % (label(p), p.get("cause_words") or "died of %s" % p.get("cause")) for p in dead))
    if K.on(cfg, "visitor5") and visitor.on(cfg) and visitor.away(house, cfg) >= cfg["visitor5"]["absent_days"]:
        lines.append("The visitor, whom the hobs cannot see, has not been felt in the house for some days.")
    lines.append("The menu (choose one):\n" + "\n".join("- %s: %s" % (n, MENU[n]["menu"]) for n in menu))
    lines.append('Reply with one JSON object and nothing else: {"name": "<one of the menu>", "target": "<the hob or the room it falls on, or empty>", '
                 '"why": "<one plain sentence a neighbour would say about it, no poetry>"}\n'
                 'For example, "why": "The rain got in through the attic roof last night." or "why": "Something was dug up by the pond, and nobody knows whose it is."')
    ctx = {"menu": list(menu), "hobs": [label(p) for p in hobs], "rooms": [r["name"] for r in director.found(house)], "quiet": cfg["stage"]["quiet"]}
    return "\n\n".join(lines), ctx


def schema(menu):
    from .talk import obj, text
    return obj(name={"enum": list(menu)}, target=text(60, 0), why=text(200, 0))


def target_of(house, words):
    """A hob's id or a room's id from the narrator's words, or None."""
    w = str(words or "").strip()
    if not w:
        return None
    pid = hooks.hob_of(house, w)
    if pid and house["pets"][pid]["stage"] not in ("egg", "dead"):
        return pid
    rooms = sorted(hooks.rooms_of(house, w))
    return rooms[0] if rooms else None


def take(house, cfg, reply, menu, day):
    """The narrator's answer, kept to the rules: a name it was not offered is nothing. The choice waits for its dawn."""
    from . import actions
    r = reply if isinstance(reply, dict) else {}
    name = r.get("name") if r.get("name") in menu else "nothing"
    hap = K.happening({"name": name, "target": target_of(house, r.get("target")) if name != "nothing" else None,
                       "why": actions.clean(str(r.get("why") or ""), 200) if name != "nothing" else "", "day": day})
    house["coming"] = [x for x in house.get("coming", []) if x["day"] != day] + [hap]
    house["happenings"] = sorted([x for x in house.get("happenings", []) if day - x["day"] < 7 and x["day"] != day] + [hap], key=lambda x: x["day"])
    K.note(house, "happening", name=name, target=hap["target"])
    return hap


async def choose(eng):
    """The director's one call, at midnight (§8.1): tomorrow's happening(), kept in house["coming"]."""
    h, cfg = eng.house, eng.cfg
    day = h["clock"]["day"] + 1
    menu = offered(h, cfg, day)
    reply, brain = None, eng.narrator
    if brain and len(menu) > 1:
        text, ctx = packet(h, cfg, menu)
        if getattr(brain, "instant", False):
            async def fn():
                return await brain.director(text, ctx)
        else:
            from .brains.model import parse
            think, most, warm = K.thinking(cfg, "director")

            async def fn():
                return parse(await asyncio.to_thread(brain.chat, text, schema(menu), think, most, warm, "director"))
        try:
            reply = await eng.call(3, "house", "director", "midnight", fn, len(text))
        except Exception as e:
            logging.warning("the director's call failed: %r; tomorrow is quiet", e)
    return take(h, cfg, reply, menu, day)


# ---- the day: asked at midnight, foreshadowed at dusk, landed at dawn ----

def tick(eng):
    h, cfg = eng.house, eng.cfg
    if not on(cfg) or not h.get("lineage") or not living(h):
        return
    c, s = h["clock"], S(h)
    for nxt in list(h.get("coming") or []):
        if nxt["day"] < c["day"]:
            h["coming"].remove(nxt)   # (its day went by while the engine was not running)
        elif nxt["day"] == c["day"] and c["phase"] == "day":
            h["coming"].remove(nxt)
            land(h, cfg, nxt)
        elif nxt["day"] == c["day"] + 1 and c["phase"] == "dusk" and s["omen"] != nxt["day"]:
            s["omen"] = nxt["day"]
            if MENU[nxt["name"]]["omen"]:
                director.tell_all(h, MENU[nxt["name"]]["omen"], "phase")
                moment(h, "omen", MENU[nxt["name"]]["omen"])
    if s["asked"] != c["day"] and c["day"] >= 2 and ((h["chronicle"] or [{"day": 0}])[-1]["day"] >= c["day"] - 1 or c["hour"] >= 1):   # (after yesterday's chronicle)
        s["asked"] = c["day"]
        eng.spawn(choose(eng))


def land(house, cfg, hap):
    """A happening comes (§8.4). Returns what happened, in words, or None (nothing, or its makings had gone)."""
    hap = K.happening(hap)
    line = EFFECTS[hap["name"]](house, cfg, hap) if hap["name"] != "nothing" else None
    if not line:
        hap = K.happening({"name": "nothing", "day": hap["day"]})
    house["happening"] = hap
    house["happenings"] = sorted([x for x in house.get("happenings", []) if x["day"] != hap["day"]] + [hap], key=lambda x: x["day"])
    if not line:
        return None
    tp = house["pets"].get(hap["target"] or "")
    room = hap["target"] if hap["target"] in house["rooms"] else tp["room"] if tp else None
    moment(house, "happening", "%s%s" % (line[:1].upper() + line[1:], ": " + hap["why"] if hap["why"] else ""), tp["id"] if tp else None, room)
    from . import book
    for p in director.awake_pets(house):
        memories.add(house, cfg, p, line, 3, about=[tp["id"]] if tp and tp is not p else (), kind="happening")
        book.wonder(house, cfg, p, "happening", book.HAPPENED.get(hap["name"], hap["name"].replace("_", " ")))   # SPEC-v5.1 §6.3 (helper B)
    return line


# ---- what each happening does (EFFECTS: contracts.HAPPENINGS, every one; check_contracts) ----

def hob(house, hap, r, ok=lambda p: True):
    """The happening's hob: its target if it is one and alive, else one drawn."""
    p = house["pets"].get(hap["target"] or "")
    if p and p["stage"] not in ("egg", "dead") and ok(p):
        return p
    xs = [p for p in living(house) if ok(p)]
    return r.choice(xs) if xs else None


def indoors(house):
    return [x for x in director.found(house) if not x.get("outdoor")]


def room_for(house, hap, r):
    x = house["rooms"].get(hap["target"] or "")
    if x and x.get("type") and not x.get("outdoor"):
        return x
    p = house["pets"].get(hap["target"] or "")
    if p and p["stage"] not in ("egg", "dead") and not house["rooms"][p["room"]].get("outdoor"):
        return house["rooms"][p["room"]]
    lived = [x for x in indoors(house) if any(q["room"] == x["id"] for q in living(house))] or indoors(house)
    return r.choice(lived) if lived else None


def set_sky(house, kind):
    house["weather"] = kind
    S(house)["sky"] = [house["clock"]["day"], kind]
    director.tell_all(house, director.SKY[kind], "phase")


def storm(house, cfg, hap):
    r = rnd(house, "stage storm", house["tick"])
    set_sky(house, "storm")
    W = cfg["house"]["weather"]
    if r.random() < W["storm_power_cut"]:   # (some time in the dark hours, as the weather's own storm)
        house["storm_cut"] = house["tick"] + hours(cfg, r.uniform(*W["storm_cut_hours"]))
    room = room_for(house, hap, r)
    built = [(x, n) for x in indoors(house) for n, o in x["objects"].items() if (o.get("fix") or {}).get("built") and not o["fix"]["built"].get("worn") and "site" not in o]
    made = [(x, n) for x in indoors(house) for n, o in things.made(x).items() if not o["made"].get("damp")]
    broke = ""
    if built:
        from . import build
        x, n = r.choice(built)
        build.wear_out(house, cfg, x, n)
        broke = ", and the %s in %s took the worst of it" % (n, x["name"])
    elif made:
        x, n = r.choice(made)
        x["objects"][n]["made"]["damp"] = True
        broke = ", and the %s in %s is soaked through and wants mending" % (n, x["name"])
    if room:
        director.leak(house, cfg, room)
    return "a storm broke over the house%s%s" % (" and the rain came in through the roof of %s" % room["name"] if room and room["wet_until"] > house["tick"] else "", broke)


def buried(house, cfg, hap):
    garden = next((x for x in director.found(house) if x["type"] == "garden"), None)
    if not garden:
        return None
    r = rnd(house, "stage buried", house["tick"])
    dead = sorted((p for p in house["pets"].values() if p["stage"] == "dead"), key=lambda p: p.get("died") or 0)
    bit = r.choice(bit_kinds(house, cfg))
    things.drop_bits(house, cfg, garden, free_tile(house, cfg, garden, [r.randrange(cfg["W"]), r.randrange(cfg["H"])]), [bit])
    whose = "it was %s's, long ago" % label(dead[-1]) if dead and r.random() < 0.7 else "nobody knows whose it was"
    director.tell_all(house, "something has been dug up here: %s, and %s" % (a_bit(bit), whose), room=garden["id"])
    return "%s was found buried in the garden, and %s" % (a_bit(bit), whose)


def stranger_egg(house, cfg, hap):
    """A founder egg of a new family (SPEC-v4.0.5 §3): a stranger's, kin to nobody."""
    from . import genes, genome as G, names
    if len(alive(house)) >= cfg.get("population", {}).get("most", 7):
        return None
    r = rnd(house, "stage egg", house["tick"])
    rooms = [x for x in indoors(house) if x["type"] not in ("yard", "meadow")]
    room = next((x for x in rooms if x["type"] == "nursery"), rooms[0] if rooms else None)
    if not room:
        return None
    body = genes.apart(house, dict(G.START, hue=r.randrange(360), pattern=r.choice(G.PATTERNS), **{k: round(r.uniform(*v), 2) for k, v in G.RANGES.items()}), r)
    egg = new_pet(house, cfg, room["id"], free_tile(house, cfg, room, [cfg["W"] // 2, cfg["H"] // 2]), genome=body,
                  family=max(family(p) for p in house["pets"].values()) + 1)
    egg["founder"] = True
    names.foundling(house, cfg, egg)
    director.tell_all(house, "there is an egg here that nobody laid, and it is like no egg of the house", room=room["id"])
    return "an egg nobody laid turned up in %s, a stranger's" % room["name"]


def bad_food(house, cfg, hap):
    rooms = shelf_rooms(house, cfg)
    x = house["rooms"].get(hap["target"] or "")
    room = x if x in rooms else rnd(house, "stage food", house["tick"]).choice(rooms) if rooms else None
    if not room or not health.spoil(house, cfg, room, early=True):
        return None
    return "the food put by in %s turned bad overnight" % room["name"]


def missing(house, cfg, hap):
    """A thing goes missing (§8.2): a greedy hob took it and keeps quiet (a secret), or a creature did."""
    r = rnd(house, "stage missing", house["tick"])
    things_ = owned(house)
    p = house["pets"].get(hap["target"] or "")
    mine = [(x, n) for x, n in things_ if p and things.made(x)[n]["made"]["owner"] == p["id"]]
    if not things_:
        return None
    frm, n = r.choice(mine or things_)
    owner = house["pets"][things.made(frm)[n]["made"]["owner"]]
    greedy = [q for q in living(house) if q is not owner and q.get("flaw") and K.flaw(q["flaw"])["name"] == "greedy"]
    by = r.choice(greedy) if greedy else None
    to = house["rooms"][by["room"]] if by and by["room"] != frm["id"] and not house["rooms"][by["room"]].get("outdoor") else None
    director.lose(house, cfg, r, frm, n, to, by)
    if by:
        K.secret_later(by, "taken", "I took %s's %s and hid it, and I have said nothing" % (label(owner), n), owner["id"], house["tick"])
    return "%s's %s went missing in the night" % (label(owner), n)


def cold_snap(house, cfg, hap):
    health.cold_snap(house, cfg, 2)
    director.tell_all(house, "the cold has come early: the night will be bitter", "phase")
    return "a cold snap came before its season, and the nights are bitter"


def heat_wave(house, cfg, hap):
    set_sky(house, "heat")
    return "a heat wave came before its season: the air is hot and still"


def leak(house, cfg, hap):
    room = room_for(house, hap, rnd(house, "stage leak", house["tick"]))
    if not room:
        return None
    director.leak(house, cfg, room)
    return "water came into %s" % room["name"] if room["wet_until"] > house["tick"] else None


def power_cut(house, cfg, hap):
    from .world import power_on
    if not power_on(house):
        return None
    director.power_cut(house, cfg, rnd(house, "stage cut", house["tick"]).uniform(*cfg["house"]["events"]["power_cut_hours"]), "chosen")
    return "the power went out all through the house"


def letter(house, cfg, hap):
    from . import visitor
    return visitor.deliver(house, cfg, hap["target"])


def dream(house, cfg, hap):
    """A hob wakes with a belief it did not have (truth unknown: §5.2): of a tale of its family, or of what it fears."""
    r = rnd(house, "stage dream", house["tick"])
    p = hob(house, hap, r, lambda p: p["stage"] != "hatchling")
    if not p:
        return None
    tale = next((t for t in reversed(house.get("tales", [])) if t["family"] == family(p) and t["about"] != p["id"]), None)
    fear = (p.get("self") or {}).get("what I fear")
    seen = "%s, who %s, came to me and said: %s" % (tale["name"], tale["words"], tale["last_words"] or "be careful") if tale and r.random() < 0.6 else \
        "I must face %s" % fear if fear else "there is a room in the house that nobody has found"
    text = "in a dream I learned that %s" % seen
    K.believe_later(p, text, hooks.parse(house, seen, cfg), "a dream", truth=None)
    if p["sleep"]:
        p.setdefault("on_wake", []).append("you dreamt in the night: %s" % seen)
    else:
        add_event(house, p, "you remember a dream: %s" % seen)
    return "%s woke from a dream it cannot shake" % label(p)


def train(house, cfg, hap):
    r = rnd(house, "stage train", house["tick"])
    lying = {s["bit"] for x in house["rooms"].values() for s in x.get("spots", [])}
    strange = [b for b in bit_kinds(house, cfg) if b not in lying] or bit_kinds(house, cfg)
    room = director.storeroom(house) or (indoors(house) or [None])[0]
    if not room or not strange:
        return None
    bit = r.choice(strange)
    things.drop_bits(house, cfg, room, [cfg["W"] // 2, cfg["H"] // 2], [bit])
    director.tell_all(house, "the train came through in the night and left something strange behind: %s" % a_bit(bit), room=room["id"])
    return "the train came in the night and left %s in %s, a thing nobody had seen here" % (a_bit(bit), room["name"])


def creature(house, cfg, hap):
    r = rnd(house, "stage creature", house["tick"])
    p = hob(house, hap, r)
    if not p:
        return None
    room = house["rooms"][p["room"]]
    kind = "bird" if room["type"] == "garden" else "mouse" if room["type"] in ("cellar", "storeroom") else "beetle"
    cr = director.born(house, cfg, kind, room, free_tile(house, cfg, room, p["pos"]), cfg["house"]["creatures"][kind]["stay_hours"] * 2)
    director.trusts(cr, p, cfg["taming"]["tame_at"] / 2)
    director.seen(house, cfg, cr, "a %s has come in, and it keeps close to %s" % (kind, label(p)))
    return "a %s took to %s and keeps close by it" % (kind, label(p))


def visitor_gone(house, cfg, hap):
    from . import visitor
    for p in living(house):
        if visitor.involves(p):
            visitor.move(house, cfg, p, "he has gone, they say")
    director.tell_all(house, "they are saying the visitor has gone, and nobody has felt him for days")
    return "the house began to say the visitor has gone"


EFFECTS = {"nothing": lambda house, cfg, hap: None, "storm": storm, "buried": buried, "stranger_egg": stranger_egg, "bad_food": bad_food,
           "missing": missing, "cold_snap": cold_snap, "heat_wave": heat_wave, "leak": leak, "power_cut": power_cut, "letter": letter,
           "dream": dream, "train": train, "creature": creature, "visitor_gone": visitor_gone}
