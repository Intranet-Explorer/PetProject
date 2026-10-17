"""The pond (SPEC-v3.6a): water across most of the pond room, fish in it, and what comes up on a line.

A house lived in before has its old small pond spread once, on load ("after the spring rains, the pond spread"):
what stood where the water now lies moves to the edge, and nothing is lost (`spread`). Hobs walk round the water,
over the dock and the bridge, and on the ice in the coldest weeks (`step`). Fishing is a body activity (activities.toml
`fish`, body.py): no model is asked; the catch is rolled as the hob sets out (`targets`) and landed when it is done
(`landed`). Numbers in pond.toml."""
import re
import tomllib
from collections import deque

from . import craft, feats, feel, things
from .world import add_event, dist, family, free_tile, label, moment, rnd

REFUSE = re.compile(r"\b(not|never|no|don't|dont|mustn't|shouldn't|wrong|cruel|leave|spare|let)\b")


def load(cfg, directory):
    """pond.toml, laid into the config; the pond's creatures beside the house's."""
    cfg["pond"] = tomllib.loads((directory / "pond.toml").read_text())
    for kind, c in cfg["pond"].get("creatures", {}).items():
        cfg["house"]["creatures"].setdefault(kind, dict(c, likes=[]))
    return cfg


def P(cfg):
    return cfg["pond"]


def room_of(house, cfg):
    return next((r for r in house["rooms"].values() if r["type"] == P(cfg)["pond"]["room"]), None)


def state(house):
    return house.setdefault("pond", {"stock": None, "today": [0, 0], "catches": [], "frozen": False, "holes": [], "dock": None, "spread": None, "thin": False})


def water(room):
    return [t for o in room["objects"].values() for t in o.get("fix", {}).get("water", [])]


def frozen(house, cfg):
    """The coldest weeks: the middle of winter (pond.toml [winter] frozen, a share of the season)."""
    if house["clock"]["season"] != "winter":
        return False
    span = cfg["house"]["house"]["season_days"]
    k = ((house["clock"]["day"] - 1 + cfg.get("season_off", 0)) % span) / span
    lo, hi = P(cfg)["winter"]["frozen"]
    return lo <= k < hi


def dry_over(house, cfg, room):
    """Water tiles a hob may stand on: the dock, the bridge (once the hobs have built it), the ice (not its holes)."""
    S = state(house)
    out = {tuple(t) for t in (S["dock"] or {}).get("tiles", [])}
    if any(n == "pond bridge" or n.endswith(" bridge") for n, o in room["objects"].items() if "fix" in o):
        out |= {tuple(t) for t in P(cfg)["pond"]["bridge"]}
    if S["frozen"]:
        out |= {tuple(t) for t in water(room)} - {tuple(t) for t in S["holes"]}
    return out


def wet(house, cfg, room):
    """The tiles a hob cannot walk on here: open water."""
    w = water(room)
    return {tuple(t) for t in w} - dry_over(house, cfg, room) if w else set()


def step(house, cfg, room, pos, goal):
    """The next tile toward `goal`: straight, unless that is open water; then round it (the shortest way over dry
    tiles, 8 ways). Straight on if there is no way round."""
    straight = [p + (g > p) - (g < p) for p, g in zip(pos, goal)]
    w = wet(house, cfg, room)
    if not w or tuple(straight) not in w:
        return straight
    start, end = tuple(pos), tuple(goal)
    if end in w and max(abs(start[0] - end[0]), abs(start[1] - end[1])) <= 1:
        return list(pos)   # (beside what is out on the water: as near as it gets)
    seen, todo = {start: None}, deque([start])
    while todo:
        at = todo.popleft()
        if at == end or (end in w and max(abs(at[0] - end[0]), abs(at[1] - end[1])) <= 1):
            while seen[at] != start and seen[at] is not None:
                at = seen[at]
            return list(at) if at != start else list(pos)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (at[0] + dx, at[1] + dy)
                if n not in seen and 0 <= n[0] < cfg["W"] and 0 <= n[1] < cfg["H"] and n not in w:
                    seen[n] = at
                    todo.append(n)
    return straight


