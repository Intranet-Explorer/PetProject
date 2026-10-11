"""The engine's front door (SPEC §3, §16): the tick loop, a websocket for the view, and a few read-only pages
of JSON for the drawer. Binds to localhost and checks Origin on every websocket.

    uv run python -m engine.server                    # the real clock
    PET_PROFILE=showcase uv run python -m engine.server   # the short-life profile, in turbo time
    PET_DATA=data.showcase PET_PAUSED=1 PET_PORT=8001 uv run python -m engine.server   # look at an archived run; nothing moves
"""
import asyncio
import gzip
import json
import logging
import os
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import actions, body, director, feel, order, life, metrics, mind, physics, radio, songs, story, things, walls
from .tick import Engine, model_brains, stub_brains
from . import world
from .world import ROOT, STAGE_WORD, alive, label, load_config, power_on, relation

cfg = load_config(profile=os.environ.get("PET_PROFILE") or None)
DATA = ROOT / os.environ.get("PET_DATA", "data")
PAUSED = bool(os.environ.get("PET_PAUSED"))   # open a finished run to look at and replay, without living it any further
eng = Engine(cfg, DATA, stub_brains if cfg["stub"]["enabled"] else model_brains, readonly=PAUSED)   # ... and without writing a byte of it
clients = {}   # websocket -> {"seen": when it last reported an attentive visitor, "room": the room it is showing}


def first_egg():
    """What the first egg of a new house is given (§13 part 0): the last v2 pet's words and body."""
    path = ROOT / "first-egg.json"
    if not path.exists():
        return None, None
    d = json.loads(path.read_text())
    return [{"by": None, "who": d["who"], "kind": "message", "text": d["message"], "tick": 0}], d["genome"]


if not eng.house["lineage"]:
    eng.new_lineage(*first_egg())


def present():
    """The room a visitor is attending to: a view tab is focused and has had input lately (SPEC §4)."""
    live = [c for c in clients.values() if time.time() - c["seen"] < 45]
    return live[0]["room"] if live else None


def pet_view(p):
    """One pet as the view needs it. Numbers are for the view and the Lab; no pet ever sees them."""
    h = eng.house
    out = {k: p.get(k) for k in ("id", "name", "stage", "room", "pos", "gen", "parent", "children", "word", "genome", "temper", "eggs",
                                 "laid", "born", "died", "cause", "lineage", "stage_before")}
    # the visitor's naming, for the pet's card: the name offered, and whether the pet has taken it
    out["naming"] = {"offered": p["called"], "took": (p.get("name") or "").lower() == p["called"].strip().lower(),
                     "at": (p.get("named") or {}).get("tick")} if p.get("called") else None
    out.update(label=label(p), buried=bool(p.get("buried")), made=p.get("made", 0), useful=len(p.get("useful", [])), family=p.get("family", 1))
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
        feelings=feel.feelings(p), felt={n: feel.WORDS[n][feel.level(p, n)] for n in p["needs"]}, seems=feel.seems(p), doing=mind.doing(h, p), asleep=bool(p["sleep"]), thinking=p["thinking"],
        carrying=p["carrying"], following=p["following"], weak=p["weak"], said=said, days=round(life.days(h, cfg, p), 1),
        project=p["project"], offers=[{"from": o["from"], "kind": o["kind"]} for o in p["offers"]],
        plan={"intention": plan["intention"], "thought": plan["thought"], "expect": plan["expect"], "i": plan["i"], "why": plan["why"],
              "steps": [actions.words(s) for s in plan["steps"]], "acting": plan["left"] is not None and not plan.get("idle"),
              "idle": bool(plan.get("idle"))} if plan else None,
        body=body.doing(cfg, h, p) if cfg["body"]["on"] and not p["sleep"] and not world.busy(p) else None,   # SPEC-v3.3 §1, §5.4
        focus=p.get("focus"), habits=body.habits(h, cfg, p), react=body.state(p).get("react"), orderly=p["temper"].get("orderly"),
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
    return out


