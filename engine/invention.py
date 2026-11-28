"""SPEC-v5.1 §4, §7 (helper C): invention. A hob proposes a thing nobody has made (the plan's make aim or a reaction's
`do`, contracts.invent); the parser (grammar.parse, with what is in the house and the hob's tier) accepts it or refuses
it in the world's words. A refusal is a memory tagged with the part and the material, goes into the next packet, and
three of the same invention in a day make the want behind it fade. An accepted one is a job (jobs.py): a gather step
for each part's material and the charge, then a make at the station its tier needs (the bench up to tier 1; the forge,
else the Works, for 2). On making it the house has a new kind (house["invented"][kind], contracts.recipe with the
legacy fields invent.py reads), its maker knows the recipe, it is a first, and its drawn sprite is asked for (§7.2).

Switches: [grammar] on (on51); the sprite call also wants [sprites2] on and tools/sprites/invent.py, else the view's
compositor draws it from its parts, as it does until the sprite lands."""
import hashlib
import json
import subprocess
import sys
import threading
from pathlib import Path

from . import contracts as K
from . import craft, firsts, grammar, items, memories, things
from .world import add_event, label, moment, rnd

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "sprites" / "invent.py"   # Codex's step 5 (§7.2): `invent.py <description> <recipe-hash>`
OWN = ROOT / "view" / "assets" / "own" / "invented"   # where it leaves <hash>/16.png and 24.png (served at /art/own/invented/)
LITTLE = ("egg", "dead", "hatchling", "child")
FADE = 3   # refusals of the same invention in a day before the want fades (§4.3)
LANDED = []   # sprite calls returned, (kind, hash, ok), applied on the engine's thread by `tick`


def on(cfg):
    return K.on51(cfg, "grammar")


def a(word):
    return "an" if str(word)[:1] in "aeiou" else "a"


def listed(xs):
    xs = list(xs)
    return ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else "".join(xs)


def parts_words(parts, charge=None):
    """"a tube of wood and a spring of metal, charged with pebble"."""
    return listed("%s %s of %s" % (a(p["part"]), p["part"], p["material"]) for p in parts) + (", charged with %s" % charge if charge else "")


# ---- §4.1 the grammar in the prompt ----

def line(house, cfg, kind):
    """An example for the grammar: "a lantern: a flame of oil, a shade of glass and a handle of wood (it gives light)"."""
    r = grammar.recipe(house, cfg, kind)
    if not r or not r["parts"] or not r["verbs"]:
        return None
    top = max(r["verbs"], key=r["verbs"].get)
    return "%s %s: %s (%s)" % (cfg["kinds"].get(kind, {}).get("a") or a(kind), kind, parts_words(r["parts"], r["charge"]), K.VERB_WORDS[top])


def examples(house, cfg, pet):
    """API51: up to five example lines for contracts.grammar: the kinds it knows of (pet["knows"] with `of`, which
    reading gives: §6.4) first, then catalog kinds within its reach (tier + 1), a different few each day."""
    reach = grammar.tier(house, cfg, pet) + grammar.TIERS_UP
    of = [k[5:] for k, v in (pet.get("knows") or {}).items() if k.startswith("kind:") and K.knowledge(v)["of"]]
    cat = sorted(k for k in cfg["items5"]["kind"] if k not in of and (grammar.recipe(house, cfg, k) or {}).get("tier", 9) <= reach)
    rnd(house, "examples", pet["id"], house["clock"]["day"]).shuffle(cat)
    out = []
    for k in of + cat:
        x = line(house, cfg, k)
        if x:
            out.append(x)
        if len(out) >= 5:
            break
    return out


def reach_names(house, cfg, pet):
    """(parts, materials) the reply may name: those of the grammar shown (up to its tier + 1)."""
    D, reach = grammar.data(), grammar.tier(house, cfg, pet) + grammar.TIERS_UP
    return sorted(p for p, x in D["part"].items() if x["tier"] <= reach), sorted(m for m, x in D["material"].items() if x["tier"] <= reach)


def text(house, cfg, pet):
    """The grammar block for its packet (contracts.grammar at its tier, with what is to hand and the examples)."""
    return K.grammar(grammar.tier(house, cfg, pet), have=grammar.have(house, cfg), examples=examples(house, cfg, pet))


