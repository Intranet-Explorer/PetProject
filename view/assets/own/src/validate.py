"""Checks the art data against itself and against the house. From the project folder:

  uv run python view/assets/own/src/validate.py

Prints every fault and exits 1 if there is one. Needs only Python 3.11+ (no Pillow)."""
import json, struct, sys, tomllib
from collections import deque
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2]
ROOT = ASSETS.parents[1]
faults = []
bad = faults.append
J = lambda name: json.loads((ASSETS / name).read_text())


def png_size(path):
    raw = path.read_bytes()[:24]
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", raw[16:24])


packs, sprites, kinds, sounds = J("packs.json"), J("sprites.json"), J("kinds.json"), J("sounds.json")
house = tomllib.loads((ROOT / "house.toml").read_text())
materials = [m for m, v in tomllib.loads((ROOT / "materials.toml").read_text()).items() if isinstance(v, dict) and "says" in v]
W, H = house["house"]["room_size"]
DOORS = {k: tuple(v) for k, v in house["house"]["doors"].items()}
used = set()


def pack_file(entry, what):
    pack = packs.get(entry.get("pack"))
    if not pack:
        return bad("%s: no pack %r" % (what, entry.get("pack")))
    path = ASSETS / pack["dir"] / entry["file"]
    if not path.is_file():
        return bad("%s: no file %s" % (what, path.relative_to(ASSETS)))
    used.add(path)
    return path


# ---- sprites: the file is there, the rectangle and every animation frame lie inside it ----
for name, s in sprites.items():
    path = pack_file(s, name)
    if not path:
        continue
    iw, ih = png_size(path)
    x, y, w, h = s["rect"]
    cells = [(0, 0)] + [tuple(f) for a in s.get("anims", {}).values() for f in a["frames"]]
    for cx, cy in cells:
        if x + cx * w < 0 or y + cy * h < 0 or x + (cx + 1) * w > iw or y + (cy + 1) * h > ih or w <= 0 or h <= 0:
            bad("%s: frame %s of rect %s reaches outside %s (%dx%d)" % (name, [cx, cy], s["rect"], s["file"], iw, ih))
    if "slice" in s and (s["slice"][0] + s["slice"][2] >= w or s["slice"][1] + s["slice"][3] >= h):
        bad("%s: its nine-slice margins leave no middle" % name)
    if packs[s["pack"]].get("local") and s.get("fallback") not in sprites:
        bad("%s: from a pack kept outside the repository, so it needs a fallback sprite" % name)
have = lambda n: n in sprites or bad("no sprite %r" % n)

# ---- the catalog of kinds ----
for k, v in kinds.items():
    if have(v.get("sprite", "")) is True and sprites[v["sprite"]].get("tint") not in ("hue", "none"):   # "none": a kind that keeps its own colours (SPEC-v3.6a §5)
        bad("kind %s: its sprite is not marked to be recoloured, or to keep its colours" % k)
    for key in ("rank", "wall", "not", "a"):
        if key not in v:
            bad("kind %s: no %r" % (k, key))
    for m in v.get("not", []):
        if m not in materials:
            bad("kind %s: %r is not a material" % (k, m))
for m in materials:
    n = sum(m not in v["not"] for v in kinds.values())
    if n < (1 if m == "sweet" else 3):
        bad("material %s can only be %d kinds" % (m, n))
for k in ("sculpture", "mobile"):
    if k not in kinds:
        bad("the catalog has no %s (what combining two different kinds gives)" % k)
parts = ASSETS / "kinds-from-parts.json"
if parts.exists():
    def named(x):
        return [x] if isinstance(x, str) else [k for v in (x.values() if isinstance(x, dict) else x if isinstance(x, list) else []) for k in named(v)]
    t = json.loads(parts.read_text())
    for k in set(named(t.get("shape")) + named(t.get("material")) + named(t.get("pair")) + [t.get("many", {}).get("then"), t.get("many", {}).get("else")]):
        if k and k not in kinds:
            bad("kinds-from-parts.json names the kind %r, which the catalog does not have" % k)

# ---- everything the house has: fixtures and their states, bits, small creatures, feelings ----
for name in ("fix.dial box", "fix.dial box.on", "fix.dial box.off", "fix.little radio", "fix.little radio.on", "fix.little radio.off", "fix.heavy book", "egg", "stone", "crate", "door.open", "door.shut", "door.stuck",
             "ui.bubble.say", "ui.bubble.think", "ui.bubble.say.tail", "ui.bubble.think.tail", "ui.plate", "ui.panel", "icon.room.unknown",
             "fx.sparkle", "fx.puff", "fx.flash", "fx.heart", "fx.note", "fx.zzz", "fx.dust", "fx.glow", "fx.chalk dust", "fx.drip", "fx.rain", "fx.snow",
             "fx.burst.want", "fx.burst.find"):
    have(name)
