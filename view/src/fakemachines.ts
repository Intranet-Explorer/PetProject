// For checks only (SPEC-v3.6b §4): the five machines laid over a house whose engine does not have them yet, as
// CONTRACT.md has them, so each can be seen and measured before the engine sends them. The kiln and the forge in the
// workshop, the millstone and the stove in the cellar, the loom in the nursery (or the music room); a hob at each,
// runs counting down and filling the trays; a pot of fish stew on the stove with two hobs eating from it; the first
// kiln's and the first dish's banners. Nothing runs unless `petView.fakeMachines()` is called (or the page is opened
// with `?fakemachines`, `?fakemachines=cold`, `=worn` or `=night`); `petView.fakeMachines(null)` stops it.
import type { Burst, BitSpot, Machine, Obj, PetV, Snap, Tile } from "./types";

/** `state`: every machine working (the default), all cold, or all worn; `night`: the house at night (embers glow);
 *  `bursts`: the first kiln's and first dish's banners; `hobs`: false leaves the hobs where they are (to see the
 *  machines whole); `ms`: how often a fake moment passes. */
export type FakeMachines = { state?: "working" | "cold" | "worn"; night?: boolean; bursts?: boolean; hobs?: boolean; ms?: number };

const SET: { kind: Machine["kind"]; room: string[]; at: Tile; tray: Tile; hob: Tile; doing: string; makes: string; led: string; icon: string; run: number }[] = [
  { kind: "kiln", room: ["workshop"], at: [9, 2], tray: [11, 2], hob: [9, 3], doing: "firing clay", makes: "fired brick", led: "KILN", icon: "flame", run: 40 },
  { kind: "forge", room: ["workshop"], at: [9, 5], tray: [11, 5], hob: [7, 5], doing: "forging metal", makes: "nail", led: "FORGE", icon: "anvil", run: 30 },
  { kind: "millstone", room: ["cellar"], at: [3, 5], tray: [1, 5], hob: [4, 6], doing: "grinding seed", makes: "flour", led: "MILL", icon: "grind", run: 20 },
  { kind: "stove", room: ["cellar"], at: [6, 3], tray: [6, 3], hob: [5, 4], doing: "cooking fish stew", makes: "fish stew", led: "STOVE", icon: "pot", run: 36 },
  { kind: "loom", room: ["nursery", "music"], at: [7, 5], tray: [9, 5], hob: [6, 5], doing: "weaving fibre", makes: "cloth", led: "LOOM", icon: "weave", run: 30 },
];
const AT: Record<string, string> = { kiln: "at the kiln", forge: "at the forge", millstone: "at the millstone", stove: "at the stove", loom: "on the loom" };

