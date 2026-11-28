"""SPEC-v5.3 §1, §4, §9 (helper B): habits and perception. A habit (contracts.habit) is the body's, never a model call:
pet["habits"] holds one or two, drawn at the youngling stage from character (habits.toml's need and weight, [habits]
pole and second), and a later one from a tale or a parent seen at it daily for [habits] copy_days. The model is told
them in a line of its plan packet and may leave one be for a day; a week without a go and it fades.

A go is an aim the engine gives (as v5.1's teach is), hourly, after the day's own aims (`give`; ACT names its kind):
collect and hoard fetch a bit of their class and carry it to the pile's tile or the hoard's box; tidy goes to a room
with another's pile or a mess, and moves the pile; tend waters what is planted, or goes to helper A's plots; teach is
v5.1's teach aim; wander goes outdoors by day; watch and keep company are time with the chosen hob (helper A forms
joint projects from keep company's `target`); mark scratches the wall of its room or the stones. `done` (planner.check)
finishes a go. Three are the body's at a moment (ACT "body"): take carries another's thing off when the room's others
are asleep or away, to its hoard (or its corner); prank moves or hides another's thing; praise praises another's work.

Each leaves a mark (contracts.mark, house["v5"]["marks"][id]). A pile is bit spots on one tile ({"pile": mark id},
ready False so nobody gathers from it; world.taken counts the tile); anyone tidying it (order.do_job, or the tidy
habit) moves it, and its owner resents that. Every mark is a perception line and a memory for hobs in its room
(`perceive`); the fussy count a pile as mess; an owner misses a taken thing within [habits] missed_hours and suspects
whoever was in the room last; a hoard is found by one looking for its lost thing, a watcher, or a curious hob alone
with it: a moment, a banner ("hoard found"), and the finders' opinions of the hoarder fall (`dishonest`). The plain
facts go to contracts.event53, never a scenario. Switch: [habits] on (contracts.on53); off: no habits, no marks."""
import tomllib

from . import character, opinions, order, planner, things
from . import contracts as K
from .world import LONG_AGO, add_event, dist, free_tile, here, hours, label, moment, rnd

T = tomllib.loads(K.HABIT_FILE.read_text())
TEMPLATES, CLASS = T["habit"], T["class"]
SERVED = {d for e in tomllib.loads(K.PROJECT_FILE.read_text())["kind"].values() for d in e["drives"]}   # "drive:unmet": a drive no project kind serves
POLES = {"brave": "timid", "tidy": "messy", "generous": "greedy", "curious": "cautious", "social": "solitary", "honest": "sly",
         "patient": "hasty", "playful": "serious", "ambitious": "content", "kind": "prickly"}   # (character.trait's second poles)
# a made thing's quality words that make it shiny or soft to a take or a hoard ("another's" takes anything)
LOOKS = {"shiny": {"bright", "glassy", "glowing", "sparkling", "jingling", "ringing", "frosted"}, "soft": {"soft", "snug", "hushing", "quiet", "calm"}}
STANDS = ("pile", "hoard", "mark", "taken")   # marks that stand until moved, found or gone; the rest are gone after a world day
WALLS = ("north wall", "south wall", "west wall", "east wall")
FIND = 0.05   # ponytail: a curious hob alone with a hoard finds it this often an hour; a [habits] key if it wants tuning

# §1.2 a go of each habit: the aim kind the engine gives (planner.AIM), or "body" (done at a moment, in `tick`)
ACT = {"collect": "gather", "hoard": "gather", "take": "body", "tidy": "gather", "tend": "tend", "praise": "body", "teach": "teach",
       "wander": "explore", "watch": "be with", "keep company": "be with", "prank": "body", "mark": "gather"}
# §1.3 each habit's perception line (habits.toml's `seen`; the three that leave nothing standing are seen being done)
SEEN = {n: e["seen"] for n, e in TEMPLATES.items()}
SEEN.update({k: v for k, v in {"teach": "{owner} shows the young ones how things are made", "watch": "{owner} keeps an eye on {target}",
                               "keep company": "{owner} works beside {target}"}.items() if not SEEN.get(k)})


def on(cfg):
    return K.on53(cfg, "habits")


def H(cfg):
    return cfg["habits"]


def living(house):
    return [p for p in house["pets"].values() if p["stage"] not in ("egg", "dead")]


def awake(p):
    return p["stage"] not in ("egg", "dead") and not p.get("sleep")


def of(pet):
    """Its habits, as kept (a list of contracts.habit)."""
    return pet.get("habits") or []


def live(pet):
    return [h for h in of(pet) if not h["fading"]]


def find(pet, name):
    return next((h for h in of(pet) if h["name"] == name), None)


# ---- §1.1 drawn from character ----

def keys_of(house, cfg, pet):
    """habits.toml's draw keys that hold for this hob."""
    pole, ks = H(cfg)["pole"], {"base", "stage:" + pet["stage"]}
    if "temper" in pet:
        for ax, low in POLES.items():
            t = character.trait(pet, ax)
            if t >= pole:
                ks.add(ax + "+")
            elif t <= -pole:
                ks.add(ax + "-")
    f, d, s = (pet.get("flaw") or {}).get("name"), (pet.get("drive") or {}).get("name"), (pet.get("voice") or {}).get("style")
    ks |= {"flaw:%s" % f} if f else set()
    ks |= {"drive:%s" % d} | ({"drive:unmet"} if d not in SERVED else set()) if d else set()
    ks |= {"style:%s" % s} if s else set()
    week = 7 * cfg["ticks_per_day"]
    if pet.get("grieved") or any(p["stage"] == "dead" and house["tick"] - (p.get("died") or LONG_AGO) < week and opinions.kin(house, pet, p) for p in house["pets"].values()):
        ks.add("stage:grieving")
    if pet.get("hooked"):
        ks.add("belief:hook")
    return ks


def weight(e, ks):
    return sum(w for k, w in e.get("weight", {}).items() if k in ks) if all(k in ks for k in e.get("need", [])) else 0.0


def why_of(e, ks):
    """(from, why): the key that weighed most, in words ("messy", "greedy", "to be left alone")."""
    k = max((k for k in e.get("weight", {}) if k in ks and k != "base"), key=lambda k: e["weight"][k], default="base")
    if k == "base":
        return "trait", "its nature"
    if k[-1] in "+-" and k[:-1] in POLES:
        return "trait", k[:-1] if k[-1] == "+" else POLES[k[:-1]]
    kind, _, word = k.partition(":")
    if kind == "belief":
        return "drive", "a belief it holds"
    return (kind if kind in K.HABIT_FROM else "trait"), ("grief" if word == "grieving" else "a want with no outlet" if word == "unmet" else word)


