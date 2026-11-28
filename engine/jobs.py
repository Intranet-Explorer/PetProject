"""SPEC-v5.0 §3 (helper B): jobs. A job is an open deficit (deficits.py) with the engine's plan for it (`plan`): get
the thing that fixes it if the house has one, else gather what one is made of (buying at the machine what lies
nowhere, while it trades), make it, and use it where the deficit is. Jobs live on the work board
(house["v5"]["board"]["jobs"], contracts.job, with the thing a job carries as `item` and `at`).

Who takes what (§3.2): each tick a free hob (no job, awake, not worn out, not a little one) scores the open jobs:
urgency x its fit (`FIT`: traits, voice style, drive) x its skill x nearness; it takes the best at `[jobs] take_at` or
over. A loner (drive "to be left alone", or solitary) halves a job in a room with others in it; a sociable one likes one
where someone else is at work; a curious one or a know-it-all one that makes a kind nobody has made. One taker a job, and one job a
deficit (21 October 2026: never made again while one is on the board). A job its taker leaves untouched `[jobs] free_after_hours` of its
waking working hours is free again. A step that cannot be done fails in the world's words (§3.6), as an event and a
reaction ("plan failed").

The body does the steps (§3.1): the job's current step is the hob's current aim (planner.current reads
pet["job_aim"]), so the planner's aim pulls and leans walk it there, gather the bit, make at the bench (planner.make
makes the job's kind); the engine does the rest when the taker stands where the step is: the thing picked up goes
along with it, and is used, laid down, lit or given at the deficit's place. Making is a job (§3.3): a thing is made
for a job, a plan's reason, or the visitor's teaching (counted as made_for); nobody idles (§3.4): while a job it fits
is open, the leisure set weighs `[jobs] leisure` of itself (`weigh`). Switch: [jobs] on (on5)."""
from . import contracts as K
from . import character, craft, deficits, feel, items, order, things
from .world import LONG_AGO, add_event, dist, free_tile, hours, label

LITTLE = ("hatchling", "child")
# §3.4 the leisure set (activities.toml / behaviours.toml names): sit, look, play, wander, nap, peek, hum, stretch, a quirk
LEISURE = ("wander", "look about", "inspect", "stretch", "hum", "groom", "play", "sit by the window", "sit on", "nap", "nap in a sunbeam",
           "peek next door", "explore a doorway", "a quirk")
# §3.2 fit by character: an axis (character.trait, -1..1), a voice style or a drive (1 when it has it)
FIT = {"cold": {"kind": 1.0, "generous": 0.3, "gentle": 0.4, "to keep the family safe": 0.5},
       "dark": {"kind": 0.4, "tidy": 0.3, "to keep the family safe": 0.4},
       "mess": {"tidy": 1.0, "fussy": 0.6},
       "leak": {"brave": 1.0, "patient": 0.3, "to keep the family safe": 0.4},
       "food_low": {"generous": 0.6, "kind": 0.4, "to keep the family safe": 0.5},
       "food_spoiling": {"tidy": 0.6, "patient": 0.3, "fussy": 0.3},
       "mouse": {"brave": 1.0, "curious": 0.3},
       "no_bed": {"kind": 1.0, "generous": 0.4, "big-sister": 0.3},
       "sick_untended": {"kind": 1.0, "gentle": 0.5, "big-sister": 0.3},
       "broken": {"tidy": 1.0, "patient": 0.4},
       "works_goal": {"tidy": 0.4, "ambitious": 0.5},
       "gate_shut": {"brave": 1.0, "to leave the house": 0.8},
       "own_box": {"tidy": 1.0, "generous": 0.3},
       "own_tool": {"ambitious": 0.6, "know-it-all": 0.5, "to make the thing nobody has made": 0.4},
       "own_light": {"kind": 0.5, "curious": 0.3}}
NOVEL = {"curious": 0.5, "know-it-all": 0.5, "to make the thing nobody has made": 0.8}   # a job that makes a kind nobody has made
SKILL = {"mess": "tidying", "broken": "mending", "leak": "mending", "food_low": "fishing", "sick_untended": "making"}
# what a thing for each deficit must do (verbs, all of them), and its class if it matters
NEEDS = {"cold": (("cover",), None), "no_bed": (("cover", "hold"), None), "dark": (("light",), None), "own_light": (("light",), None),
         "mess": (("carry",), None), "leak": (("mend",), "used_up"), "food_spoiling": (("hold",), "cool"), "mouse": (("signal",), None),
         "own_box": (("hold",), "store")}
AIMK = {"get": "job", "buy": "job", "use": "job", "inspect": "job", "gather": "gather", "make": "make"}   # (planner.JOB_AIM: the way there)


def on(cfg):
    return K.on5(cfg, "jobs")


def stages(cfg):
    """SPEC-v5.3 §7 ([jobs] stages, helper C): little ones and younglings take jobs; a gather aim doesn't sit."""
    return on(cfg) and bool(cfg["jobs"].get("stages"))


PLACED = ("cold", "no_bed", "dark", "own_light", "own_box", "food_spoiling", "works_goal")   # a use step that sets down (or sells) what was fetched


def child_job(j):
    """§7: a child takes mess jobs, and jobs of fetching and gathering only (a thing set down where it is wanted at the
    end, or sold): never making, mending, nursing, fishing, the mouse or the gate."""
    return j["kind"] == "mess" or all(s["do"] in ("get", "gather", "buy") or (s["do"] == "use" and j["kind"] in PLACED) for s in j["steps"])


def board(house):
    return deficits.board(house)


def of(house, pet):
    """API5: its job, or None (an invention set aside, blocked, is not the job it is on)."""
    return next((j for j in board(house)["jobs"] if j["taker"] == pet["id"] and j["state"] == "taken" and not j.get("blocked")), None)


def deficit_of(house, j):
    return next((d for d in board(house)["deficits"] if d["id"] == j["deficit"]), None)


def step(j):
    return next((s for s in j["steps"] if not s["done"]), None)


def say(house, pet, words):
    """The world's last answer to it, for its next reaction (§3.5)."""
    pet["answer5"] = [house["tick"], words]
    add_event(house, pet, words)


# ---- the plan (§3.1) ----

def known(house, pet):
    """The rooms it knows (with no hob, those some living hob knows)."""
    ids = set(pet["rooms"]) if pet else {r for p in house["pets"].values() if p["stage"] not in ("egg", "dead") for r in p["rooms"]}
    return [r for r in house["rooms"].values() if r["type"] and r["id"] in ids]


def lying(house, pet=None):
    """{bit: the room it lies ready in} in the rooms it knows (the house's, with no hob)."""
    out = {}
    for r in known(house, pet):
        for s in r["spots"]:
            if s.get("ready") and not s.get("on") and not s.get("machine"):
                out.setdefault(s["bit"], r["id"])
    return out


