"""SPEC-v4.0 §10 the visitor's tools: talk, answer, teach, praise, scold, give, suggest, step in (helper B).
§10.1 belief in the visitor: some hobs doubt you until you speak to them or they see what only you could do; doubt
is seeded by the cautious and the sly and spreads or fades in talk; in hard times a hob may ask you for help.
Switch: [visitor4] on (off: the old toolbar only; nothing here runs).
SPEC-v4.2 §9 (helper D, at the end): their theory of him, his absence, his notes on the walls, tend and remedy;
switch [visitor5] (contracts.on), with [visitor4].
SPEC-v5.3.2 §1: "place" and "remove": he sets a thing down on a tile of the room he is looking at, and takes it
back again. A placed thing is owned by "visitor" and does what its kind does (its verbs are kinds.toml's, read by
items.entry). Both are gated on [visitor4] with every other tool: off, they refuse. No switch of their own.

house["visitor"] = {"inbox": [{"n", "pet", "q", "tick", "kind": "question"|"help", "answer", "answered"}],
                    "protect": {pid: until}, "log": [{"tick", "tool", "pet", "text", "said"}]}"""
import asyncio
import difflib
import logging
import re

from . import actions, character, craft, feel, memories, opinions, things
from . import contracts as K
from . import hooks
from . import items   # SPEC-v5.0
from .world import LONG_AGO, add_event, alive, days as world_days, free_tile, here, hours, label, moment, rnd

TOOLS = ("talk", "answer", "teach", "praise", "scold", "give", "suggest", "stepin", "tend", "remedy", "place", "remove")
TOOLS5 = ("tend", "remedy")   # SPEC-v4.2 §9.4: only with [visitor5] on
# SPEC-v5.3.2 §1: these two work on a room and a tile, not on a hob, so they are answered before any hob is looked up
ROOM_TOOLS = ("place", "remove")
OWNER = "visitor"   # what a placed thing's owner and maker are called; things.whose already has words for it
HOW = ("stop", "protect", "pardon", "shun", "drive out")
# the opinions.toml causes the visitor's tools move a hob's opinion of you by (helper A's data gives the amounts)
CAUSES = ("talked_kindly", "talked_harshly", "told_me", "taught_me", "praised_me", "scolded_me", "gift", "spoke_to", "protected_me", "stepped_in")
KIND_WORDS = ("love", "good", "thank", "well done", "proud", "sweet", "dear", "friend", "clever", "kind", "lovely", "brave", "sorry")
HARSH_WORDS = ("stupid", "bad", "hate", "shut up", "idiot", "ugly", "lazy", "useless", "awful", "go away", "dumb", "pathetic")


def on(cfg):
    return bool(cfg.get("visitor4", {}).get("on"))


def state(house):
    v = house.setdefault("visitor", {})
    for k, d in (("inbox", []), ("protect", {}), ("log", [])):
        v.setdefault(k, d)
    return v


def believe(house, pet, how):
    """It knows now you are real (§10.1)."""
    if pet.get("believes") is False:
        pet["believes"] = True
        add_event(house, pet, "the visitor is real after all: %s" % how)


def remember(house, cfg, pet, text, weight, cause):
    """Every tool: a memory, and the hob's opinion of the visitor moved for a cause (opinions.toml)."""
    memories.add(house, cfg, pet, text, weight, about=("visitor",), kind="visitor")
    if cause:
        opinions.move(house, cfg, pet, "visitor", cause, text, remember=False)


def use(eng, tool, body):
    """A tool, from the page. Returns (ok, what to tell the visitor)."""
    if not on(eng.cfg):
        return False, "the visitor's tools are switched off"
    h, cfg = eng.house, eng.cfg
    if not isinstance(body, dict):
        return False, "nothing asked"
    if tool in ROOM_TOOLS:   # SPEC-v5.3.2 §1: the room on screen and a tile, no hob chosen
        ok, said = globals()["t_" + tool](eng, None, body, None)
        if ok:
            v = state(h)
            v["log"].append({"tick": h["tick"], "tool": tool, "pet": None,
                             "text": actions.clean(str(body.get("kind") or body.get("name") or ""), 200), "said": said})
            del v["log"][:-200]
        return ok, said
    if tool == "answer":
        q = next((q for q in state(h)["inbox"] if q["n"] == body.get("n") and not q.get("answer")), None)
        pet = h["pets"].get(q["pet"]) if q else None
        if not q:
            return False, "no such question waiting"
    else:
        pet = h["pets"].get(str(body.get("pet") or ""))
    if not pet or pet["stage"] in ("egg", "dead"):
        return False, "no such hob"
    ok, said = globals()["t_" + tool](eng, pet, body, q if tool == "answer" else None)
    if ok:
        v = state(h)
        v["log"].append({"tick": h["tick"], "tool": tool, "pet": pet["id"], "text": actions.clean(str(body.get("text") or body.get("what") or body.get("how") or body.get("about") or ""), 200),
                         "said": q.get("ack") if tool == "answer" and cfg["visitor4"].get("plain_help") else None})   # (24 November 2026: an answer showed "..." for ever, as if it had not been heard)
        del v["log"][:-200]
        if tool not in ("suggest", "stepin"):   # (spoken to, given to, taught: it knows you are real)
            believe(h, pet, "you spoke to it")
        if on5(cfg) and tool in MOVES:   # SPEC-v4.2 §9.1: what he does moves its theory of him
            move(h, cfg, pet, MOVES[tool])
    return ok, said


def text_of(body, most=200):
    return actions.clean(str(body.get("text") or ""), most).strip()


# ---- talk: one model call, kind "visitor" ----

def t_talk(eng, pet, body, _):
    h, cfg = eng.house, eng.cfg
    said = text_of(body)
    if not said:
        return False, "nothing to say"
    if pet["sleep"]:
        return False, "%s is asleep" % label(pet)
    if not eng.minds.get(pet["id"]):
        return False, "no such hob"
    hear(eng, pet, said, h["tick"])
    add_event(h, pet, 'the visitor said to you: "%s"' % said)
    asked_after(h, cfg, pet, said)
    return True, "%s is listening" % label(pet)


