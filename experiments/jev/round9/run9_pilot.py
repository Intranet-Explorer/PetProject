#!/usr/bin/env python3
"""Round 9 pilot: does the hobs' own brain (pet-brain, through Ollama) read a personality sheet at all?

    python3 run9_pilot.py            # asks pet-brain on this Mac (stop the house first: ./run.sh stop)
    python3 run9_pilot.py --mock     # no model needed, made-up answers, to check the script runs

6 sheets x 6 situations x 5 asks = 180 calls. The model is called the way the engine calls it on a waking turn:
/v1/chat/completions, thinking off, temperature 0.7, with a JSON shape that only allows the listed answers.
If OPENROUTER_API_KEY is set, Jev is asked the same 36 questions for comparison (about a tenth of a cent);
if not, the round 8 numbers are shown where round 8 had them. Writes pilot_results.json and pilot_report.md.
"""
import argparse, hashlib, json, os, random, statistics, sys, time, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENDPOINT = os.environ.get("PET_ENDPOINT", "http://localhost:11434/v1")
BRAIN = os.environ.get("PET_MODEL", "pet-brain")
JEV_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.14")
NAME = "Nib"
INTRO = "%s is a hob, a small creature living in a shared house with other hobs." % NAME


def who(lines):
    return (INTRO + ("\n" + "\n".join(lines) if lines else " Nothing is known about its character.")).replace("{name}", NAME)


def options(sit):
    """[(label the model answers with, what it means)], and the label that counts as the notable answer."""
    if sit["type"] == "noul":
        yes, no = ("true", "false") if sit["yes_pole"] == "A" else ("false", "true")
        return [("yes", sit["criteria"]["true"]), ("no", sit["criteria"]["false"])], ("yes" if yes == "true" else "no")
    return list(sit["criteria"].items()), sit["a"]


def prompt(lines, sit, order):
    opts, _ = options(sit)
    opts = [opts[i] for i in order]
    return "\n".join([
        who(lines), "",
        "Situation: " + sit["situation"].replace("{name}", NAME), "",
        sit["instructions"].replace("{name}", NAME),
        "Answer with what %s most likely does, as one of:" % NAME,
        *["- %s: %s" % (k, v) for k, v in opts], "",
        'Reply as JSON: {"does": "<one of the answers above>"}',
    ]), [k for k, _ in opts]


def post(url, body, headers, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode(), dict({"Content-Type": "application/json"}, **headers))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ask_brain(lines, sit, seed):
    """One ask. Returns (label or None, seconds, raw text)."""
    opts, _ = options(sit)
    order = list(range(len(opts)))
    random.Random(seed).shuffle(order)   # the order of the answers changes from ask to ask, so position cannot decide
    text, labels = prompt(lines, sit, order)
    body = {"model": BRAIN, "temperature": 0.7, "max_tokens": 60, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": text}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "reply", "schema": {
                "type": "object", "properties": {"does": {"type": "string", "enum": labels}}, "required": ["does"], "additionalProperties": False}}}}
    t0 = time.monotonic()
    d = post(ENDPOINT + "/chat/completions", body, {}, 300)
    raw = (d["choices"][0]["message"].get("content") or "").strip()
    try:
        got = json.loads(raw).get("does")
    except Exception:
        got = next((k for k in labels if k in raw.lower()), None)
    return (got if got in labels else None), time.monotonic() - t0, raw


def ask_jev(lines, sit, key):
    body = {"model": JEV_MODEL, "state": {"hob": who(lines), "situation": sit["situation"].replace("{name}", NAME)},
            "questions": {"q": {"type": sit["type"], "instructions": sit["instructions"].replace("{name}", NAME), "criteria": sit["criteria"]}}}
    try:
        a = (post(JEV_URL, body, {"Authorization": "Bearer " + key}, 60).get("answers") or {}).get("q") or {}
    except Exception as e:
        print("Jev not available (%r); carrying on without it" % e, file=sys.stderr)
        return None
    if a.get("type") == "noul":
        return a["noul"] if sit["yes_pole"] == "A" else 1 - a["noul"]
    if a.get("type") == "choice":
        return (a.get("probabilities") or {}).get(sit["a"], float(a.get("choice") == sit["a"]))
    return None


