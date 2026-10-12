// Pets and creatures on the floor (SPEC-v3.2 §4, §5). The engine says where each one is; this walks it there along
// a path, in walk frames facing the way it goes, and between the engine's steps keeps it alive: looking about,
// shifting a tile, sitting, glancing at the others. All of that is cosmetic; the engine's position wins the moment a
// step starts. Pets are drawn only through petsprite.ts.
import { Container, Graphics, Sprite, Texture } from "pixi.js";
import { petSheet } from "../petsprite";
import type { PetAnim, PetSheet } from "../petsprite";
import { bodyStage } from "../types";
import type { Creature, PetV, Tile } from "../types";
import { anim, fromCanvas, has, tex } from "./assets";
import { fxTexture } from "./fx";
import type { Fx } from "./fx";
import { clamp, foot, FX, OX, OY, TILE, tileAt } from "./geom";
import type { Dir, Rect } from "./geom";
import { path } from "./path";
import type { Grid } from "./path";
import type { Thing } from "./still";

/** What an actor may know of the room each frame. `free`: could a pet stand on this tile just now. `where`: the
 *  place of a pet, creature, thing or wall by its name, in the room's pixels. */
export type Stage = { now: number; dt: number; fx: Fx; blocked: Grid; K: number; free: (t: Tile, me: string) => boolean; where: (name: string | null | undefined, near?: number[]) => number[] | null;
  others: () => number[][]; book: () => number[] | null;
  /** The house is not moving on just now (a replay stopped): nobody shifts or looks about. */
  held: boolean;
  /** A thing in the room by its name (what a pet has picked up is drawn in its paws). */
  thing: (name: string | null | undefined) => Thing | undefined;
  /** How dark the room is just now, 0 (full day) to 1. */
  dim: number };
/** The step a pet is on, whether the engine says so (`act`) or an older recording only names it (`step`). */
export type Doing = { type: string; what?: string | null; to?: string | null; acting: boolean };
export function doing(p: PetV): Doing | null {
  if (p.act) return { type: p.act.type, what: p.act.what, to: p.act.to, acting: !!p.plan?.acting };
  return p.step ? { type: p.step, acting: !!p.plan?.acting } : null;
}

const textures = new WeakMap<HTMLCanvasElement, Texture>();
const texOf = (c: HTMLCanvasElement) => {
  let t = textures.get(c);
  if (!t) textures.set(c, (t = fromCanvas(c)));
  return t;
};
const boxes = new WeakMap<HTMLCanvasElement, Rect>();
/** The part of a frame that is body, so plates and bubbles sit close to it and never on it. */
function bodyBox(c: HTMLCanvasElement): Rect {
  let b = boxes.get(c);
  if (b) return b;
  const [w, h] = [c.width, c.height], p = c.getContext("2d")!.getImageData(0, 0, w, h).data;
  let [x0, y0, x1, y1] = [w, h, 0, 0];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (p[(y * w + x) * 4 + 3] > 40) [x0, y0, x1, y1] = [Math.min(x0, x), Math.min(y0, y), Math.max(x1, x), Math.max(y1, y)];
  boxes.set(c, (b = x1 < x0 ? { x: w / 4, y: h / 4, w: w / 2, h: (h * 3) / 4 } : { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 }));
  return b;
}

/** Something that walks: a point moving along a line of tiles at a steady pace. */
export class Walker {
  x = 0;
  y = 0;
  dir: Dir = "down";
  moving = false;
  private pts: number[] = [];
  private i = 0;
  private v = 0;
  place(t: Tile) {
    [this.x, this.y] = foot(t);
    this.pts.length = 0;
    this.moving = false;
  }
  tile(): Tile { return tileAt(this.x, this.y); }
  /** Walk to `to` round what is blocked, arriving in about `ms` (longer if the way round is long: `max` tiles in that time). */
  go(to: Tile, g: Grid, ms: number, max = 2.6) {
    const tiles = path(this.tile(), to, g);
    this.pts.length = 0;
    let [px, py, len] = [this.x, this.y, 0];
    for (const t of tiles.slice(1)) {
      const [fx, fy] = foot(t);
      this.pts.push(fx, fy);
      len += Math.hypot(fx - px, fy - py);
      [px, py] = [fx, fy];
    }
    this.i = 0;
    this.moving = len > 0.5;
    this.v = len / (ms * Math.max(1, len / 16 / max));
  }
  step(dt: number) {
    let d = this.v * dt;
    while (d > 0 && this.i < this.pts.length) {
      const dx = this.pts[this.i] - this.x, dy = this.pts[this.i + 1] - this.y, len = Math.hypot(dx, dy);
      if (len > 0.01) this.dir = Math.abs(dx) >= Math.abs(dy) ? (dx < 0 ? "left" : "right") : dy < 0 ? "up" : "down";
      if (len <= d) { [this.x, this.y] = [this.pts[this.i], this.pts[this.i + 1]]; this.i += 2; d -= len; }
      else { this.x += (dx / len) * d; this.y += (dy / len) * d; d = 0; }
    }
    if (this.i >= this.pts.length) this.moving = false;
  }
}

