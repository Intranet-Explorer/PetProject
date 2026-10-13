"""Bodies that evolve (SPEC-v3.5 §2). A body is settled at birth: each slot comes from the parent, now and then a step
to a neighbouring value, patterns combine, and about one birth in twelve gets something no ancestor had. A few parts do
something for their pet in the house, and it feels them do it: a line it notices or is told, never a number. A family
that lived before all this is given its parts once. Slots, rates, traits and their words are data
(view/assets/bodies.json); no model is asked anything here.

    uv run python -m engine.genes [DATA_DIR] [--births 200]    # the stub run of §7.2: rates, plans, the families apart
"""
import random
from collections import Counter

from . import genome
from .genome import BODIES, PLANS, RANGES, SLOTS, START, get
from .world import LONG_AGO, add_event, bit_kinds, dist, family, moment, label, neighbours, rnd

R, T, PARTS = BODIES["rates"], BODIES["traits"], BODIES["parts"]
MIX = {frozenset(k.split("+")): v for k, v in BODIES["pattern_mix"].items()}
UNMIX = {v: k.split("+") for k, v in BODIES["pattern_mix"].items()}
BASE = [p for p in BODIES["patterns"] if p not in UNMIX]   # the patterns that are not two others combined


# ---- inheritance (§2.1, §2.2) ----

def mix(old, new, rng):
    """Patterns combine rather than replace: spots and stripes give broken stripes. A combined one comes apart again."""
    if old in UNMIX:
        return rng.choice(UNMIX[old])
    return MIX.get(frozenset((old, new)), new)


def child(g, rng, line=()):
    """A child's body: (its genome, the rare big mutation or None). Each number is the parent's, nudged; each slot the
    parent's, with a small chance of a step to a neighbouring value (never to a part nobody in its line had: that is
    the rare thing). `line`: the bodies of the parent's own ancestors. Marks are earned, not inherited."""
    c = dict({k: get(g, k) for k in START}, marks=[])
    for k, (lo, hi) in RANGES.items():
        c[k] = round(min(hi, max(lo, c[k] + rng.gauss(0, R["size"] if k == "size" else R["nudge"] * (hi - lo)))), 2)
    c["hue"] = round(c["hue"] + rng.gauss(0, R["hue"])) % 360
    had = lambda s: any(get(a, s) != SLOTS[s][0] for a in (g, *line))   # has anyone in its line had a part here?
    for s, values in SLOTS.items():
        i = values.index(c[s])
        if rng.random() < R["step"] and (i or s not in PARTS or had(s)):
            c[s] = values[rng.choice([j for j in (i - 1, i + 1) if 0 <= j < len(values)])]
    if rng.random() < R["pattern"]:
        c["pattern"] = mix(c["pattern"], rng.choice(BASE), rng)
    new, r = None, rng.random()
    if r < R["plan"]:   # a different body plan: a great-grandchild can look like another creature
        new = {"slot": "plan", "from": c["plan"], "to": rng.choice([p for p in PLANS if p != c["plan"]])}
    elif r < R["plan"] + R["new"]:   # a part no ancestor had, or a value two steps from the parent's
        was = lambda s: SLOTS[s].index(get(g, s))
        s, v = rng.choice([(s, v) for s, values in SLOTS.items() for i, v in enumerate(values)
                           if abs(i - was(s)) >= 2 or (i and s in PARTS and not had(s))])
        new = {"slot": s, "from": get(g, s), "to": v}
    if new:
        c[new["slot"]] = new["to"]
    return c, new


def line(house, pet):
    """The bodies of its ancestors, nearest first. ponytail: only those the house still holds; one buried long ago is
    forgotten, and a part of theirs could count as new again."""
    out, p = [], house["pets"].get(pet.get("parent") or "")
    while p and len(out) < 40:
        out.append(p["genome"])
        p = house["pets"].get(p.get("parent") or "")
    return out


