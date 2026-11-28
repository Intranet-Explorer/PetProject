"""The model brain (SPEC §7, SPEC-v3 §3): a local model behind an OpenAI-compatible endpoint on this machine.
It is given its situation in words, what it can do, and the shape of a reply. Nothing tells it what it is."""
import asyncio
import json
import logging
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ..actions import FOCUS, PLACES as SPOTS
from .. import contracts as K
from ..log import HTTP
from ..songs import NOTES, PITCH
from ..things import COLORS, DO, PLACES, SHAPES, WHEN

from ..things import SIZES
PART = '{"shape": %s, "size": 1 to 3, "color": %s, "at": %s}' % ("|".join(SHAPES), "|".join(COLORS), "|".join(PLACES))   # a picture of itself, at night
WRITTEN = {   # how each action is written, shown only for the actions it can do right now
    "observe": '{"type": "observe"}',
    "look": '{"type": "look", "target": anything or anyone here, or a door}',
    "move": '{"type": "move", "to": anything or anyone here, or %s}' % " | ".join(SPOTS),
    "go": '{"type": "go", "door": one of the doors}',
    "speak": '{"type": "speak", "text": at most 120 chars, "to": someone here or "visitor" (leave out to speak to nobody in particular)}',
    "rest": '{"type": "rest"}',
    "use": '{"type": "use", "target": a thing here}',
    "gather": '{"type": "gather", "what": something lying about}',
    "drop": '{"type": "drop", "what": something you carry}',
    "make": ('{"type": "make", "recipe": {"kind": what it is, one of %%s, "material": what it will be like, one of %%s (it uses up one bit that can be that), '
             '"color": %s, "size": %%s, "name": your own name for it, up to 24 chars, "purpose": what it is for, up to 80 chars}, '
             '"near": a thing here, or "here"}' % "|".join(COLORS)),
    "unmake": '{"type": "unmake", "target": a made thing that is yours to take apart}',
    "arrange": '{"type": "arrange", "object": something that can be moved, "near": a thing here, or "here"}',
    "combine": ('{"type": "combine", "a": a made thing, "b": another, "recipe": {"name": up to 24 chars, '
                '"material": what either of them is like, "purpose": what it is for, up to 80 chars}} (the two become one thing; what kind it is follows from what they were, and if nobody here has made the like it is a new kind of thing, known by the name you give it: name it for what it does)'),
    "paint": '{"type": "paint", "where": "wall" | "floor" | a rug here, "pattern": "like your coat" | "stripes" | "dots" | "border"} (it uses up the dye you carry, and is in its colour)',
    "teach": ('{"type": "teach", "target": one of your things, "behavior": {"when": %s, "do": %s|change_color:<a color>}}'
              % ("|".join(WHEN), "|".join(d for d in DO if ":" not in d))),
    "give": '{"type": "give", "what": something you carry or a thing of yours, "to": someone here}',
    "show": '{"type": "show", "what": a thing here, "to": someone here}',
    "follow": '{"type": "follow", "who": someone here}',
    "nuzzle": '{"type": "nuzzle", "who": someone beside you}',
    "accept": '{"type": "accept", "from": whoever is offering}',
    "take": '{"type": "take", "what": a thing here that is someone else\'s}',
    "chase": '{"type": "chase", "who": a small creature here}',
    "tell": '{"type": "tell", "to": someone here, "text": something for them to keep, up to 400 chars}',
    "lay_egg": ('{"type": "lay_egg", "name": a name for your child, up to 16 chars (or "" to leave it to them): a real name, one of those offered or your own, not a phrase, '
                '"message": a few sentences, at most four, in your own words, on what you have learned in your own life}'),
    "bequeath": '{"type": "bequeath", "what": a thing of yours here, "to": a child\'s name, or "my children"}',
    "write_belief": '{"type": "write_belief", "statement": one short sentence of at most 200 characters, "source": how you know it: lived | seen | told by <who>}',
    "revise_belief": '{"type": "revise_belief", "id": belief id, "statement": new text or "discard"}',
    "take_name": '{"type": "take_name"} (take the name the visitor calls you, as your own)',
    "put_away": '{"type": "put_away", "what": a made thing here that you may move, "where": something here that keeps things}',
    "take_out": '{"type": "take_out", "what": a thing that is put away here}',
    "hang": '{"type": "hang", "what": a thing here that can hang on a wall}',
    # SPEC-v3.1
    "write": '{"type": "write", "text": a few words, at most 80 chars, "on": a wall (north wall | south wall | west wall | east wall), a stone here, or a thing of yours}',
    "scrub": '{"type": "scrub", "what": one of the writings here, named by where it is and how it begins}',
    "compose": ('{"type": "compose", "name": a name for the song, up to 24 chars, "notes": [3 to 12 notes, each a pitch (%s; or "low " or "high " before one) '
                'followed by "short" or "long", for example "do short", "high so long"]}' % ", ".join(PITCH[5:10])),
    "sing": '{"type": "sing", "song": a song you know, "to": someone here or "egg" (leave out to sing to the room)}',
    "teach_song": '{"type": "teach_song", "song": a song you know, "to": someone awake here; they will have it note for note}',
    "call": '{"type": "call", "who": an animal of yours}',
    "name": '{"type": "name", "what": an animal of yours here, or "egg", "name": a real name, up to 16 chars}',
    "ask_book": '{"type": "ask_book", "question": what you want to know, at most 80 chars}',
    # SPEC-v3.4 §3
    "process": '{"type": "process", "what": a bit you carry or one lying here, "how": one of the ways it could be tried here} (do that to it and see what comes of it)',
    "mend": '{"type": "mend", "target": a made thing here that is worn or spoiled}',
    "carry": '{"type": "carry", "door": one of the doors} (carry the heavy book through it, slowly; it stays where you put it down)',
}
from ..machine import WRITTEN as _machine, schema as machine_schema   # SPEC-v3.5 §4.3
WRITTEN.update(_machine)
from ..rail import WRITTEN as _rail, schema as rail_schema   # SPEC-v3.5.12 §3
WRITTEN.update(_rail)
FORMAT_OLD = """
Reply with one JSON object and nothing else:
{"thought": "<short, why>", "intention": "<what you mean to do, in a few words>", "steps": [<2 to 5 of the things you can do, carried out in order>], "expect": "<how you expect to feel once the steps are done, or what you expect to see>"}
each step is one of:
%s
"""
# SPEC-v3.3 §1.2: it says what it wants to be about, and decides the things that are its to decide. Wandering, resting,
# eating, tidying and the like happen between thoughts without being asked for.
FORMAT = """
Reply with one JSON object and nothing else:
{"thought": "<short, why>", "focus": {"type": "<%s>", "target": "<who or what it is about, where that applies: someone or something here>", "words": "<what you want to be about for the next while, in a few plain words of your own>"}, "steps": [<0 to 3 things you decide to do now, carried out in order; leave it empty to simply carry on>], "expect": "<how you expect to feel before long, or what you expect to see>"}
between thoughts you carry on by yourself with whatever your focus is: moving about, resting, eating, looking at things. A step is for something you decide. Each step is one of:
%s
"""
# SPEC-v3.6c §2: quicker thoughts. The same steps, said shortly (the reply's schema holds each to what is really
# there, so the words need not list it), and a shorter reply. Steps not here are said as in WRITTEN.
SHORT = {
    "observe": "observe", "rest": "rest", "take_name": "take_name (the visitor's name for you)",
    "look": "look: target", "move": "move: to", "go": "go: door", "use": "use: target", "gather": "gather: what (lying about)",
    "drop": "drop: what (you carry)", "unmake": "unmake: target (yours)", "arrange": "arrange: object, near", "chase": "chase: who",
    "speak": "speak: text (at most 120 chars), to (or leave out)", "give": "give: what, to", "show": "show: what, to", "follow": "follow: who",
    "nuzzle": "nuzzle: who", "accept": "accept: from", "take": "take: what (someone else's)", "tell": "tell: to, text (for them to keep)",
    "make": "make: recipe {kind, material (uses up one bit that can be that), color, size, name (your own, up to 24 chars), purpose (up to 80 chars)}, near",
    "combine": "combine: a, b, recipe {name, material, purpose} (the two become one thing; a new kind if nobody has made the like: name it for what it does)",
    "paint": "paint: where (wall, floor or a rug), pattern (uses up your dye)", "teach": "teach: target (yours), behavior {when, do}",
    "write": "write: text (a few words), on", "scrub": "scrub: what", "compose": "compose: name, notes (3 to 12, like \"do short\", \"high so long\")",
    "sing": "sing: song, to (or leave out)", "teach_song": "teach_song: song, to", "call": "call: who (an animal of yours)", "name": "name: what, name",
    "ask_book": "ask_book: question (at most 80 chars)", "process": "process: what (a bit), how (a way it could be tried here)",
    "mend": "mend: target (worn or spoiled)", "carry": "carry: door (the heavy book)", "put_away": "put_away: what, where",
    "take_out": "take_out: what", "hang": "hang: what", "bequeath": "bequeath: what, to",
    "write_belief": "write_belief: statement (one short sentence), source", "revise_belief": "revise_belief: id, statement (or \"discard\")",
    "lay_egg": "lay_egg: name (a real name, or \"\"), message (a few sentences, at most four, on what you have learned)",
    "machine_take": "machine_take: what (a material it holds)", "machine_feed": "machine_feed: what (a made thing of yours, or \"bits\"), for (the material back)",
    "ask_train": "ask_train: what (kept in the store)",
}
FORMAT_SHORT = """
Reply with one JSON object and nothing else:
{"thought": "<short, why>", "focus": {"type": "<%s>", "target": "<who or what, if it applies>", "words": "<what you want to be about next, in a few words>"}, "steps": [<0 to 3 things you decide to do now, in order; empty to carry on>], "expect": "<what you expect, briefly>"}
between thoughts you carry on by yourself with your focus. A step is {"type": ..., and its fields}; the steps you can take now:
%s
"""
NIGHT = """
Reply with one JSON object and nothing else:
{%s}
"""
NIGHT_PARTS = {
    "dream": '"dream": "<two or three sentences about your day, in your own words>"',
    "changes": ('"changes": [<at most 3 of {"type": "write_belief", "statement": "<one short sentence of at most 200 characters, about how something works or about yourself or someone; '
                'not a list of what happened>", "source": "lived | seen | told by <who>"} or {"type": "revise_belief", "id": "<belief id>", "statement": "<new text or discard>"}>]'),
    "review": '"review": {"decision": "keep | revise | discard", "statement": "<the new text, if you revise it>"}',
    "project": '"project": {"decision": "keep | set | finish | abandon", "text": "<the project in a few of your own words, at most 130 characters, if you set one: something to do or find out over the coming days, that you can finish; not a way to be, and not something to wait for or not do>"}',
    "people": '"people": [<for anyone you want to remember something about: {"who": "<who>", "line": "<one line, in your own words>"}>]',
    "message": '"message": "<your message for your children, written fresh in your own words: a few sentences, at most four, on what you have learned in your own life. Do not start from your old message or add to it>"',
    "my_life": '"my_life": "<the story of your life, in your own words, up to 800 characters>"',
    "ambition": '"ambition": {"take": "<the one you take, in its words as written above, or keep to keep your own>", "words": "<it in a few words of your own, a short line>"}',   # SPEC-v3.5.4 §9
}   # (19 October 2026, REVIEW-v4.0.4 C11: an ambition is taken by its words, not its number; took_words turns them back into firsts.took's number)


