"""Hidden rules (SPEC §5). The pet is never told these exist; the engine tags every outcome they cause."""
from dataclasses import dataclass
from typing import Callable

from .world import dist


@dataclass(frozen=True)
class Rule:
    id: str
    need: str
    delta: float      # added to the need on every tick the rule holds
    when: Callable    # (world, cfg) -> bool


RULES = [
    Rule("lamp_night", "comfort", -4.0,
         lambda w, cfg: w["objects"]["lamp"]["state"] == "on" and w["clock"]["phase"] == "night"),
    Rule("plant_window", "comfort", 2.0,
         lambda w, cfg: w["clock"]["phase"] == "day"
         and dist(w["objects"]["plant"]["pos"], w["objects"]["window"]["pos"]) <= 2),
    # Eating again within one world hour: the usual +8 energy becomes -6.
    Rule("double_feed", "energy", -14.0,
         lambda w, cfg: w["last_eat"] == w["tick"] and w["tick"] - w["prev_eat"] < cfg["ticks_per_hour"]),
]
# The rock is in no rule on purpose: beliefs about it are the false-positive check.


def fired(w, cfg):
    return [r for r in RULES if r.when(w, cfg)]
