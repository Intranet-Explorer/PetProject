# Voice

The pet gets a creature voice: babble synthesized in the browser from its genome, not a human text-to-speech voice. You read its words in the speech bubble and hear them as its own sounds.

**Phase 1 is view-only.** The brain never hears the voice, nothing about sound goes into the perception packet, and the engine's rules don't change. That's what makes it safe to add to the current life. Phases 2 and 3 are queued for later (see NEXT-LIFE.md).

---

## Phase 1: genome babble and state sounds (now)

### Where it lives
- `view/src/voice.ts`, Web Audio only. No libraries, no audio files, no assets.
- Driven by what the view already receives: genome, stage, needs and their trend, `said`, sleep, and moments.
- If the view lacks an event it needs (for example "used a thing and it helped"), expose it in the snapshot sent to the view, but **never** in anything the brain sees.

### Speech
When `w.pet.said` changes:
- Split the text into syllables (vowel groups per word), at most 24 syllables. Spaces become short gaps, commas longer gaps.
- Each syllable is one short note with a soft attack and release.
- **The same syllable always sounds the same:** its pitch offset and length come from a hash of the syllable's letters. Repeated words become recognizable over time, so its babble starts to feel like a language.
- **Punctuation shapes the contour:** `?` rises at the end, `!` is louder and higher, `.` falls, `...` trails off and slows.

### Genome → voice
| Voice | Driven by | Mapping |
|---|---|---|
| Base pitch | stage (body size) | hatchling ~700 Hz, child ~520, youngling ~420, adult ~330; ±10% from `stretch` (taller is lower) |
| Timbre | `roundness` | > 0.7 sine; 0.4–0.7 triangle; < 0.4 square through a low-pass filter so it buzzes without being harsh |
| Brightness | `saturation` | filter cutoff: pale is muffled, vivid is clear |
| Speed | energy | syllables ~60 ms at energy 100, ~140 ms at energy 0 |
| Vibrato | `wobble` | depth 0–40 cents, rate 5–7 Hz |
| Intonation | needs | curiosity high or rising: phrases end up; comfort under 30: phrases drift down and lower; any need under 20: tremolo, slightly shaky |

When the body mutates at sleep, the voice changes with it on the next sound.

### Sounds without words
The pet speaks rarely (four times in about 38 hours of v2 life), so most of what you hear should come from its state and actions. All of these are generated from the same voice so they sound like the same creature:

| Moment | Sound |
|---|---|
| Egg | a faint slow heartbeat; a little faster while a visitor is present |
| Hatching | a first cry: a short rising squeak |
| Made a thing | a small chirp |
| Took a thing apart | a short falling blip |
| Used a thing that helped | a content trill |
| Stage up | a rising three-note figure |
| Visitor talks or pokes | a short acknowledging "hm?" |
| Comfort under 20 for a long stretch | an occasional small whimper, at most one every 5 minutes |
| Asleep | slow, very quiet breathing |
| A thing it taught to `hum` | a hum with a different timbre from the pet's voice, so you can tell which is which |

Throttle: at most one non-speech sound every 2 seconds. Speech always plays and cancels anything queued.

### Controls
- A sound toggle in the header, plus a volume slider.
- Browsers block audio until the first click on the page, so the toggle starts off and the first click turns sound on.
- Remember on/off and volume in `localStorage`, wrapped in try/catch.
- Keep playing when the tab is in the background; that's the point. Schedule notes on the AudioContext clock, not with `setTimeout`, since browsers slow down timers in background tabs.

### Voice lab
In the drawer's Lab tab: play a sample sentence and each state sound with the current genome, plus sliders for stage, roundness, wobble, energy and comfort to hear how the voice changes. Nothing in the lab touches the pet or the engine.

### Done when
- Speech plays with the genome mapping; the same word sounds the same twice.
- Every state sound in the table plays on its real trigger in the live run.
- Mute and volume work and survive a reload.
- A rebuilt view doesn't need an engine restart (if it does, say so before restarting).
- A NOTES.md entry: what each sound is for, and what it sounded like on the live pet.

---

## Phase 2: talking grows with the stage (next life)

| Stage | Voice |
|---|---|
| Egg | heartbeat only |
| Hatchling | chirps and beeps; no syllable babble |
| Child | full babble |
| Youngling | babble, with a few real words starting to come through: its own name if it has one, the names of its useful things, "hello" |
| Adult | its described voice (Phase 3) |

Still view-only.

## Phase 3: a voice it chooses (later)

At Adult, at sleep, it writes a short description of the voice it wants ("a small, breathy, quick voice"). A local text-to-speech model that builds a voice from a written description turns that into its real voice. Parler-TTS worked this way as of mid-2026; check what's current before building. The described voice is logged next to its body, like its self-portraits. This is the first part of the voice that touches the brain, so it waits for a new life.
