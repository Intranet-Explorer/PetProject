"""Self-check for v4.0.6 (SPEC-v4.0.5 §1, §2, §8's queue wait, §9.3's code; helper A): the spine and the model's I/O.
Stub brains and houses in a temporary folder only; the server's parts run in a child process on its own folder (and,
for the log and the portrait, on port 8110), never on the live house, and nothing calls the model.
    uv run python -m engine.check_spine"""
import asyncio
import contextlib
import io
import json
import logging
import math
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

from . import brain4, log, metrics, sleep, tick
from .brains import model
from .check import at
from .check_brain4 import valid
from .tick import Engine, stub_brains
from .world import ROOT, load_config


class Heard(logging.Handler):
    """What the engine said, while a check runs."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []
        logging.getLogger().addHandler(self)
        logging.getLogger().setLevel(logging.INFO)

    def emit(self, record):
        self.records.append(record)

    def said(self, level, text):
        return [r for r in self.records if r.levelno == level and text in r.getMessage()]

    def close(self):
        logging.getLogger().removeHandler(self)
        super().close()


def house(d, cfg=None, hatched=True):
    cfg = cfg or load_config()
    eng = Engine(cfg, d, stub_brains)
    pet = eng.new_lineage()
    if hatched:
        pet["laid"] = -10 ** 6
    return eng, pet


def committed(eng, sql):
    """Read the log from a second connection, as the Lab or sqlite3 would: only what has been committed."""
    other = log.open_db(eng.lineage_dir() / "lineage.db", readonly=True)
    try:
        return other.execute(sql).fetchall()
    finally:
        other.close()


async def save_order(d):
    """§1.1: the log is committed though house.json cannot be written; a mind's failing state leaves the house and the log agreeing."""
    eng, pet = house(d)
    for _ in range(6):
        await eng.tick()
    heard, was = Heard(), list(eng.saved_at)
    try:
        log.put(eng.db, "events", tick=eng.house["tick"], day=1, kind="check", room=None, detail="before the folder shut")
        os.chmod(d, 0o500)
        try:
            eng.save()
        finally:
            os.chmod(d, 0o700)
        assert committed(eng, "SELECT count(*) FROM events WHERE detail='before the folder shut'") == [(1,)], "the log committed though house.json could not be written"
        assert eng.saved_at == was and heard.said(logging.ERROR, "save: house.json"), "the failed save is said, and not counted as a save"
        t = eng.house["tick"]
        for _ in range(6):
            await eng.tick()
        assert eng.house["tick"] == t + 6 and eng.saved_at[1] > was[1], "the engine ticks on and saves again"
        m = eng.minds[pet["id"]]

        def broken():
            raise OSError("no room on the disk")
        m.save = broken
        log.put(eng.db, "events", tick=eng.house["tick"], day=1, kind="check", room=None, detail="before the mind failed")
        eng.save()
        on_disk = json.loads((Path(d) / "house.json").read_text())
        assert on_disk["tick"] == eng.house["tick"] and committed(eng, "SELECT count(*) FROM events WHERE detail='before the mind failed'") == [(1,)], \
            "a mind's state failing leaves house.json and the log agreeing"
        assert eng.saved_at[1] == eng.house["tick"] and heard.said(logging.ERROR, "save: the state of %s" % pet["id"]), "and is said"
        del m.save
        eng.close()
        assert eng.db is None
    finally:
        heard.close()


async def wal(d):
    """§1.2: the log is read from a second connection while the engine writes it."""
    eng, pet = house(d)
    for _ in range(6):
        await eng.tick()
    assert eng.db.execute("PRAGMA journal_mode").fetchone()[0] == "wal" and eng.db.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    log.put(eng.db, "events", tick=eng.house["tick"], day=1, kind="check", room=None, detail="not yet committed")   # (a write in progress)
    reader = sqlite3.connect("file:%s?mode=ro" % (eng.lineage_dir() / "lineage.db"), uri=True)
    for _ in range(20):
        assert reader.execute("SELECT count(*) FROM calls").fetchone()[0] >= 0   # (no "database is locked")
        await eng.tick()
    reader.close()
    eng.save()
    with contextlib.redirect_stdout(io.StringIO()) as out:
        metrics.main(d)   # (the Lab's own script opens it read-only)
    assert "calls in the last hour" in out.getvalue()
    eng.close()


