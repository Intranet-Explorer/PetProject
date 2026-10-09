# Pet — v3 spec: a lineage in a living house

v2 made a creature that works. It is also boring and predictable, and the long run shows why:

- **It thinks like an accountant.** Its packet is full of numbers ("energy -4.0, curiosity +0.1", "you have made 8 of the 12"), so it optimizes numbers. Its own reasoning: *"Creating a new object … is the most efficient way to spike curiosity."* Its beliefs are about game mechanics: what `observe` costs, when `look` fails with "bad target", how much an unmake refunds.
- **Its world runs out.** One room, three rules, one table of materials. The door has never led anywhere.
- **Every life is the same life.** The personality is the model's default, nothing carries from one pet to the next, and it ends when we stop it.
- **It is alone.** The only other mind in its world is a visitor who is rarely there.

v3 fixes all four together. Pets live, age, lay eggs and die. Children inherit a body, a temperament, a few heirlooms and a message from their parent, and live alongside the parent for a while. The door opens onto a house that keeps generating rooms, with weather, seasons, power cuts and small creatures that aren't the pet's doing. The pet feels its life instead of reading a scoreboard.

The aim is not to measure one more thing. It's that you can leave it for a day, come back, and find something happened that nobody predicted: a myth handed down three generations, a child that refuses its parent's advice, a family that moved into the garden.

SPEC-v2.md and SPEC.md stay as history. NEXT-LIFE.md is folded in here (§3) and can be deleted once this is built.

---

## 0. How to build this (read first)

This spec is a direction, not a script. It's written by someone who can't run the code. You can, so you will find places where it's wrong.

