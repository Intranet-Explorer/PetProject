"""Self-check for SPEC-v4.0 §7 (engine/conflict.py, engine/health.py, conflict.toml), with stub minds in a temporary house:
the ladder keeps its thresholds, witnesses and little ones; sabotage and theft act on the world; a kind onlooker steps in;
injuries heal (faster with a healer) and can leave a limp; sickness spreads and heals; a forced killing is told, grieved,
judged and avenged; the visitor stops a fight, protects and judges; making up and time apart close grievances; and with
[ladder] or [health] off, none of it starts. Then §13.2's stub run: a few world days of the whole engine with scripted
brains: a feud climbs and comes down, a fight injures and heals, a forced killing leads to grief, justice and vengeance.

    uv run python -m engine.check_conflict          (the checks and the stub run)
    uv run python -m engine.check_conflict quick    (the checks only)"""
import asyncio
import os
import sys
import tempfile

from . import tick as _engine   # noqa: F401 (the engine first)
from . import character, conflict, health, opinions, outdoors, visitor, world
from .check import engine, load_config
from .check_build import grown
from .check_machine import thing
from .world import generate_room, new_pet

LADDER = ("snub", "insult", "sabotage", "theft", "shove", "fight", "harm", "killing", "making up", "justice", "vigil")


def config(body=False):
    cfg = load_config(body=body)
    cfg["weather"]["real"] = False
    for part in ("traits", "opinions", "ladder", "health"):
        cfg[part]["on"] = True
    return cfg


async def house(d, cfg, names):
    """A house with a garden, the yard and the meadow, and grown hobs: the first is the others' parent unless named
    with a leading '!' (no kin)."""
    eng, first = engine(cfg, d)
    h = eng.house
    for _ in range(2):
        await eng.tick()
    rid = next(r for r, x in sorted(h["rooms"].items()) if not x["type"] and x["cell"][1] == 2)
    generate_room(h, cfg, rid, "garden")
    outdoors.migrate(h, cfg)
    pets = [first]
    for i, n in enumerate(names[1:]):
        pets.append(new_pet(h, cfg, first["room"], [2 + i, 2], parent=None if n.startswith("!") else first["id"]))
    for p in pets:
        p["laid"] = -10 ** 6
    await eng.tick()
    for p, n in zip(pets, names):
        grown(h, p)
        p["name"] = n.lstrip("!")
        p["temper"].update(kind=0.5, honest=0.5, generous=0.5, bold=0.5)
    return eng, h, pets


def temper(p, **axes):
    for axis, v in axes.items():
        p["temper"][character.GENE.get(axis, axis)] = (v + 1) / 2


def like(h, p, q, liking, why="it broke my cup", fear=0, respect=5):
    p.setdefault("opinions", {})[q["id"]] = {"liking": liking, "trust": 5, "fear": fear, "respect": respect, "fixed": {}, "since": h["tick"],
                                             "causes": [{"tick": h["tick"], "cause": "insult", "why": why, "d": {"liking": -3}}]}


def sure(cfg):
    """Every chance a certainty (the checks of what may happen, not of how often)."""
    for r in conflict.C(cfg)["rung"]:
        r["chance"] = 1.0
    conflict.C(cfg)["ladder"]["watched_hold"] = 1.0


def moments(h, kind):
    return [m for m in h["moments"] if m["kind"] == kind]


