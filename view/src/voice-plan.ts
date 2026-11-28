// The house's sound, as plans (AUDIO-BRIEF §4, VOICE.md): plain arithmetic, no browser, so check-voice.ts can test it.
// What a snapshot holds that calls for a sound (news), what the sound files are and how loud (sounds.json), a hob's
// line as babble pitched to its body, the music and ambience the room on screen wants, and songs in a hob's own voice
// (the one sound still made in the browser: the hobs' tunes are theirs, no file has them). voice.ts plays it all.
import type { Genome } from "./pet";

export type Needs3 = { energy: number; comfort: number; curiosity: number; company?: number };
/** `words` are the real words it knows how to say (its name, its useful things, the others' names); see planSpeech. */
export type VoiceInput = { stage: string; genome: Genome; needs: Needs3; trend?: Partial<Needs3>; words?: string[] };
export type Tone = { at: number; dur: number; f0: number; f1: number; gain: number };   // seconds, Hz, 0..1
export type Timbre = { wave: "sine" | "triangle" | "square"; cutoff: number; vibratoCents: number; vibratoHz: number; tremolo: number };
export type Plan = { tones: Tone[]; timbre: Timbre; length: number; words?: { at: number; word: string }[] };

const BASE: Record<string, number> = { egg: 700, hatchling: 700, child: 520, youngling: 420, adult: 330, elder: 290 };
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
  pets: { id: string; room: string; said?: { text: string; tick: number; song?: string; to?: string | null } | null }[];
  moments: { n: number; kind: string; pet: string | null; room: string | null }[];
  sung?: { tick: number; by: string; song: string; room: string }[];
  // SPEC-v3.2: steps just finished, numbered. SPEC-v3.3: `kind` of a made thing, `loud` if what was used sounds
  acts?: { n: number; type: string; pet: string; what?: string | null; room: string; ok: boolean; kind?: string | null; loud?: boolean }[];
  vox?: { n: number; pet: string; room: string; kind: string }[];   // SPEC-v3.3 §4: the small sounds, numbered
};
export type Seen = { tick: number; said: Record<string, number>; moment: number; sung: number; act: number; vox: number };
/** SPEC-v3.6b §4: the anvil rings while the forge is worked in the room on screen, never sooner than `RING_GAP` seconds after the last ring. */
export const RING_GAP = 4;
export const rings = (s: { rooms: { id: string; objects?: Record<string, { machine?: { kind: string; state: string } }> }[] }, here: string, now: number, last: number) =>
  now - last >= RING_GAP && !!s.rooms.find((r) => r.id === here && Object.values(r.objects ?? {}).some((o) => o.machine?.kind === "forge" && o.machine.state === "working"));

/** Compare what was heard before with what is here now. On the first look nothing plays: old news is not announced. */
export function news(seen: Seen | null, s: Ears) {
  const sung = s.sung ?? [], acts = s.acts ?? [], vox = s.vox ?? [];
  // a replay wound back or scrubbed far ahead, or a tab left asleep: start listening afresh, announce nothing old
  if (seen && (s.tick < seen.tick || (s.tick - seen.tick) * (s.tick_seconds ?? 0) > 120)) seen = null;
  const now: Seen = { tick: s.tick, act: Math.max(seen?.act ?? 0, ...acts.map((a) => a.n)), vox: Math.max(seen?.vox ?? 0, ...vox.map((x) => x.n)), said: Object.fromEntries(s.pets.filter((p) => p.said).map((p) => [p.id, p.said!.tick])), moment: Math.max(0, ...s.moments.map((m) => m.n)),
                      sung: Math.max(seen?.sung ?? 0, ...sung.map((x) => x.tick)) };
  const speak: { pet: string; text: string; to?: string | null }[] = [];
  if (seen) for (const p of s.pets) if (p.said && p.said.tick !== seen.said[p.id] && !p.said.song) speak.push({ pet: p.id, text: p.said.text, to: p.said.to });   // a song is played, not said
  // songs sung (SPEC-v3.1): each is heard once; and each step a pet finishes (SPEC-v3.2 §8), by its running number
  const was = seen?.sung ?? 0, done = seen?.act ?? 0;
  return { seen: now, speak, moments: seen ? s.moments.filter((m) => m.n > seen.moment) : [], sing: seen ? sung.filter((x) => x.tick > was) : [],
           acts: seen ? acts.filter((a) => a.n > done && a.ok) : [], vox: seen ? vox.filter((x) => x.n > seen.vox) : [] };
}

// ---- the sound files (view/assets/sounds.json, view/assets/README.md "sounds.json") ----

export type SoundEntry = { group: string; n?: number; loop?: boolean; gain?: number };
export type Sounds = {
  dir: string; groups: Record<string, number>; buses: Record<string, "music" | "ambience" | "voices">;
  mix: { night: number; far: number; muffle: number; train_far: number; roof: number; shut_in: number; indoors: number; fade: number; rest: [number, number]; gap: [number, number]; effects: number; loops: number };
  music: { day: string; night: string; winter: string; outdoors: { day: string; night: string }; rooms: Record<string, string | null>; moods: Record<string, string>; visitor: Record<string, string[]> };
  ambience: { rooms: Record<string, string[]>; weather: Record<string, { in: string[]; out: string[] }>; outside: string[]; open: string[]; shut_in: string[] };
  floors: Record<string, string>; on: Record<string, string | string[]>; sounds: Record<string, SoundEntry>;
};
export type Bus = "music" | "ambience" | "effects" | "voices";
export const BUSES: Bus[] = ["music", "ambience", "effects", "voices"];