def asked_after(h, cfg, pet, said):
    """SPEC-v4.2 §6.3: a secret is found out by the visitor's question when the question touches it (the one it is
    about, or a word of it); a dishonest hob lies to keep it the first time it is asked in a day."""
    from . import drives
    s = pet.get("secret")
    if not K.on(cfg, "drives") or not s or s.get("found") or "?" not in said:
        return False
    low, about = said.lower(), h["pets"].get(s.get("about") or "")
    from .story import content
    words = {w for w in re.findall(r"[a-z]+", s["text"].lower()) if len(w) >= 4 and content(w)}
    if not ((about and label(about).lower() in low) or any(re.search(r"\b%s\b" % w, low) for w in words)):
        return False
    if (pet.get("flaw") or {}).get("name") == "dishonest" and pet.get("lied_day") != h["clock"]["day"]:
        pet["lied_day"] = h["clock"]["day"]
        add_event(h, pet, "the visitor asked about what you keep to yourself, and you said it was nothing")
        return False
    return drives.found(h, cfg, pet, "visitor", "the visitor asked")


def hear(eng, pet, said, tick):
    """Ask the hob's answer of the model (one call, kind "visitor"); `tick`: when the visitor spoke, which the answer is
    filed under in the log."""
    h, cfg, m = eng.house, eng.cfg, eng.minds[pet["id"]]
    packet, shape = packet_of(h, cfg, pet, said), reply_schema()
    if getattr(m.brain, "instant", False):
        async def fn():
            return stub_answer(pet, said)
    else:
        from .brains.model import parse

        async def fn():
            return parse(await asyncio.to_thread(m.brain.chat, packet, shape, False, cfg["visitor4"]["max_tokens"], 0.8, "visitor"))
    from . import brain4
    fut = eng.call(brain4.PRIORITY["visitor"], pet["id"], "visitor", "the visitor spoke", fn, len(packet))
    eng.__dict__.setdefault("visitor_calls", []).append({"fut": fut, "pet": pet["id"], "text": said, "tick": tick, "log": len(state(h)["log"])})


def packet_of(h, cfg, pet, said):
    from . import needs, talk
    from .mind import doing
    op = opinions.of(pet, "visitor")
    mem = [x["text"] for x in memories.relevant(h, cfg, pet, about=("visitor",), n=5)]
    lines = ["You are %s, a hob, %s, in %s, %s." % (label(pet), pet["stage"], h["rooms"][pet["room"]]["name"], doing(h, pet))]
    if character.words(pet):
        lines.append("Your character: %s." % character.words(pet))
    lines += ["Your mood: %s. You feel: %s." % (character.mood(pet), "; ".join(needs.feel(pet) or [feel.feelings(pet)])),
              "The visitor is %s, who owns your world and watches the house; you can't see him. You %s." % (cfg["visitor"]["name"], talk.regard(op, "him").replace("them", "him"))]
    if pet.get("believes") is False:
        lines.append("Until now you did not believe he was real.")
    if on5(cfg):   # SPEC-v4.2 §9.1, §9.5: what it asks him comes from what it thinks he is, and from its drive
        lines.append("What you think the visitor is: %s." % theory(h, pet) + (" You want to find out what he is." if wants_to_know(pet) else ""))
    if mem:
        lines.append("You remember: " + " | ".join(talk.short(x, 30, 200) for x in mem))
    lines.append("How you talk: %s." % (K.voice_line(pet["voice"]) if pet.get("voice") else talk.voice(pet)))   # (v4.2.2 §2: the card, where it has one)
    lines.append('The visitor says to you: "%s"' % said)
    lines.append('Answer him in your own voice, in at most thirty words (a little one babbles). Then say how what he said made you feel '
                 '(warmed, nothing, or hurt), your mood now, and a question you want to ask him, if any.\n'
                 'Reply with one JSON object and nothing else: {"says": "...", "felt": "warmed|nothing|hurt", "mood": "...", "ask": "... or empty"}')
    return "\n".join(lines)


def reply_schema():
    from .talk import MOODS, obj, text
    return obj(says=text(200), felt={"enum": ["warmed", "nothing", "hurt"]}, mood={"enum": list(MOODS)}, ask=text(100, 0))


def stub_answer(pet, said):
    low = said.lower()
    felt = "hurt" if any(w in low for w in HARSH_WORDS) else "warmed" if any(w in low for w in KIND_WORDS) else "nothing"
    says = {"hurt": "That was unkind.", "warmed": "Oh! Thank you.", "nothing": "Hm. I hear you."}[felt]
    if character.trait(pet, "kind") < -0.3:
        says = says.rstrip(".!") + ". What do you want?"
    return {"says": says, "felt": felt, "mood": {"hurt": "sad", "warmed": "happy", "nothing": "content"}[felt], "ask": ""}


def answered(eng, call, reply):
    """The hob's answer has come back: it is said aloud, remembered, and how you spoke moves its opinion of you."""
    from .talk import babble, short, valid
    h, cfg = eng.house, eng.cfg
    pet = h["pets"].get(call["pet"])
    if not pet or pet["stage"] == "dead":
        return
    if not isinstance(reply, dict) or not valid(reply, reply_schema()):
        logging.warning("the visitor's talk with %s came back out of shape", call["pet"])
        return
    says = babble(reply["says"], pet["stage"], rnd(h, "visitor babble", h["tick"])) if pet["stage"] in ("hatchling", "child") else short(reply["says"], 30, 200)
    pet["said"] = {"text": says, "tick": h["tick"], "to": "visitor"}   # (the card and the bubble show it, as speaking always did)
    for x in reversed(state(h)["log"]):
        if x["tool"] == "talk" and x["pet"] == pet["id"] and x["tick"] == call["tick"] and x["said"] is None:
            x["said"] = says
            break
    remember(h, cfg, pet, 'the visitor said to me "%s", and I said "%s"' % (short(call["text"], 25, 140), says), 3,
             {"warmed": "talked_kindly", "hurt": "talked_harshly"}.get(reply["felt"]))
    if reply["mood"] != character.mood(pet):
        character.set_mood(h, cfg, pet, reply["mood"], "the visitor spoke to me")
    if reply["ask"].strip():
        ask(h, cfg, pet, short(reply["ask"], 20, 100), "question")
    moment(h, "visitor", 'the visitor spoke to %s: "%s" - "%s"' % (label(pet), short(call["text"], 25, 140), says), pet["id"], pet["room"])


# ---- answer, teach, praise, scold, give, suggest ----

