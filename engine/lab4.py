"""SPEC-v4.0.5 §8: the Lab's "Today": what the owner reads the morning after a deploy, read by `/api/lab` (server.py).

Per living hob: pride, hunger and safety; its memories by weight; its aims today, done, failed (with their words) and
open; its thoughts today by kind, with the mean seconds each waited for its turn and was computed; its talks, and those
that failed; replies that were not JSON and replies cut off. The house: how long since the last good save, the model's
busy share, calls in the last real hour against the budget, eggs laid and found this lineage, founder eggs re-parented,
websocket clients and the last message's size. Beside each, yesterday's.

What only the house as it is now can say (needs, memories, aims, which are cleared at night) is kept through the day by
`keep`, each tick, in house["lab4"]; the rest is read from the lineage's log by tick. Columns and counts other parts add
(calls.wait/finish, eng.saved_at, house["migrated"]["orphans"]) are read where they are; where they are not yet, the
number is None. (house["failed_talks"], talk.py's, is there once a talk has failed: until then, none have.)

SPEC-v4.2 §11.5: the Lab's "Spirit" (`spirit`); and the two shapes the page reads of what C writes (`card`, a talk's
minds by speaker), each read through engine/contracts.py, and each only once its writer has written it.

SPEC-v5.0 §5 (helper C): the Lab's "Jobs" (`jobs`), read only from contracts.counts and the work board, so it reads
zeros, not errors, before deficits and jobs write anything."""
import time
from collections import Counter

from . import contracts as K
from . import memories
from .world import alive, clock, label, ticks

NEEDS = ("pride", "hunger", "safety")


def day_start(house, cfg):
    """The tick the world day on the clock began."""
    return house["tick"] - round(house["clock"]["hour"] * cfg["ticks_per_hour"])


def kept(house, cfg, p):
    """A hob's day so far, as only the house as it is now can say it."""
    mem = {"1-3": 0, "4": 0, "5": 0}
    for m in p.get("memories") or []:
        w = round(memories.fade(house, cfg, m))
        mem["5" if w >= 5 else "4" if w == 4 else "1-3"] += 1
    return {"needs": {k: round(p["needs"][k]) if k in p.get("needs", {}) else None for k in NEEDS}, "memories": mem}


def keep(house, cfg):
    """Each tick (server.snapshot): each living hob's needs and memories as they are, and every aim it has had today
    and how it went (the night clears them); when the day turns, the day's are kept as yesterday's."""
    L, day = house.setdefault("lab4", {}), house["clock"]["day"]
    if L.get("day") != day:
        if L.get("day") is not None:
            L["yesterday"] = {"day": L["day"], "pets": L.get("pets", {})}
        L.update(day=day, pets={})
    for p in alive(house):
        if p["stage"] == "egg":
            continue
        rec = L["pets"].setdefault(p["id"], {"aims": {}})
        rec.update(kept(house, cfg, p))
        for a in p.get("aims") or []:
            rec["aims"][str(a.get("text", ""))[:160]] = "done" if a.get("done") else "failed" if a.get("failed") else "open"


def aims(rec):
    a = list((rec or {}).get("aims", {}).items())
    return {"done": sum(v == "done" for _, v in a), "failed": sum(v == "failed" for _, v in a), "open": sum(v == "open" for _, v in a),
            "failed_text": [t for t, v in a if v == "failed"]}


def columns(db):
    return {r[1] for r in db.execute("PRAGMA table_info(calls)")} if db else set()


