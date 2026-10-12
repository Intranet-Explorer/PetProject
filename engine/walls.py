"""Writing (SPEC-v3.1 §2): words scratched on a wall, a stone or a thing, that stay in the place and fade there.
A message goes from a parent to its child; an inscription waits for whoever walks in. Every one ever written
is kept in the lineage's log, whether or not it is still on the wall."""
from . import things
from .world import days as world_days, dist, family, knows, label, moment, relation, witness

WALLS = ["north wall", "south wall", "west wall", "east wall"]


def marks(room):
    return room.setdefault("marks", [])


def tool(cfg, pet):
    """What it has to write with: chalk, or failing that any hard bit, which only scratches."""
    if "chalk" in pet["carrying"]:
        return "chalk"
    return "scratch" if any("hard" in cfg["house"]["bits"][b]["can"] for b in pet["carrying"]) else None


def surfaces(house, pet, room):
    """Where it could write here: a wall, a stone, or a thing of its own."""
    return WALLS + [n for n, o in room["objects"].items() if "memorial" in o] + things.mine(house, pet, room)


def clarity(cfg, room, m, tick):
    """1 when just written, 0 when it has gone. Chalk lasts longer than a scratch; the cellar's damp takes both sooner."""
    W = cfg["writing"]
    last = W["chalk_days" if m["medium"] == "chalk" else "scratch_days"] / (W["damp"] if room["type"] == "cellar" else 1.0)
    return max(0.0, 1.0 - world_days(cfg, m["fresh"], tick) / last)


def before(cfg, room, pet, m):
    """Is it standing in front of this one?"""
    x, y = pet["pos"]
    if m["on"] in WALLS:
        return {"north wall": y <= 1, "south wall": y >= cfg["H"] - 2, "west wall": x <= 1, "east wall": x >= cfg["W"] - 2}[m["on"]]
    o = room["objects"].get(m["on"])
    return bool(o) and dist(pet["pos"], o["pos"]) <= 1


def hand(house, pet, m):
    """Whose hand, as this pet would know it: its own, kin by what they are to it, someone it knows, the visitor's,
    or a hand it does not know (a stranger's, or someone dead before its time)."""
    if m["by"] == pet["id"]:
        return "your own hand"
    if m["by"] == "visitor":
        return "the visitor's hand"
    writer = house["pets"].get(m["by"])
    if writer:
        rel = relation(house, pet, writer)
        if rel:
            return "your %s's hand" % rel
        if writer["stage"] != "dead" and knows(pet, writer):
            return "%s's hand" % label(writer)
    return "a hand you don't know"


def handle(m):
    """How an inscription is named in an action: where it is and how it starts."""
    return "%s: %s" % (m["on"], m["text"][:28].lower())


def read(house, cfg, pet):
    """What it can read here: (the one it is standing in front of, the others newest and clearest first), as lines,
    and the handles a scrub can name."""
    room, tick = house["rooms"][pet["room"]], house["tick"]
    live = sorted(marks(room), key=lambda m: (-round(clarity(cfg, room, m, tick), 1), -m["tick"]))
    front = next((m for m in live if before(cfg, room, pet, m)), None)
    shown = ([front] if front else []) + [m for m in live if m is not front][:cfg["writing"]["shown"] - bool(front)]

    def line(m):
        faded = ", faded" if clarity(cfg, room, m, tick) < 1 - cfg["writing"]["faded"] else ""
        faint = ", scratched faintly" if m["medium"] == "scratch" else ""
        return 'on the %s, in %s%s%s: "%s"' % (m["on"], hand(house, pet, m), faint, faded, m["text"])

    return (line(front) if front else None), [line(m) for m in shown if m is not front], [handle(m) for m in shown]


def note(house, room, m, what, actor):
    """For the log: every inscription and what became of it."""
    house.setdefault("fresh_marks", []).append({"id": m["id"], "tick": house["tick"], "room": room["id"], "place": m["on"], "text": m["text"],
                                                "by": m["by"], "medium": m["medium"], "what": what, "actor": actor})


def put(house, cfg, room, by, text, on, medium, at, fam=1):
    """An inscription goes up. The same words over a faded one restore it; a full room loses its most faded."""
    from .story import alike, content
    tick, words = house["tick"], content(text, True)
    old = next((m for m in marks(room) if m["on"] == on and alike(words, content(m["text"], True)) >= 0.8), None)
    if old:
        old["fresh"], old["medium"] = tick, "chalk" if "chalk" in (medium, old["medium"]) else "scratch"
        note(house, room, old, "restored", by)
        return old, True
    house["n"]["mark"] = house["n"].get("mark", 0) + 1
    m = {"id": house["n"]["mark"], "text": text, "by": by, "family": fam, "on": on, "medium": medium, "tick": tick, "fresh": tick, "at": at}
    marks(room).append(m)
    note(house, room, m, "written", by)
    while len(marks(room)) > cfg["writing"]["cap"]:
        worn = min((x for x in marks(room) if x is not m), key=lambda x: clarity(cfg, room, x, tick))
        marks(room).remove(worn)
        note(house, room, worn, "worn away", by)
    return m, False


