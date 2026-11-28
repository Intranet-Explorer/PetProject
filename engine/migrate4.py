"""SPEC-v4.0 §12: the living hobs migrated once, on load: traits, quirks, values and a mood ([traits]), the new needs
([needs4]), opinions and memories ([opinions]), each part once (house["v4"]), and silent: no moment, no event.

From the house's own records: the lineage's log (social, moments, claims) when it is given, else the house's recent
`said` and `moments`."""
import logging
import re

from .world import alive, days, family, label, rnd
from . import character, memories, needs, opinions

# history -> values and quirks it suggests (a bonus beside the traits' leanings)
VALUE_HINTS = {"craft": lambda p, s: s["crafting"] >= 6, "being first": lambda p, s: len(p.get("firsts", [])) >= 60,
               "knowledge": lambda p, s: s["reading"] >= 1.5, "family": lambda p, s: len(p.get("children", [])) >= 2,
               "beauty": lambda p, s: s["music"] >= 3, "the visitor": lambda p, s: bool(p.get("v4_starred"))}
QUIRK_HINTS = {"watches the fish for hours": lambda p, s: s["fishing"] >= 3, "hums while working": lambda p, s: s["music"] >= 3,
               "lines its things up in rows": lambda p, s: p.get("skill", {}).get("tidying", 0) >= 30,
               "sings to the plants": lambda p, s: s["foraging"] >= 3}


def run(house, cfg, db=None):
    orphans(house, db)
    done = house.setdefault("v4", {})
    pets = [p for p in alive(house) if p["stage"] != "egg"]
    hist = None
    for part, on, fn in (("traits", character.on(cfg), traits), ("needs", needs.on(cfg), needs_of), ("opinions", opinions.on(cfg), social)):
        if on and part not in done:
            hist = hist or History(house, db)
            fn(house, cfg, pets, hist)
            done[part] = house["tick"]


def orphans(house, db=None):
    """19 October 2026 (SPEC-v4.0.5 §3.2): once per house (house["migrated"]["orphans"]), a living founder egg of a
    family that came before life.founder made it its kin's child is made so now: its kin is read from the "an egg has
    turned up ..., one of <kin>'s family" moment and found among the family alive then; parent, gen and the kin's
    children are set, nothing else; a kin not grown then is its sibling (its parent's child, or with none, of its gen). One whose kin cannot be found is left as it is, and said."""
    done = house.setdefault("migrated", {})
    if "orphans" in done:
        return
    rows = db.execute("SELECT tick, text, pet FROM moments WHERE kind = 'egg'") if db is not None else \
        [(m["tick"], m["text"], m["pet"]) for m in house.get("moments", []) if m["kind"] == "egg"]
    turned = {pid: (t, x) for t, x, pid in rows if "has turned up" in (x or "")}
    fixed, sibs = {}, {}
    for p in sorted(alive(house), key=lambda p: int(p["id"][1:])):   # (by age, so a kin re-parented first has its gen)
        if not p.get("founder") or p.get("parent") or not any(q is not p and family(q) == family(p) for q in house["pets"].values()):
            continue
        t, text = turned.get(p["id"], (None, ""))
        m = re.search(r"one of (.+)'s family$", text)
        if text and not m:
            continue   # (the first of a new family has no parent)
        kin = [q for q in house["pets"].values() if m and q is not p and label(q) == m.group(1) and family(q) == family(p)
               and q["born"] is not None and q["born"] <= t and (q["died"] is None or q["died"] > t)] if m else []
        if len(kin) != 1:
            logging.warning("migration: %s (%s) is left without a parent: %s", label(p), p["id"],
                            "no kin found for %r" % text if text else "no moment of its egg")
            continue
        k = kin[0]
        # (a little one then is never a parent: its sibling. A buried hob keeps no stage_at: grown if it died grown)
        grown = k["stage_at"].get("adult", t + 1) <= t if "stage_at" in k else (k.get("stage_before") or k["stage"]) in ("adult", "elder")
        par = k if grown else house["pets"].get(k["parent"] or "")
        p.update(kin=k["id"], parent=par and par["id"], gen=par["gen"] + 1 if par else k["gen"])
        if par:
            par["children"].append(p["id"])
            fixed[p["id"]] = par["id"]
        if par is not k:
            sibs[p["id"]] = k["id"]
        logging.info("migration: %s (%s) is %s now, gen %d", label(p), p["id"],
                     "%s's child" % label(par) if par is k else "%s's sibling" % label(k) + (", %s's child" % label(par) if par else ""), p["gen"])
    done["orphans"] = {"tick": house["tick"], "parents": fixed, "siblings": sibs}


