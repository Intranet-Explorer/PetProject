"""SPEC-v4.0 §9 the new body: the activities scored by needs, the day's aims, traits, mood and routine; behaviours from
traits without a thought (behaviours.toml) (helper D). Switch: [planner] on (off: v3.6c's body, exactly).

The body (engine/body.py) was already a utility AI: every activity in activities.toml finds what it could be done
with in the room (body.targets: each object and place advertises what it offers) and is scored (body.score). The
planner adds to that score, never replaces it:
  - the day's aims (the morning plan, brain4.py): the activities that work on the current aim, and the door toward
    where it is done (lean), pull hard in the hours set aside for aims, and less in free time; an aim is done when
    the body has done it (`check`), and one not done in time has failed (a reaction);
  - routines: breakfast and lunch (the hasty skip breakfast; the social eat where the others are), the day's aims,
    free time (play), the evening gathering with kin and friends;
  - traits: behaviours.toml's behaviours, each at one pole of an axis (`pole`), done only by a hob toward that end;
  - mood: behaviours.toml [moods];
  - who its plan seeks out or avoids;
  - SPEC-v4.0 §6.2, housekeeping off their backs: the house's clearing and carrying (loading the train, clearing
    scrap) is not a hob's; only a tidy hob puts others' things away (grumbling, and scolding a messy owner); the rest
    put away only their own; a messy one leaves things where it stood (order.job's `only`, body.targets)."""
import tomllib

from . import actions, bonds, character, feats, feel, opinions, order, things
from . import contracts as K
from .world import LONG_AGO, STAGES, add_event, arrived, beside, dist, free_tile, here, hours, label, moment, relation, rnd

# an aim's kind -> (the activities' `do` that work on it, the focus it gives the body: actions.FOCUS)
AIM = {"make": (("gather", "bench", "lay out", "place", "try", "machine", "vend"), "make"),
       "build": (("build", "machine", "vend"), "project"),
       "design": (("bench", "gather", "vend"), "make"),   # (contracts.AIMS_V4 keeps it; SPEC-v5.1 §4.5: never offered, designing is gone)
       "fish": (("fish",), "project"),
       "cook": (("machine", "eat"), "project"),
       "tend": (("tend",), "tend"),
       "gather": (("gather",), "project"),
       "explore": (("go", "doorway", "peek", "inspect", "tail", "watch", "b:poke"), "explore"),
       "learn": (("place", "try", "listen", "inspect", "b:poke"), "explore"),
       "be with": (("follow", "sit with", "bring", "babble", "sing", "b:follow", "play"), "be with"),
       "help": (("follow", "sit with", "bring", "build", "b:share", "b:follow"), "be with"),
       "rest": (("nap", "window", "seat", "b:sunbeam"), "rest"),
       "play": (("play", "dance", "sing", "ride", "b:prank"), "play"),
       "vigil": (("b:grieve", "stone"), "stay near"),   # (conflict.py's, after a death: to the dead one's stone)
       # talk.py's aims (19 October 2026: an aim of a kind not here stopped that hob's mind each tick all night, 4,802 times)
       "plan": (("follow", "sit with", "bring", "build", "gather", "b:share", "b:follow"), "be with"),
       "give": (("bring", "b:share", "follow", "sit with"), "be with"),
       # SPEC-v4.2 §1.3 the stages' jobs (contracts.AIMS_NEW): a child asks, a youngling tries, an adult nurses (the nurse
       # activity is A's), an elder tells (its telling is D's: until then it sits with the little ones)
       "ask": (("follow", "sit with", "babble", "try"), "be with"),
       "try": (("try", "place", "inspect", "b:poke", "b:new"), "explore"),
       "nurse": (("nurse", "sit with", "bring", "b:pat"), "be with"),
       "tell": (("b:tell", "sit with", "babble", "sing", "b:lecture"), "be with"),   # (b:tell: activities.toml's `tell`, D's)
       "lay": (("nap", "seat", "window"), "rest"),   # (laying.py's, 20 October 2026: to the nursery, to rest there until the egg comes)
       # SPEC-v5.1 (helper B, contracts.AIMS51; "learn" is v4's, and with [book2] its question is looked up: wants.lean):
       # teach is time with the one taught (knowledge.done teaches at its end); study is the bench (knowledge.study_targets)
       "teach": (("sit with", "follow", "b:lecture", "babble"), "be with"),
       "study": (("b:study",), "explore")}
KINDS = tuple(k for k in AIM if k not in ("vigil", "plan", "give") + K.AIMS_NEW)   # (the kinds a plan may choose; v4.2's by stage: `feasible`)
JOBS = {"child": ("ask",), "youngling": ("try",), "adult": ("nurse",), "elder": ("nurse", "tell")}   # §1.3


JOB_AIM = {"job": ((), "project")}   # SPEC-v5.0 §3.1 a job's step that takes it somewhere (jobs.aim): the way there pulls, nothing else


def aim_of(kind):
    """The activities that work on an aim of this kind, and the body's focus: an aim of a kind not known works like help."""
    return AIM.get(kind) or JOB_AIM.get(kind) or AIM["help"]


def working(a, sl):
    """Is it the hours for this aim: the aims' and free time's; a job's, every waking hour but the evening's gathering."""
    return sl in ("aims", "free") or bool(a and a.get("job") and sl != "gather") or bool(a and a.get("evening53"))   # (SPEC-v5.3 §3: out to its shelter for the night)
EATS = ("eat", "b:serving", "b:push", "b:stash")
LEISURE = ("play", "seat", "window", "inspect", "wander", "doorway", "peek", "take out", "fiddle", "tail", "watch", "listen", "dance", "b:known")
LITTLE = ("hatchling", "child")
CORNERS = lambda cfg: [[0, 0], [cfg["W"] - 1, 0], [0, cfg["H"] - 1], [cfg["W"] - 1, cfg["H"] - 1]]


def on(cfg):
    return bool(cfg.get("planner", {}).get("on"))


def load(cfg, directory):
    """behaviours.toml, laid in beside the activities (marked, so a body with the planner off never does them), and its
    moods kept for `adjust`. (world.load_config)"""
    B = tomllib.loads((directory / "behaviours.toml").read_text())
    for n, A in B["behaviours"].items():
        cfg["activities"][n] = dict(A, behaviour=True)
    cfg.setdefault("planner", {})["moods"] = B.get("moods", {})
    return cfg


from . import sheet
HARSH = ("b:sneer", "b:push", "b:pocket", "b:serving", "b:stash", "b:lecture")   # (24 November 2026) behaviours [sheet] temper does not make stronger


def trait(pet, axis):
    return character.trait(pet, axis) if "temper" in pet else 0.0


