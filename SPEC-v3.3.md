# Pet — v3.3 spec: alive

v3.1 and v3.2 gave the house new things and a real look. The pets still don't *do* much. In the live house over three world days:

- **About 40% of all steps were rest, look or observe.** Making things was 19 steps out of roughly 530. "Look at the west door" filled whole hours.
- **The language model is the pets' only source of behaviour.** It thinks about once a minute and plans two steps, and those steps are often a 40-second rest or a 12-second observe. Even a well-motivated pet spends most of its time standing still.
- **Nothing in the house needs doing.** Needs are the only motive, and things they make pile up in heaps.
- **Tyler rarely hears them talk.** Speech is rare, and the rooms have gone quiet.

v3.3 makes the pets **always visibly busy** without spending more model calls, by giving each pet a body that acts on its own between thoughts. It adds order (tidying and places to keep things), lets Tyler turn the radio on for them whenever he likes, brings back sound, and fixes what the v3.2 deploy left rough.

This is **Phase A**. Phase B (purpose: crafting by discovery, tools, building, work, mysteries, games) is outlined in §7 so Phase A is built to take it. SPEC-v3, v3.1 and v3.2 still hold. Departures go in DECISIONS.md as **Part 15**.

---

## 0. How to build this

Same rules as before: intent over letter, every section's **Why** is the test, log departures, stop only for data deletion, network beyond what's allowed, a model change, or an impossible Why.

**The test for the whole spec:** Tyler watches any room for ten minutes and it feels alive. Before that, these must hold on a copy of the live house with the real model (§8):
- In any 5 minutes, every awake pet does **at least 5 visibly different things**.
- No awake pet stands still for more than **30 seconds**, unless it's visibly asleep or resting in a resting pose.
- Resting, looking and observing together are **under 25%** of awake time.
- **Model calls per hour don't go up.**
- Someone watching cold for 5 minutes can say what each pet was doing and roughly why.

**The live family keeps living.** Build on a branch in a worktree, verify on a copy, back up `data/`, deploy with one restart. Keep parallel helper agents to **two at most**; the last build hit the usage limit with four.

Commits authored as Intranet-Explorer, short imperative subjects, no co-author trailers. Keep `pet-voice.xlsx` and `IDEAS.md` untracked unless Tyler says otherwise.

---

## 1. Two layers: body and mind

**Why:** this is how *The Sims* and the Stanford "generative agents" town stay alive on little compute. A cheap layer keeps the creature moving every moment; the expensive layer decides what matters. Right now the expensive layer does everything, so most of the time nothing happens.

### 1.1 The body (no model)
- Runs every engine tick (about 2 s). When the pet isn't already doing something, it picks the best **activity** from a menu and does it.
- Activities are **short** (3–20 s), **animated**, and **real**: they change the world where they should (tidying moves things, gathering fills paws, eating empties the bowl) and are logged, more briefly than a model-chosen step.
- **Starting menu** (defined in data, `activities.toml`, so Phase B can add more without engine changes):
  wander · explore a doorway · peek into the next room · inspect a thing · fiddle with a thing · play with a toy (ball, top, bell…) · sit by the window · short nap · stretch / yawn / groom · eat · tidy (pick something up and put it where it belongs, §2) · carry a thing to its place · gather a bit · tend a plant · follow kin · sit with kin · watch or follow a creature · visit a memorial stone · hum or murmur to itself · babble to someone nearby · sing a song it knows
- **Scoring**, each tick, for each activity the pet could do now:
  - **needs:** the most urgent need pulls toward what eases it (tired → nap; lonely → sit with kin)
  - **temperament:** curious → explore and inspect; playful → toys and play; sociable → kin; orderly → tidy (§2.4); bold → doorways
  - **habits** (§1.3)
  - **the mind's current focus** (§1.2): strongly weights what serves it
  - **time of day and weather:** windows at dusk, staying in when it storms
  - **variety:** an activity done many times in a row scores lower, so the body doesn't loop
  - a little randomness, so two similar pets don't move in lockstep