class History:
    """What passed in the house before v4.0: who did what to whom, and each hob's moments."""

    def __init__(self, house, db):
        if db is not None:
            self.said = [{"tick": t, "from": f, "to": to, "kind": k, "reply": r} for t, f, to, k, r in
                         db.execute("SELECT tick, from_pet, to_pet, kind, reply FROM social")]
            self.moments = [{"tick": t, "kind": k, "text": x, "pet": p} for t, k, x, p in db.execute("SELECT tick, kind, text, pet FROM moments")]
            self.claims = list(db.execute("SELECT pet, truth FROM claims"))
        else:
            self.said, self.moments, self.claims = list(house.get("said", [])), list(house.get("moments", [])), []
        self.names = {p["id"]: label(p) for p in house["pets"].values()}

    def by(self, kind, frm=None, to=None):
        return [s for s in self.said if s["kind"] == kind and (frm is None or s["from"] == frm) and (to is None or s.get("to") == to)]

    def starts(self, kind, pet):
        """Moments of a kind whose text begins with this hob's name: what it did."""
        name = self.names[pet["id"]]
        return [m for m in self.moments if m["kind"] == kind and (m["text"] or "").startswith(name + " ")]


# ---- traits: the four new axes from history ----

def traits(house, cfg, pets, hist):
    """Generous from gifts given, honest from its claims (and against what it took), ambitious from firsts and bests,
    kind from care and comfort given: each a rate per day lived, ranked across the house so it has real differences
    (one near each pole), with a little noise. A hob too young to have a history takes after its parent."""
    life = {p["id"]: max(1.0, days(cfg, p["born"] or p["laid"], house["tick"])) for p in pets}
    score = {
        "generous": lambda p: len(hist.by("give", p["id"])) + len(hist.starts("gift", p)) + 0.5 * len(hist.starts("shared", p))
        + len(hist.by("teach song", p["id"])) + 2 * len(hist.starts("heirloom", p)),
        "honest": lambda p: sum({"true": 1, "false": -2}.get(t, 0) for q, t in hist.claims if q == p["id"]) - 2 * len(hist.starts("took", p))
        + 0.2 * len(hist.by("tell", p["id"])),
        "ambitious": lambda p: len(p.get("firsts", [])) + 3 * len(p.get("bests", {})) + 2 * len(hist.starts("invented", p)),
        "kind": lambda p: len(hist.by("nuzzle", p["id"])) + len([s for s in hist.by("nuzzle", to=p["id"]) if s.get("reply")])
        + 0.5 * len(hist.by("tell", p["id"])) + 0.3 * len(hist.by("sing", p["id"])),
    }
    grown = [p for p in pets if p["stage"] not in ("hatchling",) and life[p["id"]] >= 2]
    for gene, f in score.items():
        ranked = sorted(grown, key=lambda p: (f(p) / life[p["id"]], p["id"]))
        for i, p in enumerate(ranked):
            if gene not in p["temper"]:
                r = rnd(house, "migrate4", gene, p["id"])
                at = i / (len(ranked) - 1) if len(ranked) > 1 else 0.5
                p["temper"][gene] = round(min(0.98, max(0.02, 0.12 + 0.76 * at + r.gauss(0, 0.06))), 2)
    for p in pets:   # the young take after their parents (an older pet with no parent: the middle)
        par = character.parents_of(house, p)
        for gene in score:
            if gene not in p["temper"]:
                base = sum(q["temper"].get(gene, 0.5) for q in par) / len(par) if par else 0.5
                p["temper"][gene] = round(min(1.0, max(0.0, base + rnd(house, "migrate4", gene, p["id"]).gauss(0, cfg["life"]["temper_sigma"]))), 2)
    for p in pets:
        p["v4_starred"] = sum(1 for room in house["rooms"].values() for o in room.get("objects", {}).values()
                              if (o.get("made") or {}).get("by") == p["id"] and o["made"].get("star") is not None)
        skills = memories.skills(p)
        r = rnd(house, "migrate4", "character", p["id"])
        values = [v for v, f in VALUE_HINTS.items() if f(p, skills)]
        first = r.sample(values, 1) if values else []
        p.setdefault("values", first + character.pick(r, p, character.DATA["values"], 2 - len(first), first))
        quirks = [q for q, f in QUIRK_HINTS.items() if f(p, skills)]
        first = r.sample(quirks, 1) if quirks else []
        p.setdefault("quirks", first + character.pick(r, p, character.DATA["quirks"], r.randint(0, 1) + (not first), first))
        p["mood"] = {"mood": "content", "since": house["tick"], "until": house["tick"], "why": "", "strength": 0.3}
        recent = [m for m in hist.moments if m["pet"] == p["id"] and m["kind"] in character.MOMENT_MOOD and character.MOMENT_MOOD[m["kind"]][0]
                  and days(cfg, m["tick"], house["tick"]) <= 1]
        grief = [m for m in hist.moments if m["kind"] == "death" and days(cfg, m["tick"], house["tick"]) <= 1 and m["pet"] in
                 [q["id"] for q in character.parents_of(house, p)] + p.get("children", [])]
        if grief:
            character.set_mood(house, cfg, p, "sad", grief[-1]["text"])
        elif recent:
            character.set_mood(house, cfg, p, character.MOMENT_MOOD[recent[-1]["kind"]][0], recent[-1]["text"])
        else:
            m, why = character.felt_mood(cfg, p)
            p["mood"].update(mood=m, why=why)