def at_pole(cfg, pet, A):
    """May this hob do this behaviour at all: toward its pole, or in one of its moods (none named: anyone may)."""
    pole, moods = A.get("pole") or {}, A.get("mood") or []
    if not pole and not moods:
        return True
    least = cfg["planner"]["pole"]
    return any(trait(pet, ax) * sign >= least for ax, sign in pole.items()) or character.mood(pet) in moods


def tidy_scope(cfg, pet):
    """Whose things this hob puts away (§6.2): everyone's ("all") if it is tidy, its own (its id) if neither, none if messy."""
    t = trait(pet, "tidy")
    return "all" if t >= cfg["planner"]["pole"] else None if t <= -cfg["planner"]["pole"] else pet["id"]


# ---- the day: aims and routine ----

def current(pet):
    """The aim it works on now: a question from life to look up first (SPEC-v5.1 §6.3, wants.life: an hour at a screen,
    and the job waits), then its job's step (SPEC-v5.0 §3.1, jobs.aim: only while [jobs] is on), else the day's."""
    q = next((a for a in pet.get("aims") or [] if a.get("from") == "question" and a.get("ready") and not a.get("done") and not a.get("failed")), None)
    if q:
        return q
    if pet.get("job_aim"):
        return pet["job_aim"]
    return next((a for a in pet.get("aims") or [] if not a.get("done") and not a.get("failed")), None)


def feasible(house, cfg, pet):
    """The kinds of aim it could work on today, as the house is (the packet offers only these): fishing once it knows
    the pond, cooking once there is a stove, building while there is something to build, tending
    while something is planted, learning once it knows where the book is, being with or helping while there is anyone."""
    from . import cook, life
    from .pond import room_of
    known = [house["rooms"][r] for r in pet["rooms"] if house["rooms"][r]["type"]]
    pond, s = room_of(house, cfg), cook.stove(house)
    can = life.unlocked(house, pet["stage"])
    ok = {"make": "make" in can, "fish": bool(pond) and pond["id"] in pet["rooms"] and STAGES.index(pet["stage"]) >= STAGES.index("child"),
          "cook": bool(s) and s[0]["id"] in pet["rooms"],
          "build": any(w["what"] in ("build", "paint", "design") for w in pet.get("wants", [])),
          "design": False,   # SPEC-v5.1 §4.5: invent does through a make aim what a design did
          "tend": any(o.get("planted") for r in known for o in r["objects"].values()),
          "learn": any(learnable(house, o) for r in known for o in r["objects"].values()),
          "be with": len(here(house, pet)) + sum(p["room"] != pet["room"] for p in house["pets"].values() if p is not pet and p["stage"] not in ("egg", "dead")) > 0}
    ok["help"] = ok["be with"]
    from . import knowledge   # SPEC-v5.1 §5.3-5.4: with [knowledge] off, neither
    ok["teach"] = knowledge.on(cfg) and knowledge.lesson(house, cfg, pet)[0] is not None
    ok["study"] = knowledge.on(cfg) and pet["stage"] not in ("hatchling", "child") and any(o.get("fix", {}).get("bench") for r in known for o in r["objects"].values())
    out = [k for k in KINDS if ok.get(k, True)]
    if K.on(cfg):   # SPEC-v4.2 §1.3: what its stage is for
        others = [p for p in house["pets"].values() if p is not pet and p["stage"] not in ("egg", "dead")]
        job = {"ask": any(p["stage"] in ("youngling", "adult", "elder") for p in others), "try": True,
               "nurse": bool(patients(house, cfg, pet)), "tell": any(p["stage"] in LITTLE for p in others)}
        out += [k for k in JOBS.get(pet["stage"], ()) if job[k]]
    return out


def patients(house, cfg, pet):
    """Who it could nurse here (A's health.patients: nothing while [deaths] is off)."""
    from . import health
    return health.patients(house, cfg, pet)


def learnable(house, o):
    """What a "learn" aim is met by a close look at (inspect, b:poke): the book or a lit screen, a thing with a title, a
    machine (19 October 2026: only trying a bit, or reading, counted, and a learn aim was almost never done)."""
    from . import hub, machines
    if not o:
        return False
    return bool(hub.heavy(o) or (o.get("fix", {}).get("book") and arrived(house, "book")) or (o.get("made") or {}).get("recipe", {}).get("title") or machines.key_of(o))


def seconds(cfg, pet, A, lo, hi):
    """body.choose: how long an activity lasts. At the current aim's work it keeps at it longer, the patient longest
    (§1.1: the patient finish long projects; the hasty rush and abandon them)."""
    a = current(pet)
    if a and A["do"] in aim_of(a["kind"])[0] and not A.get("fidget"):
        k = cfg["planner"]["keep_at"] * (1.0 + 0.5 * trait(pet, "patient"))
        return lo * k, hi * k
    return lo, hi


def slot(house, cfg):
    """Where the waking day is: breakfast, aims, lunch, free, gather."""
    hr = house["clock"]["hour"]
    for name, (lo, hi) in cfg["planner"]["routine"].items():
        if lo <= hr < hi:
            return name
    return "aims"


def hungry(pet, least=2):
    n = "hunger" if "hunger" in pet["needs"] else "energy"
    return feel.level(pet, n) >= least


def aim_room(house, cfg, pet, a):
    """The room an aim takes it to, if it names or needs one it knows."""
    t = a.get("target")
    if t in house["rooms"] and t in pet["rooms"]:
        return t
    who = house["pets"].get(t or "")
    if who and who["stage"] not in ("egg", "dead") and who["room"] in pet["rooms"]:
        return who["room"]
    if a["kind"] == "vigil":   # SPEC-v4.0 §7.4 (conflict.py): the room with the dead one's stone
        return next((rid for rid in pet["rooms"] for o in house["rooms"][rid].get("objects", {}).values() if (o.get("memorial") or {}).get("pet") == t), None)
    if a["kind"] == "fish":
        from .pond import room_of
        r = room_of(house, cfg)
        return r["id"] if r and r["id"] in pet["rooms"] else None
    if a["kind"] == "gather" and t:
        return next((rid for rid in pet["rooms"] if any(s["bit"] == t and s["ready"] for s in house["rooms"][rid].get("spots", []))), None)
    if a["kind"] == "learn":
        return next((rid for rid in [pet["room"]] + list(pet["rooms"]) if any(learnable(house, o) for o in house["rooms"][rid].get("objects", {}).values())), None)
    return None


def toward(house, cfg, pet):
    """The door toward the current aim's room, in the hours for aims and free time, or None."""
    from .body import way_to
    a = current(pet)
    rid = aim_room(house, cfg, pet, a) if a and working(a, slot(house, cfg)) else None
    return way_to(house, pet, {rid}) if rid and rid != pet["room"] else None


