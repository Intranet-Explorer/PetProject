"""The engine's front door (SPEC §3, §16): the tick loop, a websocket for the view, and a few read-only pages
of JSON for the drawer. Binds to localhost and checks Origin on every websocket.

    uv run python -m engine.server                    # the real clock
    PET_PROFILE=showcase uv run python -m engine.server   # the short-life profile, in turbo time
    PET_DATA=data.showcase PET_PAUSED=1 PET_PORT=8001 uv run python -m engine.server   # look at an archived run; nothing moves
"""
import asyncio
import gzip
import hashlib
import json
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import actions, body, craft, firsts, wants, director, feel, hub, order, life, metrics, mind, pages, physics, radio, songs, story, things, walls
from . import needs, opinions, talk   # SPEC-v4.0
from . import lab4   # SPEC-v4.0.5 §8
from . import habits   # SPEC-v5.3 (helper B)
from . import sheet
from . import contracts as K   # SPEC-v4.2 E
from .tick import Engine, model_brains, stub_brains
from . import world
from . import build
from . import machine
from . import machines, pond, rail, store
from .world import ROOT, STAGE_WORD, alive, label, load_config, power_on, relation

# 19 October 2026 (REVIEW-v4.0.4 §10): every line of the log says when, how bad and whose (uvicorn's own lines too: main)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
cfg = load_config(profile=os.environ.get("PET_PROFILE") or None)
DATA = ROOT / os.environ.get("PET_DATA", "data")
DIST = ROOT / "view" / "dist"
PAUSED = bool(os.environ.get("PET_PAUSED"))   # open a finished run to look at and replay, without living it any further
try:
    eng = Engine(cfg, DATA, stub_brains if cfg["stub"]["enabled"] else model_brains, readonly=PAUSED)   # ... and without writing a byte of it
except ValueError as e:   # (19 October 2026, REVIEW-v4.0.4 A2: a house that cannot be started this way says why in one line, and exits EX_CONFIG)
    print("the house cannot start: %s" % e, file=sys.stderr)
    raise SystemExit(78)
clients = {}   # websocket -> {"seen": when it last reported an attentive visitor, "room": the room it is showing, "have": the sections it keeps, by hash}
sent = {"bytes": 0}   # SPEC-v4.0.5 §8: the size of the last message a page was sent, for the Lab


def first_egg():
    """What the first egg of a new house is given (§13 part 0): the last v2 pet's words and body."""
    path = ROOT / "first-egg.json"
    if not path.exists():
        return None, None
    d = json.loads(path.read_text())
    return [{"by": None, "who": d["who"], "kind": "message", "text": d["message"], "tick": 0}], d["genome"]


def begin():
    """The first egg of a new house. (SPEC-v4.0.5 §9.3, 19 October 2026: not until someone comes to look, the first
    websocket client, or PET_HEADLESS=1, so a check or a wrong start does not write a house.)"""
    if not eng.house["lineage"] and not PAUSED:
        eng.new_lineage(*first_egg())


if os.environ.get("PET_HEADLESS"):
    begin()


def present():
    """The room a visitor is attending to: a view tab is focused and has had input lately (SPEC §4)."""
    live = [c for c in clients.values() if time.time() - c["seen"] < 45]
    return live[0]["room"] if live else None


def pet_view(p):
    """One pet as the view needs it. Numbers are for the view and the Lab; no pet ever sees them."""
    h = eng.house
    out = {k: p.get(k) for k in ("id", "name", "stage", "room", "pos", "gen", "parent", "children", "word", "genome", "temper", "eggs",
                                 "laid", "born", "died", "cause", "lineage", "stage_before", "mutation")}
    # SPEC-v4.2 A: the cause in words (§2.7), on the hob or, once it is buried, on its life record
    out["cause_words"] = p.get("cause_words") or (p["life"].get("cause_words") if isinstance(p.get("life"), dict) else None)
    # SPEC-v4.2 A: end
    # the visitor's naming, for the pet's card: the name offered, and whether the pet has taken it
    out["naming"] = {"offered": p["called"], "took": (p.get("name") or "").lower() == p["called"].strip().lower(),
                     "at": (p.get("named") or {}).get("tick")} if p.get("called") else None
    out.update(label=label(p), buried=bool(p.get("buried")), made=p.get("made", 0), useful=len(p.get("useful", [])), family=p.get("family", 1))
    out["byname"] = p.get("byname")   # SPEC-v3.5.8 §2: "Clementine, called Open Hand"
    out["riding"] = p.get("riding")   # SPEC-v3.5.12 §3: the train it rides in, if any
    out["design"] = p.get("design")   # SPEC-v3.6d §9: the design in hand, for its sign, its card and the quest log
    out.update(v4_view(p))   # SPEC-v4.0 §11: character, mood, hurt, the day's aims, its friends and enemy
    if p["stage"] == "dead":
        out["days"] = (p.get("life") or {}).get("days")
        # view only: how far it has faded towards its stone, 0 to 1
        out["fade"] = min(1.0, (h["tick"] - p["died"]) * cfg["clock"]["tick_seconds"] / (cfg["life"]["fade_minutes"] * 60))
        return out
    if p["stage"] == "egg":
        out["hatches_in"] = max(0, cfg["life"]["egg_minutes"] * 60 - (h["tick"] - p["laid"]) * cfg["clock"]["tick_seconds"]) * cfg["pace"]   # in real seconds: it is read by the visitor
        return out
    plan = p["plan"]
    said = p["said"] if p["said"] and (h["tick"] - p["said"]["tick"]) * cfg["clock"]["tick_seconds"] <= 30 else None
    if said:
        to = h["pets"].get(said["to"])
        said = dict(said, to_name="the visitor" if said["to"] == "visitor" else label(to) if to else None)
    step = plan["steps"][min(plan["i"], len(plan["steps"]) - 1)] if plan and not plan.get("idle") else None
    out.update(
        needs={n: round(v, 1) for n, v in p["needs"].items()}, levels={n: feel.level(p, n) for n in p["needs"]},
        feelings=feel.feelings(p), felt={n: needs.WORDS[n][feel.level(p, n)] for n in p["needs"]}, seems=feel.seems(p), doing=mind.doing(h, p), asleep=bool(p["sleep"]), thinking=p["thinking"],
        carrying=p["carrying"], following=p["following"], weak=p["weak"], said=said, days=round(life.days(h, cfg, p), 1),
        project=p["project"], progress=build.progress(h, cfg, p), offers=[{"from": o["from"], "kind": o["kind"]} for o in p["offers"]],
        plan={"intention": plan["intention"], "thought": plan["thought"], "expect": plan["expect"], "i": plan["i"], "why": plan["why"],
              "steps": [actions.words(s) for s in plan["steps"]], "acting": plan["left"] is not None and not plan.get("idle"),
              "idle": bool(plan.get("idle"))} if plan else None,
        body=body.doing(cfg, h, p) if cfg["body"]["on"] and not p["sleep"] and not world.busy(p) else None,   # SPEC-v3.3 §1, §5.4
        # SPEC-v3.4: what it wants (in its mind's own words), how practised it is, what it has found out
        wants=[{"text": w["text"], "what": w["what"], "since": w["since"]} for w in sorted(p.get("wants", []), key=lambda w: (
            w["key"] != ((body.state(p)["now"] or {}).get("want") or ""), w["what"] not in wants.SERVED, -w["since"]))],   # the one its body is about just now first, then those its body can serve skills=craft.skills_line(cfg, p), recipes=craft.recipe_lines(cfg, p, 12),
        sheet=sheet.card(h, cfg, p),   # (24 November 2026) its pursuit, its place, its fear, its food, and whether it is at its pursuit now
        focus=focus_view(p), sign=sign_view(p), habits=body.habits(h, cfg, p), react=body.state(p).get("react"), orderly=p["temper"].get("orderly"),
        step=step and step.get("type"), last_plan=p["last_plan"], calls_hour=len(p["calls"]), spring=p["spring"] > 0,
        portrait=p["portraits"][-1] if p["portraits"] else None, old=life.span(cfg, p) - life.days(h, cfg, p) <= 1,
        songs=[e["id"] for e in p.get("songs", []) if e["id"] in h.get("songs", {})],   # SPEC-v3.1
        animals=[{"id": c["id"], "kind": c["kind"], "name": c.get("name"), "room": c["room"]} for c in h["creatures"] if c.get("tame") == p["id"]],
        read=p.get("read", [])[:3],
        # SPEC-v3.2 §5, §6: in plain words for the page. `mood`: what is wrong, worst first, at most two; `emote`: one
        # strong feeling, if there is one; `act`: the step it is on.
        stage_word=STAGE_WORD.get(p["stage"], p["stage"]), mood=mood(p), emote=emote(p),
        act=story.act_of(h, p, plan["steps"][min(plan["i"], len(plan["steps"]) - 1)]) | {"since": plan.get("step_began", plan["started"])} if world.busy(p) else None,
    )
    out["ambition"] = p.get("ambition") and firsts.third(p["ambition"])   # SPEC-v3.5.4 §9: on its card
    # SPEC-v4.2 E: "old and slow" (§2.1, §11.3) is the lives part's own, an elder's last days
    if K.on(cfg, "lives"):
        out["old"] = bool(p.get("old"))
    # SPEC-v4.2 E: end
    if K.on5(cfg):   # SPEC-v5.0 §4.1, §5: its scrap-points, a pile on its card (the visitor sees the number; the hobs never do)
        out["scrap"] = int(p.get("scrap") or 0)
    return out