def hatched(house, pet):
    """What hatched is not quite what its line has been: a moment, and the tree marks the branch (pet["mutation"])."""
    m = pet.get("mutation")
    if not m:
        return
    what = genome.WORDS.get(m["slot"], {}).get(m["to"])
    first = m["slot"] in PARTS and m["from"] == SLOTS[m["slot"]][0]
    text = "%s hatched with %s: nobody in its line had the like" % (label(pet), what) if what and (first or m["slot"] == "plan") else \
        "%s hatched with %s, not like its parent's" % (label(pet), what) if what else "%s hatched without its parent's %s" % (label(pet), genome.WORDS[m["slot"]][m["from"]].replace("a ", "", 1))
    moment(house, "mutation", text, pet["id"], pet["room"])


def grey(pet):
    """Growing old shows a little: its colour fades (slowing is in how an elder walks)."""
    g = pet["genome"]
    g["saturation"] = round(max(RANGES["saturation"][0], g["saturation"] * 0.8), 2)


def apart(house, g, rng):
    """A stranger's egg (§2.4): a body that differs from everyone's in the house in two slots at least."""
    here = [p["genome"] for p in house["pets"].values() if p["stage"] != "dead"]
    for s in rng.sample(BODIES["live"]["slots"], 2):
        g[s] = rng.choice([v for v in SLOTS[s] if all(get(x, s) != v for x in here)] or SLOTS[s][1:])
    return g


def migrate(house, cfg):
    """SPEC-v3.5 §2.4 comes to a house already lived in, once: every living pet and egg gets its slots, mostly plain
    (so nobody looks much different in the morning). Each family is given two slots of its own, drawn from the
    house's seed, so two families differ in four; its feet come from the limbs it used to have. The dead stay as
    they were, but for the names of their patterns. True if this was the time."""
    if "v35" in house:
        return False
    house["v35"], L = {"at": house["tick"], "families": {}}, BODIES["live"]
    for p in house["pets"].values():
        if p["genome"].get("pattern") in genome.OLD_PATTERNS:
            p["genome"]["pattern"] = genome.OLD_PATTERNS[p["genome"]["pattern"]]
    living = [p for p in house["pets"].values() if p["stage"] != "dead" and "plan" not in p["genome"]]
    order = rnd(house, "v35").sample(L["slots"], len(L["slots"]))
    for i, fam in enumerate(sorted({family(p) for p in living})):
        r = rnd(house, "v35", fam)
        own = {s: r.choice(SLOTS[s][1:]) for s in (order[2 * i % len(order)], order[(2 * i + 1) % len(order)])}
        house["v35"]["families"][str(fam)] = own
        for p in [p for p in living if family(p) == fam]:
            g = p["genome"]
            g.update({k: own.get(k, v) for k, v in START.items() if k not in g}, feet=L["feet"][min(g.get("limbs", 0), len(L["feet"]) - 1)])
    return True


# ---- traits that matter (§2.3) ----

def has(g, trait):
    """Does a body have this trait? Every body has one of the last two: how it sleeps."""
    if trait == "fur":
        return get(g, "fur") == "thick" or (get(g, "tail") == "fluffy" and get(g, "ears") == "long")
    if trait in ("ears", "legs", "dark", "whiskers"):
        return get(g, {"legs": "feet", "dark": "shade"}.get(trait, trait)) == {"ears": "long", "legs": "legs", "dark": "dark", "whiskers": "yes"}[trait]
    if trait == "small":
        return get(g, "size") <= T["small"]["size"]
    curled = get(g, "plan") in T["curled"]["plans"] and g["roundness"] >= T["curled"]["roundness"]
    return curled if trait == "curled" else not curled


def felt(house, cfg, pet, trait, text, tell=True, gap=0):
    """Its body did something for it, and it felt it: it is told (unless the line is already among what it notices),
    and it is written down to be counted (alive.py), the same trait once a world hour at most. `gap`: world hours
    before it is told the same again."""
    seen = pet.setdefault("felt", {})
    if house["tick"] - seen.get(trait, LONG_AGO) < gap * cfg["ticks_per_hour"]:
        return
    if tell:
        add_event(house, pet, text)
    if house["tick"] - seen.get(trait, LONG_AGO) >= cfg["ticks_per_hour"]:
        seen[trait] = house["tick"]
        house.setdefault("fresh_traits", []).append({"pet": pet["id"], "tick": house["tick"], "day": house["clock"]["day"], "trait": trait, "text": text})


