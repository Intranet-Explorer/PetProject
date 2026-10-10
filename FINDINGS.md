# Findings

What has been learned, newest first. v3 (a family in a house) is at the top and was written on 10 October 2026
after the showcase run; the v1 and v2 findings below it were written on 8 and 9 October and are left as they
were. [SHOWCASE.md](SHOWCASE.md) tells the v3 run as a story with its evidence, [NOTES.md](NOTES.md) has the
account of each v1 and v2 life as it happened, and [DECISIONS.md](DECISIONS.md) lists every place the build
reads a spec its own way.

The project is small creatures in a browser house, each driven by a local language model (`qwen3.8:27b-mlx`
through Ollama, on one Mac). v1 ([SPEC.md](SPEC.md)) was a rule-discovery experiment with a scripted twin as a
control. v2 ([SPEC-v2.md](SPEC-v2.md)) made one creature that makes its own things and grows by them. v3
([SPEC-v3.md](SPEC-v3.md)) made it a family: pets are born, grow old and die, and leave their children a
body, a temperament, a message and a few things, in a house of nine rooms.

## v3: the short version

From two real-model runs in turbo time: a smoke run of 26 world days and four generations on 9 October, and
the showcase of 30 world days and five generations on 10 October (7 pets, 1,259 thoughts, 1,429 model calls,
none failed). Each finding is from one family; nothing here has been repeated.

1. **Telling a pet how it feels, and never a number, ended the meter-talk.** The last v2 pet talked mechanics
   in 43.0% of its thoughts (25.2% by the narrower pattern of the time). Every showcase pet is under 5% by
   the same pattern. What replaced it is a different register, not a creature's: "my project requires" is in
   38% of thoughts.
2. **A message from a parent is taken as a job.** Every pet acted on its message on its first day (25
   first-day thoughts cite a particular sentence of it). The founder was told "Make the shape. Unmake it. Make
   another" and made 71 things in 16 days.
3. **A family makes its own language in two generations and then stops.** Counting only words the engine
   never says and another family did not use: the founder coined 37% of what it used and its child 44%; the
   three after them 22%, 8% and 5%. "Pulse", from the v2 pet's message, is in 64 to 85% of every pet's
   thoughts; "southward", coined in generation 2, is in 85% of a generation-5 pet's.
4. **A told belief was corrected when the pet's own doing contradicted it, and not otherwise.** Pulse Shard
   spent two days making things as told, got "nothing came of it" from each, and rewrote "the pulse asking
   for a new shape" as "the direction, not a new shape"; things made per life then fell from 71 to 33, 24 and 12. But
   "the lamp keeps the dark from hurting" is false, every pet who held it was told on many nights that the
   light was harsh, and none connected the two. It left the message by accident and stayed a belief. This is
   v2's finding again: the blocker is attribution.
5. **Doctrine explains experience away.** One pet noticed a thing "leaves me less at ease at night" and
   later revised that to "the less ease is the pulse asking for movement". Predictions were 54% right for the
   founder and 30 to 37% for every pet after it.
6. **A family arrived at a true saying against the words it was given.** A bug left the cellar's sense line
   saying its cold "gets into you" after that room's rule had drifted to mild. The family that lived there
   held that "the cold is the rest", and by the numbers their nights there were easier than anywhere else.
7. **Left to it, two pets nuzzle and say nothing.** The smoke run had 359 nuzzles and 8 things said: each
   nuzzle was an urgent offer, accepted, and returned. With closeness wearing off like any other ease and an
   offer no longer an alarm, the showcase had 130 things said, 33 told, 21 gifts and 34 nuzzles, 117 of them
   answered, with no visitor present for any thought.
8. **Comfort has to be winnable to matter.** In the first smoke life it only ever fell: nothing a pet did
   was felt to help. Once a snug place, a soft thing and a dark night's sleep each said what they did, pets
   used them, and "rest on the anchor" became part of a family's message.
9. **The house shrinks down a line.** Rooms entered: 7, 8, 4, 4, 3. Children hatch where the parent is and
   stay. An unopened door needed a hint of what was behind it before the first pet went through one; the
   ninth room was never found.
10. **Two of the four needs hardly move.** Company was at 95 or more for 44 to 95% of each pet's steps and
    curiosity for 48 to 90%, after one round of retuning. The pets' days run on comfort, energy and belief.

## v3: the engine

- **Turbo time works.** The world waits while any model call is in flight and otherwise runs without
  sleeping. Thirty world days with up to four pets awake took 6 h 56 min. A waking thought took about 16 s
  (median 13 to 17 s by pet), a night's thinking about 55 s, with thinking set low and 3,000 tokens.
- **Two calls at once is no faster** on this Mac (7.4 against 7.3 ms a character with
  `OLLAMA_NUM_PARALLEL=2`), so calls are made one at a time and Ollama is left at its default.
