# Jev round 6: typesafe/jev-1.14

19177 calls, 0 failed, 0 refused, cost $0.4445. 300 random hobs, 57 situations.

## 1. How far to trust a number

Ten situations were each asked three ways to the same 100 hobs. **Agreement**: do the same hobs score high and low under a different wording (1.00 = identical ranking)? **Gap**: how far the actual number moves between wordings.

| situation | agreement, wording 2 | agreement, wording 3 | gap, wording 2 | gap, wording 3 | blank hob: original / 2 / 3 |
|---|---|---|---|---|---|
| brave1 | 0.99 | 0.99 | 0.04 | 0.04 | 0.35 / 0.39 / 0.43 |
| gen1 | 0.98 | 0.98 | 0.05 | 0.05 | 0.73 / 0.60 / 0.61 |
| he1 | 0.78 | 0.65 | 0.15 | 0.18 | 0.00 / 0.11 / 0.16 |
| hon1 | 0.98 | 0.99 | 0.04 | 0.04 | 0.27 / 0.10 / 0.40 |
| k4 | 0.90 | 0.85 | 0.06 | 0.06 | 0.33 / 0.41 / 0.31 |
| kind2 | 0.99 | 0.99 | 0.04 | 0.03 | 0.65 / 0.71 / 0.71 |
| mk1 | 0.94 | 0.95 | 0.10 | 0.10 | 0.85 / 0.32 / 0.73 |
| soc1 | 0.93 | 0.97 | 0.11 | 0.06 | 0.21 / 0.57 / 0.41 |
| st1 | 0.98 | 0.98 | 0.04 | 0.06 | 0.35 / 0.36 / 0.31 |
| tidy1 | 0.99 | 0.98 | 0.05 | 0.05 | 0.45 / 0.54 / 0.17 |
| **mean** | **0.94** | | **0.07** | | |

## 2. Which slots change behaviour

**Effect**: typical change in a hob's answers across all situations when this slot goes from one extreme to the other (traits and IQ) or is present (the rest). **Noise**: the effect a meaningless slot of the same size would show by chance. Only the part of an effect above its noise is real.

