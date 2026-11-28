"""SPEC-v4.0 §7.3 injury and sickness (helper C); SPEC-v4.2 §2.2-2.6 sickness with a course and a cause (helper A).
Switches: [health] on; [deaths] on (through contracts.on) for v4.2's. The numbers are in conflict.toml [hurt], [sick] and
config.toml [deaths].

pet["hurt"] = {"level": "bruised"|"hurt"|"badly hurt"|None, "since", "lasting": "limp"|None, "left", "why"}: it slows the
hob, wears its energy and comfort, and heals a level at a time, faster asleep and with a healer by it. Badly hurt may
leave a lasting limp (then level is None and the limp stays). pet["sick"] = {"level": one of contracts.SICK, "since",
"from"}. v4.0.6 called the levels unwell, sick, very sick: an old save's are read as the new (contracts.OLD_SICK).

With [deaths] off, v4.0.6's: from the cold out of doors, food about to go stale, or another sick hob; looked over every
world hour: care (rest, warmth, a healer) brings it down, neglect makes it worse, and very sick and neglected can kill.

With [deaths] on (§2.2): it is caught at night (a cold room in autumn or winter without a bed, a bed shared with a sick
hob, a bad hurt left untended a day, a winter night out of doors) or at once from bad food (§2.4); once a world day,
in the small hours, a day untended moves it on with `worsen`'s chance, and gravely ill and untended a further day it
dies. A day tended (a hob's `nurse` beside it, the visitor's tend, a remedy) moves it back a stage (a remedy two). The
record also keeps "cause" (a contracts.DEATHS key), "what" (what it ate), "tended" (tick), "grave" (tick it got there).
pet["decline"] = {cause: tick}: since when its decline has shown on the page (§2 "foreshadowed"; FORESHADOW).

A death is handed to the engine's own path: pet["death_due"] = cause (and pet["death_words"]), which life.due returns,
and Engine.kill does the rest. Switched off: nothing starts, and whatever hurt or sickness a hob has goes at once (the
limp too): v3.6c's hobs."""
from . import conflict, contracts as K, memories, opinions
from .world import add_event, here, label, moment, rnd

HURT = ("bruised", "hurt", "badly hurt")
SICK = K.SICK
# its body in words, for a packet: v4.2's (a stage that shows), and v4.0.6's for a sickness caught with [deaths] off
FEEL = {"unwell": "you feel unwell: pale, and slow", "ill": "you are ill: you want your bed, and can hardly eat", "gravely ill": "you are gravely ill: you cannot get up"}
OLD_FEEL = {"unwell": "you feel unwell", "ill": "you are sick", "gravely ill": "you are very sick"}
# §2 "foreshadowed": for each cause but old age and killing, what has shown on the page (§11.3) for at least a world
# day before it can kill. declined() is the gate; life.due asks it.
FORESHADOW = {"sickness": "unwell, then ill, then gravely ill: pale, in bed, then not getting up",
              "injury": "badly hurt, and the hurt left untended until it turned to a sickness",
              "bad food": "ill at once from what it ate, then gravely ill",
              "exposure": "unwell after a night out in the cold, ill after a second",
              "manslaughter": "a feud with the one who shoved it: a thing of its broken, hidden or taken first",
              "starvation": "starving: weak and slow",
              "neglect": "weak from neglect"}
NIGHT_HOUR = 3   # the small hours: the night's catching and the day's course are looked at once a world day, then
REMEDY = "remedy"


def on(cfg):
    return bool(cfg.get("health", {}).get("on"))


def deaths(cfg):
    return on(cfg) and K.on(cfg, "deaths")


def C(cfg):
    return conflict.C(cfg)


def alive(p):
    return p["stage"] not in ("egg", "dead")


def stage_of(pet):
    """Its sickness: one of contracts.SICK, or None (an old save's names read as the new)."""
    lv = (pet.get("sick") or {}).get("level")
    lv = K.OLD_SICK.get(lv, lv)
    return lv if lv in SICK else None


