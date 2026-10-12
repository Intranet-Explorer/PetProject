"""The body (SPEC-v3.3 §1): what a pet does by itself between thoughts, with no model asked. Each tick a pet that
is not carrying out something it decided picks the best activity for the moment from activities.toml and does it:
short, visible and real (tidying moves things, eating empties the bowl). The mind still decides everything that
belongs to the pet's story; the body only fills the time in between, in character."""
from . import actions, feel, order, songs, story, things
from .world import LONG_AGO, STAGES, add_event, beside, dist, free_tile, here, label, relation, rnd, ticks

URGENT = {"visitor", "woke", "hatched", "low", "spoken", "event"}   # what stops it in its tracks (as it hurries a thought)
# what a finished activity is to whoever is watching: the same words the steps a mind decides use, where there is one
ACT = {"inspect": "look", "play": "use", "eat": "eat", "stone": "use", "go": "go", "tidy": "put_away", "gather": "gather", "fiddle": "fiddle",
       "tend": "tend", "dance": "dance", "babble": "babble", "nap": "nap", "listen": "listen", "watch": "watch"}
COUNT = ["", "", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def state(pet):
    return pet.setdefault("body", {"now": None, "recent": [], "since": [], "habits": {}, "idle": [], "n": 0})


def phase(house):
    c = house["clock"]
    return "morning" if c["morning"] else c["phase"]


def music(house, pet):
    """Is there music where it is: the visitor's, or something ringing in the room?"""
    dj = (house.get("dj") or {}).get("music")
    return bool(dj and dj.get("mood") and dj["scope"] in ("house", pet["room"])) or house["rooms"][pet["room"]].get("sounding_until", 0) > house["tick"]


def anchor(house, pet):
    """Where its mind wants it to be near, if anywhere: the thing or the one its focus names, when they are in this room."""
    f = pet.get("focus") or {}
    if f.get("type") not in ("stay near", "tend", "be with", "make"):
        return None
    objs = house["rooms"][pet["room"]]["objects"]
    if f.get("type") == "make" and laid_out(pet):   # its bits are laid out: it stays by them
        return next((o["pos"] for o in objs.values() if o.get("fix", {}).get("bench")), pet["pos"])
    o, who = objs.get(f.get("what") or ""), house["pets"].get(f.get("who") or "")
    return o["pos"] if o else who["pos"] if who and who["room"] == pet["room"] and who["stage"] not in ("egg", "dead") else None


def laid_out(pet):
    """Has it laid out the very bits it is carrying? (Then it is ready to make, and does not lay them out again.)"""
    return bool(pet["carrying"]) and state(pet).get("laid") == pet["carrying"]


def out_of_sight(cfg, room, o):
    """Put away inside something (a chest, a crate): not a thing to play with or look at until it is taken out."""
    store = room["objects"].get(o.get("on") or "")
    return bool(store) and bool(store.get("fix", {}).get("inside") or cfg["kinds"].get(store.get("made", {}).get("recipe", {}).get("kind"), {}).get("inside"))


def kin_here(house, pet):
    return [p for p in here(house, pet) if relation(house, pet, p)]


def targets(house, cfg, pet, mem, name, A):
    """Everything this activity could be done with right now: [{what/who, goal, ...}]. Empty if it cannot be done."""
    room, do, me, r = house["rooms"][pet["room"]], A["do"], pet["pos"], rnd(house, "body-t", pet["id"], house["tick"], name)
    objs, focus = room["objects"], pet.get("focus") or {}
    near = lambda pos: None if dist(me, pos) <= 1 else beside(cfg, pos, me)
    if do == "self":
        return [{}]
    if do == "wander":   # somewhere a few steps off: the farthest of a few tries (or near what its mind is on)
        at = anchor(house, pet)
        tries = [[r.randrange(1, cfg["W"] - 1), r.randrange(1, cfg["H"] - 1)] for _ in range(4)] if not at else \
            [[min(cfg["W"] - 2, max(1, at[0] + r.randint(-2, 2))), min(cfg["H"] - 2, max(1, at[1] + r.randint(-2, 2)))] for _ in range(4)]
        return [{"goal": free_tile(house, cfg, room, max(tries, key=lambda t: min(dist(me, t), 6)))}]
    if do in ("doorway", "peek", "go"):
        out = []
        for d, rid in room["doors"].items():
            stuck = house["shut"].get("%s|%s" % (room["id"], d), LONG_AGO) > house["tick"]
            to, been = house["rooms"][rid], rid in pet["rooms"]
            if do == "doorway" and not been:
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
                elif focus.get("type") == "tidy" and to.get("mess") == 2 and not order.job(house, cfg, pet, room):
                    out.append({"what": d, "goal": list(house["door_tiles"][d]), "bonus": 2.0})   # this room is done and the next is a mess: tidying moves on
                elif focus.get("type") in (None, "explore", "play") and house["tick"] - pet["rooms"].get(room["id"], LONG_AGO) >= ticks(cfg, cfg["body"]["go_again_seconds"]):
                    # (it stays where its mind put it a good while, and where its mind wants it: it never walks out on a focus)
                    messier = to.get("mess") == 2 and room.get("mess", 0) < 2   # a mess next door draws the orderly, as one here keeps them
                    out.append({"what": d, "goal": list(house["door_tiles"][d]),
                                "bonus": (0.6 if kin and not kin_here(house, pet) else 0.0) + (0.8 if focus.get("type") == "explore" else 0.0)
                                + (cfg["body"]["mess_pull"] * 2 * pet["temper"].get("orderly", 0.5) if messier else 0.0)})
        return out
    if do == "inspect":
        seen = lambda n: pet["times"].get("look " + n, 0)
        names = sorted((n for n in objs if not out_of_sight(cfg, room, objs[n])), key=lambda n: (seen(n), dist(me, objs[n]["pos"])))[:3]
        return [{"what": n, "goal": near(objs[n]["pos"]), "bonus": 0.4 if not seen(n) else 0.0} for n in names]
    if do == "fiddle":
        mine = [n for n, o in things.made(room).items() if things.free_to_change(house, pet, o) and not out_of_sight(cfg, room, o)] \
            + [n for n, o in objs.items() if o.get("fix", {}).get("movable")]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in sorted(mine, key=lambda n: dist(me, objs[n]["pos"]))[:2]]
    if do == "play":
        toys = [n for n, o in objs.items() if "toy" in o.get("fix", {})]
        toys += [n for n, o in things.made(room).items() if things.prop(cfg, o).get("use", {}).get("curiosity") and not things.prop(cfg, o).get("food")
                 and things.free_to_change(house, pet, o) and not out_of_sight(cfg, room, o)]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in sorted(toys, key=lambda n: (pet["times"].get("body play " + n, 0), dist(me, objs[n]["pos"])))[:2]]
    if do == "window":
        return [{"what": n, "goal": near([o["pos"][0], max(o["pos"][1], 0)])} for n, o in objs.items() if o.get("fix", {}).get("window")][:1]
    if do == "nap":
        if feel.level(pet, "energy") < 1 and focus.get("type") != "rest":
            return []   # not tired, and not minded to rest
        beds = [o["pos"] for o in objs.values() if "rest" in o.get("fix", {}) or o.get("fix", {}).get("cozy")]
        return [{"goal": near(min(beds, key=lambda t: dist(me, t))) if beds else None}]
    if do == "eat":
        if feel.level(pet, "energy") < 2 or (house["tick"] - pet.get("last_eat", LONG_AGO)) * cfg["clock"]["tick_seconds"] <= cfg["effects"]["double_feed_seconds"]:
            return []
        food = [n for n, o in objs.items() if ("meal" in o.get("fix", {}) and o.get("servings")) or (o.get("fix", {}).get("plant") and o.get("state") == "ripe")]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in food[:1]]
    if do == "tidy":
        job = order.job(house, cfg, pet, room)   # the worse the mess, the more it pulls, on the orderly most of all
        if not job:
            return []
        pull = (order.clutter(house, cfg, room) + (job["job"][0] == "old")) * cfg["body"]["mess_pull"] * (0.4 + 1.2 * pet["temper"].get("orderly", 0.5))
        return [{"what": job["what"], "job": job["job"], "goal": near(job["pos"]), "bonus": pull}]
    making = focus.get("type") == "make" and not laid_out(pet)   # its mind is on making, and it is not ready yet
    bench = next((n for n, o in objs.items() if o.get("fix", {}).get("bench")), None)
    if do == "gather":
        if len(pet["carrying"]) >= (cfg["body"]["make_bits"] if making else cfg["make"]["carry"] if focus.get("type") == "project" else 1):
            return []
        spots = sorted((s for s in room["spots"] if s["ready"]), key=lambda s: dist(me, s["pos"]))
        return [{"what": s["bit"], "goal": near(s["pos"]), "bonus": cfg["body"]["make_pull"] if making else 0.0} for s in spots[:1]]
    if do in ("bench", "lay out"):   # (§1.2: the body works toward what the mind is about)
        enough = len(pet["carrying"]) >= cfg["body"]["make_bits"] or (pet["carrying"] and not any(s["ready"] for s in room["spots"]))
        at_bench = not bench or dist(me, objs[bench]["pos"]) <= 1
        if not making or not enough or (do == "bench") == at_bench:
            return []
        if do == "bench":
            return [{"what": bench, "goal": near(objs[bench]["pos"]), "bonus": cfg["body"]["make_pull"]}]
        return [{"where": "on the %s" % bench if bench else "on the floor", "bonus": cfg["body"]["make_pull"]}]
    if do == "tend":
        plants = [n for n, o in objs.items() if o.get("fix", {}).get("plant") and o.get("state") != "ripe"]
        return [{"what": n, "goal": near(objs[n]["pos"])} for n in plants[:2]]
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
    if focus.get("type") in A.get("focus", []):
        on = focus.get("what") or focus.get("who")
        s += B["focus"] * (1.0 if not on or on in (t.get("what"), t.get("who")) else 0.4)
    now = {phase(house), house["weather"]} | ({"music"} if music(house, pet) else set())
    s += sum(w for k, w in A.get("when", {}).items() if k in now)
    s -= B["variety"] * b["recent"][-8:].count(name) + (B["again"] if b["recent"][-1:] == [name] else 0.0)
    # the longer since it last did this, the more it is due: whatever its mind is about, in five minutes it has done many things (§0)
    s += B["fresh"] * (0.5 if A.get("passive") else 1.0) * min(1.0, (house["tick"] - b.get("done", {}).get(name, LONG_AGO)) / ticks(cfg, B["fresh_seconds"]))
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


