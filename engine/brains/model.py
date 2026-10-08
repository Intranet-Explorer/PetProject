"""The model brain (v1 §7, SPEC-v2 §3): a local model behind an OpenAI-compatible endpoint.
It is given its situation, its allowed actions and the output format. Nothing tells it what it is.
Settings are the ones tested in M0 (m0/model_test.py); since v2 a turn returns an intention of several steps."""
import asyncio
import json
import logging
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ..actions import MOVABLE

SHAPES = {   # how each action is written, shown only for the actions the stage allows
    "observe": '{"type": "observe"}',
    "look": '{"type": "look", "target": something visible}',
    "move": '{"type": "move", "target": object} or {"type": "move", "tile": [x, y]}',
    "speak": '{"type": "speak", "text": at most 120 chars}',
    "rest": '{"type": "rest"}',
    "use": '{"type": "use", "target": object}',
    "arrange": '{"type": "arrange", "object": object, "tile": [x, y]}',
    "write_belief": '{"type": "write_belief", "statement": text}',
    "revise_belief": '{"type": "revise_belief", "id": belief id, "statement": new text or "discard"}',
}
FORMAT = """
Reply with one JSON object and nothing else:
{"thought": "<short, why>", "intention": "<what you mean to do, in a few words>", "steps": [<2 to 5 actions, carried out in order>], "expect": "<what you expect to have happened once the steps are done>"}
"expect" must name a need (energy, comfort, curiosity) and which way it goes, or a visible change.
each step is one action:
%s
"""


def schema(allowed, objects, belief_ids):
    """Constrained output (SPEC-v2 §3): an intention of 1 to 5 steps, each step one variant per allowed action,
    built from what the packet shows. A step cannot name a locked action, leave out a parameter, or point at
    something that is not there."""
    obj = lambda **props: {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    tile = {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}
    text = {"type": "string", "minLength": 1}
    belief = {"type": "string", "minLength": 1, "maxLength": 140}
    variants = {
        "observe": [obj(type={"const": "observe"})],
        "rest": [obj(type={"const": "rest"})],
        "look": [obj(type={"const": "look"}, target={"enum": objects + ["visitor"]})],
        "move": [obj(type={"const": "move"}, target={"enum": objects}), obj(type={"const": "move"}, tile=tile)],
        "speak": [obj(type={"const": "speak"}, text={"type": "string", "minLength": 1, "maxLength": 120})],
        "use": [obj(type={"const": "use"}, target={"enum": objects})],
        "arrange": [obj(type={"const": "arrange"}, object={"enum": list(MOVABLE)}, tile=tile)],
        "write_belief": [obj(type={"const": "write_belief"}, statement=belief)],
        "revise_belief": [obj(type={"const": "revise_belief"}, id={"enum": belief_ids}, statement=belief)] if belief_ids else [],
    }
    step = {"anyOf": [v for a in allowed for v in variants[a]]}
    return obj(thought={"type": "string"}, intention=text,
               steps={"type": "array", "items": step, "minItems": 2, "maxItems": 5}, expect={"type": "string"})


CONSOLIDATE = """
Reply with one JSON object and nothing else, holding at most 3 belief changes.
Each is a short statement (under 140 characters) about how something in your world works, or about yourself; not a list of what happened:
{"changes": [{"type": "write_belief", "statement": "<text>"}, {"type": "revise_belief", "id": "<belief id>", "statement": "<new text or discard>"}]}
"""
CHANGES = {
    "type": "object",
    "properties": {"changes": {"type": "array", "items": {
        "type": "object",
        "properties": {"type": {"type": "string", "enum": ["write_belief", "revise_belief"]},
                       "id": {"type": "string"}, "statement": {"type": "string", "maxLength": 140}},
        "required": ["type", "statement"],
    }}},
    "required": ["changes"],
}


BODY = {
    "type": "object",
    "properties": {"choice": {"type": "integer", "enum": [1, 2, 3]}, "reason": {"type": "string"}},
    "required": ["choice", "reason"],
}


def parse(text):
    try:
        d = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip()))
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


class Model:
    def __init__(self, cfg, directory):
        self.cfg = cfg["model"]
        if urlparse(self.cfg["endpoint"]).hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("model endpoint must be on localhost (SPEC §16)")
        self.training = Path(directory) / "training.jsonl"
        self.s = {}   # no state of its own: each turn sees only its packet

    def chat(self, prompt, schema=None, think=False, max_tokens=None):
        body = {
            "model": self.cfg["name"], "temperature": self.cfg["temperature"],
            "max_tokens": max_tokens or self.cfg["max_tokens"],
            # No thinking on a tick (M0: about 4 s a turn). Sleep is not bound by the tick, so it thinks there.
            "reasoning_effort": "medium" if think else "none",
            "messages": [{"role": "user", "content": prompt}],
        }
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "schema": schema}}
        req = urllib.request.Request(self.cfg["endpoint"] + "/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600 if think else self.cfg["timeout_seconds"]) as r:
            reply = json.load(r)["choices"][0]["message"]["content"] or ""
        with self.training.open("a") as f:   # every prompt and response pair, for v2 LoRA
            f.write(json.dumps({"prompt": prompt, "response": reply}) + "\n")
        return reply

    async def act(self, packet):
        """One model turn: the packet in, an intention out. Returns the turn, or a string saying why there is none."""
        line = dict(l.split(": ", 1) for l in packet.splitlines() if ": " in l and not l.startswith(" "))
        allowed = line["stage"].split("allowed actions: ")[1].split(", ")
        prompt = packet + FORMAT % "\n".join("  " + SHAPES[a] for a in allowed)
        shape = schema(allowed, [o.split(" (")[0] for o in line["visible"].split(" · ")],
                       re.findall(r"^  (b\d+):", packet, re.M))
        for _ in range(2):   # one retry, then there is no new intention this time
            try:
                turn = parse(await asyncio.to_thread(self.chat, prompt, shape))
            except Exception as e:
                logging.warning("model call failed: %r", e)
                why = "model unreachable"
                continue
            if turn:
                return turn
            why = "invalid json"
        return why

    async def consolidate(self, journal, beliefs):
        """§9.1: read the day and return up to 3 belief changes. Thinking on, as M0 found it needs."""
        held = "".join("\n  %s: %s" % (b["id"], b["statement"]) for b in beliefs) or " none yet"
        prompt = "This is your journal for today:\n%s\n\nyour beliefs:%s\n%s" % (journal, held, CONSOLIDATE)
        reply = parse(await asyncio.to_thread(self.chat, prompt, CHANGES, True, 8000))
        return (reply or {}).get("changes", [])

    async def dream(self, journal):
        """§9.2: a short summary of the day in its own words."""
        prompt = "This is your journal for today:\n%s\n\nWrite two or three sentences about your day." % journal
        return await asyncio.to_thread(self.chat, prompt, None, False, 200)

    async def choose_body(self, body, options):
        """§9.3: pick one of three mutations from their descriptions, with a reason."""
        prompt = ("This is your body: %s.\nWhile you sleep it can change in one of these ways:\n%s\n\n"
                  'Reply with one JSON object and nothing else: {"choice": <1, 2 or 3>, "reason": "<short>"}'
                  % (body, "\n".join("%d. %s" % (i + 1, o) for i, o in enumerate(options))))
        reply = parse(await asyncio.to_thread(self.chat, prompt, BODY)) or {}
        if reply.get("choice") not in (1, 2, 3):
            raise ValueError("no usable body choice: %r" % reply)
        return reply["choice"] - 1, reply.get("reason", "")
