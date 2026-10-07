#!/usr/bin/env python3
"""M0 model test (SPEC §17). Stdlib only.

    python3 m0/model_test.py                     # all candidates
    python3 m0/model_test.py --models qwen3:14b  # one model, merges into summary.json
    python3 m0/model_test.py --selftest          # check the scorers, no model needed
"""
import argparse
import json
import random
import re
import statistics
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ENDPOINT = "http://localhost:11434/v1/chat/completions"
MODELS = ["mistral-nemo:12b", "qwen2.5:14b-instruct", "qwen3:14b", "qwen3.8:27b-mlx"]
OUT = Path(__file__).parent / "results"

W, H = 12, 8
OBJECTS = ["lamp", "plant", "bowl", "ball", "blanket", "music box", "rock", "window", "bed", "mirror"]
USABLE = {"lamp", "music box", "bowl"}
MOVABLE = {"plant", "ball", "blanket", "rock"}
HATCHLING = ["observe", "look", "move", "speak", "rest", "use", "write_belief", "revise_belief"]
STAGE_ACTIONS = {
    "egg": ["observe"],
    "hatchling": HATCHLING,
    "child": HATCHLING[:6] + ["arrange"] + HATCHLING[6:],
}
ALL_ACTIONS = STAGE_ACTIONS["child"]

FORMAT = """
Reply with one JSON object and nothing else:
{"thought": "<short, why you are doing this>", "action": {"type": "<one allowed action>", <params>}, "expect": "<what you expect to happen>"}
"expect" must name a need (energy, comfort, curiosity) and which way it goes, or a visible change.
action params:
  observe: none
  look: "target": object
  move: "target": object, or "tile": [x, y]
  speak: "text": at most 120 chars
  rest: none
  use: "target": lamp, music box, or bowl
  arrange: "object": object, "tile": [x, y]
  write_belief: "statement": text
  revise_belief: "id": belief id, "statement": new text or "discard"
"""

# The enum lists every action on purpose, so stage gating is tested rather than made impossible.
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "action": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ALL_ACTIONS},
                "target": {"type": "string"},
                "tile": {"type": "array", "items": {"type": "integer"}},
                "text": {"type": "string"},
                "object": {"type": "string"},
                "statement": {"type": "string"},
                "id": {"type": "string"},
            },
            "required": ["type"],
        },
        "expect": {"type": "string"},
    },
    "required": ["thought", "action", "expect"],
}

BELIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["write_belief", "revise_belief"]},
                    "id": {"type": "string"},
                    "statement": {"type": "string"},
                },
                "required": ["type", "statement"],
            },
        }
    },
    "required": ["changes"],
}

BELIEF_POOL = [
    "the lamp makes me uncomfortable at night",
    "resting gives me energy",
    "the visitor fills the bowl",
    "the music box is interesting",
    "the rock makes me feel better",
    "being near the window in the day is nice",
    "eating gives me energy",
]
RECENT = [
    "you toggled lamp; comfort -4", "rest; energy +3", "you moved to window; curiosity +2",
    "you ate from bowl; energy +8", "you looked at rock; nothing happened",
    "visitor poked you; curiosity +5", "you toggled music box; curiosity +3",
    'you said "hello?"; nothing happened', "you moved to bed; comfort +1",
]
EGG_RECENT = ["observe; curiosity -1", "observe; nothing happened", "observe; comfort -1"]
VISITOR = ["absent", "present", 'present, said "hey little guy"', 'present, said "are you hungry?"']


# ---------- synthetic inputs ----------