def t_answer(eng, pet, body, q):
    h, cfg = eng.house, eng.cfg
    said = text_of(body)
    if not said:
        return False, "no answer"
    q["answer"], q["answered"] = said, h["tick"]
    belief = 'the visitor told me, when I asked "%s": %s' % (q["q"], said)
    m = eng.minds.get(pet["id"])
    if m:
        m.mem.write(belief[:240], h["tick"], source="told by the visitor")   # a belief it holds, and may pass on
    if K.on(cfg, "hooks"):   # SPEC-v4.2 §5.6: an answer that says to do something, or names a place, is an aim for tomorrow
        hooks.aim_from(h, cfg, pet, said, q["q"], "answer")
    if re.search(r"\b(find out|look it up|the book|read about)\b", said.lower()):   # SPEC-v5.1 §6.3 (helper B): "go find out" is a read
        from . import book
        book.wonder(h, cfg, pet, "visitor", q["q"])
    add_event(h, pet, 'the visitor answered you: "%s"' % said)
    pet["news"].append("visitor")
    q["ack"] = "(hears you, and keeps it in mind)"
    if cfg["visitor4"].get("plain_help") and q.get("kind") == "help" and re.search(r"\b(yes|yeah|yep|ok|okay|sure|of course|i will|i'll|i am here|i'm here|help)\b", said.lower()) \
            and not re.search(r"\b(no|not|won't|can't|cannot|never)\b", said.lower()):   # (24 November 2026) a yes to a plea is some help in itself
        from . import needs
        V = cfg["visitor4"]
        pet["needs"]["comfort"] = round(min(100.0, pet["needs"]["comfort"] + V["yes_comfort"]), 2)
        needs.lift(h, cfg, pet, "safety", V["yes_safety"])
        character.set_mood(h, cfg, pet, "happy", "the visitor said it would help")
        add_event(h, pet, "knowing the visitor will help, you rest a little easier")
        q["ack"] = "(eases a little: it rests easier knowing you will help)"
    remember(h, cfg, pet, belief, 3, "told_me")
    moment(h, "visitor", 'the visitor answered %s: "%s"' % (label(pet), said), pet["id"], pet["room"])
    return True, "%s has your answer %s" % (label(pet), q["ack"]) if cfg["visitor4"].get("plain_help") else "%s has your answer" % label(pet)


def t_teach(eng, pet, body, _):
    """A recipe or a skill it doesn't have, or a hint in words; it learns it freely."""
    h, cfg = eng.house, eng.cfg
    what = actions.clean(str(body.get("what") or ""), 200).strip()
    if not what:
        return False, "nothing to teach"
    if K.on(cfg, "hooks"):   # SPEC-v4.2 §5.3-5.4
        ok, said = teach2(eng, pet, what)
        if not ok:
            return ok, said
        taught = said
    elif what in memories.SKILLS:   # (skills 0-10, helper A's)
        memories.practise(h, cfg, pet, what, cfg["visitor4"]["teach_skill"])
        taught = "how to get better at %s" % what
    else:
        try:
            words = craft.words(cfg, what)
        except Exception:
            words = None
        if words:
            if what in pet.get("recipes", {}):
                return False, "%s knows that already" % label(pet)
            craft.learn(h, cfg, pet, what, "taught by the visitor")
            taught = words
        else:   # a hint, in the visitor's own words
            m = eng.minds.get(pet["id"])
            if m:
                m.mem.write(("the visitor told me: " + what)[:240], h["tick"], source="told by the visitor")
            taught = what
    add_event(h, pet, "the visitor taught you: %s" % taught)
    remember(h, cfg, pet, "the visitor taught me: %s" % taught, 3, "taught_me")
    moment(h, "taught", "the visitor taught %s: %s" % (label(pet), taught), pet["id"], pet["room"])
    return True, "%s learned it" % label(pet)


# SPEC-v4.2 B: teaching acts (§5.3), and can be refused (§5.4)
SKILL_AIMS = {"fishing": "fish", "cooking": "cook", "building": "build", "crafting": "make", "foraging": "tend", "reading": "learn", "music": "play",
              "healing": "nurse", "inventing": "design", "talking": "be with", "fighting": "help"}


def doubts(cfg, pet):
    """A hob that will not simply take the visitor's word (§5.4): a proud one, one that does not trust him or believe in
    him, one whose flaw is pride (C's)."""
    proud = pet["needs"].get("pride", 0) >= cfg["hooks"]["proud"] or (bool(pet.get("flaw")) and K.flaw(pet["flaw"])["name"] == "proud")
    return proud or opinions.of(pet, "visitor").get("trust", 5) <= 2 or pet.get("believes") is False


def teach2(eng, pet, what):
    """A recipe is tomorrow's first aim and what the body makes for a day; a skill is told when it matters and shows on
    its card; a hint with a hook (hooks.parse) is a belief that acts, else it goes into tomorrow's plan in his words.
    Returns (ok, what it was taught, in words)."""
    h, cfg = eng.house, eng.cfg
    if what in memories.SKILLS:
        memories.practise(h, cfg, pet, what, cfg["visitor4"]["teach_skill"])
        pet["taught"] = list(dict.fromkeys((pet.get("taught") or []) + [what]))[-6:]
        return True, "how to get better at %s" % what
    try:
        words = craft.words(cfg, what)
    except Exception:
        words = None
    if words:
        if what in pet.get("recipes", {}):
            return False, "%s knows that already" % label(pet)
        craft.learn(h, cfg, pet, what, "taught by the visitor")
        kind = what[5:] if what.startswith("kind:") else None
        if kind:
            pet["taught_recipe"] = {"key": what, "kind": kind, "tick": h["tick"], "until": h["tick"] + 2 * cfg["ticks_per_day"]}
        aim = {"text": "make the %s the visitor showed you" % kind if kind else "try what the visitor showed you: %s" % words[:60], "why": "the visitor taught me",
               "kind": "make" if kind else "cook" if what.startswith("dish:") else "try", "target": None, "since": None, "done": False, "made0": pet.get("made", 0), "from": "taught"}
        pet["aims_next"] = (pet.get("aims_next") or [])[-2:] + [aim]
        return True, words
    hook = hooks.parse(h, what, cfg)
    if hook:
        doubt = doubts(cfg, pet)
        hooks.believe(eng, pet, "the visitor told me: " + what, hook, "told by the visitor", None, doubt)
        if doubt:
            add_event(h, pet, "you are not sure about what the visitor said: %s" % what)
            moment(h, "doubt", "%s isn't sure about that" % label(pet), pet["id"], pet["room"])
        return True, what
    m = eng.minds.get(pet["id"])
    if m:
        m.mem.write(("the visitor told me: " + what)[:240], h["tick"], source="told by the visitor")
    pet["visitor_hints"] = (pet.get("visitor_hints") or [])[-2:] + [what]   # (not "hints": those are the craft hints of wants.py)
    return True, what


