#!/usr/bin/env python3
"""Round 8: uniqueness. No caps. Bigger pools, more kinds of slot, sheets from sparse to very rich.

340 random hobs. Each has 4 to 14 of 14 traits and, by chance, any of: a core value, a fear, body size,
a learned quirk, a favourite food, a favourite place, a craft, a pet peeve, a superstition, a relationship,
an odd trait, and up to three quirks. Some hobs are sparse (a few lines), some rich (20 or more).

The question: does a richer sheet make a hob more unlike every other hob?

    export OPENROUTER_API_KEY=...
    python3 run8.py           # about 32,000 calls, roughly 20 minutes, about 95 cents
    python3 run8.py --mock

Writes report.md, matrix.csv and results.json. Everything tested is in plan.json.
"""
import argparse, csv, random, hashlib, json, math, os, statistics, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.14")
NAME = "Nib"
INTRO = f"{NAME} is a hob, a small creature living in a shared house with other hobs."
DECENCY = ["gen1", "kind4", "kind2", "gen4", "hl1"]
VIOLENCE = ["k2", "k4", "k5"]
MAKING = ["mk1", "mk2", "mk3"]
K = 3


def body(lines, sit):
    who = INTRO + ("\n" + "\n".join(lines) if lines else " Nothing is known about its character.")
    return {"model": MODEL, "state": {"hob": who.replace("{name}", NAME), "situation": sit["situation"].replace("{name}", NAME)},
            "questions": {"q": {"type": sit["type"], "instructions": sit["instructions"].replace("{name}", NAME), "criteria": sit["criteria"]}}}


def call(b, key, tries=6):
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


def mock(sid, sit):
    h = int(hashlib.md5(f"{sid}{sit['id']}".encode()).hexdigest(), 16)
    pa = 0.1 + (h % 80) / 100
    if sit["type"] == "noul":
        return {"answers": {"q": {"type": "noul", "noul": pa if sit.get("yes_pole", "A") == "A" else 1 - pa}}, "usage": {"cost": 0}}
    rest = [o for o in sit["criteria"] if o != sit["a"]]
    pr = {sit["a"]: pa, **{o: (1 - pa) / len(rest) for o in rest}}
    return {"answers": {"q": {"type": "choice", "choice": max(pr, key=pr.get), "probabilities": pr}}, "usage": {"cost": 0}}


def p_a(ans, sit):
    """Returns (probability, refused?)."""
    if ans and ans.get("type") == "refusal":
        return None, True
    if not ans or ans.get("type") != sit["type"]:
        return None, False
    if sit["type"] == "noul":
        return (ans["noul"] if sit["yes_pole"] == "A" else 1 - ans["noul"]), False
    pr = ans.get("probabilities")
    return (pr.get(sit["a"], 0.0) if pr else float(ans.get("choice") == sit["a"])), False


def mean(xs):
    xs = [x for x in xs if x is not None and x == x]
    return statistics.fmean(xs) if xs else float("nan")


def dials(rows, k=K):
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
    f = [vec[j] - mu[j] for j in range(len(vec))]
    res = f[:]
    for u in vecs:
        d = sum(f[j] * u[j] for j in range(len(f)))
        res = [res[j] - d * u[j] for j in range(len(f))]
    tot = sum(x * x for x in f) or 1e-9
    return sum(x * x for x in res) / tot, math.sqrt(tot / len(f))


def variety(rows):
    """(effective number of independent directions, typical distance between two hobs)."""
    n = len(rows[0])
    mu = [mean([r[j] for r in rows]) for j in range(n)]
    X = [[r[j] - mu[j] for j in range(n)] for r in rows]
    G = [[sum(a[j] * b[j] for j in range(n)) for b in X] for a in X]
    tr = sum(G[i][i] for i in range(len(X)))
    tr2 = sum(G[i][j] ** 2 for i in range(len(X)) for j in range(len(X)))
    d = [math.sqrt(sum((a[j] - b[j]) ** 2 for j in range(n)) / n) for i, a in enumerate(rows) for b in rows[:i]]
    return tr * tr / (tr2 or 1e-9), mean(d)