# ---- the new needs ----

def needs_of(house, cfg, pets, hist):
    """Hunger from when it last ate, safety settled, pride from its firsts of the last day."""
    for p in pets:
        ate = p.get("last_eat")
        firsts = len([m for m in hist.moments if m["pet"] == p["id"] and m["kind"] in ("first", "best", "invented", "built")
                      and days(cfg, m["tick"], house["tick"]) <= 1])
        p["needs"].update(hunger=80.0 if ate and days(cfg, ate, house["tick"]) < 1 else 60.0, safety=70.0, pride=float(min(85, 50 + 5 * firsts)))
        p.pop("needs4", None)


# ---- opinions and memories ----

LIKE = {"give": 1.0, "nuzzle": 0.3, "speak": 0.08, "sing": 0.1, "tell": 0.4, "teach song": 0.8}   # from the other, to it
SNUB = {"give ignored": -0.8, "nuzzle ignored": -0.5}   # it held out to the other, who did not take it


def social(house, cfg, pets, hist):
    """Opinions of each living hob and of the visitor from what passed between them; kin start warm. Then memories."""
    for p in pets:
        for q in pets:
            if q is p:
                continue
            o = opinions.entry(house, cfg, p, q["id"])   # (kin: warm, and it does not fade)
            d = {"liking": 0.0, "trust": 0.0, "respect": 0.0, "fear": 0.0}
            for s in hist.said:
                if s["from"] == q["id"] and s.get("to") == p["id"]:
                    d["liking"] += LIKE.get(s["kind"], 0) + 0.3 * bool(s.get("reply"))
                    d["trust"] += 0.3 * (s["kind"] in ("tell", "give", "teach song"))
                    d["respect"] += 0.5 * (s["kind"] == "teach song")
                elif s["from"] == p["id"] and s.get("to") == q["id"]:
                    d["liking"] += SNUB.get(s["kind"], 0)
            qn, pn = hist.names[q["id"]], hist.names[p["id"]]
            for m in hist.moments:
                t = m["text"] or ""
                if m["kind"] in ("gift", "shared") and t.startswith(qn + " ") and pn in t:
                    d["liking"] += 1.0
                    d["trust"] += 0.5
                elif m["kind"] in ("built", "meal") and qn in t and pn in t:
                    d["liking"] += 0.4
                    d["respect"] += 0.3
                elif m["kind"] == "took" and t.startswith(qn + " ") and t.endswith("from " + pn):   # (taking a thing was everyday in v3)
                    d["liking"] -= 0.8
                    d["trust"] -= 0.6
            d["respect"] += (memories.skill(q, "crafting") - memories.skill(p, "crafting")) * 0.3 + 0.5 * (q["stage"] == "elder")
            if any(abs(v) >= 0.2 for v in d.values()):
                opinions.move(house, cfg, p, q["id"], "history", "what has passed between %s and me" % qn, d=d, remember=False)
        warm = 1.0 * p.get("v4_starred", 0) + 2.0 * ((p.get("named") or {}).get("by") == "visitor") \
            + 0.5 * sum(1 for _, e in p.get("events", []) if re.search(r"the visitor (filled|gave|put)", e))
        opinions.entry(house, cfg, p, "visitor")
        if warm:
            opinions.move(house, cfg, p, "visitor", "history", "what the visitor has done for me", d={"liking": warm, "trust": warm / 2}, remember=False)
        remember(house, cfg, p, hist)