def thoughts(db, cols, pid, lo, hi):
    """Its thoughts in [lo, hi) by kind: how many, and the mean seconds each waited for its turn and was computed (one row
    an HTTP call once calls has `wait`: the thought's last row carries the wait); not-JSON replies and cut-off ones."""
    out, bad, cut = {}, 0, (0 if "finish" in cols else None)
    if not db:
        return out, None, None
    # (a thought is its last row, the one with the wait; a row from before the wait was kept, or a stub's, is one alone)
    n_ = "SUM(wait IS NOT NULL OR http IS NULL)" if {"wait", "http"} <= cols else "COUNT(*)"
    for kind, n, secs, wait, b, c in db.execute(
            "SELECT kind, %s, SUM(seconds), %s, SUM(failed LIKE 'invalid json%%'), %s FROM calls WHERE pet=? AND tick>=? AND tick<? GROUP BY kind"
            % (n_, "AVG(wait)" if "wait" in cols else "NULL", "SUM(finish='length')" if "finish" in cols else "0"), (pid, lo, hi)):
        n = n or 0
        compute = round((secs or 0) / n, 1) if n else 0
        w = round(wait, 1) if wait is not None else None
        out[kind] = {"n": n, "seconds": round(compute + (w or 0), 1), "wait": w, "compute": compute}
        bad += b or 0
        if cut is not None:
            cut += c or 0
    return out, bad, cut


def hob(house, cfg, db, cols, p, rec, lo, hi):
    talks = [t for t in house.get("talks", []) if p["id"] in (t["a"], t["b"]) and lo <= t["tick"] < hi]
    failed = house.get("failed_talks", [])   # (talk.py's list of failed talks: none yet, none failed)
    th, bad, cut = thoughts(db, cols, p["id"], lo, hi)
    return {"id": p["id"], "name": label(p), **(rec or {"needs": dict.fromkeys(NEEDS), "memories": None}), "aims": aims(rec),
            "thoughts": th, "talks": len(talks), "talks_failed": sum(p["id"] in f["pets"] and lo <= f["tick"] < hi for f in failed),
            "invalid_json": bad, "cut_off": cut}


def busy(db, lo, hi, real_seconds):
    """The share of the time the model was computing, from the log: [lo, hi) is `real_seconds` long."""
    s = db.execute("SELECT SUM(seconds) FROM calls WHERE tick>=? AND tick<?", (lo, hi)).fetchone()[0] if db else None
    return round((s or 0) / real_seconds, 3) if db and real_seconds else None


def today(eng, cfg, clients=0, last_bytes=0):
    """The "Today" section, with yesterday's beside it. `clients`, `last_bytes`: the server's websocket, as it is now."""
    h, db = eng.house, eng.db
    L, start, tpd, now = h.get("lab4") or {}, day_start(h, cfg), cfg["ticks_per_day"], h["tick"]
    cols, per_tick = columns(db), cfg["clock"]["tick_seconds"] * cfg["pace"]   # (real seconds a tick, on the live clock)
    real_hour = ticks(cfg, 3600 / cfg["pace"])
    lin = (h.get("lineage") or {}).get("id")
    born = [p for p in h["pets"].values() if p.get("lineage") == lin]
    orphans = (h.get("migrated") or {}).get("orphans")
    saved = getattr(eng, "saved_at", None)
    ytd = L.get("yesterday") if (L.get("yesterday") or {}).get("day") == h["clock"]["day"] - 1 else None
    living = [p for p in alive(h) if p["stage"] != "egg"]
    mine = L.get("pets", {}) if L.get("day") == h["clock"]["day"] else {}
    failed = h.get("failed_talks", [])
    return {
        "day": h["clock"]["day"],
        "pets": [hob(h, cfg, db, cols, p, mine.get(p["id"]) or {**kept(h, cfg, p), "aims": {}}, start, now + 1) for p in living],
        "house": {
            "save_age": round(time.time() - saved[0]) if saved else None,
            "busy_world_hour": round(sum(b[1] for b in h.get("busy", [])) / (cfg["ticks_per_hour"] * per_tick), 3),
            "busy_real_hour": busy(db, now - real_hour, now + 1, 3600),
            "busy_day": busy(db, start, now + 1, max(1, now + 1 - start) * per_tick),
            "calls_hour": sum(t > now - real_hour for t in h.get("calls", [])), "budget": cfg["model"]["calls_per_hour"],
            "eggs_laid": sum(bool(p.get("parent")) and not p.get("founder") for p in born), "eggs_found": sum(bool(p.get("founder")) for p in born),
            "reparented": None if orphans is None else len(orphans.get("parents") or {}) + len(orphans.get("siblings") or {}),
            "talks_failed": sum(start <= f["tick"] <= now for f in failed),
            "ws_clients": clients, "ws_bytes": last_bytes,
        },
        "yesterday": {
            "day": h["clock"]["day"] - 1,
            "pets": [hob(h, cfg, db, cols, h["pets"][pid], rec, start - tpd, start) for pid, rec in ((ytd or {}).get("pets") or {}).items() if pid in h["pets"]],
            "house": {"busy_day": busy(db, start - tpd, start, tpd * per_tick),
                      "talks_failed": sum(start - tpd <= f["tick"] < start for f in failed)},
        },
    }