def along(cfg, pet, on):
    """How far along a wall the words go (0 to 1), from where the writer stands."""
    if on in ("north wall", "south wall"):
        return round(pet["pos"][0] / (cfg["W"] - 1), 2)
    return round(pet["pos"][1] / (cfg["H"] - 1), 2) if on in WALLS else 0.5


def check_write(a, house, cfg, pet, norm, filled):
    room = house["rooms"][pet["room"]]
    if not filled(a.get("text")):
        return "nothing to write"
    if not tool(cfg, pet):
        return "you have nothing to write with"
    return None if norm(a.get("on")) in surfaces(house, pet, room) else "there is nothing like that here to write on"


def write(house, cfg, pet, a, clean, norm):
    from .life import last_sentence
    room, on = house["rooms"][pet["room"]], norm(a["on"])
    text, medium = last_sentence(clean(a["text"], cfg["writing"]["max_chars"] + 20), cfg["writing"]["max_chars"]), tool(cfg, pet)
    m, restored = put(house, cfg, room, pet["id"], text, on, medium, along(cfg, pet, on), family(pet))
    used = ""
    if medium == "chalk":
        pet["chalked"] = pet.get("chalked", 0) + 1
        if pet["chalked"] >= cfg["writing"]["chalk_writings"]:
            pet["carrying"].remove("chalk")
            pet["chalked"], used = 0, "; the chalk is used up"
    where = "the " + on
    witness(house, pet, "%s wrote on %s" % (label(pet), where))
    moment(house, "wrote", "%s wrote on %s%s" % (label(pet), where if on not in WALLS else "the %s %s" % (room["name"].replace("the ", ""), on.split()[1]),
                                               " again" if restored else ""), pet["id"], room["id"])
    how = "you wrote it again over the old words on %s, and they are clear again" % where if restored else \
        "you %s on %s: \"%s\"" % ("wrote in chalk" if medium == "chalk" else "scratched faintly", where, m["text"])
    return how + used, dict(cfg["effects"]["write"]), "write"


def find(room, norm, name):
    n = norm(name)
    return next((m for m in marks(room) if norm(handle(m)) == n), None)


def scrub(house, cfg, pet, a, norm):
    """Anyone can scrub anything (§2.1). Whoever wrote it is told if they are there to see, and finds out if not."""
    room = house["rooms"][pet["room"]]
    m = find(room, norm, a["what"])
    marks(room).remove(m)
    note(house, room, m, "scrubbed", pet["id"])
    writer = house["pets"].get(m["by"])
    whose = "its own" if m["by"] == pet["id"] else "the visitor's" if m["by"] == "visitor" else "%s's" % label(writer) if writer else "someone's"
    witness(house, pet, "%s rubbed out the words on the %s" % (label(pet), m["on"]))
    if writer and writer is not pet and writer["stage"] not in ("dead", "egg"):
        if writer["room"] == room["id"] and not writer["sleep"]:
            writer["news"].append("spoken")
        else:
            writer.setdefault("lost", []).append({"name": "words", "by": pet["id"], "room": room["id"],
                                                  "text": "the words you wrote on the %s here have been rubbed out" % m["on"]})
    moment(house, "scrubbed", "%s scrubbed out %s words in %s" % (label(pet), whose, room["name"]), pet["id"], room["id"])
    return 'you rubbed out the words on the %s: "%s"' % (m["on"], m["text"]), {}, "scrub"


def fade(house, cfg):
    """Once an hour: what has faded right away is gone from the wall."""
    for room in house["rooms"].values():
        for m in [m for m in room.get("marks", []) if clarity(cfg, room, m, house["tick"]) <= 0]:
            room["marks"].remove(m)
            note(house, room, m, "faded away", None)


def visitor(house, cfg, room, text, on):
    """The visitor writes too (§2.3)."""
    m, _ = put(house, cfg, room, "visitor", text, on if on in WALLS else "north wall", "chalk", 0.5, 0)
    moment(house, "wrote", "the visitor wrote on the %s of %s" % (m["on"], room["name"]), None, room["id"])
    return m
