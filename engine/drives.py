"""SPEC-v4.2 §6 character (helper C): a drive, a flaw, a secret and a voice. Switch: [drives] on.

A drive (contracts.DRIVES) is drawn at hatching from its traits and its parents' drives (character.toml [drives]); a
flaw against it (each drive's `flaws`, weighted by [flaws]). The drive is told to every packet with what the hob has
done for it so far (`line`), and scores the planner for what serves it (`SERVES`, [drives] serve); the flaw scores it
too (`FLAW_SCORE`, [drives] flaw), and a hot one climbs the ladder faster (conflict.climb). "To be loved by one" is
given its one at the youngling stage: the hob it likes most. A drive changes once in a life, in the reflection, on a
day that shook it (a death of one close, a betrayal), when the hob writes a new "what I am for" (`reconsider`).

A secret (contracts.secret), zero or one at a time, is kept from life when nobody saw: a lie told, a thing broken or
hidden, a thing taken, a fall caused (A's, through contracts.secret_later), a feeling it has never said. It is in its
talk's `holds` and its reflection; it comes out in talk (talk.apply) or by the visitor's question (`found`).

The voice card (SPEC-v4.2.2 §2) is pet["voice"]: a style drawn from the traits and what it cares about, from the drive
(`card`); never a model call. None of the numbers reach a hob."""
from . import character
from . import contracts as K
from .world import alive, hours, label, moment, rnd

HOT = 2.0   # §6.2 how much likelier a hot hob is to take the next rung of the ladder
FOUND = (0.5, 0.15)   # §6.3 a secret comes out in a talk at this share of [talk] lie_found: with the one it is about, with anyone else

# §6.1 each drive -> what serves it: the activities' `do`, activity names, and the aim kinds a plan may take for it
SERVES = {
    "to be remembered": {"do": ("bench", "build", "design", "machine", "lay out", "sing", "b:strut"), "names": (), "aims": ("make", "build", "design")},
    "to be loved by one": {"do": ("follow", "sit with", "bring", "b:follow", "b:share", "b:pat"), "names": (), "aims": ("be with", "give", "help")},
    "to find out what the visitor is": {"do": ("window", "listen", "inspect", "doorway"), "names": ("go to ask",), "aims": ("learn", "explore", "ask")},
    "to make the thing nobody has made": {"do": ("try", "design", "bench", "b:new", "place"), "names": (), "aims": ("make", "design", "try")},
    "to keep the family safe": {"do": ("nurse", "bring", "follow", "sit with", "b:pat", "b:share"), "names": (), "aims": ("help", "nurse", "be with")},
    "to leave the house": {"do": ("go", "doorway", "peek", "ride", "train", "wander"), "names": (), "aims": ("explore",)},
    "to know everything in the book": {"do": ("inspect", "listen"), "names": ("go to the book", "leaf through the book", "look up a name"), "aims": ("learn",)},
    "to be left alone": {"do": ("nap", "window", "seat", "b:alone", "b:hide", "b:wall"), "names": (), "aims": ("rest",)},
}
# §6.2 each flaw -> what it pulls toward (+1) or away from (-1): an activity's `do` or its name
FLAW_SCORE = {
    "proud": {"listen": -1, "go to ask": -1, "b:strut": 1, "b:lecture": 1},
    "envious": {"b:sneer": 1, "b:share": -1},
    "fearful": {"go": -1, "doorway": -1, "peek": -1, "try": -1, "b:new": -1, "ride": -1, "b:wall": 1, "b:hide": 1},
    "greedy": {"b:stash": 1, "b:pocket": 1, "b:serving": 1, "b:share": -1, "bring": -1},
    "lazy": {"nap": 1, "seat": 1, "b:sunbeam": 1, "bench": -1, "build": -1, "design": -1},
    "hot": {"b:sneer": 1, "b:push": 1, "b:pat": -1},
    "dishonest": {"b:pocket": 1, "b:return": -1},
    "clinging": {"follow": 1, "b:follow": 1, "sit with": 1, "b:alone": -1},
}
# the flaw in words, for every packet and the card (§6.2)
FLAW_WORDS = {"proud": "won't ask for help, won't be taught", "envious": "can't stand it when someone else does a thing first", "fearful": "scared of anything new",
              "greedy": "keeps what it's given, and takes", "lazy": "always puts it off till tomorrow", "hot": "gets angry fast, and acts on it faster",
              "dishonest": "lies to save face", "clinging": "can't stand being away from the one it loves"}   # (v4.2.2 §5: in plain words)
