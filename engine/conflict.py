"""SPEC-v4.0 §7 conflict (helper C): the ladder, witnesses, coming down, a killing and what follows it, stepping in.
Switch: [ladder] on; the numbers are in conflict.toml.

house["grievances"]: [{"by", "against", "why", "since", "rung", "history": [[tick, rung, what]], ...}]: `by` holds it,
and climbs the ladder against `against`, one rung a step: 1 snub, 2 insult (both in conversations, talk.py, while
[talk] is on), 3 sabotage, 4 theft (through the things and actions the house already has), 5 shove, 6 fight, 7 grave
harm, 8 killing (a short scuffle, then health.py and the engine's own death). Every step needs a reason (a grievance is
only opened with one), and is decided here from both hobs' traits, moods, opinions and the situation; the brain gives
only feelings and intent (pet["intent"] = {"against", "how"}). Grievances come down by making up (an apology, a gift,
a hob talking them down), or by time apart, ending in peace or a lasting coldness (pet["avoid"]).

A killing (house["killings"]) is told by its witnesses (a sly one may lie), or worked out in time; the dead's friends,
bond and kin grieve and keep a vigil; the house is afraid, most near the killer; the family judges it (shunned, driven
out to the meadow as an outcast, forgiven, or nothing); kin and friends of the dead take vengeance, and the family keeps
it as a legend. The visitor may step in: stop_fight, protect, judge.

Switched off: no rung from 3 up happens (and the engine says no snubs or insults); grievances only cool; a scuffle
under way ends; outcasts are let in (outdoors.come_in) and nothing else of a killing's aftermath moves."""
import tomllib

from . import bonds, character, craft, health, memories, needs, opinions, outdoors, talk, things
from . import contracts   # SPEC-v4.2
from .world import ROOT, add_event, beside, family, free_tile, here, label, moment, rnd, ticks

LITTLE = ("hatchling", "child", "youngling")
NAMES = ("", "snub", "insult", "sabotage", "theft", "shove", "fight", "harm", "killing")   # moment kinds (PLAN.md)
POLES = {"sly": ("honest", -1), "prickly": ("kind", -1), "greedy": ("generous", -1), "timid": ("brave", -1),
         "kind": ("kind", 1), "brave": ("brave", 1), "honest": ("honest", 1), "generous": ("generous", 1)}
VERDICTS = {"pardon": "forgiven", "forgive": "forgiven", "forgiven": "forgiven", "shun": "shunned", "shunned": "shunned",
            "drive out": "driven out", "driven out": "driven out", "nothing": "nothing"}


def on(cfg):
    return bool(cfg.get("ladder", {}).get("on"))


def C(cfg):
    if "conflict" not in cfg:   # (read once, beside config.toml)
        cfg["conflict"] = tomllib.loads((ROOT / "conflict.toml").read_text())
    return cfg["conflict"]


def is_(cfg, pet, word):
    """Is it at that pole: sly, prickly, greedy, timid, kind, brave, honest, generous?"""
    axis, sign = POLES[word]
    return sign * character.trait(pet, axis) >= C(cfg)["ladder"]["pole"]


def alive(p):
    return bool(p) and p["stage"] not in ("egg", "dead")


def awake_here(house, pet, but=()):
    return [p for p in here(house, pet, awake=True) if p["id"] not in but]


def kin(house, p, q):
    return opinions.kin(house, p, q)


def dear(house, p, q):
    """Is q its kin, its bond or its friend?"""
    return kin(house, p, q) or bonds.kind(house, p["id"], q["id"]) in ("close", "friend")


def say(house, kind, text, pid, room, pets=None, hurt=None):
    """A moment; the page draws fights from `pets` (both hobs) and `hurt` (someone was injured)."""
    moment(house, kind, text, pid, room)
    m = house["moments"][-1]
    if pets:
        m["pets"] = list(pets)
    if hurt is not None:
        m["hurt"] = hurt
    return m


def avoid(pet, other_id):
    if other_id not in pet.setdefault("avoid", []):
        pet["avoid"].append(other_id)


# ---- grievances ----

def grievances(house):
    return house.setdefault("grievances", [])


def find(house, by, against):
    return next((g for g in grievances(house) if g["by"] == by and g["against"] == against), None)


def between(house, a, b):
    return [g for g in grievances(house) if {g["by"], g["against"]} == {a, b}]


def grudge(house, cfg, by, against, why, vengeance=False, rung=0):
    """A reason (a theft, an insult, a broken promise, envy, a loss): `by` holds a grievance against `against`, opened at
    `rung` if new, else this reason is added to it and makes it fresh. Returns it (None for no such pair)."""
    P, t = house["pets"], house["tick"]
    if by == against or not alive(P.get(by)) or against not in P:
        return None
    g = find(house, by, against)
    if not g:
        g = {"by": by, "against": against, "why": why, "since": t, "rung": rung, "history": [[t, rung, why]], "fresh": t}
        grievances(house).append(g)
    else:
        g["fresh"] = t
        g["history"].append([t, g["rung"], why])
        del g["history"][:-30]
    if vengeance and not g.get("vengeance"):
        g.update(vengeance=True, rung=max(g["rung"], rung))
    return g


def close(house, cfg, g, how):
    """A grievance ends: made up, talked down, time apart, avoidance, a death, forgiven."""
    if g in grievances(house):
        grievances(house).remove(g)
    done = house.setdefault("grievances_done", [])
    done.append(dict(g, ended=[house["tick"], how]))
    del done[:-200]
    if how not in ("avoidance",):
        holder = house["pets"].get(g["by"])
        if holder and g["against"] in (holder.get("avoid") or []):
            holder["avoid"].remove(g["against"])


def stepped(house, g, rung, what):
    g["rung"], g["last_act"] = rung, house["tick"]
    g["history"].append([house["tick"], rung, what])
    del g["history"][:-30]


def act(house, cfg, by, against, rung, what=""):
    """A rung done in a conversation (talk.py: 1 snub, 2 insult): the step, its moment, and the other's reason to hold
    it against `by`. Opinions are talk's to move. Returns the grievance."""
    P = house["pets"]
    g = find(house, by, against) or grudge(house, cfg, by, against, what or NAMES[rung])
    if not g:
        return None
    stepped(house, g, max(g["rung"], rung), what or NAMES[rung])
    a, b = P[by], P[against]
    say(house, NAMES[rung], "%s %s %s%s" % (label(a), "turned away from" if rung == 1 else "mocked", label(b), ": " + what if what else ""), by, a["room"], pets=[by, against])
    if rung >= 2:
        grudge(house, cfg, against, by, "%s mocked me" % label(a))
    return g