async def flush(d):
    """§1.3: a row that cannot go into the log holds nothing else back, and is gone after two ticks."""
    eng, pet = house(d)
    await eng.tick()
    heard = Heard()
    try:
        h = eng.house
        h["fresh_moments"].append({"n": 10 ** 6, "tick": h["tick"], "day": 1, "hour": 9.0, "kind": "check", "text": object(), "pet": None, "room": None})
        h["fresh_events"].append({"tick": h["tick"], "day": 1, "kind": "check", "room": None, "detail": "beside the bad one"})
        eng.flush()
        assert not h["fresh_moments"] and not h["fresh_events"] and len(eng.retry) == 1, "the lists are emptied; the bad row waits once"
        assert eng.db.execute("SELECT count(*) FROM events WHERE detail='beside the bad one'").fetchone()[0] == 1, "the other rows go in"
        eng.flush()
        assert not eng.retry and len(heard.said(logging.ERROR, "could not go into the log twice")) == 1, "failing twice, it is dropped with one ERROR"
        for _ in range(3):
            await eng.tick()
        assert not eng.retry and len(heard.said(logging.ERROR, "could not go into the log twice")) == 1
    finally:
        heard.close()
    eng.close()


async def hatch(d):
    """§1.4: a mind that cannot be made leaves the egg an egg, said once a world hour; a pet with no mind still dies."""
    eng, egg = house(d, hatched=False)
    egg["laid"] = -10 ** 6
    real, heard = tick.Mind.__init__, Heard()

    def refuse(self, eng_, pet):
        if pet["id"] == egg["id"]:
            raise RuntimeError("no mind for this one")
        real(self, eng_, pet)
    tick.Mind.__init__ = refuse
    try:
        n = round(eng.cfg["ticks_per_hour"] * 2)
        for _ in range(n):
            await eng.tick()
        said = heard.said(logging.ERROR, "house step a mind for %s failed" % egg["id"])
        assert egg["stage"] == "egg" and egg["id"] not in eng.minds, "the egg stays an egg"
        assert len(said) == math.ceil(n / eng.cfg["ticks_per_hour"]), "said once a world hour: %d in %d ticks" % (len(said), n)
    finally:
        tick.Mind.__init__ = real
        heard.close()
    await eng.tick()
    assert egg["stage"] == "hatchling" and egg["id"] in eng.minds, "and hatches once a mind can be made"
    del eng.minds[egg["id"]]
    eng.kill(egg, "old age")
    assert egg["stage"] == "dead" and (eng.lineage_dir() / egg["id"] / "life.json").exists(), "a pet with no mind still dies"
    for _ in range(round(eng.cfg["life"]["fade_minutes"] * 60 / eng.cfg["clock"]["tick_seconds"]) + 2):
        await eng.tick()
    assert egg.get("buried"), "and is buried"
    eng.close()


async def night(d):
    """§1.5: a night's work that raises outside its own try blocks is over all the same, and the hob wakes at dawn;
    one that ends without being done is begun once more, then let go."""
    eng, pet = house(d)
    await eng.tick()
    at(eng, 23)
    real_condense, real_night = sleep.condense, sleep.night
    heard = Heard()
    try:
        sleep.condense = lambda *a, **k: 1 / 0
        for _ in range(20):
            await eng.tick()
        assert pet["sleep"] and pet["sleep"]["done"] and heard.said(logging.ERROR, "the night failed for %s" % pet["id"]), "the night is over, and said"
        at(eng, eng.cfg["sleep"]["wake_hour"] + 1, eng.house["clock"]["day"] + 1)
        for _ in range(3):
            await eng.tick()
        assert not pet["sleep"], "the hob woke at dawn"
        sleep.condense = real_condense
        tries = []

        async def lost(mind):   # (a night's work that ends with the night not done)
            tries.append(eng.house["tick"])
        sleep.night = lost
        at(eng, 23, eng.house["clock"]["day"])
        for _ in range(20):
            await eng.tick()
        assert pet["sleep"] and pet["sleep"]["done"] and len(tries) == 2, "begun once more, then let go: %s" % tries
    finally:
        sleep.condense, sleep.night = real_condense, real_night
        heard.close()
    eng.close()


