// What stands in a room (SPEC-v3 §10.2): every fixture in house.toml, the bits that lie about, doors, memorial
// stones and the small creatures. Each is a few shapes; a fixture the view has never heard of gets a plain box.
import type { Graphics } from "pixi.js";
import { hex, INK, mix, PAD, T } from "./rooms";
import type { Obj } from "./types";

export type Env = { phase: string; power: boolean; season: string };
type Draw = (g: Graphics, x: number, y: number, o: Obj, env: Env) => void;

const WOOD = 0x8a5a36, WOOD_D = 0x6b4426, IRON = 0x59636a, LEAF = 0x3f9b63, LEAF_L = 0x4fae72, LEAF_D = 0x2f8553, SOIL = 0x6b4a34;
const on = (o: Obj, env: Env) => o.state === "on" && env.power;
const line = { width: 2, color: INK };

function lamp(g: Graphics, x: number, y: number, lit: boolean) {
  g.rect(x - 2, y - 6, 4, 22).fill(INK).rect(x - 9, y + 14, 18, 4).fill(INK);
  g.poly([x - 14, y - 4, x + 14, y - 4, x + 7, y - 22, x - 7, y - 22]).fill(lit ? 0xffc93c : 0x9aa8a2).stroke({ width: 1.5, color: INK });
}
function lantern(g: Graphics, x: number, y: number, lit: boolean) {
  g.moveTo(x - 6, y - 14).quadraticCurveTo(x, y - 26, x + 6, y - 14).stroke({ width: 2, color: IRON });
  g.rect(x - 9, y - 15, 18, 4).fill(IRON).rect(x - 10, y + 12, 20, 5).fill(IRON);
  g.roundRect(x - 8, y - 11, 16, 23, 3).fill(lit ? 0xffd76a : 0x7f8c8a).stroke({ width: 1.5, color: INK });
  g.rect(x - 0.7, y - 11, 1.4, 23).fill({ color: INK, alpha: 0.5 });
}
/** A bed of soil with something growing in it: `grow` 0..1, and fruit once it is ripe. */
function bed(g: Graphics, x: number, y: number, o: Obj, each: (px: number, py: number, k: number, ripe: boolean) => void) {
  const k = Math.min(1, Math.max(0.12, o.grow ?? 0.5)), ripe = o.state === "ripe";
  g.roundRect(x - 26, y - 4, 52, 24, 8).fill(SOIL).stroke({ width: 1.5, color: INK, alpha: 0.5 });
  for (const dx of [-16, 0, 16]) each(x + dx, y + 8, k, ripe);
}
const rug = (g: Graphics, x: number, y: number, main: number, band: number) => {
  g.roundRect(x - 40, y - 22, 80, 44, 6).fill(main).stroke({ width: 1.5, color: INK, alpha: 0.5 });
  g.roundRect(x - 32, y - 14, 64, 28, 3).stroke({ width: 2.5, color: band });
  for (const dx of [-36, -28, -20, -12, -4, 4, 12, 20, 28, 36]) g.rect(x + dx - 0.5, y + 22, 1, 5).rect(x + dx - 0.5, y - 27, 1, 5);
  g.fill({ color: band });
};

