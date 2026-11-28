"""SPEC-v5.0 §5 (helper C): the Lab's "Jobs" and what the page is sent of v5, on a stub house.

lab4.jobs with counters laid in by hand (contracts.count) and a board made by hand (contracts.board, as B's deficits
will write it): a row for every deficit kind, every counter read and its numbers the ones laid in, plain data, nothing
changed; and on a house where nothing has written yet, every row is there and reads zero. The snapshot of a house of
a hundred items, with [v5] on: each item's card in words (a lantern half full, a broken knife, a keepsake kept for its
own sake), each hob's scrap, the board; the board is a kept section (sent again only when it changes); and what v5 adds
to a whole message and to a kept one is under a bound (REVIEW-v4.0.4 D2). With [v5] off: no `v5`, no item, no scrap,
and no Jobs in /api/lab.

    uv run python -m engine.check_lab5
"""
import asyncio
import json
import os
import tempfile

from . import tick as _tick  # noqa: F401  (the engine first: a module run alone)
from . import contracts as K
from . import items, lab4, pages
from .check_brain4 import hob, house
from .check_machine import thing

KINDS = ("lantern", "knife", "cushion", "sign", "chest", "bucket", "jar", "blanket", "hammer", "bell")
PER_ITEM, BOARD, KEPT = 70, 1500, 400   # bytes v5 may add: to a whole message, an item's words each and the board; to a kept one (measured: ~50 an item, ~100 kept)


def board(h, pets):
    """A board as B's deficits.tick will leave it: three open deficits (one with no words yet), a job taken, one closed."""
    a, b = pets
    h.setdefault("v5", {})["board"] = K.board({
        "deficits": [{"kind": "cold", "where": "r1", "since": h["tick"] - 40, "words": "the attic is cold at night"},
                     {"kind": "leak", "where": "r2", "since": h["tick"] - 900, "words": "water is coming into the storeroom"},
                     {"kind": "own_box", "who": a["id"], "since": h["tick"] - 5}],
        "jobs": [{"id": "j1", "deficit": "cold|r1|", "kind": "cold", "taker": b["id"], "since": h["tick"] - 30, "state": "taken", "words": "a blanket for the attic"}],
        "closed": [{"kind": "dark", "where": "r3", "by": a["id"], "tick": h["tick"] - 100, "words": "the music room is lit tonight"}],
        "tick": h["tick"]})


def sizes(S, state, have=None):
    msg = S.trimmed(state, S.sections(state), have or {})
    return len(json.dumps(msg, separators=(",", ":"), ensure_ascii=False)), msg


