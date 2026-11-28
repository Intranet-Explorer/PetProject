"""Cooking (SPEC-v3.6b §2): at the stove a hob puts what it has to hand in the pot, and a dish comes out (dishes.toml).
A dish found is a family recipe ("dish:fish stew") like any other: taught, handed down, lost. The pot stands on the
stove with servings; hobs come and eat from it, and two who eat from one pot have eaten together. A dish cooked from a
recipe someone handed down carries their name. Each hob comes to love a dish or two. A pot not eaten up goes stale in
a day, three with a keeper in the room. The stove's load is engine/machines.py; no model is asked."""
import tomllib
from collections import Counter

from . import craft, feel, firsts, things
from . import needs, opinions   # SPEC-v4.0
from .world import LONG_AGO, add_event, label, moment, ticks

KEEPERS = ("jar", "box", "basket")


def load(cfg, directory):
    """dishes.toml, laid into the config; every food that goes into a dish can be cooked: a rule like any process's
    (crafting.toml), giving the plainest dish it is in, so a hob wants to find out what cooking it makes."""
    cfg["cook"] = tomllib.loads((directory / "dishes.toml").read_text())
    cfg["cook"]["poisoned"] = {n: cfg["cook"]["dish"].pop(n) for n, d in list(cfg["cook"]["dish"].items()) if d.get("poison")}   # SPEC-v4.2 §2.4: set aside; health.install lays them in with [deaths] on
    for name, d in sorted(cfg["cook"]["dish"].items(), key=lambda kv: (len(kv[1]["needs"]), kv[0])):
        for b in d["needs"]:
            cfg["craft"]["rules"].setdefault((b, "cook"), {"bit": b, "how": "cook", "gives": name, "says": d["says"], "dish": True})
    return cfg


def D(cfg):
    return cfg["cook"]["dish"]


def C(cfg):
    return cfg["cook"]["cook"]


def at_hand(pet, room):
    """What could go in the pot: what it carries, and what lies about the room or is put by in it (not a machine's tray)."""
    return Counter(pet["carrying"]) + Counter(s["bit"] for s in room["spots"] if s["ready"] and not s.get("machine"))


def can(cfg, name, have):
    return all(have[b] >= D(cfg)[name]["needs"].count(b) for b in D(cfg)[name]["needs"])


def lately(house, cfg):
    """How often each dish has been cooked in the last two world days."""
    since = house["tick"] - 2 * cfg["ticks_per_day"]
    return Counter(e[3] for e in house.get("kitchen", {}).get("log", []) if e[0] == "cooked" and e[1] >= since)


def choose(house, cfg, pet, room, bit, want=None):
    """The dish this bit and what is to hand make: the one asked for if it can be made; else one it has not found yet,
    the richest, the one cooked least lately."""
    have, n = at_hand(pet, room), lately(house, cfg)
    ok = [d for d, v in D(cfg).items() if bit in v["needs"] and can(cfg, d, have)]
    if want in ok:
        return want
    return min(ok, key=lambda d: ("dish:" + d in pet.get("recipes", {}), -len(D(cfg)[d]["needs"]), n[d], d)) if ok else None


def take_in(house, cfg, pet, room, bit):
    """One of it into the pot: from its paws, else from the room (what was put by, too). SPEC-v4.2 §2.4: returns what
    makes the pot bad, if this does ({"what", "level"}: a poisonous catch it carries, food spoiled on a shelf), or None."""
    if bit in pet["carrying"]:
        pet["carrying"].remove(bit)
        bad = pet.pop("tainted", None) if bit in ("fish", "big fish") else None
        return {"what": bad, "level": "ill"} if bad else None
    s = min((s for s in room["spots"] if s["ready"] and s["bit"] == bit and not s.get("machine")), key=lambda s: (bool(s.get("on")), s["pos"]))
    if s.get("spoiled"):
        room["spots"].remove(s)
        return {"what": "spoiled %s" % bit, "level": "unwell"}
    if s["loose"] or s.get("on"):
        room["spots"].remove(s)
    else:
        from .world import hours
        s["ready"], s["back"] = False, house["tick"] + hours(cfg, cfg["house"]["rooms"][room["type"]]["regrow_hours"])


