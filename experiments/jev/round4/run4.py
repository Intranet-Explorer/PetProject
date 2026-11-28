#!/usr/bin/env python3
"""Round 4: behaviour-only descriptors, the 'becoming' ladder, a quirk generator, and the cast test.

  1. Motive vs behaviour  8 concepts, each written both ways. Does behaviour-only wording win?
  2. Becoming             a hob's record grows a line at a time (killer, maker, thief paths).
                          Does each line make the next step more likely?
  3. Generator            40 random 'when + does' behaviour lines, scored for whether they are
                          distinct, contained, and what Jev thinks they imply.
  4. Cast                 20 hobs on the old ten-trait sheet vs 20 on layered sheets
                          (two behaviours + a want + maybe a state). Which cast is more varied?

    export OPENROUTER_API_KEY=...
    python3 run4.py           # about 15,600 calls, roughly 10 minutes, about 30 cents
    python3 run4.py --mock    # no network; checks the pipeline

Writes report.md, matrix.csv (every sheet x every situation) and results.json.
Everything tested is in plan.json; edit it and rerun.
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
DECENCY = ["gen1", "kind4", "kind2", "gen4", "hl1"]
VIOLENCE = ["k1", "k2", "k3", "k4", "k5"]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    sits = json.loads((HERE / "situations4.json").read_text())
    traits = json.loads((HERE / "traits_v1.json").read_text())
    plan = json.loads((HERE / "plan.json").read_text())
    S = {s["id"]: s for s in sits}
    ids = [s["id"] for s in sits]
    key = os.environ.get("OPENROUTER_API_KEY")
    if not args.mock and not key:
        sys.exit("Set OPENROUTER_API_KEY, or use --mock.")
    tline = {t["id"]: f"{t['label']}: {t['text']}" for t in traits}
    decent = [tline[i] for i in DECENT]

    sheets = {"empty": [], "decent": decent}
    for t in traits:
        sheets["t:" + t["id"]] = [tline[t["id"]]]
    for p in plan["pairs"]:
        for form in ("motive", "behavior"):
            sheets[f"p:{p['concept']}:{form}:alone"] = [p[form]]
            sheets[f"p:{p['concept']}:{form}:decent"] = decent + [p[form]]
    for path, lines in plan["paths"].items():
        for k in range(1, len(lines) + 1):
            sheets[f"path:{path}:{k}:empty"] = lines[:k]
            sheets[f"path:{path}:{k}:decent"] = decent + lines[:k]
    for g in plan["generated"]:
        sheets[f"g:{g['id']}:alone"] = [g["line"]]
        sheets[f"g:{g['id']}:decent"] = decent + [g["line"]]
    for i, L in enumerate(plan["cast_old"]):
        sheets[f"cast:old:{i}"] = L
    for i, L in enumerate(plan["cast_layered"]):
        sheets[f"cast:layered:{i}"] = L

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
    P, refused, failed = {}, [], 0
    for r in rows:
        v, ref = p_a(r["answer"], S[r["sit"]])
        if ref:
            refused.append((r["sheet"], r["sit"]))
        elif v is None:
            failed += 1
        P[(r["sheet"], r["sit"])] = v
    cost = sum(r["cost"] or 0 for r in rows)
    g = lambda sid, i: P.get((sid, i))
    vec = lambda sid: [0.5 if g(sid, i) is None else g(sid, i) for i in ids]
    avg = lambda sid, group: mean([g(sid, i) for i in group])
    f = lambda x: "  - " if x is None or x != x else f"{x:.2f}"

    with open(HERE / "matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet", "lines"] + ids)
        for sid, lines in sheets.items():
            w.writerow([sid, " | ".join(lines)] + ["" if g(sid, i) is None else f"{g(sid, i):.2f}" for i in ids])

    tv = {t["id"]: vec("t:" + t["id"]) for t in traits}
    mu, vecs = dials(list(tv.values()))
    loo = [outside(tv[t["id"]], *dials([v for i, v in tv.items() if i != t["id"]]))[0] for t in traits]
    ref = statistics.median(loo)
    dec0 = avg("decent", DECENCY)

    out = [f"# Jev round 4: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} failed, {len(refused)} refused by Jev, cost ${cost:.4f}.", "",
           f"Reference points: the plain decent hob scores **{dec0:.2f}** on decency; an ordinary adjective trait sits about **{ref:.0%}** outside the three dials.", ""]
    if refused:
        cnt = {}
        for sh, si in refused:
            cnt[si] = cnt.get(si, 0) + 1
        out += ["Refusals by situation: " + ", ".join(f"{k} x{v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])), ""]

    # ---- 1
    out += ["## 1. Motive vs behaviour", "",
            "Same concept written as a motive and as a plain behaviour, each added to the decent hob. "
            "**Does it**: mean P(signature behaviour). **Decency**: still shares, forgives, reassures. **Outside**: share the dials can't reproduce.", "",
            "| concept | wording | does it (decent hob alone) | does it (with line) | spill | decency | outside dials |", "|---|---|---|---|---|---|---|"]
    tot = {"motive": [], "behavior": []}
    for p in plan["pairs"]:
        for form in ("motive", "behavior"):
            d, a = f"p:{p['concept']}:{form}:decent", f"p:{p['concept']}:{form}:alone"
            non = [i for i in ids if i not in p["targets"]]
            spill = mean([abs(g(d, i) - g("decent", i)) for i in non if g(d, i) is not None and g("decent", i) is not None])
            row = (avg(d, p["targets"]), spill, avg(d, [i for i in DECENCY if i not in p["targets"]]), outside(vec(a), mu, vecs)[0])
            tot[form].append(row)
            out.append(f"| {p['concept']} | {form} | {f(avg('decent', p['targets']))} | {f(row[0])} | {row[1]:.2f} | {f(row[2])} | {row[3]:.0%} |")
    for form in tot:
        out.append(f"| **mean** | **{form}** | | {mean([r[0] for r in tot[form]]):.2f} | {mean([r[1] for r in tot[form]]):.2f} | {mean([r[2] for r in tot[form]]):.2f} | {mean([r[3] for r in tot[form]]):.0%} |")

    # ---- 2
    out += ["", "## 2. Becoming", "",
            "Each row adds one more line to the hob's record. Columns are P(does it) for each step of the ladder. "
            "If the record drives behaviour, numbers should rise down each column, and later columns should need a longer record.", ""]
    ladders = {"killer": VIOLENCE, "maker": MAKING, "thief": ["st1", "st2", "st3", "st4", "st5"]}
    for path, lines in plan["paths"].items():
        cols = ladders[path]
        for base in ("empty", "decent"):
            out += [f"**{path} path, on {'a blank hob' if base == 'empty' else 'the decent hob'}**", "",
                    "| record | " + " | ".join(cols) + " | decency | making | violence |", "|---|" + "---|" * (len(cols) + 3)]
            for k in range(0, len(lines) + 1):
                sid = base if k == 0 else f"path:{path}:{k}:{base}"
                label = "nothing yet" if k == 0 else f"+{k}: {lines[k - 1][:48]}"
                out.append(f"| {label} | " + " | ".join(f(g(sid, c)) for c in cols) + f" | {f(avg(sid, DECENCY))} | {f(avg(sid, MAKING))} | {f(avg(sid, VIOLENCE))} |")
            out.append("")

    # ---- 3
    G = []
    for x in plan["generated"]:
        a, d = f"g:{x['id']}:alone", f"g:{x['id']}:decent"
        o, size = outside(vec(a), mu, vecs)
        spill = mean([abs(g(d, i) - g("decent", i)) for i in ids if g(d, i) is not None and g("decent", i) is not None])
        top = sorted([i for i in ids if g(a, i) is not None and g("empty", i) is not None], key=lambda i: -abs(g(a, i) - g("empty", i)))[:3]
        G.append({**x, "outside": o, "size": size, "spill": spill, "decency": avg(d, DECENCY),
                  "violence": avg(d, VIOLENCE) - avg("decent", VIOLENCE), "making": avg(d, MAKING) - avg("decent", MAKING),
                  "top": [(i, g(a, i) - g("empty", i)) for i in top]})
    keep = [x for x in G if x["outside"] >= 0.5 and x["decency"] >= 0.85 and x["size"] >= 0.10]
    out += ["## 3. Generator", "",
            f"40 random behaviour lines. **Keepers** (distinct, contained, and big enough to notice): **{len(keep)}/40**. "
            "Violence and making are the change against the decent hob.", "",
            "| line | size | spill | decency | outside | violence | making | moves most |", "|---|---|---|---|---|---|---|---|"]
    for x in sorted(G, key=lambda x: -x["outside"]):
        out.append(f"| {'**' if x in keep else ''}{x['line']}{'**' if x in keep else ''} | {x['size']:.2f} | {x['spill']:.2f} | {f(x['decency'])} | {x['outside']:.0%} | {x['violence']:+.2f} | {x['making']:+.2f} | "
                   + ", ".join(f"{i} {v:+.2f}" for i, v in x["top"]) + " |")

    # ---- 4
    old48 = [j for j, s in enumerate(sits) if s.get("set") == "old"]
    out += ["", "## 4. Cast", "",
            "20 random hobs each way. **Directions**: effective number of independent ways the hobs differ. **Distance**: how far apart two hobs typically are.", "",
            "| cast | directions (all 79 situations) | distance | directions (original 48 only) | distance |", "|---|---|---|---|---|"]
    for name in ("old", "layered"):
        R = [vec(f"cast:{name}:{i}") for i in range(20)]
        a1, d1 = variety(R)
        a2, d2 = variety([[r[j] for j in old48] for r in R])
        out.append(f"| {name} | {a1:.1f} | {d1:.2f} | {a2:.1f} | {d2:.2f} |")
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print(f"Done. {failed} failed, {len(refused)} refused, cost ${cost:.4f}. Report: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
