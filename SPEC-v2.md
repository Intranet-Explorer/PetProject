# Pet — v2 spec

v1 built a rule-discovery experiment with a creature painted on it. v2 turns it into a creature: something that lives in its room, makes its own things, and gets more power over its world as it grows. The engine stays; what the pet can do, how often it thinks, and what you see all change.

This replaces SPEC.md as the working spec. SPEC.md (v1) stays in git history.

---

## 1. What changes, in one table

| | v1 | v2 |
|---|---|---|
| What it is | a learning experiment | a creature you watch live |
| Thinking | one model call every 10 s, one action | an intention every few minutes, carried out over several steps |
| Its world | 10 fixed objects | the starting room plus everything it makes |
| Growth | passing a 60% prediction test | what it has made and lived through |
| Each stage unlocks | one extra action | more power over its world |
| Egg | a whole world day of "observe" | about 10 real minutes, no model calls |
| Hidden rules | the point of the experiment | the physics its inventions run into |
| Screen | dashboard with a creature in it | the room, big; the mind and lab behind tabs |
| Twin | runs alongside | code kept, off by default |

## 2. What stays

- **The world is data, and the pet acts only through the action set.** No shell, files, network or code. Every action is checked by the engine.
- **The engine is ground truth.** What an object actually does is decided by code, never by the model.
- **The journal, append-only.** Every turn is still logged with its prediction and outcome, so learning can be measured from the logs at any time. It's just no longer what drives growth or the screen.
- **Sleep:** dream summary, belief changes, body evolution, context reset.
- **Genome and body** (genome.py, pet.ts), marks, the mirror.
- **Safety** (SPEC v1 §16) and repo conventions (v1 §18), unchanged.
- **Constrained JSON output** built from what's actually in the room (model.py `schema`).

---

## 3. Intentions instead of ticks

The pet stops being asked "what now?" every 10 seconds.

### The intention
A model turn now returns an intention, not a single action:
```json
{
  "thought": "it's dark and the lamp is too bright to sleep by",
  "intention": "make something soft and dim to sleep near",
  "steps": [
    {"type": "move", "target": "bed"},
    {"type": "make", "recipe": { ... }},
    {"type": "rest"}
  ],
  "expect": "comfort goes up tonight"
}
```
- 1 to 5 steps. Each step uses the same action schema as v1, constrained by stage.
- `expect` stays required; the engine scores it when the intention ends.

### The loop
- The engine ticks every **2 real seconds** (config) so movement and animation look alive.
- Each tick executes the next step of the current intention. **No model call.**
- The model is called only when:
  1. the intention finished or a step was rejected or failed,
  2. something new happened: a visitor action, a need crossing 30 (down) or 80 (up), a phase change, waking up,
  3. or `max_idle_seconds` (default 180) passed with nothing new, so it never freezes.
- While waiting for the model the pet idles visibly (the view already animates bob and wobble).

This cuts model calls from ~360 an hour to roughly 20–40, and makes the pet look like it is doing something on purpose.

### Perception packet changes
- Add `you are doing: <current intention>, step 2 of 3` and the result of each step since the last call.
- Add `your things:` the objects it made, each with its name and the purpose it gave it.
- Replace the long `recent:` repetition with a compressed line: `[t440-449] you observed x10`.
- Everything else as in v1, including no system prompt saying what it is.

---

## 4. Making things

The core new feature. From hatching, the pet can invent objects.

### The `make` action
```json
{"type": "make", "recipe": {
  "name": "dim stone",
  "parts": [
    {"shape": "blob", "size": 2, "color": "blue"},
    {"shape": "dot", "size": 1, "color": "white", "at": "top"}
  ],
  "material": "soft",
  "purpose": "to hold when the light is too bright"
}, "tile": [9, 2]}
```
- **Shapes:** `circle`, `square`, `triangle`, `blob`, `bar`, `dot`, `ring`, `star`.
- **Sizes:** 1–3. **Colors:** a fixed 12-color palette (names). **at:** `center`, `top`, `bottom`, `left`, `right`.
- **Parts allowed:** hatchling 1–2, child up to 4, later stages up to 6.
- **Material** (one per item, from a fixed list; more unlock by stage, see §6): `soft`, `hard`, `warm`, `cool`, `bright`, `dark`, `noisy`, `quiet`, `bouncy`, `heavy`, `sweet`.
- **Name** ≤ 24 chars, **purpose** ≤ 80 chars, both free text, cleaned like `speak`.
- Engine checks: valid recipe, tile free and inside the room, under the item cap, enough energy.