def may(house, cfg, pet):
    """§4.1 whether the grammar goes into its plan packet: it may make or invent today, by a job's make step, a make aim
    it holds or may choose (its own make for the day not yet made), a want of a kind to make, or a wrong on the board
    that no job can see to (no catalog kind for it). Not a
    little one, not one already inventing, and not after the day's third refusal (its want has faded)."""
    if not on(cfg) or pet["stage"] in LITTLE or pet.get("inventing") or pet.get("invent_off") == house["clock"]["day"]:
        return False
    if any(a_["kind"] == "make" and not a_.get("done") and not a_.get("failed") for a_ in pet.get("aims") or []):
        return True
    from . import wants
    if any(w["what"] in wants.KIND_WANTS for w in pet.get("wants") or []):
        return True
    if not K.on5(cfg, "jobs"):
        return False
    from . import jobs
    if not jobs.made_up(house, cfg, pet):   # (a plan's make aim is the plan's to choose: one with its own make left today may make, so may invent; the lead, at the rehearsal)
        return True
    j = jobs.of(house, pet)
    if j and (jobs.step(j) or {}).get("do") == "make":
        return True
    B = jobs.board(house)
    return any(d["kind"] in jobs.NEEDS and not any(x["deficit"] == d["id"] for x in B["jobs"]) for d in B["deficits"])


def refused_lines(house, cfg, pet):
    """What it was told when it last tried to make something new, today (§4.3: it learns the grammar by being told)."""
    day = house["clock"]["day"]
    seen = [r for r in pet.get("refused51") or [] if r["day"] == day]
    return ["when you tried to make %s %s today: %s" % (a(r["name"]), r["name"], r["words"]) for r in seen[-2:]]


# ---- §4.3 proposing ----

def same_as(house, inv):
    """An invented kind of these very parts and charge, or None (making it again is routine)."""
    key = sorted((p["part"], p["material"]) for p in inv["parts"])
    return next((k for k, v in (house.get("invented") or {}).items() if v.get("draw") is not None
                 and sorted((p["part"], p["material"]) for p in K.parts_of(v.get("parts"))) == key and (v.get("charge") or None) == inv["charge"]), None)


def kind_name(house, cfg, name):
    """The new kind's name, the hob's own made unique (things.unique_name): never a kind's, an invented kind's or a
    pending invention's."""
    from . import jobs
    base = things.clean_name(name) or "thing"
    pending = {(j.get("invent") or {}).get("kind") for j in jobs.board(house)["jobs"]}
    taken = set(cfg["kinds"]) | set(house.get("invented") or {}) | pending
    for n in [base] + ["%s %s" % (w, base) for w in things.OTHER]:
        n = things.unique_name(house, cfg, n)
        if n not in taken:
            return n
    return "%s of day %d" % (base, house["clock"]["day"])


def refuse(house, cfg, pet, inv, words, part=None, material=None):
    """A refusal: a memory with the part and the material as tags, a reaction to it (the grammar shown again), and on
    the day's third refusal of the same invention, the want fades: its want and make aims let go, no grammar today."""
    from . import brain4
    day, key = house["clock"]["day"], (inv["name"] or inv["for"]).lower()
    K.count(house, "refused", words)
    tags = [x for x in (part, material) if x]
    memories.remember(house, cfg, pet, "I thought to make %s %s of %s, but %s" % (a(inv["name"]), inv["name"], parts_words(inv["parts"], inv["charge"]), words), 3, "refused", (), None, tags)
    rs = pet.setdefault("refused51", [])
    rs.append({"tick": house["tick"], "day": day, "name": inv["name"], "key": key, "words": words, "part": part, "material": material, "invent": inv})
    del rs[:-6]
    if sum(r["day"] == day and r["key"] == key for r in rs) >= FADE:
        pet["invent_off"] = day
        pet["wants"] = [w for w in pet.get("wants") or [] if w.get("text") != inv["for"]]
        for x in pet.get("aims") or []:
            if x["kind"] == "make" and not x.get("done"):
                x["failed"] = True
        add_event(house, pet, "you gave up on the %s for today: %s" % (inv["name"], words))
        return
    brain4.notable(house, cfg, pet, "refused", "you thought to make %s %s of %s, but %s" % (a(inv["name"]), inv["name"], parts_words(inv["parts"], inv["charge"]), words))


