"""The tables behind sprites.json, rooms/*.json, sounds.json and packs.json (see build.py: `build.py data <pack>`).

PACK names every picture taken from the Ninja Adventure pack; ROOMS holds the nine hand-made layouts; SOUNDS the
effects and music. Floor coordinates are [x, y], 0 <= x < 12, 0 <= y < 8, y = 0 against the north wall."""
import json, os, shutil, wave
from PIL import Image
from build import ASSETS

NINJA = "third_party/ninja_adventure"
FONT = "Ui/Font/NormalFont.ttf"   # the pack's pixel face, for the page's headings (packs.json: "font")
T = "Backgrounds/Tilesets/"
SHEET = {"H": T + "TilesetHouse.png", "E": T + "TilesetElement.png", "C": T + "tileset_camp.png", "N": T + "TilesetNature.png",
         "B": T + "tileset_bed.png", "W": T + "TilesetWater.png", "D": T + "TilesetFloorDetail.png", "P": T + "Pipes.png",
         "F": T + "TilesetFloor.png", "I": T + "Interior/TilesetInteriorFloor.png"}

# name: (sheet, x, y, w, h) in pixels, or (sheet, "cell", col, row[, cols, rows]) for whole 16-pixel cells.
# A dict after it adds keys to the sprite (anchor, anims, slice ...).
PACK = {}


def cell(sheet, col, row, cols=1, rows=1, **extra):
    return (SHEET.get(sheet, sheet), col * 16, row * 16, cols * 16, rows * 16, extra)


def px(sheet, x, y, w, h, **extra):
    return (SHEET.get(sheet, sheet), x, y, w, h, extra)


def patch(prefix, sheet, col, row):
    """A 3 x 3 block of floor: corners, edges and middle, so a floor of any size gets its border."""
    for j, ns in enumerate(("n", "", "s")):
        for i, we in enumerate(("w", "", "e")):
            PACK["%s.%s" % (prefix, (ns + we) or "c")] = cell(sheet, col + i, row + j)


# ---- floors and outdoor ground ----
patch("tile.floor.brick.cream", "I", 0, 0)
patch("tile.floor.brick.orange", "I", 0, 6)
patch("tile.floor.cobble", "I", 0, 12)
patch("tile.floor.cobble.dark", "I", 11, 12)
patch("tile.carpet.tan", "I", 11, 0)
patch("tile.carpet.green", "I", 11, 6)
patch("tile.soil", "F", 11, 7)            # dark soil with a grass edge: a planting bed of any size
patch("tile.soil.light", "F", 0, 7)
PACK.update({
    "tile.floor.planks": cell("W", 1, 13),
    "tile.grass": cell("F", 11, 12), "tile.grass.1": cell("F", 12, 12), "tile.grass.2": cell("F", 13, 12), "tile.grass.3": cell("F", 15, 12),
    "tile.grass.light": cell("F", 0, 12), "tile.grass.light.1": cell("F", 1, 12), "tile.grass.light.2": cell("F", 2, 12), "tile.grass.light.3": cell("F", 4, 12),
    "tile.path": cell("F", 14, 8), "tile.path.n": cell("F", 14, 7), "tile.path.s": cell("F", 14, 9),
    "tile.fence": cell("H", 11, 5), "tile.fence.w": cell("H", 11, 4), "tile.fence.e": cell("H", 11, 4),
    "tile.fence.nw": cell("H", 8, 4), "tile.fence.ne": cell("H", 9, 4), "tile.fence.sw": cell("H", 8, 5), "tile.fence.se": cell("H", 9, 5),
})

# ---- fixtures the pack has ----
PACK.update({
    "fix.plant": px("E", 0, 120, 15, 24),
    "fix.bed": px("B", 192, 48, 16, 32, anchor=[0, 0]),                     # a bed lies on its own tile and the one south of it
    "fix.herb patch": cell("N", 8, 10), "fix.herb patch.growing": cell("N", 8, 10), "fix.herb patch.ripe": cell("N", 6, 11),
    "fix.old bench": px("C", 2, 113, 44, 14, anchor=[14, -2]),               # three tiles wide, its tile in the middle
    "fix.barrel": px("H", 288, 234, 16, 22),
    "fix.shelf": px("E", 64, 113, 16, 29),
    "fix.trunk": px("C", 65, 129, 14, 14, anchor=[-1, -2]), "fix.trunk.closed": px("C", 65, 129, 14, 14, anchor=[-1, -2]),
    "fix.trunk.open": px("C", 81, 129, 14, 14, anchor=[-1, -2]),
    "fix.reeds": cell("N", 7, 10),
    "fix.flat stone": px("B", 33, 176, 29, 16, anchor=[-1, 0]),              # two tiles wide
    "fix.workbench": px("H", 466, 132, 28, 23, anchor=[-2, 7]),              # two tiles wide
    "fix.stool": px("E", 80, 119, 16, 9, anchor=[0, -6]),
    "fix.rug": cell("I", 14, 5),                                              # the middle of the music room's carpet
    "fix.crates": px("E", 67, 60, 27, 20, anchor=[-2, 4]),                    # two tiles wide
    "fix.shelves": px("E", 160, 113, 32, 29),                                 # two tiles wide
    "crate": px("E", 1, 1, 14, 15, anchor=[-1, -1]),
    # somewhere to keep things in every room: the pack's own chest, basket, box and shelves (the music room's is drawn: art.py)
    "fix.toy chest": px("E", 48, 17, 16, 13), "fix.reed basket": px("C", 81, 80, 15, 16), "fix.tool box": px("E", 33, 99, 14, 12, anchor=[-1, -3]),
    "fix.pot shelf": px("E", 64, 113, 16, 29), "fix.attic shelf": px("E", 48, 113, 16, 29), "fix.long shelf": px("E", 160, 113, 32, 29),   # the last is two tiles wide
})

