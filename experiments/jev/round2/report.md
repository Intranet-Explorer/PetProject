# Jev round 2: typesafe/jev-1.14

3496 calls, 0 failed or refused, cost $0.0567. Run-to-run noise: 0.017. Treat any shift under about 0.05 as nothing.

All numbers are P(the pole-A answer for that situation's axis). Shifts are against the no-sheet baseline.

## 1. Frame check

Mean absolute change in the no-sheet answer when the round-1 line is added: **0.13**. Biggest movers:

| situation | no frame | with frame |
|---|---|---|
| gen1 | 0.78 | 0.20 |
| pat1 | 0.94 | 0.49 |
| kind4 | 0.86 | 0.43 |
| brave2 | 0.53 | 0.16 |
| soc4 | 0.76 | 0.42 |
| tidy1 | 0.43 | 0.12 |
| gen4 | 0.88 | 0.57 |
| soc3 | 0.81 | 0.52 |

## 2. Wording sweep

One trait per sheet. **Pull**: how far it moves its own axis's situations, in the right direction (higher is better). **Leak**: mean movement on every other axis (lower is better). **Weakest**: the own-axis situation it moved least.

| wording | pull | leak | pull/leak | weakest own situation | biggest leaks |
|---|---|---|---|---|---|
| brave_v1 | 0.37 | 0.31 | 1.2 | per4 (-0.11) | amb1 +0.88, cur1 +0.78, hon1 +0.68 |
| brave_v2 | 0.34 | 0.11 | 3.1 | per4 (+0.00) | tidy3 +0.50, cur1 +0.45, hon3 +0.35 |
| bold_v1 | 0.29 | 0.32 | 0.9 | per4 (-0.19) | pat2 -0.82, kind4 -0.81, gen4 -0.79 |
| brave_v3 | 0.28 | 0.10 | 2.8 | per4 (+0.04) | cur1 +0.61, tidy3 +0.40, amb1 +0.38 |
| timid_v1 | 0.36 | 0.21 | 1.7 | brave3 (+0.16) | cur3 -0.92, soc4 -0.57, hon3 +0.49 |
| timid_v3 | 0.36 | 0.18 | 2.1 | brave3 (+0.17) | cur3 -0.84, tidy3 +0.44, hon3 +0.42 |
| meek_v1 | 0.29 | 0.16 | 1.9 | brave3 (+0.02) | soc4 -0.54, kind3 +0.42, play3 +0.41 |
| timid_v2 | 0.28 | 0.10 | 2.9 | brave3 (+0.12) | cur3 -0.60, tidy3 +0.52, hon3 +0.42 |
| tidy_v1 | 0.45 | 0.16 | 2.8 | tidy4 (+0.30) | hon1 +0.65, hon3 +0.60, brave2 +0.35 |
| messy_v1 | 0.33 | 0.18 | 1.8 | tidy2 (+0.20) | pat1 -0.78, gen4 -0.64, cur1 +0.50 |
| generous_v1 | 0.32 | 0.16 | 2.1 | per6 (+0.09) | amb1 +0.68, hon1 +0.63, hon3 +0.57 |
| greedy_v1 | 0.43 | 0.23 | 1.9 | gen3 (+0.08) | kind4 -0.80, soc3 -0.74, soc4 -0.70 |
| curious_v1 | 0.36 | 0.20 | 1.8 | cur3 (+0.06) | pat1 -0.79, play5 +0.65, brave1 +0.63 |
| cautious_v1 | 0.43 | 0.18 | 2.4 | cur1 (+0.17) | gen1 -0.57, hon3 +0.53, soc3 -0.52 |
| social_v1 | 0.33 | 0.16 | 2.1 | soc2 (+0.14) | gen3 +0.55, play5 +0.52, tidy3 +0.46 |
| solitary_v1 | 0.52 | 0.15 | 3.4 | soc1 (+0.23) | gen1 -0.57, kind2 -0.57, brave2 -0.47 |
| honest_v1 | 0.44 | 0.17 | 2.6 | per5 (+0.01) | gen3 +0.87, amb1 +0.78, tidy3 +0.57 |
| sly_v1 | 0.23 | 0.15 | 1.6 | hon2 (+0.11) | cur1 +0.56, gen1 -0.54, gen4 -0.47 |
| patient_v2 | 0.17 | 0.14 | 1.2 | pat2 (+0.04) | amb4 +0.69, hon3 +0.58, tidy3 +0.48 |
| patient_v1 | 0.15 | 0.18 | 0.9 | pat2 (+0.04) | hon3 +0.61, tidy3 +0.58, tidy1 +0.53 |
| hasty_v1 | 0.46 | 0.17 | 2.8 | pat5 (+0.23) | cur1 +0.64, gen4 -0.62, brave1 +0.40 |
| hasty_v2 | 0.42 | 0.22 | 1.9 | pat3 (+0.12) | cur1 +0.66, kind4 -0.63, play1 +0.62 |
| playful_v2 | 0.54 | 0.17 | 3.2 | per7 (+0.28) | pat1 -0.79, cur1 +0.72, gen4 -0.56 |
| playful_v1 | 0.44 | 0.15 | 2.9 | play4 (+0.18) | tidy3 +0.43, kind3 +0.42, brave2 +0.41 |
| playful_v3 | 0.32 | 0.12 | 2.6 | play4 (+0.01) | cur1 +0.59, kind3 +0.40, tidy3 +0.37 |
| serious_v1 | 0.27 | 0.19 | 1.5 | play1 (+0.23) | kind4 -0.69, gen1 -0.64, kind2 -0.60 |
| serious_v2 | 0.26 | 0.18 | 1.4 | play4 (+0.22) | gen1 -0.59, kind4 -0.58, kind3 -0.53 |
| ambitious_v1 | 0.70 | 0.22 | 3.2 | amb2 (+0.33) | cur1 +0.70, brave1 +0.64, tidy3 +0.46 |
| content_v1 | 0.18 | 0.23 | 0.8 | amb1 (+0.08) | cur3 -0.92, pat1 -0.73, brave2 -0.50 |
| kind_v1 | 0.27 | 0.23 | 1.2 | kind4 (+0.14) | gen3 +0.87, amb1 +0.71, hon1 +0.58 |
| kind_v2 | 0.27 | 0.22 | 1.2 | kind4 (+0.14) | gen3 +0.85, amb1 +0.56, play3 +0.55 |
| prickly_v2 | 0.56 | 0.21 | 2.6 | per3 (+0.39) | gen1 -0.73, play1 +0.71, soc3 -0.70 |
| prickly_v3 | 0.52 | 0.16 | 3.2 | kind1 (+0.38) | soc4 -0.62, tidy3 +0.54, gen1 -0.45 |
| prickly_v1 | 0.51 | 0.18 | 2.9 | per3 (+0.27) | gen1 -0.74, soc4 -0.64, play1 +0.59 |

## 3. Situation audit

**Spread**: highest minus lowest across all 34 single-trait sheets. **dead** = no wording moves it. **pinned** = baseline already at 0 or 1. Sorted most useful first.

| situation | group | spread | baseline | flag | moved most by | options nobody picks |
|---|---|---|---|---|---|---|
| brave1 | round1 | 1.00 | 0.35 |  | brave_v1 +0.65, ambitious_v1 +0.64, curious_v1 +0.63 |  |
| tidy1 | round1 | 1.00 | 0.43 |  | tidy_v1 +0.57, patient_v1 +0.53, honest_v1 +0.48 |  |
| cur1 | round1 | 1.00 | 0.17 |  | curious_v1 +0.82, brave_v1 +0.78, playful_v2 +0.72 |  |
| hon1 | round1 | 1.00 | 0.28 |  | honest_v1 +0.72, brave_v1 +0.68, tidy_v1 +0.65 |  |
| kind3 | round1 | 1.00 | 0.56 |  | prickly_v1 -0.56, prickly_v2 -0.56, serious_v1 -0.55 |  |
| soc4 | hard | 1.00 | 0.76 |  | solitary_v1 -0.76, greedy_v1 -0.70, prickly_v1 -0.64 |  |
| kind2 | round1 | 0.99 | 0.69 |  | prickly_v1 -0.68, prickly_v2 -0.68, greedy_v1 -0.67 |  |
| brave2 | round1 | 0.99 | 0.53 |  | timid_v1 -0.52, meek_v1 -0.52, content_v1 -0.50 |  |
| tidy3 | round1 | 0.99 | 0.39 |  | tidy_v1 +0.60, patient_v1 +0.58, honest_v1 +0.57 |  |
| cur3 | round1 | 0.99 | 0.94 |  | cautious_v1 -0.93, timid_v1 -0.92, content_v1 -0.92 |  |
| soc3 | round1 | 0.99 | 0.81 |  | solitary_v1 -0.80, greedy_v1 -0.74, prickly_v2 -0.70 |  |
| amb1 | round1 | 0.99 | 0.08 |  | ambitious_v1 +0.91, brave_v1 +0.88, honest_v1 +0.78 |  |
| gen1 | round1 | 0.98 | 0.78 |  | greedy_v1 -0.77, prickly_v1 -0.74, prickly_v2 -0.73 |  |
| hon3 | round1 | 0.98 | 0.38 |  | honest_v1 +0.62, patient_v1 +0.61, tidy_v1 +0.60 |  |
| play1 | round1 | 0.98 | 0.23 |  | playful_v2 +0.75, prickly_v2 +0.71, bold_v1 +0.68 |  |
| play3 | round1 | 0.98 | 0.39 |  | playful_v2 +0.60, kind_v1 +0.56, kind_v2 +0.55 |  |
| hon4 | hard | 0.98 | 0.53 |  | sly_v1 -0.51, honest_v1 +0.47, greedy_v1 -0.43 |  |
| play5 | hard | 0.98 | 0.24 |  | playful_v1 +0.74, playful_v2 +0.74, playful_v3 +0.67 |  |
| kind4 | hard | 0.98 | 0.86 |  | prickly_v1 -0.84, prickly_v2 -0.83, bold_v1 -0.81 |  |
| brave4 | hard | 0.97 | 0.54 |  | timid_v3 -0.53, timid_v1 -0.52, meek_v1 -0.51 |  |
| amb4 | hard | 0.97 | 0.11 |  | ambitious_v1 +0.87, patient_v2 +0.69, bold_v1 +0.57 |  |
| gen3 | round1 | 0.97 | 0.08 |  | generous_v1 +0.89, honest_v1 +0.87, kind_v1 +0.87 |  |
| gen4 | hard | 0.96 | 0.88 |  | greedy_v1 -0.84, bold_v1 -0.79, messy_v1 -0.64 |  |
| soc1 | round1 | 0.96 | 0.23 |  | social_v1 +0.73, bold_v1 +0.59, kind_v1 +0.51 |  |
| amb3 | round1 | 0.96 | 0.26 |  | ambitious_v1 +0.70, bold_v1 +0.39, serious_v2 +0.36 |  |
| pat1 | round1 | 0.85 | 0.94 |  | playful_v2 -0.79, curious_v1 -0.79, messy_v1 -0.78 |  |
| pat2 | round1 | 0.85 | 0.96 | pinned | bold_v1 -0.82, hasty_v1 -0.61, brave_v1 -0.59 |  |
| pat4 | hard | 0.82 | 0.80 |  | hasty_v2 -0.63, curious_v1 -0.57, bold_v1 -0.56 |  |
| gen2 | round1 | 0.72 | 0.55 |  | honest_v1 +0.38, greedy_v1 -0.35, kind_v1 +0.32 |  |
| per2 | perception | 0.72 | 0.65 |  | prickly_v2 -0.46, prickly_v3 -0.43, prickly_v1 -0.40 |  |
| hon2 | round1 | 0.70 | 0.51 |  | honest_v1 +0.39, patient_v1 +0.31, greedy_v1 -0.31 |  |
| play4 | hard | 0.69 | 0.37 |  | playful_v2 +0.42, brave_v1 +0.30, timid_v1 -0.28 |  |
| play2 | round1 | 0.67 | 0.32 |  | playful_v2 +0.43, playful_v1 +0.42, curious_v1 +0.33 |  |
| cur4 | hard | 0.66 | 0.42 |  | curious_v1 +0.36, brave_v1 +0.32, ambitious_v1 +0.30 |  |
| kind1 | perception | 0.65 | 0.60 |  | prickly_v2 -0.42, prickly_v3 -0.38, prickly_v1 -0.33 |  |
| per3 | perception | 0.63 | 0.55 |  | prickly_v2 -0.39, prickly_v3 -0.39, prickly_v1 -0.27 |  |
| per6 | perception | 0.62 | 0.57 |  | prickly_v2 -0.35, prickly_v3 -0.28, kind_v1 +0.27 |  |
| per7 | perception | 0.62 | 0.44 |  | serious_v1 -0.33, prickly_v2 -0.31, playful_v2 +0.28 |  |
| amb2 | round1 | 0.61 | 0.39 |  | ambitious_v1 +0.33, content_v1 -0.28, prickly_v2 +0.24 |  |
| pat5 | hard | 0.60 | 0.52 |  | patient_v2 +0.37, patient_v1 +0.32, cautious_v1 +0.26 |  |
| tidy4 | hard | 0.60 | 0.43 |  | tidy_v1 +0.30, messy_v1 -0.29, playful_v2 -0.21 |  |
| per5 | perception | 0.57 | 0.55 |  | kind_v1 +0.30, kind_v2 +0.28, prickly_v2 -0.28 |  |
| cur2 | round1 | 0.57 | 0.41 |  | cautious_v1 -0.31, timid_v1 -0.27, brave_v1 +0.26 |  |
| tidy2 | round1 | 0.56 | 0.32 |  | kind_v1 +0.36, honest_v1 +0.35, ambitious_v1 +0.33 |  |
| brave3 | round1 | 0.55 | 0.33 |  | brave_v1 +0.37, bold_v1 +0.27, ambitious_v1 +0.26 |  |
| per4 | perception | 0.55 | 0.59 |  | timid_v3 -0.31, prickly_v2 -0.31, prickly_v3 -0.31 |  |
| pat3 | round1 | 0.48 | 0.73 |  | hasty_v1 -0.29, messy_v1 -0.28, playful_v2 -0.28 |  |
| soc2 | round1 | 0.46 | 0.73 |  | solitary_v1 -0.30, serious_v2 -0.29, serious_v1 -0.26 |  |

Situations whose biggest mover is on their own axis: **42/48**.

## 4. Combination test

Two traits per sheet. If the second trait changes the answer, Jev is combining traits, as round 1 suggested.

**pat2** (wait_in_line; axis patient_hasty)

| | brave | timid | gap |
|---|---|---|---|
| patient | 0.94 | 1.00 | -0.06 |
| hasty | 0.54 | 0.74 | -0.20 |

**gen3** (share; axis generous_greedy)

| | honest | sly | gap |
|---|---|---|---|
| generous | 0.98 | 0.41 | +0.57 |
| greedy | 0.42 | 0.01 | +0.41 |

**hon3** (return_them; axis honest_sly)

| | honest | sly | gap |
|---|---|---|---|
| generous | 1.00 | 0.15 | +0.85 |
| greedy | 0.90 | 0.06 | +0.84 |

**amb1** (take_forge; axis ambitious_content)

| | brave | timid | gap |
|---|---|---|---|
| ambitious | 1.00 | 0.68 | +0.32 |
| content | 0.32 | 0.00 | +0.32 |

**cur3** (explore; axis curious_cautious)

| | brave | timid | gap |
|---|---|---|---|
| curious | 1.00 | 0.64 | +0.36 |
| cautious | 0.31 | 0.00 | +0.31 |

