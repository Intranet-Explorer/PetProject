# Running PetProject

How to run, watch and work on the house. What the project is: [README.md](../README.md).

Other docs: DECISIONS.md (every place the build reads a spec its own way), [NOTES.md](NOTES.md)
(the v1 and v2 lives as they happened), [VOICE.md](VOICE.md) (the voice), and the specs from SPEC.md to
SPEC-v3.3.md.

## Run

```sh
./run.sh start live     # the family living in data/: a world day is two real hours, a life about forty world days (v4.2)
./run.sh status
./run.sh stop
```

**From a fresh clone**, first: `cd view && npm install && npm run build` (the engine serves `view/dist` and will not
start without it, saying so), and unzip the sound files, the release asset `pet-audio-v4.0.2.zip`, into
`view/assets/audio/` (they are not in git; `tools/audio/build_all.sh` rebuilds them from source). `run.sh` starts
the engine with `uv run --extra book` (libzim, for the encyclopedia below). `./run.sh start` moves the last
`data/server.log` to `data/server.log.1` (two kept); every line has a time. A new house begins only when the first
page connects, or at once with `PET_HEADLESS=1` (scripted runs and checks). The lineage's log is SQLite in WAL mode:
while the engine runs there are `lineage.db-wal` and `-shm` files beside it, so a backup of a running house copies
those too, or uses `sqlite3 <db> ".backup <file>"` (the deploys' way).

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
and the sounds. The code names no tile and no pack. [view/assets/README.md](../view/assets/README.md) gives the
formats and how to add a pack: put its zip in `assets-incoming/` (not in the repository) and map its pieces to
names there. `view/assets/third_party/CREDITS.md` credits what is used.

**The skin** (since v3.5.6) is Crusenho's Travel Book, Wood and Holo Book sprites and the Toriko pixel face, in
`view/assets/third_party/crusenho/` (only the sprites used; credits and licences in `third_party/CREDITS.md`), drawn
by `view/src/skin.css` as 9-sliced frames at whole-number scales. Short words are Toriko at 32 px; what is read is
Pixelify Sans (`third_party/pixelify/`), 16 px or, with "Large text" under More, 20 px. Since v3.5.7 the House tab follows
the action by itself (the chip beside "Here" says what it follows; `petView.follows()` lists every room change and
why), its right column is the blue console (the map, the room's readout, the board in VT323, the Works), and the
house's big moments drop in as banners (`petView.replayMoment(n)` shows a recorded one again, for checking). From 1000 px wide the House tab is a game screen
in three columns; narrower, one column that scrolls.
**The book** reads `book/wikipedia_en-simple_all_maxi_2026-09.zim` (Simple English Wikipedia from
download.kiwix.org, 2.9 GB, not in the repository). Without it the book never arrives and nothing else minds.
**The radio** (since v3.5.1) is a real station, Radio Paradise: while the pets' radio is on, the page plays the
chosen mix's stream and the engine asks `api.radioparadise.com` what song is on, at most once a minute. The
stations and the allowlist are `[radio]` in `config.toml`; every reply is in `data/radio/fetched.log`. The old
news, spoken forecast and "on this day" are gone. No hob action reaches the network; the view's art pipeline does: a
thing a hob invents is drawn by PixelLab (`tools/sprites/invent.py`, SPEC-v5.1 §7.2), like the radio's song titles come
from Radio Paradise. `[sprites2] on = false` (the default) leaves everything composited and makes no call.

**Profiles** are laid over `config.toml`. A house keeps to the world clock it was made on: the living family
was made on the showcase's, so it is started with `live` (or `showcase`), never with no profile.

| | |
|---|---|
| `./run.sh start live` | `config.live.toml`: forty-day lives with `[spirit]` on (the showcase's thirteen with it off) off turbo, with a world day of two real hours (1800 ticks; one hour until 12 October 2026). The house in `data/`. |
| `./run.sh start` | `config.toml` alone, for a new house: a world day is two real hours, a life about two days. |
| `./run.sh start showcase` | `config.showcase.toml`: short lives in turbo time (the world waits while the model thinks and otherwise runs straight on). About seven or eight real hours for five generations. Watch it afterwards with Replay. |
| `PET_PROFILE=viewdev PET_DATA=data.viewdev PET_PORT=8002 uv run python -m engine.server` | scripted brains on a quick clock, every v3.1 discovery within minutes, for working on the view |
| `PET_PROFILE=v31check PET_DATA=<a copy of data/> PET_PORT=8001 uv run python -m engine.server` | SPEC-v3.1 §9.2: v3.1 on a copy of the live house, in turbo, arrivals forced early. Never on `data/` itself. |
| `PET_PROFILE=live PET_DATA=<a copy of data/> PET_PORT=8001 PET_YIELD_TO=$PWD/data/model.busy uv run python -m engine.server` | a real-model copy beside the living family, without pausing it: the copy holds each of its thoughts back while the family has one waiting or in flight (the family keeps `data/model.busy` while it does). A copy's thought already in flight is not stopped, so a family thought can wait behind one. |
| `PET_PROFILE=showcase PET_DATA=data.showcase-3 PET_PAUSED=1 PET_PORT=8001 uv run python -m engine.server` | open an archived run (`data.showcase-1` to `-4`) to look at and replay (http://localhost:8001/?replay=1); nothing in it moves |

A copy of the house for a test lives beside the repo, in `../PetProject-tests/<version>/` (its data, log, reports and
pictures), never in /tmp: a shutdown clears /tmp, and a copy kept beside the repo just carries on from its saved tick
when its server is started again (16 October 2026).

### How a change is made (18 October 2026: this replaces the testing tiers of 16 and 17 October)

- **Build on a branch, run the self-checks (`./check.sh`: every check, the art and sound, the view; about fifteen
  minutes, stops at the first failure), back up `data/`, deploy, restart.** No copies, no smoke runs.
- **After a deploy, watch for 15 minutes:** errors in `data/server.log`, the tick advancing, the page loading, one
  screenshot. The Lab's **Today** section (top of the Lab tab) has the day's numbers beside yesterday's: each hob's
  needs, memories, aims done and failed, thoughts by kind (queue wait and compute apart), talks and failed replies;
  the house's last save, the model's busy share and calls, eggs laid and found, websocket clients and message size. Send the owner a five-line report. No day-long measurements unless he asks; a spec's bars are what to look
  for, not gates.
- **The owner watches and says what's wrong; it is fixed forward the same day.** Page-only fixes (view, CSS, art) go out
  without a restart. Roll back from the backup only if something is broken.
- **Every new part gets a switch in config that turns it fully off.**

**Standing rules for every Claude Code session on this project (20 October 2026):**

1. **Never poll.** Waiting on a helper, a background command, `check.sh` or a rehearsal: end the turn and say in one
   line what is being waited on; the session is resumed when it finishes. No sleep loops, no `until grep` loops, no
   re-reading a log to see whether a job is done. (Every poll re-sends the whole session as input to learn "not yet".)
2. **Don't re-read a file already read this session** unless it has changed.
3. **Reports in five lines or fewer** unless the owner asks for detail; departures go in DECISIONS.md, not in the reply.
4. **Every helper's brief carries rules 1–3.**
5. **One session per release**, and a `HANDOFF.md` between them.

### Switches for v3.6c (18 October 2026)

Each part of v3.6c can be turned off in `config.toml` without a rollback; restart the engine after changing one
(`./run.sh stop live && ./run.sh start live`):

| | |
|---|---|
| `[clearout] on` | the great clear-out, a one-time event on the first start with v3.6c (already done once it has run) |
| `[clearout] floors` | nothing made stands in the middle of a room; the evening tidy |
| `[population] on` | seven hobs, the guard on the model (no egg while it is over 85% busy), the egg that turns up by itself |
| `[population] lay` | v4.2.1: a grown hob with an egg in it is given a "lay" aim a day after it could lay, and lays (one model thought for the egg's words and name) |
| `[packet] trim` | the trimmed thought and the shorter reply |
| `[spotlight] on` | seasons for new things (the kiln, the yard, designing, fishing with a rod) |
| `[outdoors] on` | the garden gate opens by day in fair weather (off: it stays shut, and anyone out comes in) |
| `[design] on` | designing; since v5.1 (SPEC-v5.1 §4.5 deleted designing) only the catalog's buying back of a thing that matters |

And each part of v4.0 (characters, 18 October 2026), the same way:

| | |
|---|---|
| `[traits] on` | the ten axes' behaviours, quirks, values, moods |
| `[needs4] on` | hunger, safety, pride (off: food gives energy again) |
| `[opinions] on` | memories, opinions, gossip, bonds, two-parent eggs |
| `[talk] on` | conversations |
| `[talk] want` | talk when a hob wants company, not up to a count (off: `per_day` is the cap again) |
| `[ladder] on` | conflict from sabotage up (off: grudges only cool) |
| `[health] on` | injury and sickness |
| `[brain4] on` | the five kinds of thought (off: v3.6c's per-action thoughts) |
| `[planner] on` | the utility body, routines, housekeeping off the hobs' backs (off: v3.6c's body) |
| `[visitor4] on` | the visitor's tools in the console (off: the old toolbar) |

And v4.2, spirit (SPEC-v4.2, 19 October 2026). `[spirit] on` turns the whole release off at once (v4.0.6's house);
it is on in `config.live.toml` and off in the base, so the older self-checks run as they were. Every part reads its
switch through `engine/contracts.py`'s `on(cfg, part)`:

| | |
|---|---|
| `[spirit] on` | all of v4.2; and the model's budget: which kinds think, how hard, with how many tokens (`think_effort`, `think_tokens`) |
| `[lives] on` | forty-day lives in five stages, grief, old and slow (off: `[life]` and `[growth]` as they are) |
| `[deaths] on` | death with a cause: sickness, injury, bad food, the fall, exposure, the floor of four; nursing and the remedy |
| `[memory2] on` | memories in their own words with tags, found by the moment; what a talk leaves; tales |
| `[selfpage] on` | the page a hob keeps about itself |
| `[hooks] on` | beliefs, teachings and the visitor's words that change what a hob does |
| `[drives] on` | a drive, a flaw, a secret and a voice for each hob |
| `[talk2] on` | talk with a subject and subtext, longer lines |
| `[stage] on` | the director's one call a night, from `stage.toml`'s menu |
| `[visitor5] on` | the visitor's theory, absence, notes, tend and remedy |

The first start with `[spirit]` on migrates the house once (each part once, when it is first on): every living hob's
stage under the new thresholds and its drive, flaw, voice and secret; the report is in the log and in
`data/migration-v4.2.txt`.


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
./check.sh                                  # the one gate: engine.check and every engine/check_*.py, validate.py, the view's types, build and checks
uv run python -m engine.check               # the engine's self-check alone (about ten minutes, no model; it runs every check_*.py at its end)
uv run python -m engine.tick --days 40      # a headless lineage with scripted brains
uv run --extra book python -m engine.rehearse --to ../PetProject-tests/<version> [--days 40] [--model-migration] [--v51] [--from <data dir>]   # SPEC-v4.2 §0 (--extra book, or the book is unreadable: v5.1): a copy of data/, its migration, forty turbo days with scripted brains; deaths by cause, tracebacks, the Lab's Spirit numbers
uv run python -m engine.metrics [data dir]  # the Lab's numbers for a run
uv run python -m engine.alive <data dir>    # SPEC-v3.4 §0, from a house's own log: things handled, tiles walked, wants met, discoveries, tools, food grown, the book, the box
uv run python -m engine.bars <data dir> --since T [--until T]   # SPEC-v3.5.4 §0, the drive bars; a copy's sampler (bars.sample, every world minute) writes the bars.jsonl it reads curiosity and crowding from
uv run python -m engine.showcase [data dir] # the evidence for SPEC-v3 §12's bar, from a run's logs
uv run python -m engine.genes [data dir]    # SPEC-v3.5 §7.2: mutation rates, body plans and how far apart the two families stay, over 1,000 births
uv run --with pillow python view/assets/own/src/parts.py   # redraw the parts (also building.py, seasons.py, machine.py), then validate.py
cd view && npm install && npm run build     # rebuild the view; the running engine serves it as is
node view/check-voice.ts                    # the sound's self-check: sounds.json, babble, music and ambience choices (no browser, no sound)
```

**The sound files are not in git** (v4.0.2, about 310 MB of WAV): they are the release asset `pet-audio-v4.0.2.zip`,
unzipped into `view/assets/audio/` in every checkout the engine serves; their generators are in `tools/audio/`
(`build_all.sh`, deterministic) with the set's own README (`git` keeps `view/assets/audio/credits.json` and
`sounds.json`, and ignores the WAVs). The engine serves them at
`/art/audio/` with the rest of `view/assets` (they are not copied into `view/dist`); `validate.py` says so if they are missing.

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
