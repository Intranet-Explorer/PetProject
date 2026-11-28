"""SPEC-v5.1 §5, §9 (helper B): what a hob knows how to make. pet["knows"][key] = contracts.knowledge(), a key being a
kind's ("kind:lantern", contracts.key_of) or v4's process ("clay|fire"). Every writer of v4's pet["recipes"] (making,
the talk's lesson, the visitor's teach, a child's inheriting) learns the key here too (`learned`); C's invention writes
its maker's record itself. A hob makes a kind only if it knows it, is inventing it now (pet["inventing"]), or it is a
catalog kind at or under [knowledge] free_tier (things found and put together by paw). Knowing-of (`of`: read about,
or studied above its reach) is not the recipe. A hob's tier and the house's are grammar.tier and grammar.house_tier.

Study (§5.3) is a body activity at the bench (activities.toml [study], planner's `b:study`): a world hour beside a thing
there gives its recipe if the hob's tier reaches the thing's tier - 1, else knowing-of; a fine thing sooner. Teach
(§5.4) is an aim the engine gives an elder or a know-it-all once an hour when its child or sibling lacks a recipe the
house uses (a thing of that kind stands in the house); done when they have spent the aim's while together. A tale
carries the dead one's recipe (house["tale_recipes"][tale id], beside the tale: contracts.tale keeps its shape).
Switch: [knowledge] on (contracts.on51); off is v5.0: anyone makes anything."""
from . import contracts as K
from . import grammar
from .world import add_event, label, moment

FALL = {1: "nobody left knows how to work things", 2: "nobody left knows the forge", 3: "nobody left knows how to power things",
        4: "nobody left knows signals"}   # the page's line when the house's tier falls (§5.2)
LITTLE = ("egg", "hatchling", "dead")
_seen = {}   # id(house) -> (who is alive and how much each knows, the tier then): the tier is worked out again only when that changes


def on(cfg):
    return K.on51(cfg, "knowledge")


def mine(pet):
    """Its knowledge, a dict (a list here is v3.1's strangers it knows, from before they were pet["met_hobs"])."""
    k = pet.get("knows")
    if isinstance(k, list):
        pet["met_hobs"] = list(dict.fromkeys(pet.get("met_hobs", []) + k))
    if not isinstance(k, dict):
        k = pet["knows"] = {}
    return k


def knows(house, pet, key):
    """API51: its knowledge of this key, or None."""
    v = pet.get("knows")
    return K.knowledge(v[key]) if isinstance(v, dict) and isinstance(v.get(key), dict) else None


def put(house, pet, key, how, of=False, by=None, since=None):
    """Kept, unless it knew as much already (a recipe over knowing-of is new; knowing-of over a recipe is not)."""
    cur = knows(house, pet, key)
    if not key or pet["stage"] in ("egg", "dead") or (cur and (of or not cur["of"])):
        return False
    mine(pet)[key] = K.knowledge({"since": house["tick"] if since is None else since, "from": how, "of": of, "by": by})
    return True


def learn(house, cfg, pet, key, how, of=False, by=None):
    """API51: new knowledge kept (KNOW_FROM). False when off, or it knew as much."""
    return on(cfg) and put(house, pet, key, how, of, by)


def kept(key):
    """The keys knowledge holds: kinds and processes (a dish or a joining is v4's alone)."""
    return str(key).startswith("kind:") or "|" in str(key)


def from_v4(src):
    """v4's pet["recipes"][k]["from"] in KNOW_FROM: a hob told it or seen at it is taught; taken apart is studied."""
    s = str(src or "")
    return "taught" if s.startswith(("taught", "told", "watching")) else "studied" if s == "taken apart" else s


def learned(house, cfg, pet, key, src="found"):
    """Hook (craft.learn, craft.inherit, craft.first_of, invent.make): v4's pet["recipes"] has the key; so does this."""
    if on(cfg) and kept(key):
        put(house, pet, key, from_v4(src))


def made(house, cfg, pet, kind):
    """Hook (things.make): it made one, so it knows how."""
    if on(cfg):
        put(house, pet, K.key_of(kind), "made")


def can_make(house, cfg, pet, kind):
    """API51 §5.1: it knows the recipe, or is inventing it now, or it is a catalog kind anyone can put together."""
    if not on(cfg) or pet.get("inventing") == kind:
        return True
    k = knows(house, pet, K.key_of(kind))
    if k and not k["of"]:
        return True
    if kind in (house.get("invented") or {}):
        return False
    r = grammar.recipe(house, cfg, kind)
    return r is None or r["tier"] <= cfg["knowledge"]["free_tier"]


