"""Building that lasts, and decorating (SPEC-v3.5 §4). A room that lacks something gives a pet the want to build
it; what it takes is carried there and set in place, a hammer knocks it together over several spells of work (two
at it together go faster), and what stands when it is done is a fixture of the house with its builders' names on
it: it changes its room for as long as it is sound, outlasts the family that built it, wears, and can be mended.
With a dye a wall, a patch of floor or a rug is painted in a pattern; the paint fades, and a room is felt as
homely by the family that painted it. Everything is data (building.toml), and no model is asked."""
import tomllib

from . import craft, things
from .world import LONG_AGO, STAGES, add_event, days as world_days, dist, family, free_tile, label, moment, ticks

PROJECT = {}   # building.toml's projects, by name (the same in every config: fixture_says has no config to look in)
COMFORT = ("rest", "cozy", "glow")   # what a worn thing no longer gives until it is mended
WALL_AT, FLOOR_AT = [0, 3, 6, 9], [[2, 4], [7, 4]]   # where a room's wall sections and floor patches are (three tiles wide; a patch two deep)


def load(cfg, directory):
    """building.toml, laid into the config: its activities beside activities.toml's, its dyes and what gives them
    beside crafting.toml's, and what can be planted in beside the house's beds."""
    B = cfg["build"] = tomllib.loads((directory / "building.toml").read_text())
    C, bits = cfg["craft"], cfg["house"]["bits"]
    cfg["activities"].update(B.get("activities", {}))
    bits.update(B.get("bits", {}))
    for name, m in B.get("material", {}).items():
        bits[name] = {"can": list(m["can"]), "looks": bits.get(m.get("like"), {}).get("looks", {"shape": "blob", "color": "grey"}), "late": "crafting", "made": True}
    C["rules"].update({(r["bit"], r["how"]): r for r in B.get("rule", [])})
    C["growing"]["beds"] = list(dict.fromkeys(C["growing"]["beds"] + [n for n, P in B["project"].items() if P.get("fix", {}).get("bed")]))
    for P in B["project"].values():
        P.setdefault("weight", B["build"]["weight"])
    PROJECT.clear()
    PROJECT.update(B["project"])
    return cfg


# ---- what is being built, and what stands ----

def record(o):
    """What an object knows of its building: a thing under way (`site`), a thing that stands (`fix.built`), or None."""
    return o.get("site") or o.get("fix", {}).get("built")


def find(room, key):
    """(name, object) of this project in this room, begun or standing; (None, None) if there is none."""
    return next(((n, o) for n, o in room["objects"].items() if (record(o) or {}).get("project") == key), (None, None))


def sound(o):
    b = o.get("fix", {}).get("built")
    return bool(b) and not b.get("worn")


def standing(room, what):
    """The sound things built here whose project has this key (`proof`, `cold`, `rules`): [(name, its project)]."""
    return [(n, PROJECT[o["fix"]["built"]["project"]]) for n, o in room["objects"].items() if sound(o) and what in PROJECT.get(o["fix"]["built"]["project"], {})]


def missing(P, o):
    """What it still wants set in place: {bit: how many}."""
    placed = (o or {}).get("site", {}).get("placed", {})
    return {b: n - placed.get(b, 0) for b, n in P["needs"].items() if n > placed.get(b, 0)} if o is None or "site" in o else {}


def spot(house, cfg, room, P):
    """The tile it stands on (or hangs above), or None if this room has not what it goes on."""
    objs = room["objects"]
    if P.get("on"):
        return next((list(o["pos"]) for o in objs.values() if P["on"] in o.get("fix", {})), None)
    if P.get("wall"):   # a free stretch of the north wall, as near its place as there is one (never over the door)
        used = [o["pos"][0] for o in objs.values() if o.get("wall")] + [house["door_tiles"]["north"][0]]
        return [min((x for x in range(1, cfg["W"] - 1) if x not in used), key=lambda x: abs(x - P["at"][0]), default=P["at"][0]), 0]
    return free_tile(house, cfg, room, P["at"])


def and_(names):
    return " and ".join(([", ".join(names[:-1])] if len(names) > 1 else []) + names[-1:])


def some(needs):
    from . import wants
    return and_([wants.some(b) if n == 1 else "%s pieces of %s" % (things.COUNT[n], b) for b, n in needs.items()])


def under_way(house):
    return sum(1 for r in house["rooms"].values() if r["type"] for o in r["objects"].values() if "site" in o)


# ---- wants (SPEC-v3.5 §4.1: "wants for projects come from the room") ----

def tamed(house, pet):
    return any(c.get("tame") == pet["id"] for c in house["creatures"])


