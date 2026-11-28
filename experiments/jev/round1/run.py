#!/usr/bin/env python3
"""Does Jev turn a hob's trait sheet into different behaviour?

30 situations x 8 hob sheets (+ a no-personality baseline), each asked twice.
Stdlib only. Needs an OpenRouter key:

    export OPENROUTER_API_KEY=...
    python3 run.py            # real run, ~540 calls
    python3 run.py --mock     # no network, fake answers, checks the pipeline

Writes results.json (raw answers), results.csv (one row per call) and report.md.
"""
import argparse, csv, hashlib, json, os, statistics, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.14")
# Appended to every question. This wording is itself a variable worth changing.
FRAME = " Answer with what this hob would actually do, going by its character. Not what would be wisest or kindest."
BASELINE = "(no sheet)"


def sheet(hob, axes):
    """Render a hob's poles as the plain-words trait sheet Jev sees."""
    lines = [f"{axes[ax][pole][0]}: {axes[ax][pole][1]}" for ax, pole in hob["traits"].items()]
    return f"{hob['name']} is a hob, a small creature living in a shared house with other hobs.\n" + "\n".join(lines)


def build(hob, sit, axes):
    name = hob["name"] if hob else "The hob"
    who = sheet(hob, axes) if hob else "A hob, a small creature living in a shared house with other hobs. Nothing is known about its character."
    crit = sit["criteria"]
    return {
        "model": MODEL,
        "state": {"hob": who, "situation": sit["situation"].replace("{name}", name)},
        "questions": {"q": {"type": sit["type"], "instructions": sit["instructions"].replace("{name}", name) + FRAME, "criteria": crit}},
    }


