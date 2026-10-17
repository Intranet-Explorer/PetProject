// SPEC-v3.6a §1, §2, §6: the pond. Its water is drawn in code from the snapshot's tiles (snap.pond.water), in a natural
// shape that keeps to the tiles' edges with rounded corners: a dark bank round it, shallow water lighter, deep water
// darker, light streaks drifting over it; in the frozen weeks ice over all of it, with a dark hole where one was cut.
// Under the water, about as many fish shadows as the pond has fish, gliding about; on it, lily pads; over it, the dock
// (pond32's planks and posts) once the Works has built it. Each hob fishing sits at its spot: with a rod, the rod held
// out, the line and the float drawn in code (the float bobs, dips when something bites, splashes when it is pulled up);
// by paw, a paw dangled at the edge; what came up held up over its head a moment, with a burst for a find.
import { Container, Graphics, Sprite } from "pixi.js";
import type { Texture } from "pixi.js";
import type { Fisher, Pond, RoomV, Snap, Tile } from "../types";
import { drawnOf } from "./still";
import { has, kind, size, tex, fromCanvas } from "./assets";
import type { Fx } from "./fx";
import { FX, FY, OX, OY, seeded, TILE } from "./geom";
import { REDUCE } from "./weather";

const PW = FX * TILE, PH = FY * TILE;   // the floor, in pixels: the water is drawn on it
const key = (t: Tile | number[]) => `${t[0]},${t[1]}`;
const rgb = (n: number) => [(n >> 16) & 255, (n >> 8) & 255, n & 255];
/** A hob as the pond needs to know it: where its feet are, how tall it stands, its coat. */
export type Who = { x: number; y: number; tall: number; coat: number };

/** This room's pond, if it has one: the snapshot's (SPEC-v3.6a), or the water of an older engine's pond fixture. */
export function pondOf(snap: Snap, room: RoomV): Pond | null {
  if (snap.pond && snap.pond.room === room.id) return snap.pond;
  const water = Object.values(room.objects).find((o) => o.water?.length)?.water;
  return water ? { room: room.id, water, dock: null, frozen: false, holes: [], stock: 0, most: 0, says: "", today: 0, fishers: [], catches: [] } : null;
}

/** The hobs' pond bridge (SPEC-v3.6a §1: "pond bridge", built, laid across the narrow neck of the water north to south):
 *  its column, and the tiles it runs over from bank to bank; null while there is none, or it is still being built. */
export function bridgeOf(p: Pond, room: RoomV): { name: string; x: number; y0: number; y1: number } | null {
  const hit = Object.entries(room.objects).find(([n, o]) => (n === "pond bridge" || o.build?.sprite === "fix.built.pond bridge") && o.build?.progress == null);
  if (!hit) return null;
  const [name, o] = hit, x = o.pos[0], wet = new Set(p.water.filter((t) => t[0] === x).map((t) => t[1]));
  if (!wet.size) return null;
  let y = [...wet].sort((a, b) => Math.abs(a - o.pos[1]) - Math.abs(b - o.pos[1]))[0], y0 = y;
  while (wet.has(y0 - 1)) y0--;
  while (wet.has(y + 1)) y++;
  return { name, x, y0: y0 - 1, y1: y + 1 };
}

/** The water tiles a hob can stand on just now: the dock's and the bridge's, and all of it while it is frozen. */
export function footing(p: Pond, room: RoomV): Tile[] {
  if (p.frozen) return p.water;
  const b = bridgeOf(p, room), out: Tile[] = [...(p.dock?.tiles ?? [])];
  if (b) for (let y = b.y0 + 1; y < b.y1; y++) out.push([b.x, y]);
  return out;
}

// ---- the water, drawn once for each shape ----

type Mask = { inside: Uint8Array; dist: Uint8Array };
/** Which pixels of the floor are water, and how far each is from the bank (1 at the edge, up to 12). The edge runs
 *  along the tiles' edges, the corners rounded and a pixel or two of wobble in it, the same for the same room. */
