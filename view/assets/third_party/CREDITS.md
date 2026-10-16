# Credits

## Ninja Adventure Asset Pack

By **Pixel-boy** (https://pixel-boy.itch.io/) and **AAA** (https://www.instagram.com/challenger.aaa/).
Pack page: https://pixel-boy.itch.io/ninja-adventure-asset-pack

Released under Creative Commons Zero (CC0 1.0): see `ninja_adventure/LICENSE.txt`. Attribution is not required;
it is given gladly.

`ninja_adventure/` holds only the files of the pack that `sprites.json` and `sounds.json` name, at the pack's own
paths, unchanged: tilesets, items, two animals, the emotes, a few effects and interface pieces, sound effects, a
jingle, two weather loops (rain, thunder) and sixteen music tracks (one per room type, and the visitor's music by
mood).

## Pixel Art Vending Machines Pack

By **Karsiori** (https://karsiori.itch.io/). Pack page, and the source of its licence:
https://karsiori.itch.io/pixel-art-vending-machines

Released under Creative Commons Zero (CC0 1.0) on that page; the pack itself came with no licence file, so
`karsiori_vending/LICENSE.txt` says so and points there. Attribution is not required; it is given gladly.

`karsiori_vending/src/` holds the one picture of the pack that is used, unchanged: `Vending Machine 6.3 (No Glass).png`.
The machine room's vending machine (`../own/works.png`) is built out of it by `../own/src/works.py`: the pack's rounded
cabinet top (its lettering and logo taken off for a plain glowing sign), its palette and its manner.

## Complete UI Essential Pack and Complete UI Book Styles Pack (the page's skin, SPEC-v3.5.6)

By **Crusenho Agus Hennihuno**, https://crusenho.itch.io (the Book Styles pack's page, as its licence gives it:
https://crusenho.itch.io/complete-ui-book-styles-pack).

- The **Essential** pack is released under Creative Commons Attribution 4.0 (CC BY 4.0,
  https://creativecommons.org/licenses/by/4.0/): `crusenho/LICENSE-Essential.txt`. Used from it: the Wood theme
  (`UI_Wood_*`: cards and frames, the hanging sign, buttons and their four press frames, the need bars), the hand
  cursor (`Icon_Cursor_02a`) and the pixel face Toriko (`Toriko.ttf`).
- The **Book Styles** pack may be used and changed, with credit or a link to its page, and may not be re-sold or
  published as itself: `crusenho/LICENSE-BookStyles.txt`. Used from it: the Travel Book (`UI_TravelBook_*`: the
  header banner, tabs, paper strips, the book pages and cover, slots, icons, the bookmark, the arrow cursor), the Holo Book
  (`UI_HoloBook_*`: the console's cover and panels, the digit frame), the white `UI_Icon_*01b` icons and the Papernote
  pencil cursor. The Travel Book popup (`UI_TravelBook_Popup01a`) is also the hobs' speech bubble in the room
  (SPEC-v3.5.9 §7: `ui.bubble.say` in `sprites.json`, through the pack entry `crusenho`, marked `"skin"`: the page's
  style sheets name most of its files, so `validate.py` does not count them).

`crusenho/` holds only the sprites the page uses, never the packs. **Changed:** most are cropped to their visible
pixels; the three cursors are also kept enlarged (nearest neighbour, `@1x` and `@2x`), since a browser cannot scale
a cursor. The page credits it at its foot: "UI art: Crusenho", linking to the store.

## Pixelify Sans (the page's reading face, since 15 October 2026)

By the Pixelify Sans Project Authors (https://github.com/eifetx/Pixelify-Sans), released under the SIL Open Font
License 1.1: `pixelify/OFL.txt`. `pixelify/PixelifySans-latin-400.woff2` is the Latin regular as Fontsource packs it
(`@fontsource/pixelify-sans` 5.3.0), unchanged; it is bundled, not loaded from the web.

## DotGothic16 and VT323 (the console's screens, SPEC-v3.5.7)

**DotGothic16** by the DotGothic16 Project Authors (https://github.com/fontworks-fonts/DotGothic16) and **VT323** by
the VT323 Project Authors (Peter Hull), both released under the SIL Open Font License 1.1: `dotgothic16/OFL.txt`,
`vt323/OFL.txt`. Each is the Latin regular as Fontsource packs it (`@fontsource/dotgothic16` 5.3.1,
`@fontsource/vt323` 5.3.0), unchanged and bundled.

## Drawn for this project

`../own/*.png` (made things, some fixtures and scenery, bits, the moth and the beetle, walls, doors, icons, the signs
over a pet's head) were drawn for this project in the pack's palette and manner, from `../own/src/art.py`. They are
CC0 as well.

## PixelLab (the sweeper and its dock, v3.5.9.1; five kinds, SPEC-v3.5.8)

`../own/robot.png` is cut from pictures generated for this project with **PixelLab** (https://www.pixellab.ai) on
16 October 2026: the sweeper, a little orange delivery robot (`assets-incoming/pixellab/robotC/`, PixelLab object
45d2830b-b942-4d12-a70a-19830087361d, made with `create-8-direction-object` from cell 2 of `robots32.png`): its eight
still directions (`C_<direction>.png`) and its drive animation (`C_drive_<south|east|north|west>_<0-4>.png`), each cut
from 34 × 34 to the 26 × 25 that holds the robot; and its dock, cell 26 of `assets-incoming/pixellab/robots32.png`
(`generate-with-style-v2`, 32 × 32 cells; the charging dock with the green light), cut to 20 × 21. Changed only in the
robot's green light, which is drawn lit in every frame (PixelLab's drive frames blink and glare on their own; the view
blinks it).

`../own/sweeper.png` is cut from a sheet generated for this project with **PixelLab** on 15 October 2026
(`generate-with-style-v2`, the Ninja Adventure items as the style; the sheet is `assets-incoming/pixellab/sweeper16.png`,
its names in `lists.py` `SHEETS["sweeper16"]`). Used unchanged: cells 24, 13, 52, 27, 45 (clay brick, bundle of sticks,
rag, bundle of fibre, label tag: the tile, tinder bundle, patch, draught stopper and sign kinds). The sweeper and its
dock from that sheet (cells 0, 1, 2, 6, 7) are no longer used. Generated images are used under PixelLab's terms of
service.
