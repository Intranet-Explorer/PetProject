"""The body (SPEC-v3.3 §1): what a pet does by itself between thoughts, with no model asked. Each tick a pet that
is not carrying out something it decided picks the best activity for the moment from activities.toml and does it:
short, visible and real (tidying moves things, eating empties the bowl). The mind still decides everything that
belongs to the pet's story; the body only fills the time in between, in character.

SPEC-v3.4 §1: a body goes places and handles things. A stretch, a hum or a look about is filler (a fidget: one
tick, on the spot, between two activities), never the thing it chose to do; a thing put away or brought to
someone is carried there; being with someone is doing what they do; and a mind set on rest does not hold a body
that is not tired."""
from . import actions, craft, feel, order, songs, story, things, wants
from . import season
from . import build
from . import machine
from . import hub
from .world import LONG_AGO, STAGES, add_event, beside, dist, free_tile, here, label, relation, rnd, ticks

URGENT = {"visitor", "woke", "hatched", "low", "spoken", "event"}   # what stops it in its tracks (as it hurries a thought)
# what a finished activity is to whoever is watching: the same words the steps a mind decides use, where there is one
ACT = {"inspect": "look", "play": "use", "eat": "eat", "stone": "use", "go": "go", "tidy": "put_away", "gather": "gather", "fiddle": "fiddle",
       "tend": "tend", "dance": "dance", "babble": "babble", "nap": "nap", "listen": "listen", "watch": "watch",
       "seat": "use", "take out": "take_out", "bring": "show"}
TO = {"soak": "to the water", "warm": "to the warmth", "melt": "to the heat", "dry": "up into the dry air", "press": "over to something heavy",
      "weave": "to the bench", "carve": "to the bench", "grind": "onto the stone floor", "plant": "to the earth"}   # where a bit is carried to be tried (v3.4 §3)