def offered(text):
    """The ambitions a packet offers (firsts.offer: "  1. ..." under "your ambition for your life"), in order."""
    at = text.find("your ambition for your life")
    return re.findall(r"^ *\d+\. (.+)$", text[at:], re.M) if at >= 0 else []


def took_words(reply, text_):
    """The ambition chosen by its words, given the number firsts.took reads (0 keeps its own): the one offered that
    the words are, or that they are part of (or the other way about)."""
    a = reply.get("ambition")
    if isinstance(a, dict) and "take" in a:
        took = " ".join(str(a["take"]).lower().split()).strip(" .")
        a["pick"] = next((i for i, o in enumerate(offered(text_), 1) if took not in ("", "keep") and (took in o.lower() or o.lower().strip(" .") in took)), 0)
    return reply


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def text(most, least=1):
    return {"type": "string", "minLength": least, "maxLength": most}


AMBITION = {"type": "object", "properties": {"take": text(140), "words": text(140, 0)}, "required": ["take"]}   # (taken by its words: took_words)


def schema(ctx):
    """Constrained output (SPEC-v2 §3): an intention of 2 to 5 steps, each step one variant per thing it can do
    now, built from what the packet shows. A step cannot name something that is not there."""
    c = ctx
    anyone, awake = c["pets"] + c["creatures"], c["awake"]
    visible = c["things"] + c["pets"] + c["creatures"] + c["bits"] + [d + " door" for d in c["doors"]] + (["egg"] if c["eggs"] else [])
    most, reach = c["make"]
    # one variant per material in reach, so a kind is only ever offered in a material it can be (SPEC-v3.2 §3.1)
    recipes = [obj(kind={"enum": c["kinds"][m]}, material={"const": m}, color={"enum": COLORS}, size={"enum": SIZES[:max(most, 1)]},
                   name=text(24), purpose=text(80)) for m in reach if c["kinds"].get(m)]
    near = {"enum": c["things"] + ["here"]}
    one = lambda t, **p: obj(type={"const": t}, **p)
    v = {
        "observe": [one("observe")], "rest": [one("rest")], "take_name": [one("take_name")],
        "put_away": [one("put_away", what={"enum": c["loose"]}, where={"enum": c["stores"]})] if c.get("loose") and c.get("stores") else [],
        "take_out": [one("take_out", what={"enum": c["stored"]})] if c.get("stored") else [],
        "hang": [one("hang", what={"enum": c["hangable"]})] if c.get("hangable") else [],
        "look": [one("look", target={"enum": visible + ["visitor"]})],
        "move": [one("move", to={"enum": c["things"] + anyone + list(SPOTS)})],
        "go": [one("go", door={"enum": c["doors"]})],
        "speak": [one("speak", text=text(160))] + ([one("speak", text=text(160), to={"enum": awake + ["visitor"]})] if awake else []),
        "use": [one("use", target={"enum": c["things"]})],
        "gather": [one("gather", what={"enum": c["bits"]})] if c["bits"] else [],
        "drop": [one("drop", what={"enum": c["carrying"]})] if c["carrying"] else [],
        "make": [one("make", recipe=r, near=near) for r in recipes] if most else [],
        "unmake": [one("unmake", target={"enum": c["free"]})] if c["free"] else [],
        "arrange": [one("arrange", object={"enum": c["movable"]}, near=near)] if c["movable"] else [],
        "combine": [one("combine", a={"enum": c["free"]}, b={"enum": c["free"]},
                        recipe=obj(name=text(24), material={"enum": c["materials"]}, purpose=text(80)))] if len(c["free"]) > 1 else [],
        "paint": [one("paint", where={"enum": ["wall", "floor"] + c.get("rugs", [])}, pattern={"enum": ["like your coat", "stripes", "dots", "border"]})],
        "teach": [one("teach", target={"enum": c["mine"]}, behavior=obj(when={"enum": WHEN}, do={"enum": DO}))] if c["mine"] else [],
        "give": [one("give", what={"enum": list(dict.fromkeys(c["carrying"] + c["bits"] + c["mine"]))}, to={"enum": awake + c["creatures"]})]
        if (awake or c["creatures"]) and (c["carrying"] or c["bits"] or c["mine"]) else [],
        "show": [one("show", what={"enum": c["things"]}, to={"enum": awake})] if awake and c["things"] else [],
        "follow": [one("follow", who={"enum": anyone})] if anyone else [],
        "nuzzle": [one("nuzzle", who={"enum": awake + (["egg"] if c["eggs"] else [])})] if awake or c["eggs"] else [],
        "accept": [one("accept", **{"from": {"enum": c["offers"]}})] if c["offers"] else [],
        "take": [one("take", what={"enum": c["theirs"]})] if c["theirs"] else [],
        "chase": [one("chase", who={"enum": c["creatures"]})] if c["creatures"] else [],
        "tell": [one("tell", to={"enum": awake}, text=text(400))] if awake else [],
        "lay_egg": [one("lay_egg", name=text(16, 0), message=text(640))],
        "bequeath": [one("bequeath", what={"enum": c["leave"] + c["songs"]}, to={"enum": c["kids"] + ["my children"]})] if c["leave"] or c["songs"] else [],
        "write": [one("write", text=text(100), on={"enum": c["surfaces"]})],
        "scrub": [one("scrub", what={"enum": c["writings"]})] if c["writings"] else [],
        "compose": [one("compose", name=text(24), notes={"type": "array", "items": {"enum": NOTES}, "minItems": 3, "maxItems": 12})],
        "sing": ([one("sing", song={"enum": c["songs"]})] + ([one("sing", song={"enum": c["songs"]}, to={"enum": c["pets"] + (["egg"] if c["eggs"] else [])})]
                                                              if c["pets"] or c["eggs"] else [])) if c["songs"] else [],
        "teach_song": [one("teach_song", song={"enum": c["songs"]}, to={"enum": awake})] if c["songs"] and awake else [],
        "call": [one("call", who={"enum": c["tame"]})] if c["tame"] else [],
        "name": [one("name", what={"enum": c["nameable"]}, name=text(16))] if c["nameable"] else [],
        "ask_book": [one("ask_book", question=text(80))],
        "process": [one("process", what={"const": b}, how={"enum": hows}) for b, hows in c.get("process", {}).items() if hows],
        "mend": [one("mend", target={"enum": c["mendable"]})] if c.get("mendable") else [],
        "carry": [one("carry", door={"enum": c["doors"]})],
        "write_belief": [one("write_belief", statement=text(240), source={"enum": ["lived", "seen"] + ["told by " + t for t in c["tellers"]]})],
        "revise_belief": [one("revise_belief", id={"enum": c["beliefs"]}, statement=text(240))] if c["beliefs"] else [],
    }
    v.update(machine_schema(c, one))
    v.update(rail_schema(c, one))
    step = {"anyOf": [x for a in c["allowed"] for x in v[a]]}
    if not step["anyOf"]:
        step = {"anyOf": v["observe"]}
    if not c.get("body"):
        return obj(thought=text(340, 0), intention=text(120),
                   steps={"type": "array", "items": step, "minItems": 2, "maxItems": 5}, expect=text(230, 0))
    t_, e_, f_ = c.get("reply") or (340, 230, 70)   # (SPEC-v3.6c §2: shorter when the thought is trimmed)
    plain = obj(type={"enum": ["tidy", "explore", "make", "rest", "project", "play"]}, words=text(f_))
    about = [obj(type={"const": "be with"}, target={"enum": c["pets"]}, words=text(f_))] if c["pets"] else []
    about += [obj(type={"enum": ["tend", "stay near"]}, target={"enum": c["things"]}, words=text(f_))] if c["things"] else []
    return obj(thought=text(t_, 0), focus={"anyOf": [plain] + about},
               steps={"type": "array", "items": step, "minItems": 0, "maxItems": 3}, expect=text(e_, 0))