export const FIX: Record<string, Draw> = {
  lamp: (g, x, y, o, env) => lamp(g, x, y, on(o, env)),
  "work lamp"(g, x, y, o, env) {
    g.rect(x - 11, y + 13, 22, 5).fill(IRON);
    g.moveTo(x, y + 13).lineTo(x - 7, y - 4).lineTo(x + 5, y - 16).stroke({ width: 3, color: IRON });
    g.poly([x + 1, y - 22, x + 15, y - 12, x + 9, y - 6, x - 3, y - 14]).fill(on(o, env) ? 0xffc93c : 0x9aa8a2).stroke({ width: 1.5, color: INK });
  },
  lantern: (g, x, y, o, env) => lantern(g, x, y, on(o, env)),
  "old lantern": (g, x, y, o, env) => lantern(g, x, y, on(o, env)),
  plant(g, x, y) {
    g.poly([x - 10, y + 2, x + 10, y + 2, x + 7, y + 18, x - 7, y + 18]).fill(0xa8623a).stroke({ width: 1.5, color: INK });
    g.circle(x, y - 10, 10).fill(LEAF).circle(x - 9, y - 2, 8).fill(LEAF_L).circle(x + 9, y - 2, 8).fill(LEAF_D);
  },
  bowl(g, x, y, o) {
    g.ellipse(x, y + 6, 17, 9).fill(0x6f8fa8).stroke({ width: 1.5, color: INK });
    g.ellipse(x, y + 3, 13, 5).fill(0xdfe7ea);
    if (o.state !== "empty") g.ellipse(x, y + 3, o.state === "full" ? 13 : 7, o.state === "full" ? 5 : 3).fill(0x9a6a3c);
  },
  ball(g, x, y) {
    g.circle(x, y + 4, 11).fill(0xd9483b).stroke({ width: 1.5, color: INK }).circle(x - 4, y, 3).fill({ color: 0xffffff, alpha: 0.7 });
  },
  blanket(g, x, y) {
    g.roundRect(x - 22, y - 12, 44, 28, 5).fill(0x8a6fb0).stroke({ width: 1.5, color: INK });
    g.rect(x - 21, y - 3, 42, 3).fill(0xc9b8e3).rect(x - 21, y + 6, 42, 3).fill(0xc9b8e3);
  },
  "music box"(g, x, y, o) {
    g.rect(x - 14, y - 2, 28, 18).fill(0x2f8f8a).stroke({ width: 1.5, color: INK }).rect(x - 14, y - 8, 28, 6).fill(0x1f6b67).stroke({ width: 1.5, color: INK });
    g.rect(x + 14, y + 4, 6, 2).fill(INK).circle(x + 21, y + 5, 2.5).fill(0xf2c94c);
    if (o.state === "playing") g.circle(x + 12, y - 20, 4).fill(INK).rect(x + 15, y - 34, 2, 14).fill(INK).circle(x, y - 26, 3).fill(INK).rect(x + 2, y - 37, 2, 11).fill(INK);
  },
  rock(g, x, y) {
    g.poly([x - 15, y + 14, x - 11, y - 2, x - 1, y - 9, x + 12, y - 3, x + 16, y + 14]).fill(0x8d9793).stroke({ width: 1.5, color: INK });
    g.poly([x - 7, y - 1, x - 1, y - 6, x + 4, y - 3]).fill({ color: 0xffffff, alpha: 0.35 });
  },
  bed(g, x, y) {
    g.roundRect(x - 24, y - 16, 48, 34, 5).fill(0x5f86b3).stroke({ width: 1.5, color: INK });
    g.roundRect(x - 20, y - 12, 16, 26, 4).fill(0xf3f1e8).rect(x + 2, y - 16, 2, 34).fill({ color: INK, alpha: 0.15 });
  },
  mirror(g, x, y) {
    g.roundRect(x - 11, y - 22, 22, 42, 9).fill(0xcfe3e8).stroke({ width: 3, color: 0x7b6a4a });
    g.poly([x - 5, y - 4, x + 3, y - 14, x + 5, y - 12, x - 3, y - 2]).fill({ color: 0xffffff, alpha: 0.8 });
  },
  // ---- the garden ----
  "bean row": (g, x, y, o) => bed(g, x, y, o, (px, py, k, ripe) => {
    g.rect(px - 1, py - 30 * k - 4, 2, 30 * k + 4).fill(0xb9a37a);
    for (let i = 0; i < 3 * k + 1; i++) g.ellipse(px + (i % 2 ? 5 : -5), py - 6 - i * 8, 5, 3).fill(i % 2 ? LEAF : LEAF_L);
    if (ripe) g.roundRect(px + 2, py - 20, 3, 11, 1.5).fill(0x9bd06a).stroke({ width: 1, color: INK, alpha: 0.6 });
  }),
  "berry bush": (g, x, y, o) => bed(g, x, y, o, (px, py, k, ripe) => {
    g.circle(px, py - 8 * k - 2, 6 + 9 * k).fill(px > x ? LEAF_D : px < x ? LEAF_L : LEAF);
    if (ripe) for (const [dx, dy] of [[-4, -12], [4, -6], [0, -17]]) g.circle(px + dx, py + dy, 2.6).fill(0xc9304a);
  }),
  "herb patch": (g, x, y, o) => bed(g, x, y, o, (px, py, k, ripe) => {
    for (const a of [-0.5, 0, 0.5]) g.moveTo(px, py).lineTo(px + Math.sin(a) * 16 * k, py - 6 - 14 * k);
    g.stroke({ width: 2.5, color: LEAF_L });
    if (ripe) g.circle(px, py - 8 - 14 * k, 3).fill(0xb79be0);
  }),
  "tomato vine": (g, x, y, o) => bed(g, x, y, o, (px, py, k, ripe) => {
    g.rect(px - 1, py - 34, 2, 34).fill(0xb9a37a);
    g.moveTo(px, py).quadraticCurveTo(px + 8, py - 14 * k, px, py - 30 * k).stroke({ width: 2, color: LEAF_D });
    for (let i = 0; i < 3 * k; i++) g.ellipse(px + (i % 2 ? 6 : -6), py - 8 - i * 9, 5, 3).fill(LEAF);
    if (ripe) g.circle(px + 5, py - 10, 4).fill(0xd9483b).circle(px - 4, py - 20, 3.4).fill(0xe2603a);
  }),
  "melon bed": (g, x, y, o) => bed(g, x, y, o, (px, py, k, ripe) => {
    g.ellipse(px - 4, py - 3, 7 * k + 2, 4 * k + 1).fill(LEAF).ellipse(px + 5, py - 6, 6 * k + 2, 4 * k + 1).fill(LEAF_L);
    if (ripe && px === x) g.ellipse(px, py - 9, 10, 8).fill(0x7fb069).stroke({ width: 1.2, color: INK, alpha: 0.6 }).rect(px - 1, py - 16, 2, 14).fill({ color: 0xdff0c8, alpha: 0.7 });
  }),
  "old bench"(g, x, y) {
    g.rect(x - 24, y - 12, 48, 5).fill(WOOD).stroke(line).rect(x - 26, y - 2, 52, 9).fill(0xa87447).stroke(line);
    g.rect(x - 22, y + 7, 4, 11).fill(WOOD_D).rect(x + 18, y + 7, 4, 11).fill(WOOD_D).rect(x - 22, y - 7, 3, 5).fill(WOOD_D).rect(x + 19, y - 7, 3, 5).fill(WOOD_D);
  },
  "bird bath"(g, x, y) {
    g.rect(x - 4, y - 2, 8, 18).fill(0xb9bfbc).stroke({ width: 1.5, color: INK }).rect(x - 10, y + 14, 20, 5).fill(0xa4aba8).stroke({ width: 1.5, color: INK });
    g.ellipse(x, y - 6, 20, 8).fill(0xc9cfcb).stroke({ width: 1.5, color: INK }).ellipse(x, y - 7, 15, 5).fill(0x7fb7d6);
  },
  // ---- the cellar ----
  barrel(g, x, y) {
    g.roundRect(x - 15, y - 20, 30, 40, 9).fill(WOOD).stroke(line);
    for (const dx of [-7, 0, 7]) g.rect(x + dx - 0.5, y - 19, 1, 38).fill({ color: INK, alpha: 0.25 });
    g.rect(x - 16, y - 12, 32, 4).fill(IRON).rect(x - 16, y + 8, 32, 4).fill(IRON);
  },
  shelf(g, x, y) {
    g.rect(x - 24, y - 22, 48, 42).fill(WOOD_D).stroke(line);
    for (const dy of [-8, 6]) g.rect(x - 22, y + dy, 44, 3).fill(0xa87447);
    g.roundRect(x - 18, y - 19, 9, 11, 2).fill(0xb9d6c2).roundRect(x - 5, y - 17, 8, 9, 2).fill(0xd9b06a).roundRect(x + 8, y - 20, 9, 12, 2).fill(0x9fb7d0);
    g.roundRect(x - 16, y - 4, 12, 10, 2).fill(0xc98f6a).roundRect(x + 2, y - 3, 14, 9, 2).fill(0xdcd6c2);
  },
  "old rug": (g, x, y) => rug(g, x, y, 0x8c5a52, 0xd8b88a),
  // ---- the attic ----
  trunk(g, x, y, o) {
    const open = o.state === "open";
    g.roundRect(x - 22, y - 6, 44, 24, 3).fill(0x7a5236).stroke(line);
    if (open) g.poly([x - 22, y - 6, x + 22, y - 6, x + 18, y - 26, x - 18, y - 26]).fill(0x5d3d27).stroke(line).rect(x - 16, y - 9, 32, 5).fill(0xd9b06a);
    else g.roundRect(x - 23, y - 16, 46, 12, 5).fill(0x8f6242).stroke(line);
    g.rect(x - 14, y - 6, 3, 24).fill(0xc9a24a).rect(x + 11, y - 6, 3, 24).fill(0xc9a24a).rect(x - 3, y - 3, 6, 7).fill(0xc9a24a);
  },
  "rocking chair"(g, x, y) {
    g.moveTo(x - 20, y + 14).quadraticCurveTo(x, y + 24, x + 22, y + 13).stroke({ width: 3, color: WOOD_D });
    g.rect(x - 13, y - 22, 4, 36).fill(WOOD).rect(x + 10, y - 2, 4, 16).fill(WOOD);
    g.roundRect(x - 14, y - 24, 22, 20, 4).fill(0xa87447).stroke(line).roundRect(x - 15, y - 3, 30, 8, 3).fill(0xb98456).stroke(line);
    for (const dx of [-8, -3, 2]) g.rect(x + dx, y - 21, 1.5, 15).fill({ color: INK, alpha: 0.3 });
  },
  // ---- the pond room ----
  reeds(g, x, y) {
    for (const [dx, tall] of [[-12, 30], [-5, 40], [3, 34], [10, 42], [16, 28]]) {
      g.moveTo(x + dx, y + 16).quadraticCurveTo(x + dx + 3, y, x + dx + (dx % 2 ? 4 : -3), y + 16 - tall).stroke({ width: 2, color: 0x5d8f4e });
      g.roundRect(x + dx + (dx % 2 ? 2 : -5), y + 14 - tall, 4, 11, 2).fill(0x7a5236);
    }
  },
  "flat stone"(g, x, y) {
    g.ellipse(x, y + 5, 26, 13).fill(0x9aa3a0).stroke({ width: 1.5, color: INK }).ellipse(x - 5, y + 1, 14, 5).fill({ color: 0xffffff, alpha: 0.25 });
  },
  // ---- the workshop ----
  workbench(g, x, y) {
    g.rect(x - 34, y - 8, 68, 16).fill(0xb98456).stroke(line).rect(x - 30, y + 8, 5, 14).fill(WOOD_D).rect(x + 25, y + 8, 5, 14).fill(WOOD_D);
    g.rect(x - 26, y - 16, 12, 8).fill(IRON).rect(x - 22, y - 20, 4, 4).fill(IRON);   // a vice
    g.rect(x + 2, y - 12, 22, 4).fill(0xe0c08a).stroke({ width: 1, color: INK, alpha: 0.5 });
  },
  stool(g, x, y) {
    g.rect(x - 9, y, 3, 16).fill(WOOD_D).rect(x + 6, y, 3, 16).fill(WOOD_D).rect(x - 8, y + 9, 16, 2).fill(WOOD_D);
    g.ellipse(x, y - 1, 13, 6).fill(0xb98456).stroke(line);
  },
  // ---- the music room ----
  drum(g, x, y) {
    g.rect(x - 16, y - 6, 32, 20).fill(0xb3423a).stroke(line).ellipse(x, y + 14, 16, 5).fill(0xb3423a).stroke(line);
    g.ellipse(x, y - 6, 16, 6).fill(0xf0e6cf).stroke(line);
    for (const dx of [-12, -4, 4, 12]) g.moveTo(x + dx, y - 1).lineTo(x + dx + 4, y + 15);
    g.stroke({ width: 1.2, color: 0xf2c94c });
    g.rect(x + 8, y - 20, 16, 2.5).fill(0xd8b98c).circle(x + 8, y - 19, 3).fill(0xd8b98c);
  },
  chimes(g, x, y) {
    g.rect(x - 18, y - 22, 36, 4).fill(WOOD).stroke({ width: 1.5, color: INK }).rect(x - 1, y - 28, 2, 6).fill(INK);
    [-13, -6.5, 0, 6.5, 13].forEach((dx, i) => g.rect(x + dx - 0.5, y - 18, 1, 5).fill(INK).roundRect(x + dx - 2.5, y - 13, 5, 16 + i * 4, 2).fill(0xc9d3d8).stroke({ width: 1, color: INK }));
  },
  rug: (g, x, y) => rug(g, x, y, 0xa24a4a, 0xf0d9a0),
  // ---- the greenhouse ----
  "hot pipe"(g, x, y) {
    g.roundRect(x - 22, y - 5, 44, 10, 5).fill(0xb5653a).stroke(line);
    for (const dx of [-12, 0, 12]) g.rect(x + dx - 2, y - 7, 4, 14).fill(0x8f4a2a);
    g.circle(x - 22, y, 6).fill(0xc94f3a).stroke({ width: 1.5, color: INK });
    for (const dx of [-8, 6]) g.moveTo(x + dx, y - 10).quadraticCurveTo(x + dx + 5, y - 16, x + dx, y - 22);
    g.stroke({ width: 1.5, color: 0xffffff, alpha: 0.55 });
  },
  // ---- the storeroom ----
  crates(g, x, y) {
    for (const [dx, dy, s] of [[-14, 0, 24], [12, 2, 22], [0, -19, 22]]) {
      g.rect(x + dx - s / 2, y + dy - s / 2 + 4, s, s).fill(0xa87447).stroke(line);
      g.moveTo(x + dx - s / 2, y + dy - s / 2 + 4).lineTo(x + dx + s / 2, y + dy + s / 2 + 4).stroke({ width: 2, color: WOOD_D });
    }
  },
  shelves(g, x, y) {
    g.rect(x - 26, y - 24, 52, 46).fill(0x5d4a38).stroke(line);
    for (const dy of [-10, 5]) g.rect(x - 24, y + dy, 48, 3).fill(0x8a6a48);
    g.rect(x - 20, y - 21, 12, 11).fill(0xa87447).rect(x - 3, y - 19, 9, 9).fill(0xc9b27a).rect(x + 10, y - 22, 11, 12).fill(0x7f8c8a);
    g.rect(x - 18, y - 5, 16, 10).fill(0xb98456).rect(x + 4, y - 3, 8, 8).fill(0x9fb7d0).rect(x - 12, y + 10, 26, 9).fill(0xa87447);
  },
};