# ---- scenery ----
PACK.update({
    "decor.bed.red": px("B", 80, 48, 16, 32, anchor=[0, 0]),
    "decor.rug.white": px("B", 34, 98, 44, 29, anchor=[-2, -1]),             # three tiles by two
    "decor.bookshelf": px("E", 48, 113, 16, 29), "decor.shelf.pots": px("E", 64, 113, 16, 29),
    "decor.drawers": px("E", 32, 120, 16, 24), "decor.dresser": px("E", 16, 121, 16, 23), "decor.dresser.wide": px("E", 96, 121, 32, 23),
    "decor.bookshelf.wide": px("E", 128, 112, 32, 30), "decor.shelf.wide": px("E", 160, 113, 32, 29),
    "decor.table": px("E", 48, 145, 16, 15), "decor.counter": px("E", 33, 162, 45, 13, anchor=[-1, -3]),
    "decor.pot": px("E", 33, 146, 14, 14, anchor=[-1, -2]), "decor.urn": px("E", 17, 0, 14, 16, anchor=[-1, 0]), "decor.vase": px("E", 1, 160, 14, 15, anchor=[-1, -1]),
    "decor.plant": px("E", 0, 120, 15, 24),
    "decor.grate": px("E", 16, 176, 16, 15, anchor=[0, 9]),                   # the cellar's one high window
    "decor.crate": px("E", 1, 1, 14, 15, anchor=[-1, -1]), "decor.crates": px("E", 67, 60, 27, 20, anchor=[-2, 4]),
    "decor.crate.apples": cell("H", 19, 14), "decor.crate.bread": cell("H", 20, 14), "decor.crate.empty": cell("H", 19, 15),
    "decor.barrel": px("H", 288, 234, 16, 22), "decor.barrel.open": px("H", 256, 235, 16, 21), "decor.barrel.dark": px("H", 272, 236, 16, 20),
    "decor.tub": cell("H", 16, 13), "decor.keg": cell("H", 18, 11), "decor.sack": px("H", 481, 257, 14, 15, anchor=[-1, -1]),
    "decor.planks": px("H", 496, 258, 32, 13, anchor=[0, -3]), "decor.plank.tall": px("H", 514, 272, 13, 32, anchor=[-2, 16]),
    "decor.logs": px("H", 498, 288, 13, 16, anchor=[-2, 0]), "decor.bucket": px("H", 465, 289, 15, 14, anchor=[0, -2]),
    "decor.banner.1": cell("H", 22, 20, 1, 2), "decor.banner.2": cell("H", 23, 20, 1, 2), "decor.banner.3": cell("H", 24, 20, 1, 2),
    "decor.banner.4": cell("H", 25, 20, 1, 2), "decor.banner.5": cell("H", 26, 20, 1, 2), "decor.banner.6": cell("H", 27, 20, 1, 2),
    "decor.cask": cell("C", 4, 6, 2, 2), "decor.barrel.small": cell("C", 4, 5), "decor.basket": px("C", 81, 80, 15, 16),
    "decor.urn.tall": cell("C", 6, 7, 1, 2), "decor.firewood": px("C", 65, 64, 14, 16, anchor=[-1, 0]),
    "decor.twigs": px("C", 193, 130, 15, 12, anchor=[0, -3]), "decor.twigs.small": px("C", 213, 135, 11, 7, anchor=[-3, -6]),
    "decor.sprout": px("C", 50, 131, 11, 9, anchor=[-3, -5]), "decor.mound": px("C", 0, 129, 16, 14, anchor=[0, -2]),
    "decor.anvil": cell("Items/Tool/Anvil.png", 0, 0),
    "decor.tool.hammer": cell("Items/Tool/Hammer.png", 0, 0, anchor=[0, 8]), "decor.tool.axe": cell("Items/Tool/Axe.png", 0, 0, anchor=[0, 8]),
    "decor.tool.pickaxe": cell("Items/Tool/Pickaxe.png", 0, 0, anchor=[0, 8]), "decor.tool.sickle": cell("Items/Tool/Sickle.png", 0, 0, anchor=[0, 8]),
    "decor.tool.shovel": cell("Items/Tool/Shovel.png", 0, 0, anchor=[0, 8]),
    "decor.watering can": cell("Items/Tool/WateringCan.png", 0, 0),
    "decor.flower.sun": cell("N", 0, 11), "decor.flower.red": cell("N", 3, 11), "decor.flower.white": cell("N", 6, 11),
    "decor.grass.tuft": cell("N", 4, 10), "decor.grass.tall": cell("N", 7, 10), "decor.bush": cell("N", 1, 10),
        "decor.rock": cell("N", 15, 9),
})

# ---- what leaf and wood grow on (the other bits' sources are drawn: draw.py GROWN) ----
PACK.update({
    "grows.leaf": cell("N", 0, 10), "grows.leaf.bare": cell("N", 5, 9),
    "grows.wood": px("C", 65, 64, 14, 16, anchor=[-1, 0]), "grows.wood.bare": px("C", 213, 135, 11, 7, anchor=[-3, -6]),
})

# ---- bits the pack has, small creatures, feelings, effects, bubbles ----
ACT = "Actor/Animal/"
side = lambda fps: {"idle": {"frames": [[0, 0]], "fps": 1}, "walk.right": {"frames": [[0, 0], [1, 0]], "fps": fps}, "walk.down": {"frames": [[0, 0], [1, 0]], "fps": fps},
                    "walk.left": {"frames": [[0, 0], [1, 0]], "fps": fps, "flip": True}, "walk.up": {"frames": [[0, 0], [1, 0]], "fps": fps, "flip": True}}
