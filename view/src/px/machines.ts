// SPEC-v3.6b §4: the machines move. still.ts draws each as it stands (`fix.built.<it>`, `.working`, the kiln's `.full`;
// a hot one's fire and embers as lamps); this adds what moves while `machine.state` is "working": the kiln's fire
// flickering and its chimney smoking, the loom's shuttle flying and the cloth growing on it, the millstone's top stone
// turning and flour sifting down, the forge's coals flickering and sparks off the anvil (a shower when the ring is
// heard: voice.ts sends "pet:anvil"), and the stove's pot bubbling and steaming while it has servings, with the dish
// itself set out beside the stove. Coordinates are in each picture's own pixels (own/src/machines.py cuts them).
import { Container, Graphics, Sprite } from "pixi.js";
import type { Machine, RoomV } from "../types";
import { has, size, tex } from "./assets";
import type { Fx } from "./fx";
import type { Rect } from "./geom";
import type { Still, Thing } from "./still";
import { REDUCE } from "./weather";

/** Where things are on each machine's picture: its fire (middle, half-size), its chimney's top, the anvil's face,
 *  the pot, the top stone (middle, half-size), where the flour comes out, the cloth on the loom (x0, y0, x1, y1). */
const AT = {
  kiln: { fire: [17, 24, 6, 4], smoke: [17, 1] },
  forge: { fire: [21, 19, 6, 3], smoke: [24, 2], anvil: [8, 26] },
  stove: { pot: [7, 8], smoke: [14, 0] },
  millstone: { stone: [20, 13, 11, 4], spout: [17, 35] },
  loom: { cloth: [9, 18, 26, 32] },
};
const CLOTH = [0x8a4a3a, 0xb8875a, 0x5a6a8a, 0xc9a86a];

type One = { name: string; t: Thing; m: Machine; g: Graphics; next: number; run: number };
/** Each run's longest `left`, by machine: how far along the loom's cloth is (kept across redraws of the room). */
const runs = new Map<string, number>();

export class Machines {
  private all: One[] = [];
  private dish: Sprite | null = null;
  /** The dish beside the stove, where it is drawn (for the pointer: the pot's card), and the stove's name. */
  pot: { rect: Rect; stove: string } | null = null;
  private struck = 0;
  private onRing = () => { this.struck = performance.now(); };

  constructor() { addEventListener("pet:anvil", this.onRing); }

  /** The room was drawn again: find its machines; their moving parts go in among what stands, just in front of each. */
  attach(still: Still, room: RoomV, add: (c: Container) => void) {
    this.detach();
    for (const t of still.things.values()) {
      const m = room.objects[t.name]?.machine;
      if (!m) continue;
      const g = new Graphics();
      g.zIndex = t.s.zIndex + 0.15;
      add(g);
      this.all.push({ name: t.name, t, m, g, next: 0, run: 0 });
    }
    this.update(room);
    const stove = this.all.find((o) => o.m.kind === "stove"), pot = stove?.m.pot;
    if (stove && pot && pot.servings > 0) {   // the dish, set out on the floor at the stove's right, a little smaller than a thing made
      const name = has(`dish.${pot.dish}`) ? `dish.${pot.dish}` : "dish.fish stew", s = (this.dish = new Sprite(tex(name))), sz = size(name), r = stove.t.rect;
      s.anchor.set(0.5, 1);
      s.position.set(Math.round(r.x + r.w + 3), Math.round(stove.t.y - 1));
      s.zIndex = stove.t.s.zIndex + 0.2;
      add(s);
      this.pot = { rect: { x: s.x - sz.w / 2, y: s.y - sz.h, w: sz.w, h: sz.h }, stove: stove.name };
    }
  }
  detach() {
    for (const o of this.all) o.g.destroy();
    this.all = [];
    this.dish?.destroy();
    this.dish = null;
    this.pot = null;
  }
  /** A snapshot: each machine as the room has it now (how long it has left, the pot). */
  update(room: RoomV) {
    for (const o of this.all) {
      o.m = room.objects[o.name]?.machine ?? o.m;
      const was = runs.get(o.name) ?? 0;
      runs.set(o.name, o.m.state === "working" ? (o.m.left > was ? o.m.left : was) : 0);   // a new run begins with more left than the last had
      o.run = runs.get(o.name)!;
    }
  }

