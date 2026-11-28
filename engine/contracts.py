"""SPEC-v4.2 §0.1: the shapes more than one module reads, owned here and nowhere else (the lead's).

Every bug v4.0 shipped was a contract between two helpers' modules that nobody owned. So: a record another module
reads is made by a function here (each takes what it is given, keeps what is known, and fills the rest with defaults,
so an old save or a short reply is never a crash); every closed list is a tuple here, and check_contracts.py proves
each table that consumes a list covers every name; the reply schemas' new fields are built here and defaulted here.

    who writes             what                         who reads
    B memories.remember    memory()                     C talk's subject, D the director, E the Lab
    B hooks.parse, A, D    hook(), belief_extra()        B planner, A hatch (inherited), D teach and tales, E the Mind page
    D stage.choose         happening()                  A health (bad food, cold snap), E banners, B packets
    D story.tale           tale()                       D tell, E the family page
    C drives.draw          drive() flaw() voice() secret()   B packets and the self-page, D the director, E the card
    B self.write           self_page()                  every packet, E the card, A the life record
    B reflect              REFLECT fields               B self-page, D theory, C drive change, E the card
    C talk                 TALK fields (wants/holds/knows)   B memories, E bubbles

None of the numbers here reach a hob: everything it is told is in words (SPEC-v3 §8).
"""
import re
from pathlib import Path

# ---- the switches (§0): [spirit] on turns the whole release off; each part has its own ----

PARTS = ("lives", "deaths", "memory2", "selfpage", "hooks", "drives", "talk2", "stage", "visitor5")


def on(cfg, part=None):
    """Is this part of v4.2 on? Off at [spirit] means every part is off (v4.0.6's behaviour). The one gate: every
    module asks here, never cfg[part] directly, so [spirit] off reaches all of them."""
    s = cfg.get("spirit") or {}
    if not s.get("on"):
        return False
    return part is None or bool((cfg.get(part) or {}).get("on"))


# ---- closed lists (§0.1 item 2: check_contracts.py asserts every consumer covers every name) ----

STAGES = ("egg", "hatchling", "child", "youngling", "adult", "elder")

# §5.1 belief hooks. The argument each takes, in words, for the schema's description and hooks.parse.
HOOKS = ("avoid_place", "avoid_thing", "prefer_thing", "trust", "watch", "do_at", "make", "never")
HOOK_ARG = {"avoid_place": "room", "avoid_thing": "kind|material|catch", "prefer_thing": "kind|material", "trust": "hob",
            "watch": "hob", "do_at": "activity", "make": "kind", "never": "activity"}

# §2 the causes of death. key -> the stone's words when nothing more is known (life.die writes the full words).
DEATHS = {"old age": "died of old age", "sickness": "died of a sickness", "injury": "died of a hurt that was not tended",
          "bad food": "died of bad food", "killing": "was killed", "manslaughter": "died of a fall", "exposure": "died of the cold",
          "starvation": "died of hunger", "neglect": "wasted away"}
CAUSES = tuple(DEATHS)
# v4.0.6's cause strings, to their keys (the stones already in the house)
OLD_CAUSE = {"violence": "killing", "starvation": "starvation", "neglect": "neglect", "old age": "old age", "sickness": "sickness"}

# §2.2 sickness, mildest first. v4.0.6 called them unwell, sick, very sick (OLD_SICK, for the migration).
SICK = ("unwell", "ill", "gravely ill")
OLD_SICK = {"unwell": "unwell", "sick": "ill", "very sick": "gravely ill"}

# §8.2 the director's menu. hard: never two hard ones in a row (§8.3).
HAPPENINGS = {"storm": True, "buried": False, "stranger_egg": False, "bad_food": True, "missing": True, "cold_snap": True,
              "heat_wave": True, "leak": True, "power_cut": True, "letter": False, "dream": False, "train": False,
              "creature": False, "visitor_gone": False, "nothing": False}

# §6 character
DRIVES = ("to be remembered", "to be loved by one", "to find out what the visitor is", "to make the thing nobody has made",
          "to keep the family safe", "to leave the house", "to know everything in the book", "to be left alone")
FLAWS = ("proud", "envious", "fearful", "greedy", "lazy", "hot", "dishonest", "clinging")
# SPEC-v4.2.2 §2: the eight ways a hob talks, each with the one line a packet says it in (drawn from the traits, never by the model)
STYLES = {"sunny": "cheerful, quick to be pleased, says so; asks how you are and means it",
          "grumbly": "complains first, helps anyway; short with everyone, soft with the little ones",
          "easygoing": "slow, unbothered, a bit lazy; says \"later\" and means tomorrow",
          "fussy": "particular about how things are done and where they go; notices crumbs",
          "big-sister": "bossy, protective, blunt; tells you what you should have done",
          "eager": "always in the middle of something, wants you to come and see",
          "know-it-all": "explains things nobody asked about; usually right, which is worse",
          "gentle": "quiet, listens, asks the second question; remembers what you said"}
SECRETS = ("lie", "broken", "fall", "feeling", "taken")

# §4.4 the self-page's five lines, in order
SELF = ("who I am", "what I am for", "what I have lost", "what I fear", "what I owe or am owed")
SELF_MOST = 320   # a line's characters at most (v4.2.3: 200 cut the plain pages mid-sentence)

# Aim kinds: v4.0's (planner.AIM) and v4.2's. planner.AIM must cover every one (check_contracts).
AIMS_V4 = ("make", "build", "design", "fish", "cook", "tend", "gather", "explore", "learn", "be with", "help", "rest", "play",
           "vigil", "plan", "give")
AIMS_NEW = ("ask", "nurse", "tell", "try", "lay")   # §1.3: a child asks, an adult nurses and raises, an elder tells; §2.2 a youngling tries
AIM_KINDS = AIMS_V4 + AIMS_NEW
AIM_FROM = ("plan", "react", "talk", "visitor", "drive", "taught", "answer", "note", "question")   # where an aim came from (§5.3-5.6; v5.1 §6.3: a question from life)

# §9.4: the visitor's tools, v4.0's and the two new ones; SPEC-v5.3.2 §1: place and remove (a room and a tile, not a hob)
VISITOR_TOOLS = ("talk", "answer", "teach", "praise", "scold", "give", "suggest", "stepin", "tend", "remedy", "place", "remove")

# moments v4.2 adds that the view puts in a banner (view/src/banner.ts SPIRIT) and the chronicle tells
MOMENTS = ("happening", "secret found", "gravely ill", "poisoned", "belief acted", "tale", "taught first", "visitor back")

# memory kinds the model writes (§4.1); a memory's "by" is set by its writer (memories.remember), never guessed from its kind
MODEL_KINDS = ("react", "talk", "reflect", "knows", "subtext", "flaw")


# ---- records ----

def _s(x, most=240):
    return re.sub(r"\s+", " ", str(x or "")).strip()[:most]


def _ids(xs):
    return [str(x) for x in (xs or []) if x]


def memory(d, tick=0):
    """§4.1 a memory: {"text", "tick", "weight" 1-5, "about": [hob ids, "visitor"], "where": room id or None, "what":
    [kinds, things, materials, catches], "kind", "by": "model"|"engine"}. ("about" is the spec's "who": every v4.0
    reader already reads "about".)"""
    d = d if isinstance(d, dict) else {"text": d}
    kind = _s(d.get("kind"), 40)
    return {"text": _s(d.get("text"), 240), "tick": int(d.get("tick", tick) or 0), "weight": max(1, min(5, int(d.get("weight", 1) or 1))),
            "about": _ids(d.get("about") or d.get("who")), "where": d.get("where") or None, "what": [_s(w, 40).lower() for w in d.get("what") or [] if w],
            "kind": kind, "by": "model" if d.get("by") == "model" else "engine",   # (the writer says; an old memory is the engine's)
            **({"from": d["from"]} if "from" in d else {})}


def hook(d):
    """§5.1 a belief's hook: {"name": one of HOOKS, "arg": str, "when": hour words or ""}, or None. The model's "none"
    (the schema has no null) and anything not on the list are None."""
    if not isinstance(d, dict) or d.get("name") not in HOOKS:
        return None
    arg = _s(d.get("arg"), 60)
    if not arg:
        return None
    return {"name": d["name"], "arg": arg, "when": _s(d.get("when"), 30) if d["name"] == "do_at" else ""}


def belief_extra(b):
    """§5.1-5.4 what a belief carries beside its statement (beliefs.json, memory.Memory): its hook, the truth when the
    engine set it (True/False) or None for the model's, doubted (§5.4), tested (times acted against with nothing
    happening, §5.2), acted (the tick it was first acted on, or None). Fills the keys in place; returns b."""
    b["hook"] = hook(b.get("hook"))
    b.setdefault("truth", None)
    b.setdefault("doubted", False)
    b.setdefault("tested", 0)
    b.setdefault("acted", None)
    return b


def happening(d, day=0):
    """§8 the director's choice for a day: {"name", "target": a hob or room id or None, "why": one plain sentence (v4.2.2),
    "day", "hard"}."""
    d = d if isinstance(d, dict) else {}
    name = d.get("name") if d.get("name") in HAPPENINGS else "nothing"
    return {"name": name, "target": d.get("target") or None, "why": _s(d.get("why"), 200), "day": int(d.get("day", day) or 0), "hard": HAPPENINGS[name]}