def choose(mind):
    """The best thing to do now. There is always something: a pet awake is never doing nothing (§1.4)."""
    pet, h, cfg = mind.pet, mind.eng.house, mind.cfg
    b, r, best = state(pet), rnd(h, "body", pet["id"], h["tick"]), None
    rested = sum(b["idle"]) / max(1, len(b["idle"]))
    for name, A in cfg["activities"].items():
        if STAGES.index(pet["stage"]) < STAGES.index(A.get("stage", "hatchling")) or A.get("needs_tool") or A.get("needs_place"):
            continue   # (Phase B: a tool it must carry, a place it must be at; nothing has either yet)
        if A.get("passive") and rested >= cfg["body"]["passive_max"]:
            continue   # it has sat and looked enough for now, however tired and whatever its mind is on (§0); the night is for sleeping
        for t in targets(h, cfg, pet, mind.mem, name, A):
            s = score(h, cfg, pet, name, A, t, b, r)
            if best is None or s > best[0]:
                best = (s, name, t)
    _, name, t = best
    A = cfg["activities"][name]
    lo, hi = A["seconds"]
    now = {"name": name, "do": A["do"], "what": t.get("what"), "who": t.get("who"), "where": t.get("where"), "job": t.get("job"), "door": t.get("door"), "creature": t.get("creature"),
            "goal": t.get("goal"), "left": ticks(cfg, r.uniform(lo, hi)), "since": h["tick"], "began": None, "passive": bool(A.get("passive")),
            "icon": A.get("icon"), "voice": A.get("voice")}
    now["doing"] = say(cfg, h, pet, now, "doing")   # in the page's words, and the packet's
    return now


