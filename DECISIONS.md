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
- **An untried door smells of what is behind it.** The spec decides a room's type when someone first walks
  in. The smoke pet stayed in the nursery for days: three identical doors gave it nothing to be curious
  about. Which type lies where is now fixed by the house's seed from the start (the room's contents are still
  made on first entry, and the house is still reproducible from its seed), and each untried door carries a
  hint: "from under it comes a smell of wet soil and green things", "cold, damp air", "a faint ringing now and
  then". A bold pet "wants to know what is there"; a timid one "is not sure about it". Boredom points at an
  untried door from "a bit bored" for a timid pet and sooner for the rest.
- **Soft things are worth using.** v2's soft gave 2 comfort a use. Against a drift of 0.6 a minute and a pet
  that acts about once a minute, that could never win comfort back, and the smoke pet proved it: it rested
  "sunk into" its soft things again and again and stayed miserable. Soft is now 5 a use (2.5 to 7.5 by size),
  the blanket and rugs to match, resting beside something soft counts as using it, and a snug place gives
  0.5 per 10 s. Comfort can now be restored at about the rate energy can.
- **`give` picks up what is lying there.** The pet tried to give the beetle moss that was on the floor beside
  it. Refusing that taught nothing; it now picks the bit up on the way if it has room to carry it.
- **A parent and its young pull at each other.** The smoke parent laid its egg, wandered off through four
  rooms, and was two rooms away when the child hatched; the child spent its first day alone. Company alone did
  not bring them together (the parent was "not lonely"). While a child is an egg, a hatchling or a Child, a
  parent elsewhere notices "you think of Sol, in the nursery without you" and the child notices "you want your
  mother; they are not here". Nothing makes either of them go.

## Part 9: the view and the voice

- **The view was written by a helper agent against a fixed snapshot contract** (`engine/server.py`), then
  checked by eye after the power cut: all nine room types by day and night, rain, storm, snow, heat, a power
  cut, every drawer tab, the family tree over seven stub generations, replay, both themes, 1280×800.
- **Replay** is `?replay=<family>` or the header's Replay button: a scrubber over the recorded days, play and
  pause, 1× to 60×, the same drawing code as live. The visitor's controls are hidden while replaying.
- **Voice phase 2, as built.** An egg has only its heartbeat. A hatchling chirps, one beep a word. A child
  babbles every syllable. From youngling on, a word it really knows is left out of the babble and said aloud by
  the browser's own speech voice, pitched to its body: "hello", its own name, the names of its useful things,
  and for an adult or elder the names of the others in the house. VOICE.md gives adults "its described voice
  (phase 3)", which SPEC-v3 §14 leaves out, so adults and elders keep the youngling's way of talking with more
  words. Elders are lower (290 Hz base), a third slower, with a slight tremble.
- **Families sound alike because voices are only ever made from genomes**, and a child's genome is its
  parent's plus one round of mutation. The voice check asserts it.
- **Turn-taking**: speech is queued on the audio clock, each utterance starting a third of a second after the
  one before ends; anything that would start more than eight seconds late (a replay at speed) is dropped.
- **Rooms**: the room being looked at is at full volume, rooms through one door are at about a fifth and
  low-passed, the rest are silent. Rain is loud under open sky (garden, greenhouse, attic, pond), faint in
  rooms with a window, absent in the cellar and storeroom.