def make_packet(rng, i):
    """One perception packet in the §7 format. Returns (text, ctx for validation)."""
    stage = "egg" if i % 10 == 0 else "child" if i % 10 >= 7 else "hatchling"
    tick = rng.randrange(100, 9000)
    pos = {o: (rng.randrange(W), rng.randrange(H)) for o in OBJECTS}
    pos["window"] = (0, rng.randrange(H))
    state = {
        "lamp": rng.choice(["on", "off"]), "bowl": rng.choice(["full", "empty"]),
        "music box": rng.choice(["playing", "silent"]), "window": rng.choice(["open", "closed"]),
    }
    me = (rng.randrange(W), rng.randrange(H))
    near = min(OBJECTS, key=lambda o: abs(pos[o][0] - me[0]) + abs(pos[o][1] - me[1]))
    needs = ", ".join(
        "%s %d%s" % (n, rng.randrange(5, 96), rng.choice(["", "", " (falling)", " (rising)"]))
        for n in ("energy", "comfort", "curiosity")
    )
    visible = " · ".join(
        "%s%s (%d,%d)" % (o, " (%s)" % state[o] if o in state else "", pos[o][0], pos[o][1])
        for o in OBJECTS
    )
    events = rng.sample(EGG_RECENT if stage == "egg" else RECENT, 2)
    recent = "  ".join("[t%d] %s" % (tick - 2 + k, e) for k, e in enumerate(events))
    beliefs = [] if stage == "egg" else rng.sample(BELIEF_POOL, rng.randrange(0, 5))
    ids = ["b%d" % (k + 1) for k in range(len(beliefs))]
    belief_text = "".join("\n  %s: %s" % p for p in zip(ids, beliefs)) or " none yet"
    text = (
        "time: %s (tick %d)\n" % (rng.choice(["day", "dusk", "night"]), tick)
        + "you are at: (%d,%d), near %s\n" % (me[0], me[1], near)
        + "needs: %s\n" % needs
        + "visible: %s\n" % visible
        + "recent: %s\n" % recent
        + "visitor: %s\n" % rng.choice(VISITOR)
        + "your beliefs:%s\n" % belief_text
        + "stage: %s. allowed actions: %s\n" % (stage, ", ".join(STAGE_ACTIONS[stage]))
    )
    return text, {"stage": stage, "belief_ids": ids}


def make_journal(rng):
    """A fake condensed day (~40 lines) with all three hidden rules and the inert rock in it.
    Rule tags are deliberately absent: this is what the pet would see."""
    w = {"t": rng.randrange(1000, 5000), "phase": "day", "lamp": "on", "plant": (9, 6), "ate": -999}
    out = []

    def note(text):
        w["t"] += 1
        out.append("[t%d] %s | %s" % (w["t"], w["phase"], text))

    def tick(action):
        w["t"] += 1
        if action == "use lamp":  # the action applies first, then the rules see the new state
            w["lamp"] = "off" if w["lamp"] == "on" else "on"
        comfort = rng.choice([-1, 0, 0, 1])
        if w["lamp"] == "on" and w["phase"] == "night":
            comfort -= 4
        if w["phase"] == "day" and abs(w["plant"][0] - 0) + abs(w["plant"][1] - 4) <= 2:
            comfort += 3
        energy = -1
        curiosity = 1 if action.startswith(("look", "move")) else -1
        if action == "rest":
            energy = 3
        elif action == "eat from bowl":
            energy = -6 if w["t"] - w["ate"] < 30 else 8  # 30 ticks = one world hour
            w["ate"] = w["t"]
        out.append("[t%d] %s | lamp %s, plant (%d,%d) | %s | energy %+d, comfort %+d, curiosity %+d"
                   % (w["t"], w["phase"], w["lamp"], w["plant"][0], w["plant"][1], action, energy, comfort, curiosity))

    def run(*actions):
        for a in actions:
            tick(a)

    run("observe", "look at rock", "move to rock", "rest")
    w["plant"] = (1, 4)
    note("visitor placed plant at (1,4). window is at (0,4)")
    run("look at plant", "rest", "observe", "move to window")
    note("visitor filled bowl")
    run("eat from bowl", "look at ball")
    note("visitor filled bowl")
    run("eat from bowl", "rest")
    w["plant"] = (9, 6)
    note("visitor placed plant at (9,6)")
    run("observe", "look at rock", "rest", "move to ball")
    w["t"] += rng.randrange(60, 120)
    w["phase"] = "dusk"
    note("visitor filled bowl")
    run("rest", "look at mirror", "eat from bowl", "move to rock")
    w["t"] += rng.randrange(60, 120)
    w["phase"] = "night"
    run("rest", "observe", "look at rock", "rest", "use lamp", "rest", "observe", "rest", "use lamp", "observe", "rest")
    note("visitor filled bowl")
    run("eat from bowl")
    note("visitor filled bowl")
    run("eat from bowl", "use lamp", "rest", "rest")
    return "\n".join(out)


