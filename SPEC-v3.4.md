# Pet — v3.4 spec: purpose

v3.3 made the pets busy on paper. Watching the live house on 12 October, they barely seemed to do anything:

- **Busy meant fidgeting.** In ten minutes each pet logged 65 to 91 activities, nearly all babble, stretch, hum, groom and fiddle. The pet stays where it is and a different icon appears. v3.3 §0 counted these as "different things", so the house passed while looking still. That was the spec's mistake.
- **The minds hold the bodies in place.** A pet's focus is "rest" about a third of the time and "be with" another fifth, and the body stays close. Three pets sat bunched in one corner of the storeroom, each set on being with the others.
- **What's worth watching is rare.** In those ten minutes: 8 tidies and 1 thing made.
- **Nothing makes them want anything.** Needs are mostly met, and curiosity reads "interested" whatever a pet does (FINDINGS v3, item 11). No pet wants to find something out, make something better or get better at anything.
- **The book and the radio don't matter to them.** The book has been in the attic since it arrived and has been asked nothing, ever. The radio has spoken 44 times, and pets mentioned it in 2 of about 2,000 thoughts.
- **Making never produces anything new.** Each bit gives one property; `combine` stacks two things under a name made from theirs ("settling signal five"). The house holds 40 charms and 25 nests.

v3.4 gives the pets **wants**, **skills**, **making by discovery**, **tools** and **food they grow**. It connects the book and the radio to what they want, makes the body go places and handle things, and makes the room easier to read. SPEC-v3 to v3.3 still hold. Departures go in DECISIONS.md as **Part 16**.

---

## 0. How to build this

Same rules as before: intent over letter, every section's **Why** is the test, log departures, and stop only for data deletion, network access beyond what's allowed, a model change, or a Why that can't be met.

**The test for the whole spec:** Tyler watches any room with pets in it for ten minutes. He sees them go places and handle things, and at least one of them makes something new or finds something out. He can say what each pet was trying to do.

Before that, these must hold. They're measured in watching time on the live clock, on a copy of the live house with the real model, per awake pet:

| | Bar |
|---|---|
| Things handled in any 5 minutes: different objects or bits picked up, used, carried, put away or made with (fidgets don't count) | at least 3 |
| Distance walked in any 5 minutes | at least 15 tiles |
| Longest in one spot outside a visible rest pose | 30 s (unchanged) |
| Wants fulfilled per world day (§2) | at least 2 |
| Things made that repeat a kind and material the maker has made before | under half |
| Discoveries house-wide per world day, over the first three days (§3) | at least 2 |
| A tool made, house-wide (§3.4) | by the end of world day three |
| Food grown and eaten, house-wide (§3.5) | by the end of world day four |
| Book asked, house-wide per world day | at least once |
| Something the radio said shows up in a thought, question or telling, house-wide per world day | at least once |
| Model calls per pet per world day | no more than 10% up |

**The live family keeps living.** Build on a branch in a worktree, check on a copy, back up `data/`, and deploy with one restart. Use two helper agents at most. **Say before running a real-model copy alongside the live house**, because they share the model and live thoughts time out.

Commit as Intranet-Explorer, with short imperative subjects. A Claude co-author trailer is fine. README.md is the repo's front page: don't edit it. Run and build notes go in RUNNING.md, and small visual fixes in POLISH.md. Keep `pet-voice.xlsx` and `IDEAS.md` untracked.

---

## 1. Bodies that go places

**Why:** a viewer reads "alive" from movement across the room and from things being handled. Gestures in place don't register.

- **Fidgets are filler, not activities.** Stretch, groom, hum, babble, fiddle and look about last 3 seconds at most. They happen only between activities or just before a thought, are never chosen as the activity itself, and don't count in §0.
- **The menu favours moving and handling.** Weight up activities that end somewhere else in the room and involve a thing:
  - carry, tidy, gather
  - play with a toy (roll the ball to kin, spin the top)
  - use furniture (sit on the stool, lie on a cushion, look out of the window)
  - tend a plant, eat, visit the stone
  - take something out of a box and look at it
  - follow a creature
  - carry bits to where a process happens (§3)
  
  Each lasts 5 to 20 seconds.
- **"Be with" means doing something together:** following when the other goes, playing with the same toy, tidying side by side, sitting at the window together, humming the same song. Standing next to each other is a short pause between those, not the activity.
- **"Rest" doesn't hold an untired body.** If the mind says rest and the pet isn't tired, the body is free, as the tidying change began.

---

## 2. Wanting things

**Why:** needs alone don't push a pet that is mostly fed, comfortable and in company. Games like *The Sims* keep characters purposeful with concrete, short-lived wants drawn from their situation, and these pets need the same.

### 2.1 Wants
- Each awake pet holds **up to three wants**. The engine makes them from the pet's surroundings, history and temperament, with no model calls. Kinds:
  - **To know:** a room it hasn't entered, a door it hasn't opened, a creature it hasn't been near, a bit it has never held, a word it heard and doesn't know (§4).
  - **To make better:** a thing it made that did nothing, a cold room, a leak, a mess with nowhere to put things, a lamp that's harsh at night.
  - **To make for someone:** kin who is uncomfortable, a young one with no toy, the visitor.
  - **Of the family:** a recipe its parent knew (§3.3), the question written on a grandparent's thing, a song it hasn't learned.
  - **To get better** (§2.2): "you want to make something finer than your last bell".
- Temperament weights which kinds appear:
  - curious: to know
  - orderly: to make better
  - sociable: for someone
  - playful: toys and games
  - bold: doors and creatures
- **The mind sees them in plain words** ("you want to know what is behind the north door", "you want something that keeps the cellar warm at night") and may take one as its focus or project, or ignore them all. The body leans toward whatever serves the pet's wants.
- **A want fulfilled is felt and seen.** The pet feels a lift ("you feel proud", "something settled in you"), a small burst shows over it, and a moment is logged. A new want takes its place. A want left alone for a world day fades and is replaced.

### 2.2 Skills
- Skills grow with practice: **making, mending, tidying, music, tending, reading**. A pet feels them in words, never numbers ("your paws are surer at the bench").
- **Skill changes results.** A skilled maker's things are bigger, do more and last longer, and some processes (§3.1) need some skill. A skilled singer's songs drift less when passed on. Young ones watching a skilled parent pick up a little.

### 2.3 Repeating stops paying
- Making the same kind from the same material again gives no lift, and the result says so: "you have made this before; it doesn't feel new". New kinds, new materials and new properties are what lift a pet.

---

## 3. Making by discovery

**Why:** properties exist (soft, warm, bright, noisy, cool, dark, quiet, bouncy, heavy…), but each bit gives one and combining only stacks them, so nothing new ever comes out. Finding out what works was v2's best moment. This is IDEAS "crafting by discovery", brought forward.

### 3.1 Materials change
- **Processes**, each at a place in the house:
  - soak: the pond
  - warm: by the hot pipe, in the sun shaft, or near a lit lamp
  - dry: the attic
  - press: under something heavy
  - weave: two strands at the workbench
  - carve: a hard bit at the workbench
  - melt: wax by heat
  - grind: stone on stone in the cellar
  - plant: a seed in the garden or greenhouse, which grows over days
- A process turns a bit into a **new material with new properties**, by hidden rules in a new data file, `crafting.toml`. Examples:
  - reed, soaked: supple reed, which can be woven
  - supple reed, woven: wicker, light and holds things
  - wax, melted: clear wax, bright and slow-burning
  - clay, warmed: fired clay, hard and holds water
  - string, woven: rope, strong
  
  Write about 30 to 40 rules, mostly plausible and a few surprising. Some processes fail or spoil a bit, which the pet is told.
- New mind action: `process <bit> <how>`. When the mind's focus is making, the body carries bits to the right place. The result is told plainly: "the reed went soft and bendy in the water".
- **Some kinds need processed materials:**
  - basket: wicker
  - candle: clear wax
  - pot: fired clay
  - rope: woven string
  - lantern: clear wax and something hard
  
  Getting one unlocks the kind, and that's a story moment.

### 3.2 Combining can make something new
- When two things' properties meet in a known way, the result gets an **emergent property** neither part had, from a table in `crafting.toml`. Examples:
  - bright + dark: glows softly, a light that isn't harsh at night (the lamp problem finally has an answer to find)
  - soft + warm: a nest that deepens sleep
  - noisy + bouncy: a toy that rings as it rolls and draws kin to play
  - heavy + noisy: a drum heard in the next room
  - cool + quiet: a calm corner for hot days
  
  Write about 15 to 25.
- **The house tells the pet what's new:** "this does something neither part did: it glows without being harsh". The pet is asked to name it for what it does now.
- Combining things whose properties don't meet makes the larger kind, as now, and the result says "nothing new came of it".

### 3.3 Recipes are family knowledge
- A discovery becomes a **recipe** the pet knows ("reed soaked, then woven, makes wicker"). It can teach it, write it on a wall or put it in a message, and its children start knowing some of what it knew.
- A recipe nobody alive knows is **lost**, though the things made with it stay. Finding a lost one again is a moment.
- Moments: "Grey Light found out that soaked reed can be woven", "the first soft glow in the house".

### 3.4 Tools
**Why:** without tools, discovery runs out once the easy processes are found. Tools make one discovery open the next.

- Three tools to start, each a kind made from a processed material (exact recipes in `crafting.toml`):
  - **carver** (e.g. carved stone, or fired clay with an edge): needed for carving
  - **trowel** (e.g. fired clay or carved wood): needed for planting (§3.5)
  - **hammer** (e.g. a heavy stone bound to wood with rope): mends a thing that broke or stopped working, and builds furniture (stool, shelf, chest) bigger and sturdier than hand-made ones
- A tool is a thing like any other: it has a maker and owner, can be given, taught, inherited and kept in storage. It wears with use and a skilled pet can mend it.
- Processes and activities that need a tool say so plainly when tried without one ("you need something with an edge to carve this"), and that gives the want "make something that cuts". Activities may already carry `needs_tool` from v3.3; use it.
- The first of each tool in the house is a story moment.
- The key (a locked room) and the ladder (the attic's high shelf) are not in v3.4. They come with mysteries.

### 3.5 Growing food
**Why:** the garden and greenhouse are rooms pets rarely visit, and the bowl the visitor fills is the only food. Growing food gives those rooms a reason, gives the forecast stakes, and is work the house needs.

- **Plant:** a seed (a bit found in the garden, greenhouse and storeroom deliveries) planted with a trowel in a planting bed or pot. It grows over two to four world days, through sprout and leaves to ripe.
- **Tending matters:** watered (by rain if it's outside, or carried water if not) and kept from the cold, it grows faster and gives more. Neglected, it wilts. A forecast of rain makes waiting a choice; a cold night ahead makes moving a pot inside one. The body's "tend" activity serves this.
- **Ripe food** is picked and can be eaten (energy, like the bowl, and a lift for eating something it grew), given, carried to the nursery for the young, or planted again for seed. Some plants give a bit used in making instead (fibre, dye, wax).
- Growing is felt in plain words: "the seedling you planted has two leaves now".
- The visitor's bowl stays. Fed by both, a pet prefers what the family grew.

---

## 4. The book and the radio matter

**Why:** both are windows to the real world, and right now neither connects to anything a pet wants.

### 4.1 Questions, and where they go
- A pet that meets something it doesn't know gets a **want to know**: a word from the radio it hasn't heard before ("drones"), a new creature, a material, a kind of weather, a word on a wall.
- **The book answers questions.** A pet with a want to know is told "the heavy book in the attic might know", once, until it finds the book. A grown pet can carry the book, slowly, to another room. It stays where it's put.
- **Answers can lead to making.** A small data map links what the book says to crafting rules. Reading that reeds are woven into baskets when wet gives the want "find out what water does to a reed". Read knowledge is a hint, never a recipe: the pet still has to try.
- What a pet reads it can tell kin, as now. A young one may ask an elder first.

### 4.2 The radio's forecast is useful
- The house's weather already follows the real sky, so the forecast is true. A pet that hears it gets a want to **prepare**: shut the window before rain, move things away from the leak, gather petals before the rain spoils them, take a warm thing to the cellar before a cold night.
- Preparing well is felt afterwards: "the rain came and your things stayed dry".
- **News:** each unknown word becomes a want to know. A pet that hears something new wants to tell someone ("the box said…"), and a telling is logged.

---

## 5. Easier to watch

**Why:** Tyler finds the bubbles too much ("I like the effect but it's too much"), and loose bits read as mess.

- **One line per pet over its head:** its name and a small sign for what it's doing.
  - The "wants to…" caption shows for 6 seconds when the focus changes, and on hover. The cards below the room hold the full words.
  - Speech bubbles only for words actually said.
  - Labels stay at a fixed spot above the head and never jump. When two overlap, the later one waits its turn instead of moving.
- **Bits that grow back are drawn where they grow:** petals on a flower, pebbles in a little pile, feathers in a nest, reed among the reeds. Only dropped bits lie loose.
- **A want fulfilled or a discovery** shows a small burst and takes the top line of the page.
- Fold in POLISH.md items where they touch these.

---

## 6. Packet and budget

- New in the packet: wants (up to three), skills in words, recipes known (short), questions. Fit them under the existing budget, cutting old lines first.
- Wants, skills, crafting results and recipes are all engine work, with no model calls. Calls per pet per world day go up by at most 10%.

---

## 7. Verifying and deploying

1. **Self-check additions:**
   - every process and emergent property follows the table;
   - recipes are inherited and lost;
   - wants are made, fulfilled and fade;
   - fidgets are never chosen as activities;
   - the book can be carried;
   - tools are required where the table says, wear and can be mended;
   - plants grow, wilt untended, ripen and feed.
2. **Stub runs over several world days:**
   - the §0 numbers;
   - no loops (a pet soaking the same reed forever);
   - discoveries keep coming for at least three days;
   - no single want type crowds out the rest.
3. **Real-model copy, two world days** (say first). Report:
   - every §0 number;
   - the list of discoveries with their moment text, including the first of each tool;
   - what was planted, where, and whether it ripened or wilted;
   - book questions and answers;
   - radio words that became questions;
   - 20 sample thoughts that show wants being used or ignored.
4. **Fresh-eyes watch:** a reviewer who hasn't seen the build watches three rooms for 5 minutes each and writes what each pet did, why, and what it was trying to achieve. Fix and repeat once if they can't.
5. **Deploy:** back up `data/`, one restart.
   - Living pets get skills from their history (things made count toward making).
   - They get no recipes; discovery starts fresh.
   - The book stays in the attic until someone carries it.
6. **Tell Tyler:** the numbers, screenshots, and a short list of what to watch for.

## 8. Not in v3.4

Invented kinds drawn from a pixel-part library, the key and the ladder, building that lasts, mysteries and games (wants and tools leave room for them), bodies that evolve (planned as v3.5), training while they sleep, and new asset packs. All stay in IDEAS.md.