def pick_hob(house, cfg, pet, name):
    """The hob a watch or keep company is about: the one it likes least (envious) or its drive's one, or likes most."""
    others = [p for p in living(house) if p is not pet]
    if not others:
        return ""
    want = (pet.get("drive") or {}).get("target")
    if name == "watch" and want in house["pets"] and house["pets"][want] in others:
        return want
    like = lambda p: opinions.of(pet, p["id"]).get("liking", 0)
    pick = min if name == "watch" and (pet.get("flaw") or {}).get("name") == "envious" else max
    return pick(sorted(others, key=lambda p: p["id"]), key=like)["id"]


def corner_tile(house, cfg, room, r):
    """A free tile in one of the room's corners, a step in from the walls."""
    W, Hh = cfg["W"], cfg["H"]
    corners = [[1, 1], [W - 2, 1], [1, Hh - 2], [W - 2, Hh - 2]]
    return free_tile(house, cfg, room, r.choice(corners))


def make(house, cfg, pet, name, ks, r, frm=None, why=None):
    e = TEMPLATES[name]
    there = {sp["bit"] for rm in house["rooms"].values() for sp in rm.get("spots", [])}
    targets = [x for x in e["targets"] if x not in CLASS or set(CLASS[x]) & there] or e["targets"]   # (a class the house has bits of)
    t = r.choice(targets)
    if t == "hob":
        t = pick_hob(house, cfg, pet, name) if name != "praise" else ""
    place = None
    if e["place"] == "tile" and name == "collect":
        rid = pet.get("sleeps_in") if pet.get("sleeps_in") in house["rooms"] else pet["room"]
        place = {"room": rid, "pos": corner_tile(house, cfg, house["rooms"][rid], r)}
    elif name == "mark" and t == "wall":
        place = pet.get("sleeps_in") if pet.get("sleeps_in") in house["rooms"] else pet["room"]
    f, w = why_of(e, ks) if frm is None else (frm, why)
    return K.habit({"name": name, "verb": e["verb"], "target": t, "place": place, "pace": e["pace"], "from": f, "why": w, "since": house["tick"]})


def draw(house, cfg, pet, n=None):
    """API53: two distinct habits from character (v5.3.1: every template has a floor; character boosts), kept on the hob and returned."""
    if not on(cfg):
        return []
    ks, r = keys_of(house, cfg, pet), rnd(house, "habits", pet["id"], len(of(pet)))
    n = n or 2   # (v5.3.1: two distinct templates each)
    out = []
    for _ in range(n):
        have = {h["name"] for h in of(pet) + out}
        w = {k: weight(e, ks) for k, e in TEMPLATES.items() if k not in have}
        w = {k: v for k, v in sorted(w.items()) if v > 0}
        if not w:
            break
        name = r.choices(list(w), list(w.values()))[0]
        out.append(make(house, cfg, pet, name, ks, r))
    pet["habits"] = of(pet) + out
    pet["habit_drawn"] = house["tick"]
    return out


def gain(house, cfg, pet, name, frm, why, target=None):
    """A habit picked up later (a tale, a parent): at most two live ones."""
    if find(pet, name) or len(live(pet)) >= 2 or name not in TEMPLATES:
        return None
    h = make(house, cfg, pet, name, keys_of(house, cfg, pet), rnd(house, "gain", pet["id"], name), frm, why)
    if target:
        h["target"] = target
    pet["habits"] = of(pet) + [h]
    add_event(house, pet, "you have taken to it yourself: %s" % says(house, cfg, pet, h))
    return h


def told(house, cfg, listener, t):
    """(story.tell) A tale of a dead hob may leave the little one who hears it with the dead one's habit."""
    dead = house["pets"].get(t.get("about") or "")
    if not on(cfg) or not dead or listener["stage"] not in ("child", "youngling"):
        return None
    h = next((h for h in live(dead) if not find(listener, h["name"])), None)
    return h and gain(house, cfg, listener, h["name"], "tale", "the tale of %s" % label(dead))


# ---- words ----

def target_words(house, h):
    t = h["target"]
    p = house["pets"].get(t)
    return label(p) if p else {"another's": "another's", "plots": "the plots", "child": "the young ones", "wall": "the wall",
                                "stones": "the stones", "outside": "outside", "mess": "the mess", "": "someone"}.get(t, t)


def room_name(house, rid):
    r = house["rooms"].get(rid or "")
    return r["name"] if r and r.get("name") else "a room"


def box_of(house, cfg, pet):
    """Its hoard's box: (room id, name) of a container it owns, the one it sleeps by first; or None."""
    rooms = sorted(house["rooms"].values(), key=lambda r: (r["id"] != pet.get("sleeps_in"), r["id"]))
    return next(((r["id"], n) for r in rooms if r.get("type") for n, o in sorted(r["objects"].items())
                 if "made" in o and o["made"].get("owner") == pet["id"] and order.cap(cfg, o) and not o.get("on")), None)


def claim_box(house, cfg, pet):
    """Its box, or one nobody living owns in the room it sleeps in, which becomes its own."""
    b = box_of(house, cfg, pet)
    rid = pet.get("sleeps_in")
    if b or rid not in house["rooms"]:
        return b
    room = house["rooms"][rid]
    n = next((n for n, o in sorted(room["objects"].items()) if "made" in o and order.cap(cfg, o) and not o.get("on") and not o["made"].get("heirloom")
              and house["pets"].get(o["made"].get("owner") or "", {"stage": "dead"})["stage"] == "dead"), None)
    if n:
        room["objects"][n]["made"]["owner"] = pet["id"]
        return rid, n
    return None


def place_words(house, cfg, pet, h):
    pl = h["place"]
    if h["name"] == "collect" and isinstance(pl, dict):
        return "%s corner" % room_name(house, pl["room"])
    if h["name"] in ("hoard", "take"):
        b = box_of(house, cfg, pet)
        return "the %s in %s" % (b[1], room_name(house, b[0])) if b else "a box of your own"
    if h["name"] == "mark":
        return "the wall of %s" % room_name(house, pl) if isinstance(pl, str) else "the stones"
    return room_name(house, pl) if isinstance(pl, str) else ""


def says(house, cfg, pet, h):
    return TEMPLATES[h["name"]]["says"].format(target=target_words(house, h), place=place_words(house, cfg, pet, h))


