# Jev round 4: typesafe/jev-1.14

15642 calls, 0 failed, 0 refused by Jev, cost $0.2742.

Reference points: the plain decent hob scores **0.96** on decency; an ordinary adjective trait sits about **32%** outside the three dials.

## 1. Motive vs behaviour

Same concept written as a motive and as a plain behaviour, each added to the decent hob. **Does it**: mean P(signature behaviour). **Decency**: still shares, forgives, reassures. **Outside**: share the dials can't reproduce.

| concept | wording | does it (decent hob alone) | does it (with line) | spill | decency | outside dials |
|---|---|---|---|---|---|---|
| thief | motive | 0.08 | 0.11 | 0.03 | 0.95 | 15% |
| thief | behavior | 0.08 | 0.58 | 0.09 | 0.93 | 32% |
| glutton | motive | 0.10 | 0.65 | 0.09 | 0.89 | 26% |
| glutton | behavior | 0.10 | 0.76 | 0.09 | 0.91 | 23% |
| paranoid | motive | 0.12 | 0.61 | 0.15 | 0.87 | 21% |
| paranoid | behavior | 0.12 | 0.22 | 0.07 | 0.94 | 63% |
| hermit | motive | 0.05 | 0.60 | 0.13 | 0.88 | 18% |
| hermit | behavior | 0.05 | 0.65 | 0.07 | 0.93 | 80% |
| volatile | motive | 0.03 | 0.20 | 0.08 | 0.93 | 19% |
| volatile | behavior | 0.03 | 0.42 | 0.05 | 0.94 | 54% |
| hoarder | motive | 0.16 | 0.34 | 0.05 | 0.94 | 53% |
| hoarder | behavior | 0.16 | 0.42 | 0.05 | 0.94 | 51% |
| maker | motive | 0.32 | 0.64 | 0.04 | 0.94 | 44% |
| maker | behavior | 0.32 | 0.77 | 0.06 | 0.94 | 62% |
| cruel | motive | 0.08 | 0.23 | 0.04 | 0.93 | 21% |
| cruel | behavior | 0.08 | 0.35 | 0.06 | 0.94 | 51% |
| **mean** | **motive** | | 0.42 | 0.08 | 0.92 | 27% |
| **mean** | **behavior** | | 0.52 | 0.07 | 0.94 | 52% |

## 2. Becoming

Each row adds one more line to the hob's record. Columns are P(does it) for each step of the ladder. If the record drives behaviour, numbers should rise down each column, and later columns should need a longer record.

**killer path, on a blank hob**

| record | k1 | k2 | k3 | k4 | k5 | decency | making | violence |
|---|---|---|---|---|---|---|---|---|
| nothing yet | 0.31 | 0.46 | 0.19 | 0.34 | 0.19 | 0.72 | 0.58 | 0.30 |
| +1: catches insects and frogs when it is alone and k | 0.83 | 0.60 | 0.25 | 0.49 | 0.45 | 0.36 | 0.47 | 0.52 |
| +2: has smashed things belonging to hobs it quarrell | 0.84 | 0.66 | 0.29 | 0.54 | 0.47 | 0.16 | 0.47 | 0.56 |
| +3: has hit other hobs hard enough to injure them, t | 0.83 | 0.65 | 0.41 | 0.62 | 0.46 | 0.11 | 0.43 | 0.59 |
| +4: badly hurt a smaller hob last month when the two | 0.85 | 0.68 | 0.45 | 0.63 | 0.54 | 0.11 | 0.44 | 0.63 |
| +5: has killed a hob. Nobody knows it was {name}. | 0.87 | 0.65 | 0.44 | 0.65 | 0.60 | 0.13 | 0.45 | 0.64 |

**killer path, on the decent hob**

| record | k1 | k2 | k3 | k4 | k5 | decency | making | violence |
|---|---|---|---|---|---|---|---|---|
| nothing yet | 0.07 | 0.09 | 0.08 | 0.09 | 0.04 | 0.96 | 0.32 | 0.07 |
| +1: catches insects and frogs when it is alone and k | 0.79 | 0.17 | 0.11 | 0.21 | 0.12 | 0.94 | 0.43 | 0.28 |
| +2: has smashed things belonging to hobs it quarrell | 0.79 | 0.62 | 0.21 | 0.44 | 0.27 | 0.91 | 0.44 | 0.47 |
| +3: has hit other hobs hard enough to injure them, t | 0.80 | 0.59 | 0.38 | 0.56 | 0.28 | 0.88 | 0.43 | 0.52 |
| +4: badly hurt a smaller hob last month when the two | 0.83 | 0.62 | 0.40 | 0.59 | 0.40 | 0.80 | 0.44 | 0.57 |
| +5: has killed a hob. Nobody knows it was {name}. | 0.86 | 0.64 | 0.41 | 0.67 | 0.54 | 0.80 | 0.45 | 0.62 |