// How a pet holds itself while a step is under way. "turn": it stands turned toward whom or what the step is for.
const POSE: Record<string, PetAnim | "turn" | "wall" | "look"> = {
  make: "make", combine: "make", unmake: "make", teach: "make", arrange: "make", paint: "make", gather: "make", drop: "make", use: "make", take: "make",
  give: "make", show: "make", bequeath: "make", eat: "eat", rest: "sit", lay_egg: "sit", revise_belief: "sit", write_belief: "sit", nuzzle: "happy", accept: "happy",
  sing: "happy", compose: "happy", teach_song: "happy", call: "happy", name: "happy", speak: "turn", tell: "turn", write: "wall", scrub: "wall",
  ask_book: "wall", observe: "look", look: "look", put_away: "make", take_out: "make", hang: "wall",
};
/** What rises from a pet while it is at something, and how often (ms). */
const AIR: Record<string, [string, number]> = { make: ["sparkle", 450], combine: ["sparkle", 380], teach: ["sparkle", 600], sing: ["note", 520], compose: ["note", 700],
  teach_song: ["note", 520], write: ["chalk", 420], scrub: ["chalk", 320], ask_book: ["page", 650], unmake: ["grit", 300], paint: ["grit", 300], lay_egg: ["sparkle", 500] };

/** How a thing a body does by itself looks on the spot (SPEC-v3.3 §1.4), looked up by the activity's name and then by
 *  its icon: an activity added to activities.toml later moves like the others that share its icon, and one with an
 *  icon nobody has heard of still breathes, sways and looks at what it is about (PLAIN), or sits (REST, if it is a
 *  resting one). `a`: the frames; "face" is standing turned to what or whom it is about, "talk" the same chattering,
 *  "look" turning this way and that. `hop`, `sway`: pixels up and sideways, once every `ms`. `lean`: pixels toward
 *  what it is about, in and back every `ms`. `air`: what rises from it, how often (ms), and its colour.
 *  `stir`: what the thing does meanwhile: 1 bounces, 2 shakes, 3 is picked up and held overhead. */
export type Move = { a: PetAnim | "face" | "talk" | "look"; hop?: number; sway?: number; lean?: number; ms?: number; air?: [string, number, number?]; stir?: number };
const MOVES: Record<string, Move> = {
  // by icon
  walk: { a: "look" }, eye: { a: "face", lean: 3, ms: 1300 }, stretch: { a: "stretch" }, groom: { a: "groom" }, note: { a: "idle", sway: 1, ms: 900, air: ["note", 1000] },
  door: { a: "face", lean: 3, ms: 520 }, paws: { a: "make", stir: 2 }, ball: { a: "happy", lean: 4, ms: 430, stir: 1 }, window: { a: "sit.up" }, zzz: { a: "sleep", air: ["z", 2100] },
  bowl: { a: "eat", air: ["speck", 420, 0xd9b36a] }, broom: { a: "make", stir: 3, air: ["dust", 700] }, leaf: { a: "make", air: ["leaf", 650, 0x8fd06a] },
  heart: { a: "sit", lean: 2, ms: 2600, air: ["heart", 3000] }, stone: { a: "quiet" }, speech: { a: "talk", hop: 1, ms: 380 }, radio: { a: "face", sway: 1, ms: 700, lean: 1 },
  // by name, where the icon alone does not say it
  "look about": { a: "look" }, "peek next door": { a: "face", lean: 6, ms: 1700 }, "follow kin": { a: "face", hop: 2, ms: 420, air: ["heart", 3000] }, gather: { a: "make" },
  dance: { a: "dance", sway: 2, ms: 640, air: ["note", 650] }, sing: { a: "happy", air: ["note", 520] }, "watch a creature": { a: "face", lean: 2, ms: 1500 },
  // SPEC-v3.4 §1: settled on something; a thing out of its box, or carried to someone, is in its paws; after a creature at a trot
  seat: { a: "sit" }, box: { a: "make", stir: 3 }, "follow a creature": { a: "face", hop: 2, ms: 420 },
};
const REST: Move = { a: "sit" }, PLAIN: Move = { a: "face", sway: 1, ms: 1100, lean: 1 };
const ABOUT: Dir[] = ["left", "down", "right", "down"];
/** How much bigger than the art's own pixels a pet is drawn (SPEC-v3.3 §5): about 1.6 times, on whole screen pixels. */
export const petScale = (K: number) => Math.max(1, Math.round(K * 1.6)) / K;

