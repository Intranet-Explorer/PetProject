# Notes

What was seen at the end of each milestone. Newest at the bottom.

## V2.0: the v1 run, stopped and archived (7 Oct 2026)

The v1 two-week run was stopped after 1 h 55 min, at tick 690 (06:58 on world day 2), and archived to
`data.v1/`. The earlier dev lives are in `data.m1/`, `data.m2/` and `data.rehearsal/`.

- **It ran cleanly.** One start, no errors in the log, no failed model calls, no rejected actions in
  480 turns per pet. Both eggs slept, dreamed, changed body and hatched at tick 661, in step.
- **The egg day was most of it.** 450 of the model pet's 480 turns were `observe` as an egg: an hour and a
  quarter of model calls to watch a room it could not touch. Its prediction accuracy over that stretch was 17%,
  because it kept predicting changes a dormant egg cannot have.
- **Its first beliefs were log entries.** After night 1 it wrote "A visitor arrived at t137, refilled the bowl,
  and opened the window from closed to open", "The window is open; it was closed until the visitor opened it at
  t137" and "The agent has remained stationary at (5,3) for the entire journal". All true, none about how
  anything works.
- **As a hatchling it had 30 turns.** It used the blanket nine times, walked to the ball and played with it,
  and toggled the music box. It never spoke. No hidden rule had fired yet when the run stopped.
- **From the rehearsal life** (`data.rehearsal/`), which did reach a lamp-lit night: the model turned the lamp
  off at comfort 22, which stopped the drop, then turned it back on the next turn reasoning that the dark was
  the problem. Hidden-rule predictions that night: model 2 of 38 right, twin 34 of 58.

What this says for v2: the experiment worked as a measurement, and was dull to watch. One call every ten
seconds bought single disconnected actions, and the first two hours bought nothing visible at all.

## V2.1: alive (7 Oct 2026)

Fresh life started 17:15 with `./run.sh start`; nothing to archive first, since V2.0 had already moved the
v1 data and the V2.1 dev lives were kept out of `data/`. Watched from the egg through its first hour as a
hatchling and its first sleep (17:15 to 18:31, ticks 0 to 2273). No errors in the log, no failed model calls.

**The check: it visibly walks around and does short sequences; model calls under 60 an hour.** Passed, with
one reservation about how short the sequences are.

- **Egg:** 10 minutes, no model calls, hatched at tick 300.
- **Model calls:** 48 in the hour, median 8.0 s each, slowest 12 s. 47 of the 48 were "nothing to do", so the
  75-second floor is what set the rate, not the pet's own pace. v1 made 360 an hour.
- **What it did:** 80 steps in 48 intentions: 33 walks, 22 uses, 12 looks, 10 rests, 2 observes, 1 belief
  written. No step was ever impossible. It never spoke.
- **Sequences are very short.** 30 intentions had 2 steps, 17 had 1, one had 3; none used 4 or 5. A typical
  one is "Move to blanket and use it" or "Move to bed and rest". They take about 25 seconds, so it stands
  idle for roughly half of every 75. Asking for "a few steps" in the output format did not lengthen them.
- **Predictions:** 67% of 46 scorable ones were right, against 16 to 21% in v1. The needs label and predicting
  over a whole intention both help.
- **Its first night went badly, fast.** Night began at tick 1950 with the lamp on. Comfort fell from the 90s to
  0 by tick 2090, under five minutes, and it earned the notch. In that time it had four thoughts: look at the
  window, turn the music box on "for comfort", turn it off because the music "likely contributes to discomfort
  in the night", go to bed. It never touched the lamp.
- **Why that matters for the design:** the hidden rules still run at v1 speed (4 comfort per 10 s), but the
  mind now runs about seven times slower. v1 gave it 25 decisions during a drop like that; v2 gives it three
  or four. And because a step's reported change covers the whole step, a 40-second rest under the lamp reads
  as "resting cost 16 comfort".