def tale(d):
    """§10.3 a tale: {"id", "family", "about": the dead hob's id, "name", "cause" (a key of DEATHS), "words": the cause in
    words, "last_words", "self_line", "hook" or None, "tick", "told": [hob ids who have heard it]}."""
    d = d if isinstance(d, dict) else {}
    cause = d.get("cause") if d.get("cause") in DEATHS else "old age"
    return {"id": _s(d.get("id"), 40), "family": d.get("family"), "about": d.get("about"), "name": _s(d.get("name"), 40), "cause": cause,
            "words": _s(d.get("words") or DEATHS[cause], 160), "last_words": _s(d.get("last_words"), 400), "self_line": _s(d.get("self_line"), 200),
            "hook": hook(d.get("hook")), "tick": int(d.get("tick", 0) or 0), "told": _ids(d.get("told"))}


def drive(d):
    """§6.1 {"name": one of DRIVES, "target": a hob id (to be loved by one) or None, "since": tick, "changed": bool (a drive changes once)}."""
    d = d if isinstance(d, dict) else {"name": d}
    return {"name": d.get("name") if d.get("name") in DRIVES else DRIVES[0], "target": d.get("target") or None,
            "since": int(d.get("since", 0) or 0), "changed": bool(d.get("changed"))}


def flaw(d):
    """§6.2 {"name": one of FLAWS, "asked": the day the reflection last asked about it}."""
    d = d if isinstance(d, dict) else {"name": d}
    return {"name": d.get("name") if d.get("name") in FLAWS else FLAWS[0], "asked": int(d.get("asked", -99) or -99)}


def voice(d):
    """SPEC-v4.2.2 §2 the voice card: {"style": one of STYLES or None, "cares": one thing, in plain words}. (v4.2's
    register, returns_to, overuses and samples are gone: an old card, a dead hob's, has no style.)"""
    d = d if isinstance(d, dict) else {}
    return {"style": d.get("style") if d.get("style") in STYLES else None, "cares": _s(d.get("cares"), 60)}


def voice_line(v):
    """The voice card in one line, for a packet and the card ("" for an old card)."""
    v = voice(v)
    return "; ".join(([STYLES[v["style"]]] if v["style"] else []) + (["cares about %s" % v["cares"]] if v["cares"] else []))


def secret(d):
    """§6.3 {"kind": one of SECRETS, "text": in the hob's own words, "about": a hob id or None, "tick", "found": tick or None}."""
    d = d if isinstance(d, dict) else {}
    return {"kind": d.get("kind") if d.get("kind") in SECRETS else "lie", "text": _s(d.get("text"), 200), "about": d.get("about") or None,
            "tick": int(d.get("tick", 0) or 0), "found": d.get("found")}


def self_page(d):
    """§4.4 the self-page: the five lines of SELF, in order, as a dict. A list of five is taken in order."""
    if isinstance(d, list):
        d = dict(zip(SELF, d))
    d = d if isinstance(d, dict) else {}
    return {k: _s(d.get(k), SELF_MOST) for k in SELF}


def self_lines(page):
    page = self_page(page)
    return ["%s: %s" % (k, page[k]) for k in SELF if page[k]]


# ---- the house's ledger of v4.2 doings, for the Lab (§11.5) and the checks: house["spirit"][what] = [{"tick", ...}] ----
# missed: a reply lacked a new field {"pet", "kind", "fields"}; acted: a belief's hook moved a choice {"pet", "belief", "hook"};
# told: a tale told {"by", "to": [ids], "tale"}; knows: a talk left its lines {"a", "b", "n"}; refusal: a failure said in
# the world's terms {"pet", "text"}; secret found {"pet", "by"}; happening {"name", "target"}; nursed {"pet", "by", "how"};
# (v4.2.2 §6) monologue: a talk whose lines didn't answer each other {"a", "b", "pairs"}; purple: one that read like a novel {"a", "b", "why"}.
LEDGER = ("missed", "acted", "told", "knows", "refusal", "secret found", "happening", "nursed", "monologue", "purple")
LEDGER_KEEP = 400


def note(house, what, **rec):
    """One line in the ledger (the newest LEDGER_KEEP of each kind are kept)."""
    assert what in LEDGER, what
    rows = house.setdefault("spirit", {}).setdefault(what, [])
    rows.append(dict(rec, tick=house["tick"]))
    del rows[:-LEDGER_KEEP]


def since(house, what, tick):
    return [r for r in (house.get("spirit") or {}).get(what, []) if r["tick"] >= tick]


# Seams across a wave: a part that wants another part to act leaves it a line here, and the other part takes it up
# (so neither imports the other). beliefs_due: B's hooks.tick turns each into a belief with its hook (§2 "remembered",
# §5.1: whoever saw a poisoning or a fall). secret_due: C's drives turns it into the hob's secret if it has none (§2.5,
# §6.3). Each is a list on the pet; the taker pops what it has taken.
def believe_later(pet, text, hook_=None, source="seen", truth=None):
    pet.setdefault("beliefs_due", []).append({"text": _s(text, 200), "hook": hook(hook_), "source": _s(source, 60) or "seen", "truth": truth})
    del pet["beliefs_due"][:-6]


def secret_later(pet, kind, text, about=None, tick=0):
    pet.setdefault("secret_due", []).append(secret({"kind": kind, "text": text, "about": about, "tick": tick}))
    del pet["secret_due"][:-3]


# A talk's record (talk.py's, in house["talks"] / talk.recent) gains "subject" (words) and "minds": {name: {"wants",
# "holds", "knows", "remember"}} (§7.2-7.4): talk_minds() reads it from any record, old or new.
def talk_minds(rec):
    m = (rec or {}).get("minds")
    return {n: {k: _s((v or {}).get(k), 200) for k in ("wants", "holds", "knows", "remember")} for n, v in m.items()} if isinstance(m, dict) else {}


# ---- the reply schemas' new fields (§0.1 items 1, 5) ----

def _text(most, least=0):
    return {"type": "string", "minLength": least, "maxLength": most}


def _obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


HOOK_SCHEMA = _obj(name={"enum": list(HOOKS) + ["none"]}, arg=_text(60), when=_text(30))


def react_fields():
    """react gains `remember`: one line it keeps from this, in its own words (may be empty)."""
    return {"remember": _text(200)}


def talk_fields(names):
    """talk gains, for each speaker (by the name the reply uses): `wants` (from this talk), `holds` (what it will not
    say), `knows` (what it now knows about the other: a fact, a feeling, a secret suspected, a promise), and
    `remember` (one line it keeps). §7.2, §4.3, §4.1."""
    side = _obj(wants=_text(160, 1), holds=_text(160, 1), knows=_text(200, 1), remember=_text(200))
    return {"minds": _obj(**{n: side for n in names})}


def reflect_fields(flaw_asked=False, old=False):
    """reflect gains `remember` (up to three lines), `learned` with its hook, `self` (the five lines), `visitor` (its
    theory, may be unchanged), and on some nights `flaw` and, for an old hob, `leave`. §10.2."""
    f = {"remember": {"type": "array", "items": _text(200, 1), "maxItems": 3},
         "learned": _obj(text=_text(200), hook=HOOK_SCHEMA),
         "self": _obj(**{k.replace(" ", "_"): _text(SELF_MOST, 1) for k in SELF}),
         "visitor": _text(200, 1)}
    if flaw_asked:
        f["flaw"] = _text(240, 1)
    if old:
        f["leave"] = _obj(what=_text(160, 1), to=_text(60, 1), last_words=_text(300, 1))
    return f


def plan_fields():
    """plan gains nothing but room to think: its aims' kinds now include AIMS_NEW (planner.feasible offers them by stage)."""
    return {}


FIELDS = {"plan": plan_fields, "react": react_fields, "talk": talk_fields, "reflect": reflect_fields}


def add_fields(schema, fields):
    """The new fields put into a reply's schema: required, so the model cannot leave them out (§0.1 item 5)."""
    schema["properties"].update(fields)
    schema["required"] = list(dict.fromkeys(list(schema.get("required", [])) + list(fields)))
    return schema


