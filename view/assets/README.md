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
  seasons.json         which picture stands in for which, by season and room type (snow, blossom, fallen leaves)
  sounds.json          sound effects and music, by a name of ours -> a file in some pack
  parts.json           the parts library (SPEC-v3.5 §1): what an invented thing and a pet's body are put together from
  bodies.json          the body genes: each slot's values, the plans, the patterns (the engine inherits them; the view draws them)
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

`"skin": true` (SPEC-v3.5.9): a pack whose files the page's style sheets name rather than sprites.json (the Crusenho UI
art); validate.py does not count its files as unused.

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
  small white plate so it reads on any floor) · `plant.<stage>` something growing (below) · `door.<state>` · `egg` ·
  `stone` (a memorial).
- `fix.little radio` (`.on`, `.off`) is the visitor's own radio, set down in a room until the pets find theirs.
- SPEC-v3.5.1, the machine room: `fix.terminal` is every screen (`terminal` in house.toml), whatever its name; its `glass`
  ([x, y, w, h]) is where the view writes what was typed and read. `fix.radio set` (`.on`, `.off`) is the pets' radio while
  it stands in the hub. Both are drawn by `own/src/hub.py` into `own/hub.png`. The lit sign and the statue are drawn by the
  view in code; a layout's `fix.lit sign` only gives the sign its size and place.
- A bit a room grows is drawn on its source, standing on the bit's tile like a fixture: `grows.<bit>` with the bit on
  it (petals on a flower, feathers in a nest, reed among the reeds), `grows.<bit>.bare` after it has been picked,
  until it grows back. Only a bit a pet dropped is drawn loose, as `bit.<bit>`. A bit with no `grows.*` sprite is
  drawn loose as before, and not at all while it grows back, so a pack can bring sources by adding these names.
  Ours are in `own/bits.png` (`own/src/draw.py`, `GROWN`: a source from `art.py` with the bit's own picture set on
  it), but for leaf and wood, which grow on pictures of the pack.
- What a process gives (`crafting.toml`, `[material.<name>]`: wicker, fired clay, rope…) is a bit like any other and
  needs a `bit.<name>`. Ours are drawn by `own/src/draw.py` at the end of `own/bits.png`, one for every material in
  that file: its own picture if `art.py`'s `BITS` has one, or else the bit it is `like` in its `tint`. After adding
  a material, draw the sheets again and give the new `bit.<name>` its entry here (validate.py asks for it).
- A material that says `sheet = "machine"` in `crafting.toml` (SPEC-v3.5 §4.3: stone, plank, grit, cord…) is left out
  of `bits.png`: `own/src/machine.py` draws it into `own/machine.png`, and lays its entries into this file as one block
  after `fix.bed`.
- The vending machine (SPEC-v3.5.1: "The Works", in the machine room) is drawn by `own/src/works.py` into
  `own/works.png`, with the plain stand-ins for the room's other new pieces (`fix.lit sign`, the three `fix.… screen`s,
  `decor.plinth`, `decor.machine pad`, `icon.room.hub`). `fix.vending machine` has an animation for each of `idle`,
  `take` (the hopper gulps), `work`, `drop` (the belt runs) and `lit`; `fix.vending machine.lit` (while it gives, takes
  or is stocked) is the same sheet with `lit` as its idle. Its `works` field says where on the picture its six windows
  are (in `materials` order), the hopper's mouth and the belt (`[x0, y0, x1, y1]`), for the view (px/works.ts). Its picture is typed there (`BITS`), or is the bit it is `like` in its `tint`.
- Something planted (SPEC-v3.4 §3.5) is drawn over the pot or bed it is in: `plant.<stage>` for each stage in
  `crafting.toml` (`planted`, `sprout`, `leaves`, `ripe`) and `plant.wilted`, or `plant.<what>.<stage>` where one
  plant should look different from the rest (`plant.bean.ripe`). The picture is set foot to foot and middle to
  middle on what it is planted in, at that thing's size; ours put the earth where a 16 × 16 pot's rim is. A thing
  that has `<its sprite>.bare` is drawn as that while something is planted in it (`kind.plant pot.bare`: our pot is
  typed with a plant of its own). A pack with no `plant.*` shows nothing.
- SPEC-v3.5.12, the train: `creature.train` (the engine), `creature.train.cart`, `creature.train.cart.open` (stills only)
  and `creature.train.tram`, each with `still.<direction>` for the eight ways and `walk.down|right|up|left` to drive in, as
  `creature.sweeper`; `station.*` stand beside a platform (the lamp post, the bell post, the bench, the clock). All in
  `own/train.png`, drawn by `own/src/train.py`. The track itself is drawn by the view (px/train.ts).
- `fx.burst.want` and `fx.burst.find`: the moment a pet gets what it wanted, or finds something out; each has a
  `play` animation.

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
- `tool`: it is a tool (a carver, a trowel, a hammer): `crafting.toml` says what each is for and what it is made of.
- The engine reads `rank`, `wall`, `not`, `a`, `flat`, `store`, `inside`, `hooks`, `hangs`, `tool`. The view reads `sprite`.

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
  "display": [x, y],                                    (optional, SPEC-v3.5.9 §4) where the room's small LED display hangs; else the clearest stretch of north wall
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

## seasons.json

```json
{ "winter": { "garden": { "tile.grass": "season.winter.tile.grass", "decor.sprout": null,
                          "decor.flower.sun": "season.winter.snow mound" },
              "*":      { "fix.window": "season.winter.fix.window" } },
  "autumn": { "garden": { "tile.grass": ["season.autumn.tile.grass", "season.autumn.tile.grass~1", "tile.grass"] } } }
```