def mark(house, pet, cause):
    """Its decline from this cause has begun to show (kept from the first time until it is well)."""
    pet.setdefault("decline", {}).setdefault(cause, house["tick"])


def declined(house, cfg, pet, cause):
    """Has its decline from this cause shown for at least a world day (§2 "foreshadowed")? Old age and killing need none."""
    t, day = house["tick"], cfg["ticks_per_day"]
    if cause in ("old age", "killing"):
        return True
    if cause == "manslaughter":   # (the feud's history: a sabotage or a theft against it, a world day before; v5.3.1: or its shover's near-fall)
        by = house["pets"].get(pet.get("shoved_by") or "") or {}
        if by.get("near_fell") is not None:
            return True
        return any(g["against"] == pet["id"] and any(r >= 3 and t - at >= day for at, r, _ in g["history"]) for g in conflict.grievances(house) + house.get("grievances_done", []))
    since = (pet.get("decline") or {}).get(cause)
    return since is not None and t - since >= day


def hurt(house, cfg, pet, level, why):
    """An injury (a fight, a fall, the forge: accidents): the worse of what it has and this; hurt again on top of a hurt is worse.
    Returns the level, or None while off."""
    if not on(cfg) or not alive(pet):
        return None
    old = pet.get("hurt") or {}
    if old.get("level") in HURT and HURT.index(old["level"]) >= HURT.index(level):
        level = HURT[min(2, HURT.index(old["level"]) + (1 if HURT.index(level) else 0))]
    pet["hurt"] = {"level": level, "since": house["tick"], "lasting": old.get("lasting"), "left": C(cfg)["hurt"]["heal_days"][level] * cfg["ticks_per_day"], "why": why}
    if level == "badly hurt" and deaths(cfg):
        mark(house, pet, "injury")
    add_event(house, pet, "you are %s: %s" % (level, why))
    pet["news"].append("event")
    return level


def sicken(house, cfg, pet, frm, level=None, cause="sickness", what=None):
    """It falls ill, or a little worse if it already is (to `level` at least, if given). With [deaths] on the record
    keeps its cause (a contracts.DEATHS key) and, for bad food, what it ate."""
    if not on(cfg) or not alive(pet):
        return None
    if not deaths(cfg):
        if pet.get("sick"):
            return worse(house, cfg, pet)
        pet["sick"] = {"level": "unwell", "since": house["tick"], "from": frm}
        add_event(house, pet, "you feel unwell (%s)" % frm)
        moment(house, "sick", "%s has fallen ill (%s)" % (label(pet), frm), pet["id"], pet["room"])
        return "unwell"
    now = stage_of(pet)
    if now:
        if not level or SICK.index(level) <= SICK.index(now):
            return worse(house, cfg, pet) if not level else now
        pet["sick"]["level"] = level
    else:
        pet["sick"] = {"level": level or "unwell", "since": house["tick"], "from": frm, "cause": cause, "what": what}
        moment(house, "sick", "%s has fallen ill (%s)" % (label(pet), frm), pet["id"], pet["room"])
    mark(house, pet, pet["sick"].get("cause") or cause)
    add_event(house, pet, "%s (%s)" % (FEEL[pet["sick"]["level"]], frm))
    pet["news"].append("event")
    if pet["sick"]["level"] == SICK[2]:
        grave(house, pet)
    return pet["sick"]["level"]


def grave(house, pet):
    pet["sick"]["grave"] = house["tick"]
    moment(house, "gravely ill", "%s is gravely ill, and does not get up" % label(pet), pet["id"], pet["room"])


def worse(house, cfg, pet):
    s = pet["sick"]
    s["level"] = stage_of(pet)
    if s["level"] != SICK[2]:
        s["level"] = SICK[SICK.index(s["level"]) + 1]
        add_event(house, pet, "you feel worse: you are %s" % ({"ill": "sick", "gravely ill": "very sick"}[s["level"]] if not s.get("cause") else s["level"]))
        if s["level"] == SICK[2]:
            if s.get("cause"):
                grave(house, pet)
            else:
                moment(house, "sick", "%s is very sick" % label(pet), pet["id"], pet["room"])
    return s["level"]


