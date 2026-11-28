"""SPEC-v4.0 §8 the new brain (helper D). Switch: [brain4] on (off: v3.6c's per-action thoughts, exactly).

Four kinds of thought (SPEC-v5.1 §4.5: designing, the fifth, is gone) replace the thought that picked each small action:
  - the morning plan, on waking: two or three aims for the day, each with a reason, and who to seek out or avoid
    (pet["aims"], pet["seek"], pet["avoid"]); the body works on them (planner.py);
  - a reaction, to a notable event (a hurt, an insult, a gift, a death, a find, a first, the visitor, a plan
    failing or done, a need gone critical, a fight nearby, being spoken to): how it feels (its mood) and what it does
    now (an aim, a hob to seek out, a rung on the ladder it means to climb: pet["intent"] for conflict.py, a gift);
  - a conversation (talk.py, helper B's);
  - the evening reflection, at bedtime (`reflect`, called from sleep.night in place of the night's thinking: one
    call): a diary line, what it learned (a belief), the hobs it now feels warmer or cooler toward, its ambition kept
    or taken, a memory to keep (and, as the night did, the message for its children and the story of its life).
"Ready to make" and "something changed" no longer start thoughts: the body makes by itself (planner.make).

Each kind has its own packet (§8.2), carrying only what bears on it, never more than [brain4] packet_chars (v3.6c's
trimmed thought). The reply's shape is a JSON schema per kind (brains/model.py `schema4`); the stub brain answers each
kind (brains/stub.py `think4`). Calls go through Engine.call at PRIORITY (§8.3); while the house is over its budget
of calls, only reactions to a death, a hurt or the visitor are asked, and a reflection is skipped (the diary line is
the engine's). Other parts tell a hob something notable with `notable(...)` (conflict.py: a hurt, a fight; talk.py:
an insult; visitor.py: the visitor).

SPEC-v4.2 (helper B), under [spirit]: every packet reads in one order (§4.5: the self-page, who and where, drive and
flaw, voice, who is here, the strongest feelings, what has just happened, the memories that bear on it, what the house
could use and what it wants, the ask); a need is said when it crosses a band, never after every act (§3.4); the same
line is said once (§3.6); sunrise's plans are asked across the first world hour, eldest first (§3.2); react and reflect
write memories (§4.1), reflect writes the self-page, a belief with its hook, the theory of the visitor (§10.2)."""
import logging
import re

from . import health
from . import actions, body, bonds, character, feel, firsts, life, memories, needs, opinions, planner, things, wants, world
from . import contracts as K
from . import sheet
from . import hooks
from . import self as self_page
from .world import LONG_AGO, here, hours, label, relation, ticks

PRIORITY = {"react death": 0, "react hurt": 0, "react nurse": 0, "visitor": 1, "talk": 2, "react": 2, "plan": 3, "reflect": 4}
MOODS = ("happy", "content", "grumpy", "sad", "afraid", "angry", "proud", "ashamed", "lonely", "excited")
DOES = ("aim", "seek", "rung", "gift", "nothing")
URGENT = ("death", "hurt", "visitor", "nurse")   # a reaction to these waits for nothing (§8.3; nurse: jobs.ask_nurse)
# the steps a plan or a reaction may take now (actions.py, carried out by the Mind's plan machinery, as v3.6c's were)
STEPS = ("lay_egg", "name", "take_name", "give", "accept", "speak", "tell", "nuzzle", "show", "go", "use", "look", "sing", "teach_song",
         "bequeath", "ask_book", "mend")
DAY = {"make": "make things", "tend": "tend what is planted", "learn": "learn something (the book, a machine, a thing with words on it)", "be with": "be with someone", "help": "help someone",
       # SPEC-v4.2 §1.3: what each stage is for
       "ask": "ask someone grown about something you wonder at", "try": "try something nobody showed you", "nurse": "look after one who is sick or hurt",
       "tell": "tell the little ones what you have known", "lay": "lay your egg somewhere safe"}
DAY.update({k: w.format(who="someone", what="something") for k, w in K.AIM_WORDS51.items() if k not in DAY})   # SPEC-v5.1 (learn keeps its words)
FINDS = ("room", "discovery", "invented", "catch")
WITNESSED = ("fight", "harm", "killing", "shove", "theft", "sabotage")
LINES = dict({"talk": 6, "gift": 5, "hurt": 8}, **{k: 7 for k in WITNESSED + ("snub", "insult")})   # moments that are a line of the day of those in them
ROOM51 = 250   # SPEC-v5.1 §4.2: what the reply's words on inventing (model.INVENT4, 420) take of a packet's room beyond the 1,600 kept for the reply's form
# SPEC-v5.1 §4.1: a packet with the grammar, over its room, loses the grammar's examples, then what is to hand, and only
# then the grammar itself (and with it the reply's `invent`), after what it would lose without it; never its ask
GRAMMAR_CUT = ("Things that can be made", "What's to hand", "when you tried to make", "How things are made")
HEARD = re.compile(r"said to you|showed you|took your|told you|taught you")   # what another did to it, never its own "you said to"


def on(cfg):
    return bool(cfg.get("brain4", {}).get("on"))


def priority(kind):
    return PRIORITY.get("react " + kind, PRIORITY["visitor"] if kind == "visitor" else PRIORITY["react"])


def notable(house, cfg, pet, kind, text, about=()):
    """Something has happened to this hob that it will react to (§8.1): kept until a reaction takes it up (the five
    most pressing). Returns the event. Other parts call this: conflict.py ("hurt", "fight", "death"), talk.py
    ("insulted"), visitor.py ("visitor"), the planner ("plan failed", "plan done", "insulted" by a scold or a sneer)."""
    if not pet or pet.get("stage") in (None, "egg", "dead"):
        return None
    q = pet.setdefault("notable", [])
    about = [a for a in about if a]
    if any(e["kind"] == kind and e["about"] == about and house["tick"] - e["tick"] < hours(cfg, 0.5) for e in q):
        return None
    e = {"kind": kind, "text": str(text)[:200], "about": about, "tick": house["tick"]}
    q.append(e)
    q.sort(key=lambda e: (priority(e["kind"]), -e["tick"]))
    del q[5:]
    return e


def jot(mind, text, weight):
    """A line of the day for the evening's reflection: at most 40, the heaviest kept, in order (19 October 2026: it saw
    only the steps a thought decided, a few a day; with [brain4] off, as before: the last 800)."""
    t = mind.today
    t.append([mind.eng.house["tick"], "%s %s" % (mind.stamp(), text), weight])
    while len(t) > (40 if on(mind.cfg) else 800):
        t.remove(min(t, key=lambda e: e[2]) if on(mind.cfg) else t[0])


def scan(house, cfg, pet, mind=None):
    """What it has come to know of since it last looked: the house's moments (a death of one it loved or of kin, or in
    its room; a first of its own that matters; a find of its own; a gift to it; a fight in its room), a hurt of its
    own, the visitor, being spoken to, a need gone critical. A talk, a gift, a hurt or a fight it was in is a line of
    its day (`mind`)."""
    seen = pet.get("moment_seen")
    ms = house["moments"]
    if seen is None:
        pet["moment_seen"] = ms[-1]["n"] if ms else 0
        return
    for m in (m for m in ms if m["n"] > seen):
        who = house["pets"].get(m.get("pet") or "")
        if mind and m["kind"] in LINES and (who is pet or pet["id"] in (m.get("pets") or []) or (m["kind"] == "gift" and label(pet) in (m["text"] or ""))):
            jot(mind, m["text"], LINES[m["kind"]])
        if m["kind"] == "death" and who and who is not pet and (planner.loved(house, pet, who["id"]) or m.get("room") == pet["room"]):
            notable(house, cfg, pet, "death", m["text"], [who["id"]])
        elif m["kind"] in ("first", "first design", "first working design") and who is pet and m.get("matters", True):
            notable(house, cfg, pet, "first", m["text"].replace(label(pet), "you", 1))
        elif m["kind"] in FINDS and who is pet:
            notable(house, cfg, pet, "find", m["text"].replace(label(pet), "you", 1))
        elif m["kind"] == "gift" and who is pet:
            notable(house, cfg, pet, "gifted", m["text"].replace(label(pet), "you"))
        elif m["kind"] in WITNESSED and m.get("room") == pet["room"] and who is not pet:
            notable(house, cfg, pet, "fight", m["text"], [who["id"]] if who else [])
    pet["moment_seen"] = ms[-1]["n"] if ms else seen
    hurt = pet.get("hurt")
    if hurt and hurt.get("since", LONG_AGO) > pet.get("hurt_seen", LONG_AGO):
        pet["hurt_seen"] = hurt["since"]
        notable(house, cfg, pet, "hurt", "you are %s" % hurt.get("level", "hurt"))
    news = set(pet["news"])
    if "visitor" in news:
        notable(house, cfg, pet, "visitor", next((e for t, e in reversed(pet["events"]) if "visitor" in e), "the visitor did something"))
    if "spoken" in news:   # (19 October 2026: what was said to it, from its inbox (think clears it) or its events; " said" read it its own "you said to")
        notable(house, cfg, pet, "spoken", next((e for e in list(reversed(pet["inbox"])) + [e for t, e in reversed(pet["events"])] if HEARD.search(e)), "someone spoke to you"))
    if "low" in news:
        worst = max(pet["needs"], key=lambda n: feel.level(pet, n) if n in feel.WORDS else 0)
        if worst in feel.WORDS and feel.level(pet, worst) >= 4:
            notable(house, cfg, pet, "need", "you feel " + feel.WORDS[worst][4])
    pet["news"] = []   # (the body has turned to it already, this tick; what matters is now a notable event)


