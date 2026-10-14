# Running Pet

How to run, watch and work on the house. What the project is: [README.md](README.md).

Other docs: [DECISIONS.md](DECISIONS.md) (every place the build reads a spec its own way), [NOTES.md](NOTES.md)
(the v1 and v2 lives as they happened), [VOICE.md](VOICE.md) (the voice), and the specs from [SPEC.md](SPEC.md) to
[SPEC-v3.3.md](SPEC-v3.3.md).

## Run

```sh
./run.sh start live     # the family living in data/: a world day is two real hours, a life about sixteen
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

**The art is data.** Everything the house looks and sounds like is described by files in `view/assets/`: the
asset packs, a name for every picture, the catalog of kinds a pet can make, a hand-made layout for each room type,
and the sounds. The code names no tile and no pack. [view/assets/README.md](view/assets/README.md) gives the
formats and how to add a pack: put its zip in `assets-incoming/` (not in the repository) and map its pieces to
names there. `view/assets/third_party/CREDITS.md` credits what is used.

**The book** reads `book/wikipedia_en-simple_all_maxi_2026-09.zim` (Simple English Wikipedia from
download.kiwix.org, 2.9 GB, not in the repository). Without it the book never arrives and nothing else minds.
**The radio** (since v3.5.1) is a real station, Radio Paradise: while the pets' radio is on, the page plays the
chosen mix's stream and the engine asks `api.radioparadise.com` what song is on, at most once a minute. The
stations and the allowlist are `[radio]` in `config.toml`; every reply is in `data/radio/fetched.log`. The old
news, spoken forecast and "on this day" are gone. No pet action reaches the network.

**Profiles** are laid over `config.toml`. A house keeps to the world clock it was made on: the living family
was made on the showcase's, so it is started with `live` (or `showcase`), never with no profile.

| | |
|---|---|
| `./run.sh start live` | `config.live.toml`: the showcase's lives (about 16 world days) off turbo, with a world day of two real hours (1800 ticks; one hour until 12 October 2026). The house in `data/`. |
| `./run.sh start` | `config.toml` alone, for a new house: a world day is two real hours, a life about two days. |
| `./run.sh start showcase` | `config.showcase.toml`: short lives in turbo time (the world waits while the model thinks and otherwise runs straight on). About seven or eight real hours for five generations. Watch it afterwards with Replay. |
| `PET_PROFILE=viewdev PET_DATA=data.viewdev PET_PORT=8002 uv run python -m engine.server` | scripted brains on a quick clock, every v3.1 discovery within minutes, for working on the view |
| `PET_PROFILE=v31check PET_DATA=<a copy of data/> PET_PORT=8001 uv run python -m engine.server` | SPEC-v3.1 §9.2: v3.1 on a copy of the live house, in turbo, arrivals forced early. Never on `data/` itself. |
| `PET_PROFILE=live PET_DATA=<a copy of data/> PET_PORT=8001 PET_YIELD_TO=$PWD/data/model.busy uv run python -m engine.server` | a real-model copy beside the living family, without pausing it: the copy holds each of its thoughts back while the family has one waiting or in flight (the family keeps `data/model.busy` while it does). A copy's thought already in flight is not stopped, so a family thought can wait behind one. |
| `PET_PROFILE=showcase PET_DATA=data.showcase-3 PET_PAUSED=1 PET_PORT=8001 uv run python -m engine.server` | open an archived run (`data.showcase-1` to `-4`) to look at and replay (http://localhost:8001/?replay=1); nothing in it moves |

## Look at it

- **The house:** the room being followed fills the screen; the map beside it shows every room found so far and
  who is where. Click a room to look at it, a pet to follow it, or leave "Follow" on "whatever is happening".
- **Mind and lab** opens a drawer: **Mind** (how the selected pet feels, what it notices, what it means to do,
  what its parent told it, what it believes and where each belief came from), **Things**, **Family** (the tree,
  life records, family sayings and heirlooms), **Story** (the chronicle and each day's moments), **Lab** (the
  numbers the pets never see, and the voice lab).
- **You are the visitor**, in whichever room you are looking at: feed, talk, give a bit, move things, poke,
  open the window, name a pet or a thing. **Music** in the header plays calm, lively, mysterious or sad music
  to the room or the whole house (the pets feel it, may dance, and can pick the tune up); **Radio** switches
  the pets' radio on and chooses the station, or sets down your own little one until they have found theirs.
- **Stock the machine** in the header puts base materials of your choice (wood, stone, metal, clay, fibre, sand)
  into the vending machine in the storeroom, up to its limit of 12 each. The pets are told you did.
- **Sheets** (v3.5): `/sheet.html` shows every living pet's sprite by family and every thing invented in the
  house (`?names=0` hides the names and shuffles, for a blind test; `&key=1` adds the answers). `/parts.html`
  shows every part, every body plan, each use in five materials (`#uses`) and curios from real pairs (`#curios`).
