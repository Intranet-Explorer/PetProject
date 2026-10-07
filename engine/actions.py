"""The action set (SPEC §6): validation and application. The only way a pet changes the world.
Visitor actions live here too; they arrive as data and are validated the same way."""
import re

from . import genome
from .world import H, W, add_event, near, tile_ok

HATCHLING = ["observe", "look", "move", "speak", "rest", "use", "write_belief", "revise_belief"]
STAGE_ACTIONS = {
    "egg": ["observe"],
    "hatchling": HATCHLING,
    "child": HATCHLING[:6] + ["arrange"] + HATCHLING[6:],
}
ALL_ACTIONS = STAGE_ACTIONS["child"]
USABLE = ("lamp", "music box", "bowl", "blanket", "bed")
MOVABLE = ("plant", "ball", "blanket", "rock")              # what the pet may arrange
PLACEABLE = MOVABLE + ("lamp", "bowl", "music box")         # what the visitor may place
TOGGLE = {"on": "off", "off": "on", "playing": "silent", "silent": "playing",
          "open": "closed", "closed": "open"}


def norm(v):
    """Object name as the engine resolves it: "Music_Box" and "bowl (empty) (1,4)" both count."""
    return re.sub(r"\s*\(.*", "", v.strip().lower().replace("_", " ")) if isinstance(v, str) else None


def clean(text, limit):
    """Free text is world data. Keep it on one line and unable to imitate a "[t12] ..." event."""
    return re.sub(r"\s+", " ", text).replace("[", "(").replace("]", ")").strip()[:limit]


def filled(v):
    return isinstance(v, str) and bool(v.strip())


def check(turn, w, mem):
    """None if the engine accepts the turn, else the reason it is a no-op."""
    a = turn.get("action") if isinstance(turn, dict) else None
    if not isinstance(a, dict):
        return "no action object"
    if not isinstance(turn.get("expect"), str):
        return "no expect"
    t, objs = a.get("type"), w["objects"]
    if t not in ALL_ACTIONS:
        return "unknown action"
    if t not in STAGE_ACTIONS[w["pet"]["stage"]]:
        return "not unlocked"
    target = norm(a.get("target"))
    if t == "look" and target not in objs and target != "visitor":
        return "bad target"
    if t == "move" and target not in objs and not tile_ok(a.get("tile")):
        return "bad target"
    if t == "use" and target not in USABLE:
        return "bad target"
    if t == "speak" and not (filled(a.get("text")) and len(a["text"]) <= 120):
        return "bad text"
    if t == "arrange" and not (norm(a.get("object")) in MOVABLE and tile_ok(a.get("tile"))):
        return "bad arrange"
    if t in ("write_belief", "revise_belief") and not filled(a.get("statement")):
        return "no statement"
    if t == "revise_belief" and not mem.is_active(a.get("id")):
        return "bad belief id"
    return None


def approach(w, pos):
    """Step next to pos, onto the neighbouring tile nearest to where the pet already is."""
    px, py = w["pet"]["pos"]
    tiles = [(pos[0] + dx, pos[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
             if (dx or dy) and 0 <= pos[0] + dx < W and 0 <= pos[1] + dy < H]
    w["pet"]["pos"] = list(min(tiles, key=lambda t: max(abs(t[0] - px), abs(t[1] - py))))


def describe(w, target):
    if target == "visitor":
        ago = w["tick"] - w["visitor_last"]
        return "someone was just here" if ago <= 3 else "someone was here a while ago" if ago <= 60 else "no one is there"
    if target == "mirror":
        return "you see yourself: " + genome.describe(w["pet"]["genome"])
    return "it is " + w["objects"][target].get("state", "just sitting there")


def apply(w, a, mem):
    """Apply a checked action. Returns (what the pet is told, need effects, novelty key or None)."""
    t, pet, objs = a["type"], w["pet"], w["objects"]
    target = norm(a.get("target"))
    if t == "observe":
        return "you observed", {}, None
    if t == "rest":
        return "you rested", {"energy": 3.0 if near(w, "bed") else 2.0}, None
    if t == "speak":
        pet["said"] = [w["tick"], clean(a["text"], 120)]
        return 'you said "%s"' % pet["said"][1], {}, None
    if t == "look":
        return "you looked at %s: %s" % (target, describe(w, target)), {}, "look " + target
    if t == "move":
        if target in objs:
            approach(w, objs[target]["pos"])
            return "you moved to " + target, {"energy": -0.5}, "move " + target
        pet["pos"] = list(a["tile"])
        return "you moved to (%d,%d)" % tuple(a["tile"]), {"energy": -0.5}, "move tile"
    if t == "use":
        approach(w, objs[target]["pos"])
        o = objs[target]
        if target == "blanket":
            return "you used blanket", {"comfort": 2.0}, "use blanket"
        if target == "bed":
            return "you rested on the bed", {"energy": 3.0}, None
        if target == "bowl":
            if o["state"] == "empty":
                return "you tried the bowl but it is empty", {}, None
            o["state"] = "half" if o["state"] == "full" else "empty"
            w["prev_eat"], w["last_eat"] = w["last_eat"], w["tick"]
            return "you ate from bowl", {"energy": 8.0}, "use bowl"
        o["state"] = TOGGLE[o["state"]]
        return "you toggled %s (%s)" % (target, o["state"]), {}, "use " + target
    if t == "arrange":
        name = norm(a["object"])
        approach(w, objs[name]["pos"])
        objs[name]["pos"] = list(a["tile"])
        return "you arranged %s to (%d,%d)" % (name, *a["tile"]), {"energy": -0.5}, "arrange " + name
    if t == "write_belief":
        bid = mem.write(clean(a["statement"], 200), w["tick"])
        return ("you wrote belief " + bid if bid else "your beliefs are full; nothing happened"), {}, None
    mem.revise(a["id"], clean(a["statement"], 200), w["tick"])
    return "you revised belief " + a["id"], {}, None


def visit(w, msg):
    """A visitor action from the view. Returns the event text, or None if the message is not valid."""
    kind, objs, needs = msg.get("type"), w["objects"], w["pet"]["needs"]
    if kind == "feed":
        objs["bowl"]["state"] = "full"
        text = "visitor filled the bowl"
    elif kind == "poke":
        needs["curiosity"] = min(100.0, needs["curiosity"] + 5)
        text = "visitor poked you"
    elif kind == "talk" and filled(msg.get("text")):
        needs["curiosity"] = min(100.0, needs["curiosity"] + 3)
        text = 'visitor said "%s"' % clean(msg["text"], 200)
    elif kind == "window":
        objs["window"]["state"] = TOGGLE[objs["window"]["state"]]
        text = "visitor made the window " + objs["window"]["state"]
    elif kind == "place" and msg.get("object") in PLACEABLE and tile_ok(msg.get("tile")):
        objs[msg["object"]]["pos"] = list(msg["tile"])
        text = "visitor placed %s at (%d,%d)" % (msg["object"], *msg["tile"])
    else:
        return None
    w["visitor_last"] = w["tick"]
    w["inbox"].append(text[len("visitor "):])
    add_event(w, text)
    return text