def cook(house, cfg, pet, room, bit, want=None):
    """craft.process for `cook`: what is to hand goes in the pot, and the stove works on it (machines.start). Returns
    (what it is told, effects, novelty key)."""
    from . import machines
    name = choose(house, cfg, pet, room, bit, want)
    if not name:
        pet.setdefault("tried", {})["%s|cook" % bit] = None
        return "you put the %s in the pot; on its own it would make nothing much: something to go with it would" % bit, {}, None
    d, key = D(cfg)[name], "dish:" + name
    bad = [x for x in (take_in(house, cfg, pet, room, b) for b in d["needs"]) if x]
    if d.get("poison"):
        bad.append({"what": name, "level": "ill"})
    new = craft.learn(house, cfg, pet, key)
    craft.practise(house, cfg, pet, "cooking")
    pet.setdefault("tried", {})["%s|cook" % bit] = name
    pet["cooked"] = house["tick"]
    rec, R = pet["recipes"][key], house.get("recipes", {}).get(key, {})
    founder = house["pets"].get(R.get("by") or "") if rec.get("from") != "found" else None
    title = "%s's %s" % (label(founder), name) if founder and founder is not pet else None
    firsts.noticed(house, cfg, pet, firsts.first(house, cfg, pet, [key]))
    for kid in [p for p in house["pets"].values() if p.get("parent") == pet["id"] and p["room"] == pet["room"] and p["stage"] not in ("egg", "dead") and not p["sleep"]]:
        if craft.learn(house, cfg, kid, key, "watching %s" % label(pet)):   # a young one watching picks it up
            add_event(house, kid, "you watched and saw how: %s" % craft.words(cfg, key))
    later = machines.start(house, cfg, pet, room, "cook", name, name, dish=name, title=title, recipe_by=R.get("by"), **({"bad": max(bad, key=lambda x: x["level"] == "ill")} if bad else {}))
    went = " and ".join(things_a(b) for b in d["needs"])
    said = "you put %s in the pot on the stove: %s" % (went, d["says"]) if new else "you put %s in the pot on the stove for %s" % (went, title or name)
    return "%s; %s" % (said, later), {"curiosity": cfg["craft"]["knowing"]["lift"] if new else 0.0}, "found " + key if new else None


def things_a(bit):
    from .wants import some
    return some(bit)


def keeper(cfg, room):
    """A thing in the room that keeps food: a jar, a box, a basket, or a made keeper."""
    return any(things.kind_of(o) in KEEPERS or cfg["kinds"].get(things.kind_of(o), {}).get("use") == "keeper" for o in things.made(room).values())


def done(house, cfg, room, name, o, r, pet):
    """machines.done for the stove: the pot stands on it, full, and the house is told."""
    K, d, tick = house.setdefault("kitchen", {"n": 0, "log": []}), D(cfg)[r["dish"]], house["tick"]
    K["n"] += 1
    days = C(cfg)["kept_days"] if keeper(cfg, room) else C(cfg)["keep_days"]
    o["pot"] = {"n": K["n"], "dish": r["dish"], "servings": d["servings"], "of": d["servings"], "by": r["by"], "title": r.get("title"), "from": list(d["needs"]),
                "recipe_by": r.get("recipe_by"), "at": tick, "keeps": tick + round(days * cfg["ticks_per_day"]), "ate": {}, **({"bad": r["bad"]} if r.get("bad") else {})}
    o.setdefault("output", {})[r["dish"]] = o.get("output", {}).get(r["dish"], 0) + 1
    log(house, "cooked", tick, r["by"], r["dish"], K["n"])
    who = label(pet) if pet else "someone"
    what = r.get("title") or r["dish"]
    moment(house, "cooked", "%s cooked %s in %s" % (who, what, room["name"]), r["by"], room["id"])
    if not house.setdefault("firsts", {}).get("dish") and pet:
        from . import feats
        house["firsts"]["dish"] = tick
        text = "the first cooked dish in the house: %s, by %s" % (r["dish"], who)
        craft.burst(house, pet, "dish", text)
        feats.record(house, cfg, "first", pet["id"], text, board="THE FIRST DISH: %s BY %s" % (r["dish"].upper(), who.upper()), room=room["id"])
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead") and not p["sleep"] and room["id"] in p["rooms"]:
            add_event(house, p, "the %s you put on is ready on the stove in %s" % (r["dish"], room["name"]) if p is pet else
                      "%s has cooked %s: it is on the stove in %s, enough for %d" % (who, what, room["name"], d["servings"]))