def there(house, cfg, room, pos, goal):
    """Has it got as near as it can? On the goal, or beside it when the goal is open water."""
    return pos == goal or (max(abs(pos[0] - goal[0]), abs(pos[1] - goal[1])) <= 1 and tuple(goal) in wet(house, cfg, room))


# ---- the spread: once, on load ----

def spread(house, cfg):
    """A house whose pond is not yet the size pond.toml says has it spread, once: the water is laid, what stood
    where it now lies moves to the edge (fixtures, things on the floor, bits), the bridge is laid across the neck,
    and the story says so. A new house is born with the big pond (house.toml) and nothing happens."""
    room, S = room_of(house, cfg), state(house)
    if not room:
        return
    if S["stock"] is None:
        S["stock"] = float(P(cfg)["fish"]["most"])
    pool = next((o for o in room["objects"].values() if "water" in o.get("fix", {})), None)
    want = [list(t) for t in P(cfg)["pond"]["water"]]
    if not pool or sorted(map(tuple, pool["fix"]["water"])) == sorted(map(tuple, want)):
        S["spread"] = S["spread"] or house["tick"]
        return
    pool["fix"]["water"] = want
    wet_ = {tuple(t) for t in want}
    moved = []
    bridge = next((n for n, o in room["objects"].items() if "fix" in o and n.endswith("bridge")), None)
    if bridge:   # the hobs' bridge: laid across the neck, still theirs
        room["objects"][bridge]["pos"] = list(P(cfg)["pond"]["bridge"][0])
    for n, o in list(room["objects"].items()):
        if n == bridge or o is pool or o.get("on") or o.get("wall") or tuple(o["pos"]) not in wet_:
            continue
        o["pos"] = free_tile(house, cfg, room, o["pos"], n)   # (free_tile keeps off the water)
        moved.append(n)
        for x in room["objects"].values():   # what was on it goes with it
            if x.get("on") == n:
                x["pos"] = list(o["pos"])
    for s in room["spots"]:
        if tuple(s["pos"]) in wet_:
            s["pos"] = free_tile(house, cfg, room, s["pos"])
    for p in house["pets"].values():
        if p["room"] == room["id"] and tuple(p["pos"]) in wet_:
            p["pos"] = free_tile(house, cfg, room, p["pos"])
    for c in house["creatures"]:
        if c["room"] == room["id"] and tuple(c["pos"]) in wet_ and c["kind"] not in ("train", "duck"):
            c["pos"] = free_tile(house, cfg, room, c["pos"])
    S["spread"] = house["tick"]
    text = "%s: it fills most of %s now%s" % (P(cfg)["pond"]["spread"], room["name"], ", and what stood where the water lies was moved to its edge (%s)" % ", ".join(moved) if moved else "")
    moment(house, "pond", text, None, room["id"])
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead"):
            add_event(house, p, "%s: the water fills most of %s now, with a walkway round it" % (P(cfg)["pond"]["spread"], room["name"]))
    from . import rail
    if house.get("rail") and rail.train(house):
        rail.lay(house, cfg)   # (the track keeps off the water: it is laid again round it)


def build_dock(house, cfg, new=False):
    """The Works has built the dock (works.toml `dock`): it goes out over the water from the south walkway."""
    S, room = state(house), room_of(house, cfg)
    if S["dock"] or not room:
        return
    S["dock"] = {"tiles": [list(t) for t in P(cfg)["dock"]["tiles"]], "end": list(P(cfg)["dock"]["end"])}
    for n, o in room["objects"].items():   # nothing is left standing on it
        if not o.get("on") and not o.get("wall") and "fix" not in o and o["pos"] in S["dock"]["tiles"]:
            o["pos"] = free_tile(house, cfg, room, o["pos"], n)
    if new:
        moment(house, "pond", "a wooden dock goes out over the pond now, with a post at its end", None, room["id"])


def drift(house, cfg, room, name):
    """A thing set on the big pond's water floats off out of sight, and washes up at its edge a world day later
    (things.upkeep; `hourly` brings it back). True if it drifted."""
    if room["type"] != P(cfg)["pond"]["room"]:
        return False
    o = room["objects"].pop(name)
    state(house).setdefault("drift", []).append({"name": name, "back": house["tick"] + cfg["ticks_per_day"], "o": o})
    owner = house["pets"].get(o["made"]["owner"])
    if owner and owner["stage"] != "dead":
        add_event(house, owner, "your %s drifted off across the pond, out of sight" % name)
    moment(house, "floated", "the %s drifted off across the pond" % name, None, room["id"])
    return True