for wall in DOORS:
    for state in ("open", "shut", "stuck"):
        have("door.%s.%s" % (wall, state))
for b, v in house["bits"].items():
    have("bit." + b)
    if any(not v.get("late") if r["bits"] == "any" else b in r["bits"] for r in house["rooms"].values()):   # a room grows it: it is drawn on what it grows on
        have("grows." + b)
        have("grows.%s.bare" % b)
crafting = tomllib.loads((ROOT / "crafting.toml").read_text()) if (ROOT / "crafting.toml").exists() else {}   # SPEC-v3.4 §3
for m in crafting.get("material", {}):   # what a process gives is a bit like any other
    have("bit." + m)
for k in list(crafting.get("needs", {})) + list(crafting.get("tool", {})):
    if k not in kinds:
        bad("crafting.toml names the kind %r, which the catalog does not have" % k)
for stage in {st for g in crafting.get("grow", {}).values() for st in g.get("stages", [])} | ({"wilted"} if crafting.get("grow") else set()):
    have("plant." + stage)   # what is planted is drawn over its pot or bed, by how far it has grown
for c in house["creatures"]:
    if have("creature." + c) is True:
        for a in ("idle", "walk.up", "walk.down", "walk.left", "walk.right"):
            if a not in sprites["creature." + c].get("anims", {}):
                bad("creature.%s has no %r animation" % (c, a))
for mood in ("tired", "uneasy", "lonely", "bored", "content"):
    have("emote." + mood)
for a in tomllib.loads((ROOT / "activities.toml").read_text()).values():   # what a pet's body does by itself: a sign for each
    if isinstance(a, dict) and "icon" in a:
        have("icon.act." + a["icon"])
for sign in tomllib.loads((ROOT / "config.toml").read_text()).get("process_signs", {}).values():   # the sign over a hob trying a process
    have("icon.act." + sign)
# SPEC-v3.6b: each machine stands as fix.built.<it>; each dish the pot can hold has its picture
for key, p in tomllib.loads((ROOT / "building.toml").read_text()).get("project", {}).items():
    if p.get("machine"):
        have("fix.built." + key)
for d in (tomllib.loads((ROOT / "dishes.toml").read_text()) if (ROOT / "dishes.toml").exists() else {}).get("dish", {}):
    have("dish." + d)

# ---- room layouts ----
for kind, room in house["rooms"].items():
    have("icon.room." + kind)
    path = ASSETS / "rooms" / (kind + ".json")
    if not path.exists():
        bad("no layout for the %s" % kind)
        continue
    L = json.loads(path.read_text())
    say = lambda msg: bad("rooms/%s.json: %s" % (kind, msg))
    inside = lambda t: len(t) == 2 and 0 <= t[0] < W and 0 <= t[1] < H
    for g in ("floor", "walls"):
        if len(L[g]) != H + 3 or any(len(r) != W + 2 for r in L[g]):
            say("%s is not %d x %d" % (g, W + 2, H + 3))
        for n in {n for r in L[g] for n in r if n}:
            have(n)
    for d in L.get("decor", []):
        have(d["sprite"])
        if d.get("layer") not in ("floor", "wall", "top"):
            say("decor %s is on no known layer" % d["sprite"])
    taken = {tuple(b) for b in L.get("blocked", [])}
    for b in taken:
        if not inside(b):
            say("blocked tile %s is not on the floor" % list(b))
    for f in room["fixtures"]:
        name, at = f["name"], L.get("fixtures", {}).get(f["name"])
        states = ["on", "off"] if "light" in f else f.get("states", []) + (["growing", "ripe"] if f.get("plant") else [])
        for n in ["fix." + name] + ["fix.%s.%s" % (name, s) for s in states]:
            have(n)
        if name == "bowl":
            for s in ("full", "half", "empty"):
                have("fix.bowl." + s)
        if not at:
            say("the fixture %r is not placed" % name)
            continue
        have(at.get("sprite", ""))
        pos = tuple(at["pos"])
        if not inside(pos):
            say("%s stands off the floor at %s" % (name, list(pos)))
        if pos in taken:
            say("%s stands on a tile something else has: %s" % (name, list(pos)))
        taken.add(pos)   # also for what hangs on the wall ("wall": true): the engine still keeps its tile
        if f.get("window") and not L.get("light", {}).get("window"):
            say("it has a window but light.window is empty")
        if "water" in f:
            water = {tuple(t) for t in f["water"]}
            drawn = {(x - 1, y - 2) for y, r in enumerate(L["floor"]) for x, n in enumerate(r) if n and n.startswith("tile.pond")}
            if drawn and water != drawn:   # (SPEC-v3.6a: the view draws the pond's water from the snapshot; a floor that draws it too must agree)
                say("the pond is drawn on %s but the engine's water is %s" % (sorted(drawn), sorted(water)))
            taken |= water
    for name in L.get("fixtures", {}):
        if name not in [f["name"] for f in room["fixtures"]] + ["dial box", "heavy book"]:
            say("places %r, which this room does not have" % name)
    doors = {d: t for d, t in DOORS.items() if d in room.get("doors", DOORS)}   # (an outdoor room has its own few doors: SPEC-v3.6c §4)
    for d, t in doors.items():
        if t in taken:
            say("the %s door tile %s is not free" % (d, list(t)))
    free = {(x, y) for x in range(W) for y in range(H)} - taken
    start = next(iter(doors.values()))
    seen, todo = {start}, deque([start])
    while todo:
        x, y = todo.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in free and n not in seen:
                seen.add(n)
                todo.append(n)
    for d, t in doors.items():
        if t not in seen:
            say("the %s door cannot be reached from the %s door" % (d, next(iter(doors))))
    if free - seen:
        say("free tiles nobody can reach: %s" % sorted(free - seen))
    if len(free) < 60:
        say("only %d floor tiles can be walked on" % len(free))
    slots = L.get("wall_slots", [])
    if not 2 <= len(slots) <= 4 or any(s[1] != 0 or not inside(s) for s in slots):
        say("wall_slots should be 2 to 4 tiles in the row against the north wall")
    if isinstance(room["bits"], dict):
        for b, n in room["bits"].items():
            spots = [tuple(s) for s in L.get("bit_spots", {}).get(b, [])]
            if len(spots) < n:
                say("%d %s lie about at once but there are %d spots for them" % (n, b, len(spots)))
            for s in spots:
                if s not in free or s in doors.values():
                    say("a %s spot at %s is not on a free tile" % (b, list(s)))