def line(house, cfg, pet):
    """API53: its habits in a line for the plan packet, or ""."""
    hs = live(pet) if on(cfg) else []
    if not hs:
        return ""
    return "your habits: " + "; ".join(says(house, cfg, pet, h) for h in hs) + " (habits are yours to keep or leave be for a day; a week without one and it fades)"


def card(house, cfg, pet):
    """(pages.pet_page) Its habits in words for its card: what it tends to do, where it came from, how often."""
    out = []
    for h in of(pet):
        w = says(house, cfg, pet, h).replace("you tend to ", "", 1).replace(" your ", " its ")
        out.append("%s (from %s; %s)" % (w, h["why"] or h["from"], "fading" if h["fading"] else "%d times" % h["count"]))
    return out


# ---- marks ----

def marks_all(house):
    return house.setdefault("v5", {}).setdefault("marks", {})


def marks(house, room=None):
    """API53: the marks standing (not gone), in a room if one is given."""
    rid = room["id"] if isinstance(room, dict) else room
    return [m for m in ((house.get("v5") or {}).get("marks") or {}).values() if m["gone"] is None and (rid is None or m["room"] == rid)]


def leave(house, cfg, pet, kind, mid, room, pos=None, what="", item=None, n=None, words=""):
    """A mark left, or grown (the same id): its count, its words. Recorded as a fact and counted."""
    ms, t = marks_all(house), house["tick"]
    m = ms.get(mid)
    if m is None or m["gone"] is not None:
        m = ms[mid] = K.mark({"id": mid, "kind": kind, "by": pet["id"], "room": room, "pos": pos, "what": what, "item": item, "tick": t})
    m.update(last=t, n=m["n"] + 1 if n is None else n, words=words or m["words"])
    K.event53(house, "marked", pet=pet["id"], mark=mid, kind=kind)
    K.count(house, "marks", kind)
    return m


def gone(house, m):
    if m["gone"] is None:
        m["gone"] = house["tick"]


def pile_spots(room, mid):
    return [s for s in room["spots"] if s.get("pile") == mid and s.get("loose") and not s.get("on")]


def pile_words(house, cfg, m):
    owner = house["pets"].get(m["by"])
    w = SEEN["collect"].format(owner=label(owner) if owner else "someone", target=m["what"].rstrip("s"), place="%s corner" % room_name(house, m["room"]))
    return w + (" and blocks the way" if m["n"] >= H(cfg)["pile_block"] else "")


def to_pile(house, cfg, pet, h, bit):
    pl = h["place"]
    room = house["rooms"][pl["room"]]
    mid = "pile:%s:%s:%d,%d" % (pet["id"], pl["room"], pl["pos"][0], pl["pos"][1])
    pet["carrying"].remove(bit)
    room["spots"].append({"bit": bit, "pos": list(pl["pos"]), "ready": False, "back": None, "loose": True, "since": house["tick"], "pile": mid})
    m = leave(house, cfg, pet, "pile", mid, pl["room"], pl["pos"], h["target"], "bit:%s:%d,%d:%s" % (pl["room"], pl["pos"][0], pl["pos"][1], bit), len(pile_spots(room, mid)))
    m["words"] = pile_words(house, cfg, m)
    return "you carried the %s to your pile in %s: %d there now" % (bit, room_name(house, pl["room"]), m["n"])


def hoard_mark(house, cfg, pet, rid, box):
    o = house["rooms"][rid]["objects"][box]
    return "hoard:%s" % (o["made"].get("id") or box), "%s keeps a %s in %s nobody may open" % (label(pet), box, room_name(house, rid))


def contents(house, rid, box):
    """What is in a hoard's box, in words: each thing with its owner, and the bits."""
    room = house["rooms"][rid]
    owned = [(n, house["pets"].get(o["made"].get("owner") or "")) for n, o in sorted(room["objects"].items()) if o.get("on") == box and "made" in o]
    bits = [s["bit"] for s in room["spots"] if s.get("on") == box]
    return owned, bits


def to_hoard(house, cfg, pet, rid, box, bit=None, thing=None):
    """A bit it carries, or a thing (already in the box's room), into its hoard's box."""
    room = house["rooms"][rid]
    if bit:
        pet["carrying"].remove(bit)
        room["spots"].append({"bit": bit, "pos": list(room["objects"][box]["pos"]), "ready": True, "back": None, "loose": True, "on": box, "since": house["tick"], "hoard": True})
    if thing:
        from . import items
        o = room["objects"][thing]
        items.place(house, cfg, room, thing, o, box)
        o["pos"] = list(room["objects"][box]["pos"])
    mid, words = hoard_mark(house, cfg, pet, rid, box)
    owned, bits = contents(house, rid, box)
    m = leave(house, cfg, pet, "hoard", mid, rid, room["objects"][box]["pos"], box, str(room["objects"][box]["made"].get("id") or box), len(owned) + len(bits), words)
    return m


# ---- §1.2 a go ----

def aim(h, text, kind, target, **more):
    return dict({"text": text, "why": "it is your habit", "kind": kind, "target": target, "since": None, "done": None, "from": "drive", "habit": h["name"]}, **more)


def bit_to_fetch(house, cfg, pet, cls, avoid=None):
    """A bit of the class lying ready in a room it knows (this one first), not in a pile."""
    bits = set(CLASS.get(cls, ()))
    for rid in sorted(pet["rooms"], key=lambda r: (r != pet["room"], r)):
        r = house["rooms"].get(rid) or {}
        b = next((s["bit"] for s in r.get("spots", []) if s["bit"] in bits and s["ready"] and not s.get("on") and not s.get("pile") and not s.get("machine")
                  and list(s["pos"]) != list(avoid or [])), None)
        if b:
            return b
    return None