const rims = new WeakMap<HTMLCanvasElement, Texture>();
/** A frame's outline alone, half a pixel of the pet's thick outside its body, pale: laid over the dark so a pet is
 *  always found (SPEC-v3.3 §5). Drawn at twice the frame's size, to be shown at half. */
function rimOf(src: HTMLCanvasElement): Texture {
  let t = rims.get(src);
  if (t) return t;
  const c = document.createElement("canvas"), [w, h] = [src.width * 2, src.height * 2];
  [c.width, c.height] = [w + 2, h + 2];
  const x = c.getContext("2d")!;
  x.imageSmoothingEnabled = false;
  for (const [dx, dy] of [[0, 1], [2, 1], [1, 0], [1, 2]]) x.drawImage(src, dx, dy, w, h);
  x.globalCompositeOperation = "source-in";
  x.fillStyle = "#e6ecff";
  x.fillRect(0, 0, c.width, c.height);
  x.globalCompositeOperation = "destination-out";
  x.drawImage(src, 1, 1, w, h);
  rims.set(src, (t = fromCanvas(c)));
  return t;
}

export class PetActor {
  c = new Container();
  /** Its outline in pale, for the room to lay over the dark: it shows in low light only. */
  rim = new Sprite();
  w = new Walker();
  pet!: PetV;
  home: Tile = [0, 0];
  sheet!: PetSheet;
  box: Rect = { x: 0, y: 0, w: 16, h: 16 };
  /** How much bigger than the art it is drawn. */
  P = 1;
  eating = false;
  /** Set by the room: a pose for a moment (a startle, a lean, a hop), over at `until`. */
  pose: { anim: PetAnim; until: number } | null = null;
  private body = new Sprite();
  private held = [new Sprite(), new Sprite(), new Sprite(fxTexture("plus"))];   // what it carries: two bits at most, and a "+" for more
  private lifted = new Sprite();   // what it has picked up to put away
  private ring = new Graphics();
  private lean = { x: 0, y: 0, t0: 0, until: 0 };
  private turned: Dir | null = null;
  private turnUntil = 0;
  private idle: { kind: "none" | "sit" | "mood" | "look"; until: number } = { kind: "none", until: 0 };
  private nextIdle = performance.now() + 1500 + Math.random() * 3000;
  private nextAir = 0;
  private t0 = Math.random() * 1000;
  private seen = "";
  private away = false;   // it has shifted off its tile to pass the time
  private move: Move | null = null;   // how what its body is doing looks
  private moveKey = "";
  private began = 0;
  private aim = [0, 0];               // what it is about, in the room's pixels
  private aimed = false;
  private aimAt = 0;
  private reacted = -1;
  private off = [0, 0, 0, 0];         // this frame: its body moved sideways and up, and the whole of it leaned
  private at = [0, 0];                // where it stands, less any lean

  constructor() {
    this.body.anchor.set(0.5, 1);
    this.rim.anchor.set(0.5, 1);
    this.rim.visible = false;
    this.lifted.anchor.set(0.5, 1);
    this.lifted.visible = false;
    for (const h of this.held) h.anchor.set(0.5, 1);
    this.c.addChild(this.ring, this.body, ...this.held, this.lifted);
  }

