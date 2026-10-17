// SPEC-v3.5.12 §3, §5: the rail in a room and the little train on it. The track is drawn in code to fit the floor (two
// rails on sleepers, rounded where a branch turns, a buffer stop past the platform at a dead end), with the platform's
// slab beside it; the train is three cars (engine, cart, tram), each gliding along the track from the tile it stood on
// to the tile it stands on now, round the corners and in and out at the doors. Like the sweeper it drives in the drive
// frames of the nearest of its four ways and stands in the still of the eight; the engine puffs, the tram rings its
// bell at a stop, the cart's lid is up while it stands, and a hob riding stands on the tram's back step.
import { Container, Graphics, Sprite } from "pixi.js";
import type { Texture } from "pixi.js";
import type { Car, Creature, RailRoom, RoomV, Snap, Tile } from "../types";
import { anim, canvasOf, fromCanvas, tex } from "./assets";
import type { Fx } from "./fx";
import { clamp, FX, FY, H, OX, OY, TILE, W } from "./geom";
import type { Rect } from "./geom";
import { REDUCE } from "./weather";

export const OUT: Record<string, Tile> = { north: [0, -1], south: [0, 1], west: [-1, 0], east: [1, 0] };
const COMPASS = ["south", "south-east", "east", "north-east", "north", "north-west", "west", "south-west"];
const CARDINAL: Record<number, string> = { 0: "walk.down", 2: "walk.right", 4: "walk.up", 6: "walk.left" };
const compass = (dx: number, dy: number) => (Math.round(Math.atan2(dx, dy) / (Math.PI / 4)) + 8) % 8;
const same = (a: Tile | number[], b: Tile | number[]) => a[0] === b[0] && a[1] === b[1];
const key = (t: Tile | number[]) => `${t[0]},${t[1]}`;
const CARS = ["creature.train", "creature.train.cart", "creature.train.tram"];
const R = 8;   // a corner's radius: half a tile

/** The way along the track through tile centres (tile units; a tile off the floor is outside a door), as points one
 *  pixel apart in the room's pixels, each corner rounded. `at[j]`: the index of the point standing for tile j. `arc[i]`:
 *  0 on a straight, else how far into its corner the point is (1 to 13). */
export function lay(tiles: Tile[]): { p: number[]; at: number[]; arc: number[] } {
  const c = tiles.map((t) => [OX + t[0] * TILE + TILE / 2, OY + t[1] * TILE + TILE / 2]), p: number[] = [], arc: number[] = [], at: number[] = [];
  if (!c.length) return { p, at, arc };
  let [x, y] = c[0];
  p.push(x, y); arc.push(0); at.push(0);
  const to = (tx: number, ty: number) => {   // straight on, a pixel at a time
    const n = Math.round(Math.hypot(tx - x, ty - y));
    for (let i = 1; i <= n; i++) { p.push(x + ((tx - x) * i) / n, y + ((ty - y) * i) / n); arc.push(0); }
    [x, y] = [tx, ty];
  };
  for (let j = 1; j < c.length; j++) {
    const [cx, cy] = c[j], din = [Math.sign(cx - c[j - 1][0]), Math.sign(cy - c[j - 1][1])], nx = c[j + 1];
    const dout = nx ? [Math.sign(nx[0] - cx), Math.sign(nx[1] - cy)] : din;
    if (din[0] * dout[0] + din[1] * dout[1] === 0 && (din[0] || din[1]) && (dout[0] || dout[1])) {   // a quarter turn: round it
      to(cx - din[0] * R, cy - din[1] * R);
      const ox = cx - din[0] * R + dout[0] * R, oy = cy - din[1] * R + dout[1] * R, a0 = Math.atan2(y - oy, x - ox);
      let da = Math.atan2(cy + dout[1] * R - oy, cx + dout[0] * R - ox) - a0;
      if (da > Math.PI) da -= 2 * Math.PI;
      if (da < -Math.PI) da += 2 * Math.PI;
      for (let i = 1; i <= 13; i++) { p.push(ox + Math.cos(a0 + (da * i) / 13) * R, oy + Math.sin(a0 + (da * i) / 13) * R); arc.push(i); if (i === 7) at.push(p.length / 2 - 1); }
      [x, y] = [cx + dout[0] * R, cy + dout[1] * R];
    } else { to(cx, cy); at.push(p.length / 2 - 1); }
  }
  return { p, at, arc };
}

