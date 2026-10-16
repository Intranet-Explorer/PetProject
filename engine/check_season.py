"""Self-check for the seasons (SPEC-v3.5 §5, §7): the rules in seasons.toml and engine/season.py, proved without a model.

    uv run python -m engine.check_season

Scripted and stub minds only, in a temp folder of its own; a few seconds."""
import asyncio
import copy
import json
import tempfile

from . import craft, feel, life, physics, season, things, wants, world
from .check import at, do, engine, scripted
from .tick import Engine
from .world import clock, generate_room, weather_of

SEASONS = ["spring", "summer", "autumn", "winter"]


def force(eng, name):
    """Hold the house in this season, as `[season] force` does."""
    eng.cfg["season"]["force"] = name
    eng.house["clock"] = clock(eng.cfg, eng.house["tick"])


def hours(eng, n, each=None):
    """Let n world hours of the slow things pass: growing, the season's bits, food going bad."""
    h, cfg = eng.house, eng.cfg
    for _ in range(n):
        h["tick"] += world.hours(cfg, 1)
        h["clock"] = clock(cfg, h["tick"])
        for fn in each or (craft.grow, season.hourly, things.upkeep):
            fn(h, cfg)


def cold(eng, pet):
    return sum(e["rate"] for e in physics.effects(eng.house, eng.cfg, pet) if e["tag"] == "cold")


