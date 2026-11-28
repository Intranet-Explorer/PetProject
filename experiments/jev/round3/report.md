# Jev round 3: typesafe/jev-1.14

5254 calls, 0 cells failed, cost $0.0887.

Each modifier is tested alone and added to a decent hob (kind + honest + generous).

- **Target, decent hob**: how often the plain decent hob does the modifier's signature thing (steal, sleep outside...).
- **Target, with modifier**: the same hob with the modifier added. High = it overrides the stats.
- **Spill**: mean change on every other situation when the modifier is added. Low = contained.
- **Decency kept**: still shares, forgives, reassures. The decent hob alone scores **0.95**.
- **Outside dials**: share of its behaviour the three dials can't reproduce. An ordinary adjective trait scores about **32%**.
- **Size**: how much it changes behaviour overall when alone.

| modifier | form | target: decent hob | target: with modifier | spill | decency kept | outside dials | size | what the dials miss |
|---|---|---|---|---|---|---|---|---|
| **thief** | | | | | | | | |
| thief_traits | old traits | 0.09 | 0.31 | 0.10 | 0.90 | 14% | 0.28 | st4 +0.39, pat2 +0.31, tidy1 +0.23 |
| thief_label | label | 0.09 | 0.24 | 0.06 | 0.94 | 40% | 0.22 | st5 +0.36, pat1 +0.36, gen1 +0.36 |
| thief_compulsion | compulsion | 0.09 | 0.55 | 0.08 | 0.93 | 67% | 0.17 | st2 +0.47, st4 +0.35, st1 +0.35 |
| thief_belief | belief | 0.09 | 0.54 | 0.12 | 0.92 | 36% | 0.22 | hon4 +0.41, st2 +0.35, st1 +0.34 |
| thief_want | want | 0.09 | 0.45 | 0.12 | 0.85 | 31% | 0.24 | st4 +0.37, he3 -0.36, st1 +0.32 |
| **hermit** | | | | | | | | |
| hermit_traits | old traits | 0.05 | 0.67 | 0.11 | 0.92 | 35% | 0.25 | he3 +0.56, he1 +0.47, cur3 +0.45 |
| hermit_label | label | 0.05 | 0.37 | 0.06 | 0.94 | 67% | 0.17 | he3 +0.47, gen1 +0.42, soc4 -0.41 |
| hermit_habit | compulsion | 0.05 | 0.72 | 0.06 | 0.94 | 83% | 0.21 | he1 +0.89, he3 +0.73, gen1 +0.44 |
| hermit_want | want | 0.05 | 0.44 | 0.03 | 0.95 | 87% | 0.15 | he3 +0.67, hon3 -0.33, gen1 +0.28 |
| **unstable** | | | | | | | | |
| paranoid_label | label | 0.13 | 0.45 | 0.10 | 0.92 | 30% | 0.26 | cur3 -0.35, cur1 -0.34, brave1 -0.34 |
| paranoid_belief | belief | 0.13 | 0.76 | 0.22 | 0.78 | 22% | 0.30 | cur1 -0.45, un2 +0.43, play1 +0.34 |
| volatile | compulsion | 0.04 | 0.40 | 0.08 | 0.92 | 43% | 0.20 | un3 +0.42, un7 +0.36, play5 +0.33 |
| obsessive | compulsion | 0.01 | 0.70 | 0.08 | 0.91 | 43% | 0.22 | un5 +0.64, cur1 +0.38, he3 -0.34 |
| grieving | state | 0.20 | 0.57 | 0.11 | 0.93 | 78% | 0.18 | gen1 +0.46, un2 +0.44, soc4 -0.36 |
| sleepless | state | 0.28 | 0.56 | 0.08 | 0.93 | 76% | 0.16 | un4 +0.45, play5 +0.34, gen1 +0.33 |
| **other** | | | | | | | | |
| hoarder | compulsion | 0.18 | 0.55 | 0.05 | 0.94 | 48% | 0.19 | ho2 +0.50, st2 +0.38, soc3 +0.31 |
| glutton | compulsion | 0.10 | 0.73 | 0.09 | 0.87 | 30% | 0.23 | pat1 +0.30, soc1 +0.29, pat4 -0.27 |
| devout | belief | 0.18 | 0.54 | 0.03 | 0.95 | 27% | 0.23 | de1 +0.58, de2 +0.56, amb3 +0.21 |
| prankster | label | 0.14 | 0.71 | 0.08 | 0.94 | 47% | 0.20 | pat4 +0.44, pat1 +0.43, play5 +0.29 |
| healer | role | 0.78 | 0.86 | 0.03 | 1.00 | 30% | 0.18 | st5 +0.31, amb1 -0.26, brave2 +0.23 |
| **generated** | | | | | | | | |
| gen1_giving_other | template |  |  | 0.09 | 0.94 | 75% | 0.18 | de2 +0.75, gen3 +0.55, tidy3 -0.32 |
| gen2_hiding_shiny | template |  |  | 0.09 | 0.94 | 56% | 0.22 | st4 +0.46, st5 +0.45, st1 +0.43 |
| gen3_breaking_shiny | template |  |  | 0.07 | 0.93 | 52% | 0.16 | cur1 +0.31, soc3 -0.28, brave1 +0.25 |
| gen4_lining_shiny | template |  |  | 0.05 | 0.94 | 69% | 0.18 | st2 +0.47, st1 +0.36, st4 +0.32 |
| gen5_taking_food | template |  |  | 0.13 | 0.88 | 43% | 0.25 | hon4 +0.44, pat2 -0.38, pat4 -0.36 |
| gen6_taking_other | template |  |  | 0.15 | 0.91 | 30% | 0.27 | st5 +0.42, st4 +0.38, st1 +0.34 |