/** A point along a laid way, `s` pixels from its start (held at the ends), and the way it runs there. */
function along(w: number[], s: number): [number, number, number, number] {
  const n = w.length / 2 - 1, i = clamp(Math.floor(s), 0, Math.max(0, n - 1)), f = clamp(s - i, 0, 1), j = Math.min(n, i + 1);
  const x = w[2 * i] + (w[2 * j] - w[2 * i]) * f, y = w[2 * i + 1] + (w[2 * j + 1] - w[2 * i + 1]) * f;
  const a = Math.max(0, i - 2), b = Math.min(n, i + 3);
  return [x, y, w[2 * b] - w[2 * a], w[2 * b + 1] - w[2 * a + 1]];
}

/** The track as a graph of tiles: each branch's steps, and from each door tile on out through the wall a few tiles. */
function graph(rr: RailRoom, doors: Record<string, Tile>) {
  const g = new Map<string, Tile[]>(), link = (a: Tile, b: Tile) => {
    for (const [u, v] of [[a, b], [b, a]]) { const l = g.get(key(u)) ?? []; if (!l.some((t) => same(t, v))) l.push(v); g.set(key(u), l); }
  };
  for (const b of rr.track) {
    for (let i = 1; i < b.length; i++) link(b[i - 1], b[i]);
    const d = doorAt(b[0], doors);
    if (d) for (let k = 0; k < 3; k++) link([b[0][0] + OUT[d][0] * k, b[0][1] + OUT[d][1] * k], [b[0][0] + OUT[d][0] * (k + 1), b[0][1] + OUT[d][1] * (k + 1)]);
  }
  return g;
}
const doorAt = (t: Tile, doors: Record<string, Tile>) => Object.entries(doors).find(([, d]) => same(d, t))?.[0];
/** The tiles from `a` to `b` along the track (the shortest way), or straight there if the track does not join them. */
function way(g: Map<string, Tile[]>, a: Tile, b: Tile): Tile[] {
  const from = new Map<string, Tile | null>([[key(a), null]]), q: Tile[] = [a];
  while (q.length) {
    const t = q.shift()!;
    if (same(t, b)) { const out: Tile[] = []; for (let u: Tile | null = t; u; u = from.get(key(u)) ?? null) out.unshift(u); return out; }
    for (const n of g.get(key(t)) ?? []) if (!from.has(key(n))) { from.set(key(n), t); q.push(n); }
  }
  return same(a, b) ? [a] : [a, b];
}
/** The next tile on from `t`, coming from `from`: straight ahead if the track goes on there, else its only other way. */
function beyond(g: Map<string, Tile[]>, t: Tile, from: Tile | undefined): Tile | null {
  const ns = (g.get(key(t)) ?? []).filter((n) => !from || !same(n, from));
  return (from && ns.find((n) => same(n, [2 * t[0] - from[0], 2 * t[1] - from[1]]))) ?? (ns.length === 1 ? ns[0] : null);
}

// ---- the track, once per room as it is built ----

const SLEEPER = [122, 82, 50], SLEEPER_DARK = [74, 50, 32], RAIL = [190, 196, 204], RAIL_DARK = [72, 74, 84];
const SLAB = [188, 176, 156], SLAB_DARK = [110, 100, 88], EDGE = [232, 197, 71];

