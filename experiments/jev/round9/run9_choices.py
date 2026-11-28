#!/usr/bin/env python3
"""Round 9, choices: real decision points from the house, with the options the autopilot had, put to pet-brain.

    python3 run9_choices.py            # asks pet-brain on this Mac (about 850 calls)
    python3 run9_choices.py --mock     # made-up answers, to check the script runs

Each of 150 moments from a copy of the live house is asked up to six ways: with no sheet, with a pursuit that one of
the options serves, with a fear of one of the options, with a favourite place one of the doors leads to, and with
two full random sheets. Same options, same order, only the sheet lines differ. Writes choices_results.json and
choices_report.md.
"""
import argparse, collections, hashlib, json, os, random, statistics, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENDPOINT = os.environ.get("PET_ENDPOINT", "http://localhost:11434/v1")
BRAIN = os.environ.get("PET_MODEL", "pet-brain")


def post(body, timeout=600):
    req = urllib.request.Request(ENDPOINT + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ask(d):
    body = {"model": BRAIN, "temperature": 0.7, "max_tokens": 120, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": d["prompt"]}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "reply", "schema": {
                "type": "object", "properties": {"does": {"type": "string", "enum": d["labels"]}, "why": {"type": "string"}},
                "required": ["does", "why"], "additionalProperties": False}}}}
    t0 = time.monotonic()
    r = post(body)
    raw = (r["choices"][0]["message"].get("content") or "").strip()
    try:
        j = json.loads(raw)
        got, why = j.get("does"), str(j.get("why") or "")
    except Exception:
        got, why = None, raw[:120]
    return (got if got in d["labels"] else None), why, time.monotonic() - t0, (r.get("usage") or {}).get("prompt_tokens")


