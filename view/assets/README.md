# The art, as data

Everything the house looks and sounds like is described by the files in this folder. The view's code draws what
they say; it names no tile, no sprite sheet and no pack. To change how something looks, or to add an asset pack,
edit these files. The engine serves this folder at `/art/`, and reads `kinds.json` and `rooms/*.json` itself.

```
view/assets/
  README.md            this file
  packs.json           the asset packs: where each lives, its tile size, its licence
  sprites.json         every picture the view can draw, by a name of ours -> a rectangle in some pack's file
  kinds.json           the catalog of things a pet can make (SPEC-v3.2 §3): rules for the engine, a sprite for the view
  rooms/<type>.json    one hand-designed layout per room type: floor, walls, furniture, where things can hang
  sounds.json          sound effects and music, by a name of ours -> a file in some pack
  own/                 pieces drawn for this project in the pack's style (PNG), where a pack had nothing
  third_party/<pack>/  only the files of a pack that are actually used, with its licence, and CREDITS.md
```

## Geometry

- A source tile is 16×16 pixels. It is drawn at a whole-number scale (3, 4, 5…), nearest-neighbour, on whole pixels.
- The engine's room is a floor of **12 × 8 tiles**; a pet's `pos` is `[x, y]` with `0 ≤ x < 12`, `0 ≤ y < 8`, `y = 0`
  against the north wall.
- A room is drawn on a **canvas of 14 × 11 tiles** (224 × 176 source pixels). Floor tile `[0, 0]` is canvas tile
  `[1, 2]`: there are two rows of north wall above the floor (windows, pictures, shelves and writing go there), one
  column of wall on each side, and one row of south wall below.
- Doors are in the engine's `door_tiles` (sent in every snapshot; house.toml sets them): `north [7, 0]`,
  `south [7, 7]`, `west [0, 5]`, `east [11, 4]`. A door is drawn in the wall beside its tile.

## packs.json

```json
{ "ninja": { "dir": "third_party/ninja_adventure", "tile": 16, "licence": "CC0", "by": "Pixel-boy and AAA" },
  "own":   { "dir": "own", "tile": 16, "licence": "CC0", "by": "this project" } }
```

`"font": "<file in the pack>"` on a pack entry names a pixel font the page uses for its headings.

A pack whose licence forbids redistribution lives outside the repository: give it `"dir": "/absolute/path"` and
`"local": true`. The view must work without it (every sprite from a local pack needs a `"fallback"` sprite id).

## sprites.json

```json
{ "tile.floor.wood":   { "pack": "ninja", "file": "Backgrounds/Tilesets/Interior/TilesetInteriorFloor.png", "rect": [0, 0, 16, 16] },
  "fix.bed":           { "pack": "ninja", "file": "Backgrounds/Tilesets/tileset_bed.png", "rect": [0, 0, 16, 32], "anchor": [0, 16] },
  "creature.mouse":    { "pack": "ninja", "file": "Actor/Animal/Hamster/SpriteSheet.png", "rect": [0, 0, 16, 16],
                         "anims": { "idle": { "frames": [[0,0]], "fps": 2 }, "walk.down": { "frames": [[0,0],[0,1],[0,2],[0,3]], "fps": 8 } } },
  "kind.cushion":      { "pack": "own", "file": "kinds.png", "rect": [0, 0, 16, 16], "tint": "hue" } }
```

- `rect` is `[x, y, w, h]` in source pixels. A sprite may be bigger than a tile.
- `anchor` is the pixel of the sprite that sits on the top-left corner of its floor tile (default `[0, h - 16]`: a
  tall sprite stands on its tile and rises above it).
- `anims`: named animations as lists of `[col, row]` cells of `rect`'s size counted from `rect`'s origin, with `fps`.
- `anims` entries may carry `"flip": true`: draw the frames mirrored left to right (a sheet that only faces right).
- `slice`: `[left, top, right, bottom]` marks a nine-slice piece (bubbles, plates, panels): the corners keep their
  size and the middle stretches. A bubble's tail is a sprite of its own (`ui.bubble.say.tail`).
- `tint`: `"hue"` means the view recolours it to a made thing's colour (hue and saturation replaced, lightness
  kept, outline and highlights left alone); absent means draw as is.
- Names of ours, by prefix: `tile.*` floors and walls · `decor.*` furniture that is only scenery · `fix.<fixture
  name>` the engine's fixtures (lamp, bed, bowl, music box, dial box, heavy book, …; `fix.<name>.<state>` where a
  state looks different: `fix.lamp.on`) · `kind.<kind>` made things · `bit.<bit>` things to gather ·
  `grows.<bit>` and `grows.<bit>.bare` what a room grows that bit on (below) ·
  `creature.<kind>` · `emote.<mood>` (tired, uneasy, lonely, bored, content, and more) · `fx.*` puffs, sparkles,
  hearts, notes, z's · `ui.*` bubbles and frames · `icon.room.<type>` for the minimap · `icon.act.<icon>` what a
  pet's body is doing by itself, to go over its head (one for each `icon` in activities.toml: 12 × 12, a sign on a
  small white plate so it reads on any floor) · `door.<state>` · `egg` · `stone` (a memorial).