def vigil(pet):
    """At night the day's aims, seeking and avoiding end, but for a vigil not yet kept (conflict.py's)."""
    pet["aims"] = [a for a in pet.get("aims") or [] if a["kind"] == "vigil" and not a.get("done") and not a.get("failed")]
    pet["seek"], pet["avoid"] = [], []
    pet["notable"] = [e for e in pet.get("notable") or [] if e["kind"] == "nurse"]   # (19 October 2026: what it did not get to react to is let go; being asked to nurse waits for its answer)


def reacts_today(house, pet):
    t = pet.get("reacts") or [None, 0]
    return t[1] if t[0] == house["clock"]["day"] else 0


def wants_thought(mind):
    """Why this hob should think now, or None (tick.Mind.wants_thought while on): "plan" or "react". On the
    way, the day's aims are looked over (planner.check) and bits laid out are made (planner.make)."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    B, day = cfg["brain4"], h["clock"]["day"]
    scan(h, cfg, pet, mind)
    if K.on(cfg):
        hooks.due(mind.eng, pet)   # SPEC-v4.2 §5.1: what it was left to believe, and the body's marks on its beliefs
        taught_first(h, cfg, pet)
    planner.check(h, cfg, pet)
    if pet.get("ready") and not world.busy(pet):
        planner.make(mind)
    if body.laid_out(pet) and not pet.get("ready") and not world.busy(pet):
        planner.put_down(h, cfg, pet)   # (19 October 2026: nothing could be made of them, or the making was refused)
    quiet = h["tick"] - pet["last_call"]
    busy = not mind.brain.instant and mind.eng.over_budget()
    q = pet.get("notable") or []
    if q and q[0]["kind"] in URGENT and quiet >= ticks(cfg, B["urgent_seconds"]):
        return "react"
    if busy or h["clock"]["phase"] == "night":
        return None
    tries = pet.get("plan_tries") or [None, 0]
    tries = tries[1] if tries[0] == day else 0
    if pet.get("planned") != day and tries < 3 and (not tries or quiet >= hours(cfg, B["react_gap_hours"])) and turn_to_plan(h, cfg, pet):
        return "plan"   # (19 October 2026: a plan whose reply was lost is asked again after a while, at most three times a day)
    if q and quiet >= hours(cfg, B["react_gap_hours"]) and reacts_today(h, pet) < B["reacts_per_day"]:
        return "react"
    return None


def turn_to_plan(house, cfg, pet):
    """SPEC-v4.2 §3.2: in the first world hour after waking the plans are asked one after another, eldest first, each at
    its share of the hour (v4.0.6 asked them all at once, and they waited 20-65 s in the queue for 11 s of work)."""
    if not K.on(cfg) or not cfg["spirit"].get("stagger"):
        return True
    wake, hr = cfg["sleep"]["wake_hour"], house["clock"]["hour"]
    if not wake <= hr < wake + 1:
        return True
    awake = sorted((p for p in house["pets"].values() if p["stage"] not in ("egg", "dead") and not p["sleep"]), key=lambda p: (p.get("born") or 0, p["id"]))
    rank = next((i for i, p in enumerate(awake) if p is pet), 0)
    return hr >= wake + rank / max(1, len(awake))


def taught_first(house, cfg, pet):
    """SPEC-v4.2 §5.3: the first thing made of a recipe the visitor taught is a first, "taught by the visitor"."""
    t, made = pet.get("taught_recipe"), pet.get("last_made") or {}
    if t and made.get("tick", LONG_AGO) >= t["tick"] and made.get("kind") == t["kind"]:
        pet.pop("taught_recipe")
        world.moment(house, "taught first", "%s made %s %s for the first time, taught by the visitor" % (label(pet), cfg["kinds"].get(t["kind"], {}).get("a", "a"), t["kind"]), pet["id"], pet["room"])
        memories.add(house, cfg, pet, "I made %s %s, as the visitor showed me" % (cfg["kinds"].get(t["kind"], {}).get("a", "a"), t["kind"]), 3, ["visitor"], "visitor")


# ---- the packets (§8.2) ----

def opinion_words(house, pet, other):
    """How it feels about another hob, in words: never a number."""
    o = opinions.of(pet, other["id"])
    l = o.get("liking", 0)
    line = "you are very fond of" if l >= 6 else "you like" if l >= 2 else "you hate" if l <= -6 else "you dislike" if l <= -2 else "you feel nothing much about"
    more = [w for w, ok in (("do not trust", o.get("trust", 5) <= 2), ("are afraid of", o.get("fear", 0) >= 5), ("look up to", o.get("respect", 5) >= 8)) if ok]
    rel = relation(house, pet, other)
    bond = {"close": "; you are close", "friend": "; a friend", "rival": "; a rival", "enemy": "; an enemy"}.get(bonds.kind(house, pet["id"], other["id"]), "")
    return "%s %s%s (%s%s)" % (line, label(other), ", and " + " and ".join(more) if more else "", "your " + rel if rel else "not kin", bond)


def likely(house, pet, n=5):
    """The hobs it is likely to meet: those in its room, those its plan seeks, kin, and those it feels most about."""
    alive = [p for p in house["pets"].values() if p is not pet and p["stage"] not in ("egg", "dead")]
    rank = lambda p: (p["room"] != pet["room"], p["id"] not in (pet.get("seek") or []), relation(house, pet, p) is None, -abs(opinions.of(pet, p["id"]).get("liking", 0)), p["id"])
    return sorted(alive, key=rank)[:n]


def head(house, cfg, pet):
    """The lines every packet starts with: when and where, who it is, how it feels."""
    feels = "; ".join(needs.feel(pet) + health.feel(pet)) or feel.feelings(pet)
    why = (pet.get("mood") or {}).get("why")
    return ["it is %s; you are %s, a hob, in %s" % (feel.when(house), label(pet), house["rooms"][pet["room"]]["name"]),
            character.describe(pet) if character.on(cfg) else "",   # (traits, quirks and values, in words)
            sheet.words(house, cfg, pet) if sheet.on(cfg) else "",   # (24 November 2026: its place, its pursuit, its fear, its food)
            "your mood: %s%s" % (character.mood(pet), " (%s)" % why if why else ""),
            "you feel: " + feels]


def remembered(house, cfg, pet, about=(), n=None):
    ms = memories.relevant(house, cfg, pet, about=about, n=n or cfg["brain4"]["memories"])
    return "you remember: " + "; ".join("%s (%s)" % (m["text"], feel.ago(house, cfg, m["tick"])) for m in ms) if ms else ""


def fit(lines, most, cut_order):
    """The packet's lines joined, the least needed cut first while it is over `most` characters (§8.2: v3.6c's ceiling)."""
    lines = [l for l in lines if l]
    size = lambda: sum(len(l) + 1 for l in lines)
    for key in cut_order:
        if size() <= most:
            break
        if key.endswith("*"):   # (SPEC-v4.2 §4.5: such lines one at a time, from the bottom)
            while size() > most and any(l.startswith(key[:-1]) for l in lines):
                del lines[max(i for i, l in enumerate(lines) if l.startswith(key[:-1]))]
            continue
        lines = [l for l in lines if not l.startswith(key)]
    text = "\n".join(lines) + "\n"
    cut = text.rfind("\n", 0, most)   # (19 October 2026: at a line's end, not in a word)
    return text if len(text) <= most else text[:cut + 1] if cut > 0 else text[:most]


def names_of(house, pet, hobs):
    return {label(p): p["id"] for p in hobs}


def step_ctx(house, cfg, pet, mem):
    """mind.perceive's ctx (what a step can name), its actions cut to those a plan or a reaction may take now."""
    from . import mind as mind_
    _, ctx = mind_.perceive(house, cfg, pet, mem)
    ctx["allowed"] = [a for a in ctx["allowed"] if a in STEPS]
    return ctx