KEEPS_UP = ("follow", "tail")   # done on the move: it keeps after whoever it is for as long as it lasts
TOGETHER = ("sing", "dance")    # besides whatever handles a thing: done with someone when they are doing it too
COUNT = ["", "", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def state(pet):
    return pet.setdefault("body", {"now": None, "recent": [], "since": [], "habits": {}, "idle": [], "n": 0})


def phase(house):
    c = house["clock"]
    return "morning" if c["morning"] else c["phase"]


def music(house, pet):
    """Is there music where it is: the visitor's, or something ringing in the room?"""
    dj = (house.get("dj") or {}).get("music")
    return bool(dj and dj.get("mood") and dj["scope"] in ("house", pet["room"])) or house["rooms"][pet["room"]].get("sounding_until", 0) > house["tick"] \
        or any(o.get("fix", {}).get("radio") and o.get("state") == "on" for o in house["rooms"][pet["room"]]["objects"].values())   # (SPEC-v3.5.1 §5: or the radio)


def anchor(house, pet):
    """Where its mind wants it to be near, if anywhere: the thing or the one its focus names, when they are in this room."""
    f = pet.get("focus") or {}
    if f.get("type") not in ("stay near", "tend", "make"):   # (not "be with": that is doing what the other does, not standing by them; v3.4 §1)
        return None
    objs = house["rooms"][pet["room"]]["objects"]
    if f.get("type") == "make" and laid_out(pet):   # its bits are laid out: it stays by them
        return next((o["pos"] for o in objs.values() if o.get("fix", {}).get("bench")), pet["pos"])
    o, who = objs.get(f.get("what") or ""), house["pets"].get(f.get("who") or "")
    return o["pos"] if o else who["pos"] if who and who["room"] == pet["room"] and who["stage"] not in ("egg", "dead") else None


def focus_who(pet):
    return (pet.get("focus") or {}).get("who")


def laid_out(pet):
    """Has it laid out the very bits it is carrying? (Then it is ready to make, and does not lay them out again.)"""
    return bool(pet["carrying"]) and state(pet).get("laid") == pet["carrying"]


def out_of_sight(cfg, room, o):
    """Put away inside something (a chest, a crate): not a thing to play with or look at until it is taken out."""
    store = room["objects"].get(o.get("on") or "")
    return bool(store) and bool(store.get("fix", {}).get("inside") or cfg["kinds"].get(store.get("made", {}).get("recipe", {}).get("kind"), {}).get("inside"))


def kin_here(house, pet):
    return [p for p in here(house, pet) if relation(house, pet, p)]


def way_to(house, pet, targets):
    """The door from where it is toward the nearest of these rooms, through rooms it knows: a door, or None."""
    rooms, seen, queue = house["rooms"], {pet["room"]}, [(pet["room"], None)]
    while queue and targets:
        rid, first = queue.pop(0)
        if first and rid in targets:
            return first
        for d, to in rooms[rid]["doors"].items():
            if to in pet["rooms"] and to not in seen and rooms[to]["type"]:
                seen.add(to)
                queue.append((to, first or d))
    return None


def handled_lately(house, cfg, pet):
    """How many different things it has had its paws on in the last while."""
    return len({th for tk, th in state(pet).get("handled", []) if house["tick"] - tk < cfg["body"]["handle_ticks"]})


def tired(pet):
    return feel.level(pet, "energy") >= 2


def minded(pet):
    """What its mind is about, as far as its body goes: a mind set on rest does not hold a body that is not tired (v3.4 §1)."""
    f = pet.get("focus") or {}
    return None if f.get("type") == "rest" and not tired(pet) else f.get("type")


def targets(house, cfg, pet, mem, name, A):
    """Everything this activity could be done with right now: [{what/who, goal, ...}]. Empty if it cannot be done."""
    room, do, me, r = house["rooms"][pet["room"]], A["do"], pet["pos"], rnd(house, "body-t", pet["id"], house["tick"], name)
    objs, focus = room["objects"], pet.get("focus") or {}
    near = lambda pos: None if dist(me, pos) <= 1 else beside(cfg, pos, me)
    if do == "self":
        return [{}]
    if do == "build":   # SPEC-v3.5 §4: carrying to a thing being built, working on it, mending it, binding a hammer, painting
        return build.targets(house, cfg, pet, A, near)
    if do in machine.DOS:   # SPEC-v3.5 §4.3: at the vending machine
        return machine.targets(house, cfg, pet, A, near)
    L, W = wants.lean(house, cfg, pet) if do in ("go", "gather", "tail", "watch", "place", "try", "play", "inspect", "eat") else None, cfg["body"]["want"]   # SPEC-v3.4 §2.1: its body leans toward what serves its wants
    if do == "wander":   # somewhere a few steps off: the farthest of a few tries (or near what its mind is on)
        at = anchor(house, pet)
        tries = [[r.randrange(1, cfg["W"] - 1), r.randrange(1, cfg["H"] - 1)] for _ in range(4)] if not at else \
            [[min(cfg["W"] - 2, max(1, at[0] + r.randint(-2, 2))), min(cfg["H"] - 2, max(1, at[1] + r.randint(-2, 2)))] for _ in range(4)]
        return [{"goal": free_tile(house, cfg, room, max(tries, key=lambda t: min(dist(me, t), 6)))}]
    if do in ("doorway", "peek", "go"):
        out, mess = [], order.way(house, cfg, pet) if do == "go" else None
        # may a mess elsewhere draw it out of this room? Not out of a mess, not from beside what its mind keeps it by, not when it is resting tired
        trip = state(pet).get("trip") or [None, True]   # [the world day it last set off for a mess, has it got there]: one such trip a day
        if do == "go" and trip[0] == house["clock"]["day"] and not trip[1] and (room.get("mess") == 2 or not mess):
            trip[1] = True   # it stands in a mess, or the one it set off for has been cleared: that was today's trip (it used to stay "under way" all day, free to set off again)
        under_way = trip[0] == house["clock"]["day"] and not trip[1]
        drawn = bool(mess) and room.get("mess", 0) < 2 and not anchor(house, pet) and (focus.get("type") != "rest" or feel.level(pet, "energy") < 2) \
            and (trip[0] != house["clock"]["day"] or under_way)
        toward = way_to(house, pet, L["rooms"]) if do == "go" else None
        for d, rid in room["doors"].items():
            stuck = house["shut"].get("%s|%s" % (room["id"], d), LONG_AGO) > house["tick"]
            to, been = house["rooms"][rid], rid in pet["rooms"]
            if do == "go" and not stuck and (d in L["doors"] or d == toward) and not anchor(house, pet) and not tired(pet) and handled_lately(house, cfg, pet) >= 3:   # (not while it has had its paws on little: v3.4 §0 comes first)
                # a door it wants to know the other side of (the one way a body goes where it has never been), or the way to where a want takes it
                out.append({"what": d, "goal": list(house["door_tiles"][d]), "bonus": W})
            elif do == "doorway" and not been:
                out.append({"what": d, "goal": list(house["door_tiles"][d]), "bonus": 0.5})
            elif do == "doorway":
                out.append({"what": d, "goal": list(house["door_tiles"][d])})
            elif do == "peek" and to["type"] and not stuck:
                out.append({"what": to["name"], "door": d, "goal": list(house["door_tiles"][d])})
            elif do == "go" and not stuck and to["type"] and been:   # only into rooms it knows: finding a room is its mind's to decide
                want = house["pets"].get(focus.get("who") or "")
                kin = [p for p in house["pets"].values() if p["room"] == rid and p["stage"] not in ("egg", "dead") and not p["sleep"] and relation(house, pet, p)]
                if focus.get("type") == "be with" and want and want["room"] == rid:
                    out.append({"what": d, "goal": list(house["door_tiles"][d]), "bonus": 2.5})
                elif focus.get("type") == "tidy" and d == mess and not order.job(house, cfg, pet, room):
                    out.append({"what": d, "goal": list(house["door_tiles"][d]), "bonus": 2.0})   # this room is done and there is a mess it knows of: tidying moves on, door by door
                elif (minded(pet) in (None, "explore", "play", "project") or (focus.get("type") == "be with" and not (want and want["room"] == room["id"])) or (d == mess and drawn)
                      or (state(pet).get("bare") and not anchor(house, pet))) \
                        and ((under_way and d == mess) or state(pet).get("bare") or house["tick"] - pet["rooms"].get(room["id"], LONG_AGO) >= ticks(cfg, cfg["body"]["go_again_seconds"])):
                    # (it stays where its mind put it a good while, and it never walks out on someone or something its mind
                    # keeps it by. Otherwise a mess it knows of draws it as one here would, the orderly most)
                    out.append({"what": d, "goal": list(house["door_tiles"][d]),
                                "bonus": (0.6 if kin and not kin_here(house, pet) else 0.0) + (0.8 if focus.get("type") == "explore" else 0.0)
                                + (cfg["body"]["mess_pull"] * 2 * (0.4 + 1.2 * pet["temper"].get("orderly", 0.5)) if d == mess and drawn else 0.0),
                                "trip": d == mess and drawn})
        return out
    if do == "inspect":
        seen = lambda n: pet["times"].get("look " + n, 0)
        names = sorted((n for n in objs if not out_of_sight(cfg, room, objs[n])), key=lambda n: (seen(n), dist(me, objs[n]["pos"])))[:3]
        names = [n for n in L["look"] if n in objs and not out_of_sight(cfg, room, objs[n])][:1] + [n for n in names if n not in L["look"]]   # what it wants a closer look at, first
        return [{"what": n, "goal": near(objs[n]["pos"]), "bonus": W if n in L["look"] else 0.4 if not seen(n) else 0.0} for n in names]
    if do == "fiddle":
        mine = [n for n, o in things.made(room).items() if things.free_to_change(house, pet, o) and not out_of_sight(cfg, room, o)] \
            + [n for n, o in objs.items() if o.get("fix", {}).get("movable")]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in sorted(mine, key=lambda n: dist(me, objs[n]["pos"]))[:2]]
    if do == "play":
        toys = [n for n, o in objs.items() if "toy" in o.get("fix", {})]
        toys += [n for n, o in things.made(room).items() if things.prop(cfg, o).get("use", {}).get("curiosity") and not things.prop(cfg, o).get("food")
                 and things.free_to_change(house, pet, o) and not out_of_sight(cfg, room, o)]
        ball = lambda n: bool(L["play"]) and (n == "ball" or objs[n].get("made", {}).get("recipe", {}).get("kind") == "ball")   # a game it wants with someone: the ball first
        return [{"what": n, "goal": near(objs[n]["pos"]), "bonus": W if ball(n) else 0.0} for n in sorted(toys, key=lambda n: (not ball(n), pet["times"].get("body play " + n, 0), dist(me, objs[n]["pos"])))[:2]]
    if do == "window":
        return [{"what": n, "goal": near([o["pos"][0], max(o["pos"][1], 0)])} for n, o in objs.items() if o.get("fix", {}).get("window")][:1]
    if do == "nap":
        if feel.level(pet, "energy") < 1 or not (tired(pet) or focus.get("type") == "rest"):
            return []   # not tired; or only a bit, and not minded to rest
        beds = [o["pos"] for o in objs.values() if "rest" in o.get("fix", {}) or o.get("fix", {}).get("cozy")]
        return [{"goal": near(min(beds, key=lambda t: dist(me, t))) if beds else None}]
    if do == "eat":
        ripe = [n for n in L["pick"] if n in objs and (objs[n].get("planted") or {}).get("grow", 0) >= 1]   # what it wants to pick: hungry or not (13 October 2026)
        if ripe:
            return [{"what": ripe[0], "goal": near(objs[ripe[0]]["pos"]), "bonus": W}]
        if feel.level(pet, "energy") < 2 or (house["tick"] - pet.get("last_eat", LONG_AGO)) * cfg["clock"]["tick_seconds"] <= cfg["effects"]["double_feed_seconds"]:
            return []
        # what the family grew before the bowl the visitor fills (SPEC-v3.4 §3.5)
        food = [n for n, o in objs.items() if o.get("planted") and o["planted"]["grow"] >= 1 and not o["planted"].get("wilted")] \
            + [n for n, o in objs.items() if "meal" in o.get("fix", {}) and o.get("servings")]
        return [{"what": n, "goal": near(objs[n]["pos"]), "bonus": 0.5 if objs[n].get("planted") else 0.0} for n in food[:1]]
    if do == "tidy":
        job = season.job(house, cfg, pet, room) or order.job(house, cfg, pet, room)   # the worse the mess, the more it pulls, on the orderly most of all (SPEC-v3.5 §5: food it wants put by comes first)
        if not job or any((state(p)["now"] or {}).get("do") == "tidy" and state(p)["now"].get("what") == job["what"] for p in here(house, pet)):
            return []   # nothing to put away, or someone is already putting that very thing away
        pull = order.clutter(house, cfg, room) * cfg["body"]["mess_pull"] * (0.4 + 1.2 * pet["temper"].get("orderly", 0.5))
        place = objs[job["job"][3]]["pos"] if job["job"][2] == "on" else job["job"][3]   # the shelf, the place on the wall or the tile it goes to: it is carried there
        return [{"what": job["what"], "job": job["job"], "goal": near(job["pos"]), "to": None if dist(job["pos"], place) <= 1 else beside(cfg, place, job["pos"]), "bonus": pull + job.get("bonus", 0.0)}]
    if do == "seat":   # something to sit or lie on that nobody is on: it goes and settles on it
        S = cfg["body"]["seats"]
        seats = [n for n, o in objs.items() if ("rest" in o.get("fix", {}) or "soft" in o.get("fix", {}) or n in S or o.get("made", {}).get("recipe", {}).get("kind") in S)
                 and not o.get("wall") and not o.get("on") and not any(p["pos"] == o["pos"] for p in here(house, pet))]
        return [{"what": n, "goal": None if me == objs[n]["pos"] else list(objs[n]["pos"])} for n in sorted(seats, key=lambda n: (pet["times"].get("body seat " + n, 0), dist(me, objs[n]["pos"])))[:2]]
    if do == "take out":   # something put away that it may take: out it comes, is looked over there, and goes back where it was (13 October 2026: left out, sixteen such things lay about one room); not in a mess, and not what has only just gone in
        fresh = house["tick"] - ticks(cfg, cfg["order"]["just_out_seconds"])
        kept = [n for n, o in things.made(room).items() if o.get("on") in objs and order.may_move(house, pet, o) and not o["made"].get("heirloom") and o.get("kept", 0) < fresh]
        if room.get("mess", 0) >= 2 or not kept:
            return []
        n = min(kept, key=lambda n: (pet["times"].get("look " + n, 0), dist(me, objs[n]["pos"])))
        return [{"what": n, "goal": near(objs[n]["pos"])}]
    if do == "bring":   # one of its own things, carried over to someone it is fond of
        kin = [p for p in kin_here(house, pet) if not p["sleep"]]
        mine = [n for n, o in things.on_floor(room).items() if o["made"]["owner"] == pet["id"] and not o["made"].get("heirloom") and not order.cap(cfg, o) and not things.prop(cfg, o).get("fixed")]
        out = []
        for p in sorted(kin, key=lambda p: (focus.get("who") != p["id"], dist(me, p["pos"])))[:1]:
            far = [n for n in mine if dist(objs[n]["pos"], p["pos"]) > 2]
            if far:
                n = min(far, key=lambda n: (pet["times"].get("body bring " + n, 0), dist(me, objs[n]["pos"])))
                out.append({"what": n, "who": p["id"], "goal": near(objs[n]["pos"]), "to": beside(cfg, p["pos"], objs[n]["pos"]), "bonus": 1.0 if focus.get("who") == p["id"] else 0.0})
        return out
    if do == "tail":
        return [{"what": c["kind"], "creature": c["id"], "goal": None if dist(me, c["pos"]) <= 1 else beside(cfg, c["pos"], me), "bonus": W if c["kind"] in L["creatures"] else 0.0}
                for c in sorted(house["creatures"], key=lambda c: c["kind"] not in L["creatures"]) if c["room"] == room["id"]][:1]
    making = focus.get("type") == "make" and not laid_out(pet)   # its mind is on making, and it is not ready yet
    bench = next((n for n, o in objs.items() if o.get("fix", {}).get("bench")), None)
    if do == "gather":
        wanted = [s for s in room["spots"] if s["ready"] and not s.get("on") and s["bit"] in L["gather"]]   # a bit one of its wants is about: picked up whatever else it carries
        if wanted:   # (with its arms full it puts something else down first)
            s = min(wanted, key=lambda s: dist(me, s["pos"]))
            return [{"what": s["bit"], "goal": near(s["pos"]), "bonus": W, "want": "swap" if len(pet["carrying"]) >= cfg["make"]["carry"] else None}]
        if len(pet["carrying"]) >= (cfg["body"]["make_bits"] if making else cfg["make"]["carry"] if focus.get("type") == "project" else 1):
            return []
        spots = sorted((s for s in room["spots"] if s["ready"] and not s.get("on")), key=lambda s: dist(me, s["pos"]))
        return [{"what": s["bit"], "goal": near(s["pos"]), "bonus": cfg["body"]["make_pull"] if making else 0.0} for s in spots[:1]]
    if do == "place":   # a bit it wants to try something on, carried to where that can be tried; there its mind is told, once, and thinks sooner
        P, slot = (L["ask"], "booked") if A.get("book") else (L["place"], "placed")   # (the book and the place a thing is tried are gone to separately)
        if not P or state(pet).get(slot) == [P[2], room["id"]] or (A.get("book") and bool(A.get("elder")) != (len(P) == 4)):
            return []
        how, bit, key = P[:3]
        if how == "ask" and len(P) == 4:   # too young to read: it goes over to an elder, to ask out loud
            who = house["pets"][P[3]]
            return [{"who": who["id"], "where": "ask " + bit, "want": key, "goal": near(who["pos"]), "bonus": W * 1.5}] if who["room"] == room["id"] else []
        if how == "ask":   # something it wants to know, and the book is here: it goes over to it
            name, at = hub.book_at(house, cfg, room, pet)   # SPEC-v3.5.1 §3: a screen nobody else is at, or the heavy book
            return [{"what": name, "where": "ask " + bit, "want": key, "goal": near(at), "bonus": W * 1.5}] if at else []
        at = craft.place(house, cfg, room, how)
        return [{"what": bit, "where": TO[how], "want": key, "how": how, "goal": near(at[1]) if at[1] else None, "bonus": W * 1.5}]
    if do == "try":   # it has stood where the thing can be tried long enough for its mind to take it up, and its mind has not: its paws try it
        b = state(pet)
        P, slot, done = (L["ask"], "booked", "asked_at") if A.get("book") else (L["place"], "placed", "tried_at")
        if not P or len(P) == 4 or b.get(slot) != [P[2], room["id"]] or b.get(done) == P[2] \
                or house["tick"] - b.get(slot + "_at", house["tick"]) < ticks(cfg, cfg["body"]["try_after_seconds"]):
            return []
        how, bit, key = P[:3]
        if how == "ask":
            name, at = hub.book_at(house, cfg, room, pet)   # SPEC-v3.5.1 §3: a screen nobody else is at, or the heavy book
            return [{"what": name, "where": "ask " + bit, "want": key, "goal": near(at), "bonus": W * 1.5}] if at else []
        at = craft.place(house, cfg, room, how)
        return [{"what": bit, "where": how, "want": key, "how": how, "goal": near(at[1]) if at[1] else None, "bonus": W * 1.5}]
    if do in ("bench", "lay out"):   # (§1.2: the body works toward what the mind is about)
        enough = len(pet["carrying"]) >= cfg["body"]["make_bits"] or (pet["carrying"] and not any(s["ready"] for s in room["spots"]))
        at_bench = not bench or dist(me, objs[bench]["pos"]) <= 1
        if not making or not enough or (do == "bench") == at_bench:
            return []
        if do == "bench":
            return [{"what": bench, "goal": near(objs[bench]["pos"]), "bonus": cfg["body"]["make_pull"]}]
        return [{"where": "on the %s" % bench if bench else "on the floor", "bonus": cfg["body"]["make_pull"]}]
    if do == "tend":   # what is planted and not yet ripe, the driest first (SPEC-v3.4 §3.5: tending is watering)
        plants = sorted((n for n, o in objs.items() if o.get("planted") and o["planted"]["grow"] < 1 and not o["planted"].get("wilted") and not o["planted"].get("dormant")), key=lambda n: objs[n]["planted"]["watered"])
        return [{"what": n, "goal": near(objs[n]["pos"]), "bonus": 0.6 if house["tick"] - objs[n]["planted"]["watered"] > cfg["ticks_per_day"] / 2 else 0.0} for n in plants[:2]]
    if do in ("follow", "sit with"):
        kin = kin_here(house, pet)
        if do == "follow":
            kin = [p for p in kin if not p["sleep"] and dist(me, p["pos"]) > 2]
        return [{"who": p["id"], "goal": near(p["pos"]), "bonus": 1.0 if focus.get("who") == p["id"] else 0.0} for p in kin[:2]]
    if do == "watch":
        return [{"what": c["kind"], "creature": c["id"], "goal": None if dist(me, c["pos"]) <= 3 else beside(cfg, c["pos"], me)}
                for c in house["creatures"] if c["room"] == room["id"]][:1]
    if do == "stone":
        stones = [n for n, o in objs.items() if "memorial" in o and house["pets"].get(o["memorial"]["pet"]) and relation(house, pet, house["pets"][o["memorial"]["pet"]])]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in stones[:1]]
    if do == "babble":
        return [{"who": p["id"]} for p in here(house, pet, awake=True)][:1]
    if do == "dance":
        return [{}] if music(house, pet) else []
    if do == "listen":   # a box that is on, here: it may come over to listen (§3.2)
        on = [n for n, o in objs.items() if o.get("fix", {}).get("radio") and o.get("state") == "on"]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in on[:1]]
    if do == "sing":
        known = [e for e in pet.get("songs", []) if e["id"] in songs.book(house)]
        if not known or (house["tick"] - max((e.get("last", LONG_AGO) for e in known), default=LONG_AGO)) < ticks(cfg, cfg["body"]["sing_again_seconds"]):
            return []
        e = min(known, key=lambda e: e.get("last", LONG_AGO))
        dj = (house.get("dj") or {}).get("music") or {}   # the visitor's tune, if it knows it and it is playing: it sings along (§3.1)
        along = next((x for x in known if dj.get("mood") and songs.book(house)[x["id"]]["name"] == "the visitor's %s tune" % dj["mood"] and music(house, pet)), None)
        theirs = {state(p)["now"]["what"] for p in kin_here(house, pet) if (state(p)["now"] or {}).get("do") == "sing"}   # someone here is singing one it knows: the same song
        along = along or next((x for x in known if songs.book(house)[x["id"]]["name"] in theirs), None)
        return [{"what": songs.book(house)[(along or e)["id"]]["name"], "bonus": 1.0 if along else 0.0}]
    return []