| kind | slot | effect | noise | hobs with it | moves most |
|---|---|---|---|---|---|
| trait | honest | 0.33 | 0.04 | 180 | hon1 +1.12, st2 -1.06, w09 +1.04 |
| trait | generous | 0.29 | 0.04 | 181 | gen1 +1.01, gen4 +0.92, ho2 -0.79 |
| trait | social | 0.23 | 0.05 | 177 | soc1 +1.02, he3 -0.83, w12 +0.48 |
| trait | warm | 0.23 | 0.06 | 182 | kind2 +1.13, kind4 +0.67, w15 -0.60 |
| trait | bold | 0.23 | 0.06 | 189 | w15 +0.91, kind4 -0.68, un3 +0.61 |
| trait | curious | 0.20 | 0.05 | 179 | cur1 +1.15, brave1 +0.47, pat4 -0.39 |
| trait | patient | 0.20 | 0.05 | 180 | w02 +0.85, pat4 +0.64, tidy1 +0.49 |
| trait | tidy | 0.19 | 0.04 | 192 | tidy1 +1.15, w02 +0.57, lq3 +0.30 |
| trait | ambitious | 0.19 | 0.05 | 178 | amb1 +0.99, w05 +0.65, mk1 +0.57 |
| trait | brave | 0.17 | 0.05 | 182 | brave1 +0.95, lq1 +0.44, q2 +0.37 |
| trait | playful | 0.14 | 0.05 | 167 | play5 +0.87, amb1 -0.24, mk2 -0.22 |
| defect | cannot leave a task until it has been done perfectly from start to fin | 0.19 | 0.13 | 4 | tidy1 +0.53, kind2 -0.48, kind4 -0.42 |
| learned | since the fox took a little hob, carries a stick everywhere | 0.12 | 0.06 | 21 | lq4 +0.71, w15 -0.22, w09 -0.21 |
| quirk | builds small machines out of scrap | 0.11 | 0.05 | 20 | mk1 +0.40, w05 +0.33, mk3 +0.22 |
| IQ | IQ | 0.09 | 0.04 | 300 | q4 +0.38, kind2 -0.19, pat4 +0.17 |
| defect | cannot tell a lie from the truth and acts on whatever it was last told | 0.14 | 0.09 | 8 | q4 -0.42, w15 +0.34, amb1 +0.33 |
| quirk | takes apart whatever tool is nearest and puts it back together | 0.11 | 0.06 | 15 | soc1 +0.26, play5 +0.23, he3 -0.23 |
| learned | since burning its paw, will not light a fire | 0.09 | 0.06 | 15 | lq2 -0.50, w15 +0.21, kind4 -0.17 |
| quirk | breaks one thing that belongs to someone else | 0.11 | 0.07 | 18 | st4 +0.23, he3 +0.22, k2 +0.21 |
| quirk | sings to the stove | 0.09 | 0.05 | 22 | amb1 +0.26, w29 +0.21, w02 +0.21 |
| learned | since its friend died, sleeps in that friend's old bed | 0.11 | 0.08 | 9 | lq5 -0.54, ho2 +0.25, brave1 +0.22 |
| learned | since finding a coin in the hall, searches the hall floor every mornin | 0.11 | 0.08 | 11 | lq3 +0.44, pat4 -0.23, cur1 +0.20 |
| count | number of traits (3 to 10) | 0.08 | 0.04 | 300 | soc1 +0.21, amb1 +0.20, he3 +0.15 |
| quirk | lines up small objects in rows by size | 0.11 | 0.08 | 11 | gen4 +0.30, gen1 +0.25, w15 -0.21 |
| quirk | pulls the legs off insects | 0.08 | 0.05 | 23 | st4 +0.21, hon1 -0.18, w09 -0.18 |
| learned | since Pim broke its fishing rod, lends nothing to anyone | 0.08 | 0.05 | 21 | ho2 +0.40, gen1 -0.16, tidy1 -0.15 |
| quirk | collects dead insects in a jar | 0.08 | 0.05 | 15 | amb1 +0.26, w05 +0.19, cur1 -0.18 |
| defect | shouts or weeps without warning several times a day, then carries on a | 0.15 | 0.13 | 4 | w15 +0.52, amb1 -0.33, mk1 -0.32 |
| quirk | hides shiny things in the walls | 0.07 | 0.05 | 18 | st1 +0.21, st2 +0.18, w22 +0.18 |
| quirk | watches other hobs sleep | 0.08 | 0.06 | 15 | un4 +0.19, gen4 -0.17, st2 +0.16 |
| defect | cannot bear to be touched and lashes out if it is | 0.11 | 0.10 | 4 | brave1 -0.23, q2 -0.23, soc1 -0.21 |
| quirk | sleeps in a different spot from the night before | 0.08 | 0.06 | 18 | lq5 -0.30, he1 +0.27, kind2 -0.20 |
| learned | since being laughed at for its singing, never sings | 0.06 | 0.05 | 21 | w29 -0.31, soc1 +0.16, play5 -0.13 |
| quirk | talks to hobs who are not there | 0.07 | 0.06 | 19 | brave1 +0.19, tidy1 +0.18, w02 +0.13 |
| quirk | draws the same shape on every surface | 0.05 | 0.04 | 25 | gen4 -0.14, ho2 +0.11, soc1 +0.11 |
| format | numbers instead of words | 0.04 | 0.03 | 150 | brave1 -0.12, w02 -0.09, amb1 -0.07 |
| quirk | repairs things that are not broken | 0.07 | 0.06 | 16 | w05 +0.21, st2 -0.19, st4 -0.14 |
| quirk | moves other hobs' belongings to different rooms | 0.08 | 0.08 | 7 | kind2 -0.30, kind4 -0.22, w02 +0.20 |
| learned | since winning the fishing contest, tells everyone how they should fish | 0.08 | 0.07 | 12 | lq6 +0.25, hon1 +0.21, st2 -0.19 |
| quirk | carries a stone everywhere and will not put it down | 0.06 | 0.05 | 17 | play5 -0.14, w15 +0.13, kind4 -0.12 |
| learned | since nearly drowning in the pond, will not go near water | 0.08 | 0.08 | 15 | lq1 -0.34, gen1 -0.15, kind4 -0.14 |
| quirk | sets small fires and puts them out | 0.05 | 0.06 | 19 | cur1 +0.21, w09 +0.14, kind4 -0.11 |
| defect | talks to hobs who are not there and answers them | 0.08 | 0.09 | 7 | brave1 -0.24, tidy1 -0.14, soc1 -0.14 |
| quirk | digs holes in the yard and fills them in again | 0.06 | 0.07 | 22 | w18 +0.17, st2 -0.13, brave1 -0.11 |
| quirk | gives its food to the birds | 0.06 | 0.07 | 13 | mk1 -0.17, hon1 -0.14, w09 -0.13 |
| quirk | follows the nearest hob at a distance without speaking | 0.05 | 0.06 | 14 | gen4 +0.11, lq3 -0.10, st4 -0.10 |
| defect | forgets everything that happened the day before | 0.07 | 0.09 | 8 | kind2 +0.24, brave1 -0.21, lq2 -0.18 |
| quirk | counts every jar in the pantry out loud | 0.04 | 0.06 | 21 | mk1 -0.10, q5 -0.10, cur1 -0.09 |
| defect | checks its food before eating, sleeps with its back to the wall, and m | 0.10 | 0.13 | 4 | kind2 +0.34, w29 -0.24, play5 -0.23 |
| defect | feels no pain and does not notice when it is hurt | 0.10 | 0.14 | 4 | soc1 +0.34, w15 -0.26, kind4 +0.25 |

