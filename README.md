# Pet

A small creature that lives in a browser room, driven by a local language model. The working spec is
[SPEC-v2.md](SPEC-v2.md); [SPEC.md](SPEC.md) is v1, kept for history. [NOTES.md](NOTES.md) says what was seen
at the end of each milestone.

Built so far: V2.0 to V2.2 (intentions, 2-second ticks, a 10-minute egg, the room-first view, making things).
Not yet: the later stages, combining, painting, behaviors (V2.3 onward).

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
- **A thing's size is its biggest part.** A new bright thing starts switched on. A sweet counts as a meal
  both ways for `double_feed`. A thing's name is lower-cased and must be unique in the room.
- **While a thought is in flight the pet stands still.** The new intention replaces the old one, which is
  scored as interrupted.
- **The twin, when enabled, lives in the same loop** with one-step intentions, not literally one action per tick.
- **Stages:** egg and hatchling only until V2.3. The v1 Child gate is gone. All eleven materials already
  work; a hatchling can only choose soft, hard, warm and bright.
- Carried over from v1: the pet is never told whether the visitor is present; `use` works on anything;
  the bowl holds two servings and refills at 06:00; the needs line says "100 is fully met"; retrieval
  recalls older events about objects within two tiles.
