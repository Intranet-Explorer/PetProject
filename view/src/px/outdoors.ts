// SPEC-v3.6c §4, §5: what an outdoor room (the yard, the meadow: `room.outdoor`) has that a room indoors has not. No
// walls: behind it the world outside (world.ts's own sky, sun, clouds and hills at the house's hour, season and weather).
// The weather on the ground: puddles in rain (rings in them while it falls), drifts in snow and ice in winter, piles of
// leaves and leaves falling in autumn, and the grass moving in the wind, more as the weather rises. The stream runs on
// past the floor's edge (the pond's water, px/pond.ts, carried out to the picture's edge). The hobs' shadows lengthen
// toward evening (`shadowLen`, drawn by actors.ts). Pictures by name from sprites.json (`outdoor.*`); all in whole pixels.
import { Container, Graphics, Sprite, Texture } from "pixi.js";
import type { RoomV, Snap, Tile } from "../types";
import { fromCanvas, has, size, tex } from "./assets";
import type { Fx } from "./fx";
import { FX, FY, H, idx, OX, OY, seeded, TILE, W } from "./geom";
import type { Still } from "./still";
import { REDUCE } from "./weather";
import { horizon } from "../world";

const PW = FX * TILE, PH = FY * TILE;
const WIND: Record<string, number> = { clear: 1, heat: 0.5, cloudy: 1.4, rain: 1.6, storm: 2.6, snow: 1 };
const BLADES: Record<string, number[]> = { spring: [0x3f8f3c, 0x62b04c], summer: [0x4c8a34, 0x86a844], autumn: [0x8c8034, 0xb0923e], winter: [0x5c7a58, 0x8aa080] };
const LEAVES = [0xd0702a, 0xe0a030, 0xa8442a, 0xc8b040];

/** How long a hob's shadow lies on the ground outdoors just now, in the art's pixels: none at noon, at night or under
 *  rain; longer toward morning and evening, to the west before noon and the east after (negative: west). */
export function shadowLen(s: Snap): number {
  const h = s.clock.hour, w = s.weather, k = (h - 6) / 14;
  if (s.clock.phase === "night" || !(w === "clear" || w === "heat" || w === "cloudy") || k <= 0 || k >= 1) return 0;
  const len = Math.min(14, Math.round(2.5 * (1 / Math.max(0.12, Math.sin(Math.PI * k)) - 1)));
  return (h < 13 ? -1 : 1) * (w === "cloudy" ? Math.round(len / 2) : len);
}

export class Outdoors {
  sky = new Sprite();          // the world behind (the room puts it under its ground)
  under = new Container();     // the stream past the floor, puddles, drifts, leaves: on the ground
  grass = new Graphics();      // the grass in the wind: over the floor's scenery, under everyone
  private skyFor = "";
  private groundFor = "";
  private still: Still | null = null;
  private blades: number[] = [];   // x, y, height, shade: four to a blade
  private wind = 0;
  private drawn = 0;
  private trees: number[][] = [];  // where leaves fall from: x0, y0, width, height
  private pools: number[][] = [];
  private next = 0;
  private weather = "";
  private season = "";

  update(snap: Snap, room: RoomV, still: Still) {
    const on = !!room.outdoor;
    this.sky.visible = this.under.visible = this.grass.visible = on;
    if (!on) return;
    const sk = `${Math.round(snap.clock.hour * 20)}|${snap.clock.season}|${snap.weather}`;
    if (sk !== this.skyFor) {
      this.skyFor = sk;
      const old = this.sky.texture;
      this.sky.texture = fromCanvas(horizon(snap, W, OY));
      if (old !== Texture.EMPTY) old.destroy(true);
    }
    const gk = `${snap.weather}|${snap.clock.season}`;
    if (gk === this.groundFor && still === this.still) return;
    [this.groundFor, this.still, this.weather, this.season, this.wind] = [gk, still, snap.weather, snap.clock.season, WIND[snap.weather] ?? 1];
    for (const c of this.under.removeChildren()) c.destroy({ texture: true, textureSource: true });   // (SPEC-v4.0.5 §7.1: the margin's own texture)
    this.margins(still);
    const r = seeded(room.id + gk), doors = Object.values(snap.door_tiles).map(String), free: Tile[] = [];
    for (let y = 0; y < FY; y++) for (let x = 0; x < FX; x++) if (!still.blocked[idx([x, y])] && !doors.includes(String([x, y])) && !room.spots.some((s) => s.pos[0] === x && s.pos[1] === y)) free.push([x, y]);
    for (let i = free.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [free[i], free[j]] = [free[j], free[i]]; }
    const lay = (name: string, t: Tile) => {
      if (!has(name)) return;
      const sz = size(name), s = new Sprite(tex(name));
      s.position.set(OX + t[0] * TILE + 8 - (sz.w >> 1), OY + t[1] * TILE + 10 - (sz.h >> 1));
      this.under.addChild(s);
      return s;
    };
    const wet = snap.weather === "rain" || snap.weather === "storm", winter = snap.clock.season === "winter";
    this.pools = [];
    if (wet) for (const t of free.slice(0, snap.weather === "storm" ? 6 : 4)) { lay(winter ? "outdoor.ice" : "outdoor.puddle", t); this.pools.push([OX + t[0] * TILE + 8, OY + t[1] * TILE + 10]); }
    if (snap.weather === "snow" || winter) {   // drifts against the fence and the edges; ice where water lay
      const edge = free.filter((t) => t[0] === 0 || t[0] === FX - 1 || t[1] === 0);
      for (const t of edge.slice(0, snap.weather === "snow" ? 5 : 3)) lay("outdoor.drift", t);
      if (!wet) for (const t of free.filter((t) => !edge.includes(t)).slice(0, 2)) lay("outdoor.ice", t);
    }
    // where the trees are (the fixtures and scenery that are tall and leafy): leaves fall from them, and lie under them
    this.trees = [...[...still.things.values()].filter((t) => /tree|bramble|bush/.test(t.name)).map((t) => t.rect), ...still.scenery.filter((d) => /tree|pine|birch|bush/.test(d.sprite)).map((d) => d.rect)]
      .map((b) => [b.x, b.y, b.w, b.h * 0.6]);
    if (snap.clock.season === "autumn") for (const b of this.trees.slice(0, 4)) {
      const t = free.find((f) => Math.abs(OX + f[0] * TILE + 8 - (b[0] + b[2] / 2)) < 20 && OY + f[1] * TILE >= b[1] + b[3]);
      if (t) { lay("outdoor.leaves", t); free.splice(free.indexOf(t), 1); }
    }
    this.blades = [];   // the grass that moves: a few blades on each grass tile nothing stands on (under snow in winter, none)
    if (!winter) {
      const floor = still.layout?.floor ?? [], g = seeded(room.id + "blades");
      for (let cy = 2; cy < 10; cy++) for (let cx = 1; cx < 13; cx++) {
        const fx = cx - 1, fy = cy - 2, on = fx >= 0 && fy >= 0 && fx < FX && fy < FY;
        if (!/grass/.test(floor[cy]?.[cx] ?? "") || (on && still.blocked[idx([fx, fy])])) continue;
        for (let k = 0; k < 3; k++) this.blades.push(cx * TILE + 1 + Math.floor(g() * 14), cy * TILE + 4 + Math.floor(g() * 11), 2 + Math.floor(g() * 2), g() < 0.5 ? 0 : 1);
      }
    }
    this.drawn = 0;
  }