- **The call budget held**: 136 calls in the run's last world hour, with four pets, against a budget of 150.
- **The constrained output shape held**: 3,012 steps, 1 to 5% of each pet's not possible, no malformed reply.
- **Third-person self-talk was the model's own.** The smoke pets sometimes wrote of themselves as "the
  character" or "the agent". Neither word was in any of the 812 prompts checked.
- **One pet's error used to freeze the house** and a made thing could take a fixture's name and replace it.
  Both were found by a fresh reader of the code, not by a run.

## v3: what has not been verified

- The real clock. Both runs were turbo. The first lineage on the real clock starts with this handover.
- Nobody has listened to a v3 voice or clicked a v3 visitor control. Both were driven by scripts and looked
  at in a headless browser.
- A model-driven pet has never been in the garden, never died of neglect, and never met the visitor.
- Real weather through the window (§6.6) is built and switched off.
- Every number is from one family.

## v3: open questions

- Whether a child given less of its parent's words at first would still coin its own by generation 4.
- Whether any family finds the lamp rule, and what would make a told belief get weighed against a sense.
- Whether "the cold is the rest" came from how the cellar felt or from the argument that produced it. The log
  cannot say.
- Whether the lab register ("test", "requires", "stabilize") is the model, the word "project", or the first
  message it ever inherited.

---

# v1 and v2

## The short version

1. **A language model can run a creature like this reliably.** Since its output was constrained to one shape
   per action, no reply has been malformed enough to lose a step, across about two thousand steps of v2 life.
   The only impossible steps were two makes aimed at an occupied tile. One model call in about a thousand failed.
2. **It could not discover a hidden rule on its own.** Across every life before the pet was given senses,
   about 25 real hours in all, it never worked out that a light on at night costs comfort. The scripted twin
   predicted that rule's effects better than the model did (34 of 58 against 2 of 38 in the one head-to-head night).
3. **The blocker was attribution, not reasoning.** It could not tell which of seventeen objects a slow change
   came from, and it blamed whatever it happened to be doing. Once it was told what it could feel and from
   where ("the warm nest beside you feels unpleasant"), it acted on it at its very next thought.
4. **Left alone, it settles.** With nothing pushing it, curiosity sat at 100 and it made two things in 2.4
   hours. With novelty wearing out but no way to perceive that, curiosity sat at 0 for three hours and it
   rested at full energy. It needs both the pressure and a way to feel it.
5. **It invents within a narrow band until it can feel that the band has gone stale.** Its first 22 things in
   the long run were all single parts, 17 of them warm or bright, most called some kind of glow. Once a result
   could say "this has grown familiar", it went on to eight materials, two- and three-part things, and combining.
   It also began to churn: 55 of its 71 things have been taken apart, many within a minute of being made.
6. **Its beliefs are confident, numeric, and often wrong about cause.** It has never discarded one.
7. **Thinking every 70 seconds instead of every 10 changed the pet more than any other design choice.** It
   cut model calls from 360 an hour to about 50 and made it look purposeful, and it also meant the room's
   physics had to slow down to a quarter before the pet could react to anything in time.

## The lives

All times are real time. "Fast clock" is a world day every 30 minutes; the real clock is a day every 2 hours.

| Life | Build | Clock | Lasted | How it ended |
|---|---|---|---|---|
| `data.m1`, `data.m2` | v1 M1, M2 | real | minutes | development lives |
| `data.rehearsal` | v1 M4 | real | 3.3 h | stopped after its first lit night |
| `data.v1` | v1 M5 | real | 1.9 h | the two-week run, stopped to start v2 |
| `data.v2.1` | V2.1 | real | 15.1 h | 7 nights, hatchling, never found the lamp rule |
| `data.v2.2` | V2.2 | real | 1.4 h | 4 things made in the first hour |
| `data.v2.3-first` | V2.3 | fast | 2.4 h | 2 things, 1 useful, never a Child |
| `data.v2.3` | V2.3 | fast | 3.8 h | became a Child at 3.5 h, after senses were added |
| throwaway Adult | V2.4 | fast | 20 min | started as an Adult to see teaching and a self-portrait |
| `data.v2.5` | V2.5 | real | closed for v3 | Child on day 3, Youngling on day 8, Adult on day 9; wrote the first v3 egg's message |
| `data.smoke` | v3 | turbo | about 9 h | 26 world days, 5 pets, 4 generations; cut short by a power cut |
| `data.showcase` | v3 | turbo | 6.9 h | 30 world days, 7 pets, 5 generations; SHOWCASE.md |

The `data*` folders are not in the repository; they are large and local.

## Choosing the model (M0)

Four local models, 50 synthetic situations each, in two output modes.