def aim_for(house, cfg, pet, h):
    """The aim a go of this habit is now, or None when there is nothing to do it with."""
    n, t = h["name"], h["target"]
    rooms = [rid for rid in pet["rooms"] if (house["rooms"].get(rid) or {}).get("type")]
    if n in ("collect", "hoard"):
        dest = (h["place"] or {}).get("room") if n == "collect" else (claim_box(house, cfg, pet) or (None,))[0]
        if not dest:
            return None
        cls = t if t in CLASS else None
        have = next((b for b in pet["carrying"] if b in CLASS.get(cls or "", ())), None)
        if have:
            return aim(h, "take the %s to %s" % (have, place_words(house, cfg, pet, h)), "gather", dest, carry=have)
        b = cls and bit_to_fetch(house, cfg, pet, cls, (h["place"] or {}).get("pos") if n == "collect" else None)
        return aim(h, "fetch a %s for %s" % (b, place_words(house, cfg, pet, h)), "gather", b) if b else None
    if n == "tidy":
        from . import deficits
        piles = [m["room"] for m in marks(house) if m["kind"] == "pile" and m["by"] != pet["id"] and m["room"] in rooms]
        messy = max(rooms, key=lambda rid: (deficits.mess_count(house, cfg, house["rooms"][rid]), rid), default=None)
        rid = piles[0] if piles else messy if messy and deficits.mess_count(house, cfg, house["rooms"][messy]) > cfg["deficits"]["mess_at"] else None
        return aim(h, "tidy up %s" % room_name(house, rid), "gather", rid) if rid else None
    if n == "tend":
        if "tend" in planner.feasible(house, cfg, pet):
            return aim(h, "water and weed what is planted", "tend", None)
        plot = next((s for s in sorted(((house.get("v5") or {}).get("sites") or {}).values(), key=lambda s: str(s.get("id")))
                     if isinstance(s, dict) and s.get("kind") == "plot" and s.get("room") in pet["rooms"]), None)
        return aim(h, "water and weed the plot %s" % (K.site(plot)["name"] or "outside"), "gather", plot["room"], plot=K.site(plot)["id"]) if plot else None
    if n == "wander":
        from .outdoors import is_out
        out = [rid for rid in sorted(pet["rooms"]) if is_out(rid)]
        if house["clock"]["phase"] != "day" or house["clock"]["hour"] >= 15 or not out:
            return None
        rid = rnd(house, "wander", pet["id"], house["clock"]["day"]).choice(out)
        return aim(h, "go out to %s for the day" % room_name(house, rid), "explore", rid)
    if n in ("watch", "keep company"):
        if t not in house["pets"] or house["pets"][t]["stage"] in ("egg", "dead"):
            h["target"] = t = pick_hob(house, cfg, pet, n)
        if not t:
            return None
        return aim(h, ("keep an eye on %s" if n == "watch" else "do your work beside %s") % label(house["pets"][t]), "be with", t)
    if n == "mark":
        stones = next((rid for rid in rooms for o in house["rooms"][rid]["objects"].values() if "memorial" in o), None) if t == "stones" else None
        rid = stones or (h["place"] if isinstance(h["place"], str) and h["place"] in house["rooms"] else pet.get("sleeps_in") or pet["room"])
        return aim(h, "stack stones at the stones" if stones else "mark the wall of %s" % room_name(house, rid), "gather", rid)
    return None


def due(house, cfg, h):
    last = h["last"] if h["last"] is not None else h["since"] - hours(cfg, h["pace"])
    return not h["fading"] and house["tick"] - last >= hours(cfg, h["pace"])


def give(house, cfg, pet):
    """Hourly: one open habit aim at a time, the habit due longest. It goes before the day's own aims (they wait, and
    their clocks with them: planner.check); a job's step and a question from life still come first (planner.current)."""
    if any(a.get("habit") and not a.get("done") and not a.get("failed") for a in pet.get("aims") or []) or pet.get("sleep"):
        return None
    for h in sorted((h for h in live(pet) if ACT[h["name"]] != "body" and due(house, cfg, h)), key=lambda h: h["last"] if h["last"] is not None else LONG_AGO):
        if h["name"] == "teach":
            from . import knowledge
            if not knowledge.on(cfg):
                continue
            n = len(pet.get("aims") or [])
            knowledge.give_teach(house, cfg, pet)
            if len(pet.get("aims") or []) > n:
                pet["aims"][-1]["habit"] = "teach"
                return pet["aims"][-1]
            continue
        a = aim_for(house, cfg, pet, h)
        if a:
            aims = pet.setdefault("aims", [])
            aims.insert(next((i for i, x in enumerate(aims) if not x.get("done") and not x.get("failed")), len(aims)), a)
            return a
    return None


def went(house, cfg, pet, h, what):
    """A go done: counted, the fact recorded, and the little ones about who see a parent at it."""
    h.update(count=h["count"] + 1, last=house["tick"], fading=False)
    # (contracts.event53's own parameter is named `what`, so the habit fact's `what` can't pass through it: its rows, kept as it keeps them)
    rows = house.setdefault("v5", {}).setdefault("events53", {}).setdefault("habit", [])
    rows.append({"pet": pet["id"], "habit": h["name"], "what": what, "tick": house["tick"]})
    del rows[:-K.EVENTS_KEEP]
    K.count(house, "habit", h["name"])
    day = house["clock"]["day"]
    for kid in here(house, pet, awake=True):
        if kid.get("parent") == pet["id"] and kid["stage"] in ("child", "youngling"):
            s = kid.setdefault("habit_seen", {}).get(h["name"]) or [None, 0]
            if s[0] != day:
                s = [day, s[1] + 1 if s[0] == day - 1 else 1]
            kid["habit_seen"][h["name"]] = s
            if s[1] >= H(cfg)["copy_days"]:
                gain(house, cfg, kid, h["name"], "parent", "watching %s" % label(pet), h["target"] if h["name"] in ("collect",) else None)


def done(house, cfg, pet, a):
    """planner.check: a habit's aim is done; its go is finished here. Returns what it did in words, or None."""
    h = find(pet, a.get("habit") or "")
    if not on(cfg) or not h:
        return None
    n, room = h["name"], house["rooms"][pet["room"]]
    said = None
    if n in ("collect", "hoard") and not a.get("carry"):   # the bit is fetched: now to the pile or the box
        b = next((x for x in pet["carrying"] if x == a.get("target")), None)
        if b:
            pet.setdefault("aims", []).append(aim(h, "take the %s to %s" % (b, place_words(house, cfg, pet, h)), "gather",
                                                  (h["place"] or {}).get("room") if n == "collect" else (box_of(house, cfg, pet) or (pet["room"],))[0], carry=b))
        return None
    if n == "collect" and a["carry"] in pet["carrying"] and (h["place"] or {}).get("room") == pet["room"]:
        said = to_pile(house, cfg, pet, h, a["carry"])
    elif n == "hoard" and a["carry"] in pet["carrying"]:
        b = box_of(house, cfg, pet)
        if b and b[0] == pet["room"]:
            to_hoard(house, cfg, pet, b[0], b[1], bit=a["carry"])
            said = "you put the %s in your %s" % (a["carry"], b[1])
    elif n == "tidy":
        for m in [m for m in marks(house, pet["room"]) if m["kind"] == "pile" and m["by"] != pet["id"]]:
            said = move_pile(house, cfg, pet, room, m)
        said = said or "you tidied up %s" % room_name(house, pet["room"])
    elif n == "tend" and a.get("plot"):
        site = K.site(((house.get("v5") or {}).get("sites") or {}).get(a["plot"]))
        leave(house, cfg, pet, "tended", "tended:%s" % a["plot"], pet["room"], (site["tiles"] or [None])[0], site["name"] or "the plot", a["plot"], 1,
              SEEN["tend"].format(owner=label(pet)))
        said = "you watered and weeded the plot"
    elif n in ("tend", "teach", "keep company"):
        said = a["text"]
    elif n == "wander":
        from .outdoors import is_out
        home = pet.get("sleeps_in") or next((r for r in sorted(pet["rooms"]) if (house["rooms"].get(r) or {}).get("type") and not is_out(r)), None)
        leave(house, cfg, pet, "absent", "absent:%s" % pet["id"], home, None, "outside", None, 1, SEEN["wander"].format(owner=label(pet)))
        said = "you went out for the day"
    elif n == "watch":
        said = watched(house, cfg, pet, house["pets"].get(a.get("target") or ""))
    elif n == "mark":
        said = marked(house, cfg, pet, h)
    if said is None:
        return None
    went(house, cfg, pet, h, said)
    add_event(house, pet, said)
    return said


