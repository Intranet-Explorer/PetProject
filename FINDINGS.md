# Findings

What has been learned, newest first. v3 (a family in a house) is at the top: written on 10 October 2026 after
the first showcase run and rewritten on 11 October after the third. The v1 and v2 findings below it were
written on 8 and 9 October and are left as they were. The three runs are told in
[showcase/first-run.md](showcase/first-run.md), [second-run.md](showcase/second-run.md) and
[third-run.md](showcase/third-run.md); none of them passed SPEC-v3 §12's bar, and a fourth was running as
this was written. [NOTES.md](NOTES.md) has the account of each v1 and v2 life as it happened, and
[DECISIONS.md](DECISIONS.md) lists every place the build reads a spec its own way and every change made
between runs.

The project is small creatures in a browser house, each driven by a local language model (`qwen3.8:27b-mlx`
through Ollama, on one Mac). v1 ([SPEC.md](SPEC.md)) was a rule-discovery experiment with a scripted twin as a
control. v2 ([SPEC-v2.md](SPEC-v2.md)) made one creature that makes its own things and grows by them. v3
([SPEC-v3.md](SPEC-v3.md)) made it a family: pets are born, grow old and die, and leave their children a
body, a temperament, a message and a few things, in a house of nine rooms.

## v3: the short version

From four real-model runs in turbo time: a smoke run of 26 world days and four generations on 9 October, and
three attempts at the showcase on 10 and 11 October (30, 28.5 and 31.1 world days; 7, 7 and 8 pets; 1,259,
1,288 and 1,512 thoughts; 4,632 model calls, none failed). Every founder hatched with the same message, the
last v2 pet's. The house's rules were changed between runs, and under the second while it ran. Every run used
the same seed, so the doors, the schedule of events and the temperament drawn for each birth in order were
the same each time: what differed between families was the rules and the model's words. Where a thing was
seen in all three it says so; the rest is from one family. A fourth run of eleven days is now the living
house; [SHOWCASE.md](SHOWCASE.md) reports all four, with a second reader's corrections.

1. **The same message made three different families.** "Combine before you create … Make the shape. Unmake
   it. Make another." The first founder took it as a job and made 71 things. The second did it for six days,
   wrote "All making is a drain … the answer is not a better kind of making but the choice to stay", and named
   its egg Stay. The third made lights for three days and then spent its life on a question it wrote on a
   thing it made: "To test if sweet persists in softness."
2. **A message from a parent is taken as a job, in all three.** In the first run 25 first-day thoughts cite a
   particular sentence of the message. Stay was told "Lay your own egg and let it be enough" and its first
   project began "Lay my own egg and let it be enough." A pet told "Keep the seed, feather, and wood" gathered those three with cloth, moss and pebble lying beside
   them. Twins hatched ten ticks apart with different messages lived differently from their first day.
3. **Telling a pet how it feels, and never a number, ended most of the meter-talk, and one word brought some
   back.** The last v2 pet talked mechanics in 43.0% of its thoughts. Every pet of the first run is under
   5%. Two pets of the second (14.0%, 10.5%) and one of the third (11.3%) are over 10%, all on "cost": pets
   choosing by what a deed costs or returns, in felt words in place of numbers.
4. **"Cost" is a rare seed and a strong amplifier.** The seeds: the v2 pet's "it costs less than either
   alone", in every founder's message; and a line of the journal, "apart from that, while it lasted you grew
   a little less at ease", which was read as the price of the deed beside it. The amplifier: a pet rereads
   its beliefs in every prompt. Of 165 nights in the second and third runs, 60 began with no "cost" belief in
   front of the pet and 2 of those wrote one; 105 began with one and 53 wrote it again (a second reader,
   counting more simply, got 7 of 76 and 41 of 94: the same direction, weaker). The second family kept the
   same books under a word the measure does not count: "drain" is in 43 to 58% of three pets' thoughts. Replaying the two
   nights the word was first coined on: 6 of 24 produced a "cost" belief with the old journal line and 1 of
   24 with "not from that but from the hour and the place".
5. **A family's words are the founder's, in all three.** Counting only words the engine never says and
   another family did not use: the founder coined about four in five of the ones it used (81%, 83%, 78%) and
   the fourth generation inherited most of theirs (77%; 60%; 75% and 77%). No word coined after the second
   generation was used by a descendant in any run (the later pets had few descendants, and young ones, to
   use them). What survives differs: the v2 pet's "pulse" is in 47 to 70% of the thoughts of each of the
   first family's first five pets (not counting it in a name) and 7% of the third founder's; "below thirty" was copied from message to message as far as the
   first family's third generation, in no thought of any of them, and is in nothing a pet of the other two
   wrote.
