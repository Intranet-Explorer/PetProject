"""The model brain (SPEC §7): a local model behind an OpenAI-compatible endpoint.
It is given its situation, its allowed actions and the output format. Nothing tells it what it is.
The prompt and settings are the ones tested in M0 (m0/model_test.py)."""
import asyncio
import json
import logging
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

FORMAT = """
Reply with one JSON object and nothing else:
{"thought": "<short, why you are doing this>", "action": {"type": "<one allowed action>", <params>}, "expect": "<what you expect to happen>"}
"expect" must name a need (energy, comfort, curiosity) and which way it goes, or a visible change.
action params:
  observe: none
  look: "target": something visible
  move: "target": object, or "tile": [x, y]
  speak: "text": at most 120 chars
  rest: none
  use: "target": object
  arrange: "object": object, "tile": [x, y]
  write_belief: "statement": text
  revise_belief: "id": belief id, "statement": new text or "discard"
"""


def schema(allowed):
    """Constrained output. Only the stage's own actions are offered, so gating cannot be violated by accident."""
    return {
        "type": "object",
        "properties": {
            "thought": {"type": "string"},
            "action": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": allowed},
                    "target": {"type": "string"}, "tile": {"type": "array", "items": {"type": "integer"}},
                    "text": {"type": "string"}, "object": {"type": "string"},
                    "statement": {"type": "string"}, "id": {"type": "string"},
                },
                "required": ["type"],
            },
            "expect": {"type": "string"},
        },
        "required": ["thought", "action", "expect"],
    }


CONSOLIDATE = """
Reply with one JSON object and nothing else, holding at most 3 belief changes. Keep each statement short:
{"changes": [{"type": "write_belief", "statement": "<text>"}, {"type": "revise_belief", "id": "<belief id>", "statement": "<new text or discard>"}]}
"""
CHANGES = {
    "type": "object",
    "properties": {"changes": {"type": "array", "items": {
        "type": "object",
        "properties": {"type": {"type": "string", "enum": ["write_belief", "revise_belief"]},
                       "id": {"type": "string"}, "statement": {"type": "string"}},
        "required": ["type", "statement"],
    }}},
    "required": ["changes"],
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
        prompt = packet + FORMAT
        allowed = packet.rsplit("allowed actions: ", 1)[1].strip().split(", ")
        for _ in range(2):   # one retry, then the turn is a no-op
            try:
                turn = parse(await asyncio.to_thread(self.chat, prompt, schema(allowed)))
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