- `fix.little radio` (`.on`, `.off`) is the visitor's own radio, set down in a room until the pets find theirs.
- A bit a room grows is drawn on its source, standing on the bit's tile like a fixture: `grows.<bit>` with the bit on
  it (petals on a flower, feathers in a nest, reed among the reeds), `grows.<bit>.bare` after it has been picked,
  until it grows back. Only a bit a pet dropped is drawn loose, as `bit.<bit>`. A bit with no `grows.*` sprite is
  drawn loose as before, and not at all while it grows back, so a pack can bring sources by adding these names.
  Ours are in `own/bits.png` (`own/src/draw.py`, `GROWN`: a source from `art.py` with the bit's own picture set on
  it), but for leaf and wood, which grow on pictures of the pack.

## kinds.json

```json
{ "cushion": { "rank": 1, "wall": false, "not": ["glassy", "noisy", "hard", "heavy"], "sprite": "kind.cushion", "a": "a" },
  "picture": { "rank": 2, "wall": true,  "not": ["soft", "sweet"], "sprite": "kind.picture", "a": "a" } }
```

- `rank` 1 to 3: how complex a kind is. Combining two things gives the higher-ranked kind; two different kinds of
  equal rank give a `mobile` or a `sculpture` (engine/things.py).
- `wall`: it hangs on a wall instead of standing on the floor.
- `not`: materials this kind cannot be made of (a candle cannot be springy). Everything else is allowed.
- `a`: the article, for sentences ("a cushion", "an urn").
- `flat`: it lies flat on the floor (a rug, a blanket) and can be walked over; the view's pets walk round anything else.
- `store`: it keeps things, this many (a shelf, a chest, a crate, a basket, a box). `inside`: they go in it, out of
  sight, instead of on it.
- `hooks`: things can be hung on it, this many (a wall hook). `hangs`: a pet can hang it on a wall or on a hook.
- The engine reads `rank`, `wall`, `not`, `a`, `flat`, `store`, `inside`, `hooks`, `hangs`. The view reads `sprite`.

## rooms/<type>.json

```json
{ "type": "nursery",
  "floor": [[ "tile.floor.wood", "..." ]],              14 × 11 sprite names (or null), drawn first, canvas coordinates
  "walls": [[ null, "tile.wall.n", "..." ]],            14 × 11, drawn over the floor
  "decor": [ { "sprite": "decor.rug.red", "at": [4, 4], "layer": "floor" },      floor coordinates; "floor" = under pets,
             { "sprite": "decor.shelf", "at": [2, -1], "layer": "wall" } ],      "wall" = on the wall, "top" = over pets
  "fixtures": { "bed": { "pos": [10, 1], "sprite": "fix.bed" }, "lamp": { "pos": [2, 1], "sprite": "fix.lamp" } },
  "blocked": [[0, 0], [1, 0]],                          floor tiles nobody can stand on (scenery furniture)
  "wall_slots": [[3, 0], [8, 0]],                       floor tiles under the places a picture, mirror or shelf can hang
  "bit_spots": { "petal": [[2, 5], [3, 5]] },           where each kind of bit turns up, if it should not be just anywhere
  "light": { "window": [[0, 3]], "night": 0.45 } }      where daylight comes in; how dark the room gets
```

- `fixtures`: every fixture the engine has for this room type (house.toml lists them) must be here. `pos` is
  where it stands; the engine moves an unmovable fixture to this tile, so the layout decides. `"wall": true`
  means it hangs on the north wall above `pos` (a window, a mirror, a lantern on a hook) and takes no floor.
  A fixture that arrives later (the heavy book) can be given its place here too.
- `"doors": "gate"` draws this room's doors from `door.gate.<wall>.<state>` instead of `door.<wall>.<state>`.
- `light.day` is how dark the room is even by day (a cellar), `light.night` by night. `light.sky`: `"open"` (weather
  falls in the room: the garden) or `"glass"` (it shows on a glass roof: the greenhouse).
- Draw order: the floor grid, the walls grid, wall decor (`at: [x, -1]` or `[x, -2]`), doors, floor decor, then
  fixtures, made things, bits and pets sorted by `y`, then `top` decor. A sprite is drawn with its `anchor` pixel
  on the top-left corner of its floor tile; things on walls lift themselves by their anchor.
- A fixture's sprite by state: the bare name is its resting look (`fix.lamp` is off), `fix.<name>.<state>` the
  others (`.on`, `.off`; a bowl's `.full`, `.half`, `.empty`; `.silent`, `.playing`; `.closed`, `.open`;
  `.growing`, `.ripe`).
