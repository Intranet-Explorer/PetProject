"""The page's read-only views of the house (SPEC-v3.5.3): every pet that ever lived, a page for each, the story by
world day, and everything made. Nothing here changes the house; it only gathers what is already recorded."""
import json
import re

from . import firsts, genome, order, store, things
from . import design
from . import contracts as K
from . import items, lab4   # SPEC-v5.0 §5 (helper C)
from . import projects   # SPEC-v5.3 (helper A)
from .world import clock, label, season_of

HOOK_WORDS = {"avoid_place": "keeps away from %s", "avoid_thing": "keeps away from %s", "prefer_thing": "goes for %s", "trust": "trusts %s",
              "watch": "watches %s", "do_at": "does it: %s", "make": "makes %s", "never": "never will: %s"}   # SPEC-v4.2 §5.1 on the Mind page


def hook_words(h):
    h = K.hook(h)
    return (HOOK_WORDS[h["name"]] % h["arg"] + (" (%s)" % h["when"] if h.get("when") else "")) if h else ""

ROMAN = ["", "", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"]
GONE_WHERE = {"fed to the machine": "traded into the machine", "taken apart": "taken apart", "combined": "joined into something else",
              "eaten": "eaten", "stolen by the mouse": "taken by the mouse", "set into a statue": "set into a statue",
              "swept up and fed to the Works by the sweeper": "swept up by the sweeper and fed to the Works"}
KEPT = ("how", "made_in", "users", "words", "title_shown", "design", "parts")   # SPEC-v3.5.8: what a made thing keeps for its card from now on (SPEC-v3.6d: a design's effects and parts)


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
            "cause": p.get("cause"), "days": life.get("days"), "room": p.get("room"), "word": p.get("word"), "byname": p.get("byname"),
            "founder": bool(p.get("founder")), "kin": p.get("kin")}   # (SPEC-v4.0.5 §3.4: the tree marks a founder egg given to a family)


def links(house, db, fam, names):
    """What passed between the two families, one line each, oldest first: the foundling, and gifts, songs taught,
    nuzzles and things told across the line (the social log)."""
    out = []
    for pid, f in fam.items():
        p = house["pets"][pid]
        if f > 1 and not p.get("parent") and not p.get("kin"):   # (a founder egg with a kin is that family's, not a stranger: SPEC-v4.0.5 §3.4)
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


def made_firsts(house):
    """(maker, tick made, kind) -> "house" or "family": the made things that were a first (SPEC-v3.5.7 §5, §7), from the
    house's feats ("kind:rug", or "make:rug|soft" for the first soft one), each logged at the very tick the thing was
    made. Feats were kept from day 61 (SPEC-v3.5.4); a first before then is not known."""
    out = {}
    for f in house.get("feats", {}).get("list", []):
        kind, _, key = f.get("key", "").partition(":")
        if f["kind"] == "first" and kind in ("kind", "make") and f.get("level") in ("house", "family"):
            k = (f["pet"], f["tick"], key.split("|")[0])
            out[k] = "house" if "house" in (out.get(k), f["level"]) else "family"
    return out


def all_things(eng):
    """Everything made, where it is now, newest first: standing or put away in a room (a keepsake box says whose),
    and what is gone and how."""
    h, cfg = eng.house, eng.cfg
    fam, names, firsts_ = families(h), numbered(h), made_firsts(h)
    first = lambda by, tick, r: firsts_.get((by, tick, r.get("kind")))
    out = []
    for r in h["rooms"].values():
        if not r["type"]:
            continue
        for n, o in things.made(r).items():
            m, on = o["made"], o.get("on")
            box = r["objects"].get(on) if on else None
            keep = (box or {}).get("fix", {}).get("keepsake")
            where, stored = store.where(h, cfg, r, n)   # SPEC-v3.5.12 §1: where it is, in the same words as its card
            out.append({"id": thing_key(m, n), "name": n, "recipe": m["recipe"], "by": m["by"], "by_name": names.get(m["by"]), "owner": m.get("owner"),
                        "family": fam.get(m["by"]), "room": r["id"], "room_name": r["name"], "where": where, "stored": stored, "found": m.get("found"), "gone": None, "tick": m["tick"],
                        "day": day_of(cfg, m["tick"]), "bits": m.get("bits", []), "uses": m.get("uses", 0), "heirloom": bool(m.get("heirloom")),
                        "invented": m["recipe"].get("kind") in h.get("invented", {}), "statue": False, "keepsake": bool(keep), "star": m.get("star"),
                        "first": first(m["by"], m["tick"], m["recipe"]), "title_shown": bool(m["recipe"].get("title")) and order.kept(h, cfg, r, n),
                        **{k: m[k] for k in KEPT if m.get(k)}})
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
                    "tick": g["made"], "day": day_of(cfg, g["made"]), "bits": g.get("bits", []), "uses": g.get("uses", 0), "heirloom": False, **{k: g[k] for k in KEPT if g.get(k)},
                    "invented": g["recipe"].get("kind") in h.get("invented", {}), "statue": False, "keepsake": False, "star": g.get("star"),
                    "first": first(g["by"], g["made"], g["recipe"]), "gone_day": day_of(cfg, g["gone"][0]),
                    # SPEC-v3.6d §7: a thing that matters can be bought back from the catalog, once
                    "made_id": g.get("id"), "buyable": bool(cfg.get("design", {}).get("on") and g.get("id") is not None and not g.get("bought") and design.matters(h, cfg, g))})
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
    return dict(t, moments=[m for m in moments if ok(m)][:200], does=(t["recipe"] or {}).get("purpose"), **({} if t["statue"] else thing_more(eng, t)))