def log(house, *e):
    K = house.setdefault("kitchen", {"n": 0, "log": []})
    K["log"].append(list(e))
    del K["log"][:-2000]


def eat(house, cfg, pet, room, name, o):
    """actions.use on a stove with a pot: a serving, better food than the bowl's, company for whoever ate from it
    lately too, and more if it is a dish it loves."""
    from . import actions
    pot, Cc, tick = o["pot"], C(cfg), house["tick"]
    if not pot["servings"]:
        return "the pot on the %s is empty" % name, {}, None
    pot["servings"] -= 1
    soon = (tick - pet.get("last_eat", LONG_AGO)) * cfg["clock"]["tick_seconds"] <= cfg["effects"]["double_feed_seconds"]
    pet["prev_eat"], pet["last_eat"] = pet.get("last_eat", LONG_AGO), tick
    others = [house["pets"][p] for p, t in pot["ate"].items() if p != pet["id"] and p in house["pets"] and tick - t <= Cc["together_hours"] * cfg["ticks_per_hour"]]
    first_together = bool(others) and not pot.get("shared")
    pot["ate"][pet["id"]] = tick
    log(house, "ate", tick, pet["id"], pot["dish"], pot["n"], [p["id"] for p in others])
    what = pot.get("title") or pot["dish"]
    if soon:
        return "you ate some %s from the pot; it sits heavy on top of the last meal" % what, {"comfort": cfg["materials"]["rules"]["double_feed"], "tags": ["double_feed"]}, "eat"
    fx = needs.food(house, cfg, pet, dict(D(cfg)[pot["dish"]]["food"]))   # SPEC-v4.0 §2: food fills hunger
    if pot.get("bad"):   # SPEC-v4.2 §2.4
        from . import health
        health.poisoned(house, cfg, pet, pot["bad"]["what"], pot["bad"]["level"])
    loved = loves(house, cfg, pet, pot)
    if loved:
        fx["comfort"] = fx.get("comfort", 0.0) + Cc["loved"]
    if others:
        fx["company"] = Cc["company"]
        for p in others:   # (eating from one pot is being with each other: SPEC-v3.6b §2)
            opinions.move(house, cfg, p, pet, "ate_together", "%s and I ate %s together" % (label(pet), what)), opinions.move(house, cfg, pet, p, "ate_together", "%s and I ate %s together" % (label(p), what))   # SPEC-v4.0 §4
            actions.bump(p, cfg, {"company": Cc["company"]})
            add_event(house, p, "%s ate from the pot of %s too: you have eaten together" % (actions.handle(house, p, pet), pot["dish"]))
    if first_together:
        pot["shared"] = tick
        moment(house, "meal", "%s and %s ate %s together" % (build_and([label(p) for p in others]), label(pet), what), pet["id"], room["id"])
    return "you ate some %s from the pot on the %s%s%s" % (what, name, " with %s" % build_and([actions.handle(house, pet, p) for p in others]) if others else "",
                                                       "; you love %s" % pot["dish"] if loved else ""), fx, "eat"


def build_and(names):
    from .build import and_
    return and_(names)


def loves(house, cfg, pet, pot):
    """Does it love this dish (and does it come to, now)? The one its parent cooked for it when it was little, one
    that suits its nature (the playful a sweet one, the bold a fish one), or one it has eaten three times."""
    L, why, dish = pet.setdefault("loves", []), pet.setdefault("loves_why", {}), pot["dish"]
    if dish in L:
        return True
    ate = pet.setdefault("ate", {})
    ate[dish] = ate.get(dish, 0) + 1
    needs, T = D(cfg)[dish]["needs"], pet["temper"]
    because = "your parent made it for you" if pot["by"] == pet.get("parent") and pet["stage"] in ("hatchling", "child", "youngling") else \
        "it suits you" if (T.get("playful", 0.5) >= 0.65 and {"berry", "seed cake"} & set(needs)) or (T.get("bold", 0.5) >= 0.65 and {"fish", "big fish"} & set(needs)) else \
        "you have had it often" if ate[dish] >= C(cfg)["loved_after"] else None
    if because and len(L) < C(cfg)["loves"]:
        L.append(dish)
        why[dish] = because
        return True
    return False