def lean(house, cfg, pet, L):
    """body.targets, after wants.lean: the rooms the day calls it to (the current aim's, in its hours; kin and friends
    in the evening; where food is, when hungry at a meal)."""
    sl, a = slot(house, cfg), current(pet)
    if a and working(a, sl):
        L["rooms"].add(aim_room(house, cfg, pet, a))
    if sl == "gather" and trait(pet, "social") > -cfg["planner"]["pole"]:
        count = {}
        for p in house["pets"].values():
            if p["id"] != pet["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"] and p["room"] in pet["rooms"] and (relation(house, pet, p) or friend(house, pet, p)):
                count[p["room"]] = count.get(p["room"], 0) + 1
        if count:
            L["rooms"].add(max(count, key=count.get))
    if a and (a.get("job") or a.get("habit") or (K.on5(cfg, "jobs") and cfg["jobs"].get("stages"))) and a["kind"] == "gather" and a.get("target") and a["target"] not in house["rooms"]:   # SPEC-v5.0 §3.1: the bit its job's step gathers (SPEC-v5.3 §7: or its plan's)
        L["gather"].add(a["target"])
    if a and a["kind"] == "learn" and sl in ("aims", "free"):   # (a close look at what it could learn from, here)
        objs = house["rooms"][pet["room"]]["objects"]
        L["look"].add(min((n for n, o in objs.items() if learnable(house, o)), key=lambda n: (dist(pet["pos"], objs[n]["pos"]), n), default=None))
        L["look"].discard(None)
    if (pet.get("focus") or {}).get("type") == "make" and len(pet["carrying"]) < cfg["body"]["make_bits"] and not any(sp["ready"] and not sp.get("on") for sp in house["rooms"][pet["room"]]["spots"]):
        L["rooms"].add(next((rid for rid in pet["rooms"] if any(sp["ready"] and not sp.get("on") for sp in house["rooms"][rid].get("spots", []))), None))   # (making, with nothing to make with here: where there is)
    if sl in ("breakfast", "lunch") and hungry(pet, 1) and not food(house["rooms"][pet["room"]]):
        L["rooms"].add(next((rid for rid in pet["rooms"] if food(house["rooms"][rid])), None))
    L["rooms"].discard(None)
    L["rooms"].discard(pet["room"])


def did(house, pet, now, done):
    """body.finish: what the body did, kept a while so an aim can be seen done."""
    if done:
        near = [p["id"] for p in here(house, pet, awake=True)]
        learnt = now["do"] in ("inspect", "b:poke") and learnable(house, house["rooms"][pet["room"]]["objects"].get(now.get("what") or ""))
        pet["did4"] = (pet.get("did4", []) + [[house["tick"], now["name"], now["do"], now.get("what"), now.get("who"), house["tick"] - now["since"], near, learnt]])[-60:]
    if pet.get("pressed"):   # SPEC-v4.2 §5.1-5.2: the beliefs that bore on the choice held, or were acted against
        from . import hooks
        hooks.verdict(house, pet, now if done else None)


def aim_done(house, cfg, pet, a):
    """Has the body (or the mind) done what the aim is about since it was set? The engine judges, never the model."""
    k, since, t = a["kind"], a["since"], a.get("target")
    if k == "vigil" or since is None:
        return False   # (conflict.py says when a vigil is kept; an aim not yet begun is not done)
    log, most = [x for x in pet.get("did4", []) if x[0] >= since and x[2] in aim_of(k)[0]], hours(cfg, cfg["planner"]["aim_work_hours"])
    spent = lambda xs: sum(x[5] for x in xs if len(x) > 5)   # (a day's aim is a good while's work, not one go at it)
    if k == "lay":   # (laying.py's: the egg is laid)
        return pet["eggs"] > a.get("eggs0", pet["eggs"])
    if k == "try":   # SPEC-v4.2 §1.3: a youngling's try is one go at something new
        return any(x[2] == "try" for x in log)
    if k == "study":   # SPEC-v5.1 §5.3: a thing studied through
        return pet.get("studied_at", LONG_AGO) >= since
    if k in ("be with", "help", "plan", "give", "ask", "nurse", "tell", "teach") and t in house["pets"]:   # time in its company, whatever they were at, and what was done with it
        return spent([x for x in pet.get("did4", []) if x[0] >= since and len(x) > 6 and t in x[6]]) + spent([x for x in log if t in (x[3], x[4])]) >= most
    if k in ("be with", "help"):
        return spent(log) >= most
    if k == "explore" and t in house["rooms"]:
        return pet["rooms"].get(t, LONG_AGO) >= since and spent(log) >= most / 2
    if k == "make" and K.on5(cfg, "jobs"):   # SPEC-v5.0 §3.3: a make the plan gives no reason for is no aim; one made, done
        from . import jobs
        return not a.get("for") or jobs.made_up(house, cfg, pet)
    if k == "make":
        return pet.get("made", 0) - a.get("made0", 0) >= 2 or (pet.get("last_made") or {}).get("tick", LONG_AGO) >= since and spent(log) >= most
    if k == "learn" and a.get("from") == "question":   # (SPEC-v5.1 §6.3, wants.life: a question from life is done when it is read)
        return a["question"].lower() in [q.lower() for q in pet.get("asked", [])] or any(r.get("tick", LONG_AGO) >= since and r.get("question") == a["question"] for r in pet.get("read", [])[:1])
    if k == "learn":
        return any(x[2] in ("try", "place", "listen") or (len(x) > 7 and x[7]) for x in log) or any(r.get("tick", LONG_AGO) >= since for r in pet.get("read", [])[:1])
    if k == "gather" and t in house["rooms"]:   # (talk.py's: to a gathering, in that room)
        return pet["room"] == t
    if k == "gather" and t:
        return t in pet["carrying"] or any(x[3] == t for x in log)
    return spent(log) >= most


