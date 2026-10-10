"""Genome and body (SPEC §11). The pet never draws: the genome is numbers, the view turns them into a sprite.
The engine mutates it each sleep, adds permanent marks from events, and describes it in words for the mirror."""
START = {"roundness": 0.72, "stretch": 1.05, "wobble": 0.2, "hue": 31, "saturation": 0.6, "pattern": "speckle",
         "pattern_density": 0.3, "eye_size": 0.5, "eye_spacing": 0.4, "limbs": 0, "marks": []}
RANGES = {"roundness": (0.2, 1.0), "stretch": (0.75, 1.4), "wobble": (0.0, 1.0), "saturation": (0.2, 1.0),
          "pattern_density": (0.0, 1.0), "eye_size": (0.2, 1.0), "eye_spacing": (0.15, 0.9)}
PATTERNS = ["plain", "speckle", "stripe", "patch"]
COLOURS = [(15, "red"), (45, "orange"), (70, "yellow"), (160, "green"), (200, "teal"), (260, "blue"),
           (300, "purple"), (345, "pink"), (361, "red")]
# parameter -> (word when it goes up, word when it goes down)
WORDS = {"roundness": ("rounder", "more angular"), "stretch": ("taller", "squatter"), "wobble": ("wobblier", "steadier"),
         "saturation": ("more vivid", "paler"), "pattern_density": ("a denser pattern", "a sparser pattern"),
         "eye_size": ("bigger eyes", "smaller eyes"), "eye_spacing": ("eyes further apart", "eyes closer together"),
         "limbs": ("one more limb", "one fewer limb")}


def colour(hue):
    return next(name for upto, name in COLOURS if hue < upto)


def mutations(g, rng, stage):
    """Three different nudges of 2-3 parameters each. Limbs only once it is a child."""
    keys = list(RANGES) + ["hue", "pattern"] + (["limbs"] if stage in ("child", "youngling", "adult", "elder") else [])
    out = []
    while len(out) < 3:
        m = dict(g, marks=list(g["marks"]))
        for k in rng.sample(keys, rng.choice([2, 3])):
            if k == "pattern":
                m[k] = rng.choice([p for p in PATTERNS if p != g[k]])
            elif k == "limbs":
                m[k] = g[k] + (1 if g[k] == 0 else -1 if g[k] == 4 else rng.choice([-1, 1]))
            elif k == "hue":
                m[k] = round(g[k] + rng.choice([-1, 1]) * rng.uniform(20, 45)) % 360
            else:
                lo, hi = RANGES[k]
                m[k] = round(min(hi, max(lo, g[k] + rng.choice([-1, 1]) * rng.uniform(0.1, 0.22) * (hi - lo))), 2)
        if m != g and m not in out:
            out.append(m)
    return out


def describe_change(old, new):
    """A mutation in a few words, which is all the pet sees of it."""
    parts = []
    for k, (up, down) in WORDS.items():
        if new[k] != old[k]:
            parts.append(up if new[k] > old[k] else down)
    if new["hue"] != old["hue"]:
        parts.append("a shift toward " + colour(new["hue"]) if colour(new["hue"]) != colour(old["hue"])
                     else "a slightly different " + colour(new["hue"]))
    if new["pattern"] != old["pattern"]:
        parts.append("a %s pattern" % new["pattern"] if new["pattern"] != "plain" else "no pattern")
    return ", ".join(parts)


def describe(g):
    """Plain-language description of the body. Looking in the mirror is the only way the pet sees itself."""
    level = lambda k, low, mid, high: low if g[k] < 0.4 else high if g[k] > 0.7 else mid
    limbs = "no limbs" if not g["limbs"] else "%s limb%s" % (["no", "one", "two", "three", "four"][min(g["limbs"], 4)], "s" * (g["limbs"] > 1))
    text = "%s and %s, %s %s, %s, with %s eyes set %s, and %s" % (
        level("roundness", "angular", "rounded", "very round"),
        "squat" if g["stretch"] < 0.95 else "tall" if g["stretch"] > 1.15 else "about as tall as wide",
        level("saturation", "pale", "soft", "vivid"), colour(g["hue"]),
        "unpatterned" if g["pattern"] == "plain" else "%s %s pattern" % (
            level("pattern_density", "a sparse", "a", "a dense"), g["pattern"]),
        level("eye_size", "small", "medium", "big"), level("eye_spacing", "close together", "evenly", "wide apart"), limbs)
    return text + "".join("; it has %s" % m for m in g["marks"])


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


def child_of(g, rng, jump=0.4):
    """A child's body (SPEC-v3 §5.4): the parent's with one round of the nightly mutation, and now and then one
    bigger jump: a new pattern, a limb, or a hue more than 45 degrees away. Marks are earned, not inherited."""
    child = mutations(dict(g, marks=[]), rng, "child")[0]
    if rng.random() < jump:
        kind = rng.choice(["pattern", "limbs", "hue"])
        if kind == "pattern":
            child["pattern"] = rng.choice([p for p in PATTERNS if p != child["pattern"]])
        elif kind == "limbs":
            child["limbs"] = max(0, min(4, child["limbs"] + rng.choice([-1, 1, 1])))
        else:
            child["hue"] = round(child["hue"] + rng.choice([-1, 1]) * rng.uniform(50, 120)) % 360
    return child
