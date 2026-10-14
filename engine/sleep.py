"""Sleep (SPEC §9, SPEC-v3 §3.3, §5.2, §8.2): each night a pet stops, and thinks the day over once, with
thinking on. It may change up to three beliefs, looks again at one old belief beside its own memories of it,
decides about its project, may rewrite the message for its children, and dreams. Its body no longer changes in
the night (SPEC-v3.5 §2.1: a body is settled at birth); once grown, it still draws itself."""
import logging

from . import genome, life, story, things
from .actions import belief, clean, filled
from .feel import ago
from .log import put
from .world import label, moment


def should_sleep(house, cfg, pet):
    c, s = house["clock"], cfg["sleep"]
    tired = pet["needs"]["energy"] < s["energy_below"]
    return c["phase"] == "night" and (tired or c["hour"] >= s["hour"] or c["hour"] < s["wake_hour"])


def condense(today, limit=40):
    """The day's journal cut to about 40 lines: the moments a need moved most (anything said to it always
    counts), plus an even sample of the rest."""
    ranked = sorted(today, key=lambda e: -e[2])
    top, rest = ranked[:limit - 10], sorted(ranked[limit - 10:])
    spread = rest[::max(1, len(rest) // 10)][:10]
    return "\n".join(e[1] for e in sorted(top + spread))


def bearing(belief, mind, n=6):
    """Its own memories that bear on a belief (§3.3): today's lines and past dreams sharing its words."""
    words = story.content(belief["statement"])
    lines = [e[1] for e in mind.today] + ["(%s) %s" % (ago(mind.eng.house, mind.cfg, d["tick"]), d["dream"]) for d in mind.pet["diary"] if d.get("dream")]
    scored = sorted(((len(words & story.content(l)), i, l) for i, l in enumerate(lines)), reverse=True)
    return [l for hit, i, l in sorted(scored[:n], key=lambda x: x[1]) if hit >= 2]


def apply_changes(mind, changes):
    """Apply up to 3 belief changes. Returns what was done, as text."""
    mem, tick, done = mind.mem, mind.eng.house["tick"], []
    for c in changes[:3] if isinstance(changes, list) else []:
        if not isinstance(c, dict) or not filled(c.get("statement")):
            continue
        text = belief(c["statement"])
        if c.get("type") == "revise_belief" and mem.is_active(c.get("id")):
            mem.revise(c["id"], text, tick)
            done.append("%s %s" % (c["id"], "discarded" if text.lower() == "discard" else "revised: " + text))
            if text.lower() != "discard":
                story.claims(mind.eng, mind.pet, "belief", text)
        elif c.get("type") == "write_belief" and not text.lower().startswith("discard"):
            bid = mem.write(text, tick, c.get("source") if filled(c.get("source")) else "lived")
            if bid:
                done.append("%s written: %s" % (bid, text))
                story.claims(mind.eng, mind.pet, "belief", text)
    return done


async def night(mind):
    """The night's work, run once per sleep while the pet's ticks are paused."""
    eng, pet, mem, cfg = mind.eng, mind.pet, mind.mem, mind.cfg
    house = eng.house
    day, lines = pet["sleep"]["day"], condense(mind.today)
    out = {"day": day, "tick": house["tick"], "dream": "", "changes": [], "review": None, "project": None, "body": "", "reason": ""}
    try:
        review = mem.to_review() if len(mem.active()) >= 2 else None
        last_day = life.span(cfg, pet) - life.days(house, cfg, pet) <= 1.2
        asks = ["dream", "changes"] + ["review"] * bool(review) + ["project", "people"] + ["message"] * bool(pet["message"]) + \
            ["my_life"] * bool(last_day and not pet.get("my_life"))
        held = "".join("\n  %s (%s): %s" % (b["id"], b.get("source", "lived"), b["statement"]) for b in mem.active()) or " none yet"
        text = "This is your journal for today:\n%s\n\nyour beliefs:%s\n" % (lines or "(a quiet day)", held)
        if review:
            mine = bearing(review, mind)
            text += '\none of your beliefs, to look at again: %s: "%s"\nwhat your own days say that bears on it:%s\n' % (
                review["id"], review["statement"], "".join("\n  " + l for l in mine) or " nothing you remember bears on it")
        proj = pet["project"]
        text += "\nyour project: %s\n" % ("%s (started %s)" % (proj["text"], ago(house, cfg, proj["since"])) if proj else "none yet")
        for m in [m for m in pet["told"] if m["kind"] in ("message", "last words")][:1]:
            text += 'what your %s told you: "%s"\n' % (m["who"], m["text"])
        if pet["message"]:   # SPEC-v3.5.4 §4: its own old message is not shown: it writes the next one fresh
            text += "you have children: tonight you write your message for them again, fresh, from your own life\n"
        if proj and life.not_doing(proj["text"]):   # §4: a living pet whose project is a way to be gets a new one
            text += "your project is not something you can do and finish: tonight you set a new one\n"
        if last_day:
            text += "you feel very old and tired.\n"
        tellers = sorted({m["who"] for m in pet["told"]})
        reply = await eng.call(2, pet["id"], "night", "sleep", lambda: mind.brain.night(text, asks, [b["id"] for b in mem.active()], tellers), len(text))
        p = reply.get("project")
        wrong = isinstance(p, dict) and (life.not_doing(p.get("text")) if p.get("decision") == "set" else p.get("decision") == "keep" and proj and life.not_doing(proj["text"]))
        if wrong:   # SPEC-v3.5.4 §4: "wait", "do not make", "attend to the hour" are not projects: asked once more
            again = text + '\nyou were going to take as your project: "%s". That is a way to be, or something not to do. A project is something you will do or find out over the coming days, and can finish.\n' % (p.get("text") or proj["text"])
            r2 = await eng.call(2, pet["id"], "night", "project", lambda: mind.brain.night(again, ["project"], [], tellers), len(again))
            if isinstance(r2.get("project"), dict) and not life.not_doing(r2["project"].get("text")):
                reply["project"] = dict(r2["project"], decision="set")
            pet["project_asked"] = pet.get("project_asked", 0) + 1
        out["changes"] = apply_changes(mind, reply.get("changes", []))
        out["dream"] = clean(reply.get("dream", ""), 500)
        r = reply.get("review")
        if review and isinstance(r, dict) and mem.is_active(review["id"]):
            d, new = r.get("decision"), belief(r.get("statement", ""))
            if d == "discard":
                mem.revise(review["id"], "discard", house["tick"], reviewed=True)
                moment(house, "discarded", "%s gave up a belief: %s" % (label(pet), review["statement"]), pet["id"], pet["room"])
            elif d == "revise" and new:
                mem.revise(review["id"], new, house["tick"], reviewed=True)
                story.claims(eng, pet, "belief", new)
            else:
                d = "keep"
                mem.revise(review["id"], None, house["tick"], reviewed=True)
            out["review"] = {"id": review["id"], "was": review["statement"], "decision": d, "now": new if d == "revise" else None}
        p = reply.get("project")
        if isinstance(p, dict):
            d, new = p.get("decision"), life.last_sentence(clean(p.get("text", ""), 200), 140)
            if d in ("finish", "abandon") and proj:
                pet["projects"].append({"text": proj["text"], "since": proj["since"], "ended": house["tick"], "how": "finished" if d == "finish" else "abandoned"})
                pet["project"] = None
                moment(house, "project", "%s %s its project: %s" % (label(pet), "finished" if d == "finish" else "gave up", proj["text"]), pet["id"], pet["room"])
            if new and (d == "set" or (d in ("finish", "abandon") and new != (proj or {}).get("text"))) and new != (proj or {}).get("text"):
                if pet["project"]:
                    pet["projects"].append({"text": proj["text"], "since": proj["since"], "ended": house["tick"], "how": "changed"})
                pet["project"] = {"text": new, "since": house["tick"]}
                moment(house, "project", "%s has a project: %s" % (label(pet), new), pet["id"], pet["room"])
                d = "set"
            out["project"] = {"decision": d, "text": (pet["project"] or {}).get("text")}
        for who in reply.get("people", [])[:3] if isinstance(reply.get("people"), list) else []:
            name = str(who.get("who", "")).strip().lower()
            for other in house["pets"].values():
                names = {(other["name"] or "").lower(), "your " + (eng.relation(pet, other) or "?")}
                if other["id"] != pet["id"] and name and (name in names or name.replace("my ", "your ") in names):
                    pet["known"][other["id"]] = life.last_sentence(clean(who.get("line", ""), 160), 120)
        msg = life.sentences(life.last_sentence(clean(reply.get("message", ""), 640), 600), 4)
        if pet["message"] and msg and msg != pet["message"][-1]["text"]:
            pet["message"].append({"tick": house["tick"], "text": msg})
            for kid in (house["pets"].get(c) for c in pet["children"]):   # an egg not yet hatched gets the words as they now stand
                if kid and kid["stage"] == "egg":
                    kid["told"][0]["text"] = msg
            put(eng.db, "messages", pet=pet["id"], tick=house["tick"], kind="message", to_pet=None, text=msg)
            story.claims(eng, pet, "message", msg)
            moment(house, "message", "%s rewrote the message for its children" % label(pet), pet["id"], pet["room"])
        if "my_life" in asks and filled(reply.get("my_life")):
            pet["my_life"] = life.last_sentence(clean(reply["my_life"], 860), 800)
    except Exception:
        logging.exception("sleep failed for %s", pet["id"])
    try:   # §8: how a grown pet sees itself. (v3 §9.3's nightly change of body is gone, and with it this call for the young.)
        reply = await eng.call(2, pet["id"], "body", "sleep", lambda: mind.brain.body(genome.describe(pet["genome"]), [], True)) if pet["stage"] in ("adult", "elder") else {}
        parts = [{"shape": p["shape"], "size": p["size"], "color": p["color"], "at": p.get("at", "center")}
                 for p in (reply.get("portrait") or [])[:8] if isinstance(p, dict)
                 and p.get("shape") in things.SHAPES and p.get("size") in (1, 2, 3) and p.get("color") in things.COLORS
                 and p.get("at", "center") in things.PLACES]
        if parts:   # §8: how it sees itself. Nothing about its real body changes.
            pet["portraits"] = (pet["portraits"] + [{"day": day, "parts": parts, "stage": pet["stage"], "genome": dict(pet["genome"])}])[-30:]
            mem.update_self(portrait=parts)
    except Exception:
        logging.exception("body choice failed for %s", pet["id"])
    pet["last_night"] = out
    pet["diary"] = (pet["diary"] + [out])[-40:]
    mem.journal({"pet": pet["id"], "type": "sleep", **out})
    put(eng.db, "sleeps", pet=pet["id"], tick=house["tick"], day=day, dream=out["dream"], changes=out["changes"],
        review=out["review"] or {}, project=out["project"] or {})
    if pet["sleep"]:
        pet["sleep"]["done"] = True