def defaults(kind, reply, names=(), old_self=None, old_theory=""):
    """A reply's new fields, defaulted where it lacks them: the thought goes on (§0.1 item 5). Returns (reply, the
    fields that were missing), for the Lab's count. `names`: talk's speakers. Never raises on a reply of any shape."""
    if not isinstance(reply, dict):
        return reply, []
    missed = []

    def need(k, default, ok=lambda v: True):
        if k not in reply or not ok(reply[k]):
            missed.append(k)
            reply[k] = default

    if kind == "react":
        need("remember", "", lambda v: isinstance(v, str))
    elif kind == "reflect":
        need("remember", [], lambda v: isinstance(v, list))
        reply["remember"] = [_s(x, 200) for x in reply["remember"] if isinstance(x, str) and _s(x)][:3]
        l = reply.get("learned")
        if isinstance(l, str):   # (v4.0.6's shape: a sentence, no hook)
            reply["learned"] = {"text": l, "hook": None}
        else:
            need("learned", {"text": "", "hook": None}, lambda v: isinstance(v, dict))
            reply["learned"] = {"text": _s(reply["learned"].get("text"), 200), "hook": hook(reply["learned"].get("hook"))}
        s = reply.get("self")
        if isinstance(s, dict):
            s = {k: s.get(k, s.get(k.replace(" ", "_"))) for k in SELF}
        page = self_page(s) if isinstance(s, (dict, list)) else None
        if not page or not any(page.values()):
            missed.append("self")
            page = self_page(old_self)
        else:   # a line it left empty stays as it was
            old = self_page(old_self)
            page = {k: page[k] or old[k] for k in SELF}
        reply["self"] = page
        need("visitor", old_theory, lambda v: isinstance(v, str) and _s(v))
    elif kind == "talk":
        m = reply.get("minds") if isinstance(reply.get("minds"), dict) else {}
        out = {}
        for n in names:
            side = m.get(n) if isinstance(m.get(n), dict) else {}
            for k in ("wants", "holds", "knows"):
                if not _s(side.get(k)):
                    missed.append("%s.%s" % (n, k))
            out[n] = {k: _s(side.get(k), 200) for k in ("wants", "holds", "knows", "remember")}
        reply["minds"] = out
    return reply, missed


# ---- the model's budget (§3, the lead's): which kinds think, with how much room, how warm ----

def thinking(cfg, kind):
    """(think, max_tokens, temperature) for a kind of thought; think is False or the reasoning effort ("low", "medium"). With [spirit] off: v4.0.6's (thinking only at night,
    700 tokens, 0.7; talk 0.8)."""
    M = cfg["model"]
    if not on(cfg):
        return (kind in ("reflect", "night"), M["night_tokens"] if kind in ("reflect", "night") else (cfg["talk"]["max_tokens"] if kind == "talk" else None),
                0.8 if kind == "talk" else 0.7)
    S = cfg["spirit"]
    effort = S["think_effort"].get(kind)
    return effort or False, S["think_tokens"].get(kind, M["max_tokens"]) if effort else M["max_tokens"], S["temperature"].get(kind, 0.7)


# ---- the API each helper's module exposes to the others (check_contracts: present once that helper is merged) ----
# module -> {function: what it does}. A seam is a call across this table, nowhere else.
API = {
    "A": {"engine.life": {"grieve": "an elder loses grief_days of span when a close bond or child dies (§1.2)",
                          "cause_words": "a death's cause in words for the stone and the record (§2.7)",
                          "floor": "True while fewer than [deaths] floor hobs are alive (§2): no death but of age"},
          "engine.health": {"sicken": "(house, cfg, pet, frm, level=None): it falls ill, or worse (§2.2)",
                            "tend": "(house, cfg, pet, by, how): a day's tending: a hob's nurse, the visitor's tend, a remedy (§2.2, §9.4)",
                            "stage_of": "(pet) -> one of SICK or None",
                            "spoil": "(house, cfg, room=None, early=False): food on shelves past spoil_days spoils; the director's bad_food spoils a shelf early (§2.4, §8.2)",
                            "patients": "(house, cfg, pet) -> [(sick or hurt hob, how much it needs tending 0..1)] in reach of this hob, for the planner's nurse (§2.2)",
                            "cold_snap": "(house, cfg, days): the season's cold, early (§8.2)"}},
    "B": {"engine.memories": {"remember": "(house, cfg, pet, text, weight, kind, about=(), where=None, what=()) -> memory(): a line, tagged (§4.1)",
                              "tag": "(house, text) -> (about, where, what): the names in a line (§4.1)",
                              "relevant": "(house, cfg, pet, about=(), where=None, what=(), kind=None, n=5, only=False) (§4.2)",
                              "shared": "(house, cfg, a, b, n=1) -> memories both hold (§7.3)"},
          "engine.hooks": {"parse": "(house, text) -> hook() or None, no model call (§5.3, §5.6)",
                           "believe": "(eng, pet, text, hook, source, truth=None) -> belief id: a belief with its hook (§5.1)",
                           "score": "(house, cfg, pet, activity, target) -> the planner's score from its hooks (§5.1)",
                           "aim_from": "(house, cfg, pet, text, why, frm) -> an aim parsed from words (§5.6, §9.3)"},
          "engine.self": {"write": "(house, cfg, pet, page): the self-page set (§4.4)",
                          "engine_page": "(house, cfg, pet) -> the page the engine writes for a little one (§4.4)"}},
    "C": {"engine.drives": {"draw": "(house, cfg, pet): drive, flaw and (with the model) a voice at hatching (§6)",
                            "score": "(house, cfg, pet, activity) -> the planner's score from its drive and flaw (§6.1, 6.2)",
                            "line": "(pet) -> drive and flaw in one line, for a packet (§4.5)",
                            "keep_secret": "(house, cfg, pet, kind, text, about=None): a secret, if it has none (§6.3)",
                            "found": "(house, cfg, pet, by, how='in talk'): its secret found out, by a hob or 'visitor' (D's question): a moment and the ledger (§6.3)",
                            "migrate": "async (eng) -> [report lines]: every living hob's drive, flaw, voice and secret, once a house (§6.5)"}},
    "D": {"engine.stage": {"choose": "(eng) -> happening(): the director's one call, at midnight (§8)",
                           "today": "(house) -> today's happening() or None"},
          "engine.story": {"tale": "(house, cfg, dead) -> tale(): written at a death (§10.3)"},
          "engine.visitor": {"theory": "(house, pet) -> its theory of the visitor (§9.1)"}},
    "E": {"engine.lab4": {"spirit": "(eng) -> the Lab's Spirit section (§11.5)"}},
}
BUILT = {"A", "B", "C", "D", "E"}   # the helpers merged so far; the lead adds each at its merge


# ==== SPEC-v5.0: items, deficits, jobs (the lead's; helpers A items, B deficits and jobs, C the view and the Lab) ====
# A record another helper reads is made here; a closed list is a tuple here; check_contracts proves every consumer
# covers it. `[v5] on` gates the phase; each part has its own switch, read only through on5 (off: v4.2.2's behaviour).
#
#    who writes            what                      who reads
#    A items, A migrate    item()                    B detectors and jobs, C cards, the page
#    A verbs               (words, fx, key)          the mind and the body, as things.use was
#    B deficits.scan       deficit(), board()        B jobs and packets, C the board and the Lab
#    B jobs                job()                     B planner, C the board and the Lab
#    A, B                  count()                   C the Lab's Jobs section

PARTS5 = ("items", "deficits", "jobs", "trade")


def on5(cfg, part=None):
    """Is this part of v5.0 on? `[v5]` off is every part off (v4.2.2's behaviour). The one gate."""
    if not (cfg.get("v5") or {}).get("on"):
        return False
    return part is None or bool((cfg.get(part) or {}).get("on"))


# §1.2 the sixteen verbs (V5-DESIGN §2). REACHABLE: the ones the current kinds give; launch and bind wait for v5.1's parts.
VERBS = ("hold", "carry", "cover", "light", "heat", "pour", "cut", "strike", "dig", "catch", "mend", "grow", "signal", "move", "launch", "bind")
REACHABLE = VERBS   # (v5.0: VERBS[:14]; v5.1's parts give launch and bind)
# what a verb is, said on an item's card (§5): "it keeps rain off; it holds things"
VERB_WORDS = {"hold": "it holds things", "carry": "it carries a load", "cover": "it covers and keeps warm", "light": "it gives light",
              "heat": "it gives heat", "pour": "it pours", "cut": "it cuts", "strike": "it knocks things in", "dig": "it digs",
              "catch": "it catches things", "mend": "it mends things", "grow": "things grow in it", "signal": "it calls the house",
              "move": "it moves things", "launch": "it throws things", "bind": "it ties things"}
# §1.3 an item's class: how fast it wears ([items] wear) and what the class means (cool: food in it spoils at half
# speed; store: the mouse can't get in; keepsake: no verbs; food: eaten; fixture: the house's own)
CLASSES = ("soft", "tool", "glass", "cool", "store", "plain", "keepsake", "food", "fixture")
CHARGES = ("oil", "wax", "bait", "fuel", "shot")   # §1.6 what runs out (kinds.toml [charge] says what refills each); shot: a launcher's (v5.1)
# §1.3 the `use` an invented kind can have (invent.py's), each given verbs by kinds.toml [invented.use]
INVENTED_USES = ("carried light", "soft light", "keeper", "seat or bed", "chime", "instrument", "planter", "digger", "reacher",
                 "rolling toy", "curio", "keepsake", "design")
WHERE = ("room", "in", "held", "site")     # an item is in a room at a tile, in a container, held by a hob, or on a site