export function fixture(g: Graphics, name: string, x: number, y: number, o: Obj, env: Env) {
  if (FIX[name]) return FIX[name](g, x, y, o, env);
  g.rect(x - 14, y - 10, 28, 24).fill(0xa87447).stroke(line);   // something the house file added later
}

/** A window in the west wall or a skylight in the north one: the frame and how far it is open. The glass and the
 *  weather in it are drawn every frame by the room, above the dark. */
export function windowRect(o: Obj): [number, number, number, number] {
  return o.pos[1] === 0 && o.pos[0] > 0 ? [PAD + o.pos[0] * T - 8, 6, T + 16, PAD - 10] : [6, PAD + o.pos[1] * T + 3, PAD - 12, T - 6];
}

/** One gathered bit (§6.2): each kind has its own small shape, so a floor of bits can be read at a glance. */
export function bit(g: Graphics, kind: string, looks: { shape: string; color: string } | undefined, x: number, y: number, s = 1) {
  const c = hex(looks?.color ?? "grey"), ink = { width: 1.2, color: INK };
  const d = (v: number) => v * s;
  switch (kind) {
    case "fluff": g.circle(x - d(5), y + d(1), d(5)).circle(x + d(4), y + d(2), d(5.5)).circle(x, y - d(3), d(6)).fill(0xfbfaf4).stroke({ width: 1, color: INK, alpha: 0.45 }); break;
    case "pebble": g.ellipse(x, y + d(1), d(8), d(6)).fill(c).stroke(ink).ellipse(x - d(2), y - d(1), d(3), d(1.6)).fill({ color: 0xffffff, alpha: 0.5 }); break;
    case "wax": g.roundRect(x - d(6), y - d(5), d(12), d(11), d(2)).fill(c).stroke(ink).rect(x - d(0.6), y - d(9), d(1.2), d(4)).fill(INK); break;
    case "seed": g.ellipse(x - d(4), y + d(1), d(3), d(4.5)).ellipse(x + d(3), y - d(1), d(3), d(4.5)).ellipse(x + d(1), y + d(6), d(2.6), d(3.6)).fill(c).stroke({ width: 1, color: INK }); break;
    case "leaf": g.moveTo(x - d(9), y + d(5)).quadraticCurveTo(x - d(4), y - d(9), x + d(9), y - d(6)).quadraticCurveTo(x + d(5), y + d(8), x - d(9), y + d(5)).fill(c).stroke(ink).moveTo(x - d(8), y + d(4)).lineTo(x + d(6), y - d(4)).stroke({ width: 1, color: INK, alpha: 0.5 }); break;
    case "petal": g.ellipse(x - d(4), y, d(4), d(7)).fill(c).stroke({ width: 1, color: INK, alpha: 0.6 }).ellipse(x + d(4), y + d(1), d(4), d(6.5)).fill(mix(c, 0xffffff, 0.3)).stroke({ width: 1, color: INK, alpha: 0.6 }); break;
    case "clay": g.poly([x - d(8), y + d(6), x - d(6), y - d(4), x + d(2), y - d(7), x + d(8), y - d(1), x + d(7), y + d(6)]).fill(0xb5714a).stroke(ink); break;
    case "moss": for (const [dx, dy, r] of [[-5, 2, 5], [4, 3, 5], [0, -2, 6]]) g.circle(x + d(dx), y + d(dy), d(r)).fill(dx ? 0x5c8a4e : 0x76a363); break;
    case "soot": for (const [dx, dy, r] of [[-4, 2, 3.4], [3, 3, 3], [0, -3, 3.6], [6, -2, 2], [-6, -4, 1.6]]) g.circle(x + d(dx), y + d(dy), d(r)).fill(0x26302c); break;
    case "feather": g.moveTo(x - d(9), y + d(7)).quadraticCurveTo(x - d(6), y - d(8), x + d(9), y - d(8)).quadraticCurveTo(x + d(7), y + d(5), x - d(9), y + d(7)).fill(0xfbfaf4).stroke({ width: 1, color: INK, alpha: 0.6 }).moveTo(x - d(11), y + d(9)).lineTo(x + d(7), y - d(7)).stroke({ width: 1.2, color: INK, alpha: 0.6 }); break;
    case "cloth": g.poly([x - d(8), y - d(6), x + d(8), y - d(7), x + d(7), y + d(6), x - d(7), y + d(7)]).fill(c).stroke(ink).poly([x + d(8), y - d(7), x + d(2), y - d(1), x + d(7), y + d(1)]).fill(mix(c, 0xffffff, 0.35)); break;
    case "wood": g.roundRect(x - d(10), y - d(3), d(20), d(7), d(2)).fill(c).stroke(ink).ellipse(x + d(8), y + d(0.5), d(1.6), d(2.4)).fill(0xd8b98c); break;
    case "shell": g.moveTo(x - d(8), y + d(5)).arc(x, y + d(5), d(8), Math.PI, Math.PI * 2).closePath().fill(c).stroke(ink); for (const a of [-0.6, 0, 0.6]) g.moveTo(x, y + d(5)).lineTo(x + Math.sin(a) * d(8), y + d(5) - Math.cos(a) * d(8)); g.stroke({ width: 1, color: INK, alpha: 0.5 }); break;
    case "bead": g.circle(x, y, d(6)).fill({ color: c, alpha: 0.85 }).stroke(ink).circle(x - d(2), y - d(2), d(2)).fill({ color: 0xffffff, alpha: 0.8 }); break;
    case "reed": g.rect(x - d(1), y - d(8), d(2), d(17)).fill(c).roundRect(x - d(2.5), y - d(10), d(5), d(8), d(2)).fill(0x7a5236).stroke({ width: 1, color: INK, alpha: 0.6 }); break;
    case "wire": for (const dx of [-6, -2, 2, 6]) g.ellipse(x + d(dx), y, d(3.2), d(6.5)); g.stroke({ width: 1.8, color: 0x3f4a50 }); g.moveTo(x - d(9), y + d(6.5)).lineTo(x - d(6), y + d(6.5)).moveTo(x + d(6), y - d(6.5)).lineTo(x + d(10), y - d(6.5)).stroke({ width: 1.8, color: 0x3f4a50 }); break;
    case "metal": g.poly([x - d(8), y + d(6), x + d(1), y - d(8), x + d(8), y + d(4)]).fill(0xaab4b8).stroke(ink).poly([x - d(3), y + d(2), x + d(1), y - d(5), x + d(3), y + d(1)]).fill({ color: 0xffffff, alpha: 0.45 }); break;
    case "string": g.moveTo(x - d(9), y + d(3)).bezierCurveTo(x - d(4), y - d(9), x - d(1), y + d(9), x + d(3), y - d(2)).bezierCurveTo(x + d(5), y - d(7), x + d(8), y - d(2), x + d(9), y + d(4)).stroke({ width: 1.8, color: c }); break;
    case "bell": g.moveTo(x - d(7), y + d(5)).quadraticCurveTo(x - d(6), y - d(8), x, y - d(8)).quadraticCurveTo(x + d(6), y - d(8), x + d(7), y + d(5)).closePath().fill(c).stroke(ink).circle(x, y + d(6.5), d(2)).fill(INK); break;
    case "felt": g.roundRect(x - d(7), y - d(6), d(14), d(12), d(2)).fill(c).stroke(ink); for (const dx of [-4, 0, 4]) g.rect(x + d(dx) - 0.5, y - d(4), 1, d(2.5)); g.fill({ color: 0xffffff, alpha: 0.8 }); break;
    case "resin": g.moveTo(x, y - d(9)).quadraticCurveTo(x + d(8), y + d(2), x, y + d(7)).quadraticCurveTo(x - d(8), y + d(2), x, y - d(9)).fill({ color: c, alpha: 0.9 }).stroke(ink).circle(x - d(2), y + d(1), d(1.6)).fill({ color: 0xffffff, alpha: 0.7 }); break;
    case "vine": g.moveTo(x - d(9), y + d(6)).bezierCurveTo(x - d(8), y - d(10), x + d(8), y - d(8), x + d(5), y + d(1)).bezierCurveTo(x + d(3), y + d(6), x - d(3), y + d(4), x - d(1), y - d(1)).stroke({ width: 2, color: c }).ellipse(x + d(7), y - d(5), d(3.5), d(2.2)).fill(LEAF_L); break;
    default:   // a kind the view has not met: the plain shape house.toml gives it
      if (looks?.shape === "square") g.rect(x - d(6), y - d(6), d(12), d(12)).fill(c).stroke(ink);
      else if (looks?.shape === "triangle") g.poly([x, y - d(7), x + d(7), y + d(6), x - d(7), y + d(6)]).fill(c).stroke(ink);
      else if (looks?.shape === "bar") g.rect(x - d(9), y - d(2.5), d(18), d(5)).fill(c).stroke(ink);
      else if (looks?.shape === "ring") g.circle(x, y, d(6)).stroke({ width: d(3), color: c });
      else g.circle(x, y, looks?.shape === "dot" ? d(3.5) : d(6.5)).fill(c).stroke(ink);
  }
}

