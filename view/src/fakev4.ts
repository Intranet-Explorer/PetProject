// For checks only (SPEC-v4.0 §11): the characters laid over a house whose engine does not send them yet, as PLAN.md's
// contracts have them. Every hob awake in the room on screen, by day, each with its ten axes, a mood (each a different
// one), quirks, values, likings, its friends and enemy; one bruised, one with a bandaged head, one limping, one sick; two
// talking (a conversation that starts again every 40 seconds); a close bond, a rival, an enemy; the visitor's inbox; and,
// one after another, the moments v4.0 adds (a conversation, an insult, a gift, a scuffle that ends in blood, a fight that
// hurt, a close bond, a killing, justice driving a hob out, one coming back, a first that matters and one that does not),
// with C's bursts for the banners. Nothing runs unless
// `petView.fakeV4()` is called, or the page is opened with `?fakev4` (`=calm`: no moments, no banners; `=<mood>`: every
// hob in that mood; `=away`: the last visit was long ago); null stops it.
import type { Burst, Moment, PetV, Snap, Talk, Tile } from "./types";

export type FakeV4 = { mood?: string | null; moments?: boolean; ms?: number };

const AXES = ["brave", "tidy", "generous", "curious", "social", "honest", "patient", "playful", "ambitious", "kind"];
const GENE: Record<string, string> = { brave: "bold", tidy: "orderly", social: "sociable" };
export const MOODS = ["happy", "angry", "sad", "afraid", "proud", "excited", "grumpy", "ashamed", "lonely", "content"];
const QUIRKS = ["hums while working", "collects feathers", "afraid of the dark", "talks to the radio", "always the same chair", "counts things", "sleeps on its back", "hoards buttons"];
const VALUES = ["family", "craft", "knowledge", "beauty", "fairness", "comfort", "being first", "freedom", "the visitor"];
const hash = (s: string) => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
const LINES = [
  "You took the last of the berries again.", "I was hungry. You weren't even here.", "That's not the point. We share, or we don't eat.",
  "Fine. Tomorrow the first basket is yours.", "Promise? Say it like you mean it.", "I promise. Now stop glaring at me.",
];

