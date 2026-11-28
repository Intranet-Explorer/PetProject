"""SPEC-v4.0 §3 what a hob carries: memories (lines with a weight; the heaviest never fade, the rest fade over days,
about 50 kept, at most 20 of them heavy) and skills 0-10 over the practice records craft.py keeps. Memories are part of [opinions].

SPEC-v4.2 §4 ([memory2]): a memory is a line with tags (contracts.memory: who it is about, where, what things and
materials, its kind); the model writes the ones that matter (react's, talk's and reflect's `remember`); memories are
found by the situation (recency x importance x relevance), not by weight alone; [memory2] keep and heavy_keep."""
import re

from .world import alive, days, label
from . import contracts as K
from . import opinions

KEEP, HEAVY = 50, 4
# The ten skills of §3, over the practice records the house already keeps (craft.practise): (records, how much each counts).
SKILLS = {"crafting": {"making": 1.0, "mending": 1.0, "tidying": 0.1}, "building": {"building": 1.0, "mending": 0.5},
          "cooking": {"cooking": 1.0}, "fishing": {"fishing": 1.0}, "foraging": {"tending": 1.0, "foraging": 1.0},
          "healing": {"healing": 1.0}, "inventing": {"designing": 2.0, "inventing": 1.0}, "music": {"music": 1.0},
          "reading": {"reading": 1.0}, "fighting": {"fighting": 1.0}, "talking": {"talking": 1.0}}


def on(cfg):
    return opinions.on(cfg)


def on2(cfg):
    return K.on(cfg, "memory2")


def fade(house, cfg, m):
    """What is left of a memory's weight: a light one loses a point every `fade_days`, a heavy one (4) every
    `heavy_fade_days`, and the heaviest (5) keeps it (19 October 2026: 4 never faded, and the house's verdicts filled
    every hob's memory)."""
    if m["weight"] >= 5:
        return m["weight"]
    M = opinions.DATA["memories"]
    if m["weight"] >= HEAVY and on2(cfg):   # (SPEC-v4.2 §4.1: a weight-4 memory is gone over [memory2] heavy_fade_days)
        return m["weight"] * (1 - days(cfg, m.get("from", m["tick"]), house["tick"]) / cfg["memory2"]["heavy_fade_days"])
    return m["weight"] - days(cfg, m.get("from", m["tick"]), house["tick"]) / M["heavy_fade_days" if m["weight"] >= HEAVY else "fade_days"]   # (from: a migrated one fades from then)


def add(house, cfg, pet, text, weight, about=(), kind=""):
    """A line it will remember. The same line on the same day is kept once (the heavier). (With [memory2]: `remember`.)"""
    if on2(cfg):
        return remember(house, cfg, pet, text, weight, kind, about, by="engine")   # (the model's lines come through remember, by="model")
    if not on(cfg) or pet["stage"] in ("egg", "dead") or not text:
        return None
    mems = pet.setdefault("memories", [])
    same = next((m for m in mems if m["text"] == text and days(cfg, m["tick"], house["tick"]) < 1), None)
    if same:
        same["weight"] = max(same["weight"], weight)
        return same
    m = {"tick": house["tick"], "text": text, "weight": max(1, min(5, int(weight))), "about": list(about), "kind": kind}
    mems.append(m)
    trim(house, cfg, pet)
    return m


def trim(house, cfg, pet):
    """Memories that have faded go; past `heavy_keep` heavy ones (4 and 5), and then past `KEEP` in all, the lightest and
    then the oldest go first."""
    keep_, most = (cfg["memory2"]["keep"], cfg["memory2"]["heavy_keep"]) if on2(cfg) else (KEEP, opinions.DATA["memories"]["heavy_keep"])
    mems = [m for m in pet.get("memories", []) if fade(house, cfg, m) > 0]
    heavy = [m for m in mems if m["weight"] >= HEAVY]
    if len(heavy) > most:
        gone = {id(m) for m in sorted(heavy, key=lambda m: (fade(house, cfg, m), m["tick"]))[:-most]}
        mems = [m for m in mems if id(m) not in gone]
    if len(mems) > keep_:
        keep = sorted(mems, key=lambda m: (fade(house, cfg, m), m["tick"]))[-keep_:]
        mems = [m for m in mems if m in keep]
    pet["memories"] = mems