def check(house, cfg, pet):
    """The day's aims looked over (brain4.wants_thought, each tick): done, failed (too long, or what it named is gone),
    and the body's focus kept on the current one. Returns a notable event for a reaction, or None."""
    from . import brain4
    aims, out, tick = pet.get("aims") or [], None, house["tick"]
    # (19 October 2026: an aim's clock starts when it becomes the one worked on, and runs only in the hours for aims and
    # free time: all of them were clocked from the morning plan, and the second and third failed by noon unbegun)
    cur = current(pet)
    for a in aims:
        if a is not cur:
            a.pop("checked", None)
    if cur and cur.get("since") is not None:
        if slot(house, cfg) in ("aims", "free"):
            cur["worked"] = cur.get("worked", 0) + tick - cur.get("checked", tick)
        cur["checked"] = tick
    for a in aims:
        if a.get("done") or a.get("failed"):
            continue
        who = house["pets"].get(a.get("target") or "") if a["kind"] != "vigil" else None
        if aim_done(house, cfg, pet, a):
            a["done"] = house["tick"]
            if a["kind"] == "teach":   # SPEC-v5.1 §5.4: the while together spent, it shows it how
                from . import knowledge
                knowledge.done(house, cfg, pet, a)
            if a.get("habit"):   # SPEC-v5.3 §1.2 (helper B): a habit's go finished (the pile grows, the box fills ...)
                from . import habits
                habits.done(house, cfg, pet, a)
            add_event(house, pet, "you have done what you meant to: %s" % a["text"])
            actions.bump(pet, cfg, dict(cfg["wants"]["lift"]))
        elif (a is cur and a.get("worked", 0) >= hours(cfg, cfg["brain4"]["aim_hours"])) or (who and who["stage"] == "dead"):
            a["failed"] = house["tick"]
            if not a.get("habit"):   # (SPEC-v5.3: a habit's go not come about is no news: no thought is asked for it)
                out = out or brain4.notable(house, cfg, pet, "plan failed", "you meant to %s, and it has not come about" % a["text"], [a["target"]] if who else [])
        if (a.get("done") or a.get("failed")) and K.on(cfg):
            over(house, cfg, pet, a, who)
    if aims and all(a.get("done") or a.get("failed") for a in aims) and pet.get("aims_over") != pet.get("planned"):
        pet["aims_over"] = pet.get("planned")
        out = out or brain4.notable(house, cfg, pet, "plan done", "the things you meant to do today are behind you")
    cur = current(pet)
    if cur and cur.get("since") is None:
        cur["since"], cur["checked"] = tick, tick
    focus(house, cfg, pet)
    return out


def over(house, cfg, pet, a, who):
    """SPEC-v4.2: an aim just done or failed leaves what it was worth: a child's question its answer (§1.3: what the one
    it asked remembers of the thing, a memory with content), the visitor's suggestion how it went (§5.5)."""
    from . import memories
    if a["kind"] == "ask" and a.get("done") and who:
        _, where, what = memories.tag(house, a["text"], cfg)
        told = memories.relevant(house, cfg, who, where=where, what=what, n=1) if memories.on2(cfg) else memories.relevant(house, cfg, who, n=1)
        memories.add(house, cfg, pet, "I meant to %s, and %s told me: %s" % (a["text"], label(who), told[-1]["text"] if told else "it did not know"), 3, [who["id"]], "told")
    if a.get("from") in ("visitor", "taught", "answer"):
        memories.add(house, cfg, pet, "I did what the visitor asked, %s, and it was good" % a["text"] if a.get("done") else "I meant to do what the visitor asked, %s, and it came to nothing" % a["text"], 3, ["visitor"], "visitor")


def planner_work(house, cfg, pet):
    from . import life
    return on(cfg) and pet.get("aims") and slot(house, cfg) == "aims" and "make" in life.unlocked(house, pet["stage"])


def focus(house, cfg, pet):
    """The body's focus (SPEC-v3.3 §1.2, which body.py already works toward) is the current aim."""
    a = current(pet)
    if not a and planner_work(house, cfg, pet) and not K.on5(cfg, "jobs"):   # (SPEC-v5.0 §3.3: with jobs, nothing is made for nothing)   # the aims are done, and there are hours left for them: it makes something useful
        a = {"kind": "make", "text": "make something useful", "since": -1, "target": None}
    if not a:
        if (pet.get("focus") or {}).get("aim"):
            pet["focus"] = None
        return
    f = pet.get("focus") or {}
    if f.get("aim") == a["since"] and f.get("words") == a["text"][:70]:
        return
    t = a.get("target")
    room = house["rooms"][pet["room"]]
    pet["focus"] = {"type": aim_of(a["kind"])[1], "words": a["text"][:70], "since": house["tick"], "aim": a["since"],
                    "who": t if t in house["pets"] else None, "what": t if t in room["objects"] else None}


# ---- the score ----

def adjust(house, cfg, pet, name, A, t):
    """What the planner adds to body.score for this activity and target."""
    Q, do, s = cfg["planner"], A["do"], 0.0
    sl, a, mood = slot(house, cfg), current(pet), character.mood(pet)
    from . import sheet
    for ax, w in (A.get("traits") or {}).items():   # a behaviour pulls the harder the further toward its pole
        s += (1.0 if do in HARSH else sheet.scale(cfg)) * w * trait(pet, ax)   # (24 November 2026: times [sheet] temper, but not what is done to hurt or to take: the house had sneered itself worthless)
    lean_ = Q["moods"].get(mood, {})
    s += lean_.get(do, 0.0) + lean_.get(name, 0.0)
    if a and working(a, sl) and do in aim_of(a["kind"])[0]:
        s += Q["aim"] * (1.0 if sl == "aims" else 0.5) * (1.0 + 0.25 * trait(pet, "patient"))
        tg = a.get("target")
        if tg and tg in (t.get("what"), t.get("who")):
            s += Q["aim_target"]
    elif sl == "aims" and (A.get("passive") or do in LEISURE) and not (A.get("rest") and feel.level(pet, "energy") >= 2):
        s -= Q["leisure"]   # the hours for the day's aims are not for sitting about (that is free time's)
    if do == "go" and t.get("bonus") and a and working(a, sl):
        s += 0.5 * Q["aim"]   # (a door wants.lean leads toward: the aim's room among them)
    if do == "go" and a and a.get("job") and t.get("what") and t["what"] == toward(house, cfg, pet):
        s += Q["aim"]   # SPEC-v5.0 §3.1: the way to where its job's step is
    if do in EATS or name == "eat from the pot":
        if "hunger" in pet["needs"]:
            s += Q["hunger"] * feel.level(pet, "hunger") / 4
        if sl == "lunch" or (sl == "breakfast" and trait(pet, "patient") > -Q["pole"]):   # the hasty skip breakfast
            s += Q["meal"]
        if sl in ("breakfast", "lunch") and trait(pet, "social") >= Q["pole"] and here(house, pet, awake=True):
            s += Q["together"]   # the social eat together
    if sl == "free" and do in ("play", "sing", "dance", "babble", "b:prank"):
        s += Q["free"] * (1.0 + trait(pet, "playful"))
    if sl == "gather" and do in ("sit with", "follow", "b:follow", "babble", "sing"):
        s += Q["gather"] * (1.0 + trait(pet, "social")) / 2
    who = t.get("who")
    if who and who in (pet.get("seek") or []):
        s += sheet.seek(cfg) * Q["seek"]
    elif who and who in (pet.get("avoid") or []):
        s -= sheet.seek(cfg) * Q["seek"] * 2
    if do == "go" and pet.get("seek"):   # (18 October 2026: seeking someone out took a hob nowhere: a door toward the room it is in)
        from . import body
        rooms = {house["pets"][x]["room"] for x in pet["seek"] if x in house["pets"] and house["pets"][x]["stage"] not in ("egg", "dead")} - {pet["room"]}
        if rooms and t.get("what") == body.way_to(house, pet, rooms):
            s += sheet.seek(cfg) * Q["seek"]
    if do == "go" and t.get("what") in house["rooms"][pet["room"]]["doors"] and pet.get("avoid"):   # (not into a room where one it avoids is: conflict.py's shunned and cold too)
        rid = house["rooms"][pet["room"]]["doors"][t["what"]]
        if any(house["pets"].get(x, {}).get("room") == rid for x in pet["avoid"]):
            s -= sheet.seek(cfg) * Q["seek"] * 2
    if name == "take out":
        s -= Q["take_out"] * (1.0 - max(0.0, trait(pet, "curious")))
    # SPEC-v4.2 A: nursing and raising (§2.2, §1.3): a patient by its need, the nurse's kindness and their bond, a little one more; a door toward one in need
    if do in ("nurse", "go"):
        from . import health
        s += health.nurse_pull(house, cfg, pet, do, t)
    # SPEC-v4.2 A: end
    if pet.get("hooked"):   # SPEC-v4.2 §5.1: its beliefs' hooks ([hooks])
        from . import hooks
        s += hooks.score(house, cfg, pet, name, t, A)
    # SPEC-v4.2 C: what serves its drive, and what its flaw pulls at (§6.1, §6.2; nothing with [drives] off)
    if pet.get("drive") or pet.get("flaw"):
        from . import drives
        s += drives.score(house, cfg, pet, name, A, t)
    # SPEC-v4.2 C: end
    return s


