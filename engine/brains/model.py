"""The model brain (SPEC §7, SPEC-v3 §3): a local model behind an OpenAI-compatible endpoint on this machine.
It is given its situation in words, what it can do, and the shape of a reply. Nothing tells it what it is."""
import asyncio
import json
import logging
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ..actions import FOCUS, PLACES as SPOTS
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
                '"material": what either of them is like, "purpose": what it is for, up to 80 chars}} (the two become one thing; what kind it is follows from what they were)'),
    "paint": '{"type": "paint", "wall": %s, "floor": one of the same}' % "|".join(COLORS),
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
    "lay_egg": ('{"type": "lay_egg", "name": a name for your child, up to 16 chars (or "" to leave it to them), '
                '"message": what you want your child to know, in your own words, up to 600 chars; what you were told yourself is yours to pass on, change or leave out}'),
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
    "name": '{"type": "name", "what": an animal of yours here, or "egg", "name": up to 16 chars}',
    "ask_book": '{"type": "ask_book", "question": what you want to know, at most 80 chars}',
}
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
NIGHT = """
Reply with one JSON object and nothing else:
{%s}
"""
NIGHT_PARTS = {
    "dream": '"dream": "<two or three sentences about your day, in your own words>"',
    "changes": ('"changes": [<at most 3 of {"type": "write_belief", "statement": "<one short sentence of at most 200 characters, about how something works or about yourself or someone; '
                'not a list of what happened>", "source": "lived | seen | told by <who>"} or {"type": "revise_belief", "id": "<belief id>", "statement": "<new text or discard>"}>]'),
    "review": '"review": {"decision": "keep | revise | discard", "statement": "<the new text, if you revise it>"}',
    "project": '"project": {"decision": "keep | set | finish | abandon", "text": "<the project in a few of your own words, at most 130 characters, if you set one: something for the coming days>"}',
    "people": '"people": [<for anyone you want to remember something about: {"who": "<who>", "line": "<one line, in your own words>"}>]',
    "message": '"message": "<your message for your children as you would have it now, up to 600 characters; the same words again if nothing has changed. What you were told yourself is yours to pass on, change or leave out>"',
    "my_life": '"my_life": "<the story of your life, in your own words, up to 800 characters>"',
}


def obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def text(most, least=1):
    return {"type": "string", "minLength": least, "maxLength": most}


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
        "paint": [one("paint", wall={"enum": COLORS}, floor={"enum": COLORS})],
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
        "write_belief": [one("write_belief", statement=text(240), source={"enum": ["lived", "seen"] + ["told by " + t for t in c["tellers"]]})],
        "revise_belief": [one("revise_belief", id={"enum": c["beliefs"]}, statement=text(240))] if c["beliefs"] else [],
    }
    step = {"anyOf": [x for a in c["allowed"] for x in v[a]]}
    if not step["anyOf"]:
        step = {"anyOf": v["observe"]}
    if not c.get("body"):
        return obj(thought=text(340, 0), intention=text(120),
                   steps={"type": "array", "items": step, "minItems": 2, "maxItems": 5}, expect=text(230, 0))
    plain = obj(type={"enum": ["tidy", "explore", "make", "rest", "project", "play"]}, words=text(70))
    about = [obj(type={"const": "be with"}, target={"enum": c["pets"]}, words=text(70))] if c["pets"] else []
    about += [obj(type={"enum": ["tend", "stay near"]}, target={"enum": c["things"]}, words=text(70))] if c["things"] else []
    return obj(thought=text(340, 0), focus={"anyOf": [plain] + about},
               steps={"type": "array", "items": step, "minItems": 0, "maxItems": 3}, expect=text(230, 0))


def prompt(packet, ctx):
    most, reach = ctx["make"]
    kinds = sorted({k for m in reach for k in ctx["kinds"].get(m, [])})
    written = dict(WRITTEN, make=WRITTEN["make"] % ("|".join(kinds), "|".join(reach), "|".join(SIZES[:max(most, 1)])))
    usable = [a for a in ctx["allowed"] if a != "make" or (reach and most)]
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
        "message": text(640), "my_life": text(860),
    }
    return obj(**{k: parts[k] for k in asks})


