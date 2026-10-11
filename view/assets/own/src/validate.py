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
    if have(v.get("sprite", "")) is True and sprites[v["sprite"]].get("tint") != "hue":
        bad("kind %s: its sprite is not marked to be recoloured" % k)
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
for name in ("fix.dial box", "fix.dial box.on", "fix.dial box.off", "fix.heavy book", "egg", "stone", "crate", "door.open", "door.shut", "door.stuck",
             "ui.bubble.say", "ui.bubble.think", "ui.bubble.say.tail", "ui.bubble.think.tail", "ui.plate", "ui.panel", "icon.room.unknown",
             "fx.sparkle", "fx.puff", "fx.flash", "fx.heart", "fx.note", "fx.zzz", "fx.dust", "fx.glow", "fx.chalk dust", "fx.drip", "fx.rain", "fx.snow"):
    have(name)
for wall in DOORS:
    for state in ("open", "shut", "stuck"):
        have("door.%s.%s" % (wall, state))
for b in house["bits"]:
    have("bit." + b)
for c in house["creatures"]:
    if have("creature." + c) is True:
        for a in ("idle", "walk.up", "walk.down", "walk.left", "walk.right"):
            if a not in sprites["creature." + c].get("anims", {}):
                bad("creature.%s has no %r animation" % (c, a))
for mood in ("tired", "uneasy", "lonely", "bored", "content"):
    have("emote." + mood)

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
            if water != drawn:
                say("the pond is drawn on %s but the engine's water is %s" % (sorted(drawn), sorted(water)))
            taken |= water
    for name in L.get("fixtures", {}):
        if name not in [f["name"] for f in room["fixtures"]] + ["dial box", "heavy book"]:
            say("places %r, which this room does not have" % name)
    for d, t in DOORS.items():
        if t in taken:
            say("the %s door tile %s is not free" % (d, list(t)))
    free = {(x, y) for x in range(W) for y in range(H)} - taken
    seen, todo = {DOORS["north"]}, deque([DOORS["north"]])
    while todo:
        x, y = todo.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in free and n not in seen:
                seen.add(n)
                todo.append(n)
    for d, t in DOORS.items():
        if t not in seen:
            say("the %s door cannot be reached from the north door" % d)
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
                if s not in free or s in DOORS.values():
                    say("a %s spot at %s is not on a free tile" % (b, list(s)))
for path in (ASSETS / "rooms").glob("*.json"):
    if path.stem not in house["rooms"]:
        bad("rooms/%s is a layout for a room type that does not exist" % path.name)

# ---- sounds ----
for name in "pickup drop make unmake combine door step eat write book call heart radio arrival".split():
    if name not in sounds["sfx"]:
        bad("sounds.json has no sfx %r" % name)
for kind in house["rooms"]:
    if kind not in sounds["music"]:
        bad("sounds.json has no music for the %s" % kind)
for group, lo, hi in (("sfx", 0.15, 0.35), ("music", 0.05, 0.15)):
    for name, s in sounds[group].items():
        pack_file(s, "%s %s" % (group, name))
        if not lo <= s.get("gain", 0) <= hi:
            bad("%s %s: gain %s is outside %s to %s" % (group, name, s.get("gain"), lo, hi))

for name, pack in packs.items():   # a pack may bring a font for the page's headings
    if pack.get("font"):
        pack_file({"pack": name, "file": pack["font"]}, "the font of pack %s" % name)

# ---- nothing lies about unused ----
for pack in packs.values():
    if pack.get("local"):
        continue
    for path in (ASSETS / pack["dir"]).rglob("*"):
        if path.is_file() and path not in used and path.name not in ("LICENSE.txt", "CREDITS.md") and "src" not in path.relative_to(ASSETS).parts:
            bad("unused file %s" % path.relative_to(ASSETS))
    if pack["dir"].startswith("third_party") and not (ASSETS / pack["dir"] / "LICENSE.txt").is_file():
        bad("%s has no LICENSE.txt" % pack["dir"])
if not (ASSETS / "third_party" / "CREDITS.md").is_file():
    bad("third_party/CREDITS.md is missing")

print("\n".join(faults) if faults else "art data: %d sprites, %d kinds, %d layouts, %d sounds, %d files: all in order"
      % (len(sprites), len(kinds), len(list((ASSETS / "rooms").glob("*.json"))), len(sounds["sfx"]) + len(sounds["music"]), len(used)))
sys.exit(1 if faults else 0)
