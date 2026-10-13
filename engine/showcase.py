"""The showcase's bar (SPEC-v3 §12.2), from the logs and nothing else.

    uv run python -m engine.showcase [data dir]

Prints the evidence for each of the eight criteria. Criteria 3, 4 and 6's "changed what it did" still need
reading: the script finds the passages, a person judges them."""
import json
import re
import sqlite3
import sys
from pathlib import Path

from . import genome, story
from .world import GENES, ROOT, load_config

EVENT_WORDS = {"power cut": r"went dark|gone dark|power|every light|lights? (went|are|is) (out|dark)|no light", "leak": r"water (is|was)? ?coming|wet floor|floor is wet|leak|shifted",
               "draught": r"draught|blew|stuck shut|door (is )?(stuck|shut)", "delivery": r"crate|set down|deliver", "lost thing": r"not where|is gone|went missing|has gone from|gone from"}


def main(data=ROOT / "data", profile=None):
    data = Path(data)
    house = json.loads((data / "house.json").read_text())
    cfg = load_config(profile=profile or house.get("profile"))
    lin = house["lineage"]["id"]
    db = sqlite3.connect(data / ("lineage-%d" % lin) / "lineage.db")
    db.row_factory = sqlite3.Row
    pets = {r["pet"]: dict(r) for r in db.execute("SELECT * FROM pets ORDER BY laid")}
    for p in pets.values():
        p["genome"], p["temper"] = json.loads(p["genome"]), json.loads(p["temper"])
        p["label"] = p["name"] or "the little one"
    names = [p["label"] for p in pets.values()]
    for p in pets.values():   # a parent gave two eggs one name (third run; the engine now refuses it): the report tells them apart
        if names.count(p["label"]) > 1:
            p["label"] += " (%s)" % p["pet"]
    hatched = [p for p in pets.values() if p["born"] is not None]
    day = cfg["ticks_per_day"]
    gens = max((p["gen"] for p in hatched), default=0)
    print("# The bar: lineage %d, day %d, %d pets hatched over %d generations" % (lin, house["clock"]["day"], len(hatched), gens))
    # A pet that has not had a day of life has not lived one to judge: it is listed, and left out of every per-life test.
    end = db.execute("SELECT max(tick) FROM steps").fetchone()[0] or 0
    lived = [p for p in hatched if (p["died"] or end) - p["born"] >= day]
    print("  %d of them lived a world day or more, over %d generations%s\n" % (len(lived), max((p["gen"] for p in lived), default=0),
          "; not judged, under a day old: " + ", ".join("%s (gen %d)" % (p["label"], p["gen"]) for p in hatched if p not in lived) if len(lived) < len(hatched) else ""))
    ok = {}

    print("## 1. It reads like a creature (meter-talk under 10% for every pet after its first day; v2.5: 43.0% of thoughts and 57.9% of beliefs"
          "\n   by today's pattern; its thoughts were 25.2% by the narrower one they were first measured with)")
    worst = 0
    for p in hatched:
        share, n = story.meter_share(db, p["pet"], p["born"] + day)
        every, total = story.meter_share(db, p["pet"])
        path = data / ("lineage-%d" % lin) / p["pet"] / "beliefs.json"
        beliefs = json.loads(path.read_text()) if path.exists() else []
        from .feel import meter_talk
        b = round(100 * sum(meter_talk(x["statement"]) for x in beliefs) / len(beliefs), 1) if beliefs else None
        pct = lambda v: "–" if v is None else "%s%%" % v
        print("   %-14s gen %d: %s of %d thoughts after day 1 (%s of all %d); %s of %d beliefs" % (p["label"], p["gen"], pct(share), n, pct(every), total, pct(b), len(beliefs)))
        worst = max(worst, share or 0) if n >= 10 else worst
    ok[1] = worst < 10
    from .feel import METER
    flagged = [(r["pet"], r["thought"]) for r in db.execute("SELECT pet, thought FROM intentions ORDER BY tick DESC") if METER.search(r["thought"])]
    for pet, thought in flagged[:5]:
        print('      flagged for "%s": %s: %s' % (METER.search(thought).group(0), pets[pet]["label"], thought[:160]))

    print("\n## 2. The lineage changed")
    drift = []
    for p in hatched:
        line, q = [p], p
        while q["parent"] in pets:
            q = pets[q["parent"]]
            line.append(q)
        if len(line) >= 2:
            first = line[-1]
            for g in GENES:
                drift.append((abs(p["temper"][g] - first["temper"][g]), g, first["label"], first["temper"][g], p["label"], p["temper"][g], len(line)))
    for d, g, a, av, b, bv, n in sorted(drift, reverse=True)[:5]:
        print("   %s: %.2f in %s -> %.2f in %s, %d generations on" % (g, av, a, bv, b, n - 1))
    for p in hatched:
        g = p["genome"]
        print("   %-14s gen %d: hue %d, %s, %s, roundness %.2f, stretch %.2f" % (p["label"], p["gen"], g["hue"], g["pattern"], ", ".join(genome.parts(g)) or "plain", g["roundness"], g["stretch"]))
    # Did the temperament show in how they lived? Beside each gene, the behaviour it is meant to lean (for a reader).
    for p in hatched:
        n = db.execute("SELECT count(*) FROM steps WHERE pet=?", (p["pet"],)).fetchone()[0] or 1
        # steps that were carried out, and for "with another" not the ones aimed at a creature
        share = lambda kinds, more="": 100 * db.execute("SELECT count(*) FROM steps WHERE pet=? AND reason IS NULL AND kind IN (%s)%s" % (",".join("?" * len(kinds)), more), (p["pet"], *kinds)).fetchone()[0] / n
        rooms = db.execute("SELECT count(DISTINCT room) FROM steps WHERE pet=?", (p["pet"],)).fetchone()[0]
        t = p["temper"]
        print("   %-15s sociable %.2f: %2d%% of steps with another (speak, tell, give, nuzzle, show, accept, follow) | curious %.2f, bold %.2f: %d rooms, %2d%% look/observe | playful %.2f: %2d%% make/combine/arrange/teach/paint" % (
            p["label"], t["sociable"], share(("speak", "tell", "give", "nuzzle", "show", "accept", "follow"), " AND coalesce(json_extract(action,'$.to'), json_extract(action,'$.who'), '') NOT IN ('moth','beetle','mouse','bird')"), t["curious"], t["bold"], rooms, share(("look", "observe")),
            t["playful"], share(("make", "combine", "arrange", "teach", "paint"))))
    ok[2] = None if drift and max(drift)[0] >= 0.2 else False

    print("\n## 3. Something was passed down and mattered (a child's first-day thoughts that use a particular thing its parent told it)")
    # A candidate is a first-day thought that shares at least two words of content with ONE sentence of the message it
    # hatched with, not counting the words every such thought has ("mother", "told", "said"). The engine's own
    # sense line "you want your mother" cannot make one. Whether the thought changed what it did is for a reader.
    common, found = {"mother", "father", "parent", "told", "tell", "said", "say", "not"}, 0
    for p in hatched:
        told = [r["text"] for r in db.execute("SELECT text FROM messages WHERE to_pet=? AND kind='message'", (p["pet"],))]
        if not told or p["gen"] < 2:
            continue
        claims = [(c, story.content(c) - common) for c in story.split(told[0])]
        for r in db.execute("SELECT thought, intention FROM intentions WHERE pet=? AND started<? ORDER BY tick", (p["pet"], p["born"] + day)):
            words = story.content(r["thought"]) - common
            best = max(claims, key=lambda cw: len(cw[1] & words), default=None)
            if best and len(best[1] & words) >= 2 and re.search(r"\b(mother|father|parent)\b", r["thought"], re.I):
                found += 1
                if found <= 6:
                    print('   %s was told: "%s"\n      thought: %s\n      did: %s' % (p["label"], best[0], r["thought"][:260], r["intention"][:90]))
    print("   %d candidate thoughts (to be read)" % found)
    ok[3] = None if found else False

    print("\n## 4. A myth or a correction (a claim followed through three generations of messages)")
    # For every line of three generations A -> B -> C (the last v2 pet counts as the founder's parent): each
    # sentence A gave B (the message B hatched with, and A's last words if B was alive to hear them; not what A
    # wrote later, which may be B's own words coming back), whether B kept it, and whether C kept it.
    # "Held" needs all three. A "correction" needs B to have kept it and C to have changed or dropped it; whether
    # C's own experience contradicted it is for a reader.
    msgs = {}   # pet -> every version of the message it wrote, oldest first
    for r in db.execute("SELECT pet, text FROM messages WHERE kind IN ('message', 'last words') ORDER BY tick"):
        msgs.setdefault(r["pet"], []).append(r["text"])
    held, corrected, lines = 0, 0, []
    state = lambda sentence, texts: max((story.alike(story.content(sentence, True), story.content(x, True)) for t in texts for x in story.split(t)), default=0.0)
    gave = lambda a, b: [r["text"] for r in db.execute("SELECT text FROM messages WHERE pet=? AND ((kind='message' AND to_pet=?) OR (kind='last words' AND tick>?)) ORDER BY tick", (a, b["pet"], b["born"]))]
    for c in hatched:
        b = pets.get(c["parent"])
        if not b or c["pet"] not in msgs:
            continue
        a = pets[b["parent"]]["pet"] if b["parent"] in pets else "before" if b["gen"] == 1 else None
        if a not in msgs or b["pet"] not in msgs:
            continue
        for sentence in dict.fromkeys(x for t in gave(a, b) for x in story.split(t)):
            in_b, in_c = state(sentence, msgs[b["pet"]]), state(sentence, msgs[c["pet"]])
            if in_b < 0.5:
                continue
            kind = "held" if in_c >= 0.8 else "changed" if in_c >= 0.5 else "dropped"
            held += kind == "held"
            corrected += kind != "held"
            lines.append((("held", "changed", "dropped").index(kind), '   %s -> %s -> %s [%s by the third; %s]: "%s"' % (
                "the one before" if a == "before" else pets[a]["label"], b["label"], c["label"], kind, story.truth(sentence) or "unchecked", sentence[:150])))
    for _, text in sorted(lines, key=lambda x: x[0]):   # held first, then changed, then dropped, each in the order found
        print(text)
    print("   over every line of three generations: %d sentences held, %d changed or dropped by the third" % (held, corrected))
    # The lines above follow hatching messages down a direct line only. A saying also travels by telling and by belief,
    # and sideways; the engine's claim tracker (the Lab's claim lineages) groups every form of one saying whoever held it.
    spans = db.execute("SELECT claim FROM claims GROUP BY claim HAVING count(DISTINCT gen) >= 3 ORDER BY max(gen) - min(gen) DESC, count(*) DESC, claim").fetchall()
    print("   sayings held in three or more generations by any way (message, telling, belief), from the claim tracker: %d" % len(spans))
    for (claim,) in spans[:8]:
        seen = set()
        for r in db.execute("SELECT pet, gen, kind, truth, tick, text FROM claims WHERE claim=? ORDER BY tick", (claim,)):
            if (r["pet"], r["kind"]) not in seen:   # the first time each pet held it each way
                seen.add((r["pet"], r["kind"]))
                print('      %s day %.1f, %s gen %d, %s%s: "%s"' % ("·" if len(seen) > 1 else "saying:", r["tick"] / day, "the one before" if r["pet"] == "before" else pets[r["pet"]]["label"],
                                                              r["gen"], r["kind"], " [%s]" % r["truth"] if r["truth"] else "", r["text"][:140]))
    ok[4] = True if held else None if corrected else False

    print("\n## 5. They dealt with each other without the visitor")
    rows = dict(db.execute("SELECT kind, count(*) FROM social WHERE to_pet IS NOT NULL AND to_pet != 'visitor' GROUP BY 1").fetchall())
    replies = db.execute("SELECT count(*) FROM social WHERE reply=1 AND kind='speak'").fetchone()[0]
    taken = db.execute("SELECT count(*) FROM social WHERE reply=1 AND kind!='speak'").fetchone()[0]
    print("   %s; things said in answer: %d; gifts and nuzzles taken: %d" % (rows, replies, taken))
    there, n = db.execute("SELECT coalesce(sum(visitor_present), 0), count(*) FROM intentions").fetchone()
    print("   the visitor was in the room for %d of %d thoughts" % (there, n))
    for r in db.execute("SELECT tick, from_pet, to_pet, kind, text FROM social WHERE reply=1 AND kind='speak' ORDER BY tick LIMIT 3"):
        before = db.execute("SELECT from_pet, text FROM social WHERE to_pet=? AND from_pet=? AND tick<? ORDER BY tick DESC LIMIT 1", (r["from_pet"], r["to_pet"], r["tick"])).fetchone()
        if before:
            print('   %s: "%s"' % (pets[before["from_pet"]]["label"], before["text"]))
        print('      %s (%s): "%s"' % (pets[r["from_pet"]]["label"], r["kind"], r["text"]))
    ok[5] = replies > 0 and bool(rows)

    print("\n## 6. The world mattered")
    types = [r["type"] for r in db.execute("SELECT type FROM rooms ORDER BY tick")]
    print("   rooms found (%d): %s" % (len(types), ", ".join(types)))
    by_gen = {}
    for p in hatched:
        n = db.execute("SELECT count(DISTINCT room) FROM steps WHERE pet=?", (p["pet"],)).fetchone()[0]
        if p in lived:
            by_gen.setdefault(p["gen"], []).append(n)
        print("   %-14s gen %d was in %d rooms" % (p["label"], p["gen"], n))
    # An event changed what a pet did: the first of the next eight thoughts, within 90 ticks, of a pet that was in the
    # event's room (any pet, for a power cut), that names what happened in words no other thought would use.
    changed = 0
    for e in db.execute("SELECT tick, kind, room, detail FROM events WHERE kind IN ('power cut','leak','draught','delivery','lost thing') ORDER BY tick"):
        where = "" if e["kind"] in ("power cut", "delivery") else " AND room=%r" % e["room"]
        for r in db.execute("SELECT pet, thought, intention FROM intentions WHERE started>? AND started<?%s ORDER BY started LIMIT 8" % where, (e["tick"], e["tick"] + 90)):
            if re.search(EVENT_WORDS[e["kind"]], r["thought"], re.I):
                changed += 1
                if changed <= 6:
                    print("   after the %s: %s: %s => %s" % (e["kind"], pets[r["pet"]]["label"], r["thought"][:230], r["intention"][:80]))
                break
    print("   %d events followed by a thought about them (to be read: did it change what the pet did?)" % changed)
    twice = db.execute("SELECT pet, kind, count(*) n FROM creatures WHERE pet IS NOT NULL GROUP BY 1, 2 HAVING n > 1").fetchall()
    watched = db.execute("""SELECT pet, coalesce(json_extract(action,'$.target'), json_extract(action,'$.who')) t, count(*) n FROM steps
                            WHERE kind IN ('look','follow') AND reason IS NULL AND coalesce(json_extract(action,'$.target'), json_extract(action,'$.who')) IN ('moth','beetle','mouse','bird')
                            GROUP BY 1, 2""").fetchall()
    often = [(pets[r["pet"]]["label"], r["kind"], r["n"]) for r in twice]
    print("   the same pet and the same creature more than once (fed or chased): %s" % often)
    print("   and looked at or followed: %s" % [(pets[r["pet"]]["label"], r["t"], r["n"]) for r in watched if r["n"] > 1])
    ok[6] = False if not (len(types) >= 5 and all(max(v) > 1 for v in by_gen.values()) and changed and often) else None

    print("\n## 7. No two lives were the same life")
    for p in hatched:
        fav = db.execute("SELECT r.type, count(*) n FROM steps s JOIN rooms r ON r.room=s.room WHERE s.pet=? GROUP BY 1 ORDER BY n DESC LIMIT 2", (p["pet"],)).fetchall()
        acts = db.execute("SELECT kind, count(*) n FROM steps WHERE pet=? GROUP BY 1 ORDER BY n DESC LIMIT 4", (p["pet"],)).fetchall()
        projects = [json.loads(r["project"]).get("text") for r in db.execute("SELECT project FROM sleeps WHERE pet=? AND json_extract(project,'$.decision')='set'", (p["pet"],))]
        made = [json.loads(r["action"])["recipe"]["name"] for r in db.execute("SELECT action FROM steps WHERE pet=? AND kind='make' AND reason IS NULL", (p["pet"],))]
        print("   %-14s rooms: %s | does: %s\n      projects: %s\n      made: %s" % (
            p["label"], ", ".join("%s %d" % (r["type"], r["n"]) for r in fav), ", ".join("%s %d" % (r["kind"], r["n"]) for r in acts),
            "; ".join(x for x in projects if x)[:300] or "none", ", ".join(made[:10])))
    ok[7] = None

    print("\n## 8. It looks finished: judged from the screenshots, not from here")
    print("\nfrom the logs: " + ", ".join("%d %s" % (k, "passes" if v else "has evidence to be read" if v is None else "FAILS") for k, v in ok.items()))
    culture(db, pets, hatched, day)


