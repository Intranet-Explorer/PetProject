# Pet

A small creature that lives in a browser room, driven by a local language model. The working spec is
[SPEC-v2.md](SPEC-v2.md); [SPEC.md](SPEC.md) is v1, kept for history. [NOTES.md](NOTES.md) says what was seen
at the end of each milestone.

Built so far: V2.0 and V2.1 (intentions, 2-second ticks, a 10-minute egg, the room-first view).
Not yet: making things, the later stages, behaviors (V2.2 onward).

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
  means to do, its diary, its beliefs, and the measurements. Feed, poke, talk, move objects, open the window.
- **Metrics:** `uv run python -m engine.metrics [data dir]` prints the core numbers, including model calls an hour.
- **Raw record:** `data/pet.db` (SQLite), `data/model/journal.jsonl`, `beliefs.json`, `self.json`, and
  `training.jsonl` (every prompt and reply).

## Work on it

```sh
uv run python -m engine.check               # engine self-check
uv run python -m engine.tick --minutes 240  # a headless life with the scripted twin
cd view && npm install && npm run build     # rebuild the view after changing it
python3 m0/model_test.py --selftest         # the M0 model test harness
```

## Where the build reads the specs its own way

- **"Per tick" means per 10 seconds.** The rules were tuned for v1's 10 s tick. With a 2 s tick they run at the
  same real-time speed: a light on at night costs 4 comfort per 10 s, not per tick.
- **Steps take time** (`[steps]` in the config), and a step's effect lands when it completes. Walking is one tile a tick.
- **It thinks at most every 75 s** (`min_think_seconds`, not in the spec), which is what holds model calls
  between 20 and 48 an hour. A visitor's action, waking and hatching are not made to wait; a need crossing
  30 or 80 and a change of phase are.
- **While a thought is in flight the pet stands still.** The new intention replaces the old one, which is
  scored as interrupted.
- **The twin, when enabled, lives in the same loop** with one-step intentions, not literally one action per tick.
- **Stages:** egg and hatchling only until V2.3. The v1 Child gate is gone.
- Carried over from v1: the pet is never told whether the visitor is present; `use` works on anything;
  the bowl holds two servings and refills at 06:00; the needs line says "100 is fully met"; retrieval
  recalls older events about objects within two tiles.
