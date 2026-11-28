"""SPEC-v5.3 §2, §3 (helper A): projects and sites. A project (contracts.project, at house["v5"]["projects"][id]) is a
goal that takes days: steps in order (projects.toml), done by the body one a day at most for each owner (`[projects]
steps_per_day`). The day's step is the hob's aim as a job's step is (pet["job_aim"], planner.current), set here every
tick it has no job: a gather step goes where the material lies or to the machine (jobs.source), and what it carries of
it goes into the project's stock (bought at the trade price at the machine); every other step is a while at the site
(`[projects] work_hours`), awake; furnish carries a made thing of its kind there. A site (contracts.site, at
house["v5"]["sites"][id]) is one of the outdoor plots (outdoors.plots) or a tile indoors; it shows by stage. Done, a
project is a fixture with its kind's verbs (items.entry reads fix.project5) carrying its owners' names.

Projects outlive hobs (§2.4): an owner's death leaves a project with no living owner orphaned, said on the board in
words; kin and friends may take it up; a project with no step for `[projects] abandon_days` is abandoned, its stock
laid out free at its site, and its site decays over `decay_days`. Joint projects (§2.5) have two owners who take
steps in turn (the one who did fewer goes next); worked_together fires on a day a step is done; a [ladder] grievance
between them halves the stock and leaves the project with the one who did more. A hob's first project is drawn at
the youngling stage from its drive (§2.6) and named by the model in its next plan (the `project` proposal).
build.py's under-way builds are mirrored as projects of kind "build" (or "statue") with a site and owners, for the
board; build.py still builds them. Switch: [projects] on (contracts.on53); off, none of this runs."""
import tomllib

from . import contracts as K
from .world import STAGES, add_event, days, dist, free_tile, hours, label, moment, rnd

KINDS = {}   # projects.toml's [kind.*]
OPEN = ("planned", "under way", "blocked")
DONE_WORDS = {"clear": "the ground is cleared", "dig": "the ground is dug", "frame": "the frame is up", "cover": "it is covered over",
              "hearth": "the hearth is laid", "furnish": "it is furnished", "grow": "it is planted", "build": "it is knocked together", "gather": "it has its %s"}
STAGE_OF = {"clear": "cleared", "dig": "cleared", "frame": "framed", "build": "framed", "cover": "covered", "hearth": "covered", "grow": "covered", "furnish": "covered"}
NUM = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]


def num(n):
    return NUM[n] if 0 <= n < len(NUM) else str(n)


def kinds():
    if not KINDS:
        KINDS.update(tomllib.loads(K.PROJECT_FILE.read_text())["kind"])
    return KINDS


def on(cfg):
    return K.on53(cfg, "projects")


def P(cfg):
    return cfg.get("projects") or {}


def store(house):
    return house.setdefault("v5", {}).setdefault("projects", {})


def sites(house):
    return house.setdefault("v5", {}).setdefault("sites", {})


def setbacks(house):
    return house.setdefault("v5", {}).setdefault("setbacks", {})