def loves_line(pet):
    """For its mind (the "you feel" line): "you love fish stew (your parent made it for you)"."""
    w = pet.get("loves_why", {})
    return "; ".join("you love %s (%s)" % (d, w.get(d, "")) for d in pet.get("loves", []))


def hourly(house, cfg):
    """A pot not eaten up goes stale and is thrown out."""
    for room in house["rooms"].values():
        for n, o in room["objects"].items() if room["type"] else ():
            pot = o.get("pot")
            if pot and pot["servings"] and house["tick"] >= pot["keeps"]:
                moment(house, "stale", "the %s left in the pot on the %s went stale, and was thrown out" % (pot["dish"], n), None, room["id"])
                log(house, "stale", house["tick"], None, pot["dish"], pot["n"], pot["servings"])
                pot["servings"] = 0


# ---- a body (machines.targets for the stove; body.py for the pot) ----

def target(house, cfg, pet, room):
    """A dish it knows that what is to hand makes: (the bit to start with, the dish, how strongly). One it loves
    first, then the one cooked least lately."""
    have, n = at_hand(pet, room), lately(house, cfg)
    known = [k[5:] for k in pet.get("recipes", {}) if k.startswith("dish:") and k[5:] in D(cfg)]
    ok = [d for d in known if can(cfg, d, have)]
    if not ok:   # (nothing it knows: what is to hand goes in the pot, to find out what it makes)
        new = sorted((d for d in D(cfg) if "dish:" + d not in pet.get("recipes", {}) and can(cfg, d, have)), key=lambda d: (-len(D(cfg)[d]["needs"]), d))
        wanted = any(w["what"] == "cook" for w in pet.get("wants", []))
        return (D(cfg)[new[0]]["needs"][0], new[0], 1.5 if wanted else 0.3) if new else None
    d = min(ok, key=lambda d: (d not in pet.get("loves", []), n[d], -len(D(cfg)[d]["needs"]), d))
    wanted = any(w["what"] == "cook" for w in pet.get("wants", []))
    return D(cfg)[d]["needs"][0], d, 1.5 if wanted else 0.6


def pot_here(room, pet):
    """The stove here with something in its pot it has not eaten from: (name, object) or None."""
    return next(((n, o) for n, o in room["objects"].items() if (o.get("pot") or {}).get("servings") and pet["id"] not in o["pot"]["ate"]), None)


def eat_targets(house, cfg, pet, near):
    """body.targets for `eat from the pot`: a pot here, and it hungry enough, and not just eaten."""
    room = house["rooms"][pet["room"]]
    p = pot_here(room, pet)
    if not p or feel.level(pet, needs.appetite(cfg, pet)) < C(cfg)["hungry"] or (house["tick"] - pet.get("last_eat", LONG_AGO)) * cfg["clock"]["tick_seconds"] <= cfg["effects"]["double_feed_seconds"]:
        return []
    n, o = p
    eating = [x for x in house["pets"].values() if x is not pet and x["room"] == room["id"] and (((x.get("body") or {}).get("now") or {}).get("do") == "eat" and (x["body"]["now"].get("what") == n))]
    from .actions import handle
    where = "%s%s" % (o["pot"]["dish"], " with %s" % build_and([handle(house, pet, x) for x in eating]) if eating else "")
    wanted = any(w["what"] == "meal" for w in pet.get("wants", []))
    return [{"what": n, "where": where, "goal": near(o["pos"]), "bonus": cfg["body"]["want"] * (1.5 if wanted else 0.8) + (1.0 if pot_loved(pet, o) else 0.0)}]