- **The consolidation fix works.** Its first sleep produced three statements about how things work and no
  log entries: resting on the bed is the best way to regain energy; "Comfort drops sharply during the night
  (around -4)", which is half of the lamp rule; and "The music box eventually stops playing on its own", which
  is wrong (it turned it off itself).
- **The view:** the room fills the window, the creature is twice its old size and walks tile by tile with a
  small hop, three dots show while it thinks, and the notch is visible on its body. Checked in a headless
  browser with the drawer closed and open, on the Mind and Lab tabs; the visitor controls were not clicked.

To decide before V2.2:
- Whether the standing rules should slow down to match the slower mind, or a need falling under 30 should
  be allowed to interrupt the 75-second floor. As it is, a lit night is over before the pet can work it out.
- Whether to push for longer plans (for instance a minimum of two steps), or accept one-and-two-step
  intentions and shorten the floor so it idles less.

### The same life after 15 hours (8 Oct, 08:20; archived to `data.v2.1/`)

Left running overnight: 15.1 real hours, world day 8, seven sleeps, 516 intentions, 915 steps, one start,
no errors, none of the 516 model calls failed.

- **It never found the lamp rule.** It turned the lamp off on purpose once in seven nights. Comfort was under
  20 at the end of 24% of its steps. Only 52% of its 23 predictions about a need the lamp was moving were right.
- **It blamed the wrong things, and the reporting helped it do so.** "Night is universally comfort-hostile",
  and "The catastrophic comfort drop (-14.4) at night occurs specifically during a rest action". A 40-second
  rest under the lamp was reported as one change of -14.4, so resting looked like the cause.