def offered(house, cfg, pet, kinds):
    """mind.perceive: the kinds offered to make, by material, only those it can make."""
    if not on(cfg):
        return kinds
    return {m: [k for k in ks if can_make(house, cfg, pet, k)] for m, ks in kinds.items()}


def unknown(cfg, kind):
    """things.check_make's refusal, in the world's words."""
    return "you don't know how to make %s %s: someone who does could show you, or you could work one out at the bench" % (cfg["kinds"].get(kind, {}).get("a", "a"), kind)


def words_of(cfg, key):
    return "how to make %s %s" % (cfg["kinds"].get(key[5:], {}).get("a", "a"), key[5:]) if key.startswith("kind:") else "how %s" % key.replace("|", " is done: ", 1)


# ---- §5.3 study ----

def kind_of(o):
    return ((o or {}).get("made") or {}).get("recipe", {}).get("kind") or ((o or {}).get("item") or {}).get("kind")


def would(house, cfg, pet, o):
    """What studying this thing would give it: "recipe", "of", or None (nothing it hasn't)."""
    kind = kind_of(o)
    r = grammar.recipe(house, cfg, kind) if kind else None
    if not r:
        return None
    k = knows(house, pet, K.key_of(kind))
    if k and not k["of"]:
        return None
    if grammar.tier(house, cfg, pet) >= r["tier"] - 1:
        return "recipe"
    return None if k else "of"


def study(house, cfg, pet, name):
    """API51 §5.3: an hour at the bench with a thing: its recipe if the hob's tier reaches its tier - 1, else knowing-of.
    Returns (words, ok)."""
    o = house["rooms"][pet["room"]]["objects"].get(name)
    got = would(house, cfg, pet, o) if on(cfg) else None
    if not got:
        return "there is nothing more to work out from the %s" % name, False
    kind = kind_of(o)
    learn(house, cfg, pet, K.key_of(kind), "studied", of=got == "of")
    K.count(house, "studied", pet["id"])
    a = cfg["kinds"].get(kind, {}).get("a", "a")
    words = "you worked out how %s %s is made, from the %s" % (a, kind, name) if got == "recipe" else \
        "you worked out what the %s is, but not how to make one: it is beyond what you know yet" % name
    moment(house, "studied", "%s studied the %s at the bench and %s" % (label(pet), name, "worked out how to make %s %s" % (a, kind) if got == "recipe" else "saw what it is, but not how it is made"),
           pet["id"], pet["room"])
    from . import memories
    memories.remember(house, cfg, pet, "I studied the %s at the bench and %s" % (name, "worked out how %s %s is made" % (a, kind) if got == "recipe" else "could not see how it is made"),
                      3, "studied", what=[kind])
    return words, True


def study_targets(house, cfg, pet, near):
    """(planner.targets, `b:study`) At a room's bench, a thing here whose making it hasn't: one whose aim is to study, or a
    curious one."""
    from . import character, planner
    if not on(cfg) or pet["stage"] in LITTLE + ("child",):
        return []
    objs = house["rooms"][pet["room"]]["objects"]
    bench = next((n for n, o in objs.items() if o.get("fix", {}).get("bench")), None)
    a = planner.current(pet)
    aimed = bool(a) and a["kind"] == "study"
    if not bench or not (aimed or character.trait(pet, "curious") >= cfg["planner"]["pole"]):
        return []
    was = (pet.get("study") or {}).get("what")
    names = sorted((n for n, o in objs.items() if "made" in o and would(house, cfg, pet, o)), key=lambda n: (n != was, n))
    return [{"what": names[0], "goal": near(objs[bench]["pos"]), "bonus": 2.0 if aimed else 0.0}] if names else []


def studied(house, cfg, pet, now):
    """(planner.finish, `b:study`) A while at the bench with the thing: a world hour of it ([knowledge] study_hours, less
    for a finer thing) and it is studied. Returns what it did, in words."""
    name, room = now.get("what"), house["rooms"][pet["room"]]
    o = room["objects"].get(name or "")
    if not o or not would(house, cfg, pet, o):
        pet.pop("study", None)
        return None
    s = pet.get("study") if (pet.get("study") or {}).get("what") == name else {"what": name, "ticks": 0}
    s["ticks"] += max(1, house["tick"] - now.get("since", house["tick"]))
    pet["study"] = s
    need = cfg["knowledge"]["study_hours"] * cfg["ticks_per_hour"] * (1 - cfg["knowledge"]["fine_faster"] * (o["made"].get("fine") or 0))
    if s["ticks"] < need:
        return "turned the %s over at the bench, working out how it was made" % name
    pet.pop("study", None)
    words, ok = study(house, cfg, pet, name)
    pet["studied_at"] = house["tick"]
    add_event(house, pet, words)
    return words.replace("you ", "", 1)


