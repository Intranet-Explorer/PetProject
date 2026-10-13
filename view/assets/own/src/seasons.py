"""The seasons' pictures (SPEC-v3.5 §5): the garden and the windows as they look in spring, autumn and winter (summer
is the art as it stands). Needs Python 3.11+ and Pillow. From this folder:

  python3 seasons.py        draws own/seasons.png, writes ../../seasons.json (which picture stands in for which, by
                            season and room type) and lays this sheet's entries into ../../sprites.json as one block

Nothing here is a new picture of a thing: each is the pack's (or our) own tile or sprite with the season laid over it
in the pack's palette, so it sits beside the rest: blossom dotted on what is green, the green gone to rust and leaves
on the grass, snow lying on whatever faces up. The tables below say what gets which; the view only reads seasons.json.
The two small bits a season brings (a fallen leaf, food gone bad) are typed, like the bits in art.py."""
import colorsys, json, os, random, re
from PIL import Image
import art
from build import ASSETS, Sheet, pic, rgba

P = lambda ch: rgba(art.PAL[ch])
OUT = P("#")
SNOW, SNOW_SHADE, ICE = (240, 246, 250, 255), (201, 222, 233, 255), P("l")
RUST = [P("B"), P("r"), P("R"), P("q")]                   # the green of a bush gone to autumn, dark to light
LITTER = [P("q"), P("q"), P("y"), P("R")]                 # leaves lying on the grass
PINK, PINK_DARK, WHITE, YOLK = P("p"), P("X"), P("w"), P("Y")

sprites = json.load(open(os.path.join(ASSETS, "sprites.json")))
packs = json.load(open(os.path.join(ASSETS, "packs.json")))
files = {}


def source(name):
    """The picture a name of ours stands for, as it is drawn today."""
    d = sprites[name]
    path = os.path.join(ASSETS, packs[d["pack"]]["dir"], d["file"])
    if path not in files:
        files[path] = Image.open(path).convert("RGBA")
    x, y, w, h = d["rect"]
    return files[path].crop((x, y, x + w, y + h))


def hsv(p):
    return colorsys.rgb_to_hsv(p[0] / 255, p[1] / 255, p[2] / 255)


def green(p):
    h, s, v = hsv(p)
    return p[3] > 0 and 0.16 <= h <= 0.45 and s > 0.25 and v > 0.3


def glass(p):
    h, s, v = hsv(p)
    return p[3] > 0 and 0.45 <= h <= 0.62 and s > 0.15 and v > 0.55


def each(im, fn):
    """The same picture with every pixel put through fn(pixel, x, y)."""
    out = im.copy()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            out.putpixel((x, y), fn(im.getpixel((x, y)), x, y))
    return out


def mix(a, b, k):
    return tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3)) + (a[3],)


# ---- winter: snow ----

def tones(im, test):
    """The different lightnesses of the pixels that pass the test, dark to light."""
    return sorted({round(hsv(im.getpixel((x, y)))[2], 2) for y in range(im.size[1]) for x in range(im.size[0]) if test(im.getpixel((x, y)))})


def snowed(im, name, trodden=False):
    """Ground under snow: everything green is snow (its darker blades the snow's own shadows, thinned out). Dug earth
    is a hollow in it, in the snow's shadow, its furrows a little darker; a `trodden` path stays bare, and frosted."""
    r = random.Random(name)
    lightest = (tones(im, green) or [1])[-1]
    earth = tones(im, lambda p: p[3] > 0 and p != OUT and not green(p))

    def fn(p, x, y):
        if green(p):
            return SNOW if hsv(p)[2] >= lightest - 0.08 or r.random() < 0.45 else SNOW_SHADE
        if p[3] and p != OUT:
            return mix(p, SNOW, 0.18) if trodden else SNOW_SHADE if round(hsv(p)[2], 2) == earth[-1] else mix(SNOW_SHADE, P("u"), 0.18)
        return p
    return each(im, fn)


def capped(im, deep=2, body=lambda p: p[3] > 0):
    """A thing with snow lying on it: on each column, the first pixels under its top outline are snow."""
    out = im.copy()
    w, h = im.size
    for x in range(w):
        top = next((y for y in range(h) if body(im.getpixel((x, y)))), None)
        if top is None:
            continue
        y = top + 1 if im.getpixel((x, top)) == OUT else top
        for i in range(deep):
            if y + i < h and im.getpixel((x, y + i)) != OUT and im.getpixel((x, y + i))[3]:
                out.putpixel((x, y + i), SNOW if i < deep - 1 or deep == 1 else SNOW_SHADE)
    return out


def frozen(im):
    """Snow on it, and its water ice."""
    return each(capped(im), lambda p, x, y: ICE if glass(p) and p not in (SNOW, SNOW_SHADE) else p)


# ---- autumn: rust and fallen leaves ----