def praise_scold(eng, pet, body, up):
    """Pride and its opinion of you move; what it did becomes more or less likely (`pet["praised"]`, read by the body).
    A greedy or prickly hob scolded may feel shame, or resent you."""
    h, cfg = eng.house, eng.cfg
    about = actions.clean(str(body.get("about") or ""), 120).strip()
    key, praised = about or "what it does", pet.setdefault("praised", {})
    praised[key] = praised.pop(key, 0) + (1 if up else -1)   # (the latest last ...
    while len(praised) > 20:   # ... and the oldest go past twenty: 19 October 2026, it grew for ever)
        del praised[next(iter(praised))]
    if up:
        mood, line, cause = "proud", "the visitor praised me%s" % (" for " + about if about else ""), "praised_me"
    else:
        resent = character.trait(pet, "kind") + character.trait(pet, "generous") < -0.5
        mood = "angry" if resent else "ashamed"
        line = "the visitor scolded me%s%s" % (" for " + about if about else "", ", and it wasn't fair" if resent else "")
        cause = "scolded_me"
    remember(h, cfg, pet, line, 3, cause)   # (praised_me and scolded_me carry the pride)
    character.set_mood(h, cfg, pet, mood, line)
    add_event(h, pet, line.replace("me", "you", 1))
    moment(h, "visitor", line.replace(" me", " " + label(pet), 1), pet["id"], pet["room"])
    return True, "%s heard you" % label(pet)


def t_praise(eng, pet, body, _):
    return praise_scold(eng, pet, body, True)


def t_scold(eng, pet, body, _):
    return praise_scold(eng, pet, body, False)


def t_give(eng, pet, body, _):
    """A material, food, or a thing from the store appears in its paws with a sparkle (a `sparkle` burst)."""
    from . import order, store, things
    from .world import a as a_bit, free_tile
    h, cfg = eng.house, eng.cfg
    what = str(body.get("what") or "").strip()
    room = h["rooms"][pet["room"]]
    if what in cfg["house"]["bits"]:
        if len(pet["carrying"]) < cfg["make"]["carry"]:
            pet["carrying"].append(what)
        else:
            things.drop_bits(h, cfg, room, pet["pos"], [what])
        given = a_bit(what)
    else:
        name = store.find(h, cfg, what)
        if not name:
            return False, "there is no %s to give" % what
        src = h["rooms"][store.RID]
        o = src["objects"].pop(name)
        items.place(h, cfg, src, name, o)
        o.pop("wall", None)
        o["pos"] = free_tile(h, cfg, room, pet["pos"], name)
        o["made"]["owner"] = pet["id"]
        room["objects"][name] = o
        order.moved(o, h["tick"], h, cfg, room, name)
        given = "the %s" % name
    craft.burst(h, pet, "sparkle", "the visitor gave %s %s" % (label(pet), given))
    add_event(h, pet, "%s appeared in your paws with a sparkle: a gift from the visitor" % given)
    remember(h, cfg, pet, "the visitor gave me %s" % given, 3, "gift")
    for p in here(h, pet, awake=True):   # (something only the visitor could do, seen)
        believe(h, p, "it saw a gift appear out of nowhere")
    moment(h, "gift", "the visitor gave %s %s" % (label(pet), given), pet["id"], pet["room"])
    return True, "%s has it" % label(pet)


def t_suggest(eng, pet, body, _):
    """An aim considered in its next morning plan (helper D's brain reads pet["suggested"]), weighted by trust."""
    h, cfg = eng.house, eng.cfg
    aim = text_of(body, 120)
    if not aim:
        return False, "nothing suggested"
    pet["suggested"] = (pet.get("suggested") or [])[-2:] + [{"text": aim, "tick": h["tick"], "trust": opinions.of(pet, "visitor").get("trust", 5)}]
    add_event(h, pet, "the visitor would like you to: %s" % aim)
    remember(h, cfg, pet, "the visitor asked me to %s" % aim, 2, "spoke_to")
    return True, "%s will think about it" % label(pet)


# ---- step in ----

def t_stepin(eng, pet, body, _):
    """Stop a fight (they freeze and back off), protect a hob for a world day, or judge a killer (helper C's hooks do the
    deed). Rare, and the whole house remembers."""
    from . import conflict
    h, cfg = eng.house, eng.cfg
    how = body.get("how")
    if how not in HOW:
        return False, "step in how? (stop, protect, pardon, shun, drive out)"
    if not conflict.on(cfg):   # (19 October 2026: with [ladder] off they still drove a hob out, for good)
        return False, "the house has no quarrels to judge"
    if how == "protect":
        conflict.protect(h, cfg, pet["id"], h["tick"] + hours(cfg, cfg["visitor4"]["protect_hours"]))
        line = "the visitor put %s under protection for a day" % label(pet)
        remember(h, cfg, pet, line, 5, "protected_me")
        moment(h, "visitor", line, pet["id"], pet["room"])
    elif how == "stop":
        sc = next((s for s in reversed(h.get("scuffles", [])) if pet["id"] in (s["a"], s["b"]) and not s.get("outcome") and not s.get("stopped") and s["until"] > h["tick"]), None)
        if not sc or not conflict.stop_fight(h, cfg, sc["a"], sc["b"]):
            return False, "%s is in no fight just now" % label(pet)
        line = "the visitor stopped the fight between %s and %s" % (label(h["pets"][sc["a"]]), label(h["pets"][sc["b"]]))
        for x in (sc["a"], sc["b"]):
            remember(h, cfg, h["pets"][x], line, 4, "stepped_in")
    else:   # (helper C's judge: the verdict, its moment, and everyone remembers)
        ok, line = conflict.judge(h, cfg, pet["id"], how)
        if not ok:
            return False, line
        opinions.move(h, cfg, pet, "visitor", "stepped_in" if how == "pardon" else "scolded_me", line, remember=False)
        return True, line
    for p in alive(h):   # the whole house remembers (19 October 2026: lightly; the hobs it was for, above, more)
        if p["stage"] != "egg" and p is not pet:
            memories.add(h, cfg, p, line, 3, about=("visitor", pet["id"]), kind="visitor")
    return True, line


