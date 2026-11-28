"""What is left of designing (SPEC-v3.6d), which SPEC-v5.1 §4.5 deleted: the design thought, the judge, the plans,
the offer and the failed wants are gone, and `invent` (helper C) does through the plan or a react what a design did,
with the parser (engine/grammar.py) as the only gate. Kept: the house's designs as history (house["designs"]), the
kinds the working ones became (house["invented"]; `as_kind` is the catalog's view of them, from effects.toml), their
recipes in words, and the catalog's buying back of a thing that matters (`[design] on` is that switch now)."""
import tomllib

from . import craft, invent, things
from .world import free_tile, hours, label, moment

SKILL = ["", "you are getting the hang of designing things", "your designs come out the way you meant", "what you design works, and works well"]
CARRIED = ("handle", "strap", "pole", "stick")   # a light with one of these to carry it by goes where its owner goes
D = {}   # effects.toml, as loaded (the same for every config: as_kind reads it without one)


def load(cfg, directory):
    """effects.toml (what the old designs' effects do), laid in beside config.toml's [design] switch; designing stays
    a skill, as hobs have practised it."""
    T = tomllib.loads((directory / "effects.toml").read_text())
    D.clear()
    D.update(T)
    cfg["design"] = dict(T, on=cfg.get("design", {}).get("on", False))
    craft.SKILLS.setdefault("designing", SKILL)
    return cfg


def on(cfg):
    """[design] on: the catalog buys back a thing that matters (designing itself is gone)."""
    return bool(cfg.get("design", {}).get("on"))


def uses(rec):
    """The uses (uses.json) of what works in it: a light with something to carry it by is a carried light."""
    carried = any(p["part"] in CARRIED for p in rec["design_parts"])
    return ["carried light" if e == "light" and carried else D["effect"][e]["use"] for e in rec["works"]]


def as_kind(cfg, rec):
    """A designed kind as the catalog would have it (invent.as_kind asks): what works in it does what its use does;
    it is of the stuff it is built on."""
    E = {}
    for u in uses(rec):
        E = invent.plus(E, invent.USES[u]["effect"])
    nature = (cfg["house"]["bits"].get(rec["design_parts"][0]["material"], {}).get("can") or ["hard"])[0]
    main = uses(rec)[0] if rec["works"] else None
    return {"invented": True, "design": True, "a": rec["a"], "everyday": invent.USES[main]["everyday"] if main else rec["name"], "not": [], "rank": 2,
            "wall": False, "hangs": False, "store": E.get("store", 0), "inside": bool(E.get("inside")), "furniture": rec["size"] == "large", "from": None,
            "base": rec["parts"][0]["part"], "signature": next((p["part"] for p in rec["parts"][:0:-1]), None), "prop": invent.plus(dict(cfg["materials"][nature]), E.get("prop", {})),
            "effect": E, "design_parts": rec["design_parts"], **({"counts": E["tool"]} if E.get("tool") else {}), **({"plantable": True} if E.get("plantable") else {})}


def install(house, cfg):
    """The kinds the house's failed designs were (its working ones are in house["invented"]: invent.install)."""
    for rec in house.get("design_kinds", {}).values():
        cfg["kinds"].setdefault(rec["name"], as_kind(cfg, rec))


def words(cfg, kind):
    """The recipe in plain words (craft.words, by way of invent.words)."""
    K = cfg["kinds"][kind]
    return "%s %s can be made of %s" % (K["a"], kind, ", ".join("%s (%s)" % (p["part"], p["material"]) for p in K["design_parts"]))



def shown(house, cfg, o):
    """A working effect shows in its room a while (o.effect_on: the view draws a light cone, a glow, water ...)."""
    d = o.get("made", {}).get("design")
    works = [e for e, r in (d or {}).get("effects", {}).items() if r["works"]]
    if works:
        o["effect_on"] = {"effect": D["effect"][works[0]]["show"], "until": house["tick"] + hours(cfg, D["tune"]["show_minutes"] / 60)}



# ---- the catalog (§7): buying back what matters, and finding its recipe again ----

def matters(house, cfg, g):
    """A thing gone that may be bought back: an invention, a design, a first, an heirloom, a titled or starred thing."""
    from . import order
    k = cfg["kinds"].get(g["recipe"].get("kind"), {})
    return bool(k.get("invented") or g.get("design") or g["recipe"].get("title") or g.get("star") is not None or g.get("heirloom") or (g["by"], g["made"]) in order.firsts_of(house))


def buy_back(house, cfg, cmd):
    """The visitor's "buy back" in the catalog (actions.visit: {"type": "buy_back", "id": the thing's id}): once
    each, for `cost` of the machine's materials (the most plentiful first); it comes back beside the machine. Returns
    an error string, or None."""
    from . import machine
    if not on(cfg):
        return "buying back is switched off"
    g = next((g for g in reversed(house.get("gone_things", [])) if g.get("id") == cmd.get("id")), None)
    room = machine.found(house)
    if not g:
        return "there is no such thing in the catalog"
    if not matters(house, cfg, g):
        return "only a thing that matters can be bought back: an invention, a design, a first, an heirloom, or a thing with a title"
    if g.get("bought"):
        return "it has been bought back once already"
    if not room:
        return "nobody has found the machine yet"
    S, n = machine.state(house, cfg)["stock"], D["tune"]["cost"]
    if sum(S.values()) < n:
        return "the machine has not enough in it: it takes %d of its materials" % n
    paid = []
    for _ in range(n):
        m = max(sorted(S), key=lambda x: S[x])
        S[m] -= 1
        paid.append(m)
    g["bought"] = house["tick"]
    owner = g["owner"] if house["pets"].get(g["owner"] or "", {}).get("stage") not in (None, "dead") else None
    name = things.unique_name(house, cfg, g["name"])
    made = {k: g[k] for k in ("id", "recipe", "by", "uses", "ups", "bits", "how", "made_in", "users", "words", "design", "parts", "star") if k in g}
    room["objects"][name] = {"pos": free_tile(house, cfg, room, [6, 4]), "made": dict(made, owner=owner, tick=g["made"], used_at=house["tick"], heirloom=None, behavior=None, bought_back=house["tick"])}
    machine.state(house, cfg)["used"] = house["tick"]
    moment(house, "bought back", "the visitor bought back the %s from the catalog, for %s from the machine" % (name, ", ".join(paid)), None, room["id"])
    return None


def unmade(house, cfg, pet, o):
    """things.unmake: a bought-back thing of a kind with a recipe, taken apart, teaches how it is made."""
    kind = o["made"]["recipe"].get("kind")
    if not o["made"].get("bought_back") or kind not in house.get("invented", {}) or "kind:" + kind in pet.get("recipes", {}):
        return ""
    craft.learn(house, cfg, pet, "kind:" + kind, "taken apart")
    house.setdefault("recipes", {}).setdefault("kind:" + kind, {"by": pet["id"], "tick": house["tick"]}).pop("lost", None)
    moment(house, "rediscovered", "%s rediscovered how to make the %s" % (label(pet), kind), pet["id"], pet["room"])
    return "; taking it apart, you saw how the %s is made" % kind
