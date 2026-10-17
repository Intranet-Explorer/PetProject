// For checks only (SPEC-v3.6a §6): the bigger pond laid over a house whose engine does not have it yet, so it can be
// seen and measured before the engine sends it. The contract's water (29 tiles), the dock, two hobs fishing (one with a
// rod from the dock's end, one by paw at the edge) who cast, wait, get a bite and pull something up over and over, now
// and then a rare find with its banner; a duck on the water and a frog at the edge. Nothing runs unless
// `petView.fakePond()` is called (or the page is opened with `?fakepond`); `petView.fakePond(null)` stops it.
import type { Creature, Fisher, Moment, Obj, Pond, Snap, Tile } from "./types";

/** `frozen`: deep winter, with a hole cut; `rain`: it rains; `dock`: false until the Works builds it; `stock`: fish in the pond. */
export type FakePond = { frozen?: boolean; rain?: boolean; dock?: boolean; stock?: number; ms?: number };

const WATER: Tile[] = [];
for (let y = 1; y <= 4; y++) for (let x = 2; x <= 5; x++) if (x !== 2 || y !== 1) WATER.push([x, y]);
WATER.push([6, 2], [6, 3]);
for (let y = 1; y <= 4; y++) for (let x = 7; x <= 9; x++) WATER.push([x, y]);
const wet = (t: Tile) => WATER.some((w) => w[0] === t[0] && w[1] === t[1]);
const COMMON = ["small fish", "small fish", "pebble", "shell", "reed", "waterlogged wood", "weed"], UNCOMMON = ["big fish", "glass bottle", "jar", "string", "hook", "spring"];
const RARE: [string, string][] = [["small bell", "bell"], ["lens", "lens"], ["gear", "gear"], ["ring", "ring"], ["old key", "key"], ["golden fish", "golden fish"]];

