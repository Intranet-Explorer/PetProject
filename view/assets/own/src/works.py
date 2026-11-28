"""The machine room (SPEC-v3.5.1 §1): "The Works", the vending machine as the room's centrepiece, and the plain
stand-ins the room's other new pieces start from. Needs Python 3.11+ and Pillow. From this folder:

  python3 works.py          draws own/works.png and lays its entries into ../../sprites.json as one block, right
                            after "fix.vending machine" (whose own entries it replaces)

The machine is option D of the design study, built out of Karsiori's Pixel Art Vending Machines Pack (CC0; the
picture it is cut from is in third_party/karsiori_vending/src/). Left to right: a red hopper at a pet's height where
things are thrown in; a wide arcade cabinet under the pack's rounded top, which carries a plain glowing sign instead
of the pack's lettering, with a row of six windows showing what it holds; the belt out of its right side that throws
what it gives off the end; glass tubes up out of its shoulders into the top of the wall, with light running through
them while it works. It stands on the floor row against the north wall and rises nearly to the top of the wall.

One frame is a cell of CW x CH; the sheet has a row for each of idle, take (the hopper gulps), work (tubes, bulbs,
screen; the windows flicker in turn), drop (the belt runs, the lamps go green) and lit (idle with its lights up,
for `fix.vending machine.lit`). What changes with the house is left to the view (px/works.ts): which window is
dim (its material is out), which one lights (what it gives), and what rides the belt. The `works` field of the
sprite tells it where those are on the picture."""
import json, os, re, tomllib
from PIL import Image, ImageFilter
from build import ASSETS, Sheet

ROOT = os.path.dirname(os.path.dirname(ASSETS))
PACK = os.path.join(ASSETS, "third_party", "karsiori_vending", "src", "Vending Machine 6.3 (No Glass).png")
W, H = 80, 50            # the machine's box: x 0..79; y is the room canvas's own (0 the top of the wall, 47 the foot of floor row 0)
OX, OY = 4, 4            # where the box sits in a cell: a margin for its glow
CW, CH = W + 8, H + 6    # a cell: 88 x 56
MODES = {"idle": 4, "take": 4, "work": 8, "drop": 6, "lit": 4}
FPS = {"idle": 3, "take": 8, "work": 8, "drop": 8, "lit": 6}
BODY = 13                # the top of the cabinet's shoulders
WIN_Y = 22               # the windows' frames: rows WIN_Y .. WIN_Y + 12
HOP = 35                 # the hopper's rim
TUBE = 20                # a pulse of light every 20 px of tube, 5 px long, 5 px a frame

PD = dict(a="657392", h="92a1b9", e="424c6e", d="0c2e44", b="06101c", m="18203b", c="b4b4b4", i="c7cfdd", l="858585",
          f="2872a8", g="dbece8", r="1beec6", n="efaf19", q="ae1bee", p="007ab1", s="009dca", w="ddfffc", V="00e8a9",
          j="b8c0cf", k="345966", o="38384c", t="96edd0", W="fdfdb5", P="efa3c9", y="5a303f", J="1b141e", u="ccc1be",
          x="6bceeb", A="be5340", D="e7825a", F="7a321c", C="390c14", O="f0933f", B="20243d", G="45465b", R="e93f47",
          M="ffbb9d", E="3cac81", Y="6bcb95", Z="6c0c1a", U="075a44")

# The sign: the house's name for the machine in a small square face, typed like the pieces in art.py
LETTERS = {
    "T": ["###", ".#.", ".#.", ".#.", ".#."], "H": ["#.#", "#.#", "###", "#.#", "#.#"], "E": ["###", "#..", "##.", "#..", "###"],
    "W": ["#...#", "#...#", "#.#.#", "#.#.#", ".#.#."], "O": ["###", "#.#", "#.#", "#.#", "###"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "S": ["###", "#..", "###", "..#", "###"], " ": ["..", "..", "..", "..", ".."]}


def col(h): return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def swap(im, pairs):
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y] in pairs: px[x, y] = pairs[px[x, y]]
    return im


