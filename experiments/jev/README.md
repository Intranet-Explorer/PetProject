# The personality tests: files

Nine rounds of tests on how a written character sheet changes what a model decides. The write-up is
[docs/JEV.md](../../docs/JEV.md).

| folder | what it asked | calls |
|---|---|---|
| round1 | Do ten traits on a sheet steer decisions at all? | 540 |
| round2 | How much does wording matter, and do traits leak onto each other? | 3,496 |
| round3 | Can a line override the traits: a thief, a hermit, a hob coming apart? | 5,254 |
| round4 | Motive against behaviour, a record that grows, lines made at random | 15,642 |
| round5 | Relationships, roles, states, intensity, dilution | 18,683 |
| round6 | 300 random hobs: which kinds of line change behaviour, and does smartness? | 19,177 |
| round7 | 360 random hobs: values, fears, quirks, defects, age | 26,353 |
| round8 | 340 random hobs: is every one distinct, and does a long sheet still work? | 32,054 |
| round9 | The hobs' own model choosing among the house's real options | 1,022 |

Each folder holds the script (`run*.py`), the situations and sheets it used (`*.json`), the report (`report.md`)
and the summary tables (`*.csv`). The raw per-call results are left out for size.

Rounds 1 to 8 call `typesafe/jev-1.14` through OpenRouter and read the key from `OPENROUTER_API_KEY`. Each
script has a `--mock` mode that runs without a key. Round 9 calls a local model.

`charts.py` draws the charts in `docs/img` from numbers copied out of the reports.
