"""SPEC-v4.0 §2 needs: hunger, safety, pride. Switch: [needs4] on.

While on, pet["needs"] holds them beside the four (0-100, high is well), food fills hunger instead of energy, and the
body eats when hungry. Off, they are put aside in pet["needs4"] so everything reads the four needs of v3.6c, and food
gives energy again."""
from .world import alive, days, label, moment
from . import feel as F, memories
from . import sheet

NEW = ("hunger", "safety", "pride")
START = {"hunger": 75.0, "safety": 70.0, "pride": 55.0}
WORDS = dict(F.WORDS, hunger=["full", "fed", "a bit hungry", "hungry", "starving"], safety=["safe", "settled", "a little on edge", "afraid", "terrified"],
             pride=["proud of yourself", "worth something", "a little useless", "useless", "worthless"])   # (feel.WORDS stays v3.6c's four)


def on(cfg):
    return bool(cfg.get("needs4", {}).get("on"))


def feel(pet):
    """Every need as a feeling, the worst first (never a number): the four of v3.6c and the three new ones."""
    out = []
    for n in sorted(pet["needs"], key=lambda n: -F.level(pet, n)):
        lvl = F.level(pet, n)
        out.append(WORDS[n][lvl] + (" (it is hard to think of anything else)" if lvl == 4 else ""))
    return out


def appetite(cfg, pet):
    """The need the body eats for: hunger while on, energy as in v3.6c."""
    return "hunger" if on(cfg) and "hunger" in pet["needs"] else "energy"


def food(house, cfg, pet, fx):
    """What eating does: while on, its energy goes into hunger instead (`food` times as much). Returns fx."""
    if on(cfg) and "hunger" in pet["needs"] and fx.get("energy", 0) > 0:
        lift(house, cfg, pet, "hunger", fx.pop("energy") * cfg["needs4"]["food"])
    return fx


def lift(house, cfg, pet, need, amount):
    """A new need moved by an event (pride from praise or a first, safety after a fight, hunger from food)."""
    if on(cfg) and need in pet["needs"]:
        pet["needs"][need] = round(min(100.0, max(0.0, pet["needs"][need] + amount)), 2)


def slow(pet):
    """How much a hungry hob slows: 1, then 0.8 hungry, 0.6 starving (for the body)."""
    return {3: 0.8, 4: 0.6}.get(F.level(pet, "hunger"), 1.0) if "hunger" in pet["needs"] else 1.0


def starved(house, cfg, pet):
    """(life.due) Starving this long kills: rare, while the house has food."""
    s = pet.get("starving")
    return bool(on(cfg) and s is not None and days(cfg, s, house["tick"]) >= cfg["needs4"]["starve_days"])


def lit5(house, cfg, room):
    """SPEC-v5.0 §1.4: a light lit in the room as an item (a lantern that burns oil is lit in a power cut too)."""
    from . import contracts, items
    return contracts.on5(cfg, "items") and items.strength(house, cfg, room, "light", True) > 0


def safe_target(house, cfg, pet):
    """Where safety settles: company, light at night and shelter raise it; dark, storms, outdoors at night, enemies
    and a recent threat lower it."""
    from . import opinions, things
    from .world import here
    room, night, N = house["rooms"][pet["room"]], house["clock"]["phase"] == "night", cfg["needs4"]
    others = here(house, pet)
    t = 60 + (15 if others else -10)
    if night:
        t += 10 if things.light_on(house, cfg, room) or lit5(house, cfg, room) else -10
        t -= 15 if room.get("outdoor") else 0
    if house["weather"] == "storm" and room["type"] not in ("cellar", "storeroom"):
        t -= 10 if others else 25
    if opinions.on(cfg):
        t -= sum(2 * opinions.of(pet, o["id"])["fear"] + (10 if opinions.of(pet, o["id"])["liking"] < -5 else 0) for o in others)
    if (pet.get("hurt") or {}).get("level"):   # (a lasting limp alone is no threat)
        t -= 10
    return max(5, min(95, t))


def tick(house, cfg):
    pets = [p for p in alive(house) if p["stage"] != "egg"]
    if not on(cfg):
        for p in pets:   # put aside, so every v3.6c reader sees its four needs
            if "hunger" in p["needs"]:
                p["needs4"] = {n: p["needs"].pop(n) for n in NEW if n in p["needs"]}
        return
    N, dt = cfg["needs4"], cfg["dt"]
    from . import health
    deaths = health.deaths(cfg)   # SPEC-v4.2 §2
    for p in pets:
        if "hunger" not in p["needs"]:
            p["needs"].update({n: (p.get("needs4") or {}).get(n, START[n]) for n in NEW})
        n = p["needs"]
        n["hunger"] = max(0.0, n["hunger"] + N["hunger_drift"] * dt * (N["asleep"] if p["sleep"] else 1))
        if house["tick"] % 5 == 0:
            n["safety"] += (safe_target(house, cfg, p) - n["safety"]) * N["safety_rate"]
        n["pride"] = max(0.0, n["pride"] + N["pride_drift"] * dt * n["pride"] / 50)
        if n["hunger"] <= 1:
            if p.get("starving") is None:
                p["starving"] = house["tick"]
                moment(house, "starving", "%s is starving" % label(p), p["id"], p["room"])
            p["weak"] = True
            if deaths:
                health.mark(house, p, "starvation")   # SPEC-v4.2 §2: its decline shows from here
            if days(cfg, p["starving"], house["tick"]) >= 1 and not p.get("sick") and cfg.get("health", {}).get("on"):
                if deaths:
                    health.sicken(house, cfg, p, "hunger", level="ill")
                else:
                    p["sick"] = {"level": "ill", "since": house["tick"], "from": "hunger"}   # (health.py heals it, or not)
        elif n["hunger"] > 20:
            p["starving"] = None
            (p.get("decline") or {}).pop("starvation", None)
    for m in memories.new_moments(house, "needs"):
        p = house["pets"].get(m["pet"] or "")
        if p and m["kind"] in PRIDE:
            lift(house, cfg, p, "pride", PRIDE[m["kind"]])
        elif p and m["kind"] in DEEDS and sheet.on(cfg):   # (24 November 2026) the day's ordinary good work is worth something too
            lift(house, cfg, p, "pride", DEEDS[m["kind"]])


# moment kind -> pride for the hob it is about (making something good, a first, a best...); praise and thanks come
# through opinions.toml's causes, winning from conflict.py
DEEDS = {"fixed": 0.5, "mended": 1, "cooked": 1, "stored": 0.5, "planted": 0.5}   # (24 November 2026, with [sheet] on) a job seen to, a thing mended, a meal cooked, food put by, a seed planted
PRIDE = {"made": 1.5, "first": 5, "best": 10, "invented": 8, "built": 6, "discovery": 4, "catch": 2, "named": 3, "song": 3}