function maskOf(water: Tile[], seed: string): Mask {
  const wet = new Set(water.map(key)), occ = (x: number, y: number) => (wet.has(`${x},${y}`) ? 1 : 0), r = seeded(seed);
  const N = 8, noise = Array.from({ length: (PW / N + 2) * (PH / N + 2) }, () => (r() - 0.5) * 0.2), nw = PW / N + 2;
  const s = (t: number) => t * t * (3 - 2 * t), inside = new Uint8Array(PW * PH), dist = new Uint8Array(PW * PH);
  for (let y = 0; y < PH; y++) for (let x = 0; x < PW; x++) {
    const u = (x + 0.5) / TILE - 0.5, v = (y + 0.5) / TILE - 0.5, i = Math.floor(u), j = Math.floor(v), su = s(u - i), sv = s(v - j);
    const f = (occ(i, j) * (1 - su) + occ(i + 1, j) * su) * (1 - sv) + (occ(i, j + 1) * (1 - su) + occ(i + 1, j + 1) * su) * sv;
    const a = x / N, b = y / N, ia = Math.floor(a), ib = Math.floor(b), fa = a - ia, fb = b - ib, n = (k: number, l: number) => noise[l * nw + k];
    const wob = (n(ia, ib) * (1 - fa) + n(ia + 1, ib) * fa) * (1 - fb) + (n(ia, ib + 1) * (1 - fa) + n(ia + 1, ib + 1) * fa) * fb;
    inside[y * PW + x] = f > 0.5 + wob ? 1 : 0;
  }
  // how far from the bank: a few rounds of growing in from the edge
  const q: number[] = [];
  for (let i = 0; i < PW * PH; i++) if (inside[i]) {
    const x = i % PW, y = (i / PW) | 0;
    if (x === 0 || y === 0 || x === PW - 1 || y === PH - 1 || !inside[i - 1] || !inside[i + 1] || !inside[i - PW] || !inside[i + PW]) { dist[i] = 1; q.push(i); }
  }
  for (let h = 0; h < q.length; h++) {
    const i = q[h], d = dist[i];
    if (d >= 12) continue;
    for (const k of [i - 1, i + 1, i - PW, i + PW]) if (k >= 0 && k < PW * PH && inside[k] && !dist[k]) { dist[k] = d + 1; q.push(k); }
  }
  return { inside, dist };
}

const BANK = 0x2c4a2e, SHADE = 0x2e6690, EDGE = 0x5fa8d0, SHALLOW = 0x4b93c4, MID = 0x3f84b8, DEEP = 0x387aae, LIP = 0x9ed3ea, FLECK = 0x4a90c2;
const STREAK = [0x79bde0, 0xa8dcf0, 0x79bde0];
const ICE = 0xcde7f2, ICE_EDGE = 0xeef8fc, ICE_SHADE = 0xb4d4e4, ICE_LIGHT = 0xe2f2f8, CRACK = 0x93bdd2, HOLE = 0x183449, HOLE_RIM = 0x6f9db6;

