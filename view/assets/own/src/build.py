"""Builds the art data of view/assets (see ../../README.md). Needs Python 3.11+ and Pillow.

  python3 build.py                 draw own/*.png again from art.py (nothing else is touched)
  python3 build.py data <pack>     also write sprites.json, rooms/*.json, sounds.json and packs.json from data.py,
                                   and copy the files they name out of the unpacked Ninja Adventure pack at <pack>
                                   into third_party/ninja_adventure/ (anything there that is no longer named is removed)

The JSON files are what the view and the engine read. They were written by `data`, from the tables and the room
maps in data.py; change them there and run `data` again, or edit the JSON by hand and stop running `data`.
Check the result with validate.py."""
import json, os, shutil, sys
from PIL import Image
import art

HERE = os.path.dirname(os.path.abspath(__file__))
OWN = os.path.dirname(HERE)
ASSETS = os.path.dirname(OWN)


def rgba(hexa, a=255):
    return (int(hexa[0:2], 16), int(hexa[2:4], 16), int(hexa[4:6], 16), a)


def pic(rows, swap=None):
    """A picture from its text. `swap` replaces characters first (a lit lamp from an unlit one)."""
    w = len(rows[0])
    im = Image.new("RGBA", (w, len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        assert len(row) == w, "row %d is %d wide, not %d: %r" % (y, len(row), w, row)
        for x, ch in enumerate(row):
            ch = (swap or {}).get(ch, ch)
            if ch != ".":
                im.putpixel((x, y), rgba(art.PAL[ch]))
    return im


class Sheet:
    """Pictures packed left to right in rows on a 16-pixel grid, in the order they are added, so adding one at the
    end moves none of the others."""
    def __init__(self, file, cols=16):
        self.file, self.cols, self.items, self.x, self.y, self.rowh = file, cols, [], 0, 0, 1

    def add(self, name, im, **extra):
        cw, ch = -(-im.size[0] // 16), -(-im.size[1] // 16)
        if self.x + cw > self.cols:
            self.x, self.y, self.rowh = 0, self.y + self.rowh, 1
        self.items.append((name, im, self.x * 16, self.y * 16, extra))
        self.x, self.rowh = self.x + cw, max(self.rowh, ch)

    def strip(self, name, frames, **extra):
        """Frames of one size side by side: an animation. The sprite's rect is the first frame."""
        w, h = frames[0].size
        im = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
        for i, f in enumerate(frames):
            im.paste(f, (i * w, 0))
        self.add(name, im, frame=[w, h], **extra)

    def save(self):
        out = Image.new("RGBA", (self.cols * 16, (self.y + self.rowh) * 16), (0, 0, 0, 0))
        sprites = {}
        for name, im, x, y, extra in self.items:
            out.paste(im, (x, y))
            w, h = extra.pop("frame", im.size)
            sprites[name] = dict({"pack": "own", "file": self.file, "rect": [x, y, w, h]}, **extra)
        out.save(os.path.join(OWN, self.file))
        return sprites


def own_art():
    """Draws every own sheet; returns {sprite name: entry for sprites.json}."""
    import draw
    sprites = {}
    for sheet in draw.sheets():
        sprites.update(sheet.save())
    return sprites


if __name__ == "__main__":
    own = own_art()
    print("drew %d pictures into %s" % (len(own), OWN))
    if len(sys.argv) > 2 and sys.argv[1] == "data":
        import data
        data.write(own, sys.argv[2])
