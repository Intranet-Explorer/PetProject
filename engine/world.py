"""World state (SPEC §4). The world is one JSON-able dict; everything else is functions over it."""
import tomllib
from pathlib import Path

from .genome import START

ROOT = Path(__file__).parent.parent
W, H = 12, 8
NEEDS = ("energy", "comfort", "curiosity")
LONG_AGO = -10**6


def load_config(path=ROOT / "config.toml"):
    cfg = tomllib.loads(Path(path).read_text())
    cfg["ticks_per_day"] = round(cfg["clock"]["day_seconds"] / cfg["clock"]["tick_seconds"])
    cfg["ticks_per_hour"] = cfg["ticks_per_day"] / 24
    cfg["dt"] = cfg["clock"]["tick_seconds"] / 10   # standing rates are written per 10 s, as in v1
    cfg["materials"] = tomllib.loads((Path(path).parent / "materials.toml").read_text())
    return cfg


def ticks(cfg, seconds):
    return max(1, round(seconds / cfg["clock"]["tick_seconds"]))


def new_world(cfg):
    """The starting room. Fixed layout, so every pet's life starts identically."""
    w = {
        "tick": 0,
        "pet": {
            "pos": [5, 3],
            "stage": cfg["world"]["start_stage"],
            "needs": {"energy": 70.0, "comfort": 60.0, "curiosity": 60.0},
            "trend": {},     # last tick's need deltas
            "said": None,    # [tick, text] of the latest speech bubble
            "name": None,    # set if it ever says "my name is ..."
            "genome": dict(START, marks=[]),
        },
        "objects": {
            "lamp": {"pos": [2, 1], "state": "on"},
            "plant": {"pos": [8, 6]},
            "bowl": {"pos": [6, 7], "state": "full"},      # full, half, empty: two servings
            "ball": {"pos": [4, 5]},
            "blanket": {"pos": [9, 3]},
            "music box": {"pos": [7, 2], "state": "silent"},
            "rock": {"pos": [3, 6]},
            "window": {"pos": [0, 3], "state": "closed"},   # left wall; the door is on the right wall
            "bed": {"pos": [10, 1]},
            "mirror": {"pos": [5, 0]},
        },
        "events": [],                  # [tick, text], what the pet can recall as "recent"
        "inbox": [],                   # what the visitor did since the pet last perceived
        "seen_at": {},                 # novelty: interaction -> tick it last happened
        "last_eat": LONG_AGO,
        "prev_eat": LONG_AGO,
        "visitor_last": LONG_AGO,      # tick of the visitor's latest action
        "sleep": None,                 # {"since", "day", "done"} while asleep
        "last_night": None,            # {"day", "dream", "changes", "body", "reason"} from the latest sleep
        "diary": [],                   # every night so far, same shape
        "plan": None,                  # the intention being carried out (see tick.Pet.adopt)
        "last_plan": None,             # {"intention", "ended", "score"} of the one before
        "thinking": None,              # why the model is being asked, while it is
        "news": [],                    # reasons to think again: visitor, woke, hatched, need, phase
        "seen": -1,                    # events up to this tick were in a packet already
        "last_call": LONG_AGO,         # tick of the latest model call
        "calls": [],                   # ticks of the model calls in the last real hour
        "phase_seen": "day",
        "moments": [],                 # [tick, text]: things worth seeing, for the view (SPEC-v2 §9)
        "exploits": {"lights_night": 0, "plant_window": 0, "double_feed": 0},   # times each rule was used on purpose
        "near_window": 0,              # waking ticks spent near the window
    }
    w["clock"] = clock(cfg, 0)
    return w


def clock(cfg, tick):
    """Life starts at 08:00 on day 1. Light follows the phase; the view adds the lamp."""
    hour = (8 + tick / cfg["ticks_per_hour"]) % 24
    phase = "day" if 6 <= hour < 18 else "dusk" if 18 <= hour < 21 else "night"
    return {"phase": phase, "hour": round(hour, 2), "day": 1 + int((8 + tick / cfg["ticks_per_hour"]) // 24)}


def dist(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def near(w, name, r=1):
    return dist(w["pet"]["pos"], w["objects"][name]["pos"]) <= r


def tile_ok(t):
    return (isinstance(t, list) and len(t) == 2 and all(type(v) is int for v in t)
            and 0 <= t[0] < W and 0 <= t[1] < H)


def moment(w, text):
    w["moments"] = (w["moments"] + [[w["tick"], text]])[-200:]


def add_event(w, text):
    w["events"].append([w["tick"], text])
    del w["events"][:-200]   # ponytail: retrieval looks back 200 events, not the whole journal
