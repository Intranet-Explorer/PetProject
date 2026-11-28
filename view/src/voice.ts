// The house's sound (AUDIO-BRIEF §4, VOICE.md): the files of view/assets/audio, named and levelled by sounds.json,
// played with Web Audio. Music by the time of day and the mood, with rests; ambience by the room on screen, the
// weather on top; the house's events as effects; a hob's lines as babble. Only the room on screen is heard, the rooms
// next door quieter and muffled, the train faintly everywhere. Five volumes (master, music, ambience, effects,
// voices) under the one Sound switch. Files are fetched only when first wanted, and dropped once unused a while.
// The one sound still made here is a song: the hobs' tunes are their own (planSong, the music box, a bird).
// View-only: it listens to what the view already receives and nothing here goes back to the engine.
import { babble, BUSES, filesOf, Gate, gainOf, levelOf, news, planSong, rings, semitone, soundFor, voiceOf, wantAmbience, wantMusic } from "./voice-plan";
import type { Bus, Plan, Seen, Sounds, VoiceInput } from "./voice-plan";
import { inventedSound } from "./parts";
import { sounds } from "./sprite";
import { ago, bodyStage } from "./types";
import type { Note, PetV, Snap } from "./types";

const STORE = "sound", ART = "/art/";
const KEEP = 180;   // seconds a decoded file is kept after it was last used (what is going round is always kept)
/** What the page has sounded, for checking without ears (window.petView.audioLog): `t` is ms since the page loaded. */
export type Logged = { t: number; what: string; name: string; pet?: string; room?: string; where: Where; gain: number };
type Where = "here" | "next door" | "everywhere";
export type Levels = Record<"master" | Bus, number>;
type Track = { name: string; el: HTMLAudioElement; src: MediaElementAudioSourceNode; gain: GainNode; take: boolean; dj: boolean; where: Where };
type Hold = { name: string; gain: GainNode; src: AudioBufferSourceNode | null; url: string; level: number; gone: boolean };
type Want = { name: string; level: number; dest: AudioNode; what: string; room?: string; where: Where };
const S = () => sounds() as Sounds;   // (checked to be there before anything plays: update() waits for `sounds`)
const rnd = (lo: number, hi: number) => lo + (hi - lo) * Math.random();

/** Put a plan's notes on an audio clock (a song in a hob's own voice). Works on an offline context too. */
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

/** A pet as the voice needs it (its stage, its body, its needs). */
export function voiceInput(p: PetV, _s?: Snap): VoiceInput {
  return { stage: bodyStage(p), genome: p.genome, needs: p.needs ?? { energy: 60, comfort: 60, curiosity: 60, company: 60 } };
}

export class Voice {
  on = false;
  levels: Levels = { master: 0.8, music: 0.6, ambience: 0.8, effects: 0.8, voices: 0.9 };
  heard: { at: number; what: string }[] = [];   // what has played lately, for the Lab
  log: Logged[] = [];                            // the same for a check without ears: the last 500 sounds begun
  onchange: () => void = () => {};
  private ctx: AudioContext | null = null;
  private master!: GainNode;                     // the master slider
  private scale!: GainNode;                      // quieter at night, silent while the tab is hidden
  private bus = {} as Record<Bus, GainNode>;     // the four sliders under it
  private far = {} as Record<Bus, GainNode>;     // the rooms next door: quieter and muffled, into each bus
  private roof!: BiquadFilterNode;               // the weather heard through a roof, into the ambience
  private clips = new Map<string, { p: Promise<AudioBuffer | null>; used: number }>();   // decoded files, by address
  readonly missing = new Set<string>();   // SPEC-v4.0.5 §7.9: files the engine has not got (404): the Sound button says so
  private radioIn = false;                // the radio's stream goes through the music bus (once routed, always)
  private holds = new Map<string, Hold>();       // what goes round: the ambience, machines, the train, a scuffle
  private track: Track | null = null;            // the music playing (one at a time)
  private restUntil = 0;                         // performance.now() until which the music rests
  private djN = 0;                               // the visitor's music: how many tracks it has gone on by itself
  private moodUntil: Record<string, number> = {};   // grief and celebration, from the banners, until then
  private sounding = 0;                          // effects sounding now (§4.8: at most mix.effects)
  private gate = new Gate([1, 2]);
  private seen: Seen | null = null;
  private snap: Snap | null = null;
  private here = "";
  private phase = "";
  private talkFree = 0;                          // the audio clock when the last line ends: hobs take turns
  private boxAt = 0;
  private rang = -1e9;
  private thunderAt = 0;
  private greeted = false;
  private was = { body: new Map<string, string>(), mood: new Map<string, string>(), react: new Map<string, number>(), fish: new Map<string, { cast: number; bite: boolean; pulled: boolean }>(),
                  catches: 0, visitor: -1, sweep: new Map<string, number>(), blood: new Set<number>(), train: new Map<string, boolean>(), kiln: new Map<string, string>() };

