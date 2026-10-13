// The pets' voices, as plans (VOICE.md phases 1 and 2, SPEC-v3 §10.6). Everything here is plain arithmetic: text
// and genome in, notes out. voice.ts turns the notes into sound. Nothing in the voice reaches a pet or the engine.
// Phase 2: talking grows with the stage (an egg only has a heartbeat, a hatchling chirps a beep a word, a child
// babbles, and from youngling on a few real words come through), elders are lower and slower with a tremble, and
// since every voice comes from a genome a child sounds like its parent.
import type { Genome } from "./pet";

export type Needs3 = { energy: number; comfort: number; curiosity: number; company?: number };
/** `words` are the real words it knows how to say (its name, its useful things, the others' names); see planSpeech. */
export type VoiceInput = { stage: string; genome: Genome; needs: Needs3; trend?: Partial<Needs3>; words?: string[] };
export type Tone = { at: number; dur: number; f0: number; f1: number; gain: number };   // seconds, Hz, 0..1
export type Timbre = { wave: "sine" | "triangle" | "square"; cutoff: number; vibratoCents: number; vibratoHz: number; tremolo: number };
export type Plan = { tones: Tone[]; timbre: Timbre; length: number; words?: { at: number; word: string }[] };
export type SoundKind = "cry" | "chirp" | "blip" | "trill" | "stageup" | "hm" | "whimper" | "last";
/** The small sounds a pet makes by itself (SPEC-v3.3 §4), as the engine names them in `snap.vox`. */
export type VoxKind = "murmur" | "hum" | "chirp" | "yawn" | "laugh" | "greet" | "grumble" | "gasp";
export const VOX: VoxKind[] = ["murmur", "hum", "chirp", "yawn", "laugh", "greet", "grumble", "gasp"];

const BASE: Record<string, number> = { egg: 700, hatchling: 700, child: 520, youngling: 420, adult: 330, elder: 290 };
const TALKS = ["youngling", "adult", "elder"];   // the stages at which real words come through the babble
const SCALE = [-7, -5, -2, 0, 2, 5, 7];   // semitones a syllable can sit at, either side of the base pitch, so babble is tuneful
const MAX_SYLLABLES = 24;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const semis = (n: number) => 2 ** (n / 12);

/** The same letters always give the same number, so the same syllable always sounds the same. */
export function hash(letters: string) {
  let h = 2166136261;
  for (let i = 0; i < letters.length; i++) h = Math.imul(h ^ letters.charCodeAt(i), 16777619);
  return h >>> 0;
}

/** Genome and state to voice (the table in VOICE.md). */
export function voiceOf(v: VoiceInput) {
  const g = v.genome, low = Math.min(v.needs.energy, v.needs.comfort, v.needs.curiosity, v.needs.company ?? 100), old = v.stage === "elder";
  const base = (BASE[v.stage] ?? 700) * (1 - 0.1 * clamp((g.stretch - 1.075) / 0.325, -1, 1));   // taller is lower
  const wave: Timbre["wave"] = g.roundness > 0.7 ? "sine" : g.roundness >= 0.4 ? "triangle" : "square";
  const open = base * (2 + 8 * g.saturation);                                    // pale is muffled, vivid is clear
  return {
    base,
    syllable: (140 - 0.8 * clamp(v.needs.energy, 0, 100)) / 1000 * (old ? 1.35 : 1),   // 60 ms lively, 140 ms worn out; an elder is slower
    sad: v.needs.comfort < 30,                                                  // phrases drift down and sit lower
    eager: v.needs.curiosity >= 70 || (v.trend?.curiosity ?? 0) > 0.5,          // phrases end up
    timbre: {
      wave, cutoff: wave === "square" ? Math.min(open, base * 3.5) : open,       // a square buzzes; keep it from being harsh
      vibratoCents: 40 * clamp(g.wobble, 0, 1), vibratoHz: 5 + 2 * clamp(g.wobble, 0, 1),
      tremolo: low < 20 ? 0.4 : old ? 0.2 : 0,                                  // any need under 20: shaky; an elder always trembles a little
    } as Timbre,
  };
}