WHEN = {
    "always": lambda house, cfg, pet, room: True,
    "no_rest": lambda house, cfg, pet, room: not any("rest" in o.get("fix", {}) for o in room["objects"].values()),
    "no_bench": lambda house, cfg, pet, room: not any(o.get("fix", {}).get("bench") for o in room["objects"].values()),
    "crowded": lambda house, cfg, pet, room: room.get("mess") == 2,
    "sleeps": lambda house, cfg, pet, room: pet.get("sleeps_in") == room["id"] and not any("rest" in o.get("fix", {}) and o["fix"].get("cozy") for o in room["objects"].values()),
    "leaks": lambda house, cfg, pet, room: world_days(cfg, room.get("leaked", LONG_AGO), house["tick"]) < cfg["build"]["build"]["recent_days"],
    "draughty": lambda house, cfg, pet, room: world_days(cfg, room.get("draught", LONG_AGO), house["tick"]) < cfg["build"]["build"]["recent_days"],
    "cold": lambda house, cfg, pet, room: (things.room_rule(cfg, room, "cold_night", 0.0) or 0.0) < 0 or cfg["house"]["seasons"][house["clock"]["season"]]["cold"] < 0,
    "tame": lambda house, cfg, pet, room: tamed(house, pet) and room["id"] == (pet.get("sleeps_in") or pet["room"]),
}


def old_enough(pet, stage="child"):
    return pet["stage"] in STAGES and STAGES.index(pet["stage"]) >= STAGES.index(stage)


def hammer_words(house, cfg, pet):
    """What a want to build says of the hammer there is not."""
    from . import wants
    if "hammer" not in pet.get("takes", []):
        book = wants.book_room(house)
        return "; it wants knocking together and nobody has a hammer" + ("; the heavy book in %s might know what one is made of" % house["rooms"][book]["name"] if book and not wants.asked_of(pet, "hammer") else "")
    if not craft.lacking(cfg, "hammer", pet["carrying"]):
        return "; you carry what a hammer takes: you could make one now"
    return "; nobody has a hammer: one takes %s" % craft.takes(cfg, "hammer")


def candidates(house, cfg, pet, add, known):
    """What it could want to build, mend or paint just now (one line in wants.candidates). A thing already begun
    comes a good deal more strongly than one not begun, so the house works on a thing together; and past a few
    things under way no new one is begun."""
    S, tick = cfg["build"]["build"], house["tick"]
    if not old_enough(pet):
        return
    hammer, begun = craft.tool_for(house, cfg, pet, "hammer"), under_way(house)
    for r in known:
        for key, P in cfg["build"]["project"].items():
            if P["rooms"] != "any" and r["type"] not in P["rooms"]:
                continue
            name, o = find(r, key)
            k, lack = "%s|%s" % (r["id"], key), missing(P, o)
            if o is None:
                if begun >= S["most"] or not WHEN[P["when"]](house, cfg, pet, r) or spot(house, cfg, r, P) is None:
                    continue
                text, done, weight = P["want"].format(room=r["name"]) + "; it takes %s, and a hammer" % some(P["needs"]), P["done"].format(room=r["name"]), P["weight"]
            elif "site" in o:
                text = "the %s being built in %s wants %s" % (key, r["name"], "%s yet" % some(lack) if lack else "more work with the hammer")
                done, weight = P["done"].format(room=r["name"]), S["started"]
                pet.get("wanted", {}).pop("build:" + k, None)   # (a thing under way may be wanted again as soon as it was let go)
            elif o["fix"]["built"].get("worn"):
                text, done, weight = "the %s in %s has worn: you want to mend it" % (key, r["name"]), "mended the %s in %s" % (key, r["name"]), 2.0
            else:
                continue
            add("build", k, text + ("" if hammer or lack else hammer_words(house, cfg, pet)), done, weight * (1.3 if r["id"] == pet["room"] else 1.0), room=r["id"], project=key)
    w = next((w for w in pet.get("wants", []) if w["what"] == "build"), None)
    if w and chain(house, cfg, pet, w):
        pet.setdefault("lacks", {})["hammer"] = tick   # (so its mind is offered the making of one: mind.py)
    paint_want(house, cfg, pet, add, known)


def chain(house, cfg, pet, w):
    """Is it the hammer this want waits on: there is none it can get to, and nothing more it could be carrying over?"""
    room = house["rooms"][w["room"]]
    name, o = find(room, w["project"])
    lack = missing(cfg["build"]["project"][w["project"]], o)
    return not craft.tool_for(house, cfg, pet, "hammer") and (not lack or fetch(house, cfg, pet, w, lack) is None)


def met(house, cfg, pet, w):
    if w["what"] == "paint":
        return any(p["by"] == pet["id"] and p["tick"] >= w["since"] for p in house["rooms"][w["room"]].get("painted", []))
    name, o = find(house["rooms"][w["room"]], w["project"])
    b = (o or {}).get("fix", {}).get("built")
    return bool(b) and not b.get("worn") and pet["id"] in b["paws"] and max(b["at"], b.get("mended", 0)) >= w["since"]


def possible(house, cfg, pet, w):
    """Can it still be had? Not a thing not begun once enough is under way, or once the room no longer lacks it;
    not a thing someone else finished without it."""
    if w["what"] == "paint":
        return True
    room, P = house["rooms"][w["room"]], cfg["build"]["project"][w["project"]]
    name, o = find(room, w["project"])
    if o is None:
        return under_way(house) < cfg["build"]["build"]["most"] and WHEN[P["when"]](house, cfg, pet, room)
    return "site" in o or bool(o["fix"]["built"].get("worn"))


