"""The store and the memory shelves (SPEC-v3.5.12 §1, §4): the storage furniture of PixelLab's rail sheet, cut into
own/store.png. Needs Python 3.11+ and Pillow. From this folder:

  python3 store.py [rail32.png]   cuts own/store.png and lays its entries into ../../sprites.json as one block, right
                                  after "fix.sweeper dock" (whose own entries it replaces)

The sheet is `assets-incoming/pixellab/rail32.png` (32 x 32 cells, 8 a row; names in sheets.toml under [rail32]).
Cells 24 to 51 are the storage furniture and the memory shelves; each is `fix.<its [rail32] name>` (a store fixture's
`fix.art` names it), whole and unchanged, standing on its tile with its middle on the tile's middle and rising one tile
up the wall. Its `surface` is the front of its lowest shelf, where an open shelf's three things stand in a row. Added:
the three open material crates empty (`.empty`, their contents taken out and the dark inside of the crate showing), for
a crate that holds no bits; and the keepsake box (cell 39) small enough to stand in a row on a memory shelf (`.slot`)."""
import json, os, re, sys
from PIL import Image
from build import ASSETS

RAIL = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/PetProject/assets-incoming/pixellab/rail32.png")
NAMES = ["wooden storage shelf with neat jars", "tall storage rack with labelled crates", "cabinet with many small drawers", "stack of tidy crates with lids",
         "wooden locker cabinet", "wall of cubby holes with small things", "storage chest with iron bands", "big wicker storage hamper",
         "pegboard with hanging tools", "shelf of folded cushions and blankets", "shelf of lamps and candles", "shelf of cups and bowls",
         "shelf with rows of small boxes, a memory shelf", "family memory shelf with candles and keepsake boxes", "small shrine shelf with a photo frame and flowers",
         "little wooden keepsake box", "round hat box", "shelf of scrolls", "bin of loose bits sorted by kind", "jar of buttons", "jar of seeds", "jar of beads",
         "crate of reeds", "crate of stones", "crate of wood offcuts", "coil of rope", "bolt of cloth", "tidy stack of tiles"]   # cells 24..51
FIRST, C = 24, 32
OPEN = (46, 47, 48)        # the crates whose contents show: an empty one of each
FRONT, X0, X1 = 17, 4, 27  # in those three: the top of the crate's front, its left and right sides
# the keepsake box (cell 39) as a slot on a memory shelf: its dark wood, the carved lid lighter, the brass clasp
SLOT = [".#######.",
        "#hhhhhhh#",
        "#mmmmmmm#",
        "#########",
        "#dddbddd#",
        "#ddd#ddd#",
        "#########"]
SLOT_PAL = {"#": "24160e", "h": "c08a56", "m": "9a6440", "d": "74462a", "b": "e8c070"}


def empty(cell):
    """The crate with nothing in it: above its front, only its open top, its back board and the dark inside."""
    out, p = cell.copy(), cell.load()
    q = out.load()
    dark = p[16, FRONT]
    for y in range(FRONT):
        for x in range(C):
            q[x, y] = (0, 0, 0, 0)
    top = FRONT - 6
    for y in range(top, FRONT):
        for x in range(X0, X1 + 1):
            wood = p[x, FRONT + 3]
            if y == top or x in (X0, X1):
                q[x, y] = dark
            elif y == top + 1 or x in (X0 + 1, X1 - 1):
                q[x, y] = wood
            else:   # the inside, darker toward the front
                k = 0.5 - 0.05 * (y - top - 2)
                q[x, y] = (round(wood[0] * k), round(wood[1] * k), round(wood[2] * k), 255)
    return out


def sheet():
    src = Image.open(RAIL).convert("RGBA")
    cell = lambda i: src.crop(((i % 8) * C, (i // 8) * C, (i % 8) * C + C, (i // 8) * C + C))
    im, out = Image.new("RGBA", (8 * C, 4 * C), (0, 0, 0, 0)), {}
    for j, name in enumerate(NAMES):
        x, y = (j % 8) * C, (j // 8) * C
        im.paste(cell(FIRST + j), (x, y))
        out["fix." + name] = {"pack": "own", "file": "store.png", "rect": [x, y, C, C], "anchor": [8, 16], "surface": [4, 27, 24]}
    for k, i in enumerate(OPEN):   # after the last cell, in the same row
        x, y = (len(NAMES) % 8 + k) * C, (len(NAMES) // 8) * C
        im.paste(empty(cell(i)), (x, y))
        out["fix.%s.empty" % NAMES[i - FIRST]] = {"pack": "own", "file": "store.png", "rect": [x, y, C, C], "anchor": [8, 16], "surface": [4, 27, 24]}
    slot = Image.new("RGBA", (len(SLOT[0]), len(SLOT)), (0, 0, 0, 0))
    for y, row in enumerate(SLOT):
        for x, ch in enumerate(row):
            if ch != ".":
                slot.putpixel((x, y), tuple(int(SLOT_PAL[ch][i:i + 2], 16) for i in (0, 2, 4)) + (255,))
    x, y = (len(NAMES) % 8 + len(OPEN)) * C, (len(NAMES) // 8) * C
    im.paste(slot, (x, y))
    out["fix.little wooden keepsake box.slot"] = {"pack": "own", "file": "store.png", "rect": [x, y, slot.width, slot.height], "anchor": [0, slot.height - 16]}
    im.save(os.path.join(ASSETS, "own", "store.png"))
    return out


if __name__ == "__main__":
    own = sheet()
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(%s)":' % "|".join(re.escape(n) for n in own), l)]
    at_ = next(i for i, l in enumerate(lines) if l.startswith(' "fix.sweeper dock":'))
    lines[at_ + 1:at_ + 1] = [" %s: %s," % (json.dumps(n), json.dumps(e)) for n, e in own.items()]
    open(path, "w").write("\n".join(lines))
    print("cut %d pictures into own/store.png" % len(own))