# words in a "what I am for" line that name a drive (`reconsider`), the first named wins
DRIVE_WORDS = {"to be remembered": ("remembered", "my name"), "to be loved by one": ("loved", "love "), "to find out what the visitor is": ("visitor",),
               "to make the thing nobody has made": ("nobody has made", "never been made", "new thing", "invent"),
               "to keep the family safe": ("safe", "protect", "keep the family", "look after"),
               "to leave the house": ("leave the house", "beyond the gate", "meadow", "the train", "outside"),
               "to know everything in the book": ("the book", "know everything", "learn everything"), "to be left alone": ("alone", "left be", "by myself")}
BETRAYED = ("lied_to_me", "broke_promise", "killed_my_kin", "hurt_me", "beat_me", "took_my_thing", "broke_my_thing")


def on(cfg):
    return K.on(cfg, "drives")


# ---- at hatching ----

def draw(house, cfg, pet):
    """(life.hatch) Its drive, from its traits and its parents' drives; a flaw against it; and its voice card. A hob that
    has a drive keeps it."""
    if not on(cfg) or pet.get("drive"):
        return
    r, D = rnd(house, "drive", pet["id"]), character.DATA["drives"]
    kin = [K.drive(p["drive"])["name"] for p in character.parents_of(house, pet) if p.get("drive")]
    w = [max(0.05, 1 + 2 * character.leans(pet, D[d]["leans"])) + kin.count(d) for d in K.DRIVES]
    d = r.choices(K.DRIVES, w)[0]
    f = r.choices(D[d]["flaws"], [max(0.05, 1 + 2 * character.leans(pet, character.DATA["flaws"][f])) for f in D[d]["flaws"]])[0]
    pet["drive"], pet["flaw"] = K.drive({"name": d, "since": house["tick"]}), K.flaw({"name": f})
    pet["voice"] = card(house, pet)


def card(house, pet):
    """SPEC-v4.2.2 §2 the voice card: its style drawn by its traits (character.toml [voice.style]: sociable, sunny or
    eager; tidy, fussy; brave, big-sister; patient, gentle or easygoing; unkind, grumbly; curious, know-it-all), and
    what it cares about, from its drive (its one by name, once it has one)."""
    V = character.DATA["voice"]
    style = character.pick(rnd(house, "style", pet["id"]), pet, V["style"], 1)[0]
    cares = (pet["drive"].get("target_name") or V["cares"][K.drive(pet["drive"])["name"]]) if pet.get("drive") else ""
    return K.voice({"style": style, "cares": cares})


def keep_secret(house, cfg, pet, kind, text, about=None):
    """§6.3 a secret, if it keeps none now (one found out leaves room for another). Returns it, or None."""
    if not on(cfg) or not pet or pet["stage"] in ("egg", "dead") or (pet.get("secret") and not pet["secret"].get("found")):
        return None
    pet["secret"] = K.secret({"kind": kind, "text": text, "about": about, "tick": house["tick"]})
    return pet["secret"]


def found(house, cfg, pet, by, how="in talk"):
    """§6.3 its secret is out: a moment (the view's banner), the ledger's line, a memory each side; a lie, a thing broken
    or taken, a fall cost it the finder's trust. `by`: a hob, or "visitor" (D's question). True if there was one."""
    from . import memories, opinions
    s = pet.get("secret")
    if not on(cfg) or not s or s.get("found"):
        return False
    s["found"] = house["tick"]
    finder = house["pets"].get(by) if isinstance(by, str) else by
    who = label(finder) if finder else "the visitor"
    moment(house, "secret found", "%s found out what %s kept to itself: %s" % (who, label(pet), s["text"]), pet["id"], pet["room"])
    house["moments"][-1]["pets"] = [pet["id"]] + ([finder["id"]] if finder else [])
    K.note(house, "secret found", pet=pet["id"], by=finder["id"] if finder else "visitor", how=how)
    memories.add(house, cfg, pet, "%s found out what I kept to myself: %s" % (who, s["text"]), 4, about=[finder["id"]] if finder else ["visitor"], kind="secret found")
    if finder:
        memories.add(house, cfg, finder, "I found out what %s kept to itself: %s" % (label(pet), s["text"]), 4, about=[pet["id"]], kind="secret found")
        if s["kind"] in ("lie", "broken", "taken", "fall"):
            opinions.move(house, cfg, finder, pet["id"], "lied_to_me", "%s kept it from me: %s" % (label(pet), s["text"]))
    return True