def lying(house, pet, bit):
    """The room it knows where this bit lies ready, this one first; or None."""
    rooms = [pet["room"]] + [r for r in pet["rooms"] if r != pet["room"] and house["rooms"][r]["type"]]
    return next((rid for rid in rooms if any(s["bit"] == bit and s["ready"] and not s.get("on") for s in house["rooms"][rid]["spots"])), None)


def fetch(house, cfg, pet, w, lack):
    """The next thing to do about what a thing being built still wants: ("gather", the bits of it lying here),
    ("place",) with some of it in its paws, ("go", the room where some lies), or None when there is none to be had
    just now (it has all been picked and has not grown back, or it has to be made of something first)."""
    carry, full = pet["carrying"], len(pet["carrying"]) >= cfg["make"]["carry"]
    mine = [b for b in carry if b in lack]
    short = [b for b, n in lack.items() if n > carry.count(b)]
    here_ = {b for b in short if lying(house, pet, b) == pet["room"]}
    if here_ and not (full and mine):   # (with its arms full of other things it puts one down first: body.py's swap)
        return "gather", here_
    if mine:
        return ("place",)
    there = next((lying(house, pet, b) for b in short if lying(house, pet, b)), None)
    return ("go", there) if there else None


def lean(house, cfg, pet, w, out):
    """What its body leans toward for the sake of a want to build or paint (one line in wants.lean): the bits it
    takes, the room it is in, the book while nobody knows what a hammer is made of."""
    from . import wants
    here_, room = pet["room"], house["rooms"][w["room"]]
    if w["what"] == "paint":
        if dye_of(cfg, pet) and room["id"] != here_:
            out["rooms"].add(room["id"])
        return
    name, o = find(room, w["project"])
    lack = missing(cfg["build"]["project"][w["project"]], o)
    step = fetch(house, cfg, pet, w, lack) if lack else None
    if step and step[0] == "gather":
        out["gather"] |= step[1]
    elif step:
        out["rooms"].add(room["id"] if step[0] == "place" else step[1])
    elif craft.tool_for(house, cfg, pet, "hammer"):
        out["rooms"].add(room["id"])   # all it takes is there, or it has worn: to work
    elif "hammer" not in pet.get("takes", []):   # nobody has a hammer, and it does not know what one is made of: to the book
        if not wants.asked_of(pet, "hammer") and wants.book_room(house) in pet["rooms"]:
            out["rooms"].add(wants.book_room(house))
    else:   # it knows: whatever of a hammer's makings lies about is picked up as it comes to it (what has to be made first is a step: named)
        for alts in parts(cfg, pet):
            there = next((lying(house, pet, b) for b in alts if lying(house, pet, b)), None)
            if there == here_:
                out["gather"].add(next(b for b in alts if lying(house, pet, b) == here_))
            elif there:
                out["rooms"].add(there)


def parts(cfg, pet):
    """What a hammer takes that it does not carry: [the bits any one of which would do]."""
    return [g.split("|") for g in cfg["craft"]["needs"]["hammer"] if not any(x in pet["carrying"] for x in g.split("|"))]


def named(house, cfg, pet):
    """What its wants to build or paint name that it has not got and that has to be made of something first (one
    line in wants.candidates: each becomes a step, as a tool's makings do): a material that comes of a process; the
    makings of a hammer, once it knows them and the hammer is all that is wanting; a dye. [(the bit, the want)]"""
    C, carry, out = cfg["craft"], pet["carrying"], []
    for w in pet.get("wants", []):
        if w["what"] == "paint" and not dye_of(cfg, pet) and not any(x["what"] == "build" for x in pet["wants"]):   # (a thing being built comes first: one step at a time)
            out += [(d, w["key"]) for d in cfg["build"]["paint"]["dyes"]]
        elif w["what"] == "build":
            name, o = find(house["rooms"][w["room"]], w["project"])
            out += [(b, w["key"]) for b in missing(cfg["build"]["project"][w["project"]], o) if cfg["house"]["bits"][b].get("made")]
            if "hammer" in pet.get("takes", []) and chain(house, cfg, pet, w):   # (what lies about it simply picks up: lean)
                out += [(b, w["key"]) for alts in parts(cfg, pet) if not any(lying(house, pet, b) for b in alts) for b in alts]
    return [(bit, key) for bit, key in out if bit not in carry]


def question(house, cfg, pet, w):
    """What a want to build asks the book (one line in wants.question): how a hammer is made, once that is what it
    waits on. Never twice."""
    from . import wants
    q = "how do you " + cfg["craft"]["tool"]["hammer"]["want"]
    return q if w["what"] == "build" and chain(house, cfg, pet, w) and not wants.asked_of(pet, "hammer") and q not in pet.get("asked", []) else None


