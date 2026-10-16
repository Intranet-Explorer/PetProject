// Small moving things: puffs, sparkles, hearts, notes, z's, dust, flying bits. Each has a built-in picture of a few
// pixels, drawn here; an entry `fx.<name>` in sprites.json replaces it (its one animation, if it has one, plays once
// over the effect's life; an animation called "kinds" is a set of variants instead).
// Sprites are reused, so a busy room allocates nothing per frame.
import { Container, Sprite } from "pixi.js";
import { textCanvas } from "./font";
import type { Texture } from "pixi.js";
import { anim, def, fromCanvas, has, tex } from "./assets";

const INK = "#2b2233";
const SHAPES: Record<string, [string[], string, boolean]> = {   // rows, colour, with a dark outline
  heart: [[".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."], "#e8506e", true],
  note: [["..##", "..#.", "..#.", ".##.", "###.", ".#.."], "#3a3350", false],
  z: [["#####", "...#.", "..#..", ".#...", "#####"], "#f4f1e4", true],
  sparkle: [["..#..", "..#..", "##.##", "..#..", "..#.."], "#fff6c8", false],
  glint: [[".#.", "###", ".#."], "#ffffff", false],
  flash: [["..#..", ".###.", "#####", ".###.", "..#.."], "#ffffff", false],
  dust: [[".###.", "#####", ".###."], "#e9e2d2", false],
  puff: [[".###.", "#####", "#####", "#####", ".###."], "#f1ece0", false],
  grit: [["##", "##"], "#f4f0e0", false],
  chalk: [["##", "##"], "#f4f0e0", false],
  speck: [["#"], "#ffffff", false],
  tick: [["#..", ".#.", ".#.", ".#.", "#.."], "#3a3350", false],
  drop: [["#", "#", "#"], "#9fd0ee", false],
  bang: [["##", "##", "##", "##", "..", "##"], "#ffd24a", true],
  page: [["####", "####", "####"], "#fffbe8", true],
  ribbon: [[".#.", "###", "#.#"], "#ffcf4a", true],
  plus: [[".#.", "###", ".#."], "#ffffff", true],
  pip: [["##", "##"], "#ffffff", true],
  out: [["..##.", ".##..", "####.", "..##.", ".##..", "#...."], "#aab0c6", true],
  flag: [["###", "###", "#..", "#.."], "#ffffff", true],
  wisp: [[".##.", "####", ".##."], "#ece6da", false],   // SPEC-v3.5.9: a small puff (at the bench), a breath in the cold
};
/** Our names here -> the art's, where they differ. */
const ALIAS: Record<string, string> = { z: "zzz", chalk: "chalk dust", drop: "drip" };
const built = new Map<string, Texture>();
const artName = (name: string) => `fx.${ALIAS[name] ?? name}`;
/** The animation an effect's sprite plays, if it has one. */
function playOf(name: string): string | undefined {
  const d = def(artName(name));
  return d?.anims ? Object.keys(d.anims).find((k) => k !== "kinds") : undefined;
}

/** The picture for an effect: the art's own if it has one, or the few pixels above. */
export function fxTexture(name: string, frame = 0): Texture {
  if (has(artName(name))) return tex(artName(name), playOf(name), frame);
  let t = built.get(name);
  if (t) return t;
  const [rows, color, outline] = SHAPES[name] ?? SHAPES.speck, o = outline ? 1 : 0;
  const c = document.createElement("canvas");
  [c.width, c.height] = [rows[0].length + 2 * o, rows.length + 2 * o];
  const x = c.getContext("2d")!;
  const each = (fn: (px: number, py: number) => void) => rows.forEach((row, py) => [...row].forEach((ch, px) => ch === "#" && fn(px + o, py + o)));
  if (outline) { x.fillStyle = INK; each((px, py) => x.fillRect(px - 1, py - 1, 3, 3)); }
  x.fillStyle = color;
  each((px, py) => x.fillRect(px, py, 1, 1));
  built.set(name, (t = fromCanvas(c)));
  return t;
}

/** SPEC-v3.5.9 §7: a soap-bubble ring, for a made thing rising from its maker; and a little red "made" stamp. */
let ring: Texture | null = null, stamp: Texture | null = null;
export function bubbleTexture() {
  if (ring) return ring;
  const c = document.createElement("canvas"), x = c.getContext("2d")!, R = 10;
  c.width = c.height = 2 * R + 1;
  for (let y = -R; y <= R; y++) for (let i = -R; i <= R; i++) {
    const d = Math.hypot(i, y);
    if (d > R + 0.5) continue;
    x.fillStyle = d > R - 0.7 ? "rgba(255,255,255,0.9)" : "rgba(220,240,255,0.28)";
    x.fillRect(i + R, y + R, 1, 1);
  }
  x.fillStyle = "#ffffff";
  x.fillRect(R - 6, R - 5, 2, 1); x.fillRect(R - 6, R - 4, 1, 2);   // its shine
  return (ring = fromCanvas(c));
}
export function stampTexture() {
  if (stamp) return stamp;
  const t = textCanvas(["MADE"], { color: "#c4484a" }), c = document.createElement("canvas"), x = c.getContext("2d")!;
  [c.width, c.height] = [t.width + 6, 13];
  x.fillStyle = "#fff6e8"; x.fillRect(1, 1, c.width - 2, c.height - 2);
  x.strokeStyle = "#c4484a"; x.lineWidth = 1; x.strokeRect(0.5, 0.5, c.width - 1, c.height - 1);
  x.drawImage(t, 3, 2);
  return (stamp = fromCanvas(c));
}