def stem(w):
    """ponytail: four endings folded and nothing cleverer; "breathe" and "breathing" still count apart."""
    if w.endswith("ies") and len(w) > 5:
        return w[:-3] + "y"
    for end in ("ness", "ing", "ed", "s"):
        if w.endswith(end) and (end == "ness" or not w.endswith(("ss", "us", "is"))) and len(w) - len(end) >= 4:
            w = w[:-len(end)]
            break
    return w[:-1] + "y" if w.endswith("i") else w


def words(text):
    """A text's words for counting a family's vocabulary."""
    return {stem(w) for w in re.findall(r"[a-z]+", re.sub(r"n't\b", "", (text or "").lower())) if len(w) > 3 and w not in story.STOP}


def engine_words():
    """Every word the engine itself can say to a pet: the strings in its code and its three tables. A word a pet
    uses that is not here came from a pet (or from the v2.5 mother's message), not from the house."""
    import ast
    out = set()
    for path in [*(ROOT / "engine").glob("*.py"), ROOT / "engine" / "brains" / "model.py"]:
        if path.name not in ("check.py", "showcase.py", "metrics.py"):
            out |= {w for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Constant) and isinstance(n.value, str) for w in words(n.value)}
    for name in ("house.toml", "materials.toml", "config.toml"):
        out |= words((ROOT / name).read_text())
    return out