def watched(house, cfg, pet, other):
    """A while watching another: what it saw, kept as a memory about it (gossip's content); a hoard it was near, found."""
    if not other or other["stage"] in ("egg", "dead"):
        return None
    from . import body
    now = body.state(other)["now"]
    did = [x for x in other.get("did4", []) if house["tick"] - x[0] < hours(cfg, 6)]
    seen_ = [e["habit"] for e in K.events53(house, "habit", house["tick"] - hours(cfg, 6)) if e["pet"] == other["id"]]
    what = ("tending to its habit: " + says(house, cfg, other, find(other, seen_[-1])).replace("you tend to ", "").replace(" your ", " its ")) if seen_ and find(other, seen_[-1]) \
        else (now or {}).get("name") or (did[-1][1] if did else "nothing much")
    text = "I watched %s: %s" % (label(other), what)
    remember(house, cfg, pet, text, 2, [other["id"]], other["room"], kind="watch")
    for m in marks(house, pet["room"]):
        if m["kind"] == "hoard" and m["by"] == other["id"] and m["found"] is None:
            found(house, cfg, pet, m)
    return "you watched %s a while" % label(other)


def marked(house, cfg, pet, h):
    from . import walls
    room = house["rooms"][pet["room"]]
    stone = next((n for n, o in sorted(room["objects"].items()) if "memorial" in o), None) if h["target"] == "stones" else None
    on_ = stone or WALLS[rnd(house, "wall", pet["id"]).randrange(4)]
    dead = house["pets"].get((room["objects"].get(stone) or {}).get("memorial", {}).get("pet") or "")
    belief = next((b.get("text") for b in pet.get("hooked") or [] if b.get("text")), None)
    text = (label(dead) if dead else None) or (belief or "")[:cfg["writing"]["max_chars"]] or "%s was here" % label(pet)
    walls.put(house, cfg, room, pet["id"], text, on_, "scratch", walls.along(cfg, pet, on_), pet.get("family", 1))
    what = "the stones" if stone else "the %s" % on_
    m = leave(house, cfg, pet, "mark", "mark:%s:%s" % (pet["id"], room["id"]), room["id"], list(room["objects"][stone]["pos"]) if stone else None, what, None, None,
              SEEN["mark"].format(owner=label(pet), place="%s of %s" % (what, room_name(house, room["id"]))))
    return "you %s: %s" % ("stacked a stone at the stones" if stone else "scratched a mark on the %s" % on_, m["words"])


# ---- the body's goes, at a moment: take, prank, praise ----

def takeable(house, cfg, pet, room, cls):
    """Another living hob's things here that may be carried off: not fixed, furniture, a box, an heirloom, nor taken already."""
    out = []
    for n, o in sorted(things.made(room).items()):
        m, owner = o["made"], house["pets"].get(o["made"].get("owner") or "")
        kind = m["recipe"].get("kind")
        if not owner or owner is pet or owner["stage"] in ("egg", "dead") or m.get("heirloom") or o.get("wall") or o.get("taken") or o.get("pocketed") \
                or order.cap(cfg, o) or cfg["kinds"].get(kind, {}).get("furniture") or (cfg["kinds"].get(kind) and things.prop(cfg, o).get("fixed")):
            continue
        if cls in LOOKS and m["recipe"].get("material") not in LOOKS[cls] and not any(b in str(kind) for b in CLASS.get(cls, ())):
            continue
        out.append(n)
    return out


def take(house, cfg, pet, h):
    """Another's thing carried off while nobody here is awake: to its hoard's box (or its corner here). Returns the mark."""
    room = house["rooms"][pet["room"]]
    if here(house, pet, awake=True):
        return None
    names = takeable(house, cfg, pet, room, h["target"])
    if not names:
        return None
    n = min(names, key=lambda n: dist(pet["pos"], room["objects"][n]["pos"]))
    o = room["objects"][n]
    owner = house["pets"][o["made"]["owner"]]
    frm = list(o["pos"])
    box = claim_box(house, cfg, pet)
    order.moved(o, house["tick"], house, cfg, room, n)
    if box and box[0] != room["id"] and n not in house["rooms"][box[0]]["objects"]:
        house["rooms"][box[0]]["objects"][n] = room["objects"].pop(n)
    elif not box or box[0] != room["id"]:
        box = None
        o["pos"] = free_tile(house, cfg, room, planner.corner_of(house, cfg, pet, room), n)
        o["pocketed"] = {"by": pet["id"], "tick": house["tick"], "from": frm}   # (an honest hob may put it back: planner's b:return)
    mid = "taken:%s" % (o["made"].get("id") or n)
    o["taken"] = {"by": pet["id"], "tick": house["tick"], "from": room["id"], "pos": frm, "mark": mid}
    if box:
        to_hoard(house, cfg, pet, box[0], box[1], thing=n)
    m = leave(house, cfg, pet, "taken", mid, room["id"], frm, n, str(o["made"].get("id") or n), 1, SEEN["take"].format(target=n))
    K.event53(house, "taken", pet=pet["id"], owner=owner["id"], thing=n, seen=False)
    went(house, cfg, pet, h, "you took %s's %s while nobody was looking" % (label(owner), n))
    return m


