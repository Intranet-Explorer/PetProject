# Pet

A small creature that lives in a browser room, driven by a local language model.

**[FINDINGS.md](FINDINGS.md) is the write-up of what has been learned so far.** The working spec is
[SPEC-v2.md](SPEC-v2.md); [SPEC.md](SPEC.md) is v1, kept for history. [NOTES.md](NOTES.md) is the account of
each life as it happened.

Built so far: V2.0 to V2.4 (intentions, 2-second ticks, a 10-minute egg, the room-first view, making things,
growth by useful things through to Adult, arrange, combine, paint, visitor gifts, taught behaviors, self-portraits).
V2.5, the long real-clock run, started on 8 Oct 2026; `NOTES.md` has what to look at.

## Run

```sh
uv run python -m engine.server        # engine + view at http://localhost:8000
```

Needs Ollama running with the model named in `config.toml`. Create it once with
`ollama create pet-brain -f Modelfile` (the M0 pick, `qwen3.8:27b-mlx`, with a smaller context so it holds
18 GB instead of 28). Everything tunable lives in `config.toml`.
A pet's life is in `data/`; move or delete that folder to start a new life.

For a run that should survive a closed terminal, a crash or a reboot:

```sh
./run.sh start     # installs a per-user launchd agent, keeps the Mac awake while it runs
./run.sh status
./run.sh stop      # stops it and removes the agent
```

## Look at it

- **The view:** http://localhost:8000. The room is the screen; "Mind and lab" opens a drawer with what it
  means to do, the things it has made (and what each really does), its diary, its beliefs, and the
  measurements. Feed, poke, talk, move objects, open the window.
- **Metrics:** `uv run python -m engine.metrics [data dir]` prints the core numbers, including model calls an hour.
- **Raw record:** `data/pet.db` (SQLite), `data/model/journal.jsonl`, `beliefs.json`, `self.json`, and
  `things.json` (everything it ever made), and `training.jsonl` (every prompt and reply).
- **The physics:** `materials.toml` holds what each material and hidden rule really does.

## Work on it

```sh
uv run python -m engine.check               # engine self-check
uv run python -m engine.tick --minutes 240  # a headless life with the scripted twin
cd view && npm install && npm run build     # rebuild the view after changing it
python3 m0/model_test.py --selftest         # the M0 model test harness
```

## Where the build reads the specs its own way

- **"Per tick" means per 10 seconds,** and the standing effects are a quarter of the spec's numbers. The pet
  thinks about seven times less often than in v1, so a light on at night costs 1 comfort per 10 s (the spec
  says 4 per tick) and warm or cool things give half a point. All of it is in `materials.toml`.
- **Steps take time** (`[steps]` in the config), and a step's effect lands when it completes. Walking is one tile a tick.
- **It thinks at most every 70 s** (`min_think_seconds`, not in the spec), which is what holds model calls
  under 60 an hour. A visitor's action, waking, hatching and a need falling under 30 are not made to wait
  that long; a need rising over 80 and a change of phase are.
- **An intention has 2 to 5 steps,** not 1 to 5: with one-step plans it stood idle most of the time.
- **A step's result separates what it did from what was happening anyway** ("you rested; energy +8.0;
  in the 44 s that took, apart from it: comfort -4.4"), so a long step does not look like the cause of the room's effects.
- **The pet has senses** (`[senses]` in the config, on by default). Its packet has a "you feel:" line naming what
  is acting on it right now and whether that is pleasant: "the warm nest beside you feels unpleasant", "the
  light in the room is harsh on you". The spec says the pet is told none of the physics. Two fast-clock lives
  showed it cannot work out an effect that comes from standing near one thing among seventeen, and it built a
  ring of warm things around itself that held its comfort at zero. A sensation says where, never why or when.
- **Novelty wears for good, not just for a while.** Each repeat of the same interaction is worth 0.8 of the
  last, down to a tenth. v1's novelty only recharged, which let the ten starting objects keep curiosity at 100
  forever; the first V2.3 life then made two things in 2.4 hours. Novelty goes by kind: making or using another
  thing of a material it already knows wears like a repeat, and a first of its kind is fully novel. Each night
  undoes two repeats of everything, and repeats stop counting at ten. From the fourth repeat the result says
  "(this has grown familiar)", and when curiosity is under 30 it feels "restless for something new".
- **A thing aimed at a taken tile is put on the nearest free one** and the pet is told where; the spec rejects
  it. The V2.3 life lost two of its first three makes that way.
- **A thing's size is its biggest part.** A new bright thing starts switched on. A sweet counts as a meal
  both ways for `double_feed`. A thing's name is lower-cased and must be unique in the room.
- **While a thought is in flight the pet stands still.** The new intention replaces the old one, which is
  scored as interrupted.
- **The twin, when enabled, lives in the same loop** with one-step intentions, not literally one action per tick.
- **Stages:** egg, hatchling, child, youngling, adult. Days lived are whole world days completed, so the Child
  check can first pass on the morning of day 3. A belief counts as kept for 2 days if it is still held and was
  first written at least 2 world days ago, revised since or not.
- **Behaviors, where the spec leaves them open** (`[behaviors]` in `materials.toml`): `visitor` means the visitor
  did something in the last minute (not that they are watching, which the pet is never told); `touched` lasts
  20 s after a use; `alone` is more than 3 tiles from the pet; `pet_resting` covers sleep. Glow makes a thing a
  light, dim makes it shelter from lights, hum is interesting to be near and bad to rest beside, bounce is
  mildly interesting, the two moves go one tile every other tick, and a colour change is only seen.
- **A self-portrait is parts only,** up to 8, with no name or material, drawn after that night's body change.
- **A "use" of a thing is any occasion it acted on the pet,** not only a `use` action: resting beside a quiet
  or noisy thing, a step spent beside a warm or cool one, or a dark one keeping a light's harm off. Otherwise
  a thing that works by being near could never count as useful.
- **Combining costs the base making energy** and puts the new thing where the first one stood.
- **A gift from the visitor is one shape of size 2,** named "gift N". The pet can use it but not take it apart,
  and it never counts toward growth.
- Carried over from v1: the pet is never told whether the visitor is present; `use` works on anything;
  the bowl holds two servings and refills at 06:00; the needs line says "100 is fully met"; retrieval
  recalls older events about objects within two tiles.
