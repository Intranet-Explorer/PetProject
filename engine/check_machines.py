"""Self-check for SPEC-v3.6b §6.1: each machine can be wanted, built, worked, worn and mended; the chain holds (no forge
or stove without fired bricks); each process gives what its rules say; dishes cook, serve, are shared, spoil and are
kept; recipes are found, taught, handed down and lost; little ones keep back from the hot machines; what a machine
makes waits in its tray.
    uv run python -m engine.check_machines"""
import asyncio
import tempfile

from . import actions, build, cook, craft, machine, machines, things, wants
from .check import at, engine, load_config
from .check_build import cand, put_up
from .check_machine import thing
from .world import generate_room, new_pet


async def run(d):
    cfg = load_config()
    cfg["weather"]["real"] = False
    C, MP, D = cfg["craft"], machines.projects(cfg), cfg["cook"]["dish"]
    bits = cfg["house"]["bits"]

    # ---- the data holds together ----
    assert {k: P["rooms"] for k, P in MP.items()} == {"kiln": ["workshop"], "loom": ["nursery", "music"], "millstone": ["cellar"], "forge": ["workshop"], "stove": ["cellar"]}, "the five machines, where the spec puts them"
    assert {k: P["needs"] for k, P in MP.items()} == {"kiln": {"clay": 3, "stone": 2}, "loom": {"wood": 3, "rope": 1}, "millstone": {"stone": 4},
                                                      "forge": {"fired brick": 3, "metal": 2}, "stove": {"fired brick": 3, "metal": 2}}, "built from what the spec says"
    assert machines.processes(cfg) == {"fire", "loom", "mill", "forge", "cook"} and all(p in C["process"] and p in craft.DONE and p in wants.TRY for p in machines.processes(cfg))
    brick = {how for (_, how), r in C["rules"].items() if r.get("gives") == "fired brick" or "fired brick" in r.get("also", [])}
    assert brick == {"fire"}, "the chain: only the kiln makes fired bricks, and the forge and the stove are built of them: %s" % brick
    assert 15 <= len(D) <= 25 and all(b in bits for d in D.values() for b in d["needs"]), "about twenty dishes, of what the house really has"
    assert all((b, "cook") in C["rules"] for b in cfg["seasons"]["food"]["bits"] if any(b in d["needs"] for d in D.values())), "every food that goes in a dish can be cooked"
    assert all(d["food"]["energy"] > cfg["effects"]["eat"]["energy"] for d in D.values() if d["food"]["energy"] > 5) and \
        max(D, key=lambda d: D[d]["food"]["energy"]) in ("fish and bean pie",), "a dish is better food than the bowl; fish is the best of all"

    eng, pet = engine(cfg, d + "/a")
    h = eng.house
    for _ in range(3):
        await eng.tick()
    at(eng, 10)
    pet.update(stage="adult", name="Oya")
    pet["stage_at"]["adult"] = h["tick"]
    mem = eng.minds[pet["id"]].mem
    nursery = h["rooms"][pet["room"]]
    hub_ = generate_room(h, cfg, next(iter(nursery["doors"].values())), "hub")
    cellar = generate_room(h, cfg, next(rid for rid, x in h["rooms"].items() if not x["type"]), "cellar")
    shop = generate_room(h, cfg, next(rid for rid, x in h["rooms"].items() if not x["type"]), "workshop")

    def go(room, carrying=()):
        pet.update(room=room["id"], pos=[5, 4], carrying=list(carrying), sleep=None)
        pet["rooms"][room["id"]] = h["tick"]
        pet["needs"]["energy"] = 80.0

    def act(a, who=None):
        who = who or pet
        why = actions.check(a, h, cfg, who, mem)
        return why, (None if why else actions.apply(h, cfg, who, a, mem)[0])

    def finish(room, name):
        h["tick"] = room["objects"][name]["run"]["done"]
        machines.tick(h, cfg)

    for r in (hub_, cellar, shop):
        go(r)

    # ---- wanting a kiln: clay by a lamp bakes only now and then; failing says what would do it, and gives the want ----
    go(nursery, ["clay"])
    nursery["objects"]["lamp"]["state"] = "on"
    for _ in range(40):
        why, said = act({"type": "process", "what": "clay", "how": "warm"})
        h["tick"] += 1
        if "real fire" in (said or ""):
            break
        pet["carrying"] = ["clay"]
    assert not why and "a real fire, closed in, would bake it through" in said and pet["carrying"] == ["clay"] and "kiln" in pet["wants_machine"], "failing to bake clay: %s %s" % (why, said)
    c = cand(h, cfg, pet, "build:%s|kiln" % shop["id"])
    assert c and "kiln" in c["text"] and "three pieces of clay and two pieces of stone" in c["text"], "and it wants a kiln in the workshop: %s" % c
    assert any("a kiln, which the house has none of" in l for _ in range(8) for l in things.better(h, cfg, pet, mark=True)), "the needs list offers it in its turn, once it has failed"
    other = new_pet(h, cfg, nursery["id"], [3, 3], name="Rain")
    other.update(stage="adult", sleep=None, rooms=dict(pet["rooms"]))
    tried = pet.pop("tried")
    assert not any("a kiln" in l for l in [x[1] for x in machines.offers(h, cfg, other)]) and any("a millstone" in x[1] for x in machines.offers(h, cfg, other)), \
        "nobody who has not failed at it is offered a kiln while nobody has tried firing; the loom and the millstone can come at any time"
    other["project"] = {"text": "Learn how clay is fired and make the first tile.", "since": h["tick"]}
    assert any("a kiln" in x[1] for x in machines.offers(h, cfg, other)), "a project to learn how clay is fired brings the kiln to the needs list"
    other["project"], pet["tried"] = None, tried
    assert any("a kiln" in x[1] for x in machines.offers(h, cfg, other)), "and once anyone has tried firing clay, it is offered to everyone"
    assert not any("forge" in x[0] or "stove" in x[0] for x in machines.offers(h, cfg, other)), "no forge or stove offered while nothing can make a fired brick"
    other["wants_machine"] = {"stove": h["tick"]}   # (as if it had tried to cook a fish by the lamp)
    assert not machines.wanted(h, cfg, other, "stove") and cand(h, cfg, other, "build:%s|stove" % cellar["id"]) is None, "nor wanted: it would stand half-built, waiting on bricks"
    assert machines.toward(h, cfg, pet, cfg["craft"]["rules"][("clay", "warm")]) and not machines.toward(h, cfg, pet, cfg["craft"]["rules"][("fish", "warm")]), \
        "baking clay by the pipe is weighted up while there is no kiln; cooking a fish there is not, while a stove could not be built"

    # ---- building it: one of each in the house; the first is a banner and a line on the board ----
    kiln, ko = put_up(h, cfg, pet, shop, "kiln")
    assert ko["fix"].get("kiln") and machines.built(h, "kiln") and not machines.wanted(h, cfg, pet, "kiln") and cand(h, cfg, pet, "build:%s|kiln" % shop["id"]) is None, "it stands, and is wanted no more"
    assert any(b["kind"] == "machine" and "the first kiln in the house" in b["text"] for b in h["bursts"][-3:]) and any((f.get("board") or "").startswith("THE FIRST KILN") for f in h["feats"]["list"][-3:]), "a banner and the board"
    assert any("forge" in x[0] for x in machines.offers(h, cfg, other)), "with a kiln, a forge can be offered"
    go(nursery, ["clay"])
    why, said = act({"type": "process", "what": "clay", "how": "warm"})
    assert not why and ("the kiln in the workshop would do it" in said or "fired clay" in pet["carrying"]), "with a kiln standing, failing by the lamp says where it would work: %s" % said

    # ---- working it: a load goes in and comes out in its run time, into the tray; one load at a time ----
    go(shop, ["clay", "sand"])
    why, said = act({"type": "process", "what": "clay", "how": "fire"})
    run = ko.get("run")
    assert not why and "minutes" in said and run and run["bit"] == "clay" and pet["carrying"] == ["sand"], "the clay goes in, and it will be a while: %s %s" % (why, said)
    assert run["done"] - h["tick"] == round(MP["kiln"]["machine"]["run"] / cfg["clock"]["tick_seconds"]), "a load takes the kiln's run"
    assert "busy firing clay" in act({"type": "process", "what": "sand", "how": "fire"})[0], "one load at a time"
    finish(shop, kiln)
    tray = machines.tray(shop, kiln)
    assert [s["bit"] for s in tray] == ["fired brick"] and pet["got"][0] == "fired brick" and "clay|fire" in pet["recipes"] and ko["output"] == {"fired brick": 1}, "out it comes, a fired brick in the tray: %s" % tray
    assert any("is done: a fired brick waits in its tray" in e for _, e in pet["events"]), "and whoever set it going is told"
    pet["carrying"] = ["clay"]
    act({"type": "process", "what": "clay", "how": "fire"})
    finish(shop, kiln)
    assert sorted(s["bit"] for s in machines.tray(shop, kiln)) == ["fired brick", "fired clay"], "the next load comes out as what the house has made least of"
    name, site = build.begin(h, cfg, pet, cellar, "stove")
    assert "fired brick" in machines.needed(h)
    pet["carrying"] = ["clay"]
    act({"type": "process", "what": "clay", "how": "fire"})
    finish(shop, kiln)
    assert [s["bit"] for s in machines.tray(shop, kiln)].count("fired brick") == 2, "a stove under way wants fired bricks: that is what the clay is shaped into"
    del cellar["objects"][name]
    shop["spots"] = [s for s in shop["spots"] if not s.get("machine")]

    # ---- a full tray waits to be emptied; at night it rests; little ones keep back from what is hot ----
    shop["spots"] += [{"bit": "glass", "pos": [8, 3], "ready": True, "back": None, "loose": True, "machine": kiln} for _ in range(MP["kiln"]["machine"]["hold"])]
    go(shop, ["sand"])
    assert "tray is full" in act({"type": "process", "what": "sand", "how": "fire"})[0], "a full tray waits"
    things.drop_bits(h, cfg, shop, [2, 2], ["pebble"] * 20)
    assert len(machines.tray(shop, kiln)) == MP["kiln"]["machine"]["hold"], "what waits in a tray is never swept away with loose bits"
    shop["spots"] = [s for s in shop["spots"] if not s.get("machine")]
    at(eng, 23)
    assert "banked for the night" in act({"type": "process", "what": "sand", "how": "fire"})[0], "a machine rests at night"
    at(eng, 10, h["clock"]["day"] + 1)
    kid = new_pet(h, cfg, shop["id"], [5, 5], parent=pet["id"], name="Bogna")
    kid.update(stage="youngling", sleep=None, carrying=["sand"])
    kid["rooms"][shop["id"]] = h["tick"]
    kid.setdefault("recipes", {})["sand|fire"] = {"tick": h["tick"], "from": "found"}
    assert "little ones keep back" in (actions.check({"type": "process", "what": "sand", "how": "fire"}, h, cfg, kid, mem) or ""), "a little one keeps back from the kiln"
    assert machines.targets(h, cfg, kid, cfg["activities"]["work a machine"], lambda t: t) == [], "and its body does not go to it"

    # ---- the body works one by itself: what it knows, from its paws, the room or the machine's stock ----
    go(hub_)
    go(shop, [])
    machine.state(h, cfg)["stock"]["sand"] = 10
    pet["recipes"]["sand|fire"] = {"tick": h["tick"], "from": "found"}
    t = machines.targets(h, cfg, pet, cfg["activities"]["work a machine"], lambda t: t)
    assert t and t[0]["job"][:3] == ["fire", "sand", "stock"] and t[0]["where"] == "firing sand in the kiln", "a load from the machine's stock: %s" % t
    now = dict(t[0], name="work a machine", do="machine")
    told, did = machines.finish(eng.minds[pet["id"]], now)
    assert did and "fetched sand from the machine's stock" in told and ko["run"]["bit"] == "sand" and machine.state(h, cfg)["stock"]["sand"] == 9, "fetched and in: %s" % told
    finish(shop, kiln)
    machine.state(h, cfg)["stock"]["sand"] = machines.KEEP
    assert machines.source(h, cfg, pet, shop, "sand") is None, "the stock is never drawn below a few"
    shop["spots"] = [s for s in shop["spots"] if not s.get("machine")]

    # ---- every machine's rules give what they say ----
    loom, _ = put_up(h, cfg, pet, nursery, "loom")
    mill, _ = put_up(h, cfg, pet, cellar, "millstone")
    forge, _ = put_up(h, cfg, pet, shop, "forge")
    thing(eng, shop, "hammer", "hammer", "hard", pet["id"])
    where = {"fire": (shop, kiln), "loom": (nursery, loom), "mill": (cellar, mill), "forge": (shop, forge)}
    for (bit, how), rule in C["rules"].items():
        if how not in where:
            continue
        room, name = where[how]
        go(room, [bit])
        why, said = act({"type": "process", "what": bit, "how": how})
        assert not why and rule["says"] in said, "%s|%s: %s %s" % (bit, how, why, said)
        finish(room, name)
        out = [s["bit"] for s in machines.tray(room, name)]
        assert len(out) == 1 and out[0] in [rule["gives"]] + rule.get("also", []), "%s|%s gives what its rule says: %s" % (bit, how, out)
        room["spots"] = [s for s in room["spots"] if not s.get("machine")]
    assert "hammer" in C["process"]["forge"]["tool"] and craft.words(cfg, "clay|fire") == "clay, fired in the kiln, makes fired brick"

    # ---- wear and mending ----
    build.wear_out(h, cfg, shop, kiln)
    go(shop, ["sand"])
    assert act({"type": "process", "what": "sand", "how": "fire"})[0] == craft.NOWHERE["fire"] and machines.at(shop, "fire") is None, "a worn kiln does nothing"
    v = {}
    machines.view(h, cfg, shop, kiln, ko, v)
    assert v["machine"]["state"] == "worn" and v["machine"]["led"] == "KILN: WORN"
    build.mend(h, cfg, pet, shop, kiln)
    assert machines.at(shop, "fire") and not act({"type": "process", "what": "sand", "how": "fire"})[0], "mended with the hammer, it works again"
    finish(shop, kiln)
    shop["spots"] = [s for s in shop["spots"] if not s.get("machine")]

    # ---- wanting a stove; cooking: a dish found is a family recipe, and the pot stands on the stove with servings ----
    go(nursery, ["fish"])
    why, said = act({"type": "process", "what": "fish", "how": "warm"})
    assert not why and "in a pot over a fire it would cook through" in said and "stove" in pet["wants_machine"] and pet["carrying"] == ["fish"], said
    assert cand(h, cfg, pet, "build:%s|stove" % cellar["id"]), "and it wants a stove in the cellar"
    stove, so = put_up(h, cfg, pet, cellar, "stove")
    go(cellar, ["fish", "bean"])
    kid.update(room=cellar["id"], pos=[4, 4], carrying=[])
    why, said = act({"type": "process", "what": "fish", "how": "cook"})
    assert not why and "a stew" in said and pet["carrying"] == [] and "dish:fish stew" in pet["recipes"] and so["run"]["dish"] == "fish stew", "fish and a bean make a stew: %s %s" % (why, said)
    assert "dish:fish stew" in kid["recipes"], "a young one watching picks it up"
    assert craft.words(cfg, "dish:fish stew") == "fish and bean, cooked together at the stove, make fish stew"
    pet["carrying"] = ["bean"]
    assert "the stove is busy cooking fish stew" in (act({"type": "process", "what": "bean", "how": "cook"})[0] or ""), "one pot at a time"
    finish(cellar, stove)
    pot = so["pot"]
    assert pot and pot["dish"] == "fish stew" and pot["servings"] == D["fish stew"]["servings"] and any(b["kind"] == "dish" for b in h["bursts"][-3:]), "a pot of stew, and the first dish is a banner: %s" % pot
    assert any("has cooked fish stew" in e for _, e in other["events"]) or other["room"] not in pet["rooms"], "the house is told"
    v = {}
    machines.view(h, cfg, cellar, stove, so, v)
    assert v["machine"]["pot"]["dish"] == "fish stew" and v["machine"]["led"] == "STOVE: FISH STEW · 4 SERVINGS", v["machine"]
    assert "there is fish stew in the pot on the stove still" in (act({"type": "process", "what": "bean", "how": "cook"})[0] or ""), "a full pot wants eating before the next"
    pet["carrying"] = []

    # ---- eating from one pot together: better food than the bowl, and company for both ----
    pet.update(last_eat=-10 ** 9)
    text, fx, _ = actions.use(h, cfg, pet, stove)
    assert "you ate some fish stew" in text and fx["energy"] == D["fish stew"]["food"]["energy"] > cfg["effects"]["eat"]["energy"] and "company" not in fx, (text, fx)
    other.update(room=cellar["id"], last_eat=-10 ** 9, temper=dict(other["temper"], bold=0.5, playful=0.5))
    pet["needs"]["company"] = was = 50.0
    text, fx, _ = actions.use(h, cfg, other, stove)
    assert fx.get("company") and pet["needs"]["company"] > was and "with Oya" in text, "two who ate from one pot ate together: %s %s" % (text, fx)
    assert any(m["kind"] == "meal" and "ate fish stew together" in m["text"] for m in h["moments"]), "the house notices"
    assert pot["servings"] == D["fish stew"]["servings"] - 2 and set(pot["ate"]) == {pet["id"], other["id"]}

    # ---- favourites: the dish its parent cooked for it when it was little ----
    kid["last_eat"] = -10 ** 9
    text, fx, _ = actions.use(h, cfg, kid, stove)
    assert kid["loves"] == ["fish stew"] and "your parent made it for you" in cook.loves_line(kid) and "you love fish stew" in text, (kid.get("loves"), text)

    # ---- a pot not eaten up goes stale in a day; with a keeper in the room it keeps three ----
    h["tick"] = pot["keeps"]
    cook.hourly(h, cfg)
    assert pot["servings"] == 0 and any(m["kind"] == "stale" for m in h["moments"]), "it goes stale"
    thing(eng, cellar, "jar", "jar", "hard", pet["id"])
    go(cellar, ["bean"])
    act({"type": "process", "what": "bean", "how": "cook"})
    finish(cellar, stove)
    assert so["pot"]["dish"] == "bean soup" and so["pot"]["keeps"] - so["pot"]["at"] == round(cfg["cook"]["cook"]["kept_days"] * cfg["ticks_per_day"]), "kept in a room with a jar"
    so["pot"]["servings"] = 0

    # ---- recipes: taught, handed down with its finder's name on the dish, and lost ----
    stranger = new_pet(h, cfg, cellar["id"], [6, 5], name="Moss")
    stranger.update(stage="adult", sleep=None)
    stranger["rooms"][cellar["id"]] = h["tick"]
    assert craft.pass_on(h, cfg, pet, stranger) and any(k.startswith("dish:") for k in stranger["recipes"]), "taught"
    stranger["recipes"] = {"dish:fish stew": {"tick": h["tick"], "from": "told by Oya"}}
    stranger.update(carrying=["fish", "bean"], room=cellar["id"], pos=[5, 4], needs=dict(stranger["needs"], energy=80.0))
    why, said = act({"type": "process", "what": "fish", "how": "cook", "dish": "fish stew"}, stranger)   # (as its body would: the dish it knows)
    assert not why and so["run"]["title"] == "Oya's fish stew", "a dish from a handed-down recipe carries its finder's name: %s %s" % (why, so.get("run"))
    finish(cellar, stove)
    assert so["pot"]["title"] == "Oya's fish stew"
    baby = new_pet(h, cfg, cellar["id"], [2, 2], parent=pet["id"], name="Pip")
    craft.inherit(h, cfg, baby)
    for p in (pet, kid, stranger):
        p["recipes"].pop("dish:bean soup", None)
    if "dish:bean soup" not in baby.get("recipes", {}):
        craft.lost(h, cfg)
        assert h["recipes"]["dish:bean soup"].get("lost") and any(m["kind"] == "forgotten" and "bean soup" in m["text"] for m in h["moments"]), "lost when nobody living knows it"

    # ---- wants: to eat from a pot, hungry enough; to cook what it knows with what it carries ----
    so["pot"]["servings"], so["pot"]["ate"] = 3, {}
    other["needs"]["energy"] = 40.0
    c = cand(h, cfg, other, "meal:%d" % so["pot"]["n"])
    assert c and "there is Oya's fish stew on the stove" in c["text"] and c["room"] == cellar["id"], "a hungry hob wants some: %s" % c
    so["pot"]["servings"] = 0
    pet.update(carrying=["fish", "bean"])
    c = cand(h, cfg, pet, "cook:fish stew")
    assert c and "you want to cook fish stew" in c["text"], "one who knows it and carries it wants to cook it: %s" % c
    h["kitchen"]["log"] = [e for e in h["kitchen"]["log"] if e[0] != "ate"]
    pet["offered"] = {}
    assert any("a cooked meal: nobody has eaten one today" in l for _ in range(8) for l in things.better(h, cfg, pet, mark=True)), "the needs list asks for a cooked meal"
    # ---- 18 October 2026: a fish in the paws wants cooking; the train takes loose fish and a full tray to be put by ----
    pet.update(carrying=["fish"], recipes={k: v for k, v in pet["recipes"].items() if not k.startswith("dish:")})
    c = cand(h, cfg, pet, "cook:" + cfg["craft"]["rules"][("fish", "cook")]["gives"])
    assert c and "you have a fish: you want to cook it" in c["text"], "a fish in the paws wants cooking, with no recipe for it yet: %s" % c
    from . import rail
    h["rail"] = {"rooms": {r["id"]: {"platform": [1, 1]} for r in h["rooms"].values() if r["type"]}, "depot": hub_["id"]}
    tr = {"held": [], "trail": [[shop["id"], [1, 1]]], "lead": "engine"}
    shop["spots"] = [s_ for s_ in shop["spots"] if not s_.get("machine")]
    things.drop_bits(h, cfg, shop, [5, 5], ["fish"])
    rail.bits_on(h, cfg, tr, shop)
    assert [x["spot"] for x in tr["held"]] == ["fish"] and tr["held"][0]["to"] == cellar["id"], "a loose fish goes on the train, to the stove: %s" % tr["held"]
    full = [n for n, o in shop["objects"].items() if machines.key_of(o) == "kiln"][0]
    hold = build.PROJECT["kiln"]["machine"]["hold"]
    shop["spots"] += [{"bit": "fired brick", "pos": [8, 5], "ready": True, "back": None, "loose": True, "since": h["tick"], "machine": full} for _ in range(hold)]
    rail.bits_on(h, cfg, tr, shop)
    assert hold <= 4 and not machines.tray(shop, full) and sum(x["spot"] == "fired brick" for x in tr["held"]) == hold, "a full tray goes to the store"
    rail.bits_off(h, cfg, tr, cellar)
    assert not tr["held"] or all(x["to"] != cellar["id"] for x in tr["held"]), "and the fish is put by at the stove"
    assert any(s_["bit"] == "fish" for s_ in cellar["spots"]), "it is there"

    # ---- 18 October 2026: an everyday kind made again and again is worth less, as a charm is ----
    pet["made_at"] = [[h["tick"] - 10, "spring|springy"], [h["tick"] - 5, "spring|hard"]]
    assert things.kind_lately(h, cfg, pet) == ("spring", 2), "two springs today"
    from .world import plural
    assert [plural(w) for w in ("box", "patch", "berry", "spring", "toy")] == ["boxes", "patches", "berries", "springs", "toys"]
    assert things.honest(cfg, {"kind": "charm", "name": "Spring Lily Charm", "material": "soft"}) == "charm" and \
        things.honest(cfg, {"kind": "charm", "name": "Wire Bead Spring", "material": "springy"}) == "spring", "the season's name is no spring; a thing called a spring is"
    print("machines check passed")


def main():
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(run(d))


if __name__ == "__main__":
    main()
