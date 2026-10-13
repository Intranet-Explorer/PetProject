"""The pictures for building that lasts and for decorating (SPEC-v3.5 §4), drawn as art.py's are: one character is
one pixel, in art.py's palette with a few colours of its own. Needs Pillow, like build.py.

  uv run --with pillow python view/assets/own/src/building.py     draws own/building.png and prints the entries for
                                                                   sprites.json (kept there by hand, in one block after
                                                                   the last "fix." entry)

A thing under way is `fix.site` (what it takes, set down between two posts) and then `fix.site.half` (a frame half
boarded), or on a wall `fix.site.wall` and `fix.site.wall.half` (a ladder, then a ladder and a plank); what stands
when it is done is `fix.built.<project>` for each project in building.toml. The dyes are one dish in each colour."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art
from build import Sheet, rgba
from PIL import Image

PAL = dict(art.PAL, **{"1": "3f9b63", "2": "8fd0a0", "3": "4a7fc1", "4": "9cc0ee", "5": "26302c", "6": "5a6660", "7": "f08a2e", "8": "f7b877"})


def S(text):
    return text.strip("\n").split("\n")


def pic(rows, swap=None):
    w = len(rows[0])
    im = Image.new("RGBA", (w, len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        assert len(row) == w, "row %d is %d wide, not %d: %r" % (y, len(row), w, row)
        for x, ch in enumerate(row):
            ch = (swap or {}).get(ch, ch)
            if ch != ".":
                im.putpixel((x, y), rgba(PAL[ch]))
    return im


SITE = S("""
................
................
................
.##..........##.
#bo#........#bo#
#bo##########bo#
#boaAaAaAaAaAbo#
#bo##########bo#
#bo#........#bo#
#bo#.######.#bo#
#bo##oooooo##bo#
#bo#nnnnnnnn#bo#
#bo##########bo#
#bo#bbbbbbbb#bo#
.##.########.##.
................
""")

HALF = S("""
................
.##..........##.
#bo#........#bo#
#bo##########bo#
#bonnnnnnnnnnbo#
#bo##########bo#
#bo#.##.....#bo#
#bo#.#b#....#bo#
#bo#..#b#...#bo#
#bo#...#b#..#bo#
#bo#....#b#.#bo#
#bo#.....#b##bo#
#bo##########bo#
#bonnnnnnnnnnbo#
#bo##########bo#
#bo#oon#oon##bo#
#bo#oon#oon#.#o#
#bo#oon#oon#.#o#
#bo#oon#oon#.#o#
#bo#oon#oon#.#o#
#bo#########.#o#
#bo#........#bo#
.##..........##.
................
""")

RAIL, RUNG = "..#b#......#b#..", ["..#b########b#..", "..#bnnnnnnnnb#..", "..#b########b#.."]
LADDER = ["..###......###.."] + (RUNG + [RAIL] * 3) * 5 + ["..###......###.."]   # 32 tall: it stands on the floor and leans up the wall
PLANK = ["################", "#oooooooooooooo#", "#nnnnnnnnnnnnnn#", "################"]
LADDER_HALF = LADDER[:7] + PLANK + LADDER[11:]

BENCH = S("""
................
................
................
................
.##############.
#oooooooooooooo#
#nnnnnnnnnnnnnn#
.##############.
.#b#........#b#.
.##############.
#oooooooooooooo#
#nnnnnnnnnnnnnn#
################
.#b#........#b#.
.#b#........#b#.
.###........###.
""")

TABLE = S("""
................
................
................
................
................
.##############.
#OOOOOOOOOOOOOO#
#oooooooooooooo#
#nnnnnnnnnnnnnn#
################
.#b#........#b#.
.#b#........#b#.
.#b##########b#.
.#b#........#b#.
.#b#........#b#.
.###........###.
""")

BACK, BOARD = "#o#KKKKKKKKKK#o#", ["#o############o#", "#onnnnnnnnnnnno#", "#o############o#"]
SHELF = [".##############.", "#oooooooooooooo#", "#o############o#"] + ([BACK] * 6 + BOARD) * 2 + [BACK] * 6 + \
    ["#o############o#", "#oooooooooooooo#", "################", ".#b#........#b#.", ".###........###."]

BED = S("""
.##############.
#oooooooooooooo#
#onnnnnnnnnnnno#
#o############o#
#o#vvvvvvvvvv#o#
#o#vwwwwwwwwv#o#
#o#vvvvvvvvvv#o#
#o############o#
#o#IIIIIIIIII#o#
#o#IllIIIIllI#o#
#o#IIIIIIIIII#o#
#o#IIIIllIIII#o#
#o#IIIIIIIIII#o#
#o#IllIIIIllI#o#
#o#IIIIIIIIII#o#
#o#IIIIllIIII#o#
#o#IIIIIIIIII#o#
#o#iiiiiiiiii#o#
#o############o#
#oooooooooooooo#
#nnnnnnnnnnnnnn#
################
.#b#........#b#.
.###........###.
""")

ROOF = S("""
.##############.
#nnnnnnn#nnnnnn#
#ooooooo#oooooo#
################
#bbbb#bbbbbbbbb#
#nnnn#nnnnnnnnn#
################
#GgG#DDDDD#gGGg#
#gGg#DdDdD#GgGg#
.##############.
""")

FOLD = ".#zZPZzZPZzZPZ#."
CURTAIN = ["################", "#yyyyyyyyyyyyyy#", "################"] + [FOLD] * 21 + [".#zzzzzzzzzzzz#.", "..############.."]

BRIDGE = ["." + "#" * 46 + ".", "#" + "o" * 46 + "#", "#" * 48] + ["#" + "ooo#" * 11 + "oo#"] * 3 + ["#" + "nnn#" * 11 + "nn#"] * 7 + \
    ["#" * 48, "#" + "b" * 46 + "#", "." + "#" * 46 + "."]

BOX = S("""
................
................
################
#KKKKKKKKKKKKKK#
################
#oooooooooooooo#
#nnnnnnnnnnnnnn#
#bbbbbbbbbbbbbb#
.##############.
""")

NICHE = S("""
....########....
..##KKKKKKKK##..
.#KKKKKKKKKKKK#.
.#KKKKKKKKKKKK#.
#KKKKKKYYKKKKKK#
#KKKKKYwwYKKKKK#
#KKKKKYwwYKKKKK#
#KKKKKKYYKKKKKK#
#KKKKKK##KKKKKK#
#KKKKK#cc#KKKKK#
#KKKKK#cc#KKKKK#
#KKKK######KKKK#
#KKK#DDDDDD#KKK#
#dddddddddddddd#
#DDDDDDDDDDDDDD#
################
""")

HUTCH = S("""
................
......####......
....##oooo##....
..##oooooooo##..
.#oooooooooooo#.
################
.#nnnnnnnnnnnn#.
.#nnnn####nnnn#.
.#nnn#KKKK#nnn#.
.#nn#KKKKKK#nn#.
.#nn#KKKKKK#nn#.
.#nn#KKKKKK#nn#.
.#bb#KKKKKK#bb#.
.##############.
..yyAyyyAyyAyy..
................
""")

DISH = S("""
................
................
................
................
................
................
................
.....######.....
...##xxXXxx##...
..#DxxxxXXxxD#..
..#DDxxxxxxDD#..
..#dDDDDDDDDd#..
...#dddddddd#...
....########....
................
................
""")
DYES = {"red dye": {"X": "p"}, "green dye": {"x": "1", "X": "2"}, "black dye": {"x": "5", "X": "6"}, "ochre dye": {"x": "7", "X": "8"}, "blue dye": {"x": "3", "X": "4"}}

LILY = S("""
................
................
................
................
................
................
.....##..##.....
....#ww##ww#....
...#wvvwwvvw#...
....#wvYYvw#....
...#wvvYYvvw#...
....#ww##ww#....
.....##..##.....
................
................
................
""")

PAD = S("""
................
................
................
....##..##......
...#ww##ww#.....
..#wvvwwvvw#....
...#wvYYvw#.....
..#wvvYYvvw#....
...#ww##ww#.....
....########....
..##GGGGGGGG##..
.#GGGGgGGGGGGG#.
.#GGGGGgggGGGG#.
..##GGGGGGGG##..
....########....
................
""")
PAD_BARE = [("................" if 3 <= y <= 8 else r) for y, r in enumerate(PAD)]


def lining():
    """A stretch of wall lined against the cold: three courses of clay tiles with moss packed along the top."""
    course = ["ddddD#", "ddddD#", "DDDDB#", "######"]
    rows = ["." + "#" * 30 + ".", "#" + "GgGGgG" * 5 + ".", "#" * 31 + "."]
    for c in range(3):
        for r in course:
            line = (r * 6)[3 * (c % 2):][:30]   # each course half a tile along from the one above
            rows.append("#" + line[:29] + "#.")
    return rows


def trellis():
    """A frame for vines to climb: two posts, rails and a middle slat, with a vine winding up it."""
    rows = [["."] * 16 for _ in range(32)]
    def put(x, y, ch):
        if 0 <= x < 16 and 0 <= y < 32:
            rows[y][x] = ch
    for y in range(1, 31):
        for x0 in (1, 12):
            put(x0, y, "#"); put(x0 + 1, y, "n" if x0 == 1 else "b"); put(x0 + 2, y, "#")
        put(7, y, "#"); put(8, y, "#")
    for x in range(1, 15):
        put(x, 0, "#"); put(x, 31, "#")
    for y0 in (3, 10, 17, 24):
        for x in range(1, 15):
            put(x, y0, "#"); put(x, y0 + 1, "o"); put(x, y0 + 2, "#")
    for i, y in enumerate(range(27, 1, -3)):   # the vine: a stem that crosses from side to side, a leaf at each turn
        x = 4 + (i % 3) * 3
        for dx, dy, ch in ((0, 0, "g"), (1, 0, "G"), (0, 1, "G"), (1, 1, "g"), (-1, 0, "#"), (2, 0, "#"), (0, -1, "#"), (1, -1, "#"), (-1, 1, "#"), (2, 1, "#"), (0, 2, "#"), (1, 2, "#")):
            put(x + dx, y + dy, ch)
    return ["".join(r) for r in rows]


def sheet():
    s = Sheet("building.png", 16)
    s.add("fix.site", pic(SITE))
    s.add("fix.site.half", pic(HALF))
    s.add("fix.site.wall", pic(LADDER))
    s.add("fix.site.wall.half", pic(LADDER_HALF))
    s.add("fix.built.bench", pic(BENCH))
    s.add("fix.built.table", pic(TABLE), surface=[2, 6, 12])
    s.add("fix.built.big shelf", pic(SHELF), surface=[3, 19, 10])
    s.add("fix.built.bed frame", pic(BED))
    s.add("fix.built.roof patch", pic(ROOF), anchor=[0, 30])            # what hangs on the wall: how far above its tile's top edge the picture's top is
    s.add("fix.built.draught curtain", pic(CURTAIN), anchor=[0, 27])
    s.add("fix.built.wall lining", pic(lining()), anchor=[8, 24])
    s.add("fix.built.pond bridge", pic(BRIDGE), anchor=[16, 0])          # three tiles wide, its tile in the middle
    s.add("fix.built.window box", pic(BOX), anchor=[0, 9])               # under the window
    s.add("fix.built.lamp niche", pic(NICHE), anchor=[0, 24])
    s.add("fix.built.trellis", pic(trellis()))
    s.add("fix.built.hutch", pic(HUTCH))
    for name, swap in DYES.items():
        s.add("bit." + name, pic(DISH, swap))
    s.add("bit.lily", pic(LILY))
    s.add("grows.lily", pic(PAD))
    s.add("grows.lily.bare", pic(PAD_BARE))
    return s


if __name__ == "__main__":
    for name, entry in sheet().save().items():
        print(' %s: %s,' % (json.dumps(name), json.dumps(entry)))