EMOTE = {"energy": "tired", "comfort": "uneasy", "curiosity": "bored", "company": "lonely"}


def mood(p):
    worst = sorted(p["needs"], key=lambda n: -feel.level(p, n))
    out = [feel.WORDS[n][feel.level(p, n)] for n in worst if feel.level(p, n) >= 2][:2]
    return out or [feel.WORDS[worst[-1]][feel.level(p, worst[-1])]]


def emote(p):
    worst = max(p["needs"], key=lambda n: feel.level(p, n))
    return EMOTE[worst] if feel.level(p, worst) >= 3 else "content" if all(feel.level(p, n) <= 1 for n in p["needs"]) else None


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
                         "ups": m["ups"], "useful": things.useful(m, cfg), "called": m.get("called"), "tick": m["tick"],
                         "worn": [k for k in ("damp", "dusty", "eaten") if m.get(k)],
                         "loud": bool(things.prop(cfg, o).get("loud")),                           # it sounds when used (SPEC-v3.3 §4)
                         "hums": bool(o.get("active") and things.doing(cfg, o).get("loud"))}     # it is making a noise by itself now
            if o.get("home"):
                v["home"] = o["home"]   # SPEC-v3.3 §2.3: where it belongs: {room, on} or {room, pos}
        elif "memorial" in o:
            v["memorial"] = o["memorial"]
        else:
            v["fix"] = {k: (True if k == "water" else x) for k, x in o["fix"].items() if k != "states"}
            v["says"] = actions.fixture_says(o["fix"])   # what it is, for the visitor's hover card
            if "water" in o["fix"]:
                v["water"] = o["fix"]["water"]
            if o["fix"].get("plant"):
                v["grow"] = o["grow"]
            if "meal" in o["fix"]:
                v["servings"] = o["servings"]
        if o.get("wall"):
            v["wall"] = True
        if o.get("on"):
            v["on"] = o["on"]   # SPEC-v3.3 §2.2: put away on (or in) this; it stands on that thing's tile
        if order.cap(cfg, o):
            v["store"] = {"cap": order.cap(cfg, o), "holds": order.held(r, n),
                          "inside": bool(o.get("fix", {}).get("inside") or cfg["kinds"].get(o.get("made", {}).get("recipe", {}).get("kind"), {}).get("inside"))}
        objs[n] = v
    return {"id": r["id"], "cell": r["cell"], "type": r["type"], "name": r["name"], "doors": r["doors"], "paint": r["paint"],
            "shut": [k.split("|")[1] for k, t in h["shut"].items() if k.startswith(r["id"] + "|") and t > h["tick"]],
            "wet": r["wet_until"] > h["tick"], "cold": r["cold_until"] > h["tick"], "lit": things.light_on(h, cfg, r),
            "marks": [dict(m, clarity=round(walls.clarity(cfg, r, m, h["tick"]), 2), by_name=mark_by(m)) for m in r.get("marks", [])],
            "mess": order.clutter(h, cfg, r), "mess_says": order.MESS[order.clutter(h, cfg, r)], "areas": r.get("areas", []),   # SPEC-v3.3 §2
            "sounding": r.get("sounding_until", 0) > h["tick"], "objects": objs, "found": r["found"], "by": r["by"],
            "spots": [{"bit": s["bit"], "pos": s["pos"]} for s in r["spots"] if s["ready"]]}


def mark_by(m):
    p = eng.house["pets"].get(m["by"])
    return "the visitor" if m["by"] == "visitor" else label(p) if p else "someone long gone"