/** A memorial (§4.2): a small standing stone, a little grown over. Its name is a label; its words are on hover. */
export function stone(g: Graphics, x: number, y: number) {
  g.ellipse(x, y + 15, 17, 5).fill({ color: INK, alpha: 0.18 });
  g.moveTo(x - 12, y + 15).lineTo(x - 12, y - 6).quadraticCurveTo(x - 12, y - 20, x, y - 20).quadraticCurveTo(x + 12, y - 20, x + 12, y - 6).lineTo(x + 12, y + 15).closePath()
    .fill(0xa9b0ad).stroke({ width: 2, color: INK });
  g.rect(x - 6, y - 8, 12, 1.6).rect(x - 4, y - 3, 8, 1.6).fill({ color: INK, alpha: 0.45 });
  g.circle(x - 11, y + 13, 4).circle(x - 6, y + 15, 3).fill(0x5c8a4e).circle(x + 11, y + 12, 2.6).fill(0xf7c6d9);
}

/** A door in a wall. `open`: someone has been through and it stands ajar onto the next room's colour.
 *  `shut`: a draught has blown it to. `unknown`: nobody has been through it yet. Returns where it was drawn. */
export function door(g: Graphics, dir: string, tile: number[], how: "open" | "shut" | "unknown", beyond: number, w: number, h: number): [number, number, number, number] {
  const flat = dir === "north" || dir === "south";
  const [bw, bh] = flat ? [42, PAD - 6] : [PAD - 6, 46];
  const bx = flat ? PAD + tile[0] * T + T / 2 - bw / 2 : dir === "west" ? 3 : PAD + w * T + 3;
  const by = flat ? (dir === "north" ? 3 : PAD + h * T + 3) : PAD + tile[1] * T + T / 2 - bh / 2;
  const leaf = how === "unknown" ? 0x6f5a48 : 0x9a6a40;
  g.rect(bx - 3, by - 3, bw + 6, bh + 6).fill(0x4a3626).rect(bx, by, bw, bh).fill(how === "open" ? mix(beyond, 0x10181c, 0.25) : leaf);
  if (how === "open") {   // the leaf swung back against the wall
    flat ? g.rect(bx, by, 7, bh).fill(0x9a6a40).stroke({ width: 1.2, color: INK }) : g.rect(bx, by, bw, 7).fill(0x9a6a40).stroke({ width: 1.2, color: INK });
  } else {
    g.rect(bx + 4, by + 4, bw - 8, bh - 8).stroke({ width: 1.5, color: INK, alpha: 0.35 });
    const [cx, cy] = [bx + bw / 2, by + bh / 2];
    if (how === "unknown") g.moveTo(cx - 4, cy - 3).arc(cx, cy - 3, 4, Math.PI, Math.PI * 2.5).lineTo(cx, cy + 3).stroke({ width: 2.2, color: 0xe9dcc0 }).circle(cx, cy + 7, 1.5).fill(0xe9dcc0);
    else g.circle(flat ? bx + bw - 7 : cx, flat ? cy : by + bh - 7, 2.5).fill(0xf2c94c).stroke({ width: 1, color: INK });
  }
  g.rect(bx, by, bw, bh).stroke({ width: 2, color: INK });
  return [bx, by, bw, bh];
}