def item(d):
    """§1.1 an item: {"id", "kind", "parts": [{"part", "material", "at"}], "verbs": {verb: 0..1}, "tier": 0-4 (v5.1), "class",
    "state": {"wear" 0..1, "broken", "charge": {material: n}, "holds": [ids], "on", "lit"}, "owner", "maker", "made"
    (tick), "quality" 0..1, "name", "heirloom", "star", "where": {"room", "pos"} | {"in": id} | {"held": hob} |
    {"site": project}}. A bit stack is an item with "material" and "n" and no parts."""
    d = d if isinstance(d, dict) else {}
    s = d.get("state") if isinstance(d.get("state"), dict) else {}
    w = d.get("where") if isinstance(d.get("where"), dict) else {}
    where = next(({k: w[k]} for k in ("in", "held", "site") if w.get(k)), {"room": w.get("room"), "pos": w.get("pos")})
    num = lambda x, lo=0.0, hi=1.0: max(lo, min(hi, float(x or 0)))
    out = {"id": str(d.get("id") or ""), "kind": _s(d.get("kind"), 60) or "thing",
           "parts": [{"part": _s(p.get("part"), 30), "material": _s(p.get("material"), 30), "at": p.get("at")} for p in d.get("parts") or [] if isinstance(p, dict)],
           "verbs": {v: num(n) for v, n in (d.get("verbs") or {}).items() if v in VERBS and num(n) > 0},
           "tier": max(0, min(4, int(d.get("tier") or 0))), "class": d.get("class") if d.get("class") in CLASSES else "plain",
           "state": {"wear": num(s.get("wear"), 0.0, 1.5), "broken": bool(s.get("broken")),
                     "charge": {m: max(0, int(n or 0)) for m, n in (s.get("charge") or {}).items() if m in CHARGES},
                     "holds": _ids(s.get("holds")), "on": bool(s.get("on")), "lit": bool(s.get("lit"))},
           "owner": d.get("owner") or None, "maker": d.get("maker") or None, "made": int(d.get("made") or 0), "quality": num(d.get("quality")),
           "name": _s(d.get("name"), 60), "heirloom": d.get("heirloom") or None, "star": bool(d.get("star")), "where": where}
    if d.get("material") is not None or d.get("n") is not None:   # a bit stack
        out.update(material=_s(d.get("material"), 30), n=max(1, int(d.get("n") or 1)))
    return out


def works(it, verb):
    """An item's strength at a verb now: 0 when broken, or when what it runs on is empty."""
    it = item(it)
    if it["state"]["broken"] or verb not in it["verbs"]:
        return 0.0
    return 0.0 if it["state"]["charge"] and not any(it["state"]["charge"].values()) else it["verbs"][verb]


# §2.1 what can be wrong with the house: kind -> (the fixers: verbs, or "trade", "nurse", "wait", "tool"; the base urgency 1-4)
FIXERS = VERBS + ("trade", "nurse", "wait", "tool")
DEFICITS = {"cold": (("heat", "cover"), 3), "dark": (("light",), 2), "mess": (("carry",), 1), "leak": (("mend",), 3),
            "food_low": (("grow", "catch", "trade"), 3), "food_spoiling": (("hold",), 2), "mouse": (("catch", "cover", "signal"), 2),
            "no_bed": (("cover", "hold"), 2), "sick_untended": (("nurse", "pour", "heat"), 4), "broken": (("mend",), 1),
            "works_goal": (("carry",), 1), "gate_shut": (("move", "wait"), 1), "own_box": (("hold",), 1), "own_tool": (("tool",), 1),
            "own_light": (("light",), 1)}
DEFICIT_KINDS = tuple(DEFICITS)


def deficit(d):
    """§2.1 {"id": "kind|where|who" (the dedup key), "kind", "where": a room or item id or None, "who": a hob or None,
    "urgency" 1-4, "fixers": [FIXERS], "since": tick, "closed": tick or None, "by": the hob whose job closed it, "words": the
    deficit in plain words (B's deficits.words, kept so the board and the page need not ask B)}."""
    d = d if isinstance(d, dict) else {}
    kind = d.get("kind") if d.get("kind") in DEFICITS else "mess"
    where, who = d.get("where") or None, d.get("who") or None
    return {"id": "%s|%s|%s" % (kind, where or "", who or ""), "kind": kind, "where": where, "who": who,
            "urgency": max(1, min(4, int(d.get("urgency") or DEFICITS[kind][1]))),
            "fixers": [f for f in (d.get("fixers") or DEFICITS[kind][0]) if f in FIXERS] or list(DEFICITS[kind][0]),
            "since": int(d.get("since") or 0), "closed": d.get("closed"), "by": d.get("by") or None, "words": _s(d.get("words"), 200)}


# §3.1 a job's steps (the body's) and states
JOB_STEPS = ("get", "gather", "buy", "make", "use", "inspect")
JOB_STATES = ("open", "taken", "done", "failed")
MADE_FOR = ("job", "plan", "taught", "nothing")   # §3.3 why a thing was made (the Lab's: "nothing" should read 0)


def job(d):
    """§3.1 {"id", "deficit": its id, "kind": the deficit's kind, "steps": [{"do": JOB_STEPS, "what": a kind, material or
    item id, "where": a room id or None, "verb": a verb or None, "done": bool}], "taker": a hob or None, "since",
    "touched": the taker's last step, "state": JOB_STATES, "words": what it is, in plain words ("a patch for the attic's leak")}."""
    d = d if isinstance(d, dict) else {}
    steps = [{"do": s["do"], "what": _s(s.get("what"), 60), "where": s.get("where") or None, "verb": s.get("verb") if s.get("verb") in VERBS else None,
              "done": bool(s.get("done"))} for s in d.get("steps") or [] if isinstance(s, dict) and s.get("do") in JOB_STEPS]
    return {"id": str(d.get("id") or ""), "deficit": str(d.get("deficit") or ""), "kind": d.get("kind") if d.get("kind") in DEFICITS else "mess",
            "steps": steps, "taker": d.get("taker") or None, "since": int(d.get("since") or 0), "touched": int(d.get("touched") or d.get("since") or 0),
            "state": d.get("state") if d.get("state") in JOB_STATES else "open", "words": _s(d.get("words"), 200)}


def board(d):
    """§2.2 house["v5"]["board"] (house["board"] is the hub's news board, v3.5.4): {"deficits": [deficit()] open, by urgency x age; "jobs": [job()] open or taken; "closed":
    [{"kind", "where", "who", "by", "tick", "words"}] today; "tick"}."""
    d = d if isinstance(d, dict) else {}
    return {"deficits": [deficit(x) for x in d.get("deficits") or []], "jobs": [job(x) for x in d.get("jobs") or []],
            "closed": [{"kind": c.get("kind"), "where": c.get("where"), "who": c.get("who"), "by": c.get("by"), "tick": int(c.get("tick") or 0),
                        "words": _s(c.get("words"), 200)} for c in d.get("closed") or [] if isinstance(c, dict)],
            "tick": int(d.get("tick") or 0)}


# §5 the Lab's Jobs section reads these counters: house["v5"]["counts"][world day][key][sub] = n (fourteen days kept: a rehearsal sums ten).
# verbs: verb -> uses; broke, mended: kind -> n; made_for: MADE_FOR -> n; scrap_earned, scrap_spent: hob -> points;
# idle: hob -> ticks in leisure while a job it fits was open; awake: hob -> ticks awake; taken: hob -> jobs taken;
# taken_kind: deficit kind -> jobs taken; opened, closed: deficit kind -> n.
COUNTS = ("verbs", "broke", "mended", "made_for", "scrap_earned", "scrap_spent", "idle", "awake", "taken", "taken_kind", "opened", "closed")


def count(house, key, sub, n=1, day=None):
    assert key in COUNTS + COUNTS51 + COUNTS53, key
    days = house.setdefault("v5", {}).setdefault("counts", {})
    d = str(house["clock"]["day"] if day is None else day)
    days.setdefault(d, {}).setdefault(key, {})
    days[d][key][str(sub)] = days[d][key].get(str(sub), 0) + n
    for old in sorted(days, key=int)[:-14]:
        days.pop(old)


def counts(house, day=None):
    """One world day's counters (today's by default), every key present."""
    d = (house.get("v5") or {}).get("counts", {}).get(str(house["clock"]["day"] if day is None else day), {})
    return {k: dict(d.get(k, {})) for k in COUNTS + COUNTS51 + COUNTS53}