- **Replay** plays back any recorded day of any family at up to 60×.
- **Sound** is off until you click "Sound off". Every voice is made in the browser from the pet's body, so
  families sound alike; no pet ever hears it.

## Work on it

```sh
uv run python -m engine.check               # the engine's self-check (about two minutes, no model)
uv run python -m engine.tick --days 40      # a headless lineage with scripted brains
uv run python -m engine.metrics [data dir]  # the Lab's numbers for a run
uv run python -m engine.alive <data dir>    # SPEC-v3.4 §0, from a house's own log: things handled, tiles walked, wants met, discoveries, tools, food grown, the book, the box
uv run python -m engine.bars <data dir> --since T [--until T]   # SPEC-v3.5.4 §0, the drive bars; a copy's sampler (bars.sample, every world minute) writes the bars.jsonl it reads curiosity and crowding from
uv run python -m engine.check               # (the self-check takes about ten minutes now)
uv run python -m engine.showcase [data dir] # the evidence for SPEC-v3 §12's bar, from a run's logs
uv run python -m engine.genes [data dir]    # SPEC-v3.5 §7.2: mutation rates, body plans and how far apart the two families stay, over 1,000 births
uv run --with pillow python view/assets/own/src/parts.py   # redraw the parts (also building.py, seasons.py, machine.py), then validate.py
cd view && npm install && npm run build     # rebuild the view; the running engine serves it as is
node view/check-voice.ts                    # the voice's self-check (no browser, no sound)
```

Everything tunable is in `config.toml` (the engine), `house.toml` (rooms, bits, weather, events, creatures),
`materials.toml` (what each property of a made thing does), `activities.toml` (what a pet's body does by
itself: add an activity there and the body can do it) and `crafting.toml` (SPEC-v3.4: what can be done to a bit and
where, what comes of it, the kinds that take a material found out first, the tools, what two joined things make
that neither was, what a seed grows into, what a passage in the book can point at, and the book's own few pages).
`picturable.txt` lists the words from the box a pet may wonder about: things it could picture. The pets are told
none of the numbers in any of them.

## What a pet is given

A page of plain words, a few times a minute at most: the time and weather, how it feels (four needs as
feelings, never numbers), what it notices, what and who is in the room, what just happened, what was said to
it, its project, what its parent told it, its beliefs, and what it can do. It answers with a thought, a
focus (what it wants to be about for the next while), up to three things it decides to do now, and what it
expects to feel; the engine carries those out and scores the expectation when the pet next thinks.

Between thoughts the pet's **body** carries on by itself, with no model asked (SPEC-v3.3): it wanders, plays,
naps, eats, tidies, peeks through doors, sits with kin, dances when there is music, each for a few seconds, in
character (its needs, its temperament, its habits and its mind's focus weigh the choice). The body never
makes, speaks words, writes, gives or lays an egg: what belongs to a pet's story is still its mind's. The mind
is told, in a line, what the body did since it last thought. Nothing tells it what it is. `Mind` in the drawer shows the page as the pet saw it.