EMOTE = {"energy": "tired", "comfort": "uneasy", "curiosity": "bored", "company": "lonely"}
EMOTE.update(hunger="hungry", safety="afraid", pride="low")   # SPEC-v4.0 §2 (needs.WORDS: the four needs' words and the three new ones)


def mood(p):
    worst = sorted(p["needs"], key=lambda n: -feel.level(p, n))
    out = [needs.WORDS[n][feel.level(p, n)] for n in worst if feel.level(p, n) >= 2][:2]
    return out or [needs.WORDS[worst[-1]][feel.level(p, worst[-1])]]


def emote(p):
    worst = max(p["needs"], key=lambda n: feel.level(p, n))
    return EMOTE[worst] if feel.level(p, worst) >= 3 else "content" if all(feel.level(p, n) <= 1 for n in p["needs"]) else None


def focus_view(p):
    """What its mind is about, with the plain words for it (SPEC-v3.3 §0: a stranger can say roughly why)."""
    f = p.get("focus")
    if not f:
        return None
    who, what = eng.house["pets"].get(f.get("who") or ""), f.get("what")
    on = label(who) if who else "the " + what if what else {"be with": "someone", "tend": "something", "stay near": "something"}.get(f["type"], "")
    return dict(f, says=actions.FOCUS_SAYS[f["type"]].format(on=on))


def sign_view(p):
    """The sign over its head while it carries out a step it decided (§5.4): what it is at, and the icon for it."""
    if not world.busy(p):
        return None
    plan = p["plan"]
    step = plan["steps"][min(plan["i"], len(plan["steps"]) - 1)]
    t = step.get("type")
    icon = cfg["process_signs"].get(actions.norm(step.get("how"))) if t == "process" else None   # SPEC-v3.4 §3.1: each way of changing a thing has its own sign
    return {"icon": icon or cfg["signs"].get(t), "word": mind.doing(eng.house, p), "step": t, "walking": plan["left"] is None}


def v4_view(p):
    """SPEC-v4.0 §11: what the page shows of a hob's character and life with others (each part only while it is on)."""
    from . import bonds, character, opinions
    out = {}
    if character.on(cfg):
        out.update(traits={a: character.trait(p, a) for a in character.AXES}, mood4=character.mood(p), mood4_why=(p.get("mood") or {}).get("why"),
                   quirks=p.get("quirks", []), values=p.get("values", []))   # (`mood4`: the v4 mood; `mood` stays v3.2's few plain words)
    if opinions.on(cfg):
        ops = {k: v for k, v in (p.get("opinions") or {}).items() if k != "visitor" and k in eng.house["pets"] and eng.house["pets"][k]["stage"] != "dead"}
        out["likes"] = {k: v["liking"] for k, v in ops.items()}   # (the family page's web, and how much on the card)
        out["top"] = {"friends": sorted(ops, key=lambda k: -ops[k]["liking"])[:2], "enemy": min(ops, key=lambda k: ops[k]["liking"], default=None) if ops and min(o["liking"] for o in ops.values()) < 0 else None,
                      "visitor": (p.get("opinions") or {}).get("visitor", {}).get("liking")}
    out.update(hurt=p.get("hurt"), sick=p.get("sick"), aims=p.get("aims"), outcast=p.get("outcast"), shunned=p.get("shunned"))
    return out


def ties(h):
    """Every pair of living hobs with a tie: [{a, b, kind}] (close, friend, rival, enemy)."""
    from . import bonds
    live = sorted(p["id"] for p in h["pets"].values() if p["stage"] not in ("egg", "dead"))
    return [{"a": a, "b": b, "kind": k} for i, a in enumerate(live) for b in live[i + 1:] for k in [bonds.kind(h, a, b)] if k]


def visitor4_view(h):
    """The visitor's side: the inbox (unanswered, and the last five answered), the last 30 things the visitor did, who is
    protected. (`visitor` in the snapshot is the room the visitor is looking at.)"""
    v = h.get("visitor") or {}
    inbox = [q for q in v.get("inbox", []) if not q.get("gone") and h["pets"].get(q["pet"], {}).get("stage", "dead") != "dead"]   # (not a dead hob's)
    # SPEC-v4.2 D: and the visitor's hour beside a sick hob, for the page's timer (§9.4: "tend", {hob id: the tick it is up}); tend and remedy go by /api/visitor/{tool}
    return {"inbox": [q for q in inbox if not q.get("answer")] + [q for q in inbox if q.get("answer")][-5:], "log": v.get("log", [])[-30:], "protect": v.get("protect", {}),
            "tend": v.get("tend", {})}
    # SPEC-v4.2 D: end


