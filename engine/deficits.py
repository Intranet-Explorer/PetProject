"""SPEC-v5.0 §2 (helper B): what is wrong with the house, every `[deficits] every` ticks, kept on the work board.

Each detector (`DETECT`, one for every kind in contracts.DEFICITS) looks at the house as it stands and returns what it
sees wrong, as deficit records without their `since`. `tick` dedups them by id (kind|where|who), keeps the `since` of
one already open, opens the new ones and closes the ones no detector sees any more: a closing is a moment in plain
words, credited to whoever's job it was ("the attic is warm tonight: Pansy's blanket"). The board is
house["v5"]["board"] (contracts.board; house["board"] is the hub's news board). Words never carry a number (§3.5).

Readings of the table (DECISIONS Part 43): `cold` and `dark` are a room's standing condition, looked for all day,
so a night's cold is a job by day and does not close itself at dawn. A hob lies down wherever it is when sleep comes
(tick.sleep_tick), so a cover or a bed is judged by the room and the hob, not one tile: cold is a room someone slept in,
in autumn or winter (or a cold snap), with no heat in it and fewer loose things that cover than sleepers; no_bed is a
hob with no bed of its own (holds and covers) and none where it slept; dark is a room someone sleeps in with
no working light, or, at night, a room with someone awake in it and no light lit. "A day's eating" is two servings a
hob (the routine's two meals). Switch: [deficits] on (on5)."""
from . import contracts as K
from . import health, items, order
from .world import days as world_days, dist, label, moment

MEALS = 2   # servings a hob eats in a day (planner's routine: breakfast and lunch)
GROWN = ("adult", "elder")
SKILL_TOOL = {"tending": "trowel", "fishing": "rod", "making": "carver", "mending": "hammer", "tidying": "broom"}   # own_tool: the tool a skill wants
CLOSED = {"cold": "%(room)s is warm tonight", "dark": "%(room)s has a light", "mess": "%(room)s is tidy again", "leak": "the leak in %(room)s is mended",
          "food_low": "the stores have food again", "food_spoiling": "the food in %(room)s is kept", "mouse": "the mouse is out of %(room)s",
          "no_bed": "%(who)s has a bed", "sick_untended": "%(who)s has been looked after", "broken": "the %(what)s is mended",
          "works_goal": "the Works has its scrap", "gate_shut": "the garden gate is open again", "own_box": "%(who)s has a box of its own",
          "own_tool": "%(who)s has a tool of its own", "own_light": "%(who)s has a light to work by"}


def on(cfg):
    return K.on5(cfg, "deficits")


def board(house):
    """The work board, made on first use (contracts.board's shape)."""
    return house.setdefault("v5", {}).setdefault("board", K.board({}))


def rooms(house):
    return [r for r in house["rooms"].values() if r["type"]]