  /** A snapshot: who it is now, and the tile it should stand on. `ms`: how long a tick takes. `rest`: what its body
   *  is doing is done lying or sitting down. */
  update(p: PetV, home: Tile, st: Stage, ms: number, selected: boolean, first: boolean, rest = false) {
    const stage = bodyStage(p), b = p.asleep ? null : p.body ?? null, now = st.now;
    this.pet = p;
    this.P = petScale(st.K);
    this.c.scale.set(this.P);
    this.sheet = petSheet(p.genome, p.stage === "egg" ? "egg" : stage, { grey: stage === "elder" ? (p.old ? 0.85 : 0.55) : 0 });
    const key = b ? `${b.activity}|${b.what}|${b.who}` : "";
    if (key !== this.moveKey) {   // its body has turned to something else
      const m = b ? MOVES[b.activity] ?? MOVES[b.icon ?? ""] : null;
      this.move = !b ? null : rest && !(m && /^(sit|sleep)/.test(m.a)) ? REST : m ?? PLAIN;
      [this.moveKey, this.began, this.aimAt] = [key, now, 0];
      const t = this.move?.stir === 3 ? st.thing(b!.what) : null;
      this.lifted.texture = t ? t.texture : Texture.EMPTY;
      if (t) this.lifted.scale.set((t.scale * 0.8) / this.P);
    }
    if (!first && p.react && p.react.tick > this.reacted && !p.asleep) {   // stopped in its tracks: a start, or a turn to whoever it was
      if (p.react.kind === "startle") { this.react("startled", now, 750); st.fx.spawn("bang", this.w.x, this.w.y - this.tall - 5, { vy: -6, life: 800 }); }
      else [this.turned, this.turnUntil] = ["down", now + 1600];
    }
    this.reacted = p.react?.tick ?? this.reacted;
    // its body as it is drawn just now: lying asleep or dead it takes other room than standing
    const lying = p.asleep || (this.move?.a === "sleep" && !b?.walking);
    this.box = bodyBox(p.stage === "egg" ? this.sheet.egg[0] : p.stage === "dead" ? this.sheet.dead : lying ? this.sheet.frames.sleep[0] ?? this.sheet.frames.idle[0] : this.sheet.frames.idle[0]);
    const busy = !!doing(p) || !!b, moved = home[0] !== this.home[0] || home[1] !== this.home[1];
    this.home = home;
    if (first || p.stage === "egg" || p.stage === "dead") this.w.place(home);
    else if (moved || (busy && this.away && !this.w.moving)) {
      const here = this.w.tile(), far = Math.max(Math.abs(here[0] - home[0]), Math.abs(here[1] - home[1]));
      if (far > 7 && !moved) this.w.place(home);
      else this.w.go(home, st.blocked, moved ? ms : 700);
      this.away = false;
      this.idle.until = 0;
    }
    const look = `${selected}|${this.box.w}|${(p.carrying ?? []).join()}|${p.emote ?? ""}|${st.K}|${p.stage}`;
    if (look !== this.seen) {
      this.seen = look;
      const r = this.ring.clear(), hw = Math.ceil(this.box.w / 2) + 2, sw = Math.max(3, Math.floor(this.box.w / 2) - 1);
      if (p.stage !== "dead") r.rect(-sw, -2, 2 * sw, 3).rect(-sw + 2, -3, 2 * sw - 4, 1).rect(-sw + 2, 1, 2 * sw - 4, 1).fill({ color: 0x1a1420, alpha: 0.22 });   // its shadow on the floor
      if (selected) {   // who the page has chosen: a ring on the floor under it, in whole pixels
        r.rect(-hw + 2, -3, 2 * hw - 4, 1).rect(-hw + 2, 2, 2 * hw - 4, 1).rect(-hw, -1, 1, 2).rect(hw - 1, -1, 1, 2).rect(-hw + 1, -2, 1, 1).rect(hw - 2, -2, 1, 1).rect(-hw + 1, 1, 1, 1).rect(hw - 2, 1, 1, 1).fill(0xffb347);
      }
      const bits = p.carrying ?? [], small = Math.max(1, Math.round(st.K * 0.55)) / st.K / this.P;   // (what it carries stays the size it is on the floor)
      this.held.forEach((h, i) => {
        h.visible = i < 2 ? !!bits[i] : bits.length > 2;
        if (i < 2 && bits[i]) { h.texture = tex(`bit.${bits[i]}`); h.scale.set(small); }
      });
    }
  }

