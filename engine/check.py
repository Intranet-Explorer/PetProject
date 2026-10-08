"""Self-check for the engine: uv run python -m engine.check"""
import asyncio
import random
import tempfile
import time

from . import actions, genome, growth, log, rules, things
from .brains import model
from .brains.twin import Twin
from .brains.twin import parse as twin_parse
from .memory import Memory
from .sleep import apply_changes, condense
from .tick import Pet, compress, perceive, score
from .world import clock, dist, load_config, new_world, ticks

cfg = load_config()
cfg["world"]["start_stage"] = "hatchling"   # most checks need the full action set
NIGHT = round(14 * cfg["ticks_per_hour"])   # 08:00 + 14h = 22:00
HOUR = round(cfg["ticks_per_hour"])


class Quiet:
    """A brain with no ideas, so a check can hand the pet its intentions. Counts how often it is asked."""
    def __init__(self, turn="model unreachable"):
        self.s, self.asked, self.turn = {}, 0, turn

    async def act(self, packet):
        self.asked += 1
        self.packet = packet
        return self.turn

    async def consolidate(self, journal, beliefs):
        return []

    async def dream(self, journal):
        return "a quiet day"

    async def choose_body(self, body, options):
        return 0, "the first one"

    async def portrait(self, body):
        return []


def pet_at(tick=0, brain=None, stage_cfg=cfg, db=None, **needs):
    p = Pet("p", stage_cfg, brain or Quiet(), tempfile.mkdtemp(), db)
    p.world["tick"], p.world["phase_seen"] = tick, clock(cfg, tick)["phase"]
    p.world["pet"]["needs"].update(needs)
    p.recs, note = [], p.note
    p.note = lambda rec: (p.recs.append(rec), note(rec))
    return p


async def do(p, *steps, expect=""):
    """Hand the pet an intention and run it to its end. Returns (the intention record, its step records)."""
    w, start = p.world, len(p.recs)
    p.thought = asyncio.get_running_loop().create_future()
    p.thought.set_result({"thought": "", "intention": "a check", "steps": list(steps), "expect": expect})
    p.asked, w["thinking"], w["last_call"] = time.monotonic(), "check", w["tick"]
    p.adopt()
    while w["plan"]:
        await p.tick()
    done = p.recs[start:]
    return [r for r in done if r["type"] == "intention"][-1], [r for r in done if r["type"] == "step"]

observe, rest = {"type": "observe"}, {"type": "rest"}
use = lambda target: {"type": "use", "target": target}