async def checks(d):
    cfg = config()
    sure(cfg)
    L = conflict.C(cfg)
    eng, h, (flint, bogna, mira, odo, pip) = await house(d, cfg, ["Flint", "!Bogna", "Mira", "!Odo", "Pip"])
    pip["stage"] = "child"
    tph, tpd = cfg["ticks_per_hour"], cfg["ticks_per_day"]
    for p in (mira, odo, pip):
        p["room"] = next(r for r in h["rooms"] if h["rooms"][r]["type"] == "garden")   # out of the way
    temper(flint, honest=-0.8, kind=-0.8, generous=-0.6, brave=0.6)
    temper(bogna, kind=0.1, brave=-0.1)
    like(h, flint, bogna, -10)
    conflict.seed(h, cfg)
    g = conflict.find(h, flint["id"], bogna["id"])
    assert g and g["rung"] == 0 and g["why"] == "it broke my cup", "a grievance needs a remembered reason: %s" % g
    assert not conflict.find(h, bogna["id"], flint["id"]), "no reason, no grievance"

    # ---- thresholds (conflict.toml [[rung]]) ----
    W = lambda n: conflict.why_not(h, cfg, g, flint, bogna, n)
    assert W(3) is None and W(4) is None
    like(h, flint, bogna, -3)
    assert W(3) == "liking" and W(4) == "liking", "sabotage and theft need liking below -4"
    like(h, flint, bogna, -10)
    temper(flint, honest=0.5, kind=0.5, generous=0.5)
    assert W(3) == "temper" and W(4) == "temper", "and sly or prickly; greedy or sly"
    temper(flint, honest=-0.8, kind=-0.8, generous=-0.6)
    g["fresh"] = h["tick"] - 7 * tph
    assert W(5) == "not angry", "a shove needs anger"
    g["fresh"] = h["tick"]
    assert W(5) is None
    g["since"] = h["tick"] - 2 * tph
    temper(flint, brave=-0.6)
    assert W(6) == "temper", "the timid don't fight"
    temper(flint, brave=0.6)
    assert W(6) is None
    assert W(7) == "too soon", "grave harm needs a long grudge"
    g["since"] = h["tick"] - 3 * tpd
    assert W(7) is None and W(8) == "never climbed again", "a killing needs a grievance that came down once and climbed again"
    g["history"].append([h["tick"], 5, "cooled"])
    assert W(8) is None
    mira["room"] = flint["room"]
    assert W(7) == "not alone" and W(8) == "not alone", "the top rungs need the two alone"
    mira["room"] = odo["room"]
    conflict.protect(h, cfg, bogna["id"], h["tick"] + tpd)
    assert W(5) == "protected" and W(3) is None, "the visitor's protection: nobody can hurt it"
    h["visitor"]["protect"] = {}
    pip["room"] = flint["room"]
    gp = conflict.grudge(h, cfg, pip["id"], bogna["id"], "it took my ball")
    like(h, pip, bogna, -10)
    temper(pip, kind=-0.8, honest=-0.8, brave=0.8)
    gp["since"], gp["history"] = h["tick"] - 3 * tpd, gp["history"] + [[h["tick"], 0, "cooled"]]
    assert all(conflict.why_not(h, cfg, gp, pip, bogna, n) == "little" for n in (5, 6, 7, 8)), "little ones are never killers"
    assert conflict.why_not(h, cfg, gp, pip, bogna, 4) is None
    conflict.close(h, cfg, gp, "check")
    gl = conflict.grudge(h, cfg, flint["id"], pip["id"], "it laughed at me")   # (19 October 2026) nor ever the victim of the worst
    like(h, flint, pip, -10)
    pip["sleep"], gl["since"], gl["history"] = None, h["tick"] - 3 * tpd, gl["history"] + [[h["tick"], 0, "cooled"]]
    for venge in (False, True):
        gl["vengeance"] = venge
        assert conflict.why_not(h, cfg, gl, flint, pip, 5) is None and all(conflict.why_not(h, cfg, gl, flint, pip, n) == "little victim" for n in (6, 7, 8)), \
            "a little one at liking -10 may be shoved, never fought, badly hurt or killed"
    conflict.close(h, cfg, gl, "check")
    pip["room"] = odo["room"]

    # ---- rung 3 and 4 act on the world ----
    room = h["rooms"][flint["room"]]
    thing(eng, room, "blue cup", "cup", "hard", bogna["id"])
    g["rung"] = 2
    conflict.climb(h, cfg, g)
    assert g["rung"] == 3 and "blue cup" not in room["objects"] and any("blue cup" in r.get("objects", {}) for r in h["rooms"].values()), "the sly hide it elsewhere"
    assert moments(h, "sabotage")[-1]["pets"] == [flint["id"], bogna["id"]]
    thing(eng, room, "red cup", "cup", "hard", bogna["id"])
    thing(eng, room, "old cup", "cup", "hard", bogna["id"])
    room["objects"]["red cup"]["made"]["uses"] = 9
    g["last_act"] = h["tick"] - 5 * tph
    conflict.climb(h, cfg, g)
    assert g["rung"] == 4 and room["objects"]["red cup"]["made"]["owner"] == flint["id"], "theft takes what it loves most"
    assert conflict.find(h, bogna["id"], flint["id"]), "the one robbed (and watching) now holds a grievance too"

    # ---- witnesses: above rung 4, a watched hob holds back ----
    g["last_act"] = h["tick"] - 5 * tph
    mira["room"] = flint["room"]
    temper(flint, brave=0.0)
    assert conflict.climb(h, cfg, g) is None and g["rung"] == 4, "held back while watched"
    temper(flint, brave=0.6)
    mira["room"] = odo["room"]
    sc = conflict.climb(h, cfg, g)
    assert sc and sc["rung"] == 5 and flint["scuffle"] > h["tick"] and health.slowed(h, cfg, flint), "a shove, alone: a scuffle nobody walks out of"
    while not sc["outcome"]:
        h["tick"] += 1
        conflict.scuffles(h, cfg)
    assert g["rung"] == 5 and not bogna.get("hurt") and "scuffle" not in flint, "a shove: no injury"

    # ---- a fight injures; a kind onlooker steps in, and the kind protect little ones first ----
    sc = conflict.force(h, cfg, flint["id"], bogna["id"], 6)
    h["tick"] = sc["until"]
    conflict.scuffles(h, cfg)
    hurt = [p for p in (flint, bogna) if (p.get("hurt") or {}).get("level")]
    assert hurt and sc["blood"] and moments(h, "fight")[-1]["hurt"] is True and moments(h, "fight")[-1]["pets"] == [flint["id"], bogna["id"]], sc
    assert any(b["kind"] == "fight" for b in h["bursts"]), "a fight with injury is a banner"
    temper(mira, kind=0.8)
    mira["room"], pip["room"] = flint["room"], flint["room"]
    L["coming_down"]["step_in_little"] = 1.0
    sc = conflict.force(h, cfg, flint["id"], pip["id"], 7)
    h["tick"] = sc["until"]
    conflict.scuffles(h, cfg)
    assert sc["outcome"] == "stepped in: %s" % mira["id"] and not (pip.get("hurt") or {}).get("level"), "Mira steps in for the little one: %s" % sc
    assert moments(h, "harm")[-1]["pets"][2] == mira["id"]
    mira["room"] = pip["room"] = odo["room"]

    # ---- injuries heal, faster with a healer; badly hurt may leave a limp ----
    for p in (flint, bogna, odo, mira):
        p["hurt"] = None
    health.hurt(h, cfg, odo, "hurt", "a fall")
    health.hurt(h, cfg, bogna, "hurt", "a fall")
    mira["room"] = bogna["room"]
    mira.setdefault("skill", {})["healing"] = 8
    start, healed = h["tick"], {}
    while len(healed) < 2 and h["tick"] - start < 4 * tpd:
        h["tick"] += 1
        for p in (odo, bogna):
            p["sleep"] = None
            p["needs"].update(energy=80.0, comfort=80.0)
        health.tick(h, cfg)
        for p in (odo, bogna):
            if not p.get("hurt") and p["id"] not in healed:
                healed[p["id"]] = h["tick"] - start
    assert len(healed) == 2 and healed[bogna["id"]] < healed[odo["id"]], "both heal, the nursed one sooner: %s" % healed
    assert mira["id"] in bogna.get("nursed_by", {}) and mira["skill"]["healing"] > 8, "nursing is remembered, and the healer learns"
    L["hurt"]["limp"] = 1.0
    health.hurt(h, cfg, odo, "badly hurt", "a fall from the shelf")
    odo["hurt"]["left"] = 0
    health.heal(h, cfg, odo)
    assert odo["hurt"]["lasting"] == "limp" and odo["hurt"]["level"] == "hurt"
    odo["hurt"].update(level=None)
    assert health.slowed(h, cfg, odo) == (h["tick"] % L["hurt"]["slow"]["limp"] == 0)

    L["hurt"]["forge"] = 1.0
    h.setdefault("machine_runs", []).append([h["tick"] - 1, "forge", flint["id"], "ore", "nail"])
    flint["hurt"] = None
    health.accidents(h, cfg)
    assert flint["hurt"]["level"] == "bruised" and moments(h, "hurt")[-1]["text"] == "Flint burned a paw at the forge", "the forge burns"
    flint["hurt"] = None

    # ---- sickness spreads, and care brings it down ----
    S = L["sick"]
    S.update(catch=1.0, better=0.0, worse=0.0)
    h["tick"] = (h["tick"] // round(tph) + 1) * round(tph)
    odo["room"] = bogna["room"]
    health.sicken(h, cfg, bogna, "the cold")
    h["tick"] += round(tph)
    health.tick(h, cfg)
    assert (odo.get("sick") or {}).get("from") == "caught it from Bogna", odo.get("sick")
    S.update(catch=0.0, better=1.0)
    for _ in range(4):
        h["tick"] += round(tph)
        health.tick(h, cfg)
    assert not bogna.get("sick") and not odo.get("sick"), "rest, warmth and a healer bring it down"
    S.update(better=0.0, worse=1.0, die=1.0)
    health.sicken(h, cfg, odo, "the cold")
    odo["needs"].update(energy=5.0, comfort=5.0)
    odo["sick"]["level"] = "very sick"
    h["tick"] += round(tph)
    health.sickness(h, cfg)
    assert odo.get("death_due") == "sickness", "neglect can kill"
    odo.pop("death_due")
    odo["sick"] = None
    S.update(better=0.18, worse=0.12, die=0.04, catch=0.04)

    # ---- making up, a gift, time apart ----
    L["coming_down"]["accept"] = 2.0
    gb = conflict.grudge(h, cfg, bogna["id"], flint["id"], "it stole my cup")
    assert conflict.made_up(h, cfg, flint["id"], bogna["id"], "apology") and not conflict.between(h, flint["id"], bogna["id"]), "an accepted apology closes both sides"
    assert moments(h, "making up")[-1]["pets"] == [flint["id"], bogna["id"]]
    conflict.grudge(h, cfg, bogna["id"], flint["id"], "it stole my cup")
    conflict.gift(h, cfg, flint["id"], bogna["id"])
    assert not conflict.find(h, bogna["id"], flint["id"]), "a gift from the one it holds a grievance against makes it up"
    gb = conflict.grudge(h, cfg, bogna["id"], flint["id"], "it laughed at me")
    gb["rung"] = 1
    like(h, bogna, flint, -2)
    h["tick"] += round(1.6 * tpd)
    conflict.cool(h, cfg)
    assert not conflict.find(h, bogna["id"], flint["id"]) and [bogna["id"], flint["id"]] == h["cold"][-1][:2], "time apart: it ends in a coldness"
    h["tick"] = (h["tick"] // conflict.every(cfg) + 1) * conflict.every(cfg)
    conflict.tick(h, cfg)
    assert flint["id"] in bogna["avoid"], "and they keep apart (pet['avoid'], for the body)"
    opinions.move(h, cfg, bogna, flint["id"], "gift", "it gave me a cup")   # (19 October 2026: a coldness thaws)
    assert opinions.of(bogna, flint["id"])["liking"] >= 0
    conflict.tick(h, cfg)   # (the next look at the ladder; the same tick, so the chances below stay as they were)
    assert flint["id"] not in bogna["avoid"] and not h["cold"], "liking back past nothing: within ten minutes they no longer keep apart"

    # ---- the visitor stops a fight ----
    g = conflict.grudge(h, cfg, flint["id"], bogna["id"], "again")
    sc = conflict.force(h, cfg, flint["id"], bogna["id"], 6)
    assert conflict.stop_fight(h, cfg, bogna["id"], flint["id"]) and sc["stopped"] == "visitor" and "scuffle" not in flint
    h["tick"] = sc["until"] + 1
    conflict.scuffles(h, cfg)
    assert not sc["outcome"] and not (bogna.get("hurt") or {}).get("level"), "stopped: nothing comes of it"

    # ---- a forced killing: told, grieved, judged, avenged ----
    for r in L["rung"]:
        r["chance"] = 0.0   # (from here on only what is forced)
    son = new_pet(h, cfg, flint["room"], [3, 3], parent=odo["id"])
    son["laid"] = -10 ** 6
    await eng.tick()
    grown(h, son)
    son["name"] = "Sol"
    kid = new_pet(h, cfg, odo["room"], [3, 3], parent=odo["id"])   # Odo's child, not yet hatched: it will hear the legend
    for p in (flint, odo, mira, bogna, son):
        p["room"], p["sleep"] = flint["room"], None
    for p in (flint, odo, mira):
        p["pos"] = world.free_tile(h, cfg, h["rooms"][flint["room"]], [4, 4])
    temper(mira, kind=0.8, brave=0.6)
    L["coming_down"]["step_in"] = 0.0
    gk = conflict.grudge(h, cfg, flint["id"], odo["id"], "it shamed me")
    sc = conflict.force(h, cfg, flint["id"], odo["id"], 8)
    while odo["stage"] != "dead":
        await eng.tick()
    assert odo["cause"] == "violence" and moments(h, "killing")[-1]["hurt"] and any(b["kind"] == "killing" for b in h["bursts"]), "it falls and lies still"
    assert any(m["kind"] == "death" for m in h["moments"][-5:]), "through the engine's own death"
    k = h["killings"][-1]
    assert k["killer"] == flint["id"] and set(k["witnesses"]) >= {mira["id"], bogna["id"]} and k["found"], k
    assert any(a["kind"] == "vigil" and a["target"] == odo["id"] for a in son.get("aims", [])), "grief: its kin will keep a vigil"
    assert not conflict.find(h, mira["id"], flint["id"]), "no vengeance from a hob that wasn't the dead's kin or friend"
    conflict.tick(h, cfg) if h["tick"] % conflict.every(cfg) == 0 else conflict.after(h, cfg)
    v = conflict.find(h, son["id"], flint["id"])
    assert v and v["vengeance"] and v["rung"] == 5 and conflict.why_not(h, cfg, v, son, flint, 6) is None, "vengeance: its son starts at a fight: %s" % v
    kid["laid"] = -10 ** 6
    await eng.tick()
    while not k["verdict"]:
        h["tick"] += conflict.every(cfg) - h["tick"] % conflict.every(cfg)
        conflict.tick(h, cfg)
    assert kid["id"] in k["legend"] and not (conflict.find(h, kid["id"], flint["id"]) or {}).get("vengeance"), "the family tells it to the young; a hatchling holds no vengeance (19 October 2026)"
    kid["stage"] = "youngling"
    conflict.after(h, cfg)
    assert conflict.find(h, kid["id"], flint["id"])["vengeance"], "grown a little, it does: the feud runs on a generation"
    assert k["verdict"] == "driven out" and flint["outcast"] and flint["room"] == outdoors.MEADOW, k
    assert outdoors.barred(h, cfg, flint, outdoors.YARD, "north") and not outdoors.come_in(h, cfg, flint), "an outcast lives out there"
    assert any(b["kind"] == "driven out" for b in h["bursts"]) and moments(h, "justice")
    ok, said = conflict.judge(h, cfg, flint["id"], "pardon")
    assert ok and k["verdict"] == "forgiven" and k["by"] == "the visitor" and not flint["outcast"] and not conflict.find(h, kid["id"], flint["id"])["vengeance"], said
    flint["outcast"], flint["room"] = {"since": h["tick"] - 9 * tpd, "why": "a check"}, outdoors.MEADOW
    L["after"]["come_back"] = 10 ** 6
    conflict.outcasts(h, cfg)
    assert not flint["outcast"] and any(b["kind"] == "coming back" for b in h["bursts"]), "it may come back"
    assert character.mood(flint) in ("proud", "ashamed", "afraid") or not character.on(cfg), "the killer gives itself away"
    assert conflict.judge(h, cfg, flint["id"], "pardon") == (False, "Flint is forgiven already"), "(19 October 2026) a verdict is not given twice"
    conflict.verdict_on(h, cfg, k, "shunned", "the family")
    assert any("shunned Flint" in m["text"] for m in flint["memories"]) and not any("shunned Flint" in m["text"] for m in mira["memories"]), \
        "a changed verdict: the killer remembers it, the house doesn't again"
    conflict.after(h, cfg)
    assert not conflict.find(h, kid["id"], flint["id"])["vengeance"], "and vengeance, granted once, is not granted again"
    conflict.outcasts(h, cfg)
    assert flint["shunned"] == h["tick"] and flint["id"] in mira["avoid"], "shunned: everyone keeps away from it"
    h["tick"] += 7 * tpd
    conflict.outcasts(h, cfg)
    assert flint["shunned"] is None and flint["id"] not in mira["avoid"]

    # ---- with conversations on, snubs and insults are talk's, unless the two haven't had words for a day ----
    cfg["talk"]["on"] = True
    for r in L["rung"]:
        r["chance"] = 1.0
    bogna["sleep"] = mira["sleep"] = None
    mira["room"] = bogna["room"]
    like(h, mira, bogna, -3)
    gm = conflict.grudge(h, cfg, mira["id"], bogna["id"], "it took my seat")
    assert conflict.climb(h, cfg, gm) is None and gm["rung"] == 0
    gm["since"] -= 25 * tph
    assert conflict.climb(h, cfg, gm) and gm["rung"] == 1 and moments(h, "snub")[-1]["pets"] == [mira["id"], bogna["id"]]
    assert opinions.of(bogna, mira["id"])["causes"][-1]["cause"] == "snubbed", "the ladder's own snub moves the other's opinion (19 October 2026)"
    cfg["talk"]["on"] = False

    # ---- 19 October 2026: a vigil ends after grief_hours, also when the killer is dead (it never did) ----
    for r in L["rung"]:
        r["chance"] = 0.0
    baby = new_pet(h, cfg, son["room"], [5, 5], parent=son["id"])
    conflict.killed(h, cfg, bogna, baby, [])
    vigil = next(a for a in son["aims"] if a["kind"] == "vigil" and a["target"] == baby["id"])
    bogna["stage"] = baby["stage"] = "dead"
    end = h["tick"] + L["after"]["grief_hours"] * tph
    while h["tick"] < end + conflict.every(cfg):
        assert not vigil["done"] or h["tick"] >= end, "kept until grief_hours are over"
        h["tick"] += conflict.every(cfg) - h["tick"] % conflict.every(cfg)
        conflict.tick(h, cfg)
    assert vigil["done"], "the killer is dead and nobody came to the stone: the vigil still ends"
    return eng


async def switches(d):
    """[ladder] off: no rung from 3 up, grievances only cool, a scuffle under way ends; [health] off: nothing starts and
    what there was goes at once; the outcast is let in."""
    cfg = config()
    sure(cfg)
    eng, h, (flint, bogna) = await house(d, cfg, ["Flint", "!Bogna"])
    temper(flint, honest=-0.8, kind=-0.8, generous=-0.6, brave=0.6)
    like(h, flint, bogna, -10)
    thing(eng, h["rooms"][flint["room"]], "blue cup", "cup", "hard", bogna["id"])
    sc = conflict.force(h, cfg, flint["id"], bogna["id"], 6)
    cfg["ladder"]["on"] = False
    g = conflict.find(h, flint["id"], bogna["id"])
    g["rung"], g["fresh"], g["since"] = 2, h["tick"] - 2 * cfg["ticks_per_day"], h["tick"] - 2 * cfg["ticks_per_day"]
    g.pop("last_act", None)
    # (19 October 2026) off means off: the visitor can't judge, the shunned may talk again, protection still runs out
    cfg["visitor4"]["on"] = True
    assert visitor.use(eng, "stepin", {"pet": flint["id"], "how": "shun"}) == (False, "the house has no quarrels to judge")
    flint["shunned"] = h["tick"]
    conflict.avoid(bogna, flint["id"])
    cfg["visitor4"]["on"] = False
    conflict.protect(h, cfg, bogna["id"], h["tick"] + 1)
    for _ in range(3 * conflict.every(cfg)):
        await eng.tick()
    assert flint["shunned"] is None and not flint.get("outcast") and flint["id"] not in bogna["avoid"], "a shunned hob can talk again with the ladder off"
    assert not h["visitor"]["protect"], "the visitor's protection ran out"
    assert sc["stopped"] == "switched off" and not sc["outcome"] and "scuffle" not in flint, "a scuffle under way ends"
    assert g["rung"] == 1 and g["history"][-1][2] == "cooled" and "blue cup" in h["rooms"][flint["room"]]["objects"], "off: nothing climbs, it only cools"
    assert not moments(h, "sabotage") and not moments(h, "theft")
    flint["outcast"] = {"since": h["tick"], "why": "a check"}
    flint["room"] = outdoors.MEADOW
    assert not outdoors.barred(h, cfg, flint, outdoors.YARD, "north"), "the outcast may come in while the ladder is off"
    cfg["ladder"]["on"] = True
    cfg["health"]["on"] = False
    flint["outcast"], flint["room"] = None, bogna["room"]
    assert health.hurt(h, cfg, bogna, "hurt", "a check") is None and health.sicken(h, cfg, bogna, "a check") is None, "off: nothing starts"
    bogna["hurt"] = {"level": "hurt", "since": 0, "lasting": "limp", "left": 9}
    bogna["sick"] = {"level": "sick", "since": 0, "from": "a check"}
    health.tick(h, cfg)
    assert not bogna["hurt"] and not bogna["sick"] and not health.slowed(h, cfg, bogna), "off: what there was goes at once"
    g["rung"], g["fresh"], g["since"] = 5, h["tick"], h["tick"] - cfg["ticks_per_day"]
    g.pop("last_act", None)
    assert conflict.climb(h, cfg, g) is None and g["rung"] == 5, "off: no fight (rung 6 and up act through health)"


def story(d):
    """§13.2: seven world days of the whole engine (the body on), with scripted brains: from half a day in Flint is angry
    with Bogna and means to make her pay, until it has come to blows; from then on Bogna means to make up, every few
    hours; on day four Flint is made to kill Odo (forced, with nobody stepping in) in front of Bogna; the mourners go to
    the stone. Everything else (each rung, injury, healing, telling, justice, vengeance) is the engine's."""
    cfg = config(body=True)
    out = []

    async def run():
        eng, h, (mira, flint, bogna, odo) = await house(d, cfg, ["Mira", "!Flint", "!Bogna", "Odo"])
        kid = new_pet(h, cfg, mira["room"], [3, 3], parent=odo["id"])
        temper(flint, honest=-0.7, kind=-0.7, generous=-0.6, brave=0.6)
        temper(bogna, honest=0.6, kind=0.3, brave=0.3)
        temper(mira, kind=0.8, brave=0.4)
        like(h, flint, bogna, -9, "Bogna laughed at my pot in front of everyone")
        like(h, bogna, flint, -5, "Flint takes the best fish")
        for n in ("blue bowl", "green cup", "reed basket"):
            thing(eng, h["rooms"][bogna["room"]], n, "bowl", "hard", bogna["id"])
        start, tpd, tph = h["tick"], cfg["ticks_per_day"], round(cfg["ticks_per_hour"])
        steps, hurt_seen, healed, killed = 0, None, None, None
        while h["tick"] - start < 7 * tpd:
            await eng.tick()
            steps += 1
            t = h["tick"] - start
            hurt = [(p["name"], p["hurt"]["level"]) for p in (flint, bogna, mira) if (p.get("hurt") or {}).get("level")]
            if hurt_seen is None and hurt:
                hurt_seen = (t, hurt)
            if hurt_seen and healed is None and not hurt:
                healed = t
            if 0.5 * tpd <= t and not hurt_seen and t % tph == 0:   # the scripted brain: anger and intent, until it comes to blows
                character.set_mood(h, cfg, flint, "angry", "Bogna mocks me", hours=6)
                flint["intent"] = {"against": bogna["id"], "how": "make her pay"}
            if hurt_seen and flint.get("intent"):
                flint.pop("intent")
                flint["mood"] = {"mood": "content", "since": h["tick"], "until": h["tick"], "why": "", "strength": 0.3}
            if hurt_seen and t % (4 * tph) == 0 and conflict.between(h, flint["id"], bogna["id"]):
                bogna["intent"] = {"against": flint["id"], "how": "make up"}
            if t == 4 * tpd:
                for p in (flint, odo, bogna):
                    p["room"], p["sleep"] = mira["room"], None
                mira["room"] = next(r for r in h["rooms"] if h["rooms"][r]["type"] and r != flint["room"] and not outdoors.is_out(r))
                was, conflict.C(cfg)["coming_down"]["step_in"] = conflict.C(cfg)["coming_down"]["step_in"], 0.0
                killed = (t, conflict.force(h, cfg, flint["id"], odo["id"], 8))
                kid["laid"] = -10 ** 6
            if killed and t == killed[0] + 40:
                conflict.C(cfg)["coming_down"]["step_in"] = was
            if killed and odo.get("buried") and not h["killings"][-1]["vigil"] and t % tph == 0 and h["clock"]["phase"] == "day":
                stone = next((r for r in h["rooms"].values() if r["type"] and any((o.get("memorial") or {}).get("pet") == odo["id"] for o in r["objects"].values())), None)
                for p in (mira, kid):   # the mourners go to the stone (their body would, by their aim)
                    if stone and not p["sleep"]:
                        p["room"] = stone["id"]
        lines = ["day %.2f  %-10s %s%s" % ((m["tick"] - start) / tpd, m["kind"], m["text"], "  [hurt]" if m.get("hurt") else "")
                 for m in h["moments"] if m["kind"] in LADDER + ("death", "sick", "well", "limp") and m["tick"] >= start]
        out.extend(lines)
        acts = [x for g in h["grievances"] + h.get("grievances_done", []) for x in g["history"] if x[2] not in ("cooled",)]
        k = (h.get("killings") or [{}])[-1]
        out.append("ticks %d (%.1f world days); first injury at day %.2f %s, healed by day %s; ladder entries %d; killing verdict %s by %s; vengeance: %s" % (
            steps, steps / tpd, (hurt_seen or (0,))[0] / tpd, (hurt_seen or (0, ""))[1], "%.2f" % (healed / tpd) if healed else "not yet", len(acts),
            k.get("verdict"), k.get("by"), [h["pets"][g["by"]]["name"] or g["by"] for g in h["grievances"] if g.get("vengeance")]))
        print("\n".join(out))
        out.clear()
        done = [g for g in h.get("grievances_done", []) if {g["by"], g["against"]} == {flint["id"], bogna["id"]}]
        open_ = conflict.between(h, flint["id"], bogna["id"])
        top = max([x[1] for g in done + open_ for x in g["history"]] or [0])
        assert top >= 5 and healed, "the feud climbed to blows (%d), and the hurt healed (%s)" % (top, healed)
        assert done or all(g["rung"] < top for g in open_), "and came down"
        assert odo["stage"] == "dead" and k.get("verdict") and any(g.get("vengeance") for g in h["grievances"]), "a killing: justice and vengeance"
        assert any(a.get("kind") == "vigil" and a["done"] for a in mira.get("aims", [])) and any(m["kind"] == "vigil" for m in h["moments"]), "grief: a vigil"
        per_day = {}
        for g in h["grievances"] + h.get("grievances_done", []):
            for x in g["history"]:
                key = (g["by"], g["against"], int((x[0] - start) // tpd))
                per_day[key] = per_day.get(key, 0) + 1
        assert max(per_day.values()) <= 24 / conflict.C(cfg)["ladder"]["act_gap_hours"] + 12, "no loops: %s" % per_day

    asyncio.run(run())
    return out


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:   # (anywhere: PET_SCRATCH when set, else the system's)
        asyncio.run(checks(d + "/a"))
        asyncio.run(switches(d + "/b"))
        print("conflict checks passed")
        if "quick" not in sys.argv:
            for line in story(d + "/c"):
                print(line)
            print("stub run passed")


if __name__ == "__main__":
    main()