def score(house, cfg, pet, name, A, t, b, r):
    """How much it wants to do this now (§1.1): its needs, its temperament, its habits, what its mind is about, the
    hour and the sky, what it has just been doing, and a little chance."""
    B, T = cfg["body"], pet["temper"]
    s = A.get("base", 0.5) + t.get("bonus", 0.0)
    s += sum(w * feel.level(pet, n) / 4 for n, w in A.get("needs", {}).items())
    s += sum(w * (T.get(g, 0.5) - 0.5) * 2 for g, w in A.get("temper", {}).items())
    s += B["habit"] * min(1.0, b["habits"].get(habit_key(house, pet, name), 0) / B["habit_full"])
    focus = pet.get("focus") or {}
    if minded(pet) in A.get("focus", []):
        on = focus.get("what") or focus.get("who")
        s += B["focus"] * (1.0 if not on or on in (t.get("what"), t.get("who")) else 0.4)
    if A.get("handles") and t.get("what") and not (minded(pet) == "make" and not laid_out(pet)):   # (not while it is getting ready to make.) The fewer different things it has had its paws on lately, the more a thing it has not just handled draws it (v3.4 §0, §1)
        lately = {th for tk, th in b.get("handled", []) if house["tick"] - tk < B["handle_ticks"]}
        if t["what"] not in lately:
            s += B["handle"] * (0.0 if len(lately) >= 3 else 1.5 if len(lately) == 2 else 2.3)   # (with one or none, little else is chosen before it)
    if t.get("goal") and b.get("strides") and not (minded(pet) == "make" and not laid_out(pet)) and pet.get("walked", 0) - b["strides"][0][1] < B["stride_tiles"] and house["tick"] - b["strides"][0][0] >= B["handle_ticks"] - 5:
        s += B["stride"] * min(1.0, dist(pet["pos"], t["goal"]) / 6)   # it has not walked far lately: what is further off draws it (v3.4 §0)
    if A.get("handles") or name in TOGETHER:   # being with someone is doing what they do (v3.4 §1): the same toy, the same song, tidying side by side
        want = house["pets"].get(focus.get("who") or "") if focus.get("type") == "be with" else None
        for p in [want] if want and want["room"] == pet["room"] else kin_here(house, pet):
            on = state(p)["now"]
            if on and not p["sleep"] and on["name"] == name and (name not in ("play", "sing") or on.get("what") == t.get("what")):
                s += B["together"] * (1.0 if p is want else 0.3)
                break
    now = {phase(house), house["weather"]} | ({"music"} if music(house, pet) else set())
    s += sum(w for k, w in A.get("when", {}).items() if k in now)
    s -= B["variety"] * b["recent"][-8:].count(name) + (B["again"] if b["recent"][-1:] == [name] else 0.0)
    # the longer since it last did this, the more it is due: whatever its mind is about, in five minutes it has done many things (§0)
    s += B["fresh"] * (1.0 if A.get("handles") else 0.5) * min(1.0, (house["tick"] - b.get("done", {}).get(name, LONG_AGO)) / ticks(cfg, B["fresh_seconds"]))
    if b.get("last_still") and (not t.get("goal") or t["goal"] == pet["pos"]) and not A.get("rest"):
        s -= B["stay"]   # it has just done something on this spot: next it moves (§1.4)
    at = anchor(house, pet)
    if at and dist(t.get("goal") or pet["pos"], at) > 3:
        s -= B["leash"]   # its mind is on staying near something: its body does not drift off from it
    if A.get("passive"):   # resting, looking and watching stay a small part of the day, unless it is worn out
        share = sum(b["idle"]) / max(1, len(b["idle"]))
        s -= B["passive"] * max(0.0, share - B["passive_share"]) * (0.6 if feel.level(pet, "energy") >= 3 else 1.0) + (B["again"] if b.get("last_passive") else 0.0)
    return s + r.uniform(0, B["chance"])