def propose(house, cfg, pet, inv):
    """API51 §4.3-4.4: (words, ok). Parsed with what is in the house and its tier: refused in words (a memory, the next
    packet, a reaction), or a job it takes at once."""
    inv = K.invent(inv)
    if not on(cfg) or not K.on5(cfg, "jobs") or not inv or pet["stage"] in LITTLE:   # (an invention is a job: none while [jobs] is off)
        return "", False
    K.count(house, "invent", "proposed")
    got = grammar.parse(cfg, inv["parts"], charge=inv["charge"], have=grammar.have(house, cfg), tier=grammar.tier(house, cfg, pet))
    if not got["ok"]:
        refuse(house, cfg, pet, inv, got["words"], got["part"], got["material"])
        return got["words"], False
    j, missing = job(house, cfg, pet, inv, got)
    if j is None:
        words = "there's no %s to be had in the rooms you know" % missing
        refuse(house, cfg, pet, inv, words, None, missing)
        return words, False
    K.count(house, "invent", "accepted")
    return "you set about making the %s: %s" % (j["invent"]["kind"], j["words"]), True


# ---- §4.4 the job ----

def station(house, cfg, pet, tier):
    """(room id, words) where it is made: the forge, else the Works, for tier 2 and up; else the nearest bench; else
    where it stands, by paw."""
    from . import jobs, machine, machines
    if tier >= 2:
        f = machines.built(house, "forge")
        if f and f[0]["id"] in pet["rooms"]:
            return f[0]["id"], "the forge"
        m = machine.found(house)
        if m and m["id"] in pet["rooms"]:
            return m["id"], "the Works"
    benches = [r for r in jobs.known(house, pet) if any(o.get("fix", {}).get("bench") for o in r["objects"].values())]
    if benches:
        return min(benches, key=lambda r: (jobs.hops(house, pet["room"], r["id"]), r["id"]))["id"], "the bench"
    return pet["room"], "by paw"


def job(house, cfg, pet, inv, got):
    """(the invention's job, taken by its inventor, or None and the material it can't come by). Tied to the wrong on
    the board it is for (its words), the job ends with that wrong's use step, so the board closes it."""
    from . import jobs
    again = same_as(house, inv)
    kind = again or kind_name(house, cfg, inv["name"])
    bits = [p["material"] for p in inv["parts"]] + ([inv["charge"]] if inv["charge"] else [])
    lying, sells, steps = jobs.lying(house, pet), jobs.sells(house, cfg), []
    for b in bits:
        if b in lying:
            steps.append({"do": "gather", "what": b, "where": lying[b]})
        elif b in sells:
            steps.append({"do": "buy", "what": b, "where": sells[b]})
        elif b in pet["carrying"]:
            steps.append({"do": "gather", "what": b, "where": None})
        else:
            return None, b
    at, words = station(house, cfg, pet, got["tier"])
    steps.append({"do": "make", "what": kind, "where": at})
    B = jobs.board(house)
    d = next((d for d in B["deficits"] if d["words"] == inv["for"] and (d["kind"] in jobs.NEEDS or d["kind"] == "own_tool")), None)
    old = next((x for x in B["jobs"] if d and x["deficit"] == d["id"]), None)
    if old and old["taker"] not in (None, pet["id"]):
        d = old = None   # (someone else is seeing to it: this one is made for its own sake)
    mine = jobs.of(house, pet)
    if mine:
        jobs.leave(house, pet, mine)
    if old:
        B["jobs"].remove(old)
    if d:
        verb = (jobs.NEEDS.get(d["kind"]) or (("hold",), None))[0][0]
        steps.append({"do": "use", "what": d.get("who") or d.get("name"), "where": jobs.target(house, d), "verb": verb})
        K.count(house, "taken", pet["id"])
        K.count(house, "taken_kind", d["kind"])
    t = house["tick"]
    j = dict(K.job({"id": "invent|%s#%d" % (kind, t), "deficit": d["id"] if d else "invent|%s|%s" % (kind, pet["id"]), "kind": d["kind"] if d else "own_tool",
                    "steps": steps, "since": t, "taker": pet["id"], "state": "taken",
                    "words": "%s, with a new %s" % (d["words"], kind) if d else "the %s, a thing nobody has made" % kind}),
             thing=kind, item=None, at=None, step_at=t,
             invent={"kind": kind, "name": inv["name"], "parts": inv["parts"], "charge": inv["charge"], "how": inv["how"], "for": inv["for"], "tier": got["tier"],
                     "verbs": got["verbs"], "bits": bits, "at": words, "again": bool(again)})
    B["jobs"].append(j)
    pet["inventing"] = kind
    add_event(house, pet, "you set about making the %s: %s" % (kind, parts_words(inv["parts"], inv["charge"])))
    jobs.aim(house, cfg, pet, j)
    return j, None