type Mote = { s: Sprite; x: number; y: number; vx: number; vy: number; g: number; age: number; life: number; sway: number; name: string; frames: number; fps: number; a: number };
type Tween = { t0: number; dur: number; fn: (k: number) => void; done?: () => void };
export type MoteOpts = { vx?: number; vy?: number; g?: number; life?: number; sway?: number; tint?: number; alpha?: number };

export class Fx {
  c = new Container();
  private live: Mote[] = [];
  private pool: Sprite[] = [];
  private tweens: Tween[] = [];
  private floats = new Set<Container>();
  private now = 0;
  /** Nothing rises past this (the top of the room, in its pixels): a note at the ceiling is gone, not cut in half. */
  top = 0;

  /** One mote at (x, y), in the room's pixels; speeds are pixels a second. */
  spawn(name: string, x: number, y: number, o: MoteOpts = {}) {
    if (this.live.length > 260) return;   // a storm of effects never grows without bound
    const s = this.pool.pop() ?? new Sprite();
    const play = playOf(name), a = play ? anim(artName(name), play) : null;
    s.texture = fxTexture(name);
    s.anchor.set(0.5);
    s.tint = o.tint ?? 0xffffff;
    s.alpha = o.alpha ?? 1;
    s.scale.set(1);
    s.visible = true;
    this.c.addChild(s);
    this.live.push({ s, x, y, vx: o.vx ?? 0, vy: o.vy ?? 0, g: o.g ?? 0, age: 0, life: o.life ?? 900, sway: o.sway ?? 0, name, frames: a?.frames.length ?? 1, fps: a?.fps ?? 8, a: o.alpha ?? 1 });
  }
  /** Several at once, thrown outward. */
  burst(name: string, x: number, y: number, n: number, speed = 22, o: MoteOpts = {}) {
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + Math.random(), v = speed * (0.5 + Math.random() * 0.6);
      this.spawn(name, x, y, { vx: Math.cos(a) * v, vy: Math.sin(a) * v - speed * 0.4, life: 500 + Math.random() * 300, ...o });
    }
  }
  /** Call `fn` with 0..1 over `dur` milliseconds, then `done`. */
  tween(dur: number, fn: (k: number) => void, done?: () => void) {
    this.tweens.push({ t0: this.now, dur, fn, done });
  }
  after(ms: number, done: () => void) {
    this.tween(ms, () => {}, done);
  }
  /** A picture carried from one place to another in a low arc, then gone. */
  fly(texture: Texture, from: number[], to: number[], dur: number, scale = 1, done?: () => void) {
    const s = this.pool.pop() ?? new Sprite();
    s.texture = texture;
    s.anchor.set(0.5);
    s.tint = 0xffffff;
    s.alpha = 1;
    s.scale.set(scale);
    s.visible = true;
    this.c.addChild(s);
    this.tween(dur, (k) => s.position.set(from[0] + (to[0] - from[0]) * k, from[1] + (to[1] - from[1]) * k - Math.sin(k * Math.PI) * 7), () => { this.free(s); done?.(); });
  }
  /** Pictures that pop in with a bounce at (x, y), rise `rise` pixels and fade over `dur` ms (the first is drawn behind). */
  float(pics: [Texture, number][], x: number, y: number, rise = 14, dur = 1600) {
    const c = new Container();
    for (const [t, scale] of pics) { const s = new Sprite(t); s.anchor.set(0.5); s.scale.set(scale); c.addChild(s); }
    this.c.addChild(c);
    this.floats.add(c);
    this.tween(dur, (k) => {
      c.scale.set(k < 0.12 ? (k / 0.12) * 1.2 : k < 0.2 ? 1.2 - ((k - 0.12) / 0.08) * 0.2 : 1);
      c.position.set(Math.round(x), Math.round(y - rise * k));
      c.alpha = k > 0.7 ? (1 - k) / 0.3 : 1;
    }, () => { this.floats.delete(c); c.destroy({ children: true }); });
  }
  private free(s: Sprite) {
    s.visible = false;
    this.c.removeChild(s);
    this.pool.push(s);
  }
  clear() {
    for (const m of this.live) this.free(m.s);
    this.live.length = 0;
    this.tweens.length = 0;
    for (const c of this.floats) c.destroy({ children: true });
    this.floats.clear();
  }
  step(now: number, dt: number) {
    this.now = now;
    for (let i = this.live.length - 1; i >= 0; i--) {
      const m = this.live[i];
      m.age += dt;
      if (m.age >= m.life || m.y - m.s.height / 2 < this.top) { this.free(m.s); this.live[i] = this.live[this.live.length - 1]; this.live.pop(); continue; }
      const k = m.age / m.life, sec = dt / 1000;
      m.vy += m.g * sec;
      m.x += m.vx * sec;
      m.y += m.vy * sec;
      m.s.position.set(m.x + (m.sway ? Math.sin(m.age / 260 + m.x) * m.sway : 0), m.y);
      m.s.alpha = m.a * (k > 0.7 ? (1 - k) / 0.3 : 1);
      if (m.frames > 1) m.s.texture = fxTexture(m.name, Math.min(m.frames - 1, Math.floor(k * m.frames)));
    }
    for (let i = this.tweens.length - 1; i >= 0; i--) {
      const t = this.tweens[i], k = Math.min(1, (now - t.t0) / t.dur);
      t.fn(k);
      if (k >= 1) { this.tweens.splice(i, 1); t.done?.(); }
    }
  }
}