### What an item actually does
The engine derives real effects from **material, size and context**. The purpose text has no effect at all. The pet only finds out what its invention does by using it.

| Material | Effect |
|---|---|
| soft | `use`: comfort +2 (×size/2) |
| hard | none; can be stood on, blocks a tile |
| warm | nearby (≤1 tile): comfort +1 per tick at night, −1 per tick during the day |
| cool | nearby: comfort +1 per tick during the day, −1 at night |
| bright | counts as a **light** (§5): toggled with `use` |
| dark | nearby: cancels light effects within 1 tile |
| noisy | `use`: curiosity +3, energy −1; makes its neighbours' rest worse |
| quiet | nearby: `rest` gives +1 extra energy |
| bouncy | `use`: curiosity +2, energy −1 |
| heavy | can't be arranged once placed |
| sweet | `use`: energy +5 once, then the item is used up |

Values live in `materials.toml`, not code, so they can be tuned.

### Novelty wears off
Using the same item repeatedly gives diminishing curiosity (reuse the v1 `seen` novelty map). It's a reason to keep making new things.

### Costs and limits
- Making costs energy: 4 + 2 per part.
- Item cap: 12 made items in the room (config). At the cap, a `make` is rejected with "there's no room for more"; the pet has to `unmake` one first.
- `unmake` (target: one of its own items) removes it and gives back 3 energy. The journal keeps a record of every item that ever existed.
- Starting objects can't be unmade.

### The pet's catalog
`data/<pet>/things.json`: every item ever made, with recipe, tile, made-on tick, times used, and the needs changes observed when it was used (engine truth, not shown to the pet).

---

## 5. Hidden rules become physics

Keep the v1 rules but generalize them so they apply to what the pet makes:

1. **lights_night** (was lamp_night): any light that's on at night (the lamp or any `bright` item) lowers comfort by 4 per tick, unless a `dark` item is within 1 tile of the pet.
2. **plant_window:** unchanged.
3. **double_feed:** unchanged, and also applies to `sweet` items.

The material table in §4 is itself mostly hidden rules: warm and cool flip with time of day, noisy hurts nearby rest. The pet is told none of it. Each rule-caused change is tagged in the journal, as in v1.

---

## 6. Growth by experience

Stages are earned by what the pet has done, checked each morning.

**A useful thing:** an item it made, used at least 5 times, where the related need went up on most of those uses (engine truth). That's the bridge between learning and growth: it can only make useful things by figuring out how its world works.

| Stage | Entered when | Unlocks |
|---|---|---|
| Egg | start | nothing; the engine doesn't call the model |
| Hatchling | after `egg_minutes` (default 10 real minutes) | move, look, use, speak, rest, make (1–2 parts; soft, hard, warm, bright), unmake, beliefs |
| Child | 2 world days lived and 2 useful things | arrange (any movable object including its own things), make up to 4 parts, all materials except sweet |
| Youngling | 4 days and 5 useful things | **combine**: merge two of its things into one (union of parts up to 6, material of either, new name and purpose); **paint**: set wall and floor colors from the palette; sweet material |
| Adult | 8 days and 8 useful things, plus 3 beliefs it has kept for 2+ days | **teach**: give one of its things a behavior (§7); self-portrait at each sleep (§8) |

- Thresholds in config.
- A stage change is an event the pet perceives ("you feel bigger; you can do new things: …") and the view shows (§9).
- Body size and limb count follow stage as in v1, extended to youngling and adult.
- Still one model for all stages. Brain upgrades remain a later experiment.

---

## 7. Behaviors (Adult)

`teach` attaches one behavior to one of its things, from a small engine-checked language:
```json
{"type": "teach", "target": "dim stone", "behavior": {"when": "night", "do": "glow"}}
```
- **when:** `day`, `night`, `dusk`, `visitor`, `touched`, `alone`, `pet_resting`.
- **do:** `glow`, `dim`, `hum`, `bounce`, `move_toward_pet`, `move_away`, `change_color:<palette name>`.
- One behavior per item, 4 taught items maximum.
- The engine runs behaviors each tick. Their effects follow the same physics: a glowing thing counts as a light at night.

---

## 8. Self

