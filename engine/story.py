"""The story (SPEC-v3 §5.5, §9): which claims travel down a family and how they change, each pet's life
record, and the house's chronicle. All from the logs; a model writes only the chronicle's one paragraph."""
import json
import re

from . import genome, life, things
from .feel import meter_talk
from .log import pet_row, put
from .world import label, moment

STOP = set("""a an the and or but if then so that this these those it its is are was were be been being am do does did
to of in on at by for with from as into than too very not no you your yours i my me mine we our they them their he she
will would can could should may might must have has had when while where what which who whom there here all any some
one out up down over under again once more most much many few just only own same also still even ever never always
make made thing things way get got go went come came let keep kept say said""".split())
CUT = re.compile(r"(?<=[.!?;])\s+")
# Claims the engine can check against the physics (§5.5). Each: what the claim must say, and whether that is so.
TRUTH = [
    (r"\b(light|lamp|bright|glow)\w*\b.*\bnight\b.*\b(harsh|hurt|uneas|uncomfort|bad|cost|ache|wrong|off|dark)|\bnight\b.*\b(light|lamp)\w*\b.*\b(harsh|hurt|uneas|uncomfort|bad|off)", True),
    (r"\b(light|lamp)\w*\b.*\b(keeps?|stops?)\b.*\bdark\b.*\b(hurt|harm)|\b(stay|sleep|rest)\b.*\bnear\b.*\b(lamp|light)", False),
    (r"\bwarm\w*\b.*\b(night|cold|winter)\b", True),
    (r"\b(eat|meal|bowl|fed|feed)\w*\b.*\b(twice|again|too soon|too often|second)\b", True),
    (r"\bquiet\w*\b.*\b(rest|sleep)|\b(rest|sleep)\w*\b.*\bquiet", True),
    (r"\bcellar\b.*\bcold\b", True),
    (r"\b(pond|water)\b.*\b(rest|sleep)", True),
    (r"\bstorm\w*\b.*\b(near|with|together|close|alone)\b", True),
    (r"\bplant\b.*\bwindow\b", True),
]


def content(text):
    """The words of a sentence that carry its meaning, roughly stemmed."""
    out = set()
    for w in re.findall(r"[a-z']+", text.lower()):
        if w in STOP or len(w) < 3:
            continue
        for end in ("ing", "ed", "es", "s"):
            if w.endswith(end) and len(w) - len(end) >= 3:
                w = w[:-len(end)]
                break
        out.add(w)
    return out


def split(text):
    """One claim a sentence (§5.5). A sentence with fewer than two words of content is not a claim."""
    return [s.strip() for s in CUT.split(text) if len(content(s)) >= 2]


def alike(a, b):
    """How alike two claims are, 0 to 1. ponytail: word overlap, no embeddings; its error rate on a hand-checked
    sample is in DECISIONS.md. Swap in embeddings here if the sample shows it confusing too many claims."""
    if not a or not b:
        return 0.0
    both = len(a & b)
    return max(both / len(a | b), 0.85 * both / min(len(a), len(b)) if min(len(a), len(b)) >= 4 else 0.0)


def truth(text):
    s = text.lower()
    return next(("true" if ok else "false" for pattern, ok in TRUTH if re.search(pattern, s)), None)


