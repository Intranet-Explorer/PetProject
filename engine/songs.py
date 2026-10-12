"""Songs (SPEC-v3.1 §3): tunes made up, sung, taught, and misheard. A song taught is learned exactly; a song
picked up by ear may shift a note, and that new version is what the listener sings from then on. Every version
is kept, with the one it came from, so the Songbook can show how a tune drifted down a family."""
from .world import add_event, family, here, label, moment, rnd

PITCH = ["low do", "low re", "low mi", "low so", "low la", "do", "re", "mi", "so", "la",
         "high do", "high re", "high mi", "high so", "high la"]
NOTES = ["%s %s" % (p, n) for p in PITCH for n in ("short", "long")]   # how a note is written in an action
BOX = [["mi", 0], ["so", 0], ["la", 1], ["so", 0], ["mi", 0], ["re", 0], ["do", 1]]   # the music box's tune
BIRD = [["high mi", 0], ["high so", 0], ["high mi", 0], ["high la", 1], ["high so", 0]]


def parse(notes, cfg):
    """An action's notes as [[pitch, long], ...], or None if they are not a tune."""
    S = cfg["songs"]
    if not isinstance(notes, list) or not S["min_notes"] <= len(notes) <= S["max_notes"] or any(n not in NOTES for n in notes):
        return None
    return [[n.rsplit(" ", 1)[0], int(n.endswith("long"))] for n in notes]


def sound(notes):
    """How a tune sounds, in a couple of words. A pet is told this and never the notes (§3.3)."""
    at = [PITCH.index(p) for p, _ in notes]
    third = max(1, len(at) // 3)
    lean = sum(at[-third:]) / third - sum(at[:third]) / third
    shape = "rising" if lean >= 1.5 else "falling" if lean <= -1.5 else "turning back on itself" if max(at) - min(at) >= 4 else "level"
    pace = "slow" if sum(l for _, l in notes) * 2 >= len(notes) else "quick" if not any(l for _, l in notes) else "unhurried"
    place = "low" if sum(at) / len(at) < 4 else "high" if sum(at) / len(at) > 9.5 else ""
    return ", ".join(w for w in (shape, pace, place) if w)


def book(house):
    return house.setdefault("songs", {})


def add(house, name, notes, by, frm=None, how="made up", fam=1):
    """A song, or a new version of one. `frm` is the version it came from."""
    house["n"]["song"] = house["n"].get("song", 0) + 1
    sid = "s%d" % house["n"]["song"]
    book(house)[sid] = {"id": sid, "name": name, "notes": notes, "by": by, "from": frm, "how": how, "tick": house["tick"], "family": fam}
    house.setdefault("fresh_songs", []).append(book(house)[sid])
    return sid


def root(house, sid):
    while book(house)[sid]["from"]:
        sid = book(house)[sid]["from"]
    return sid


def known(house, pet, name=None, of=None):
    """Its entry for a song by name, or for any version of the same tune as `of`."""
    for e in pet.get("songs", []):
        s = book(house).get(e["id"])
        if s and ((name is not None and s["name"].lower() == name.strip().lower()) or (of is not None and root(house, e["id"]) == root(house, of))):
            return e
    return None


def names(house, pet):
    return [book(house)[e["id"]]["name"] for e in pet.get("songs", []) if e["id"] in book(house)]


def keep(house, cfg, pet, sid, heir=None):
    """Into its repertoire. Past what it can hold, the one it has sung least goes (the newest is safe)."""
    pet.setdefault("songs", []).append({"id": sid, "sung": 0, "since": house["tick"], **({"heir": heir} if heir else {})})
    while len(pet["songs"]) > cfg["songs"]["repertoire"]:
        lost = min(pet["songs"][:-1], key=lambda e: (e["sung"], e["since"]))
        pet["songs"].remove(lost)
        add_event(house, pet, 'you find you can no longer bring "%s" to mind' % book(house)[lost["id"]]["name"])


def by_ear(house, cfg, pet, sid):
    """What it makes of a song it has only heard: each note may slip a step. A slipped tune is a new version."""
    from . import craft   # SPEC-v3.4 §2.2: a tune slips less in the ear of one who holds a tune well
    r, notes, drift = rnd(house, "ear", pet["id"], sid, house["tick"]), [], cfg["songs"]["ear_drift"] * (1 - 0.25 * craft.skill(cfg, pet, "music"))
    for p, long in book(house)[sid]["notes"]:
        i = PITCH.index(p)
        if r.random() < drift:
            i = min(len(PITCH) - 1, max(0, i + r.choice([-1, 1])))
        notes.append([PITCH[i], long])
    if notes == book(house)[sid]["notes"]:
        return sid
    return add(house, book(house)[sid]["name"], notes, pet["id"], sid, "by ear", family(pet))


def heard(house, cfg, room, sid, singer, said, but=()):
    """A song sounds in a room. Everyone awake there hears it; whoever does not know the tune takes an interest and
    picks it up by ear (§3.2)."""
    s = book(house)[sid]
    for p in [p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]]:
        if p["id"] == singer or p in but:
            continue
        add_event(house, p, '%s "%s": %s' % (said(p), s["name"], sound(s["notes"])))
        if not known(house, p, of=sid):
            keep(house, cfg, p, by_ear(house, cfg, p, sid))
            p["needs"]["curiosity"] = min(100.0, p["needs"]["curiosity"] + cfg["effects"]["new_song"])
            add_event(house, p, "you had not heard it before, and it stays with you; you could sing it")
            p["news"].append("heard")
    house.setdefault("sung", []).append({"tick": house["tick"], "by": singer, "song": sid, "room": room["id"]})
    del house["sung"][:-12]
    house.setdefault("said", []).append({"tick": house["tick"], "from": singer, "to": None, "kind": "sing", "text": s["name"]})