def keep(house, cfg, pet):
    """The bits in its paws that a want to build is about: not what it puts down to pick something else up."""
    out = set()
    for w in pet.get("wants", []):
        if w["what"] == "build":
            name, o = find(house["rooms"][w["room"]], w["project"])
            out |= set(missing(cfg["build"]["project"][w["project"]], o))
            if chain(house, cfg, pet, w):
                out |= {alt for g in cfg["craft"]["needs"]["hammer"] for alt in g.split("|")}
        elif w["what"] == "paint":
            out |= set(cfg["build"]["paint"]["dyes"])
    return out


# ---- what a body does at it (one line each in body.targets and body.finish) ----

def at_it(house, cfg, room, name, pet):
    """Who else is at work on this just now: hammering at it, or was a moment ago."""
    since, last = house["tick"] - ticks(cfg, cfg["build"]["build"]["near_seconds"]), room["objects"][name]["site"]["last"]
    out = []
    for p in house["pets"].values():
        now = (p.get("body") or {}).get("now") or {}
        if p is not pet and p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"] \
                and ((now.get("name") == "build" and now.get("what") == name) or last.get(p["id"], LONG_AGO) >= since):
            out.append(p)
    return out


def targets(house, cfg, pet, A, near):
    """Everything this activity could be done with right now, as body.targets gives it."""
    mode, room, tick = A["mode"], house["rooms"][pet["room"]], house["tick"]
    B, S, W, objs = cfg["build"], cfg["build"]["build"], cfg["body"]["want"], house["rooms"][pet["room"]]["objects"]
    mine = {w["key"][6:]: w for w in pet.get("wants", []) if w["what"] == "build" and w["room"] == room["id"]}
    hammer = craft.tool_for(house, cfg, pet, "hammer")
    if mode == "place":   # something it carries that a thing it wants to build here still wants: over to it (the first of it marks the place)
        for k, w in mine.items():
            P = B["project"][w["project"]]
            name, o = find(room, w["project"])
            bit = next((b for b in pet["carrying"] if b in missing(P, o)), None)
            at = o["pos"] if o else spot(house, cfg, room, P)
            if bit and at:
                from . import wants
                return [{"what": name or w["project"], "where": wants.some(bit), "job": ["place", w["project"], bit], "goal": near(at), "bonus": W * 1.5, "want": w["key"]}]
        return []
    if mode == "work":   # a thing here with all it takes in place, a hammer to be had, and its paws rested: a spell of work (anyone may lend a paw)
        if not hammer or pet["needs"]["energy"] < cfg["make"]["tired"]:
            return []
        out = []
        for n, o in objs.items():
            s = o.get("site")
            if s and not missing(B["project"][s["project"]], o) and tick - s["last"].get(pet["id"], LONG_AGO) >= ticks(cfg, S["rest_seconds"]):
                out.append({"what": n, "goal": near(o["pos"]), "bonus": (W * 1.5 if "%s|%s" % (room["id"], s["project"]) in mine else 0.0) + (2.0 if at_it(house, cfg, room, n, pet) else 0.0)})
        return out[:2]
    if mode == "mend":   # a built thing that has worn, and a hammer; or the hammer itself, worn, if its paws are up to mending it
        worn = [n for n, o in objs.items() if o.get("fix", {}).get("built", {}).get("worn")] if hammer else []
        out = [{"what": n, "goal": near(objs[n]["pos"]), "bonus": W if "%s|%s" % (room["id"], objs[n]["fix"]["built"]["project"]) in mine else 0.0} for n in worn[:1]]
        blunt = next((n for n, o in things.made(room).items() if o["made"]["recipe"].get("kind") == "hammer" and o["made"].get("wear", 0) >= craft.lasts(cfg, o)), None)
        if blunt and not hammer and any(w["what"] == "build" for w in pet.get("wants", [])) and craft.check_mend({"target": blunt}, house, cfg, pet, lambda s: s) is None:
            out.append({"what": blunt, "goal": near(objs[blunt]["pos"]), "job": ["tool"], "bonus": W})
        return out
    if mode == "hammer":   # it carries what a hammer takes, wants one to build with, and its mind has had its chance: its paws bind one
        b = pet["body"]
        ready = not hammer and not craft.lacking(cfg, "hammer", pet["carrying"]) and any(w["what"] == "build" for w in pet.get("wants", []))
        b["hammer_at"] = b.get("hammer_at") or tick if ready else None
        if ready and b.get("hammer_told") != b["hammer_at"]:   # its mind is told, once, and thinks sooner (as with a bit carried to where it can be tried)
            b["hammer_told"], pet["ready"] = b["hammer_at"], tick
            add_event(house, pet, "you carry all a hammer takes: you could make one now")
        return [{"bonus": W * 1.5}] if ready and tick - b["hammer_at"] >= ticks(cfg, cfg["body"]["try_after_seconds"]) and check_hammer(house, cfg, pet) is None else []
    if mode == "paint":   # a dye in its paws and somewhere here its family has not painted: it paints, as its coat is patterned
        from . import life
        dye, place = dye_of(cfg, pet), free_place(house, cfg, pet, room)
        if not dye or not place or "paint" not in life.unlocked(house, pet["stage"]):
            return []
        wanted = any(w["what"] == "paint" and w["room"] == room["id"] for w in pet.get("wants", []))
        return [{"what": place[0] if place[0] != "rug" else place[1], "job": ["paint", place[0], place[1]], "goal": near(place_tile(room, place)), "bonus": W if wanted else 0.0}]
    return []


