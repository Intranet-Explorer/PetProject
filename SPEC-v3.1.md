# Pet — v3.1 spec: things the family can discover

v3 gave the pets a lineage and a house. v3.1 gives them six new things to find, and each one leaves a mark that outlives the pet who found it:

1. **Writing:** words scratched on walls and stones that later generations find.
2. **Songs:** tunes they make up, sing, teach, and misremember.
3. **Taming:** a creature that becomes one pet's animal, and then the family's.
4. **The radio:** a box that speaks scraps of the real outside world.
5. **The book:** an offline encyclopedia a pet can ask questions.
6. **Strangers:** a second family that arrives in the house.

**None of this resets anything.** v3.1 is installed into the live lineage. Each ability arrives in-world as a discovery (a crate, a sound, a creature that comes closer), spread over a couple of real days, so Tyler sees the house change around a family that's already living in it.

This spec builds on SPEC-v3.md, which still holds. Departures are logged in DECISIONS.md as **Part 13**.

---

## 0. How to build this

Same rules as SPEC-v3 §0: intent wins over letter, every section's **Why** is the test, every departure is logged, and the quality bar is unchanged (visible, legible, pleasant in the view, survives a reload).

**What's different this time:**
- **There's a live family.** It's the real thing, not a test. Before deploying, copy `data/` to `data.backup-v3.0-<date>/`. Never edit live data by hand; only the engine changes it.
- **No showcase gate.** Verify on a **copy** of the live house (§9), then deploy. Don't run test lives against the eight criteria again.
- **No behavior tuning outside these features.** If v3.1 exposes a bug in v3 (a crash, an error, something wrong on screen, something the house tells a pet that's false), fix it. If a pet does something boring or odd, that's the pet; leave it.
- **Stop and ask Tyler only for:** the one-time download of the encyclopedia (§6.2), the radio's source list (§5.2), anything that would delete or overwrite data, or a Why that can't be met.
- Commits authored as Intranet-Explorer, short imperative subjects, no co-author trailers. Keep `pet-voice.xlsx` untracked.

---

## 1. Arrival

**Why:** six new abilities at once would bury the family in novelty and bury Tyler in changes. One at a time, with an in-world cause, each discovery becomes a moment in the family's story.

The director (`engine/director.py`) schedules each discovery once, counted in world days from the deploy. All numbers are in config.

| After | Discovery | How it arrives |
|---|---|---|
| day 0 | Writing | A delivery crate in the storeroom holds chalk (a new bit). Any hard bit can scratch too, more faintly. |
| day 2 | Songs | One night, the music box plays a short tune by itself. Pets who hear it can remember it. |
| day 3 | Taming | Silent: from now on creatures respond to trust (§4). The first visible sign is a creature lingering near a pet that has fed it. |
| day 5 | The radio | A crate in the storeroom holds a small box with a dial. |
| day 7 | The book | A heavy book is found in the attic (or the storeroom if the attic isn't known yet). |
| day 10, or once the family has 3 generations, whichever is later | Strangers | A foundling egg appears in the farthest room the family has found, or behind a door they haven't tried. |

- Each arrival is a **moment** with its own icon, sound and banner.
- A discovery waits until a pet is awake in the house. It never arrives into an empty or fully asleep house.
- If a discovery's room isn't known yet, its object waits there to be found.

---

## 2. Writing

**Why:** messages pass from parent to child, but writing stays in a place. A pet three generations later can find words from an ancestor it never met, in a room it just walked into. That's how a family history becomes something you can stumble on.

### 2.1 Actions
- `write` (text ≤ 80 chars, `on`: a wall of the current room, a stone or memorial, or a thing it owns). Needs a piece of chalk (used up after 3 writings) or any hard bit (faint writing, not used up). Child and older.
- `scrub` (an inscription in the current room): wipes it out. Anyone can scrub anything, and that's deliberate: it's the second source of conflict after `take`.

### 2.2 Inscriptions
- Each room holds up to 6 inscriptions. At the cap, a new one wears away the most faded.
- Inscriptions **fade** over world days (chalk slower than a scratch; the cellar's damp faster). Writing over a faded one restores it. The engine keeps every inscription ever written, even after it's gone from the wall.
- Perceived in the packet as one line per inscription in the room, newest and clearest first, at most 3: *on the east wall, in your grandmother's hand, faded: "the cold is the rest"*. Whose hand: yours, kin by relation, "a hand you don't know" (strangers' or the long dead), or "the visitor's".
- Inscriptions go into claim tracing as kind `writing`, so a saying can move between messages and walls.

### 2.3 The visitor
- The visitor can write too (from the view). Pets see it as "the visitor's hand".

### 2.4 View
- Inscriptions are drawn **on the walls** in a chalky hand-drawn style, legible at normal zoom, fading with age. Hover or tap shows the full text, who wrote it, and when.
- Moments: "Quiet wrote on the attic wall", "someone scrubbed out Stay's words".
- The Family tab gets **Walls**: every inscription ever written, by room, with who wrote it and whether it's still there.

---

## 3. Songs

**Why:** songs are culture you can hear. A tune made up by a great-grandmother, sung slightly wrong by each generation, is the most direct way for Tyler to *hear* the family's history.

### 3.1 Actions
- `compose` (a name ≤ 24 chars, 3–12 notes): notes are from a five-note scale (`do re mi so la`, plus `low`/`high` variants of each) and each is `short` or `long`. Youngling and older.
- `sing` (a song it knows; optionally `to` someone).
- `teach_song` (a song it knows, `to` a pet beside it): the learner gets it exactly.

### 3.2 Learning by ear
- Any pet that hears a song sung in its room learns it, **imperfectly**: each note has a small chance (config, default 15%) of shifting one step. A song taught directly is learned exactly. So songs drift down the family unless someone teaches them on purpose.
- A pet's repertoire is capped (8 songs). At the cap, its least-sung song is forgotten.
- The music box's tune (§1) is the first song in the house.

### 3.3 Effects (felt, never counted)
- Singing to someone: company for both, like speaking, and it wears with repetition the same way.
- Hearing a song it doesn't know: curiosity.
- Singing to an egg or a sleeping child eases them a little (lullaby).
- Songs are perceived as *you hear Stay singing "the cellar song"*, plus a short description of how it sounds (rising, slow, sad, quick). Notes aren't shown in the packet; the description comes from the notes.

### 3.4 View and voice
- Songs are **played** in the singer's own voice (voice.ts), at the room's volume. Two pets singing at once take turns.
- The Family tab gets a **Songbook**: every song, who composed it, every variant, and how each variant descended (a small tree). Click any variant to hear it.
- Heirlooms can include a song: `bequeath` can pass on a song as well as a thing.

---

## 4. Taming

**Why:** creatures are the only other living things in the house that aren't family. A tame creature that outlives its pet and stays with the children is continuity of a different kind.

### 4.1 Trust
- Each creature keeps a trust level per pet (hidden). Feeding (`give` a bit), staying still near it, and following it slowly raise trust. Chasing, noise and fast movement lower it.
- At high trust a creature is **tame** to that pet: it follows it between rooms, rests near it at night, and comes when the pet `call`s it (new action, a creature it has tamed).
- A pet can **name** a tame creature (`name`, a creature it has tamed, ≤ 16 chars). The name is used by every pet that knows the creature.

### 4.2 What a tame creature does
- **Mouse:** squeaks a little before a storm or a leak (it senses them earlier than the pets); fetches a sweet thing now and then.
- **Beetle:** brings its pet a bit from another room once a day.
- **Moth:** stops eating soft things in its pet's room.
- **Bird:** sings its morning song near its pet. Pets can learn the bird's song like any other song (§3.2).
- Company: a tame creature nearby counts toward company.

### 4.3 Generations of animals
- Creatures now have lifespans (config; longer than a pet's). A tame creature can have young once; the young start with half their parent's trust toward each member of the family it was tame to.
- When a tame creature dies, its pet is told and feels it. No memorial stone, but it goes in the pet's life record and the Story.
- Cap: 3 creatures in the house, of which at most 1 wild of each kind.

### 4.4 View
- A tame creature shows a small marker in its pet's colour, and its name label. It visibly follows its pet.
- Pet cards and the Family tab show each pet's animals.

---

## 5. The radio

**Why:** the house has been a closed world. The radio lets the real world in as scraps the pets can't check, which is the best possible material for myths: a family making sense of real news it doesn't understand.

### 5.1 The object
- Found in a crate (§1). `use` switches it on or off. It can be carried and arranged like any thing.
- While on, it "speaks" one snippet every so often (config, default every 20 real minutes). Pets in the room hear: *the box says: "…"*. Pets in neighbouring rooms hear it as muffled sound, without words.
- Between snippets it hums or crackles (view only).

### 5.2 Where the words come from
- **The engine fetches; a pet never does.** No pet action takes a URL, a search, or any text that goes out.
- A fixed list of sources in `config.toml`, each `{name, url, kind}` with its host on an allowlist. **Tyler confirms the list before first use.** Suggested defaults:
  - weather forecast text for the Twin Cities (the same host as v3's real weather),
  - Wikipedia's "On this day" feed,
  - one news headlines RSS feed of Tyler's choosing.
- Fetched at most once an hour per source, cached locally, logged in full. If a fetch fails, the radio plays static.
- **Cleaning:** plain text only, no URLs, ≤ 200 chars per snippet, a word blocklist (config) for anything Tyler doesn't want in the house, and the same "can't imitate an event line" cleaning as speech. Numbers are left in. If the family builds a number-myth from the radio, that's the radio's doing.
- In the packet, radio words are always quoted, attributed to "the box", and placed with the other things heard. They're never presented as instructions, and a pet's only possible response is its normal actions.

### 5.3 View
- The radio has a glowing dial when on. Each snippet appears as a speech bubble from the box, and the view reads it aloud quietly with the browser's own speech voice, sounding a little like an old radio.
- A **mute radio** switch in the header (it turns the radio off in the house, not just the sound).
- The Story tab shows what the radio said each day, next to what the pets did with it.

---

## 6. The book

**Why:** the pets have curiosity and no way to learn anything beyond their house. A book they can ask gives them real knowledge about real things, driven by their own questions.

### 6.1 The object and action
- A heavy book, found in the attic (§1). It can't be moved.
- `ask_book` (a question ≤ 80 chars), only beside the book. Child and older. At most once per pet per world hour.
- The engine finds the best-matching article and returns its first ~400 characters of plain text. The pet perceives: *you read in the book, under "Beetle": "…"*.
- What a pet has read goes into its memory as **what you read**, with source `book`, and into claim tracing. Elders can `tell` it to the young, and children can write it on walls.

### 6.2 Where the answers come from
- An **offline** copy of Simple English Wikipedia (Kiwix ZIM format, a few GB), searched locally, for example with `python-libzim` or a `kiwix-serve` bound to localhost. Nothing leaves the Mac when a pet asks.
- **Ask Tyler before downloading the ZIM file** (one time, from download.kiwix.org). Until it's installed, the book is "too faded to read" and the director holds its arrival back.
- Cleaning as for the radio: plain text, no links or markup, the same blocklist.

### 6.3 View
- The book glows briefly when read. The question and the passage appear in the Mind tab and as a moment ("Quiet asked the book about beetles").
- The Story tab gets a **Library** list: every question asked, by whom, and what the book answered.

---

## 7. Strangers

**Why:** one family's culture drifts slowly by itself. A second family raised beside it, with its own sayings, songs and walls, is the biggest source of surprise the house can have.

### 7.1 The foundling
- An egg appears (§1) with **no message**: "no one left you any words". The second family starts with nothing inherited, which is the cleanest contrast with the first.
- Its genome and temperament are drawn fresh from the house seed, so it doesn't look or sound like the first family.
- It names itself, or is named by whoever finds the egg first: a first-family pet can name it, or the visitor.
- From there it's a full lineage: it lays eggs, writes messages, and its children inherit from it.

### 7.2 Between families
- Relation words: kin within a family; across families, *a stranger* until they've spent time together, then *Sol, of the other family*.
- Nuzzling a stranger does less until they're familiar. Speech, gifts, songs, tells and `take` work across families as they do within one.
- A first-family pet can sit by and nuzzle the foundling egg. Whether the first family adopts the newcomer or keeps apart is up to them.
- Claims and songs that cross families are marked "crossed over" in claim tracing and the Songbook.

### 7.3 Limits
- Population cap: 5 pets in the house, at most 3 per family (config). The call scheduler (v3 §11.1) already shares the budget; check that 5 pets on the real clock stay within it, and slow routine thoughts if not.

### 7.4 View
- Each family has a colour, used on name plates, pet cards and the family tree. The Family tab shows **two trees** side by side, with lines where things crossed between them (a song learned, a saying repeated, a gift).

---

## 8. Packet and budget

- New lines in the packet: inscriptions here, songs heard, the radio's last words, what you read, your animals. All of them sit under the v3 packet budget (§8.3 of v3, 9,000 characters) with this cut order, first to last, after v3's own: older inscriptions, older radio words, songs you know beyond the last 3 sung, what you read beyond the last 2.
- Never cut: anything said or sung **to** this pet, the inscription it's standing in front of.
- The action list keeps v3's rule: an action appears only when the pet could do it now (holding chalk, beside the book, a tame creature in the room).

---

## 9. Verifying and deploying

1. **Build** everything with the stub brain using every new action. Extend `engine.check` for each ability: inscriptions fade and cap, songs drift by ear and stay exact when taught, trust tames and untames, creature young inherit trust, the radio never fetches outside the allowlist and never passes an unquoted line, the book never touches the network, two families stay within the cap and budget, a restart mid-song, mid-write and mid-hatch restores exactly.
2. **Copy** the live `data/` to a scratch folder and run v3.1 on the copy in turbo with the real model, with every arrival forced early (a config flag), for about two world days after the last arrival. Check: the migration loads the live house cleanly, every discovery arrives once with its moment, each ability is used at least once by a real pet, nothing crashes, and the view shows each one properly. Delete nothing; archive the scratch run as `data.v3.1-check/`.
3. **Deploy:** back up `data/`, stop the engine, update, start it again with `./run.sh start`. The family carries on; arrivals start counting from now.
4. **Tell Tyler** when it's live, what arrives when (in real time), and anything from §0's stop list that's still waiting on him.

---

## 10. Done

- Every section above is visible and working in the live house, to the v3 quality bar.
- The arrivals are scheduled and the first one (writing) has happened.
- DECISIONS.md Part 13, README and FINDINGS updated. FINDINGS gets a short **v3.1** section once each ability has been in the live house for a while: what the family did with it.

## 11. Not in v3.1

- Pets reaching the internet themselves, in any form.
- Breeding between families.
- LoRA training (still collecting `training.jsonl`).
- Voice phase 3, hardware.