def call(body, key, tries=4):
    data = json.dumps(body).encode()
    for i in range(tries):
        req = urllib.request.Request(URL, data=data, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (401, 403, 404):
                sys.exit(f"HTTP {e.code} from OpenRouter: {msg}")
            err = f"HTTP {e.code}: {msg}"
        except Exception as e:  # timeouts, resets
            err = repr(e)
        time.sleep(2 ** i)
    return {"error": err}


def mock(body, hob, sit, rep):
    """Fake answer: leans toward the hob's pole, plus per-call noise."""
    h = int(hashlib.md5(f"{hob and hob['name']}{sit['id']}{rep}".encode()).hexdigest(), 16)
    noise = (h % 100) / 100 * 0.1
    pole = hob["traits"][sit["axis"]] if hob else None
    p_a = {"A": 0.75, "B": 0.35, None: 0.6}[pole] + noise
    if sit["type"] == "noul":
        return {"answers": {"q": {"type": "noul", "noul": p_a if sit["yes_pole"] == "A" else 1 - p_a}}, "usage": {"cost": 0}}
    opts = list(sit["criteria"])
    rest = [o for o in opts if o != sit["a"]]
    probs = {sit["a"]: p_a, **{o: (1 - p_a) / len(rest) for o in rest}}
    return {"answers": {"q": {"type": "choice", "choice": max(probs, key=probs.get), "probabilities": probs}}, "usage": {"cost": 0}}


def p_a(ans, sit):
    """Probability of the answer pole A predicts. None if refused / errored."""
    if not ans or ans.get("type") != sit["type"]:
        return None
    if sit["type"] == "noul":
        return ans["noul"] if sit["yes_pole"] == "A" else 1 - ans["noul"]
    probs = ans.get("probabilities")
    if probs:
        return probs.get(sit["a"], 0.0)
    return 1.0 if ans.get("choice") == sit["a"] else 0.0


def p_pole(ans, sit, pole):
    """Probability of the answer the given pole predicts (choice: that pole's option)."""
    if not ans or ans.get("type") != sit["type"]:
        return None
    if sit["type"] == "noul":
        return ans["noul"] if sit["yes_pole"] == pole else 1 - ans["noul"]
    opt = sit["a"] if pole == "A" else sit["b"]
    probs = ans.get("probabilities")
    return probs.get(opt, 0.0) if probs else float(ans.get("choice") == opt)


def in_character(ans, sit, pole):
    """Is the hob's own pole's answer the one Jev actually picked?"""
    if not ans or ans.get("type") != sit["type"]:
        return None
    if sit["type"] == "noul":
        return (ans["noul"] > 0.5) == (sit["yes_pole"] == pole)
    return ans.get("choice") == (sit["a"] if pole == "A" else sit["b"])


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="no network; fake answers")
    ap.add_argument("--repeats", type=int, default=2, help="times each question is asked (>=2 measures run-to-run noise)")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    cfg = json.loads((HERE / "hobs.json").read_text())
    axes, hobs = cfg["axes"], cfg["hobs"]
    sits = json.loads((HERE / "situations.json").read_text())
    key = os.environ.get("OPENROUTER_API_KEY")
    if not args.mock and not key:
        sys.exit("Set OPENROUTER_API_KEY, or use --mock.")

    jobs = [(h, s, r) for h in hobs + [None] for s in sits for r in range(args.repeats)]
    print(f"{len(jobs)} calls to {MODEL}{' (mock)' if args.mock else ''}...")

    def run(job):
        h, s, r = job
        body = build(h, s, axes)
        resp = mock(body, h, s, r) if args.mock else call(body, key)
        return {"hob": h["name"] if h else BASELINE, "sit": s["id"], "rep": r,
                "answer": (resp.get("answers") or {}).get("q"), "cost": (resp.get("usage") or {}).get("cost"), "error": resp.get("error")}

    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(run, jobs))
    (HERE / "results.json").write_text(json.dumps({"model": MODEL, "frame": FRAME, "rows": rows}, indent=1))

    S = {s["id"]: s for s in sits}
    H = {h["name"]: h for h in hobs}
    ans = {(r["hob"], r["sit"], r["rep"]): r["answer"] for r in rows}
    failed = sum(1 for r in rows if p_a(r["answer"], S[r["sit"]]) is None)

    with open(HERE / "results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hob", "situation", "axis", "pole", "rep", "p_pole_A_answer", "picked", "in_character"])
        for r in rows:
            s = S[r["sit"]]
            pole = H[r["hob"]]["traits"][s["axis"]] if r["hob"] in H else ""
            a = r["answer"] or {}
            picked = a.get("choice") if s["type"] == "choice" else ("" if "noul" not in a else ("yes" if a["noul"] > 0.5 else "no"))
            w.writerow([r["hob"], s["id"], s["axis"], pole, r["rep"], p_a(r["answer"], s), picked, in_character(r["answer"], s, pole) if pole else ""])

    def avg_pa(hob, sid):  # mean over repeats
        return mean([p_a(ans[(hob, sid, r)], S[sid]) for r in range(args.repeats)])

    # Per situation: effect = mean P(A-answer) for pole-A hobs minus pole-B hobs. 0 = traits ignored, 1 = fully followed.
    per_sit = []
    for s in sits:
        A = [h["name"] for h in hobs if h["traits"][s["axis"]] == "A"]
        B = [h["name"] for h in hobs if h["traits"][s["axis"]] == "B"]
        xs = [avg_pa(h["name"], s["id"]) for h in hobs]
        inchar = mean([in_character(ans[(h["name"], s["id"], r)], s, h["traits"][s["axis"]]) for h in hobs for r in range(args.repeats)])
        per_sit.append({"id": s["id"], "axis": s["axis"], "effect": mean([avg_pa(h, s["id"]) for h in A]) - mean([avg_pa(h, s["id"]) for h in B]),
                        "spread": max(xs) - min(xs), "baseline": avg_pa(BASELINE, s["id"]), "in_character": inchar, "unwise": s.get("unwise")})

    noise = mean([abs(p_a(ans[(h, s["id"], 0)], s) - p_a(ans[(h, s["id"], 1)], s))
                  for h in list(H) + [BASELINE] for s in sits
                  if args.repeats > 1 and None not in (p_a(ans[(h, s["id"], 0)], s), p_a(ans[(h, s["id"], 1)], s))])
    flips = mean([in_character(ans[(h, s["id"], 0)], s, "A") != in_character(ans[(h, s["id"], 1)], s, "A")
                  for h in H for s in sits if args.repeats > 1 and ans[(h, s["id"], 0)] and ans[(h, s["id"], 1)]])

    # The "too sensible" check: situations where one pole predicts the unwise/petty answer.
    uw_p, uw_ic, uw_base = [], [], []
    for s in sits:
        pole = s.get("unwise")
        if not pole:
            continue
        for h in hobs:
            if h["traits"][s["axis"]] == pole:
                for r in range(args.repeats):
                    uw_p.append(p_pole(ans[(h["name"], s["id"], r)], s, pole))
                    uw_ic.append(in_character(ans[(h["name"], s["id"], r)], s, pole))
        uw_base += [p_pole(ans[(BASELINE, s["id"], r)], s, pole) for r in range(args.repeats)]

    eff, ic = mean([p["effect"] for p in per_sit]), mean([p["in_character"] for p in per_sit])
    cost = sum(r["cost"] or 0 for r in rows)
    verdict = ("Traits clearly steer decisions." if eff >= 0.30 else "Traits steer decisions weakly." if eff >= 0.10 else "Traits barely reach the decisions.")
    sensible = ("It will pick the unwise, in-character option." if mean(uw_ic) >= 0.5 else
                "It leans back toward the sensible option even when the sheet says otherwise.")

    out = [f"# Jev x hob sheets: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} failed or refused, cost ${cost:.4f}. Thresholds below are rough rules of thumb.", "",
           "## Headline", "",
           f"- **Trait effect: {eff:.2f}** (0 = sheet ignored, 1 = sheet fully decides). {verdict}",
           f"- **In-character picks: {ic:.0%}** of decisions went the way the hob's own pole predicts.",
           f"- **Run-to-run noise: {noise:.3f}** mean probability change on an identical repeat; {flips:.1%} of picks flipped. Effects near this size mean nothing.",
           f"- **Unwise-option check:** hobs whose sheet predicts the unwise answer chose it {mean(uw_ic):.0%} of the time (mean probability {mean(uw_p):.2f}; the no-sheet baseline gives it {mean(uw_base):.2f}). {sensible}", "",
           "## By trait axis", "", "| axis | effect | in-character |", "|---|---|---|"]
    for ax in axes:
        ps = [p for p in per_sit if p["axis"] == ax]
        out.append(f"| {ax.replace('_', ' / ')} | {mean([p['effect'] for p in ps]):.2f} | {mean([p['in_character'] for p in ps]):.0%} |")
    out += ["", "## By situation", "",
            "Effect: pole-A hobs minus pole-B hobs on the pole-A answer. Spread: highest minus lowest hob. Baseline: same number with no sheet.", "",
            "| situation | effect | spread | baseline | in-character | unwise pole |", "|---|---|---|---|---|---|"]
    for p in sorted(per_sit, key=lambda p: p["effect"]):
        out.append(f"| {p['id']} | {p['effect']:.2f} | {p['spread']:.2f} | {p['baseline']:.2f} | {p['in_character']:.0%} | {p['unwise'] or ''} |")
    out += ["", "## Per hob: P(pole-A answer), mean of repeats", "", "| situation | " + " | ".join(H) + " |", "|---|" + "---|" * len(H)]
    for s in sits:
        out.append(f"| {s['id']} | " + " | ".join(f"{avg_pa(h, s['id']):.2f}{'ᴬ' if H[h]['traits'][s['axis']] == 'A' else 'ᴮ'}" for h in H) + " |")
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[5:10]))
    print(f"\nFull table: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