- **Name:** detected from `speak "my name is ..."` as in v1, shown in the header once chosen. The pet can also name its things (that's the `name` field).
- **Self-portrait (Adult):** at each sleep, the pet writes a recipe for itself in the `make` format (up to 8 parts). The view draws it next to its actual body in a "portraits" gallery. Nothing about its real body changes; it's a record of its self-image.
- **Consolidation prompt fix:** the v1 run wrote log entries as beliefs ("A visitor arrived at t137…"). The sleep prompt now asks for "short statements about how something in your world works, or about yourself; not a list of what happened". Reject a change at sleep if it contains a tick number like `t137`.

---

## 9. The view

The room is the screen.

- **Room:** fills most of the window. The creature drawn at 2× the v1 size. Its made items drawn from their recipes by a `drawThing(recipe)` renderer in the same style as the starting objects. Each made item gets a small label with its name. Speech bubbles as v1. Room colors follow `paint`.
- **Moments:** short banner messages for things worth seeing: "it made a *dim stone*", "it hatched", "it is now a Child", "it named itself *Pip*", "it took apart the *loud ball*". Kept in a scrollable list.
- **Drawer, closed by default, with tabs:**
  - **Mind:** current intention, its thought, the step it's on, needs bars.
  - **Things:** a shelf of everything it has made, ever, with its name and purpose. Unmade ones greyed out. For you (not the pet): what each one actually does and how many times it was used.
  - **Diary:** dream summaries by day.
  - **Beliefs.**
  - **Lab:** everything from v1's Compare tab and journal, plus useful-things count and stage progress.
- **Visitor:** feed, poke, talk, window, move an object, and **give**: drop a simple item into the room (pick shape, color, material from the same lists). Given items count as visitor's, not the pet's.

---

## 10. The twin

- Code stays. `twin.enabled = false` by default.
- When enabled it runs headless with the old one-action-per-tick loop and random recipes for `make`, and its metrics show in the Lab tab only. Not part of the default experience.

---

## 11. Milestones

Each milestone ends with: stop the run, archive `data/` to `data.<milestone>/`, start a fresh life, watch it for an hour, and write what you saw in `NOTES.md`.

**V2.0 Stop and archive.** `./run.sh stop`. Move the current `data/` to `data.v1/`.

**V2.1 Alive.** Intentions loop (§3), 2 s ticks, 10-minute egg with no model calls, compressed `recent:` line, consolidation prompt fix (§8), room-first view with the drawer (§9) holding the existing panels. No new world features yet. Check: the pet visibly walks around and does short sequences; model calls under 60 per hour.

**V2.2 Making.** `make`, `unmake`, materials and effects from `materials.toml`, item cap and energy cost, `things.json`, `drawThing` renderer, Things tab, moments, generalized lights rule (§5). Stages: egg and hatchling only. Check: in its first hour as a hatchling it makes at least 2 things, and every made thing renders and has the effect the table says.

**V2.3 Growing.** Useful-thing tracking, stages through Youngling (§6), arrange, combine, paint, the stage-up event and banner. Visitor `give`. Check: run a day at fast clock (`day_seconds = 1800`) and confirm stage-ups fire from the right counts.

**V2.4 Adult.** `teach` and behaviors (§7), self-portraits and the portraits gallery (§8).

**V2.5 Long run.** A real-clock run. What to look at, in order: what it makes and why, whether its things get more useful over time, which useful things it kept, what it names itself and its things, how its self-portraits change.

### Kill or rethink if
- After V2.2, most made things are near-identical (same shape, material and purpose over and over). The pet isn't inventing; it's repeating. Fix the prompt or the novelty pressure before going on.
- After V2.3, it never reaches Child at the fast clock: the materials are too hard to discover or the threshold is wrong.

---

## 12. Config additions

```toml
[clock]
tick_seconds = 2
max_idle_seconds = 180

[egg]
egg_minutes = 10

[make]
item_cap = 12
energy_base = 4
energy_per_part = 2
unmake_refund = 3

[growth]
useful_uses = 5
child = { days = 2, useful = 2 }
youngling = { days = 4, useful = 5 }
adult = { days = 8, useful = 8, kept_beliefs = 3, kept_days = 2 }

[twin]
enabled = false
```
Remove the v1 accuracy and exploit thresholds from `[growth]`; keep computing those metrics for the Lab tab.

---

## 13. Open questions

- The pet's name in the repo (currently "Pet").
- Whether made items survive across lives or every new egg starts with an empty room.
- Whether the visitor can see the pet's intention before it acts, or only after (spoils the surprise vs. helps you follow it).