/** One picture of the floor's size: the bank round the water and, inside, `paint` for each pixel of water. */
function picture(m: Mask, paint: (x: number, y: number, d: number, shade: boolean, lip: boolean) => number | null): HTMLCanvasElement {
  const c = Object.assign(document.createElement("canvas"), { width: PW, height: PH }), x2 = c.getContext("2d")!, im = x2.createImageData(PW, PH), d = im.data;
  const put = (i: number, col: number, a = 255) => { const [r, g, b] = rgb(col); d[i * 4] = r; d[i * 4 + 1] = g; d[i * 4 + 2] = b; d[i * 4 + 3] = a; };
  const at = (x: number, y: number) => x >= 0 && y >= 0 && x < PW && y < PH && m.inside[y * PW + x] === 1;
  for (let y = 0; y < PH; y++) for (let x = 0; x < PW; x++) {
    const i = y * PW + x;
    if (!m.inside[i]) {   // the bank: a dark line round the water, a shadow of it a pixel further out
      if (at(x - 1, y) || at(x + 1, y) || at(x, y - 1) || at(x, y + 1)) put(i, BANK);
      else if (at(x - 2, y) || at(x + 2, y) || at(x, y + 2) || at(x - 1, y - 1) || at(x + 1, y - 1) || at(x - 1, y + 1) || at(x + 1, y + 1)) put(i, BANK, 70);
      continue;
    }
    const shade = !at(x, y - 1) || !at(x, y - 2) || !at(x, y - 3), lip = !at(x, y + 1), col = paint(x, y, m.dist[i], shade, lip);
    if (col != null) put(i, col);
  }
  x2.putImageData(im, 0, 0);
  return c;
}

type Look = { frames: Texture[]; ice: Texture; deep: number[]; isDeep: Uint8Array };
const looks = new Map<string, Look>();
/** The water in four frames of its drifting streaks, and the ice with its holes: made once for each shape. */
function lookOf(p: Pond, seed: string): Look {
  const k = JSON.stringify([p.water, p.holes, seed]);
  let l = looks.get(k);
  if (l) return l;
  const m = maskOf(p.water, seed), r = seeded(seed + "streaks"), deep: number[] = [];
  const isDeep = new Uint8Array(PW * PH);
  for (let i = 0; i < PW * PH; i++) if (m.dist[i] >= 3) { deep.push(i); isDeep[i] = 1; }
  const flecks = new Set<number>(), streaks: [number, number, number][] = [];
  for (const i of deep) if (r() < 0.02) flecks.add(i);
  for (let n = 0; n < Math.max(6, Math.round(deep.length / 110)); n++) { const i = deep[Math.floor(r() * deep.length)]; streaks.push([i % PW, (i / PW) | 0, 2 + Math.floor(r() * 3)]); }
  const water = (x: number, y: number, d: number, shade: boolean, lip: boolean) =>
    shade ? SHADE : lip ? LIP : flecks.has(y * PW + x) ? FLECK : d <= 1 ? EDGE : d <= 3 ? SHALLOW : d <= 6 ? MID : DEEP;
  const frames = [0, 1, 2, 3].map((f) => {
    const lit = new Map<number, number>();
    streaks.forEach(([sx, sy, len], i) => {   // each streak drifts a pixel a frame, waxing and waning, one frame in four gone
      const ph = (f + i) % 4;
      if (ph === 3) return;
      for (let j = 0; j < len - (ph === 2 ? 1 : 0); j++) { const x = sx + ph - 1 + j; if (x >= 0 && x < PW && m.dist[sy * PW + x] >= 2) lit.set(sy * PW + x, STREAK[ph]); }
    });
    return fromCanvas(picture(m, (x, y, d, shade, lip) => lit.get(y * PW + x) ?? water(x, y, d, shade, lip)));
  });
  // the ice: pale, frost at its edge, long faint streaks of light, a few cracks; a dark round of open water at each hole
  const cr = seeded(seed + "cracks"), crack = new Set<number>();
  for (let n = 0; n < Math.max(3, Math.round(deep.length / 500)); n++) {
    let i = deep[Math.floor(cr() * deep.length)], x = i % PW, y = (i / PW) | 0;
    const dx = cr() < 0.5 ? -1 : 1;
    for (let s = 0; s < 6 + cr() * 10; s++) { crack.add(y * PW + x); x += cr() < 0.7 ? dx : 0; y += cr() < 0.5 ? 1 : 0; i = y * PW + x; if (!m.inside[i]) break; }
  }
  const holes = p.holes.map((t) => [t[0] * TILE + 8, t[1] * TILE + 8]);
  const ice = fromCanvas(picture(m, (x, y, d, shade) => {
    for (const [hx, hy] of holes) {
      const e = ((x + 0.5 - hx) / 5) ** 2 + ((y + 0.5 - hy) / 3.6) ** 2;
      if (e < 0.62) return HOLE;
      if (e < 1) return HOLE_RIM;
      if (e < 1.5 && y < hy) return ICE_EDGE;
    }
    return crack.has(y * PW + x) ? CRACK : d <= 1 ? ICE_EDGE : shade ? ICE_SHADE : (x + 2 * y) % 29 < 2 ? ICE_LIGHT : ICE;
  }));
  looks.set(k, (l = { frames, ice, deep, isDeep }));
  return l;
}

