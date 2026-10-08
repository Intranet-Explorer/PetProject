"""Making things (SPEC-v2 §4). A recipe is a few shapes, a material, a name and a purpose. The engine checks
it, and decides what the thing really does from its material, size and surroundings (materials.toml).
The purpose is the pet's own idea and changes nothing."""
import re

from .world import dist, moment, tile_ok

SHAPES = ["circle", "square", "triangle", "blob", "bar", "dot", "ring", "star"]
COLORS = ["red", "orange", "yellow", "green", "teal", "blue", "purple", "pink", "brown", "white", "grey", "black"]
PLACES = ["center", "top", "bottom", "left", "right"]
MATERIALS = ["soft", "hard", "warm", "bright", "cool", "dark", "noisy", "quiet", "bouncy", "heavy", "sweet"]
STAGE = {   # stage -> (parts allowed, materials unlocked), §4 and §6
    "hatchling": (2, MATERIALS[:4]),
    "child": (4, MATERIALS[:10]),
    "youngling": (6, MATERIALS),
    "adult": (6, MATERIALS),
}
TAG_NEED = {"warm": "comfort", "cool": "comfort", "quiet": "energy", "noisy": "energy"}   # hidden effects that get tagged


def allowed(stage):
    return STAGE.get(stage, (0, []))


def own(w):
    return [n for n, o in w["objects"].items() if o.get("made", {}).get("by") == "pet"]


def material(w, cfg, name):
    return cfg["materials"][w["objects"][name]["made"]["recipe"]["material"]]


def close(w, cfg, key):
    """The made things within one tile of the pet whose material has the given property."""
    return [n for n, o in w["objects"].items()
            if "made" in o and dist(w["pet"]["pos"], o["pos"]) <= 1 and key in material(w, cfg, n)]


def clean_name(text):
    """A thing's name is how it is pointed at afterwards, so it is kept plain: letters, digits, spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w' -]", "", text.lower())).strip()[:24] if isinstance(text, str) else ""


def cost(recipe, cfg):
    return cfg["make"]["energy_base"] + cfg["make"]["energy_per_part"] * len(recipe["parts"])


def check_make(a, w, cfg):
    """None if the thing can be made, else why not."""
    r, (most, materials) = a.get("recipe"), allowed(w["pet"]["stage"])
    if not isinstance(r, dict) or not isinstance(r.get("parts"), list) or not r["parts"]:
        return "no recipe"
    if len(r["parts"]) > most:
        return "too many parts"
    for p in r["parts"]:
        if not (isinstance(p, dict) and p.get("shape") in SHAPES and p.get("size") in (1, 2, 3)
                and p.get("color") in COLORS and p.get("at", "center") in PLACES):
            return "bad part"
    if r.get("material") not in materials:
        return "unknown material" if r.get("material") not in MATERIALS else "material not unlocked"
    name = clean_name(r.get("name"))
    if not name or not isinstance(r.get("purpose"), str):
        return "no name" if not name else "no purpose"
    if name in w["objects"] or name == "visitor":
        return "there is already a " + name
    if not tile_ok(a.get("tile")):
        return "bad tile"
    if any(o["pos"] == a["tile"] for o in w["objects"].values()):
        return "that tile is taken"
    if len(own(w)) >= cfg["make"]["item_cap"]:
        return "there's no room for more"
    if w["pet"]["needs"]["energy"] < cost(r, cfg):
        return "not enough energy"
    return None


def make(w, a, cfg, mem, clean):
    r = a["recipe"]
    name = clean_name(r["name"])
    recipe = {"name": name, "material": r["material"], "purpose": clean(r["purpose"], 80),
              "parts": [{"shape": p["shape"], "size": p["size"], "color": p["color"], "at": p.get("at", "center")}
                        for p in r["parts"]]}
    w["objects"][name] = {"pos": list(a["tile"]), "made": {"recipe": recipe, "by": "pet", "tick": w["tick"]}}
    if cfg["materials"][r["material"]].get("light"):
        w["objects"][name]["state"] = "on"
    mem.thing_made(name, recipe, a["tile"], w["tick"])
    moment(w, "it made a " + name)
    return "you made " + name, {"energy": -float(cost(r, cfg))}, "make " + name


def unmake(w, a, cfg, mem, name):
    del w["objects"][name]
    mem.thing_gone(name, w["tick"], "taken apart")
    moment(w, "it took apart the " + name)
    return "you took apart " + name, {"energy": float(cfg["make"]["unmake_refund"])}, None


def use(w, cfg, mem, name):
    """What using a made thing does. Returns (what the pet is told, need effects, novelty key or None)."""
    o, m = w["objects"][name], material(w, cfg, name)
    fx = {n: v * (max(p["size"] for p in o["made"]["recipe"]["parts"]) / 2 if m.get("by_size") else 1)
          for n, v in m.get("use", {}).items()}
    if m.get("light"):
        o["state"] = "off" if o["state"] == "on" else "on"
        return "you switched %s %s" % (name, o["state"]), fx, "use " + name
    if m.get("food"):
        del w["objects"][name]
        w["prev_eat"], w["last_eat"] = w["last_eat"], w["tick"]
        mem.thing_gone(name, w["tick"], "eaten")
        moment(w, "it ate the " + name)
        return "you ate " + name, fx, "use " + name
    if not fx:
        return "you tried to use the %s; nothing happened" % name, fx, None
    return "you used " + name, fx, "use " + name


def nearby(w, cfg):
    """Standing effects of the things next to the pet: [(tag, need, rate per 10 s)]."""
    phase = w["clock"]["phase"]
    return [(material(w, cfg, n) and w["objects"][n]["made"]["recipe"]["material"], need, rate)
            for n in close(w, cfg, "near") for need, rate in material(w, cfg, n)["near"].get(phase, {}).items()]


def light_on(w, cfg):
    return any(o.get("state") == "on" and (n == "lamp" or ("made" in o and material(w, cfg, n).get("light")))
               for n, o in w["objects"].items())


def rest(w, cfg, energy):
    """Resting next to a noisy or a quiet thing: (energy per 10 s, tags)."""
    tags = []
    for n in close(w, cfg, "rest_near"):
        energy, tags = energy * material(w, cfg, n)["rest_near"], tags + ["noisy"]
    for n in close(w, cfg, "rest_bonus"):
        energy, tags = energy + material(w, cfg, n)["rest_bonus"], tags + ["quiet"]
    return energy, sorted(set(tags))