def prompt(packet, ctx):
    most, reach = ctx["make"]
    kinds = sorted({k for m in reach for k in ctx["kinds"].get(m, [])})
    written = dict(WRITTEN, make=WRITTEN["make"] % ("|".join(kinds), "|".join(reach), "|".join(SIZES[:max(most, 1)])))
    usable = [a for a in ctx["allowed"] if a != "make" or (reach and most)]
    if ctx.get("trim") and ctx.get("body"):   # SPEC-v3.6c §2
        return packet + FORMAT_SHORT % (" | ".join(FOCUS), "\n".join("  " + SHORT.get(a, written[a]) for a in usable))
    if not ctx.get("body"):
        return packet + FORMAT_OLD % "\n".join("  " + written[a] for a in usable)
    return packet + FORMAT % (" | ".join(FOCUS), "\n".join("  " + written[a] for a in usable))


def night_schema(asks, belief_ids, tellers):
    change = {"type": "object", "properties": {
        "type": {"enum": ["write_belief", "revise_belief"]}, "id": {"type": "string"}, "statement": text(240),
        "source": {"enum": ["lived", "seen"] + ["told by " + t for t in tellers]}}, "required": ["type", "statement"]}
    parts = {
        "dream": text(500), "changes": {"type": "array", "items": change, "maxItems": 3},
        "review": {"type": "object", "properties": {"decision": {"enum": ["keep", "revise", "discard"]}, "statement": text(240, 0)}, "required": ["decision"]},
        "project": {"type": "object", "properties": {"decision": {"enum": ["keep", "set", "finish", "abandon"]}, "text": text(180, 0)}, "required": ["decision"]},
        "people": {"type": "array", "maxItems": 3, "items": obj(who={"type": "string"}, line=text(150))},
        "message": text(640), "my_life": text(860), "ambition": AMBITION,
    }
    return obj(**{k: parts[k] for k in asks})


