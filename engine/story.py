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


NOT = re.compile(r"\b(not|never|no|nor|cannot|neither)\b|n't\b")


def content(text, polarity=False):
    """The words of a sentence that carry its meaning, roughly stemmed. With `polarity`, a sentence that denies
    something also carries "not" (a stop word otherwise), so `alike` can tell a claim from its denial."""
    out = {"not"} if polarity and NOT.search(text.lower()) else set()
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
    denied = ("not" in a) != ("not" in b)   # one says it is so and the other that it is not: related, never the same
    a, b = a - {"not"}, b - {"not"}
    if not a or not b:
        return 0.0
    both = len(a & b)
    score = max(both / len(a | b), 0.85 * both / min(len(a), len(b)) if min(len(a), len(b)) >= 4 else 0.0)
    return min(score, 0.7) if denied else score


def truth(text):
    s = text.lower()
    return next(("true" if ok else "false" for pattern, ok in TRUTH if re.search(pattern, s)), None)


def claims(eng, pet, kind, text):
    """Split what a pet wrote into claims and tie each to the family's earlier ones: first said, repeated,
    or changed. The index lives in the house; every row goes in the lineage's log."""
    house = eng.house
    index = house["claims"]
    fam = pet.get("family", 1)
    for sentence in split(text):
        words = content(sentence, True)
        best = max((c for c in index if c["lineage"] == pet["lineage"]), key=lambda c: alike(words, set(c["words"])), default=None)
        score = alike(words, set(best["words"])) if best else 0.0
        if best and score >= 0.5:
            mine = pet["id"] in best["pets"]
            relation = "repeated" if score >= 0.8 else "changed"
            if fam and best.get("family", 1) != fam and fam not in best.setdefault("crossed", []):   # SPEC-v3.1 §7.2
                best["crossed"].append(fam)
                relation = "crossed over"
                moment(house, "crossed", 'a saying has crossed between the families: "%s"' % best["text"], pet["id"], pet.get("room"))
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
                     "lineage": pet["lineage"], "kind": kind, "family": fam}
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
    said = [content(s, True) for s in split(gave)]
    for sentence in split(got[0]):
        words = content(sentence, True)
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
        "wellbeing": round(life.wellbeing(pet)), "span": round(life.span(cfg, pet), 1), "meter_talk": meter_share(eng.db, pet["id"])[0],   # from the words, by today's pattern
        "eggs": pet["eggs"], "diary": [d["dream"] for d in pet["diary"] if d.get("dream")][-8:],
        "family": pet.get("family", 1), "animals": pet.get("animals", []),   # SPEC-v3.1 §4.3: its animals are part of its life
        "songs": [house.get("songs", {}).get(e["id"], {}).get("name") for e in pet.get("songs", [])],
        "read": [{"question": r["question"], "title": r["title"]} for r in pet.get("read", [])],
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


# ---- SPEC-v3.2 §5: what a pet is doing, for whoever is watching. None of this is ever shown to a pet. ----

def act_of(house, pet, a):
    """A step as the view needs it to animate: what it is about and whom or where it is toward, taken before the step
    happens (afterwards the thing may be gone)."""
    from .actions import norm
    t, room = a.get("type"), house["rooms"][pet["room"]]
    what = a.get("target") or a.get("what") or a.get("object") or a.get("a") or a.get("song") or a.get("door") or (a.get("recipe") or {}).get("name")
    to = a.get("to") or a.get("who") or a.get("from") or a.get("near") or a.get("on") or a.get("b")
    o = room["objects"].get(norm(what)) if isinstance(what, str) else None
    recipe = o["made"]["recipe"] if o and "made" in o else (a.get("recipe") if t == "make" else None) or {}
    return {"pet": pet["id"], "type": t, "what": what if isinstance(what, str) else None, "to": to if isinstance(to, str) else None, "room": pet["room"],
            "kind": recipe.get("kind"), "color": recipe.get("color"), "from": [norm(a.get("a")), norm(a.get("b"))] if t == "combine" else None,
            "text": a.get("text") if t in ("speak", "tell", "write") else None, "things": house["n"]["thing"]}


