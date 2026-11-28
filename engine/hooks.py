"""SPEC-v4.2 §5 (helper B): beliefs that act. A belief may carry a hook the engine can read (contracts.HOOKS: avoid a
place, avoid or prefer a thing, trust or watch a hob, do something at an hour, make a kind, never do something); the
planner scores by it (`score`, from [hooks]); a belief acted on is a moment the first time and a line in the ledger
each time; acted against with nothing coming of it, it is "tested", and the night's reflection is told. The model
sets a hook in reflect's `learned`; the engine sets those it knows the truth of (A's deaths, through
contracts.believe_later); the visitor's words are parsed for one (`parse`: keywords and names, no model call).
Switch: [hooks] on.

pet["hooked"] mirrors the hob's beliefs that have a hook, for the planner (which has no Memory): {"id", "text",
"hook", "truth", "doubted", "tested", "tested_at", "acted", "source"}. The marks the body sets on it (acted, tested)
go back into beliefs.json at the next look (`due`)."""
import re

from . import contracts as K
from . import memories
from .world import label, moment

# activities its words may name (do_at, never), to the activities' `do`
VERBS = {"sing": "sing", "dance": "dance", "fish": "fish", "tend": "tend", "water": "tend", "nap": "nap", "play": "play", "cook": "machine",
         "rest": "nap", "read": "inspect", "gather": "gather", "explore": "go", "build": "build", "make": "bench", "eat": "eat", "tidy": "tidy",
         "listen": "listen", "babble": "babble", "follow": "follow"}
WHEN = {"morning": "morning", "night": "night", "evening": "dusk", "dusk": "dusk", "day": "day"}


def on(cfg):
    return K.on(cfg, "hooks")


# ---- what a hook is about, in the room as it is ----

def rooms_of(house, arg):
    """The rooms its words name: by the room's name or type ("the cellar", "pond room", "pond")."""
    a = re.sub(r"^the ", "", arg.lower()).strip()
    return {rid for rid, r in house["rooms"].items() if r.get("type") and a and (a in (r.get("name") or "").lower() or (r.get("name") or "~").lower() in a or r["type"] in a)}


def hob_of(house, arg):
    a = arg.lower().strip()
    return next((p["id"] for p in house["pets"].values() if a and a in ((p.get("name") or "").lower(), label(p).lower())), None)


def things_of(house, pet, t):
    """The words for what an activity's target is: its name, a made thing's kind, material and name."""
    o = house["rooms"][pet["room"]]["objects"].get(t.get("what") or "") or {}
    r = (o.get("made") or {}).get("recipe") or {}
    return {str(x).lower() for x in (t.get("what"), r.get("kind"), r.get("material"), r.get("name")) if x}


def same_word(arg, words):
    a = arg.lower()
    return any(w and (w == a or re.search(r"\b%s\b" % re.escape(w), a) or re.search(r"\b%s\b" % re.escape(a), w)) for w in words)


def doing(arg, name, A):
    """Do its words name this activity? ("sing to the egg": sing; "never fish": fish)"""
    a = arg.lower()
    verb = next((v for v in VERBS if re.match(r"%s\b" % v, a)), None)
    return (verb and VERBS[verb] == A.get("do")) or a in name.lower() or (A.get("do") and a == A["do"])


def hour_is(house, when):
    if not when:
        return True
    c = house["clock"]
    now = "morning" if c["morning"] else c["phase"]
    return any(w in when.lower() and (now == v or (v == "day" and c["phase"] == "day")) for w, v in WHEN.items())


def _door_room(house, pet, t):
    room = house["rooms"][pet["room"]]
    return room["doors"].get(t.get("what") or t.get("door") or "")


def _make_work(A):
    from .planner import AIM
    return A.get("do") in AIM["make"][0]