def others_of(house, pet):
    return [p for p in house["pets"].values() if p is not pet and p["stage"] not in ("egg", "dead")]


def plan_packet(house, cfg, pet, mem):
    """The morning plan: traits and values, needs as feelings, ambition and mood, the 5 most relevant memories, its
    feelings about the hobs it is likely to meet, what the house and the visitor have asked of it."""
    if K.on(cfg):
        return plan_packet2(house, cfg, pet, mem)
    meet = likely(house, pet)
    rooms = {house["rooms"][r]["name"]: r for r in pet["rooms"] if house["rooms"][r]["type"]}
    asked, wanted = things.better(house, cfg, pet), wants.lines(pet)[:3]
    board = projects53(house, cfg, pet, jobs5(house, cfg, pet))
    sug = pet.get("suggested")
    woke = (pet.get("last_night") or {}).get("day", -9) >= house["clock"]["day"] - 1   # (19 October 2026: not for one that hatched at noon)
    lines = head(house, cfg, pet) + [
        ("you have just woken. " if woke else "") + "Choose two or three things to do today, each for a reason of your own",
        firsts.lines(house, cfg, pet),
        remembered(house, cfg, pet, about=[p["id"] for p in meet]),
        "who you may meet today: " + "; ".join(opinion_words(house, pet, p) for p in meet) if meet else "",
        "the house could use: " + "; ".join(asked) if asked else "",
        *board["lines"],
        ("\nand you want: " if asked else "you want: ") + "; ".join(wanted) if wanted else "",   # (19 October 2026: its wants were run on after the house's needs)
        "the visitor asked you: %s" % (sug.get("text") if isinstance(sug, dict) else sug) if sug else "",
        "yesterday you wrote in your diary: " + pet["last_night"]["dream"] if (pet.get("last_night") or {}).get("dream") else "",
        "you carry: " + (", ".join(pet["carrying"]) or "nothing"),
        *habits53(house, cfg, pet),
        "rooms you know: " + ", ".join(rooms),
    ]
    kinds = planner.feasible(house, cfg, pet)
    grammar, more = invent51(house, cfg, pet, kinds)
    lines += grammar
    lines.append("what a day can hold: " + ", ".join(DAY.get(k, k) for k in kinds))
    ctx = step_ctx(house, cfg, pet, mem)
    who = names_of(house, pet, others_of(house, pet))
    ctx.update(board["ctx"], **more)
    ctx.update(kind="plan", aim_kinds=kinds, hobs=sorted(who), who=who, rooms=rooms,
               bits=sorted({s["bit"] for r in pet["rooms"] for s in house["rooms"][r].get("spots", []) if s["ready"]} | set(pet["carrying"])))
    ctx["targets"] = sorted(set(ctx["hobs"]) | set(ctx["rooms"]) | set(ctx["bits"]))
    return shown51(fit(lines, cfg["brain4"]["packet_chars"] - 1600 + (cfg["grammar"].get("packet_room", 0) - ROOM51) * bool(more), ["yesterday", "rooms you know", "about the house", "you remember", "the house could use", "who you may meet", *GRAMMAR_CUT]), ctx)


def react_packet(house, cfg, pet, mem, e):
    """A reaction: the event, its mood, the memories and opinions it touches; who is here; the day's aims."""
    if K.on(cfg):
        return react_packet2(house, cfg, pet, mem, e)
    about =[house["pets"][a] for a in e["about"] if a in house["pets"] and house["pets"][a] is not pet]
    others = here(house, pet)
    aims = pet.get("aims") or []
    kinds = planner.feasible(house, cfg, pet)
    grammar, more = invent51(house, cfg, pet, kinds, e)
    lines = head(house, cfg, pet) + [
        "what has just happened: " + e["text"],
        *grammar,
        remembered(house, cfg, pet, about=e["about"], n=3),
        "; ".join(opinion_words(house, pet, p) for p in list({p["id"]: p for p in about + others}.values())[:4]),
        "with you: " + (", ".join(label(p) + (" (asleep)" if p["sleep"] else "") for p in others) or "nobody"),
        "you carry: " + (", ".join(pet["carrying"]) or "nothing"),
        "today you meant to: " + "; ".join("%s (%s)" % (a["text"], "done" if a.get("done") else "it has not come about" if a.get("failed") else "not yet") for a in aims) if aims else "",
        "since you last thought, without thinking about it, you: " + body.since(pet) if cfg["body"]["on"] else "",
    ]
    ctx = step_ctx(house, cfg, pet, mem)
    who = names_of(house, pet, others_of(house, pet))
    ctx.update(kind="react", event=e, aim_kinds=kinds, hobs=sorted(who), who=who, moods=list(MOODS), does=list(DOES),
               rooms={house["rooms"][r]["name"]: r for r in pet["rooms"] if house["rooms"][r]["type"]}, bits=sorted(set(pet["carrying"])), **more)
    ctx["targets"] = sorted(set(ctx["hobs"]) | set(ctx["rooms"]) | set(ctx["bits"]))
    return shown51(fit(lines, cfg["brain4"]["packet_chars"] - 1600 + (cfg["grammar"].get("packet_room", 0) - ROOM51) * bool(more), ["since you last thought", "today you meant to", "you remember", *GRAMMAR_CUT]), ctx)


# ---- SPEC-v4.2 §3.4, §4.5: the packet's shape under [spirit] ----

MEM = "  - "   # a memory's line in a packet (fit cuts them from the bottom first)


def once(xs):
    """§3.6: each line once, in order."""
    return list(dict.fromkeys(x for x in xs if x))


def traits_line(pet):
    """§6.5: the two strongest traits and the weakest, in words."""
    if "temper" not in pet:
        return ""
    ranked = sorted(character.AXES, key=lambda a: -abs(character.trait(pet, a)))
    word = lambda a: character.DATA["axes"][a]["words"][character.trait(pet, a) < 0]
    strong = [(character.degree(character.trait(pet, a)) or "") + word(a) for a in ranked[:2] if character.degree(character.trait(pet, a)) is not None]
    weak = ranked[-1]
    return "you are %s; and neither very %s nor very %s" % (" and ".join(strong), *character.DATA["axes"][weak]["words"]) if strong else ""


def drive_line(cfg, pet):
    """§4.5 drive and flaw in one line (C's drives.line once it is there; read from the records until then)."""
    if not pet.get("drive") and not pet.get("flaw"):
        return ""
    try:
        from . import drives
        return drives.line(pet)
    except (ImportError, AttributeError):
        bits = (["your drive: " + K.drive(pet["drive"])["name"]] if pet.get("drive") else []) + (["your flaw: you are " + K.flaw(pet["flaw"])["name"]] if pet.get("flaw") else [])
        return "; ".join(bits)