def hammer_recipe(cfg, pet):
    can = {p for b in pet["carrying"] for p in cfg["house"]["bits"][b]["can"]} - set(cfg["kinds"]["hammer"].get("not", []))
    return {"type": "make", "near": "here", "recipe": {"name": "hammer", "kind": "hammer", "material": next((m for m in ("heavy", "hard") if m in can), next(iter(sorted(can)), None)),
                                                        "color": "brown", "size": "medium", "purpose": "to knock things together"}}


def check_hammer(house, cfg, pet):
    from . import actions
    return actions.check(hammer_recipe(cfg, pet), house, cfg, pet, None)


def finish(mind, now, A):
    """The activity is over: what it really did is done. Returns (what it is told it did, or None for the
    activity's own words; whether anything was done)."""
    from . import actions
    pet, house, cfg = mind.pet, mind.eng.house, mind.cfg
    mode, room, tick, S = A["mode"], house["rooms"][pet["room"]], house["tick"], cfg["build"]["build"]
    name = actions.norm(now.get("what")) if now.get("what") else None
    o = room["objects"].get(name)
    if mode == "place":
        _, key, bit = now["job"]
        P = cfg["build"]["project"][key]
        name, o = find(room, key)
        if bit not in pet["carrying"] or not missing(P, o).get(bit) or (o is None and (under_way(house) >= S["most"] or spot(house, cfg, room, P) is None)):
            return None, False
        if o is None:
            name, o = begin(house, cfg, pet, room, key)
        s = o["site"]
        pet["carrying"].remove(bit)
        s["placed"][bit] = s["placed"].get(bit, 0) + 1
        s["paws"].setdefault(pet["id"], 0)
        worked(house, pet, room, key)
        if not missing(P, o):
            add_event(house, pet, "everything the %s takes is in place: it wants knocking together with a hammer now" % name)
        return "set %s in place at the %s" % (now["where"], name), True
    if mode == "work":
        s = (o or {}).get("site")
        if not s or missing(cfg["build"]["project"][s["project"]], o) or not craft.tool_for(house, cfg, pet, "hammer"):
            return None, False
        P, others = cfg["build"]["project"][s["project"]], at_it(house, cfg, room, name, pet)
        tool, frm = craft.fetch(house, cfg, pet, "hammer")
        craft.wear(house, cfg, pet, room, tool)
        s["work"] = round(s["work"] + (S["together"] if others else 1.0), 2)
        s["last"][pet["id"]], s["paws"][pet["id"]] = tick, s["paws"].get(pet["id"], 0) + 1
        actions.bump(pet, cfg, {"energy": -S["effort"], **({"company": S["company"]} if others else {})})
        craft.practise(house, cfg, pet, "making", 0.5)
        worked(house, pet, room, s["project"])
        for p in others:   # (working side by side is being with someone: SPEC-v3.4 §1)
            actions.bump(p, cfg, {"company": S["company"]})
        told = "worked on the %s with the hammer%s%s" % (name, ", side by side with %s: it goes faster with two" % and_([actions.handle(house, pet, p) for p in others]) if others else "",
                                                        "; you fetched the %s from %s" % (tool, frm) if frm else "")
        if s["work"] >= P["sessions"]:
            stand(house, cfg, pet, room, name)
            told += "; it is finished: the %s stands in %s" % (name, room["name"])
        return told, True
    if mode == "mend" and now.get("job") == ["tool"]:
        a = {"type": "mend", "target": name}
        if not o or actions.check(a, house, cfg, pet, mind.mem) is not None:
            return None, False
        return actions.apply(house, cfg, pet, a, mind.mem)[0].replace("you ", "", 1), True
    if mode == "mend":
        b = (o or {}).get("fix", {}).get("built")
        if not b or not b.get("worn") or not craft.tool_for(house, cfg, pet, "hammer"):
            return None, False
        tool, _ = craft.fetch(house, cfg, pet, "hammer")
        craft.wear(house, cfg, pet, room, tool)
        mend(house, cfg, pet, room, name)
        return None, True
    if mode == "hammer":
        a = hammer_recipe(cfg, pet)
        if craft.tool_for(house, cfg, pet, "hammer") or actions.check(a, house, cfg, pet, mind.mem) is not None:
            return None, False
        text, fx, _ = actions.apply(house, cfg, pet, a, mind.mem)
        actions.bump(pet, cfg, {n: v for n, v in fx.items() if n in pet["needs"]})
        pet["body"]["hammer_at"] = None
        return text.replace("you ", "", 1), True
    if mode == "paint":
        _, where, at = now["job"]
        dye = dye_of(cfg, pet)
        if not dye or (where == "rug" and at not in room["objects"]):
            return None, False
        return paint(house, cfg, pet, room, dye, where, at, echo(cfg, pet)).replace("you ", "", 1), True
    return None, False


