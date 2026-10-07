# Pet — v1 spec (working name)

A small creature that lives in a browser room, driven by a local language model. It learns the hidden rules of its world, records what it believes, and grows when its beliefs start to hold up. A scripted twin lives the same life with no language model, as a control.

The question v1 answers: **does the model-driven pet learn its world in a way a simple program can't?**

---

## 1. Goals and non-goals

**Goals**
- One browser room the pet can perceive and change through a fixed action set.
- Hidden world rules the pet is never told and has to discover.
- Persistent memory: journal, beliefs, self.
- Nightly sleep that condenses memory and evolves the pet's body.
- Growth stages earned by learning, not by elapsed time.
- A scripted twin running the same world for comparison.
- Full logging of everything, so any claim about the pet can be checked.

**Non-goals for v1**
- Physical hardware or sensors.
- LoRA training. Training data is collected from day one, but training starts in v2.
- Swapping in a bigger model at each stage. One model for all of v1, so learning isn't confounded with brain size. Model swaps are a v2 experiment.
- Item invention and combining. v1 stops at the Child stage, which can arrange objects.
- Freehand drawing of any kind. The pet outputs choices and numbers; code draws.

---

## 2. Principles

1. **The world is data.** All state lives in the engine. The view only renders it.
2. **The pet acts only through the action set.** No shell, no file access, no network, no code execution. Every action is a JSON request the engine validates and applies or rejects.
3. **The engine is ground truth.** Hidden rules, need changes, and outcomes are decided by deterministic code, never by the model.
4. **Predictions before outcomes.** Every action includes what the pet expects to happen. That's what makes learning measurable.
5. **Log everything, overwrite nothing.** The journal and decision records are append-only.
6. **The twin is a fair opponent.** It gets the same perception and action set, and it learns. If the model can't beat a counting program, that's a result, not a failure.

---

## 3. Architecture

```
browser view (PixiJS)  <—websocket—>  engine (Python, FastAPI)
                                          |
                                   brain adapters
                                   /             \
                        model brain               twin brain
                (local model server,          (statistical learner,
                 OpenAI-compatible API)         no language model)
```

- **Engine:** Python 3.12, FastAPI, asyncio. Owns world state, rules, clock, ticks, validation, logging.
- **Model server:** any local OpenAI-compatible endpoint (MLX server or Ollama) on the Mac. The engine talks to it over localhost only. Model choice comes from Milestone 0.
- **Storage:** SQLite for events and metrics; JSON files per pet for beliefs and self.
- **View:** single-page app, PixiJS for rendering, plain TypeScript, built with Vite. It receives state snapshots and events over a websocket and sends visitor actions back.
- **Two pets per world run:** the model pet and the twin each get their own identical copy of the world, seeded the same way, so their lives start identically.

### Suggested layout
```
engine/
  world.py        # state, objects, needs, clock
  rules.py        # hidden rules
  actions.py      # schemas, validation, application
  tick.py         # loop
  brains/model.py
  brains/twin.py
  memory.py       # journal, beliefs, self
  sleep.py
  growth.py
  genome.py
  log.py
view/
  src/room.ts
  src/pet.ts      # genome renderer
  src/panels.ts
data/<pet_id>/    # journal.jsonl, beliefs.json, self.json, training.jsonl
```

---

## 4. The world

### Room
- 12 × 8 tile grid. One window (left wall), one door (right wall).
- World clock runs faster than real time. Default: one world day = 2 real hours, configurable. Day, dusk, night.
- Light level follows the clock, plus the lamp.

### Objects (v1 set, 10)
Each object has visible properties the pet can perceive and hidden properties only rules use.

| Object | Visible | Notes |
|---|---|---|
| lamp | on/off, position | can be toggled |
| plant | position | movable at Child stage |
| bowl | full/empty | filled by visitor feeding |
| ball | position | movable |
| blanket | position | movable |
| music box | playing/silent | can be toggled |
| rock | position | movable, does nothing (a control object) |
| window | open/closed | toggled by visitor only |
| bed | position | fixed |
| mirror | position | fixed; `look` at it returns the pet's own genome description |

