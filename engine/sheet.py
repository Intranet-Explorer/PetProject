"""The sheet (24 November 2026): a favourite place, a pursuit, a fear and a favourite food for every hob, drawn at
random, which the body's score reads at a size that competes with what every hob shares (config.toml [sheet];
sheet.toml has the catalogue). The body is two thirds of a hob's waking day, and until now temperament moved its
score by about 0.3 where the rotation terms moved it by 2 to 7: six hobs did the same things. No model is asked.

    lean(house, cfg, pet, L)             body.targets: its favourite place is somewhere it makes for
    adjust(house, cfg, pet, name, A, t)  body.score: what its sheet adds to or takes from this activity and target
    give(house, cfg, pet)                a sheet for a hob that has none (character.tick: at hatching, and the living once)
    words(cfg, pet)                      its sheet as the hob is told it (character.describe)
"""
from .world import rnd

SLOTS = ("pursuit", "fear", "food")
FEARS = {"dark": "the dark", "sky": "the open sky", "machines": "the machines", "creatures": "small creatures"}   # a fear's name on a card, where its key does not read


def on(cfg):
    return bool(cfg.get("sheet", {}).get("on"))


def scale(cfg):
    """How many times over a hob's temperament and traits count in the body's score (1 with the sheet off)."""
    return cfg["sheet"]["temper"] if on(cfg) else 1.0


def turns(cfg):
    """What is left of the body's taking turns at everything (handle, fresh, stride) with the sheet on (1 with it off)."""
    return cfg["sheet"]["turns"] if on(cfg) else 1.0


def seek(cfg):
    """How many times over a hob it seeks out, or avoids, counts ([planner] seek; 1 with the sheet off)."""
    return cfg["sheet"]["seek"] if on(cfg) else 1.0


def table(cfg, slot, pet):
    return cfg["sheets"].get(slot, {}).get((pet.get("sheet") or {}).get(slot) or "", None)


def pursues(cfg, pet, name):
    p = table(cfg, "pursuit", pet)
    return bool(p) and name in p["does"]


def place(house, pet):
    """The id of its favourite room, or None (none on its sheet, or the house has no such room now)."""
    want = (pet.get("sheet") or {}).get("place")
    return next((r["id"] for r in house["rooms"].values() if r["type"] == want), None) if want else None


def feared(house, cfg, pet, rid):
    f = table(cfg, "fear", pet)
    return bool(f) and house["rooms"][rid]["type"] in f.get("rooms", ())


def shuns(house, cfg, pet, kind, rid=None):
    """Is an aim or a job of this kind (in this room) the very thing it is afraid of? (jobs.may: it does not take it.)"""
    from . import planner
    f = table(cfg, "fear", pet)
    if not f:
        return False
    dos = {cfg["activities"][n]["do"] for n in f.get("does", ()) if n in cfg["activities"]}
    return bool(dos & set(planner.aim_of(kind)[0])) or bool(rid and rid in house["rooms"] and feared(house, cfg, pet, rid))


def free(house, cfg, pet):
    """May its favourite place call it now? Not at a meal it is hungry for: the day's needs come first."""
    from . import planner
    return not (planner.on(cfg) and planner.slot(house, cfg) in ("breakfast", "lunch") and planner.hungry(pet, 1))


def grounds(house, cfg, pet):
    """The ids of the rooms its pursuit is done in, if it is one that has rooms (fishing: the pond room), that it knows."""
    p = table(cfg, "pursuit", pet)
    if not p:
        return set()
    known = [r for r in house["rooms"].values() if r["type"] and r["id"] in pet["rooms"]]
    out = {r["id"] for r in known if r["type"] in p.get("rooms", ())}
    seeks = p.get("seeks")   # a pursuit with no room of its own goes looking for what it is done with
    if seeks == "toys":
        out |= {r["id"] for r in known if any("toy" in o.get("fix", {}) for o in r["objects"].values())}
    elif seeks == "creatures":
        out |= {c["room"] for c in house["creatures"] if c["kind"] not in ("sweeper", "train") and c["room"] in pet["rooms"]}
    elif seeks == "book":
        from . import wants
        out |= {wants.book_room(house)} & set(pet["rooms"])
    elif seeks == "mess":
        out |= {r["id"] for r in known if r.get("mess", 0) >= 1}
    elif seeks == "kin":
        out |= {x["room"] for x in house["pets"].values() if x["id"] != pet["id"] and x["stage"] not in ("egg", "dead") and not x["sleep"] and x["room"] in pet["rooms"]}
    return out