def snapshot():
    h = eng.house
    recent = lambda rows, secs: [x for x in rows if (h["tick"] - x["tick"]) * cfg["clock"]["tick_seconds"] <= secs]
    return {
        # SPEC-v3.1: songs lately sung (the view plays them), every version the living know, what the box just said, and
        # which discoveries have come
        "sung": recent(h.get("sung", []), 30), "songs": {e: h["songs"][e] for p in h["pets"].values() for e in [x["id"] for x in p.get("songs", [])] if e in h.get("songs", {})}
        | {s["song"]: h["songs"][s["song"]] for s in recent(h.get("sung", []), 30)},
        "radio": {"on": radio.is_on(h), "here": bool(radio.boxes(h)), "said": recent(h.get("radio", {}).get("said", []), 45)},
        "arrived": h.get("v31", {}).get("arrived", {}), "read_glow": (h["tick"] - h.get("read_glow", -10**9)) * cfg["clock"]["tick_seconds"] <= 20,
        "pace": cfg["pace"],
        # SPEC-v3.3: the visitor's music and radio (§3), the small sounds pets make by themselves (§4: each numbered, to
        # be played once), and the body's activities with their icons (§1.1, §5.4)
        "dj": {"music": (h.get("dj") or {}).get("music"), "moods": list(cfg["music"]["tunes"]),
               "radio": {"on": radio.is_on(h), "plays": h.get("radio", {}).get("plays") or "mix", "theirs": any(n != "little radio" for _, n, _ in radio.boxes(h)),
                         "rooms": [r["id"] for r, _, _ in radio.boxes(h)]}},
        "vox": recent(h.get("vox", []), 20),
        "activities": {n: {"icon": a.get("icon"), "passive": bool(a.get("passive")), "rest": bool(a.get("rest"))} for n, a in cfg["activities"].items()},
        # SPEC-v3.2: the one plain sentence about the house now, and the steps finished in the last world minute or so
        "now": story.now(h, cfg), "acts": recent(h.get("acts", []), 40),
        "tick": h["tick"], "clock": h["clock"], "weather": h["weather"], "power": power_on(h), "size": [cfg["W"], cfg["H"]],
        "tick_seconds": cfg["clock"]["tick_seconds"], "day_seconds": cfg["clock"]["day_seconds"], "turbo": cfg["clock"]["turbo"],
        "profile": cfg["profile"], "start": h["start"], "door_tiles": h["door_tiles"], "lineage": h["lineage"],
        "rooms": [room_view(r) for r in h["rooms"].values()], "pets": [pet_view(p) for p in h["pets"].values()],
        "creatures": h["creatures"], "moments": h["moments"][-60:], "events": h["events"][-8:],
        "chronicle": h["chronicle"][-1:], "visitor": present(), "population": cfg["life"]["population"],
        "sayings": [{"text": c["text"], "gens": len(c["gens"]), "truth": c["truth"]} for c in story.sayings(h, 3)],
    }


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
    for sock in list(clients):
        try:
            await sock.send_json(state)
        except Exception:
            clients.pop(sock, None)


async def loop():
    turbo, sent = cfg["clock"]["turbo"], 0.0
    while True:
        started = time.monotonic()
        try:
            ended = eng.house["lineage"]["ended"] is not None or PAUSED
            if ended and cfg["life"]["auto_lineage"] and not PAUSED:
                eng.new_lineage()
            elif ended or (turbo and eng.busy()):   # an empty house waits to be started again; in turbo the world waits for a thought
                await asyncio.sleep(1.0 if ended else 0.02)
                if ended and time.monotonic() - sent > 2:
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
    """§6.6: once an hour the engine (never a pet) asks one fixed host what the weather is over the Twin Cities.
    Only when `weather.real` is on. Any failure leaves the house's own weather alone."""
    import urllib.request
    from . import director
    while cfg["weather"]["real"] and not PAUSED:
        try:
            raw = await asyncio.to_thread(lambda: urllib.request.urlopen(cfg["weather"]["real_url"], timeout=20).read())
            director.real_weather(eng.house, director.real_kind(json.loads(raw)["current"]))
        except Exception as e:
            logging.warning("real weather not available: %r", e)
        await asyncio.sleep(3600)