for path in (ASSETS / "rooms").glob("*.json"):
    if path.stem not in house["rooms"]:
        bad("rooms/%s is a layout for a room type that does not exist" % path.name)

# ---- the seasons (SPEC-v3.5 §5): their own bits have pictures, and every stand-in in seasons.json is for a name that exists ----
turns = tomllib.loads((ROOT / "seasons.toml").read_text()) if (ROOT / "seasons.toml").exists() else {}
for b in turns.get("bit", {}):
    have("bit." + b)
for season, rooms in (J("seasons.json") if (ASSETS / "seasons.json").exists() else {}).items():
    if season not in house["seasons"]:
        bad("seasons.json: there is no season %r" % season)
    for kind, swaps in rooms.items():
        if kind != "*" and kind not in house["rooms"]:
            bad("seasons.json: there is no room type %r" % kind)
        for name, to in swaps.items():
            for n in [name] + (to if isinstance(to, list) else [to] if to else []):
                have(n)

# ---- sounds (AUDIO-BRIEF §4; README "sounds.json"): every file of audio/ is a sound of ours, every sound's file is there ----
AUDIO = ASSETS / sounds.get("dir", "audio")
wavs = {p.relative_to(AUDIO).as_posix() for p in AUDIO.rglob("*.wav")} if AUDIO.is_dir() else set()
credits = {f["file"] for f in json.loads((AUDIO / "credits.json").read_text())["files"]} if (AUDIO / "credits.json").is_file() else set()
if not wavs:
    bad("%s has no sound files: unzip the release asset pet-audio-v4.0.2.zip into it, or rebuild them with tools/audio/build_all.sh (RUNNING.md)" % AUDIO.relative_to(ROOT))
if not credits:
    bad("%s/credits.json is missing" % AUDIO.relative_to(ASSETS))
groups, mapped = sounds.get("groups", {}), set()
for name, e in sounds.get("sounds", {}).items():
    files = ["%s_%d.wav" % (name, i) for i in range(1, e["n"] + 1)] if e.get("n") else [name + ".wav"]
    mapped.update(files)
    if e.get("group") not in groups:
        bad("sounds.json: %s has no group of the groups (%r)" % (name, e.get("group")))
    for f in files:
        if wavs and f not in wavs:
            bad("sounds.json: %s has no file audio/%s" % (name, f))
        if credits and f not in credits:
            bad("audio/credits.json says nothing of %s" % f)
for f in sorted(wavs - mapped):
    bad("audio/%s is no sound of ours in sounds.json" % f)
for g, db in groups.items():
    if not isinstance(db, (int, float)) or not -40 <= db <= 6:
        bad("sounds.json: group %s has a level of %r dB" % (g, db))
for g, bus in sounds.get("buses", {}).items():
    if g not in groups or bus not in ("music", "ambience", "voices"):
        bad("sounds.json: buses: %s -> %r" % (g, bus))