async def boot(d):
    """§1.6: a house.json cut short: the engine starts from house.json.bak, with one CRITICAL line."""
    eng, pet = house(d)
    for _ in range(12):
        await eng.tick()
    eng.close()
    bak = json.loads((Path(d) / "house.json.bak").read_text())
    whole = (Path(d) / "house.json").read_text()
    assert bak["tick"] < json.loads(whole)["tick"], "the .bak is the save before"
    (Path(d) / "house.json").write_text(whole[:len(whole) // 2])
    heard = Heard()
    try:
        again = Engine(load_config(), d, stub_brains)
        assert again.house["tick"] == bak["tick"] and len(heard.said(logging.CRITICAL, "house.json.bak")) == 1
    finally:
        heard.close()
    again.close()
    for f in Path(d).rglob("*.tmp"):
        raise AssertionError("a .tmp left behind: %s" % f)


async def calls(d):
    """§2.1, §2.2, §2.4, §2.5, §8: each HTTP call a row, with how it finished and its tokens; a cut-off reply is asked
    again differently, and only once; a reply that is not JSON is said; the deadline; the wait."""
    cfg = load_config(profile="live")
    cfg["spirit"]["on"] = False   # (written for v4.0.6's quick plan: with SPEC-v4.2's thinking plan a cut-off is asked again with thinking off: check_contracts.budget)
    eng, pet = house(d, cfg)
    for _ in range(3):
        await eng.tick()
    m = eng.minds[pet["id"]]
    brain = model.Model(cfg, Path(d) / "brain", {"pet": pet["id"]})
    sent, answers = [], []

    def post(body, timeout):
        sent.append(json.loads(json.dumps(body)))
        content, finish = answers.pop(0)
        return {"choices": [{"message": {"content": content}, "finish_reason": finish}], "usage": {"prompt_tokens": 900, "completion_tokens": 40}}
    brain.post = post
    text, ctx = brain4.plan_packet(eng.house, cfg, pet, m.mem)
    good = json.dumps(await m.brain.think4("plan", text, ctx))   # (a reply in the right shape, from the stub)

    async def ask(kind="plan", packet=text, ctx_=ctx):
        return await eng.call(1, pet["id"], kind, "check", lambda: brain.think4(kind, packet, ctx_), len(packet))
    rows = lambda: [dict(zip(("http", "finish", "prompt_tokens", "completion_tokens", "failed", "wait"), r))
                    for r in eng.db.execute("SELECT http, finish, prompt_tokens, completion_tokens, failed, wait FROM calls WHERE why='check' ORDER BY rowid")]
    heard = Heard()
    try:
        answers[:] = [(good, "length"), (good, "stop")]   # §2.1: cut off once, then whole
        assert isinstance(await ask(), dict)
        r = rows()
        assert [x["http"] for x in r] == [1, 2] and [x["finish"] for x in r] == ["length", "stop"] and r[0]["completion_tokens"] == 40 and r[0]["prompt_tokens"] == 900, r
        assert r[0]["failed"] == "cut off" and r[1]["failed"] is None and r[0]["wait"] is None and r[1]["wait"] is not None, "the thought's verdict and wait are on its last row"
        assert sent[1]["max_tokens"] == 2 * sent[0]["max_tokens"] and sent[1]["reasoning_effort"] == "none", "asked again with twice the room, never the same request"
        sent.clear()
        answers[:] = [(good[:50], "length"), (good[:50], "length")]   # §2.2: cut off twice
        assert await ask() == "cut off" and len(sent) == 2 and not answers, "no third call"
        assert len(heard.said(logging.WARNING, "cut off twice: plan %s 40" % pet["id"])) == 1 and rows()[-1]["failed"] == "cut off"
        answers[:] = [("I would rather not say", "stop"), ("still not json", "stop")]   # §2.4
        assert await ask() == "invalid json" and [x["failed"] for x in rows()[-2:]] == ["invalid json", "invalid json"]
        assert heard.said(logging.WARNING, "invalid json: plan %s 'I would rather not say'" % pet["id"])
        sent.clear()   # §2.5: the reflection thinks as the night does, in 4000 tokens; cut off, it is asked again with thinking off
        rtext, rctx = brain4.reflect_packet(m)
        answers[:] = [("{}", "length"), (json.dumps({"diary": "a day"}), "stop")]
        await ask("reflect", rtext, rctx)
        assert sent[0]["reasoning_effort"] == "low" and sent[0]["max_tokens"] == 4000 and sent[1]["reasoning_effort"] == "none" and sent[1]["max_tokens"] == 4000, sent
        # §2.3: a thought past its deadline frees the slot, and the next runs
        eng.cfg["model"]["timeout_seconds"] = 0.2
        t0 = time.monotonic()
        stuck = eng.call(1, pet["id"], "plan", "check", lambda: asyncio.to_thread(time.sleep, 1.5))
        after = eng.call(1, pet["id"], "plan", "check", lambda: asyncio.sleep(0, result={"aims": []}))
        assert await stuck == "timed out" and await after == {"aims": []} and time.monotonic() - t0 < 1.2, "the slot freed, the next thought ran"
        assert heard.said(logging.WARNING, "timed out: plan %s" % pet["id"]) and rows()[-2]["failed"] == "timed out"
        eng.cfg["model"]["timeout_seconds"] = 300
        eng.took["plan"] = deque([0.1] * 6, maxlen=20)
        await eng.call(1, pet["id"], "plan", "check", lambda: asyncio.sleep(1.1))
        assert heard.said(logging.WARNING, "slow: plan %s" % pet["id"]), "a call past twice the mean of its kind is said"
        # §8: the time a thought waited for its turn is kept apart from the time it took
        first = eng.call(1, pet["id"], "plan", "check", lambda: asyncio.sleep(0.4))
        second = eng.call(1, pet["id"], "plan", "check", lambda: asyncio.sleep(0))
        await asyncio.gather(first, second)
        assert rows()[-1]["wait"] >= 0.35 and eng.house["busy"][-1][1] < 0.2, "the wait is its own, and the model's busy share is compute only: %s %s" % (rows()[-1], eng.house["busy"][-1])
    finally:
        heard.close()
    eng.close()


def nits():
    """§4.8's model.py part: doing nothing needs no aim; an ambition is taken by its words."""
    ctx = {"hobs": ["Wen"], "does": list(brain4.DOES), "aim_kinds": ["make", "be with"], "moods": ["content"], "allowed": []}
    shape = model.schema4("react", ctx)
    assert valid(shape, {"thought": "", "feel": "content", "do": {"kind": "nothing", "who": "", "text": ""}, "steps": []}) is None, "nothing, with no aim"
    assert valid(shape, {"thought": "", "feel": "content", "do": {"kind": "aim", "who": "Wen", "text": "x"}, "steps": []}), "an aim still names its kind"
    packet = "your ambition for your life: none yet. Take one, to keep all your life: something you mean to do, and can finish. You could:\n  1. make a lamp\n  2. Find out what is past the garden gate\n"
    assert model.offered(packet) == ["make a lamp", "Find out what is past the garden gate"]
    took = lambda words: model.took_words({"ambition": {"take": words, "words": ""}}, packet)["ambition"]["pick"]
    assert took("find out what is past the garden gate.") == 2 and took("make a lamp") == 1 and took("keep") == 0 and took("fly to the moon") == 0
    assert "number" not in model.NIGHT_PARTS["ambition"] and valid(model.schema4("reflect", {"asks": ["ambition"], "hobs": []}), {"ambition": {"take": "make a lamp", "words": ""}}) is None


SERVER = r'''
import asyncio, json, sys, threading, time
from pathlib import Path
import engine.tick
from engine import server as s
mode = sys.argv[1]
if mode == "stuck":   # §1.7: a house step that never yields
    s.STALE_SECONDS, s.WATCH_SECONDS = 3, 0.5
    s.order.upkeep = lambda h, cfg: time.sleep(200)
    threading.Thread(target=s.watchdog, daemon=True).start()
    asyncio.run(s.loop())
elif mode == "unsaved":   # §1.7: a house that ticks but is never saved
    s.UNSAVED_SECONDS, s.WATCH_SECONDS, s.cfg["pace"] = 3, 0.5, 0.05
    def nowhere():
        raise OSError("no room on the disk")
    s.eng.write_house = nowhere
    threading.Thread(target=s.watchdog, daemon=True).start()
    asyncio.run(s.loop())
elif mode == "broadcast":   # §1.8: a client that never reads
    class Stuck:
        sent = 0
        async def send_json(self, state):
            Stuck.sent += 1
            await asyncio.sleep(1000)
        send_text = send_json   # (the page is sent text since §7.2's diff)
    async def main():
        sock, t = Stuck(), s.eng.house["tick"]
        s.clients[sock] = {"seen": 0, "room": None, "have": {}}
        s.cfg["pace"] = 0.1
        task = asyncio.create_task(s.loop())
        await asyncio.sleep(5)
        task.cancel()
        print(json.dumps({"ticks": s.eng.house["tick"] - t, "gone": sock not in s.clients, "sent": Stuck.sent}))
    asyncio.run(main())
elif mode == "headless":   # §9.3: no house until someone comes
    from fastapi import WebSocketDisconnect
    class Visitor:
        headers, sent = {"origin": s.cfg["server"]["origins"][0]}, []
        async def accept(self): pass
        async def send_json(self, x): Visitor.sent.append(x)
        async def send_text(self, x): Visitor.sent.append(x)
        async def receive_json(self): raise WebSocketDisconnect()
    before = s.eng.house["lineage"], (s.DATA / "house.json").exists()
    asyncio.run(s.ws(Visitor()))
    print(json.dumps({"before": before, "after": bool(s.eng.house["lineage"]), "sent": len(Visitor.sent), "saved": (s.DATA / "house.json").exists()}))
elif mode == "nodist":   # §9.3
    s.DIST = Path("/nonexistent/dist")
    s.main()
elif mode == "serve":   # §1.9, §1.10: a stub day, quickly
    s.DIST, s.cfg["pace"] = Path(sys.argv[2]), 0.02
    s.main()
'''


def server(d, mode, *args, env=None, timeout=60):
    env = dict(os.environ, PET_DATA=str(d), PET_PROFILE="viewdev", **(env or {}))
    return subprocess.run([sys.executable, "-c", SERVER, mode, *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)


def serving(d):
    """§1.9, §1.10: the real entry on port 8110 with a stub house, through a world day: every line of its log says
    when; a portrait from another page is refused; no access log."""
    dist = Path(d) / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<p>check</p>")
    out = open(Path(d) / "server.log", "w")
    proc = subprocess.Popen([sys.executable, "-c", SERVER, "serve", str(dist)], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                            env=dict(os.environ, PET_DATA=str(Path(d) / "data"), PET_PROFILE="viewdev", PET_HEADLESS="1", PET_PORT="8110"))
    try:
        url = "http://127.0.0.1:8110"
        for _ in range(60):
            try:
                urllib.request.urlopen(url + "/api/pets", timeout=2).read()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise AssertionError("the server did not come up: " + (Path(d) / "server.log").read_text()[-2000:])
        pid = json.loads(urllib.request.urlopen(url + "/api/pets", timeout=5).read())["pets"][0]["id"]

        def put(origin, body):
            req = urllib.request.Request(url + "/portrait/%s.png" % pid, body, {"Origin": origin, "Content-Type": "image/png"}, method="POST")
            try:
                return urllib.request.urlopen(req, timeout=5).status
            except urllib.error.HTTPError as e:
                return e.code
        assert put("http://elsewhere.example", b"\x89PNG\r\n\x1a\n" + b"0" * 10) == 403, "a portrait from another page is refused"
        assert put("http://localhost:8000", b"\x89PNG\r\n\x1a\n" + b"0" * 70000) == 413, "too big, refused before it is read"
        for _ in range(240):   # (a stub day: the viewdev profile's 240 ticks)
            if json.loads(urllib.request.urlopen(url + "/api/away?since=999999", timeout=5).read())["tick"] >= 250:
                break
            time.sleep(0.5)
        else:
            raise AssertionError("the stub day did not pass")
    finally:
        proc.terminate()
        proc.wait(timeout=30)
        out.close()
    lines = (Path(d) / "server.log").read_text().splitlines()
    stamp = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} (DEBUG|INFO|WARNING|ERROR|CRITICAL) \S+: ")
    assert lines and all(stamp.match(l) for l in lines), "every line of the log says when: %s" % [l for l in lines if not stamp.match(l)][:5]
    assert any("Uvicorn running" in l for l in lines) and not any("GET /api/pets" in l for l in lines), "uvicorn's lines are in the house's form; no access log"
    return len(lines)


def processes(d):
    """The server's parts, each in a child process on a folder of its own."""
    r = server(Path(d) / "stuck", "stuck", env={"PET_HEADLESS": "1"})
    assert r.returncode == 1 and "has not moved" in r.stderr and "CRITICAL" in r.stderr, "§1.7: a stuck loop ends the process: %s" % r.stderr[-800:]
    r = server(Path(d) / "unsaved", "unsaved", env={"PET_HEADLESS": "1"})
    assert r.returncode == 1 and "has not been saved" in r.stderr, "§1.7: a house never saved ends the process: %s" % r.stderr[-800:]
    r = server(Path(d) / "broadcast", "broadcast", env={"PET_HEADLESS": "1"})
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert got["gone"] and got["sent"] == 1 and got["ticks"] >= 3, "§1.8: the client that does not read is let go after one message, and the tick goes on: %s" % got
    r = server(Path(d) / "headless", "headless")
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert got["before"] == [None, False] and got["after"] and got["saved"] and got["sent"] == 1, "§9.3: no house until the first visitor: %s" % got
    r = server(Path(d) / "nodist", "nodist")
    assert r.returncode == 1 and "build the view first: cd view && npm install && npm run build" in r.stderr, "§9.3: %s" % r.stderr[-400:]
    other = Path(d) / "profile"   # §1.6: a house made with another clock says so in one line, and exits EX_CONFIG
    eng = Engine(load_config(), other, stub_brains)
    eng.new_lineage()
    eng.close()
    r = server(other, "headless")
    assert r.returncode == 78 and "the house cannot start: this house was made with profile None" in r.stderr, (r.returncode, r.stderr[-400:])
    return serving(Path(d) / "serve")


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        for name, check in (("save order", save_order), ("sqlite", wal), ("flush", flush), ("hatch", hatch), ("night", night), ("boot", boot), ("calls", calls)):
            t0 = time.monotonic()
            asyncio.run(check(str(Path(d) / name.replace(" ", "_"))))
            print("  %s: ok (%.1f s)" % (name, time.monotonic() - t0))
        nits()
        print("  prompt nits: ok")
        n = processes(Path(d) / "server")
        print("  server: ok (%d lines of log, each with its time)" % n)
    print("spine check passed")


if __name__ == "__main__":
    main()