let timer = 0;
export function fakeV4(get: () => Snap | null, tweak: (o: Record<string, unknown> | null) => void, room: () => string, o: FakeV4 | null = {}) {
  clearInterval(timer);
  if (o === null) return tweak(null);
  const s0 = get();
  if (!s0) return console.warn("fakeV4: no house yet");
  const hobs = s0.pets.filter((p) => p.stage !== "egg" && p.stage !== "dead");
  const ids = hobs.map((p) => p.id), H = (i: number) => ids[i % Math.max(1, ids.length)];
  const bursts: Burst[] = [], scuffles: NonNullable<Snap["scuffles"]> = [];
  const born = performance.now(), base = 1_000_000 + Math.max(0, ...s0.moments.map((m) => m.n)), moments: Moment[] = [];   // (numbered clear of the house's own, which go on coming)
  const liking = (a: string, b: string) => {
    const k = [a, b].sort().join();
    if (k === [H(0), H(1)].sort().join()) return 9;
    if (k === [H(0), H(2)].sort().join()) return -8;
    if (k === [H(1), H(3)].sort().join()) return -3;
    return (hash(a + b) % 15) - 4;
  };
  let n = 0;
  const step = () => {
    const s = get();
    if (!s) return;
    n++;
    const rid = room(), r = s.rooms.find((x) => x.id === rid), label = (id: string) => s.pets.find((p) => p.id === id)?.label ?? "someone";
    const say = (kind: string, text: string, pet: string, more: Partial<Moment> = {}) => moments.push({ n: base + moments.length + 1, tick: s.tick, day: s.clock.day, hour: s.clock.hour, kind, text, pet, room: rid, ...more });
    if (o.moments !== false) {
      const t = n * (o.ms ?? 1500), tickMs = s.tick_seconds * (s.pace ?? 1) * 1000;
      const at = (sec: number) => t >= sec * 1000 && t - (o.ms ?? 1500) < sec * 1000;
      const burst = (kind: Burst["kind"], text: string, pet: string) => bursts.push({ n: base + 500 + bursts.length, tick: s.tick, pet, room: rid, kind, text });
      if (at(3)) say("talk", `${label(H(0))} and ${label(H(1))} talked about the berries`, H(0), { lines: LINES.map((text, i) => ({ who: H(i % 2), text })) });
      if (at(8)) say("insult", `${label(H(2))} mocked ${label(H(0))}'s crooked pot in front of everyone`, H(2), { pets: [H(2), H(0)] });
      if (at(14)) say("gift", `${label(H(1))} gave ${label(H(0))} a blue feather`, H(1), { pets: [H(1), H(0)] });
      if (at(17)) scuffles.push({ n: 1, a: H(2), b: H(0), room: rid, pos: [5, 5], rung: 6, since: s.tick, until: s.tick + 6000 / tickMs, blood: [6, 4] });
      if (at(23)) { say("fight", `${label(H(2))} and ${label(H(0))} came to blows over the pot, and ${label(H(0))} was hurt`, H(2), { pets: [H(2), H(0)], hurt: true }); burst("fight", `${label(H(2))} hurt ${label(H(0))} in a fight over the pot`, H(2)); }
      if (at(28)) say("bond", `${label(H(0))} and ${label(H(1))} are close now: they nest together`, H(0), { pets: [H(0), H(1)] });
      if (at(34)) { say("killing", `${label(H(2))} killed ${label(H(3))} in the dark of the cellar`, H(2), { pets: [H(2), H(3)], hurt: true }); burst("killing", `${label(H(2))} killed ${label(H(3))}`, H(2)); }
      if (at(41)) { say("justice", `The family drove ${label(H(2))} out of the house, to live in the meadow`, H(2), { pets: [H(2)] }); burst("driven out", `${label(H(2))} was driven out, to live in the meadow`, H(2)); }
      if (at(48)) burst("coming back", `${label(H(4))} came back to the house after years in the meadow, changed`, H(4));
      if (at(53)) say("first", `${label(H(1))} cooked the first fish stew in the house`, H(1), { matters: true });
      if (at(56)) say("first", `${label(H(3))} sat on the cushion first in its family`, H(3), { matters: false });
    }
    // every hob awake, by day, in the room on screen, the two who talk side by side
    const spots: Tile[] = [[4, 4], [6, 4], [8, 5], [3, 6], [9, 3], [5, 6], [7, 6], [2, 4]];
    const cycle = Math.floor((performance.now() - born) / 40_000), began = born + cycle * 40_000;
    const pets: PetV[] = s.pets.map((p) => {
      const i = ids.indexOf(p.id);
      if (i < 0) return p;
      const likes = Object.fromEntries(ids.filter((q) => q !== p.id).map((q) => [q, liking(p.id, q)]));
      const ranked = Object.entries(likes).sort((a, b) => b[1] - a[1]), worst = ranked.at(-1);
      const traits = Object.fromEntries(AXES.map((a) => { const g = p.temper?.[GENE[a] ?? a]; return [a, g != null ? Math.round((2 * g - 1) * 100) / 100 : ((hash(p.id + a) % 200) - 100) / 100]; }));
      return { ...p, asleep: false, doing: p.asleep ? "sitting about" : p.doing, room: rid, pos: spots[i % spots.length] ?? p.pos, traits, mood4: o.mood ?? MOODS[i % MOODS.length], mood4_why: ["Bogna shared her fish", "someone broke its pot", "it misses its mother"][i % 3],
        quirks: [QUIRKS[hash(p.id) % QUIRKS.length], ...(i % 2 ? [QUIRKS[(hash(p.id) + 3) % QUIRKS.length]] : [])], values: [VALUES[hash(p.id) % VALUES.length], VALUES[(hash(p.id) + 4) % VALUES.length]],
        likes, top: { friends: ranked.filter(([, v]) => v > 0).slice(0, 2).map(([k]) => k), enemy: worst && worst[1] < 0 ? worst[0] : null, visitor: [6, -2, 3, 0, 8][i % 5] },
        hurt: i === 0 && n * (o.ms ?? 1500) > 20_000 ? { level: "hurt", since: s.tick, lasting: null } : i === 2 ? { level: "bruised", since: s.tick, lasting: null } : i === 3 ? { level: "badly hurt", since: s.tick, lasting: "limp" } : null,
        sick: i === 4 ? { level: "feverish", since: s.tick, from: "spoiled fish" } : null,
        aims: [{ text: "get clay for the kiln", why: "I want to be first to fire one", kind: "make" }, { text: "make up with " + label(H(i + 1)), why: "we argued", kind: "talk", target: H(i + 1) }],
        ambition: p.ambition ?? "be the best cook the house has known" };
    });
    const ms = performance.now() - began, talk: Talk = { n: 1000 + cycle, tick: s.tick - ms / (s.tick_seconds * (s.pace ?? 1) * 1000), room: rid, a: H(0), b: H(1),
      lines: LINES.map((text, i) => ({ who: H(i % 2), text })), came_of: ["an argument", "a gift promised"], after: { [H(0)]: { mood: "content", liking: 1 }, [H(1)]: { mood: "proud", liking: 1 } } };
    tweak({ pets, clock: { ...s.clock, hour: 11, phase: "day" }, v4: { traits: true, needs4: true, opinions: true, talk: true, ladder: true, health: true, brain4: true, planner: true, visitor4: true },
      talks: r ? [talk] : [], bonds: [{ a: H(0), b: H(1), kind: "close", since: s.tick - 500 }],
      ties: [{ a: H(0), b: H(1), kind: "close" }, { a: H(1), b: H(3), kind: "rival" }, { a: H(0), b: H(2), kind: "enemy" }, { a: H(3), b: H(4), kind: "friend" }],
      visitor4: { inbox: [{ n: 1, pet: H(1), q: "What is beyond the meadow?", tick: s.tick - 40, answer: null }, { n: 2, pet: H(3), q: "Why did the old one have to die?", tick: s.tick - 10, answer: null }],
        protect: {}, log: [{ tick: s.tick - 30, tool: "talk", pet: H(0), text: "How are you today?", said: "Hungry. And Pip took my berries again." }] },
      moments: [...s.moments, ...moments].slice(-200), bursts: [...(s.bursts ?? []), ...bursts], scuffles });
  };
  step();
  timer = window.setInterval(step, o.ms ?? 1500);
}