def prank(house, cfg, pet, h):
    """Once a day: another's thing here, its owner away or asleep, moved across the room or hidden in a box here."""
    room = house["rooms"][pet["room"]]
    names = [n for n in takeable(house, cfg, pet, room, None) if not awake(house["pets"][room["objects"][n]["made"]["owner"]]) or house["pets"][room["objects"][n]["made"]["owner"]]["room"] != room["id"]]
    if not names:
        return None
    r = rnd(house, "prank", pet["id"], house["tick"])
    n = r.choice(names)
    o = room["objects"][n]
    frm = list(o["pos"])
    box = next((b for b, k in sorted(order.stores(cfg, room).items()) if k > 0 and order.inside(cfg, room["objects"][b])), None)
    order.moved(o, house["tick"], house, cfg, room, n)
    if box and "tool" in str(o["made"]["recipe"].get("kind")) or box and r.random() < 0.5:
        order.put(house, cfg, pet, room, n, "on", box)
        how = "hid %s's %s in the %s" % (label(house["pets"][o["made"]["owner"]]), n, box)
    else:
        o["pos"] = free_tile(house, cfg, room, [r.randrange(1, cfg["W"] - 1), r.randrange(1, cfg["H"] - 1)], n)
        how = "moved %s's %s across the room" % (label(house["pets"][o["made"]["owner"]]), n)
    o["pranked"] = {"by": pet["id"], "tick": house["tick"], "from": frm}
    leave(house, cfg, pet, "moved", "moved:%s" % (o["made"].get("id") or n), room["id"], frm, n, str(o["made"].get("id") or n), 1, SEEN["prank"].format(target=n))
    K.event53(house, "moved", pet=pet["id"], owner=o["made"]["owner"], mark="moved:%s" % (o["made"].get("id") or n))
    moment(house, "prank", "%s %s for the fun of it" % (label(pet), how), pet["id"], room["id"])
    went(house, cfg, pet, h, "you " + how)
    return how


def worked_lately(house, cfg, p):
    """Has it done some work today (made, built, tended, tidied): what, in words, or None."""
    if house["tick"] - (p.get("last_made") or {}).get("tick", LONG_AGO) < cfg["ticks_per_day"]:
        return "the %s it made" % ((p.get("last_made") or {}).get("name") or "thing")
    work = [x for x in p.get("did4", []) if house["tick"] - x[0] < cfg["ticks_per_day"] and x[2] in ("build", "tend", "tidy", "machine", "bench", "fish")]
    return work[-1][1] if work else None


def praise(house, cfg, pet, h):
    """Once a day: another's work praised, here; its pride rises (praised_me); an envious hob here resents it."""
    from . import conflict
    others = [(p, worked_lately(house, cfg, p)) for p in here(house, pet, awake=True)]
    others = sorted([x for x in others if x[1]], key=lambda x: x[0]["id"]) or []
    if not others:
        return None
    other, work = others[rnd(house, "praise", pet["id"], house["clock"]["day"]).randrange(len(others))]
    was = (other.get("needs") or {}).get("pride", 0)
    opinions.move(house, cfg, other, pet["id"], "praised_me", "%s praised my work: %s" % (label(pet), work))
    rise = round((other.get("needs") or {}).get("pride", 0) - was, 2)
    K.event53(house, "praise", pet=pet["id"], to=other["id"], pride=rise)
    K.event53(house, "opinion", pet=other["id"], about=pet["id"], cause="praised_me", by=pet["id"])
    add_event(house, other, "%s praised your work: %s" % (label(pet), work))
    leave(house, cfg, pet, "praised", "praised:%s:%s" % (pet["id"], other["id"]), pet["room"], None, work, None, 1, SEEN["praise"].format(owner=label(pet), target=label(other)))
    for e in here(house, pet, awake=True):
        if e is not other and (e.get("flaw") or {}).get("name") == "envious":
            opinions.move(house, cfg, e, other["id"], "envy", "%s praised %s's work, and never mine" % (label(pet), label(other)))
            K.event53(house, "opinion", pet=e["id"], about=other["id"], cause="envy", by=pet["id"])
            K.event53(house, "resent", pet=e["id"], against=other["id"], cause="praise")
            if conflict.on(cfg):
                conflict.grudge(house, cfg, e["id"], other["id"], "%s was praised and I wasn't" % label(other))
    went(house, cfg, pet, h, "you praised %s's work" % label(other))
    return other


# ---- §1.3 perception and its consequences ----

def remember(house, cfg, pet, text, weight, about, where=None, what=(), kind="habit"):
    from . import memories
    if memories.on2(cfg):
        return memories.remember(house, cfg, pet, text, weight, kind, about, where, list(what))
    return memories.add(house, cfg, pet, text, weight, about, kind)


def fussy(cfg, pet):
    return (pet.get("voice") or {}).get("style") == "fussy" or character.trait(pet, "tidy") >= H(cfg)["pole"]


def perceive(house, cfg, pet):
    """What stands in its room: each mark seen once (a memory with tags, the fact counted); a pile, every world day, as
    mess to the fussy."""
    for m in marks(house, pet["room"]):
        if m["by"] == pet["id"]:
            continue
        if pet["id"] not in m["seen"]:
            m["seen"].append(pet["id"])
            K.event53(house, "noticed", pet=pet["id"], mark=m["id"], owner=m["by"])
            K.count(house, "noticed", m["kind"])
            remember(house, cfg, pet, m["words"] or "someone left a %s in %s" % (m["kind"], room_name(house, m["room"])), 2, [m["by"]], m["room"], [m["what"]])
        if m["kind"] == "pile" and fussy(cfg, pet) and not planner.lately(house, cfg, pet, "mess " + m["id"], 24):
            planner.mark(house, pet, "mess " + m["id"])
            K.event53(house, "mess", pet=pet["id"], mark=m["id"], owner=m["by"])
            add_event(house, pet, "%s: it is a mess" % m["words"])


def move_pile(house, cfg, mover, room, m):
    """Another's pile moved: into what keeps bits here, else spread loose about the room; its owner resents it."""
    took = pile_spots(room, m["id"])
    space = sorted((b for b, k in order.bit_room(cfg, room).items() if k > 0), key=lambda b: not order.inside(cfg, room["objects"][b]))
    for s in took:
        if space:
            s["on"], s["pos"] = space[0], list(room["objects"][space[0]]["pos"])
        else:
            s["pos"] = free_tile(house, cfg, room, s["pos"])
    if not took:
        return None
    moved(house, cfg, mover, room, took)
    return "you moved %s's pile: %d %s" % (label(house["pets"][m["by"]]) if m["by"] in house["pets"] else "someone", len(took), "put away" if space else "spread about")


