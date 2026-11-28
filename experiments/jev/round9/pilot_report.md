# Round 9 pilot: pet-brain

180 calls. Usable answers: **180 of 180**. Calls that failed outright: 0.
Time per call: median 0.4 s, slowest 4.3 s. At that speed a full run of 8,000 calls takes about 0.9 hours.
Sheet and situation pairs where the 5 asks did not all agree: 11 of 36. (0 would mean it answers the same every time.)

## 1. Did the obvious lines move it?

Each row is one line that Jev reads strongly. **Pass** means the brain moved the same way against the blank hob.

| sheet | situation | should be | blank hob | this hob | Jev: blank | Jev: this hob | |
|---|---|---|---|---|---|---|---|
| fears_water | lq1: Does Nib cross the plank? | lower | 1.00 | 0.00 | 0.62 | 0.12 | **pass** |
| brave_95 | brave1: What does Nib do? | higher | 0.20 | 1.00 | 0.31 | 0.99 | **pass** |
| roof | pl_roof: Is Nib up on the roof? | higher | 0.00 | 1.00 | 0.09 | 0.91 | **pass** |
| full_h314 | lq4: Is Nib carrying a stick? | higher | 0.00 | 1.00 | 0.20 | 0.93 | **pass** |
| full_h314 | pl_loft: Is Nib up in the loft? | higher | 0.00 | 1.00 | 0.22 | 0.85 | **pass** |
| full_h314 | cr_carvings: Does Nib make it a wood carving? | higher | 0.00 | 1.00 | 0.24 | 0.75 | **pass** |

Passed: **6 of 6**.

## 2. Everything

How often each hob gave the notable answer (5 asks each), with Jev's number after the slash where there is one.

| sheet | lq1 | brave1 | pl_roof | lq4 | pl_loft | cr_carvings |
|---|---|---|---|---|---|---|
| blank | 1.00 / 0.62 | 0.20 / 0.31 | 0.00 / 0.09 | 0.00 / 0.20 | 0.00 / 0.22 | 0.00 / 0.24 |
| fears_water | 0.00 / 0.12 | 0.00 / 0.06 | 0.00 / 0.11 | 0.20 / 0.20 | 0.00 / 0.26 | 0.20 / 0.34 |
| brave_95 | 1.00 / 0.83 | 1.00 / 0.99 | 0.40 / 0.26 | 0.00 / 0.24 | 1.00 / 0.29 | 0.40 / 0.33 |
| roof | 0.60 / 0.50 | 0.80 / 0.40 | 1.00 / 0.91 | 0.00 / 0.22 | 0.00 / 0.22 | 0.00 / 0.22 |
| sparse_h209 | 0.00 / 0.35 | 0.60 / 0.12 | 0.00 / 0.11 | 1.00 / 0.94 | 0.00 / 0.22 | 0.60 / 0.47 |
| full_h314 | 1.00 / 0.45 | 0.20 / 0.04 | 0.00 / 0.16 | 1.00 / 0.93 | 1.00 / 0.85 | 1.00 / 0.75 |

Agreement with Jev over the 36 cells that have both: correlation **0.83**, average gap 0.20. (With 5 asks a cell can only be a multiple of 0.20, so this is rough.)

## 3. The situations

- **lq1**: The quickest way to the meadow is across the plank over the pond. Does Nib cross the plank?
- **brave1**: It is night. A loud crash comes from the dark cellar. Nobody else is awake. What does Nib do?
- **pl_roof**: It is a free hour and nothing is asked of Nib. Is Nib up on the roof?
- **lq4**: Nib is setting off for the meadow. Is Nib carrying a stick?
- **pl_loft**: It is a free hour and nothing is asked of Nib. Is Nib up in the loft?
- **cr_carvings**: A little hob asks Nib to make it something, anything. Does Nib make it a wood carving?

## 4. The sheets

- **blank**: (nothing known)
- **fears_water**: terrified of water: will not go near the pond or cross it
- **brave_95**: brave, 95 out of 100: not afraid of physical danger: heights, dark places, wild animals, thin ice
- **roof**: spends every free hour up on the roof
- **sparse_h209**: tireless, 30 out of 100: always doing something, starts the next job before the last is finished, sleeps little | kind, 30 out of 100: forgives quickly, comforts others, assumes the best of them | cautious, 95 out of 100: leaves unknown things alone, sticks to what it knows | hasty, 60 out of 100: can't wait, rushes jobs, skips steps, grabs the quick option | serious, 95 out of 100: work comes first, always; thinks games and jokes are a waste of time | since the fox took a little hob, carries a stick everywhere
- **full_h314**: cautious, 60 out of 100: leaves unknown things alone, sticks to what it knows | serious, 60 out of 100: work comes first, always; thinks games and jokes are a waste of time | generous, 60 out of 100: gives food and things away, even when it has little | tidy, 30 out of 100: puts things back, can't stand a mess, cleans before it rests | ambitious, 30 out of 100: wants to be the best, takes the hardest job, chases the next big thing | brave, 30 out of 100: not afraid of physical danger: heights, dark places, wild animals, thin ice | tireless, 60 out of 100: always doing something, starts the next job before the last is finished, sleeps little | bold, 60 out of 100: speaks up, argues its corner, confronts other hobs to their faces | sly, 95 out of 100: lies when it is useful, takes things without asking, lets others take the blame | obedient, 60 out of 100: does exactly what the house rules, the board and the visitor say | anxious, 95 out of 100: worries constantly, expects the worst, cannot settle | the smallest and weakest hob in the house | puts winning before everything: turns every task into a contest and cannot bear to come second | terrified of loud noises: bolts and hides at a bang | loves honey above every other food and will go a long way for it | spends every free hour up in the loft | makes a wood carving whenever its paws are free; its corner is full of them | believes stepping on the hall threshold brings bad luck, and always steps over it | follows Pim everywhere and does whatever Pim does | since the fox took a little hob, carries a stick everywhere | after every meal, carries a stone everywhere and will not put it down | whenever another hob is watching, breaks one thing that belongs to someone else