  constructor() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) ?? "{}");
      this.on = saved.on === true;
      for (const k of Object.keys(this.levels) as (keyof Levels)[]) if (typeof saved[k] === "number") this.levels[k] = Math.min(1, Math.max(0, saved[k]));
      if (typeof saved.volume === "number" && saved.master == null) this.levels.master = Math.min(1, Math.max(0, saved.volume));   // (before v4.0.2: one volume)
    } catch { /* private window: it just starts off */ }
    // A browser plays nothing until the page has been clicked. If sound was left on, the first click starts it (§4.10).
    if (this.on) for (const type of ["pointerdown", "keydown"]) addEventListener(type, () => this.on && void this.start(), { once: true, capture: true });
    addEventListener("pet:thunder", () => this.thunder());   // SPEC-v3.5.9 §3: lightning in the world outside (world.ts)
    addEventListener("pet:step", (e) => this.step((e as CustomEvent<string>).detail));   // a hob's foot comes down (px/actors.ts)
    addEventListener("pet:line", (e) => this.line((e as CustomEvent<Line>).detail));     // a line of a conversation comes up (room.ts)
    document.addEventListener("visibilitychange", () => this.hidden(document.hidden));   // §4.10: silent while the tab is hidden
  }

  get live() { return this.on && this.ctx?.state === "running"; }

  private save() {
    try { localStorage.setItem(STORE, JSON.stringify({ on: this.on, ...this.levels })); } catch { /* not remembered */ }
    this.onchange();
  }

  private start() {
    if (!this.ctx) {
      const ctx = this.ctx = new AudioContext(), mix = S()?.mix;
      this.master = new GainNode(ctx, { gain: this.levels.master });
      this.scale = new GainNode(ctx, { gain: 1 });
      this.scale.connect(this.master).connect(ctx.destination);
      for (const b of BUSES) {
        (this.bus[b] = new GainNode(ctx, { gain: this.levels[b] })).connect(this.scale);
        (this.far[b] = new GainNode(ctx, { gain: gainOf(mix?.far ?? -10) })).connect(new BiquadFilterNode(ctx, { type: "lowpass", frequency: mix?.muffle ?? 700 })).connect(this.bus[b]);
      }
      this.roof = new BiquadFilterNode(ctx, { type: "lowpass", frequency: mix?.roof ?? 1200 });
      this.roof.connect(this.bus.ambience);
      ctx.onstatechange = () => this.onchange();
      setInterval(() => this.sweep(), 30_000);
    }
    return this.ctx.resume().then(() => { if (this.snap && this.on) this.update(this.snap, this.here, null); });
  }

  setOn(on: boolean) {   // called from a click, which is what lets the browser start the audio
    this.on = on;
    if (on) void this.start();
    else if (this.ctx) {
      this.quiet();
      void this.ctx.suspend();
    }
    this.save();
  }

  /** One of the five volumes, 0 to 1. */
  setLevel(k: keyof Levels, v: number) {
    this.levels[k] = Math.min(1, Math.max(0, v));
    if (this.ctx) (k === "master" ? this.master : this.bus[k]).gain.setTargetAtTime(this.levels[k], this.ctx.currentTime, 0.03);
    this.save();
  }

  private hidden(hide: boolean) {
    const ctx = this.ctx;
    if (!ctx || !this.on) return;
    if (hide) {
      this.scale.gain.setTargetAtTime(0, ctx.currentTime, 0.05);
      this.track?.el.pause();
      setTimeout(() => document.hidden && void ctx.suspend(), 400);
    } else void ctx.resume().then(() => { this.night(true); void this.track?.el.play().catch(() => {}); });
  }

  /** SPEC-v4.0.5 §7.9: the radio's stream into the music bus, so the Music slider, the night's quiet and a hidden page
   *  hold for it as for any track. Once: an element routed through the audio graph stays routed. */
  radio(el: HTMLAudioElement) {
    if (!this.ctx || this.radioIn) return;
    this.radioIn = true;
    this.ctx.createMediaElementSource(el).connect(this.bus.music);
  }

  /** §4.9: the night is quieter overall. */
  private night(now = false) {
    const ctx = this.ctx!, mix = S()?.mix;   // (SPEC-v4.0.5 §7.9: nothing to scale by if sounds.json did not come)
    if (!mix) return;
    this.scale.gain.setTargetAtTime(this.snap?.clock.phase === "night" ? gainOf(mix.night) : 1, ctx.currentTime, now ? 0.1 : 1);
  }

  // ---- files ----

  /** A file, decoded, fetched the first time it is wanted and kept while it is used. */
  private load(url: string) {
    let c = this.clips.get(url);
    if (!c) this.clips.set(url, c = { p: fetch(ART + url).then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(r.status === 404 && this.lost(url)))).then((b) => this.ctx!.decodeAudioData(b)).catch(() => null), used: 0 });
    c.used = performance.now();
    return c.p;
  }

  /** A file the engine has not got (the WAVs are not in the repo: RUNNING.md says where they come from). */
  private lost(url: string) {
    if (!this.missing.has(url)) { this.missing.add(url); this.onchange(); }
  }

  /** Drop what has not been used for a while (what goes round is in use all the time). */
  private sweep() {
    const keep = new Set([...this.holds.values()].map((h) => h.url)), old = performance.now() - KEEP * 1000;
    for (const [url, c] of this.clips) if (c.used < old && !keep.has(url)) this.clips.delete(url);
  }

  // ---- what is heard ----

  /** Every sound begins here: written in the audio log, so what played can be checked without ears, and among what
   *  the Lab has heard lately. The answer is whether to really play it (the audio clock is running). */
  private begin(what: string, name: string, where: Where, gain: number, from: { pet?: string; room?: string | null } = {}) {
    this.log.push({ t: Math.round(performance.now()), what, name, ...(from.pet ? { pet: from.pet } : {}), ...(from.room ? { room: from.room } : {}), where, gain: Math.round(gain * 1000) / 1000 });
    if (this.log.length > 500) this.log.splice(0, this.log.length - 500);
    this.heard = [{ at: Date.now(), what: `${name.replace(/^\w+\//, "")}${from.pet ? ` (${from.pet})` : ""}${where !== "here" ? `, ${where}` : ""}` }, ...this.heard].slice(0, 40);
    this.onchange();
    return this.ctx?.state === "running";
  }

  /** Distance (§4.4): what happens in the room on screen is heard as it is; next door, through a door, quiet and
   *  muffled; further off not at all (null). */
  private where(room: string | null | undefined): Where | null {
    if (!room || room === this.here) return "here";
    return Object.values(this.snap?.rooms.find((r) => r.id === this.here)?.doors ?? {}).includes(room) ? "next door" : null;
  }

  /** One sound of ours, once (§4.7): a variant at random, its pitch ±5%, the same one in the same room at most once
   *  every 1 to 2 seconds, at most mix.effects effects at once. `room`: where it happens (null: here). False if it was not played. */
  fx(name: string | null, o: { room?: string | null; where?: Where; pet?: string; what?: string; at?: number; rate?: number; gain?: number; v?: number; jitter?: boolean; gate?: string | false; every?: number; bus?: Bus; dest?: AudioNode; quiet?: boolean } = {}) {
    const lv = name && S().sounds ? levelOf(S(), name) : null, ctx = this.ctx, where = o.where ?? this.where(o.room);
    if (!name || !lv || !where || !ctx) return false;
    const urls = filesOf(S(), name), bus = o.bus ?? lv.bus, key = o.gate === false ? null : o.gate ?? `${name}|${o.room ?? this.here}`;
    if (key && !this.gate.open(key, performance.now() / 1000, o.every)) return false;
    const vital = ["jingles", "conflict", "life"].includes(S().sounds[name].group);   // (these always play)
    if (bus === "effects" && this.sounding >= S().mix.effects && !vital) return false;
    const gain = lv.gain * (o.gain ?? 1), dest = o.dest ?? (where === "here" ? this.bus[bus] : this.far[bus]);
    if (o.quiet ? ctx.state !== "running" : !this.begin(o.what ?? "sfx", name, where, gain, { pet: o.pet, room: o.room })) return false;
    const asked = ctx.currentTime, url = urls[o.v ?? Math.floor(Math.random() * urls.length)];
    if (bus === "effects") this.sounding++;
    void this.load(url).then((buffer) => {
      const late = ctx.currentTime - asked > 1.5;   // (a file still on its way after a second and a half: its moment has gone)
      if (!buffer || late || !this.live) { if (bus === "effects") this.sounding--; return; }
      const src = new AudioBufferSourceNode(ctx, { buffer, playbackRate: (o.rate ?? 1) * (o.jitter === false ? 1 : 1 + (Math.random() * 2 - 1) * 0.05) });
      src.connect(new GainNode(ctx, { gain })).connect(dest);
      if (bus === "effects") src.onended = () => this.sounding--;
      src.start(Math.max(ctx.currentTime, o.at ?? 0));
    });
    return true;
  }

  /** The sound the `on` table gives an event (sounds.json), once. */
  private on_(key: string, o: Parameters<Voice["fx"]>[1] = {}) { return this.fx(soundFor(S(), key), { what: key.split(".")[0], ...o }); }

  /** Keep exactly these going round (§4.2, §4.5): whatever is new fades in over the cross-fade, whatever is no longer
   *  wanted fades out, the rest carries on at its new level. A loop starts once its file has come. */
  private hold(want: Map<string, Want>) {
    const ctx = this.ctx!, now = ctx.currentTime, tc = S().mix.fade / 3;
    for (const [key, w] of want) {
      let h = this.holds.get(key);
      if (!h) {
        const url = filesOf(S(), w.name)[0], gain = new GainNode(ctx, { gain: 0 });
        gain.connect(w.dest);
        this.holds.set(key, h = { name: w.name, gain, src: null, url, level: w.level, gone: false });
        this.begin(w.what, w.name, w.where, w.level, { room: w.room });
        const held = h;
        void this.load(url).then((buffer) => {
          if (!buffer || held.gone) return;
          held.src = new AudioBufferSourceNode(ctx, { buffer, loop: true });
          held.src.connect(held.gain);
          held.src.start(ctx.currentTime, Math.random() * buffer.duration);   // (two rooms of the same kind need not begin at the same place)
          held.gain.gain.setTargetAtTime(held.level, ctx.currentTime, tc);
        });
      } else if (h.src) h.gain.gain.setTargetAtTime(w.level, now, tc);
      h.level = w.level;
    }
    for (const [key, h] of this.holds) {
      if (want.has(key)) continue;
      h.gone = true;
      h.gain.gain.setTargetAtTime(0, now, tc);
      h.src?.stop(now + 4 * tc);
      this.holds.delete(key);
    }
  }

  // ---- music ----

  /** §4.2, §4.5, §4.6: one track at a time. The visitor's music while it is heard (one after another), nothing while
   *  the radio plays here, else the house's own: a mood takes over at once, cross-fading; otherwise a track plays once,
   *  then 1 to 3 minutes of ambience only, then the next; a new room or the night coming cross-fades to its own. */
  private music(s: Snap, type: string) {
    const M = S().music, now = performance.now(), m = s.dj?.music, mw = m ? (m.scope === "house" ? "here" : this.where(m.scope)) : null;
    const radio = s.dj?.radio, radioHere = !!radio?.on;   // (the radio is heard, more quietly, from every room: the house's own music never plays over it)
    let want: { name: string; take: boolean; dj: boolean; where: Where } | null = null;
    if (m && mw) {
      const list = M.visitor[m.mood] ?? [];
      if (list.length) want = { name: list[(m.since + this.djN) % list.length], take: true, dj: true, where: mw };
    } else if (!radioHere) {
      const w = wantMusic(S(), { mood: this.mood(s), type, phase: s.clock.phase, season: s.clock.season, weather: s.weather });
      if (w) want = { ...w, dj: false, where: "here" };
    }
    const t = this.track;
    if (t && want && t.name === want.name && t.dj === want.dj) {
      if (t.where !== want.where) { t.gain.disconnect(); t.gain.connect(want.where === "here" ? this.bus.music : this.far.music); t.where = want.where; }
      return;
    }
    if (t) {   // another wanted, or none: this one fades out; a mood that is over leaves a rest behind it
      this.fade(t);
      if (t.take && !t.dj && !want?.take) this.rest();
    }
    if (want && (want.take || now >= this.restUntil)) this.play(want);
  }

  private rest() {
    const [lo, hi] = S().mix.rest;
    this.restUntil = performance.now() + rnd(lo, hi) * 1000;
  }

  private play(w: { name: string; take: boolean; dj: boolean; where: Where }) {
    const url = filesOf(S(), w.name)[0], ctx = this.ctx!, el = new Audio(ART + url), gain = new GainNode(ctx, { gain: 0 }), level = levelOf(S(), w.name)?.gain ?? 1;
    el.preload = "auto";   // (streamed, not decoded whole: a track starts at once)
    el.onerror = () => { if (el.getAttribute("src")) void fetch(ART + url, { method: "HEAD" }).then((r) => r.status === 404 && this.lost(url)).catch(() => {}); };
    const src = ctx.createMediaElementSource(el);
    src.connect(gain).connect(w.where === "here" ? this.bus.music : this.far.music);
    gain.gain.setTargetAtTime(level, ctx.currentTime, S().mix.fade / 3);
    const t: Track = this.track = { ...w, el, src, gain };
    el.onended = () => {
      if (this.track !== t) return;
      this.track = null;
      this.fade(t);
      for (const k of Object.keys(this.moodUntil)) if (S().music.moods[k] === t.name) delete this.moodUntil[k];   // grief and celebration play once
      if (t.dj) this.djN++;
      else if (!t.take) this.rest();
      if (this.snap) this.music(this.snap, this.snap.rooms.find((r) => r.id === this.here)?.type ?? "");
    };
    void el.play().catch(() => {});
    this.begin("music", w.name, w.where, level);
  }

  private fade(t: Track) {
    if (this.track === t) this.track = null;
    t.gain.gain.setTargetAtTime(0, this.ctx!.currentTime, S().mix.fade / 3);
    setTimeout(() => { t.el.pause(); t.el.removeAttribute("src"); t.el.load(); t.src.disconnect(); t.gain.disconnect(); }, S().mix.fade * 1500);   // (SPEC-v4.0.5 §7.9: its nodes let go)
  }

  /** The mood that takes the music over: a fight here or next door; a fight elsewhere, or a quarrel in the last minute
   *  and a half; grief or a celebration (from a banner, until its track has played). */
  private mood(s: Snap) {
    const live = (s.scuffles ?? []).filter((x) => !x.stopped && s.tick <= x.until);
    if (live.some((x) => this.where(x.room))) return "fight";
    const QUARREL = ["snub", "insult", "threat", "sneer", "sabotage", "theft", "shove", "fight", "harm"];
    if (live.length || s.moments.some((m) => QUARREL.includes(m.kind) && ago(s, m.tick) < 90)) return "tension";
    for (const k of ["grief", "celebration"]) if ((this.moodUntil[k] ?? 0) > performance.now()) return k;
    return null;
  }

  // ---- what the house does ----

  private thunder() {   // a moment after the lightning, at most every 12 seconds (the sky flashes more often than that)
    const ctx = this.ctx;
    if (!this.live || !ctx || ctx.currentTime < this.thunderAt) return;
    this.thunderAt = ctx.currentTime + 12;
    this.on_("moment.storm", { at: ctx.currentTime + rnd(0.5, 1.5), gate: false, where: "here" });
  }

  /** A hob's foot comes down in the room on screen: its floor's step, or a limp. */
  private step(id: string) {
    const s = this.snap, p = s?.pets.find((q) => q.id === id);
    if (!this.live || !s || !p || p.room !== this.here) return;
    const F = S().floors, type = s.rooms.find((r) => r.id === p.room)?.type ?? "";
    this.fx(p.hurt?.lasting === "limp" || p.hurt?.level ? F.limp : F[type] ?? F.default, { room: p.room, pet: p.label, what: "step" });
  }

  /** A line of a hob's: babble, a syllable at a time, in turn after whoever spoke last. `lead`: a sound before it. */
  private say(p: PetV, text: string, where: Where, lead?: string) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.talkFree + 0.25);
    if (at - now > 4) return;   // too far behind to still mean anything (a replay at speed)
    const v = voiceInput(p), syl = babble(text, voiceOf(v).base, v.stage, S().sounds["sfx/voice_babble"]?.n ?? 8);
    if (!syl.length || !this.begin("speech", text, where, 1, { pet: p.label, room: p.room })) return;
    const t0 = lead && this.fx(lead, { room: p.room, where, pet: p.label, gate: false }) ? at + 0.35 : at;
    this.talkFree = this.babble(syl, { room: p.room, where, at: t0 }) + 0.15;
  }

  /** Babble on the audio clock (from `at`, else now), on the voices volume; returns when its last syllable begins. */
  babble(syl: ReturnType<typeof babble>, o: { room?: string; where?: Where; at?: number } = {}) {
    const at = o.at ?? (this.ctx?.currentTime ?? 0) + 0.03;
    for (const x of syl) this.fx("sfx/voice_babble", { room: o.room, where: o.where ?? "here", at: at + x.at, rate: x.rate, gain: x.gain, v: x.v, jitter: false, gate: false, quiet: true });
    return at + (syl.at(-1)?.at ?? 0);
  }

  /** SPEC-v4.0 §5: a line of a conversation has come up over its speaker's head (room.ts: the room on screen). The last
   *  line's end brings what came of it (an argument, a hug, a whisper of gossip...). */
  private line(l: Line) {
    const p = this.snap?.pets.find((q) => q.id === l.pet), where = this.where(l.room);
    if (!this.live || !p || !where) return;
    this.say(p, l.text, where);
    if (l.last) for (const c of l.came ?? []) {
      const key = `talk.${typeof c === "string" ? c : c.what}`;
      if (S().on?.[key]) { setTimeout(() => this.on_(key, { room: l.room, pet: p.label }), Math.min(6000, l.after)); break; }
    }
  }

  /** For the Songbook: hear one version now, outside the queue. False if sound is off. */
  hear(notes: Note[], v: VoiceInput | "box" | "bird") {
    if (!this.live || !this.ctx) return false;
    const at = this.ctx.currentTime + 0.03;
    typeof v === "string" ? tune(this.ctx, this.bus.effects, notes, at, v === "bird") : schedule(this.ctx, this.bus.voices, planSong(notes, v), at);
    return true;
  }

  /** A song (SPEC-v3.1 §3.4), in the singer's own voice, or the music box's or a bird's. It waits its turn like speech. */
  private sing(who: string, title: string, notes: Note[], v: VoiceInput | "box" | "bird", where: Where, room: string) {
    const ctx = this.ctx!, now = ctx.currentTime, at = Math.max(now + 0.03, this.talkFree + 0.35), bus = typeof v === "string" ? "effects" : "voices";
    if (at - now > 14 || !this.begin("song", title, where, 0.42, { pet: who, room })) return;
    const dest = where === "here" ? this.bus[bus] : this.far[bus];
    this.talkFree = typeof v === "string" ? tune(ctx, dest, notes, at, v === "bird") : schedule(ctx, dest, planSong(notes, v), at);
  }

  /** The Lab's sound board: one sound of ours now (a loop for a few seconds), whatever the gate says. */
  audition(name: string) {
    const ctx = this.ctx, lv = levelOf(S(), name);
    if (!this.live || !ctx || !lv) return false;
    if (lv.bus === "music" || name.startsWith("music/")) {   // a few seconds of a track, faded in and out
      const el = new Audio(ART + filesOf(S(), name)[0]), g = new GainNode(ctx, { gain: 0 }), src = ctx.createMediaElementSource(el);
      src.connect(g).connect(this.bus.music);
      g.gain.setTargetAtTime(lv.gain, ctx.currentTime, 0.3);
      g.gain.setTargetAtTime(0, ctx.currentTime + 9, 0.4);
      void el.play().catch(() => {});
      setTimeout(() => { el.pause(); el.removeAttribute("src"); el.load(); src.disconnect(); g.disconnect(); }, 11_000);
      return this.begin("lab", name, "here", lv.gain);
    }
    if (!lv.loop) return this.fx(name, { where: "here", gate: false, what: "lab", bus: lv.bus === "ambience" ? "effects" : lv.bus });
    const key = `lab|${name}`, url = filesOf(S(), name)[0];
    void this.load(url).then((buffer) => {
      if (!buffer) return;
      const src = new AudioBufferSourceNode(ctx, { buffer, loop: true }), g = new GainNode(ctx, { gain: 0 });
      src.connect(g).connect(this.bus[lv.bus]);
      src.start();
      g.gain.setTargetAtTime(lv.gain, ctx.currentTime, 0.2);
      g.gain.setTargetAtTime(0, ctx.currentTime + 6, 0.3);
      src.stop(ctx.currentTime + 8);
    });
    return this.begin("lab", key.slice(4), "here", lv.gain);
  }

  /** The page's own small sounds (uisound.ts): ui/click, a page turned, the tram's bell... */
  ui(kind: string) { return this.live && this.on_(`ui.${kind}`, { where: "here", gate: `ui|${kind}` }); }

  /** A banner has come up (banner.ts): its jingle. A death or a killing brings grief to the music, a great thing a celebration. */
  banner(kind: string) {
    const until = performance.now() + 6 * 60_000;
    if (kind === "death" || kind === "killing") this.moodUntil.grief = until;
    if (["works", "ambition", "clearout"].includes(kind)) this.moodUntil.celebration = until;   // (a finished project, a new era: not every first)
    if (!this.live) return;
    this.on_(S().on?.[`banner.${kind}`] ? `banner.${kind}` : "ui.banner", { where: "here" });   // (the same sound as the moment's own, just played, is not played twice)
    if (this.snap) this.music(this.snap, this.snap.rooms.find((r) => r.id === this.here)?.type ?? "");
  }

  private quiet() {   // stop everything that goes on by itself
    if (this.track) this.fade(this.track);
    this.hold(new Map());
  }

  /** Called with every snapshot that reaches the screen, live or replayed, sound on or off (so that turning sound
   *  on later does not replay old news). `here` is the room being looked at. */
  update(s: Snap, here: string, _sel: string | null) {
    const t = news(this.seen, s), ctx = this.ctx, fresh = !this.seen || t.seen.tick < (this.seen?.tick ?? 0);
    this.seen = t.seen;
    this.snap = s;
    this.here = here;
    if (!this.on || !ctx || !S().sounds || ctx.state !== "running") { this.remember(s); return; }
    const pets = new Map(s.pets.map((p) => [p.id, p])), label = (id: string | null | undefined) => pets.get(id ?? "")?.label;
    const room = s.rooms.find((r) => r.id === here), type = room?.type ?? "", now = ctx.currentTime;
    if (!this.greeted) { this.greeted = true; this.on_("visitor.arrives", { where: "here" }); }   // the owner of the world has arrived

    // the time of day: the dawn's and the dusk's jingles, and the night quieter
    if (this.phase && this.phase !== s.clock.phase && !this.mood(s)) {
      if (this.phase === "night" && s.clock.phase === "day") this.on_("dawn", { where: "here", bus: "music" });
      if (this.phase === "day" && s.clock.phase === "dusk") this.on_("dusk", { where: "here", bus: "music" });
    }
    this.phase = s.clock.phase;
    this.night();
    this.music(s, type);

    // ---- what goes round: the room and the weather (§4.2), the machines, the sweeper, the train, a scuffle ----
    const want = new Map<string, Want>(), loops: [number, string, Want][] = [];
    for (const a of wantAmbience(S(), type, s.clock.phase, s.weather))
      want.set(`amb|${a.name}|${a.roof}`, { name: a.name, level: (levelOf(S(), a.name)?.gain ?? 1) * a.gain, dest: a.roof ? this.roof : this.bus.ambience, what: "ambience", room: here, where: "here" });
    const loop = (rank: number, key: string, name: string | null, where: Where | null, room: string, extra = 1) => {
      const lv = name ? levelOf(S(), name) : null;
      if (name && lv && where) loops.push([rank, `${key}|${where}`, { name, level: lv.gain * extra, dest: where === "here" ? this.bus[lv.bus] : this.far[lv.bus], what: "loop", room, where }]);
    };
    for (const x of s.scuffles ?? []) if (!x.stopped && s.tick <= x.until) loop(0, `scuffle|${x.n}`, soundFor(S(), "fight.scuffle"), this.where(x.room), x.room);
    for (const r of s.rooms) {
      const w = r.type ? this.where(r.id) : null;
      for (const [name, o] of w ? Object.entries(r.objects) : []) {
        const m = o.machine;
        if (!m) continue;
        if (m.state === "working" && m.kind !== "forge") loop(w === "here" ? 1 : 4, `m|${r.id}|${name}`, soundFor(S(), `machine.${m.kind}`), w, r.id);
        if (m.pot?.servings) loop(w === "here" ? 2 : 5, `pot|${r.id}|${name}`, soundFor(S(), "machine.pot"), w, r.id);
        // the kiln's door clanks as it is opened when its firing is done; the stove's cook chops and stirs; the forge's bellows
        const key = `${r.id}|${name}`, before = this.was.kiln.get(key);
        if (m.kind === "kiln" && before === "working" && m.state !== "working") this.on_("machine.kiln door", { room: r.id });
        this.was.kiln.set(key, m.state);
        if (w === "here" && m.state === "working" && m.kind === "stove") this.on_(Math.random() < 0.5 ? "machine.stove.work" : "machine.stove.stir", { room: r.id, gate: `stove|${key}`, every: 4 });
        if (w === "here" && m.state === "working" && m.kind === "forge") this.on_("machine.forge", { room: r.id, gate: `bellows|${key}`, every: 6 });
      }
    }
    for (const c of s.creatures) {
      if (c.kind === "train") {   // §4.4: the train is heard faintly everywhere; in the room it is in, as it is
        const inHere = (c.cars ?? []).some((x) => x?.room === here), wasMoving = this.was.train.get(c.id);
        if (c.moving) loop(3, `train|${c.id}`, soundFor(S(), "train.chug"), inHere ? "here" : "everywhere", here, inHere ? 1 : gainOf(S().mix.train_far));
        if (inHere && wasMoving && !c.moving) this.on_("train.brake", { room: here });
        this.was.train.set(c.id, !!c.moving);
      } else if (c.kind === "sweeper" && c.room === here) {
        if (!c.docked) loop(2, `sweeper|${c.id}`, soundFor(S(), "sweeper.whir"), "here", here);
        if (c.full) this.on_("sweeper.beep", { room: here, gate: `beep|${c.id}`, every: 3 });
        if ((c.load ?? 0) > (this.was.sweep.get(c.id) ?? Infinity)) this.on_("sweeper.pickup", { room: here });
        this.was.sweep.set(c.id, c.load ?? 0);
      }
    }
    loops.sort((a, b) => a[0] - b[0]);
    for (const [, key, w] of loops.slice(0, S().mix.loops)) want.set(key, w);
    this.hold(want);
    if (fresh) { this.remember(s); return; }

    // ---- what has just happened ----
    for (const a of t.acts) {   // a step just finished, each heard once
      const where = this.where(a.room), o = s.rooms.find((r) => r.id === a.room)?.objects[(a.what ?? "").toLowerCase().replace(/^(the|my|your|an?) /, "")], used = a.type === "use" || a.type === "fiddle";
      // SPEC-v3.3 §4: a thing that sounds, sounded: its own sound by its kind or (a fixture) its name, from wherever it is
      const loud = a.loud || (used && !!(o?.made?.loud || o?.fix?.loud));
      const thing = [inventedSound(a.kind ?? o?.made?.recipe.kind), a.kind ?? o?.made?.recipe.kind, a.what, loud ? "default" : null].find((k) => k && S().on[`thing.${k}`]);
      if (where && thing && (loud || used)) this.on_(`thing.${thing}`, { room: a.room, pet: label(a.pet), what: "instrument" });
      else if (where) this.on_(a.type === "use" ? (o?.fix && "meal" in o.fix ? "use.meal" : o?.fix && "water" in o.fix ? "use.water" : "") : `act.${a.type}`, { room: a.room, pet: label(a.pet) });
    }
    for (const x of t.speak) {   // a hob's words (a reply to the visitor begins with the hob's answering sound)
      const p = pets.get(x.pet), where = p && this.where(p.room);
      if (p && where) this.say(p, x.text, where, x.to === "visitor" ? soundFor(S(), "visitor.answered") ?? undefined : undefined);
    }
    for (const x of t.vox) {   // SPEC-v3.3 §4: the small sounds a hob makes by itself
      const p = pets.get(x.pet);
      if (p && x.kind === "murmur") { const where = this.where(x.room); if (where) this.say(p, "mm hm", where); }
      else this.on_(`vox.${x.kind}`, { room: x.room, pet: p?.label, gate: `vox|${x.pet}` });
    }
    for (const m of t.moments) {
      const kind = m.kind.startsWith("arrival ") ? "arrival" : m.kind === "stage" ? (pets.get(m.pet ?? "")?.stage === "elder" ? "stage.old" : "stage.up") : `moment.${m.kind}`;
      if (kind === "arrival" || kind === "moment.storm") this.on_(kind, { where: "here" });   // a discovery is heard all through the house
      else this.on_(kind, { room: m.room, pet: label(m.pet) });
    }
    for (const x of t.sing) {   // SPEC-v3.1 §3.4: whoever sang, in their own voice, as loud as their room is from here
      const song = s.songs?.[x.song], p = pets.get(x.by), where = song && this.where(x.room);
      const beast = s.creatures.find((c) => c.id === x.by), who = p?.label ?? (x.by === "music box" ? "the music box" : beast?.name ?? `a ${beast?.kind ?? "bird"}`);
      if (where) this.sing(who, song!.name, song!.notes, p ? voiceInput(p, s) : x.by === "music box" ? "box" : "bird", where, x.room);
    }
    // a music box left playing plays: the house's own box tune, round again after a pause, as loud as its room is from here
    const playing = performance.now() < this.boxAt ? undefined : s.rooms.find((r) => Object.values(r.objects ?? {}).some((o) => o.state === "playing") && this.where(r.id));
    if (playing) {
      const song = Object.values(s.songs ?? {}).find((x) => x.by === "music box");
      this.sing("the music box", song?.name ?? "the music box's tune", song?.notes ?? BOX_TUNE, "box", this.where(playing.id)!, playing.id);
      this.boxAt = performance.now() + 12000;
    }
    if (rings(s, here, now, this.rang)) {   // SPEC-v3.6b §4: struck at the forge in the room on screen; the room throws a shower of sparks with it
      this.rang = now + Math.random() * 3;
      this.on_("machine.anvil", { room: here, gate: false });
      dispatchEvent(new Event("pet:anvil"));
    }
    for (const x of s.scuffles ?? []) {   // a fight here: blows now and then; the blood when it ends
      if (x.room !== here) continue;
      if (!x.stopped && s.tick <= x.until) this.on_("fight.hit", { room: here });
      if (x.blood && s.tick >= x.until && !this.was.blood.has(x.n)) { this.was.blood.add(x.n); this.on_("fight.splat", { room: here }); }
    }
    this.visitor(s);
    this.room(s, here, type);
    this.remember(s);
  }

  /** SPEC-v4.0 §10: the visitor's tools, as they are used (snap.visitor4.log), from whoever's page. */
  private visitor(s: Snap) {
    const log = s.visitor4?.log ?? [], last = log.length ? log[log.length - 1].tick : -1;
    if (this.was.visitor >= 0) for (const x of log.filter((x) => x.tick > this.was.visitor)) {
      const where = this.where(s.pets.find((p) => p.id === x.pet)?.room) ?? "here", talk = x.tool === "talk" || x.tool === "answer";
      for (let i = 0, n = talk ? Math.min(4, Math.max(1, Math.round((x.text ?? "").length / 25))) : 1; i < n; i++)
        this.on_(`visitor.${x.tool}`, { where, gate: false, at: (this.ctx?.currentTime ?? 0) + i * 0.4 });
    }
    this.was.visitor = Math.max(this.was.visitor, last);
  }

  /** The hobs and creatures in the room on screen: what their bodies take up, a mood turning, a startle, sleep, an egg
   *  about to hatch, sickness, hunger and cold now and then, fishing, the creatures' calls. */
  private room(s: Snap, here: string, type: string) {
    const outside = S().ambience.outside.includes(type), sec = performance.now() / 1000;
    for (const p of s.pets.filter((q) => q.room === here && q.stage !== "dead")) {
      const o = { room: here, pet: p.label }, b = p.body ? `${p.body.activity}|${p.body.since}` : "";
      if (b && this.was.body.has(p.id) && this.was.body.get(p.id) !== b) this.on_(`body.${p.body!.activity}`, o);
      if (p.mood4 && this.was.mood.has(p.id) && this.was.mood.get(p.id) !== p.mood4) this.on_(`mood.${p.mood4}`, o);
      if (p.react && this.was.react.has(p.id) && this.was.react.get(p.id) !== p.react.tick) this.on_(`react.${p.react.kind}`, o);
      if (p.asleep && this.gate.open(`sleep|${here}`, sec, 6)) this.on_("sleep", { ...o, gate: false });   // (one breath at a time, however many sleep)
      if (p.stage === "egg" && (p.hatches_in ?? 99) < 20 && this.gate.open(`egg|${p.id}`, sec, 3)) this.on_("egg.wobble", { ...o, gate: false });
      if (p.sick && !p.asleep && this.gate.open(`sick|${p.id}`, sec, 25)) this.on_("sick", { ...o, gate: false });
      if ((p.levels as Record<string, number> | undefined)?.hunger === 4 && !p.asleep && this.gate.open(`hungry|${p.id}`, sec, 40)) this.on_("hungry", { ...o, gate: false });
      if (outside && s.weather === "snow" && !p.asleep && p.stage !== "egg" && this.gate.open(`cold|${p.id}`, sec, 30)) this.on_("cold", { ...o, gate: false });
    }
    for (const f of s.pond?.room === here ? s.pond.fishers : []) {   // SPEC-v3.6a: cast, the float, a bite, reeling in, and what came of it
      const was = this.was.fish.get(f.pet), o = { room: here, pet: s.pets.find((p) => p.id === f.pet)?.label };
      if (was && was.cast !== f.cast) { if (was.bite && !was.pulled) this.on_("fish.lost", o); this.on_("fish.cast", o); this.on_("fish.plop", { ...o, at: (this.ctx?.currentTime ?? 0) + 0.8 }); }
      if (was && !was.bite && f.bite != null) this.on_("fish.bite", o);
      if (was && !was.pulled && f.pulled != null) { this.on_("fish.reel", o); this.on_(f.caught && /rare/.test(f.caught.tier) ? "fish.rare" : f.caught ? "fish.caught" : "fish.lost", o); }
    }
    for (const c of s.creatures.filter((c) => c.room === here && !/asleep/.test(c.doing)))   // small creatures make small sounds now and then
      if (S().on[`creature.${c.kind}`] && this.gate.open(`creature|${c.id}`, sec, c.doing.startsWith("singing") ? 5 : 12)) this.on_(`creature.${c.kind}`, { room: here, gate: false });
  }

  /** What was so this time, to hear what changes next time (also while sound is off, so nothing old plays on). */
  private remember(s: Snap) {
    for (const p of s.pets) {
      this.was.body.set(p.id, p.body ? `${p.body.activity}|${p.body.since}` : "");
      if (p.mood4) this.was.mood.set(p.id, p.mood4);
      this.was.react.set(p.id, p.react?.tick ?? -1);
    }
    this.was.fish = new Map((s.pond?.fishers ?? []).map((f) => [f.pet, { cast: f.cast, bite: f.bite != null, pulled: f.pulled != null }]));
    const log = s.visitor4?.log ?? [];
    this.was.visitor = Math.max(this.was.visitor, log.length ? log[log.length - 1].tick : 0);
  }
}

/** A line of a conversation as room.ts sends it: who says it, in which room, and, for the last, what came of it and when it ends (ms). */
export type Line = { pet: string; text: string; room: string; last: boolean; after: number; came?: (string | { what: string })[] };