What the house looks like by season (SPEC-v3.5 §5): for a season and a room type (`"*"`: every room), the picture that
stands in for one of the names above wherever the room draws it: a floor or wall tile, a piece of decor, a fixture in
any of its states, what a bit grows on. `null`: it is not drawn that season. A list: one of them is taken by where the
tile is, so a floor of one tile is not one picture repeated. A season, a room or a name that is not here is drawn as it
always is (summer has nothing). Ours are in `own/seasons.png`, drawn by `own/src/seasons.py` from the pictures they
stand in for (snow laid on, the green turned, blossom dotted in); it writes this file and its block of `sprites.json`
(`season.<season>.<name>`, after the last `tile.*`), and the two bits the seasons bring (`seasons.toml`, `[bit.*]`).

## sounds.json

```json
{ "sfx": { "pickup": { "pack": "ninja", "file": "Audio/Sounds/Bonus/Bonus.wav", "gain": 0.3 } },
  "music": { "nursery": { "pack": "ninja", "file": "Audio/Musics/4 - Village.ogg", "gain": 0.12 } } }
```

`sfx` names the view uses: pickup, drop, make, unmake, combine, door, step, eat, write, book, call, heart, radio,
arrival (and `arrival.<discovery>`), clunk (the vending machine gives something). `music` is one quiet track per room type, off unless the visitor turns it on.

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

The pictures in `own/` are drawn by `own/src/build.py` from the tables in `own/src`: change them there and run it
again (its first lines say how). The JSON beside this file was first written by it too and is kept by hand now: a
new picture's entry for `sprites.json` is what `build.own_art()` returns for its name. Add pictures at the end of a
sheet, so no other moves.

## parts.json

The parts library. Its pictures are drawn by `own/src/parts.py` into `own/parts/` (run it again after changing a
part; it rewrites the drawing fields here and leaves the names, roles, spots, rules and kinds alone). Look at them
all on a running house at `/parts.html`; check them with `uv run python -m engine.check_parts`.

```json
{ "rules":   { "max_parts": 3, "no_stack": ["flame", "blade"], "px": { "small": 16, "large": 24, "furniture": 32 }, "behind": ["inside"] },
  "palette": { "main": ["8a4a1f", "…"], "trim": ["…"], "glow": ["…"], "ink": "141b1b", "white": "ffffff", "red": "c4484a" },
  "looks":   { "dark": { "sat": 0.7, "light": 0.62 } },
  "thing":   { "bowl":  { "role": "base", "spots": ["inside", "side", "top", "base"], "layer": "body",
                          "px": { "16": { "file": "own/parts/thing16.png", "rect": [16, 0, 16, 16], "at": { "top": [7, 8], "inside": [7, 11], "side": [13, 11], "base": [7, 15], "face": [7, 12] } } } },
               "flame": { "role": "top", "on": ["tip", "top", "inside"], "glow": true, "px": { "16": { "file": "…", "rect": [0, 16, 16, 16], "pin": [7, 15] } } },
               "band":  { "role": "wrap", "on": ["side"], "clip": true, "to": { "side": "face" }, "px": { "…": {} } } },
  "kinds":   { "candle": { "base": "stick", "signature": "flame" } },
  "body":    { "file": "own/parts/body.png", "small": 10, "shade": { "dark": -0.22 }, "plans": { "tall": { "w": 0.68, "h": 1.4 } },
               "slots": { "ears": { "layer": "behind", "pair": true, "spread": 0.3, "values": { "long": { "frames": { "front.l": { "rect": [0, 16, 2, 6], "pin": [1, 5] } } } } } } } }
```

- `palette`: the colours a part's picture is drawn in, dark to light. The view paints `main` in the part's own colour
  (a thing part: its `color`, changed by its `material` as `looks` says; a body part: the pet's coat), `trim` in a
  duller tone of it (a pet: the pattern's dark and its pale), and leaves `glow`, `white`, `red` and the line as drawn.
- A thing is composed of at most `max_parts` parts (the snapshot's `invented`, one record a kind): the first is the
  base, drawn where it is; each other is set with its `pin` on the base's `at` point for the spot it was given (`to`
  sends a spot to another point: a wrap on the side goes to the middle of the `face`). A part on a spot in
  `rules.behind` is drawn behind the base, so it shows over a rim or through a hole; a part with `clip` is painted
  only on the base's own body; a part with `"outline": false` has no line of its own. A part that `carries` a spot
  has an `at` point of its own for it: a later part given the same spot stands there (a flame in a fork). The whole stands in the middle
  of the bottom of a square of `rules.px[size]` pixels, and anything with a part that has `glow` gets a soft halo.
- What an invention may be is in `uses.json` (SPEC-v3.5 §3.0): each use's allowed `base` parts and the parts it adds.
  Every part a use adds is the `signature` of some kind in `kinds`, so the use can be reached from two things a pet
  can make, and every signature part has a spot on every base, so any two things make at least a curio (the first
  one's base, the other's signature part on the first spot of its `on` list that the base has free).
  `/parts.html#uses` and `#curios` show them all.
- `body.slots.<slot>.values.<value>.frames`: a body part's picture from each side at each size (`front.l`, `side.s`
  …: the side view faces right; `s` is for a body under `body.small` pixels wide; a mouth has one for each thing a
  face does with it). `layer`: behind the body (it grows out of it), front, or on (only where the body is). `pair`:
  one each side of the middle, the second mirrored. `plans`: a body plan as proportions of the one body a genome's
  roundness and stretch give; with a `head`, that stands on the body and carries the face.