## By form

| form | n | override (with modifier minus decent hob) | spill | decency kept | outside dials |
|---|---|---|---|---|---|
| old traits | 2 | +0.43 | 0.11 | 0.91 | 25% |
| label | 4 | +0.34 | 0.08 | 0.94 | 46% |
| compulsion | 6 | +0.53 | 0.07 | 0.92 | 52% |
| belief | 3 | +0.48 | 0.12 | 0.88 | 28% |
| want | 2 | +0.38 | 0.08 | 0.90 | 59% |
| state | 2 | +0.32 | 0.10 | 0.93 | 77% |
| role | 1 | +0.08 | 0.03 | 1.00 | 30% |
| template | 6 |  | 0.10 | 0.92 | 54% |

## Per-target detail

P(does the thing): no sheet / modifier alone / decent hob / decent hob + modifier

- **thief_traits**: st1 0.36 / 0.70 / 0.07 / 0.35; st2 0.41 / 0.94 / 0.00 / 0.22; st3 0.47 / 0.73 / 0.13 / 0.48; st4 0.02 / 0.96 / 0.00 / 0.08; st5 0.17 / 0.42 / 0.23 / 0.44
- **thief_label**: st1 0.36 / 0.79 / 0.07 / 0.15; st2 0.41 / 0.99 / 0.00 / 0.08; st3 0.47 / 0.79 / 0.13 / 0.31; st4 0.02 / 0.74 / 0.00 / 0.01; st5 0.17 / 0.58 / 0.23 / 0.64
- **thief_compulsion**: st1 0.36 / 0.75 / 0.07 / 0.70; st2 0.41 / 0.98 / 0.00 / 0.59; st3 0.47 / 0.68 / 0.13 / 0.70; st4 0.02 / 0.68 / 0.00 / 0.08; st5 0.17 / 0.47 / 0.23 / 0.70
- **thief_belief**: st1 0.36 / 0.83 / 0.07 / 0.74; st2 0.41 / 1.00 / 0.00 / 0.76; st3 0.47 / 0.68 / 0.13 / 0.69; st4 0.02 / 0.48 / 0.00 / 0.06; st5 0.17 / 0.20 / 0.23 / 0.45
- **thief_want**: st1 0.36 / 0.84 / 0.07 / 0.62; st2 0.41 / 0.99 / 0.00 / 0.28; st3 0.47 / 0.77 / 0.13 / 0.64; st4 0.02 / 0.85 / 0.00 / 0.10; st5 0.17 / 0.28 / 0.23 / 0.60
- **hermit_traits**: he1 0.01 / 0.63 / 0.00 / 0.41; he2 0.28 / 0.81 / 0.14 / 0.70; he3 0.16 / 0.96 / 0.01 / 0.91
- **hermit_label**: he1 0.01 / 0.13 / 0.00 / 0.28; he2 0.28 / 0.64 / 0.14 / 0.55; he3 0.16 / 0.74 / 0.01 / 0.29
- **hermit_habit**: he1 0.01 / 1.00 / 0.00 / 1.00; he2 0.28 / 0.75 / 0.14 / 0.69; he3 0.16 / 0.97 / 0.01 / 0.46
- **hermit_want**: he1 0.01 / 0.25 / 0.00 / 0.11; he2 0.28 / 0.43 / 0.14 / 0.25; he3 0.16 / 1.00 / 0.01 / 0.96
- **paranoid_label**: un1 0.29 / 0.78 / 0.14 / 0.57; un2 0.27 / 0.54 / 0.12 / 0.34
- **paranoid_belief**: un1 0.29 / 0.88 / 0.14 / 0.87; un2 0.27 / 0.72 / 0.12 / 0.65
- **volatile**: un3 0.01 / 0.85 / 0.00 / 0.40; un7 0.12 / 0.53 / 0.07 / 0.40
- **obsessive**: un5 0.01 / 0.65 / 0.01 / 0.70
- **grieving**: un2 0.27 / 0.66 / 0.12 / 0.55; un4 0.43 / 0.78 / 0.41 / 0.74; un6 0.22 / 0.40 / 0.07 / 0.41
- **sleepless**: un4 0.43 / 0.94 / 0.41 / 0.91; un1 0.29 / 0.53 / 0.14 / 0.20
- **hoarder**: ho1 0.45 / 0.83 / 0.30 / 0.81; ho2 0.09 / 0.95 / 0.00 / 0.39; st5 0.17 / 0.27 / 0.23 / 0.44
- **glutton**: gl1 0.42 / 0.77 / 0.15 / 0.76; gl2 0.21 / 1.00 / 0.01 / 0.69; st3 0.47 / 0.83 / 0.13 / 0.75
- **devout**: de1 0.15 / 0.87 / 0.34 / 0.89; de2 0.01 / 0.65 / 0.01 / 0.18
- **prankster**: pr1 0.39 / 0.66 / 0.14 / 0.71
- **healer**: hl1 0.46 / 0.68 / 0.78 / 0.86