6. **A told belief was corrected when the pet's own doing contradicted it, and not otherwise.** In the first
   run Pulse Shard spent two days making things as told, got "nothing came of it" from each, and rewrote "the
   pulse asking for a new shape" as "the direction, not a new shape"; things made per life then fell from 71
   to 33, 24 and 12. In the third the founder held "it costs less than either alone" on day 0.6 and "costs
   more than either alone, but it opens a small interest that the parts did not have" on day 1.6, after a day
   of making, and both its children kept the corrected form for life.
7. **Nobody who was told about the lamp found out the lamp.** "The lamp keeps the dark from hurting" is false
   in this house: a light left on at night is harsh, and the pets are told so. No pet that was given the
   claim wrote a belief or a message against it, in four families. The first founder passed it on whole; its
   child dropped the sentence and went on acting on it. The second founder never took it up. The third kept
   the words and moved them: it made a soft thing, named it Cloth Wax Lamp, and wrote "resting in it holds
   the dark from hurting". The third and fourth founders each thought "the harsh light" and "keeps the dark
   from hurting" in one and the same thought. One pet did switch a lamp off at night because the light was
   harsh, and wrote that it helped: a grandchild in the third family who had never been told the claim. This
   is v2's finding again: the blocker is attribution, and what blocks it is having been told.
8. **What cannot be tested lasts longest.** "The storm chime is the brother's voice", said by one pet to its
   child, was a belief of the third generation within the hour, was at the head of the message to the fourth,
   and was written into the fifth's egg. The first family's was "You are new, but the pulse is old."
9. **A thing can carry what a message does not.** The third founder's question was in none of its messages.
   Its grandchild read it on the label of a thing the founder had made, on the day it hatched, took "my
   grandmother's question, still open" as its project for ten days, and put it in two more eggs.
10. **What the house says wrongly becomes what the family knows.** A gift to a creature was refused for a
    reason that was not the reason, and one line of the third family built "things made in the attic are
    rooted" on it. In the first run a stale line said the cellar's cold "gets into you" after its rule had
    drifted to mild; that family held that "the cold is the rest", which by the numbers was true of their
    nights there.
11. **A need that is filled by deeds and emptied at a fixed rate has no middle.** A pet that earns a little
    more than the rate is always full and one that earns a little less is always empty: curiosity sat at the
    top in the first run (95 or more for 48 to 90% of steps) and at the bottom in the second (by day 26 every
    adult at 0 to 5). A rate in proportion to the level gives a middle, and then the rate decides where everyone sits:
    in the third run every pet read "interested" or "fascinated" in 76 to 100% of its prompts and "bored" in
    7 of 1,515, and the pet that used one door in 8.8 days was about as interested as the one that found seven rooms.
12. **A creed that costs nothing is kept.** Stay sat in one room for three days at energy 96, comfort 98,
    company 100 and curiosity 27, saying "staying is the final making". The founder went through the door
    it had sat beside only after boredom was made to wear on comfort, and wrote "following a clean pull can
    also rest you". Stay carried that sentence in its own last words and never acted on it.
13. **Left to it, two pets nuzzle and say nothing, and talk thins down a line.** The smoke run had 359 nuzzles
    and 8 things said. With closeness wearing off and an offer no longer an alarm, the first run had 130
    things said to another pet and 62 said in answer, and the third 131 and 63, with no visitor present for
    any thought of either. In the third, things said per pet, eldest first: 17, 47, 29, 31, 17, 11, 2.
14. **The dead crowd out the living.** Rooms hold ten made things and fill with what the dead made; "make"
    was missing from 40 to 74% of what four of the third run's later pets were offered. Nobody made as much
    as its founder in any run (things made by generation: 71, 33, 24, 12; 40, 9 and 22, 14 and 7, 4; 56, 36
    and 21, 24 and 23, 25 and 10; the last of each were still alive when the run stopped).
15. **The house shrank down a line in one family and not in another.** Rooms entered in the first run: 7, 8,
    4, 4, 3, and the ninth room never found. In the third: 4, 6, 8, 9, 6, 2, 7, and all nine found. Boredom
    was made to cost something between the two (part 11 of DECISIONS.md); whether that is why was not tested.
16. **Doctrine explains experience away.** One pet of the first run noticed a thing "leaves me less at ease at
    night" and later revised that to "the less ease is the pulse asking for movement". Its family's
    predictions were 54% right for the founder and 30 to 37% for every pet after it.