def habit_key(house, pet, name):
    return "%s|%s|%s" % (name, house["rooms"][pet["room"]]["type"], phase(house))


def choose(mind, fidget=False):
    """The best thing to do now. There is always something: a pet awake is never doing nothing (§1.4).
    `fidget`: the best bit of filler instead (a stretch, a hum, a fiddle with what is in reach), or None: done where
    it stands, for one tick, and never what is chosen when there is something to do (v3.4 §1)."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    b, r, best, new = state(pet), rnd(h, "body", pet["id"], h["tick"], fidget), None, False
    rested = sum(b["idle"]) / max(1, len(b["idle"]))
    lately = {th for tk, th in b.get("handled", []) if h["tick"] - tk < cfg["body"]["handle_ticks"]}
    for name, A in cfg["activities"].items():
        if STAGES.index(pet["stage"]) < STAGES.index(A.get("stage", "hatchling")) or A.get("needs_tool") or A.get("needs_place") or bool(A.get("fidget")) != fidget:
            continue   # (Phase B: a tool it must carry, a place it must be at; nothing has either yet)
        if A.get("passive") and rested >= cfg["body"]["passive_max"]:
            continue   # it has sat and looked enough for now, however tired and whatever its mind is on (§0); the night is for sleeping
        for t in targets(h, cfg, pet, mind.mem, name, A):
            if fidget and t.get("goal"):
                continue   # (only with what is already in reach: a fidget takes it nowhere)
            s = score(h, cfg, pet, name, A, t, b, r) + (cfg["body"]["handle"] if b.get("bare") and A["do"] == "go" else 0.0)
            if best is None or s > best[0]:
                best = (s, name, t)
            new = new or bool(A.get("handles") and t.get("what") and t["what"] not in lately)
    if best is None:
        return None
    if not fidget:
        b["strides"] = [x for x in b.get("strides", []) + [[h["tick"], pet.get("walked", 0)]] if h["tick"] - x[0] <= cfg["body"]["handle_ticks"]]   # how far it had walked, at each thing chosen lately
    if not fidget:   # nothing here it has not just had its paws on, and it has handled little lately: the next room has more (v3.4 §1)
        b["bare"] = len(lately) < 3 and not new
    _, name, t = best
    A = cfg["activities"][name]
    lo, hi = A["seconds"]
    now = {"name": name, "do": A["do"], "what": t.get("what"), "who": t.get("who"), "where": t.get("where"), "job": t.get("job"), "door": t.get("door"), "trip": t.get("trip"), "creature": t.get("creature"),
            "goal": t.get("goal"), "to": t.get("to"), "want": t.get("want"), "left": ticks(cfg, r.uniform(lo, hi)), "since": h["tick"], "began": None, "passive": bool(A.get("passive")),
            "icon": cfg["process_signs"].get(t.get("how")) or A.get("icon"), "voice": A.get("voice")}
    now["doing"], now["of"] = say(cfg, h, pet, now, "doing"), now["left"]   # in the page's words, and the packet's
    return now


def then(mind):
    """What comes after the thing just done: now and then a fidget, never two running, more often while a thought
    is on its way; otherwise the next thing to do."""
    pet, h, B = mind.pet, mind.eng.house, mind.cfg["body"]
    getting_ready = minded(pet) == "make" and not laid_out(pet)   # (a body working toward what its mind is set on making does not dawdle)
    if not state(pet).get("fidgeted") and not getting_ready and rnd(h, "fidget", pet["id"], h["tick"]).random() < B["fidget"] * (2 if pet.get("thinking") else 1):
        return choose(mind, fidget=True) or choose(mind)
    return choose(mind)


def say(cfg, house, pet, now, form, where=""):
    """An activity in words: `doing` for the page, `did` for what the pet is told afterwards."""
    who, what = house["pets"].get(now.get("who") or ""), now.get("what") or ""
    o = house["rooms"][pet["room"]]["objects"].get(what, {})
    if form == "doing" and "made" in o and o["made"]["recipe"].get("kind") and o["made"]["recipe"]["kind"] not in what:
        what = "%s (a %s)" % (what, o["made"]["recipe"]["kind"])   # its maker's name for it says little to a stranger: what it is, too
    A = cfg["activities"][now["name"]]
    form = form + "_screen" if o.get("fix", {}).get("terminal") and form + "_screen" in A else form   # (a screen is not the heavy book)
    return A[form].format(what=what, where=where or (now.get("where") if isinstance(now.get("where"), str) else ""),
                                                         who=(actions.handle(house, pet, who) if form == "did" else label(who)) if who else "someone")


def tick(mind):
    """One tick of the body. Called when the pet has nothing it decided left to do."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    b = state(pet)
    now = b["now"]
    urgent = bool(URGENT & set(pet["news"]))
    if now and urgent and not now.get("startled"):   # something happened: it stops and turns to it (§1.1), once
        b["react"] = {"tick": h["tick"], "kind": "startle" if "event" in pet["news"] else "turn"}
        voice(h, pet, "gasp" if "event" in pet["news"] else "chirp")
        finish(mind, now, cut=True)
        now = None
    if not now:
        now = b["now"] = choose(mind)
        now["startled"] = urgent
    who = h["pets"].get(now.get("who") or "")
    if who and who["room"] == pet["room"] and now["do"] in ("follow", "sit with"):
        now["goal"] = None if dist(pet["pos"], who["pos"]) <= 1 else beside(cfg, who["pos"], pet["pos"])
    if now["do"] == "tail":
        c = next((c for c in h["creatures"] if c["id"] == now.get("creature") and c["room"] == pet["room"]), None)
        now["goal"] = None if not c or dist(pet["pos"], c["pos"]) <= 1 else beside(cfg, c["pos"], pet["pos"])
    def step(to):
        now["there"] = h["tick"]   # the last tick it took a step on: what it does after that is done in one place
        mind.walk(to)
    if now["began"] is None:
        if now["do"] not in KEEPS_UP and now.get("goal") and pet["pos"] != now["goal"] and h["tick"] - now["since"] < ticks(cfg, cfg["body"]["walk_seconds"]):
            return step(now["goal"])
        now["began"] = h["tick"]
        if now.get("voice"):
            voice(h, pet, now["voice"])
    if now["do"] in KEEPS_UP and now.get("goal") and pet["pos"] != now["goal"]:
        step(now["goal"])   # it keeps after them for as long as this lasts
    elif now.get("to") and pet["pos"] != now["to"] and h["tick"] - now["began"] < ticks(cfg, cfg["body"]["walk_seconds"]):
        return step(now["to"])   # it has the thing in its paws and is carrying it to where it goes
    now["left"] -= 1
    if now["left"] <= 0:
        finish(mind, now)
        b["now"] = dict(then(mind), startled=urgent)   # and straight on to the next thing: there is no tick on which it is doing nothing (§1.4)