def claims(eng, pet, kind, text):
    """Split what a pet wrote into claims and tie each to the family's earlier ones: first said, repeated,
    or changed. The index lives in the house; every row goes in the lineage's log."""
    house = eng.house
    index = house["claims"]
    for sentence in split(text):
        words = content(sentence)
        best = max((c for c in index if c["lineage"] == pet["lineage"]), key=lambda c: alike(words, set(c["words"])), default=None)
        score = alike(words, set(best["words"])) if best else 0.0
        if best and score >= 0.5:
            mine = pet["id"] in best["pets"]
            relation = "repeated" if score >= 0.8 else "changed"
            if not mine:
                best["pets"].append(pet["id"])
            if pet["gen"] not in best["gens"] and kind in ("message", "tell"):
                best["gens"].append(pet["gen"])
                if len(best["gens"]) == 3:
                    moment(house, "saying", 'a saying has reached a third generation: "%s"' % best["text"], pet["id"], pet["room"])
            if relation == "changed":
                best["forms"] = (best["forms"] + [[pet["id"], sentence]])[-8:]
            claim = best
        else:
            house["n"]["claim"] = house["n"].get("claim", 0) + 1
            claim = {"id": house["n"]["claim"], "text": sentence, "words": sorted(words), "first": pet["id"], "pets": [pet["id"]],
                     "gens": [pet["gen"]] if kind in ("message", "tell") else [], "forms": [], "truth": truth(sentence),
                     "lineage": pet["lineage"], "kind": kind}
            index.append(claim)
            relation = "first"
        put(eng.db, "claims", claim=claim["id"], pet=pet["id"], tick=house["tick"], kind=kind, text=sentence, relation=relation,
            truth=claim["truth"], gen=pet["gen"])
    # the index stays bounded: sayings that travelled are kept, the rest fall off the old end
    if len(index) > 500:
        index.sort(key=lambda c: (len(c["gens"]) > 1, c["id"]))
        del index[:len(index) - 400]


def dropped(eng, pet):
    """At a pet's death: which of its parent's claims it did not hand on (§5.5)."""
    house = eng.house
    got = [m["text"] for m in pet["told"] if m["kind"] in ("message", "last words")]
    gave = " ".join(m["text"] for m in pet["message"])
    if not got or not gave:
        return
    said = [content(s) for s in split(gave)]
    for sentence in split(got[0]):
        words = content(sentence)
        if not any(alike(words, s) >= 0.5 for s in said):
            claim = next((c for c in house["claims"] if alike(words, set(c["words"])) >= 0.8), None)
            put(eng.db, "claims", claim=claim["id"] if claim else None, pet=pet["id"], tick=house["tick"], kind="message", text=sentence,
                relation="dropped", truth=claim["truth"] if claim else truth(sentence), gen=pet["gen"])


def sayings(house, n=8):
    """The claims that travelled furthest down the family (§10.4)."""
    alive_line = house["lineage"]["id"] if house["lineage"] else None
    told = [c for c in house["claims"] if len(c["gens"]) >= 2 and c["lineage"] == alive_line]
    return sorted(told, key=lambda c: (-len(c["gens"]), c["id"]))[:n]


# ---- a life, once it is over (§9.3) ----

def made_by(house, pet):
    """Every thing a pet made, still standing or gone, most used first."""
    out = [{"name": n, "recipe": o["made"]["recipe"], "uses": o["made"]["uses"], "ups": o["made"]["ups"], "room": r["name"], "gone": None}
           for r in house["rooms"].values() if r["type"] for n, o in things.made(r).items() if o["made"]["by"] == pet["id"]]
    out += [{"name": g["name"], "recipe": g["recipe"], "uses": g["uses"], "ups": g["ups"], "room": None, "gone": g["gone"][1]}
            for g in house["gone_things"] if g["by"] == pet["id"]]
    return sorted(out, key=lambda t: -t["uses"])