def pot_loved(pet, o):
    return o["pot"]["dish"] in pet.get("loves", [])


# ---- wants (wants.candidates) ----

GROUPS = {"cook": "tend", "meal": "tend"}
SERVED = ("cook", "meal")


def stove(house):
    from .machines import built
    s = built(house, "stove")
    return s if s and not s[2]["fix"]["built"].get("worn") else None


def wants(house, cfg, pet, known, add):
    """To cook a dish it knows, with what it carries; to eat from a pot on the stove, hungry enough."""
    s = stove(house)
    if not s or s[0]["id"] not in pet["rooms"]:
        return
    room, n, o = s
    pot, Cc = o.get("pot") or {}, C(cfg)
    if pot.get("servings") and pet["id"] not in pot["ate"] and feel.level(pet, needs.appetite(cfg, pet)) >= Cc["hungry"]:
        loved = pot["dish"] in pet.get("loves", [])
        add("meal", str(pot["n"]), "there is %s on the stove in %s: you want some%s" % (pot.get("title") or pot["dish"], room["name"], ", and you love it" if loved else ""),
            "ate %s from the pot" % pot["dish"], Cc["want"] * (1.5 if loved else 1.0), room=room["id"], pot=pot["n"])
    if pot.get("servings") or pet["stage"] in ("hatchling", "child", "youngling"):
        return
    have = Counter(pet["carrying"])
    for k in pet.get("recipes", {}):
        d = k[5:] if k.startswith("dish:") else None
        if d in D(cfg) and any(b in have for b in D(cfg)[d]["needs"]) and can(cfg, d, have + Counter(s_["bit"] for s_ in room["spots"] if s_["ready"] and not s_.get("machine"))):
            add("cook", d, "you want to cook %s at the stove in %s: you have what it takes" % (d, room["name"]), "cooked %s" % d, Cc["cook_want"], room=room["id"], dish=d)
            break
    else:   # (18 October 2026: fish were caught, carried and put down; with a stove, a fish in the paws wants cooking)
        f = next((b for b in ("big fish", "fish") if b in have), None)
        d = f and cfg["craft"]["rules"].get((f, "cook"), {}).get("gives")
        if d:
            add("cook", d, "you have %s: you want to cook it at the stove in %s" % (things_a(f), room["name"]), "cooked %s" % d, Cc["cook_want"], room=room["id"], dish=d)


def met(house, cfg, pet, w):
    if w["what"] == "meal":
        s = stove(house)
        pot = (s[2].get("pot") if s else None) or {}
        return pot.get("n") == w["pot"] and pet["id"] in pot["ate"]
    return pet.get("cooked", LONG_AGO) >= w["since"]


def possible(house, cfg, pet, w):
    s = stove(house)
    pot = (s[2].get("pot") if s else None) or {}
    if w["what"] == "meal":
        return pot.get("n") == w["pot"] and bool(pot.get("servings"))
    return bool(s) and not pot.get("servings") and any(b in pet["carrying"] for b in D(cfg)[w["dish"]]["needs"])


def lean(house, cfg, pet, out):
    for w in pet.get("wants", []):
        if w["what"] in SERVED and w.get("room") and w["room"] != pet["room"]:
            out["rooms"].add(w["room"])


# ---- for the page (machines.view; CONTRACT) ----

def view(house, cfg, room, o):
    pot = o.get("pot")
    if not pot or not pot["servings"]:
        return None
    by, rb = house["pets"].get(pot["by"]), house["pets"].get(pot.get("recipe_by") or "")
    eating = [label(p) for p in house["pets"].values() if p["room"] == room["id"] and ((p.get("body") or {}).get("now") or {}).get("do") == "eat"
              and ((p.get("body") or {}).get("now") or {}).get("what") in room["objects"] and room["objects"][p["body"]["now"]["what"]] is o]
    return {"dish": pot["dish"], "servings": pot["servings"], "of": pot["of"], "from": pot["from"], "by": pot["by"], "by_name": label(by) if by else None,
            "title": pot.get("title"), "recipe_by": label(rb) if rb else None, "at": pot["at"], "keeps": pot["keeps"], "eating": eating}