def made_up(house, cfg, a, b, how):
    """Making up between a and b (SPEC-v4.0 §7.2): an apology in a talk ("apology"), a gift ("gift"), a hob talking them
    down ("talked down by X"), the visitor. Whoever holds a grievance decides, by its kindness and how far it climbed
    (vengeance barely ever). Each accepted one is closed. True if any was."""
    K, P, done = C(cfg)["coming_down"], house["pets"], []
    for g in between(house, a, b):
        holder, other = P[g["by"]], P.get(g["against"])
        p = K["accept"] + K["accept_kind"] * character.trait(holder, "kind") - K["accept_rung"] * g["rung"]
        if g.get("vengeance"):
            p *= K["vengeance_accept"]
        if rnd(house, "make up", g["by"], g["against"], house["tick"], how).random() < p:
            close(house, cfg, g, how)
            cause = how if how in ("apology", "gift") else "made_up"
            opinions.move(house, cfg, holder, g["against"], cause, "we made up (%s)" % how)
            memories.add(house, cfg, holder, "%s and I made up (%s)" % (label(other), how), 3, about=[g["against"]], kind="making up")
            done.append(g)
    if done:
        one = len(done) == 1 and between(house, a, b)   # one side forgave; the other still holds its grievance
        text = "%s forgave %s (%s)" % (label(P[done[0]["by"]]), label(P[done[0]["against"]]), how) if one else "%s and %s made up (%s)" % (label(P[a]), label(P[b]), how)
        say(house, "making up", text, a, P[a]["room"], pets=[a, b])
    return bool(done)


def gift(house, cfg, giver, taker):
    """actions.accept: a gift taken from a hob it holds a grievance against may make it up."""
    if on(cfg) and find(house, taker, giver):
        made_up(house, cfg, taker, giver, "gift")


# ---- the ladder ----

def every(cfg):
    return max(1, round(cfg["ticks_per_hour"] * C(cfg)["ladder"]["every_minutes"] / 60))


def protected(house, pid):
    return (house.get("visitor") or {}).get("protect", {}).get(pid, -1) > house["tick"]


def angry(house, cfg, a, g):
    return g.get("vengeance") or character.mood(a) == "angry" or house["tick"] - g.get("fresh", g["since"]) < C(cfg)["ladder"]["angry_hours"] * cfg["ticks_per_hour"]


def why_not(house, cfg, g, a, b, n):
    """None if `a` may take rung n against `b` now (conflict.toml [[rung]]), else why not."""
    L, R, t = C(cfg)["ladder"], C(cfg)["rung"][n - 1], house["tick"]
    venge = g.get("vengeance")
    if a["stage"] in LITTLE and n > L["little_max"]:
        return "little"
    if n >= 6 and b["stage"] not in ("adult", "elder"):   # (19 October 2026: nor ever the victim of a fight, grave harm or a killing)
        return "little victim"
    if not venge and opinions.of(a, b["id"])["liking"] >= R["liking"] and not any(is_(cfg, a, w) for w in R.get("or_any", [])):
        return "liking"
    if R.get("any") and not any(is_(cfg, a, w) for w in R["any"]):
        return "temper"
    if not all(is_(cfg, a, w) for w in R.get("all", [])) or any(is_(cfg, a, w) for w in R.get("not", [])):
        return "temper"
    if R.get("angry") and not angry(house, cfg, a, g):
        return "not angry"
    held = t - g["since"]
    if not venge and (R.get("remembered") and held < L["grudge_hours"] * cfg["ticks_per_hour"] or held < R.get("grudge_days", 0) * cfg["ticks_per_day"]):
        return "too soon"
    if R.get("again") and not venge and not any(x[2] == "cooled" for x in g["history"]):
        return "never climbed again"
    if n in (1, 2, 5, 6, 7, 8) and (b["room"] != a["room"] or (n <= 6 and b["sleep"])):
        return "not together"
    if R.get("alone") and awake_here(house, a, but=(b["id"],)):
        return "not alone"
    if n >= 5 and protected(house, b["id"]):
        return "protected"
    if n >= 6 and floor(house, cfg):   # SPEC-v4.2 §2: under the floor a fight stops at a shove
        return "floor"
    return None


def floor(house, cfg):
    from . import life
    return life.floor(house, cfg)


# SPEC-v4.2 §2.5: where a shove can end in a fall (room types)
FALLS = {"pond": "at the pond", "attic": "from the attic ladder"}


def fall(house, cfg, a, b, r, onlookers):
    """A shove beside the pond or at the attic ladder: a hob's first is a near-fall (v5.3.1); a later one, with its grievance
    against the other open, may end in a fall that kills ([deaths] on, `fall_chance`, never under the floor; the
    near-fall is its foreshadowing, in place of health.declined). The shover is no killer in the ladder's sense:
    a memory of weight 5, and a secret if nobody saw (contracts.secret_later); a seen fall is a killing to be judged, an
    accident. Returns what happened, or None."""
    where = FALLS.get(house["rooms"][b["room"]].get("type"))
    if not where or not contracts.on(cfg, "deaths"):
        return None
    if not a.get("near_fell"):   # (v5.3.1: a hob's first shove by an edge is a near-fall; only a later one can kill)
        return near_fall(house, cfg, a, b, where)
    open_ = any(g["by"] == a["id"] and g["against"] == b["id"] for g in grievances(house))
    if floor(house, cfg) or not open_ or r.random() >= cfg["deaths"]["fall_chance"]:   # (the near-fall was its warning: health.declined's foreshadowing)
        return None
    what = "%s fell %s when %s shoved it" % (label(b), where, label(a))
    b.update(death_due="manslaughter", death_words="fell %s when %s shoved it" % (where, label(a)), shoved_by=a["id"])
    memories.add(house, cfg, a, "I shoved %s, and it fell %s and did not get up" % (label(b), where), 5, about=[b["id"]], kind="fall")
    if onlookers:
        k = killed(house, cfg, a, b, [w["id"] for w in onlookers])
        k.update(accident=True, provoked=True)
    else:
        contracts.secret_later(a, "fall", "I shoved %s, and it fell %s; nobody saw" % (label(b), where), b["id"], house["tick"])
    return what