def door(house, cfg, pet):
    """The door toward where its pursuit is done, else toward its favourite place; None if it is there, or the day's needs come first."""
    from .body import way_to
    if not free(house, cfg, pet):
        return None
    g = grounds(house, cfg, pet) or ({place(house, pet)} - {None})
    return way_to(house, pet, g) if g and pet["room"] not in g else None


def lean(house, cfg, pet, L):
    rid = place(house, pet)
    if rid and rid != pet["room"] and rid in pet["rooms"] and free(house, cfg, pet):
        L["rooms"].add(rid)
    g = grounds(house, cfg, pet)
    if g and pet["room"] not in g and free(house, cfg, pet):
        L["rooms"] |= g


def adjust(house, cfg, pet, name, A, t):
    Q, s, do = cfg["sheet"], 0.0, A["do"]
    room = house["rooms"][pet["room"]]
    p = table(cfg, "pursuit", pet)
    if p and name in p["does"]:
        s += Q["pursuit"]
    fd = table(cfg, "food", pet)
    if fd and name in fd["does"]:
        s += Q["food"]
    f = table(cfg, "fear", pet)
    if f:
        if name in f.get("does", ()):
            s += Q["fear"]
        if do == "go" and t.get("what") in room["doors"]:
            if feared(house, cfg, pet, room["doors"][t["what"]]):
                s += Q["fear"]
            elif feared(house, cfg, pet, room["id"]):
                s += Q["flee"]   # it is somewhere it is afraid of: any way out
            elif f.get("night") and house["clock"]["phase"] == "night":
                s += Q["fear"] / 2   # afraid of the dark: it stays where it is at night
    g = grounds(house, cfg, pet)
    if g and do == "go" and t.get("what") in room["doors"] and free(house, cfg, pet):
        if room["id"] in g:
            s -= Q["leave"]   # it is where its pursuit is done
        else:
            from .body import way_to
            if way_to(house, pet, g) == t["what"]:
                s += Q["pursuit"]
    home = place(house, pet)
    if home and not g and do == "go" and t.get("what") in room["doors"] and free(house, cfg, pet):
        if room["id"] == home:
            s -= Q["leave"]   # it is where it likes to be
        else:
            from .body import way_to
            if way_to(house, pet, {home}) == t["what"]:
                s += Q["place"]
    return s


def once(house, cfg):
    """(24 November 2026) The living, once: pride back to where a hob starts, for a house that had sneered it away."""
    done = house.setdefault("migrated", {})
    if "sheet_pride" in done:
        return
    for p in house["pets"].values():
        if p.get("stage") not in ("egg", "dead") and "pride" in p.get("needs", {}):
            p["needs"]["pride"] = max(p["needs"]["pride"], cfg["sheet"]["pride"])
    done["sheet_pride"] = house["tick"]


