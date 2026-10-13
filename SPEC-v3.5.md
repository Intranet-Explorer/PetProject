# Pet — v3.5 spec: parts

v3.4 gave the pets wants, tools, food and making by discovery, and they used it: the house's first trowel came from a pet reading the book, warming clay and making it within a world hour. Two limits are left, and both are about what the eye sees:

- **Bodies don't show descent.** The genome only tweaks one blob (roundness, colour, pattern, eyes), and a body drifts every night, so a child doesn't look like its parent and two families look like two colours of the same creature (SHOWCASE "What's still boring", item 9).
- **Pets can only make what someone drew.** Every made thing is one of about 40 kinds with a fixed sprite. A discovery can change what a thing *does*, but never produces a thing that didn't exist before.

v3.5 adds **one library of pixel parts** and uses it twice: for **bodies that evolve**, and for **things the pets invent**. Two environmental changes ride along because they use the same tools and art: **building that lasts** (the house becomes theirs over generations) and **seasons that matter**.

SPEC-v3 to v3.4 still hold. Departures go in DECISIONS.md as **Part 17**.

---

## 0. How to build this

Same rules as before: intent over letter, every section's **Why** is the test, log departures, and stop only for data deletion, network access beyond what's allowed, a model change, or a Why that can't be met.

**The test for the whole spec:** Tyler can tell the two families apart at a glance and see which pet is whose child. Things invented in the house look like what they are, and the rooms look different from how they started.

These are measured on a copy of the live house with the real model (in turbo where a bar needs many days or births), plus a stub run for anything about many generations:

| | Bar |
|---|---|
| A reviewer shown 8 pets' sprites, with no names, sorts them into their families | at least 6 of 8 |
| The same reviewer pairs each child with its parent | at least 3 of 4 |
| A new body part appears in a family (stub run, many births) | about 1 birth in 12, never more than 1 in 6 |
| A body trait is felt (a sense line from it), per pet per world day | at least once |
| Invented kinds, house-wide per world day | at least 1 |
| A reviewer shown 10 invented things (sprite and name) says what each is for | at least 7 of 10 |
| A lasting project finished, house-wide | by the end of world day three |
| In winter on the copy, the outdoor garden is dormant and the greenhouse still grows | yes |
| Model calls per pet per world day | no more than 10% up |
| v3.3 and v3.4 bars | still pass |

**How to work:**
- **Branch and copies:** build on a branch in a worktree, check on a copy, back up `data/`, and deploy with one restart. Use two helper agents at most.
- **Real-model copies:** pause the live house while one runs, and say when you pause and resume.
- **Deploying:** if every bar passes, deploy without waiting. If a bar misses by a hair (one pet, a few percent), deploy and note it in DECISIONS. If it misses by more, stop and report.
- **Commits** are authored as Intranet-Explorer, with short imperative subjects. A Claude co-author trailer is fine.
- **Files:** README.md is the front page, so don't edit it. Run notes go in RUNNING.md and small visual fixes in POLISH.md. Keep `pet-voice.xlsx` and `IDEAS.md` untracked.

---

## 1. The parts library

**Why:** the house can only show what has a sprite. A library of parts the engine puts together itself lets the pets and their bodies become things nobody drew in advance.

- **Parts are pixel art in the repo:** drawn for this project in the Ninja Adventure style, saved under `view/assets/own/parts/`, and released under the repo's MIT licence.
- **No pack is needed.** Optional packs never supply parts. Anyone who clones the repo gets every part.
- **Every part has:**
  - **attach spots:** tip, top, side, base and inside, so other parts know where they can go;
  - **a layer:** behind, body or front;
  - **regions** that material and genome colours paint: main, trim and glow.
- **Two families of parts:**
  - **Body parts:** ears, tails, horns and antennae, crests, whiskers, feet, mouths, plus 4 to 5 body plans (§2).
  - **Thing parts:**
    - bases: stick, bowl, box, disc, ring, frame, cushion, block, bundle;
    - tops and ends: flame, blade, tines, bell dome, lid, spout, strings, wheel, hook, flower, gem, sail;
    - wraps and details: cord, cloth, band, studs.
  
  About 40 to 60 parts to start.
- **Composition rules,** in data:
  - at most 3 parts per thing;
  - scaled to fit the kind's size (16×16 for small things, 24×24 or 32×32 for furniture);
  - outlined, and lit the way the pets are;
  - anything that glows gets a soft halo.