/** The small creatures (§6.5), drawn about (0,0) every frame so they can flutter, scuttle and hop. `t` is ms. */
export function creature(g: Graphics, kind: string, t: number, moving: boolean) {
  g.clear();
  if (kind === "moth") {
    const flap = 0.35 + 0.65 * Math.abs(Math.sin(t / 60));
    g.ellipse(0, 12, 8, 2.5).fill({ color: INK, alpha: 0.12 });
    for (const s of [-1, 1]) g.poly([0, -3, s * 13 * flap, -11, s * 15 * flap, 1, s * 8 * flap, 7, 0, 3]).fill(0xd9cdb4).stroke({ width: 1, color: INK });
    for (const s of [-1, 1]) g.circle(s * 9 * flap, -3, 2).fill(0x8a6a48);
    g.ellipse(0, 0, 2.6, 7).fill(0x6b5a48).moveTo(-1, -6).lineTo(-4, -11).moveTo(1, -6).lineTo(4, -11).stroke({ width: 1, color: INK });
  } else if (kind === "beetle") {
    const step = moving ? Math.sin(t / 70) * 2.5 : 0;
    for (const dy of [-5, 0, 5]) g.moveTo(-10, dy + (dy ? step : -step)).lineTo(10, dy - (dy ? step : -step));
    g.stroke({ width: 1.5, color: INK });
    g.ellipse(0, 0, 8, 10).fill(0x2f5d50).stroke({ width: 1.5, color: INK }).rect(-0.6, -8, 1.2, 17).fill({ color: INK, alpha: 0.6 });
    g.circle(0, -11, 4).fill(INK).ellipse(-3, -3, 2, 3).fill({ color: 0xffffff, alpha: 0.35 });
  } else if (kind === "mouse") {
    const twitch = Math.sin(t / 110) * 1.2;
    g.ellipse(0, 9, 13, 3).fill({ color: INK, alpha: 0.14 });
    g.moveTo(10, 4).bezierCurveTo(20, 6 + twitch, 18, -6, 25, -4 - twitch).stroke({ width: 1.6, color: 0xc9a3a0 });
    g.ellipse(0, 0, 12, 8).fill(0xa39a92).stroke({ width: 1.5, color: INK });
    g.circle(-6, -8, 4.5).fill(0xc9a3a0).stroke({ width: 1.2, color: INK }).circle(-11, -3, 4).fill(0xa39a92).stroke({ width: 1.2, color: INK });
    g.circle(-9, -1, 1.3).fill(INK).circle(-13.5 - twitch * 0.3, 2, 1.5).fill(0xe58fb1);
  } else {   // bird
    const hop = moving ? Math.abs(Math.sin(t / 110)) * 5 : Math.max(0, Math.sin(t / 400)) * 1.5, y = -hop;
    g.ellipse(0, 10, 9, 2.5).fill({ color: INK, alpha: 0.14 });
    g.moveTo(-3, 8).lineTo(-3, 3 + y).moveTo(3, 8).lineTo(3, 3 + y).stroke({ width: 1.3, color: 0xd9772e });
    g.poly([8, y - 2, 17, y - 7, 15, y + 2]).fill(0x3f6f8f).stroke({ width: 1, color: INK });
    g.ellipse(0, y - 3, 10, 8).fill(0x5f93b8).stroke({ width: 1.5, color: INK }).ellipse(2, y - 2, 5, 4).fill(0x3f6f8f);
    g.circle(-7, y - 10, 5.5).fill(0x5f93b8).stroke({ width: 1.5, color: INK }).circle(-8.5, y - 11, 1.2).fill(INK);
    g.poly([-12, y - 10, -17, y - 8.5, -12, y - 7]).fill(0xf2c94c).stroke({ width: 1, color: INK });
    g.ellipse(-2, y + 1, 5, 3).fill({ color: 0xf3e3c4, alpha: 0.9 });
  }
}

/** A gold tag on something handed down (§5.3). */
export function heirloomMark(g: Graphics, x: number, y: number) {
  g.poly([x - 4, y, x + 4, y, x + 4, y + 11, x, y + 7, x - 4, y + 11]).fill(0xe2b33c).stroke({ width: 1, color: INK });
  g.circle(x, y, 4.5).fill(0xf2c94c).stroke({ width: 1, color: INK });
}