# ---- behaviours: what each finds (body.targets) and does (body.finish) ----

def food(room):
    """What can be eaten from here now: [name] (a bowl with servings, the pot on the stove)."""
    return [n for n, o in room["objects"].items() if ("meal" in o.get("fix", {}) and o.get("servings")) or (o.get("pot") or {}).get("servings")]


def eating_at(house, pet, n):
    """Another hob eating at this food just now."""
    from .body import state
    for p in here(house, pet, awake=True):
        now = state(p)["now"] or {}
        if (now.get("do") in EATS or now.get("name") == "eat from the pot") and now.get("what") == n and now.get("began") is not None:
            return p
    return None


def friend(house, pet, other):
    return bonds.kind(house, pet["id"], other["id"]) in ("friend", "close") or opinions.of(pet, other["id"]).get("liking", 0) >= 5


def foe(house, pet, other):
    o = opinions.of(pet, other["id"])
    return bonds.kind(house, pet["id"], other["id"]) == "enemy" or o.get("liking", 0) <= -5 or o.get("fear", 0) >= 5


def stranger(house, pet, other):
    from .world import family
    return family(other) != family(pet) and other["id"] not in pet.get("met_hobs", [])


def lately(house, cfg, pet, key, n_hours=1.0):
    """Has it done this (to this one) in the last few world hours?"""
    return house["tick"] - pet.get("b4", {}).get(key, LONG_AGO) < hours(cfg, n_hours)


def mark(house, pet, key):
    b = pet.setdefault("b4", {})
    b[key] = house["tick"]
    if len(b) > 40:
        for k in sorted(b, key=b.get)[:10]:
            del b[k]


def corner_of(house, cfg, pet, room):
    """Its own corner here: where it sleeps, if it sleeps here, else the corner of the room nearest it."""
    if pet.get("sleeps_in") == room["id"] and pet.get("sleeps_at"):
        return list(pet["sleeps_at"])
    return free_tile(house, cfg, room, min(CORNERS(cfg), key=lambda t: dist(t, pet["pos"])))


def loved(house, pet, pid):
    dead = house["pets"].get(pid)
    return bool(dead) and (relation(house, pet, dead) is not None or opinions.of(pet, pid).get("liking", 0) >= 3)