# ---- SPEC-v4.2 §11.5: the Lab's "Spirit" ----

# every cause of death (contracts.CAUSES), as the Lab's table says it
CAUSES = {"old age": "old age", "sickness": "a sickness", "injury": "a hurt not tended", "bad food": "bad food", "killing": "killed",
          "manslaughter": "a fall", "exposure": "the cold", "starvation": "hunger", "neglect": "wasting away"}
# every line of the ledger (contracts.LEDGER), as the Lab says it
LEDGER = {"missed": "replies that lacked a new field", "acted": "beliefs acted on", "told": "tales told", "knows": "talks that left their lines",
          "refusal": "failures said in the world's terms", "secret found": "secrets found out", "happening": "the director's happenings",
          "nursed": "hobs nursed or tended", "monologue": "talks whose lines didn't answer each other (asked again)",
          "purple": "talks that read like a novel"}   # (v4.2.2 §6: monologue and purple, each under a tenth of the talks)


def thinking(db, cfg, lo, hi, pid=None):
    """Model seconds in [lo, hi) of the kinds that think (contracts.thinking), and of every kind; a hob's with `pid`."""
    if not db:
        return None, None
    rows = db.execute("SELECT kind, SUM(seconds) FROM calls WHERE tick>=? AND tick<?%s GROUP BY kind" % (" AND pet=?" if pid else ""),
                      (lo, hi) + ((pid,) if pid else ())).fetchall()
    return round(sum(s or 0 for k, s in rows if K.thinking(cfg, k)[0]), 1), round(sum(s or 0 for _, s in rows), 1)


def mind_of(t, p):
    """A hob's side of a talk (§7.2), by the name the reply used for it."""
    m = K.talk_minds(t)
    return m.get(label(p)) or m.get(p.get("name") or "") or {}


def spirit_hob(eng, cfg, p, lo, hi):
    h, mind = eng.house, eng.minds.get(p["id"])
    mems = [K.memory(m) for m in p.get("memories") or []]
    heavy = [m for m in mems if m["weight"] >= 4]
    beliefs = [b for b in (mind.mem.beliefs if mind else []) if b.get("status", "active") == "active"]
    sides = [mind_of(t, p) for t in h.get("talks", []) if p["id"] in (t["a"], t["b"]) and lo <= t["tick"] < hi]
    return {"id": p["id"], "name": label(p),
            "memories": {"model": sum(m["by"] == "model" for m in mems), "engine": sum(m["by"] != "model" for m in mems),
                         "heavy_model": sum(m["by"] == "model" for m in heavy), "heavy": len(heavy)},
            "beliefs": {"hooked": sum(bool(K.hook(b.get("hook"))) for b in beliefs), "acted_today": sum(r.get("pet") == p["id"] for r in K.since(h, "acted", lo))},
            "talks": len(sides), "knows": sum(bool(s.get("knows")) for s in sides), "wants_holds": sum(bool(s.get("wants") and s.get("holds")) for s in sides),
            "thinking_seconds": thinking(eng.db, cfg, lo, hi, p["id"])[0]}