def near_fall(house, cfg, a, b, where):
    """v5.3.1: the first time a hob shoves another by an edge, it is a near-fall: a moment and a banner, a weight-4
    memory for both, word to everyone in the room, and the fearful there keep away from the shover near edges (wary)."""
    a["near_fell"] = house["tick"]
    what = "%s nearly went over %s when %s shoved it" % (label(b), where, label(a))
    memories.add(house, cfg, a, "I shoved %s %s and it nearly went over" % (label(b), where), 4, about=[b["id"]], kind="fall")
    memories.add(house, cfg, b, "%s shoved me %s and I nearly fell" % (label(a), where), 4, about=[a["id"]], kind="fall")
    for p in here(house, b, awake=True):
        if p["id"] in (a["id"], b["id"]):
            continue
        add_event(house, p, "%s nearly went over %s: %s shoved it" % (label(b), where, label(a)))
        if (p.get("flaw") or {}).get("name") == "fearful" or character.trait(p, "brave") < -cfg["planner"]["pole"]:
            p["wary_of"] = sorted(set(p.get("wary_of") or []) | {a["id"]})
    moment(house, "near fall", what, b["id"], b["room"])
    return what


def wary(house, pet, rid):
    """v5.3.1: a fearful hob that saw a near-fall keeps out of an edge room while the shover is in it (body's doors)."""
    room = house["rooms"].get(rid) or {}
    return bool(pet.get("wary_of")) and room.get("type") in FALLS and any(p["room"] == rid and p["id"] in pet["wary_of"] for p in house["pets"].values() if p["stage"] != "dead")


def climb(house, cfg, g):
    """One look at a grievance: does its holder take the next rung now?"""
    P, L, t = house["pets"], C(cfg)["ladder"], house["tick"]
    a, b = P[g["by"]], P[g["against"]]
    n = g["rung"] + 1
    if n > 8 or a["sleep"] or a.get("scuffle", -1) > t or b.get("scuffle", -1) > t or a.get("outcast") and not outdoors.is_out(b["room"]):
        return None
    if n <= 2 and talk.on(cfg) and t - g.get("last_act", g["since"]) < L["talk_wait_hours"] * cfg["ticks_per_hour"]:
        return None   # snubs and insults are talk's (unless the two haven't had words for a long while)
    if n >= 6 and not health.on(cfg):   # fights and worse act through health
        return None
    if t - g.get("last_act", -10**9) < L["act_gap_hours"] * cfg["ticks_per_hour"] or why_not(house, cfg, g, a, b, n):
        return None
    r = rnd(house, "ladder", a["id"], b["id"], t)
    chance = C(cfg)["rung"][n - 1]["chance"] * (L["outdoors"] if outdoors.is_out(a["room"]) else 1.0) * (L["night"] if house["clock"]["phase"] == "night" else 1.0)
    chance *= character.mood_weight(a, "ladder")   # angry hobs climb more easily, sad and content ones less
    if (a.get("intent") or {}).get("against") == b["id"]:
        chance *= L["intent"]
    # SPEC-v4.2 C: a hot hob climbs a rung faster (§6.2)
    if contracts.on(cfg, "drives") and (a.get("flaw") or {}).get("name") == "hot":
        from .drives import HOT
        chance *= HOT
    # SPEC-v4.2 C: end
    if r.random() >= chance:
        return None
    if n >= 5 and awake_here(house, a, but=(b["id"],)) and r.random() < L["watched_hold"] * (1 - max(0.0, character.trait(a, "brave"))):
        return None   # many won't, with others watching
    if n <= 2:   # (talk moves its own snubs' and insults' opinions; these, made outside a talk, move the other's a little: 19 October 2026)
        g = act(house, cfg, a["id"], b["id"], n, "")
        opinions.move(house, cfg, b, a["id"], "snubbed", "%s %s me" % (label(a), "turned away from" if n == 1 else "mocked"))
        return g
    if n == 3:
        return sabotage(house, cfg, g, a, b, r)
    if n == 4:
        return theft(house, cfg, g, a, b)
    return start(house, cfg, g, a, b, n)


def noticed(house, cfg, a, b, rung, what, cause, moved=False):
    """After sabotage or theft: if the owner or anyone saw, it knows who; else it only finds its loss. (`moved`: the
    house's own take/unmake already moved the opinion of an owner who saw it.)"""
    seen = here(house, a, awake=True)
    if seen:
        if not (moved and b in seen):
            opinions.move(house, cfg, b, a["id"], cause, what)
        memories.add(house, cfg, b, what, 3, about=[a["id"]], kind=NAMES[rung])
        grudge(house, cfg, b["id"], a["id"], what)
        character.set_mood(house, cfg, b, "angry", what)
        avoid(b, a["id"])
    else:
        memories.add(house, cfg, b, "something of mine went missing or was spoiled, and I don't know who did it", 2, kind=NAMES[rung])
        # SPEC-v4.2 C: done and unseen, it is the doer's secret (§6.3; nothing with [drives] off)
        from . import drives
        drives.keep_secret(house, cfg, a, "taken" if rung == 4 else "broken", memories.mine(what, a) + ", and nobody saw", b["id"])
        # SPEC-v4.2 C: end
    for w in seen:
        if w is not b:
            memories.add(house, cfg, w, "I saw %s %s" % (label(a), what.replace("%s " % label(a), "", 1)), 2, about=[a["id"], b["id"]], kind=NAMES[rung])