def rusted(im):
    """What was green has turned: the same shading, in the pack's oranges."""
    vs = tones(im, green)   # (by rank, not by how far apart they are: a bush's greens are close, and must not all come out one orange)
    return each(im, lambda p, x, y: RUST[round((vs.index(round(hsv(p)[2], 2)) + 1) / len(vs) * (len(RUST) - 1))] if green(p) else p)


def littered(im, name, n=5):
    """Grass gone a little yellow, with leaves lying on it: each a pixel or two with a dark one under it."""
    r, out = random.Random(name), each(im, lambda p, x, y: mix(p, P("h"), 0.3) if green(p) else p)
    w, h = im.size
    for _ in range(n):
        x, y, c = r.randrange(1, w - 2), r.randrange(1, h - 2), r.choice(LITTER)
        if not all(green(im.getpixel(t)) for t in ((x, y), (x + 1, y), (x, y + 1))):
            continue   # (leaves lie on the grass, not on the path or the earth: those keep their own look)
        out.putpixel((x, y), c)
        out.putpixel((x + 1, y), c)
        out.putpixel((x + r.randrange(2), y + 1), P("B"))
    return out


# ---- spring: blossom ----

def blossomed(im, name, n=4, small=False):
    """Blossom on what is green: on the grass a white speck with a yellow eye, on a bush or a hedge a pink one."""
    r, out, rows = random.Random(name), im.copy(), []
    w, h = im.size
    for _ in range(n * 8):
        x, y = r.randrange(1, w - 2), r.randrange(1, h - 2)
        if n and all(abs(y - at) > 2 for at in rows) and all(green(out.getpixel(t)) for t in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1), (x - 1, y), (x, y - 1))):
            rows.append(y)
            a, b = (WHITE, YOLK) if small else (PINK, WHITE)
            out.putpixel((x, y), a)
            out.putpixel((x + 1, y), b if small else a)
            if not small:
                out.putpixel((x, y + 1), PINK_DARK)
                out.putpixel((x + 1, y + 1), a if r.random() < 0.5 else b)
            n -= 1
    return out


# ---- the windows: what is seen through the glass ----

def window(im, season):
    out, (w, h) = im.copy(), im.size
    panes = [(x, y) for y in range(h) for x in range(w) if glass(im.getpixel((x, y)))]
    if season == "winter":   # snow along the foot of every pane, drifted up its corners; snow on the sill
        for x, y in panes:
            under = next(i for i in range(1, h) if (x, y + i) not in panes) - 1   # how many pixels of glass lie below this one
            side = (x - 1, y) not in panes or (x + 1, y) not in panes
            if under == 0 or (under == 1 and (side or x % 2)) or (under == 2 and side):
                out.putpixel((x, y), SNOW)
        sill = max((y for y in range(h) if any(im.getpixel((x, y))[3] and im.getpixel((x, y)) != OUT for x in range(w))), default=None)
        for x in range(w) if sill is not None and sill > max(y for _, y in panes) + 1 else ():
            if im.getpixel((x, sill))[3] and im.getpixel((x, sill)) != OUT:
                out.putpixel((x, sill), SNOW)
        return out
    r = random.Random(season)   # a sprig across the corner of the glass: blossom in spring, turned leaves in autumn
    tones = {"spring": [PINK, PINK, WHITE], "autumn": [P("q"), P("R"), P("y")]}[season]
    left, top = min(x for x, _ in panes), min(y for _, y in panes)
    right, bottom = max(x for x, _ in panes), max(y for _, y in panes)
    sprig = [(left, top), (left + 1, top), (left, top + 1), (left + 2, top + 1), (left + 1, top + 2), (right, top), (right - 1, top + 1), (right, top + 2), (right, bottom - 1)]
    for x, y in sprig:
        if (x, y) in panes:
            out.putpixel((x, y), r.choice(tones))
    return out


# ---- the two bits a season brings ----

BITS = {"fallen leaf": art.S("""
................
................
................
................
................
................
........##......
...##..#qR#.....
..#qo##oRq#.....
.#qoRo#Rq#......
.#oRoq##B#......
..#RqB#.##......
..#BB#..........
...##...........
................
................
"""), "spoiled food": art.S("""
................
................
................
................
................
................
................
......##........
....##SM##......
...#MzMMSM#.....
..#MMMSMzMM#....
..#mMMMMMMm#....
...##mmmm##.....
.....####.......
................
................
""")}

# ---- what gets which: {season: {room type ("*": every room): {name: how}}}. A name ending in * takes every state of it. ----