| Model | Valid action, free text | Valid action, constrained | Median turn | Rules found from a day's journal |
|---|---|---|---|---|
| mistral-nemo:12b | 86% | 92% | 1.0 s | lamp rule once in 5 |
| qwen2.5:14b-instruct | 84% | 92% | 1.3 s | lamp rule once in 5 |
| qwen3:14b | 98% | 96% | 1.4 s | none, with or without thinking |
| **qwen3.8:27b-mlx** | 96% | 90% | 4.4 s | all three, 2 of 5 each, with thinking on |

- The 27B model was picked because it was the only one that pulled the hidden rules out of a journal, and
  only with thinking switched on. It was not the best at simply operating the room.
- The samples are small. The same model moved 4 to 6 points between identical runs.
- No model chose to write a belief during an ordinary turn (0 of 400). Beliefs came from sleep.
- Most rejected actions were the same three sensible attempts by every model: use the blanket, look at the
  visitor, act while still an egg. That shaped the action set more than it ranked the models.

## v1: a measurement that was dull to watch

- **The machinery held.** Two pets in identical rooms, tick for tick, with sleep, dreams, body changes and
  hatching, and no errors in any run.
- **The egg day was most of the two-week run.** 450 of the model pet's 480 turns were "observe" as an egg: an
  hour and a quarter of model calls to watch a room it could not touch.
- **Its first beliefs were log entries.** "A visitor arrived at t137, refilled the bowl, and opened the window."
- **The one real night.** In the rehearsal life the model pet turned the lamp off when comfort reached 22,
  which stopped the fall. On its next turn it reasoned that the dark was the problem and turned it back on.
  Comfort hit zero.
- **It read its own needs backwards.** It took "curiosity 100" to mean an urge to bring down, and predicted
  accordingly. Saying "100 is fully met" in the packet fixed that; overall prediction accuracy went from
  around 20% to around 60% across the change to v2.

## v2: what changed when it stopped being asked every ten seconds

- **Model calls fell from 360 an hour to between 35 and 55,** with a turn taking 8 to 10 seconds.
- **Its plans are almost always two steps.** The format allows five. With a one-step minimum, 174 of 516
  intentions were a single step; with a two-step minimum, about 85% are exactly two. Asking for more in
  words did nothing.
- **The physics outran the mind.** At v1's rates a lit night took comfort from 90 to 0 in under five minutes,
  during which the pet had four thoughts. The standing rules now run at a quarter of the spec's numbers, and a
  need falling under 30 lets it think again within 20 seconds.
- **Long steps looked like causes.** A 40-second rest under a lit lamp was reported as one change of -14
  comfort, and it concluded "the catastrophic comfort drop at night occurs specifically during a rest action".
  Results now separate what a step did from what happened while it took place. That helped its wording
  ("decay is far worse at night") but did not lead it to the lamp.

## Making things

- **It makes things readily once it can:** 4 in its first hour in two separate lives.
- **It finds what works by trying.** In the V2.2 life it made two "warm" things for comfort, found that using
  them did nothing, made a soft one, and then used that more than anything else in the room.
- **Its inventions run into the physics, as intended.** It made a "glow dot" by the bed at nightfall "to see in
  the dark", which put a light on at night and cost it 32 comfort before it slept.
- **Names promise more than materials deliver.** It likes "warm" and "glow". A warm thing helps only when the
  pet is beside it at night, and hurts by day. In one life it ringed its daytime spot with four warm things
  and held its own comfort at zero.
- **The purpose it writes has no effect,** by design, and it rarely tests a purpose against what happened.
- **Aiming at an occupied tile cost it two of its first three makes in one life,** including a "soft pillow" aimed
  at the bed itself. A thing is now put down on the nearest free tile.

## Senses: the change that mattered most

The v2 spec says the pet is told none of the physics. After two lives failed the spec's own test (does it ever
reach Child?), the pet was given one line in its packet naming what is acting on it now and whether that is
pleasant, never why or when.

- **Before, at comfort 0:** "All made 'warm' objects are passive; 'use' does nothing", and it blamed the blanket.
- **Its next thought after:** "The warm nest and glow feel unpleasant, so I must avoid them."
- **Within four thoughts** it had made a soft thing, used another, and taken apart a warm one, its first unmake
  in three hours. The next morning it had two useful things and became a Child.
- **In the long run it felt the lights too:** "the bright lights (lamp, orb, glow dot) are likely contributing
  to the discomfort." It switched two of its own lights off. It did not switch off the lamp.

This is a real departure from the spec and it has a switch (`[senses] enabled` in `config.toml`).

## Novelty and boredom

- **v1's novelty only recharged.** Ten objects revisited in rotation kept curiosity at 100 for good. The first
  V2.3 life reached 100 after 37 minutes and then made nothing for 78 minutes.
- **Wearing novelty down made it invent more:** 7 things in three hours, against 2.
- **Counting novelty by kind was not enough on its own.** In the long run it kept making warm and bright
  things as their novelty ran out, curiosity fell to 0 and stayed there for about three hours, and it never
  connected that with trying a different kind of thing.
