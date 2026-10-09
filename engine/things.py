"""Making things (SPEC-v2 §4). A recipe is a few shapes, a material, a name and a purpose. The engine checks
it, and decides what the thing really does from its material, size and surroundings (materials.toml).
The purpose is the pet's own idea and changes nothing."""
import re

from .world import H, W, dist, moment, tile_ok

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
TAG_NEED = {"warm": "comfort", "cool": "comfort", "quiet": "energy", "noisy": "energy",   # hidden effects that get tagged
            "hum": "curiosity", "bounce": "curiosity"}
WHEN = ["day", "night", "dusk", "visitor", "touched", "alone", "pet_resting"]
DO = ["glow", "dim", "hum", "bounce", "move_toward_pet", "move_away"] + ["change_color:" + c for c in COLORS]


def allowed(stage):
    return STAGE.get(stage, (0, []))


def own(w):
    return [n for n, o in w["objects"].items() if o.get("made", {}).get("by") == "pet"]


def movable(w, cfg):
    """What can be arranged: the loose starting objects and any made thing that is not heavy."""
    return ["plant", "ball", "blanket", "rock"] + [n for n, o in w["objects"].items()
                                                  if "made" in o and not material(w, cfg, n).get("fixed")]


def material(w, cfg, name):
    return cfg["materials"][w["objects"][name]["made"]["recipe"]["material"]]


def doing(w, cfg, name):
    """What a taught thing is doing right now (§7): the properties of its behavior while its "when" holds, else {}."""
    o = w["objects"][name]
    return cfg["materials"]["behaviors"][o["made"]["behavior"]["do"].split(":")[0]] if o.get("active") else {}


def close(w, cfg, key):
    """The made things within one tile of the pet that have the given property, from their material or from
    what they have been taught to do."""
    return [n for n, o in w["objects"].items() if "made" in o and dist(w["pet"]["pos"], o["pos"]) <= 1
            and (key in material(w, cfg, n) or key in doing(w, cfg, n))]


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
    if len(own(w)) >= cfg["make"]["item_cap"]:
        return "there's no room for more"
    if w["pet"]["needs"]["energy"] < cost(r, cfg):
        return "not enough energy"
    return None


def free_tile(w, tile):
    """The tile asked for if nothing is on it, else the nearest one that is free. The V2.3 life lost two of
    its first three makes to a taken tile; putting the thing down beside what is there loses nothing."""
    taken = [o["pos"] for o in w["objects"].values()]
    return min(([x, y] for x in range(W) for y in range(H) if [x, y] not in taken), key=lambda t: dist(t, tile))


def make(w, a, cfg, mem, clean):
    r, a = a["recipe"], dict(a, tile=free_tile(w, a["tile"]))
    name = clean_name(r["name"])
    recipe = {"name": name, "material": r["material"], "purpose": clean(r["purpose"], 80),
              "parts": [{"shape": p["shape"], "size": p["size"], "color": p["color"], "at": p.get("at", "center")}
                        for p in r["parts"]]}
    w["objects"][name] = {"pos": list(a["tile"]), "made": {"recipe": recipe, "by": "pet", "tick": w["tick"]}}
    if cfg["materials"][r["material"]].get("light"):
        w["objects"][name]["state"] = "on"
    mem.thing_made(name, recipe, a["tile"], w["tick"])
    moment(w, "it made a " + name)
    # Novelty goes by kind: another thing of a material it has made before is less new than a first of its kind.
    return "you made %s at (%d,%d)" % (name, *a["tile"]), {"energy": -float(cost(r, cfg))}, "make " + r["material"]


def check_combine(a, w, cfg, norm):
    x, y, r = norm(a.get("a")), norm(a.get("b")), a.get("recipe")
    if x not in own(w) or y not in own(w) or x == y:
        return "you can only combine two different things of your own"
    if not isinstance(r, dict) or not isinstance(r.get("purpose"), str):
        return "no recipe"
    if r.get("material") not in {w["objects"][n]["made"]["recipe"]["material"] for n in (x, y)}:
        return "the material must be one of theirs"
    name = clean_name(r.get("name"))
    if not name:
        return "no name"
    if name not in (x, y) and (name in w["objects"] or name == "visitor"):
        return "there is already a " + name
    if w["pet"]["needs"]["energy"] < cfg["make"]["energy_base"]:
        return "not enough energy"
    return None