// ---- fish shadows ----

const FISH = ["#..####..", ".#######.", "#..####.."];   // facing right, its tail at the left
let fishTex: Texture | null = null;
function fishTexture() {
  if (fishTex) return fishTex;
  const c = Object.assign(document.createElement("canvas"), { width: 9, height: 3 }), x = c.getContext("2d")!;
  x.fillStyle = "#16324a";
  FISH.forEach((row, y) => [...row].forEach((ch, i) => ch === "#" && x.fillRect(i, y, 1, 1)));
  return (fishTex = fromCanvas(c));
}
type FishV = { s: Sprite; x: number; y: number; a: number; v: number; dart: number; next: number };

// ---- a hob fishing ----

type Line = { f: Fisher; c: Container; g: Graphics; held: Sprite; cast: number; castAt: number; biteAt: number; pulledAt: number; seenPulled: boolean; landed: boolean; t: number };
const TIER_SPARKS: Record<string, number> = { uncommon: 5, rare: 9, "very rare": 14 };

/** What of the pond holds still between redraws of the room (Still builds it): the water (or the ice), the lilies, the
 *  dock; `under` and `over` are where the moving parts go (the fish under the lilies, the floats over all). */
export class PondWater {
  c = new Container();
  under = new Container();
  over = new Container();
  look: Look;
  private water = new Sprite();
  constructor(readonly p: Pond, room: RoomV, seed: string) {
    this.look = lookOf(p, seed);
    this.c.position.set(OX, OY);
    this.water.texture = p.frozen ? this.look.ice : this.look.frames[0];
    this.c.addChild(this.water, this.under);
    if (!p.frozen) this.lilies(p, room, seed);
    if (p.dock && p.dock.tiles.length) this.dock(p.dock.tiles, p.dock.end);
    this.c.addChild(this.over);
  }
  /** Every frame: the streaks drift. */
  frame(now: number) {
    if (!this.p.frozen) this.water.texture = this.look.frames[Math.floor(now / (REDUCE.matches ? 1000 : 340)) % 4];
  }

  /** Lily pads on the open water, off the dock and the bridge: the same for the same room. */
  private lilies(p: Pond, room: RoomV, seed: string) {
    const wet = new Set(p.water.map(key)), busy = new Set([...footing(p, room), ...(p.dock?.tiles ?? [])].map(key)), r = seeded(seed + "lilies");
    const open = p.water.filter((t) => !busy.has(key(t)) && [[1, 0], [-1, 0], [0, 1], [0, -1]].filter(([dx, dy]) => wet.has(`${t[0] + dx},${t[1] + dy}`)).length >= 3);
    for (let i = open.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [open[i], open[j]] = [open[j], open[i]]; }
    const pick = ["pond.lily", "pond.lily.pad", "pond.lily", "pond.lily.pad", "pond.lily.flower", "pond.lily.pad"].slice(0, Math.max(2, Math.round(p.water.length / 5)));
    pick.forEach((name, i) => {
      const t = open[i];
      if (!t || !has(name)) return;
      const sz = size(name), s = new Sprite(tex(name));
      s.position.set(Math.round(t[0] * TILE + 8 - sz.w / 2 + (r() - 0.5) * 6), Math.round(t[1] * TILE + 8 - sz.h / 2 + (r() - 0.5) * 4));
      this.c.addChild(s);
    });
  }