strip = lambda n, fps, name="play": {name: {"frames": [[i, 0] for i in range(n)], "fps": fps}}
PACK.update({
    "creature.mouse": px(ACT + "Hamster/SpriteSheetGray.png", 0, 0, 15, 15, anims=side(8), anchor=[0, -1]),
    "creature.bird": px(ACT + "Parrot/SpriteSheetBlue.png", 0, 0, 16, 16, anims=side(6)),
    "fx.sparkle": px("FX/Particle/Spark.png", 0, 0, 10, 8, anims=strip(7, 12), anchor=[-3, -4]),
    "fx.puff": px("FX/Smoke/Smoke/SpriteSheet.png", 0, 0, 32, 32, anims=strip(6, 12), anchor=[8, 12]),
    "fx.flash": px("FX/Magic/Circle/SpriteSheetSpark.png", 0, 0, 32, 32, anims=strip(6, 14), anchor=[8, 10]),
    "fx.heart": px("Ui/Receptacle/IconHeart.png", 0, 0, 14, 12, anchor=[-1, 4]),
    "fx.dust": px("FX/Smoke/SmokeCircular/SpriteSheet.png", 0, 0, 30, 14, anims=strip(8, 14), anchor=[7, -4]),
    "fx.rain": px("FX/Particle/Rain.png", 0, 0, 8, 8, anims=strip(3, 1, "kinds")), "fx.rain.splash": px("FX/Particle/RainOnFloor.png", 0, 0, 8, 8, anims=strip(3, 10)),
    "fx.snow": px("FX/Particle/Snow.png", 0, 0, 8, 8, anims=strip(7, 1, "kinds")),
    "fx.leaf": px("FX/Particle/Leaf.png", 0, 0, 12, 7, anims=strip(6, 8)),
    "ui.bubble.say": px("Ui/Theme/Wip/ThemeBubble/nine_path_panel.png", 0, 0, 16, 16, slice=[5, 5, 5, 6]),
    "ui.plate": px("Ui/Theme/Theme Wood/nine_path_bg.png", 0, 0, 16, 16, slice=[5, 5, 5, 5]),
    "ui.panel": px("Ui/Dialog/ChoiceBox.png", 0, 0, 64, 20, slice=[5, 5, 5, 5]),
})
EMOTES = {"happy": 6, "sleepy": 28, "scared": 1, "curious": 23,
          "sad": 16, "love": 27, "heartbroken": 26, "surprised": 21, "alarm": 22, "proud": 29, "sick": 15, "cross": 9, "calm": 11}
for mood, n in EMOTES.items():
    PACK["emote." + mood] = px("Ui/Emote/emote%d.png" % n, 0, 0, 14, 13, anchor=[-1, -2])

# ---- sounds: quiet, under the pets' own voices ----
S = "Audio/Sounds/"
SFX = {"pickup": "Bonus/Bonus2.wav", "drop": "Jump & Bounce/Bounce4.wav", "make": "Magic & Skill/Heal3.wav", "unmake": "Whoosh & Slash/Whoosh.wav",
       "combine": "Magic & Skill/Magic2.wav", "door": "Hit & Impact/Impact2.wav", "step": "Menu/Move2.wav", "eat": "Elemental/Bubble2.wav",
       "write": "Elemental/Grass.wav", "book": "Whoosh & Slash/Launch.wav", "call": "Creature/Bird.wav", "heart": "Bonus/Bonus3.wav",
       "radio": "Magic & Skill/Fx.wav", "arrival": "Bonus/PowerUp1.wav", "arrival.writing": "Menu/Accept3.wav", "arrival.songs": "Menu/Accept.wav",
       "arrival.taming": "Creature/Wings.wav", "arrival.radio": "Magic & Skill/Spirit.wav", "arrival.book": "Menu/Accept8.wav",
       "arrival.strangers": "Bonus/Bonus.wav", "drip": "Elemental/WaterDrop.wav", "rain": "Ambient/Rain.wav", "splash": "Elemental/Water6.wav",
       "bounce": "Jump & Bounce/Bounce.wav",
       # things that sound when used (INSTRUMENTS): one clear note, a rising run of four, an octave ring, a falling thud, two soft pure notes, a rattle
       "bell": "Bonus/Coin.wav", "chime": "Bonus/Coin2.wav", "chimes": "Bonus/Gold1.wav", "drum": "Hit & Impact/Impact.wav",
       "flute": "Audio/Jingles/Success1.wav", "clatter": "Hit & Impact/Hit5.wav"}
MUSIC = {"nursery": "5 - Peaceful.ogg", "garden": "11 - Clearing.ogg", "cellar": "2 - The Cave.ogg", "attic": "9 - Quiet.ogg", "pond": "18 - Aquatic.ogg",
         "workshop": "4 - Village.ogg", "music": "27 - Chill.ogg", "greenhouse": "13 - Mystical.ogg", "storeroom": "26 - Lost Village.ogg"}


# The visitor's music by mood (SPEC-v3.3 §3.1). The number is how loud the track is by itself (root mean square of its
# samples, measured once by decoding it in a browser: nothing here reads ogg); the gain evens the tracks out.
MOODS = {"calm": {"5 - Peaceful.ogg": 0.146, "9 - Quiet.ogg": 0.186, "27 - Chill.ogg": 0.057},
         "lively": {"20 - Good Time.ogg": 0.073, "31 - Sunny.ogg": 0.128, "23 - Road.ogg": 0.135, "4 - Village.ogg": 0.097},
         "mysterious": {"13 - Mystical.ogg": 0.156, "2 - The Cave.ogg": 0.151, "26 - Lost Village.ogg": 0.049, "30 - Ruins.ogg": 0.049},
         "sad": {"7 - Sad Theme.ogg": 0.040, "16 - Melancholia.ogg": 0.084, "29 - Lament.ogg": 0.088}}