def feelings(house, cfg, pet, first=False):
    """§4.5 the two or three strongest feelings in words: its mood, its body, and a need only when it has crossed a band
    since it last thought (§3.4: not after every act); `first`: the worst need too, at the day's first thought."""
    words = needs.WORDS if needs.on(cfg) else feel.WORDS
    bands, was = {n: feel.level(pet, n) for n in pet["needs"] if n in words}, pet.get("bands") or {}
    crossed = sorted((n for n in bands if bands[n] != was.get(n) and (bands[n] >= 2 or was.get(n, 0) >= 2)), key=lambda n: -bands[n])
    if first and not crossed:
        crossed = [n for n in sorted(bands, key=lambda n: -bands[n])[:1] if bands[n] >= 2]
    pet["bands"] = bands
    why = (pet.get("mood") or {}).get("why")
    out = ["your mood: %s%s" % (character.mood(pet), " (%s)" % why if why else "")] + health.feel(pet) + ["you feel %s%s" % (words[n][bands[n]], " now" if n in was else "") for n in crossed]
    return "how you feel: " + "; ".join(out[:3])


def who_here(house, pet):
    from .mind import doing
    others = here(house, pet)
    return "with you: " + (", ".join("%s (%s)" % (label(p), doing(house, p)) for p in others) or "nobody")


def head2(house, cfg, pet):
    """§4.5 the lines every packet starts with: the self-page; who it is, where and when; drive and flaw; voice; traits."""
    return self_page.lines(house, cfg, pet) + [
        "you are %s, %s %s hob, in %s; it is %s" % (label(pet), "an" if pet["stage"][0] in "aeiou" else "a", pet["stage"], house["rooms"][pet["room"]]["name"], feel.when(house)),
        drive_line(cfg, pet),
        "how you talk: " + K.voice_line(pet["voice"]) if pet.get("voice") else "",
        traits_line(pet) if character.on(cfg) else ""]


def memory_lines(house, cfg, pet, n, **about):
    ms = memories.relevant(house, cfg, pet, n=n, **about)
    return ["what you remember that bears on this:"] + once(MEM + "%s (%s)" % (m["text"], feel.ago(house, cfg, m["tick"])) for m in ms) if ms else []


def plain(text):
    """A line of what it did, without the needs said after it (§3.4)."""
    return feel.PLAIN.sub("", text)


def asked_lines(house, cfg, pet, kinds):
    """What the visitor has put into today: the aims it means first, his suggestions and hints, a skill he taught it
    when the day could use it (§5.3-5.6)."""
    from .visitor import SKILL_AIMS
    sug = pet.get("suggested") or []
    sug = [s.get("text") if isinstance(s, dict) else s for s in (sug if isinstance(sug, list) else [sug])]
    first, taught = pet.get("aims_next") or [], [s for s in pet.get("taught") or [] if SKILL_AIMS.get(s) in kinds]
    return ["before anything, today you mean to: " + "; ".join(once(a["text"] for a in first)) if first else "",
            "the visitor would like you to: " + "; ".join(once(sug)) if sug else "",
            "the visitor told you: " + "; ".join(once(pet.get("visitor_hints") or [])) if pet.get("visitor_hints") else "",
            "the visitor taught you %s: you can do it better now" % " and ".join(taught) if taught else ""]


def plan_packet2(house, cfg, pet, mem):
    meet = likely(house, pet)
    rooms = {house["rooms"][r]["name"]: r for r in pet["rooms"] if house["rooms"][r]["type"]}
    asked, wanted = things.better(house, cfg, pet), [w for w in wants.lines(pet)[:3]]
    board = projects53(house, cfg, pet, jobs5(house, cfg, pet))
    woke = (pet.get("last_night") or {}).get("day", -9) >= house["clock"]["day"] - 1
    kinds = planner.feasible(house, cfg, pet)
    grammar, more = invent51(house, cfg, pet, kinds)
    lines = head2(house, cfg, pet) + [
        who_here(house, pet),
        "who you may meet today: " + "; ".join(opinion_words(house, pet, p) for p in meet) if meet else "",
        feelings(house, cfg, pet, first=True),
        ("you have just woken. " if woke else "") + ("yesterday you wrote in your diary: " + pet["last_night"]["dream"] if (pet.get("last_night") or {}).get("dream") else ""),
        *asked_lines(house, cfg, pet, kinds),
        *("lately: " + "; ".join(once(l[8:].split("; "))) if l.startswith("lately: ") else l for l in firsts.lines(house, cfg, pet).split("\n")),   # (§3.6)
        *memory_lines(house, cfg, pet, cfg["brain4"]["memories"], about=[p["id"] for p in meet], where=pet["room"]),
        "the house needs: " + "; ".join(once(asked)) if asked else "",
        *board["lines"],
        "you want: " + "; ".join(w for w in once(wanted) if w not in asked) if [w for w in wanted if w not in asked] else "",
        "you carry: " + (", ".join(pet["carrying"]) or "nothing"),
        *habits53(house, cfg, pet),
        "rooms you know: " + ", ".join(rooms),
        *grammar,
        "what a day can hold: " + ", ".join(DAY.get(k, k) for k in kinds),
        "Choose two or three things to do today, each for a reason of your own",
    ]
    ctx = step_ctx(house, cfg, pet, mem)
    who = names_of(house, pet, others_of(house, pet))
    ctx.update(board["ctx"], **more)
    if K.on51(cfg, "book2") and "learn" in kinds:
        ctx["learn51"] = True   # SPEC-v5.1 §6.3: a learn aim may say its question
    ctx.update(kind="plan", aim_kinds=kinds, hobs=sorted(who), who=who, rooms=rooms, spirit=True,
               bits=sorted({s["bit"] for r in pet["rooms"] for s in house["rooms"][r].get("spots", []) if s["ready"]} | set(pet["carrying"])))
    ctx["targets"] = sorted(set(ctx["hobs"]) | set(ctx["rooms"]) | set(ctx["bits"]))
    return shown51(fit(lines, cfg["brain4"]["packet_chars"] - 1600 + (cfg["grammar"].get("packet_room", 0) - ROOM51) * bool(more), [MEM + "*", "rooms you know", "about the house", "who you may meet", "yesterday", *GRAMMAR_CUT]), ctx)


def react_packet2(house, cfg, pet, mem, e):
    about = [house["pets"][a] for a in e["about"] if a in house["pets"] and house["pets"][a] is not pet]
    others = here(house, pet)
    aims = pet.get("aims") or []
    _, where, what = memories.tag(house, e["text"], cfg)
    if cfg["body"]["on"]:   # (the needs taken out first, so the same deed is counted once: §3.4, §3.6)
        body.state(pet)["since"] = [plain(x) for x in body.state(pet)["since"]]
    since = [body.since(pet)] if cfg["body"]["on"] else []
    grammar, more = invent51(house, cfg, pet, planner.feasible(house, cfg, pet), e)
    lines = head2(house, cfg, pet) + [
        who_here(house, pet),
        feelings(house, cfg, pet),
        "what has just happened: " + e["text"],
        jobs_answer(house, cfg, pet),
        *grammar,
        *memory_lines(house, cfg, pet, 4, about=e["about"] + [p["id"] for p in others], where=where or pet["room"], what=what, kind=e["kind"]),
        "; ".join(opinion_words(house, pet, p) for p in list({p["id"]: p for p in about + others}.values())[:4]),
        "today you meant to: " + "; ".join(once("%s (%s)" % (a["text"], "done" if a.get("done") else "it has not come about" if a.get("failed") else "not yet") for a in aims)) if aims else "",
        "since you last thought, without thinking about it, you: " + since[0] if since and since[0] else "",
        "you carry: " + (", ".join(pet["carrying"]) or "nothing"),
        "How does it strike you, and what will you do? And one line you will keep of it, in your own words",
        "Will you go and nurse %s? (nurse: yes or no)" % label(about[0]) if e["kind"] == "nurse" and about else "",
    ]
    ctx = step_ctx(house, cfg, pet, mem)
    who = names_of(house, pet, others_of(house, pet))
    ctx.update(kind="react", event=e, aim_kinds=planner.feasible(house, cfg, pet), hobs=sorted(who), who=who, moods=list(MOODS), does=list(DOES), spirit=True,
               rooms={house["rooms"][r]["name"]: r for r in pet["rooms"] if house["rooms"][r]["type"]}, bits=sorted(set(pet["carrying"])),
               nurse5=e["kind"] == "nurse" and bool(about), **more)
    ctx["targets"] = sorted(set(ctx["hobs"]) | set(ctx["rooms"]) | set(ctx["bits"]))
    return shown51(fit(lines, cfg["brain4"]["packet_chars"] - 1600 + (cfg["grammar"].get("packet_room", 0) - ROOM51) * bool(more), [MEM + "*", "since you last thought", "today you meant to", *GRAMMAR_CUT]), ctx)