  /** The dock from the walkway out over the water: its foot on the bank, planks, its end with the posts. */
  private dock(tiles: Tile[], end: Tile) {
    const far = tiles.reduce((a, t) => (Math.abs(t[0] - end[0]) + Math.abs(t[1] - end[1]) > Math.abs(a[0] - end[0]) + Math.abs(a[1] - end[1]) ? t : a), end);
    const len = (Math.abs(far[0] - end[0]) + Math.abs(far[1] - end[1]) + 1) * TILE, d = new Container();
    // laid out running north from (0, 0), the far edge of its end; then turned to run the way it does
    const put = (name: string, y: number) => { const s = new Sprite(tex(name)); s.position.set(-12, y); d.addChild(s); };
    for (let y = 6; y < len - 10; y += 8) put("pond.dock.planks", y);
    put("pond.dock.foot", len - 10);
    put("pond.dock.end", -2);
    const [dx, dy] = [Math.sign(end[0] - far[0]), Math.sign(end[1] - far[1]) || (end === far ? -1 : 0)];
    d.rotation = dx > 0 ? Math.PI / 2 : dx < 0 ? -Math.PI / 2 : dy > 0 ? Math.PI : 0;
    d.position.set(end[0] * TILE + 8 + dx * 8, end[1] * TILE + 8 + dy * 8);
    this.c.addChild(d);
  }
}

/** The pond's moving life, kept for as long as the room is looked at (the room is redrawn under it whenever something
 *  in it changes): the fish, the floats and rings, each fisher's rod, line and catch, the glints and the rain. */
export class Fishing {
  /** Each fisher's rod and line and the catch it holds up, sorted among the hobs: the room adds them as they come. */
  onAdd: (c: Container) => void = () => {};
  private fishC = new Container();
  private floats = new Graphics();
  private fish: FishV[] = [];
  private lines = new Map<string, Line>();
  private pond: Pond | null = null;
  private look: Look | null = null;
  private next = { glint: 0, rain: 0 };
  private fresh = true;

  /** The room has been drawn again: the fish go back under its lilies, the floats over its water. */
  attach(w: PondWater) {
    this.look = w.look;
    w.under.addChild(this.fishC);
    w.over.addChild(this.floats);
    for (const f of this.fish) if (!deepAt(w.look, Math.round(f.x), Math.round(f.y))) this.place(f);   // (the water has changed shape under it)
  }
  detach() { this.fishC.removeFromParent(); this.floats.removeFromParent(); }
  private place(f: FishV) {
    const d = this.look?.deep ?? [], i = d.length ? d[Math.floor(Math.random() * d.length)] : 0;
    [f.x, f.y] = [i % PW, (i / PW) | 0];
  }

  /** A snapshot: the fish to match the stock, the fishers and what each has just done. */
  update(p: Pond, now: number) {
    this.pond = p;
    const want = p.frozen || !this.look ? 0 : Math.min(16, Math.max(0, Math.round(p.stock)));
    while (this.fish.length > want) this.fish.pop()!.s.destroy();
    while (this.fish.length < want) {
      const s = new Sprite(fishTexture()), f: FishV = { s, x: 0, y: 0, a: Math.random() * Math.PI * 2, v: 3 + Math.random() * 5, dart: 0, next: now + Math.random() * 3000 };
      s.anchor.set(0.5);
      s.alpha = 0.5;
      this.fishC.addChild(s);
      this.place(f);
      this.fish.push(f);
    }
    const seen = new Set<string>();
    for (const f of p.fishers) {
      seen.add(f.pet);
      let l = this.lines.get(f.pet);
      if (!l) {
        const c = new Container(), g = new Graphics(), held = new Sprite();
        held.anchor.set(0.5, 1);
        held.visible = false;
        c.addChild(g, held);
        // one first seen as the room comes into view is not seen to cast again, nor to splash what it pulled up a while ago
        this.lines.set(f.pet, (l = { f, c, g, held, cast: f.cast, castAt: this.fresh ? -1e9 : now, biteAt: f.bite != null ? now - 400 : 0, pulledAt: f.pulled != null && this.fresh ? -1e9 : 0,
                                    seenPulled: f.pulled != null && this.fresh, landed: this.fresh, t: Math.random() * 1000 }));
        this.onAdd(c);
      }
      if (f.cast !== l.cast) Object.assign(l, { cast: f.cast, castAt: now, biteAt: 0, pulledAt: 0, seenPulled: false, landed: false });
      if (f.bite != null && !l.biteAt) l.biteAt = now;
      if (f.bite == null) l.biteAt = 0;
      if (f.pulled != null && !l.seenPulled) { l.pulledAt = now; l.seenPulled = true; }
      l.f = f;
    }
    for (const [id, l] of this.lines) if (!seen.has(id)) { l.c.destroy({ children: true }); this.lines.delete(id); }
    this.fresh = false;
  }

