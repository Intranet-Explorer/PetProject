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
- Doors are in the engine's `door_tiles` (sent in every snapshot): `north [6, 0]`, `south [6, 7]`, `west [0, 4]`,
  `east [11, 4]` unless house.toml says otherwise. A door is drawn in the wall beside its tile.

## packs.json

```json
{ "ninja": { "dir": "third_party/ninja_adventure", "tile": 16, "licence": "CC0", "by": "Pixel-boy and AAA" },
  "own":   { "dir": "own", "tile": 16, "licence": "CC0", "by": "this project" } }
```

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
- `tint`: `"hue"` means the view recolours it to a made thing's colour (hue and saturation replaced, lightness
  kept, outline and highlights left alone); absent means draw as is.
- Names of ours, by prefix: `tile.*` floors and walls · `decor.*` furniture that is only scenery · `fix.<fixture
  name>` the engine's fixtures (lamp, bed, bowl, music box, dial box, heavy book, …; `fix.<name>.<state>` where a
  state looks different: `fix.lamp.on`) · `kind.<kind>` made things · `bit.<bit>` things to gather ·
  `creature.<kind>` · `emote.<mood>` (tired, uneasy, lonely, bored, content, and more) · `fx.*` puffs, sparkles,
  hearts, notes, z's · `ui.*` bubbles and frames · `icon.room.<type>` for the minimap · `door.<state>` · `egg` ·
  `stone` (a memorial).

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
- The engine reads `rank`, `wall`, `not`, `a`. The view reads `sprite`.

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
  where it stands; the engine moves an unmoved, unmovable fixture to this tile, so the layout decides.
- `blocked` plus the fixtures' tiles plus the `wall` things is what the engine and the view both treat as not
  walkable. Keep every door tile, and a path between all doors, free.

## sounds.json

```json
{ "sfx": { "pickup": { "pack": "ninja", "file": "Audio/Sounds/Bonus/Bonus.wav", "gain": 0.3 } },
  "music": { "nursery": { "pack": "ninja", "file": "Audio/Musics/4 - Village.ogg", "gain": 0.12 } } }
```

`sfx` names the view uses: pickup, drop, make, unmake, combine, door, step, eat, write, book, call, heart, radio,
arrival (and `arrival.<discovery>`). Music is off unless the visitor turns it on.

## Adding a pack

1. Put the zip in `~/PetProject/assets-incoming/` and unpack it somewhere outside the repository.
2. Copy only the files you will use into `third_party/<pack>/`, with the pack's licence file, and add the pack
   to `packs.json` and to `third_party/CREDITS.md`. (A pack that may not be redistributed stays outside: see above.)
3. Point names in `sprites.json` at the new files: a new look for an existing name, or new names.
4. For new kinds of thing, add them to `kinds.json`; for new furniture, use it in `rooms/*.json`.
5. Run `uv run python -m engine.check` (it checks that every kind, fixture and layout names a sprite that exists,
   that every layout leaves its doors reachable, and that nothing in the catalog is unusable).