def room_view(r):
    h = eng.house
    if not r["type"]:
        return {"id": r["id"], "cell": r["cell"], "type": None, "doors": r["doors"]}
    objs = {}
    for n, o in r["objects"].items():
        v = {"pos": o["pos"], "state": o.get("state")}
        if "made" in o:
            m = o["made"]
            owner = h["pets"].get(m["owner"])
            v["made"] = {"id": m["id"], "recipe": m["recipe"], "owner": m["owner"], "owner_name": label(owner) if owner else None, "by": m["by"],
                         "heirloom": m.get("heirloom"), "behavior": m.get("behavior"), "active": bool(o.get("active")), "uses": m["uses"],
                         "ups": m["ups"], "useful": things.useful(m, cfg), "called": m.get("called"), "tick": m["tick"], "star": m.get("star"),   # (SPEC-v3.5.4 §10)
                         "worn": [k for k in ("damp", "dusty", "eaten") if m.get(k)],
                         "loud": bool(things.prop(cfg, o).get("loud")),                           # it sounds when used (SPEC-v3.3 §4)
                         "hums": bool(o.get("active") and things.doing(cfg, o).get("loud")),     # it is making a noise by itself now
                         # SPEC-v3.5.8: its maker's title shows only where it matters; and what is kept from now on for its card
                         "title_shown": bool(m["recipe"].get("title")) and order.kept(h, cfg, r, n), "from": m.get("bits", []),
                         **{k: m[k] for k in ("how", "made_in", "users", "words", "design", "parts") if m.get(k)}}   # (SPEC-v3.6d: a design's effects and parts)
            if o.get("home"):
                v["home"] = o["home"]   # SPEC-v3.3 §2.3: where it belongs: {room, on} or {room, pos}
            v["where"], v["stored"] = store.where(h, cfg, r, n)   # SPEC-v3.5.12 §1: where it is, in plain words
        elif "memorial" in o:
            v["memorial"] = o["memorial"]
            if o.get("words"):
                v["words"] = o["words"]   # SPEC-v3.5.8: what has been written on the stone
        else:
            v["fix"] = {k: (True if k == "water" else x) for k, x in o["fix"].items() if k != "states"}
            v["says"] = actions.fixture_says(o["fix"])   # what it is, for the visitor's hover card
            if o["fix"].get("machine"):
                v["state"] = machine.light(h, cfg)   # SPEC-v3.5 §4.3: its lights are up while it is in use
            if "water" in o["fix"]:
                v["water"] = o["fix"]["water"]
            if o["fix"].get("plant"):
                v["grow"] = o["grow"]
            if "meal" in o["fix"]:
                v["servings"] = o["servings"]
        build.view(h, cfg, r, n, o, v)   # SPEC-v3.5 §4: a thing being built or built: its picture, its title, who built it
        if o.get("item") and K.on5(cfg):   # SPEC-v5.0 §5: an item's card in words (pages.item_view), and broken for the room
            v["item"] = pages.item_view(h, cfg, o, n)
        machines.view(h, cfg, r, n, o, v)   # SPEC-v3.6b §1: a machine's state, its tray, its pot
        hub.statue_view(h, cfg, o, v, DATA)   # SPEC-v3.5.1 §4: whose statue, in stone, its name and last words
        if o.get("screen"):   # SPEC-v3.5.1 §3: what was last asked at this screen and read on it
            v["screen"] = dict(o["screen"], by=label(h["pets"][o["screen"]["pet"]]) if o["screen"]["pet"] in h["pets"] else "someone")
        if o.get("planted"):   # SPEC-v3.4 §3.5
            v["planted"] = {"what": o["planted"]["what"], "stage": craft.stage(o["planted"]), "wilted": bool(o["planted"].get("wilted"))}
        if o.get("wall"):
            v["wall"] = True
        for k in ("effect_on", "sputter"):   # SPEC-v3.6d §9: a design's effect at work, a failure just built
            if o.get(k):
                v[k] = o[k]
        if o.get("on"):
            v["on"] = o["on"]   # SPEC-v3.3 §2.2: put away on (or in) this; it stands on that thing's tile
        if order.cap(cfg, o):
            v["store"] = {"cap": None if order.keeps(o) else order.cap(cfg, o), "holds": order.held(r, n), "bits": [s["bit"] for s in r["spots"] if s.get("on") == n],
                          "inside": bool(o.get("fix", {}).get("inside") or cfg["kinds"].get(o.get("made", {}).get("recipe", {}).get("kind"), {}).get("inside"))}
            # SPEC-v4.2 E: food on it that has spoiled (§2.4, §11.3: a tint), only once any has
            bad = [s["bit"] for s in r["spots"] if s.get("on") == n and s.get("spoiled")]
            if bad:
                v["store"]["spoiled"] = bad
            # SPEC-v4.2 E: end
        objs[n] = v
    return {"id": r["id"], "cell": r["cell"], "type": r["type"], "name": r["name"], "doors": r["doors"], "paint": r["paint"], "painted": build.painted(h, cfg, r), "outdoor": bool(r.get("outdoor")),
            "shut": [k.split("|")[1] for k, t in h["shut"].items() if k.startswith(r["id"] + "|") and t > h["tick"]],
            "wet": r["wet_until"] > h["tick"], "cold": r["cold_until"] > h["tick"], "lit": things.light_on(h, cfg, r),
            "marks": [dict(m, clarity=round(walls.clarity(cfg, r, m, h["tick"]), 2), by_name=mark_by(m)) for m in r.get("marks", [])],
            "mess": order.clutter(h, cfg, r), "mess_says": order.MESS[order.clutter(h, cfg, r)], "areas": r.get("areas", []),   # SPEC-v3.3 §2
            "sounding": r.get("sounding_until", 0) > h["tick"], "objects": objs, "found": r["found"], "by": r["by"],
            # what can be gathered, and (SPEC-v3.4 §5) what a bit the room grows is growing on, picked bare or not; bits put away are in `store.bits`
            "spots": [{"bit": s["bit"], "pos": s["pos"], "ready": s["ready"], "loose": s["loose"], **({"machine": s["machine"]} if s.get("machine") else {})} for s in r["spots"] if not s.get("on") and (s["ready"] or not s["loose"])]}


def mark_by(m):
    p = eng.house["pets"].get(m["by"])
    return "the visitor" if m["by"] == "visitor" else label(p) if p else "someone long gone"


