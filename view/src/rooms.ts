// The nine kinds of room (SPEC-v3 §10.2): each one's colours, floor and walls. All drawn in code; no art assets.
import type { Graphics } from "pixi.js";
import { fixedRandom } from "./pet";
import { PALETTE } from "./things";

export const T = 56, PAD = 34;
export const INK = 0x16241f, MUTED = 0x586a63;
export const mid = (p: number[]): [number, number] => [PAD + p[0] * T + T / 2, PAD + p[1] * T + T / 2];
export const hex = (name: string) => parseInt((PALETTE[name] ?? PALETTE.grey).slice(1), 16);

export function mix(a: number, b: number, t: number) {
  const ch = (s: number) => Math.round(((a >> s) & 255) * (1 - t) + ((b >> s) & 255) * t) << s;
  return ch(16) | ch(8) | ch(0);
}
const darker = (c: number, t: number) => mix(c, 0x10181c, t), lighter = (c: number, t: number) => mix(c, 0xffffff, t);

/** `open` rooms have the weather in them; `glass` rooms have it on the roof. `dim` is how dark the room is by nature. */
export type Kind = { wall: number; floor: number; css: string; dim: number; sky?: "open" | "glass" };
export const ROOMS: Record<string, Kind> = {
  nursery: { wall: 0xcfc3ab, floor: 0xe6dcc8, css: "#e0cfa8", dim: 0 },
  garden: { wall: 0x5f8f55, floor: 0x9cc474, css: "#8fbf6a", dim: 0, sky: "open" },
  cellar: { wall: 0x5b6266, floor: 0x8e9496, css: "#7f878b", dim: 0.16 },
  attic: { wall: 0x7d5f44, floor: 0xc69c6d, css: "#c08f5c", dim: 0.05 },
  pond: { wall: 0x8fb1b3, floor: 0xcfd9d0, css: "#6fb3c4", dim: 0, sky: "glass" },
  workshop: { wall: 0xa3906f, floor: 0xcbb38b, css: "#b79a68", dim: 0.02 },
  music: { wall: 0xb5806f, floor: 0xdcbd96, css: "#c9796a", dim: 0 },
  greenhouse: { wall: 0xa9d0c8, floor: 0xcfa983, css: "#7ecbb0", dim: 0, sky: "glass" },
  storeroom: { wall: 0x4f463d, floor: 0x86725c, css: "#77654f", dim: 0.22 },
};
const GRASS: Record<string, number> = { spring: 0x9cc474, summer: 0x86b35a, autumn: 0xb3a45c, winter: 0xbcc8b2 };
/** A wash over the whole room so the season can be felt indoors too. */
export const SEASON: Record<string, [number, number]> = {
  spring: [0xe9ffd8, 0.05], summer: [0xfff0b8, 0.07], autumn: [0xffb05a, 0.08], winter: [0xc4dcff, 0.1],
};

export function skyColor(phase: string, weather: string) {
  const base = ({ day: 0x9fd3ea, dusk: 0xf0a868, night: 0x1c2550 } as Record<string, number>)[phase] ?? 0x9fd3ea;
  const veil: Record<string, [number, number]> = { cloudy: [0xb4bec6, 0.6], rain: [0x7f93a1, 0.7], storm: [0x4a5466, 0.8], snow: [0xd9e1e8, 0.7], heat: [0xf6e7b4, 0.35] };
  const [c, t] = veil[weather] ?? [0, 0];
  return phase === "night" ? mix(base, darker(c || base, 0.7), t * 0.5) : mix(base, c, t);
}

/** A paint colour laid over the room's own, so a painted room stays a calm stage (SPEC-v2 §6). */
function tint(base: number, name: string | null) {
  return name && PALETTE[name] ? mix(base, hex(name), 0.5) : base;
}

/** The colour of a room's walls as painted, for whatever is drawn on them. */
export const wallColor = (type: string | null, paint: string | null) => tint((ROOMS[type ?? ""] ?? ROOMS.nursery).wall, paint);
export const light = (c: number) => (0.299 * ((c >> 16) & 255) + 0.587 * ((c >> 8) & 255) + 0.114 * (c & 255)) / 255 > 0.5;

