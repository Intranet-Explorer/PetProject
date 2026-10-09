# Decisions

Where the build departs from [SPEC-v3.md](SPEC-v3.md), or settles something the spec leaves open: what the spec
said, what was done, and the evidence. Newest at the bottom of each part. (The v1 and v2 departures are in
README.md's history and NOTES.md.)

## Part 0: closing v2.5

- **The parent's message was cut to its last whole sentence.** The spec says at most 600 characters. The
  constrained output stopped the reply at exactly 600, mid-sentence ("I rested near the calm and"). The egg is
  given the 573 characters up to "…the breathing moon." The full reply is kept in
  `data.v2.5/baseline/message.json`. From now on the message schema allows a little over the limit and the
  engine trims to the last whole sentence inside it, so a parent's words never end on half a thought.
- **The message was asked with thinking on.** Every other waking call in v2 had thinking off. This was one
  call that a whole lineage starts from, and M0 found the model writes better with it.
- **The mother has no name, so she is "the first one".** Asked what it calls itself, the pet left it empty.
- **The first v3 egg also gets her body.** The spec passes on only the message. The egg will be laid with the
  v2.5 pet's final genome and one round of mutation, as §5.4 does for every later egg, so the lineage's bodies
  and voices begin from her and not from the default. Her temperament was never measured, so the first
  egg's is drawn at random from the house's seed.
- **More was saved than asked.** Beliefs, the last five dreams and Things, as the spec says, plus her final
  state, her two self-portraits, her moments, and her meter-talk figure (25.2% of 765 thoughts, 57.9% of 19
  beliefs), which §12 wants beside v3's.
- **"character" and "agent" were never in a prompt.** Checked across all 812 prompts of the v2.5 life, outside
  her own beliefs, dreams and speech: zero. Her calling herself "the character", "the agent" and "the entity"
  was her own. That goes in FINDINGS.md when it is next updated.

## The two amendments of 9 October

- **Growth is paced by days (§4.1 as amended).** Stages come at a day of life from `[growth]` in config.toml
  (Child 2, Youngling 4, Adult 7), Elder after `adult_days` as an Adult. Nothing else gates a stage: v2's
  kept-beliefs condition for Adult went with the useful-things one, since it has the same think-rate bound.
  Before the amendment I had built a "late bloomer" rule (grow up anyway at 1.75 times the days); it is gone.
- **Useful things as wellbeing, not as a gate.** Each useful thing a pet made counts as 3 points of lifelong
  wellbeing, for up to five things. Wellbeing moves a lifespan by up to 30% across 30 points, so five useful
  things are worth about 15% of a life (3.6 days of 24). A pet with none by Adult notices "you haven't made
  anything that's really yours" and `bequeath` refuses with "you have made nothing yet that is really yours
  to leave". The count is in the life record.
- **Turbo time.** `clock.turbo`: the server ticks without sleeping, and does not tick at all while any model
  call or night's work is in flight. A tick is about a millisecond, so "jump to the next thing due" is done by
  simply running the ticks in between; nothing is skipped and every timer still counts ticks, so a pet gets
  the same thoughts per world day as on the real clock. The call budget is counted in world time for the same
  reason. Parallel calls: the queue takes `model.parallel` workers; whether two is faster is measured before
  the showcase and recorded under Part 11.
- **The showcase profile is a file laid over the config**: `config.showcase.toml`, chosen with
  `PET_PROFILE=showcase` (`./run.sh start showcase`). Its timings are checked by the self-check (at least
  about 15 thoughts per world day) and by a stub run before any model time is spent.
- **Replay.** The server keeps what it sent the view every fifth tick, one gzipped file per world day under
  `data/replay/`, on every clock, not only in turbo: it is also how a day Tyler missed can be watched back.

## Part 1: feel, don't count

- **No coordinates either.** The spec removes need numbers, deltas, costs and counts. Tile coordinates were
  the other thing the v2.5 pet wrote into its beliefs ("the spectral wave at (3,2)"), so the packet has none:
  things are "beside you", "close by" or "across the room", and `move`, `make` and `arrange` take the name of
  something to go or put things near (or "here", or a wall) where v2 took a tile. The self-check asserts the
  packet contains no digit at all outside a parent's quoted words.
- **Time is words too.** No tick numbers anywhere a pet reads; "started yesterday", "morning, in spring".
- **Scoring `expect`.** `feel.expected` reads a prediction for the first need-word it names (rested, tired, at
  ease, uneasy, bored, lonely and their relatives) and which way: "less tired" and "more rested" are both
  energy up. Only the first need named is scored, as in v2.
- **A need turning bad is told once as an event** ("you have begun to feel tired"), because a pet reading
  five feeling-words every turn cannot be relied on to notice which one changed.
- **The meter-talk check is a regular expression** (`feel.METER`): signed numbers, percentages, coordinates,
  tick numbers, and the words efficient, optimal, optimise, maximise, cost(s), refund, action(s), bad target,
  stat(s), metric, point(s), cooldown, spike. It is counted per thought as it is adopted and kept on the
  intention's row, so the Lab's figure and the showcase's are the same query.
- **Hidden effects still carry a sense line**, as v2.2 found they must: every standing effect in
  `physics.effects` is a rate and the words for how it feels, in one record, so an effect cannot be added
  without its feeling.

## Part 2: engine for many pets

- **One house, one loop.** v2 gave each pet its own copy of the world. v3 has one house dict that every pet
  lives in; `Engine.tick` moves the clock once and then each pet in turn.
- **A pet keeps doing what it was doing while it thinks.** v2 stood it still until the reply came. With
  several pets sharing one queue a reply can take a while, and a creature that freezes whenever it is spoken
  to looks wrong. The new intention replaces the old one when it lands.
- **The budget is smoothed.** 150 calls an hour is also held as 15 in any six minutes, so one busy stretch
  cannot use the hour up and leave everyone waiting.
- **Per-lineage SQLite grows with the life**, by design: it is the append-only log. "Must not grow without
  bound" is applied to what is held in memory and rewritten every few seconds: `house.json` keeps the last 40
  dead pets (as a family-tree entry and a life record, their working memory dropped at burial), 400 moments,
  200 vanished things, 500 claims. Sixty stub days with four pets acting every tick: house.json 372 kB.
- **Loose bits are swept.** A room's floor holds 12 dropped bits; past that the oldest goes. Found by the
  first long stub run, which filled a room until nothing could be put down.

## Part 3: the house

- **The bit table is in house.toml**, not materials.toml as §6.3 says: bits belong to rooms, and house.toml
  is where rooms are. materials.toml is still only the physics of properties.
- **Feathers make soft or bouncy things.** The spec's example says "soft or light"; there is no "light"
  property and bouncy had no bit.
- **Nine room types fill nine rooms**: the nursery and the eight in the spec's table, each once per house, in
  an order shuffled by the house's seed. The door plan is a seeded spanning tree with a loop or two, at most
  three doors a room, except that a room the cap would cut off is joined all the same; the self-check walks
  the plan for several seeds and asserts every room can be reached.
- **Local rules, as built:** garden (plants ripen over about two days, faster in rain; rain on the soil
  eases); cellar (cold at night, lights do no harm, soft things left 16 hours go damp and give half); attic
  (the sun shaft crosses the floor and is warm, things unused two days gather dust: half, and a sneeze); pond
  (rest is worth half as much again; a thing left on the water turns up in another room); workshop (combining
  takes half the effort, noisy things are twice as loud); music room (while something there has just sounded,
  the rooms next door gain a little curiosity); greenhouse (warm by day in any season, plants at twice the
  rate); storeroom (dark: looking is worth half unless a light is lit; a little of four kinds of bit).
- **Memorials stay where the pet died.** The spec's storeroom row says a previous lineage's memorials "may
  be here". Stones stay on the tile of the death (§4.2), so the next family finds them wherever the last one
  lived, which is the point; the storeroom has nothing special beyond dark and odd bits.
- **Pets walk in straight lines and through each other**, as in v2. The pond is drawn shallow.
- **The three new properties.** fragrant: comfort for everyone in the room, fading as each pet gets used to
  it; the nose clears overnight and on leaving the room, which is itself something to find out. glassy:
  curiosity and a little comfort near it while the sun is out and the room has a window or sky. springy:
  using it gives six ticks of walking at double pace.

## Part 4: life, death, eggs

- **Hardiness moves a lifespan by ±10%** on top of wellbeing's ±30%; the spec's gene table gives hardy a
  "lifespan bonus" without a size.
- **The parent's word** (mother, father, parent) is drawn from the house's seed when the egg is laid.
- **Final words reach living children at the death**, as a second line under the message they hatched with
  ("the last thing your mother said to you"), when the last version differs from the one they were given.
  An egg not yet hatched simply gets the newest version.
- **Messages and tells end on a whole sentence** (see Part 0): the schema allows 640, the engine keeps the
  last full stop inside 600.
- **Dying.** A pet whose days are up dies at once, awake or asleep; it lies where it fell for `fade_minutes`
  and then the stone is all that is left. "Neglect" is given as the cause when neglect cost it more than a
  day and it never reached Elder.
- **An egg can be nuzzled.** It gives a little company at once, with nothing to accept: a lone parent
  sitting by its egg is the picture §5.1 describes.

## Part 5: others

- **Offers lapse after five real minutes**, and the one who offered is told ("Sol did not take the fluff").
- **A taken thing moves to the taker.** The owner is told at once if it is in the room and awake, otherwise
  when it next walks into the room the thing was in.
- **`give` to a creature is feeding it**; there is no separate `feed` action.
- **Company was slowed.** At the first rate a lone founder was "aching for company" within two hours and
  stayed there for days, with nothing it could do about it: exactly the unanswerable pressure FINDINGS warns
  about. Alone, company now takes most of a real day to run down. It also holds or rises with a creature in
  the room (more with one it has fed), while the visitor is looking in, and on touching the stone of one of
  its own.
- **A reply** is speech addressed to someone who addressed you within ten minutes, or an offer accepted.

## Part 6: mind

- **Temperament, as built.** curious: familiarity wears faster and "bored" comes sooner. sensitive:
  "uncomfortable" comes sooner. sociable: company falls faster, "lonely" comes sooner, and with someone
  there it notices wanting to be near them. bold: an unvisited door reads as an invitation, a plain fact or a
  doubt; the mouse lets a timid pet closer. patient: thinks 20% less or more often. playful: sampling
  temperature 0.5 to 1.0, and it notices things that "want to be played with". fertile: 1 to 3 eggs. hardy:
  neglect costs less, lifespan ±10%. No line ever tells a pet what it is like.
- **Projects are decided in the night's call** and take effect on waking, where the spec says "on waking":
  one fewer model call per pet per day, and the night is when it has the whole day in front of it.
- **The night is two calls, not five.** One with thinking on: dream, up to three belief changes, the one
  belief looked at again beside its own memories of it, the project, a line about anyone it wants to
  remember, the message if it has laid an egg, "My life" on its last day. One without: the body choice and,
  once grown, the self-portrait.
- **The belief review's "own memories"** are today's journal lines and its past dreams that share at least
  two content words with the belief.
- **Packet budget: 9,000 characters.** Cut first to last when over: earlier happenings, rooms it knows, who
  it knows, what others (not its parent) told it, its things' purposes, sounds from next door, beliefs
  beyond the eight most recently touched. Never cut: how it feels, what it notices, what and who is here,
  what just happened, what was said to it, its parent's words, what it can do.
- **"What it can do" is what it can do now.** The list and the reply's schema leave out an action there is
  nothing to do it with (nobody to give to, nothing offered, the house full), so limits are met as the world
  and not as a refusal. `make` is offered when there are bits to pick up as well as when it is carrying some,
  because its plans are two steps long: gather, make.

## Part 7: weather, events, creatures

- **A storm's power cut comes 11 to 16 hours into the storm's day**, so that it falls in the dark hours and
  does the job §6.4 gives it: a dark night nobody chose.
- **Events are skipped, not queued, in a crisis** (a pet weak or with a need near the bottom), and come at
  half the interval after six quiet hours.
- **The visitor's surprise** is off by default and, when on, is logged as "the director's, in the visitor's
  name".
- **Rule drift** picks one found room once per lineage, some days in: the cellar turns mild at night, the
  attic's sun turns harsh, the pond stops helping rest, the workbench makes combining harder, the greenhouse
  turns close by day, rain in the garden stops easing, the music room's sounds start to grate next door, or
  the storeroom becomes worth looking round.
- **Creatures.** At most two, never two of a kind. The moth comes to a lit light at night and eats at soft
  things within two tiles of it (after two hours they give half). The beetle carries loose bits between
  rooms and sleeps at night where it first appeared. The mouse keeps away from a pet that is walking, creeps
  toward one that is still, steals a sweet thing from an empty room, and after three feedings from one pet
  waits near it. The bird sings in the garden in the morning and leaves at a loud noise.

## Part 8: claims and story

- **Claims are matched by word overlap** (`story.alike`: stemmed content words, Jaccard or containment), not
  embeddings or a model: no second model is installed and a model call per sentence would eat the budget.
  At 0.5 two sentences are the same claim; at 0.8 a repeat, below it a changed form. Its error rate on a
  hand-checked sample from the showcase goes under Part 11.
- **"Dropped" is decided at death**: a sentence of the message a pet hatched with that nothing in its own
  messages resembles.
- **Truth flags** come from nine patterns over the physics the engine can check (lights at night, warm
  things in the cold, a second meal too soon, quiet and rest, the cellar's cold, the pond and rest, storms
  and company, the plant by the window, and the one known falsehood in the first mother's message: that the
  lamp keeps the dark from hurting).
- **The chronicle's paragraph is asked at each midnight** for the day just ended, at the lowest priority.

## Found by the turbo smoke run (one real-model life, before the showcase)

- **Comfort could not be won.** By the second day the smoke pet's comfort was at zero and had only ever
  fallen: the same chronic low comfort v2.5 ended with. Nothing it did raised it, the things that would
  (the bed, the blanket) gave no sign of it, three warm "glows" made after its mother's advice each cost
  comfort by day and added up, and a leak, a draught and a lit lamp did the rest. Changed, all in the
  direction FINDINGS points (a pressure has to be felt, and so does its remedy):
  - standing beside a bed, blanket or rug is noticed ("it is snug here by the bed"), and an uneasy pet
    notices that the bed "looks like somewhere you could settle";
  - like things no longer add up: beside five warm things it feels the warmest one, not five;
  - sleep in the dark eases comfort (up to 60, or 75 by a bed or blanket), sleep under a light does not, and
    it wakes knowing which it had ("you slept badly: there was a light on you all night"). This gives the v2
    lights rule a second, slower way to be felt, and it is the direct test of the first mother's one false
    claim, that the lamp keeps the dark from hurting;
  - a leak and a draught cost a little less (they last hours on the real clock).
- **Rates stay in real seconds on every clock.** I briefly made sleep restore energy by the world hour so a
  short showcase night would be "worth a night". That was wrong: every waking rate is per real second, because
  what a pet can do about a need is bound by how often it thinks, so a short day drains a quarter as much and
  should restore a quarter as much. Reverted.
- **Boredom points at the untried door.** A day and a half in, the pet had not left the nursery (its mother
  told it to stay near the lamp). A bored pet now notices "you wonder what is through the east door"; a timid
  one only when properly bored.
- **Inherited meter-talk.** The check flagged the hatchling's thoughts for the word "costs": it was quoting
  its v2 mother ("it costs less than either alone"). Counted as the spec says; noted because it shows the
  way a parent's vocabulary comes down with the message.
- **Misery dulls interest.** With comfort made winnable and its remedy pointed out, the smoke pet still chose
  its fascination (a private theory about the music box) over its misery, and nothing made that a bad trade.
  A miserable pet now gets 40% of the interest a thing would give, and is told why ("you are too miserable to
  take much interest in it"). Needs that can be traded off one for one let a pet live at zero in one of them.
- **Beliefs can be 220 characters.** At 140 and then 160 the model's beliefs kept being cut ("…only a different
  B"). They end on a whole sentence or, failing that, a whole word and an ellipsis.
- **One model call at a time.** Measured on this Mac with the real packet and schema, six calls each way,
  Ollama restarted between settings: with `OLLAMA_NUM_PARALLEL=2`, one at a time took 20.7 s (7.4 ms per
  character of reply) and two at a time 23.3 s (7.3 ms per character). No throughput to be had, and the second
  slot costs memory. `model.parallel` stays 1 and Ollama was put back to its default.
- **Night calls are capped for the showcase** at 3,000 tokens with reasoning effort "low": 42 s for the first
  night's thinking, against several minutes uncapped in v2.
- **A lack draws the eye to what would answer it.** The smoke pet sat at zero comfort for a day beside a soft
  thing of its own that it never thought to use, saying "I feel content": it had read the company word
  ("content with the company you have") as its mood, and "miserable" named no remedy the way "tired" and
  "lonely" do. Three changes. Company's second word is "not lonely" (the spec has "content"). The feelings
  are listed worst first, and a need at its very bottom reads "(it is hard to think of anything else)",
  whichever need it is. And `physics.drawn` adds one line per need running short, pointing at the nearest
  thing that would help: something soft "looks soft enough to sink into", the bowl can be smelled, the bed
  "looks like a good place to rest", a kin's stone "draws you". It names where to look, not what will happen.
