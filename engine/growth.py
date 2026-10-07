"""Growth (SPEC-v2 §6). Stages are earned by what the pet has lived through.
`exploit` is the v1 measure of using a hidden rule on purpose, still counted for the Lab tab."""
from .actions import norm
from .world import dist, ticks

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
    return rule if was["needs"][NEED[rule]] < cfg["lab"]["exploit_need_below"] else None


def earned(w, cfg):
    """The stage the pet has earned, or None. V2.1 knows only hatching; the rest arrive with V2.3."""
    if w["pet"]["stage"] == "egg" and w["tick"] >= ticks(cfg, cfg["egg"]["egg_minutes"] * 60):
        return "hatchling"
    return None
