"""Life and death, eggs and inheritance (SPEC-v3 §4, §5). A pet hatches, grows by what it has lived and made,
grows old, and dies; before that it may lay eggs, and what it hands on is a body, a temperament, a message,
and a couple of things."""
import re

from . import craft, firsts, genes, names, order, resting, things
from . import bonds, character, needs   # SPEC-v4.0
from . import contracts as K   # SPEC-v4.2
from .feel import level
from .world import (GENES, STAGES, days as world_days, add_event, alive, arrived, family, free_tile, hours, label, moment, new_pet, rnd, ticks)

GROWS = {"hatchling": "child", "child": "youngling", "youngling": "adult"}
UNLOCKS = {
    "hatchling": ["observe", "look", "move", "go", "speak", "rest", "use", "gather", "drop", "make", "unmake", "give", "show",
                  "follow", "nuzzle", "accept", "take", "chase", "write_belief", "revise_belief"],
    # SPEC-v3.4 §3: a child may try what can be done to a bit, a youngling mend, a grown pet carry the book to another room
    "child": ["arrange", "process"], "youngling": ["combine", "paint", "mend"], "adult": ["teach", "lay_egg", "carry"], "elder": ["tell", "bequeath"],
}
# SPEC-v3.1: what a discovery makes possible, the stage it needs, and the discovery it waits for. These are never
# announced with a stage: a pet meets them in the world (a stick of chalk, a tune that stays with it, a creature that
# no longer runs).
LATE = {"scrub": ("hatchling", "writing"), "write": ("child", "writing"), "sing": ("hatchling", "songs"), "teach_song": ("hatchling", "songs"),
        "compose": ("youngling", "songs"), "call": ("hatchling", "taming"), "name": ("hatchling", "taming"), "ask_book": ("child", "book")}


def actions_of(stage):
    """Everything a pet of this stage can ever do; what it can do right now is narrower (actions.allowed)."""
    out = []
    for s in STAGES[1:STAGES.index(stage) + 1] if stage in STAGES else []:
        out += UNLOCKS[s]
    return out


def unlocked(house, stage):
    """What a pet of this stage can ever do in this house as it is now: its stage's actions, and those of the
    discoveries that have arrived (SPEC-v3.1 §1)."""
    if stage not in STAGES[1:]:
        return []
    return actions_of(stage) + [a for a, (at, what) in LATE.items() if STAGES.index(stage) >= STAGES.index(at) and arrived(house, what)]


def full(house, cfg, pet):
    """Is there no room for another egg of this pet's? SPEC-v3.6c §2: seven in the house, four of a family; and while
    the model is too busy to think for more, none. (SPEC-v4.0.5 §9.4: the one cap; v3's four and v3.1's five are gone.)"""
    Pop = cfg["population"]
    return len(alive(house)) >= Pop["most"] or sum(family(p) == family(pet) for p in alive(house)) >= Pop["per_family"] or model_busy(house, cfg) > Pop["guard"]


def model_busy(house, cfg):
    """The share of the last world hour the model spent thinking for this house (tick.Engine.call keeps the record)."""
    span = cfg["ticks_per_hour"]
    real = span * cfg["clock"]["tick_seconds"] * cfg.get("pace", 1)
    return sum(s for t, s in house.get("busy", []) if t > house["tick"] - span) / real if real else 0.0


