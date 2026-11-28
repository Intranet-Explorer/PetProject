// For checks only (SPEC-v3.6c §4, §5): the yard and the meadow laid over a house whose engine does not have them yet,
// as the contract has them (PLAN.md): the two rooms below the garden with their fixtures and forage from the layouts,
// the garden's south gate, hobs out there (by the fire pit, on the bench, foraging), the creatures (a rabbit, a squirrel,
// a hedgehog, butterflies, birds; an owl at dusk), and the weather, hour and season asked for; the great clear-out's two
// banners and the season for something new ("SOMETHING NEW: THE KILN") with its "new" badges. Nothing runs unless
// `petView.fakeOutdoors()` is called (or the page is opened with `?fakeoutdoors`, `=rain`, `=snow,meadow`, `=dusk`,
// `=autumn`, `=night`, `=shut` and so on, comma-separated); `petView.fakeOutdoors(null)` stops it.
import type { BitSpot, Creature, Moment, Obj, PetV, RoomV, Snap, Spotlight, Tile } from "./types";

/** `weather`, `season`, `hour` (and `phase`): the sky out there; `shut`: the gate shut (and why); `banners`: the clear-out's
 *  and the spotlight's moments; `hobs`: false leaves the hobs where they are. */
export type FakeOutdoors = { weather?: string; season?: string; hour?: number; phase?: "day" | "dusk" | "night"; shut?: string | null; banners?: boolean; hobs?: boolean; ms?: number };

type Lay = { fixtures: Record<string, { pos: Tile; water?: Tile[]; layer?: string }>; bit_spots?: Record<string, Tile[]>; blocked?: Tile[] };
const SAYS: Record<string, string> = { "shade tree": "a big leafy tree that throws shade over the bench", "yard bench": "a wooden bench under the shade tree", "fire pit": "a ring of stones with logs in it",
  woodpile: "split logs stacked by the shed", shed: "a small wooden shed", stream: "a stream running along the meadow's foot", "clay bank": "a bank of wet clay",
  footbridge: "a small wooden footbridge", "big tree": "an old tree with wide branches", bramble: "a bramble heavy with berries", boulder: "a big mossy boulder" };
const BEASTS: [string, string, string][] = [["rabbit", "ryard", "nibbling the grass"], ["squirrel", "ryard", "running along the fence"], ["bird", "ryard", "hopping about the path"],
  ["hedgehog", "rmeadow", "snuffling in the long grass"], ["butterfly", "rmeadow", "flitting over the wildflowers"], ["butterfly", "rmeadow", "flitting over the wildflowers"],
  ["bird", "rmeadow", "pecking by the stream"], ["owl", "ryard", "watching from the shed's roof"]];

