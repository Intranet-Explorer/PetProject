# Pet

A family of small creatures living in a house in the browser, each driven by a local language model. They
hatch, grow, grow old and die; they lay eggs and leave their children a body, a temperament, a message and a
thing or two. The house has nine rooms behind doors, weather, seasons, power cuts and a few small animals.

- **[SHOWCASE.md](SHOWCASE.md)**: four families from one message, with screenshots and the evidence for each
  thing it was built to show, and what it did not show. The fourth family is the one living in `data/` now.
- **[FINDINGS.md](FINDINGS.md)**: what has been learned, from the first model test to v3.
- **[SPEC-v3.md](SPEC-v3.md)** is the working spec; [SPEC-v2.md](SPEC-v2.md) and [SPEC.md](SPEC.md) are kept for
  history. **[DECISIONS.md](DECISIONS.md)** lists every place the build reads the spec its own way, and why.
  [NOTES.md](NOTES.md) is the account of the v1 and v2 lives as they happened; [VOICE.md](VOICE.md) is the voice.

## Run

```sh
./run.sh start live     # the family living in data/: a world day is one real hour, a life about sixteen
./run.sh status
./run.sh stop
```

This installs a per-user launchd agent that keeps the Mac awake and brings the engine back after a crash or a
reboot. The view is at http://localhost:8000. It needs Ollama running with the model named in `config.toml`;
create it once with `ollama create pet-brain -f Modelfile` (`qwen3.8:27b-mlx` with a 16k context).

To run it in a terminal instead: `uv run python -m engine.server`.

The house and everyone in it live in `data/`. A family's log is `data/lineage-N/lineage.db`; each pet has a
folder beside it with its journal, beliefs, life record and every prompt it was ever given (`training.jsonl`).
When a family dies out the view offers to start another in the same house. To start a new house, archive
`data/` under another name.

**Profiles** are laid over `config.toml`. A house keeps to the world clock it was made on: the living family
was made on the showcase's, so it is started with `live` (or `showcase`), never with no profile.

| | |
|---|---|
| `./run.sh start live` | `config.live.toml`: the showcase's lives (a world day is 900 ticks, a life about 16 days) shown at one world day to the real hour. The house in `data/`. |
| `./run.sh start` | `config.toml` alone, for a new house: a world day is two real hours, a life about two days. |
| `./run.sh start showcase` | `config.showcase.toml`: short lives in turbo time (the world waits while the model thinks and otherwise runs straight on). About seven or eight real hours for five generations. Watch it afterwards with Replay. |
| `PET_PROFILE=viewdev PET_DATA=data.viewdev PET_PORT=8002 uv run python -m engine.server` | scripted brains on a quick clock, for working on the view |
| `PET_PROFILE=showcase PET_DATA=data.showcase-3 PET_PAUSED=1 PET_PORT=8001 uv run python -m engine.server` | open an archived run (`data.showcase-1` to `-4`) to look at and replay (http://localhost:8001/?replay=1); nothing in it moves |

## Look at it

- **The house:** the room being followed fills the screen; the map beside it shows every room found so far and
  who is where. Click a room to look at it, a pet to follow it, or leave "Follow" on "whatever is happening".
- **Mind and lab** opens a drawer: **Mind** (how the selected pet feels, what it notices, what it means to do,
  what its parent told it, what it believes and where each belief came from), **Things**, **Family** (the tree,
  life records, family sayings and heirlooms), **Story** (the chronicle and each day's moments), **Lab** (the
  numbers the pets never see, and the voice lab).
- **You are the visitor**, in whichever room you are looking at: feed, talk, give a bit, move things, poke,
  open the window, name a pet or a thing.
- **Replay** plays back any recorded day of any family at up to 60×.
- **Sound** is off until you click "Sound off". Every voice is made in the browser from the pet's body, so
  families sound alike; no pet ever hears it.

## Work on it

```sh
uv run python -m engine.check               # the engine's self-check (about two minutes, no model)
uv run python -m engine.tick --days 40      # a headless lineage with scripted brains
uv run python -m engine.metrics [data dir]  # the Lab's numbers for a run
uv run python -m engine.showcase [data dir] # the evidence for SPEC-v3 §12's bar, from a run's logs
cd view && npm install && npm run build     # rebuild the view; the running engine serves it as is
node view/check-voice.ts                    # the voice's self-check (no browser, no sound)
```

Everything tunable is in `config.toml` (the engine), `house.toml` (rooms, bits, weather, events, creatures)
and `materials.toml` (what each property of a made thing does). The pets are told none of the numbers in any
of them.

## What a pet is given

A page of plain words, a few times a minute at most: the time and weather, how it feels (four needs as
feelings, never numbers), what it notices, what and who is in the room, what just happened, what was said to
it, its project, what its parent told it, its beliefs, and what it can do. It answers with a thought, an
intention of two to five steps, and what it expects to feel afterwards; the engine carries the steps out and
scores the expectation. Nothing tells it what it is. `Mind` in the drawer shows the page as the pet saw it.
