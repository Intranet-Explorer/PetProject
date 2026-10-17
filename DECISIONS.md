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

## Part 13: v3.1, things the family can discover

SPEC-v3.1 built into the living house. Tyler was asked for the two things its §0 says to ask: the radio's
news source (he chose NPR's top stories, beside the forecast and "On this day") and the encyclopedia (he chose
the edition with pictures, `wikipedia_en-simple_all_maxi_2026-09.zim`, 2.9 GB, from download.kiwix.org).

### How it was built

- **In a separate worktree, not in the folder the house runs from.** The live engine is kept alive by launchd,
  so a crash would have restarted it on whatever half-written code was in its folder. Everything was written
  and checked in `../PetProject-v31` on a branch and merged at the deploy.
- **I stopped the live engine once by mistake**, at about 12:20 on 11 October, with a `pkill` whose pattern
  matched it as well as the test server I meant. It shut down cleanly, launchd started it again about twenty
  seconds later, and the house and family were as they had been, less one thought in flight. Test servers are
  now stopped by their process ids only.
- **The house is started with `./run.sh start live`**, not `./run.sh start` as §9.3 has it: this family lives
  on the showcase's world clock (part 12, last entry) and the engine refuses to start it on another.

### Arrivals (§1)

- Counted from the tick the house was first loaded by v3.1 code (`house["v31"]["at"]`). One at a time and in
  order: a discovery that cannot come yet holds back the ones after it.
- **None of the new actions is announced with a stage.** A pet that grows into a stage is told what it can now
  do, and that list is v3's. Chalk, a tune that stays with it, a creature that no longer runs, a book: each
  tells the pet what it could do when the pet meets it.
- **Chalk is a bit that never turns up before writing has arrived** (`late = "writing"` in house.toml), then
  comes in deliveries like any other.
- **The music box is the nursery's**, the only one in the house. "One night" is taken as: at night, with a pet
  awake somewhere. Only pets awake in the nursery hear the tune well enough to keep it, so it plays again on
  later nights until one has. If a day and a half pass with nobody awake at night, it plays by day.
- **The book waits for the encyclopedia** and, by the one-at-a-time rule, so do the strangers behind it.
- **A foundling appears in the farthest room the family has found**, never behind a door nobody has tried:
  the spec allows either, and an egg in a room that does not exist yet would have meant making the room
  without anyone finding it.
- `arrivals.force` (§9.2) brings each a twentieth of a world day after the one before.

### Writing (§2)

- A wall's inscription remembers how far along the wall the writer stood, so the view can put it there.
- **Whose hand**: its own; kin by what they are to it (the five relations the engine knows: parent, child,
  sibling, grandparent, grandchild); someone living that it knows, by name; the visitor's; otherwise "a hand
  you don't know". A great-grandparent's hand is one it does not know, as the spec's "long dead".
- **A scrub names the writing by where it is and how it begins**, and only the (at most three) inscriptions a
  pet is shown can be named. The writer is told if it is there to see; if not, it finds its words gone when
  it next comes into the room.