def voice(house, pet, kind):
    """A small sound in its own voice, for whoever is watching (§4): each is numbered so it is played once."""
    house["n"]["vox"] = house["n"].get("vox", 0) + 1
    house.setdefault("vox", []).append({"n": house["n"]["vox"], "tick": house["tick"], "pet": pet["id"], "room": pet["room"], "kind": kind})
    del house["vox"][:-30]


def finish(mind, now, cut=False):
    """The activity is over: what it really did is done, and it is written down, briefly."""
    pet, h, cfg, eng = mind.pet, mind.eng.house, mind.cfg, mind.eng
    b, room, E = state(pet), h["rooms"][pet["room"]], cfg["effects"]
    b["now"], did, fx, key, where, told = None, None, {}, None, "", None
    A = cfg["activities"][now["name"]]
    done = not cut and now["began"] is not None
    name = actions.norm(now.get("what")) if now.get("what") else None
    news = {p["id"]: list(p["news"]) for p in h["pets"].values() if "news" in p}   # a body is never news to anyone: nobody is asked to think about it
    act = None
    try:
        if done:
            do, o = now["do"], room["objects"].get(name)
            if do in ACT:   # numbered like any finished step, so the view plays it once (and sounds what sounds: §4)
                onto = now["job"][3] if do == "tidy" and now.get("job") and now["job"][2] == "on" else None   # the shelf it goes on
                act = story.act_of(h, pet, {"type": ACT[do], "door" if do == "go" else "target": now.get("what"), "to": now.get("who") or onto})
                act.update(type=ACT[do], body=now["name"], loud=bool(o and ACT[do] in ("use", "fiddle") and ((things.prop(cfg, o).get("loud") if "made" in o else o.get("fix", {}).get("loud")))))
            if do == "inspect" and o is not None:
                _, fx, key = actions.look(h, cfg, pet, {"target": name})
            elif do in ("play", "eat", "stone") and o is not None and not ("made" in o and things.prop(cfg, o).get("food")):
                _, fx, key = actions.use(h, cfg, pet, name)
                fx.pop("tags", None)
                if do == "play":
                    key = "body play " + name
                    if o.get("made", {}).get("recipe", {}).get("kind") == "ball" or (name == "ball" and o.get("fix", {}).get("movable")):   # a ball rolls: to someone, if anyone is up, who may send it back
                        mate = min((p for p in kin_here(h, pet) if not p["sleep"]), key=lambda p: (focus_who(pet) != p["id"], dist(pet["pos"], p["pos"])), default=None)
                        r = rnd(h, "roll", pet["id"], h["tick"])
                        order.moved(o, h["tick"])
                        o["pos"] = free_tile(h, cfg, room, beside(cfg, mate["pos"], pet["pos"]) if mate else [min(cfg["W"] - 2, max(1, pet["pos"][0] + r.randint(-4, 4))), min(cfg["H"] - 2, max(1, pet["pos"][1] + r.randint(-3, 3)))], name)
                        told = "rolled the %s over to %s" % (name, actions.handle(h, pet, mate)) if mate else "sent the %s rolling across the room" % name
                        if mate:
                            pet.setdefault("played_with", {})[mate["id"]] = h["tick"]
                            add_event(h, mate, "%s rolled the %s over to you" % (actions.handle(h, mate, pet), name))
            elif do == "seat" and o is not None:
                _, fx, key = actions.use(h, cfg, pet, name)
                fx.pop("tags", None)
                key = "body seat " + name
            elif do == "take out" and o is not None and o.get("on"):
                where, o["kept"] = o["on"], h["tick"]   # it is back where it was: looking is not leaving out
                key = "look " + name
            elif do == "bring" and o is not None and not o.get("on"):
                other = h["pets"].get(now.get("who") or "")
                order.moved(o, h["tick"])
                o["pos"] = free_tile(h, cfg, room, pet["pos"], name)
                key = "body bring " + name
                if other:
                    pet["gave"] = {"tick": h["tick"], "to": other["id"]}
                if other and other["room"] == pet["room"] and not other["sleep"]:
                    add_event(h, other, "%s carried the %s over to you" % (actions.handle(h, other, pet), name))
            elif do == "try":
                asking = now["where"].startswith("ask ")   # (the book: it turns the pages looking for the word it wondered about)
                a = {"type": "ask_book", "question": now["where"][4:]} if asking else {"type": "process", "what": name, "how": now["where"]}
                b["asked_at" if asking else "tried_at"] = now["want"]
                why = actions.check(a, h, cfg, pet, mind.mem)
                told, fx, key = (why, {}, None) if why else actions.apply(h, cfg, pet, a, mind.mem)
                add_event(h, pet, told if asking else "you tried the %s: %s" % (name, told))
                told = None
                act = story.act_of(h, pet, a) if not why else None
            elif do == "tail":
                pet["met"][now["what"]] = pet["met"].get(now["what"], 0) + 1
            elif do == "go" and name in room["doors"] and actions.check({"type": "go", "door": name}, h, cfg, pet, mind.mem) is None:
                text, fx, key = actions.go(h, cfg, pet, name)
                add_event(h, pet, text)
                room = h["rooms"][pet["room"]]
                if now.get("trip"):   # drawn out by a mess: that is today's one such trip, over once it stands in the mess
                    b["trip"] = [h["clock"]["day"], room.get("mess") == 2]
            elif do == "peek" and now.get("door") in room["doors"]:
                there = [p for p in h["pets"].values() if p["room"] == room["doors"][now["door"]] and p["stage"] not in ("egg", "dead")]
                add_event(h, pet, "you peeked into %s: %s" % (now["what"], ", ".join("%s is there" % actions.handle(h, pet, p) for p in there) or "nobody is there"))
            elif do == "tidy" and now.get("job"):
                where = order.do_job(h, cfg, pet, room, now["job"])
                done, act = bool(where), act if where else None   # it was gone, or the place was taken: nothing was put away
                if where:
                    craft.practise(h, cfg, pet, "tidying", 0.25)
            elif do == "gather":
                if now.get("want") == "swap" and len(pet["carrying"]) >= cfg["make"]["carry"]:   # room in its arms for the bit it wants: the first thing it carries that no want of its is about
                    keep = {w.get("bit") for w in pet.get("wants", [])} | build.keep(h, cfg, pet)   # (nor what it is building with: SPEC-v3.5 §4)
                    spare = next((x for x in pet["carrying"] if x not in keep), pet["carrying"][0])
                    pet["carrying"].remove(spare)
                    things.drop_bits(h, cfg, room, pet["pos"], [spare])
                a = {"type": "gather", "what": name}
                if actions.check(a, h, cfg, pet, mind.mem) is None:
                    actions.apply(h, cfg, pet, a, mind.mem)
            elif do == "lay out":   # everything is to hand: it thinks about making sooner than it otherwise would
                b["laid"], where = list(pet["carrying"]), now["where"]
                add_event(h, pet, "what you carry is laid out %s: everything is ready to make something" % where)
                pet["ready"] = h["tick"]
            elif do == "tend" and o is not None and o.get("planted"):
                craft.water(h, cfg, pet, room, name)
            elif do == "place":   # it is where the thing can be tried, with the thing: its mind is told, and thinks sooner
                slot, where = "booked" if now["where"].startswith("ask ") else "placed", now["where"]
                other, asking = h["pets"].get(now.get("who") or ""), where.startswith("ask ")
                where = "" if asking else where
                if now.get("who") and (not other or other["room"] != pet["room"] or other["sleep"]):
                    done = False   # (the elder it was going to ask has gone, or dropped off: another time)
                else:
                    b[slot], b[slot + "_at"], pet["ready"] = [now["want"], room["id"]], h["tick"], h["tick"]
                    if other:   # (an elder is gone to once for each thing it wants to know)
                        pet["asked_aloud"] = (pet.get("asked_aloud", []) + [now["where"][4:]])[-12:]
                    add_event(h, pet, ('%s is right here; you could ask out loud: "%s"' % (actions.handle(h, pet, other), now["where"][4:]) if other
                                       else '%s is right here; you could ask it: "%s"' % ("the screen" if room["objects"].get(now.get("what") or "", {}).get("fix", {}).get("terminal") else "the book", now["where"][4:])) if asking
                              else "you have carried the %s %s: you could try it now" % (name, where))
            elif do == "build":   # SPEC-v3.5 §4
                told, done = build.finish(mind, now, A)
            elif do == "nap":
                fx = {"energy": E["rest_per_10s"] * A["seconds"][1] / 10}
            elif do == "babble":
                other = h["pets"].get(now.get("who") or "")
                if other and other["room"] == pet["room"] and not other["sleep"]:
                    add_event(h, other, "%s babbled at you" % actions.handle(h, other, pet))
            elif do == "sing" and songs.known(h, pet, now["what"]):
                songs.sing(h, cfg, pet, {"song": now["what"]}, actions.find, actions.handle, actions.bump)
            elif do == "watch":
                pet["met"][now["what"]] = pet["met"].get(now["what"], 0) + 1
            elif do in machine.DOS:   # SPEC-v3.5 §4.3: it takes from the machine, feeds it, or carries a thing a room nearer to it
                told, fx, key, act = machine.finish(mind, now)
                done = bool(told)
            for n, v in A.get("effects", {}).items():
                fx[n] = fx.get(n, 0) + v
            if fx.get("curiosity") or key:
                mind.novelty(fx, key or "body " + now["name"], False, fx.pop("scale", 1.0))
            fx.pop("scale", None)
            actions.bump(pet, cfg, {n: v for n, v in fx.items() if n in pet["needs"]})
            did = told or say(cfg, h, pet, now, "did", where)
            if act:
                story.acted(h, cfg, pet, act, True)
    except Exception:   # a body's mistake must never stop a pet: it just did not do that
        import logging
        logging.exception("body activity %s failed for %s", now["name"], pet["id"])
    for p in h["pets"].values():
        if p["id"] in news:
            p["news"] = news[p["id"]]
    start = now["since"]
    b["fidgeted"] = bool(A.get("fidget"))
    if done and did and not A.get("fidget"):   # (a stretch or a hum is not something it did: its mind is not told of them, and they are no habit)
        b["since"].append(did)
        del b["since"][:-40]
        k = habit_key(h, pet, now["name"])
        b["habits"][k] = b["habits"].get(k, 0) + 1
        for kid in here(h, pet, awake=True):   # the young pick up a little of what they watch a parent do (§1.3)
            if kid["parent"] == pet["id"] and kid["stage"] in ("hatchling", "child", "youngling"):
                kb = state(kid)
                kb["habits"][k] = round(kb["habits"].get(k, 0) + cfg["body"]["habit_watched"], 2)
        if len(b["habits"]) > 60:
            for k2 in sorted(b["habits"], key=b["habits"].get)[:20]:
                del b["habits"][k2]
    if not A.get("fidget"):
        b["recent"] = (b["recent"] + [now["name"]])[-12:]
    if done:
        b.setdefault("done", {})[now["name"]] = h["tick"]
        if A.get("handles") and now.get("what"):
            b["handled"] = (b.get("handled", []) + [[h["tick"], now["what"]]])[-12:]
    b["last_passive"] = bool(now["passive"]) and done
    span = max(1, h["tick"] - start)
    b["idle"] = (b["idle"] + [1 if now["passive"] and now["began"] is not None else 0] * min(span, 60))[-cfg["body"]["window_ticks"]:]
    b["n"] += 1
    b["last_still"] = now["began"] is not None and not now.get("there")   # it did not take a step to do it
    eng.did(pet, start, h["tick"], now["name"], bool(now["passive"]), "body", did or "",
            still=h["tick"] - max(now["began"], now.get("there") or 0) if now["began"] is not None else 0, rest=bool(A.get("rest")),
            thing=now.get("what") if done and A.get("handles") else None)


