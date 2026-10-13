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
            self.px[(x, y)] = region + str(flat if flat is not None else lvl if n == 4 else (0, 0, 1, 2)[lvl])
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
    p = Pic(S).piece(rect(7, 8, 9, 15)).outline()
    return p, base_points(p, 11.5, 11.5)


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
    p = Pic(S).piece(less(ell(8, 11, 4.15, 4.15), ell(8, 11, 2.4, 2.4))).outline()
    return p, base_points(p, 11, 11, inside=sill(p, 11))


@part("frame")
def _(S):
    p = Pic(S).piece(less(rect(3, 7, 13, 15), rect(4.2, 8.2, 11.8, 13.8))).outline()
    return p, base_points(p, 11, 11, inside=sill(p, 11))


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
    p = Pic(S).piece(either(rect(5, 13, 11, 15), rect(5, 9, 6, 14), rect(7, 9, 9, 14), rect(10, 9, 11, 14))).outline()
    return top(p)


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
def _(S):
    p = Pic(S).piece(poly((5, 14.2), (5, 12.6), (6.6, 10.4), (8, 10.4), (8, 11.6), (6.4, 14.2))).outline()   # short: it must not reach out of the thing's square
    return top(p, p.left(13.4))


@part("strings")
def _(S):
    p = Pic(S)
    for x in (6, 8, 10):
        p.piece(rect(x, 9, x + 1, 14), "trim", flat=3)
    p.piece(rect(5.2, 8, 11.8, 9), "trim", flat=0).piece(rect(5.2, 14, 11.8, 15), "trim", flat=0)
    return top(p, p.mid(11.5))


@part("wheel")
def _(S):
    p = Pic(S).piece(rect(5, 12.9, 11, 14.1), "trim", flat=1)
    for x in (4.5, 11.5):
        p.piece(ell(x, 13.5, 1.48, 1.48)).piece(ell(x, 13.5, 0.5, 0.5), "trim", flat=3)
    p.outline()
    return top(p, [p.cx, max(y for _, y in p.px)])   # their feet level with the foot of what they carry


@part("hook")
def _(S):
    p = Pic(S).piece(line(1.05, (7.5, 14.6), (7.5, 13), (9.5, 12), (9.5, 11.2), (8.5, 10.5), (7.2, 10.5), (6.3, 11.5)), "trim").outline()
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
    p = Pic(S).piece(rect(7, 10, 8, 15), "trim", flat=1).piece(poly((8, 10.1), (8, 13.6), (12, 13.6))).outline()
    return top(p)


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

# what the composer needs to know about a part that the contract did not say
EXTRA = {"strings": {"outline": False, "to": {"inside": "face", "side": "face"}}, "wheel": {"to": {"side": "base"}},
         "cord": {"clip": True, "to": {"side": "face"}}, "band": {"clip": True, "to": {"side": "face"}}, "studs": {"clip": True, "to": {"side": "face"}},
         "weave": {"clip": True, "to": {"side": "face"}}, "cloth": {"clip": True, "to": {"side": "face"}}}

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
LOOKS = {"soft": {"cap": 0.78}, "dark": {"sat": 0.7, "light": 0.62}, "glassy": {"sat": 0.6, "add": 0.08}, "heavy": {"sat": 0.8, "light": 0.88}, "bright": {"add": 0.05}}


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
                where["at"] = {k: v for k, v in where["at"].items() if k in entry["spots"] or k in ("face", "base")}
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