# ---- asking the visitor; belief in the visitor; hard times ----

def words_of(q):
    return " ".join(re.findall(r"\w+", q.casefold()))


def ask(house, cfg, pet, q, kind="question"):
    """A hob's question reaches the inbox: one waiting from each hob at most, only from one that believes in you, and
    never one it asked in the last world day, answered or not, in the same words or nearly (19 October 2026: Paquita
    asked "Is the light on the reeds beautiful?" three times, once just after it was answered)."""
    v = state(house)
    if pet.get("believes") is False or any(x["pet"] == pet["id"] and not x.get("answer") for x in v["inbox"]):
        return None
    if any(x["pet"] == pet["id"] and house["tick"] - x["tick"] < hours(cfg, 24)
           and difflib.SequenceMatcher(None, words_of(x["q"]), words_of(q)).ratio() >= 0.85 for x in v["inbox"]):
        return None
    house["n"]["ask"] = house["n"].get("ask", 0) + 1
    x = {"n": house["n"]["ask"], "pet": pet["id"], "q": q, "tick": house["tick"], "kind": kind, "answer": None}
    v["inbox"].append(x)
    del v["inbox"][:-100]
    return x


def spread(house, cfg, a, b, r):
    """In talk (§10.1): a believer may bring a doubter round, by how much the doubter trusts it; a doubter may put doubt
    into one the visitor has never spoken to."""
    for p, o in ((a, b), (b, a)):
        if p.get("believes") is not False and o.get("believes") is False and r.random() < opinions.of(o, p["id"]).get("trust", 5) / 10:
            believe(house, o, "%s told it so" % label(p))
            memories.add(house, cfg, o, "%s told me the visitor is real, and I believe it now" % label(p), 2, about=("visitor", p["id"]), kind="belief")
            return
        if p.get("believes") is False and o.get("believes") is not False and not memories.relevant(house, cfg, o, about=("visitor",), n=1, only=True) \
                and r.random() < opinions.of(o, p["id"]).get("trust", 5) / 20:
            o["believes"] = False
            memories.add(house, cfg, o, "%s says there is no visitor, and I wonder" % label(p), 2, about=("visitor", p["id"]), kind="belief")
            return


def hardship(pet):
    """What its hard time is: "hurt", "sick", "hungry" or "comfort" (plea; and it pleads once for each, not once a day)."""
    return "hurt" if (pet.get("hurt") or {}).get("level") else "sick" if pet.get("sick") else "hungry" if pet["needs"].get("hunger", 100) < 25 else "comfort"


def plea(pet, plain=False):
    """Asking for help in hard times, in a voice shaped by its traits. `plain` ([visitor4] plain_help, 24 November 2026):
    it says what is wrong and what would help, so the visitor knows which of his tools to reach for."""
    need = "I'm hurt" if (pet.get("hurt") or {}).get("level") else "I'm sick" if pet.get("sick") else "I'm so hungry" if pet["needs"].get("hunger", 100) < 25 else "Things are hard"
    if plain:
        why = (pet.get("hurt") or {}).get("why")
        return {"hurt": "I'm hurt%s. If you tend me it will mend sooner." % (" (%s)" % why if why else ""),
                "sick": "I'm sick. A remedy would help me.",
                "hungry": "I'm so hungry, and there is nothing here to eat. Food would help me.",
                "comfort": "I'm cold and sore and there is nowhere soft to rest. A bed or a blanket where I am would help me."}[hardship(pet)]
    if character.trait(pet, "kind") < -0.3 or character.trait(pet, "ambitious") > 0.5:
        return "I don't ask often. %s. Will you help?" % need
    if character.trait(pet, "brave") < -0.3:
        return "%s... if you're there, could you help?" % need
    return "%s. Please, can you help me?" % need


def tick(eng):
    if not on(eng.cfg):
        return
    h, cfg = eng.house, eng.cfg
    for c in list(eng.__dict__.get("visitor_calls", [])):
        if c["fut"].done():
            eng.visitor_calls.remove(c)
            try:
                answered(eng, c, c["fut"].result())
            except Exception:
                logging.exception("the visitor's talk could not be taken in")
    v = state(h)
    v["protect"] = {k: u for k, u in v["protect"].items() if u > h["tick"]}
    flying = {(c["pet"], c["tick"]) for c in eng.__dict__.get("visitor_calls", [])}
    for x in v["log"][-30:]:   # (19 October 2026: what the visitor said just before a restart was never answered: a thought in flight is lost; it is asked again, once)
        p = h["pets"].get(x["pet"])
        if x["tool"] == "talk" and x.get("said") is None and not x.get("again") and (x["pet"], x["tick"]) not in flying and h["tick"] - x["tick"] <= hours(cfg, 1) \
                and p and p["stage"] not in ("egg", "dead") and not p["sleep"] and p["id"] in eng.minds:
            x["again"] = h["tick"]
            hear(eng, p, x["text"], x["tick"])
    for q in v["inbox"]:   # (19 October 2026: a dead hob's questions could not be answered): a question goes with the hob who asked it
        if not q.get("answer") and not q.get("gone") and h["pets"].get(q["pet"], {}).get("stage", "dead") == "dead":
            q["gone"] = h["tick"]
    if h["tick"] % 10:
        return
    if on5(cfg):
        tick5(eng)
    for p in alive(h):
        if p["stage"] in ("egg", "hatchling") or p["sleep"]:
            continue
        if "believes" not in p:   # §10.1: the cautious and the sly may start out doubting
            doubter = character.trait(p, "curious") < -0.2 or character.trait(p, "honest") < -0.2
            p["believes"] = not (doubter and rnd(h, "doubt", p["id"]).random() < cfg["visitor4"]["doubt"])
        hard = (p.get("hurt") or {}).get("level") or p.get("sick") or p["needs"].get("hunger", 100) < 25 or feel.level(p, "comfort") == 4
        last = max([x["tick"] for x in v["inbox"] if x["pet"] == p["id"] and x["kind"] == "help"], default=-10**9)
        plain = bool(cfg["visitor4"].get("plain_help"))
        if not hard:
            p.pop("pleaded", None)   # (24 November 2026) that hard time is over: the next is a new thing to ask about
        if hard and p["believes"] and h["tick"] - last > hours(cfg, cfg["visitor4"]["plea_hours"]) and not (plain and p.get("pleaded") == hardship(p)):
            if ask(h, cfg, p, plea(p, plain), "help"):
                p["pleaded"] = hardship(p)
                moment(h, "visitor", "%s asked the visitor for help" % label(p), p["id"], p["room"])


