// For checks only (SPEC-v3.5.12 §5): a train driven through one room by the page itself, along that room's track as the
// snapshot's rail lays it, so the train can be watched and measured on a paused house. It comes in at one door, stops
// at the platform (its bell rung, its lid up), and goes out at another, or backs out of a dead end, round and round.
// Nothing runs unless `petView.fakeTrain(room)` is called (or the page is opened with `?faketrain=<room>`).
import type { Car, Creature, Snap, Tile } from "./types";

const OUT: Record<string, Tile> = { north: [0, -1], south: [0, 1], west: [-1, 0], east: [1, 0] };
const DIRS: Record<string, string> = { "0,1": "south", "1,0": "east", "0,-1": "north", "-1,0": "west" };

let timer = 0;
/** Drive the fake train through room `rid` (null stops it), a step every `ms`; `rider`: a hob riding in the tram. */
export function fakeTrain(get: () => Snap | null, tweak: (over: Record<string, unknown> | null) => void, rid: string | null, ms = 2000, rider: string | null = null) {
  clearInterval(timer);
  if (!rid) return tweak(null);
  const s0 = get(), rr = s0?.rail?.rooms?.[rid], room = s0?.rooms.find((r) => r.id === rid);
  if (!s0 || !rr || !room) return console.warn("fakeTrain: no rail in", rid);
  const door = (t: Tile) => Object.entries(s0.door_tiles).find(([, d]) => d[0] === t[0] && d[1] === t[1])?.[0] ?? "north";
  const away = (b: Tile[]) => Array.from({ length: 6 }, (): [string, Tile] => [room.doors[door(b[0])] ?? "elsewhere", b[0]]);
  const [a, b] = [rr.track[0], rr.track[1] ?? null];
  // the leading car's way: in from the next room, along a branch to the platform, out along another (or back the same)
  const seq: [string, Tile][] = [...away(a), ...a.map((t): [string, Tile] => [rid, t]), ...(b ? [...b].reverse().slice(1).map((t): [string, Tile] => [rid, t]) : []), ...(b ? away(b) : [])];
  const stop = 6 + a.length - 1;
  let h = 1, n = 0, wait = 0, back = false, bell = 0;
  const step = (i: number) => { const p = seq[Math.max(0, i - 1)][1], q = seq[Math.min(seq.length - 1, Math.max(1, i))][1]; return DIRS[`${Math.sign(q[0] - p[0])},${Math.sign(q[1] - p[1])}`]; };
  const dirAt = (i: number) => step(i) ?? step(i + 1) ?? "south";
  const tick = () => {
    const s = get();
    if (!s) return;
    if (wait > 0) { if (--wait === 0 && !b) back = true; }
    else if (!back && h < stop && h + 2 >= stop) { h = stop; wait = 3; bell = s.tick + n; }
    else if (back) { h -= 2; if (h - 4 < 0) { h = 1; back = false; } }
    else { h += 2; if (h - 4 >= seq.length) h = 1; }
    n++;
    const cars = [0, 1, 2].map((i): Car | null => { const j = h - 2 * i, e = seq[j]; return j < 0 || !e ? null : { room: e[0], pos: e[1], dir: dirAt(j) }; });
    const lead = back ? cars[2] : cars[0], moving = wait === 0;
    const trail = (back ? [] : seq.slice(Math.max(0, h - 7), h + 1).reverse());
    const train: Creature = { id: "cfake", kind: "train", name: null, room: lead?.room ?? rid, pos: lead?.pos ?? rr.platform, carry: null, doing: moving ? `on its way through ${room.name}` : `stopped in ${room.name}`,
      cars, trail, lead: back ? "tram" : "engine", moving, lid: moving ? "closed" : "open", bell, asleep: false, rider, load: 2, cargo: ["felt cushion", "jar", "jar"], speed: 2 };
    const tram = cars[2];
    tweak({ tick: s.tick + n, creatures: [...s.creatures.filter((c) => c.kind !== "train"), train],
            pets: s.pets.map((p) => (p.id === rider && tram ? { ...p, riding: "cfake", room: tram.room, pos: tram.pos } : p)) });
  };
  tick();
  timer = window.setInterval(tick, ms);
}