def spirit(eng):
    """§11.5, as plain data (the rehearsal writes it out as JSON). Per living hob: its memories model-written and
    mechanical (all, and the heavy ones), its beliefs with hooks and those acted on today, its talks today with the
    `knows` lines and the `wants/holds` it left, its thinking seconds today. The house: deaths by cause this lineage, the
    week's happenings, who is sick or hurt now, tales kept and told this week, each hob's theory of the visitor,
    thinking's share of the model's time today, and every ledger line (today, this week) with the fields the model's
    replies lacked this week."""
    h, cfg = eng.house, eng.cfg
    lo, now, tpd = day_start(h, cfg), h["tick"], cfg["ticks_per_day"]
    week, lin = now - 7 * tpd, (h.get("lineage") or {}).get("id")
    living = [p for p in alive(h) if p["stage"] != "egg"]
    deaths = dict.fromkeys(CAUSES, 0)
    for p in h["pets"].values():
        if p["stage"] == "dead" and p.get("lineage") == lin:
            c = K.OLD_CAUSE.get(p.get("cause"), p.get("cause")) or "old age"
            deaths[c] = deaths.get(c, 0) + 1
    think, total = thinking(eng.db, cfg, lo, now + 1)
    missed = Counter("%s.%s" % (r.get("kind"), f) for r in K.since(h, "missed", week) for f in r.get("fields") or [])
    return {
        "day": h["clock"]["day"],
        "pets": [spirit_hob(eng, cfg, p, lo, now + 1) for p in living],
        "house": {
            "deaths": deaths,
            "happenings": [{"day": clock(cfg, r["tick"])["day"], "name": r.get("name"), "target": label(h["pets"][r["target"]]) if r.get("target") in h["pets"] else r.get("target")}
                           for r in K.since(h, "happening", week)],
            "unwell": [{"name": label(p), "sick": (p.get("sick") or {}).get("level"), "hurt": (p.get("hurt") or {}).get("level")}
                       for p in living if p.get("sick") or (p.get("hurt") or {}).get("level")],
            "tales": {"kept": len(h.get("tales") or []), "told_week": len(K.since(h, "told", week))},
            "theories": [{"name": label(p), "theory": p.get("visitor_theory") or ""} for p in living],
            "thinking_share": None if total is None else round(think / total, 3) if total else 0.0,
            "ledger": {w: {"says": says, "today": len(K.since(h, w, lo)), "week": len(K.since(h, w, week))} for w, says in LEDGER.items()},
            "missed_fields": dict(missed.most_common()),
        },
    }


# ---- SPEC-v5.0 §5 (helper C): the Lab's "Jobs" ----

# every deficit (contracts.DEFICITS), as the Lab's rows say it; the board's words for one B has not worded
DEFICIT_WORDS = {"cold": "cold at night", "dark": "dark at night", "mess": "a mess", "leak": "a leak", "food_low": "food running low",
                 "food_spoiling": "food spoiling", "mouse": "a mouse in the stores", "no_bed": "slept on the floor", "sick_untended": "ill and untended",
                 "broken": "a thing broken", "works_goal": "the Works' goal", "gate_shut": "the gate shut", "own_box": "no box of its own",
                 "own_tool": "no tool for its craft", "own_light": "working in the dark"}