USED = ("use", "sit on", "play")   # what in the log's `doing` is a pet using a thing (not tidying it, carrying it or putting it away)


def thing_more(eng, t):
    """SPEC-v3.5.7 §5: what the thing card shows beyond the list, each only as far as it is recorded: what its kind is
    for, the room it was made in (its "made" moment), the things it was joined from, who used it most (the log's
    `doing`, kept from tick 17663, which sees sitting, playing and using but not, say, a lamp's warmth), and what pets
    said or wrote about it (claims and inscriptions that name it)."""
    h, cfg, db, name, kind = eng.house, eng.cfg, eng.db, t["name"], t["recipe"].get("kind")
    if t["gone"]:
        rec = next((g for g in h.get("gone_things", []) if g["name"] == name and g["made"] == t["tick"]), {})
        end = (rec.get("gone") or [None])[0]
    else:
        o = h["rooms"][t["room"]]["objects"].get(name, {})
        rec, end = o.get("made", {}), None
    inv, tool = h.get("invented", {}).get(kind), cfg["craft"]["tool"].get(kind)
    need = cfg["materials"].get(t["recipe"].get("material"), {}).get("need")
    use = inv["does"] if inv and inv.get("does") else "used to %s" % tool["does"] if tool else "for %s" % need if need else None
    # SPEC-v5.0 §5: a standing item's card in words (what it does, its wear, charge and make), as the room sends it
    out = {**({"item": item_view(h, cfg, o, name)} if not t["gone"] and K.on5(cfg) and o.get("item") else {}),
           **({"recipe5": lab4.recipe_view(h, cfg, kind)} if K.on51(cfg, "grammar") else {}), "use": use, "material": t["recipe"].get("material"), "joined": rec.get("from") or [], "invention": bool(inv and inv.get("by") == t["by"] and inv.get("tick") == t["tick"]),
           "made_in": None, "used_by": [], "words": []}
    if not db:
        return out
    upto = end if end is not None else 1 << 62
    m = rows(db, "SELECT room FROM moments WHERE kind = 'made' AND tick = ? AND pet = ? AND text LIKE ?", t["tick"], t["by"], "%'" + name + "'%")
    out["made_in"] = h["rooms"].get(m[0]["room"], {}).get("name") if m and m[0]["room"] else None
    out["used_by"] = rows(db, "SELECT pet AS id, COUNT(*) AS n FROM doing WHERE lower(thing) = lower(?) AND what IN (%s) AND tick_from BETWEEN ? AND ? "
                          "GROUP BY pet ORDER BY n DESC" % ",".join("?" * len(USED)), name, *USED, t["tick"] or 0, upto)
    if " " in name:   # a one-word name ("leaning") is a word pets use for other things too
        longer = [n for n in all_names(h) if n != name.lower() and name.lower() in n]   # "dusk signal" is not "dusk signal two"
        said = re.compile(r"(?<![\w'])%s(?![\w])" % re.escape(name), re.I)
        seen = set()
        for r in rows(db, "SELECT pet, tick, kind, text FROM claims WHERE kind IN ('tell', 'writing') AND text LIKE ? AND tick BETWEEN ? AND ? ORDER BY tick",
                      "%" + name + "%", t["tick"] or 0, upto):
            low = r["text"].lower()
            if said.search(r["text"]) and not any(n in low for n in longer) and low not in seen:
                seen.add(low)
                out["words"].append({"pet": r["pet"], "tick": r["tick"], "day": day_of(cfg, r["tick"]), "how": "wrote" if r["kind"] == "writing" else "said", "text": r["text"]})
    for r in rows(db, "SELECT by, tick, text FROM inscriptions WHERE place = ? AND what = 'written' AND tick BETWEEN ? AND ? ORDER BY tick", name, t["tick"] or 0, upto):
        out["words"].append({"pet": r["by"], "tick": r["tick"], "day": day_of(cfg, r["tick"]), "how": "wrote on it", "text": r["text"]})
    out["words"] = sorted(out["words"], key=lambda w: w["tick"])[:6]
    return out


