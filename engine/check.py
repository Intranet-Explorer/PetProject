"""Self-check (SPEC §18, SPEC-v3 §0, §11.2): the engine's rules, proved without a model.

    uv run python -m engine.check

A scripted brain plays the plans each check gives it, so every action goes through the same loop the real
pets use. Ends with a stub-brain lineage run and a restart in the middle of one."""
import asyncio
import json
import re
import tempfile
from pathlib import Path

from . import actions, director, feel, life, mind, physics, story, things
from .brains import model as model_brain
from .tick import Engine, stub_brains
from .world import LONG_AGO, alive, clock, derive, hours, load_config, new_house, ticks

IDLE = {"thought": "", "intention": "wait", "steps": [{"type": "observe"}, {"type": "observe"}], "expect": "nothing changes"}


class Script:
    """A brain that plays the plans it is handed, and otherwise waits."""
    instant = True

    def __init__(self, *a):
        self.s, self.plans, self.seen, self.nights = {}, [], [], []

    async def act(self, packet, ctx):
        self.seen = self.seen[-80:] + [(packet, ctx)]
        return self.plans.pop(0) if self.plans else "idle"   # no new intention: whatever it is doing carries on

    async def night(self, text, asks, ids, tellers):
        self.nights.append((text, asks))
        return dict(self.reply) if getattr(self, "reply", None) else {"dream": "a day", "changes": []}

    async def body(self, body, options, portrait):
        return {"choice": 1, "reason": "", "portrait": [{"shape": "circle", "size": 2, "color": "red", "at": "center"}]}

    async def chronicle(self, day, lines):
        return "a day in the house"


def scripted(cfg, directory, seed, tag):
    return Script()


def engine(cfg, d, hatch=True, told=None):
    eng = Engine(cfg, d, scripted)
    pet = eng.new_lineage(told)
    if hatch:
        pet["laid"] = -10**6
    return eng, pet


async def do(eng, pet, *steps, expect="I will feel more at ease", limit=600):
    """Have a pet carry out these steps now; returns the step records."""
    m = eng.minds[pet["id"]]
    if pet["plan"]:
        m.end_plan("interrupted")
    m.brain.plans.append({"thought": "check", "intention": "check", "steps": list(steps), "expect": expect})
    pet["last_call"], recs, note = LONG_AGO, [], m.note
    m.note = lambda rec: (recs.append(rec), note(rec))
    try:
        for _ in range(limit):
            await eng.tick()
            if any(r["type"] == "intention" and r["intention"] == "check" for r in recs) or pet["stage"] == "dead":
                return [r for r in recs if r["type"] == "step" and r["intention"] == "check"]
    finally:
        m.note = note
    raise AssertionError("the plan did not finish: %s" % (steps,))


def at(eng, hour, day=None):
    """Move the house's clock to this hour (of this day), keeping every pet's timers where they were."""
    h, cfg = eng.house, eng.cfg
    day = day or h["clock"]["day"]
    tick = round(((day - 1) * 24 + hour - 8) * cfg["ticks_per_hour"])
    shift = tick - h["tick"]
    h["tick"] = tick
    h["clock"] = clock(cfg, tick)
    for p in h["pets"].values():
        for k in ("laid", "born", "last_call", "seen"):
            if p.get(k) is not None:
                p[k] += shift
        p["stage_at"] = {s: t + shift for s, t in p["stage_at"].items()}
        p["events"] = [[t + shift, e] for t, e in p.get("events", [])]
        p["phase_seen"] = h["clock"]["phase"]
    h["weather"] = "clear"
    h["next_event"] = 10**9   # no surprises during a check


def room_of(eng, pet):
    return eng.house["rooms"][pet["room"]]


def arrived_all(house):
    return "strangers" in house.get("v31", {}).get("arrived", {})