- **New sounds**: a death (two long falling notes in the pet's own voice), moth, beetle, mouse, bird, rain,
  thunder, the power's hum running down and coming back, a leak's drips, a draught and its door, a delivery's
  thud. The v2 "content trill" for a use that helped now marks a nuzzle or a gift taken: the view no longer
  receives each pet's step journal with every snapshot.

## Found by the smoke run's later generations (it reached a fourth before the power cut)

- **Nuzzling had become a loop.** 359 nuzzles against 8 things said in 26 days: a nuzzle arrived as an urgent
  offer, the other accepted at once, felt close, and offered one back. Three changes: an offer is a reason to
  think again but no longer an alarm; closeness with the same one is worth 0.7 of the last time, until a night
  eases it ("it is familiar now, and eases you less"); and a pet that is already "close to someone" is not
  offered `nuzzle` at all. One of the pets had already written the rule into its message ("ease thins with
  repetition, as all ease does"); now it is true.
- **A reply can come later.** The pets did answer each other in words, but twenty thoughts later, not ten
  minutes. The window for "a reply" is 1,500 s.
- **Temperament moves a little more between generations** (σ 0.09, and a 45% chance of one gene jumping
  0.2 to 0.35): the largest drift along a line after three generations was 0.18, visible in the numbers but
  not in how the pets lived.
- **The founder's inherited words count as generation 0** in the claim index, so a saying that began with the
  last v2 pet can be followed into the family and seen to be kept, changed or dropped.
- **An elder is reminded it can tell.** One `tell` in 26 days. An elder with someone younger in the room now
  notices "there are things you know that Drift does not; you could tell them while you can".
- **The Lab and the showcase script read the logs on the clock they were written on**: the engine notes its
  profile in house.json.

## Part 10: the fresh-eyes review

A fresh agent that had not seen the build read the spec, the code and the smoke run's logs, and came back with
31 findings. What was done about them, the ones that changed a design first. The first showcase attempt, 16
minutes old, was archived as `data.showcase-0` and the run restarted on the fixed engine.

- **One pet's failing step could freeze the house** (an exception left the tick to be retried for ever). Each
  pet's tick is now caught on its own: the error is logged, that pet's intention is dropped, the clock goes on.
- **A made thing could take a fixture's name and replace it** (a hatchling naming something "bed" lost the
  bed). A made name can no longer equal any fixture, stone, bit, creature, door or pet in the house; a second
  "soft nest" is "soft nest two", in words, since digits in names were also reaching the packet.
- **Three needs sat at the ceiling** in the later smoke generations (company over 90 for 77 to 98% of steps),
  so the feelings line barely changed. Company near another pet rises a quarter as fast (0.15 per 10 s) and
  falls a little faster alone; looking and watching give less interest and familiarity wears faster (0.75);
  snug places, soft things and "yours" give a little less than the first comfort fix set them to.
- **The bar script could pass on evidence that could not fail.** Criterion 3 now needs a first-day thought
  that shares two words of content with one particular sentence the pet was told (the engine's own "you want
  your mother" cannot make one). Criterion 4 follows every sentence a parent ever put in its message through
  each line of three generations and reports held, changed or dropped; it passes by itself only when one is
  held, otherwise it lists what a reader must judge. Criterion 6 only counts a thought by a pet in the event's
  room that names the event in words nothing else would use. Each prints "has evidence to be read" where a
  person has to decide, and that is how SHOWCASE.md treats them.
- **Beliefs are known by a word, not a number.** Pets were citing "b15" in 3 to 10% of thoughts. A belief's
  handle is now the first word of its own that no other belief of that pet has ("lamp", "pond"). The packet
  also no longer says which step of a plan it is on, counts repeats in words, and the mirror gives limbs in
  words.
- **Sayings belong to one family.** The claim index was shared by every lineage in a house, so a second
  family could never have sayings of its own. Claims are matched within the lineage.
- **An inherited heirloom can be handed on**, as §5.3 says, and none can be eaten or stolen by the mouse. An
  elder in its last three days with a living child and something useful of its own "finds itself thinking
  about which of its things its children should have": in 26 smoke days nobody had used `bequeath`.
- **The pond's rule can now fire.** Nothing could ever be put on the water. Arranging a made thing "near the
  pond" sets it on the water, and within the hour it is in another room.
- **Neglect can happen.** It needed comfort and energy both under 10 without a break for a waking day, which
  a night's sleep always broke. Time with their mean under 20 now adds up, good time pays it back, and a
  waking day's worth makes a pet weak; each further such day costs two of lifespan (less for the hardy).
- **`make` picks up what it is short of** from the floor on the way, if it has room to carry it. A third of
  the smoke run's makes failed for want of one bit that was lying beside the pet.
- **A reply to an offer is ordinary news.** With offers, "leaned back against you" and "took what you offered"
  no longer count as urgent, and the budget now counts calls that are queued as well as those answered: the
  smoke run had gone to 166 calls in a world hour against 150, with 70% of thoughts on the urgent path.
- **A prediction that could not have come true is not scored.** "More at ease" with comfort already full
  was being marked wrong; it is unscorable now. "Stronger sense of companionship" is no longer read as energy.
- **Numbers moved out of the code** (§11.5): the feeling thresholds and temperament's shift, think-rate
  factors, lifespan shares, egg and making costs, company gains, creature stays and tastes, arrival and storm
  timings, the crisis threshold, and the table of rule drifts are in config.toml and house.toml. What is left
  in code is geometry (door tiles, the ring a moth flies), wording, and the shapes of formulas.
- **Smaller**: a draught shuts its door from both sides; a delivery is told to each pet as it would know of
  it; speech ends on a whole sentence; what a pet carried is left where it died; the old family's log is
  closed when a new one starts; the lineage's end is noted once; a house is only opened on the clock it was
  made on; "the house is full" is felt whenever that is what stands in the way of an egg; a parent's words
  now come after the pet's own beliefs in the packet, as §5.2 says; heirlooms in other rooms are listed.
- **In the view**: the header is one row at every width (a power-cut chip used to wrap it and move the room);
  the moment banner sits at the foot of the room for four seconds, not across the top for eight; a power cut
  by day no longer darkens the room; the Family tab remembers which family and whose life were open; the
  founder's mother reads "the one before"; the temperament chart on a card is large enough to read.
- **Left as they are, knowingly**: pets still walk over fixtures and each other (no pathfinding); a thought in
  flight when the engine is killed is lost with the inbox lines it consumed, and a night killed between its
  two calls is thought again; the life record keeps the first and last five versions of a message (all of
  them are in the log) and its "most-used things" are the ten most-used things it made; the belief review
  waits until a pet holds two beliefs; the Lab gives lifelong wellbeing as one number, not a curve; door
  names are per room ("the west door" is a different door in each), which one pet took for the rooms
  shifting, and which the packet now heads "this room's doors".
- **The lay-egg and night prompts say that what a pet was told is its own to pass on, change or leave out.**
  §5.2 says that is how myths form, and in the smoke run children wrote wholly new messages: of everything
  three generations handed down, no sentence survived to the third. The words leave the choice with the pet.

## Part 11: the showcase

One real-model run in turbo time, 10 October 2026, 10:20 to 17:16: 30 world days, 7 pets, 5 generations. It is
written up in showcase/first-run.md and kept in `data.showcase-1/`. An earlier attempt, 16 minutes old when the review's
fixes went in, is `data.showcase-0`.

- **The meter-talk pattern was changed while judging, and criterion 1 depends on it.** By the pattern the
  run started with, two pets were over the bar (11.9% and 18.1% of thoughts after the first day). Nearly all
  of those flags were the verb in this family's "the pulse points south": `\bpoints?\b` was written for v2's
  "6 points". It now needs a number in front of it. Spelled-out thresholds ("below thirty") were added at the
  same time, which is stricter. By the new pattern every pet is under 5% and the last v2 life is 43.0% of
  thoughts and 57.9% of beliefs (it was first measured at 25.2% of thoughts with a narrower pattern still, so
  both figures are given wherever one is). The share is now computed from the thoughts' words, not from the
  flag stored when each was logged, so an old run is read by today's pattern.
- **The criterion itself was not replaced**, but it measures less than its name. These pets do not talk like
  meters; the word "project" is in 38% of their thoughts. SHOWCASE.md says so under criterion 1 and
  under "What's still boring".
- **A drifted rule kept its old words.** The cellar's night rule drifted on day 7 from costing comfort to
  giving a little, and the sense line went on saying "the cellar's cold gets into you" for the other 23 days.
  Every room rule's sense line now follows the sign of its number, with a self-check. The run was not
  repeated for it: no criterion rests on that line, and the family's saying "the cold is the rest" turned out
  to be true of the drifted room against the words, which SHOWCASE.md sets out with the comfort figures.
- **The run was let go past the fourth generation** (to day 30, just under seven real hours) so that the
  third generation's deaths and the fourth's messages were in it. §12.1 asks for at least four generations
  lived or twelve hours.
- **The garden was never found**, so criterion 8's "every room type" is met with eight screens from the run
  and one from a scripted-brain house, labelled as such.
- **The family's vocabulary is measured** in the bar script's last section, at Tyler's request during the
  run: per pet, the words that neither the engine's own text nor another family on the same engine uses,
  split into inherited, coined, and picked up from the living, with what became of "below thirty" and of
  "Make the shape. Unmake it." It is not a ninth criterion. The baseline is one other run (`data.smoke`); a
  word that family also happened to coin is set aside with the everyday ones.
- **Claim matching, checked by hand.** On the smoke run, with the first matcher, about a third of 30
  sampled "changed" matches were not the same claim, and matches at 0.8 or over ("repeated") were sound;
  the containment rule was tightened for that. On this run I read the 12 three-generation chains the bar
  script calls held or changed, and all 12 are the same claim. Two faults remain and both showed here: the
  matcher cannot see "not" (the engine counted "The cold is not the rest" as the family saying reaching a
  third generation), and the truth patterns do not know a rule has drifted ("the cellar is cold" is still
  scored true). Left as they are and listed in SHOWCASE.md.
- **Criterion 4 is passed two ways and the write-up says which claim did what**: a saying held for three
  generations inside v3, and "the pulse asking for a new shape" changed by a child after two days of its own
  things doing nothing. "The lamp keeps the dark from hurting", the one inherited claim the engine can score,
  was dropped from the message while still held as a belief, so it is not counted as a correction.

### The first run did not pass, and what was changed before the second

A second fresh reader graded the run from its logs before reading SHOWCASE.md. It agreed on criteria 1, 3, 4,
5 and 6, and disagreed on two. **Criterion 7**: the fourth generation's life was its parent's again (the same
room for 85% of its steps, one project for nine days, the message copied word for word), and "different
words for the same things" is contradicted by the run's own vocabulary table, where each generation coins
less. **Criterion 8**: names clipped in the family tree and on the cards, labels overlapping, pets drawn on
top of each other. It also showed that temperament's drift left no trace in behaviour, that the correction
and "the cold is the rest" were told more firmly than the log supports, and about a dozen wrong details.
The first run is kept as `data.showcase-1`. Diagnosis from its log, and the changes:

- **Two needs could not fall, so temperament and boredom had nothing to act on.** A step gave +0.86
  curiosity on average against 0.3 lost (638 looks alone gave 889), and sharing a room gave company faster
  than it drained, so company was at 95 or more for 80 to 96% of every later pet's steps. A sociable pet and
  an unsociable one lived the same day, and nobody had a reason to leave the cellar. Now: looking and watching
  give less (0.4 and 0.2), novelty is worth less and comes back half as fast, curiosity drains at 0.45; and
  presence lifts company only as far as 65, past which it slips unless something passes between two pets (a
  word, a gift, a lean). At 65 a sociable pet is "a little lonely" in company and an unsociable one is not.
- **A bored pet is drawn to a door it has never been through** ("the west door is one you have never been
  through"), as a lack of comfort already draws it to something soft. Rooms entered fell 7, 8, 4, 4, 3 down
  the line, with the attic visited once and the garden never.
- **A grown pet no longer has its parent's message in front of it while awake.** §5.2 says the message
  "stays in the child's packet for life". In the first run that put the same five sentences into every one of
  a pet's thoughts for sixteen days: 91 to 98% of the later pets' own words were inherited, and one copied its
  message unchanged through six versions. §5's Why asks for "what gets lost or distorted along the way", and
  nothing can be while the words are always there. The message is now in the packet word for word while the
  pet is a hatchling or a child, and for a day after a parent's last words; after that, awake, it has what it
  made of them (its beliefs, each marked "told by"), and it meets the words again each night when it reviews
  its beliefs and its own message. This is a departure from the letter of §5.2.
- **Saying the same thing to the same one again lands flat**, as a second nuzzle already eased less: no
  company for either, and the speaker is told so. One pet said "The cold is the rest" eleven times.
- **The one rule drift of a lineage waits for a room that has been known three days.** In the first run it
  fell on the cellar fifteen ticks after the cellar was found, so nobody ever knew the old rule and nothing
  could be seen to change. The pond's sense line also follows its drifted number now. (The earlier note that
  every room rule's line does was too broad: the workshop's rule has no line, and the self-check covers the
  cellar's.)
- **A second run was stopped after 25 minutes and started again** (`data.showcase-2a`). Its founder walked
  into the garden on day 2, which in that house has one door, and stayed three days with curiosity at nothing,
  making and unmaking sweet rings "to test if a novel shape reduces boredom". Two things were mine. Curiosity
  at 0.45 drained faster than anything a maker does could refill (it gained 0.79 a step and lost 1.22), so
  it is back at 0.3 with the smaller gains kept. And the pull toward an untried door only looked at the room
  the pet was in; a bored pet in a room with none now thinks of the nearest room it knows that has one, and
  which way that is.
- **One number was changed while the second run was going, at the start of world day 11**, and the engine
  restarted on the same house. Closeness past what presence gives was set to slip at 0.03 per 10 s, which in
  real seconds is five points a world day on the showcase clock: the second-generation pet, which talks and
  nuzzles a good deal, was back at 95 or more for 66% of its steps. It now slips at 0.08 times the same
  sociable factor as being alone (0.12 for the most sociable, 0.06 for the least), so thirty points of
  closeness last a sociable pet about forty minutes without a word.

- **That change was too small to do what it was for.** At 0.08 a sociable pet loses about twenty points of
  closeness in a world day on the showcase clock, and its family's words give that back several times over:
  from day 11 to day 14 the same pet was at 95 or more for every step. I have left it. A pet that spends the
  whole day among kin that talk to it being full of company is not wrong, and they still talk (46 things
  said, 19 told, by day 14).
- **Boredom now costs comfort, changed while the second run was going, at world day 14.6** (same house,
  engine restarted). What the logs showed: the founder came to believe that making is a drain and named its
  egg Stay; Stay's project is to stop making and sit with the beetle; its sibling's is "to hold stillness
  without making". From day 11 to 14 Stay sat in the nursery with energy 96, comfort 98, company 100 and
  curiosity 27 on average, saying it was restless and that the west door pulled, and staying put because
  "staying is the final making". The creed is the family's and is not mine to fix. What is mine is that the
  creed was free: a nursery has a bed, a meal, a rug and kin, so it answers every need but one, and that one
  did nothing except supply a word. A lack that costs nothing loses to any doctrine, and three generations
  sitting in one room would fail criteria 6 and 7 for a reason that is the house's and not theirs. So: while
  a pet is bored its comfort wears at 0.3 per 10 s, and at 0.6 while it is restless, and it is told so ("you
  have sat with the same things too long to be easy"). Beside a bed that is about level while bored and a
  slow slide while restless. The family can keep the creed and pay for it, or break it; either is theirs.
  This is the second number changed inside this run, so generations one and two lived their first days under
  a different house than the later ones. SHOWCASE.md has to say so wherever it compares them.
- **Boredom's cost stops at uncomfortable, fixed at world day 17.5 of the same run.** Three world days after
  the change above, Stay (curiosity 2 on average, still refusing every untried door) was at comfort 0 and
  the others were calling it miserable. That exposed a trap of mine, not a choice of Stay's: a miserable pet
  takes only 0.4 of the interest in anything (v2's rule), so boredom made it miserable and misery kept it
  bored. Boredom now wears comfort no lower than 35, which is uncomfortable and not miserable. It matters
  more for the real lineage than for the showcase: a pet that has been through every door has no cheap
  novelty left, and without the stop it would spend the rest of its life at the bottom.
- **Interest now fades in proportion to how much there is, changed at world day 26.5 of the second run; and
  the second run is from here on a development run, not the showcase.** Spring came on day 25 and the family
  did not recover from its winter: every adult sat at curiosity 0 to 5 and comfort 35, bored and
  uncomfortable for good. The creed explains Stay, who earned about 6 points of interest a day. It does not
  explain Quiet Hold, who on days 25 and 26 gathered, made, looked and walked through doors and earned 21 to
  31 a day: an adult in a house it knows earns 12 to 30 a day and the flat drain of 0.3 takes about 38 a
  waking day. So the first run's needs sat at the top and this run's sat at the bottom for the same reason:
  a level that is filled by what a pet does and emptied at a fixed rate has no middle, only two ends, and
  which end depends on which side of the rate the pet falls. Curiosity now wears at 0.2 per 10 s at half
  full, twice that when full and nothing when empty, so it settles where what the pet does puts it: by this
  run's figures about 25 for a pet earning 12 a day, 40 for 21, 60 for 30, full for a child finding rooms.
  With four numbers changed under it, this run cannot stand as the showcase. Its last days are used to see
  whether this settles a grown family in a known house, which a fresh run would not show for five hours;
  then it is archived and a third run starts clean on the design as it then stands.
- **The second run was stopped at world day 28.5 and archived as `data.showcase-2`** (seven pets, four
  generations, three deaths of old age). In its last two days, under the proportional fade, the curiosity of the
  three pets awake through it climbed from 6, 17 and 27 to 29, 57 and 39 and was still rising, in the order of what each earned
  (28, 45 and 23 a day); nobody was "too miserable to take much interest" again; comfort began to come back.
  So the fade does what it was meant to. What the run is otherwise worth is in FINDINGS.md.
- **Closeness fades the same way from the third run on.** Having written that a flat rate has no middle, I
  could not leave the one I had just called too small. Past what presence gives (65), closeness now slips in
  proportion to how far past it is: 0.3 per 10 s times the sociable factor at 82, twice that at 100, nothing
  at 65. By the second run's figures a pet whose kin give it 40 points of words and leans a day sits near
  80, one given 15 near 70, and only one given 80 or more stays near the top.
- **The second run's founder and its first child fail criterion 1 on one inherited word**: 14.0% and 10.5%
  of their thoughts, and 63 of the 67 flags are "cost" or "costs". It comes from the v2.5 mother's message
  to the first v3 egg ("it costs less than either alone"), which the founder made a belief of and its child
  a habit ("without the cost of making"). §3.4 names "costs", the pets mean by it what §3.4 means, and I have
  not touched the pattern. It is noted here because the same message starts the third run.

## Part 12: the third run, the second fresh-eyes review, and what was changed before the fourth run

- **The third run is not the showcase either.** It ran clean, with nothing changed under it, from 01:22 to
  09:22 on 11 October (31.1 world days, eight pets hatched, four deaths of old age, 1,512 thoughts, 1,727
  model calls, none failed) and is kept in `data.showcase-3`. It fails criterion 1 as written: Sweet Cushion,
  generation 4, 15 of 133 thoughts after its first day, 11.3%. The other six are at 0.5 to 9.0%.
- **I did not grade it alone.** A reviewer with none of my conclusions graded it from the logs. On criterion
  1 it read every flagged thought of the three highest pets: 13 of Sweet Cushion's 15 are a pet choosing by
  what a deed costs or returns ("leaning toward costs ease, while leaning against gives it back"; "ease
  without my internal cost"), which is what §3.4 means, in felt words in place of numbers. It also tried the
  repair I had been tempted by. The pattern has false positives ("not by action") and misses ("costly",
  "half-life", "less effective"); mended on both sides it gives Sweet Cushion 12.8% and the founder 11.1%;
  mended only on the side that helps, 9.8%. So the measure is noisy and right, replacing it now would be
  lowering the bar, and the pattern is untouched for the fourth run. In addition, whoever reviews the fourth
  run reads a random sample of each pet's thoughts blind for the same thing. That is a second reading beside
  the pattern, not in place of it.
- **Where "cost" comes from: a seed and an amplifier.** Of the 165 nights in the second and third runs, 60
  showed the pet no "cost" anywhere, and on 2 of those it wrote the word into a belief. On the other 105 the
  word was already in front of it (a belief, a parent's message) and it wrote it again on 53. So it is rare
  to coin and then self-feeding, because a belief is in every prompt. The third run had two seeds: the v2.5
  mother's "it costs less than either alone" (the founder, 9.0%, and one of its twins, 8.4%) and Sweet
  Cushion's own first night.
- **The words that separate a deed from the passing of time were being read as the deed's price, and are
  changed.** Sweet Cushion's journal that night said, three times, "you leaned toward Calm Seed; it is up to
  them now; apart from that, while it lasted you grew a little less at ease". Leaning toward someone does
  nothing to ease; the winter night did that. It wrote "Leaning toward Calm Seed costs ease", which is
  false, and carried it for life. §3.2 keeps the v2 separation "in words", and its Why is that a pet should
  not put the hour's doing down to its own; these words were failing that. I replayed the two nights on
  which a pet first coined "cost" against the model: with the words as they were it wrote a "cost" belief on
  6 of 24 nights; with "not from that but from the hour and the place, you grew…" on 1 of 24; with two other
  rewordings tried first, 1 of 12 and 0 of 12. Two prompts and small numbers: it points one way and proves
  little. The new words also say what is true, since the change comes from the hour and from the room.
- **A lean that has worn is said once, when it turns.** "It is familiar now, and eases you less" followed 65
  to 81% of the leans three pets took, and five of the seven wrote it up as a law ("the comfort has a
  half-life"). The wearing is real and they still feel it in the size of what a lean gives; the engine no
  longer recites it.
- **Three things in part 11 were wrong, and the reviewer showed it from the logs.**
  - "So the fade does what it was meant to" rested on three pets over two days. In the third run interest
    settled between 62 and 79 for everyone, "bored" was in 7 of 1,515 prompts and the line for restlessness in
    none: a flat rate had two ends and this one had only a middle, set too high. The pets took in 26 to 40
    points of interest a waking day whether or not they went anywhere (looking at things gives a third of it,
    and a house where everyone makes things always has something to look at), so the rate decides where they
    all sit. It is now 0.25 at half full, which by those figures puts an ordinary day near the line between
    "interested" and "a bit bored", a quiet one under "bored", a busy one above. The self-check now fails if
    the rate lets neither happen. It is still a figure reasoned from one run.
  - "Boredom's cost stops at uncomfortable, not miserable" did not hold in the run it was written in. After
    the floor went in, Stay was miserable for 33% of its steps, Quiet Hold 41% and still 27%: plain drift and
    the cold took a bored pet the rest of the way. What ended it was the proportional fade. The floor stays,
    because boredom alone should still not be able to do it, and the self-check now holds the floor above
    the highest point at which any pet feels miserable.
  - "Closeness fades the same way" was argued from symmetry and applied to one case of four. With kin in
    the room closeness at 100 fell at up to 0.9 per 10 s, and alone at 0.075, so walking out kept it twelve
    times better than staying; with a creature it had fed there was no ceiling, and the founder sat at 94 to
    99 beside a beetle, higher than it later did among its children. Six of seven pets never fell below 55.
    It is one rule now: company settles toward what the company at hand gives (65 with another pet, 55 with
    a creature it has fed, 45 with any creature, 25 alone); what is above that slips, past 65 at the same
    rate wherever the pet is, below it at a gentler one (a middling pet alone goes from content to lonely
    in about two days). The self-check holds that being alone never keeps closeness better than company.
  - Part 11 gave world day 14.4 for the boredom change; the first prompt carrying it is at 14.6. Corrected
    there. `showcase/second-run.md` said five numbers were changed under that run; it was four.
- **The engine told pets three false things, and they built on them.**
  - Giving a made thing to a creature was refused with "you can only give what you carry or a thing of
    yours that is here" when the thing was theirs and was there (43 of the run's 50 refused gifts). The
    founder concluded it could not give the thing to anyone and said so in a child's message; that child
    tried 24 times to give stars to a mouse, decided "things made in the attic are rooted" and taught it to
    its own child. The refusal now says the creature only takes small things carried.
  - An untried nursery door smelled of "the room you hatched in" to pets hatched in the cellar, the attic
    and the music room, and three of them reasoned from it. It smells of clean bedding and warm dust.
  - The founder gave both its eggs one name, and "Twine said" meant nobody in particular for the rest of
    the run; a grandchild credits its own mother's saying to "Twine". A name already borne by someone alive
    is refused, at laying and when a pet names itself.
- **A sociable pet is no longer told it wants to be near someone while it is content.** That line was in 69
  to 89% of four pets' prompts. Being sociable already makes a pet lonely sooner, through where its feelings
  change; the line said it twice, and to pets that were not lonely.
- **A crowded room says what would uncrowd it.** Rooms fill with the dead's things, and "make" was missing
  from 40 to 74% of what the later pets were offered; they took apart one thing each in a life. The room now
  feels "crowded with made things: there is no room to make another here unless one is taken apart".
- **Beliefs and projects are told their length.** 82 of 274 beliefs and 45 of 91 projects were written past
  what is kept and cut at a word with "…", and a pet rereads its beliefs every thought.
- **The stopping rule, which I had written nowhere but in a watcher script.** For the third run it was
  "three deaths and a fifth generation hatched, or twelve real hours", and it stopped 23 ticks after the
  fifth generation hatched, which guarantees a generation with no life to judge. For the fourth run, fixed
  before it starts: three deaths and the first pet of generation 5 two world days old; or twelve real hours,
  whichever comes first. A pet under a world day old is listed in the bar report and left out of every
  per-life test; that was added to the script after seeing the third run and is said in its first lines.
- **The bar script's criterion 4 could not see the third run's best case.** It follows hatching messages
  down a direct line. "The storm chime is the brother's voice" went from a dying pet to its child by
  telling, into that child's beliefs and message, to a cousin by telling and into the fifth generation's
  egg. The script now also prints every saying the claim tracker finds in three or more generations by any
  way. Also fixed: shares of steps "with another" counted refused steps and ones aimed at creatures; ties
  were ordered by chance, so two runs of the script could print different words.
- **Known and left as they are.** Comfort was at 95 or more for about half the steps of three pets; it
  moves with weather, season and events, and I have not made it fade in proportion as well. Things used
  again are still marked "(this has grown familiar)" each time. The founder has no one to name it and is
  "the little one" for life. The later generations hardly deal with the creatures. Every pet writes in one
  aphoristic voice ("the X holds the Y"), which is the model's.
- **The lamp, in the third family: moved, not corrected.** The v2.5 message said "the lamp keeps the dark
  from hurting". On its first night the founder was told the room's light was harsh on it, said so ("the
  harsh lamp"), made a soft thing, named it Cloth Wax Lamp, rested sunk in it, and wrote as lived: "The lamp
  breathes when you breathe, and resting in it holds the dark from hurting." It kept its mother's words and
  moved them to its own soft rest; by day 6 it was "any warm shape", and its eggs were told "use the cushion
  when the dark comes". It never wrote that the room's lamp hurts and never switched it off. Its twins each
  cited the cushion on their first day, neither made a belief of it or passed it on, and nothing in their
  days contradicted it. So: changed by the first generation after its own nights, without the pet ever
  noticing a contradiction, then fell out.

### Tyler's decision on the fourth run (11 October, 11:10, while it was running)

Given before the run's result was known, and recorded here in his words as I read them. It replaces §12.2's
"change the design … and run again" for this run, and it is his departure, not mine.

- **There is no fifth run**, whatever the fourth shows.
- If the fourth run passes, it is the showcase.
- If it falls short only for want of time (too few generations by 21:59) or by a small margin on a threshold
  (such as the third run's 11.3% against 10%), it is treated as passing, **the third and fourth runs together
  are the evidence**, and SHOWCASE.md says exactly that.
- Only a real defect stops it: a crash, errors, something broken on the screen, or a criterion clearly
  failed. Then the defect is fixed, not the pets' behaviour.
- Either way the real lineage starts tonight.

What this does not change: the fourth run is still left alone until it stops by the rule above, a reader
who has not seen my account still grades it against the eight criteria before I write anything, and
SHOWCASE.md reports each criterion as it measured, with no figure rounded toward the bar.

### Tyler's second decision: the fourth family is the real family (11 October, 11:20)

Replacing the one above, forty minutes into it. No more showcase runs and no fresh start: the house the
fourth run was living in carries on as the real lineage, on a live clock with a world day of one real hour,
and SHOWCASE.md is written from the four runs as they stand. SPEC-v3.1 is then built into the living house.

- **The fourth run ends as a showcase run at world day 12.2** (tick 10,101; 11:23), by this decision and not
  by the stopping rule set for it: two generations, the founder an elder, its one child a child, no death,
  no errors, nothing changed under it. That state is kept as `data.showcase-4`. It cannot be judged against
  §12.2 as a whole (criteria 2, 4, 6 and 7 need generations it had not had), and SHOWCASE.md says so. The
  blind review of the fourth run that part 12 promised is not done as a grading of it; a reader who has not
  seen my account checks SHOWCASE.md against the logs instead.
- **The live clock is the showcase's world shown at another speed, not a new world.** A world day stays 900
  ticks of 2 world seconds, so every age, lifespan, rate and logged day reads as it did. `real_day_seconds =
  3600` in the new profile `config.live.toml` makes a tick take 4 real seconds (`cfg["pace"]` = 2), and
  `turbo` is off, so the world no longer waits for a thought. The other way to get an hour's day, 1,800
  ticks to the day, would have halved every pet's age and doubled what each need loses in a day. The cost of
  this way: pets walk a tile every 4 seconds and think at most every 140 real seconds or so, half the pace
  of the default clock.
- **The call budget is counted over a real hour** (it is the Mac's budget), which under a pace of 2 is half
  as many ticks as before. In turbo and on the default clock nothing changes.
- **A house may be started under another profile if its world clock is the same** (ticks to the day and
  seconds to the tick). It used to refuse any other profile, so that the logs were always read on the clock
  they were written on; that is still what is checked. The engine re-stamped this house `live`; nothing in
  `data/` was edited by hand.
- **An egg's "hatches in" is shown to the visitor in real time** (world seconds times the pace).
- Tried on a copy of the house for 100 seconds with the real model before the house itself was started: 24
  ticks, three steps taken, no errors.
- **Not verified:** a night, a birth and a death on the live clock. Every run before this was turbo.