async def wireless():
    """SPEC-v3.1 §5.2: the engine (never a pet) asks the radio's few fixed sources what is new, each at most once an hour,
    and only once there is a box in the house. Any failure leaves the box with what it had; with nothing, it plays static."""
    while True:
        if radio.boxes(eng.house) and not PAUSED:
            try:
                eng.radio_items = await asyncio.to_thread(radio.refresh, cfg, DATA / "radio")
            except Exception as e:
                logging.warning("radio not refreshed: %r", e)
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app):
    task, window, air = asyncio.create_task(loop()), asyncio.create_task(sky()), asyncio.create_task(wireless())
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
        await sock.close(code=1008)
        return
    await sock.accept()
    clients[sock] = {"seen": 0, "room": None}
    try:
        await sock.send_json(dict(snapshot(), hello={
            "bits": cfg["house"]["bits"], "properties": {m: v["says"] for m, v in cfg["materials"].items() if isinstance(v, dict) and "says" in v},
            "rooms": {t: {"name": r["name"], "feel": r["feel"]} for t, r in cfg["house"]["rooms"].items()}}))
        while True:
            msg = await sock.receive_json()
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "presence":
                clients[sock] = {"seen": time.time() if msg.get("active") is True else 0, "room": msg.get("room")}
            elif msg.get("type") == "new_lineage":
                if eng.house["lineage"]["ended"] is not None:   # only once the house is empty; the old family's things stay (§4.2)
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
    return out


@app.get("/api/family")
async def api_family():
    h = eng.house
    heir = [{"name": n, "room": r["name"], "recipe": o["made"]["recipe"], "line": [label(h["pets"][x]) if x in h["pets"] else x for x in o["made"]["heirloom"]["line"]],
             "to": [label(h["pets"][x]) for x in o["made"]["heirloom"]["to"] if x in h["pets"]]}
            for r in h["rooms"].values() if r["type"] for n, o in things.made(r).items() if o["made"].get("heirloom")]
    says = [{"text": c["text"], "gens": c["gens"], "truth": c["truth"], "first": c["first"], "forms": c["forms"],
             "pets": [{"id": x, "name": label(h["pets"][x]) if x in h["pets"] else "the one before" if x == "before" else "someone gone"} for x in c["pets"]]} for c in story.sayings(h, 8)]
    return {"pets": [pet_view(p) for p in h["pets"].values()], "sayings": says, "heirlooms": heir, "lineage": h["lineage"],
            "records": {p["id"]: p["life"] for p in h["pets"].values() if p.get("life")}}


@app.get("/api/story")
async def api_story():
    h = eng.house
    rows = eng.db.execute("SELECT n, tick, day, hour, kind, text, pet, room FROM moments ORDER BY n DESC LIMIT 600").fetchall()
    keys = ("n", "tick", "day", "hour", "kind", "text", "pet", "room")
    dead = sorted((p for p in h["pets"].values() if p.get("life")), key=lambda p: -p["died"])
    return {"chronicle": h["chronicle"][::-1], "moments": [dict(zip(keys, r)) for r in rows], "day": h["clock"]["day"],
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
        except Exception:   # a run from before v3.1, opened to look at: its log has no such table, and is not given one
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
    return metrics.lab(eng.db, eng.house, cfg, beliefs_of)


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


# SPEC-v3.2: the art is data (view/assets/README.md): packs, sprite mappings, the kind catalog, room layouts, sounds
if (ROOT / "view" / "assets").exists():
    app.mount("/art", StaticFiles(directory=ROOT / "view" / "assets"))
if (ROOT / "view" / "dist").exists():
    app.mount("/", StaticFiles(directory=ROOT / "view" / "dist", html=True))

if __name__ == "__main__":
    uvicorn.run(app, host=cfg["server"]["host"], port=int(os.environ.get("PET_PORT", cfg["server"]["port"])))
