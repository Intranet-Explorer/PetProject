"""Which pictures go on which own sheet, and the ones that are computed instead of typed (walls, floors, light)."""
import colorsys, os, tomllib
from PIL import Image
import art
from build import ASSETS, Sheet, pic, rgba

OUT = rgba(art.PAL["#"])


def rows_with(rows, changes):
    """The same picture with some rows replaced: {row number: new row}."""
    return [changes.get(i, r) for i, r in enumerate(rows)]


def outlined(points, size=(16, 16), fill="ffffff"):
    """Loose pixels (letters, dust) with the pack's dark line drawn round them."""
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    pts = set(points)
    for (x, y) in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (x + dx, y + dy) not in pts and 0 <= x + dx < size[0] and 0 <= y + dy < size[1]:
                    im.putpixel((x + dx, y + dy), OUT)
    for p in pts:
        im.putpixel(p, rgba(fill))
    return im


def glyph(rows, ox, oy):
    return [(ox + x, oy + y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch != "."]


# ---- made things ----

def kinds():
    s = Sheet("kinds.png", 8)
    later = ("rope", "carver", "trowel", "hammer")   # drawn after the egg had its place: they go behind it, so nothing moves
    for name, rows in art.KINDS.items():
        extra = {"anchor": [0, 24]} if name in ("shelf", "mirror", "picture", "wall hook") else {}   # these hang on the wall above their tile
        if name not in later:
            s.add("kind." + name, pic(rows), tint="hue", **extra)
    egg = pic(art.EGG)
    lean = Image.new("RGBA", egg.size, (0, 0, 0, 0))   # the second frame: the egg rocks to one side
    for y in range(16):
        lean.paste(egg.crop((0, y, 16, y + 1)), (1 if y < 7 else -1 if y > 11 else 0, y))
    s.strip("egg", [egg, lean], tint="hue", anims={"idle": {"frames": [[0, 0]], "fps": 1}, "rock": {"frames": [[0, 0], [1, 0]], "fps": 3}})
    for name in later:
        s.add("kind." + name, pic(art.KINDS[name]), tint="hue")
    # a pot with something planted in it is drawn without the plant it is typed with: plant.* (bits.png) goes on it instead
    s.add("kind.plant pot.bare", pic(rows_with(art.KINDS["plant pot"], {y: "." * 16 for y in range(8)})), tint="hue")
    return s


# ---- fixtures, scenery, doors ----

UNLIT = {"lamp": {"Y": "a", "y": "A", "w": "c"}, "work lamp": {"Y": "E", "w": "t"}, "lantern": {"Y": "i", "w": "I"},
         "old lantern": {"k": "B", "Y": "e", "w": "E"}, "dial box": {"Y": "i", "w": "I"}, "little radio": {"Y": "B", "w": "b"}}
WALL_HUNG = {"lantern": 26, "old lantern": 26, "window": 28, "mirror": 28, "skylight": 30}   # how far above its tile's top edge the picture's top is


def fixtures():
    s = Sheet("fixtures.png", 16)
    F = art.FIX

    def put(name, rows, swap=None, key=None):
        key = key or name.split(".")[0]
        s.add("fix." + name, pic(rows, swap), **({"anchor": [0, WALL_HUNG[key]]} if key in WALL_HUNG else {}))

    for lamp in ("lamp", "work lamp", "lantern", "dial box"):   # the bare name is the unlit one
        put(lamp, F[lamp], UNLIT[lamp]); put(lamp + ".off", F[lamp], UNLIT[lamp]); put(lamp + ".on", F[lamp])
    put("old lantern", F["lantern"], UNLIT["old lantern"]); put("old lantern.off", F["lantern"], UNLIT["old lantern"])
    put("old lantern.on", F["lantern"], {"k": "B"})
    for name in ("bowl.full", "bowl.half", "bowl.empty", "ball", "blanket", "music box.silent", "music box.playing", "window", "window.open",
                 "mirror", "bird bath", "old rug", "skylight", "rocking chair", "drum", "chimes", "pond", "heavy book", "rock"):
        put(name, F[name])
    put("bowl", F["bowl.full"]); put("music box", F["music box.silent"]); put("window.closed", F["window"])
    s.add("fix.hot pipe", pic(F["hot pipe"]), anchor=[0, 16])   # three tiles tall, its tile in the middle
    for st, swap in (("", {"x": "G"}), (".growing", {"x": "G"}), (".ripe", None)):
        put("berry bush" + st, F["berry bush"], swap)
    s.add("stone", pic(F["stone"]))   # a memorial: a headstone with a flower at its foot
    put("bean row", F["bean row.growing"]); put("bean row.growing", F["bean row.growing"]); put("bean row.ripe", F["bean row"])
    put("tomato vine", F["tomato vine"], {"x": "G"}); put("tomato vine.growing", F["tomato vine"], {"x": "G"}); put("tomato vine.ripe", F["tomato vine"])
    put("melon bed", F["melon bed"], {"h": "G", "Y": "H"}); put("melon bed.growing", F["melon bed"], {"h": "G", "Y": "H"}); put("melon bed.ripe", F["melon bed"])

    shaft = Image.new("RGBA", (24, 59), (0, 0, 0, 0))   # sun from the skylight: a slanting beam down to a soft pool on the floor. Light, not a thing
    light = {}
    for y in range(48):   # the beam, fainter the higher it goes
        cx = 13 - (47 - y) // 9
        for x in range(cx - (5 if y > 30 else 4), cx + (5 if y > 30 else 4) + 1):
            light[(x, y)] = (24, 36, 50, 66, 84)[min(4, y // 10)]
    for y in range(44, 59):   # the pool
        for x in range(24):
            d = ((x - 11.5) / 11) ** 2 + ((y - 51) / 6.5) ** 2
            if d < 1:
                light[(x, y)] = max(light.get((x, y), 0), 175 if d < 0.4 else 120)
    for xy, a in light.items():
        shaft.putpixel(xy, rgba("ffe18d", a))
    for xy in ((9, 14), (13, 25), (10, 33), (14, 40)):   # dust in the beam
        shaft.putpixel(xy, rgba("ffffff", 200))
    s.add("fix.sun shaft", shaft, anchor=[4, 43])

    for name in ("cobweb", "blocks", "harp", "gong", "stepping stone"):   # a cobweb goes on the top wall row, just under the wall's cap
        s.add("decor." + name, pic(art.DECOR[name]), **({"anchor": [0, -4]} if name == "cobweb" else {}))
    s.add("decor.cobweb.right", pic(art.DECOR["cobweb"]).transpose(Image.FLIP_LEFT_RIGHT), anchor=[0, -4])
    for n, (phase, leaves) in enumerate(((0, (3, 9, 15, 21, 26)), (2, (5, 12, 18, 24)))):   # vines up the greenhouse frames
        stem = [(7 + (1 if (y + phase) % 8 < 3 else -1 if (y + phase) % 8 in (4, 5, 6) else 0), y) for y in range(2, 32)]
        leaf = [(x + dx * side, y + dy) for i, y in enumerate(leaves) for side in ((1, -1)[(i + n) % 2],) for x in (stem[y - 2][0],) for dx, dy in ((1, 0), (2, 0), (3, 0), (2, -1), (3, -1), (2, 1))]
        im = outlined(stem + leaf, (16, 32), "74a334")
        for x, y in stem:
            im.putpixel((x, y), rgba("56864c"))
        for x, y in leaf[1::6]:
            im.putpixel((x, y), rgba("adbc3a"))
        s.add("decor.vine.%d" % (n + 1), im)

    roof = Image.new("RGBA", (56, 28), (0, 0, 0, 0))   # the attic: the roof comes down into both top corners of the end wall
    for x in range(56):
        for y in range(28):
            t = x / 56 + y / 28
            if t < 1:
                edge = 1 - t
                roof.putpixel((x, y), OUT if edge < 0.05 else rgba("a3754e") if edge < 0.13 else OUT if edge < 0.16 else rgba("4e484a" if (x + 2 * y) % 12 == 0 else "695953"))
    s.add("decor.roof.left", roof, anchor=[0, 16]); s.add("decor.roof.right", roof.transpose(Image.FLIP_LEFT_RIGHT), anchor=[40, 16])

    # doors: one picture per wall and state; the anchor puts each in the wall beside its door tile
    D = art.DOOR
    board = "#TTTTTTTTTTTTTT#"
    north = {"shut": D["north"],
             "open": [r[:3] + "".join("#" if c in "bBY" else c for c in r[3:13]) + r[13:] for r in D["north"][:17]] + [r[:3] + "kkkkkkkkkk" + r[13:] for r in D["north"][17:]],
             "stuck": rows_with(D["north"], {6: board, 7: board, 13: board, 14: board})}
    south = {"shut": D["south"], "open": rows_with(D["south"], {i: "#o#kkkkkkkkkk#o#" if i < 3 else "#o#mmmmmmmmmm#o#" for i in range(1, 8)}),
             "stuck": rows_with(D["south"], {i: "#o#TTTTTTTTTT#o#" for i in (3, 4)})}
    west = {"shut": D["west"], "open": rows_with(D["west"], {i: "mmmmmmkkk" for i in range(3, 13)}),
            "stuck": rows_with(D["west"], {i: "#TTTTTTT#" for i in (5, 6, 10, 11)})}
    gate = {"shut": D["gate"], "open": rows_with(D["gate"], {i: "#b#..........#b#" for i in range(2, 14)}),
            "stuck": rows_with(D["gate"], {5: "#b#G#o#oo#o#o#b#", 6: "#b#GG##oo#o#G#b#", 7: "#b#oGG#oo#GGo#b#", 8: "#b#o#GGooGG#o#b#", 9: "#b#o#oGGGG#o##b#", 10: "#b#o#o#GG#o#o#b#"})}
    side_gate = {st: [r.replace("m", ".").replace("k", ".").replace("o", "b") for r in west[st]] for st in west}

    def unknown(rows, x, y):
        """A door nobody has been through yet: the shut door, darker, with a small question mark at (x, y)."""
        dark = [r.translate(str.maketrans("bBYon", "KkkEe")) for r in rows]
        for dy, mark in enumerate(("vvv", "..v", ".v.", "...", ".v.")):
            dark[y + dy] = dark[y + dy][:x] + "".join(m if m != "." else c for m, c in zip(mark, dark[y + dy][x:])) + dark[y + dy][x + 3:]
        return dark
    north["unknown"], south["unknown"], west["unknown"] = unknown(D["north"], 6, 7), unknown(D["south"], 6, 2), unknown(D["west"], 3, 5)
    gate["unknown"] = unknown(D["gate"], 6, 5)
    side_gate["unknown"] = west["unknown"]
    for st in ("shut", "open", "stuck", "unknown"):
        n, so, w = pic(north[st]), pic(south[st]), pic(west[st])
        s.add("door.north." + st, n, anchor=[0, 20]); s.add("door.south." + st, so, anchor=[0, -16])
        s.add("door.west." + st, w, anchor=[9, 0]); s.add("door.east." + st, w.transpose(Image.FLIP_LEFT_RIGHT), anchor=[-16, 0])
        g, sg = pic(gate[st]), pic(side_gate[st])
        s.add("door.gate.north." + st, g, anchor=[0, 16]); s.add("door.gate.south." + st, g, anchor=[0, -16])
        s.add("door.gate.west." + st, sg, anchor=[9, 0]); s.add("door.gate.east." + st, sg.transpose(Image.FLIP_LEFT_RIGHT), anchor=[-16, 0])
        s.add("door." + st, n, anchor=[0, 20])
    for st, swap in (("", UNLIT["little radio"]), (".off", UNLIT["little radio"]), (".on", None)):   # the visitor's own, set down on the floor (SPEC-v3.3 §3.2)
        put("little radio" + st, F["little radio"], swap)
    put("instrument shelf", F["instrument shelf"])   # the pack's shelf, with a drum and two bells left on it and the top shelf free
    return s


# A bit a room grows is drawn on what it grows on (SPEC-v3.4 §5): petals on a flower, feathers in a nest.
# bit: (the source picked bare, the source it is on when it is there, where the bit's own picture goes on that).
# The sources are art.GROWS; several bits may share one. (Leaf and wood grow on pictures of the pack: sprites.json.)
GROWN = {
    "petal": ("flower.bare", "flower", []), "wax": ("candle.bare", "candle", []),
    "fluff": ("twig", "twig", [(0, 1), (6, 3)]), "vine": ("stake", "stake", [(2, 2), (3, 7)]),
    "pebble": ("gravel", "gravel", [(0, 9), (7, 9), (3, 6)]), "metal": ("gravel", "gravel", [(0, 8), (6, 8), (3, 4)]),
    "seed": ("seedhead", "seedhead", [(4, 1)]), "reed": ("reeds", "reeds", [(2, 1), (7, 3)]),
    "clay": ("bank", "bank", [(1, 5), (7, 7)]), "moss": ("stone", "stone", [(1, 5), (6, 8)]), "soot": ("pan", "pan", [(3, 3)]),
    "feather": ("nest", "nest", [(1, 2), (6, 3)]), "resin": ("stump", "stump", [(2, 7), (9, 6)]),
    "cloth": ("bench", "bench", [(2, 5), (3, 1)]), "felt": ("bench", "bench", [(3, 5), (2, 1)]),
    "shell": ("sand", "sand", [(0, 5), (6, 8)]), "bead": ("clam", "clam.open", [(5, 6)]),
    "wire": ("spindle", "spindle", [(3, 6), (3, 2)]), "string": ("spindle", "spindle", [(3, 7), (4, 2)]),
    "bell": ("stand", "stand", [(0, 3), (8, 3)]),
}


def source(name):
    """A picture of art.GROWS with the pack's dark line drawn round it (sand lies flat: it has none)."""
    im = pic(art.GROWS[name])
    if name == "sand":
        return im
    out = im.copy()
    for x in range(16):
        for y in range(16):
            if not im.getpixel((x, y))[3] and any(0 <= x + dx < 16 and 0 <= y + dy < 16 and im.getpixel((x + dx, y + dy))[3] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), OUT)
    return out


def materials():
    """What the processes give (crafting.toml, [material.<name>]): each names the bit it is `like` and a `tint`."""
    with open(os.path.join(os.path.dirname(os.path.dirname(ASSETS)), "crafting.toml"), "rb") as f:
        return tomllib.load(f).get("material", {})


def recoloured(im, tint):
    """A picture in another colour: the tint's hue and saturation, and its lightness for the picture's middle tone, so
    the shading stays. The dark line is left alone."""
    th, tl, ts = colorsys.rgb_to_hls(*(v / 255 for v in rgba(tint.lstrip("#"))[:3]))
    px = [(xy, colorsys.rgb_to_hls(*(v / 255 for v in im.getpixel(xy)[:3]))[1]) for xy in ((x, y) for y in range(im.size[1]) for x in range(im.size[0]))
          if im.getpixel(xy)[3] and im.getpixel(xy) != OUT]
    mid = sum(l for _, l in px) / max(1, len(px))
    out = im.copy()
    for xy, l in px:
        out.putpixel(xy, tuple(round(v * 255) for v in colorsys.hls_to_rgb(th, max(0.1, min(0.97, tl + (l - mid))), ts)) + (255,))
    return out


def bits():
    s = Sheet("bits.png", 8)
    made = materials()
    for name, rows in art.BITS.items():
        if name not in made:
            s.add("bit." + name, pic(rows))
    for name, (bare, base, at) in GROWN.items():
        im, bit = source(base), pic(art.BITS[name])
        bit = bit.crop(bit.getbbox())
        for x, y in at:
            assert x + bit.size[0] <= 16 and y + bit.size[1] <= 16, "the %s at %s does not fit on its %s" % (name, (x, y), base)
            im.alpha_composite(bit, (x, y))
        s.add("grows." + name, im)
        s.add("grows.%s.bare" % name, source(bare))
    for name, rows in art.PLANT.items():   # something growing, to go over the pot or bed it is planted in
        s.add("plant." + name, pic(rows))
    # Last, because crafting.toml may grow: a material's own picture if art.BITS has one, or else the bit it is like, tinted.
    for name, m in made.items():
        if m.get("sheet"):   # (drawn on a sheet of its own: SPEC-v3.5 §4.3, machine.py)
            continue
        assert name in art.BITS or m.get("like") in art.BITS, "the material %r is like %r, which art.BITS has no picture of" % (name, m.get("like"))
        s.add("bit." + name, pic(art.BITS[name]) if name in art.BITS else recoloured(pic(art.BITS[m["like"]]), m["tint"]))
    return s


def creatures():
    """A moth and a beetle, seen from above. Drawn facing up; the other three ways are the same picture turned."""
    s = Sheet("creatures.png", 4)
    for kind, fps in (("moth", 10), ("beetle", 6)):
        a, b = pic(art.CRE[kind + ".a"]), pic(art.CRE[kind + ".b"])
        block = Image.new("RGBA", (32, 64), (0, 0, 0, 0))
        for row, turn in enumerate((None, Image.ROTATE_270, Image.ROTATE_180, Image.ROTATE_90)):   # up, right, down, left
            for col, f in enumerate((a, b)):
                block.paste(f.transpose(turn) if turn is not None else f, (col * 16, row * 16))
        anims = {"idle": {"frames": [[0, 2], [1, 2]] if kind == "moth" else [[0, 2]], "fps": fps if kind == "moth" else 1}}
        for row, way in enumerate(("up", "right", "down", "left")):
            anims["walk." + way] = {"frames": [[0, row], [1, row]], "fps": fps}
        s.add("creature." + kind, block, frame=[16, 16], anims=anims)
    return s


def fx():
    s = Sheet("fx.png", 8)
    for n in ("1", "2", "3"):
        s.add("fx.note." + n, pic(art.FX["note" + n]))
    s.add("fx.note", pic(art.FX["note1"]))
    z1, z2, z3 = glyph(["wwww", "..w.", ".w..", "wwww"], 2, 10), glyph(["wwwww", "...w.", "..w..", ".w...", "wwwww"], 6, 5), glyph(["wwwwww", "....w.", "...w..", "..w...", "wwwwww"], 9, 0)
    s.strip("fx.zzz", [outlined(z1), outlined(z1 + z2), outlined(z1 + z2 + z3)], anims={"rise": {"frames": [[0, 0], [1, 0], [2, 0], [2, 0]], "fps": 2}})
    s.strip("fx.drip", [pic(art.FX["drip%d" % i]) for i in (1, 2, 3)], anims={"fall": {"frames": [[0, 0], [1, 0], [2, 0]], "fps": 6}})
    dust = [[(6, 11), (7, 11), (8, 10), (9, 11), (7, 9), (8, 12)], [(4, 10), (6, 8), (9, 7), (11, 10), (7, 11), (10, 12), (5, 12)], [(3, 8), (6, 5), (10, 5), (12, 8), (8, 9)]]
    frames = []
    for i, pts in enumerate(dust):
        im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        for p in pts:
            im.putpixel(p, rgba("f2eaf1", (255, 210, 130)[i]))
            if i < 2:
                im.putpixel((p[0], p[1] + 1), rgba("abc2bc", (200, 120)[i]))
        frames.append(im)
    s.strip("fx.chalk dust", frames, anims={"puff": {"frames": [[0, 0], [1, 0], [2, 0]], "fps": 6}})
    glow = Image.new("RGBA", (32, 32), (0, 0, 0, 0))   # light in three flat rings, so it stays pixel art
    for y in range(32):
        for x in range(32):
            d = ((x - 15.5) ** 2 + (y - 15.5) ** 2) ** 0.5
            if d < 15:
                glow.putpixel((x, y), rgba("ffe18d", 130 if d < 6 else 80 if d < 10.5 else 40))
    s.add("fx.glow", glow, anchor=[8, 8])
    # Two bursts (SPEC-v3.4 §5): a pet got what it wanted (warm gold); a pet found something out (white-hot, with sparks of teal).
    gold = lambda d: "ffffff" if d < 2 else "ffe18d" if d < 5 else "f1c471"
    hot = lambda d: "ffffff" if d < 3 else "ffe18d" if d < 6 else TEAL
    play = lambda n: {"play": {"frames": [[i, 0] for i in range(n)], "fps": 10}}
    want = [burst((0, 3), (0, 0), gold), burst((0, 6), (1, 4), gold), burst((3, 7), (2, 5), gold), burst((5, 7), (4, 6), gold)]
    s.strip("fx.burst.want", want, anims=play(4))
    find = [burst((0, 4), (0, 2), hot), burst((0, 7), (0, 5), hot, [(3, 5), (11, 4), (4, 11), (12, 10)]),
            burst((2, 7), (2, 6), hot, [(2, 4), (12, 3), (3, 12), (13, 11)]), burst((5, 7), (4, 6), hot, [(1, 3), (13, 2), (2, 13), (14, 12), (5, 5), (10, 10)])]
    s.strip("fx.burst.find", find, anims=play(4))
    return s


TEAL = "8feff1"


def burst(straight, slant, tone, sparks=()):
    """One frame of a star-burst about the middle of 16 x 16: four straight rays two pixels thick and four slanting
    ones, each (from, to) in pixels out from the middle; `tone(d)` is the colour that far out. `sparks` are loose
    pixels of teal. A darker line of its own colour goes round it, so it shows on a pale floor as well as a dark one."""
    lit = {}
    for d in range(*straight):
        for a in (7, 8):
            for xy in ((a, 7 - d), (a, 8 + d), (7 - d, a), (8 + d, a)):
                lit[xy] = tone(d)
    for d in range(*slant):
        for xy in ((7 - d, 7 - d), (8 + d, 7 - d), (7 - d, 8 + d), (8 + d, 8 + d)):
            lit[xy] = tone(d + 1)
    lit.update({xy: TEAL for xy in sparks})
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for (x, y), c in sorted(lit.items(), key=lambda p: p[1] != TEAL):   # the warm line last: it wins where the two meet
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in lit and 0 <= x + dx < 16 and 0 <= y + dy < 16:
                im.putpixel((x + dx, y + dy), rgba("2d697b" if c == TEAL else "d78b4a"))
    for xy, c in lit.items():
        im.putpixel(xy, rgba(c))
    return im


def ui():
    s = Sheet("ui.png", 8)
    s.add("ui.bubble.think", pic(art.UI["think"]), slice=[5, 5, 5, 6])
    s.add("ui.bubble.think.tail", pic(art.UI["think.tail"]))
    s.add("ui.bubble.say.tail", pic(art.UI["say.tail"]))
    for name, sign in art.MOOD.items():   # the five moods: a bold sign on an outlined plate, readable at a glance by day and by night
        plate = [r for r in art.UI["mood"]]
        for dy, row in enumerate(sign):
            plate[2 + dy] = plate[2 + dy][:3] + "".join(m if m != "." else c for m, c in zip(row, plate[2 + dy][3:13])) + plate[2 + dy][13:]
        s.add("emote." + name, pic(plate), anchor=[0, -1])
    for name, rows in art.EMOTE.items():
        s.add("emote." + name, pic(rows))
    for name, rows in art.ICON.items():
        s.add("icon.room." + name, pic(rows))
    for name, sign in art.ACT.items():   # what a pet's body is doing: a sign on a small white plate, the same plate for all, to go over its head
        assert all(len(r) == 10 for r in sign) and len(sign) == 10 and sign[0][0] + sign[0][9] + sign[9][0] + sign[9][9] == "....", "the sign %r is 10 x 10 with empty corners" % name
        plate = [r if not 1 <= y <= 10 else r[0] + "".join(m if m != "." else c for m, c in zip(sign[y - 1], r[1:11])) + r[11] for y, r in enumerate(art.UI["act"])]
        s.add("icon.act." + name, pic(plate), anchor=[-2, -2])
    return s


# ---- walls and floors ----
# A room's north wall is two tiles high: a strip of its top, seen from above, then its face. The side and south
# walls show only their tops. `face(x, y)` gives the colour of the face at a pixel (y from 5 to 26).

def bricks(brick, light, mortar, wide=8, high=6):
    def f(x, y):
        course, r = (y - 5) // high, (y - 5) % high
        if r == high - 1 or (x + (0 if course % 2 == 0 else wide // 2)) % wide == wide - 1:
            return mortar
        return light if r == 0 else brick
    return f


def planks(board, joint, grain, wide=8):
    return lambda x, y: joint if x % wide == wide - 1 else grain if (x * 7 + y * 3) % 29 == 0 else board


def panes(sky, glint, frame, top, mid, bottom, green=None):
    hill = [22, 21, 21, 20, 20, 20, 21, 22, 23, 23, 22, 21, 21, 22, 23, 23]
    def f(x, y):
        if x in (0, 15) or y in (top, top + 1, mid, mid + 1) or y >= bottom:
            return frame
        if green and y >= hill[x]:
            return green[1] if y >= hill[x] + 3 else green[0]
        return glint if (x + y) % 11 == 0 or (x + y) % 11 == 1 and y % 2 else sky
    return f


def stone_window(x, y):
    if y < 9 or y > 24:
        return bricks("abc2bc", "f2eaf1", "8d977f", 8, 5)(x, y)
    if x in (0, 15) or y in (9, 24) or y == 17:
        return "5f7160"
    return "f2eaf1" if (x + y) % 11 == 0 else "b8dce5" if y < 21 - (x % 5 == 2) else "8feff1"


WALLS = {   # style: cap, line under the cap, trim, face, baseboard, line over the baseboard
    "plaster": ("ffcba9", "d3865f", "ffffff", lambda x, y: "ffcb8d" if (x, y) in ((3, 10), (11, 16), (6, 22)) else "fce2ca", "d78b4a", "965340"),
    "paper": ("ffcba9", "d3865f", "ffe18d", lambda x, y: "8f3e56" if x % 4 == 0 else "a5608b", "543c52", "3b3643"),
    "stone": ("8d977f", "5f7160", "8d977f", bricks("5f7160", "8d977f", "345a52"), "345a52", "141b1b"),
    "wood": ("c8966b", "90775e", "d2b37d", planks("b3957f", "816855", "90775e"), "816855", "695953"),
    "attic": ("c8966b", "90775e", "d2b37d", lambda x, y: "141b1b" if y in (7, 12) else ("a3754e" if y == 8 else "816855") if 7 < y < 12 else planks("b3957f", "816855", "90775e")(x, y), "816855", "695953"),
    "panel": ("ffbc75", "d78b4a", "ffffff", lambda x, y: ("965340" if y == 18 else "ffad5d" if y == 19 else "a3754e" if x % 4 == 3 else "d78b4a") if y >= 18 else "eecf9b", "a3754e", "965340"),
    "dark": ("816855", "4e484a", "816855", planks("695953", "4e484a", "4e484a"), "4e484a", "3b3643"),
    "glass": ("f2eaf1", "abc2bc", "f2eaf1", panes("b8dce5", "f2eaf1", "f2eaf1", 5, 16, 27, ("adbc3a", "74a334")), "abc2bc", "f2eaf1"),
    "conservatory": ("abc2bc", "8d977f", "f2eaf1", stone_window, "8d977f", "5f7160"),
}


def wall_set(style, outside="141b1b"):
    """The nine wall tiles of a style. The side and south walls are half a tile thick; beyond them is `outside`
    (None: nothing is drawn there, so the floor grid shows: a greenhouse stands in grass)."""
    cap, line, trim, face, base, baseline = WALLS[style]
    col = Image.new("RGBA", (16, 32))
    for x in range(16):
        for y in range(32):
            c = cap if y < 2 else line if y == 2 else "141b1b" if y in (3, 31) else trim if y == 4 else baseline if y == 27 else base if y > 27 else face(x, y)
            col.putpixel((x, y), rgba(c))
    def top(rule):
        im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        for x in range(16):
            for y in range(16):
                c = {"o": "141b1b", "l": line, "c": cap, "v": outside}[rule(x, y)]
                if c:
                    im.putpixel((x, y), rgba(c))
        return im
    w = top(lambda x, y: "v" if x < 7 else "o" if x in (7, 15) else "l" if x >= 13 else "c")
    s = top(lambda x, y: "v" if y > 8 else "o" if y in (0, 8) else "l" if y <= 2 else "c")
    nw = top(lambda x, y: "v" if x < 7 else "o" if x == 7 or x == 15 and y >= 3 else "l" if x >= 13 and y >= 2 else "c")
    sw = top(lambda x, y: "v" if x < 7 or y > 8 else "o" if x == 7 or y == 8 or (x == 15 and y == 0) else "l" if x >= 13 and y <= 2 else "c")
    flip = lambda im: im.transpose(Image.FLIP_LEFT_RIGHT)
    return {"n0": col.crop((0, 0, 16, 16)), "n1": col.crop((0, 16, 16, 32)), "w": w, "e": flip(w), "s": s, "nw": nw, "ne": flip(nw), "sw": sw, "se": flip(sw)}


def pond_tile(land, corner=None):
    """One tile of still water with a stone rim wherever `land` (some of "nesw") is beside it; `corner` ("ne", "sw" ...)
    puts a rim in that corner alone, where only the tile diagonally across is land."""
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for x in range(16):
        for y in range(16):
            side = {"n": y, "s": 15 - y, "w": x, "e": 15 - x}
            d = min([side[k] for k in land] + [99])
            for a, b in ("nw", "ne", "sw", "se"):   # two banks meeting: a rounded corner
                if a in land and b in land and side[a] < 5 and side[b] < 5:
                    d = 5 - ((5 - side[a]) ** 2 + (5 - side[b]) ** 2) ** 0.5
            if corner:
                d = min(d, (side[corner[0]] ** 2 + side[corner[1]] ** 2) ** 0.5 - 1.5)
            if d < 0:
                continue
            c = "141b1b" if d < 1 else "abc2bc" if d < 2 else "8d977f" if d < 3 else "2d697b" if d < 4 else "8feff1" if (x * 5 + y * 3) % 17 < 2 and y % 3 == 0 else "71ddee"
            im.putpixel((x, y), rgba(c))
    return im


def boards(board, line, knot):
    im = Image.new("RGBA", (16, 16), rgba(board))
    for y in (3, 7, 11, 15):
        for x in range(16):
            im.putpixel((x, y), rgba(line))
    for x, y in ((5, 0), (12, 4), (2, 8), (9, 12)):
        for d in range(3):
            im.putpixel((x, y + d), rgba(line))
    for x, y in ((10, 1), (3, 5), (13, 9), (6, 13)):
        im.putpixel((x, y), rgba(knot)); im.putpixel((x + 1, y), rgba(knot))
    return im


def tiles():
    s = Sheet("tiles.png", 9)
    for style in WALLS:
        for part, im in wall_set(style, None).items():   # nothing is painted beyond the walls: the page shows through, in either theme
            s.add("tile.wall.%s.%s" % (style, part), im)
    s.add("tile.floor.boards.old", boards("d2b37d", "b3957f", "c8966b"))
    s.add("tile.floor.boards.dark", boards("816855", "695953", "90775e"))
    sky = Image.new("RGBA", (16, 16), rgba("b8dce5"))
    s.add("tile.sky", sky)
    wisp = sky.copy()
    for x, y in [(x, 6) for x in range(3, 12)] + [(x, 7) for x in range(1, 14)] + [(x, 5) for x in range(6, 10)]:
        wisp.putpixel((x, y), rgba("f2eaf1"))
    s.add("tile.sky.cloud", wisp)
    hedge = sky.copy()
    bump = [7, 6, 6, 5, 5, 6, 7, 7, 6, 5, 5, 5, 6, 6, 7, 8]
    for x in range(16):
        for y in range(bump[x], 16):
            hedge.putpixel((x, y), OUT if y == bump[x] else rgba("74a334" if y < bump[x] + 3 else "56864c"))
    s.add("tile.sky.hedge", hedge)
    for land in ("", "n", "e", "s", "w", "ne", "es", "sw", "nw", "ns", "ew", "nes", "esw", "nsw", "new", "nesw"):
        s.add("tile.pond." + (land or "c"), pond_tile(land))
    for corner in ("ne", "se", "sw", "nw"):
        s.add("tile.pond.c." + corner, pond_tile("", corner))
    return s


def sheets():
    return [kinds(), fixtures(), bits(), creatures(), fx(), ui(), tiles()]