def jobs(eng):
    """§5, as plain data: today's deficits by kind (open on the board now, opened and closed today, jobs taken); per living
    hob its jobs taken, its idle share (ticks in leisure while a job it fits was open, of its ticks awake: §3.4 wants it
    under a tenth), its scrap and what it earned and spent; why things were made ("nothing" should read 0); the economy;
    items broken and mended by kind; verbs used by verb; and the board's size."""
    h = eng.house
    c, b = K.counts(h), K.board((h.get("v5") or {}).get("board"))
    on_board = Counter(d["kind"] for d in b["deficits"])
    share = lambda idle, awake: round(idle / awake, 3) if awake else None
    pets = [{"id": p["id"], "name": label(p), "taken": c["taken"].get(p["id"], 0), "idle": c["idle"].get(p["id"], 0), "awake": c["awake"].get(p["id"], 0),
             "idle_share": share(c["idle"].get(p["id"], 0), c["awake"].get(p["id"], 0)), "scrap": int(p.get("scrap") or 0),
             "earned": c["scrap_earned"].get(p["id"], 0), "spent": c["scrap_spent"].get(p["id"], 0)} for p in alive(h) if p["stage"] != "egg"]
    return {
        "day": h["clock"]["day"],
        "deficits": [{"kind": k, "says": DEFICIT_WORDS[k], "open": on_board[k], "opened": c["opened"].get(k, 0), "closed": c["closed"].get(k, 0),
                      "taken": c["taken_kind"].get(k, 0)} for k in K.DEFICITS],
        "pets": pets,
        "idle_share": share(sum(c["idle"].values()), sum(c["awake"].values())),
        "made_for": {k: c["made_for"].get(k, 0) for k in K.MADE_FOR},
        "economy": {"earned": sum(c["scrap_earned"].values()), "spent": sum(c["scrap_spent"].values()), "held": sum(p["scrap"] for p in pets)},
        "broke": c["broke"], "mended": c["mended"],
        "verbs": {v: c["verbs"].get(v, 0) for v in K.VERBS},
        "board": {"open": len(b["deficits"]), "jobs": len(b["jobs"]), "taken": sum(bool(j["taker"]) for j in b["jobs"]), "closed": len(b["closed"])},
    }


# ---- SPEC-v4.2 §11.1, §11.2: what the page reads of C's fields ----

def card(house, p):
    """§11.2 the card's lines from C's fields, in words: its drive (and for "to be loved by one", whom), its flaw, its
    voice in one line, and its secret: only that it keeps one, until it is found out (its words are never sent before)."""
    out = {}
    if p.get("drive"):
        d = K.drive(p["drive"])
        who = house["pets"].get(d["target"] or "")
        out["drive"] = d["name"] + (" (%s)" % label(who) if who and d["name"] == "to be loved by one" else "")
    if p.get("flaw"):
        out["flaw"] = K.flaw(p["flaw"])["name"]
    if p.get("voice"):
        out["voice"] = K.voice_line(p["voice"])
    if p.get("secret"):
        s = K.secret(p["secret"])
        out["secret"] = {"found": True, "text": s["text"]} if s["found"] is not None else {"found": False}
    from .talk import threads   # SPEC-v5.3 §8 (helper C): its open threads, in words
    th = ["with %s, about %s (%s)" % (label(house["pets"][t["with"]]) if t["with"] in house["pets"] else "someone", t["subject"], t["question"]) for t in threads(house, p)]
    if th:
        out["threads"] = th
    return out


def talk_view(house, t):
    """§11.1 a talk as the page reads it: its speakers' minds (§7.2) by hob id rather than by the name the reply used."""
    m = K.talk_minds(t)
    if not m:
        return t
    ids = {}
    for x in (t.get("a"), t.get("b")):
        q = house["pets"].get(x)
        if q:
            ids.update({label(q).lower(): x, (q.get("name") or label(q)).lower(): x})
    return dict(t, minds={ids.get(n.lower(), n): v for n, v in m.items()})


# ---- SPEC-v5.1 §8 (helper C): the Lab's "Grammar", the header's tier, a hob's knowing, a thing's recipe ----

def knowing(p):
    """(recipes it knows, kinds it knows of), as pet["knows"] (B's) has them, each a name."""
    name = lambda k: k[5:] if k.startswith("kind:") else k.replace("|", " by ")
    ks = {k: K.knowledge(v) for k, v in (p.get("knows") or {}).items()}
    return sorted(name(k) for k, v in ks.items() if not v["of"]), sorted(name(k) for k, v in ks.items() if v["of"])


def header(house, cfg):
    """§5.2, §8 the header's line, B's knowledge.words, as the house's tier in words and its fall while it is recent
    ("nobody left knows the forge")."""
    from . import knowledge
    tier, _, fall = knowledge.words(house, cfg).partition("; ")
    return {"tier": tier, "fall": fall or None}


