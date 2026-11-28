"""SPEC-v4.0 §1 character: ten axes with opposites (genes), quirks, values and moods. Switch: [traits] on.

The axes are temper genes (world.GENES): six from v3 under new names, four new ones appended last. What each pole does
is data (character.toml), read by the body through `does`; moods shade behaviour through `mood_weight`."""
import tomllib

from .world import ROOT, alive, hours, rnd
from . import sheet

AXES = ("brave", "tidy", "generous", "curious", "social", "honest", "patient", "playful", "ambitious", "kind")
GENE = {"brave": "bold", "tidy": "orderly", "social": "sociable"}   # the axes from older genes; the rest have their own
MOODS = ("happy", "content", "grumpy", "sad", "afraid", "angry", "proud", "ashamed", "lonely", "excited")
DATA = tomllib.loads((ROOT / "character.toml").read_text())
BEHAVIOURS = {b: (axis, sign) for axis, a in DATA["axes"].items() for sign, pole in ((1, "plus"), (-1, "minus")) for b in a[pole]}


def on(cfg):
    return bool(cfg.get("traits", {}).get("on"))


ON = True   # (19 October 2026) the switch as the house last ticked (`tick`): `trait` has no cfg, and was read everywhere while off
# ponytail: one switch for the whole process (the engine runs one house); a cfg argument on `trait` if two houses ever share one


def trait(pet, axis):
    """-1 (the second pole) to +1 (the first): brave/timid, tidy/messy, generous/greedy, curious/cautious, social/solitary,
    honest/sly, patient/hasty, playful/serious, ambitious/content, kind/prickly. Off: 0, the middle, for every hob."""
    if not ON:
        return 0.0
    return round(2 * pet["temper"].get(GENE.get(axis, axis), 0.5) - 1, 2)


def leans(pet, spec):
    """How well a hob fits a list of leanings like ["brave+", "social-"]: the mean of the signed traits (0 for none)."""
    return sum(trait(pet, s[:-1]) * (1 if s[-1] == "+" else -1) for s in spec) / len(spec) if spec else 0.0


def does(pet, behaviour):
    """0..1: how strongly this hob shows one pole's behaviour (character.toml): 0 in the middle and at the other pole."""
    axis, sign = BEHAVIOURS[behaviour]
    return round(max(0.0, (trait(pet, axis) * sign - 0.2) / 0.8), 2)


def degree(v):
    return "very " if abs(v) >= 0.7 else "" if abs(v) >= 0.45 else "a little " if abs(v) >= 0.25 else None


def words(pet):
    """Its traits in plain words, the strongest first: "very brave, tidy, a little greedy"."""
    out = []
    for a in sorted(AXES, key=lambda a: -abs(trait(pet, a))):
        v = trait(pet, a)
        if degree(v) is not None:
            out.append(degree(v) + DATA["axes"][a]["words"][v < 0])
    return ", ".join(out) or "even-tempered in everything"


def describe(pet):
    """Traits, quirks and values in one line, for a packet."""
    s = "you are " + words(pet)
    if pet.get("quirks"):
        s += "; your ways: " + " and ".join(pet["quirks"])
    if pet.get("values"):
        s += "; what you care about most: " + " and ".join(pet["values"])
    return s


# ---- moods (§1.3) ----

def mood(pet):
    return (pet.get("mood") or {}).get("mood") or "content"


def swing(pet):
    """A sensitive hob's moods swing harder and last longer: 0.5 to 1.5."""
    return 0.5 + pet["temper"].get("sensitive", 0.5)


def left(house, pet):
    """What is left of its mood's strength now, fading to nothing at its end."""
    m = pet.get("mood")
    if not m or house["tick"] >= m["until"]:
        return 0.0
    return m.get("strength", 0.3) * (m["until"] - house["tick"]) / max(1, m["until"] - m["since"])


def set_mood(house, cfg, pet, mood_, why, hours=None):
    """A mood from an event; it lasts hours and fades. A weaker mood does not push a stronger one aside. True if set."""
    if not on(cfg) or mood_ not in MOODS or pet["stage"] in ("egg", "dead"):
        return False
    M, s = DATA["moods"][mood_], swing(pet)
    strength = M["strength"] * s
    if mood_ != mood(pet) and strength < left(house, pet):
        return False
    long = (M["hours"] if hours is None else hours) * s
    pet["mood"] = {"mood": mood_, "since": house["tick"], "until": house["tick"] + round(long * cfg["ticks_per_hour"]), "why": why,
                   "strength": round(strength, 2)}
    return True


def mood_weight(pet, what):
    """How its mood shades one kind of behaviour (character.toml [moods]): ladder, give, play, talk, withdraw, work,
    explore, rest. 1 is no change; a sensitive hob's mood counts for more."""
    w = DATA["moods"].get(mood(pet), {}).get(what)
    return 1.0 if w is None else round(max(0.0, 1 + (w - 1) * swing(pet)), 2)


def felt_mood(cfg, pet):
    """The mood its needs give it when nothing has happened: lonely, afraid, grumpy, sad, or content."""
    from . import feel, needs
    new = needs.on(cfg) and "hunger" in pet["needs"]
    if feel.level(pet, "company") >= 3:
        return "lonely", "nobody near"
    if new and feel.level(pet, "safety") >= 3:
        return "afraid", "feeling unsafe"
    if new and feel.level(pet, "hunger") >= 3:
        return "grumpy", "hungry"
    if feel.level(pet, "energy") >= 4:
        return "grumpy", "worn out"
    if new and feel.level(pet, "pride") >= 4:
        return "sad", "feeling useless"
    if all(feel.level(pet, n) <= 1 for n in ("company", "comfort", "energy")) and (not new or feel.level(pet, "hunger") <= 1):
        return "happy", "a good day: rested, comfortable and in company"
    return "content", "nothing much has happened"