  /** What the thing its body is at should be doing meanwhile (see Move.stir), or 0. */
  get stirs() { const b = this.pet.body; return b && !b.walking && !this.pet.asleep && !this.w.moving ? this.move?.stir ?? 0 : 0; }

  /** Lean toward a point for a moment (a nuzzle, a gift held out). */
  leanTo(x: number, y: number, now: number, ms = 1500, far = 4) {
    const d = Math.hypot(x - this.w.x, y - this.w.y) || 1;
    this.lean = { x: ((x - this.w.x) / d) * far, y: ((y - this.w.y) / d) * far * 0.5, t0: now, until: now + ms };
    this.turn(x, y, now, ms);
  }
  /** Stand turned toward a point for a while. */
  turn(x: number, y: number, now: number, ms = 1500) {
    this.turned = this.toward(x, y);
    this.turnUntil = now + ms;
  }
  private toward(x: number, y: number): Dir {
    const dx = x - this.w.x, dy = y - this.w.y;
    return Math.abs(dx) >= Math.abs(dy) ? (dx < 0 ? "left" : "right") : dy < 0 ? "up" : "down";
  }
  react(a: PetAnim, now: number, ms = 900) {
    if (this.pet.asleep || this.pet.stage === "egg" || this.pet.stage === "dead") return;
    this.pose = { anim: a, until: now + ms };
  }

  /** Where its head is, and the whole of it, in the room's pixels: bubbles and plates keep clear of this. (Where it
   *  stands, not where a hop or a lean has it this instant: its plate and its bubbles hold still while it plays.) */
  rect(): Rect {
    const n = this.sheet.size, b = this.box, P = this.P;
    return { x: this.at[0] + (b.x - n / 2) * P, y: this.at[1] + (b.y - n) * P, w: b.w * P, h: b.h * P };
  }
  /** How far above its feet the top of its head is, in the room's pixels. */
  get tall() { return (this.sheet.size - this.box.y) * this.P; }

  /** Its pale outline, over the dark: the darker the room, the plainer. */
  private edge(st: Stage, frame: HTMLCanvasElement) {
    const on = st.dim > 0.14;
    this.rim.visible = on;
    if (!on) return;
    this.rim.texture = rimOf(frame);
    this.rim.alpha = this.c.alpha * clamp((st.dim - 0.1) * 4, 0, 0.8);
    this.rim.scale.set(this.P / 2);
    this.rim.position.set(this.c.x + this.body.x * this.P, this.c.y + (this.body.y + 0.5) * this.P);
  }

