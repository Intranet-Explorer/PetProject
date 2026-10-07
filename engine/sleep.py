"""Sleep (SPEC §9): each world night the pet stops ticking, consolidates its day into beliefs, and dreams.
Evolving the body is added in M4."""
import json
import logging

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
        text = clean(c["statement"], 200)
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
    w["last_night"] = {"day": w["sleep"]["day"], "dream": dream, "changes": changes}
    pet.mem.journal({"pet": pet.id, "tick": w["tick"], "type": "sleep", **w["last_night"]})
    if pet.db:
        pet.db.execute("INSERT INTO sleeps VALUES (?,?,?,?,?)",
                       (pet.id, w["tick"], w["sleep"]["day"], dream, json.dumps(changes)))
        pet.db.commit()
    w["sleep"]["done"] = True
