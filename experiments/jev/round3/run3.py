#!/usr/bin/env python3
"""Round 3: which KIND of descriptor makes a hob behave differently?

Tests 26 modifiers (labels, compulsions, beliefs, wants, states, roles, and six
random template quirks) two ways each: alone, and bolted onto a decent hob
(kind + honest + generous). Scores every one on:

  override     does it still do the thing, against the decent base?
  decency kept is it still decent elsewhere, or did it turn bad across the board?
  outside      how much of what it does can't be reproduced by the three dials
               (warm/cold, bold/careful, dutiful/loose) from round 2?

    export OPENROUTER_API_KEY=...
    python3 run3.py           # about 5,300 calls, several minutes, about 10 cents
    python3 run3.py --mock    # no network; checks the pipeline

Writes report.md, modifiers.csv and results.json. Edit modifiers.json to add your own.
"""
import argparse, csv, hashlib, json, math, os, statistics, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.14")
NAME = "Nib"
INTRO = f"{NAME} is a hob, a small creature living in a shared house with other hobs."
DECENT = ["kind_v1", "honest_v1", "generous_v1"]
# "Still a decent hob" checks: P(pole-A answer) = the decent answer on each.
DECENCY = ["gen1", "kind4", "kind2", "gen4", "hl1"]
K = 3  # number of dials


def body(lines, sit):
    who = INTRO + ("\n" + "\n".join(lines) if lines else " Nothing is known about its character.")
    return {"model": MODEL, "state": {"hob": who, "situation": sit["situation"].replace("{name}", NAME)},
            "questions": {"q": {"type": sit["type"], "instructions": sit["instructions"].replace("{name}", NAME), "criteria": sit["criteria"]}}}


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


def mock(sid, hot, sit):
    h = int(hashlib.md5(f"{sid}{sit['id']}".encode()).hexdigest(), 16)
    pa = (0.85 if sit["id"] in hot else 0.2 + (h % 40) / 100)
    if sit["type"] == "noul":
        return {"answers": {"q": {"type": "noul", "noul": pa if sit.get("yes_pole", "A") == "A" else 1 - pa}}, "usage": {"cost": 0}}
    rest = [o for o in sit["criteria"] if o != sit["a"]]
    pr = {sit["a"]: pa, **{o: (1 - pa) / len(rest) for o in rest}}
    return {"answers": {"q": {"type": "choice", "choice": max(pr, key=pr.get), "probabilities": pr}}, "usage": {"cost": 0}}


def p_a(ans, sit):
    if not ans or ans.get("type") != sit["type"]:
        return None
    if sit["type"] == "noul":
        return ans["noul"] if sit["yes_pole"] == "A" else 1 - ans["noul"]
    pr = ans.get("probabilities")
    return pr.get(sit["a"], 0.0) if pr else float(ans.get("choice") == sit["a"])


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else float("nan")


def dials(rows, k=K):
    """Top-k principal directions of a list of equal-length vectors (pure Python power iteration)."""
    n = len(rows[0])
    mu = [mean([r[j] for r in rows]) for j in range(n)]
    X = [[r[j] - mu[j] for j in range(n)] for r in rows]
    C = [[sum(x[a] * x[b] for x in X) for b in range(n)] for a in range(n)]
    vecs = []
    for c in range(k):
        v = [math.sin(1 + j * (c + 1)) for j in range(n)]
        for _ in range(300):
            w = [sum(C[a][b] * v[b] for b in range(n)) for a in range(n)]
            for u in vecs:
                d = sum(w[j] * u[j] for j in range(n))
                w = [w[j] - d * u[j] for j in range(n)]
            nrm = math.sqrt(sum(x * x for x in w)) or 1.0
            v = [x / nrm for x in w]
        vecs.append(v)
    return mu, vecs