def targets(house, cfg, pet, mem, name, A, near):
    """body.targets for a behaviour (`do` "b:..."): [] unless this hob may do it (at_pole) and the moment calls for it."""
    if not at_pole(cfg, pet, A):
        return []
    room, do, me = house["rooms"][pet["room"]], A["do"], pet["pos"]
    objs, others = room["objects"], here(house, pet, awake=True)
    if do == "b:wall":
        if order.edge(cfg, me) or lately(house, cfg, pet, "wall", 1):
            return []
        tiles = [[x, y] for x in range(cfg["W"]) for y in range(cfg["H"]) if order.edge(cfg, [x, y])]
        return [{"goal": free_tile(house, cfg, room, min(tiles, key=lambda t: (dist(t, me), t)))}]
    if do == "b:hide":
        came = lambda p: house["tick"] - p["rooms"].get(room["id"], LONG_AGO) <= hours(cfg, 0.25)   # (it has just come in)
        threat = next((p for p in others if came(p) and (foe(house, pet, p) or stranger(house, pet, p)) and not lately(house, cfg, pet, "hide " + p["id"], 2)), None)
        if not threat:
            return []
        return [{"who": threat["id"], "goal": free_tile(house, cfg, room, max(CORNERS(cfg), key=lambda t: dist(t, threat["pos"])))}]
    if do == "b:new":
        from . import machines
        new = [n for n, o in objs.items() if ("made" in o or machines.key_of(o) or o.get("fix", {}).get("toy") or o.get("fix", {}).get("radio"))
               and not o.get("on") and not o.get("wall") and not any(pet["times"].get(k + n) for k in ("use ", "body play ", "body seat ", "look "))]
        new.sort(key=lambda n: (not machines.key_of(objs[n]), dist(me, objs[n]["pos"])))
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in new[:1]]
    if do == "b:leave":
        from . import body, build
        if body.minded(pet) == "make" or body.laid_out(pet):
            return []
        keep = {w.get("bit") for w in pet.get("wants", [])} | build.keep(house, cfg, pet)
        if K.on5(cfg, "jobs"):   # SPEC-v5.0: nor what its job gathered
            from . import jobs
            keep |= jobs.keeping(house, pet)
        spare = [b for b in pet["carrying"] if b not in keep]
        return [{"what": spare[0]}] if spare else []
    fed = food(room)
    if do == "b:share":
        hungry_ = [p for p in others if hungry(p) and not lately(house, cfg, pet, "share " + p["id"], 2)]
        if not fed or not hungry_:
            return []
        p, n = min(hungry_, key=lambda p: dist(me, p["pos"])), fed[0]
        return [{"what": n, "who": p["id"], "goal": near(objs[n]["pos"]), "to": beside(cfg, p["pos"], objs[n]["pos"])}]
    if do == "b:serving":
        big = [n for n in fed if (objs[n].get("servings") or (objs[n].get("pot") or {}).get("servings", 0)) >= 2]
        return [{"what": big[0], "goal": near(objs[big[0]]["pos"])}] if big and hungry(pet, 1) else []
    if do == "b:stash":
        if hungry(pet, 2) and pet.get("stash"):
            return [{"what": "food you tucked away", "eat": True, "goal": near(corner_of(house, cfg, pet, room))}]
        if not fed or pet.get("stash", 0) >= 2 or hungry(pet, 2) or lately(house, cfg, pet, "stash", 3):
            return []
        return [{"what": fed[0], "goal": near(objs[fed[0]]["pos"]), "to": corner_of(house, cfg, pet, room)}]
    if do == "b:poke":
        looked = set(pet.get("looked", []))
        new = [n for n, o in objs.items() if "made" in o and o["made"]["owner"] != pet["id"] and n not in looked and not pet["times"].get("look " + n) and not o.get("on")]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in sorted(new, key=lambda n: dist(me, objs[n]["pos"]))[:1]]
    if do == "b:known":
        if lately(house, cfg, pet, "known", 2):
            return []
        used = [(pet["times"].get(k + n, 0), n) for n in objs for k in ("use ", "body play ", "body seat ") if pet["times"].get(k + n)]
        return [{"what": max(used)[1], "goal": near(objs[max(used)[1]]["pos"])}] if used else []
    if do == "b:follow":
        mates = [p for p in others if friend(house, pet, p) and dist(me, p["pos"]) > 2]
        return [{"who": p["id"], "goal": near(p["pos"])} for p in mates[:1]]
    if do == "b:alone":
        from .body import doors_open
        from .outdoors import barred
        if len(others) < 2 or not doors_open(house, cfg, pet):
            return []
        quiet = [d for d, rid in room["doors"].items() if rid in pet["rooms"] and house["rooms"][rid]["type"]
                 and house["shut"].get("%s|%s" % (room["id"], d), LONG_AGO) <= house["tick"] and not barred(house, cfg, pet, room["id"], d)
                 and not any(p["room"] == rid and p["stage"] not in ("egg", "dead") and not p["sleep"] for p in house["pets"].values())]
        return [{"what": d, "goal": list(house["door_tiles"][d])} for d in quiet[:1]]
    if do == "b:return":
        took = [n for n, o in things.made(room).items() if (o.get("pocketed") or {}).get("by") not in (None, pet["id"])]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in took[:1]]
    if do == "b:pocket":
        if others or lately(house, cfg, pet, "pocket", 6):
            return []
        loose = [n for n, o in things.on_floor(room).items() if o["made"]["owner"] not in (None, pet["id"]) and not o["made"].get("heirloom")
                 and not o.get("pocketed") and not o.get("home") and not order.cap(cfg, o) and not things.prop(cfg, o).get("fixed")
                 and house["pets"].get(o["made"]["owner"], {}).get("stage", "dead") != "dead"]
        if not loose:
            return []
        n = min(loose, key=lambda n: dist(me, objs[n]["pos"]))
        return [{"what": n, "goal": near(objs[n]["pos"]), "to": corner_of(house, cfg, pet, room)}]
    if do in ("b:wait", "b:push"):
        busy = [(n, eating_at(house, pet, n)) for n in fed] if hungry(pet, 1) else []
        return [{"what": n, "who": p["id"], "goal": near(objs[n]["pos"])} for n, p in busy if p][:1]
    if do == "b:prank":
        asleep = [p for p in here(house, pet) if p["sleep"] and p["stage"] not in ("egg", "dead") and not lately(house, cfg, pet, "prank " + p["id"], 6)]
        return [{"who": p["id"], "goal": near(p["pos"])} for p in asleep[:1]]
    if do == "b:lecture":
        from .body import state
        young = [p for p in others if p["stage"] in ("hatchling", "child", "youngling") and STAGES.index(p["stage"]) < STAGES.index(pet["stage"])
                 and (state(p)["now"] or {}).get("do") in ("play", "dance") and not lately(house, cfg, pet, "lecture " + p["id"], 3)]
        return [{"who": p["id"], "goal": near(p["pos"])} for p in young[:1]]
    # SPEC-v4.2 D: an elder's tale for the little ones, in the evening's gathering (§10.3: story.py)
    if do == "b:tell":
        from . import story
        return story.tell_targets(house, cfg, pet, near)
    # SPEC-v4.2 D: end
    if do == "b:study":   # SPEC-v5.1 §5.3 (helper B): at the bench, with a thing whose making it hasn't
        from . import knowledge
        return knowledge.study_targets(house, cfg, pet, near)
    if do == "b:strut":
        g = pet.get("glow")
        if feats.shine(cfg, house, g) < 2 or pet.get("strutted") == g["since"]:
            return []
        r = rnd(house, "strut", pet["id"], house["tick"])
        return [{"goal": free_tile(house, cfg, room, [r.randrange(2, cfg["W"] - 2), r.randrange(2, cfg["H"] - 2)])}]
    if do == "b:sunbeam":
        sun = [n for n, o in objs.items() if o.get("fix", {}).get("sun") or o.get("fix", {}).get("window")]
        if house["clock"]["phase"] != "day" or house["weather"] not in ("clear", "heat") or not sun:
            return []
        return [{"what": sun[0], "goal": near(objs[sun[0]]["pos"])}]
    if do == "b:pat":
        little = [p for p in others if p["stage"] in LITTLE and (feel.level(p, "comfort") >= 2 or character.mood(p) in ("sad", "afraid", "lonely"))
                  and not lately(house, cfg, pet, "pat " + p["id"], 1)]
        return [{"who": p["id"], "goal": near(p["pos"])} for p in little[:1]]
    if do == "b:sneer":
        disliked = [p for p in others if (opinions.of(pet, p["id"]).get("liking", 0) <= -3 or bonds.kind(house, pet["id"], p["id"]) in ("enemy", "rival"))
                    and not lately(house, cfg, pet, "sneer " + p["id"], cfg["sheet"]["sneer_hours"] if sheet.on(cfg) else 8)]   # (24 November 2026: once a day at the same hob)
        return [{"who": p["id"], "goal": near(p["pos"])} for p in disliked[:1]]
    if do == "b:grieve":
        stones = [n for n, o in objs.items() if "memorial" in o and loved(house, pet, o["memorial"]["pet"])]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in stones[:1]]
    if do == "b:quirk":
        q = pet.get("quirks") or []
        return [{"what": rnd(house, "quirk", pet["id"], house["tick"]).choice(q)}] if q else []
    return []