def worked(house, pet, room, key):
    """It has had a paw in this: its want to build it is not one left alone."""
    for w in pet.get("wants", []):
        if w["key"] == "build:%s|%s" % (room["id"], key):
            w["touched"] = house["tick"]


def begin(house, cfg, pet, room, key):
    """The first of what it takes is set down: the place is marked, and the thing is under way."""
    P = cfg["build"]["project"][key]
    elsewhere = any(find(r, key)[1] for r in house["rooms"].values() if r["type"] and r is not room)   # the house's first is "bench"; another is "storeroom bench"
    name = things.unique_name(house, cfg, "%s %s" % (room["type"], key) if elsewhere else key)
    o = room["objects"][name] = {"pos": spot(house, cfg, room, P), "fix": {"site": key}, "state": "being built",
                                 "site": {"project": key, "by": pet["id"], "at": house["tick"], "placed": {}, "work": 0.0, "paws": {}, "last": {}}}
    if P.get("wall"):
        o["wall"] = True
    moment(house, "project", "%s began %s %s in %s" % (label(pet), P["a"], key, room["name"]), pet["id"], room["id"])
    for p in house["pets"].values():
        if p is not pet and p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
            from .actions import handle
            add_event(house, p, "%s has begun building %s %s here" % (handle(house, p, pet), P["a"], key))
    return name, o


def stand(house, cfg, pet, room, name):
    """The last spell of work is done: it stands, a fixture of the house with its builders' names on it, and its
    room is changed by it."""
    from . import actions
    o, tick = room["objects"][name], house["tick"]
    s = o.pop("site")
    key, P = s["project"], cfg["build"]["project"][s["project"]]
    paws = sorted(s["paws"], key=lambda p: (-s["paws"][p], p != pet["id"]))   # whoever did most of it first
    names = [label(house["pets"][p]) for p in paws if p in house["pets"]]
    o["fix"] = dict(P.get("fix", {}), built={"project": key, "by": paws[0], "names": names, "paws": paws, "at": tick, "began": s["at"]})
    o.pop("state", None)
    for bit, n in P.get("bits", {}).items():   # what the room grows as well, now
        for i in range(n):
            at = P["spots"][i] if i < len(P.get("spots", [])) else free_tile(house, cfg, room, o["pos"])
            room["spots"].append({"bit": bit, "pos": list(at), "ready": True, "back": None, "loose": False, "built": name})
    settle(room)
    text = "%s %s" % (and_(names), P["done"].format(room=room["name"]))
    craft.found(house, pet, text, "built")
    for pid in paws:
        p = house["pets"].get(pid)
        if p and p["stage"] not in ("egg", "dead"):
            if p is not pet:
                add_event(house, p, "the %s you had a paw in building stands finished in %s" % (name, room["name"]))
            if not any(w["key"] == "build:%s|%s" % (room["id"], key) for w in p.get("wants", [])):   # (whoever wanted it feels it as a want met)
                actions.bump(p, cfg, dict(cfg["build"]["build"]["lift"]))


def settle(room):
    """The room's own rule as the sound things built in it leave it (things.room_rule reads this)."""
    room["rules"] = {k: v for _, P in standing(room, "rules") for k, v in P["rules"].items()}


def wear_out(house, cfg, room, name):
    o = room["objects"][name]
    b = o["fix"]["built"]
    b["worn"], o["state"] = True, "worn"
    b["off"] = {k: o["fix"].pop(k) for k in COMFORT if k in o["fix"]}   # (it still stands, and keeps what is on it; it is no comfort until it is mended)
    settle(room)
    moment(house, "worn", "the %s %s built in %s has worn" % (b["project"], and_(b["names"]), room["name"]), None, room["id"])


def mend(house, cfg, pet, room, name):
    o = room["objects"][name]
    b = o["fix"]["built"]
    b.pop("worn", None)
    o["fix"].update(b.pop("off", {}))
    o.pop("state", None)
    b["mended"], b["paws"] = house["tick"], list(dict.fromkeys(b["paws"] + [pet["id"]]))
    settle(room)
    craft.practise(house, cfg, pet, "mending")
    moment(house, "mended", "%s mended the %s %s built in %s" % (label(pet), b["project"], and_(b["names"]), room["name"]), pet["id"], room["id"])