def invent51(house, cfg, pet, kinds, e=None):
    """SPEC-v5.1 §4.1-4.2: (the grammar's lines, what the reply's `invent` may name), when it may make or invent today
    (a plan) or has just been refused (a reaction to it); nothing otherwise, or while [grammar] is off."""
    from . import invention
    if not invention.on(cfg) or "make" not in kinds or (e["kind"] != "refused" if e else not invention.may(house, cfg, pet)):
        return [], {}
    parts, mats = invention.reach_names(house, cfg, pet)
    last = (pet.get("refused51") or [None])[-1] if e else None
    g = invention.text(house, cfg, pet).split("\n")
    tail = [x for x in g if x.startswith(GRAMMAR_CUT[:2])]   # (what's to hand, the examples: lines of their own, so a packet short of room loses them first)
    return ([] if e else invention.refused_lines(house, cfg, pet)) + ["\n".join(x for x in g if x not in tail)] + tail, \
        {"invent51": {"parts": parts, "materials": mats}, **({"refused51": last} if last else {})}


def shown51(packet, ctx):
    """The grammar cut from a packet over its size takes the reply's `invent` with it (it names the parts shown)."""
    if "invent51" in ctx and "How things are made" not in packet:
        ctx.pop("invent51")
        ctx.pop("refused51", None)
    return packet, ctx


def habits53(house, cfg, pet):
    """SPEC-v5.3 §4 (helper B): its habits in a line, and what it has seen standing about the house (nothing while
    [habits] is off). The reply may not return a habit: habits are the body's."""
    from . import habits
    return [habits.line(house, cfg, pet), habits.block(house, cfg, pet)]


def jobs5(house, cfg, pet):
    """SPEC-v5.0 §3.5: the board and its job for the plan packet, and what its reply may name (nothing while [jobs] is off)."""
    if not K.on5(cfg, "jobs"):
        return {"lines": [], "ctx": {}}
    from . import jobs
    return {"lines": jobs.line(house, cfg, pet).split("\n"), "ctx": {"jobs5": jobs.open_words(house, pet), "for5": jobs.for_words(house, pet)}}


def projects53(house, cfg, pet, board):
    """SPEC-v5.3 §4 (helper A): its project and next step (or what its drive could start) after the board, and what
    the plan's `project` may name (nothing while [projects] is off)."""
    from . import projects
    if not projects.on(cfg):
        return board
    return {"lines": board["lines"] + [projects.line(house, cfg, pet)], "ctx": dict(board["ctx"], project53=projects.ctx(house, cfg, pet))}


def jobs_answer(house, cfg, pet):
    """SPEC-v5.0 §3.5: the world's answer to what it last did with a thing, for a reaction."""
    if not K.on5(cfg, "jobs"):
        return ""
    from . import jobs
    return jobs.answer(house, cfg, pet)


def start_plan(mind, thought, intention, steps, why):
    """A decided intention, as tick.Mind.adopt makes one (what its body was at ends; the steps are carried out by
    Mind.advance and finish_step), with no expectation to score."""
    pet, h = mind.pet, mind.eng.house
    if pet["plan"]:
        mind.end_plan("interrupted" if world.busy(pet) else "done")
    now = body.state(pet)["now"]
    if now and steps:
        body.finish(mind, now, cut=not body.begun(pet, now))
    pet["plan"] = {"thought": thought, "intention": actions.clean(intention, 120) or "carry on", "steps": steps[:5], "expect": "", "why": why,
                   "meter": feel.meter_talk(thought), "i": 0, "left": None, "started": h["tick"], "needs0": dict(pet["needs"]), "tags": [],
                   "tag_need": {}, "room": pet["room"], "step_needs0": None, "step_tags": []}
    if not steps:
        pet["plan"]["idle"] = True
    body.state(pet)["last_still"] = True


def think(mind, why):
    """Start a thought of the kind `why` calls for (tick.Mind.think while on)."""
    pet, h, cfg, eng = mind.pet, mind.eng.house, mind.cfg, mind.eng
    if why == "plan":
        packet, ctx = plan_packet(h, cfg, pet, mind.mem)
        pri = PRIORITY["plan"]
    else:
        e = pet["asked"] = pet["notable"].pop(0)   # (kept until the reply has come: a restart asks it again)
        packet, ctx = react_packet(h, cfg, pet, mind.mem, e)
        pri = priority(e["kind"])
        if e["kind"] not in URGENT:
            t = pet.get("reacts") or [None, 0]
            pet["reacts"] = [h["clock"]["day"], (t[1] if t[0] == h["clock"]["day"] else 0) + 1]
    for said in pet["inbox"]:
        jot(mind, said, 99)   # (as the old thought did: anything said to it always counts)
    pet["thinking"], pet["last_call"], pet["seen"], pet["inbox"] = why, h["tick"], h["tick"], []
    mind.b4, mind.last_packet = ctx, packet
    mind.thought = eng.call(pri, pet["id"], why, (ctx.get("event") or {}).get("kind") or why, lambda: mind.brain.think4(why, packet, ctx), len(packet))


def again(pet, e):
    """A reaction whose reply was lost (a bad reply, a restart: tick.Mind) is asked again, twice at most."""
    if e.get("again", 0) < 2:
        pet.setdefault("notable", []).insert(0, dict(e, again=e.get("again", 0) + 1))


def pick(ctx, name):
    """A name the reply gave, back to what it names: a hob's id, a room's id, a bit, or None."""
    for k in ("who", "rooms"):
        if name in ctx.get(k, {}):
            return ctx[k][name]
    return name if name in ctx.get("bits", []) else None


def aim_of(house, ctx, a):
    if not isinstance(a, dict) or a.get("kind") not in planner.KINDS + K.AIMS_NEW or not actions.filled(a.get("text")):
        return None
    return {"text": actions.clean(a["text"], 100), "why": actions.clean(a.get("why") or "", 120), "kind": a["kind"],
            "target": pick(ctx, a.get("target")), "since": None, "done": False, "made0": house["pets"].get(ctx.get("pet"), {}).get("made", 0),
            **({"for": actions.clean(a["for"], 120)} if isinstance(a.get("for"), str) and a["for"] else {}),   # (SPEC-v5.0 §3.3: what a make is for)
            **({"question": actions.clean(a["question"], 120)} if a["kind"] == "learn" and actions.filled(a.get("question")) else {})}   # (SPEC-v5.1 §6.3: a learn aim's own question, B's book reads it)


def propose51(house, cfg, pet, inv):
    from . import invention
    words, ok = invention.propose(house, cfg, pet, inv)
    return {"name": (K.invent(inv) or {}).get("name"), "ok": ok, "words": words}


def missed(house, pet, kind, fields):
    """§0.1 item 5: a reply lacked a new field; it was defaulted and the thought went on; the Lab counts it."""
    if fields:
        K.note(house, "missed", pet=pet["id"], kind=kind, fields=fields)


def visitor_aims(house, cfg, pet):
    """The morning's first aims (SPEC-v4.2): what the visitor taught it to make, what his answers and notes said to do
    (hooks.aim_from: pet["aims_next"]), and his suggestion, taken if it trusts him (§5.5: `from: visitor`)."""
    out = pet.pop("aims_next", None) or []
    sug = pet.get("suggested") or []
    for s in (sug if isinstance(sug, list) else [sug])[-1:]:
        s = s if isinstance(s, dict) else {"text": str(s), "trust": 5}
        if s.get("trust", 5) >= 5:
            a = hooks.aim_from(house, cfg, pet, s["text"], "the visitor asked me", "visitor") or aim_of(house, {"pet": pet["id"]}, {"text": s["text"], "why": "the visitor asked me", "kind": "help"})
            pet.pop("aims_next", None)
            if a:
                a["from"] = "visitor"
                out.append(a)
    pet.pop("visitor_hints", None)   # (the visitor's words have been weighed; "hints" are the craft hints of wants.py)
    return out[-3:]


