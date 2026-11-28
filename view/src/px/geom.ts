// The room's geometry (view/assets/README.md, "Geometry"), in source pixels: a canvas of 14 x 11 tiles of 16, with the
// engine's 12 x 8 floor starting at canvas tile [1, 2]. Everything in the room is placed in these units.
import type { Tile } from "../types";

export const TILE = 16, COLS = 14, ROWS = 11, W = COLS * TILE, H = ROWS * TILE;
export const FX = 12, FY = 8;                 // the floor, in tiles
export const OX = TILE, OY = 2 * TILE;        // where floor tile [0, 0] starts
export type Rect = { x: number; y: number; w: number; h: number };
export type Dir = "down" | "up" | "left" | "right";

export const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
export const hit = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
export const inside = (r: Rect, x: number, y: number) => x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h;
/** The top-left corner of a floor tile. */
export const corner = (t: Tile): [number, number] => [OX + t[0] * TILE, OY + t[1] * TILE];
/** Where something standing on a floor tile has its feet: the middle of the tile, a little above its lower edge. */
export const foot = (t: Tile): [number, number] => [OX + t[0] * TILE + TILE / 2, OY + t[1] * TILE + TILE - 3];
/** The floor tile under a point (clamped to the floor). */
export const tileAt = (x: number, y: number): Tile => [clamp(Math.floor((x - OX) / TILE), 0, FX - 1), clamp(Math.floor((y - OY) / TILE), 0, FY - 1)];
export const onFloor = (t: Tile) => t[0] >= 0 && t[1] >= 0 && t[0] < FX && t[1] < FY;
export const idx = (t: Tile) => t[1] * FX + t[0];

/** The same pseudo-random numbers for the same key, so scattered detail holds still between redraws. */
export function seeded(key: string) {
  let seed = 7;
  for (let i = 0; i < key.length; i++) seed = (seed * 31 + key.charCodeAt(i)) >>> 0;
  return () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
}