# The v5 helpers' seams: module -> {function: what it does}. check_contracts: present once that helper is merged.
API5 = {
    "A": {"engine.items": {"of": "(house, cfg, o, name=None) -> item(): a made thing's or a fixture's record (o['item']), made on first sight",
                           "everything": "(house, cfg) -> [(room id, name, item)]: every item in the house, bit stacks included",
                           "find": "(house, cfg, verb=None, kind=None, owner=None, room=None, working=True) -> [(room id, name, item)]",
                           "bits": "(house, cfg, room) -> [item()]: the room's loose bits as stacks by tile and kind",
                           "strength": "(house, cfg, room, verb, lit_only=False) -> the strongest working item at a verb in a room (0 for none)",
                           "covered": "(house, cfg, pet) -> 0..1: the cover on a sleeper (its bed's, a blanket's)",
                           "wear": "(house, cfg, it, uses=1) -> True when this use broke it",
                           "put": "(house, cfg, pet, name, container) -> words: into a container it can reach (the owner's guard)",
                           "take_out": "(house, cfg, pet, container, item_id) -> words",
                           "scrap_value": "(cfg, it) -> scrap-points it fetches at the machine (§4.1)",
                           "migrate": "(house, cfg) -> [report lines]: every made thing an item, the clear-out; once a house (§6)"},
          "engine.verbs": {"apply": "(house, cfg, pet, name, verb=None, target=None) -> (words, fx, key): using a thing, as things.use was",
                           "mend": "(house, cfg, pet, name) -> (words, ok): a broken item mended with the part (and the hammer for a tool)",
                           "refill": "(house, cfg, pet, name) -> (words, ok): what it runs on, poured in from what it carries",
                           "RESOLVE": "verb -> its resolver (every one of VERBS)"}},
    "B": {"engine.deficits": {"scan": "(house, cfg) -> [deficit()]: what is wrong now (every ten ticks)",
                              "tick": "(house, cfg): scan, dedup by id, open and close, the moments and the board",
                              "words": "(house, cfg, d) -> the deficit in plain words, for the board and the packets",
                              "DETECT": "deficit kind -> its detector (every one of DEFICITS)"},
          "engine.jobs": {"plan": "(house, cfg, d) -> job() or None: the engine's plan for a deficit (§3.1)",
                          "tick": "(eng): free hobs take jobs by fit; untouched jobs go free; done jobs close (§3.2)",
                          "of": "(house, pet) -> its job() or None",
                          "line": "(house, cfg, pet) -> words for its plan packet: the board and its job (§3.5)",
                          "FIT": "deficit kind -> {trait or style or drive: weight} (every one of DEFICITS)"},
          "engine.trade": {"buy": "(house, cfg, pet, material) -> (words, ok): a bit for scrap at the machine (§4.1)",
                           "sell": "(house, cfg, pet, name) -> (words, ok): a thing it carries for scrap"}},
    "C": {"engine.lab4": {"jobs": "(eng) -> the Lab's Jobs section (§5)"}},
}
BUILT5 = {"A", "B", "C"}   # the v5 helpers merged so far; the lead adds each at its merge


# ==== SPEC-v5.1: the grammar, knowledge and the book (the lead's; helper A parts and the parser; then B knowledge
# and the book, C the prompt, invention, sprites and the view) ====
#
#    who writes                 what                                   who reads
#    lead                       parts.toml (parts, materials, lines),   A grammar, contracts.grammar
#                               kinds.toml's `parts` (the recipes)
#    A grammar.parse            parsed()                                A items' verbs, C invention, the migration
#    A items                    item(): parts, verbs from them, tier    everyone
#    B knowledge                pet["knows"][key] = knowledge()         A grammar.tier, C the prompt and the cards
#    B book                     pet["read"][i] = read()                 B talk and wants, C the cards and the Lab
#    C invention                house["invented"][kind] = recipe()      A grammar.recipe, B study, C sprites, the view
#    A, B, C                    count() with COUNTS51                   C the Lab's Grammar section
#    B knowledge.tick           house["v5"]["tier"][day] = 0-4          C the header and the Lab (tier over time)
#
# A part that wants another of the same wave to act leaves it a line (as v4.2's beliefs_due), never an import.

PARTS51 = ("grammar", "knowledge", "book2", "sprites2")


def on51(cfg, part=None):
    """Is this part of v5.1 on? It rides on v5.0's items (`[v5] on` and `[items] on`); off is v5.0's behaviour. The one gate."""
    if not on5(cfg, "items"):
        return False
    return part is None or bool((cfg.get(part) or {}).get("on"))


# §2 tiers, said on the header ("the house knows worked things") and on a hob's card
TIERS = ("found", "worked", "mechanism", "powered", "signal")
TIER_WORDS = ("found things", "worked things", "mechanisms", "powered things", "signals")
MAT_CLASSES = ("soft", "hard", "sharp", "rigid", "glassy", "springy", "conductive")
SOURCES = ("grows", "found", "worked", "bought", "window", "scavenged")   # (window and scavenged: none in the house this phase)
ROLES = ("base", "on", "wrap")
INVENT_MOST = 5      # parts in one invention (parts.json's max_design_parts)
CHARGE_LAUNCH = ("pebble", "seed", "nut", "berry", "dart")   # §3 what a launcher's "shot" is filled from (kinds.toml [charge]); a dart is a pin and a feather
GRAMMAR_FILE = Path(__file__).resolve().parent.parent / "parts.toml"


def tier_words(t):
    return "the house knows " + TIER_WORDS[max(0, min(4, int(t or 0)))]


def part(d, name=""):
    """§1 a part: {"name", "verbs": {verb: 0..1}, "needs": {verb: [alternative]} where an alternative is a tuple of
    names that must all be on the thing (a part, a material, a material class, or "charge"), "with": {part: [materials]},
    "materials": [names or classes], "tier" 0-4, "role", "icon", "draw" (the view's part), "wear" (x the class's),
    "words"}."""
    d = d if isinstance(d, dict) else {}
    num = lambda x: max(0.0, min(1.0, float(x or 0)))
    alts = lambda xs: [tuple(_s(n, 30) for n in (a if isinstance(a, (list, tuple)) else [a]) if n) for a in xs or [] if a]
    return {"name": _s(d.get("name") or name, 30), "verbs": {v: num(s) for v, s in (d.get("verbs") or {}).items() if v in VERBS and num(s) > 0},
            "needs": {v: [a for a in alts(xs) if a] for v, xs in (d.get("needs") or {}).items() if v in VERBS},
            "with": {_s(p, 30): [_s(m, 30) for m in ms or []] for p, ms in (d.get("with") or {}).items()},
            "materials": [_s(m, 30) for m in d.get("materials") or [] if m], "tier": max(0, min(4, int(d.get("tier") or 0))),
            "role": d.get("role") if d.get("role") in ROLES else "on", "icon": _s(d.get("icon"), 80), "draw": _s(d.get("draw") or d.get("name") or name, 30),
            "wear": max(0.1, min(1.0, float(d.get("wear") or 1.0))), "words": _s(d.get("words"), 200)}


def material(d, name=""):
    """§2 a material: {"name", "tier" 0-4, "source": SOURCES, "from": the bit it is worked from or None, "at": the
    process or None, "class": MAT_CLASSES, "quality" 0.5-1.0}."""
    d = d if isinstance(d, dict) else {}
    return {"name": _s(d.get("name") or name, 30), "tier": max(0, min(4, int(d.get("tier") or 0))),
            "source": d.get("source") if d.get("source") in SOURCES else "found", "from": d.get("from") or None, "at": d.get("at") or None,
            "class": d.get("class") if d.get("class") in MAT_CLASSES else "hard", "quality": max(0.5, min(1.0, float(d.get("quality") or 0.5)))}


def parts_of(xs):
    """A recipe's parts as [{"part", "material"}], from kinds.toml's words ("flame of oil") or the model's objects."""
    out = []
    for x in xs or []:
        if isinstance(x, str) and " of " in x:
            p, m = x.split(" of ", 1)
            out.append({"part": _s(p, 30).lower(), "material": _s(m, 30).lower()})
        elif isinstance(x, dict) and x.get("part"):
            out.append({"part": _s(x.get("part"), 30).lower(), "material": _s(x.get("material"), 30).lower()})
    return out


def key_of(kind):
    """A kind's recipe key in pet["knows"] (v4's pet["recipes"] already says "kind:<kind>"; a process is "<bit>|<how>")."""
    return "kind:%s" % kind


def recipe(d):
    """§4.4 a recipe, a catalog kind's or an invented one's (house["invented"][kind]): {"key": key_of(kind), "kind",
    "parts": parts_of(), "charge": a material or None, "tier" 0-4, "verbs": {verb: 0..1} (the parser's), "by": the
    inventor or None, "how": its one sentence, "for": what it was for, "tick", "sprite": its drawn sprite's path or None}.
    An invented kind from before v5.1 keeps its other fields (use, from, props...) beside these."""
    d = d if isinstance(d, dict) else {}
    kind = _s(d.get("kind") or d.get("name"), 60)
    ch = _s(d.get("charge"), 30).lower()
    return {"key": key_of(kind), "kind": kind, "parts": parts_of(d.get("parts")), "charge": ch if ch and ch != "none" else None,
            "tier": max(0, min(4, int(d.get("tier") or 0))), "verbs": {v: max(0.0, min(1.0, float(s or 0))) for v, s in (d.get("verbs") or {}).items() if v in VERBS},
            "by": d.get("by") or None, "how": _s(d.get("how"), 200), "for": _s(d.get("for"), 120), "tick": int(d.get("tick") or 0), "sprite": d.get("sprite") or None}


# §4.3 the parser's answer. A refusal is said in the world's terms, never as a rule: REFUSE[why] is its words, filled
# by grammar.parse ({a}: "a"/"an"; {alts}: "wood or metal"). "absent" adds MACHINE when the material is of tier 3+.
REFUSE = {"empty": "a thing has to be made of something",
          "unknown": "there's no such thing as {a} {part} to make a thing of",
          "material": "{a} {part} can't be made of {material}: {alts} would",
          "with": "{a} {material} {part} won't take {a2} {other}: {alts} would",
          "absent": "there's no {material} in the house",
          "tier": "that's beyond what anyone here knows how to make",
          "needs": "{a} {part} wants {alts} before it can {verb}"}
MACHINE = "; the machine might have some one day"
REFUSALS = tuple(REFUSE)


