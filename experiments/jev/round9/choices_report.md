# Round 9, choices: pet-brain

842 calls on 150 moments from the house. Usable answers: **840 of 842**.
Time per call: median **1.7 s**, slowest 4.4 s. Prompt size: about 280 tokens.
At that speed, six hobs each deciding every 20 seconds would keep the model busy **52%** of the time.

## 1. Does the sheet move the choice?

Same moment, same options. "With no sheet" is how often it picked that same option when the sheet line was absent.

| Sheet line added | It picked the option the line is about | With no sheet |
|---|---|---|
| A pursuit one option serves | 27% (36 of 135) | 13% (18 of 135) |
| A favourite place one door leads to | 69% (33 of 48) | 38% (18 of 48) |
| A fear of one option (lower is right) | 3% (4 of 124) | 15% (18 of 124) |
| Full sheet: options it favours | 35% (14 of 40) | 45% (18 of 40) |
| Full sheet: options it fears (lower is right) | 15% (5 of 34) | 24% (8 of 34) |
| Second full sheet: options it favours | 28% (11 of 40) | 28% (11 of 40) |
| Second full sheet: options it fears (lower is right) | 6% (2 of 34) | 18% (6 of 34) |

A full random sheet changed the choice from the no-sheet choice in 44% (131 of 296) of moments.
Two hobs with different full sheets, at the same moment, chose differently in 45% (68 of 150).

## 2. With no sheet, what does it choose?

It agreed with the autopilot's own first choice in 28% (41 of 148).
It chose 20 different activities across 148 moments. The most chosen, with how often each was on offer:

| Activity | Chosen | On offer | Chosen when offered |
|---|---|---|---|
| wander | 27 | 135 | 20% |
| inspect | 25 | 149 | 17% |
| go next door | 22 | 60 | 37% |
| sit by the window | 16 | 78 | 21% |
| sit on | 10 | 111 | 9% |
| watch a creature | 10 | 53 | 19% |
| follow a creature | 9 | 62 | 15% |
| take out | 6 | 27 | 22% |
| gather | 4 | 17 | 24% |
| lay out the bits | 3 | 3 | 100% |

By position in the list (a habit of picking the first or last would show here): a 48, b 159, c 122, d 108, e 96, f 107, g 72, h 48

## 3. Asked the same thing twice

The same answer both times in 62% (49 of 79).

## 4. What it said

Twelve answers, with the sheet line it was given:

- **Antonia** (pursuit: creatures) chose *wandering about*: "restless, need move, stores low"
- **Islam** (pursuit: company) chose *sitting with Brody*: "just want Brody now"
- **Islam** (fear: creatures) chose *wandering about*: "too sad to sit, no one here, just moving"
- **Bogna II** (fear: creatures) chose *taking the dark drum out to look at*: "must see the thief's tool, hate its sound"
- **Lev** (pursuit: music) chose *sitting by the window*: "already sitting, too sad to move"
- **Islam** (fear: noise) chose *wandering about*: "Restless for new, can't sit still, need to move"
- **Lev** (pursuit: creatures) chose *following the beetle about*: "Must chase it. Greedy for the catch."
- **Islam** (fear: water) chose *going through the north door to the machine room*: "need wood, no time for pond"
- **Islam** (pursuit: company) chose *sitting with Brody*: "need kin close, heart feels light and lonely, Brody is safe"
- **Bogna II** (place: yard, pursuit: tidying, fear: heights, food: grown) chose *sitting by the window*: "Need to see the rain, not the mess."
- **Islam** (place: yard, pursuit: making, fear: dark, food: fish) chose *wandering about*: "restless, need fresh air, machine room too stuffy"
- **Bogna II** (pursuit: machines) chose *looking closely at the sweeper dock*: "must fix Lev's broom; focus on work"

## 5. One whole prompt

```
You are Bogna II, a grown hob. It is day, in autumn (food not put by spoils; winter is next); the sky is grey. You are in the music room.
You are very brave, very ambitious, very prickly, very cautious, very patient, generous, a little serious, a little solitary, a little tidy; your ways: stares at the rain; what you care about most: freedom and craft.
You play whenever you can.
Your mood: angry.
You feel: worthless (it is hard to think of anything else); uneasy; a bit bored; a little on edge.
What you are working toward: Lev has no broom of its own, with a broom.
You have just: sit by the window, go next door, play.

What do you do next? Choose one:
- a: settling on the music bench
- b: playing with the chimes
- c: looking closely at the drum
- d: sitting by the window
- e: wandering about
- f: singing "Lively Visitor's Echo"
- g: dancing
- h: using the old familiar drum

Reply as JSON: {"does": "<the letter>", "why": "<a few words, as yourself>"}
```

## 6. Answers that could not be used (first few)

- 071-none: `{
 "does": "b",
 "why": "watching the mouse, it is the only thing moving, the only thing alive, the ` 
- 119-none: `{
"does": "e",
"why": "looking for wood, maybe good bits, need to move, can't sit still, sad but loo` 