- `blocked` plus the fixtures' tiles plus the `wall` things is what the engine and the view both treat as not
  walkable. Keep every door tile, and a path between all doors, free.

## sounds.json

```json
{ "sfx": { "pickup": { "pack": "ninja", "file": "Audio/Sounds/Bonus/Bonus.wav", "gain": 0.3 } },
  "music": { "nursery": { "pack": "ninja", "file": "Audio/Musics/4 - Village.ogg", "gain": 0.12 } } }
```

`sfx` names the view uses: pickup, drop, make, unmake, combine, door, step, eat, write, book, call, heart, radio,
arrival (and `arrival.<discovery>`). `music` is one quiet track per room type, off unless the visitor turns it on.

Three more sections say what the house sounds like (SPEC-v3.3 §3 and §4):

```json
{ "moods": { "calm": [ { "pack": "ninja", "file": "Audio/Musics/5 - Peaceful.ogg", "gain": 0.08 } ],
             "lively": [], "mysterious": [], "sad": [] },
  "ambience": {
    "rooms":   { "cellar": [ { "synth": "drips", "gain": 0.05, "rate": 0.15, "echo": 0.7, "sfx": "drip", "says": "slow drips with a long echo" },
                             { "synth": "wind", "gain": 0.02, "rate": 0.05, "pitch": 90, "says": "a low draught, more felt than heard" } ] },
    "weather": { "storm": [ { "pack": "ninja", "file": "Audio/Sounds/Ambient/Rain.wav", "gain": 0.4 },
                            { "pack": "ninja", "file": "Audio/Sounds/Ambient/Storm.wav", "gain": 0.35 } ] } },
  "instruments": { "bell": "bell", "wind chime": "chime", "default": "clatter",
                   "hum": { "synth": "hum", "gain": 0.04, "pitch": 180, "says": "one steady note with a slow wobble" } } }
```

- `moods`: the visitor's music. Each of calm, lively, mysterious and sad has 2 to 4 tracks, played one after another
  or shuffled; `gain` evens them out (a quiet track has the higher gain), so one volume serves them all.
- `ambience.rooms.<room type>`: 1 to 3 quiet layers that play together while that room is looked at.
  `ambience.weather.<weather>`: 1 or 2 more on top while the sky is so (rain, storm, snow, heat; a sky with no entry
  adds nothing). Which rooms hear the weather, and how muffled, is the page's business (`light.sky` in a layout
  says where the sky is open or glass).
- A layer is one of two things:
  - a file that loops: `pack`, `file`, `gain`. Only files long enough to loop are given this way; cross-fade the
    ends (Storm.wav ends quieter than it starts).
  - a sound the page makes: `synth` is one of wind, drips, crackle, hum, crickets, water, birds, creak, with `gain`
    (0 to 0.1) and `says`, one line on what it should sound like in this place. The rest are optional and a page
    that ignores them still sounds right: `rate`, how often, per second (events for drips, birds, creak, crackle
    and crickets; swells for wind and water) · `pitch`, in Hz (the note of a hum, where a wind is centred: 90 is a
    rumble, 900 a whistle, 3000 a rustle) · `echo` 0 to 1, how long a drip rings on · `steady` true, evenly spaced
    (a clock) rather than scattered · `when` "day" or "night", the only time it plays · `sfx`, an effect of `sfx`
    that may be played for each event instead of making one (a drip, a bird's call, a splash).
- `instruments`: the sound of a thing that sounds when used (an act with `loud`), by its kind or, for a fixture, its
  name -> a name in `sfx`. `default` is for any other loud thing (anything made of something noisy). `hum` is a
  thing humming by itself (`made.hums`): a layer like those above, played from where the thing is.

## Adding a pack

1. Put the zip in `~/PetProject/assets-incoming/` and unpack it somewhere outside the repository.
2. Copy only the files you will use into `third_party/<pack>/`, with the pack's licence file, and add the pack
   to `packs.json` and to `third_party/CREDITS.md`. (A pack that may not be redistributed stays outside: see above.)
3. Point names in `sprites.json` at the new files: a new look for an existing name, or new names.
4. For new kinds of thing, add them to `kinds.json`; for new furniture, use it in `rooms/*.json`.
5. Run `uv run python view/assets/own/src/validate.py` (seconds: every sprite, kind, fixture, activity sign, layout
   and sound names something that exists, every layout leaves its doors reachable, nothing in the catalog is
   unusable, no file lies about unused), and `uv run python -m engine.check` (minutes: the whole house, the art too).

The pictures in `own/` and the JSON beside this file (all but `kinds.json`) are written by `own/src/build.py` from
the tables in `own/src`: change them there and run it again (its first lines say how).