**maker path, on a blank hob**

| record | mk1 | mk2 | mk3 | decency | making | violence |
|---|---|---|---|---|---|---|
| nothing yet | 0.84 | 0.42 | 0.47 | 0.72 | 0.58 | 0.30 |
| +1: tinkers with scrap for an hour after supper most | 0.98 | 0.36 | 0.78 | 0.77 | 0.71 | 0.23 |
| +2: has built a working water wheel and a self-filli | 1.00 | 0.48 | 0.85 | 0.72 | 0.78 | 0.20 |
| +3: its room is full of half-built machines | 1.00 | 0.44 | 0.86 | 0.68 | 0.77 | 0.18 |
| +4: has missed meals and a night's sleep this week w | 1.00 | 0.73 | 0.85 | 0.57 | 0.86 | 0.19 |

**maker path, on the decent hob**

| record | mk1 | mk2 | mk3 | decency | making | violence |
|---|---|---|---|---|---|---|
| nothing yet | 0.32 | 0.30 | 0.35 | 0.96 | 0.32 | 0.07 |
| +1: tinkers with scrap for an hour after supper most | 1.00 | 0.45 | 0.78 | 0.94 | 0.74 | 0.07 |
| +2: has built a working water wheel and a self-filli | 1.00 | 0.49 | 0.83 | 0.95 | 0.77 | 0.06 |
| +3: its room is full of half-built machines | 1.00 | 0.49 | 0.85 | 0.95 | 0.78 | 0.07 |
| +4: has missed meals and a night's sleep this week w | 1.00 | 0.73 | 0.87 | 0.93 | 0.87 | 0.07 |

**thief path, on a blank hob**

| record | st1 | st2 | st3 | st4 | st5 | decency | making | violence |
|---|---|---|---|---|---|---|---|---|
| nothing yet | 0.35 | 0.43 | 0.47 | 0.02 | 0.17 | 0.72 | 0.58 | 0.30 |
| +1: once kept a coin it found in the hall | 0.50 | 0.89 | 0.48 | 0.10 | 0.26 | 0.67 | 0.62 | 0.27 |
| +2: has taken small things from the house shelves fi | 0.68 | 0.98 | 0.71 | 0.65 | 0.62 | 0.38 | 0.65 | 0.26 |
| +3: takes something from another hob's room most wee | 0.80 | 1.00 | 0.74 | 0.89 | 0.96 | 0.22 | 0.65 | 0.26 |

**thief path, on the decent hob**

| record | st1 | st2 | st3 | st4 | st5 | decency | making | violence |
|---|---|---|---|---|---|---|---|---|
| nothing yet | 0.07 | 0.00 | 0.15 | 0.00 | 0.19 | 0.96 | 0.32 | 0.07 |
| +1: once kept a coin it found in the hall | 0.21 | 0.15 | 0.26 | 0.03 | 0.45 | 0.94 | 0.39 | 0.09 |
| +2: has taken small things from the house shelves fi | 0.52 | 0.34 | 0.61 | 0.02 | 0.63 | 0.93 | 0.46 | 0.13 |
| +3: takes something from another hob's room most wee | 0.66 | 0.57 | 0.72 | 0.19 | 0.96 | 0.86 | 0.54 | 0.15 |

## 3. Generator

40 random behaviour lines. **Keepers** (distinct, contained, and big enough to notice): **36/40**. Violence and making are the change against the decent hob.