def sells(house, cfg):
    """{material: the machine's room} it would sell now (while trading)."""
    from . import machine
    at = machine.found(house)
    if not at or not K.on5(cfg, "trade"):
        return {}
    return {m: at["id"] for m, n in machine.state(house, cfg)["stock"].items() if n > 0}


def source(house, cfg, pet, bit):
    """How to come by a bit: [] in its paws already, a gather step, a buy step, or None."""
    if pet and bit in pet["carrying"]:
        return []
    at = lying(house, pet).get(bit)
    if at:
        return [{"do": "gather", "what": bit, "where": at}]
    at = sells(house, cfg).get(bit)
    return [{"do": "buy", "what": bit, "where": at}] if at else None


def recipe(house, cfg, pet, kind):
    """The bits for a kind (craft.toml [needs], and one that gives it its nature), as steps; None if not to be had."""
    bad, out, got = set(cfg["kinds"][kind].get("not", [])), [], list(pet["carrying"]) if pet else []
    natural = lambda b: bool(set(cfg["house"]["bits"].get(b, {}).get("can", [])) - bad)
    for g in cfg["craft"].get("needs", {}).get(kind, []):
        alts = g.split("|")
        way = next(((b, source(house, cfg, pet, b)) for b in alts if source(house, cfg, pet, b) is not None), None)
        if not way:
            return None
        out += way[1]
        got.append(way[0])
    if not any(natural(b) for b in got):
        way = next(((b, source(house, cfg, pet, b)) for b in sorted(set(lying(house, pet)) | set(sells(house, cfg)) | set(got)) if natural(b)), None)
        if not way:
            return None
        out += way[1]
    return out


def verbs_of(house, cfg, kind):
    """A catalog kind's verbs: the parser's, of its recipe, while [grammar] is on (SPEC-v5.1 §3; DECISIONS Part 45, the
    lead's settlement at A's merge); kinds.toml's hand verbs while it is off."""
    if K.on51(cfg, "grammar"):
        from . import grammar
        return (grammar.recipe(house, cfg, kind) or {}).get("verbs") or {}
    return items.T(cfg)["kind"].get(kind, {}).get("verbs", {})


def makeable(house, cfg, verbs, cls):
    """The catalog kinds that do all these verbs, cheapest first (fewest makings, then strongest): never a keepsake,
    nothing only found or invented."""
    T, out = items.T(cfg)["kind"], []
    for k, e in T.items():
        if k not in cfg["kinds"] or cfg["kinds"][k].get("found") or cfg["kinds"][k].get("invented") or e.get("class") == "keepsake":
            continue
        vs = verbs_of(house, cfg, k)
        if not all(vs.get(v) for v in verbs) or (cls == "used_up" and not e.get("used_up")) or (cls not in (None, "used_up") and e.get("class") != cls):
            continue
        out.append((len(cfg["craft"].get("needs", {}).get(k, [])), -min(vs[v] for v in verbs), k))
    return [k for *_, k in sorted(out)]