# ---- §5.4 teach ----

def teach(house, cfg, pet, other, key):
    """API51 §5.4: it shows another how to make what it knows. Returns (words, ok)."""
    from . import craft, memories
    k = knows(house, pet, key)
    if not on(cfg) or not k or k["of"]:
        return "you don't know how to make that yourself", False
    if other["stage"] in LITTLE or (knows(house, other, key) and not knows(house, other, key)["of"]):
        return "%s knows that already" % label(other), False
    learn(house, cfg, other, key, "taught", by=pet["id"])
    craft.learn(house, cfg, other, key, "taught by %s" % label(pet))   # (and v4's recipes: the lesson's words, the house's record)
    K.count(house, "taught", pet["id"])
    w = words_of(cfg, key)
    add_event(house, other, "%s showed you %s" % (label(pet), w))
    memories.remember(house, cfg, other, "%s showed me %s" % (label(pet), w), 3, "taught", about=[pet["id"]], what=[key.split(":")[-1].split("|")[0]])
    moment(house, "taught", "%s showed %s %s" % (label(pet), label(other), w), pet["id"], pet["room"])
    return "you showed %s %s" % (label(other), w), True


def used_kinds(house):
    from . import things
    return {o["made"]["recipe"].get("kind") for r in house["rooms"].values() if r["type"] for o in things.made(r).values()}


def gap(house, cfg, a, b):
    """(talk.subject) A recipe the house uses that a knows and b doesn't, or None."""
    if not on(cfg) or not isinstance(a.get("knows"), dict):
        return None
    used = used_kinds(house)
    return next((k for k, v in sorted(a["knows"].items()) if k.startswith("kind:") and k[5:] in used and not K.knowledge(v)["of"]
                 and not (knows(house, b, k) and not knows(house, b, k)["of"])), None)


def lesson(house, cfg, pet):
    """(learner, key) it could teach: its child's or sibling's lack of a recipe the house uses, the highest tier first."""
    from . import jobs
    if pet["stage"] in LITTLE + ("child",) or not (pet["stage"] == "elder" or jobs.has(pet, "know-it-all")):
        return None, None
    used = used_kinds(house)
    mine_ = [k for k, v in (pet.get("knows") or {}).items() if k.startswith("kind:") and k[5:] in used and not K.knowledge(v)["of"]]
    kin = [p for p in house["pets"].values() if p is not pet and p["stage"] not in LITTLE
           and (p.get("parent") == pet["id"] or (p.get("parent") and p.get("parent") == pet.get("parent")))]
    for key in sorted(mine_, key=lambda k: -grammar.key_tier(house, cfg, k)):
        p = next((p for p in kin if not (knows(house, p, key) and not knows(house, p, key)["of"])), None)
        if p:
            return p, key
    return None, None


def give_teach(house, cfg, pet):
    """The aim to teach, once a day at most (a plan may drop it; it is given again the next hour)."""
    if pet.get("teach_day") == house["clock"]["day"] or any(a["kind"] == "teach" and not a.get("done") and not a.get("failed") for a in pet.get("aims") or []):
        return
    p, key = lesson(house, cfg, pet)
    if not p:
        return
    pet.setdefault("aims", []).append({"text": K.AIM_WORDS51["teach"].format(who=label(p)) + ": " + words_of(cfg, key), "why": "%s doesn't know it" % label(p),
                                       "kind": "teach", "target": p["id"], "key": key, "since": None, "done": None, "from": "drive"})


def done(house, cfg, pet, a):
    """planner.check: a teach aim is done (the while together spent): the teaching itself."""
    other = house["pets"].get(a.get("target") or "")
    if a["kind"] == "teach" and other and a.get("key"):
        words, ok = teach(house, cfg, pet, other, a["key"])
        if ok:
            pet["teach_day"] = house["clock"]["day"]
        add_event(house, pet, words)


def card(house, cfg, pet):
    """(pages.pet_page) What its card shows (C's view): its tier in words, the recipes it knows and what it knows of,
    each with how it came by it."""
    ks = pet.get("knows") if isinstance(pet.get("knows"), dict) else {}
    row = lambda k, v: {"key": k, "words": words_of(cfg, k), "from": K.knowledge(v)["from"], "how": K.KNOW_WORDS[K.knowledge(v)["from"]]}
    t = grammar.tier(house, cfg, pet)
    return {"tier": t, "tier_words": K.TIER_WORDS[t], "recipes": [row(k, v) for k, v in sorted(ks.items()) if not K.knowledge(v)["of"]],
            "of": [row(k, v) for k, v in sorted(ks.items()) if K.knowledge(v)["of"]]}


