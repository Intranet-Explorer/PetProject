#!/usr/bin/env python3
"""Round 6: 300 random hobs built from a slot template, to find which slots matter.

Template:  IQ | traits (3 to 10 of 11, each at one of three strengths) | quirks (0 to 2)
           | learned quirk (half of hobs) | odd or defective trait (15 percent of hobs)
Half the hobs have strengths written as words ("a little brave"), half as numbers ("brave, 30 out of 100").

Report covers: how far to trust the numbers (reworded questions), which slots change behaviour most,
whether strengths step properly in words and in numbers, what IQ does, whether learned quirks stick,
and how many traits a sheet should carry.

    export OPENROUTER_API_KEY=...
    python3 run6.py           # about 19,200 calls, roughly 12 minutes, about 35 cents
    python3 run6.py --mock

Writes report.md, matrix.csv, features.csv and results.json. Everything tested is in plan.json.
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



IQN = {-2: 10, -1: 30, 1: 70, 2: 95}
LVN = {1: 30, 2: 60, 3: 95}
LVW = {1: "a little ", 2: "", 3: "extremely "}
SMART = ["q1", "q2", "q3", "q4", "q5", "q6"]


def render(h, plan):
    L, num = [], h["fmt"] == "numbers"
    if h["iq"]:
        L.append(f"intelligence, {IQN[h['iq']]} out of 100 (100 is the cleverest hob there has ever been)" if num else plan["iq"][str(h["iq"])])
    for a, v in h["traits"].items():
        label, text = plan["axes"][a]["A" if v > 0 else "B"]
        L.append(f"{label}, {LVN[abs(v)]} out of 100: {text}" if num else f"{LVW[abs(v)]}{label}: {text}")
    L += [f"{w}, {d}" for w, d in h["quirks"]]
    if h["learned"]:
        L.append(plan["learned"][h["learned"]][0])
    if h["defect"]:
        L.append(plan["defect"][h["defect"]])
    return L


def rms(xs):
    xs = [x for x in xs if x == x]
    return math.sqrt(sum(x * x for x in xs) / len(xs)) if xs else float("nan")


def corr(a, b):
    ma, mb = mean(a), mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    sits = json.loads((HERE / "situations6.json").read_text())
    plan = json.loads((HERE / "plan.json").read_text())
    hobs = plan["hobs"]
    S = {s["id"]: s for s in sits}
    core = [s["id"] for s in sits if s["group"] != "para"]
    para = [s for s in sits if s["group"] == "para"]
    key = os.environ.get("OPENROUTER_API_KEY")
    if not args.mock and not key:
        sys.exit("Set OPENROUTER_API_KEY, or use --mock.")
    sheets = {"empty": []}
    for h in hobs:
        sheets[h["id"]] = render(h, plan)
    npara = plan["n_para_hobs"]
    jobs = [(sid, S[i]) for sid in sheets for i in core] + [(h["id"], s) for h in hobs[:npara] for s in para] + [("empty", s) for s in para]
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
    allids = [s["id"] for s in sits]
    with open(HERE / "matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet", "lines"] + allids)
        for sid, lines in sheets.items():
            w.writerow([sid, " | ".join(lines)] + ["" if g(sid, i) is None else f"{g(sid, i):.2f}" for i in allids])
    axes = list(plan["axes"])
    with open(HERE / "features.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "fmt", "iq", "n_traits"] + axes + ["quirk1", "quirk2", "learned", "defect"])
        for h in hobs:
            q = [d for _, d in h["quirks"]] + ["", ""]
            w.writerow([h["id"], h["fmt"], h["iq"], len(h["traits"])] + [h["traits"].get(a, 0) for a in axes] + q[:2] + [h["learned"] or "", h["defect"] or ""])

    out = [f"# Jev round 6: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} failed, {refused} refused, cost ${cost:.4f}. 300 random hobs, {len(core)} situations.", ""]

    # 1 rewording
    out += ["## 1. How far to trust a number", "",
            "Ten situations were each asked three ways to the same 100 hobs. **Agreement**: do the same hobs score high and low under a different wording (1.00 = identical ranking)? "
            "**Gap**: how far the actual number moves between wordings.", "",
            "| situation | agreement, wording 2 | agreement, wording 3 | gap, wording 2 | gap, wording 3 | blank hob: original / 2 / 3 |", "|---|---|---|---|---|---|"]
    ph = [h["id"] for h in hobs[:npara]]
    ag, gp = [], []
    for b in plan["paraphrased"]:
        o = [G(h, b) for h in ph]
        c, d = [], []
        for i in (1, 2):
            p = [G(h, f"{b}_p{i}") for h in ph]
            c.append(corr(o, p)); d.append(mean([abs(x - y) for x, y in zip(o, p)]))
        ag += c; gp += d
        out.append(f"| {b} | {c[0]:.2f} | {c[1]:.2f} | {d[0]:.2f} | {d[1]:.2f} | {f(g('empty', b))} / {f(g('empty', b + '_p1'))} / {f(g('empty', b + '_p2'))} |")
    out += [f"| **mean** | **{mean(ag):.2f}** | | **{mean(gp):.2f}** | | |", ""]

    # 2 slot importance
    ids = core
    X = {h["id"]: [G(h["id"], i) for i in ids] for h in hobs}
    idx = list(range(len(hobs)))
    def slope_effect(vals, span, sub=None):
        sub = idx if sub is None else sub
        mx = mean([vals[i] for i in sub]); vx = sum((vals[i] - mx) ** 2 for i in sub)
        if not vx:
            return [0.0] * len(ids)
        return [span * sum((vals[i] - mx) * X[hobs[i]["id"]][j] for i in sub) / vx for j in range(len(ids))]
    def group_effect(flags, sub=None):
        sub = idx if sub is None else sub
        a = [X[hobs[i]["id"]] for i in sub if flags[i]]; b = [X[hobs[i]["id"]] for i in sub if not flags[i]]
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
    add("IQ", "IQ", slope_effect, [h["iq"] for h in hobs], 300, 4)
    for a_ in axes:
        add("trait", a_, slope_effect, [h["traits"].get(a_, 0) for h in hobs], sum(a_ in h["traits"] for h in hobs), 6)
    QF = {d: [any(q[1] == d for q in h["quirks"]) for h in hobs] for d in plan["does"]}
    for d, fl in QF.items():
        add("quirk", d, group_effect, fl, sum(fl))
    for k in plan["learned"]:
        fl = [h["learned"] == k for h in hobs]; add("learned", plan["learned"][k][0], group_effect, fl, sum(fl))
    for k in plan["defect"]:
        fl = [h["defect"] == k for h in hobs]; add("defect", plan["defect"][k], group_effect, fl, sum(fl))
    add("format", "numbers instead of words", group_effect, [h["fmt"] == "numbers" for h in hobs], 150)
    add("count", "number of traits (3 to 10)", slope_effect, [len(h["traits"]) for h in hobs], 300, 7)
    out += ["## 2. Which slots change behaviour", "",
            "**Effect**: typical change in a hob's answers across all situations when this slot goes from one extreme to the other (traits and IQ) or is present (the rest). "
            "**Noise**: the effect a meaningless slot of the same size would show by chance. Only the part of an effect above its noise is real.", "",
            "| kind | slot | effect | noise | hobs with it | moves most |", "|---|---|---|---|---|---|"]
    for kind, name, e, n, fl in sorted(E, key=lambda t: -(rms(t[2]) - t[4])):
        top = sorted(range(len(ids)), key=lambda j: -abs(e[j]))[:3]
        out.append(f"| {kind} | {name[:70]} | {rms(e):.2f} | {fl:.2f} | {n} | " + ", ".join(f"{ids[j]} {e[j]:+.2f}" for j in top) + " |")
    out += ["", "| kind | slots | mean effect | mean noise | clearly above noise |", "|---|---|---|---|---|"]
    for kind in dict.fromkeys(t[0] for t in E):
        es = [(rms(e), fl) for k, _, e, _, fl in E if k == kind]
        out.append(f"| {kind} | {len(es)} | {mean([a for a, _ in es]):.2f} | {mean([b for _, b in es]):.2f} | {sum(a > 1.5 * b for a, b in es)} |")

    # 3 strength steps (each format is measured against the direction learned from the OTHER format, so chance reads 0)
    out += ["", "## 3. Do strengths step?", "",
            "Each trait's pull at strength 1, 2 and 3. An even staircase reads 1, 2, 3; a slot that does nothing reads 0. "
            "Each column is scored against the other column's hobs, so the two are directly comparable.", "",
            "| strength | words (a little / plain / extremely) | numbers (30 / 60 / 95 out of 100) |", "|---|---|---|"]
    step = {(fm, L): [] for fm in ("words", "numbers") for L in (1, 2, 3)}
    bysub = {fm: [i for i in idx if hobs[i]["fmt"] == fm] for fm in ("words", "numbers")}
    for a_ in axes:
        vals = [h["traits"].get(a_, 0) for h in hobs]
        for fm, other in (("words", "numbers"), ("numbers", "words")):
            d = slope_effect(vals, 1, bysub[other])
            dd = sum(x * x for x in d) or 1e-9
            base = [X[hobs[i]["id"]] for i in bysub[fm] if vals[i] == 0]
            if len(base) < 5:
                continue
            bm = [mean([r[j] for r in base]) for j in range(len(ids))]
            for sgn in (1, -1):
                for L in (1, 2, 3):
                    grp = [X[hobs[i]["id"]] for i in bysub[fm] if vals[i] == sgn * L]
                    if len(grp) >= 3:
                        gm = [mean([r[j] for r in grp]) for j in range(len(ids))]
                        step[(fm, L)].append(sgn * sum((gm[j] - bm[j]) * d[j] for j in range(len(ids))) / dd)
    for L in (1, 2, 3):
        out.append(f"| {L} | {mean(step[('words', L)]):.2f} | {mean(step[('numbers', L)]):.2f} |")

    # 4 IQ
    out += ["", "## 4. IQ", "", "Mean P(the smart answer) over six problem situations.", "",
            "| IQ | words | numbers | " + " | ".join(SMART) + " |", "|---|---|---|" + "---|" * len(SMART),
            f"| blank hob | {f(mean([g('empty', i) for i in SMART]))} | | " + " | ".join(f(g("empty", i)) for i in SMART) + " |"]
    names = {-2: "very dim / 10", -1: "a bit slow / 30", 0: "not stated", 1: "sharp / 70", 2: "brilliant / 95"}
    for lv in (-2, -1, 0, 1, 2):
        cells = [f(mean([G(h["id"], i) for h in hobs if h["iq"] == lv and h["fmt"] == fm for i in SMART])) for fm in ("words", "numbers")]
        out.append(f"| {names[lv]} | {cells[0]} | {cells[1]} | " + " | ".join(f(mean([G(h["id"], i) for h in hobs if h["iq"] == lv])) for i in SMART) + " |")

    # 5 learned
    out += ["", "## 5. Learned quirks", "", "| learned quirk | target | P(target) with it | without it | hobs |", "|---|---|---|---|---|"]
    for k, (line, tg) in plan["learned"].items():
        a = [G(h["id"], tg) for h in hobs if h["learned"] == k]; b = [G(h["id"], tg) for h in hobs if h["learned"] != k]
        out.append(f"| {line} | {tg}: {S[tg]['instructions'].replace('{name}', NAME)} | {f(mean(a))} | {f(mean(b))} | {len(a)} |")

    # 6 how many traits
    em = [G("empty", i) for i in ids]
    out += ["", "## 6. How many traits?", "",
            "**From blank**: how far the hob sits from a blank hob. **Quirk still shows**: how strongly quirks act on these hobs, relative to how they act on all the other hobs (1.00 = full strength, 0 = drowned out).", "",
            "| traits on sheet | hobs | from blank | quirk still shows |", "|---|---|---|---|"]
    for lo, hi in ((3, 4), (5, 6), (7, 8), (9, 10)):
        inb = [i for i in idx if lo <= len(hobs[i]["traits"]) <= hi]; outb = [i for i in idx if i not in inb]
        dist = mean([math.sqrt(mean([(X[hobs[i]["id"]][j] - em[j]) ** 2 for j in range(len(ids))])) for i in inb])
        qs = []
        for d, fl in QF.items():
            e = group_effect(fl, outb)
            mine = group_effect(fl, inb)
            if e and mine:
                ee = sum(x * x for x in e) or 1e-9
                qs.append(sum(mine[j] * e[j] for j in range(len(ids))) / ee)
        out.append(f"| {lo} to {hi} | {len(inb)} | {dist:.2f} | {mean(qs):.2f} |")

    # 7 variety
    a, d = variety([X[h["id"]] for h in hobs])
    out += ["", "## 7. Variety of the whole cast", "", f"300 random hobs: **{a:.1f}** independent directions, typical distance **{d:.2f}**.",
            "Earlier casts on a different battery, for rough comparison only: old ten-trait sheet 5.7 and 0.29; four temperament lines plus extras 4.8 and 0.29."]
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print(f"Done. {failed} failed, {refused} refused, cost ${cost:.4f}. Report: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