def adopt(mind):
    """The reply has come: the aims, the feeling, the intent, taken up (tick.Mind.adopt while on)."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    ctx, kind = getattr(mind, "b4", None) or {}, pet["thinking"]
    try:
        turn = mind.thought.result()
    except Exception:
        logging.exception("thought failed for %s", pet["id"])
        turn = "model unreachable"
    pet["thinking"], mind.thought = None, None
    pet["calls"] = [t for t in pet["calls"] if t > h["tick"] - ticks(cfg, 3600)] + [h["tick"]]
    asked = pet.pop("asked", None)
    if not isinstance(turn, dict):
        # (19 October 2026: a lost reply is not a thought had: the plan or the event is asked about again
        # after the gap between thoughts (pet["last_call"] is now), the plan at most three times a day)
        if kind == "plan":
            t = pet.get("plan_tries") or [None, 0]
            pet["plan_tries"] = [h["clock"]["day"], (t[1] if t[0] == h["clock"]["day"] else 0) + 1]
        elif kind == "react" and asked:
            again(pet, asked)
        mind.note({"pet": pet["id"], "tick": h["tick"], "type": "no_intention", "reason": str(turn), "why": kind})
        return
    if kind == "plan":
        pet["planned"] = h["clock"]["day"]
    thought = life.last_sentence(actions.clean(str(turn.get("thought", "")), 260), 220)
    steps = [s for s in turn.get("steps") or [] if isinstance(s, dict) and s.get("type") in ctx.get("allowed", ())][:2]
    rec = {"pet": pet["id"], "tick": h["tick"], "type": "thought4", "kind": kind, "thought": thought}
    keep = lambda: [x for x in pet.get("aims") or [] if not x.get("done") and not x.get("failed")][:2]
    same = lambda a: any(x["kind"] == a["kind"] and x["text"].lower()[:30] == a["text"].lower()[:30] for x in keep())   # (19 October 2026: one hob held "attempt to make a small vessel" three times over)
    if kind == "plan":
        aims = [x for x in (aim_of(h, ctx, a) for a in (turn.get("aims") or [])[:3]) if x]
        if K.on(cfg):   # SPEC-v4.2 §5.3-5.6: what the visitor taught, answered or suggested comes first
            aims = (visitor_aims(h, cfg, pet) + aims)[:4]
        aims = [a for i, a in enumerate(aims) if not any(b["kind"] == a["kind"] and b["text"].lower()[:30] == a["text"].lower()[:30] for b in aims[:i])]   # (no aim twice)
        pet["aims"] = [a for a in pet.get("aims") or [] if a["kind"] == "vigil" and not a.get("done") and not a.get("failed")] + aims   # (a vigil, conflict.py's, stays)
        pet["seek"] = [x for x in (pick(ctx, n) for n in turn.get("seek") or []) if x in h["pets"]][:2]
        pet["avoid"] = [x for x in (pick(ctx, n) for n in turn.get("avoid") or []) if x in h["pets"]][:2]
        pet.pop("suggested", None)   # (the visitor's suggestion has been weighed: helper B's)
        rec.update(aims=[a["text"] for a in aims], seek=pet["seek"], avoid=pet["avoid"])
        if ctx.get("jobs5") is not None:   # SPEC-v5.0 §3.5: a job to take, one to refuse (defaulted: never a failed thought)
            from . import jobs
            j = turn.get("job") if isinstance(turn.get("job"), dict) else {}
            missed(h, pet, "plan", [k for k in ("job",) if not isinstance(turn.get("job"), dict)] + ["for"] * any(isinstance(a, dict) and "for" not in a for a in turn.get("aims") or []))
            jobs.ask(h, cfg, pet, j.get("take") if isinstance(j.get("take"), str) else "", j.get("refuse") if isinstance(j.get("refuse"), str) else "")
            rec["job"] = j
        if ctx.get("project53") is not None:   # SPEC-v5.3 §2.6, §4: a project named, begun or taken up (optional: "none")
            from . import projects
            rec["project"] = projects.propose(h, cfg, pet, turn.get("project"))[0]
        a = next((a for a in turn.get("aims") or [] if isinstance(a, dict) and a.get("kind") == "make" and K.invent(a.get("invent"))), None) if ctx.get("invent51") else None
        if a:   # SPEC-v5.1 §4.2: one invention a plan, for what its make aim is for if it says nothing itself
            rec["invent"] = propose51(h, cfg, pet, dict(a["invent"], **({"for": a["for"]} if not a["invent"].get("for") and isinstance(a.get("for"), str) else {})))
        intention = "today: " + "; ".join(a["text"] for a in aims) if aims else "the day as it comes"
    elif kind == "react":
        e = ctx.get("event") or {}
        mood = turn.get("feel")
        if mood in MOODS:
            character.set_mood(h, cfg, pet, mood, e.get("text", ""))
        do = turn.get("do") if isinstance(turn.get("do"), dict) else {}
        who = pick(ctx, do.get("who"))
        intention = actions.clean(do.get("text") or "", 120) or "take it as it comes"
        if do.get("kind") == "aim":
            a = aim_of(h, ctx, {"text": do.get("text"), "why": e.get("text"), "kind": do.get("aim") or "be with", "target": do.get("who")})
            if a and not same(a):
                pet["aims"] = keep() + [a]
        elif do.get("kind") == "seek" and who in h["pets"]:
            pet["seek"] = list(dict.fromkeys([who] + (pet.get("seek") or [])))[:3]
        elif do.get("kind") == "rung" and who in h["pets"]:   # conflict.py decides what comes of it (§8.4)
            pet["intent"] = {"against": who, "how": intention, "why": e.get("text", ""), "tick": h["tick"]}
        elif do.get("kind") == "gift" and who in h["pets"] and not steps:
            other, what = h["pets"][who], next(iter(pet["carrying"]), None)
            if other["room"] == pet["room"] and what and "give" in ctx.get("allowed", ()):
                steps = [{"type": "give", "what": what, "to": label(other)}]
            else:
                pet["aims"] = keep() + [aim_of(h, ctx, {"text": "bring %s something" % label(other), "why": e.get("text"), "kind": "help", "target": do.get("who")})]
        rec.update(event=e, feel=mood, do=do)
        if ctx.get("invent51") and K.invent(do.get("invent")):   # SPEC-v5.1 §4.2: a reaction's invention
            rec["invent"] = propose51(h, cfg, pet, do["invent"])
        if K.on(cfg):   # SPEC-v4.2 §4.1: what it keeps of it, in its own words
            missed(h, pet, "react", K.defaults("react", turn)[1])
            if memories.on2(cfg) and actions.filled(turn["remember"]):
                _, where, what = memories.tag(h, e.get("text", ""), cfg)
                memories.remember(h, cfg, pet, actions.clean(turn["remember"], 200), 3, "react", e.get("about") or [], where, what, by="model")
                rec["remember"] = turn["remember"]
        if ctx.get("nurse5"):   # (jobs.ask_nurse: its answer, or asked again)
            from . import jobs
            if turn.get("nurse") in ("yes", "no"):
                jobs.nurse_answer(h, cfg, pet, e, turn["nurse"] == "yes")
                rec["nurse"] = turn["nurse"]
            else:
                missed(h, pet, "react", ["nurse"])
                again(pet, e)
    else:   # (a thought of a kind since gone: SPEC-v5.1 §4.5's design, asked before the deploy)
        steps, intention = [], "take it as it comes"
    planner.focus(h, cfg, pet)
    rec["steps"] = steps
    mind.note(rec)
    start_plan(mind, thought, intention, steps, kind)


# ---- the evening reflection (§8.1), in place of the night's thinking (sleep.night) ----

def reflect_packet(mind):
    """The day's events for this hob, and its ambition (§8.2); its aims, how it came to feel about others today."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    if K.on(cfg):
        return reflect_packet2(mind)
    from .sleep import condense
    start = h["tick"] - cfg["ticks_per_day"]
    aims = pet.get("aims") or []
    changed = [(pid, o) for pid, o in (pet.get("opinions") or {}).items() if pid in h["pets"] and any(c.get("tick", 0) >= start for c in o.get("causes", []))]
    beliefs = sorted(mind.mem.active(), key=lambda b: -b["revised"])[:3]
    offer = firsts.offer(h, cfg, pet)
    last = life.span(cfg, pet) - life.days(h, cfg, pet) <= 1.2
    today = [m["text"] for m in pet.get("memories") or [] if m["tick"] >= start]
    lines = head(h, cfg, pet)[:4] + [
        "the day is over and you are going to sleep. You write a line in your diary, and think over what the day taught you",
        "today you meant to: " + "; ".join("%s (%s)" % (a["text"], "done" if a.get("done") else "not done") for a in aims) if aims else "",
        "what happened to you today:\n" + (condense(mind.today, 24) or "a quiet day"),
        "what stayed with you: " + "; ".join(today)[:600] if today else "",
        "how you came to feel today: " + "; ".join(opinion_words(h, pet, h["pets"][pid]) for pid, o in changed[:4]) if changed else "",
        "your beliefs: " + "; ".join(b["statement"] for b in beliefs) if beliefs else "",
        firsts.lines(h, cfg, pet).split("\n")[0] if not offer else "",
        offer.strip(),
        "you have children: tonight you write your message for them again, fresh, from your own life" if pet["message"] else "",
        "you feel very old and tired" if last else "",
    ]
    hobs = [h["pets"][pid] for pid in (pet.get("opinions") or {}) if pid in h["pets"] and h["pets"][pid]["stage"] not in ("egg", "dead")]
    who = names_of(h, pet, hobs + [p for p in others_of(h, pet) if relation(h, pet, p) or p["room"] == pet["room"]])
    asks = ["diary", "learned", "opinions", "memory"] + ["ambition"] * bool(offer) + ["message"] * bool(pet["message"]) + ["my_life"] * bool(last and not pet.get("my_life"))
    ctx = {"kind": "reflect", "asks": asks, "hobs": sorted(who), "who": who}
    return fit(lines, cfg["brain4"]["packet_chars"], ["your beliefs", "how you came to feel", "what stayed with you"]), ctx