# each hook: does it bear on this activity with this target (the planner adds [hooks] <name> when it does)
SCORE = {
    "avoid_place": lambda house, pet, h, name, A, t: _door_room(house, pet, t) in rooms_of(house, h["arg"]),
    "avoid_thing": lambda house, pet, h, name, A, t: same_word(h["arg"], things_of(house, pet, t)),
    "prefer_thing": lambda house, pet, h, name, A, t: same_word(h["arg"], things_of(house, pet, t)),
    "trust": lambda house, pet, h, name, A, t: bool(t.get("who")) and t["who"] == hob_of(house, h["arg"]),
    "watch": lambda house, pet, h, name, A, t: bool(t.get("who")) and t["who"] == hob_of(house, h["arg"]),
    "do_at": lambda house, pet, h, name, A, t: bool(doing(h["arg"], name, A)) and hour_is(house, h.get("when")),
    "make": lambda house, pet, h, name, A, t: _make_work(A),
    "never": lambda house, pet, h, name, A, t: bool(doing(h["arg"], name, A)),
}


def score(house, cfg, pet, activity, target, A=None):
    """The planner's score for an activity and its target from the hob's hooked beliefs ([hooks]); a doubted belief
    (§5.4) does not act. The beliefs that bore on a candidate are marked (pet["pressed"]: id -> +1 or -1), for `verdict`
    when the chosen activity is over."""
    if not on(cfg) or not pet.get("hooked"):
        return 0.0
    A = A or cfg["activities"].get(activity, {})
    s, pressed = 0.0, pet.setdefault("pressed", {})
    for b in pet["hooked"]:
        h = b.get("hook")
        if not h or b.get("doubted") or h["name"] not in SCORE:
            continue
        if SCORE[h["name"]](house, pet, h, activity, A, target):
            w = cfg["hooks"][h["name"]]
            s += w
            pressed[b["id"]] = 1 if w > 0 else -1
    return s


ACTED = {"avoid_place": "kept away from %s", "avoid_thing": "kept away from the %s", "prefer_thing": "went for the %s", "trust": "trusted %s",
         "watch": "kept an eye on %s", "do_at": "did as it believed (%s)", "make": "set about making %s", "never": "would not %s"}


def as_said(source):
    s = source or ""
    return "as %s said" % s[9:].replace("my ", "its ") if s.startswith("told by ") else "as it had seen" if s == "seen" else "as it had learned"


def verdict(house, pet, now):
    """(planner.did) The activity chosen is over: each belief that bore on the choice either held (it went for what
    it believed good, or kept from what it believed bad: acted on) or was acted against (tested, §5.2)."""
    pressed = pet.pop("pressed", None)
    if not pressed or not now:
        return
    t = {"what": now.get("what") or now.get("door"), "who": now.get("who")}
    for b in pet.get("hooked", []):
        sign = pressed.get(b["id"])
        if not sign:
            continue
        h, A = b["hook"], {"do": now.get("do")}
        if h["name"] == "avoid_place":   # (a door it went through has it in the room now)
            chose = pet["room"] in rooms_of(house, h["arg"])
        else:
            chose = SCORE[h["name"]](house, pet, h, now.get("name", ""), A, t)
        if sign > 0 and chose or sign < 0 and not chose:
            if b.get("acted") is None:
                b["acted"] = house["tick"]
                what = h["arg"] if h["name"] != "avoid_place" else next((house["rooms"][r]["name"] for r in sorted(rooms_of(house, h["arg"]))), h["arg"])
                moment(house, "belief acted", "%s %s, %s" % (label(pet), ACTED[h["name"]] % what, as_said(b.get("source"))), pet["id"], pet["room"])
            if b.get("noted") != house["clock"]["day"]:   # (the ledger: once a day a belief, not every tick of it)
                b["noted"] = house["clock"]["day"]
                K.note(house, "acted", pet=pet["id"], belief=b["id"], hook=h)
        elif sign < 0 and chose and b.get("truth") is not True:
            b["tested"], b["tested_at"] = b.get("tested", 0) + 1, house["tick"]
        else:
            continue
        pet["hooked_dirty"] = True


# ---- beliefs with hooks ----

