#!/usr/bin/env python3
"""Round 2: use Jev to find which trait wordings and situations are worth keeping.

Four parts, one run:
  1. Frame check      - does the "not what would be wisest" line change Jev's default?
  2. Wording sweep    - 34 trait wordings, each alone on a sheet, across 48 situations.
                        Scores each wording on pull (moves its own axis) and leak (moves others).
  3. Situation audit  - which situations separate hobs, which are dead, which options nobody picks.
  4. Combination test - 2x2 sheets for the five trait-combination guesses from round 1.

    export OPENROUTER_API_KEY=...
    python3 run2.py           # about 3,500 calls, a few minutes, under 10 cents
    python3 run2.py --mock    # no network; checks the pipeline

Writes report.md, fingerprints.csv (wording x situation shifts) and results.json.
Edit traits.json / situations2.json to try your own wordings, then rerun.
"""
import argparse, csv, hashlib, json, os, statistics, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.14")
OLD_FRAME = " Answer with what this hob would actually do, going by its character. Not what would be wisest or kindest."
NAME = "Nib"  # same name on every sheet so the name can't matter
INTRO = f"{NAME} is a hob, a small creature living in a shared house with other hobs."
# Round-1 guesses, each a 2x2: (first axis, second axis, target situations)
COMBOS = [("patient_hasty", "brave_timid", ["pat2"]), ("generous_greedy", "honest_sly", ["gen3", "hon3"]),
          ("ambitious_content", "brave_timid", ["amb1"]), ("curious_cautious", "brave_timid", ["cur3"])]


def body(lines, sit, frame=""):
    who = INTRO + ("\n" + "\n".join(lines) if lines else " Nothing is known about its character.")
    return {"model": MODEL, "state": {"hob": who, "situation": sit["situation"].replace("{name}", NAME)},
            "questions": {"q": {"type": sit["type"], "instructions": sit["instructions"].replace("{name}", NAME) + frame, "criteria": sit["criteria"]}}}