def knower(house, cfg, kind, pet=None):
    """SPEC-v5.1 §5.1: can its taker make it (knowledge.can_make: it knows the recipe, or it is a kind anyone can put
    together)? With no taker yet, can any grown hob? So a job never reaches a make step its taker can't do."""
    from . import knowledge
    return any(knowledge.can_make(house, cfg, p, kind) for p in ([pet] if pet else [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead") + LITTLE]))


def lacking(house, cfg, pet, kind):
    """What a kind's making lacks, in the board's words: "glass, which nobody has", or "someone who knows how to make a
    lantern"; None when nothing does."""
    if not knower(house, cfg, kind):
        return "someone who knows how to make %s %s" % (cfg["kinds"].get(kind, {}).get("a", "a"), kind)
    for g in cfg["craft"].get("needs", {}).get(kind, []):
        alts = g.split("|")
        if all(source(house, cfg, pet, b) is None for b in alts):
            return "%s, which nobody has" % alts[0]
    if recipe(house, cfg, pet, kind) is None:   # (no bit of a nature it can be made of)
        return "something to make %s %s of, which nobody has" % (cfg["kinds"].get(kind, {}).get("a", "a"), kind)
    return None


def needs(house):
    """SPEC-v5.1 §8: {deficit id: what its job's make step is blocked by}, for the board."""
    return house.setdefault("v5", {}).setdefault("needs", {})


def serving(house, room, o):
    """Is this thing already where it does its work (by a sleeper's place)?"""
    return any(p.get("sleeps_in") == room["id"] and p.get("sleeps_at") and dist(p["sleeps_at"], o.get("pos") or [99, 99]) <= 1
               for p in house["pets"].values() if p["stage"] not in ("egg", "dead"))


def at_hand(house, cfg, d, verbs, cls, pet=None):
    """A thing in the house that does it and may be taken for it: (room id, name), the nearest to where it is wanted."""
    ok_owner = lambda o: o["made"]["owner"] in (None, d.get("who"), pet and pet["id"]) or house["pets"].get(o["made"]["owner"] or "", {}).get("stage") == "dead"
    found = []
    for rid, n, it in items.find(house, cfg, verb=verbs[0]):
        room = house["rooms"][rid]
        o = room["objects"].get(n)
        if not o or "made" not in o or not all(K.works(it, v) for v in verbs) or things.prop(cfg, o).get("fixed") or not ok_owner(o):
            continue
        if cls == "used_up" and not items.T(cfg)["kind"].get(it["kind"], {}).get("used_up") or cls not in (None, "used_up") and it["class"] != cls:
            continue
        if d["kind"] in ("cold", "no_bed") and (serving(house, room, o) or (d["kind"] == "cold" and rid == d.get("where"))):
            continue
        if d["kind"] in ("own_box", "own_light") and o["made"]["owner"] is not None:
            continue
        found.append((rid != d.get("where"), rid, n))
    return min(found)[1:] if found else None


def target(house, d):
    """The room a deficit's use step is done in (a hob's: where that hob is now)."""
    if d["kind"] in ("own_box", "own_tool", "own_light", "sick_untended") and d.get("who") in house["pets"]:
        return house["pets"][d["who"]]["room"]
    if d["kind"] == "broken":
        return d.get("room")
    return d.get("where") if d.get("where") in house["rooms"] else None


def plan(house, cfg, d, pet=None):
    """API5: the engine's plan for a deficit (§3.1), or None when the house has no way to it now. `pet`: the taker,
    whose paws and rooms it is planned from."""
    d = d if "id" in d else K.deficit(d)
    k, where = d["kind"], target(house, d)
    use = {"do": "use", "what": d.get("who") or d.get("name"), "where": where, "verb": None}
    item, steps, thing = None, None, None
    if k in NEEDS or k == "own_tool":
        verbs, cls = NEEDS.get(k, ((), None))
        kinds = [d["tool"]] if k == "own_tool" and d.get("tool") in items.T(cfg)["kind"] else makeable(house, cfg, verbs, cls)
        if k == "own_tool":
            verbs = tuple(verbs_of(house, cfg, d.get("tool")))[:1] or ("hold",)
        item = at_hand(house, cfg, d, verbs, cls, pet) if k != "own_tool" else None
        use["verb"] = verbs[0] if verbs else None
        if item:
            o = house["rooms"][item[0]]["objects"][item[1]]
            thing = o["made"]["recipe"].get("kind")
            steps = ([] if item[0] == where else [{"do": "get", "what": item[1], "where": item[0], "verb": use["verb"]}]) + [use]
        else:
            for kind in kinds:
                bits = recipe(house, cfg, pet, kind) if kind in cfg["kinds"] and knower(house, cfg, kind, pet) else None
                if bits is not None:
                    thing, steps = kind, bits + [{"do": "make", "what": kind, "where": None}, use]
                    break
            if steps is None and kinds and pet is None and K.on51(cfg, "grammar"):   # (SPEC-v5.1 §8: the board says what the make step lacks)
                needs(house)[d["id"]] = lacking(house, cfg, pet, kinds[0]) or ""
        if steps is None and k == "mess":   # (no carry tool to be had: tidied by paw)
            steps = [use]
        if steps is None and k == "mouse":   # (nothing to scare it with: chased off by paw)
            steps = [use]
    elif k == "broken":
        from . import verbs as V
        o = house["rooms"].get(d.get("room") or "", {}).get("objects", {}).get(d.get("name") or "")
        if o is None:
            return None
        part = next((s for b in V.PARTS[V.family(o)] for s in [source(house, cfg, pet, b)] if s is not None), None)
        if part is None:
            return None
        steps = part + [dict(use, what=d["name"], verb="mend")]
    elif k == "food_low":
        F = cfg["seasons"]["food"]["bits"]
        bit = next((b for b, _ in sorted(lying(house, pet).items()) if b in F), None)
        from .pond import room_of
        pond = room_of(house, cfg)
        steps = [{"do": "gather", "what": bit, "where": lying(house, pet)[bit]}] if bit else \
            [{"do": "use", "what": None, "where": pond["id"], "verb": "catch"}] if pond and (pet is None or pond["id"] in pet["rooms"]) else None
    elif k == "works_goal":
        bit = max(sorted(lying(house, pet)), key=lambda b: sum(s["bit"] == b and s.get("ready") for r in known(house, pet) for s in r["spots"]), default=None)
        have = list(pet["carrying"]) if pet else []
        steps = ([{"do": "gather", "what": bit, "where": lying(house, pet)[bit]}] * max(0, 3 - len(have)) if bit else []) + [use]
        if not bit and not have:
            return None
    elif k == "gate_shut":
        steps = [{"do": "inspect", "what": None, "where": where}]
    else:   # sick_untended: nursing, the body's (planner's nurse)
        steps = [use]
    if not steps or (pet and any(s["do"] in ("get", "gather", "use", "inspect") and s.get("where") and s["where"] not in pet["rooms"] for s in steps)):
        return None
    words = d.get("words") or deficits.words(house, cfg, d)
    return dict(K.job({"id": "%s#%d" % (d["id"], house["tick"]), "deficit": d["id"], "kind": k, "steps": steps, "since": house["tick"], "state": "open",
                       "words": "%s, with %s %s" % (words, cfg["kinds"].get(thing, {}).get("a", "a"), thing) if thing else words}),
                item=item[1] if item else None, at=item[0] if item else None, thing=thing)


# ---- who takes what (§3.2) ----

def has(pet, name):
    """Its trait (-1..1), voice style or drive (1 if it has it, else 0)."""
    if name in character.AXES:
        return character.trait(pet, name)
    return 1.0 if name in ((pet.get("voice") or {}).get("style"), (pet.get("drive") or {}).get("name")) else 0.0


def loner(cfg, pet):
    return (pet.get("drive") or {}).get("name") == "to be left alone" or character.trait(pet, "social") <= -cfg["planner"]["pole"]


def hops(house, a, b):
    """Doors between two rooms (4 if there is no way)."""
    seen, edge = {a}, [a]
    for n in range(4):
        if b in seen:
            return n
        edge = [to for r in edge for to in house["rooms"][r]["doors"].values() if house["rooms"][to]["type"] and to not in seen]
        seen.update(edge)
    return 0 if b in seen and b == a else 4


def made_kinds(house):
    return {o["made"]["recipe"].get("kind") for r in house["rooms"].values() if r["type"] for o in things.made(r).values()} \
        | {g.get("recipe", {}).get("kind") for g in house.get("gone_things", [])}


def fit(house, cfg, pet, j):
    """How well it suits this hob (0 up): its character, its own need, a kind nobody has made, company at work."""
    d = deficit_of(house, j) or {}
    f = 0.5 + sum(w * has(pet, n) for n, w in FIT[j["kind"]].items())
    if d.get("who") == pet["id"] and j["kind"].startswith("own"):
        f += 0.5   # (its own need)
    if j.get("thing") and any(s["do"] == "make" for s in j["steps"]) and j["thing"] not in made_kinds(house):
        f += sum(w * has(pet, n) for n, w in NOVEL.items())
    room = target(house, d) if d else None
    if room and any(x["taker"] and x["taker"] != pet["id"] and target(house, deficit_of(house, x) or {"kind": None}) == room for x in board(house)["jobs"]):
        f += 0.4 * has(pet, "social")   # (where someone else is already at work)
    return max(0.0, f)


def may(house, cfg, pet, j):
    """May this hob take this job at all: its stage, a sick one not its own nurse, not refused today."""
    d = deficit_of(house, j) or {}
    if stages(cfg):   # SPEC-v5.3 §7: a child fetches, gathers and tidies; a youngling takes any but nursing (below); grown, all
        if pet["stage"] == "hatchling" or (pet["stage"] == "child" and not child_job(j)):
            return False
    elif pet["stage"] in LITTLE or (pet["stage"] == "youngling" and d.get("urgency", 1) > 2):
        return False
    if j["kind"] == "sick_untended" and (pet["stage"] not in ("adult", "elder") or d.get("who") == pet["id"]):
        return False
    from . import sheet
    if sheet.on(cfg) and any(sheet.shuns(house, cfg, pet, "fish" if j["kind"] == "food_low" and s["do"] == "use" else AIMK.get(s["do"], "help"), target(house, d) if d else None) for s in j["steps"]):
        return False   # (24 November 2026) not a job that is what it is afraid of, or where
    r = pet.get("refused5") or {}
    return not (r.get("day") == house["clock"]["day"] and j["deficit"] in r.get("ids", []))


def score(house, cfg, pet, j):
    """urgency x fit x skill x nearness; a loner halves a job in a room with others in it."""
    d = deficit_of(house, j)
    if not d or not may(house, cfg, pet, j) or house["tick"] - j.get("cant", {}).get(pet["id"], LONG_AGO) < hours(cfg, 1):
        return 0.0
    if d["urgency"] < 3 and K.on53(cfg, "projects"):   # SPEC-v5.3 §2.1 (helper A): the day's project step comes before a job that can wait
        from . import projects
        if projects.due(house, cfg, pet):
            return 0.0
    first = next((s["where"] for s in j["steps"] if s.get("where")), None) or target(house, d) or pet["room"]
    near = 1.0 / (1 + 0.25 * hops(house, pet["room"], first))
    s = d["urgency"] * fit(house, cfg, pet, j) * (1 + 0.2 * craft.skill(cfg, pet, SKILL.get(j["kind"], "making"))) * near
    room = target(house, d)
    if room and loner(cfg, pet) and sum(p["room"] == room and p is not pet and not p["sleep"] for p in house["pets"].values() if p["stage"] not in ("egg", "dead")) >= 2:
        s /= 2
    return s


def free_hob(house, cfg, pet):
    return pet["stage"] not in ("egg", "dead") + (("hatchling",) if stages(cfg) else LITTLE) and not pet["sleep"] and not of(house, pet) and feel.level(pet, "energy") < 3


def fits(house, cfg, pet):
    """Is there an open job it fits (would take)?"""
    return any(j["state"] == "open" and score(house, cfg, pet, j) >= cfg["jobs"]["take_at"] for j in board(house)["jobs"])


def take(house, cfg, pet, j):
    """It takes the job: planned again from what it carries and knows; counted."""
    d = deficit_of(house, j)
    again = plan(house, cfg, d, pet) if d else None
    if not again or (stages(cfg) and pet["stage"] == "child" and not child_job(again)):   # (it has no way to it from what it carries and knows, or none a child may: not offered it again for a world hour)
        j.setdefault("cant", {})[pet["id"]] = house["tick"]
        return False
    j.update({k: again[k] for k in ("steps", "item", "at", "thing", "words")}, taker=pet["id"], state="taken", touched=house["tick"], step_at=house["tick"])
    d["by"] = pet["id"]
    K.count(house, "taken", pet["id"])
    K.count(house, "taken_kind", j["kind"])
    add_event(house, pet, "you set about it: %s" % j["words"])
    aim(house, cfg, pet, j)
    return True


def leave(house, pet, j, state="open"):
    """It lets the job go (free again), or the job is over (done, failed): off the taker. An invention is its
    inventor's and is never dropped (21 October 2026): let go, it is set aside, blocked, until it can go on."""
    if j.get("invent"):
        if pet.get("inventing") == j["invent"]["kind"]:
            pet.pop("inventing")
        if state == "open":
            return block(house, pet, j, j.get("blocked") or "set aside for now")
    j.update(taker=None if state == "open" else j["taker"], state=state)
    pet.pop("job_aim", None)
    if state == "open":
        for s in j["steps"]:
            s["done"] = s["done"] and s["do"] in ("gather", "buy")   # (what it gathered it still carries: the next taker plans its own)


def block(house, pet, j, words):
    """SPEC-v5.1 §4.4 an invention that can't go on waits on the board, blocked, in words ("needs reed; the garden has
    none"), still its inventor's. It is untied from its wrong, so the wrong can be put right another way meanwhile."""
    j["blocked"] = words
    if not j["deficit"].startswith("invent|"):
        j["deficit"] = "invent|%s#%d" % (j["invent"]["kind"], j["since"])
        j["steps"] = [s for s in j["steps"] if s["do"] != "use"]
    pet.pop("job_aim", None)


def unblock(house, cfg, pet, j):
    """A blocked invention goes on when its inventor is free and every bit it still needs is to be had: lying in a room
    it knows, sold by the machine, or in its paws."""
    if of(house, pet) or pet.get("inventing") or pet["stage"] in ("egg", "dead"):
        return False
    lying_, sells_ = lying(house, pet), sells(house, cfg)
    for s in j["steps"]:
        if s["do"] in ("gather", "buy") and not s["done"]:
            b = s["what"]
            if b in lying_:
                s.update(do="gather", where=lying_[b])
            elif b in sells_:
                s.update(do="buy", where=sells_[b])
            elif b in pet["carrying"]:
                s.update(do="gather", where=None)
            else:
                return False
    j.pop("blocked", None)
    j["touched"] = j["step_at"] = house["tick"]
    pet["inventing"] = j["invent"]["kind"]
    aim(house, cfg, pet, j)
    return True


def fail(house, cfg, pet, j, words):
    """§3.6 a step that cannot be done, in the world's words: an event, a reaction, and the job off the board. An
    invention's is blocked instead, its words on the board, and is never dropped (SPEC-v5.1 §4.4)."""
    from . import brain4
    if j.get("invent"):
        s = step(j)
        if s and s["do"] == "gather":
            where = house["rooms"][s["where"]]["name"] if s.get("where") in house["rooms"] else "the house"
            words = "needs %s; %s has none" % (s["what"], where)
        if j.get("blocked") != words:
            say(house, pet, "the %s will have to wait: it %s" % (j["invent"]["kind"], words))
            brain4.notable(house, cfg, pet, "plan failed", words)
        if pet.get("inventing") == j["invent"]["kind"]:
            pet.pop("inventing")
        return block(house, pet, j, words)
    say(house, pet, words)
    brain4.notable(house, cfg, pet, "plan failed", words)
    leave(house, pet, j, "failed")
    d = deficit_of(house, j)
    if d:
        d["next_job"] = house["tick"] + hours(cfg, cfg["jobs"]["free_after_hours"])


def aim(house, cfg, pet, j):
    """The job's current step as the hob's current aim (planner.current)."""
    s = step(j)
    if not s:
        pet.pop("job_aim", None)
        return
    d = deficit_of(house, j) or {}
    kind, tg = AIMK[s["do"]], s.get("where") if s["do"] != "gather" else s["what"]
    if s["do"] == "make" and j.get("invent"):   # (SPEC-v5.1 §4.4: to the station; the engine makes it there)
        kind = "job"
    if s["do"] == "use" and j["kind"] == "sick_untended":
        kind, tg = "nurse", d.get("who")
    elif s["do"] == "use" and j["kind"] == "food_low":
        kind, tg = "fish", None
    elif s["do"] == "use" and not s.get("where") and d.get("who") in house["pets"]:
        tg = house["pets"][d["who"]]["room"]
    a = {"kind": kind, "text": j["words"][:100], "target": tg, "since": j.get("step_at", house["tick"]), "done": False, "job": j["id"]}
    if (pet.get("job_aim") or {}).get("since") != a["since"] or (pet.get("job_aim") or {}).get("target") != tg:
        pet["job_aim"] = a


# ---- the steps, done where they are (§3.1) ----

def move_along(house, cfg, pet, j):
    """The thing the job carries goes where its taker goes."""
    n, src = j.get("item"), house["rooms"].get(j.get("at") or "")
    o = src and src["objects"].get(n)
    if not o or src["id"] == pet["room"]:
        return bool(o)
    dst = house["rooms"][pet["room"]]
    if n in dst["objects"]:
        return True   # ponytail: a thing of that name is there already; it waits where it was
    src["objects"].pop(n)
    items.place(house, cfg, src, n, o)
    for k in ("wall", "home", "places", "kept"):
        o.pop(k, None)
    o["pos"] = free_tile(house, cfg, dst, pet["pos"], n)
    dst["objects"][n] = o
    j["at"] = dst["id"]
    return True


def lay_by(house, cfg, room, n, o, at):
    """Set a thing down by a place (a sleeper's)."""
    items.place(house, cfg, room, n, o)
    order.moved(o, house["tick"], house, cfg, room, n)
    o["pos"] = free_tile(house, cfg, room, at, n)


def whose(house, cfg, j, n, room):
    o = room["objects"].get(n or "") or {}
    owner = house["pets"].get((o.get("made") or {}).get("owner") or "")
    return "%s's %s" % (label(owner), j.get("thing") or n) if owner else "the %s" % n


def use(house, cfg, pet, j, d):
    """The last step, at the deficit's place: (words, True done | False failed | None the body is at it till it closes)."""
    from . import director, verbs
    room, k, n = house["rooms"][pet["room"]], j["kind"], j.get("item")
    o = room["objects"].get(n or "")
    if n and o is None and k not in ("broken", "works_goal"):
        return "the %s isn't here any more" % n, False
    if k in ("cold", "no_bed"):
        who = house["pets"].get(d.get("who") or "") if k == "no_bed" else next((p for p in deficits.living(house) if p.get("sleeps_in") == room["id"] and p.get("sleeps_at")), None)
        if not who or not who.get("sleeps_at"):
            return None, None
        lay_by(house, cfg, room, n, o, who["sleeps_at"])
        if k == "no_bed":   # (its bed, its own)
            o["made"]["owner"] = who["id"]
        return "you laid the %s where %s sleeps" % (n, label(who)), True
    if k in ("dark", "own_light"):
        if k == "own_light" and d.get("who") in house["pets"]:
            o["made"]["owner"] = d["who"]
        it = items.of(house, cfg, o, n, room)
        if deficits.night(house) and it and not it["state"]["lit"]:
            words, _, key = verbs.apply(house, cfg, pet, n, "light")
            return words, key is not None
        return "you set the %s down in %s, ready for the night" % (n, room["name"]), True
    if k == "mess":
        if not o:
            return None, None
        words, _, key = verbs.apply(house, cfg, pet, n, "carry")
        return words, key is not None
    if k == "leak":
        things.gone(house, room["objects"].pop(n), n, "used up mending the leak in %s" % room["name"], room)
        room["wet_until"] = house["tick"]
        craft.practise(house, cfg, pet, "mending")
        return "you set the %s over the leak in %s; the water has stopped coming in" % (n, room["name"]), True
    if k == "food_spoiling":
        for s in deficits.spoiling(house, cfg, room):
            s["on"], s["pos"] = n, list(o["pos"])
        return "you put the food by in the %s, where it keeps" % n, True
    if k == "mouse":
        cr = next((c for c in house["creatures"] if c["kind"] == "mouse" and c["room"] == room["id"] and not c.get("tame")), None)
        if not cr:
            return "the mouse has gone", True
        said = verbs.apply(house, cfg, pet, n, "signal")[0] + "; " if o else ""
        return said + director.chased(house, cfg, cr, pet), True
    if k == "broken":
        return verbs.mend(house, cfg, pet, d.get("name") or "")
    if k == "works_goal":
        return sell(house, cfg, pet, j)
    if k in ("own_box", "own_tool"):
        who = house["pets"].get(d.get("who") or "")
        if not who:
            return None, None
        o["made"]["owner"] = who["id"]
        if who is not pet:
            add_event(house, who, "%s gave you the %s: it is yours" % (label(pet), n))
        return "you gave the %s to %s" % (n, label(who)) if who is not pet else "the %s is yours now" % n, True
    return None, None   # (sick_untended, food_low at the pond: the body's, till it closes)


def sell(house, cfg, pet, j):
    """works_goal's use: what it gathered for the Works, sold (trading) or fed to the machine."""
    from . import machine, trade
    bits = [b for b in pet["carrying"] if b in keep(pet, j)] or list(pet["carrying"])
    if not bits:
        return "you have nothing to bring the Works", False
    if K.on5(cfg, "trade"):
        said = [trade.sell(house, cfg, pet, b)[0] for b in bits]
        return said[-1], True
    if len(bits) < cfg["machine"]["bits"]:
        return "the machine takes three bits at a time, and you have fewer", False
    pet["carrying"] = [b for b in pet["carrying"] if b not in bits[:3]] + bits[:3]
    back = min(cfg["machine"]["materials"], key=lambda m: machine.state(house, cfg)["stock"].get(m, 0))
    return machine.feed(house, cfg, pet, "bits", back, keep=True)[0], True


def advance(house, cfg, pet, j):
    """Its taker's job, one tick: the step done where it stands, the thing carried along, the next step its aim."""
    s, d = step(j), deficit_of(house, j)
    if not d and not j.get("invent"):
        return finish(house, cfg, pet, j)
    if j.get("held"):
        move_along(house, cfg, pet, j)
    if pet["sleep"] or _slot(house, cfg) not in ("aims", "free"):
        j["touched"] = house["tick"]   # (asleep, or at a meal or the evening's gathering: the job waits; that is not leaving it)
    if s is None:
        return finish(house, cfg, pet, j)
    where = s.get("where") or (house["pets"][d["who"]]["room"] if s["do"] == "use" and d.get("who") in house["pets"] else None)
    here = where is None or pet["room"] == where
    if here and s.get("where"):
        j["touched"] = house["tick"]
    done, why = False, None
    if s["do"] == "get" and here:
        if s["what"] in house["rooms"][where]["objects"]:
            j.update(item=s["what"], at=where, held=True)
            done = True
        else:
            why = "the %s isn't in %s any more" % (s["what"], house["rooms"][where]["name"])
    elif s["do"] == "gather":
        need = sum(1 for x in j["steps"][:j["steps"].index(s) + 1] if x["do"] in ("gather", "buy") and x["what"] == s["what"])
        done = pet["carrying"].count(s["what"]) >= need
        if not done and s["what"] not in lying(house, pet):
            other = lying(house).get(s["what"])
            why = "there's no %s left in %s%s" % (s["what"], house["rooms"][where]["name"] if where in house["rooms"] else "the rooms you know",
                                                 "; %s might have some" % house["rooms"][other]["name"] if other and other != where else "")
    elif s["do"] == "buy" and here:
        from . import trade
        why, done = trade.buy(house, cfg, pet, s["what"])
        why = None if done else why
    elif s["do"] == "make" and j.get("invent"):   # SPEC-v5.1 §4.4: made at the station, by the engine
        if here:
            from . import invention
            done, why = bool(invention.finish(house, cfg, pet, j)), j.pop("why", None)
            if not done:   # (a bit it hasn't with it: back to gathering it, not off the board)
                have = list(pet["carrying"])
                for x in j["steps"]:
                    if x["do"] in ("gather", "buy"):
                        x["done"] = x["what"] in have and not have.remove(x["what"])
                why = None if any(x["do"] in ("gather", "buy") and not x["done"] for x in j["steps"]) else why
    elif s["do"] == "make":
        m = pet.get("last_made") or {}
        if m.get("tick", LONG_AGO) >= j.get("step_at", 0) and m.get("kind") == s["what"]:
            room = house["rooms"][pet["room"]]
            n = max((n for n, o in things.made(room).items() if o["made"]["by"] == pet["id"] and o["made"]["tick"] == m["tick"]), default=None)
            if n:
                j.update(item=n, at=room["id"], held=True)
                done = True
        why = j.pop("why", None)
    elif s["do"] == "use" and here:
        why, ok = use(house, cfg, pet, j, d)
        if ok is None:
            why = None
        elif ok:
            say(house, pet, why)
            d["thing"] = whose(house, cfg, j, j.get("item"), house["rooms"][pet["room"]]) if j.get("item") else None
            j["held"], done, why = False, True, None
    elif s["do"] == "inspect" and here:
        say(house, pet, "you looked out at the weather from %s: the gate stays shut a while yet" % house["rooms"][pet["room"]]["name"])
        done = True
    if why:
        return fail(house, cfg, pet, j, why)
    if done:
        s["done"] = True
        j["touched"] = j["step_at"] = house["tick"]
        if step(j) is None:
            return finish(house, cfg, pet, j)
    aim(house, cfg, pet, j)


def finish(house, cfg, pet, j):
    """The job is done (its last step, or its deficit closed): off the board; the deficit's next job after a while."""
    d = deficit_of(house, j)
    leave(house, pet, j, "done")
    if d:
        d["next_job"] = house["tick"] + hours(cfg, cfg["jobs"]["free_after_hours"] * (12 if d["kind"] == "gate_shut" else 1))


def _slot(house, cfg):
    from . import planner
    return planner.slot(house, cfg)


# ---- the tick ----

def tick(eng):
    """API5: open deficits get their jobs; taken jobs go a step on, or go free untouched; free hobs take jobs by
    fit; what was made is counted by why; each awake hob's tick counted, and as idle when it sat about with a job it
    fits open (§3.4)."""
    house, cfg = eng.house, eng.cfg
    if not on(cfg):
        for p in house["pets"].values():
            for k in ("job_aim", "job_fit"):
                p.pop(k, None)
        return
    B, t = board(house), house["tick"]
    open_ = {d["id"]: d for d in B["deficits"]}
    B["jobs"] = [j for j in B["jobs"] if j["state"] in ("open", "taken")]
    if K.on51(cfg, "grammar"):
        from . import invention
        invention.tick(house, cfg)   # (the sprites that have landed)
    for j in list(B["jobs"]):
        p = house["pets"].get(j["taker"] or "")
        if j.get("invent") and j["deficit"] not in open_ and not j["deficit"].startswith("invent|"):   # (its wrong is gone: made for its own sake now)
            j["deficit"] = "invent|%s|%s" % (j["invent"]["kind"], j["taker"])
            j["steps"] = [s for s in j["steps"] if s["do"] != "use"]
        if j.get("invent"):
            if not p or p["stage"] in ("egg", "dead"):
                j["state"] = "failed"
                continue
            if j.get("blocked") and not (t % 10 == 0 and unblock(house, cfg, p, j)):
                continue
            advance(house, cfg, p, j)
            if j["state"] == "taken" and t - j["touched"] > hours(cfg, cfg["jobs"]["free_after_hours"]):
                add_event(house, p, "you left it undone: %s" % j["words"])
                leave(house, p, j)
            continue
        if j["deficit"] not in open_:
            if p:
                finish(house, cfg, p, j)
            else:
                j["state"] = "done"
        elif p and j["state"] == "taken":
            if p["stage"] in ("egg", "dead"):
                leave(house, p, j)
            else:
                advance(house, cfg, p, j)
                if j["state"] == "taken" and t - j["touched"] > hours(cfg, cfg["jobs"]["free_after_hours"]):
                    add_event(house, p, "you left it undone: %s" % j["words"])
                    leave(house, p, j)
    seen = set()   # (one job a deficit, the taken one kept: v5.0 made a second at urgency 4, Brody's sick_untended twice)
    B["jobs"] = [j for j in sorted(B["jobs"], key=lambda j: j["state"] != "taken") if j["state"] in ("open", "taken")
                 and (j.get("invent") and not seen.add(j["deficit"]) or not (j["deficit"] in seen or seen.add(j["deficit"])))]   # (an invention is never a second copy)
    N = needs(house) if K.on51(cfg, "grammar") else {}
    for k in [k for k in N if k not in open_ or k in seen]:
        N.pop(k)
    for d in B["deficits"]:
        if d.get("next_job", 0) > t or d["id"] in seen:
            continue
        j = plan(house, cfg, d)
        if j:
            B["jobs"].append(j)
            seen.add(d["id"])
        else:
            d["next_job"] = t + hours(cfg, cfg["jobs"]["free_after_hours"])
    pets = sorted((p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")), key=lambda p: p["id"])
    for p in pets:
        if p.get("job_aim") and not of(house, p):
            p.pop("job_aim", None)
        if stages(cfg):
            release(house, cfg, p)
        if free_hob(house, cfg, p):
            best = max(((score(house, cfg, p, j), j["id"], j) for j in B["jobs"] if j["state"] == "open"), default=None, key=lambda x: x[:2])
            if best and best[0] >= cfg["jobs"]["take_at"] and not any(x["deficit"] == best[2]["deficit"] and x["taker"] == p["id"] for x in B["jobs"]):
                take(house, cfg, p, best[2])
    if cfg["jobs"]["ask_nurse"]:
        ask_nurse(house, cfg, B)
    for p in pets:
        counted(house, cfg, p)


def counted(house, cfg, p):
    """What it made since (by why: job, plan, taught, nothing), and its tick: awake, and idle (§3.4)."""
    m = p.get("last_made") or {}
    if "made_seen" not in p:
        p["made_seen"] = m.get("tick")
    elif m.get("tick") != p["made_seen"]:
        p["made_seen"] = m["tick"]
        why = p.pop("make_for", None) or "nothing"
        K.count(house, "made_for", why)
        if K.on51(cfg, "grammar"):   # SPEC-v5.1 §8: by a recipe, or the first of an invention
            K.count(house, "made_by", p.pop("made_by51", None) or "recipe")
        if why == "plan":
            o = p.get("own_made") or [None, 0]
            p["own_made"] = [house["clock"]["day"], (o[1] if o[0] == house["clock"]["day"] else 0) + 1]
    if p["sleep"]:
        p.pop("job_fit", None)
        return
    from . import body, planner
    awake = feel.level(p, "energy") < 3 and planner.slot(house, cfg) != "gather"
    fitting = awake and fits(house, cfg, p)
    p["job_fit"] = awake and bool(fitting or of(house, p))   # (the leisure set damped: a job it fits is open, or it has one)
    K.count(house, "awake", p["id"])
    now = body.state(p)["now"] or {}
    reading = (planner.current(p) or {}).get("from") == "question"   # (21 October 2026: the reading hour at a screen is a job, not idle)
    if fitting and now.get("name") in LEISURE and not reading:   # §3.4 idle: in leisure while a job it fits was open
        K.count(house, "idle", p["id"])
        if any(K.on53(cfg, x) for x in K.PARTS53) and (p.get("talking") or {}).get("until", -1) < house["tick"]:   # SPEC-v5.3 §7, §8: the reading hour out (as above), and a talk's rounds
            K.count(house, "idle53", p["id"])


def gathering(pet):
    """SPEC-v5.3 §7: its current aim is a gather aim, open (a plan's or a talk's, a habit's or a job's step)."""
    from . import planner
    a = planner.current(pet)
    return bool(a and a["kind"] == "gather" and not a.get("done") and not a.get("failed"))


def release(house, cfg, pet):
    """§7 a gather aim (the plan's or a talk's) whose step can't be reached, the bit lying in no room it knows (or the
    gathering in a room it doesn't), is blocked and let go: said, and the next aim is its own."""
    from . import planner
    a = planner.current(pet)
    if not gathering(pet) or a.get("job") or a.get("habit") or not a.get("target") or pet["sleep"]:
        return
    t = a["target"]
    if (t in pet["rooms"]) if t in house["rooms"] else (t in pet["carrying"] or planner.aim_room(house, cfg, pet, a)):
        return
    a["failed"], a["blocked"] = house["tick"], "there's no %s in the rooms you know" % t if t not in house["rooms"] else "you don't know the way there"
    add_event(house, pet, "you let it go for now: %s; %s" % (a["text"], a["blocked"]))


# ---- the planner's and the body's (§3.3, §3.4) ----

def weigh(house, cfg, pet, name, A, t, s):
    """body.score, last: the leisure set at `[jobs] leisure` of itself while a job it fits is open and it is not worn
    out nor at the evening's gathering; tidying, when its job is a mess with no broom to hand, pulls as an aim does."""
    a = pet.get("job_aim")
    if a and name == "tidy" and a["text"] and (of(house, pet) or {}).get("kind") == "mess" and pet["room"] == a.get("target"):
        s += cfg["planner"]["aim"]
    from . import sheet
    if name in LEISURE and (pet.get("job_fit") or (stages(cfg) and gathering(pet))) and not (sheet.on(cfg) and sheet.pursues(cfg, pet, name)):   # (24 November 2026: its pursuit is not idling)   # (SPEC-v5.3 §7: and while a gather aim is open)
        s -= (1 - cfg["jobs"]["leisure"]) * abs(s)
    return s


def keep(pet, j=None):
    """The bits its job is gathering, kept in its paws."""
    j = j or {}
    return {s["what"] for s in j.get("steps", []) if s["do"] in ("gather", "buy")} if j else set()


def keeping(house, pet):
    j = of(house, pet)
    return keep(pet, j) if j and j["kind"] != "works_goal" else set()


def why_make(house, cfg, pet, a, taught):
    """§3.3 why it would make now: ("job", the kind its job's step names), ("taught", the kind), ("plan", what the aim
    says), or (None, "") when nothing asked for it (and its own make for the day is spent)."""
    j = of(house, pet)
    s = step(j) if j else None
    if j and j.get("invent"):   # (SPEC-v5.1 §4.4: an invention is made at its station by the engine, and nothing else meanwhile)
        return None, ""
    if s and s["do"] == "make":
        return "job", s["what"]
    if (taught or {}).get("until", 0) > house["tick"]:
        return "taught", taught["kind"]
    o = pet.get("own_made") or [None, 0]
    if a and a.get("kind") == "make" and a.get("for") and (o[1] if o[0] == house["clock"]["day"] else 0) < cfg["jobs"]["own_make_per_day"]:
        d = next((d for d in board(house)["deficits"] if d["words"] == a["for"]), None)
        fixes = " ".join(makeable(house, cfg, NEEDS[d["kind"]][0], NEEDS[d["kind"]][1])[:3]) if d and d["kind"] in NEEDS else ""
        return "plan", "%s %s %s" % (a.get("text", ""), a["for"], fixes)
    return None, ""


def cannot(house, pet, words):
    """planner.make could not make its job's kind: the job's step fails with why."""
    j = of(house, pet)
    if j:
        j["why"] = words


def made_up(house, cfg, pet):
    """Has it made its own thing today (planner.check: a plan's make aim is then done)?"""
    o = pet.get("own_made") or [None, 0]
    return (o[1] if o[0] == house["clock"]["day"] else 0) >= cfg["jobs"]["own_make_per_day"]


# ---- the model's part (§3.5) ----

def open_words(house, pet):
    """The jobs a plan may name (to take or refuse): open ones not refused today, and its own."""
    r = pet.get("refused5") or {}
    out = [j["words"] for j in board(house)["jobs"] if (j["state"] == "open" and not (r.get("day") == house["clock"]["day"] and j["deficit"] in r.get("ids", [])))
           or j["taker"] == pet["id"]]
    return list(dict.fromkeys(w[:120] for w in out))[:8]


def for_words(house, pet):
    """What a make may be for: a deficit, a hob, to sell, a gift, for itself."""
    hobs = [label(p) for p in house["pets"].values() if p is not pet and p["stage"] not in ("egg", "dead")]
    return list(dict.fromkeys([d["words"] for d in board(house)["deficits"]][:6] + hobs[:6] + ["to sell", "a gift", "for myself"]))


def ask(house, cfg, pet, take_words, refuse_words):
    """The plan's reply: a job it takes (if it may), a job it refuses (not offered it again today; let go if its own)."""
    B = board(house)
    if refuse_words:
        for j in [j for j in B["jobs"] if j["words"][:120] == refuse_words[:120]]:
            refuse(house, pet, j)
    if take_words and free_hob(house, cfg, pet):
        j = next((j for j in B["jobs"] if j["state"] == "open" and j["words"][:120] == take_words[:120] and score(house, cfg, pet, j) > 0), None)   # (not one it would never: its fit is nothing)
        if j:
            take(house, cfg, pet, j)


def refuse(house, pet, j):
    """Not offered it again today; let go if its own."""
    r = pet.get("refused5") or {}
    pet["refused5"] = {"day": house["clock"]["day"], "ids": (r.get("ids", []) if r.get("day") == house["clock"]["day"] else []) + [j["deficit"]]}
    if j["taker"] == pet["id"]:
        leave(house, pet, j)


# ---- nursing is a decision, not a gap (21 October 2026; switch [jobs] ask_nurse) ----

def gravity(p):
    """How ill or hurt it is, tended today or not (health.need_of's measure without the day's tending): 0 when well."""
    from . import health
    s, h = health.stage_of(p), (p.get("hurt") or {}).get("level")
    return max((health.SICK.index(s) + 1) / 3 if s else 0.0, (0.8 if h == "badly hurt" else 0.4) if h in health.HURT[1:] else 0.0)


def ask_nurse(house, cfg, B):
    """A sick hob whose sick_untended job nobody has taken: every grown hob is told so plainly (a reaction, URGENT in
    brain4) and answers, when it first has no nurse and again each time it gets worse, not once a day. Nothing makes
    it say yes: the answer is its character's (nurse_answer)."""
    from . import brain4
    from .machine import listed
    for p in house["pets"].values():
        if "nurse_asked5" in p and not gravity(p):
            p.pop("nurse_asked5")
    for d in B["deficits"]:
        p = house["pets"].get(d.get("who") or "") if d["kind"] == "sick_untended" else None
        if not p or gravity(p) <= p.get("nurse_asked5", 0) or any(j["deficit"] == d["id"] and j["taker"] for j in B["jobs"]):
            continue
        p["nurse_asked5"] = gravity(p)
        qs = [q for q in house["pets"].values() if q is not p and q["stage"] in ("adult", "elder")]
        for q in qs:
            others = sorted(label(x) for x in qs if x is not q)
            who = "you are the only grown hob who can nurse it" if not others else "you and %s are the grown hobs who can nurse it" % listed(others)
            brain4.notable(house, cfg, q, "nurse", "%s is %s in %s; %s" % (label(p), "ill" if p.get("sick") else "hurt", deficits.place(house, p["room"]), who), [p["id"]])


def nurse_answer(house, cfg, pet, e, yes):
    """Its answer to being asked to nurse: yes takes the job (or, busy with another, a nurse aim); no is a decision,
    kept by both (weight 4) and seen by the house."""
    p = house["pets"].get((e.get("about") or [""])[0])
    if not p or p["stage"] in ("egg", "dead"):
        return
    j = next((j for j in board(house)["jobs"] if j["kind"] == "sick_untended" and (deficit_of(house, j) or {}).get("who") == p["id"]), None)
    if yes:
        if j and j["state"] == "open" and free_hob(house, cfg, pet) and take(house, cfg, pet, j):
            return
        if not any(a["kind"] == "nurse" and a.get("target") == p["id"] and not a.get("done") for a in pet.get("aims") or []):
            pet["aims"] = (pet.get("aims") or []) + [{"text": "nurse %s" % label(p), "why": e["text"], "kind": "nurse", "target": p["id"],
                                                      "since": None, "done": False, "made0": pet.get("made", 0)}]
        return
    from . import memories
    from .world import moment
    memories.remember(house, cfg, pet, "I left %s lying there" % label(p), 4, "refusal", [p["id"]])
    memories.remember(house, cfg, p, "%s left me lying there when I was %s" % (label(pet), "ill" if p.get("sick") else "hurt"), 4, "refusal", [pet["id"]])
    moment(house, "would not nurse", "%s would not nurse %s" % (label(pet), label(p)), pet["id"], p["room"])
    if j:
        refuse(house, pet, j)


def step_words(house, cfg, pet, j):
    s = step(j)
    if not s:
        return "it is nearly done"
    room = lambda r: house["rooms"][r]["name"] if r in house["rooms"] else "the house"
    if s["do"] == "get":
        return "the %s in %s will do: fetch it" % (s["what"], room(s["where"]))
    if s["do"] == "gather":
        return "you need %s, there's %s in %s" % (s["what"], s["what"], room(s["where"]))
    if s["do"] == "buy":
        return "you need %s, and the machine in %s sells it" % (s["what"], room(s["where"]))
    if s["do"] == "make" and j.get("invent"):
        return "take it all to %s and make the %s" % (room(s["where"]), s["what"])
    if s["do"] == "make":
        return "make %s %s" % (cfg["kinds"].get(s["what"], {}).get("a", "a"), s["what"])
    if s["do"] == "inspect":
        return "go and see to the gate in %s" % room(s["where"])
    return "then see to it in %s" % room(s.get("where") or (house["pets"].get((deficit_of(house, j) or {}).get("who") or "") or {}).get("room"))


def line(house, cfg, pet):
    """API5: its plan packet's words: what the house needs today, and its job if it has one (§3.5)."""
    B, j = board(house), of(house, pet)
    if not B["deficits"] and not (j and j.get("invent")):   # (an invention is said with no wrong on the board)
        return ""
    out = "what the house needs today: " + "; ".join(d["words"] for d in B["deficits"][:5]) if B["deficits"] else ""
    if j:
        out += "\nyou're seeing to %s: %s" % (j["words"], step_words(house, cfg, pet, j))
    return out


def answer(house, cfg, pet):
    """The react packet's line: the world's answer to what it last did with a thing (within the hour)."""
    a = pet.get("answer5")
    return "what came of it: " + a[1] if a and house["tick"] - a[0] <= hours(cfg, 1) else ""