def mirror(pet, mem):
    """pet["hooked"] from its beliefs, keeping the marks the body has set since (and writing them into beliefs.json)."""
    marks, out, dirty = {b["id"]: b for b in pet.get("hooked", [])}, [], False
    for b in mem.active():
        if not K.hook(b.get("hook")):
            continue
        m = marks.get(b["id"], {})
        for k in ("tested", "tested_at", "acted", "doubted"):
            if k in m and m[k] != b.get(k):
                b[k], dirty = m[k], True
        K.belief_extra(b)
        out.append({"id": b["id"], "text": b["statement"], "hook": b["hook"], "truth": b["truth"], "doubted": b["doubted"], "tested": b["tested"],
                    "tested_at": b.get("tested_at"), "acted": b["acted"], "source": b.get("source", "lived"), "noted": m.get("noted")})
    pet["hooked"] = out
    if dirty:
        mem.save()


def believe(eng, pet, text, hook, source, truth=None, doubted=False):
    """A belief with its hook (§5.1), from where it came. One it holds already (the same words or the same hook) is
    kept, and a doubt it had goes when it is told again by what it sees. A hob full of beliefs lets the longest unused
    one without a hook go. Returns the belief's id, or None."""
    m = eng.minds.get(pet["id"])
    text = K._s(text, 240)
    if not m or not text:
        return None
    hk, tick = K.hook(hook), eng.house["tick"]
    same = next((b for b in m.mem.active() if b["statement"] == text or (hk and K.hook(b.get("hook")) == hk)), None)
    if same:
        if same.get("doubted") and not doubted and source == "seen":
            same["doubted"] = False
            m.mem.save()
        mirror(pet, m.mem)
        return same["id"]
    held = m.mem.active()
    if len(held) >= m.mem.max:
        old = min(held, key=lambda b: (bool(b.get("hook")), max(b["revised"], b.get("reviewed", b["revised"])), b["created"]))
        m.mem.revise(old["id"], "discard", tick)
    bid = m.mem.write(text, tick, source, **K.belief_extra({"hook": hk, "truth": truth, "doubted": doubted}))
    mirror(pet, m.mem)
    return bid


def due(eng, pet):
    """(brain4.wants_thought, each tick) What other parts left it to believe (contracts.believe_later: what it saw of a
    death, what its parent believed) becomes beliefs; the body's marks go into beliefs.json."""
    if not on(eng.cfg):
        return
    for d in pet.pop("beliefs_due", None) or []:
        believe(eng, pet, d["text"], d.get("hook"), d.get("source") or "seen", d.get("truth"))
    if pet.pop("hooked_dirty", None) and eng.minds.get(pet["id"]):
        mirror(pet, eng.minds[pet["id"]].mem)


def tick(eng):
    """Every living hob's `due` (for a caller that runs once a tick rather than a hob at a time)."""
    for m in list(eng.minds.values()):
        due(eng, m.pet)


def inherit(house, cfg, child, parent):
    """(craft.inherit, at hatching) Its parent's beliefs with hooks are its own, told: it acts on them without knowing
    why (§5.1). They become beliefs at its first look (`due`)."""
    if not on(cfg) or not parent:
        return
    for b in parent.get("hooked", [])[:6]:
        K.believe_later(child, b["text"], b["hook"], "told by %s" % (parent.get("word") or label(parent)), b.get("truth"))


# ---- words to hooks and aims (§5.3, §5.6), no model call ----

AVOID_PLACE = re.compile(r"\b(stay|keep) (away|out)|\bavoid\b|\bdon'?t go|\bdo not go|\bnever go|\bdanger|\bbad place|\bnot safe")
BAD = re.compile(r"\bbad\b|poison|\bdon'?t (eat|touch)|\bdo not (eat|touch)|\bnever (eat|touch)|\bsick|\bavoid\b|\b(stay|keep) away|\bharm|\bdanger")
GOOD = re.compile(r"\bgood\b|\btry\b|\buse\b|\blike\b|\bbest\b|\bkeep\b|\bwant\b")


