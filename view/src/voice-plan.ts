// The pet's voice, as plans (VOICE.md, Phase 1). Everything here is plain arithmetic: text and genome in,
// notes out. voice.ts turns the notes into sound. Nothing in the voice reaches the pet or the engine.
import type { Genome } from "./pet";

export type Needs3 = { energy: number; comfort: number; curiosity: number };
export type VoiceInput = { stage: string; genome: Genome; needs: Needs3; trend?: Partial<Needs3> };
export type Tone = { at: number; dur: number; f0: number; f1: number; gain: number };   // seconds, Hz, 0..1
export type Timbre = { wave: "sine" | "triangle" | "square"; cutoff: number; vibratoCents: number; vibratoHz: number; tremolo: number };
export type Plan = { tones: Tone[]; timbre: Timbre; length: number };
export type SoundKind = "cry" | "chirp" | "blip" | "trill" | "stageup" | "hm" | "whimper";

const BASE: Record<string, number> = { egg: 700, hatchling: 700, child: 520, youngling: 420, adult: 330 };
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
  const g = v.genome, low = Math.min(v.needs.energy, v.needs.comfort, v.needs.curiosity);
  const base = (BASE[v.stage] ?? 700) * (1 - 0.1 * clamp((g.stretch - 1.075) / 0.325, -1, 1));   // taller is lower
  const wave: Timbre["wave"] = g.roundness > 0.7 ? "sine" : g.roundness >= 0.4 ? "triangle" : "square";
  const open = base * (2 + 8 * g.saturation);                                    // pale is muffled, vivid is clear
  return {
    base,
    syllable: (140 - 0.8 * clamp(v.needs.energy, 0, 100)) / 1000,              // 60 ms lively, 140 ms worn out
    sad: v.needs.comfort < 30,                                                  // phrases drift down and sit lower
    eager: v.needs.curiosity >= 70 || (v.trend?.curiosity ?? 0) > 0.5,          // phrases end up
    timbre: {
      wave, cutoff: wave === "square" ? Math.min(open, base * 3.5) : open,       // a square buzzes; keep it from being harsh
      vibratoCents: 40 * clamp(g.wobble, 0, 1), vibratoHz: 5 + 2 * clamp(g.wobble, 0, 1),
      tremolo: low < 20 ? 0.4 : 0,                                              // any need under 20: shaky
    } as Timbre,
  };
}

/** A word as syllables: each is its consonants and the vowel group after them; trailing consonants join the last. */
export function syllables(word: string): string[] {
  const letters = word.toLowerCase().replace(/[^a-z]/g, "");
  return letters ? letters.match(/[^aeiouy]*[aeiouy]+(?:[^aeiouy]*$)?/g) ?? [letters] : [];
}

/** Speech: one short note per syllable, shaped by punctuation and by how the pet is. */
export function planSpeech(text: string, v: VoiceInput): Plan {
  const voice = voiceOf(v), tones: Tone[] = [];
  let t = 0, count = 0;
  for (const sentence of text.match(/[^.!?…]+(?:\.\.\.|…|[.!?])?/g) ?? []) {
    const end = /(\.\.\.|…)$/.test(sentence) ? "..." : /[.!?]$/.test(sentence) ? sentence.slice(-1) : "";
    const first = tones.length;
    sentence.split(",").forEach((clause, c) => {
      if (c) t += voice.syllable * 2;                                           // a comma is a longer gap
      for (const word of clause.split(/\s+/)) {
        const parts = syllables(word).slice(0, MAX_SYLLABLES - count);
        if (!parts.length) continue;
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
  return { tones, timbre: voice.timbre, length: Math.max(0, t - voice.syllable * 3) };
}

/** The sounds without words, made from the same voice so they are the same creature. */
export function planSound(kind: SoundKind, v: VoiceInput): Plan {
  const voice = voiceOf(v), b = voice.base, timbre = { ...voice.timbre };
  const seq = (notes: [number, number, number, number][], gain: number): Plan => {   // [at, dur, from, to] in multiples of the base
    const tones = notes.map(([at, dur, from, to]) => ({ at, dur, f0: b * from, f1: b * to, gain }));
    return { tones, timbre, length: Math.max(...tones.map((n) => n.at + n.dur)) };
  };
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
  }
}

// ---- which changes in what the view receives call for which sound ----

type Made = { made?: { behavior?: { do: string } }; active?: boolean };
export type Heard = {
  pet: { said: [number, string] | null; stage: string };
  moments: [number, string][];
  events: [number, string][];
  objects: Record<string, Made>;
  sleep: unknown;
};
export type Step = { type: string; tick: number; action?: unknown; reason?: string | null; own?: Partial<Needs3> };
export type Catalog = { name: string; ups?: number }[];
export type Seen = { said: number; moments: Set<string>; events: Set<string>; step: number; ups: Record<string, number> };

const MOMENT: [RegExp, SoundKind][] = [
  [/^it hatched/, "cry"], [/^it is now a/, "stageup"], [/^it (made a|combined)/, "chirp"], [/^it took apart/, "blip"],
];

/** Compare what was seen before with what is here now. On the first look nothing plays: old news is not announced. */
export function triggers(seen: Seen | null, w: Heard, journal: Step[], things: Catalog) {
  const key = ([tick, text]: [number, string]) => `${tick}|${text}`;
  const steps = journal.filter((r) => r.type === "step");
  const now: Seen = {
    said: w.pet.said ? w.pet.said[0] : -1, moments: new Set(w.moments.map(key)), events: new Set(w.events.map(key)),
    step: Math.max(-1, ...steps.map((r) => r.tick)), ups: Object.fromEntries(things.map((t) => [t.name, t.ups ?? 0])),
  };
  const sounds: SoundKind[] = [];
  let speak: string | null = null;
  if (seen) {
    if (w.pet.said && now.said !== seen.said) speak = w.pet.said[1];
    for (const m of w.moments) {
      const kind = seen.moments.has(key(m)) ? undefined : MOMENT.find(([pattern]) => pattern.test(m[1]))?.[1];
      if (kind) sounds.push(kind);
    }
    for (const r of steps) {   // used a thing that helped: energy or comfort went up from the use itself, or the engine counted it as a help
      const a = r.action as { type?: string; target?: string } | undefined;
      if (r.tick <= seen.step || r.reason || a?.type !== "use" || !a.target) continue;
      const helped = (r.own?.comfort ?? 0) >= 0.5 || (r.own?.energy ?? 0) >= 0.5 || (now.ups[a.target] ?? 0) > (seen.ups[a.target] ?? 0);
      if (helped) sounds.push("trill");
    }
    if (w.events.some((e) => !seen.events.has(key(e)) && /^visitor (said|poked)/.test(e[1]))) sounds.push("hm");
  }
  const order: SoundKind[] = ["cry", "stageup", "chirp", "blip", "trill", "hm"];
  return {
    seen: now, speak, sounds: [...new Set(sounds)].sort((a, b) => order.indexOf(a) - order.indexOf(b)),
    ambient: {
      egg: w.pet.stage === "egg", asleep: !!w.sleep,
      hums: Object.entries(w.objects).filter(([, o]) => o.active && o.made?.behavior?.do === "hum").map(([name]) => name),
    },
  };
}
