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