def parsed(d):
    """§4.3 grammar.parse's answer: {"ok", "verbs": {verb: 0..1}, "tier" 0-4, "wear" (the casing's factor), "unmet":
    [{"part", "verb", "alts"}] (needs not met, said in the card and the next packet), "refusal": REFUSALS or None,
    "words": the refusal (or "" when ok), "part", "material": what was refused}. ok is True with verbs and no refusal."""
    d = d if isinstance(d, dict) else {}
    why = d.get("refusal") if d.get("refusal") in REFUSALS else None
    verbs = {v: max(0.0, min(1.0, float(s or 0))) for v, s in (d.get("verbs") or {}).items() if v in VERBS and float(s or 0) > 0}
    return {"ok": bool(verbs) and why is None, "verbs": verbs, "tier": max(0, min(4, int(d.get("tier") or 0))),
            "wear": max(0.1, min(1.0, float(d.get("wear") or 1.0))),
            "unmet": [{"part": _s(u.get("part"), 30), "verb": u.get("verb"), "alts": [_s(a, 60) for a in u.get("alts") or []]} for u in d.get("unmet") or [] if isinstance(u, dict)],
            "refusal": why, "words": _s(d.get("words"), 200) if why else "", "part": d.get("part") or None, "material": d.get("material") or None}


# §5 knowledge: pet["knows"][key] = knowledge(). `of` is knowing-of (read about, or studied above its reach): the
# grammar's examples show it and the hob may try to invent it, but it is not the recipe.
KNOW_FROM = ("made", "taught", "studied", "told", "read")
KNOW_WORDS = {"made": "made one", "taught": "was shown how", "studied": "worked it out from one", "told": "heard it in a tale", "read": "read of it"}
OLD_FROM = {"found": "made", "designed": "made", "inherited": "told"}   # v4's pet["recipes"][k]["from"] -> KNOW_FROM ("taught by X" -> taught)


def knowledge(d):
    """{"since": tick, "from": KNOW_FROM, "of": bool, "by": the teacher or the tale's hob or None}."""
    d = d if isinstance(d, dict) else {}
    f = str(d.get("from") or "")
    f = "taught" if f.startswith("taught") else OLD_FROM.get(f, f)
    f = f if f in KNOW_FROM else "made"
    return {"since": int(d.get("since") or d.get("tick") or 0), "from": f, "of": bool(d.get("of")) or f == "read", "by": d.get("by") or None}


# §5.3-5.4, §6.3 the aims v5.1 adds (planner.AIM covers them once B is merged; brain4.DAY says them from here)
AIMS51 = ("teach", "learn", "study")
AIM_WORDS51 = {"teach": "show {who} how to make something you know", "learn": "find out {what} in the book",
               "study": "take a thing to the bench and work out how it is made"}

# §6.3 where a question comes from (a want of kind "word"; "own" is the model's plan aim of kind learn)
QUESTIONS = ("material", "death", "happening", "first_seen", "heard", "visitor", "own")


def read(d):
    """§6.1-6.2 one read, pet["read"][i] (newest first): {"tick", "question", "title", "text", "links": [up to five
    titles from the passage], "source": QUESTIONS, "chain": how many reads on from a link (0 for a question's), "kinds":
    [catalog kinds it teaches of (book/known_of.toml)]}. Its memory is memory(kind="read", weight=3, what=[the title,
    the kinds, the material words])."""
    d = d if isinstance(d, dict) else {}
    return {"tick": int(d.get("tick") or 0), "question": _s(d.get("question"), 120), "title": _s(d.get("title"), 80), "text": _s(d.get("text"), 600),
            "links": [_s(x, 80) for x in d.get("links") or [] if x][:5], "source": d.get("source") if d.get("source") in QUESTIONS else "material",
            "chain": max(0, int(d.get("chain") or 0)), "kinds": [_s(k, 60) for k in d.get("kinds") or [] if k]}


# §4.2 the reply's `invent`, on a plan's make aim and a react's do: optional, constrained, defaulted to None.
def invent_schema(part_names, materials):
    return _obj(name=_text(24, 1), **{"for": _text(120, 1)},
                parts={"type": "array", "minItems": 1, "maxItems": INVENT_MOST,
                       "items": _obj(part={"enum": sorted(part_names)}, material={"enum": sorted(materials)})},
                charge={"enum": ["none"] + sorted(materials)}, how=_text(200, 1))


def invent(d):
    """The model's invent field made safe: {"name", "for", "parts": parts_of(), "charge": a material or None, "how"},
    or None when there is none (missing, "none", or no parts)."""
    if not isinstance(d, dict) or not d.get("parts") or _s(d.get("name")).lower() in ("", "none"):
        return None
    ps = parts_of(d.get("parts"))[:INVENT_MOST]
    ch = _s(d.get("charge"), 30).lower()
    return {"name": _s(d.get("name"), 24), "for": _s(d.get("for"), 120), "parts": ps, "charge": ch if ch and ch != "none" else None,
            "how": _s(d.get("how"), 200)} if ps else None


_GRAMMAR = {}


def grammar_data(path=None):
    """parts.toml as loaded: {"part": {name: part()}, "material": {name: material()}, "line": [{"parts", "says"}]}."""
    import tomllib
    path = Path(path or GRAMMAR_FILE)
    if path not in _GRAMMAR:
        t = tomllib.loads(path.read_text())
        _GRAMMAR[path] = {"part": {n: part(p, n) for n, p in t.get("part", {}).items()}, "material": {n: material(m, n) for n, m in t.get("material", {}).items()},
                          "line": [{"parts": list(x.get("parts") or []), "says": _s(x.get("says"), 300)} for x in t.get("line", [])]}
    return _GRAMMAR[path]


def line_tier(line, data=None):
    """A line is of its first part's tier (its subject: the tube's line names the spring, and is shown with the tube)."""
    data = data or grammar_data()
    return data["part"][line["parts"][0]]["tier"] if line["parts"] and line["parts"][0] in data["part"] else 0


def grammar(tier, have=(), examples=(), data=None):
    """§4.1 the grammar in words, for a hob that may make things up to tier + 1: the lines whose parts are all of that
    reach, what's to hand (`have`: materials in the house, those within reach), and up to five `examples` the caller
    chose (C: the catalog's and the known-of kinds, each "a lantern: a flame of oil under a shade of glass, on a
    handle of wood"). Plain words, about thirty lines at the top tier."""
    data = data or grammar_data()
    reach = max(0, min(4, int(tier or 0))) + 1
    lines = [x["says"] for x in data["line"] if line_tier(x, data) <= reach]
    out = ["How things are made: a thing is its parts, and each part is made of something."] + lines
    mats = [m for m in have if m in data["material"] and data["material"][m]["tier"] <= reach]
    if mats:
        out.append("What's to hand: %s." % ", ".join(mats))
    if examples:
        out.append("Things that can be made: %s." % "; ".join(list(examples)[:5]))
    return "\n".join(out)


# §8 the Lab's Grammar section reads these counters (count(), fourteen days kept, as v5.0's):
# invent: proposed|accepted -> n; refused: the refusal's words -> n; made_by: recipe|invention -> n; studied: hob -> n;
# taught: hob -> n; read: QUESTIONS (and "on" for a read-on) -> n; chain: hob -> chains of three; sprites:
# generated|composited|failed -> n.
COUNTS51 = ("invent", "refused", "made_by", "studied", "taught", "read", "chain", "sprites")


# The v5.1 helpers' seams: module -> {function: what it does}. check_contracts: present once that helper is merged.
API51 = {
    "A": {"engine.grammar": {"parse": "(cfg, parts, charge=None, have=None, tier=None) -> parsed(): verbs, tier, or a refusal in words (§4.3)",
                             "recipe": "(house, cfg, kind) -> recipe() or None: a catalog kind's (kinds.toml parts) or an invented one's",
                             "key_tier": "(house, cfg, key) -> 0-4: what knowing a key reaches: a kind's highest part's tier; a process 0",
                             "tier": "(house, cfg, pet) -> 0-4: the highest tier it knows (pet['knows'], not knowing-of)",
                             "house_tier": "(house, cfg) -> 0-4: the highest among the living",
                             "have": "(house, cfg) -> [materials]: what is in the house now (bits, the machine's stock, carried)",
                             "migrate": "(house, cfg) -> [report lines]: parts on every item, verbs re-parsed, mismatches against v5.0's (§9)"},
          "engine.verbs": {"RESOLVE": "verb -> its resolver; launch and bind are real (§3)"}},
    "B": {"engine.knowledge": {"knows": "(house, pet, key) -> knowledge() or None",
                               "can_make": "(house, cfg, pet, kind) -> bool: it knows the recipe (§5.1)",
                               "learn": "(house, cfg, pet, key, how, of=False, by=None) -> bool: new knowledge kept (KNOW_FROM)",
                               "study": "(house, cfg, pet, name) -> (words, ok): an hour at the bench with a thing (§5.3)",
                               "teach": "(house, cfg, pet, other, key) -> (words, ok)",
                               "words": "(house, cfg) -> the header's line (tier_words), and 'nobody left knows the forge' after a fall",
                               "tick": "(house, cfg): the house's tier per day, its falls, tales' recipes",
                               "migrate": "(house, cfg) -> [report lines]: every living hob knows what it made and its recipes (§9)"},
          "engine.book": {"remember": "(house, cfg, pet, rec) -> the read's memory (§6.1)",
                          "known_of": "(cfg) -> {title: [kinds]}: book/known_of.toml (§6.4)",
                          "ASK": "QUESTIONS -> the engine's question for each source (§6.3)"}},
    "C": {"engine.invention": {"propose": "(house, cfg, pet, inv) -> (words, ok): parsed and refused in words (a memory), or a job (§4.3-4.4)",
                               "finish": "(house, cfg, pet, job) -> the new kind: house['invented'], known by its maker, a first (§4.4)",
                               "examples": "(house, cfg, pet) -> [up to five example lines for contracts.grammar]",
                               "sprite": "(house, cfg, kind) -> queues the drawn sprite, or None when [sprites2] is off (§7.2)"},
          "engine.lab4": {"grammar": "(eng) -> the Lab's Grammar section (§8)"}},
}
BUILT51 = {"A", "B", "C"}   # the v5.1 helpers merged so far; the lead adds each at its merge