def snapshot():
    h = eng.house
    lab4.keep(h, cfg)   # SPEC-v4.0.5 §8: the day's needs, memories and aims, for the Lab's "Today" (the night clears the aims)
    recent = lambda rows, secs: [x for x in rows if (h["tick"] - x["tick"]) * cfg["clock"]["tick_seconds"] <= secs]
    return {
        # SPEC-v3.1: songs lately sung (the view plays them), every version the living know, what the box just said, and
        # which discoveries have come
        "sung": recent(h.get("sung", []), 30), "songs": {e: h["songs"][e] for p in h["pets"].values() for e in [x["id"] for x in p.get("songs", [])] if e in h.get("songs", {})}
        | {s["song"]: h["songs"][s["song"]] for s in recent(h.get("sung", []), 30)},
        "radio": {"on": radio.is_on(h), "here": bool(radio.boxes(h)), "said": recent(h.get("radio", {}).get("said", []), 45)},
        "arrived": h.get("v31", {}).get("arrived", {}), "read_glow": (h["tick"] - h.get("read_glow", -10**9)) * cfg["clock"]["tick_seconds"] <= 20,
        "pace": cfg["pace"], "machine": machine.view(h, cfg),   # SPEC-v3.5 §4.3: what the vending machine holds, for "Stock the machine"
        # SPEC-v3.3: the visitor's music and radio (§3), the small sounds pets make by themselves (§4: each numbered, to
        # be played once), and the body's activities with their icons (§1.1, §5.4)
        "dj": {"music": (h.get("dj") or {}).get("music"), "moods": list(cfg["music"]["tunes"]),
               "radio": {"on": radio.is_on(h), "theirs": any(n != "little radio" for _, n, _ in radio.boxes(h)), "rooms": [r["id"] for r, _, _ in radio.boxes(h)],
                         # SPEC-v3.5.1 §5: the station it is tuned to (the page plays its stream), the others, and the song on now
                         "station": radio.station(h, cfg)["id"], "stations": [{k: x[k] for k in ("id", "name", "mood", "sound", "stream", "home")} for x in cfg["radio"]["stations"]],
                         "now": {"title": radio.song_words(eng.radio_song).strip('"').replace('" by ', " - "), "at": h["tick"]} if eng.radio_song and radio.is_on(h) else None}},
        "vox": recent(h.get("vox", []), 20),
        "ticker": hub.ticker(h, cfg),   # SPEC-v3.5.1 §2: what the machine room's lit sign runs
        "invented": h.get("invented", {}),   # SPEC-v3.5 §3: the kinds this house invented, each with its parts (the view draws them)
        "bursts": recent(h.get("bursts", []), 20),   # SPEC-v3.4 §5: a want fulfilled or a thing found out, each numbered, to be shown once
        "activities": {n: {"icon": a.get("icon"), "passive": bool(a.get("passive")), "rest": bool(a.get("rest"))} for n, a in cfg["activities"].items()},
        # SPEC-v3.2: the one plain sentence about the house now, and the steps finished in the last world minute or so
        "now": story.now(h, cfg), "acts": recent(h.get("acts", []), 40),
        "tick": h["tick"], "clock": h["clock"], "weather": h["weather"], "power": power_on(h), "size": [cfg["W"], cfg["H"]],
        "tick_seconds": cfg["clock"]["tick_seconds"], "day_seconds": cfg["clock"]["day_seconds"], "turbo": cfg["clock"]["turbo"], "shift": cfg.get("shift"),
        "profile": cfg["profile"], "start": h["start"], "door_tiles": h["door_tiles"], "lineage": h["lineage"],
        "rooms": [room_view(r) for r in h["rooms"].values()], "pets": [pet_view(p) for p in h["pets"].values()],
        "creatures": [{k: v for k, v in c.items() if k not in ("held", "swept", "shooed", "legs", "route", "asked")} for c in h["creatures"]], "moments": h["moments"][-60:], "events": h["events"][-8:],
        "chronicle": h["chronicle"][-1:], "visitor": present(), "population": cfg["population"]["most"],
        "sayings": [{"text": c["text"], "gens": len(c["gens"]), "truth": c["truth"]} for c in story.sayings(h, 3)],
        # SPEC-v3.5.12: the rail (null until built), what is in the cart, and the garden's resting place
        "rail": rail.view(h, cfg), "cart": rail.cart_view(h, cfg), "resting": h.get("resting"), "pond": pond.view(h, cfg), "machines": machines.views(h, cfg),
        # SPEC-v3.6c: the garden gate, the great clear-out, and the seasons for new things
        "paused": PAUSED,   # (an archived run, opened to look at: its clock is meant to stand still)
        "v4": {k: bool(cfg.get(k, {}).get("on")) for k in ("traits", "needs4", "opinions", "talk", "ladder", "health", "brain4", "planner", "visitor4")},   # SPEC-v4.0: which parts are on
        "talks": [lab4.talk_view(h, t) for t in talk.recent(h, 300)] if talk.on(cfg) else [],   # SPEC-v4.0 §5, §11: recent conversations, for the bubbles (SPEC-v4.2 E: with their minds by hob)
        "bonds": h.get("bonds", []) if opinions.on(cfg) else [],
        "scuffles": (h.get("scuffles") or [])[-20:] if cfg.get("ladder", {}).get("on") else [],   # SPEC-v4.0 §7.3: a scuffle and its blood, for the room
        "ties": ties(h) if opinions.on(cfg) else [],   # SPEC-v4.0 §6.3: friends, close bonds, rivals, enemies, for the web
        "visitor4": visitor4_view(h) if cfg.get("visitor4", {}).get("on") else None,   # SPEC-v4.0 §10: the inbox, what the visitor did, who is protected
        "outdoors": h.get("outdoors"), "clearout": dict({k: v for k, v in h["clearout"].items() if k not in ("plan", "moved", "planned")}, moved=sum(len(x) for x in h["clearout"].get("moved", {}).values()))
        if h.get("clearout") else None, "spotlights": {k: v for k, v in h["spotlights"].items() if k not in ("migrated", "off")} if h.get("spotlights") and S_ON() else None,
        **({"spirit": True} if K.on(cfg) else {}),   # SPEC-v4.2 E: §11's thoughts, decline and banners are drawn (off: the key is not sent)
        **({"v5": {"board": pages.board_view(h), **({"tier": lab4.header(h, cfg)} if K.on51(cfg, "knowledge") else {}),
                   **({"sites": pages.projects.view(h, cfg)} if K.on53(cfg, "projects") else {}),
                   **({"marks53": habits.view(h, cfg)} if K.on53(cfg, "habits") else {})}} if K.on5(cfg) else {}),   # SPEC-v5.3 §2.3 (helper A): the sites by stage   # SPEC-v5.0 §5: the work board; items, piles and scrap are drawn (off: not sent); SPEC-v5.1 §8: the house's tier for the header
    }


def sections(state):
    """SPEC-v4.0.5 §7.2: the heavy parts of a snapshot, each with a hash: every room's objects and spots, and the kinds
    the house invented. A page says which it keeps (`have`); one it keeps is sent as null until it changes. (And the
    dead, whose stones the room draws: on live, 26 of 33 hobs and a third of `pets`; without them a message was 128 KB.)
    SPEC-v5.0 §5: and the work board, which changes at a deficit scan (ten ticks) at most."""
    parts = {"invented": state["invented"], "dead": [p for p in state["pets"] if p["stage"] == "dead"]}
    if "v5" in state:
        parts["board"] = state["v5"]["board"]
    for r in state["rooms"]:
        if r["type"]:
            parts["objects:" + r["id"]], parts["spots:" + r["id"]] = r["objects"], r["spots"]
    return {k: hashlib.blake2b(json.dumps(v, sort_keys=True).encode(), digest_size=8).hexdigest() for k, v in parts.items()}