def relevant(house, cfg, pet, about=(), where=None, what=(), kind=None, n=5, only=False):
    """The `n` memories that bear most on a thought about `about` (hob ids, "visitor"), oldest first; `only`: none but
    those about it (19 October 2026: "never dealt with the visitor" was false for any hob with a memory at all).
    With [memory2] (SPEC-v4.2 §4.2): recency (a half-life) x importance (weight / 5) x relevance (1, and 1 more for each
    tag it shares with the moment: the hobs, the room, the things and materials in play, the event's kind)."""
    if isinstance(where, int):   # (v4.0's callers give n fifth)
        n, where = where, None
    about = set(about)
    if on2(cfg):
        score = lambda m: score2(house, cfg, m, about, where, what, kind)
    else:
        score = lambda m: fade(house, cfg, m) + 3 * bool(about & set(m["about"])) - days(cfg, m["tick"], house["tick"]) / 20
    mems = [m for m in pet.get("memories", []) if not only or about & set(m["about"])]
    return sorted(sorted(mems, key=score)[-n:], key=lambda m: m["tick"]) if n else []


def score2(house, cfg, m, about=(), where=None, what=(), kind=None):
    """§4.2 how much a memory bears on the moment."""
    hits = len(set(about) & set(m["about"])) + bool(where and m.get("where") == where) + len(set(what) & set(m.get("what") or [])) + bool(kind and m.get("kind") == kind)
    recency = 0.5 ** (days(cfg, m["tick"], house["tick"]) / cfg["memory2"]["half_life_days"])
    return recency * max(0.0, fade(house, cfg, m)) / 5 * (1 + hits)


# ---- SPEC-v4.2 §4.1: a memory with tags ----

VOCAB = {}


def vocabulary(house, cfg):
    """The words a line may name that are things: kinds, bits and catches, materials, what stands in the rooms."""
    key = (id(cfg), len(house["rooms"]))
    if VOCAB.get("key") != key:
        words = set(cfg.get("kinds", {})) | set(cfg["house"]["bits"]) | {m for b in cfg["house"]["bits"].values() for m in b.get("can", [])}
        words |= {n for r in house["rooms"].values() for n, o in r.get("objects", {}).items() if "made" not in o}
        VOCAB.update(key=key, words={w.lower() for w in words if w})
    return VOCAB["words"]


def tag(house, text, cfg=None):
    """The names in a line (§4.1): (about: hob ids and "visitor"; where: the first room it names, or None; what: the
    kinds, bits, catches, materials and things it names, with a cfg). Whole words, one to three of them."""
    low = (text or "").lower()
    words = re.findall(r"[a-z][a-z'-]*", low)
    grams = {" ".join(words[i:i + k]) for k in (1, 2, 3) for i in range(len(words) - k + 1)}
    grams |= {g[:-1] for g in grams if g.endswith("s")}   # (bowls: a bowl)
    about = [p["id"] for p in house["pets"].values() if (p.get("name") or "").lower() in grams or label(p).lower() in low] + ["visitor"] * ("visitor" in grams)
    named = lambda r: re.sub(r"^the ", "", (r.get("name") or "").lower())
    rooms = sorted((low.find(named(r)) if named(r) in low else low.find(r["type"]), rid) for rid, r in house["rooms"].items()
                   if r.get("type") and (named(r) and named(r) in low or r["type"] in grams))
    what = sorted(grams & vocabulary(house, cfg)) if cfg else []
    return list(dict.fromkeys(about)), rooms[0][1] if rooms else None, what


def remember(house, cfg, pet, text, weight, kind, about=(), where=None, what=(), by=None):
    """A line it will keep, tagged by the engine from the names in it and what the caller adds: a contracts.memory().
    The same text is kept once (the heavier, at the newer tick). Returns the memory, or None."""
    if not on(cfg) or not pet or pet["stage"] in ("egg", "dead") or not K._s(text):
        return None
    a, w, x = tag(house, text, cfg)
    m = K.memory({"text": text, "tick": house["tick"], "weight": weight, "kind": kind, "about": [i for i in dict.fromkeys(list(about) + a) if i != pet["id"]],
                  "where": where or w, "what": list(dict.fromkeys(list(what) + x)), **({"by": by} if by else {})})
    mems = pet.setdefault("memories", [])
    same = next((o for o in mems if o["text"] == m["text"]), None)
    if same:
        same.update(weight=max(same["weight"], m["weight"]), tick=house["tick"])
        same.pop("from", None)
        return same
    mems.append(m)
    trim(house, cfg, pet)
    return m


def shared(house, cfg, a, b, n=1):
    """§7.3: memories both hold (the same line in each), or a line of one about the other; the most relevant first."""
    mine, theirs = a.get("memories", []), b.get("memories", [])
    texts = {m["text"] for m in theirs}
    pool = [m for m in mine if m["text"] in texts or b["id"] in m["about"]] + [m for m in theirs if a["id"] in m["about"] and m["text"] not in {x["text"] for x in mine}]
    score = (lambda m: score2(house, cfg, m, (a["id"], b["id"]))) if on2(cfg) else (lambda m: fade(house, cfg, m))
    return sorted(pool, key=score, reverse=True)[:n]


