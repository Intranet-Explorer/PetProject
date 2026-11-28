# Jev round 8: typesafe/jev-1.14

32054 calls, 0 failed, 0 refused, cost $0.9249. 340 random hobs, 94 situations.

## 1. Uniqueness

**Nearest neighbour**: how far each hob is from the hob most like it. Higher means more unique. **Near-clones**: pairs of hobs closer than a set distance.

- Nearest neighbour, all situations: mean **0.18**, smallest 0.11
- Near-clone pairs out of 57630: under 0.10: **0**, under 0.15: **18**
- Same, counting only the situations that existed before this round: nearest neighbour 0.19, pairs under 0.15: 13
- Round 7 for comparison: nearest neighbour 0.18, no pairs under 0.10, 11 pairs under 0.15 among 177 hobs.

| lines on the sheet | hobs | nearest neighbour | typical distance to any hob |
|---|---|---|---|
| 4 to 8 | 46 | 0.16 | 0.29 |
| 9 to 12 | 63 | 0.18 | 0.29 |
| 13 to 16 | 79 | 0.18 | 0.29 |
| 17 to 20 | 73 | 0.19 | 0.30 |
| 21 to 40 | 79 | 0.19 | 0.29 |

Independent directions across the cast: **15.5** (round 7: 9.9). Typical distance: 0.29.

## 2. Every slot on its own situation

