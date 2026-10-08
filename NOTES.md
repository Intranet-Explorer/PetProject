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