SEEN = ("death", "first", "fight", "harm", "killing", "shove", "hatched", "taught first", "secret found", "belief acted", "tale", "happening")


def old_hob(house, cfg, pet):
    """In its last days (§2.1: [lives] old_days; v4.0.6: the last 1.2)."""
    return life.span(cfg, pet) - life.days(house, cfg, pet) <= (cfg["lives"]["old_days"] if K.on(cfg, "lives") else 1.2)


def tested(cfg, pet, since):
    """§5.2: the beliefs it acted against today, with nothing coming of it, often enough to be told."""
    return [b for b in pet.get("hooked") or [] if b.get("tested", 0) >= cfg["hooks"]["tested"] and (b.get("tested_at") or LONG_AGO) >= since]


FOR53 = "what you're for may hold two things, if two are true of you: say both"


def life53(h, cfg, pet):
    """SPEC-v5.3 §4 (helper C): what the reflection sees of its project (A's projects.line) and its habits (B's), with
    how often it has kept each."""
    out = []
    if K.on53(cfg, "projects"):
        from . import projects
        out.append(projects.line(h, cfg, pet))
    if K.on53(cfg, "habits"):
        from . import habits
        hs = habits.live(pet)
        if hs:
            out.append("your habits: " + "; ".join("%s (%d times so far)" % (habits.says(h, cfg, pet, x), x["count"]) for x in hs))
    return [x for x in out if x]