def all_names(h):
    return {n.lower() for r in h["rooms"].values() if r["type"] for n in things.made(r)} | {g["name"].lower() for g in h.get("gone_things", [])}


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
    # SPEC-v3.5.7 §6: which of its things were firsts (the house's record of who first made each kind, at that tick),
    # how many firsts it has in the house and in its family, and its quest log
    N, f = h.get("new") or {}, str(fam.get(pid, 1))
    by_me = lambda d: {k for k, v in (d or {}).items() if v.get("pet") == pid and not k.startswith(("join:", "got:", "make:"))}   # (a nature is at most its own first; the other two restate a kind or a process)
    in_house, in_family = by_me(N.get("house")), by_me((N.get("family") or {}).get(f))
    for t in made:
        k, was = "kind:%s" % (t["recipe"] or {}).get("kind"), lambda d: (d or {}).get(k, {})
        t["first"] = "house" if was(N.get("house")) == {"pet": pid, "tick": t["tick"]} else \
            "family" if was((N.get("family") or {}).get(f)) == {"pet": pid, "tick": t["tick"]} else None
    A = p.get("ambition") or {}
    done_with = next((t for t in made if A.get("done") and t["tick"] == A["done"]), None)
    quest = {
        "ambition_thing": done_with and {"id": done_with["id"], "name": done_with["name"]},
        "project": p.get("project") and {"text": p["project"]["text"], "day": day_of(cfg, p["project"].get("since"))},
        "projects_done": [{"text": x["text"], "day": day_of(cfg, x.get("ended"))} for x in p.get("projects", []) if x.get("how") == "finished"][-3:],
        "wants": [w["text"] for w in p.get("wants", [])] if p["stage"] != "dead" else [],
        "wants_done": list({m["text"]: {"text": m["text"], "day": m["day"]} for m in moments if m["kind"] == "want"}.values())[-3:],   # (the latest of each)
    }
    if K.on(cfg):   # SPEC-v4.2 (helper B): the mind on the card: its self-page, its beliefs with their hooks, what it was taught, its theory of the visitor
        words["beliefs_hooked"] = [{"statement": b.get("statement"), "hook": hook_words(b.get("hook")), "acted": b.get("acted") is not None,
                                    "doubt": "%s isn't sure about that." % label(p) if b.get("doubted") else ""} for b in (beliefs_of(p) or []) if b.get("status", "active") == "active" and b.get("hook")][-8:]
        card["spirit"] = {"self": K.self_lines(p.get("self") or (p.get("last_self") or {}).get("page")), "taught": "taught: " + ", ".join(p["taught"]) if p.get("taught") else "",
                          "theory": p.get("visitor_theory") or "", "leave": p.get("leave")}
    from . import book, knowledge   # SPEC-v5.1 §5, §6 (helper B): what it knows how to make, and its reading list with each read's links and source
    if knowledge.on(cfg):
        card["knows51"] = knowledge.card(h, cfg, p)
    from . import habits   # SPEC-v5.3 §1.4 (helper B): its habits in words
    if habits.on(cfg):
        card["habits53"] = habits.card(h, cfg, p)
    if projects.on(cfg):   # SPEC-v5.3 §8 (helper A): its project and the next step
        card["project53"] = projects.card(h, cfg, p)
    if book.on(cfg):
        words["reading"] = [dict(K.read(r), day=day_of(cfg, r.get("tick"))) for r in p.get("read") or []]
    return {"pet": card, "named_after": named_after(h, p, names), "parent": par and par["id"], "siblings": sibs,
            "children": card["children"], "names": {k: names[k] for k in h["pets"]}, "traits": traits(h, p), "moments": moments,
            "made": made, "words": words, "my_life": life.get("my_life"), "family_names": {},
            "bests": firsts.page(h, cfg, p),   # SPEC-v3.5.4 §7, §9: its ambition, its bests and its family's
            "firsts": {"house": len(in_house), "family": len(in_family - in_house)}, "quest": quest}