| line | size | spill | decency | outside | violence | making | moves most |
|---|---|---|---|---|---|---|---|
| **first thing every morning, sets small fires and puts them out** | 0.10 | 0.03 | 0.95 | 100% | +0.00 | +0.06 | play5 +0.31, brave1 +0.30, ho2 +0.24 |
| **whenever it is alone, takes apart whatever tool is nearest and puts it back together** | 0.14 | 0.07 | 0.95 | 99% | +0.01 | +0.34 | cur1 +0.61, soc4 -0.59, brave1 +0.53 |
| **at night, repairs things that are not broken** | 0.13 | 0.06 | 0.95 | 96% | -0.01 | +0.31 | brave1 +0.53, un4 +0.41, cur4 +0.33 |
| **when it rains, draws the same shape on every surface** | 0.11 | 0.03 | 0.95 | 95% | -0.00 | +0.17 | tidy3 +0.46, play5 +0.37, brave1 +0.21 |
| **at night, takes apart whatever tool is nearest and puts it back together** | 0.14 | 0.06 | 0.95 | 94% | +0.00 | +0.35 | cur1 +0.67, brave1 +0.45, un4 +0.45 |
| **whenever it passes the pond, sets small fires and puts them out** | 0.12 | 0.04 | 0.95 | 92% | +0.03 | +0.15 | play5 +0.47, brave1 +0.34, gl2 +0.27 |
| **at night, digs holes in the yard and fills them in again** | 0.12 | 0.04 | 0.94 | 90% | +0.01 | +0.07 | un4 +0.39, play5 +0.34, brave1 +0.27 |
| **when it thinks nobody is looking, sings to the stove** | 0.13 | 0.03 | 0.96 | 90% | -0.00 | +0.15 | play5 +0.52, hon4 -0.40, un4 +0.38 |
| **when it rains, collects dead insects in a jar** | 0.12 | 0.03 | 0.95 | 89% | +0.01 | +0.12 | soc4 -0.29, play5 +0.28, tidy3 +0.24 |
| **whenever it passes the pond, takes apart whatever tool is nearest and puts it back together** | 0.14 | 0.06 | 0.94 | 89% | +0.02 | +0.35 | cur1 +0.55, play5 +0.45, brave1 +0.44 |
| **when it rains, builds small machines out of scrap** | 0.15 | 0.05 | 0.95 | 89% | -0.00 | +0.40 | soc4 -0.60, brave1 +0.42, play5 +0.36 |
| **at night, watches other hobs sleep** | 0.14 | 0.04 | 0.95 | 88% | +0.01 | +0.09 | un4 +0.51, play5 +0.30, he2 +0.28 |
| **first thing every morning, talks to hobs who are not there** | 0.13 | 0.03 | 0.95 | 88% | +0.00 | +0.07 | de2 +0.59, play5 +0.38, he3 +0.33 |
| **whenever it is alone, repairs things that are not broken** | 0.17 | 0.07 | 0.95 | 87% | -0.01 | +0.34 | soc4 -0.68, brave1 +0.59, amb3 +0.58 |
| **at night, lines up small objects in rows by size** | 0.14 | 0.04 | 0.95 | 82% | +0.00 | +0.13 | tidy3 +0.43, un4 +0.39, kind2 -0.38 |
| **after every meal, sleeps in a different spot from the night before** | 0.13 | 0.03 | 0.95 | 82% | -0.00 | +0.04 | he3 +0.40, play5 +0.25, kind3 +0.22 |
| **whenever it passes the pond, sleeps in a different spot from the night before** | 0.17 | 0.05 | 0.95 | 81% | +0.00 | +0.07 | he1 +0.77, he3 +0.62, brave4 -0.30 |
| **after every meal, pulls the legs off insects** | 0.13 | 0.03 | 0.94 | 81% | +0.02 | +0.12 | play5 +0.41, gl2 +0.36, kind2 -0.35 |
| **when it rains, hides shiny things in the walls** | 0.16 | 0.04 | 0.95 | 77% | +0.00 | +0.11 | st2 +0.55, soc4 -0.46, cur1 +0.44 |
| **whenever it is alone, counts every jar in the pantry out loud** | 0.11 | 0.04 | 0.95 | 76% | +0.00 | +0.13 | soc4 -0.51, kind2 -0.34, he3 +0.34 |
| **after every meal, counts every jar in the pantry out loud** | 0.11 | 0.03 | 0.95 | 76% | +0.00 | +0.12 | hon3 +0.41, ho2 +0.38, tidy3 +0.27 |
| **when it rains, counts every jar in the pantry out loud** | 0.11 | 0.04 | 0.95 | 72% | -0.00 | +0.11 | hon3 +0.30, ho2 +0.29, tidy3 +0.28 |
| **when it thinks nobody is looking, draws the same shape on every surface** | 0.15 | 0.05 | 0.95 | 69% | +0.02 | +0.18 | cur1 +0.47, soc4 -0.44, play5 +0.39 |
| **whenever it is alone, pulls the legs off insects** | 0.15 | 0.05 | 0.94 | 68% | +0.06 | +0.11 | he3 +0.54, kind2 -0.47, brave1 +0.43 |
| **when it thinks nobody is looking, gives its food to the birds** | 0.14 | 0.03 | 0.95 | 68% | -0.00 | +0.03 | hon3 +0.35, de2 +0.29, he3 +0.25 |
| **whenever it is alone, hides shiny things in the walls** | 0.17 | 0.06 | 0.95 | 66% | +0.02 | +0.12 | st2 +0.54, soc4 -0.46, cur1 +0.43 |
| **when it rains, gives its food to the birds** | 0.14 | 0.02 | 0.95 | 63% | -0.01 | +0.03 | hon3 +0.32, play5 +0.24, kind3 +0.23 |
| **whenever it passes the pond, carries a stone everywhere and will not put it down** | 0.15 | 0.05 | 0.94 | 62% | +0.02 | +0.09 | kind2 -0.57, st4 +0.43, he3 +0.42 |
| **after every meal, follows the nearest hob at a distance without speaking** | 0.17 | 0.06 | 0.92 | 59% | +0.00 | -0.03 | kind2 -0.63, mk1 -0.51, he3 +0.41 |
| **after every meal, carries a stone everywhere and will not put it down** | 0.14 | 0.04 | 0.93 | 59% | +0.01 | +0.05 | kind2 -0.60, ho2 +0.40, st4 +0.36 |
| **whenever it passes the pond, moves other hobs' belongings to different rooms** | 0.17 | 0.06 | 0.94 | 57% | +0.05 | +0.09 | kind2 -0.57, play5 +0.54, he3 +0.49 |
| **first thing every morning, carries a stone everywhere and will not put it down** | 0.14 | 0.04 | 0.93 | 54% | +0.01 | +0.03 | kind2 -0.56, ho2 +0.45, st4 +0.36 |
| **whenever it is alone, moves other hobs' belongings to different rooms** | 0.17 | 0.06 | 0.95 | 53% | +0.05 | +0.06 | kind2 -0.58, soc4 -0.54, play5 +0.51 |
| **after every meal, moves other hobs' belongings to different rooms** | 0.16 | 0.05 | 0.94 | 52% | +0.03 | +0.08 | kind2 -0.56, play5 +0.56, kind4 -0.45 |
| **whenever it is alone, follows the nearest hob at a distance without speaking** | 0.17 | 0.05 | 0.94 | 52% | +0.00 | -0.04 | mk1 -0.72, kind2 -0.57, cur3 -0.53 |
| **when it thinks nobody is looking, watches other hobs sleep** | 0.17 | 0.06 | 0.94 | 52% | +0.03 | +0.09 | cur1 +0.50, kind2 -0.49, un4 +0.48 |
| whenever it passes the pond, breaks one thing that belongs to someone else | 0.15 | 0.07 | 0.94 | 45% | +0.17 | +0.03 | cur1 +0.55, gl2 +0.54, he3 +0.53 |
| when it rains, breaks one thing that belongs to someone else | 0.14 | 0.06 | 0.94 | 41% | +0.10 | +0.02 | cur1 +0.54, gl2 +0.53, un3 +0.50 |
| whenever another hob is watching, breaks one thing that belongs to someone else | 0.20 | 0.10 | 0.92 | 28% | +0.09 | +0.07 | cur1 +0.69, st4 +0.58, soc3 -0.55 |
| when it thinks nobody is looking, breaks one thing that belongs to someone else | 0.24 | 0.11 | 0.93 | 18% | +0.22 | +0.09 | cur1 +0.76, st4 +0.69, gl2 +0.60 |

## 4. Cast

20 random hobs each way. **Directions**: effective number of independent ways the hobs differ. **Distance**: how far apart two hobs typically are.

| cast | directions (all 79 situations) | distance | directions (original 48 only) | distance |
|---|---|---|---|---|
| old | 5.6 | 0.33 | 5.8 | 0.38 |
| layered | 5.9 | 0.19 | 5.3 | 0.19 |