def acted(house, cfg, pet, act, ok):
    """The step is over. Keep it a little while, numbered, so the view can play it once."""
    room = house["rooms"].get(act["room"], {})
    if ok and act["type"] in ("make", "combine") and house["n"]["thing"] > act["things"]:   # the thing that came of it, under the name it got
        name, o = next(((n, o) for n, o in room.get("objects", {}).items() if o.get("made", {}).get("id") == house["n"]["thing"]), (act["what"], None))
        if o:
            act.update(what=name, kind=o["made"]["recipe"].get("kind"), color=o["made"]["recipe"].get("color"))
    house["n"]["act"] = house["n"].get("act", 0) + 1
    act.pop("things", None)
    house.setdefault("acts", []).append(dict(act, n=house["n"]["act"], tick=house["tick"], ok=bool(ok), room=pet["room"] if act["type"] == "go" else act["room"]))
    del house["acts"][:-40]


PAST = {"make": "made {thing}", "unmake": "took apart {thing}", "combine": "joined two things into {thing}", "use": "used the {what}",
        "gather": "picked up some {what}", "drop": "put down some {what}", "give": "held out {what} to {to}", "show": "showed {to} the {what}",
        "nuzzle": "leaned toward {to}", "accept": "took what {to} offered", "speak": "said something", "tell": "told {to} something to keep",
        "go": "came through the {what} door", "write": "wrote on the {to}", "scrub": "rubbed out some writing", "sing": "sang \"{what}\"",
        "compose": "made up a song", "teach_song": "taught {to} a song", "ask_book": "asked the book a question", "call": "called its {what}",
        "name": "gave a name to something", "lay_egg": "laid an egg", "bequeath": "chose something to leave behind", "arrange": "moved the {what}",
        "take": "took the {what}", "chase": "chased the {to}", "paint": "painted the room", "teach": "taught the {what} a trick"}


def now(house, cfg):
    """The one plain sentence at the top of the page (§5.4), rewritten whenever something changes. No model is asked."""
    from . import mind, things
    from .world import a_stage, dist, relation
    living = [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")]
    eggs = [p for p in house["pets"].values() if p["stage"] == "egg"]
    if not living:
        return "An egg is waiting in %s." % house["rooms"][eggs[0]["room"]]["name"] if eggs else "The house is quiet. Nobody lives here now."
    recent = [a for a in house.get("acts", []) if a["ok"] and a["type"] in PAST and house["tick"] - a["tick"] <= cfg["ticks_per_hour"]]
    last = recent[-1] if recent else None
    who = house["pets"].get(last["pet"]) if last else None
    pet = who if who in living else max(living, key=lambda p: p["last_call"])
    name = lambda p, of=None: p["name"] or ("its " + relation(house, of, p) if of and relation(house, of, p) else "the little one")
    cap = lambda t: t[:1].upper() + t[1:]
    room = house["rooms"][pet["room"]]
    near = [p for p in living if p is not pet and p["room"] == pet["room"]]
    beside = next((p for p in near if dist(p["pos"], pet["pos"]) <= 2), None)
    doing = mind.doing(house, pet).split(" (")[0]
    first = "%s, %s, is %s%s in %s." % (cap(name(pet)), a_stage(pet["stage"]), doing, " by " + name(beside, pet) if beside else "", room["name"])
    others = [p for p in living if p is not pet and p is not beside]
    if others and len(first) < 90:
        o = others[0]
        first += " %s is %s%s." % (cap(name(o)), mind.doing(house, o).split(" (")[0], "" if o["room"] == pet["room"] else " in " + house["rooms"][o["room"]]["name"])
    if not last or who not in living:
        return first
    to = next((p for p in living if last.get("to") and (p["name"] or "").lower() == str(last["to"]).lower()), None)
    told = {"thing": things.a_thing(cfg, {"kind": last.get("kind") or "thing", "color": last.get("color")}), "what": last.get("what") or "something",
            "to": name(to, who) if to else (last.get("to") or "someone")}
    return "%s %s just %s." % (first, cap(name(who)), PAST[last["type"]].format(**told))