17. **The engine's own words become beliefs.** The journal line that was reworded to stop "cost" says a change
    came "not from that but from the hour and the place". Within four nights the fourth founder held, as its
    own: "the unease I feel at night is not from [the door] but from the hour and the room growing familiar."
18. **I graded my own runs too kindly, each time.** A second reader, grading from the logs before reading my
    account, disagreed on two criteria of the first run. On the third it showed that three things I had
    written about the second run's fixes were not so (pets were still miserable for 27 to 41% of their steps
    after the fix that "stopped" it), and that the lamp had been moved, not corrected as I had it. On the page that
    reports all four it found, among other things, the one pet that did switch the lamp off, which I had
    missed, and that "the lineage changed" was the same seeded draw replayed in every run.

## v3: the engine

- **Turbo time works.** The world waits while any model call is in flight and otherwise runs without
  sleeping. Thirty world days with up to four pets awake took 6 h 56 min, and 31.1 took 8 h. A waking thought
  took about 16 s (median 13 to 17 s by pet), a night's thinking about 55 s, with thinking set low and 3,000
  tokens.
- **Two calls at once is no faster** on this Mac (7.4 against 7.3 ms a character with
  `OLLAMA_NUM_PARALLEL=2`), so calls are made one at a time and Ollama is left at its default.
- **The call budget held**: 136 calls in the first run's last world hour, with four pets, against a budget
  of 150.
- **The constrained output shape held**: in the first run 3,012 steps, 1 to 5% of each pet's not possible,
  and no malformed reply in any run.
- **What is stored was shorter than what the model was told it could write.** 82 of the third run's 274
  beliefs ended cut off, and a pet rereads its beliefs at every thought.
- **Third-person self-talk was the model's own.** The smoke pets sometimes wrote of themselves as "the
  character" or "the agent". Neither word was in any of the 812 prompts checked.
- **One pet's error used to freeze the house** and a made thing could take a fixture's name and replace it.
  Both were found by a fresh reader of the code, not by a run.
- **A run whose rules change under it cannot be judged**, and neither can a generation that hatches as the
  run stops. The second run had four numbers changed while it ran; the third stopped with its fifth
  generation 23 ticks old. The rule for when a run stops is now written down before it starts.

## v3: what has not been verified

- The real clock. Every run was turbo.
- Nobody has listened to a v3 voice or clicked a v3 visitor control. Both were driven by scripts and looked
  at in a headless browser.
- A model-driven pet has never died of neglect and never met the visitor.
- Real weather through the window (§6.6) is built and switched off.
- Whether the changes made after the third run do what they are for: interest that can run low, one rule
  for company, the journal line reworded, three false statements put right. The fourth run is the test.
- The vocabulary baseline (what counts as a word "another family did not use") is one smoke run.

## v3: open questions

- Whether any family finds the lamp rule, and what would make a told belief get weighed against a sense.
- Whether a founder that did not inherit "costs less than either alone" would ever count costs.
- Whether a child given less of its parent's words at first would still coin its own by generation 4.
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
| `data.showcase-1` | v3 | turbo | 6.9 h | 30 world days, 7 pets, 5 generations; did not pass the bar; showcase/first-run.md |

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

## v3.3: alive (11 October 2026)

What was measured before the body layer went into the live house, on copies of that house with the real
model (`engine/alive.py`; everything in watching time on the live clock, where a tick is four seconds):

| | the bar (SPEC-v3.3 §0) | turbo copy, one full world day on the deployed code | a second copy at live pace, 11 minutes |
|---|---|---|---|
| different things in any 5 minutes, the worst window of the worst pet | at least 5 | 7 (the four pets: 11, 11, 10, 7) | 12 |
| longest on one spot doing one thing, outside a resting pose | 30 s | 24 s | 24 s |
| resting, looking and watching, share of waking time | under 25% | 1% to 23% | 6% to 19% |
| thoughts asked of the model, per pet per live hour | no more than before | 9 to 14 (the live house before: 16 to 21) | n/a (too short) |
| nuzzle and accept, share of decided steps | (v3.2: 9 to 13% of thoughts) | about 13 of 84 | about 1 of 18 |

The world day before that, on code that differed only in the last two additions (getting ready to make, the
radio speaking at once), gave 8 to 10 things, 24 s, 3% to 16% and 13 to 15 thoughts an hour. Over the
whole of the copy runs (407 calls to the model) none failed and the engine logged no error.

**Corrected 12 October 2026, from the live house's first eleven world days on v3.3** (38 pet-days, all inside the
bars: 8 to 13 things, 20 to 28 s, 5% to 23%):

