# Polish list

Small things Tyler has seen and set aside. No action until he says so. Newest at the bottom.

- **Tool box sprite** (garden): it is a plain metal box; it should look like a tool box. (12 October 2026)
- **Things on a one-tile shelf overlap**: three or more things put on one shelf are drawn on top of each other. (12 October 2026)
- **Lightning and thunder are out of step**: the flash comes every five seconds or so, the thunder every 14 to 30,
  each on its own timer (`view/src/px/weather.ts`, `view/src/voice.ts`). (12 October 2026)
- **Tidying is silent and partly unseen**: putting a thing away, taking one out and hanging one up make no sound,
  and loose bits put away blink off the floor with no movement. (12 October 2026)
- **The ball is silent**: it bounces without a sound though the sound data has a bounce. The lamp switch, the
  trunk and the window make no sound either. (12 October 2026)
- **The attic skylight looks the same open or shut**: there is one picture for both. (12 October 2026)
- **The garden's top row can be stood on**: a pet napping by the old bench is drawn over the fence. The layout
  should keep them off that row. (12 October 2026, from the fresh-eyes watch)
- **Two pets close together: one name line is hidden** until they part, and two of the family look alike. (12 October
  2026, from the fresh-eyes watch; the spec asks for the later label to wait, not move)
- **Owner markers are unexplained**: the small coloured squares by made things and the faint tint of a named corner
  mean nothing to someone who has not been told. (12 October 2026, from the fresh-eyes watch)
- **Notes keep rising from the drum and chimes in an empty music room** for a minute and a half after anything loud
  was used there. (12 October 2026, from the second fresh-eyes watch)
- **The storeroom's top row can be stood on** too: a pet is drawn up over the wall and the lamp. (12 October 2026)
- **The "+" beside what a pet carries** (more than two bits) is unexplained. (12 October 2026)
- **A mind's own words can end in a stray character** on a card ("inside the m宅"): the model wrote it. (12 October 2026)
- **"Grey Light took a charm from Sven"** is said even when Sven is in another room: the charm was Sven's, not
  in Sven's paws. (12 October 2026)

- A made thing carried toward the machine leaves its floor shadow and maker's pip where it lay until it is set
  down (v3.5.1).
- The ticker's clock is read at the start of each run of messages, so it can be a minute or two behind (v3.5.1).
- A pet at one of the hub's screens is told "the book is right here" and "you read in the book", and the story says it
  "asked the book": the words of the heavy book, not of a screen (v3.5.1).

- **v3.5.8 view, 15 October 2026:**
  - The toolbar's Stock, Music and More are icons up to 1700 px now (v3.5.7: 1400), and below 1400 Say is its icon and
    the words box is narrow, to keep one row with the chosen hob's face and name at its head. At 1000 px it wrapped
    before and still does.
  - The Charms filter sits on the Things tab's count line (out of the phone's fold), not inside the kind chooser.
  - A sweeper on its dock is drawn in front of the dock's foot; the dock shows only above it. A bigger dock picture
    would read better.
  - A bit held in the paws is a small picture at its floor size; pale bits (fibre, string) are hard to see on a pale hob.
  - A big thing over the head of a hob seen side-on: its arms are hidden behind its body's outline.
  - The sack's count pip can sit under the hob's name plate when the plate is placed low.
  - The sweeper drives in straight lines, over the pond and past furniture, not along the room's paths (engine/sweeper.py `move`).
  - A thing card with every new record (title, how, made from, users, words) is taller than an 800 px window's room:
    it keeps within the window, and the "click to move" hint under it can meet the toolbar.

- **v3.5.9 canvas, 16 October 2026:**
  - Lightning and thunder are in step now: the room and the world outside flash on one schedule (`px/weather.ts`
    `flashAt`), and the thunder follows the world's flash (`world.ts` -> `voice.ts`), at most every 12 seconds.
  - A room's display reads its time at the start of each run (sky, time, line), so after a jump in time it can be
    behind for one run; like the big board.
  - The display hangs where the north wall is clearest; in a crowded room tall furniture can stand in front of it.
    A layout's `display` ([x, y]) puts it somewhere else (only the garden's is set: on the fence).
  - The "made" stamp is in the room's 5 x 7 lettering, so it is as big as a small thing; a smaller face would suit it.
  - The garden at night is still much lighter than the sky behind the page.
  - The world's fog is drawn as thin drifting bands; it reads as mist lines more than a bank of fog.
