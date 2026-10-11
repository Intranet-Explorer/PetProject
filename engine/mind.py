"""What a pet perceives (SPEC-v3 §3, §7.1, §8): the packet a brain is given, in plain words.
No numbers, no coordinates, no counts of anything, and no sentence telling the pet what it is or what it is
like. Its temperament shows only in what is mentioned and how (§8.1). Alongside the text comes `ctx`: the
names the packet shows, so a brain's reply can be held to things that are really there."""
from . import actions, feel, life, physics, things
from .world import LONG_AGO, dist, here, neighbours, room_type

BUSY = {"observe": "watching the room", "look": "looking at something", "move": "walking", "go": "heading for a door",
        "speak": "speaking", "rest": "resting", "use": "using something", "gather": "picking something up",
        "drop": "putting something down", "make": "making something", "unmake": "taking something apart",
        "arrange": "moving something", "combine": "putting two things together", "paint": "painting", "teach": "teaching a thing",
        "give": "holding something out", "show": "showing something", "follow": "following someone", "nuzzle": "leaning close",
        "accept": "taking what was offered", "take": "taking something", "chase": "chasing", "tell": "telling something",
        "lay_egg": "laying an egg", "bequeath": "choosing what to leave", "write_belief": "thinking", "revise_belief": "thinking", "take_name": "taking a name"}
RECENT = 6          # how many earlier happenings are shown
# What is cut first when the packet is over its budget (§8.3), least needed first. Never cut: how it feels, what
# it notices, what is here, who is here, what just happened, what was said to it, its parent's words, what it can do.
CUT_ORDER = ["earlier", "rooms", "known", "told", "things", "sounds", "beliefs"]


def doing(house, pet):
    if pet["sleep"]:
        return "asleep"
    plan = pet["plan"]
    if not plan:
        return "standing still"
    step = plan["steps"][min(plan["i"], len(plan["steps"]) - 1)]
    target = step.get("target") or step.get("what")
    word = BUSY.get(step.get("type"), "busy")
    return "%s (the %s)" % (word, actions.norm(target)) if isinstance(target, str) and step["type"] in ("use", "look", "gather", "unmake", "take") else word


def collapse(lines):
    """Runs of the same happening become one line."""
    out = []
    for text in lines:
        if out and out[-1][0] == text:
            out[-1][1] += 1
        else:
            out.append([text, 1])
    return ["%s%s" % (t, " (twice)" if n == 2 else " (several times)" if n < 6 else " (many times)" if n > 1 else "") for t, n in out]


def sounds(house, cfg, pet):
    """What carries through the doors (§6.1, §7.1): sounds, never words."""
    out, tick = [], house["tick"]
    for d, rid in neighbours(house, pet["room"]).items():
        room = house["rooms"][rid]
        place = room["name"] if rid in pet["rooms"] else "behind the %s door" % d
        where = ("in %s" % place) if rid in pet["rooms"] else place
        others = [p for p in house["pets"].values() if p["room"] == rid and p["stage"] not in ("egg", "dead") and not p["sleep"]]
        if any(p["said"] and (tick - p["said"]["tick"]) * cfg["clock"]["tick_seconds"] <= 40 for p in others):
            out.append("you hear a voice %s" % where)
        elif others:
            out.append("you hear someone moving %s" % where)
        if room.get("sounding_until", 0) > tick:
            out.append("you hear something ringing %s" % where)
        if any(things.doing(cfg, o).get("loud") for o in things.made(room).values()):
            out.append("you hear something humming %s" % where)
        if any(c["room"] == rid and c["kind"] == "bird" and c["doing"].startswith("singing") for c in house["creatures"]):
            out.append("a bird is singing %s" % where)
    return out