# What each room sounds like by itself (SPEC-v3.3 §4), and the weather on top: a file of the pack that loops, or a
# sound the page makes (README.md says what the keys mean). Quiet, and no two rooms alike.
LOOP = lambda f, gain: {"pack": "ninja", "file": S + "Ambient/" + f, "gain": gain}
AMBIENCE = {
    "rooms": {
        "nursery": [{"synth": "crackle", "gain": 0.03, "rate": 1, "steady": True, "says": "a clock: one soft tick a second, evenly, tick then tock"}],
        "garden": [{"synth": "wind", "gain": 0.04, "rate": 0.15, "pitch": 500, "says": "a light breeze in leaves, coming and going"},
                   {"synth": "birds", "gain": 0.05, "rate": 0.2, "sfx": "call", "when": "day", "says": "a few birds, now here, now there, never a chorus"},
                   {"synth": "crickets", "gain": 0.03, "rate": 2, "when": "night", "says": "crickets after dark"}],
        "cellar": [{"synth": "drips", "gain": 0.05, "rate": 0.15, "echo": 0.7, "sfx": "drip", "says": "slow drips with a long echo"},
                   {"synth": "wind", "gain": 0.02, "rate": 0.05, "pitch": 90, "says": "a low draught, more felt than heard"}],
        "attic": [{"synth": "wind", "gain": 0.045, "rate": 0.1, "pitch": 900, "says": "wind under the eaves: thin, rising to a faint whistle and falling away"},
                  {"synth": "creak", "gain": 0.035, "rate": 0.04, "says": "a rafter creaks now and then"}],
        "pond": [{"synth": "water", "gain": 0.05, "rate": 0.3, "says": "still water lapping at its edge"},
                 {"synth": "wind", "gain": 0.02, "rate": 0.3, "pitch": 3000, "says": "reeds rustling: dry, high, in short breaths"},
                 {"synth": "drips", "gain": 0.04, "rate": 0.05, "sfx": "splash", "says": "a plop now and then, as something surfaces"}],
        "workshop": [{"synth": "creak", "gain": 0.04, "rate": 0.08, "says": "timber and the bench settling"},
                     {"synth": "crackle", "gain": 0.025, "rate": 1.5, "says": "small uneven ticks, like metal cooling"}],
        "music": [{"synth": "hum", "gain": 0.02, "pitch": 440, "says": "a faint ringing, as if the strings were answering the room: pure, high, slowly swelling"}],
        "greenhouse": [{"synth": "hum", "gain": 0.03, "pitch": 70, "says": "a warm low hum from the hot pipe"},
                       {"synth": "crackle", "gain": 0.015, "rate": 0.4, "says": "the pipe ticking as it warms"},
                       {"synth": "drips", "gain": 0.025, "rate": 0.06, "sfx": "drip", "says": "condensation dripping off the glass, close by, no echo"}],
        "storeroom": [{"synth": "creak", "gain": 0.02, "rate": 0.02, "says": "near silence: a board settles about once a minute"}]},
    "weather": {
        "rain": [LOOP("Rain.wav", 0.3)],
        "storm": [LOOP("Rain.wav", 0.4), LOOP("Storm.wav", 0.35)],   # the second is the thunder: low rolls, four in fourteen seconds
        "snow": [{"synth": "wind", "gain": 0.025, "rate": 0.05, "pitch": 250, "says": "a hush: slow soft wind, muffled, nothing sharp"}],
        "heat": [{"synth": "crickets", "gain": 0.03, "rate": 6, "says": "cicadas: a dry steady shimmer"}]}}

# The sound of a thing that sounds when used (SPEC-v3.3 §4), by its kind or its fixture name -> an effect in SFX.
# "default" is for any other noisy thing; "hum" is a thing humming by itself, which the page makes.
INSTRUMENTS = {"bell": "bell", "drum": "drum", "wind chime": "chime", "flute": "flute", "chimes": "chimes", "default": "clatter",
               "hum": {"synth": "hum", "gain": 0.04, "pitch": 180, "says": "one steady note with a slow wobble, coming from the thing itself"}}


def named(x):
    """Every pack file a piece of sounds.json names, however deep it lies."""
    if isinstance(x, dict) and "file" in x:
        yield x["file"]
    elif isinstance(x, (dict, list)):
        for v in (x.values() if isinstance(x, dict) else x):
            yield from named(v)


def loudness(path):
    import array, math
    w = wave.open(path)
    a = array.array("h", w.readframes(w.getnframes())) if w.getsampwidth() == 2 else [1638]
    return math.sqrt(sum(x * x for x in a[::5]) / max(1, len(a[::5]))) / 32768


def sounds(pack):
    """Every effect about as loud as every other: quieter files get the higher gain, all within 0.15 to 0.35."""
    sfx = {n: f if f.startswith("Audio/") else S + f for n, f in SFX.items()}
    sfx = {n: {"pack": "ninja", "file": f, "gain": round(max(0.15, min(0.35, 0.25 * 0.05 / max(loudness(os.path.join(pack, f)), 0.001))), 2)} for n, f in sfx.items()}
    moods = {m: [{"pack": "ninja", "file": "Audio/Musics/" + f, "gain": round(max(0.05, min(0.3, 0.012 / rms)), 2)} for f, rms in tracks.items()] for m, tracks in MOODS.items()}
    return {"sfx": sfx, "music": {n: {"pack": "ninja", "file": "Audio/Musics/" + f, "gain": 0.1} for n, f in MUSIC.items()},
            "moods": moods, "ambience": AMBIENCE, "instruments": INSTRUMENTS}