/** The room's track and its platform's slab, as one picture of the room's size: drawn over the floor, under everything. */
export function trackCanvas(rr: RailRoom, doors: Record<string, Tile>): HTMLCanvasElement {
  const c = Object.assign(document.createElement("canvas"), { width: W, height: H }), x = c.getContext("2d")!, im = x.createImageData(W, H), d = im.data;
  const put = (px: number, py: number, rgb: number[], a = 255) => {
    px = Math.round(px); py = Math.round(py);
    if (px < OX || py < OY || px >= OX + FX * TILE || py >= OY + FY * TILE) return;   // (never over the walls)
    const i = (py * W + px) * 4;
    [d[i], d[i + 1], d[i + 2], d[i + 3]] = [rgb[0], rgb[1], rgb[2], a];
  };
  // the slab beside the platform: worn stone, a yellow line along the edge by the track
  const [sx, sy] = [OX + rr.side[0] * TILE, OY + rr.side[1] * TILE], e = [rr.platform[0] - rr.side[0], rr.platform[1] - rr.side[1]];
  for (let j = 0; j < TILE; j++) for (let i = 0; i < TILE; i++) {
    const rim = i === 0 || j === 0 || i === TILE - 1 || j === TILE - 1, edge = (e[0] > 0 && i >= TILE - 3) || (e[0] < 0 && i <= 2) || (e[1] > 0 && j >= TILE - 3) || (e[1] < 0 && j <= 2);
    put(sx + i, sy + j, rim ? SLAB_DARK : edge && (i + j) % 4 !== 0 ? EDGE : (i * 7 + j * 3) % 11 === 0 ? SLAB_DARK : SLAB);
  }
  // every way through: from each branch's door to each other's (through the platform), or to the buffer at a dead end
  const outside = (b: Tile[]) => { const dr = doorAt(b[0], doors); return dr ? [[b[0][0] + OUT[dr][0], b[0][1] + OUT[dr][1]] as Tile] : []; };
  const runs: Tile[][] = [];
  rr.track.forEach((a, i) => rr.track.slice(i + 1).forEach((b) => runs.push([...outside(a), ...a, ...[...b].reverse().slice(1), ...outside(b).reverse()])));
  let buffer: number[] | null = null;
  if (rr.track.length === 1) {
    const b = rr.track[0], end = b.at(-1)!, prev = b.at(-2) ?? b[0], dir = [Math.sign(end[0] - prev[0]), Math.sign(end[1] - prev[1])];
    runs.push([...outside(b), ...b, [end[0] + dir[0], end[1] + dir[1]]]);
    if (rr.buffer) buffer = [OX + end[0] * TILE + 8 + dir[0] * 12, OY + end[1] * TILE + 8 + dir[1] * 12, dir[0], dir[1]];
  }
  const rails: number[][] = [];
  for (const run of runs) {
    const { p, arc } = lay(run), n = p.length / 2;
    const last = buffer && rr.track.length === 1 ? n - 5 : n;   // (to the buffer, not on past it)
    for (let i = 0; i < last; i++) {
      const [px, py, tx, ty] = along(p, i), l = Math.hypot(tx, ty) || 1, nx = -ty / l, ny = tx / l;
      const sleeper = arc[i] ? arc[i] % 4 === 3 : Math.abs(nx) > 0.9 ? ((Math.round(py) - OY) & 3) === 1 : ((Math.round(px) - OX) & 3) === 1;
      if (sleeper) for (let k = -6; k <= 6; k++) for (const w of [0, 1]) put(px + nx * k + (Math.abs(nx) > 0.9 ? 0 : w) , py + ny * k + (Math.abs(nx) > 0.9 ? w : 0), Math.abs(k) === 6 ? SLEEPER_DARK : SLEEPER);
      for (const s of [-4, 4]) rails.push([px + nx * s, py + ny * s]);
    }
  }
  for (const [px, py] of rails) put(px + 1, py + 1, RAIL_DARK);
  for (const [px, py] of rails) put(px, py, RAIL);
  if (buffer) {   // a beam across the end, red and white, on two dark posts
    const [bx, by, dx, dy] = buffer, nx = -dy, ny = dx;
    for (let k = -6; k <= 6; k++) for (let w = 0; w < 3; w++) put(bx + nx * k + dx * w, by + ny * k + dy * w, Math.abs(k) >= 5 ? [58, 44, 40] : w === 1 && Math.abs(k) < 3 ? [240, 236, 228] : [196, 58, 48]);
  }
  x.putImageData(im, 0, 0);
  return c;
}