def well(house, pet):
    pet["sick"] = None
    for c in ("sickness", "injury", "bad food", "exposure"):
        (pet.get("decline") or {}).pop(c, None)
    add_event(house, pet, "you feel well again")
    moment(house, "well", "%s is well again" % label(pet), pet["id"], pet["room"])


def slowed(house, cfg, pet):
    """Mind.walk asks: does it miss this step? Hurt and limping hobs walk slower; in a scuffle nobody walks off. With
    [deaths] on, an ill hob is slow and a gravely ill one hardly moves."""
    if pet.get("scuffle", -1) > house["tick"]:
        return True
    if deaths(cfg) and stage_of(pet) in SICK[1:]:
        return house["tick"] % (2 if stage_of(pet) == SICK[1] else 4) != 0
    if not on(cfg) or not pet.get("hurt"):
        return False
    S, h = C(cfg)["hurt"]["slow"], pet["hurt"]
    n = S.get(h.get("level")) or (S["limp"] if h.get("lasting") == "limp" else 0)
    return bool(n) and house["tick"] % n == 0


def feel(pet):
    """Its body in words, for a packet."""
    out, h, s = [], pet.get("hurt") or {}, pet.get("sick") or {}
    if h.get("level"):
        out.append({"bruised": "you are bruised and sore", "hurt": "you are hurt, and it aches to move", "badly hurt": "you are badly hurt and can barely move"}[h["level"]])
    if h.get("lasting") == "limp":
        out.append("you walk with a limp")
    if stage_of(pet):
        out.append((FEEL if s.get("cause") else OLD_FEEL)[stage_of(pet)])
    return out


def healer(house, cfg, pet):
    """The best carer awake in the room with it: (the hob, how much it helps 0..1), or (None, 0)."""
    from . import character
    best, care = None, 0.0
    for p in house["pets"].values():
        if p is pet or p["room"] != pet["room"] or not alive(p) or p["sleep"] or p["stage"] in conflict.LITTLE or (p.get("hurt") or {}).get("level") == "badly hurt":
            continue
        c = memories.skill(p, "healing") / 10 + max(0.0, character.trait(p, "kind")) * 0.5
        if c > care:
            best, care = p, min(1.0, c)
    return best, care


def nursed(house, cfg, pet, by):
    """Once a world day for each pair: remembered, liked for it, and the healer gets a little better at it."""
    if deaths(cfg) and (pet.get("hurt") or {}).get("level"):
        pet["hurt"]["tended"] = house["tick"]   # (a hurt with someone by it is not "untended": §2.3)
    seen = pet.setdefault("nursed_by", {})
    if seen.get(by["id"]) == house["clock"]["day"]:
        return
    seen[by["id"]] = house["clock"]["day"]
    memories.practise(house, cfg, by, "healing")
    what = (pet.get("hurt") or {}).get("level") or stage_of(pet) or "poorly"
    opinions.move(house, cfg, pet, by["id"], "nursed_me", "%s looked after me when I was %s" % (label(by), what))
    memories.add(house, cfg, pet, "%s looked after me when I was %s" % (label(by), what), 3, about=[by["id"]], kind="care")
    add_event(house, by, "you looked after %s" % label(pet))


# ---- §2.2 tending, for the planner's nurse, the visitor's tend and a remedy ----

def need_of(house, p):
    """How much it wants tending today, 0..1 (0 when it has been tended today, or is well)."""
    day, s, h, n = house["clock"]["day"], p.get("sick") or {}, p.get("hurt") or {}, 0.0
    if stage_of(p) and s.get("tended_day") != day:
        n = (SICK.index(stage_of(p)) + 1) / 3
    if h.get("level") in HURT[1:] and h.get("tended_day") != day:
        n = max(n, 0.8 if h["level"] == "badly hurt" else 0.4)
    return n


