# px: the room as pixel art

`view/src/room.ts` draws the one room being looked at; the pieces it is made of are here. Everything is drawn from
the data in `view/assets/` (see its README): no tile coordinate, file name or pack name appears in this code. A
sprite name that is missing draws a small plain box (a missing `icon.act.*` a small plain dot) and warns once in the
console: nothing is ever a hole.

| file | what it does |
|---|---|
| `geom.ts` | the 14 x 11 tile canvas, the 12 x 8 floor inside it, small helpers |
| `assets.ts` | loads `/art/packs.json`, `sprites.json`, `kinds.json`, `kinds-from-parts.json`, `rooms/<type>.json`; textures and canvases by sprite name |
| `tint.ts` | a made thing's colour, material and wear laid on its kind's sprite (hue and saturation replaced, lightness kept), cached |
| `font.ts` | the room's 5 x 7 pixel lettering: measure, wrap to lines, draw (plain or chalky) |
| `path.ts` | the way round furniture on the floor grid; the nearest free tile |
| `still.ts` | what holds still: floor, walls, decor, doors, fixtures in their states, made things by kind, bits, stones; things put away on shelves, counts on chests, the tint of a named place |
| `weather.ts` | the light map (day, dusk, night, season, weather, lamps, power cuts, windows; dark at the room's edges more than its middle), rain and snow, storm flashes |
| `actors.ts` | pets and creatures: walking the path, poses for each kind of step, what a body does by itself (`MOVES`), a pale outline in low light |
| `acts.ts` | each finished step or body activity played once: pop, puff, slide together, heart, notes, dust, a thing flown to its shelf |
| `fx.ts` | the small moving things (sparkles, hearts, notes, z's, dust), pooled |
| `marks.ts` | writing on the walls |
| `bubbles.ts` | each pet's one line (the sign of what it is doing, its name), the caption of what it wants, speech bubbles, the box's words, the names of things, and whose turn it is to show |

## What the page gives the room, and gets back

```ts
const room = new Room();
await room.init(element);              // loads the art; the canvas goes inside `element`
room.update({ snap, room, hello, selected, picked, replay });   // every snapshot (and whenever the page's choice changes)
room.onClick = (target) => { ... };
room.onHover = (target, fx, fy) => { ... };   // target is null when the pointer leaves; fx, fy: where, 0 to 1 across `element`
room.labels();                          // name lines, captions and bubbles that show now (CSS pixels in the canvas), for overlap checks
room.describe(target);                  // what a hover card can show: see below
room.picture(genome, stage, look);      // a data URL of a body, kept for the old page; new code can use petsprite.ts directly
room.clear = ["roomName", "banner"];    // ids of the page's own elements lying over the room: lettering keeps out from under them
room.names(on);                         // hold the names of the things in the room on, or let them go
```

**Names of things (SPEC-v3.3 §5).** They show while `names(true)` holds them, and one at a time while the pointer
is on its thing (a tap on a touch screen); nothing names itself when a room comes into view. Otherwise they are faded out and not drawn.

**Size.** Give `element` a width (and, to cap the height, a CSS `max-height`). The canvas takes the largest whole
number of screen pixels to an art pixel that fits, and is centred in the element; it sets its own CSS size
(with `!important`), so a stylesheet rule that stretches it does nothing. It follows the element when that resizes.

**Pets (SPEC-v3.3).** A pet is drawn `petScale(K)` times the art's pixels (about 1.6: 5/3 where an art pixel is 3
screen pixels, 3/2 where it is 2 or 4), and everything about it follows: where it can be pointed at, its shadow, its
plate and bubbles, how far apart two of them stand. In low light (dusk, night, storm, a power cut) each wears a thin
pale outline, laid over the dark. While `pet.body` is set its body is at something by itself: over its head is the
sign `icon.act.<body.icon>` (with `body.doing` in words for four seconds whenever it changes), and it moves as
`MOVES` in `actors.ts` says: a table by the activity's name, then by its icon, so an activity added to
`activities.toml` with a known icon needs nothing here, and one with a new icon still stands turned to what it is
about and sways (or sits, if `snap.activities[name].rest`). While it carries out a step it decided (`pet.act`) there
is no sign and it holds itself as v3.2 had it.

**Order (SPEC-v3.3 §2).** A thing with `obj.on` stands small on the thing it is put away on, side by side with the
others there, along that sprite's `surface` (`sprites.json`, optional: `[x, y, w]` inside the sprite; without it,
across the sprite's middle). In a thing whose `store.inside` is true it is not drawn: the chest wears a small
number. `room.areas` are tinted faintly, each name its own colour, and named when names show.

**The hover card (SPEC-v3.2 §3.3).** Nothing in the room carries a permanent label except the pets' name plates.
`onHover` and `onClick` give a `Target` (`tile`, and whichever of `pet`, `creature`, `door`, `object`, `bit`, `mark`
is under the pointer). `room.describe(target)` turns that into a `Card`, or null:

```ts
type Card = { what: "pet" | "creature" | "thing" | "fixture" | "stone" | "bit" | "door" | "writing" | "scenery";
  title: string;                       // "a blue cushion", "the lamp", "some moss", "Pip", "the door to the pond room"
  sprite: HTMLCanvasElement | null;    // its picture at the art's own size: show it with CSS `image-rendering: pixelated`, scaled by a whole number
  name?, kind?, color?, material?,     // a made thing: the name its maker gave it, its kind, colour and material
  maker?, owner?, heirloom?, worn?, purpose?,
  does?,                               // what it has been taught to do (for the owner's eyes only: the page decides whether to show it)
  state?, text?,                       // a fixture's state; one plain line (an inscription's words, what a creature is doing and whose it is,
                                       //   where a door leads, what a bit can become, "part of the room" for scenery)
  can?,                                // a bit: the properties a thing made of it can have (hello.bits[bit].can)
  notes? };                            // SPEC-v3.3 §2, plain lines to show as they are: "holds: a red cup, a blue bell", "room for 2 more",
                                       //   "kept on the shelf", "its home is in the sleeping corner", "part of the making bench"
```

Everything drawn answers: pets, creatures, made things, fixtures (`does` is the engine's `obj.says`), bits, doors,
writing, and the room's own scenery (`target.decor`, the sprite's name; its title comes from that name). A creature
shows a small name plate in the room while it is pointed at.

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