# ---- SPEC-v4.0 §8: the five kinds of thought (engine/brain4.py), each with its own reply (helper D) ----

FORMAT4 = {
    "plan": """
Reply with one JSON object and nothing else:
{"thought": "<short: how the day looks to you>", "aims": [<2 or 3 of {"text": "<what you mean to do today, in a few words>", "why": "<your own reason>", "kind": "<%s>", "target": "<who, where or what it is about: one of the names you know, or empty>"}>], "seek": [<at most 2: who you want to spend time with today>], "avoid": [<at most 2: who you would rather keep away from>], "steps": [<0 to 2 things to do right now; empty to simply begin>]}
the steps you can take now:
%s
""",
    "react": """
Reply with one JSON object and nothing else:
{"thought": "<short: how this strikes you, in your own voice>", "feel": "<%s>", "do": {"kind": "<aim: something to do about it today | seek: go and find someone | rung: get back at someone (what comes of it is not yours to decide) | gift: give someone something | nothing>", "who": "<who it is about, or empty>", "aim": "<if an aim, its kind: %s>", "text": "<what you mean to do about it, in a few words>"}, "steps": [<0 to 2 things to do right now>]}
the steps you can take now:
%s
""",
    "reflect": """
Reply with one JSON object and nothing else:
{%s}
""",
}
REFLECT_PARTS = {
    "diary": '"diary": "<one or two sentences for your diary: the day, in your own words>"',
    "learned": '"learned": "<one short sentence: something today taught you about how things are, about yourself or someone; or empty>"',
    "opinions": '"opinions": [<at most 2 of {"who": "<someone>", "way": "warmer | cooler"}: whom you now feel more warmly or more coolly toward, after today>]',
    "memory": '"memory": "<one thing from today you want to keep, in a short line; or empty>"',
    "ambition": NIGHT_PARTS["ambition"], "message": NIGHT_PARTS["message"], "my_life": NIGHT_PARTS["my_life"],
}
# SPEC-v4.2 §10.2 (helper B): the reflection's fields under [spirit] (contracts.reflect_fields), in words
HOOK_WORDS = ("avoid_place: keep away from a room | avoid_thing: keep away from a kind of thing, a material or a catch | prefer_thing: go for one | "
              "trust: someone | watch: someone, warily | do_at: do something, at a time | make: a kind of thing | never: do something | none")