# ---- the new kind ----

def nature(cfg, bit):
    """A bit's first nature (materials.toml), what the house's v3 making reads."""
    return (cfg["house"]["bits"].get(bit, {}).get("can") or ["hard"])[0]


def as_kind(cfg, rec):
    """An invention as the catalog would have it (invent.as_kind asks, for a record with `draw`): called by its own
    name about the house, of its first part's nature, and no joining."""
    return {"invented": True, "a": rec["a"], "everyday": rec["name"], "not": [], "rank": 2, "wall": False, "hangs": False, "store": rec.get("store", 0),
            "inside": False, "furniture": False, "from": None, "base": rec["parts"][0]["part"], "signature": rec["parts"][-1]["part"],
            "prop": dict(cfg["materials"].get(rec["material"], {})), "effect": {}}


def draw_parts(parts):
    """§7.2 the compositor's parts (parts.toml `draw` names the view's part): the first on nothing, the rest on its top."""
    D = grammar.data()["part"]
    return [{"part": D[p["part"]]["draw"], "at": None if i == 0 else "top", "material": p["material"]} for i, p in enumerate(parts)]


def record(house, cfg, pet, I):
    """house["invented"][kind]: contracts.recipe, and what invent.py's routine making and the view read beside it."""
    kind, ps = I["kind"], I["parts"]
    return dict(K.recipe({"kind": kind, "parts": ps, "charge": I["charge"], "tier": I["tier"], "verbs": I["verbs"], "by": pet["id"], "how": I["how"],
                          "for": I["for"], "tick": house["tick"]}),
                name=kind, a=a(kind), use="curio", draw=draw_parts(ps), props=list(dict.fromkeys(nature(cfg, p["material"]) for p in ps)), material=nature(cfg, ps[0]["material"]),
                size="small", wall=False, hangs=False, store=2 if "hold" in I["verbs"] else 0, sound=None, glow="light" in I["verbs"],
                does="; ".join(K.VERB_WORDS[v] for v in sorted(I["verbs"], key=lambda v: -I["verbs"][v])), **{"from": [ps[0]["part"], ps[-1]["part"]]})