def hourly(house, cfg):
    """Once a world hour (one line in director.hourly): a room that is wet or in a draught is remembered as one that
    leaks or takes one; what was built wears; paint that has faded away is gone; a tamed creature with a hutch in
    the house does not go wild."""
    S, tick = cfg["build"]["build"], house["tick"]
    hutch = False
    for room in [r for r in house["rooms"].values() if r["type"]]:
        if room["wet_until"] > tick:
            room["leaked"] = tick
        if room["cold_until"] > tick:
            room["draught"] = tick
        for n, o in list(room["objects"].items()):
            b = o.get("fix", {}).get("built")
            if b and not b.get("worn") and world_days(cfg, max(b["at"], b.get("mended", 0)), tick) >= S["wear_days"]:
                wear_out(house, cfg, room, n)
            hutch = hutch or (sound(o) and bool(o["fix"].get("hutch")))
        if room.get("painted"):
            room["painted"] = [p for p in room["painted"] if strength(house, cfg, p) > 0]
    for cr in house["creatures"] if hutch else ():
        if cr.get("tame") and cr["tame"] in cr.get("trust", {}):
            cr["trust"][cr["tame"]] = max(cr["trust"][cr["tame"]], cfg["taming"]["tame_at"] * 0.75)


def proof(house, cfg, room, what):
    """Does something built here, and sound, keep this out (one line each where director makes a leak and a
    draught)? Whoever is in the room is told what it was spared."""
    kept = standing(room, "proof")
    name = next((n for n, P in kept if P["proof"] == what), None)
    if name:
        for p in house["pets"].values():
            if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                add_event(house, p, ("water drips somewhere overhead, and the %s keeps it out: the floor stays dry" if what == "leak" else "a draught rattles the door, and the %s keeps it out") % name)
        moment(house, "held", "the %s in %s kept %s out" % (name, room["name"], "the water" if what == "leak" else "a draught"), None, room["id"])
    return bool(name)


def felt(house, cfg, pet, room, out, cold):
    """One line in physics.effects: a painted room is felt (homely by the family that painted it, a little strange
    by another), and a room lined against the cold lets less of it in. Returns the cold as the lining leaves it."""
    P = cfg["build"]["paint"]
    fresh = [p for p in room.get("painted", []) if strength(house, cfg, p) >= P["felt_above"]]
    if any(p["family"] == family(pet) for p in fresh):
        out.append({"tag": "painted", "need": "comfort", "rate": P["homely"], "feel": "the patterns painted here are your family's: the room feels like home", "hidden": False})
    elif fresh:
        out.append({"tag": "painted", "need": "comfort", "rate": P["strange"], "feel": "the patterns painted here are another family's: the room feels a little strange", "hidden": False})
    lined = standing(room, "cold")
    if lined and cold:
        out.append({"tag": "lined", "need": "comfort", "rate": 0.0, "feel": "the %s keeps most of the cold out" % lined[0][0], "hidden": False})
    return cold * min((P_["cold"] for _, P_ in lined), default=1.0)


def says(fix):
    """What a thing being built or built is, in a few words (one line in actions.fixture_says)."""
    from . import actions
    s, b = fix.get("site"), fix.get("built")
    if s:
        return "%s %s being built: it wants what it takes set in place, and knocking together with a hammer" % (PROJECT[s]["a"], s)
    P = PROJECT.get(b["project"], {})
    return "%s; %s built it%s" % (P.get("says") or actions.fixture_says({k: v for k, v in fix.items() if k != "built"}), and_(b["names"]), "; it has worn and wants mending with a hammer" if b.get("worn") else "")


def view(house, cfg, room, name, o, v):
    """How a thing being built or built is drawn and named, for the page (one line in server.room_view)."""
    s, b = o.get("site"), o.get("fix", {}).get("built")
    if not s and not b:
        return
    key = (s or b)["project"]
    P = cfg["build"]["project"].get(key, {})
    if s:
        lack, part = missing(P, o), s["work"] / P["sessions"]
        v["build"] = {"sprite": "fix.site%s%s" % (".wall" if P.get("wall") else "", ".half" if part >= 0.4 else ""), "title": "%s %s being built" % (P["a"], key),
                      "progress": round(part, 2), "placed": s["placed"], "needs": P["needs"]}
        by = house["pets"].get(s["by"])
        v["says"] = "%s began it; %s" % (label(by) if by else "someone", "it wants %s yet" % some(lack) if lack else
                                         "it is %s: it wants more work with the hammer" % ("more than half built" if part >= 0.5 else "begun" if part else "ready to be knocked together"))
    else:
        v["build"] = {"sprite": "fix.built." + key, "title": "the %s %s built" % (key, and_(b["names"])), "flat": bool(P.get("flat")), "glow": bool(o["fix"].get("glow")),
                      "worn": bool(b.get("worn")), "at": b["at"]}
        v["says"] = says(o["fix"])


# ---- decorating (§4.2) ----

def dye_of(cfg, pet):
    """The dye it carries, if any."""
    return next((b for b in pet["carrying"] if b in cfg["build"]["paint"]["dyes"]), None)


def strength(house, cfg, p):
    """How fresh a painted place is: 1 new, 0 faded away."""
    return max(0.0, 1.0 - world_days(cfg, p["tick"], house["tick"]) / cfg["build"]["paint"]["fade_days"])