def living(house):
    return [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")]


def night(house):
    return house["clock"]["phase"] == "night"


def at(house, cfg, rid, pos, verb, both=None):
    """The strongest working thing at a verb lying within a tile of `pos` in a room (and, `both`, at that verb too)."""
    room = house["rooms"][rid]
    return max((K.works(it, verb) for n, it in items.objects(house, cfg, room) if not room["objects"][n].get("on") and not room["objects"][n].get("wall")
                and dist(room["objects"][n].get("pos") or [99, 99], pos) <= 1 and (not both or K.works(it, both))), default=0.0)


def covers(house, cfg, rid):
    """How many things lie loose in a room that cover a sleeper (a hob lies down where it stands: cold and a bed are
    the room's and the hob's, not one tile's)."""
    room = house["rooms"][rid]
    return sum(1 for n, it in items.objects(house, cfg, room) if K.works(it, "cover") and not room["objects"][n].get("on") and not room["objects"][n].get("wall"))


def bed_of(house, cfg, pet):
    """Its own bed (a thing that holds and covers it), or one at the place it slept."""
    return any(K.works(it, "cover") and K.works(it, "hold") for _, _, it in items.find(house, cfg, verb="cover", owner=pet["id"])) \
        or bool(at(house, cfg, pet["sleeps_in"], pet["sleeps_at"], "cover", "hold"))


def sleepers(house):
    """{room id: [the hobs that sleep there]}."""
    out = {}
    for p in living(house):
        if p.get("sleeps_in") in house["rooms"] and p.get("sleeps_at"):
            out.setdefault(p["sleeps_in"], []).append(p)
    return out


def d(kind, where=None, who=None, urgency=None, **more):
    return dict(K.deficit({"kind": kind, "where": where, "who": who, "urgency": urgency}), **more)


# ---- the detectors: (house, cfg) -> [deficit] ----

def d_cold(house, cfg):
    if house["clock"]["season"] not in ("autumn", "winter") and house.get("cold_snap", -1) <= house["tick"]:
        return []
    out = []
    for rid, ps in sorted(sleepers(house).items()):
        if items.strength(house, cfg, rid, "heat") > 0 or covers(house, cfg, rid) >= len(ps):
            continue
        out.append(d("cold", rid, urgency=4 if any(health.stage_of(p) for p in ps) else 3))
    return out


def d_dark(house, cfg):
    out, slept = [], sleepers(house)
    for r in rooms(house):
        up = night(house) and any(p["room"] == r["id"] and not p["sleep"] for p in living(house))
        if (r["id"] in slept and not items.strength(house, cfg, r, "light")) or (up and not items.strength(house, cfg, r, "light", lit_only=True)):
            out.append(d("dark", r["id"]))
    return out


def mess_count(house, cfg, r):
    return len(order.loose_bits(r)) + sum(1 for _, it in items.objects(house, cfg, r) if it["state"]["broken"])


def d_mess(house, cfg):
    most = cfg["deficits"]["mess_at"]
    return [d("mess", r["id"], urgency=1 if n <= 2 * most else 2) for r in rooms(house) for n in [mess_count(house, cfg, r)] if n > most]


def d_leak(house, cfg):
    return [d("leak", r["id"]) for r in rooms(house) if r.get("wet_until", -1) > house["tick"]]


def food(house, cfg):
    """Servings the house has: food bits put by, lying ready or carried, a bowl's servings, the pot's."""
    F = cfg["seasons"]["food"]["bits"]
    return sum(1 for r in rooms(house) for s in r["spots"] if s["bit"] in F and s.get("ready", True) and not s.get("spoiled")) \
        + sum((o.get("servings") or 0) if "meal" in o.get("fix", {}) else (o.get("pot") or {}).get("servings", 0) for r in rooms(house) for o in r["objects"].values()) \
        + sum(b in F for p in living(house) for b in p["carrying"])


def d_food_low(house, cfg):
    return [d("food_low")] if food(house, cfg) < MEALS * len(living(house)) else []


def spoiling(house, cfg, r):
    """Food put by in this room that will spoil within a day, not in a cool thing."""
    if not health.deaths(cfg):
        return []
    F, last = cfg["seasons"]["food"]["bits"], (cfg["deaths"]["spoil_days"] - 1) * cfg["ticks_per_day"]
    return [s for s in r["spots"] if s["bit"] in F and s.get("on") and not s.get("spoiled") and house["tick"] - s.get("put", house["tick"]) >= last
            and not items.stored_in(house, cfg, r, s, "cool")]


def d_food_spoiling(house, cfg):
    return [d("food_spoiling", r["id"]) for r in rooms(house) if spoiling(house, cfg, r)]


def stores(house, cfg, r):
    """Is this a room food is kept in (the storeroom, the cellar, or food put by or lying here, not shut away)?"""
    F = cfg["seasons"]["food"]["bits"]
    return r["type"] in ("storeroom", "cellar") or any(s["bit"] in F and not items.stored_in(house, cfg, r, s, "store") for s in r["spots"] if s.get("loose"))


def d_mouse(house, cfg):
    return [d("mouse", c["room"]) for c in house["creatures"] if c["kind"] == "mouse" and not c.get("tame") and c["room"] in house["rooms"]
            and house["rooms"][c["room"]]["type"] and stores(house, cfg, house["rooms"][c["room"]])]


def d_no_bed(house, cfg):
    return [d("no_bed", rid, p["id"]) for rid, ps in sorted(sleepers(house).items()) for p in ps if not bed_of(house, cfg, p)]


def d_sick_untended(house, cfg):
    if not health.deaths(cfg):
        return []
    return [d("sick_untended", p["room"], p["id"]) for p in living(house) if health.need_of(house, p) > 0]


def d_broken(house, cfg):
    return [d("broken", it["id"], it["owner"], urgency=3 if it["id"].startswith(items.WHO) else 1, room=rid, name=n)
            for rid, n, it in items.find(house, cfg, working=False) if "n" not in it and it["state"]["broken"]]


def d_works_goal(house, cfg):
    from . import machine, works
    g, at_ = works.goal(house, cfg), machine.found(house)
    if g is cfg["works"].get("forever"):   # (20 October 2026: the house store is not a deficit; only the real build list is)
        return []
    return [d("works_goal", at_["id"], goal=g["what"])] if g and at_ else []


def d_gate_shut(house, cfg):
    from . import outdoors
    V = house.setdefault("v5", {})
    if not outdoors.usable(house, cfg) or not outdoors.gate_room(house):
        V.pop("gate_shut", None)
        return []
    why = outdoors.why_shut(house, cfg)
    if why in (None, "shut"):
        V.pop("gate_shut", None)
        return []
    if why in ("night", "dusk"):   # (the night shuts it every day: the weather's day goes on through it)
        since = V.get("gate_shut")
    else:
        since = V.setdefault("gate_shut", house["tick"])
    wants_out = [p for p in living(house) if (p.get("drive") or {}).get("name") == "to leave the house" or any(w.get("room") in outdoors.OUT for w in p.get("wants", []))]
    if since is None or world_days(cfg, since, house["tick"]) < 1 or not wants_out:
        return []
    return [d("gate_shut", outdoors.gate_room(house), wants_out[0]["id"])]


def owns(house, cfg, pet, ok):
    return any(ok(it) for _, _, it in items.find(house, cfg, owner=pet["id"]) if "n" not in it)


def d_own_box(house, cfg):
    return [d("own_box", None, p["id"]) for p in living(house) if p["stage"] in GROWN and not owns(house, cfg, p, lambda it: it["class"] == "store" and K.works(it, "hold"))]


def tool_of(cfg, pet):
    """The tool its best skill wants, or None."""
    from . import craft
    best = max(SKILL_TOOL, key=lambda s: (craft.skill(cfg, pet, s), s))
    return SKILL_TOOL[best] if craft.skill(cfg, pet, best) >= 1 else None


def d_own_tool(house, cfg):
    return [d("own_tool", None, p["id"], tool=t) for p in living(house) if p["stage"] in GROWN for t in [tool_of(cfg, p)]
            if t and not owns(house, cfg, p, lambda it: it["kind"] == t and not it["state"]["broken"])]


def d_own_light(house, cfg):
    if not night(house):
        return []
    from .body import state
    return [d("own_light", p["room"], p["id"]) for p in living(house) if not p["sleep"] and p["stage"] in GROWN
            and not (state(p)["now"] or {}).get("passive") and not items.strength(house, cfg, p["room"], "light", lit_only=True)
            and not owns(house, cfg, p, lambda it: K.works(it, "light"))]


DETECT = {"cold": d_cold, "dark": d_dark, "mess": d_mess, "leak": d_leak, "food_low": d_food_low, "food_spoiling": d_food_spoiling, "mouse": d_mouse,
          "no_bed": d_no_bed, "sick_untended": d_sick_untended, "broken": d_broken, "works_goal": d_works_goal, "gate_shut": d_gate_shut,
          "own_box": d_own_box, "own_tool": d_own_tool, "own_light": d_own_light}


# ---- in words (no numbers) ----

def place(house, where):
    r = house["rooms"].get(where or "")
    return r["name"] if r else "the house"


def who_(house, who):
    p = house["pets"].get(who or "")
    return label(p) if p else "someone"


def thing_words(house, d):
    """A broken thing: "Pansy's lantern", "the work lamp"."""
    o = house["rooms"].get(d.get("room") or "", {}).get("objects", {}).get(d.get("name") or "")
    kind = ((o or {}).get("item") or {}).get("kind") or d.get("name") or "thing"
    return "%s's %s" % (who_(house, d["who"]), kind) if house["pets"].get(d.get("who") or "") else "the %s" % (d.get("name") or kind)


def words(house, cfg, d):
    """API5: the deficit in plain words, for the board and the packets."""
    k, room, who = d["kind"], place(house, d.get("where")), who_(house, d.get("who"))
    if k == "cold":
        return "%s is cold at night" % room
    if k == "dark":
        return "%s is dark" % room
    if k == "mess":
        return "%s is a mess" % room
    if k == "leak":
        return "water is coming into %s" % room
    if k == "food_low":
        return "the stores are low on food"
    if k == "food_spoiling":
        return "the food put by in %s will spoil soon" % room
    if k == "mouse":
        return "%s has a mouse" % room
    if k == "no_bed":
        return "%s sleeps on the floor" % who
    if k == "sick_untended":
        p = house["pets"].get(d.get("who") or "") or {}
        return "%s is %s in %s and nobody has looked in" % (who, "ill" if p.get("sick") else "hurt", place(house, p.get("room")))
    if k == "broken":
        return "%s is broken" % thing_words(house, d)
    if k == "works_goal":
        return "the Works wants scrap for %s" % d.get("goal", "the house")
    if k == "gate_shut":
        return "the weather has kept the garden gate shut, and %s wants out" % who
    if k == "own_box":
        return "%s has nowhere of its own to keep things" % who
    if k == "own_tool":
        return "%s has no %s of its own" % (who, d.get("tool") or "tool")
    return "%s is working in the dark" % who


# ---- the board ----

def scan(house, cfg):
    """API5: what is wrong now, each with its words (a detector that throws is skipped, never the scan)."""
    import logging
    out = {}
    for kind, f in DETECT.items():
        try:
            found = f(house, cfg)
        except Exception:
            logging.exception("deficit detector %s failed", kind)
            continue
        for x in found:
            x["words"] = words(house, cfg, x)
            out.setdefault(x["id"], x)
    return list(out.values())


def rank(house, cfg, d):
    """Urgency x age (a day open counts double)."""
    return d["urgency"] * (1 + world_days(cfg, d["since"], house["tick"]))


def tick(house, cfg):
    """API5: every `[deficits] every` ticks: scan, dedup by id, open the new (counted), close the gone (counted, a
    moment credited `by` the taker of a job of it), keep today's closed, rank the open."""
    if not on(cfg) or house["tick"] % max(1, cfg["deficits"]["every"]):
        return
    B, now, t = board(house), {x["id"]: x for x in scan(house, cfg)}, house["tick"]
    was = {x["id"]: x for x in B["deficits"]}
    for i, x in now.items():
        old = was.get(i)
        if old:
            x.update(since=old["since"], **{k: old[k] for k in ("by", "thing", "next_job") if old.get(k)})
        else:
            x["since"] = t
            K.count(house, "opened", x["kind"])
    for i, x in was.items():
        if i not in now:
            close(house, cfg, x)
    B["deficits"] = sorted(now.values(), key=lambda x: (-rank(house, cfg, x), x["id"]))
    day0 = t - t % cfg["ticks_per_day"]
    B["closed"] = [c for c in B["closed"] if c["tick"] >= day0]
    B["tick"] = t


def close(house, cfg, x):
    """A deficit no detector sees any more: closed, in words, credited to whoever's job it was."""
    t = house["tick"]
    x.update(closed=t)
    K.count(house, "closed", x["kind"])
    fields = {"room": place(house, x.get("where")), "who": who_(house, x.get("who")), "what": x.get("name") or "thing"}
    said = CLOSED[x["kind"]] % fields
    by = house["pets"].get(x.get("by") or "")
    if by:
        said += ": %s" % (x.get("thing") or "%s saw to it" % label(by))
    board(house)["closed"].append({"kind": x["kind"], "where": x.get("where"), "who": x.get("who"), "by": x.get("by"), "tick": t, "words": said})
    moment(house, "fixed", said, x.get("by"), x["where"] if x.get("where") in house["rooms"] else None)
