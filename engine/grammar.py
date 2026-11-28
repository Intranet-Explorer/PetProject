"""SPEC-v5.1 §1-§3, §9 (helper A): the parser. A thing is its parts (parts.toml, the lead's); `parse` says what it
does, or why it can't be made, in the world's words (contracts.REFUSE). The semantics are parts.toml's header: a
part's verb is live when it has no `needs` for that verb, or one alternative is met by another part on the thing (a
part's name, a material's name or class, or "charge" when the thing has one; an alternative that is a list wants all
of them). A verb's strength is the part's x its material's quality, and the thing's is its strongest part's. Its tier
is the highest of its parts' and materials'; its wear the lowest of its parts' `wear` (a casing halves it).

`recipe` is a kind's parts: the catalog's are kinds.toml's; an invented kind's are its own (a v5.1 invention), else
the old design's design_parts made fit, else its use's (kinds.toml [invented.use]). Switch: [grammar] on (on51)."""
import copy
import functools
from collections import Counter

from . import contracts as K

TIERS_UP = 1   # a hob may make up to its tier + 1 (§5.2)


def data():
    return K.grammar_data()


def a(word):
    return "an" if word[:1] in "aeiou" else "a"


def listed(xs):
    xs = list(xs)
    return ", ".join(xs[:-1]) + " or " + xs[-1] if len(xs) > 1 else "".join(xs)


def part_tier(D, part, mat):
    """A part's tier on a thing: the lower of its own and its material's (21 October 2026): a wooden hinge is
    not a mechanism; a bulb of thin glass is signal."""
    return min(D["part"][part]["tier"], D["material"][mat]["tier"]) if mat in D["material"] else D["part"][part]["tier"]


def made_of(D, part, mat):
    """Can this part be made of this material (by its name or its class)?"""
    p, m = D["part"][part], D["material"].get(mat)
    return bool(m) and (mat in p["materials"] or m["class"] in p["materials"])


def fits(D, names, have=None, most=3):
    """Two or three materials out of names and classes, what's in the house and the lowest tier first."""
    out = []
    for n in names:
        out += [n] if n in D["material"] else [m for m, x in D["material"].items() if x["class"] == n]
    out = list(dict.fromkeys(out))
    out.sort(key=lambda m: (have is not None and m not in have, D["material"][m]["tier"]))
    return out[:most]


def alt_words(D, alt):
    """An alternative of a need in words: "a handle", "glass", "a wire and a cell", "a charge"."""
    w = lambda n: "%s %s" % (a(n), n) if n in D["part"] or n == "charge" else n
    return " and ".join(w(n) for n in alt)


def parse(cfg, parts, charge=None, have=None, tier=None):
    """API51: what a thing of these parts does, or a refusal in words (contracts.parsed). The refusals in order: empty,
    unknown, material, with; then, only for a thing proposed (`have`, `tier` given), absent, tier, and needs when it
    would do nothing at all (the catalog's lens or doll does nothing and is no refusal: a keepsake)."""
    ps = tuple((p["part"], p["material"]) for p in K.parts_of(parts))
    return copy.deepcopy(_parse(ps, bool(charge), None if have is None else tuple(sorted(set(have))), None if tier is None else int(tier)))


@functools.lru_cache(maxsize=4096)   # (an item's verbs are read every tick: the same few recipes)
def _parse(ps, charge, have, tier):
    D = data()
    ps = [{"part": p, "material": m} for p, m in ps]
    no = lambda why, **f: K.parsed({"refusal": why, "words": K.REFUSE[why].format(**f), "part": f.get("part"), "material": f.get("material")})
    if not ps:
        return no("empty")
    for p in ps:
        if p["part"] not in D["part"]:
            return no("unknown", a=a(p["part"]), part=p["part"])
    for p in ps:
        if not made_of(D, p["part"], p["material"]):
            alts = fits(D, D["part"][p["part"]]["materials"], have)
            return no("material", a=a(p["part"]), part=p["part"], material=p["material"] or "nothing", alts=listed(alts))
    for p in ps:
        for other, mats in D["part"][p["part"]]["with"].items():
            for q in ps:
                if q is not p and q["part"] == other and q["material"] not in mats:
                    return no("with", a=a(q["material"]), material=q["material"], part=other, a2=a(p["material"]), other="%s %s" % (p["material"], p["part"]),
                              alts=listed(fits(D, mats, have)))
    if have is not None:
        for p in ps:
            if p["material"] not in have:
                return no("absent", material=p["material"]) if D["material"][p["material"]]["tier"] < 3 else \
                    K.parsed({"refusal": "absent", "words": K.REFUSE["absent"].format(material=p["material"]) + K.MACHINE, "part": p["part"], "material": p["material"]})
    t = max(part_tier(D, p["part"], p["material"]) for p in ps)
    if tier is not None and t > int(tier) + TIERS_UP:
        return no("tier")
    verbs, unmet = {}, []
    for i, p in enumerate(ps):
        P, q = D["part"][p["part"]], D["material"][p["material"]]["quality"]
        others = set()
        for j, x in enumerate(ps):
            if j != i:
                others |= {x["part"], x["material"], D["material"][x["material"]]["class"]}
        if charge:
            others.add("charge")
        for v, s in P["verbs"].items():
            alts = P["needs"].get(v)
            if alts and not any(set(alt) <= others for alt in alts):
                unmet.append({"part": p["part"], "verb": v, "alts": [alt_words(D, alt) for alt in alts]})
                continue
            verbs[v] = max(verbs.get(v, 0), round(s * q, 3))
    if not verbs and unmet and (have is not None or tier is not None):   # (a gate only for a thing proposed: the catalog's lens or doll is a keepsake)
        u = unmet[0]
        return K.parsed({"refusal": "needs", "words": K.REFUSE["needs"].format(a=a(u["part"]), part=u["part"], alts=listed(u["alts"]), verb=u["verb"]),
                         "part": u["part"], "unmet": unmet, "tier": t})
    return K.parsed({"verbs": verbs, "tier": t, "wear": min(D["part"][p["part"]]["wear"] for p in ps), "unmet": unmet})


