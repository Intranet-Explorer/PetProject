"""SPEC-v4.0.5 §8: the Lab's "Today" (engine/lab4.py), on half a stub day of five grown hobs, and past midnight into the
next: every field is there, and every one is a number, a list or words, but for those another part of the engine
writes (calls.wait and calls.finish, the last good save, the re-parented orphans) where that part
is not there yet.

SPEC-v4.2 §11.5 (helper E): the Lab's "Spirit" on a third of a stub day with spirit on, with a talk that left its
minds, a death of sickness, a tale and a line of every kind in the ledger laid in by hand (C and D write them): every
field is there, the numbers count what was laid in, it is plain data and it changes nothing; its cause table and its
ledger cover contracts' lists. And the two shapes the page reads: the card never carries a secret's words before it is
found out, and a talk's minds come by hob.

    uv run python -m engine.check_lab4
"""
import asyncio
import json
import os
import tempfile

from . import tick as _tick  # noqa: F401  (the engine first: a module run alone)
from . import contracts as K
from . import lab4
from .check_brain4 import hob, house
from .world import label

HOB = ("id", "name", "needs", "memories", "aims", "thoughts", "talks", "talks_failed", "invalid_json", "cut_off")
HOUSE = ("save_age", "busy_world_hour", "busy_real_hour", "busy_day", "calls_hour", "budget", "eggs_laid", "eggs_found", "reparented",
         "talks_failed", "ws_clients", "ws_bytes")
SPIRIT_HOB = ("id", "name", "memories", "beliefs", "talks", "knows", "wants_holds", "thinking_seconds")
SPIRIT_HOUSE = ("deaths", "happenings", "unwell", "tales", "theories", "thinking_share", "ledger", "missed_fields")