def recipe_view(house, cfg, kind):
    """§8 a thing's recipe for its card: each part (its compositor part, `draw`, and its PixelLab cell, `icon`) of its
    material, the charge, what it does in words, its tier, who living knows how to make it, and, for an invention, who
    invented it, for what, and how it works in the inventor's words; its drawn sprite once it has one. None for a kind
    with no recipe."""
    from . import grammar
    r = grammar.recipe(house, cfg, kind)
    if not r or not r["parts"]:
        return None
    D, key = grammar.data()["part"], K.key_of(kind)
    by = house["pets"].get(r["by"] or "")
    from . import knowledge
    who = [label(p) for p in alive(house) if p["stage"] != "egg" and not (knowledge.knows(house, p, key) or {"of": True})["of"]]
    return {"parts": [{"part": x["part"], "material": x["material"], "draw": D[x["part"]]["draw"], "icon": D[x["part"]]["icon"]} for x in r["parts"]],
            "materials": list(dict.fromkeys([x["material"] for x in r["parts"]] + ([r["charge"]] if r["charge"] else []))), "charge": r["charge"],
            "does": [K.VERB_WORDS[v] for v in sorted(r["verbs"], key=lambda v: -r["verbs"][v])], "tier": K.TIER_WORDS[r["tier"]], "knows": who,
            "invented": {"by": label(by) if by else "someone long gone", "by_id": r["by"], "for": r["for"], "how": r["how"]} if r["by"] else None,
            "sprite": r["sprite"]}


def grammar(eng):
    """§8, as plain data, over the days the counters keep (fourteen; a rehearsal's ten): inventions proposed, accepted
    and refused, with the refusals' words counted; things made by recipe and by invention; the recipes each living hob
    knows and the house's; the house's tier by day; study sessions and teachings (B's); reads by where the question
    came from, and chains of three read on (B's); sprites drawn by PixelLab, composited, or failed."""
    from .grammar import tier
    h, cfg = eng.house, eng.cfg
    days = sorted((h.get("v5") or {}).get("counts", {}), key=int)
    c = {k: Counter() for k in K.COUNTS51}
    for d in days:
        for k, v in K.counts(h, int(d)).items():
            if k in c:
                c[k].update(v)
    pets, house_known = [], set()
    for p in (p for p in alive(h) if p["stage"] != "egg"):
        made, of = knowing(p)
        house_known |= set(made)
        pets.append({"id": p["id"], "name": label(p), "tier": K.TIER_WORDS[tier(h, cfg, p)], "recipes": len(made), "of": len(of), "read": len(p.get("read") or []),
                     "studied": c["studied"].get(p["id"], 0), "taught": c["taught"].get(p["id"], 0), "chains": c["chain"].get(p["id"], 0)})
    tiers = (h.get("v5") or {}).get("tier")
    return {
        "day": h["clock"]["day"], "days": len(days),
        "invent": {"proposed": c["invent"].get("proposed", 0), "accepted": c["invent"].get("accepted", 0), "refused": sum(c["refused"].values())},
        "refused": [{"words": w, "n": n} for w, n in c["refused"].most_common(12)],
        "made_by": {k: c["made_by"].get(k, 0) for k in ("recipe", "invention")},
        "recipes": {"house": len(house_known)}, "pets": pets,
        "tier": [{"day": int(d), "tier": t, "words": K.TIER_WORDS[t]} for d, t in sorted(tiers.items(), key=lambda x: int(x[0])) if isinstance(t, int)] if isinstance(tiers, dict) else [],
        "studied": sum(c["studied"].values()), "taught": sum(c["taught"].values()),
        "read": {q: c["read"].get(q, 0) for q in K.QUESTIONS + ("on",)}, "chains": sum(c["chain"].values()),
        "sprites": {k: c["sprites"].get(k, 0) for k in ("generated", "composited", "failed")},
    }


# ---- SPEC-v5.3 §8 (helper C): the Lab's "Life" ----