def patients(house, cfg, pet):
    """[(a sick or hurt hob here, how much it needs tending 0..1)], the neediest first, for a grown hob's `nurse`
    (body.targets; the planner weighs them by kind and bond: nurse_pull). Nothing while [deaths] is off."""
    if not deaths(cfg) or pet["stage"] not in ("adult", "elder"):
        return []
    return sorted(((p, need_of(house, p)) for p in here(house, pet) if need_of(house, p)), key=lambda x: (-x[1], x[0]["id"]))


def tend(house, cfg, pet, by, how="nurse"):
    """A day's tending (§2.2, §9.4): `by` a hob, or "visitor"; `how` "nurse", "tend" (the visitor) or "remedy" (back
    two stages). Its sickness goes back a stage (well, from unwell) and its hurt counts as tended; once a world day.
    Returns its sickness after (a SICK level or "well"), or None if there was nothing to tend today."""
    if not on(cfg) or not alive(pet):
        return None
    day, t, did = house["clock"]["day"], house["tick"], False
    h = pet.get("hurt") or {}
    if h.get("level") and h.get("tended_day") != day:
        h.update(tended=t, tended_day=day)
        did = True
    lv = stage_of(pet)
    if lv and (pet["sick"].get("tended_day") != day or how == REMEDY):
        pet["sick"].update(tended=t, tended_day=day)
        i = SICK.index(lv) - (2 if how == REMEDY else 1)
        if i < 0:
            well(house, pet)
        else:
            pet["sick"]["level"] = SICK[i]
            pet["sick"].pop("grave", None)
            add_event(house, pet, "you feel a little better: %s" % ("someone sat with you" if how != REMEDY else "the remedy helped"))
        did = True
    if not did:
        return None
    who = by["id"] if isinstance(by, dict) else str(by)
    K.note(house, "nursed", pet=pet["id"], by=who, how=how)
    if isinstance(by, dict) and by is not pet:
        nursed(house, cfg, pet, by)
    elif who == "visitor":
        opinions.move(house, cfg, pet, "visitor", "nursed_me", "the visitor looked after me when I was poorly")
        memories.add(house, cfg, pet, "the visitor looked after me when I was poorly", 3, about=["visitor"], kind="care")
    return stage_of(pet) or "well"


def nurse_pull(house, cfg, pet, do, t):
    """(planner.adjust) What nursing adds: to `nurse` with a patient, by its need, the nurse's kindness and their bond,
    and more for a little one (§2.2, §1.3 "raise"); to a door toward a room with one gravely in need."""
    if not deaths(cfg) or pet["stage"] not in ("adult", "elder"):
        return 0.0
    from . import bonds, character
    W, P = cfg["deaths"], house["pets"]
    if do == "nurse" and t.get("who") in P:
        p = P[t["who"]]
        dear = opinions.kin(house, pet, p) or bonds.kind(house, pet["id"], p["id"]) in ("close", "friend")
        return need_of(house, p) * W["nurse"] * (1 + 0.5 * character.trait(pet, "kind")) * (W["raise"] if p["stage"] in conflict.LITTLE else 1.0) + (1.0 if dear else 0.0)
    if do == "go" and t.get("what"):
        from . import body
        rooms = {p["room"] for p in P.values() if alive(p) and p is not pet and need_of(house, p) >= 0.6} - {pet["room"]}
        if rooms and t["what"] == body.way_to(house, pet, rooms):
            return 0.5 * W["nurse"]
    return 0.0


def nursing(house, cfg):
    """Each tick: a hob at its `nurse` beside its patient tends it (a remedy it carries goes to it); a sick hob that
    has a remedy in its paws takes it."""
    from .body import state
    P = house["pets"]
    for p in list(P.values()):
        if not alive(p):
            continue
        now = state(p)["now"] if "body" in p else None
        q = P.get((now or {}).get("who") or "")
        if now and now["name"] == "nurse" and now.get("began") is not None and q and q["room"] == p["room"] and alive(q) and need_of(house, q):
            rem = REMEDY in p["carrying"] and stage_of(q)
            if rem:
                p["carrying"].remove(REMEDY)
            tend(house, cfg, q, p, REMEDY if rem else "nurse")
        if stage_of(p) and REMEDY in p["carrying"]:
            p["carrying"].remove(REMEDY)
            tend(house, cfg, p, p, REMEDY)


