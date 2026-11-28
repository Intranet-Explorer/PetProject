"""Laying is the body's, as making is (20 October 2026). Under brain4 lay_egg was a rare model step that nothing
in the body ever did: on live nobody laid for twelve days. Now a grown hob that could lay (`life.can_lay` but for being
tired) for `[population] lay_after_days` is given a "lay" aim: to the nursery if it knows it. There, awake and rested
(or anywhere, half a day later), the step asks the model one thought, what it tells the egg and what it
names it, and `life.lay_egg` runs with the reply. A failed or missing reply is never a failed egg: the engine's words
stand in. `[population] lay = false` turns it fully off.

    (tick.py, each tick) laying.tick(eng)
"""
import asyncio

from . import contracts as K
from . import actions, life, names
from .world import add_event, alive, hours, label

TEXT = "lay my egg somewhere safe"
WORDS = "Keep warm, stay close to the family, and be kind."   # (what the egg is told when no reply came)


def on(cfg):
    """(brain4's: under v3.6c's mind the model laid as often as it liked)"""
    return bool(cfg.get("population", {}).get("lay") and cfg.get("brain4", {}).get("on"))


def fertile(house, cfg, pet):
    """Could it lay, being rested: grown, an egg left in it, room in the house."""
    return pet["stage"] in ("adult", "elder") and "lay_egg" in life.unlocked(house, pet["stage"]) and pet["eggs"] < life.fertility(pet) \
        and not life.full(house, cfg, pet)


def aim_of(pet):
    return next((a for a in pet.get("aims") or [] if a["kind"] == "lay" and not a.get("done") and not a.get("failed")), None)


def tick(eng):
    h, cfg = eng.house, eng.cfg
    if not on(cfg) or not h.get("lineage"):
        return
    day = hours(cfg, 24)
    for pet in alive(h):
        if pet["stage"] == "egg":
            continue
        if not fertile(h, cfg, pet):
            pet.pop("fertile_since", None)
            continue
        since = pet.setdefault("fertile_since", h["tick"])
        if h["tick"] - since < day * cfg["population"]["lay_after_days"]:
            continue
        a = aim_of(pet)
        if not a:
            nursery = next((r for r in pet["rooms"] if h["rooms"][r]["type"] == "nursery"), None)
            a = {"text": TEXT, "why": "there is an egg in you", "kind": "lay", "target": nursery, "since": None, "done": None, "eggs0": pet["eggs"]}
            pet["aims"] = [a] + (pet.get("aims") or [])   # (first: what the day is for now; the morning's plan may drop it, and it is given again)
        there = a["target"] in (None, pet["room"]) or h["tick"] - since >= day * (cfg["population"]["lay_after_days"] + 0.5)   # (half a day on, wherever it is)
        busy = h["tick"] - pet.get("laying", -day) < hours(cfg, 2)   # (a mark left by a restart mid-thought runs out)
        if there and not pet["sleep"] and not busy and life.can_lay(h, cfg, pet) is None:
            pet["laying"] = h["tick"]
            eng.spawn(lay(eng, pet, a))


def packet(house, cfg, pet):
    """What it is asked (no numbers: SPEC-v4.2)."""
    bits = ["You are %s, a hob of this house." % label(pet)]
    if pet.get("voice"):
        bits.append("How you talk: %s." % K.voice_line(pet["voice"]))
    if pet.get("drive"):
        bits.append("You want %s." % K.drive(pet["drive"])["name"])
    told = next((t["text"] for t in reversed(pet.get("told") or []) if t["kind"] in ("message", "last words")), None)
    if told:
        bits.append('When you were an egg you were told: "%s"' % told)
    bits += ["You are about to lay an egg. What do you tell it, in a few sentences it will carry all its life, and what do you name it?",
             names.line(house, cfg, pet) + ".",
             'Reply with one JSON object and nothing else: {"message": "<what you tell the egg>", "name": "<its name>"}']
    return "\n".join(bits)


SCHEMA = {"type": "object", "additionalProperties": False, "required": ["message", "name"],
          "properties": {"message": {"type": "string", "minLength": 1, "maxLength": 600}, "name": {"type": "string", "maxLength": 16}}}


async def ask(eng, pet):
    """The one react thought, or None where no model is asked (the stub) or it failed."""
    m = eng.minds.get(pet["id"])
    brain = m.brain if m else None
    if brain is None or getattr(brain, "instant", False) or not hasattr(brain, "chat"):
        return None
    from .brain4 import PRIORITY
    from .brains.model import parse
    text = packet(eng.house, eng.cfg, pet)

    async def fn():
        think, most, warm = K.thinking(eng.cfg, "react")
        return parse(await asyncio.to_thread(brain.chat, text, SCHEMA, think, most, warm, "react"))
    try:
        return await eng.call(PRIORITY["react"], pet["id"], "react", "about to lay an egg", fn, len(text))
    except Exception:
        return None


async def lay(eng, pet, a):
    h, cfg = eng.house, eng.cfg
    try:
        reply = await ask(eng, pet)
        reply = reply if isinstance(reply, dict) else {}
        if pet["stage"] == "dead" or life.can_lay(h, cfg, pet) is not None:
            return
        words, name = actions.clean(reply.get("message") or "", 640) or WORDS, actions.clean(reply.get("name") or "", 16)
        if name and any((p["name"] or "").lower() == name.lower() for p in alive(h)):
            name = ""   # (two of one name at once: nobody could tell who was meant; the engine names it)
        said, fx, _ = life.lay_egg(h, cfg, pet, {"message": words, "name": name}, actions.clean)
        actions.bump(pet, cfg, fx)
        add_event(h, pet, said)
        a["done"] = h["tick"]
        pet.pop("fertile_since", None)
    finally:
        pet.pop("laying", None)