def say(cfg, house, pet, now, form, where=""):
    """An activity in words: `doing` for the page, `did` for what the pet is told afterwards."""
    who, what = house["pets"].get(now.get("who") or ""), now.get("what") or ""
    o = house["rooms"][pet["room"]]["objects"].get(what, {})
    if form == "doing" and "made" in o and o["made"]["recipe"].get("kind") and o["made"]["recipe"]["kind"] not in what:
        what = "%s (a %s)" % (what, o["made"]["recipe"]["kind"])   # its maker's name for it says little to a stranger: what it is, too
    return cfg["activities"][now["name"]][form].format(what=what, where=where or (now.get("where") if isinstance(now.get("where"), str) else ""),
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
    if now["began"] is None:
        if now.get("goal") and pet["pos"] != now["goal"] and h["tick"] - now["since"] < ticks(cfg, cfg["body"]["walk_seconds"]):
            return mind.walk(now["goal"])
        now["began"] = h["tick"]
        if now.get("voice"):
            voice(h, pet, now["voice"])
    now["left"] -= 1
    if now["left"] <= 0:
        finish(mind, now)
        b["now"] = dict(choose(mind), startled=urgent)   # and straight on to the next thing: there is no tick on which it is doing nothing (§1.4)


def voice(house, pet, kind):
    """A small sound in its own voice, for whoever is watching (§4): each is numbered so it is played once."""
    house["n"]["vox"] = house["n"].get("vox", 0) + 1
    house.setdefault("vox", []).append({"n": house["n"]["vox"], "tick": house["tick"], "pet": pet["id"], "room": pet["room"], "kind": kind})
    del house["vox"][:-30]


def finish(mind, now, cut=False):
    """The activity is over: what it really did is done, and it is written down, briefly."""
    pet, h, cfg, eng = mind.pet, mind.eng.house, mind.cfg, mind.eng
    b, room, E = state(pet), h["rooms"][pet["room"]], cfg["effects"]
    b["now"], did, fx, key, where = None, None, {}, None, ""
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
                act.update(type=ACT[do], body=now["name"], loud=bool(o and ((things.prop(cfg, o).get("loud") if "made" in o else o.get("fix", {}).get("loud")))))
            if do == "inspect" and o is not None:
                _, fx, key = actions.look(h, cfg, pet, {"target": name})
            elif do in ("play", "eat", "stone") and o is not None and not ("made" in o and things.prop(cfg, o).get("food")):
                _, fx, key = actions.use(h, cfg, pet, name)
                fx.pop("tags", None)
                if do == "play":
                    key = "body play " + name
            elif do == "go" and name in room["doors"] and actions.check({"type": "go", "door": name}, h, cfg, pet, mind.mem) is None:
                text, fx, key = actions.go(h, cfg, pet, name)
                add_event(h, pet, text)
                room = h["rooms"][pet["room"]]
            elif do == "peek" and now.get("door") in room["doors"]:
                there = [p for p in h["pets"].values() if p["room"] == room["doors"][now["door"]] and p["stage"] not in ("egg", "dead")]
                add_event(h, pet, "you peeked into %s: %s" % (now["what"], ", ".join("%s is there" % actions.handle(h, pet, p) for p in there) or "nobody is there"))
            elif do == "tidy" and now.get("job"):
                where = order.do_job(h, cfg, pet, room, now["job"])
                done, act = bool(where), act if where else None   # it was gone, or the place was taken: nothing was put away
            elif do == "gather":
                a = {"type": "gather", "what": name}
                if actions.check(a, h, cfg, pet, mind.mem) is None:
                    actions.apply(h, cfg, pet, a, mind.mem)
            elif do == "lay out":   # everything is to hand: it thinks about making sooner than it otherwise would
                b["laid"], where = list(pet["carrying"]), now["where"]
                add_event(h, pet, "what you carry is laid out %s: everything is ready to make something" % where)
                pet["ready"] = h["tick"]
            elif do == "tend" and o is not None and o.get("fix", {}).get("plant") and o.get("state") != "ripe":
                o["grow"] = round(min(1.0, o["grow"] + cfg["body"]["tend_grow"]), 3)
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
            for n, v in A.get("effects", {}).items():
                fx[n] = fx.get(n, 0) + v
            if fx.get("curiosity") or key:
                mind.novelty(fx, key or "body " + now["name"], False, fx.pop("scale", 1.0))
            fx.pop("scale", None)
            actions.bump(pet, cfg, {n: v for n, v in fx.items() if n in pet["needs"]})
            did = say(cfg, h, pet, now, "did", where)
            if act:
                story.acted(h, cfg, pet, act, True)
    except Exception:   # a body's mistake must never stop a pet: it just did not do that
        import logging
        logging.exception("body activity %s failed for %s", now["name"], pet["id"])
    for p in h["pets"].values():
        if p["id"] in news:
            p["news"] = news[p["id"]]
    start = now["since"]
    if done and did:
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
    b["recent"] = (b["recent"] + [now["name"]])[-12:]
    if done:
        b.setdefault("done", {})[now["name"]] = h["tick"]
    b["last_passive"] = bool(now["passive"]) and done
    span = max(1, h["tick"] - start)
    b["idle"] = (b["idle"] + [1 if now["passive"] and now["began"] is not None else 0] * min(span, 60))[-cfg["body"]["window_ticks"]:]
    b["n"] += 1
    b["last_still"] = now["began"] is not None and now["began"] <= start   # it did not take a step to do it
    eng.did(pet, start, h["tick"], now["name"], bool(now["passive"]), "body", did or "",
            still=h["tick"] - now["began"] if now["began"] is not None else 0, rest=bool(A.get("rest")))


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
            "since": now["since"], "passive": now["passive"], "walking": now["began"] is None, "goal": now.get("goal")}
