"""SPEC-v4.2 §4.4 the self-page (helper B): five short lines a hob keeps about itself (contracts.SELF: who I am, what I
am for, what I have lost, what I fear, what I owe or am owed), in pet["self"], the first block of every packet it
thinks with. A hatchling's and a child's is written by the engine from its kin's words (`engine_page`); from the
youngling stage the model writes it, first from its drive, flaw and first days, then each night in the reflection
(changing at most two lines). pet["last_self"] is the latest page, which the life record keeps at a death (A's
life.die / story.life_record read it). Switch: [selfpage] on."""
from . import contracts as K
from .character import parents_of
from .world import label

LITTLE = ("hatchling", "child")
# SPEC-v4.2.2 §3: how the self-page is written, with the example the model is given (the reflection's, and the migration's)
RULE = "the way you'd tell a neighbour. No poetry. Say what happened and how you feel about it, not what it means."
PLAIN = """Five plain sentences, """ + RULE + """ Each line under thirty words. For example:
who I am: I'm Pansy. Spoon's daughter. I'm the one who keeps the workbench in order.
what I'm for: I want to make something that's still here after I'm gone. A hinge, maybe. Something people use.
what I've lost: Spoon died two days ago. Old age. The house is quiet without her and I don't like it.
what I'm afraid of: Dying at fifteen days like she did, before I've made anything that lasts.
what I owe: I owe Antonia more patience. I told her to walk before she could and that was me being proud."""


def on(cfg):
    return K.on(cfg, "selfpage")


def write(house, cfg, pet, page, by="model"):
    """The self-page set (from the reflection's `self`, or the engine's for a little one)."""
    if not on(cfg):
        return None
    pet["self"] = K.self_page(page)
    pet["self_by"], pet["last_self"] = by, {"page": pet["self"], "tick": house["tick"], "by": by}
    return pet["self"]


def engine_page(house, cfg, pet):
    """The page the engine writes for a little one, from what its kin have said and what it has lived."""
    kin = parents_of(house, pet) or ([house["pets"][pet["kin"]]] if pet.get("kin") in house["pets"] else [])
    first = kin[0] if kin else None
    told = next((t["text"] for t in pet.get("told", []) if t.get("kind") in ("message", "last words")), "")
    lost = [p for p in kin if p["stage"] == "dead"]
    fear = max((m for m in pet.get("memories", []) if m.get("kind") in ("hurt", "injury", "fight", "death", "grief", "harm")), key=lambda m: m["weight"], default=None)
    drive = K.drive(pet["drive"])["name"] if pet.get("drive") else ""
    a = "an" if pet["stage"][0] in "aeiou" else "a"
    return K.self_page({
        "who I am": "%s, %s %s of %s's family" % (label(pet), a, pet["stage"], label(first)) if first else "%s, %s %s of the house" % (label(pet), a, pet["stage"]),
        "what I am for": "I think I am here %s" % drive if drive else ('my %s told me: %s' % (first.get("word") or "kin", told.split(".")[0]) if first and told else "I do not know yet; I am small"),
        "what I have lost": "; ".join("my %s, %s" % (p.get("word") or "kin", label(p)) for p in lost) or "nothing yet",
        "what I fear": fear["text"] if fear else "the dark, and being left alone",
        "what I owe or am owed": "I owe %s for keeping me" % label(first) if first and first["stage"] != "dead" else "I am owed a home by the house",
    })


def page(house, cfg, pet):
    """The page a packet shows: a little one's is the engine's, always; a grown one's its own (the engine's until it
    has written one)."""
    if pet["stage"] in LITTLE or not pet.get("self"):
        return engine_page(house, cfg, pet)
    return K.self_page(pet["self"])


def lines(house, cfg, pet):
    """The packet's first block, or nothing with [selfpage] off."""
    if not on(cfg):
        return []
    return ["how you see yourself:"] + ["  " + x for x in K.self_lines(page(house, cfg, pet))]


def wants_first(pet):
    """A grown hob whose page has never been its own writes it tonight, from scratch."""
    return pet["stage"] not in LITTLE and pet.get("self_by") != "model"


