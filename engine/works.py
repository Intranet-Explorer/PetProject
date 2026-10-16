"""The Works (SPEC-v3.5.4 §8): the machine in the machine room has a goal. What it is fed counts as scrap toward the
next thing on its list (works.toml, cheapest first); when its meter is full it builds that thing for the whole house,
everyone who fed it is named and proud, and the next goal starts. No model is asked. The pets hear of it in words:
the packet's line at the machine, the board (§11), and a want to feed it (machine.wants calls `wants`).

What it has built stays built: the house keeps the list (`house["works"]["built"]`) and `lay` lays each one into the
config, and a fixture into its room, on load and when it is built, as machine.migrate lays the machine into a room.

Scrap counts once for each thing (by the thing's id: it is kept), and only for a thing made at least `age_hours`
world hours before it is fed. The machine gives a material back for whatever it is fed, so without that a pet could
take a material, make a thing of it, feed it and be given another, round and round; with it, nothing fresh from the
machine counts until it has lain about the house a while, so each scrap is a thing made and kept, not a loop. Three
bits count as one: they give one back for three, so they cannot go round."""
import tomllib

from . import feats, order, things
from .world import add_event, days, label, moment

FULL = ["it has nothing in it yet", "it has a little in it", "it is about half full", "it is nearly full"]


def load(cfg, directory):
    """works.toml, laid into the config."""
    cfg["works"] = tomllib.loads((directory / "works.toml").read_text())
    return cfg


def state(house, cfg):
    return house.setdefault("works", {"goal": 0, "have": 0, "fed": {}, "counted": [], "built": []})


def goal(house, cfg):
    """What the Works is gathering scrap for now, or None once it has built everything on its list."""
    L, g = cfg["works"]["build"], state(house, cfg)["goal"]
    return L[g] if g < len(L) else None


def full(house, cfg):
    """How full its meter is, in words (never a number)."""
    g, S = goal(house, cfg), state(house, cfg)
    k = S["have"] / g["scrap"] if g else 0
    return FULL[0 if not S["have"] else 3 if k >= cfg["works"]["works"]["nearly"] else 2 if k >= 0.4 else 1]


def nearly(house, cfg):
    g = goal(house, cfg)
    return bool(g) and state(house, cfg)["have"] >= g["scrap"] * cfg["works"]["works"]["nearly"]


def view(house, cfg):
    """For the page and the board: the goal and its meter (the visitor may see the numbers), or None."""
    from . import machine
    g = goal(house, cfg)
    if not g or not machine.found(house):
        return None
    return {"what": g["what"], "have": state(house, cfg)["have"], "need": g["scrap"], "says": full(house, cfg),
            "line": "THE WORKS NEEDS %d SCRAP: %s" % (g["scrap"], g["what"].upper()), "built": [b["what"] for b in state(house, cfg)["built"]]}


# ---- the spring clean (SPEC-v3.5.8 §4) ----

def spring(house, cfg):
    """Is the spring clean on: the world days after it was called, while scrap is wanted fed all the more?"""
    return house["tick"] < (house.get("spring_clean") or {}).get("until", 0)


def spring_clean(house, cfg):
    """Once, when v3.5.8 comes to a house: the family is told the old charms could go to the Works, and the story
    says so. What is cleared, they clear by their own paws over the next world days."""
    from . import hub
    if "spring_clean" in house:
        return
    house["spring_clean"] = {"at": house["tick"], "until": house["tick"] + round(cfg["works"]["works"]["spring_days"] * cfg["ticks_per_day"])}
    moment(house, "spring", "A spring clean: the old charms about the house, and the things nobody uses, could go to the Works as scrap", None, hub.RID)
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead"):
            add_event(house, p, "it is time for a spring clean: there are too many old charms about the house. Everyone keeps their few newest charms, "
                                "and anything that means something; the rest, and things nobody uses, could go to the Works as scrap, and the Works gives something back for scrap")


# ---- fed ----

def key(o):
    m = o["made"]
    return m.get("id") if m.get("id") is not None else "%s|%s" % (m["tick"], m["recipe"].get("name"))


def counts(house, cfg, o):
    """Would this made thing count as scrap: the Works has a goal, the thing has not counted before, and it is old enough."""
    W = cfg["works"]["works"]
    return bool(goal(house, cfg)) and key(o) not in state(house, cfg)["counted"] and days(cfg, o["made"]["tick"], house["tick"]) * 24 >= W["age_hours"]


def fed(house, cfg, pet, o=None):
    """machine.feed calls this with what it was fed: a made thing `o`, or None for three bits. Returns what the pet is
    told of the Works and what it feels for it: helping fill it is worth what a paw in a build is (building.toml
    [build] lift). ("", {}) when it did not count."""
    from . import machine
    W, S, g = cfg["works"]["works"], state(house, cfg), goal(house, cfg)
    if not g or not machine.found(house) or (o is not None and not counts(house, cfg, o)):
        return "", {}
    if o is not None:
        S["counted"] = (S["counted"] + [key(o)])[-W["keep"]:]
    S["have"] += W["thing"] if o is not None else W["bits"]
    if pet:   # (the sweeper's scrap counts, and names nobody)
        S["fed"][pet["id"]] = S["fed"].get(pet["id"], 0) + 1
    lift = dict(cfg["build"]["build"]["lift"])
    if S["have"] >= g["scrap"]:
        built(house, cfg, g)
        return "; it was the last scrap the Works needed, and it has built %s" % g["what"], lift
    return "; the Works took it as scrap for %s, and %s" % (g["what"], full(house, cfg)), lift


