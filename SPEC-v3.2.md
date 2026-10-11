# Pet — v3.2 spec: a house you can read at a glance

Tyler opened the live view and couldn't tell what was going on. He was right:

- **Objects are meaningless.** Things are built from abstract shapes, so "storm rest pulse" is a small teal ring and "quiet reed bar" is a green rectangle. Nothing looks like what it is.
- **Rooms aren't rooms.** The pond room is a grey tiled floor with blue squares and scattered dots. No walls with furniture, no sense of place.
- **Pets don't visibly do anything.** In the live house the mother and child have spent their recent thoughts doing only *accept → nuzzle → rest* in one corner. Between thoughts nothing moves.
- **The mind is hidden.** What a pet wants is in a drawer. The room shows nothing. The feed reads like "Quiet combined the morning vessel and the settled storm into a bright storm loop".

v3.2 is a presentation overhaul in a real pixel-art style, plus one change to making so things are recognizable, and one bug fix (the nuzzle loop is back). It also draws everything v3.1 adds, so v3.1 and v3.2 are deployed **together**.

SPEC-v3.md and SPEC-v3.1.md still hold. Departures go in DECISIONS.md as **Part 14**.

---

## 0. How to build this

Same rules as before: intent over letter, every section's **Why** is the test, log departures, stop only for the reasons below.

**The test for the whole spec**, used by the reviewer in §9:
> Someone who has never seen this opens the page. Within ten seconds they can say what every pet is doing, roughly how it feels, and what every object in the room is.

If a design choice doesn't serve that, change it.

**Stop and ask Tyler only for:** an asset download that needs a browser (§1.2), anything that would delete or overwrite data, or a Why that can't be met.

**The live family keeps living throughout.** Build in the worktree; deploy v3.1 and v3.2 together with one restart (§10).

Commits authored as Intranet-Explorer, short imperative subjects, no co-author trailers. Keep `pet-voice.xlsx` untracked.

---

## 1. Art

**Why:** shapes drawn in code have hit their ceiling. A consistent pixel-art style makes every room, object and creature instantly readable, and it's what makes the page something you'd leave open.