def since(pet):
    """What its body has been doing since it last thought, in a few words (§1.2), for the packet: "you tidied two
    things, played with the ball, sat with Garry by the window". Clears the list."""
    b = state(pet)
    seen, out = {}, []
    for text in b["since"]:
        seen[text] = seen.get(text, 0) + 1
    for text, n in seen.items():
        out.append(text if n == 1 else "%s (%s times)" % (text, COUNT[n] if n < len(COUNT) else "many"))
    b["since"] = []
    return ", ".join(out[-8:])


def habits(house, cfg, pet, n=3):
    """Its strongest habits in plain words: "sits by the window at dusk"."""
    b = state(pet)
    top = sorted(((v, k) for k, v in b["habits"].items() if v >= cfg["body"]["habit_shown"]), reverse=True)[:n]
    out = []
    for _, k in top:
        name, room_type, when = k.split("|")
        A = cfg["activities"].get(name)
        if A:
            place = cfg["house"]["rooms"].get(room_type, {}).get("name", "the house")
            out.append("%s in %s %s" % (name, place, {"day": "by day", "night": "at night", "dusk": "at dusk", "morning": "in the morning"}.get(when, when)))
    return out


def going(house, pet, now):
    """While it is still on its way: where it is off to, so nobody reads "nosing at the east door" from across the room."""
    who = house["pets"].get(now.get("who") or "")
    if now["do"] in ("doorway", "peek", "go"):
        return "going over to the %s door" % (now.get("door") or now.get("what"))
    if now["do"] in ("nap", "window"):
        return "going to %s" % {"nap": "lie down", "window": "sit by the window"}[now["do"]]
    return "going over to %s" % (label(who) if who else "the " + now["what"]) if who or now.get("what") else now["doing"]


def begun(pet, now):
    """Has it got there and been at it a tick or more (and, carrying something, got it where it goes)? Then cutting it short still leaves it done."""
    return now["began"] is not None and now["left"] < now.get("of", now["left"]) and (not now.get("to") or pet["pos"] == now["to"])


def on_its_way(pet, now):
    return now["began"] is None and bool(now.get("goal")) and dist(pet["pos"], now["goal"]) > 1


def words(house, pet, now):
    """What its body is at, in words, right now."""
    return going(house, pet, now) if on_its_way(pet, now) else now["doing"]


def doing(cfg, house, pet):
    """What its body is doing right now, for the page: {activity, doing, icon, what, who, since, passive, walking} or None."""
    now = state(pet)["now"]
    if not now:
        return None
    walking = on_its_way(pet, now)
    return {"activity": now["name"], "doing": words(house, pet, now), "icon": "walk" if walking and now["do"] in ("nap", "window") else now["icon"], "what": now.get("what"), "who": now.get("who"),
            "since": now["since"], "passive": now["passive"], "walking": now["began"] is None, "goal": now.get("goal"),
            "carrying": (bool(now.get("to")) or now["do"] == "take out") and now["began"] is not None}   # it has the thing in its paws and is taking it where it goes (the page shows it carried)