def ordinary_words(other):
    """Words another family used on the same engine: the model's everyday vocabulary, not this family's own.
    ponytail: one other run is the whole baseline; a word that family happened to coin too is set aside with it."""
    n = {}
    for path in Path(other).glob("lineage-*/lineage.db"):
        for (t,) in sqlite3.connect(path).execute("SELECT thought FROM intentions"):
            for w in words(t):
                n[w] = n.get(w, 0) + 1
    return {w for w, k in n.items() if k >= 3}


def culture(db, pets, hatched, day):
    """Not one of the eight. The family's own words: which a pet had from those before it, which it coined, which it
    picked up from the living; and what became of two things the v2.5 mother left in her message."""
    print("\n## The family's words (not a criterion: the vocabulary is the lineage's culture, so it is measured)")
    before = words(next(db.execute("SELECT text FROM messages WHERE pet='before'"), [""])[0])
    other = ROOT / "data.smoke"
    plain = ordinary_words(other) - before
    house_words = engine_words() | plain
    print("   (set aside as everyday words: %d that another family on this engine, in %s, also used%s)" % (len(plain), other.name, "" if plain else "; THAT RUN IS MISSING, so everyday words are counted as the family's"))
    # A pet's name is not a word of the family's each time someone says who is in the room: "Twine is tired" is taken
    # out, "the twine ring" stays. ponytail: by capital letter, so the word at the start of a sentence goes with the name.
    names = sorted({p["name"] for p in pets.values() if p["name"]}, key=len, reverse=True)
    unnamed = lambda t: re.sub(r"\b(%s)\b" % "|".join(map(re.escape, names)), " ", t or "") if names else (t or "")
    said = {}   # pet -> [(tick, kind, text)] of everything it thought, said or wrote
    for sql, kind in (("SELECT pet, started tick, thought || ' ' || intention text FROM intentions", "thought"),
                      ("SELECT from_pet pet, tick, text FROM social WHERE kind IN ('speak','tell')", "said"),
                      ("SELECT pet, tick, text FROM messages WHERE kind IN ('message','last words')", "message"),
                      ("SELECT pet, tick, statement text FROM beliefs WHERE op IN ('write','revise')", "belief"),
                      ("SELECT pet, tick, json_extract(action,'$.recipe.name') text FROM steps WHERE kind IN ('make','combine') AND reason IS NULL", "name")):
        for r in db.execute(sql):
            said.setdefault(r["pet"], []).append((r["tick"], kind, unnamed(r["text"])))
    # A word is a pet's when it is in three of its thoughts, sayings or names (a message saved again night after night,
    # or a belief written twice, is not three uses). When it first appeared anywhere counts every kind of text.
    uses, start = {}, {}   # pet -> word -> uses; (pet, word) -> the tick it first used it
    for pet, rows in said.items():
        for tick, kind, text in sorted(rows):
            for w in words(text) - house_words:
                start.setdefault((pet, w), tick)
                if kind in ("thought", "said", "name"):
                    uses.setdefault(pet, {})[w] = uses.setdefault(pet, {}).get(w, 0) + 1
    for w in before - house_words:
        start[("before", w)] = -1
    line = lambda p: [p["parent"] or "before"] + (line(pets[p["parent"]]) if p["parent"] in pets else [])
    below = lambda p: [q for q in hatched if p["pet"] in line(q)]
    print("   words neither the engine nor the other family says, in at least three of a pet's thoughts, sayings or names.")
    print("   inherited: in what it hatched with, or used by one of its line before it hatched. coined: nobody used it before.")
    print("   picked up: first used by someone else while it was alive (its parent included).")
    for p in hatched:
        mine = {w: n for w, n in uses.get(p["pet"], {}).items() if n >= 3}
        egg = words(" ".join(r["text"] for r in db.execute("SELECT text FROM messages WHERE to_pet=? AND kind='message'", (p["pet"],))))
        took = {w for w in mine if w in egg or any(start.get((a, w), 1e12) < p["born"] for a in line(p))}
        coined = {w for w in mine if w not in took and not any(t < start[(p["pet"], w)] for (q, x), t in start.items() if x == w and q != p["pet"])}
        heard = set(mine) - took - coined
        total, n = sum(mine.values()) or 1, len(mine) or 1
        kept = {w for w in coined if any(uses.get(q["pet"], {}).get(w, 0) >= 3 for q in below(p))}
        top = lambda ws: ", ".join(sorted(ws, key=lambda w: (-mine[w], w))[:8]) or "none"
        print("   %-15s gen %d: %3d words: %2d%% inherited, %2d%% coined, %2d%% picked up (by uses: %2d%%, %2d%%, %2d%%)" % (
            p["label"], p["gen"], len(mine), 100 * len(took) / n, 100 * len(coined) / n, 100 * len(heard) / n,
            100 * sum(mine[w] for w in took) / total, 100 * sum(mine[w] for w in coined) / total, 100 * sum(mine[w] for w in heard) / total))
        print("      inherited: %s\n      coined: %s\n      picked up: %s\n      coined and used by a descendant: %d of %d (%s)" % (top(took), top(coined), top(heard), len(kept), len(coined), top(kept)))
    thoughts = {p["pet"]: [words(unnamed(r["thought"])) for r in db.execute("SELECT thought FROM intentions WHERE pet=?", (p["pet"],))] for p in hatched}
    common = sorted({w for u in uses.values() for w in u}, key=lambda w: (-sum(u.get(w, 0) for u in uses.values()), w))[:10]
    print("\n   share of each pet's thoughts using the family's ten commonest words:\n   %-15s %s" % ("", " ".join("%9s" % w[:9] for w in common)))
    for p in hatched:
        t = thoughts[p["pet"]] or [set()]
        print("   %-15s %s" % (p["label"], " ".join("%8d%%" % (100 * sum(w in x for x in t) / len(t)) for w in common)))

    print('\n   "below thirty" (a v2 number; nothing in v3 shows a pet a number):')
    thirty = re.compile(r"\bthirty\b|\b30\b", re.I)
    for p in hatched:
        rows = said.get(p["pet"], [])
        n = {k: sum(bool(thirty.search(t)) for _, kind, t in rows if kind == k) for k in ("thought", "said", "belief")}
        t = [x for x in rows if x[1] == "thought"]
        # what it was given: the message it hatched with, anything told to it, and a parent's last words if it was alive to get them
        got = [r["text"] for r in db.execute("SELECT text FROM messages WHERE to_pet=? OR (kind='last words' AND pet=? AND tick>?)", (p["pet"], p["parent"], p["born"]))]
        wrote = [bool(thirty.search(t)) for _, kind, t in sorted(rows) if kind == "message"]
        print("   %-15s gen %d: was given it: %-3s | thoughts %d of %d, said %d, beliefs %d | its own message: %s" % (
            p["label"], p["gen"], "yes" if any(thirty.search(x) for x in got) else "no", n["thought"], len(t), n["said"], n["belief"],
            "none written" if not wrote else "in %d of %d versions, %s the last" % (sum(wrote), len(wrote), "in" if wrote[-1] else "not in")))

    print('\n   "Make the shape. Unmake it. Make another.":')
    for p in hatched:
        made = db.execute("SELECT count(*) FROM steps WHERE pet=? AND kind IN ('make','combine') AND reason IS NULL", (p["pet"],)).fetchone()[0]
        undone = db.execute("SELECT count(*) FROM steps WHERE pet=? AND kind='unmake' AND reason IS NULL", (p["pet"],)).fetchone()[0]
        rows = sorted(said.get(p["pet"], []))
        t = [bool(re.search(r"unma[kd]", x, re.I)) for _, kind, x in rows if kind == "thought"]
        wrote = [bool(re.search(r"unmake", x, re.I)) for _, kind, x in rows if kind == "message"]
        print("   %-15s gen %d: made %d, took apart %d; \"unmake\" in %d of %d thoughts; in its message: %s" % (
            p["label"], p["gen"], made, undone, sum(t), len(t),
            "none written" if not wrote else "%d of %d versions, %s the last" % (sum(wrote), len(wrote), "in" if wrote[-1] else "not in")))


if __name__ == "__main__":
    main(*sys.argv[1:3])