def living(house):
    return [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")]


def grown(pet, stage="youngling"):
    return pet["stage"] in STAGES and STAGES.index(pet["stage"]) >= STAGES.index(stage)


def mirror(pr):
    return pr["id"].startswith("build:")


def owners(house, pr):
    """Its living owners."""
    return [o for o in pr["owners"] if house["pets"].get(o, {}).get("stage") not in (None, "egg", "dead")]


def of(house, pet):
    """API53: the project it owns and works now (planned, under way or blocked), or None. build.py's builds are not
    one a hob works as its project."""
    return next((pr for pr in store(house).values() if pet["id"] in pr["owners"] and pr["state"] in OPEN and not mirror(pr)), None)


def step(pr):
    return next((s for s in pr["steps"] if not s["done"]), None)


def parse(x):
    do, what, n = (str(x).split(":") + ["", "1"])[:3]
    return {"do": do, "what": what, "n": int(n or 1), "got": 0, "done": False, "by": []}


def noun(pr):
    return pr.get("build") or pr["kind"]


def names_of(house, ids):
    ns = [label(house["pets"][i]) for i in ids if i in house["pets"]]
    return " and ".join(ns) if ns else "someone"


def state(house, pr, st):
    if pr["state"] == st:
        return
    pr["state"] = st
    K.event53(house, "project", project=pr["id"], kind=pr["kind"], state=st, owners=list(pr["owners"]))
    K.count(house, "projects", st)


def kinds_for(pet, house=None):
    """The kinds its drive (or a habit) could start (§2.6): not one it has finished already."""
    drive = (pet.get("drive") or {}).get("name")
    habits = {h.get("name") for h in pet.get("habits") or [] if isinstance(h, dict)}
    have = {pr["kind"] for pr in store(house).values() if pr["state"] == "done" and pet["id"] in pr["names"]} if house else set()
    return [k for k, e in kinds().items() if k != "build" and k not in have and (drive in e.get("drives", []) or e.get("habit") in habits)]


# ---- sites (§2.3) ----

def site_of(house, pr):
    return sites(house).get(pr.get("site") or "")


def where(house, site):
    room = house["rooms"].get(site["room"] or "")
    return "%s in %s" % (site["name"], room["name"]) if site["kind"] == "plot" and room else site["name"]


def wish(house, cfg, pet, pr, words):
    """Where it means to build (v5.3.1): a plot is only words until the first step there begins (claim); an
    indoor site is taken at once, as before."""
    if kinds()[pr["kind"]]["site"] == "plot":
        pr["where"] = words
        return None
    return claim(house, cfg, pet, pr, words)


def release(house, pr):
    """v5.3.1: its plot let go, free for another (a decaying structure stays on it as a thing, not a reservation)."""
    site = site_of(house, pr)
    if site and site["kind"] == "plot" and site["project"] == pr["id"]:
        site["project"] = None
        if site["stage"] != "decaying":
            site.update(stage="bare", since=0, decay=0.0)
    if site and site["kind"] == "plot":
        pr["site"] = None


def claim(house, cfg, pet, pr, words=""):
    """A site for it: a free plot outdoors (the one its words name, else one in a room it knows), or a tile indoors in
    a room its kind may go in. None if there is none."""
    from . import outdoors
    e, S = kinds()[pr["kind"]], sites(house)
    if e["site"] == "plot":
        outdoors.plots(house, cfg)
        free = [s for s in S.values() if s["kind"] == "plot" and not s["project"]]
        w = (words or "").lower()
        hit = lambda s: (bool(s["name"]) and s["name"].split()[-1] in w) + (house["rooms"][s["room"]]["name"].split()[-1] in w)
        free.sort(key=lambda s: (s["stage"] == "decaying", -hit(s), s["room"] not in pet["rooms"], s["room"] != outdoors.MEADOW, s["id"]))
        site = free[0] if free else None
        if site:
            pet["rooms"].setdefault(site["room"], house["tick"])   # (the map shows the outdoors: SPEC-v3.6c §4)
    else:
        rooms = e.get("rooms") or ["any"]
        mine = [house["rooms"][r] for r in [pet.get("sleeps_in"), pet["room"]] + list(pet["rooms"]) if r in house["rooms"]]
        room = next((r for r in mine if r["type"] and not r.get("outdoor") and ("any" in rooms or r["type"] in rooms)), None)
        if not room:
            return None
        used = {tuple(t) for s in S.values() if s["room"] == room["id"] for t in s["tiles"]}
        tile = free_tile(house, cfg, room, pet.get("sleeps_at") if pet.get("sleeps_in") == room["id"] and pet.get("sleeps_at") else [cfg["W"] // 2, cfg["H"] // 2])
        if tuple(tile) in used:
            return None
        sid = "in:%s:%d,%d" % (room["id"], tile[0], tile[1])
        site = S[sid] = K.site({"id": sid, "kind": "indoor", "room": room["id"], "tiles": [tile], "name": "in %s" % room["name"]})
    if site:
        site.update(project=pr["id"], stage="bare", since=house["tick"], decay=0.0)
        pr["site"] = site["id"]
    return site


def restage(house, pr):
    site = site_of(house, pr)
    if not site:
        return
    st = "bare"
    for s in pr["steps"]:
        if s["done"] and s["do"] in STAGE_OF and K.SITE_STAGES.index(STAGE_OF[s["do"]]) > K.SITE_STAGES.index(st):
            st = STAGE_OF[s["do"]]
    site["stage"] = "done" if pr["state"] == "done" else st


# ---- beginning one (§2.6) ----

def begin(house, cfg, pet, kind, why="", goal="", site=None, with_=None):
    """API53: a new project of this kind, its owner the hob (and `with_`, a joint one), planned. One a hob at a time:
    with one already, this one waits (pet["project_next"]) and None is returned."""
    if not on(cfg) or kind not in kinds() or kind == "build" or pet["stage"] in ("egg", "dead"):
        return None
    other = with_ if isinstance(with_, dict) else house["pets"].get(with_ or "")
    if of(house, pet) or (other and of(house, other)):
        pet["project_next"] = {"kind": kind, "why": why, "goal": goal, "site": site or ""}
        return None
    V = house.setdefault("v5", {})
    V["project_n"] = V.get("project_n", 0) + 1
    e = kinds()[kind]
    pr = K.project({"id": "p%d" % V["project_n"], "goal": goal or "%s %s" % (e["a"], kind), "kind": kind, "steps": [parse(x) for x in e["steps"]],
                    "owners": [pet["id"]] + ([other["id"]] if other else []), "since": house["tick"], "state": "planned", "why": why or e["words"]})
    pr["named"] = bool(goal)
    store(house)[pr["id"]] = pr
    K.event53(house, "project", project=pr["id"], kind=kind, state="planned", owners=list(pr["owners"]))
    K.count(house, "projects", "planned")
    if site:
        wish(house, cfg, pet, pr, site)
    for p in [pet] + ([other] if other else []):
        add_event(house, p, "you mean to build %s: %s" % (pr["goal"], e["words"]) if not other else "you and %s mean to build %s together" % (label(other if p is pet else pet), pr["goal"]))
    return pr


def draw(house, cfg, pet):
    """§2.6 its first project, from its drive, at the youngling stage (once a hob): planned, with no site yet; the model
    names it in its next plan. Returns it, or None."""
    if "project53" in pet or not grown(pet):
        return None
    pet["project53"] = house["tick"]
    ks = kinds_for(pet, house)
    if not ks or of(house, pet):
        return None
    return begin(house, cfg, pet, ks[0], why=(pet.get("drive") or {}).get("name") or kinds()[ks[0]]["words"])


def propose(house, cfg, pet, proposal):
    """API53: the plan's `project` (contracts.proposal, or None): its planned project named (goal and site), an orphan of
    that kind taken up, or a new one begun (a second waits). (words, ok)."""
    p = K.proposal(proposal)
    if not on(cfg) or not p:
        return "", False
    cur = of(house, pet)
    if not cur and any(x["state"] == "done" and x["kind"] == p["kind"] and pet["id"] in x["names"] for x in store(house).values()):
        return "your %s stands already" % p["kind"], False
    if cur and cur["kind"] == p["kind"]:
        if p["goal"]:
            cur["goal"], cur["named"] = p["goal"], True
        if not cur["site"] and p["site"]:
            wish(house, cfg, pet, cur, p["site"])
        return "you mean %s" % cur["goal"], True
    if cur:
        pet["project_next"] = p
        return "one thing at a time: the %s comes first" % noun(cur), False
    orphan = next((pr for pr in store(house).values() if pr["state"] == "orphaned" and pr["kind"] == p["kind"]), None)
    if orphan and take_up(house, cfg, pet, orphan["id"]):
        return "you took up %s" % orphan["goal"], True
    pr = begin(house, cfg, pet, p["kind"], why=p["why"], goal=p["goal"], site=p["site"])
    return ("you mean to build %s" % pr["goal"], True) if pr else ("", False)


# ---- the day's step (§2.1) ----

def worker(house, pr):
    """Whose turn it is: of a joint project, the owner who has done fewer steps (§2.5)."""
    live = owners(house, pr)
    return min(live, key=lambda o: (pr["steps_by"].get(o, 0), pr["owners"].index(o))) if live else None


def due(house, cfg, pet):
    """Has it a step of its own project to do today (its turn, not done for the day, nothing in the way)? Then a job
    that can wait waits (jobs.score)."""
    pr = of(house, pet)
    return bool(pr) and spent(house, pet) < P(cfg).get("steps_per_day", 1) and worker(house, pr) == pet["id"] and pr["id"] not in setbacks(house)


def spent(house, pet):
    d = pet.get("proj53_day") or [None, 0]
    return d[1] if d[0] == house["clock"]["day"] else 0


def made_thing(house, pet, kind, rooms=None):
    """(room id, name) of a made thing of this kind it may take (nothing in it, not put away), or None."""
    from . import things
    for rid in rooms or [pet["room"]] + list(pet["rooms"]):
        r = house["rooms"].get(rid)
        if not r or not r["type"]:
            continue
        for n, o in sorted(things.made(r).items()):
            if o["made"]["recipe"].get("kind") == kind and not o.get("on") and things.free_to_change(house, pet, o) and not any(x.get("on") == n for x in r["objects"].values()):
                return rid, n
    return None


def setback(house, pr, words):
    """What stands in its way, for the plan packet (§4) and the board; None clears it. Blocked while it says so."""
    S = setbacks(house)
    if words:
        S[pr["id"]] = words
        if pr["state"] in ("planned", "under way"):
            state(house, pr, "blocked")
    elif S.pop(pr["id"], None) and pr["state"] == "blocked":
        state(house, pr, "under way" if any(s["done"] for s in pr["steps"]) else "planned")


def need_words(house, cfg, pet, pr, s):
    """Why a gather step can't go on just now, in the world's words, or None."""
    from . import jobs
    if s["what"] in pet["carrying"] or jobs.source(house, cfg, pet, s["what"]) is not None:
        return None
    return "it needs %s more %s, and there's none in the rooms you know%s" % (num(s["n"] - s["got"]), s["what"], " nor in the machine" if jobs.sells(house, cfg) else "")


def step_aim(house, cfg, pet):
    """API53: an aim for today's step (the planner follows it as a job's), or None: none today, its step done for the
    day, not its turn (it keeps the other company), or the way out shut. An owner of a finished shelter goes out to it
    as the day ends."""
    from . import jobs, outdoors
    pr = of(house, pet)
    if pet["stage"] in ("egg", "dead", "hatchling") or pet["sleep"]:
        return None
    ev = evening(house, cfg, pet)
    if ev or not pr or spent(house, pet) >= P(cfg).get("steps_per_day", 1):
        return ev
    s, w = step(pr), worker(house, pr)
    if not s:
        return None
    base = {"done": False, "job": "project:" + pr["id"], "project": pr["id"], "since": pr["touched"]}
    if w != pet["id"]:   # (§2.5: not its turn: it keeps the other company at it)
        return dict(base, kind="be with", target=w, text="keep %s company at the %s" % (label(house["pets"][w]), noun(pr)))
    if s["do"] != "gather" and not pr["site"] and not claim(house, cfg, pet, pr, pr.get("where") or ""):
        setback(house, pr, "there is nowhere free to build it")
        return None
    site = site_of(house, pr)
    if s["do"] == "gather":
        src = jobs.source(house, cfg, pet, s["what"])
        why = need_words(house, cfg, pet, pr, s)
        setback(house, pr, why)
        if why:
            return None
        if src and src[0]["do"] == "buy":
            return dict(base, kind="job", target=src[0]["where"], text="buy %s at the machine for the %s" % (s["what"], noun(pr)))
        return dict(base, kind="gather", target=s["what"], text="gather %s for the %s" % (s["what"], noun(pr)))
    if s["do"] == "furnish":
        got = made_thing(house, pet, s["what"])
        setback(house, pr, None if got else "it wants a %s, and there's none to be had" % s["what"])
        return dict(base, kind="job", target=got[0], text="bring a %s to the %s" % (s["what"], noun(pr))) if got else None
    setback(house, pr, None)
    if outdoors.is_out(site["room"]) and pet["room"] != site["room"] and not outdoors.is_out(pet["room"]) and outdoors.why_shut(house, cfg):
        return None   # (the gate is shut: tomorrow)
    return dict(base, kind="job", target=site["room"], text="%s at the %s %s" % (s["do"], noun(pr), site["name"]))


def evening(house, cfg, pet):
    """A finished shelter's owner goes out to it before dusk (§3), and stays out there through it."""
    from . import outdoors
    sh = sheltered(house, cfg, pet)
    if not sh or not outdoors.is_out(sh[0]):
        return None
    c, s = house["clock"], cfg["house"]["seasons"][house["clock"]["season"]]
    if not (c["phase"] == "dusk" or (c["phase"] == "night" and outdoors.is_out(pet["room"])) or (c["phase"] == "day" and c["hour"] >= s["sunset"] - 2)) or (pet["room"] != sh[0] and not outdoors.is_out(pet["room"]) and outdoors.why_shut(house, cfg)):
        return None
    return {"kind": "job", "target": sh[0], "text": "out to your shelter for the night", "done": False, "job": "project:shelter", "project": None, "evening53": True, "since": house["clock"]["day"]}


def work(house, cfg, pet, pr, s):
    """clear, dig, frame, cover, hearth, grow, build: a while at the site, awake."""
    site = site_of(house, pr)
    if not site or pet["room"] != site["room"]:
        return False
    s["got"] += 1
    return s["got"] >= hours(cfg, P(cfg).get("work_hours", 1.0))


def gather(house, cfg, pet, pr, s):
    """What it carries of the material goes into the stock; at the machine, one bought at the trade price (§3)."""
    from . import jobs, trade
    m = s["what"]
    if m not in pet["carrying"] and s["got"] < s["n"] and not jobs.lying(house, pet).get(m) and jobs.sells(house, cfg).get(m) == pet["room"]:
        words, ok = trade.buy(house, cfg, pet, m)
        if not ok:
            setback(house, pr, words)
    while m in pet["carrying"] and s["got"] < s["n"]:
        pet["carrying"].remove(m)
        s["got"] += 1
        pr["stock"][m] = pr["stock"].get(m, 0) + 1
    return s["got"] >= s["n"]


def furnish(house, cfg, pet, pr, s):
    """A made thing of its kind, where it stands, goes into it."""
    from . import things
    got = made_thing(house, pet, s["what"], [pet["room"]])
    if not got:
        return False
    room = house["rooms"][got[0]]
    things.gone(house, room["objects"].pop(got[1]), got[1], "set into %s's %s" % (names_of(house, pr["owners"]), noun(pr)), room)
    pr["stock"][s["what"]] = pr["stock"].get(s["what"], 0) + 1
    s["got"] += 1
    return s["got"] >= s["n"]


STEP = {"clear": work, "gather": gather, "dig": work, "frame": work, "cover": work, "hearth": work, "furnish": furnish, "grow": work, "build": work}


def advance(house, cfg, pet, pr):
    """Its turn's step, one tick, where it stands: done, counted, the site staged; the last one finishes it."""
    s = step(pr)
    if not s or worker(house, pr) != pet["id"] or spent(house, pet) >= P(cfg).get("steps_per_day", 1) or pet["sleep"]:
        return
    if not STEP[s["do"]](house, cfg, pet, pr, s):
        return
    s["done"], s["by"] = True, list(dict.fromkeys(s["by"] + [pet["id"]]))
    pr["steps_by"][pet["id"]] = pr["steps_by"].get(pet["id"], 0) + 1
    pr["touched"], pr["waited"] = house["tick"], 0
    pr["progress"] = round(sum(x["done"] for x in pr["steps"]) / len(pr["steps"]), 2)
    pet["proj53_day"] = [house["clock"]["day"], spent(house, pet) + 1]
    setbacks(house).pop(pr["id"], None)
    K.event53(house, "step", project=pr["id"], pet=pet["id"], do=s["do"])
    K.count(house, "steps", pet["id"])
    state(house, pr, "under way")
    restage(house, pr)
    add_event(house, pet, "the %s: %s" % (noun(pr), DONE_WORDS[s["do"]] % s["what"] if s["do"] == "gather" else DONE_WORDS[s["do"]]))
    together(house, cfg, pr)
    if step(pr) is None:
        finish(house, cfg, pet, pr)


def together(house, cfg, pr):
    """§2.5 worked_together, once a day a step is done on a joint project."""
    from . import opinions
    live = owners(house, pr)
    if len(live) < 2 or pr.get("together") == house["clock"]["day"]:
        return
    pr["together"] = house["clock"]["day"]
    a, b = (house["pets"][x] for x in live[:2])
    opinions.move(house, cfg, a, b["id"], "worked_together", "%s and I worked on our %s together" % (label(b), noun(pr)))
    opinions.move(house, cfg, b, a["id"], "worked_together", "%s and I worked on our %s together" % (label(a), noun(pr)))


def finish(house, cfg, pet, pr):
    """The last step done: it stands, a fixture with its kind's verbs, named for everyone who owned it."""
    from . import things
    site, e = site_of(house, pr), kinds()[pr["kind"]]
    state(house, pr, "done")
    restage(house, pr)
    who = names_of(house, pr["names"])
    room = house["rooms"].get((site or {}).get("room") or "")
    if room:
        name = things.unique_name(house, cfg, "%s's %s" % (who, pr["kind"]))
        verbs = {v: x for v, x in e.get("becomes", {}).items() if v in K.VERBS}
        room["objects"][name] = {"pos": list(site["tiles"][0]), "fix": {"project5": pr["id"], "verbs5": verbs, "cozy": bool(e["becomes"].get("sleep")),
                                                                   "says": "%s; %s built it" % (e["words"], who)}}
        pr["fixture"] = name
    moment(house, "project", "%s's %s stands finished %s" % (who, pr["kind"], where(house, site) if site else ""), pet["id"], (site or {}).get("room") or pet["room"])
    for o in owners(house, pr):
        add_event(house, house["pets"][o], "the %s is finished: %s" % (pr["kind"], pr["goal"]))
    nxt(house, cfg, pr)


def nxt(house, cfg, pr):
    """A project that waited begins once its owner's is over (§2.6)."""
    for o in owners(house, pr):
        p = house["pets"][o]
        w = p.pop("project_next", None)
        if w and not of(house, p):
            begin(house, cfg, p, w["kind"], why=w.get("why", ""), goal=w.get("goal", ""), site=w.get("site") or None)


# ---- §3 a shelter to sleep in ----

def sheltered(house, cfg, pet):
    """API53: (room id, tile) of a finished thing of its own it may sleep at (cover counts as a bed: `sleep` in its
    kind's becomes), the outdoor one first; or None."""
    if not on(cfg):
        return None
    out = []
    for pr in store(house).values():
        site = site_of(house, pr)
        if pr["state"] == "done" and pet["id"] in pr["names"] and site and kinds().get(pr["kind"], {}).get("becomes", {}).get("sleep"):
            out.append((site["kind"] != "plot", site["room"], list(site["tiles"][0])))
    return min(out)[1:] if out else None


def night(house, cfg, pet):
    """A night under its own cover (slept_out, once a night), curled up beside it; and in again by day (came_in)."""
    from . import feel, outdoors
    sh = sheltered(house, cfg, pet)
    if pet["sleep"] and sh and pet["room"] == sh[0] and outdoors.is_out(sh[0]):
        if dist(pet["pos"], sh[1]) > 1:
            from .world import beside
            pet["pos"] = beside(cfg, sh[1], pet["pos"])
            pet["sleeps_in"], pet["sleeps_at"] = pet["room"], list(pet["pos"])
        if pet.get("slept_out53") != pet["sleep"]["since"]:
            pet["slept_out53"] = pet["sleep"]["since"]
            K.event53(house, "slept_out", pet=pet["id"], site=next((s["id"] for s in sites(house).values() if s["room"] == sh[0] and s["tiles"][0] == sh[1]), None))
    elif pet.get("slept_out53") and not pet["sleep"] and not outdoors.is_out(pet["room"]):
        pet.pop("slept_out53")
        hungry = "hunger" in pet["needs"] and feel.level(pet, "hunger") >= 2
        K.event53(house, "came_in", pet=pet["id"], why="for food" if hungry else "for company")


# ---- §2.4 orphans, taking up, abandonment and decay ----

def words(house, pr):
    """A project in the board's words: "Spoon's shelter stands half built in the meadow"."""
    site = site_of(house, pr)
    who, at = names_of(house, pr["names"]), where(house, site) if site else ""
    far = "begun" if pr["progress"] < 0.3 else "half built" if pr["progress"] < 0.8 else "nearly finished"
    last = next((DONE_WORDS[s["do"]] for s in reversed(pr["steps"]) if s["done"] and s["do"] != "gather"), "")
    st, n = pr["state"], noun(pr)
    if st == "orphaned":
        return "%s's %s stands %s %s" % (who, n, far, at) if site else "%s's %s was never begun" % (who, n)
    if st == "done":
        return "%s's %s stands finished %s" % (who, n, at)
    if st == "abandoned":
        return "%s's %s was left %s %s" % (who, n, far, at) if site else "%s gave up on %s" % (who, pr["goal"])
    if st == "blocked":
        return "%s's %s waits: %s" % (who, n, setbacks(house).get(pr["id"], "it can't go on just now"))
    if st == "planned":
        return "%s means to build %s" % (who, pr["goal"])
    return "%s's %s %s: %s" % (who, n, at, last or far)


def orphan(house, cfg, dead):
    """API53: its projects with no living owner left are orphaned, said on the board in words; kin and friends see it.
    A joint one goes on with the other owner (and still carries the dead one's name)."""
    if not on(cfg):
        return
    from . import bonds, opinions
    for pr in store(house).values():
        if dead["id"] not in pr["owners"] or pr["state"] not in OPEN or mirror(pr):
            continue
        pr["owners"] = [o for o in pr["owners"] if o != dead["id"]]
        if owners(house, pr):
            for o in owners(house, pr):
                add_event(house, house["pets"][o], "%s is gone; the %s is yours to finish" % (label(dead), noun(pr)))
            continue
        state(house, pr, "orphaned")
        pr["touched"] = house["tick"]
        said = words(house, pr)
        for p in living(house):
            if opinions.kin(house, p, dead) or bonds.kind(house, p, dead) in ("friend", "close"):
                add_event(house, p, said)
        moment(house, "project", said, dead["id"], (site_of(house, pr) or {}).get("room") or dead["room"])


def may_take(house, pet, pr):
    from . import bonds, opinions
    if pet["stage"] in ("egg", "dead", "hatchling") or of(house, pet):
        return False
    dead = [house["pets"][x] for x in pr["names"] if x in house["pets"]]
    return any(opinions.kin(house, pet, d) or bonds.kind(house, pet, d) in ("friend", "close") for d in dead) or not dead


def take_up(house, cfg, pet, pid):
    """API53: a kin or friend takes an orphan up (§2.4): its owner now, the dead one's name kept on it. True if so."""
    pr = store(house).get(pid)
    if not on(cfg) or not pr or pr["state"] != "orphaned" or not may_take(house, pet, pr):
        return False
    was = pr["names"][0] if pr["names"] else None
    pr["owners"] = [pet["id"]]
    pr["names"] = list(dict.fromkeys(pr["names"] + [pet["id"]]))
    pr["touched"] = house["tick"]
    state(house, pr, "under way" if any(s["done"] for s in pr["steps"]) else "planned")
    K.event53(house, "taken_up", project=pid, pet=pet["id"], was=was)
    site = site_of(house, pr)
    moment(house, "project", "%s took up %s's %s%s" % (label(pet), names_of(house, [was]), noun(pr), " " + where(house, site) if site else ""), pet["id"], pet["room"])
    add_event(house, pet, "you took up %s's %s: you will finish it" % (names_of(house, [was]), noun(pr)))
    return True


def free_stock(house, cfg, pr, stock):
    """Stock let go: laid out loose at its site, free to take."""
    site = site_of(house, pr)
    room = house["rooms"].get((site or {}).get("room") or "")
    if not room:
        return
    for m, n in stock.items():
        for _ in range(n):
            room["spots"].append({"bit": m, "pos": free_tile(house, cfg, room, site["tiles"][0]), "ready": True, "back": None, "loose": True, "since": house["tick"]})


def abandon(house, cfg, pr):
    state(house, pr, "abandoned")
    free_stock(house, cfg, pr, pr["stock"])
    pr["stock"] = {}
    setbacks(house).pop(pr["id"], None)
    site = site_of(house, pr)
    if site:
        site.update(stage="decaying", since=house["tick"], decay=0.0)
        release(house, pr)   # (v5.3.1: the ruin stands; the plot is free at once)
    for o in owners(house, pr):
        add_event(house, house["pets"][o], "you have let the %s go: nobody has worked on it for days" % noun(pr))
    nxt(house, cfg, pr)


def decay(house, cfg):
    """An abandoned project's site decays to nothing over a season, then is free (a plot) or gone (indoors)."""
    S = sites(house)
    for sid, s in list(S.items()):
        if s["stage"] != "decaying":
            continue
        s["decay"] = round(min(1.0, days(cfg, s["since"], house["tick"]) / max(1, P(cfg).get("decay_days", 42))), 3)
        if s["decay"] >= 1.0:
            if s["kind"] == "plot":
                s.update(stage="bare", decay=0.0, since=house["tick"])
            else:
                S.pop(sid)


def falling_out(house, cfg, pr):
    """§2.5 a [ladder] grievance between joint owners: the stock halved (the other half laid out free), and the project
    left with the one who did more."""
    from . import conflict
    live = owners(house, pr)
    if len(live) < 2 or not conflict.between(house, live[0], live[1]):
        return
    keep = max(live, key=lambda o: (pr["steps_by"].get(o, 0), -pr["owners"].index(o)))
    gone = next(o for o in live if o != keep)
    half = {m: n // 2 for m, n in pr["stock"].items()}
    pr["stock"] = {m: n - half[m] for m, n in pr["stock"].items()}
    free_stock(house, cfg, pr, half)
    pr["owners"] = [keep]
    for o, words_ in ((keep, "you and %s fell out: the %s is yours alone now" % (label(house["pets"][gone]), noun(pr))),
                      (gone, "you and %s fell out: the %s is %s's now, and half of what you gathered is left lying" % (label(house["pets"][keep]), noun(pr), label(house["pets"][keep])))):
        add_event(house, house["pets"][o], words_)


# ---- §2.5 joint projects ----

def keeps_company(a, b):
    return any(isinstance(h, dict) and h.get("name") == "keep company" and h.get("target") == b["id"] for h in a.get("habits") or [])


def joint(house, cfg, a, b):
    """API53: two hobs' shared project: the one either has (the other joins it, a planned one of its own let go if of
    the same kind), or a new one of a kind both their drives could start (else either's, else a bridge). None if both
    are at their own already."""
    if not on(cfg) or a is b or "dead" in (a["stage"], b["stage"]):
        return None
    pa, pb = of(house, a), of(house, b)
    if pa and pb and pa is pb:
        return pa
    for mine, other, theirs in ((pa, b, pb), (pb, a, pa)):
        if mine and len(mine["owners"]) == 1 and (not theirs or (theirs["state"] == "planned" and theirs["kind"] == mine["kind"] and len(theirs["owners"]) == 1)):
            if theirs:
                store(house).pop(theirs["id"])
                if theirs.get("site") in sites(house):
                    sites(house)[theirs["site"]].update(project=None, stage="bare")
            mine["owners"].append(other["id"])
            mine["names"] = list(dict.fromkeys(mine["names"] + [other["id"]]))
            for p, q in ((house["pets"][mine["owners"][0]], other), (other, house["pets"][mine["owners"][0]])):
                add_event(house, p, "you and %s will build the %s together" % (label(q), noun(mine)))
            return mine
    if pa or pb:
        return None
    ka, kb = kinds_for(a, house), kinds_for(b, house)
    kind = next((k for k in ka if k in kb), None) or (ka + kb + ["bridge"])[0]
    return begin(house, cfg, a, kind, why="to build it together", with_=b)


def pairs(house, cfg):
    """The day's joint projects: two hobs whose keep company is at each other, or two close ones whose projects (or
    drives) share a kind."""
    from . import bonds
    pets = sorted((p for p in living(house) if grown(p, "child")), key=lambda p: p["id"])
    for i, a in enumerate(pets):
        for b in pets[i + 1:]:
            pa, pb = of(house, a), of(house, b)
            if pa and pa is pb:
                continue
            ka, kb = ({pa["kind"]} if pa else set(kinds_for(a, house))), ({pb["kind"]} if pb else set(kinds_for(b, house)))
            if (keeps_company(a, b) and keeps_company(b, a)) or (bonds.close(house, a) == b["id"] and ka & kb):
                joint(house, cfg, a, b)


# ---- build.py's builds, on the board the same way ----

def mirrors(house, cfg):
    """build.py's things under way are projects of kind "build" (the statue: "statue") with a site and owners, kept in
    step with them: done when they stand, abandoned when they are gone."""
    from . import build
    S, seen = store(house), set()
    for room in house["rooms"].values():
        if not room["type"]:
            continue
        for n, o in room["objects"].items():
            rec = build.record(o)
            if not rec:
                continue
            pid = "build:%s|%s" % (room["id"], n)
            pr = S.get(pid)
            if pr is None and "site" not in o:
                continue
            seen.add(pid)
            if pr is None:
                s = o["site"]
                key = s["project"]
                pr = S[pid] = K.project({"id": pid, "goal": "%s %s in %s" % (build.PROJECT.get(key, {}).get("a", "a"), key, room["name"]), "build": key,
                                         "kind": "statue" if build.PROJECT.get(key, {}).get("honours") else "build", "steps": [{"do": "build"}],
                                         "owners": [s["by"]], "since": s["at"], "state": "under way", "why": "the room wants it"})
                sites(house)[pid] = K.site({"id": pid, "kind": "indoor", "room": room["id"], "tiles": [o["pos"]], "name": "in %s" % room["name"], "project": pid, "since": s["at"]})
                pr["site"] = pid
                K.event53(house, "project", project=pid, kind=pr["kind"], state="under way", owners=list(pr["owners"]))
                K.count(house, "projects", "under way")
            if "site" in o:
                s = o["site"]
                pr["owners"] = list(dict.fromkeys([s["by"]] + sorted(s["paws"], key=lambda p: -s["paws"][p])))
                pr["names"] = list(dict.fromkeys(pr["names"] + pr["owners"]))
                pr["progress"] = round(min(1.0, s["work"] / max(1, build.PROJECT.get(s["project"], {}).get("sessions", 1))), 2)
                pr["touched"] = max([pr["touched"]] + list(s["last"].values()))
                sites(house)[pid]["stage"] = "framed" if pr["progress"] >= 0.4 else "cleared" if s["placed"] else "bare"
            elif pr["state"] != "done":
                b = o["fix"]["built"]
                pr.update(owners=list(b["paws"]), names=list(dict.fromkeys(pr["names"] + b["paws"])), progress=1.0, fixture=n)
                pr["steps"][0]["done"] = True
                state(house, pr, "done")
                sites(house)[pid]["stage"] = "done"
    for pid, pr in S.items():
        if mirror(pr) and pid not in seen and pr["state"] in OPEN:
            state(house, pr, "abandoned")
            sites(house).pop(pid, None)


# ---- the tick ----

def tick(house, cfg):
    """API53: every tick, each owner's step a tick on where it stands and today's step its aim (when it has no job);
    nights out under its own cover; hourly, build.py's builds kept in step; once a world day, first projects drawn,
    joint ones formed, falling-outs split, orphans taken up, the abandoned let go, and sites decaying."""
    if not on(cfg):
        for p in house["pets"].values():
            if str((p.get("job_aim") or {}).get("job") or "").startswith("project:"):
                p.pop("job_aim")
        return
    from . import jobs, outdoors
    for p in sorted(living(house), key=lambda p: p["id"]):
        j = jobs.of(house, p)
        if j and ((jobs.deficit_of(house, j) or {}).get("urgency", 1) >= 3 or not evening(house, cfg, p)):   # (out to its shelter at dusk before a job that can wait)
            continue
        pr = of(house, p)
        if pr:
            advance(house, cfg, p, pr)
        a = step_aim(house, cfg, p)
        old = p.get("job_aim") or {}
        if a and not (old.get("job") == a["job"] and old.get("target") == a["target"] and old.get("since") == a["since"]):
            p["job_aim"] = a
        elif not a and str(old.get("job") or "").startswith("project:"):
            p.pop("job_aim")
        night(house, cfg, p)
    if house["tick"] % hours(cfg, 1) == 0:
        outdoors.plots(house, cfg)
        mirrors(house, cfg)
    V = house.setdefault("v5", {})
    if V.get("projects_day") == house["clock"]["day"]:
        return
    V["projects_day"] = house["clock"]["day"]
    for p in sorted(living(house), key=lambda p: p["id"]):
        draw(house, cfg, p)
    pairs(house, cfg)
    for pr in list(store(house).values()):
        if pr["state"] not in OPEN + ("orphaned",) or mirror(pr):
            continue
        if not any(s["done"] for s in pr["steps"]) and pr["state"] != "orphaned":   # (v5.3.1: no plot held until its first step is done)
            release(house, pr)
        falling_out(house, cfg, pr)
        if pr["state"] == "orphaned":
            r = rnd(house, "take up", pr["id"], house["clock"]["day"])
            who = sorted((p for p in living(house) if may_take(house, p, pr)), key=lambda p: (p["stage"] not in ("child", "youngling"), p["id"]))
            if who and r.random() < 0.5 and take_up(house, cfg, who[0], pr["id"]):
                continue
        if pr["state"] == "blocked":   # (a day it waited on what it can't get is not a day it let it go; a season of it is)
            pr["waited"] = pr.get("waited", 0) + 1
        idle = days(cfg, pr["touched"], house["tick"])
        if idle - pr.get("waited", 0) >= P(cfg).get("abandon_days", 6) or idle >= P(cfg).get("decay_days", 42):
            abandon(house, cfg, pr)
    decay(house, cfg)


# ---- the model's part (§4), the board and the card ----

def step_words(house, cfg, pet, pr):
    s = step(pr)
    if not s:
        return "it is finished"
    if s["do"] == "gather":
        left = s["n"] - s["got"]
        at = (jobs_lying(house, pet).get(s["what"]))
        there = "; there's %s in %s" % (s["what"], house["rooms"][at]["name"]) if at else ""
        return "it needs %s more %s%s" % (num(left), s["what"], there)
    return {"clear": "clear the ground", "dig": "dig the ground", "frame": "put up the frame", "cover": "cover it over", "hearth": "lay a hearth of stones",
            "furnish": "bring a %s to it" % s["what"], "grow": "plant it and water it", "build": "knock it together"}[s["do"]]


def jobs_lying(house, pet):
    from . import jobs
    return jobs.lying(house, pet)


def line(house, cfg, pet):
    """API53: its project and next step in words for the plan packet, or "you have no project" with the kinds its drive
    could start (§4)."""
    if not on(cfg):
        return ""
    pr = of(house, pet)
    if pr and not pr.get("named") and pr["state"] == "planned":
        return "you mean to build %s, %s (for %s): in your plan, say what it is and where (project)" % (pr["goal"], kinds()[pr["kind"]]["words"], pr["why"])
    if pr:
        site = site_of(house, pr)
        joint_ = [label(house["pets"][o]) for o in owners(house, pr) if o != pet["id"]]
        last = next((DONE_WORDS[s["do"]] % s["what"] if s["do"] == "gather" else DONE_WORDS[s["do"]] for s in reversed(pr["steps"]) if s["done"]), "nothing is done yet")
        bad = setbacks(house).get(pr["id"])
        return "your %s%s (%s%s): %s; next: %s%s" % (noun(pr), " with " + " and ".join(joint_) if joint_ else "", pr["goal"], ", " + where(house, site) if site else "",
                                                last, step_words(house, cfg, pet, pr), "; but " + bad if bad else "")
    ks = [k for k in kinds_for(pet, house)]
    done = [noun(x) for x in store(house).values() if x["state"] == "done" and pet["id"] in x["names"] and not mirror(x)]
    return ("your %s stands finished. " % done[-1] if done else "") + ("you have no project" + ("; your wish could start %s" % " or ".join("%s %s" % (kinds()[k]["a"], k) for k in ks) if ks else ""))


def ctx(house, cfg, pet):
    """What the plan's `project` may name (brain4)."""
    return {"kinds": [k for k in K.PROJECT_KINDS if k != "build"], "sites": sorted({s["name"] for s in sites(house).values() if s["kind"] == "plot" and not s["project"]}),
            "name": (lambda pr: pr["kind"] if pr and not pr.get("named") else None)(of(house, pet)), "drive": kinds_for(pet, house)}


def board(house):
    """§8 the board's rows: each project by state (orphans in words), the finished and the let go of the last day."""
    out = []
    for pr in sorted(store(house).values(), key=lambda x: (K.PROJECT_STATES.index(x["state"]) if x["state"] != "orphaned" else -1, -x["touched"])):
        if pr["state"] in ("done", "abandoned") and house["tick"] - pr["touched"] > house.get("day_ticks", 10 ** 9):
            continue
        out.append({"id": pr["id"], "kind": pr["kind"], "state": pr["state"], "words": words(house, pr), "owners": list(pr["owners"])})
    return out


def card(house, cfg, pet):
    """The hob's card: its project with its next step, in a line ("" with none)."""
    pr = of(house, pet)
    if not on(cfg) or not pr:
        return ""
    return "%s: %s" % (pr["goal"], step_words(house, cfg, pet, pr))


def view(house, cfg):
    """The page's sites: each with its kind, stage, room, tiles and words (build.py's own are drawn by build.py)."""
    S = store(house)
    out = []
    for s in sites(house).values():
        pr = S.get(s["project"] or "")
        if s["kind"] == "plot" or (pr and not mirror(pr)):
            out.append({"id": s["id"], "room": s["room"], "tiles": s["tiles"], "stage": s["stage"], "decay": s["decay"], "plot": s["kind"] == "plot",
                        "kind": pr["kind"] if pr else None, "name": s["name"], "words": words(house, pr) if pr else "a plot %s" % s["name"]})
    return out


# ---- §9 the migration ----

def migrate(house, cfg):
    """API53: once a house: the plots; first projects for every living youngling and older whose drive maps to one;
    build.py's under-way builds as projects with their builders as owners. Returns the report's lines."""
    from . import outdoors
    if not on(cfg) or (house.get("migrated") or {}).get("v53_projects"):
        return []
    house.setdefault("migrated", {})["v53_projects"] = house["tick"]
    lines = []
    made = outdoors.plots(house, cfg)
    lines.append("plots: %s" % (", ".join(where(house, s) for s in made) or "none yet (no outdoors)"))
    for p in sorted(living(house), key=lambda p: p["id"]):
        if not grown(p):
            continue
        pr = draw(house, cfg, p)
        lines.append("%s: %s" % (label(p), "%s (planned, for its wish: %s)" % (pr["goal"], pr["why"]) if pr else "no first project (%s)" % ((p.get("drive") or {}).get("name") or "no drive")))
    mirrors(house, cfg)
    for pr in store(house).values():
        if mirror(pr):
            lines.append("%s: a project now, %s's" % (pr["goal"], names_of(house, pr["owners"])))
    return lines