def mend(house, cfg):
    """(24 November 2026) The living, once, with [sheet] mend: a house whose every grown hob had come to hate every
    other (liking -7 to -10 across the board, fifteen grievances) starts again from nothing held against anyone. What
    is liked is kept; what is disliked, the grievances and the lists of who to avoid are let go, and each is set at ease
    and interested once (comfort and curiosity had sunk with the making)."""
    done = house.setdefault("migrated", {})
    if "sheet_mend" in done or not cfg["sheet"].get("mend"):
        return
    living = {p["id"] for p in house["pets"].values() if p.get("stage") not in ("egg", "dead")}
    for p in house["pets"].values():
        if p["id"] not in living:
            continue
        for other, o in (p.get("opinions") or {}).items():
            if other in living and isinstance(o, dict) and o.get("liking", 0) < 0:
                o["liking"] = 0.0
                if isinstance(o.get("fixed"), dict) and o["fixed"].get("liking", 0) < 0:
                    o["fixed"]["liking"] = 0.0
                o["fear"] = 0
        p["avoid"] = [x for x in p.get("avoid") or [] if x not in living]
        for need, least in (("comfort", cfg["sheet"]["ease"]), ("curiosity", cfg["sheet"]["interest"])):   # and they start at ease and interested: misery dulls interest, and boredom wears on ease
            if need in p.get("needs", {}):
                p["needs"][need] = max(p["needs"][need], least)
    house["grievances"] = [g for g in house.get("grievances", []) if not ({g.get("by"), g.get("against")} <= living)]
    done["sheet_mend"] = house["tick"]


def give(house, cfg, pet):
    """A pursuit always; each other slot filled `fill` of the time, at least two of the four in all; a fear never of its own place or pursuit."""
    Q, T, r = cfg["sheet"], cfg["sheets"], rnd(house, "sheet", pet["id"])
    rooms = sorted({x["type"] for x in house["rooms"].values() if x["type"]})
    taken = [p["sheet"] for p in house["pets"].values() if p.get("sheet") and p.get("stage") != "dead" and p["id"] != pet["id"]]
    fresh = lambda slot, all_: [v for v in all_ if v not in {t.get(slot) for t in taken}] or all_   # what no living hob has yet, while there is any: no two alike
    for _ in range(50):
        sh = {"place": r.choice(fresh("place", rooms)) if rooms and r.random() < Q["fill"] else None}
        for slot in SLOTS:
            sh[slot] = r.choice(fresh(slot, sorted(T[slot]))) if slot == "pursuit" or r.random() < Q["fill"] else None   # (every hob has a pursuit: without one its day is anyone's)
        f, p = T["fear"].get(sh["fear"] or "", {}), T["pursuit"].get(sh["pursuit"] or "", {})
        clash = sh["place"] in f.get("rooms", ()) or set(f.get("does", ())) & (set(p.get("does", ())) | set(T["food"].get(sh["food"] or "", {}).get("does", ())))
        if sum(v is not None for v in sh.values()) >= 2 and not clash:
            break
    pet["sheet"] = sh
    return sh


def card(house, cfg, pet):
    """Its sheet for its card on the page: {"text": "its own: fishing; the yard; afraid of heights; loves grown food",
    "now": is it at its pursuit this moment}. None with the sheet off, or for a hob that has none."""
    sh = pet.get("sheet")
    if not on(cfg) or not sh:
        return None
    rid = place(house, pet)
    bits = [sh.get("pursuit"), house["rooms"][rid]["name"] if rid else None, "afraid of %s" % FEARS.get(sh["fear"], sh["fear"]) if sh.get("fear") else None,
            ("loves fish" if sh["food"] == "fish" else "loves %s food" % sh["food"]) if sh.get("food") else None]
    now = (pet.get("body") or {}).get("now") or {}
    return {"text": "its own: " + "; ".join(b for b in bits if b), "now": bool(now) and not pet.get("sleep") and pursues(cfg, pet, now.get("name"))}


def words(house, cfg, pet):
    """ "you spend every free hour in the attic; you fish whenever you can; you are terrified of ..." (or "")."""
    sh, out = pet.get("sheet") or {}, []
    rid = place(house, pet)
    if rid:
        out.append("spend every free hour in %s" % house["rooms"][rid]["name"])
    out += [cfg["sheets"][slot][sh[slot]]["words"] for slot in SLOTS if sh.get(slot) in cfg["sheets"].get(slot, {})]
    return "; ".join("you " + w for w in out)
