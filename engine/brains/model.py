"""The model brain (SPEC §7, SPEC-v3 §3): a local model behind an OpenAI-compatible endpoint on this machine.
It is given its situation in words, what it can do, and the shape of a reply. Nothing tells it what it is."""
import asyncio
import json
import logging
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ..actions import PLACES as SPOTS
from ..things import COLORS, DO, PLACES, SHAPES, WHEN

PART = '{"shape": %s, "size": 1 to 3, "color": %s, "at": %s}' % ("|".join(SHAPES), "|".join(COLORS), "|".join(PLACES))
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
    "make": ('{"type": "make", "recipe": {"name": up to 24 chars, "parts": [1 to %%d of %s] (each part uses up one bit you carry), '
             '"material": what it will be like, one of %%s, "purpose": what it is for, up to 80 chars}, "near": a thing here, or "here"}' % PART),
    "unmake": '{"type": "unmake", "target": a made thing that is yours to take apart}',
    "arrange": '{"type": "arrange", "object": something that can be moved, "near": a thing here, or "here"}',
    "combine": ('{"type": "combine", "a": a made thing, "b": another, "recipe": {"name": up to 24 chars, '
                '"material": what either of them is like, "purpose": what it is for, up to 80 chars}}'),
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
                '"message": what you want your child to know, in your own words, up to 600 chars}'),
    "bequeath": '{"type": "bequeath", "what": a thing of yours here, "to": a child\'s name, or "my children"}',
    "write_belief": '{"type": "write_belief", "statement": text, "source": how you know it: lived | seen | told by <who>}',
    "revise_belief": '{"type": "revise_belief", "id": belief id, "statement": new text or "discard"}',
}
FORMAT = """
Reply with one JSON object and nothing else:
{"thought": "<short, why>", "intention": "<what you mean to do, in a few words>", "steps": [<2 to 5 of the things you can do, carried out in order>], "expect": "<how you expect to feel once the steps are done, or what you expect to see>"}
each step is one of:
%s
"""
NIGHT = """
Reply with one JSON object and nothing else:
{%s}
"""
NIGHT_PARTS = {
    "dream": '"dream": "<two or three sentences about your day, in your own words>"',
    "changes": ('"changes": [<at most 3 of {"type": "write_belief", "statement": "<one short sentence, about how something works or about yourself or someone; '
                'not a list of what happened>", "source": "lived | seen | told by <who>"} or {"type": "revise_belief", "id": "<belief id>", "statement": "<new text or discard>"}>]'),
    "review": '"review": {"decision": "keep | revise | discard", "statement": "<the new text, if you revise it>"}',
    "project": '"project": {"decision": "keep | set | finish | abandon", "text": "<the project in a few of your own words, if you set one: something for the coming days>"}',
    "people": '"people": [<for anyone you want to remember something about: {"who": "<who>", "line": "<one line, in your own words>"}>]',
    "message": '"message": "<your message for your children as you would have it now, up to 600 characters; the same words again if nothing has changed>"',
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
    part = obj(shape={"enum": SHAPES}, size={"enum": [1, 2, 3]}, color={"enum": COLORS}, at={"enum": PLACES})
    recipe = obj(name=text(24), parts={"type": "array", "items": part, "minItems": 1, "maxItems": max(most, 1)},
                 material={"enum": reach}, purpose=text(80))
    near = {"enum": c["things"] + ["here"]}
    one = lambda t, **p: obj(type={"const": t}, **p)
    v = {
        "observe": [one("observe")], "rest": [one("rest")],
        "look": [one("look", target={"enum": visible + ["visitor"]})],
        "move": [one("move", to={"enum": c["things"] + anyone + list(SPOTS)})],
        "go": [one("go", door={"enum": c["doors"]})],
        "speak": [one("speak", text=text(120))] + ([one("speak", text=text(120), to={"enum": awake + ["visitor"]})] if awake else []),
        "use": [one("use", target={"enum": c["things"]})],
        "gather": [one("gather", what={"enum": c["bits"]})] if c["bits"] else [],
        "drop": [one("drop", what={"enum": c["carrying"]})] if c["carrying"] else [],
        "make": [one("make", recipe=recipe, near=near)] if reach and most else [],
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
        "bequeath": [one("bequeath", what={"enum": c["mine"]}, to={"enum": c["kids"] + ["my children"]})] if c["mine"] else [],
        "write_belief": [one("write_belief", statement=text(240), source={"enum": ["lived", "seen"] + ["told by " + t for t in c["tellers"]]})],
        "revise_belief": [one("revise_belief", id={"enum": c["beliefs"]}, statement=text(240))] if c["beliefs"] else [],
    }
    step = {"anyOf": [x for a in c["allowed"] for x in v[a]]}
    return obj(thought=text(340, 0), intention=text(120),
               steps={"type": "array", "items": step, "minItems": 2, "maxItems": 5}, expect=text(230, 0))


def prompt(packet, ctx):
    most, reach = ctx["make"]
    written = dict(WRITTEN, make=WRITTEN["make"] % (max(most, 1), "|".join(reach)))
    usable = [a for a in ctx["allowed"] if a != "make" or (reach and most)]
    return packet + FORMAT % "\n".join("  " + written[a] for a in usable)


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
