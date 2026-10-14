"""The board (SPEC-v3.5.4 §11) and the visitor's star (§10).

The machine room's lit sign grows into a board of what the house is proudest of: the Works' goal and its meter, and
the feats that have a board line (feats.record: firsts, bests, ambitions reached, what the Works built, the visitor's
stars). Everyone gets a turn: every world hour (and whenever there is a new feat) the board turns, and the feats it
shows are the newest, with the young favoured and whoever has been up there lately put back, one line to a pet. While
there are too few feats, the sign's own proudest headlines (an invention, a discovery, a statue) fill it.

A pet in the machine room reads it (hub.read_sign): its own name there makes it pleased with itself; someone else's
is a nudge. The visitor may give a thing a star, one to a thing: its maker feels it when it is next awake, and it goes
in the story and on the board. Tunables in config.toml [drive]."""
from . import feats, things, works
from .world import add_event, days, label

YOUNG = ("hatchling", "child", "youngling")


def who(f):
    """The pets a feat names."""
    return f.get("pets") or ([f["pet"]] if f.get("pet") else [])


def turn(house, cfg):
    """Choose what the board shows, if it is time: a new world hour, or a feat since it last turned."""
    D, F = cfg["drive"], house.get("feats") or {"n": 0, "list": []}
    B = house.setdefault("board", {"hour": None, "n": 0, "up": [], "log": []})
    hour = int(house["tick"] // (cfg["ticks_per_hour"] * D["board_hours"]))
    if B["hour"] == hour and B["n"] == F["n"]:
        return B
    B["hour"], B["n"] = hour, F["n"]
    B["log"] = [x for x in B["log"] if days(cfg, x[0], house["tick"]) <= D["board_days"]]
    named = {}
    for _, p in B["log"]:
        named[p] = named.get(p, 0) + 1
    young = lambda p: house["pets"].get(p, {}).get("stage") in YOUNG
    rank = lambda f: days(cfg, f["tick"], house["tick"]) * 24 + D["board_named"] * sum(named.get(p, 0) for p in who(f)) \
        - D["board_young"] * any(young(p) for p in who(f))
    fresh = [f for f in F["list"] if f.get("board") and days(cfg, f["tick"], house["tick"]) <= D["board_days"]]
    up, taken = [], set()
    for f in sorted(fresh, key=lambda f: (rank(f), -f["n"])):
        if len(up) >= D["board_rows"] or taken & set(who(f)):
            continue   # (one line to a pet at a time)
        up.append(f["n"])
        taken |= set(who(f))
    B["log"] += [[house["tick"], p] for f in F["list"] if f["n"] in up for p in who(f)]   # (each turn up there counts)
    B["up"] = up
    return B


def lines(house, cfg):
    """What the board shows now, in the order it runs it: the Works first, then the feats up, newest first, then (if
    there are too few) the sign's proudest headlines. Each {key, text, kind, pets, meter}: `text` is in its capitals,
    "WHAT: WHO"; `meter` is [have, need] for the Works (the page may show numbers; the pets are told words)."""
    out, B = [], turn(house, cfg)
    w = works.view(house, cfg)
    if w:
        out.append({"key": "works:%s" % w["what"], "text": w["line"], "kind": "works", "pets": [], "meter": [w["have"], w["need"]], "says": w["says"], "what": w["what"]})
    up = sorted((f for f in (house.get("feats") or {}).get("list", []) if f["n"] in B["up"]), key=lambda f: -f["n"])
    out += [{"key": "feat:%d" % f["n"], "text": f["board"], "kind": f["kind"], "pets": who(f), "meter": None, "for": f.get("for")} for f in up]
    if len(up) < cfg["drive"]["board_rows"]:
        heads = [h for h in house.get("ticker", {}).get("lines", []) if h.get("anim") == "star"][::-1]
        out += [{"key": "head:%d" % h["n"], "text": h["text"].upper(), "kind": h["kind"], "pets": [], "meter": None} for h in heads[:cfg["drive"]["board_rows"] - len(up)]]
    return out


def for_words(l):
    """What a line is on the board for, in plain words: "the first bowl in the house"."""
    if l.get("for"):
        return l["for"]
    what = l["text"].split(":")[0].lower()
    return what if what.startswith(("the ", "a ", "an ")) else "the " + what


def read(house, cfg, pet):
    """hub.read_sign calls this for a pet awake in the machine room: what is new on the board since it last read it,
    the newest two lines of it; its own name there is a glow of pride; someone else's, a nudge (once a reading)."""
    seen = pet.setdefault("sign", {"day": None, "n": 0})
    had = seen.setdefault("board", [])
    new = [l for l in lines(house, cfg) if (l["key"] + "|" + (l.get("says") or "")) not in had]
    if not new:
        return
    nudged = False
    for l in new[:2]:
        if l["kind"] == "works":
            add_event(house, pet, "the board on the wall says the Works is gathering scrap to build %s, and %s" % (l["what"], l["says"]))
            continue
        add_event(house, pet, 'the board on the wall says: "%s"' % l["text"])
        others = [house["pets"][p] for p in l["pets"] if p in house["pets"] and p != pet["id"]]
        if pet["id"] not in l["pets"] and others and not nudged:
            nudged = True
            add_event(house, pet, "%s %s on the board for %s; %s" % (works_names(others), "is" if len(others) == 1 else "are", for_words(l).replace("your ", "their "),
                                                                    "you could feed the Works too" if l["kind"] == "works" else "you could do something no one has done"))
    for l in new:
        if pet["id"] in l["pets"]:
            feats.glow(house, cfg, pet, 1, "your name is on the board for %s" % for_words(l))
    seen["board"] = (had + [l["key"] + "|" + (l.get("says") or "") for l in new])[-60:]


def works_names(pets):
    from .machine import listed
    return listed([label(p) for p in pets])


# ---- the visitor's star (§10) ----

def find(house, key):
    """(room, name, thing) of the made thing whose key is `key` (its id, as the Things tab has it), or Nones."""
    for r in house["rooms"].values():
        for n, o in things.made(r).items() if r["type"] else ():
            if str(o["made"].get("id")) == str(key):
                return r, n, o
    return None, None, None


def star(house, cfg, key):
    """The visitor gives a thing a star (server.py, POST /api/star/<id>). One to a thing. Its maker feels it the next
    time it is awake (`tick`); it is in the story and on the board. Returns an error string, or None."""
    room, name, o = find(house, key)
    if not o:
        return "there is no such thing about the house"
    m = o["made"]
    if m.get("star") is not None:
        return "it has a star already"
    m["star"] = house["tick"]
    house["visitor_last"] = house["tick"]
    maker = house["pets"].get(m["by"])
    whose = "%s's" % label(maker) if maker else "the visitor's own" if m["by"] == "visitor" else "a"
    feats.record(house, cfg, "star", maker["id"] if maker else None, "the visitor gave %s %s a star" % (whose, name),
                 board="A STAR FROM THE VISITOR: %s %s" % (whose.upper(), name.upper()), room=room["id"], thing=name, **{"for": "the visitor's star on your %s" % name})
    if maker and maker["stage"] not in ("egg", "dead"):
        maker.setdefault("starred", []).append(name)
    return None


def tick(house, cfg):
    """Every tick (hub.tick): a maker awake feels the stars given to its things while it slept, or just now."""
    for p in house["pets"].values():
        if p.get("starred") and not p["sleep"] and p["stage"] not in ("egg", "dead"):
            for name in p.pop("starred"):
                feats.glow(house, cfg, p, 2, "the visitor gave your %s a star" % name)