def finish(house, cfg, pet, j):
    """API51 §4.4: its job's make step, at the station: the bits used, the thing made, the new kind kept, known by its
    maker, a first, its sprite asked for. Returns the kind, or None with the job's `why` (what it lacks)."""
    I, room = j["invent"], house["rooms"][pet["room"]]
    kind, left = I["kind"], list(pet["carrying"])
    for b in I["bits"]:
        if b not in left:
            j["why"] = "you haven't the %s for the %s with you" % (b, kind)
            return None
        left.remove(b)
    used, pet["carrying"] = list(I["bits"]), left
    t, new = house["tick"], kind not in (house.get("invented") or {})
    if new:
        rec = house.setdefault("invented", {})[kind] = record(house, cfg, pet, I)
        from . import invent
        cfg["kinds"][kind] = invent.as_kind(cfg, rec)
    rec = house["invented"][kind]
    r = rnd(house, "invention", pet["id"], t)
    recipe = {"kind": kind, "material": rec["material"], "color": r.choice(things.COLORS), "size": 2, "purpose": (I["for"] or I["how"] or "to see what it does")[:80]}
    name, title = things.named(house, cfg, recipe, used, pet, room, I["name"])
    house["n"]["thing"] += 1
    o = {"pos": things.spot_for(house, cfg, pet, None),
         "made": {"id": house["n"]["thing"], "recipe": recipe, "by": pet["id"], "owner": pet["id"], "tick": t, "bits": used, "uses": 0, "ups": 0, "used_at": t,
                  "heirloom": None, "behavior": None, "fine": craft.skill(cfg, pet, "making"), **things.record(house, cfg, pet, room, used, "made %s" % ("at " + I["at"] if I["at"] != "by paw" else "by paw"))}}
    room["objects"][name] = o
    pet["made"] += 1
    pet["last_made"] = {"tick": t, "kind": kind, "material": rec["material"], "new": new}
    pet.setdefault("made_at", []).append([t, "%s|%s" % (kind, rec["material"])])
    pet["make_for"], pet["made_by51"] = "job", "invention" if new else "recipe"
    craft.practise(house, cfg, pet, "making")
    moment(house, "made", "%s made %s%s" % (label(pet), things.a_thing(cfg, recipe), ", which it calls '%s'" % title if title else ""), pet["id"], room["id"])
    if new:
        craft.found(house, pet, "%s invented the %s: %s" % (label(pet), kind, I["how"] or rec["does"]), "invented")
    firsts.made(house, cfg, pet, o, room)
    items.of(house, cfg, o, name, room)
    from . import knowledge
    knowledge.learn(house, cfg, pet, K.key_of(kind), "made")   # (§5.1: it knows the recipe)
    pet.setdefault("recipes", {})["kind:" + kind] = {"tick": t, "from": "found"}   # (v4's, so invent.offered lets it make one again)
    house.setdefault("recipes", {}).setdefault("kind:" + kind, {"by": pet["id"], "tick": t})
    pet.pop("inventing", None)
    K.count(house, "invent", "made")   # (of the accepted, how many were made: The owner's question of the rehearsal)
    add_event(house, pet, "you made the %s: %s" % (kind, rec["does"] or "it does nothing yet"))
    j.update(item=name, at=room["id"], held=True)
    if new:
        sprite(house, cfg, kind)
    return kind


# ---- §7.2 its own sprite ----

def recipe_hash(rec):
    return hashlib.sha1(json.dumps([sorted((p["part"], p["material"]) for p in K.parts_of(rec["parts"])), rec.get("charge")]).encode()).hexdigest()[:12]


def description(rec):
    return "%s %s: %s; %s" % (rec["a"], rec["name"], parts_words(K.parts_of(rec["parts"]), rec.get("charge")), rec.get("how") or rec.get("does") or "")


def sprite(house, cfg, kind):
    """API51 §7.2: its drawn sprite asked of PixelLab (tools/sprites/invent.py, in a thread), or None when [sprites2] is
    off or the script isn't there: then, as until it lands, the compositor draws it from its parts. No hob waits."""
    rec = house["invented"][kind]
    if not K.on51(cfg, "sprites2") or not SCRIPT.exists():
        K.count(house, "sprites", "composited")
        return None
    h = recipe_hash(rec)
    t = threading.Thread(target=call, args=(kind, description(rec), h), daemon=True, name="sprite " + kind)
    t.start()
    return t


def call(kind, desc, h):
    """The script, off the engine's thread: it leaves <hash>/16.png (and 24.png) under OWN and exits 0."""
    try:
        r = subprocess.run([sys.executable, str(SCRIPT), desc, h], cwd=ROOT, capture_output=True, timeout=600)
        ok = r.returncode == 0 and (OWN / h / "16.png").exists()
    except Exception:
        ok = False
    LANDED.append((kind, h, ok))


def tick(house, cfg):
    """The sprites that have landed since, recorded on the engine's thread (the snapshot then sends them: the view swaps)."""
    while LANDED:
        kind, h, ok = LANDED.pop(0)
        rec = (house.get("invented") or {}).get(kind)
        if rec is None:
            continue
        if ok:
            rec["sprite"] = "own/invented/%s" % h
        K.count(house, "sprites", "generated" if ok else "failed")