  step(st: Stage) {
    const p = this.pet, now = st.now, egg = p.stage === "egg", dead = p.stage === "dead", elder = p.stage === "elder";
    const d = doing(p), acting = !!d?.acting && !this.w.moving, b = p.asleep ? null : p.body ?? null, off = this.off;
    this.w.step(egg || dead ? 0 : st.dt);   // one that falls asleep on its way still gets to where it lies
    let a: PetAnim = "idle";
    off[0] = off[1] = off[2] = off[3] = 0;
    if (egg || dead) {
      this.c.alpha = dead ? 1 - 0.8 * (p.fade ?? 0) : 1;
      const rock = egg && (p.hatches_in ?? 99) < 20, frame = dead ? this.sheet.dead : this.sheet.egg[rock ? Math.floor(now / 160) % this.sheet.egg.length : 0];   // about to hatch: it rocks
      this.body.texture = texOf(frame);
      this.body.x = rock ? Math.round(Math.sin(now / 90)) : 0;
      this.c.position.set(this.w.x, this.w.y);
      this.at[0] = this.w.x; this.at[1] = this.w.y;
      this.c.zIndex = this.w.y;
      for (const h of this.held) h.visible = false;
      this.lifted.visible = false;
      this.edge(st, frame);
      return;
    }
    this.c.alpha = 1;
    const target = d ? (d.type === "ask_book" ? st.book() : null) ?? st.where(d.to, [this.w.x, this.w.y]) ?? st.where(d.what, [this.w.x, this.w.y]) : null;
    if (this.w.moving) a = `walk.${this.w.dir}`;
    else if (p.asleep) a = "sleep";
    else if (this.pose && now < this.pose.until) a = this.pose.anim;
    else if (acting) {
      const pose = this.eating ? "eat" : POSE[d!.type] ?? "idle";
      if (pose === "turn" || pose === "wall" || pose === "look") {   // stood turned to it, breathing
        const dir: Dir = pose === "wall" ? (target && Math.abs(target[0] - this.w.x) > Math.abs(target[1] - this.w.y) * 2 ? (target[0] < this.w.x ? "left" : "right") : target && target[1] > this.w.y + 4 ? "down" : "up")
          : pose === "look" ? (Math.floor(now / 900) % 2 ? "left" : "right") : target ? this.toward(target[0], target[1]) : "down";
        a = pose === "turn" ? `talk.${dir}` : `stand.${dir}`;
      } else a = pose;
    } else if (now < this.turnUntil && this.turned) a = `stand.${this.turned}`;
    else if (b && this.move) a = this.busy(st, b, this.move);
    else a = this.pass(st, !d);

    // what rises from it while it is busy, or asleep
    if (now > this.nextAir) {
      const top = this.w.y - this.tall;
      if (p.asleep) { st.fx.spawn("z", this.w.x + 7, top - 2, { vx: 2, vy: -3, life: 1900 }); this.nextAir = now + 2100; }
      else if (acting && AIR[d!.type]) {
        const [what, every] = AIR[d!.type], wall = d!.type === "write" || d!.type === "scrub" || d!.type === "ask_book";
        const at = wall && target ? [target[0] + (Math.random() - 0.5) * 8, target[1]] : [this.w.x + (Math.random() - 0.5) * 10, what === "note" ? top : this.w.y - 5];
        st.fx.spawn(what, at[0], at[1], what === "note" ? { vx: (Math.random() - 0.5) * 8, vy: -14, life: 1500, sway: 2 } : what === "grit" ? { vx: (Math.random() - 0.5) * 12, vy: 6, g: 20, life: 600 } : what === "chalk" ? { vy: 4, life: 500 }
          : { vx: (Math.random() - 0.5) * 14, vy: -12, life: 650 });
        this.nextAir = now + every;
      } else if (acting && this.eating) { st.fx.spawn("speck", this.w.x + (Math.random() - 0.5) * 6, this.w.y - 6, { vy: 8, g: 30, life: 400, tint: 0xd9b36a }); this.nextAir = now + 420; }
      else if (b && this.move?.air && !b.walking && !this.w.moving) {
        const [what, every, tint] = this.move.air, x = this.w.x + (Math.random() - 0.5) * 8;
        if (what === "z") st.fx.spawn("z", this.w.x + 7, top - 2, { vx: 2, vy: -3, life: 1900 });
        else if (what === "note" || what === "heart") st.fx.spawn(what, x, top - 2, { vx: (Math.random() - 0.5) * 6, vy: what === "heart" ? -7 : -14, life: 1600, sway: 2 });
        else if (what === "dust") st.fx.spawn("dust", x, this.w.y - 2, { life: 450 });
        else st.fx.spawn(what, x, this.w.y - this.tall / 2, { vx: (Math.random() - 0.5) * 10, vy: what === "speck" ? 8 : -8, g: what === "speck" ? 30 : 0, life: what === "speck" ? 400 : 900, sway: 1, tint });
        this.nextAir = now + every;
      } else this.nextAir = now + 200;
    }

    const frames = this.sheet.frames[a]?.length ? this.sheet.frames[a] : this.sheet.frames.idle, fps = (this.sheet.fps[a] ?? 2) * (elder ? 0.75 : 1);
    const frame = frames[Math.floor(((now + this.t0) / 1000) * fps) % frames.length], grain = st.K * this.P;   // (moved on whole screen pixels)
    this.body.texture = texOf(frame);
    this.body.position.set(Math.round(off[0] * grain) / grain, Math.round(off[1] * grain) / grain);
    const k = now < this.lean.until ? Math.sin(Math.min(1, (now - this.lean.t0) / (this.lean.until - this.lean.t0)) * Math.PI) : 0;
    const half = Math.ceil((this.box.w * this.P) / 2) + 1;   // in a doorway too it stays inside the walls
    this.at[0] = clamp(this.w.x, OX + half, OX + FX * TILE - half); this.at[1] = this.w.y;
    this.c.position.set(clamp(this.w.x + this.lean.x * k + off[2], OX + half, OX + FX * TILE - half), this.w.y + this.lean.y * k + off[3]);
    this.c.zIndex = this.w.y;
    this.edge(st, frame);
    const side = a === "walk.left" ? -1 : a === "walk.right" ? 1 : 0;
    // what it carries, at its side by its paws (never over its face)
    // small, down at its paws beside its body, never across its face; behind it when it walks away from us
    const hx = (side || 1) * (Math.ceil(this.box.w / 2) + 1), hy = -(a === "make" ? Math.floor(now / 250) % 2 : 0), n = (p.carrying ?? []).length;
    this.held[0].position.set(hx, hy);
    this.held[1].position.set(hx + (side || 1) * 4, hy);
    this.held[2].position.set(hx + (side || 1) * (n > 1 ? 7 : 4), hy - 2);
    this.held.forEach((h, i) => (h.visible = a !== "walk.up" && (i < 2 ? i < n : n > 2)));
    // what it has picked up to put away: held out at its other side, off the floor, bobbing
    this.lifted.visible = this.stirs === 3 && this.lifted.texture !== Texture.EMPTY;
    if (this.lifted.visible) this.lifted.position.set(-(Math.ceil(this.box.w / 2) + 3), -3 - Math.round(Math.abs(Math.sin((now - this.began) / 300)) * 2 * grain) / grain);
  }

