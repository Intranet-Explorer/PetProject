"""The sheet's self-check (24 November 2026): uv run python -m engine.check_sheet. A sheet is drawn the same way twice,
never fears its own place or pursuit, pulls the body's score the way its lines say, keeps a hob from a job it is
afraid of, is told to the hob in words, and with [sheet] off nothing reads it."""
from . import sheet, world
from .world import load_config


def main():
    cfg = load_config()
    assert not sheet.on(cfg), "off unless a profile turns it on"
    assert sheet.scale(cfg) == sheet.turns(cfg) == sheet.seek(cfg) == 1.0, "off: the body's score is v5.3.2's"
    cfg["sheet"]["on"] = True
    house = world.new_house(cfg)
    rooms = list(house["rooms"].values())
    for r, t, n in zip(rooms, ("pond", "attic", "cellar"), ("the pond room", "the attic", "the cellar")):
        r["type"], r["name"] = t, n
    seen = set()
    for i in range(300):
        pet = {"id": "p%d" % i}
        sh = sheet.give(house, cfg, pet)
        assert sh == sheet.give(house, cfg, {"id": "p%d" % i}), "the same hob is given the same sheet"
        assert sum(v is not None for v in sh.values()) >= 2, sh
        f = cfg["sheets"]["fear"].get(sh["fear"] or "", {})
        assert sh["place"] not in f.get("rooms", ()), sh
        assert not set(f.get("does", ())) & set(cfg["sheets"]["pursuit"].get(sh["pursuit"] or "", {}).get("does", ())), sh
        seen.add(tuple(sh.values()))
    assert len(seen) > 100, "three hundred hobs, more than a hundred different sheets: %d" % len(seen)
    for slot in sheet.SLOTS:   # every activity the catalogue names is one the body has
        for k, v in cfg["sheets"][slot].items():
            assert all(n in cfg["activities"] or n in cfg.get("behaviours", {}) for n in v.get("does", ())), (slot, k)
            assert v["words"]
    here, pond = rooms[1], rooms[0]
    here["doors"], pond["doors"] = {"west": pond["id"]}, {"east": here["id"]}
    pet = {"id": "p1", "room": here["id"], "rooms": {here["id"]: 0, pond["id"]: 0}, "needs": {}, "sheet": {"place": None, "pursuit": "music", "fear": "water", "food": None}}
    A = cfg["activities"]
    adj = lambda name, t=None: sheet.adjust(house, cfg, pet, name, A[name], t or {})
    assert adj("sing") == cfg["sheet"]["pursuit"] and adj("fish") == cfg["sheet"]["fear"] and adj("inspect") == 0
    assert adj("go next door", {"what": "west"}) == cfg["sheet"]["fear"], "not through the door to the pond"
    pet["room"] = pond["id"]
    assert adj("go next door", {"what": "east"}) == cfg["sheet"]["flee"], "and out of it, if it finds itself there"
    assert sheet.shuns(house, cfg, pet, "fish") and not sheet.shuns(house, cfg, pet, "tend"), "it takes no fishing job"
    assert sheet.pursues(cfg, pet, "sing") and not sheet.pursues(cfg, pet, "fish")
    pet["sheet"] = {"place": "attic", "pursuit": None, "fear": None, "food": "fish"}
    assert adj("go next door", {"what": "east"}) == cfg["sheet"]["place"], "the way to its favourite place"
    pet["room"] = here["id"]
    assert adj("go next door", {"what": "west"}) == -cfg["sheet"]["leave"], "and it is slow to leave it"
    assert adj("fish") == cfg["sheet"]["food"]
    L = {"rooms": set()}
    pet["room"] = pond["id"]
    sheet.lean(house, cfg, pet, L)
    assert L["rooms"] == {here["id"]}
    assert sheet.words(house, cfg, pet) == "you spend every free hour in the attic; you love fish above every other food", sheet.words(house, cfg, pet)
    # ---- mend: the living let go of what they hold against one another, once ----
    cfg["sheet"]["mend"] = True
    a, b = ({"id": "pa", "stage": "adult", "needs": {"comfort": 10.0, "curiosity": 10.0}, "avoid": ["pb"], "opinions": {"pb": {"liking": -9.0, "fear": 3, "fixed": {"liking": -4.0}}}},
            {"id": "pb", "stage": "adult", "needs": {"comfort": 90.0, "curiosity": 90.0}, "avoid": [], "opinions": {"pa": {"liking": 6.0, "fear": 0}}})
    house["pets"] = {"pa": a, "pb": b}
    house["grievances"] = [{"by": "pa", "against": "pb", "rung": 4}]
    sheet.mend(house, cfg)
    assert a["opinions"]["pb"]["liking"] == 0 and a["opinions"]["pb"]["fixed"]["liking"] == 0 and b["opinions"]["pa"]["liking"] == 6.0, "dislike is let go, liking is kept"
    assert not house["grievances"] and not a["avoid"] and a["needs"]["comfort"] == cfg["sheet"]["ease"] and b["needs"]["comfort"] == 90.0
    a["opinions"]["pb"]["liking"] = -5.0
    sheet.mend(house, cfg)
    assert a["opinions"]["pb"]["liking"] == -5.0, "once"
    print("sheet check passed")


if __name__ == "__main__":
    main()
