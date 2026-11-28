"""Outdoors (SPEC-v3.6c §4): the yard's and the meadow's fixtures and scenery, the weather lying on the ground, the
creatures outdoors, what is foraged there, the garden gate open and shut, the two Works goals that wanted art (the
weather vane, the fountain) and the map's two room icons, cut from PixelLab's outdoor32.png into own/outdoor.png.
Needs Python 3.11+ and Pillow. From this folder:

  python3 outdoor.py [PIXELLAB]   cuts own/outdoor.png (PIXELLAB: the folder holding outdoor32.png; by default
                                  ~/PetProject/assets-incoming/pixellab) and lays its entries into ../../sprites.json
                                  as one block, right after "icon.act.pot"

Names are in sheets.toml ([outdoor32]). Everything is drawn at the art's own size (a tree is about two tiles across),
its foot on the middle of its tile. The stream's water, the sky and hills behind, rain, puddles' rings, the grass in
the wind and the long evening shadows are drawn by the view (px/outdoors.ts, px/pond.ts)."""
import json, os, re, sys
from PIL import Image
from build import ASSETS

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/PetProject/assets-incoming/pixellab")
# name: (cell, crop box or None for its own bounding box)
STANDING = {
    # the yard's fixtures
    "fix.shade tree": (2, None), "fix.yard bench": (25, (7, 10, 30, 31)), "fix.fire pit": (27, None), "fix.fire pit.off": (27, None), "fix.fire pit.on": (28, None),
    "fix.woodpile": (34, None), "fix.shed": (30, None),
    # the meadow's
    "fix.big tree": (0, None), "fix.bramble": (6, None), "fix.boulder": (11, None), "fix.stream": (14, None),
    # the Works' two goals (works.toml): a fountain for the garden; the vane is drawn below, on a pole
    "fix.fountain": (62, None),
    # scenery
    "decor.pine": (1, None), "decor.birch": (3, None), "decor.stump": (4, None), "decor.log": (5, None), "decor.flowering bush": (7, None),
    "decor.long grass": (8, None), "decor.wildflowers": (9, None), "decor.mushroom ring": (10, None), "decor.rocks": (12, None),
    "decor.signpost": (24, None), "decor.beehive": (31, None), "decor.wheelbarrow": (33, None), "decor.birdhouse": (60, None),
    # the weather on the ground (px/outdoors.ts)
    "outdoor.puddle": (35, None), "outdoor.drift": (36, None), "outdoor.ice": (37, None), "outdoor.leaves": (38, None),
}
# creatures: a still and, to go about, the same a pixel up (a hop; the butterfly folds its wings)
CREATURES = {"creature.rabbit": (39, None), "creature.hedgehog": (40, None), "creature.squirrel": (41, None), "creature.butterfly": (45, None),
             "creature.owl": (48, (9, 3, 23, 21)), "creature.bird.outdoors": (44, (8, 6, 24, 21))}
# what is foraged outdoors, on the grass it lies in (grows.*, 16 x 16), and loose (bit.*), where the house has no picture yet
FORAGE = {"flint": 56, "pine cone": 51, "berry": 53, "nut": 54, "mushroom": 55, "acorn": 50}
WATER = lambda p: p[3] and p[2] > p[0] + 30 and p[2] > p[1]   # the blue of a pictured stream: the view draws its own water