def perceive(house, cfg, pet, mem):
    """Returns (the packet, ctx). The packet is the same in structure for every brain."""
    room, T, tick = house["rooms"][pet["room"]], pet["temper"], house["tick"]
    objs, me = room["objects"], pet["pos"]
    acting = physics.effects(house, cfg, pet)
    can = actions.allowed(house, cfg, pet, mem)
    others = here(house, pet)
    creatures = [c for c in house["creatures"] if c["room"] == room["id"]]
    eggs = [p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] == "egg"]
    lying = [p for p in house["pets"].values() if p["room"] == room["id"] and p["stage"] == "dead" and not p.get("buried")]

    # ---- what is here ----
    def thing_line(n, o):
        notes = []
        if "made" in o:
            notes.append(things.whose(house, pet, o))
            if o["made"].get("called"):
                notes.append("the visitor calls it " + o["made"]["called"])
            if o.get("state") in ("on", "off"):
                notes.append(o["state"])
            if o.get("active") and o["made"].get("behavior"):
                notes.append(o["made"]["behavior"]["do"].split(":")[0].replace("_", " ") + "ing")
        elif "memorial" not in o:
            fix = o.get("fix", {})
            state = o.get("state")
            if fix.get("plant"):
                state = "ripe" if o["state"] == "ripe" else None
            if "light" in fix and not physics.power_on(house):
                state = "dark"
            if state and state != "closed":
                notes.append(state)
        notes.append(feel.near_word(me, o["pos"]))
        return "%s (%s)" % (n, "; ".join(notes))

    seen = [thing_line(n, o) for n, o in sorted(objs.items(), key=lambda no: dist(me, no[1]["pos"]))]
    seen += ["%s egg (%s)" % ("your" if e["parent"] == pet["id"] else "an", feel.near_word(me, e["pos"])) for e in eggs]

    def other_line(p):
        said = p["said"] if p["said"] and (tick - p["said"]["tick"]) * cfg["clock"]["tick_seconds"] <= 60 else None
        return "%s (%s; %s; seems %s%s)" % (actions.handle(house, pet, p), feel.near_word(me, p["pos"]), doing(house, p),
                                           feel.seems(p), '; just said "%s"' % said["text"] if said else "")

    who = [other_line(p) for p in others] + ["%s lies still and does not move" % actions.handle(house, pet, p) for p in lying]
    who += ["a %s (%s; %s)" % (c["kind"], feel.near_word(me, c["pos"]), c["doing"]) for c in creatures]

    ready = [s for s in room["spots"] if s["ready"]]
    kinds = sorted({s["bit"] for s in ready})
    bits = ", ".join("%s (%s)" % (k, feel.near_word(me, min((s["pos"] for s in ready if s["bit"] == k), key=lambda t: dist(me, t))))
                     for k in kinds) or "nothing"
    space = cfg["make"]["carry"] - len(pet["carrying"])
    carry = (", ".join(pet["carrying"]) + ("; your arms are full" if space <= 0 else "")) if pet["carrying"] else "nothing"
    could = sorted({p for b in pet["carrying"] for p in cfg["house"]["bits"][b]["can"]})
    if could:
        carry += "; from this you could make something " + " or ".join(could)

    def door_line(d, rid):
        shut = house["shut"].get("%s|%s" % (room["id"], d), LONG_AGO) > tick
        if rid in pet["rooms"]:
            text = "to " + house["rooms"][rid]["name"]
        else:   # what comes under an untried door, and how a bold or a timid pet takes it (§8.1)
            hint = cfg["house"]["rooms"][room_type(house, rid)]["hint"]
            text = "you have not been through it; from under it comes %s%s" % (
                hint, ", and you want to know what is there" if T["bold"] > 0.6 else "" if T["bold"] > 0.4 else "; you are not sure about it")
        return "%s (%s%s)" % (d, text, "; it is stuck shut" if shut else "")

    doors = " · ".join(door_line(d, rid) for d, rid in room["doors"].items())

    # ---- what it notices: the feel of everything acting on it, plus what its temperament brings forward ----
    senses = physics.senses(house, cfg, pet, acting) if cfg["senses"]["enabled"] else []
    if T["playful"] > 0.6 and any("toy" in o.get("fix", {}) or things.prop(cfg, o).get("use", {}).get("curiosity") if "made" in o
                                  else "toy" in o.get("fix", {}) for o in objs.values()):
        senses.append("something here looks like it wants to be played with")
    unseen = [d for d, rid in room["doors"].items() if rid not in pet["rooms"]]
    if unseen and feel.level(pet, "curiosity") >= (2 if T["bold"] < 0.4 else 1):   # boredom points at the one thing here not yet tried
        senses.append("you wonder what is through the %s door" % unseen[0])
    if actions.offered(pet):
        senses.append("the visitor calls you %s; you could take the name" % pet["called"])

    # ---- what happened ----
    since = [e for t, e in pet["events"] if t > pet["seen"]]
    earlier = collapse([e for t, e in pet["events"] if t <= pet["seen"]])[-RECENT:]
    plan = pet["plan"]
    busy = "%s (not finished)" % plan["intention"] if plan else "nothing"
    offers = []
    for off in pet["offers"]:
        giver = house["pets"].get(off["from"])
        if giver and giver["room"] == pet["room"]:
            h = actions.handle(house, pet, giver)
            offers.append("%s is leaning toward you" % h if off["kind"] == "nuzzle" else "%s is holding out %s to you" % (h, off["what"]))

    # ---- what it carries in its head ----
    # Word for word while it is small, and for a day after last words are said; a grown pet meets them again only at
    # night (sleep.py). Awake it has what it made of them: its beliefs. (§5 Why: "what gets lost or distorted".)
    fresh = house["tick"] - cfg["ticks_per_day"]
    parent_words = [m for m in pet["told"] if m["kind"] in ("message", "last words") and (pet["stage"] in ("hatchling", "child") or (m["kind"] == "last words" and m["tick"] >= fresh))]
    tells = [m for m in pet["told"] if m["kind"] == "tell"][:3]
    beliefs = sorted(mem.active(), key=lambda b: -b["revised"])
    proj = pet["project"]
    project = "%s (started %s)" % (proj["text"], feel.ago(house, cfg, proj["since"])) if proj else "none yet; you can choose one when you sleep"
    mine_here = [n for n in things.mine(house, pet, room)]
    heirs = [n for n, o in things.made(room).items() if pet["id"] in (o["made"].get("heirloom") or {}).get("to", [])]

    far_heirs = ["%s (in %s)" % (n, r["name"]) for r in house["rooms"].values() if r["type"] and r["id"] != room["id"]
                 for n, o in things.made(r).items() if pet["id"] in (o["made"].get("heirloom") or {}).get("to", [])]

    def room_note(rid):
        r = house["rooms"][rid]
        way = next((d for d, x in room["doors"].items() if x == rid), None)
        found = pet["gathered"].get(rid)
        return r["name"] + (" (here)" if rid == room["id"] else " (through the %s door)" % way if way else "") + (
            ": you found %s there" % ", ".join(found) if found else "")

    def known_line(pid, line):
        p = house["pets"].get(pid)
        if not p:
            return None
        return "%s%s: %s" % (actions.handle(house, pet, p), ", who has died" if p["stage"] == "dead" else "", line)

    sections = {
        "time": "it is %s" % feel.when(house),
        "room": "you are in %s%s" % (room["name"], ": %s walls, %s floor" % (room["paint"]["wall"], room["paint"]["floor"]) if room["paint"]["wall"] else ""),
        "feel": "you feel: " + feel.feelings(pet),
        "senses": "you notice: " + ("; ".join(senses) or "nothing in particular"),
        "here": "here: " + " · ".join(seen),
        "who": "with you: " + (" · ".join(who) or "nobody"),
        "bits": "lying about: " + bits,
        "carry": "you carry: " + carry,
        "doors": "this room's doors: " + doors,
        "sounds": "from next door: " + "; ".join(sounds(house, cfg, pet)),
        "doing": "you are doing: " + busy,
        "since": "since you last thought:" + ("".join("\n  " + e for e in since) or " nothing"),
        "earlier": "earlier: " + "  |  ".join(earlier),
        "said": "said to you: " + "; ".join(pet["inbox"]),
        "offers": "offered to you: " + "; ".join(offers),
        "project": "your project: " + project,
        "beliefs": "your beliefs:" + ("".join("\n  %s (%s): %s" % (b["id"], b.get("source", "lived"), b["statement"]) for b in beliefs) or " none yet"),
        "parent": "".join("%s your %s %s you: \"%s\"\n" % ("what" if m["kind"] == "message" else "the last thing", m["who"],
                                                          "told" if m["kind"] == "message" else "said to", m["text"]) for m in parent_words).rstrip("\n"),
        "told": "".join('what %s told you: "%s"\n' % (m["who"], m["text"]) for m in tells).rstrip("\n"),
        "things": "your things here: " + "; ".join("%s (for: %s)" % (n, objs[n]["made"]["recipe"]["purpose"]) for n in dict.fromkeys(mine_here + heirs)) + (
            "" if not far_heirs else "%sleft to you, elsewhere: %s" % ("; " if mine_here or heirs else "", ", ".join(far_heirs))),
        "rooms": "rooms you know: " + "; ".join(room_note(r) for r in pet["rooms"]),
        "known": "who you know: " + "; ".join(filter(None, (known_line(p, l) for p, l in pet["known"].items()))),
        "can": "you can: " + ", ".join(can),
    }
    empty = {"sounds": "from next door: ", "earlier": "earlier: ", "said": "said to you: ", "offers": "offered to you: ", "parent": "",
             "told": "", "things": "your things here: ", "known": "who you know: "}
    for k, blank in empty.items():
        if sections[k] == blank:
            del sections[k]
    cut = []
    for k in CUT_ORDER:   # the budget (§8.3)
        if sum(len(s) + 1 for s in sections.values()) <= cfg["packet"]["max_chars"]:
            break
        if k == "beliefs" and len(beliefs) > 8:
            sections[k] = "your beliefs:" + "".join("\n  %s (%s): %s" % (b["id"], b.get("source", "lived"), b["statement"]) for b in beliefs[:8])
            cut.append(k)
        elif k in sections and k != "beliefs":
            del sections[k]
            cut.append(k)
    text = "\n".join(sections.values()) + "\n"

    most = min(cfg["make"]["parts"].get(pet["stage"], 0), cfg["make"]["carry"])
    reach = sorted({p for b in pet["carrying"] + kinds for p in cfg["house"]["bits"][b]["can"]})
    free = actions.changeable(house, pet, room)
    ctx = {
        "pet": pet["id"], "stage": pet["stage"], "allowed": can, "temperature": round(0.5 + 0.5 * T["playful"], 2),
        "things": list(objs), "pets": [actions.handle(house, pet, p) for p in others],
        "awake": [actions.handle(house, pet, p) for p in others if not p["sleep"]],
        "creatures": [c["kind"] for c in creatures], "bits": kinds, "carrying": list(dict.fromkeys(pet["carrying"])),
        "doors": list(room["doors"]), "eggs": bool(eggs), "mine": mine_here, "free": free,
        "theirs": [n for n in actions.others_things(house, pet, room) if not objs[n]["made"].get("heirloom")],
        "leave": list(dict.fromkeys(mine_here + heirs)),
        "movable": [n for n, o in objs.items() if actions.movable(cfg, o)] + (["egg"] if any(e["parent"] == pet["id"] for e in eggs) else []),
        "beliefs": [b["id"] for b in beliefs], "make": [most, reach],
        "materials": sorted({objs[n]["made"]["recipe"]["material"] for n in free}),
        "offers": [actions.handle(house, pet, house["pets"][o["from"]]) for o in pet["offers"]
                   if o["from"] in house["pets"] and house["pets"][o["from"]]["room"] == pet["room"]],
        "tellers": sorted({m["who"] for m in pet["told"]}), "kids": [house["pets"][c]["name"] for c in pet["children"]
                                                                    if house["pets"].get(c, {}).get("name") and house["pets"][c]["stage"] != "dead"],
        "cut": cut, "chars": len(text),
    }
    return text, ctx


def describe(house, pet):
    """Where it was and what was so, in a few words, for the day's journal that sleep reads back."""
    room = house["rooms"][pet["room"]]
    states = ", ".join("%s %s" % (n, o["state"]) for n, o in room["objects"].items() if o.get("state") in ("on", "off", "playing", "open"))
    near = [n for n, o in room["objects"].items() if dist(pet["pos"], o["pos"]) <= 1]
    return "%s, %s%s%s" % (room["name"], house["clock"]["phase"], "; " + states if states else "", "; by the " + near[0] if near else "")
