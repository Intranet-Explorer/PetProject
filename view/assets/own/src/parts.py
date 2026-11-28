"""The parts library (SPEC-v3.5 §1): the pieces an invented thing is put together from, and the parts of a body.

  uv run --with pillow python view/assets/own/src/parts.py

draws own/parts/*.png and writes what the view needs to draw with them into ../../parts.json: `palette`, each
thing part's `px` (per size: its file and rectangle, a base's `at` points, any other part's `pin`), and `body`.
The names, roles, spots, rules and kinds already in parts.json are kept as they are. Check with engine.check_parts.

Thing parts are shapes, not typed pixels, so that one description gives 16, 24 and 32 pixel pictures with the same
one-pixel line. A shape is given on a 16 x 16 grid (x right, y down); a pixel is in it if its middle is. Each piece
is lit from the upper left by the rule the pets are lit by (view/src/petsprite.ts, shade), then inked all round.
Body parts are a few pixels each and are typed, one character a pixel, at two sizes (s: a body under 10 wide)."""
import json, math, os, re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OWN = os.path.dirname(HERE)
ASSETS = os.path.dirname(OWN)
OUT = os.path.join(OWN, "parts")
# what the view paints: `main` in the part's own colour (a thing's material, a pet's coat), `trim` in a duller
# tone of it (a pet: its pattern's dark and its pale), `glow` left as it is drawn. Dark to light.
PALETTE = {"main": ["8a4a1f", "bf6a2c", "dc9457", "ecc19d"], "trim": ["5b5f6e", "7e8491", "a9afb7", "d3d6d9"], "glow": ["e46d3a", "ffad5d", "ffe18d"],
           "ink": "141b1b", "white": "ffffff", "red": "c4484a"}
SIZES = (16, 24, 32)


def rgba(h):
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def colour(name):
    return rgba(PALETTE[name] if name in ("ink", "white", "red") else PALETTE[name[:-1]][int(name[-1])])


# ---- shapes on the 16 grid ----
rect = lambda x0, y0, x1, y1: lambda u, v: x0 < u < x1 and y0 < v < y1
ell = lambda cx, cy, rx, ry: lambda u, v: ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2 < 1
both = lambda a, b: lambda u, v: a(u, v) and b(u, v)
either = lambda *s: lambda u, v: any(f(u, v) for f in s)
less = lambda a, b: lambda u, v: a(u, v) and not b(u, v)


def poly(*pts):
    def inside(u, v):
        hit = False
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            if (y1 > v) != (y2 > v) and u < x1 + (v - y1) * (x2 - x1) / (y2 - y1):
                hit = not hit
        return hit
    return inside


def line(t, *pts):
    """A stroke t thick along the points."""
    def inside(u, v):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            dx, dy = x2 - x1, y2 - y1
            k = max(0, min(1, ((u - x1) * dx + (v - y1) * dy) / (dx * dx + dy * dy or 1)))
            if math.hypot(u - x1 - k * dx, v - y1 - k * dy) < t / 2:
                return True
        return False
    return inside