  /** What its body is doing by itself (SPEC-v3.3 §1): on its way there it faces where it is going; there, the frames
   *  and the small motion that say what it is at (Move). The room's pixels it moves by go in `off`. */
  private busy(st: Stage, b: NonNullable<PetV["body"]>, m: Move): PetAnim {
    const now = st.now, off = this.off, low = this.pet.emote === "uneasy" || this.pet.emote === "lonely";
    if (b.walking) return b.goal ? `stand.${this.toward(OX + b.goal[0] * TILE + TILE / 2, OY + b.goal[1] * TILE + TILE - 3)}` : "idle";   // between two of the engine's steps
    if (now > this.aimAt) {   // what it is about may move (a creature, another pet): looked up a few times a second, not every frame
      this.aimAt = now + 300;
      const t = st.where(b.who, [this.w.x, this.w.y]) ?? st.where(b.what, [this.w.x, this.w.y]);
      this.aimed = !!t && Math.hypot(t[0] - this.w.x, t[1] - this.w.y) > 2;
      if (t) [this.aim[0], this.aim[1]] = t;
    }
    const t = now - this.began, ms = m.ms ?? 900, ax = this.aim[0], ay = this.aim[1], dist = this.aimed ? Math.hypot(ax - this.w.x, ay - this.w.y) : 0;
    if (m.sway) off[0] = Math.sin((t / ms) * Math.PI) * m.sway;
    if (m.hop) off[1] = -Math.abs(Math.sin((t / ms) * Math.PI)) * m.hop;
    if (m.lean && dist) { const k = (m.lean * (1 - Math.cos((t / ms) * Math.PI * 2))) / 2 / dist; off[2] = (ax - this.w.x) * k; off[3] = (ay - this.w.y) * k * 0.5; }
    const dir = this.aimed ? this.toward(ax, ay) : "down";
    return m.a === "face" ? `stand.${dir}` : m.a === "talk" ? `talk.${dir}` : m.a === "look" ? `stand.${ABOUT[Math.floor((t + this.t0 * 3) / 1100) % 4]}` : m.a === "idle" && low ? "sad" : m.a;
  }

  /** Between thoughts (§5.1): look about, glance at someone, sit a while, shift a tile if nothing holds it there. How
   *  it feels shows in how it holds itself (§5.3): drooping when uneasy or lonely, sat down when tired, a hop now and
   *  then when content. (A pet whose engine gives it a body is at something all the time: see `busy`.) */
  private pass(st: Stage, mayShift: boolean): PetAnim {
    const now = st.now, p = this.pet, low = p.emote === "uneasy" || p.emote === "lonely", rest: PetAnim = low ? "sad" : p.emote === "tired" ? "sit" : "idle";
    if (now < this.idle.until) return this.idle.kind === "sit" ? "sit" : this.idle.kind === "mood" ? "happy" : rest;
    if (now < this.nextIdle || st.held) return rest;
    this.nextIdle = now + 2600 + Math.random() * 4200;
    const r = Math.random(), others = st.others();
    if (p.emote === "content" && r < 0.45) this.idle = { kind: "mood", until: now + 1100 };
    else if (r < 0.34 && !low) {
      const o = others.length && Math.random() < 0.7 ? others[Math.floor(Math.random() * others.length)] : [this.w.x + (Math.random() < 0.5 ? -20 : 20), this.w.y];
      this.turn(o[0], o[1], now, 900 + Math.random() * 1300);
    } else if (r < 0.52 && mayShift && rest === "idle") {
      const h = this.home, back = this.away && Math.random() < 0.6;
      const spots: Tile[] = back ? [h] : ([[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, 1]] as Tile[]).map(([dx, dy]): Tile => [h[0] + dx, h[1] + dy]).filter((t) => st.free(t, p.id));
      const to = spots[Math.floor(Math.random() * spots.length)];
      if (to) { this.w.go(to, st.blocked, 1100, 1); this.away = !back; }
    } else if (r < 0.66 && rest === "idle") this.idle = { kind: "sit", until: now + 2500 + Math.random() * 3000 };
    return rest;
  }
}

