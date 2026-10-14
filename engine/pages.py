"""The page's read-only views of the house (SPEC-v3.5.3): every pet that ever lived, a page for each, the story by
world day, and everything made. Nothing here changes the house; it only gathers what is already recorded."""
import json
import re

from . import firsts, genome, things
from .world import clock, label, season_of

ROMAN = ["", "", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"]
GONE_WHERE = {"fed to the machine": "traded into the machine", "taken apart": "taken apart", "combined": "joined into something else",
              "eaten": "eaten", "stolen by the mouse": "taken by the mouse", "set into a statue": "set into a statue"}


def day_of(cfg, tick):
    return None if tick is None else clock(cfg, tick)["day"]


def rows(db, sql, *args):
    try:
        cur = db.execute(sql, args)
    except Exception:   # a run from before the table was kept
        return []
    keys = [d[0] for d in cur.description]
    return [dict(zip(keys, r)) for r in cur.fetchall()]


def families(house):
    """pet id -> family number: the first of each line with no parent, in the order they came, is a family (the first
    one 1, the foundling 2), and everyone descended from it is of it. (The dead are put away without their own word
    for it, so it is worked out from the tree.)"""
    P, out = house["pets"], {}
    roots = sorted((p for p in P.values() if not p.get("parent") or p["parent"] not in P), key=lambda p: int(p["id"][1:]))
    for n, r in enumerate(roots, 1):
        todo = [r["id"]]
        while todo:
            pid = todo.pop()
            out[pid] = P[pid].get("family", n)
            todo += [k for k in P[pid].get("children", []) if k in P]
    return out


def numbered(house):
    """pet id -> its name as shown, with a number where a name was used before ("Grey Light II"), by the order they came.
    The stored name is not changed."""
    seen, out = {}, {}
    for p in sorted(house["pets"].values(), key=lambda p: int(p["id"][1:])):
        name = label(p)
        seen[name] = seen.get(name, 0) + 1
        out[p["id"]] = name + (ROMAN[seen[name]] if seen[name] < len(ROMAN) else " %d" % seen[name])
    return out


def life_stage(p):
    """The stage it is drawn at: as it is, or for the dead as they were in life."""
    return p.get("stage_before") or "elder" if p["stage"] == "dead" else p["stage"]


def pet_card(house, cfg, p, fam, names):
    life = p.get("life") if isinstance(p.get("life"), dict) else {}
    return {"id": p["id"], "name": names[p["id"]], "stored_name": p.get("name"), "family": fam.get(p["id"], 1), "gen": p["gen"],
            "stage": p["stage"], "drawn": life_stage(p), "genome": p["genome"], "parent": p.get("parent"),
            "children": [k for k in p.get("children", []) if k in house["pets"]], "alive": p["stage"] not in ("dead",),
            "laid_day": day_of(cfg, p.get("laid")), "born_day": day_of(cfg, p.get("born")), "died_day": day_of(cfg, p.get("died")),
            "cause": p.get("cause"), "days": life.get("days"), "room": p.get("room"), "word": p.get("word")}


def links(house, db, fam, names):
    """What passed between the two families, one line each, oldest first: the foundling, and gifts, songs taught,
    nuzzles and things told across the line (the social log)."""
    out = []
    for pid, f in fam.items():
        p = house["pets"][pid]
        if f > 1 and not p.get("parent"):
            out.append({"kind": "foundling", "tick": p.get("laid"), "a": pid, "b": None, "text": "%s came to the house as an egg that was nobody's" % names[pid]})
    seen = set()
    for r in rows(db, "SELECT tick, from_pet, to_pet, kind, text FROM social WHERE kind IN ('give','teach song','nuzzle','tell') ORDER BY tick"):
        a, b = r["from_pet"], r["to_pet"]
        if a in fam and b in fam and fam[a] != fam[b] and (a, b, r["kind"]) not in seen:
            seen.add((a, b, r["kind"]))
            verb = {"give": "gave something to", "teach song": "taught a song to", "nuzzle": "nuzzled", "tell": "told something to"}[r["kind"]]
            out.append({"kind": r["kind"], "tick": r["tick"], "a": a, "b": b, "text": "%s %s %s" % (names[a], verb, names[b])})
    return out


def all_pets(eng):
    h, cfg = eng.house, eng.cfg
    fam, names = families(h), numbered(h)
    pets = [pet_card(h, cfg, p, fam, names) for p in sorted(h["pets"].values(), key=lambda p: int(p["id"][1:]))]
    return {"pets": pets, "links": links(h, eng.db, fam, names) if eng.db else [], "day": h["clock"]["day"]}


def named_after(house, p, names):
    """The earlier pet whose name this one carries, nearest in the family first, or None."""
    if not p.get("name"):
        return None
    before = [q for q in house["pets"].values() if q["id"] != p["id"] and q.get("name") == p["name"] and int(q["id"][1:]) < int(p["id"][1:])]
    line, q = [], house["pets"].get(p.get("parent") or "")
    while q:
        line.append(q["id"])
        q = house["pets"].get(q.get("parent") or "")
    before.sort(key=lambda q: (q["id"] not in line, -int(q["id"][1:])))
    return {"id": before[0]["id"], "name": names[before[0]["id"]]} if before else None


def traits(house, p):
    """Its body and temperament in plain words, each with the parent it came from where that is known."""
    par = house["pets"].get(p.get("parent") or "")
    mine = genome.parts(p["genome"], ("plan",)) + genome.parts(p["genome"])
    theirs = set(genome.parts(par["genome"], ("plan",)) + genome.parts(par["genome"])) if par else set()
    body = [{"text": w, "from": par["id"] if par and w in theirs else None} for w in mine]
    temper = []
    for g, v in sorted(p.get("temper", {}).items(), key=lambda kv: -kv[1]):
        if v >= 0.6 or v <= 0.3:
            pv = (par or {}).get("temper", {}).get(g)
            like = pv is not None and (pv >= 0.6) == (v >= 0.6) and (pv <= 0.3) == (v <= 0.3)
            temper.append({"text": g if v >= 0.6 else "not very " + g, "from": par["id"] if par and like else None})
    return {"body": body or [{"text": "a plain, smooth body", "from": None}], "temper": temper, "describe": genome.describe(p["genome"])}


def thing_key(o_made, name):
    return str(o_made["id"]) if o_made.get("id") is not None else "g%s-%s" % (o_made.get("made") or o_made.get("tick"), re.sub(r"\W+", "-", name))


def all_things(eng):
    """Everything made, where it is now, newest first: standing or put away in a room (a keepsake box says whose),
    and what is gone and how."""
    h, cfg = eng.house, eng.cfg
    fam, names = families(h), numbered(h)
    out = []
    for r in h["rooms"].values():
        if not r["type"]:
            continue
        for n, o in things.made(r).items():
            m, on = o["made"], o.get("on")
            box = r["objects"].get(on) if on else None
            keep = (box or {}).get("fix", {}).get("keepsake")
            where = "in the keepsake box for %s, in %s" % (names.get(keep, "someone"), r["name"]) if keep else \
                "on the %s in %s" % (on, r["name"]) if on else "on the wall of %s" % r["name"] if o.get("wall") else "in %s" % r["name"]
            out.append({"id": thing_key(m, n), "name": n, "recipe": m["recipe"], "by": m["by"], "by_name": names.get(m["by"]), "owner": m.get("owner"),
                        "family": fam.get(m["by"]), "room": r["id"], "room_name": r["name"], "where": where, "gone": None, "tick": m["tick"],
                        "day": day_of(cfg, m["tick"]), "bits": m.get("bits", []), "uses": m.get("uses", 0), "heirloom": bool(m.get("heirloom")),
                        "invented": m["recipe"].get("kind") in h.get("invented", {}), "statue": False, "keepsake": bool(keep), "star": m.get("star")})
        for n, o in r["objects"].items():
            if o.get("statue") or (o.get("fix", {}).get("built") and "statue" in n):
                # a statue standing has `fix.built` (who raised it, began and finished); one going up has `site`
                built, site = o.get("fix", {}).get("built") or {}, o.get("site") or {}
                by, began = built.get("by") or site.get("by"), built.get("began") or site.get("at")
                paws = built.get("paws") or [k for k, v in (site.get("paws") or {}).items() if v] or ([by] if by else [])
                out.append({"id": "statue-" + re.sub(r"\W+", "-", n), "name": n, "recipe": {"kind": "statue"}, "by": by,
                            "by_name": names.get(by), "owner": None, "family": (o.get("statue") or {}).get("family"),
                            "room": r["id"], "room_name": r["name"], "where": "in %s" % r["name"] if built else "going up in %s" % r["name"], "gone": None,
                            "tick": began, "day": day_of(cfg, began), "bits": [], "uses": 0, "heirloom": False, "invented": False, "statue": True,
                            "keepsake": False, "of": (o.get("statue") or {}).get("of"), "of_name": names.get((o.get("statue") or {}).get("of")),
                            "standing": bool(built), "raised_day": day_of(cfg, built.get("at")), "makers": [{"id": k, "name": names.get(k)} for k in paws if k in names],
                            "statue_name": (o.get("statue") or {}).get("name")})
    for g in h.get("gone_things", []):
        out.append({"id": thing_key(g, g["name"]), "name": g["name"], "recipe": g["recipe"], "by": g["by"], "by_name": names.get(g["by"]), "owner": g.get("owner"),
                    "family": fam.get(g["by"]), "room": None, "room_name": None, "where": GONE_WHERE.get(g["gone"][1], g["gone"][1]), "gone": g["gone"][1],
                    "tick": g["made"], "day": day_of(cfg, g["made"]), "bits": [], "uses": g.get("uses", 0), "heirloom": False,
                    "invented": g["recipe"].get("kind") in h.get("invented", {}), "statue": False, "keepsake": False, "star": g.get("star")})
    out.sort(key=lambda t: -(t["tick"] or 0))
    return {"things": out, "kinds": sorted({t["recipe"].get("kind") for t in out if t["recipe"].get("kind")}),
            "rooms": sorted({t["room_name"] for t in out if t["room_name"]})}


def thing_page(eng, key):
    t = next((t for t in all_things(eng)["things"] if t["id"] == key), None)
    if not t:
        return None
    name = t["name"]
    if t["statue"]:   # a statue is told of as "began a <name> in…" and "a statue of <pet>"
        ok = lambda m: ("began a %s in" % name) in m["text"] or (t.get("of_name") and ("statue of %s" % t["of_name"].rstrip(" IVX")) in m["text"])
        like = "%statue%"
    else:   # by its name in quotes, or (older moments, and "invented the <name>:") bare and not the start of a longer name
        bare = re.compile(r"(?<![\w'])%s(?=$|[:,.;!?]| it calls)" % re.escape(name))
        ok = lambda m: ("'%s'" % name) in m["text"] or ("'" not in m["text"].replace("'s ", "") and bare.search(m["text"])) or (m["kind"] == "invented" and bare.search(m["text"]))
        like = "%" + name.replace("%", "") + "%"
    moments = rows(eng.db, "SELECT tick, day, hour, kind, text, pet, room FROM moments WHERE text LIKE ? AND tick >= ? ORDER BY tick LIMIT 400",
                   like, t["tick"] or 0) if eng.db else []
    return dict(t, moments=[m for m in moments if ok(m)][:200], does=(t["recipe"] or {}).get("purpose"))


def pet_page(eng, pid, beliefs_of):
    h, cfg, db = eng.house, eng.cfg, eng.db
    p = h["pets"].get(pid)
    if not p:
        return None
    fam, names = families(h), numbered(h)
    card = pet_card(h, cfg, p, fam, names)
    life = p.get("life") if isinstance(p.get("life"), dict) else {}
    par = h["pets"].get(p.get("parent") or "")
    sibs = [k for k in (par or {}).get("children", []) if k != pid and k in h["pets"]]
    moments = rows(db, "SELECT tick, day, hour, kind, text, pet, room FROM moments WHERE pet = ? ORDER BY tick", pid) if db else []
    made = [t for t in all_things(eng)["things"] if t["by"] == pid]
    said = lambda sql: rows(db, sql, pid) if db else []
    words = {
        "message": [m["text"] for m in (p.get("message") or life.get("messages") or []) if isinstance(m, dict)][-1:],
        "last_words": life.get("last_words") or (p.get("last_words") if isinstance(p.get("last_words"), str) else None),
        "sayings": [r["text"] for r in said("SELECT DISTINCT text FROM claims WHERE pet = ? AND kind IN ('tell', 'writing') ORDER BY tick DESC LIMIT 12")],
        "songs": [{"name": r["name"], "how": r["how"]} for r in said("SELECT name, how FROM songs WHERE by = ? ORDER BY tick")],
        "walls": [{"text": r["text"], "place": r["place"], "room": h["rooms"].get(r["room"], {}).get("name")}
                  for r in said("SELECT DISTINCT text, place, room FROM inscriptions WHERE by = ? AND what = 'written' ORDER BY tick")],
        "beliefs": [b.get("statement") for b in (beliefs_of(p) or [])][-8:] if p["stage"] != "dead" else [b["statement"] for b in life.get("beliefs", [])][-8:],
        "reads": [{"question": r["question"], "title": r["title"], "text": r["text"], "day": day_of(cfg, r["tick"])}
                  for r in said("SELECT question, title, text, tick FROM library WHERE pet = ? ORDER BY tick DESC LIMIT 20")],
    }
    if not words["last_words"] and p["stage"] == "dead":   # the founder's are kept with its life (life.json)
        from pathlib import Path
        f = eng.lineage_dir(p["lineage"]) / pid / "life.json" if hasattr(eng, "lineage_dir") else None
        try:
            words["last_words"] = json.loads(Path(f).read_text()).get("last_words") if f else None
        except Exception:
            pass
    return {"pet": card, "named_after": named_after(h, p, names), "parent": par and par["id"], "siblings": sibs,
            "children": card["children"], "names": {k: names[k] for k in h["pets"]}, "traits": traits(h, p), "moments": moments,
            "made": made, "words": words, "my_life": life.get("my_life"), "family_names": {},
            "bests": firsts.page(h, cfg, p)}   # SPEC-v3.5.4 §7, §9: its ambition, its bests and its family's


def story_days(eng, before=None, n=7):
    """The house's history by world day, newest first, `n` days at a time (before world day `before`), each day with
    its season and, from 14 October 2026 on, its weather."""
    h, cfg = eng.house, eng.cfg
    top = (before or h["clock"]["day"] + 1) - 1
    lo = max(1, top - n + 1)
    ms = rows(eng.db, "SELECT n, tick, day, hour, kind, text, pet, room FROM moments WHERE day BETWEEN ? AND ? ORDER BY tick DESC", lo, top) if eng.db else []
    skies, chron = h.get("skies", {}), {c["day"]: c for c in h.get("chronicle", [])}
    days = [{"day": d, "season": season_of(cfg, d), "weather": skies.get(str(d)) or (h["weather"] if d == h["clock"]["day"] else None),
             "summary": (chron.get(d) or {}).get("text"), "moments": [m for m in ms if m["day"] == d]} for d in range(top, lo - 1, -1)]
    fam, names = families(h), numbered(h)
    return {"days": days, "more": lo > 1, "names": names, "families": fam, "today": h["clock"]["day"],
            "things": {t["name"]: t["id"] for t in all_things(eng)["things"]}}
