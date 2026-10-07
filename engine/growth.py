"""Growth (SPEC §10): stages are earned, and checked once per world day, when the pet wakes."""
from .actions import norm
from .world import dist

NEED = {"lamp_night": "comfort", "double_feed": "energy", "plant_window": "comfort"}


def plant_by_window(w):
    return dist(w["objects"]["plant"]["pos"], w["objects"]["window"]["pos"]) <= 2


def exploit(w, cfg, action, was):
    """The rule this (already applied) action took advantage of, if any. `was` is the room before it.
    Counts only when the related need was low, so stumbling into the right action by chance is not learning."""
    t, target = action.get("type"), norm(action.get("target"))
    if t == "use" and target == "lamp" and w["objects"]["lamp"]["state"] == "off" \
            and w["clock"]["phase"] in ("dusk", "night"):
        rule = "lamp_night"       # turned the lamp off for the night
    elif t == "use" and target == "bowl" and w["last_eat"] == w["tick"] and was["bowl"] == "half" \
            and w["tick"] - w["prev_eat"] >= cfg["ticks_per_hour"]:
        rule = "double_feed"      # left the second serving for at least a world hour
    elif t == "arrange" and norm(action.get("object")) == "plant" and not was["plant_by_window"] and plant_by_window(w):
        rule = "plant_window"     # brought the plant to the window
    else:
        return None
    return rule if was["needs"][NEED[rule]] < cfg["growth"]["exploit_need_below"] else None


def check(pet):
    """The morning check. Returns the stage the pet has earned, or None."""
    w, g = pet.world, pet.cfg["growth"]
    stage = w["pet"]["stage"]
    if stage == "egg" and w["clock"]["day"] > g["egg_days"]:
        return "hatchling"
    if stage == "hatchling":
        learned = len(pet.window) >= g["window"] and pet.accuracy() >= g["accuracy"]
        used = sum(n >= g["exploit_times"] for n in w["exploits"].values())
        if learned and used >= g["rules_exploited"]:
            return "child"
    return None