async def run(d):
    cfg = world.load_config()
    cfg["make"]["charm_takes"] = []
    cfg["make"]["own_names"] = True   # (things go by their makers' names here: engine/check_hobs.py checks everyday names)
    cfg["weather"]["real"] = False

    # ---- the clock: four seasons by the world's days; one forced holds whatever the clock says; a bad name is refused ----
    assert [clock(cfg, round(dd * cfg["ticks_per_day"]))["season"] for dd in range(0, 24, 6)] == SEASONS
    cfg["season"]["force"] = "winter"
    assert {clock(cfg, round(dd * cfg["ticks_per_day"]))["season"] for dd in range(0, 30)} == {"winter"}, "a forced season holds on every day"
    assert {weather_of({"seed": 1}, cfg, dd) for dd in range(1, 80)} >= {"snow"} and "heat" not in {weather_of({"seed": 1}, cfg, dd) for dd in range(1, 80)}, "and its sky is that season's"
    bad = copy.deepcopy(cfg)
    bad["season"]["force"] = "wintr"
    try:
        season.load(bad, world.ROOT)
        raise AssertionError("a season that does not exist was taken")
    except ValueError:
        pass
    cfg["season"]["force"] = ""
    assert cfg["house"]["seasons"]["summer"]["sunset"] - cfg["house"]["seasons"]["summer"]["sunrise"] > 14 > 10 > cfg["house"]["seasons"]["winter"]["sunset"] - cfg["house"]["seasons"]["winter"]["sunrise"], "long days in summer, short in winter"

    # ---- the live house: a season is 42 world days (three and a half real days on the two-hour day, all four in two
    # weeks), and a house that lived by the six-day seasons opens in the season it was in, as far through it ----
    live = world.load_config(profile="live")
    live["weather"]["real"] = False
    real_days = live["house"]["house"]["season_days"] * live["clock"]["real_day_seconds"] / 86400
    assert 3 <= real_days <= 4 and 13 <= 4 * real_days <= 15, "a season is a few real days: %.1f" % real_days
    old, _ = engine(live, d + "/old")
    was = copy.deepcopy(live)
    was["house"]["house"]["season_days"] = live["house"]["house"]["was_season_days"]
    h = old.house
    h["tick"] = round((45 * 24 + 5.9 - 8) * live["ticks_per_hour"])   # day 46, as the live house was on 13 October 2026
    h["clock"] = clock(was, h["tick"])
    del h["season_days"]   # (a house saved before v3.5 has neither of these)
    h.pop("season_off", None)
    assert h["clock"]["day"] == 46 and h["clock"]["season"] == "winter"
    n = h["n"]["moment"]
    old.close()
    live.pop("season_off", None)
    again = Engine(live, d + "/old", scripted)
    h = again.house
    assert h["clock"]["season"] == "winter" and h["season_off"] == 270 and h["n"]["moment"] == n, "the live house keeps its winter, and nothing is said of a turn: %s" % h["clock"]
    await again.tick()
    assert h["clock"]["season"] == "winter" and h["clock"]["year"] == 2
    turns = [dd for dd in range(46, 400) if world.season_of(live, dd) != world.season_of(live, dd + 1)]
    assert turns[0] == 46 + 20 and world.season_of(live, turns[0] + 1) == "spring" and turns[1] - turns[0] == 42, "half of winter was gone, so half of the long one is left; then each season is 42 days: %s" % turns[:3]
    again.close()
    reopened = Engine(live, d + "/old", scripted)
    assert reopened.house["season_off"] == 270, "and the place it was given is kept, not worked out twice"
    reopened.close()
    live.pop("season_off", None)
    new, _ = engine(live, d + "/new")
    assert new.house["clock"]["season"] == "spring" and "season_off" not in new.house and world.season_of(live, 42) == "spring" and world.season_of(live, 43) == "summer", "a new house begins in spring"
    new.close()
    plain, _ = engine(cfg, d + "/plain")   # an old saved house on the plain clock: nothing about it moves
    del plain.house["season_days"]
    plain.house["tick"] = 5000
    plain.close()
    plain = Engine(cfg, d + "/plain", scripted)
    assert "season_off" not in plain.house and cfg["season_off"] == 0 and plain.house["season_days"] == 6
    plain.close()

    # ---- a house with a garden and a greenhouse ----
    cfg["body"]["on"] = False
    eng, pet = engine(cfg, d + "/garden")
    h = eng.house
    await eng.tick()
    at(eng, 12)
    blank = [rid for rid, r in h["rooms"].items() if not r["type"]]
    garden, glass, cellar = (generate_room(h, cfg, rid, kind) for rid, kind in zip(blank, ("garden", "greenhouse", "cellar")))
    for r in (garden, glass, cellar):
        pet["rooms"][r["id"]] = h["tick"]
    beds = lambda room: {n: o for n, o in room["objects"].items() if "fix" in o and o["fix"].get("plant")}

    def sow(grow=0.3):
        for room in (garden, glass):
            for n, o in beds(room).items():
                o["planted"] = {"what": "seed", "at": h["tick"], "grow": grow, "watered": h["tick"], "by": pet["id"], "stage": "planted"}

    # seasons switch the garden: asleep outdoors in winter while the greenhouse grows; fastest in summer
    grew = {}
    for s in SEASONS:
        force(eng, s)
        sow()
        hours(eng, 12, [craft.grow])
        grew[s] = (min(o["planted"]["grow"] for o in beds(garden).values()) - 0.3, min(o["planted"]["grow"] for o in beds(glass).values()) - 0.3)
    assert grew["winter"][0] == 0 and grew["winter"][1] > 0.05, "in winter the outdoor beds sleep and the greenhouse still grows: %s" % (grew["winter"],)
    assert grew["summer"][0] > grew["spring"][0] > grew["autumn"][0] > 0, "outdoors: fastest in summer, then spring, then autumn: %s" % grew
    force(eng, "winter")
    sow()
    hours(eng, 24 * 4, [craft.grow])   # four world days without water
    assert all(o["planted"]["dormant"] and not o["planted"].get("wilted") and o["planted"]["grow"] == 0.3 for o in beds(garden).values()), "asleep under snow it neither grows nor wilts"
    assert any("asleep under the snow" in e for _, e in pet["events"]), "and whoever planted it is told"
    pet["room"], pet["pos"] = garden["id"], [6, 4]
    name = next(iter(beds(garden)))
    craft.water(h, cfg, pet, garden, name)
    told, _, _ = craft.use_planted(h, cfg, pet, garden, name)
    assert garden["objects"][name]["planted"]["grow"] == 0.3 and "asleep under the snow" in told, "tending does not wake it: %s" % told
    assert craft.by_paw(h, pet) == 0 or not garden["objects"][name]["planted"].get("paw")
    felt = " | ".join(physics.senses(h, cfg, pet))
    assert "snow lies over the garden" in felt and "in winter (only the greenhouse grows; keep warm)" in feel.when(h), "the sleeping garden is felt, and the season's needs are said with the time: %s" % feel.when(h)
    pet["carrying"] = ["seed"]
    garden["objects"][name].pop("planted")
    plant = lambda: [c for c in wants.candidates(h, cfg, pet) if c["what"] == "plant" and c["room"] == garden["id"]]
    assert not plant(), "nobody wants to plant in earth that is asleep"
    force(eng, "spring")
    assert plant(), "... and in spring they do"
    hours(eng, 2, [craft.grow])
    assert all("dormant" not in o["planted"] and o["planted"]["grow"] > 0.3 for o in beds(garden).values() if o.get("planted")), "in spring what slept grows on"
    assert any("growing again" in e for _, e in pet["events"])

    # the seasons' own bits in the garden: flowers and seeds in spring, fallen leaves in autumn, gone with the season
    own = lambda: sorted(s["bit"] for s in garden["spots"] if s.get("season"))
    hours(eng, 1, [season.hourly])
    assert own() == ["petal", "petal", "seed", "seed"] and not any(s.get("season") for s in glass["spots"]), "spring: more flowers and seeds, under the open sky only: %s" % own()
    hours(eng, 3, [season.hourly])
    assert len(own()) == 4, "they do not pile up"
    force(eng, "summer")
    hours(eng, 1, [season.hourly])
    assert own() == []
    force(eng, "autumn")
    hours(eng, 1, [season.hourly])
    assert own() == ["fallen leaf"] * 4 and cfg["house"]["bits"]["fallen leaf"]["late"] and "fallen leaf" not in world.bit_kinds(h, cfg), "autumn: leaves fall in the garden, and nowhere else"
    r = await do(eng, pet, {"type": "gather", "what": "fallen leaf"})
    assert not r[0]["reason"] and "fallen leaf" in pet["carrying"] and "warm" in r[0]["feedback"], r
    hours(eng, cfg["house"]["rooms"]["garden"]["regrow_hours"] + 1, [season.hourly, lambda h_, c_: __import__("engine.director", fromlist=["x"]).hourly(h_, c_)])
    assert sum(1 for s in garden["spots"] if s.get("season") and s["ready"]) == 4, "picked up, a fallen leaf comes back while autumn lasts"
    pet["carrying"] = []

    # spring: an egg comes a little easier
    pet["stage"], pet["stage_at"]["adult"], pet["needs"]["energy"] = "adult", h["tick"], 50.0
    assert feel.level(pet, "energy") == 2
    force(eng, "summer")
    assert life.can_lay(h, cfg, pet) == "you are too tired to lay an egg"
    force(eng, "spring")
    assert life.can_lay(h, cfg, pet) is None, "in spring a pet a bit tired can still lay"

    # autumn: the harvest is plentiful
    picked = {}
    for s in ("summer", "autumn"):
        force(eng, s)
        sow(1.0)
        pet["last_eat"] = h["tick"]   # (it has just eaten: all of it is left lying)
        garden["spots"] = [x for x in garden["spots"] if not x["loose"]]
        craft.use_planted(h, cfg, pet, garden, name)
        picked[s] = sorted(x["bit"] for x in garden["spots"] if x["loose"])
    assert picked["summer"] == ["bean", "bean", "seed"] and picked["autumn"] == ["bean", "bean", "bean", "seed"], "one more of each food in autumn, no more seed: %s" % picked

    # ---- food keeps put away and spoils loose, slower in the cold ----
    def lay(room, where=None):
        room["spots"] = [x for x in room["spots"] if not x["loose"]]
        things.drop_bits(h, cfg, room, [6, 4], ["bean", "berry", "seed"])
        for x in room["spots"][-3:]:
            if where:
                x["on"] = where
        return room["spots"][-3:]

    F = cfg["seasons"]["food"]
    force(eng, "summer")
    n = h["n"]["moment"]
    loose, put = lay(garden), lay(h["rooms"][h["start"]], "toy chest")
    hours(eng, round(24 * F["days"]) - 2)
    assert [x["bit"] for x in loose] == ["bean", "berry", "seed"], "not yet"
    assert "will go bad" in " | ".join(physics.senses(h, cfg, pet)), "food lying loose is noticed before it goes"
    hours(eng, 3)
    assert [x["bit"] for x in loose] == ["spoiled food", "spoiled food", "seed"] and [x["bit"] for x in put] == ["bean", "berry", "seed"], "loose it spoils, a seed does not; put away it keeps: %s" % loose
    gone = [m for m in h["moments"] if m["n"] > n and m["kind"] == "spoiled"]
    assert len(gone) == 2 and "left lying in the garden went bad" in gone[0]["text"] and any("has gone bad" in e for _, e in pet["events"]), gone
    assert "sweet" not in cfg["house"]["bits"]["spoiled food"]["can"] and "spoiled food" not in F["bits"], "what is left is nothing to eat"
    hours(eng, 25)
    assert [x["bit"] for x in garden["spots"] if x["loose"]] == ["seed"], "and it is gone in a day"
    force(eng, "winter")
    loose, low = lay(garden), lay(cellar)
    hours(eng, round(24 * F["days"]) + 2)
    assert [x["bit"] for x in loose] == ["bean", "berry", "seed"], "in winter it lasts longer"
    hours(eng, round(24 * F["days"]))
    assert [x["bit"] for x in loose][:2] == ["spoiled food"] * 2 and [x["bit"] for x in low][:2] == ["bean", "berry"], "... but goes in the end; in the cellar's cold it lasts longer still"

    # ---- winter is colder: the cold rooms day and night; a warm thing is a comfort by day (and too warm in summer) ----
    pet["room"], pet["pos"] = cellar["id"], [6, 4]
    night = {}
    for s in ("autumn", "winter"):
        force(eng, s)
        at(eng, 23)
        night[s] = cold(eng, pet)
    assert night["winter"] < night["autumn"] < 0 and night["winter"] < cfg["house"]["seasons"]["winter"]["cold"], "the cellar on a winter night is colder than the season alone: %s" % night
    at(eng, 12)
    force(eng, "winter")
    day = cold(eng, pet)
    force(eng, "summer")
    assert day < 0 == cold(eng, pet) and "cold gets into you" not in " ".join(physics.senses(h, cfg, pet)), "and it is cold there by day in winter, never in summer"
    pet["room"] = h["start"]
    force(eng, "winter")
    assert cold(eng, pet) == 0, "a room that is not a cold one is no colder by day"
    pet["carrying"], pet["needs"]["energy"] = ["wax"], 90.0
    r = await do(eng, pet, {"type": "make", "recipe": {"name": "warm lump", "kind": "cushion", "material": "warm", "color": "red", "size": "medium", "purpose": "to be warm by"}, "near": "here"})
    assert not r[0]["reason"], r
    pet["pos"] = list(h["rooms"][h["start"]]["objects"]["warm lump"]["pos"])
    warm = {}
    for s in SEASONS:
        force(eng, s)
        at(eng, 12)
        e = next(e for e in physics.effects(h, cfg, pet) if e["tag"] == "warm")
        warm[s] = (e["rate"], e["feel"])
    assert warm["summer"][0] < warm["spring"][0] == warm["autumn"][0] < 0 < warm["winter"][0], "a warm thing by day: worse in summer, a comfort in winter: %s" % warm
    assert "too warm" in warm["summer"][1] and "against the winter" in warm["winter"][1] and "unpleasant" in warm["spring"][1]

    # ---- autumn: food lying loose is wanted put by, and a body can do it ----
    eng.close()
    cB = world.load_config()
    cB["make"]["own_names"] = True
    cB["weather"]["real"], cB["stub"] = False, dict(cB["stub"], paced=True)
    eB, pb = engine(cB, d + "/autumn")
    hB = eB.house
    await eB.tick()
    at(eB, 10)
    gB = generate_room(hB, cB, next(rid for rid, r in hB["rooms"].items() if not r["type"]), "garden")
    pb["room"], pb["pos"], pb["rooms"][gB["id"]] = gB["id"], [6, 4], hB["tick"]
    things.drop_bits(hB, cB, gB, [3, 4], ["bean", "bean"])
    keep = lambda: [c for c in wants.candidates(hB, cB, pb) if c["what"] == "keep"]
    force(eB, "summer")
    assert not keep(), "no such want in summer"
    force(eB, "autumn")
    assert len(keep()) == 1 and "winter is coming" in keep()[0]["text"] and "put by in something" in keep()[0]["text"], keep()
    full = {n: o["fix"].pop("store") for n, o in gB["objects"].items() if o.get("fix", {}).get("store")}
    assert "a basket or a box" in keep()[0]["text"] and season.job(hB, cB, pb, gB) is None, "with nowhere to put it, it wants somewhere"
    for n, k in full.items():
        gB["objects"][n]["fix"]["store"] = k
    pb["wants"] = [dict({k: v for k, v in keep()[0].items() if k != "weight"}, since=hB["tick"])]
    assert season.job(hB, cB, pb, gB)["job"][2:] == ["on", "tool box"] and wants.possible(hB, cB, pb, pb["wants"][0]) and not wants.met(hB, cB, pb, pb["wants"][0])
    n = hB["n"]["moment"]
    for _ in range(600):
        hB["next_event"] = 10**9
        await eB.tick()
        if pb.get("stored") and not any(w["what"] == "keep" for w in pb["wants"]):
            break
    moments = [(m["kind"], m["text"]) for m in hB["moments"] if m["n"] > n]
    assert [s.get("on") for s in gB["spots"] if s["bit"] == "bean"] == ["tool box", "tool box"], "its body put the beans in the tool box: %s" % [s for s in gB["spots"] if s["bit"] == "bean"]
    assert any(k == "stored" and "put food by in the tool box: bean, bean" in t for k, t in moments) and any(k == "want" and "put food by for the winter" in t for k, t in moments), moments
    assert not season.loose_food(cB, gB) and not keep(), "and with nothing left lying, nothing is wanted"
    hours(eB, 24 * 3, [season.hourly])
    assert sum(s["bit"] == "bean" for s in gB["spots"]) == 2, "put by, it keeps"

    # ---- a season forced on a house that was in another is said once, when the house is opened ----
    eB.close()
    cB["season"]["force"] = "winter"
    eB = Engine(cB, d + "/autumn", scripted)
    turned = [m for m in eB.house["moments"] if m["kind"] == "season"]
    assert eB.house["clock"]["season"] == "winter" and turned and turned[-1]["text"] == "winter has come", turned
    eB.close()
    eB = Engine(cB, d + "/autumn", scripted)
    assert len([m for m in eB.house["moments"] if m["kind"] == "season"]) == len(turned), "once"
    json.dumps(eB.house)
    eB.close()


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))
    print("season check passed")


if __name__ == "__main__":
    main()
