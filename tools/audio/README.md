# the house: audio

Procedural retro (NES-style) audio for *the house*, a cozy pixel-art game about small creatures called hobs.
Every sound is synthesized from scratch in Python (numpy/scipy): pulse/square, 4-bit triangle and noise
oscillators, envelopes, filters, echo. There are no samples and no third-party material. License: original work
(see `credits.json`).

## Layout

| folder | contents | files |
|---|---|---|
| `music/` | 60-120 s seamless loops (places, moods, time of day) | 16 |
| `ambience/` | 45-90 s seamless room/outdoor beds | 24 |
| `sfx/` | one-shots < 2 s, plus 9 looping sfx and 3 thunder sounds (<= 5 s) | 174 |
| `jingles/` | event stings 1-4 s; dawn/dusk transitions 5-10 s | 9 |
| `ui/` | interface sounds | 10 |
| `credits.json` | one entry per file: method, generator, seed, parameters, loudness, license | 233 |
| `reports/` | `check_batchN.txt/.json` verification reports, review spectrograms, voice demos (not deliverables) | |
| `src/` | all generators + `check.py` + build scripts | |

Format: WAV PCM 16-bit, 44.1 kHz. Mono everywhere except the 7 stereo music tracks: house_night,
outdoors_day, outdoors_night, pond, celebration, storm, winter. Stereo is light and mono-compatible:
L/R correlation is about 0.97-0.99 and the mono fold-down changes loudness by less than 0.1 LU.
No MP3s.

## Loudness and level

Integrated loudness is measured to ITU BS.1770-4 (pyloudnorm), and true peak with 4x oversampling.
Files are matched by loudness, not by peak.

| category | target | tolerance |
|---|---|---|
| music | -20 LUFS | +-1 LU |
| ambience | -28 LUFS | +-1 LU |
| sfx | -16 LUFS | +-1 LU |
| jingles | -16 LUFS | +-1 LU |
| ui | -16 LUFS (click and hover: -24, see deviations) | +-1 LU |

All files: true peak <= -1 dBTP. The limiter ceiling is -1.4 dBTP and is only engaged where needed.

**Short-sound LUFS method.** A file shorter than one 400 ms BS.1770 block (footsteps, hits, clicks) is
zero-padded to 400 ms before measuring. Its loudness is therefore its energy averaged over 400 ms. This is
stricter than a momentary reading of the click itself, so very short sounds can feel a little hot at
-16 LUFS. Trim them in the mixer if needed.

## Other rules check.py enforces

- **SFX, jingles and ui:** must start immediately (lead silence <= 5 ms) and end with a short fade, with
  trailing silence <= 0.1 s.
- **No steady tone held longer than 0.3 s** in sfx, jingles, ui and ambience. Only the sustained part of a
  tone counts: frames within 6 dB of its running maximum and within +-50 cents. A decaying bell stops
  counting once it falls 6 dB. Ambience also has no hum, whine or drone.
- **Loops (music, ambience, looping sfx):** seamless, with the seam crossfaded or built circularly. Both ends
  are exactly 0 and there is no jump at the seam.
- **Music:** no level dips at note boundaries (5 ms frames more than 12 dB below the 200 ms median).
- **Naming:** lowercase_underscores. Variants are `name_1..N`: alike, not identical.

## Deviations and special cases (all intentional)

- **ui/click and ui/hover use -24 LUFS** instead of -16, because the brief asks for "very quiet" page clicks
  and has no ui target. check.py checks this through `FILE_TARGET`.
- **jingles/dawn and jingles/dusk run 5-10 s** (9.3 s). They are one-off transitions, so held notes are
  reported but not flagged. The same applies to the 7 event jingles (first, invention, project_done,
  new_era, something_new, birth, death).
- **sfx/thunder_1..3 may run up to 5 s.**
- **Looping sfx** have an exact length, both ends at 0, and the steady-tone rule; the lead/trail silence
  rule does not apply to them:
  kiln_fire 10 s, loom 6 s, millstone 8 s, stove_sizzle 6 s, pot_bubble 6 s, train_chug 4 s,
  sweeper_whir 4 s, argue 4 s, scuffle 4 s. The game plays train_chug faintly everywhere.
- **sfx/killing_blow** ends in a deliberate hard cut to silence (6 ms fade, no tail).
- **Duplicate name `attic`:** `ambience/attic.wav` (room bed) and `music/attic.wav` (mysterious theme)
  share a name per the brief. They live in different folders.
- **Music held notes** (long bass and pad notes) are reported for information only.

## Musical identity

House key: C major. The house_day motif is E-G-A-G at 86 BPM. It recurs in:
- dawn, dusk and house_night
- workshop and celebration
- the jingles first, invention, project_done, new_era and birth
- grief, in A minor
- vengeance and vengeance_oath, turned dark as Eb-G-Ab-G in C minor
- winter, which is house_day re-arranged with the same tune, chords, tempo and length

## Voices

Hobs speak through `src/hob_voice.py`: Animal-Crossing-style babble with a 480 Hz base, pulse + triangle
source and vowel formants scaled x1.18 for a small creature. All hob vocal sfx use it. It is parameterized
(`BASE`, `FS`, `VOW`), so the voice can be revised and everything rebuilt.

The visitor (the owner of the world) uses the same engine with a distinct voice: 210 Hz base, formant
scale 0.90, squarer pulse, darker filter (`src/social_sfx.py`).

## Rebuilding

Requirements: Python 3 with numpy, scipy and pyloudnorm (plus matplotlib for review images only).

```bash
cd src
./build_all.sh          # regenerate everything, then check -> reports/check_all.txt
./build_batch5.sh       # or one batch: regenerate it, then run the full check
python3 hands_sfx.py hammer_2 saw     # or single files (most generators accept names)
python3 check.py /workspace/house-audio out.json   # verify only; exit code 1 on any violation
```

| script | generators | batch content |
|---|---|---|
| build_batch0.sh | sfx_fishing.py, ambience_machine_room.py, music.py | fishing sfx, machine_room, attic + house_day music |
| build_batch1.sh | music_batch1.py | house_night, outdoors_day, outdoors_night, dawn, dusk |
| build_batch2.sh | ambience_batch2.py (+ machine_room) | 14 room ambiences |
| build_batch3.sh | ambience_batch3.py, sfx_thunder.py | 9 outdoor/weather ambiences, thunder |
| build_batch4.sh | hob_voice.py, hob_sfx.py | hob body and voice sfx |
| build_batch5.sh | hands_sfx.py | hands, making, building, gathering |
| build_batch6.sh | machines_sfx.py | machines, cooking, train, sweeper, house (+ 7 loops) |
| build_batch7.sh | life_sfx.py | books, creatures, life sfx, event jingles, ui |
| build_batch8.sh | music_batch8.py | 11 place/mood music loops |
| build_batch9.sh | social_sfx.py | needs, getting along, conflict, the visitor (+ 2 loops) |

Every item is rendered from a fixed RNG seed (recorded in credits.json), so rebuilds reproduce the same
files. `/workspace/retro-audio` is the untouched original first draft and is not part of this project.
