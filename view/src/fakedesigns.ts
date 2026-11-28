// For checks only (SPEC-v3.6d §9): designs laid over a house whose engine does not make them yet, as PLAN.md's
// contract has them. A hob with a design in hand at the bench (half its parts in place, one still missing), another
// building one beside it, and finished designs standing in the room, each with its effect working (a light, a warm
// kettle steaming, a music box, a bell, a horn, a watering can, a boat afloat, a cart with its load, a go-cart, a seed
// pot, a fan, a table lamp, an axe) and a jetpack sputtering because nothing in it lifts. The story gets the three new
// kinds of moment and the two banners. Nothing runs unless `petView.fakeDesigns()` is called, or the page is opened with
// `?fakedesigns` (`=night`: the house at night, to see the lights; `=fail`: every one just failed); null stops it.
import type { Design, DesignDone, Moment, Obj, PetV, Snap, Tile } from "./types";
import type { Invention } from "./parts";

export type FakeDesigns = { night?: boolean; fail?: boolean; only?: string | null; ms?: number };   // `only`: one effect's design, alone in the middle of the room

type One = { name: string; effect: string; spec: string[]; works?: Record<string, boolean> };
const COLOR: Record<string, string> = { wood: "brown", metal: "grey", iron: "grey", glass: "teal", cloth: "red", copper: "orange", brass: "yellow", leather: "brown", stone: "yellow", reed: "green", string: "white", wax: "white", clay: "orange", feather: "white" };
const SET: One[] = [
  { name: "hand lamp", effect: "light", spec: ["tube:metal", "lens@tip:glass"] },
  { name: "lantern on a pole", effect: "light", spec: ["pole:wood", "lamp shade@tip:metal", "glow stone@tip:stone"] },
  { name: "kettle", effect: "heat", spec: ["pot:copper", "spout@side:copper", "lid@top:copper"], works: { heat: true, pour: true } },
  { name: "music box", effect: "music", spec: ["box:wood", "piano keys@top", "wind-up key@side:brass"] },
  { name: "bell post", effect: "sound", spec: ["pole:wood", "bell dome@tip:brass", "rope@side:string"] },
  { name: "horn", effect: "signal", spec: ["pipe:brass", "horn@tip:brass"] },
  { name: "watering can", effect: "pour", spec: ["bucket:metal", "spout@side:metal"] },
  { name: "toy boat", effect: "float", spec: ["hull:wood", "sail@top:cloth"] },
  { name: "cart", effect: "carry", spec: ["box:wood", "wheel@base:wood", "handlebar@top:metal"] },
  { name: "go-cart", effect: "roll", spec: ["plank:wood", "wheel@base:wood", "seat@top:wood"] },
  { name: "seed pot", effect: "grow", spec: ["pot:clay", "soil@inside", "sprout@top"] },
  { name: "fan", effect: "cold", spec: ["stand:metal", "propeller@tip:metal"] },
  { name: "table lamp", effect: "soft light", spec: ["stand:wood", "lamp shade@tip:cloth", "glow stone@tip:stone"] },
  { name: "axe", effect: "cut", spec: ["pole:wood", "axe head@tip:iron"] },
  { name: "jetpack", effect: "lift", spec: ["tank:metal", "rocket@base:iron"], works: { lift: false } },
];
const parse = (spec: string[]): Invention["parts"] => spec.map((s, i) => { const [pa, mat] = s.split(":"), [part, at] = pa.split("@"); return { part, at: i ? at ?? null : null, material: mat, color: COLOR[mat] }; });
const HINT: Record<string, string> = { lift: "nothing in it pushes upward", light: "nothing in it glows" };