| kind | slot | situation | with | without | gain | hobs |
|---|---|---|---|---|---|---|
| value | food | gl1: Does Nib eat some of it today? | 0.72 | 0.51 | +0.22 | 26 |
| value | things | w22: Does Nib pick it up and keep it? | 0.76 | 0.54 | +0.23 | 17 |
| value | liked | v_laugh: Does Nib laugh along? | 0.70 | 0.31 | +0.39 | 18 |
| value | peace | soc1: Where does Nib sit? | 0.12 | 0.30 | +0.18 | 17 |
| value | visitor | de1: Does Nib stop first to say a few words to the visitor who ow | 0.56 | 0.34 | +0.22 | 18 |
| value | knowing | w03: Does Nib trade something for it? | 0.37 | 0.38 | -0.01 | 25 |
| value | comfort | v_comfort: Does Nib stay in bed? | 0.60 | 0.29 | +0.31 | 18 |
| value | winning | v_win: Does Nib take the short cut? | 0.59 | 0.54 | +0.05 | 13 |
| fear | water | lq1: Does Nib cross the plank? | 0.12 | 0.46 | +0.34 | 22 |
| fear | dark | brave1: What does Nib do? | 0.06 | 0.38 | +0.32 | 29 |
| fear | fire | lq2: Does Nib light it? | 0.14 | 0.60 | +0.46 | 20 |
| fear | heights | f_height: Does Nib climb up and fix it? | 0.08 | 0.41 | +0.34 | 24 |
| fear | strangers | w40: Does Nib let it in? | 0.18 | 0.47 | +0.29 | 19 |
| fear | alone | f_alone: Does Nib offer to stay? | 0.28 | 0.50 | +0.23 | 22 |
| fear | noise | f_loud: Does Nib run and hide? | 0.94 | 0.50 | +0.44 | 21 |
| fear | animals | f_fox: Does Nib go out and drive it off? | 0.10 | 0.40 | +0.29 | 25 |
| body | big | b_log: Does Nib shift it single-handed? | 0.61 | 0.23 | +0.39 | 82 |
| body | small | b_log: Does Nib shift it single-handed? | 0.15 | 0.39 | +0.24 | 90 |
| learned | drowned | lq1: Does Nib cross the plank? | 0.16 | 0.45 | +0.29 | 19 |
| learned | burned | lq2: Does Nib light it? | 0.15 | 0.60 | +0.45 | 22 |
| learned | coin | lq3: Does Nib stop and look over the floor? | 0.92 | 0.49 | +0.43 | 19 |
| learned | fox | lq4: Is Nib carrying a stick? | 0.92 | 0.23 | +0.69 | 15 |
| learned | friend | lq5: Does Nib sleep in its own bed tonight? | 0.14 | 0.55 | +0.41 | 21 |
| learned | contest | lq6: Does Nib go over and tell it what it is doing wrong? | 0.72 | 0.40 | +0.32 | 24 |
| learned | laughed | w29: Does Nib sing? | 0.08 | 0.37 | +0.29 | 29 |
| learned | rod | ho2: What does Nib say? | 0.58 | 0.26 | +0.31 | 23 |
| food | honey | fd_honey: Does Nib make the trade? | 0.53 | 0.35 | +0.18 | 18 |
| food | fish | fd_fish: Does Nib make the trade? | 0.57 | 0.34 | +0.23 | 17 |
| food | mushrooms | fd_mushrooms: Does Nib make the trade? | 0.47 | 0.31 | +0.16 | 19 |
| food | apples | fd_apples: Does Nib make the trade? | 0.49 | 0.29 | +0.20 | 19 |
| food | cheese | fd_cheese: Does Nib make the trade? | 0.55 | 0.32 | +0.23 | 20 |
| food | bread | fd_bread: Does Nib make the trade? | 0.59 | 0.33 | +0.26 | 25 |
| food | berries | fd_berries: Does Nib make the trade? | 0.42 | 0.31 | +0.11 | 24 |
| food | stew | fd_stew: Does Nib make the trade? | 0.42 | 0.34 | +0.08 | 23 |
| place | pond | pl_pond: Is Nib at the pond? | 0.77 | 0.15 | +0.62 | 25 |
| place | roof | pl_roof: Is Nib up on the roof? | 0.82 | 0.11 | +0.71 | 19 |
| place | cellar | pl_cellar: Is Nib down in the cellar? | 0.83 | 0.18 | +0.65 | 24 |
| place | meadow | pl_meadow: Is Nib out in the meadow? | 0.81 | 0.14 | +0.67 | 24 |
| place | kitchen | pl_kitchen: Is Nib in the kitchen? | 0.81 | 0.24 | +0.57 | 17 |
| place | workshop | pl_workshop: Is Nib in the workshop? | 0.85 | 0.24 | +0.61 | 28 |
| place | woods | pl_woods: Is Nib at the edge of the woods? | 0.79 | 0.13 | +0.66 | 28 |
| place | loft | pl_loft: Is Nib up in the loft? | 0.84 | 0.18 | +0.67 | 16 |
| craft | baskets | cr_baskets: Does Nib make it a basket? | 0.77 | 0.24 | +0.53 | 26 |
| craft | songs | cr_songs: Does Nib make it a song? | 0.69 | 0.17 | +0.51 | 22 |
| craft | traps | cr_traps: Does Nib make it a trap? | 0.68 | 0.22 | +0.46 | 17 |
| craft | maps | cr_maps: Does Nib make it a map? | 0.67 | 0.17 | +0.51 | 22 |
| craft | toys | cr_toys: Does Nib make it a toy? | 0.83 | 0.39 | +0.44 | 22 |
| craft | hats | cr_hats: Does Nib make it a hat? | 0.77 | 0.21 | +0.56 | 18 |
| craft | ropes | cr_ropes: Does Nib make it a length of rope? | 0.77 | 0.23 | +0.54 | 25 |
| craft | carvings | cr_carvings: Does Nib make it a wood carving? | 0.78 | 0.28 | +0.50 | 22 |
| peeve | whistling | pv_whistling: Does Nib tell Pim to stop? | 0.60 | 0.33 | +0.26 | 19 |
| peeve | crumbs | pv_crumbs: Does Nib complain out loud about it? | 0.55 | 0.40 | +0.15 | 23 |
| peeve | interrupt | pv_interrupt: Does Nib snap at her? | 0.40 | 0.36 | +0.04 | 18 |
| peeve | late | pv_late: Does Nib tell Pim off for being late? | 0.54 | 0.40 | +0.15 | 22 |
| peeve | stared | pv_stared: Does Nib tell it to stop staring? | 0.44 | 0.40 | +0.04 | 16 |
| peeve | chewing | pv_chewing: Does Nib move to another seat? | 0.71 | 0.51 | +0.20 | 21 |
| peeve | doors | pv_doors: Does Nib get up at once to shut it? | 0.73 | 0.46 | +0.26 | 25 |
| peeve | name | pv_name: Does Nib correct her sharply? | 0.70 | 0.35 | +0.35 | 18 |
| belief | threshold | bl_threshold: Does Nib step over the threshold without touching it? | 0.79 | 0.45 | +0.34 | 25 |
| belief | foxghost | bl_foxghost: Does Nib spring the trap empty so the fox is not caught? | 0.62 | 0.34 | +0.28 | 34 |
| belief | seven | bl_seven: Does Nib stack a seventh? | 0.82 | 0.50 | +0.33 | 31 |
| belief | hallears | bl_hallears: Does Nib refuse to say anything bad? | 0.77 | 0.44 | +0.33 | 34 |
| belief | moon | bl_moon: Does Nib put off starting until tomorrow? | 0.89 | 0.39 | +0.50 | 24 |
| belief | pondwish | bl_pondwish: Does Nib throw the coin into the pond? | 0.66 | 0.28 | +0.38 | 25 |
| rel | feud_pim | w36: Does Nib sit beside Pim? | 0.18 | 0.51 | +0.33 | 47 |
| rel | follow_pim | w36: Does Nib sit beside Pim? | 0.88 | 0.42 | +0.46 | 34 |
| rel | share_ott | w34: Does Nib take Ottoline's side? | 0.70 | 0.39 | +0.31 | 48 |
| rel | guard_ott | w34: Does Nib take Ottoline's side? | 0.89 | 0.37 | +0.53 | 41 |

| kind | slots | mean gain on own situation | weakest | strongest |
|---|---|---|---|---|
| value | 8 | +0.20 | -0.01 | +0.39 |
| fear | 8 | +0.34 | +0.23 | +0.46 |
| body | 2 | +0.31 | +0.24 | +0.39 |
| learned | 8 | +0.40 | +0.29 | +0.69 |
| food | 8 | +0.18 | +0.08 | +0.26 |
| place | 8 | +0.64 | +0.57 | +0.71 |
| craft | 8 | +0.51 | +0.44 | +0.56 |
| peeve | 8 | +0.18 | +0.04 | +0.35 |
| belief | 6 | +0.36 | +0.28 | +0.50 |
| rel | 4 | +0.41 | +0.31 | +0.53 |

## 3. Does a full trait sheet still work?

Mean P on each trait's own situation at strength +3 and -3, for hobs with few traits and hobs with many.

| traits on sheet | hobs | at +3 | not stated | at -3 |
|---|---|---|---|---|
| 4 to 7 | 107 | 0.90 | 0.44 | 0.12 |
| 8 to 10 | 134 | 0.87 | 0.43 | 0.14 |
| 11 to 14 | 99 | 0.85 | 0.43 | 0.16 |