class Pic:
    def __init__(self, S):
        self.S, self.px = S, {}   # (x, y) -> a colour's name: "main2", "ink" ...

    def piece(self, inside, region="main", flat=None, sep=False):
        """One lit piece over what is there. `flat`: one tone instead. `sep`: with a line between it and what it lies on."""
        S, k = self.S, 16 / self.S
        pts = {(x, y) for y in range(S) for x in range(S) if inside((x + 0.5) * k, (y + 0.5) * k)}
        if not pts:
            return self
        if sep:
            for (x, y) in pts:
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n in self.px and n not in pts:
                        self.px[n] = "ink"
        x1, x2, y1, y2 = min(x for x, _ in pts), max(x for x, _ in pts), min(y for _, y in pts), max(y for _, y in pts)
        n = len(PALETTE[region])
        for (x, y) in pts:
            u, v = (x - x1) / max(1, x2 - x1), (y - y1) / max(1, y2 - y1)
            under, right, over, left = (x, y + 1) not in pts, (x + 1, y) not in pts, (x, y - 1) not in pts, (x - 1, y) not in pts
            d = u * 0.6 + v
            low = under and v > 0.45   # (the underside of a hole's upper edge is not in shadow)
            lvl = 0 if (low and right) or d > 1.42 else 1 if low or (right and v > 0.3) or d > 1.2 else 3 if d < 0.5 or ((over or left) and u + v < 0.8) else 2
            self.px[(x, y)] = region if isinstance(PALETTE[region], str) else region + str(flat if flat is not None else lvl if n == 4 else (0, 0, 1, 2)[lvl])   # (red, white, ink: one colour)
        return self

    def cut(self, inside):
        k = 16 / self.S
        for p in [p for p in self.px if inside((p[0] + 0.5) * k, (p[1] + 0.5) * k)]:
            del self.px[p]
        return self

    def dot(self, u, v, name):
        """One pixel, whatever the size: a glint."""
        self.px[(int(u * self.S / 16), int(v * self.S / 16))] = name
        return self

    def outline(self):
        for (x, y) in list(self.px):
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in self.px and 0 <= n[0] < self.S and 0 <= n[1] < self.S:
                    self.px[n] = "ink"
        return self

    def each(self, f):
        """A pattern said pixel by pixel (the wraps): f(x, y, S) -> a colour's name or None."""
        for y in range(self.S):
            for x in range(self.S):
                c = f(x, y, self.S)
                if c:
                    self.px[(x, y)] = c
        return self

    # where it is, for pins and spots
    cx = property(lambda self: self.S // 2 - 1)   # the column left of the middle line
    row = lambda self, v: int(v * self.S / 16)
    top = lambda self, x=None: [x if x is not None else self.cx, min(y for (a, y) in self.px if a == (x if x is not None else self.cx))]
    bottom = lambda self, x=None: [x if x is not None else self.cx, max(y for (a, y) in self.px if a == (x if x is not None else self.cx))]
    right = lambda self, v: [max(x for (x, b) in self.px if b == self.row(v)), self.row(v)]
    left = lambda self, v: [min(x for (x, b) in self.px if b == self.row(v)), self.row(v)]
    mid = lambda self, v: [self.cx, self.row(v)]

    def image(self):
        im = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        for p, name in self.px.items():
            im.putpixel(p, colour(name))
        return im


# ---- the thing parts: name -> f(S) -> (Pic, {"at": {...}} for a base or {"pin": [x, y]} for any other) ----
THING = {}


def part(name):
    def add(f):
        THING[name] = f
        return f
    return add


def base_points(p, face, side, **more):
    """Where things go on a base. `face`: the middle of its body, where a wrap is centred. `inside`: a part put inside
    is drawn behind the base with its foot here, so it shows over the rim or through the hole."""
    return {"at": dict({"top": p.top(), "tip": p.top(), "base": p.bottom(), "side": p.right(side), "face": p.mid(face)}, **more)}


def sill(p, v):
    """The bottom of a hole, down from row v in the middle: where something inside it stands."""
    return [p.cx, min(y for (x, y) in p.px if x == p.cx and y > p.row(v) and (x, y - 1) not in p.px)]


@part("stick")
def _(S):
    p = Pic(S).piece(rect(7, 9, 9, 15)).outline()   # short: what it carries is the thing
    return p, base_points(p, 12, 12)


@part("bowl")
def _(S):
    p = Pic(S).piece(either(both(ell(8, 9, 5.5, 5.7), rect(0, 9, 16, 16)), rect(6, 13, 10, 15)))
    p.piece(ell(8, 9.8, 4.3, 0.95), flat=0).outline()   # the dark of its opening
    return p, base_points(p, 12.5, 11.5, inside=[p.cx, p.top()[1] + p.row(2.2)])


@part("box")
def _(S):
    p = Pic(S).piece(rect(3, 10, 13, 15)).piece(rect(3, 8, 13, 10), flat=3).outline()
    return p, base_points(p, 12.5, 12.5, inside=[p.cx, p.top()[1] + p.row(2.2)])


@part("disc")
def _(S):
    p = Pic(S).piece(ell(8, 12, 5, 2.7)).outline()
    return p, {"at": dict(base_points(p, 12, 12)["at"], top=p.mid(11.5))}   # things stand on it


@part("ring")
def _(S):
    p = Pic(S).piece(less(ell(8, 11.5, 3.65, 3.65), ell(8, 11.5, 1.9, 1.9))).outline()
    return p, base_points(p, 11.5, 11.5, inside=sill(p, 11.5))


@part("frame")
def _(S):
    p = Pic(S).piece(less(rect(3, 8, 13, 15), rect(4.2, 9.2, 11.8, 13.8))).outline()
    return p, base_points(p, 11.5, 11.5, inside=sill(p, 11.5))


@part("cushion")
def _(S):
    p = Pic(S).piece(lambda u, v: ((u - 8) / 5.5) ** 4 + ((v - 12.6) / 2.45) ** 4 < 1)
    p.dot(7.5, 12.5, "main1").outline()   # the dimple a button makes
    return p, base_points(p, 12.5, 12.5)


@part("block")
def _(S):
    p = Pic(S).piece(either(rect(3.5, 9.6, 12.5, 13.6), ell(8, 13.4, 4.5, 1.7))).piece(ell(8, 9.6, 4.5, 1.75), flat=3).outline()
    return p, base_points(p, 12.5, 12.5)


@part("bundle")
def _(S):
    p = Pic(S).piece(poly((4.8, 8), (11.2, 8), (9.3, 11.4), (11.6, 15), (4.4, 15), (6.7, 11.4)))
    p.piece(rect(6, 10.4, 10, 12.4), "trim").outline()   # what ties it
    return p, base_points(p, 11.4, 11.4)


def top(p, pin=None):
    return p, {"pin": pin or p.bottom()}


@part("flame")
def _(S):
    p = Pic(S).piece(either(ell(8, 12.7, 2.05, 2.3), poly((8.7, 10.1), (6.2, 12.6), (9.8, 12.6))), "glow")
    p.piece(ell(8, 13.3, 1.05, 1.5), "glow", flat=2).dot(7.6, 13.6, "white").outline()
    return top(p)


@part("blade")
def _(S):
    p = Pic(S).piece(poly((7, 9.2), (7.6, 9.2), (10.2, 12.4), (10.2, 13.6), (9, 15), (7, 15)))   # a straight back, a curved edge
    return top(p.dot(7.5, 11.5, "white").outline())


@part("tines")
def _(S):
    p = Pic(S).piece(either(rect(4, 13, 12, 15), rect(4, 10, 5, 14), rect(7, 10, 9, 14), rect(11, 10, 12, 14))).outline()
    return p, {"pin": p.bottom(), "at": {"tip": [p.cx, p.row(13)]}}   # a flame given the same tip stands in the fork (EXTRA: carries)


@part("spade")
def _(S):   # flat and broad, its edge rounded: nothing like the blade
    p = Pic(S).piece(poly((4.8, 9), (11.2, 9), (11.2, 12), (9, 14.9), (7, 14.9), (4.8, 12))).piece(rect(7.5, 9.5, 8.5, 13), flat=3)   # a square edge, shoulders, a rib
    return top(p.dot(5.6, 9.6, "white").outline())


@part("bell dome")
def _(S):
    p = Pic(S).piece(either(both(ell(8, 13.4, 2.45, 3.9), rect(0, 0, 16, 13)), rect(4, 13, 12, 14))).piece(rect(7, 14, 9, 15), "trim", flat=1)   # its dome, its lip, its clapper
    p.dot(6.6, 11.6, "white").outline()
    return top(p)


@part("lid")
def _(S):
    p = Pic(S).piece(either(both(ell(8, 15.2, 5.3, 2.6), rect(0, 0, 16, 15)), rect(7, 11.5, 9, 13))).outline()
    return top(p)


@part("spout")
def _(S):   # what makes a pot a watering can: a spout rising from low on its side, and a handle arched over its top
    p = Pic(S).piece(line(1.0, (3, 9.8), (3.6, 7.4), (5.5, 6.2), (7.5, 6.2), (9.4, 7.4), (10, 9.8)), "trim")
    p.piece(poly((10, 11.5), (11.8, 11.5), (14.6, 8.8), (14.95, 9.9), (12.6, 14.4), (10, 14.4))).outline()
    return top(p, [int(11 * S / 16), p.row(12.5)])   # its root lies over the pot's side


@part("strings")
def _(S):
    p = Pic(S)
    for x in (6, 8, 10):
        p.piece(rect(x, 9, x + 1, 14), "trim", flat=3)
    p.piece(rect(5.2, 8, 11.8, 9), "trim", flat=0).piece(rect(5.2, 14, 11.8, 15), "trim", flat=0)
    return top(p, p.mid(11.5))


@part("wheel")
def _(S):
    p = Pic(S)
    for x in (4, 12):   # two dark tyres, each with a pale hub
        p.piece(ell(x, 13, 1.95, 1.95), flat=1).piece(ell(x, 13, 0.8, 0.8), "trim", flat=3)
    p.outline()
    return top(p, [p.cx, p.row(12.2)])   # low on its corners, most of each wheel under it


@part("hook")
def _(S):
    p = Pic(S).piece(line(1.05, (7.5, 14.6), (7.5, 12.6), (9.5, 11.6), (9.5, 10.6), (8.5, 9.9), (7.2, 9.9), (6.3, 10.9)), "trim").outline()
    return top(p)


@part("flower")
def _(S):
    p = Pic(S)
    p.piece(ell(8, 12, 3.3, 2.2), flat=1).piece(either(rect(7, 10, 9, 14), rect(5, 11, 11, 13)), flat=3)   # four light petals round a yellow middle, on a bit of stem
    p.piece(rect(7, 11, 9, 13), "glow", flat=2).piece(rect(7, 14, 9, 15), "trim", flat=0).outline()
    return top(p)


@part("gem")
def _(S):
    p = Pic(S).piece(poly((6, 10), (10, 10), (11.2, 11.6), (8, 14.9), (4.8, 11.6))).dot(6.6, 10.6, "white").outline()
    return top(p)


@part("sail")
def _(S):
    p = Pic(S).piece(rect(7, 9, 8, 15), "trim", flat=1).piece(poly((8.2, 9.1), (8.2, 13.4), (12.8, 13.4))).piece(poly((6.8, 10.4), (6.8, 13.4), (4.2, 13.4)))   # a mast, a mainsail and a jib
    return top(p.outline())


@part("chimes")
def _(S):   # three tubes of three lengths; they hang under what holds them (EXTRA: to), their tops over its foot
    p = Pic(S)
    for x, y in ((4, 14), (7, 15), (10, 13)):
        p.piece(rect(x, 9, x + 2, y))
    p.outline()
    return top(p, [p.cx, p.row(10)])


@part("pad")
def _(S):   # a cushion to go on something: thick, soft at the corners, tufted
    p = Pic(S).piece(lambda u, v: ((u - 8) / 5.3) ** 4 + ((v - 13.1) / 2.05) ** 4 < 1)
    return top(p.dot(5.5, 13.5, "main1").dot(10.5, 13.5, "main1").outline())


@part("seeds")
def _(S):   # a heap, speckled; put inside a bowl it shows over the rim
    p = Pic(S).piece(both(ell(8, 13, 4.5, 4.1), rect(0, 0, 16, 13)))
    for (x, y) in list(p.px):
        p.px[(x, y)] = "glow2" if (x * 3 + y * 5) % 7 == 0 else "main0" if (x * 5 + y * 3) % 7 == 3 else p.px[(x, y)]
    p.outline()
    return top(p, [p.cx, min(S - 1, p.bottom()[1] + round(2 * S / 16))])


@part("head")
def _(S):
    p = Pic(S).piece(rect(4, 10.6, 12, 14)).piece(rect(4, 10.6, 5.6, 14), "trim").outline()
    return top(p)


def wrap(f, rows):
    """A pattern as wide as the picture, `rows` of it high on the 16 grid, about the middle row. It is painted only on
    the base's own body (parts.json: `clip`), so it needs no line of its own."""
    def make(S):
        k, p = S / 16, Pic(S)
        y0, y1 = round(S / 2 - rows * k / 2), round(S / 2 + rows * k / 2)
        p.each(lambda x, y, S: f(x, y - y0, y1 - y0) if y0 <= y < y1 else None)
        return p, {"pin": [p.cx, (y0 + y1) // 2]}
    return make


THING["cord"] = wrap(lambda x, y, n: "main%d" % (3 if (x + y) % 2 else 1), 2)                       # a twist
THING["band"] = wrap(lambda x, y, n: "main%d" % (3 if y == 0 else 1 if y == n - 1 else 2), 2.4)
THING["studs"] = wrap(lambda x, y, n: ("trim3" if y < n - 1 else "trim0") if x % (n + 1) < max(1, n // 2) else None, 2)


def cloth(S):   # draped: it hangs from its pin, with a scalloped hem
    k, p = S / 16, Pic(S)
    y0, n = round(S / 2), round(4.2 * k)
    p.each(lambda x, y, S: None if not y0 <= y < y0 + n or (y == y0 + n - 1 and (x // max(1, round(k))) % 3 == 0)
           else "main%d" % (3 if y == y0 else 1 if y >= y0 + n - 2 and (x // max(1, round(k))) % 3 == 2 else 2))
    return p, {"pin": [p.cx, y0]}


THING["cloth"] = cloth
THING["weave"] = wrap(lambda x, y, n: "main%d" % (3 if (x // 2 + y // 2) % 2 else 2), 16)          # the whole of it, woven


# ---- SPEC-v3.6d §3: the parts a design is made of (up to five: a base and four on its spots). Drawn bigger than the
# first library's, so that a whole design reads at 24 pixels: a base stands about ten of the grid's sixteen high, what
# goes on it four to six. A part on a `side` mostly has its pin at its left (it sticks out to the right of the base);
# on a `base`, at its top (it hangs under). Shapes are named for what they are. ----
def points(p, face, sv, **over):
    """base_points, any of whose points (side too) may be given."""
    out = base_points(p, face, sv)
    out["at"].update(over)
    return out


def at(p, x, v):
    """A point: column x (on the 16 grid) at row v."""
    return [int(x * p.S / 16), p.row(v)]


def lowest(p, x):
    """The lowest drawn pixel in column x (16 grid)."""
    c = int(x * p.S / 16)
    return [c, max(y for (a, y) in p.px if a == c)]


def highest(p, x):
    c = int(x * p.S / 16)
    return [c, min(y for (a, y) in p.px if a == c)]


def edge(p, v):
    """The rightmost pixel of row v."""
    return p.right(v)


@part("tube")
def _(S):   # lying on its side, open at the right: the tip is its mouth, things there stand on its lower lip
    p = Pic(S).piece(either(rect(2, 9.6, 12.6, 14.4), ell(2.2, 12, 1.2, 2.4)))
    p.piece(rect(4.5, 9.6, 5.6, 14.4), flat=1).piece(ell(12.6, 12, 1.25, 2.4), flat=3).piece(ell(12.6, 12, 0.6, 1.5), flat=0).outline()
    return p, points(p, 12, 12, tip=lowest(p, 12.6), top=highest(p, 8), side=highest(p, 6), inside=at(p, 8, 12))


@part("pole")
def _(S):   # long and thin, upright: the tip is its top (under eight high: what goes on its tip has six)
    p = Pic(S).piece(rect(7.1, 7.6, 8.9, 15.2)).piece(rect(7.1, 13.2, 8.9, 14), flat=1).outline()
    return p, points(p, 10.6, 11.6)


@part("handle")
def _(S):   # a grip that swells a little, with a collar at its top
    p = Pic(S).piece(either(ell(8, 13, 1.5, 2.4), rect(6.8, 10.4, 9.2, 13))).piece(rect(6.2, 9.4, 9.8, 10.6), "trim", flat=2).outline()
    return p, points(p, 12.6, 12)


@part("bar")
def _(S):   # square-ended, upright, with a bolt near each end
    p = Pic(S).piece(rect(6.6, 7.6, 9.4, 15.2)).dot(8, 9, "trim0").dot(8, 13.6, "trim0").outline()
    return p, points(p, 11, 10)


@part("pipe")
def _(S):   # upright, with a mouthpiece at its top and three finger holes
    p = Pic(S).piece(rect(6.9, 7.4, 9.1, 15.2)).piece(rect(6.5, 7, 9.5, 8.4), "trim", flat=2)
    for v in (10, 12, 14):
        p.dot(7.6, v, "main0")
    return p.outline(), points(p, 11, 11, inside=at(p, 7.6, 12))


@part("tank")
def _(S):   # an upright tank in two rounded halves (a groove down its middle), a seam round its foot
    p = Pic(S).piece(either(rect(3.6, 11, 12.4, 15.2), ell(5.8, 11, 2.2, 2.2), ell(10.2, 11, 2.2, 2.2))).piece(rect(3.6, 13.8, 12.4, 14.6), "trim", flat=1)
    p.piece(rect(4.4, 10.4, 5.2, 13.6), flat=3).piece(rect(8.8, 10.4, 9.6, 13.6), flat=3).piece(rect(7.6, 10.2, 8.4, 15.2), flat=0).outline()
    return p, points(p, 12.4, 12, inside=at(p, 8, 12), top=highest(p, 5.8))


@part("jar")
def _(S):   # squat, a wide mouth with a lip
    p = Pic(S).piece(either(ell(8, 12.4, 4.3, 3), rect(4.5, 12, 11.5, 15))).piece(rect(5, 8.6, 11, 10.4), flat=3)
    p.piece(ell(8, 9.4, 2.2, 0.55), flat=0).dot(5.5, 12, "white").outline()
    return p, points(p, 12.5, 12.5, inside=at(p, 8, 9.6))


@part("cup")
def _(S):   # a mug: straight sides, a loop of handle at the right
    p = Pic(S).piece(less(ell(12.2, 12, 2.1, 2.1), ell(12.2, 12, 1, 1)), "main").piece(rect(4, 9, 11, 15)).piece(ell(7.5, 9.4, 3.2, 0.6), flat=0).outline()
    return p, points(p, 12, 10.5, side=at(p, 11, 10.5), inside=at(p, 7.5, 9.6))


@part("pot")
def _(S):   # round-bellied, with a rolled rim and two ear handles
    p = Pic(S).piece(either(both(ell(8, 12, 4.8, 3.6), rect(0, 10, 16, 16)), rect(5, 14.5, 11, 15.3)))
    p.piece(rect(3.6, 9.4, 12.4, 10.8), "trim", flat=2).piece(rect(2.2, 11, 3.6, 12.2), "trim", flat=1).piece(rect(12.4, 11, 13.8, 12.2), "trim", flat=1).outline()
    return p, points(p, 13, 12.6, inside=at(p, 8, 10), side=at(p, 12, 12.6))


@part("plate")
def _(S):   # flat and round, seen a little from above: a rim round a well
    p = Pic(S).piece(ell(8, 13, 6.2, 2.1)).piece(ell(8, 12.9, 3.8, 1.1), flat=1).outline()
    return p, {"at": dict(points(p, 13, 13)["at"], top=at(p, 8, 13.6))}


@part("barrel")
def _(S):   # staves bulging between two dark hoops
    p = Pic(S).piece(lambda u, v: abs(u - 8) < 4.2 - ((v - 11.6) / 3.6) ** 2 * 1.2 and 8 < v < 15.3)
    p.piece(rect(3, 9.4, 13, 10.4), "trim", flat=0).piece(rect(3, 13, 13, 14), "trim", flat=0).piece(rect(7.6, 8, 8.4, 15.3), flat=1)
    return p.outline(), points(p, 11.7, 11.7, inside=at(p, 8, 9.2))


@part("basket")
def _(S):   # open and woven, wider at its mouth
    p = Pic(S).piece(poly((3, 9.4), (13, 9.4), (11.6, 15.2), (4.4, 15.2)))
    for (x, y) in list(p.px):
        if (x // max(1, S // 8) + y // max(1, S // 8)) % 2 and p.px[(x, y)] != "main3":
            p.px[(x, y)] = "main1"
    p.piece(rect(2.6, 8.6, 13.4, 10), flat=3).outline()
    return p, points(p, 12.5, 12.5, inside=at(p, 8, 9.6))


@part("bucket")
def _(S):   # tapering, banded at its rim, a hoop handle over it
    p = Pic(S).piece(less(ell(8, 10.6, 4.6, 3.4), ell(8, 10.6, 3.8, 2.6)), "trim", flat=1).cut(rect(0, 10.6, 16, 16))
    p.piece(poly((3.8, 10.6), (12.2, 10.6), (11.2, 15.2), (4.8, 15.2)), sep=True).piece(rect(3.8, 10.6, 12.2, 11.6), "trim", flat=2).outline()
    return p, points(p, 13, 13, inside=at(p, 8, 11), top=at(p, 8, 7.2))


@part("bottle")
def _(S):   # narrow-necked, the neck at the tip
    p = Pic(S).piece(either(ell(8, 12.4, 3, 3), rect(5, 12.4, 11, 15.2), rect(7, 7.4, 9, 11))).piece(rect(6.6, 6.8, 9.4, 8), flat=3)
    p.dot(6.2, 12, "white").dot(6.2, 13, "white").outline()
    return p, points(p, 13, 12.4, inside=at(p, 8, 12))


@part("dome")
def _(S):   # a bell jar: clear glass on a round wooden foot
    p = Pic(S).piece(either(both(ell(8, 11.6, 3.6, 4.2), rect(0, 0, 16, 13.8)), rect(4.4, 11, 11.6, 13.8)), "trim", flat=3)
    p.piece(ell(8, 11.6, 2.6, 3.2), "trim", flat=2).piece(rect(7.4, 6.8, 8.6, 7.8), "trim", flat=1).dot(5.8, 10, "white").dot(5.8, 11, "white").dot(6.2, 9, "white")
    p.piece(rect(3.2, 13.8, 12.8, 15.2), sep=True).outline()
    return p, points(p, 12, 11, inside=at(p, 8, 13.4))


@part("cage")
def _(S):   # a round cage of thin bars on a base, a ring on top
    k = max(1, round(S / 16))
    p = Pic(S).piece(less(ell(8, 10.8, 3.8, 3.8), ell(8, 10.8, 3.8 - 1.1 / k, 3.8 - 1.1 / k)), "trim", flat=1)
    for x in (5.6, 8, 10.4):
        p.piece(both(rect(x - 0.45, 6, x + 0.45, 14), ell(8, 10.8, 3.8, 3.8)), "trim", flat=2)
    p.piece(rect(3.8, 13.8, 12.2, 15.2), "trim", flat=1).piece(less(ell(8, 6.4, 1.1, 1.1), ell(8, 6.4, 0.45, 0.45)), "trim", flat=2).outline()
    return p, points(p, 11, 10.8, inside=at(p, 8, 13.6), top=highest(p, 8))


@part("firebox")
def _(S):   # a squat iron box, a grate door at the front
    p = Pic(S).piece(rect(3, 9, 13, 15.2)).piece(rect(2.6, 8.2, 13.4, 9.4), flat=3)
    p.piece(rect(5, 10.6, 11, 14), "trim", flat=0)
    for x in (6.4, 8, 9.6):
        p.piece(rect(x - 0.4, 10.6, x + 0.4, 14), "trim", flat=2)
    return p.outline(), points(p, 12, 12, inside=at(p, 8, 13.6))


@part("hull")
def _(S):   # a little boat from the side: pointed at the front (right), a rail along its top
    p = Pic(S).piece(poly((2.4, 10.2), (14, 9.6), (11.8, 14.4), (4, 14.4))).piece(rect(2.4, 10.2, 13.4, 11.2), flat=3).piece(rect(3.4, 12.4, 12.4, 13), flat=1).outline()
    return p, points(p, 12, 11, inside=at(p, 8, 10.2), top=at(p, 8, 10), side=at(p, 8, 11.6))   # (an oar over its side goes down into the water)


@part("plank")
def _(S):   # a board lying across, its grain showing
    p = Pic(S).piece(rect(2.6, 11.4, 13.4, 13.6)).piece(rect(4.4, 12.3, 8.6, 12.9), flat=1).piece(rect(10, 12.3, 12.4, 12.9), flat=1).outline()
    return p, points(p, 12.5, 12.5, tip=edge(p, 12.5), side=at(p, 11, 12.4))


@part("stand")
def _(S):   # a tripod with a flat round top
    p = Pic(S).piece(line(1.2, (8, 11.4), (4, 15))).piece(line(1.2, (8, 11.4), (12, 15))).piece(rect(7.3, 11.4, 8.7, 15.2), flat=1)
    p.piece(ell(8, 11, 4, 1.1), flat=3).outline()
    return p, points(p, 12, 12)


@part("ladder")
def _(S):   # two rails and four rungs
    p = Pic(S)
    for v in (8.4, 10.6, 12.6, 14.4):
        p.piece(rect(5.5, v, 10.5, v + 0.8), flat=1)
    p.piece(rect(4.4, 7.4, 5.6, 15.2)).piece(rect(10.4, 7.4, 11.6, 15.2)).outline()
    return p, points(p, 11, 9.6, tip=highest(p, 5))


# -- what goes on a base (SPEC-v3.6d §3) --
def pin_left(p, v):
    """Its leftmost pixel in row v: where a part that sticks out to the right is fixed."""
    return p.left(v)


@part("point")
def _(S):   # a spearhead: a leaf of a blade on a socket
    p = Pic(S).piece(poly((8, 9), (10, 12), (8.9, 13.6), (7.1, 13.6), (6, 12))).piece(poly((8, 9.2), (8, 13.4), (9.6, 12)), flat=1)
    p.piece(rect(7.2, 13.6, 8.8, 15.2), "trim", flat=1).dot(7.2, 11.6, "white").outline()
    return top(p)


@part("saw")
def _(S):   # a straight blade up from a grip, teeth down its right edge
    p = Pic(S).piece(lambda u, v: 6.4 < u < 9.4 + (1 - (v - 8.4) % 1.6 / 1.6) * 1.8 and 8.4 < v < 13.4).piece(rect(6, 13.2, 10, 15.2), "trim", flat=1)
    return top(p.dot(7.4, 9.6, "white").outline())


@part("axe head")
def _(S):   # a socket round what holds it, the wedge out to the right with a bright curved edge
    p = Pic(S).piece(poly((8.6, 10), (12, 8), (13, 11.2), (12, 14.4), (8.6, 12.6))).piece(line(0.9, (12.2, 8.4), (12.8, 11.2), (12.2, 14)), flat=3)
    p.piece(rect(6.4, 9, 8.8, 13.6), "trim", flat=1).outline()
    return top(p, lowest(p, 7.6))


@part("scoop")
def _(S):   # a deep round bowl on a short neck
    p = Pic(S).piece(both(ell(8, 9, 3.4, 3.4), rect(0, 9, 16, 16))).piece(ell(8, 9.2, 3.2, 0.7), flat=0).piece(rect(7.3, 12, 8.7, 15.2), "trim", flat=1).outline()
    return top(p)


@part("needle")
def _(S):   # long and thin, an eye at its top
    p = Pic(S).piece(less(either(rect(7.4, 9, 8.6, 14), poly((7.4, 14), (8.6, 14), (8, 15.4))), rect(7.8, 9.6, 8.2, 10.8)), "trim", flat=2).outline()
    return top(p)


@part("claw")
def _(S):   # three fingers, open, on a wrist
    p = Pic(S).piece(rect(7, 13.6, 9, 15.2), "trim", flat=1).piece(rect(4.8, 12.6, 11.2, 13.8), "trim", flat=2)
    for path in (((5.4, 12.8), (4.6, 11.2), (5.6, 9.8)), ((8, 12.8), (8, 9.6)), ((10.6, 12.8), (11.4, 11.2), (10.4, 9.8))):
        p.piece(line(1.1, *path), "trim", flat=2)
    return top(p.outline())


@part("lens")
def _(S):   # a round glass in a thin rim, seen a little from the side, catching the light
    p = Pic(S).piece(ell(8, 11.6, 2.4, 3.6)).piece(ell(8.2, 11.6, 1.6, 2.8), "trim", flat=3).piece(ell(8.6, 12.2, 0.9, 1.8), "trim", flat=2)
    return top(p.dot(7.6, 10, "white").dot(7.6, 10.8, "white").outline())


@part("bulb")
def _(S):   # a round glass bulb on a little screw neck, a filament in it
    p = Pic(S).piece(ell(8, 11, 2.6, 2.6), "trim", flat=3).piece(rect(6.9, 13, 9.1, 15.2), "trim", flat=1).piece(rect(6.9, 13.8, 9.1, 14.3), "trim", flat=0)
    p.piece(line(0.8, (7.1, 12.2), (7.5, 10.6), (8.5, 10.6), (8.9, 12.2)), "glow", flat=1).dot(6.8, 9.8, "white").outline()
    return top(p)


@part("wick")
def _(S):   # a twisted wick in a dab of wax
    p = Pic(S).piece(ell(8, 14.4, 2.4, 0.9), flat=3).piece(line(0.9, (8, 14), (8.3, 12.4), (7.7, 11.2), (8.1, 10)), "trim", flat=0)
    return p.outline(), {"pin": p.bottom(), "at": {"tip": highest(p, 8)}}


@part("candle")
def _(S):   # a short stubby candle, unlit, wax run down its side
    p = Pic(S).piece(rect(6.4, 11.4, 9.6, 15.2), flat=3).piece(rect(6.4, 12, 7.3, 13.6), flat=2).piece(rect(7.7, 10.2, 8.3, 11.4), "trim", flat=0)
    return p.outline(), {"pin": p.bottom(), "at": {"tip": highest(p, 8)}}   # a flame given its tip after stands on its wick (EXTRA: carries)


@part("ember")
def _(S):   # a few glowing coals
    p = Pic(S)
    for x, y, r in ((6, 13.6, 1.7), (10, 13.6, 1.7), (8, 12, 1.7)):
        p.piece(ell(x, y, r, r * 0.85), "glow")
    p.dot(6, 13.4, "glow2").dot(8, 11.8, "glow2").dot(10.4, 13.8, "red")
    return top(p.outline())


@part("glow stone")
def _(S):   # a smooth stone, glowing
    p = Pic(S).piece(ell(8, 12.4, 3, 2.7), "glow").piece(ell(7.6, 12, 1.6, 1.4), "glow", flat=2).dot(6.8, 11.2, "white")
    return top(p.outline())


@part("fireflies")
def _(S):   # four little lights
    p = Pic(S)
    for x, y in ((5.5, 13), (8.5, 10.5), (10.6, 13.6), (7.4, 14.6)):
        p.piece(ell(x, y, 1.05, 1.05), "glow", flat=2)
    return top(p.outline(), at(p, 7.4, 15.2))


@part("mirror")
def _(S):   # a round glass in a frame, a bright streak across it
    p = Pic(S).piece(ell(8, 11.4, 3.4, 3.6)).piece(ell(8, 11.4, 2.5, 2.7), "trim", flat=3).piece(rect(7.2, 14.8, 8.8, 15.4), flat=1)
    p.piece(line(0.8, (6.4, 12.4), (8.6, 10)), "white").outline()
    return top(p)


@part("lamp shade")
def _(S):   # a cone shade, wide at the bottom, sitting by its rim on what holds it; a light given its tip after hangs in its mouth (EXTRA: carries)
    p = Pic(S).piece(poly((6.6, 9), (9.4, 9), (12.6, 12.8), (3.4, 12.8))).piece(rect(3.2, 12.2, 12.8, 13.2), flat=1).piece(rect(7.4, 8, 8.6, 9.2), "trim", flat=1).outline()
    return p, {"pin": [p.cx, p.row(12.6)], "at": {"tip": [p.cx, p.row(15.4)]}}


@part("cork")
def _(S):   # a stopper, slightly tapering
    p = Pic(S).piece(poly((6, 11.6), (10, 11.6), (9.5, 15.2), (6.5, 15.2))).dot(7, 13, "main0").dot(9, 14, "main0").outline()
    return top(p)


@part("nozzle")
def _(S):   # a tapering metal nozzle with a narrow mouth
    p = Pic(S).piece(poly((6, 15.2), (10, 15.2), (8.8, 11), (7.2, 11)), "trim", flat=2).piece(rect(6.8, 10.2, 9.2, 11.2), "trim", flat=1).outline()
    return top(p)


@part("valve")
def _(S):   # a round spoked wheel on a stem
    p = Pic(S).piece(less(ell(8, 11.6, 2.4, 2.4), ell(8, 11.6, 1.4, 1.4)), "red").piece(rect(7.4, 9.4, 8.6, 13.8), "red").piece(rect(5.8, 11, 10.2, 12.2), "red")
    p.piece(rect(7.2, 13.8, 8.8, 15.2), "trim", flat=1).outline()
    return top(p)


@part("tap")
def _(S):   # a spigot: out to the right and down, a turn handle on its top
    p = Pic(S).piece(either(rect(5.6, 11.4, 10, 13), rect(8.4, 12, 10, 14.6)), "trim", flat=2).piece(rect(7, 9.8, 8.2, 11.4), "trim", flat=1).piece(rect(5.8, 9, 9.4, 10), "red").outline()
    return top(p, pin_left(p, 12.2))


@part("bellows")
def _(S):   # pleated, a handle at its back and a nose to the right
    p = Pic(S).piece(poly((5, 10.2), (9.6, 11), (9.6, 13.4), (5, 14.2))).piece(rect(9.6, 11.6, 11.8, 12.6), "trim", flat=1)
    for x in (6.2, 7.8):
        p.piece(rect(x, 10.6, x + 0.6, 13.8), flat=0)
    p.piece(rect(3.4, 11.4, 5, 13), "trim", flat=1).outline()
    return top(p, pin_left(p, 12.2))


@part("gear")
def _(S):   # a toothed cog, a hole at its middle
    import math as m
    p = Pic(S).piece(lambda u, v: (lambda r, a: r < 2.9 or (r < 3.9 and m.cos(a * 8) > 0))(m.hypot(u - 8, v - 11.6), m.atan2(v - 11.6, u - 8)), "glow", flat=0)
    p.piece(ell(8, 11.6, 2.2, 2.2), "glow", flat=1).cut(ell(8, 11.6, 0.9, 0.9)).outline()
    return top(p, at(p, 8, 11.6))   # its middle on the spot: half of it shows past a side


@part("spring")
def _(S):   # a coil hanging from its top
    p = Pic(S)
    p.piece(line(1, (5.4, 8.6), (10.6, 9.8), (5.4, 11), (10.6, 12.2), (5.4, 13.4), (10.6, 14.6)), "trim", flat=2)
    return top(p.outline(), highest(p, 8))


@part("axle")
def _(S):   # a bare rod across with a hub at each end
    p = Pic(S).piece(rect(3, 9.4, 13, 10.6), "trim", flat=1).piece(rect(1.6, 8.6, 3.2, 11.4), "trim", flat=2).piece(rect(12.8, 8.6, 14.4, 11.4), "trim", flat=2).outline()
    return top(p, highest(p, 8))


@part("pulley")
def _(S):   # a grooved wheel in a bracket, a rope over it hanging down both sides
    p = Pic(S).piece(rect(7.5, 13.2, 8.5, 15.2), "trim", flat=1).piece(less(ell(8, 10.4, 2.6, 2.6), ell(8, 10.4, 1, 1)), "trim", flat=2)
    p.piece(rect(5, 10.4, 5.8, 14.6), "main").piece(rect(10.2, 10.4, 11, 14.6), "main").outline()
    return top(p)


@part("crank")
def _(S):   # a bent crank: out, up, a knob
    p = Pic(S).piece(line(1.1, (6.8, 13.2), (8.4, 13.2), (8.4, 11), (9.2, 11)), "trim", flat=2).piece(ell(9.8, 11, 1.1, 1.1), "red").outline()
    return top(p, pin_left(p, 13.2))


@part("hinge")
def _(S):   # two leaves on a pin, half open
    p = Pic(S).piece(rect(6.6, 10.6, 8, 13.6), "trim", flat=2).piece(poly((8.6, 10.6), (10.4, 9.8), (10.4, 12.6), (8.6, 13.6)), "trim", flat=1).piece(rect(7.8, 10, 8.8, 14.2), "trim", flat=3)
    p.dot(7.2, 12, "trim0").outline()
    return top(p, pin_left(p, 12))


@part("propeller")
def _(S):   # two blades on a hub, on a short shaft
    p = Pic(S).piece(ell(4.6, 10, 3.2, 1.1)).piece(ell(11.4, 10, 3.2, 1.1)).piece(rect(7.4, 10.6, 8.6, 15.2), "trim", flat=1).piece(ell(8, 10, 1.3, 1.3), "trim", flat=2)
    return top(p.outline())


@part("paddle wheel")
def _(S):   # flat blades round a hub
    p = Pic(S).piece(less(ell(8, 11.6, 3, 3), ell(8, 11.6, 2.1, 2.1)), "trim", flat=1)
    for a in range(0, 360, 45):
        r = math.radians(a)
        p.piece(line(1.2, (8 + math.cos(r) * 2.4, 11.6 + math.sin(r) * 2.4), (8 + math.cos(r) * 4, 11.6 + math.sin(r) * 4)))
    p.piece(ell(8, 11.6, 0.9, 0.9), "trim", flat=2).outline()
    return top(p, at(p, 8, 11.6))


@part("wind-up key")
def _(S):   # a stem out to the right and a looped bow of a handle
    p = Pic(S).piece(rect(5.6, 11.6, 8.2, 12.4), "glow", flat=0).piece(less(ell(9, 10.4, 1.3, 1.7), ell(9, 10.4, 0.5, 0.8)), "glow", flat=1).piece(less(ell(9, 13.6, 1.3, 1.7), ell(9, 13.6, 0.5, 0.8)), "glow", flat=1)
    return top(p.outline(), pin_left(p, 12))


@part("lever")
def _(S):   # a rod up from a pivot, a red knob on it
    p = Pic(S).piece(ell(8, 14.4, 2.2, 1), "trim", flat=1).piece(line(1, (8, 14), (10, 8.6)), "trim", flat=2).piece(ell(10.2, 8.2, 1.4, 1.4), "red")
    return top(p.outline())


@part("magnet")
def _(S):   # a red horseshoe, its grey ends down
    p = Pic(S).piece(less(both(ell(8, 10.6, 3.8, 3.8), rect(0, 0, 16, 11)), ell(8, 10.6, 1.8, 1.8)), "red").piece(rect(4.2, 10.6, 6.2, 13), "red").piece(rect(9.8, 10.6, 11.8, 13), "red")
    p.piece(rect(4.2, 13, 6.2, 15), "trim", flat=3).piece(rect(9.8, 13, 11.8, 15), "trim", flat=3)
    return top(p.outline(), at(p, 8, 15))


@part("runners")
def _(S):   # two long runners under it, curled up at the front
    p = Pic(S).piece(line(1.1, (2, 13.6), (12.6, 13.6), (14, 12.6), (14, 11.4))).piece(rect(4.4, 9.4, 5.6, 13.4), "trim", flat=1).piece(rect(10.4, 9.4, 11.6, 13.4), "trim", flat=1)
    return top(p.outline(), at(p, 8, 9))


@part("legs")
def _(S):   # three short sturdy legs, splayed a little
    p = Pic(S)
    for a, b in (((4.8, 11.4), (4, 14.6)), ((8, 11.4), (8, 14.6)), ((11.2, 11.4), (12, 14.6))):
        p.piece(line(1.6, a, b))
    return top(p.outline(), at(p, 8, 11.2))


@part("net")
def _(S):   # a net bag hanging from a ring
    p = Pic(S).piece(both(ell(8, 9.4, 3.6, 5), rect(0, 9.4, 16, 16)), "trim", flat=3)
    k = max(1, S // 16)
    for (x, y) in list(p.px):
        if (x // k + y // k) % 2:
            del p.px[(x, y)]
    p.piece(ell(8, 9.4, 3.8, 0.9), "main").outline()
    return p, {"pin": at(p, 8, 9.4)}


@part("bristles")
def _(S):   # a tuft, splayed at its end; it hangs from what holds it
    p = Pic(S).piece(poly((6.2, 11), (9.8, 11), (11.8, 15.2), (4.2, 15.2)), "glow", flat=0)
    for x in (5.6, 7.2, 8.8, 10.4):
        p.piece(rect(x, 12.4, x + 0.5, 15.2), "glow", flat=1)
    p.piece(rect(5.8, 10.6, 10.2, 11.8), "trim", flat=1).outline()
    return top(p, highest(p, 8))


@part("fishing line")
def _(S):   # the bending tip of a rod up and out to the right, a line down from it with a red and white float and a hook
    p = Pic(S).piece(line(0.9, (3, 10.8), (4.6, 8.4), (7, 6.8), (11, 6.2)))
    p.piece(line(0.5, (11, 6.4), (11, 13.4)), "trim", flat=0)
    p.piece(both(ell(11, 10, 1.4, 1.7), rect(0, 0, 16, 10)), "red").piece(both(ell(11, 10, 1.4, 1.7), rect(0, 10, 16, 16)), "white")
    p.piece(line(0.8, (11, 13.2), (11, 14.4), (12.2, 14.4), (12.2, 13.4)), "trim", flat=2).outline()
    return top(p, lowest(p, 3))


@part("wings")
def _(S):   # a pair, spread, feathered at their tips
    p = Pic(S)
    for sgn in (-1, 1):
        p.piece(poly((8, 12.6), (8 + sgn * 2, 9.4), (8 + sgn * 6.4, 8.2), (8 + sgn * 6, 10.6), (8 + sgn * 5, 11.4), (8 + sgn * 4.6, 13), (8 + sgn * 3, 13.6)), "trim", flat=3)
        p.piece(line(0.6, (8 + sgn * 2, 11), (8 + sgn * 5.4, 9.6)), "trim", flat=1)
    return top(p.outline(), at(p, 8, 12.6))


@part("fin")
def _(S):   # a swept fin out to the right
    p = Pic(S).piece(poly((3, 9.6), (6, 9.6), (12.6, 13.2), (12, 14.6), (3, 14.6))).piece(line(0.6, (4.4, 10.4), (10, 13.6)), flat=1)
    return top(p.outline(), pin_left(p, 12))


@part("kite")
def _(S):   # a diamond with a cross of sticks and a ribbon tail
    p = Pic(S).piece(poly((8, 7.2), (10.6, 9.8), (8, 13), (5.4, 9.8))).piece(rect(5.4, 9.4, 10.6, 10.2), "trim", flat=1).piece(rect(7.6, 7.2, 8.4, 13), "trim", flat=1)
    p.piece(line(0.6, (8, 13), (9, 13.8), (7.4, 14.6), (8.4, 15.2)), "red").outline()
    return top(p)


@part("balloon")
def _(S):   # round and red on a string
    p = Pic(S).piece(ell(8, 10.4, 2.7, 2.8), "red").piece(rect(7.6, 13, 8.4, 13.8), "red").piece(line(0.6, (8, 13.8), (8.6, 14.6), (8, 15.2)), "trim", flat=1)
    p.dot(6.8, 9, "white").outline()
    return top(p)


@part("rudder")
def _(S):   # a flat blade, a keel, under it
    p = Pic(S).piece(poly((5.4, 9), (10.6, 9), (9.6, 12.6), (6.6, 12.6))).piece(rect(7.6, 9, 8.4, 12.4), flat=1)
    return top(p.outline(), highest(p, 8))


@part("oar")
def _(S):   # a shaft down to the right, a flat blade at its end
    p = Pic(S).piece(line(1, (4, 9), (8, 12))).piece(poly((7.4, 11.2), (9.2, 11), (11.6, 13.6), (10.4, 15), (9, 14)), flat=3)
    return top(p.outline(), pin_left(p, 9))


@part("rocket")
def _(S):   # a stubby block hanging under, two flared nozzles at its bottom, a hot tongue of fire in each
    p = Pic(S).piece(rect(4.6, 7.6, 11.4, 9.6), "trim", flat=2).piece(rect(4.6, 8.2, 11.4, 8.9), "red")
    for x in (6, 10):
        p.piece(poly((x - 1, 9.6), (x + 1, 9.6), (x + 1.8, 11.8), (x - 1.8, 11.8)), "trim", flat=0)
        p.piece(poly((x - 1.4, 11.8), (x + 1.4, 11.8), (x + 0.3, 15.2), (x - 0.3, 15.2)), "glow", flat=1).piece(rect(x - 0.6, 11.8, x + 0.6, 13), "glow", flat=2)
    return top(p.outline(), highest(p, 8))


@part("drum skin")
def _(S):   # a pale drumhead in a rim, laced down
    p = Pic(S).piece(rect(3, 12, 13, 15.2)).piece(ell(8, 12, 5, 1.6), "trim", flat=3)
    for x in (4.4, 6.8, 9.2, 11.6):
        p.piece(line(0.6, (x, 12.8), (x + 1.2, 15)), "trim", flat=2)
    return top(p.outline())


@part("whistle")
def _(S):   # a little tin whistle, its mouthpiece at the left
    p = Pic(S).piece(either(rect(3, 11.2, 8, 13), ell(9.8, 12.8, 2.6, 2.4)), "trim", flat=2).piece(rect(6.4, 10.6, 8.4, 11.4), "trim", flat=0).piece(less(ell(13.2, 11, 1, 1), ell(13.2, 11, 0.4, 0.4)), "trim", flat=1)
    return top(p.outline(), lowest(p, 4))


@part("horn")
def _(S):   # flaring up and out to the right from a narrow mouthpiece
    p = Pic(S).piece(line(1.3, (8, 15.2), (8.4, 13.8), (10, 12.4)), "glow", flat=1).piece(poly((9.4, 12.2), (11.4, 9.6), (13.4, 11.4), (11, 13.2)), "glow", flat=1)
    p.piece(line(1, (11.6, 10), (13, 11.4)), "glow", flat=0).outline()
    return top(p, lowest(p, 8.2))


@part("comb")
def _(S):   # a row of tuned teeth, long to short, on a bar
    p = Pic(S).piece(rect(3.4, 14, 12.6, 15.2), "trim", flat=1)
    for i, x in enumerate((4, 5.6, 7.2, 8.8, 10.4, 12)):
        p.piece(rect(x - 0.45, 10.4 + i * 0.5, x + 0.45, 14), "trim", flat=3)
    return top(p.outline())


@part("piano keys")
def _(S):   # white keys and black ones, a row of them
    p = Pic(S).piece(rect(2.6, 10, 13.4, 15.2), "white")
    for x in (4.4, 6.6, 8.8, 11):
        p.piece(rect(x - 0.3, 10, x + 0.3, 15.2), "trim", flat=1)
    for x in (5.5, 7.7, 10):
        p.piece(rect(x - 0.6, 10, x + 0.6, 12.8), "ink")
    return top(p.outline())


@part("panpipes")
def _(S):   # reed pipes long to short, bound across
    p = Pic(S)
    for i, x in enumerate((4, 6, 8, 10, 12)):
        p.piece(rect(x - 0.9, 7.6 + i * 1.2, x + 0.9, 15.2))
    p.piece(rect(3, 12, 13, 13), "trim", flat=1)
    return top(p.outline(), at(p, 8, 15.2))


@part("seat")
def _(S):   # a small flat seat with a rounded edge, on a short post
    p = Pic(S).piece(lambda u, v: ((u - 8) / 4.8) ** 4 + ((v - 11) / 1.3) ** 4 < 1).piece(rect(7.2, 12.2, 8.8, 15.2), "trim", flat=1).outline()
    return top(p)


@part("roof")
def _(S):   # a little peaked roof
    p = Pic(S).piece(poly((8, 9.6), (13.4, 13.4), (2.6, 13.4))).piece(rect(2.2, 13, 13.8, 14.2), flat=1).piece(rect(7, 14.2, 9, 15.2), "trim", flat=1).outline()
    return top(p)


@part("arm")
def _(S):   # a jointed crane arm, bent at its elbow, a hook at its end
    p = Pic(S).piece(line(1.2, (4.6, 15), (4.6, 11.4), (10.4, 9.4))).piece(ell(4.6, 11.4, 1.2, 1.2), "trim", flat=2).piece(line(0.6, (10.4, 9.4), (10.4, 12)), "trim", flat=1)
    p.piece(line(0.7, (10.4, 12), (10.4, 13), (11.6, 13), (11.6, 12.2)), "trim", flat=2)
    return top(p.outline(), lowest(p, 4.6))


@part("handlebar")
def _(S):   # a crossbar with grips, on a short post
    p = Pic(S).piece(rect(7.4, 12.4, 8.6, 15.2), "trim", flat=1).piece(rect(3.4, 11.4, 12.6, 12.6), "trim", flat=2).piece(rect(2.4, 11, 4.4, 13), "red").piece(rect(11.6, 11, 13.6, 13), "red")
    return top(p.outline())


@part("ice")
def _(S):   # a clear block of ice
    p = Pic(S).piece(poly((4.6, 10.4), (11, 9.6), (11.6, 15.2), (4, 15.2)), "trim", flat=3).piece(rect(5, 10.6, 6, 14.6), "white").dot(9.6, 11.4, "white")
    return top(p.outline())


@part("soil")
def _(S):   # a mound of dark earth, a pebble in it
    p = Pic(S).piece(both(ell(8, 15, 5, 3.6), rect(0, 0, 16, 15.2)), flat=0).dot(6, 13.4, "main1").dot(9.6, 12.4, "main1").dot(10.6, 14, "trim2")
    return top(p.outline())


@part("sprout")
def _(S):   # a stem and two leaves
    p = Pic(S).piece(rect(7.6, 10.4, 8.4, 15.2), "trim", flat=0).piece(ell(5.8, 10.4, 2.3, 1.2)).piece(ell(10.2, 9.4, 2.3, 1.2)).outline()
    return top(p)


@part("ball")
def _(S):   # a round ball, a stripe round it
    p = Pic(S).piece(ell(8, 12, 3.2, 3.2)).piece(both(ell(8, 12, 3.2, 3.2), rect(0, 11.2, 16, 12.6)), "white").dot(6.6, 10.4, "white").outline()
    return top(p)


@part("ribbon")
def _(S):   # a streamer fluttering out to the right
    p = Pic(S).piece(poly((3, 10), (6, 9), (9, 11), (12.4, 9.6), (13.4, 11.4), (9.4, 13), (6, 11), (3, 12)), "red").outline()
    return top(p, pin_left(p, 11))


@part("flag")
def _(S):   # a pennant on a little staff
    p = Pic(S).piece(rect(7, 10, 8, 15.2), "trim", flat=1).piece(poly((8, 10.2), (12, 11.6), (8, 13.2)), "red").outline()
    return top(p, lowest(p, 7.4))


@part("clamp")
def _(S):   # a C of iron with a screw through its lower jaw
    p = Pic(S).piece(less(rect(5.6, 9.6, 10.6, 14), rect(7, 10.8, 10.6, 12.8)), "trim", flat=1).piece(rect(8.4, 12.8, 9.4, 15), "trim", flat=2).piece(rect(7.4, 14.6, 10.4, 15.4), "trim", flat=2)
    return top(p.outline(), pin_left(p, 11.8))


# wraps: round its middle (clip: only where the base is)
THING["strap"] = wrap(lambda x, y, n: "trim1" if (x % 9) in (3, 4) and 0 < y < n - 1 else "main%d" % (2 if y == 0 else 0 if y == n - 1 else 1), 2.2)   # leather, a buckle now and then
THING["rope"] = wrap(lambda x, y, n: "main%d" % (3 if (x - y) % 3 == 0 else 2 if (x - y) % 3 == 1 else 1), 3)   # coils
THING["chain"] = wrap(lambda x, y, n: ("trim3" if (x % 4 in (0, 3)) == (y % 2 == 0) else "trim1") if (x % 4 != 1 or y % 2) else None, 2)
THING["hose"] = wrap(lambda x, y, n: "main%d" % (3 if y % 2 == 0 and x % 5 else 1), 3)


def pocket(S):   # a sewn patch with a flap
    k, p = S / 16, Pic(S)
    x0, x1, y0, y1 = round(S / 2 - 2.6 * k), round(S / 2 + 2.6 * k), round(S / 2 - 2 * k), round(S / 2 + 2.6 * k)
    p.each(lambda x, y, S: None if not (x0 <= x < x1 and y0 <= y < y1) else "main0" if x in (x0, x1 - 1) or y == y1 - 1 else "main3" if y < y0 + max(1, round(1.4 * k)) else "main2")
    return p, {"pin": [p.cx, (y0 + y1) // 2]}


def quilt(S):   # patches in squares, draped over its top and down its sides
    k, p = S / 16, Pic(S)
    y0, n, c = round(S / 2 - 3 * k), round(6 * k), max(1, round(2 * k))
    p.each(lambda x, y, S: None if not y0 <= y < y0 + n else ("red" if (x // c + y // c) % 3 == 0 else "main3" if (x // c + y // c) % 3 == 1 else "trim2"))
    return p, {"pin": [p.cx, y0 + n // 2]}


THING["pocket"] = pocket
THING["quilt"] = quilt

# what the composer needs to know about a part that the contract did not say
# the parts SPEC-v3.5 §3.0's uses name that the first library did not have
NEW = {"spade": {"role": "top", "on": ["tip", "top"], "layer": "front"}, "chimes": {"role": "top", "on": ["inside", "top", "tip"], "layer": "front", "sound": "ring"},
       "pad": {"role": "top", "on": ["top", "tip"], "layer": "front"}, "seeds": {"role": "top", "on": ["inside", "top", "tip"], "layer": "front"}}
# §3.0: any two things may be combined, so every part a kind gives must have a spot on every base: these go on one more
ALSO_ON = {"blade": "top", "head": "top", "lid": "tip"}
# ... and the catalog kinds that give them (and strings and a sail) to an invention, so every use can be reached from two things a pet can make
SIGNATURE = {"trowel": "spade", "wind chime": "chimes", "mobile": "chimes", "cushion": "pad", "bed-mat": "pad", "treat": "seeds", "blanket": "sail", "drum": "strings"}
EXTRA = {"strings": {"outline": False, "to": {"inside": "face", "side": "face"}}, "wheel": {"to": {"side": "base"}}, "tines": {"carries": ["tip"]},
         "chimes": {"to": {"inside": "base", "top": "base", "tip": "side"}},
         "cord": {"clip": True, "to": {"side": "face"}}, "band": {"clip": True, "to": {"side": "face"}}, "studs": {"clip": True, "to": {"side": "face"}},
         "weave": {"clip": True, "to": {"side": "face"}}, "cloth": {"clip": True, "to": {"side": "face"}},
         # SPEC-v3.6d: a light given a lamp shade's tip after it hangs in its mouth; the wraps lie on the base's own body
         "lamp shade": {"carries": ["tip"]}, "candle": {"carries": ["tip"]}, "wick": {"carries": ["tip"]}, **{w: {"clip": True, "to": {"side": "face"}} for w in ("strap", "rope", "chain", "hose", "pocket", "quilt")}}

# ---- the body parts (SPEC-v3.5 §2.1), typed. M L D: the coat's middle, light and dark tone; S its shine; T t: the
# pattern's dark, the pale; G g: the warm accent (a beak, an antenna's bob); W white; R red; #: ink.
CH = {"D": "main0", "M": "main1", "L": "main2", "S": "main3", "T": "trim0", "t": "trim2", "g": "glow0", "G": "glow1", "W": "white", "R": "red", "#": "ink"}
solid = lambda rows: [r.replace("t", "M").replace("T", "M") for r in rows]   # seen from behind: no inside to an ear


def views(front_l, front_s, side_l=None, side_s=None, back_l=None, back_s=None):
    """Each view at each size as (rows, pin). A view not drawn is the front one. The side view faces right."""
    return {"front.l": front_l, "front.s": front_s, "side.l": side_l or front_l, "side.s": side_s or front_s, "back.l": back_l or front_l, "back.s": back_s or front_s}


def ear(front_l, front_s, side_l=None, side_s=None):
    return views(front_l, front_s, side_l, side_s, (solid(front_l[0]), front_l[1]), (solid(front_s[0]), front_s[1]))


def mouths(widen, beak=False):
    """A mouth in each of the five things a face does with it, over one or two middle columns, and in profile."""
    out = {}
    for size in "ls":
        for n in (1, 2, "side"):
            for expr in ("flat", "smile", "frown", "open", "o"):
                opens, w = expr in ("open", "o"), 1 if n == "side" else n
                if beak and n == "side":
                    rows, pin = (["GG", "R.", "g."] if opens else ["GG", "g."]), (0, 0)
                elif beak:
                    rows, pin = ["G" * (w + 2)] + (["." + "R" * w + "."] if opens else []) + ["." + "g" * w + "."], (1, 0)
                elif opens:
                    e = widen + (1 if w == 1 and size == "l" else 0)
                    rows = ["#" * (w + 2 * e), ("R" if expr == "open" else "#") * (w + 2 * e)] + (["#" * (w + 2 * e)] if expr == "open" and size == "l" else [])
                    pin = (e, 0)
                else:
                    line_, ends = "." + "#" * (w + 2 * widen) + ".", "#" + "." * (w + 2 * widen) + "#"
                    rows, pin = ([line_.strip(".")], (widen, 0)) if expr == "flat" else ([ends, line_] if expr == "smile" else [line_, ends], (widen + 1, 0))
                out["%s.%s.%s" % (expr, n, size)] = (rows, pin)
    return out


# layer: behind (shows only round the body, grows out of it), front (over it), on (only where the body is). pair: one
# each side, the second mirrored. hard: its line is drawn over the body too. spread: how far from the middle of the head
# a pair stands, as a part of the head's width.
BODY = {
    "ears": {"layer": "behind", "pair": True, "spread": 0.3, "values": {
        "round": ear(([".LL.", "LttM", "MttM"], (2, 2)), (["LM", "MM"], (1, 1))),
        "pointed": ear((["L..", "Lt.", "LtM", "MtM"], (1, 3)), (["L.", "LM", "MM"], (1, 2))),
        "long": ear((["LM", "Lt", "Lt", "Lt", "Mt", "MM"], (1, 5)), (["L", "L", "M", "M"], (0, 3)),
                    (["LL...", "MLL..", ".MtL.", "..MtM", "...MM"], (4, 4)), (["LL.", ".LM", "..M"], (2, 2)))}},
    "head": {"layer": "behind", "pair": True, "spread": 0.16, "values": {
        "horns": views((["W..", "tW.", ".tW", ".tt"], (2, 3)), (["W.", "tW"], (1, 1))),
        "antennae": views((["GG.", "GG.", "..#", "..#", "..#"], (2, 4)), (["G.", ".#", ".#"], (1, 2))),
        "crest": dict(views((["T.T.T", "TTTTT", "TTTTT"], (2, 2)), (["T.T", "TTT", "TTT"], (1, 2))), pair=False)}},
    "tail": {"layer": "behind", "pair": False, "values": {   # the front view's is out to the right; a side view turns it to the back
        "stub": views(([".LL.", "MLMM", ".MMD"], (0, 1)), ([".LM", "MMD"], (0, 1)), back_l=(["LLM", "LMM", "MMD"], (1, 2)), back_s=(["LM", "MD"], (0, 1))),
        "long": views((["...LL", "....M", "....M", "...MM", "MMMD."], (0, 4)), (["..L", "..M", "MMM"], (0, 2)),
                      back_l=(["L.", "M.", ".M", ".M", ".M"], (1, 4)), back_s=(["L", "M", "M"], (0, 2))),
        "fluffy": views((["..ttt.", ".tLLMM", ".LMMMD", "MMMMD.", ".MMD.."], (0, 3)), ([".tt", "MLM", ".MD"], (0, 1)),
                        back_l=([".tt.", "LLMM", "LMMD", ".MD."], (1, 3)), back_s=([".t.", "LMM", ".M."], (1, 2)))}},
    "whiskers": {"layer": "front", "pair": True, "outline": False, "values": {
        "yes": views((["##.", "...", "##."], (2, 1)), (["##."], (2, 0)))}},
    "feet": {"layer": "front", "pair": True, "values": {   # the pin is the pixel under the body's foot column
        "nubs": views((["DD"], (0, 0)), (["DD"], (0, 0))),
        "paws": views((["MMM", "DDD"], (1, 0)), (["DDD"], (1, 0)), (["MMM.", "DDDD"], (0, 0)), (["DDD"], (0, 0))),
        "legs": views(([".D", ".D", ".D", "DD"], (1, 0)), ([".D", ".D", "DD"], (1, 0)), (["D.", "D.", "D.", "DD"], (0, 0)), (["D.", "D.", "DD"], (0, 0)))}},
    "mouth": {"layer": "on", "pair": False, "outline": False, "values": {
        "dot": mouths(0), "wide": mouths(1), "beak": dict(mouths(0, True), layer="front", side_at="edge")}},
}
# the body plans (§2.2), as proportions of the one body the genome's roundness and stretch give: `w`, `h` of the body;
# with a `head`, that stands on it (`w` of the body's width, `tall` of its own width) and carries the face.
PLANS = {"blob": {"w": 1, "h": 1}, "head": {"w": 0.62, "h": 0.5, "head": {"w": 1, "tall": 0.82, "round": 0.85}, "overlap": 1},
         "segments": {"w": 1.12, "h": 0.72, "head": {"w": 0.66, "tall": 0.9, "round": 0.9}, "overlap": 2},
         "long": {"w": 1.45, "h": 0.6}, "tall": {"w": 0.68, "h": 1.4}}


SHADE = {"light": 0, "mid": -0.09, "dark": -0.17}   # how much darker a coat of each shade is than the first
# what a material does to the colour of a part made of it: `sat` and `light` multiply, `add` lightens, `cap` softens the highlights
LOOKS = {"soft": {"cap": 0.78}, "dark": {"sat": 0.7, "light": 0.62}, "glassy": {"sat": 0.6, "add": 0.08}, "heavy": {"sat": 0.8, "light": 0.88}, "bright": {"add": 0.05},
         # SPEC-v3.6d: what a design's part made of a bit looks like; `color` (things.ts PALETTE) where the part has none of its own
         "wood": {"color": "brown"}, "metal": {"color": "grey", "sat": 0.8, "light": 0.95}, "iron": {"color": "grey", "light": 0.8}, "brass": {"color": "yellow", "light": 0.85},
         "copper": {"color": "orange", "light": 0.85}, "glass": {"color": "teal", "sat": 0.6, "add": 0.08}, "clay": {"color": "orange", "sat": 0.8}, "fired clay": {"color": "red", "sat": 0.7},
         "cloth": {"color": "red", "cap": 0.78}, "stone": {"color": "grey"}, "leather": {"color": "brown", "light": 0.8}, "wax": {"color": "white", "cap": 0.9}, "reed": {"color": "green", "sat": 0.6},
         "string": {"color": "white", "cap": 0.85}, "fibre": {"color": "white", "cap": 0.85}, "bone": {"color": "white"}, "feather": {"color": "white", "cap": 0.9}, "paper": {"color": "white"}}


def stamp(rows):
    im = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        assert len(r) == len(rows[0]), rows
        for x, ch in enumerate(r):
            if ch != ".":
                im.putpixel((x, y), colour(CH[ch]))
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(ASSETS, "parts.json")
    data = json.load(open(path))
    data["palette"] = PALETTE
    data["rules"]["behind"] = ["inside"]
    for name, entry in NEW.items():
        data["thing"][name] = dict(data["thing"].get(name, {}), **entry)
    for name, spot in ALSO_ON.items():
        if spot not in data["thing"][name]["on"]:
            data["thing"][name]["on"].append(spot)
    for kind, sig in SIGNATURE.items():
        data["kinds"][kind]["signature"] = sig
    names = list(data["thing"])
    assert set(names) == set(THING), set(names) ^ set(THING)
    for S in SIZES:
        cols, file = 9, "own/parts/thing%d.png" % S
        sheet = Image.new("RGBA", (cols * S, -(-len(names) // cols) * S), (0, 0, 0, 0))
        for i, name in enumerate(names):
            p, where = THING[name](S)
            x, y = (i % cols) * S, (i // cols) * S
            sheet.paste(p.image(), (x, y))
            entry = data["thing"][name]
            entry.update(EXTRA.get(name, {}))
            if entry["role"] == "base":
                where["at"] = {k: v for k, v in where["at"].items() if k in entry["spots"] or k in ("face", "base", "side")}   # (side: where a chime given a tip hangs)
            entry.setdefault("px", {})[str(S)] = dict({"file": file, "rect": [x, y, S, S]}, **where)
        sheet.save(os.path.join(ASSETS, file))
    # the body parts: one row a value, its frames side by side on an 8 pixel grid
    C, file, slots = 8, "own/parts/body.png", {}
    rows_ = [(slot, value, frames) for slot, s in BODY.items() for value, frames in s["values"].items()]
    sheet = Image.new("RGBA", (C * max(len([k for k in f if "." in k]) for _, _, f in rows_), C * len(rows_)), (0, 0, 0, 0))
    for r, (slot, value, frames) in enumerate(rows_):
        s = slots.setdefault(slot, dict({k: v for k, v in BODY[slot].items() if k != "values"}, values={}))
        out = s["values"][value] = {k: v for k, v in frames.items() if "." not in k}
        out["frames"] = {}
        for c, (frame, (rows, pin)) in enumerate((k, v) for k, v in frames.items() if "." in k):
            im = stamp(rows)
            assert im.size[0] <= C and im.size[1] <= C, (slot, value, frame)
            sheet.paste(im, (c * C, r * C))
            out["frames"][frame] = {"rect": [c * C, r * C, im.size[0], im.size[1]], "pin": list(pin)}
    sheet.save(os.path.join(ASSETS, file))
    data["body"] = {"about": "The body parts a genome's slots name (bodies.json), as the view stamps them on a pet: `frames` are <view>.<size> (front, side facing right, back; l, or s for a body under `small` pixels wide), a mouth's <what it does>.<1 or 2 middle columns, or side>.<size>. `layer`: behind the body, in front of it, or on it. `pair`: one each side, mirrored. `plans`: each body plan as proportions of the one body.",
                    "file": file, "small": 10, "shade": SHADE, "plans": PLANS, "slots": slots}
    data["looks"] = LOOKS
    text = json.dumps(data, indent=1)
    text = re.sub(r"\[\s+((?:(?:-?[\d.]+|\"[^\"\n]*\"),\s+)*(?:-?[\d.]+|\"[^\"\n]*\"))\s+\]", lambda m: "[" + re.sub(r",\s+", ", ", m.group(1)) + "]", text)   # a list of numbers or names on one line
    open(path, "w").write(text)
    print("drew %d thing parts at %s and %d body parts into %s" % (len(names), "/".join(map(str, SIZES)), len(rows_), OUT))


if __name__ == "__main__":
    main()