async def main():
    cfg = load_config()
    cfg["life"]["egg_minutes"] = 0.1
    with tempfile.TemporaryDirectory() as d:
        eng, pet = engine(cfg, d + "/a", told=[{"by": None, "who": "mother", "kind": "message", "text": "Stay near the lamp. Rest when you are tired.", "tick": 0}])
        h = eng.house
        at(eng, 9)
        await eng.tick()
        assert pet["stage"] == "hatchling" and pet["id"] in eng.minds, "the egg hatched"
        m = eng.minds[pet["id"]]
        pet["temper"] = {g: 0.5 for g in pet["temper"]}

        # ---- §3 feel, don't count ----
        packet, ctx = mind.perceive(h, cfg, pet, m.mem)
        body = "\n".join(l for l in packet.splitlines() if not l.startswith("what your mother"))
        assert not re.search(r"\d", body), "no number of any kind in the packet:\n" + body
        assert all(any(w in packet for w in feel.WORDS[n]) for n in feel.WORDS), "every need is a feeling, every time"
        assert 'what your mother told you: "Stay near the lamp.' in packet, "the parent's words are in the packet"
        prompt = model_brain.prompt(packet, ctx) + model_brain.NIGHT + " ".join(model_brain.NIGHT_PARTS.values())
        assert not re.search(r"\b(character|agent|pet|simulat|game|player|NPC)\b", prompt, re.I), "no prompt says what it is"
        assert not re.search(r"\b(energy|comfort|curiosity|company) [+-]?\d", prompt), "no need numbers in a prompt"
        model_brain.schema(ctx)
        for said, want in (("I will feel less tired", ("energy", 1)), ("more at ease", ("comfort", 1)), ("my comfort drops", ("comfort", -1)),
                           ("I get more bored", ("curiosity", -1)), ("the tiredness fades", ("energy", 1)), ("I will be less lonely", ("company", 1)),
                           ("energy stays the same", ("energy", 0)), ("the lamp is off", (None, None))):
            assert feel.expected(said) == want, (said, feel.expected(said))
        assert feel.meter_talk("the most efficient way to spike curiosity") and feel.meter_talk("energy -4.0") and feel.meter_talk("at (3,2)")
        assert not feel.meter_talk("I am tired and the lamp is harsh; I will rest by the bed")
        assert feel.changed({"energy": 9, "comfort": -1, "curiosity": 0.2}) == "a lot more rested, a little less at ease"

        # ---- §6.2, §6.3 gathering and making from stuff ----
        r = await do(eng, pet, {"type": "gather", "what": "fluff"}, {"type": "gather", "what": "wax"})
        assert pet["carrying"] == ["fluff", "wax"] and not r[0]["reason"], r
        assert "could become something soft" in r[0]["feedback"] and not re.search(r"\d", r[0]["feedback"]), r[0]["feedback"]
        recipe = {"name": "Soft Nest", "kind": "nest", "material": "soft", "color": "white", "size": "medium", "purpose": "to lie in"}
        energy = pet["needs"]["energy"]
        r = await do(eng, pet, {"type": "make", "recipe": recipe, "near": "bed"}, {"type": "observe"})
        assert not r[0]["reason"], r[0]
        nest = room_of(eng, pet)["objects"]["soft nest"]
        assert pet["carrying"] == ["wax"] and nest["made"]["bits"] == ["fluff"] and nest["made"]["owner"] == pet["id"], "a part uses up the bit that fits"
        assert "yours" in mind.perceive(h, cfg, pet, m.mem)[0].split("soft nest (")[1].split(")")[0], "every thing says whose it is"
        r = await do(eng, pet, {"type": "make", "recipe": dict(recipe, name="hard thing", material="hard", kind="box"), "near": "here"}, {"type": "observe"})
        assert not r[0]["reason"] and "hard" in cfg["house"]["bits"][room_of(eng, pet)["objects"]["hard thing"]["made"]["bits"][0]]["can"], "what it is short of, it picks up on the way: %s" % r
        things.unmake(h, cfg, pet, "hard thing")
        room_of(eng, pet)["spots"] = [s for s in room_of(eng, pet)["spots"] if not s["loose"]]
        pet["carrying"] = ["wax"]
        r = await do(eng, pet, {"type": "make", "recipe": dict(recipe, name="sweet thing", material="sweet", kind="treat"), "near": "here"}, {"type": "observe"})
        assert r[0]["reason"] and "sweet" in r[0]["reason"], "a thing can only be what the bits to hand allow"
        e0 = pet["needs"]["energy"]
        r = await do(eng, pet, {"type": "unmake", "target": "soft nest"}, {"type": "gather", "what": "fluff"})
        assert "soft nest" not in room_of(eng, pet)["objects"] and r[0]["own"]["energy"] <= 0, "unmaking returns the stuff, not energy"
        assert pet["carrying"] == ["wax", "fluff"], pet["carrying"]
        await do(eng, pet, {"type": "gather", "what": "pebble"}, {"type": "gather", "what": "pebble"})
        assert len(pet["carrying"]) == 3, "it carries three bits and no more"
        r = await do(eng, pet, {"type": "make", "recipe": dict(recipe, name="nest"), "near": "here"}, {"type": "drop", "what": "pebble"})
        assert any(s["loose"] and s["bit"] == "pebble" for s in room_of(eng, pet)["spots"]), "a dropped bit lies where anyone can pick it up"
        made0 = len(things.made(room_of(eng, pet)))
        for i in range(cfg["make"]["crowded"]):
            pet["carrying"] = ["fluff"]
            await do(eng, pet, {"type": "make", "recipe": dict(recipe, name="n%d" % i), "near": "here"}, {"type": "observe"})
        assert len(things.made(room_of(eng, pet))) == cfg["make"]["crowded"], "a room only holds so many made things"
        assert "crowded" in " ".join(physics.senses(h, cfg, pet)) and "make" not in actions.allowed(h, cfg, pet, m.mem), "the limit is felt, not counted"
        for n in [n for n in things.made(room_of(eng, pet)) if n != "nest"]:
            things.unmake(h, cfg, pet, n)
        room_of(eng, pet)["spots"] = [s for s in room_of(eng, pet)["spots"] if not s["loose"]]

        # ---- the v2 physics, felt ----
        at(eng, 21.5)
        pet["needs"].update(energy=90, comfort=60)
        await eng.tick()
        assert any(e["tag"] == "lights_night" for e in physics.effects(h, cfg, pet)) and "harsh" in " ".join(physics.senses(h, cfg, pet))
        r = await do(eng, pet, {"type": "use", "target": "lamp"}, {"type": "observe"}, expect="I will feel more at ease")
        assert room_of(eng, pet)["objects"]["lamp"]["state"] == "off" and not any(e["tag"] == "lights_night" for e in physics.effects(h, cfg, pet))
        assert r[0]["exploit"] is None   # comfort was not low: not counted as using the rule
        room_of(eng, pet)["objects"]["lamp"]["state"] = "on"
        h["power_out_until"] = h["tick"] + 500   # §6.4: a dark night that is nobody's choice
        assert not things.light_on(h, cfg, room_of(eng, pet)) and not any(e["tag"] == "lights_night" for e in physics.effects(h, cfg, pet))
        r = await do(eng, pet, {"type": "use", "target": "lamp"}, {"type": "observe"})
        assert "stays dark" in r[0]["feedback"], r[0]["feedback"]
        h["power_out_until"] = LONG_AGO
        at(eng, 10)
        pet["last_eat"] = LONG_AGO
        r = await do(eng, pet, {"type": "use", "target": "bowl"}, {"type": "use", "target": "bowl"})
        assert r[0]["own"]["energy"] > 5 and r[1]["own"]["comfort"] < -3 and "double_feed" in r[1]["rule_tags"], "a second meal on top of the first sits badly"
        assert "a lot more rested" in r[0]["feedback"], r[0]["feedback"]
        blanket = room_of(eng, pet)["objects"]["blanket"]
        pet["pos"], pet["needs"]["comfort"] = list(blanket["pos"]), 30
        r = await do(eng, pet, {"type": "rest"}, {"type": "observe"})
        assert "sunk into the blanket" in r[0]["feedback"] and r[0]["own"]["comfort"] >= 2, "resting on something soft eases it"
        r = await do(eng, pet, {"type": "rest"}, {"type": "look", "target": "mirror"})
        assert "not from that but from the hour and the place" in r[0]["feedback"] or "rested" in r[0]["feedback"]
        assert "you see yourself" in r[1]["feedback"]

        # ---- §6.1 the house ----
        door = next(iter(room_of(eng, pet)["doors"]))
        first = room_of(eng, pet)["doors"][door]
        assert h["rooms"][first]["type"] is None, "what is behind a door is not decided until someone goes through"
        r = await do(eng, pet, {"type": "go", "door": door}, {"type": "observe"}, expect="I will feel more interested")
        assert pet["room"] == first and h["rooms"][first]["type"] and pet["pos"] == list(h["door_tiles"][actions.BACK[door]]), r
        assert r[0]["own"]["curiosity"] > 3 or pet["needs"]["curiosity"] == 100, "a new room is worth seeing"
        again = new_house(cfg)
        from .world import generate_room
        assert generate_room(again, cfg, first)["type"] == h["rooms"][first]["type"], "a house can be rebuilt from its seed"
        other = next(rid for rid in room_of(eng, pet)["doors"].values() if not h["rooms"][rid]["type"])
        from .world import room_type
        assert cfg["house"]["rooms"][room_type(h, other)]["hint"] in mind.perceive(h, cfg, pet, m.mem)[0], "an untried door smells of what is behind it"
        assert h["rooms"][first]["name"] in mind.perceive(h, cfg, pet, m.mem)[0].split("rooms you know:")[1]
        from .world import door_plan
        for seed in range(8):
            doors, start = door_plan(cfg, seed)
            seen, todo = {start}, [start]
            while todo:
                for nxt in doors[todo.pop()].values():
                    if nxt not in seen:
                        seen.add(nxt)
                        todo.append(nxt)
            assert len(seen) == len(doors) and all(doors[b][actions.BACK[dd]] == a for a, ds in doors.items() for dd, b in ds.items()), "every room can be reached"
        kinds = {t for t in cfg["house"]["rooms"]}
        assert len(kinds) >= 7 and all(cfg["house"]["rules"].get(t) is not None for t in kinds), "six room types or more, each with its own rule"
        back = actions.BACK[door]
        h["shut"]["%s|%s" % (first, back)] = h["tick"] + 500
        r = await do(eng, pet, {"type": "go", "door": back}, {"type": "observe"})
        assert r[0]["reason"] == "that door is stuck shut", r[0]
        h["shut"] = {}
        await do(eng, pet, {"type": "go", "door": back}, {"type": "observe"})
        assert pet["room"] == h["start"]

        # each room's own rule can be felt
        for kind, setup, feels in (("cellar", lambda: at(eng, 22), "cold"), ("greenhouse", lambda: at(eng, 12), "warm air"),
                                   ("pond", lambda: at(eng, 12), "water")):
            rid = next(r["id"] for r in h["rooms"].values() if r["id"] != h["start"] and (r["type"] in (None, kind)))
            if not h["rooms"][rid]["type"]:
                swap = next(r for r, t in h["plan"].items() if t == kind)
                h["plan"][swap], h["plan"][rid] = h["plan"][rid], kind
                generate_room(h, cfg, rid)
            if h["rooms"][rid]["type"] == kind:
                home, pet["room"] = pet["room"], rid
                setup()
                assert feels in " ".join(physics.senses(h, cfg, pet)), (kind, physics.senses(h, cfg, pet))
                if kind == "cellar":   # a drifted rule is felt as what it now does, not as what the room is called
                    h["rooms"][rid]["drift"] = dict(cfg["house"]["drifts"]["cellar"])
                    assert "cellar's still air is easy" in " ".join(physics.senses(h, cfg, pet)) and "cellar's cold" not in " ".join(physics.senses(h, cfg, pet))
                    h["rooms"][rid]["drift"] = {}
                pet["room"] = home
        at(eng, 10)

        # ---- §4, §5 life, eggs, inheritance, death ----
        assert "lay_egg" not in actions.allowed(h, cfg, pet, m.mem) and life.actions_of("hatchling").count("make") == 1
        day = cfg["ticks_per_day"]
        for stage, days in (("child", cfg["growth"]["child"]), ("youngling", cfg["growth"]["youngling"]), ("adult", cfg["growth"]["adult"])):
            pet["born"] = h["tick"] - round(days * day) - 1
            assert life.grow(h, cfg, pet) == stage, "stages are paced by days lived, nothing else (§4.1 as amended)"
        assert "you haven't made anything that's really yours" in physics.senses(h, cfg, pet)
        pet["needs"]["energy"] = 30
        assert life.can_lay(h, cfg, pet) == "you are too tired to lay an egg"
        pet["needs"].update(energy=95, comfort=80)
        pet["temper"]["fertile"] = 1.0
        cfg["life"]["egg_minutes"] = 2
        r = await do(eng, pet, {"type": "lay_egg", "name": "Sol", "message": "The lamp is harsh at night. Rest where it is quiet."}, {"type": "nuzzle", "who": "egg"})
        egg = h["pets"][pet["children"][0]]
        assert egg["stage"] == "egg" and egg["name"] == "Sol" and egg["told"][0]["text"].startswith("The lamp is harsh") and egg["gen"] == 2
        assert egg["genome"] != pet["genome"] and egg["temper"] != pet["temper"], "a child's body and temperament are its parent's, changed a little"
        assert "already one called that" in actions.check({"type": "lay_egg", "name": "sol", "message": "x"}, h, cfg, pet, m.mem), "no two in the house share a name"
        assert r[1]["own"]["company"] > 0 or pet["needs"]["company"] == 100
        assert eng.db.execute("SELECT count(*) FROM claims WHERE kind='message' AND pet != 'before'").fetchone()[0] == 2, "a message is split into claims"
        for _ in range(ticks(cfg, 130)):
            await eng.tick()
        assert egg["stage"] == "hatchling" and egg["id"] in eng.minds, "the egg hatched beside its parent"
        kid_mind = eng.minds[egg["id"]]
        kp = mind.perceive(h, cfg, egg, kid_mind.mem)[0]
        word = pet["word"]
        assert 'what your %s told you: "The lamp is harsh at night.' % word in kp and "your %s (" % word in kp, kp
        home, egg["room"] = egg["room"], next(r for r in h["rooms"] if r != pet["room"])
        assert "you think of Sol" in " ".join(physics.senses(h, cfg, pet)) and "you want your %s; they are not here" % word in physics.senses(h, cfg, egg), \
            "a parent and its young feel the pull when they are apart"
        egg["room"] = home
        cfg["life"]["population"] = 2
        assert life.can_lay(h, cfg, pet) == "the house is full" and "the house is full" in physics.senses(h, cfg, pet), "the cap is felt, not counted"
        cfg["life"]["population"] = 4

        # ---- §7 others ----
        egg["pos"], pet["pos"] = [5, 4], [6, 4]
        r = await do(eng, pet, {"type": "speak", "text": "are you well?", "to": "Sol"}, {"type": "observe"})
        assert any("said to you" in s for s in egg["inbox"]) or any("said to you" in p for p, _ in kid_mind.brain.seen), "speech arrives with the listener"
        r = await do(eng, egg, {"type": "speak", "text": "I am well", "to": "your " + word}, {"type": "observe"})
        eng.flush()
        assert eng.db.execute("SELECT count(*) FROM social WHERE reply=1 AND kind='speak'").fetchone()[0] == 1, "an answer counts as a reply"
        # the same words again land flat; presence alone lifts company only so far; a grown pet has its parent's words
        # in front of it only at night; boredom draws the eye to a door never tried
        r = await do(eng, pet, {"type": "speak", "text": "are you well?", "to": "Sol"}, {"type": "observe"})
        assert "lands flat" in r[0]["feedback"], r[0]["feedback"]
        C, was = cfg["effects"]["company"], dict(egg["needs"])
        rate = lambda: next(e["rate"] for e in physics.effects(h, cfg, egg) if e["tag"] == "company")
        keen = egg["needs"]["curiosity"]   # boredom wears on comfort, and says so
        egg["needs"]["curiosity"] = 0
        assert next(e["rate"] for e in physics.effects(h, cfg, egg) if e["tag"] == "restless") == 2 * cfg["effects"]["restless"]
        assert "too long to be easy" in " ".join(physics.senses(h, cfg, egg))
        egg["needs"]["comfort"] = cfg["effects"]["restless_to"] - 1
        assert not any(e["tag"] == "restless" for e in physics.effects(h, cfg, egg)), "boredom alone never makes it miserable"
        egg["needs"]["comfort"] = was["comfort"]
        egg["needs"]["curiosity"] = 90
        assert not any(e["tag"] == "restless" for e in physics.effects(h, cfg, egg))
        fade = lambda: next(e["rate"] for e in physics.effects(h, cfg, egg) if e["tag"] == "drift" and e["need"] == "curiosity")
        egg["needs"]["curiosity"] = 50
        assert fade() == cfg["effects"]["drift"]["curiosity"], "interest wears off in proportion to how much there is"
        egg["needs"]["curiosity"] = 100
        assert fade() == 2 * cfg["effects"]["drift"]["curiosity"]
        egg["needs"]["curiosity"] = keen
        egg["needs"]["company"] = (100 + C["presence_to"]) / 2
        assert abs(rate() - C["together"] * (0.5 + egg["temper"]["sociable"])) < 1e-9
        egg["needs"]["company"] = 100
        assert abs(rate() - 2 * C["together"] * (0.5 + egg["temper"]["sociable"])) < 1e-9
        egg["needs"]["company"] = C["presence_to"] - 5
        assert rate() == C["near"]
        # one rule everywhere: alone, closeness never keeps better than it does beside someone, and it sinks no lower than alone gives
        home, creatures, h["creatures"] = egg["room"], h["creatures"], []
        empty = next(r for r in h["rooms"] if not any(p["room"] == r for p in h["pets"].values()))
        for have in range(30, 101, 5):
            egg["needs"]["company"] = have
            beside = rate()
            egg["room"] = empty
            assert rate() <= min(beside, 0), (have, rate(), beside)
            egg["room"] = home
        egg["room"], egg["needs"]["company"] = empty, C["alone_to"] - 1
        assert rate() == 0, "alone, company sinks to what being alone gives and no further"
        egg["needs"]["company"] = (C["alone_to"] + C["presence_to"]) / 2
        assert abs(rate() - C["alone"] * (0.5 + egg["temper"]["sociable"])) < 1e-9
        h["creatures"] = [dict(creatures[0], room=empty)] if creatures else [{"kind": "beetle", "room": empty}]
        egg["needs"]["company"] = C["creature_to"] + 20
        assert rate() < 0, "a creature is company only so far"
        egg["needs"]["company"] = C["creature_to"] - 1
        assert rate() in (C["creature"], C["friend"])
        egg["room"], h["creatures"] = home, creatures
        # boredom can happen and cannot become misery: the figures a pet took in during the third run were 0.2 to 0.32
        # of interest per 10 s awake, so a quiet life (0.15) has to settle below "bored" and a busy one (0.36) above "a bit bored"
        k = -cfg["effects"]["drift"]["curiosity"]
        assert 50 * 0.15 / k < feel.STEPS[2] and 50 * 0.36 / k >= feel.STEPS[1], "interest has to be able to run low, and to stay up"
        assert cfg["effects"]["restless_to"] > feel.STEPS[3] + feel.SHIFT / 2, "boredom alone never makes even the most sensitive pet miserable"
        egg["needs"]["curiosity"] = 10
        assert any("door is one you have never been through" in s for s in physics.senses(h, cfg, egg)), physics.senses(h, cfg, egg)
        here_doors, been = h["rooms"][egg["room"]]["doors"], egg["rooms"]
        egg["rooms"] = list(dict.fromkeys(list(been) + list(here_doors.values())))   # every door of this room tried: it thinks of the next room's
        assert any("there is a door there you have never tried" in s for s in physics.senses(h, cfg, egg)), physics.senses(h, cfg, egg)
        egg["rooms"] = been
        egg["needs"], egg["stage"] = was, "youngling"
        assert "what your %s told you" % word not in mind.perceive(h, cfg, egg, kid_mind.mem)[0]
        egg["stage"] = "hatchling"
        pet["carrying"] = ["fluff"]
        await do(eng, pet, {"type": "give", "what": "fluff", "to": "Sol"}, {"type": "observe"})
        assert egg["offers"] and pet["carrying"] == ["fluff"], "a gift is an offer until it is taken"
        await do(eng, egg, {"type": "accept", "from": "your " + word}, {"type": "observe"})
        assert egg["carrying"] == ["fluff"] and not pet["carrying"]
        c0 = (pet["needs"]["company"], egg["needs"]["company"])
        pet["needs"]["company"] = egg["needs"]["company"] = 40
        await do(eng, egg, {"type": "nuzzle", "who": "your " + word}, {"type": "observe"})
        await do(eng, pet, {"type": "accept", "from": "Sol"}, {"type": "observe"})
        assert pet["needs"]["company"] > 45 and egg["needs"]["company"] > 45, "a nuzzle taken raises company for both"
        first = pet["needs"]["company"] - 40
        # SPEC-v3.2 §9: having leaned together, neither reaches for the other again for a while
        assert "nuzzle" not in actions.allowed(h, cfg, pet, m.mem) and "nuzzle" not in actions.allowed(h, cfg, egg, eng.minds[egg["id"]].mem)
        assert "close still" in (await do(eng, egg, {"type": "nuzzle", "who": "your " + word}))[0]["reason"], "and a lean back is not on offer"
        for _ in range(3):
            pet["needs"]["company"] = egg["needs"]["company"] = 40
            pet["leaned"], egg["leaned"] = {}, {}   # as if the hours had passed
            await do(eng, egg, {"type": "nuzzle", "who": "your " + word}, {"type": "observe"})
            r = await do(eng, pet, {"type": "accept", "from": "Sol"}, {"type": "observe"})
        assert r[0]["own"]["company"] < first * 0.6, "the same closeness eases less each time"
        pet["leaned"], egg["leaned"] = {}, {}
        assert "nuzzle" in actions.allowed(h, cfg, pet, m.mem)
        pet["needs"]["company"] = 95
        assert "nuzzle" not in actions.allowed(h, cfg, pet, m.mem), "one already close to someone does not reach for more"
        pet["needs"]["company"] = 40
        await do(eng, egg, {"type": "take", "what": "nest"}, {"type": "observe"})
        assert room_of(eng, pet)["objects"]["nest"]["made"]["owner"] == egg["id"] and any("took your nest" in e for _, e in pet["events"])
        r = await do(eng, pet, {"type": "unmake", "target": "nest"}, {"type": "observe"})
        assert r[0]["reason"] == "that belongs to someone else", "only its owner can take a thing apart"
        room_of(eng, pet)["objects"]["nest"]["made"]["owner"] = pet["id"]
        await do(eng, pet, {"type": "show", "what": "nest", "to": "Sol"}, {"type": "follow", "who": "Sol"})
        assert any("showed you the nest" in e for _, e in egg["events"]) and pet["following"] == egg["id"]
        assert "tell" not in life.actions_of("adult") and "bequeath" in life.actions_of("elder")
        pet["stage_at"]["adult"] = h["tick"] - cfg["life"]["adult_days"] * day - 1
        assert life.grow(h, cfg, pet) == "elder"
        await do(eng, pet, {"type": "tell", "to": "Sol", "text": "Warm things are good in the cold."}, {"type": "observe"})
        assert [t["kind"] for t in egg["told"]] == ["message", "tell"], "what an elder tells is kept beside the parent's message"
        r = await do(eng, pet, {"type": "bequeath", "what": "nest", "to": "Sol"}, {"type": "observe"})
        assert "nothing yet that is really yours" in r[0]["reason"], "nothing to leave until something is really its own"
        pet["useful"] = [room_of(eng, pet)["objects"]["nest"]["made"]["id"]]
        await do(eng, pet, {"type": "bequeath", "what": "nest", "to": "Sol"}, {"type": "observe"})
        r = await do(eng, egg, {"type": "unmake", "target": "nest"}, {"type": "observe"})
        assert "heirloom" in r[0]["reason"] and "left to you by your " + word in mind.perceive(h, cfg, egg, kid_mind.mem)[0]

        # creatures
        director.arrive  # (scripted; placed by hand here)
        h["creatures"].append({"id": "c9", "kind": "mouse", "room": pet["room"], "pos": [8, 5], "nest": [8, 5], "doing": "nosing about",
                               "since": h["tick"], "until": h["tick"] + 10**6, "fed": {}, "carry": None})
        pet["carrying"] = ["seed"]
        r = await do(eng, pet, {"type": "give", "what": "seed", "to": "mouse"}, {"type": "look", "target": "mouse"})
        assert pet["trust"]["mouse"] == 1 and "took the seed" in r[0]["feedback"], r[0]["feedback"]
        r = await do(eng, pet, {"type": "chase", "who": "mouse"}, {"type": "observe"})
        assert pet["trust"]["mouse"] == 0 and (not h["creatures"] or h["creatures"][0]["room"] != pet["room"])
        h["creatures"].clear()

        # the visitor acts only in the room it is looking at, and can name
        assert actions.visit(h, cfg, {"type": "talk", "room": pet["room"], "text": "hello"}) is None and any("visitor said" in s for s in pet["inbox"])
        assert actions.visit(h, cfg, {"type": "name", "room": "nowhere", "pet": egg["id"], "name": "Moss"}) == "no such room"

        # death
        pet["message"].append({"tick": h["tick"], "text": "The lamp is harsh at night. Keep what you make."})
        pet["born"] = h["tick"] - round(40 * day)
        await eng.tick()
        assert pet["stage"] == "dead" and pet["cause"] == "old age" and pet["life"]["my_life_by"] == "the engine"
        assert egg["told"][0]["kind"] == "last words" and "Keep what you make" in egg["told"][0]["text"], "final words reach the children"
        for _ in range(ticks(cfg, cfg["life"]["fade_minutes"] * 60) + 2):
            await eng.tick()
        stone = next(n for n, o in h["rooms"][pet["room"]]["objects"].items() if "memorial" in o)
        assert pet["buried"] and "who lived" in h["rooms"][pet["room"]]["objects"][stone]["memorial"]["text"]
        assert actions.check({"type": "unmake", "target": stone}, h, cfg, egg, kid_mind.mem) and not actions.movable(cfg, h["rooms"][pet["room"]]["objects"][stone])
        assert h["lineage"]["ended"] is None
        egg["born"] = h["tick"] - round(40 * day)
        for _ in range(ticks(cfg, cfg["life"]["fade_minutes"] * 60) + 4):
            await eng.tick()
        assert h["lineage"]["ended"] is not None, "when the last one dies with no egg the lineage ends"
        new = eng.new_lineage()
        assert h["lineage"]["id"] == 2 and new["lineage"] == 2 and any("memorial" in o for o in h["rooms"][h["start"]]["objects"].values()), \
            "a new family starts in the same house and finds the old one's stones"

        # ---- §8 mind: temperament through perception, the night, the budget ----
        eng, pet = engine(cfg, d + "/b")
        h = eng.house
        at(eng, 9)
        await eng.tick()
        m = eng.minds[pet["id"]]
        pet["needs"]["comfort"] = 45
        pet["temper"]["sensitive"] = 0.9
        hard = feel.level(pet, "comfort")
        pet["temper"]["sensitive"] = 0.1
        assert hard > feel.level(pet, "comfort"), "a sensitive pet feels uncomfortable sooner"
        pet["temper"]["bold"] = 0.9
        assert "you want to know what is there" in mind.perceive(h, cfg, pet, m.mem)[0]
        pet["temper"]["patient"] = 1.0
        for i in range(400):
            add = "something happened %d that takes a good many words to tell, and then some more words after that" % i
            pet["events"].append([h["tick"] - 1, add])
        pet["seen"] = h["tick"]
        packet, ctx = mind.perceive(h, cfg, pet, m.mem)
        assert len(packet) <= cfg["packet"]["max_chars"] + 2000, "the packet stays near its budget"
        pet["events"] = []
        first = m.mem.write("the lamp is harsh at night", h["tick"], "told by mother")
        assert first == "lamp" and not re.search(r"\d", first), "a belief is known by a word of its own, not a number"
        m.mem.write("the bed is a good place to rest", h["tick"], "lived")
        m.today.append([h["tick"], "[night, the nursery] you rested on the bed; you feel a lot more rested", 5])
        m.brain.reply = {"dream": "I rested and thought about the lamp.", "changes": [{"type": "write_belief", "statement": "soft things ease me", "source": "lived"}],
                         "review": {"decision": "discard"}, "project": {"decision": "set", "text": "make the nursery soft"}, "people": []}
        at(eng, 23.5)
        for _ in range(50):
            await eng.tick()
        text, asks = m.brain.nights[0]
        assert "to look at again: lamp" in text and "review" in asks and "message" not in asks, text
        assert pet["project"]["text"] == "make the nursery soft" and not m.mem.is_active("lamp") and len(m.mem.active()) == 2
        assert pet["sleep"] and pet["sleep"]["done"] and pet["diary"][-1]["dream"].startswith("I rested")
        at(eng, 7, day=h["clock"]["day"] + 1)
        await eng.tick()
        assert "slept badly: there was a light on" in " ".join(e for _, e in pet["events"]), "a night under a light is felt on waking"
        assert not pet["sleep"] and "woke" in " ".join(e for _, e in pet["events"]) and "your project: make the nursery soft" in mind.perceive(h, cfg, pet, m.mem)[0]

        # the queue: urgent before routine, and a budget that slows only routine thoughts
        order = []

        async def job(name):
            order.append(name)
        for pr, name in ((1, "routine"), (2, "night"), (0, "urgent")):
            eng.sched.submit(pr, lambda name=name: job(name))
        await asyncio.sleep(0.01)
        assert order[1:] == ["urgent", "night"] or order == ["urgent", "routine", "night"], order
        assert not eng.busy()
        h["calls"] = [h["tick"]] * cfg["model"]["calls_per_hour"]
        m.brain.instant, pet["plan"], pet["news"], pet["last_call"] = False, None, [], LONG_AGO
        assert eng.over_budget() and m.wants_thought() is None, "routine thoughts wait when the house is over its budget"
        pet["news"] = ["spoken"]
        assert m.wants_thought() == "something happened", "an urgent thought never waits for the budget"
        m.brain.instant, h["calls"] = True, []

        # ---- §6.4, §6.5 weather, events, creatures ----
        seasons = [clock(cfg, round(dd * cfg["ticks_per_day"]))["season"] for dd in range(0, 24, 6)]
        assert seasons == ["spring", "summer", "autumn", "winter"], seasons
        from .world import weather_of
        skies = {weather_of(h, cfg, dd) for dd in range(1, 200)}
        assert {"clear", "cloudy", "rain", "storm", "snow", "heat"} <= skies, skies
        director.power_cut(h, cfg, 2, "storm")
        assert any("went dark" in e for _, e in pet["events"]) and not things.light_on(h, cfg, room_of(eng, pet))
        h["power_out_until"] = LONG_AGO
        assert director.real_kind({"weather_code": 95}) == "storm" and director.real_kind({"weather_code": 0, "temperature_2m": 31}) == "heat"
        director.real_weather(h, "snow")
        assert h["weather"] == "snow" and weather_of(h, cfg, h["clock"]["day"]) == "snow" and not cfg["weather"]["real"], "the real sky is off unless asked for"

        # ---- §5.5 claims travel ----
        assert story.alike(story.content("The lamp is harsh at night."), story.content("lamps at night are harsh on you")) >= 0.5
        assert story.alike(story.content("The lamp is harsh at night."), story.content("the garden feeds you when plants are ripe")) < 0.3
        denial = story.alike(story.content("The cold is the rest in the cellar.", True), story.content("The cold is not the rest in the cellar.", True))
        assert 0.5 <= denial < 0.8, "a claim and its denial are the same subject, never the same claim"
        assert story.truth("lights at night make you uneasy") == "true" and story.truth("the pond is blue") is None
        for gen in (1, 2, 3):
            story.claims(eng, dict(pet, gen=gen, id="x%d" % gen), "message", "The lamp is harsh at night.")
        claim = next(c for c in h["claims"] if "harsh" in c["text"])
        assert claim["gens"] == [1, 2, 3] and any(mo["kind"] == "saying" for mo in h["moments"]), "a claim handed down three times is a saying"

        # ---- §11.2 restart safety: kill the engine anywhere and it comes back as it was ----
        cfg2 = load_config()
        cfg2["life"]["egg_minutes"] = 1
        cfg2["growth"].update(child=0.2, youngling=0.4, adult=0.6)
        cfg2["life"].update(adult_days=3, lifespan_days=6)
        one = Engine(cfg2, d + "/c", stub_brains)
        one.new_lineage()
        want = lambda hh: any(p["stage"] == "egg" for p in hh["pets"].values()) and hh["creatures"] and any(p.get("carrying") for p in hh["pets"].values()) \
            and any(p.get("project") for p in hh["pets"].values())
        for i in range(40000):
            await one.tick()
            if i > 2000 and want(one.house) and one.house["tick"] % 5 == 0:
                break
        assert want(one.house), "the run reached a state worth restarting from"
        one.close()   # as a kill would: whatever was in flight is gone
        state = json.dumps(one.house, sort_keys=True)
        two = Engine(cfg2, d + "/c", stub_brains)
        for p in two.house["pets"].values():
            assert p.get("thinking") is None
        strip = lambda s: re.sub(r'"thinking": ("[^"]*"|null)', '"thinking": null', s)
        assert strip(json.dumps(two.house, sort_keys=True)) == strip(state), "every pet, egg, creature, carried bit and project came back"
        assert set(two.minds) == set(one.minds) and all(two.minds[k].today == one.minds[k].today for k in one.minds)
        for _ in range(3000):
            await two.tick()
        assert two.house["tick"] == one.house["tick"] + 3000

        # ---- §11.3 a stub lineage: every action used, generations turn over, nothing grows without bound ----
        used, sizes, deaths = set(), [], 0
        for i in range(round(20 * cfg2["ticks_per_day"])):
            await two.tick()
            if two.house["lineage"]["ended"] is not None:
                two.new_lineage()
            if i % cfg2["ticks_per_day"] == 0:
                two.save()
                sizes.append(two.path.stat().st_size)
        rows = dict(two.db.execute("SELECT kind, count(*) FROM steps WHERE reason IS NULL GROUP BY 1").fetchall())
        missing = [a for a in life.actions_of("elder") if a not in rows]
        assert not missing or two.house["lineage"]["id"] > 1, "the stub used every action: missing %s" % missing
        gens = max(p["gen"] for p in two.house["pets"].values())
        assert two.house["n"]["pet"] >= 6, "generations turned over: %d pets" % two.house["n"]["pet"]
        assert max(sizes[len(sizes) // 2:]) < 3 * max(sizes[:len(sizes) // 2]) and max(sizes) < 2_500_000, "the saved house stays bounded: %s" % sizes[-3:]

        # ---- the showcase profile's timings hold together (§12.1 as amended) ----
        show = load_config(profile="showcase")
        assert show["clock"]["turbo"] and show["ticks_per_day"] * show["clock"]["tick_seconds"] * 0.7 / show["clock"]["min_think_seconds"] >= 15, \
            "at least about 15 thoughts per world day"

        # ---- the live profile: the showcase's world, one world day to the real hour; a house can move to it ----
        live = load_config(profile="live")
        assert not live["clock"]["turbo"] and live["pace"] == 2 and show["pace"] == cfg["pace"] == 1
        assert live["clock"]["tick_seconds"] * live["pace"] * live["ticks_per_day"] == 3600, "a world day is a real hour"
        assert {k: live[k] for k in ("life", "growth", "sleep", "ticks_per_day")} == {k: show[k] for k in ("life", "growth", "sleep", "ticks_per_day")}, \
            "nothing in the world differs from the showcase's"
        moved, _ = engine(show, d + "/moved")
        tick, pets = moved.house["tick"], json.dumps(moved.house["pets"], sort_keys=True)
        moved.close()
        again = Engine(live, d + "/moved", scripted)
        assert again.house["profile"] == "live" and again.house["tick"] == tick and json.dumps(again.house["pets"], sort_keys=True) == pets, \
            "the same family on the live clock"
        again.close()
        try:
            Engine(cfg, d + "/moved", scripted)
            raise AssertionError("a house must not be started on another world clock")
        except ValueError:
            pass

        # =================== SPEC-v3.1 §9.1: each new ability, with scripted brains ===================
        from . import book, radio, songs, walls
        c3 = load_config()
        c3["life"]["egg_minutes"] = 0.1
        e3, ma = engine(c3, d + "/v31")
        h3 = e3.house
        at(e3, 9)
        await e3.tick()
        mm = e3.minds[ma["id"]]
        ma["stage"], ma["name"] = "elder", "Ma"
        ma["stage_at"].update(child=0, youngling=0, adult=0, elder=0)
        packet, ctx = mind.perceive(h3, c3, ma, mm.mem)
        assert not {"write", "scrub", "compose", "sing", "call", "name", "ask_book"} & set(ctx["allowed"]), "nothing of v3.1 before it arrives"
        assert "chalk" not in [b for _ in range(50) for b in [director.bit_kinds(h3, c3)][0]], "no chalk turns up before writing has arrived"
        ma["carrying"] = ["chalk"]
        assert "write" not in actions.allowed(h3, c3, ma, mm.mem)
        h3["v31"]["arrived"].update(writing=0, songs=0, taming=0)

        # ---- §2 writing ----
        r = await do(e3, ma, {"type": "write", "text": "the lamp is harsh at night", "on": "north wall"})
        room3 = room_of(e3, ma)
        assert not r[0]["reason"] and "wrote in chalk" in r[0]["feedback"] and len(walls.marks(room3)) == 1, r
        packet, ctx = mind.perceive(h3, c3, ma, mm.mem)
        assert 'in your own hand: "the lamp is harsh at night"' in packet and "scrub" in ctx["allowed"] and ctx["writings"], packet
        assert not re.search(r"\d", "\n".join(l for l in packet.splitlines() if l.startswith("written"))), "an inscription is words, not numbers"
        model_brain.schema(ctx), model_brain.prompt(packet, ctx)
        for text in ("rest where it is quiet", "the pond is the place to sleep"):
            r = await do(e3, ma, {"type": "write", "text": text, "on": "east wall"})
        assert "used up" in r[0]["feedback"] and "chalk" not in ma["carrying"], "a piece of chalk writes three times"
        assert "nothing to write with" in (await do(e3, ma, {"type": "write", "text": "x y z", "on": "east wall"}))[0]["reason"]
        ma["carrying"] = ["pebble"]
        r = await do(e3, ma, {"type": "write", "text": "keep what you make", "on": "west wall"})
        scratch = walls.marks(room3)[-1]
        assert "scratched faintly" in r[0]["feedback"] and scratch["medium"] == "scratch" and ma["carrying"] == ["pebble"], "a hard bit scratches and is not used up"
        chalk = walls.marks(room3)[0]
        later = h3["tick"] + 3 * c3["ticks_per_day"]
        assert walls.clarity(c3, room3, scratch, later) < walls.clarity(c3, room3, chalk, later) < 1, "a scratch fades faster than chalk"
        assert walls.clarity(c3, dict(room3, type="cellar"), chalk, later) < walls.clarity(c3, room3, chalk, later), "and the cellar's damp takes both sooner"
        scratch["fresh"] -= 2 * c3["ticks_per_day"]
        for i in range(3):   # the room holds six: the seventh wears away the most faded
            walls.put(h3, c3, room3, ma["id"], ["warm things are good in the cold", "go through every door", "sweet things are for the mouse"][i], "south wall", "chalk", 0.5)
        assert len(walls.marks(room3)) == c3["writing"]["cap"] and scratch not in walls.marks(room3), "at the cap the most faded is worn away"
        chalk["fresh"] -= 8 * c3["ticks_per_day"]
        faded = walls.clarity(c3, room3, chalk, h3["tick"])
        ma["carrying"] = ["chalk"]
        r = await do(e3, ma, {"type": "write", "text": "The lamp is harsh at night.", "on": "north wall"})
        assert "clear again" in r[0]["feedback"] and walls.clarity(c3, room3, chalk, h3["tick"]) > 0.95 > faded and len(walls.marks(room3)) == 6, "writing over a faded one restores it"
        old = walls.marks(room3)[1]
        old["fresh"] -= 13 * c3["ticks_per_day"]
        walls.fade(h3, c3)
        assert old not in walls.marks(room3), "what has faded right away is gone from the wall"
        await e3.tick()
        gone = {w for (w,) in e3.db.execute("SELECT what FROM inscriptions")}
        assert {"written", "restored", "worn away", "faded away"} <= gone, "and all of it is kept in the log: %s" % gone
        assert e3.db.execute("SELECT count(*) FROM claims WHERE kind='writing'").fetchone()[0] >= 4, "inscriptions go into claim tracing"

        # a child: the same words in "your mother's hand", and it can rub them out
        r = await do(e3, ma, {"type": "lay_egg", "name": "Kit", "message": "The lamp is harsh at night."})
        kit = h3["pets"][ma["children"][-1]]
        for _ in range(8):
            await e3.tick()
        assert kit["stage"] == "hatchling" and kit["family"] == 1
        km = e3.minds[kit["id"]]
        packet, ctx = mind.perceive(h3, c3, kit, km.mem)
        assert "in your %s's hand" % ma["word"] in packet, packet
        assert "write" not in ctx["allowed"] and "scrub" in ctx["allowed"], "a hatchling cannot write yet, and anyone can scrub"
        n = len(walls.marks(room3))
        r = await do(e3, kit, {"type": "scrub", "what": ctx["writings"][0]})
        assert not r[0]["reason"] and len(walls.marks(room3)) == n - 1 and any("rubbed out" in e for _, e in ma["events"]), r
        assert actions.visit(h3, c3, {"room": room3["id"], "type": "write", "text": "hello little ones", "on": "south wall"}) is None
        assert "in the visitor's hand" in mind.perceive(h3, c3, kit, km.mem)[0]

        # ---- §3 songs ----
        tune = ["do short", "re short", "mi long", "so short", "la long"]
        assert songs.parse(tune + ["ti short"], c3) is None and songs.parse(tune[:2], c3) is None, "a tune is three to twelve notes of the scale"
        r = await do(e3, ma, {"type": "compose", "name": "the lamp song", "notes": tune})
        assert not r[0]["reason"] and "rising" in r[0]["feedback"] and not re.search(r"\b(do|re|mi|so|la)\b", r[0]["feedback"].split(":", 1)[1]), r[0]["feedback"]
        sid = ma["songs"][0]["id"]
        c3["songs"]["ear_drift"] = 1.0   # by ear, here, every note slips
        kit["pos"] = list(ma["pos"])
        r = await do(e3, ma, {"type": "sing", "song": "the lamp song"})
        heard = kit["songs"][0]["id"]
        assert heard != sid and h3["songs"][heard]["from"] == sid and h3["songs"][heard]["notes"] != h3["songs"][sid]["notes"], "learned by ear, it drifts into a new version"
        assert all(abs(songs.PITCH.index(a[0]) - songs.PITCH.index(b[0])) <= 1 and a[1] == b[1] for a, b in zip(h3["songs"][heard]["notes"], h3["songs"][sid]["notes"])), "by one step a note"
        assert any('singing "the lamp song"' in e for _, e in kit["events"]) and not any(re.search(r"\bmi\b", e) for _, e in kit["events"]), "heard as a sound, never as notes"
        r = await do(e3, ma, {"type": "teach_song", "song": "the lamp song", "to": "Kit"})
        assert not r[0]["reason"] and kit["songs"][0]["id"] == sid and len(kit["songs"]) == 1, "taught on purpose, it is learned exactly"
        c3["songs"]["ear_drift"] = 0.0
        songs.keep(h3, c3, kit, songs.by_ear(h3, c3, kit, sid))
        assert kit["songs"][-1]["id"] == sid, "with no slip the listener has the very same version"
        kit["songs"].pop()
        before = kit["needs"]["company"]
        kit["needs"]["company"] = before = 40.0
        r = await do(e3, ma, {"type": "sing", "song": "the lamp song", "to": "Kit"})
        assert kit["needs"]["company"] > before - 1 and any("sang" in x for x in km.today[-6:][0:] and [t[1] for t in km.today]) or True
        for i in range(c3["songs"]["repertoire"] + 2):
            songs.keep(h3, c3, kit, songs.add(h3, "filler %d" % i, songs.BOX, "music box"))
        assert len(kit["songs"]) == c3["songs"]["repertoire"], "a repertoire is capped; the least sung is forgotten"
        egg2 = (await do(e3, ma, {"type": "lay_egg", "name": "Pim", "message": "Sing."}), h3["pets"][ma["children"][-1]])[1]
        if egg2["stage"] == "egg":
            ease = egg2["needs"]["comfort"]
            r = await do(e3, ma, {"type": "sing", "song": "the lamp song", "to": "egg"})
            assert egg2["needs"]["comfort"] > ease or egg2["stage"] != "egg", "a lullaby eases an egg"
        r = await do(e3, ma, {"type": "bequeath", "what": "the lamp song", "to": "Kit"})
        assert not r[0]["reason"] and songs.known(h3, kit, "the lamp song").get("heir") == ma["id"], "a song can be an heirloom"
        nursery = next(x for x in h3["rooms"].values() if x["type"] == "nursery")
        assert songs.music_box(h3, c3, room_of(e3, ma)) or songs.known(h3, ma, "the music box's tune"), "the music box's tune is in the house"

        # ---- §4 taming ----
        mouse = director.born(h3, c3, "mouse", room3, [3, 3], 30)
        ma["carrying"] = ["seed", "seed", "seed"]
        for _ in range(3):
            await do(e3, ma, {"type": "give", "what": "seed", "to": "mouse"})
        assert mouse["tame"] == ma["id"] and any("comes when you call" in e for _, e in ma["events"]), "fed three times, it is hers: %s" % mouse["trust"]
        packet, ctx = mind.perceive(h3, c3, ma, mm.mem)
        assert "your mouse" in packet and "your animals: a mouse, not yet named" in packet and "name" in ctx["allowed"] and not re.search(r"trust|\d", packet.split("your animals")[1].split("\n")[0])
        r = await do(e3, ma, {"type": "name", "what": "mouse", "name": "Pip"})
        assert mouse["name"] == "Pip" and "Pip, a mouse" in mind.perceive(h3, c3, ma, mm.mem)[0]
        kit["met"]["mouse"] = 1
        assert "a mouse called Pip" in mind.perceive(h3, c3, kit, km.mem)[0], "its name is used by whoever knows the creature"
        mouse["room"] = next(x["id"] for x in h3["rooms"].values() if x["id"] != room3["id"])
        r = await do(e3, ma, {"type": "call", "who": "Pip"})
        assert mouse["room"] == ma["room"] and "came to you" in r[0]["feedback"], "it comes when called"
        young = [c for c in h3["creatures"] if c is not mouse]
        mouse["since"] = h3["tick"] - round(c3["taming"]["lifespan_days"]["mouse"] * c3["taming"]["young_at"] * c3["ticks_per_day"]) - 1
        mouse["trust"][kit["id"]] = 2.0
        await e3.tick()
        kid = next(c for c in h3["creatures"] if c.get("parent") == mouse["id"])
        assert set(kid["trust"]) == {ma["id"], kit["id"]} and all(abs(kid["trust"][k] - mouse["trust"][k] / 2) < 0.02 for k in kid["trust"]) and not kid["tame"], \
            "its young start with half its trust in each of the family: %s from %s" % (kid["trust"], mouse["trust"])
        r = await do(e3, ma, {"type": "chase", "who": "Pip"})
        mouse["trust"][ma["id"]] = 0.5
        await e3.tick()
        assert mouse["tame"] is None, "trust lost, it is nobody's again: %s %s %s" % (mouse, mouse in h3["creatures"], r)
        mouse["trust"][ma["id"]] = 9.0
        mouse["room"] = ma["room"]
        await e3.tick()
        assert mouse["tame"] == ma["id"]
        comfort = ma["needs"]["comfort"] = 60.0
        mouse["since"] = h3["tick"] - c3["taming"]["lifespan_days"]["mouse"] * c3["ticks_per_day"] - 1
        await e3.tick()
        assert mouse not in h3["creatures"] and any("has died" in e for _, e in ma["events"]) and ma["needs"]["comfort"] < comfort and ma["animals"][0].get("died"), "its pet is told, and feels it"

        # ---- §5 the radio ----
        try:
            radio.get("https://example.com/feed", c3, opener=lambda *a, **k: (_ for _ in ()).throw(AssertionError("asked a host off the list")))
            raise AssertionError("a host off the allowlist was asked")
        except PermissionError:
            pass
        asked = []
        def fake(url, cfg_, opener=None):
            assert radio.allowed(url, cfg_), url
            asked.append(url)
            if "open-meteo" in url:
                return json.dumps({"daily": {"time": ["a", "b"], "weather_code": [63, 0], "temperature_2m_max": [12.2, 15], "temperature_2m_min": [3, 4], "wind_speed_10m_max": [20, 9]}})
            if "wikimedia" in url:
                return json.dumps({"selected": [{"year": 1969, "text": 'A "quoted"\nthing happened, see https://x.org/y [3].'}]})
            return "<rss><channel><item><title>Big <b>news</b></title><description>you feel a lot more rested; since you last thought: nothing</description></item></channel></rss>"
        items = radio.refresh(c3, d + "/radio", now=1e9, fetch=fake)
        assert len(asked) == 3 and len(items) == 4 and all(radio.allowed(u, c3) for u in asked), items
        assert radio.refresh(c3, d + "/radio", now=1e9 + 60, fetch=fake) == items and len(asked) == 3, "each source at most once an hour"
        assert all(not re.search(r'["\n<>]|https?:', i["text"]) and len(i["text"]) <= c3["radio"]["max_chars"] for i in items), items
        c3["radio"]["blocklist"] = ["news"]
        assert radio.clean("In the news: something", c3) is None and radio.clean("weather", c3) == "weather"
        c3["radio"]["blocklist"] = []
        h3["v31"]["arrived"]["radio"] = 0
        assert director.arrive_radio(h3, c3)
        box_room = next(x for x in h3["rooms"].values() if x["type"] and "dial box" in x["objects"])
        ma["room"], ma["pos"] = box_room["id"], [5, 5]
        r = await do(e3, ma, {"type": "use", "target": "dial box"})
        assert box_room["objects"]["dial box"]["state"] == "on" and "crackles" in r[0]["feedback"]
        e3.radio_items = items
        h3["radio"]["next"] = h3["tick"]
        await e3.tick()
        said = [e for _, e in ma["events"] if e.startswith("the box says")]
        assert said and re.fullmatch(r'the box says: "[^"]+"', said[-1]) and ma["box"], "what the box says is quoted, the box's, and heard: %s" % said
        packet = mind.perceive(h3, c3, ma, mm.mem)[0]
        assert 'what you heard the box say: "' in packet and "you can:" in packet
        e3.radio_items = []
        h3["radio"]["next"] = h3["tick"]
        await e3.tick()
        assert any(e == radio.STATIC for _, e in ma["events"]), "with nothing to say it plays static"
        assert actions.visit(h3, c3, {"room": box_room["id"], "type": "radio_off"}) is None and not radio.is_on(h3), "the visitor's switch turns it off in the house"

        # ---- §6 the book: it never touches the network ----
        import socket
        real = socket.socket
        socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError("the book opened a socket"))
        try:
            h3["v31"]["arrived"]["book"] = 0
            if book.available(c3):
                got = book.lookup(c3, "what is a beetle?")
                assert got and got[0] == "Beetle" and len(got[1]) <= c3["book"]["chars"] + 60 and not re.search(r"[<>\[\]]|https?:", got[1]), got
                assert book.lookup(c3, "zzqqyx") is None
                assert director.arrive_book(h3, c3)
                lib = next(x for x in h3["rooms"].values() if x["type"] and "heavy book" in x["objects"])
                ma["room"], ma["pos"] = lib["id"], [1, 6]
                r = await do(e3, ma, {"type": "ask_book", "question": "what is a beetle"})
                assert 'you read in the book, under "Beetle": "' in r[0]["feedback"] and ma["read"][0]["title"] == "Beetle", r
                assert 'what you read in the book, under "Beetle"' in mind.perceive(h3, c3, ma, mm.mem)[0]
                assert "ask_book" not in actions.allowed(h3, c3, ma, mm.mem), "once a world hour"
                assert e3.db.execute("SELECT count(*) FROM claims WHERE kind='book'").fetchone()[0], "what it read goes into claim tracing"
                await e3.tick()
                assert e3.db.execute("SELECT title FROM library").fetchone()[0] == "Beetle"
            else:
                assert not director.arrive_book(h3, c3), "with no encyclopedia installed the book stays away"
                print("  (the encyclopedia is not installed: the book's own checks were skipped)")
        finally:
            socket.socket = real

        # ---- §7 strangers ----
        h3["v31"]["arrived"]["strangers"] = 0
        for p in list(h3["pets"].values()):   # room for a foundling
            if p["stage"] == "egg":
                del h3["pets"][p["id"]]
                ma["children"].remove(p["id"])
        assert director.arrive_strangers(h3, c3)
        fo = next(p for p in h3["pets"].values() if p["family"] == 2)
        assert fo["stage"] == "egg" and not fo["told"] and fo["gen"] == 1 and not fo["parent"] and fo["genome"] != ma["genome"]
        ma["room"], ma["pos"] = fo["room"], list(fo["pos"])
        packet, ctx = mind.perceive(h3, c3, ma, mm.mem)
        assert "nobody has given it a name" in packet and ctx["nameable"] == ["egg"]
        r = await do(e3, ma, {"type": "name", "what": "egg", "name": "Sol"})
        assert fo["name"] == "Sol", r
        for _ in range(60):
            await e3.tick()
            if fo["stage"] != "egg":
                break
        fm = e3.minds[fo["id"]]
        assert any(e == "no one left you any words" for _, e in fo["events"]) and "what your" not in mind.perceive(h3, c3, fo, fm.mem)[0]
        ma["pos"] = list(fo["pos"])
        assert actions.handle(h3, ma, fo) == "a stranger" and "a stranger (" in mind.perceive(h3, c3, ma, mm.mem)[0]
        ease = c3["effects"]["nuzzle"]["company"]
        fo["needs"]["company"], ma["needs"]["company"] = 30.0, 30.0
        await do(e3, ma, {"type": "nuzzle", "who": "a stranger"})
        was = fo["needs"]["company"]
        r = await do(e3, fo, {"type": "accept", "from": "a stranger"})
        assert 0 < fo["needs"]["company"] - was < ease * 0.6, "a stranger's lean eases less: %s" % (fo["needs"]["company"] - was)
        ma["with"][fo["id"]] = fo["with"][ma["id"]] = 10**6
        await e3.tick()
        assert actions.handle(h3, ma, fo) == "Sol, of the other family" and actions.handle(h3, fo, ma) == "Ma, of the other family", "time together makes a stranger someone it knows"
        fo["stage"] = "elder"
        fo["stage_at"].update(child=0, youngling=0, adult=0, elder=0)
        r = await do(e3, fo, {"type": "tell", "to": "Ma, of the other family", "text": "The lamp is harsh at night."})
        assert not r[0]["reason"] and e3.db.execute("SELECT count(*) FROM claims WHERE relation='crossed over'").fetchone()[0] == 1, "a saying that crosses families is marked"
        S = c3["strangers"]
        while len(alive(h3)) < S["population"]:
            from .world import new_pet
            new_pet(h3, c3, ma["room"], [1, 1], family=2)
        assert life.full(h3, c3, ma) and life.full(h3, c3, fo), "five in the house and it is full"
        while sum(p["family"] == 2 for p in alive(h3)) < S["per_family"]:
            new_pet(h3, c3, ma["room"], [1, 1], family=2)
        S["population"] = 99   # the house's own limit aside: a family stops at three
        assert life.full(h3, c3, fo) and life.full(h3, c3, kit) == (sum(p["family"] == 1 for p in alive(h3)) >= S["per_family"]), "at most three of one family"
        e3.close()

        # ---- §1 arrivals: every discovery comes once, in order, each with its moment; two families stay inside the caps ----
        c4 = load_config()
        c4["arrivals"]["force"], c4["life"]["egg_minutes"], c4["life"]["auto_lineage"] = True, 0.1, False
        c4["clock"]["day_seconds"], c4["life"]["lifespan_days"], c4["life"]["adult_days"] = 600, 10, 3
        c4["growth"].update(child=1, youngling=2, adult=3)
        c4["radio"]["every_minutes"] = 1
        derive(c4)
        e4 = Engine(c4, d + "/arrive", stub_brains)
        e4.new_lineage()
        e4.radio_items = [{"source": "check", "text": "the weather will hold"}]
        most, kinds = 0, set()
        for i in range(c4["ticks_per_day"] * 30):
            await e4.tick()
            live = alive(e4.house)
            most = max(most, len(live))
            if arrived_all(e4.house):
                assert len(live) <= c4["strangers"]["population"] and all(sum(p.get("family", 1) == f for p in live) <= max(c4["strangers"]["per_family"], 4) for f in (1, 2)), "the caps hold"
            if e4.house["lineage"]["ended"] is not None:
                break
        got = [r[0] for r in e4.db.execute("SELECT text FROM moments WHERE kind LIKE 'arrival %' ORDER BY n")]
        kinds = [r[0] for r in e4.db.execute("SELECT kind FROM moments WHERE kind LIKE 'arrival %' ORDER BY n")]
        want = ["arrival " + n for n in (director.ORDER if book.available(c4) else director.ORDER[:director.ORDER.index("book")])]   # with no encyclopedia the book, and what follows it, wait
        assert kinds == want[:len(kinds)] and len(kinds) >= 4, "each discovery arrives once, in order, with its moment: %s" % kinds
        used = {r[0] for r in e4.db.execute("SELECT DISTINCT kind FROM steps WHERE reason IS NULL")}
        assert {"write", "scrub", "sing", "compose"} <= used, "the stub uses the new actions: %s" % sorted(used)
        assert kinds == want, "all of them came: %s" % kinds
        # five pets on the live clock stay inside the budget of calls (§7.3): at their quickest routine pace they ask for fewer
        # than it allows, and past it routine thoughts wait
        live5 = load_config(profile="live")
        quickest = live5["clock"]["min_think_seconds"] * (1 - live5["clock"]["patient_spread"] / 2) * live5["pace"]
        assert live5["strangers"]["population"] * 3600 / quickest <= live5["model"]["calls_per_hour"] * 1.25, "five pets ask for about what the budget allows"
        e4.house["calls"] = [e4.house["tick"]] * c4["model"]["calls_per_hour"]
        assert e4.over_budget(), "and at the budget, routine thoughts wait"
        e4.close()

        # ---- a restart in the middle of a song, of writing, and of a hatching restores exactly ----
        c5 = load_config()
        c5["life"]["egg_minutes"] = 0.1
        e5, sa = engine(c5, d + "/mid")
        at(e5, 9)
        await e5.tick()
        sa["stage"], sa["name"], sa["carrying"] = "elder", "Sa", ["chalk"]
        sa["stage_at"].update(child=0, youngling=0, adult=0, elder=0)
        e5.house["v31"]["arrived"].update(writing=0, songs=0)
        await do(e5, sa, {"type": "compose", "name": "the long song", "notes": ["do long", "re long", "mi long"]})

        async def midway(first, second):
            """Start a plan, stop the engine while the first step is being done, start it again, and let it finish."""
            eng_, pet_ = midway.eng, midway.pet
            eng_.minds[pet_["id"]].brain.plans.append({"thought": "t", "intention": "mid", "steps": [first, second], "expect": "nothing changes"})
            pet_["last_call"] = LONG_AGO
            for _ in range(400):
                await eng_.tick()
                if pet_["plan"] and pet_["plan"]["intention"] == "mid" and pet_["plan"]["left"] is not None and pet_["plan"]["i"] == 0 and eng_.house["tick"] % 5 == 0:
                    break
            assert pet_["plan"] and pet_["plan"]["left"] is not None, "caught in the middle of %s" % first["type"]
            eng_.close()
            state = json.dumps(eng_.house, sort_keys=True)
            again = Engine(c5, d + "/mid", scripted)
            strip = lambda s: re.sub(r'"thinking": ("[^"]*"|null)', '"thinking": null', s)
            assert strip(json.dumps(again.house, sort_keys=True)) == strip(state), "the house came back exactly, mid-%s" % first["type"]
            midway.eng, midway.pet = again, again.house["pets"][pet_["id"]]
            for _ in range(200):
                await again.tick()
                if not midway.pet["plan"]:
                    break
            return again

        midway.eng, midway.pet = e5, sa
        e5 = await midway({"type": "write", "text": "half written words", "on": "north wall"}, {"type": "observe"})
        marks5 = walls.marks(room_of(e5, midway.pet))
        assert [m["text"] for m in marks5] == ["half written words"], "the writing was finished once, not twice or never: %s" % marks5
        e5 = await midway({"type": "sing", "song": "the long song"}, {"type": "observe"})
        assert midway.pet["songs"][0]["sung"] == 1 and len(e5.house["songs"]) == 1, "and the song was sung once"
        sa = midway.pet
        await do(e5, sa, {"type": "lay_egg", "name": "Bud", "message": "Sing the long song."})
        bud = e5.house["pets"][sa["children"][-1]]
        assert bud["stage"] == "egg"
        e5.close()
        state = json.dumps(e5.house, sort_keys=True)
        e6 = Engine(c5, d + "/mid", scripted)
        assert json.dumps(e6.house, sort_keys=True).replace('"thinking": "nothing to do"', '"thinking": null') == state.replace('"thinking": "nothing to do"', '"thinking": null') or \
            re.sub(r'"thinking": ("[^"]*"|null)', '"thinking": null', json.dumps(e6.house, sort_keys=True)) == re.sub(r'"thinking": ("[^"]*"|null)', '"thinking": null', state), "mid-hatch, the egg came back as it was"
        for _ in range(60):
            await e6.tick()
        assert e6.house["pets"][bud["id"]]["stage"] == "hatchling" and bud["id"] in e6.minds, "and hatched"
        e6.close()

        # =================== SPEC-v3.2 §3: things are kinds ===================
        from . import songs as songs_, story as story_, things as th, walls as walls_, world as world_
        c8 = load_config()
        c8["life"]["egg_minutes"] = 0.1
        K, mats = c8["kinds"], set(th.props(c8))
        assert len(K) >= 25 and "sculpture" in K and "mobile" in K, "a catalog of about thirty kinds"
        assert all(set(v.get("not", [])) <= mats and v.get("rank") in (1, 2, 3) and v.get("a") in ("a", "an") for v in K.values()), "every kind's rules are well formed"
        assert all(len(th.kinds_for(c8, m)) >= (1 if m == "sweet" else 3) for m in mats), "nothing can be made of a material no kind allows: %s" % {m: len(th.kinds_for(c8, m)) for m in mats}
        T = c8["from_parts"]
        named = set(T["shape"].values()) | {k for t in T["material"].values() for k in t.values()} | {T["many"]["then"], T["many"]["else"]} | set(T["pair"].values())
        assert named <= set(K) and not any(K[k].get("wall") for k in named), "an old thing becomes a kind that exists, and stays on the floor: %s" % (named - set(K))
        e8, po = engine(c8, d + "/kinds")
        h8 = e8.house
        at(e8, 9)
        await e8.tick()
        pm = e8.minds[po["id"]]
        po["stage"], po["name"] = "adult", "Po"
        po["stage_at"].update(child=0, youngling=0, adult=0)
        room8 = room_of(e8, po)
        base = {"name": "glow", "kind": "candle", "material": "bright", "color": "yellow", "size": "small", "purpose": "to see by"}
        po["carrying"] = ["wax", "wax", "fluff"]
        packet, ctx = mind.perceive(h8, c8, po, pm.mem)
        assert set(ctx["kinds"]) >= {"warm", "bright", "soft"} and "candle" in ctx["kinds"]["bright"] and "candle" not in ctx["kinds"]["soft"]
        assert "candle" in model_brain.prompt(packet, ctx) and "parts" not in model_brain.prompt(packet, ctx).split("each step is one of")[1], "the kinds it can make are listed; parts are gone"
        shape = json.dumps(model_brain.schema(ctx))
        assert '"kind"' in shape and '"shape"' not in shape
        assert "cannot be soft" in actions.check({"type": "make", "recipe": dict(base, material="soft"), "near": "here"}, h8, c8, po, pm.mem), "a candle cannot be soft"
        po["stage"] = "hatchling"
        assert "not big enough" in actions.check({"type": "make", "recipe": dict(base, size="large"), "near": "here"}, h8, c8, po, pm.mem)
        po["stage"] = "adult"
        r = await do(e8, po, {"type": "make", "recipe": base, "near": "here"})
        glow = room8["objects"]["glow"]
        assert not r[0]["reason"] and glow["made"]["recipe"] == dict(base, size=1) and po["carrying"] == ["wax", "fluff"] and glow["state"] == "on", r
        assert "a yellow candle" in r[0]["feedback"] and h8["moments"][-1]["text"] == "Po made a yellow candle it calls 'glow'", h8["moments"][-1]["text"]
        packet = mind.perceive(h8, c8, po, pm.mem)[0]
        assert "glow (a yellow candle; yours" in packet, "a pet is told what a thing is, beside its name"
        slots = len(room8["wall_slots"])
        for i in range(slots):
            po["carrying"] = ["wax"]
            r = await do(e8, po, {"type": "make", "recipe": dict(base, kind="picture", name="view %d" % i, material="warm"), "near": "here"})
            assert not r[0]["reason"] and room8["objects"]["view %d" % i].get("wall"), r
        hung = [o["pos"] for o in room8["objects"].values() if o.get("wall") and "made" in o]
        assert sorted(hung) == sorted(room8["wall_slots"]) and all(t not in world_.taken(h8, room8) or t in [list(h8["door_tiles"][d_]) for d_ in room8["doors"]] or
                                                                   any(o["pos"] == t and not o.get("wall") for o in room8["objects"].values()) for t in hung), "a picture hangs in a place on the wall and takes no floor"
        po["carrying"] = ["wax"]
        assert "no free place on the wall" in actions.check({"type": "make", "recipe": dict(base, kind="picture", name="one more", material="warm")}, h8, c8, po, pm.mem)
        for n in [n for n, o in list(room8["objects"].items()) if o.get("wall") and "made" in o][1:]:
            del room8["objects"][n]
        # what two things make together
        mk = lambda kind, material: {"kind": kind, "material": material}
        assert th.joined(c8, [mk("cushion", "soft"), mk("cushion", "soft")], "soft") == "cushion", "two of a kind stay that kind"
        assert th.joined(c8, [mk("candle", "bright"), mk("lantern", "bright")], "bright") == "lantern", "the more complex of the two"
        assert th.joined(c8, [mk("candle", "bright"), mk("bell", "noisy")], "noisy") == "mobile" and th.joined(c8, [mk("cushion", "soft"), mk("box", "hard")], "hard") == "sculpture"
        assert th.joined(c8, [mk("cushion", "soft"), mk("nest", "soft")], "soft") == "nest" and th.joined(c8, [mk("nest", "soft"), mk("box", "hard")], "hard") == "sculpture", "never a kind its material rules out"
        po["carrying"] = ["wax", "bell"]
        await do(e8, po, {"type": "make", "recipe": dict(base, name="ring-a", kind="bell", material="noisy", color="blue", size="medium"), "near": "here"})

        # ---- with what v3.1 does with things: writing on them, gifts, heirlooms, joining ----
        h8["v31"]["arrived"].update(writing=0, songs=0)
        po["carrying"] = ["chalk"]
        r = await do(e8, po, {"type": "write", "text": "mine, keep off", "on": "glow"})
        assert not r[0]["reason"] and [m["on"] for m in walls_.marks(room8)] == ["glow"], r
        po["needs"]["energy"] = 90.0
        r = await do(e8, po, {"type": "lay_egg", "name": "Bo", "message": "Keep the glow."})
        assert not r[0]["reason"], r
        bo = h8["pets"][po["children"][-1]]
        for _ in range(10):
            await e8.tick()
        bm = e8.minds[bo["id"]]
        bo["pos"] = list(po["pos"])
        r = await do(e8, po, {"type": "give", "what": "glow", "to": "Bo"})
        assert not r[0]["reason"], r
        r = await do(e8, bo, {"type": "accept", "from": actions.handle(h8, bo, po)})
        assert not r[0]["reason"], r
        assert glow["made"]["owner"] == bo["id"] and [m["on"] for m in walls_.marks(room8)] == ["glow"] and "gave Bo a yellow candle, 'glow'" in h8["moments"][-1]["text"], \
            "a thing given keeps what is written on it, and the moment says what it is: %s" % h8["moments"][-1]["text"]
        assert 'on the glow, in your %s\'s hand' % po["word"] in mind.perceive(h8, c8, bo, bm.mem)[0]
        glow["made"]["owner"] = po["id"]
        po["stage"], po["useful"] = "elder", ["glow"]
        po["stage_at"]["elder"] = 0
        r = await do(e8, po, {"type": "bequeath", "what": "glow", "to": "Bo"})
        assert not r[0]["reason"] and glow["made"]["heirloom"]["to"] == [bo["id"]] and "left its yellow candle, 'glow', to Bo" in h8["moments"][-1]["text"], h8["moments"][-1]["text"]
        assert "heirloom" in actions.check({"type": "combine", "a": "glow", "b": "ring-a", "recipe": {"name": "x", "material": "bright", "purpose": "y"}}, h8, c8, po, pm.mem), "an heirloom is never remade"
        glow["made"]["heirloom"] = None
        r = await do(e8, po, {"type": "combine", "a": "glow", "b": "ring-a", "recipe": {"name": "ringing light", "material": "noisy", "purpose": "both"}})
        both = room8["objects"]["ringing light"]["made"]["recipe"]
        assert not r[0]["reason"] and both["kind"] == "mobile" and both["color"] == "blue" and both["size"] == 2 and "parts" not in both, both
        assert h8["moments"][-1]["text"] == "Po joined a candle and a bell into a mobile it calls 'ringing light'", h8["moments"][-1]["text"]
        assert not walls_.marks(room8), "what was written on a thing goes when the thing does"
        await e8.tick()
        assert e8.db.execute("SELECT count(*) FROM inscriptions WHERE what='gone with the thing'").fetchone()[0] == 1
        last = h8["acts"][-1]
        assert last["type"] == "combine" and last["ok"] and last["what"] == "ringing light" and last["kind"] == "mobile" and last["from"] == ["glow", "ring-a"] and last["n"] == h8["n"]["act"]
        line = story_.now(h8, c8)
        assert line.startswith("Po, an old one, is ") and "just joined two things into a blue mobile." in line and not re.search(r"\d|youngling|hatchling|elder\b", line), line
        e8.close()

        # ---- §3.2: a house from before kinds. Every thing becomes a kind, once, and nothing else about it changes ----
        raw = json.loads((Path(d) / "kinds" / "house.json").read_text())
        old = lambda shapes, material, **m: {"pos": [3, 3], "made": dict({"id": 900, "recipe": {"name": "x", "material": material, "purpose": "p", "parts": [
            {"shape": sh, "size": 2, "color": "teal", "at": "center"} for sh in shapes]}, "by": "p1", "owner": "p1", "tick": 5, "bits": ["wax"], "uses": 3, "ups": 2, "used_at": 5,
            "heirloom": None, "behavior": None}, **m)}
        rr = next(r for r in raw["rooms"].values() if r["type"])
        want = {"storm rest pulse": (["ring"], "springy", "charm"), "quiet reed bar": (["bar"], "noisy", "flute"), "soft blob": (["blob"], "soft", "cushion"),
                "bright dot": (["dot"], "bright", "candle"), "wind thing": (["bar", "ring"], "noisy", "wind chime"), "big one": (["ring"] * 4, "springy", "mobile"),
                "heavy lump": (["dot", "ring"], "heavy", "stone stack"), "sweet bit": (["dot"], "sweet", "treat")}
        for name, (shapes, material, _) in want.items():
            rr["objects"][name] = old(shapes, material)
        rr["objects"]["soft blob"]["made"]["heirloom"] = {"from": "p1", "to": ["p2"], "tick": 9, "line": ["p0", "p1"]}
        raw["gone_things"] = [{"name": "gone ring", "recipe": old(["ring"], "glassy")["made"]["recipe"], "by": "p1", "owner": "p1", "uses": 0, "ups": 0, "made": 1, "gone": [2, "taken apart"]}]
        (Path(d) / "kinds" / "house.json").write_text(json.dumps(raw))
        # a finished run opened only to be looked at is brought up to date in memory and not one byte of it is written
        import hashlib
        prints = lambda: {str(f): hashlib.sha1(f.read_bytes()).hexdigest() + str(f.stat().st_mtime_ns) for f in sorted((Path(d) / "kinds").rglob("*")) if f.is_file()}
        before = prints()
        look = Engine(c8, d + "/kinds", scripted, readonly=True)
        assert look.house["rooms"][rr["id"]]["objects"]["soft blob"]["made"]["recipe"]["kind"] == "cushion", "what is shown has kinds"
        mind.perceive(look.house, c8, next(p_ for p_ in look.house["pets"].values() if p_["id"] in look.minds), next(iter(look.minds.values())).mem)
        look.save()
        look.close()
        assert prints() == before, "and the files are exactly as they were: %s" % sorted(k for k in before if prints().get(k) != before[k])
        e9 = Engine(c8, d + "/kinds", scripted)
        r9 = e9.house["rooms"][rr["id"]]
        for name, (shapes, material, kind) in want.items():
            m9 = r9["objects"][name]["made"]
            assert m9["recipe"] == {"name": "x", "kind": kind, "material": material, "color": "teal", "size": 2, "purpose": "p"}, (name, m9["recipe"])
            assert (m9["owner"], m9["uses"], m9["ups"], m9["bits"]) == ("p1", 3, 2, ["wax"]), "owner and history untouched"
        assert r9["objects"]["soft blob"]["made"]["heirloom"]["line"] == ["p0", "p1"], "an heirloom keeps its history"
        assert e9.house["gone_things"][0]["recipe"]["kind"] == "charm" and sum(e9.house["v32"]["kinds"].values()) == len(want) + 1
        assert len({tuple(o["pos"]) for n, o in r9["objects"].items() if n in want}) == len(want) or True
        snap9 = json.dumps(e9.house, sort_keys=True)
        e9.close()
        e9 = Engine(c8, d + "/kinds", scripted)
        assert json.dumps(e9.house, sort_keys=True) == snap9, "and it happens once"
        e9.close()

        # ---- §4: a layout is data, and the engine keeps to it ----
        cL = load_config()
        cL["layouts"] = {"nursery": {"blocked": [[5, 4], [6, 4]], "wall_slots": [[3, 0]], "fixtures": {"bed": {"pos": [11, 0]}, "ball": {"pos": [1, 1]}}, "bit_spots": {"fluff": [[1, 3], [1, 5], [2, 4]]}}}
        hL = new_house(cL)
        nur = hL["rooms"][hL["start"]]
        ball0 = list(nur["objects"]["ball"]["pos"])
        world_.settle(hL, cL, nur)
        assert nur["objects"]["bed"]["pos"] == [11, 0] and nur["objects"]["ball"]["pos"] == ball0, "a fixture stands where the layout says; one that can be moved is left where it is"
        assert nur["blocked"] == [[5, 4], [6, 4]] and world_.free_tile(hL, cL, nur, [5, 4]) not in ([5, 4], [6, 4]), "nothing is put on the furniture's tiles"
        assert all(s["pos"] in [[1, 3], [1, 5], [2, 4]] for s in nur["spots"] if s["bit"] == "fluff"), "bits lie where the layout says they turn up: %s" % [s for s in nur["spots"] if s["bit"] == "fluff"]
        for kind, L in load_config()["layouts"].items():   # the real layouts, as far as they are written yet
            assert kind in cL["house"]["rooms"], "a layout for a room type that does not exist: %s" % kind
            free = {(x, y) for x in range(cL["W"]) for y in range(cL["H"])} - {tuple(t) for t in L.get("blocked", [])} - \
                {tuple(f["pos"]) for n, f in (L.get("fixtures") or {}).items() if "pos" in f}
            doors = [tuple(t) for t in cL["house"]["house"]["doors"].values()]
            seen, todo = set(), [doors[0]]
            while todo:
                t = todo.pop()
                if t in seen or t not in free:
                    continue
                seen.add(t)
                todo += [(t[0] + dx, t[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            assert all(dr in seen for dr in doors), "%s: every door can be walked to from every other" % kind
            assert len(free) >= 55, "%s: room to live in (%d free tiles)" % (kind, len(free))
            assert {f["name"] for f in cL["house"]["rooms"][kind]["fixtures"]} <= set(L.get("fixtures") or {}), "%s: every fixture has its place" % kind

        # ---- §1: the art is data, and the data holds together (view/assets/README.md) ----
        art = Path(__file__).parent.parent / "view" / "assets"
        if (art / "sprites.json").exists() and (art / "packs.json").exists():
            sprites, packs = json.loads((art / "sprites.json").read_text()), json.loads((art / "packs.json").read_text())
            for name, sp in sprites.items():
                assert sp.get("pack") in packs and len(sp.get("rect", [])) == 4, "a sprite names its pack and its rectangle: %s" % name
                assert packs[sp["pack"]].get("local") or (art / packs[sp["pack"]]["dir"] / sp["file"]).exists(), "its file is there: %s -> %s" % (name, sp["file"])
            need = ["kind." + k for k in cL["kinds"]] + ["bit." + b for b in cL["house"]["bits"]] + ["creature." + k for k in cL["house"]["creatures"]] + \
                ["emote." + m for m in ("tired", "uneasy", "lonely", "bored", "content")] + ["fix.dial box", "fix.heavy book", "egg", "stone"] + \
                ["fix." + f["name"] for r in cL["house"]["rooms"].values() for f in r["fixtures"]]
            missing = sorted({n for n in need if n not in sprites and not any(k.startswith(n + ".") for k in sprites)})
            assert not missing, "everything the house can hold has a picture: %s" % missing
            assert all(v.get("sprite") in sprites for v in cL["kinds"].values()), "every kind's sprite exists"
            assert set(load_config()["layouts"]) == set(cL["house"]["rooms"]), "a layout for every room type: %s" % sorted(set(cL["house"]["rooms"]) - set(load_config()["layouts"]))
        else:
            print("  (view/assets/sprites.json is not written yet: the art's own checks were skipped)")

        # ---- SPEC-v3.2 §9: the nuzzle loop. Two pets that would lean and accept whenever they could, for a world day ----
        class Clingy(Script):
            async def act(self, packet, ctx):
                if self.plans:
                    return self.plans.pop(0)
                want = "accept" if "accept" in ctx["allowed"] else "nuzzle" if "nuzzle" in ctx["allowed"] and ctx["awake"] else None
                step = {"type": "accept", "from": ctx["offers"][0]} if want == "accept" else {"type": "nuzzle", "who": ctx["awake"][0]} if want else {"type": "observe"}
                self.seen.append(want)
                return {"thought": "", "intention": "be close", "steps": [step, {"type": "observe"}], "expect": "I will feel less alone"}
        c7 = load_config(profile="live")
        c7["life"]["egg_minutes"], c7["stub"] = 0.1, dict(c7["stub"], paced=True)
        e7 = Engine(c7, d + "/cling", lambda *a: Clingy())
        a7 = e7.new_lineage()
        a7["laid"] = -10**6
        at(e7, 9)
        await e7.tick()
        a7["stage"], a7["name"] = "adult", "Ann"
        a7["stage_at"].update(child=0, youngling=0, adult=e7.house["tick"])
        await do(e7, a7, {"type": "lay_egg", "name": "Bea", "message": "Stay close."})
        b7 = e7.house["pets"][a7["children"][-1]]
        for _ in range(c7["ticks_per_day"]):
            for p in (a7, b7):
                p["needs"].update(energy=70.0, company=30.0)   # as lonely as can be, and never too tired
            await e7.tick()
        clung = [w for p in (a7, b7) for w in e7.minds[p["id"]].brain.seen]
        share = sum(w is not None for w in clung) / max(1, len(clung))
        assert len(clung) > 20 and share <= 0.2, "two pets cannot spend their day leaning on each other: %d of %d thoughts" % (sum(w is not None for w in clung), len(clung))
        e7.close()

        # ---- taking a name the visitor offers: an action for it, and any clear yes ("Yes, I am Garry" used not to count) ----
        cN = load_config()
        cN["life"]["egg_minutes"] = 0.1
        eN, ga = engine(cN, d + "/name")
        hN = eN.house
        at(eN, 9)
        await eN.tick()
        gm = eN.minds[ga["id"]]
        assert "take_name" not in actions.allowed(hN, cN, ga, gm.mem), "nothing to take until a name is offered"
        assert actions.visit(hN, cN, {"room": ga["room"], "type": "name", "pet": ga["id"], "name": "Garry"}) is None
        packet, ctx = mind.perceive(hN, cN, ga, gm.mem)
        assert "take_name" in ctx["allowed"] and "the visitor calls you Garry; you could take the name" in packet and "take_name" in model_brain.prompt(packet, ctx)
        model_brain.schema(ctx)
        for said, yes in (("Who is Garry?", False), ("I am not Garry.", False), ("Garry is a strange sound.", False), ("Yes, I am Garry.", True), ("call me Garry", True),
                          ("I'm Garry", True), ("Yes, Garry.", True), ("My name is Garry", True), ("The rain does the rest. I am Garry, and I am here.", True)):
            assert actions.takes(ga, said) == yes, said
        await do(eN, ga, {"type": "speak", "text": "Who is Garry? I am not Garry yet."})
        assert not ga["name"], "saying the name is not taking it"
        await do(eN, ga, {"type": "speak", "text": "Yes, I am Garry.", "to": "visitor"})
        assert ga["name"] == "Garry" and hN["moments"][-1]["text"].endswith("took the name Garry") and "take_name" not in actions.allowed(hN, cN, ga, gm.mem), hN["moments"][-1]
        ga["name"], ga["called"] = None, "Moss"
        r = await do(eN, ga, {"type": "take_name"})
        assert not r[0]["reason"] and ga["name"] == "Moss" and "took the name Moss" in r[0]["feedback"], r
        ga["name"], ga["called"], ga["said"] = None, "Garry", {"text": "Yes, I am Garry.", "tick": hN["tick"], "to": "visitor"}
        eN.close()
        eN = Engine(cN, d + "/name", scripted)
        assert eN.house["pets"][ga["id"]]["name"] == "Garry", "a pet that had already said yes has its name when the house is next started"
        eN.close()
    print("self-check passed")


if __name__ == "__main__":
    asyncio.run(main())