# ---- each tick (talk.tick calls it: the one part of the house with an engine at hand) ----

def tick(eng):
    """The secrets other parts left take hold; once a world hour, "to be loved by one" finds its one, what it has done
    for its drive is kept, and a love never said becomes a secret."""
    h, cfg = eng.house, eng.cfg
    if not on(cfg):
        return
    from . import memories, opinions
    for m in memories.new_moments(h, "drives"):   # an envious hob resents another's first (§6.2)
        if m["kind"] == "first" and m.get("pet") in h["pets"]:
            for p in alive(h):
                if p["id"] != m["pet"] and (p.get("flaw") or {}).get("name") == "envious" and p["stage"] not in ("egg", "hatchling"):
                    opinions.move(h, cfg, p, m["pet"], "envy", "%s got there first: %s" % (label(h["pets"][m["pet"]]), m["text"]))
    hourly = h["tick"] % hours(cfg, 1) == 0
    for pet in alive(h):
        for s in pet.pop("secret_due", None) or []:
            keep_secret(h, cfg, pet, s["kind"], s["text"], s.get("about"))
        if hourly and pet.get("drive") and pet["stage"] != "egg":
            standing(h, cfg, pet)


def standing(house, cfg, pet):
    from . import bonds, opinions
    d = pet["drive"]
    if d["name"] == "to be loved by one" and pet["stage"] in ("youngling", "adult", "elder"):
        one = house["pets"].get(d.get("target") or "")
        if not one or one["stage"] == "dead":
            liked = [(opinions.of(pet, p["id"])["liking"], p["id"]) for p in alive(house) if p is not pet and p["stage"] != "egg"]
            if liked:
                one = house["pets"][max(liked)[1]]
                d.update(target=one["id"], target_name=label(one))
                if pet.get("voice"):
                    pet["voice"]["cares"] = label(one)   # (SPEC-v4.2.2 §2: what it cares about is its one, by name)
        if one and one["stage"] != "dead" and bonds.kind(house, pet["id"], one["id"]) != "close" and opinions.of(pet, one["id"])["liking"] >= 5:
            keep_secret(house, cfg, pet, "feeling", "I love %s, and I have never said so" % label(one), one["id"])
    did = pet.setdefault("for_drive", [])
    for a in pet.get("aims") or []:   # (an aim of a kind that serves it, done, is something done for it)
        if isinstance(a.get("done"), int) and a["kind"] in SERVES[d["name"]]["aims"] and a["text"] not in did:
            did.append(a["text"])
    del did[:-5]


def line(pet):
    """§4.5 drive and flaw in one line, for every packet: the standing aim, with what it has done for it so far."""
    bits = []
    if pet.get("drive"):
        d = pet["drive"]
        did = pet.get("for_drive") or []
        bits.append("what you want most: %s%s; what you've done about it so far: %s" % (K.drive(d)["name"], " (%s)" % d["target_name"] if d.get("target_name") else "",
                                                                                "; ".join(did[-3:]) or "nothing yet"))
    if pet.get("flaw"):
        f = K.flaw(pet["flaw"])["name"]
        bits.append("your flaw: %s (%s)" % (f, FLAW_WORDS[f]))
    return "; ".join(bits)


def score(house, cfg, pet, activity, A=None, t=None):
    """(planner.adjust) What its drive and flaw add to an activity: [drives] serve for one that serves the drive ("to be
    loved by one": with its one, once it has one), [drives] flaw toward or away from what the flaw pulls at."""
    if not on(cfg):
        return 0.0
    A, t, s = A or cfg["activities"].get(activity) or {}, t or {}, 0.0
    do, d = A.get("do"), pet.get("drive")
    if d:
        S = SERVES[K.drive(d)["name"]]
        if (do in S["do"] or activity in S["names"]) and (not d.get("target") or not t.get("who") or t["who"] == d["target"]):
            s += cfg["drives"]["serve"]
    if pet.get("flaw"):
        F = FLAW_SCORE[K.flaw(pet["flaw"])["name"]]
        s += F.get(activity, F.get(do, 0)) * cfg["drives"]["flaw"]
    return s


