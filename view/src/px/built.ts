// Decorating (SPEC-v3.5 §4.2): the paint a room wears. Each painted place (a stretch of the north wall, a patch of
// floor, a rug) is a wash of the dye's colour with a simple pattern through it in the painter's own coat colour, so a
// family's rooms come to look like it. Paint fades: the fainter the engine says it is, the fainter it is drawn.
// (What is built is drawn by still.ts like any fixture, from the sprite the engine names for it: `Obj.build`.)
import { Graphics } from "pixi.js";
import { PALETTE } from "../things";
import type { Painted } from "../types";
import { OX, OY, TILE } from "./geom";
import type { Rect } from "./geom";
import { hslInt } from "./tint";

/** Where a painted place is, in the room's pixels. `north`: the face of the north wall; `rug`: the rug's own picture. */
export function paintRect(p: Painted, north: Rect, rug?: Rect): Rect | null {
  if (p.where === "rug") return rug ? { x: Math.round(rug.x) + 2, y: Math.round(rug.y) + 2, w: Math.round(rug.w) - 4, h: Math.round(rug.h) - 4 } : null;
  if (typeof p.at === "string") return null;
  const x = OX + p.at[0] * TILE;
  return p.where === "wall" ? { x: x + 1, y: north.y + 2, w: 3 * TILE - 2, h: north.h - 5 } : { x: x + 1, y: OY + p.at[1] * TILE + 1, w: 3 * TILE - 2, h: 2 * TILE - 2 };
}

/** One painted place, drawn into `g`. */
export function paintOn(g: Graphics, r: Rect, p: Painted) {
  const base = parseInt((PALETTE[p.color] ?? PALETTE.grey).slice(1), 16), coat = hslInt(p.hue, 0.65, 0.62), k = Math.max(0.15, Math.min(1, p.strength ?? 1));
  const wash = (p.where === "wall" ? 0.62 : 0.5) * k, mark = 0.9 * k, small = r.w < 20;
  g.rect(r.x, r.y, r.w, r.h).fill({ color: base, alpha: wash });
  if (p.pattern === "stripes") {   // up and down a wall, across a floor
    if (p.where === "wall") for (let x = r.x + 3; x + 3 <= r.x + r.w; x += 8) g.rect(x, r.y, 3, r.h);
    else for (let y = r.y + 2; y + 2 <= r.y + r.h; y += small ? 4 : 6) g.rect(r.x, y, r.w, 2);
  } else if (p.pattern === "dots") {   // in rows, each row half a step along from the last
    const step = small ? 4 : 6;
    for (let y = r.y + 2, row = 0; y + 2 <= r.y + r.h; y += step, row++) for (let x = r.x + 2 + (row % 2 ? step / 2 : 0); x + 2 <= r.x + r.w; x += step) g.rect(x, y, 2, 2);
  } else {   // a border: a line all the way round, a little in from the edge, with a square at each corner
    const i = small ? 1 : 2, t = small ? 1 : 2;
    g.rect(r.x + i, r.y + i, r.w - 2 * i, t).rect(r.x + i, r.y + r.h - i - t, r.w - 2 * i, t).rect(r.x + i, r.y + i, t, r.h - 2 * i).rect(r.x + r.w - i - t, r.y + i, t, r.h - 2 * i);
    if (!small) g.rect(r.x + 6, r.y + 6, 3, 3).rect(r.x + r.w - 9, r.y + 6, 3, 3).rect(r.x + 6, r.y + r.h - 9, 3, 3).rect(r.x + r.w - 9, r.y + r.h - 9, 3, 3);
  }
  g.fill({ color: coat, alpha: mark });
  g.rect(r.x, r.y, r.w, 1).rect(r.x, r.y + r.h - 1, r.w, 1).rect(r.x, r.y, 1, r.h).rect(r.x + r.w - 1, r.y, 1, r.h).fill({ color: 0x1a1420, alpha: 0.22 * k });   // a soft edge, so a patch reads as paint and not as a tile
}

/** What a painted place is, for the pointer: "a stretch of wall painted in red dots". */
export const paintTitle = (p: Painted) => `${p.where === "wall" ? "a stretch of wall" : p.where === "floor" ? "a patch of floor" : "a rug"} painted in ${p.color} ${p.pattern}`;
export const paintText = (p: Painted) => `painted by ${p.name}${(p.strength ?? 1) < 0.5 ? "; it is fading" : ""}`;