- **Interrupts:** being spoken to, an event, a need dropping into "bad", a new thing in the room. The body stops what it's doing and reacts (turns, looks, startles), and if it matters, the mind is asked to think sooner, as now.

### 1.2 The mind (the model)
- Thinks at the same rate as now. What it returns changes:
  - **focus:** what it wants to be about for the next while, in its own words *and* as a structured type the body can use: `tidy <room>`, `be with <pet>`, `explore`, `make <something>`, `rest`, `tend <thing>`, `project` (its current project), `play`, `stay near <thing>`.
  - **deliberate acts**, as now: speak, tell, make, combine, write, sing a new song, compose, give, take, lay an egg, take a name, teach, ask the book, and so on. These stay **mind-only**. The body never makes, speaks meaningful words, writes, lays eggs or decides anything that belongs to the pet's story.
- The packet tells the mind what the body has been doing since its last thought, in words and compressed: *"since you last thought: you tidied two things onto the shelf, played with the ball, sat with Garry by the window."*
- So each pet's character and story still come from the model. The body only fills the time in between in character.

### 1.3 Habits
- Each pet keeps counts of its activities, places and times (the window at dusk, the stone in the morning, a favourite cushion). Frequent ones become **habits** that score higher.
- Children pick up a little of a parent's habits from watching them, so families get habits ("this family always visits the window at dusk").
- Habits show on the pet's card and in its life record.

### 1.4 Never standing still
- An awake pet with nothing better to do picks a low-key activity (fidget, look around, groom, hum), never nothing.
- "Rest" is a visible pose with breathing and at most 20 s before the body reconsiders, unless the pet is genuinely tired.

---

## 2. Order

**Why:** things pets make and drop pile up wherever they were left (the workshop has five wind chimes in one corner). Tidying is the most natural "always busy" activity a creature has, and rooms that get organised over generations are something to watch.

### 2.1 Clutter is felt
- Each room has a clutter level from loose things (made things and bits on the floor) against storage space. It's felt as a sense line ("this room is a mess", "everything here has its place"), with a small comfort effect for orderly pets and none for messy ones.

### 2.2 Places to keep things
- **Storage kinds:** shelf, chest, basket, wall hook, crate, plus existing furniture with surfaces (tables, benches). Each has capacity and shows what's on it.
- New actions, available to body and mind: `put_away <thing> <storage>`, `take_out <thing>`, `hang <thing> <wall>`.
- Storage can be made (new kinds in the make catalog) and found (the storeroom and workshop start with some).

### 2.3 Homes for things
- A thing put in the same place twice gets a **home**. Tidying returns things to their homes first. Heirlooms get a home near the family's stone or bed.
- Over time the engine names **areas** from what's in them (a sleeping corner where cushions and beds gather, a making bench, a keepsake shelf), shown as a faint floor or wall tint and in hover cards.

### 2.4 The orderly gene
- New temperament gene, **orderly** (0–1), inherited and mutating like the others. Orderly pets tidy often and feel clutter; messy ones don't care and leave things where they fall. A household with both should visibly disagree about the room.

---

## 3. The visitor can turn on the radio

**Why:** Tyler wants to put the radio on for the pets whenever he likes. *(Amended 11 Oct: radio only, no music-by-mood controls.)*

- A **Radio** control in the header: on or off, and what it plays (news, forecast, On this day, or a mix), in the room being viewed.
- Before the pets have found the radio (v3.1 arrival), this is the visitor's own little radio, set down in the room being viewed. Once they've found theirs, the control switches theirs on or off and pets can still switch it themselves.
- Pets perceive it like the found radio: quoted, attributed ("the visitor turned the box on"), logged, cleaned with the same blocklist. Listening can ease boredom; a pet may come over to listen, or wander off.

## 4. Sound

**Why:** Tyler hears the same few sound effects and almost never the pets' voices, and the rooms have gone quiet.