# ---- every world hour ----

def hourly(house, cfg):
    """The fish come back; the pond freezes in the coldest weeks and thaws after; a new day's catches start at none;
    a fish carried a world day is no good, and goes to the edge for the birds."""
    room, S, F = room_of(house, cfg), state(house), P(cfg)["fish"]
    if not room:
        return
    if S["stock"] is None:
        S["stock"] = float(F["most"])
    S["stock"] = round(min(F["most"], S["stock"] + F["most"] / (24 * F["back_days"])), 3)
    if S["thin"] and S["stock"] >= F["most"] * F["thin"]:
        S["thin"] = False
    day = house["clock"]["day"]
    if S["today"][0] != day:
        S["today"], S["catches"] = [day, 0], []
    ice = frozen(house, cfg)
    if ice != S["frozen"]:
        S["frozen"], S["holes"] = ice, []
        moment(house, "pond", "the pond froze over: the hobs can walk on the ice" if ice else "the ice on the pond broke up, and the water is open again", None, room["id"])
        for p in house["pets"].values():
            if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                add_event(house, p, "the pond has frozen over" if ice else "the ice on the pond has broken up")
    for d in [d for d in S.get("drift", []) if house["tick"] >= d["back"]]:   # what drifted off washes up at the edge
        S["drift"].remove(d)
        edge = [s for s, _, how in spots(house, cfg, room) if how != "from the dock"] or [[1, 6]]
        d["o"]["pos"] = free_tile(house, cfg, room, edge[0])
        name = things.unique_name(house, cfg, d["name"]) if d["name"] in room["objects"] else d["name"]
        room["objects"][name] = d["o"]
        moment(house, "floated", "the %s washed up at the edge of the pond" % name, None, room["id"])
        owner = house["pets"].get(d["o"]["made"]["owner"])
        if owner and owner["stage"] != "dead":
            add_event(house, owner, "your %s has washed up at the edge of the pond" % name)
    spoil = P(cfg)["eat"]["spoil_days"] * cfg["ticks_per_day"]
    for p in house["pets"].values():
        caught = p.get("caught_at")
        if caught and house["tick"] - caught >= spoil:
            gone = [b for b in p["carrying"] if b in ("fish", "big fish")]
            p.pop("caught_at")
            if gone:
                p["carrying"] = [b for b in p["carrying"] if b not in ("fish", "big fish")]
                add_event(house, p, "the %s you were carrying has gone off; you left it at the water's edge for the birds" % gone[0])


# ---- fishing ----

def refuses(mem):
    """A family whose beliefs have turned against taking fish leaves them alone: its own beliefs say so."""
    return any("fish" in b.get("statement", "").lower() and REFUSE.search(b["statement"].lower()) for b in (mem.active() if mem else []))


def fishers(house, room, but=None):
    from .body import state as body
    return [p for p in house["pets"].values() if p["room"] == room["id"] and p is not but and p["stage"] not in ("egg", "dead")
            and ((body(p).get("now") or {}).get("do") == "fish")]


def fished(house, cfg, pet):
    """World ticks it has fished today."""
    f = pet.get("fished") or [0, 0]
    return f[1] if f[0] == house["clock"]["day"] else 0