export type Look = { wall: string | null; floor: string | null; season: string; sky: number; snow: boolean };
type Ctx = { w: number; h: number; W: number; H: number; wall: number; floor: number; rnd: () => number; look: Look };

/** Thin lines every tile, so distance can be read. */
function grid(g: Graphics, c: Ctx, alpha: number, step = T) {
  for (let x = step; x < c.W; x += step) g.rect(PAD + x, PAD, 1, c.H).fill({ color: INK, alpha });
  for (let y = step; y < c.H; y += step) g.rect(PAD, PAD + y, c.W, 1).fill({ color: INK, alpha });
}
/** Floorboards: long ones across (or down), with joints that do not line up. */
function boards(g: Graphics, c: Ctx, across: boolean, wide: number) {
  const [len, n] = across ? [c.W, c.H / wide] : [c.H, c.W / wide];
  for (let i = 0; i < n; i++) {
    if (c.rnd() < 0.5) across ? g.rect(PAD, PAD + i * wide, c.W, wide).fill({ color: INK, alpha: 0.035 }) : g.rect(PAD + i * wide, PAD, wide, c.H).fill({ color: INK, alpha: 0.035 });
    across ? g.rect(PAD, PAD + i * wide, c.W, 1).fill({ color: INK, alpha: 0.13 }) : g.rect(PAD + i * wide, PAD, 1, c.H).fill({ color: INK, alpha: 0.13 });
    for (let at = c.rnd() * 200; at < len; at += 120 + c.rnd() * 160) {
      across ? g.rect(PAD + at, PAD + i * wide, 1, wide).fill({ color: INK, alpha: 0.13 }) : g.rect(PAD + i * wide, PAD + at, wide, 1).fill({ color: INK, alpha: 0.13 });
    }
  }
}
function cobweb(g: Graphics, x: number, y: number, sx: number, sy: number) {
  for (const r of [14, 24, 34]) g.moveTo(x + sx * r, y).quadraticCurveTo(x + sx * r * 0.55, y + sy * r * 0.55, x, y + sy * r);
  g.moveTo(x, y).lineTo(x + sx * 30, y + sy * 30).stroke({ width: 1, color: 0xffffff, alpha: 0.35 });
}