REFLECT_SPIRIT = {
    "diary": '"diary": "<a few sentences for your diary: the day, in your own words, what happened and what it meant to you; up to 600 characters>"',
    "review": '"review": {"decision": "keep | revise | discard", "statement": "<the belief in new words, if you revise it>"}',
    "remember": '"remember": [<up to three things from today you\'ll remember, each one plain sentence: what happened, what was said, what you found out>]',
    "learned": '"learned": {"text": "<one short sentence: something today taught you about how things are, about yourself or someone; or empty>", '
               '"hook": {"name": "<if it should change what you do: %s>", "arg": "<what it is about: the room, the thing, the one, or what to do>", "when": "<for do_at, when; else empty>"}}' % HOOK_WORDS,
    "self": '"self": {%s} (how you see yourself, five plain sentences, each under thirty words)' % ", ".join('"%s": "<...>"' % k.replace(" ", "_") for k in K.SELF),
    "visitor": '"visitor": "<one line: what you think the visitor is; as before, unless today changed it>"',
    "flaw": '"flaw": "<a line: where your %s got in the way today>"',
    "leave": '"leave": {"what": "<what you would leave>", "to": "<to whom>", "last_words": "<what you would say last, in a few sentences>"}',
}
# react's one new field (contracts.react_fields)
REACT_REMEMBER = ', "remember": "<one plain sentence you\'ll remember of this; or empty>"}'