def spots(house, cfg, room):
    """[(where it sits, the water tile its line goes into, how it is said)]: the dock's end (once built, not
    while frozen), else dry tiles at the water's edge; while frozen, beside the holes in the ice."""
    from . import rail
    S = state(house)
    track = rail.on_track(house, room["id"]) if house.get("rail") else set()
    doors = {tuple(house["door_tiles"][d]) for d in room["doors"]}
    fixed = {tuple(o["pos"]) for o in room["objects"].values() if not o.get("wall") and not o.get("on") and ("fix" in o or things.prop(cfg, o).get("fixed"))}
    bad = doors | {tuple(t) for t in track} | fixed | {tuple(t) for t in room.get("blocked", [])}
    dock = {tuple(t) for t in (S["dock"] or {}).get("tiles", [])}
    out = []
    if S["dock"] and not S["frozen"]:
        out.append((S["dock"]["end"], P(cfg)["dock"]["line"], "from the dock"))
    open_ = [tuple(t) for t in (S["holes"] if S["frozen"] and S["holes"] else water(room))]   # (frozen with no hole yet: the edge, where one is cut)
    stand = (set(map(tuple, water(room))) - set(open_)) if S["frozen"] and S["holes"] else set()
    for (x, y) in open_:
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            t = (x + dx, y + dy)
            if 0 <= t[0] < 12 and 0 <= t[1] < 8 and t not in bad and t not in dock and (t not in {tuple(w) for w in water(room)} or t in stand):
                out.append((list(t), [x, y], "through the hole in the ice" if S["frozen"] else "at the water's edge"))
    return out


def roll(house, cfg, pet, rod, dock):
    """What comes up on this pull, or None: by paw only common things, with a rod uncommon ones too, and rare and
    very rare ones only from the dock with a rod. A fish only if there is one left to catch."""
    S, O, F = state(house), P(cfg)["odds"], P(cfg)["fish"]
    r = rnd(house, "fish", pet["id"], house["tick"])
    p = (O["rod"] if rod else O["paw"]) + O["skill"] * craft.skill(cfg, pet, "fishing")
    p *= (F["thin_odds"] if (S["stock"] or 0) < F["most"] * F["thin"] else 1.0) * (O["frozen"] if S["frozen"] else 1.0)
    if r.random() >= p:
        return None
    x = r.random()
    tier = "common"
    if rod and dock and x < O["very_rare"]:
        tier = "very rare"
    elif rod and dock and x < O["very_rare"] + O["rare"]:
        tier = "rare"
    elif rod and x < O["very_rare"] + O["rare"] + O["uncommon"]:
        tier = "uncommon"
    can = [c for c in P(cfg)["catch"] if c["tier"] == tier and (not c.get("fish") or (S["stock"] or 0) >= 1)]
    if not can:
        return None
    pick = r.uniform(0, sum(c.get("weight", 1) for c in can))
    for c in can:
        pick -= c.get("weight", 1)
        if pick <= 0:
            return dict(c)
    return dict(can[-1])


def targets(house, cfg, pet, mem, room, A):
    """body.targets for `fish`: a place at the water (the dock's end for one with a rod), and what it will pull up."""
    S, T = state(house), P(cfg)["time"]
    if room["type"] != P(cfg)["pond"]["room"] or pet["stage"] in ("egg", "hatchling") or house["clock"]["phase"] == "night" or refuses(mem):
        return []
    if fished(house, cfg, pet) >= T["share"] * cfg["ticks_per_day"]:
        return []   # (fishing does not take over its day)
    others = fishers(house, room, pet)
    if len(others) >= P(cfg)["fish"]["fishers"]:
        return []
    from .body import state as body
    taken = {tuple(p["pos"]) for p in house["pets"].values() if p["room"] == room["id"] and p is not pet and p["stage"] != "dead"}
    taken |= {tuple(body(p)["now"].get("goal") or p["pos"]) for p in others}
    rod = craft.tool_for(house, cfg, pet, "rod")
    can = [s for s in spots(house, cfg, room) if tuple(s[0]) not in taken]
    if not can:
        return []
    if S["frozen"] and not S["holes"]:   # the ice has to be opened first: a hole is cut where it stands
        at = min(can, key=lambda s: dist(s[0], pet["pos"]))
        knife = craft.tool_for(house, cfg, pet, "carver")
        lo, hi = T["cut"]
        return [{"what": "pond", "goal": None if pet["pos"] == at[0] else at[0], "where": "cutting a hole in the ice",
                 "fish": {"cut": True, "spot": at[0], "line": at[1], "rod": False}, "seconds": (lo / 2, hi / 2) if knife else (lo, hi)}]
    dock = [s for s in can if s[2] == "from the dock"]
    at = dock[0] if dock and rod else min((s for s in can if s[2] != "from the dock") or can, key=lambda s: dist(s[0], pet["pos"]))
    hungry = 0.6 if feel.level(pet, "energy") >= 2 else 0.0
    return [{"what": "pond", "goal": None if pet["pos"] == at[0] else at[0], "where": at[2], "bonus": hungry + (0.3 if rod else 0.0),
             "fish": {"spot": at[0], "line": at[1], "rod": bool(rod), "dock": at[2] == "from the dock", "catch": roll(house, cfg, pet, rod, at[2] == "from the dock")},
             "seconds": tuple(T["rod"] if rod else T["paw"])}]


