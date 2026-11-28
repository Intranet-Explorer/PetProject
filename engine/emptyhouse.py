"""The empty house (v5.3.2, the brief of 4 November 2026, widened on 23 November to clearing everything): once,
on the first start with it on, the house is emptied of everything the hobs made, built or earned, so a family starts
again in a house that holds only what it was drawn with.

What goes: every made thing in every room and in a creature's hold (the train's cart, the sweepers), what lies in the
keepsake boxes included; everything the hobs built - what stands (`fix.built`: beds, benches, shelves, patches,
curtains, statues, the kiln, loom, millstone, forge and stove), what is under way (`site`) and what a v5.3 project
left standing (`fix.project5`); and every fixture the Works built for a room (lamps, rugs, shelves, the mirror), with
the Works' list begun again so the house can earn them back. What stays: the fixtures the house was drawn with
(house.toml), the machine and what the Works did for it, the screens and the heavy book, the radio, the lit sign, the
Works, the train with its platforms and track, the sweepers and their dock, the pond's dock, the stones with their
(empty) keepsake boxes and memory shelves, the walls' writing, bits lying about, and anything the visitor set down.
Nothing is lost to the record: the Things tab keeps a note of every made thing (things.gone), and the family pages,
the story and the copy of the data folder are untouched.

A made thing leaves by the house's own path (items.place, things.gone, works.fed), credited to the Works once: the
key of everything fed is kept in house["empty_house"]["fed"], and a key in it is never fed again. v5.3 projects under
way or blocked go back to planned (projects.state) with their steps undone. The machine is filled, and gives each hob
`free` things a world day for `free_days` world days whatever [trade] says (machine.free reads allowance).

Before any of it, the data folder is copied beside itself to <data>.bak-day<world day>-t<tick>; if that copy fails the
house is left exactly as it was and it is tried again at the next start. Switch: [empty_house] on (contracts.on53)."""
import logging
import shutil
from pathlib import Path

from . import contracts as K
from . import items, things
from .world import add_event, days as world_days, moment

OWNER = "visitor"   # (visitor.OWNER: what he set down is his, not the hobs')


def E(cfg):
    return cfg.get("empty_house") or {}


def on(cfg):
    return K.on53(cfg, "empty_house")


def hob_built(o):
    """A fixture the hobs built or are building: build.py's (standing or under way, statues too) and a v5.3 project's."""
    f = o.get("fix") or {}
    return "made" not in o and bool(f.get("built") or f.get("project5") or "site" in o)


def backup(data_dir, house):
    """The data folder copied beside itself. Returns the copy's path; raises if it cannot be made whole."""
    src = Path(data_dir)
    dst = src.parent / ("%s.bak-day%04d-t%d" % (src.name, house["clock"]["day"], house["tick"]))
    shutil.copytree(src, dst)   # (raises if dst is there already: a copy is never written over)
    if not (dst / "house.json").exists() and (src / "house.json").exists():
        raise OSError("the copy at %s has no house.json" % dst)
    return dst


def feed(house, cfg, S, o):
    """One made thing to the Works, once: a key already fed is never fed again."""
    from . import works
    k = str(works.key(o))
    if k in S["fed"]:
        return False
    S["fed"].append(k)
    works.fed(house, cfg, None, o)
    return True


def clear_made(house, cfg, S):
    n = 0
    for room in [r for r in house["rooms"].values() if r["type"]]:
        for name in sorted(things.made(room)):
            o = room["objects"][name]
            if o["made"].get("by") == OWNER:
                continue
            room["objects"].pop(name)
            items.place(house, cfg, room, name, o)
            things.gone(house, o, name, "cleared out when the house was emptied", room)
            feed(house, cfg, S, o)
            n += 1
    for cr in house.get("creatures") or []:   # (what rode in the train's cart or a sweeper when it happened; bits ride on)
        for x in list(cr.get("held") or []):
            o = x.get("o")
            if not o or "made" not in o or o["made"].get("by") == OWNER:
                continue
            cr["held"].remove(x)
            things.gone(house, o, x["name"], "cleared out when the house was emptied")
            feed(house, cfg, S, o)
            n += 1
    return n


def clear_built(house, cfg):
    out = []
    for room in [r for r in house["rooms"].values() if r["type"]]:
        for name in sorted(n for n, o in room["objects"].items() if hob_built(o)):
            drop(room, name)
            out.append("%s in %s" % (name, room["name"]))
    return out


def drop(room, name):
    """A fixture out of its room: an authored thing that stood on it stands on the floor now, and what the room grew
    for it and what was written on it go with it."""
    room["objects"].pop(name)
    for o in room["objects"].values():
        if o.get("on") == name:
            o.pop("on")
    room["spots"] = [s for s in room.get("spots", []) if s.get("built") != name]
    room["marks"] = [m for m in room.get("marks", []) if m.get("on") != name]