def named(x, what):
    """Every name a table gives is a sound of ours."""
    if isinstance(x, str):
        if x not in sounds["sounds"]:
            bad("sounds.json: %s names %r, which is no sound of ours" % (what, x))
    elif isinstance(x, list):
        for y in x:
            named(y, what)
    elif isinstance(x, dict):
        for k, y in x.items():
            named(y, "%s.%s" % (what, k))


M, A = sounds.get("music", {}), sounds.get("ambience", {})
named({k: v for k, v in M.items() if k != "rooms"}, "music")
named({k: v for k, v in M.get("rooms", {}).items() if v}, "music.rooms")   # (null: a room with no theme of its own)
named(A.get("rooms", {}), "ambience.rooms")
named(A.get("weather", {}), "ambience.weather")
named(sounds.get("floors", {}), "floors")
named(sounds.get("on", {}), "on")
for kind in house["rooms"]:
    if not 1 <= len(A.get("rooms", {}).get(kind, [])) <= 2:
        bad("sounds.json: the %s needs its ambience (by day, and by night if it differs)" % kind)
for kind in list(M.get("rooms", {})) + A.get("outside", []) + A.get("open", []) + A.get("shut_in", []) + [k for k in sounds.get("floors", {}) if k not in ("default", "limp")]:
    if kind not in house["rooms"]:
        bad("sounds.json: there is no room type %r" % kind)
for l in [x for x in A.get("rooms", {}).values() for x in x] + [x for w in A.get("weather", {}).values() for x in w.get("in", []) + w.get("out", [])]:
    if not sounds["sounds"].get(l, {}).get("loop"):
        bad("sounds.json: the ambience %s does not loop" % l)
skies = {w for s in house["seasons"].values() for w in s["weather"]}
for w in ("rain", "storm"):
    if w not in A.get("weather", {}):
        bad("sounds.json has no ambience for %s" % w)
for w in A.get("weather", {}):
    if w not in skies:
        bad("sounds.json: ambience for the weather %r: there is no such weather" % w)
for mood in ("calm", "lively", "mysterious", "sad"):   # the visitor's music (SPEC-v3.3 §3.1)
    if not 2 <= len(M.get("visitor", {}).get(mood, [])) <= 4:
        bad("sounds.json has %d %s tracks for the visitor's music, not 2 to 4" % (len(M.get("visitor", {}).get(mood, [])), mood))
on = sounds.get("on", {})   # things that sound when used (SPEC-v3.3 §4), by kind, fixture or a part's sound
fixtures = {f["name"]: f for r in house["rooms"].values() for f in r["fixtures"]}
part_sounds = {p["sound"] for p in J("parts.json")["thing"].values() if p.get("sound")} if (ASSETS / "parts.json").exists() else set()   # SPEC-v3.5 §3.4: what an invented thing sounds like
for name in {"bell", "drum", "wind chime", "flute", "default"} | part_sounds | {n for n, f in fixtures.items() if f.get("loud")}:
    if "thing." + name not in on:
        bad("sounds.json: on has no thing.%s" % name)
for key in on:
    if key.startswith("thing.") and key[6:] not in kinds and key[6:] not in fixtures and key[6:] not in part_sounds and key[6:] != "default":
        bad("sounds.json: %s is neither a kind, a fixture nor a part's sound" % key)

for name, pack in packs.items():   # a pack may bring a font for the page's headings
    if pack.get("font"):
        pack_file({"pack": name, "file": pack["font"]}, "the font of pack %s" % name)

# ---- the parts library (SPEC-v3.5 §1; engine.check_parts looks at it closely): its pictures are in use ----
if (ASSETS / "parts.json").exists():
    lib = J("parts.json")
    used.update(ASSETS / x["file"] for p in lib["thing"].values() for x in p.get("px", {}).values())
    used.update([ASSETS / lib["body"]["file"]] if lib.get("body") else [])

# ---- nothing lies about unused ----
for pack in packs.values():
    if pack.get("local") or pack.get("skin"):   # (the page's skin: its style sheets and pages name its files, and its licences are its own)
        continue
    for path in (ASSETS / pack["dir"]).rglob("*"):
        if path.is_file() and path not in used and path.name not in ("LICENSE.txt", "CREDITS.md") and "src" not in path.relative_to(ASSETS).parts:
            bad("unused file %s" % path.relative_to(ASSETS))
    if pack["dir"].startswith("third_party") and not (ASSETS / pack["dir"] / "LICENSE.txt").is_file():
        bad("%s has no LICENSE.txt" % pack["dir"])
if not (ASSETS / "third_party" / "CREDITS.md").is_file():
    bad("third_party/CREDITS.md is missing")

print("\n".join(faults) if faults else "art data: %d sprites, %d kinds, %d layouts, %d sounds in %d sound files, %d files: all in order"
      % (len(sprites), len(kinds), len(list((ASSETS / "rooms").glob("*.json"))), len(sounds["sounds"]), len(wavs), len(used)))
sys.exit(1 if faults else 0)