def fur(pet, cold, out):
    """Thick fur: the cellar's cold and the season's wear on comfort less (physics.effects). Returns the cold that is left."""
    if not has(pet["genome"], "fur"):
        return cold
    for e in out:
        if e["tag"] == "cellar" and e["rate"] < 0:
            e.update(rate=e["rate"] * T["fur"]["cold"], feel=T["fur"]["cellar"], trait="fur")
    if cold and not any(e["tag"] == "greenhouse" for e in out):
        out.append({"tag": "fur", "need": "comfort", "rate": 0.0, "feel": T["fur"]["feel"], "hidden": False, "trait": "fur"})
    return cold * T["fur"]["cold"]


def stride(house, pet):
    """Long legs walk faster: an extra tile every other tick."""
    return int(has(pet["genome"], "legs") and house["tick"] % T["legs"]["every"] == 0)


def unseen(house, cfg, cr, pet):
    """A dark coat: the moth takes no notice of it, however it moves about (director.trust)."""
    if cr["kind"] != "moth" or cr.get("tame") or not has(pet["genome"], "dark"):
        return False
    felt(house, cfg, pet, "dark", T["dark"]["feel"], gap=6)
    return True


def whiskers(pet, want):
    """Whiskers notice loose bits and creatures sooner: those wants come to it more often (wants.refresh)."""
    return T["whiskers"]["weight"] if want["what"] in T["whiskers"]["wants"] and has(pet["genome"], "whiskers") else 1.0


def nook(house, cfg, pet):
    """The corner behind the gap under the storeroom shelves, if this pet is in that room, is small enough, and
    something lies there: (the room, the shelves), else None."""
    S, room = T["small"], house["rooms"][pet["room"]]
    under = room["objects"].get(S["under"])
    return (room, under) if room["type"] == S["room"] and under and has(pet["genome"], "small") and room.get("nook", 0) <= house["tick"] else None


def senses(house, cfg, pet, acting):
    """What its body adds to what it notices (mind.perceive), and the note that a trait among them was felt."""
    for e in acting:
        if e.get("trait") and e["feel"]:
            felt(house, cfg, pet, e["trait"], e["feel"], tell=False)
    if nook(house, cfg, pet):
        felt(house, cfg, pet, "small", T["small"]["feel"], tell=False)
        return [T["small"]["feel"]]
    return []


def own(house, pet):
    """Its own body in a few words, as it sees it once a day (§6): "you have long ears and a fluffy tail, like your mother"."""
    mine = (genome.parts(pet["genome"], ("plan",)) + genome.parts(pet["genome"]))[:3]
    parent = house["pets"].get(pet.get("parent") or "")
    theirs = genome.parts(parent["genome"], ("plan",)) + genome.parts(parent["genome"]) if parent else []
    if not mine:
        return "your body is plain and smooth, with no ears or tail to speak of" + (", like your %s's" % parent["word"] if parent and not theirs else "")
    new = [w.replace("a ", "", 1) if w.startswith("a ") else w for w in mine if w not in theirs]
    return "you have %s%s" % (genome.join(mine), "" if not parent else ", like your %s" % parent["word"] if not new else "; your %s had no %s" % (parent["word"], " or ".join(new)))


