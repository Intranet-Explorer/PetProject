// The house's sound (VOICE.md, SPEC-v3 §10.6). Web Audio only: no libraries, no audio files; from youngling on, a
// word a pet really knows is said with the browser's own speech voice, pitched to its body.
// View-only: it listens to what the view already receives and nothing here goes back to the engine.
import { hash, news, planSong, planSound, planSpeech, planVox, semitone, voiceOf } from "./voice-plan";
import type { HouseSound, Plan, Seen, SoundKind, VoiceInput, VoxKind } from "./voice-plan";
import { inventedSound } from "./parts";
import { clip, sound, sounds } from "./sprite";
import type { Layer } from "./sprite";
import { bodyStage } from "./types";
import type { Note, PetV, Snap } from "./types";

const STORE = "sound";
const AHEAD = 6;   // seconds of heartbeat, breathing or a room's ticks kept scheduled on the audio clock; a snapshot tops it up
// SPEC-v3.3 §4, distance: next door is heard this much quieter and only under this many Hz; `FADE` is how fast one
// thing gives way to another (the time constant of a cross-fade, in seconds)
const [FAR, MUFFLE, FADE] = [0.22, 700, 0.6];
/** What the page has sounded, for checking without ears (window.petView.audioLog): `t` is ms since the page loaded. */
export type Logged = { t: number; what: "speech" | "vox" | "instrument" | "song" | "ambience" | "music" | "radio" | "sfx"; name: string; pet?: string; room?: string;
  where: "here" | "next door"; gain: number };
const LABEL: Record<SoundKind, string> = {
  cry: "first cry (hatched)", chirp: "chirp (made a thing)", blip: "falling blip (took a thing apart)",
  trill: "content trill (a nuzzle or a gift taken)", stageup: "three rising notes (a new stage)",
  hm: "“hm?”", whimper: "whimper (miserable a long while)", last: "two falling notes (a death)",
};
const HOUSE: Record<HouseSound | Creature, string> = {
  powerdown: "the power's hum dying", powerup: "the power coming back", thunder: "thunder", drip: "water dripping", whoosh: "a draught, and a door",
  thud: "a crate set down", moth: "a moth's flutter", beetle: "a beetle's clicks", mouse: "a mouse's squeak", bird: "birdsong",
  chalk: "chalk on a wall (writing has come)", chime: "the music box, by itself (songs have come)", patter: "small feet coming closer (taming has come)",
  tuning: "a dial finding a voice (the radio has come)", pages: "a heavy book set down (the book has come)", knock: "a knock from inside an egg (a stranger has come)",
};
export type Creature = "moth" | "beetle" | "mouse" | "bird";
/** SPEC-v3.2 §8: the step a pet has just finished, as the name of a sound effect in the art data (sounds.json). */
const SFX: Record<string, string> = { gather: "pickup", take: "pickup", accept: "pickup", drop: "drop", give: "drop", arrange: "drop", make: "make", unmake: "unmake",
  combine: "combine", go: "door", eat: "eat", write: "write", scrub: "write", ask_book: "book", call: "call", nuzzle: "heart",
  machine_take: "clunk", machine_feed: "clunk" };   // SPEC-v3.5 §4.3: the vending machine gives something
// how much of the sky a kind of room hears: all of it, none of it, or (every other room) some, through the roof
const OPEN = ["garden", "greenhouse", "attic", "pond"], SHUT_IN = ["cellar", "storeroom"];

/** Put a plan's notes on an audio clock. Works on a live context and on an offline one, which is how it is checked. */
export function schedule(ctx: BaseAudioContext, dest: AudioNode, plan: Plan, at: number) {
  const { wave, cutoff, tremolo, vibratoCents, vibratoHz } = plan.timbre, end = at + plan.length + 0.1;
  const filter = new BiquadFilterNode(ctx, { type: "lowpass", frequency: cutoff, Q: 0.7 });
  const shake = new GainNode(ctx, { gain: 1 - tremolo / 2 });
  filter.connect(shake).connect(dest);
  const lfo = (frequency: number, depth: number) => {
    const osc = new OscillatorNode(ctx, { frequency }), amount = new GainNode(ctx, { gain: depth });
    osc.connect(amount);
    osc.start(at);
    osc.stop(end);
    return amount;
  };
  if (tremolo) lfo(9, tremolo / 2).connect(shake.gain);                     // shaky when a need is very low
  const vibrato = vibratoCents ? lfo(vibratoHz, vibratoCents) : null;
  const loud = wave === "square" ? 0.4 : wave === "triangle" ? 0.8 : 1;      // even out how loud each wave seems
  for (const n of plan.tones) {
    const t0 = at + n.at, t1 = t0 + n.dur, attack = Math.min(0.012, n.dur / 3), release = Math.min(0.03, n.dur / 2);
    const osc = new OscillatorNode(ctx, { type: wave, frequency: n.f0 }), env = new GainNode(ctx, { gain: 0 });
    osc.frequency.setValueAtTime(n.f0, t0);
    if (n.f1 !== n.f0) osc.frequency.exponentialRampToValueAtTime(n.f1, t1);
    vibrato?.connect(osc.detune);
    env.gain.setValueAtTime(0, t0);                                         // a soft attack and release on every note
    env.gain.linearRampToValueAtTime(n.gain * loud, t0 + attack);
    env.gain.setValueAtTime(n.gain * loud, t1 - release);
    env.gain.linearRampToValueAtTime(0, t1);
    osc.connect(env).connect(filter);
    osc.start(t0);
    osc.stop(t1 + 0.02);
  }
  return end;
}

/** One heartbeat thump: low and soft, for the egg. */
function thump(ctx: BaseAudioContext, dest: AudioNode, at: number, level: number) {
  const osc = new OscillatorNode(ctx, { type: "triangle", frequency: 96 }), env = new GainNode(ctx, { gain: 0 });
  osc.frequency.setValueAtTime(96, at);
  osc.frequency.exponentialRampToValueAtTime(58, at + 0.14);
  env.gain.setValueAtTime(0, at);
  env.gain.linearRampToValueAtTime(0.5 * level, at + 0.012);
  env.gain.exponentialRampToValueAtTime(0.001, at + 0.2);
  osc.connect(env).connect(new BiquadFilterNode(ctx, { type: "lowpass", frequency: 320 })).connect(dest);
  osc.start(at);
  osc.stop(at + 0.22);
}