- **Plans stayed short:** 174 of one step, 293 of two, 38 of three, 11 of four or five.
- **Beliefs:** seven, none ever discarded, no log entries. They grew long and full of numbers ("+11.2 during
  day, dusk, and night when the entity has moved away and returned"). One is plainly wrong: the music box
  "autonomously oscillates" (it toggles it itself).
- **It spoke once:** "The melody loops endlessly. Do you hear it too?" Nobody was there; no visitor ever acted.
- **Body:** pale green, taller, more angular, with the notch from night one.

Decided from this, before V2.2:
1. A need falling under 30 interrupts the thinking floor, and the standing hidden rules slow to a quarter
   (a light at night costs 1 comfort per 10 s, not 4), so a bad night lasts about a dozen thoughts, not three.
2. An intention has at least two steps, and the floor drops from 75 s to 65 s, so it idles less.
3. A step's result separates what the step did from what was happening anyway ("you rested; energy +12.0;
   meanwhile comfort -4.4"), so a long step stops looking like the cause of the room's effects.
4. A belief is at most 140 characters.

## V2.2: making (8 Oct 2026)

The V2.1 life was stopped and archived to `data.v2.1/` (see above). Fresh life started 08:35 with
`./run.sh start`; watched from the egg through its first hour as a hatchling and its first sleep
(ticks 0 to 2273, 08:35 to 09:51). No errors, no failed model calls, no step ever impossible.

**The check: in its first hour as a hatchling it makes at least 2 things, and every made thing renders and
has the effect the table says.** Passed.

- **It made four things**, at ticks 710, 1239, 1305 and 1968:

  | Name | Material | Shape | Its purpose | What happened |
  |---|---|---|---|---|
  | warm pebble | warm | brown blob, size 1 | "to hold for comfort" | used 8 times, nothing each time: warm works by being near it at night, not by using it |
  | warm hug | warm | brown blob, size 2 | "to hold for comfort" | used 3 times, nothing |
  | warm fuzz | soft | orange blob, size 2 | "to hold and feel warm" | used 13 times, +2.0 comfort each time, exactly what soft at size 2 gives |
  | glow dot | bright | yellow dot, size 1 | "to see in the dark and feel curious" | never used; switched on from the moment it was made |

- **All four are drawn** in the room and on the Things shelf, and the shelf's "what it really does" line
  matched what the catalog recorded. One check per material covers the other seven materials, which a
  hatchling cannot choose yet. The star shape has only been looked at on the shelf, not in the room.
- **It found a useful thing by trying.** Two warm things did nothing when used, so the third was soft, and
  that one it then used more than anything else in the room, by name, in its plans ("Using the warm fuzz again
  is the most reliable way to boost comfort (+2.0)").
- **Its invention ran into the physics, as §5 intends.** It had turned the lamp off in the morning. Just after
  nightfall it made the glow dot beside the bed "to see in the dark". That put a light on at night: comfort
  fell from 54 to 22 before it slept, twice crossing 30 and triggering an urgent thought each time. It
  answered with the blanket and the warm fuzz and never suspected the glow dot.
- **It still blamed resting.** After the first sleep: "At night, resting causes comfort -3.0 instead of the
  +0.8 comfort seen during day/dusk". The split step result ("you rested; energy +12.0; meanwhile comfort
  -3.0") was not enough to stop that reading. The wording now says "in the 44 s that took, apart from it:
  comfort -3.0"; whether that helps is for the next life to show.
- **Slower rules did what was wanted.** With a light on, comfort took about 5 minutes to fall 32 points, and
  the pet had nine thoughts in that time. In V2.1 the whole fall to zero took under five minutes and four thoughts.
- **Plans:** 53 of two steps, 2 of three, none longer. The two-step minimum is being met and not exceeded.
- **Model calls:** 55 in the hour, median 8.0 s. Under 60, but close, so the floor between thoughts went from
  65 s to 70 s (51 an hour, plus urgent ones).
- **Predictions:** 65% right overall; 3 of 16 about a need a hidden rule was moving.

**The gate: are most made things near-identical?** Not failed, but worth watching. Three of the four are
single blobs meant "to hold" for comfort, and the first two differ only in size. Against that: it used three
of its four materials, the sequence was a real search that ended in something that works, and the fourth
thing is different in shape, material and purpose. It never used a second part. If the next life's shelf is
mostly comfort blobs again, the novelty pressure needs work before V2.4.

## V2.3: growing (8 Oct 2026)

The V2.2 life was stopped and archived to `data.v2.2/`. This milestone's check is a fast-clock day
(`day_seconds = 1800`), and it took two lives and two changes before the pet earned a stage.

**The check: run a day at fast clock and confirm stage-ups fire from the right counts.** Passed, in the end.
On the second life the pet became a Child at tick 6225, 06:00 on world day 8, 3.5 real hours in, on the first
morning it held two useful things. It was told "you feel bigger; you can do new things: arrange, things of up
to 4 parts, the cool material, the dark material, the noisy material, the quiet material, the bouncy material,
the heavy material", and the view showed "it is now a Child". On every earlier morning it had the days and
not the things, and was correctly left a hatchling. The counts are also covered by the self-check, including a
simulated fast-clock life that is promoted on the morning of day 3 and not before.

**The gate: does it ever reach Child at the fast clock?** It tripped twice before it passed.

- **First life (`data.v2.3-first/`, 2.4 hours, to world day 6): two things made, one useful, never a Child.**
  Two of its first three makes were rejected for aiming at a taken tile (once the bed's own tile, for a "soft
  pillow"). Then it stopped making altogether for 78 minutes. Its curiosity had reached 100 after 37 minutes
  and stayed there: revisiting the ten starting objects kept paying out fresh curiosity for ever, so it had
  no reason to invent.
  - Change: a thing aimed at a taken tile is put on the nearest free one.
  - Change: novelty wears for good. Each repeat of the same interaction is worth 0.8 of the last, down to a
    tenth. Making something new is always fully novel.
- **Second life (`data/`, started 12:24): seven things in three hours, still one useful, still no Child.**
  Novelty wear worked: it made more. But four of the seven were warm things, which it parked around the spot
  where it spends its days. Warm things cost comfort by day, each one of them, and comfort sat at 0 until it
  earned the notch. It worked out that "all made 'warm' objects are passive; 'use' does nothing", and blamed the
  falling comfort on the blanket ("recent uses result in comfort loss").
  - Change: senses. The packet gained "you feel:", naming what is acting on it right now and whether that is
    pleasant, never why or when. This goes against §5's "the pet is told none of it" and has a config switch.
- **Same life, after senses were switched on at tick 5466:** on its very next thought, "The warm nest and glow
  feel unpleasant, so I must avoid them." Within four thoughts it had made a soft ball, gone to its soft cloud,
  taken apart the warm nest (its first unmake in 3 hours) and made a soft star. That night it took apart the
  bright ring too. The next morning it was a Child.

**What this says about growth.**
- At the fast clock the days requirement is always met early; what takes time is inventing, which runs at the
  pet's thinking rate and does not speed up with the clock. One useful thing took about 1.5 to 2 real hours.
  At the real clock that is roughly on schedule for Child at 2 days (4 hours), and tight for Youngling.
- For a hatchling only soft things can realistically become useful: hard and bright are for no need, and a
  warm thing helps only at night, when it is mostly asleep. Both useful things were soft blobs.
- A "use" is counted as any occasion a thing acted on the pet, so the warm nest logged 88 occasions and 10
  helpful ones. That is the engine saying, truthfully, that it was a bad thing to have made.

**Still weak.**
- Plans are almost always two steps (2.1 on average).
- Model calls ran at 35 to 39 an hour: the fast clock spends 29% of the time asleep, and a turn now takes 10 s.
- It never spoke, and no visitor has ever acted on any v2 life, so talk, gifts and the give control have only
  been exercised by the self-check and one websocket message.
- The made things are still narrow: blobs and rings, three materials, one part each, nearly all "for comfort".
  Child unlocks six more materials and four-part things; whether it uses them is the thing to watch next.

## V2.4: adult (8 Oct 2026)

Built while the V2.3 lives ran, and kept out of the V2.3 commit. A pet cannot become an Adult inside an
hour's watch (8 days lived and 8 useful things), so this milestone was watched on a throwaway life started
as an Adult (`start_stage = "adult"`), on its own port and data beside the real Child, for about 20 minutes
at the fast clock: one whole day and its night. The real Child was left running.

- **It taught on its own, five times in one day**, all to one thing, a soft ring it found already in the room
  called "drone": hum when it rests, then hum when alone, then hum when touched, then dim at night, then
  move toward it when alone. No step was impossible in 32. It noticed the returns: "Teaching the drone yields
  diminishing curiosity returns as repeated sessions progress (4.0→0.2)".
- **The behaviors run and show.** A lantern taught to glow by day had a halo by day and none at night, a
  humming thing drew rings, a thing taught to change colour was red by day and its own blue at night, and
  the drone had moved across the room to sit beside the sleeping pet. Bounce cannot be judged from a still.
- **Their effects are physics.** The self-check covers each: a thing glowing at night is a light and costs
  comfort, a dimming one shelters from the lamp, a hum spoils rest beside it, and four taught things is the limit.
- **It drew itself at its first sleep.** Its body was "very round and about as tall as wide, soft green, a
  sparse stripe pattern, with medium eyes set close together, and 4 limbs". The portrait was a green blob, a
  green bar, two black dots at the top, and green dots around the sides. An earlier single call for a
  three-limbed body returned a green circle, two white bars, two black dots and three green triangles.
- **The Self tab** shows each night's real body beside the portrait. The body pictures are taken from the
  room's own renderer, so they match what was on screen.
- **Not seen live:** the stage-up into Adult itself. Its counts (8 days, 8 useful things, 3 beliefs held for 2
  days) are checked only by the self-check. `visitor`-conditioned behaviors have not been triggered by a visitor.

One thing from the real Child, seen the same afternoon: after its senses were switched on it took apart
every warm thing and then made three soft things in a row (soft pillow, soft nest, soft moon), all white,
all one part. It has found what works and is repeating it, which is the V2.2 gate's worry. It has not touched
a new material, a second part, or `arrange`.

## V2.5: the long run, first hour (8 Oct 2026)

The fast-clock V2.3 life was stopped as a Child on world day 9 and archived to `data.v2.3/`. Between V2.4 and
this run one more change went in, from watching that Child make white soft thing after white soft thing:
novelty now goes by kind (another thing of a known material wears like a repeat) and eases back two repeats
a night. The clock is back to real time (`day_seconds = 7200`). Fresh life started 16:14 with `./run.sh start`;
watched from the egg through its first hour as a hatchling and its first sleep (ticks 0 to 2295, to 17:31).
No errors in the log; one model call of 57 failed and was retried at the next thought.

- **It made four things in the hour:** a "warm nest" that is in fact soft (a pink circle, "a place to rest"),
  then three bright things: light orb, glow dot, tiny star, "to add a point of light and interest". Two
  materials, all one part. Novelty by kind did not stop it making three lights in a row.
- **Its lights met the night, and this time it could feel it.** At nightfall the lamp and all three of its
  lights were on. "Comfort is falling and I feel the light is harsh." It first went to the blanket and the nest
  "away from the harsh light source". Four thoughts later: "the bright lights (lamp, orb, glow dot) are likely
  contributing to the discomfort". By the record it had switched the light orb and the glow dot off a little
  before that (ticks 2071 and 2077), switched the orb back on a minute later, and off again at tick 2177.
- **It stopped short.** It never switched off the lamp or its tiny star, so the light stayed harsh, comfort reached 0
  and it earned the notch. What it wrote down afterwards was wrong: "Light orb and glow dot are not permanent;
  they can turn off on their own after some time, unlike the lamp." Every change of state had been its own doing.
- **It spoke once**, unprompted, about the music box.
- **Numbers:** 53 model calls in the hour, median 8.0 s; 114 steps in 56 intentions, none impossible; 51 of
  56 intentions had two steps; 51% of predictions right, none of the 6 about a need a hidden rule was moving.
- **Toward Child:** 0 days lived, 0 useful things. The nest has been used once.

What to look at as it runs, in the spec's order: what it makes and why; whether its things get more useful
over time; which useful things it keeps; what it names itself and its things; how its self-portraits change.
And two of my own: whether it ever puts out the lamp for the night, and whether it uses a second part or a
material beyond soft, warm and bright once it is a Child.

Review with `uv run python -m engine.metrics`, the Things and Self tabs, and `data/model/things.json`.

### The long run at 6.8 hours (8 Oct, 23:00)

World day 4, 17:08. One start, no errors, 1 failed model call in 232. It became a Child on the morning of
day 3 (tick 6900), the first morning it could, with two useful things.

- **19 things made, 8 in the room.** Nearly all are lights or "glows": light orb, glow dot, tiny star, soft glow
  dot, gentle pulse, soft warm glow, cozy glow ring, shimmer dot, flickering glow, pulsing warm dot. Four
  materials tried (bright, soft, warm, and quiet once), every one a single part. As a Child it has six new
  materials and four-part things and has used neither, apart from that one quiet thing.
- **Both useful things are warm, and it arranged them.** "soft warm glow" and "cozy glow ring" were moved
  to the wall by the window (it used `arrange` four times) and have helped on most of 17 and 15 occasions.
  Earlier lives never made a warm thing useful.
- **It has settled into making a thing and taking it apart.** Eleven unmakes, most within a minute of the make.
- **Its curiosity has been at 0 for about three hours.** Novelty wore out on what it keeps doing ("move
  blanket" 41 times, "look music box" 27, "move warm nest" 24, five warm things), and it did not connect that
  with trying something of a new kind. It rests instead: 193 of 498 steps, at full energy, because resting by
  the blanket gives a little comfort.
- **It still has the lamp backwards:** "The lamp provides comfort; toggling it off causes a comfort loss of
  about 0.9." It has toggled it off twice and back on twice.

Changed at tick 12170 and applied to this same life (the engine restarted onto it; the life carried on):
- From the fourth repeat, a result says "(this has grown familiar)".
- With curiosity under 30 it feels "restless for something new".
- Repeats stop counting at ten, so a night's easing can bring some novelty back to what it has worn out.

### The long run at 14.6 hours (9 Oct, 06:49)

World day 8, 14:43. No errors, 1 failed model call in 533. The engine has started twice: once at the
beginning and once when I restarted it onto the familiarity change. It has not crashed.

- **It is a Youngling,** since the morning of day 8 (tick 24900), with six useful things. Adult needs 8 days
  lived (it has 7), 8 useful things, and 3 beliefs kept for 2 days (it has 11). The next check is the morning
  of day 9.
- **The band of what it makes has widened a great deal since it could feel familiarity.** 71 things made, in
  eight materials: soft 19, bright 17, warm 14, bouncy 11, quiet 4, noisy 4, cool 1, sweet 1. Nine have more
  than one part (eight of two, one of three), for instance "gliding comet", a white star over a blue ring,
  in the cool material. Six shapes used. The names moved on from glows: breathing moon, whispering mist,
  twirling vortex, floating jelly light.
- **It has combined twice** ("it combined the shifting light orb and the bouncy bubble into a wobbling light")
  and made and eaten one sweet. It has not painted, and has never used hard, dark or heavy.
- **It churns.** 55 of the 71 have been taken apart, many within a minute of being made: make a thing for the
  novelty, take it apart for the room and the energy. Twelve makes were refused because the room was full; it
  believes the limit is "about 6 light objects".
- **Its useful things are nearly all soft:** warm nest, warm cushion (26 helpful uses of 26), soothing wave,
  soft cloud, calm glow, and one warm one, the cozy glow ring.
- **It has been uncomfortable for most of its life.** Comfort was under 20 at the end of 52% of all steps, and
  of every single step on days 5 and 6. Nothing was hurting it for most of that time (it felt something
  unpleasant in 21 of 114 daytime packets). It was simply not tending to comfort: since it could feel
  "restless for something new", it chases novelty first. Curiosity is under 20 at the end of a third of steps
  too, so it is short of both.
- **It has spoken three times.** After "hello!" from the visitor: "Look at this! It changes!" Two and a half
  hours later, to an empty room: "Hello? I am ready for something new. Please come and change the room."
  It did not answer "what changes?".
- **About visitors it wrote:** "Visitors can place objects in the room, fill the bowl, and speak to you; their
  words appear as quoted text."
- **The lamp:** still believed to give comfort. It toggles it off and on again about once a day. On 17 of 17
  night packets on days 5 and 6 it felt the light as harsh.
- **13 beliefs, none ever discarded.** One new and wrong: things it made "can appear in the room without the
  character creating them".
- **Body:** tall, very round, pale, plain, no limbs, with the notch.
- **A model call now takes 12 s at the median,** up from 8, as the packet has grown with its things and beliefs.

Nothing was changed at this check.

## Voice, phase 1 (9 Oct 2026)

Built from [VOICE.md](VOICE.md) and added to the running long run without touching it. It is view-only:
`view/src/voice-plan.ts` (text and genome to notes), `view/src/voice.ts` (notes to sound, Web Audio only) and
`view/src/voicelab.ts` (the header controls and the Lab tab's voice lab). The engine, the brain and the
perception packet were not changed, and no engine restart was needed: every trigger could be read from what
the view already received, so nothing was added to the snapshot either. The engine kept the same process
(pid 36116) throughout and served the rebuilt view from disk.

**I have not heard any of this.** What follows is what was scheduled and what was measured. Whether it sounds
like a creature is for a person to judge.

What each sound is for:

| Sound | When | What it is |
|---|---|---|
| Speech | `said` changes | one short note per syllable, at most 24; the same syllable always has the same pitch and length |
| Heartbeat | while it is an egg | two soft low thumps every 1.4 s, every 0.9 s while a visitor is present |
| First cry | "it hatched" | a squeak rising to more than twice its pitch |
| Chirp | "it made a ..." or "it combined ..." | two quick notes, the second higher |
| Falling blip | "it took apart ..." | one short note sliding down |
| Content trill | a `use` that raised comfort or energy, or that the engine counted as a help | six fast notes alternating between two pitches |
| Three rising notes | "it is now a ..." | a new stage |
| "Hm?" | the visitor speaks to it or pokes it | a short note that dips, then rises |
| Whimper | comfort under 20 for 3 minutes while awake, then at most one every 5 minutes | two wavering notes that sink |
| Breathing | while asleep | filtered noise, in and out every 5.4 s, very quiet |
| Hum | a thing it taught to `hum`, while that thing is humming | a low filtered sawtooth, pitched by the thing's name; no pet's voice is ever a sawtooth |

Sounds without words are spaced at least 2 seconds apart and queue on the audio clock; speech cuts off any
still waiting. Everything is scheduled on the AudioContext clock and topped up from each snapshot, not from
timers, so it keeps going in a background tab.

How it was checked:
- `node view/check-voice.ts` covers the plans: syllables, the same word giving the same notes, the 24-syllable
  limit, each row of the genome table, each punctuation contour, the need-driven intonation, and every trigger.
- In a headless browser, notes were rendered offline and measured. Planned and measured pitch agreed within
  2 Hz for all four stages and all three waveforms, the same sentence rendered identically twice, and every
  wordless sound was audible (not silent).
- On a throwaway engine with a scripted pet, on its own port and data, every trigger fired in order: heartbeat,
  first cry, chirp, trill, speech, falling blip, "hm?" (from a poke), three rising notes, a taught thing's hum,
  breathing. A second run kept a pet awake and uncomfortable; the whimper came at the 3-minute mark.
- Sound starts off, turns on with a click, and after a reload comes back as "Sound on (click anywhere)" with
  the volume it was left at.
- Those headless runs were not muted, so for about 12 minutes around 07:21 to 07:35 this Mac may have played
  the test sounds out loud. Later runs are muted.

On the live pet, at the time it was added (world day 8, 22:50, a Youngling):
- **Its voice by the numbers:** base pitch about 399 Hz (Youngling 420, lowered 5% because it is tall). A sine
  wave, because it is very round. Muffled, with the filter at about 1.4 kHz, because it has gone pale. No
  vibrato to speak of, because its wobble has mutated down to 0.03. Shaky and pitched lower, because comfort
  was at 0. Syllables about 100 ms. "Hello? I am ready for something new!" would take 1.5 seconds and run
  between about 270 and 570 Hz.
- **What actually played in the first five minutes:** breathing only. It fell asleep at 23:00, half a minute
  after the view was rebuilt.
- **Not possible on this life:** the heartbeat and the first cry, since it hatched yesterday. They need a new egg.
- **Not yet seen on this life:** speech (it has spoken three times in 15 hours), the stage-up figure (its next
  chance is waking on day 9, if it has 8 useful things), and a taught hum (it cannot teach until it is an Adult).

The voice lab in the drawer's Lab tab plays a sentence and each sound with the pet's current voice, or with
sliders for stage, roundness, wobble, energy and comfort, and lists what has played lately.

Phases 2 and 3, and the brain changes held back for the next life, are in [NEXT-LIFE.md](NEXT-LIFE.md).

### Voice, an hour later: "I've not heard any sounds yet" (9 Oct, 08:20)

The sound path was working: measured in real time on the live page, every sound reached the output with
peaks between 0.2 and 0.45 of full scale. What was wrong was the design around it.

- The pet was asleep for the first 35 minutes, and breathing had been set so quiet (about 0.02 of full scale)
  that it could not be heard. It is now about three times louder (0.06).
- Awake, sounds come only on events, minutes apart, and nothing showed that sound was on or what had played.
  Turning sound on now answers at once with a "hm?" in the pet's own voice, and a readout beside the button
  names each sound for a few seconds as it plays.
- The default volume is 0.8, up from 0.6. A volume already saved in the browser is kept.

Still view-only, and the engine was not restarted.

Meanwhile the pet became an Adult on waking at tick 28500, the morning of day 9: the first live promotion
into Adult. Within 16 ticks it had taught its calm glow "to glow when pet resting". The stage-up figure will
have played for anyone with sound on at 08:05. Its moment reads "it is now a Adult"; the article is the
engine's, so it waits for the next life.

### Voice on the live pet, 07:35 to 08:31

A muted headless page listened to the live run for 55 minutes without acting on it. What it logged as played:

| Sound | Times | When |
|---|---|---|
| Breathing | 1 start | from 07:35 until it woke |
| Three rising notes | 1 | 08:05:26, as it became an Adult |
| Content trill | 21 | roughly once a minute while awake; it uses its soft things and the blanket constantly |
| Whimper | 4 | 08:08, 08:13, 08:18, 08:29: comfort stayed under 20 for most of the half hour |
| Falling blip | 2 | 08:17, 08:24 |
| Chirp | 1 | 08:18 |

No speech, no "hm?" (nobody spoke to it or poked it in that time) and no hum (the one thing it has taught
glows, it does not hum). As an Adult its voice dropped to a base of about 313 Hz. With comfort back above
20 the shake went out of it; syllables were about 90 ms.

So with sound on, an awake pet is heard about once a minute, nearly always as a trill. That may be too much
of one sound; it is what the table in VOICE.md asks for, and it is easy to thin out if it grates.

### The long run at 18.4 hours (9 Oct, 10:39)

World day 10, 12:45. One failed model call in 681. The engine has not been restarted since the familiarity
change (the voice was view-only), and has not crashed.

- **It is an Adult,** promoted on waking on day 9 (tick 28500, 08:05) with 8 days lived, 8 useful things and 11
  kept beliefs: every stage the spec defines, in 16.5 real hours. It now has 10 useful things.
- **It taught once,** 16 ticks after the promotion: the calm glow "to glow when pet resting". Nothing since.
- **Its first self-portrait** (night of day 9): an orange circle, two black circles at the top, and one orange
  triangle at the bottom. Its body that night was very round, orange, with one limb.
- **It combines now, in chains.** Six combines since becoming an Adult, each one feeding the next: twirling
  vortex + shifting prism = prismatic vortex; + another shifting prism = twirling kaleidoscope; + pulsing orb
  = living light sphere; + luminous bloom = pulsing star. Three of its things now have the full six parts.
- **90 things made, 8 in the room.** Bright 29, soft 22, warm 15, bouncy 12, quiet 5, noisy 4, cool 1, sweet 1.
  Still never hard, dark or heavy, and it has still not painted.
- **It put out the last light on purpose for the first time,** at tick 27407 on the night of day 8, with comfort
  low. Its hidden-rule predictions are right 62% of the time over the last 50, up from 18% at seven hours.
  Its belief about it has moved closer without arriving: "Night-time resting causes a comfort drain of about
  -4.2 in the passive 'apart from it' effects; this does not occur during day rests."
- **It is still short of both comfort and curiosity:** 12 and 14 at this check; comfort under 20 at the end of
  49% of all steps.
- **The visitor gave it a warm gift,** which it has used five times.
- **Still:** no name, 17 beliefs and none discarded, three utterances in all, the lamp toggled off and on.

## V3, part 0: the v2.5 life closed (9 Oct 2026, 12:55)

The long run was stopped at 20.7 real hours, world day 11, an Adult, with 126 things made, 12 of them useful,
19 beliefs (none ever discarded) and two self-portraits. It is archived to `data.v2.5/`, with a `baseline/`
folder holding what the next pets are compared against.

Before it was stopped it was asked, once, for a message to an egg it would never see. It wrote:

> Stay near the lamp. It breathes when you breathe. The room holds twelve things; you will make some of your
> own. Combine before you create — two small lights make one strange light, and it costs less than either
> alone. Rest when energy drops below thirty; the lamp keeps the dark from hurting. You will feel restless.
> That is not wrong. That is the pulse asking for a new shape. Make the shape. Unmake it. Make another. The
> spectral wave at (3,2) is mine. Let it fade. Let yourself be new. I was the one who made the resonant
> pulse, the luminous shatter, the breathing moon.

It passes on what she believed, true and false alike: the lamp as comfort, which the engine says is wrong;
churn as a way of life; and a number, thirty, that no v3 pet will ever be shown. That is the first thing the
v3 lineage inherits.