let timer = 0;
export function fakePond(get: () => Snap | null, tweak: (over: Record<string, unknown> | null) => void, o: FakePond | null = {}) {
  clearInterval(timer);
  if (!o) return tweak(null);
  const s0 = get(), room = s0?.rooms.find((r) => r.type === "pond");
  if (!s0 || !room) return console.warn("fakePond: no pond room");
  const rid = room.id, hobs = s0.pets.filter((p) => p.stage !== "egg" && p.stage !== "dead").slice(0, 2).map((p) => p.id);
  const dock = o.dock === false ? null : { tiles: [[3, 5], [3, 4], [3, 3]] as Tile[], end: [3, 3] as Tile };
  const holes: Tile[] = o.frozen ? [[4, 2]] : [];
  // where each sits and where its float goes: the dock's end (or the ice by the hole), and the east bank by paw
  const seats: { spot: Tile; line: Tile; rod: boolean }[] = [o.frozen ? { spot: [5, 2], line: [4, 2], rod: true } : dock ? { spot: [3, 3], line: [3, 2], rod: true } : { spot: [3, 5], line: [3, 4], rod: true },
    { spot: [10, 2], line: [9, 2], rod: false }];
  const r = (n: number) => Math.floor(Math.random() * n);
  let n = 0, today = 3, stock = o.stock ?? 9, finds = 0;
  const catches: Pond["catches"] = [], moments: Moment[] = [], found: Record<string, Obj> = {};
  const state = seats.map((_, i) => ({ cast: 0, bite: null as number | null, pulled: null as number | null, caught: null as Fisher["caught"], at: -i * 3 }));
  let duck: Tile = [4, 2], frog: Tile = [1, 4];
  const step = () => {
    const s = get();
    if (!s) return;
    n++;
    const tick = s.tick + n;
    state.forEach((f, i) => {   // cast; three ticks on something bites; the next it is pulled up; two more, cast again
      const k = n - f.at;
      if (k === 1) Object.assign(f, { cast: tick, bite: null, pulled: null, caught: null });
      else if (k === 3 + (i % 2)) f.bite = tick;
      else if (k === 4 + (i % 2)) {
        f.pulled = tick;
        const rare = seats[i].rod && n % 3 === 0, what = rare ? RARE[finds++ % RARE.length] : null, tier = rare ? "rare" : seats[i].rod && Math.random() < 0.3 ? "uncommon" : "common";
        const name = what?.[0] ?? (tier === "uncommon" ? UNCOMMON[r(UNCOMMON.length)] : COMMON[r(COMMON.length)]);
        let thing: string | null = null;
        if (what) {   // a find: a new thing in the room, and a moment for its banner
          thing = `${what[0]} from the pond ${finds}`;
          found[thing] = { pos: [2 + (finds % 3), 6], made: { id: `fake${finds}`, recipe: { name: thing, kind: what[1], material: "hard", purpose: "found in the pond" }, owner: hobs[i], owner_name: null, by: hobs[i],
            heirloom: null, behavior: null, active: false, uses: 0, ups: 0, useful: false, called: null, tick, worn: [], found: { from: "pond", tier: "rare", by: hobs[i], tick } } as never };
          const label = s.pets.find((p) => p.id === hobs[i])?.label ?? "Someone";
          moments.push({ n: (s.moments.at(-1)?.n ?? 0) + 1 + moments.length, tick, day: s.clock.day, hour: s.clock.hour, kind: "find", text: `${label} fished up ${/^[aeiou]/.test(what[0]) ? "an" : "a"} ${what[0]}`, pet: hobs[i], room: rid });
        }
        f.caught = { what: name, tier, thing };
        catches.push({ tick, pet: hobs[i], what: name, tier });
        today++;
        stock = Math.max(1, stock - 1);
      } else if (k >= 7) f.at = n;
    });
    if (n % 5 === 0) stock = Math.min(12, stock + 1);
    // the duck paddles from water tile to water tile; the frog hops along the bank
    const near = (t: Tile, ok: (u: Tile) => boolean) => { const c = ([[1, 0], [-1, 0], [0, 1], [0, -1]] as Tile[]).map(([dx, dy]): Tile => [t[0] + dx, t[1] + dy]).filter(ok); return c.length ? c[r(c.length)] : t; };
    if (!o.frozen) duck = near(duck, (u) => wet(u) && !(dock?.tiles.some((d) => d[0] === u[0] && d[1] === u[1])));
    if (n % 2 === 0) frog = near(frog, (u) => u[0] >= 0 && u[1] >= 0 && u[0] < 12 && u[1] < 8 && !wet(u) && WATER.some((w) => Math.abs(w[0] - u[0]) + Math.abs(w[1] - u[1]) === 1));
    const says = stock >= 8 ? "plenty of fish" : stock >= 4 ? "some fish" : "fished thin";
    const fishers: Fisher[] = state.map((f, i) => ({ pet: hobs[i], spot: seats[i].spot, line: seats[i].line, rod: seats[i].rod, ...f }));
    const pond: Pond = { room: rid, water: WATER, dock, frozen: !!o.frozen, holes, stock, most: 12, says, today, fishers, catches: catches.slice(-12) };
    // the room as the spreading left it: its fixtures at the edge, the bridge over the neck, nothing standing in the water
    const free: Tile[] = [[0, 2], [11, 1], [11, 3], [10, 0], [0, 6], [6, 7], [8, 7], [11, 7], [4, 7], [1, 0]];
    let fi = 0;
    const objects: Record<string, Obj> = {};
    for (const [name, ob] of Object.entries(room.objects)) {
      if (name === "pond bridge") objects[name] = { ...ob, pos: [6, 2] };
      else if (!ob.wall && !ob.on && !ob.water && wet(ob.pos)) objects[name] = { ...ob, pos: free[fi++ % free.length] };
      else objects[name] = ob;
    }
    const rooms = s.rooms.map((x) => (x.id === rid ? { ...x, objects: { ...objects, ...found }, spots: x.spots.filter((b) => b.on || !wet(b.pos) || b.bit === "lily") } : x));
    const pets = s.pets.map((p) => {
      const i = hobs.indexOf(p.id);
      if (i < 0) return p;
      const f = fishers[i], hold = f.pulled != null && f.caught && !f.caught.thing ? [f.caught.what === "small fish" ? "fish" : f.caught.what] : [];
      return { ...p, room: rid, pos: f.spot, asleep: false, act: null, plan: null, carrying: hold,
               body: { activity: "fish", doing: f.rod ? (dock && !o.frozen && i === 0 ? "fishing from the dock" : "fishing with a rod") : "fishing by paw", icon: "eye", what: "pond", who: null, since: f.cast, passive: false, walking: false, goal: null } };
    });
    const beasts: Creature[] = [...(o.frozen ? [] : [{ id: "cduck", kind: "duck", room: rid, pos: duck, doing: "paddling about the pond", carry: null } as Creature]),
      { id: "cfrog", kind: "frog", room: rid, pos: frog, doing: "sitting at the water's edge", carry: null }];
    tweak({ tick, pond, rooms, pets, creatures: [...s.creatures.filter((c) => c.kind !== "duck" && c.kind !== "frog"), ...beasts], moments: [...s.moments, ...moments],
            ...(o.rain ? { weather: "rain" } : {}), ...(o.frozen ? { weather: "snow", clock: { season: "winter" } } : {}) });
  };
  step();
  timer = window.setInterval(step, o.ms ?? 2000);
}
