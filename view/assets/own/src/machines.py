"""Machines and cooking (SPEC-v3.6b §4, §5): the kiln, the loom, the millstone, the forge and its anvil, the stove, in
their states; the bits the machines make; a picture for each dish the pot can hold; the signs over a hob at the forge
or the stove. Cut from PixelLab's pictures into own/machines.png. Needs Python 3.11+ and Pillow. From this folder:

  python3 machines.py [PIXELLAB]   cuts own/machines.png (PIXELLAB: the folder holding machines48.png,
                                   machines48b.png, products16.png, pond16.png; by default
                                   ~/PetProject/assets-incoming/pixellab) and lays its entries into ../../sprites.json
                                   as one block, right after "icon.act.fish"

Names are in sheets.toml ([machines48], [machines48b], [products16], [pond16]). A machine is drawn at the art's own
size (about two tiles across, like the store's 32-pixel shelves are about two), its foot on the middle of its one tile.
`fix.built.<machine>` is how it stands cold; `.working` while it works (the view adds what moves: px/machines.ts);
the kiln's `.full` is cold with pots inside (something waits in its tray). Dishes are `dish.<name>`, keeping their
own colours."""
import json, os, re, sys
from PIL import Image
from build import ASSETS

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/PetProject/assets-incoming/pixellab")
# sprite: (sheet, cell); a: machines48, b: machines48b (48 x 48 cells, five across)
MACHINES = {"fix.built.kiln.working": ("b", 4), "fix.built.kiln.full": ("b", 5), "fix.built.loom": ("b", 0),
            "fix.built.millstone": ("b", 8), "fix.built.forge.working": ("a", 1), "fix.built.stove.working": ("b", 6), "fix.built.stove": ("b", 7)}
# bit.<name>: products16's cell
BITS = {"fired brick": 0, "flour": 12, "netting": 9, "nail": 19, "blade": 16, "hinge": 17, "chain": 20}
# dish.<name>: the nearest picture (p: products16, q: pond16)
DISHES = {"grilled fish": ("p", 34), "baked big fish": ("p", 56), "fish stew": ("p", 30), "big fish stew": ("q", 24), "fish pie": ("p", 35), "fish cakes": ("p", 47),
          "fish soup": ("p", 53), "fish and bean pie": ("p", 54), "bread": ("p", 28), "seed loaf": ("q", 40), "pancakes": ("p", 37), "berry pie": ("p", 29),
          "berry cake": ("q", 32), "bean soup": ("p", 31), "bean bake": ("p", 46), "green soup": ("q", 26), "porridge": ("p", 32), "stewed berries": ("p", 58),
          "leaf tea": ("p", 41), "petal tea": ("q", 30), "herb dumplings": ("p", 45)}
# the signs over a hob at the forge and at the stove (config.toml [process_signs]), on the plate the others have
SIGNS = {"anvil": ["........y.", ".KKKKKKKo.", "KllggggggK", ".KKggggKK.", "...KggK...", "..KggggK..", ".KKKKKKKK.", ".KbbbbbbK.", ".KKKKKKKK.", ".........."],
         "pot": ["..w..w....", "...w..w...", "..w..w....", ".KKKKKKKK.", "KooooooooK", "KlgggggggK", ".KggggggK.", ".KggggggK.", "..KKKKKK..", ".........."]}
SIGN_PAL = {"K": (38, 33, 46), "l": (176, 182, 196), "g": (110, 116, 132), "b": (150, 96, 56), "o": (240, 140, 50), "y": (255, 222, 90), "w": (196, 204, 214)}


def lum(p):
    return p[0] * 0.3 + p[1] * 0.59 + p[2] * 0.11