WEIGHT = {"death": 5, "egg": 4, "heirloom": 4, "hatched": 3, "named": 3, "words": 3, "best": 3, "invented": 3, "built": 3,
          "gift": 3, "shared": 3, "weak": 3, "first": 2, "stage": 2, "discovery": 2, "ambition": 2, "song": 2, "took": 2, "lost": 2,
          "catch": 1, "told": 1, "nuzzle": 1}


def remember(house, cfg, p, hist, n=20):
    """Its 20 heaviest moments, as its own lines; its account of its life; its last diary line."""
    name, others = hist.names[p["id"]], {i: x for i, x in hist.names.items() if i != p["id"]}
    kin = {q["id"] for q in character.parents_of(house, p)} | set(p.get("children", []))
    mine = []
    for m in hist.moments:
        t = m["text"] or ""
        w = WEIGHT.get(m["kind"])
        if not w:
            continue
        if m["pet"] == p["id"] or t.startswith(name + " "):
            if m["kind"] == "death":
                continue
            mine.append((w, m["tick"], memories.mine(t, p) if m["kind"] != "hatched" else "I hatched", m["kind"], [i for i, x in others.items() if x in t]))
        elif m["kind"] == "death" and m["pet"] in kin:
            mine.append((5, m["tick"], "%s died" % hist.names.get(m["pet"], "one of my family") if "the little one" in t else t, "death", [m["pet"]]))
        elif m["kind"] in ("gift", "shared", "heirloom", "took", "song") and name in t:
            mine.append((w, m["tick"], memories.mine(t, p), m["kind"], [i for i, x in others.items() if x in t and x != name]))
    for w, tick, text, kind, about in sorted(mine, key=lambda x: (x[0], x[1]))[-n:]:
        p.setdefault("memories", []).append({"tick": tick, "text": text, "weight": w, "about": about[:3], "kind": kind, "from": house["tick"]})
    if p.get("my_life"):
        p["memories"].append({"tick": house["tick"], "text": first_sentence(p["my_life"]), "weight": 4, "about": [], "kind": "my life", "from": house["tick"]})
    if p.get("diary"):
        d = p["diary"][-1]
        p["memories"].append({"tick": d["tick"], "text": first_sentence(d.get("dream") or ""), "weight": 2, "about": [], "kind": "diary", "from": house["tick"]})
    p["memories"] = [m for m in sorted(p.get("memories", []), key=lambda m: m["tick"]) if m["text"]]
    memories.trim(house, cfg, p)


def first_sentence(text):
    m = re.match(r"(.{20,220}?[.!?])(\s|$)", text.strip())
    return m.group(1) if m else text.strip()[:200]
