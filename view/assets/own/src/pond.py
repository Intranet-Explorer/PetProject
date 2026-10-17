"""The pond (SPEC-v3.6a §1, §2, §5, §7): the dock, the hobs' bridge lying north to south, lily pads, cattails, the duck
and the frog, the catches and finds, and the everyday kinds, cut from PixelLab's pictures into own/pond.png. Needs
Python 3.11+ and Pillow. From this folder:

  python3 pond.py [PIXELLAB]   cuts own/pond.png (PIXELLAB: the folder holding pond32.png, pond16.png, everyday16.png;
                               by default ~/PetProject/assets-incoming/pixellab) and lays its entries into
                               ../../sprites.json as one block, right after "fix.sweeper dock"

Names are in sheets.toml ([pond32], [pond16], [everyday16]). The water itself, the fish under it, the ice and its holes,
the line and the float are drawn by the view (px/pond.ts). The everyday kinds and the finds keep their own colours
(`"tint": "none"`): a fork is a fork whatever its maker's colour."""
import json, os, re, sys
from PIL import Image
from build import ASSETS

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/PetProject/assets-incoming/pixellab")
# kind.<name> and bit.<name>: (sheet, cell)
KINDS = {"fork": ("e", 24), "spoon": ("e", 25), "knife": ("e", 26), "plate": ("e", 28), "kettle": ("e", 31), "stick": ("e", 32), "tube": ("e", 34),
         "brush": ("e", 35), "broom": ("e", 36), "bucket": ("e", 37), "torch": ("e", 38), "needle": ("e", 39), "wheel": ("e", 41), "hook": ("e", 42),
         "spring": ("e", 40), "rod": ("e", 0), "bottle": ("p", 8), "note bottle": ("e", 13), "lens": ("e", 17), "gear": ("e", 18), "ring": ("e", 19),
         "key": ("e", 15), "golden fish": ("e", 7)}
BITS = {"fish": ("e", 5), "big fish": ("e", 6), "waterlogged wood": ("e", 21), "weed": ("e", 22), "hook": ("e", 2), "spring": ("e", 40)}


