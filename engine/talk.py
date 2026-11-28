"""SPEC-v4.0 §5 conversations: two hobs, one model call, both sides; the engine decides the effects (helper B).
§6.1 cooperation that comes of talk (help taken on as an aim, lessons, gifts promised and kept, trade, gatherings).
Switch: [talk] on.

A conversation starts where two hobs share a room, awake and free, and one of them has something on its mind. The
brain writes the lines, what came of it and how each feels after (`schema`); the engine decides what that does
(`apply`): opinions move only by named causes (opinions.toml), promises become aims, insults and threats become
grievances (helper C's ladder climbs from them), and it is remembered when it mattered.

SPEC-v4.2 §7 (helper C), [talk2] on: talk with subtext. The engine gives both sides a subject (`subject`: a memory
both hold, the day's happening, a death, a first, the visitor's last visit, a belief one holds and the other doesn't,
an elder's tale); the packet carries each hob's self-page, drive and flaw, traits in words, its voice card with its
three lines, what it already knows of the other, its beliefs and what it keeps to itself (`packet2`). The reply
(`schema2`) fills, before its four to eight longer lines, each speaker's `minds`: wants, holds (a secret always
there), knows, remember; they become memories (memories.from_talk) and the record keeps them with the subject. A reply
without them is a talks_failed and asked once more; a second without them is defaulted and counted. Babble is only a
hatchling's, and a hatchling learns a word a day from whoever talks to it. With [drives] on a secret can come out."""
import asyncio
import json
import logging
import re

from . import contracts
from . import bonds, character, craft, feel, memories, needs, opinions
from .world import add_event, alive, family, here, hours, knows, label, moment, relation, rnd

MOODS = ("happy", "content", "grumpy", "sad", "afraid", "angry", "proud", "ashamed", "lonely", "excited")
CAME = ("news", "help asked", "help given", "help refused", "lesson", "gossip", "plan", "argument", "apology", "threat",
        "insult", "making up", "gift promised", "trade", "gathering", "close bond", "justice", "nothing")
LITTLE = ("hatchling", "child")
OCCASIONS = {"hatched": "celebration", "death": "vigil", "discovery": "celebration", "machine": "celebration", "design built": "celebration", "cooked": "meal"}
NEWS = ("made", "discovery", "catch", "cooked", "machine", "design built", "invented", "harvest", "read", "song", "tamed", "gift")
# the opinions.toml causes this module moves opinions by (helper A's data gives the amounts)
CAUSES = ("talked_kindly", "talked_harshly", "insult", "threatened_me", "apology", "made_up", "taught_me", "helped_me", "ignored_me",
          "kept_promise", "broke_promise", "lied_to_me", "worked_together", "ate_together", "sang_with")
VOICE = {   # how a pole talks (§5 "Voice"), for the packet
    ("kind", -1): "curt and sharp", ("kind", 1): "warm", ("playful", 1): "teases", ("playful", -1): "lectures",
    ("honest", -1): "flatters, and fibs when it suits", ("brave", -1): "trails off, unsure", ("brave", 1): "speaks up boldly",
    ("social", -1): "says little", ("social", 1): "chatters", ("generous", -1): "bargains", ("patient", -1): "hurries, cuts in",
    ("curious", 1): "asks questions", ("ambitious", 1): "boasts a little", ("tidy", 1): "fusses about mess", ("patient", 1): "takes its time",
}
# SPEC-v4.2.2 §1: the talk prompt, verbatim; the engine fills the angle brackets (`packet2`)
TALK = """Two neighbours in a small house, talking. Write what they say, taking turns, <N> lines in all.

How hobs talk: like neighbours, not like a book. Short lines, most under fifteen words. They talk about real things:
what they're doing right now, what they want, what happened today, who annoyed them, what they're afraid of, what
they found. They ask each other things and answer what they're asked. They tease, complain a little, change the
subject, say one odd thing they actually think. They use each other's names. They can be wrong, and they can lie.
Nobody makes a speech. Nobody says "the hour", "the ache", "the shape of", or anything that sounds like a poem.

Each line answers the line before it: a question gets an answer, a complaint gets a reaction, a story gets a
question. The second line can't ignore the first.

What's between them right now: <subject, in plain words>.
<A> wants from this talk: fill in. <A> won't say: fill in (its secret, if it has one, always goes here).
<B> wants: fill in. <B> won't say: fill in.

Then the lines. Then, for each: one plain sentence of what they now know about the other that they didn't before,
and one thing each will remember from this (or nothing).

Here is how it should sound. These are examples of the manner only; the words must be about these two hobs and this
house today.

Example 1 (a favour, a grumble):
  Wren: Sipho. Sipho! Have you seen the small hammer?
  Sipho: On the bench where you left it. Under your cushion.
  Wren: Why is it under my cushion.
  Sipho: You sat on it to keep it from me. Yesterday. You said so.
  Wren: That sounds like me. Can you bring it? My feet are cold.
  Sipho: Your feet are always cold. Fine. You owe me a bean.

Example 2 (news, with content):
  Bodhi: Did you hear the roof went in the attic last night?
  Mara: I was under it. There's a puddle on my rug the size of a pond.
  Bodhi: Oh no. The good rug?
  Mara: The good rug. Pansy says she'll mend the beam but Pansy says a lot of things.
  Bodhi: She fixed the loom though.
  Mara: She fixed the loom in three days and told everyone about it for six.

Example 3 (a child and a grown hob):
  Fen: Why is the pond dark?
  Oya: Because the sun's gone round the back. It'll be light again by breakfast.
  Fen: Does the fish know?
  Oya: The fish doesn't know anything, Fen. That's why it's a fish.
  Fen: I'm going to tell it.
  Oya: You do that. Don't fall in. I'm not fishing you out twice in one day.

Example 4 (something underneath):
  Tam: You've been in the cellar a lot.
  Lio: It's cool down there. It's summer.
  Tam: It's cool in the pond room too and you never go in the pond room.
  Lio: The pond room has Brody in it.
  Tam: So it's not the cool.
  Lio: Leave it, Tam. Do you want a cup or not? I made four."""
# SPEC-v5.3 §5.3 ([talk3] on): lines get room when there's content, and a fifth example, about a project; off, TALK as it was
TALK53 = TALK.replace("Short lines, most under fifteen words.", "A line may be two or three sentences when there's something to tell — what you saw, "
                      "what happened, what you want. Short when there isn't.") + """

Example 5 (a project, something to tell):
  Ivo: The frame's up by the willow. Took me all morning and two trips for reed.
  Nell: You're really going out there, then.
  Ivo: I'm really going. You can come and see it. Bring the hammer, mine's split."""
AGAIN = "Each line answers the line before it: a question gets an answer, a complaint gets a reaction, a story gets a question. The second line can't ignore the first."
PURPLE = ("the hour", "the ache", "the shape of")   # §6: what a talk that reads like a novel says (counted, never retried)


def on(cfg):
    return bool(cfg.get("talk", {}).get("on"))


def recent(house, ticks_back):
    """The talks and snubs of the last `ticks_back` ticks, in order (for the page's bubbles)."""
    return sorted((t for t in house.get("talks", []) + house.get("snubs", []) if house["tick"] - t["tick"] <= ticks_back), key=lambda t: t["tick"])


def attach(house, moments):
    """Moments read back from the log have only their text: a talk's gets its lines and what came of it again, from
    house["talks"] (its last 300), by tick and first speaker."""
    talks = {(t["tick"], t["a"]): t for t in house.get("talks", [])}
    for m in moments:
        t = talks.get((m["tick"], m["pet"])) if m["kind"] == "talk" else None
        if t:
            m.update(lines=t["lines"], came_of=t["came_of"], pets=[t["a"], t["b"]], talk=t["n"], **{k: t[k] for k in ("subject", "minds", "rounds", "third") if k in t})
    return moments


# ---- words ----

def regard(op, name):
    """An opinion in words, never a number."""
    l, out = op["liking"], []
    out.append("is very fond of %s" % name if l >= 7 else "likes %s" % name if l >= 3 else "can't stand %s" % name if l <= -7
               else "dislikes %s" % name if l <= -3 else "feels nothing much either way about %s" % name)
    if op.get("trust", 5) >= 8:
        out.append("trusts them")
    elif op.get("trust", 5) <= 2:
        out.append("doesn't trust them")
    if op.get("fear", 0) >= 5:
        out.append("is afraid of them")
    if op.get("respect", 5) >= 8:
        out.append("looks up to them")
    elif op.get("respect", 5) <= 2:
        out.append("looks down on them")
    return ", ".join(out)


def voice(pet):
    if pet["stage"] == "hatchling":
        return "only babbles"
    if pet["stage"] == "child":
        return "babbles, with a few real words"
    axes = sorted(character.AXES, key=lambda a: -abs(character.trait(pet, a)))
    said = [VOICE.get((a, 1 if character.trait(pet, a) > 0 else -1)) for a in axes[:3] if abs(character.trait(pet, a)) >= 0.3]
    return "; ".join(s for s in said if s) or "plain"


def babble(text, stage, r, words=None):
    """Little ones babble (§5): a hatchling all of it, a child with a few real words mixed in. `words`: those a
    hatchling has learned (SPEC-v4.2 §7.6), now and then in its babble."""
    syl = ["ba", "da", "mm", "goo", "na", "pa", "ee", "bo"]
    if stage == "hatchling":
        out = [r.choice(syl) for _ in range(r.randint(2, 4))]
        if words and r.random() < 0.6:
            out[r.randrange(len(out))] = r.choice(words)
        return "-".join(out) + r.choice(["!", "?", "..."])
    return " ".join(w if r.random() < 0.4 else r.choice(syl) for w in text.split()[:8]) or "ba!"


def unnamed(text, pets):
    """A line without its speaker's name in front ("Bogna: Align the leaves" -> "Align the leaves"), however often."""
    text, names = str(text).strip(), [label(p).lower() for p in pets if label(p)]
    while any(text.lower().startswith(n + ":") for n in names):
        text = text.split(":", 1)[1].strip()
    return text


def short(text, words=20, chars=140):
    return " ".join(re.sub(r"\s+", " ", str(text)).strip().split(" ")[:words])[:chars]


# ---- what is on a hob's mind ----

def grievances(house, by, against):
    return [g for g in house.get("grievances", []) if g["by"] == by and g["against"] == against and not g.get("closed")]


def occasion(house, cfg):
    """A birth, a death or a first in the last world day: (kind of gathering, its moment), or None."""
    m = next((m for m in reversed(house["moments"]) if m["kind"] in OCCASIONS and house["tick"] - m["tick"] <= hours(cfg, 24)), None)
    return (OCCASIONS[m["kind"]], m) if m else None