  /** Every frame. */
  frame(now: number, fx: Fx) {
    const calm = REDUCE.matches ? 3 : 1;
    for (const o of this.all) {
      const { m, t, g } = o, r = t.rect, X = (x: number) => Math.round(r.x + x), Y = (y: number) => Math.round(r.y + y);
      g.clear();
      g.visible = t.s.visible;
      const working = m.state === "working", pot = m.kind === "stove" && (m.pot?.servings ?? 0) > 0;
      if (!working && !pot) continue;
      const due = now > o.next;
      if (due) o.next = now + 140 * calm;
      if (m.kind === "kiln" || m.kind === "forge") {
        const [fx0, fy0, hw, hh] = (AT[m.kind] as { fire: number[] }).fire;
        for (let i = 0; i < 5; i++) {   // the fire flickers: a few bright pixels come and go in it
          const k = Math.floor(now / (90 * calm)) + i * 7, x = ((k * 13) % (2 * hw)) - hw, y = ((k * 7) % (2 * hh)) - hh;
          g.rect(X(fx0 + x), Y(fy0 + y), 1, 1).fill({ color: i % 2 ? 0xfff3a0 : 0xffb040, alpha: 0.9 });
        }
        const [sx, sy] = AT[m.kind].smoke;
        if (due && Math.random() < 0.35) fx.spawn("wisp", X(sx) + (Math.random() - 0.5) * 2, Y(sy), { vy: -7, vx: 2, life: 2200, sway: 2, tint: 0x9a9490, alpha: 0.75 });
        if (due && m.kind === "kiln" && Math.random() < 0.1) fx.spawn("speck", X(fx0), Y(fy0 - hh), { vy: -12, vx: (Math.random() - 0.5) * 6, life: 700, tint: 0xffb040 });
        if (m.kind === "forge") {   // the anvil throws sparks: now and then, and a shower when the ring is heard
          const [ax, ay] = AT.forge.anvil, shower = now - this.struck < 60;
          if (shower) { this.struck = 0; fx.burst("speck", X(ax), Y(ay), 9, 26, { tint: 0xffd060, g: 60, life: 450 }); }
          else if (due && Math.random() < 0.18) fx.burst("speck", X(ax), Y(ay), 3, 16, { tint: 0xffc050, g: 60, life: 380 });
        }
      } else if (m.kind === "stove") {   // the pot bubbles and steams
        const [px, py] = AT.stove.pot;
        for (let i = 0; i < 3; i++) {
          const ph = ((now / (260 * calm)) + i * 0.37) % 1;
          if (ph < 0.6) g.rect(X(px - 3 + i * 3), Y(py - 1 - Math.floor(ph * 3)), 1, 1).fill({ color: 0xffd8a0, alpha: 1 - ph });
        }
        if (due && Math.random() < 0.3) fx.spawn("wisp", X(px) + (Math.random() - 0.5) * 4, Y(py - 3), { vy: -8, life: 1600, sway: 2, tint: 0xf4f6f8, alpha: 0.6 });
      } else if (m.kind === "millstone") {   // the top stone turns: the peg it is turned by goes round its rim, a glint opposite; flour sifts down
        const [cx, cy, rx, ry] = AT.millstone.stone, a = now / (700 * calm), at = (ang: number, k: number) => [X(cx + Math.cos(ang) * rx * k), Y(cy + Math.sin(ang) * ry * k)];
        const [gx, gy] = at(a + Math.PI, 0.6), [px, py] = at(a, 0.75);
        g.rect(gx, gy, 2, 1).fill(0xe4e8ec);
        g.rect(px - 1, py - 4, 3, 5).fill(0x2b1a10).rect(px, py - 3, 1, 3).fill(0xb07a48);
        const [fx1, fy1] = AT.millstone.spout;
        if (due && Math.random() < 0.5) fx.spawn("speck", X(fx1) + (Math.random() - 0.5) * 2, Y(fy1), { vy: 8, life: 500, tint: 0xf4ecd8 });
      } else if (m.kind === "loom") {   // the cloth grows from the bottom as the run goes on; the shuttle flies across above it
        const [x0, y0, x1, y1] = AT.loom.cloth, done = o.run ? Math.min(1, Math.max(0.1, 1 - m.left / o.run)) : 0.5;
        const open = Math.round((y1 - y0) * (1 - done));
        if (open > 0) {   // the warp not yet woven: dark between bare threads
          g.rect(X(x0), Y(y0), x1 - x0, open).fill(0x3a2418);
          for (let x = x0 + 1; x < x1; x += 2) g.rect(X(x), Y(y0), 1, open).fill(0xd8c8a8);
          g.rect(X(x0), Y(y0 + open - 1), x1 - x0, 1).fill(CLOTH[Math.floor(now / 1500) % CLOTH.length]);   // the newest row
        }
        const k = (now / (900 * calm)) % 2, s = k < 1 ? k : 2 - k, ease = s * s * (3 - 2 * s);
        const sx = X(x0 - 3 + ease * (x1 - x0 + 2)), sy = Y(y0 + Math.max(1, open - 2));
        g.rect(sx - 1, sy - 1, 8, 3).fill(0x2b1a10).rect(sx, sy, 6, 1).fill(0xf0d890);
      }
    }
  }

  destroy() { this.detach(); removeEventListener("pet:anvil", this.onRing); }
}