# ---- a kind's recipe ----

def stand_in(D, cls):
    """A material of a class, for an old design that named a class ("springy" is reed): the lowest tier, first."""
    return min((m for m, x in D["material"].items() if x["class"] == cls), key=lambda m: D["material"][m]["tier"], default=None)


def real(D, ps):
    return bool(ps) and all(p["part"] in D["part"] and made_of(D, p["part"], p["material"]) for p in ps)


def fitted(D, ps):
    """An old design's parts made to fit the grammar: parts it has not are left out, a class is a material of it, a
    material the part can't be made of is the part's first (as design.plan did with a stuff that would not do)."""
    out = []
    for p in K.parts_of(ps):
        if p["part"] not in D["part"]:
            continue
        m = p["material"] if p["material"] in D["material"] else stand_in(D, p["material"])
        if not m or not made_of(D, p["part"], m):
            m = fits(D, D["part"][p["part"]]["materials"], most=1)[0]
        out.append({"part": p["part"], "material": m})
    return out


def kind_parts(house, cfg, kind):
    """(parts, charge material or None, where from: "catalog", "invented", "design", "use" or None) of a kind."""
    D, T = data(), cfg["items5"]
    e = T["kind"].get(kind)
    if e:
        ch = next(iter(e.get("charge") or {}), None)
        return K.parts_of(e.get("parts")), T["charge"][ch]["from"][0] if ch else None, "catalog"
    inv = (house.get("invented") or {}).get(kind)
    if not inv:
        return [], None, None
    own = K.parts_of(inv.get("parts"))
    if real(D, own):
        ch = str(inv.get("charge") or "").lower()
        return own, ch if ch in D["material"] else None, "invented"
    old = fitted(D, inv.get("design_parts"))
    if old:
        return old, None, "design"
    return K.parts_of(T["invented"]["use"].get(inv.get("use"), {}).get("parts")), None, "use"


def recipe(house, cfg, kind):
    """API51: a catalog kind's or an invented one's recipe (contracts.recipe), its verbs and tier the parser's; None
    for a kind that is neither."""
    ps, ch, frm = kind_parts(house, cfg, kind)
    if frm is None:
        return None
    got = parse(cfg, ps, charge=ch) if ps else K.parsed({})
    inv = (house.get("invented") or {}).get(kind) or {}
    return K.recipe(dict({k: inv.get(k) for k in ("by", "how", "for", "tick", "sprite")}, kind=kind, parts=ps, charge=ch, tier=got["tier"], verbs=got["verbs"]))


# ---- tiers and what's to hand ----

def key_tier(house, cfg, key):
    """API51: what knowing a recipe key reaches (21 October 2026): a kind's highest part's tier (`part_tier`: the
    lower of the part's and its material's: a knife of metal is a blade on a handle, tier 1); a process recipe
    ("<bit>|<how>") reaches nothing. So a house climbs by the things it knows how to put together, not by what it can work."""
    key = str(key or "")
    if not key.startswith("kind:"):
        return 0
    D = data()
    return max((part_tier(D, p["part"], p["material"]) for p in kind_parts(house, cfg, key[5:])[0] if p["part"] in D["part"]), default=0)


def tier(house, cfg, pet):
    """API51: the highest tier it knows (pet["knows"], knowing-of left out)."""
    return max((key_tier(house, cfg, k) for k, v in (pet.get("knows") or {}).items() if not K.knowledge(v)["of"]), default=0)


def house_tier(house, cfg):
    """API51: the highest tier among the living."""
    return max((tier(house, cfg, p) for p in house["pets"].values() if p["stage"] not in ("egg", "dead")), default=0)