/** A word as syllables: each is its consonants and the vowel group after them; trailing consonants join the last. */
export function syllables(word: string): string[] {
  const letters = word.toLowerCase().replace(/[^a-z]/g, "");
  return letters ? letters.match(/[^aeiouy]*[aeiouy]+(?:[^aeiouy]*$)?/g) ?? [letters] : [];
}

/** A hatchling does not babble yet: one chirp a word, high and short, the last one bent by how the sentence ends. */
function planChirps(text: string, v: VoiceInput): Plan {
  const voice = voiceOf(v), tones: Tone[] = [];
  let t = 0;
  for (const word of text.split(/\s+/).filter((w) => /[a-z]/i.test(w)).slice(0, 8)) {
    const h = hash(word.toLowerCase().replace(/[^a-z]/g, "")), f = voice.base * 1.5 * semis(SCALE[h % SCALE.length]);
    const bend = /\?$/.test(word) ? semis(5) : /[.…]$/.test(word) ? semis(-4) : semis(1);
    tones.push({ at: t, dur: 0.07 + (h % 4) / 100, f0: f, f1: f * bend, gain: /!$/.test(word) ? 0.65 : 0.45 });
    t += 0.17 + ((h >>> 4) % 6) / 100 + (/[,.!?…]$/.test(word) ? 0.16 : 0);
  }
  return { tones, timbre: voice.timbre, length: tones.length ? tones.at(-1)!.at + tones.at(-1)!.dur : 0 };
}

/** Speech: one short note per syllable, shaped by punctuation and by how the pet is. From youngling on, a word it
 *  really knows is left out of the babble and given back in `words`, to be said aloud as a word. */