# ---- §2.4 bad food ----

def poisoned(house, cfg, pet, what, level="ill"):
    """It ate something bad (a poisonous catch, the cellar's broth, spoiled food): ill at once (spoiled food: unwell).
    It and whoever saw it come to believe so (contracts.believe_later; B's hooks make the belief)."""
    if not deaths(cfg) or not alive(pet):
        return None
    lv = sicken(house, cfg, pet, "it ate the %s" % what, level=level, cause="bad food", what=what)
    moment(house, "poisoned", "%s was taken ill after eating the %s" % (label(pet), what), pet["id"], pet["room"])
    for p in [pet] + here(house, pet, awake=True):
        K.believe_later(p, "the %s makes you ill" % what if p is pet else "the %s made %s ill" % (what, label(pet)),
                        {"name": "avoid_thing", "arg": what}, "lived" if p is pet else "seen", truth=True)
    return lv


def keeps(cfg, room, name):
    """Does the thing it is put by on keep food (a jar, a box, a basket, anything made to keep)?"""
    from . import cook, things
    o = room["objects"].get(name or "") or {}
    k = things.kind_of(o) if "made" in o else None
    return bool(k) and (k in cook.KEEPERS or cfg["kinds"].get(k, {}).get("use") == "keeper")


def spoil(house, cfg, room=None, early=False):
    """Food put by on a shelf (not in something that keeps it) spoils after `spoil_days`; `early`: now (the director's
    sickness in the food, §8.2). A spoiled bit is marked (`spoiled`, for the page) and sickens whoever eats what is cooked
    from it (cook.py). Returns how many spoiled."""
    if not deaths(cfg):
        return 0
    t, F, n = house["tick"], cfg["seasons"]["food"]["bits"], 0
    from . import items
    v5 = K.on5(cfg, "items")   # (with items on, what keeps food is a cool thing, not any keeper: §1.4)
    for r in [room] if room else [x for x in house["rooms"].values() if x.get("type")]:
        for s in r["spots"]:
            if s["bit"] in F and s.get("on") and not s.get("spoiled") and (v5 or not keeps(cfg, r, s["on"])):
                put = s.setdefault("put", t)
                slow = 2 if v5 and items.stored_in(house, cfg, r, s, "cool") else 1   # SPEC-v5.0 §1.4: in a cool thing (a jar) food spoils at half speed
                if early or t - put >= cfg["deaths"]["spoil_days"] * cfg["ticks_per_day"] * slow:
                    s["spoiled"] = t
                    n += 1
                    moment(house, "spoiled", "the %s put by on the %s in %s has spoiled" % (s["bit"], s["on"], r["name"]), None, r["id"])
    return n


def cold_snap(house, cfg, days):
    """§8.2 the season's cold, early: for `days` world days nights are as winter's (a cold night catches, a night out
    of doors is exposure) and the cold rooms are colder (season.cold)."""
    house["cold_snap"] = house["tick"] + round(days * cfg["ticks_per_day"])
    moment(house, "cold", "a cold snap has come early: the nights are bitter", None, None)


def install(cfg):
    """With [deaths] on, what the data keeps aside for it (so that off is v4.0.6's): the remedy's recipe and material
    (crafting.toml [remedy]) and the poisonous dishes (dishes.toml `poison = true`, cook.load sets them aside)."""
    if cfg.get("deaths_installed"):
        return
    cfg["deaths_installed"] = True
    R = cfg["craft"].get("remedy")
    if R:
        like = cfg["house"]["bits"].get(R.get("like"), {})
        cfg["house"]["bits"].setdefault(R["gives"], {"can": list(R["can"]), "looks": like.get("looks", {"shape": "blob", "color": "green"}), "late": "crafting", "made": True})
        cfg["craft"]["rules"].setdefault((R["bit"], R["how"]), {k: R[k] for k in ("bit", "how", "gives", "says", "hint") if k in R})
    for name, d in cfg["cook"].get("poisoned", {}).items():
        cfg["cook"]["dish"][name] = d
        for b in d["needs"]:
            cfg["craft"]["rules"].setdefault((b, "cook"), {"bit": b, "how": "cook", "gives": name, "says": d["says"], "dish": True})