# ---- quirks and values (§1.2) ----

def pick(rng, pet, table, n, have=()):
    """`n` of a table's keys, weighted by how well the hob fits each one's leanings."""
    out, pool = [], [k for k in table if k not in have]
    for _ in range(n):
        k = rng.choices(pool, [max(0.05, 1 + 2 * leans(pet, table[k])) for k in pool])[0]
        out.append(k)
        pool.remove(k)
    return out


def parents_of(house, pet):
    return [house["pets"][p] for p in (pet.get("parents") or [pet.get("parent")]) if p in house["pets"]]


def quirks_for(house, pet, rng):
    """One or two quirks, from its traits and (half the time) one of its parents'."""
    n, out = 1 + (rng.random() < 0.5), []
    kin = sorted({q for p in parents_of(house, pet) for q in p.get("quirks", [])})
    if kin and rng.random() < 0.5:
        out.append(rng.choice(kin))
    return out + pick(rng, pet, DATA["quirks"], n - len(out), out)


def give_character(house, cfg, pet, rng=None):
    """Quirks, values and a mood, for a hob that has none yet (at hatching, a foundling, or a living hob migrated)."""
    rng = rng or rnd(house, "character", pet["id"])
    pet.setdefault("quirks", quirks_for(house, pet, rng))
    pet.setdefault("values", pick(rng, pet, DATA["values"], 2))
    pet.setdefault("mood", {"mood": "content", "since": house["tick"], "until": house["tick"], "why": "", "strength": 0.3})


def kin_and_friends(house, pet):
    """The living who would grieve it or be glad for it: its parents, children, bond and those who like it well."""
    from . import opinions
    out = {p["id"]: p for p in parents_of(house, pet)}
    out.update({c: house["pets"][c] for c in pet.get("children", []) if c in house["pets"]})
    out.update({p["id"]: p for p in alive(house) if opinions.of(p, pet["id"])["liking"] >= 4})
    return [p for p in out.values() if p["stage"] not in ("egg", "dead") and p is not pet]


# moment kind -> (the mood of the hob it is about, (who else feels it, and what)). The moment listener is the one place
# the house's existing events set moods; events with two sides set them at their sites through opinions.move.
MOMENT_MOOD = {"first": ("proud", None), "best": ("proud", None), "invented": ("excited", None), "built": ("proud", None),
               "catch": ("happy", None), "gift": ("happy", None), "egg": ("proud", None), "weak": ("sad", None), "lost": ("grumpy", None),
               "meal": ("happy", None), "discovery": ("excited", None),
               # (18 October 2026, two days of v4.0 on live: every hob "content", for the moods its days gave were few)
               "want": ("happy", None), "mended": ("proud", None), "machine": ("happy", None), "harvest": ("happy", None),
               "designed": ("excited", None), "design built": ("proud", None), "first working design": ("proud", None),
               "design failed": ("grumpy", None), "noticed": ("proud", None), "planted": ("content", None), "read": ("excited", None),
               "hatched": (None, (parents_of, "happy")), "death": (None, (kin_and_friends, "sad"))}


def tick(house, cfg):
    global ON
    ON = on(cfg)
    if not ON:
        for pet in house["pets"].values():   # (off: nobody is in a mood, so mood_weight is 1 for every reader)
            if (pet.get("mood") or {}).get("mood", "content") != "content":
                pet["mood"] = dict(pet["mood"], mood="content", until=house["tick"])
        return
    from . import memories
    if sheet.on(cfg):
        sheet.once(house, cfg)
        sheet.mend(house, cfg)
    for pet in alive(house):
        if pet["stage"] == "egg":
            continue
        if "values" not in pet:
            give_character(house, cfg, pet)
        if "sheet" not in pet and sheet.on(cfg):   # (24 November 2026) at hatching, and the living once
            sheet.give(house, cfg, pet)
        if house["tick"] >= pet["mood"]["until"] and house["tick"] % hours(cfg, 0.25) == 0:   # between events, the mood its needs give it, for a while
            m, why = felt_mood(cfg, pet)   # (18 October 2026: it lasted no time at all, so every hob read "content", with no why)
            if m == pet["mood"]["mood"] and pet["mood"].get("why") == why:
                pet["mood"]["until"] = house["tick"] + hours(cfg, cfg["traits"].get("needs_mood_hours", 2))
            else:
                pet["mood"] = {"mood": m, "since": house["tick"], "until": house["tick"] + hours(cfg, cfg["traits"].get("needs_mood_hours", 2)),
                               "why": why, "strength": round(DATA["moods"][m]["strength"] * 0.5, 2)}
    for m in memories.new_moments(house, "character"):
        pet = house["pets"].get(m["pet"] or "")
        if not pet or m["kind"] not in MOMENT_MOOD:
            continue
        own, also = MOMENT_MOOD[m["kind"]]
        if own:
            set_mood(house, cfg, pet, own, m["text"])
        if also:
            for other in also[0](house, pet):
                set_mood(house, cfg, other, also[1], m["text"])