const tracks = new Map<string, Texture>();   // (one for each room: drawn once)
export function trackTexture(rr: RailRoom, doors: Record<string, Tile>): Texture {
  const k = JSON.stringify([rr.track, rr.platform, rr.side, rr.buffer, doors]);
  let t = tracks.get(k);
  if (!t) tracks.set(k, (t = fromCanvas(trackCanvas(rr, doors))));
  return t;
}

/** What stands beside a platform: on a slab beside the track's side, something narrow (a lamp post, the bell post, a
 *  clock); a bench where the track runs along it. The same for the same room. */
export function stationSprite(rid: string, rr: RailRoom, depot: boolean): string {
  const narrow = ["station.lamp post", "station.bell post", "station.clock"], n = [...rid].reduce((a, ch) => a * 31 + ch.charCodeAt(0), 7) >>> 0;
  if (depot) return "station.clock";
  return rr.side[0] !== rr.platform[0] ? narrow[n % 2] : [...narrow.slice(0, 2), "station.bench"][n % 3];
}

/** SPEC-v3.5.12 §6: what the room's display says of the train: "CAR HERE", "CAR IN 4 MIN", "CAR IN THE MORNING". */
export function carLine(s: Snap, rid: string): string | null {
  const rr = s.rail?.rooms?.[rid];
  if (!rr) return null;
  const tr = s.creatures.find((c) => c.kind === "train");
  if (tr && !tr.moving && !tr.asleep && tr.cars?.[0]?.room === rid) return "CAR HERE";
  if (rr.due == null) return "CAR IN THE MORNING";
  const min = Math.max(1, Math.ceil(((rr.due - s.tick) * s.tick_seconds * (s.pace ?? 1)) / 60));
  return `CAR IN ${min} MIN`;
}

// ---- the train ----

type Leg = { w: number[]; from: number; to: number; gone: boolean };
type CarView = { c: Container; s: Sprite; leg: Leg | null; rest: number[] | null; came: Tile | undefined; car: Car | null; x: number; y: number; face: number };

export class TrainActor {
  cr!: Creature;
  readonly cars: CarView[] = CARS.map(() => { const c = new Container(), s = new Sprite(); s.anchor.set(17 / 34, 27 / 34); c.addChild(s); return { c, s, leg: null, rest: null, came: undefined, car: null, x: 0, y: 0, face: 0 }; });
  private lid = new Graphics();          // the cart's lid up, where its own open picture reads badly (east, west)
  private t0 = 0;
  private pace = 2000;
  private seen = "";
  private bell = -1;
  private ringAt = -1e9;
  private setOff = -1e9;                 // it pulled away: thick steam for a while
  private nextPuff = 0;
  private t = Math.random() * 1000;
  /** Where the hob riding stands (the tram's back step), and its depth; null while the tram is not in sight. */
  step: number[] | null = null;

  constructor() {
    this.lid.rect(-9, -28, 18, 7).fill(0x2b2233).rect(-8, -27, 16, 5).fill(0x8a5a34).rect(-8, -27, 16, 1).fill(0xb07a48).rect(-3, -26, 1, 4).rect(3, -26, 1, 4).fill(0x5e3b22)
      .rect(-8, -21, 16, 2).fill(0x1c1620);   // (stood up behind the open top, the dark inside showing)
    this.lid.visible = false;
    this.cars[1].c.addChild(this.lid);
  }