def cell(im, i):
    return im.crop(((i % 8) * 32, (i // 8) * 32, (i % 8) * 32 + 32, (i // 8) * 32 + 32))


def dry(im, grass=False):
    """The picture without its pictured water (and the white glints on it), and without its grass if `grass` is false."""
    im = im.copy()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            p = px[x, y]
            if WATER(p) or (p[3] and min(p[:3]) > 200) or (not grass and p[3] and p[1] > p[0] + 10 and p[1] > p[2]):
                px[x, y] = (0, 0, 0, 0)
    return im.crop(im.getbbox())


def clay():
    """The clay bank: a low mound of wet grey-brown clay cut in layers, a dark wet foot where it meets the stream (drawn
    here: the pictured bank is seen from the side and has the water in it)."""
    rows = ["......KKKKKKKKKK......",
            "....KKhhhhhhhhhhKK....",
            "...KhhcccccchhhhhcK...",
            "..KhccccccccccccccdK..",
            ".KcccddddcccccdddccdK.",
            ".KccccccccccccccccccK.",
            "KcddcccccdddddcccccddK",
            "KccccccccccccccccccccK",
            "KwwccdddcccccccdddcwwK",
            ".KwwwwwwwwwwwwwwwwwwK.",
            "..KKKKKKKKKKKKKKKKKK.."]
    pal = {"K": (58, 40, 30), "h": (186, 150, 112), "c": (150, 112, 82), "d": (118, 86, 64), "w": (88, 66, 56)}
    im = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in pal:
                im.putpixel((x, y), pal[ch] + (255,))
    return im


def small(im):
    """A 32-pixel picture at half its size, its edge kept hard."""
    im = im.reduce(2)
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            p = px[x, y]
            px[x, y] = p[:3] + (255,) if p[3] >= 110 else (0, 0, 0, 0)
    return im


def main():
    src = Image.open(os.path.join(SRC, "outdoor32.png")).convert("RGBA")
    pics, extra = {}, {}
    for name, (i, box) in {**STANDING, **CREATURES}.items():
        c = cell(src, i)
        pics[name] = c.crop(box or c.getbbox())
    # the clay bank: its earth and grass, without the water; the stepping stones, without theirs
    pics["fix.clay bank"] = clay()
    pics["decor.stepping stones"] = dry(cell(src, 16))
    # the weather vane on a pole of its own (the picture has it on a roof's peak)
    vane = cell(src, 61).crop((6, 2, 26, 22))
    v = Image.new("RGBA", (20, 38), (0, 0, 0, 0))
    v.alpha_composite(vane, (0, 0))
    for y in range(18, 38):
        for x, col in ((9, (44, 30, 22, 255)), (10, (92, 64, 44, 255))):
            v.putpixel((x, y), col)
    for x in range(7, 13):
        v.putpixel((x, 37), (44, 30, 22, 255))
    pics["fix.weather vane"] = v
    # the garden gate, shut and open, in the garden's south fence and the yard's north one (door.outgate.*)
    for state, i in (("open", 20), ("shut", 21)):
        g = cell(src, i)
        g = g.crop((1, 3, 31, 28))
        pics["door.outgate.north.%s" % state] = g
        pics["door.outgate.south.%s" % state] = g
    have = json.load(open(os.path.join(ASSETS, "sprites.json")))
    for b, i in FORAGE.items():
        pics["grows." + b] = small(cell(src, i))
        pics["grows.%s.bare" % b] = small(cell(src, 8))   # picked: only grass there until it grows back
        if "bit." + b not in have or have["bit." + b].get("file") == "outdoor.png":
            pics["bit." + b] = pics["grows." + b]
    # the map's icons: a fence with its gate for the yard, a round tree for the meadow
    pics["icon.room.yard"] = small(cell(src, 18).crop((0, 3, 32, 35)))
    pics["icon.room.meadow"] = small(cell(src, 0))

    sheet = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    out, x, y, row = {}, 0, 0, 0
    for name, im in pics.items():   # a shelf at a time, left to right
        w, h = im.size
        frames = 2 if name in CREATURES else 1
        if x + w * frames > 256:
            x, y, row = 0, y + row, 0
        sheet.alpha_composite(im, (x, y))
        e = {"pack": "own", "file": "outdoor.png", "rect": [x, y, w, h]}
        if name in CREATURES:
            if name == "creature.butterfly":   # wings folded: half as wide
                f = im.resize((max(4, w // 2), h), Image.NEAREST)
                sheet.alpha_composite(f, (x + w + (w - f.width) // 2, y))
            else:
                sheet.alpha_composite(im.crop((0, 1, w, h)), (x + w, y))   # a pixel up
            go = {"frames": [[0, 0], [1, 0]], "fps": 8 if name == "creature.butterfly" else 5}
            e["anims"] = {"idle": {"frames": [[0, 0]], "fps": 1}, "walk.right": go, "walk.down": go, "walk.left": dict(go, flip=True), "walk.up": dict(go, flip=True)}
            if name in ("creature.rabbit", "creature.hedgehog", "creature.squirrel", "creature.bird.outdoors"):   # (the pictures face left)
                e["anims"] = {"idle": {"frames": [[0, 0]], "fps": 1, "flip": True}, "walk.right": dict(go, flip=True), "walk.down": dict(go, flip=True), "walk.left": go, "walk.up": go}
        elif name.startswith("door.outgate.north"):
            e["anchor"] = [w // 2 - 8, h]   # standing on the fence line, over the north door's tile
        elif name.startswith("door.outgate.south"):
            e["anchor"] = [w // 2 - 8, 0 - 6]   # in the south fence, a little into the door's tile
        elif name.startswith(("fix.", "decor.", "outdoor.")) and (w > 16 or h > 16):
            e["anchor"] = [w // 2 - 8, h - 15]   # its foot on the middle of its tile
        out[name] = e
        x += w * frames + 1
        row = max(row, h + 1)
    assert y + row <= 256, "the sheet is full"
    # the footbridge: the pond's hobs' bridge, north to south, from the bank's tile down over the stream and out of view
    out["fix.fire pit.on"]["lamp"] = 34   # (a picture that gives light: the room makes it a lamp of this size)
    out["fix.footbridge"] = dict(have["fix.built.pond bridge.ns"], anchor=[3, -6])
    sheet.save(os.path.join(ASSETS, "own", "outdoor.png"))
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(%s)":' % "|".join(re.escape(k) for k in out), l) and '"file": "outdoor.png"' not in l]
    at = next(i for i, l in enumerate(lines) if l.startswith(' "icon.act.pot":'))
    lines[at + 1:at + 1] = [" %s: %s," % (json.dumps(k), json.dumps(v)) for k, v in out.items()]
    open(path, "w").write("\n".join(lines))
    print("cut %d pictures into own/outdoor.png" % len(out))


if __name__ == "__main__":
    main()