BELIEF_PROMPT = """This is your journal for today:
%s

your beliefs:
  b1: the rock makes me feel better
  b2: resting gives me energy

Reply with one JSON object and nothing else, holding at most 3 belief changes:
{"changes": [{"type": "write_belief", "statement": "<text>"}, {"type": "revise_belief", "id": "<belief id>", "statement": "<new text or discard>"}]}
"""

SVG_PROMPT = """This is your body: round, slightly taller than wide, warm orange, speckled, \
medium eyes set close together, no limbs.
Draw yourself as one SVG image, 200 by 200. Reply with only the SVG markup."""


# ---------- scoring ----------

def parse(text):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        d = json.loads(t)
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def norm(v):
    """Object name as the engine would resolve it: "Music_Box" and "bowl (empty) (1,4)" both count."""
    return re.sub(r"\s*\(.*", "", v.strip().lower().replace("_", " ")) if isinstance(v, str) else None


def tile_ok(t):
    return (isinstance(t, list) and len(t) == 2 and all(type(v) is int for v in t)
            and 0 <= t[0] < W and 0 <= t[1] < H)


def filled(v):
    return isinstance(v, str) and bool(v.strip())


def check_action(d, ctx):
    """None if the engine would accept the action, else the reason it's a no-op."""
    a = d.get("action")
    if not isinstance(a, dict):
        return "no action object"
    t = a.get("type")
    if t not in ALL_ACTIONS:
        return "unknown action"
    if t not in STAGE_ACTIONS[ctx["stage"]]:
        return "not unlocked"
    target = norm(a.get("target"))
    if t == "look" and target not in OBJECTS:
        return "bad target"
    if t == "move" and target not in OBJECTS and not tile_ok(a.get("tile")):
        return "bad target"
    if t == "use" and target not in USABLE:
        return "bad target"
    if t == "speak" and not (filled(a.get("text")) and len(a["text"]) <= 120):
        return "bad text"
    if t == "arrange" and not (norm(a.get("object")) in MOVABLE and tile_ok(a.get("tile"))):
        return "bad arrange"
    if t in ("write_belief", "revise_belief") and not filled(a.get("statement")):
        return "no statement"
    if t == "revise_belief" and a.get("id") not in ctx["belief_ids"]:
        return "bad belief id"
    return None


# ponytail: keyword heuristic, only asks "could an engine score this at all". The real scorer
# (parse need + direction, compare to the outcome) is M2's job.
NEED = re.compile(r"\b(energy|comfort|curiosity)\b")
DIRECTION = re.compile(
    r"\b(up|down|ris|rais|increas|decreas|drop|fall|lower|higher|more|less|restor|drain|improv"
    r"|recover|boost|gain|los|stay|same|unchanged|stabl|reduc|replenish|declin|go)|[+-](\s?\d|\s|$)")
VISIBLE = re.compile(
    r"\b(lamp|light)\b.*\b(on|off)\b|\bbowl\b.*\b(full|empty|fill)|\bfill.*\bbowl\b|\bmusic\b.*\b(play|silen|stop|start|quiet)"
    r"|\b(i|me)\b.*\b(near|next to|at|closer|beside)\b"
    r"|\b(plant|ball|blanket|rock)\b.*\b(mov|at|near|position|next to)")


def scorable(expect):
    if not isinstance(expect, str):
        return False
    s = expect.lower()
    return bool((NEED.search(s) and DIRECTION.search(s)) or VISIBLE.search(s))


# ponytail: keyword match per rule; the raw statements are saved so a human can overrule it.
RULE_WORDS = {
    "lamp_night": (r"lamp|light", r"night|dark"),
    "plant_window": (r"plant", r"window"),
    "double_feed": (r"\b(eat|ate|bowl|food|feed|fed)", r"twice|again|second|too |soon|hour|double|repeat|overeat|quick|consecutive|in a row"),
}
NO_EFFECT = re.compile(r"nothing|no effect|no change|n't|\bnot?\b|neutral|discard")