def section(eng, pid):
    """The "the visitor" section of a hob's page: whether it believes in you, how it feels about you, what you have done
    with it, its questions, and what you could teach it."""
    h, cfg = eng.house, eng.cfg
    p = h["pets"].get(pid)
    if not p:
        return None
    from .talk import regard
    v = state(h)
    known = set(p.get("recipes", {}))
    return {"believes": p.get("believes", True), "feeling": regard(opinions.of(p, "visitor"), "you") if p["stage"] != "dead" else None,
            "log": [x for x in v["log"] if x["pet"] == pid][-20:], "asks": [x for x in v["inbox"] if x["pet"] == pid][-10:],
            "memories": [m["text"] for m in p.get("memories", []) if "visitor" in m.get("about", [])][-10:], "suggested": p.get("suggested", []),
            "protected": v["protect"].get(pid),
            "can_teach": {"recipes": [{"key": k, "words": craft.words(cfg, k)} for k in sorted(h.get("recipes", {})) if k not in known][:60],
                          "skills": sorted(memories.SKILLS)}}


# ---- SPEC-v4.2 §9 (helper D): the visitor as a character in their world. Switch: [visitor5] on (with [visitor4]) ----
# pet["visitor_theory"]: what it thinks he is, one line (§9.1): its kin's until it has its own, moved by what he does
# ("<theory> — and <what he did>"), rewritten each night by the reflection (B's). state["away"] = {"last": when he was
# last felt (a tool, or the page open on the house), "noted": the absence told} (§9.2). A visitor's mark on a wall gains
# "to" (a hob's id, or "house", from its first word) and "read" (who has read it) (§9.3). state["tend"] = {hob id: the
# tick the visitor's hour beside it is up}, for the page's timer (§9.4).

THEORIES = ("the visitor is the one who feeds us", "the visitor made the house", "the visitor is a hob who grew too big",
            "there is no visitor, things just come")
MOVES = {"talk": "he spoke to me", "answer": "he answers when I ask", "teach": "he showed me how", "praise": "he was pleased with me",
         "scold": "he was cross with me", "give": "things come from him out of nowhere", "tend": "he sat with me when I was poorly",
         "remedy": "he gave me a remedy when I was sick"}
NOBODY = re.compile(r"\bno visitor\b|\bnot real\b|\bnobody (is )?there\b|\bnever was\b")
KNOW = "to find out what the visitor is"


def on5(cfg):
    return on(cfg) and K.on(cfg, "visitor5")


def base(text):
    return (text or "").split(" — ")[0].strip()


def kin_theory(house, pet):
    """A theory to start from: its kin's (a parent's, the kin of a founder egg, the family's), or one of the house's own."""
    kin = character.parents_of(house, pet) + [house["pets"][k] for k in [pet.get("kin")] if k in house["pets"]]
    kin += sorted((p for p in house["pets"].values() if p.get("family", 1) == pet.get("family", 1) and p is not pet), key=lambda p: p["id"])
    had = next((base(p["visitor_theory"]) for p in kin if p.get("visitor_theory")), None)
    return had or rnd(house, "theory", pet["id"]).choice(THEORIES)


def theory(house, pet):
    """(contracts.API) Its theory of the visitor, one line (§9.1)."""
    return pet.get("visitor_theory") or kin_theory(house, pet)


def move(house, cfg, pet, did):
    """What he did moves its theory: kept beside what it thinks, until the night's reflection makes one line of them.
    A theory may be false and stay false: nothing here corrects it."""
    pet["visitor_theory"] = actions.clean("%s — and %s" % (base(theory(house, pet)), did), 200)


def involves(pet):
    """Does its theory have him in it (one who believes there is no visitor misses nobody)?"""
    return pet.get("believes") is not False and not NOBODY.search((pet.get("visitor_theory") or "").lower())


def wants_to_know(pet):
    return bool(pet.get("drive")) and K.drive(pet["drive"])["name"] == KNOW


def question(pet):
    """Its question for the inbox, from its theory (§9.1: "Are you the one who made the walls?")."""
    t = base(pet.get("visitor_theory")).rstrip(".")
    if NOBODY.search(t.lower()):
        return "Is anyone there?"
    m = re.match(r"(?:the visitor|he) (is )?(.+)", t, re.I)
    return ("Are you %s?" if m.group(1) else "Is it you who %s?") % m.group(2) if m else "What are you?"


def felt(house):
    """When he was last felt in the house: a tool used, or the page open on it."""
    return max([house.get("visitor_last", LONG_AGO)] + [x["tick"] for x in state(house)["log"]])


def away(house, cfg):
    """World days since he was last felt (counted from when the house began to keep count)."""
    a = state(house).get("away") or {"last": house["tick"]}
    return world_days(cfg, max(a["last"], felt(house)), house["tick"])


def addressee(house, text):
    """A note's first word, if it names a hob ("Ada, the clay is in the storeroom"; "to Ada: ..."), else the house."""
    m = re.match(r"\s*(?:to |dear |for )?([A-Za-z][\w'-]*)\s*[:,;-]", text or "", re.I)
    pid = hooks.hob_of(house, m.group(1)) if m else None
    return pid or "house"


def notes(house):
    """The visitor's marks on the walls, each with whom it is to: [(room, mark)]."""
    out = []
    for room in house["rooms"].values():
        for m in room.get("marks", []) if room.get("type") else ():
            if m["by"] == "visitor":
                m.setdefault("to", addressee(house, m["text"]))
                out.append((room, m))
    return out


def unread(house):
    """Notes to a living hob it has not read: what the director's letter may bring by the train."""
    return [(r, m) for r, m in notes(house) if house["pets"].get(m["to"], {}).get("stage") not in (None, "egg", "dead") and m["to"] not in m.get("read", [])]