def on_mind(house, cfg, pet, other):
    """What it might bring up (§5 "When"): news, a want, a grudge, gratitude, gossip, a question, a plan, loneliness."""
    out, oid, name = [], other["id"], label(other)
    out += ["a grudge against %s: %s" % (name, g["why"]) for g in grievances(house, pet["id"], oid)[:1]]
    op = opinions.of(pet, oid)
    if op["liking"] <= -3 and not out:
        out.append("it dislikes %s" % name)
    good = [c for c in op.get("causes", []) if (c.get("d") or {}).get("liking", 0) > 0 and house["tick"] - c["tick"] <= hours(cfg, 24)]
    if good:
        out.append("grateful to %s: %s" % (name, good[-1]["why"]))
    news = [m for m in house["moments"] if m.get("pet") == pet["id"] and m["kind"] in NEWS and house["tick"] - m["tick"] <= hours(cfg, 3)]
    if news:
        out.append("news: %s" % news[-1]["text"])
    aim_ = next((a for a in pet.get("aims") or [] if not a.get("done") and a["kind"] != "gather"), None)
    if aim_:
        out.append("a plan: %s" % aim_["text"])
    elif pet.get("wants"):
        out.append("wants: %s" % pet["wants"][0].get("text", ""))
    third = [(k, v["liking"]) for k, v in (pet.get("opinions") or {}).items() if k not in (oid, "visitor") and abs(v["liking"]) >= 4
             and k in house["pets"] and house["pets"][k]["stage"] != "dead"]
    if third:
        k, l = max(third, key=lambda kl: abs(kl[1]))
        out.append("has views about %s (%s)" % (label(house["pets"][k]), "likes them" if l > 0 else "dislikes them"))
    if character.trait(pet, "curious") >= 0.4:
        out.append("full of questions")
    if feel.level(pet, "company") >= 2:
        out.append("lonely")
    if (pet.get("hurt") or {}).get("level") or pet.get("sick") or pet["needs"].get("hunger", 100) < 25:   # (a lasting limp alone is no hard time)
        out.append("in hard times")
    occ = occasion(house, cfg)
    if occ and character.trait(pet, "social") > 0:
        out.append("thinking of this: %s" % occ[1]["text"])
    if pet.get("believes") is False:
        out.append("doesn't believe the visitor is real")
    for k in house.get("killings", []):   # §7.4: the family decides in talk what to do with a killer
        if k.get("known") and k.get("verdict") is None and k["killer"] in house["pets"] and k["killer"] != pet["id"]:
            out.append("what to do about %s, who killed %s" % (label(house["pets"][k["killer"]]), label(house["pets"][k["dead"]]) if k["dead"] in house["pets"] else "one of us"))
            break
    if two(cfg):   # SPEC-v4.2 §7: the beliefs it acts on (§5.1's hooks)
        out += ["believes: %s" % b["text"] for b in (pet.get("hooked") or [])[:2]]
    if three(cfg):   # SPEC-v5.3 §5.2: a talk it left open with this one
        out += ["wants to talk more about %s" % t["subject"] for t in threads(house, pet, other) if t["by"] == pet["id"]][:1]
    return out


def two(cfg):
    """SPEC-v4.2 §7: talk with subtext ([talk2])."""
    return contracts.on(cfg, "talk2")


def three(cfg):
    """SPEC-v5.3 §5: talk that goes on ([talk3]): rounds, threads, a third listener, subjects never repeated. It rides on
    [talk2]'s talk with subtext (the rounds are its replies)."""
    return two(cfg) and contracts.on53(cfg, "talk3")


# ---- SPEC-v5.3 §5.2, §5.5 (helper C): threads, and the subjects habits, projects and perception give ----

def threads(house, pet, other=None):
    """API53: its threads open (contracts.thread), with `other` (a hob or its id) only if given. Picked-up ones are gone
    from the list, and talk.tick drops those past [talk3] thread_days."""
    oid = other["id"] if isinstance(other, dict) else other
    return [t for t in pet.get("threads") or [] if t.get("picked") is None and (oid is None or t["with"] == oid)]


def _who(house, pid):
    p = house["pets"].get(pid or "")
    return label(p) if p else ""


HABIT_TALK = {"tidy": "{who}'s tidying", "tend": "{who} tending the plots", "praise": "{who} praising everyone's work",
              "teach": "{who} showing the young ones how things are made", "wander": "{who} going out every day",
              "watch": "{who} keeping an eye on {target}", "keep company": "{who} always working beside {target}"}   # (take, prank: unseen; collect, hoard, mark: by their marks)


def _habit_subjects(house, cfg, a, b, third=None):
    """"Brody's pile": the habits of the two (and a third) in plain words. A pile, a found hoard or marks only once they
    stand (house["v5"]["marks"]); a take or a prank never (nobody is meant to see them)."""
    out, ids = [], [p["id"] for p in (a, b, third) if p]
    for m in ((house.get("v5") or {}).get("marks") or {}).values():
        if m.get("by") in ids and m.get("gone") is None and (m["kind"] in ("pile", "mark") or (m["kind"] == "hoard" and m.get("found") is not None)):
            out.append("%s's %s" % (_who(house, m["by"]), {"pile": "pile", "mark": "marks on the wall", "hoard": "hoard"}[m["kind"]]))
    for p in (a, b, third):
        for h in (p or {}).get("habits") or []:
            if isinstance(h, dict) and h.get("name") in HABIT_TALK and not h.get("fading"):
                out.append(HABIT_TALK[h["name"]].format(who=label(p), target=_who(house, h.get("target")) or "someone"))
    return out


def _project_subjects(house, cfg, a, b, third=None):
    """"Antonia's shelter": the projects any of them is named on, not abandoned."""
    ids = {p["id"] for p in (a, b, third) if p}
    out = []
    for pr in ((house.get("v5") or {}).get("projects") or {}).values():
        if ids & set(pr.get("names") or pr.get("owners") or []) and pr.get("state") != "abandoned":
            who = " and ".join(_who(house, x) for x in pr.get("names") or pr.get("owners") or [] if _who(house, x)) or "someone"
            out.append("%s's %s" % (who, pr.get("build") or pr.get("kind")))
    return out


def _thread_subjects(house, cfg, a, b, third=None):
    """A talk the two left open (start takes it first, and says so)."""
    return [t["subject"] for t in threads(house, a, b) + threads(house, b, a) if t["subject"]][:1]


def _perception_subjects(house, cfg, a, b, third=None):
    """A mark one of them saw that isn't theirs: its perception line ("the small hammer is not where it was")."""
    ids = {p["id"] for p in (a, b, third) if p}
    return [m["words"] for m in ((house.get("v5") or {}).get("marks") or {}).values()
            if m.get("words") and m.get("by") not in ids and {a["id"], b["id"]} & set(m.get("seen") or []) and m.get("gone") is None]


SUBJECT53 = {"habit": _habit_subjects, "project": _project_subjects, "thread": _thread_subjects, "perception": _perception_subjects}


def pair_key(a, b):
    return "|".join(sorted((a["id"], b["id"])))


def thread_of(house, cfg, a, b):
    """The open thread between them still within [talk3] thread_days, the newest, or None."""
    t = sorted((x for x in threads(house, a, b) + threads(house, b, a) if house["tick"] - x["tick"] <= hours(cfg, 24 * cfg["talk3"]["thread_days"])),
               key=lambda x: x["tick"])
    return t[-1] if t else None


def urgent(house, cfg, pet):
    """A hob with an urgent job (urgency 4) says no to another round (§5.1)."""
    from . import jobs
    j = jobs.of(house, pet) if jobs.on(cfg) else None
    return bool(j and (jobs.deficit_of(house, j) or {}).get("urgency", 0) >= 4)


def go_on(house, cfg, reply, a, b):
    """§5.1 each side's go_on and why from a round's reply (contracts.go_on: missing is no), with the engine's word: a hob
    with an urgent job says no."""
    g = contracts.go_on(reply, names(a, b))
    for n, p in zip(names(a, b), (a, b)):
        if g[n]["go_on"] == "yes" and urgent(house, cfg, p):
            g[n] = {"go_on": "no", "why": "I've something urgent to see to"}
    return g


def pick_third(eng, a, b, r):
    """§5.4: another hob in the room, awake and free, as a listener, at [talk3] third."""
    h = eng.house
    can = sorted((p for p in here(h, a, awake=True) if p["id"] not in (a["id"], b["id"]) and p["stage"] != "hatchling" and free(eng, p)), key=lambda p: p["id"])
    return r.choice(can) if can and r.random() < eng.cfg["talk3"]["third"] else None


def names3(a, b, third):
    """The reply's names for the two and the listener (its id when its name is taken)."""
    ns = names(a, b)
    return ns + ([label(third) if label(third) not in ns else third["id"]] if third else [])


def left(h, cfg, a, b, subj, g):
    """§5.2 a talk that ended with a side wanting more leaves a thread on both, and a memory with its content."""
    want = [(p, g[n]) for n, p in zip(names(a, b), (a, b)) if g[n]["go_on"] == "yes"]
    if not want:
        return None
    by, w = want[0]
    other = b if by is a else a
    subj = subj or "what they were saying"
    t = None
    for p, o in ((a, b), (b, a)):
        t = contracts.thread({"with": o["id"], "subject": subj, "question": w["why"] or "there was more to say", "by": by["id"], "tick": h["tick"]})
        p["threads"] = [x for x in p.get("threads") or [] if x["with"] != o["id"]] + [t]
        memories.add(h, cfg, p, "I want to talk more with %s about %s: %s" % (label(o), subj, t["question"]) if p is by
                     else "%s wanted to talk more about %s: %s" % (label(by), subj, t["question"]), 3, about=(o["id"],), kind="thread")
    contracts.event53(h, "thread", a=a["id"], b=b["id"], subject=subj, picked=False)
    contracts.count(h, "threads", "left")
    return t


def picked(h, a, b, t):
    """The thread they took up (start gave it as the subject): off both."""
    for p in (a, b):
        p["threads"] = [x for x in p.get("threads") or [] if not (x["tick"] == t["tick"] and x["subject"] == t["subject"])]
    contracts.event53(h, "thread", a=a["id"], b=b["id"], subject=t["subject"], picked=True)
    contracts.count(h, "threads", "picked")


# ---- when and who ----

def free(eng, pet):
    """Awake, hatched, and not caught up in anything urgent."""
    m = eng.minds.get(pet["id"])
    return (pet["stage"] not in ("egg", "dead") and not pet["sleep"] and not pet.get("riding") and not pet.get("outcast")
            and not pet.get("shunned") and not pet.get("scuffle") and (pet.get("hurt") or {}).get("level") != "badly hurt" and m is not None
            and not (m.thought and {"low", "event"} & set(pet.get("news", [])))
            and (pet.get("talking") or {}).get("until", -1) < eng.house["tick"])


