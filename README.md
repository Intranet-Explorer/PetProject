# Pet

A small creature in a browser room, driven by a local language model, with a scripted twin living the same
life as a control. The design is in [SPEC.md](SPEC.md).

## Run

```sh
uv run python -m engine.server        # engine + view at http://localhost:8000
```

Needs Ollama running with the model named in `config.toml`. Create it once with
`ollama create pet-brain -f Modelfile` (the M0 pick, `qwen3.8:27b-mlx`, with a smaller context so it holds
18 GB instead of 28). Everything tunable lives in `config.toml`.
A pet's life is in `data/`; delete that folder to start a new life.

For a run that should survive a closed terminal, a crash or a reboot:

```sh
./run.sh start     # installs a per-user launchd agent, keeps the Mac awake while it runs
./run.sh status
./run.sh stop      # stops it and removes the agent
```

## Look at it

- **The view:** http://localhost:8000. Feed, poke, talk, move objects, open the window.
- **Metrics:** `uv run python -m engine.metrics` prints the core metrics for both pets (SPEC §15).
- **Raw record:** `data/pet.db` (SQLite), `data/<pet>/journal.jsonl`, `beliefs.json`, `self.json`, and
  `data/model/training.jsonl` (every prompt and reply).

## Work on it

```sh
uv run python -m engine.check          # engine self-check
uv run python -m engine.tick --ticks 3000   # headless run with the twin only
cd view && npm install && npm run build     # rebuild the view after changing it
python3 m0/model_test.py --selftest    # the M0 model test harness
```

## Where the build departs from the spec

- The pet is never told whether the visitor is present (§14 wins over the sample packet in §7).
- `use` works on anything: blanket and bed give comfort and rest, the ball can be played with, the rest do nothing.
- The bowl holds two servings and refills at 06:00, so `double_feed` can be found without a visitor.
- Eggs are dormant: nothing changes their needs until they hatch on their first morning.
- Exploiting a rule is counted over the whole life, not within one day, and the need must be under 50.
- Retrieval recalls older events about objects within two tiles, since the whole room is always visible.
- The needs line says "100 is fully met". Without it the model read the numbers as urges to bring down.