def tick(house, cfg):
    if not on(cfg):
        for p in house["pets"].values():   # off: none, and what there was goes at once
            if p.get("hurt") or p.get("sick"):
                p["hurt"] = p["sick"] = None
        return
    D = deaths(cfg)
    if D:
        install(cfg)
    H, t = C(cfg)["hurt"], house["tick"]
    for p in list(house["pets"].values()):
        if not alive(p):
            continue
        if p.get("sick") and p["sick"].get("level") in K.OLD_SICK:
            p["sick"]["level"] = K.OLD_SICK[p["sick"]["level"]]   # (v4.0.6's names, read as the new)
        h = p.get("hurt")
        if h and h.get("level"):
            for n in ("energy", "comfort"):
                p["needs"][n] = max(0.0, p["needs"][n] - H["drain"][h["level"]] * cfg["dt"])
            by, care = healer(house, cfg, p)
            h["left"] -= (H["rest"] if p["sleep"] else 1.0) * (1 + H["care"] * care)
            if by and care > 0.1:
                nursed(house, cfg, p, by)
            if h["left"] <= 0:
                heal(house, cfg, p)
        if p.get("sick"):
            p["needs"]["energy"] = max(0.0, p["needs"]["energy"] - C(cfg)["sick"]["drain"] * cfg["dt"])
    accidents(house, cfg)
    if D:
        nursing(house, cfg)
        c = house["clock"]
        if c["hour"] >= NIGHT_HOUR and c["hour"] < NIGHT_HOUR + 3 and house.get("health_day") != c["day"]:
            daily(house, cfg)
    if t % max(1, round(cfg["ticks_per_hour"])) == 0:
        if D:
            spoil(house, cfg)
        else:
            sickness(house, cfg)


def accidents(house, cfg):
    """Injury besides fights: a burn at the forge (machines.start's record, the tick after; the hasty likelier), and,
    once a world hour, a fall for a hasty hob or an elder on the move."""
    from . import character, items, world
    H, t, P = C(cfg)["hurt"], house["tick"], house["pets"]
    for at, key, pid, bit, _ in (house.get("machine_runs") or [])[-3:]:
        p = P.get(pid)
        if at == t - 1 and key == "forge" and alive(p) and rnd(house, "forge", pid, at).random() < H["forge"] * (1.5 if character.trait(p, "patient") <= -0.2 else 1.0):
            hurt(house, cfg, p, "bruised", "a burn at the forge")
            moment(house, "hurt", "%s burned a paw at the forge" % label(p), pid, p["room"])
    if t % max(1, round(cfg["ticks_per_hour"])):
        return
    for p in list(P.values()):
        if alive(p) and not p["sleep"] and world.moving(p) and (p["stage"] == "elder" or character.trait(p, "patient") <= -0.2):
            if K.on5(cfg, "items") and house["clock"]["phase"] == "night" and items.strength(house, cfg, p["room"], "light", True):   # SPEC-v5.0 §1.4: no falls in a lit room at night
                continue
            r = rnd(house, "fall", p["id"], t)
            if r.random() < H["fall"]:
                level = hurt(house, cfg, p, "hurt" if p["stage"] == "elder" and r.random() < 0.3 else "bruised", "a fall")
                moment(house, "hurt", "%s took a fall and is %s" % (label(p), level), p["id"], p["room"])