  /** Every frame. `who`: where a hob is, by its id (null if it is not in this room). */
  frame(now: number, dt: number, snap: Snap, fx: Fx, who: (id: string) => Who | null, K: number, catchOf: (c: NonNullable<Fisher["caught"]>) => Texture | null) {
    const p = this.pond, look = this.look, calm = REDUCE.matches ? 3 : 1;
    if (!p || !look) return;
    // the fish: each glides on, turning where the water gives out, now and then darting
    for (const f of this.fish) {
      if (now > f.next) { f.next = now + 1500 + Math.random() * 4000; f.a += (Math.random() - 0.5) * 1.6; f.dart = Math.random() < 0.15 ? now + 500 : 0; f.v = 3 + Math.random() * 5; }
      const v = (now < f.dart ? 22 : f.v) / calm, nx = f.x + Math.cos(f.a) * v * (dt / 1000), ny = f.y + Math.sin(f.a) * v * 0.6 * (dt / 1000);
      if (deepAt(look, Math.round(nx), Math.round(ny))) [f.x, f.y] = [nx, ny];
      else f.a += Math.PI * (0.6 + Math.random() * 0.8);
      f.s.position.set(Math.round(f.x), Math.round(f.y));
      f.s.scale.x = Math.cos(f.a) >= 0 ? 1 : -1;
    }
    // glints on the water, and rings where the rain falls on it
    const spot = () => { const i = look.deep.length ? look.deep[Math.floor(Math.random() * look.deep.length)] : 0; return [OX + (i % PW) + 0.5, OY + ((i / PW) | 0) + 0.5]; };
    if (!p.frozen && now > this.next.glint) {
      this.next.glint = now + 700 * calm;
      for (let n = 0; n < 2; n++) { const [x, y] = spot(); fx.spawn("glint", x, y, { life: 600, alpha: 0.7 }); }
    }
    if (!p.frozen && (snap.weather === "rain" || snap.weather === "storm") && now > this.next.rain) {
      this.next.rain = now + 300 * calm;
      for (let n = 0; n < Math.round((p.water.length * 0.25) / calm); n++) { const [x, y] = spot(); fx.spawn("rain.splash", x, y, { life: 380, tint: 0xd8f0ff, alpha: 0.8 }); }
    }
    // the fishers
    const g0 = this.floats.clear(), thin = Math.max(1, Math.round(K / 2)) / K;
    for (const l of this.lines.values()) {
      const f = l.f, h = who(f.pet);
      l.c.visible = !!h;
      if (!h) continue;
      const g = l.g.clear(), fl = [OX + f.line[0] * TILE + 8, OY + f.line[1] * TILE + 9];
      // a float straight behind a hob would be hidden by it: it lies out to one side, as far as the water there allows
      const side = fl[0] > h.x + 2 ? 1 : fl[0] < h.x - 2 ? -1 : deepAt(look, fl[0] - OX + 11, fl[1] - OY) || !deepAt(look, fl[0] - OX - 11, fl[1] - OY) ? 1 : -1;
      if (f.rod && !p.frozen && Math.abs(fl[0] - h.x) < 11 && fl[1] < h.y) for (const k of [12, 10, 8, 6, 4]) if (deepAt(look, Math.round(h.x + side * k - OX), Math.round(fl[1] - OY))) { fl[0] = h.x + side * k; break; }
      const paw = [h.x + side * 6, h.y - Math.round(h.tall * 0.3)], edge = [(OX + f.spot[0] * TILE + 8 + fl[0]) / 2, (OY + f.spot[1] * TILE + 9 + fl[1]) / 2];
      l.c.zIndex = h.y + 0.5;
      const sinceCast = now - l.castAt, sincePull = l.pulledAt ? now - l.pulledAt : Infinity, biting = !!l.biteAt && !l.pulledAt;
      if (f.rod) {
        let [dx, dy] = [fl[0] - paw[0], fl[1] - paw[1]];
        const n = Math.hypot(dx, dy) || 1;
        [dx, dy] = [dx / n, dy / n];
        const up = sincePull < 900 ? 5 : biting ? 2 : 0;   // (raised as it pulls, bent a little as something bites)
        const tip = [paw[0] + side * 7 + dx * 5, paw[1] - 13 + dy * 3 - up];   // (held out and up, toward the float)
        g.moveTo(paw[0], paw[1]).lineTo(tip[0], tip[1]).stroke({ width: 1, color: 0x3a2414 }).moveTo(paw[0], paw[1]).lineTo(tip[0], tip[1]).stroke({ width: thin, color: 0xa8743e });
        g.rect(Math.round(tip[0]) - 0.5, Math.round(tip[1]) - 0.5, 1, 1).fill(0xe8d2a0);
        // where the float is: flying out as it is cast, on the water bobbing (under as something bites), flying back as it is pulled
        let at: number[] | null = fl, arc = 0;
        if (sinceCast < 600) { const k = sinceCast / 600; at = [tip[0] + (fl[0] - tip[0]) * k, tip[1] + (fl[1] - tip[1]) * k]; arc = Math.sin(k * Math.PI) * 10; }
        else if (!l.landed) { l.landed = true; fx.spawn("rain.splash", fl[0], fl[1], { life: 360, tint: 0xe8f6ff }); }
        if (l.pulledAt) {
          if (sincePull < 500) { const k = sincePull / 500; at = [fl[0] + (tip[0] - fl[0]) * k, fl[1] + (tip[1] - fl[1]) * k]; arc = Math.sin(k * Math.PI) * 8; }
          else at = null;
        }
        if (at) {
          const [x, y] = [at[0], at[1] - arc], mid = [(tip[0] + x) / 2, Math.max(tip[1], y) + (arc ? -2 : 4)];
          g.moveTo(tip[0], tip[1]).quadraticCurveTo(mid[0], mid[1], x, y).stroke({ width: thin, color: 0xf2f6f4, alpha: 0.8 });
          if (arc) bob(g, x, y, false, now, l.t);   // (in the air: drawn with the line, over everything)
          else bob(g0, x - OX, y - OY, biting, now, l.t);
        }
      } else {   // by paw: an arm down to the water at the edge, and rings round it
        const dip = biting ? Math.round(Math.sin(now / 70)) : 0;
        g.moveTo(paw[0], paw[1]).lineTo(edge[0], edge[1] + dip).stroke({ width: 2, color: 0x2b2233 }).moveTo(paw[0], paw[1]).lineTo(edge[0], edge[1] + dip).stroke({ width: 1, color: h.coat });
        g.rect(Math.round(edge[0]) - 1.5, Math.round(edge[1] + dip) - 1, 3, 2).fill(h.coat);
        if (!l.pulledAt || sincePull > 900) rings(g0, edge[0] - OX, edge[1] - OY + 1, now, l.t, biting ? 500 : 1500);
      }
      // pulled up: a splash, and what came up held up over its head a moment (a burst for a find)
      if (l.pulledAt > 0 && sincePull < 30 + dt) {
        const [sx, sy] = f.rod ? fl : edge;
        fx.spawn("rain.splash", sx, sy, { life: 420, tint: 0xe8f6ff });
        for (let i = 0; i < 6; i++) fx.spawn("drop", sx + (Math.random() - 0.5) * 4, sy - 2, { vx: (Math.random() - 0.5) * 34, vy: -28 - Math.random() * 22, g: 140, life: 520, tint: 0xd8f0ff });
        const tier = f.caught?.tier ?? "common", n = TIER_SPARKS[tier];
        if (n) fx.after(500, () => { fx.burst("sparkle", h.x, h.y - h.tall - 8, n, tier === "uncommon" ? 20 : 30); if (tier !== "uncommon") fx.burst("glint", h.x, h.y - h.tall - 8, 6, 26, { tint: 0xffe28a }); });
      }
      const pic = f.caught && sincePull > 450 && sincePull < 3000 ? catchOf(f.caught) : null;
      l.held.visible = !!pic;
      if (pic) {
        l.held.texture = pic;
        const k = Math.min(1, (sincePull - 450) / 250);
        l.held.position.set(Math.round(h.x + side * 9), Math.round(h.y - h.tall * 0.45 - k * 6 + (Math.floor(now / 300) % 2 ? 0 : -1)));   // (held up beside its head: its name is over it)
      }
    }
  }