const FLOOR: Record<string, (g: Graphics, c: Ctx) => void> = {
  nursery(g, c) {
    grid(g, c, 0.06);
    g.ellipse(PAD + c.W * 0.52, PAD + c.H * 0.56, 168, 104).fill({ color: lighter(c.floor, 0.45), alpha: 0.8 }).stroke({ width: 4, color: 0xd9b58a, alpha: 0.55 });
    g.ellipse(PAD + c.W * 0.52, PAD + c.H * 0.56, 150, 90).stroke({ width: 1.5, color: 0xd9b58a, alpha: 0.5 });
    for (let x = PAD + 14; x < PAD + c.W; x += 28) g.circle(x, 14, 2.5).fill({ color: lighter(c.wall, 0.5), alpha: 0.7 });   // dotted wallpaper
  },
  garden(g, c) {
    const full = c.W + 2 * PAD, hedge = c.wall;
    g.rect(0, 0, full, PAD).fill(c.look.sky);
    for (let x = 8; x < full; x += 22) g.circle(x, PAD - 3 + c.rnd() * 4, 12 + c.rnd() * 5).fill(c.rnd() < 0.5 ? hedge : darker(hedge, 0.12));
    for (let x = 6; x < full; x += 30) g.rect(x, PAD - 14, 4, 14).fill(0xe9e2cf).rect(x - 13, PAD - 10, 30, 3).fill(0xe9e2cf);   // a low fence
    for (let y = PAD + 10; y < c.H + 2 * PAD; y += 20) for (const x of [10, full - 10]) g.circle(x + c.rnd() * 6 - 3, y, 13 + c.rnd() * 4).fill(c.rnd() < 0.5 ? hedge : darker(hedge, 0.12));
    for (let x = 10; x < full; x += 20) g.circle(x, c.H + 2 * PAD - 10 + c.rnd() * 5, 14).fill(c.rnd() < 0.5 ? hedge : darker(hedge, 0.12));
    const blade = darker(c.floor, 0.22);
    for (let i = 0; i < 90; i++) {   // tufts
      const [x, y] = [PAD + 8 + c.rnd() * (c.W - 16), PAD + 8 + c.rnd() * (c.H - 16)];
      g.moveTo(x - 4, y - 5).lineTo(x, y).lineTo(x + 4, y - 6);
    }
    g.stroke({ width: 1.5, color: blade, alpha: 0.6 });
    const dots: Record<string, number[]> = { spring: [0xf7c6d9, 0xffffff], summer: [0xf2c94c, 0xffffff], autumn: [0xd9772e, 0xa8623a], winter: [] };
    for (const col of dots[c.look.season] ?? []) for (let i = 0; i < 10; i++) g.circle(PAD + 10 + c.rnd() * (c.W - 20), PAD + 10 + c.rnd() * (c.H - 20), 2.6).fill(col);
    for (let i = 0; i < 5; i++) g.ellipse(PAD + 7.5 * T + (i % 2 ? 9 : -9), PAD + c.H - 30 - i * 44, 15, 10).fill({ color: 0xcfc9b8, alpha: 0.9 });   // stepping stones up from the south door
    if (c.look.snow) for (let i = 0; i < 26; i++) g.ellipse(PAD + c.rnd() * c.W, PAD + c.rnd() * c.H, 22 + c.rnd() * 30, 9 + c.rnd() * 10).fill({ color: 0xffffff, alpha: 0.6 });
  },
  cellar(g, c) {
    for (let j = 0; j < c.h; j++) for (let x = -c.rnd() * 60; x < c.W;) {   // flagstones
      const wide = 60 + c.rnd() * 70, a = Math.max(0, x), b = Math.min(c.W, x + wide);
      g.rect(PAD + a + 1, PAD + j * T + 1, b - a - 2, T - 2).fill({ color: c.rnd() < 0.5 ? 0xffffff : INK, alpha: 0.03 + c.rnd() * 0.07 });
      x += wide;
    }
    grid(g, c, 0.16, T);
    for (let i = 0; i < 5; i++) g.ellipse(PAD + c.rnd() * c.W, PAD + c.rnd() * c.H, 40 + c.rnd() * 40, 18 + c.rnd() * 16).fill({ color: 0x24323a, alpha: 0.13 });   // damp
    for (const [x, y] of [[PAD + 6, PAD + c.H - 6], [PAD + c.W - 8, PAD + 8], [PAD + c.W - 10, PAD + c.H - 8]]) for (let i = 0; i < 7; i++) g.circle(x + (c.rnd() - 0.5) * 34, y + (c.rnd() - 0.5) * 26, 5 + c.rnd() * 5).fill({ color: 0x5c8a4e, alpha: 0.7 });
    for (let x = 0; x < c.W + 2 * PAD; x += 46) g.rect(x, 0, 1.5, PAD).fill({ color: INK, alpha: 0.25 });   // blocks in the wall
    g.rect(0, PAD / 2, c.W + 2 * PAD, 1.5).fill({ color: INK, alpha: 0.25 });
    cobweb(g, PAD, PAD, 1, 1);
  },
  attic(g, c) {
    boards(g, c, true, T / 2);
    for (const f of [0.22, 0.5, 0.78]) {   // rafters overhead: their shadows on the floor, their ends in the wall
      g.rect(PAD + c.W * f - 9, PAD, 18, c.H).fill({ color: INK, alpha: 0.07 });
      for (const y of [6, c.H + PAD + 6]) g.rect(PAD + c.W * f - 11, y, 22, 22).fill(darker(c.wall, 0.3)).stroke({ width: 1.5, color: INK, alpha: 0.5 });
    }
    cobweb(g, PAD + c.W, PAD, -1, 1);
    cobweb(g, PAD, PAD + c.H, 1, -1);
  },
  pond(g, c) {
    grid(g, c, 0.1, T * 2);
    for (let i = 0; i < 40; i++) g.ellipse(PAD + c.rnd() * c.W, PAD + c.rnd() * c.H, 3 + c.rnd() * 3, 2 + c.rnd() * 2).fill({ color: INK, alpha: 0.08 });
    const full = c.W + 2 * PAD;
    g.rect(0, 0, full, PAD - 4).fill(c.look.sky);   // glass along the top, with its frame
    for (let x = 0; x <= full; x += T) g.rect(x - 2, 0, 4, PAD - 4).fill(lighter(c.wall, 0.5));
    g.rect(0, PAD - 6, full, 6).fill(lighter(c.wall, 0.35));
    for (let x = -c.H; x < c.W; x += T * 2) g.moveTo(PAD + Math.max(0, x), PAD + Math.max(0, -x)).lineTo(PAD + Math.min(c.W, x + c.H), PAD + Math.min(c.H, c.W - x));
    g.stroke({ width: 5, color: 0xffffff, alpha: 0.1 });   // the roof's frame, as light on the floor
  },
  workshop(g, c) {
    boards(g, c, false, T / 2);
    for (let i = 0; i < 46; i++) {   // shavings
      const [x, y, r] = [PAD + 10 + c.rnd() * (c.W - 20), PAD + 10 + c.rnd() * (c.H - 20), 3 + c.rnd() * 3], a = c.rnd() * 6;
      g.moveTo(x + Math.cos(a) * r, y + Math.sin(a) * r).arc(x, y, r, a, a + 4);
    }
    g.stroke({ width: 1.6, color: 0xf0dcae, alpha: 0.9 });
    g.ellipse(PAD + c.W * 0.7, PAD + c.H * 0.3, 34, 18).fill({ color: INK, alpha: 0.08 });
    g.rect(PAD + T, 9, 3.4 * T, 3).fill(darker(c.wall, 0.4));   // a rail of tools
    for (const [i, kind] of [[1.3, 0], [2.1, 1], [2.9, 2], [3.7, 0], [9.3, 1], [10.1, 2]]) {
      const x = PAD + i * T;
      if (i > 5) g.rect(x - 14, 9, 28, 3).fill(darker(c.wall, 0.4));
      if (kind === 0) g.rect(x - 1.5, 10, 3, 18).fill(0x8a5a36).rect(x - 7, 8, 14, 7).fill(0x59636a);                        // hammer
      else if (kind === 1) g.poly([x - 9, 12, x + 9, 12, x + 9, 20, x - 9, 26]).fill(0xb8c2c6).rect(x + 7, 10, 6, 12).fill(0x8a5a36);   // saw
      else g.rect(x - 1.5, 12, 3, 16).fill(0x59636a).circle(x, 12, 5).stroke({ width: 3, color: 0x59636a });               // spanner
    }
  },
  music(g, c) {
    for (let i = 0; i < c.w * 2; i++) for (let j = 0; j < c.h * 2; j++) {   // parquet
      const [x, y, s] = [PAD + i * T / 2, PAD + j * T / 2, T / 2], flip = (i + j) % 2 === 0;
      g.rect(x, y, s, s).fill({ color: flip ? 0xffffff : INK, alpha: 0.035 });
      for (const k of [1 / 3, 2 / 3]) flip ? g.rect(x + s * k, y, 1, s).fill({ color: INK, alpha: 0.09 }) : g.rect(x, y + s * k, s, 1).fill({ color: INK, alpha: 0.09 });
    }
    for (let x = 7; x < c.W + 2 * PAD; x += 14) g.rect(x, 0, 5, PAD - 5).fill({ color: lighter(c.wall, 0.3), alpha: 0.5 });   // striped paper
    g.rect(0, PAD - 5, c.W + 2 * PAD, 5).fill(darker(c.wall, 0.3));
    const fx = PAD + 3.5 * T;
    g.roundRect(fx - 30, 5, 60, 22, 2).fill(0xf5efdf).stroke({ width: 3, color: 0x7b5a3a });   // a few bars of something, framed
    for (const y of [11, 15, 19]) g.rect(fx - 24, y, 48, 1).fill({ color: INK, alpha: 0.5 });
    for (const [dx, dy] of [[-14, 19], [-2, 15], [10, 11]]) g.circle(fx + dx, dy, 2.2).fill(INK);
    g.roundRect(PAD + 9 * T + 6, PAD + 5.2 * T, 2 * T - 12, 1.4 * T, 8).fill({ color: 0x3f6f8f, alpha: 0.85 }).roundRect(PAD + 9 * T + 14, PAD + 5.2 * T + 8, 2 * T - 28, 1.4 * T - 16, 5).stroke({ width: 2, color: 0xe9d9a6, alpha: 0.8 });
  },
  greenhouse(g, c) {
    const [fw, fh] = [c.W + 2 * PAD, c.H + 2 * PAD], frame = 0xf2f4ee;
    g.rect(0, 0, fw, fh).fill(c.look.sky).rect(PAD, PAD, c.W, c.H).fill(c.floor);   // glass all round
    for (let x = PAD; x <= PAD + c.W; x += T) g.rect(x - 2, 0, 4, PAD).fill(frame).rect(x - 2, PAD + c.H, 4, PAD).fill(frame);
    for (let y = PAD; y <= PAD + c.H; y += T) g.rect(0, y - 2, PAD, 4).fill(frame).rect(PAD + c.W, y - 2, PAD, 4).fill(frame);
    g.rect(PAD - 4, PAD - 4, c.W + 8, c.H + 8).stroke({ width: 4, color: frame });
    grid(g, c, 0.1, T / 2);
    g.rect(PAD, PAD + 3.5 * T, c.W, T).fill({ color: 0xe6dcc6, alpha: 0.75 });   // a gravel walk
    for (let i = 0; i < 70; i++) g.circle(PAD + c.rnd() * c.W, PAD + 3.5 * T + 4 + c.rnd() * (T - 8), 1.6).fill({ color: INK, alpha: 0.18 });
    for (let x = PAD + 10; x < PAD + c.W - 10; x += 26) {   // a vine along the top frame
      g.moveTo(x, PAD + 6).quadraticCurveTo(x + 13, PAD + 18, x + 26, PAD + 6).stroke({ width: 2, color: 0x3f7f4c });
      g.ellipse(x + 13, PAD + 15, 6, 4).fill(c.rnd() < 0.5 ? 0x4fae72 : 0x3f9b63);
    }
  },
  storeroom(g, c) {
    boards(g, c, true, T / 2);
    for (let i = 0; i < 80; i++) g.circle(PAD + c.rnd() * c.W, PAD + c.rnd() * c.H, 1.2).fill({ color: 0xffffff, alpha: 0.12 });   // dust
    for (let x = 6; x < c.W + 2 * PAD - 30;) {   // boxes stacked against the far wall
      const [wide, tall] = [26 + c.rnd() * 30, 14 + c.rnd() * 14];
      if (Math.abs(x + wide / 2 - (PAD + 7.5 * T)) > T) g.rect(x, PAD - tall - 2, wide, tall).fill(mix(0x8a6a48, 0x5d4a38, c.rnd())).stroke({ width: 1.5, color: INK, alpha: 0.5 });
      x += wide + 4 + c.rnd() * 22;
    }
    cobweb(g, PAD, PAD, 1, 1);
    cobweb(g, PAD + c.W, PAD + c.H, -1, -1);
  },
};