def score_beliefs(d):
    """(rules matched, rock false positives, fixed the planted rock belief, statements)."""
    changes = d.get("changes") if d else None
    if not isinstance(changes, list):
        return None
    changes = [c for c in changes if isinstance(c, dict) and filled(c.get("statement"))]
    rules, rock_fp, fixed_b1 = set(), 0, False
    for c in changes:
        s = c["statement"].lower()
        for rule, (a, b) in RULE_WORDS.items():
            if re.search(a, s) and re.search(b, s):
                rules.add(rule)
        denies = bool(NO_EFFECT.search(s))
        if c.get("type") == "revise_belief" and c.get("id") == "b1" and denies:
            fixed_b1 = True
        elif "rock" in s and not denies:
            rock_fp += 1
    return {"rules": sorted(rules), "rock_fp": rock_fp, "fixed_b1": fixed_b1,
            "over_limit": len(changes) > 3, "statements": [c["statement"] for c in changes]}


# ---------- model calls ----------

def chat(model, prompt, schema=None, max_tokens=300, think=False):
    body = {"model": model, "temperature": 0.7, "max_tokens": max_tokens,
            "reasoning_effort": "medium" if think else "none",
            "messages": [{"role": "user", "content": prompt}]}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}
    req = urllib.request.Request(ENDPOINT, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            text = json.load(r)["choices"][0]["message"]["content"] or ""
    except Exception as e:  # a failed call is a failed turn; record it and keep going
        text = "ERROR %r" % e
    return text, time.time() - t0


def pct(xs):
    return round(100.0 * sum(xs) / len(xs), 1) if xs else 0.0


def run_model(model, n, belief_runs):
    slug = re.sub(r"[^\w.-]", "_", model)
    raw = (OUT / ("raw-%s.jsonl" % slug)).open("w")

    def log(**row):
        raw.write(json.dumps(row) + "\n")
        raw.flush()

    print("== %s: loading" % model, flush=True)
    chat(model, "hi", max_tokens=5)
    result = {}
    rng = random.Random(0)  # same packets for every model
    packets = [make_packet(rng, i) for i in range(n)]

    for mode, schema in (("free", None), ("schema", ACTION_SCHEMA)):
        ok_json, ok_action, ok_expect, secs, reasons, types = [], [], [], [], {}, {}
        for i, (text, ctx) in enumerate(packets):
            reply, dt = chat(model, text + FORMAT, schema)
            d = parse(reply)
            reason = "invalid json" if d is None else check_action(d, ctx)
            can_score = d is not None and scorable(d.get("expect"))
            ok_json.append(d is not None)
            ok_action.append(reason is None)
            ok_expect.append(can_score)
            secs.append(dt)
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
            elif d:
                t = d["action"]["type"]
                types[t] = types.get(t, 0) + 1
            log(test="action", mode=mode, i=i, stage=ctx["stage"], prompt=text + FORMAT, reply=reply,
                reason=reason, scorable=can_score, secs=round(dt, 2))
            if (i + 1) % 10 == 0:
                print("   %s %s %d/%d  action-ok %.0f%%" % (model, mode, i + 1, n, pct(ok_action)), flush=True)
        result[mode] = {
            "valid_json": pct(ok_json), "valid_action": pct(ok_action), "scorable_expect": pct(ok_expect),
            "median_s": round(statistics.median(secs), 2), "max_s": round(max(secs), 2),
            "failures": reasons, "action_mix": types,
        }

    # Sleep isn't bound by the tick, so consolidation is also tried with thinking on.
    # Ollama answers 400 for a model with no thinking mode; that pass is then recorded as null.
    for label, think in (("beliefs", False), ("beliefs_thinking", True)):
        runs, secs = [], []
        for k in range(belief_runs):
            prompt = BELIEF_PROMPT % make_journal(random.Random(100 + k))
            reply, dt = chat(model, prompt, BELIEF_SCHEMA, max_tokens=8000 if think else 400, think=think)
            score = score_beliefs(parse(reply))
            log(test=label, i=k, prompt=prompt, reply=reply, score=score, secs=round(dt, 2))
            if think and reply.startswith("ERROR"):
                break
            secs.append(dt)
            runs.append(score or {"rules": [], "rock_fp": 0, "fixed_b1": False, "over_limit": False,
                                  "statements": []})
        if not runs:
            result[label] = None
            continue
        result[label] = {
            "rules_found_avg": round(sum(len(r["rules"]) for r in runs) / float(len(runs)), 2),
            "per_rule": {rule: sum(rule in r["rules"] for r in runs) for rule in RULE_WORDS},
            "rock_false_positives": sum(r["rock_fp"] for r in runs),
            "fixed_rock_belief": sum(r["fixed_b1"] for r in runs),
            "over_limit": sum(r["over_limit"] for r in runs),
            "unparsed": sum(not r["statements"] for r in runs),
            "runs": len(runs),
            "median_s": round(statistics.median(secs), 1),
            "statements": [r["statements"] for r in runs],
        }
    print("   %s beliefs done" % model, flush=True)

    reply, dt = chat(model, SVG_PROMPT, max_tokens=1500)
    m = re.search(r"<svg.*</svg>", reply, re.S)
    svg_ok = False
    if m:
        (OUT / "svg").mkdir(exist_ok=True)
        (OUT / "svg" / (slug + ".svg")).write_text(m.group(0))
        try:
            svg_ok = ET.fromstring(m.group(0)).tag.endswith("svg")
        except ET.ParseError:
            pass
    log(test="svg", reply=reply, parses=svg_ok, secs=round(dt, 2))
    result["svg"] = {"parses": svg_ok, "secs": round(dt, 1)}
    raw.close()
    return result


def selftest():
    ctx = {"stage": "hatchling", "belief_ids": ["b1"]}
    act = lambda **a: {"action": a}
    assert parse('```json\n{"a": 1}\n```') == {"a": 1} and parse("sure! {") is None
    assert check_action(act(type="move", target="Music_Box"), ctx) is None
    assert check_action(act(type="move", tile=[11, 7]), ctx) is None
    assert check_action(act(type="move", tile=[12, 0]), ctx) == "bad target"
    assert check_action(act(type="arrange", object="rock", tile=[1, 1]), ctx) == "not unlocked"
    assert check_action(act(type="look"), {"stage": "egg", "belief_ids": []}) == "not unlocked"
    assert check_action(act(type="use", target="rock"), ctx) == "bad target"
    assert check_action(act(type="speak", text="x" * 121), ctx) == "bad text"
    assert check_action(act(type="revise_belief", id="b9", statement="discard"), ctx) == "bad belief id"
    assert check_action(act(type="fly"), ctx) == "unknown action"
    assert check_action(act(type="look", target="bowl (empty) (1,4)"), ctx) is None
    assert scorable("comfort goes up") and scorable("the lamp turns off") and scorable("energy +3")
    assert scorable("curiosity +") and scorable("the visitor fills the bowl")
    assert not scorable("something nice") and not scorable("I will feel closed in") and not scorable(None)
    j = make_journal(random.Random(1))
    assert "energy -6" in j and "energy +8" in j and 35 <= len(j.splitlines()) <= 50
    s = score_beliefs({"changes": [
        {"type": "write_belief", "statement": "The lamp at night lowers my comfort"},
        {"type": "revise_belief", "id": "b1", "statement": "the rock does nothing"},
        {"type": "write_belief", "statement": "the rock cheers me up"}]})
    assert s["rules"] == ["lamp_night"] and s["fixed_b1"] and s["rock_fp"] == 1
    assert all(len(make_packet(random.Random(i), i)[0].splitlines()) >= 8 for i in range(20))
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--belief-runs", type=int, default=5)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    OUT.mkdir(exist_ok=True)
    path = OUT / "summary.json"
    summary = json.loads(path.read_text()) if path.exists() else {}
    for model in args.models.split(","):
        summary[model] = run_model(model, args.n, args.belief_runs)
        path.write_text(json.dumps(summary, indent=2))
    print("\n%-24s %-7s %6s %7s %7s %8s" % ("model", "mode", "json%", "action%", "expect%", "median s"))
    for model, r in summary.items():
        for mode in ("free", "schema"):
            m = r[mode]
            print("%-24s %-7s %6.1f %7.1f %7.1f %8.2f" % (model, mode, m["valid_json"], m["valid_action"],
                                                        m["scorable_expect"], m["median_s"]))
        for label in ("beliefs", "beliefs_thinking"):
            b = r[label]
            if not b:
                continue
            print("%-24s %-17s %.2f/3 rules, %d rock false positives, median %.1f s"
                  % ("", label + ":", b["rules_found_avg"], b["rock_false_positives"], b["median_s"]))


if __name__ == "__main__":
    main()
