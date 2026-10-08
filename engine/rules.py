"""Hidden rules (SPEC §5). The pet is never told these exist; the engine tags every outcome they cause."""
from dataclasses import dataclass
from typing import Callable

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
    Rule("lamp_night", "comfort",
         lambda w, cfg: w["objects"]["lamp"]["state"] == "on" and w["clock"]["phase"] == "night"),
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