  destroy() {
    for (const l of this.lines.values()) l.c.destroy({ children: true });
    this.fishC.destroy({ children: true });
    this.floats.destroy();
  }
}

/** The float: red over white, a ring round it now and then; under as something bites, the water ringing round it. */
function bob(g: Graphics, x: number, y: number, under: boolean, now: number, t: number) {
  const b = under ? 2 : Math.sin((now + t) / 520) > 0.3 ? 1 : 0, [fx, fy] = [Math.round(x), Math.round(y)];
  rings(g, fx + 0.5, fy + 1, now, t, under ? 450 : 1800);
  if (under && Math.floor(now / 160) % 3 === 0) return;   // (pulled right under, for a blink)
  g.rect(fx - 1, fy - 3 + b, 3, under ? 1 : 2).fill(0xe0403a).rect(fx, fy - 4 + b, 1, 1).fill(0xf4f0e4);
  if (!under) g.rect(fx - 1, fy - 1 + b, 3, 1).fill(0xf4f0e4);
}
function rings(g: Graphics, x: number, y: number, now: number, t: number, every: number) {
  const k = ((now + t) % every) / every;
  g.ellipse(x, y, 2 + k * 5, 1 + k * 2.2).stroke({ width: 0.6, color: 0xdff2fb, alpha: 0.75 * (1 - k) });
}

/** Is a floor pixel well out on the water (three pixels or more from the bank), where a fish can swim. */
const deepAt = (l: Look, x: number, y: number) => x >= 0 && y >= 0 && x < PW && y < PH && l.isDeep[y * PW + x] === 1;

/** What came up, as it is held up: the thing made of it if it is one (a find), else the bit, else the kind it is. */
export function catchPicture(c: NonNullable<Fisher["caught"]>, room: RoomV): Texture | null {
  const made = c.thing ? room.objects[c.thing]?.made : null;
  if (made) return tex(drawnOf(made).sprite);
  const words = c.what.toLowerCase().replace(/^(a|an|the|some) /, ""), last = words.split(" ").at(-1) ?? words;
  for (const n of [`bit.${words}`, `kind.${words}`, kind(words)?.sprite, `bit.${last}`, `kind.${last}`]) if (has(n)) return tex(n!);
  return null;
}
