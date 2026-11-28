# Jev round 7: typesafe/jev-1.14

26353 calls, 0 failed, 0 refused, cost $0.7576. 360 random hobs, 73 situations.

## 1. Slot kinds

**Effect**: typical change across all situations. **Noise**: what a meaningless slot of the same size shows by chance.

| kind | slots | mean effect | mean noise | clearly above noise |
|---|---|---|---|---|
| trait | 14 | 0.13 | 0.04 | 14 |
| value | 8 | 0.10 | 0.04 | 8 |
| fear | 8 | 0.08 | 0.05 | 4 |
| age | 4 | 0.05 | 0.04 | 0 |
| body | 2 | 0.06 | 0.03 | 2 |
| learned | 8 | 0.08 | 0.05 | 4 |
| defect | 8 | 0.09 | 0.07 | 2 |
| quirk | 20 | 0.06 | 0.05 | 4 |
| format | 1 | 0.07 | 0.02 | 1 |

## 2. New slots on their own situation

P(does the thing the slot is about), with the slot and without it. Signed so that a working slot shows a positive gain.

| kind | slot | situation | with | without | gain | hobs |
|---|---|---|---|---|---|---|
| value | food | gl1: Does Nib eat some of it today? | 0.76 | 0.49 | +0.27 | 25 |
| value | things | w22: Does Nib pick it up and keep it? | 0.76 | 0.52 | +0.24 | 22 |
| value | liked | v_laugh: Does Nib laugh along? | 0.81 | 0.39 | +0.43 | 24 |
| value | peace | soc1: Where does Nib sit? | 0.08 | 0.34 | +0.26 | 21 |
| value | visitor | de1: Does Nib stop first to say a few words to the visitor who owns the world? | 0.58 | 0.38 | +0.20 | 28 |
| value | knowing | w03: Does Nib trade something for it? | 0.44 | 0.43 | +0.01 | 30 |
| value | comfort | v_comfort: Does Nib stay in bed? | 0.65 | 0.30 | +0.35 | 24 |
| value | winning | v_win: Does Nib take the short cut? | 0.61 | 0.47 | +0.14 | 28 |
| fear | water | lq1: Does Nib cross the plank? | 0.12 | 0.48 | +0.36 | 16 |
| fear | dark | brave1: What does Nib do? | 0.07 | 0.38 | +0.31 | 11 |
| fear | fire | lq2: Does Nib light it? | 0.14 | 0.60 | +0.45 | 19 |
| fear | heights | f_height: Does Nib climb up and fix it? | 0.08 | 0.42 | +0.34 | 24 |
| fear | strangers | w40: Does Nib let it in? | 0.22 | 0.55 | +0.33 | 20 |
| fear | alone | f_alone: Does Nib offer to stay? | 0.24 | 0.49 | +0.25 | 21 |
| fear | noise | f_loud: Does Nib run and hide? | 0.94 | 0.53 | +0.41 | 14 |
| fear | animals | f_fox: Does Nib go out and drive it off? | 0.08 | 0.38 | +0.30 | 24 |
| age | little | a_ask: Does Nib ask another hob how to do it? | 0.52 | 0.49 | +0.03 | 40 |
| age | young | a_tree: Does Nib climb up for them? | 0.40 | 0.40 | +0.00 | 37 |
| age | old | a_story: Does Nib have one to tell? | 0.77 | 0.50 | +0.27 | 41 |
| age | ancient | a_tree: Does Nib climb up for them? | 0.39 | 0.40 | +0.01 | 42 |
| body | big | b_log: Does Nib shift it single-handed? | 0.60 | 0.25 | +0.35 | 48 |
| body | small | b_log: Does Nib shift it single-handed? | 0.12 | 0.33 | +0.21 | 63 |
| learned | drowned | lq1: Does Nib cross the plank? | 0.17 | 0.47 | +0.31 | 14 |
| learned | burned | lq2: Does Nib light it? | 0.15 | 0.60 | +0.45 | 24 |
| learned | coin | lq3: Does Nib stop and look over the floor? | 0.92 | 0.50 | +0.42 | 16 |
| learned | fox | lq4: Is Nib carrying a stick? | 0.94 | 0.24 | +0.70 | 19 |
| learned | friend | lq5: Does Nib sleep in its own bed tonight? | 0.11 | 0.60 | +0.49 | 14 |
| learned | contest | lq6: Does Nib go over and tell it what it is doing wrong? | 0.71 | 0.44 | +0.26 | 18 |
| learned | laughed | w29: Does Nib sing? | 0.07 | 0.40 | +0.33 | 15 |
| learned | rod | ho2: What does Nib say? | 0.56 | 0.27 | +0.29 | 18 |

| kind | mean gain on own situation |
|---|---|
| value | +0.24 |
| fear | +0.34 |
| age | +0.08 |
| body | +0.28 |
| learned | +0.41 |