  /** A snapshot: the cars as they stand now; each glides there from where it stood, over `ms`. */
  update(cr: Creature, room: RoomV, snap: Snap, now: number, ms: number, sound: boolean) {
    const was = this.cr;
    this.cr = cr;
    const cars = cr.cars ?? [], rr = snap.rail?.rooms?.[room.id], seen = JSON.stringify([cars, room.id]);
    if (cr.bell != null && cr.bell !== this.bell) {
      if (this.bell >= 0 && cars.some((c) => c?.room === room.id)) { this.ringAt = now; if (sound) dispatchEvent(new CustomEvent("pet:sound", { detail: "bell" })); }
      this.bell = cr.bell;
    }
    if (cr.moving && was && !was.moving) this.setOff = now;
    if (seen === this.seen) return;
    const fresh = !this.seen || !was || JSON.parse(this.seen)[1] !== room.id;
    this.seen = seen;
    [this.t0, this.pace] = [now, ms];
    const g = rr ? graph(rr, snap.door_tiles) : new Map<string, Tile[]>(), go = cr.speed ?? 2;
    cars.forEach((car, i) => {
      const v = this.cars[i], old = v.car;
      v.car = car;
      v.leg = null;
      const here = car?.room === room.id, there = old?.room === room.id;
      if (fresh || !old || !car || (!here && !there)) { v.rest = here ? centre(car!.pos) : null; v.came = undefined; return; }
      if (here && there && same(old.pos, car.pos)) return;
      let tiles: Tile[];
      const door = (other: string) => { const d = Object.entries(room.doors).find(([, id]) => id === other)?.[0]; return d ? ([snap.door_tiles[d], OUT[d]] as const) : null; };
      if (here && there) tiles = way(g, old.pos, car.pos);
      else if (here) {   // coming in at the door from the next room
        const d = door(old.room);
        if (!d) { v.rest = centre(car.pos); return; }
        const inside = way(g, d[0], car.pos), k = Math.max(1, go - (inside.length - 1));
        tiles = [...Array.from({ length: k }, (_, j): Tile => [d[0][0] + d[1][0] * (k - j), d[0][1] + d[1][1] * (k - j)]), ...inside];
      } else {           // going out at the door into the next room
        const d = door(car!.room);
        if (!d) { v.rest = null; return; }
        const inside = way(g, old.pos, d[0]), k = Math.max(1, go - (inside.length - 1));
        tiles = [...inside, ...Array.from({ length: k }, (_, j): Tile => [d[0][0] + d[1][0] * (j + 1), d[0][1] + d[1][1] * (j + 1)])];
      }
      if (tiles.length - 1 > go + 1) { v.rest = here ? centre(car!.pos) : null; return; }   // further than it goes in a tick: it was set there (turned round at a dead end), not driven
      // a tile either side, so a corner at either end is rounded as it will be when the car goes on round it
      const before = v.came && (g.get(key(tiles[0])) ?? []).some((n) => same(n, v.came!)) ? v.came : beyond(g, tiles[0], tiles[1]), after = beyond(g, tiles.at(-1)!, tiles.at(-2));
      const all = [...(before ? [before] : []), ...tiles, ...(after ? [after] : [])], l = lay(all), b = before ? 1 : 0;
      v.leg = { w: l.p, from: l.at[b], to: l.at[b + tiles.length - 1], gone: !here };
      v.came = tiles.at(-2);
    });
  }