/** Breath is noise through a band around the pet's own pitch; the returned gain is what each breath shapes. */
function lungs(ctx: BaseAudioContext, dest: AudioNode, base: number) {
  const buffer = new AudioBuffer({ length: ctx.sampleRate * 2, sampleRate: ctx.sampleRate }), data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  const noise = new AudioBufferSourceNode(ctx, { buffer, loop: true }), air = new GainNode(ctx, { gain: 0 });
  noise.connect(new BiquadFilterNode(ctx, { type: "bandpass", frequency: Math.min(1100, Math.max(280, base * 1.1)), Q: 0.8 })).connect(air).connect(dest);
  noise.start();
  return { noise, air };
}

function breath(air: GainNode, at: number) {   // in for a second and a half, out for two and a half; quiet, but meant to be heard
  air.gain.setValueAtTime(0, at);
  air.gain.linearRampToValueAtTime(0.2, at + 1.5);
  air.gain.linearRampToValueAtTime(0.015, at + 2.1);
  air.gain.linearRampToValueAtTime(0.14, at + 2.8);
  air.gain.linearRampToValueAtTime(0, at + 4.6);
  return at + 5.4;
}

function hiss(ctx: BaseAudioContext, seconds = 2) {   // white noise, the stuff of rain, wind, wings and thunder
  const buffer = new AudioBuffer({ length: Math.ceil(ctx.sampleRate * seconds), sampleRate: ctx.sampleRate }), data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  return buffer;
}

/** One note that is nobody's voice: a wave sliding from `f0` to `f1`, struck and dying away. */
function blip(ctx: BaseAudioContext, dest: AudioNode, at: number, type: OscillatorType, f0: number, f1: number, dur: number, gain: number, cutoff = 6000) {
  const osc = new OscillatorNode(ctx, { type, frequency: f0 }), env = new GainNode(ctx, { gain: 0 });
  osc.frequency.setValueAtTime(f0, at);
  osc.frequency.exponentialRampToValueAtTime(f1, at + dur);
  env.gain.setValueAtTime(0, at);
  env.gain.linearRampToValueAtTime(gain, at + Math.min(0.02, dur / 3));
  env.gain.exponentialRampToValueAtTime(0.001, at + dur);
  osc.connect(new BiquadFilterNode(ctx, { type: "lowpass", frequency: cutoff })).connect(env).connect(dest);
  osc.start(at);
  osc.stop(at + dur + 0.05);
}

/** A sound of the house or of a small creature: none of them is anyone's voice. Returns when it ends. */
export function effect(ctx: BaseAudioContext, dest: AudioNode, kind: HouseSound | Creature, at: number) {
  const tone = (type: OscillatorType, f0: number, f1: number, t: number, dur: number, gain: number, cutoff = 6000) => (blip(ctx, dest, at + t, type, f0, f1, dur, gain, cutoff), t + dur);
  const burst = (type: BiquadFilterType, f0: number, f1: number, t: number, dur: number, gain: number, attack = 0.02) => {
    const src = new AudioBufferSourceNode(ctx, { buffer: hiss(ctx, dur + 0.1) }), env = new GainNode(ctx, { gain: 0 });
    const filter = new BiquadFilterNode(ctx, { type, frequency: f0, Q: 0.9 });
    filter.frequency.setValueAtTime(f0, at + t);
    filter.frequency.exponentialRampToValueAtTime(f1, at + t + dur);
    env.gain.setValueAtTime(0, at + t);
    env.gain.linearRampToValueAtTime(gain, at + t + attack);
    env.gain.exponentialRampToValueAtTime(0.001, at + t + dur);
    src.connect(filter).connect(env).connect(dest);
    src.start(at + t);
    src.stop(at + t + dur + 0.05);
    return t + dur;
  };
  switch (kind) {
    case "powerdown": return at + tone("sawtooth", 120, 28, 0, 1.8, 0.16, 420);                    // every light at once: the hum runs down
    case "powerup": return at + tone("sawtooth", 40, 120, 0, 0.9, 0.12, 420);
    case "thunder": burst("lowpass", 260, 70, 0, 0.5, 2.2, 0.03); return at + burst("lowpass", 160, 50, 0.3, 2.6, 2.0, 0.25);
    case "drip": return at + Math.max(...[0, 0.42, 0.7].map((t, i) => tone("sine", 1500 - 200 * i, 700, t, 0.09, 0.16)));
    case "whoosh": burst("bandpass", 300, 1300, 0, 0.9, 0.3, 0.4); return at + tone("sine", 90, 45, 0.85, 0.22, 0.4);   // and the door thuds shut
    case "thud": return at + tone("sine", 85, 40, 0, 0.28, 0.5);
    case "moth": return at + Math.max(...[0, 1, 2, 3, 4, 5, 6, 7].map((i) => burst("bandpass", 3200, 2600, i * 0.045, 0.03, 0.3, 0.005)));
    case "beetle": return at + Math.max(...[0, 0.11, 0.2].map((t) => tone("square", 190, 150, t, 0.018, 0.1, 900)));
    case "mouse": return at + Math.max(tone("sine", 2600, 3400, 0, 0.07, 0.1), tone("sine", 2900, 3600, 0.12, 0.06, 0.08));
    // the six discoveries (SPEC-v3.1 §1)
    case "chalk": return at + Math.max(...[0, 0.24, 0.5].map((t) => burst("bandpass", 2400, 3800, t, 0.17, 0.2)), tone("sine", 900, 500, 0.72, 0.04, 0.12));   // three strokes and a tap
    case "chime": return at + Math.max(...[1047, 1319, 1568, 2093].map((f, i) => tone("sine", f, f, i * 0.12, 0.6, 0.13)));
    case "patter": return at + Math.max(...[0, 1, 2, 3, 4].map((i) => tone("sine", 240, 120, i * 0.09, 0.05, 0.16)), tone("sine", 1800, 2400, 0.56, 0.08, 0.06));
    case "tuning": burst("bandpass", 600, 3200, 0, 0.7, 0.16, 0.1); tone("sine", 2400, 700, 0.1, 0.6, 0.05); return at + tone("square", 120, 80, 0.74, 0.03, 0.2, 800);
    case "pages": tone("sine", 70, 38, 0, 0.3, 0.55); return at + Math.max(...[0.36, 0.48, 0.6].map((t) => burst("highpass", 2500, 4500, t, 0.09, 0.12, 0.01)));
    case "knock": tone("triangle", 180, 110, 0, 0.07, 0.4, 700); tone("triangle", 180, 110, 0.18, 0.07, 0.4, 700); return at + tone("sine", 520, 780, 0.5, 0.3, 0.12);
    case "bird": return at + Math.max(...[[0, 2400, 3100], [0.13, 3100, 2500], [0.26, 2600, 3300], [0.42, 3300, 3300], [0.5, 3300, 2700]].map(([t, a, b]) => tone("sine", a, b, t, 0.1, 0.11)));
  }
}

