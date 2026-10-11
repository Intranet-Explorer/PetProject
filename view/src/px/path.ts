// Walking round furniture (SPEC-v3.2 §4). The engine's position is the truth and moves in straight lines; the room
// animates the walk along a path over the 12 x 8 floor that keeps off blocked tiles.
import type { Tile } from "../types";
import { FX, FY, idx, onFloor } from "./geom";

/** One byte a floor tile: 1 = nobody can stand there. */
export type Grid = Uint8Array;
export const grid = (blocked: Tile[] = []): Grid => {
  const g = new Uint8Array(FX * FY);
  for (const t of blocked) if (onFloor(t)) g[idx(t)] = 1;
  return g;
};

const STEPS: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];

/** The shortest way from one tile to another round what is blocked, both ends included. Diagonal steps never cut a
 *  corner. If there is no way (or an end is blocked), the straight line: better a slide than a pet that never arrives.
 *  ponytail: Dijkstra with a linear scan for the nearest open tile; 96 tiles, so nothing cleverer is needed. */
export function path(from: Tile, to: Tile, g: Grid): Tile[] {
  if (!onFloor(from) || !onFloor(to) || (from[0] === to[0] && from[1] === to[1])) return [from, to];
  const cost = new Float32Array(FX * FY).fill(Infinity), prev = new Int16Array(FX * FY).fill(-1), done = new Uint8Array(FX * FY);
  cost[idx(from)] = 0;
  for (;;) {
    let at = -1;
    for (let i = 0; i < cost.length; i++) if (!done[i] && cost[i] < Infinity && (at < 0 || cost[i] < cost[at])) at = i;
    if (at < 0) return [from, to];
    if (at === idx(to)) break;
    done[at] = 1;
    const [x, y] = [at % FX, Math.floor(at / FX)];
    for (const [dx, dy] of STEPS) {
      const n: Tile = [x + dx, y + dy];
      if (!onFloor(n) || g[idx(n)]) continue;
      if (dx && dy && (g[idx([x + dx, y])] || g[idx([x, y + dy])])) continue;
      const c = cost[at] + (dx && dy ? 1.4142 : 1);
      if (c < cost[idx(n)]) { cost[idx(n)] = c; prev[idx(n)] = at; }
    }
  }
  const out: Tile[] = [];
  for (let i = idx(to); i >= 0; i = prev[i]) out.unshift([i % FX, Math.floor(i / FX)]);
  return out;
}

/** The free tile nearest to `want` (itself, if it is free); among equals, the one nearest `prefer`. */
export function nearestFree(want: Tile, g: Grid, taken: Set<number>, prefer: Tile = want): Tile {
  let best: Tile | null = null, score = Infinity;
  for (let y = 0; y < FY; y++) for (let x = 0; x < FX; x++) {
    if (g[idx([x, y])] || taken.has(idx([x, y]))) continue;
    const s = Math.hypot(x - want[0], y - want[1]) * 100 + Math.hypot(x - prefer[0], y - prefer[1]) + (y < want[1] ? 0.5 : 0);   // rather in front of a thing than behind it
    if (s < score) [best, score] = [[x, y], s];
  }
  return best ?? want;
}

/** The smallest thing that fails if the above breaks; run by the development page. */
export function selfCheck() {
  const g = grid([[3, 0], [3, 1], [3, 2], [3, 3]]);   // a wall with a way round at y = 4
  const p = path([1, 1], [5, 1], g);
  console.assert(p.every((t) => !g[idx(t)]), "path crosses a blocked tile");
  console.assert(p.some((t) => t[1] >= 4), "path did not go round");
  console.assert(p.every((t, i) => !i || Math.max(Math.abs(t[0] - p[i - 1][0]), Math.abs(t[1] - p[i - 1][1])) === 1), "path jumps");
  const n = nearestFree([3, 1], g, new Set());
  console.assert(!g[idx(n)] && Math.abs(n[0] - 3) === 1, "nearestFree is not beside the blocked tile");
  console.assert(path([0, 0], [0, 0], g).length === 2, "standing still");
}
