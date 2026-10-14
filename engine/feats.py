"""Drive (SPEC-v3.5.4 §6 to §12): what a pet can be proud of, and what the house is proud of.

This module holds what the parts share: pride, a glow felt in words that fades over a few world hours and is never
a need (§12); and the house's record of its feats (firsts, bests, ambitions reached, the Works, the visitor's stars),
which the board shows (§11), the story tells and the packet draws on. Tunables are in config.toml [drive]."""
from .world import add_event, moment

GLOW = ["pleased with yourself", "proud", "very proud"]   # size 1, 2, 3


def glow(house, cfg, pet, size, why):
    """Pride (§12): `size` 1 (pleased), 2 (proud) or 3 (very proud), `why` in plain words ("you made the first bowl in
    the house"). A bigger glow replaces a smaller one; a smaller one while a bigger is still bright only adds its why.
    It also lifts curiosity a little (§6: a first is felt as pride and as a lift in curiosity)."""
    D, now = cfg["drive"], house["tick"]
    size = max(1, min(3, size))
    g = pet.get("glow")
    if g and shine(cfg, house, g) >= size:
        g["also"] = why
    else:
        pet["glow"] = {"size": size, "why": why, "since": now, "until": now + round(D["glow_hours"] * cfg["ticks_per_hour"])}
    pet["needs"]["curiosity"] = min(100.0, pet["needs"]["curiosity"] + D["glow_curiosity"] * size)
    if not pet["sleep"]:
        add_event(house, pet, why)


def shine(cfg, house, g):
    """How bright a glow still is, 0 to 3: it fades from its size to nothing over its hours."""
    if not g or house["tick"] >= g["until"]:
        return 0
    left = (g["until"] - house["tick"]) / max(1, g["until"] - g["since"])
    return min(g["size"], max(1, round(g["size"] * left + 0.49)))


def felt(cfg, house, pet):
    """The glow as a feeling for the packet (feel.feelings adds it), or ""."""
    g = pet.get("glow")
    s = shine(cfg, house, g)
    if not s:
        return ""
    word = GLOW[s - 1] if s == g["size"] else "still a little " + GLOW[0 if s == 1 else 1].replace("pleased with yourself", "pleased")
    return "%s (%s)" % (word, g["why"].removeprefix("you "))


def record(house, cfg, kind, pet, text, board=None, room=None, **extra):
    """A feat: a moment for the story (`kind`: first, best, ambition, works, star, noticed), and when `board` is given
    a line for the board (§11), in its capitals ("FIRST BOWL IN THE HOUSE: OPEN STONE"). `pet` is the pet's id or None.
    Returns the feat."""
    F = house.setdefault("feats", {"n": 0, "list": []})
    F["n"] += 1
    f = {"n": F["n"], "tick": house["tick"], "day": house["clock"]["day"], "kind": kind, "pet": pet, "text": text, "board": board, **extra}
    F["list"] = (F["list"] + [f])[-cfg["drive"]["keep_feats"]:]
    moment(house, kind, text, pet, room)
    return f