const BOX_TUNE: Note[] = [["mi", 0], ["so", 0], ["la", 1], ["so", 0], ["mi", 0], ["re", 0], ["do", 1]];   // the music box's tune, as the engine has it (songs.BOX), for a house where it has not yet played by itself

/** A tune that is nobody's voice (SPEC-v3.1 §3.4): the music box plucks each note and lets it ring, a bird whistles
 *  it high with a little run up into each note. Returns when it ends. */
export function tune(ctx: BaseAudioContext, dest: AudioNode, notes: Note[], at: number, bird = false) {
  let t = at;
  for (const [pitch, long] of notes) {
    const f = (bird ? 1175 : 880) * 2 ** (semitone(pitch) / 12), dur = (bird ? 0.13 : 0.3) * (long ? 2 : 1);
    for (const [k, gain] of bird ? [[1, 0.1]] : [[1, 0.2], [3, 0.04]]) {   // the box's comb rings with a high partial
      const osc = new OscillatorNode(ctx, { frequency: f * k }), env = new GainNode(ctx, { gain: 0 });
      osc.frequency.setValueAtTime(f * k * (bird ? 0.86 : 1), t);
      osc.frequency.exponentialRampToValueAtTime(f * k, t + 0.04);
      env.gain.setValueAtTime(0, t);
      env.gain.linearRampToValueAtTime(gain, t + (bird ? 0.015 : 0.004));
      env.gain.exponentialRampToValueAtTime(0.001, t + dur + (bird ? 0 : 0.9));
      osc.connect(env).connect(dest);
      osc.start(t);
      osc.stop(t + dur + 1);
    }
    t += dur + (bird ? 0.05 : 0);
  }
  return t + (bird ? 0 : 0.6);
}

/** A sound file made to go round without a seam: its last second is faded into its first (a recording of rain ends
 *  quieter than it begins). */
function seamless(b: AudioBuffer) {
  const n = Math.floor(Math.min(1, b.duration / 4) * b.sampleRate), out = new AudioBuffer({ length: b.length - n, numberOfChannels: b.numberOfChannels, sampleRate: b.sampleRate });
  for (let c = 0; c < b.numberOfChannels; c++) {
    const from = b.getChannelData(c), to = out.getChannelData(c);
    to.set(from.subarray(0, b.length - n));
    for (let i = 0; i < n; i++) to[i] = from[i] * (i / n) + from[b.length - n + i] * (1 - i / n);
  }
  return out;
}

type Clip = { buffer: AudioBuffer; gain: number };
/** One layer of what a place sounds like (assets/README.md, "ambience"): a file going round, or one of the sounds made
 *  here (wind, water, hum, and the ones made of separate events: drips, birds, creak, crackle, crickets). It keeps
 *  going until it is stopped. `out` is its own volume, silent to begin with, for fading it in and out; `tick` puts
 *  the events up to a moment on the audio clock, and is called again and again. `gain` in the data is how loud the
 *  layer's loudest moment is; `load` fetches a sound file of the data (an effect by name, or the layer's own file). */