def unique(house, name):
    taken, base, n = {s["name"].lower() for s in book(house).values()}, name, 2
    while name.lower() in taken:
        name, n = "%s %d" % (base, n), n + 1
    return name


def compose(house, cfg, pet, a, clean):
    name = unique(house, clean(a["name"], 24))
    sid = add(house, name, parse(a["notes"], cfg), pet["id"], fam=family(pet))
    keep(house, cfg, pet, sid)
    moment(house, "song", '%s made up a song: "%s"' % (label(pet), name), pet["id"], pet["room"])
    return 'you made up a song and called it "%s": %s' % (name, sound(book(house)[sid]["notes"])), {"curiosity": cfg["effects"]["new_song"]}, "compose"


def sing(house, cfg, pet, a, find, handle, bump):
    """Sing a song it knows, to someone or to the room. To an egg or a sleeping child it is a lullaby."""
    e, room, E = known(house, pet, a["song"]), house["rooms"][pet["room"]], cfg["effects"]
    s = book(house)[e["id"]]
    e["sung"], e["last"] = e["sung"] + 1, house["tick"]
    from . import craft
    craft.practise(house, cfg, pet, "music", 0.5)
    kind, other = find(house, pet, a.get("to")) if isinstance(a.get("to"), str) and a["to"].strip() else (None, None)
    fx, to = dict(E["speak"]), ""
    if kind == "egg" or (kind == "pet" and other["sleep"]):
        other["needs"]["comfort"] = min(100.0, other["needs"]["comfort"] + E["lullaby"])
        to = " to the egg" if kind == "egg" else " over %s as they slept" % handle(house, pet, other)
    elif kind == "pet":
        key = "sing " + other["id"]   # wears with repetition, as speaking and leaning do, until a night has passed
        n = pet["times"].get(key, 0)
        worth = max(0.1, E["nuzzle_wear"] ** n)
        pet["times"][key], pet["seen_at"][key] = min(cfg["novelty"]["cap"], n + 1), house["tick"]
        bump(other, cfg, {"company": E["spoken_to"] * worth})
        other["inbox"].append('%s sang "%s" to you: %s' % (handle(house, other, pet), s["name"], sound(s["notes"])))
        other["news"].append("spoken")
        fx["company"], to = E["said_to"] * worth, " to " + handle(house, pet, other)
    heard(house, cfg, room, e["id"], pet["id"], lambda p: "you hear %s singing" % handle(house, p, pet), but=[other] if kind == "pet" and not other["sleep"] else ())
    if kind == "pet" and not other["sleep"] and not known(house, other, of=e["id"]):   # sung to, it learns by ear like anyone
        keep(house, cfg, other, by_ear(house, cfg, other, e["id"]))
        other["needs"]["curiosity"] = min(100.0, other["needs"]["curiosity"] + E["new_song"])
        other["inbox"].append("you had not heard it before, and it stays with you; you could sing it")
    house["said"][-1]["to"] = other["id"] if kind in ("pet", "egg") else None
    pet["said"] = {"text": "♪ " + s["name"], "tick": house["tick"], "to": other["id"] if kind == "pet" else None, "song": e["id"]}
    return 'you sang "%s"%s' % (s["name"], to), fx, "sing " + root(house, e["id"])


def teach(house, cfg, pet, a, find, handle):
    """Taught on purpose, a song is learned exactly (§3.1)."""
    e, other = known(house, pet, a["song"]), find(house, pet, a["to"])[1]
    s = book(house)[e["id"]]
    had = known(house, other, of=e["id"])
    if had:
        had["id"] = e["id"]   # its own version gives way to the one it is taught
    else:
        keep(house, cfg, other, e["id"])
    add_event(house, other, '%s taught you "%s", note for note: %s' % (handle(house, other, pet), s["name"], sound(s["notes"])))
    other["news"].append("spoken")
    house.setdefault("said", []).append({"tick": house["tick"], "from": pet["id"], "to": other["id"], "kind": "teach song", "text": s["name"]})
    moment(house, "song", '%s taught %s "%s"' % (label(pet), label(other), s["name"]), pet["id"], pet["room"])
    return 'you taught %s "%s", note for note' % (handle(house, pet, other), s["name"]), {"company": cfg["effects"]["said_to"]}, "teach song"


def leave(house, cfg, pet, kids, name):
    """An heirloom can be a song (§3.4): the children have it from then on, exactly."""
    e = known(house, pet, name)
    for k in kids:
        had = known(house, k, of=e["id"])
        if had:
            had.update(id=e["id"], heir=pet["id"])
        else:
            keep(house, cfg, k, e["id"], heir=pet["id"])
        if k["stage"] != "egg":
            add_event(house, k, 'your %s has left you a song, "%s"' % (pet["word"], book(house)[e["id"]]["name"]))
    moment(house, "heirloom", '%s left the song "%s" to %s' % (label(pet), book(house)[e["id"]]["name"], " and ".join(label(k) for k in kids)), pet["id"], pet["room"])
    return 'you gave "%s" to %s to keep' % (book(house)[e["id"]]["name"], "your children" if len(kids) > 1 else label(kids[0])), {}, "bequeath"


def music_box(house, cfg, room):
    """The first song in the house (§1): the music box plays a tune by itself. Whoever is awake to hear it has it."""
    sid = next((s["id"] for s in book(house).values() if s["by"] == "music box"), None) or add(house, "the music box's tune", BOX, "music box", how="the music box", fam=0)
    before = {p["id"] for p in house["pets"].values() if known(house, p, of=sid)}
    heard(house, cfg, room, sid, "music box", lambda p: "the music box begins to play by itself:")
    return any(known(house, p, of=sid) and p["id"] not in before for p in house["pets"].values())