async def spirit(d):
    from .check_mind import house as spirit_house
    eng, a = await spirit_house(d)
    h, cfg = eng.house, eng.cfg
    room = h["rooms"][a["room"]]
    b, c, dead = (hob(eng, room, [3 + 2 * i, 5]) for i in range(3))
    for _ in range(cfg["ticks_per_day"] // 3):
        await eng.tick()
    h["talks"].append({"n": 999, "tick": h["tick"], "room": room["id"], "a": a["id"], "b": b["id"], "lines": [{"who": a["id"], "text": "the pond is cold"}],
                       "minds": {label(a): {"wants": "to be forgiven", "holds": "that I broke the cup", "knows": "it fears the cellar", "remember": ""},
                                 label(b): {"wants": "the clay", "holds": "", "knows": "", "remember": ""}}})
    dead.update(stage="dead", cause="sickness", died=h["tick"], lineage=h["lineage"]["id"])
    eng.minds.pop(dead["id"], None)
    h.setdefault("tales", []).append(K.tale({"id": "t1", "about": dead["id"], "name": label(dead), "cause": "sickness"}))
    rec = {"missed": dict(pet=a["id"], kind="react", fields=["remember"]), "acted": dict(pet=a["id"], belief="b1", hook="avoid_place"), "told": dict(by=a["id"], to=[b["id"]], tale="t1"),
           "knows": dict(a=a["id"], b=b["id"], n=1), "refusal": dict(pet=a["id"], text="the clay is in the storeroom"), "secret found": dict(pet=b["id"], by=a["id"]),
           "happening": dict(name="storm", target=None), "nursed": dict(pet=c["id"], by=a["id"], how="nurse"),
           "monologue": dict(a=a["id"], b=b["id"], pairs=2), "purple": dict(a=a["id"], b=b["id"], why="the hour")}
    for what in K.LEDGER:
        K.note(h, what, **rec[what])
    c["sick"] = {"level": "ill", "since": h["tick"]}
    a.update(drive={"name": "to be loved by one", "target": b["id"]}, flaw="proud", voice={"style": "fussy", "cares": "the book"},
             secret={"kind": "lie", "text": "I took the blue feather", "tick": 1}, visitor_theory="the visitor made the walls")
    before = json.dumps(h, sort_keys=True, default=str)
    s = lab4.spirit(eng)
    assert json.dumps(h, sort_keys=True, default=str) == before, "the Lab's Spirit changes nothing"
    assert json.loads(json.dumps(s)) == s, "plain data"
    assert set(K.CAUSES) <= set(lab4.CAUSES) and set(lab4.LEDGER) == set(K.LEDGER), "the cause table and the ledger cover contracts' lists"
    pets = {p["id"]: p for p in s["pets"]}
    assert set(pets) == {p["id"] for p in h["pets"].values() if p["stage"] not in ("egg", "dead")}, "every living hob"
    for p in s["pets"]:
        for k in SPIRIT_HOB:
            assert p.get(k) is not None, "%s: %s is there" % (p["name"], k)
        q = h["pets"][p["id"]]
        assert p["memories"]["model"] + p["memories"]["engine"] == len(q.get("memories") or []), p
    assert any(p["memories"]["model"] for p in s["pets"]), "the stub's reactions left model-written memories"
    for k in SPIRIT_HOUSE:
        assert s["house"].get(k) is not None, "the house: %s is there" % k
    A, H = pets[a["id"]], s["house"]
    assert A["talks"] >= 1 and A["knows"] >= 1 and A["wants_holds"] >= 1 and A["beliefs"]["acted_today"] == 1, A   # (the hand-made talk's, and since C's merge the stub's own talks' too)
    assert A["knows"] <= A["talks"] and A["wants_holds"] <= A["talks"], "no more talks with minds than talks"
    assert H["deaths"]["sickness"] == 1 and all(H["ledger"][w]["today"] >= 1 for w in K.LEDGER) and H["missed_fields"].get("react.remember") == 1, H
    assert H["happenings"][0]["name"] == "storm" and H["tales"]["kept"] == 1 and H["tales"]["told_week"] == 1, H
    assert any(u["sick"] == "ill" for u in H["unwell"]) and {"name": label(a), "theory": "the visitor made the walls"} in H["theories"], H
    assert H["thinking_share"] is not None and 0 <= H["thinking_share"] <= 1
    # the card: a secret is "keeps something to itself" until found, and its words never reach the page before
    card = lab4.card(h, a)
    assert card == {"drive": "to be loved by one (%s)" % label(b), "flaw": "proud", "voice": K.STYLES["fussy"] + "; cares about the book", "secret": {"found": False}}, card
    assert "blue feather" not in json.dumps(card)
    a["secret"]["found"] = h["tick"]
    assert lab4.card(h, a)["secret"] == {"found": True, "text": "I took the blue feather"} and lab4.card(h, b).get("drive") and lab4.card(h, b).get("secret") in (None, {"found": False})   # (since C's merge every hob hatches with a drive)
    t = lab4.talk_view(h, h["talks"][-1])
    assert set(t["minds"]) == {a["id"], b["id"]} and t["minds"][a["id"]]["holds"] == "that I broke the cup" and lab4.talk_view(h, {"a": a["id"]}) == {"a": a["id"]}
    eng.close()
    return s


def maybe(eng, field):
    """The fields whose source is another helper's, and may not be merged in yet: None is right while it is not."""
    h, cols = eng.house, lab4.columns(eng.db)
    return {"cut_off": "finish" not in cols, "save_age": not hasattr(eng, "saved_at"),
            "reparented": (h.get("migrated") or {}).get("orphans") is None}.get(field, False)


def whole(eng, d, keys, where):
    for k in keys:
        assert k in d, "%s: %s is there" % (where, k)
        assert d[k] is not None or maybe(eng, k), "%s: %s is not null" % (where, k)


async def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        eng, pet = await house(d)
        h, cfg = eng.house, eng.cfg
        room = h["rooms"][pet["room"]]
        for i, g in enumerate((0.2, 0.5, 0.5, 0.8)):
            hob(eng, room, [2 + 2 * i, 5], orderly=g, curious=0.6)
        for _ in range(cfg["ticks_per_day"] // 2):
            await eng.tick()
            lab4.keep(h, cfg)
        t = lab4.today(eng, cfg, 2, 12345)
        assert t["day"] == h["clock"]["day"] and len(t["pets"]) == sum(q["stage"] not in ("egg", "dead") for q in h["pets"].values()) >= 5, "every living hob: %s" % [p["name"] for p in t["pets"]]
        for p in t["pets"]:
            whole(eng, p, HOB, p["name"])
            assert all(v is not None for v in p["needs"].values()) and sum(p["memories"].values()) == len(eng.house["pets"][p["id"]].get("memories") or []), p
            assert set(p["aims"]) == {"done", "failed", "open", "failed_text"} and len(p["aims"]["failed_text"]) == p["aims"]["failed"], p["aims"]
            for k in p["thoughts"].values():
                whole(eng, k, ("n", "seconds", "compute"), p["name"] + "'s thoughts")
                assert "wait" in k and (k["wait"] is not None or "wait" not in lab4.columns(eng.db)) and k["n"] > 0, k
        assert any(p["thoughts"] for p in t["pets"]), "the stub thought, and its thoughts are counted"
        whole(eng, t["house"], HOUSE, "the house")
        assert t["house"]["ws_clients"] == 2 and t["house"]["ws_bytes"] == 12345 and t["house"]["budget"] == cfg["model"]["calls_per_hour"]
        assert t["house"]["eggs_found"] == sum(bool(q.get("founder")) for q in h["pets"].values()) and 0 <= t["house"]["busy_day"] <= 1, t["house"]
        day = h["clock"]["day"]
        for _ in range(cfg["ticks_per_day"]):   # on past midnight: today's is kept as yesterday's
            await eng.tick()
            lab4.keep(h, cfg)
            if h["clock"]["day"] != day:
                break
        for _ in range(20):
            await eng.tick()
            lab4.keep(h, cfg)
        y = lab4.today(eng, cfg)["yesterday"]
        assert y["day"] == day and {p["id"] for p in y["pets"]} == {p["id"] for p in t["pets"]}, "yesterday: the same hobs"
        for p in y["pets"]:
            whole(eng, p, HOB, "yesterday, " + p["name"])
            assert p["aims"]["done"] + p["aims"]["failed"] + p["aims"]["open"] >= t["pets"][[q["id"] for q in t["pets"]].index(p["id"])]["aims"]["done"], "the day's aims, not cleared by the night"
        assert y["house"]["busy_day"] is not None
        eng.close()
        s = await spirit(d + "/spirit")
    print("lab4 check ok: %s" % {k: v for k, v in t["house"].items()})
    print("lab4 check ok, the Spirit section: %s" % {k: s["house"][k] for k in ("deaths", "thinking_share", "missed_fields")})


if __name__ == "__main__":
    asyncio.run(main())