### 1.1 The pack
- **Primary:** *Ninja Adventure* by Pixel-boy and AAA (https://pixel-boy.itch.io/ninja-adventure-asset-pack). It's **CC0** (no attribution required, commercial use allowed) and includes 16×16 tilesets with interiors, 60+ items, animals, characters, UI, effects, sound effects and music tracks. One pack, one style.
- **Only if something essential is missing** (e.g. a specific piece of furniture): *Roguelike Indoor Pack* by Kenney (CC0, https://opengameart.org/content/roguelike-indoor-pack), or draw the missing piece in the pack's style. Never mix styles visibly; if a Kenney piece clashes, redraw it instead.
- Everything third-party lives in `view/assets/third_party/<pack>/` with the pack's own license file and a `CREDITS.md` naming the authors, even though CC0 doesn't require it.
- Only files actually used are committed. No unused bulk.

### 1.2 More packs, carefully
- More packs only where Ninja Adventure is thin (most likely furniture and interiors), and only if they match its scale, outline weight and palette. Before adopting any second pack, render one test room mixing it with Ninja Adventure, screenshot it, and keep it only if a reviewer can't tell where one pack ends and the other begins. Otherwise redraw the missing pieces in Ninja Adventure's style.
- **Licence decides where a pack can live.** CC0 packs (Ninja Adventure, Kenney) go in the repo. A pack whose licence forbids redistribution (most paid itch.io packs, e.g. *Pixel Lands Interiors* by Trislin) must stay **outside the repo** in a local folder the view reads at runtime, with the repo still working without it. Don't add such a folder to .gitignore by name; keep it outside the project directory. CC-BY-SA packs: ask Tyler first.
- Candidates, in order: *Roguelike Indoor Pack* (Kenney, CC0); *Pixel Lands Interiors* (Trislin, 16×16, paid, local only, only if Tyler buys it).

### 1.3 Getting it
- Try to fetch the pack directly. If itch.io requires a browser click, **ask Tyler** to download the zip and put it in `~/PetProject/assets-incoming/`. Unpack from there.

### 1.4 Rendering rules
- 16×16 source tiles drawn at an integer scale (3× or 4×, whichever fits the window better), nearest-neighbour, no blurring, no fractional positions for tiles.
- Day, night, season and weather as palette shifts and overlays (rain, snow, storm flashes, power-cut darkness with window light), in the same pixel style.
- Light and dark theme apply to the page around the room, not to the pixel art.

---

## 2. Pets

**Why:** the pets are the point, and they're the only thing not taken from the pack. They need to look like they belong in this world while still being made from their genome.

- Each pet is a **procedural pixel sprite** generated from its genome at 24×24 or 32×32 source pixels (Code's call, matching the pack's character scale): body shape from roundness and stretch, palette from hue and saturation, pattern as pixel dithering or spots, eyes from eye genes, limbs as pixel nubs, marks as visible pixel details. Use a small palette that sits well beside the pack's.
- **Animation frames** for each pet: idle (breathing bob), walk in four directions, sit/rest, sleep (curled, z's), eat, make (paws busy), happy (bounce), sad (droop), startled. Generated from the same genome, so every pet has every animation.
- Stage changes size and proportion; elders are a little greyer and slower.
- Families resemble each other because genomes do.

---

## 3. Things are recognizable

**Why:** this is the biggest single cause of "the objects make no sense". A pet that makes a cushion should produce something that looks like a cushion. The name stays the pet's own.

### 3.1 Making by kind
- `make` changes from assembling shapes to choosing a **kind** from a catalog, each backed by a sprite from the pack (or drawn in its style). The pet still chooses material, colour, name and purpose.
- Catalog (about 30; adjust to what the pack has): cushion, rug, blanket, nest, bed-mat, lantern, candle, lamp, wind chime, bell, drum, flute, ball, spinning top, doll, mobile, jar, bowl, cup, vase, basket, box, shelf, stool, mirror, picture, plant pot, garland, charm, stone stack, sculpture.
- **Material and colour tint the sprite** (soft things look soft, glassy things shine, dark things are shadowed). Material still decides what a thing **does**, as before. The kind only decides what it looks like, with one exception: a kind can rule out materials that make no sense (a candle can't be springy).
- `combine` produces the more complex of the two kinds, or a "sculpture"/"mobile" when the two are different.
- The recipe the pet writes becomes: `{kind, material, colour, name, purpose}`. Parts go away. The constrained-output schema is updated; the packet lists the kinds the pet can make.

### 3.2 Migrating the live house
- Every existing made thing is mapped once to the nearest kind from its parts and material (a ring → charm, a bar → shelf or stool, a soft blob → cushion, a bright dot → candle, and so on). The mapping table is logged in DECISIONS.md. Names, owners, materials and effects don't change.
- Heirlooms keep their history.

### 3.3 Hover, not labels
- Object names are **not** drawn permanently. Hover or tap shows a small card: the sprite, *a blue cushion*, its name in quotes, who made it, its material, and (for Tyler only) what it actually does.

---

## 4. Rooms

**Why:** a room should read as a place at a glance: where the walls are, what's on them, where you'd sit, where the water is.

- Each of the nine room types gets a **hand-designed layout** made from pack tiles: walls with trim and windows, floors, rugs, fixed furniture against walls, doors on the walls they lead through. Store layouts as data (Tiled JSON or arrays), one file per room type.
  - nursery: beds, a rug, the lamp, toy shelf, window.
  - garden: grass, planting beds, a path, a fence, sky.
  - cellar: stone floor, shelves, barrels, one high window.
  - attic: wooden boards, beams, a skylight with the sun shaft.
  - pond room: a real pond with edges, reeds, stepping stones.
  - workshop: workbenches, tools on walls.
  - music room: rugs, instruments on stands.
  - greenhouse: glass walls, plant tables, vines.
  - storeroom: crates and shelves, dim.
- Fixed furniture blocks tiles. Made things go on free floor tiles or, for wall kinds (picture, mirror, shelf), on walls.
- **Pathfinding:** pets walk around furniture and through doors (simple A* on the room grid). The engine's position stays authoritative; the view animates the walk along the path.
- Bits to gather appear as small pack items in sensible places (petals in the garden, pebbles in the cellar), not as dots scattered everywhere.

---

## 5. Life on screen

**Why:** a pet thinks about once a minute. Between thoughts it has to look alive, and every action has to be visible as an action.

### 5.1 Between thoughts
- **Idle behaviour** in the view, between engine steps: look around, small wander within a tile or two of where it is, sit, scratch, glance at whoever else is in the room, react to a creature or the weather. This is cosmetic only. The engine's position wins whenever a step starts.
- When asleep: curled up, slow breathing, z's.

### 5.2 Every action has an animation
| Action | On screen |
|---|---|
| walk / move | walks the path, animated |
| make | sits, paws busy, sparkle, the new thing pops in |
| unmake | the thing breaks into its bits with a puff |
| combine | both things drawn together, flash, new thing |
| use | interacts with the thing (sits on cushion, rings bell, lights lantern) |
| gather / drop | picks up / puts down, the bit shows in its paws while carried |
| speak / tell | speech bubble with the text, turned toward the listener |
| nuzzle | the two lean together, a small heart |
| give / show | holds the thing out toward the other |
| rest | sits down, eyes half closed |
| eat | eating animation, the bowl empties |
| write (v3.1) | scratches at the wall; the chalk text appears stroke by stroke |
| sing (v3.1) | music notes rise; the song plays |
| ask the book (v3.1) | opens the book, page glow |
| call a creature (v3.1) | the creature comes trotting |

### 5.3 What it's thinking
- A **thought caption** above each pet: its current intention, short and plain, in a small pixel speech-bubble style with a thought tail ("wants to show Mother the bead"). It fades when the intention ends.
- A **mood emote** next to it when a feeling is strong (tired, uneasy, lonely, bored, content), using the pack's emote icons. This replaces words like "miserable" in the main view.

### 5.4 The "now" line
- One plain sentence at the top of the page, rewritten by the engine (no model call) whenever something changes: *"The little one, an old one, is resting by Quiet in the pond room. Quiet just showed its mother a glass bead."*

---

## 6. Plain words everywhere

**Why:** the feed and panels are written for the logs, not for a person.

- Moments name the kind as well as the name: *"Quiet made a glass bead it calls 'bright bead drop'"*, *"Quiet took apart its lantern"*.
- Combine moments say what went in and what came out in kinds: *"Quiet joined a bead and a chime into a mobile"*.
- Stages in plain words: little one, young one, grown, old one.
- Feelings in plain words, worst first, at most two per pet on its card.
- Drawer tabs: **Family** (tree, sayings, songs, walls), **Story** (chronicle, moments, library, radio), **Things** (everything made, with sprites), **Lab** (everything technical, unchanged).

---

## 7. Layout of the page

- The room fills the width, at the largest integer scale that fits.
- A small **minimap** in a corner, with pixel icons for each room and dots for pets.
- **Pet cards** in a strip under the room: sprite, name, stage word, mood emote, current thought.
- Visitor controls in one tidy bar under the cards.
- Everything readable from 1280×800 up to a big monitor. Nothing clipped, nothing overlapping (the reviewer of the showcase failed this twice).

---

## 8. Sound

- Use the pack's sound effects for actions (pickup, make, door, footsteps) at a low level, under the pets' own voices.
- Optional ambient music from the pack per room type, very quiet, with its own toggle (off by default).
- The genome voices from v3 stay the pets' voices.

---

## 9. The nuzzle loop (bug)

**Why:** two pets accepting and nuzzling each other forever is the loop v3 already fixed once, and it's back in the live house. It's a bug, not behaviour to keep.

- Find why the fix stopped holding (likely the offer → accept → offer-back chain, or "close to someone" not suppressing offers). Fix the cause, add a self-check case that two pets can't spend more than a small share of a day's thoughts on accept/nuzzle with each other, and log it.
- Don't tune anything else about behaviour. Chronic low comfort stays a finding, not a fix.

---

## 10. Verifying and deploying

1. Build v3.2 in the worktree alongside v3.1.
2. On a **copy** of the live house (the v3.1 check copy is fine), run with the real model and every v3.1 arrival forced early. Check:
   - the migration maps every existing thing to a kind,
   - every room type renders with its layout,
   - every action in §5.2 animates,
   - the nuzzle loop doesn't recur over a day.
3. **Fresh-eyes review:** an agent that hasn't seen the build opens the page cold and answers the test in §0 from screenshots of every room, a birth, a death, a storm, the family tree, and each v3.1 discovery. Fix what it can't read. Repeat once if needed.
4. **Deploy v3.1 and v3.2 together:** back up `data/`, one restart, the family carries on.
5. Tell Tyler it's live, with a few screenshots and the real-time schedule of the v3.1 arrivals.

## 11. Not in v3.2

- Any change to what pets can do beyond §3 (kinds) and §9 (the loop fix).
- Pets reaching the internet, breeding between families, LoRA, hardware.