def heal(house, cfg, p):
    h, H = p["hurt"], C(cfg)["hurt"]
    i = HURT.index(h["level"])
    if i == 2 and rnd(house, "limp", p["id"], house["tick"]).random() < H["limp"]:
        h["lasting"] = "limp"
        moment(house, "limp", "%s is mending, but will always walk with a limp" % label(p), p["id"], p["room"])
        memories.add(house, cfg, p, "I was badly hurt (%s), and I will always limp from it" % h.get("why", ""), 5, kind="injury")
    if i:
        h.update(level=HURT[i - 1], left=H["heal_days"][HURT[i - 1]] * cfg["ticks_per_day"])
        add_event(house, p, "you are mending: only %s now" % h["level"])
    else:
        add_event(house, p, "your hurts have healed")
        if h.get("lasting"):
            h["level"] = None
        else:
            p["hurt"] = None
    if i == 2 and (p.get("decline") or {}).get("injury") is not None and not (p.get("sick") or {}).get("cause") == "injury":
        p["decline"].pop("injury")   # (no longer badly hurt, and it did not turn to a sickness)


# ---- §2.2-2.6: once a world day, in the small hours (with [deaths] on) ----

COLD_SEASONS = ("autumn", "winter")


def bed(house, pet):
    """The bed (anything cosy) it sleeps by, or None."""
    from .world import dist
    room = house["rooms"][pet["room"]]
    return next((n for n, o in sorted(room["objects"].items()) if o.get("fix", {}).get("cozy") and dist(pet["pos"], o["pos"]) <= 1), None)


def cold_night(house, cfg, pet):
    """A night in a cold room in autumn or winter (or a cold snap) without a bed."""
    from . import outdoors
    cold = set(cfg["house"]["seasons"].get("winter", {}).get("cold_rooms", {})) | {"cellar"}
    season = house["clock"]["season"] in COLD_SEASONS or house.get("cold_snap", -1) > house["tick"]
    room = house["rooms"][pet["room"]]
    return season and (room.get("type") in cold or outdoors.is_out(pet["room"])) and not bed(house, pet)


def warm5(house, cfg, pet):
    """SPEC-v5.0 §1.4: a sleeper under cover, or in a room with heat, catches a cold night half as often."""
    from . import items
    if not K.on5(cfg, "items"):
        return 1.0
    return 0.5 if items.covered(house, cfg, pet) > 0 or items.strength(house, cfg, pet["room"], "heat") > 0 else 1.0


def daily(house, cfg):
    """The night's catching and the day's course (§2.2-2.6). Little ones catch things `little_sick` times as easily.
    A hob tended since the last look has already been moved back (tend); one untended moves on with `worsen`'s chance;
    gravely ill since the last look and untended, it dies, unless the house is under the floor (it lingers)."""
    from . import life, outdoors
    W, t, c = cfg["deaths"], house["tick"], house["clock"]
    last = house.get("health_last", t - cfg["ticks_per_day"])
    house["health_day"], house["health_last"] = c["day"], t
    pets = sorted((p for p in house["pets"].values() if alive(p)), key=lambda p: p["id"])
    asleep_sick, moved = {}, set()
    for p in pets:
        if stage_of(p) and p["sleep"]:
            asleep_sick.setdefault((p["room"], bed(house, p)), []).append(p)
    for p in pets:
        r = rnd(house, "catch", p["id"], c["day"])
        little = W["little_sick"] if p["stage"] in conflict.LITTLE else 1.0
        if outdoors.exposed(house, cfg, p) and stage_of(p) != SICK[2]:   # §2.6: unwell by morning, ill after a second night (gravely ill, the course below)
            if stage_of(p):
                worse(house, cfg, p)
            else:
                sicken(house, cfg, p, "a night out in the cold", cause="exposure")
            moved.add(p["id"])
            continue
        if stage_of(p):
            continue
        h, x = p.get("hurt") or {}, r.random()
        shared = [q for q in asleep_sick.get((p["room"], bed(house, p)), []) if q is not p] if p["sleep"] and bed(house, p) else []
        if p["sleep"] and cold_night(house, cfg, p) and x < W["cold_night"] * little * warm5(house, cfg, p):
            sicken(house, cfg, p, "a cold night without a bed")
        elif shared and x < W["catch"] * little:
            sicken(house, cfg, p, "caught it from %s" % label(shared[0]))
        elif h.get("level") == "badly hurt" and t - h["since"] >= cfg["ticks_per_day"] and h.get("tended", -1) < h["since"] and x < W["untended_hurt"] * little:
            sicken(house, cfg, p, "a bad hurt left untended", cause="injury")
    for p in pets:
        s = p.get("sick")
        if not stage_of(p) or p["id"] in moved or s["since"] >= t or s.get("tended", -10 ** 9) >= last:
            continue
        if not s.get("cause"):
            s["cause"] = "sickness"   # (one caught before [deaths] was on)
        if stage_of(p) == SICK[2] and s.get("grave", t) <= last:
            if life.floor(house, cfg):
                continue   # §2: under the floor a sickness lingers
            p["death_due"] = s["cause"]
            p["death_words"] = WORDS.get(s["cause"], WORDS["sickness"]).format(what=s.get("what") or "thing")
        elif rnd(house, "course", p["id"], c["day"]).random() < W["worsen"]:
            worse(house, cfg, p)