export function ambient(ctx: BaseAudioContext, dest: AudioNode, L: Layer, load: (what: string | Layer) => Promise<Clip | null> = async () => null) {
  const out = new GainNode(ctx, { gain: 0 }), into = new GainNode(ctx, { gain: L.gain ?? 0.03 }), live: AudioScheduledSourceNode[] = [];
  const g = into.gain.value, rate = L.rate ?? 0.2, f = L.pitch ?? 400, r = Math.random;
  let until = Infinity, tick = (_until: number) => {}, drop: Clip | null = null;
  into.connect(out).connect(dest);
  if (L.echo) {   // a drip in a cellar rings on
    const delay = new DelayNode(ctx, { delayTime: 0.33 }), back = new GainNode(ctx, { gain: 0.65 * L.echo });
    into.connect(delay).connect(back).connect(delay);
    back.connect(out);
  }
  const run = <T extends AudioScheduledSourceNode>(n: T) => { n.start(); live.push(n); return n; };
  /** Hiss through a filter, made up to the loudness asked for whatever the filter leaves of it (`width`, in Hz). */
  const noise = (filter: BiquadFilterNode, width: number) => {
    const vol = new GainNode(ctx, { gain: (0.3 * g) / (0.577 * Math.sqrt((Math.PI * width) / ctx.sampleRate)) });
    run(new AudioBufferSourceNode(ctx, { buffer: hiss(ctx, 3), loop: true })).connect(filter).connect(vol).connect(out);
    return vol;
  };
  const sway = (to: AudioParam, hz: number, depth: number) => { run(new OscillatorNode(ctx, { frequency: hz })).connect(new GainNode(ctx, { gain: depth })).connect(to); };
  /** Something that happens now and then: `rate` times a second, evenly (a clock) or scattered. The data may name a
   *  recorded effect to use for it; an effect's own gain is what evens the recordings out, so ten times it is full size. */
  const every = (make: (t: number, n: number) => void) => {
    const gap = () => (L.steady ? 1 : -Math.log(1 - r())) / rate;
    let next = ctx.currentTime + (L.steady ? 0.1 : gap()), n = 0;
    tick = (until) => {
      for (next = Math.max(next, ctx.currentTime); next < until; next += gap()) {
        if (!drop) { make(next, n++); continue; }
        const src = new AudioBufferSourceNode(ctx, { buffer: drop.buffer, playbackRate: 0.85 + 0.4 * r() });
        src.connect(new GainNode(ctx, { gain: 10 * drop.gain })).connect(into);
        src.start(next);
      }
    };
  };
  if (L.sfx) void load(L.sfx).then((c) => (drop = c));
  switch (L.synth) {
    case "wind": {   // hiss in a band round its pitch, swelling and sinking, the band sliding a little as it does
      const band = new BiquadFilterNode(ctx, { type: "bandpass", frequency: f, Q: 1.5 }), vol = noise(band, f / 1.5);
      sway(vol.gain, rate, vol.gain.value * 0.6);
      sway(band.frequency, rate * 0.37, f * 0.2);
      break;
    }
    case "water": {   // low hiss, lapping: a slow swell and a quicker one over it
      const vol = noise(new BiquadFilterNode(ctx, { type: "lowpass", frequency: 500 }), 500);
      sway(vol.gain, rate, vol.gain.value * 0.5);
      sway(vol.gain, rate * 2.7, vol.gain.value * 0.25);
      break;
    }
    case "hum": {   // one steady note and a little of the two above it, with a slow wobble
      const vol = new GainNode(ctx, { gain: g });
      for (const [k, a] of [[1, 0.8], [2, 0.15], [3, 0.05]]) run(new OscillatorNode(ctx, { frequency: f * k })).connect(new GainNode(ctx, { gain: a })).connect(vol);
      vol.connect(out);
      sway(vol.gain, 0.13, g * 0.35);
      break;
    }
    case "drips": every((t) => blip(ctx, into, t, "sine", 1200 + 500 * r(), 600, 0.09, 1)); break;
    case "birds": every((t) => { const hi = 2300 + 900 * r(); [0, 0.13, 0.26].forEach((d, i) => blip(ctx, into, t + d, "sine", hi * (i % 2 ? 1.25 : 1), hi * (i % 2 ? 1 : 1.25), 0.1, 1)); }); break;
    case "creak": every((t) => { const lo = 60 + 40 * r(); blip(ctx, into, t, "sawtooth", lo, lo * (1.3 + 0.5 * r()), 0.25 + 0.3 * r(), 1, 700); }); break;
    case "crackle": every((t, n) => { const hi = L.steady ? (n % 2 ? 1500 : 2000) : 1500 + 2500 * r(); blip(ctx, into, t, "sine", hi, hi * 0.6, 0.03, L.steady ? 1 : 0.4 + 0.6 * r()); }); break;   // tick, tock
    case "crickets": every((t) => [0, 0.045, 0.09].forEach((d) => blip(ctx, into, t + d, "sine", 4300, 4300, 0.03, 1))); break;
    default: if (L.file) void load(L).then((c) => {   // a recording, going round; it may arrive after the layer was told when to stop
      if (!c || ctx.currentTime >= until) return;
      const src = run(new AudioBufferSourceNode(ctx, { buffer: seamless(c.buffer), loop: true }));
      src.connect(new GainNode(ctx, { gain: c.gain })).connect(out);
      if (until < Infinity) src.stop(until);
    });
  }
  return { out, tick: (to: number) => tick(to), stop: (at: number) => { until = at; for (const n of live) n.stop(at); } };
}

/** A pet as the voice needs it. The real words it can say: its name, the things of its own that proved useful,
 *  and once grown the names of the others in the house (VOICE.md phase 2; phase 3's described voice is not in v3). */
export function voiceInput(p: PetV, s?: Snap): VoiceInput {
  const stage = bodyStage(p), grown = stage === "adult" || stage === "elder";
  const useful = s ? s.rooms.flatMap((r) => Object.entries(r.objects ?? {})).filter(([, o]) => o.made?.by === p.id && o.made.useful).map(([name]) => name) : [];
  const others = s && grown ? s.pets.filter((q) => q.id !== p.id && q.name && q.stage !== "dead").map((q) => q.name!) : [];
  return { stage, genome: p.genome, needs: p.needs ?? { energy: 60, comfort: 60, curiosity: 60, company: 60 }, words: [p.name ?? "", ...useful, ...others].filter(Boolean) };
}

export class Voice {
  on = false;
  ambience = true;                               // the room's own sound has its own switch; it is on whenever sound is turned on
  volume = 0.8;
  heard: { at: number; what: string }[] = [];   // what has played lately, for the voice lab
  log: Logged[] = [];                            // the same for a check without ears: the last 500 sounds begun
  onchange: () => void = () => {};
  private ctx: AudioContext | null = null;
  private master!: GainNode;
  private near!: GainNode;                       // the room being looked at: full volume
  private far!: GainNode;                        // the rooms next door: quiet and muffled (§4); further off is silent
  private roof!: AudioNode;                      // the weather, as it is heard from indoors
  private talkFree = 0;                          // when the last speech ends: pets take turns, with a short gap
  private sfxFree = 0;
  private beatAt = 0;
  private breathAt = 0;
  private air: ReturnType<typeof lungs> | null = null;
  private kept = new Map<string, ReturnType<typeof ambient>>();   // what keeps going by itself: the room's layers, the weather's, things that hum
  private band: { mood: string; el: HTMLAudioElement; name: string; gain: number; here: GainNode; far: GainNode; where: string } | null = null;   // the visitor's music
  private voxAt = new Map<string, number>();     // pet -> when it last made a small sound
  private boxAt = 0;                             // when a music box left playing may go round again
  private seen: Seen | null = null;
  private power = true;
  private nextCall: Record<string, number> = {};
  private thunderAt = 0;
  private low = new Map<string, number>();       // pet -> since when it has been miserable
  private whimpered = 0;
  private last: VoiceInput | null = null;        // the voice of whoever is selected, for answering when sound is turned on
  private clips = new Map<string, Promise<AudioBuffer | null>>();   // sound files from the art data, fetched when first wanted