def clear_works(house, cfg):
    """What the Works built for a room: the fixture out of every room of its type and out of the house's list
    (works.lay put it there), and off the Works' own list of what it has built, which is begun again from the top with
    an empty meter: the house can earn each one back. What it did for the machine, the sweepers, the rail and the dock
    stay built."""
    from . import works
    S, out = works.state(house, cfg), []
    done = {b["what"] for b in S["built"]}
    for b in cfg["works"]["build"]:
        f = b.get("fixture")
        if not f or b["what"] not in done:
            continue
        fixtures = cfg["house"]["rooms"][f["room"]]["fixtures"]
        fixtures[:] = [x for x in fixtures if x["name"] != f["name"]]
        for room in [r for r in house["rooms"].values() if r["type"] == f["room"] and f["name"] in r["objects"]]:
            drop(room, f["name"])
        S["built"] = [x for x in S["built"] if x["what"] != b["what"]]
        out.append(b["what"])
    if out:
        S.update(goal=0, have=0, fed={})
        S.pop("front", None)
    return out


def reset_projects(house, cfg):
    """v5.3's projects under way or blocked: planned again, nothing gathered, their sites bare."""
    from . import projects
    n = 0
    for pr in projects.store(house).values():
        if pr.get("build"):   # (build.py's mirror of a thing that is gone now: projects.mirrors abandons it)
            continue
        if pr["state"] == "done" and pr.get("fixture"):
            pr["fixture"] = None
        if pr["state"] not in ("under way", "blocked"):
            continue
        for s in pr["steps"]:
            s.update(got=0, done=False, by=[])
        pr.update(stock={}, progress=0.0, steps_by={})
        projects.setbacks(house).pop(pr["id"], None)
        projects.state(house, pr, "planned")
        projects.restage(house, pr)
        n += 1
    return n


def migrate(house, cfg, data_dir, copy=backup):
    """Once a house (house["empty_house"]), from tick.alive_migration after clearout.migrate. Returns the report's
    lines, [] when it did not run."""
    if not on(cfg) or "empty_house" in house:
        return []
    try:
        kept = copy(data_dir, house)
    except Exception as e:   # (no copy, no clearing: the house is as it was, and the next start tries again)
        logging.error("the empty house: the data folder could not be copied (%s); nothing was cleared", e)
        return []
    from . import machine, works
    S = house["empty_house"] = {"at": house["tick"], "day": house["clock"]["day"], "backup": str(kept), "fed": [], "made": 0, "built": [], "works": []}
    before = len(works.state(house, cfg)["built"])
    S["made"] = clear_made(house, cfg, S)
    paid = [b["what"] for b in works.state(house, cfg)["built"][before:]]   # (what the scrap filled, before the Works' own list is begun again)
    S["built"] = clear_built(house, cfg)
    S["works"] = clear_works(house, cfg)
    S["projects"] = reset_projects(house, cfg)
    if K.on5(cfg, "items"):
        items.sync(house, cfg)
    if machine.found(house):
        for m in cfg["machine"]["materials"]:
            machine.fill(house, cfg, m, cfg["machine"]["limit"])
        machine.state(house, cfg)["used"] = house["tick"]
    moment(house, "tidy", "the house was emptied: %d made things, %d built things and %d of the Works' are gone, and the machine is full" % (S["made"], len(S["built"]), len(S["works"])), None, None)
    for p in house["pets"].values():
        if p["stage"] not in ("egg", "dead"):
            add_event(house, p, "the house has been emptied: everything anyone made or built is gone, the beds and the kiln too, and what the Works built for the rooms. "
                                "The machine is full, and for a few days it gives freely")
            p["news"].append("event")
    new = paid
    return ["made things cleared: %d (fed to the Works once each: %d)" % (S["made"], len(S["fed"])),
            "built things cleared: %d%s" % (len(S["built"]), ": " + ", ".join(S["built"]) if S["built"] else ""),
            "what the Works had built for the rooms, cleared and to be earned again: %d%s" % (len(S["works"]), ": " + ", ".join(S["works"]) if S["works"] else ""),
            "projects back to planned: %d" % S["projects"],
            "the machine: full; %d free a hob a world day for %d world days" % (E(cfg).get("free", 2), E(cfg).get("free_days", 7)),
            "the copy: %s" % kept] + ["the Works, fed the scrap, built: %s" % ", ".join(new)] * bool(new)


def allowance(house, cfg):
    """What the machine gives each hob free a world day while the emptied house finds its feet, or None: the
    configured value (machine.free)."""
    S = house.get("empty_house")
    if not S or not on(cfg) or world_days(cfg, S["at"], house["tick"]) >= E(cfg).get("free_days", 7):
        return None
    return E(cfg).get("free", 2)
