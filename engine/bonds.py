"""SPEC-v4.0 §6.3 bonds: friends, close bonds, rivals, enemies; two-parent eggs. Part of [opinions].

house["bonds"] = [{"a", "b", "kind": "close", "since"}]: close bonds, formed and broken by `form` and `break_` (talk.py's
"stay with me", and the rules in `tick`). Friends, rivals and enemies are read off the opinions (`kind`)."""
from .world import alive, label, moment
from . import character, contracts, memories, opinions

B = opinions.DATA["bonds"]


def pid(x):
    return x if isinstance(x, str) else x["id"]


def close(house, a):
    """The id of `a`'s close bond, or None."""
    a = pid(a)
    return next((b["b"] if b["a"] == a else b["a"] for b in house.get("bonds", []) if a in (b["a"], b["b"])), None)


def kind(house, a, b):
    """"close", "enemy", "friend", "rival" or None, between two hobs."""
    a, b = house["pets"].get(pid(a)), house["pets"].get(pid(b))
    if not a or not b or a is b:
        return None
    if close(house, a) == b["id"]:
        return "close"
    ab, ba = opinions.of(a, b["id"])["liking"], opinions.of(b, a["id"])["liking"]
    if min(ab, ba) < B["enemy"]:
        return "enemy"
    if min(ab, ba) > B["friend"]:
        return "friend"
    if rivals(a, b):
        return "rival"
    return None


def rivals(a, b):
    """Both ambitious, chasing the same thing: the same ambition, or the best at the same skill."""
    if min(character.trait(a, "ambitious"), character.trait(b, "ambitious")) < B["rival"]:
        return False
    same = lambda k: k(a) is not None and k(a) == k(b)
    return same(lambda p: (p.get("ambition") or {}).get("key") if not (p.get("ambition") or {}).get("done") else None) \
        or same(lambda p: ((p.get("bests") or {}).get("skill") or {}).get("name"))


def form(house, cfg, a, b, why):
    """A close bond. Each hob has one at most, and never with its kin (19 October 2026: talk bonded parent and child, who
    then laid two-parent eggs; kin are friends). True if formed."""
    a, b = house["pets"][pid(a)], house["pets"][pid(b)]
    if not opinions.on(cfg) or a is b or close(house, a) or close(house, b) or "dead" in (a["stage"], b["stage"]) or opinions.kin(house, a, b):
        return False
    house.setdefault("bonds", []).append({"a": a["id"], "b": b["id"], "kind": "close", "since": house["tick"]})
    for p, q in ((a, b), (b, a)):
        memories.add(house, cfg, p, "%s and I became close: %s" % (label(q), why), 5, [q["id"]], "bond")
        character.set_mood(house, cfg, p, "happy", "close to %s" % label(q))
    moment(house, "bond", "%s and %s have become close" % (label(a), label(b)), a["id"], a["room"])
    rose(house, cfg, a, b, "close")
    return True


LEVELS = ("enemy", None, "rival", "friend", "close")


def rose(house, cfg, a, b, level):
    """SPEC-v5.3 §6 (helper A): a bond's level rose, for any cause (contracts.event53 "bond"), with [projects] on."""
    if contracts.on53(cfg, "projects"):
        contracts.event53(house, "bond", a=pid(a), b=pid(b), level=level)


def risen(house, cfg):
    """(Hourly.) Each pair's level, against the last seen: a rise to friend recorded (close is form's)."""
    if not contracts.on53(cfg, "projects"):
        return
    seen = house.setdefault("v5", {}).setdefault("bond_seen", {})
    pets = sorted((p for p in alive(house) if p["stage"] not in ("egg",)), key=lambda p: p["id"])
    for i, a in enumerate(pets):
        for b in pets[i + 1:]:
            k, now = "%s|%s" % (a["id"], b["id"]), kind(house, a, b)
            if k in seen and LEVELS.index(now) > LEVELS.index(seen[k]) and now == "friend":
                rose(house, cfg, a, b, now)
            seen[k] = now


def break_(house, cfg, a, b, why):
    """The close bond between them ends. True if there was one."""
    a, b = pid(a), pid(b)
    bond = next((x for x in house.get("bonds", []) if {x["a"], x["b"]} == {a, b}), None)
    if not bond:
        return False
    house["bonds"].remove(bond)
    pa, pb = house["pets"].get(a), house["pets"].get(b)
    for p, q in ((pa, pb), (pb, pa)):
        if p and q and p["stage"] != "dead":
            memories.add(house, cfg, p, "%s and I are not close any more: %s" % (label(q), why), 4, [q["id"]], "bond")
            character.set_mood(house, cfg, p, "sad", why)
    if pa and pb and "dead" not in (pa["stage"], pb["stage"]):
        moment(house, "bond broken", "%s and %s are not close any more" % (label(pa), label(pb)), a, pa["room"])
    return True


def qualifies(house, a, b):
    if a["stage"] not in ("adult", "elder") or b["stage"] not in ("adult", "elder") or opinions.kin(house, a, b):
        return False
    oa, ob = opinions.of(a, b["id"]), opinions.of(b, a["id"])
    return min(oa["liking"], ob["liking"]) > B["close_liking"] and min(oa["trust"], ob["trust"]) >= B["close_trust"] \
        and min(len(oa["causes"]), len(ob["causes"])) >= B["close_causes"]


def tick(house, cfg):
    """(Hourly, from opinions.tick.) Close bonds break with a death or a fall in liking, and form by themselves between
    the closest pairs (talk.py forms them sooner, in a conversation)."""
    for x in list(house.get("bonds", [])):
        a, b = house["pets"].get(x["a"]), house["pets"].get(x["b"])
        if not a or not b or "dead" in (a["stage"], b["stage"]):
            break_(house, cfg, x["a"], x["b"], "%s died" % label(b if b and b["stage"] == "dead" else a) if a and b else "gone")
        elif min(opinions.of(a, b["id"])["liking"], opinions.of(b, a["id"])["liking"]) < B["break_liking"]:
            break_(house, cfg, a, b, "the warmth between us went")
    risen(house, cfg)
    pets = [p for p in alive(house) if p["stage"] in ("adult", "elder") and not close(house, p)]
    for i, a in enumerate(pets):
        for b in pets[i + 1:]:
            if qualifies(house, a, b) and not close(house, a) and not close(house, b):
                form(house, cfg, a, b, "we have been through so much together")


# ---- two-parent eggs ----

def parents(house, cfg, pet):
    """The other parent of an egg this hob lays now (its close bond, alive and grown), or None."""
    if not opinions.on(cfg):
        return None
    other = house["pets"].get(close(house, pet) or "")
    return other if other and other["stage"] in ("adult", "elder") and not opinions.kin(house, pet, other) else None   # (a bond made before kin were refused)


def blend(g1, g2, rng):
    """A body from two: each gene of it taken from one parent or the other (genes.child then nudges it as for one)."""
    return dict({k: (g1 if rng.random() < 0.5 else g2).get(k, g1.get(k)) for k in g1 if k != "marks"}, marks=[])
