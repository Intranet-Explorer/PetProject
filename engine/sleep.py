"""Sleep (SPEC §9): each world night the pet stops ticking, consolidates its day into beliefs, dreams,
and chooses how its body changes."""
import json
import logging
import random
import re

from . import genome, things

from .actions import clean, filled
from .world import clock


def should_sleep(w, cfg):
    c, s = clock(cfg, w["tick"]), cfg["sleep"]
    tired = w["pet"]["needs"]["energy"] < s["energy_below"]
    return c["phase"] == "night" and (tired or c["hour"] >= s["hour"] or c["hour"] < s["wake_hour"])


def condense(today, limit=40):
    """The day's journal cut to about 40 lines: the ticks where a need moved most (visits always count),
    plus an even sample of the rest. Salience is the size of the change, never the rule tags."""
    ranked = sorted(today, key=lambda e: -e[2])
    top, rest = ranked[:limit - 10], sorted(ranked[limit - 10:])
    spread = rest[::max(1, len(rest) // 10)][:10]
    return "\n".join(e[1] for e in sorted(top + spread))


def apply_changes(mem, changes, tick):
    """Apply up to 3 belief changes from consolidation. Returns what was done, as text."""
    done = []
    for c in changes[:3] if isinstance(changes, list) else []:
        if not isinstance(c, dict) or not filled(c.get("statement")):
            continue
        text = clean(c["statement"], 140)
        if re.search(r"\bt\d+\b", text):   # "a visitor arrived at t137" is a log entry, not a belief (SPEC-v2 §8)
            continue
        if c.get("type") == "revise_belief" and mem.is_active(c.get("id")):
            mem.revise(c["id"], text, tick)
            done.append("%s %s" % (c["id"], "discarded" if text.lower() == "discard" else "revised: " + text))
        elif c.get("type") == "write_belief" and not text.lower().startswith("discard"):
            bid = mem.write(text, tick)
            if bid:
                done.append("%s written: %s" % (bid, text))
    return done


async def night(pet):
    """The night's work, run once per sleep while the pet's ticks are paused."""
    w, lines = pet.world, condense(pet.today)
    changes, dream = [], ""
    try:
        changes = apply_changes(pet.mem, await pet.brain.consolidate(lines, pet.mem.active()), w["tick"])
        dream = clean(await pet.brain.dream(lines), 500)
    except Exception:
        logging.exception("sleep failed for %s", pet.id)
    body, reason = "", ""
    try:   # §9.3: three mutations, described in words; the pet picks one
        me = w["pet"]
        options = genome.mutations(me["genome"], random.Random("%s-%d" % (pet.id, w["sleep"]["day"])), me["stage"])
        described = [genome.describe_change(me["genome"], o) for o in options]
        choice, reason = await pet.brain.choose_body(genome.describe(me["genome"]), described)
        me["genome"], body, reason = options[choice], described[choice], clean(str(reason), 200)
        pet.log_body("sleep: " + body, reason)
    except Exception:
        logging.exception("evolve failed for %s", pet.id)
    if w["pet"]["stage"] == "adult":   # §8: how it sees itself, as a recipe. Nothing about its real body changes.
        try:
            parts = [{"shape": p["shape"], "size": p["size"], "color": p["color"], "at": p.get("at", "center")}
                     for p in (await pet.brain.portrait(genome.describe(w["pet"]["genome"])))[:8]
                     if p.get("shape") in things.SHAPES and p.get("size") in (1, 2, 3) and p.get("color") in things.COLORS
                     and p.get("at", "center") in things.PLACES]
            if parts:
                w["portraits"] = (w["portraits"] + [{"day": w["sleep"]["day"], "parts": parts, "stage": "adult",
                                                    "genome": dict(w["pet"]["genome"])}])[-60:]
                pet.mem.update_self(portrait=parts)
        except Exception:
            logging.exception("portrait failed for %s", pet.id)
    w["last_night"] = {"day": w["sleep"]["day"], "dream": dream, "changes": changes, "body": body, "reason": reason}
    w["diary"] = (w["diary"] + [w["last_night"]])[-60:]
    pet.mem.journal({"pet": pet.id, "tick": w["tick"], "type": "sleep", **w["last_night"]})
    if pet.db:
        pet.db.execute("INSERT INTO sleeps VALUES (?,?,?,?,?)",
                       (pet.id, w["tick"], w["sleep"]["day"], dream, json.dumps(changes)))
        pet.db.commit()
    w["sleep"]["done"] = True