# ==== SPEC-v5.3: habits, projects, sites, and talk that goes on (the lead's; helpers A projects and sites, B habits
# and perception, then C talk rounds and §7's fixes) ====
#
#    who writes                 what                                   who reads
#    lead                       habits.toml, projects.toml             A, B (habits.TEMPLATES, projects.KINDS)
#    B habits                   pet["habits"] = [habit()]               B planner, C talk subjects and the card, the Lab
#    B habits                   house["v5"]["marks"][id] = mark()       B perception, C subjects, the view, the Lab
#    A projects                 house["v5"]["projects"][id] = project() B keep company, C subjects, the board, the Lab
#    A outdoors                 house["v5"]["sites"][id] = site()       A projects, the view
#    C talk                     a talk record's "rounds", "third"; pet["threads"] = [thread()]   C, the view, the Lab
#    A, B, C                    event53()                               the lead's §6 scenes (engine/scenes.py), the Lab
#
# The five scenarios of §6 are never written as rules: each module records the plain facts it causes (event53), and
# the lead's scenes.py finds a scenario where its facts line up. A module never records a scenario itself.

PARTS53 = ("habits", "projects", "talk3", "wallrail", "empty_house")


def on53(cfg, part=None):
    """Is this part of v5.3 on? It rides on v5.0 (`[v5] on`); off is v5.1's behaviour. The one gate. ([jobs] stages,
    §7's youngling rule, is a key of [jobs], read as cfg["jobs"].get("stages").)"""
    if not on5(cfg):
        return False
    return part is None or bool((cfg.get(part) or {}).get("on"))


# §1.2 the habit templates (habits.toml has each one's verb, targets, place, pace, what it leaves and its draw)
HABITS = ("collect", "hoard", "take", "tidy", "tend", "praise", "teach", "wander", "watch", "keep company", "prank", "mark")
HABIT_FROM = ("trait", "flaw", "drive", "style", "stage", "tale", "parent")   # §1.1: drawn from character, or picked up later
HABIT_FILE = Path(__file__).resolve().parent.parent / "habits.toml"
# §1.3 what a habit leaves that others can perceive. pile: a bit stack on a tile that grows; hoard: a container its owner
# guards; taken: a thing gone from its owner; moved: a thing not where it was (prank, tidy); mark: on a wall or the
# stones; tended: a plot watered; absent: a wanderer out; praised: pride given; site: a project's place (A's)
MARKS = ("pile", "hoard", "taken", "moved", "mark", "tended", "absent", "praised", "site")


def habit(d):
    """§1.1 {"name": HABITS, "verb": a verb or "" (praise, watch and keep company have none), "target": the class or
    hob it is about ("sticks", "shiny", a hob id), "place": a room id, {"room", "pos"}, or None, "pace": world hours
    between goes, "from": HABIT_FROM, "why": the trait, flaw, drive, style, stage, tale or parent it came of, "since",
    "count": goes done, "last": the tick of the last go, "fading": True once a week has passed without one}."""
    d = d if isinstance(d, dict) else {"name": d}
    pl = d.get("place")
    place = {"room": pl.get("room"), "pos": list(pl["pos"]) if isinstance(pl.get("pos"), (list, tuple)) else None} if isinstance(pl, dict) else (pl if isinstance(pl, str) and pl else None)
    return {"name": d.get("name") if d.get("name") in HABITS else HABITS[0], "verb": d.get("verb") if d.get("verb") in VERBS else "",
            "target": _s(d.get("target"), 40), "place": place, "pace": max(0.25, float(d.get("pace") or 24)),
            "from": d.get("from") if d.get("from") in HABIT_FROM else "trait", "why": _s(d.get("why"), 60),
            "since": int(d.get("since") or 0), "count": max(0, int(d.get("count") or 0)), "last": d.get("last"), "fading": bool(d.get("fading"))}


def mark(d):
    """§1.3 a mark a habit (or a project) left: {"id", "kind": MARKS, "by": the hob whose it is, "room", "pos" or None,
    "what": the bit class or thing ("sticks", "the small hammer"), "item": the item or stack id it is, or None, "n": how
    many (a pile's count), "tick": first left, "last": last grown, "seen": [hob ids that have perceived it], "found":
    tick or None (a hoard or a theft found out), "gone": tick or None (moved away, emptied), "words": the perception
    line in plain words ("Brody's stick pile fills the attic corner")}."""
    d = d if isinstance(d, dict) else {}
    pos = d.get("pos")
    return {"id": str(d.get("id") or ""), "kind": d.get("kind") if d.get("kind") in MARKS else "mark", "by": d.get("by") or None,
            "room": d.get("room") or None, "pos": list(pos) if isinstance(pos, (list, tuple)) and len(pos) == 2 else None,
            "what": _s(d.get("what"), 60), "item": d.get("item") or None, "n": max(0, int(d.get("n") or 0)), "tick": int(d.get("tick") or 0),
            "last": int(d.get("last") or d.get("tick") or 0), "seen": _ids(d.get("seen")), "found": d.get("found"), "gone": d.get("gone"),
            "words": _s(d.get("words"), 200)}


# §2 projects
PROJECT_KINDS = ("shelter", "bridge", "hearth", "bed", "bell post", "lookout", "garden plot", "workshop corner", "statue", "library nook", "build")
PROJECT_STATES = ("planned", "under way", "blocked", "orphaned", "abandoned", "done")
# a project's steps, in the body's terms: clear a site; gather a material (n of it, from the house's stocks or the
# machine at the trade price, §3); dig; frame (bind a frame); cover; hearth (stones and tinder); furnish (carry a made
# thing to it); grow (plant and water); build (build.py's spells with the hammer, for its own kinds and the statue)
PROJECT_STEPS = ("clear", "gather", "dig", "frame", "cover", "hearth", "furnish", "grow", "build")
PROJECT_FILE = Path(__file__).resolve().parent.parent / "projects.toml"
# §2.3 a site's stages as it is drawn; "decaying" after abandonment (§2.4)
SITE_STAGES = ("bare", "cleared", "framed", "covered", "done", "decaying")
SITE_KINDS = ("plot", "indoor")   # an outdoor plot (three in the yard, three in the meadow) or indoor tiles
PLOTS = {"ryard": 5, "rmeadow": 5}   # §3 plots per outdoor area (v5.3.1: ten, five an area; v5.3 had three)


def project(d):
    """§2.1 {"id", "goal": the model's words ("a shelter by the willow, for when the house is too loud") or the kind's,
    "kind": PROJECT_KINDS, "build": the building.toml project for kind "build" (and the statue), else None, "site": a
    site id or None, "steps": [{"do": PROJECT_STEPS, "what": a material or kind or "", "n": how many, "got": how many so
    far, "done": bool, "by": [hob ids who worked it]}], "stock": {material: n} (gathered and kept for it), "owners": [hob
    ids, the first is the one who began it], "names": [every owner it has had, for the finished thing's name (§2.4)],
    "progress": 0..1, "since", "touched": the tick of the last step, "state": PROJECT_STATES, "why": the drive or reason
    in words, "steps_by": {hob: steps done} (who did more, §2.5), "fixture": the finished thing's name in its room, or None}."""
    d = d if isinstance(d, dict) else {}
    kind = d.get("kind") if d.get("kind") in PROJECT_KINDS else "shelter"
    steps = [{"do": s["do"], "what": _s(s.get("what"), 40), "n": max(1, int(s.get("n") or 1)), "got": max(0, int(s.get("got") or 0)),
              "done": bool(s.get("done")), "by": _ids(s.get("by"))} for s in d.get("steps") or [] if isinstance(s, dict) and s.get("do") in PROJECT_STEPS]
    owners = _ids(d.get("owners"))
    return {"id": str(d.get("id") or ""), "goal": _s(d.get("goal"), 160), "kind": kind, "build": d.get("build") or None, "site": d.get("site") or None,
            "steps": steps, "stock": {_s(m, 30): max(0, int(n or 0)) for m, n in (d.get("stock") or {}).items() if m},
            "owners": owners, "names": list(dict.fromkeys(_ids(d.get("names")) + owners)),
            "progress": max(0.0, min(1.0, float(d.get("progress") or (sum(s["done"] for s in steps) / len(steps) if steps else 0)))),
            "since": int(d.get("since") or 0), "touched": int(d.get("touched") or d.get("since") or 0),
            "state": d.get("state") if d.get("state") in PROJECT_STATES else "planned", "why": _s(d.get("why"), 160),
            "steps_by": {str(k): max(0, int(v or 0)) for k, v in (d.get("steps_by") or {}).items()}, "fixture": d.get("fixture") or None}