**Intent wins over letter.** Every section starts with a **Why**. When a mechanism here would defeat its own Why (a number that makes the pet stuck, a rule that can't be perceived, a feature that looks bad on screen), change the mechanism to serve the Why. Record every such change in `DECISIONS.md`: what the spec said, what you did, and the evidence. Don't ask first. Don't silently drop anything either: dropping a feature is a decision and gets logged with a reason.

**Use what the project has already learned.** FINDINGS.md is evidence. In particular:
- Pressure the pet can't perceive produces a stuck pet, not a clever one. Every new pressure in v3 needs a way to be felt.
- It can't attribute slow effects to one object among many without senses. New effects need sense lines.
- The physics must be slow enough for a pet that thinks every ~70 s to react.
- It makes 2-step plans whatever the format allows; design for that, don't fight it with wording.

**Don't stop at checkpoints.** Build the whole spec. Tyler is not going to look at intermediate states. The only reasons to stop and ask:
- deleting or overwriting any `data*` folder other than by archiving it,
- any network access beyond §6.6,
- changing the model,
- discovering that a section's Why can't be met at all.

**The quality bar.** A feature is done when it is visible, legible and pleasant in the view, works in the live engine with the real model, and survives a reload. A feature that works but looks rough is not done. A feature that only exists in the engine and the logs is not done. If you're unsure whether something is good enough, it isn't yet.

**Verification vs. watching.** Engine correctness is checked continuously by you, with the self-check, headless runs and stub brains. Watching a real life is the last step (§12), and it's yours too: you run the showcase, judge it against the interestingness bar, and improve until it passes. Tyler's first look is at something that already passed.

**Review your own work.** After each part (§13 order), re-read the part's Why and check the result against it. Before handing over, have a fresh agent that hasn't seen the build review the whole thing against this spec and the quality bar, and fix what it finds.

**Commits:** one or more per part, short imperative subjects, authored as Intranet-Explorer, no co-author trailers. Keep `pet-voice.xlsx` untracked.

---

## 1. What changes, in one table

| | v2 | v3 |
|---|---|---|
| What the pet perceives | numbers, deltas, costs, counts | feelings, events, what it notices |
| Lifetime | one pet, until we stop it | birth, aging, eggs, death, generations |
| What carries over | nothing | body, temperament, heirlooms, a parent's message, a name, a family tree |
| Others | a rare visitor | parent, children, siblings, small creatures, the visitor |
| World | one room | a house that grows room by room, with weather, seasons and events |
| Making things | costs energy, unmaking refunds it | made from gathered stuff; unmaking returns the stuff |
| Plans | 2-step intentions | intentions inside multi-day projects |
| Personality | the model's default | inherited temperament that shapes how it feels and thinks |
| Voice | one voice, same at every stage | grows by stage; every pet sounds like its family |
| The view | one room and a drawer | the house, many pets, weather, a family tree, life stories |

## 2. What stays

- The world is data. Pets act only through the checked action set. The engine is ground truth.
- No shell, files, network or code for pets. The model server stays on localhost.
- Intentions, think-rate limits, senses, familiarity, constrained JSON output, step durations, the voice's view-only rule.
- The genome renderer, marks, the mirror, self-portraits, taught behaviors, combine, paint.
- Append-only journals and `training.jsonl` (now per pet, tagged with lineage ids, for a later LoRA).

---

## 3. Feel, don't count

**Why:** a pet that reads numbers optimizes numbers, and that's the main reason v2 is predictable. It should experience its life the way a creature would: tired, uneasy, drawn to something, bored of something. The numbers stay in the engine and the Lab, never in the packet.

### 3.1 Needs as feelings
- Remove need numbers from the packet. Each need is reported as a felt state with an intensity, on every packet, for every need (not just the urgent one):
  - energy: *full of energy · awake · a bit tired · tired · exhausted*
  - comfort: *at ease · fine · uneasy · uncomfortable · miserable*
  - curiosity: *fascinated · interested · a bit bored · bored · restless for something new*
  - company (new, §7.4): *close to someone · content · a bit lonely · lonely · aching for company*
- The words for one need must not be systematically louder than another's. v2 showed restlessness, the only need described as a feeling, beating comfort.
- Temperament (§8.1) shifts the thresholds per pet, so a sensitive pet feels "uncomfortable" earlier.

### 3.2 Results as experiences
- Step results drop numeric deltas. "you rested; energy +8.0" becomes "you rested by the quiet stone and woke rested". Changes are described by size in words (*a little, clearly, a lot*) and direction.
- Remove "you have made 8 of the 12", energy costs, refunds and every other mechanic from the packet. Limits are felt in the world: the room is crowded; you're too tired to make anything that big.
- The "apart from it" separation from v2 stays, in words.
- `expect` is still required and still scored by the engine against the real (numeric) change. The scorer gets the words-to-numbers mapping; the pet never sees the numbers.

### 3.3 Folded in from NEXT-LIFE.md
1. **Feelings for every need:** done by §3.1.
2. **Churn stops paying:** done by §6.3. Making uses gathered stuff, unmaking returns it, nothing refunds energy. Novelty from making also fades for things similar to what it made recently, and things kept for a world day or more give a small comfort bonus when near ("this feels like yours").
3. **One belief reviewed per sleep:** at each sleep, show one belief (oldest unreviewed first) next to its own journal lines that bear on it. Ask: keep, revise or discard. Its own memories only.
4. **Mark what it made:** every thing in the packet says whose it is: *yours*, *your mother's*, *Pip's*, *a gift from the visitor*, *found*. Also grep every prompt for "character" and "agent"; if neither is in a prompt, its third-person self-talk is its own and goes in FINDINGS.md.

### 3.4 The meter-talk check
Count, per pet, the share of thoughts and beliefs that talk mechanics: numbers with signs, "efficient", "costs", "refund", "action", "bad target", tick numbers. This is a quality signal for the whole spec (§12), shown in the Lab.

---

## 4. Life and death

**Why:** a life that never ends has no shape, no stakes and nothing to pass on. Aging gives each pet a story with a beginning and an end; death makes care and choices matter.

### 4.1 Stages
Egg → Hatchling → Child → Youngling → Adult → **Elder** → death.
- Growth through Adult keeps v2's rule (days lived plus useful things), with the v2 thresholds as defaults.
- **Elder** begins after `adult_days` as an Adult (default 6). Elders move slower, think a little less often, tire faster, and unlock **bequeath** (§5.3) and **tell** (§7.2).
- **Lifespan:** a base (default 24 world days) adjusted by how well it lived: average wellbeing across its life shortens or lengthens it by up to 30%. Wellbeing is the engine's mean of all needs. The pet never sees its lifespan, but it feels aging: "your body feels slower than it used to".
- **Neglect:** if comfort and energy stay at the bottom for a long stretch (default 1 world day), the pet weakens: it feels "weak", and each further day costs 2 days of lifespan. A pet can die young. This is a Tamagotchi; that's the deal.

### 4.2 Death
- In its last day it feels "very old and tired". It may write final words (§5.2) and give heirlooms (§5.3).
- When it dies it lies still for a while, fades, and leaves a **memorial**: a small stone on the tile where it died, with its name. Anyone can `look` at it: "a stone for Pip, who lived 22 days and made 140 things". Memorials can't be moved or unmade.
- Its things stay where they are and become *Pip's things*: other pets can use, arrange, combine or unmake them.
- The engine writes its **life record** (§9.3).
- If the last pet dies with no egg, the lineage ends. The view says so, gently, and offers to start a new lineage. A new lineage starts in the same house, so the next family finds the old one's memorials and things.

---

## 5. Eggs and inheritance

**Why:** this is where "evolves" comes from. Bodies and temperaments change by mutation and by who survives to lay eggs. Knowledge changes by what parents choose to pass on, what children choose to believe, and what gets lost or distorted along the way.

### 5.1 Eggs
- Adults and Elders unlock `lay_egg` (one egg per action, a good amount of energy, only when energy is at least "awake"). Fertility (§8.1) sets how many eggs a pet can lay in its life: 1 to 3.
- If an Adult lays no egg by the end of its 3rd Adult day, it feels a strong pull to ("you feel ready to lay an egg"). It can still refuse. Refusing is data.
- Eggs hatch after `egg_minutes` (default 10 real minutes). The egg sits where it was laid. The parent can see it, sit by it, move it (`arrange`).
- Population cap: 4 pets alive (config). At the cap, `lay_egg` is unavailable and it feels "the house is full".
- The parent names the child as part of `lay_egg` (free text, ≤ 16 chars). If it doesn't, the child names itself the first time it says "my name is …"; until then it's "the little one".

### 5.2 The message
- At `lay_egg` the parent writes a message for the child, ≤ 600 characters, free text, in its own voice.
- At each sleep afterwards, until it dies, it can rewrite it. The last version is its **final words**. Every version is kept.
- The child receives the message at hatching, in its packet under **what your mother told you** (or father, or parent; the parent's genome sets a word, or the parent picks one when naming). It stays in the child's packet for life, below the child's own beliefs.
- The child's beliefs are its own. Inherited claims are never copied into its beliefs automatically. It can adopt, revise or reject them through normal beliefs, and the belief records its source: *lived*, *told by Pip*, *seen*.
- When the child later writes its own message, it decides what to pass on. That's how myths form.

### 5.3 Heirlooms
- `bequeath`: an Elder marks up to 2 of its things as heirlooms for a named child (or "my children"). Heirlooms can't be unmade by anyone, survive the parent, and show as *your mother's moon, left to you*.
- Heirlooms travel down generations: a child can bequeath an inherited heirloom (it counts toward its 2).

### 5.4 Body and temperament
- The child's genome is the parent's at laying, with one round of mutation (as at sleep) plus a stronger chance of one larger jump (a new pattern, a limb, a hue shift beyond 45°).
- Temperament (§8.1) is inherited with small mutations.
- Voice follows the genome, so families sound related (§10.6).

### 5.5 Claim tracing
**Why:** we want to see myths form, and that needs evidence, not impressions.
- Every message and belief is split into claims (one sentence each) by a cheap step at write time: model call or heuristic, your choice, but cheap.
- Claims are matched across generations by embedding similarity or by the model judging "same claim?", your choice; record which and its error rate on a hand-checked sample.
- Each claim gets a lineage id: who first said it, who repeated it, who changed it, who dropped it. A claim the engine can check against the physics (e.g. "lights at night make you uneasy") gets a truth flag.
- The Lab shows the claim lineages; the Family tab shows the most-inherited ones as "family sayings".

---

## 6. The house

**Why:** a world that can be exhausted produces a pet that settles. The house keeps offering new places, materials and rules, and it changes on its own, so neither the pet nor Tyler can predict what each life will face.

### 6.1 Rooms
- The house is a grid of rooms (up to 9, a 3×3 layout by default; config). The first lineage starts in the **nursery**, the v2 room, with the v2 objects.
- Each room has 1–3 doors to neighbours. A door leads to a room that is generated the first time any pet walks through it, from the room types below. Generation is seeded and logged so a house can be reproduced.
- **Room types** (each gets its own look, objects, findable materials, and one local rule):

| Room | Looks like | Found here | Local rule |
|---|---|---|---|
| Garden | soil, plants, sky | seeds, leaves, petals | rain waters plants; plants grow over days and can be eaten (a meal) |
| Cellar | stone, damp, dim | clay, stones, moss | cold at night; lights cost no comfort down here; things left on the floor get damp |
| Attic | beams, dust, light shafts | feathers, cloth scraps, old wood | sun shafts move with the hour; standing in one is warm; dust settles on things nobody uses |
| Pond room | water, reeds, glass | shells, glass beads, reed | the water's sound helps rest; things placed in water float away to a random room |
| Workshop | benches, shavings | wire, wood, metal bits | combining here costs less; noisy things are twice as loud |
| Music room | instruments, rugs | strings, bells, felt | sounds linger: noisy and humming things affect pets in neighbouring rooms too |
| Greenhouse | glass, heat, vines | resin, vines, petals | warm by day even in winter; plants grow twice as fast |
| Storeroom | shelves, crates | anything, a little of each | memorials of a previous lineage may be here; dark |

Add, change or cut room types to serve the Why; keep at least six.

- Each room's local rule is hidden like the v2 rules, felt through senses, and one rule per lineage can **drift** (§6.5).
- Moving between rooms: walking to a door and through it is a step. A pet perceives only the room it's in, plus sounds from next door ("you hear something humming in the music room").
- The house map is world data. Pets learn it by going places. Their packet includes a short "rooms you know" line from their own experience, not from the engine.

### 6.2 Gathering
- New action `gather` (target: a findable material in the current room). The pet carries up to 3 gathered bits. Bits regrow in their room over time (config per material).
- New action `drop` (put a carried bit down; it becomes a small object anyone can pick up).
- Bits have their own look in the view (a few distinct small sprites per material), not a generic dot.

### 6.3 Making from stuff
- Making now consumes gathered bits: one bit per part, and the bit's kind sets what the part can be made of. The v2 materials stay as **properties**; each bit kind maps to one or two properties (e.g. clay → hard or cool; feathers → soft or light; bells → noisy; resin → warm or bright). Write the mapping in `materials.toml`.
- Making still costs a little energy, felt, not counted.
- `unmake` returns the bits (one per part), not energy.
- This replaces the item cap as the main limit. Keep a crowding limit per room (felt: "this room is crowded").
- New properties found only in far rooms (at least three): e.g. **fragrant** (comfort for everyone in the room, wears with familiarity), **glassy** (a light that's only bright in sun), **springy** (move twice as far after using it). Tune them so they're worth discovering.

### 6.4 Weather and seasons
- A season lasts `season_days` (default 6 world days): spring, summer, autumn, winter. Seasons change day length, temperature (felt), rain chance, garden growth, and the light through windows.
- Weather is per day with variation: clear, cloudy, rain, storm, snow (winter), heat (summer). Felt by everyone, shown in windows and in outdoor-ish rooms (garden, greenhouse, attic).
- **Storms** can cut the power: every lamp-type light and every `bright` thing goes dark for a while. The pets don't control it. This is also the confound breaker from v2: dark nights that aren't the pet's choice, so "night" and "lights at night" finally come apart.

### 6.5 Events
**Why:** things should happen that no pet caused.
- A **director** (scripted, not a model) schedules events, more often when nothing new has happened for a while and less often during a crisis. Events, each with its own look and sound:
  - power cut; leak (water in a room, things move); draught (a door blows shut, a room gets cold); a delivery (a crate of random bits appears in the storeroom); a lost thing (one of a pet's things is found in another room); a visitor's surprise (if Tyler enables it, the director drops a gift at random times in his name, logged as the director's).
  - **Rule drift:** once per lineage, one room's local rule changes. Logged; the pets aren't told.
- **Small creatures** (scripted, never a model), at most 2 in the house at once, each with simple wants and visible behavior:
  - **moth:** comes at night, circles lights, eats soft things if left long enough.
  - **beetle:** wanders, carries bits from room to room, can be followed to where it sleeps.
  - **mouse:** shy; steals sweet things; hides in the cellar; runs from pets that move fast; comes closer to pets that stay still.
  - **bird** (garden only): sings in the morning, startled by noisy things.
  Pets perceive creatures, can look at, follow, feed (give a bit) or chase them. Creatures react to pets. A pet that feeds the mouse every day may find it waiting.

### 6.6 The window to the real world (optional)
- Config `real_weather` (default off): the engine (never a pet) fetches the current Twin Cities weather from one fixed host once an hour and uses it for the house's weather. Local only, no keys, failure falls back to simulated weather. This is the only network access in v3.

---

## 7. Others

**Why:** the most surprising things in projects like *Creatures*, *The Sims* and the Stanford generative-agents town come from minds reacting to each other. Parents and children overlapping in time gives v3 that for free.

### 7.1 Perceiving each other
- A pet perceives the other pets in its room: name, relation (mother, child, sister …), where they are, what they seem to be doing, how they seem (from their needs, as words: *seems tired*, *looks content*), and what they just said.
- It perceives what another pet did and how it seemed after, which is how it can learn by watching ("Pip used the fluffy nest and looked content").
- It hears pets in neighbouring rooms as sounds, without words.

### 7.2 Social actions
- `speak` takes an optional `to` (a pet or the visitor). Speech to a pet arrives in that pet's packet as "Pip said to you: …".
- `give` a carried bit or a thing (yours) to another pet nearby. The thing becomes theirs.
- `show` a thing to another pet: they get a line about it and its look, and it counts as novelty for them.
- `follow` a pet (continues until either acts otherwise).
- `nuzzle` a pet beside you: raises company for both, a little comfort.
- `tell` (Elder): a longer piece, ≤ 400 chars, to a pet nearby. The listener keeps it under "what Pip told you", like a parent's message.
- Pets can refuse: a `give` or `nuzzle` arrives as an offer the other accepts or ignores in its next intention.

### 7.3 Ownership and conflict
- Things belong to someone. A pet can use anyone's things, but can only unmake or combine its own (or a dead pet's). `take` (a living pet's thing) is allowed and the owner feels it when it notices ("your soft cloud is gone; Sol has it"). It's the only source of conflict; keep it.

### 7.4 Company
- A fourth need, felt like the others: rises near kin, nuzzling, being spoken to, the visitor talking; falls slowly when alone. It's what makes the visitor and family matter.
- Temperament `sociable` (§8.1) sets how fast it falls.

### 7.5 The visitor
- The visitor (Tyler) is perceived as "the visitor", a big presence that can feed, give, talk, place, poke and open windows in any room the view is showing.
- New: the visitor can **name** a pet or a thing (it's heard as "the visitor calls you Moss"); the pet decides whether to take the name.
- The visitor's actions arrive only in the room being viewed.

---

## 8. Mind

**Why:** v2's pets are the same mind every time. Temperament makes each one lean differently, and projects give lives a longer arc than two-step plans.

### 8.1 Temperament
Inherited, mutating genes that shape the mind, never named to the pet. Each is 0–1. Suggested set:

| Gene | What it changes |
|---|---|
| curious | how fast familiarity wears off and how loud boredom is |
| sensitive | the thresholds where discomfort becomes "uncomfortable" |
| sociable | how fast company falls; how often it addresses others |
| bold | willingness to go into unknown rooms; how creatures react to it |
| patient | how often it thinks (within the global limits); longer plans |
| playful | sampling temperature (0.5–1.0) and the sense lines' tone |
| fertile | eggs per life, 1–3 |
| hardy | resistance to neglect; lifespan bonus |

- These act through perception (thresholds, wording, what's mentioned) and the engine (think rate, temperature, lifespan), never through a sentence telling the pet what it is like.
- Show temperament as a small radial chart per pet in the Family tab and on its card.

### 8.2 Projects
- On waking, the pet may set a **project**: a goal for the coming days in its own words ("make the garden a place to sleep"), up to 1 at a time. It's in every packet while it lasts: "your project: … (started 2 days ago)".
- At each sleep it can keep, revise, finish or abandon its project. Finished and abandoned projects go into its life record.
- Intentions stay as they are; projects give them a direction. Don't force plan length.

### 8.3 Memory
- Beliefs: keep v2's, plus source (*lived / told by X / seen*), plus the sleep review (§3.3). Cap active beliefs; at the cap it must revise or discard.
- **What you were told:** messages and tells from others, separate from beliefs, most recent and parent first.
- **Rooms you know**, **who you know** (with one line each, from its own words), **your things** (now possibly spread over rooms; list those in the current room plus heirlooms).
- **Packet budget:** keep the packet under a fixed size (default ~2,500 tokens; tune by latency). v2's packet grew until a call took 12 s at the median. Decide what's cut first and log it in DECISIONS.md.

---

## 9. Story

**Why:** Tyler should be able to catch up on a day he missed in two minutes, and on a whole lineage in ten.

### 9.1 Moments
Births, first words, namings, deaths, eggs, messages written, heirlooms passed, first time in a new room, events, creatures befriended, takes, gifts between pets, a claim passed down a third time, a belief discarded. Each moment is one line with a small icon and time, clickable to jump to that pet and room.

### 9.2 Diary
Per pet, its dream summaries by day, as v2, plus project changes.

### 9.3 Life record
At death, the engine assembles, and the pet (as an Elder, in its last day) contributes to, a record:
- name, parents, children, lifespan, stages with dates, cause of death,
- body at each stage (rendered portraits), self-portraits, temperament,
- its message (all versions) and final words,
- its 10 most-used things, heirlooms given and received, rooms it knew, creatures it met,
- **"My life"**: a short story it writes in its last day, ≤ 800 chars. If it dies before writing it, the engine writes a factual summary instead, marked as such.

### 9.4 Chronicle
A daily house summary written by the engine from moments (no model), plus, once per world day, one model-written paragraph (`chronicle`, thinking on, during the night when the pets sleep), shown at the top of the Story tab.

---

## 10. The view

**Why:** v2's view is functional. v3's should be something Tyler wants to leave open on a second screen. Every system above has to be visible, or it doesn't count.

### 10.1 Layout
- **House view:** the main screen is the room currently followed. A minimap of the house shows every known room, which pets are where, weather, and events in progress. Click a room to look at it.
- **Follow:** click a pet to follow it between rooms. "Follow: auto" follows whatever is most interesting right now (a birth, a death, a creature, a conversation).
- **Pet cards:** a small strip of every living pet: portrait, name, stage, how it seems, its project.
- **Drawer tabs:** Mind (selected pet), Things, Family, Story, Lab.

### 10.2 Rooms
- Each room type has its own palette, floor, walls, light and props, drawn in code in a coherent style with the v2 room. No third-party art.
- Day and night light, season palette shifts, weather effects (rain streaks on windows and in the garden, snow, storm flashes, heat shimmer), power cuts plunge rooms into dark with only windows lit.
- Gathered bits, eggs, memorials, creatures and doors all have distinct, readable drawings.

### 10.3 Pets
- Several pets at once, each with its genome body and name label; labels never overlap.
- Expressions from state: tired eyes, content bounce, uneasy tremble, a small heart on nuzzle, a startle on events.
- Aging shows: Elders are a little greyer and slower, with a slight stoop in the bob.
- Speech bubbles name the listener when directed ("→ Sol").

### 10.4 Family tab
- A family tree, generations top to bottom, each pet as its portrait at death (or now), name, lifespan, and number of eggs. Living pets highlighted. Click a pet for its life record.
- Under the tree: **family sayings** (the most-inherited claims, with their path through the tree and a truth mark where the engine can check them), and **heirlooms** with their history.

### 10.5 Story tab
The chronicle, today's moments, then earlier days. The life records of the dead, newest first.

### 10.6 Voice
- Voice Phase 2 (VOICE.md): talking grows with the stage. Elder voices are lower, slower, with a little tremble.
- Every pet's voice comes from its genome, so a child sounds like its parent. Two pets talking babble at each other audibly, with a short gap like turn-taking.
- Creatures, weather and events get their own sounds (moth flutter, rain, thunder, the power cut's hum dying).
- Sound from the followed room is full volume, neighbouring rooms muffled, others silent.
- Still view-only; nothing about sound reaches a pet.

### 10.7 Quality
- Smooth at 60 fps with 4 pets, 2 creatures and weather on an M-series Mac; nothing jitters when the snapshot updates.
- Readable at 1280×800 and on a big screen. Light and dark theme.
- No overlapping labels, no text clipped, no placeholder art, no debug text in the main view.
- A reload restores exactly what was on screen.

---

## 11. Engine

### 11.1 Many minds
- A scheduler serializes model calls across pets with priorities: urgent (low need, spoken to, an event) before routine; sleep work at night. Track calls per hour per pet and total; the total stays under a configured budget (default 150/hour) by slowing routine thoughts, never by dropping urgent ones.
- Per-pet data folders under `data/lineage-<id>/<pet>/`; one SQLite db per lineage with tables for pets, kinship, messages, claims, rooms, bits, events, creatures, moments.

### 11.2 Restart safety
- Kill the engine at any moment and restart it: every pet, egg, creature, carried bit, project and pending message comes back as it was. Add this to the self-check.

### 11.3 Simulation modes
- **Stub brain:** a scripted brain that uses every action (including the social ones) in plausible ways, for headless runs. It is how you verify the engine at speed.
- **Fast clock** with real model, for the showcase (§12).
- Headless runs with stub brains over many simulated generations must not grow memory or db without bound.

### 11.4 Lab
- Everything v2's Lab had, per pet, plus: meter-talk share (§3.4), claim lineages, temperament over generations, wellbeing over life, cause of death, rooms discovered, creature interactions, model calls per hour.

### 11.5 Config
Everything new is tunable in `config.toml`, `materials.toml`, and a new `house.toml` (room types, bits, creatures, events, seasons). No magic numbers in code.

---

## 12. Done: the showcase

**Why:** Tyler said it plainly: we test nothing until there's something interesting to test. So before handing over, you run a life yourself and only hand it over if it's interesting by the bar below.

### 12.1 The run
- Archive the v2.5 life first (§13 part 0).
- Fast clock and short lives (e.g. world day = 15 real minutes, lifespan 16 days), real model, until at least **4 generations** have lived, or 12 real hours, whichever comes first. Use `./run.sh` so it survives.

### 12.2 The interestingness bar
All of these must be true, from the logs, not impressions:
1. **It reads like a creature.** Meter-talk (§3.4) in under 10% of thoughts for every pet after its first day. v2.5's figure goes next to it for comparison.
2. **The lineage changed.** Bodies, temperaments and voices visibly differ across generations; at least one temperament gene drifted noticeably along a line.
3. **Something was passed down and mattered.** At least one inherited claim changed a child's behavior in its first day, traceable in its thoughts.
4. **A myth or a correction.** At least one claim travelled 3 generations, either holding (a family saying) or being changed or dropped by a child after its own experience contradicted it.
5. **They dealt with each other without the visitor.** Pet-to-pet speech, gifts or nuzzles happened, and at least one exchange got a reply.
6. **The world mattered.** Every generation went beyond the nursery; at least 5 room types were discovered; at least one event visibly changed what a pet did next; at least one creature was interacted with more than once by the same pet.
7. **No two lives were the same life.** Different projects, different favourite rooms or things, different words for the same things.
8. **It looks finished.** Screens of every room type, the family tree, a birth, a death and a storm, all meeting §10.7.

If a criterion fails, diagnose why from the logs, change the design (and log the decision), and run again. Don't lower the bar. If a criterion turns out to be wrong as a measure, say why in DECISIONS.md and replace it with a better one.

### 12.3 The handover
- `SHOWCASE.md`: the run's story in a page, with screenshots, the family tree, three message chains quoted in full across generations, the strongest myth or correction traced step by step, the best pet-to-pet exchange, what each event changed, and the bar with evidence per criterion.
- A required last section, **"What's still boring"**: your honest list of what still feels predictable and what you'd do next.
- Update FINDINGS.md and README.md. Then start the real lineage on the real clock and tell Tyler it's ready.

---

## 13. Build order

Not checkpoints, just a sensible order, since later parts depend on earlier ones. Don't stop between them.

0. **Close v2.5.** Before stopping it: one model call asking the current Adult to write a message for the egg it will never see (≤ 600 chars, using the §5.2 prompt). That message becomes the first v3 pet's "what your mother told you", from a mother whose name is whatever it calls itself, or "the first one". Save its beliefs, last five dreams and Things into `data.v2.5/`. Archive. Delete NEXT-LIFE.md (folded into §3).
1. Feel, don't count (§3). It changes every prompt, so it goes first.
2. Engine for many pets: scheduler, per-pet data, restart safety, stub brain (§11).
3. House: rooms, doors, generation, gathering, making from stuff, local rules (§6.1–6.3).
4. Life and death, eggs, inheritance, messages, heirlooms (§4, §5.1–5.4).
5. Others: perception and social actions, company, the visitor's new powers (§7).
6. Mind: temperament, projects, memory and packet budget (§8).
7. Weather, seasons, events, creatures, real weather (§6.4–6.6).
8. Claim tracing (§5.5), story, life records, chronicle (§9).
9. The view, in full (§10), and voice Phase 2 and per-pet voices.
10. Lab (§11.4), self-check additions, fresh-eyes review.
11. Showcase (§12) until it passes, then hand over.

---

## 14. Not in v3

- LoRA training. Keep writing `training.jsonl` per pet, tagged by lineage, so a later version can train on a family's experience.
- Voice Phase 3 (a TTS voice it describes).
- Hardware.
- More than one house.