def trimmed(state, hashes, have):
    """The snapshot as one page is sent it: a section it keeps at the same hash is null, and the hashes go with it.
    (The recorder keeps the whole snapshot: it is written before this.)"""
    same = {k for k, v in hashes.items() if have.get(k) == v}
    rooms = [dict(r, **{f: None for f in ("objects", "spots") if "%s:%s" % (f, r["id"]) in same}) if r["type"] else r for r in state["rooms"]]
    dead = {"pets": [p for p in state["pets"] if p["stage"] != "dead"], "dead": None} if "dead" in same else {}   # (the living only, and `dead: null`)
    v5 = {"v5": dict(state["v5"], board=None)} if "board" in same else {}   # SPEC-v5.0 §5
    return dict(state, rooms=rooms, invented=None if "invented" in same else state["invented"], hashes=hashes, **dead, **v5)


class Recorder:
    """Keeps what the view was sent, a few times a world minute, so a run can be played back afterwards
    (SPEC-v3 amendment: a turbo run is replayed, not watched live). One file per world day; each snapshot is a
    whole gzip stream of its own appended to it, so a kill or a power cut can cost one snapshot and no more."""

    def __init__(self):
        self.dir, self.day, self.file = DATA / "replay", None, None

    def write(self, snap):
        if snap["tick"] % cfg["replay"]["every_ticks"] or not snap["lineage"]:
            return
        key = (snap["lineage"]["id"], snap["clock"]["day"])
        if key != self.day:
            self.close()
            d = self.dir / ("lineage-%d" % key[0])
            d.mkdir(parents=True, exist_ok=True)
            self.day, self.file = key, open(d / ("day-%04d.jsonl.gz" % key[1]), "ab")
            for old in sorted(d.glob("day-*.jsonl.gz"))[:-cfg["replay"]["keep_days"]]:
                old.unlink()
        self.file.write(gzip.compress((json.dumps(snap) + "\n").encode(), 6))
        self.file.flush()

    def close(self):
        if self.file:
            self.file.close()
            self.file = None


recorder = Recorder()


async def broadcast(state=None):
    state = state or snapshot()
    hashes = sections(state)
    for sock in list(clients):
        try:
            text = json.dumps(trimmed(state, hashes, clients[sock].get("have", {})), separators=(",", ":"), ensure_ascii=False)
            sent["bytes"] = len(text)
            await asyncio.wait_for(sock.send_text(text), 2.0)   # (19 October 2026, REVIEW-v4.0.4 A9: a client that does not read is let go, and the tick goes on)
        except Exception:
            clients.pop(sock, None)


def skipping():
    """(24 November 2026) With [clock] skip_night: is every living hob asleep? Then the clock runs as fast as it
    can until one wakes, waiting only for the night's thinking to land: a night was half an hour of nothing to watch."""
    if not cfg["clock"].get("skip_night") or PAUSED:
        return False
    up = [p for p in eng.house["pets"].values() if p["stage"] not in ("egg", "dead")]
    return bool(up) and all(p.get("sleep") for p in up)


async def loop():
    turbo, sent = cfg["clock"]["turbo"], 0.0
    while True:
        started = time.monotonic()
        try:
            turbo = cfg["clock"]["turbo"] or skipping()
            ended = not eng.house["lineage"] or eng.house["lineage"]["ended"] is not None or PAUSED   # (no lineage: nobody has come to look yet)
            if ended and eng.house["lineage"] and cfg["life"]["auto_lineage"] and not PAUSED:
                eng.new_lineage()
            elif ended or (turbo and eng.busy()):   # an empty house waits to be started again; in turbo the world waits for a thought
                await asyncio.sleep(1.0 if ended else 0.02)
                if ended and eng.house["lineage"] and time.monotonic() - sent > 2:
                    sent = time.monotonic()
                    await broadcast()
                continue
            await eng.tick(present())
            state = snapshot()
            recorder.write(state)
            if not turbo or time.monotonic() - sent > 0.2:
                sent = time.monotonic()
                await broadcast(state)
        except Exception:   # one bad tick must not end a long run
            logging.exception("tick failed")
            await asyncio.sleep(0.5)
        await asyncio.sleep(0 if turbo else max(0.0, cfg["clock"]["tick_seconds"] * cfg["pace"] - (time.monotonic() - started)))


async def sky():
    """§6.6: once an hour the engine (never a pet) asks one fixed host what the weather is at the configured place.
    Only when `weather.real` is on. Any failure leaves the house's own weather alone."""
    import urllib.request
    from . import director
    while cfg["weather"]["real"] and not PAUSED:
        try:
            raw = await asyncio.to_thread(lambda: urllib.request.urlopen(cfg["weather"]["real_url"].format(**cfg["weather"]), timeout=20).read())
            d = json.loads(raw)
            director.real_weather(eng.house, director.real_kind(d["current"]))
            if d.get("hourly", {}).get("weather_code", [])[2:]:   # SPEC-v3.5.1 §2: the sky two real hours on (the house's tomorrow, on the live clock), for the lit sign
                eng.house["real_forecast"] = {"day": eng.house["clock"]["day"] + 1, "kind": director.real_kind({"weather_code": d["hourly"]["weather_code"][2], "temperature_2m": d["hourly"]["temperature_2m"][2]})}
        except Exception as e:
            logging.warning("real weather not available: %r", e)
        await asyncio.sleep(3600)


async def wireless():
    """SPEC-v3.5.1 §5: while their radio is on, the engine (never a pet) asks the station what song is on, at most once
    a minute. Any failure leaves the last song (or none: it plays all the same)."""
    while True:
        if radio.is_on(eng.house) and not PAUSED:
            try:
                eng.radio_song = await asyncio.to_thread(radio.now_playing, cfg, DATA / "radio", radio.station(eng.house, cfg))
            except Exception as e:
                logging.warning("radio not refreshed: %r", e)
        else:
            eng.radio_song = None
        await asyncio.sleep(cfg["radio"]["fetch_seconds"] if radio.is_on(eng.house) else 5)


def S_ON():
    """[spotlight] on: switched off, the page is sent no spotlights (no banner, no "new" badge)."""
    return bool(cfg.get("spotlight", {}).get("on"))


STALE_SECONDS = 180   # REVIEW-code.md (18 October 2026): a clock that has not moved this long is stuck
UNSAVED_SECONDS = 600   # REVIEW-v4.0.4 A1 (19 October 2026): ... and a house that has not been saved this long
WATCH_SECONDS = 15


