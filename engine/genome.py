"""Genome and body (SPEC §11, SPEC-v3.5 §2). The pet never draws: the genome is numbers and part names, the view turns
them into a sprite. A body is settled at birth (genes.py); the engine adds permanent marks from events, and describes
it in words for the mirror. The slots, their values and the words for them are data (view/assets/bodies.json)."""
import json
from pathlib import Path

BODIES = json.loads((Path(__file__).parent.parent / "view" / "assets" / "bodies.json").read_text())
SLOTS, PLANS, PATTERNS, WORDS = BODIES["slots"], BODIES["plans"], BODIES["patterns"], BODIES["words"]
OLD_PATTERNS = {"speckle": "spots", "stripe": "stripes"}   # what a pattern was called before v3.5
START = {"roundness": 0.72, "stretch": 1.05, "wobble": 0.2, "hue": 31, "saturation": 0.6, "pattern": "spots",
         "pattern_density": 0.3, "eye_size": 0.5, "eye_spacing": 0.4, "plan": PLANS[0], "size": 1.0,
         **{slot: values[0] for slot, values in SLOTS.items()}, "marks": []}
RANGES = {"roundness": (0.2, 1.0), "stretch": (0.75, 1.4), "wobble": (0.0, 1.0), "saturation": (0.2, 1.0),
          "pattern_density": (0.0, 1.0), "eye_size": (0.2, 1.0), "eye_spacing": (0.15, 0.9), "size": (0.8, 1.2)}
COLOURS = [(15, "red"), (45, "orange"), (70, "yellow"), (160, "green"), (200, "teal"), (260, "blue"),
           (300, "purple"), (345, "pink"), (361, "red")]


def colour(hue):
    return next(name for upto, name in COLOURS if hue < upto)


def get(g, key):
    """A gene's value. A body from before v3.5 has no slots: a missing one is its first value (plan blob, size 1)."""
    return OLD_PATTERNS.get(g.get(key), g.get(key, START[key])) if key == "pattern" else g.get(key, START[key])


def parts(g, slots=("ears", "tail", "head", "whiskers", "feet", "mouth", "fur", "shade")):
    """Its parts worth a word, as a pet would be told them: ["long ears", "a fluffy tail"]. A plain value has none."""
    return [WORDS[s][get(g, s)] for s in slots if get(g, s) in WORDS.get(s, {})]


def join(words):
    return ", ".join(words[:-1]) + (" and " if len(words) > 1 else "") + words[-1] if words else ""


def describe(g):
    """Plain-language description of the body. Looking in the mirror is the only way the pet sees itself."""
    level = lambda k, low, mid, high: low if g[k] < 0.4 else high if g[k] > 0.7 else mid
    size = "small, " if get(g, "size") <= 0.9 else "big, " if get(g, "size") >= 1.1 else ""
    text = "%s%s and %s, %s %s, %s, with %s eyes set %s" % (
        size, level("roundness", "angular", "rounded", "very round"),
        "squat" if g["stretch"] < 0.95 else "tall" if g["stretch"] > 1.15 else "about as tall as wide",
        level("saturation", "pale", "soft", "vivid"), colour(g["hue"]),
        "unpatterned" if get(g, "pattern") == "plain" else "%s pattern of %s" % (level("pattern_density", "a sparse", "a", "a dense"), get(g, "pattern")),
        level("eye_size", "small", "medium", "big"), level("eye_spacing", "close together", "evenly", "wide apart"))
    has = parts(g, ("plan",)) + parts(g)
    return text + (", and " + join(has) if has else ", and no ears or tail to speak of") + "".join("; it has %s" % m for m in g["marks"])


def update_marks(house, cfg, pet):
    """Permanent marks from what has happened to it. Never removed. Returns a new mark, if one appeared."""
    g, room = pet["genome"], house["rooms"][pet["room"]]
    window = next((o for o in room["objects"].values() if o.get("fix", {}).get("window")), None)
    if window:
        pet["near_window"] += cfg["dt"] * (max(abs(pet["pos"][0] - window["pos"][0]), abs(pet["pos"][1] - window["pos"][1])) <= 2)
    for mark, earned in (("a small notch", pet["needs"]["comfort"] <= 0),                # comfort hit 0
                         ("a faded patch", pet["near_window"] * 10 >= cfg["marks"]["window_patch_seconds"])):
        if earned and mark not in g["marks"]:
            g["marks"].append(mark)
            return mark
    return None