def mock(d, k):
    r = random.Random(d["id"] + str(k))
    w = [3.0 if o["adj"] > 0 else 0.2 if o["adj"] < 0 else 1.0 for o in d["opts"]]
    return r.choices(d["labels"], w)[0], "(mock)", 0.0, 300


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="only the first N moments")
    args = ap.parse_args()
    D = json.loads((HERE / "decisions.json").read_text())
    if args.limit:
        D = [d for d in D if d["point"] < args.limit]
    if not args.mock:
        try:
            post({"model": BRAIN, "max_tokens": 5, "reasoning_effort": "none", "messages": [{"role": "user", "content": "Say ok."}]}, 300)
        except Exception as e:
            sys.exit("Could not reach %s at %s: %r" % (BRAIN, ENDPOINT, e))
    again = [d for d in D if d["cond"] == "none"][:80]   # the same question a second time: does it answer the same?
    jobs = [(d, 0) for d in D] + [(d, 1) for d in again]
    print("%d calls to %s%s..." % (len(jobs), BRAIN, " (mock)" if args.mock else ""), flush=True)
    rows = []
    for n, (d, k) in enumerate(jobs, 1):
        try:
            got, why, secs, ptok = mock(d, k) if args.mock else ask(d)
            err = None
        except Exception as e:
            got, why, secs, ptok, err = None, "", 0.0, None, repr(e)
        rows.append({"id": d["id"], "ask": k, "does": got, "why": why[:200], "seconds": round(secs, 2), "prompt_tokens": ptok, "error": err})
        if n % 50 == 0:
            print("  %d/%d" % (n, len(jobs)), flush=True)
    (HERE / "choices_results.json").write_text(json.dumps({"brain": BRAIN, "rows": rows}, indent=1))

    by = {d["id"]: d for d in D}
    first = {r["id"]: r for r in rows if r["ask"] == 0}
    opt = lambda d, letter: next((o for o in d["opts"] if o["letter"] == letter), None)
    pick = lambda i: opt(by[i], first[i]["does"]) if first.get(i) and first[i]["does"] else None
    none = {d["point"]: d for d in D if d["cond"] == "none"}
    pct = lambda a, b: "  - " if not b else "%d%% (%d of %d)" % (round(100 * a / b), a, b)
    ok = sum(r["does"] is not None for r in rows)
    secs = [r["seconds"] for r in rows if r["error"] is None]
    toks = [r["prompt_tokens"] for r in rows if r["prompt_tokens"]]
    med = statistics.median(secs) if secs else 0
    out = ["# Round 9, choices: %s%s" % (BRAIN, " (MOCK DATA)" if args.mock else ""), "",
           "%d calls on %d moments from the house. Usable answers: **%d of %d**." % (len(rows), len(none), ok, len(rows)),
           "Time per call: median **%.1f s**, slowest %.1f s. Prompt size: about %d tokens." % (med, max(secs) if secs else 0, statistics.median(toks) if toks else 0),
           "At that speed, six hobs each deciding every 20 seconds would keep the model busy **%d%%** of the time." % round(100 * med * 6 / 20), ""]

    def moved(cond, sign):
        """With this sheet: how often it picked an option the sheet favours (sign>0) or fears (sign<0), and how often it
        picked that same option with no sheet."""
        w = b = n = 0
        for d in D:
            if d["cond"] != cond:
                continue
            marked = {o["name"] + "|" + o["text"] for o in d["opts"] if (o["adj"] > 0) == (sign > 0) and o["adj"] != 0}
            p, q = pick(d["id"]), pick(none[d["point"]]["id"])
            if not marked or not p or not q:
                continue
            n += 1
            w += (p["name"] + "|" + p["text"]) in marked
            b += (q["name"] + "|" + q["text"]) in marked
        return w, b, n

    out += ["## 1. Does the sheet move the choice?", "",
            "Same moment, same options. \"With no sheet\" is how often it picked that same option when the sheet line was absent.", "",
            "| Sheet line added | It picked the option the line is about | With no sheet |", "|---|---|---|"]
    for cond, sign, text in (("pursuit", 1, "A pursuit one option serves"), ("place", 1, "A favourite place one door leads to"), ("fear", -1, "A fear of one option (lower is right)"),
                             ("full1", 1, "Full sheet: options it favours"), ("full1", -1, "Full sheet: options it fears (lower is right)"),
                             ("full2", 1, "Second full sheet: options it favours"), ("full2", -1, "Second full sheet: options it fears (lower is right)")):
        w, b, n = moved(cond, sign)
        out.append("| %s | %s | %s |" % (text, pct(w, n), pct(b, n)))

    diff = tot = 0
    for d in D:
        if d["cond"] in ("full1", "full2"):
            p, q = pick(d["id"]), pick(none[d["point"]]["id"])
            if p and q:
                tot += 1
                diff += p["text"] != q["text"]
    f1 = {d["point"]: d for d in D if d["cond"] == "full1"}
    f2 = {d["point"]: d for d in D if d["cond"] == "full2"}
    two = [(pick(f1[k]["id"]), pick(f2[k]["id"])) for k in f1 if k in f2]
    two = [(a, b) for a, b in two if a and b]
    out += ["", "A full random sheet changed the choice from the no-sheet choice in %s of moments." % pct(diff, tot),
            "Two hobs with different full sheets, at the same moment, chose differently in %s." % pct(sum(a["text"] != b["text"] for a, b in two), len(two)), ""]

    picks = [pick(d["id"]) for d in D if d["cond"] == "none"]
    picks = [p for p in picks if p]
    names = collections.Counter(p["name"] for p in picks)
    offered = collections.Counter(o["name"] for d in D if d["cond"] == "none" for o in d["opts"])
    out += ["## 2. With no sheet, what does it choose?", "",
            "It agreed with the autopilot's own first choice in %s." % pct(sum(p["engine_rank"] == 0 for p in picks), len(picks)),
            "It chose %d different activities across %d moments. The most chosen, with how often each was on offer:" % (len(names), len(picks)), "",
            "| Activity | Chosen | On offer | Chosen when offered |", "|---|---|---|---|"]
    out += ["| %s | %d | %d | %d%% |" % (k, v, offered[k], round(100 * v / offered[k])) for k, v in names.most_common(10)]
    pos = collections.Counter(first[d["id"]]["does"] for d in D if first.get(d["id"]) and first[d["id"]]["does"])
    out += ["", "By position in the list (a habit of picking the first or last would show here): " + ", ".join("%s %d" % (k, pos[k]) for k in sorted(pos)), ""]

    same = [(first[r["id"]]["does"], r["does"]) for r in rows if r["ask"] == 1 and r["does"] and first.get(r["id"]) and first[r["id"]]["does"]]
    out += ["## 3. Asked the same thing twice", "", "The same answer both times in %s." % pct(sum(a == b for a, b in same), len(same)), "",
            "## 4. What it said", "", "Twelve answers, with the sheet line it was given:", ""]
    r = random.Random(3)
    show = [d for d in D if d["cond"] in ("pursuit", "fear", "full1") and pick(d["id"])]
    for d in r.sample(show, min(12, len(show))):
        sh = ", ".join("%s: %s" % (k, v) for k, v in (d["sheet"] or {}).items() if v)
        out.append("- **%s** (%s) chose *%s*: \"%s\"" % (d["pet"], sh, pick(d["id"])["text"], first[d["id"]]["why"]))
    out += ["", "## 5. One whole prompt", "", "```", D[1]["prompt"] if len(D) > 1 else "", "```"]
    bad = [r for r in rows if r["does"] is None][:5]
    if bad:
        out += ["", "## 6. Answers that could not be used (first few)", ""] + ["- %s: `%s` %s" % (r["id"], r["why"][:100], r["error"] or "") for r in bad]
    (HERE / "choices_report.md").write_text("\n".join(out) + "\n")
    print("Done. %d of %d usable. Report: %s" % (ok, len(rows), HERE / "choices_report.md"))


if __name__ == "__main__":
    main()