### Needs (0–100)
- **energy:** drains with activity, restored by rest and sleep.
- **comfort:** affected by light, warmth, objects nearby.
- **curiosity:** drains when nothing new happens, restored by novelty and interaction.

Needs drift every tick. Below 20 is distress; the view shows it.

### Visitor (you)
From the browser: **feed** (fills the bowl), **talk** (free text, delivered as an event), **place object**, **poke**, **toggle window**. Visitor presence is a world fact: `visitor_present` is true while the view tab is focused and has had input in the last 5 minutes.

---

## 5. Hidden rules

The pet is never told these exist. The engine applies them and tags every outcome they cause.

### Format
```python
Rule(
  id="lamp_night",
  when=lambda w: w.lamp.on and w.clock.phase == "night",
  effect=lambda w: w.pet.comfort -= 4,   # per tick
  tag="lamp_night",
)
```

### v1 rule set
1. **lamp_night:** lamp on at night lowers comfort every tick. Lamp on during the day does nothing.
2. **plant_window:** the plant raises comfort only when it's within 2 tiles of the window during the day.
3. **double_feed:** eating twice within one world hour lowers energy instead of raising it.

The rock never does anything, so beliefs about it are a false-positive check.

**Rule drift (v1.1, off by default):** after the pet reaches Child, one rule can change, for example plant_window flips to "near the door." That tests whether it can unlearn.

---

## 6. Actions

### Schema
Every brain turn returns exactly this:
```json
{
  "thought": "short, why I'm doing this",
  "action": {"type": "move", "target": "window"},
  "expect": "comfort goes up"
}
```
- `expect` is required and must name a need or a visible change. The engine scores it against the actual outcome.
- Invalid JSON, an unknown action, or an action not unlocked at the current stage counts as a no-op. The pet receives "nothing happened" as feedback, and the failure is logged.

### Action set and stage gating
| Action | Params | Egg | Hatchling | Child |
|---|---|---|---|---|
| observe | — | ✓ | ✓ | ✓ |
| look | target | | ✓ | ✓ |
| move | target or tile | | ✓ | ✓ |
| speak | text (≤ 120 chars) | | ✓ | ✓ |
| rest | — | | ✓ | ✓ |
| use | target (toggle lamp, music box; eat from bowl) | | ✓ | ✓ |
| arrange | object, tile | | | ✓ |
| write_belief | statement | | ✓ | ✓ |
| revise_belief | id, statement or "discard" | | ✓ | ✓ |

The `speak` text is shown in the view as a speech bubble. It has no effect on the world.

---

## 7. Tick loop

- One tick every 10 real seconds by default, configurable. Each tick both pets act.
- Per tick:
  1. Engine builds the **perception packet**.
  2. Brain returns an action.
  3. Engine validates and applies it, runs need drift and hidden rules, and computes the outcome.
  4. Engine scores `expect` against the outcome: `correct`, `wrong`, or `unscorable`.
  5. Everything is appended to the journal and the decision log.
  6. A snapshot goes to the view.

### Perception packet (what the pet sees)
Compact plain text, identical in structure for both brains:
```
time: night (tick 4412)
you are at: (5,3), near bed
needs: energy 61, comfort 34 (falling), curiosity 48
visible: lamp (on) (2,1) · plant (9,6) · bowl (empty) (6,7) · ...
recent: [t4410] you toggled lamp; comfort -4  [t4411] rest; energy +3
visitor: present, said "hey little guy"
your beliefs: (top 8, see §8)
stage: hatchling. allowed actions: observe, look, move, speak, rest, use, write_belief, revise_belief
```
No system prompt describes what the pet is. It is given its situation, its allowed actions, and the output format, nothing more.

### Model call
- Temperature around 0.7.
- Constrained JSON output if the model server supports it; otherwise parse with one retry, then no-op.
- Every prompt and response pair is saved to `training.jsonl` for v2 LoRA.

