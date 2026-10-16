"""Hob names (SPEC-v3.5.8 §2). A hob naming an egg is offered five real names, each from a different source: the
screens, the name bank (names.toml), the family's sound, an old family name to honour someone, and something from its
own life. The mind still chooses; a name that is a phrase made of the family's words ("Rain Rest", "Open Hand") is
not taken: the egg gets the first name offered, and the phrase becomes its by-name. No model is asked for any of it."""
import re
import tomllib

from . import hub
from .world import LONG_AGO, arrived, label, moment, rnd, who

TITLES = {"sir", "lady", "dame", "lord", "captain", "master", "mistress", "miss", "mister", "madame", "monsieur", "auntie", "uncle",
          "saint", "doctor", "professor", "baron", "duke", "count", "countess", "prince", "princess", "king", "queen", "admiral",
          "major", "old", "little"}
ROMAN = ["", "", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
NUMERAL = re.compile(r"\s+(I{1,3}|IV|VI{0,3}|IX|X)$")
CONS = ["b", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "r", "s", "t", "v", "w", "z", "th", "sh"]
NEAR = {"b": "p", "p": "b", "d": "t", "t": "d", "g": "k", "k": "g", "v": "f", "f": "v", "z": "s", "s": "z", "m": "n", "n": "m",
        "l": "r", "r": "l", "w": "h", "h": "w", "j": "sh", "sh": "th", "th": "sh"}   # a sound drifts to one like it
WORDY = re.compile(r"(tion|sion|ment|ness|ity|ism|ture|ing|ogy|ics|ance|ence|ship|hood|(?<=....)ly)$")   # a word's ending, not a name's ("Agriculture")
RANK = re.compile(r"(ptera|idae|inae|aceae|ales|formes)$|^.{6,}ia$")   # a Latin rank of creatures or plants, or a long place ("Coleoptera", "Antarctica")
ENDINGS = ["o", "io", "on", "an", "a", "ia", "ie", "y", "ly", "el", "en", "in", "is", "us", "ix", "wick", "bert", "kin", "by", "wyn"]


def load(cfg, root):
    """names.toml into cfg["names"]: every bank name with what an offer says of it, the family's words, the screen's
    non-names, and the words of a hob's life that become names."""
    d = tomllib.loads((root / "names.toml").read_text())
    split = lambda g: re.split(r"\s*[,\n]\s*", g["names"].strip())
    bank = {}
    for g in d["bank"].values():
        for n in split(g):
            bank.setdefault(n, g["why"])
    cfg["names"] = {"bank": bank, "words": {w for n in bank for w in n.lower().split()}, "vocabulary": set(d["vocabulary"].split()),
                    "nature": set(split(d["bank"]["nature"])), "skip": set(d["screen"]["skip"].split()), "life": d["life"]}


# ---- the rules ----

def sayable(word):
    """Easy to say: a vowel in it, no more than three consonant sounds or three vowels running."""
    w = re.sub(r"(.)\1", r"\1", re.sub(r"[cpstgw]h|ck", "h", re.sub(r"[^a-z]", "", word.lower())))   # (th, sh, ck, a double letter: one sound)
    return len(w) >= 2 and bool(re.search(r"[aeiouy]", w)) and not re.search(r"[^aeiouy]{4}|[aeiou]{4}", w)


def family_words(house, cfg):
    """The vocabulary, and the words of any hob's two-word name in the house that is not a name from the bank ("Grey
    Light II", "Petal's Rest", "Purple Camo")."""
    out = set(cfg["names"]["vocabulary"])
    for p in house["pets"].values():
        ws = [re.sub(r"'s$", "", w) for w in NUMERAL.sub("", p.get("name") or "").lower().split()]
        if len(ws) > 1 and not all(w in cfg["names"]["words"] for w in ws):
            out |= set(ws)
    return out


def rules(house, cfg, name):
    """None if it is a name, else why not: never a phrase, nor made of the family's words, easy to say, at most 16."""
    name = (name or "").strip()
    if not name:
        return "no name"
    if len(name) > 16:
        return "too long for a name"
    if not re.fullmatch(r"[A-Za-z][A-Za-z' -]*", name):
        return "not a name"
    from .world import ends_in_number
    if ends_in_number(NUMERAL.sub("", name)):   # SPEC-v3.5.9.1: never "Open Six" (an honoured name's numeral, "Odo II", is no number word)
        return "a number, not a name"
    words = [re.sub(r"'s$", "", w) for w in re.split(r"[\s-]+", NUMERAL.sub("", name).lower()) if w]
    core = [w for w in words if w not in TITLES] or words
    fw = family_words(house, cfg)
    if all(w.strip("'") in fw or any(w[:i] in fw and w[i:] in fw for i in range(3, len(w) - 2)) for w in core):   # SPEC-v3.5.8 §2: never a phrase made from the family's vocabulary ("Rain Rest", "Rainrest")
        return "made of your family's words, not a name"
    if len(core) > 1 and not all(w in cfg["names"]["words"] for w in core):
        return "a phrase, not a name"
    if not all(sayable(w) for w in core):   # SPEC-v3.5.8 §2: easy to say
        return "hard to say"
    return None


def living(house, name):
    return any((p.get("name") or "").lower() == name.strip().lower() for p in house["pets"].values() if p["stage"] != "dead")


def check(house, cfg, name):
    """None if a hob can be called this, else why not (SPEC-v3.5.8 §2): the rules, and never a living hob's name
    (one honoured is numbered: "Odo II")."""
    return rules(house, cfg, name) or ("the name of a hob alive in the house" if living(house, name) else None)


# ---- the family's sound ----

def founded(rng):
    """A family's sounds, picked once at its founding: three consonants, two vowels, an ending."""
    return {"cons": rng.sample(CONS, 3), "vowels": rng.sample("aeiou", 2), "end": rng.choice(ENDINGS)}


def sound(house, fam, gen):
    """A family's sound in a generation: the founding one (kept in the house), drifted a little each generation since.
    Its first consonant and first vowel never drift, so the family keeps its flavour."""
    s = house.setdefault("sounds", {}).setdefault(str(fam), founded(rnd(house, "sound", fam)))
    s = {"cons": list(s["cons"]), "vowels": list(s["vowels"]), "end": s["end"]}
    for g in range(2, gen + 1):
        r = rnd(house, "drift", fam, g)
        if r.random() < 0.5:
            i = r.choice([1, 2])
            s["cons"][i] = NEAR[s["cons"][i]] if r.random() < 0.6 else r.choice([c for c in CONS if c not in s["cons"]])
        if r.random() < 0.25:
            s["vowels"][1] = r.choice([v for v in "aeiou" if v != s["vowels"][0]])
        if r.random() < 0.2:
            e = ENDINGS.index(s["end"]) + r.choice([-1, 1])
            s["end"] = ENDINGS[min(len(ENDINGS) - 1, max(0, e))]
    return s


def in_sound(s, r):
    """A name made in a sound: its first consonant, a vowel, perhaps another syllable, the ending."""
    parts = [s["cons"][0], r.choice(s["vowels"])]
    if r.random() < 0.6:
        parts += [r.choice(s["cons"]), r.choice(s["vowels"])]
    if s["end"][0] in "aeiouy":
        parts.append(r.choice(s["cons"][1:]))
    return ("".join(parts) + s["end"]).capitalize()


# ---- the five sources ----

def from_screens(house, pet, r):
    """Names the hob found on the screens (look_up)."""
    finds = list(pet.get("name_finds", []))
    r.shuffle(finds)
    return [(f["name"], f["why"]) for f in finds]


def from_bank(cfg, r):
    bank = cfg["names"]["bank"]
    return [(n, bank[n]) for n in r.sample(sorted(bank), 60)]


def from_sound(house, fam, gen, r):
    s = sound(house, fam, gen)
    return [(in_sound(s, r), "in your family's sound") for _ in range(12)]


def honoured(house, cfg, pet, fam, r):
    """An old family name, to honour someone: its own forebears first, then the rest of the family, the dead before
    the living; numbered by how many have had it ("Garry II"). Only real names: a phrase name honours nobody."""
    line, p = [], pet
    while p and p.get("parent") and p["parent"] in house["pets"]:
        p = house["pets"][p["parent"]]
        line.append(p)
    kin = sorted((q for q in house["pets"].values() if q.get("name") and hub.family_of(house, q) == fam and q not in line and q is not pet and q["stage"] == "dead"),   # (an old name: not a living sister's)
                 key=lambda q: (q["stage"] != "dead", q["laid"]))
    out = []
    for q in [q for q in line if q.get("name") and hub.family_of(house, q) == fam] + kin + ([pet] if pet.get("name") and hub.family_of(house, pet) == fam else []):
        base = NUMERAL.sub("", q["name"]).strip()
        if rules(house, cfg, base) is None:
            n = sum(NUMERAL.sub("", x.get("name") or "").strip().lower() == base.lower() for x in house["pets"].values())
            out.append(("%s %s" % (base, ROMAN[min(n + 1, 10)]) if n else base, "after %s" % who(house, pet, q) if q is not pet else "after yourself"))
    head = out[:3]
    r.shuffle(head)
    return head + out[3:]


def own_life(house, cfg, pet, r):
    """Something from its own life, as a name: the thing it made best, a song it loves, the things of the room it
    knows best, the creature it has watched most."""
    from .story import made_by
    L, out, room = cfg["names"]["life"], [], house["rooms"][pet["room"]]
    things = {w for n in list(cfg["house"]["bits"]) + list(cfg["kinds"]) + list(pet.get("met", {})) for w in n.split()} \
        | {n.split()[0] for r in house["rooms"].values() if r["type"] for n, o in r["objects"].items() if o.get("planted")}   # (words that come out as a name: things, not ways to be)
    add = lambda words, why, but=(): out.extend((L.get(w) or w.capitalize(), why) for w in re.findall(r"[a-z]+", words.lower())
                                                if w not in but and (w in L or w in things or w.capitalize() in cfg["names"]["bank"]))
    best = made_by(house, pet)[:1]
    if best:
        add(best[0]["recipe"].get("kind") or "", "after the %s you made" % (best[0]["recipe"].get("kind") or "thing"))
    loved = max(pet.get("songs", []), key=lambda e: e.get("sung", 0), default=None)
    song = house.get("songs", {}).get(loved["id"]) if loved else None
    if song:
        add(song["name"], 'after the song "%s"' % song["name"])
    rooms = {}
    for k, v in (pet.get("body") or {}).get("habits", {}).items():
        rooms[k.split("|")[1]] = rooms.get(k.split("|")[1], 0) + v
    room = next((x for x in house["rooms"].values() if x["type"] == max(rooms, key=rooms.get, default=None)), None) or room
    for n, o in sorted(room.get("objects", {}).items()):
        if "made" not in o and not o.get("memorial") and not n.startswith("keepsake"):
            add(n, "after the %s in %s" % (n, room.get("name", "the house")), cfg["house"]["rooms"])
    add(room.get("type") or "", "after %s" % room.get("name", "the house"))
    met = max(pet.get("met", {}), key=pet["met"].get, default=None)
    if met:
        add(met, "after the %s you have watched" % met)
    r.shuffle(out)
    return out


def offers(house, cfg, pet, for_family=None, tick=None):
    """Five names a hob could give an egg, each from a different source: [{"name", "source", "why"}] (SPEC-v3.5.8 §2).
    Its own egg is of its family, a generation on; `for_family`: an egg that is nobody's, the founder of that family.
    Where a source has nothing, the bank fills in. The same hob at the same tick is always offered the same names."""
    r = rnd(house, "names", pet["id"], house["tick"] if tick is None else tick, for_family)
    fam = for_family or hub.family_of(house, pet)
    gen = 1 if for_family is not None else pet["gen"] + 1
    out, seen = [], set()
    bank = iter(from_bank(cfg, r))
    for source, made in (("screens", from_screens(house, pet, r)), ("bank", []), ("sound", from_sound(house, fam, gen, r)),
                         ("honour", honoured(house, cfg, pet, fam, r)), ("life", own_life(house, cfg, pet, r))):
        pick = next(((n, why) for n, why in made if n.lower() not in seen and check(house, cfg, n) is None), None)
        if not pick:
            source, pick = "bank", next((n, why) for n, why in bank if n.lower() not in seen and check(house, cfg, n) is None)
        seen.add(pick[0].lower())
        out.append({"name": pick[0], "source": source, "why": pick[1]})
    return out


def line(house, cfg, pet, egg=None):
    """The packet's line: the five names, and that it may give one of its own."""
    offs = offers(house, cfg, pet, egg["family"] if egg else None)
    return "names you could give %s: %s; or one of your own: a real name, not a phrase" % (
        "the egg" if egg else "your egg", ", ".join("%s (%s)" % (o["name"], o["why"]) for o in offs))


def given(house, cfg, pet, said, for_family=None):
    """The name an egg gets from what a hob gave it: (name, by-name, what the hob is told). A real name is taken; a
    phrase is not: the egg gets the first name offered, and the phrase is its by-name (SPEC-v3.5.8 §2)."""
    said = (said or "").strip()
    why = check(house, cfg, said) if said else None
    if not said or not why:
        return said or None, None, ""
    name = offers(house, cfg, pet, for_family, pet["last_call"])[0]["name"]
    return name, said, '; "%s" is %s, so the egg is called %s, and "%s" is what it is called besides' % (said, why, name, said)


def nobodys(house, pet):
    """The egg in its room that is nobody's and has no name, or None."""
    return next((p for p in house["pets"].values() if p["room"] == pet["room"] and p["stage"] == "egg" and not p["parent"] and not p["name"]), None)


# ---- the screens (SPEC-v3.5.8 §2, 1) ----

def wanted(house, cfg, pet):
    """Is a name on its mind: grown, with an egg still in it (the house may be full today, not by then), or there is an
    egg that is nobody's without one?"""
    from . import life
    if pet["stage"] not in ("adult", "elder"):
        return None
    if pet["eggs"] < life.fertility(pet):
        return "your egg"
    return "the egg that is nobody's" if any(p["stage"] == "egg" and not p["parent"] and not p["name"] for p in house["pets"].values()) else None


def targets(house, cfg, pet, near):
    """The body's "look up a name": a screen nobody else is at, or the heavy book, once a world day."""
    from . import book
    room = house["rooms"][pet["room"]]
    if house["tick"] - pet.get("name_look", LONG_AGO) < cfg["ticks_per_day"] or not wanted(house, cfg, pet) or not book.available(cfg):
        return []
    name, at = hub.book_at(house, cfg, room, pet)
    if not name or (not arrived(house, "book") and not hub.heavy(room["objects"][name])):   # (a screen is dark until the book has come)
        return []
    return [{"what": name, "goal": near(at), "bonus": 1.5}]


def topics(house, cfg, pet):
    """Things from its life to look up: what it has read about lately, what grows where it stands, the creatures it
    has watched, the kind of thing it made best."""
    from .story import made_by
    out = [r["title"] for r in pet.get("read", [])[:3]]
    out += [n.split()[0] for n, o in sorted(house["rooms"][pet["room"]]["objects"].items()) if o.get("planted")]
    out += sorted(pet.get("met", {}))
    out += [(made_by(house, pet)[:1] or [{"recipe": {}}])[0]["recipe"].get("kind")]
    return [t for t in dict.fromkeys(out) if t]


def found_in(house, cfg, title, text):
    """The real names in a page: a word written with a capital inside a sentence, on its own (people, places, stars,
    rivers; not "Internet Explorer"), and the names of plants and creatures in the bank, however they are written."""
    out, latin = [], set()   # a Latin name for a kind of creature or plant ("genus Vitis", "(Plutella xylostella)"), or half of a name in two ("Internet Explorer")
    for m in re.finditer(r"\b(?:genus|genera|order|family|class|species|phylum|tribe) ([A-Z][a-z]+)|\(([A-Z][a-z]+) [a-z]+|(?<=[a-z,] )([A-Z][a-z]+) ([A-Z][a-z]+)", text):
        latin |= set(m.groups()) - {None}
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        ws = [re.sub(r"'s$", "", w) for w in re.findall(r"[A-Za-z][a-z]*(?:'s)?", sentence)]
        cap = lambda i: 0 <= i < len(ws) and ws[i][0].isupper()
        for i, w in enumerate(ws):
            proper = i > 0 and cap(i) and not (i > 1 and cap(i - 1)) and not cap(i + 1) and 4 <= len(w) <= 9 and not WORDY.search(w) and not RANK.search(w) and (w not in latin or w in cfg["names"]["bank"]) and " %s " % w.lower() not in text
            if (proper or w.capitalize() in cfg["names"]["nature"]) and w.lower() not in cfg["names"]["skip"]:
                out.append(w.capitalize())
    out += [title] if title in cfg["names"]["bank"] else []
    return sorted((n for n in dict.fromkeys(out) if check(house, cfg, n) is None), key=lambda n: n not in cfg["names"]["bank"])   # (a name people give first)


def look_up(house, cfg, pet, at):
    """It reads the encyclopedia about something from its own life and keeps a few real names it found there. What it
    is told; the house's story has it too."""
    from . import book
    pet["name_look"] = house["tick"]
    r, screen = rnd(house, "look up", pet["id"], house["tick"]), "on the " + at if house["rooms"][pet["room"]]["objects"].get(at, {}).get("fix", {}).get("terminal") else "in the heavy book"
    ts, whose = topics(house, cfg, pet), wanted(house, cfg, pet) or "your egg"
    r.shuffle(ts)
    for t in ts[:8]:   # (a few pages: most pages about everyday things have no name in them)
        got = book.lookup(dict(cfg, book=dict(cfg["book"], chars=1200)), t)   # (a longer read than a question gets: names are few in a page)
        names = found_in(house, cfg, *got)[:3] if got else []
        if names:
            pet["name_finds"] = ([{"name": n, "why": "from %s, in a page about %s" % ("the screen" if screen.startswith("on") else "the book", got[0]), "tick": house["tick"]} for n in names] + pet.get("name_finds", []))[:6]
            moment(house, "read", "%s looked up a name for %s egg %s and found %s" % (label(pet), "its" if whose == "your egg" else "the", screen, " and ".join(names)), pet["id"], pet["room"])
            return "looked up a name for %s %s, in a page about %s: %s" % (whose, screen, got[0], ", ".join(names))
    return "looked up a name for %s %s, and found none" % (whose, screen)