def schema4(kind, ctx):
    """The reply's shape for each kind of thought (constrained output): every name it gives is one the packet knows."""
    names = lambda xs: {"enum": list(xs)} if xs else {"enum": [""]}
    pick = lambda xs, most: {"type": "array", "items": {"enum": list(xs)}, "maxItems": most} if xs else {"type": "array", "maxItems": 0}
    if kind == "reflect":
        parts = {"diary": text(300), "learned": text(200, 0), "memory": text(160, 0), "message": text(640), "my_life": text(860),
                 "opinions": {"type": "array", "maxItems": 2, "items": obj(who={"enum": ctx["hobs"]}, way={"enum": ["warmer", "cooler"]})} if ctx["hobs"] else {"type": "array", "maxItems": 0},
                 "ambition": AMBITION}
        if not ctx.get("spirit"):
            return obj(**{k: parts[k] for k in ctx["asks"]})
        parts.update(diary=text(600), review=obj(decision={"enum": ["keep", "revise", "discard"]}, statement=text(240, 0)))   # SPEC-v4.2 §10.2
        return K.add_fields(obj(**{k: parts[k] for k in ctx["asks"]}), K.reflect_fields(ctx.get("flaw"), ctx.get("old")))
    steps = schema(ctx)["properties"]["steps"]["items"] if ctx["allowed"] else None
    steps = {"type": "array", "items": steps, "maxItems": 2} if steps else {"type": "array", "maxItems": 0}
    if kind == "plan":
        jobs = ctx.get("jobs5")   # SPEC-v5.0 §3.5: an aim says what it is for; the plan may take a job and refuse one
        more = {"for": {"enum": ctx["for5"]}} if jobs is not None and ctx.get("for5") else {}
        aim = obj(text=text(100), why=text(120), kind={"enum": ctx["aim_kinds"]}, target={"enum": ctx["targets"] + [""]}, **more)
        if ctx.get("learn51"):   # SPEC-v5.1 §6.3: a learn aim may say what it wants to find out (optional)
            aim["properties"]["question"] = text(120, 0)
        if ctx.get("invent51"):   # SPEC-v5.1 §4.2: a make aim may invent (optional: defaulted to none)
            aim["properties"]["invent"] = K.invent_schema(ctx["invent51"]["parts"], ctx["invent51"]["materials"])
        out = obj(thought=text(200, 0), aims={"type": "array", "items": aim, "minItems": 2, "maxItems": 3},
                  seek=pick(ctx["hobs"], 2), avoid=pick(ctx["hobs"], 2), steps=steps)
        if ctx.get("project53") is not None:   # SPEC-v5.3 §4: a project named or proposed ("none": nothing)
            out = K.add_fields(out, {"project": K.project_schema(ctx["project53"]["kinds"])})
        return K.add_fields(out, {"job": obj(take={"enum": jobs + [""]}, refuse={"enum": jobs + [""]})}) if jobs is not None else out
    who, words, doing = {"enum": ctx["hobs"] + [""]}, text(100, 0), [d for d in ctx["does"] if d != "nothing"]
    act = obj(kind={"enum": doing}, who=who, aim={"enum": ctx["aim_kinds"]}, text=words)
    if ctx.get("invent51"):   # SPEC-v5.1 §4.2: and so may what it does now (optional)
        act["properties"]["invent"] = K.invent_schema(ctx["invent51"]["parts"], ctx["invent51"]["materials"])
    do = {"anyOf": ([act] if doing else [])
          + ([obj(kind={"const": "nothing"}, who=who, text=words)] if "nothing" in ctx["does"] else [])}   # (REVIEW-v4.0.4 C11: doing nothing needs no aim)
    out = obj(thought=text(200, 0), feel={"enum": ctx["moods"]}, do=do, steps=steps)
    out = K.add_fields(out, K.react_fields()) if ctx.get("spirit") else out   # (SPEC-v4.2 §4.1)
    return K.add_fields(out, {"nurse": {"enum": ["yes", "no"]}}) if ctx.get("nurse5") else out   # (jobs.ask_nurse)


INVENT4 = ('\nTo make a thing nobody has made, of the parts in "How things are made", a make aim (or what you do now, as an aim of kind make) '
           'may add "invent": {"name": "<what you call it, a few words>", "for": "<what or whom it is for>", "parts": [<1 to 5 of {"part": "<a part>", '
           '"material": "<what that part is made of>"}>], "charge": "<what it is filled or charged with, or none>", "how": "<one plain sentence: how it works>"}\n')


PROJECT4 = ('Your plan also says "project": {"kind": "<none, or what you mean to build: %s>", "site": "<where, in a few words: %s; or empty>", '
            '"why": "<why, in your words>", "goal": "<what it is, in your words: a shelter by the willow, for when the house is too loud>"}: '
            'name the one you mean to build, or begin one when a wish of yours is unmet; "none" otherwise\n')   # SPEC-v5.3 §4 (helper A)


LEARN4 = 'A learn aim may add "question": "<what you want to find out in the book, in a few words>"\n'   # SPEC-v5.1 §6.3


def prompt4(kind, packet, ctx):
    """SPEC-v5.1 §4.2: and how to invent, when the grammar was shown."""
    P = ctx.get("project53")
    return prompt4_(kind, packet, ctx) + (INVENT4 if ctx.get("invent51") and kind in ("plan", "react") else "") + (LEARN4 if ctx.get("learn51") and kind == "plan" else "") \
        + (PROJECT4 % (" | ".join(P["kinds"]), ", ".join(P["sites"]) or "a corner of a room") if P is not None and kind == "plan" else "")


