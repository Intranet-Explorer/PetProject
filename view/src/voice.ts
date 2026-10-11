// The house's sound (VOICE.md, SPEC-v3 §10.6). Web Audio only: no libraries, no audio files; from youngling on, a
// word a pet really knows is said with the browser's own speech voice, pitched to its body.
// View-only: it listens to what the view already receives and nothing here goes back to the engine.
import { hash, news, planSong, planSound, planSpeech, semitone, voiceOf } from "./voice-plan";
import type { HouseSound, Plan, Seen, SoundKind, VoiceInput } from "./voice-plan";
import { sound } from "./sprite";
import { bodyStage } from "./types";
import type { Heard, Note, PetV, Snap } from "./types";

const STORE = "sound";
const AHEAD = 6;   // seconds of heartbeat or breathing kept scheduled on the audio clock; a snapshot tops it up every 2 s
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
  combine: "combine", go: "door", eat: "eat", write: "write", scrub: "write", ask_book: "book", call: "call", nuzzle: "heart" };
const WET = ["rain", "storm"], OPEN = ["garden", "greenhouse", "attic", "pond"], SHUT_IN = ["cellar", "storeroom"];

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

/** A taught thing's hum: a low filtered sawtooth, which no pet's voice ever is, pitched by the thing's name. */
function drone(ctx: BaseAudioContext, dest: AudioNode, name: string) {
  const osc = new OscillatorNode(ctx, { type: "sawtooth", frequency: 110 + (hash(name) % 80) }), gain = new GainNode(ctx, { gain: 0 });
  const sway = new OscillatorNode(ctx, { frequency: 0.6 }), depth = new GainNode(ctx, { gain: 0.012 });
  sway.connect(depth).connect(gain.gain);
  osc.connect(new BiquadFilterNode(ctx, { type: "lowpass", frequency: 480 })).connect(gain).connect(dest);
  osc.start();
  sway.start();
  return { osc, sway, gain };
}


function hiss(ctx: BaseAudioContext, seconds = 2) {   // white noise, the stuff of rain, wind, wings and thunder
  const buffer = new AudioBuffer({ length: Math.ceil(ctx.sampleRate * seconds), sampleRate: ctx.sampleRate }), data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  return buffer;
}