def parse(house, text, cfg=None):
    """A hook in a line of words, or None (§5.3: "stay away from the cellar at night", "the red fish is bad", "trust
    Eirlys", "sing to the egg"): keywords and the names the house knows."""
    low = " " + (text or "").lower() + " "
    about, where, what = memories.tag(house, text, cfg)
    hobs = [a for a in about if a != "visitor"]
    name = lambda pid: house["pets"][pid].get("name") or label(house["pets"][pid])
    when = next((w for w in WHEN if re.search(r"\b(at|in the|by|every) %s\b" % w, low)), "")
    place = house["rooms"][where]["name"] if where else next((R["name"] for t, R in sorted((cfg or {}).get("house", {}).get("rooms", {}).items())
                                                              if R.get("name") and (R["name"].lower() in low or re.search(r"\b%s\b" % re.escape(t), low))), None)   # (a room not yet found, by its name)
    if place and AVOID_PLACE.search(low):
        return K.hook({"name": "avoid_place", "arg": place})
    if what and BAD.search(low):
        return K.hook({"name": "avoid_thing", "arg": what[0]})
    if hobs and re.search(r"\b(don'?t|do not|never) trust|\bwatch\b|\bbeware\b|\bcareful (of|with)|\bkeep an eye", low):
        return K.hook({"name": "watch", "arg": name(hobs[0])})
    if hobs and re.search(r"\btrust", low):
        return K.hook({"name": "trust", "arg": name(hobs[0])})
    m = re.search(r"\b(?:never|don'?t ever|do not ever) (\w+)", low)
    if m and m.group(1) in VERBS:
        return K.hook({"name": "never", "arg": m.group(1)})
    m = re.search(r"\bmake (?:a |an |the |some )?([a-z][a-z -]*)", low)
    kinds = (cfg or {}).get("kinds", {})
    kind = next((k for k in sorted(kinds, key=len, reverse=True) if m and m.group(1).startswith(k)), None)
    if kind:
        return K.hook({"name": "make", "arg": kind})
    verb = next((v for v in VERBS if re.search(r"(^|[^a-z])%s\b" % v, low.strip())), None)
    if verb and (when or re.match(r"\s*%s\b" % verb, low)):
        return K.hook({"name": "do_at", "arg": text.strip().split(".")[0][:60] if not when else verb, "when": when})
    if what and GOOD.search(low):
        return K.hook({"name": "prefer_thing", "arg": what[0]})
    return None


AIM_WORDS = (("ask", r"\bask (\w+)"), ("explore", r"\b(look|go|search) (in|into|to|through|round|around)\b|\bexplore\b"), ("make", r"\bmake\b"),
             ("fish", r"\bfish"), ("tend", r"\b(tend|water)\b"), ("learn", r"\bfind out\b|\blearn\b|\bread\b"),
             ("help", r"\bhelp (\w+)"), ("be with", r"\b(be|stay|play|sit) with (\w+)"), ("rest", r"\b(rest|sleep|nap)\b"))


def aim_from(house, cfg, pet, text, why, frm):
    """An aim for tomorrow from words that are an imperative or a place ("go find out", "look in the attic", "ask Wen")
    (§5.6, §9.3): kept in pet["aims_next"] for the morning plan, the words' question its why. Returns the aim or None."""
    from .brain4 import aim_of
    low = (text or "").lower()
    about, where, what = memories.tag(house, text, cfg)
    hobs = [a for a in about if a != "visitor" and a != pet["id"] and house["pets"][a]["stage"] not in ("egg", "dead")]
    for kind, pat in AIM_WORDS:
        if not re.search(pat, low):
            continue
        target = (hobs[0] if hobs else None) if kind in ("ask", "help", "be with") else where if kind == "explore" else next((w for w in what if w in cfg.get("kinds", {})), None) if kind == "make" else None
        if kind in ("ask", "help", "be with") and not target:
            continue
        if kind == "explore" and not target:
            kind = "learn"
        a = aim_of(house, {"pet": pet["id"]}, {"text": K._s(text, 100), "why": K._s(why, 120), "kind": kind, "target": None})
        if not a:
            return None
        a.update(target=target, **{"from": frm})
        pet["aims_next"] = (pet.get("aims_next") or [])[-2:] + [a]
        return a
    return None