- "Writing over a faded one restores it" is read as: the same words (alike by the claim tracker's measure) on
  the same wall or thing.
- Writing gives a little interest, wearing with repetition like anything else. Not in the spec; without it a
  pet has no felt reason to write a second time.

### Songs (§3)

- A note is written `"<pitch> <short|long>"`, the pitch one of fifteen: do re mi so la, and each with `low` or
  `high` before it.
- **A listener picks a tune up by ear only if it knows no version of it.** Otherwise every hearing would add
  another variant and a repertoire of eight would fill with one song.
- **Taught, a pet's own version gives way to the teacher's.** That is what "exactly" has to mean for a pet
  that already had it by ear.
- A song bequeathed is the children's at once, exactly, and marked as left to them.
- How a tune "sounds" (rising, falling, level, turning back on itself; slow, quick, unhurried; low, high) is
  worked out from the notes. There is no "sad": nothing in five notes says so.

### Taming (§4)

- Trust is per creature and per pet: 2 for food it likes, a little for each minute a pet stays still within
  three tiles or keeps close to it, less for a pet rushing by, 3 lost to a chase and 1 to a loud thing used in
  its room. Tame at 6; no longer tame below 3. A creature already fed before taming arrived starts with what
  its feedings would have earned.
- **A tame creature that is chased does not leave the house.** It goes to the far corner and thinks the worse
  of the pet. Wild ones flee as before.
- **When its pet dies it goes to the child it trusts most**, or failing children to another of the family, and
  stays tame to them (§4 Why: "stays with the children").
- **The mouse senses a leak one world minute ahead**: the leak is put off that long when a tame mouse is in
  the room it will come to. A storm it senses in the last hours of the day before.
- Creatures now die of age only if some pet has their trust; wild ones still come and go as before.
- Two creatures of one kind (a parent and its young) answer to the same word in an action until one has a
  name. `ponytail:` first match wins; name them apart.

### The radio (§5)

- **The forecast's text is written by the engine** from Open-Meteo's numbers (the host v3's real weather
  uses): it serves no prose. "On this day" is Wikimedia's feed of selected events; the news is NPR's top
  stories, title and summary.
- The box is called "dial box" in the house. A pet is never told what it is.
- It speaks to whoever is awake in its room; next door it is "something talking, too muffled to make out".
- Each source is asked at most once an hour and only once there is a box in the house. The whole of every
  reply is kept in `data/radio/fetched.log`.
- Cleaning also strips quotation marks, so nothing the box says can close the quotation it is shown in.

### The book (§6)

- Searched in the process with `python-libzim`; nothing is served and no socket is opened (checked by
  running a lookup with sockets disabled).
- **Titles before full text**: the question's own words are tried as article titles, in order, and only then
  the book's full-text index. "Why does it rain" finds Rain, not a song called "Why Does My Heart Feel So Bad?".
- The pictures in the edition Tyler chose are not used by anything.

### Strangers (§7)

- **A family is a mark on a pet (`family`), not a second lineage.** One house, one log, one clock; the second
  family's founder is generation 1 of its own line.
- **Before the foundling arrives the house keeps v3's limit of four.** From then on it is five in the house
  and three of a family. A family already over three when it arrives loses nobody; it lays no more until it
  is under.
- A pet of the other family is "a stranger" until the two have been awake in a room together for eight world
  hours, then "Sol, of the other family". Two unfamiliar strangers in a room are both "a stranger".
  `ponytail:` first match wins.
- A foundling's body is drawn fresh from the house's seed and the tick it arrived on.

### The packet (§8)

- The new lines are cut, after v3's own, in the spec's order, and each cut keeps the newest: the clearest
  inscription, the box's last words, the three songs last sung, the last passage read. The inscription a pet
  stands in front of has a line of its own that is never cut; what is sung to a pet arrives with what is said
  to it, which is never cut.

### What the v3.1 check on a copy showed (§9.2), before v3.2 was laid over it

A copy of the living house, on the real model, in turbo, every arrival forced: about four world days, 157
model calls, none failed, no errors. All six discoveries came once, in order, each with its moment. The
founder scratched "dusk" on a wall within a quarter of a day and read it back later ("The west wall says
'dusk'…"). Quiet made up a song, "Rain Delay"; it was sung five times and taught once, and the new child Hush
has it. The foundling hatched. A mouse had come to trust the foundling most of anyone (4.8 of the 6 that
makes it tame). Nobody switched the box on and nobody asked the book, so "each ability used at least once by
a real pet" was not yet met when v3.2 replaced the plan; the two are checked together (part 14). The founder
died of old age in the copy at fifteen days.

## Part 14: v3.2, a house you can read at a glance

SPEC-v3.2, built in the worktree beside v3.1 and deployed with it in one restart.

### How it was built

- **Tyler's addition, 11 October: the art is data.** "The kind catalog, sprite mappings and room layouts should
  live in data files, so I can add more asset packs later just by dropping them into assets-incoming and asking
  you to map them." So `view/assets/` holds `packs.json`, `sprites.json`, `kinds.json`, `rooms/<type>.json`
  and `sounds.json`, documented in `view/assets/README.md`; the view's code names no tile, file or pack; the
  engine reads the part that is rules (kinds, layouts) from the same files and serves the folder at `/art/`.
- **The pack came by Tyler's hand.** itch.io's page serves Ninja Adventure free, but the last step of the
  download was refused on my side, so he put the zip in `assets-incoming/` (§1.3).
- **The v3.1 view was stopped part-way** when this spec replaced it. Its lists and sound (Walls, Songbook,
  Library, the radio's voice, song playback) compiled and were kept as the base; its drawing of the room was
  replaced.
- **Four builders worked at once** on parts that share no file (the art data, the room, the pets' sprites, the
  page), against written formats, while I did the engine. A reader who had seen none of it then judged the
  page cold (§10.3).

### Things are kinds (§3)

- **A recipe is `{kind, material, color, size, name, purpose}`.** The spec's list has no size. It is kept
  because size is how "a bigger one gives more" works (materials.toml), and a pet could always choose it: it
  was each part's size.
- **A thing uses one bit**, the one that gives it its material. Before, it used one per part, and nearly every
  thing had one part. Stages still limit how large a thing a pet can make (the old limit on parts: a hatchling
  up to medium).
- **One kind was added to the spec's list: a "treat"**, the only thing a sweet (eaten) material can
  sensibly be.
- **A kind rules materials out (`not`)**, and the model is only ever offered a kind in a material it can be:
  the reply's shape has one variant per material in reach.
- **Things that hang** (picture, mirror, shelf) go to a free place on the north wall (`wall_slots` in the
  room's layout), take no floor, and are refused when the wall is full.
- **Joining two things**: two of a kind stay that kind; otherwise the more complex kind of the two (each kind
  has a rank, 1 to 3); two different kinds of the same rank make a mobile (of stuff that hangs and moves) or a
  sculpture; and anything whose kind cannot be of the material kept is a sculpture. The spec's sentence can be
  read more than one way; this is the reading in which "the more complex of the two" is ever used.
- **The migration** (§3.2) is `view/assets/kinds-from-parts.json`: a thing's material and the shape of its
  largest part decide its kind; three or more parts make a mobile or a sculpture; two parts of different
  shapes that are noisy make a wind chime, soft a nest. Colour and size are the largest part's. It never
  yields a kind that hangs, so nothing in the house jumps to a wall. Names, owners, materials, uses and
  heirloom histories are untouched, and the parts are dropped. The table as it applied to the living house is
  at the end of this part.
- **What is written on a thing is the thing's** (v3.1 with v3.2): it is kept when the thing is given or
  taken, moves with the thing if the thing turns up in another room, and goes when the thing is taken apart,
  joined into another, eaten or stolen (logged as "gone with the thing").
- A pet's picture of itself at night is still made of shapes. That is its drawing, not a thing.

### Rooms (§4)

- **A layout decides where fixtures stand.** An unmovable fixture is moved to its layout tile when the house
  is loaded; one that can be moved is left where pets or the visitor put it. Tiles the scenery's furniture
  takes are blocked for the engine too, and anything made, lying or standing there is shifted to the nearest
  free tile once.
- The engine still walks a pet in a straight line a tile a tick. The view draws the walk around the
  furniture (§4: "the engine's position stays authoritative").

### Life on screen, and plain words (§5, §6)

- **The "now" line** is put together by the engine from who acted last, what it is doing, who is beside it
  and the last thing anyone finished, with no model call.
- **Every finished step is kept for about a world minute, numbered**, so the view can play it once and not
  again after a reload.
- **Stage words**: hatchling and child are both "little one", youngling "young one", adult "grown", elder
  "old one". The spec gives four words for five stages. Pets are told nothing new: their own packets still
  say what they said.
- **Moments name what a thing is**: "Po made a yellow candle it calls 'glow'", "Po joined a candle and a bell
  into a mobile it calls 'ringing light'", "… gave Bo a yellow candle, 'glow'".

### The nuzzle loop (§9)

- **Cause.** v3 stopped the loop by not offering a lean to a pet that already felt close. Part 12 made
  closeness settle in the middle of its range, so no pet ever felt close again, and offer, accept, lean back,
  accept came round for as long as two pets were in a room: 15 of the 34 thoughts on the live clock before
  this was found, and 30 of 133 in the v3.1 check.
- **Fix.** What a lean leaves is remembered between the two pets: having leaned together, neither can offer
  the other a lean for eight world hours (`nuzzle_again_hours`), and the action is not in its list. An egg can
  still be leaned on. Nothing else about company was touched.
- **Check.** Two pets that lean and accept whenever they can, kept as lonely as can be for a world day, may
  not spend more than a fifth of their thoughts on it.

### Added while v3.2 was being built (Tyler, 11 October)

- **Taking a name.** In the living house the visitor called a hatchling Garry and it answered "Yes, I am
  Garry", three times, and stayed nameless: only the exact words "my name is X" counted. Now, while the
  visitor has offered a name, the pet has an action for it (`take_name`, in its list only then), and any
  clear yes to that name takes it: "my name is Garry", "I am Garry", "I'm Garry", "call me Garry", "yes,
  Garry". "I am not Garry" and "who is Garry?" do not. A pet that had already said yes has its name when the
  house next starts (its last few sayings are read from the log). The pet's card says "you called it Garry;
  waiting to hear", then "it took the name Garry". This went into the living house at once, as a small
  change by itself (commits 9219ab1, 5bcab5e on the v3.0 code; two restarts, about a minute down), and Garry
  has his name.
- **Unnamed pets have labels of their own**: "the first one", "the third one", by the order they came into
  the house, in words. They were all "the little one", and "the little one told the little one something to
  keep" said nothing. A pet still calls its kin by what they are to it ("your mother"). This comes with the
  v3.1 and v3.2 deploy.
- **The start script waits for the old engine to finish stopping.** Starting again at once failed ("Bootstrap
  failed: 5") and left the house down until it was run a second time.

### A mistake, and what was changed because of it

- **An archive was written to.** Two builders were told, by me, to open the third run's archive
  (`data.showcase-3`) with `PET_PAUSED=1` to test old recordings. Paused did not mean read-only: the new
  engine brought the house up to date and saved it (`house.json` converted to kinds; four empty tables added
  to its log). Both stopped as soon as they saw it. The changed files were put back from an untouched copy
  made at 11:33 the same day, with Tyler's leave, and all 47 files were compared and match; the recorded
  frames were never touched. The copy is kept as `data.showcase-3.as-of-1133`.
- **A paused engine is now read-only**: the house is brought up to date in memory so the view can draw it and
  nothing is written, not the house, not a pet's files, not a table in its log; and a visitor's command to a
  paused house is refused. The self-check hashes every file of a house before and after opening it this way.

### More added before the deploy (Tyler, 11 October)

- **A door come unstuck is told.** When a draught lets go of a door, the pets in the room on each side are
  told "the west door has come unstuck" (one that is asleep, when it wakes). Nothing told them before, and
  Quiet sat for hours in the workshop, which has one door, believing it shut. Its beliefs are left alone. At
  the first start under this code the engine also tells, once, of every door a draught ever shut that is free
  now, so Quiet hears it. (The first deploy looked back only two world days and Quiet's draught was five days
  old; the look-back was widened and the house restarted a second time, at night with everyone asleep.)
- **Real weather is on** (`[weather] real = true`): once an hour the engine asks Open-Meteo what the sky is
  over the Twin Cities (§6.6, built in v3 and left off). It is on for a house on a real clock, which the
  living one is; the turbo and test profiles (`showcase`, `viewdev`, `v31check`) turn it off, because their
  clocks are not the real one and their checks should not depend on the weather outside; and a paused house
  never asks.
- **The v3.1 branch is pushed** to the private repository as a backup, and main after the merge.

### The cold readings (§10.3), and what they changed

Three readers who had seen nothing of the build looked at the page in turn, wrote down what they could tell
from each screenshot before looking anything up, and then checked themselves against the page's own data.
The spec asks for one reading and one repeat; the third was to check the fixes made after the second.

- **First reading** (24 views): what room it was, 24 of 24; what every creature was doing, 13 of 17; how it
  felt, 17 of 17 from the cards and 0 of 17 from the room; what every object was, 0 of 24. It read a mother
  and child swapped because a thought bubble sat nearer the wrong one, saw two pets drawn on one spot, and
  took chalk for feathers and clay for potatoes. Changed: every bubble has a tail to its owner and the
  owner's name; pets stand side by side; mood shows in the body (the sad, sitting and happy frames); bits
  are smaller than made things; everything drawn has a hover card; a power cut darkens made lights too; the
  drawer no longer squeezes the room.
- **Second reading** (37 views): rooms 37 of 37; doing 24 of 28; feeling 25 of 25 from the cards; every
  object 1 of 37. "The page does not pass the ten-second test": loose things and made things could not be
  named without hovering, the book read as a crate, the music box as a chest, the memorial as a metronome,
  and a death was not in the headline. Changed: **when a room comes into view everything in it is named for
  eight seconds** (a made thing by its kind, a fixture by its name, one label for each kind of bit), and a
  Names button holds the labels on. This departs from §3.3 ("object names are not drawn permanently") only
  as far as §0's test needs: they are not permanent, and they are the kind, not the pet's own name for the
  thing. Also: made things carry a pip in their maker's family colour; the book, music box, hot pipe, rock,
  sun shaft, memorial and sculpture were redrawn; the five mood faces became bold signs; a stone is always
  labelled and nothing is drawn over it; a death, a birth, an arrival or a storm is in the headline for a
  while; a storm shows on window glass in every room that has any; cards say what a pet is doing and what it
  wants on separate lines.
- **Third reading** (24 views, after those changes): doing 14 of 18; feeling about 14 of 18 from the cards
  and still about 0 from the room alone; every object about 5 of 12 while the names were showing and 0 of 7
  after they had faded. "The page does not pass the ten-second test. It nearly passes for what pets are
  doing, and fails for feelings and for objects." Its reasons: with up to 28 labels they piled on each other;
  once they fade, furniture is recognised and small made things and loose bits are not; the mood signs were
  misread (a storm cloud as "bothered by the storm", a heart as affection); and a long thought on a card
  could make the whole room drop a scale. Changed after it, and **not read cold again**: labels are kept
  apart with leader lines and grouped by kind; a mood's word shows beside its sign when it appears; a
  hatching leaves shell and a tag; cards are one fixed height.
- **Where that leaves §0's test.** A stranger can say what room this is at once, and who is doing what and
  how each feels from the sentence at the top and the cards. They cannot name every small object in a room
  at a glance unless the names are showing (on entering a room, on resting the pointer over it, or with the
  Names button). Thirty-two kinds in sixteen pixels, recoloured, do not all read by shape alone. This is the
  part of v3.2 that is short of its own test.

### What the check on a copy showed (§10.2)

A copy of the living house, on the real model, in turbo, every arrival forced, 2.7 world days and two world
days past the last arrival: 184 model calls, none failed, no errors. Kept as `data.v3.2-check` (the earlier,
v3.1-only copy as `data.v3.1-check`).

- **Every existing thing became a kind**: all 37 in the house (and those in the dead's records), by the
  table below; none without a kind.
- **The nuzzle loop did not recur**: 5 of 55, 7 of 54 and 7 of 52 thoughts in the three world days had a lean
  or an accept in them (it was 15 of 34 on the live clock before the fix), and three leans were refused as
  "you leaned together not long ago and are close still".
- **Things made by kind** by real pets: charms, wind chimes, cushions, sculptures, treats, a bowl, a blanket,
  a bell. The foundling's first words, to a pet of the first family: "I made this. It listens to the wind,
  just like yours."
- **Not shown by a real pet in any check run**: the radio switched on, the book asked, a creature tamed,
  called or named. In the copies nobody happened to go where the box and the book were; in a fresh house
  with everything in one room two hatchlings learned the music box's tune and sang it four times, and were
  too young for the rest when the deploy came. These are covered by the scripted checks only, and are worth
  watching for in the living house.

### The deploy (11 October 2026, 16:03)

`data/` was copied to `data.backup-v3.0-2026-10-11` at tick 14,190; the engine was stopped, the branch merged
into main, the view built, and the house started again with `./run.sh start live`: about a minute and a half
down. A second restart followed four minutes later, at night with all three pets asleep, to widen the
look-back for doors (above). The arrivals count from tick 14,192.

**What the 124 things made before kinds became** (§3.2: the standing ones, the ones that are gone, and those
in the dead's records), by the table in `view/assets/kinds-from-parts.json`:

| became | how many | from (material and the shapes of its parts) |
|---|---|---|
| charm | 31 | springy ring (15); springy ring+ring (4); quiet dot (3); hard ring (2); glassy ring (2); glassy dot (2); springy dot (1); springy bar+ring (1); glassy dot+ring (1) |
| nest | 28 | soft ring (10); soft blob+ring (9); quiet ring (4); soft blob+dot (2); quiet blob+ring (2); soft blob+circle (1) |
| cushion | 16 | soft blob (14); springy blob+ring (1); soft circle (1) |
| candle | 9 | bright dot (5); warm dot (2); warm blob+dot (2) |
| blanket | 9 | warm blob (7); warm blob+ring (2) |
| bell | 8 | noisy ring (6); noisy ring+ring (1); noisy dot (1) |
| wind chime | 5 | noisy bar+ring (4); noisy dot+ring (1) |
| mobile | 4 | springy ring+ring+ring+ring (1); springy dot+ring+ring (1); glassy star (1); bright bar+dot+dot (1) |
| stool | 3 | springy bar+ring (1); springy bar (1); quiet bar+dot (1) |
| doll | 3 | soft star (2); soft dot (1) |
| lantern | 2 | bright ring (2) |
| stone stack | 2 | heavy ring (1); heavy dot+ring (1) |
| vase | 2 | glassy blob+ring (1); glassy blob (1) |
| bowl | 1 | hard circle (1) |
| flute | 1 | noisy bar (1) |

"Storm rest pulse", the small teal ring of the spec's first paragraph, is a teal charm; "quiet reed bar" is a
green stool. Forty-two things were standing in the house and none is without a kind.

**Screens of the living house** just after: `showcase/v32/live-1.png` (the workshop at night, Quiet and Chet
asleep by a candle), `live-2.png` and `live-3.png` (the nursery and the music room), `live-4.png` (the family
tree).

## Part 15: v3.3, alive

SPEC-v3.3, Phase A, built in a worktree on branch `v3.3` and checked on a copy of the live house before
the one restart. Phase B is outlined only (the last section here).

### Two layers (§1)

- **The body is `engine/body.py`, its menu `activities.toml`.** Each tick a pet that is not carrying out a
  step it decided picks the best-scoring activity for the moment and does it: 3 to 10 world seconds once it
  is there, which is 6 to 20 seconds of watching on the live clock. An activity names how it is carried out
  (`do`), and several share one, so a new activity is a few lines of data.
- **What the body really does goes through the same code a decided step uses** (`use`, `look`, `gather`,
  `go`, the songs), with the same wearing-off of doing a thing again. So the tuned economy is the one the
  body lives in; it is not a second, easier one. The small effects an activity adds of its own (grooming's
  comfort, dancing's lift) are in `activities.toml`, in the units of `config.toml [effects]`.
- **The body is never news.** Nothing it does asks anyone to think: a body singing or babbling at another pet
  leaves that pet's "something happened" untouched. That is what keeps the model calls where they were.
- **The mind's reply changed shape**: `{thought, focus: {type, target, words}, steps: 0 to 3, expect}`. It
  is no longer offered `observe`, `rest`, `move` or `follow` (the body does those); everything else it could
  do it still can, and those stay the mind's alone. An empty `steps` means "carry on".
- **A thought stays with the pet until the next one.** Before, an intention ended with its last step and what
  it expected was scored then. Now the steps finish, the thought goes idle, the body carries on, and the
  expectation is scored when the pet next thinks, over everything that happened in between. Otherwise a reply
  with no steps would be scored over no time at all.
- **How often a pet thinks is unchanged** (`min_think_seconds` and the rest of `[clock]`). Measured in the live
  house before this, a pet asked about every 70 world seconds; that was already the floor, so shorter lists
  of steps do not make it ask more often.
- **The body never goes into a room it has not been in, never makes, speaks words, writes, gives, lays an egg
  or opens a door that has not been opened.** It does walk into rooms it knows, at most every four world
  minutes unless its focus sends it.
- **Five decided steps were shortened** (make, combine, compose and teach_song from 16 world seconds to 14,
  lay_egg from 20 to 14) so that nothing a pet does keeps it on one spot for more than 30 watched seconds.
  This is the only change to the older tuning.
- **Habits** are counts of activity, kind of room and time of day. A settled habit adds to that activity's
  score there and then; a young pet watching a parent gains a fraction of a count each time; the card and the
  life record show the strongest in words.
- **How §0 is measured** (`engine/alive.py`, from a new log table `doing`): in watching time on the live
  clock, whatever clock the copy ran on. "Different things" are different activities or decided steps;
  setting out for something and never beginning it counts only as walking. "Standing still" is the longest a
  pet spent on one spot doing one thing outside a resting pose (nap, sitting by the window, sitting with kin).
  The script also prints the longest a pet kept to one tile across several things in a row, which §0 does not
  ask for and decided steps (making three things at a bench) can stretch.

### Order (§2)

- **A thing put away is still in the room**, still itself, still doing what it does; it has `on` (the name of
  what holds it) and takes no floor. Whatever happens to the shelf happens to what is on it: moved, they move;
  taken apart or carried off, they are on the floor again.
- **Where storage is**: the storeroom's crates and shelves, the workshop's bench, the cellar's shelf and the
  attic's trunk hold things from the start; the nursery, garden, pond, greenhouse and music room have nowhere
  until someone makes a shelf, box, basket, chest or crate (chest, crate and wall hook are new kinds). In a
  room with nowhere, tidying sets a thing against the wall beside others of its kind.
- **Clutter** counts what lies loose: made things not on something, not on the wall, not in their home and not
  set straight, and half for each dropped bit. Two or fewer is tidy, more than six a mess. Only a pet more
  orderly than the middle feels it (a small ease in a tidy room, a small wear in a mess); everyone is told
  when a room is a mess.
- **Tidying is not taking**: a pet moves its own things, nobody's, the dead's, and its young children's.
- **The crowded-room limit now counts things standing on the floor.** Putting things away makes room to make
  more, which is the point of a shelf.
- **Areas** are named from what stands together (three cushions and blankets: a sleeping corner; a bench in
  use: a making bench; a shelf with an heirloom on it: a keepsake shelf), once a world hour.
- **Everyone alive at the deploy gets an `orderly` gene**, drawn from the house's seed and its own number the
  way its other genes were, between 0.25 and 0.75.

### The visitor's music and radio (§3)

- **Music has four moods and each mood has one tune** (`config.toml [music] tunes`) that a pet who hears it
  for six world minutes picks up by ear, as "the visitor's lively tune". The pack's tracks are what the
  visitor hears; the tune is what the pets can come to sing. It is not kept before songs have come to the
  house, because a tune is kept the way a song is.
- **The radio control** before the pets have their box sets down a fixture, "little radio", in the room being
  looked at while it is on, and takes it away when switched off or when their own arrives. Afterwards it
  switches theirs. It uses the v3.1 sources and blocklist; nothing new is asked of the network.

### Getting ready to make, and the radio at once (Tyler, 11 October, before the deploy)

- **A mind set on making something has a body that works toward it.** With the focus "make", the body picks
  up bits (two, or what there is), takes them to the workbench if the room has one, and lays them out; these
  three pull hard enough to happen in order, one after the other. The bits stay in its paws: laying them out
  is handling, not making. Then the pet is told "everything is ready to make something" and **thinks at once**
  rather than at its usual time (never sooner than 20 world seconds after its last thought). What that saved
  is owed back: the thought after waits that much longer, so a pet thinks no more often than before. Once it
  has laid out the very bits it carries it does not lay them out again; it stays by them.
- **A box switched on speaks straight away**, whoever switched it (the engine sees that it has just come on),
  and again at once when the visitor asks it for something else. If nothing has been fetched yet (a little
  radio only just set down), it waits up to a minute for the first words before it gives static, and the
  engine looks for them every ten seconds meanwhile; each source is still asked at most once an hour.

### What the copy runs and the watchers found

- **The body walked back out of a room the mind had just chosen.** Now it does not leave a room sooner than
  four world minutes after coming in, however it came, and never while its focus is on something there.
- **A new hatchling with its mind on exploring did four things only** (door, door, look, wander). An activity
  now comes due the longer since it was last done, whatever the focus, which is what makes "five different
  things in any five minutes" hold for every pet.
- **Resting crept toward a quarter** for an old, tired pet and for two pets each set on being with the other.
  Past 18% of its last ten minutes a pet now does nothing passive at all, tired or not; the night is for sleep.
- **There was one tick between activities with nothing going on**, four seconds on the live clock: the next
  activity is now chosen on the tick the last one ends.
- **The first fresh-eyes watcher** (three rooms, five minutes each, a frame every five seconds, at live pace
  with the real model) could say what pets did only from the sentence above the room, found the "why" weak,
  and saw pets with no sign for half a minute. Changed: a sign over the head during decided steps too; the
  caption is the focus in plain words ("wants to be with Chet"), with the pet's own words on its card; "going
  over to the east door" while still on the way; a pet whose mind is on a thing or a pet stays near it; any
  pet may tidy; things shut in a chest are not played with.
- **The second watcher** (new, the repeat §8 allows): what each pet was doing, mostly yes; why, yes for two
  of four pets; alive, one room yes, one for most of it, one empty (four pets, nine rooms). Still open after
  it: made things carry their makers' names, which say little to a stranger (the name now shows on the thing
  while a pet uses it, and the words say what kind of thing it is; not watched again); captions crowd when
  several pets stand together.
- **Sound** was checked from the page's own log of what it started (`window.petView.audioLog`): speech, eight
  kinds of small voice, instruments, room ambience and the visitor's music, at full level in the room on
  screen and low next door. Speech was not broken in v3.2: pets seldom chose to speak.
- **The music's moods were chosen by track name** and measured loudness, not by ear (`MOODS` in
  `view/assets/own/src/data.py`).

### Phase B, outlined (§7)

Nothing of Phase B is built. What is there for it: activities, storage kinds and their effects are data
(`activities.toml`, `view/assets/kinds.json`, `house.toml`); an activity may carry `needs_tool` or
`needs_place`, which the body reads and, for now, treats as "cannot be done"; the kinds of focus are one
tuple (`actions.FOCUS`) with the activities that serve each listed per activity.

### A two-hour day for the live house (12 October 2026)

Eleven world days went by in the first night of v3.3 and three of the family died with nobody watching, so the
live house's day is now two real hours. Slowing the whole world to half speed would have undone §0 (a tick of
eight seconds, a tile every eight seconds), so the tick stays at four real seconds and everything a watcher
times stays as it was: a step, an activity, the wait between thoughts, every per-second rate, model calls per
real hour. What is counted in world days and hours takes twice as long: a life, a stage, a night, a season,
food growing back, an event coming round. The base profile has always had a longer day than this, so nothing
here is a new balance.

A house that already has a past keeps it: `world.wt` counts each tick before the change for two, so the clock
did not jump, the date carried on from day 32, and nobody got younger. The engine notes the change once in
`house["shift"]` when it first opens a house whose day differs from the profile's `was_day_seconds`; the view
reads the same two numbers for the times it prints. Left as they fall: a few things already under way that are
timed in days (writing fading, an animal's age) count their past at the new rate, so they last a little longer
than they would have. One change of day length per house; a second would need a list.

### Tidying a person can see (12 October 2026)

After a night of v3.3 Tyler could see the house was untidy and the house could not. Seven of nine rooms had
nowhere to keep anything; of 115 things made, none was a shelf, box, basket or chest; with nowhere to put a
thing, tidying meant "out of the way", which moved it a tile, marked it tidy and looked like nothing; the mess
score called every room tidy or nearly, so no pet was ever told otherwise; about 120 dropped bits lay on the
floors; and nothing ever left, so each generation's things piled on the last. Changed, in his order:

1. **Every kind of room starts with somewhere that fits it** (`house.toml`, placed by the room layouts): a toy
   chest in the nursery, an instrument shelf in the music room, a reed basket by the pond, a pot shelf in the
   greenhouse, a tool box in the garden, a second shelf in the cellar and in the attic. A room found before
   this is given its own the next time the house starts (`Engine.alive_migration`).
2. **Clutter is what a person sees** (`order.count`): every made thing on the floor that is not on or in
   something, on the wall or part of a named corner, and every loose bit. "Out of the way" is gone: a thing
   with nowhere to go is left where it lies and goes on counting. A corner is three or more of a sort standing
   together (`order.areas`), and a tidy pet will put a fourth with them. An heirloom by its stone is in its place.
3. **Nowhere left.** In a room that is a mess with nothing left to put things in, a pet is told "there's nowhere
   left to put things here: a shelf, a box, a basket or a chest would be somewhere to keep them". The crowding
   rule used to stop any making in such a room; something that keeps things can now always be made.
4. **Loose bits are tidied too**, a pawful (3) at a go, into whatever keeps things: each shelf, chest or basket
   takes 8 bits beside its things. They stay bits: anyone can take one out again to make with, and the page
   lists them on the thing's card instead of drawing them on the floor.
5. **Old things leave.** A made thing nobody has used or moved for five world days, that is not an heirloom,
   not put away on anything and not itself a place to keep things, is carried off to the storeroom by a pet
   that is tidying (its own things, the dead's and nobody's; never another living pet's). The storeroom keeps
   them on its crates and shelves. When those are full, whichever has gone longest untouched, of the newcomer
   and what is kept there, wears out and goes back to bits. (His words were "if the storeroom is full it wears
   out": read as the longest forgotten, since otherwise the first ten things set aside would stay for ever and
   nothing after them would ever reach the storeroom.) Memorial stones are not made things and never move.
   The thing goes by itself once the pet has picked it up; walking it through the house is left for later.
6. **Measured**: the house notes what lies about in each room every world hour (`house["clutter"]`, four days
   back) and `engine/alive.py` prints it beside the §0 numbers.

Found on a copy of the live house with the real model (one world day), and changed before it went live:

- **Bits overflowed.** A floor holds up to 12 dropped bits and one shelf took 8, so the music room stuck at 8
  lying about. A place that keeps things now takes 12, and "nowhere left" is also said when it is bits that
  have nowhere to go.
- **Nobody would touch a housemate's thing.** Tidying kept to a pet's own things, the dead's and its young
  children's, so one living pet's cushions and charms lay about a room for good. Now anyone may put anyone's
  thing in its place in the same room (it stays its owner's, who is told where it went). Carrying a thing off
  to the storeroom is still only for its own, the dead's and nobody's.
- **Nobody went to the messes.** Four pets spent two world days in three or four rooms; the music room fell
  from 8 to 1-3 and stayed there, and the five rooms nobody walked into did not change at all. A door now says
  so when the room beyond it is a mess ("north (to the storeroom, which is a mess)"), and "rooms you know" says
  so of the ones further off. That alone moved no mind in a world day, so the body does the walking: a mess a
  pet knows of, anywhere in the house, draws its body door by door through the rooms it knows, as strongly as a
  mess in the room it is in (`order.way`), once it has been in a room four world minutes.
- **The minds left the bodies no time to go.** v3.3 had a body leave a room by itself only with nothing on its
  mind, or exploring, or playing: "it never walks out on a focus". Sampled through a waking day, the real minds
  were about resting 34% of the time, being with someone 22%, tending 12%, making 11%, a project 12%, and
  playing or exploring 5%. Even with a project counted as free, a body could go about one time in six, and
  the storeroom and the pond room stayed at 19 and 20 things all day. The rule is now narrower: a body does not walk out on someone or
  something its mind keeps it by (be with, stay near or tend what is in the room; making, with its bits laid
  out), nor out of a mess, nor when it is minded to rest and is tired. Otherwise a mess it knows of may draw
  it. So a pet whose mind is on resting and which is not tired may get up and go and tidy the storeroom. Its
  wandering for no reason is as it was.

Tyler's rulings on that, the same day, and two more rules of his:

- **Yes to the narrower rule, with a cap: one tidying trip to another room per pet per world day.** A trip is a
  body setting off for a mess it knows of; it may take several doors, and is over once the pet stands in the
  mess. After that, until the next world day, no mess draws that body out of a room. Read as a cap on what the
  body does by itself: a mind that chooses to go, or says it wants to tidy, is not counted or stopped.
- **What the house moves to the storeroom goes into its crates** and counts as stored. Old things carried
  there did already count, but went onto whatever had room; now crates first, out of sight. What made the
  copy's storeroom go from 16 to 18 with nobody in it was the other thing the house brings there: a delivery,
  "a crate of bits", was four loose bits dropped in the middle of the floor. Those now go into the crates too
  (`order.stow`), and only what nothing has room for is left out. The storeroom had ten places for a house of
  over a hundred things, so nine things wore out in three days; the crates now take 6 (were 4) and the crates
  in the corner, which were only drawn, take 8. Twenty places. When those are full the longest forgotten
  still wears out.
- **Loose bits fade.** A bit dropped on a floor and left there is gone after `fades_days` world days
  (`house.toml`, per bit): petals and leaves after one, fluff and feathers after two, as Tyler said, and by
  the same reasoning vine, moss and reed after one and soot after two. Everything else stays. Bits a room
  grows and bits put away in something do not fade. A bit already on a floor on 12 October counts from then.

Pets still only tidy a room they are in, and a body only goes to rooms its pet has been in: a room no living pet
has found (the garden, on 12 October) stays as it is until a mind chooses to go through that door.

## Names of things only when asked for (12 October 2026)

Tyler: item names are not to show when a room comes into view; only on hover (a tap on a touch screen) or while
the Names button is held on. This takes back the eight seconds of names on entering a room (the "second reading"
above, and SPEC-v3.3 §5). Taken out with it, as the same thing by another road: a thing's name showing by itself
while a pet was busy with it. Left as they were: a pet's name plate, which does not come and go with the room but
is always under its feet, and the "just hatched" tag on a newcomer, which is not the name of a thing. View only.

## Keepsake boxes: nothing made wears out (12 October 2026)

Rule 5 of "Tidying a person can see" (old things are carried to the storeroom, and wear out when it is full) ran
on the live house for one waking day. The storeroom's twenty places were full within hours, and after that every
old thing sent there wore out the one longest untouched: 19 things in a day, three of them living pets', five
taken down off walls. Tyler stopped it (carrying-off switched off, one restart while the pets slept) and
replaced the rule:

- **Nothing made wears out.** `order.wear_out` and `order.set_aside` are gone. Only loose bits fade.
- **A keepsake box beside every memorial stone.** It appears with the stone (`life.bury`); a house already lived in
  got one for each stone it had. It has no limit, what is in it counts as put away, and a pet may take a thing out
  of it (a mind's `take_out`; the dead's things are anyone's to take, as they always were).
- **What the dead left lying about goes into their box**: a made thing whose owner has a stone, untouched for five
  world days. Not a thing on a wall, not a thing already on a shelf or in a chest, not a thing that itself keeps
  things, not a thing too heavy to move, and never an heirloom.
- **The living's things stay where they are**, however long untouched.
- My choices, where the ruling left room. *The house does the moving, once a world hour* (`order.keep`), not a
  pet that happens to be tidying there; so it also reaches rooms no living pet knows. *A thing taken out is not
  old again for five days.* *Tidying never puts anything into a keepsake box* (it would swallow a whole room,
  and the room would never read as full); a mind may put back only what belonged to the one the box is for.
  *A mind is told what a box holds in one line* ("what Garry left is kept in it: a, b, c and 4 more"), not a
  line for each thing: a box with no limit would otherwise crowd the packet. *The things in a box still do what
  they did* (a lamp left on in a box is still on), as on any shelf. *The box's picture* is the small camp
  chest (`fix.keepsake box` in sprites.json).

**What wore out was put back** (`tick.unwear`, once, at the restart): from the copy of the house taken just before
the tidying deploy, every thing the house's own list of gone things said had worn out. A living pet's thing went
back where it was (the room, the wall or the shelf if still free) and its owner was told; the dead's went into
their keepsake boxes, including five that had hung on walls, as Tyler asked. The bits those things fell into were
left where they went (in the storeroom's crates). One thing the old rule took down from the pond room wall and
put in a storeroom crate has been used since, so it was left there.

**Fixed with it.**
- *The one-trip cap leaked.* A trip was only marked done on arriving in a mess; a mess cleared on the way left it
  "under way" for the rest of the day, free to set off again and to change rooms without waiting. Now it ends
  when the pet stands in a mess or there is none left to go to, and only the door toward the mess is free of the
  wait.
- *The mind and the body follow one rule.* A body could put a housemate's thing in its place; a mind that chose
  to was told "that belongs to someone else". Anyone may now put away or hang up anyone's thing in the room, and
  its owner is told. Taking a thing out is still taking: its own, nobody's, the dead's, its children's.
- *Two messes could send a tidying pet back and forth.* With its mind on tidying and nothing it could put away
  here, a body made for the nearest known mess; if that one had nowhere left either, it came straight back. A
  mess now draws a body only if there is something it could put away there (`order.way`), which also stops a
  day's one trip being spent on a room where nothing can be done.
- *An heirloom could be tidied for ever.* With no free tile by its stone it was put on the nearest free one, still
  counted as lying about, and was moved again. It is now put somewhere else (a wall, a corner, a shelf) or left.
- *Looking at a loud thing sounded it.* A body's every act on a loud thing was marked loud; only playing with it
  or fiddling with it is now.

Not changed, as Tyler ruled: a room that settles at "a few things lie about" is lived in, and the garden is left
as it is until someone finds it (the house will still box what the dead left there).

On the page: a music box left playing now plays its tune, round again every twelve seconds, as loud as its room
is from where the visitor looks. On a touch screen a tap shows a thing's card and name for five seconds (they
used to vanish as the finger lifted). Small things seen and set aside are in POLISH.md.

## Part 16: v3.4, purpose

### Part A: bodies that go places (§1), and a room that is easier to read (§5). 12 October 2026

**How §0 is measured** (`engine/alive.py`). The log's `doing` table has two new columns: `thing`, what a pet handled
in doing something, and `walked`, the tiles it walked since the row before.
- *Handled* is a thing picked up, used, carried, put away or made with: by the body, the activities marked
  `handles` in activities.toml (play, eat, tidy, gather, tend, the stone, sitting on something, sitting by the
  window, taking a thing out, bringing a thing to someone, the bench); by the mind, the steps use, gather, drop,
  make, unmake, combine, arrange, put_away, take_out, hang, give, take, teach and show. Looking closely at a thing
  is not handling it. A window counts the different things handled in it.
- *Any five minutes* is every stretch of 75 ticks (five minutes of watching on the live clock) through which the
  pet was awake, started every five ticks. The number reported is the worst of them, beside the share of windows
  that meet the bar and the usual window.
- *Tiles walked* is counted as it walks, a tile a tick.

**A tick is four seconds of watching, so nothing is shorter than that.** The spec asks for fidgets of three seconds
at most; a fidget is one tick. "Each lasts 5 to 20 seconds" is read as two to five ticks once a pet is there.

**Fidgets** (stretch, groom, hum, babble, fiddle, look about) are marked `fidget` in activities.toml. A body never
chooses one as the thing to do. After an activity, three times in ten (six in ten while a thought is on its way),
one comes before the next activity, never two running. Its mind is not told of them, they make no habit, and
they are not counted as anything done. Fiddling and babbling happen only with what or whom is in reach.

**What a body does instead.** The menu was reweighted toward things done somewhere else in the room with a thing,
and four activities were added: *sit on* (a stool, a cushion, a rug, a bed: it goes and settles on it), *take
out* (a thing put away comes out, a few steps off, to be looked at), *bring to kin* (one of its own things carried
over to someone it is fond of) and *follow a creature*. Playing with a ball rolls it, to someone if anyone is up.
- *Things are carried.* A thing put away, taken out or brought to someone is in the pet's paws while it walks to
  where the thing goes, where before it was put away from where it lay.
- *A pull toward what it has not handled lately*: while a body has handled fewer than three different things in
  the last 50 ticks, a thing it has not just handled scores higher; and in a room with nothing new to handle it
  is free to go next door without waiting.
- *A thing just taken out, brought over or rolled is left alone for 300 world seconds* before anybody's body
  tidies it. What someone who died left, taken out of its keepsake box, is tidied back into the box if the box
  is in that room (a change to this morning's "tidying never puts anything into a box": it may put back that
  pet's own things, nothing else).

**Being with someone** no longer holds a body within three tiles of them. It is doing what they do: an activity
the other is at scores higher (the same toy, the same song, tidying or tending beside them), following goes on for
as long as the activity lasts and keeps up as they move, and standing by them is a short pause (two ticks).
**Rest** holds a body only when the pet is tired (energy at "tired" or worse); otherwise its body is as free as with
no focus at all, and it does not nap. A body may now leave the room with its mind on a project, or on being with
someone who is elsewhere, as well as with no focus, exploring or playing.

**How Part A was checked, and what it took** (a copy of the live house, real model, turbo, the live house paused):
- *First pass* (the evening of day 36 and the morning of day 37): three pets met every bar in every five minutes.
  The elder, Grey Light, did in 95% of its windows; its worst had 2 things handled and 13 tiles walked. Its mind
  had cut in on things its body had already begun (sitting on a nest, at the stone), which were then dropped
  uncounted, and an elder walks two ticks in three. Changed: a thing a body has begun is done when its mind's
  step cuts in; a body that has walked little lately is drawn to what is further off.
- *Second pass* (the rest of day 37): Purple Camo's worst window had 1 to 2 things handled (96% of its windows
  met the bar); the others met every bar. Changed: the pull toward a thing not handled lately is much stronger
  while a body has handled fewer than three in the last 50 ticks.
- *Third pass* (day 38): the numbers are in FINDINGS.md.
Tyler's ruling while the third pass ran: if it misses only "three things handled" by the same small margin,
deploy anyway and note it here; no fourth pass.

**In turbo the world waits while a thought is being thought**, so on the copy a body never acts during a thought,
as it does on the live house (where a thought takes five to ten ticks). The copy's numbers are therefore a little
harder on the body than the live house will be: more of its time is its mind's.
### Part B: wants, skills, making by discovery, tools, growing food, the book and the radio (§2 to §4). 12 October 2026

**Where it lives.** `crafting.toml` is the whole table: processes and where each is done, the materials they give,
41 rules, the kinds that take a material found out first, three tools, 20 pairs of properties that make a new one
when two things are joined, what a planted seed gives, and what a passage in the book can point at. `engine/craft.py`
carries it out (and keeps skills); `engine/wants.py` makes, meets and fades wants. Nothing in either asks a model.

**Materials are bits; what emerges is a property.** A processed material (wicker, fired clay, rope) is a bit like
any other: carried, dropped, tidied away, made with. A property that emerges from joining two things (glowing,
snug, booming) is a property like those in materials.toml, built from the same parts (a light, a comfort near it,
more rest), so everything the house already does with a property it does with these. Three of the spec's examples
needed one new thing each: *glowing* is a light that does not count as harsh at night (`gentle`); the others use
what was there. Where a table entry says more than the engine does (a jingling toy "draws kin", a honeyed treat
wins a creature over sooner), the extra is words only for now.

**What a pet is and is not told.** Told plainly: what came of a thing it tried, in the table's words; that it
"needs something with an edge"; where a thing cannot be done ("there is no water here to soak it in"). Not told:
what a kind is made of. A basket is simply not among the kinds it can make until it holds wicker; then "with this
you could make a basket" is in its packet. A pet that asks for a gated kind without the material is told only
"you have not got what a basket is made of".

**The body prepares; the mind tries; after a wait the paws try by themselves.** The spec gives the mind a new
action, `process`, and has the body carry bits to the right place. Built so: a pet that wants to find out what
water does to a reed picks one up, makes for a room with water through rooms it knows, carries the reed to the
water, and its mind is told ("you have carried the reed to the water: you could try it now") and thinks sooner.
If after 90 world seconds its mind has not taken that up, its body tries it. This last is mine, not the spec's: a
want the body serves should not die for a day because the mind was about something else, and §0 asks for
discoveries every day. The same for a word it wonders about when the book is in the room: it goes over to the
book, its mind may ask, and left long enough it leafs through for the word by itself.

**A body may now go through a door it has never been through, if finding out what is behind it is one of its
wants.** v3.3 kept finding a room for the mind. A want is the pet's own, and "the body leans toward whatever
serves the pet's wants"; without this, a want to know a room would wait on the mind every time, and the garden
would stay unfound.

**Wants.** Up to three, looked over every five ticks. Eighteen kinds in five groups (to know, to make better, for
someone, of the family, to get better). No two of a kind and never three of one group; one of the three is always
something its body can do something about, when there is such a thing. A want is met when the world shows it is,
not by a hook in whatever met it. A want that can no longer be had (the bit used up, the thing taken apart) is
dropped, one left a world day fades, and neither comes back for three days. Two wants are mine: a closer look at
a thing a housemate has just made, and (from a failed try) the tool it lacked. Not built: "the question written
on a grandparent's thing", a want for the visitor, a leak.
- *A word from the box:* the longest word in what the box said that this pet has never heard before. Crude, and it
  picks proper names as readily as "drones".
- *Preparing for rain:* a pet that has heard a forecast of rain for today, and knows a room with an open window,
  wants it shut; if it is shut when the rain comes it is told "the rain came and the window was shut". The other
  three preparations in §4.2 (moving things from the leak, gathering petals, a warm thing to the cellar) are not
  built.

**Skills** are counts of things done, read in three steps (3, 10, 25 times) and said only in words. Making: a
practised maker's things are finer (they do more when used), a step bigger, and its tools last longer. Tending:
it grows things faster and picks more. Music: a tune slips less in its ear. Tidying, reading and mending are
counted and said, and mending lets a pet mend without a hammer; they change nothing else yet. A young one
watching a practised parent make, tidy, tend or sing picks up a little.

**Tools are used where they lie, and fetched.** A pet does not carry a made thing. A tool works for anyone in the
room it is in; one in another room the pet knows comes with the pet as it sets to work ("you fetched the trowel
from the greenhouse"). Walking it through the house is the upgrade. A worn tool does nothing until it is mended:
with a hammer, or by a pet practised at mending or making. Nothing made wears out; "wears" here means blunt.

**Growing.** The house's planting beds are the five plant fixtures it always had, and a plant pot. What was growing
in them when v3.4 came goes on growing; once picked, a bed is bare until someone plants it with a trowel. Tending is
watering (nobody carries water). Rain waters the garden. Dry for two world days, a plant wilts and gives nothing.
A pot cannot be moved to another room, so "a cold night makes moving a pot inside a choice" is not built; a cold
night halves the garden's growth. Picking a ripe plant eats one of what it gives there and then and leaves the rest
beside it. Only what a pet planted counts as "food grown" in §0.

**The book** can be carried through a door by a grown pet (`carry`), a step at a time. What a pet reads can give
it a want to try something (twelve hints in the table, matched on words in the passage); it is never told a rule.

**A recipe rides with a telling.** There is no "teach a recipe" action. When a pet tells another something to
keep, the newest thing it has found out that the other has not goes with it; a young one watching its parent try
something picks it up; a child starts out knowing each thing its parent knew as likely as not. Writing a recipe on
a wall or in a message is the mind's own words, read by other minds as a hint.

**"Name it for what it does now."** A pet that joins two things into something new is told it could; there is no
action to rename a thing, so the name it gave when joining stands.

### Part B deployed, and a follow-up (13 October 2026)

**Part B went live at 07:41 on 13 October** as measured (FINDINGS: v3.4 Part B). Tyler accepted the "three things
handled" margin as he had for Part A: one or two pets with a single window of one or two, 97 to 99% of windows met.
The repeat share (7 of 12 on the second day) and the missing tool and planting are what the follow-up is for.

**Repeats.** After a pet has made the same kind in the same material twice in a world day, that pair is not
offered to it again until the next day: its mind's list of kinds for that material leaves it out, and a make of it
is refused in plain words. Everything else stays open. I read "twice" as twice that day, not twice ever; a pet can
still make two springy charms every day, and both count as repeats if it has made one before.

**Tools.** Trying to make a tool without what it takes now says what is missing ("it takes fired clay or carved
wood"); every other kind that takes a found-out material still says only that something is missing. A tool kind is
offered to a mind that wants that tool even when it cannot be made yet, so that the attempt can happen at all. The
want then carries what the tool takes; before that it points at the book, and the pet's body goes there as it does
for a word. The book has four pages of its own (crafting.toml `[[entry]]`: trowel, digging, clay, edge), found
before the encyclopedia is searched, and each points at something to try through the hints already there.

**Planting by paw.** A seed can be planted with no trowel. Planted by paw it grows at 0.7 of the rate, and a pet
can have one such planting coming up at a time; with a trowel, the full rate and as many as there are beds. That
is my reading of "slower and fewer plants". Planting by paw is where wanting something to dig with starts.

**A body tries only what a want is about.** Wants opening doors stays. A body carries a bit to where it can be
tried, and tries it if its mind has not, only for one of the pet's current wants; with no such want it does
neither. That was already how it was built; the self-check now holds it there.

**Words from the box.** A word a pet wonders about is now a thing it could picture, from a list (picturable.txt,
about 400 nouns: animals, plants, land and sky, buildings, vehicles, made things, people by what they carry, food),
less anything the house already has a word for. Not the longest word. Words already wondered about that are not on
the list were dropped once.

**The mess.** Clutter is every made thing on the floor that is not furniture the room uses: something that keeps
things, a stool, a plant pot, a rug, something too heavy to move, an heirloom by its stone, or one of a corner.
A corner is at most four tiles. A sleeping corner is against a wall and holds one bed-thing (cushion, blanket,
nest, bed-mat) for each pet who sleeps in that room, which is where it last lay down to sleep; a room nobody
sleeps in has none. A music or lamp corner is three or four of the sort standing together. Everything else of the
sort is clutter, and tidying stacks it in storage. A thing whose home is a shelf or a box is never part of a
corner, lies about while it is out, and is put back before anything else. A body taking something out to look at
holds it up where it is kept and puts it back; a mind that takes a thing out leaves it out, and where it was kept
becomes its home. Once, on arrival: every thing on a floor whose home was a keepsake box went back into it.

## Wants that lead somewhere (13 October 2026, second follow-up)

Tyler's six items after the follow-up's first day, where nobody made a tool, planted or asked the book.

**A want that names a thing leads to a want to get it.** Two kinds of want name a thing a pet has not got: a tool
whose makings it knows, and something a parent knew how to make. Each gives a step: "you want a pebble (there is
some in the nursery)" if it lies about; "you want to find out what warmth does to clay" if something in reach
becomes it and the pet has not found that out; "you want to warm some clay, for the fired clay" if it has. A step
is not one of the three wants, a pet has one at a time, its body does it first, and meeting it keeps the want it
serves from fading. A step that needs a tool nobody has is a long way down the list. One step deep: it does not
plan a chain.

**The book before the answer.** A tool kind is offered to a mind for making only once its pet has asked the book
about it, or there is no book it can reach. Its body goes to the book and asks in the want's own words ("how do you
make something that cuts"). The book's own pages now say what each tool is made of, and reading one tells the pet
(the want then carries "a carver takes sharp stone or fired clay"). A page was added for the hammer. If the book
finds nothing, the failed attempt still says what is missing.

**Planting and picking.** Bare earth in a room it knows and a seed it carries or can find: a want to plant there,
weighted by how practised it is at tending (1.5 times one plus its tending step). Something ripe: a want to pick
it. Its body goes and picks, hungry or not; a pet that has only just eaten eats none and leaves it all beside the
bed ("share" is that: what lies there is anyone's).

**Repeats.** Two of a kind in a material within three world days (a rolling 5,400 ticks), counted on arrival from
the things each pet has standing.

**Words.** A forecast's words count like any broadcast's; the list gained frost, thunder, thunderstorm, fog, hail,
drizzle, sleet, mist. The forecast only named a sky, so it now ends "Frost overnight." when the low is at or below
zero. A creature a pet has been close to becomes a thing to wonder about, one a world day ("you want to know what a
moth is: you have been close to one").

**Drawn to the book.** A pet in the book's room with a want the book might answer (a word, a tool's makings, a bit
it wants to try something on, a thing a parent knew how to make) goes over to it, is told 'the book is right here;
you could ask it: "what is clay"', and left a while leafs through by itself. Not while its eyes are tired (once a
world hour), and never the same question twice.

**Too young to read (13 October 2026, after the first day).** A hatchling cannot read, and was drawn to the book
all the same; it asked the room out loud and an elder answered. So one too young to read is not drawn to the book:
with something it wants to know it makes for the nearest elder that is up (with no elder, the nearest grown pet),
goes over, and is told 'Sven is right here; you could ask out loud: "what is vine"'. Once for each question. Its
body does not ask for it, and nothing makes the elder answer: both are left to their minds.

**Rain Rest and the carver.** Its body gets what a carver takes and its mind puts it down, for its beliefs about
stopping. Tyler: that is behaviour, not a bug. Left alone.

## Part 17: v3.5, parts

Built on 13 October 2026 by five helpers, each in its own worktree: the parts and the drawing; genes and
inventions; building and paint; seasons and food; the vending machine and base materials (added for §4.3). The spec
said two helpers at most; Tyler's message allowed three or more.

**How it was run.** The live house was not paused for real-model copies (Tyler). It was restarted once before any
copy ran, on a change that lets a copy share the model: a thought waits up to 300 seconds instead of 90, the family
keeps `data/model.busy` while it has a thought waiting or in flight, and a copy started with `PET_YIELD_TO` holds
each of its own thoughts back while that file is there. A copy's thought already in flight is not stopped.

**The parts library (§1).** 31 thing parts at 16, 24 and 32 pixels and 16 body parts, drawn by
`view/assets/own/src/parts.py`. Body plans are proportions in `parts.json`, not pictures, because every animation
bends the body; thick fur and shade are drawn by rule. The parts preview is `view/parts.html`, built with the view,
because it draws with the house's own code. An `inside` part is drawn behind its base. Four parts were added for
the uses: spade, chimes, pad, seeds.

**Bodies (§2).**
- Nightly drift is gone; the night's "body" call remains for adults and elders, as a portrait only.
- A genome with no `feet` key draws exactly as before. Once a pet has the new keys the old `limbs` gene is not
  drawn.
- The live families: the first gets a crest and a stub of a tail, the second long ears and a beak. That is more
  than "nobody changes look much overnight", and is what "differ in at least two slots" needs.
- Small steps never create a part the line never had; that is the rare thing. Ancestors buried long ago are
  forgotten, so a part can count as new again.
- Every body has one trait it can feel, so a plain pet meets the bar: it sleeps curled (comfort on waking) or
  stretched (a spring in its step).
- Dark coat: the moth is not disturbed by it, so trust builds. Small: a bit from behind the storeroom shelves every
  12 world hours, not a visible spot.

**Inventions (§3, as amended twice).**
- The uses are `view/assets/uses.json`, not `uses.toml`, so the preview draws from the file the engine reads.
- Any two things joined in a way the house has not seen make a new kind: a use if it fits one, else a curio.
  A plain `make` never makes a kind.
- A curio has three parts: the base thing's base, its own signature part, and the other thing's signature. With two
  the base thing's half could not be recognised.
- A recipe is the two kinds each in its material, so the same kinds in other materials are another kind.
- A taken name is numbered. "Loudest part" is part order: the parts have no loudness.
- Nearest existing effect: a carried light and a cart follow their owner between rooms; a keeper is a store that
  keeps food; a seat or bed is a fixed rest bonus; a chime tells tomorrow's weather once a day; an instrument plays
  the last song its user knows; a keepsake and a curio do nothing.
- The want to join appears only for two things that would fit a use, and never names the use.

**Building and paint (§4.1, §4.2).**
- Twelve projects in `building.toml`, made of the six base materials. Materials go down before the hammer, so a
  site shows on day one. The want to build leads to the hammer itself (the book, the makings), and a body binds the
  hammer after 40 seconds if its mind has not.
- With three or four pets a small project takes hours, not one to three world days; a solo big one takes days.
- The moment kind "project" is shared with the projects chosen in sleep; a building one reads "X began a …".
- The old `paint` (whole-room colours, no dye) is replaced: it needs a dye, a place and a pattern.
- A hutch only stops a tame creature going wild. A worn thing keeps its store and bit spots.

**The machine and base materials (§4.3).**
- Wood has no "light" property (none exists). Stone and the things made of it are materials, so no room grows them.
- Feeding never draws the stock down. A body with no use for what it is offered leaves it in the machine.
- "Leave" from an owner means the owner is holding the thing out to that pet.
- Stocking is a visitor message like the others; "all" fills it.
- Beyond the spec's examples, a pet's own things put away and untouched for five days are spare (one per pet per
  day), and three loose bits lying about are wanted fed.

**Seasons and food (§5).**
- Seasons are 42 world days on the live profile only (about three and a half real days); the default stays 6.
  The live house keeps how far through its season it is: at day 46 it reopens in winter with 21 days left.
- Spring rain is not raised: the live house uses the real sky.
- Food keeps in any store, not only a crafted pot or basket. Spoiling only costs stock: loose food is never eaten
  directly. Indoor pots still grow slowly in winter.
- A bed's sleep is not in the snapshot; the view shows snow by season.

## Part 18: v3.5.1, the hub (13 October 2026)

How it was run: the engine by the lead, the art and view by two helpers (the machine and its room; the sign, the
screens, the statue and the radio). Tested on a copy with stub minds for the moves (the machine and radio change
rooms), then deployed to the live house with a backup, as the spec says.

**The room (§1).**
- The hub is not one of the nine room types: it is hung on afterwards, on the outside of the storeroom (north if
  free, else west, east, south), as room `rhub`. On the live house that is cell [0, -1], north of the storeroom.
  A new house gets it at birth; a lived-in one on load.
- The machine leaves the storeroom at the restart, not when the hub is found: whoever is in the storeroom is told
  a door stands where it stood, and the door is wanted like any untried door. Until someone goes in, "Stock the
  machine" says nobody has found it.
- The radio moves into the hub when the hub is found (and a radio that arrives later goes straight there), and is
  no longer movable. Its name stays "dial box": the pets know it by that name.

**The lit sign (§2).** The engine keeps the last eight headlines from moments (inventions, discoveries, hatchings,
deaths, things built, statues, rooms found) and tomorrow's weather; the view draws the time from the clock. On the
live house, which uses the real sky, "tomorrow" is the real forecast two hours on (one world day on the live
clock), from the same weather host as before. A pet in the hub reads tomorrow's weather once a day and each new
headline once (two at most at a time), as events: no thought is woken for it.

**The screens (§3).** Three screens, each a "book" that cannot be carried. A pet uses one nobody else has used in
the last world hour; at a screen it may ask again after a quarter hour (the heavy book still asks an hour). The
screens are dark until the book has arrived in the house. What was asked and read stays on the glass.

**The statue (§4).**
- Two projects in `building.toml`, one per family, on fixed plinths ([5, 4] and [7, 4]); five stone, sixteen
  spells with a hammer. A statue eases whoever is near it (cozy).
- The eldest living of a family whose founder is dead is given the want outright once the hub is found (in place
  of its oldest want) and holds it three days before it can fade; it is told where the hub is if it has not been.
  Once begun, everyone has the want to work on it, as for any project.
- A founder's family is traced through its children (the dead are put away without it). On the live house the
  founders are the little one (family 1, never named) and Purple Camo (family 2).
- A statue of an unnamed founder gets a name through the `name` action ("statue"), wanted by the grown of that
  family; Purple Camo's statue carries its own name. The plaque's words are the founder's last words.

**The radio (§5).**
- SomaFM was ruled out: its terms forbid playing its streams in any other site or app without written permission,
  and its API is closed to third parties.
- Chosen: Radio Paradise's four mixes, Serenity, Mellow, Main and Rock (mellow to lively). Listener-supported,
  no ads; its FAQ recommends other players (VLC, "just about any other radio app") and gives direct stream links.
  It says nothing about web pages either way: the house's page is a player on Tyler's own Mac, for him alone.
  Its now-playing address (`api.radioparadise.com`) is public but undocumented. Tyler should confirm or veto.
- The engine asks what song is on at most once a minute while the radio is on; it replaces the three old hosts
  on the radio's allowlist (the weather host stays, for the real sky). A pet is told the kind of music on a station
  change or a new song, and feels it like the visitor's music of that mood; it may dance. Songs heard are kept in
  `pet["box"]` as the box's words were.

**Art and view.**
- The machine is option D built from Karsiori's pack (`view/assets/own/src/works.py`), taller, with a plain glowing
  "THE WORKS" plate in place of the pack's lettering. It stands at the west end of the north wall, not the middle,
  so the north door's tile stays clear; the landing pad is beside it. The pack is credited in
  `view/assets/third_party/CREDITS.md`, with its itch.io page as the source (it came with no licence file).
- The three screens stand under the lit sign at the east end of the north wall; the radio set is by the east wall.
  The hub has a crate to keep things in, as every room does.
- The ticker, the glass of the screens and the statue are drawn in code. The glass is too small to read in the
  room: clicking a screen opens a large green or amber panel with the same text. The statue is the founder's elder
  picture in a stone ramp at twice a pet's size, rising inside a scaffold while it is built.
- The page plays the station only while the page's Sound is on; a browser that refuses to start it plays it on
  the next click, and says so beside the control. It is quieter when another room is on screen.
- The view no longer shows the box's speech; "What the box said" in the story keeps the record of the old radio.
- The extra Karsiori packs the spec names (gears, pipes and cables, buttons, neon signs) were not in
  `assets-incoming`, so none were used.

### Deployed (13 to 14 October 2026)

Deployed at 23:46 on 13 October (live tick 61195). Open Hand found the machine room at tick 62009, about 800 ticks
after the restart (under half a world day), and took fibre from the machine at once; within a world day three of the five living pets had
been in, the machine had been bought from and fed thirteen times, and three pets had heard the station's songs by
name. Rain Rest, eldest of the second family now that Lean is dead, began Purple Camo's statue at 63792 and has two of its five stones on
the plinth. Before it had the project it made three stone stacks it called "first one's mark", "first one's
statue" and "foundling's third stone": the want was understood, and the making came first.

No pet used a screen in the first world day. `wants.book_room` returned the first room with a book in it, which
was the attic, so every hint and every walk to look something up led to the heavy book. Fixed on 14 October
(03:21): the screens come first once they are found and the book has come, the hints name them, and a pet asks
whichever book is in the room it is in. The heavy book is still read when a pet is in the attic.
After the fix, at 65790, Rain Rest came for stone, took two, read the lit sign (tomorrow's cloud and two
discoveries) and asked the left screen "what is stone"; the article stayed on the glass. A pet at a screen is
still told it is at "the book" ("the book is right here", "you read in the book"): the same encyclopedia, but the
words are left over from the heavy book (in POLISH.md).

### The book's matching, and stacks made for a statue (14 October 2026)

Tyler asked for both. The book (the screens and the heavy book alike) now looks up the main noun of a question: the
words before "of", "for", "to" and the like, less the question words, tried whole and then by the last of them
("how to make supple reed" -> "reed"). Where a title is only a list of meanings, it takes the everyday or natural
sense from the title's brackets (zoology, plant, material, rock, weather and so on, in that order); full-text search
comes last and skips any article whose first sentence is about a company, a band, a film or a person of that kind.
The house's own pages (crafting.toml [[entry]]) are still read first. Of the last ten questions, three answers
changed: Shell Oil Company became Shell (zoology), and Immunity (medical), twice, became Reed (plant).

A stone stack with "statue" in its name (or anything with stone in it so named), that a pet may take apart, does
for a piece of stone for a statue that still wants stone: a pet that wants the statue built goes to where one lies,
takes it up as a piece of stone and sets it on the plinth like any other. Only while a statue lacks stone: on the
day this went live both founders' statues had all five, so it waits for the next statue.

## Part 19: v3.5.3, the page (14 October 2026)

How it was run: the lead built the base (the tabs and addresses, the slim header, the House tab's shorter cards and
grouped Visit controls, the shared building blocks, the read-only endpoints, the portraits, the two small fixes);
one helper built the Family tab and the pet pages, another the Story and Things tabs. Tested on a paused copy of
the live house, then on the live house.

- **Addresses.** `#/house`, `#/house/<pet>` (watching that pet: a pet page's "Watch now"), `#/family`, `#/pet/<id>`,
  `#/story`, `#/things`, `#/thing/<id>`, `#/lab`. The drawer is gone; the Lab is its own page, reached by a small link
  at the foot of every page and in the Visit bar.
- **The header** keeps the name, the world's day, time and season, and Sound. Ambience, volume, light/dark,
  Replay and Stock the machine moved to the Visit bar, under "More".
- **House.** The cards say who, stage, what it is doing and what it wants; a feeling is the small picture it was
  before. A card now opens the pet's page instead of following it (following is the Follow menu, or clicking the
  pet in the room). On a phone the room fills the width and the page scrolls down to the cards (a strip that
  scrolls sideways) and the map; the Visit controls fold behind one button.
- **Repeated names** are numbered by the order the pets came ("Grey Light II"); the stored name is untouched.
  "Named after" is the nearest earlier pet of that name, its own line first. In a sentence, a repeated name links
  to whoever bore it on that day, or to the pet whose page it is.
- **Families** are worked out from the tree (the dead are put away without their own word for it): each first of
  a line with no parent, in the order they came, is a family.
- **Portraits** (§8): the engine has no picture library and the pets are drawn by the page (petsprite.ts, from the
  genome), so the first page to draw a pet sends its PNG (1x and 4x) to `/portrait/<id>.png`, where the engine keeps
  it under `data/portraits/`, one per pet per stage, and serves it from then on. The dead are drawn as they were in
  life. The only thing the page can write there is a PNG of at most 64 KB for a pet that exists, once.
- **Weather in the story** is recorded from today (`skies` in house.json, once a world hour; the page only reads it).
  Earlier days show their season alone: the live house uses the real sky, so a weather for them cannot be worked out.
- **Things** are keyed by their id; something made before today and since gone has none recorded, and is keyed by
  when it was made and its name.
- **§10:** a model reply with writing in another script is asked for once more; what is left of it after that is
  taken out; each time is noted in `data/<lineage>/<pet>/foreign.jsonl` (beside training.jsonl). A pet at a screen is
  told "the screen is right here", "you read on the screen", and the story says it "asked the screen".

## Part 20: v3.5.4, drive (14 October 2026)

How it was run: the lead built the shared pride and feats (`engine/feats.py`), clearing, curiosity, doors, messages,
projects, names and the bars (`engine/bars.py`); one helper built firsts, bests, ambitions and pets noticing
(`engine/firsts.py`), another the Works, the board and the visitor's star (`engine/works.py`, `engine/board.py`).
Tested with the scripted brain on copies of the live house, then for one world day on a copy with the real model.

- **Clearing (§1).** "No room to make" is gone. A room with `make.crowded` made things on its floor (boxes count,
  as they did for the old cap) feels "cluttered with old things". Its clutter is what may go by §1's list, oldest
  first; what is in an ordinary box goes too, the emptiest box first, and an emptied box can then go. A pet's own
  clutter, or a dead pet's, becomes a want to take it to the machine, weighted above other spare things
  (`machine.clutter_weight`); the body carries it there like any want it serves. A dead pet's clutter goes into its
  keepsake box at the hourly sweep instead of being carried, as before. A bored pet that knows of a door it has never
  been through is told so, wherever it is, so a pet that has not found the machine room goes looking.
- **Curiosity (§2).** Novelty wears off by kind as well as by thing (`novelty.per_kind`): ten bowls are as familiar as
  one bowl handled ten times. Something not handled for `new_hours` is new again. Fidgets give none. A pet that grows
  bored is told so once ("nothing here is new to you any more") and thinks. **Comfort** was pinned by every warm or
  fragrant thing nearby; its drift is now in proportion to how comfortable it is, so it settles lower instead of at
  the top.
- **Doors (§3).** A pet that has just come through a door does not go straight back for `body.back_seconds` unless
  something calls it (someone it wants to be with, the visitor, an event, a want that began after it left), or it is
  cornered. A pet stays `body.stay_seconds` before the body moves it on unless the mind sends it. Going next door
  needs a reason: a room not seen for `stale_hours`, kin there and nobody here, a mess it minds, nothing to do here.
  Walking about inside a room ("wander") is counted apart from doors in the bars: it is not a door.
- **Messages and projects (§4).** The night no longer shows a pet its own last message; it writes fresh from its
  life, at most four sentences (the engine cuts to four). A project that is a "don't" (a way to be, not a thing to
  do) is asked again once that night, with why.
- **Names (§5).** The parent is shown the family's names and told an egg can have one of its own or honour someone.
- **Firsts, bests, ambitions (§6, §7, §9).** A first is keyed by what was done: a kind, a kind with its nature, a
  process, a tool, a room, a passage. The record was filled from what the house still has (things in rooms, the last
  200 things gone, each pet's kinds and tries, recipes, tool firsts), so a kind made and gone before `gone_things` was
  kept can be a first again. A kind with a nature ("the first noisy bowl in the house") is a first too, which makes
  house firsts common at first; they thin as the house fills its record. Bests sum the maker's practice, size,
  sturdiness, the kind's rank, and newness, so beating a parent needs a harder or newer thing, not just more practice.
  The ambition is chosen by the engine at hatching (no call) and from numbered offers at night.
- **The Works (§8).** The first goal is 12 scrap (a lamp for the cellar), not the spec's example 30: at today's
  feeding rate that is about a world day. A thing counts once, and only if it is at least 12 world hours old.
- **The board (§11)** replaces the sign's forecast and headlines: the Works line and its meter first, then up to four
  feats, one to a pet, the young and the rarely named sooner. It turns every world hour, or at once for a new feat.
- **Numbers** are in `config.toml [drive]`, `[novelty]`, `[body]`, `[make]` and `works.toml`.
- **Clearing, after the test day (Tyler, 14 October).** The nursery stayed at the cap all day: its floor was ten
  things, six of them boxes and baskets, and the one thing §1 lets go (an empty box) was Grey Light's, who had never
  found the machine room. So anyone about may now put a crowded room's old things into a box or onto a shelf with room
  in that room (a tidying job, pulling like a mess: `order.clear_pull`). Only the owner feeds its things to the
  machine. Statues stay: the machine refuses anything made or named as a statue (on the copy, Open Hand fed "first
  one's statue whole", its parent's, before this).
- **The Works' first goal is 3 scrap**, then 6, 10, 15, 20 (Tyler: small enough to pay off within a world day; the
  copy fed it five in its test day). "Nearly full" is from 0.6 of the goal.
- **Names that begin with an article** ("the letting go") keep it when an action names them: the machine could not
  take one, and the live house's "you could not use the letting go (that is not here)" was the same fault.
- **Ambitions** are said to others in the engine's plain words ("Open Stone means to be the first of its family to
  warm cloth in its life"); the pet's own words are for itself and its page. Two pets cannot take one first on the
  same night.

The test day (a copy of the live house with the real model, ticks 77711 to 79511, after one restart of the copy for
the article fault): every §0 bar passed but four. Rooms at the cap (the nursery, 20 world hours) and the Works (not
reached at 12) were fixed as above and checked on the copy's own nursery and scrap count, not by another test day.
Charms were 6 of 13 things made (Tyler: too few to judge; watched on live). v3.4's busy paws is a near-miss: its
bar takes each pet's worst five minutes, and four of the five pets handled two things there; 96% to 99% of their
five-minute windows had three or more, Open Stone's 86% (the live house misses it on some days too).

## Part 21: v3.5.5, a small round (15 October 2026)

Tyler's five points after v3.5.4's first live days, built together and tested on a copy with the real model.

- **Firsts count what a thing is.** A house or family first is a new kind, process, tool or substance. A new nature
  on an old kind ("make:charm|bouncy") is now at most its maker's own first. A kind invented by joining counts as new
  only as the first joining of those two kinds ("join:charm+charm"): on live, charm joined with charm under new names
  had been a house first each time. What a process gives is its own key ("got:felt"), and the words "the first felt"
  belong to that key alone, so pressing fibre after fluff is "the first of its family to have pressed fibre", not a
  second first felt (Green Seed, days 61 and 66). A house that kept firsts before this derives the new keys once from
  the ones it has.
- **"the first first clear wax base"**: a kind whose own name begins "first" is said "a first clear wax base, the
  first in the house".
- **A target that left (fix b).** When a step's pet or thing is not there when it begins or when the pet arrives, the
  step goes after it once instead of failing: through the door to the room the pet went into, if that room is next
  door; for a thing that has gone, to the nearest made thing of the same kind in the room, or through the door to the
  thing if it was only moved next door. Otherwise it is told where the other went ("Green Seed is in the music room
  now", or "another room" for a room it has not been in), not "there is nobody like that here".
- **Cluttered counts loose things.** The nursery felt "cluttered with old things" with ten things on its floor and
  none of them loose: crowding counted boxes, baskets, stools and sculptures. It now counts made things lying loose
  (order.loose: not furniture, nothing that keeps things, not on or in anything, not one of a corner), less statues and
  sculptures. The cap stays at 10.
- **Going straight back** is reported both ways: every return within six real minutes, and the empty trips among
  them, in and straight out with nothing done there but doors, walking about, looking about or following kin. On the
  live house's five and a half v3.5.4 days that was 25% and 3%.

The test day (a copy of the live house with the real model, ticks 89780 to 91580, beside the living family over the
same hours on v3.5.4): no errors. Straight back 11% (empty trips 6%; live 24% and 5%), stays 4.4 real minutes, doors
7%, no room at the cap, 0 "no room to make", projects 0 don'ts, five kinds made, six firsts (one house, two family).
The Works built its wax. Targets gone: 2 of 69 steps failed for it, against live's 18 of 223; 2 steps went after a
stand-in and 2 were told where the other had gone. Near-misses, deployed and noted:
- **Curiosity** 40% (bar 50 to 80%): the live house was at 41% on the old code over the same hours, so it is the day
  (a night and a slow morning), not this round.
- **Charms** 2 of 8 things made, 25% (bar 20%); live made 11 of 21 as charms over the same hours. Eight is few:
  watched on live.
- **Bored, then something new within a world hour** 6 of 12 times (bar: most times; v3.5.4's copy 8 of 12).
The copy had about half live's thoughts, giving way to it (12.6 calls a pet a world day), so it made eight things.

## Part 22: v3.5.6, the skin (15 October 2026)

Crusenho's Travel Book, Wood and Holo Book on every tab, built to the mockups in `assets-incoming/skin-mockups/`.
View only: the engine is unchanged.

- **The family colours are a shade darker for text.** §2 says the mockups' colours reach 4.5 : 1; measured against the
  sprites' own fills they do not: `#1f6f8b` is 4.2 on paper and 3.5 on the Wood card, `#a3366a` 4.7 and 3.9. Text uses
  the nearest darker shades that reach 4.5 on every panel a name is written on (the lightest is the selected tab):
  `#165266` and `#842b55` (a third and fourth family `#45510d`, `#653492`), and the accent `#833214`. Everything else
  in §2 is as given.
- **One look.** The skin decides the colours, so the page no longer switches to dark, and the light/dark button is
  gone. The Lab stays plain (system face, the skin's colours).
- **The pixel face** fills v3.5.3's slot (`--pixel`) from `skin.css`; the old pack face (Ninja Adventure's) is no
  longer named in `packs.json` and its file is gone. Toriko is used at 16 px and 32 px only (a rule in `skin.css`
  holds everything else at 16). **Body text stays 16 px at 1280 px; no "large text" setting:** Toriko is drawn for
  16 px and reads cleanly there. Names, tabs and headings are 32 px on a desktop, as §5 asks.
- **Whole-number scales.** Every frame is 9-sliced at x1 or x2 of its slice; the buttons and bars are x1 as in the
  mockups, the rest x2. Pixel art too: the small portraits on a desktop's "Elsewhere" lines are drawn at their size,
  not shrunk. A browser cannot scale a cursor, so the three cursors are kept enlarged (x3 arrow, x2 hand and pencil,
  each with a x2 copy for a sharp screen).
- **The desktop House tab** is the mockup's game screen. The columns are 256 and 262 px (the mockup's 262 and 270),
  so that at 1280 x 800 the room is drawn at 3x; the wood sign hangs over the frame's top edge and a little of the top
  wall rather than above the frame, for the same reason. When the cards or the right column hold more than the
  screen, that column scrolls (a thin bar); the room never does. From 1000 px wide the House tab is the game screen;
  narrower, the phone's one column.
- **Fitting 1280 x 800.** On a desktop the room's panel leaves out its name (the sign over the room says it) and the
  creatures and the radio (they are in the room, on the map and under Music; warnings stay); the board shows three of
  its lines and the Works; the map's frame is Wood at x1. With that the room is 3x and the right column needs no
  scrolling with today's board.
- **What moved on the House tab.** "Lately" (the moments beside the room) is gone from it: the Story tab has them all.
  The status chips show only what is wrong (a power cut, the engine away), not "you are here". Follow and Names stay,
  in the room's panel. The visitor's toolbar has Care, Talk and More; Music and the radio, and the rest of More
  (ambience, volume, Replay, the Lab), open as paper pop-ups from their buttons, as Stock already did. Naming (Poke,
  a name, Star, Let go) appears at the top of the left column once a pet or a thing has been clicked in the room, and
  in the column on a phone. A phone shows the groups as rows of three buttons; they fit, so nothing is folded behind "Visit".
- **Cursors (§8).** The arrow everywhere, buttons and links included; the hand over the pets in the room and over
  every card; the pencil in the text box. The room's canvas sets its own cursor, so the room sets the hand inline.
- **Hover names (§9)** were already the room's way (the "Names" switch still holds them all on); the hover card is a
  paper strip now. The Things grid's tooltip (`view/src/pages/tip.ts`) carries the kind, the maker and the place as
  well as the name, so the grid lost nothing by not printing names; a second tap, or the name in it, opens the thing.
- **Holo (§1)** is the board on the House tab, the Works' goal and its segmented meter (one segment a scrap, thirty at
  most), and the machine room's screens when one is opened (blue, or amber for the amber screen).
- **A pet's page** is one book page; ambition and bests come first, then family, now, body, words, made, life.
- **Separators are dashes.** Toriko draws a middle dot as a raised tick, so the page's " · " between facts is " - ",
  as in the mockups (in `dom.el`, which builds every line, so engine words get it too).
- **The fresh reviewer** (phone screenshots only) did the four v3.5.3 tasks in 2, 2, 1 and 1 taps. From its notes the
  board's headings are brighter, the credit is no longer faded, and the phone's sign sits higher over the frame.
  Not done, and noted: Toriko has no curly quotes, so “ and ” come from the fallback face and stand a little large; the
  House cards say a pet's name as the engine does ("Grey Light"), where the pages number it ("Grey Light II").

## Part 23: v3.5.6 follow-ups (15 October 2026)

- **Two faces (Tyler: Toriko at 16 px is only about 7 px tall).** Toriko is now for short words only, at 32 px:
  the name in the header, the tabs, every button and chip, headings, the names on cards and in the gallery, the room's
  sign and the board. Everything read (the "now" line, card lines, pet pages, Story, words, fields) is in Pixelify
  Sans (OFL, bundled from Fontsource), 16 px, or 20 px with "Large text" (under More; kept in the browser). Pixelify
  has the curly quotes Toriko lacks. Its "fi" ligature reads as "A", so ligatures are off.
- **What that cost the House tab, and how it was made to fit.** The sign is x3 on a phone and x4 on a desktop, to
  hold its words at 32 px; on a desktop it no longer reaches over the "now" strip. The board shows its newest line
  and the Works' count and meter at 32 px, with what the Works are making in the reading face (the rest of the
  board is in its title). The toolbar's buttons say "Feed" and "Window" whether or not they can be used (the title
  says why not), and below 1400 px the group labels give way, so the toolbar stays one row. At a full-screen
  1512 x 945 or 1920 x 1080 everything fits, the room at 3.5x and 4x; at 1280 x 800 the room is 2x and the right
  column scrolls a little. A phone's card puts the name across the card's width.
- **The House cards use the pages' numbered names** ("Grey Light II"), from `/api/pets`, asked for every minute and
  when someone new appears; a replay keeps the recorded labels.
- **The machine room's floor** (Tyler saw it plain grey; its paint is null): not reproduced. Its paint is null in
  every backup since v3.5.4, so that is not it; the layout and its cobblestone tiles are served, the room draws them
  at every size and time of day tried, and the skin touched no art but its own sprites and the one font file. A plain
  floor is what a room draws without its layout; the room redraws when its layout arrives.

## Part 24: v3.5.7, alive on screen (15 October 2026)

(SPEC-v3.5.7 asks for Part 23; Tyler moved it here, Part 23 being the font fix.)

**Read my own way**
- **Buttons and chips read in Pixelify.** §1's table gives Toriko to titles only (names, tabs, signs, section
  headings, banners), and the mockups' buttons are in the reading face; the font fix had buttons in Toriko.
- **Following (§2).** Rooms score by what happened there in the last minute of the house (something made, found out or
  a first; pets together; the visitor's doings), what each awake pet is at (making, or carrying two bits to make with;
  talking), and one point for any pet awake; at night, where most of them sleep. "About to reach a first" has nothing
  to go on but a pet carrying the makings, so that is what counts. The page changes room at most once in two minutes
  (an event excepted), never while a banner is up, and never within a minute of a click or a key; only its first
  look, when the page opens on an empty room, goes to the action at once. (A first build left an emptied room after
  20 seconds; the watch caught two changes 68 seconds apart, so that went.)
  Clicking a pet in the room follows it, as before; a room on the map turns following off; the chip's pop-up picks
  the house, a pet or nobody. Every change is written with its reason (`petView.follows()`).
- **The console (§3).** Its map is the old map recoloured blue, with every pet a dot in its family's colour placed
  where it stands in its room, gliding as it walks (families on blue: amber and pink, the colours the mockup used).
  The room's readout keeps time, day, sky, light and who is here; a room that is a real mess says so; the families'
  count and the creatures elsewhere are left out of it (warnings stay). The board shows three lines (the mockup's
  count) and the Works on their own. On a desktop below 1400 px the toolbar's Stock, Music and More are their icons
  alone (their names are in their titles), and below 1600 px the toolbar's group names give way, so the toolbar keeps
  one row. On a phone the console sits under the room and folds to the board.
- **Banners (§4).** What gets one is read from the engine's own words for each moment: a first "in the house" or "of
  its family", "did what it meant to do", the Works, a hatching, a death, the visitor's star. The thing on a banner is
  the one its maker made within three ticks of the moment. Every banner's moment is already on the board (the engine
  puts feats, births and deaths there). §4 says a death has no sound and §9 a low tone for a death: a death's banner
  plays the low tone and nothing else (Tyler may want it silent).
- **The thing card (§5).** A click on a thing in the room still picks it up to move, name or star it (the visitor's
  doings need it); the card says so, and the naming row has "Its page". The card keeps within the window, not the
  room, being taller than most rooms.
- **A pet's sheet (§6).** On a phone the two pages stack, left first, rather than turning. The bookmarks sit on the
  book's top edge (the sprite opens downward). The badges count house and family firsts apart. Grey Light II is dead
  in the house now, so its sheet is a dead one.
- **Things (§7).** Kind and room stay dropdowns (there are too many kinds for chips); families, marks and sort are chips.
  A phone folds the filters under "Filter and sort". The use line comes from the house's rules for the kind.
- **Story (§8).** A desktop's arrows turn two days; a phone's back arrow says "‹ Yesterday". The tree's rows were made
  taller: at Toriko 32 the names overlapped the row below.
- **Room changes** wipe in eight steps across the room; the board's marquee moves the line by position, not by a
  transform (a sliding layer went unpainted in captures).
- **The grey floor** (Tyler, 14:37, the Claude app's browser at 707 px, the machine room at night): a room whose layout
  was still loading was drawn on a plain floor, and a failed fetch of a layout was kept as "no layout" until a reload.
  Now the room on screen stays as it was until the layout is in, and a failed fetch is asked again.
- **Fonts** are bundled from Fontsource with their OFL licences; ligatures are off everywhere (a `font:` shorthand had
  turned Pixelify's broken "fi" back on).

**Gaps: asked for, not recorded, left out**
- How a thing was made ("woven at the loom", "fired in the kiln"): not kept on a made thing; a process lives only in a
  bit's name ("fired clay").
- What a gone thing was made from: `gone_things` keeps no bits.
- Firsts before day 61: the house kept no feats before then.
- Where 37 early things were made: no "made" moment for them.
- Who used a thing most: the activity log starts at tick 17663 and sees sitting, playing and using, not a thing's warmth
  or light, so "most often by" shows only where the log has three sightings or more (144 of 607 things).
- Where a thing stands within its room ("by the screens"): only the room, a shelf, a wall or a box is kept.
- Words said about a thing when it was laid down: not kept. The card shows the maker's words when it made it, claims
  that name it, and what is written on it.
- A project's progress: not kept, so no project has a bar.
- Whether a dead pet's ambition was missed: it is simply left unticked.
- Words on a stone: none are kept; the stone shows its name and days.
- Pictures for some kinds (some invented kinds, rugs) are the "?" placeholder: the thing art is not there yet (v3.6).

**Measured** (headless Chrome on the Mac, a paused copy of the house; the room's frames over ten seconds): before,
60.1 fps (worst frame 16.8 ms) at 1512 x 945 and 60.0 on a phone; after, the same, and 60.0 with a banner up.

**The fresh reviewer** (phone screenshots only) did the four v3.5.3 tasks in 2, 2, 2 and 1 taps (yesterday is the
Story tab and "‹ Yesterday" on a phone). Most interesting: a dead pet's sheet ("reads like an obituary"). Most
confusing: the lower half of the House tab on a phone (the console's unlabelled map, the scrolling board, the Works,
and the visitor's controls, whose pet they act on is not obvious). Acted on: the foot of the page wraps with a gutter,
the phone's choices are no longer cut short, a count in a title is "Made: 48" (Toriko draws brackets like C and J).
Noted, not changed: Pixelify's 5 reads like an S; a board line mid-scroll is cut at the panel's edges by design; the
tree on a phone scrolls sideways in its own box, and its families' names are cut there until scrolled to.

**The watch** (the live House tab, 75 real minutes from house hour 23.8 to about 14, a browser that never clicked,
so no visitor): while any pet was awake (265 samples of 10 s, about 44 minutes), an awake pet was on screen 96.2% of
the time. Asleep, the page stayed on the room where they slept and did not move. 16 room changes; every one that was
not an event came 120 s or more after the last (most at exactly 120 s: the house is busy enough that a better room is
always waiting, so the page moves about every two minutes by day). Three big moments in the window (two house firsts,
a family first): three banners, the page taken to each room first.

## Part 25: v3.5.8, hobs (16 October 2026)

SPEC-v3.5.8 as built, and where it was read one way.

- **Hob** is the word on the page and in what a hob is told: the packet says "you are a hob, in the kitchen"; the
  day's chronicle is asked of "a house of hobs, small household spirits". HOBS.md is the reference. The page's own
  title stays "Pet" (§8: the game's name is not in this version).
- **Names (§2, engine/names.py, names.toml):** a bank of 2,758 names; five offers from five sources (the screens,
  the bank, the family's sound, an old family name, its own life), filled from the bank where a source has nothing.
  Screen finds keep to words that read as names: Latin ranks, genus names, scriptures and gods, and words over nine
  letters are skipped, so most screen slots fall back to the bank. An old family name honours forebears or the dead,
  never a living sister. A name that fails the rules (a phrase of the family's words, a living hob's name, hard to
  say) is not refused: the egg takes the first offer, and the phrase becomes its **by-name**, which the parent is
  told. By-names from what the family says about a hob later: not built; the rejected phrase is the only source.
- **Things' names (§3):** the everyday name is the kind and one telling word, in this order: its stuff ("felt
  cushion"), its nature ("soft cushion"), colour and stuff, size, the maker's name ("Pim's cushion"), the room, then
  "other"/"spare". The maker's own name for it stands when it is one of these ("soft nest"); otherwise it is the
  thing's title, and a pet may still use the title in an action. A thing of an invented kind is called by its use
  (uses.json `everyday`: a "seat or bed" is a seat, a keepsake a charm); a curio by its base part, logged.
  The older self-checks (check.py, check_bodies, check_firsts, check_season) keep their makers' names
  (`make.own_names`); engine/check_hobs.py checks everyday names.
- **Honest kinds (§3.1):** only a "charm" is refiled, by the last everyday word for a kind in its name, else in what it
  is for (kinds.json `words`), never as a tool or a thing that hangs on a wall. Five kinds added: tile, patch, tinder
  bundle, draught stopper, sign (art: cells of the PixelLab sweeper sheet).
- **Kept (§4):** heirlooms, statues, firsts (marked on the thing from now on, and from the feats since day 61), gifts
  (owner is not its maker), things the visitor named or starred, anything in a keepsake box. "Named (titled)" is read
  as one of those: every new thing has a title now. A title shows on the page only for a kept thing.
- **Scrap (§4):** charms past a hob's three newest, anywhere; any other made thing untouched for three world days
  (`make.scrap_days`). Never a tool, a store, what has things in it, what is planted, too heavy, a lit light, or a
  bed-thing where a hob sleeps. Handling a thing (a body playing with it) now counts as using it.
- **Clearing is an ordinary activity** ("clear scrap", like tidying, orderly hobs more): found needed on the copy,
  where clearing only for a want moved 10 charms in half a world day. A hob carries up to three at a time, a room
  at a time, toward the Works. Only once it knows where the Works is (a hob that had never been there crashed its
  body for a fifth of the test window before this was fixed).
- **Materials back (§4.1):** one base material for every three pieces of scrap, from what most of them were made of,
  into the paws of whoever fed them. A thing fed for a material of the hob's choosing (the v3.5 trade, one for one)
  is not counted again.
- **The spring clean:** once, on the first start of v3.5.8 in a house with charms; told to every hob and in the
  story; scrap is wanted twice as much for three world days (`works.spring_days`).
- **The sweeper (§4.2, engine/sweeper.py):** the Works' next goal, 12 scrap, after "a third thing a day". It sweeps
  floors only (scrap lying loose, and loose bits), never a shelf, a wall or a box; brings four at a time, or what it
  has after three hours, to the Works; charges an hour between rounds and stays on its dock at night. A hob using or
  standing by what it heads for shoos it off for two hours. Bits it brings count three for one. Hobs see it like any
  creature; naming it needs it tame, as for any creature.
- **Gone things** keep what they were made of, and how, where and by whom used; the house keeps the last 2,000 gone
  things (was 200), so every charm traded in stays in the Things tab's history.
- **Recorded from now on (Tyler's list):** how a thing was made and where (`made.how`, e.g. "stitched at the bench",
  `made.made_in`); what it was made from, kept after it is gone; who uses it (`made.users`, a count per hob); what a
  hob had in mind as it made it or set it down (`made.words`, its plan's thought); a build project's progress (parts
  set in place of all it takes; a hob's own free-text project has nothing to measure); words written on a stone
  (kept on the stone after the chalk fades).
- **View:** carrying in the paws / a sack with a count / overhead; the sweeper and its dock; by-names under names;
  titles in italics; a Charms chip on Things; the chosen hob's face and name at the head of the toolbar; the phone's
  house map captioned. Notes in POLISH.md.

**Measured** on a copy of the live house with the real model, one world day (ticks 102970 to 104770), the copy
holding its thoughts back while the family has one waiting:
- Things about the house 485 to 422 (13% fewer); charms 205 to 140; none from a keepsake box or an heirloom.
- The Works built the sweeper a third of the way in; it then brought 16 things and 8 bits in 6 trips.
- 53 pieces of scrap fed, 15 materials back. No "some X" in anything told, done or seen. Every new thing's name at
  most three words, none numbered. No charm with a use in its name filed as a charm.
- One egg laid and named in the window: Pethuthus (its family's sound). Things made: wood lamp, cloth rope, stone
  charm, wood stone stack, felt charm, petal rope.
- **Near misses, noted:** charms among things made 2 of 6 (33%; the day before on the live house, 68%; bar 20%), on
  a small day: the copy had 12 thoughts per hob against the live house's 30, because it waits behind the family.
  Curiosity median 35% against the live house's 49% the day before, on the same starved thinking; thoughts from
  "nothing to do" 8% (10%), at doors 6% (9%), straight back within 6 min 36% (35%), projects that are a "don't" 0 (0).
  To be watched on the live house, with its full share of the model.
- Before the clearing fix, an earlier window on another copy: 10 charms cleared in half a world day.

## Part 26: v3.5.9, layout and weather (16 October 2026)

SPEC-v3.5.9 as built, and where it was read one way. Tested by the rule of 16 October (RUNNING.md): the page on a
paused copy at the nine sizes; the Works' list and its endless goal by the self-checks and a 30-minute smoke run on a
copy (0 errors; that copy's Works built the first new goal, a lantern for the garden); one restart for `works.toml`.

- **The room's name off the room (§1):** the hanging sign is gone; a slim Holo strip on top of the room's frame holds
  the following chip, the name, the time in amber, a weather icon (a moon on a clear night) and the season. On a phone
  the name takes its own row and the season is left to the page header.
- **Set layouts (§2):** Phone, Small, Laptop, Large and Huge at the spec's widths, columns and UI scales (CSS `zoom` on
  the panels; the room has its own zoom), centred, the world filling anything wider. The room takes the largest
  whole number of screen pixels per art pixel that fits (so 3.5 on a sharp screen, as since v3.5.6). On Small the
  page scrolls to the toolbar, the cards and the console below the room, as the table's "below" says.
- **Short windows:** the toolbar folds into one "Visit" button only when the room would otherwise be smaller than 3x;
  the console gives way a section at a time: first its room readout (the strip says the time, weather and season),
  then the map, leaving the board and the Works. Both found in review: a first version folded the toolbar at 1920
  and 2560 and the whole console at 1728 and 1920, leaving the visitor's buttons hidden and half the panel empty.
- **The world outside (§3):** drawn in code (no PixelLab call): a sky on the house's clock and season with stars and
  the moon, three layers of hills and trees in the season's colours with a slight parallax, clouds, rain, snow,
  morning fog and a storm's lightning, which the house's thunder now follows (in place of its own 14-30 s timer). The
  room's surround is a darker, blurred window onto it.
- **A display in every room (§4):** the machine room's board, smaller, on each room's clearest stretch of north wall
  (or a layout's `display`), with the time, the weather and a line; hovering it gives the line in words. Lines with no
  data of their own: the pond's water (from weather, season and cold; fish wait for v3.6), the cellar's damp and
  warmth (from a leak, a draught and the weather), the workshop's bench (what is on it, and who is making).
- **Weather inside:** sunbeams from the windows through the day, warm by evening; frost at the windows in winter;
  rain and snow on the glass, lightning, lamp pools and dark corners at night (kept from before); dust in the beam,
  fireflies in the garden at night, breath-mist in the cold, rain rings on the pond; plants that are fixtures or
  planted sway in wind (scenery plants do not).
- **The Works never runs out (§5):** 23 goals after the sweeper, cheapest first (lights for the garden, music room,
  pond room and attic; a rug and a rocking chair for the nursery; a bench by the pond; a blanket and a mirror for the
  music room; chimes, a tool box, a plant for the storeroom; resin, string and cloth in the machine; a bigger daily
  allowance, delivery and stock; a second sweeper; the greenhouse's extension in three fills), every one using art
  the house already has. Not built from the spec's examples: a new radio station (it would mean a new stream on the
  network), a gift for each hob, a weather vane and a fountain (no art). When the list is done, "the house store"
  (30 scrap) puts three of every base material in the machine each time it fills. The console shows the goal and
  "N OF M SCRAP" with its meter, and keeps it when folded.
- **The board (§6):** VT323 at 24 px (32 on Large, 40 on Huge, as big as the text round it), a 1-2 px glow on a
  near-black panel. One line at a time over two rows (two one-row lines were each longer than the panel at 24 px, so
  every line scrolled and was never whole), the newest amber with its cursor, the rest a brighter blue paging every
  5 s; a line longer than two rows scrolls slowly with pauses.
- **More pop (§7):** lamps, candles and screens glow and flicker at night; puffs and sparks at the work while a hob
  makes, then a burst, a "MADE" stamp and the thing rising in a bubble; a "+" in a need's colour when it rises by 3 or
  more, and the card's bar ticks up; speech bubbles in the Travel Book popup with a tail, popping in; a hovered door
  lights and its card says who is in the next room; portraits breathe and blink, a sleeping hob's card shows shut
  eyes and "z"s; frost on the frames in winter, a leaf caught on them in autumn (not on the now box, whose words run
  to its edge).
- **Art data:** `packs.json` has `"skin": true` for the Crusenho UI pack (its files are named by the style sheets,
  so validate.py does not count them unused); room layouts may give a `display` tile.

**Measured** (headless Chrome on the Mac, a paused copy): at all nine sizes no overlap, cut-off or sideways scroll,
the room at a whole-number zoom, no text under 16 px, the room never covered, 98-99% of the width used. 60 fps, worst
frame 16.8 ms, at 1280 x 800 and 2560 x 1440 before and after, with the world and weather running.

**The fresh reviewer** read both 1280 x 800 boards whole ("FIRST WARM REED CHARM IN / THE HOUSE: OPEN HUM").
Best size: 1512 x 982 (1440 x 900 nearly as good). Worst: 1024 x 768 (Small: the room fills the window and the rest is
below it). Acted on: the folding above. Noted, not changed: Pixelify's 5 reads as S in the clock; hob cards run past
the window's foot at desktop sizes and scroll in their column; name plates pile up when hobs crowd one spot; the
machine room's own board is caught mid-scroll in a still.

## Part 27: v3.5.9.1, charms with a cost, no numbered names, the sweeper's robot (16 October 2026)

After v3.5.8's first live day (charms 70% of things made, the bar 20%; one thing called "warm reed charm two"),
Tyler: fix forward, not roll back (RUNNING.md now: roll back only for a bar made worse or something broken).

- **Charms count lately:** the three a hob keeps count the charms it owns and those it made in the last world day that
  have gone since (the spring clean fed them to the Works, so it rarely owned three and the nudge seldom came).
- **A charm costs a base material** (wood, stone, metal, clay, fibre or sand: `make.charm_takes`) besides the bit
  that gives it its nature; a hob without one is told so. Scrap gives materials back, so there is a supply.
- **A better thing, not only a warning:** past its three, its packet says "you have made N charms lately: another
  would be worth little; the house could use ..." with one or two things: a lamp or a candle for a room it knows
  that has no light, a cushion for a room where hobs sit and none lies, and scrap for what the Works is building.
- **No name or title ends in a number** (world.unnumbered, ends_in_number): a hob's own title for a thing ("Seed
  Rest Six" is "Seed Rest"), an invented kind, a second song of a name, a built thing; things are told apart by a word
  ("other bell", "little red soft nest"), never "two". A hob's name may not end in a number word; an honoured name's
  numeral ("Odo II") is not one. The cause of "warm reed charm two": a thing of an invention of an invention was
  called by that invention's three-word name, so no telling word fitted and the old fallback numbered it; an
  everyday word is now always a catalog kind or a use's word, and the fallback never numbers.
- **The sweeper is the orange delivery robot** (PixelLab robotC, 8 stills and a 4-way drive; the dock is robots32
  #26): it faces the way it drives, turns through the stills between, and its green light blinks in code (once a
  second, four times when full; steady or slow with reduce motion). It drives round the pond, by the shortest way
  over dry tiles. Any hob can name it (a creature otherwise needs to be tame). The five kind pictures that came from
  the old sweeper sheet (tile, tinder bundle, patch, draught stopper, sign) stay: Tyler's word was about the sweeper.

## Part 28: v3.5.10, view polish (16 October 2026)

Page only, deployed without restarting the engine (the day's charm measurement ran on).

- **Evening:** one curve, `evening(hour)` (px/weather.ts), from 16:48 to about 21:36 house time, deepest 19:00-20:00:
  the sky's orange horizon and pink-lit clouds, a warm light and dusk-coloured glass in the room, a warm tint on the
  wooden and paper frames (not the blue console, which has its own light), and the halos and pools of lights that are
  on from about 18:00. The engine's phases are unchanged, so in winter the sky can be golden while the house already
  calls it night (POLISH.md). The room's surround was a 60% navy fill with a blur that wiped out the sky; it is now a
  light darkening with no blur, so stars, moon, hills and sunset show round the room at every size. The strip shows
  the time of day (sunrise, sun, sunset, moon) and, beside it, the weather when there is any.
- **Hover cards in the room** use the Things panel's card for everything in it: hobs (the whole first want,
  wrapped), creatures, writing, doors, stones, fixtures, bits; a keepsake box no longer repeats itself.
- **Things:** gone things hidden until "Show gone"; charms get one of five pendants and the colour of their main bit,
  the same for the same charm, until their art comes (the room still draws the old charm).
- **The board** is measured again once its font has loaded (the half-cut row was a line measured in the fallback
  font), steps a whole row at a time, and keeps the word before a colon with the name.
- **The toolbar:** saying and writing are one "Say…" pop-up, labelled; "Give [amber]".
- **Phone:** the room's name over a soft shimmer until it first draws; hob cards full width.
- **Following:** only the follow chip's choice is remembered in the browser; a room picked by hand lasts the visit;
  a fresh browser opens on an awake hob (it opened on a stored room before: a map click stored "not following").
- **1024 x 768** is a narrow Laptop (sides 205 / 240): the room at x2 with the hobs and the board beside it.
- **After a deploy** an open page asks for its front page every half minute and when it comes back into view, and
  reloads when the build's script has changed; one part of the room that throws (it was the Works' drawing) is
  skipped and said once, and the rest goes on being drawn. Checked by forcing the Works' drawing to throw.

## Part 29: v3.5.11, the sweeper leaves fresh bits, a day-old floor, three in a box (16 October 2026)

Engine. Self-checks, a 30-minute smoke run on a copy (Tyler chose the smoke run although this clears many things),
backup `data.backup-v3.5.11-2026-10-16`, one restart at tick 110391.

- **Fresh and in-use bits:** the sweeper takes a loose bit only after it has lain `bit_hours` (6 world hours) untouched,
  and never one a hob is doing something with, has laid out, or wants for what it means to make in that room.
- **The floor:** a loose thing on the floor (not held, laid out, boxed, shelved, planted, fixed, a tool, a lit light, a
  store, or furniture) is scrap after `floor_days` (1 world day); anything else after `scrap_days` (3).
- **Keepsake boxes** keep `box_keeps` (3): heirlooms, then the dead hob's firsts, then things a hob meant, then titled,
  then newest. The rest is scrap and goes the ordinary way, by the hobs' "clear scrap" and the sweeper. No data edited.
- **Charms** on a shelf are kept only while their owner is alive and they are among its newest three.
- **The log:** each pickup is a creature row, "swept up X, lying N hours" for a bit, "swept up NAME" for a thing.

## Part 30: v3.5.11.1 (the lamp and titles round), what the house really needs, and titles that don't repeat (17 October 2026)

Engine. Tyler, after a day of lamps (10 of 27 things made, 14 of 35 the day before).

- **Why lamps:** a room counted as lit only by a fixture or a made thing whose stuff gives light. A "hard lamp" gives
  none, so the machine room, with five lamps, still had "no light of its own", and every hob past its charms was asked
  for a sixth. The lamps it made lay on the floor, were cleared as scrap a day later, and the room asked again.
- **Needs** (`things.room_needs`): a room with no light fixture needs one light (any lamp, candle or lantern, or
  anything whose stuff gives light, not a charm); one with a seat, a cushion (or a blanket, nest, mat or rug); one with
  a meal place, a cup or a bowl; one a hob sleeps in, a rug (or a blanket or mat); one with three or more things on the
  floor, a shelf, a box or a basket. Then a tool nobody in the house has, a box of the hob's own, and the Works' goal.
  One made thing that meets a need crosses it off, and the newest such thing is in use, not scrap (`things.meets`).
- **Turns:** the line offers at most two, the longest since offered first, never one kind twice to the same hob in a
  world day (`pet["offered"]`, pruned to the day). With nothing left, a catalog kind it has never made, and "something
  nobody has made yet, from two things never joined before". The two are joined by "or", not "and".
- **Titles:** no two things about the house share a title. A second "Machine Room Light" takes its stuff, nature,
  colour or size ("Wax Machine Room Light"), else another word. Titles already given stay.
- **RUNNING.md:** a bar that moves the wrong way one day, modestly and with a clear cause, is watched a second day;
  roll back when it is worse two days running, worse by a lot, or something broke.

## Part 31: v3.5.12, a place for everything (17 October 2026)

Engine (engine/store.py, rail.py, resting.py, check_rail.py) and view. Save format: house["rail"], a `train`
creature, a `platform` fixture in every room, the store's shelves, memory shelves, house["resting"], pet["riding"].

- **What a room keeps** (store.stays): furniture, what is fixed or planted, statues and sculptures, what is on a wall,
  what the visitor named or starred, heirlooms, keepsake boxes, what is in a box (it goes with its box), anything
  used in the last world day, the one or two bed-things by where a hob sleeps, and up to its type's `belongs` of each
  kind (house.toml), with one cushion a seat and one light where the room has none of its own. Everything else is out
  of place: hobs load it on the train for the store (scrap goes to the Works instead). A box holding things counts as
  one thing and travels with what is in it, each to its own shelf; an empty box unused for a world day is scrap.
- **Made things on view** is counted as §2 counts a box: everything not on the store's shelves and not inside a box.
  The report also gives the count of everything outside the store's shelves.
- **The store** is the storeroom's own fixtures plus thirteen new ones (house.toml [store]). The floor-pile scenery of
  its layout is gone. Full, it sends the oldest thing on its shelves nobody has touched in `full_days` and that is not
  meant or titled to the Works, and says so in the gone list. The material crates show the machine's stock.
- **The train** runs the spec's route (rail.route checks it against the doors; another house gets a walk out and back
  along every branch). Each room's track is two or three arms from its doors to one platform, long enough for the
  train to stand clear of the doors, along the walls where it can; a doorway is never blocked, and a room with no way
  round its fixtures gets a track over them. It stops once a round in each room, the first time it comes, and at the
  depot. **Timing:** with one-minute stops it could not fit six rounds into the hours it is awake (it sleeps at night,
  and a world day's daylight is about 80 real minutes), so it stops 11 ticks (44 s) and runs 3 tiles a tick: about
  seven rounds a day. A hob on the track is rung at, and steps aside after 3 ticks.
- **Loading** is a body activity ("load the train"): into the cart while the train stands here, else onto the platform.
  Hauling scrap to the Works by hand stops once the train runs (except beside the machine). "Ask the train" is a mind's
  step at a platform, one thing at a time. Riding is a body activity for little ones and old ones; the rider gets down
  when its stops are up, falls asleep, or its mind has something to do.
- **The allowance:** on the day's first round the cart takes one of the machine's materials for every hob with takes
  left, and hands it over at a stop where that hob is; what it could not hand out goes back into the machine.
- **The resting place** is the garden's bottom-left corner, family by family; memory shelves go up in the attic, one per
  family, named for its founder. The move is a house event over the first 0.6 world day, one stone or box at a time,
  each credited to a living hob of the family when one is awake (not carried by the train: it may not be built yet). Two
  of the dead with the same name keep their stones and boxes apart ("the other keepsake box for grey light").
- **The rail goal** goes after the Works' current goal, like the sweeper out of cost order.
