"""Self-check (SPEC §18, SPEC-v3 §0, §11.2): the engine's rules, proved without a model.

    uv run python -m engine.check

A scripted brain plays the plans each check gives it, so every action goes through the same loop the real
pets use. Ends with a stub-brain lineage run and a restart in the middle of one."""
import asyncio
import json
import re
import tempfile

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
        recipe = {"name": "Soft Nest", "material": "soft", "purpose": "to lie in", "parts": [{"shape": "blob", "size": 3, "color": "white", "at": "center"}]}
        energy = pet["needs"]["energy"]
        r = await do(eng, pet, {"type": "make", "recipe": recipe, "near": "bed"}, {"type": "observe"})
        assert not r[0]["reason"], r[0]
        nest = room_of(eng, pet)["objects"]["soft nest"]
        assert pet["carrying"] == ["wax"] and nest["made"]["bits"] == ["fluff"] and nest["made"]["owner"] == pet["id"], "a part uses up the bit that fits"
        assert "yours" in mind.perceive(h, cfg, pet, m.mem)[0].split("soft nest (")[1].split(")")[0], "every thing says whose it is"
        r = await do(eng, pet, {"type": "make", "recipe": dict(recipe, name="hard thing", material="hard"), "near": "here"}, {"type": "observe"})
        assert not r[0]["reason"] and "pebble" in room_of(eng, pet)["objects"]["hard thing"]["made"]["bits"], "what it is short of, it picks up on the way"
        things.unmake(h, cfg, pet, "hard thing")
        room_of(eng, pet)["spots"] = [s for s in room_of(eng, pet)["spots"] if not s["loose"]]
        pet["carrying"] = ["wax"]
        r = await do(eng, pet, {"type": "make", "recipe": dict(recipe, name="sweet thing", material="sweet"), "near": "here"}, {"type": "observe"})
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
        for _ in range(3):
            pet["needs"]["company"] = egg["needs"]["company"] = 40
            await do(eng, egg, {"type": "nuzzle", "who": "your " + word}, {"type": "observe"})
            r = await do(eng, pet, {"type": "accept", "from": "Sol"}, {"type": "observe"})
        assert r[0]["own"]["company"] < first * 0.6, "the same closeness eases less each time"
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