  constructor() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) ?? "{}");
      this.on = saved.on === true;
      if (typeof saved.volume === "number") this.volume = Math.min(1, Math.max(0, saved.volume));
    } catch { /* private window: it just starts off */ }
    // A browser plays nothing until the page has been clicked. If sound was left on, the first click starts it.
    if (this.on) for (const type of ["pointerdown", "keydown"]) addEventListener(type, () => this.on && void this.start(), { once: true, capture: true });
  }

  get live() { return this.on && this.ctx?.state === "running"; }

  private save() {
    try { localStorage.setItem(STORE, JSON.stringify({ on: this.on, volume: this.volume })); } catch { /* not remembered */ }
    this.onchange();
  }

  private start() {
    if (!this.ctx) {
      const ctx = this.ctx = new AudioContext();
      this.master = new GainNode(ctx, { gain: this.volume });
      this.master.connect(ctx.destination);
      this.near = new GainNode(ctx);
      this.near.connect(this.master);
      this.far = new GainNode(ctx, { gain: FAR });
      this.far.connect(new BiquadFilterNode(ctx, { type: "lowpass", frequency: MUFFLE })).connect(this.master);
      this.roof = new BiquadFilterNode(ctx, { type: "lowpass", frequency: 1200 });
      this.roof.connect(this.near);
      ctx.onstatechange = () => this.onchange();
    }
    return this.ctx.resume();
  }

  setOn(on: boolean) {   // called from a click, which is what lets the browser start the audio
    this.on = on;
    if (on) {   // answer at once in a pet's own voice, so it is plain that sound works even when nothing is happening
      this.ambience = true;
      void this.start().then(() => { if (this.last && this.sample("hm", this.last)) this.note("sound is on: this is its voice"); });
    } else if (this.ctx) {
      this.quiet();
      void this.ctx.suspend();
    }
    this.save();
  }

  setVolume(volume: number) {
    this.volume = Math.min(1, Math.max(0, volume));
    if (this.ctx) this.master.gain.setTargetAtTime(this.volume, this.ctx.currentTime, 0.03);
    this.save();
  }

  /** The room's own sound (SPEC-v3.3 §4). Turning it on turns sound on too: it is a click, which is what a browser wants. */
  setAmbience(on: boolean) {
    this.ambience = on;
    if (on && !this.on) return this.setOn(true);
    this.onchange();
  }

  /** Every sound begins here. It is written in the audio log, so that what played can be checked without ears, and
   *  (`said`) among what the voice lab has heard lately. The answer is whether the audio clock is running, which is
   *  whether to really play it: on a clock that stands still everything would pile up on one moment. */
  private begin(what: Logged["what"], name: string, dest: AudioNode | null, gain: number, from: { pet?: string; room?: string | null } = {}, said = "") {
    const far = dest === this.far;
    this.log.push({ t: Math.round(performance.now()), what, name, ...(from.pet ? { pet: from.pet } : {}), ...(from.room ? { room: from.room } : {}),
      where: far ? "next door" : "here", gain: Math.round(gain * (far ? FAR : 1) * 1000) / 1000 });
    if (this.log.length > 500) this.log.splice(0, this.log.length - 500);
    if (said) this.note(said);
    return this.ctx?.state === "running";
  }

  /** A sound file of the art data: an effect by our name, or a layer's own file. Null if the data has none. */
  private load = (what: string | Layer) => {
    const s = typeof what === "string" ? sound(what) : clip(what), ctx = this.ctx!;
    if (!s) return Promise.resolve(null);
    if (!this.clips.has(s.url)) this.clips.set(s.url, fetch(s.url).then((r) => r.arrayBuffer()).then((b) => ctx.decodeAudioData(b)).catch(() => null));
    return this.clips.get(s.url)!.then((buffer) => (buffer ? { buffer, gain: s.gain } : null));
  };

  /** A sound effect by our name, from the art data: quiet, under the voices. False if the data has none. */
  private sfx(name: string, dest: GainNode, said: string, what: Logged["what"] = "sfx", from: { pet?: string; room?: string | null } = {}) {
    const s = sound(name), ctx = this.ctx!;
    if (!s) return false;
    if (this.begin(what, name, dest, s.gain, from, said)) void this.load(name).then((c) => {
      if (!c || !this.live) return;
      const src = new AudioBufferSourceNode(ctx, { buffer: c.buffer });
      src.connect(new GainNode(ctx, { gain: c.gain })).connect(dest);
      src.start();
    });
    return true;
  }

  private note(what: string) {
    this.heard = [{ at: Date.now(), what }, ...this.heard].slice(0, 40);
    this.onchange();
  }

  /** Distance (SPEC-v3.3 §4), for everything that sounds: what happens in the room being looked at is heard as it is
   *  (`near`); in a room next door, through a door, it is quiet and muffled (`far`); further off it is not heard (null). */
  private bus(room: string | null, s: Snap, here: string) {
    if (room === null || room === here) return this.near;
    return Object.values(s.rooms.find((r) => r.id === here)?.doors ?? {}).includes(room) ? this.far : null;
  }

  /** Babble on the audio clock, and the real words in it through the browser's speech at the right moments. */
  private utter(plan: Plan, v: VoiceInput, dest: AudioNode, at: number, quiet: boolean) {
    const ctx = this.ctx!, end = schedule(ctx, dest, plan, at);
    if (typeof speechSynthesis === "undefined") return end;
    for (const w of plan.words ?? []) {
      const u = new SpeechSynthesisUtterance(w.word), base = voiceOf(v).base;
      u.pitch = Math.min(2, Math.max(0.3, base / 300));
      u.rate = v.stage === "elder" ? 0.8 : 1.15;
      u.volume = this.volume * (quiet ? FAR : 0.9);
      setTimeout(() => this.live && speechSynthesis.speak(u), Math.max(0, (at + w.at - ctx.currentTime) * 1000));
    }
    return end;
  }

  /** Speech takes turns: each waits for the one before, with a breath between, as two pets talking would. */
  private say(p: PetV, text: string, v: VoiceInput, dest: GainNode) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.talkFree + 0.35);
    if (at - now > 8) return;   // too far behind to still mean anything (a replay at speed)
    if (!this.begin("speech", text, dest, 0.5, { pet: p.label, room: p.room }, `${p.label}${dest === this.far ? ", next door" : ""}: “${text}”`)) return;
    this.talkFree = this.utter(planSpeech(text, v), v, dest, at, dest === this.far);
    this.sfxFree = Math.max(this.sfxFree, this.talkFree + 0.15);
  }

  /** A sound without words: queued on the audio clock behind whatever is playing, at most one a second. */
  private sound(p: PetV, kind: SoundKind, v: VoiceInput, dest: GainNode) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.sfxFree), plan = planSound(kind, v);
    if (at - now > 10 || !this.begin("vox", LABEL[kind], dest, plan.tones[0].gain, { pet: p.label, room: p.room }, `${p.label}: ${LABEL[kind]}`)) return;
    schedule(ctx, dest, plan, at);
    this.sfxFree = at + 1;
  }

  /** A song (SPEC-v3.1 §3.4), in the singer's own voice, or the music box's or a bird's. It waits its turn like
   *  speech, so two singing at once take turns. */
  private sing(name: string, title: string, notes: Note[], v: VoiceInput | "box" | "bird", dest: GainNode, room: string) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.talkFree + 0.35);
    if (at - now > 14 || !this.begin("song", title, dest, 0.42, { pet: name, room }, `${name}${dest === this.far ? ", next door" : ""} sings “${title}”`)) return;
    this.talkFree = typeof v === "string" ? tune(ctx, dest, notes, at, v === "bird") : schedule(ctx, dest, planSong(notes, v), at);
    this.sfxFree = Math.max(this.sfxFree, this.talkFree + 0.15);
  }

  /** For the Songbook: hear one version now, outside the queue. False if sound is off. */
  hear(notes: Note[], v: VoiceInput | "box" | "bird") {
    if (!this.live || !this.ctx) return false;
    const at = this.ctx.currentTime + 0.03;
    typeof v === "string" ? tune(this.ctx, this.master, notes, at, v === "bird") : schedule(this.ctx, this.master, planSong(notes, v), at);
    return true;
  }

  /** A thing humming by itself (README, instruments.hum): the data's layer, each thing on a note of its own. */
  private humOf(name: string, quiet = 1): Layer {
    const h = sounds().instruments?.hum, L: Layer = (typeof h === "string" ? sounds().sfx?.[h] : h) ?? { synth: "hum", gain: 0.04, pitch: 180 };
    return { ...L, gain: (L.gain ?? 0.04) * quiet, pitch: (L.pitch ?? 180) * (0.8 + (hash(name) % 40) / 100) };
  }

  /** For the voice lab: play one thing now, outside the queue. */
  sample(what: SoundKind | HouseSound | Creature | `vox ${VoxKind}` | "say" | "heartbeat" | "breath" | "hum" | "rain", v: VoiceInput, text = "") {
    if (!this.live || !this.ctx) return false;
    const ctx = this.ctx, at = ctx.currentTime + 0.03;
    const taste = (L: Layer) => {   // a few seconds of something that would keep going
      const k = ambient(ctx, this.master, L, this.load);
      k.tick(at + 3);
      k.out.gain.setTargetAtTime(1, at, 0.3);
      k.out.gain.setTargetAtTime(0, at + 2.6, 0.3);
      k.stop(at + 4.5);
    };
    if (what === "say") this.utter(planSpeech(text, v), v, this.master, at, false);
    else if (what === "heartbeat") [0, 0.26, 1.4, 1.66, 2.8, 3.06].forEach((t, i) => thump(ctx, this.master, at + t, i % 2 ? 0.6 : 1));
    else if (what === "breath") {
      const { noise, air } = lungs(ctx, this.master, voiceOf(v).base);
      noise.stop(breath(air, at));
    } else if (what === "hum") taste(this.humOf("sample"));
    else if (what === "rain") taste(sounds().ambience?.weather?.rain?.[0] ?? { synth: "wind", pitch: 3000, gain: 0.05 });
    else if (what.startsWith("vox ")) schedule(ctx, this.master, planVox(what.slice(4) as VoxKind, v), at);
    else if (what in HOUSE) effect(ctx, this.master, what as HouseSound, at);
    else schedule(ctx, this.master, planSound(what as SoundKind, v), at);
    return true;
  }

  /** Keep exactly these going: whatever is new fades in, whatever is no longer wanted fades out, the rest carries on. */
  private keep(want: Map<string, { L: Layer; dest: AudioNode; level: number; what: Logged["what"]; name: string; room?: string }>) {
    const ctx = this.ctx!, now = ctx.currentTime;
    for (const [key, w] of want) {
      let k = this.kept.get(key);
      if (!k) {
        this.kept.set(key, k = ambient(ctx, w.dest, w.L, this.load));
        this.begin(w.what, w.name, w.dest, (w.L.gain ?? 0.03) * w.level, { room: w.room }, w.L.says ? `${w.name} (${w.L.says})` : w.name);
      }
      k.out.gain.setTargetAtTime(w.level, now, FADE);
      k.tick(now + AHEAD);
    }
    for (const [key, k] of this.kept) {
      if (want.has(key)) continue;
      k.out.gain.setTargetAtTime(0, now, FADE);
      k.stop(now + 6 * FADE);
      this.kept.delete(key);
    }
  }

  /** The visitor's music (SPEC-v3.3 §3.1): the data's tracks for the mood, one after another and round again, as
   *  loud as the room it plays in is from here (through the whole house, it is here). A change of mood cross-fades. */
  private retune(s: Snap, here: string) {
    const ctx = this.ctx!, m = s.dj?.music, dest = m ? (m.scope === "house" ? this.near : this.bus(m.scope, s, here)) : null;
    const tracks = m && dest ? (sounds().moods?.[m.mood] ?? []).map(clip).filter((c) => !!c) : [];
    if (!m || !tracks.length) return this.hush();
    if (this.band?.mood !== m.mood) {
      this.hush();
      this.spin(m.mood, tracks, m.since % tracks.length);
    }
    const b = this.band!, where = dest === this.far ? "next door" : "here";
    if (b.where !== where) {   // a track has begun, or the room it plays in is now somewhere else from here
      b.where = where;
      this.begin("music", b.name, dest, b.gain, { room: m.scope }, `the visitor's music${dest === this.far ? ", next door" : ""}: ${b.name}`);
    }
    b.here.gain.setTargetAtTime(dest === this.near ? b.gain : 0, ctx.currentTime, FADE);
    b.far.gain.setTargetAtTime(dest === this.far ? b.gain : 0, ctx.currentTime, FADE);
  }

  private spin(mood: string, tracks: { url: string; gain: number }[], i: number) {
    const ctx = this.ctx!, t = tracks[i % tracks.length], el = new Audio(t.url), src = ctx.createMediaElementSource(el);
    const send = (to: AudioNode) => { const g = new GainNode(ctx, { gain: 0 }); src.connect(g).connect(to); return g; };
    const b = this.band = { mood, el, gain: t.gain, here: send(this.near), far: send(this.far), where: "", name: `${mood}: ${decodeURI(t.url).split("/").pop()!.replace(/\.\w+$/, "")}` };
    el.onended = () => { if (this.band === b) { this.hush(); this.spin(mood, tracks, i + 1); } };   // the next update lets it be heard, and says so
    void el.play().catch(() => {});
  }

  private hush() {
    const b = this.band;
    if (!b) return;
    this.band = null;
    for (const g of [b.here, b.far]) g.gain.setTargetAtTime(0, this.ctx!.currentTime, FADE);
    setTimeout(() => b.el.pause(), 5000 * FADE);
  }

  private quiet() {   // stop everything that keeps going by itself
    const now = this.ctx!.currentTime;
    this.beatAt = this.breathAt = 0;
    this.air?.air.gain.cancelScheduledValues(now);
    this.air?.air.gain.setTargetAtTime(0, now, 0.1);
    if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    this.hush();
    this.keep(new Map());
  }

  /** Called with every snapshot that reaches the screen, live or replayed, sound on or off (so that turning sound
   *  on later does not replay old news). `here` is the room being looked at; `sel` the pet the drawer is on. */
  update(s: Snap, here: string, sel: string | null) {
    const t = news(this.seen, s), ctx = this.ctx, was = this.power;
    this.seen = t.seen;
    this.power = s.power;
    const pets = new Map(s.pets.map((p) => [p.id, p]));
    const chosen = pets.get(sel ?? "") ?? s.pets.find((p) => p.room === here && p.stage !== "dead" && p.stage !== "egg");
    this.last = chosen ? voiceInput(chosen, s) : this.last;
    const inRoom = s.pets.filter((p) => p.room === here), awake = inRoom.filter((p) => p.needs && !p.asleep);
    for (const p of awake) (p.levels?.comfort === 4) ? this.low.set(p.id, this.low.get(p.id) ?? Date.now()) : this.low.delete(p.id);
    const room = s.rooms.find((r) => r.id === here);
    if (!this.on || !ctx) return;
    const now = ctx.currentTime, label = (id: string) => pets.get(id)?.label ?? "someone";
    this.retune(s, here);

    const tools = sounds().instruments ?? {};
    for (const a of t.acts) {   // a step just finished, each heard once
      const dest = this.bus(a.room, s, here), o = s.rooms.find((r) => r.id === a.room)?.objects[(a.what ?? "").toLowerCase().replace(/^(the|my|your|an?) /, "")], used = a.type === "use" || a.type === "fiddle";
      // SPEC-v3.3 §4: a thing that sounds, sounded: its own sound by its kind or (a fixture) its name, from wherever it is
      const loud = a.loud || (used && !!(o?.made?.loud || o?.fix?.loud));
      const rings = [inventedSound(a.kind ?? o?.made?.recipe.kind), a.kind ?? o?.made?.recipe.kind, a.what, loud ? "default" : null].map((k) => (k ? tools[k] : null)).find((x) => typeof x === "string");   // (an invented thing sounds like its loudest part)
      if (dest && rings && (loud || used)) this.sfx(rings, dest, `${label(a.pet)} sounds the ${a.what}`, "instrument", { pet: label(a.pet), room: a.room });
      else if (dest === this.near) {   // SPEC-v3.2 §8: the small sounds of a step, in this room only
        const fix = o?.fix, name = a.type === "use" ? (fix && "meal" in fix ? "eat" : "") : SFX[a.type];
        if (name) this.sfx(name, dest, `${name} (${label(a.pet)})`, "sfx", { pet: label(a.pet), room: a.room });
      }
    }

    for (const say of t.speak) {
      const p = pets.get(say.pet), dest = p && this.bus(p.room, s, here);
      if (p && dest) this.say(p, say.text, voiceInput(p, s), dest);
    }
    for (const x of t.vox) {   // SPEC-v3.3 §4: the small sounds a pet makes by itself, no more than one every couple of seconds from each
      const p = pets.get(x.pet), dest = p && this.bus(x.room, s, here), plan = p && planVox(x.kind, voiceInput(p, s));
      if (!p || !dest || !plan || performance.now() - (this.voxAt.get(p.id) ?? -1e9) < 2000) continue;
      this.voxAt.set(p.id, performance.now());
      if (this.begin("vox", x.kind, dest, plan.tones[0].gain, { pet: p.label, room: x.room }, `${p.label}${dest === this.far ? ", next door" : ""}: ${x.kind}`)) schedule(ctx, dest, plan, now + 0.05);
    }
    for (const m of t.sounds) {
      const p = pets.get(m.pet), dest = p && this.bus(m.room ?? p.room, s, here);
      if (p && dest) this.sound(p, m.kind, voiceInput(p, s), dest);
    }
    for (const x of t.sing) {   // SPEC-v3.1 §3.4: whoever sang, in their own voice, as loud as their room is from here
      const song = s.songs?.[x.song], p = pets.get(x.by), dest = song && this.bus(x.room, s, here);
      const beast = s.creatures.find((c) => c.id === x.by), who = p?.label ?? (x.by === "music box" ? "the music box" : beast?.name ?? `a ${beast?.kind ?? "bird"}`);
      if (dest) this.sing(who, song!.name, song!.notes, p ? voiceInput(p, s) : x.by === "music box" ? "box" : "bird", dest, x.room);
    }
    // a music box left playing plays (12 October 2026: it showed notes and made no sound): the house's own box tune,
    // round again after a pause, as loud as its room is from here
    const playing = performance.now() < this.boxAt ? undefined : s.rooms.find((r) => Object.values(r.objects ?? {}).some((o) => o.state === "playing") && this.bus(r.id, s, here));
    if (playing) {
      const song = Object.values(s.songs ?? {}).find((x) => x.by === "music box");
      this.sing("the music box", song?.name ?? "the music box's tune", song?.notes ?? BOX_TUNE, "box", this.bus(playing.id, s, here)!, playing.id);
      this.boxAt = performance.now() + 12000;
    }
    const house = (kind: HouseSound | Creature, dest: GainNode, room?: string | null) => { if (this.begin("sfx", kind, dest, 1, { room }, HOUSE[kind])) effect(ctx, dest, kind, now + 0.05); };
    for (const h of t.house.filter((h) => h.kind !== "powerdown")) {   // weather and events have sounds of their own
      // a discovery (SPEC-v3.1 §1) is heard all through the house: the pack's jingle for it if the data has one, else the sound made here
      const found = h.moment.startsWith("arrival ") ? h.moment.slice(8) : null;
      if (found && (this.sfx(`arrival.${found}`, this.near, `${found} has come`) || this.sfx("arrival", this.near, `${found} has come`))) continue;
      const dest = found || h.kind === "thunder" ? this.near : this.bus(h.room, s, here);
      if (dest) house(h.kind, dest, h.room);
    }
    if (was !== s.power) house(s.power ? "powerup" : "powerdown", this.near);
    for (const [id, since] of this.low) {   // at most one whimper every 5 minutes, after 3 minutes of misery
      if (Date.now() - since >= 180_000 && Date.now() - this.whimpered >= 300_000 && pets.has(id)) {
        this.whimpered = Date.now();
        this.sound(pets.get(id)!, "whimper", voiceInput(pets.get(id)!, s), this.near);
      }
    }

    // ---- what keeps going by itself ----
    const want: Parameters<Voice["keep"]>[0] = new Map(), type = room?.type ?? "", called = (L: Layer) => L.synth ?? L.file?.split("/").pop()?.replace(/\.\w+$/, "") ?? "?";
    if (this.ambience && type) {   // SPEC-v3.3 §4: the room's own soundscape, and the weather over it as far as this room hears the sky
      const A = sounds().ambience, night = s.clock.phase === "night", sky = OPEN.includes(type) ? 1 : SHUT_IN.includes(type) ? 0 : 0.4;
      for (const L of A?.rooms?.[type] ?? []) if (!L.when || (L.when === "night") === night) want.set(`${type}|${JSON.stringify(L)}`, { L, dest: this.near, level: 1, what: "ambience", name: `${type}: ${called(L)}`, room: here });
      for (const L of sky ? A?.weather?.[s.weather] ?? [] : []) want.set(`${sky}|${JSON.stringify(L)}`, { L, dest: sky < 1 ? this.roof : this.near, level: sky, what: "ambience", name: `${s.weather}: ${called(L)}`, room: here });
    }
    for (const r of s.rooms) {   // a thing humming by itself, from where it is (the radio is a real station now: hub.ts plays it)
      const dest = r.type ? this.bus(r.id, s, here) : null;
      for (const [name, o] of dest ? Object.entries(r.objects) : []) {
        if (o.made && (o.made.hums ?? (o.made.active && o.made.behavior?.do === "hum")))
          want.set(`hum|${r.id}|${name}|${dest === this.far}`, { L: this.humOf(name), dest: dest!, level: 1, what: "instrument", name: `hum: ${name}`, room: r.id });
      }
    }
    this.keep(want);

    if (inRoom.some((p) => p.stage === "egg")) {   // an egg: a faint slow heartbeat, a little faster while someone is watching
      if (!this.beatAt) this.begin("sfx", "heartbeat", this.near, 0.35, { room: here }, "heartbeat (an egg)");
      for (this.beatAt = Math.max(this.beatAt, now + 0.1); this.beatAt < now + AHEAD; this.beatAt += s.visitor === here ? 0.9 : 1.4) {
        thump(ctx, this.near, this.beatAt, 0.7);
        thump(ctx, this.near, this.beatAt + 0.26, 0.42);
      }
    } else this.beatAt = 0;

    const sleeper = inRoom.find((p) => p.asleep);
    if (sleeper) {   // slow, quiet breathing, at the sleeper's own pitch
      this.air ??= lungs(ctx, this.master, voiceOf(voiceInput(sleeper)).base);
      if (!this.breathAt) this.begin("sfx", "breathing", this.near, 0.2, { pet: sleeper.label, room: here }, `${sleeper.label} breathing, asleep`);
      for (this.breathAt = Math.max(this.breathAt, now + 0.1); this.breathAt < now + AHEAD;) this.breathAt = breath(this.air.air, this.breathAt);
    } else if (this.breathAt) {
      this.air!.air.gain.cancelScheduledValues(now);
      this.air!.air.gain.setTargetAtTime(0, now, 0.2);
      this.breathAt = 0;
      this.air!.noise.stop(now + 1);
      this.air = null;
    }

    if (s.weather === "storm" && now >= this.thunderAt) {
      if (this.thunderAt) house("thunder", this.near);
      this.thunderAt = now + 14 + (hash(String(s.tick)) % 16);
    } else if (s.weather !== "storm") this.thunderAt = 0;

    for (const c of s.creatures.filter((c) => c.room === here)) {   // small creatures make small sounds now and then
      const kind = c.kind as Creature, singing = c.doing.startsWith("singing");
      if (now < (this.nextCall[kind] ?? 0) || /asleep/.test(c.doing)) continue;
      if (this.nextCall[kind] !== undefined) house(kind, this.near, here);
      this.nextCall[kind] = now + (singing ? 4 : 9) + (hash(c.id + s.tick) % 6);
    }
  }
}
