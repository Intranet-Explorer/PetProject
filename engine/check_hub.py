"""Self-check for the hub (SPEC-v3.5.1): the machine room hung on the storeroom and found like any room, the machine
and radio moving into it, the lit sign, the screens, the founder's statue and the station radio, proved without a
model or the network.

    uv run python -m engine.check_hub

Scripted minds only, in a temp folder of its own; a few seconds."""
import asyncio
import json
import tempfile

from . import actions, book, build, hub, machine, physics, radio, wants, world
from .check import at, engine
from .world import generate_room, room_type


async def run(d):
    cfg = world.load_config()
    cfg["weather"]["real"] = False

    # ---- §1 a tenth room, behind a door of the storeroom, outside the grid ----
    fresh = world.new_house(cfg)
    store = next(r for r in sorted(fresh["rooms"]) if room_type(fresh, r) == "storeroom")
    hb = fresh["rooms"][hub.RID]
    gx, gy = cfg["house"]["house"]["grid"]
    assert len(fresh["rooms"]) == gx * gy + 1 and not hb["type"] and room_type(fresh, hub.RID) == "hub", "a new house has its hub, not yet found"
    assert not (0 <= hb["cell"][0] < gx and 0 <= hb["cell"][1] < gy) and list(hb["doors"].values()) == [store] and hub.RID in fresh["rooms"][store]["doors"].values()
    assert "hub" not in fresh["unused_types"] and not hub.migrate(fresh, cfg), "once"

    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    at(eng, 10)
    pet.update(stage="elder", name="Lean")
    store = next(r for r in sorted(h["rooms"]) if room_type(h, r) == "storeroom")
    sr = generate_room(h, cfg, store)
    assert machine.spot(sr) is None and machine.view(h, cfg) is None, "the machine is not in the storeroom any more, and nobody has found it"
    pet["room"], pet["pos"], pet["rooms"][store] = store, [5, 5], h["tick"]
    assert any(w["key"] == "door:" + hub.RID for w in wants.candidates(h, cfg, pet)), "the new door is wanted like any untried door"
    # a house lived in before: the machine leaves its storeroom for the hub
    old = json.loads(json.dumps(h))
    del old["rooms"][hub.RID]
    old["rooms"][store]["doors"] = {k: v for k, v in old["rooms"][store]["doors"].items() if v != hub.RID}
    old["plan"].pop(hub.RID, None)
    old["rooms"][store]["objects"]["vending machine"] = world.fixture({"name": "vending machine", "pos": [8, 0], "machine": True})
    old["pets"][pet["id"]]["sleep"] = None
    assert hub.migrate(old, cfg) and machine.spot(old["rooms"][store]) is None and hub.RID in old["rooms"]
    assert any("a door you have never seen" in e for _, e in old["pets"][pet["id"]]["events"]), "whoever is in the storeroom sees the door where the machine stood"
    # found: the machine and the radio are there
    sr["objects"]["dial box"] = {"pos": [3, 3], "state": "on", "fix": {"radio": True, "movable": True, "states": ["off", "on"]}}
    room = generate_room(h, cfg, hub.RID, by=pet["id"])
    assert machine.spot(room) == "vending machine" and machine.view(h, cfg)["room"] == hub.RID, "the machine is in the hub"
    assert "dial box" in room["objects"] and "dial box" not in sr["objects"] and not room["objects"]["dial box"]["fix"].get("movable") and radio.is_on(h), "and the radio, still on, to stay"
    assert sum(1 for o in room["objects"].values() if o.get("fix", {}).get("terminal")) == 3 and any(o.get("fix", {}).get("sign") for o in room["objects"].values())

    # ---- §2 the lit sign ----
    n = len(h.get("ticker", {}).get("lines", []))
    world.moment(h, "made", "Lean made a cup it calls 'cup'", pet["id"], hub.RID)
    world.moment(h, "invented", "Lean invented the warm reacher: it reaches", pet["id"], hub.RID)
    world.moment(h, "death", "Sven died of old age, 16 days old", None, None)
    lines = h["ticker"]["lines"]
    assert len(lines) == n + 2 and lines[-2]["kind"] == "invention" and lines[-2]["anim"] == "star" and lines[-1]["text"].startswith("Sven"), "inventions and deaths, not every made thing"
    t = hub.ticker(h, cfg)
    assert t["room"] == hub.RID and t["forecast"]["text"].startswith("Tomorrow: ") and t["forecast"]["anim"] in ("sun", "cloud", "rain", "snow")
    pet["room"], pet["pos"], pet["sleep"] = hub.RID, [6, 4], None
    pet["rooms"][hub.RID] = h["tick"]
    pet["events"].clear()
    hub.read_sign(h, cfg, pet)
    hub.read_sign(h, cfg, pet)
    read = [e for _, e in pet["events"] if e.startswith("the lit sign")]
    assert len(read) == 3 and "Tomorrow" in read[0] and "Sven" in read[-1], "it reads tomorrow's weather and what is new, once: %s" % read

    # ---- §3 the screens ----
    other = world.new_pet(h, cfg, hub.RID, [8, 4])
    other.update(stage="adult", born=h["tick"], sleep=None)
    n1, p1 = hub.book_at(h, cfg, room, pet)
    room["objects"][n1]["screen"] = {"pet": pet["id"], "asked": "x", "title": None, "text": None, "tick": h["tick"]}
    n2, _ = hub.book_at(h, cfg, room, other)
    assert n1 != n2 and hub.book_at(h, cfg, room, pet)[0] == n1, "two pets look things up at two screens at once"
    h.setdefault("v31", {}).setdefault("arrived", {})["book"] = 0
    a = {"type": "ask_book", "question": "what is a hammer"}
    pet["asked_at"] = h["tick"] - round(cfg["book"]["terminal_hours"] * cfg["ticks_per_hour"]) - 1
    assert book.check_ask(a, h, cfg, pet, lambda x: bool(x)) is None, "a quarter hour at a screen, not an hour"
    text, fx, key = book.ask(h, cfg, pet, a, lambda x, n: x)
    s = room["objects"][n1]["screen"]
    assert s["pet"] == pet["id"] and s["asked"] == "what is a hammer" and s["tick"] == h["tick"], "what it asked is on the glass"
    assert actions.check(dict(a), h, cfg, pet, eng.minds[pet["id"]].mem) is not None, "and not again so soon"
    assert not any(hub.heavy(o) for o in room["objects"].values()), "a screen is not the heavy book: it cannot be carried"
    sr["objects"]["heavy book"] = {"pos": [2, 2], "state": None, "fix": {"book": True}}
    assert book.lookup(cfg, "what is shell")[0] != "Shell Oil Company" and book.lookup(cfg, "how to make supple reed")[0] == "Reed (plant)" if book.available(cfg) else True, "the everyday sense of the main noun"
    assert wants.book_room(h) == hub.RID and "the screens in" in wants.book_words(h, hub.RID), "a pet with a question is sent to the screens, not the heavy book"

    # ---- §4 the founder's statue ----
    P = cfg["build"]["project"]["statue"]
    first = world.new_pet(h, cfg, hub.RID, [0, 7])
    pet["parent"] = other["parent"] = first["id"]
    f1 = hub.founder(h, 1)
    assert f1 is first, "the founder is the first with no parent"
    f1.update(stage="dead", died=h["tick"], last_words="Stay near the lamp.")
    kin = [p for p in h["pets"].values() if p.get("family", 1) == 1 and p["stage"] not in ("egg", "dead")]
    eldest = min(kin, key=lambda p: (p["laid"], p["id"]))
    assert hub.honours(h, cfg, eldest, P) and not any(hub.honours(h, cfg, p, P) for p in kin if p is not eldest), "the eldest of the family, and only it"
    cands = []
    hub.candidates(h, cfg, eldest, lambda what, key, text, done, weight=1.0, **more: cands.append(dict(more, what=what, key=key, text=text)), [])
    assert cands and cands[0]["key"] == "%s|statue" % hub.RID and "statue of the first one" in cands[0]["text"], cands
    eldest["sleep"] = None
    hub.honour(h, cfg)
    assert any(w["key"] == "build:%s|statue" % hub.RID for w in eldest["wants"]) and len([w for w in eldest["wants"] if w["what"] != "get"]) <= cfg["wants"]["most"], "given the want outright"
    room["objects"]["lost cup"] = {"pos": list(P["at"]), "made": {"id": 99, "recipe": {"name": "lost cup", "kind": "cup", "material": "hard", "color": "blue", "size": 1}, "by": pet["id"], "owner": pet["id"],
                                   "tick": 0, "bits": [], "uses": 0, "ups": 0, "used_at": 0, "heirloom": None, "behavior": None}}
    name, o = build.begin(h, cfg, eldest, room, "statue")
    assert o["pos"] == list(P["at"]) and room["objects"]["lost cup"]["pos"] != o["pos"] and o["statue"]["of"] == f1["id"], "on its plinth, and nothing left lying on it"
    # a stone stack named for the statue, lying here, is taken up and does for a piece of its stone
    room["objects"]["statue stone"] = {"pos": [2, 6], "made": {"id": 98, "recipe": {"name": "statue stone", "kind": "stone stack", "material": "heavy", "color": "grey", "size": 2},
                                       "by": eldest["id"], "owner": eldest["id"], "tick": 0, "bits": ["wood"], "uses": 0, "ups": 0, "used_at": 0, "heirloom": None, "behavior": None}}
    eldest.update(room=hub.RID, pos=[3, 6], carrying=[], sleep=None)
    eldest["rooms"][hub.RID] = h["tick"]
    build.take_stack(h, cfg, eldest)
    assert "statue stone" not in room["objects"] and eldest["carrying"] == ["stone"], "taken up as stone"
    eldest["carrying"] = []
    v = {}
    hub.statue_view(h, cfg, o, v, d)
    assert v["statue"]["genome"] == f1["genome"] and v["statue"]["words"] == "Stay near the lamp."
    o["site"]["paws"] = {eldest["id"]: 3}
    build.stand(h, cfg, eldest, room, name)
    assert o["fix"]["built"] and o["statue"]["name"] == f1["name"] and any(l["kind"] == "statue" for l in h["ticker"]["lines"])
    if not f1["name"]:   # the first one was never named: the family names it
        eldest.update(room=hub.RID, pos=[5, 5])
        assert "statue" in actions.nameable(h, eldest)
        assert any(c["what"] == "name" for c in wants.candidates(h, cfg, eldest))
        r = actions.apply(h, cfg, eldest, {"type": "name", "what": "statue", "name": "Little One"}, eng.minds[eldest["id"]].mem)
        assert o["statue"]["name"] == "Little One" and "statue" not in actions.nameable(h, eldest), r

    # ---- §5 the station ----
    room["objects"]["dial box"]["state"] = "on"
    assert radio.playing(h, cfg, hub.RID)["id"] == cfg["radio"]["stations"][0]["id"]
    assert actions.visit(h, cfg, {"room": hub.RID, "type": "radio", "on": True, "plays": "rock"}) is None and radio.station(h, cfg)["id"] == "rock"
    assert any(e["tag"] == "radio" for e in physics.effects(h, cfg, pet)), "felt in the room"
    assert all(radio.allowed(cfg["radio"]["now_url"].format(chan=s_["chan"]), cfg) for s_ in cfg["radio"]["stations"]), "the engine asks only its allowlist"
    pet["events"].clear()
    radio.tick(h, cfg, {"artist": "A", "title": "Song"})
    radio.tick(h, cfg, {"artist": "A", "title": "Song"})
    assert sum("the radio is playing" in e for _, e in pet["events"]) == 1 and "loud and driving" in pet["events"][0][1]
    print("hub check passed")


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))


if __name__ == "__main__":
    main()