let timer = 0;
export function fakeDesigns(get: () => Snap | null, tweak: (over: Record<string, unknown> | null) => void, room: () => string, o: FakeDesigns | null = {}) {
  clearInterval(timer);
  if (!o) return tweak(null);
  const s0 = get();
  if (!s0) return console.warn("fakeDesigns: no house yet");
  const hobs = s0.pets.filter((p) => p.stage !== "egg" && p.stage !== "dead");
  const rid = room(), r0 = s0.rooms.find((r) => r.id === rid)!;
  // free tiles for the finished designs: two apart, away from what stands there
  const taken = new Set(Object.values(r0.objects).map((ob) => `${ob.pos}`)), free: Tile[] = [];
  for (let y = 2; y <= 6 && free.length < SET.length; y += 2) for (let x = 1; x <= 10 && free.length < SET.length; x += 2) if (!taken.has(`${x},${y}`) || r0.objects[Object.keys(r0.objects).find((k) => `${r0.objects[k].pos}` === `${x},${y}`)!]?.made) free.push([x, y]);
  const name = (i: number) => hobs[i % Math.max(1, hobs.length)]?.label ?? "Oya";
  let n = 0;
  const born = s0.tick, moments: Moment[] = [];
  const say = (kind: string, text: string, pet: PetV | undefined, tick: number) => moments.push({ n: Math.max(0, ...s0.moments.map((m) => m.n)) + moments.length + 1, tick, day: s0.clock.day, hour: s0.clock.hour, kind, text, pet: pet?.id ?? null, room: rid });
  const step = () => {
    const s = get();
    if (!s) return;
    n++;
    const tick = s.tick + n;
    if (n === 1 && !o.only) {
      say("first design", `${name(0)} designed the first thing in the house: a hand lamp`, hobs[0], tick);
      say("designed", `${name(0)} designed a hand lamp`, hobs[0], tick);
    }
    if (n === 3 && !o.only) { say("design built", `${name(1)} built the music box: it plays a tune`, hobs[1 % hobs.length], tick); say("first working design", `${name(1)}'s music box works: it plays a tune`, hobs[1 % hobs.length], tick); }
    if (n === 4 && !o.only) say("design failed", `${name(2)}'s jetpack sputtered and smoked and did not lift: nothing in it pushes upward`, hobs[2 % hobs.length], tick);
    // (the room's own made things are put out of sight, so that the designs are seen)
    const objects: Record<string, Obj> = Object.fromEntries(Object.entries(s.rooms.find((r) => r.id === rid)!.objects).filter(([, ob]) => !ob.made));
    const set = o.only ? SET.filter((d) => d.effect === o.only || d.name === o.only) : SET;
    set.forEach((d, j) => {
      const i = SET.indexOf(d);
      if (o.only) free[i] = [4 + j * 3, 3] as Tile;
      if (!free[i]) return;
      const fails = o.fail || d.works?.[d.effect] === false;
      const effects: DesignDone["effects"] = Object.fromEntries([...new Set([d.effect, ...Object.keys(d.works ?? {})])].map((e) => [e, (o.fail || d.works?.[e] === false) ? { works: false, hint: HINT[e] ?? "something in it is missing" } : { works: true, strength: 0.7 }]));
      objects[d.name] = { pos: free[i], state: null, says: `a ${d.name}`, effect_on: fails ? null : { effect: d.effect, until: tick + 100 }, sputter: fails ? tick : null,
        made: { id: `fd${i}`, recipe: { name: d.name, kind: d.name, material: "hard", purpose: `to ${d.effect}` }, owner: hobs[i % hobs.length]?.id ?? "", owner_name: name(i), by: hobs[i % hobs.length]?.id ?? "",
                heirloom: null, behavior: null, active: !fails, uses: 2, ups: 0, useful: !fails, called: null, tick: born - 20 + i, worn: [], title_shown: true,
                design: { id: 100 + i, effects, for: `to ${d.effect}`, how: "its parts do it together", by: hobs[i % hobs.length]?.id }, parts: parse(d.spec) } };
    });
    // a hob at the bench with a hand lamp half made (the glow stone still missing); another building a kettle beside it
    const hand: Design = { id: 1, name: "hand lamp", for: "a light I can carry into the attic", how: "the glow sits in the tube and the lens throws it forward", effects: ["light", "carry"], since: born,
      where: rid, at: "bench", placed: 2, need: 4, parts: [{ part: "tube", material: "metal", color: "grey", have: true, placed: true }, { part: "lens", material: "glass", color: "teal", have: true, placed: true },
        { part: "glow stone", material: "stone", color: "yellow", have: false, placed: false }, { part: "strap", material: "leather", color: "brown", have: true, placed: false }] };
    const kettle: Design = { id: 2, name: "kettle", for: "to warm water for the greenhouse", effects: ["heat", "pour"], since: born, where: rid, at: null, placed: 1 + (n % 3 === 0 ? 1 : 0), need: 3,
      parts: [{ part: "pot", material: "copper", color: "orange", have: true, placed: true }, { part: "spout", material: "copper", color: "orange", have: true, placed: n % 3 === 0 }, { part: "lid", material: "copper", color: "orange", have: false, placed: false }] };
    const pets = s.pets.map((p) => (p.id === hobs[0]?.id ? { ...p, design: hand, room: rid, pos: (o.only ? [2, 6] : [5, 5]) as Tile } : p.id === hobs[3 % hobs.length]?.id && hobs.length > 3 ? { ...p, design: kettle, room: rid, pos: [9, 5] as Tile } : p));
    tweak({ tick, pets, rooms: s.rooms.map((r) => (r.id === rid ? { ...r, objects } : r)), moments: [...s.moments, ...moments].slice(-200), ...(o.night ? { clock: { ...s.clock, hour: 23, phase: "night" } } : {}) });
  };
  step();
  timer = window.setInterval(step, o.ms ?? 2000);
}