# ---- §5.2 tiers, and the tick ----

def words(house, cfg):
    """API51: the header's line, "the house knows worked things", and the fall's line while it is a day old."""
    w = K.tier_words(grammar.house_tier(house, cfg))
    f = (house.get("v5") or {}).get("tier_fall")
    return w + "; " + f["words"] if f and house["tick"] - f["tick"] < cfg["ticks_per_day"] else w


def tale_recipe(house, cfg, dead):
    """The recipe a dead hob's tale carries: what it knew how to make that nobody living knows, else its highest."""
    living = [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead") and p is not dead]
    keys = [k for k, v in (dead.get("knows") or {}).items() if k.startswith("kind:") and not K.knowledge(v)["of"]] if isinstance(dead.get("knows"), dict) else []
    lost = lambda k: not any(knows(house, p, k) and not knows(house, p, k)["of"] for p in living)
    return max(keys, key=lambda k: (lost(k), grammar.key_tier(house, cfg, k), k), default=None)


def told(house, cfg, teller, listener, t):
    """(story.tell) The tale's recipe goes to the little one who heard it. Returns its words for the telling, or ""."""
    key = (house.get("tale_recipes") or {}).get(t["id"])
    if not on(cfg) or not key:
        return ""
    learn(house, cfg, listener, key, "told", by=t["about"])
    return "; %s knew %s" % (t["name"], words_of(cfg, key))


def tick(house, cfg):
    """API51: the house's tier for today and its falls; a tale's recipe; the hour's teach aims."""
    if not on(cfg):
        return
    for t in house.get("tales") or []:
        if t["id"] not in house.setdefault("tale_recipes", {}):
            dead = house["pets"].get(t["about"])
            house["tale_recipes"][t["id"]] = tale_recipe(house, cfg, dead) if dead else None
    living = [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")]
    sig = tuple((p["id"], len(p.get("knows") or ())) for p in living)
    V = house.setdefault("v5", {})
    days = V.setdefault("tier", {})
    seen = _seen.get(id(house))
    if not seen or seen[0] != sig or str(house["clock"]["day"]) not in days:
        was = seen[1] if seen else days[max(days, key=int)] if days else None
        t = grammar.house_tier(house, cfg)
        _seen[id(house)] = (sig, t)
        days[str(house["clock"]["day"])] = t
        for old in sorted(days, key=int)[:-14]:
            days.pop(old)
        if was is not None and t < was:
            V["tier_fall"] = {"tick": house["tick"], "words": FALL.get(was, "nobody left knows what was known")}
            moment(house, "forgotten", V["tier_fall"]["words"], None, None)
    if house["tick"] % cfg["ticks_per_hour"] == 0:
        for p in living:
            give_teach(house, cfg, p)


# ---- §9 the migration's knowledge half ----

def migrate(house, cfg):
    """API51 §9, once a house (house["migrated"]["v51_knows"]): every living hob knows every kind it has made and every
    key of its pet["recipes"]. Returns the report's lines: the house's tier, each living hob's tier and what it knows."""
    done_ = house.setdefault("migrated", {})
    if done_.get("v51_knows") or not on(cfg):
        return []
    living = [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")]
    for p in living:
        mine(p)
        for k, n in (p.get("times") or {}).items():
            if k.startswith("kind ") and n > 0:
                put(house, p, K.key_of(k[5:]), "made")
        for k, r in (p.get("recipes") or {}).items():
            if kept(k):
                put(house, p, k, from_v4(r.get("from")), since=r.get("tick"))
    t = grammar.house_tier(house, cfg)
    lines = ["knowledge: the house's tier is %d (%s)" % (t, K.tier_words(t))]
    for p in sorted(living, key=lambda p: int(p["id"][1:])):
        ks = p["knows"]
        rec = sorted(k for k, v in ks.items() if not K.knowledge(v)["of"])
        of = sorted(k for k, v in ks.items() if K.knowledge(v)["of"])
        lines.append("knowledge: %s (%s), tier %d: %d recipes (%s); knows of %d (%s)" % (label(p), p["id"], grammar.tier(house, cfg, p), len(rec), ", ".join(rec) or "none",
                                                                                     len(of), ", ".join(of) or "none"))
    done_["v51_knows"] = house["tick"]
    return lines