def found(house, cfg, pet, room, c):
    """A thing out of the pond: new (never a lost thing come back), with a "from the pond" mark; rare and very rare
    ones kept for good, with a title. Returns (its name, the thing)."""
    r = rnd(house, "found", pet["id"], house["tick"])
    recipe = {"kind": c["kind"], "material": c["material"], "color": r.choice(c["colors"]), "size": 1, "purpose": "found in the pond"}
    title = None
    if c.get("titles"):
        taken = {o["made"]["recipe"].get("title") for x in house["rooms"].values() for o in things.made(x).values()}
        title = next((t for t in c["titles"] if t not in taken), "%s's %s" % (label(pet), c["what"].title()))
        recipe["title"] = title
    name = things.everyday(house, cfg, recipe, [], pet, room)
    house["n"]["thing"] += 1
    o = {"pos": free_tile(house, cfg, room, pet["pos"]),
         "made": {"id": house["n"]["thing"], "recipe": recipe, "by": pet["id"], "owner": pet["id"], "tick": house["tick"], "bits": [], "uses": 0, "ups": 0,
                  "used_at": house["tick"], "heirloom": None, "behavior": None, "fine": 0, "how": "pulled up out of the pond", "made_in": room["name"],
                  "users": {}, "words": [], "found": {"from": "pond", "tier": c["tier"], "by": pet["id"], "tick": house["tick"]}}}
    if c["kind"] == "note bottle":
        o["made"]["note"] = r.choice(P(cfg)["note"]["says"])
    room["objects"][name] = o
    return name, o


def eats_raw(cfg, pet):
    return pet["temper"].get("bold", 0.5) >= P(cfg)["eat"]["raw_bold"]


def eat(house, cfg, pet, bit):
    """A raw fish eaten: (what it is told, what it does to it)."""
    E = P(cfg)["eat"]
    soon = (house["tick"] - pet.get("last_eat", -10 ** 9)) * cfg["clock"]["tick_seconds"] <= cfg["effects"]["double_feed_seconds"]
    pet["prev_eat"], pet["last_eat"] = pet.get("last_eat", -10 ** 9), house["tick"]
    house.setdefault("pond_eaten", []).append([house["tick"], pet["id"], bit])
    del house["pond_eaten"][:-200]
    return "you ate the %s raw, there by the water%s" % (bit, "; it sits heavy, so soon after eating" if soon else ""), ({"comfort": -1.0} if soon else dict(E[bit]))


