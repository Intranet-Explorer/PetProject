// The pet's body. Code draws, the pet never does. M4 swaps the fixed look for the genome (SPEC §11).
import { Graphics } from "pixi.js";

const INK = 0x16241f;

export function drawPet(g: Graphics, stage: string, distressed: boolean, asleep: boolean) {
  g.clear();
  if (stage === "egg") {
    g.ellipse(0, 0, 14, 18).fill(0xe9b872).stroke({ width: 2, color: INK });
    for (const [x, y] of [[-5, -6], [4, 2], [-2, 8], [6, -9]]) g.circle(x, y, 1.6).fill(0xb07a3a);
    return;
  }
  const r = stage === "child" ? 20 : 15;
  g.ellipse(0, r * 1.05, r * 0.9, 4).fill({ color: INK, alpha: 0.18 });
  g.ellipse(0, 0, r, r * 1.05).fill(distressed ? 0xc9a184 : 0xf08a2e).stroke({ width: 2, color: INK });
  for (const x of [-r * 0.32, r * 0.32]) {
    if (asleep) g.rect(x - r * 0.2, -r * 0.15, r * 0.4, 2).fill(INK);
    else g.circle(x, -r * 0.15, r * 0.2).fill(0xffffff).circle(x, -r * 0.12, r * 0.1).fill(INK);
  }
  if (asleep) for (const [x, y, s] of [[r, -r, 3], [r + 7, -r - 8, 4], [r + 15, -r - 18, 5]]) {
    g.poly([x, y, x + 2 * s, y, x, y + 2 * s, x + 2 * s, y + 2 * s]).stroke({ width: 1.5, color: INK }); // z z z
  }
}