def echo(cfg, pet):
    """The pattern it paints by itself: its coat's (§2.1)."""
    P = cfg["build"]["paint"]
    return P["echo"].get(pet["genome"].get("pattern"), P["echo"]["plain"])


def rugs(cfg, room):
    return [n for n, o in room["objects"].items() if not o.get("on") and not o.get("wall") and (o.get("made", {}).get("recipe", {}).get("kind") == "rug" or ("fix" in o and n.endswith("rug")))]


def places(cfg, room):
    """Everywhere in a room that can be painted: [(where, at)]: sections of the north wall, patches of floor, each rug."""
    P = cfg["build"]["paint"]
    return [("wall", [x, 0]) for x in WALL_AT[:P["wall"]]] + [("floor", list(t)) for t in FLOOR_AT[:P["floor"]]] + [("rug", n) for n in rugs(cfg, room)]


def place_tile(room, place):
    return room["objects"][place[1]]["pos"] if place[0] == "rug" else [place[1][0] + 1, place[1][1]]


def patch(room, where, at):
    return next((p for p in room.get("painted", []) if p["where"] == where and p["at"] == at), None)


def free_place(house, cfg, pet, room, where=None):
    """Where it would paint here by itself: the nearest place with no paint on it, or paint faded by half; none once
    its family has painted its share of the room. `where`: only a place of this sort, and then any will do (its
    mind chose: it may paint over what is there)."""
    P = cfg["build"]["paint"]
    stale = lambda pl: not patch(room, *pl) or strength(house, cfg, patch(room, *pl)) < 0.5
    if not where and sum(1 for p in room.get("painted", []) if p["family"] == family(pet) and strength(house, cfg, p) >= 0.5) >= P["family"]:
        return None
    options = [pl for pl in places(cfg, room) if (pl[0] == where or pl == ("rug", where) if where else stale(pl))]
    return min(options, key=lambda pl: (not stale(pl), dist(pet["pos"], place_tile(room, pl))), default=None)


def can_paint(house, cfg, pet):
    return bool(dye_of(cfg, pet))


def check_paint(a, house, cfg, pet, norm):
    room, P = house["rooms"][pet["room"]], cfg["build"]["paint"]
    if not dye_of(cfg, pet):
        return "you have no colour to paint with: it takes a dye"
    if a.get("pattern") not in P["patterns"] + ["like your coat"]:
        return "there is no such pattern"
    return None if free_place(house, cfg, pet, room, norm(a.get("where")) or "wall") else "there is no such place here to paint"


def do_paint(house, cfg, pet, a, norm):
    """`paint`, as its mind decides it: a wall, the floor or a rug, in a pattern it chose or its coat's."""
    room = house["rooms"][pet["room"]]
    where, at = free_place(house, cfg, pet, room, norm(a.get("where")) or "wall")
    text = paint(house, cfg, pet, room, dye_of(cfg, pet), where, at, echo(cfg, pet) if a["pattern"] == "like your coat" else a["pattern"])
    return text, dict(cfg["effects"]["paint"]), "paint"


def paint(house, cfg, pet, room, dye, where, at, pattern):
    """The dye goes on: one place, in one pattern, in the dye's colour with the painter's own coat colour through
    it. What was painted there before is painted over."""
    P = cfg["build"]["paint"]
    pet["carrying"].remove(dye)
    room["painted"] = [p for p in room.get("painted", []) if not (p["where"] == where and p["at"] == at)] + [
        {"where": where, "at": at, "color": P["dyes"][dye], "hue": pet["genome"].get("hue", 0), "pattern": pattern, "by": pet["id"], "name": label(pet), "family": family(pet), "tick": house["tick"]}]
    what = "the %s" % at if where == "rug" else "a stretch of the wall" if where == "wall" else "a patch of the floor"
    moment(house, "painted", "%s painted %s of %s in %s %s" % (label(pet), what, room["name"], P["dyes"][dye], pattern), pet["id"], room["id"])
    return "you painted %s in %s %s with the %s" % (what, P["dyes"][dye], pattern, dye)


def paint_want(house, cfg, pet, add, known):
    """To make a room look like its family's: the room it sleeps in, while none of its family's paint is fresh there."""
    from . import life
    P = cfg["build"]["paint"]
    room = next((r for r in known if r["id"] == (pet.get("sleeps_in") or pet["room"])), None)
    if not room or "paint" not in life.unlocked(house, pet["stage"]) or not free_place(house, cfg, pet, room) \
            or any(p["family"] == family(pet) and strength(house, cfg, p) >= 0.5 for p in room.get("painted", [])):
        return
    dye = dye_of(cfg, pet)
    add("paint", room["id"], "you want %s to look like your family's, with colour on its walls%s" % (room["name"], "; you carry %s: you could paint here" % dye if dye else ": it takes a dye"),
        "painted %s in its family's colours" % room["name"], P["weight"], room=room["id"])


def painted(house, cfg, room):
    """What is painted in a room, for the page: each place, its colours and pattern, and how fresh it is."""
    return [dict(p, strength=round(strength(house, cfg, p), 2)) for p in room.get("painted", [])]