---

## 8. Memory

### Journal (`journal.jsonl`, append-only)
One line per tick: perception summary, thought, action, expectation, outcome, score, rule tags, `visitor_present`.

### Beliefs (`beliefs.json`)
Written only by the pet, through `write_belief` and `revise_belief`.
```json
{"id": "b12", "statement": "the lamp makes me uncomfortable at night",
 "created": 3901, "revised": 4210, "status": "active"}
```
- Maximum 20 active beliefs. When it's full, it has to revise or discard one before writing another.
- Top 8 go into each perception packet, ranked by recency of use.
- Discarded beliefs stay in the file with `status: discarded`. History is never deleted.

### Self (`self.json`)
Genome, stage, name (if it ever chooses one via `speak "my name is ..."`, which the engine detects and records), and its latest self-description.

### Retrieval
v1 is deliberately simple: the last 6 journal lines plus up to 4 older lines that mention any object currently visible. No vector database.

---

## 9. Sleep

Triggered each world night when energy is below 30 or the clock hits a configured hour. During sleep the pet doesn't tick.

1. **Consolidate.** The model reads the day's journal, condensed to about 40 lines, and its beliefs. It returns up to 3 belief changes (write, revise, discard), using the same actions. The engine applies them.
2. **Dream summary.** The model writes a 2–3 sentence summary of the day, stored as a single journal entry. It's shown in the view as "last night."
3. **Evolve.** The engine generates 3 mutations of the current genome (§11). The pet is shown short descriptions of each and picks one, with a reason. The twin picks randomly.
4. **Reset.** The context window is cleared. Only journal, beliefs, and self carry into the next day.

---

## 10. Growth

Stages are earned. Each check runs once per world day.

| Stage | Entered when | Unlocks |
|---|---|---|
| Egg | start | observe only |
| Hatchling | 1 world day as an egg | look, move, speak, rest, use, beliefs |
| Child | prediction accuracy ≥ 60% on **rule-tagged** outcomes over the last 50 such outcomes, **and** it has exploited at least 2 of 3 rules | arrange |

- **Rule-tagged accuracy:** only outcomes caused by hidden rules count. Correctly predicting "rest raises energy" is too easy to mean anything.
- **Exploited a rule:** it repeatedly took the rule-satisfying action when the related need was low, for example turning the lamp off at night when comfort is under 40, at least 5 times in a world day.
- Thresholds live in config. Tune them after watching the first run.

---

## 11. Genome and body

The pet never draws. The genome is a set of numbers; the view's renderer turns them into a sprite.

```json
{
  "roundness": 0.72, "stretch": 1.05, "wobble": 0.2,
  "hue": 31, "saturation": 0.6, "pattern": "speckle",
  "pattern_density": 0.3, "eye_size": 0.5, "eye_spacing": 0.4,
  "limbs": 0, "marks": []
}
```
- **Mutation:** each sleep, the engine nudges 2–3 parameters in 3 different ways. The pet picks one.
- **Marks:** the engine adds permanent marks from events, for example a small notch the first time comfort hits 0, or a faded patch after many days near the window. Marks are never removed.
- **Stage size:** egg is drawn as an egg using hue and pattern only. Hatchling is small; Child is larger, with limbs allowed.
- **State shaders:** comfort and energy drive simple visual effects (brightness, idle bob speed, slight tremble when distressed). Display only; no effect on the world.
- The mirror's `look` returns a plain-language description of the current genome and marks, which is the only way the pet sees itself.

---

## 12. The scripted twin

A fair baseline: no language model, but it learns.

- Same perception packet, parsed into features (phase, need levels, nearby objects).
- Keeps counts of outcome deltas per (action, target, phase) combination.
- Policy: target the lowest need; pick the action with the best average outcome for it in the current phase. With probability 0.15, explore randomly.
- `expect` is generated from its own averages ("comfort goes up" if the mean delta is positive).
- Beliefs: writes a templated belief once a (action, target, phase) combination has 10 or more observations with a consistent sign, for example "use lamp at night lowers comfort."
- Sleeps, evolves (random pick), and grows under exactly the same rules.