def live(house, cfg, pet):
    """Each waking tick: what its body does for it that needs no deciding. On waking (or hatching), once a day, it sees
    its own body and feels how it slept; long ears catch what is said, sung and broadcast next door; long legs, whiskers and a small
    body are felt when they have just been of use."""
    from . import craft, songs
    from .actions import bump, handle
    g, tick = pet["genome"], house["tick"]
    since, pet["body_at"] = max(pet.get("body_at", tick - 1), tick - 3), tick   # (what happened on the tick before is whole by now)
    if {"woke", "hatched"} & set(pet["news"]) and pet.get("body_day") != house["clock"]["day"]:
        pet["body_day"] = house["clock"]["day"]
        add_event(house, pet, own(house, pet))
        if has(g, "curled"):
            bump(pet, cfg, {"comfort": T["curled"]["comfort"]})
            felt(house, cfg, pet, "curled", T["curled"]["feel"])
        else:
            pet["spring"] = max(pet["spring"], T["stretched"]["spring"])
            felt(house, cfg, pet, "stretched", T["stretched"]["feel"])
    if has(g, "ears"):
        E = T["ears"]
        for d, rid in neighbours(house, pet["room"]).items():
            where = house["rooms"][rid]["name"] if rid in pet["rooms"] else "behind the %s door" % d
            for p in house["pets"].values():
                said = p.get("said")
                if p["room"] == rid and p["stage"] not in ("egg", "dead") and said and since <= said["tick"] < tick and "song" not in said:
                    felt(house, cfg, pet, "ears", E["speech"] % (handle(house, pet, p), said["text"]))
            for s in house.get("sung", []):
                if s["room"] == rid and since <= s["tick"] < tick and s["song"] in songs.book(house):
                    felt(house, cfg, pet, "ears", E["song"] % (where, songs.book(house)[s["song"]]["name"], songs.sound(songs.book(house)[s["song"]]["notes"])))
                    if not songs.known(house, pet, of=s["song"]):   # heard through a wall it is picked up by ear like any other
                        songs.keep(house, cfg, pet, songs.by_ear(house, cfg, pet, s["song"]))
            for s in house.get("radio", {}).get("said", []):
                if s["room"] == rid and since <= s["tick"] < tick and s["text"]:
                    pet["box"] = ([{"tick": tick, "text": s["text"]}] + pet.get("box", []))[:cfg["radio"]["keep"]]
                    pet["news"].append("heard")
                    felt(house, cfg, pet, "ears", E["radio"] % (where, s["text"]))
    if has(g, "legs") and pet.get("walked", 0) - pet.get("strode", 0) >= T["legs"]["tiles"]:
        pet["strode"] = pet.get("walked", 0)
        felt(house, cfg, pet, "legs", T["legs"]["feel"], gap=6)
    if has(g, "whiskers"):
        for w in pet.get("wants", []):
            if w["what"] in T["whiskers"]["wants"] and since <= w["since"] < tick:
                felt(house, cfg, pet, "whiskers", T["whiskers"]["feel"] % ("the " + (w.get("bit") or w.get("kind"))))
    at = nook(house, cfg, pet)
    if at and dist(pet["pos"], at[1]["pos"]) <= T["small"]["reach"]:
        room, bit = at[0], rnd(house, "nook", at[0]["id"], tick).choice(bit_kinds(house, cfg))
        room["nook"] = tick + round(T["small"]["hours"] * cfg["ticks_per_hour"])
        craft.give(house, cfg, pet, room, bit)
        pet["got"] = [bit, tick]
        felt(house, cfg, pet, "small", T["small"]["found"] % ("some " + bit))


# ---- the stub run of §7.2: inheritance alone, many births ----

def apart_in(a, b):
    """The slots (and the plan) in which two families can be told apart: no body of one has the other's value."""
    return [s for s in list(SLOTS) + ["plan"] if not {get(g, s) for g in a} & {get(g, s) for g in b}]