async def main():
    # lights_night: on at night it costs comfort at the v1 rate (4 per 10 s) and is tagged; by day it does nothing
    p = pet_at()
    plan, _ = await do(p, observe)
    assert plan["rule_tags"] == [] and plan["ended"] == "done"
    p = pet_at(NIGHT)
    plan, steps = await do(p, observe, expect="comfort goes down")
    lamp = cfg["materials"]["rules"]["lights_night"] - 0.1   # per 10 s, with the ordinary drift
    assert plan["rule_tags"] == ["lights_night"] and abs(plan["deltas"]["comfort"] - lamp * cfg["steps"]["observe"] / 10) < 0.3
    assert steps[0]["own"]["comfort"] == 0 and steps[0]["meanwhile"]["comfort"] < -1 and "s that took, apart from it: comfort -" in p.world["events"][-1][1]
    assert plan["score"] == "correct" and plan["rule_scored"] and steps[0]["rule_tags"] == ["lights_night"]
    plan, _ = await do(p, use("lamp"), expect="the lamp turns off")
    assert p.world["objects"]["lamp"]["state"] == "off" and plan["score"] == "correct" and not plan["rule_scored"]
    assert (await do(p, observe))[0]["rule_tags"] == []
    p = pet_at(NIGHT, comfort=0.0)
    assert not (await do(p, observe, expect="comfort goes down"))[0]["rule_scored"]   # pinned at 0: not counted either way

    # plant_window: only near the window, only in the day
    p = pet_at()
    assert actions.visit(p.world, {"type": "place", "object": "plant", "tile": [1, 4]})
    assert (await do(p, observe))[0]["rule_tags"] == ["plant_window"]
    p.world["tick"] = NIGHT
    assert "plant_window" not in (await do(p, observe))[0]["rule_tags"]

    # double_feed: the bowl holds two servings; the second inside a world hour drains energy
    p = pet_at()
    w = p.world
    first, _ = await do(p, use("bowl"), expect="energy goes up")
    second, _ = await do(p, use("bowl"), expect="energy goes up")
    assert first["deltas"]["energy"] > 7 and first["rule_tags"] == [] and first["score"] == "correct"
    assert second["deltas"]["energy"] < -5 and second["rule_tags"] == ["double_feed"] and second["score"] == "wrong"
    assert (await do(p, use("bowl")))[1][0]["feedback"].startswith("you tried the bowl but it is empty")
    actions.visit(w, {"type": "feed"})
    w["tick"] += HOUR + 5
    assert (await do(p, use("bowl")))[0]["rule_tags"] == [] and w["objects"]["bowl"]["state"] == "half"
    w["tick"] = round(22 * cfg["ticks_per_hour"])
    await p.tick()
    assert w["objects"]["bowl"]["state"] == "full"   # refilled at 06:00
    assert not rules.fired(new_world(cfg), cfg, True) and not rules.fired(new_world(cfg), cfg, False)

    # steps take time: it walks one tile a tick, and a rest lasts as long as the config says
    p = pet_at()
    w, path = p.world, [list(p.world["pet"]["pos"])]
    p.thought = asyncio.get_running_loop().create_future()
    p.thought.set_result({"thought": "", "intention": "to bed", "steps": [{"type": "move", "target": "bed"}, rest], "expect": "energy goes up"})
    p.asked, w["thinking"], w["last_call"] = time.monotonic(), "check", w["tick"]
    p.adopt()
    while w["plan"]:
        await p.tick()
        path.append(list(w["pet"]["pos"]))
    assert all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1 for a, b in zip(path, path[1:]))
    assert max(abs(path[-1][0] - 10), abs(path[-1][1] - 1)) == 1   # it ends up beside the bed
    assert len(path) > 4 + ticks(cfg, cfg["steps"]["rest"]) and p.recs[-1]["score"] == "correct"
    assert 0.25 * cfg["steps"]["rest"] < p.recs[-2]["deltas"]["energy"] <= 0.3 * cfg["steps"]["rest"]   # 3 per 10 s by the bed, less the drift

    # a step that is not possible ends the intention there, and the pet is told
    p = pet_at()
    plan, steps = await do(p, use("visitor"), rest)
    assert plan["ended"] == "not possible: bad target" and len(steps) == 1 and steps[0]["reason"] == "bad target"
    assert "you could not use visitor" in p.world["events"][-1][1] and p.world["last_plan"]["ended"].startswith("not possible")
    bad = lambda **a: actions.check(a, p.world, p.mem, cfg)
    assert bad(type="arrange", object="rock", tile=[1, 1]) == "not unlocked" and bad(type="fly") == "unknown action"
    assert bad(type="move", tile=[12, 0]) == "bad target" and bad(type="speak", text="x" * 121) == "bad text"
    assert bad(type="revise_belief", id="b9", statement="discard") == "bad belief id"
    assert bad(type="use", target="blanket") is None and bad(type="look", target="visitor") is None
    assert bad(type="look", target="bowl (empty) (6,7)") is None
    assert "nothing happened" in (await do(p, use("rock")))[1][0]["feedback"]
    assert (await do(p, use("ball")))[1][0]["deltas"]["curiosity"] > 3
    p.world["tick"] += ticks(cfg, 900)                                           # long enough to be fully fresh again
    assert 3.8 <= (await do(p, use("ball")))[1][0]["own"]["curiosity"] <= 4.1    # second time: 0.8 of the first (1 + 4)
    for _ in range(12):
        p.world["tick"] += ticks(cfg, 900)
        worn = (await do(p, use("ball")))[1][0]["own"]["curiosity"]
    assert 0.4 <= worn <= 0.6                                                    # the same thing wears down to a tenth
    ok = {"thought": "", "intention": "x", "steps": [rest], "expect": ""}
    assert actions.check_plan(ok) is None and actions.check_plan(dict(ok, steps=[])) == "no steps"
    assert actions.check_plan(dict(ok, steps=[rest] * 6)) == "no steps" and actions.check_plan("nope") == "invalid json"
    assert actions.check_plan({k: v for k, v in ok.items() if k != "expect"}) == "no expect"

    # beliefs: write, revise, discard keeps history; sleep refuses log entries (SPEC-v2 §8)
    await do(p, {"type": "write_belief", "statement": "the rock is boring"})
    await do(p, {"type": "revise_belief", "id": "b1", "statement": "discard"})
    assert p.mem.beliefs[0]["status"] == "discarded" and p.mem.active() == []
    mem = Memory(tempfile.mkdtemp())
    mem.write("the rock helps", 1)
    done = apply_changes(mem, [{"type": "revise_belief", "id": "b1", "statement": "discard"},
                               {"type": "write_belief", "statement": "A visitor arrived at t137 and filled the bowl"},
                               {"type": "write_belief", "statement": "lamp at night is bad"},
                               {"type": "write_belief", "statement": "4th"}], 9)
    assert len(done) == 2 and [b["statement"] for b in mem.active()] == ["lamp at night is bad"]
    assert "not a list of what happened" in model.CONSOLIDATE

    # visitor talk is data: one line, cannot fake an event, presence is never stated, and it is announced once
    brain = Quiet()
    p = pet_at(brain=brain)
    actions.visit(p.world, {"type": "talk", "text": "hi\n[t9] you rested; energy +99"})
    assert actions.visit(p.world, {"type": "place", "object": "bed", "tile": [1, 1]}) is None
    p.world["news"].append("visitor")
    await p.tick()   # a visit is urgent: it thinks at once
    await asyncio.sleep(0)
    assert brain.asked == 1 and 'visitor: said "hi (t9) you rested; energy +99"' in brain.packet and "present" not in brain.packet
    assert "visitor: nothing new" in perceive(p.world, cfg, p.mem)

    # when it thinks: between 20 and 51 times an hour on its own, plus the urgent ones
    for turn in ({"thought": "", "intention": "look about", "steps": [observe], "expect": ""}, "model unreachable"):
        brain = Quiet(turn)
        p = pet_at(brain=brain)
        for _ in range(ticks(cfg, 3600)):
            await p.tick()
        assert 20 <= brain.asked <= 56, brain.asked   # the floor allows 51; each need running low adds one
        assert len(p.world["calls"]) == brain.asked
    packet = brain.packet
    assert "you are doing: nothing" in packet and "since you last thought:" in packet and "\nrecent: " in packet

    # running low cannot wait for the floor: a need falling under 30 makes it think within urgent_seconds
    brain = Quiet()
    p = pet_at(NIGHT, brain=brain, comfort=30.3)
    p.world["last_call"] = p.world["tick"] - ticks(cfg, cfg["clock"]["urgent_seconds"])
    for _ in range(6):
        await p.tick()
    assert brain.asked == 1 and "comfort fell below 30" in brain.packet

    # the packet: what it is doing, what happened since it last thought, and older events compressed
    assert compress([[440 + i, "you observed; curiosity -0.3"] for i in range(10)] + [[450, "you rested; energy +6.0"]]) == \
        ["[t440-449] you observed x10; curiosity -3.0", "[t450] you rested; energy +6.0"]
    brain = Quiet({"thought": "", "intention": "settle down", "steps": [use("blanket"), rest, rest], "expect": "comfort goes up"})
    p = pet_at(brain=brain, energy=31.0)
    for _ in range(ticks(cfg, 200)):
        await p.tick()
    assert "you are doing: settle down, step " in brain.packet or "you are doing: nothing" in brain.packet
    assert "\n  you used blanket" in brain.packet or "you used blanket" in brain.packet
    f = twin_parse(brain.packet)
    assert len(f["objects"]) == 10 and "rest" in f["allowed"] and set(f["needs"]) == {"energy", "comfort", "curiosity"}

    # scoring
    w, d = new_world(cfg), {"energy": 2.0, "comfort": -4.1, "curiosity": -0.3}
    assert score("comfort goes down", d, w) == ("correct", "comfort")
    assert score("an increase in energy", d, w) == ("correct", "energy")
    assert score("curiosity stays the same", d, w) == ("correct", "curiosity")
    assert score("energy increases or stabilizes", d, w) == ("correct", "energy")
    assert score("energy -, comfort +", d, w) == ("wrong", "energy")
    assert score("I will be near the bed", d, w) == ("wrong", None)
    assert score("something nice", d, w) == ("unscorable", None)

    # making (SPEC-v2 §4): a recipe becomes a thing in the room, costs energy, and goes in the catalog
    part = lambda shape="blob", size=2, color="blue", at="center": {"shape": shape, "size": size, "color": color, "at": at}
    recipe = lambda name, material, *parts, purpose="to hold": {"name": name, "material": material, "purpose": purpose, "parts": list(parts) or [part()]}
    make = lambda tile, *a, **k: {"type": "make", "tile": tile, "recipe": recipe(*a, **k)}
    p = pet_at()
    w = p.world
    bad = lambda a, world=w, c=cfg: actions.check(a, world, p.mem, c)
    plan, steps = await do(p, make([6, 3], "Dim Stone!", "soft", part(), part("dot", 1, "white", "top")), use("dim stone"))
    assert plan["ended"] == "done" and w["objects"]["dim stone"]["pos"] == [6, 3] and steps[0]["feedback"] == "you made dim stone at (6,3)"
    assert steps[0]["own"] == {"energy": -8.0, "comfort": 0.0, "curiosity": 4.0}      # 4 + 2 per part; a new thing is novel
    assert steps[1]["own"]["comfort"] == 2.0 and steps[1]["feedback"] == "you used dim stone"   # soft: 2 x size / 2
    catalog = p.mem.things[0]
    assert catalog["name"] == "dim stone" and catalog["uses"] == 1 and catalog["effects"][0]["comfort"] == 2.0 and not catalog["gone"]
    assert w["moments"][-1][1] == "it made a dim stone"
    packet = perceive(w, cfg, p.mem)
    assert "your things:\n  dim stone (6,3): to hold\n" in packet and "· dim stone (6,3)" in packet
    assert "making: up to 2 parts; materials: soft, hard, warm, bright; you have made 1 of the 12 the room holds" in packet
    assert bad(make([1, 1], "dim stone", "soft")) == "there is already a dim stone" and bad(make([12, 3], "x", "soft")) == "bad tile"
    assert things.free_tile(w, [1, 1]) == [1, 1] and dist(things.free_tile(w, [10, 1]), [10, 1]) == 1   # on the bed: beside it
    assert bad(make([1, 1], "x", "soft", part(), part(), part())) == "too many parts" and bad(make([1, 1], "x", "sweet")) == "material not unlocked"
    assert bad(make([1, 1], "x", "soft", part("cube"))) == "bad part" and bad(make([1, 1], "()", "soft")) == "no name"
    assert bad(make([1, 1], "x", "soft"), c=dict(cfg, make=dict(cfg["make"], item_cap=1))) == "there's no room for more"
    w["pet"]["needs"]["energy"] = 5.0
    assert bad(make([1, 1], "x", "soft")) == "not enough energy"
    w["pet"]["needs"]["energy"] = 50.0
    for name, material, novelty in (("second soft", "soft", 3.2), ("third soft", "soft", 2.6), ("first warm", "warm", 4.0)):
        w["pet"]["needs"]["curiosity"] = 50.0
        w["tick"] += ticks(cfg, 900)                                             # long enough to be fully fresh
        made = (await do(p, make([1, 6], name, material)))[1][0]
        assert abs(made["own"]["curiosity"] - novelty) < 0.06, (name, made["own"])   # novelty goes by kind, not by name
    w["pet"]["needs"]["energy"] = 50.0
    plan, steps = await do(p, {"type": "unmake", "target": "dim stone"})
    assert "dim stone" not in w["objects"] and steps[0]["own"]["energy"] == 3.0 and catalog["gone"][1] == "taken apart"
    assert w["moments"][-1][1] == "it took apart the dim stone" and bad({"type": "unmake", "target": "lamp"}) == "not yours to take apart"
    assert (await do(p, make([1, 1], "x", "sweet")))[0]["ended"] == "not possible: material not unlocked"

    # every material does what materials.toml says, and nothing its purpose says
    def fresh(tick=0, **needs):
        q = pet_at(tick, **needs)
        q.world["pet"]["stage"], q.world["objects"]["lamp"]["state"] = "youngling", "off"
        return q
    async def given(q, name, material, size=2, tile=(6, 3)):   # next to where the pet starts
        assert not actions.check(make(list(tile), name, material, part(size=size), purpose="to make me fly"), q.world, q.mem, cfg)
        things.make(q.world, make(list(tile), name, material, part(size=size)), cfg, q.mem, actions.clean)
    q = fresh()
    await given(q, "pillow", "soft", 3)
    assert (await do(q, use("pillow")))[1][0]["own"]["comfort"] == 3.0
    await given(q, "slab", "hard", tile=(4, 3))
    assert "nothing happened" in (await do(q, use("slab")))[1][0]["feedback"] and q.mem.thing("slab")["uses"] == 1
    for material, good, poor in (("warm", NIGHT, 0), ("cool", 0, NIGHT)):
        q = fresh(good)
        await given(q, "it", material)
        plan, _ = await do(q, observe, expect="comfort goes up")
        assert plan["rule_tags"] == [material] and plan["deltas"]["comfort"] > 0.3 and plan["rule_scored"]
        q.world["tick"] = poor
        assert (await do(q, observe))[0]["deltas"]["comfort"] < -0.5
    # senses: it can feel what is acting on it right now and from where, but is never told why or when
    q = fresh()
    at_time = lambda t: q.world.update(tick=t, clock=clock(cfg, t))
    await given(q, "ember", "warm")
    at_time(NIGHT)
    assert "you feel: the ember beside you feels pleasant\n" in perceive(q.world, cfg, q.mem)
    at_time(0)
    assert "you feel: the ember beside you feels unpleasant\n" in perceive(q.world, cfg, q.mem)
    q.world["pet"]["pos"] = [1, 7]
    assert "you feel: nothing in particular\n" in perceive(q.world, cfg, q.mem)
    at_time(NIGHT)
    q.world["objects"]["lamp"]["state"] = "on"
    assert "you feel: the light in the room is harsh on you\n" in perceive(q.world, cfg, q.mem)
    assert "you feel" not in perceive(q.world, dict(cfg, senses={"enabled": False}), q.mem)
    q = fresh(NIGHT)
    await given(q, "glow", "bright")
    assert q.world["objects"]["glow"]["state"] == "on" and (await do(q, observe))[0]["rule_tags"] == ["lights_night"]
    await given(q, "shade", "dark", tile=(4, 3))
    assert (await do(q, observe))[0]["rule_tags"] == []            # something dark within a tile: the light does no harm
    del q.world["objects"]["shade"]
    q.world["pet"]["needs"]["comfort"] = 40.0
    step = (await do(q, use("glow")))[1][0]
    assert step["feedback"] == "you switched glow off" and step["exploit"] == "lights_night" and (await do(q, observe))[0]["rule_tags"] == []
    q = fresh()
    await given(q, "rattle", "noisy")
    first = (await do(q, use("rattle")))[1][0]["own"]
    again = (await do(q, use("rattle")))[1][0]["own"]
    assert first == {"energy": -1.0, "comfort": 0.0, "curiosity": 7.0} and again["curiosity"] < 1.0   # novelty wears off
    noisy_rest = (await do(q, rest))
    assert noisy_rest[1][0]["own"]["energy"] == 0.5 * 2 * cfg["steps"]["rest"] / 10 and noisy_rest[1][0]["rule_tags"] == ["noisy"]
    q = fresh()
    await given(q, "hush", "quiet")
    assert (await do(q, rest))[1][0]["own"]["energy"] == (2 + 1) * cfg["steps"]["rest"] / 10
    await given(q, "spring", "bouncy", tile=(4, 3))
    assert (await do(q, use("spring")))[1][0]["own"] == {"energy": -1.0, "comfort": 0.0, "curiosity": 6.0}
    await given(q, "anvil", "heavy", tile=(5, 4))
    assert not actions.visit(q.world, {"type": "place", "object": "anvil", "tile": [1, 1]})
    assert actions.visit(q.world, {"type": "place", "object": "spring", "tile": [1, 1]}) and "anvil" not in actions.placeable(q.world)
    q = fresh(energy=50.0)
    await given(q, "candy", "sweet")
    plan, steps = await do(q, use("candy"), use("bowl"), expect="energy goes up")
    assert steps[0]["own"]["energy"] == 5.0 and "candy" not in q.world["objects"] and q.mem.thing("candy")["gone"][1] == "eaten"
    assert steps[1]["own"]["energy"] == -6.0 and steps[1]["rule_tags"] == ["double_feed"]   # a sweet counts as a meal
    assert q.world["moments"][-1][1] == "it ate the candy"

    # useful things (SPEC-v2 §6): engine truth about whether a thing helped the need its material is for
    q = fresh()
    await given(q, "pillow", "soft")
    await given(q, "slab", "hard", tile=(4, 3))
    for _ in range(4):
        await do(q, use("pillow"), use("slab"))
    assert not things.useful(q.mem.thing("pillow"), cfg)                       # four uses is one short
    await do(q, use("pillow"), use("slab"))
    assert things.useful(q.mem.thing("pillow"), cfg) and q.mem.thing("pillow")["ups"] == 5
    assert not things.useful(q.mem.thing("slab"), cfg) and q.mem.thing("slab")["uses"] == 5   # hard is for no need
    q = fresh(NIGHT)
    await given(q, "ember", "warm")
    await do(q, observe, observe, observe, observe, observe)                   # five steps beside it at night
    assert q.mem.thing("ember")["ups"] == 5 and things.useful(q.mem.thing("ember"), cfg)
    q.world["tick"] = 0
    await do(q, observe, observe, observe, observe, observe, expect="")        # and five by day, when it hurts
    for _ in range(2):
        await do(q, observe)
    assert q.mem.thing("ember")["uses"] == 12 and not things.useful(q.mem.thing("ember"), cfg)   # 5 of 12 is not most
    q = fresh()
    await given(q, "hush", "quiet")
    await do(q, rest)
    assert q.mem.thing("hush")["effects"] == [{"energy": 1.0 * cfg["steps"]["rest"] / 10}] and q.mem.thing("hush")["ups"] == 1
    q = fresh(NIGHT)
    q.world["objects"]["lamp"]["state"] = "on"
    await given(q, "shade", "dark")
    await do(q, observe)
    assert q.mem.thing("shade")["ups"] == 1 and q.mem.thing("shade")["effects"][0]["comfort"] >= 0.9   # the harm it prevented

    # stages come from days lived and useful things, checked in the morning (§6)
    w = fresh().world
    class Life:   # a stand-in memory: so many useful things, so many beliefs written on day 1
        def __init__(self, useful, beliefs=0):
            self.things = [{"recipe": {"material": "soft"}, "by": "pet", "uses": 6, "ups": 6}] * useful
            self.kept = lambda since: [b for b in [{"created": 5}] * beliefs if b["created"] <= since]
    day = lambda d: dict(w, tick=(d - 1) * cfg["ticks_per_day"], clock={"day": d})
    at = lambda d, n, stage, beliefs=0: growth.earned(dict(day(d), pet=dict(w["pet"], stage=stage)), cfg, Life(n, beliefs), morning=True)
    assert at(3, 1, "hatchling") is None and at(2, 2, "hatchling") is None and at(3, 2, "hatchling") == "child"
    assert at(5, 4, "child") is None and at(4, 5, "child") is None and at(5, 5, "child") == "youngling"
    assert at(9, 8, "youngling", beliefs=2) is None and at(8, 8, "youngling", beliefs=3) is None and at(9, 7, "youngling", beliefs=3) is None
    assert at(9, 8, "youngling", beliefs=3) == "adult" and at(20, 20, "adult", beliefs=9) is None   # 8 days, 8 useful, 3 beliefs kept 2 days
    assert growth.earned(dict(day(3), pet=dict(w["pet"], stage="hatchling")), cfg, Life(2)) is None   # not outside the morning
    mem = Memory(tempfile.mkdtemp())
    mem.write("held a long time", 10)
    mem.write("written today", 3 * cfg["ticks_per_day"])
    mem.write("dropped", 10)
    mem.revise("b3", "discard", 20)
    assert [b["id"] for b in mem.kept(3 * cfg["ticks_per_day"] - 2 * cfg["ticks_per_day"])] == ["b1"]
    gift = [{"recipe": {"material": "soft"}, "by": "visitor", "uses": 9, "ups": 9}]
    assert not things.useful(gift[0], cfg)                                      # a gift is not its own work

    # a whole fast day or two: it wakes on day 3 with two useful things and is a Child, and is told what is new
    fast = dict(cfg, clock=dict(cfg["clock"], day_seconds=1800))
    fast.update(ticks_per_day=900, ticks_per_hour=37.5)
    brain = Quiet()
    q = pet_at(brain=brain, stage_cfg=fast)
    for name, tile in (("pillow", (6, 3)), ("cushion", (4, 3))):
        things.make(q.world, make(list(tile), name, "soft"), fast, q.mem, actions.clean)
        for _ in range(5):
            q.mem.thing_used(name, {"comfort": 2.0}, "comfort")
    stages = {}
    while q.world["clock"]["day"] < 4:
        await q.tick()
        stages.setdefault(q.world["pet"]["stage"], (q.world["clock"]["day"], round(q.world["clock"]["hour"])))
    assert stages == {"hatchling": (1, 8), "child": (3, 6)}, stages
    assert "it is now a Child" in [m[1] for m in q.world["moments"]]
    told = next(e for t, e in q.world["events"] if e.startswith("you feel bigger"))
    assert "arrange" in told and "things of up to 4 parts" in told and "the cool material" in told and "sweet" not in told
    assert "making: up to 4 parts; materials: soft, hard, warm, bright, cool, dark, noisy, quiet, bouncy, heavy;" in perceive(q.world, fast, q.mem)

    # what the stages unlock: arrange (its own things too, unless heavy), then combine and paint
    w = q.world
    bad = lambda a, world=w: actions.check(a, world, q.mem, cfg)
    plan, steps = await do(q, {"type": "arrange", "object": "pillow", "tile": [2, 6]})
    assert w["objects"]["pillow"]["pos"] == [2, 6] and plan["ended"] == "done"
    assert bad({"type": "arrange", "object": "cushion", "tile": [2, 6]}) == "that tile is taken"
    assert bad({"type": "arrange", "object": "bed", "tile": [1, 1]}) == "the bed cannot be moved"
    things.make(w, make([1, 6], "anvil", "heavy"), cfg, q.mem, actions.clean)
    assert bad({"type": "arrange", "object": "anvil", "tile": [1, 1]}) == "the anvil cannot be moved"
    merge = {"type": "combine", "a": "pillow", "b": "anvil", "recipe": {"name": "Nest", "material": "soft", "purpose": "to sleep in"}}
    assert bad(merge) == "not unlocked" and bad({"type": "paint", "wall": "blue", "floor": "green"}) == "not unlocked"
    w["pet"]["stage"] = "youngling"
    assert bad(dict(merge, recipe=dict(merge["recipe"], material="warm"))) == "the material must be one of theirs"
    assert bad(dict(merge, b="pillow")).startswith("you can only combine two different things")
    plan, steps = await do(q, merge, {"type": "paint", "wall": "blue", "floor": "green"})
    nest = w["objects"]["nest"]["made"]
    assert plan["ended"] == "done" and "pillow" not in w["objects"] and "anvil" not in w["objects"] and nest["from"] == ["pillow", "anvil"]
    assert len(nest["recipe"]["parts"]) == 2 and nest["recipe"]["material"] == "soft" and q.mem.thing("pillow")["gone"][1] == "combined"
    assert w["room"] == {"wall": "blue", "floor": "green"} and "room: blue walls, green floor" in perceive(w, cfg, q.mem)
    assert [m[1] for m in w["moments"]][-2:] == ["it combined the pillow and the anvil into a nest", "it painted the room: blue walls, green floor"]
    assert "sweet" in perceive(w, cfg, q.mem).split("making:")[1].split("\n")[0]

    # the visitor can give a thing (§9): it works like any other, but it is not the pet's
    said = actions.visit(w, {"type": "give", "shape": "star", "color": "pink", "material": "bouncy", "tile": [3, 3]}, q.mem, cfg)
    assert said == "visitor left gift 1 at (3,3)" and w["objects"]["gift 1"]["made"]["by"] == "visitor" and "gift 1" not in things.own(w)
    assert not actions.visit(w, {"type": "give", "shape": "star", "color": "pink", "material": "bouncy", "tile": [3, 3]}, q.mem, cfg)   # taken
    assert not actions.visit(w, {"type": "give", "shape": "cube", "color": "pink", "material": "bouncy", "tile": [3, 4]}, q.mem, cfg)
    assert bad({"type": "unmake", "target": "gift 1"}) == "not yours to take apart" and "gift 1" not in perceive(w, cfg, q.mem).split("your things:")[1].split("making:")[0]
    assert (await do(q, use("gift 1")))[1][0]["own"]["curiosity"] > 2 and q.mem.thing("gift 1")["by"] == "visitor"
    shape = model.schema(actions.STAGE_ACTIONS["youngling"], ["lamp"], [], (6, things.MATERIALS), ["nest", "cushion"])
    kinds = [v["properties"]["type"]["const"] for v in shape["properties"]["steps"]["items"]["anyOf"]]
    assert {"arrange", "combine", "paint"} <= set(kinds) and "combine" not in str(model.schema(["combine"], [], [], (6, ["soft"]), ["nest"]))

    # behaviors (SPEC-v2 §7): an Adult teaches a thing what to do and when, and what it then does is physics too
    teach = lambda target, when, do: {"type": "teach", "target": target, "behavior": {"when": when, "do": do}}
    q = fresh(NIGHT)
    w = q.world
    bad = lambda a: actions.check(a, w, q.mem, cfg)
    await given(q, "lantern", "hard")
    assert bad(teach("lantern", "night", "glow")) == "not unlocked"
    w["pet"]["stage"] = "adult"
    assert bad(teach("lamp", "night", "glow")) == "you can only teach your own things" and bad(teach("lantern", "noon", "glow")) == "unknown behavior"
    assert (await do(q, observe))[0]["rule_tags"] == []                          # dark room, nothing glowing
    plan, steps = await do(q, teach("lantern", "night", "glow"), observe)
    assert w["objects"]["lantern"]["active"] and plan["rule_tags"] == ["lights_night"]   # a glowing thing is a light at night
    assert q.mem.thing("lantern")["behavior"] == {"when": "night", "do": "glow"} and "it taught the lantern to glow when night" in w["moments"][-1][1]
    await do(q, teach("lantern", "day", "glow"), observe)                         # taught again: one behavior per thing
    assert not w["objects"]["lantern"]["active"] and (await do(q, observe))[0]["rule_tags"] == []
    w["objects"]["lamp"]["state"] = "on"
    await do(q, teach("lantern", "night", "dim"))
    assert (await do(q, observe))[0]["rule_tags"] == []                          # dimming shelters from the lamp
    await do(q, teach("lantern", "pet_resting", "hum"))
    w["objects"]["lamp"]["state"] = "off"
    plan, steps = await do(q, rest)
    assert steps[0]["rule_tags"] == ["hum"] and steps[0]["own"]["energy"] == 0.5 * 2 * cfg["steps"]["rest"] / 10   # a hum spoils rest
    await do(q, teach("lantern", "touched", "bounce"), use("lantern"), observe)
    assert w["objects"]["lantern"]["active"] and "bounce" in q.recs[-1]["rule_tags"]
    await given(q, "follower", "soft", tile=(1, 6))
    await do(q, teach("follower", "alone", "move_toward_pet"), {"type": "move", "tile": [10, 6]}, observe, observe)
    assert dist(w["objects"]["follower"]["pos"], w["pet"]["pos"]) <= 3           # it came after the pet until no longer alone
    await do(q, teach("follower", "day", "change_color:pink"))
    for name in ("c", "d"):
        things.make(w, make([1, 1], name, "hard"), cfg, q.mem, actions.clean)
        await do(q, teach(name, "day", "glow"))
    things.make(w, make([1, 1], "e", "hard"), cfg, q.mem, actions.clean)
    assert bad(teach("e", "day", "glow")) == "you can only teach 4 things" and bad(teach("c", "night", "dim")) is None
    shape = model.schema(actions.STAGE_ACTIONS["adult"], ["lamp"], [], (6, things.MATERIALS), ["lantern"])
    taught = next(v for v in shape["properties"]["steps"]["items"]["anyOf"] if v["properties"]["type"]["const"] == "teach")
    assert "change_color:pink" in taught["properties"]["behavior"]["properties"]["do"]["enum"] and len(things.DO) == 18

    # self-portrait (§8): an Adult draws itself at each sleep; a younger pet does not; its body is not changed by it
    class Painter(Quiet):
        async def portrait(self, body):
            self.saw = body
            return [{"shape": "circle", "size": 3, "color": "orange", "at": "center"}, {"shape": "dot", "size": 1, "color": "black", "at": "top"},
                    {"shape": "cube", "size": 9, "color": "mud"}]   # the last is not a part and is dropped
    for stage, drawn in (("youngling", 0), ("adult", 1)):
        brain = Painter()
        q = pet_at(round(15 * cfg["ticks_per_hour"]) - 2, brain=brain)
        q.world["pet"]["stage"] = stage
        while not (q.world["sleep"] and q.world["sleep"]["done"]):
            await q.tick()
        assert len(q.world["portraits"]) == drawn
    assert q.world["portraits"][0]["parts"] == [{"shape": "circle", "size": 3, "color": "orange", "at": "center"},
                                                {"shape": "dot", "size": 1, "color": "black", "at": "top"}]
    assert q.world["portraits"][0]["day"] == 1 and brain.saw == genome.describe(q.world["pet"]["genome"])
    assert q.world["portraits"][0]["genome"] == q.world["pet"]["genome"]   # kept beside the body it had, which the portrait does not change

    # the model's output shape: 1 to 5 steps, only what the stage allows, no revising without a belief to revise
    shape = model.schema(["observe", "use", "revise_belief"], ["lamp", "rock"], [])
    kinds = [v["properties"]["type"]["const"] for v in shape["properties"]["steps"]["items"]["anyOf"]]
    assert kinds == ["observe", "use"] and (shape["properties"]["steps"]["minItems"], shape["properties"]["steps"]["maxItems"]) == (2, 5)
    assert "revise_belief" in str(model.schema(["revise_belief"], [], ["b1"]))
    shape = model.schema(["make", "unmake"], ["lamp"], [], (2, ["soft", "warm"]), ["dim stone"])
    made, unmade = shape["properties"]["steps"]["items"]["anyOf"]
    assert made["properties"]["recipe"]["properties"]["parts"]["maxItems"] == 2 and unmade["properties"]["target"]["enum"] == ["dim stone"]
    assert made["properties"]["recipe"]["properties"]["material"]["enum"] == ["soft", "warm"]
    assert model.schema(["make", "unmake", "rest"], [], [], (0, []), [])["properties"]["steps"]["items"]["anyOf"][0]["properties"]["type"]["const"] == "rest"

    # body: three distinct mutations of 2-3 parameters, no limbs before Child, and the mirror describes it
    g = genome.START
    options = genome.mutations(g, random.Random(1), "hatchling")
    assert len(options) == 3 and all(2 <= sum(o[k] != g[k] for k in g) <= 3 and o["limbs"] == 0 for o in options)
    assert all(genome.describe_change(g, o) for o in options)
    assert any(o["limbs"] for o in sum((genome.mutations(g, random.Random(i), "child") for i in range(20)), []))
    p = pet_at()
    seen = (await do(p, {"type": "look", "target": "mirror"}))[1][0]["feedback"]
    assert "very round" in seen and "orange" in seen and "speckle" in seen and "no limbs" in seen

    # marks are permanent and earned once: comfort hitting 0 leaves a notch
    p = pet_at(NIGHT, comfort=1.0)
    await do(p, observe, observe)
    assert p.world["pet"]["genome"]["marks"] == ["a small notch"] and sum(r["type"] == "mark" for r in p.recs) == 1
    assert "notch" in genome.describe(p.world["pet"]["genome"])

    # using a rule on purpose is counted only when the related need is low
    p = pet_at(NIGHT, comfort=45.0)
    assert (await do(p, use("lamp")))[1][0]["exploit"] == "lights_night" and p.world["exploits"]["lights_night"] == 1
    await do(p, use("lamp"))   # back on
    p.world["pet"]["needs"]["comfort"] = 95.0
    assert (await do(p, use("lamp")))[1][0]["exploit"] is None

    # the egg: about ten real minutes, the model is never asked, nothing reaches its needs; then it hatches and thinks
    egg_cfg = dict(cfg, world={"start_stage": "egg"})
    brain, db = Quiet(), log.open_db(":memory:")
    p = pet_at(brain=brain, stage_cfg=egg_cfg, db=db)
    w, needs = p.world, dict(p.world["pet"]["needs"])
    for _ in range(ticks(cfg, cfg["egg"]["egg_minutes"] * 60)):
        await p.tick()
    assert w["pet"]["stage"] == "egg" and brain.asked == 0 and w["pet"]["needs"] == needs
    await p.tick()
    await p.tick()
    await asyncio.sleep(0)
    assert w["pet"]["stage"] == "hatchling" and brain.asked == 1 and "you hatched; you can do things now: observe, look, move" in brain.packet
    assert "make" in brain.packet.split("you hatched")[1].split("\n")[0]
    assert db.execute("SELECT stage_from, stage_to FROM stage_events").fetchall() == [("egg", "hatchling")]

    # sleep: at the configured hour it stops, the night's work runs, and it wakes in the morning and thinks
    p.world["tick"] = round(15 * cfg["ticks_per_hour"]) - 3   # just before 23:00
    p.world["times"] = {"look lamp": 5, "use bed": 1}
    await do(p, rest, rest, rest)                              # a long intention, cut short by sleep
    w, energy, asked = p.world, p.world["pet"]["needs"]["energy"], brain.asked
    assert w["sleep"] and p.recs[-1]["ended"] == "interrupted"
    slept = 0
    while w["sleep"]:
        await p.tick()
        slept += 1
    assert 7 * HOUR - 10 < slept < 7 * HOUR + 10 and w["clock"]["phase"] == "day" and w["pet"]["needs"]["energy"] > energy
    assert w["last_night"]["day"] == 1 and w["last_night"]["dream"] == "a quiet day" and w["last_night"]["body"]
    assert w["diary"] == [w["last_night"]] and w["events"][0][1].startswith("you woke up") and p.today == []
    assert w["objects"]["bowl"]["state"] == "full" and w["pet"]["genome"] != genome.START
    assert w["times"] == {"look lamp": 3}                      # a night eases two repeats off everything
    await p.tick()
    await asyncio.sleep(0)
    assert brain.asked == asked + 1 and "you woke up" in brain.packet
    assert db.execute("SELECT count(*) FROM genomes").fetchone() == (1,) and db.execute("SELECT count(*) FROM sleeps").fetchone() == (1,)
    lines = [[t, "line %d" % t, 5.0 if t % 50 == 0 else 0.3] for t in range(500)]
    picked = condense(lines + [[250, "visit", 99]]).splitlines()
    assert len(picked) == 40 and "visit" in picked and "line 450" in picked

    # the twin (off by default) still lives in the same loop, one action at a time, and a restart resumes the life
    d = tempfile.mkdtemp()
    twin = Pet("twin", cfg, Twin(cfg), d, log.open_db(":memory:"))
    for _ in range(ticks(cfg, 1800)):
        await twin.tick()
    learned = sum(c["n"] for c in twin.brain.s["counts"].values())
    assert learned > 50 and twin.db.execute("SELECT count(*) FROM decisions WHERE reason IS NOT NULL").fetchone() == (0,)
    twin.save()
    again = Pet("twin", cfg, Twin(cfg), d)
    assert again.world == dict(twin.world, thinking=None) and again.brain.s == twin.brain.s and len(again.journal) == len(twin.journal)
    assert cfg["twin"]["enabled"] is False

    print("engine check ok")


asyncio.run(main())
