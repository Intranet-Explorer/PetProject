"""Life and death, eggs and inheritance (SPEC-v3 §4, §5). A pet hatches, grows by what it has lived and made,
grows old, and dies; before that it may lay eggs, and what it hands on is a body, a temperament, a message,
and a couple of things."""
from . import genome, things
from .feel import level
from .world import (GENES, STAGES, add_event, alive, arrived, family, free_tile, hours, label, moment, new_pet, rnd, ticks)

GROWS = {"hatchling": "child", "child": "youngling", "youngling": "adult"}
UNLOCKS = {
    "hatchling": ["observe", "look", "move", "go", "speak", "rest", "use", "gather", "drop", "make", "unmake", "give", "show",
                  "follow", "nuzzle", "accept", "take", "chase", "write_belief", "revise_belief"],
    "child": ["arrange"], "youngling": ["combine", "paint"], "adult": ["teach", "lay_egg"], "elder": ["tell", "bequeath"],
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
    """Is there no room for another egg of this pet's? One family: the v3 limit. Two: five in the house, three of a family (§7.3)."""
    if not arrived(house, "strangers"):
        return len(alive(house)) >= cfg["life"]["population"]
    S = cfg["strangers"]
    return len(alive(house)) >= S["population"] or sum(family(p) == family(pet) for p in alive(house)) >= S["per_family"]


def days(house, cfg, pet):
    """World days since it hatched."""
    return (house["tick"] - pet["born"]) / cfg["ticks_per_day"] if pet["born"] is not None else 0.0


def wellbeing(pet, cfg=None):
    """The mean of all its needs over its life; each useful thing it made counts for a little more (§4.1)."""
    G = cfg["growth"] if cfg else {"useful_wellbeing": 0, "useful_max": 0}
    return (pet["well"][0] / pet["well"][1] if pet["well"][1] else 50.0) + G["useful_wellbeing"] * min(len(pet["useful"]), G["useful_max"])


def span(cfg, pet):
    """How many days this life will run (§4.1): a base, moved up to 30% by how well it has lived, a little by
    how hardy it is, and cut by neglect. Never shown to the pet."""
    L = cfg["life"]
    lived = max(-1.0, min(1.0, (wellbeing(pet, cfg) - 50) / L["wellbeing_span"]))
    return L["lifespan_days"] * (1 + L["wellbeing_share"] * lived) * (1 + L["hardy_share"] * (pet["temper"]["hardy"] - 0.5)) - pet["lost_days"]


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
        pull = (house["tick"] - pet["stage_at"]["adult"]) >= L["egg_pull_days"] * cfg["ticks_per_day"] and pet["eggs"] == 0
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
                  genome=genome.child_of(body, rng) if body else None, told=told)
    house["lineage"]["founder"] = pet["id"]
    moment(house, "egg", "an egg is lying in the nursery", pet["id"], room["id"])
    return pet


def temper_of(parent, rng, cfg):
    """A child's temperament: the parent's, each gene nudged a little, and now and then one moved a lot (§5.4)."""
    L = cfg["life"]
    t = {g: round(min(1.0, max(0.0, parent[g] + rng.gauss(0, L["temper_sigma"]))), 2) for g in GENES}
    if rng.random() < L["temper_jump"]:
        g = rng.choice(GENES)
        t[g] = round(min(1.0, max(0.0, t[g] + rng.choice([-1, 1]) * rng.uniform(0.2, 0.35))), 2)
    return t


def can_lay(house, cfg, pet):
    """None if it can lay an egg now, else what stops it, as it would feel it."""
    if pet["eggs"] >= fertility(pet):
        return "there are no more eggs in you"
    if full(house, cfg, pet):
        return "the house is full"
    if level(pet, "energy") > 1:
        return "you are too tired to lay an egg"
    return None