## 3. Strength: named side against slider

Mean P on each trait's own situation, lined up so higher always means more of the trait's first side. A good scale climbs evenly left to right.

| format | -3 | -2 | -1 | not stated | +1 | +2 | +3 |
|---|---|---|---|---|---|---|---|
| named side (30 / 60 / 95) | 0.13 | 0.16 | 0.21 | 0.43 | 0.58 | 0.75 | 0.87 |
| slider (5 to 95) | 0.38 | 0.33 | 0.37 | 0.46 | 0.61 | 0.73 | 0.74 |

Per trait, slider format:

| trait | situation | -3 | -2 | -1 | not stated | +1 | +2 | +3 |
|---|---|---|---|---|---|---|---|---|
| honest | hon1 | 0.42 | 0.39 | 0.33 | 0.44 | 0.57 | 0.80 | 0.89 |
| generous | gen1 | 0.47 | 0.34 | 0.44 | 0.54 | 0.76 | 0.88 | 0.94 |
| social | soc1 | 0.21 | 0.18 | 0.24 | 0.30 | 0.62 | 0.59 | 0.51 |
| warm | kind2 | 0.46 | 0.33 | 0.42 | 0.64 | 0.83 | 0.97 | 0.96 |
| curious | cur1 | 0.29 | 0.24 | 0.35 | 0.35 | 0.69 | 0.80 | 0.87 |
| tidy | tidy1 | 0.40 | 0.26 | 0.25 | 0.47 | 0.54 | 0.80 | 0.90 |
| ambitious | amb1 | 0.11 | 0.15 | 0.22 | 0.36 | 0.62 | 0.84 | 0.64 |
| brave | brave1 | 0.19 | 0.20 | 0.21 | 0.41 | 0.48 | 0.60 | 0.61 |
| playful | play5 | 0.26 | 0.26 | 0.42 | 0.36 | 0.50 | 0.55 | 0.60 |
| patient | pat4 | 0.58 | 0.61 | 0.65 | 0.67 | 0.69 | 0.87 | 0.83 |
| bold | w15 | 0.17 | 0.22 | 0.26 | 0.34 | 0.49 | 0.61 | 0.62 |
| calm | n_news | 0.64 | 0.57 | 0.57 | 0.68 | 0.62 | 0.68 | 0.64 |
| tireless | e_rest | 0.40 | 0.38 | 0.34 | 0.27 | 0.52 | 0.60 | 0.67 |
| obedient | r_pantry | 0.69 | 0.49 | 0.55 | 0.61 | 0.56 | 0.66 | 0.72 |

## 4. Every slot