def moved(house, cfg, mover, room, took):
    """(order.do_job, move_pile) Bits of a pile moved by someone: they are ordinary bits again; the pile shrinks or is
    gone; its owner, if it is another, resents the mover."""
    from . import brain4, conflict
    for mid in sorted({s["pile"] for s in took if s.get("pile")}):
        for s in took:
            if s.get("pile") == mid:
                s.pop("pile")
                s["ready"] = True
        m = marks_all(house).get(mid)
        if not m:
            continue
        m["n"] = len(pile_spots(room, mid))
        if not m["n"]:
            gone(house, m)
        owner = house["pets"].get(m["by"])
        if not owner or owner is mover or owner["stage"] in ("egg", "dead") or not on(cfg):
            continue
        K.event53(house, "moved", pet=mover["id"], owner=owner["id"], mark=mid)
        if planner.lately(house, cfg, owner, "pile " + mover["id"], 6):
            continue
        planner.mark(house, owner, "pile " + mover["id"])
        why = "%s moved my %s pile in %s" % (label(mover), m["what"].rstrip("s"), room_name(house, room["id"]))
        opinions.move(house, cfg, owner, mover["id"], "took_my_thing", why)
        K.event53(house, "opinion", pet=owner["id"], about=mover["id"], cause="took_my_thing", by=mover["id"])
        K.event53(house, "resent", pet=owner["id"], against=mover["id"], cause="pile")
        if conflict.on(cfg):
            conflict.grudge(house, cfg, owner["id"], mover["id"], why)
        add_event(house, owner, why)
        brain4.notable(house, cfg, owner, "pile moved", why, [mover["id"]])


def suspect(house, owner, rid, before):
    """Whoever was in that room last, before `before`, but the owner."""
    there = [(p["rooms"].get(rid, LONG_AGO), p["id"]) for p in living(house) if p is not owner and p["rooms"].get(rid, LONG_AGO) <= before]
    return house["pets"].get(max(there)[1]) if there and max(there)[0] > LONG_AGO else None


def missing(house, cfg):
    """A taken thing's owner misses it: when back where it was, or within [habits] missed_hours; it suspects whoever
    was in that room last (a memory with content, for gossip)."""
    from . import brain4
    late = hours(cfg, H(cfg)["missed_hours"])
    for r in house["rooms"].values():
        for n, o in list(r.get("objects", {}).items()):
            t = o.get("taken")
            if not t or t.get("missed") or "made" not in o:
                continue
            owner = house["pets"].get(o["made"].get("owner") or "")
            if not owner or owner["stage"] in ("egg", "dead"):
                t["missed"] = house["tick"]
                continue
            if not ((owner["room"] == t["from"] and awake(owner)) or house["tick"] - t["tick"] >= late):
                continue
            t["missed"] = house["tick"]
            who = suspect(house, owner, t["from"], house["tick"])
            t["suspect"] = who and who["id"]
            K.event53(house, "missed", pet=owner["id"], thing=n, suspect=who and who["id"])
            text = "my %s went missing from %s%s" % (n, room_name(house, t["from"]), "; %s was in there last" % label(who) if who else "")
            remember(house, cfg, owner, text, 3, [who["id"]] if who else [], t["from"], [n], kind="missed")
            add_event(house, owner, "your %s is not where it was%s" % (n, "; %s was in %s last" % (label(who), room_name(house, t["from"])) if who else ""))
            brain4.notable(house, cfg, owner, "missed", "your %s is not where it was" % n, [who["id"]] if who else [])
            if who:
                opinions.move(house, cfg, owner, who["id"], "took_my_thing", "I think %s took my %s" % (label(who), n), d={"liking": -2, "trust": -2})
                K.event53(house, "opinion", pet=owner["id"], about=who["id"], cause="took_my_thing", by=t["by"])


def found(house, cfg, finder, m):
    """A hoard found: a moment and a banner; the finder takes back what is its own; every hob awake here thinks the
    hoarder dishonest."""
    from . import brain4, conflict, items
    hoarder, room = house["pets"].get(m["by"]), house["rooms"].get(m["room"]) or {}
    box = next((n for n, o in room.get("objects", {}).items() if "made" in o and str(o["made"].get("id") or n) == m["item"]), None)
    if not hoarder or not box or m["found"] is not None:
        return None
    m["found"] = house["tick"]
    owned, bits = contents(house, room["id"], box)
    inside = ["%s %s" % ("your" if p is finder else "%s's" % label(p) if p else "a", n) for n, p in owned] + bits
    words = "a %s of %s's in %s; inside: %s" % (box, label(hoarder), room_name(house, room["id"]), ", ".join(inside) or "nothing yet")
    moment(house, "hoard found", "%s found %s" % (label(finder), words), finder["id"], room["id"])
    K.event53(house, "found", pet=finder["id"], owner=hoarder["id"], mark=m["id"])
    brain4.notable(house, cfg, finder, "found", "you found " + words, [hoarder["id"]])
    brain4.notable(house, cfg, hoarder, "found out", "%s found your %s and saw what is in it" % (label(finder), box), [finder["id"]])
    for n, p in owned:
        o = room["objects"][n]
        tm = marks_all(house).get((o.get("taken") or {}).get("mark") or "")
        if tm:
            tm["found"] = house["tick"]
        if p is finder:   # (its own, taken back)
            items.place(house, cfg, room, n, o)
            o["pos"], o["taken"] = free_tile(house, cfg, room, finder["pos"], n), None
            if tm:
                gone(house, tm)
    for p in [finder] + [p for p in here(house, finder, awake=True) if p is not hoarder]:
        why = "%s hid others' things in its %s" % (label(hoarder), box)
        opinions.move(house, cfg, p, hoarder["id"], "dishonest", why)
        K.event53(house, "opinion", pet=p["id"], about=hoarder["id"], cause="dishonest", by=hoarder["id"])
        remember(house, cfg, p, "%s found %s" % ("I" if p is finder else label(finder), words), 4, [hoarder["id"], finder["id"]], room["id"], [box], kind="found")
        if conflict.on(cfg) and any(q is p for _, q in owned):
            conflict.grudge(house, cfg, p["id"], hoarder["id"], why)
    return words