def main():
    a = Image.open(os.path.join(SRC, "machines48.png")).convert("RGBA")
    b = Image.open(os.path.join(SRC, "machines48b.png")).convert("RGBA")
    p16 = Image.open(os.path.join(SRC, "products16.png")).convert("RGBA")
    q16 = Image.open(os.path.join(SRC, "pond16.png")).convert("RGBA")
    big = lambda s, i: (a if s == "a" else b).crop(((i % 5) * 48, (i // 5) * 48, (i % 5) * 48 + 48, (i // 5) * 48 + 48))
    small = lambda s, i: (p16 if s == "p" else q16).crop(((i % 8) * 16, (i // 8) * 16, (i % 8) * 16 + 16, (i // 8) * 16 + 16))
    pics = {name: big(*at) for name, at in MACHINES.items()}
    # the kiln cold and empty: its pots taken out of the open door (the dark of the kiln where they stood)
    k = pics["fix.built.kiln.full"].copy()
    for y in range(24, 33):
        for x in range(17, 31):
            px = k.getpixel((x, y))
            if px[3] and lum(px) > 0x30:
                k.putpixel((x, y), (0x37, 0x21, 0x1c, 255) if y < 27 else (0x24, 0x15, 0x12, 255))
    pics["fix.built.kiln"] = k
    # the forge cold: its coals dark, a dull red left in the hottest of them
    f = pics["fix.built.forge.working"].copy()
    for y in range(48):
        for x in range(48):
            r, g, bl, al = f.getpixel((x, y))
            if al and ((r > 150 and r > bl + 60 and g > 60) or lum((r, g, bl)) > 215):   # fire: orange to yellow, white at its heart
                f.putpixel((x, y), (120, 40, 30, al) if g > 200 else (58, 44, 44, al) if g < 140 else (82, 52, 48, al))
    pics["fix.built.forge"] = f
    sheet, out = Image.new("RGBA", (256, 192), (0, 0, 0, 0)), {}
    order = ["fix.built.kiln", "fix.built.kiln.full", "fix.built.kiln.working", "fix.built.loom", "fix.built.millstone",
             "fix.built.forge", "fix.built.forge.working", "fix.built.stove", "fix.built.stove.working"]
    for n, name in enumerate(order):   # cut to what is drawn, five to a row of 48 x 48 slots; the foot on the middle of its tile
        same = [pics[k].getbbox() for k in pics if k.split(".")[2] == name.split(".")[2]]   # one box for all its states: it does not shift as it changes
        im = pics[name].crop((min(b[0] for b in same), min(b[1] for b in same), max(b[2] for b in same), max(b[3] for b in same)))
        x, y = (n % 5) * 48, (n // 5) * 48
        sheet.alpha_composite(im, (x, y))
        w, h = im.size
        out[name] = {"pack": "own", "file": "machines.png", "rect": [x, y, w, h], "anchor": [w // 2 - 8, h - 16]}
    y0, n = 96, 0
    for prefix, table in (("bit.", {k: ("p", v) for k, v in BITS.items()}), ("dish.", DISHES)):   # 16 x 16, a row of 16
        for name, at in table.items():
            x, y = (n % 16) * 16, y0 + (n // 16) * 16
            sheet.alpha_composite(small(*at), (x, y))
            out[prefix + name] = {"pack": "own", "file": "machines.png", "rect": [x, y, 16, 16], **({"tint": "none"} if prefix == "dish." else {})}
            n += 1
    ui = Image.open(os.path.join(ASSETS, "own", "ui.png")).convert("RGBA")
    d = json.load(open(os.path.join(ASSETS, "sprites.json")))["icon.act.drop"]["rect"]
    for i, (name, rows) in enumerate(SIGNS.items()):
        plate = ui.crop((d[0], d[1], d[0] + 12, d[1] + 12))
        white, band = plate.getpixel((1, 2)), plate.getpixel((2, 10))   # the plate cleared: white, its pale foot
        for y in range(1, 11):
            for x in range(1, 11):
                if plate.getpixel((x, y)) != plate.getpixel((2, 0)) and plate.getpixel((x, y))[3]:
                    plate.putpixel((x, y), band if y == 10 else white)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    plate.putpixel((1 + x, 1 + y), SIGN_PAL[ch] + (255,))
        x, y = 224 + i * 16, 160
        sheet.alpha_composite(plate, (x, y))
        out["icon.act." + name] = {"pack": "own", "file": "machines.png", "rect": [x, y, 12, 12], "anchor": [-2, -2]}
    sheet.save(os.path.join(ASSETS, "own", "machines.png"))
    path = os.path.join(ASSETS, "sprites.json")
    lines = [l for l in open(path).read().split("\n") if not re.match(r' "(%s)":' % "|".join(re.escape(k) for k in out), l)]
    at = next(i for i, l in enumerate(lines) if l.startswith(' "icon.act.fish":'))
    lines[at + 1:at + 1] = [" %s: %s," % (json.dumps(k), json.dumps(v)) for k, v in out.items()]
    open(path, "w").write("\n".join(lines))
    print("cut %d pictures into own/machines.png" % len(out))


if __name__ == "__main__":
    main()