  /** Every frame: each car along its way, facing it; steam, the bell, the lid. */
  frame(now: number, fx: Fx, dim: number) {
    const cr = this.cr, k0 = clamp((now - this.t0) / this.pace, 0, 1), backing = cr.lead === "tram";
    // easing in as it pulls away, and out as it stops
    const k = !cr.moving ? 1 - (1 - k0) ** 2 : now - this.setOff < this.pace ? k0 * k0 : k0;
    this.step = null;
    this.cars.forEach((v, i) => {
      const car = v.car, n = CARS[i];
      let pt: number[] | null = null, moving = false;
      if (v.leg && k0 < 1) {
        const [x, y, tx, ty] = along(v.leg.w, v.leg.from + (v.leg.to - v.leg.from) * k), back = v.leg.to < v.leg.from ? -1 : 1;
        pt = [x, y, tx * back, ty * back];
        moving = true;
      } else if (v.leg) {
        if (v.leg.gone) { v.rest = null; v.leg = null; }
        else { const [x, y] = along(v.leg.w, v.leg.to); v.rest = [x, y]; v.leg = null; }
      }
      if (!pt && v.rest && car) pt = [v.rest[0], v.rest[1], 0, 0];
      v.c.visible = !!pt && !!car;
      if (!pt || !car) return;
      const [x, y, tx, ty] = pt, still = COMPASS.indexOf(car.dir);
      // facing: the way it goes (backwards while the engine pushes from behind); standing, the engine's word for it
      v.face = moving && (tx || ty) ? (compass(tx, ty) + (backing ? 4 : 0)) % 8 : still >= 0 ? still : v.face;
      const square = moving && Math.abs(Math.atan2(tx, ty) / (Math.PI / 2) - Math.round(Math.atan2(tx, ty) / (Math.PI / 2))) < 0.18;
      const open = i === 1 && !moving && cr.lid === "open", flat = v.face === 2 || v.face === 6;
      const name = open && !flat ? `${n}.open` : n, a = square && CARDINAL[v.face] ? CARDINAL[v.face] : `still.${COMPASS[v.face]}`, an = anim(name, a);
      const fi = an && an.frames.length > 1 ? Math.floor(((now + this.t) / 1000) * an.fps) % an.frames.length : 0;
      v.s.texture = tex(name, an ? a : undefined, backing && an ? an.frames.length - 1 - fi : fi);
      if (i === 1) this.lid.visible = open && flat;
      // the tram's bell: it rocks a pixel either way for a moment, and rings out
      const ring = i === 2 && now - this.ringAt < 1600 && !REDUCE.matches;
      v.s.x = ring ? (Math.floor((now - this.ringAt) / 90) % 2 ? 1 : -1) : 0;
      if (ring && Math.floor((now - this.ringAt) / 400) !== Math.floor((now - 16 - this.ringAt) / 400)) {
        for (const s of [-1, 1]) fx.spawn("tick", x + s * 6, y - 27, { life: 380, vx: s * 6 });
        fx.spawn("note", x, y - 30, { vy: -12, life: 1000, sway: 2 });
      }
      // in and out at a door: fading in as it comes through, out as it goes
      const inside = Math.min(x - OX, OX + FX * TILE - x, y - OY, OY + FY * TILE - y);
      v.c.alpha = clamp((inside + 4) / 10, 0, 1);
      v.c.position.set(Math.round(x), Math.round(y));
      v.c.zIndex = y + 2;
      [v.x, v.y] = [x, y];
      if (i === 0 && v.c.alpha > 0.5 && now > this.nextPuff) this.puff(now, fx, x, y, moving, dim);
      if (i === 2 && v.c.alpha > 0.5) {   // the back step: its far end from the cart, which is behind it as it faces
        const [fx2, fy2] = vec(v.face);
        this.step = [x - fx2 * 10, y - fy2 * 7 + 2, v.c.zIndex + (fy2 > 0 ? -1 : 1)];
      }
    });
  }

  /** The engine's steam: thick puffs as it pulls away, a steady stream on the run, a wisp now and then standing. */
  private puff(now: number, fx: Fx, x: number, y: number, moving: boolean, dim: number) {
    if (this.cr.asleep) { this.nextPuff = now + 3000; return; }
    const [dx, dy] = vec(this.cars[0].face), thick = moving && now - this.setOff < 3000, calm = REDUCE.matches ? 2 : 1;
    const at = [x + dx * 6, y - 24 + dy * 3];
    for (let j = 0; j < (thick ? 2 : 1); j++) fx.spawn("wisp", at[0] + (Math.random() - 0.5) * 3, at[1], { vx: -dx * (moving ? 10 : 2) + (Math.random() - 0.5) * 4, vy: -9 - Math.random() * 5, life: thick ? 1500 : 1100, alpha: dim > 0.5 ? 0.55 : 0.85, sway: 1 });
    this.nextPuff = now + (thick ? 110 : moving ? 260 : 1600) * calm;
  }

  rects(): Rect[] {
    return this.cars.filter((v) => v.c.visible).map((v) => { const t = v.s.texture; return { x: v.c.x - t.width * (17 / 34), y: v.c.y - t.height * (27 / 34), w: t.width, h: t.height }; });
  }
  /** Its picture for a card: the engine, side on. */
  static picture() { return canvasOf(CARS[0], "still.east", 0); }

  destroy() { for (const v of this.cars) v.c.destroy({ children: true }); }
}

const centre = (t: Tile) => [OX + t[0] * TILE + TILE / 2, OY + t[1] * TILE + TILE / 2];
const vec = (face: number): [number, number] => [Math.round(Math.sin((face * Math.PI) / 4)), Math.round(Math.cos((face * Math.PI) / 4))];