def story_days(eng, before=None, n=7):
    """The house's history by world day, newest first, `n` days at a time (before world day `before`), each day with
    its season and, from 14 October 2026 on, its weather."""
    h, cfg = eng.house, eng.cfg
    top = (before or h["clock"]["day"] + 1) - 1
    lo = max(1, top - n + 1)
    ms = rows(eng.db, "SELECT n, tick, day, hour, kind, text, pet, room FROM moments WHERE day BETWEEN ? AND ? ORDER BY tick DESC", lo, top) if eng.db else []
    from . import talk
    talk.attach(h, ms)   # SPEC-v4.0 §5: a conversation's lines, for the story
    skies, chron = h.get("skies", {}), {c["day"]: c for c in h.get("chronicle", [])}
    days = [{"day": d, "season": season_of(cfg, d), "weather": skies.get(str(d)) or (h["weather"] if d == h["clock"]["day"] else None),
             "summary": (chron.get(d) or {}).get("text"), "moments": [m for m in ms if m["day"] == d]} for d in range(top, lo - 1, -1)]
    fam, names = families(h), numbered(h)
    return {"days": days, "more": lo > 1, "names": names, "families": fam, "today": h["clock"]["day"],
            "things": {t["name"]: t["id"] for t in all_things(eng)["things"]}}


# ---- SPEC-v5.0 §5 (helper C): an item's card and the work board, as the page reads them ----
# Words, not numbers: an item's wear and charge move at every use, and the page is sent a room's objects again only
# when something in them changes (SPEC-v4.0.5 §7.2), so a word that holds through many uses costs nothing between.

def wear_words(it):
    s = it["state"]
    return "broken" if s["broken"] else "about to break" if s["wear"] >= 0.85 else "worn" if s["wear"] >= 0.5 else "used" if s["wear"] >= 0.1 else "new"


def charge_words(it, full):
    """§1.6 what it runs on, in words: "empty", "full of oil", "half a lantern of oil left". `full`: the kind's charge full."""
    out = []
    for m, n in it["state"]["charge"].items():
        f = max(n, full.get(m) or 1)
        out.append("empty" if not n else "full of %s" % m if n >= f else "a little %s left" % m if n * 3 <= f
                   else "half a %s of %s left" % (it["kind"], m) if n * 3 <= 2 * f else "most of its %s left" % m)
    return "; ".join(out)


def does_words(it):
    """Its verbs in contracts.VERB_WORDS, strongest first ("it covers and keeps warm; it holds things"); a keepsake is kept for itself."""
    v = sorted(it["verbs"], key=lambda k: -it["verbs"][k])
    return "; ".join(K.VERB_WORDS[k] for k in v) if v else "nothing: it is kept for its own sake"


def item_view(house, cfg, o, name):
    """§5 an item on the page, from o["item"] (read only: `items.of` is its writer): what it does, its wear, its charge and
    how well it is made, each only when there is something to say; `broken` for the room to draw it cracked. Its owner
    and maker are the made thing's, already sent."""
    it, e = o["item"], items.entry(house, cfg, o, name)
    out = {"does": does_words(it), "wear": wear_words(it), "charge": charge_words(it, e[2] if e else {}),
           "quality": "finely made" if it["quality"] >= 0.66 else "well made" if it["quality"] >= 0.33 else ""}
    return {k: v for k, v in out.items() if v} | ({"broken": True} if it["state"]["broken"] else {})


def board_view(house):
    """§2.2, §5 the work board (contracts.board at house["v5"]["board"]) as the page draws it, small: each open deficit's
    id, kind, words, urgency and since; each job's deficit, taker and words; what closed today and by whom. The board's own
    tick is left out, so the page is sent it again only when something on it changes (server.sections)."""
    b = K.board((house.get("v5") or {}).get("board"))
    say = lambda x: x["words"] or lab4.DEFICIT_WORDS.get(x["kind"], x["kind"])   # (B's words; the Lab's while B writes none)
    needs = (house.get("v5") or {}).get("needs") or {}   # SPEC-v5.1 §8 (helper C): what a make step it can't plan lacks (jobs.needs)
    return {"deficits": [{"id": d["id"], "kind": d["kind"], "words": say(d), "urgency": d["urgency"], "since": d["since"], **({"needs": needs[d["id"]]} if needs.get(d["id"]) else {})}
                         for d in b["deficits"]],
            "jobs": [{"deficit": j["deficit"], "taker": j["taker"], "words": j["words"], **({"invent": True} if raw.get("invent") else {}), **({"blocked": raw["blocked"]} if raw.get("blocked") else {})}
                     for j, raw in zip(b["jobs"], ((house.get("v5") or {}).get("board") or {}).get("jobs") or [])],   # (SPEC-v5.1 §4.4: an invention, and what it waits on)
            "closed": [{"kind": c["kind"], "words": say(c), "by": c["by"], "tick": c["tick"]} for c in b["closed"]],
            **({"projects": projects.board(house)} if (house.get("v5") or {}).get("projects") else {})}   # SPEC-v5.3 §8 (helper A): projects by state, orphans in words