def combine(w, a, cfg, mem, clean, norm):
    """§6: two of its things become one, with the parts of both (up to 6) and the material of either."""
    x, y, r = norm(a["a"]), norm(a["b"]), a["recipe"]
    parts = [dict(p) for n in (x, y) for p in w["objects"][n]["made"]["recipe"]["parts"]][:6]
    recipe = {"name": clean_name(r["name"]), "material": r["material"], "purpose": clean(r["purpose"], 80), "parts": parts}
    pos = w["objects"][x]["pos"]
    for n in (x, y):
        del w["objects"][n]
        mem.thing_gone(n, w["tick"], "combined")
    w["objects"][recipe["name"]] = {"pos": pos, "made": {"recipe": recipe, "by": "pet", "tick": w["tick"], "from": [x, y]}}
    if cfg["materials"][r["material"]].get("light"):
        w["objects"][recipe["name"]]["state"] = "on"
    mem.thing_made(recipe["name"], recipe, pos, w["tick"])
    moment(w, "it combined the %s and the %s into a %s" % (x, y, recipe["name"]))
    return "you combined %s and %s into %s" % (x, y, recipe["name"]), {"energy": -float(cfg["make"]["energy_base"])}, "combine " + r["material"]


def give(w, msg, cfg, mem):
    """A thing dropped in by the visitor (§9): one shape, the visitor's choice of material. It is not the pet's."""
    part = {"shape": msg.get("shape"), "size": 2, "color": msg.get("color"), "at": "center"}
    if not (part["shape"] in SHAPES and part["color"] in COLORS and msg.get("material") in MATERIALS and tile_ok(msg.get("tile"))):
        return None
    if any(o["pos"] == msg["tile"] for o in w["objects"].values()):
        return None
    w["gifts"] += 1
    name = "gift %d" % w["gifts"]
    recipe = {"name": name, "material": msg["material"], "purpose": "a gift from the visitor", "parts": [part]}
    w["objects"][name] = {"pos": list(msg["tile"]), "made": {"recipe": recipe, "by": "visitor", "tick": w["tick"]}}
    if cfg["materials"][msg["material"]].get("light"):
        w["objects"][name]["state"] = "on"
    if mem:
        mem.thing_made(name, recipe, msg["tile"], w["tick"], by="visitor")
    moment(w, "you gave it a " + name)
    return "visitor left %s at (%d,%d)" % (name, *msg["tile"])


def check_teach(a, w, cfg, norm):
    name, b = norm(a.get("target")), a.get("behavior")
    if name not in own(w):
        return "you can only teach your own things"
    if not isinstance(b, dict) or b.get("when") not in WHEN or b.get("do") not in DO:
        return "unknown behavior"
    taught = [n for n in own(w) if "behavior" in w["objects"][n]["made"]]
    if name not in taught and len(taught) >= cfg["growth"]["taught_max"]:
        return "you can only teach %d things" % cfg["growth"]["taught_max"]
    return None


def teach(w, a, mem, name):
    b = {"when": a["behavior"]["when"], "do": a["behavior"]["do"]}
    w["objects"][name]["made"]["behavior"] = b
    mem.thing(name)["behavior"] = b
    mem.save_things()
    moment(w, "it taught the %s to %s when %s" % (name, b["do"].replace("_", " ").replace(":", " to "), b["when"].replace("_", " ")))
    return "you taught %s: when %s, %s" % (name, b["when"], b["do"]), {}, "teach " + name