let timer = 0;
export function fakeMachines(get: () => Snap | null, tweak: (over: Record<string, unknown> | null) => void, o: FakeMachines | null = {}) {
  clearInterval(timer);
  if (!o) return tweak(null);
  const s0 = get();
  if (!s0) return console.warn("fakeMachines: no house yet");
  const hobs = s0.pets.filter((p) => p.stage !== "egg" && p.stage !== "dead");
  const name = (i: number) => hobs[i % Math.max(1, hobs.length)]?.label ?? "Oya";
  const state = o.state ?? "working", sec = (o.ms ?? 2000) / 1000;
  const live = SET.map((m) => ({ ...m, rid: m.room.map((t) => s0.rooms.find((r) => r.type === t)).find(Boolean)?.id, left: m.run * 0.6, waiting: m.kind === "stove" ? 0 : 2, made: 5, runs: 3 })).filter((m) => m.rid);
  let n = 0, servings = 3;
  const bursts: Burst[] = [];
  const step = () => {
    const s = get();
    if (!s) return;
    n++;
    const tick = s.tick + n;
    for (const m of live) if (state === "working") {   // a run counts down; done, what it made waits in its tray and another begins
      m.left -= sec;
      if (m.left <= 0) { m.left = m.run; m.runs++; m.made++; if (m.kind !== "stove") m.waiting = Math.min(9, m.waiting + 1); else servings = 4; }
    }
    if (n % 4 === 0 && servings > 0) servings--;   // ... and the pot is eaten from
    if (o.bursts !== false && (n === 2 || n === 6)) {
      const first = n === 2, top = Math.max(0, ...(s.bursts ?? []).map((b) => b.n), ...bursts.map((b) => b.n));
      const room = live.find((m) => m.kind === (first ? "kiln" : "stove"))?.rid ?? s.start;
      bursts.push({ n: top + 1, tick, pet: hobs[first ? 0 : 3 % hobs.length]?.id ?? "", room, kind: first ? "machine" : "dish",
                    text: first ? `the first kiln in the house: ${name(0)} and ${name(1)} built it` : `the first cooked dish in the house: fish stew, by ${name(3)}` });
    }
    const machine = (m: (typeof live)[number], i: number): Machine => {
      const working = state === "working", made: Record<string, number> = m.kind === "stove" ? { "fish stew": m.made, "bean soup": 2 } : { [m.makes]: m.made, ...(m.kind === "kiln" ? { glass: 1 } : {}) };
      const left = Math.ceil(m.left / 60);
      return { kind: m.kind, state, doing: working ? m.doing : null, left: working ? Math.round(m.left) : 0, makes: working ? m.makes : null, tray: m.kind === "stove" || !m.waiting ? {} : { [m.makes]: m.waiting },
               made, runs: m.runs, hot: ["kiln", "forge", "stove"].includes(m.kind), glow: state !== "worn" && (working || !!o.night), by: [name(i), name(i + 1)],
               led: state === "worn" ? `${m.led}: WORN` : m.kind === "stove" ? `STOVE: FISH STEW · ${servings} SERVINGS` : working ? `${m.led}: ${m.doing.split(" ")[0].toUpperCase()} · ${left} MIN` : `${m.led}: STILL`,
               pot: m.kind === "stove" && state !== "worn" ? { dish: "fish stew", servings, of: 4, from: ["fish", "bean"], by: hobs[3 % hobs.length]?.id ?? "", by_name: name(3), title: `${name(2)}'s fish stew`,
                                                           recipe_by: name(2), at: tick - 50, keeps: tick + 600, eating: servings ? [name(0), name(1)] : [] } : null };
    };
    const busy = new Set(live.flatMap((m) => [`${m.rid}|${m.at}`, `${m.rid}|${m.tray}`, `${m.rid}|${m.hob}`]));
    const rooms = s.rooms.map((r) => {
      const mine = live.filter((m) => m.rid === r.id);
      if (!mine.length) return r;
      const objects: Record<string, Obj> = {};
      for (const [k, ob] of Object.entries(r.objects)) if (ob.wall || ob.on || !busy.has(`${r.id}|${ob.pos}`)) objects[k] = ob;   // (what stood where a machine now stands is out of the way)
      const spots: BitSpot[] = r.spots.filter((b) => !busy.has(`${r.id}|${b.pos}`));
      for (const m of mine) {
        const i = live.indexOf(m), mc = machine(m, i);
        objects[m.kind] = { pos: m.at, state: null, fix: { [m.kind]: true }, says: `a ${m.kind}`, machine: mc,
                            build: { sprite: `fix.built.${m.kind}`, title: `the ${m.kind} ${name(i)} and ${name(i + 1)} built`, glow: mc.glow, worn: state === "worn" } };
        for (const [bit, k] of Object.entries(mc.tray)) for (let j = 0; j < k; j++) spots.push({ bit, pos: m.tray, loose: true, machine: m.kind });
      }
      return { ...r, objects, spots };
    });
    // a hob at each machine; at the stove, two eating from the pot besides the cook
    const at = new Map<string, { room: string; pos: Tile; body: PetV["body"] }>();
    if (o.hobs !== false) live.forEach((m, i) => {
      const h = hobs[i % hobs.length];
      if (!h || at.has(h.id)) return;
      at.set(h.id, { room: m.rid!, pos: m.hob, body: state === "working" ? { activity: "work a machine", doing: `${m.doing} ${AT[m.kind]}`, icon: m.icon, what: m.kind, who: null, since: tick, passive: false, walking: false, goal: null } : null });
      if (m.kind === "stove" && servings) for (const [k, pos] of [[0, [7, 4]], [1, [6, 5]]] as [number, Tile][]) {
        const e = hobs[(i + 1 + k) % hobs.length];
        if (e && !at.has(e.id)) at.set(e.id, { room: m.rid!, pos, body: { activity: "eat from the pot", doing: `eating fish stew with ${name(i)}`, icon: "bowl", what: "stove", who: h.id, since: tick, passive: false, walking: false, goal: null } });
      }
    });
    const pets = s.pets.map((p) => { const w = at.get(p.id); return w ? { ...p, room: w.room, pos: w.pos, asleep: false, act: null, plan: null, body: w.body } : p; });
    tweak({ tick, rooms, pets, bursts: [...(s.bursts ?? []), ...bursts], machines: live.map((m, i) => ({ room: m.rid!, name: m.kind, kind: m.kind, state, led: machine(m, i).led })),
            ...(o.night ? { clock: { hour: 23, phase: "night" } } : {}) });
  };
  step();
  timer = window.setInterval(step, o.ms ?? 2000);
}