async def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PET_SCRATCH")) as d:
        os.environ["PET_DATA"] = os.path.join(d, "server")   # (server.py makes an engine of its own as it is imported: in scratch, and set aside below)
        from . import server as S
        eng, p0 = await house(os.path.join(d, "house"))
        h, cfg = eng.house, eng.cfg
        own, S.eng, S.cfg = S.eng, eng, cfg
        room = h["rooms"][p0["room"]]
        pets = [p0] + [hob(eng, room, [2 + 2 * i, 5]) for i in range(4)]
        for _ in range(5):
            await eng.tick()

        # v5 off: nothing of it is sent
        cfg["v5"]["on"] = False
        for i in range(100):
            thing(eng, room, "thing %d" % i, KINDS[i % len(KINDS)], "hard", pets[i % 5]["id"])
        off = S.snapshot()
        assert "v5" not in off and not any("scrap" in p for p in off["pets"]) and not any("item" in o for r in off["rooms"] if r["type"] for o in r["objects"].values()), "v5 off: nothing of it"
        lab = await S.api_lab()
        assert "jobs" not in lab, "v5 off: the Lab has no Jobs"

        # v5 on, before anything has written: every row there, all zero
        cfg["v5"]["on"] = cfg["items"]["on"] = True
        cfg["grammar"]["on"] = False   # (v5.0's card words, on kinds.toml's hand verbs: a parsed lantern also heats a little)
        j = lab4.jobs(eng)
        assert [r["kind"] for r in j["deficits"]] == list(K.DEFICITS) and set(lab4.DEFICIT_WORDS) == set(K.DEFICITS), "a row for every deficit"
        assert all(not (r["open"] or r["opened"] or r["closed"] or r["taken"]) for r in j["deficits"]) and not any(j["made_for"].values()) and not any(j["verbs"].values())
        assert j["idle_share"] is None and all(p["idle_share"] is None for p in j["pets"]) and j["board"] == {"open": 0, "jobs": 0, "taken": 0, "closed": 0}, j

        # the counters and the board, laid in by hand
        a, b = pets[1], pets[2]
        laid = {"verbs": [("light", 3), ("cover", 2)], "broke": [("knife", 1)], "mended": [("lantern", 1)], "made_for": [("job", 2), ("plan", 1)],
                "scrap_earned": [(a["id"], 5)], "scrap_spent": [(a["id"], 2), (b["id"], 1)], "idle": [(a["id"], 3)], "awake": [(a["id"], 60), (b["id"], 40)],
                "taken": [(b["id"], 1)], "taken_kind": [("cold", 1)], "opened": [("cold", 1), ("leak", 1)], "closed": [("dark", 1)]}
        assert set(laid) == set(K.COUNTS)
        for key, subs in laid.items():
            for sub, n in subs:
                K.count(h, key, sub, n)
        a["scrap"] = 3
        board(h, (a, b))
        before = json.dumps(h, sort_keys=True, default=str)
        j = lab4.jobs(eng)
        assert json.dumps(h, sort_keys=True, default=str) == before, "the Lab's Jobs changes nothing"
        assert json.loads(json.dumps(j)) == j, "plain data"
        rows = {r["kind"]: r for r in j["deficits"]}
        assert rows["cold"] == {"kind": "cold", "says": lab4.DEFICIT_WORDS["cold"], "open": 1, "opened": 1, "closed": 0, "taken": 1}, rows["cold"]
        assert rows["leak"]["open"] == 1 and rows["dark"]["closed"] == 1 and rows["own_box"]["open"] == 1 and rows["mouse"]["open"] == 0
        P = {p["id"]: p for p in j["pets"]}
        assert P[a["id"]]["idle_share"] == 0.05 and P[a["id"]]["scrap"] == 3 and (P[a["id"]]["earned"], P[a["id"]]["spent"]) == (5, 2), P[a["id"]]
        assert P[b["id"]]["taken"] == 1 and P[b["id"]]["idle_share"] == 0 and j["idle_share"] == 0.03, (P[b["id"]], j["idle_share"])
        assert j["made_for"] == {"job": 2, "plan": 1, "taught": 0, "nothing": 0} and j["economy"] == {"earned": 5, "spent": 3, "held": 3}, j
        assert j["broke"] == {"knife": 1} and j["mended"] == {"lantern": 1} and j["verbs"]["light"] == 3 and set(j["verbs"]) == set(K.VERBS)
        assert j["board"] == {"open": 3, "jobs": 1, "taken": 1, "closed": 1}, j["board"]
        lab = await S.api_lab()
        assert lab["jobs"]["deficits"] == j["deficits"], "/api/lab carries the Jobs beside the Spirit"
        print("lab5: the Jobs section: %d deficit rows, idle share %s, made for %s" % (len(j["deficits"]), j["idle_share"], j["made_for"]))

        # the items' cards in words
        items.sync(h, cfg)
        objs = room["objects"]
        lamp, knife, sign, cushion = (next(o for o in objs.values() if o.get("made", {}).get("recipe", {}).get("kind") == k) for k in ("lantern", "knife", "sign", "cushion"))
        lamp["item"]["state"]["charge"]["oil"] = 3
        lamp["item"]["quality"] = 1.0
        knife["item"]["state"].update(wear=1.1, broken=True)
        cushion["item"]["state"]["wear"] = 0.9
        on = S.snapshot()
        R = next(r for r in on["rooms"] if r["id"] == room["id"])["objects"]
        said = {k: next(v["item"] for v in R.values() if v.get("made", {}).get("recipe", {}).get("kind") == k) for k in ("lantern", "knife", "sign", "cushion", "chest")}
        assert said["lantern"] == {"does": "it gives light", "wear": "new", "charge": "half a lantern of oil left", "quality": "finely made"}, said["lantern"]
        assert said["knife"]["wear"] == "broken" and said["knife"]["broken"] is True and said["knife"]["does"] == "it cuts", said["knife"]
        assert said["sign"]["does"] == "nothing: it is kept for its own sake" and said["cushion"]["wear"] == "about to break" and said["chest"]["does"] == "it holds things", said
        assert all("item" in v for v in R.values() if "made" in v), "every made thing's card has its words"
        lamp["item"]["state"]["charge"]["oil"] = 0
        assert pages.item_view(h, cfg, lamp, next(n for n, o in objs.items() if o is lamp))["charge"] == "empty"
        lamp["item"]["state"]["charge"]["oil"] = 3
        print("lab5: a card says %s" % said["lantern"])

        # the board on the snapshot, words for one B has not worded, and a kept section
        B = on["v5"]["board"]
        assert [x["words"] for x in B["deficits"]] == ["the attic is cold at night", "water is coming into the storeroom", lab4.DEFICIT_WORDS["own_box"]], B
        assert B["jobs"] == [{"deficit": "cold|r1|", "taker": b["id"], "words": "a blanket for the attic"}] and B["closed"][0]["by"] == a["id"], B
        assert {p["id"]: p["scrap"] for p in on["pets"] if p["stage"] != "dead"}[a["id"]] == 3
        whole, msg = sizes(S, on)
        hashes = msg["hashes"]
        assert msg["v5"]["board"] == B and "board" in hashes
        kept, msg = sizes(S, on, hashes)
        assert msg["v5"]["board"] is None and set(msg["v5"]) <= {"board", "tier", "marks53", "sites"}, "a board the page keeps is not sent again (SPEC-v5.1: the tier beside it; SPEC-v5.3: the marks and the sites)"
        h["v5"]["board"]["deficits"].pop()
        assert S.trimmed(S.snapshot(), S.sections(S.snapshot()), hashes)["v5"]["board"] is not None, "a board that changed is sent"
        board(h, (a, b))

        # what v5 adds, in bytes: the same house with it off
        cfg["v5"]["on"] = False
        off = S.snapshot()
        whole_off, msg = sizes(S, off)
        kept_off, _ = sizes(S, off, msg["hashes"])
        cfg["v5"]["on"] = True
        n = len(items.everything(h, cfg))
        print("lab5: %d items; v5 adds %d bytes to a whole message (%d -> %d), %d to a kept one (%d -> %d)" % (n, whole - whole_off, whole_off, whole, kept - kept_off, kept_off, kept))
        assert n >= 100 and whole - whole_off < PER_ITEM * n + BOARD and kept - kept_off < KEPT, "v5 adds little to the page's messages"
        eng.close()
        own.close()
    print("lab5 check ok")


if __name__ == "__main__":
    asyncio.run(main())