- **A parts preview page** (like `view/assets/preview.html`) shows every part, every body plan and a grid of random compositions, for checking the style.
- **The style check from SPEC-v3.2 §1.2 applies.** A part that clashes with the pack gets redrawn.

---

## 2. Bodies that evolve

**Why:** families should look like families. Descent you can see is half the point of generations: a lineage's look should drift, branch and sometimes surprise.

### 2.1 Body parts as genes
- **Gene slots,** each with a value:
  - ears: none, round, pointed, long
  - tail: none, stub, long, fluffy
  - head: none, horns, antennae, crest
  - whiskers: yes or no
  - feet: nubs, paws, long legs
  - mouth: dot, wide, beak-ish
  - pattern: plain, spots, stripes, patch, gradient
- **Inheritance:** a child gets each slot from its parent, with a small chance of a step to a neighbouring value. Size, colour and pattern keep their existing genes.
- **Patterns combine** rather than replace. Spots plus stripes can give broken stripes, and patch plus gradient a faded patch. These are table rules.
- **Bodies no longer drift every night.** Changes happen at birth, plus a little greying and slowing with age. That's what makes a parent and child look alike when the child hatches.

### 2.2 Rare big mutations
- **About 1 birth in 12** gets something new: a part no ancestor had (the first tail in the line), or a value two steps away.
- It's a story moment, and the family tree marks the branch.
- **Body plans** are a rarer gene, about 1 in 40 births:
  - one blob (today's)
  - head on a body
  - two segments
  - long and low
  - tall and thin
  
  A great-grandchild can look like a different species.

### 2.3 Traits that matter
- Small effects in the house, felt as senses and never as numbers:
  - **thick fur** (from fluffy tail and long ears together, or its own gene): the cellar's cold and winter (§5) wear on comfort less. "Your thick fur keeps the cellar's chill off."
  - **big ears** (long): hears speech, songs and the radio from the next room.
  - **long legs:** walks faster.
  - **dark coat:** the moth ignores it.
  - **small:** fits through the gap under the storeroom shelf to a corner others can't reach (one hidden bit spot).
  - **whiskers:** notices loose bits and creatures sooner, so gathering and taming wants come to it more often.
- **So families adapt to where they live** through who thrives and who lays eggs. That's measured over many births in the stub run, not promised.

### 2.4 The live family
- Each living pet gets slot values derived from its existing genome and seed, mostly plain ones, so nobody changes look much overnight.
- The two families must differ in at least two slots, so they can be told apart from the start.

---

## 3. Things the pets invent

**Why:** discovery should be able to produce new things, not only new materials and properties. A thing invented in one family should exist only in that house.

### 3.0 Amendment (Tyler, 13 October): inventions must have a use
The parts preview's random sheet showed what parts can do with no meaning behind them: "teal ring + brown cloth + blue strings". That is a style test, but nothing in §3.1 stopped the house filling with things like it. The difference that matters: the random sheet combined parts nobody chose. In the house, a pet chooses what to put together, and any combination is allowed. What the uses decide is what the result **does**:

- **If it fits a use** (below), it's a new kind with that use's effect. A fork with a torch on it is a carried light.
- **If it fits no use,** it's still a new thing: drawn from the two things' parts, named by the pet, with its materials' properties, but no special effect. It's a **curio**, like a bell sewn onto a cushion. Curios are kept, given and inherited like keepsakes, and can be fed to the vending machine (§4.3).

| Use | Parts (base + what's added) | What it does in the house |
|---|---|---|
| carried light | stick, fork or handle + flame | a light that goes where its carrier goes |
| soft light | flame or gem + cloth or shade | lights a room at night without harshness (the lamp's answer) |
| cutter | handle + blade or edge | counts as a carver |
| digger | handle + flat blade | counts as a trowel |
| pourer | bowl or pot + spout | carries water to plants |
| keeper | box, bowl or pot + lid | food inside doesn't spoil; things inside count as stored |
| cart | box or block + wheels | carries several things at once |
| instrument | frame, bowl or box + strings or bell dome | plays; can be learned to play like a song |
| reacher | stick + hook | reaches high places (the attic's high shelf) |
| chime | ring or frame + hanging pieces | sounds in the wind; in the garden it tells the weather |
| seat or bed | cushion + frame or block | better rest than either part |
| planter | pot or bowl + flower or seed | grows a plant indoors |
| boat | disc or bowl + sail | floats on the pond; a toy |
| rolling toy | ball or disc + bell | rings when rolled; draws kin to play |
| feeder | bowl + seed or food | draws creatures; helps taming |
| keepsake | ring, disc or block + gem, studs or band | no use but meaning: kept, given, inherited |

- **Decoration stays in the material.** Studs, bands and colour come from the material and the maker, never as a random extra part.
- **The parts preview's random sheet** is replaced by two sheets:
  - one per use, showing it in five materials;
  - one of curios made from real pairs of existing kinds (fork + torch, bell + cushion, basket + wheel), not random parts.
  
  A reviewer should say what each use is for, and recognise both halves of each curio.
- **The pet still names it** ("night fork" is a carried light), and the use decides what it does.
- More uses can be added later in data (`uses.toml`).

### 3.1 When a new kind is born
A new kind is created whenever a pet **combines** two things in a way the house hasn't seen. It gets a use if it fits one (§3.0); otherwise it's a curio.

### 3.2 What it is and does
- **Its parts:** the base comes from the sturdier or larger thing. The other thing gives its **signature part** (the torch its flame, the bell its dome, the basket its weave), placed on the base's free attach spot. Up to 3 parts in all.
- **Its materials** colour each part.
- **What it does** comes from the engine's rules, never from the picture:
  - the properties of both parts;
  - any emergent property;
  - flags taken from the base: hangs, sits on the floor, holds things, can be carried.
- **The pet names it** for what it does ("night fork"). The house registers the new kind with that name, its parts, properties and recipe.

### 3.3 Recipes and loss
- **An invented kind is a recipe** like any other (v3.4 §3.3): the maker knows it, can teach it and write it down, and it can be lost.
- **When a recipe is lost,** the things made from it stay, but nobody can make more until it's found again.
- **Moments:** "Lean invented the night fork: a light you can hold up into a dark corner."

### 3.4 Limits
- **Composition limits:**
  - at most 3 parts;
  - a part can't sit on a spot that doesn't exist;
  - two flames, or two blades, don't stack.
- **No near-duplicates:** at most 20 invented kinds a house per world day. A combination that only repeats one of the house's own inventions makes that kind, not a new one.
- **Sound:** an invented noisy thing sounds like its loudest part (bell dome rings, strings pluck, a drum-ish block thuds).

---

## 4. Building that lasts, and a house that becomes theirs

**Why:** the house looks the same in every generation except for the clutter. A family's home should look like theirs, built up and changed by its own hands, so generations leave visible marks.

### 4.1 Projects
- **Lasting projects,** each changing a room for good:
  - **furniture:** a bench, a table, a big shelf, a bed frame;
  - **mending:** stopping the leak, fixing the draught;
  - **improvements:**
    - insulating the cellar, so it stops being cold;
    - a bridge over the pond, which opens a spot only reachable from it;
    - a window box in the nursery;
    - a lamp niche with a soft glow;
    - a trellis in the greenhouse, which gives more vines;
    - a hutch for a tamed creature.
  
  Start with about 10, in data (`building.toml`).
- **What one needs:** a hammer (v3.4 §3.4), materials that are carried and placed, and several work sessions over 1 to 3 world days.
- **Shared work:** two pets can work on one together. That counts as "being with" (v3.4 §1) and goes faster.
- **Visible progress:** scaffolding or a half-built frame shows while it's under way.
- **A finished project becomes a fixture with its builder's name** ("the bench Lean built"), lasts across generations, and can be mended when it wears.
- **Wants for projects** come from the room: a draught gives the want "stop the cold coming in", and a crowded floor gives "build a big shelf".

### 4.2 Decorating
- **Dyes from plants and processes:** berries give red, leaves green, charcoal black, and so on (crafting rules in data).
- **What dye can do:**
  - a pet can paint a wall section, a floor patch or a rug with simple patterns (stripes, dots, a border);
  - a family's patterns can echo its coats (§2.1), so a household's rooms come to look like it.
- **Paint fades over many world days** unless it's redone.
- **Pets react to decoration:** a painted room is felt as homely by the family that painted it, and only as a little strange by a stranger.

### 4.3 The vending machine and base materials (Tyler, 13 October)
**Why:** making needs a steady supply of real ingredients. Bits that grow back (petals, fluff, reed) aren't enough to build tools, furniture and projects. Unwanted things also pile up with nowhere to go. A machine that hands out materials and takes things back solves both, and it's fun to watch.

- **Six new base materials,** with properties and crafting rules in `crafting.toml`:
  - **wood:** hard, light; carve gives a handle or plank
  - **stone:** hard, heavy; grind gives sharp stone or grit
  - **metal:** hard, rings when struck, holds warmth; warming lets it bend
  - **clay:** soft until warmed, then fired clay
  - **fibre:** woven gives cord, pressed gives felt
  - **sand:** kept for glass later (v3.6); for now, a weight and a filler
  
  Use them in the existing processes, and add about 15 rules.
- **The vending machine:** a fixture in the storeroom, drawn in the house style (repo art), with lights and a clunk when it gives something.
  - **It gives:** each pet can take 2 materials a world day free (so a new family can always start), choosing which.
  - **It takes back:** a pet can feed it a made thing or bits and choose a material in return, one per thing (bits: one per three). The kind decides which materials it gives: soft things give fibre, hard things wood or stone, noisy things metal.
  - **What it never takes:**
    - heirlooms;
    - memorial stones;
    - anything in a keepsake box;
    - anything belonging to another living pet without that pet's leave.
  - **Its stock is limited** (about 12 of each), with a little restocked each morning by delivery.
- **The visitor can stock it.** A header control, "Stock the machine", lets Tyler add materials of his choice, up to its limit. Pets perceive it: "the visitor put metal in the machine".
- **Wants use it:**
  - want-chaining (v3.4) can lead to "get some clay from the machine";
  - an orderly pet wants to feed spare things to it, such as a room's third nest or a charm nobody has touched in days;
  - a pet with nothing to make wants to see what's in it.
- **On screen:** the machine lights up when used, and the item drops into the pet's paws.
- **New bars for §0:**
  - the machine is used at least 3 times per world day, house-wide;
  - at least one thing is fed back per world day;
  - things lying about don't rise over two world days.

---

## 5. Seasons that matter

**Why:** seasons already change on the world clock, but "lost things and seasons leave no trace in what pets think" (SHOWCASE, "What's still boring", item 11). With food, building and fur in the house, seasons can have real stakes.

- **Spring:** flowers and more seeds in the garden, eggs a little likelier, rain more often.
- **Summer:** long days, faster growing, and warm things uncomfortable by day.
- **Autumn:** leaves fall in the garden (a new bit), and the harvest is plentiful.
- **Winter:**
  - snow over the garden: outdoor beds go dormant and only the greenhouse grows;
  - short days, and cold rooms colder;
  - warm things, insulation and thick fur matter;
  - food spoils slower in the cold.
- **Food keeps** in a pot or basket (crafted, v3.4), and spoils loose. Wants appear in autumn to store food and get ready for winter.
- **Seasons are visible:** garden and window tiles change (blossom, green, orange leaves, snow), and pets feel the season in their senses.
- **They follow the world clock, not the real calendar.** On the two-hour day a season is a few real days, so Tyler sees all four in about two weeks.

---

## 6. View, packet and budget

- **View:**
  - pets drawn from parts, with every animation working for every body plan;
  - invented things drawn from parts;
  - projects with their progress shown;
  - paint on walls and floors;
  - seasonal tiles.
- **The family tree** shows each pet's sprite, so descent can be seen at a glance.
- **New in the packet:** the pet's own body in a few words, which a pet sees once a day ("you have long ears and a fluffy tail, like your mother"); the project in hand; the season's needs. Cut old lines first, and keep calls within 10%.
- **Engine work only:** composition, inheritance, traits, building and seasons make no model calls.

---

## 7. Verifying and deploying

1. **Self-check additions:**
   - composition never exceeds 3 parts or uses a missing spot;
   - every gene slot inherits and mutates within its bounds;
   - traits apply;
   - invented kinds register, are made again from their recipe, and are lost;
   - projects progress, finish and persist;
   - seasons switch the garden.
2. **Stub run** over 40 or more births:
   - the mutation rates;
   - families stay distinguishable;
   - no single body plan takes over.
3. **Real-model copy, two world days, season forced to winter for the second** (pause the live house). Report:
   - every bar;
   - each invented kind, with its sprite, name and what it does;
   - projects started and finished;
   - what the pets said about their bodies, the season and their building.
4. **Fresh-eyes check:**
   - the family-sorting and parent-pairing test on sprites;
   - naming 10 invented things from sprite and name;
   - a 5-minute watch of three rooms.
5. **Deploy:** back up `data/`, one restart. Living pets get parts as in §2.4, and the season stays where the world clock has it.
6. **Tell Tyler:** the numbers, a sheet showing every pet's sprite and each invented thing, and a short list of what to watch for.

## 8. Not in v3.5

The key, the ladder and mysteries; areas outside the house; creatures that breed or form an ecosystem; games pets invent; training while they sleep; new asset packs. All stay in IDEAS.md.