/** Walls and floor for one room. Seeded by the room's id, so each room keeps its own scatter of detail. */
export function backdrop(g: Graphics, type: string, id: string, w: number, h: number, look: Look) {
  const kind = ROOMS[type] ?? ROOMS.nursery;
  const base = type === "garden" ? GRASS[look.season] ?? kind.floor : kind.floor;
  const c: Ctx = { w, h, W: w * T, H: h * T, wall: tint(kind.wall, look.wall), floor: tint(base, look.floor), look,
                   rnd: fixedRandom([...id + type].reduce((a, ch) => a * 31 + ch.charCodeAt(0), 7)) };
  g.clear().rect(0, 0, c.W + 2 * PAD, c.H + 2 * PAD).fill(c.wall).rect(PAD, PAD, c.W, c.H).fill(c.floor);
  (FLOOR[type] ?? FLOOR.nursery)(g, c);
  if (kind.sky !== "open") {   // a wall has a foot, and throws a little shade
    g.rect(PAD, PAD, c.W, 7).fill({ color: INK, alpha: 0.07 }).rect(PAD, PAD, 5, c.H).fill({ color: INK, alpha: 0.04 });
    g.rect(PAD - 1, PAD - 1, c.W + 2, c.H + 2).stroke({ width: 2, color: INK, alpha: 0.28 });
  }
  const [wash, alpha] = SEASON[look.season] ?? [0, 0];
  g.rect(0, 0, c.W + 2 * PAD, c.H + 2 * PAD).fill({ color: wash, alpha });
}