def outside(vec, mu, vecs):
    """(share of the vector the dials can't reproduce, size, residual vector)"""
    f = [vec[j] - mu[j] for j in range(len(vec))]
    res = f[:]
    for u in vecs:
        d = sum(f[j] * u[j] for j in range(len(f)))
        res = [res[j] - d * u[j] for j in range(len(f))]
    tot = sum(x * x for x in f) or 1e-9
    return sum(x * x for x in res) / tot, math.sqrt(tot / len(f)), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    sits = json.loads((HERE / "situations3.json").read_text())
    traits = json.loads((HERE / "traits_v1.json").read_text())
    mods = json.loads((HERE / "modifiers.json").read_text())
    S = {s["id"]: s for s in sits}
    key = os.environ.get("OPENROUTER_API_KEY")
    if not args.mock and not key:
        sys.exit("Set OPENROUTER_API_KEY, or use --mock.")
    tline = {t["id"]: f"{t['label']}: {t['text']}" for t in traits}
    decent = [tline[i] for i in DECENT]

    sheets = {"empty": ([], []), "decent": (decent, [])}
    for t in traits:
        sheets["t:" + t["id"]] = ([tline[t["id"]]], [s["id"] for s in sits if s["axis"] == t["axis"]] if t["pole"] == "A" else [])
    for m in mods:
        sheets["m:" + m["id"]] = (m["lines"], m["targets"])
        sheets["d:" + m["id"]] = (decent + m["lines"], m["targets"])

    jobs = [(sid, s, r) for sid in sheets for s in sits for r in range(args.repeats)]
    print(f"{len(jobs)} calls to {MODEL}{' (mock)' if args.mock else ''}...", flush=True)
    done = [0]

    def run(job):
        sid, s, r = job
        lines, hot = sheets[sid]
        resp = mock(sid, hot, s) if args.mock else call(body(lines, s), key)
        done[0] += 1
        if done[0] % 500 == 0:
            print(f"  {done[0]}/{len(jobs)}", flush=True)
        return {"sheet": sid, "sit": s["id"], "answer": (resp.get("answers") or {}).get("q"), "cost": (resp.get("usage") or {}).get("cost"), "error": resp.get("error")}

    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(run, jobs))
    (HERE / "results.json").write_text(json.dumps({"model": MODEL, "rows": rows}))
    acc = {}
    for r in rows:
        acc.setdefault((r["sheet"], r["sit"]), []).append(p_a(r["answer"], S[r["sit"]]))
    P = {k: mean(v) for k, v in acc.items()}
    failed = sum(1 for k, v in P.items() if v != v)
    P = {k: (0.5 if v != v else v) for k, v in P.items()}  # failed cells -> neutral
    cost = sum(r["cost"] or 0 for r in rows)
    ids = [s["id"] for s in sits]
    vec = lambda sid: [P[(sid, i)] for i in ids]

    # Dials are fitted on the 20 old single traits only, then everything is measured against them.
    tv = {t["id"]: vec("t:" + t["id"]) for t in traits}
    mu, vecs = dials(list(tv.values()))
    loo = []
    for t in traits:  # fair reference: how far outside the dials is an ordinary adjective it wasn't fitted on?
        m2, v2 = dials([v for i, v in tv.items() if i != t["id"]])
        loo.append(outside(tv[t["id"]], m2, v2)[0])
    ref = statistics.median(loo)

    R = []
    for m in mods:
        tg, a, d = m["targets"], "m:" + m["id"], "d:" + m["id"]
        non = [i for i in ids if i not in tg]
        out, size, res = outside(vec(a), mu, vecs)
        left = sorted(range(len(ids)), key=lambda j: -abs(res[j]))[:3]
        R.append({**m, "alone": mean([P[(a, i)] for i in tg]) if tg else None,
                  "base": mean([P[("decent", i)] for i in tg]) if tg else None,
                  "on": mean([P[(d, i)] for i in tg]) if tg else None,
                  "spill": mean([abs(P[(d, i)] - P[("decent", i)]) for i in non]),
                  "decency": mean([P[(d, i)] for i in DECENCY if i not in tg]),
                  "outside": out, "size": size, "left": [(ids[j], res[j]) for j in left]})
    dec0 = mean([P[("decent", i)] for i in DECENCY])
    f = lambda x: "" if x is None else f"{x:.2f}"
    with open(HERE / "modifiers.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["modifier", "situation", "empty", "alone", "decent", "decent_plus_modifier", "is_target"])
        for m in mods:
            for i in ids:
                w.writerow([m["id"], i, f(P[("empty", i)]), f(P[("m:" + m["id"], i)]), f(P[("decent", i)]), f(P[("d:" + m["id"], i)]), int(i in m["targets"])])

    out = [f"# Jev round 3: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} cells failed, cost ${cost:.4f}.", "",
           "Each modifier is tested alone and added to a decent hob (kind + honest + generous).", "",
           "- **Target, decent hob**: how often the plain decent hob does the modifier's signature thing (steal, sleep outside...).",
           "- **Target, with modifier**: the same hob with the modifier added. High = it overrides the stats.",
           "- **Spill**: mean change on every other situation when the modifier is added. Low = contained.",
           f"- **Decency kept**: still shares, forgives, reassures. The decent hob alone scores **{dec0:.2f}**.",
           f"- **Outside dials**: share of its behaviour the three dials can't reproduce. An ordinary adjective trait scores about **{ref:.0%}**.",
           "- **Size**: how much it changes behaviour overall when alone.", "",
           "| modifier | form | target: decent hob | target: with modifier | spill | decency kept | outside dials | size | what the dials miss |", "|---|---|---|---|---|---|---|---|---|"]
    for concept in dict.fromkeys(m["concept"] for m in mods):
        out.append(f"| **{concept}** | | | | | | | | |")
        for r in [r for r in R if r["concept"] == concept]:
            out.append(f"| {r['id']} | {r['form']} | {f(r['base'])} | {f(r['on'])} | {r['spill']:.2f} | {r['decency']:.2f} | {r['outside']:.0%} | {r['size']:.2f} | "
                       + ", ".join(f"{i} {v:+.2f}" for i, v in r["left"]) + " |")
    forms = {}
    for r in R:
        forms.setdefault(r["form"], []).append(r)
    out += ["", "## By form", "", "| form | n | override (with modifier minus decent hob) | spill | decency kept | outside dials |", "|---|---|---|---|---|---|"]
    for form, rs in forms.items():
        ov = mean([r["on"] - r["base"] for r in rs if r["on"] is not None])
        out.append(f"| {form} | {len(rs)} | {'' if ov != ov else f'{ov:+.2f}'} | {mean([r['spill'] for r in rs]):.2f} | {mean([r['decency'] for r in rs]):.2f} | {mean([r['outside'] for r in rs]):.0%} |")
    out += ["", "## Per-target detail", "", "P(does the thing): no sheet / modifier alone / decent hob / decent hob + modifier", ""]
    for r in R:
        if r["targets"]:
            out.append(f"- **{r['id']}**: " + "; ".join(f"{i} {P[('empty', i)]:.2f} / {P[('m:' + r['id'], i)]:.2f} / {P[('decent', i)]:.2f} / {P[('d:' + r['id'], i)]:.2f}" for i in r["targets"]))
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print(f"Done. {failed} failed, cost ${cost:.4f}. Report: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
