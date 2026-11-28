#!/usr/bin/env python3
"""Round 7: improve the template. IQ is out; values, fears, age, body and three new traits are in.

360 random hobs. Each has 5 to 9 of 14 traits, plus (by chance) quirks, a learned quirk,
an odd trait, a core value, a fear, an age and a body size.
Half the hobs write trait strength as a named side ("brave, 60 out of 100"),
half as one slider ("timid to brave: 80 out of 100").

    export OPENROUTER_API_KEY=...
    python3 run7.py           # about 26,400 calls, roughly 16 minutes, about 60 cents
    python3 run7.py --mock

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
SLIDE = {-3: 5, -2: 20, -1: 35, 1: 65, 2: 80, 3: 95}
KINDS = ["value", "fear", "age", "body", "learned", "defect"]


def render(h, plan):
    L = []
    for a, v in h["traits"].items():
        A, B = plan["axes"][a]["A"], plan["axes"][a]["B"]
        if h["fmt"] == "slider":
            L.append(f"{B[0]} to {A[0]}: {SLIDE[v]} out of 100 (0 = {B[1]}; 100 = {A[1]})")
        else:
            label, text = A if v > 0 else B
            L.append(f"{label}, {POLE[abs(v)]} out of 100: {text}")
    for k in ("age", "body", "value", "fear"):
        if h[k]:
            L.append(plan[k][h[k]][0])
    L += [f"{w}, {d}" for w, d in h["quirks"]]
    if h["learned"]:
        L.append(plan["learned"][h["learned"]][0])
    if h["defect"]:
        L.append(plan["defect"][h["defect"]])
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    sits = json.loads((HERE / "situations7.json").read_text())
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
        if done[0] % 1000 == 0:
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

    X = {h["id"]: [G(h["id"], i) for i in ids] for h in hobs}
    idx = list(range(len(hobs)))
    def slope_effect(vals, span):
        mx = mean(vals); vx = sum((v - mx) ** 2 for v in vals)
        if not vx:
            return None
        return [span * sum((vals[i] - mx) * X[hobs[i]["id"]][j] for i in idx) / vx for j in range(len(ids))]
    def group_effect(flags):
        a = [X[hobs[i]["id"]] for i in idx if flags[i]]; b = [X[hobs[i]["id"]] for i in idx if not flags[i]]
        if len(a) < 4 or len(b) < 4:
            return None
        return [mean([r[j] for r in a]) - mean([r[j] for r in b]) for j in range(len(ids))]
    rng = random.Random(0)
    def floor(fn, vals, *a):
        fl = []
        for _ in range(5):
            v = vals[:]; rng.shuffle(v); e = fn(v, *a)
            if e: fl.append(rms(e))
        return mean(fl)
    E = []
    def add(kind, name, fn, vals, n, *a):
        e = fn(vals, *a)
        if e:
            E.append((kind, name, e, n, floor(fn, vals, *a)))
    axes = list(plan["axes"])
    for a_ in axes:
        add("trait", a_, slope_effect, [h["traits"].get(a_, 0) for h in hobs], sum(a_ in h["traits"] for h in hobs), 6)
    for k in KINDS:
        for name in plan[k]:
            fl = [h[k] == name for h in hobs]; add(k, f"{name}: {plan[k][name][0] if isinstance(plan[k][name], list) else plan[k][name]}", group_effect, fl, sum(fl))
    for d in plan["does"]:
        fl = [any(q[1] == d for q in h["quirks"]) for h in hobs]; add("quirk", d, group_effect, fl, sum(fl))
    add("format", "slider instead of named side", group_effect, [h["fmt"] == "slider" for h in hobs], sum(h["fmt"] == "slider" for h in hobs))

    out = [f"# Jev round 7: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} failed, {refused} refused, cost ${cost:.4f}. {len(hobs)} random hobs, {len(ids)} situations.", "",
           "## 1. Slot kinds", "",
           "**Effect**: typical change across all situations. **Noise**: what a meaningless slot of the same size shows by chance.", "",
           "| kind | slots | mean effect | mean noise | clearly above noise |", "|---|---|---|---|---|"]
    for kind in dict.fromkeys(t[0] for t in E):
        es = [(rms(e), fl) for k, _, e, _, fl in E if k == kind]
        out.append(f"| {kind} | {len(es)} | {mean([a for a, _ in es]):.2f} | {mean([b for _, b in es]):.2f} | {sum(a > 1.5 * b for a, b in es)} |")

    out += ["", "## 2. New slots on their own situation", "",
            "P(does the thing the slot is about), with the slot and without it. Signed so that a working slot shows a positive gain.", "",
            "| kind | slot | situation | with | without | gain | hobs |", "|---|---|---|---|---|---|---|"]
    gains = {}
    for k in ("value", "fear", "age", "body", "learned"):
        for name, spec in plan[k].items():
            tg, sgn = spec[1], (spec[2] if len(spec) > 2 else None)
            a = [G(h["id"], tg) for h in hobs if h[k] == name]; b = [G(h["id"], tg) for h in hobs if h[k] != name]
            if sgn is None:
                sgn = 1 if mean(a) >= mean(b) else -1
            gain = sgn * (mean(a) - mean(b)); gains.setdefault(k, []).append(gain)
            out.append(f"| {k} | {name} | {tg}: {S[tg]['instructions'].replace('{name}', NAME)} | {f(mean(a))} | {f(mean(b))} | {gain:+.2f} | {len(a)} |")
    out += ["", "| kind | mean gain on own situation |", "|---|---|"] + [f"| {k} | {mean(v):+.2f} |" for k, v in gains.items()]

    out += ["", "## 3. Strength: named side against slider", "",
            "Mean P on each trait's own situation, lined up so higher always means more of the trait's first side. A good scale climbs evenly left to right.", "",
            "| format | -3 | -2 | -1 | not stated | +1 | +2 | +3 |", "|---|---|---|---|---|---|---|---|"]
    for fm in ("pole", "slider"):
        cells = []
        for L in (-3, -2, -1, 0, 1, 2, 3):
            per = []
            for a_, (tg, sgn) in plan["own"].items():
                v = [G(h["id"], tg) for h in hobs if h["fmt"] == fm and h["traits"].get(a_, 0) == L]
                if v:
                    m = mean(v); per.append(m if sgn > 0 else 1 - m)
            cells.append(f(mean(per)))
        out.append(f"| {'named side (30 / 60 / 95)' if fm == 'pole' else 'slider (5 to 95)'} | " + " | ".join(cells) + " |")
    out += ["", "Per trait, slider format:", "", "| trait | situation | -3 | -2 | -1 | not stated | +1 | +2 | +3 |", "|---|---|---|---|---|---|---|---|---|"]
    for a_, (tg, sgn) in plan["own"].items():
        cells = []
        for L in (-3, -2, -1, 0, 1, 2, 3):
            v = [G(h["id"], tg) for h in hobs if h["fmt"] == "slider" and h["traits"].get(a_, 0) == L]
            cells.append(f((mean(v) if sgn > 0 else 1 - mean(v)) if v else None))
        out.append(f"| {a_} | {tg} | " + " | ".join(cells) + " |")

    out += ["", "## 4. Every slot", "", "| kind | slot | effect | noise | hobs | moves most |", "|---|---|---|---|---|---|"]
    for kind, name, e, n, fl in sorted(E, key=lambda t: -(rms(t[2]) - t[4])):
        top = sorted(range(len(ids)), key=lambda j: -abs(e[j]))[:3]
        out.append(f"| {kind} | {name[:64]} | {rms(e):.2f} | {fl:.2f} | {n} | " + ", ".join(f"{ids[j]} {e[j]:+.2f}" for j in top) + " |")

    a, d = variety([X[h["id"]] for h in hobs])
    out += ["", "## 5. Variety", "", f"{len(hobs)} random hobs: **{a:.1f}** independent directions, typical distance **{d:.2f}**. Round 6 (IQ, 11 traits, 57 situations) was 7.7 and 0.34.", ""]
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print(f"Done. {failed} failed, {refused} refused, cost ${cost:.4f}. Report: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