/** Every file a sound of ours is, as paths under the art folder: `n` variants are name_1 ... name_n. */
export const filesOf = (S: Sounds, name: string) => {
  const e = S.sounds?.[name];
  return !e ? [] : e.n ? Array.from({ length: e.n }, (_, i) => `${S.dir}/${name}_${i + 1}.wav`) : [`${S.dir}/${name}.wav`];
};
/** dB to a gain. */
export const gainOf = (db: number) => 10 ** (db / 20);
/** How loud a sound of ours plays (its group's level, and its own `gain` in dB on top), and on which slider. */
export const levelOf = (S: Sounds, name: string) => {
  const e = S.sounds?.[name];
  return e ? { gain: gainOf((S.groups[e.group] ?? 0) + (e.gain ?? 0)), bus: (S.buses[e.group] ?? "effects") as Bus, loop: !!e.loop } : null;
};
/** What the `on` table says plays for an event: a name, or one of a list at random; null if nothing. */
export const soundFor = (S: Sounds, key: string, r = Math.random) => {
  const v = S.on?.[key];
  return !v ? null : typeof v === "string" ? v : v.length ? v[Math.floor(r() * v.length)] : null;
};

/** §4.7: the same sound in the same room at most once every 1 to 2 seconds (`gap`, in seconds; a random wait each time). */
export class Gate {
  private next = new Map<string, number>();
  private gap: [number, number];
  private r: () => number;
  constructor(gap: [number, number], r = Math.random) { this.gap = gap; this.r = r; }
  /** May `key` sound at `now` (seconds)? If so, it is shut for the next while. `every` overrides the gap. */
  open(key: string, now: number, every?: number) {
    if (now < (this.next.get(key) ?? -Infinity)) return false;
    const [lo, hi] = every ? [every * 0.8, every * 1.2] : this.gap;
    this.next.set(key, now + lo + (hi - lo) * this.r());
    if (this.next.size > 500) for (const [k, t] of this.next) if (t < now) this.next.delete(k);
    return true;
  }
}

/** A hob's line as babble (the brief's batch 4: single syllables strung into speech): one syllable a few letters, short
 *  gaps between words, longer ones at a comma or the end of a sentence; pitched to its body (`base`, voiceOf's Hz:
 *  a child higher, a tall elder lower), each syllable ±5%, a question rising at the end and a "!" a little louder. A
 *  hatchling peeps one syllable a word, high; an egg says nothing. `v` is the variant (0 to n-1). At most 14. */
export function babble(text: string, base: number, stage: string, n = 8, r = Math.random) {
  if (stage === "egg") return [];
  const little = stage === "hatchling", rate = clamp((base / 420) ** 0.6, 0.75, 1.4) * (little ? 1.15 : 1);
  const step = stage === "elder" ? 0.16 : little ? 0.2 : 0.12, out: { at: number; rate: number; gain: number; v: number }[] = [];
  let t = 0;
  for (const sentence of text.match(/[^.!?…]+[.!?…]*/g) ?? []) {
    const end = sentence.trim().slice(-1), first = out.length;
    for (const word of sentence.split(/\s+/)) {
      const letters = word.replace(/[^a-z]/gi, "").length;
      if (!letters) continue;
      for (let k = 0, m = little ? 1 : Math.max(1, Math.round(letters / 3.2)); k < m && out.length < 14; k++) {
        out.push({ at: t, rate: rate * (1 + (r() * 2 - 1) * 0.05), gain: 1, v: Math.floor(r() * n) });
        t += step * (0.85 + 0.3 * r());
      }
      t += /,$/.test(word) ? step * 1.5 : step * 0.35;
    }
    const said = out.slice(first);
    if (end === "?" && said.length) said[said.length - 1].rate *= 1.12;
    if (end === "!") for (const x of said) x.gain = 1.25;
    t += step * 2;
    if (out.length >= 14) break;
  }
  return out;
}

/** What music the house wants (§2, §4.2, §4.5): a mood that takes over (a fight here or next door, a quarrel, grief,
 *  a celebration) before anything; else a storm; else the room's own theme; else outdoors or the house by day or night
 *  (the winter tune for the day, in winter). `take`: the mood breaks into a rest. Null: no music (the music room plays
 *  only the hobs' own songs). */
export function wantMusic(S: Sounds, o: { mood: string | null; type: string; phase: string; season: string; weather: string }) {
  const M = S.music, day = o.phase === "day";
  if (o.mood && M.moods[o.mood]) return { name: M.moods[o.mood], take: true };
  if (o.type in M.rooms && !M.rooms[o.type]) return null;
  const name = o.weather === "storm" ? M.moods.storm : M.rooms[o.type] ?? (S.ambience.outside.includes(o.type) ? M.outdoors[day ? "day" : "night"] : day ? (o.season === "winter" ? M.winter : M.day) : M.night);
  return name ? { name, take: false } : null;
}

/** The room's ambience and the weather's on top (§4.2, at most three layers): each with how loud it is (a gain), and
 *  `roof` if it is heard through a roof (muffled). Night files after dark. */
export function wantAmbience(S: Sounds, type: string, phase: string, weather: string) {
  const A = S.ambience, room = A.rooms[type] ?? [], night = phase !== "day", out: { name: string; gain: number; roof: boolean }[] = [];
  const own = night && room[1] ? room[1] : room[0];
  if (own) out.push({ name: own, gain: 1, roof: false });
  const outside = A.outside.includes(type), w = A.weather[weather];
  const level = outside || A.open.includes(type) ? 1 : gainOf(A.shut_in.includes(type) ? S.mix.shut_in : S.mix.indoors);
  for (const name of (outside ? w?.out : w?.in) ?? []) if (out.length < 3) out.push({ name, gain: level, roof: level < 1 });
  return out;
}
