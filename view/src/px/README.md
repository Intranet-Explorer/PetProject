# px: the room as pixel art

`view/src/room.ts` draws the one room being looked at; the pieces it is made of are here. Everything is drawn from
the data in `view/assets/` (see its README): no tile coordinate, file name or pack name appears in this code. A
sprite name that is missing draws a magenta-checked tile and warns once in the console.

| file | what it does |
|---|---|
| `geom.ts` | the 14 x 11 tile canvas, the 12 x 8 floor inside it, small helpers |
| `assets.ts` | loads `/art/packs.json`, `sprites.json`, `kinds.json`, `kinds-from-parts.json`, `rooms/<type>.json`; textures and canvases by sprite name |
| `tint.ts` | a made thing's colour, material and wear laid on its kind's sprite (hue and saturation replaced, lightness kept), cached |
| `font.ts` | the room's 5 x 7 pixel lettering: measure, wrap to lines, draw (plain or chalky) |
| `path.ts` | the way round furniture on the floor grid; the nearest free tile |
| `still.ts` | what holds still: floor, walls, decor, doors, fixtures in their states, made things by kind, bits, stones |
| `weather.ts` | the light map (day, dusk, night, season, weather, lamps, power cuts, windows), rain and snow, storm flashes |
| `actors.ts` | pets and creatures: walking the path, poses for each kind of step, life between thoughts |
| `acts.ts` | each finished step played once: pop, puff, slide together, heart, notes, dust |
| `fx.ts` | the small moving things (sparkles, hearts, notes, z's, dust), pooled |
| `marks.ts` | writing on the walls |
| `bubbles.ts` | name plates, thought captions, speech bubbles, the box's words, and where each may go |

## What the page gives the room, and gets back

```ts
const room = new Room();
await room.init(element);              // loads the art; the canvas goes inside `element`
room.update({ snap, room, hello, selected, picked, replay });   // every snapshot (and whenever the page's choice changes)
room.onClick = (target) => { ... };
room.onHover = (target, fx, fy) => { ... };   // target is null when the pointer leaves; fx, fy: where, 0 to 1 across `element`
room.labels();                          // plates, captions and bubbles as laid out now (CSS pixels in the canvas), for overlap checks
room.describe(target);                  // what a hover card can show: see below
room.picture(genome, stage, look);      // a data URL of a body, kept for the old page; new code can use petsprite.ts directly
room.clear = ["roomName", "banner"];    // ids of the page's own elements lying over the room: lettering keeps out from under them
```

**Size.** Give `element` a width (and, to cap the height, a CSS `max-height`). The canvas takes the largest whole
number of screen pixels to an art pixel that fits, and is centred in the element; it sets its own CSS size
(with `!important`), so a stylesheet rule that stretches it does nothing. It follows the element when that resizes.

**The hover card (SPEC-v3.2 §3.3).** Nothing in the room carries a permanent label except the pets' name plates.
`onHover` and `onClick` give a `Target` (`tile`, and whichever of `pet`, `creature`, `door`, `object`, `bit`, `mark`
is under the pointer). `room.describe(target)` turns that into a `Card`, or null:

```ts
type Card = { what: "pet" | "creature" | "thing" | "fixture" | "stone" | "bit" | "door" | "writing";
  title: string;                       // "a blue cushion", "the lamp", "some moss", "Pip", "the door to the pond room"
  sprite: HTMLCanvasElement | null;    // its picture at the art's own size: show it with CSS `image-rendering: pixelated`, scaled by a whole number
  name?, kind?, color?, material?,     // a made thing: the name its maker gave it, its kind, colour and material
  maker?, owner?, heirloom?, worn?, purpose?,
  does?,                               // what it has been taught to do (for the owner's eyes only: the page decides whether to show it)
  state?, text? };                     // a fixture's state; an inscription's or a stone's words
```

The canvas in `sprite` is shared: draw it into the card (`ctx.drawImage`) or append a copy, do not paint on it.

## What is read from the data, beyond the assets README

Each of these is optional and has a fallback.

- `rooms/<type>.json`: `doors` (a kind of door: `"gate"` uses sprites `door.gate.<dir>.<state>`); a fixture's
  `wall` (it hangs on the wall where its sprite's anchor puts it), `walk` (it can be stood on) or `layer`
  (`"floor" | "wall" | "top"`); `light.day` (how dim the room is by day) and `light.sky`: `"open"` (weather
  falls in the room) or `"glass"` (a little of it shows under the roof). Until a layout says `light.sky`, a room
  with a `tile.sky*` among its tiles is taken as open and one whose north wall is mostly window as glass.
- Doors: the first that exists of `door.<doors>.<dir>.<state>`, `door.<dir>.<state>`, `door.<state>`, with
  states `open`, `unknown` (nobody has been through; falls back to `shut`), `stuck` (falls back to `shut` with a
  bar across). A door's sprite is anchored to the door's floor tile; its anchor carries it into the wall.
- Fixtures: the layout's `sprite`, then `<sprite>.<state>` if there is one: the engine's state (`on`, `off`,
  `open`, `closed`, `playing`, `silent`); `empty`, `half`, `full` for a bowl; `growing`, `ripe` for a plant. A
  fixture not in the room's layout (something carried in) is looked up as `fix.<its name>`. A fixture the engine
  calls soft (a rug, a blanket) lies flat and can be walked over.
- `sprites.json`: an animation may say `"flip": true` (shown mirrored). A window's sprite may give
  `"glass": [x, y, w, h]`, the part that is sky; otherwise the sprite less a 3-pixel frame is taken as glass.
  `"slice": [left, top, right, bottom]` makes a frame that stretches: `ui.bubble.say`, `ui.bubble.think` (with
  `ui.bubble.say.tail`, `ui.bubble.think.tail`) are used for speech and thoughts if they are there.
- Effects: `fx.heart`, `fx.note`, `fx.zzz`, `fx.sparkle`, `fx.puff`, `fx.dust`, `fx.flash`, `fx.chalk dust`,
  `fx.drip`, `fx.rain` and `fx.snow` (their animation `kinds` is a set of variants) are used if they are there; a
  one-shot animation of any name plays once over the effect's life. Without them, and for the smallest things
  (glints, specks, the tame creature's flag, an heirloom's ribbon), a few pixels drawn in `fx.ts` are used.
- `kinds.json`: `"flat": true` for a kind that lies on the floor and can be walked over (a rug). Otherwise a made
  thing blocks its tile.
- Creatures: animations `walk.<dir>`, or `walk`, or `idle`; a creature with one set of frames is taken to face right.