def reflect_packet2(mind):
    """SPEC-v4.2 §10.1: the day with its content: what happened, what was said in talk and what it now knows of others,
    the house's happening, what it saw of others; then what it is asked to write (§10.2)."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    from .sleep import condense
    start, day = h["tick"] - cfg["ticks_per_day"], h["clock"]["day"]
    aims = pet.get("aims") or []
    changed = [(pid, o) for pid, o in (pet.get("opinions") or {}).items() if pid in h["pets"] and any(c.get("tick", 0) >= start for c in o.get("causes", []))]
    beliefs = sorted(mind.mem.active(), key=lambda b: -b["revised"])[:3]
    offer, last = firsts.offer(h, cfg, pet), old_hob(h, cfg, pet)
    mems = [m for m in pet.get("memories") or [] if m["tick"] >= start]
    knows = once(m["text"] for m in mems if m.get("kind") == "knows")
    stayed = once(m["text"] for m in sorted(mems, key=lambda m: -m["weight"]) if m.get("kind") != "knows")[:6]
    hap = K.happening(h["happening"]) if isinstance(h.get("happening"), dict) else None
    seen = once(m["text"] for m in h["moments"] if m["tick"] >= start and m["kind"] in SEEN and m.get("pet") != pet["id"]
                and (m.get("room") == pet["room"] or (m.get("pet") and planner.loved(h, pet, m["pet"]))))[-4:]
    test = tested(cfg, pet, start)[:1]
    flaw = pet.get("flaw") and K.on(cfg, "drives") and day - K.flaw(pet["flaw"])["asked"] >= cfg["drives"]["flaw_every_days"]
    first = self_page.on(cfg) and self_page.wants_first(pet)
    early = sorted((m for m in pet.get("memories") or []), key=lambda m: -m["weight"])[:4] if first else []
    # SPEC-v4.2 C: a day that could change what it is for (§6.1: a death of one close, a betrayal), once a life
    from . import drives
    shaken = drives.shaken(h, cfg, pet, start) if self_page.on(cfg) and pet["stage"] not in self_page.LITTLE else ""
    # SPEC-v4.2 C: end
    lines = head2(h, cfg, pet) + [
        feelings(h, cfg, pet),
        "the day is over and you are going to sleep. You write in your diary, and think over what the day taught you",
        "today you meant to: " + "; ".join(once("%s (%s)" % (a["text"], "done" if a.get("done") else "not done") for a in aims)) if aims else "",
        "what happened to you today:\n" + ("\n".join(once(plain(l) for l in condense(mind.today, 24).split("\n"))) or "a quiet day"),
        "today in the house: %s" % (hap["why"] or hap["name"].replace("_", " ")) if hap and hap["day"] == day and hap["name"] != "nothing" else "",
        "what you saw and heard of others today: " + "; ".join(seen) if seen else "",
        "what you came to know of others in talk today: " + "; ".join(knows) if knows else "",
        "what stayed with you: " + "; ".join(stayed) if stayed else "",
        *life53(h, cfg, pet),   # SPEC-v5.3 §4: its project's progress, its habits' count
        "how you came to feel today: " + "; ".join(opinion_words(h, pet, h["pets"][pid]) for pid, o in changed[:4]) if changed else "",
        "your beliefs: " + "; ".join(b["statement"] for b in beliefs) if beliefs else "",
        'you believe "%s", and today you went against it and nothing came of it: look at it again' % test[0]["text"] if test else "",
        "what you think the visitor is: " + (pet.get("visitor_theory") or "you have no thought of him yet") if K.on(cfg, "visitor5") else "",
        firsts.lines(h, cfg, pet).split("\n")[0] if not offer else "",
        offer.strip(),
        "you have children: tonight you write your message for them again, fresh, from your own life" if pet["message"] else "",
        "you feel very old and tired; tonight you think what you would leave, and to whom, and what you would say last" if last else "",
        ("you have never written down how you see yourself: tonight you write it, the five lines, from what you are for, your flaw and your first days: " + "; ".join(m["text"] for m in early))
        if first else "write how you see yourself again, from the old lines and the day: change at most two of them" if self_page.on(cfg) and pet["stage"] not in self_page.LITTLE else "",
        self_page.PLAIN if self_page.on(cfg) and pet["stage"] not in self_page.LITTLE else "",   # (SPEC-v4.2.2 §3)
        FOR53 if self_page.on(cfg) and pet["stage"] not in self_page.LITTLE and any(K.on53(cfg, x) for x in K.PARTS53) else "",   # (SPEC-v5.3 §7)
        "and where your %s got in the way today" % K.flaw(pet["flaw"])["name"] if flaw else "",
        # SPEC-v4.2 C: its secret, for what it owes; and on a day that shook it, what it is for may change, once (§6.1, §6.3)
        "you keep something to yourself: %s; it is in what you owe, in your own words" % pet["secret"]["text"]
        if K.on(cfg, "drives") and pet.get("secret") and not pet["secret"].get("found") else "",
        "after today (%s), what you are for may not be what it was: if it has changed, write it so in what you are for" % shaken if shaken else "",
        # SPEC-v4.2 C: end
    ]
    hobs = [h["pets"][pid] for pid in (pet.get("opinions") or {}) if pid in h["pets"] and h["pets"][pid]["stage"] not in ("egg", "dead")]
    who = names_of(h, pet, hobs + [p for p in others_of(h, pet) if relation(h, pet, p) or p["room"] == pet["room"]])
    asks = ["diary", "opinions"] + ["memory"] * (not memories.on2(cfg)) + ["review"] * bool(test) + ["ambition"] * bool(offer) + ["message"] * bool(pet["message"]) + ["my_life"] * bool(last and not pet.get("my_life"))
    ctx = {"kind": "reflect", "asks": asks, "hobs": sorted(who), "who": who, "spirit": True, "flaw": bool(flaw), "old": last, "review": test[0]["id"] if test else None,
           "flaw_name": K.flaw(pet["flaw"])["name"] if flaw else "", "shaken": shaken}   # (SPEC-v4.2 C: shaken)
    return fit(lines, cfg["brain4"]["packet_chars"] - 1400, ["your beliefs", "how you came to feel", "what stayed with you", "what you saw and heard"]), ctx


def night_writes(mind, ctx, reply):
    """SPEC-v4.2 §10.2 what the reflection writes besides the diary and the belief: up to three memories (weight 4), the
    self-page, the theory of the visitor, the flaw's answer, an old hob's bequest and last words; and a tested belief
    looked at again (§5.2). Returns the review, as sleep.night keeps it, or None."""
    pet, h, cfg, eng = mind.pet, mind.eng.house, mind.cfg, mind.eng
    if memories.on2(cfg):
        for line in reply["remember"]:
            memories.remember(h, cfg, pet, line, 4, "reflect", by="model")
    if self_page.on(cfg) and pet["stage"] not in self_page.LITTLE and reply["self"]:
        self_page.write(h, cfg, pet, reply["self"])
        # SPEC-v4.2 C: what it now says it is for, on a day that shook it, may be another drive (§6.1, once a life)
        if ctx.get("shaken"):
            from . import drives
            drives.reconsider(h, cfg, pet, reply["self"].get("what I am for"))
        # SPEC-v4.2 C: end
    if K.on(cfg, "visitor5") and actions.filled(reply["visitor"]):
        pet["visitor_theory"] = actions.clean(reply["visitor"], 200)
    if ctx.get("flaw") and actions.filled(reply.get("flaw")):
        pet["flaw"] = dict(K.flaw(pet["flaw"]), asked=h["clock"]["day"])
        line = "where my %s got in the way: %s" % (pet["flaw"]["name"], actions.clean(reply["flaw"], 200))
        if memories.on2(cfg):
            memories.remember(h, cfg, pet, line, 3, "flaw", by="model")
        else:
            memories.add(h, cfg, pet, line, 3, (), "reflect")
    if ctx.get("old") and isinstance(reply.get("leave"), dict):
        pet["leave"] = {k: actions.clean(str(reply["leave"].get(k) or ""), 300) for k in ("what", "to", "last_words")}
    r, b = reply.get("review"), next((b for b in pet.get("hooked") or [] if b["id"] == ctx.get("review")), None)
    if not b or not isinstance(r, dict) or not mind.mem.is_active(b["id"]):
        return None
    d, new = r.get("decision"), actions.belief(r.get("statement") or "")
    if d == "discard":
        mind.mem.revise(b["id"], "discard", h["tick"], reviewed=True)
    elif d == "revise" and new:
        mind.mem.revise(b["id"], new, h["tick"], reviewed=True)
    else:
        d = "keep"
        mind.mem.revise(b["id"], None, h["tick"], reviewed=True)
    b["tested"] = 0   # (looked at again: it starts over)
    hooks.mirror(pet, mind.mem)
    return {"id": b["id"], "was": b["text"], "decision": d, "now": new if d == "revise" else None}


async def reflect(mind):
    """The evening reflection: one call (or none, while the model is over its budget: §8.3). Returns what sleep.night
    keeps of a night: {"dream", "changes", "review", "project"}."""
    pet, h, cfg, eng = mind.pet, mind.eng.house, mind.cfg, mind.eng
    from . import sleep, story
    out = {"dream": "", "changes": [], "review": None, "project": None}
    if not mind.brain.instant and eng.over_budget():
        out["dream"] = actions.clean("a day: " + "; ".join(a["text"] for a in pet.get("aims") or []), 300)
        vigil(pet)
        return out
    text, ctx = reflect_packet(mind)
    reply = await eng.call(PRIORITY["reflect"], pet["id"], "reflect", "bedtime", lambda: mind.brain.think4("reflect", text, ctx), len(text))
    vigil(pet)   # (tomorrow's are the morning's)
    if not isinstance(reply, dict):
        return out
    learned, hook = reply.get("learned"), None
    if K.on(cfg):   # SPEC-v4.2 §10.2: the new fields, defaulted where the reply lacks them
        reply, miss = K.defaults("reflect", reply, old_self=self_page.page(h, cfg, pet), old_theory=pet.get("visitor_theory", ""))
        missed(h, pet, "reflect", miss)
        learned, hook = reply["learned"]["text"], reply["learned"]["hook"]
        if "self" in miss:   # (the page stays as it was, and is not the model's for being kept)
            reply["self"] = None
    out["dream"] = actions.clean(reply.get("diary", ""), 600 if K.on(cfg) else 300)
    if actions.filled(learned) and hook and hooks.on(cfg):   # §5.1: a belief with the hook the model set (its truth unknown)
        bid = hooks.believe(eng, pet, actions.belief(learned), hook, "lived")
        out["changes"] = ["%s written: %s" % (bid, learned)] if bid else []
    elif actions.filled(learned):
        held = mind.mem.active()
        if len(held) >= mind.mem.max:   # (19 October 2026: a hob full of beliefs dropped what it learned, unsaid, and never changed its mind again: the one longest unused is let go)
            old = min(held, key=lambda b: (max(b["revised"], b.get("reviewed", b["revised"])), b["created"]))
            mind.mem.revise(old["id"], "discard", h["tick"])
            mind.note({"pet": pet["id"], "tick": h["tick"], "type": "belief retired", "belief": old["id"], "statement": old["statement"]})
        out["changes"] = sleep.apply_changes(mind, [{"type": "write_belief", "statement": learned, "source": "lived"}])
    if K.on(cfg):
        out["review"] = night_writes(mind, ctx, reply)
    for o in (reply.get("opinions") or [])[:2] if isinstance(reply.get("opinions"), list) else []:
        who = ctx["who"].get(o.get("who")) if isinstance(o, dict) else None
        if who and o.get("way") in ("warmer", "cooler"):
            planner.move(h, cfg, pet, who, "reflect_" + o["way"], out["dream"] or "thinking it over at night")
    if actions.filled(reply.get("memory")):
        memories.add(h, cfg, pet, actions.clean(reply["memory"], 160), 3, (), "reflection")
    if "ambition" in ctx["asks"]:
        firsts.took(h, cfg, pet, reply.get("ambition"))
    msg = life.sentences(life.last_sentence(actions.clean(reply.get("message", ""), 640), 600), 4)
    if pet["message"] and msg and msg != pet["message"][-1]["text"]:
        from .log import put
        pet["message"].append({"tick": h["tick"], "text": msg})
        for kid in (h["pets"].get(c) for c in pet["children"]):
            for t in kid["told"] if kid and kid["stage"] == "egg" else []:   # (19 October 2026: its own words, if the egg has them: a
                if t["by"] == pet["id"] and t["kind"] == "message":   # founder egg of its family may have none, a two-parent egg the other's)
                    t["text"] = msg
        put(eng.db, "messages", pet=pet["id"], tick=h["tick"], kind="message", to_pet=None, text=msg)
        story.claims(eng, pet, "message", msg)
        world.moment(h, "message", "%s rewrote the message for its children" % label(pet), pet["id"], pet["room"])
    if "my_life" in ctx["asks"] and actions.filled(reply.get("my_life")):
        pet["my_life"] = life.last_sentence(actions.clean(reply["my_life"], 860), 800)
    return out