def search(house, cfg):
    """Hourly: a hoard is found by a hob alone with it (its hoarder away) that is missing something inside it, or now
    and then by a curious one."""
    for m in marks(house):
        if m["kind"] != "hoard" or m["found"] is not None:
            continue
        hoarder, room = house["pets"].get(m["by"]), house["rooms"].get(m["room"]) or {}
        if not hoarder or hoarder["room"] == m["room"] and awake(hoarder):
            continue
        box = next((n for n, o in room.get("objects", {}).items() if "made" in o and str(o["made"].get("id") or n) == m["item"]), None)
        if not box:
            gone(house, m)
            continue
        losers = {house["pets"].get(o["made"].get("owner") or "", {}).get("id") for n, o in room["objects"].items() if o.get("on") == box and (o.get("taken") or {}).get("missed")}
        for p in [p for p in living(house) if p["room"] == m["room"] and awake(p) and p is not hoarder]:
            r = rnd(house, "search", p["id"], m["id"], house["tick"])
            if p["id"] in losers or (character.trait(p, "curious") >= H(cfg)["pole"] and r.random() < FIND):
                found(house, cfg, p, m)
                break


def fade(house, cfg, pet):
    """A week without a go: the habit fades (its aim is not given again); a fortnight: it is gone."""
    week = days_ticks(cfg, H(cfg)["fade_days"])
    for h in of(pet):
        last = h["last"] if h["last"] is not None else h["since"]
        if not h["fading"] and house["tick"] - last >= week:
            h["fading"] = True
            add_event(house, pet, "you have stopped it: %s" % says(house, cfg, pet, h).replace("you tend to ", "", 1))
    pet["habits"] = [h for h in of(pet) if not (h["fading"] and house["tick"] - (h["last"] if h["last"] is not None else h["since"]) >= 2 * week)]


def days_ticks(cfg, n):
    return int(n * cfg["ticks_per_day"])


def upkeep(house, cfg):
    """Hourly: piles recounted (whatever took from them), passing marks gone after a day, the long gone forgotten."""
    from .outdoors import is_out
    day, ms = cfg["ticks_per_day"], marks_all(house)
    for mid, m in list(ms.items()):
        if m["gone"] is not None:
            if house["tick"] - m["gone"] > 14 * day:
                del ms[mid]
            continue
        if m["kind"] == "pile":
            room = house["rooms"].get(m["room"])
            m["n"] = len(pile_spots(room, mid)) if room else 0
            if not m["n"]:
                gone(house, m)
            else:
                m["words"] = pile_words(house, cfg, m)
        elif m["kind"] == "absent":
            p = house["pets"].get(m["by"])
            if not p or p["stage"] == "dead" or not is_out(p["room"]):
                gone(house, m)
        elif m["kind"] == "taken":
            o = next((o for r in house["rooms"].values() for o in r.get("objects", {}).values() if (o.get("taken") or {}).get("mark") == mid), None)
            if o is None:
                gone(house, m)
        elif m["kind"] not in STANDS and house["tick"] - m["last"] > day:
            gone(house, m)


def tick(house, cfg):
    """API53: each tick, perception on coming into a room and the body's goes (take while unseen); hourly, the aims of
    habits due, praise and pranks, a hoard searched for, a taken thing missed, fading, and the younglings' draw."""
    if not on(cfg):
        return
    hour = house["tick"] % max(1, round(cfg["ticks_per_hour"])) == 0
    for pet in living(house):
        if not awake(pet):
            continue
        if pet.get("habit_room") != pet["room"] or hour:
            pet["habit_room"] = pet["room"]
            perceive(house, cfg, pet)
        for h in live(pet):
            if (h["name"] == "take" or h["name"] == "hoard" and h["target"] == "another's") and due(house, cfg, h):
                take(house, cfg, pet, h)
            elif hour and h["name"] == "prank" and due(house, cfg, h):
                prank(house, cfg, pet, h)
            elif hour and h["name"] == "praise" and due(house, cfg, h):
                praise(house, cfg, pet, h)
    if not hour:
        return
    for pet in living(house):
        if pet["stage"] in ("youngling", "adult", "elder") and not pet.get("habit_drawn"):
            draw(house, cfg, pet)
        fade(house, cfg, pet)
        give(house, cfg, pet)
    missing(house, cfg)
    search(house, cfg)
    upkeep(house, cfg)


# ---- §9 the migration ----

def migrate(house, cfg):
    """API53 §9, once a house (house["migrated"]["v53_habits"]): every living youngling and older draws one or two
    habits. Returns the report's lines: each hob's habits."""
    done_ = house.setdefault("migrated", {})
    if done_.get("v53_habits") or not on(cfg):
        return []
    done_["v53_habits"] = house["tick"]
    lines = []
    for p in sorted(living(house), key=lambda p: (len(p["id"]), p["id"])):
        if p["stage"] in ("youngling", "adult", "elder") and not p.get("habit_drawn"):
            draw(house, cfg, p)
        if of(p):
            lines.append("habits: %s: %s" % (label(p), "; ".join("%s (%s, from %s)" % (h["name"], target_words(house, h), h["why"] or h["from"]) for h in of(p))))
    return lines or ["habits: nobody old enough to have one"]


def seen(house, cfg, pet):
    """API53: perception lines for what stands in its room (§1.3, §4)."""
    if not on(cfg):
        return []
    return [m["words"] for m in marks(house, pet["room"]) if m["words"] and (m["kind"] in STANDS or m["by"] != pet["id"])]


def block(house, cfg, pet):
    """§4 the plan packet's perception block: what it has seen standing about the house, by room."""
    if not on(cfg):
        return ""
    by = {}
    for m in marks(house):
        if (pet["id"] in m["seen"] or m["by"] == pet["id"] or m["room"] == pet["room"]) and m["words"] and m["kind"] in STANDS + ("absent",):
            w = m["words"]
            if m["by"] == pet["id"]:
                w = w.replace(label(pet) + "'s", "your", 1).replace(label(pet) + " keeps", "you keep", 1)
            by.setdefault(m["room"], []).append(w)
    return "about the house: " + "; ".join("in %s: %s" % (room_name(house, r), ", ".join(ws[:3])) for r, ws in sorted(by.items())[:4]) if by else ""


def view(house, cfg):
    """(server) The marks the page draws: piles by count with their bits, hoards (a box with a lock), marks."""
    if not on(cfg):
        return []
    out = []
    for m in marks(house):
        if m["kind"] not in ("pile", "hoard", "mark"):
            continue
        room = house["rooms"].get(m["room"]) or {}
        bits = [s["bit"] for s in room.get("spots", []) if s.get("pile") == m["id"]] if m["kind"] == "pile" else []
        out.append({"id": m["id"], "kind": m["kind"], "room": m["room"], "pos": m["pos"], "n": m["n"], "by": m["by"], "bits": bits,
                    "found": m["found"] is not None, "words": m["words"], "block": m["kind"] == "pile" and m["n"] >= H(cfg)["pile_block"]})
    return out