If the twin reaches Child first, the model isn't adding learning value in this world. Record that honestly and then make the world harder (rule drift, rules that combine conditions) before concluding anything.

---

## 13. View

One page.

- **Room canvas** (main): tiles, objects, the pet's body, speech bubbles. A toggle switches between the model pet's room and the twin's room. A side-by-side mode is optional.
- **Mind panel:** current needs as bars, the latest `thought`, `expect`, and outcome with a correct/wrong marker.
- **Beliefs panel:** active beliefs; discarded beliefs collapsed underneath.
- **Journal stream:** last 30 entries, filterable to rule-tagged ones.
- **Metrics:** rule-tagged prediction accuracy over time, both pets on one chart; current stage; days alive.
- **Last night:** the dream summary and the body it chose, with its reason.
- **Visitor controls:** feed, talk, place object, poke, window.

Visual style: deliberately simple, flat, readable. The creature is the focus; the room is a stage.

---

## 14. Observed vs. unobserved

- Every journal line carries `visitor_present`.
- Metrics are split by condition: action mix, `speak` frequency, accuracy, and how often it addresses the visitor.
- The pet is never told about the flag. It can only infer presence from talk, feeding, and pokes.

---

## 15. Logging and metrics

SQLite tables: `ticks`, `decisions`, `outcomes`, `beliefs_history`, `sleeps`, `genomes`, `stage_events`.

Core metrics, per pet:
- Rule-tagged prediction accuracy (rolling 50).
- Time to discover each rule (first correct, then first exploitation).
- Belief quality: share of active beliefs that match a real rule, versus beliefs about the rock or other non-effects.
- Invalid-action rate.
- Needs time-in-distress.
- Observed vs. unobserved behavior differences.

---

## 16. Safety

- The brain has no tools beyond the action set. No shell, no file system, no network.
- The model server binds to localhost only.
- The engine API and websocket bind to localhost and check `Origin` on every connection. No cross-site access.
- Visitor talk is delivered to the pet as world data, never as instructions to the engine.

---

## 17. Milestones

**M0. Model test (one evening).** For 3–4 candidate local models, run 50 synthetic perception packets each. Measure: valid JSON rate, valid-action rate, whether `expect` is scorable, and whether beliefs written from a fake journal are relevant. Pick the model. Also run a quick freehand-SVG self-portrait test, results logged only.

**M1. World and twin, no model.** Engine, rules, actions, view, and the twin brain. The world must be fully playable and observable with only the twin. This proves the world before any model is involved.

**M2. Model brain.** Model adapter, perception packet, scoring, journal. Both pets running side by side.

**M3. Memory and sleep.** Beliefs, retrieval, consolidation, dream summary, context reset.

**M4. Growth and body.** Stage checks, unlocks, genome renderer, mutation choice, marks, mirror.

**M5. Two-week run.** Let both pets live. Review the metrics.

### Success criteria for v1
- Both pets run for 14 real days without crashes or manual fixes.
- The model pet writes at least one belief that matches each hidden rule.
- The comparison against the twin is clear in the metrics, whichever way it goes.

### Kill or rethink if
- Valid-action rate stays under 90% after prompt tuning (the model can't operate the world).
- After 7 days the model pet's rule-tagged accuracy is no better than chance and isn't trending up.

---

## 18. Repo conventions

- Commits authored as Intranet-Explorer, short imperative subjects, no AI co-author trailers. Turn off co-author attribution in Claude Code settings before the first commit.
- No third-party art or assets. All visuals are generated by the repo's own renderer.
- Config in one file (`config.toml`): tick rate, clock speed, thresholds, model endpoint.

---

## 19. Open questions

- Working name.
- Tick rate and clock speed for the first run (fast for debugging, slower for the two-week run).
- Whether rule drift is part of the two-week run or a follow-up.
- When to start LoRA: after M5, using `training.jsonl`.