# the full words a death of sickness takes (life.die writes them on the stone)
WORDS = {"sickness": "died of a sickness, untended", "injury": "died of a hurt that was never tended", "bad food": "died of the {what} it ate",
         "exposure": "died of the cold, untended"}


def sickness(house, cfg):
    """(v4.0.6, [deaths] off) Every world hour: who falls ill (cold, stale food, catching it), and who gets better or worse."""
    from . import outdoors
    S, t, c = C(cfg)["sick"], house["tick"], house["clock"]
    pets = [p for p in house["pets"].values() if alive(p)]
    for p in pets:
        if p.get("sick"):
            continue
        r = rnd(house, "sick", p["id"], t)
        bitter = c["phase"] == "night" or house["weather"] in ("snow", "storm")
        if outdoors.unsheltered(house, cfg, p) and bitter and r.random() < S["cold"] * (S["cold_low"] if p["needs"]["comfort"] < 15 else 1.0):
            sicken(house, cfg, p, "the cold")
            continue
        pots = [o["pot"] for o in house["rooms"][p["room"]]["objects"].values() if o.get("pot")]
        stale = any(t - pot.get("ate", {}).get(p["id"], -10**9) <= cfg["ticks_per_hour"] and pot.get("keeps", 10**12) - pot["ate"][p["id"]] <= S["spoiled_hours"] * cfg["ticks_per_hour"] for pot in pots)
        if stale and r.random() < S["spoiled"]:
            sicken(house, cfg, p, "food on the turn")
            continue
        ill = [q for q in pets if q.get("sick") and q is not p and q["room"] == p["room"] and q["sick"]["since"] != t and not p["sleep"]]
        if ill and r.random() < S["catch"] * sum(SICK.index(stage_of(q)) + 1 for q in ill):
            sicken(house, cfg, p, "caught it from %s" % label(ill[0]))
    for p in pets:
        s = p.get("sick")
        if not s or s["since"] == t:
            continue
        r = rnd(house, "course", p["id"], t)
        by, care = healer(house, cfg, p)
        out = outdoors.unsheltered(house, cfg, p)   # (SPEC-v5.3 §3: under its own shelter it is not out in the cold)
        neglect = (p["needs"]["energy"] < 20 and p["needs"]["comfort"] < 25) or (out and c["phase"] == "night") or p["needs"].get("hunger", 100) < 10   # (A: starving makes it sick)
        score = 1.0 + (1.0 if p["sleep"] else 0.0) + (0.0 if out else 0.5) + 2 * care - (2.0 if neglect else 0.0)
        if by and care > 0.1:
            nursed(house, cfg, p, by)
        if score > 0 and r.random() < S["better"] * score:
            i = SICK.index(stage_of(p))
            if i:
                s["level"] = SICK[i - 1]
                add_event(house, p, "you feel a little better")
            else:
                p["sick"] = None
                add_event(house, p, "you feel well again")
                moment(house, "well", "%s is well again" % label(p), p["id"], p["room"])
        elif neglect and r.random() < S["worse"]:
            if stage_of(p) == SICK[2] and r.random() < S["die"] / S["worse"]:
                p["death_due"] = "sickness"   # life.due hands it to Engine.kill this tick
            else:
                worse(house, cfg, p)