def measure(families, births=200, seed=0, keep=3, show=True):
    """Lay `births` eggs, turn about between the families, each from one of the family's living (at most `keep` of
    them: the oldest goes), and count: births with a small step, with a big mutation, with a part new to the line,
    each plan's share, and in how many slots the families can be told apart as the births go by. No house, no minds:
    this is `child` and nothing else, so it says what the rates do, not who thrives."""
    rng = random.Random("genes|%s" % seed)
    live = {f: [(g, [])] for f, g in families.items()}   # family -> [(body, its ancestors' bodies)]
    out = {"births": 0, "small": 0, "big": 0, "new_part": 0, "plan": 0, "plans": Counter(), "apart": [], "first40": None}
    for n in range(births):
        fam = sorted(live)[n % len(live)]
        g, anc = rng.choice(live[fam])
        c, new = child(g, rng, anc)
        live[fam] = (live[fam] + [(c, [g] + anc)])[-keep:]
        out["births"] += 1
        out["small"] += any(c[s] != get(g, s) for s in SLOTS if not new or s != new["slot"])
        out["big"] += bool(new)
        out["plan"] += bool(new) and new["slot"] == "plan"
        out["new_part"] += any(s in PARTS and c[s] != SLOTS[s][0] and all(get(a, s) == SLOTS[s][0] for a in [g] + anc) for s in SLOTS)
        out["plans"][c["plan"]] += 1
        if len(live) > 1:
            a, b = [[g for g, _ in live[f]] for f in sorted(live)[:2]]
            out["apart"].append(len(apart_in(a, b)))
        if n == 39:
            out["first40"] = {"big": out["big"], "new_part": out["new_part"], "apart": out["apart"][-1] if out["apart"] else None}
    out["living"] = Counter(get(g, "plan") for f in live.values() for g, _ in f)
    if show:
        b = out["births"]
        print("%d births: a small step in %d (1 in %.1f); something new in %d (1 in %.1f; the bar is about 1 in 12, never more than 1 in 6), of which a new plan %d (1 in %.0f)" % (
            b, out["small"], b / max(1, out["small"]), out["big"], b / max(1, out["big"]), out["plan"], b / max(1, out["plan"])))
        print("a part nobody in the line had: %d (1 in %.1f)" % (out["new_part"], b / max(1, out["new_part"])))
        print("plans, share of births: %s; among the living at the end: %s" % (
            ", ".join("%s %.0f%%" % (p, 100 * n / b) for p, n in out["plans"].most_common()), dict(out["living"])))
        if out["apart"]:
            ap = out["apart"]
            print("the two families can be told apart in: %d slots at the start, %d after 40 births, %d at the end; in two or more after %.0f%% of births (fewest %d)" % (
                len(apart_in(*[[g] for g in list(families.values())[:2]])), ap[min(39, len(ap) - 1)], ap[-1], 100 * sum(x >= 2 for x in ap) / len(ap), min(ap)))
    return out


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="?", help="a house's data folder: its two families as they stand (after §2.4) are where the run starts")
    ap.add_argument("--births", type=int, default=200)
    ap.add_argument("--seeds", type=int, default=5)
    a = ap.parse_args()
    if a.data:
        from .world import load_config
        house = json.loads((Path(a.data) / "house.json").read_text())
        migrate(house, load_config())
        pets = [p for p in house["pets"].values() if p["stage"] != "dead"]
        start = {f: max((p for p in pets if family(p) == f), key=lambda p: p["gen"])["genome"] for f in sorted({family(p) for p in pets})}
        for f, g in start.items():
            print("family %s starts as: %s" % (f, genome.describe(g)))
    else:   # two plain families that differ as a migrated house's do
        start = {1: dict(START, ears="round", tail="stub"), 2: dict(START, head="horns", mouth="wide", hue=200)}
    runs = [measure(start, a.births, seed, show=a.seeds == 1) for seed in range(a.seeds)]
    if a.seeds > 1:
        n = sum(r["births"] for r in runs)
        tot = lambda k: sum(r[k] for r in runs)
        plans = sum((r["plans"] for r in runs), Counter())
        print("%d runs of %d births (%d in all):" % (len(runs), a.births, n))
        print("  a small step: 1 birth in %.1f; something new: 1 in %.1f (the bar: about 1 in 12, never more than 1 in 6); of those a new plan: 1 in %.0f; a part nobody in the line had: 1 in %.1f" % (
            n / max(1, tot("small")), n / max(1, tot("big")), n / max(1, tot("plan")), n / max(1, tot("new_part"))))
        print("  in the first 40 births of each run, something new: %s" % ", ".join("%d" % r["first40"]["big"] for r in runs if r["first40"]))
        print("  plans, share of all births: %s" % ", ".join("%s %.0f%%" % (p, 100 * c / n) for p, c in plans.most_common()))
        print("  plans among the living at the end of each run: %s" % "; ".join(" ".join("%s %d" % kv for kv in r["living"].most_common()) for r in runs))
        print("  the two families told apart, slots after 40 births / at the end / fewest on the way, by run: %s" % "; ".join(
            "%d / %d / %d" % (r["apart"][min(39, len(r["apart"]) - 1)], r["apart"][-1], min(r["apart"])) for r in runs if r["apart"]))
        print("  share of births after which they differ in two slots or more: %.0f%%" % (100 * sum(x >= 2 for r in runs for x in r["apart"]) / max(1, sum(len(r["apart"]) for r in runs))))