def read_note(house, cfg, pet, m, how):
    """It reads what he wrote (§9.3): "the visitor wrote to you: ...", its brain hears of it, and the words may be an aim."""
    from . import brain4
    m.setdefault("read", []).append(pet["id"])
    said = 'the visitor wrote %s%s: "%s"' % ("to you " if m["to"] == pet["id"] else "", how, m["text"])
    add_event(house, pet, said)
    pet["news"].append("visitor")
    brain4.notable(house, cfg, pet, "visitor", said, ["visitor"])
    remember(house, cfg, pet, said, 3, "told_me")
    if K.on(cfg, "hooks"):
        hooks.aim_from(house, cfg, pet, m["text"], "the visitor wrote it to me", "note")
    move(house, cfg, pet, "he writes to me")
    return said


def deliver(house, cfg, target=None):
    """The director's letter (§8.2): one unread note comes by the train to the hob it is for. Returns what happened, or None."""
    waiting = unread(house)
    room, m = next(((r, m) for r, m in waiting if m["to"] == target), waiting[0] if waiting else (None, None))
    if not m:
        return None
    pet = house["pets"][m["to"]]
    read_note(house, cfg, pet, m, "in a letter that came by the train")
    return "a letter from the visitor came by the train for %s" % label(pet)


def remedy_in(house):
    """A remedy in the house: (a hob carrying it, None) or (a room, the spot it lies on), or None."""
    from .health import REMEDY
    for p in alive(house):
        if REMEDY in p.get("carrying", []):
            return p, None
    return next(((r, s) for r in house["rooms"].values() for s in r.get("spots", []) if s["bit"] == REMEDY), None)


def t_tend(eng, pet, body, _):
    """He sits with a sick or hurt hob a world hour (§9.4); when it is up, a day's tending (A's health.tend, by "visitor")."""
    from . import health
    h, cfg = eng.house, eng.cfg
    if not on5(cfg):
        return False, "the visitor's tending is switched off"
    v = state(h).setdefault("tend", {})
    if pet["id"] in v:
        return False, "you are sitting with %s already" % label(pet)
    if not health.need_of(h, pet):
        return False, "%s needs no tending today" % label(pet)
    v[pet["id"]] = h["tick"] + hours(cfg, cfg["visitor5"]["tend_hours"])
    add_event(h, pet, "someone is sitting with you; you cannot see him, but you know it is the visitor")
    moment(h, "visitor", "the visitor sat down with %s, who is poorly" % label(pet), pet["id"], pet["room"])
    return True, "you sit with %s for a world hour" % label(pet)


def t_remedy(eng, pet, body, _):
    """He gives a sick hob a remedy the house has (§9.4): back two stages (health.tend, how "remedy")."""
    from . import health
    h, cfg = eng.house, eng.cfg
    if not on5(cfg):
        return False, "the visitor's remedy is switched off"
    if not health.stage_of(pet):
        return False, "%s is not sick" % label(pet)
    got = remedy_in(h)
    if not got:
        return False, "the house has no remedy"
    where, spot = got
    if spot is None:
        where["carrying"].remove(health.REMEDY)
    else:
        where["spots"].remove(spot)
    health.tend(h, cfg, pet, "visitor", health.REMEDY)
    add_event(h, pet, "the visitor gave you the remedy")
    moment(h, "visitor", "the visitor gave %s the remedy" % label(pet), pet["id"], pet["room"])
    return True, "%s has the remedy" % label(pet)


def tick5(eng):
    """Every ten ticks: theories started from kin's; absence noticed, and a return; notes read; the visitor's hour beside
    a sick hob up; a question from its theory, now and then, the more if it wants to know what he is."""
    from . import brain4, health
    h, cfg = eng.house, eng.cfg
    C, v, day = cfg["visitor5"], state(h), h["clock"]["day"]
    hobs = [p for p in alive(h) if p["stage"] != "egg"]
    for p in hobs:
        if not p.get("visitor_theory"):
            p["visitor_theory"] = kin_theory(h, p)
    a = v.setdefault("away", {"last": h["tick"], "noted": False})
    last = max(a["last"], felt(h))
    if last > a["last"]:
        if a["noted"]:   # §9.2: back after days away
            moment(h, "visitor back", "the visitor came back to the house after days away", None, h.get("visitor_room"))
            for p in hobs:
                memories.add(h, cfg, p, "the visitor came back, after days away", 3, about=("visitor",), kind="visitor")
                if involves(p):
                    move(h, cfg, p, "he came back")
        a.update(last=last, noted=False)
    elif not a["noted"] and world_days(cfg, last, h["tick"]) >= C["absent_days"]:
        a["noted"] = True
        for p in hobs:
            if involves(p):
                brain4.notable(h, cfg, p, "visitor", "the visitor has not been felt in the house for days", ["visitor"])
                memories.add(h, cfg, p, "the visitor has not been felt in the house for days", 2, about=("visitor",), kind="visitor")
                move(h, cfg, p, "he has not come for days")
    for room, m in notes(h):
        for p in hobs:
            if p["room"] == room["id"] and not p["sleep"] and p["stage"] != "hatchling" and m["to"] in (p["id"], "house") and p["id"] not in m.get("read", []):
                read_note(h, cfg, p, m, "on the %s" % m["on"])
    for pid, until in list(v.get("tend", {}).items()):
        if until <= h["tick"]:
            del v["tend"][pid]
            if h["pets"].get(pid, {}).get("stage") not in (None, "egg", "dead"):
                health.tend(h, cfg, h["pets"][pid], "visitor", "tend")
    present = h["tick"] - h.get("visitor_last", LONG_AGO) <= 10
    for p in hobs:
        if p["sleep"] or p["stage"] == "hatchling":
            continue
        if present and p["room"] == h.get("visitor_room") and p.get("watched_day") != day and involves(p):
            p["watched_day"] = day
            move(h, cfg, p, "I feel him watching")
        if p.get("asked_day") != day and p.get("believes") is not False:
            p["asked_day"] = day
            if rnd(h, "theory ask", p["id"], day).random() < (0.5 if wants_to_know(p) else 0.1):
                ask(h, cfg, p, question(p), "question")


# ---- SPEC-v5.3.2 §1: place and remove. A room, a tile, and what its kind does. ----

def nature(cfg, kind):
    """What a kind is mainly like, in the one word the house uses for a nature (a recipe's `material` is a nature, a
    key of materials.toml, not a bit, since SPEC-v3.2; things.prop reads it every tick): kinds.toml's first part,
    parts.toml's first material that part takes, and the first nature a bit of that material can be ("lantern" - oil -
    "bright"). "hard" where the bit is not one the house knows."""
    ps = (cfg["items5"]["kind"].get(kind) or {}).get("parts") or []
    p = str(ps[0]).split(" of ")[0].strip() if ps else ""
    natures = {k for k, v in cfg["materials"].items() if isinstance(v, dict) and k not in ("rules", "behaviors")}
    for m in (cfg["parts51"]["part"].get(p) or {}).get("materials") or []:
        for n in [m] + list((cfg["house"]["bits"].get(m) or {}).get("can") or []):
            if n in natures:
                return n
    return "hard"