let timer = 0;
export async function fakeOutdoors(get: () => Snap | null, tweak: (over: Record<string, unknown> | null) => void, o: FakeOutdoors | null = {}) {
  clearInterval(timer);
  if (!o) return tweak(null);
  const s0 = get(), garden = s0?.rooms.find((r) => r.type === "garden");
  if (!s0 || !garden) return console.warn("fakeOutdoors: no garden");
  const lays: Record<string, Lay> = {};
  for (const t of ["yard", "meadow"]) lays[t] = await (await fetch(`/art/rooms/${t}.json`)).json();
  const r = (n: number) => Math.floor(Math.random() * n), phase = o.phase ?? (o.hour == null ? "day" : o.hour >= 21 || o.hour < 5 ? "night" : o.hour >= 18 ? "dusk" : "day");
  const hour = o.hour ?? (phase === "dusk" ? 19.2 : phase === "night" ? 23 : 15);
  const room = (id: string, type: string, cell: Tile, doors: Record<string, string>, name: string): RoomV => {
    const L = lays[type], objects: Record<string, Obj> = {}, spots: BitSpot[] = [];
    for (const [n, f] of Object.entries(L.fixtures)) objects[n] = { pos: f.pos, state: n === "fire pit" ? (phase === "day" ? "off" : "on") : null, says: SAYS[n], ...(f.water ? { water: f.water } : {}),
      fix: n === "fire pit" ? { rest: 1.5, cozy: true } : n === "yard bench" ? { rest: 2.5 } : n === "shed" ? { store: 6 } : {} };
    for (const [bit, tiles] of Object.entries(L.bit_spots ?? {})) tiles.forEach((t, i) => i < 2 && spots.push({ bit, pos: t, loose: false, ready: i === 0 }));
    return { id, cell, type, doors, name, paint: { wall: null, floor: null }, shut: [], wet: false, cold: o.weather === "snow", lit: false, sounding: false, found: s0.tick - 50, by: null, objects, spots, outdoor: true };
  };
  const yard = room("ryard", "yard", [2, 3], { north: garden.id, west: "rmeadow" }, "the yard"), meadow = room("rmeadow", "meadow", [1, 3], { east: "ryard" }, "the meadow");
  const free = (rm: RoomV): Tile[] => {
    const L = lays[rm.type!], busy = new Set([...(L.blocked ?? []), ...Object.values(L.fixtures).flatMap((f) => [f.pos, ...(f.water ?? [])])].map(String));
    const out: Tile[] = [];
    for (let y = 0; y < 8; y++) for (let x = 0; x < 12; x++) if (!busy.has(String([x, y]))) out.push([x, y]);
    return out;
  };
  const open = { ryard: free(yard), rmeadow: free(meadow) } as Record<string, Tile[]>;
  const beasts: Creature[] = BEASTS.filter(([k]) => k !== "owl" || phase !== "day").map(([kind, rm, doing], i) => ({ id: `cout${i}`, kind, room: rm, pos: open[rm][r(open[rm].length)], doing, carry: null }));
  const owl = beasts.find((b) => b.kind === "owl");
  if (owl) owl.pos = [10, 2];
  const hobs = s0.pets.filter((p) => p.stage !== "egg" && p.stage !== "dead");
  const out: [string, Tile, string, string, string][] = [["ryard", [6, 4], "sitting by the fire pit", "fire pit", "rest"], ["ryard", [3, 2], "resting on the bench in the sun", "yard bench", "rest"],
    ["rmeadow", [4, 4], "picking berries off the bramble", "bramble", "hand"], ["ryard", [8, 3], "watching the rabbit", "rabbit", "eye"], ["rmeadow", [8, 5], "looking into the stream", "stream", "eye"]];
  const name = (i: number) => hobs[i % Math.max(1, hobs.length)]?.label ?? "Oya";
  let n = 0;
  const moments: Moment[] = [];
  const workshop = s0.rooms.find((x) => Object.keys(x.objects).includes("kiln")) ?? s0.rooms.find((x) => x.type === "workshop");
  const spots: Spotlight[] = [
    { key: "kiln", title: "THE KILN", what: "the kiln", room: workshop?.id ?? null, thing: workshop && workshop.objects.kiln ? "kiln" : Object.keys(workshop?.objects ?? {})[0] ?? null, since: s0.tick, until: s0.tick + 9000, tried: [], ended: null },
    { key: "outdoors", title: "THE OUTDOORS", what: "the yard and the meadow", room: "ryard", thing: "fire pit", since: s0.tick, until: s0.tick + 9000, tried: hobs.slice(0, 1).map((p) => p.id), ended: null }];
  const step = () => {
    const s = get();
    if (!s) return;
    n++;
    const tick = s.tick + n, top = (s.moments.at(-1)?.n ?? 0) + moments.length + 1;
    const say = (kind: string, text: string, room: string | null) => moments.push({ n: top, tick, day: s.clock.day, hour, kind, text, pet: null, room });
    if (o.banners !== false && n === 2) say("clearout", "The great clear-out: everything lying about the house goes to the store or the Works", null);
    if (o.banners !== false && n === 5) say("spotlight", "Something new: the kiln", spots[0].room);
    if (o.banners !== false && n === 8) say("clearout done", "the house was cleared out: 48 things to the store, 112 to the Works", null);
    for (const b of beasts) if (b.kind !== "owl" && Math.random() < 0.7) {   // each about on its own
      const near = open[b.room].filter((t) => Math.abs(t[0] - b.pos[0]) + Math.abs(t[1] - b.pos[1]) === 1 + (b.kind === "butterfly" ? 1 : 0));
      if (near.length) b.pos = near[r(near.length)];
    }
    const rooms = [...s.rooms.filter((x) => x.id !== "ryard" && x.id !== "rmeadow").map((x) => (x.id === garden.id ? { ...x, doors: { ...x.doors, south: "ryard" } } : x)), yard, meadow];
    const pets = o.hobs === false ? s.pets : s.pets.map((p): PetV => {
      const i = hobs.findIndex((h) => h.id === p.id), w = out[i];
      return w ? { ...p, room: w[0], pos: w[1], asleep: false, act: null, plan: null, body: { activity: "outdoors", doing: w[2], icon: w[4], what: w[3], who: null, since: tick, passive: false, walking: false, goal: null } } : p;
    });
    const cleared = n < 8 ? { at: s0.tick, until: s0.tick + 600, done: null, to_store: 0, to_works: 0, moved: 0 } : { at: s0.tick, until: s0.tick + 600, done: tick, to_store: 48, to_works: 112, moved: 160 };
    tweak({ tick, rooms, pets, creatures: [...s.creatures.filter((c) => !c.id.startsWith("cout")), ...beasts.map((b) => ({ ...b }))], moments: [...s.moments, ...moments],
            outdoors: { open: !o.shut, why: o.shut ?? null }, clearout: cleared, spotlights: { on: spots, queue: [], done: [] },
            ...(o.weather ? { weather: o.weather } : {}), clock: { hour, phase, ...(o.season ? { season: o.season } : {}) } });
  };
  step();
  void name;
  timer = window.setInterval(step, o.ms ?? 2000);
}