def call(b, key, tries=5):
    data = json.dumps(b).encode()
    for i in range(tries):
        req = urllib.request.Request(URL, data=data, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (401, 402, 403, 404):
                print(f"HTTP {e.code} from OpenRouter: {msg}", file=sys.stderr)
                os._exit(1)
            err = f"HTTP {e.code}: {msg}"
        except Exception as e:
            err = repr(e)
        time.sleep(2 ** i)
    return {"error": err}


def mock(poles, sit, tag):
    h = int(hashlib.md5(f"{tag}{sit['id']}".encode()).hexdigest(), 16)
    pa = {"A": 0.8, "B": 0.25}.get(poles.get(sit["axis"]), 0.5) + (h % 100) / 1000
    if sit["type"] == "noul":
        return {"answers": {"q": {"type": "noul", "noul": pa if sit["yes_pole"] == "A" else 1 - pa}}, "usage": {"cost": 0}}
    rest = [o for o in sit["criteria"] if o != sit["a"]]
    pr = {sit["a"]: pa, **{o: (1 - pa) / len(rest) for o in rest}}
    return {"answers": {"q": {"type": "choice", "choice": max(pr, key=pr.get), "probabilities": pr}}, "usage": {"cost": 0}}


def p_a(ans, sit):
    """Probability of the answer pole A of the situation's axis predicts."""
    if not ans or ans.get("type") != sit["type"]:
        return None
    if sit["type"] == "noul":
        return ans["noul"] if sit["yes_pole"] == "A" else 1 - ans["noul"]
    pr = ans.get("probabilities")
    return pr.get(sit["a"], 0.0) if pr else float(ans.get("choice") == sit["a"])


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    traits = json.loads((HERE / "traits.json").read_text())
    sits = json.loads((HERE / "situations2.json").read_text())
    S, T = {s["id"]: s for s in sits}, {t["id"]: t for t in traits}
    key = os.environ.get("OPENROUTER_API_KEY")
    if not args.mock and not key:
        sys.exit("Set OPENROUTER_API_KEY, or use --mock.")
    line = lambda t: f"{t['label']}: {t['text']}"
    v1 = {(t["axis"], t["pole"]): t for t in traits if t["id"].endswith("_v1") and t["id"] not in ("bold_v1", "meek_v1")}

    # sheet id -> (trait lines, {axis: pole}, frame, situations to ask)
    sheets = {"base": ([], {}, "", sits), "base_framed": ([], {}, OLD_FRAME, sits)}
    for t in traits:
        sheets["w:" + t["id"]] = ([line(t)], {t["axis"]: t["pole"]}, "", sits)
    for a1, a2, targets in COMBOS:
        for p1 in "AB":
            for p2 in "AB":
                sheets[f"c:{a1}:{a2}:{p1}{p2}"] = ([line(v1[(a1, p1)]), line(v1[(a2, p2)])], {a1: p1, a2: p2}, "", [S[x] for x in targets])

    jobs = [(sid, s, r) for sid, (_, _, _, ss) in sheets.items() for s in ss for r in range(args.repeats)]
    print(f"{len(jobs)} calls to {MODEL}{' (mock)' if args.mock else ''}...", flush=True)
    done = [0]

    def run(job):
        sid, s, r = job
        lines, poles, frame, _ = sheets[sid]
        resp = mock(poles, s, f"{sid}{r}") if args.mock else call(body(lines, s, frame), key)
        done[0] += 1
        if done[0] % 500 == 0:
            print(f"  {done[0]}/{len(jobs)}", flush=True)
        return {"sheet": sid, "sit": s["id"], "rep": r, "answer": (resp.get("answers") or {}).get("q"),
                "cost": (resp.get("usage") or {}).get("cost"), "error": resp.get("error")}

    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(run, jobs))
    (HERE / "results.json").write_text(json.dumps({"model": MODEL, "rows": rows}))

    raw = {}
    for r in rows:
        raw.setdefault((r["sheet"], r["sit"]), []).append(r["answer"])
    P = {k: mean([p_a(a, S[k[1]]) for a in v]) for k, v in raw.items()}  # mean over repeats
    failed = sum(1 for r in rows if p_a(r["answer"], S[r["sit"]]) is None)
    noise = mean([abs(p_a(v[0], S[k[1]]) - p_a(v[1], S[k[1]])) for k, v in raw.items()
                  if len(v) > 1 and None not in (p_a(v[0], S[k[1]]), p_a(v[1], S[k[1]]))])
    cost = sum(r["cost"] or 0 for r in rows)
    shift = lambda tid, sid: P[("w:" + tid, sid)] - P[("base", sid)]

    # ---- 2. wording sweep
    W = []
    for t in traits:
        sign = 1 if t["pole"] == "A" else -1
        on = [s for s in sits if s["axis"] == t["axis"]]
        off = [s for s in sits if s["axis"] != t["axis"]]
        leaks = sorted(off, key=lambda s: -abs(shift(t["id"], s["id"])))
        W.append({**t, "pull": mean([sign * shift(t["id"], s["id"]) for s in on]), "leak": mean([abs(shift(t["id"], s["id"])) for s in off]),
                  "worst": min(on, key=lambda s: sign * shift(t["id"], s["id"])),
                  "top_leaks": [(s["id"], shift(t["id"], s["id"])) for s in leaks[:3]]})
    with open(HERE / "fingerprints.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wording", "axis", "pole"] + [s["id"] for s in sits])
        w.writerow(["(baseline P)", "", ""] + [f"{P[('base', s['id'])]:.2f}" for s in sits])
        for t in traits:
            w.writerow([t["id"], t["axis"], t["pole"]] + [f"{shift(t['id'], s['id']):+.2f}" for s in sits])

    # ---- 3. situation audit
    A = []
    for s in sits:
        xs = [P[("w:" + t["id"], s["id"])] for t in traits]
        movers = sorted(traits, key=lambda t: -abs(shift(t["id"], s["id"])))[:3]
        dead = []
        if s["type"] == "choice":
            for o in s["criteria"]:
                top = max([(a or {}).get("probabilities", {}).get(o, 0) for (sh, si), v in raw.items() if si == s["id"] for a in v] or [0])
                if top < 0.10:
                    dead.append(o)
        base = P[("base", s["id"])]
        flag = "dead" if max(xs) - min(xs) < 0.15 else "pinned" if (base < 0.05 or base > 0.95) else ""
        A.append({"id": s["id"], "group": s["group"], "spread": max(xs) - min(xs), "base": base, "flag": flag, "dead_opts": dead,
                  "movers": [(t["id"], shift(t["id"], s["id"])) for t in movers], "own_axis_top": movers[0]["axis"] == s["axis"]})

    out = [f"# Jev round 2: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} failed or refused, cost ${cost:.4f}. Run-to-run noise: {noise:.3f}. Treat any shift under about {max(3 * noise, 0.05):.2f} as nothing.", "",
           "All numbers are P(the pole-A answer for that situation's axis). Shifts are against the no-sheet baseline.", "",
           "## 1. Frame check", "",
           f"Mean absolute change in the no-sheet answer when the round-1 line is added: **{mean([abs(P[('base_framed', s['id'])] - P[('base', s['id'])]) for s in sits]):.2f}**. Biggest movers:", "",
           "| situation | no frame | with frame |", "|---|---|---|"]
    for s in sorted(sits, key=lambda s: -abs(P[("base_framed", s["id"])] - P[("base", s["id"])]))[:8]:
        out.append(f"| {s['id']} | {P[('base', s['id'])]:.2f} | {P[('base_framed', s['id'])]:.2f} |")
    out += ["", "## 2. Wording sweep", "",
            "One trait per sheet. **Pull**: how far it moves its own axis's situations, in the right direction (higher is better). "
            "**Leak**: mean movement on every other axis (lower is better). **Weakest**: the own-axis situation it moved least.", "",
            "| wording | pull | leak | pull/leak | weakest own situation | biggest leaks |", "|---|---|---|---|---|---|"]
    for ax in dict.fromkeys(t["axis"] for t in traits):
        for pole in "AB":
            for x in sorted([x for x in W if x["axis"] == ax and x["pole"] == pole], key=lambda x: -x["pull"]):
                sign = 1 if pole == "A" else -1
                out.append(f"| {x['id']} | {x['pull']:.2f} | {x['leak']:.2f} | {x['pull'] / max(x['leak'], 0.01):.1f} | {x['worst']['id']} ({sign * shift(x['id'], x['worst']['id']):+.2f}) | "
                           + ", ".join(f"{i} {v:+.2f}" for i, v in x["top_leaks"]) + " |")
    out += ["", "## 3. Situation audit", "",
            "**Spread**: highest minus lowest across all 34 single-trait sheets. **dead** = no wording moves it. **pinned** = baseline already at 0 or 1. "
            "Sorted most useful first.", "",
            "| situation | group | spread | baseline | flag | moved most by | options nobody picks |", "|---|---|---|---|---|---|---|"]
    for a in sorted(A, key=lambda a: -a["spread"]):
        out.append(f"| {a['id']} | {a['group']} | {a['spread']:.2f} | {a['base']:.2f} | {a['flag']} | "
                   + ", ".join(f"{i} {v:+.2f}" for i, v in a["movers"]) + f" | {', '.join(a['dead_opts'])} |")
    out += ["", f"Situations whose biggest mover is on their own axis: **{sum(a['own_axis_top'] for a in A)}/{len(A)}**.", "",
            "## 4. Combination test", "",
            "Two traits per sheet. If the second trait changes the answer, Jev is combining traits, as round 1 suggested.", ""]
    for a1, a2, targets in COMBOS:
        for sid in targets:
            n = lambda ax, p: v1[(ax, p)]["label"]
            g = lambda p1, p2: P[(f"c:{a1}:{a2}:{p1}{p2}", sid)]
            out += [f"**{sid}** ({S[sid]['a'] if S[sid]['type'] == 'choice' else 'yes/no'}; axis {S[sid]['axis']})", "",
                    f"| | {n(a2, 'A')} | {n(a2, 'B')} | gap |", "|---|---|---|---|",
                    f"| {n(a1, 'A')} | {g('A', 'A'):.2f} | {g('A', 'B'):.2f} | {g('A', 'A') - g('A', 'B'):+.2f} |",
                    f"| {n(a1, 'B')} | {g('B', 'A'):.2f} | {g('B', 'B'):.2f} | {g('B', 'A') - g('B', 'B'):+.2f} |", ""]
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print(f"Done. {failed} failed, cost ${cost:.4f}. Report: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