def have(house, cfg):
    """API51: the materials in the house now: the rooms' bits, what the machine has in it, what hobs carry."""
    out = Counter()
    for r in house["rooms"].values():
        if r["type"]:
            out.update(s["bit"] for s in r["spots"] if s.get("ready", True))
    out.update(m for m, n in ((house.get("machine") or {}).get("stock") or {}).items() if n > 0)
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead"):
            out.update(p.get("carrying") or [])
    return sorted(m for m in out if m in data()["material"])


# ---- §9 the migration's parts half ----

def migrate(house, cfg):
    """API51 §9, once a house (house["migrated"]["v51_parts"]): every item its parts and its verbs re-parsed; the
    duds' kinds (house["design_kinds"]) deleted, those with a thing still standing kept as invented kinds of the old
    design's parts, so nothing a hob owns vanishes. Returns the report's lines: parts coverage, every kind whose verbs
    move more than 0.2 from v5.0's (verb by verb, for the owner), and how many items changed verbs."""
    done = house.setdefault("migrated", {})
    if done.get("v51_parts") or not K.on51(cfg, "grammar"):
        return []
    from . import items, things
    T = cfg["items5"]
    rooms = [r for r in house["rooms"].values() if r["type"]]
    standing = {o["made"]["recipe"].get("kind") for r in rooms for o in things.made(r).values()}
    duds, kept = house.pop("design_kinds", None) or {}, []
    inv = house.setdefault("invented", {})
    for k, rec in duds.items():
        if k in standing and k not in inv:
            inv[k] = dict(rec, store=0, wall=False, hangs=False, props=[], material=None, does="", sound=None, glow=False)
            kept.append(k)
    if kept:
        from . import invent
        invent.install(house, cfg)
    held = 0
    for p in house["pets"].values():   # (a design in hand, and its wants, go with designing: §4.5)
        held += bool(p.get("design"))
        p["design"] = None
        p["wants"] = [w for w in p.get("wants") or [] if w.get("what") != "design"]
    off = lambda new, old: {v: (round(old.get(v, 0), 2), round(new.get(v, 0), 2)) for v in sorted(set(new) | set(old)) if abs(new.get(v, 0) - old.get(v, 0)) > 0.2 + 1e-9}
    say = lambda d: ", ".join("%s %s->%s" % (v, a, b) for v, (a, b) in d.items())
    cat = [k for k in T["kind"] if (recipe(house, cfg, k) or {}).get("parts")]
    lines = ["parts: %d of %d catalog kinds have a recipe%s" % (len(cat), len(T["kind"]), "" if len(cat) == len(T["kind"]) else " (none: %s)" % ", ".join(k for k in T["kind"] if k not in cat))]
    frm = Counter(kind_parts(house, cfg, k)[2] for k in inv)
    lines.append("parts: %d of %d invented kinds have parts (their own %d, the old design's %d, their use's %d)%s"
                 % (sum(1 for k in inv if (recipe(house, cfg, k) or {}).get("parts")), len(inv), frm["invented"], frm["design"], frm["use"],
                    "; %d of the duds' kinds kept, as a thing of each still stands: %s" % (len(kept), ", ".join(kept)) if kept else ""))
    lines.append("design kinds deleted: %d (the duds of v3.6d); designs in hand let go: %d; the house's designs kept as history: %d" % (len(duds) - len(kept), held, len(house.get("designs") or [])))
    v50 = dict(cfg, grammar=dict(cfg.get("grammar") or {}, on=False))   # (v5.0's verbs, as items gave them with [grammar] off)
    moved = []
    for k, e in T["kind"].items():
        d = off(recipe(house, cfg, k)["verbs"], e.get("verbs") or {})
        if d:
            moved.append("  catalog %s: %s%s" % (k, say(d), " (new or gone on purpose: %s)" % ", ".join(e.get("new", []) + e.get("gone", [])) if e.get("new") or e.get("gone") else ""))
    for k in sorted(inv):
        d = off(recipe(house, cfg, k)["verbs"], items.table(house, v50, k)[0])
        if d:
            moved.append("  invented %s (%s): %s" % (k, kind_parts(house, cfg, k)[2], say(d)))
    lines.append("kinds whose verbs move more than 0.2 from v5.0's: %d" % len(moved))
    lines += moved
    changed = n = 0
    for r in rooms:
        for name, o in r["objects"].items():
            was = items.entry(house, v50, o, name)
            it = items.of(house, cfg, o, name, r)
            if it:
                n += 1
                changed += bool(was and it["verbs"] != was[0])
    for k in inv:
        inv[k]["verbs"] = recipe(house, cfg, k)["verbs"]
    lines.append("items given parts and their verbs re-parsed: %d; of them %d changed verbs" % (n, changed))
    done["v51_parts"] = house["tick"]
    return lines