- **Check first:** confirm that a pet's speech plays (babble plus real words) when Tyler watches its room, and whether that broke in v3.2. Pets also speak rarely, so both need fixing.
- **Pets vocalise far more**, through the body layer, in their genome voices: murmurs while working, hums, chirps of interest, yawns, little laughs at play, greetings when kin arrive, grumbles at clutter, gasps at events. Short, frequent, quiet.
- **Every room gets an ambient soundscape** at low volume, from the pack's sounds or made in the browser: water and reeds in the pond room, creaks and ticks in the workshop, wind and birds in the garden, drips in the cellar, wind under the eaves in the attic, a warm hum in the greenhouse, a faint resonance in the music room, near-silence in the storeroom, a clock in the nursery. Weather layers on top (rain under open sky, thunder).
- Room ambience has its own on/off and starts on with sound. The header's existing **Music** button (the pack's background music) stays as it is.
- **Things that make sound must make sound.** When a pet uses a bell, drum, chime, harp, gong, or any noisy or humming thing, the view plays it: in the room being viewed at full volume, muffled through a door, matching what the pets themselves hear (the music room's sounds carry next door). Right now using an instrument is silent in the view even when another pet "hears ringing through the door".

---

## 5. Fixes from the v3.2 deploy

- **Name labels don't fade:** they stay dimmed on every object. They should show for 8 seconds when a room comes into view, on hover, or with the Names button held on, and otherwise be gone.
- **Bigger pets:** draw pets at 1.5–2× their current size relative to the room, so they're the first thing you see.
- **Storm and dusk are murky:** keep the mood but keep pets and objects readable. Darken the edges more than the centre and outline pets in low light.
- **Activity icon:** a small icon above each pet for what its body is doing right now (broom, ball, note, zzz, heart…), alongside the caption for what its mind wants.

---

## 6. Packet and budget

- The new lines in the packet: since-you-last-thought (body activities), clutter, the radio, habits. All of these fit under the existing packet budget, with old cut rules applied first.
- The body layer runs in the engine with no model calls. If the engine's tick time grows noticeably with 5 pets, profile it and fix it before deploy.

---

## 7. Phase B, outlined (not built now)

**Why it's here:** so Phase A's body layer and data files are built to take these without a rewrite. They come from IDEAS.md "Things worth doing".

- **Crafting by discovery:** processes at the workbench (soak, heat, weave, carve, grind) turn materials into new materials and new kinds. Recipes are hidden rules found by trying; families pass them down; a recipe can be lost.
- **Tools that open the world:** trowel (grow food), hammer (mend, build furniture), key (a locked room), ladder (the attic's high shelf).
- **Invented kinds:** a pet invents a new kind of thing, and the art system builds its sprite from a pixel-part library.
- **Building that lasts:** multi-day projects that change a room for good.
- **Work the house needs:** growing food, patching leaks, insulating the cold cellar, mending things.
- **Mysteries the director seeds**, and **games** pets invent and teach.

For Phase A this means: activities, storage kinds and their effects live in data files; the body can be given new activities that require a tool or a place; and the mind's focus types can grow.

---

## 8. Verifying and deploying

1. **Stub runs:** the body layer with stub minds over several world days. Check that activity variety, stillness and passive-share hold, that tidying converges (rooms get tidier, not shuffled forever), that no activity loops, and that the tick time is fine.
2. **Copy of the live house, real model:** a few world days in turbo. Measure every number in §0 per pet per world day, plus model calls per hour (same or lower) and nuzzle share (still low).
3. **Fresh-eyes watch:** a reviewer that hasn't seen the build watches recordings or replays of three rooms for 5 minutes each and writes what each pet did and why. If they can't, fix and repeat once.
4. **Sound check:** confirm speech, vocalisations and room ambience all play, from a recorded audio log or the voice lab, since nobody can listen from the engine.
5. **Deploy:** back up `data/`, one restart, the family carries on.
6. **Tell Tyler** it's live, with the §0 numbers from the copy run, and ask him to watch for ten minutes.

## 9. Not in v3.3

Phase B (§7), evolving bodies, training while they sleep, the experiments in IDEAS.md.