def site(d):
    """§2.3 {"id", "kind": SITE_KINDS, "room", "tiles": [[x, y]], "name": a landmark's words ("by the willow"), "project":
    the project id that owns it or None, "stage": SITE_STAGES, "since", "decay": 0..1 (abandoned: a season to nothing)}."""
    d = d if isinstance(d, dict) else {}
    return {"id": str(d.get("id") or ""), "kind": d.get("kind") if d.get("kind") in SITE_KINDS else "plot", "room": d.get("room") or None,
            "tiles": [list(t) for t in d.get("tiles") or [] if isinstance(t, (list, tuple)) and len(t) == 2], "name": _s(d.get("name"), 60),
            "project": d.get("project") or None, "stage": d.get("stage") if d.get("stage") in SITE_STAGES else "bare",
            "since": int(d.get("since") or 0), "decay": max(0.0, min(1.0, float(d.get("decay") or 0)))}


# §4 the plan's optional `project` proposal (the model may not return a habit: habits are the body's)
def project_schema(kinds=PROJECT_KINDS, sites=()):
    return _obj(kind={"enum": ["none"] + [k for k in kinds if k != "build"]}, site=_text(60), why=_text(160), goal=_text(160))


def proposal(d):
    """The model's `project` made safe: {"kind", "site": words or "", "why", "goal"}, or None ("none", missing, a habit)."""
    if not isinstance(d, dict) or d.get("kind") not in PROJECT_KINDS or d.get("kind") == "build":
        return None
    return {"kind": d["kind"], "site": _s(d.get("site"), 60), "why": _s(d.get("why"), 160), "goal": _s(d.get("goal") or d.get("why"), 160)}


# §5 talk that goes on. After each round's lines both sides answer go_on: yes|no with a reason; while both say yes
# another round is asked, up to [talk3] rounds. A talk record (house["talks"]) gains "rounds": [[lines of round 1],
# ...] (its "lines" stay all of them, in order), "third": the listener's id or None, "go_on": [{name: {"go_on", "why"}}
# per round], and "thread": the thread it left or None.
GO_ON = ("yes", "no")


def talk_round_fields(names):
    """§5.1 each speaker's go_on and why, after the lines (by the names the reply uses)."""
    return {"go_on": _obj(**{n: _obj(go_on={"enum": list(GO_ON)}, why=_text(160, 1)) for n in names})}


def go_on(reply, names):
    """{name: {"go_on": "yes"|"no", "why"}} from a round's reply; a side missing or misshapen says no (a talk never
    runs on by default)."""
    g = (reply or {}).get("go_on") if isinstance(reply, dict) else None
    g = g if isinstance(g, dict) else {}
    return {n: {"go_on": "yes" if isinstance(g.get(n), dict) and g[n].get("go_on") == "yes" else "no",
                "why": _s(g[n].get("why"), 160) if isinstance(g.get(n), dict) else ""} for n in names}


def thread(d):
    """§5.2 a talk left open, kept on both hobs (pet["threads"]): {"with": the other hob's id, "subject": plain words,
    "question": the open question (the side that wanted more, its why), "by": the hob that wanted more, "tick", "picked":
    the tick it was picked up, or None}. Picked up only within two world days."""
    d = d if isinstance(d, dict) else {}
    return {"with": d.get("with") or None, "subject": _s(d.get("subject"), 120), "question": _s(d.get("question"), 160), "by": d.get("by") or None,
            "tick": int(d.get("tick") or 0), "picked": d.get("picked")}


# §5.5 where a talk's subject may come from, beside v4.2.2's (talk.SUBJECT53 covers each)
SUBJECTS53 = ("habit", "project", "thread", "perception")


# §6, §8 the plain facts each module records (house["v5"]["events53"][kind], the newest EVENTS_KEEP of each kept, so a
# forty-day rehearsal reads them all). Never a scenario: scenes.py composes those.
#   habit {pet, habit, what}: a habit's go;  marked {pet, mark, kind}: a mark left or grown;  noticed {pet, mark, owner}
#   mess {pet, mark, owner}: a pile counted as mess;  moved {pet, owner, mark}: another's pile or thing moved
#   taken {pet, owner, thing, seen}: a thing carried off;  missed {pet, thing, suspect}: an owner found it gone
#   found {pet, owner, mark}: a hoard found;  opinion {pet, about, cause, by}: an opinion fell or rose by a cause
#   resent {pet, against, cause}: a grievance or envy;  praise {pet, to, pride}: praise given and the pride it raised
#   project {project, kind, state, owners}: a project's state changed;  step {project, pet, do}: a step done
#   slept_out {pet, site}: a night under its own cover;  came_in {pet, why}: in from its shelter for food or company
#   bond {a, b, level}: a bond rose;  taken_up {project, pet, was}: an orphan's new owner
#   round {a, b, n}: a talk's round n (2 and on);  thread {a, b, subject, picked}: left (picked False) or picked up
#   third {pet, a, b}: a third hob's line in a talk
EVENTS53 = ("habit", "marked", "noticed", "mess", "moved", "taken", "missed", "found", "opinion", "resent", "praise", "project", "step",
            "slept_out", "came_in", "bond", "taken_up", "round", "thread", "third")
EVENTS_KEEP = 3000


def event53(house, kind_, **rec):   # (kind_: a fact may carry its own "what" and "kind")
    assert kind_ in EVENTS53, kind_
    rows = house.setdefault("v5", {}).setdefault("events53", {}).setdefault(kind_, [])
    rows.append(dict(rec, tick=house["tick"]))
    del rows[:-EVENTS_KEEP]


def events53(house, what, since=0):
    return [r for r in ((house.get("v5") or {}).get("events53") or {}).get(what, []) if r["tick"] >= since]


# §6 the scenarios scenes.py looks for (the rehearsal's gate and the Lab's counters)
SCENES = ("pile", "hoard", "shelter", "praise", "joint", "orphan", "thread")

# §8 the Lab's Life counters (count(), fourteen days kept): habit: template -> goes; marks: MARKS -> left; noticed:
# MARKS -> perceived; steps: hob -> project steps; projects: PROJECT_STATES -> changes into; rounds: 1|2|3 -> talks
# that ran so many; threads: left|picked -> n; third: hob -> lines as the third; idle53: hob -> idle ticks with the
# reading hour out
COUNTS53 = ("habit", "marks", "noticed", "steps", "projects", "rounds", "threads", "third", "idle53")

# The v5.3 helpers' seams: module -> {function: what it does}. check_contracts: present once that helper is merged.
API53 = {
    "A": {"engine.projects": {"of": "(house, pet) -> its project() (the one it owns and works now) or None",
                              "begin": "(house, cfg, pet, kind, why='', goal='', site=None, with_=None) -> project() or None: one a hob at a time; a second waits (§2.6)",
                              "propose": "(house, cfg, pet, proposal) -> (words, ok): the plan's `project` (§2.6, §4)",
                              "line": "(house, cfg, pet) -> its project and next step in words, or 'you have no project' with the kinds its drive could start (§4)",
                              "step_aim": "(house, cfg, pet) -> an aim for today's step, or None (the planner's)",
                              "orphan": "(house, cfg, dead): its projects orphaned, said on the board (§2.4)",
                              "take_up": "(house, cfg, pet, pid) -> bool: a kin or friend takes an orphan up (§2.4)",
                              "joint": "(house, cfg, a, b) -> project() or None: two keep-company hobs' shared project (§2.5)",
                              "sheltered": "(house, cfg, pet) -> the site's room and tile it may sleep at, or None (§3)",
                              "tick": "(house, cfg): steps, abandonment, decay, the board's rows (§2.4)",
                              "migrate": "(house, cfg) -> [report lines]: first projects, build.py's under-way builds (§9)",
                              "STEP": "PROJECT_STEPS -> its handler (every one)"},
          "engine.outdoors": {"plots": "(house) -> [site()]: the yard's and meadow's plots, made once (§3)"}},
    "B": {"engine.habits": {"draw": "(house, cfg, pet, n=None) -> [habit()]: one or two from character at the youngling stage (§1.1)",
                            "line": "(house, cfg, pet) -> its habits in a line for the plan packet ('you tend to carry sticks to the attic corner')",
                            "seen": "(house, cfg, pet) -> [perception lines] for what's in its room (§1.3, §4)",
                            "marks": "(house, room=None) -> [mark()] standing",
                            "tick": "(house, cfg): goes at pace, fading, children copying, takes noticed (§1)",
                            "migrate": "(house, cfg) -> [report lines]: habits for every living youngling and older (§9)",
                            "ACT": "HABITS -> the planner activity (or aim) a go is (every one)",
                            "SEEN": "HABITS -> its perception line's words (every one)"}},
    "C": {"engine.talk": {"SUBJECT53": "SUBJECTS53 -> where that subject comes from (every one)",
                          "threads": "(house, pet, other=None) -> [thread()] open"},
          "engine.lab4": {"life": "(eng) -> the Lab's Life section (§8)"}},
}
BUILT53 = {"A", "B", "C"}   # the v5.3 helpers merged so far; the lead adds each at its merge