def prompt4_(kind, packet, ctx):
    if kind == "reflect" and ctx.get("spirit"):   # SPEC-v4.2 §10.2
        new = ["remember", "learned", "self", "visitor"] + ["flaw"] * bool(ctx.get("flaw")) + ["leave"] * bool(ctx.get("old"))
        words = [REFLECT_SPIRIT.get(k) or REFLECT_PARTS[k] for k in ctx["asks"]] + [REFLECT_SPIRIT[k] % ctx.get("flaw_name", "") if k == "flaw" else REFLECT_SPIRIT[k] for k in new]
        return packet + FORMAT4["reflect"] % ", ".join(words)
    if kind == "reflect":
        return packet + FORMAT4["reflect"] % ", ".join(REFLECT_PARTS[k] for k in ctx["asks"])
    usable = [a for a in ctx["allowed"] if a != "make"]
    steps = "\n".join("  " + SHORT.get(a, WRITTEN.get(a, a)) for a in usable) or "  (none just now)"
    if kind == "plan" and ctx.get("jobs5") is not None:   # SPEC-v5.0 §3.5
        form = FORMAT4["plan"].replace('"target": "<who, where or what it is about: one of the names you know, or empty>"}',
                                       '"target": "<who, where or what it is about: one of the names you know, or empty>", "for": "<what it is for: what the house needs, someone, to sell, a gift, for yourself>"}')
        form = form.replace('"steps": [<0 to 2 things to do right now; empty to simply begin>]}', '"steps": [<0 to 2 things to do right now; empty to simply begin>], '
                            '"job": {"take": "<one of the jobs the house needs done that you will see to, or empty>", "refuse": "<one you will not go near today, or empty>"}}')
        return packet + form % (" | ".join(ctx["aim_kinds"]), steps)
    if kind == "plan":
        return packet + FORMAT4["plan"] % (" | ".join(ctx["aim_kinds"]), steps)
    form = FORMAT4["react"].replace('"steps": [<0 to 2 things to do right now>]}', '"steps": [<0 to 2 things to do right now>]' + REACT_REMEMBER) if ctx.get("spirit") else FORMAT4["react"]
    return packet + form % (" | ".join(ctx["moods"]), " | ".join(ctx["aim_kinds"]), steps)


# SPEC-v3.5.3 §10: a reply with writing in another script ("resist the冲动") is asked for again, once; whatever of it is
# still there after that is taken out. Each time is noted in foreign.jsonl beside training.jsonl, to count how often.
FOREIGN = re.compile(r"[\u0370-\u03ff\u0400-\u052f\u0590-\u08ff\u0900-\u0dff\u0e00-\u0eff\u1100-\u11ff\u3000-\u30ff\u3400-\u4dbf"
                     r"\u4e00-\u9fff\ua000-\ua4cf\uac00-\ud7af\uf900-\ufaff\uff00-\uffef]+")


def foreign(text):
    return bool(FOREIGN.search(text or ""))


CONTEXT = 16384   # the model's context, in tokens (Modelfile: num_ctx)


class CutOff(Exception):
    """A reply cut off at its length twice (REVIEW-v4.0.4 C4): the thought gives up rather than ask a third time."""


def parse(reply):
    try:
        d = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", reply.strip()))
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def invalid(reply, kind, tag):
    """A reply that is not the JSON asked for (REVIEW-v4.0.4 §2.4): said, and marked on its HTTP call's row in `calls`."""
    logging.warning("invalid json: %s %s %r", kind, tag.get("pet"), reply[:120])
    calls = HTTP.get()
    if calls:
        calls[-1]["failed"] = "invalid json"
    return "invalid json"