def built(house, cfg, g):
    """The meter is full: the thing is built, everyone who fed it is named and proud, the next goal starts."""
    from . import hub, machine
    S = state(house, cfg)
    who = sorted(S["fed"], key=lambda p: -S["fed"][p])   # whoever fed it most first
    names = [label(house["pets"][p]) for p in who if p in house["pets"]]
    S["built"].append({"what": g["what"], "tick": house["tick"], "by": who})
    S.update(goal=S["goal"] + 1, have=0, fed={})
    lay(house, cfg, new=g)
    if g.get("sweeper"):   # SPEC-v3.5.8 §4.2
        from . import sweeper
        sweeper.make(house, cfg)
    feats.record(house, cfg, "works", None, "The Works built %s, fed by %s" % (g["what"], machine.listed(names)),
                 board="THE WORKS BUILT %s: %s" % (g["what"].upper(), machine.listed(names).upper()), room=hub.RID, pets=who,
                 **{"for": "feeding the Works for %s" % g["what"]})
    for p in house["pets"].values():
        if p["stage"] in ("egg", "dead"):
            continue
        if p["id"] in who:
            feats.glow(house, cfg, p, 2, "you helped fill the Works, and it has built %s" % g["what"])
        elif p["room"] == hub.RID and not p["sleep"]:
            add_event(house, p, "the machine rumbled and clanked: the Works has built %s" % g["what"])


def lay(house, cfg, new=None):
    """What the Works has built, laid into the config, and a fixture into every found room of its type: on load
    (tick.alive_migration) and as each is built (`new`). Safe to call again."""
    from . import machine, world
    M, done = cfg["machine"], {b["what"] for b in state(house, cfg)["built"]}
    for b in cfg["works"]["build"]:
        if b["what"] not in done:
            continue
        for k, v in (b.get("machine") or {}).items():
            M[k] = max(M[k], v)
        m = b.get("material")
        if m and m not in M["materials"]:
            M["materials"] = M["materials"] + [m]
        if m and machine.found(house):
            stock = machine.state(house, cfg)["stock"]
            stock.setdefault(m, 0)
            if b is new:
                machine.fill(house, cfg, m, M["restock"])
        if b.get("sweeper") and b is not new:   # (built before this house was opened: it is there; made once, on its dock)
            from . import sweeper
            sweeper.make(house, cfg)
        f = dict(b.get("fixture") or {})
        kind = f.pop("room", None)
        if not kind:
            continue
        fixtures = cfg["house"]["rooms"][kind]["fixtures"]
        if f["name"] not in [x["name"] for x in fixtures]:
            fixtures.append(f)
        for room in [r for r in house["rooms"].values() if r["type"] == kind and f["name"] not in r["objects"]]:
            room["objects"][f["name"]] = world.fixture(f)
            world.layout(cfg, room)
            world.settle(house, cfg, room)
            if b is new:
                for p in house["pets"].values():
                    if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                        add_event(house, p, "there is a %s here that was not here before: the Works built it" % f["name"])


# ---- the pets ----

def sense(house, cfg, pet):
    """One line for the packet at the machine (machine.sense adds it): the goal and how near it is, in words."""
    g = goal(house, cfg)
    if not g:
        return []
    return ["the Works (the machine here) is gathering scrap to build %s; %s; old made things and loose bits fed to it are scrap for it"
            % (g["what"], full(house, cfg))]


def wants(house, cfg, pet, known, out, add):
    """machine.wants calls this last. While the Works has a goal, a spare thing wanted fed is wanted for it too, and
    more; and once it is nearly full, a pet with an old thing of its own nobody has touched lately wants to feed it."""
    g, W = goal(house, cfg), cfg["works"]["works"]
    if not g:
        return
    why = "the Works wants scrap for %s" % g["what"]
    for c in out:
        if c["what"] == "feed":
            c["text"] += "; %s" % why
            c["weight"] *= W["weight"]
    if not nearly(house, cfg) or any(c["what"] == "feed" and c.get("thing") != "bits" for c in out):
        return
    from . import machine
    mine = [(o["made"]["tick"], n, o, r) for r in known for n, o in things.made(r).items() if o["made"]["by"] == pet["id"] or o["made"]["owner"] == pet["id"]]
    newest = max(mine, key=lambda x: x[0])[1] if mine else None   # (the newest thing it made stays: §1)
    old = sorted((order.last_touch(o), n, r) for _, n, o, r in mine if n != newest and o["made"]["owner"] == pet["id"] and not o.get("wall")
                 and o["made"]["recipe"].get("kind") not in cfg["craft"]["tool"] and not order.cap(cfg, o) and counts(house, cfg, o)
                 and days(cfg, order.last_touch(o), house["tick"]) >= W["idle_days"] and not machine.refuses(house, cfg, pet, r, n))
    for _, n, r in old[:1]:
        add("feed", n, "the Works is nearly full: it wants scrap for %s; your old %s in %s could go to it" % (g["what"], n, r["name"]),
            "fed the %s to the Works" % n, cfg["machine"]["feed_weight"] * W["nearly_weight"], thing=n, room=r["id"])