def behave(w, cfg, tick_seconds):
    """Run every taught thing for one tick (§7): decide whether its "when" holds, and move the ones that move."""
    pet, plan = w["pet"], w["plan"]
    resting = bool(w["sleep"]) or bool(plan and plan["left"] is not None and plan["steps"][plan["i"]].get("type") == "rest")
    for n, o in w["objects"].items():
        b = o.get("made", {}).get("behavior")
        if not b:
            continue
        o["active"] = {
            "day": w["clock"]["phase"] == "day", "night": w["clock"]["phase"] == "night", "dusk": w["clock"]["phase"] == "dusk",
            "visitor": (w["tick"] - w["visitor_last"]) * tick_seconds <= 60,
            "touched": (w["tick"] - o["made"].get("touched", -10**6)) * tick_seconds <= 20,
            "alone": dist(pet["pos"], o["pos"]) > 3, "pet_resting": resting,
        }[b["when"]]
        step = doing(w, cfg, n).get("step")
        if step and w["tick"] % 2 == 0 and (dist(pet["pos"], o["pos"]) > 1 if step > 0 else True):
            taken = [x["pos"] for x in w["objects"].values()] + [pet["pos"]]
            options = [[o["pos"][0] + dx, o["pos"][1] + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
            options = [t for t in options if tile_ok(t) and t not in taken]
            best = (min if step > 0 else max)(options, key=lambda t: dist(t, pet["pos"]), default=None)
            if best and (dist(best, pet["pos"]) - dist(o["pos"], pet["pos"])) * step < 0:
                o["pos"] = best


def unmake(w, a, cfg, mem, name):
    del w["objects"][name]
    mem.thing_gone(name, w["tick"], "taken apart")
    moment(w, "it took apart the " + name)
    return "you took apart " + name, {"energy": float(cfg["make"]["unmake_refund"])}, None


def use(w, cfg, mem, name):
    """What using a made thing does. Returns (what the pet is told, need effects, novelty key or None)."""
    o, m = w["objects"][name], material(w, cfg, name)
    kind = "use a %s thing" % o["made"]["recipe"]["material"]   # novelty is shared by everything of the same material
    o["made"]["touched"] = w["tick"]   # for things taught to do something "when touched"
    fx = {n: v * (max(p["size"] for p in o["made"]["recipe"]["parts"]) / 2 if m.get("by_size") else 1)
          for n, v in m.get("use", {}).items()}
    if m.get("light"):
        o["state"] = "off" if o["state"] == "on" else "on"
        return "you switched %s %s" % (name, o["state"]), fx, kind
    if m.get("food"):
        del w["objects"][name]
        w["prev_eat"], w["last_eat"] = w["last_eat"], w["tick"]
        mem.thing_gone(name, w["tick"], "eaten")
        moment(w, "it ate the " + name)
        return "you ate " + name, fx, kind
    if not fx:
        return "you tried to use the %s; nothing happened" % name, fx, None
    return "you used " + name, fx, kind


def nearby(w, cfg):
    """Standing effects of the things next to the pet: [(material, need, rate per 10 s, the thing's name)]."""
    phase, felt = w["clock"]["phase"], []
    for n in close(w, cfg, "near"):
        o = w["objects"][n]
        felt += [(o["made"]["recipe"]["material"], need, rate, n) for need, rate in material(w, cfg, n).get("near", {}).get(phase, {}).items()]
        felt += [(o["made"]["behavior"]["do"], need, rate, n) for need, rate in doing(w, cfg, n).get("near", {}).items()]
    return felt


def senses(w, cfg, fired):
    """What the pet can feel at this moment, from the hidden rules holding now (`fired`) and the things beside it.
    A sensation names its source and whether it is pleasant, never the rule: that warm things turn on it by
    day, or that the harsh light is only harsh at night, it still has to work out by living through both."""
    felt = []
    if "lights_night" in fired:
        felt.append("the light in the room is harsh on you")
    if "plant_window" in fired:
        felt.append("the air in the room feels fresh")
    if w["clock"]["phase"] == "night" and light_on(w, cfg):
        felt += ["the %s beside you keeps the light off you" % n for n in close(w, cfg, "shade")]
    for _, need, rate, n in nearby(w, cfg):
        felt.append("the %s beside you feels %s" % (n, "pleasant" if rate > 0 else "unpleasant"))
    if w["pet"]["needs"]["curiosity"] < 30:
        felt.append("you are restless for something new")
    return "; ".join(dict.fromkeys(felt)) or "nothing in particular"


def useful(t, cfg):
    """§6: it made it, and on most of at least `useful_uses` occasions the thing raised the need it is for."""
    need = cfg["materials"][t["recipe"]["material"]].get("need")
    return bool(need) and t["by"] == "pet" and t["uses"] >= cfg["growth"]["useful_uses"] and t.get("ups", 0) * 2 > t["uses"]


def light_on(w, cfg):
    return any((o.get("state") == "on" and (n == "lamp" or ("made" in o and material(w, cfg, n).get("light"))))
               or ("made" in o and doing(w, cfg, n).get("light")) for n, o in w["objects"].items())


def rest(w, cfg, energy):
    """Resting next to a noisy or a quiet thing: (energy per 10 s, tags, {thing: what it added per 10 s})."""
    tags, share = [], {}
    for n in close(w, cfg, "rest_near"):
        by = material(w, cfg, n).get("rest_near") or doing(w, cfg, n)["rest_near"]
        share[n], energy, tags = energy * (by - 1), energy * by, tags + ["noisy" if "rest_near" in material(w, cfg, n) else "hum"]
    for n in close(w, cfg, "rest_bonus"):
        share[n], energy, tags = material(w, cfg, n)["rest_bonus"], energy + material(w, cfg, n)["rest_bonus"], tags + ["quiet"]
    return energy, sorted(set(tags)), share