def budget(house, cfg):
    """At most `per_day` a hob a world day (with `want` on, only a safety net); half while the model is busy (§5, §8.3)."""
    from .life import model_busy
    T, busy = cfg["talk"], model_busy(house, cfg)
    return T["per_day"] if busy < T["busy_soft"] else max(1, T["per_day"] // 2) if busy < T["busy_hard"] else 1


def want(house, cfg, pet):
    """19 October 2026 (talk comes from a wish to talk that comes and goes): how much a hob wants company,
    0 to 1.5. It grows, as the square of the time, since its last real conversation (no snub; for a grown hob, not babble
    with a little one) over `want_hours`, sooner for a sociable hob and later for a solitary one. 1 with `want` off."""
    T = cfg["talk"]
    if not T.get("want", False):
        return 1.0
    grown = pet["stage"] not in LITTLE
    last = max((t["tick"] for t in house.get("talks", []) if pet["id"] in (t["a"], t["b"]) and "snub" not in t.get("came_of", [])
                and not (grown and any(house["pets"].get(x, {}).get("stage") in LITTLE for x in (t["a"], t["b"])))), default=-10 ** 9)
    return min(1.5, ((house["tick"] - last) / (hours(cfg, T["want_hours"]) * (1 - 0.5 * character.trait(pet, "social")))) ** 2)


def talked_today(house, cfg, pid):
    return sum(pid in (t["a"], t["b"]) for t in house.get("talks", []) if house["tick"] - t["tick"] < hours(cfg, 24)
               and "snub" not in t.get("came_of", []))   # (a snub is no conversation, and no model call: 19 October 2026)


def something_new(house, a, b, since):
    """Anything between them since they last talked: an opinion moved for a cause, a grievance went on."""
    ticks = [c["tick"] for x, y in ((a, b), (b, a)) for c in opinions.of(x, y["id"]).get("causes", [])]
    ticks += [e[0] for g in house.get("grievances", []) if {g["by"], g["against"]} == {a["id"], b["id"]} for e in g.get("history", [])]
    return max(ticks, default=-1) > since


def weight(house, a, b, cfg=None):
    """Kin and friends talk more; enemies rarely (§5)."""
    w = {"close": 3.0, "friend": 2.5, "rival": 1.0, "enemy": 0.3}.get(bonds.kind(house, a["id"], b["id"]), 1.0)
    if relation(house, a, b):
        w *= 2
    if not knows(a, b):
        w *= 0.5
    if min(opinions.of(a, b["id"])["liking"], opinions.of(b, a["id"])["liking"]) <= (cfg or {}).get("talk", {}).get("cold_below", -3):
        w = min(w, 0.3)   # (a real dislike: 19 October 2026, it was any liking below nothing, and most had slid just below)
    little = (a["stage"] in LITTLE) + (b["stage"] in LITTLE)   # (18 October 2026: most talks were babble, which changes nothing: grown pairs first)
    T = (cfg or {}).get("talk", {})
    w *= T.get("grown", 3.0) if not little else T.get("one_little", 0.3) if little == 1 else T.get("both_little", 0.1)
    return w * max(0.2, 1 + 0.5 * (character.trait(a, "social") + character.trait(b, "social")))


def pairs(eng):
    """[(weight, the one with more on its mind, the other)] for every pair that may talk now."""
    h, cfg = eng.house, eng.cfg
    most, last = budget(h, cfg), h.setdefault("talked", {})
    ok = [p for p in alive(h) if free(eng, p) and talked_today(h, cfg, p["id"]) < most]
    out = []
    for i, a in enumerate(ok):
        for b in ok[i + 1:]:
            if a["room"] != b["room"]:
                continue
            key = "|".join(sorted((a["id"], b["id"])))
            if key in last and h["tick"] - last[key] < hours(cfg, cfg["talk"]["again_hours"]) and not something_new(h, a, b, last[key]):
                continue
            ma, mb = on_mind(h, cfg, a, b), on_mind(h, cfg, b, a)
            if ma or mb:
                out.append((weight(h, a, b, cfg) * (want(h, cfg, a) + want(h, cfg, b)) / 2,) + ((a, b) if len(ma) >= len(mb) else (b, a)))
    return out


def tick(eng):
    """Take in conversations that have come back; keep promises; end a gathering; now and then start a conversation."""
    from . import drives
    drives.tick(eng)   # (SPEC-v4.2 §6: voice cards, secrets and drives, with [drives] on, whether or not hobs talk)
    if not on(eng.cfg):
        return
    h, cfg = eng.house, eng.cfg
    inflight = eng.__dict__.setdefault("talking", [])
    for t in list(inflight):
        if t["fut"].done():
            inflight.remove(t)
            rec = None
            try:
                rec = apply(eng, t, t["fut"].result())
            except Exception:
                logging.exception("a conversation could not be taken in")
            for x, y in ((t["a"], t["b"]), (t["b"], t["a"])) + (((t["third"], t["a"]),) if t.get("third") else ()):   # (taken in or not, they are free again: 19 October 2026, they were held till `until`)
                p = h["pets"].get(x)
                if p and (p.get("talking") or {}).get("with") == y:   # (SPEC-v5.3 §5.1: a round costs each a quarter-hour of its day, held talking till then)
                    p["talking"] = {"with": y, "until": t["tick"] + hours(cfg, cfg["talk3"]["round_hours"]) * len(rec["rounds"])} if rec and rec.get("rounds") else None
    keep_promises(h, cfg)
    gathering_tick(h, cfg)
    if three(cfg) and h["tick"] % hours(cfg, 1) == 0:   # SPEC-v5.3 §5.2: a thread not picked up within thread_days is let go
        for p in alive(h):
            if p.get("threads"):
                p["threads"] = [x for x in p["threads"] if h["tick"] - x["tick"] <= hours(cfg, 24 * cfg["talk3"]["thread_days"])]
    if h["tick"] % hours(cfg, cfg["talk"]["every_minutes"] / 60) or inflight:
        return   # (one conversation in flight at a time: the model is shared)
    r = rnd(h, "talk", h["tick"])
    for w, a, b in sorted(pairs(eng), key=lambda x: -x[0] * r.random()):
        if r.random() < min(1.0, w * cfg["talk"]["chance"]):
            return start(eng, a, b, r)
    seek_company(eng, r)


def seek_company(eng, r):
    """18 October 2026 (15 talks in two world days on live, most with babbling little ones): a grown hob with talks left today and
    something on its mind about another grown hob elsewhere goes to find it (the planner's `seek`), once a world hour at most."""
    h, cfg = eng.house, eng.cfg
    most = budget(h, cfg)
    grown = [p for p in alive(h) if p["stage"] not in LITTLE and free(eng, p) and talked_today(h, cfg, p["id"]) < most]
    for p in grown:
        if h["tick"] - p.get("talk_seek", -10 ** 9) < hours(cfg, 1) or p.get("seek") or want(h, cfg, p) < 0.7:
            continue
        far = [(weight(h, p, o, cfg), o) for o in grown if o is not p and o["room"] != p["room"] and on_mind(h, cfg, p, o)]
        if far:
            w, o = max(far, key=lambda x: (x[0] * r.random(), x[1]["id"]))
            if w >= 1.0:
                p["seek"], p["talk_seek"] = [o["id"]], h["tick"]


# ---- the call ----

def start(eng, a, b, r):
    h, cfg = eng.house, eng.cfg
    h.setdefault("talked", {})["|".join(sorted((a["id"], b["id"])))] = h["tick"]
    if opinions.of(b, a["id"])["liking"] <= cfg["talk"]["snub_below"] and (character.trait(b, "kind") < 0 or r.random() < 0.5) and b["stage"] not in LITTLE:
        return snub(h, cfg, a, b)
    deep, more = two(cfg), three(cfg)   # SPEC-v4.2 §7; SPEC-v5.3 §5
    third = pick_third(eng, a, b, r) if more else None   # §5.4 a listener
    thread_ = thread_of(h, cfg, a, b) if more else None   # §5.2 what they left open is the subject
    subj = thread_["subject"] if thread_ else subject(h, cfg, a, b, r, third) if deep else ""
    if more:
        h.setdefault("subjects53", {})[pair_key(a, b)] = subj   # §5.5 not again till another has been
    packet = packet2(h, cfg, a, b, subj, third, thread_) if deep else packet_of(h, cfg, a, b)
    shape, brain, think, most, warm = schema2(h, cfg, a, b, third) if deep else schema(h, a, b), eng.minds[a["id"]].brain, *contracts.thinking(cfg, "talk")
    if getattr(brain, "instant", False):
        async def ask(think, text=packet, n=1):
            r_ = rnd(h, "stub talk", h["tick"], a["id"], *([n] if n > 1 else []))
            return stub_round(h, cfg, a, b, r_, subj, n, third) if more else stub_reply2(h, cfg, a, b, r_, subj) if deep else stub_reply(h, cfg, a, b, r_)
    else:
        from .brains.model import parse

        async def ask(think, text=packet, n=1):   # (chat asks again once if the reply wanders into another script; a reply that isn't JSON comes back as words, to be said)
            raw = await asyncio.to_thread(brain.chat, text, shape, think, most, warm, "talk")   # (SPEC-v4.2 §3.1: thinking on; off, v4.0.6's: none, max_tokens, 0.8)
            return parse(raw) or "invalid json: %s" % str(raw)[:120]

    async def fn():
        out = await ask(think)
        if deep and lacks(out, names(a, b)):   # SPEC-v4.2 §7.5: without wants, holds and knows it failed; asked once more, thinking
            failed(h, a["id"], b["id"], out, "without wants, holds and knows")
            out = await ask(think or "low")
        if deep and isinstance(out, dict) and isinstance(out.get("lines"), list):   # SPEC-v4.2.2 §6
            n = monologue(out["lines"], a, b)
            if n >= 2:   # (one pair that doesn't answer is let through; two, and it is asked once more, reminded)
                contracts.note(h, "monologue", a=a["id"], b=b["id"], pairs=n)
                again = await ask(think, packet + "\n\n" + AGAIN)
                out = again if isinstance(again, dict) and isinstance(again.get("lines"), list) and not lacks(again, names(a, b)) else out
            why = purple(out["lines"])
            if why:
                contracts.note(h, "purple", a=a["id"], b=b["id"], why=why)
        if more and isinstance(out, dict) and isinstance(out.get("lines"), list):   # SPEC-v5.3 §5.1: another round while both say yes
            rs, g = [out], go_on(h, cfg, out, a, b)
            while len(rs) < cfg["talk3"]["rounds"] and all(x["go_on"] == "yes" for x in g.values()):
                for p in (a, b, third):
                    if p and p.get("talking"):
                        p["talking"]["until"] += hours(cfg, cfg["talk3"]["round_hours"])
                nxt = await ask(think, packet + onward(h, cfg, a, b, third, rs, g), len(rs) + 1)
                if lacks(nxt, names(a, b)) or not isinstance(nxt.get("lines"), list):
                    break
                rs.append(nxt)
                g = go_on(h, cfg, nxt, a, b)
            out = dict(out, rounds53=rs[1:])
        return out
    from . import brain4
    until = h["tick"] + hours(cfg, cfg["talk3"]["round_hours"] if more else 0.25)
    a["talking"], b["talking"] = {"with": b["id"], "until": until}, {"with": a["id"], "until": until}   # (the body may hold them together meanwhile)
    if third:
        third["talking"] = {"with": a["id"], "until": until}
    fut = eng.call(brain4.PRIORITY["talk"], a["id"], "talk", "%s and %s" % (label(a), label(b)), fn, len(packet))
    eng.talking.append(dict({"fut": fut, "a": a["id"], "b": b["id"], "room": a["room"], "schema": shape, "tick": h["tick"]}, **({"subject": subj} if deep else {}),
                            **({"third": third["id"] if third else None, "third_name": names3(a, b, third)[2] if third else None, "thread": thread_} if more else {})))
    return fut


def onward(h, cfg, a, b, third, rs, g):
    """§5.1 the next round's ask: the lines so far, what each now knows of the other, why both go on."""
    ns, hi, said, k = names3(a, b, third), cfg["talk2"]["lines"][1], [], 0
    for x in rs:
        for s in x["lines"][:hi]:
            said.append("  %s: %s" % (ns[k % 2], unnamed(s, (a, b))))
            k += 1
        if third and isinstance(x.get("third_line"), str) and x["third_line"].strip():
            said.append("  %s: %s" % (ns[2], x["third_line"].strip()))
    m = rs[-1].get("minds") if isinstance(rs[-1].get("minds"), dict) else {}
    knows = ["%s: %s" % (n, m[n]["knows"]) for n in ns if isinstance(m.get(n), dict) and m[n].get("knows")]
    lo, _ = cfg["talk2"]["lines"]
    return ("\n\nSo far they have said:\n%s\n%sBoth want to go on (%s). Write the next %d lines or so, %s first, carrying on from the last line: "
            "new things, not the same again. Then minds, came_of and after as before, and go_on again."
            % ("\n".join(said), "What each now knows: %s.\n" % "; ".join(knows) if knows else "", "; ".join("%s: %s" % (n, g[n]["why"] or "yes") for n in ns[:2]),
               lo, ns[k % 2]))


def monologue(lines, a, b):
    """SPEC-v4.2.2 §6: how many lines don't answer the line before: no word of four letters or more in common with it,
    and no "you", "your" or the other's name. A hatchling's lines, and the lines answering them, are babble: not counted."""
    words = lambda t: {w.lower() for w in re.findall(r"[A-Za-z]{4,}", t)}
    n = 0
    for i in range(1, len(lines)):
        was, now = (a, b)[(i - 1) % 2], (a, b)[i % 2]
        if "hatchling" in (was["stage"], now["stage"]) or not isinstance(lines[i], str) or not isinstance(lines[i - 1], str):
            continue
        prev, cur = unnamed(lines[i - 1], (a, b)), unnamed(lines[i], (a, b))
        if not words(prev) & words(cur) and not re.search(r"\byours?\b|\byou\b", cur, re.I) and label(was).lower() not in cur.lower():
            n += 1
    return n


def purple(lines):
    """SPEC-v4.2.2 §6: why a talk reads like a novel ("the hour", "the ache", "the shape of", more than one line over 200
    characters), or ""."""
    text = " ".join(x for x in lines if isinstance(x, str)).lower()
    said = [p for p in PURPLE if p in text]
    if sum(len(x) > 200 for x in lines if isinstance(x, str)) > 1:
        said.append("long lines")
    return ", ".join(said)


def lacks(reply, names_):
    """SPEC-v4.2 §7.5: a reply without every speaker's wants, holds and knows (or no reply at all)."""
    return not isinstance(reply, dict) or bool(contracts.defaults("talk", dict(reply), names_)[1])


def failed(h, a, b, reply, why="out of shape"):
    """A conversation that came back out of shape: said, with what came back, and counted where the Lab reads it."""
    said = (reply if isinstance(reply, str) else json.dumps(reply))[:120]
    h["talks_failed"] = h.get("talks_failed", 0) + 1
    h["failed_talks"] = (h.get("failed_talks", []) + [{"tick": h["tick"], "pets": [a, b], "reply": said}])[-100:]
    logging.warning("talks_failed: %s and %s, kind talk, %s: %s", a, b, why, said)


def packet_of(house, cfg, a, b):
    """Both hobs in words (§5 "The call is given"); never a number. Each hob's memories (3) and what is on its mind (6) are
    trimmed first; if it is still over `packet_most`, the memories go, then what is on their minds, then the house's news.
    The instructions are never cut (19 October 2026: the packet was cut from its end, and the JSON shape with it)."""
    room = house["rooms"][a["room"]]
    others = [label(p) for p in here(house, a, awake=True) if p["id"] != b["id"]]

    def who(p, o, mems, minds):
        rel = relation(house, p, o)
        lines = ["%s (%s%s):" % (label(p) if key[p["id"]] == label(p) else "%s [%s]" % (label(p), p["id"]), p["stage"], "" if family(p) == family(o) else ", of another family")]
        if rel:
            lines.append("- %s is its %s" % (label(o), rel))
        if character.on(cfg):   # (19 October 2026: with [traits] off they were still sent)
            lines.append("- character: %s" % character.words(p))
            if p.get("values"):
                lines.append("- cares most about: %s" % ", ".join(p["values"]))
            if p.get("quirks"):
                lines.append("- quirks: %s" % ", ".join(p["quirks"]))
        lines.append("- mood: %s" % character.mood(p))
        lines.append("- feels: %s" % "; ".join(needs.feel(p) or [feel.feelings(p)]))
        lines.append("- of %s: it %s" % (label(o), regard(opinions.of(p, o["id"]), label(o))))
        mem = [m["text"] for m in memories.relevant(house, cfg, p, about=(o["id"],), n=mems)]
        if mem:
            lines.append("- remembers: " + " | ".join(short(m, 30, 200) for m in mem))
        mind = on_mind(house, cfg, p, o)[:minds]
        if mind:
            lines.append("- on its mind: " + "; ".join(short(x, 25, 160) for x in mind))
        lines.append("- voice: " + voice(p))
        return "\n".join(lines)

    key = dict(zip((a["id"], b["id"]), names(a, b)))
    occ = occasion(house, cfg)
    ask = ("Write their conversation: two to six short lines taking turns, %s first, each under twenty words, each in the speaker's own "
           "voice as described (a little one babbles). Say what came of it (by whom, and about whom if it is gossip), and how each "
           "feels after: a mood, and whether it feels warmer, the same or cooler toward the other. Only what fits who they are.\n"
           'Reply with one JSON object and nothing else: {"lines": [...], "came_of": [{"what", "by", "about", "detail"}], '
           '"after": {"%s": {"mood", "toward"}, "%s": {...}}, "ask_visitor": {"who", "q"} (a question one of them wants to put '
           'to the visitor, the owner of their world; leave both empty for none)}' % (key[a["id"]], key[a["id"]], key[b["id"]]))
    most = cfg["talk"]["packet_most"] - len(ask)
    for mems, minds, news in ((3, 6, True), (0, 6, True), (0, 0, True), (0, 0, False)):
        text = ("Two hobs, small household spirits, meet in %s (%s), %s. Around them: %s.%s\n\n%s\n\n%s\n\n%s"
                % (room["name"], room.get("feel", "")[:120], house["clock"]["phase"], ", ".join(list(room["objects"])[:8]) or "nothing much",
                   " Also here: %s." % ", ".join(others) if others else "", who(a, b, mems, minds), who(b, a, mems, minds),
                   "Lately in the house: %s.\n" % occ[1]["text"] if occ and news else ""))
        if len(text) <= most:
            break
    return text[:most] + ask


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def text(most, least=1):
    return {"type": "string", "minLength": least, "maxLength": most}


def names(a, b):
    """What the reply calls the two: their names, or their ids when they share one (19 October 2026: two hobs with one
    label gave the reply's "after" a single key, and the talk could not be taken in)."""
    return [label(a), label(b)] if label(a) != label(b) else [a["id"], b["id"]]


def schema(house, a, b):
    """The constrained reply (§5 "It returns")."""
    names_ = names(a, b)
    about = [label(p) for p in alive(house) if p["stage"] != "egg" and p["id"] not in (a["id"], b["id"])] + ["the visitor", ""]
    after = obj(mood={"enum": list(MOODS)}, toward={"enum": ["warmer", "same", "cooler"]})
    return obj(lines={"type": "array", "items": text(140), "minItems": 2, "maxItems": 6},
               came_of={"type": "array", "minItems": 1, "maxItems": 3,
                        "items": obj(what={"enum": list(CAME)}, by={"enum": names_}, about={"enum": about}, detail=text(100, 0))},
               after=obj(**{n: after for n in names_}),
               ask_visitor=obj(who={"enum": names_ + [""]}, q=text(100, 0)))


def valid(x, s):
    """Does `x` keep to the JSON schema `s` (the parts of it these schemas use)? A reply that does not is dropped."""
    if "anyOf" in s:
        return any(valid(x, o) for o in s["anyOf"])
    if ("const" in s and x != s["const"]) or ("enum" in s and x not in s["enum"]):
        return False
    t = s.get("type")
    if t == "object":
        P = s.get("properties", {})
        return isinstance(x, dict) and all(k in x for k in s.get("required", [])) and not (s.get("additionalProperties") is False and set(x) - set(P)) \
            and all(valid(v, P[k]) for k, v in x.items() if k in P)
    if t == "array":
        return isinstance(x, list) and s.get("minItems", 0) <= len(x) <= s.get("maxItems", 10**9) and all(valid(i, s["items"]) for i in x)
    if t == "string":
        return isinstance(x, str) and s.get("minLength", 0) <= len(x) <= s.get("maxLength", 10**9)
    if t == "integer":
        return isinstance(x, int) and not isinstance(x, bool)
    return True


# ---- SPEC-v4.2 §7: talk with subtext ([talk2]) ----

def topic(house, m):
    """SPEC-v4.2.2 §4: a memory as a topic, never its words: "what Antonia said about the train", "the hinge", or ""."""
    who = next((label(house["pets"][x]) for x in m.get("about") or [] if x in house["pets"]), "the visitor" if "visitor" in (m.get("about") or []) else "")
    thing = (m.get("what") or [""])[0]
    if who and m.get("kind") in ("talk", "knows", "subtext"):
        return "what %s said%s" % (who, " about the %s" % thing if thing else "")
    return "the %s%s" % (thing, " and %s" % who if who else "") if thing else "something to do with %s" % who if who else ""


def subject(house, cfg, a, b, r, third=None):
    """§7.3 what the engine gives both sides to start from, or "" (then whatever comes up). SPEC-v4.2.2 §4: in plain
    words, from the happening's line in stage.toml or the fact; never the director's why, never a memory's words.
    SPEC-v5.3 §5.5 ([talk3]): and from habits, projects, threads and perceptions (SUBJECT53, a listener's too), never
    the one the two had last time, until another has been."""
    from .stage import MENU
    day, out = hours(cfg, 24), []
    mem = memories.shared(house, cfg, a, b, 1)
    if mem and topic(house, mem[0]):
        out.append(topic(house, mem[0]))
    hap = contracts.happening(house["happening"]) if isinstance(house.get("happening"), dict) else None
    if hap and hap["name"] != "nothing" and hap["day"] == house["clock"]["day"]:
        tp = house["pets"].get(hap["target"] or "")
        out.append(MENU[hap["name"]]["subject"].replace("{who}", label(tp) if tp else "one of them"))
    m = next((m for m in reversed(house["moments"]) if m["kind"] == "death" and house["tick"] - m["tick"] <= day * 2 and m.get("pet") in house["pets"]), None)
    if m:
        out.append("%s died %s" % (label(house["pets"][m["pet"]]), feel.ago(house, cfg, m["tick"])))
    m = next((m for m in reversed(house["moments"]) if m["kind"] == "first" and house["tick"] - m["tick"] <= day), None)
    if m:
        out.append(m["text"])
    if house.get("visitor_last") is not None and house["tick"] - house["visitor_last"] <= day:
        out.append("the visitor came by %s" % feel.ago(house, cfg, house["visitor_last"]))
    for p, o in ((a, b), (b, a)):
        theirs = {x["text"] for x in o.get("hooked") or []}
        mine = next((x["text"] for x in p.get("hooked") or [] if x["text"] not in theirs), None)
        if mine:
            out.append("%s says %s, and %s doesn't believe it" % (label(p), mine[:1].lower() + mine[1:].rstrip("."), label(o)))
            break
    tales = house.get("tales") or []
    for e in (p for p in (a, b) if p["stage"] == "elder"):   # (D's tales, once there are any)
        known = [contracts.tale(t) for t in (tales.values() if isinstance(tales, dict) else tales) if isinstance(t, dict) and (t.get("family") == family(e) or e["id"] in t.get("told", []))]
        if known:
            t = r.choice(known)
            out.append("how %s %s" % (t["name"], t["words"]))
            break
    from . import book, knowledge   # SPEC-v5.1 §6.1, §5.4 (helper B): what one read today; what one knows how to make and the other doesn't
    for p in (a, b):
        got = (p.get("read") or [None])[0]
        if book.on(cfg) and got and got.get("title") and house["tick"] - got["tick"] <= day:
            out.append("what %s read today, about %s" % (label(p), got["title"].lower()))
    for p, o in ((a, b), (b, a)):
        key = knowledge.gap(house, cfg, p, o)
        if key:
            out.append("%s knows %s, and %s doesn't" % (label(p), knowledge.words_of(cfg, key), label(o)))
            break
    if three(cfg):
        for k in contracts.SUBJECTS53:
            out += SUBJECT53[k](house, cfg, a, b, third)
        last = (house.get("subjects53") or {}).get(pair_key(a, b))
        out = [x for x in dict.fromkeys(out) if x and x != last]
    return r.choice(out) if out else ""


def packet2(house, cfg, a, b, subj, third=None, thread=None):
    """§7: both hobs in words, deeper: how each sees itself, its drive and flaw, its traits, how it talks, what it already
    knows of the other, what is on its mind and its beliefs, what it keeps to itself; then SPEC-v4.2.2 §1's prompt with
    the subject, and the reply's shape. Each hob's memories, then what is on its mind are trimmed first; never the ask."""
    from . import brain4, drives
    from . import self as self_page
    room, L = house["rooms"][a["room"]], cfg["talk2"]
    others = [label(p) for p in here(house, a, awake=True) if p["id"] != b["id"]]
    key = dict(zip((a["id"], b["id"]), names(a, b)))
    _, _, what = memories.tag(house, subj, cfg)

    def who(p, o, mems, minds):
        rel, O = relation(house, p, o), label(o)
        lines = ["%s (%s%s):" % (label(p) if key[p["id"]] == label(p) else "%s [%s]" % (label(p), p["id"]), p["stage"], "" if family(p) == family(o) else ", of another family")]
        if rel:
            lines.append("- %s is its %s" % (O, rel))
        if self_page.on(cfg):
            page = self_page.page(house, cfg, p)
            lines.append("- how it sees itself: %s; %s" % (page["who I am"], page["what I am for"]))
        if p.get("drive") or p.get("flaw"):
            lines.append("- " + drives.line(p).replace("your ", "its ").replace("what you want", "what it wants").replace("what you've done", "what it's done"))
        if character.on(cfg) and brain4.traits_line(p):   # §6.5: the two strongest and the weakest
            lines.append("- character: " + brain4.traits_line(p).replace("you are ", "", 1))
        lines.append("- mood: %s" % character.mood(p))
        lines.append("- feels: %s" % "; ".join(needs.feel(p) or [feel.feelings(p)]))
        lines.append("- of %s: it %s" % (O, regard(opinions.of(p, o["id"]), O)))
        knew = [m["text"] for m in p.get("memories") or [] if m.get("kind") == "knows" and o["id"] in m.get("about", [])][-3:]
        if knew:
            lines.append("- what it already knows of %s: %s" % (O, " | ".join(knew)))
        mem = [m["text"] for m in memories.relevant(house, cfg, p, about=(o["id"],), what=what, n=mems + len(knew)) if m["text"] not in knew][-mems:] if mems else []
        if mem:
            lines.append("- remembers: " + " | ".join(short(m, 30, 200) for m in mem))
        mind = on_mind(house, cfg, p, o)[:minds]
        if mind:
            lines.append("- on its mind: " + "; ".join(short(x, 25, 160) for x in mind))
        s = p.get("secret")
        if s and not s.get("found"):
            lines.append("- a secret it won't tell: %s" % s["text"])
        if p["stage"] == "hatchling":
            lines.append("- talks: only babbles%s" % (" (words it has learned: %s)" % ", ".join(p["learned_words"]) if p.get("learned_words") else ""))
        elif p["stage"] == "child":
            lines.append("- talks: like a child, in short plain sentences, and asks a lot")
        elif p.get("voice"):
            lines.append("- talks: " + contracts.voice_line(p["voice"]))
        else:
            lines.append("- talks: " + voice(p))
        return "\n".join(lines)

    lo, hi = L["lines"]
    n = rnd(house, "talk lines", house["tick"], a["id"]).randint(lo, hi)
    A, B = key[a["id"]], key[b["id"]]
    ask = (TALK.replace("<N>", str(n)).replace("<subject, in plain words>", subj or "nothing in particular; whatever comes up").replace("<A>", A).replace("<B>", B)
           + '\n\nReply with one JSON object and nothing else: {"minds": {"%s": {"wants", "holds", "knows", "remember"}, "%s": {...}}, "lines": [...] (%s first), '
           '"came_of": [{"what", "by", "about", "detail"}], "after": {"%s": {"mood", "toward"}, "%s": {...}}, "ask_visitor": {"who", "q"} (a question '
           'one of them wants to put to the visitor, the owner of their world; leave both empty for none)}' % (A, B, A, A, B))
    if three(cfg):   # SPEC-v5.3 §5: TALK53's longer lines; a listener with a line a round; the thread picked up; go_on after the lines
        C = names3(a, b, third)[2] if third else None
        ask = (TALK53.replace("<N>", str(n)).replace("<subject, in plain words>", subj or "nothing in particular; whatever comes up").replace("<A>", A).replace("<B>", B)
               + ("\n\n%s is in the room too, listening (%s; it %s, and it %s). %s puts in one line of its own (third_line), and is in the minds too."
                  % (C, third["stage"], regard(opinions.of(third, a["id"]), label(a)), regard(opinions.of(third, b["id"]), label(b)), C) if third else "")
               + ("\n\nLast time they talked they left this open: %s wanted to go on (%s). They pick it up now."
                  % (label(house["pets"][thread["by"]]) if thread["by"] in house["pets"] else "one of them", thread["question"]) if thread else "")
               + '\n\nReply with one JSON object and nothing else: {"minds": {"%s": {"wants", "holds", "knows", "remember"}, "%s": {...}%s}, "lines": [...] (%s first), '
               '"came_of": [{"what", "by", "about", "detail"}], "after": {"%s": {"mood", "toward"}, "%s": {...}}, "ask_visitor": {"who", "q"} (a question '
               'one of them wants to put to the visitor, the owner of their world; leave both empty for none), "go_on": {"%s": {"go_on": "yes" or "no", "why"}, "%s": {...}} '
               '(after the lines: whether each wants to keep talking, and why)%s}' % (A, B, ', "%s": {...}' % C if third else "", A, A, B, A, B,
                                                                                    ', "third_line": "<what %s says>"' % C if third else ""))
    most = cfg["talk"]["packet_most"] - len(ask)
    for mems, minds in ((3, 6), (1, 4), (0, 2), (0, 0)):
        text = ("Two hobs meet in %s%s, %s. Around them: %s.%s\n\n%s\n\n%s\n\n"
                % (room["name"], " (%s)" % room["feel"][:120] if room.get("feel") else "", house["clock"]["phase"], ", ".join(list(room["objects"])[:8]) or "nothing much",
                   " Also here: %s." % ", ".join(others) if others else "", who(a, b, mems, minds), who(b, a, mems, minds)))
        if len(text) <= most:
            break
    return text[:most] + ask


def schema2(house, cfg, a, b, third=None):
    """§7.1-7.2 the reply: each speaker's minds first (contracts.talk_fields), then four to eight longer lines.
    SPEC-v5.3 §5.1, §5.4 ([talk3]): after them each speaker's go_on (contracts.talk_round_fields), and a listener's minds
    and its one line."""
    s = contracts.add_fields(schema(house, a, b), contracts.talk_fields(names3(a, b, third) if three(cfg) else names(a, b)))
    if three(cfg):
        contracts.add_fields(s, contracts.talk_round_fields(names(a, b)))
        if third:
            contracts.add_fields(s, {"third_line": text(cfg["talk2"]["line_chars"])})
    lo, hi = cfg["talk2"]["lines"]
    s["properties"]["lines"] = {"type": "array", "items": text(cfg["talk2"]["line_chars"]), "minItems": lo, "maxItems": hi}
    s["properties"] = {"minds": s["properties"].pop("minds"), **s["properties"]}   # (the subtext before the lines: it is thought first)
    return s


STOP = {"that", "this", "with", "what", "have", "your", "will", "there", "they", "them", "then", "when", "been", "were", "from", "just",
        "like", "about", "would", "could", "into", "some", "here", "know", "yours", "very", "much", "more", "said", "does", "dont", "isnt"}


def learn(h, cfg, a, b, lines, did, r):
    """§7.6: a hatchling learns a word a day from whoever talks to it; its babble has it now and then."""
    for p, o in ((a, b), (b, a)):
        if p["stage"] != "hatchling" or o["stage"] == "hatchling" or p.get("word_day") == h["clock"]["day"]:
            continue
        heard = sorted({w.lower() for x in lines if x["who"] == o["id"] for w in re.findall(r"[A-Za-z]{4,9}", x["text"])} - STOP - set(p.get("learned_words", [])))
        if heard:
            w = r.choice(heard)
            p["learned_words"], p["word_day"] = (p.get("learned_words", []) + [w])[-12:], h["clock"]["day"]
            did.append('%s learned a word from %s: "%s"' % (label(p), label(o), w))


# ---- what the engine makes of it ----

def aim(house, pet, text_, why, kind, target):
    """An aim the body works on (PLAN.md: pet["aims"]); the oldest finished ones go first."""
    aims = pet.setdefault("aims", [])
    if any(x["kind"] == kind and x["target"] == target and not x.get("done") for x in aims):
        return   # (it is at that already)
    aims.append({"text": short(text_, 20, 120), "why": short(why, 20, 120), "kind": kind, "target": target, "since": house["tick"], "done": None})
    while len(aims) > 8:
        aims.remove(next((x for x in aims if x.get("done")), aims[0]))


def grudge(house, cfg, by, against, why):
    """A reason one holds against another (helper C's ladder climbs from these)."""
    from . import conflict
    return conflict.grudge(house, cfg, by["id"], against["id"], why)


def apply(eng, t, reply):
    """Take a conversation in (§5 "The engine decides the effects")."""
    h, cfg = eng.house, eng.cfg
    a, b = h["pets"].get(t["a"]), h["pets"].get(t["b"])
    if not a or not b or "dead" in (a["stage"], b["stage"]):
        return None
    la, lb = list(t["schema"]["properties"]["after"]["properties"])   # (their names when it was asked: one may have taken a name since)
    deep, shape, minds = "minds" in t["schema"]["properties"], t["schema"], None   # (SPEC-v4.2 §7: asked with subtext)
    more = "go_on" in t["schema"]["properties"]   # SPEC-v5.3 §5: asked in rounds
    third = h["pets"].get(t.get("third") or "") if more else None
    third = third if third and third["stage"] not in ("egg", "dead") else None
    ns = [la, lb] + ([t["third_name"]] if more and t.get("third") else [])
    extra = reply.pop("rounds53", []) if more and isinstance(reply, dict) else []
    sides = [{k: reply.pop(k, None) for k in ("go_on", "third_line")}] if more and isinstance(reply, dict) else [{}]   # (read apart: a round's go_on out of shape is a no, not a failed talk)
    if deep and isinstance(reply, dict):   # (the minds defaulted where they are missing, and counted: the talk goes on, §0.1 item 5)
        reply, miss = contracts.defaults("talk", reply, ns)
        minds, shape = reply.pop("minds"), dict(shape, required=[k for k in shape["required"] if k not in ("minds", "go_on", "third_line")])
        if miss:
            contracts.note(h, "missed", pet=a["id"], kind="talk", fields=miss)
    if not isinstance(reply, dict) or not valid(reply, shape):   # (19 October 2026: said, with what came back, and counted where the Lab reads it)
        failed(h, t["a"], t["b"], reply)
        return None
    rounds, later = [reply], []   # SPEC-v5.3 §5.1: the rounds past the first, each in shape (a round out of shape ends the talk there)
    for x in extra:
        if not isinstance(x, dict):
            break
        side = {k: x.pop(k, None) for k in ("go_on", "third_line")}
        x, _ = contracts.defaults("talk", x, ns)
        m = x.pop("minds")
        if not valid(x, shape):
            break
        rounds.append(x)
        later.append(m)
        sides.append(side)
    r = rnd(h, "talk apply", h["tick"], a["id"])
    by_name = {la: a, lb: b}
    lines, parts, k = [], [], 0
    for x, side in zip(rounds, sides):
        part = []
        for s in x["lines"][:cfg["talk2"]["lines"][1] if deep else 6]:
            p = (a, b)[k % 2]   # (they take turns, the first speaker first, whatever the reply says; on from round to round)
            k += 1
            s = unnamed(s, (a, b))   # (18 October 2026, the first talks on live: "Bogna: Bogna: Align the melon leaves...")
            if deep:   # SPEC-v4.2 §7.1: babble only for a hatchling, a child's short plain sentences, longer lines for the grown
                said = babble(s, "hatchling", r, p.get("learned_words")) if p["stage"] == "hatchling" else short(s, 24, 160) if p["stage"] in LITTLE \
                    else re.sub(r"\s+", " ", s).strip()[:cfg["talk2"]["line_chars"]]
                part.append({"who": p["id"], "text": said})
                continue
            part.append({"who": p["id"], "text": babble(s, p["stage"], r) if p["stage"] in LITTLE else short(s)})
        if third and isinstance(side.get("third_line"), str) and side["third_line"].strip():   # §5.4 the listener's one line a round
            s = unnamed(side["third_line"], (a, b, third))
            part.append({"who": third["id"], "text": short(s, 24, 160) if third["stage"] in LITTLE else re.sub(r"\s+", " ", s).strip()[:cfg["talk2"]["line_chars"]]})
            contracts.event53(h, "third", pet=third["id"], a=a["id"], b=b["id"])
            contracts.count(h, "third", third["id"])
        parts.append(part)
        lines += part
    did, moved = [], set()

    def move(pet, other, cause, why):   # (the talk's own memory says it all: none for each cause)
        opinions.move(h, cfg, pet, other["id"], cause, why, remember=False)
        moved.add((pet["id"], other["id"]))

    came, cs = [], list(reply["came_of"])
    for x in rounds[1:]:   # (SPEC-v5.3: a later round's outcomes, each kind once)
        cs += [c for c in x["came_of"] if c["what"] not in {y["what"] for y in cs}]
    babes = a["stage"] in LITTLE and b["stage"] in LITTLE   # (two little ones babbling to each other: nothing comes of it but a mood)
    for c in ([] if babes else cs):
        doer = by_name.get(c["by"], a)
        other = b if doer is a else a
        about = c["about"] if c["about"] in ("", "the visitor") else next((p for p in alive(h) if label(p) == c["about"]), None)
        if doer["stage"] in LITTLE and c["what"] not in ("news", "nothing", "help asked", "making up", "apology", "argument"):
            continue   # (a little one's babble promises, teaches and threatens nothing)
        what = effect(h, cfg, c["what"], doer, other, about, short(c["detail"], 16, 100), reply, move, did, moved, r)
        if what and what not in came:
            came.append(what)
    if babes:
        came = ["nothing"]
    after = {}
    for p, o in ((a, b), (b, a)):
        f = rounds[-1]["after"][la if p is a else lb]   # (how each feels after the last round)
        if f["mood"] != character.mood(p):
            character.set_mood(h, cfg, p, f["mood"], "talking with %s" % label(o))
        d = {"warmer": 1, "same": 0, "cooler": -1}[f["toward"]]
        if d and not babes and (p["id"], o["id"]) not in moved:   # (one move for the talk itself, and none on top of a cause it already gave)
            move(p, o, "talked_kindly" if d > 0 else "talked_harshly", "talked with %s" % label(o))
        after[p["id"]] = {"mood": f["mood"], "liking": d}
    from . import drives
    for lie in [x for x in h.get("lies", []) if {x["listener"], x["about"]} == {a["id"], b["id"]}]:   # §4: talking with the one it was lied to about
        if r.random() < cfg["talk"]["lie_found"]:
            opinions.found_out(h, cfg, lie)
            did.append("%s found out %s had lied about %s" % (label(h["pets"][lie["listener"]]), label(h["pets"][lie["teller"]]) if lie["teller"] in h["pets"] else "someone",
                                                               label(h["pets"][lie["about"]])))
            teller = h["pets"].get(lie["teller"])
            if teller and (teller.get("secret") or {}).get("kind") == "lie" and teller["secret"].get("about") == lie["listener"]:
                drives.found(h, cfg, teller, h["pets"][lie["listener"]])   # (SPEC-v4.2 §6.3: and with it the teller's secret)
    if drives.on(cfg):   # SPEC-v4.2 §6.3: the lie mechanism, for every secret: likelier with the one it is about
        for p, o in ((a, b), (b, a)):
            s = p.get("secret")
            if s and not s.get("found") and o["stage"] not in LITTLE and r.random() < cfg["talk"]["lie_found"] * drives.FOUND[s.get("about") != o["id"]]:
                drives.found(h, cfg, p, o)
                did.append("%s found out what %s kept to itself" % (label(o), label(p)))
    from . import visitor
    ask = reply["ask_visitor"]
    if visitor.on(cfg):
        visitor.spread(h, cfg, a, b, r)   # §10.1: belief in the visitor, passed on or doubted in talk
        if ask["who"] and ask["q"].strip():
            visitor.ask(h, cfg, by_name[ask["who"]], short(ask["q"], 20, 100), "question")
    came = came or ["nothing"]
    h["n"]["talk"] = h["n"].get("talk", 0) + 1
    rec = {"n": h["n"]["talk"], "tick": h["tick"], "room": t["room"], "a": a["id"], "b": b["id"], "lines": lines, "came_of": came, "after": after, "did": did}
    if deep:   # SPEC-v4.2 §7.2-7.4: the subject and what was on each mind; a secret is always in what it holds
        for nm, p in ((la, a), (lb, b)):
            s = p.get("secret")
            if s and not s.get("found") and s["text"] not in minds[nm]["holds"]:
                minds[nm]["holds"] = "; ".join(x for x in (s["text"], minds[nm]["holds"]) if x)[:200]
        rec.update(subject=t.get("subject", ""), minds=minds)
        learn(h, cfg, a, b, lines, did, r)
    if more:   # SPEC-v5.3 §5: its rounds, the listener, each round's go_on, the thread it took up and the one it left
        goes = [go_on(h, cfg, side, a, b) for side in sides]
        if t.get("thread"):
            picked(h, a, b, t["thread"])
        rec.update(rounds=parts, third=third["id"] if third else None, go_on=goes, thread=left(h, cfg, a, b, t.get("subject", ""), goes[-1]))
        contracts.count(h, "rounds", len(rounds))
        for n in range(2, len(rounds) + 1):
            contracts.event53(h, "round", a=a["id"], b=b["id"], n=n)
    h.setdefault("talks", []).append(rec)
    del h["talks"][:-300]
    if deep:
        ids = dict({la: a["id"], lb: b["id"]}, **({ns[2]: third["id"]} if third else {}))
        memories.from_talk(h, cfg, rec, ids)   # (B's: knows, wants, holds and remember become memories)
        for m in later:   # (SPEC-v5.3: what each came to know in a later round, too)
            memories.from_talk(h, cfg, {"minds": m}, ids)
    said = " / ".join('%s: "%s"' % (label(h["pets"][x["who"]]), x["text"]) for x in lines)
    moment(h, "talk", "%s and %s talked: %s" % (label(a), label(b), said), a["id"], t["room"])
    h["moments"][-1].update(lines=lines, came_of=came, pets=[a["id"], b["id"]], talk=rec["n"], **{k: rec[k] for k in ("subject", "minds", "rounds", "third") if k in rec})   # (the page; the log keeps its columns)
    for x in lines:   # (the social log, as speaking always was)
        h.setdefault("said", []).append({"tick": h["tick"], "from": x["who"], "to": b["id"] if x["who"] == a["id"] else a["id"], "kind": "talk", "text": x["text"]})
    for p, o in ((a, b), (b, a)):
        add_event(h, p, "you talked with %s: %s" % (label(o), said[:300]))
        if set(came) - {"nothing", "news"} or after[p["id"]]["liking"]:   # remembered when it mattered
            w = 4 if set(came) & {"threat", "insult", "making up", "apology", "close bond", "justice"} else 3 if set(came) & {"lesson", "help given", "gift promised", "trade"} else 2
            memories.add(h, cfg, p, "I talked with %s: %s" % (label(o), "; ".join(did) or ", ".join(came)), w, about=(o["id"],), kind="talk")
    for p in here(h, a, awake=True):
        if p["id"] != b["id"]:
            add_event(h, p, "%s and %s talked" % (label(a), label(b)))
    return rec


def effect(h, cfg, what, doer, other, about, detail, reply, move, did, moved, r):
    """One thing that came of it, as the engine allows it. Returns what it came to (a CAME word), or None."""
    from . import conflict
    D, O = label(doer), label(other)
    if what == "news":
        if detail:
            memories.add(h, cfg, other, "%s told me: %s" % (D, detail), 1, about=(doer["id"],), kind="news")
        did.append("%s told %s news" % (D, O))
    elif what in ("help asked", "help given", "help refused"):
        asker, helper = (doer, other) if what == "help asked" else (other, doer)
        if what == "help asked":
            if {c["what"] for c in reply["came_of"]} & {"help given", "help refused"}:
                return what   # (the answer is its own item)
            willing = opinions.of(helper, asker["id"])["liking"] / 10 + 0.5 * character.trait(helper, "kind") + 0.2 > 0
            what = "help given" if willing else "help refused"
        if helper["stage"] in LITTLE:
            return None   # (a little one is asked nothing it could do)
        need = detail or next((x["text"] for x in asker.get("aims") or [] if not x.get("done")), "") or "what %s is at" % label(asker)
        if what == "help given":
            aim(h, helper, "help %s: %s" % (label(asker), need), "%s asked me" % label(asker), "help", asker["id"])
            move(asker, helper, "helped_me", "%s said they would help me" % label(helper))
            did.append("%s will help %s (%s)" % (label(helper), label(asker), need))
        else:
            move(asker, helper, "ignored_me", "%s would not help me" % label(helper))
            did.append("%s would not help %s" % (label(helper), label(asker)))
    elif what == "lesson":
        taught = craft.pass_on(h, cfg, doer, other, "taught")
        if taught and contracts.on51(cfg, "knowledge"):   # SPEC-v5.1 §5.4 (helper B): a hob's teaching, counted
            contracts.count(h, "taught", doer["id"])
        if not taught:   # no recipe to pass on: a skill it is better at (skills 0-10, helper A's)
            mine, theirs = memories.skills(doer), memories.skills(other)
            better = {k: v for k, v in mine.items() if v > theirs.get(k, 0) + 1}
            if not better:
                return None
            k = max(better, key=better.get)
            memories.practise(h, cfg, other, k, cfg["talk"]["teach_skill"])
            taught = "how to get better at %s" % k
        move(other, doer, "taught_me", "%s taught me %s" % (D, taught))
        moment(h, "taught", "%s taught %s that %s" % (D, O, taught), other["id"], other["room"])
        did.append("%s taught %s that %s" % (D, O, taught))
    elif what == "gossip":
        if about != "the visitor" and not isinstance(about, dict):
            return None   # (none, or a hob gone since it was asked: its words stand, and move nothing; 19 October 2026, it raised)
        about_id = "visitor" if about == "the visitor" else about["id"]
        said, true = opinions.say(h, cfg, doer, about_id)   # a sly hob's gossip may be invented (§4)
        opinions.gossip(h, cfg, doer, other, about_id, said, true)
        if not true:   # SPEC-v4.2 §6.3: a lie told, with nobody but the listener to hear it, is the teller's secret
            from . import drives
            drives.keep_secret(h, cfg, doer, "lie", "I told %s a thing about %s that was not true" % (O, "the visitor" if about_id == "visitor" else label(about)), other["id"])
        did.append("%s told %s what it thinks of %s%s" % (D, O, "the visitor" if about_id == "visitor" else label(about), "" if true else " (not the truth)"))
    elif what == "plan":
        for p, q in ((doer, other), (other, doer)):
            if p["stage"] not in LITTLE:
                aim(h, p, detail or "do something with %s" % label(q), "we planned it together", "plan", q["id"])
        did.append("%s and %s made a plan%s" % (D, O, ": " + detail if detail else ""))
    elif what == "gathering":
        g = start_gathering(h, cfg, doer, detail)
        if not g:
            return None
        did.append("%s called everyone to a %s" % (D, g["kind"]))
    elif what == "argument":
        move(doer, other, "talked_harshly", "argued with %s" % O)
        move(other, doer, "talked_harshly", "argued with %s" % D)
        did.append("%s and %s argued" % (D, O))
    elif what == "insult":   # rung 2 (§7.1): helper C's step, moment and the insulted one's grievance; the opinion is talk's
        move(other, doer, "insult", "%s insulted me" % D)
        conflict.act(h, cfg, doer["id"], other["id"], 2, detail)
        did.append("%s insulted %s" % (D, O))
    elif what == "threat":   # a threat is a reason on both sides, and a fresh one makes the threatener angry enough to climb
        move(other, doer, "threatened_me", "%s threatened me" % D)
        grudge(h, cfg, doer, other, detail or "I mean to make %s pay" % O)
        grudge(h, cfg, other, doer, "%s threatened me" % D)
        moment(h, "threat", "%s threatened %s%s" % (D, O, ": " + detail if detail else ""), doer["id"], doer["room"])
        h["moments"][-1]["pets"] = [doer["id"], other["id"]]
        did.append("%s threatened %s" % (D, O))
    elif what in ("apology", "making up"):   # §7.2: whoever holds a grievance decides (helper C); with none, it is warmth
        if conflict.between(h, doer["id"], other["id"]):
            took = conflict.made_up(h, cfg, doer["id"], other["id"], "apology" if what == "apology" else "made up")
            moved.update({(doer["id"], other["id"]), (other["id"], doer["id"])})
            did.append("%s and %s made up" % (D, O) if took else "%s said sorry to %s, who would not have it" % (D, O) if what == "apology"
                       else "%s and %s tried to make up, and could not" % (D, O))
        else:
            move(other, doer, "apology" if what == "apology" else "made_up", "%s %s" % (D, "said sorry" if what == "apology" else "and I are friends again"))
            did.append("%s said sorry to %s" % (D, O) if what == "apology" else "%s and %s made up" % (D, O))
    elif what == "close bond":   # §6.3: "stay with me", taken only between hobs that are friends both ways
        F = opinions.DATA["bonds"]["friend"]
        if doer["stage"] in LITTLE or other["stage"] in LITTLE or min(opinions.of(doer, other["id"])["liking"], opinions.of(other, doer["id"])["liking"]) < F \
                or not bonds.form(h, cfg, doer, other, detail or "we said we would stay together"):
            return None
        did.append("%s and %s will stay together" % (D, O))
    elif what == "justice":   # §7.4: what it says the family should do with a killer
        verdict = next((v for v in ("drive out", "shun", "pardon", "nothing") if v in detail.lower()), None)
        if not isinstance(about, dict) or not verdict or not conflict.vote(h, cfg, doer["id"], about["id"], verdict):
            return None
        did.append("%s would have %s %s" % (D, label(about), {"drive out": "driven out", "shun": "shunned", "pardon": "forgiven", "nothing": "left be"}[verdict]))
    elif what == "gift promised":
        aim(h, doer, "give %s %s" % (O, detail or "something"), "I promised", "give", other["id"])
        did.append("%s promised %s %s" % (D, O, detail or "a gift"))
    elif what == "trade":
        return trade(h, cfg, doer, other, move, did, r)
    return what


def trade(h, cfg, doer, other, move, did, r):
    """Greedy hobs bargain (§6.1): one bit for one bit, fair; or a sly one takes and gives nothing back."""
    if not other["carrying"]:
        return None
    sly = character.trait(doer, "honest") < -0.3 and r.random() < -character.trait(doer, "honest")
    if not doer["carrying"] and not sly:
        return None
    theirs = other["carrying"].pop()
    if sly:
        if len(doer["carrying"]) < cfg["make"]["carry"]:
            doer["carrying"].append(theirs)
        move(other, doer, "lied_to_me", "%s took my %s and gave nothing back" % (label(doer), theirs))
        grudge(h, cfg, other, doer, "%s swindled me out of my %s" % (label(doer), theirs))
        did.append("%s swindled %s out of a %s" % (label(doer), label(other), theirs))
        return "trade"
    mine = doer["carrying"].pop()
    doer["carrying"].append(theirs)
    other["carrying"].append(mine)
    move(other, doer, "worked_together", "traded my %s for a %s" % (theirs, mine))
    move(doer, other, "worked_together", "traded my %s for a %s" % (mine, theirs))
    moment(h, "gift", "%s traded a %s for %s's %s" % (label(doer), mine, label(other), theirs), doer["id"], doer["room"])
    did.append("%s traded a %s for %s's %s" % (label(doer), mine, label(other), theirs))
    return "trade"


def snub(h, cfg, a, b):
    """Rung 1 (§7.1): it turns away and won't answer. No model call: a word, and silence (helper C's step and moment)."""
    from . import conflict
    h["n"]["talk"] = h["n"].get("talk", 0) + 1
    rec = {"n": h["n"]["talk"], "tick": h["tick"], "room": a["room"], "a": a["id"], "b": b["id"],
           "lines": [{"who": a["id"], "text": "%s?" % label(b)}, {"who": b["id"], "text": "(turns away and says nothing)"}], "came_of": ["snub"],
           "after": {a["id"]: {"mood": character.mood(a), "liking": -1}, b["id"]: {"mood": character.mood(b), "liking": 0}},
           "did": ["%s snubbed %s" % (label(b), label(a))]}
    h.setdefault("snubs", []).append(rec)   # (19 October 2026: kept apart from the talks, so a snub is no conversation for the budget, the want or the Lab)
    del h["snubs"][:-100]
    opinions.move(h, cfg, a, b["id"], "ignored_me", "%s turned away from me and would not answer" % label(b))
    conflict.act(h, cfg, b["id"], a["id"], 1)
    add_event(h, a, "%s turned away from you and would not answer" % label(b))
    return rec


# ---- promises and gatherings (§6.1) ----

def keep_promises(h, cfg):
    """A promised gift is held out when the two are next together and the giver has something in its paws; a promise
    left `promise_days` is broken, and remembered."""
    if h["tick"] % 10:
        return
    from . import actions
    for p in alive(h):
        for x in [x for x in p.get("aims") or [] if x["kind"] == "give" and not x.get("done")]:
            to = h["pets"].get(x["target"])
            if not to or to["stage"] == "dead":
                x["done"] = "gone"
            elif to["room"] == p["room"] and not p["sleep"] and not to["sleep"] and p["carrying"]:
                actions.offer(h, cfg, p, to, {"kind": "give", "what": p["carrying"][-1], "bit": True})
                add_event(h, to, "%s held out the %s it promised you" % (label(p), p["carrying"][-1]))
                opinions.move(h, cfg, to, p["id"], "kept_promise", "%s kept its promise" % label(p))
                x["done"] = h["tick"]
            elif h["tick"] - x["since"] > hours(cfg, 24 * cfg["talk"]["promise_days"]):
                x["done"] = "broken"
                opinions.move(h, cfg, to, p["id"], "broke_promise", "%s promised me a gift and never gave it" % label(p))
                grudge(h, cfg, to, p, "%s broke a promise" % label(p))


def start_gathering(h, cfg, by, detail=""):
    """Social hobs start them (§6.1): a meal together, singing, a celebration for a birth or a first, a vigil for a
    death. Each invited hob gets an aim to go; the solitary slip away."""
    occ = occasion(h, cfg)
    last = (h.get("gatherings") or [{}])[-1]
    if h.get("gathering") or character.trait(by, "social") < 0 or (occ and last.get("occasion") == occ[1]["n"]) \
            or h["tick"] - last.get("until", -10**9) < hours(cfg, cfg["talk"]["gather_every_hours"]):
        return None   # (one at a time, one for each birth, death or first, and not every hour)
    kind = occ[0] if occ else "meal" if int(h["clock"]["hour"]) in (12, 13, 18, 19) else "singing"
    room = by["room"]
    if kind == "vigil":   # at the stone, once it has one
        room = next((rid for rid, x in h["rooms"].items() if any((o.get("memorial") or {}).get("pet") == occ[1]["pet"] for o in x["objects"].values())), room)
    why = detail or (occ[1]["text"] if occ else "to be together")
    g = {"kind": kind, "room": room, "since": h["tick"], "until": h["tick"] + hours(cfg, cfg["talk"]["gather_hours"]), "by": by["id"],
         "for": occ[1]["pet"] if occ else None, "occasion": occ[1]["n"] if occ else None, "why": why, "who": []}
    for p in alive(h):
        if p["stage"] != "egg" and (p is by or character.trait(p, "social") > -0.4) and not p.get("outcast") and not p.get("shunned"):
            g["who"].append(p["id"])
            aim(h, p, "go to the %s in %s" % (kind, h["rooms"][room]["name"]), "%s called everyone" % label(by), "gather", room)
    h["gathering"] = g
    moment(h, "gathering", "%s called everyone to a %s in %s: %s" % (label(by), kind, h["rooms"][room]["name"], why), by["id"], room)
    return g


def gathering_tick(h, cfg):
    g = h.get("gathering")
    if not g or h["tick"] < g["until"]:
        return
    came = [p for p in alive(h) if p["id"] in g["who"] and p["room"] == g["room"]]
    for p in came:
        memories.add(h, cfg, p, "we held a %s in %s: %s" % (g["kind"], h["rooms"][g["room"]]["name"], g["why"]), 4 if g["kind"] == "vigil" else 2,
                     about=tuple(q["id"] for q in came if q is not p)[:4], kind="gathering")
        for q in came:
            if q is not p:
                opinions.move(h, cfg, p, q["id"], "ate_together" if g["kind"] == "meal" else "sang_with", "we were at the %s together" % g["kind"], remember=False)
    for p in alive(h):
        for x in p.get("aims") or []:
            if x["kind"] == "gather" and not x.get("done"):
                x["done"] = h["tick"]
    g["came"] = [p["id"] for p in came]
    h.setdefault("gatherings", []).append(g)
    del h["gatherings"][:-20]
    h["gathering"] = None
    moment(h, "gathering", "the %s in %s is over: %s came" % (g["kind"], h["rooms"][g["room"]]["name"], ", ".join(label(p) for p in came) or "nobody"), g["by"], g["room"])


# ---- the stub brain's side of a conversation: deterministic, from traits and opinions ----

QUESTIONS = ["What is beyond the meadow?", "Why does the house hum at night?", "Who made the house?", "Where do the dead go?",
             "Why do the lights go out in storms?", "What are the stars?"]


def stub_reply(h, cfg, a, b, r):
    """What a scripted brain says: the model's shape, chosen from who they are and what they think of each other."""
    A, B, la, lb = label(a), label(b), opinions.of(a, b["id"])["liking"], opinions.of(b, a["id"])["liking"]
    ka, kb = names(a, b)
    t = character.trait
    occ = occasion(h, cfg)
    third = [(k, v["liking"]) for k, v in (a.get("opinions") or {}).items() if k not in (b["id"], "visitor") and abs(v["liking"]) >= 4
             and k in h["pets"] and h["pets"][k]["stage"] != "dead"]
    want = next((x["text"] for x in a.get("aims") or [] if not x.get("done") and x["kind"] not in ("help", "give", "gather")), None) \
        or (a.get("wants") or [{}])[0].get("text")
    want = re.sub(r"^(you )?(want|wish|would like|mean) to ", "", want or "") or None   # (wants are told to it as "you want to ...")
    first, rest = [], []
    if (grievances(h, b["id"], a["id"]) or grievances(h, a["id"], b["id"])) and (t(a, "kind") > 0 or t(a, "honest") > 0):
        first.append("apology")
    if la < -2 and (t(a, "kind") < 0 or character.mood(a) == "angry"):
        first.append("threat" if la < -5 else "insult")
    if want and lb >= 0:
        rest.append("help asked")
    if any(k not in b.get("recipes", {}) for k in a.get("recipes", {})) and t(a, "generous") >= 0 and a["stage"] in ("adult", "elder"):
        rest.append("lesson")
    if occ and t(a, "social") > 0:
        rest.append("gathering")
    if t(a, "generous") < -0.3 and a["carrying"] and b["carrying"]:
        rest.append("trade")
    if third:
        rest.append("gossip")
    if t(a, "generous") > 0.3:
        rest.append("gift promised")
    if min(la, lb) >= 7 and a["stage"] in ("adult", "elder") and b["stage"] in ("adult", "elder"):
        rest.append("close bond")
    killer = next((k["killer"] for k in h.get("killings", []) if k.get("known") and k.get("verdict") is None and k["killer"] in h["pets"]
                   and k["killer"] not in (a["id"], b["id"])), None)
    if killer:
        first.append("justice")
    what = first[0] if first else r.choice(rest) if rest else r.choice(["news", "nothing", "plan"])
    about = label(h["pets"][max(third, key=lambda kl: abs(kl[1]))[0]]) if what == "gossip" else label(h["pets"][killer]) if what == "justice" else ""
    verdict = "pardon" if t(a, "kind") > 0.3 else "drive out" if t(a, "kind") < -0.3 else "shun"
    lines = {
        "apology": ["I was wrong before, %s. I'm sorry." % B, "Well... all right." if t(b, "kind") >= 0 else "Sorry won't mend it."],
        "insult": ["You again, %s? Clumsy as ever." % B, "Leave me be."],
        "threat": ["Cross me again, %s, and you'll be sorry." % B, "Is that a threat?", "Take it how you like."],
        "help asked": ["%s, will you help me? I'm after this: %s." % (B, (want or "finishing something").rstrip(".")),
                       "Yes, I'll help." if t(b, "kind") + lb / 10 + 0.2 > 0 else "Not now. Do it yourself."],
        "lesson": ["Watch, %s, I'll show you something I found out." % B, "Show me!", "There. Now you know it too."],
        "gathering": ["Let's all get together, %s!" % B, "Yes, everyone should come."],
        "trade": ["My %s for your %s?" % ((a["carrying"] or ["bit"])[-1], (b["carrying"] or ["bit"])[-1]), "Hm. Fine."],
        "gossip": ["Have you seen what %s has been up to?" % about, "No, tell me."],
        "gift promised": ["I'll bring you something nice, %s." % B, "You will? Thank you!"],
        "close bond": ["Stay with me, %s. Always." % B, "Always."],
        "justice": ["What should we do about %s?" % about, "I don't know.", "I say: %s." % verdict],
        "news": ["Guess what happened today, %s." % B, "Go on, tell me."],
        "plan": ["Shall we do something together later?", "Yes, let's."],
        "nothing": ["Nice day.", "Mm."],
    }[what]
    if t(a, "playful") > 0.4:
        lines[0] += " Heh."
    if t(a, "brave") < -0.4:
        lines[0] = lines[0].rstrip(".!?") + "..."
    warm = what in ("apology", "help asked", "lesson", "gathering", "gift promised", "plan", "gossip", "news", "close bond")
    cold = what in ("insult", "threat")
    came = [{"what": what, "by": ka, "about": about, "detail": short(want or "", 16, 100) if what == "help asked" else verdict if what == "justice" else ""}]
    if cold and t(b, "kind") < 0.3:
        came.append({"what": "argument", "by": kb, "about": "", "detail": ""})
    if what == "apology" and t(b, "kind") >= 0:
        came.append({"what": "making up", "by": kb, "about": "", "detail": ""})
    mood_a = "angry" if cold else "proud" if what == "lesson" else "content"
    mood_b = "afraid" if what == "threat" else "angry" if cold else "excited" if what == "lesson" else "happy" if warm else character.mood(b)
    toward = "cooler" if cold else "warmer" if warm else "same"
    q = r.choice(QUESTIONS) if t(a, "curious") >= 0.3 and a.get("believes") is not False and r.random() < 0.3 else ""
    return {"lines": [x[:140] for x in lines], "came_of": came,
            "after": {ka: {"mood": mood_a, "toward": toward}, kb: {"mood": mood_b if mood_b in MOODS else "content", "toward": toward}},
            "ask_visitor": {"who": ka if q else "", "q": q}}


def stub_reply2(h, cfg, a, b, r, subj=""):
    """SPEC-v4.2 §7: the scripted reply with subtext: v4.0's, its talk carried on from the subject to four lines or more,
    each answering the last (SPEC-v4.2.2 §1), and what was on each mind (a secret always in what it holds)."""
    out, (ka, kb) = stub_reply(h, cfg, a, b, r), names(a, b)
    lo, hi = cfg["talk2"]["lines"]
    said = ["Did you hear, {you}? %s." % (subj[:1].upper() + subj[1:]), "I heard. What do you make of it, {you}?"] if subj else []
    said += ["Have you eaten, {you}?", "Not yet. Have you?", "Later. What are you up to?", "Not much, {you}. You?"]
    lines = list(out["lines"])
    while len(lines) < lo:
        lines.append((said.pop(0) if said else "You said it.").replace("{you}", label((b, a)[len(lines) % 2])))

    def side(p, o):
        s, mind = p.get("secret"), on_mind(h, cfg, p, o)
        holds = s["text"] if s and not s.get("found") else "that I am %s" % contracts.flaw(p["flaw"])["name"] if p.get("flaw") else "what I really think of %s" % label(o)
        knows = "%s is %s, and %s" % (label(o), character.mood(o), "lives %s" % contracts.drive(o["drive"])["name"] if o.get("drive") else "cares for %s" % (o.get("values") or ["the house"])[0])
        return {"wants": (mind[0] if mind else "to pass the time with %s" % label(o))[:160], "holds": holds[:160], "knows": knows[:200],
                "remember": ("we talked of %s" % subj.split(": ", 1)[-1])[:200] if subj else ""}
    return dict(out, lines=[x[:cfg["talk2"]["line_chars"]] for x in lines[:hi]], minds={ka: side(a, b), kb: side(b, a)})


ONWARD = [["And there's more to it.", "Go on, then. I'm listening.", "I keep turning it over. I can't leave it be.", "No more can I. What do we do?"],
          ["Where were we?", "You were telling me. Don't stop now.", "All right. It's this: I think it matters more than we said.", "Maybe it does. Let me think on it."],
          ["One more thing, and then I'll leave it.", "You always say one more thing.", "This time I mean it. Truly.", "We'll see. We'll see."]]


def stub_round(h, cfg, a, b, r, subj="", n=1, third=None):
    """SPEC-v5.3 §5 the scripted reply in rounds: v4.2's for the first, more lines after it, each side's go_on from its
    sociability (so talks sometimes go on, and now and then to three), and a listener's line and minds."""
    out, (ka, kb) = stub_reply2(h, cfg, a, b, r, subj), names(a, b)
    if n > 1:
        out["lines"] = list(r.choice(ONWARD))
    about = subj or "it"
    out["go_on"] = {k: {"go_on": "yes", "why": "I want to know more about %s" % about} if r.random() < 0.6 + 0.25 * character.trait(p, "social")
                    else {"go_on": "no", "why": "I've said what I had to"} for k, p in ((ka, a), (kb, b))}
    if third:
        kc = names3(a, b, third)[2]
        out["third_line"] = r.choice(["Don't mind me. I'm only listening.", "I heard that, %s." % label(a), "That's not how I remember it, %s." % label(b)])
        out["minds"][kc] = {"wants": "to hear what they say", "holds": "what I think of the two of them",
                            "knows": "%s and %s talk of %s" % (label(a), label(b), about), "remember": ""}
    return out