  /** The stream past the floor: the picture's margin is the floor's water mirrored at its edge, so the stream runs on
   *  out of the picture (and its far bank shows along the foot). */
  private margins(still: Still) {
    const src = still.pond?.texture.source.resource as HTMLCanvasElement | undefined;
    if (!src || !src.getContext) return;
    const from = src.getContext("2d")!.getImageData(0, 0, PW, PH).data, c = Object.assign(document.createElement("canvas"), { width: W, height: H }), x = c.getContext("2d")!;
    const img = x.createImageData(W, H), d = img.data;
    for (let y = 0; y < H; y++) for (let xx = 0; xx < W; xx++) {
      if (xx >= OX && xx < OX + PW && y >= OY && y < OY + PH) continue;
      const m = (v: number, n: number) => (v < 0 ? Math.min(n - 1, -1 - v) : v >= n ? Math.max(0, 2 * n - 1 - v) : v);
      const fx = m(xx - OX, PW), fy = m(y - OY, PH), i = (fy * PW + fx) * 4, o = (y * W + xx) * 4;
      if (from[i + 3] < 200 || y < OY) continue;   // (only the water and its bank, never up into the sky)
      d[o] = from[i]; d[o + 1] = from[i + 1]; d[o + 2] = from[i + 2]; d[o + 3] = 255;
    }
    x.putImageData(img, 0, 0);
    this.under.addChild(new Sprite(fromCanvas(c)));
  }

  /** Every frame: the grass bends as the gusts go over it; leaves fall in autumn; rain rings the puddles. */
  frame(now: number, fx: Fx) {
    if (!this.sky.visible) return;
    if (now - this.drawn > (REDUCE.matches ? 400 : 90)) {
      this.drawn = now;
      const g = this.grass.clear(), A = this.wind * (REDUCE.matches ? 0.5 : 1), col = BLADES[this.season] ?? BLADES.summer, b = this.blades;
      for (const shade of [0, 1]) {
        for (let i = 0; i < b.length; i += 4) {
          if (b[i + 3] !== shade) continue;
          const [x, y, h] = [b[i], b[i + 1], b[i + 2]], gust = Math.max(0, Math.sin(now / 900 - x / 22)) * 0.7 + Math.max(0, Math.sin(now / 2300 - x / 50 + y / 70)) * 0.6;
          const lean = Math.round(A * gust);
          for (let j = 0; j < h; j++) g.rect(x + Math.round((lean * j) / Math.max(1, h - 1)), y - j, 1, 1);
        }
        g.fill(col[shade]);
      }
    }
    if (now < this.next) return;
    this.next = now + (REDUCE.matches ? 900 : 260);
    if (this.season === "autumn" && this.trees.length && Math.random() < 0.7) {
      const t = this.trees[Math.floor(Math.random() * this.trees.length)];
      fx.spawn("grit", t[0] + Math.random() * t[2], t[1] + Math.random() * t[3], { vx: 4 * this.wind, vy: 9, life: 2600, sway: 3, alpha: 0.95, tint: LEAVES[Math.floor(Math.random() * LEAVES.length)] });
    }
    if (this.pools.length && (this.weather === "rain" || this.weather === "storm") && this.season !== "winter") for (const p of this.pools) {
      if (Math.random() < 0.6) fx.spawn("glint", p[0] + Math.round((Math.random() - 0.5) * 12), p[1] + Math.round((Math.random() - 0.5) * 5), { life: 260, alpha: 0.55, tint: 0xd8f0ff });
    }
  }
}