def move(house, cfg, pet, other, cause, why):
    """An opinion moved by a behaviour, by its cause in opinions.toml (the body's own causes are at its end)."""
    opinions.move(house, cfg, pet, other, cause, why)


def eat(house, cfg, pet, name):
    """It eats from this food (actions.use: a bowl's serving, the pot's)."""
    text, fx, _ = actions.use(house, cfg, pet, name)
    actions.bump(pet, cfg, {n: v for n, v in fx.items() if n in pet["needs"]})
    return text


def finish(mind, now, A):
    """body.finish for a behaviour: what it really did, now that it is over. Returns (what it did, in words, or None
    for the activity's own `did`; done)."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    room, do, n = h["rooms"][pet["room"]], A["do"], now.get("what")
    o = room["objects"].get(n or "")
    other = h["pets"].get(now.get("who") or "")
    near = bool(other) and other["room"] == pet["room"] and other["stage"] not in ("egg", "dead")
    who = label(pet)
    if do == "b:hide" and other:
        mark(h, pet, "hide " + other["id"])
        return None, True
    if do == "b:wall":
        mark(h, pet, "wall")
    if do in ("b:wall", "b:follow", "b:wait", "b:quirk", "b:strut") and not (do == "b:strut" and pet.get("glow")):
        return None, True
    if do == "b:strut":
        pet["strutted"] = pet["glow"]["since"]
        moment(h, "strut", "%s strutted about, proud: %s" % (who, pet["glow"]["why"].replace("you ", "it ", 1)), pet["id"], room["id"])
        return None, True
    if do == "b:new" and o is not None:
        text, fx, key = actions.use(h, cfg, pet, n)
        actions.bump(pet, cfg, {k: v for k, v in fx.items() if k in pet["needs"]})
        pet["times"]["use " + n] = pet["times"].get("use " + n, 0) + 1
        return "tried the %s for the first time: %s" % (n, text.removeprefix("you ")), True
    if do == "b:leave" and n in pet["carrying"]:
        pet["carrying"].remove(n)
        things.drop_bits(h, cfg, room, pet["pos"], [n])
        return None, True
    if do == "b:share" and o is not None and near and n in food(room):
        eat(h, cfg, other, n)
        mark(h, pet, "share " + other["id"])
        add_event(h, other, "%s brought you food from the %s" % (actions.handle(h, other, pet), n))
        move(h, cfg, other, pet["id"], "shared_food", "%s brought me food when I was hungry" % who)   # (and the memory: opinions.toml)
        moment(h, "shared", "%s brought %s food from the %s" % (who, label(other), n), pet["id"], room["id"])
        return None, True
    if do == "b:serving" and o is not None and n in food(room):
        eat(h, cfg, pet, n)
        if n in food(room):
            eat(h, cfg, pet, n)
        for p in here(h, pet, awake=True):
            add_event(h, p, "%s took the biggest serving from the %s" % (actions.handle(h, p, pet), n))
        return None, True
    if do == "b:stash":
        if now.get("eat") and pet.get("stash"):
            pet["stash"] -= 1
            actions.bump(pet, cfg, dict(cfg["effects"]["eat"], **({"hunger": cfg["effects"].get("eat_hunger", 25)} if "hunger" in pet["needs"] else {})))
            return "ate the food you had tucked away", True
        if o is not None and n in food(room):
            if "meal" in o.get("fix", {}):
                o["servings"] -= 1
                o["state"] = "empty" if not o["servings"] else "half"
            else:
                o["pot"]["servings"] -= 1
            pet["stash"] = pet.get("stash", 0) + 1
            mark(h, pet, "stash")
            return None, True
        return None, False
    if do == "b:poke" and o is not None:
        actions.look(h, cfg, pet, {"target": n})
        pet["looked"] = (pet.get("looked", []) + [n])[-60:]
        pet["times"]["look " + n] = pet["times"].get("look " + n, 0) + 1
        return None, True
    if do == "b:known" and o is not None:
        mark(h, pet, "known")
        text, fx, key = actions.use(h, cfg, pet, n)
        actions.bump(pet, cfg, {k: v for k, v in fx.items() if k in pet["needs"]})
        return None, True
    if do == "b:alone" and n in room["doors"] and actions.check({"type": "go", "door": n}, h, cfg, pet, mind.mem) is None:
        text, fx, key = actions.go(h, cfg, pet, n)
        add_event(h, pet, text)
        return None, True
    if do == "b:return" and o is not None and o.get("pocketed"):
        p = o.pop("pocketed")
        o["pos"] = free_tile(h, cfg, room, p["from"], n)
        owner = h["pets"].get(o["made"]["owner"])
        if owner and owner["stage"] != "dead":
            add_event(h, owner, "%s put your %s back where it was" % (actions.handle(h, owner, pet), n))
            move(h, cfg, owner, pet["id"], "returned_my_thing", "%s put my %s back" % (who, n))
        taker = h["pets"].get(p["by"])
        moment(h, "returned", "%s put %s's %s back, where %s had taken it from" % (who, label(owner) if owner else "someone", n, label(taker) if taker else "someone"), pet["id"], room["id"])
        return None, True
    if do == "b:pocket" and o is not None and not here(h, pet, awake=True):
        o["pocketed"] = {"by": pet["id"], "tick": h["tick"], "from": list(o["pos"])}
        order.moved(o, h["tick"], h, cfg, room, n)
        o["pos"] = free_tile(h, cfg, room, corner_of(h, cfg, pet, room), n)
        mark(h, pet, "pocket")
        moment(h, "pocketed", "%s pocketed %s's %s while nobody was looking" % (who, label(h["pets"][o["made"]["owner"]]), n), pet["id"], room["id"])
        return None, True
    if do == "b:push" and o is not None and n in food(room):
        eat(h, cfg, pet, n)
        if near:
            add_event(h, other, "%s pushed in at the %s" % (actions.handle(h, other, pet), n))
            move(h, cfg, other, pet["id"], "pushed_in", "%s pushed in ahead of me at the %s" % (who, n))
        return None, True
    if do == "b:prank" and other and other["sleep"] and other["room"] == pet["room"]:
        other.setdefault("on_wake", []).append("you woke with a feather on your nose: someone played a trick on you while you slept")
        mark(h, pet, "prank " + other["id"])
        moment(h, "prank", "%s put a feather on %s's nose as it slept" % (who, label(other)), pet["id"], room["id"])
        move(h, cfg, other, pet["id"], "pranked_me", "a feather on my nose while I slept")
        return None, True
    if do == "b:lecture" and near:
        add_event(h, other, '%s told you: "stop playing and do something useful"' % actions.handle(h, other, pet))
        mark(h, pet, "lecture " + other["id"])
        moment(h, "lecture", "%s told %s to stop playing and do something useful" % (who, label(other)), pet["id"], room["id"])
        return None, True
    if do == "b:sunbeam":
        actions.bump(pet, cfg, {"energy": cfg["effects"]["rest_per_10s"] * A["seconds"][1] / 10, "comfort": 1.0})
        return None, True
    if do == "b:pat" and near:
        actions.bump(other, cfg, {"comfort": 8.0})
        add_event(h, other, "%s gave you a pat" % actions.handle(h, other, pet))
        mark(h, pet, "pat " + other["id"])
        move(h, cfg, other, pet["id"], "comforted_me", "%s patted me when I was upset" % who)
        moment(h, "pat", "%s gave %s a pat" % (who, label(other)), pet["id"], room["id"])
        return None, True
    if do == "b:sneer" and near:
        from . import brain4
        said = "%s sneered at you in passing" % actions.handle(h, other, pet)
        add_event(h, other, said)
        mark(h, pet, "sneer " + other["id"])
        move(h, cfg, other, pet["id"], "laughed_at_me", "%s sneered at me" % who)
        brain4.notable(h, cfg, other, "insulted", said, [pet["id"]])
        moment(h, "sneer", "%s sneered at %s in passing" % (who, label(other)), pet["id"], room["id"])
        return None, True
    if do == "b:grieve" and o is not None:
        actions.bump(pet, cfg, dict(cfg["effects"]["stone"]))
        return None, True
    # SPEC-v4.2 D: the tale told (§10.3: story.py)
    if do == "b:tell" and near:
        from . import story
        did = story.tell(mind.eng, pet)
        return did, bool(did)
    # SPEC-v4.2 D: end
    if do == "b:study":   # SPEC-v5.1 §5.3 (helper B)
        from . import knowledge
        did = knowledge.studied(h, cfg, pet, now)
        return did, bool(did)
    return None, False


def tidied(house, cfg, pet, room, name):
    """body.finish, after the tidy activity put a thing away: a tidy hob putting another's thing away grumbles, and
    scolds the owner if the owner is messy and here (§6.2: a moment and an event, for the conversations to pick up)."""
    o = room["objects"].get(name) or {}
    owner = house["pets"].get(o.get("made", {}).get("owner") or "")
    if not owner or owner is pet or owner["stage"] in ("egg", "dead"):
        return
    from .body import voice
    voice(house, pet, "grumble")
    if trait(owner, "tidy") <= -cfg["planner"]["pole"] and owner["room"] == pet["room"] and not owner["sleep"] and not lately(house, cfg, pet, "scold " + owner["id"], 3):
        from . import brain4
        said = "%s scolded you for leaving your %s lying about" % (actions.handle(house, owner, pet), name)
        mark(house, pet, "scold " + owner["id"])
        add_event(house, owner, said)
        move(house, cfg, owner, pet["id"], "scolded_me", "%s scolded me over my %s" % (label(pet), name))
        brain4.notable(house, cfg, owner, "insulted", said, [pet["id"]])
        moment(house, "scold", "%s scolded %s for leaving the %s lying about" % (label(pet), label(owner), name), pet["id"], room["id"])


def put_down(house, cfg, pet):
    """Bits laid out that nothing is made of are put down where it stands (the tidy routine sees to them), so its
    body is free again: it stayed by them at the bench, gathering nothing and leaving nothing, for good (19 October
    2026, REVIEW-v4.0.4 C6)."""
    from . import body
    body.state(pet)["laid"] = None
    things.drop_bits(house, cfg, house["rooms"][pet["room"]], pet["pos"], pet["carrying"])
    add_event(house, pet, "you put down the %s: nothing came of them" % " and ".join(pet["carrying"]))
    pet["carrying"] = []


# ---- routine making (§8.1: "ready to make" no longer starts a thought; the body makes from the day's aims) ----

def make(mind):
    """Its bits are laid out (body.py "lay out the bits" set pet["ready"]): the body makes something now, without a
    thought: a kind the house could use or its aim names, else the one it has made least, in what it has to hand.
    It goes through the plan machinery as one decided step would. Returns True if it set about it."""
    from . import brain4, mind as mind_
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    pet["ready"] = None
    _, ctx = mind_.perceive(h, cfg, pet, mind.mem)
    most, reach = ctx["make"]
    can = [(m, k) for m in reach for k in ctx["kinds"].get(m, [])]
    if "make" not in ctx["allowed"] or not most or not can:
        return False   # (and the bits are put down: brain4.wants_thought, put_down)
    a = current(pet)
    taught = pet.get("taught_recipe") or {}
    if K.on5(cfg, "jobs"):   # SPEC-v5.0 §3.3: making is a job's step, a plan's reason or the visitor's teaching; never for nothing
        from . import craft, jobs
        why, want = jobs.why_make(h, cfg, pet, a, taught)
        if not why:
            return False
        if why == "job":
            can = [(m, k) for m, k in can if k == want]
            if not can:
                jobs.cannot(h, pet, "you couldn't make %s %s of what you carry: it takes %s" % (cfg["kinds"].get(want, {}).get("a", "a"), want, craft.takes(cfg, want) or "something it can be made of"))
                return False
        pet["make_for"] = why
    else:
        want = " ".join(things.better(h, cfg, pet) + [(a or {}).get("text", "")]).lower()
        if taught.get("until", 0) > h["tick"]:   # SPEC-v4.2 §5.3: a recipe the visitor taught is what it makes, for a day
            want = taught["kind"]
    want = want.lower()
    want += " " + " ".join(b["hook"]["arg"] for b in pet.get("hooked") or [] if b["hook"]["name"] == "make" and not b.get("doubted"))   # §5.1
    r = rnd(h, "make4", pet["id"], h["tick"])
    m, k = min(can, key=lambda mk: (mk[1] not in want, pet["times"].get("kind " + mk[1], 0), r.random()))
    step = {"type": "make", "near": "here", "recipe": {"kind": k, "material": m, "color": r.choice(things.COLORS), "size": things.SIZES[min(most, 2) - 1],
                                                         "name": "%s %s" % (m, k), "purpose": (a["text"] if a else "for the house")[:80]}}
    brain4.start_plan(mind, "", "make %s %s %s" % (cfg["kinds"].get(k, {}).get("a", "a"), m, k), [step], "ready to make")
    return True