def landed(mind, now):
    """body.finish for `fish`: (what it is told, what it does to it, the novelty key)."""
    from . import body
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    room, S, F = h["rooms"][pet["room"]], state(h), now["fish"]
    day = h["clock"]["day"]
    f = pet.get("fished") or [day, 0]
    pet["fished"] = [day, (f[1] if f[0] == day else 0) + now.get("of", 0)]
    if F.get("cut"):
        if S["frozen"] and F["line"] not in S["holes"]:
            S["holes"].append(F["line"])
        moment(h, "pond", "%s cut a hole in the ice on the pond" % label(pet), pet["id"], room["id"])
        return "you cut a hole in the ice: there is open water under it to fish in", {}, "cut ice"
    rod = craft.tool_for(h, cfg, pet, "rod") if F.get("rod") else None
    if rod:
        if rod[0] is not room:
            craft.fetch(h, cfg, pet, "rod")
        name = craft.tool_for(h, cfg, pet, "rod")
        if name and name[0] is room:
            craft.wear(h, cfg, pet, room, name[1])
    else:
        pet["paw_fished"] = pet.get("paw_fished", 0) + 1
        if pet["paw_fished"] >= 2:   # SPEC-v3.6a §2: wanting fish leads to wanting a rod
            pet.setdefault("lacks", {})["rod"] = h["tick"]
    c = F.get("catch")
    if c and c.get("fish") and (S["stock"] or 0) < 1:
        c = None   # (someone else had the last one)
    craft.practise(h, cfg, pet, "fishing", 1.0 if c else 0.4)
    how = "your rod" if F.get("rod") else "a paw"
    if not c:
        return "you sat a while %s with %s in the water; nothing came" % (now.get("where") or "by the pond", how), {}, None
    if c.get("fish"):
        S["stock"] = round(S["stock"] - 1, 3)
        if not S["thin"] and S["stock"] < P(cfg)["fish"]["most"] * P(cfg)["fish"]["thin"]:
            S["thin"] = True
            moment(h, "pond", "the pond is fished thin: the fish are few, and slow to bite", None, room["id"])
    if S["today"][0] != day:
        S["today"], S["catches"] = [day, 0], []
    S["today"][1] += 1
    S["catches"] = (S["catches"] + [{"tick": h["tick"], "pet": pet["id"], "what": c["what"], "tier": c["tier"], "spot": list(pet["pos"]), "line": F["line"], "rod": bool(F.get("rod"))}])[-40:]
    now["caught"] = c
    if c.get("bit"):
        bit = c["bit"]
        moment(h, "catch", "%s %s %s" % (label(pet), "caught" if c.get("fish") else "fished up", things_a(c["what"])), pet["id"], room["id"])
        hungry = feel.level(pet, "energy") >= 2
        if c.get("fish") and hungry and eats_raw(cfg, pet):
            told, fx = eat(h, cfg, pet, bit)
            return "you pulled up %s with %s; %s" % (things_a(c["what"]), how, told), fx, "fish"
        kin = next((p for p in h["pets"].values() if p["room"] == room["id"] and p is not pet and p["stage"] not in ("egg", "dead") and not p["sleep"]
                    and family(p) == family(pet) and feel.level(p, "energy") >= 2 and eats_raw(cfg, p)), None) if c.get("fish") else None
        if kin:   # SPEC-v3.6a §4: shared with kin, it counts as being with them
            told, fx = eat(h, cfg, kin, bit)
            from . import actions
            actions.bump(kin, cfg, dict(fx, company=P(cfg)["eat"]["share"]))
            add_event(h, kin, "%s gave you the %s it had just caught, and %s" % (label(pet), bit, told.replace("you ate", "you ate it").split("; ")[0][len("you ate the %s " % bit):] or "you ate it"))
            moment(h, "shared", "%s shared a %s it caught with %s" % (label(pet), bit, label(kin)), pet["id"], room["id"])
            return "you pulled up %s with %s and gave it to %s, who ate it" % (things_a(c["what"]), how, label(kin)), {"company": P(cfg)["eat"]["share"]}, "fish"
        craft.give(h, cfg, pet, room, bit)
        if c.get("fish"):
            pet["caught_at"] = pet.get("caught_at") or h["tick"]
        return "you pulled up %s with %s" % (things_a(c["what"]), how), {}, "fish"
    name, o = found(h, cfg, pet, room, c)
    now["thing"] = S["catches"][-1]["thing"] = name
    title = o["made"]["recipe"].get("title")
    if c["tier"] in ("rare", "very rare"):
        if c["kind"] == "golden fish":
            return golden(h, cfg, pet, room, name, o, how)
        board = ("A NOTE IN A BOTTLE FROM OUTSIDE: %s" if c["kind"] == "note bottle" else "FROM THE POND, %s: %s" % (c["what"].upper(), "%s")) % label(pet).upper()
        text = "%s fished up %s out of the pond%s" % (label(pet), things_a(c["what"]), ", and called it %s" % title if title else "")
        feats.record(h, cfg, "find", pet["id"], text, board=board, room=room["id"], thing=name, tier=c["tier"])
        for p in h["pets"].values():
            if p is not pet and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                add_event(h, p, "%s pulled %s up out of the pond" % (label(pet), things_a(c["what"])))
        said = "you pulled up %s with %s: it is %s, and it will be kept for good" % (things_a(c["what"]), how, title)
        if c["kind"] == "note bottle":
            said += '; there is a note rolled up inside. It says: "%s"' % o["made"]["note"]
        return said, {"curiosity": 6.0}, "find " + c["kind"]
    moment(h, "catch", "%s fished up %s" % (label(pet), things_a(c["what"])), pet["id"], room["id"])
    return "you pulled up %s with %s; it lies by the water now, the %s" % (things_a(c["what"]), how, name), {"curiosity": 2.0}, "find " + c["kind"]