def mock(name, sit, seed):
    _, notable = options(sit)
    p = 0.15 + (int(hashlib.md5((name + sit["id"]).encode()).hexdigest(), 16) % 70) / 100
    other = next(k for k, _ in options(sit)[0] if k != notable)
    return (notable if random.Random(seed).random() < p else other), 0.0, "(mock)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--asks", type=int, default=5)
    args = ap.parse_args()
    plan = json.loads((HERE / "pilot.json").read_text())
    sheets, sits = plan["sheets"], plan["situations"]
    S = {s["id"]: s for s in sits}
    if not args.mock:
        try:
            post(ENDPOINT + "/chat/completions", {"model": BRAIN, "max_tokens": 5, "reasoning_effort": "none", "messages": [{"role": "user", "content": "Say ok."}]}, {}, 300)
        except Exception as e:
            sys.exit("Could not reach %s at %s: %r\nIs Ollama running? (ollama list should show %s)" % (BRAIN, ENDPOINT, e, BRAIN))
    total = len(sheets) * len(sits) * args.asks
    print("%d calls to %s%s..." % (total, BRAIN, " (mock)" if args.mock else ""), flush=True)
    rows, n = [], 0
    for name, lines in sheets.items():
        for s in sits:
            for k in range(args.asks):
                seed = "%s|%s|%d" % (name, s["id"], k)
                try:
                    got, secs, raw = mock(name, s, seed) if args.mock else ask_brain(lines, s, seed)
                    err = None
                except Exception as e:
                    got, secs, raw, err = None, 0.0, "", repr(e)
                rows.append({"sheet": name, "sit": s["id"], "ask": k, "answer": got, "seconds": round(secs, 2), "raw": raw[:200], "error": err})
                n += 1
                if n % 20 == 0:
                    print("  %d/%d" % (n, total), flush=True)
    key = os.environ.get("OPENROUTER_API_KEY")
    jev = {name: dict(v) for name, v in plan.get("jev_round8", {}).items()}
    jev_live = False
    if key and not args.mock:
        print("asking Jev the same %d questions..." % (len(sheets) * len(sits)), flush=True)
        for name, lines in sheets.items():
            for s in sits:
                v = ask_jev(lines, s, key)
                if v is not None:
                    jev.setdefault(name, {})[s["id"]] = v
                    jev_live = True
    (HERE / "pilot_results.json").write_text(json.dumps({"brain": BRAIN, "rows": rows, "jev": jev}, indent=1))

    def rate(name, sid):
        _, notable = options(S[sid])
        got = [r["answer"] for r in rows if r["sheet"] == name and r["sit"] == sid and r["answer"] is not None]
        return (sum(a == notable for a in got) / len(got), len(got)) if got else (None, 0)

    ok = sum(r["answer"] is not None for r in rows)
    errs = sum(r["error"] is not None for r in rows)
    secs = [r["seconds"] for r in rows if r["error"] is None]
    mixed = sum(1 for name in sheets for s in sits if len({r["answer"] for r in rows if r["sheet"] == name and r["sit"] == s["id"] and r["answer"]}) > 1)
    f = lambda x: "  - " if x is None else "%.2f" % x
    out = ["# Round 9 pilot: %s%s" % (BRAIN, " (MOCK DATA)" if args.mock else ""), "",
           "%d calls. Usable answers: **%d of %d**. Calls that failed outright: %d." % (len(rows), ok, len(rows), errs),
           "Time per call: median %.1f s, slowest %.1f s. At that speed a full run of 8,000 calls takes about %.1f hours." % (
               statistics.median(secs) if secs else 0, max(secs) if secs else 0, (statistics.median(secs) if secs else 0) * 8000 / 3600),
           "Sheet and situation pairs where the %d asks did not all agree: %d of %d. (0 would mean it answers the same every time.)" % (args.asks, mixed, len(sheets) * len(sits)), "",
           "## 1. Did the obvious lines move it?", "",
           "Each row is one line that Jev reads strongly. **Pass** means the brain moved the same way against the blank hob.", "",
           "| sheet | situation | should be | blank hob | this hob | Jev: blank | Jev: this hob | |", "|---|---|---|---|---|---|---|---|"]
    passed = 0
    for name, sid, way in plan["expect"]:
        b, _ = rate("blank", sid)
        h, _ = rate(name, sid)
        good = b is not None and h is not None and ((h > b) if way == "higher" else (h < b))
        passed += good
        out.append("| %s | %s: %s | %s | %s | %s | %s | %s | %s |" % (name, sid, S[sid]["instructions"].replace("{name}", NAME), way, f(b), f(h),
                                                                 f(jev.get("blank", {}).get(sid)), f(jev.get(name, {}).get(sid)), "**pass**" if good else "miss"))
    out += ["", "Passed: **%d of %d**." % (passed, len(plan["expect"])), "",
            "## 2. Everything", "",
            "How often each hob gave the notable answer (%d asks each), with Jev's number after the slash where there is one%s." % (
                args.asks, "" if jev_live else " (from round 8; set OPENROUTER_API_KEY to have Jev asked for every cell)"), "",
            "| sheet | " + " | ".join(s["id"] for s in sits) + " |", "|---|" + "---|" * len(sits)]
    pairs = []
    for name in sheets:
        cells = []
        for s in sits:
            r, _ = rate(name, s["id"])
            j = jev.get(name, {}).get(s["id"])
            cells.append("%s / %s" % (f(r), f(j)))
            if r is not None and j is not None:
                pairs.append((r, j))
        out.append("| %s | " % name + " | ".join(cells) + " |")
    if len(pairs) >= 6:
        mr, mj = statistics.mean(a for a, _ in pairs), statistics.mean(b for _, b in pairs)
        den = (sum((a - mr) ** 2 for a, _ in pairs) * sum((b - mj) ** 2 for _, b in pairs)) ** 0.5
        if den:
            out += ["", "Agreement with Jev over the %d cells that have both: correlation **%.2f**, average gap %.2f. (With %d asks a cell can only be a multiple of %.2f, so this is rough.)" % (
                len(pairs), sum((a - mr) * (b - mj) for a, b in pairs) / den, statistics.mean(abs(a - b) for a, b in pairs), args.asks, 1 / args.asks)]
    out += ["", "## 3. The situations", ""] + ["- **%s**: %s %s" % (s["id"], s["situation"].replace("{name}", NAME), s["instructions"].replace("{name}", NAME)) for s in sits]
    out += ["", "## 4. The sheets", ""] + ["- **%s**: %s" % (name, " | ".join(lines) if lines else "(nothing known)") for name, lines in sheets.items()]
    bad = [r for r in rows if r["answer"] is None][:5]
    if bad:
        out += ["", "## 5. Answers that could not be used (first few)", ""] + ["- %s on %s: `%s` %s" % (r["sheet"], r["sit"], r["raw"][:120], r["error"] or "") for r in bad]
    (HERE / "pilot_report.md").write_text("\n".join(out) + "\n")
    print("Done. %d of %d usable, %d of %d obvious lines passed. Report: %s" % (ok, len(rows), passed, len(plan["expect"]), HERE / "pilot_report.md"))


if __name__ == "__main__":
    main()
