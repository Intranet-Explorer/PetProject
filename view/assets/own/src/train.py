"""The little train (SPEC-v3.5.12 §3, §5) and the small things on its platforms. Needs Python 3.11+ and Pillow. From
this folder:

  python3 train.py [PIXELLAB]   draws own/train.png from PixelLab's pictures (PIXELLAB: the folder holding train/ and
                                rail32.png; by default assets-incoming/pixellab in the project folder) and lays its
                                entries into ../../sprites.json as one block, right after "fix.sweeper dock"

Each car (the engine, the cart with its lid shut, the tram) is a 34 x 34 cell in five rows of the sheet: its eight
still directions, then its drive animation facing south, east, north and west, five frames each (frame 0 is the
still), as `creature.sweeper` is laid out. The cart with its lid open has only the row of stills. Under them, the
station things from rail32.png (cells 53, 56, 59, 60), each cut to what it draws."""
import json, os, re, sys
from PIL import Image

ASSETS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(ASSETS))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets-incoming", "pixellab")
C = 34
EIGHT = ["south", "south-east", "east", "north-east", "north", "north-west", "west", "south-west"]
FOUR = [("walk.down", "south"), ("walk.right", "east"), ("walk.up", "north"), ("walk.left", "west")]
CARS = [("creature.train", "engine", True), ("creature.train.cart", "cart", True), ("creature.train.cart.open", "cart_open", False), ("creature.train.tram", "tram", True)]
STATION = {"station.lamp post": 53, "station.bell post": 56, "station.bench": 59, "station.clock": 60}


def main():
    rows = sum(5 if drives else 1 for *_, drives in CARS)
    sheet, out, y = Image.new("RGBA", (8 * C, rows * C + 32)), {}, 0
    for name, car, drives in CARS:
        for i, d in enumerate(EIGHT):
            sheet.alpha_composite(Image.open(os.path.join(SRC, "train", car, "%s_%s.png" % (car, d))).convert("RGBA"), (i * C, y))
        anims = {"still." + d: {"frames": [[i, 0]], "fps": 1} for i, d in enumerate(EIGHT)}
        if drives:
            for r, (a, d) in enumerate(FOUR, 1):
                for f in range(5):
                    sheet.alpha_composite(Image.open(os.path.join(SRC, "train", car, "%s_drive_%s_%d.png" % (car, d, f))).convert("RGBA"), (f * C, y + r * C))
                anims[a] = {"frames": [[f, r] for f in range(5)], "fps": 8}
            anims["idle"] = {"frames": [[0, 0]], "fps": 1}
        out[name] = {"pack": "own", "file": "train.png", "rect": [0, y, C, C], "anims": anims}
        y += (5 if drives else 1) * C
    rail, x = Image.open(os.path.join(SRC, "rail32.png")).convert("RGBA"), 0
    for name, cell in STATION.items():
        pic = rail.crop(((cell % 8) * 32, (cell // 8) * 32, (cell % 8 + 1) * 32, (cell // 8 + 1) * 32))
        pic = pic.crop(pic.getbbox())
        sheet.alpha_composite(pic, (x, y))
        w, h = pic.size
        out[name] = {"pack": "own", "file": "train.png", "rect": [x, y, w, h], "anchor": [(w - 16) // 2, h - 14]}   # stood on the middle of its tile
        x += w
    sheet.save(os.path.join(ASSETS, "own", "train.png"))
    # sprites.json is kept by hand, one name to a line: this sheet's lines go in as one block right after "fix.sweeper dock"
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(%s)":' % "|".join(re.escape(n) for n in out), l)]
    at = next(i for i, l in enumerate(lines) if l.startswith(' "fix.sweeper dock":'))
    lines[at + 1:at + 1] = [" %s: %s," % (json.dumps(n), json.dumps(e)) for n, e in out.items()]
    open(path, "w").write("\n".join(lines))
    print("drew %d pictures into own/train.png" % len(out))


if __name__ == "__main__":
    main()