# the plain facts each module records (contracts.EVENTS53), in words for the Lab
EVENT_WORDS = {"habit": "habits' goes", "marked": "marks left or grown", "noticed": "marks noticed", "mess": "piles counted as mess",
               "moved": "another's pile or thing moved", "taken": "things taken", "missed": "things missed by their owners",
               "found": "hoards found", "opinion": "opinions moved by a habit", "resent": "resentments", "praise": "praises given",
               "project": "projects changing state", "step": "project steps", "slept_out": "nights slept out", "came_in": "comings in from a shelter",
               "bond": "bonds rising", "taken_up": "orphans taken up", "round": "rounds past the first", "thread": "threads left or picked up",
               "third": "a third hob's lines"}
# §6's scenes (contracts.SCENES), in words
SCENE_WORDS = {"pile": "a pile counted as mess, moved, and resented", "hoard": "a hoard found, and opinions of its keeper fall",
               "shelter": "a shelter built over days, slept in, and come in from for food", "praise": "praise given, pride raised, and resented",
               "joint": "a joint project finished, and its owners closer", "orphan": "an orphaned project taken up by kin",
               "thread": "a talk of three rounds left open and picked up"}


def life(eng):
    """§8, as plain data, over the days the counters keep (fourteen): habits by hob and by template; marks left and
    noticed; projects by state and kind, steps done today, orphans and take-ups; talks by rounds, threads left and
    picked up (and open now), the third hob's lines; the idle share with the reading hour out (`idle53`, of the hob's
    ticks awake); each of §6's scenes with how often it happened (engine/scenes.py), and every fact recorded."""
    from . import scenes
    from .talk import threads
    h, cfg = eng.house, eng.cfg
    days = sorted((h.get("v5") or {}).get("counts", {}), key=int)
    c = {k: Counter() for k in K.COUNTS53 + ("awake",)}
    for d in days:
        for k, v in K.counts(h, int(d)).items():
            if k in c:
                c[k].update(v)
    today = K.counts(h)
    share = lambda idle, awake: round(idle / awake, 3) if awake else None
    pets = [{"id": p["id"], "name": label(p), "habits": [{"name": x.get("name"), "count": x.get("count", 0), "fading": bool(x.get("fading"))} for x in p.get("habits") or [] if isinstance(x, dict)],
             "steps_today": today["steps"].get(p["id"], 0), "third": c["third"].get(p["id"], 0), "threads": len(threads(h, p)),
             "idle53": c["idle53"].get(p["id"], 0), "idle_share": share(c["idle53"].get(p["id"], 0), c["awake"].get(p["id"], 0))}
            for p in alive(h) if p["stage"] != "egg"]
    prs = list(((h.get("v5") or {}).get("projects") or {}).values())
    found = scenes.find(h, tpd=cfg["ticks_per_day"])
    return {
        "day": h["clock"]["day"], "days": len(days), "pets": pets,
        "habit": {n: c["habit"].get(n, 0) for n in K.HABITS},
        "marks": {k: c["marks"].get(k, 0) for k in K.MARKS}, "noticed": {k: c["noticed"].get(k, 0) for k in K.MARKS},
        "projects": {st: dict(Counter(p["kind"] for p in prs if p.get("state") == st)) for st in K.PROJECT_STATES},
        "changes": {st: c["projects"].get(st, 0) for st in K.PROJECT_STATES},
        "steps": sum(today["steps"].values()), "orphans": sum(p.get("state") == "orphaned" for p in prs), "taken_up": len(K.events53(h, "taken_up")),
        "rounds": {n: c["rounds"].get(n, 0) for n in ("1", "2", "3")},
        "threads": {"left": c["threads"].get("left", 0), "picked": c["threads"].get("picked", 0), "open": sum(x["threads"] for x in pets) // 2},
        "third": sum(c["third"].values()),
        "idle_share": share(sum(c["idle53"].values()), sum(c["awake"].values())),
        "scenes": [{"scene": k, "says": SCENE_WORDS[k], "n": len(found[k]), "last": found[k][-1] if found[k] else None} for k in K.SCENES],
        "events": [{"event": k, "says": EVENT_WORDS[k], "n": len(K.events53(h, k))} for k in K.EVENTS53],
    }