def main():
    e = Image.open(os.path.join(SRC, "everyday16.png")).convert("RGBA")
    p16 = Image.open(os.path.join(SRC, "pond16.png")).convert("RGBA")
    p32 = Image.open(os.path.join(SRC, "pond32.png")).convert("RGBA")
    cell16 = lambda s, i: (e if s == "e" else p16).crop(((i % 8) * 16, (i // 8) * 16, (i % 8) * 16 + 16, (i // 8) * 16 + 16))
    cell32 = lambda i: p32.crop(((i % 8) * 32, (i // 8) * 32, (i % 8) * 32 + 32, (i // 8) * 32 + 32))
    sheet, out = Image.new("RGBA", (256, 176), (0, 0, 0, 0)), {}
    n = 0
    for prefix, table in (("kind.", KINDS), ("bit.", BITS)):   # 16 x 16, a row of 16
        for name, (s, i) in table.items():
            x, y = (n % 16) * 16, (n // 16) * 16
            sheet.alpha_composite(cell16(s, i), (x, y))
            out[prefix + name] = {"pack": "own", "file": "pond.png", "rect": [x, y, 16, 16], **({"tint": "none"} if prefix == "kind." else {})}
            n += 1
    y0 = 32
    # the frog: pond16's, sitting and mid-hop (two 16 x 16 cells)
    frog = cell16("p", 3)
    sheet.alpha_composite(frog, (0, y0))
    sheet.alpha_composite(frog, (16, y0), (0, 2))   # (the hop: two pixels up)
    hop = {"frames": [[0, 0], [1, 0]], "fps": 4}
    out["creature.frog"] = {"pack": "own", "file": "pond.png", "rect": [0, y0, 16, 16],
                            "anims": {"idle": {"frames": [[0, 0]], "fps": 1}, "walk.right": hop, "walk.down": hop, "walk.left": dict(hop, flip=True), "walk.up": dict(hop, flip=True)}}
    # the duck: pond32's, turned to face right, bobbing a pixel
    duck = cell32(31).crop((6, 8, 26, 28)).transpose(Image.FLIP_LEFT_RIGHT)
    sheet.alpha_composite(duck, (32, y0))
    sheet.alpha_composite(duck.crop((0, 0, 20, 14)), (52, y0 + 1))
    sheet.alpha_composite(duck.crop((0, 14, 20, 20)), (52, y0 + 14))   # (its ripples stay where they are)
    bob = {"frames": [[0, 0], [1, 0]], "fps": 2}
    out["creature.duck"] = {"pack": "own", "file": "pond.png", "rect": [32, y0, 20, 20],
                            "anims": {"idle": bob, "walk.right": bob, "walk.down": bob, "walk.left": dict(bob, flip=True), "walk.up": dict(bob, flip=True)}}
    # the dock (pond32 cell 0, the planks and posts seen from above): its end with two posts, a run of planks, its foot
    dock = cell32(0).crop((4, 0, 28, 32))
    for name, (top, bot) in {"pond.dock.end": (5, 13), "pond.dock.planks": (13, 21), "pond.dock.foot": (21, 31)}.items():
        x = 72 + len([k for k in out if k.startswith("pond.dock")]) * 24
        sheet.alpha_composite(dock.crop((0, top, 24, bot)), (x, y0))
        out[name] = {"pack": "own", "file": "pond.png", "rect": [x, y0, 24, bot - top]}
    # the hobs' bridge (pond32 cell 62, planks across a narrow water) turned to run north to south over four tiles: the
    # splashes at its posts taken off (they stand on the banks), the planks between drawn out to 60 pixels
    b = cell32(62).crop((0, 7, 32, 29))
    px = b.load()
    for yy in range(b.height):
        for xx in range(b.width):
            r, g, bl, a = px[xx, yy]
            if a and (bl > r + 20 or r + g + bl > 600):
                px[xx, yy] = (0, 0, 0, 0)
    long = Image.new("RGBA", (60, 22), (0, 0, 0, 0))
    long.alpha_composite(b.crop((0, 0, 8, 22)), (0, 0))
    for k in range(5):
        long.alpha_composite(b.crop((8, 0, 15, 22)), (8 + 7 * k, 0))
    long.alpha_composite(b.crop((15, 0, 32, 22)), (43, 0))
    long = long.transpose(Image.ROTATE_90)   # 22 x 60
    sheet.alpha_composite(long, (144, y0))
    out["fix.built.pond bridge.ns"] = {"pack": "own", "file": "pond.png", "rect": [144, y0, 22, 60], "anchor": [3, 46]}   # (its foot two pixels inside the south bank's tile)
    # on the water: a cluster of lily pads with a flower, a pad alone, a flower alone; by it, cattails
    for name, pic, x in (("pond.lily", cell32(26).crop((2, 6, 30, 28)), 168), ("pond.lily.pad", cell16("p", 12).crop((1, 3, 15, 14)), 196), ("pond.lily.flower", cell16("p", 13).crop((1, 2, 15, 14)), 210)):
        sheet.alpha_composite(pic, (x, y0))
        out[name] = {"pack": "own", "file": "pond.png", "rect": [x, y0, pic.width, pic.height]}
    cat = cell32(27).crop((4, 3, 27, 31))
    sheet.alpha_composite(cat, (168, y0 + 32))
    out["decor.cattails"] = {"pack": "own", "file": "pond.png", "rect": [168, y0 + 32, 23, 28], "anchor": [3, 14]}   # (stood on the middle of its tile)
    sheet.save(os.path.join(ASSETS, "own", "pond.png"))
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(%s)":' % "|".join(re.escape(k) for k in out), l)]
    at = next(i for i, l in enumerate(lines) if l.startswith(' "fix.sweeper dock":'))
    lines[at + 1:at + 1] = [" %s: %s," % (json.dumps(k), json.dumps(v)) for k, v in out.items()]
    open(path, "w").write("\n".join(lines))
    print("cut %d pictures into own/pond.png" % len(out))


if __name__ == "__main__":
    main()