export function planSpeech(text: string, v: VoiceInput): Plan {
  if (v.stage === "egg") return { tones: [], timbre: voiceOf(v).timbre, length: 0 };
  if (v.stage === "hatchling") return planChirps(text, v);
  const voice = voiceOf(v), tones: Tone[] = [], words: { at: number; word: string }[] = [];
  const known = new Set(TALKS.includes(v.stage) ? ["hello", ...(v.words ?? [])].flatMap((w) => w.toLowerCase().split(/\s+/)) : []);
  let t = 0, count = 0;
  for (const sentence of text.match(/[^.!?…]+(?:\.\.\.|…|[.!?])?/g) ?? []) {
    const end = /(\.\.\.|…)$/.test(sentence) ? "..." : /[.!?]$/.test(sentence) ? sentence.slice(-1) : "";
    const first = tones.length;
    sentence.split(",").forEach((clause, c) => {
      if (c) t += voice.syllable * 2;                                           // a comma is a longer gap
      for (const word of clause.split(/\s+/)) {
        const parts = syllables(word).slice(0, MAX_SYLLABLES - count), plain = word.toLowerCase().replace(/[^a-z']/g, "");
        if (!parts.length) continue;
        if (known.has(plain) && plain.length > 2) {                             // a real word: a gap in the babble the size of the word
          words.push({ at: t, word: plain });
          t += Math.max(0.3, 0.075 * plain.length) + voice.syllable * 0.5;
          count += parts.length;
          continue;
        }
        for (const s of parts) {
          const h = hash(s), f = voice.base * semis(SCALE[h % SCALE.length]) * (voice.sad ? 0.92 : 1);
          const dur = voice.syllable * (0.75 + ((h >>> 8) % 61) / 100);         // 0.75 to 1.35 of a syllable
          tones.push({ at: t, dur, f0: f, f1: f, gain: 0.5 });
          t += dur + 0.012;
          count++;
        }
        t += voice.syllable * 0.5;                                              // a space is a short gap
      }
    });
    const said = tones.slice(first), last = said.at(-1);
    if (!last) continue;
    if (voice.sad) said.forEach((n, i) => { const d = semis(-Math.min(4, 0.25 * i)); n.f0 *= d; n.f1 *= d; });
    if (end === "!") said.forEach((n) => { n.f0 *= semis(2); n.f1 *= semis(2); n.gain = Math.min(1, n.gain * 1.4); });
    if (end === "?") {
      last.f1 = last.f0 * semis(5);                                             // rises at the end
      const before = said.at(-2);
      if (before) before.f1 = before.f0 * semis(1);
    } else if (end === ".") last.f1 = last.f0 * semis(-4);                       // falls
    else if (end === "...") {
      said.slice(-3).forEach((n, i, tail) => {                                  // trails off and slows
        const k = (i + 1 + 3 - tail.length) / 3, stretch = 1 + 0.9 * k, moved = n.dur * (stretch - 1);
        said.slice(said.indexOf(n) + 1).forEach((later) => (later.at += moved));
        n.dur *= stretch;
        n.gain *= 1 - 0.6 * k;
        n.f1 = n.f0 * semis(-1.5 * k);
        t += moved;
      });
    }
    if (voice.eager && end !== "." && end !== "...") last.f1 *= semis(2);        // curious: the phrase ends up
    t += voice.syllable * 3;
    if (count >= MAX_SYLLABLES) break;
  }
  return { tones, timbre: voice.timbre, length: Math.max(0, t - voice.syllable * 3), words };
}

/** Notes as [at, dur, from, to], the pitches in multiples of the voice's own, all as loud as each other. */
const notesOf = (b: number, timbre: Timbre) => (notes: number[][], gain: number): Plan => {
  const tones = notes.map(([at, dur, from, to]) => ({ at, dur, f0: b * from, f1: b * to, gain }));
  return { tones, timbre, length: Math.max(...tones.map((n) => n.at + n.dur)) };
};

/** The sounds without words, made from the same voice so they are the same creature. */
export function planSound(kind: SoundKind, v: VoiceInput): Plan {
  const voice = voiceOf(v), b = voice.base, timbre = { ...voice.timbre }, seq = notesOf(b, timbre);
  switch (kind) {
    case "cry": return seq([[0, 0.3, 0.9, 2.1], [0.33, 0.12, 2.1, 1.8]], 0.55);                  // a first cry: a short rising squeak
    case "chirp": return seq([[0, 0.07, 1.5, 1.6], [0.085, 0.09, 2, 2.12]], 0.45);                 // made a thing
    case "blip": return seq([[0, 0.16, 1.6, 0.85]], 0.4);                                          // took one apart: short and falling
    case "trill": return seq([0, 1, 2, 3, 4, 5].map((i) => [i * 0.065, i === 5 ? 0.11 : 0.055, i % 2 ? 1.5 : 1.25, i % 2 ? 1.5 : 1.25]), 0.32);
    case "stageup": return seq([[0, 0.16, 1, 1], [0.19, 0.16, 1.26, 1.26], [0.38, 0.32, 1.5, 1.5]], 0.5);   // three rising notes
    case "hm": return seq([[0, 0.1, 0.95, 0.9], [0.1, 0.2, 0.9, 1.3]], 0.4);                       // an acknowledging "hm?"
    case "whimper":
      timbre.tremolo = 0.5;
      return seq([[0, 0.35, 1.3, 1.05], [0.45, 0.4, 1.15, 0.88]], 0.28);
    case "last": return seq([[0, 0.5, 1, 0.8], [0.6, 0.9, 0.8, 0.5]], 0.3);                          // a death: two long notes going down and out
  }
}

/** The small sounds a pet makes by itself while its body is busy (SPEC-v3.3 §4): the same voice again, quieter than
 *  talk (five pets at it must not be a din), each 0.2 to 1.2 s long and each its own shape, so that with eyes shut a
 *  yawn is not a laugh. A kind the engine invents later is a murmur. */
export function planVox(kind: VoxKind, v: VoiceInput): Plan {
  const voice = voiceOf(v), timbre = { ...voice.timbre }, seq = notesOf(voice.base, timbre);
  switch (kind) {
    case "hum":                                                                                   // three held notes of a little tune, with a wobble
      timbre.vibratoCents = Math.max(25, timbre.vibratoCents);
      return seq([[0, 0.3, 1, 1], [0.33, 0.3, 1.26, 1.26], [0.66, 0.45, 1.12, 1.12]], 0.2);
    case "chirp": return seq([[0, 0.05, 2, 2.2], [0.1, 0.05, 2, 2.2], [0.2, 0.08, 2.4, 2.7]], 0.22);   // interest: three quick high peeps, the last one up
    case "yawn": return seq([[0, 0.35, 0.85, 1.3], [0.35, 0.75, 1.3, 0.62]], 0.2);                 // a long slide up, and a longer one down and out
    case "laugh": return seq([0, 1, 2, 3, 4].map((i) => [i * 0.1, 0.055, 1.7 - 0.12 * i, 1.55 - 0.12 * i]), 0.24);   // five short bounces, going down
    case "greet": return seq([[0, 0.11, 1, 1.02], [0.14, 0.24, 1.34, 1.5]], 0.26);                 // two notes, the second a fourth up and still rising
    case "grumble":                                                                               // low, rough and sinking
      [timbre.tremolo, timbre.cutoff] = [0.7, timbre.cutoff * 0.5];
      return seq([[0, 0.22, 0.72, 0.62], [0.27, 0.16, 0.66, 0.6], [0.47, 0.3, 0.62, 0.5]], 0.26);
    case "gasp": return seq([[0, 0.14, 1.1, 2.6], [0.15, 0.1, 2.6, 2.5]], 0.3);                    // one sharp swoop up, and held there a moment
    default:                                                                                      // murmur: four soft low syllables, mouth nearly shut
      timbre.cutoff *= 0.6;
      return seq([[0, 0.1, 0.84, 0.8], [0.13, 0.12, 0.9, 0.86], [0.29, 0.09, 0.8, 0.8], [0.41, 0.16, 0.86, 0.75]], 0.18);
  }
}

/** A pitch of the five-note scale as semitones above "do": "low so" is 7 - 12, "high la" 9 + 12 (SPEC-v3.1 §3.1). */
export function semitone(pitch: string) {
  const [a, b] = pitch.split(" "), step: Record<string, number> = { do: 0, re: 2, mi: 4, so: 7, la: 9 };
  return b ? (step[b] ?? 0) + (a === "low" ? -12 : 12) : step[a] ?? 0;
}

/** A song in a pet's own voice (SPEC-v3.1 §3.4): the timbre it talks in, holding each note, with "do" at the pitch
 *  it speaks at. An elder sings slower. A song sounds like whoever sings it, so a tune changes as it is handed down. */
export function planSong(notes: [string, number][], v: VoiceInput): Plan {
  const voice = voiceOf(v), beat = v.stage === "elder" ? 0.36 : 0.28, tones: Tone[] = [];
  let t = 0;
  for (const [pitch, long] of notes) {
    const f = voice.base * semis(semitone(pitch)), dur = beat * (long ? 2 : 1);
    tones.push({ at: t, dur: dur * 0.9, f0: f, f1: f, gain: 0.42 });
    t += dur;
  }
  return { tones, timbre: { ...voice.timbre, vibratoCents: Math.max(12, voice.timbre.vibratoCents) }, length: t };
}

// ---- which changes in what the view receives call for which sound ----

/** The little of a snapshot the voice listens to (types.ts has the whole of it). */
export type Ears = {
  tick: number; tick_seconds?: number;
  pets: { id: string; room: string; said?: { text: string; tick: number; song?: string } | null }[];
  moments: { n: number; kind: string; pet: string | null; room: string | null }[];
  sung?: { tick: number; by: string; song: string; room: string }[];
  radio?: { said: { tick: number; room: string | null; source: string; text: string }[] };
  // SPEC-v3.2: steps just finished, numbered. SPEC-v3.3: `kind` of a made thing, `loud` if what was used sounds
  acts?: { n: number; type: string; pet: string; what?: string | null; room: string; ok: boolean; kind?: string | null; loud?: boolean }[];
  vox?: { n: number; pet: string; room: string; kind: VoxKind }[];   // SPEC-v3.3 §4: the small sounds, numbered
};
export type Seen = { tick: number; said: Record<string, number>; moment: number; sung: number; radio: number; act: number; vox: number };
export type HouseSound = "powerdown" | "powerup" | "thunder" | "drip" | "whoosh" | "thud" | "chalk" | "chime" | "patter" | "tuning" | "pages" | "knock";
const BY_PET: Record<string, SoundKind> = { hatched: "cry", stage: "stageup", made: "chirp", unmade: "blip", nuzzle: "trill", gift: "trill",
                                            named: "hm", death: "last", befriended: "trill", tamed: "trill" };
const BY_HOUSE: Record<string, HouseSound> = { power: "powerdown", storm: "thunder", leak: "drip", draught: "whoosh", delivery: "thud", stocked: "thud",
  // each discovery of SPEC-v3.1 §1 comes with a short sound of its own
  "arrival writing": "chalk", "arrival songs": "chime", "arrival taming": "patter", "arrival radio": "tuning", "arrival book": "pages", "arrival strangers": "knock" };

/** Compare what was heard before with what is here now. On the first look nothing plays: old news is not announced. */
export function news(seen: Seen | null, s: Ears) {
  const sung = s.sung ?? [], said = s.radio?.said ?? [], acts = s.acts ?? [], vox = s.vox ?? [];
  // a replay wound back or scrubbed far ahead, or a tab left asleep: start listening afresh, announce nothing old
  if (seen && (s.tick < seen.tick || (s.tick - seen.tick) * (s.tick_seconds ?? 0) > 120)) seen = null;
  const now: Seen = { tick: s.tick, act: Math.max(seen?.act ?? 0, ...acts.map((a) => a.n)), vox: Math.max(seen?.vox ?? 0, ...vox.map((x) => x.n)), said: Object.fromEntries(s.pets.filter((p) => p.said).map((p) => [p.id, p.said!.tick])), moment: Math.max(0, ...s.moments.map((m) => m.n)),
                      sung: Math.max(seen?.sung ?? 0, ...sung.map((x) => x.tick)), radio: Math.max(seen?.radio ?? 0, ...said.map((x) => x.tick)) };
  const speak: { pet: string; text: string }[] = [], sounds: { kind: SoundKind; pet: string; room: string | null }[] = [], house: { kind: HouseSound; room: string | null; moment: string }[] = [];
  if (seen) {
    for (const p of s.pets) if (p.said && p.said.tick !== seen.said[p.id] && !p.said.song) speak.push({ pet: p.id, text: p.said.text });   // a song is played, not said
    for (const m of s.moments.filter((m) => m.n > seen.moment)) {
      if (BY_PET[m.kind] && m.pet) sounds.push({ kind: BY_PET[m.kind], pet: m.pet, room: m.room });
      if (BY_HOUSE[m.kind]) house.push({ kind: BY_HOUSE[m.kind], room: m.room, moment: m.kind });
    }
  }
  // songs sung and words from the box (SPEC-v3.1): each is heard once
  // and each step a pet finishes (SPEC-v3.2 §8), by its running number
  const [was, old] = [seen?.sung ?? 0, seen?.radio ?? 0], done = seen?.act ?? 0;
  return { seen: now, speak, sounds, house, sing: seen ? sung.filter((x) => x.tick > was) : [], heard: seen ? said.filter((x) => x.tick > old) : [],
           acts: seen ? acts.filter((a) => a.n > done && a.ok) : [], vox: seen ? vox.filter((x) => x.n > seen.vox) : [] };
}
