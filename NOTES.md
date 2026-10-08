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