/** For checks: every hob's face in every mood (and asleep), then bruised, hurt, badly hurt, sick, and a limping walk,
 *  drawn large over the page. `petView.faceSheet()`; again to take it away. */
export function faceSheet(hobs: PetV[], sheet: typeof import("./petsprite").petSheet) {
  const old = document.getElementById("facesheet");
  if (old) return old.remove();
  const box = document.createElement("div"), Z = 4;
  box.id = "facesheet";
  box.style.cssText = "position:fixed;inset:0;z-index:99;background:#f4ead2;overflow:auto;padding:12px;font:14px 'Pixelify Sans',sans-serif;color:#2b2233";
  const cell = (c: HTMLCanvasElement, word: string) => {
    const f = document.createElement("figure"), k = document.createElement("canvas");
    f.style.cssText = "display:inline-block;margin:2px 6px;text-align:center";
    [k.width, k.height] = [c.width * Z, c.height * Z];
    const x = k.getContext("2d")!;
    x.imageSmoothingEnabled = false;
    x.drawImage(c, 0, 0, k.width, k.height);
    f.append(k, Object.assign(document.createElement("figcaption"), { textContent: word }));
    return f;
  };
  for (const p of hobs.slice(0, 3)) {
    const row = document.createElement("div"), stage = p.stage === "dead" ? "adult" : p.stage;
    row.append(...[...MOODS].map((m) => cell(sheet(p.genome, stage, { mood: m }).frames["stand.down"][0], m)),
      cell(sheet(p.genome, stage, {}).frames.sleep[0], "asleep"),
      cell(sheet(p.genome, stage, { hurt: 1 }).frames["stand.down"][0], "bruised"), cell(sheet(p.genome, stage, { hurt: 2 }).frames["stand.down"][0], "hurt"),
      cell(sheet(p.genome, stage, { hurt: 3 }).frames["stand.left"][0], "badly hurt"), cell(sheet(p.genome, stage, { sick: true }).frames["stand.down"][0], "sick"),
      ...sheet(p.genome, stage, { limp: true, hurt: 3 }).frames["walk.right"].map((c, i) => cell(c, `limp ${i + 1}`)));
    box.append(row);
  }
  document.body.append(box);
}