class Art:
    """A cell to draw a machine frame in, in box coordinates and the palette's letters."""
    def __init__(s):
        s.im = Image.new("RGBA", (CW, CH)); s.pal = {k: col(v) for k, v in PD.items()}
    def c(s, k): return s.pal[k] if isinstance(k, str) else k
    def p(s, x, y, k):
        x += OX; y += OY
        if 0 <= x < CW and 0 <= y < CH: s.im.putpixel((x, y), s.c(k) if k else (0, 0, 0, 0))
    def r(s, x0, y0, x1, y1, k):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.p(x, y, k)
    def rows(s, x, y, rows, sub=None):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch not in ". ": s.p(x + i, y + j, (sub or {}).get(ch, ch))
    def blit(s, im, x, y, clip=None):
        px = im.load()
        for j in range(im.height):
            for i in range(im.width):
                if px[i, j][3] and (not clip or (clip[0] <= x + i <= clip[2] and clip[1] <= y + j <= clip[3])): s.p(x + i, y + j, px[i, j])
    def stand(s, im, cx, by):
        s.blit(im, cx - im.width // 2, by - im.height + 1)
    def outline(s, k, dark):
        """One pixel of line round the silhouette, wherever the edge is not already dark."""
        dark = {s.pal[d] for d in dark}; px = s.im.load(); add = []
        for y in range(CH):
            for x in range(CW):
                if px[x, y][3]: continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    u, v = x + dx, y + dy
                    if 0 <= u < CW and 0 <= v < CH and px[u, v][3] and px[u, v] not in dark: add.append((x, y)); break
        for xy in add: px[xy] = s.c(k)


def soften(art, rects, light, a1=0.5, a2=0.22):
    """A soft halo in whole pixels: what lies one and two pixels round a lit thing takes some of its light."""
    px = art.im.load(); lc = art.c(light); done = {}
    inside = {(x + OX, y + OY) for x0, y0, x1, y1 in rects for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    for x0, y0, x1, y1 in rects:
        for y in range(y0 - 2, y1 + 3):
            for x in range(x0 - 2, x1 + 3):
                d = max(x0 - x, x - x1, y0 - y, y - y1, 0); q = (x + OX, y + OY)
                if d and q not in inside and 0 <= q[0] < CW and 0 <= q[1] < CH: done[q] = min(done.get(q, 9), d)
    for q, d in done.items():
        r, g, b, a = px[q]
        if a:
            t = a1 if d == 1 else a2
            px[q] = (round(r + (lc[0] - r) * t), round(g + (lc[1] - g) * t), round(b + (lc[2] - b) * t), 255)


def sprites():
    """The house's sprite names -> pictures (for the materials' bits)."""
    S, P = json.load(open(os.path.join(ASSETS, "sprites.json"))), json.load(open(os.path.join(ASSETS, "packs.json")))
    def pic(name):
        s = S[name]; x, y, w, h = s["rect"]
        im = Image.open(os.path.join(ASSETS, P[s["pack"]]["dir"], s["file"])).convert("RGBA").crop((x, y, x + w, y + h))
        return im.crop(im.getbbox())
    return pic


def materials():
    return tomllib.loads(open(os.path.join(ROOT, "machine.toml")).read())["machine"]["materials"]


def dome():
    """The pack's rounded cabinet top, its lettering and rainbow taken off, and a plain glowing sign in their place."""
    pk = Image.open(PACK).convert("RGBA")
    T = pk.crop((0, 0, 47, 19)).copy(); px = T.load(); P = {k: col(v) for k, v in PD.items()}
    logo = {P[k] for k in "gfrnq"}
    for y in range(T.height):
        for x in range(T.width):
            if px[x, y] in logo: px[x, y] = P["a"]
    for x, y in ((9, 6), (37, 5), (6, 15), (40, 14)): px[x, y] = P["e"]        # a few scuffs, as the pack has on its sides
    return T


SIGN = "THE WORKS"


def sign(A, k, mode):
    """The glowing sign on the cabinet's top: a dark plate, the words in light. Brighter while it works."""
    x0, y0, x1, y1 = 18, 10, 61, 18                                  # the plate (box coordinates)
    A.r(x0, y0, x1, y1, "d"); A.r(x0 + 1, y0 + 1, x1 - 1, y1 - 1, "b")
    A.r(x0 + 1, y0, x1 - 1, y0, "e"); A.r(x0 + 1, y1, x1 - 1, y1, "h")   # set into the cabinet: shadow above, light below
    A.p(x0, y0, "a"); A.p(x1, y0, "a")
    glyphs = [LETTERS[ch] for ch in SIGN]
    wide = sum(len(g[0]) + 1 for g in glyphs) - 1
    x = (x0 + x1 + 1 - wide) // 2; y = y0 + 2
    on = "W" if mode in ("work", "lit") and k % 2 == 0 else "w"
    halo = "p" if mode in ("work", "lit") else "k"
    lit = []
    for g in glyphs:
        for j, row in enumerate(g):
            for i, ch in enumerate(row):
                if ch == "#": lit.append((x + i, y + j))
        x += len(g[0]) + 1
    for (u, v) in lit:                                              # its light spills a pixel round the letters, inside the plate
        for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if x0 < u + du < x1 and y0 < v + dv < y1 and (u + du, v + dv) not in lit: A.p(u + du, v + dv, halo)
    for (u, v) in lit: A.p(u, v, on)
    return (x0, y0, x1, y1)


def machine(mode="idle", k=0):
    """One frame of the machine (see the module's doc)."""
    A = Art(); P = A.pal
    work, lit_up = mode == "work", mode == "lit"
    tick = k if work else None
    on = lambda s: tick is not None and (s - 5 * tick) % TUBE < 5
    glow = []
    # ---- the tubes (behind the body): up out of its shoulders into the top of the wall, a thin one beside each
    L = Art()
    def seg(x, y, n, lit): L.p(x, y, ("w", "w", "r")[n] if lit else ("x", "f", "k")[n])
    for x0 in (4, 73):
        for y in range(-OY, BODY + 3):
            for n in range(3): seg(x0 + n, y, n, on(BODY + 3 - y))
        for y in (3, 9):                                            # steel collars
            L.r(x0 - 1, y, x0 + 3, y, "i"); L.r(x0 - 1, y + 1, x0 + 3, y + 1, "c"); L.p(x0 - 1, y + 1, "l")
    for x0 in (11, 67):
        for y in range(-OY, BODY + 2):
            lit = tick is not None and (y + 3 * tick) % 12 < 3
            L.p(x0, y, "w" if lit else "x"); L.p(x0 + 1, y, "r" if lit else "f")
        L.r(x0 - 1, 6, x0 + 2, 6, "c"); L.r(x0 - 1, 7, x0 + 2, 7, "l")
    for x0 in (3, 72): L.r(x0, BODY - 1, x0 + 4, BODY - 1, "i"); L.r(x0, BODY, x0 + 4, BODY + 1, "c")   # where they go into the shoulders
    L.outline("d", ()); A.blit(L.im, -OX, -OY)
    # ---- the body: one wide cabinet, the pack's rounded top rising out of its middle with the sign on it
    A.r(0, BODY, 79, 46, "a"); A.r(0, BODY, 79, BODY, "h"); A.r(0, BODY + 1, 0, 44, "h"); A.r(79, BODY + 1, 79, 44, "e")
    A.r(0, 45, 79, 45, "e"); A.r(0, 46, 79, 46, "m")
    for x, y in ((0, BODY), (79, BODY), (0, 46), (79, 46)): A.p(x, y, None)
    A.blit(dome(), 16, 1)
    plate = sign(A, k, mode)
    if work or lit_up: glow.append((plate, "x"))
    bulbs = []
    def bulb(x, y, b):
        A.p(x, y, "W" if b else "y")
        if b: bulbs.append((x, y, x, y))
    for i, x in enumerate(range(24, 56, 3)):                    # bulbs round the top of the dome
        bulb(x, 3 if 27 <= x <= 52 else 4, (i - k) % (2 if work or lit_up else 4) == 0)
    for i, x in enumerate(range(3, 77, 2)):                     # a long strip of them under the sign
        b = {"idle": (i - k) % 6 == 0, "lit": (i - k) % 2 == 0, "take": (i + k) % 3 == 0, "work": (i - k) % 3 == 0, "drop": (i - 2 * k) % 4 == 0}[mode]
        bulb(x, 20, b)
    # ---- six windows, one for each material; at work they flicker in turn (the view lights the one it gives)
    spin = [1, 3, 0, 5, 2, 4, 1, 3][k] if work else None
    pic = sprites()
    for n, mat in enumerate(materials()):
        x0 = 3 + 12 * n
        A.r(x0, WIN_Y, x0 + 12, WIN_Y + 12, "d")
        A.r(x0 + 1, WIN_Y + 1, x0 + 11, WIN_Y + 11, "f" if n == spin else ("k" if not lit_up else "p")); A.r(x0 + 1, WIN_Y + 11, x0 + 11, WIN_Y + 11, "j")
        A.p(x0 + 1, WIN_Y + 2, "x"); A.p(x0 + 2, WIN_Y + 1, "x")
        A.stand(pic("bit." + mat), x0 + 6, WIN_Y + 10)
        if n == spin: glow.append(((x0, WIN_Y, x0 + 12, WIN_Y + 12), "x"))
    # ---- the screen
    A.r(29, 36, 45, 44, "c"); A.r(29, 36, 45, 36, "i"); A.r(29, 37, 29, 44, "i"); A.r(45, 37, 45, 44, "e"); A.r(29, 44, 44, 44, "l")
    rot = lambda s, n: s[-n % len(s):] + s[:-n % len(s)]
    if mode in ("idle", "lit"):
        body = [rot("pppwwppppwppppp", k * 2), rot("sswwwwsssVVssss", k), "ppppppppppppppp", rot("sVVwswwssswwwss", k * 3), "ppppppppppppppp"]
    elif mode == "take":
        body = (["ppppppppppppppp"] * (k % 2) + ["ppppppwwwpppppp", "ppppwwwwwwwpppp", "pppppwwwwwppppp", "ppppppwwwpppppp"] + ["ppppppppppppppp"] * (1 - k % 2))
    elif work:
        hs = [(2, 4, 1, 5, 3), (3, 5, 2, 4, 1), (5, 3, 4, 2, 2), (4, 1, 5, 3, 4)][k % 4]
        body = ["".join(("p" if 5 - r > h else ("w" if 5 - r == h else "V")) * 2 + "p" for h in hs) for r in range(5)]
    else:
        body = [rot(r, k * 2) for r in ("wwppppwwppppwwp", "pwwppppwwppppww", "ppwwppppwwppppw", "pwwppppwwppppww", "wwppppwwppppwwp")]
    A.rows(30, 37, ["sssssssssssssss"] + body + ["iiiiiiiiiiiiiii"])
    if work or lit_up: glow.append(((30, 37, 44, 43), "x"))
    # ---- the mouth the belt comes out of, three lamps and an arrow over the belt
    for x in range(47, 58):
        for y in (36, 37): A.p(x, y, "n" if ((x + y) // 2) % 2 else "d")
    A.r(47, 38, 57, 44, "c"); A.r(48, 38, 56, 44, "b")
    for x in (49, 51, 53, 55): A.r(x, 38, x, 39 + (0 if mode == "drop" and k % 2 else 1), "m")
    lamps = {"idle": {2} if k != 3 else set(), "lit": {1, 2} if k % 2 else {2}, "take": {1}, "work": {0, 1} if k % 2 else {0}, "drop": {2} if k % 2 == 0 else {1, 2}}[mode]
    for n, (hi, c, off) in enumerate((("M", "R", "Z"), ("W", "n", "y"), ("Y", "E", "U"))):
        x = 61 + 5 * n
        A.rows(x, 38, ["HC", "CC"] if n in lamps else ["OO", "OO"], {"H": hi, "C": c, "O": off}); A.r(x, 40, x + 1, 40, "d")
        if n in lamps: glow.append(((x, 38, x + 1, 39), c))
    go = mode == "drop"
    A.rows(75, 38, ["X.X..", ".X.X.", "X.X.."], {"X": "W" if go and k % 2 == 0 else ("n" if go else "e")})
    soften(A, bulbs, "W", 0.38, 0.12)
    for rect, light in glow: soften(A, [rect], light)
    # ---- the belt, in front and out past its side
    V = Art(); run = mode == "drop"
    V.r(49, 42, 81, 44, "o")
    for x in range(49, 82):
        if (x - (k * 2 if run else 0)) % 4 == 0: V.r(x, 42, x, 44, "B")
    V.r(49, 42, 81, 42, "G")
    V.r(82, 42, 82, 44, "c"); V.r(48, 45, 82, 45, "h"); V.r(48, 46, 82, 46, "e")
    for x in (52, 66, 79): V.r(x, 47, x + 1, 49, "e"); V.r(x + 1, 47, x + 1, 49, "m")
    for i, x in enumerate(range(55, 80, 6)): V.p(x, 46, ("Y" if (i - k) % 2 == 0 else "U") if run else "U")
    if run and k >= 4:                                          # the flap at the end kicks up
        for i in range(4): V.p(79 + i, 41 - i, "R")
        V.p(82, 38, "M")
    else: V.r(79, 41, 82, 41, "R"); V.p(79, 41, "M")
    V.outline("d", ()); A.blit(V.im, -OX, -OY)
    for x in range(49, 57): A.p(x, 41, "b")                     # no line across the dark of the mouth
    # ---- the hopper, in front too: a wide open mouth at a pet's height; it gulps
    Hh = Art(); gulp = mode == "take" and k == 2; y0 = HOP + (1 if gulp else 0)
    dark = "O" if gulp else ("F" if mode == "take" and k == 3 else "C")
    Hh.r(-1, y0, 23, y0, "D"); Hh.r(-2, y0 + 1, 24, y0 + 4, "A"); Hh.r(-1, y0 + 1, 23, y0 + 4, dark); Hh.r(-1, y0 + 1, 23, y0 + 1, "F" if dark == "C" else dark)
    Hh.r(24, y0 + 1, 24, y0 + 4, "F")
    Hh.r(-3, y0 + 5, 25, y0 + 5, "D"); Hh.r(-3, y0 + 6, 25, y0 + 6, "A"); Hh.r(-2, y0 + 7, 24, y0 + 7, "F")
    for i, y in enumerate(range(y0 + 8, 50)):
        xl, xr = -1 + 2 * i, 23 - 2 * i
        Hh.r(xl, y, xr, y, "A"); Hh.r(xl, y, xl + 1, y, "D"); Hh.r(xr - 1, y, xr, y, "F")
    cy = 44 + (1 if gulp else 0); cc = "W" if (mode in ("idle", "lit") and k % 2 == 0) or mode == "take" else "n"
    for dy in (0, 1):
        for x, y in ((9, 0), (13, 0), (10, 1), (12, 1), (11, 2)): Hh.p(x, cy + y + dy, cc)
    Hh.outline("d", ()); A.blit(Hh.im, -OX, -OY)
    if gulp: soften(A, [(-1, y0 + 1, 23, y0 + 4)], "O", 0.45, 0.2)
    A.outline("d", ("d", "m", "b"))
    if mode == "drop" and k == 5: A.p(82, 35, "w"); A.p(81, 36, "j")   # a puff where the belt threw it
    return A.im


def at(x, y): return [x + OX, y + OY]


def sheet_image():
    n = max(MODES.values())
    im = Image.new("RGBA", (CW * n, CH * len(MODES)))
    for j, (mode, frames) in enumerate(MODES.items()):
        for k in range(frames): im.alpha_composite(machine(mode, k), (k * CW, j * CH))
    return im


# ---- the stand-ins: plain pieces the room's other new fixtures start from (their own art may replace them) ----
TERMINAL = ["................", "..############..", ".#cccccccccccc#.", ".#c##########c#.", ".#c#bbbbbbbb#c#.", ".#c#bVbbbbbb#c#.",
            ".#c#bbbbbbbb#c#.", ".#c#bVVVbbbb#c#.", ".#c#bbbbbbbb#c#.", ".#c##########c#.", ".#cccccccccllc#.", "..############..",
            ".....#cccc#.....", "################", "#iiiiiiiiiiiiii#", "#cccccccccccccc#", "#c############c#", "#c#..........#c#",
            "###..........###"]
PLINTH = ["................", "................", "................", "................", "..############..", ".#iiiiiiiiiiii#.",
          ".#cccccccccccc#.", "##############..", "#jjjjjjjjjjjjjj#", "#llllllllllllll#", "#cccccccccccccc#", "################"]
PAD = ["................", "................", "...##########...", "..#nnnnnnnnnn#..", ".#nmnmnmnmnmnn#.", ".#nmbbbbbbbbmn#.", ".#nnbBBBBBBbnn#.",
       ".#nmbBkkkkBbmn#.", ".#nnbBkkkkBbnn#.", ".#nmbBBBBBBbmn#.", ".#nnbbbbbbbbnn#.", ".#nmnmnmnmnmnm#.", "..#nnnnnnnnnn#..", "...##########...",
       "................", "................"]
TICKER = ["#" * 64] + ["#" + "".join("y" if (x + y) % 3 else "W" for x in range(62)) + "#" for y in range(12)] + ["#" * 64]
HUB_ICON = ["................", "..############..", ".#aaaaaaaaaaaa#.", ".#a##########a#.", ".#a#WbWbWbWb#a#.", ".#a##########a#.",
            ".#aaaaaaaaaaaa#.", ".#a#k#k#k#k#a#..", ".#a##########a#.", ".#aDDDDDDaaaaa#.", ".#AAAAAAaaGGGG#.", ".############...",
            "................", "................", "................", "................"]


def typed(rows):
    pal = dict(PD, **{"#": "141b1b"})
    im = Image.new("RGBA", (len(rows[0]), len(rows)))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".": im.putpixel((x, y), col(pal[ch]))
    return im


def sheet():
    s = Sheet("works.png", CW * max(MODES.values()) // 16)
    anims = {mode: {"frames": [[k, j] for k in range(n)], "fps": FPS[mode]} for j, (mode, n) in enumerate(MODES.items())}
    works = {"windows": [[3 + 12 * n + OX + 1, WIN_Y + OY + 1, 11, 11] for n in range(6)], "materials": materials(),
             "hopper": at(11, HOP + 2), "belt": at(50, 41) + at(82, 41), "fps": FPS}
    s.add("fix.vending machine", sheet_image(), frame=[CW, CH], anchor=at(0, 32), anims=anims, works=works)
    s.add("fix.lit sign", typed(TICKER), anchor=[0, 27])
    for name in ("left screen", "middle screen", "right screen"):
        s.add("fix." + name, typed(TERMINAL))
    s.add("decor.plinth", typed(PLINTH), anchor=[0, 0])
    s.add("decor.machine pad", typed(PAD))
    s.add("icon.room.hub", typed(HUB_ICON))
    out = s.save()
    lit = dict(out["fix.vending machine"]); lit["anims"] = dict(lit["anims"], idle=lit["anims"]["lit"])
    out = {"fix.vending machine": out.pop("fix.vending machine"), "fix.vending machine.lit": lit, **out}
    return out


if __name__ == "__main__":
    own = sheet()
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(%s)":' % "|".join(re.escape(n) for n in own), l)]
    at_ = next(i for i, l in enumerate(lines) if l.startswith(' "fix.bed":'))
    lines[at_ + 1:at_ + 1] = [" %s: %s," % (json.dumps(n), json.dumps(e)) for n, e in own.items()]
    open(path, "w").write("\n".join(lines))
    print("drew %d pictures into own/works.png" % len(own))
