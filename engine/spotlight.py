"""New things get a season (SPEC-v3.6c §3): whenever something new arrives in the house (a machine built, a new
outdoor place, a new kind of activity: fishing with a rod, cooking), it has a few world days in the
spotlight so it is tried rather than lost among everyday wants. Called spotlights here: "season" is the year's.

The board and the story announce it and every hob is told; for three world days, or until two hobs have tried it, the
wants that lead to it rank above routine ones (wants.refresh), and a hob near it that has not tried it feels curious
about it (mind.py). Never more than two at once: the rest wait their turn in a queue, in order, and one may wait for
another to end first (`after`). On deploy the newest things are queued (migrate): the kiln and the outdoors at once,
then fishing with a rod (SPEC-v5.1 §4.5: designing's season is gone with designing). Switch: [spotlight] on. No model is asked."""
from .world import add_event, label, moment

OUTDOOR = ("ryard", "rmeadow")
PROCESS = {"fire": "kiln", "loom": "loom", "mill": "millstone", "forge": "forge", "cook": "stove"}   # crafting.toml's processes at each machine


def S(cfg):
    return cfg.get("spotlight", {})


def state(house):
    return house.setdefault("spotlights", {"on": [], "queue": [], "done": []})


def off(house):
    """Is the switch off ([spotlight] on = false)? Then nothing is in the spotlight, whatever was before (each tick
    and each load set this from the config)."""
    return bool((house.get("spotlights") or {}).get("off"))


def on(house, key):
    """Is this in the spotlight now?"""
    return not off(house) and any(s["key"] == key for s in (house.get("spotlights") or {}).get("on", []))


def known(house, key):
    st = house.get("spotlights") or {}
    return any(s["key"] == key for s in st.get("on", []) + st.get("queue", []) + st.get("done", []))


def queue(house, cfg, key, title, what, room=None, thing=None, after=None):
    """Something new: in the spotlight as soon as there is room (and whatever it waits `after` has ended). Once each."""
    if not S(cfg).get("on") or known(house, key):
        return False
    state(house)["queue"].append({"key": key, "title": title, "what": what, "room": room, "thing": thing, "after": after,
                                  "since": None, "until": None, "tried": [], "ended": None})
    tick(house, cfg)
    return True


def start(house, cfg, s):
    s["since"], s["until"] = house["tick"], house["tick"] + round(S(cfg)["days"] * cfg["ticks_per_day"])
    state(house)["on"].append(s)
    moment(house, "spotlight", "Something new: %s" % s["what"], None, s["room"])
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead"):
            add_event(house, p, "there is something new in the house: %s%s; everyone is curious about it" % (s["what"], " in %s" % house["rooms"][s["room"]]["name"] if s["room"] and house["rooms"][s["room"]].get("type") else ""))
            p["news"].append("event")


def tick(house, cfg):
    """End what has been tried by enough hobs or had its days; start what waits, up to two at once. Switched off, it
    only notes so: everything that asks (on, boost, near, tried, the page) then sees no spotlight at all."""
    if house.get("spotlights") is not None:
        house["spotlights"]["off"] = not S(cfg).get("on")
    if not S(cfg).get("on") or "migrated" not in (house.get("spotlights") or {}):
        return
    st, t = state(house), house["tick"]
    for s in [s for s in st["on"] + st["queue"] if s["key"] == "designing"]:   # (SPEC-v5.1 §4.5: designing's season ends with designing)
        (st["on"] if s in st["on"] else st["queue"]).remove(s)
        s["ended"] = t
        st["done"].append(s)
    for s in list(st["on"]):
        if len(s["tried"]) >= S(cfg)["tried"] or t >= s["until"]:
            s["ended"] = t
            st["on"].remove(s)
            st["done"].append(s)
    ended = {s["key"] for s in st["done"]}
    for s in list(st["queue"]):
        if len(st["on"]) >= S(cfg)["most"]:
            break
        if s.get("after") and s["after"] not in ended:
            continue
        st["queue"].remove(s)
        start(house, cfg, s)


