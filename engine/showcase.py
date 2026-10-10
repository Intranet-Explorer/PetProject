"""The showcase's bar (SPEC-v3 §12.2), from the logs and nothing else.

    uv run python -m engine.showcase [data dir]

Prints the evidence for each of the eight criteria. Criteria 3, 4 and 6's "changed what it did" still need
reading: the script finds the passages, a person judges them."""
import json
import re
import sqlite3
import sys
from pathlib import Path

from . import story
from .world import GENES, ROOT, load_config

EVENT_WORDS = {"power cut": r"went dark|gone dark|power|every light|lights? (went|are|is) (out|dark)|no light", "leak": r"water (is|was)? ?coming|wet floor|floor is wet|leak|shifted",
               "draught": r"draught|blew|stuck shut|door (is )?(stuck|shut)", "delivery": r"crate|set down|deliver", "lost thing": r"not where|is gone|went missing|has gone|missing"}


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
    hatched = [p for p in pets.values() if p["born"] is not None]
    day = cfg["ticks_per_day"]
    gens = max((p["gen"] for p in hatched), default=0)
    print("# The bar: lineage %d, day %d, %d pets hatched over %d generations\n" % (lin, house["clock"]["day"], len(hatched), gens))
    ok = {}

    print("## 1. It reads like a creature (meter-talk under 10% for every pet after its first day; v2.5: 25.2% of thoughts, 57.9% of beliefs)")
    worst = 0
    for p in hatched:
        share, n = story.meter_share(db, p["pet"], p["born"] + day)
        every, total = story.meter_share(db, p["pet"])
        path = data / ("lineage-%d" % lin) / p["pet"] / "beliefs.json"
        beliefs = json.loads(path.read_text()) if path.exists() else []
        from .feel import meter_talk
        b = round(100 * sum(meter_talk(x["statement"]) for x in beliefs) / len(beliefs), 1) if beliefs else None
        print("   %-14s gen %d: %s%% of %d thoughts after day 1 (%s%% of all %d); %s%% of %d beliefs" % (p["label"], p["gen"], share, n, every, total, b, len(beliefs)))
        worst = max(worst, share or 0) if n >= 10 else worst
    ok[1] = worst < 10
    for r in db.execute("SELECT pet, thought FROM intentions WHERE meter=1 ORDER BY tick DESC LIMIT 5"):
        print("      flagged: %s: %s" % (pets[r["pet"]]["label"], r["thought"][:160]))

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
        print("   %-14s gen %d: hue %d, %s, %d limbs, roundness %.2f, stretch %.2f" % (p["label"], p["gen"], g["hue"], g["pattern"], g["limbs"], g["roundness"], g["stretch"]))
    ok[2] = bool(drift) and max(drift)[0] >= 0.2

    print("\n## 3. Something was passed down and mattered (a child's first-day thoughts that use a particular thing its parent told it)")
    # A candidate is a first-day thought that shares at least two words of content with ONE sentence of the message it
    # hatched with, not counting the words every such thought has ("mother", "told", "said"). The engine's own
    # sense line "you want your mother" cannot make one. Whether the thought changed what it did is for a reader.
    common, found = {"mother", "father", "parent", "told", "tell", "said", "say"}, 0
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
    # sentence A told B, whether B kept it in its own message to C, and whether C kept it in its own message.
    # "Held" needs all three. A "correction" needs B to have kept it and C to have changed or dropped it; whether
    # C's own experience contradicted it is for a reader.
    msgs = {}   # pet -> every version of the message it wrote, oldest first
    for r in db.execute("SELECT pet, text FROM messages WHERE kind IN ('message', 'last words') ORDER BY tick"):
        msgs.setdefault(r["pet"], []).append(r["text"])
    held = corrected = 0
    state = lambda sentence, texts: max((story.alike(story.content(sentence), story.content(x)) for t in texts for x in story.split(t)), default=0.0)
    for c in hatched:
        b = pets.get(c["parent"])
        if not b or c["pet"] not in msgs:
            continue
        a = pets[b["parent"]]["pet"] if b["parent"] in pets else "before" if b["gen"] == 1 else None
        if a not in msgs or b["pet"] not in msgs:
            continue
        for sentence in dict.fromkeys(x for t in msgs[a] for x in story.split(t)):   # anything A ever put in its message
            in_b, in_c = state(sentence, msgs[b["pet"]]), state(sentence, msgs[c["pet"]])
            if in_b < 0.5:
                continue
            kind = "held" if in_c >= 0.8 else "changed" if in_c >= 0.5 else "dropped"
            held += kind == "held"
            corrected += kind != "held"
            if held + corrected <= 14:
                print('   %s -> %s -> %s [%s by the third; %s]: "%s"' % (
                    "the one before" if a == "before" else pets[a]["label"], b["label"], c["label"], kind, story.truth(sentence) or "unchecked", sentence[:150]))
    print("   over every line of three generations: %d sentences held, %d changed or dropped by the third" % (held, corrected))
    ok[4] = True if held else None if corrected else False

    print("\n## 5. They dealt with each other without the visitor")
    rows = dict(db.execute("SELECT kind, count(*) FROM social WHERE to_pet IS NOT NULL AND to_pet != 'visitor' GROUP BY 1").fetchall())
    replies = db.execute("SELECT count(*) FROM social WHERE reply=1").fetchone()[0]
    print("   %s; replies: %d" % (rows, replies))
    for r in db.execute("SELECT tick, from_pet, to_pet, kind, text FROM social WHERE reply=1 ORDER BY tick LIMIT 3"):
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
        by_gen.setdefault(p["gen"], []).append(n)
        print("   %-14s gen %d was in %d rooms" % (p["label"], p["gen"], n))
    # An event changed what a pet did: the first thought, within about fifteen thoughts' time, of a pet that was in the
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
    both = {(r["pet"], r["kind"]): r["n"] for r in twice}
    for r in watched:
        both[(r["pet"], r["t"])] = both.get((r["pet"], r["t"]), 0) + r["n"]
    often = [(pets[k[0]]["label"], k[1], n) for k, n in both.items() if n > 1]
    print("   the same pet and the same creature more than once (fed, chased, watched or followed): %s" % often)
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


if __name__ == "__main__":
    main(*sys.argv[1:3])
