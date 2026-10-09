// The pet's voice, as sound (VOICE.md, Phase 1). Web Audio only: no libraries, no audio files.
// View-only: it listens to what the view already receives and nothing here goes back to the engine.
import { hash, planSound, planSpeech, triggers, voiceOf } from "./voice-plan";
import type { Catalog, Heard, Plan, Seen, SoundKind, Step, VoiceInput } from "./voice-plan";

const STORE = "sound";
const AHEAD = 6;   // seconds of heartbeat or breathing kept scheduled on the audio clock; a snapshot tops it up every 2 s
const LABEL: Record<SoundKind, string> = {
  cry: "first cry (it hatched)", chirp: "chirp (it made a thing)", blip: "falling blip (it took a thing apart)",
  trill: "content trill (it used a thing that helped)", stageup: "three rising notes (a new stage)",
  hm: "“hm?” (you spoke to it or poked it)", whimper: "whimper (comfort has been low a long while)",
};

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

function breath(air: GainNode, at: number) {   // in for a second and a half, out for two and a half, very quiet
  air.gain.setValueAtTime(0, at);
  air.gain.linearRampToValueAtTime(0.05, at + 1.5);
  air.gain.linearRampToValueAtTime(0.004, at + 2.1);
  air.gain.linearRampToValueAtTime(0.034, at + 2.8);
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

export class Voice {
  on = false;
  volume = 0.6;
  heard: { at: number; what: string }[] = [];   // what has played lately, for the voice lab
  onchange: () => void = () => {};
  private ctx: AudioContext | null = null;
  private master!: GainNode;
  private sfx!: GainNode;                        // sounds without words, so speech can cut off the ones still queued
  private speechEnd = 0;
  private sfxFree = 0;
  private beatAt = 0;
  private breathAt = 0;
  private air: ReturnType<typeof lungs> | null = null;
  private hums = new Map<string, ReturnType<typeof drone>>();
  private seen: Seen | null = null;
  private lowSince = 0;
  private whimpered = 0;

  constructor() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) ?? "{}");
      this.on = saved.on === true;
      if (typeof saved.volume === "number") this.volume = Math.min(1, Math.max(0, saved.volume));
    } catch { /* private window: it just starts off */ }
    // A browser plays nothing until the page has been clicked. If sound was left on, the first click starts it.
    if (this.on) for (const type of ["pointerdown", "keydown"]) addEventListener(type, () => this.on && this.start(), { once: true, capture: true });
  }

  get live() { return this.on && this.ctx?.state === "running"; }

  private save() {
    try { localStorage.setItem(STORE, JSON.stringify({ on: this.on, volume: this.volume })); } catch { /* not remembered */ }
    this.onchange();
  }

  private start() {
    if (!this.ctx) {
      this.ctx = new AudioContext();
      this.master = new GainNode(this.ctx, { gain: this.volume });
      this.master.connect(this.ctx.destination);
      this.sfx = new GainNode(this.ctx);
      this.sfx.connect(this.master);
      this.ctx.onstatechange = () => this.onchange();
    }
    void this.ctx.resume();
  }

  setOn(on: boolean) {   // called from a click, which is what lets the browser start the audio
    this.on = on;
    if (on) this.start();
    else if (this.ctx) {
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

  private note(what: string) {
    this.heard = [{ at: Date.now(), what }, ...this.heard].slice(0, 40);
    this.onchange();
  }

  /** Speech always plays, and cuts off any wordless sounds still waiting their turn. */
  say(text: string, v: VoiceInput) {
    if (!this.live || !this.ctx) return;
    const now = this.ctx.currentTime;
    this.sfx.gain.setTargetAtTime(0, now, 0.01);
    this.sfx = new GainNode(this.ctx);
    this.sfx.connect(this.master);
    this.speechEnd = schedule(this.ctx, this.master, planSpeech(text, v), now + 0.03);
    this.sfxFree = this.speechEnd + 0.15;
    this.note(`speech: “${text}”`);
  }

  /** A sound without words: at most one every 2 seconds, queued on the audio clock behind whatever is playing. */
  sound(kind: SoundKind, v: VoiceInput) {
    if (!this.live || !this.ctx) return;
    const now = this.ctx.currentTime, at = Math.max(now + 0.03, this.sfxFree);
    if (at - now > 12) return;   // too far behind to still mean anything
    schedule(this.ctx, this.sfx, planSound(kind, v), at);
    this.sfxFree = at + 2;
    this.note(LABEL[kind]);
  }

  /** For the voice lab: play one thing now, outside the queue. */
  sample(what: SoundKind | "say" | "heartbeat" | "breath" | "hum", v: VoiceInput, text = "") {
    if (!this.live || !this.ctx) return false;
    const ctx = this.ctx, at = ctx.currentTime + 0.03;
    if (what === "say") schedule(ctx, this.master, planSpeech(text, v), at);
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
    } else schedule(ctx, this.master, planSound(what, v), at);
    return true;
  }

  private quiet() {   // stop everything that keeps going by itself
    const now = this.ctx!.currentTime;
    this.beatAt = this.breathAt = 0;
    this.air?.air.gain.cancelScheduledValues(now);
    this.air?.air.gain.setTargetAtTime(0, now, 0.1);
    for (const [name, h] of this.hums) {
      h.gain.gain.setTargetAtTime(0, now, 0.2);
      h.osc.stop(now + 1.5);
      h.sway.stop(now + 1.5);
      this.hums.delete(name);
    }
  }

  /** Called with every snapshot, sound on or off, so that turning sound on later does not replay old news. */
  update(world: Heard & { pet: Heard["pet"] & VoiceInput }, journal: Step[], things: Catalog, visitor: boolean) {
    const v: VoiceInput = { stage: world.pet.stage, genome: world.pet.genome, needs: world.pet.needs, trend: world.pet.trend };
    const t = triggers(this.seen, world, journal, things), ctx = this.ctx;
    this.seen = t.seen;
    const low = v.needs.comfort < 20 && !t.ambient.asleep && !t.ambient.egg;
    this.lowSince = low ? this.lowSince || Date.now() : 0;
    if (!this.live || !ctx) return;

    if (t.speak) this.say(t.speak, v);
    for (const kind of t.sounds) this.sound(kind, v);
    if (low && Date.now() - this.lowSince >= 180_000 && Date.now() - this.whimpered >= 300_000) {   // at most one every 5 minutes
      this.whimpered = Date.now();
      this.sound("whimper", v);
    }

    const now = ctx.currentTime;
    if (t.ambient.egg) {   // a faint slow heartbeat, a little faster while a visitor is there
      if (!this.beatAt) this.note("heartbeat (it is an egg)");
      for (this.beatAt = Math.max(this.beatAt, now + 0.1); this.beatAt < now + AHEAD; this.beatAt += visitor ? 0.9 : 1.4) {
        thump(ctx, this.master, this.beatAt, 0.7);
        thump(ctx, this.master, this.beatAt + 0.26, 0.42);
      }
    } else this.beatAt = 0;

    if (t.ambient.asleep) {   // slow, very quiet breathing
      this.air ??= lungs(ctx, this.master, voiceOf(v).base);
      if (!this.breathAt) this.note("breathing (it is asleep)");
      for (this.breathAt = Math.max(this.breathAt, now + 0.1); this.breathAt < now + AHEAD;) this.breathAt = breath(this.air.air, this.breathAt);
    } else if (this.breathAt) {
      this.air!.air.gain.cancelScheduledValues(now);
      this.air!.air.gain.setTargetAtTime(0, now, 0.2);
      this.breathAt = 0;
    }

    for (const name of t.ambient.hums) {   // a thing it taught to hum has its own sound, not the pet's
      if (this.hums.has(name)) continue;
      const h = drone(ctx, this.master, name);
      h.gain.gain.setTargetAtTime(0.03, now, 0.5);
      this.hums.set(name, h);
      this.note(`a hum from the ${name} (it taught it to)`);
    }
    for (const [name, h] of this.hums) {
      if (t.ambient.hums.includes(name)) continue;
      h.gain.gain.setTargetAtTime(0, now, 0.3);
      h.osc.stop(now + 2);
      h.sway.stop(now + 2);
      this.hums.delete(name);
    }
  }
}