def sabotage(house, cfg, g, a, b, r):
    """Rung 3: hide (the sly) or break the other's thing here, or spoil its project."""
    room = house["rooms"][a["room"]]
    theirs = sorted(n for n, o in things.made(room).items() if o["made"]["owner"] == b["id"] and not o["made"].get("heirloom") and not o.get("wall"))
    if theirs:
        name = r.choice(theirs)
        hide = [x for x in house["rooms"].values() if x["type"] and x["id"] != room["id"] and not outdoors.is_out(x["id"])]
        if is_(cfg, a, "sly") and hide and not any(name in x["objects"] for x in hide):
            to = r.choice(sorted(hide, key=lambda x: x["id"]))
            o = room["objects"].pop(name)
            o["pos"] = free_tile(house, cfg, to, [cfg["W"] // 2, cfg["H"] // 2])
            from . import order
            order.moved(o, house["tick"], house, cfg, room, name)
            to["objects"][name] = o
            what = "%s hid %s's %s in %s" % (label(a), label(b), name, to["name"])
        else:
            things.unmake(house, cfg, a, name)
            what = "%s broke %s's %s" % (label(a), label(b), name)
    elif b.get("project"):
        b["projects"].append(dict(b["project"], ended=house["tick"], how="spoiled by %s" % label(a)))
        b["project"] = None
        what = "%s spoiled %s's project" % (label(a), label(b))
    else:
        return None   # nothing of theirs to hand: it waits for a chance
    stepped(house, g, 3, what)
    say(house, "sabotage", what, a["id"], a["room"], pets=[a["id"], b["id"]])
    noticed(house, cfg, a, b, 3, what, "broke_my_thing", moved="broke" in what)
    return what


def theft(house, cfg, g, a, b):
    """Rung 4: it takes what the other loves (its most used thing here) through the house's own `take`."""
    from . import actions
    room = house["rooms"][a["room"]]
    theirs = [(o["made"].get("uses", 0), n) for n, o in things.made(room).items() if o["made"]["owner"] == b["id"]]
    for _, name in sorted(theirs, reverse=True):
        step = {"type": "take", "what": name}
        if not actions.check(step, house, cfg, a, None):
            actions.apply(house, cfg, a, step, None)
            what = "%s stole %s's %s" % (label(a), label(b), name)
            stepped(house, g, 4, what)
            say(house, "theft", what, a["id"], a["room"], pets=[a["id"], b["id"]])
            noticed(house, cfg, a, b, 4, what, "took_my_thing", moved=True)
            return what
    return None


# ---- a scuffle: rungs 5 to 8, a few seconds on the page ----

def start(house, cfg, g, a, b, n):
    t, room = house["tick"], house["rooms"][a["room"]]
    house["n"]["scuffle"] = house["n"].get("scuffle", 0) + 1
    sc = {"n": house["n"]["scuffle"], "a": a["id"], "b": b["id"], "room": room["id"], "pos": list(b["pos"]), "rung": n, "since": t,
          "until": t + ticks(cfg, C(cfg)["ladder"]["scuffle_seconds"]), "stopped": None, "blood": None, "outcome": None}
    house.setdefault("scuffles", []).append(sc)
    del house["scuffles"][:-20]
    a["pos"] = free_tile(house, cfg, room, beside(cfg, b["pos"], a["pos"]))
    a["scuffle"] = b["scuffle"] = sc["until"]
    g["last_act"] = t
    for p in (a, b):
        add_event(house, p, "%s went for you" % label(a) if p is b else "you went for %s" % label(b))
        p["news"].append("event")
    return sc


def strength(house, cfg, p, r):
    stage = {"hatchling": 0.2, "child": 0.35, "youngling": 0.55, "adult": 1.0, "elder": 0.7}.get(p["stage"], 0.5)
    hurt = (p.get("hurt") or {}).get("level")
    return stage + 0.05 * memories.skill(p, "fighting") + 0.3 * character.trait(p, "brave") - (0.2 * (health.HURT.index(hurt) + 1) if hurt else 0) + 0.5 * r.random()


def scuffles(house, cfg):
    """Each tick: a scuffle whose time is up ends (switched off: any under way ends with nothing)."""
    t = house["tick"]
    for sc in house.get("scuffles", []):
        if sc["outcome"] or sc["stopped"]:
            continue
        if not on(cfg):
            sc["stopped"] = "switched off"
        elif t >= sc["until"]:
            resolve(house, cfg, sc)
        else:
            continue
        for pid in (sc["a"], sc["b"]):
            house["pets"].get(pid, {}).pop("scuffle", None)


def resolve(house, cfg, sc):
    P, F, K, t = house["pets"], C(cfg)["fight"], C(cfg)["coming_down"], house["tick"]
    a, b, n = P.get(sc["a"]), P.get(sc["b"]), sc["rung"]
    if not (alive(a) and alive(b)) or a["room"] != b["room"]:
        sc["outcome"] = "apart"
        return
    g = find(house, a["id"], b["id"]) or grudge(house, cfg, a["id"], b["id"], "a scuffle")
    r = rnd(house, "scuffle", sc["n"])
    onlookers = sorted(awake_here(house, a, but=(b["id"],)), key=lambda p: (not is_(cfg, p, "kind"), p["id"]))
    stepper = next((w for w in onlookers if w["stage"] not in LITTLE and (is_(cfg, w, "kind") or is_(cfg, w, "brave"))
                    and r.random() < K["step_in_little" if b["stage"] in LITTLE else "step_in"]), None)
    witnesses = [w["id"] for w in onlookers]
    if stepper:   # §7.5: it gets between them, and may be hurt for it
        hit = r.random() < F["stepper_hurt"] and health.hurt(house, cfg, stepper, "bruised", "stepping between %s and %s" % (label(a), label(b)))
        what = "%s went for %s, and %s stepped between them%s" % (label(a), label(b), label(stepper), " and was bruised" if hit else "")
        sc["outcome"] = "stepped in: %s" % stepper["id"]
        stepped(house, g, max(0, n - 1), what)
        opinions.move(house, cfg, b, stepper["id"], "protected_me", what)
        for p, w in ((b, 4), (stepper, 4), (a, 3)):
            memories.add(house, cfg, p, what, w, about=[a["id"], b["id"], stepper["id"]], kind="stepped in")
        say(house, NAMES[n], what, a["id"], a["room"], pets=[a["id"], b["id"], stepper["id"]], hurt=bool(hit))
        grudge(house, cfg, b["id"], a["id"], "%s went for me" % label(a))
        avoid(b, a["id"])
        return
    hurt, victim = None, b
    if n >= 6 and floor(house, cfg):
        n = 5   # (SPEC-v4.2 §2: the house fell under the floor while they squared up)
    if n == 5:
        fell = fall(house, cfg, a, b, r, onlookers)
        if fell:
            sc["outcome"] = fell
            stepped(house, g, 5, fell)
            say(house, "shove", fell, a["id"], a["room"], pets=[a["id"], b["id"]], hurt=True)
            for w in onlookers:
                memories.add(house, cfg, w, "I saw it: %s" % fell, 5, about=[a["id"], b["id"]], kind="fall")
            return
        what = "%s shoved %s" % (label(a), label(b))
        opinions.move(house, cfg, b, a["id"], "threatened_me", what)
    elif n == 6:
        win, lose = (a, b) if strength(house, cfg, a, r) >= strength(house, cfg, b, r) else (b, a)
        hurt = health.hurt(house, cfg, lose, "bruised" if r.random() < F["lucky"] else "hurt", "a fight with %s" % label(win))
        if r.random() < F["both"]:
            health.hurt(house, cfg, win, "bruised", "a fight with %s" % label(lose))
        for p in (a, b):
            memories.practise(house, cfg, p, "fighting")
        what = "%s and %s came to blows; %s came off worse%s" % (label(a), label(b), label(lose), ", %s" % hurt if hurt else "")
        opinions.move(house, cfg, lose, win["id"], "beat_me", what)
        victim = lose
    elif n == 7:
        hurt = health.hurt(house, cfg, b, "badly hurt", "%s attacked it" % label(a))
        if r.random() < F["both"]:
            health.hurt(house, cfg, a, "bruised", "attacking %s" % label(b))
        what = "%s hurt %s badly" % (label(a), label(b))
        opinions.move(house, cfg, b, a["id"], "hurt_me", what)
    else:
        what = "%s killed %s" % (label(a), label(b))
        hurt = "killed"
    if hurt:
        sc["blood"] = list(victim["pos"])
    sc["outcome"] = what
    stepped(house, g, n, what)
    m = say(house, NAMES[n], what, a["id"], a["room"], pets=[a["id"], b["id"]], hurt=bool(hurt))
    if n >= 6 and hurt:
        craft.burst(house, b, "killing" if n == 8 else "fight", m["text"])
    for w in onlookers:
        memories.add(house, cfg, w, "I saw it: %s" % what, 5 if n == 8 else 3, about=[a["id"], b["id"]], kind=NAMES[n])
        opinions.move(house, cfg, w, a["id"], "saw_violence", what)
    memories.add(house, cfg, a, what, 5 if n >= 7 else 3, about=[b["id"]], kind=NAMES[n])
    if n == 8:
        b["death_due"] = "violence"   # life.due hands it to Engine.kill this tick: it falls, and lies still
        if contracts.on(cfg, "deaths"):   # SPEC-v4.2 §2.7
            b.update(death_due="killing", death_words="was killed by %s" % label(a))
        killed(house, cfg, a, b, witnesses)
        return
    memories.add(house, cfg, b, what, 5 if n >= 6 else 3, about=[a["id"]], kind=NAMES[n])
    character.set_mood(house, cfg, b, "angry" if is_(cfg, b, "brave") else "afraid", what)
    needs.lift(house, cfg, b, "safety", -10 * (n - 4))
    grudge(house, cfg, b["id"], a["id"], what)
    avoid(b, a["id"])
    for k in [p for p in house["pets"].values() if alive(p) and p is not a and p is not b and p["stage"] not in LITTLE and kin(house, p, b)
              and not is_(cfg, p, "kind") and opinions.of(p, b["id"])["liking"] >= 0]:
        if rnd(house, "sides", k["id"], t).random() < K["take_sides"]:   # kin take sides, and the feud spreads
            grudge(house, cfg, k["id"], a["id"], "%s took %s's side: %s" % (label(k), label(b), what))


# ---- after a killing (§7.4) ----

def killings(house):
    return house.setdefault("killings", [])


def killed(house, cfg, killer, dead, witnesses):
    A, t = C(cfg)["after"], house["tick"]
    house["n"]["killing"] = house["n"].get("killing", 0) + 1
    rooms = {dead["room"]} | set(house["rooms"][dead["room"]]["doors"].values())
    prov = find(house, dead["id"], killer["id"])
    k = {"n": house["n"]["killing"], "tick": t, "killer": killer["id"], "dead": dead["id"], "room": dead["room"], "witnesses": list(witnesses),
         "known": [killer["id"]] + list(witnesses), "found": t if witnesses else None, "suspicion": 0.0, "blamed": {}, "votes": {},
         "verdict": None, "by": None, "provoked": bool(prov and prov["rung"] >= 3), "feared": [], "legend": [], "vigil": None,
         "family": family(dead), "near": [p["id"] for p in house["pets"].values() if alive(p) and p["room"] in rooms and p is not killer and p is not dead]}
    killings(house).append(k)
    del killings(house)[:-20]
    character.set_mood(house, cfg, killer, "proud" if is_(cfg, killer, "prickly") and not is_(cfg, killer, "timid") else "afraid" if is_(cfg, killer, "timid") else "ashamed",
                       "I killed %s" % label(dead), hours=A["grief_hours"])   # how it gives itself away: boasting, fear, shame
    for p in house["pets"].values():
        if not alive(p) or p is killer or p is dead:
            continue
        needs.lift(house, cfg, p, "safety", -A["fear_all"])   # fear: house-wide
        if dear(house, p, dead):   # grief: sad for days, and a vigil at the resting place
            character.set_mood(house, cfg, p, "sad", "%s is dead" % label(dead), hours=A["grief_hours"])
            memories.add(house, cfg, p, "%s was killed" % label(dead), 5, about=[dead["id"]], kind="grief")
            p.setdefault("aims", []).append({"text": "keep a vigil for %s" % label(dead), "why": "I loved them", "kind": "vigil", "target": dead["id"], "since": t, "done": False})
    for gr in [x for x in grievances(house) if dead["id"] in (x["by"], x["against"])]:
        close(house, cfg, gr, "death")
    return k


def tell(house, cfg, k, killer, dead):
    """A hob that knows tells one awake beside it that doesn't: truly, or (sly, and not against the killer) blaming another."""
    A, P, t = C(cfg)["after"], house["pets"], house["tick"]
    for tid in list(k["known"]):
        teller = P.get(tid)
        if tid == k["killer"] or not alive(teller) or teller["sleep"]:
            continue
        r = rnd(house, "tell", k["n"], tid, t)
        listeners = [p for p in awake_here(house, teller) if p["id"] not in k["known"]]
        if not listeners or r.random() >= A["tell"]:
            continue
        lst = listeners[0]
        if is_(cfg, teller, "sly") and opinions.of(teller, k["killer"])["liking"] >= 0 and r.random() < A["lie"]:
            others = sorted(p["id"] for p in P.values() if alive(p) and p["id"] not in (k["killer"], k["dead"], tid, lst["id"]))
            if others:
                x = r.choice(others)
                k["blamed"][x] = k["blamed"].get(x, 0) + 1
                opinions.gossip(house, cfg, teller, lst, x, -8, true=False)
                memories.add(house, cfg, lst, "%s told me %s killed %s" % (label(teller), label(P[x]), label(dead)), 4, about=[x, k["dead"], tid], kind="told")
                continue
        k["known"].append(lst["id"])
        k["found"] = k["found"] or t
        opinions.gossip(house, cfg, teller, lst, k["killer"], -8, true=True)
        memories.add(house, cfg, lst, "%s told me %s killed %s" % (label(teller), label(killer), label(dead)), 4, about=[k["killer"], k["dead"], tid], kind="told")


def after(house, cfg):
    """Each step, for each killing: the telling, suspicion, the legend, fear near the killer, vengeance, the vigil, justice."""
    A, P, t = C(cfg)["after"], house["pets"], house["tick"]
    hours = every(cfg) / cfg["ticks_per_hour"]
    for k in killings(house):
        killer, dead = P.get(k["killer"]), P.get(k["dead"])
        if not killer or not dead:
            continue
        tell(house, cfg, k, killer, dead)
        if not k["found"]:   # no witnesses: where hobs were, gossip, and the killer giving itself away
            near = sum(1 for x in k["near"] if alive(P.get(x)))
            gives = 1.0 + (0.5 if character.mood(killer) in ("ashamed", "afraid", "proud") else 0.0) + (0.0 if is_(cfg, killer, "sly") else 0.5)
            k["suspicion"] = round(k["suspicion"] + hours / A["suspicion_hours"] * (1 + 0.2 * near) * gives, 4)
            if k["suspicion"] >= 1:
                k["found"] = t
                k["known"] += [p["id"] for p in P.values() if alive(p) and p["stage"] not in LITTLE and p["id"] not in k["known"]]
                say(house, "killing", "the house has worked out that %s killed %s" % (label(killer), label(dead)), killer["id"], killer["room"], pets=[killer["id"], dead["id"]])
        if not k["vigil"]:
            stone = next((r for r in house["rooms"].values() if r["type"] and any((o.get("memorial") or {}).get("pet") == k["dead"] for o in r["objects"].values())), None)
            mourners = [p for p in house["pets"].values() if stone and alive(p) and p["room"] == stone["id"] and not p["sleep"] and dear(house, p, dead)]
            if len(mourners) >= 2:
                k["vigil"] = t
                say(house, "vigil", "%s kept a vigil at %s's stone" % (" and ".join(label(p) for p in mourners), label(dead)), mourners[0]["id"], stone["id"], pets=[p["id"] for p in mourners])
                for p in mourners:
                    for aim in p.get("aims") or []:
                        if aim.get("kind") == "vigil" and aim.get("target") == k["dead"]:
                            aim["done"] = True
        if not k["found"]:
            continue
        for p in P.values():   # the family tells it as a legend, to the young and the not yet born
            if alive(p) and p["id"] not in k["legend"] and p is not killer and family(p) == k["family"]:
                k["legend"].append(p["id"])
                memories.add(house, cfg, p, "the family tells how %s killed %s" % (label(killer), label(dead)), 4, about=[k["killer"], k["dead"]], kind="legend")
                if p["id"] not in k["known"]:
                    k["known"].append(p["id"])
        if not alive(killer) or k.get("accident"):   # (19 October 2026: below the vigil and the legend, which go on when the killer is dead; SPEC-v4.2 §2.5: an accident is judged, not avenged)
            continue
        for pid in k["known"]:   # vengeance: kin, bond and friends of the dead start at a fight (19 October 2026: once past a child)
            p = P.get(pid)
            if alive(p) and p is not killer and p["stage"] not in ("hatchling", "child") and dear(house, p, dead) and not (find(house, pid, k["killer"]) or {}).get("vengeance") \
                    and k["verdict"] != "forgiven" and pid not in k.setdefault("avengers", []):   # (once a killing: a verdict changed after a pardon granted it again)
                k["avengers"].append(pid)
                grudge(house, cfg, pid, k["killer"], "%s killed %s" % (label(killer), label(dead)), vengeance=True, rung=5)
                opinions.move(house, cfg, p, k["killer"], "killed_my_kin", "%s killed %s" % (label(killer), label(dead)))
        if t - k["tick"] < A["fear_days"] * cfg["ticks_per_day"]:   # fear: most of all near the killer
            for p in awake_here(house, killer):
                needs.lift(house, cfg, p, "safety", -A["fear_near"])
                if p["id"] in k["known"] and p["id"] not in k["feared"]:
                    k["feared"].append(p["id"])
                    opinions.move(house, cfg, p, k["killer"], "saw_violence", "%s killed %s" % (label(killer), label(dead)))
        if k["verdict"] is None and t - k["found"] >= A["justice_hours"] * cfg["ticks_per_hour"]:
            decide(house, cfg, k, killer, dead)


def lean(house, cfg, k, v, killer, dead):
    """How one hob would have the family judge the killer."""
    o = opinions.of(v, k["killer"])
    if o["fear"] >= 7 and not is_(cfg, v, "brave"):
        return "nothing"   # it doesn't dare
    if k["provoked"] and is_(cfg, v, "kind") and o["liking"] > -3:
        return "forgiven"
    if is_(cfg, v, "prickly") or is_(cfg, v, "brave") or dear(house, v, dead):
        return "driven out"
    return "shunned"


def decide(house, cfg, k, killer, dead):
    """The family decides, in its conversations (votes from talk.py), weighted by the respected and the old."""
    P = house["pets"]
    voters = [P[x] for x in k["known"] if alive(P.get(x)) and x != k["killer"] and P[x]["stage"] not in LITTLE]
    if not voters:
        return None
    tally = {}
    for v in voters:
        respect = [opinions.of(p, v["id"])["respect"] for p in voters if p is not v] or [5]
        w = 1 + sum(respect) / len(respect) / 5 + (1 if v["stage"] == "elder" else 0)
        verdict = k["votes"].get(v["id"]) or lean(house, cfg, k, v, killer, dead)
        tally[verdict] = tally.get(verdict, 0) + w
    verdict = max(sorted(tally), key=lambda x: tally[x])
    return verdict_on(house, cfg, k, verdict, "the family")


def verdict_on(house, cfg, k, verdict, by):
    """The verdict on a killing, done. (19 October 2026: a verdict it already has is not done again (None), and a changed
    one moves only what changes: the house remembers the first, the killer every one.)"""
    P, t = house["pets"], house["tick"]
    killer, dead = P[k["killer"]], P[k["dead"]]
    if verdict == "driven out" and not outdoors.usable(house, cfg):
        verdict = "shunned"   # (with the outdoors switched off there is nowhere to drive it to)
    if verdict == k["verdict"]:
        return None
    again = k["verdict"] is not None
    k.update(verdict=verdict, judged=t, by=by)
    killer["shunned"] = t if verdict == "shunned" else None
    if killer.get("outcast") and verdict != "driven out":
        come_back(house, cfg, killer, quiet=True)
    text = {"shunned": "%s shunned %s for killing %s: nobody will talk to it, and it eats alone",
            "driven out": "%s drove %s out of the house for killing %s: it lives in the meadow now",
            "forgiven": "%s forgave %s for killing %s", "nothing": "%s did nothing about %s killing %s"}[verdict] % (by[0].upper() + by[1:], label(killer), label(dead))
    if verdict == "driven out":
        killer["outcast"] = {"since": t, "why": "killed %s" % label(dead)}
        send_out(house, cfg, killer)
        craft.burst(house, killer, "driven out", text)
    if verdict == "forgiven":
        for g in grievances(house):
            if g["against"] == k["killer"] and g.get("vengeance"):
                g["vengeance"] = False
                stepped(house, g, min(g["rung"], 3), "forgiven by the family")
    say(house, "justice", text, killer["id"], killer["room"], pets=[killer["id"], dead["id"]])
    for p in P.values():   # (19 October 2026: weight 3 for all but the killer, as for every house-wide memory: 4 never faded, and filled them)
        if alive(p) and (p is killer or not again):
            memories.add(house, cfg, p, text, 3 if p is not killer else 5, about=[k["killer"], k["dead"]] + (["visitor"] if by == "the visitor" else []), kind="justice")
    return verdict


def send_out(house, cfg, pet):
    meadow = house["rooms"][outdoors.MEADOW]
    pet.update(room=meadow["id"], pos=free_tile(house, cfg, meadow, [cfg["W"] // 2, cfg["H"] // 2]), plan=None, following=None)
    pet["rooms"][meadow["id"]] = house["tick"]


def come_back(house, cfg, pet, quiet=False):
    """An outcast comes home, changed or not."""
    g, why = outdoors.garden(house), (pet.get("outcast") or {}).get("why", "")
    pet["outcast"] = None
    if g and outdoors.is_out(pet["room"]):
        pet.update(room=g["id"], pos=free_tile(house, cfg, g, house["door_tiles"][outdoors.GATE]), plan=None)
    if quiet:
        return
    changed = rnd(house, "changed", pet["id"], house["tick"]).random() < C(cfg)["after"]["changed"]
    if changed:   # (a gene: inherited from here on)
        pet["temper"]["kind"] = round(min(0.95, pet["temper"].get("kind", 0.5) + 0.25), 2)
    text = "%s came back to the house, years after it was driven out%s" % (label(pet), ", changed" if changed else "")
    say(house, "justice", text, pet["id"], pet["room"], pets=[pet["id"]])
    craft.burst(house, pet, "coming back", text)
    for p in house["pets"].values():
        if alive(p):
            memories.add(house, cfg, p, text + (" (it had %s)" % why if why else ""), 4 if p is pet else 3, about=[pet["id"]], kind="justice")


def outcasts(house, cfg):
    t, A = house["tick"], C(cfg)["after"]
    per_day = cfg["ticks_per_day"] / every(cfg)
    for p in house["pets"].values():
        if not alive(p):
            continue
        if p.get("outcast"):
            if not outdoors.is_out(p["room"]) and outdoors.usable(house, cfg):
                send_out(house, cfg, p)
            elif t - p["outcast"]["since"] >= A["come_back_days"] * cfg["ticks_per_day"] and rnd(house, "back", p["id"], t).random() < A["come_back"] / per_day:
                come_back(house, cfg, p)
        if p.get("shunned") is not None and t - p["shunned"] >= A["shun_days"] * cfg["ticks_per_day"]:
            unshun(house, p)
            say(house, "justice", "the family has stopped shunning %s" % label(p), p["id"], p["room"], pets=[p["id"]])
        elif p.get("shunned") is not None:   # shunned: everyone keeps away from it (the body), so it eats alone
            for o in house["pets"].values():
                if alive(o) and o is not p:
                    avoid(o, p["id"])


def unshun(house, p):
    p["shunned"] = None
    for o in house["pets"].values():
        if p["id"] in (o.get("avoid") or []):
            o["avoid"].remove(p["id"])


# ---- coming down (§7.2) ----

def cool(house, cfg):
    """Time apart: a grievance with nothing new for a while comes down a rung; at the bottom it ends, in peace or in a
    coldness the two keep (house["cold"], each in the other's pet["avoid"]). A vengeance grudge stays heavy."""
    K, P, t = C(cfg)["coming_down"], house["pets"], house["tick"]
    for g in list(grievances(house)):
        if g.get("vengeance"):
            continue
        last = max(g.get("last_act", g["since"]), g.get("fresh", g["since"]), g.get("cooled", g["since"]))
        if t - last < K["cool_days"] * cfg["ticks_per_day"]:
            continue
        g["cooled"], g["rung"] = t, g["rung"] - 1
        g["history"].append([t, g["rung"], "cooled"])
        if g["rung"] <= 0:
            holder = P.get(g["by"])
            cold = holder is not None and opinions.of(holder, g["against"])["liking"] < 0
            close(house, cfg, g, "avoidance" if cold else "time apart")
            if cold:
                house.setdefault("cold", []).append([g["by"], g["against"], t])


def thawed(house, c):
    """19 October 2026 (a coldness was for ever, and undid the morning's wipe of `avoid`): it ends when the holder's liking
    is back to nothing or more, when the two have made up since, or have become close. Then the holder stops keeping away."""
    a, b, since = house["pets"][c[0]], c[1], c[2]
    o = opinions.of(a, b)
    if o["liking"] < 0 and bonds.close(house, a) != b and not any(x["cause"] in ("made_up", "apology") and x["tick"] >= since for x in o.get("causes", [])):
        return False
    if b in (a.get("avoid") or []):
        a["avoid"].remove(b)
    return True


def talk_down(house, cfg, g):
    """A kind or respected hob in the room with both talks them down."""
    P = house["pets"]
    a, b = P[g["by"]], P[g["against"]]
    if g.get("vengeance") or g["rung"] < 3 or a["room"] != b["room"] or a["sleep"]:
        return False
    for m in awake_here(house, a, but=(b["id"],)):
        respected = (opinions.of(a, m["id"])["respect"] + opinions.of(b, m["id"])["respect"]) / 2 >= 7
        if m["stage"] not in LITTLE and (is_(cfg, m, "kind") or respected) and rnd(house, "talk down", m["id"], house["tick"]).random() < C(cfg)["coming_down"]["talk_down"]:
            if made_up(house, cfg, a["id"], b["id"], "talked down by %s" % label(m)):
                for p in (a, b):
                    opinions.move(house, cfg, p, m["id"], "stepped_in", "%s talked us down" % label(m))
                return True
    return False


def seed(house, cfg):
    """A hob that dislikes another enough, for a remembered reason newer than their last grievance's end, holds one."""
    P, L = house["pets"], C(cfg)["ladder"]
    ended = {}
    for d in house.get("grievances_done", []):
        ended[(d["by"], d["against"])] = d["ended"][0]
    for p in P.values():
        if not alive(p):
            continue
        for oid, o in (p.get("opinions") or {}).items():
            if oid == p["id"] or not alive(P.get(oid)) or o.get("liking", 0) > L["seed_liking"] or find(house, p["id"], oid):
                continue
            why = next((c for c in reversed(o.get("causes") or []) if c.get("d", {}).get("liking", 0) < 0 and c.get("tick", 0) > ended.get((p["id"], oid), -1)), None)
            if why:
                grudge(house, cfg, p["id"], oid, why.get("why") or "a grudge")


def intents(house, cfg):
    """The brain's intent, read: making up is tried at once; anything else makes the next rung likelier (climb)."""
    for p in house["pets"].values():
        it = p.get("intent") or {}
        if alive(p) and (it.get("how") or "").lower() in ("make up", "apologise", "apologize", "forgive", "say sorry") and it.get("against"):
            p.pop("intent")
            made_up(house, cfg, p["id"], it["against"], "it wanted to make up")


def tick(house, cfg):
    scuffles(house, cfg)
    t, P = house["tick"], house["pets"]
    if t % every(cfg):
        return
    v = house.get("visitor") or {}
    if v.get("protect"):   # (the visitor's protection runs out here too: with [visitor4] off nothing else ends it)
        v["protect"] = {k: u for k, u in v["protect"].items() if u > t}
    for g in list(grievances(house)):   # the dead hold nothing, and nothing is held against them
        if not alive(P.get(g["by"])) or not alive(P.get(g["against"])):
            close(house, cfg, g, "death")
    house["cold"] = [c for c in house.get("cold", []) if alive(P.get(c[0])) and alive(P.get(c[1])) and not thawed(house, c)]
    for a, b, _ in house["cold"]:
        avoid(P[a], b)
    cool(house, cfg)
    for p in P.values():   # (19 October 2026) a vigil is kept for `grief_hours`, whatever else happens: once the killer was dead, or with one mourner, it never ended
        for aim in (p.get("aims") or []) if alive(p) else ():
            if aim.get("kind") == "vigil" and not aim.get("done") and t - aim["since"] >= C(cfg)["after"]["grief_hours"] * cfg["ticks_per_hour"]:
                aim["done"] = True
    if not on(cfg):   # off: grievances only cool, and (19 October 2026) the outcast and the shunned are let back in
        for p in P.values():
            if alive(p) and p.get("outcast"):
                come_back(house, cfg, p, quiet=True)
            if alive(p) and p.get("shunned") is not None:
                unshun(house, p)
        return
    intents(house, cfg)
    seed(house, cfg)
    for g in list(grievances(house)):
        if g in grievances(house) and not talk_down(house, cfg, g):
            climb(house, cfg, g)
    after(house, cfg)
    outcasts(house, cfg)


# ---- the visitor steps in (§10.2; visitor.py's "stepin" calls these) ----

def stop_fight(house, cfg, a, b):
    """They freeze and back off: the scuffle between a and b ends with nothing, and the whole room remembers."""
    P, t = house["pets"], house["tick"]
    sc = next((s for s in reversed(house.get("scuffles", [])) if {s["a"], s["b"]} == {a, b} and not s["outcome"] and not s["stopped"] and s["until"] > t), None)
    if not sc:
        return False
    sc["stopped"] = "visitor"
    x, y = P[sc["a"]], P[sc["b"]]
    for p in (x, y):
        p.pop("scuffle", None)
    g = find(house, sc["a"], sc["b"])
    what = "the visitor stepped in, and %s and %s froze and backed off" % (label(x), label(y))
    if g:
        stepped(house, g, max(0, sc["rung"] - 1), what)
    avoid(x, y["id"])
    avoid(y, x["id"])
    for p in house["pets"].values():   # rare, and the whole house remembers (the two most)
        if alive(p):
            memories.add(house, cfg, p, what, 4 if p in (x, y) else 3, about=[x["id"], y["id"], "visitor"], kind="stepped in")
    say(house, NAMES[sc["rung"]], what, x["id"], x["room"], pets=[x["id"], y["id"]], hurt=False)
    return True


def protect(house, cfg, pid, until):
    """Nobody can hurt this hob (rung 5 and up) until then."""
    house.setdefault("visitor", {}).setdefault("protect", {})[pid] = until
    return True


def judge(house, cfg, killer_id, verdict):
    """The visitor judges a killer: pardon, shun or drive out (overriding the family). Returns (ok, what happened)."""
    verdict = VERDICTS.get((verdict or "").strip().lower())
    k = next((x for x in reversed(killings(house)) if x["killer"] == killer_id), None)
    if not verdict or not k or not alive(house["pets"].get(killer_id)):
        return False, "there is no living killer by that name to judge" if verdict else "pardon, shun or drive out"
    if not verdict_on(house, cfg, k, verdict, "the visitor"):
        return False, "%s is %s already" % (label(house["pets"][killer_id]), k["verdict"] if k["verdict"] != "nothing" else "left be")
    return True, house["moments"][-1]["text"]


def vote(house, cfg, pid, killer_id, verdict):
    """talk.py: what a hob said in a conversation the family should do with a killer (shunned, driven out, forgiven, nothing)."""
    verdict = VERDICTS.get((verdict or "").strip().lower())
    k = next((x for x in reversed(killings(house)) if x["killer"] == killer_id and x["verdict"] is None), None)
    if verdict and k:
        k["votes"][pid] = verdict
    return bool(verdict and k)


def force(house, cfg, a, b, rung):
    """For the checks (and only them): a scuffle at this rung now, whatever the ladder says."""
    g = find(house, a, b) or grudge(house, cfg, a, b, "forced")
    return start(house, cfg, g, house["pets"][a], house["pets"][b], rung)