# A list: several pictures stand in for the one name, and the view takes one by where the tile is, so that the plain
# grass, which is most of the garden, is not the same few leaves over and over ("same": the picture as it stands).
GRASS = ["tile.grass.1", "tile.grass.2", "tile.grass.3"]
EARTH = ["tile.soil.nw", "tile.soil.n", "tile.soil.ne", "tile.soil.sw", "tile.soil.s", "tile.soil.se"]
WINDOWS = {"fix.window*": "window", "fix.skylight": "window"}
PLAN = {
    "spring": {"garden": dict({k: "daisy" for k in GRASS}, **{"tile.grass": ["daisy", "same", "daisies", "same", "same"], "tile.sky.hedge": "blossom", "decor.bush": "blossom"}),
               "*": WINDOWS},
    "autumn": {"garden": dict({k: "litter" for k in GRASS + EARTH}, **{"tile.grass": ["litter", "leaf", "litter", "leaf", "leaves"], "tile.path": "leaf",
                                                                     "tile.sky.hedge": "rust", "decor.bush": "rust", "grows.leaf*": "rust"}),
               "*": WINDOWS},
    "winter": {"garden": dict({k: "snow" for k in ["tile.grass"] + GRASS + EARTH}, **{"tile.path": "trodden",
                   "tile.sky.hedge": "hedge", "tile.fence": "cap", "tile.fence.nw": "cap", "tile.fence.ne": "cap", "tile.fence.sw": "cap", "tile.fence.se": "cap",
                   "decor.bush": "cap", "decor.stepping stone": "cap", "decor.sprout": None, "decor.flower.sun": "mound", "decor.flower.red": "mound", "decor.flower.white": "mound",
                   "fix.bean row*": "cap", "fix.berry bush*": "cap", "fix.herb patch*": "cap", "fix.old bench": "cap", "fix.tool box": "cap", "fix.bird bath": "frozen",
                   "grows.petal*": "cap", "grows.seed*": "cap", "grows.leaf*": "cap"}),
               "*": WINDOWS},
}


def mound():
    """A flower bed under snow: a low drift where the flower stood."""
    return pic(art.S("""
................
................
................
................
................
................
................
................
.....####.......
...##wwww###....
..#wwwwwwwww#...
.#wwwwwwwwwwl#..
.#lwwwwwwwwll#..
..##llllllll#...
....########....
................
"""), {"w": "v"})


def draw(name, how, season, seed):
    im = source(name)
    return {"snow": lambda: snowed(im, seed), "trodden": lambda: snowed(im, seed, True), "cap": lambda: capped(im), "frozen": lambda: frozen(im), "mound": mound,
            "hedge": lambda: capped(im, 3, lambda p: green(p) or p == OUT), "rust": lambda: rusted(im),
            "leaf": lambda: littered(im, seed, 1), "litter": lambda: littered(im, seed, 3), "leaves": lambda: littered(im, seed, 6),
            "daisy": lambda: blossomed(im, seed, 1, small=True), "daisies": lambda: blossomed(im, seed, 2, small=True),
            "blossom": lambda: blossomed(im, seed, 5), "window": lambda: window(im, season)}[how]()


def sheet():
    """Draws the sheet. Returns (the sheet, {season: {room: {name: what stands in for it: a name, a list of names
    to take one of, or None for nothing at all}}})."""
    s, swaps, drawn = Sheet("seasons.png"), {}, set()
    for bit, rows in BITS.items():
        s.add("bit." + bit, pic(rows))

    def stand_in(season, name, how, i=0):
        new = name if how == "same" else "season.%s.snow mound" % season if how == "mound" else "season.%s.%s%s" % (season, name, "~%d" % i if i else "")
        if how != "same" and new not in drawn:
            drawn.add(new)
            keep = {} if how == "mound" else {k: v for k, v in sprites[name].items() if k in ("anchor", "glass", "surface")}
            s.add(new, draw(name, how, season, new), **keep)
        return new

    for season, rooms in PLAN.items():
        for room, plan in rooms.items():
            for pattern, how in plan.items():
                names = sorted(n for n in sprites if n == pattern.rstrip("*") or (pattern.endswith("*") and n.startswith(pattern[:-1] + ".") and not n.startswith("season."))) if how else [pattern]
                for name in names:
                    swaps.setdefault(season, {}).setdefault(room, {})[name] = \
                        None if how is None else [stand_in(season, name, h, i) for i, h in enumerate(how)] if isinstance(how, list) else stand_in(season, name, how)
    return s, swaps


if __name__ == "__main__":
    s, swaps = sheet()
    own = s.save()
    with open(os.path.join(ASSETS, "seasons.json"), "w") as f:
        f.write(json.dumps(swaps, indent=1) + "\n")
    # sprites.json is kept by hand, one name to a line: this sheet's lines go in as one block after the last tile
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(season\.|bit\.(%s)")' % "|".join(BITS), l)]
    last = max(i for i, l in enumerate(lines) if l.startswith(' "tile.'))
    lines[last + 1:last + 1] = [" %s: %s," % (json.dumps(n), json.dumps(e)) for n, e in own.items()]
    open(path, "w").write("\n".join(lines))
    print("drew %d pictures into own/seasons.png; seasons.json says which stands in for which" % len(own))