def golden(house, cfg, pet, room, name, o, how):
    """A golden fish: kept in a bowl if there is one to hand, or let go, which the house remembers."""
    bowl = next((n for n, x in things.made(room).items() if things.kind_of(x) in ("bowl", "jar", "bucket") and not x.get("on") and n != name), None)
    if bowl and pet["temper"].get("sensitive", 0.5) < 0.6:
        o["on"], o["pos"] = bowl, list(room["objects"][bowl]["pos"])
        feats.record(house, cfg, "find", pet["id"], "%s caught a golden fish and keeps it in the %s; it is called %s" % (label(pet), bowl, o["made"]["recipe"]["title"]),
                     board="A GOLDEN FISH: %s" % label(pet).upper(), room=room["id"], thing=name, tier="rare")
        return "you pulled up a golden fish with %s! You put it in the %s, and it swims round and round; you call it %s" % (how, bowl, o["made"]["recipe"]["title"]), {"curiosity": 6.0}, "find golden fish"
    del room["objects"][name]
    things.gone(house, o, name, "let go into the pond")
    feats.record(house, cfg, "find", pet["id"], "%s caught a golden fish, looked at it a long moment, and let it go" % label(pet),
                 board="A GOLDEN FISH, LET GO: %s" % label(pet).upper(), room=room["id"], tier="rare")
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead") and not p["sleep"]:
            add_event(house, p, "%s caught a golden fish in the pond, and let it go again" % label(pet) if p is not pet else
                      "you pulled up a golden fish with %s, held it a moment in the light, and let it go back into the water" % how)
    return "you pulled up a golden fish with %s, held it a moment in the light, and let it go back into the water" % how, {"comfort": 4.0, "curiosity": 6.0}, "golden fish"


def things_a(what):
    return ("an " if what[0] in "aeiou" else "a ") + what


def view(house, cfg):
    """For the page (CONTRACT.md): the pond's water, dock, ice, stock, today's catches and who is fishing."""
    from .body import state as body
    room = room_of(house, cfg)
    if not room:
        return None
    S, F = state(house), P(cfg)["fish"]
    stock = S["stock"] if S["stock"] is not None else F["most"]
    out = []
    for p in fishers(house, room):
        now = body(p)["now"]
        fi = now.get("fish") or {}
        if now.get("began") is None or fi.get("cut"):
            continue
        end = now["began"] + now.get("of", 0)
        c = fi.get("catch")
        out.append({"pet": p["id"], "spot": p["pos"], "line": fi.get("line"), "rod": bool(fi.get("rod")), "cast": now["began"],
                    "bite": end - 2 if c else None, "pulled": None, "caught": None})
    for c in S["catches"][-4:]:   # the last pull, for a moment after it: the splash and the catch held up
        if house["tick"] - c["tick"] <= 3 and c.get("spot"):
            out = [x for x in out if x["pet"] != c["pet"]] + [{"pet": c["pet"], "spot": c["spot"], "line": c["line"], "rod": c["rod"], "cast": c["tick"] - 8,
                                                              "bite": c["tick"] - 2, "pulled": c["tick"], "caught": {"what": c["what"], "tier": c["tier"], "thing": c.get("thing")}}]
    return {"room": room["id"], "water": water(room), "dock": S["dock"] and dict(S["dock"], tiles=S["dock"]["tiles"]), "frozen": S["frozen"], "holes": S["holes"],
            "stock": int(stock), "most": F["most"], "says": "fished thin" if stock < F["most"] * F["thin"] else "plenty of fish" if stock >= F["most"] * 0.7 else "some fish",
            "today": S["today"][1] if S["today"][0] == house["clock"]["day"] else 0, "fishers": out, "catches": S["catches"]}