def founder(house, cfg):
    """SPEC-v3.6c §2: the house fills over a day or two. Once a world hour: when it has had room for more for
    `found_hours` and no egg has been laid or found in that time, and the model has time for another, an egg turns up:
    for a family with one hob left before a new family's (a new family only while there are fewer than `families`;
    else the smallest family's). Eggs laid as ever come first; this is for when nobody can lay."""
    Pop = cfg.get("population", {})
    if not Pop.get("on") or house["tick"] % hours(cfg, 1) or not house.get("lineage"):
        return None
    living = alive(house)
    if len(living) >= Pop["most"] or any(p["stage"] == "egg" for p in living) or model_busy(house, cfg) > Pop["guard"]:
        house["room_since"] = None
        return None
    since = house.get("room_since") or house["tick"]
    house["room_since"] = since
    last = max([p["laid"] for p in house["pets"].values() if p.get("laid") is not None] + [since])
    # (19 October 2026: laying first: no egg turns up while a grown hob has an egg in it; on live every new hob for ten
    # days was found. 20 October 2026: only for `hold_days` of room with no egg, and never while one hob is
    # alone: on live nobody laid for twelve days and the hold kept the house from any egg until one hob was left)
    if len(living) > 1 and house["tick"] - last < hours(cfg, 24 * Pop["hold_days"]) and any(p["stage"] in ("adult", "elder") and p["eggs"] < fertility(p) for p in living):
        return None
    if house["tick"] - last < hours(cfg, Pop["found_hours"]):
        return None
    fams = {}
    for p in living:
        fams.setdefault(family(p), []).append(p)
    lone = sorted((f for f, ps in fams.items() if len(ps) == 1 and ps[0]["stage"] not in ("egg", "dead")), key=lambda f: f)
    if lone:
        fam, kin = lone[0], fams[lone[0]][0]
    elif len(fams) < Pop["families"]:
        fam, kin = max(list(fams) + [max((family(p) for p in house["pets"].values()), default=1)]) + 1, None
    else:
        fam = min(fams, key=lambda f: (len(fams[f]), f))
        kin = min(fams[fam], key=lambda p: (p["stage"] not in ("adult", "elder"), p["id"]))   # (a grown one when there is one)
        if len(fams[fam]) >= Pop["per_family"]:
            return None
    from . import genome as G
    rooms = [r for r in house["rooms"].values() if r.get("type") and r.get("type") not in ("yard", "meadow")]
    room = house["rooms"].get(kin["room"]) if kin and house["rooms"].get(kin["room"], {}).get("type") not in ("yard", "meadow") else next((r for r in rooms if r["type"] == "nursery"), rooms[0])
    rng = rnd(house, "founder egg", house["tick"])
    body = genes.child(kin["genome"], rng, genes.line(house, kin))[0] if kin else genes.apart(house, dict(G.START, hue=rng.randrange(360), pattern=rng.choice(G.PATTERNS),
                                                                                                        **{k: round(rng.uniform(*v), 2) for k, v in G.RANGES.items()}), rng)
    # (19 October 2026: an egg of a family is that family's child: kin is its one parent, so its generation, the
    # family's words and recipes come down to it as a laid egg's do; it was gen 1 and heard "no one left you any words".
    # A little one is never a parent: with only a hatchling or a child for kin, the egg is its sibling, its parent's
    # child, or with no parent of its own (a family's first) of its generation and nobody's.)
    par = (kin if kin["stage"] in ("adult", "elder") else house["pets"].get(kin["parent"] or "")) if kin else None
    told = [{"by": par["id"], "who": par["word"], "kind": "message", "text": par["message"][-1]["text"], "tick": house["tick"]}] if par and par["message"] else None
    egg = new_pet(house, cfg, room["id"], free_tile(house, cfg, room, kin["pos"] if kin else [cfg["W"] // 2, cfg["H"] // 2]), genome=body,
                  temper=temper_of(kin["temper"], rng, cfg) if kin else None, family=fam, parent=par and par["id"], told=told)
    egg["founder"] = True
    if kin:
        egg["kin"], egg["gen"] = kin["id"], par["gen"] + 1 if par else kin["gen"]
    if par:
        firsts.laid(house, cfg, par, egg)
    names.foundling(house, cfg, egg)   # (it is named as a laid egg is: 18 October 2026)
    house["room_since"] = None
    for p in living:
        if p["stage"] not in ("egg", "dead") and p["room"] == room["id"] and not p["sleep"]:
            add_event(house, p, "there is an egg here that nobody laid" + (": it looks like one of %s's family" % label(kin) if kin else ""))
            p["news"].append("event")
    moment(house, "egg", "an egg has turned up in %s%s" % (room["name"], ", one of %s's family" % label(kin) if kin else ", the first of a new family"), egg["id"], room["id"])
    return egg


def numbers(cfg):
    """([life], [growth]) as a life runs by: with [lives] on (SPEC-v4.2 §1.1), its span, stages and adult days in their
    place (the base and the profiles' [life] and [growth] stand for [lives] off)."""
    if not K.on(cfg, "lives"):
        return cfg["life"], cfg["growth"]
    V = cfg["lives"]
    return dict(cfg["life"], lifespan_days=V["lifespan_days"], adult_days=V["adult_days"]), dict(cfg["growth"], **{s: V[s] for s in ("child", "youngling", "adult")})


def days(house, cfg, pet):
    """World days since it hatched."""
    return world_days(cfg, pet["born"], house["tick"]) if pet["born"] is not None else 0.0


def wellbeing(pet, cfg=None):
    """The mean of all its needs over its life; each useful thing it made counts for a little more (§4.1)."""
    G = cfg["growth"] if cfg else {"useful_wellbeing": 0, "useful_max": 0}
    return (pet["well"][0] / pet["well"][1] if pet["well"][1] else 50.0) + G["useful_wellbeing"] * min(len(pet["useful"]), G["useful_max"])


def span(cfg, pet):
    """How many days this life will run (§4.1): a base, moved up to 30% by how well it has lived, a little by
    how hardy it is, and cut by neglect. Never shown to the pet."""
    L = numbers(cfg)[0]
    lived = max(-1.0, min(1.0, (wellbeing(pet, cfg) - 50) / L["wellbeing_span"]))
    return L["lifespan_days"] * (1 + L["wellbeing_share"] * lived) * (1 + L["hardy_share"] * (pet["temper"]["hardy"] - 0.5)) - pet["lost_days"] + pet.get("span_add", 0.0)   # (SPEC-v4.2 §1.2, §1.4: grief, the migration's re-draw)


def fertility(pet):
    return 1 + round(pet["temper"]["fertile"] * 2)   # 1 to 3 eggs in a life


def body_feels(house, cfg, pet):
    """What it can feel of its own body: age, weakness, the pull to lay an egg (§4.1, §5.1)."""
    L, out, stage = cfg["life"], [], pet["stage"]
    if stage in ("egg", "dead"):
        return out
    left = span(cfg, pet) - days(house, cfg, pet)
    if left <= 1:
        out.append("you feel very old and tired")
    elif pet.get("old"):   # SPEC-v4.2 §2.1: the last days of a life
        out.append("you are old and slow now, and sleep more than you did")
    elif stage == "elder":
        out.append("your body feels slower than it used to")
    if stage == "elder" and left <= 3 and pet["useful"] and any(house["pets"].get(c, {}).get("stage", "dead") != "dead" for c in pet["children"]) \
            and not any((o["made"].get("heirloom") or {}).get("from") == pet["id"] for r in house["rooms"].values() if r["type"] for o in things.made(r).values()):
        out.append("you find yourself thinking about which of your things your children should have")   # §5.3: bequeath
    if stage == "elder":   # the old feel there are things to hand on while they can (§7.2: tell)
        young = [p for p in house["pets"].values() if p["room"] == pet["room"] and p["id"] != pet["id"] and p["stage"] not in ("egg", "dead", "elder")
                 and not p["sleep"]]
        if young and (left <= 3 or not any(t["by"] == pet["id"] for t in young[0]["told"])):
            out.append("there are things you know that %s does not; you could tell them while you can" % label(young[0]))
    if pet["weak"]:
        out.append("you feel weak")
    if stage in ("adult", "elder") and not pet["useful"]:
        out.append("you haven't made anything that's really yours")
    if stage in ("adult", "elder") and pet["eggs"] < fertility(pet):
        pull = world_days(cfg, pet["stage_at"]["adult"], house["tick"]) >= L["egg_pull_days"] and pet["eggs"] == 0
        if full(house, cfg, pet):
            out.append("the house is full")
        elif pull or left <= 2:
            out.append("you feel ready to lay an egg")
    return out


# ---- lineages and eggs ----

def found(house, cfg, told=None, body=None):
    """Start a lineage: one egg in the nursery. A new lineage starts in the same house (§4.2)."""
    house["n"]["lineage"] += 1
    house["lineage"] = {"id": house["n"]["lineage"], "started": house["tick"], "ended": None, "founder": None, "drift": None,
                        "drift_at": house["tick"] + round(cfg["house"]["events"]["drift_after_days"] * cfg["ticks_per_day"])}
    room = house["rooms"][house["start"]]
    rng = rnd(house, "founder", house["n"]["lineage"])
    pet = new_pet(house, cfg, room["id"], free_tile(house, cfg, room, [cfg["W"] // 2 - 1, cfg["H"] // 2 - 1]),
                  genome=genes.child(body, rng)[0] if body else None, told=told)
    house["lineage"]["founder"] = pet["id"]
    moment(house, "egg", "an egg is lying in the nursery", pet["id"], room["id"])
    return pet


def temper_of(parent, rng, cfg, other=None):
    """A child's temperament: the parent's, each gene nudged a little, and now and then one moved a lot (§5.4).
    SPEC-v4.0 §6.3: with two parents, each gene is first taken from one or the other."""
    L = cfg["life"]
    if other:
        parent = {g: (parent if rng.random() < 0.5 else other).get(g, 0.5) for g in GENES}
    nudge = lambda g: round(min(1.0, max(0.0, parent.get(g, 0.5) + rng.gauss(0, L["temper_sigma"]))), 2)
    t, jump = {g: nudge(g) for g in GENES[:9]}, None
    if rng.random() < L["temper_jump"]:
        from . import character   # SPEC-v4.0 §1: with the traits on, the jump can land on a new axis too
        g = rng.choice(GENES if character.on(cfg) else GENES[:9])
        jump = (g, rng.choice([-1, 1]) * rng.uniform(0.2, 0.35))
    t.update({g: nudge(g) for g in GENES[9:]})   # SPEC-v4.0 §1: the new genes are drawn after, so v3.6c's draws stay as they were
    from . import sheet
    if sheet.on(cfg):   # (24 November 2026) its character is its own, not its parent's: one lineage had bred six of one mind. Its body's genes are still handed on
        t.update({g: round(rng.uniform(0.1, 0.9), 2) for g in GENES if g not in ("fertile", "hardy")})
        jump = None
    if jump:
        t[jump[0]] = round(min(1.0, max(0.0, t[jump[0]] + jump[1])), 2)
    return t


def can_lay(house, cfg, pet):
    """None if it can lay an egg now, else what stops it, as it would feel it."""
    if pet["eggs"] >= fertility(pet):
        return "there are no more eggs in you"
    if full(house, cfg, pet):
        return "the house is full"
    from . import season
    if level(pet, "energy") > 1 + season.rule(house, cfg, "eggs", 0):   # (SPEC-v3.5 §5: in spring an egg comes a little easier)
        return "you are too tired to lay an egg"
    return None


def lay_egg(house, cfg, pet, a, clean):
    room, rng = house["rooms"][pet["room"]], rnd(house, "egg", pet["id"], pet["eggs"])
    text, name = sentences(last_sentence(clean(a["message"], 640), 600), 4), clean(a.get("name") or "", 16).strip() or None
    pet["message"].append({"tick": house["tick"], "text": text})
    name, byname, told = names.given(house, cfg, pet, name)   # SPEC-v3.5.8 §2: a real name; a phrase is its by-name
    other = bonds.parents(house, cfg, pet)   # SPEC-v4.0 §6.3: an egg of a close bond has two parents, and takes from both
    body, new = genes.child(bonds.blend(pet["genome"], other["genome"], rng) if other else pet["genome"], rng,
                            genes.line(house, pet) + ([other["genome"]] + genes.line(house, other) if other else []))   # SPEC-v3.5 §2: its parent's body, a slot or two moved; rarely something new
    egg = new_pet(house, cfg, room["id"], free_tile(house, cfg, room, pet["pos"]), genome=body,
                  temper=temper_of(pet["temper"], rng, cfg, other and other["temper"]), parent=pet["id"], name=name,
                  told=[{"by": pet["id"], "who": pet["word"], "kind": "message", "text": text, "tick": house["tick"]}])
    if other:
        egg["parents"] = [pet["id"], other["id"]]
        other["children"].append(egg["id"])
    firsts.laid(house, cfg, pet, egg)   # SPEC-v3.5.4 §9: it hears of an ambition its parent reached
    if new:
        egg["mutation"] = new   # (the family tree marks the branch; it is a moment when it hatches)
    if byname:
        egg["byname"] = byname
    pet["eggs"] += 1
    moment(house, "egg", "%s laid an egg%s%s" % (label(pet), " with " + label(other) if other else "", " and named it " + name + (", called " + byname if byname else "") if name else ""), pet["id"], room["id"])
    return "you laid an egg%s and told it what you want it to know%s" % (" and named it " + name if name else "", told), {"energy": -cfg["life"]["egg_energy"]}, "lay egg"


# SPEC-v3.5.4 §4: a project is something to do or find out, and finish. "Wait with the seed", "do not make",
# "attend to the hour", "be like moss" are ways to be, not projects.
NOT_DOING = re.compile(r"^\W*(do not|don't|never|wait|attend|let |be |stay|rest\b|lie |hold |keep still|listen|watch the|sit |notice|accept|allow|refrain|avoid)"
                       r"|\b(do not|don't|not to|rather than|instead of) (make|making|plant|name|unmake|shape)", re.I)


def not_doing(text):
    return bool(NOT_DOING.search(text or ""))


def sentences(text, most):
    """At most `most` sentences of it (SPEC-v3.5.4 §4: a message is a few sentences, at most four)."""
    parts = re.findall(r"[^.!?]+[.!?]+[\"'”’)]*\s*|[^.!?]+$", text.strip())
    return "".join(parts[:most]).strip() or text


def last_sentence(text, limit):
    """Words cut at a limit end on the last whole sentence inside it, or failing that the last whole word,
    so nothing is kept or handed down half said."""
    if len(text) <= limit:
        return text
    cut = max(text[:limit].rfind(c) for c in ".!?") + 1
    return text[:cut] if cut > limit * 0.4 else text[:limit].rsplit(" ", 1)[0].rstrip(",;:—- ") + "…"


def hatch(house, cfg, pet):
    pet["stage"], pet["born"], pet["season"] = "hatchling", house["tick"], house["clock"]["season"]
    pet["stage_at"]["hatchling"], pet["bodies"]["hatchling"] = house["tick"], dict(pet["genome"])
    pet["rooms"][pet["room"]] = house["tick"]
    pet["news"].append("hatched")
    if pet.get("founder"):   # (an egg that turned up by itself hatches with a name, as a laid egg does)
        names.foundling(house, cfg, pet)
    add_event(house, pet, "you hatched; you can do things now: " + ", ".join(actions_of("hatchling")))
    kin = house["pets"].get(pet.get("kin") or "") if pet.get("founder") else None   # (19 October 2026: a founder egg of a family)
    if kin:
        add_event(house, pet, "you came to %s's family as an egg nobody laid" % label(kin))
    elif not pet["told"]:
        add_event(house, pet, "no one left you any words")   # a foundling starts with nothing inherited (SPEC-v3.1 §7.1)
    for parent in [house["pets"].get(p) for p in pet.get("parents") or [pet["parent"]]]:   # SPEC-v4.0 §6.3: both parents hear
        if parent and parent["stage"] != "dead":
            add_event(house, parent, ("the egg of your family that nobody laid has hatched%s" if kin else "the egg you laid has hatched%s") % (": " + pet["name"] if pet["name"] else ""))
            parent["news"].append("event")
    moment(house, "hatched", "%s hatched" % (pet["name"] or "an egg"), pet["id"], pet["room"])
    genes.hatched(house, pet)
    craft.inherit(house, cfg, pet)   # SPEC-v3.4 §3.3: it starts out knowing some of what its parent knew
    firsts.hatched(house, cfg, pet)   # SPEC-v3.5.4 §7, §9: born knowing its line's bests, and with an ambition
    if character.on(cfg):
        character.give_character(house, cfg, pet)   # SPEC-v4.0 §1.2: quirks from its traits and its parents', two values, a mood
    # SPEC-v4.2 C: a drive, a flaw and a voice card at hatching (§6.1-6.4; nothing with [drives] off)
    from . import drives
    drives.draw(house, cfg, pet)
    # SPEC-v4.2 C: end


def earned(house, cfg, pet):
    """The stage it has earned by this morning, or None (§4.1 as amended): stages are paced by days lived.
    v2 gated them on useful things, and one of those takes a pet hours whatever the clock says."""
    stage, age = pet["stage"], days(house, cfg, pet)
    L, G = numbers(cfg)
    nxt = GROWS.get(stage)
    if nxt:
        return nxt if age >= G[nxt] else None
    if stage == "adult" and world_days(cfg, pet["stage_at"]["adult"], house["tick"]) >= L["adult_days"]:
        return "elder"
    return None


def grow(house, cfg, pet):
    """The morning check. Returns the new stage if it changed."""
    stage = earned(house, cfg, pet)
    if not stage:
        return None
    old, pet["stage"] = pet["stage"], stage
    if stage == "elder":
        genes.grey(pet)   # SPEC-v3.5 §2.1: a body changes at birth, and a little with age
    pet["stage_at"][stage], pet["bodies"][stage] = house["tick"], dict(pet["genome"])
    new = UNLOCKS[stage] + (["bigger things"] if cfg["make"]["parts"][stage] > cfg["make"]["parts"][old] else [])
    feel = "you feel older; your body is slower, and there are things only the old can do: " if stage == "elder" \
        else "you feel bigger; you can do new things: "
    add_event(house, pet, feel + ", ".join(new))
    pet["news"].append("event")
    from .world import STAGE_WORD, a_stage   # SPEC-v3.2 §6: stages in plain words, on the page; the pet is told as before
    moment(house, "stage", "%s has grown: %s now" % (label(pet), a_stage(stage)) if STAGE_WORD[stage] != STAGE_WORD[old]
           else "%s has grown a little" % label(pet), pet["id"], pet["room"])
    return stage


# ---- wearing down and dying ----

def wear(house, cfg, pet):
    """Each waking tick: remember how well it is living, and what neglect costs (§4.1). Time with comfort and
    energy both low adds up, and time when they are not pays it back; after `neglect_days` of it the pet is weak,
    and every further day of it costs days of life."""
    L, needs = cfg["life"], pet["needs"]
    pet["well"][0] += sum(needs.values()) / len(needs)
    pet["well"][1] += 1
    low = (needs["comfort"] + needs["energy"]) / 2 < L["neglect_below"]
    pet["neglect"] = max(0, pet.get("neglect", 0) + (1 if low else -1))
    if pet["neglect"] >= L["neglect_days"] * cfg["ticks_per_day"] * L["awake_share"]:
        if not pet["weak"]:
            pet["weak"] = True
            pet["news"].append("event")
            moment(house, "weak", "%s has grown weak" % label(pet), pet["id"], pet["room"])
        if low:
            pet["lost_days"] += L["neglect_cost_days"] * (1.4 - 0.8 * pet["temper"]["hardy"]) / (cfg["ticks_per_day"] * L["awake_share"])
    elif pet["weak"] and pet["neglect"] < L["neglect_days"] * cfg["ticks_per_day"] * L["awake_share"] / 2:
        pet["weak"] = False
    if K.on(cfg, "deaths"):   # SPEC-v4.2 §2: weakness is neglect's decline, on the page
        if pet["weak"]:
            pet.setdefault("decline", {}).setdefault("neglect", house["tick"])
        else:
            (pet.get("decline") or {}).pop("neglect", None)
    if K.on(cfg, "lives"):   # SPEC-v4.2 §2.1: "old and slow" for its last days (the view reads the flag), and more tired
        pet["old"] = pet["stage"] == "elder" and span(cfg, pet) - days(house, cfg, pet) <= cfg["lives"]["old_days"]
        if pet["old"]:
            needs["energy"] = max(0.0, needs["energy"] - cfg["lives"]["old_tired"] * cfg["dt"])


def due(house, cfg, pet):
    """Has its life run out? Returns the cause, or None. SPEC-v4.2 §2, with [deaths] on: the cause is a key of
    contracts.DEATHS, and no death but of old age comes under the floor, nor (but a killing) before its decline has
    shown a world day (health.declined): the death waits, and the state it came from lingers."""
    D = K.on(cfg, "deaths")
    from . import health

    def may(cause):
        return not D or cause == "old age" or (not floor(house, cfg) and health.declined(house, cfg, pet, cause))
    if pet.get("death_due") and pet["stage"] not in ("egg", "dead"):   # SPEC-v4.0 §7.3: killed, or dead of sickness (conflict.py, health.py)
        cause = K.OLD_CAUSE.get(pet["death_due"], pet["death_due"]) if D else pet["death_due"]
        if may(cause):
            return cause
        pet.pop("death_due")
        pet.pop("death_words", None)
    if pet["stage"] not in ("egg", "dead") and needs.starved(house, cfg, pet) and may("starvation"):
        return "starvation"   # SPEC-v4.0 §2: starving long enough kills
    if pet["stage"] in ("egg", "dead") or days(house, cfg, pet) < span(cfg, pet):
        return None
    return "neglect" if pet["lost_days"] > 1 and pet["stage"] not in ("elder",) and may("neglect") else "old age"


def floor(house, cfg):
    """SPEC-v4.2 §2: while fewer than [deaths] floor hobs are alive (hatched), nothing kills but old age."""
    return K.on(cfg, "deaths") and sum(p["stage"] not in ("egg", "dead") for p in house["pets"].values()) < cfg["deaths"]["floor"]


# SPEC-v4.2 §2.7: every cause in words, for the stone and the record, when nothing more is known of it (the place where a
# death is decided writes fuller ones into pet["death_words"]: "fell at the pond when Sasha shoved it")
CAUSE_WORDS = {"old age": "died of old age", "sickness": "died of a sickness, untended", "injury": "died of a hurt that was never tended",
               "bad food": "died of something it ate", "killing": "was killed", "manslaughter": "died of a fall",
               "exposure": "died of the cold, untended", "starvation": "died of hunger", "neglect": "wasted away, uncared for"}
# what the one who could have prevented it did not do (§2 "preventable": a memory of weight 4)
COULD = {"sickness": "I could have sat with %s when it was sick, and I did not", "injury": "I could have tended %s's hurt, and I did not",
         "bad food": "I could have nursed %s after what it ate, and I did not", "exposure": "I could have brought %s in from the cold, and I did not",
         "manslaughter": "I saw %s shoved, and I did not step in", "starvation": "I could have shared my food with %s, and I did not",
         "neglect": "I could have looked after %s, and I did not"}


def cause_words(pet, cause):
    """A death's cause in words for the stone and the record (§2.7)."""
    return pet.get("death_words") or CAUSE_WORDS.get(cause) or "died of %s" % cause


def grieve(house, cfg, dead):
    """SPEC-v4.2 §1.2: an elder whose close bond or child has died loses `grief_days` of its span, once a death.
    Returns the elders who did."""
    out = []
    for e in house["pets"].values():
        if e["stage"] == "elder" and e is not dead and dead["id"] not in e.setdefault("grieved", []) \
                and (bonds.close(house, e) == dead["id"] or dead["id"] in e["children"]):
            e["grieved"].append(dead["id"])
            e["span_add"] = e.get("span_add", 0.0) - cfg["lives"]["grief_days"]
            out.append(e)
    return out


def remembered(house, cfg, pet, cause, words):
    """SPEC-v4.2 §2 "preventable" and "remembered": the grown hob who could have prevented it and did not keeps a memory
    of weight 4 saying so; whoever saw it comes to believe something of it (B's hooks take contracts.believe_later)."""
    from . import memories, opinions
    P, name = house["pets"], label(pet)
    seen = [p for p in P.values() if p["room"] == pet["room"] and p is not pet and p["stage"] not in ("egg", "dead") and not p["sleep"]]
    if cause in COULD:
        nursed = set(pet.get("nursed_by") or {})
        grown = [p for p in P.values() if p is not pet and p["stage"] in ("adult", "elder") and p["id"] not in nursed and p["id"] != pet.get("shoved_by")]
        if cause == "manslaughter":
            grown = [p for p in grown if p in seen]
        dear = lambda p: (opinions.kin(house, p, pet) or bonds.kind(house, p["id"], pet["id"]) in ("close", "friend"), p in seen)
        could = max(sorted(grown, key=lambda p: p["id"]), key=dear, default=None)
        if could:
            memories.add(house, cfg, could, COULD[cause] % name, 4, about=[pet["id"]], kind="could have")
    room = house["rooms"][pet["room"]]
    what = (pet.get("sick") or {}).get("what")
    hook = {"bad food": what and {"name": "avoid_thing", "arg": what}, "manslaughter": {"name": "avoid_place", "arg": room["name"]},
            "exposure": {"name": "avoid_place", "arg": room["name"]}}.get(cause)
    text = {"bad food": "the %s killed %s" % (what or "food", name), "manslaughter": "%s is a dangerous place: %s fell there" % (room["name"], name),
            "exposure": "a night out in %s killed %s" % (room["name"], name)}.get(cause, "%s %s" % (name, words))
    for p in seen if cause != "old age" else ():
        K.believe_later(p, text, hook or None, "seen", truth=True)


def migrate(house, cfg):
    """SPEC-v4.2 §1.4, once a house, at load (the lead's restart): with [lives] on, each living hob's stage is reckoned
    again from the days it has lived under the new thresholds, except that an elder stays an elder, its span re-drawn
    (pet["span_add"]) to be as far through an elder's days of a forty-day life as it was through its old ones; with
    [deaths] on, the stones' causes become contracts.DEATHS keys and sicknesses take the new names. Returns the report's
    lines, one a living hob."""
    M, lines = house.setdefault("migrated", {}), []
    if K.on(cfg, "lives") and not M.get("v42_lives"):
        M["v42_lives"] = house["tick"]
        old_L, old_G = cfg["life"], cfg["growth"]
        L, G = numbers(cfg)
        off = dict(cfg, lives=dict(cfg["lives"], on=False))
        for p in sorted(alive(house), key=lambda p: p["id"]):
            if p["stage"] == "egg":
                continue
            age, was = days(house, cfg, p), p["stage"]
            if was == "elder" and age >= G["adult"]:
                p.pop("span_add", None)
                start_old, start_new = old_G["adult"] + old_L["adult_days"], G["adult"] + L["adult_days"]
                f = max(0.0, min(1.0, (age - start_old) / max(0.5, span(off, p) - start_old)))
                left = max(cfg["lives"]["old_days"] + 1.0, (span(cfg, p) - start_new) * (1 - f))
                p["span_add"] = round(age + left - span(cfg, p), 2)
                lines.append("%s stays an elder (day %.0f), about %.0f days left" % (label(p), age, left))
                continue
            lines.append(restage(house, cfg, p, age, was))
    if K.on(cfg, "lives") and not M.get("v42_young_elders"):
        # (20 October 2026: "an elder stays an elder" is for hobs old under the old life; one that grew old on
        # the live profile's thirteen-day clock before it is grown under the new one is re-staged, its span the new
        # life's: Pansy, an elder at day 12, is a youngling. Houses migrated before this are put right once.)
        M["v42_young_elders"] = house["tick"]
        for p in sorted(alive(house), key=lambda p: p["id"]):
            age = days(house, cfg, p)
            if p["stage"] == "elder" and age < numbers(cfg)[1]["adult"]:
                p.pop("span_add", None)
                lines.append(restage(house, cfg, p, age, "elder"))
    if K.on(cfg, "deaths") and not M.get("v42_deaths"):
        M["v42_deaths"] = house["tick"]
        for p in house["pets"].values():
            if p.get("cause") in K.OLD_CAUSE:
                p["cause"] = K.OLD_CAUSE[p["cause"]]
            if (p.get("sick") or {}).get("level") in K.OLD_SICK:
                p["sick"]["level"] = K.OLD_SICK[p["sick"]["level"]]
    return lines


def restage(house, cfg, p, age, was):
    """§1.4: its stage reckoned from the days it has lived under the new thresholds; the report's line."""
    G = numbers(cfg)[1]
    new = next((s for s in ("adult", "youngling", "child") if age >= G[s]), "hatchling")
    p["stage"] = new
    for s in STAGES[STAGES.index(new) + 1:]:
        p["stage_at"].pop(s, None)
    if new == "adult" and "adult" not in p["stage_at"]:
        p["stage_at"]["adult"] = house["tick"] - round((age - G["adult"]) * cfg["ticks_per_day"])
    return "%s: %s%s, day %.0f of about %.0f" % (label(p), new, " (was %s)" % was if new != was else "", age, span(cfg, p))


def die(house, cfg, pet, cause):
    """It lies still. Its things stay where they are and are free for others to change; its last words go to
    its children (§4.2, §5.2)."""
    things.drop_bits(house, cfg, house["rooms"][pet["room"]], pet["pos"], pet["carrying"])   # what it carried lies where it fell
    pet["carrying"] = []
    D = K.on(cfg, "deaths")
    if D:   # SPEC-v4.2 §2.7: the cause as its key, and in words
        cause = K.OLD_CAUSE.get(cause, cause)
        pet["cause_words"] = cause_words(pet, cause)
        pet.pop("death_words", None)
    pet.update(stage_before=pet["stage"], stage="dead", died=house["tick"], cause=cause, plan=None, thinking=None, sleep=None, following=None)
    craft.lost(house, cfg)   # SPEC-v3.4 §3.3: what only it knew is lost with it
    name = label(pet)
    if pet["message"]:
        pet["last_words"] = pet["message"][-1]["text"]
    for kid in (house["pets"][c] for c in pet["children"]):
        if kid["stage"] == "dead":
            continue
        had = next((t for t in kid["told"] if t["by"] == pet["id"] and t["kind"] in ("message", "last words")), None)
        if pet["last_words"] and (not had or had["text"] != pet["last_words"]):
            kid["told"].insert(0, {"by": pet["id"], "who": pet["word"], "kind": "last words", "text": pet["last_words"], "tick": house["tick"]})
        if kid["stage"] != "egg":
            add_event(house, kid, "your %s has died" % pet["word"])
            kid["news"].append("event")
    for other in house["pets"].values():
        if other["room"] == pet["room"] and other["stage"] not in ("egg", "dead") and other["id"] != pet["id"] and other["parent"] != pet["id"]:
            add_event(house, other, "%s has stopped moving and does not wake" % name)
            other["news"].append("event")
    moment(house, "death", "%s %s, %d days old" % (name, pet["cause_words"], round(days(house, cfg, pet))) if D else
           "%s died of %s, %d days old" % (name, cause, round(days(house, cfg, pet))), pet["id"], pet["room"])
    if D:
        remembered(house, cfg, pet, cause, pet["cause_words"])
    if K.on(cfg, "lives"):
        grieve(house, cfg, pet)


def bury(house, cfg, pet):
    """After it has lain still a while it fades and leaves a stone with its name (§4.2). Nobody can move or unmake it."""
    room = house["rooms"][pet["room"]]
    name, n = ("stone for %s" % label(pet)).lower(), 2
    while name in room["objects"]:
        name, n = ("stone for %s %d" % (label(pet), n)).lower(), n + 1
    lived = round(world_days(cfg, pet["born"] or pet["died"], pet["died"]))
    room["objects"][name] = {"pos": free_tile(house, cfg, room, pet["pos"]),
                             "memorial": {"pet": pet["id"], "text": "a stone for %s, who lived %d days and made %d things" % (label(pet), lived, pet["made"])}}
    if pet.get("cause_words"):   # SPEC-v4.2 §2.7: the cause on the stone's title, and in the life record (which the bury keeps)
        room["objects"][name]["memorial"].update(text="a stone for %s, who %s after %d days, and made %d things" % (label(pet), pet["cause_words"], lived, pet["made"]),
                                                 cause=pet["cause"], words=pet["cause_words"])
        if isinstance(pet.get("life"), dict):
            pet["life"].update(cause=pet["cause"], cause_words=pet["cause_words"])
    resting.bury(house, cfg, room, name)   # and a box for what it left lying about (order.keep); SPEC-v3.5.12 §4: the stone to the resting place, the box to its family's shelf
    pet["buried"] = True
    if not alive(house) and house["lineage"]["ended"] is None:
        house["lineage"]["ended"] = house["tick"]
        moment(house, "ended", "the house is quiet: nobody is left of this family", None, room["id"])


def check_bequeath(a, house, cfg, pet, norm):
    name = norm(a.get("what"))
    room = house["rooms"][pet["room"]]
    o = room["objects"].get(name)
    if not o or "made" not in o or not (o["made"]["owner"] == pet["id"] or pet["id"] in (o["made"].get("heirloom") or {}).get("to", [])):
        return "you can only leave something that is yours"
    if not pet["useful"]:
        return "you have made nothing yet that is really yours to leave"
    kids = heirs(house, pet, a.get("to"))
    if not kids:
        return "there is no child of yours to leave it to"
    left = [x for r in house["rooms"].values() if r["type"] for x in things.made(r).values()
            if (x["made"].get("heirloom") or {}).get("from") == pet["id"]]
    if o not in left and len(left) >= 2:
        return "you have already chosen the two things you will leave"
    return None


def heirs(house, pet, to):
    kids = [house["pets"][c] for c in pet["children"] if house["pets"][c]["stage"] != "dead"]
    if isinstance(to, str) and to.strip().lower() not in ("my children", "children", ""):
        kids = [k for k in kids if (k["name"] or "").lower() == to.strip().lower()]
    return kids


def bequeath(house, cfg, pet, a, norm):
    name, kids = norm(a["what"]), heirs(house, pet, a.get("to"))
    o = house["rooms"][pet["room"]]["objects"][name]
    o["made"]["heirloom"] = {"from": pet["id"], "to": [k["id"] for k in kids], "tick": house["tick"],
                             "line": (o["made"].get("heirloom") or {}).get("line", []) + [pet["id"]]}
    if not o.get("home"):   # SPEC-v3.3 §2.3: an heirloom belongs by the family's stone, or the bed
        order.heirloom_home(house, cfg, house["rooms"][pet["room"]], o)
    for k in kids:
        if k["stage"] != "egg":
            add_event(house, k, "your %s has left you the %s" % (pet["word"], name))
    moment(house, "heirloom", "%s left %s, '%s', to %s" % (label(pet), things.a_thing(cfg, o["made"]["recipe"]).replace("a ", "its ", 1).replace("an ", "its ", 1),
                                                         name, " and ".join(label(k) for k in kids)), pet["id"], pet["room"])
    return "you marked %s to be left to %s" % (name, "your children" if len(kids) > 1 else label(kids[0])), {}, "bequeath"