def watchdog():
    """If the house's tick has not moved for STALE_SECONDS, or no save has gone down for UNSAVED_SECONDS, while it
    should be running, the process ends, so launchd starts the server again (the house is saved every few ticks; a
    thought in flight does not survive a restart anyway). Not for a house that is paused, has no one left in it, or
    waits for a thought in turbo time. (19 October 2026, REVIEW-v4.0.4 A1: a plain thread, so a loop stuck in a step
    that never yields is seen too; it only reads.)"""
    last, since, running = eng.house["tick"], time.monotonic(), time.time()
    while True:
        time.sleep(WATCH_SECONDS)
        lineage = eng.house["lineage"]
        waiting = PAUSED or not lineage or lineage["ended"] is not None or ((cfg["clock"]["turbo"] or skipping()) and eng.busy())
        if waiting:
            running = time.time()
        if eng.house["tick"] != last or waiting:
            last, since = eng.house["tick"], time.monotonic()
        elif time.monotonic() - since > STALE_SECONDS:
            stop("the clock has not moved from tick %d for %d s" % (last, STALE_SECONDS))
        if time.time() - max(eng.saved_at[0], running) > UNSAVED_SECONDS:
            stop("the house has not been saved since tick %d, %d s ago" % (eng.saved_at[1], time.time() - eng.saved_at[0]))


def stop(why):
    logging.critical("%s: ending the server so it is started again", why)
    logging.shutdown()
    os._exit(1)