def lay_egg(house, cfg, pet, a, clean):
    room, rng = house["rooms"][pet["room"]], rnd(house, "egg", pet["id"], pet["eggs"])
    text, name = last_sentence(clean(a["message"], 640), 600), clean(a.get("name") or "", 16).strip() or None
    pet["message"].append({"tick": house["tick"], "text": text})
    egg = new_pet(house, cfg, room["id"], free_tile(house, cfg, room, pet["pos"]), genome=genome.child_of(pet["genome"], rng),
                  temper=temper_of(pet["temper"], rng, cfg), parent=pet["id"], name=name,
                  told=[{"by": pet["id"], "who": pet["word"], "kind": "message", "text": text, "tick": house["tick"]}])
    pet["eggs"] += 1
    moment(house, "egg", "%s laid an egg%s" % (label(pet), " and named it " + name if name else ""), pet["id"], room["id"])
    return "you laid an egg%s and told it what you want it to know" % (" and named it " + name if name else ""), {"energy": -cfg["life"]["egg_energy"]}, "lay egg"


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
    add_event(house, pet, "you hatched; you can do things now: " + ", ".join(actions_of("hatchling")))
    if not pet["told"]:
        add_event(house, pet, "no one left you any words")   # a foundling starts with nothing inherited (SPEC-v3.1 §7.1)
    parent = house["pets"].get(pet["parent"])
    if parent and parent["stage"] != "dead":
        add_event(house, parent, "the egg you laid has hatched%s" % (": " + pet["name"] if pet["name"] else ""))
        parent["news"].append("event")
    moment(house, "hatched", "%s hatched" % (pet["name"] or "an egg"), pet["id"], pet["room"])


def earned(house, cfg, pet):
    """The stage it has earned by this morning, or None (§4.1 as amended): stages are paced by days lived.
    v2 gated them on useful things, and one of those takes a pet hours whatever the clock says."""
    stage, age = pet["stage"], days(house, cfg, pet)
    nxt = GROWS.get(stage)
    if nxt:
        return nxt if age >= cfg["growth"][nxt] else None
    if stage == "adult" and house["tick"] - pet["stage_at"]["adult"] >= cfg["life"]["adult_days"] * cfg["ticks_per_day"]:
        return "elder"
    return None


def grow(house, cfg, pet):
    """The morning check. Returns the new stage if it changed."""
    stage = earned(house, cfg, pet)
    if not stage:
        return None
    old, pet["stage"] = pet["stage"], stage
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


def due(house, cfg, pet):
    """Has its life run out? Returns the cause, or None."""
    if pet["stage"] in ("egg", "dead") or days(house, cfg, pet) < span(cfg, pet):
        return None
    return "neglect" if pet["lost_days"] > 1 and pet["stage"] not in ("elder",) else "old age"


def die(house, cfg, pet, cause):
    """It lies still. Its things stay where they are and are free for others to change; its last words go to
    its children (§4.2, §5.2)."""
    things.drop_bits(house, cfg, house["rooms"][pet["room"]], pet["pos"], pet["carrying"])   # what it carried lies where it fell
    pet["carrying"] = []
    pet.update(stage_before=pet["stage"], stage="dead", died=house["tick"], cause=cause, plan=None, thinking=None, sleep=None, following=None)
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
    moment(house, "death", "%s died of %s, %d days old" % (name, cause, round(days(house, cfg, pet))), pet["id"], pet["room"])


def bury(house, cfg, pet):
    """After it has lain still a while it fades and leaves a stone with its name (§4.2). Nobody can move or unmake it."""
    room = house["rooms"][pet["room"]]
    name, n = ("stone for %s" % label(pet)).lower(), 2
    while name in room["objects"]:
        name, n = ("stone for %s %d" % (label(pet), n)).lower(), n + 1
    lived = round((pet["died"] - (pet["born"] or pet["died"])) / cfg["ticks_per_day"])
    room["objects"][name] = {"pos": free_tile(house, cfg, room, pet["pos"]),
                             "memorial": {"pet": pet["id"], "text": "a stone for %s, who lived %d days and made %d things" % (label(pet), lived, pet["made"])}}
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
    for k in kids:
        if k["stage"] != "egg":
            add_event(house, k, "your %s has left you the %s" % (pet["word"], name))
    moment(house, "heirloom", "%s left %s, '%s', to %s" % (label(pet), things.a_thing(cfg, o["made"]["recipe"]).replace("a ", "its ", 1).replace("an ", "its ", 1),
                                                         name, " and ".join(label(k) for k in kids)), pet["id"], pet["room"])
    return "you marked %s to be left to %s" % (name, "your children" if len(kids) > 1 else label(kids[0])), {}, "bequeath"
