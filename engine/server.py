"""The engine's front door (v1 §3, §16): the tick loop plus a websocket for the view.
Binds to localhost and checks Origin on every connection.

    uv run python -m engine.server
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from . import actions, log
from .brains.model import Model
from .brains.twin import Twin
from .tick import Pet
from .world import H, ROOT, W, load_config

cfg = load_config()
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
db = log.open_db(DATA / "pet.db")
pets = {"model": Pet("model", cfg, Model(cfg, DATA / "model"), DATA, db)}
if cfg["twin"]["enabled"]:   # the v1 baseline, headless, in its own identical copy of the world (SPEC-v2 §10)
    pets["twin"] = Pet("twin", cfg, Twin(cfg), DATA, db)
clients = {}   # websocket -> when it last reported an attentive visitor (0 = not attentive)


def visitor_present():
    """§4: a view tab is focused and has had input in the last 5 minutes. The tab reports that itself."""
    return any(time.time() - seen < 45 for seen in clients.values())


def snapshot():
    return {
        "size": [W, H], "tick_seconds": cfg["clock"]["tick_seconds"], "visitor_present": visitor_present(),
        "placeable": actions.placeable(pets["model"].world),
        "materials": {m: v["says"] for m, v in cfg["materials"].items() if "says" in v},
        "pets": {p.id: {"world": p.world, "beliefs": p.mem.beliefs, "things": p.mem.things, "journal": list(p.journal),
                        "accuracy": p.accuracy(), "series": p.series} for p in pets.values()},
    }


async def broadcast():
    state = snapshot()
    for sock in list(clients):
        try:
            await sock.send_json(state)
        except Exception:
            clients.pop(sock, None)


async def loop():
    # A crash can land between two pets' saves. Bring whichever is behind level, so they stay tick for tick.
    while len({p.world["tick"] for p in pets.values()}) > 1:
        await min(pets.values(), key=lambda p: p.world["tick"]).tick(False)
    while True:
        started = time.monotonic()
        try:
            present = visitor_present()
            for p in pets.values():   # a tick never waits for the model; thoughts land when they are ready
                await p.tick(present)
            await broadcast()
        except Exception:   # one bad tick must not end a two-week run
            logging.exception("tick failed")
        await asyncio.sleep(max(0.0, cfg["clock"]["tick_seconds"] - (time.monotonic() - started)))


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws(sock: WebSocket):
    if sock.headers.get("origin") not in cfg["server"]["origins"]:
        await sock.close(code=1008)
        return
    await sock.accept()
    clients[sock] = 0
    try:
        await sock.send_json(snapshot())
        while True:
            msg = await sock.receive_json()
            if not isinstance(msg, dict):
                continue
            if msg.get("type") == "presence":
                clients[sock] = time.time() if msg.get("active") is True else 0
            elif all([actions.visit(p.world, msg) for p in pets.values()]):   # every pet's world gets the same visit
                for p in pets.values():
                    p.world["news"].append("visitor")
                    p.save()
                await broadcast()
    except (WebSocketDisconnect, ValueError):
        pass
    finally:
        clients.pop(sock, None)


if (ROOT / "view" / "dist").exists():
    app.mount("/", StaticFiles(directory=ROOT / "view" / "dist", html=True))

if __name__ == "__main__":
    uvicorn.run(app, host=cfg["server"]["host"], port=cfg["server"]["port"])