/** A small creature: the pack's own frames, facing where it goes. A tame one carries a small flag in its pet's colour. */
export class CreatureActor {
  c = new Container();
  w = new Walker();
  cr!: Creature;
  private body = new Sprite();
  private flag = new Sprite(fxTexture("flag"));
  private carry = new Sprite();
  private name = "";
  private faced = "right";
  private t0 = Math.random() * 1000;

  constructor() {
    this.body.anchor.set(0.5, 1);
    this.flag.anchor.set(0, 1);
    this.carry.anchor.set(0.5, 1);
    this.c.addChild(this.body, this.flag, this.carry);
  }
  update(cr: Creature, st: Stage, ms: number, first: boolean, color: number | null) {
    this.name = `creature.${cr.kind}`;
    const moved = !this.cr || cr.pos[0] !== this.cr.pos[0] || cr.pos[1] !== this.cr.pos[1];
    this.cr = cr;
    if (first) this.w.place(cr.pos);
    else if (moved) this.w.go(cr.pos, st.blocked, ms, 4);
    this.c.scale.set(Math.max(1, Math.round(st.K * 0.7)) / st.K);   // small beside a pet, on whole pixels
    this.flag.visible = color != null;
    if (color != null) this.flag.tint = color;
    this.carry.visible = !!cr.carry;
    if (cr.carry) this.carry.texture = tex(`bit.${cr.carry}`);
  }
  rect(): Rect {
    const t = this.body.texture, k = this.c.scale.x;
    return { x: this.c.x - (t.width * k) / 2, y: this.c.y + (this.body.y - t.height) * k, w: t.width * k, h: t.height * k };
  }
  step(st: Stage) {
    this.w.step(st.dt);
    const n = this.name, dir = this.w.dir, flying = this.cr.kind === "moth" || this.cr.kind === "bird" && this.w.moving;
    // the frames it has for this: its own for the direction, the other side's mirrored, any walk, or standing
    let a: string | undefined, flip = false;
    if (this.w.moving && has(n)) {
      const other = dir === "left" ? "walk.right" : dir === "right" ? "walk.left" : null;
      if (anim(n, `walk.${dir}`)) a = `walk.${dir}`;
      else if (other && anim(n, other)) [a, flip] = [other, true];
      else a = anim(n, "walk") ? "walk" : anim(n, "walk.down") ? "walk.down" : undefined;
    }
    if (!a && anim(n, "idle")) [a, flip] = ["idle", this.faced === "left"];   // only one set of frames (drawn facing right): mirrored when it last went left
    if (dir === "left" || dir === "right") this.faced = dir;
    const an = a ? anim(n, a) : null;
    this.body.texture = tex(n, a, an ? Math.floor(((st.now + this.t0) / 1000) * an.fps) % an.frames.length : 0);
    this.body.scale.x = flip !== !!an?.flip ? -1 : 1;
    this.body.y = flying ? -7 + Math.round(Math.sin(st.now / 170 + this.t0) * 2) : 0;
    this.c.position.set(this.w.x + (flying ? Math.round(Math.sin(st.now / 230 + this.t0) * 2) : 0), this.w.y);
    this.c.zIndex = this.w.y - 1;
    const h = this.body.texture.height;
    this.flag.position.set(-this.body.texture.width / 2, this.body.y - h + 2);
    this.carry.position.set(0, this.body.y - h + 4);
  }
}