# ---- rooms ----
W_, H_ = 12, 8


def grid(fill=None):
    return [[fill] * 14 for _ in range(11)]


def floor9(g, prefix, x0=0, y0=0, x1=W_ - 1, y1=H_ - 1):
    """Lay a 3 x 3 floor block over floor tiles x0..x1, y0..y1."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            part = ("n" if y == y0 else "s" if y == y1 else "") + ("w" if x == x0 else "e" if x == x1 else "")
            g[y + 2][x + 1] = "%s.%s" % (prefix, part or "c")


def walls(style):
    g = grid()
    p = "tile.wall.%s." % style
    g[0] = [p + "nw"] + [p + "n0"] * 12 + [p + "ne"]
    g[1] = [p + "w"] + [p + "n1"] * 12 + [p + "e"]
    for y in range(2, 10):
        g[y][0], g[y][13] = p + "w", p + "e"
    g[10] = [p + "sw"] + [p + "s"] * 12 + [p + "se"]
    return g


def fill(g, name, variants=()):
    """One floor tile everywhere, with a few variants scattered the same way every time."""
    for y in range(8):
        for x in range(12):
            k = (x * 7 + y * 13 + x * y) % 11
            g[y + 2][x + 1] = variants[k % len(variants)] if variants and k < 3 else name


def D(sprite, x, y, layer="floor"):
    return {"sprite": sprite, "at": [x, y], "layer": layer}


def nursery():
    f = grid(); fill(f, "tile.floor.planks")
    return {"type": "nursery", "floor": f, "walls": walls("plaster"),
            "decor": [D("decor.rug.white", 4, 3), D("decor.bookshelf", 1, 0), D("decor.blocks", 1, 1), D("decor.drawers", 10, 0),
                      D("decor.bed.red", 11, 0)],
            "fixtures": {"lamp": {"pos": [0, 0], "sprite": "fix.lamp"}, "window": {"pos": [2, 0], "sprite": "fix.window", "wall": True},
                         "mirror": {"pos": [5, 0], "sprite": "fix.mirror", "wall": True}, "bed": {"pos": [9, 0], "sprite": "fix.bed"},
                         "bowl": {"pos": [0, 7], "sprite": "fix.bowl"}, "music box": {"pos": [0, 3], "sprite": "fix.music box"},
                         "plant": {"pos": [11, 6], "sprite": "fix.plant"}, "ball": {"pos": [5, 4], "sprite": "fix.ball"},
                         "blanket": {"pos": [8, 2], "sprite": "fix.blanket"}, "rock": {"pos": [2, 6], "sprite": "fix.rock"},
                         "heavy book": {"pos": [4, 7], "sprite": "fix.heavy book"}, "toy chest": {"pos": [4, 0], "sprite": "fix.toy chest"}},
            "blocked": [[1, 0], [1, 1], [9, 1], [10, 0], [11, 0], [11, 1]],
            "wall_slots": [[3, 0], [6, 0], [8, 0]],
            "bit_spots": {"fluff": [[8, 3], [10, 3], [6, 5], [4, 2]], "pebble": [[3, 6], [1, 6], [9, 6]], "wax": [[0, 1], [2, 1], [3, 1]]},
            "light": {"window": [[2, 0]], "night": 0.5}}


def garden():
    f = grid("tile.grass")
    fill(f, "tile.grass", ("tile.grass.1", "tile.grass.2", "tile.grass.3"))
    f[0] = ["tile.sky"] * 14
    for x in (2, 3, 9):
        f[0][x] = "tile.sky.cloud"
    f[1] = ["tile.sky.hedge"] * 14
    for y in range(8):
        f[y + 2][8] = "tile.path"
    f[10][8] = "tile.path"
    floor9(f, "tile.soil", 1, 1, 4, 2)
    floor9(f, "tile.soil", 2, 6, 4, 7)
    w = grid()
    w[1] = ["tile.fence.nw"] + ["tile.fence"] * 12 + ["tile.fence.ne"]
    for y in range(2, 10):
        w[y][0], w[y][13] = "tile.fence.w", "tile.fence.e"
    w[10] = ["tile.fence.sw"] + ["tile.fence"] * 12 + ["tile.fence.se"]
    return {"type": "garden", "floor": f, "walls": w, "doors": "gate",
            "decor": [D("decor.sprout", 1, 1), D("decor.sprout", 3, 1), D("decor.sprout", 4, 1), D("decor.sprout", 1, 2), D("decor.sprout", 3, 2),
                      D("decor.sprout", 2, 6), D("decor.sprout", 4, 6), D("decor.sprout", 2, 7), D("decor.sprout", 4, 7),
                      D("decor.flower.sun", 0, 0), D("decor.flower.red", 5, 0), D("decor.flower.white", 6, 0), D("decor.flower.sun", 11, 7),
                      D("decor.flower.red", 0, 7), D("decor.bush", 0, 3), D("decor.bush", 11, 2),
                      D("decor.stepping stone", 1, 5), D("decor.stepping stone", 3, 5), D("decor.stepping stone", 5, 5), D("decor.stepping stone", 10, 4), D("decor.stepping stone", 8, 4)],
            "fixtures": {"bean row": {"pos": [2, 1], "sprite": "fix.bean row"}, "herb patch": {"pos": [3, 6], "sprite": "fix.herb patch"},
                         "berry bush": {"pos": [10, 6], "sprite": "fix.berry bush"}, "old bench": {"pos": [10, 0], "sprite": "fix.old bench"},
                         "bird bath": {"pos": [10, 2], "sprite": "fix.bird bath"}, "tool box": {"pos": [11, 1], "sprite": "fix.tool box"}},
            "blocked": [[9, 0], [11, 0], [0, 0], [5, 0], [6, 0], [11, 7], [0, 7], [0, 3], [11, 2]],
            "wall_slots": [[2, 0], [4, 0]],
            "bit_spots": {"seed": [[1, 2], [3, 2], [4, 2], [2, 7]], "leaf": [[8, 6], [9, 6], [11, 5], [6, 1]], "petal": [[1, 0], [4, 0], [1, 7], [10, 7]]},
            "light": {"window": [], "night": 0.55, "sky": "open"}}


def cellar():
    f = grid(); floor9(f, "tile.floor.cobble.dark")
    return {"type": "cellar", "floor": f, "walls": walls("stone"),
            "decor": [D("decor.grate", 3, -1, "wall"), D("decor.cobweb", 0, -2, "wall"), D("decor.cobweb.right", 11, -2, "wall"),
                      D("decor.barrel.open", 1, 0), D("decor.barrel.dark", 0, 1),
                      D("decor.urn.tall", 11, 0), D("decor.crate", 11, 7), D("decor.sack", 11, 6), D("decor.keg", 0, 7),
                      D("decor.crate.empty", 1, 7)],
            "fixtures": {"barrel": {"pos": [0, 0], "sprite": "fix.barrel"}, "shelf": {"pos": [10, 0], "sprite": "fix.shelf"},
                         "lantern": {"pos": [5, 0], "sprite": "fix.lantern", "wall": True}, "old rug": {"pos": [5, 4], "sprite": "fix.old rug"},
                         "long shelf": {"pos": [8, 0], "sprite": "fix.long shelf"}},
            "blocked": [[1, 0], [0, 1], [9, 0], [11, 0], [11, 7], [11, 6], [0, 7], [1, 7]],
            "wall_slots": [[2, 0], [4, 0], [6, 0]],
            "bit_spots": {"clay": [[3, 6], [4, 7], [2, 3], [9, 6]], "moss": [[1, 2], [0, 3], [11, 2], [10, 7], [2, 7]], "soot": [[4, 1], [6, 1], [5, 1]]},
            "light": {"window": [[3, 0]], "night": 0.75, "day": 0.3}}


def attic():
    f = grid(); fill(f, "tile.floor.boards.old")
    return {"type": "attic", "floor": f, "walls": walls("attic"),
            "decor": [D("decor.roof.left", 0, -1, "wall"), D("decor.roof.right", 11, -1, "wall"), D("decor.cobweb", 3, -2, "wall"), D("decor.cobweb.right", 8, -2, "wall"),
                      D("decor.crate", 0, 0), D("decor.crate", 0, 1),
                      D("decor.dresser.wide", 2, 0), D("decor.drawers", 11, 0), D("decor.basket", 11, 1), D("decor.sack", 0, 7),
                      D("decor.barrel.small", 11, 7)],
            "fixtures": {"skylight": {"pos": [5, 0], "sprite": "fix.skylight", "wall": True}, "trunk": {"pos": [1, 0], "sprite": "fix.trunk"},
                         "rocking chair": {"pos": [10, 6], "sprite": "fix.rocking chair"}, "sun shaft": {"pos": [5, 3], "sprite": "fix.sun shaft"},
                         "heavy book": {"pos": [9, 0], "sprite": "fix.heavy book"}, "attic shelf": {"pos": [10, 0], "sprite": "fix.attic shelf"}},
            "blocked": [[0, 0], [0, 1], [2, 0], [3, 0], [11, 0], [11, 1], [0, 7], [11, 7]],
            "wall_slots": [[4, 0], [6, 0], [8, 0]],
            "bit_spots": {"feather": [[2, 2], [3, 5], [8, 6], [6, 6]], "cloth": [[1, 2], [2, 1], [9, 2]], "wood": [[10, 2], [4, 6], [1, 6]]},
            "light": {"window": [[5, 0]], "night": 0.6}}


POND_WATER = [[4, 3], [5, 3], [6, 3], [4, 4], [5, 4], [6, 4], [5, 5], [6, 5]]   # exactly house.toml's


def pond():
    f = grid(); fill(f, "tile.grass.light", ("tile.grass.light.1", "tile.grass.light.2", "tile.grass.light.3"))
    water = {tuple(t) for t in POND_WATER}
    for x, y in water:   # a stone rim wherever the next tile is not water
        land = "".join(k for k, (dx, dy) in (("n", (0, -1)), ("e", (1, 0)), ("s", (0, 1)), ("w", (-1, 0))) if (x + dx, y + dy) not in water)
        diag = [k for k, (dx, dy) in (("ne", (1, -1)), ("se", (1, 1)), ("sw", (-1, 1)), ("nw", (-1, -1))) if (x + dx, y + dy) not in water and (x + dx, y) in water and (x, y + dy) in water]
        f[y + 2][x + 1] = "tile.pond." + (land or "c") + ("." + diag[0] if diag and not land else "")
    return {"type": "pond", "floor": f, "walls": walls("conservatory"),
            "decor": [D("decor.grass.tall", 3, 3), D("decor.grass.tall", 4, 5), D("decor.grass.tuft", 7, 5), D("decor.grass.tuft", 3, 2),
                      D("decor.stepping stone", 8, 4), D("decor.stepping stone", 9, 4), D("decor.stepping stone", 10, 4), D("decor.stepping stone", 7, 1), D("decor.stepping stone", 7, 6),
                      D("decor.plant", 0, 0), D("decor.plant", 11, 0), D("decor.flower.white", 2, 2), D("decor.flower.white", 9, 6),
                      D("decor.rock", 8, 2)],
            "fixtures": {"pond": {"pos": [5, 4], "sprite": "fix.pond"}, "reeds": {"pos": [7, 3], "sprite": "fix.reeds"},
                         "flat stone": {"pos": [2, 5], "sprite": "fix.flat stone"}, "reed basket": {"pos": [6, 2], "sprite": "fix.reed basket"}},
            "blocked": [[3, 5], [0, 0], [11, 0], [8, 2], [2, 2], [9, 6]],
            "wall_slots": [[2, 0], [5, 0], [9, 0]],
            "bit_spots": {"shell": [[3, 4], [4, 6], [7, 4], [5, 2]], "bead": [[8, 5], [4, 2], [6, 6]], "reed": [[7, 2], [8, 3], [3, 3], [4, 5]]},
            "light": {"window": [[1, 0], [4, 0], [6, 0], [10, 0]], "night": 0.5}}


def workshop():
    f = grid(); floor9(f, "tile.floor.cobble")
    return {"type": "workshop", "floor": f, "walls": walls("panel"),
            "decor": [D("decor.tool.hammer", 4, -1, "wall"), D("decor.tool.sickle", 5, -1, "wall"), D("decor.tool.pickaxe", 9, -1, "wall"), D("decor.tool.shovel", 10, -1, "wall"),
                      D("decor.tool.axe", 11, -1, "wall"),
                      D("decor.counter", 9, 0), D("decor.anvil", 9, 2), D("decor.plank.tall", 0, 0), D("decor.planks", 0, 1),
                      D("decor.logs", 0, 7), D("decor.crate", 11, 7), D("decor.bucket", 10, 7), D("decor.barrel.small", 11, 6),
                      D("decor.twigs", 5, 2), D("decor.twigs.small", 6, 3), D("decor.twigs.small", 3, 2), D("decor.twigs", 8, 3), D("decor.twigs.small", 4, 4), D("decor.twigs.small", 10, 3)],
            "fixtures": {"workbench": {"pos": [4, 0], "sprite": "fix.workbench"}, "work lamp": {"pos": [6, 0], "sprite": "fix.work lamp"},
                         "stool": {"pos": [5, 1], "sprite": "fix.stool"}, "window": {"pos": [1, 0], "sprite": "fix.window", "wall": True}},
            "blocked": [[5, 0], [9, 0], [10, 0], [11, 0], [9, 2], [0, 0], [0, 1], [1, 1], [0, 7], [11, 7], [10, 7], [11, 6]],
            "wall_slots": [[2, 0], [3, 0], [8, 0]],
            "bit_spots": {"wire": [[8, 1], [10, 2], [7, 2], [3, 1]], "wood": [[1, 2], [2, 3], [2, 1]], "metal": [[10, 3], [8, 2], [9, 3]]},
            "light": {"window": [[1, 0]], "night": 0.55}}


def music():
    f = grid(); floor9(f, "tile.floor.brick.cream")
    floor9(f, "tile.carpet.tan", 4, 3, 6, 5)
    floor9(f, "tile.carpet.green", 1, 1, 3, 3)
    return {"type": "music", "floor": f, "walls": walls("paper"),
            "decor": [D("decor.banner.2", 5, -1, "wall"), D("decor.banner.6", 0, -1, "wall"), D("decor.banner.4", 3, -1, "wall"),
                      D("decor.harp", 4, 0), D("decor.gong", 10, 0), D("decor.table", 0, 0), D("decor.vase", 0, 7)],
            "fixtures": {"drum": {"pos": [2, 2], "sprite": "fix.drum"}, "chimes": {"pos": [9, 0], "sprite": "fix.chimes"},
                         "rug": {"pos": [5, 4], "sprite": "fix.rug"}, "window": {"pos": [1, 0], "sprite": "fix.window", "wall": True},
                         "instrument shelf": {"pos": [11, 0], "sprite": "fix.instrument shelf"}},
            "blocked": [[4, 0], [10, 0], [0, 0], [0, 7]],
            "wall_slots": [[2, 0], [6, 0], [8, 0]],
            "bit_spots": {"string": [[4, 1], [2, 5], [10, 2]], "bell": [[8, 1], [10, 1], [9, 2], [8, 2]], "felt": [[1, 4], [3, 4], [6, 6]]},
            "light": {"window": [[1, 0]], "night": 0.5}}


def greenhouse():
    f = grid("tile.grass.light"); floor9(f, "tile.floor.brick.orange")   # glass on the north side: the grass outside shows through it
    for y in range(len(f)):   # ... and nothing beyond the side and south walls: a band of grass there read as a mistake
        for x in range(len(f[y])):
            if x in (0, len(f[y]) - 1) or y == len(f) - 1:
                f[y][x] = None
    floor9(f, "tile.soil.light", 1, 1, 3, 2)
    floor9(f, "tile.soil.light", 7, 5, 9, 6)
    floor9(f, "tile.soil.light", 1, 5, 3, 6)
    return {"type": "greenhouse", "floor": f, "walls": walls("glass"),
            "decor": [D("decor.vine.1", 0, -1, "wall"), D("decor.vine.2", 3, -1, "wall"), D("decor.vine.1", 6, -1, "wall"), D("decor.vine.2", 9, -1, "wall"), D("decor.vine.1", 11, -1, "wall"),
                      D("decor.sprout", 1, 1), D("decor.sprout", 3, 1), D("decor.sprout", 1, 2), D("decor.sprout", 3, 2), D("decor.sprout", 7, 6), D("decor.sprout", 9, 6),
                      D("decor.sprout", 7, 5), D("decor.flower.red", 1, 5), D("decor.flower.sun", 2, 5), D("decor.flower.white", 3, 5),
                      D("decor.sprout", 1, 6), D("decor.sprout", 2, 6), D("decor.sprout", 3, 6),
                      D("decor.plant", 4, 0), D("decor.pot", 5, 0), D("decor.plant", 8, 0), D("decor.vase", 9, 0), D("decor.urn", 0, 0),
                      D("decor.watering can", 0, 7), D("decor.tub", 11, 7)],
            "fixtures": {"tomato vine": {"pos": [2, 1], "sprite": "fix.tomato vine"}, "melon bed": {"pos": [8, 5], "sprite": "fix.melon bed"},
                         "hot pipe": {"pos": [11, 1], "sprite": "fix.hot pipe"}, "pot shelf": {"pos": [1, 0], "sprite": "fix.pot shelf"}},
            "blocked": [[11, 0], [11, 2], [4, 0], [5, 0], [8, 0], [9, 0], [0, 0], [0, 7], [11, 7], [1, 5], [2, 5], [3, 5]],
            "wall_slots": [[2, 0], [7, 0], [10, 0]],
            "bit_spots": {"resin": [[10, 3], [10, 1], [9, 2]], "vine": [[4, 2], [1, 3], [3, 3], [6, 1]], "petal": [[5, 1], [9, 4], [7, 4], [2, 4], [4, 1]]},
            "light": {"window": [[x, 0] for x in range(12)], "night": 0.4, "sky": "glass"}}


def storeroom():
    f = grid(); fill(f, "tile.floor.boards.dark")
    return {"type": "storeroom", "floor": f, "walls": walls("dark"),
            "decor": [D("decor.cobweb", 0, -2, "wall"), D("decor.cobweb.right", 11, -2, "wall"),
                      D("decor.crate.apples", 2, 0), D("decor.shelf.pots", 4, 0), D("decor.barrel", 8, 0), D("decor.crate", 11, 0),
                      D("decor.crate", 11, 1), D("decor.crate.empty", 0, 1), D("decor.sack", 0, 7), D("decor.sack", 1, 7),
                      D("decor.crate", 10, 7), D("decor.crate.empty", 11, 7), D("decor.keg", 11, 6), D("decor.sack", 0, 6), D("decor.barrel.small", 4, 7),
                      D("decor.crate.bread", 3, 7)],
            "fixtures": {"crates": {"pos": [0, 0], "sprite": "fix.crates"}, "shelves": {"pos": [9, 0], "sprite": "fix.shelves"},
                         "old lantern": {"pos": [6, 0], "sprite": "fix.old lantern", "wall": True}, "heavy book": {"pos": [3, 0], "sprite": "fix.heavy book"}},
            "blocked": [[1, 0], [10, 0], [2, 0], [4, 0], [8, 0], [11, 0], [11, 1], [0, 1], [0, 7], [1, 7], [10, 7], [11, 7], [11, 6], [0, 6], [4, 7], [3, 7]],
            "wall_slots": [[5, 0], [2, 0]],
            "bit_spots": {},
            "light": {"window": [], "night": 0.8, "day": 0.4}}


ROOMS = [nursery, garden, cellar, attic, pond, workshop, music, greenhouse, storeroom]


def write(own, pack):
    """Write the JSON files and bring the pack files they name into third_party."""
    sprites, used = {}, set()
    for name, (file, x, y, w, h, extra) in PACK.items():
        iw, ih = Image.open(os.path.join(pack, file)).size
        assert x + w <= iw and y + h <= ih, "%s reaches outside %s" % (name, file)
        sprites[name] = dict({"pack": "ninja", "file": file, "rect": [x, y, w, h]}, **extra)
        used.add(file)
    sprites.update(own)
    snd = sounds(pack)
    used |= set(named(snd)) | {"LICENSE.txt", FONT}
    dest = os.path.join(ASSETS, NINJA)
    for root, _, files in os.walk(dest):   # nothing unused stays
        for f in files:
            if os.path.relpath(os.path.join(root, f), dest) not in used:
                os.remove(os.path.join(root, f))
    for f in sorted(used):
        os.makedirs(os.path.dirname(os.path.join(dest, f)), exist_ok=True)
        shutil.copyfile(os.path.join(pack, f), os.path.join(dest, f))
    for root, dirs, files in os.walk(dest, topdown=False):
        if not dirs and not files:
            os.rmdir(root)
    dump = lambda name, obj, **kw: json.dump(obj, open(os.path.join(ASSETS, name), "w"), ensure_ascii=False, **kw)
    dump("packs.json", {"ninja": {"dir": NINJA, "tile": 16, "licence": "CC0", "by": "Pixel-boy and AAA", "font": FONT},
                        "own": {"dir": "own", "tile": 16, "licence": "CC0", "by": "this project"}}, indent=1)
    with open(os.path.join(ASSETS, "sprites.json"), "w") as out:   # one sprite to a line, in name order
        out.write("{\n" + ",\n".join(" %s: %s" % (json.dumps(k), json.dumps(sprites[k])) for k in sorted(sprites)) + "\n}\n")
    dump("sounds.json", snd, indent=1)
    for room in ROOMS:
        r = room()
        with open(os.path.join(ASSETS, "rooms", r["type"] + ".json"), "w") as out:
            rows = lambda g: "[\n" + ",\n".join("  " + json.dumps(row) for row in g) + "\n ]"
            rest = {k: v for k, v in r.items() if k not in ("type", "floor", "walls")}
            out.write('{\n "type": %s,\n "floor": %s,\n "walls": %s,\n' % (json.dumps(r["type"]), rows(r["floor"]), rows(r["walls"])))
            out.write(",\n".join(" %s: %s" % (json.dumps(k), json.dumps(v)) for k, v in rest.items()) + "\n}\n")
    print("wrote %d sprites, %d rooms, %d sounds; %d pack files in %s" % (len(sprites), len(ROOMS), len(snd["sfx"]) + len(snd["music"]), len(used), NINJA))