- Leaning was first reported here as "0 of 84". That was the measure reading the wrong column of the log. It
  did not stop: on the live house, nuzzle and accept were 137 of 1,193 decided steps (11.5%; 163 of 1,294,
  12.6%, over the nine days before). Counting what the bodies do as well, it is 137 of about 6,000 things done.
- Thoughts did not fall as the copy suggested: 19.2 per pet per world day against 18.2 before (full days
  only). Each was quicker, 16.6 s against 29.2 s, so the model's time per pet fell by about 40%.

- **The pets think as often as they did.** The body asks nothing of the model; a thought brought forward
  because everything is laid out to make something is paid back by the next one.
- **What a thought expects is now scored over the whole time until the next thought**, body and all. The
  share judged right did not move: 16 of 54 on the copy's last world day and a bit, 18 of 58 in the live
  house before.
- **Of ten thoughts brought forward with bits laid out, about half made something at once.** The others did
  something else with a mind that was plainly on making; that is the pet's to decide.
- **What two strangers could say after watching three rooms for five minutes** is in DECISIONS.md, Part 15:
  what each pet was doing, mostly; why, for about half the pets; and a room with nobody in it is still an
  empty room.

## Tidying a person can see (12 October 2026)

Measured on a copy of the live house taken that morning (day 32), lived on in turbo with the real model while
the live house used the same model. "Lying about" is what a person sees: made things on the floor that are
not put away, hung up or part of a corner, and loose bits. The rules are in DECISIONS.md.

| room | start | first cut, a world day | bits fit, anyone tidies, a day | final rules, one waking day |
|---|---|---|---|---|
| storeroom | 16 | 18 | 17 | 10 → 0 |
| music room | 10 | 8 | 1-3 | 4 → 0 |
| cellar | 5 | 0 | 0-1 | 0-2 |
| pond room | 19 | 19 | 19 | 19 → 1 |
| nursery | 10 | 0 | 0 | 0 |
| greenhouse | 11 | 6 | 6 | 6-7 |
| workshop | 12 | 12 | 12 | 10 |
| attic | 5 | 5 | 2 | 0 |
| garden | 8 | 8 | 8 | 5 |

- **Storage and the new count were enough for the rooms the pets live in, and for no others.** With a chest,
  a shelf or a basket in every room, the nursery, the cellar and then the music room went to nothing or
  nearly and stayed there. The five rooms nobody walked into did not change in two world days.
- **Telling the minds moved nobody.** A door that says "to the storeroom, which is a mess" stood beside pets
  for a world day and none went through it to tidy. What the minds were about, sampled through a waking day:
  resting 34%, being with someone 22%, tending 12%, a project 12%, making 11%, playing or exploring 5%,
  tidying under 1%.
- **Letting a known mess draw the body did it.** Without the cap, eight waking hours took the storeroom from
  18 to 11. With everything in (one trip a day, crates, fading bits), one waking day took the storeroom from
  10 to 0, the pond room from 19 to 1 and the music room from 4 to 0. Three of the four pets made their one
  trip that day; the bodies put 33 things away.
- **Still as they were after that day:** the workshop (10), the greenhouse (6-7, "a few things lie about",
  which draws nobody) and the garden (5). With stub minds given the real minds' mix of focuses and never
  choosing to go anywhere, two world days took the workshop from 10 to 7 and held the storeroom at 0-1 and
  the pond room at 3-5.
- **§0 held throughout**, on the final rules: 8 to 10 different things in every five minutes, still 20 to
  28 s, passive 13 to 18%; 66 thoughts, none failed. One slice on an earlier build read 30% passive: a
  hatchling's last eight waking minutes of a day, mostly napping.
- **Storage made by a pet: 0 of 115 things before, 3 of 37 after**, each in a messy room with nowhere left,
  unasked: a box in the workshop, a basket in the storeroom, a basket in the music room, all by the hatchling
  Quiet Lean.
- **Nineteen old things wore out** on the copy in four world days, most while the storeroom had ten places.
  It now has twenty.

Not measured: fading bits over more than two world days; the live house itself, which got all this at once.

The cost of measuring this way: five of the live house's thoughts timed out while the copy shared its model
(Tyler's count).

**On the live house the same day:** in its first waking day on these rules the storeroom went from 17 lying about
to 0, the music room 15 to 1, the pond room 20 to 4 and the workshop 12 to 4; the nursery (15 to 14), greenhouse,
cellar, attic and garden did not move. And 19 made things wore out, three of them living pets' and five taken
down off walls: the storeroom filled within hours, and after that every old thing sent to it cost one. The copy
had shown 19 wearing out in four world days and I reported it as a count, not as a problem. The rule was
replaced that afternoon (DECISIONS.md, "Keepsake boxes") and all 19 were put back.
