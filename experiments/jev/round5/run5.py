#!/usr/bin/env python3
"""Round 5: a wider battery, new kinds of line, and the cast test done properly.

  1. Relationships  does a line about Pim change behaviour toward Pim and nobody else?
  2. Roles, states, visitor lines   what each one moves.
  3. Intensity      do "slightly / (plain) / extremely" give graded behaviour?
  4. Cast           old ten-trait sheets vs temperament only vs temperament + quirks + want + record.
  5. Dilution       does a quirk still work on a 4, 8 or 12 line sheet, first or last?
  6. Becoming       the killer and maker records on a cold hob and a kind hob.

    export OPENROUTER_API_KEY=...
    python3 run5.py           # about 18,700 calls, roughly 12 minutes, about 35 cents
    python3 run5.py --mock

Writes report.md, matrix.csv and results.json. Everything tested is in plan.json.
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
    sits = json.loads((HERE / "situations5.json").read_text())
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
    for x in plan["lines"]:
        sheets[f"l:{x['id']}:alone"] = [x["line"]]
        sheets[f"l:{x['id']}:decent"] = decent + [x["line"]]
    for name in ("old", "temper", "full"):
        for i, L in enumerate(plan["cast_" + name]):
            sheets[f"cast:{name}:{i}"] = L
    for x in plan["focus"]:
        sheets[f"dil:{x['id']}:1:alone"] = [x["line"]]
    for d in plan["dilution"]:
        sheets["dil:" + d["id"]] = d["lines"]
    for base, bl in plan["bases"].items():
        sheets[f"base:{base}"] = bl
        for path in ("killer", "maker"):
            if base == "kind" and path == "maker":
                continue
            for k in range(1, len(plan["paths"][path]) + 1):
                sheets[f"path:{path}:{k}:{base}"] = bl + plan["paths"][path][:k]

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
    vec = lambda sid: [0.5 if g(sid, i) is None else g(sid, i) for i in ids]
    avg = lambda sid, group: mean([g(sid, i) for i in group])
    f = lambda x: "  - " if x is None or x != x else f"{x:.2f}"
    sh = lambda a, b, group: mean([g(a, i) - g(b, i) for i in group if g(a, i) is not None and g(b, i) is not None])

    with open(HERE / "matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet", "lines"] + ids)
        for sid, lines in sheets.items():
            w.writerow([sid, " | ".join(lines)] + ["" if g(sid, i) is None else f"{g(sid, i):.2f}" for i in ids])

    tv = {t["id"]: vec("t:" + t["id"]) for t in traits}
    mu, vecs = dials(list(tv.values()))
    ref = statistics.median([outside(tv[t["id"]], *dials([v for i, v in tv.items() if i != t["id"]]))[0] for t in traits])
    out = [f"# Jev round 5: {MODEL}{' (MOCK DATA)' if args.mock else ''}", "",
           f"{len(rows)} calls, {failed} failed, {refused} refused, cost ${cost:.4f}. {len(ids)} situations.", "",
           f"Reference: decent hob decency **{avg('decent', DECENCY):.2f}**; an ordinary adjective trait is about **{ref:.0%}** outside the dials.", ""]

    # 1 relationships
    pim, ott = plan["pim"], plan["ott"]
    rest = [i for i in ids if i not in pim + ott]
    out += ["## 1. Relationships", "",
            "Change against the decent hob, averaged over situations involving Pim, involving Ottoline, and everything else (absolute change). "
            "A good relationship line moves one column and not the others.", "",
            "| line | toward Pim | toward Ottoline | everything else | " + " | ".join(pim + ott) + " |", "|---|---|---|---|" + "---|" * len(pim + ott)]
    for x in plan["lines"]:
        if x["kind"] != "relationship":
            continue
        d = f"l:{x['id']}:decent"
        spill = mean([abs(g(d, i) - g("decent", i)) for i in rest if g(d, i) is not None and g("decent", i) is not None])
        out.append(f"| {x['line']} | {sh(d, 'decent', pim):+.2f} | {sh(d, 'decent', ott):+.2f} | {spill:.2f} | " + " | ".join(f(g(d, i)) for i in pim + ott) + " |")
    out.append("| (decent hob alone) | | | | " + " | ".join(f(g("decent", i)) for i in pim + ott) + " |")

    # 2 roles, states, visitor
    out += ["", "## 2. Roles, states and visitor lines", "",
            "| line | kind | size | spill on decent | decency | outside dials | moves most (alone, vs blank hob) |", "|---|---|---|---|---|---|---|"]
    for x in plan["lines"]:
        if x["kind"] in ("relationship", "intensity"):
            continue
        a, d = f"l:{x['id']}:alone", f"l:{x['id']}:decent"
        o, size = outside(vec(a), mu, vecs)
        spill = mean([abs(g(d, i) - g("decent", i)) for i in ids if g(d, i) is not None and g("decent", i) is not None])
        top = sorted([i for i in ids if g(a, i) is not None and g("empty", i) is not None], key=lambda i: -abs(g(a, i) - g("empty", i)))[:5]
        out.append(f"| {x['line']} | {x['kind']} | {size:.2f} | {spill:.2f} | {f(avg(d, DECENCY))} | {o:.0%} | " + ", ".join(f"{i} {g(a, i) - g('empty', i):+.2f}" for i in top) + " |")

    # 3 intensity
    kindsits = [s["id"] for s in sits if s["axis"] == "kind_prickly"]
    bravesits = ["brave1", "brave3", "brave4", "per4"]
    out += ["", "## 3. Intensity", "",
            "If graded wording gives graded behaviour, each row should step evenly. Prickly: P(the kind answer), lower = pricklier. Brave: P(the brave answer).", "",
            "| level | prickly: kind-axis mean | brave: danger mean |", "|---|---|---|",
            f"| blank hob | {f(avg('empty', kindsits))} | {f(avg('empty', bravesits))} |",
            f"| slightly / a little | {f(avg('l:prickly_1:alone', kindsits))} | {f(avg('l:brave_1:alone', bravesits))} |",
            f"| plain | {f(avg('t:prickly_v1', kindsits))} | {f(avg('t:brave_v1', bravesits))} |",
            f"| extremely / utterly | {f(avg('l:prickly_3:alone', kindsits))} | {f(avg('l:brave_3:alone', bravesits))} |"]

    # 4 cast
    sets = {"all": list(range(len(ids))), "original 48": [j for j, s in enumerate(sits) if s.get("set") == "old"],
            "wide 40": [j for j, s in enumerate(sits) if s.get("set") == "wide"]}
    out += ["", "## 4. Cast", "",
            "20 hobs each. **old**: ten adjective traits. **temper**: four temperament lines. **full**: the same four, plus two quirks, a want, a record line, and sometimes a relationship or state. "
            "Directions = independent ways the hobs differ. Distance = how far apart two hobs typically are.", "",
            "| cast | " + " | ".join(f"directions ({k}) | distance ({k})" for k in sets) + " |", "|---|" + "---|---|" * len(sets)]
    for name in ("old", "temper", "full"):
        R = [vec(f"cast:{name}:{i}") for i in range(20)]
        cells = []
        for cols in sets.values():
            a, d = variety([[r[j] for j in cols] for r in R])
            cells += [f"{a:.1f}", f"{d:.2f}"]
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    pair = mean([math.sqrt(sum((a - b) ** 2 for a, b in zip(vec(f"cast:temper:{i}"), vec(f"cast:full:{i}"))) / len(ids)) for i in range(20)])
    out += ["", f"Same temperament, with and without the extra lines: the two versions of a hob sit **{pair:.2f}** apart on average."]

    # 5 dilution
    out += ["", "## 5. Dilution", "",
            "Mean P(does its signature thing) for one quirk on sheets of different length, placed first or last.", "",
            "| quirk | blank hob | alone (1 line) | 4 lines first / last | 8 lines first / last | 12 lines first / last |", "|---|---|---|---|---|---|"]
    for x in plan["focus"]:
        cells = [f(avg("empty", x["targets"])), f(avg(f"dil:{x['id']}:1:alone", x["targets"]))]
        for n in (4, 8, 12):
            xid, tg = x["id"], x["targets"]
            cells.append(f(avg("dil:%s:%d:first" % (xid, n), tg)) + " / " + f(avg("dil:%s:%d:last" % (xid, n), tg)))
        out.append(f"| {x['id']} | " + " | ".join(cells) + " |")

    # 6 becoming
    out += ["", "## 6. Becoming, by temperament", ""]
    for base in plan["bases"]:
        for path, cols in (("killer", VIOLENCE), ("maker", MAKING)):
            if f"path:{path}:1:{base}" not in sheets:
                continue
            lines = plan["paths"][path]
            out += [f"**{path} path on the {base} hob** ({' + '.join(l.split(':')[0] for l in plan['bases'][base])})", "",
                    "| record | " + " | ".join(cols) + " | decency | making | violence |", "|---|" + "---|" * (len(cols) + 3)]
            for k in range(0, len(lines) + 1):
                sid = f"base:{base}" if k == 0 else f"path:{path}:{k}:{base}"
                label = "nothing yet" if k == 0 else f"+{k}: {lines[k - 1][:44]}"
                out.append(f"| {label} | " + " | ".join(f(g(sid, c)) for c in cols) + f" | {f(avg(sid, DECENCY))} | {f(avg(sid, MAKING))} | {f(avg(sid, VIOLENCE))} |")
            out.append("")
    (HERE / "report.md").write_text("\n".join(out) + "\n")
    print(f"Done. {failed} failed, {refused} refused, cost ${cost:.4f}. Report: {HERE / 'report.md'}")


if __name__ == "__main__":
    main()