def parse(reply):
    try:
        d = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", reply.strip()))
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


class Model:
    instant = False

    def __init__(self, cfg, directory, tag=None):
        self.cfg, self.think = cfg["model"], cfg["sleep"].get("think", "medium")
        if urlparse(self.cfg["endpoint"]).hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("model endpoint must be on localhost (SPEC §16)")
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.training, self.tag = Path(directory) / "training.jsonl", tag or {}
        self.s = {}   # no state of its own: each turn sees only its packet

    def chat(self, prompt, schema=None, think=False, max_tokens=None, temperature=0.7, kind="act"):
        body = {
            "model": self.cfg["name"], "temperature": temperature, "max_tokens": max_tokens or self.cfg["max_tokens"],
            # No thinking on a waking turn (M0: a few seconds a turn). Sleep is not bound by the tick, so it thinks there.
            "reasoning_effort": self.think if think else "none",
            "messages": [{"role": "user", "content": prompt}],
        }
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "schema": schema}}
        req = urllib.request.Request(self.cfg["endpoint"] + "/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600 if think else self.cfg["timeout_seconds"]) as r:
            reply = json.load(r)["choices"][0]["message"]["content"] or ""
        with self.training.open("a") as f:   # every prompt and reply, tagged with whose it is, for a later LoRA (§14)
            f.write(json.dumps({**self.tag, "kind": kind, "prompt": prompt, "response": reply}) + "\n")
        return reply

    async def act(self, packet, ctx):
        """One waking turn: the packet in, an intention out. Returns the turn, or a string saying why there is none."""
        ask, shape, why = prompt(packet, ctx), schema(ctx), "model unreachable"
        for _ in range(2):   # one retry, then there is no new intention this time
            try:
                turn = parse(await asyncio.to_thread(self.chat, ask, shape, False, None, ctx["temperature"]))
            except Exception as e:
                logging.warning("model call failed: %r", e)
                why = "model unreachable"
                continue
            if turn:
                return turn
            why = "invalid json"
        return why

    async def night(self, text, asks, belief_ids, tellers):
        """The night's thinking (§9, SPEC-v3 §3.3, §5.2, §8.2), in one call with thinking on."""
        ask = text + NIGHT % ", ".join(NIGHT_PARTS[k] for k in asks)
        return parse(await asyncio.to_thread(self.chat, ask, night_schema(asks, belief_ids, tellers), True, self.cfg["night_tokens"], 0.7, "night")) or {}

    async def body(self, body, options, portrait):
        """§9.3: pick one of three ways its body can change; once grown, also a picture of itself."""
        part = obj(shape={"enum": SHAPES}, size={"enum": [1, 2, 3]}, color={"enum": COLORS}, at={"enum": PLACES})
        shape = obj(choice={"enum": [1, 2, 3]}, reason=text(200))
        ask = ("This is your body: %s.\nWhile you sleep it can change in one of these ways:\n%s\n\n"
               'Reply with one JSON object and nothing else: {"choice": <1, 2 or 3>, "reason": "<short>"'
               % (body, "\n".join("%d. %s" % (i + 1, o) for i, o in enumerate(options))))
        if portrait:
            shape["properties"]["portrait"] = {"type": "array", "items": part, "minItems": 1, "maxItems": 8}
            shape["required"].append("portrait")
            ask += ', "portrait": [<a picture of yourself as you see yourself, from up to 8 parts, each %s>]' % PART
        reply = parse(await asyncio.to_thread(self.chat, ask + "}", shape, False, None, 0.7, "body")) or {}
        if reply.get("choice") not in (1, 2, 3):
            raise ValueError("no usable body choice: %r" % reply)
        return reply

    async def chronicle(self, day, lines):
        """§9.4: the house's day told as one paragraph. Not a pet's voice; nothing here reaches a pet."""
        ask = ("These things happened in a house of small creatures on day %d:\n%s\n\n"
               "Tell the day in one short paragraph, plainly, as someone who watched it. Use only what is listed." % (day, lines))
        return (await asyncio.to_thread(self.chat, ask, None, True, 4000, 0.7, "chronicle")).strip()