class Model:
    instant = False

    def __init__(self, cfg, directory, tag=None):
        self.cfg, self.full = cfg["model"], cfg
        self.think = cfg["spirit"]["think_effort"]["reflect"] if K.on(cfg) else cfg["sleep"].get("think", "medium")   # (SPEC-v4.2 §3.1: the night's as the reflection's)
        if urlparse(self.cfg["endpoint"]).hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("model endpoint must be on localhost (SPEC §16)")
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.training, self.tag = Path(directory) / "training.jsonl", tag or {}
        self.s = {}   # no state of its own: each turn sees only its packet

    def post(self, body, timeout):
        """One HTTP call to the model: the whole of its answer, as JSON."""
        req = urllib.request.Request(self.cfg["endpoint"] + "/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def chat(self, prompt, schema=None, think=False, max_tokens=None, temperature=0.7, kind="act"):
        """19 October 2026 (REVIEW-v4.0.4 C4): the whole answer is read, not only its words: how it finished and its
        tokens go into the thought's rows in `calls` (log.HTTP). A reply cut off at its length is asked again with
        thinking off, or with twice the room if thinking was off already, never the same request; cut off twice, the
        thought gives up (CutOff)."""
        body = {
            "model": self.cfg["name"], "temperature": temperature, "max_tokens": max_tokens or self.cfg["max_tokens"],
            # No thinking on a waking turn (M0: a few seconds a turn). Sleep is not bound by the tick, so it thinks there.
            "reasoning_effort": (think if isinstance(think, str) else self.think) if think else "none",   # (SPEC-v4.2 §3.1: a kind may name its own effort)
            "messages": [{"role": "user", "content": prompt}],
        }
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "schema": schema}}
        calls, again, cut = HTTP.get(), False, False
        while True:
            t0 = time.monotonic()
            d = self.post(body, 600 if body["reasoning_effort"] != "none" else self.cfg["timeout_seconds"])
            choice, usage = d["choices"][0], d.get("usage") or {}
            reply, finish = choice["message"]["content"] or "", choice.get("finish_reason")
            note = {"seconds": round(time.monotonic() - t0, 2), "finish": finish, "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens")}
            if calls is not None:
                calls.append(note)
            if finish == "length":
                note["failed"] = "cut off"
                if cut:
                    logging.warning("cut off twice: %s %s %s", kind, self.tag.get("pet"), usage.get("completion_tokens"))
                    raise CutOff(kind)
                cut = True
                if body["reasoning_effort"] != "none":
                    body["reasoning_effort"], how = "none", "thinking off"
                else:
                    body["max_tokens"] = min(2 * body["max_tokens"], CONTEXT - (usage.get("prompt_tokens") or 0))
                    how = "room for %d tokens" % body["max_tokens"]
                logging.warning("cut off: %s %s %s; asked again with %s", kind, self.tag.get("pet"), usage.get("completion_tokens"), how)
                continue
            if not foreign(reply):
                break
            note["failed"] = "another script"
            logging.warning("model reply in another script (%s)%s", kind, ", again" if again else "; asking once more")
            with (self.training.parent / "foreign.jsonl").open("a") as f:
                f.write(json.dumps({**self.tag, "kind": kind, "at": time.time(), "again": again, "bits": FOREIGN.findall(reply)[:5]}) + "\n")
            if again:
                break
            again = True
        reply = FOREIGN.sub("", reply)
        with self.training.open("a") as f:   # every prompt and reply, tagged with whose it is, for a later LoRA (§14)
            f.write(json.dumps({**self.tag, "kind": kind, "prompt": prompt, "response": reply}) + "\n")
        return reply

    async def act(self, packet, ctx):
        """One waking turn: the packet in, an intention out. Returns the turn, or a string saying why there is none."""
        ask, shape, why = prompt(packet, ctx), schema(ctx), "model unreachable"
        for _ in range(2):   # one retry, then there is no new intention this time
            try:
                reply = await asyncio.to_thread(self.chat, ask, shape, False, None, ctx["temperature"])
            except CutOff:
                return "cut off"
            except Exception as e:
                logging.warning("model call failed: %r", e)
                why = "model unreachable"
                continue
            turn = parse(reply)
            if turn:
                return turn
            why = invalid(reply, "act", self.tag)
        return why

    async def think4(self, kind, packet, ctx):
        """SPEC-v4.0 §8: a plan, a reaction or the evening reflection. Returns the reply, or a string saying
        why there is none. The reflection thinks first, as the night did."""
        ask, shape, why = prompt4(kind, packet, ctx), schema4(kind, ctx), "model unreachable"
        night = kind == "reflect"
        if K.on(self.full):   # SPEC-v4.2 §3.1, §3.3: plan and reflect think, with 2000 tokens; each kind at its own warmth
            think, most, warm = K.thinking(self.full, kind)
        else:
            think, most, warm = night, self.cfg["night_tokens"] if night else None, ctx.get("temperature", 0.7)
        for _ in range(2):
            try:
                reply = await asyncio.to_thread(self.chat, ask, shape, think, most, warm, kind)
            except CutOff:
                return "cut off"
            except Exception as e:
                logging.warning("model call failed (%s): %r", kind, e)
                continue
            turn = parse(reply)
            if turn:
                return took_words(turn, packet) if night else turn
            why = invalid(reply, kind, self.tag)
        return why

    async def night(self, text, asks, belief_ids, tellers):
        """The night's thinking (§9, SPEC-v3 §3.3, §5.2, §8.2), in one call with thinking on."""
        ask = text + NIGHT % ", ".join(NIGHT_PARTS[k] for k in asks)
        return took_words(parse(await asyncio.to_thread(self.chat, ask, night_schema(asks, belief_ids, tellers), True, self.cfg["night_tokens"], 0.7, "night")) or {}, text)

    async def body(self, body, options, portrait):
        """§8: once grown, a picture of itself. (§9.3, picking one of three ways its body could change in the night, went
        with SPEC-v3.5: a body is settled at birth. `options` is always empty now; the shape of the call is kept.)"""
        part = obj(shape={"enum": SHAPES}, size={"enum": [1, 2, 3]}, color={"enum": COLORS}, at={"enum": PLACES})
        ask = 'This is your body: %s.\n\nReply with one JSON object and nothing else: {"portrait": [<a picture of yourself as you see yourself, from up to 8 parts, each %s>]}' % (body, PART)
        return parse(await asyncio.to_thread(self.chat, ask, obj(portrait={"type": "array", "items": part, "minItems": 1, "maxItems": 8}), False, None, 0.7, "body")) or {}

    async def chronicle(self, day, lines):
        """§9.4: the house's day told as one paragraph. Not a pet's voice; nothing here reaches a pet."""
        ask = ("These things happened in a house of hobs, small household spirits, on day %d:\n%s\n\n"
               "Tell the day plainly, as someone who watched it, in short sentences: one thing to a sentence, at most twelve sentences. Use only what is listed." % (day, lines))
        return (await asyncio.to_thread(self.chat, ask, None, True, 4000, 0.7, "chronicle")).strip()