def tried(house, cfg, key, pet):
    """A hob has tried it (ran the machine, went out, fished with a rod, designed something)."""
    if off(house) or not S(cfg).get("on"):
        return
    for s in (house.get("spotlights") or {}).get("on", []):
        if s["key"] == key and pet["id"] not in s["tried"]:
            s["tried"].append(pet["id"])
            moment(house, "tried", "%s tried %s" % (label(pet), s["what"]), pet["id"], pet["room"])
    tick(house, cfg)


def want_key(house, cfg, c):
    """The spotlight a want leads to, or None: building the machine or using it, a door to the outdoors, the rod, or a
    want that names its spotlight itself (`spot`)."""
    w = c.get("what")
    if c.get("spot"):
        return c["spot"]
    if w == "build":
        return c.get("project")
    if w in ("try", "get") and c.get("how") in PROCESS:
        return PROCESS[c["how"]]
    if w == "door" and c.get("room") in OUTDOOR:
        return "outdoors"
    if w == "tool" and c.get("tool") == "rod":
        return "rod"
    return None


def boost(house, cfg, c):
    """How much more a want weighs for leading to something in the spotlight: above routine wants (SPEC-v3.6c §3)."""
    k = want_key(house, cfg, c)
    return S(cfg).get("boost", 1.0) if k and on(house, k) else 1.0


def near(house, cfg, pet):
    """A line for a hob that has not tried what is in the spotlight, when it is near it (the room or the next):
    "you haven't been out in the new yard yet"."""
    from . import outdoors
    from .world import neighbours
    if off(house) or not S(cfg).get("on"):
        return None
    room = pet["room"]
    for s in (house.get("spotlights") or {}).get("on", []):
        if pet["id"] in s["tried"] or not s.get("room"):
            continue
        if s["room"] == room or s["room"] in neighbours(house, room).values() or (s["key"] == "outdoors" and room == outdoors.gate_room(house)):
            return CURIOUS.get(s["key"], "you haven't tried %s yet" % s["what"])
    return None


CURIOUS = {"outdoors": "you haven't been out in the new yard yet", "kiln": "you haven't fired anything in the new kiln yet",
           "rod": "you haven't fished with a rod yet"}


def migrate(house, cfg):
    """On the deploy that brings spotlights (once): the newest things get their season. The kiln first (its want ranks
    high until it stands); then fishing with a rod. (The outdoors queues its own
    when the gate appears: outdoors.migrate.)"""
    if house.get("spotlights") is not None:
        house["spotlights"]["off"] = not S(cfg).get("on")
    if not S(cfg).get("on") or "migrated" in state(house):
        return
    from . import machines
    state(house)["migrated"] = house["tick"]
    shop = machines.standing(house, "kiln")
    queue(house, cfg, "kiln", "THE KILN", "the kiln", shop[0]["id"] if shop else _room_of(house, cfg, "kiln"), shop[1] if shop else None)
    from . import pond
    queue(house, cfg, "rod", "FISHING WITH A ROD", "fishing with a rod", (pond.room_of(house, cfg) or {}).get("id"))


def _room_of(house, cfg, key):
    """The room a machine not yet built would be built in."""
    P = cfg["build"]["project"][key]
    return next((r["id"] for r in house["rooms"].values() if r.get("type") in P["rooms"]), None)


def built(house, cfg, room, name, key):
    """A machine stands (machines.stood): if it is in the spotlight already (the kiln), it is the thing now; else it is
    something new."""
    for s in state(house)["on"] + state(house)["queue"]:
        if s["key"] == key:
            s["room"], s["thing"] = room["id"], name
            return
    queue(house, cfg, key, "THE %s" % key.upper(), "the %s" % key, room["id"], name)