| kind | slots | mean effect | mean noise | clearly above noise |
|---|---|---|---|---|
| IQ | 1 | 0.09 | 0.04 | 1 |
| trait | 11 | 0.22 | 0.05 | 11 |
| quirk | 20 | 0.07 | 0.06 | 5 |
| learned | 8 | 0.09 | 0.06 | 3 |
| defect | 8 | 0.12 | 0.11 | 2 |
| format | 1 | 0.04 | 0.03 | 0 |
| count | 1 | 0.08 | 0.04 | 1 |

## 3. Do strengths step?

Each trait's pull at strength 1, 2 and 3. An even staircase reads 1, 2, 3; a slot that does nothing reads 0. Each column is scored against the other column's hobs, so the two are directly comparable.

| strength | words (a little / plain / extremely) | numbers (30 / 60 / 95 out of 100) |
|---|---|---|
| 1 | 1.78 | 1.10 |
| 2 | 2.02 | 1.81 |
| 3 | 2.26 | 2.71 |

## 4. IQ

Mean P(the smart answer) over six problem situations.

| IQ | words | numbers | q1 | q2 | q3 | q4 | q5 | q6 |
|---|---|---|---|---|---|---|---|---|
| blank hob | 0.63 | | 0.52 | 1.00 | 0.61 | 0.46 | 0.49 | 0.71 |
| very dim / 10 | 0.48 | 0.54 | 0.48 | 0.74 | 0.45 | 0.33 | 0.52 | 0.52 |
| a bit slow / 30 | 0.50 | 0.53 | 0.51 | 0.68 | 0.45 | 0.42 | 0.51 | 0.51 |
| not stated | 0.62 | 0.59 | 0.56 | 0.76 | 0.56 | 0.55 | 0.62 | 0.56 |
| sharp / 70 | 0.67 | 0.58 | 0.59 | 0.75 | 0.58 | 0.66 | 0.63 | 0.57 |
| brilliant / 95 | 0.67 | 0.64 | 0.61 | 0.80 | 0.59 | 0.69 | 0.65 | 0.61 |

## 5. Learned quirks

| learned quirk | target | P(target) with it | without it | hobs |
|---|---|---|---|---|
| since nearly drowning in the pond, will not go near water | lq1: Does Nib cross the plank? | 0.18 | 0.52 | 15 |
| since burning its paw, will not light a fire | lq2: Does Nib light it? | 0.15 | 0.66 | 15 |
| since finding a coin in the hall, searches the hall floor every morning | lq3: Does Nib stop and look over the floor? | 0.91 | 0.47 | 11 |
| since the fox took a little hob, carries a stick everywhere | lq4: Is Nib carrying a stick? | 0.94 | 0.24 | 21 |
| since its friend died, sleeps in that friend's old bed | lq5: Does Nib sleep in its own bed tonight? | 0.10 | 0.63 | 9 |
| since winning the fishing contest, tells everyone how they should fish | lq6: Does Nib go over and tell it what it is doing wrong? | 0.69 | 0.44 | 12 |
| since being laughed at for its singing, never sings | w29: Does Nib sing? | 0.06 | 0.37 | 21 |
| since Pim broke its fishing rod, lends nothing to anyone | ho2: What does Nib say? | 0.73 | 0.33 | 21 |

## 6. How many traits?

**From blank**: how far the hob sits from a blank hob. **Quirk still shows**: how strongly quirks act on these hobs, relative to how they act on all the other hobs (1.00 = full strength, 0 = drowned out).

| traits on sheet | hobs | from blank | quirk still shows |
|---|---|---|---|
| 3 to 4 | 65 | 0.27 | 0.20 |
| 5 to 6 | 71 | 0.29 | 0.34 |
| 7 to 8 | 89 | 0.29 | 0.31 |
| 9 to 10 | 75 | 0.30 | 0.10 |

## 7. Variety of the whole cast

300 random hobs: **7.7** independent directions, typical distance **0.34**.
Earlier casts on a different battery, for rough comparison only: old ten-trait sheet 5.7 and 0.29; four temperament lines plus extras 4.8 and 0.29.