@asynccontextmanager
async def lifespan(app):
    task, window, air = asyncio.create_task(loop()), asyncio.create_task(sky()), asyncio.create_task(wireless())
    threading.Thread(target=watchdog, name="watchdog", daemon=True).start()
    yield
    task.cancel()
    window.cancel()
    air.cancel()
    eng.close()
    recorder.close()


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws(sock: WebSocket):
    if sock.headers.get("origin") not in cfg["server"]["origins"]:
        await sock.accept()   # (SPEC-v4.0.5 §7.5: accepted to be closed, so the page reads 1008 and can say why; refused, it reads 1006)
        await sock.close(code=1008)
        return
    await sock.accept()
    begin()   # (a new house begins when the first visitor comes: SPEC-v4.0.5 §9.3)
    clients[sock] = {"seen": 0, "room": None, "have": {}}
    try:
        state = snapshot()   # (the first message is always whole: the page keeps nothing yet)
        await sock.send_json(dict(state, hashes=sections(state), hello={
            "bits": cfg["house"]["bits"], "properties": {m: v["says"] for m, v in cfg["materials"].items() if isinstance(v, dict) and "says" in v},
            "rooms": {t: {"name": r["name"], "feel": r["feel"]} for t, r in cfg["house"]["rooms"].items()}}))
        while True:
            msg = await sock.receive_json()
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "presence":
                clients[sock].update(seen=time.time() if msg.get("active") is True else 0, room=msg.get("room"))
            elif msg.get("type") == "have":   # SPEC-v4.0.5 §7.2: the sections the page keeps, by hash
                hashes = msg.get("hashes")
                clients[sock]["have"] = {k: v for k, v in hashes.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(hashes, dict) else {}
            elif msg.get("type") == "new_lineage":
                if eng.house["lineage"] and eng.house["lineage"]["ended"] is not None:   # only once the house is empty; the old family's things stay (§4.2)
                    eng.new_lineage()
            elif PAUSED:
                await sock.send_json({"error": "this is a finished run, opened to look at: nothing in it can be changed"})
            else:
                error = actions.visit(eng.house, cfg, msg)
                if error:
                    await sock.send_json({"error": error})
                else:
                    eng.save()
                    await broadcast()
    except (WebSocketDisconnect, ValueError):
        pass
    finally:
        clients.pop(sock, None)


def beliefs_of(p):
    if p["id"] in eng.minds:
        return eng.minds[p["id"]].mem.beliefs
    path = eng.lineage_dir(p["lineage"]) / p["id"] / "beliefs.json"
    return json.loads(path.read_text()) if path.exists() else []


@app.get("/api/pet/{pid}")
async def api_pet(pid: str):
    """Everything about one pet for the Mind tab: what it believes, what it was told, what it has just done."""
    h, p = eng.house, eng.house["pets"].get(pid)
    if not p:
        raise HTTPException(404)
    m = eng.minds.get(pid)
    out = {"pet": pet_view(p), "beliefs": beliefs_of(p), "told": p.get("told", []), "message": p.get("message", []), "life": p.get("life")}
    if m:
        kin = lambda q: {"id": q["id"], "name": label(q), "relation": relation(h, p, q)}
        out.update(
            journal=list(m.journal), diary=p["diary"], projects=p["projects"], accuracy=m.accuracy(), series=m.series[-200:],
            senses=physics.senses(h, cfg, p), packet=getattr(m, "last_packet", None), exploits=p["exploits"], met=p["met"], trust=p["trust"],
            rooms=[h["rooms"][r]["name"] for r in p["rooms"]], known=[dict(kin(h["pets"][k]), line=v) for k, v in p["known"].items() if k in h["pets"]],
            kin=[kin(q) for q in h["pets"].values() if q["id"] != pid and relation(h, p, q)], portraits=p["portraits"][-6:],
            bodies=p["bodies"], meter=p["meter"], wellbeing=round(life.wellbeing(p)), cuts=p.get("cuts", 0),
            things=story.made_by(h, p)[:30])
    if K.on(cfg):   # SPEC-v4.2 E: each belief's hook in words, on the Mind page (§5.1); a copy, the mind's own list untouched
        out["beliefs"] = [dict(b, hook_words=pages.hook_words(b["hook"])) if isinstance(b, dict) and b.get("hook") else b for b in out["beliefs"]]
    return out


@app.get("/api/family")
async def api_family():
    h = eng.house
    heir = [{"name": n, "room": r["name"], "recipe": o["made"]["recipe"], "line": [label(h["pets"][x]) if x in h["pets"] else x for x in o["made"]["heirloom"]["line"]],
             "to": [label(h["pets"][x]) for x in o["made"]["heirloom"]["to"] if x in h["pets"]]}
            for r in h["rooms"].values() if r["type"] for n, o in things.made(r).items() if o["made"].get("heirloom")]
    says = [{"text": c["text"], "gens": c["gens"], "truth": c["truth"], "first": c["first"], "forms": c["forms"],
             "pets": [{"id": x, "name": label(h["pets"][x]) if x in h["pets"] else "the one before" if x == "before" else "someone gone"} for x in c["pets"]]} for c in story.sayings(h, 8)]
    recipes = sorted(({"words": craft.words(cfg, k), "by": label(h["pets"][r["by"]]) if r.get("by") in h["pets"] else None, "dish": k.startswith("dish:"), "lost": "lost" in r}
                      for k, r in h.get("recipes", {}).items() if "|" in k or k.startswith("dish:")), key=lambda x: (not x["dish"], x["words"]))   # SPEC-v3.6b §4: the family's recipes, dishes first
    out = {"pets": [pet_view(p) for p in h["pets"].values()], "sayings": says, "heirlooms": heir, "lineage": h["lineage"], "recipes": recipes,
           "records": {p["id"]: p["life"] for p in h["pets"].values() if p.get("life")}}
    if K.on(cfg):   # SPEC-v4.2 E: the family's tales (§10.3, §11.4), newest first
        out["tales"] = [K.tale(t) for t in reversed(h.get("tales") or [])]
    return out


@app.get("/api/story")
async def api_story():
    h = eng.house
    rows = eng.db.execute("SELECT n, tick, day, hour, kind, text, pet, room FROM moments ORDER BY n DESC LIMIT 600").fetchall()
    keys = ("n", "tick", "day", "hour", "kind", "text", "pet", "room")
    dead = sorted((p for p in h["pets"].values() if p.get("life")), key=lambda p: -p["died"])
    return {"chronicle": h["chronicle"][::-1], "moments": talk.attach(h, [dict(zip(keys, r)) for r in rows]), "day": h["clock"]["day"],   # (SPEC-v4.0: a talk's lines)
            "records": [p["life"] for p in dead][:20], "lineage": h["lineage"], "nobody": not alive(h)}


@app.get("/api/v31")
async def api_v31():
    """SPEC-v3.1: the Walls (every inscription ever written), the Songbook (every version of every song and what it came
    from), the Library (every question put to the book), and what the box has said, from the lineage's log."""
    h, db = eng.house, eng.db
    if not db:
        return {"walls": [], "songs": [], "library": [], "radio": [], "arrivals": {}}

    def rows(sql, keys):
        try:
            return [dict(zip(keys, r)) for r in db.execute(sql).fetchall()]
        except Exception as e:   # a run from before v3.1, opened to look at: its log has no such table, and is not given one
            logging.warning("the Walls and Songbook could not read the log (%r): %s", e, sql[:60])
            return []
    name = lambda pid: (label(h["pets"][pid]) if pid in h["pets"] else {"visitor": "the visitor", "music box": "the music box", "bird": "a bird"}.get(pid, pid))
    walls_ = {}
    for r in rows("SELECT id, tick, room, place, text, by, medium, what, actor FROM inscriptions ORDER BY tick", ("id", "tick", "room", "place", "text", "by", "medium", "what", "actor")):
        w = walls_.setdefault(r["id"], dict(r, by_name=name(r["by"]), room_name=h["rooms"][r["room"]].get("name", r["room"]), fate="there"))
        if r["what"] in ("scrubbed", "worn away", "faded away"):
            w.update(fate=r["what"], gone=r["tick"], gone_by=name(r["actor"]) if r["actor"] else None)
    knows = {}
    for p in h["pets"].values():
        for e in p.get("songs", []):
            knows.setdefault(e["id"], []).append(label(p))
    songs_ = [dict(s, notes=json.loads(s["notes"]), by_name=name(s["by"]), known_by=knows.get(s["id"], []), sounds=songs.sound(json.loads(s["notes"])))
              for s in rows("SELECT id, tick, name, notes, by, parent, how, family FROM songs ORDER BY tick", ("id", "tick", "name", "notes", "by", "parent", "how", "family"))]
    lib = [dict(r, name=name(r["pet"])) for r in rows("SELECT pet, tick, question, title, text FROM library ORDER BY tick DESC LIMIT 300", ("pet", "tick", "question", "title", "text"))]
    said = rows("SELECT tick, room, source, text FROM radio ORDER BY tick DESC LIMIT 300", ("tick", "room", "source", "text"))
    crossed = [{"text": c["text"], "families": [c.get("family", 1)] + c["crossed"]} for c in h["claims"] if c.get("crossed")]
    tpd = cfg["ticks_per_day"]
    v, A = h.get("v31", {"at": 0, "arrived": {}}), cfg["arrivals"]
    return {"walls": list(walls_.values()), "songs": songs_, "library": lib, "radio": said, "crossed": crossed, "ticks_per_day": tpd,
            "arrivals": {n: {"arrived": v["arrived"].get(n), "due": v["at"] + round((0.05 * i if A["force"] else A[n]) * tpd)} for i, n in enumerate(director.ORDER)}}


@app.get("/api/lab")
async def api_lab():
    return dict(metrics.lab(eng.db, eng.house, cfg, beliefs_of), today=lab4.today(eng, cfg, len(clients), sent["bytes"]),   # SPEC-v4.0.5 §8
                **({"spirit": lab4.spirit(eng)} if K.on(cfg) else {}),   # SPEC-v4.2 E: §11.5
                **({"jobs": lab4.jobs(eng)} if K.on5(cfg) else {}),   # SPEC-v5.0 §5 (helper C): the Lab's Jobs
                **({"grammar": lab4.grammar(eng)} if K.on51(cfg) else {}),   # SPEC-v5.1 §8 (helper C): the Lab's Grammar
                **({"life": lab4.life(eng)} if any(K.on53(cfg, x) for x in K.PARTS53) else {}))   # SPEC-v5.3 §8 (helper C): the Lab's Life


@app.get("/api/things")
async def api_things():
    h = eng.house
    return {"gone": h["gone_things"][-60:][::-1]}


@app.get("/api/replay")
async def api_replay():
    """Which days of which lineages can be played back."""
    root = DATA / "replay"
    return {d.name: sorted(int(f.name[4:8]) for f in d.glob("day-*.jsonl.gz")) for d in sorted(root.glob("lineage-*"))} if root.exists() else {}


@app.get("/api/replay/{lineage}/{day}")
async def api_replay_day(lineage: int, day: int):
    path = DATA / "replay" / ("lineage-%d" % lineage) / ("day-%04d.jsonl.gz" % day)
    if not path.exists():
        raise HTTPException(404)
    return Response(gzip.compress(replay_lines(path.read_bytes()), 1), media_type="application/x-ndjson", headers={"Content-Encoding": "gzip"})


def replay_lines(raw):
    """A day's snapshots out of its file, whatever state the file is in: still being written (no end marker yet),
    or cut short when the engine was stopped and carried on as a second gzip stream after the restart. A browser
    refuses the first and drops the rest of the second, so the file is read here and sent as one clean stream.
    Whole lines only."""
    import zlib
    out, at = [], 0
    while 0 <= at < len(raw):
        d, got, i, broken = zlib.decompressobj(31), b"", at, False
        for i in range(at, len(raw), 1024):   # in small pieces, so a broken join costs a frame or two, not the stream
            try:
                got += d.decompress(raw[i:i + 1024])
            except zlib.error:
                broken = True
                break
            if d.eof:
                break
        out += got.split(b"\n")[:-1]          # what follows the last newline is a line cut short, or nothing
        at = min(len(raw), i + 1024) - len(d.unused_data) if d.eof else raw.find(b"\x1f\x8b\x08", max(at + 1, i)) if broken else -1
    return b"\n".join(out) + b"\n" if out else b""


# ---- SPEC-v3.5.3: the page's tabs, read only ----

@app.get("/api/pets")
async def api_pets():
    out = pages.all_pets(eng)
    if K.on(cfg):   # SPEC-v4.2 E: the cause on every stone, in words, and whether it was age (§2.7, §11.4: the tree marks the rest)
        for c in out["pets"]:
            p = eng.house["pets"][c["id"]]
            if p["stage"] == "dead":
                c["cause_words"] = p.get("cause_words") or (p.get("life") or {}).get("cause_words") or K.DEATHS.get(K.OLD_CAUSE.get(p.get("cause"), p.get("cause")), "")
                c["of_age"] = K.OLD_CAUSE.get(p.get("cause"), p.get("cause")) in ("old age", None)
    return out


@app.get("/api/petpage/{pid}")
async def api_petpage(pid: str):
    out = pages.pet_page(eng, pid, beliefs_of)
    if out is None:
        raise HTTPException(404)
    if pid in eng.minds:   # the living: how it is just now, as its card has it
        out["now"] = pet_view(eng.house["pets"][pid])
    from . import visitor
    if visitor.on(cfg):   # SPEC-v4.0 §10: the "the visitor" section of its page
        out["visitor"] = visitor.section(eng, pid)
    if "spirit" in out["pet"]:   # SPEC-v4.2 E: the card's drive, flaw, voice and secret (§11.2), beside B's self-page
        out["pet"]["spirit"].update(lab4.card(eng.house, eng.house["pets"][pid]))
    return out


@app.get("/api/days")
async def api_days(before: int | None = None):
    return pages.story_days(eng, before)


@app.get("/api/allthings")
async def api_allthings():
    return pages.all_things(eng)


@app.get("/api/thing/{key}")
async def api_thing(key: str):
    out = pages.thing_page(eng, key)
    if out is None:
        raise HTTPException(404)
    return out


@app.post("/api/star/{key}")
async def api_star(key: str, request: Request):
    """SPEC-v3.5.4 §10: the visitor gives a thing a star (one to a thing). From the house's own pages only."""
    from . import board
    if request.headers.get("origin") not in cfg["server"]["origins"]:
        raise HTTPException(403)
    error = "this is a finished run, opened to look at: nothing in it can be changed" if PAUSED else board.star(eng.house, cfg, key)
    if error:
        return Response(json.dumps({"error": error}), status_code=409, media_type="application/json")
    eng.save()
    await broadcast()
    return {"ok": True}


@app.get("/api/away")
async def api_away(since: int = 0):
    """SPEC-v4.0 §11 "while you were away": every moment since that tick that the house still holds (its last 400),
    the newest 300, in the snapshot's shape."""
    return {"tick": eng.house["tick"], "moments": [m for m in eng.house["moments"] if m["tick"] > since][-300:]}


@app.get("/api/visitor/kinds")
async def api_visitor_kinds():
    """SPEC-v5.3.2 §1: what the visitor's "place" tool offers - every kind in kinds.toml, with its words, its verbs and
    whether it hangs. Empty while [visitor4] is off, like the tools themselves."""
    from . import visitor
    return {"kinds": visitor.palette(eng.house, cfg) if visitor.on(cfg) else []}


@app.post("/api/visitor/{tool}")
async def api_visitor(tool: str, request: Request):
    """SPEC-v4.0 §10: the visitor's tools (talk, answer, teach, praise, scold, give, suggest, step in; SPEC-v4.2 §9.4: tend,
    remedy, with [visitor5]). From the house's own pages only."""
    from . import visitor
    if request.headers.get("origin") not in cfg["server"]["origins"]:
        raise HTTPException(403)
    if PAUSED or tool not in visitor.TOOLS:
        raise HTTPException(404)
    ok, said = visitor.use(eng, tool, await request.json())
    if not ok:
        return Response(json.dumps({"error": said}), status_code=409, media_type="application/json")
    eng.save()
    await broadcast()
    return {"ok": True, "said": said}


@app.post("/api/buyback/{made_id}")
async def api_buyback(made_id: int, request: Request):
    """SPEC-v3.6d §7: the visitor buys a thing that matters back from the catalog, for the machine's materials. From the house's own pages only."""
    from . import design
    if request.headers.get("origin") not in cfg["server"]["origins"]:
        raise HTTPException(403)
    error = "this is a finished run, opened to look at: nothing in it can be changed" if PAUSED else design.buy_back(eng.house, cfg, {"id": made_id})
    if error:
        return Response(json.dumps({"error": error}), status_code=409, media_type="application/json")
    eng.save()
    await broadcast()
    return {"ok": True}


# SPEC-v3.5.3 §8: each pet's portrait as a PNG. The page draws pets (view/src/petsprite.ts, from the genome); the first
# page to draw one sends it here, and it is kept and served from then on. One file per pet per stage it is drawn at:
# the living change as they grow; the dead are drawn as they were in life, and never again.
PORTRAITS = DATA / "portraits"


def portrait_file(pid, big):
    p = eng.house["pets"].get(pid)
    if not p:
        raise HTTPException(404)
    return PORTRAITS / ("%s-%s%s.png" % (pid, pages.life_stage(p), "@4x" if big else ""))


@app.get("/portrait/{name}")
async def portrait(name: str):
    pid, big = name.removesuffix(".png").removesuffix("@4x"), name.endswith("@4x.png")
    f = portrait_file(pid, big)
    if not f.exists():
        raise HTTPException(404)
    return Response(f.read_bytes(), media_type="image/png", headers={"Cache-Control": "no-cache"})


@app.post("/portrait/{name}")
async def portrait_put(name: str, request: Request):
    """Kept once: a PNG of at most 64 KB, for a pet that exists, at the stage it is drawn at, if there is none yet.
    From the house's own pages only, and its size is known before it is read (19 October 2026, REVIEW-v4.0.4 A10)."""
    if request.headers.get("origin") not in cfg["server"]["origins"]:
        raise HTTPException(403)
    size = request.headers.get("content-length") or ""
    if not size.isdigit() or int(size) > 65536:
        raise HTTPException(413)
    pid, big = name.removesuffix(".png").removesuffix("@4x"), name.endswith("@4x.png")
    f, body_ = portrait_file(pid, big), await request.body()
    if len(body_) > 65536 or not body_.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(400)
    if not f.exists():
        PORTRAITS.mkdir(parents=True, exist_ok=True)
        f.write_bytes(body_)
    return Response(status_code=204)


# SPEC-v3.2: the art is data (view/assets/README.md): packs, sprite mappings, the kind catalog, room layouts, sounds
if (ROOT / "view" / "assets").exists():
    app.mount("/art", StaticFiles(directory=ROOT / "view" / "assets"))
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True))


def main():
    """Serve the house. (SPEC-v4.0.5 §9.3: a clone with no built view is told how to build it. REVIEW-v4.0.4 §10:
    no access log, it was four lines in five of the log; uvicorn's own lines go through the format above.)"""
    if not (DIST / "index.html").exists():
        raise SystemExit("build the view first: cd view && npm install && npm run build")
    uvicorn.run(app, host=cfg["server"]["host"], port=int(os.environ.get("PET_PORT", cfg["server"]["port"])), access_log=False, log_config=None)


if __name__ == "__main__":
    main()