def life_record(eng, pet, mem):
    house, cfg = eng.house, eng.cfg
    day = lambda t: None if t is None else round((t - pet["laid"]) / cfg["ticks_per_day"], 1)
    name = label(pet)
    lived = round(life.days(house, cfg, pet), 1)
    heir = lambda o: o["made"].get("heirloom") or {}
    all_made = [(n, o) for r in house["rooms"].values() if r["type"] for n, o in things.made(r).items()]
    rooms = [house["rooms"][r]["name"] for r in pet["rooms"]]
    facts = "%s hatched in %s and lived %s days, as far as %s. It made %d things, knew %d rooms, laid %d eggs, and died of %s." % (
        name, pet.get("season", "spring"), lived, pet["stage_before"], pet["made"], len(rooms), pet["eggs"], pet["cause"])
    return {
        "id": pet["id"], "name": name, "lineage": pet["lineage"], "gen": pet["gen"], "parent": pet["parent"], "word": pet["word"],
        "children": list(pet["children"]), "days": lived, "cause": pet["cause"], "stages": {s: day(t) for s, t in pet["stage_at"].items()},
        "reached": pet["stage_before"], "bodies": pet["bodies"], "genome": pet["genome"], "portraits": pet["portraits"][-6:],
        "temper": pet["temper"], "messages": pet["message"][:1] + pet["message"][1:][-5:], "last_words": pet["last_words"],
        "told": [m for m in pet["told"] if m["kind"] in ("message", "last words")],
        "things": made_by(house, pet)[:10], "made": pet["made"], "useful": len(pet["useful"]),
        "heirlooms_given": [n for n, o in all_made if heir(o).get("from") == pet["id"]],
        "heirlooms_received": [n for n, o in all_made if pet["id"] in heir(o).get("to", [])],
        "rooms": rooms, "creatures": pet["met"], "projects": pet["projects"] + ([dict(pet["project"], how="unfinished")] if pet["project"] else []),
        "beliefs": [{"statement": b["statement"], "source": b.get("source", "lived")} for b in mem.active()],
        "my_life": pet.get("my_life") or facts, "my_life_by": "itself" if pet.get("my_life") else "the engine",
        "wellbeing": round(life.wellbeing(pet)), "span": round(life.span(cfg, pet), 1), "meter_talk": round(100 * pet["meter"][0] / pet["meter"][1]) if pet["meter"][1] else None,
        "eggs": pet["eggs"], "diary": [d["dream"] for d in pet["diary"] if d.get("dream")][-8:],
    }


# ---- the chronicle (§9.4) ----

def daily(eng):
    """At each midnight: the day just ended, as the engine saw it, and a request for one paragraph about it."""
    house = eng.house
    day = house["clock"]["day"] - 1
    if day < 1 or (house["chronicle"] and house["chronicle"][-1]["day"] >= day):
        return
    moments = [m for m in house["moments"] if m["day"] == day]
    counts = {}
    for m in moments:
        counts[m["kind"]] = counts.get(m["kind"], 0) + 1
    busy = ", ".join("%d %s" % (n, k) for k, n in sorted(counts.items(), key=lambda kn: -kn[1])[:6])
    entry = {"day": day, "season": house["clock"]["season"], "summary": busy or "a quiet day",
             "lines": [m["text"] for m in moments if m["kind"] not in ("made", "unmade", "ate")][-14:], "text": None}
    house["chronicle"] = (house["chronicle"] + [entry])[-40:]
    if not entry["lines"] or not eng.narrator:
        put(eng.db, "chronicle", day=day, summary=entry["summary"], text=None)
        return

    async def write():
        try:
            entry["text"] = (await eng.call(3, "house", "chronicle", "night", lambda: eng.narrator.chronicle(day, "\n".join(entry["lines"]))))[:900]
        except Exception:
            entry["text"] = None
        put(eng.db, "chronicle", day=day, summary=entry["summary"], text=entry["text"])
    eng.spawn(write())


def meter_share(db, pet_id, after_tick=0):
    """Share of a pet's thoughts that talk mechanics (§3.4), from the log: (percent, how many thoughts)."""
    rows = db.execute("SELECT thought FROM intentions WHERE pet=? AND started>=?", (pet_id, after_tick)).fetchall()
    return (round(100 * sum(meter_talk(r[0]) for r in rows) / len(rows), 1) if rows else None), len(rows)   # from the words, so an old log is read by today's pattern


def meter_beliefs(mem):
    held = mem.beliefs
    return round(100 * sum(meter_talk(b["statement"]) for b in held) / len(held), 1) if held else None