/** A sound of the house or of a small creature: none of them is anyone's voice. Returns when it ends. */
export function effect(ctx: BaseAudioContext, dest: AudioNode, kind: HouseSound | Creature, at: number) {
  const tone = (type: OscillatorType, f0: number, f1: number, t: number, dur: number, gain: number, cutoff = 6000) => {
    const osc = new OscillatorNode(ctx, { type, frequency: f0 }), env = new GainNode(ctx, { gain: 0 });
    osc.frequency.setValueAtTime(f0, at + t);
    osc.frequency.exponentialRampToValueAtTime(f1, at + t + dur);
    env.gain.setValueAtTime(0, at + t);
    env.gain.linearRampToValueAtTime(gain, at + t + Math.min(0.02, dur / 3));
    env.gain.exponentialRampToValueAtTime(0.001, at + t + dur);
    osc.connect(new BiquadFilterNode(ctx, { type: "lowpass", frequency: cutoff })).connect(env).connect(dest);
    osc.start(at + t);
    osc.stop(at + t + dur + 0.05);
    return t + dur;
  };
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

/** An old radio's crackle (SPEC-v3.1 §5.3): the same noise as the rain, through a narrow band, jumping about. */
function crackle(ctx: BaseAudioContext, dest: AudioNode, at: number, seconds: number, level: number) {
  const src = new AudioBufferSourceNode(ctx, { buffer: hiss(ctx, 2), loop: true }), env = new GainNode(ctx, { gain: 0 });
  for (let t = 0; t < seconds; t += 0.07) env.gain.setValueAtTime(level * (0.25 + Math.random() ** 3), at + t);
  env.gain.setValueAtTime(0, at + seconds);
  src.connect(new BiquadFilterNode(ctx, { type: "bandpass", frequency: 1900, Q: 0.7 })).connect(env).connect(dest);
  src.start(at);
  src.stop(at + seconds + 0.05);
  return at + seconds;
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
  music = false;                                 // a quiet tune for the room being looked at: its own switch, off unless turned on
  volume = 0.8;
  heard: { at: number; what: string }[] = [];   // what has played lately, for the voice lab
  onchange: () => void = () => {};
  private ctx: AudioContext | null = null;
  private master!: GainNode;
  private near!: GainNode;                       // the room being looked at: full volume
  private far!: GainNode;                        // the rooms next door: quiet and muffled (§10.6); further off is silent
  private talkFree = 0;                          // when the last speech ends: pets take turns, with a short gap
  private sfxFree = 0;
  private beatAt = 0;
  private breathAt = 0;
  private air: ReturnType<typeof lungs> | null = null;
  private rain: { src: AudioBufferSourceNode; gain: GainNode } | null = null;
  private hums = new Map<string, ReturnType<typeof drone>>();
  private seen: Seen | null = null;
  private power = true;
  private nextCall: Record<string, number> = {};
  private thunderAt = 0;
  private low = new Map<string, number>();       // pet -> since when it has been miserable
  private whimpered = 0;
  private last: VoiceInput | null = null;        // the voice of whoever is selected, for answering when sound is turned on
  private clips = new Map<string, Promise<AudioBuffer | null>>();   // sound effects from the art data, fetched when first wanted
  private band: { el: HTMLAudioElement; url: string; gain: number } | null = null;
  private roomType: string | null = null;

  constructor() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) ?? "{}");
      this.on = saved.on === true;
      this.music = saved.music === true;
      if (typeof saved.volume === "number") this.volume = Math.min(1, Math.max(0, saved.volume));
    } catch { /* private window: it just starts off */ }
    // A browser plays nothing until the page has been clicked. If sound was left on, the first click starts it.
    if (this.on) for (const type of ["pointerdown", "keydown"]) addEventListener(type, () => this.on && void this.start(), { once: true, capture: true });
  }

  get live() { return this.on && this.ctx?.state === "running"; }

  private save() {
    try { localStorage.setItem(STORE, JSON.stringify({ on: this.on, volume: this.volume, music: this.music })); } catch { /* not remembered */ }
    this.onchange();
  }

  private start() {
    if (!this.ctx) {
      const ctx = this.ctx = new AudioContext();
      this.master = new GainNode(ctx, { gain: this.volume });
      this.master.connect(ctx.destination);
      this.near = new GainNode(ctx);
      this.near.connect(this.master);
      this.far = new GainNode(ctx, { gain: 0.22 });
      this.far.connect(new BiquadFilterNode(ctx, { type: "lowpass", frequency: 700 })).connect(this.master);
      ctx.onstatechange = () => this.onchange();
    }
    return this.ctx.resume();
  }

  setOn(on: boolean) {   // called from a click, which is what lets the browser start the audio
    this.on = on;
    if (on) {   // answer at once in a pet's own voice, so it is plain that sound works even when nothing is happening
      void this.start().then(() => {
        if (this.last && this.sample("hm", this.last)) this.note("sound is on: this is its voice");
        this.retune();
      });
    } else if (this.ctx) {
      this.quiet();
      void this.ctx.suspend();
    }
    this.save();
  }

  setVolume(volume: number) {
    this.volume = Math.min(1, Math.max(0, volume));
    if (this.ctx) this.master.gain.setTargetAtTime(this.volume, this.ctx.currentTime, 0.03);
    if (this.band) this.band.el.volume = this.band.gain * this.volume;
    this.save();
  }

  /** Music (SPEC-v3.2 §8) has its own switch. Turning it on turns sound on too: it is a click, which is what a browser wants. */
  setMusic(on: boolean) {
    this.music = on;
    if (on && !this.live) return this.setOn(true);
    this.retune();
    this.save();
  }

  /** Keep the right tune going, very quietly: the one the art data gives for the kind of room being looked at, or none. */
  private retune() {
    const want = this.music && this.live && this.roomType ? sound("music", this.roomType) : null;
    if (want?.url === this.band?.url) return;
    this.band?.el.pause();
    this.band = null;
    if (!want) return;
    const el = new Audio(want.url);
    [el.loop, el.volume] = [true, want.gain * this.volume];
    void el.play().catch(() => {});
    this.band = { el, ...want };
    this.note(`music for ${this.roomType === "pond" ? "the pond room" : `the ${this.roomType}`}, quietly`);
  }

  /** A sound effect by our name, from the art data: quiet, under the voices. False if the data has none. */
  private sfx(name: string, dest: GainNode, what: string) {
    const s = sound("sfx", name), ctx = this.ctx!;
    if (!s) return false;
    if (!this.clips.has(s.url)) this.clips.set(s.url, fetch(s.url).then((r) => r.arrayBuffer()).then((b) => ctx.decodeAudioData(b)).catch(() => null));
    void this.clips.get(s.url)!.then((buffer) => {
      if (!buffer || !this.live) return;
      const src = new AudioBufferSourceNode(ctx, { buffer });
      src.connect(new GainNode(ctx, { gain: s.gain })).connect(dest);
      src.start();
    });
    this.note(what);
    return true;
  }

  private note(what: string) {
    this.heard = [{ at: Date.now(), what }, ...this.heard].slice(0, 40);
    this.onchange();
  }

  /** Where a sound from this room should go: here, next door, or nowhere. */
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
      u.volume = this.volume * (quiet ? 0.2 : 0.9);
      setTimeout(() => this.live && speechSynthesis.speak(u), Math.max(0, (at + w.at - ctx.currentTime) * 1000));
    }
    return end;
  }

  /** Speech takes turns: each waits for the one before, with a breath between, as two pets talking would. */
  private say(name: string, text: string, v: VoiceInput, dest: GainNode) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.talkFree + 0.35);
    if (at - now > 8) return;   // too far behind to still mean anything (a replay at speed)
    this.talkFree = this.utter(planSpeech(text, v), v, dest, at, dest === this.far);
    this.sfxFree = Math.max(this.sfxFree, this.talkFree + 0.15);
    this.note(`${name}${dest === this.far ? ", next door" : ""}: “${text}”`);
  }

  /** A sound without words: queued on the audio clock behind whatever is playing, at most one a second. */
  private sound(name: string, kind: SoundKind, v: VoiceInput, dest: GainNode) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.sfxFree);
    if (at - now > 10) return;
    schedule(ctx, dest, planSound(kind, v), at);
    this.sfxFree = at + 1;
    this.note(`${name}: ${LABEL[kind]}`);
  }

  /** A song (SPEC-v3.1 §3.4), in the singer's own voice, or the music box's or a bird's. It waits its turn like
   *  speech, so two singing at once take turns. */
  private sing(name: string, title: string, notes: Note[], v: VoiceInput | "box" | "bird", dest: GainNode) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.talkFree + 0.35);
    if (at - now > 14) return;
    this.talkFree = typeof v === "string" ? tune(ctx, dest, notes, at, v === "bird") : schedule(ctx, dest, planSong(notes, v), at);
    this.sfxFree = Math.max(this.sfxFree, this.talkFree + 0.15);
    this.note(`${name}${dest === this.far ? ", next door" : ""} sings “${title}”`);
  }

  /** For the Songbook: hear one version now, outside the queue. False if sound is off. */
  hear(notes: Note[], v: VoiceInput | "box" | "bird") {
    if (!this.live || !this.ctx) return false;
    const at = this.ctx.currentTime + 0.03;
    typeof v === "string" ? tune(this.ctx, this.master, notes, at, v === "bird") : schedule(this.ctx, this.master, planSong(notes, v), at);
    return true;
  }

  /** The box speaks (SPEC-v3.1 §5.3): quietly, in the browser's own voice made slow and low, under a crackle. Next
   *  door it is only the crackle, muffled. Nothing to say is static. */
  private wireless(h: Heard, dest: GainNode) {
    const ctx = this.ctx!, at = ctx.currentTime + 0.05, words = dest === this.near && h.text && typeof speechSynthesis !== "undefined";
    if (dest === this.near && h.text) this.sfx("radio", dest, "the box clicks");   // the pack's own sound for the box, if the data has one
    crackle(ctx, dest, at, h.text ? Math.min(14, 0.6 + h.text.length * 0.07) : 1.8, h.text ? 0.035 : 0.12);
    if (words) {
      const u = new SpeechSynthesisUtterance(h.text);
      [u.rate, u.pitch, u.volume] = [0.9, 0.7, this.volume * 0.35];
      speechSynthesis.speak(u);
    }
    this.note(h.text ? `the box${words ? "" : ", next door"}: “${h.text}”` : "static from the box");
  }

  /** For the voice lab: play one thing now, outside the queue. */
  sample(what: SoundKind | HouseSound | Creature | "say" | "heartbeat" | "breath" | "hum" | "rain", v: VoiceInput, text = "") {
    if (!this.live || !this.ctx) return false;
    const ctx = this.ctx, at = ctx.currentTime + 0.03;
    if (what === "say") this.utter(planSpeech(text, v), v, this.master, at, false);
    else if (what === "heartbeat") [0, 0.26, 1.4, 1.66, 2.8, 3.06].forEach((t, i) => thump(ctx, this.master, at + t, i % 2 ? 0.6 : 1));
    else if (what === "breath") {
      const { noise, air } = lungs(ctx, this.master, voiceOf(v).base);
      noise.stop(breath(air, at));
    } else if (what === "hum") {
      const { osc, sway, gain } = drone(ctx, this.master, "sample");
      gain.gain.setTargetAtTime(0.03, at, 0.3);
      gain.gain.setTargetAtTime(0, at + 2.2, 0.3);
      osc.stop(at + 3.5);
      sway.stop(at + 3.5);
    } else if (what === "rain") {
      const r = this.rainNode(ctx);
      r.gain.gain.setTargetAtTime(0.06, at, 0.3);
      r.gain.gain.setTargetAtTime(0, at + 3, 0.4);
    } else if (what in HOUSE) effect(ctx, this.master, what as HouseSound, at);
    else schedule(ctx, this.master, planSound(what as SoundKind, v), at);
    return true;
  }

  private rainNode(ctx: AudioContext) {
    if (!this.rain) {
      const src = new AudioBufferSourceNode(ctx, { buffer: hiss(ctx, 3), loop: true }), gain = new GainNode(ctx, { gain: 0 });
      src.connect(new BiquadFilterNode(ctx, { type: "highpass", frequency: 1800 })).connect(gain).connect(this.master);
      src.start();
      this.rain = { src, gain };
    }
    return this.rain;
  }

  private quiet() {   // stop everything that keeps going by itself
    const now = this.ctx!.currentTime;
    this.beatAt = this.breathAt = 0;
    this.air?.air.gain.cancelScheduledValues(now);
    this.air?.air.gain.setTargetAtTime(0, now, 0.1);
    this.rain?.gain.gain.setTargetAtTime(0, now, 0.1);
    if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
    this.band?.el.pause();
    this.band = null;
    for (const [name, h] of this.hums) {
      h.gain.gain.setTargetAtTime(0, now, 0.2);
      h.osc.stop(now + 1.5);
      h.sway.stop(now + 1.5);
      this.hums.delete(name);
    }
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
    this.roomType = room?.type ?? null;
    if (!this.live || !ctx) return;
    const now = ctx.currentTime;
    this.retune();
    for (const a of t.acts.filter((a) => a.room === here)) {   // SPEC-v3.2 §8: a step just finished in this room, each heard once
      const fix = room?.objects[a.what ?? ""]?.fix, name = a.type === "use" ? (fix && "meal" in fix ? "eat" : "") : SFX[a.type];
      if (name) this.sfx(name, this.near, `${name} (${pets.get(a.pet)?.label ?? "someone"})`);
    }

    for (const say of t.speak) {
      const p = pets.get(say.pet), dest = p && this.bus(p.room, s, here);
      if (p && dest) this.say(p.label, say.text, voiceInput(p, s), dest);
    }
    for (const m of t.sounds) {
      const p = pets.get(m.pet), dest = p && this.bus(m.room ?? p.room, s, here);
      if (p && dest) this.sound(p.label, m.kind, voiceInput(p, s), dest);
    }
    for (const x of t.sing) {   // SPEC-v3.1 §3.4: whoever sang, in their own voice, as loud as their room is from here
      const song = s.songs?.[x.song], p = pets.get(x.by), dest = song && this.bus(x.room, s, here);
      const beast = s.creatures.find((c) => c.id === x.by), who = p?.label ?? (x.by === "music box" ? "the music box" : beast?.name ?? `a ${beast?.kind ?? "bird"}`);
      if (dest) this.sing(who, song!.name, song!.notes, p ? voiceInput(p, s) : x.by === "music box" ? "box" : "bird", dest);
    }
    for (const h of t.heard) {
      const dest = this.bus(h.room, s, here);
      if (dest) this.wireless(h, dest);
    }
    for (const h of t.house.filter((h) => h.kind !== "powerdown")) {   // weather and events have sounds of their own
      // a discovery (SPEC-v3.1 §1) is heard all through the house: the pack's jingle for it if the data has one, else the sound made here
      const found = h.moment.startsWith("arrival ") ? h.moment.slice(8) : null;
      if (found && (this.sfx(`arrival.${found}`, this.near, `${found} has come`) || this.sfx("arrival", this.near, `${found} has come`))) continue;
      const dest = found || h.kind === "thunder" ? this.near : this.bus(h.room, s, here);
      if (dest) { effect(ctx, dest, h.kind, now + 0.05); this.note(HOUSE[h.kind]); }
    }
    if (was !== s.power) { effect(ctx, this.near, s.power ? "powerup" : "powerdown", now + 0.05); this.note(HOUSE[s.power ? "powerup" : "powerdown"]); }
    for (const [id, since] of this.low) {   // at most one whimper every 5 minutes, after 3 minutes of misery
      if (Date.now() - since >= 180_000 && Date.now() - this.whimpered >= 300_000 && pets.has(id)) {
        this.whimpered = Date.now();
        this.sound(pets.get(id)!.label, "whimper", voiceInput(pets.get(id)!, s), this.near);
      }
    }

    // ---- what keeps going by itself in the room being looked at ----
    if (inRoom.some((p) => p.stage === "egg")) {   // an egg: a faint slow heartbeat, a little faster while someone is watching
      if (!this.beatAt) this.note("heartbeat (an egg)");
      for (this.beatAt = Math.max(this.beatAt, now + 0.1); this.beatAt < now + AHEAD; this.beatAt += s.visitor === here ? 0.9 : 1.4) {
        thump(ctx, this.near, this.beatAt, 0.7);
        thump(ctx, this.near, this.beatAt + 0.26, 0.42);
      }
    } else this.beatAt = 0;

    const sleeper = inRoom.find((p) => p.asleep);
    if (sleeper) {   // slow, quiet breathing, at the sleeper's own pitch
      this.air ??= lungs(ctx, this.master, voiceOf(voiceInput(sleeper)).base);
      if (!this.breathAt) this.note(`${sleeper.label} breathing, asleep`);
      for (this.breathAt = Math.max(this.breathAt, now + 0.1); this.breathAt < now + AHEAD;) this.breathAt = breath(this.air.air, this.breathAt);
    } else if (this.breathAt) {
      this.air!.air.gain.cancelScheduledValues(now);
      this.air!.air.gain.setTargetAtTime(0, now, 0.2);
      this.breathAt = 0;
      this.air!.noise.stop(now + 1);
      this.air = null;
    }

    const wet = WET.includes(s.weather) ? (OPEN.includes(room?.type ?? "") ? 0.07 : SHUT_IN.includes(room?.type ?? "") ? 0 : 0.03) : 0;
    if (wet || this.rain) this.rainNode(ctx).gain.gain.setTargetAtTime(wet, now, 0.8);   // rain on the glass, loud under open sky, absent underground
    if (s.weather === "storm" && now >= this.thunderAt) {
      if (this.thunderAt) { effect(ctx, this.near, "thunder", now + 0.1); this.note(HOUSE.thunder); }
      this.thunderAt = now + 14 + (hash(String(s.tick)) % 16);
    } else if (s.weather !== "storm") this.thunderAt = 0;

    for (const c of s.creatures.filter((c) => c.room === here)) {   // small creatures make small sounds now and then
      const kind = c.kind as Creature, singing = c.doing.startsWith("singing");
      if (now < (this.nextCall[kind] ?? 0) || /asleep/.test(c.doing)) continue;
      if (this.nextCall[kind] !== undefined) { effect(ctx, this.near, kind, now + 0.05); this.note(HOUSE[kind]); }
      this.nextCall[kind] = now + (singing ? 4 : 9) + (hash(c.id + s.tick) % 6);
    }

    // a thing taught to hum has its own sound, not a pet's; so has the box while it is on, between the things it says
    const humming = Object.entries(room?.objects ?? {}).filter(([, o]) => (o.made?.active && o.made.behavior?.do === "hum") || (o.fix?.radio && o.state === "on")).map(([name]) => name);
    for (const name of humming) {
      if (this.hums.has(name)) continue;
      const h = drone(ctx, this.near, name);
      const box = !!room?.objects[name]?.fix?.radio;
      h.gain.gain.setTargetAtTime(box ? 0.012 : 0.03, now, 0.5);
      this.hums.set(name, h);
      this.note(box ? "the box hums, switched on" : `a hum from the ${name} (it was taught to)`);
    }
    for (const [name, h] of this.hums) {
      if (humming.includes(name)) continue;
      h.gain.gain.setTargetAtTime(0, now, 0.3);
      h.osc.stop(now + 2);
      h.sway.stop(now + 2);
      this.hums.delete(name);
    }
  }
}