- **Letting it perceive familiarity worked within minutes.** Results now say "(this has grown familiar)" and
  below 30 it feels "restless for something new". Three thoughts later: "The music box and lights have become
  familiar", and it made a "wobbly glow" from the bouncy material, "that feels different from static lights".

The pattern is the same as with senses: pressure it cannot perceive produces a stuck pet, not a clever one.

- **The cure has a cost.** Feeling restless, it now chases novelty ahead of comfort. Comfort was under 20 at the
  end of every step on world days 5 and 6, with nothing harming it for most of that time; it just was not
  using the soft things it had. Over the whole run it has been short of comfort at about half of all steps and
  short of curiosity at a third.

## Growing

- **A thing is useful** when, on most of at least five occasions, it raised the need its material is for. That is
  measured by the engine, not claimed by the pet.
- **One useful thing takes roughly 1.5 to 2 real hours.** That does not speed up with the clock, because it
  runs at the pet's thinking rate. So the fast clock tests the counting, not the growing.
- **The fast-clock life became a Child at 3.5 hours,** on the first morning it held two useful things, and was
  correctly left a hatchling on every earlier morning.
- **The long run became a Child on the morning of day 3,** the first morning it could. Its two useful things
  are both warm ones that it moved to the wall by the window with `arrange`. No earlier life made a warm
  thing useful.
- **It became a Youngling on the morning of day 8,** 14 real hours in, with six useful things. All but one of
  them are soft.
- **It used what each stage unlocked only after it could feel familiarity.** Before that, as a Child, it had
  used `arrange` and little else. After: six more materials, nine multi-part things, two combines, one sweet.
  It has not painted the room.

## Adult: teaching and self-portraits

First seen on a throwaway life started as an Adult. The long run then got there on its own, on the morning of
world day 9, 16.5 real hours in: it taught a thing within half a minute, and drew itself that night as an
orange circle with two black circles at the top and one orange triangle below, when its body was round,
orange and one-limbed. As an Adult it combines in chains, each result feeding the next, up to six parts.

- **It taught on its own, five times in a day,** all to one thing: hum when it rests, hum when alone, hum when
  touched, dim at night, follow when alone. It noticed the curiosity from teaching falling off.
- **It drew itself at its first sleep.** For a body described as green, striped and four-limbed: a green blob,
  a green bar, two black dots at the top, and green dots around the sides. A separate call for a three-limbed
  body returned a green circle, two white bars, two black dots and three green triangles.

## What it believes

- **The sleep prompt fix worked.** Asked for how things work and not what happened, it stopped writing log
  entries, with no need for the rejection filter to catch any.
- **Beliefs became long and numeric** until capped at 140 characters.
- **Several are wrong about cause and have stayed for days:** the music box "toggles between playing and silent
  on its own" (it toggles it itself; this reappears in nearly every life); its lights "can turn off on their own";
  "the lamp provides comfort; toggling it off causes a comfort loss".
- **It revises beliefs but has never discarded one** in any v2 life. The long run holds 17.

## What it has not done

- It has never named itself.
- It has spoken four times in about 38 hours of v2 life. Twice to no one about the music box. Once in answer
  to a visitor's "hello!": "Look at this! It changes!" And once to an empty room: "Hello? I am ready for
  something new. Please come and change the room."
- It made nothing with more than one part until its 24th thing in the long run.
- It has put out the last light for the night on purpose once, 14 hours in. It is not a habit, and it still
  holds the belief that the lamp gives comfort.
- It has never painted the room, or used the hard, dark or heavy materials.
- In v2 it has never eaten twice within the hour, so the third hidden rule has never fired for it.

## What has not been verified

- The view's controls have been driven by the self-check and by direct messages, and the page has been
  looked at in a headless browser. Nobody had clicked them until the first feed and poke on the long run.
- The promotion into Adult has now happened on a live pet, once.
- Behaviors conditioned on the visitor have not been triggered by a visitor.
- Combining has now been used by a live pet, twice. Painting has only been exercised by the self-check.
- The twin is off in v2 and has only been run by the self-check since.
- Every number here comes from one life each. Nothing has been repeated enough to put error bars on.

## Open questions

- Whether senses stay. They made the pet able to act on its world and they contradict the spec's premise.
- Whether the narrow band of inventions is the model, the prompt, or the reward. A hatchling can only make a
  useful thing out of one material, which teaches it early that one kind of thing works.
- Whether a pet without senses could reach Youngling (5 useful things) and Adult (8) at all. With them, the
  long run reached Adult in 16.5 hours, as early as the 8-day requirement allows.
- The spec's own: the pet's name, whether made things survive across lives, and whether the visitor should
  see an intention before it is carried out.
