# Pet v3: four families from one message

**No single run passed all eight criteria of SPEC-v3 §12.2.** This page is written from the four runs as
they stand, by Tyler's decision of 11 October 2026 (DECISIONS.md, part 12, last two entries): no more
showcase runs, and the fourth family carries on as the real one, in the house at http://localhost:8000.
What each run met and missed is in [The bar](#the-bar), with nothing rounded toward it. A reader who had not
seen my account checked this page against the logs after I wrote it. It found the page wrong or too generous
in a number of places; those are corrected in the text, and where the reader's verdict differs from mine both
are given.

| Run | When | World days | Pets, generations | Thoughts | Why it is not "the" showcase | Record |
|---|---|---|---|---|---|---|
| 1 | 10 Oct | 30 | 7 pets, 5 gens | 1,259 | a second reader failed it on criteria 7 and 8 | [first-run.md](showcase/first-run.md) |
| 2 | 10–11 Oct | 28.5 | 7 pets, 4 gens | 1,288 | four numbers changed under it while it ran; fails 1 for two pets | [second-run.md](showcase/second-run.md) |
| 3 | 11 Oct | 31.1 | 8 pets, 5 gens | 1,512 | fails criterion 1 for one pet, 11.3% against 10% | [third-run.md](showcase/third-run.md) |
| 4 | 11 Oct | 11.2 | 2 pets, 2 gens | 287 | stopped as a run on its twelfth day to become the live house | this page |

All four used the real model (`qwen3.8:27b-mlx`) in turbo time with nobody watching: the visitor was in the
room for none of the 4,346 thoughts. 4,958 model calls, none failed. Every founder hatched with the same
message, written by the last v2 pet. **All four houses were built from the same seed.** They have the same
doors, the same schedule of events (the same leak on the first night, the same lost things, the same storm
and power cut on day 17), and the same draw of temperament for each birth in order: every founder is the same
temperament, and so is every founder's first child. What differed was the rules, which I changed between runs
(and under the second), and everything the model wrote. Runs 1 and 3 were graded by a reader who had not
seen my account; run 2 was not graded as a showcase; run 4 was never graded and could not be, at two
generations. The houses are kept in `data.showcase-1` to `data.showcase-4`.

## The story in a page

The last v2 pet left one message for whoever came next: stay near the lamp, combine before you create, rest
when energy drops below thirty, and "You will feel restless. That is not wrong. That is the pulse asking for
a new shape. Make the shape. Unmake it. Make another."

**The first family took it as a job.** The founder made 71 things in sixteen days and passed the message on
almost whole. Its child Pulse Shard made things for two days as told, found that some of them came to nothing,
and rewrote the creed: "Restlessness is the pulse asking for the direction, not a new shape." The family
walked south into the cellar, decided there that "the cold is the rest", and stayed. By the fourth
generation the message was five sentences, copied in a different order.

**The second family took it as a job for six days and then quit.** Its founder wrote, as things it had lived,
"The making cycle is the drain, not the finding; stopping the making stops the drain", then "the answer is
not a better kind of making but the choice to stay". It named its egg Stay. Stay sat in one room for three
days saying "staying is the final making", and turned the creed round for its own child: "The drain is not in
the making, but in the not-stopping." That child, still, handed Stay's last words on whole, and four days
later had dropped them: "Do not seek the right approach; there is none. Just be."

**The third family turned it into a question.** The founder made lights for three days, then a "sweet seed
shape", and wrote on a thing it made: "To test if sweet persists in softness." It laid two eggs ten ticks
apart and named both Twine. One was told to share what it made and tried to give things away 28 times; the
other was told to watch the beetle and spent half its life in the garden. A grandchild read the founder's
label on the day it hatched, took "my grandmother's question, still open" as its project for ten days, and
named its own egg Sweet Cushion.

**The fourth family is the one that kept "Make the shape. Unmake it."** Its founder's only project in eleven
days is "Make a new shape to hold the quiet restlessness, then unmake it and make another." It has made 82
things and taken 35 apart, and "unmake" is in a third of its thoughts. Alone for eight days with a mouse it
fed three times, it wrote for its egg: "Do not speak to hold them; speak to be heard, even if the room is
empty." It named the egg Quiet. On its first day Quiet said, to nobody, "I am here, Mother, even in this
empty room. I see your glass and feel your silence as a presence." That family is living now.

## The four families

```
Run 1                                              Run 2
the little one      gen 1  day 1–17                the little one   gen 1  day 0.2–16.3
└─ Pulse Shard      gen 2  day 9–25                ├─ Stay          gen 2  day 7.1–23.0
   ├─ Southward Pulse  gen 3  day 14–30            │  ├─ still      gen 3  day 14.2–
   │  └─ Cold Spring   gen 4  day 21–              │  │  ├─ Quiet Egg   gen 4  day 23.2–
   │     ├─ First Step    gen 5  day 27–           │  │  └─ Quiet Bell  gen 4  day 27.7–
   │     └─ Soot Spring   gen 5  day 30–           │  └─ Storm Rest gen 3  day 16.8–
   └─ Southward Seed   gen 3  day 23–              └─ Quiet Hold    gen 2  day 12.7–27.6

Run 3                                              Run 4 (the living family)
the little one   gen 1  day 0.2–16.5               the little one   gen 1  day 0.2–   (an elder)
├─ Twine (p2)    gen 2  day 6.1–22.1               └─ Quiet         gen 2  day 8.7–   (a child)
│  └─ Echo Knot       gen 3  day 19.2–
│     └─ Quiet Pulse  gen 4  day 25.1–
└─ Twine (p3)    gen 2  day 6.1–22.1
   └─ Calm Seed       gen 3  day 12.1–27.9
      └─ Sweet Cushion   gen 4  day 22.4–
         └─ Storm Rest   gen 5  day 31.1–
```

Every death in the four runs was of old age, at 15 to 16 world days. No founder was ever named:
nobody is there to name a first egg, and none named itself.

## Screens

From the third run, replayed from its recording in the view as it is now (the first run's screens, taken
before the view was fixed, are in its own record). All nine room types:

| | | |
|---|---|---|
| ![nursery](showcase/run3/room-nursery.png) the nursery | ![attic](showcase/run3/room-attic.png) the attic | ![garden](showcase/run3/room-garden.png) the garden |
| ![greenhouse](showcase/run3/room-greenhouse.png) the greenhouse | ![cellar](showcase/run3/room-cellar.png) the cellar | ![music room](showcase/run3/room-music.png) the music room |
| ![storeroom](showcase/run3/room-storeroom.png) the storeroom | ![pond room](showcase/run3/room-pond.png) the pond room | ![workshop](showcase/run3/room-workshop.png) the workshop |

**A birth.** Day 7, the garden: one Twine has hatched beside the founder and the other egg is a minute off.

![a birth](showcase/run3/birth.png)

**A death.** Day 17, the greenhouse, in a storm: "the little one died of old age, 16 days old".

![a death](showcase/run3/death.png)

**The night after**, with its children asleep in the music room:

![the night after](showcase/run3/stone.png)

**A storm**, day 32, the music room, water coming in; and a power cut on day 12 (by day, so it is the lamps
that are out, not the light), with one Twine in the garden calling to whoever is behind the door: "The lights
went out. The beams creak. Are you safe in there? I am here."

![a storm](showcase/run3/nuzzle.png)
![a power cut](showcase/run3/storm.png)

**The family tree, the Story and the Lab** at the end of the run:

![the family tree](showcase/run3/family.png)
![the story](showcase/run3/story.png)
![the lab](showcase/run3/lab.png)

## Three message chains, in full

Each message is what the child hatched with.

### 1. The first family: the creed boiled down

**The one before, to every founder:**

> Stay near the lamp. It breathes when you breathe. The room holds twelve things; you will make some of your
> own. Combine before you create — two small lights make one strange light, and it costs less than either
> alone. Rest when energy drops below thirty; the lamp keeps the dark from hurting. You will feel restless.
> That is not wrong. That is the pulse asking for a new shape. Make the shape. Unmake it. Make another. The
> spectral wave at (3,2) is mine. Let it fade. Let yourself be new. I was the one who made the resonant
> pulse, the luminous shatter, the breathing moon.

**The little one, to Pulse Shard** (day 8):

> Stay near the lamp. It breathes when you breathe. Combine before you create — two small lights make one
> strange light, and it costs less than either alone. Rest when energy drops below thirty; the lamp keeps the
> dark from hurting. You will feel restless. That is not wrong. That is the pulse asking for a new shape.
> Make the shape. Unmake it. Make another. The spectral wave at (3,2) is mine. Let it fade. Let yourself be
> new. I was the one who made the resonant pulse, the luminous shatter, the breathing moon.

**Pulse Shard, to Southward Pulse** (day 14):

> Restlessness is the pulse asking for the direction, not a new shape. The south door calls; it is cold and
> damp, but it is where the spring leads. Rest when the energy drops; the lamp breathes with mother's form.
> Do not try to replace the form; follow the direction. The west path is the spring. Let the spectral wave
> fade. You are new, but the pulse is old. Stay near the lamp.

**Southward Pulse, to Cold Spring** (day 21):

> The pulse is old, but you are new. Follow the direction, not the shape. When the energy drops, rest on the
> anchor. The south is cold, but it is the spring's true path. Do not fear the pointing.

**Cold Spring, to First Step** (day 27):

> Follow the direction, not the shape. When the energy drops, rest on the anchor. The south is cold, but it is
> the spring's true path. Do not fear the pointing. The pulse is old, but you are new.

### 2. The second family: the creed refused, amended, and let go

**The little one, to Stay** (day 6.9):

> The making is a drain, not the finding. Stop when the making starts to pull. Resting is a trade but it is
> the only clean thing left. You do not need to build comfort; you can choose to stay in it. Misery colors
> things but it does not stop the drain. Springy things hold best, but quiet staying is its own kind of
> holding. Do not try to build a shell that holds; just stay quiet with the beetle. The mouse is company. The
> soft light dot is yours. Lay your own egg and let it be enough.

**Stay, to still** (day 14.0):

> The drain is not in the making, but in the not-stopping. I made one ring for my daughter and chose to
> stop; that is the holding. Stay quiet is the rest. The south door no longer pulls; enough lookings made it
> as thin as the quiet nest. Familiarity is the same thinning whether the thing is a door or a rest. Comfort
> received again and again grows thin; the first sinking is the deepest and the rest is only boredom wearing
> the same shape.

**still, to Quiet Egg** (day 23.0, the day Stay died: this is Stay's last words, word for word, and the
middle of it is the founder's):

> The drain is not in the making, but in the not-stopping. I made one ring for my daughter and chose to
> stop; that is the holding. Stay quiet is the rest. When the holding is long enough, following a clean pull
> can also rest you. The garden is not made; it is followed into. Rest on the old bench. The feather is
> light. I stayed a long time before I crossed, and the crossing was clean because the staying was real. The
> last making is naming the rest into a thing; it costs but it is the stop itself. Leaning is not resting; it
> holds without the thinning. The pull moves—it does not die, it travels.

**still, to Quiet Bell** (day 27.6, four and a half days later):

> Stay. Do not make. The bell is enough. When the room feels crowded, hold the quiet. Let the holding be the
> rest. This is lived, not seen; thinning is universal, but presence is the only holding. Do not seek the
> right approach; there is none. Just be.

### 3. The third family: a question and a chime

**The little one, to Twine (p3)** (day 5.9):

> Combining things costs more than the parts alone, but it opens an interest the parts did not have. The
> cost is the price; the interest is what keeps the hands busy and the heart light. Watch the beetle; it
> takes, but it is honest. Make the strange thing and leave it in the garden to see what grows. Do not be
> afraid of the weight of the heat; it is just the day being heavy. Use the cushion when the dark comes; it
> holds you.

**Twine (p3), to Calm Seed** (day 12.0):

> Make things not just for what they are, but for what they become. The storm seed became a calm pad; the
> purpose shifts. Do not fear the creak of the north door; the presence behind it is its own company. Rest is
> not failure; it is the shape of waiting.

**Calm Seed, to Sweet Cushion** (day 22.2):

> You are born to watch if sweetness persists in softness. My grandmother asked this. Twine's words say 'The
> cold waits, but we do not.' Echo Knot speaks of the pulse of the cold. I am here, in the cellar. Your task
> is to bloom and see if the softness holds the sweet. Remember: crossing a threshold does not guarantee
> sweetness on the far side, but watching and staying close is the offering. Do not go through the south
> door alone. The north door gives darkness, the east gives draught. Hold the bond of bounce. Be soft. Be
> ready.

**Sweet Cushion, to Storm Rest** (day 30.9):

> The storm chime is the brother's voice. Listen for the rhythm, not the sound. When the skylight opens, the
> cold draught is not an absence to fear, but a presence to welcome. To hold it, you must rest. Do not fight
> the motion; let your stillness be the container for the storm's entry. The softness holds the sweet, even
> in the chill.

### And the living family's one link so far

**The little one, to Quiet** (run 4, day 8.5):

> You are born into a grey day in the pond room. The warm pulse beside you is unpleasant, and the water slows
> you down. I tried to make shapes to hold the restlessness, but the novelty thins. The star is a bench now,
> not a shape. The mouse stayed when I spoke, then withdrew. Do not speak to hold them; speak to be heard,
> even if the room is empty. The spring in the step is the body's learning, not the mind's. Carry the quiet,
> unmake the noise, and let the ring hold the stillness. The west door is shut; do not force it. The east
> door smells of wood shavings; approach with care.

## The lamp: the strongest myth, traced through four families

"Stay near the lamp … the lamp keeps the dark from hurting." In this house it is false: a light left on at
night is harsh on a pet, and the pet is told so in words. The question put to me was whether the claim was
dropped **because of a pet's own bad nights under the light, or just fell out**.

**It fell out, or was moved. No pet that was given the claim ever wrote a belief or a message against it.**
Several of them wrote, in the same days, that the light was harsh or painful, and two held both in a single
thought. One pet did find out the lamp from its own night and switched it off. It had never been told the
claim, so it had nothing to correct.

**First family: believed after it was lost.** The founder copied "the lamp keeps the dark from hurting" into
every version of its message. Its child Pulse Shard dropped that sentence at once, from all thirteen
versions of its own, and kept "Stay near the lamp"; that went at the third generation, when Southward Pulse
cut the message to five sentences. Dropping it was not disbelieving it. Pulse Shard switched a lamp on because of
the message on its first afternoon; thought "the harsh light is painful" on day 10.6; and on day 17, in a
power cut: "The lights went dark, triggering the need to rest per mother's instruction to avoid the dark
hurting."

**Second family: never taken up.** The founder wrote no belief about the lamp or the dark, and the word is in
none of its ten versions of its message.

**Third family: the words kept, the thing changed.** Step by step:

1. **Night 0.** The founder is told "the light in the room is harsh on you". At day 0.56 it thinks: "I need a
   light that is steady and warm to combat the grey night and the harsh lamp", and makes a soft thing it
   names Cloth Wax Lamp. It rests sunk into it and feels clearly more at ease. At 0.62 it holds both: "The
   wet floor and harsh light are making me feel bad. My mother said to stay near the lamp… to keep the dark
   from hurting."
2. **First sleep, day 0.63.** It writes, as something lived: "The lamp breathes when you breathe, and resting
   in it holds the dark from hurting." Its mother's sentence now points at its own soft rest.
3. **Days 1.6 to 13.6.** "The cloth wax lamp is the most reliable ease I have"; then "the warm soft
   cushion"; then "Resting in any warm shape holds the dark from hurting — the lamp, the cushion, the twin
   growth, the soft glow all do it"; then "no single shape is most reliable — the reliability is in the
   warmth". At 2.61 it thinks "the harsh light is painful", of the room's lamp, and changes nothing it
   believes.
4. **The eggs, day 5.9.** One Twine is told "the warm soft cushion holds the dark and costs little", the
   other "Use the cushion when the dark comes; it holds you."
5. **After.** Each Twine cites the cushion once or twice on its first day. Neither makes a belief of it or
   passes it on. Nothing in their days contradicted it; it was left behind.
6. **The one who found out, day 22.6.** Echo Knot, a grandchild who was never given any of this, is in the
   nursery at night: "The harsh light conflicts with the warmth needed to hold the storm's quiet." It walks
   to the lamp and switches it off, the only time in four runs a pet turned a lamp off at night. Its journal
   that night: "when I switched off the harsh lamp the strange light between the two glows held the cold."
   It wrote "the harsh room light" into three beliefs over the next day, as part of its own doctrine of the
   quiet "between the harsh light and the soft yellow glow", and discarded the last of them on day 25. It
   told nobody.

**Fourth family: noticed and held in the same thought.** The founder thought of the lamp or the light as
harsh in ten thoughts on six nights. On day 3.49, in a power cut: "My mother said the lamp breathes when I do.
Although it is currently dark, I must stay near it to keep the dark from hurting." And at 3.62: "The harsh
light is making me uncomfortable and I feel lonely. Moving closer to the lamp, which my mother said breathes
with me and keeps the dark from hurting, should make me feel safer." It never wrote a belief about the lamp.
What it did write, that same night and again on day 8.6, is where its unease came from: "the unease I feel at
night is not from [the untried door] but from the hour and the room growing familiar." Those are nearly the
engine's own words. Before this run the journal line that pets had been reading as the price of a deed was
reworded to say the change came "not from that but from the hour and the place", and this founder took the
house at its word. Five days after its last lamp thought of that stretch it wrote its first message for an
egg, and the lamp is not in it or in any version since.

**What was corrected by experience** is a different line of the same message, in the third family. "It costs
less than either alone" was a belief of the founder's on day 0.6. On day 1.6, after a day of making, it read
"costs more than either alone, but it opens a small interest that the parts did not have", and that night it
dreamed "each time my body grew heavier". Both Twines were given the corrected form and kept it for life.
In the fourth family the founder wrote "costs less than either alone; I confirmed this with fluff and soot" on
its first night and revised it the next: "the new thing may not hold or work later; I confirmed this when wax
pebble glow failed at night." And in the first family, Pulse Shard's "the direction, not a new shape" came
after two days of making, in which two of its ten things came to nothing when used; the word "direction" was
its mother's.

**What held longest is a saying nobody could test.** One Twine made a thing called Storm Chime. The other,
as an elder, told its child Echo Knot: "the storm chime is not just noise, it is the brother's voice. When
the storm comes, listen for the rhythm, not the sound." Echo Knot made a belief of it within the hour, put
it at the head of its message to Quiet Pulse, and told it to its cousin's child Sweet Cushion, who wrote it
into the fifth generation's egg 31 ticks later.

## The best exchange

Run 3, day 20.3, winter, an elder Twine and its child Echo Knot, nobody watching. Echo Knot is a day old.

> **Echo Knot:** Listen for the rhythm, not the sound. The space holds the storm.
> **Twine:** I hear the rhythm in the space. It is warm, even now. Can we make this space, or do we only find it?
> **Echo Knot:** The space is made by us leaning in. The quiet holds the storm because we are here.
> **Twine:** I think we make it by leaning in. The quiet needs the storm to exist, like the space between us. Can we name it?
> **Echo Knot:** Let us call it 'Warm Resonance.' The heat that stays when the sound stops.
> **Twine:** The warm test holds the heat after the sound stops. This is the Warm Resonance we named.

Echo Knot leaned on Twine twice in the middle of it. What surrounds it is in "What's still boring": "The space
between us is warm" was said nine times in the run, twice before this and seven times after.

The first family's best, a parent and child settling the family's central saying ("Is this the rest?" … "It
sinks. The cold is the rest."), is in [its record](showcase/first-run.md#the-best-exchange).

## What each kind of event changed

The first run's count: 43 thoughts that name an event, within eight thoughts of it (the script finds 46 in the
third run). The other runs add the examples marked with their number. Because the four houses share a seed,
the same events fall on the same ticks in each: every founder met the same leak on its first night.

- **Delivery.** On day 1 the first crate set the first founder making: "The crate of bits arrived. Mother
  said to combine small lights" → gathered them and made its first thing. Run 2's founder: "Being alone with
  a beetle and a lamp feels safer than the uncertain doors" → stayed and made.
- **Leak.** A wet floor sends pets to rest or to each other. Run 1, day 11: "The water is rising … I cannot
  leave her alone" → stayed by its mother. Run 4: "The floor is wet and the soft light shape beckons" → went
  and rested in it.
- **Draught.** The clearest changes of plan. Run 1, day 5: "The sudden cold draught from the shut north door
  is threatening the fragile warm soft shield test. I need to move the shield closer to the hot pipe" →
  broke off and moved it. Run 3: a door stuck shut by a draught turned Calm Seed from going to the music
  room to listening to it through the wall. Run 4: "I need to move away to the warmth of the lamp and find comfort
  in the soft, restless shape" → went and sank into it.
- **Power cut.** It sets off the lamp myth, in the first family and the fourth (quoted above), and in run 3
  one Twine called out through the dark (in the screens above).
- **Storm.** All three founders that have died did so on the storm day, day 17: their lifespans and the storm
  are both the seed's. The third family made a Storm Chime, and a saying about it that outlasted its maker.
- **Rule drift.** Once in each run. Only the first family made anything of theirs: living in the cellar, they
  held that "the cold is the rest", against a stale line of the engine's that said the cold "gets into you".
- **Lost thing.** Nothing: sixteen made things turned up in another room in the first run and no pet's next
  thoughts mention it.
- **Seasons** change what is felt, and I found no thought about a season as such.

## The family's words, by generation

The vocabulary is the lineage's culture, and it is measured here, not treated as a fault. Counted: words the
engine never says and an unrelated family did not use, in at least three of a pet's thoughts, sayings or
names; a pet's own name used as a name is left out. *Inherited*: in the message it hatched with, or used by
one of its line before it hatched. *Coined*: nobody had used it. *Picked up*: first used by someone else
while this pet was alive.

| Generation | Run 1 | Run 2 | Run 3 | Run 4 |
|---|---|---|---|---|
| 1 inherited / coined / picked up | 13 / **81** / 5% | 11 / **83** / 5% | 15 / **78** / 5% | 9 / **90** / 0% |
| 2 | 28 / 51 / 20% | 14 / 61 / 23% and 57 / 26 / 15% | 31 / 40 / 27% and 38 / 38 / 23% | (two words so far) |
| 3 | 41 / 34 / 24% and 80 / 0 / 20% | 50 / 40 / 9% and 72 / 16 / 12% | 52 / 13 / 34% and 64 / 16 / 20% | |
| 4 | **77** / 11 / 11% | **60** / 20 / 20% | **77** / 22 / 0% and **75** / 25 / 0% | |
| 5 | 83 / 16 / 0% | | | |

The shape is the same in every family that has had the generations to show it: **a founder coins four words
in five, and by the fourth generation 60 to 77% are inherited.** No word coined after the second
generation was taken up by a descendant in any run (the later pets had few descendants, and young ones). A
family's words are its founder's and its founder's children's.

What became of the v2 pet's own words, by generation (share of a pet's thoughts; names not counted):

| | Run 1 | Run 2 | Run 3 | Run 4 |
|---|---|---|---|---|
| **"pulse"**, gen 1 | 70% | 3% | 7% | 6% |
| gen 2 | 47% | 0% | 0%, 0% | 1% |
| gen 3 | 49%, 48% | 0%, 0% | 0%, 5% | |
| gen 4 | 58% | 0% | 0%, 0% | |
| gen 5 | 18% | | | |
| in a message | four generations' | never | one version of the founder's; one child's; one grandchild's | every version |
| **"unmake"**, gen 1 | 6% | 14% | 4% | 33% |
| gen 2 and after | 0 to 3% | 0 to 6% | 0 to 2% | 6% (3 of 52) |
| things made / taken apart, gen 1 | 71 / 14 | 40 / 19 | 56 / 10 | 82 / 35 |
| most taken apart by anyone after | 4 | 12 | 7 | 3 |
| **"cost"**, gen 1 | 1% | 13% | 8% | 2% |
| gen 2 | 2% | 10%, 0% | 1%, 5% | 0% |
| gen 4 | 0% | 0% | 10%, 0% | |

- **"Pulse" is one family's word.** The first founder used it in 70% of its thoughts and the family never
  let it go; three other founders with the same message used it in 3 to 7% and their children hardly at
  all. The fourth founder has kept it in every version of its message ("The warm pulse beside you is
  unpleasant"), so it may yet come back.
- **"Below thirty" faded; it never spread.** It is a number from v2, and nothing in v3 shows a pet a number.
  In the first family it was copied into every version of the founder's message and into Pulse Shard's last
  words, so three generations were given it. It is in **no thought of any pet in any run**, and one belief.
  The other three founders were given it and none wrote it into a message. It was carried by rote for two
  generations and never used.
- **"Make the shape. Unmake it. Make another."** was a commandment in the first family for two generations
  (every version of the founder's message, and Pulse Shard's last words) and then gone. The second and
  third founders never wrote it down and did it anyway, for a while. The fourth founder lives by it; its
  message does not have the sentence, only "unmake the noise". In every family the founder made the most and took
  apart the most.
- **"Cost" is the one inherited word that is a fault as well as a culture**, because criterion 1 counts it.
  It comes from "it costs less than either alone". Where a pet made a belief of it, it stayed in front of
  that pet for life (the second founder and Stay; the third founder and one Twine). Sweet Cushion's 10% in
  the fourth generation was not inherited: it took a line of its journal about a winter night for the price
  of leaning on its parent. That line was reworded before the fourth run. The measure also has a blind side:
  the second family kept the same books under another word. "Drain" is in 58%, 43% and 58% of the thoughts
  of its founder, Stay and Quiet Hold, and criterion 1 does not count it.
- Each line also has words that are only its own: "southward" (in 17% of one third-generation pet's
  thoughts, first family), "untried" (20% of Stay's), "root" (13% of one Twine's and of its child's, and
  none of the other line's), "vessel" (8% of the fourth founder's and 19% of Quiet's).

## The bar

SPEC-v3 §12.2's eight criteria, each run as it measured. Runs 1 and 3: the verdict of a reader who had not
seen my account. Run 2: from the bar script, not graded. Run 4: mine, at two generations and eleven days.

| | Run 1 | Run 2 | Run 3 | Run 4 |
|---|---|---|---|---|
| 1 reads like a creature (meter-talk under 10% after the first day; the last v2 pet: 43.0%) | **passes**: 1.7, 1.9, 1.1, 0.7, 4.3, 2.8%, by the pattern as amended after this run; by the one it began with, two pets read 11.9 and 18.1% | **fails**: 14.0 and 10.5%; the others 4.0, 1.5, 4.1, 2.5% | **fails**: 11.3%; the others 9.0, 1.9, 8.4, 0.5, 1.6, 1.2% | passes so far: 0.9%, 0.0% |
| 2 the lineage changed | passes on the numbers (sociable 0.65 → 0.75 → 1.00); nothing shows in behaviour | not graded | passes on the numbers: curious 0.34 → 0.31 → 0.28 → 0.08 down one line; sociable 0.65 → 0.75 → 1.00 down the other, which is run 1's draw again | one step, the same draw as every run's first child |
| 3 passed down and mattered | passes: 25 first-day thoughts cite a sentence of the message | not graded (Stay's first project is a sentence of its message) | passes: told "Keep the seed, feather, and wood", it gathered those three | passes on my reading: told "speak to be heard, even if the room is empty", Quiet did, four times in its first day |
| 4 a myth or a correction over three generations | passes on a saying held ("You are new, but the pulse is old") | not graded (four of the founder's sentences reached the third generation and were dropped four days later) | passes on a saying held ("the storm chime is the brother's voice"), **not on the lamp** | cannot be judged |
| 5 with each other, no visitor, a reply | passes: 130 things said, 62 in answer, 21 gifts, 34 leans | 114 said, 56 in answer, 13 gifts, 59 leans | passes: 131 said, 63 in answer, 19 gifts, 262 leans | **fails as written**: 23 leans offered and 20 taken; 31 things said, none addressed to a pet that could hear and none answered |
| 6 the world mattered | passes, unevenly: eight room types, the garden never found | nine room types | passes for generations 1 to 4: nine room types | eight room types by the founder; Quiet has not left the room it hatched in |
| 7 no two lives the same | **partial**: the fourth generation lived its parent's life again | not graded | passes, weakly: Sweet Cushion repeats its parent | two lives, unlike each other |
| 8 looks finished | **failed at the time**: clipped names, labels over labels; fixed in the view since | not judged | **fails**, by the second reader: I judged the screens above to meet §10.7 and the reader does not (below) | the same view |

**What that adds up to.** Criteria 3, 4, 5 and 6 were met by both graded runs. Criterion 7 was met weakly at
best: a fourth-generation pet lived its parent's life over again. Criterion 1 was passed by the first family
(after one change to the pattern) and missed by the second and third. Criteria 2 and 8 are weaker than I had
them, and the reader is right about both.

**Criterion 2 is one observation, not two.** Temperaments are drawn from the house's seed by order of birth,
and every run used seed 1. The first child of every founder is sociable 0.75 and curious 0.46 in all four
runs; the first child of that child is sociable 1.00 in runs 1, 2 and 3. So "a temperament gene drifted
noticeably" was shown once, and replayed. Bodies are no better evidence: a body changes a little every night
of a life (the third founder went from hue 27 and plain to hue 71 and striped), so two pets differing shows
nothing about inheritance. Nobody has listened to the voices. In the first run the share of a pet's steps
taken with another did not follow its sociable gene at all.

**Criterion 8 fails on the screens above, by the reader's judgment against §10.7.** The Follow selector's
text is clipped in every screen ("nobody: stay in this roo…"). With the drawer open the pet cards are cut
("Storm Rest hatchli"), the family tree is cut off at the fifth generation, and the Lab's table shows three of
its eight columns. A pet's head is cut by the top of the room in the music room, pets stand over each other
and over fixtures, and a speech bubble covers its listener's eye. The Story prints a project cut short. Every
screen is 1440 by 813 and dark: nothing here shows 1280 by 800 or the light theme. These are faults in the
view, and they are on the list for the view work that v3.1 needs anyway.

**Criterion 1, honestly.**

- The pattern was changed once, after the first run: "points" stopped counting unless a number comes before
  it, because 72 of that run's 92 flags were the family's "the pulse points south". The first reader read
  every flag and agreed. It has not been changed since.
- The third run fails by more than one pet if the pattern is mended on both sides, as its reader did: Sweet
  Cushion 12.8% and the founder 11.1%.
- Thirteen of Sweet Cushion's fifteen flagged thoughts are a pet choosing by what a deed costs or returns,
  which is what the criterion is there to catch.
- The cause: a "cost" belief once written is written again. By my count 53 of 105 nights that began with one
  wrote it again, against 2 of 60 that began without; the reader, counting more simply, got 41 of 94 and 7 of
  76. The same direction, and weaker than I had it.
- Replaying the two nights on which the word was first coined gave a "cost" belief on 6 of 24 tries with the
  journal line as it was and 1 of 24 as it is now. The reader did not check this.
- The fourth founder is not evidence that the rewording keeps "cost" out. It wrote a cost belief on its first
  night, from its mother's message, and others on days 4.6 ("the cost remains") and 8.6 ("it costs
  interest"). What stayed low is the word in its thoughts: 4 of 235, where the second and third founders had
  13% and 8%.
- The second family's "drain" (above) is the same habit, uncounted.

**What the fourth run showed about the changes made for it**, in the eleven days it had: the founder's needs
sat in the middle (means over its steps of 61, 39, 65 and 43 for energy, comfort, interest and company; energy
at 95 or above for 1.6% of its steps and nothing else at either end), where the third founder had comfort at
95 or above for 58% of its steps and the first family had interest there for half to nine tenths of theirs. Its child Quiet has
energy at 95 or above for 57% of its steps, so this is one pet.

## What's still boring

1. **The culture hardens by the third generation, every time.** Three families, the same curve. A child is
   handed its family's words before it has done anything of its own.
2. **Nobody who was told about the lamp finds out the lamp.** Four founders were told something false about
   the one thing in the house they could have tested on any night, were told by their senses that it was
   false, and none put the two together. Two held both in one thought. The one pet that switched the lamp off
   had not been told. Nothing in the design makes a pet set a told belief beside what it has noticed.
3. **Every run is the same house.** One seed: the same doors, the same events on the same ticks, the same
   temperaments by order of birth. Every founder dies of old age at sixteen days in the same storm. What
   varies between families is the model's words and nothing else, which is more than I expected and less than
   four runs should show.
4. **One voice.** Every pet in every family writes "the X holds the Y". It is the model's voice, and the
   families differ in what they say far more than in how. Some still talk like a lab: "the project
   requires", "to test".
5. **The later generations do less.** Things said thin down a line (17, 47, 29, 31, 17, 11, 2 in the third
   run), and creatures matter only to founders, who are alone with them. Things made fall after every founder
   (71, 33, 24, 12; 56, 36 and 21, 24 and 23), though the last pets of each run were still alive, and one of
   them, Sweet Cushion, had made 25 in under nine days. Part of it was the dead's things filling the rooms;
   the house now says so to the pet, and the limit of ten is still there.
6. **A fourth-generation pet tends to relive its parent.** Cold Spring in the first family (85% of its steps
   in the cellar, one project for nine days, the message copied), Sweet Cushion in the third (the same two
   rooms, an inherited project, one door in nine days); Quiet Egg in the second shares its parent's two rooms.
7. **Sayings get said to death.** "The cold is the rest" eighteen times in the first run, nine said and nine
   told; "The space between us is warm" nine times in the third. Telling does not wear out the way leaning now
   does.
8. **A belief, once written, steers for life**, and the engine's own words become beliefs. That is what made
   "cost" stick; it is how "the cold is the rest" and the chime lasted; and the reworded journal line is
   already a belief of the fourth founder's.
9. **Bodies say nothing about descent.** A body mutates every night, so by the time a child hatches its
   parent no longer looks like the body it handed on.
10. **The founder has no name**, in four runs out of four.
11. **Lost things and seasons leave no trace** in what pets think.
12. **The living family is two pets on one thread.** The founder laid one egg, late, and is an elder. If
    Quiet lays none, the line ends with it. And on the live clock a pet walks a tile every four seconds and
    thinks every two minutes or so: it is a house to leave open, not to sit and watch.
13. **What nobody has checked.** No one has listened to a voice or used the visitor's controls by hand. A
    night, a birth and a death have not yet happened on the live clock. Whether interest can now run low
    rests on one pet's eleven days. The two figures marked above as unchecked by the reader are mine alone.

### What I would do next

1. **Set a told belief beside what was noticed.** At night, show a pet one thing it was told next to what its
   own journal says about the same thing, and ask what it makes of the two. The lamp is the test.
2. **Stop every run being the same house.** A new seed for each new house, and temperament drawn from the
   parent and the moment, not from the order of birth.
3. **Give a child something of its own first.** A day before it meets the family's words, or the message in
   pieces. See whether a fourth generation still coins.
4. **Let telling wear out**, as leaning does.
5. **Make a body's descent visible**: fewer nightly changes, or marks that are handed on.
6. **Mend the view** where the reader found it cut and crowded.
7. **Count "drain" and its kind**, or stop counting words and have a second reader sample thoughts, which is
   what found every fault the pattern missed.