def rms(xs):
    xs = [x for x in xs if x == x]
    return math.sqrt(sum(x * x for x in xs) / len(xs)) if xs else float("nan")


def corr(a, b):
    ma, mb = mean(a), mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else float("nan")




POLE = {1: 30, 2: 60, 3: 95}
ORDER = ["body", "value", "fear", "food", "place", "craft", "peeve", "belief", "rel", "learned"]


def render(h, plan):
    L = []
    for a, v in h["traits"].items():
        label, text = plan["axes"][a]["A" if v > 0 else "B"]
        L.append(f"{label}, {POLE[abs(v)]} out of 100: {text}")
    for k in ORDER:
        if h[k]:
            L.append(plan["slots"][k][h[k]][0])
    L += [f"{w}, {d}" for w, d in h["quirks"]]
    if h["defect"]:
        L.append(plan["defect"][h["defect"]])
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    sits = json.loads((HERE / "situations8.json").read_text())
    plan = json.loads((HERE / "plan.json").read_text())
    hobs = plan["hobs"]
    S = {s["id"]: s for s in sits}
    ids = [s["id"] for s in sits]
    key = os.environ.get("OPENROUTER_API_KEY")
    if not args.mock and not key:
        sys.exit("Set OPENROUTER_API_KEY, or use --mock.")
    sheets = {"empty": []}
    for h in hobs:
        sheets[h["id"]] = render(h, plan)
    jobs = [(sid, s) for sid in sheets for s in sits]
    print(f"{len(jobs)} calls to {MODEL}{' (mock)' if args.mock else ''}...", flush=True)
    done = [0]

    def run(job):
        sid, s = job
        resp = mock(sid, s) if args.mock else call(body(sheets[sid], s), key)
        done[0] += 1
        if done[0] % 2000 == 0:
            print(f"  {done[0]}/{len(jobs)}", flush=True)
        return {"sheet": sid, "sit": s["id"], "answer": (resp.get("answers") or {}).get("q"), "cost": (resp.get("usage") or {}).get("cost"), "error": resp.get("error")}

    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(run, jobs))
    (HERE / "results.json").write_text(json.dumps({"model": MODEL, "rows": rows}))
    P, refused, failed = {}, 0, 0
    for r in rows:
        v, ref = p_a(r["answer"], S[r["sit"]])
        refused += ref
        failed += (v is None and not ref)
        P[(r["sheet"], r["sit"])] = v
    cost = sum(r["cost"] or 0 for r in rows)
    g = lambda sid, i: P.get((sid, i))
    G = lambda sid, i: 0.5 if g(sid, i) is None else g(sid, i)
    f = lambda x: "  - " if x is None or x != x else f"{x:.2f}"
    with open(HERE / "matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet", "lines"] + ids)
        for sid, lines in sheets.items():
            w.writerow([sid, " | ".join(lines)] + ["" if g(sid, i) is None else f"{g(sid, i):.2f}" for i in ids])

    X = [[G(h["id"], i) for i in ids] for h in hobs]
    n = len(hobs)
    newcols = [j for j, i in enumerate(ids) if i[:3] in ("fd_", "pl_", "cr_", "pv_", "bl_")]
    oldcols = [j for j in range(len(ids)) if j not in newcols]
    def dmat(cols):
        return [[math.sqrt(sum((X[a][j] - X[b][j]) ** 2 for j in cols) / len(cols)) if a != b else 9.0 for b in range(n)] for a in range(n)]
    D = dmat(list(range(len(ids)))); Dold = dmat(oldcols)
    nn = [min(r) for r in D]; nnold = [min(r) for r in Dold]
    close = lambda M, t: sum(1 for a in range(n) for b in range(a) if M[a][b] < t)
    nlines = [len(sheets[h["id"]]) for h in hobs]
    out = [f"# Jev round 8: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} failed, {refused} refused, cost ${cost:.4f}. {n} random hobs, {len(ids)} situations.", "",
           "## 1. Uniqueness", "",
           "**Nearest neighbour**: how far each hob is from the hob most like it. Higher means more unique. **Near-clones**: pairs of hobs closer than a set distance.", "",
           f"- Nearest neighbour, all situations: mean **{mean(nn):.2f}**, smallest {min(nn):.2f}",
           f"- Near-clone pairs out of {n * (n - 1) // 2}: under 0.10: **{close(D, 0.10)}**, under 0.15: **{close(D, 0.15)}**",
           f"- Same, counting only the situations that existed before this round: nearest neighbour {mean(nnold):.2f}, pairs under 0.15: {close(Dold, 0.15)}",
           "- Round 7 for comparison: nearest neighbour 0.18, no pairs under 0.10, 11 pairs under 0.15 among 177 hobs.", "",
           "| lines on the sheet | hobs | nearest neighbour | typical distance to any hob |", "|---|---|---|---|"]
    for lo, hi in ((4, 8), (9, 12), (13, 16), (17, 20), (21, 40)):
        ix = [i for i in range(n) if lo <= nlines[i] <= hi]
        if len(ix) >= 5:
            out.append(f"| {lo} to {hi} | {len(ix)} | {mean([nn[i] for i in ix]):.2f} | {mean([D[i][j] for i in ix for j in range(n) if j != i]):.2f} |")
    a, d = variety(X)
    out += ["", f"Independent directions across the cast: **{a:.1f}** (round 7: 9.9). Typical distance: {d:.2f}.", ""]

    out += ["## 2. Every slot on its own situation", "", "| kind | slot | situation | with | without | gain | hobs |", "|---|---|---|---|---|---|---|"]
    gains = {}
    for k, items in plan["slots"].items():
        for name, spec in items.items():
            tg, sgn = spec[1], spec[2]
            a_ = [G(h["id"], tg) for h in hobs if h[k] == name]; b_ = [G(h["id"], tg) for h in hobs if h[k] != name]
            if not a_:
                continue
            if sgn is None:
                sgn = 1 if mean(a_) >= mean(b_) else -1
            gain = sgn * (mean(a_) - mean(b_)); gains.setdefault(k, []).append(gain)
            out.append(f"| {k} | {name} | {tg}: {S[tg]['instructions'].replace('{name}', NAME)[:60]} | {f(mean(a_))} | {f(mean(b_))} | {gain:+.2f} | {len(a_)} |")
    out += ["", "| kind | slots | mean gain on own situation | weakest | strongest |", "|---|---|---|---|---|"] + \
           [f"| {k} | {len(v)} | {mean(v):+.2f} | {min(v):+.2f} | {max(v):+.2f} |" for k, v in gains.items()]

    out += ["", "## 3. Does a full trait sheet still work?", "",
            "Mean P on each trait's own situation at strength +3 and -3, for hobs with few traits and hobs with many.", "",
            "| traits on sheet | hobs | at +3 | not stated | at -3 |", "|---|---|---|---|---|"]
    for lo, hi in ((4, 7), (8, 10), (11, 14)):
        hs = [h for h in hobs if lo <= len(h["traits"]) <= hi]
        cells = []
        for L in (3, 0, -3):
            per = []
            for a_, (tg, sgn) in plan["own"].items():
                if tg not in S:
                    continue
                v = [G(h["id"], tg) for h in hs if h["traits"].get(a_, 0) == L]
                if v:
                    m = mean(v); per.append(m if sgn > 0 else 1 - m)
            cells.append(f(mean(per)))
        out.append(f"| {lo} to {hi} | {len(hs)} | " + " | ".join(cells) + " |")
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print(f"Done. {failed} failed, {refused} refused, cost ${cost:.4f}. Report: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