def from_talk(house, cfg, rec, ids):
    """§4.3 what a talk leaves (talk.py calls it, C's): each speaker's `knows` a memory of weight 3 about the other, its
    `wants` and `holds` of weight 2 (kind "subtext"), its `remember` of weight 3. `ids`: {the name the reply used: pet
    id}. Returns how many `knows` lines it kept."""
    if not on2(cfg):
        return 0
    pets, n = {name: house["pets"].get(pid) for name, pid in dict(ids).items()}, 0
    for name, side in K.talk_minds(rec).items():
        me, other = pets.get(name), next((p for nm, p in pets.items() if nm != name and p), None)
        if not me or not other:
            continue
        about = [other["id"]]
        n += bool(side["knows"] and remember(house, cfg, me, side["knows"], 3, "knows", about, by="model"))
        if side["knows"]:   # SPEC-v5.1 §6.3 (helper B): a thing named in it that it has no word for is a question
            from . import book
            book.heard(house, cfg, me, side["knows"])
        if side["wants"]:
            remember(house, cfg, me, "what I wanted from talking with %s: %s" % (label(other), side["wants"]), 2, "subtext", about, by="model")
        if side["holds"]:
            remember(house, cfg, me, "what I did not say to %s: %s" % (label(other), side["holds"]), 2, "subtext", about, by="model")
        if side["remember"]:
            remember(house, cfg, me, side["remember"], 3, "talk", about, by="model")
    if n:
        ab = [p["id"] for p in pets.values() if p]
        K.note(house, "knows", a=ab[0], b=ab[-1], n=n)
    return n


def mine(text, pet):
    """A line about a hob, told as its own: "Fiji caught a fish" -> "I caught a fish"."""
    name = label(pet)
    if text.startswith(name + " "):
        text = re.sub(r"^I (means|has|is|does|wants|knows|goes)\b", lambda m: "I " + VERB[m.group(1)], "I" + text[len(name):])
        text = text.replace("its own", "my own").replace(" its ", " my ")
    return text.replace(name, "me")


VERB = {"means": "mean", "has": "have", "is": "am", "does": "do", "wants": "want", "knows": "know", "goes": "go"}


# ---- the house's moments, read once by each part that listens (character: moods, needs: pride, memories) ----

def new_moments(house, part):
    """The house's moments since `part` last looked (none the first time it looks: what came before is history)."""
    seen = house.setdefault("v4_seen", {})
    ms = house.get("moments", [])
    last = seen.get(part)
    seen[part] = ms[-1]["n"] if ms else 0
    if last is None or last == seen[part]:
        return []
    return [m for m in ms if m["n"] > last]


# moment kind -> (weight for the hob it is about, (who else remembers it, weight))
def _parents(house, pet):
    from .character import parents_of
    return parents_of(house, pet)


def _close(house, pet):
    from .character import kin_and_friends
    return kin_and_friends(house, pet)


MOMENT_WEIGHT = {"first": (2, None), "best": (3, None), "invented": (3, None), "built": (3, None), "egg": (4, None),
                 "stage": (2, None), "named": (3, None), "weak": (3, None), "lost": (2, None), "discovery": (2, None),
                 "catch": (1, None), "words": (2, None), "hatched": (3, (_parents, 4)), "death": (None, (_close, 5))}


def tick(house, cfg):
    """(From opinions.tick.) The house's moments become memories."""
    for m in new_moments(house, "memories"):
        pet = house["pets"].get(m["pet"] or "")
        if not pet or m["kind"] not in MOMENT_WEIGHT:
            continue
        own, also = MOMENT_WEIGHT[m["kind"]]
        if own:
            add(house, cfg, pet, "I hatched" if m["kind"] == "hatched" else mine(m["text"], pet), own, (), m["kind"])
        if also:
            for other in also[0](house, pet):
                add(house, cfg, other, m["text"], also[1], [pet["id"]], m["kind"])
    if house["tick"] % max(1, round(cfg["ticks_per_hour"])) == 0:
        for pet in alive(house):
            trim(house, cfg, pet)


# ---- skills, 0 to 10 ----

def level(raw):
    """Practice to 0-10: a few times is a start, a hundred is mastery's edge."""
    return round(10 * raw / (raw + 30), 1)


def skill(pet, name):
    """0-10, from its practice records (the existing ones carry over)."""
    rec = pet.get("skill", {})
    return level(sum(rec.get(k, 0) * w for k, w in SKILLS[name].items()))


def skills(pet):
    return {s: skill(pet, s) for s in SKILLS}


def practise(house, cfg, pet, name, by=1.0):
    """It did it once more (or was taught: `by` is how much a lesson counts). Records craft.py knows go through it, so
    it is told in words as before; the new ones are kept beside them."""
    from . import craft
    rec = next(iter(SKILLS[name]))
    if rec in craft.SKILLS:
        craft.practise(house, cfg, pet, rec, by)
    else:
        s = pet.setdefault("skill", {})
        s[rec] = round(s.get(rec, 0) + by, 2)