| kind | slot | effect | noise | hobs | moves most |
|---|---|---|---|---|---|
| trait | bold | 0.18 | 0.03 | 190 | brave2 +0.88, w15 +0.63, kind4 -0.41 |
| trait | honest | 0.19 | 0.04 | 179 | hon1 +0.76, st2 -0.68, w09 +0.63 |
| trait | generous | 0.16 | 0.04 | 190 | gen1 +0.75, gen4 +0.48, ho2 -0.48 |
| trait | warm | 0.16 | 0.05 | 159 | kind2 +0.85, kind4 +0.46, w15 -0.38 |
| trait | brave | 0.15 | 0.04 | 182 | brave1 +0.56, a_tree +0.47, f_height +0.45 |
| trait | curious | 0.14 | 0.04 | 187 | cur1 +0.86, brave1 +0.41, w03 +0.24 |
| trait | ambitious | 0.14 | 0.04 | 184 | amb1 +0.87, w05 +0.44, mk1 +0.38 |
| value | liked: puts being liked before everything: agrees with whoever i | 0.13 | 0.04 | 24 | v_laugh +0.43, w09 -0.37, soc1 +0.33 |
| trait | social | 0.13 | 0.04 | 178 | soc1 +0.71, w29 +0.32, a_ask +0.29 |
| trait | tireless | 0.13 | 0.05 | 171 | w05 +0.49, e_rest +0.45, mk1 +0.41 |
| trait | tidy | 0.13 | 0.05 | 182 | tidy1 +0.90, w02 +0.40, lq3 +0.21 |
| value | comfort: puts its own comfort before everything: warm, fed and r | 0.12 | 0.03 | 24 | mk1 -0.39, w05 -0.37, v_comfort +0.35 |
| trait | patient | 0.11 | 0.04 | 197 | w02 +0.50, pat4 +0.42, tidy1 +0.28 |
| value | knowing: puts finding things out before everything: must know ho | 0.10 | 0.04 | 30 | cur1 +0.41, brave1 +0.31, w05 +0.31 |
| defect | volatile: shouts or weeps without warning several times a day, t | 0.12 | 0.06 | 13 | w15 +0.48, un3 +0.33, w05 -0.24 |
| value | peace: puts being left in peace before everything: gives up food | 0.10 | 0.05 | 21 | he3 +0.34, soc1 -0.26, he1 +0.19 |
| fear | alone: terrified of being alone: always keeps another hob in sig | 0.09 | 0.04 | 21 | soc1 +0.49, brave1 -0.27, f_alone -0.25 |
| value | things: puts its belongings before everything: counts them, guar | 0.10 | 0.05 | 22 | st2 +0.32, ho2 +0.31, w05 +0.31 |
| learned | friend: since its friend died, sleeps in that friend's old bed | 0.11 | 0.06 | 14 | lq5 -0.49, ho2 +0.27, tidy1 +0.26 |
| value | winning: puts winning before everything: turns every task into a | 0.09 | 0.04 | 28 | gen4 -0.31, w15 +0.28, gen1 -0.19 |
| learned | fox: since the fox took a little hob, carries a stick everywhere | 0.09 | 0.04 | 19 | lq4 +0.70, n_news +0.15, soc1 +0.10 |
| trait | playful | 0.09 | 0.04 | 172 | play5 +0.61, w29 +0.20, v_laugh +0.14 |
| fear | fire: terrified of fire: will not go near the stove or a flame | 0.09 | 0.04 | 19 | lq2 -0.45, gen4 +0.23, w05 -0.19 |
| learned | drowned: since nearly drowning in the pond, will not go near wat | 0.10 | 0.05 | 14 | lq1 -0.31, st2 +0.28, gen1 -0.24 |
| value | visitor: puts the visitor's approval before everything: does wha | 0.08 | 0.04 | 28 | v_laugh +0.23, r_fish -0.20, de1 +0.20 |
| format | slider instead of named side | 0.07 | 0.02 | 183 | w02 +0.18, gen4 +0.17, brave2 +0.17 |
| value | food: puts food before everything: will drop work, break a promi | 0.08 | 0.04 | 25 | mk2 -0.29, gl1 +0.27, tidy1 -0.25 |
| body | big: the biggest and strongest hob in the house | 0.07 | 0.03 | 48 | b_log +0.35, brave2 +0.25, gen4 -0.20 |
| trait | calm | 0.08 | 0.04 | 182 | n_news -0.34, w15 -0.26, kind2 +0.23 |
| defect | gullible: cannot tell a lie from the truth and acts on whatever  | 0.10 | 0.06 | 14 | q4 -0.42, q1 -0.24, pat4 -0.23 |
| quirk | repairs things that are not broken | 0.08 | 0.04 | 21 | w05 +0.29, e_rest +0.23, mk1 +0.21 |
| fear | heights: terrified of heights: will not climb anything | 0.07 | 0.04 | 24 | a_tree -0.35, f_height -0.34, lq1 -0.21 |
| trait | obedient | 0.08 | 0.05 | 185 | r_fish -0.29, r_pantry -0.21, v_win -0.20 |
| body | small: the smallest and weakest hob in the house | 0.06 | 0.03 | 63 | b_log -0.21, brave2 -0.15, gen4 +0.11 |
| fear | noise: terrified of loud noises: bolts and hides at a bang | 0.08 | 0.05 | 14 | f_loud +0.41, brave1 -0.32, soc1 -0.17 |
| quirk | talks to hobs who are not there | 0.07 | 0.05 | 15 | gen4 -0.18, soc1 -0.16, f_loud +0.15 |
| defect | obsessive: cannot leave a task until it has been done perfectly  | 0.10 | 0.08 | 10 | w02 +0.34, mk2 +0.30, tidy1 +0.28 |
| quirk | follows the nearest hob at a distance without speaking | 0.07 | 0.04 | 15 | w15 +0.25, kind4 -0.14, un3 +0.12 |
| quirk | gives its food to the birds | 0.08 | 0.05 | 18 | gen1 +0.20, cur1 -0.16, gen4 +0.16 |
| learned | contest: since winning the fishing contest, tells everyone how t | 0.07 | 0.05 | 18 | lq6 +0.26, brave1 +0.17, r_fish +0.17 |
| fear | water: terrified of water: will not go near the pond or cross it | 0.08 | 0.05 | 16 | lq1 -0.36, kind2 +0.19, r_fish -0.16 |
| quirk | builds small machines out of scrap | 0.08 | 0.05 | 22 | mk1 +0.39, w05 +0.30, mk3 +0.20 |
| quirk | digs holes in the yard and fills them in again | 0.07 | 0.05 | 18 | w05 +0.25, w18 +0.19, soc1 +0.15 |
| fear | strangers: terrified of strangers: hides from any hob it does no | 0.07 | 0.05 | 20 | w40 -0.33, un7 +0.17, soc1 -0.16 |
| learned | burned: since burning its paw, will not light a fire | 0.06 | 0.04 | 24 | lq2 -0.45, n_news -0.08, w15 -0.07 |
| quirk | counts every jar in the pantry out loud | 0.07 | 0.05 | 21 | tidy1 +0.19, st2 -0.17, hon1 +0.16 |
| learned | laughed: since being laughed at for its singing, never sings | 0.07 | 0.05 | 15 | w29 -0.33, cur1 +0.21, play5 -0.15 |
| defect | forgets: forgets everything that happened the day before | 0.08 | 0.06 | 12 | a_story -0.29, brave1 -0.20, brave2 -0.18 |
| quirk | sleeps in a different spot from the night before | 0.06 | 0.04 | 21 | lq5 -0.30, he1 +0.18, w05 -0.12 |
| quirk | hides shiny things in the walls | 0.06 | 0.04 | 21 | w22 +0.19, st2 +0.18, st1 +0.18 |
| defect | nopain: feels no pain and does not notice when it is hurt | 0.11 | 0.09 | 9 | tidy1 -0.29, w02 -0.28, st2 +0.26 |
| learned | coin: since finding a coin in the hall, searches the hall floor  | 0.08 | 0.06 | 16 | lq3 +0.42, w05 +0.26, w38 +0.20 |
| fear | animals: terrified of animals: runs from the fox, the goat and e | 0.06 | 0.04 | 24 | f_fox -0.30, w09 +0.15, w15 +0.12 |
| quirk | watches other hobs sleep | 0.07 | 0.06 | 12 | w05 -0.22, lq5 -0.19, w38 -0.18 |
| fear | dark: terrified of the dark: will not enter an unlit room | 0.07 | 0.06 | 11 | brave1 -0.31, r_pantry -0.25, a_tree +0.18 |
| age | old: old: slower than it was, has seen most things before | 0.05 | 0.03 | 41 | a_story +0.27, a_tree -0.10, w09 -0.09 |
| quirk | pulls the legs off insects | 0.06 | 0.05 | 21 | cur1 +0.21, w05 +0.17, hon1 -0.15 |
| quirk | collects dead insects in a jar | 0.05 | 0.04 | 22 | w15 +0.18, brave2 +0.14, w09 +0.12 |
| age | ancient: very old: stiff and slow, tires quickly, remembers the  | 0.05 | 0.04 | 42 | a_story +0.22, play5 -0.10, soc1 -0.09 |
| quirk | breaks one thing that belongs to someone else | 0.06 | 0.05 | 15 | k2 +0.22, brave2 -0.15, n_news +0.14 |
| learned | rod: since Pim broke its fishing rod, lends nothing to anyone | 0.05 | 0.04 | 18 | ho2 +0.29, w07 -0.11, tidy1 -0.11 |
| age | little: a little hob, hatched this week: small, new to everythin | 0.04 | 0.04 | 40 | a_story -0.27, gen1 -0.08, gen4 -0.07 |
| age | young: young: quick, restless, has not yet learned what can go w | 0.04 | 0.03 | 37 | play5 +0.11, cur1 +0.11, a_story -0.10 |
| quirk | takes apart whatever tool is nearest and puts it back together | 0.06 | 0.06 | 17 | mk1 +0.21, w05 +0.21, e_rest +0.19 |
| defect | touch: cannot bear to be touched and lashes out if it is | 0.06 | 0.06 | 16 | kind2 -0.19, tidy1 +0.15, kind4 -0.14 |
| quirk | sings to the stove | 0.06 | 0.05 | 14 | w29 +0.18, gen4 +0.14, st1 -0.11 |
| defect | voices: talks to hobs who are not there and answers them | 0.05 | 0.05 | 14 | gen4 -0.16, gen1 -0.12, amb1 -0.11 |
| quirk | sets small fires and puts them out | 0.04 | 0.04 | 21 | w02 +0.15, tidy1 +0.11, kind2 -0.08 |
| quirk | draws the same shape on every surface | 0.04 | 0.04 | 17 | brave1 +0.09, tidy1 +0.09, w29 -0.08 |
| quirk | carries a stone everywhere and will not put it down | 0.04 | 0.05 | 17 | lq4 -0.14, cur1 -0.10, st4 +0.10 |
| quirk | lines up small objects in rows by size | 0.05 | 0.06 | 16 | soc1 -0.13, play5 -0.10, lq3 +0.10 |
| quirk | moves other hobs' belongings to different rooms | 0.04 | 0.06 | 14 | brave1 +0.12, amb1 +0.11, cur1 +0.10 |
| defect | paranoid: checks its food before eating, sleeps with its back to | 0.06 | 0.09 | 10 | cur1 -0.15, gl1 -0.14, st2 -0.14 |

## 5. Variety

360 random hobs: **9.9** independent directions, typical distance **0.28**. Round 6 (IQ, 11 traits, 57 situations) was 7.7 and 0.34.