async def rewrite(eng):
    """SPEC-v4.2.2 §3's migration: every grown hob's page written again under the plain instruction, one model call each
    (a little one's is the engine's; the stub's brain keeps the page). Once a house (house["migrated"]["v422_self"]).
    Returns the report's lines: each page as it now reads."""
    import asyncio
    from .brain4 import PRIORITY, head2
    from .brains.model import parse
    h, cfg = eng.house, eng.cfg
    done = h.setdefault("migrated", {})
    if not on(cfg) or done.get("v422_self"):
        return []
    done["v422_self"] = h["tick"]
    shape = {"type": "object", "additionalProperties": False, "required": ["self"], "properties": {"self": K.reflect_fields()["self"]}}
    out = []
    for pet in sorted((p for p in h["pets"].values() if p["stage"] not in LITTLE + ("egg", "dead")), key=lambda p: p["id"]):
        m = eng.minds.get(pet["id"])
        brain = m.brain if m else None
        if brain is None or getattr(brain, "instant", False) or not hasattr(brain, "chat"):
            continue
        text = "\n".join([x for x in head2(h, cfg, pet) if x] + [
            "Write how you see yourself again, from scratch: the five lines, each in your own words.", PLAIN,
            'Reply with one JSON object and nothing else: {"self": {%s}}' % ", ".join('"%s": "<...>"' % k.replace(" ", "_") for k in K.SELF)])

        async def fn():
            think, most, warm = K.thinking(cfg, "reflect")
            return parse(await asyncio.to_thread(brain.chat, text, shape, think, most, warm, "reflect"))
        try:
            reply = await eng.call(PRIORITY["reflect"], pet["id"], "reflect", "its self-page, in plain words", fn, len(text))
        except Exception:
            reply = None
        s = reply.get("self") if isinstance(reply, dict) else None
        page = K.self_page({k: s.get(k.replace(" ", "_"), s.get(k)) for k in K.SELF}) if isinstance(s, dict) else None
        if page and all(page.values()):
            write(h, cfg, pet, page)
            out.append("%s:\n%s" % (label(pet), "\n".join("    " + x for x in K.self_lines(page))))
        else:
            out.append("%s: no page came back; the old one stands" % label(pet))
    return out


async def plain_beliefs(eng):
    """v4.2.3 (20 October 2026): each living hob's beliefs written again in plain words, one model call a hob,
    under the self-page's rule, so a talk's subject and its wants and won't-say stop drawing on v4.2's voice. Each
    keeps its id, hook and marks; the stub's brain keeps them as they were. Once a house (house["migrated"]["v423_beliefs"]).
    Returns the report's lines: each belief, was and now."""
    import asyncio
    from . import actions, hooks
    from .brain4 import PRIORITY, head2
    from .brains.model import parse
    h, cfg = eng.house, eng.cfg
    done = h.setdefault("migrated", {})
    if not on(cfg) or done.get("v423_beliefs"):
        return []
    done["v423_beliefs"] = h["tick"]
    out = []
    for pet in sorted((p for p in h["pets"].values() if p["stage"] not in ("egg", "dead")), key=lambda p: p["id"]):
        m = eng.minds.get(pet["id"])
        brain = m.brain if m else None
        held = m.mem.active() if m else []
        if not held or brain is None or getattr(brain, "instant", False) or not hasattr(brain, "chat"):
            continue
        ids = [b["id"] for b in held]
        text = "\n".join([x for x in head2(h, cfg, pet) if x] + [
            "Things you believe, as you wrote them before:"] + ["- %s: %s" % (b["id"], b["statement"]) for b in held] + [
            "Write each of them again, keeping what it means: one plain sentence each, " + RULE + " Each under thirty words. "
            "What the visitor told you stays in his words.",
            'Reply with one JSON object and nothing else: {%s}' % ", ".join('"%s": "<...>"' % i for i in ids)])
        shape = {"type": "object", "additionalProperties": False, "required": ids,
                 "properties": {i: {"type": "string", "minLength": 1, "maxLength": 220} for i in ids}}

        async def fn(text=text, shape=shape, brain=brain):
            think, most, warm = K.thinking(cfg, "reflect")
            return parse(await asyncio.to_thread(brain.chat, text, shape, think, most, warm, "reflect"))
        try:
            reply = await eng.call(PRIORITY["reflect"], pet["id"], "reflect", "its beliefs, in plain words", fn, len(text))
        except Exception:
            reply = None
        if not isinstance(reply, dict):
            out.append("%s: no reply; its beliefs stand as they were" % label(pet))
            continue
        lines = []
        for b in held:
            new = actions.belief(reply.get(b["id"]) or "")
            if new and new != b["statement"]:
                lines.append("    %s: %s\n      was: %s" % (b["id"], new, b["statement"]))
                m.mem.revise(b["id"], new, h["tick"])
        hooks.mirror(pet, m.mem)
        out.append("%s, %d of %d beliefs rewritten:\n%s" % (label(pet), len(lines), len(held), "\n".join(lines)))
    return out
