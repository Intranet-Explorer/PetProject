// The pet's body (SPEC §11). The genome is numbers; this turns them into a sprite. The pet never draws.
import { Container, Graphics } from "pixi.js";

export type Genome = {
  roundness: number; stretch: number; wobble: number; hue: number; saturation: number; pattern: string;
  pattern_density: number; eye_size: number; eye_spacing: number; limbs: number; marks: string[];
};

const INK = 0x16241f;
const hsl = (h: number, s: number, l: number) => `hsl(${h}, ${Math.round(s * 100)}%, ${Math.round(l)}%)`;

/** The same pseudo-random numbers every redraw, so a pattern holds still. */
function fixedRandom(seed: number) {
  return () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);
}

export class PetBody extends Container {
  private shape = new Graphics();
  private pattern = new Graphics();
  private clip = new Graphics();
  private face = new Graphics();

  constructor() {
    super();
    this.pattern.mask = this.clip;
    this.addChild(this.shape, this.pattern, this.clip, this.face);
  }

  draw(g: Genome, stage: string, comfort: number, asleep: boolean) {
    const egg = stage === "egg";
    const size = { child: 18, youngling: 21, adult: 24 }[stage] ?? 15;   // it grows with each stage
    const [w, h] = egg ? [size * 0.85, size * 1.15] : [size, size * g.stretch];
    const corner = Math.min(w, h) * (egg ? 1 : g.roundness);
    const light = 36 + comfort * 0.24;                             // display only: brighter when comfortable
    const body = hsl(g.hue, g.saturation, light), dark = hsl(g.hue, g.saturation, light - 17);
    const outline = (to: Graphics) => to.roundRect(-w, -h, 2 * w, 2 * h, corner);

    this.shape.clear().ellipse(0, h + 2, w * 0.9, 4).fill({ color: INK, alpha: 0.18 });
    const sockets = [[-w * 0.55, h], [w * 0.55, h], [-w, h * 0.1], [w, h * 0.1]];
    for (const [x, y] of egg ? [] : sockets.slice(0, g.limbs)) this.shape.circle(x, y, 4.5).fill(dark).stroke({ width: 2, color: INK });
    outline(this.shape).fill(body).stroke({ width: 2, color: INK });
    outline(this.clip.clear()).fill(0xffffff);

    const p = this.pattern.clear(), rnd = fixedRandom(7);
    if (g.pattern === "speckle") {
      for (let i = 0; i < 4 + g.pattern_density * 26; i++) p.circle((rnd() * 2 - 1) * w, (rnd() * 2 - 1) * h, 1.7).fill(dark);
    } else if (g.pattern === "stripe") {
      const n = 2 + Math.round(g.pattern_density * 4), gap = (2 * h) / n;
      for (let i = 0; i < n; i++) p.rect(-w, -h + i * gap + gap * 0.3, 2 * w, gap * 0.35).fill(dark);
    } else if (g.pattern === "patch") {
      for (let i = 0; i < 1 + Math.round(g.pattern_density * 3); i++) p.circle((rnd() * 2 - 1) * w, (rnd() * 2 - 1) * h, w * 0.45).fill(dark);
    }
    if (g.marks.includes("a faded patch")) p.circle(w * 0.4, h * 0.35, w * 0.5).fill({ color: 0xffffff, alpha: 0.45 });

    const f = this.face.clear();
    if (g.marks.includes("a small notch")) f.poly([w * 0.35, -h - 1, w * 0.75, -h - 1, w * 0.55, -h + 6]).fill(INK);
    if (egg) return;
    const r = size * (0.1 + g.eye_size * 0.2), dx = w * (0.18 + g.eye_spacing * 0.6), y = -h * 0.2;
    for (const x of [-dx, dx]) {
      if (asleep) f.rect(x - r, y, 2 * r, 2).fill(INK);
      else f.circle(x, y, r).fill(0xffffff).circle(x, y + r * 0.2, r * 0.5).fill(INK);
    }
    if (asleep) for (const [x, zy, s] of [[w, -h, 3], [w + 7, -h - 8, 4], [w + 15, -h - 18, 5]]) {
      f.poly([x, zy, x + 2 * s, zy, x, zy + 2 * s, x + 2 * s, zy + 2 * s]).stroke({ width: 1.5, color: INK }); // z z z
    }
  }
}
