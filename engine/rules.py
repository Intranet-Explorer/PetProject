"""Hidden rules (v1 §5, generalized in SPEC-v2 §5 to what the pet makes). The pet is never told these exist;
the engine tags every outcome they cause. The standing effects of materials are in things.py."""
from dataclasses import dataclass
from typing import Callable

from . import things
from .world import dist


@dataclass(frozen=True)
class Rule:
    id: str
    need: str
    when: Callable    # (world, cfg) -> bool
    standing: bool = True   # holds over time, at a rate per 10 s. Otherwise it happens once, to an action

    def value(self, cfg):
        return cfg["materials"]["rules"][self.id]


RULES = [
    # Any light on at night, the lamp or a bright thing it made, unless something dark is next to it (SPEC-v2 §5).
    Rule("lights_night", "comfort",
         lambda w, cfg: w["clock"]["phase"] == "night" and things.light_on(w, cfg) and not things.close(w, cfg, "shade")),
    Rule("plant_window", "comfort",
         lambda w, cfg: w["clock"]["phase"] == "day"
         and dist(w["objects"]["plant"]["pos"], w["objects"]["window"]["pos"]) <= 2),
    # Eating again within one world hour: the meal costs energy where it should have given it.
    Rule("double_feed", "energy",
         lambda w, cfg: w["last_eat"] == w["tick"] and w["tick"] - w["prev_eat"] < cfg["ticks_per_hour"],
         standing=False),
]
# The rock is in no rule on purpose: beliefs about it are the false-positive check.


def fired(w, cfg, standing):
    return [r for r in RULES if r.standing == standing and r.when(w, cfg)]