def part_words(cfg, kind):
    """What the kind's first part is for, in parts.toml's own words: "a cushion is soft to sit or lie on"."""
    ps = (cfg["items5"]["kind"].get(kind) or {}).get("parts") or []
    p = str(ps[0]).split(" of ")[0].strip() if ps else ""
    return (cfg["parts51"]["part"].get(p) or {}).get("words", "")


def palette(house, cfg):
    """What "place" offers: every kind in kinds.toml, with the words for it, what it does and whether it hangs. The
    page draws each one with the catalog's own art (view/assets/kinds.json), so no picture travels with it."""
    out = []
    for kind, e in sorted((cfg["items5"].get("kind") or {}).items()):
        art = cfg["kinds"].get(kind) or {}
        out.append({"kind": kind, "words": art.get("words") or [kind], "a": art.get("a") or "a",
                    "verbs": sorted((e.get("verbs") or {})), "nature": nature(cfg, kind), "wall": bool(art.get("wall")),
                    "how": part_words(cfg, kind)})
    return out


def room_of(house, cfg, body):
    """The room the tool works on: the one asked for, else the one the visitor is looking at."""
    return house["rooms"].get(str(body.get("room") or house.get("visitor_room") or ""))


def awake_in(house, room):
    """Every living hob awake in the room (SPEC-v5.3.2 §1: they are told what appeared)."""
    return [p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]]


def a_cap(cfg, recipe):
    """"a brown cushion" as a sentence starts it: "A brown cushion"."""
    words = things.a_thing(cfg, recipe)
    return words[0].upper() + words[1:]


def t_place(eng, _pet, body, _):
    """He sets a thing down on the tile he clicked. It is the visitor's, it does what its kind does (its verbs are
    kinds.toml's, read by items.entry), and every hob awake in the room is told something has appeared."""
    h, cfg = eng.house, eng.cfg
    room = room_of(h, cfg, body)
    if not room or not room["type"]:
        return False, "no such room"
    kind = str(body.get("kind") or "")
    if kind not in (cfg["items5"].get("kind") or {}):
        return False, "there is no kind of thing called %s" % (kind[:40] or "?")
    hangs = bool((cfg["kinds"].get(kind) or {}).get("wall"))
    if hangs:
        tile = things.wall_slot(h, room)   # (a hanging thing goes where the wall has room for one)
        if not tile:
            return False, "there is no room left on that wall for a %s" % kind
    else:
        pos = body.get("pos")
        ok = isinstance(pos, (list, tuple)) and len(pos) > 1 and all(str(x).lstrip("-").isdigit() for x in list(pos)[:2])
        near = [int(pos[0]), int(pos[1])] if ok else [cfg["W"] // 2, cfg["H"] // 2]
        near = [min(max(near[0], 1), cfg["W"] - 2), min(max(near[1], 1), cfg["H"] - 2)]
        tile = free_tile(h, cfg, room, near)   # (the tile asked for if nothing stands on it, else the nearest free one)
    recipe = {"kind": kind, "material": nature(cfg, kind), "size": body.get("size") if body.get("size") in (1, 2, 3) else 2,
              "color": actions.clean(str(body.get("color") or "brown"), 20).lower() or "brown",
              "purpose": actions.clean(part_words(cfg, kind) or things.everyday_kind(cfg, kind), 80)}
    name = things.unique_name(h, cfg, things.everyday_kind(cfg, kind))
    recipe["name"] = name
    h["n"]["thing"] += 1
    o = {"pos": list(tile), **({"wall": True} if hangs else {}),
         "made": {"id": h["n"]["thing"], "recipe": recipe, "by": OWNER, "owner": OWNER, "tick": h["tick"], "bits": [],
                  "uses": 0, "ups": 0, "used_at": h["tick"], "heirloom": None, "behavior": None, "fine": 0,
                  "how": "set down by the visitor", "made_in": room["name"], "users": {}, "words": []}}
    room["objects"][name] = o
    it = items.of(h, cfg, o, name, room)   # SPEC-v5.0 §1.1: its item now, its verbs from kinds.toml
    does = ", ".join(K.VERB_WORDS[v] for v in sorted((it or {}).get("verbs") or {}, key=lambda v: -it["verbs"][v]))
    words, awake = things.a_thing(cfg, recipe), awake_in(h, room)
    for p in awake:
        add_event(h, p, "%s has appeared here, and you know who put it there" % words)
    moment(h, "visitor", "%s appears in %s: the visitor set it down%s" % (a_cap(cfg, recipe), room["name"],
           ", and %d awake saw it" % len(awake) if awake else ""), None, room["id"])
    return True, "%s stands in %s%s. It is the visitor's." % (a_cap(cfg, recipe), room["name"], "; " + does if does else " and does nothing")


def t_remove(eng, _pet, body, _):
    """He takes back what he placed. Nothing else is his to take away."""
    h, cfg = eng.house, eng.cfg
    room = room_of(h, cfg, body)
    if not room or not room["type"]:
        return False, "no such room"
    name = str(body.get("name") or "")
    o = room["objects"].get(name)
    if not o or "made" not in o:
        return False, "there is no %s here to take away" % (name[:40] or "thing")
    if o["made"].get("by") != OWNER:   # (what he placed, whoever has it now; never a thing a hob made, even one given to him)
        return False, "%s is not the visitor's to take away" % things.a_thing(cfg, o["made"]["recipe"])
    room["objects"].pop(name)
    words, awake = things.a_thing(cfg, o["made"]["recipe"]), awake_in(h, room)
    things.gone(h, o, name, "taken away by the visitor", room)
    for p in awake:
        add_event(h, p, "%s has gone: the visitor took it away" % words)
    moment(h, "visitor", "%s goes out of %s: the visitor took it away" % (a_cap(cfg, o["made"]["recipe"]), room["name"]), None, room["id"])
    return True, "%s is gone from %s." % (a_cap(cfg, o["made"]["recipe"]), room["name"])