# ---- the reflection: a drive changes once in a life ----

def shaken(house, cfg, pet, since):
    """What today did that could change what it is for (a death of one close, a betrayal), in words, or "" (and "" once
    its drive has changed)."""
    if not on(cfg) or not pet.get("drive") or K.drive(pet["drive"])["changed"]:
        return ""
    for m in reversed(house.get("moments", [])):
        if m["tick"] < since:
            break
        dead = house["pets"].get(m.get("pet") or "")
        if m["kind"] == "death" and dead and pet in character.kin_and_friends(house, dead):
            return m["text"]
    for oid, o in (pet.get("opinions") or {}).items():
        c = next((c for c in reversed(o.get("causes", [])) if c.get("tick", -1) >= since and c.get("cause") in BETRAYED), None)
        if c:
            return c.get("why") or "%s betrayed you" % label(house["pets"].get(oid, {"id": oid}))
    return ""


def reconsider(house, cfg, pet, for_line):
    """After a day that shook it, the "what I am for" it wrote names another drive: that is its drive now (once a
    life). Returns the new drive's name, or None."""
    low = " %s " % (for_line or "").lower()
    hits = sorted((low.find(w), d) for d, ws in DRIVE_WORDS.items() for w in ws if w in low)   # ponytail: keywords, a schema field if it misreads
    old = K.drive(pet.get("drive"))
    if not on(cfg) or not hits or old["changed"] or hits[0][1] == old["name"]:
        return None
    new = hits[0][1]
    pet["drive"] = K.drive({"name": new, "since": house["tick"], "changed": True})
    pet["for_drive"] = []
    from . import memories
    memories.add(house, cfg, pet, "I am not for %s any more; I am for %s now" % (old["name"][3:], new[3:]), 4, kind="drive")
    return new


# ---- §6.5 the migration, once a house (Engine.spirit_migration awaits it at the restart) ----

async def migrate(eng):
    """Every living hob gets a drive, a flaw and a voice card, and a secret if it has told a lie still not found out.
    Once a house (house["migrated"]["v42_drives"]). Returns the report's lines."""
    h, cfg = eng.house, eng.cfg
    done = h.setdefault("migrated", {})
    if not on(cfg) or done.get("v42_drives"):
        return []
    done["v42_drives"] = h["tick"]
    out = []
    for pet in sorted((p for p in alive(h) if p["stage"] != "egg"), key=lambda p: p["id"]):
        draw(h, cfg, pet)
        lie = next((x for x in reversed(h.get("lies", [])) if x["teller"] == pet["id"]), None)
        if lie:
            about = h["pets"].get(lie["about"])
            keep_secret(h, cfg, pet, "lie", "I told %s a thing about %s that was not true" % (label(h["pets"][lie["listener"]]) if lie["listener"] in h["pets"] else "someone",
                                                                                           label(about) if about else "the visitor"), lie["listener"])
        s = pet.get("secret")
        out.append("%s: %s; flaw %s; secret: %s; voice: %s" % (label(pet), pet["drive"]["name"], pet["flaw"]["name"], s["text"] if s and not s.get("found") else "none",
                                                               K.voice_line(pet["voice"])))
    return out


def restyle(house, cfg):
    """SPEC-v4.2.2 §2's migration: every living hob's voice card drawn again under the eight styles (no model call).
    Once a house (house["migrated"]["v422_voice"]). Returns the report's lines."""
    done = house.setdefault("migrated", {})
    if not on(cfg) or done.get("v422_voice"):
        return []
    done["v422_voice"] = house["tick"]
    out = []
    for pet in sorted((p for p in alive(house) if p["stage"] != "egg" and p.get("drive")), key=lambda p: p["id"]):
        pet["voice"] = card(house, pet)
        out.append("%s: %s (%s)" % (label(pet), pet["voice"]["style"], K.voice_line(pet["voice"])))
    return out
