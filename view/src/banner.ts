// SPEC-v3.5.7 §4: the house's big moments land. A house first, an ambition reached, the Works building something, a
// birth, a death and the visitor's star each drop in over the room on a hanging wood sign (Wood_Banner_02), swinging to
// rest: a headline, one line saying what, the pet's portrait and name, the thing's picture when there is one, pixel
// stars and a warm glow. A family first gets a smaller one; a birth a soft glowing one; a death a quiet grey one with
// the stone and no stars. One at a time, about five seconds each, a click takes one down. The caller takes the page to
// the room first.
import { el, face } from "./dom";
import { icon } from "./icons";
import { hasSprite, sprite, thingSprite } from "./sprite";
import { fam } from "./types";
import { composeThing } from "./parts";
import type { Invention } from "./parts";
import type { Burst, Moment, PetV, Snap } from "./types";

export type Ev = { n: number; kind: "house" | "family" | "ambition" | "works" | "birth" | "death" | "star" | "find" | "machine" | "dish" | "clearout" | "spotlight" | "design"
  | "bond" | "fight" | "killing" | "out" | "back" | "spirit"; head: string; line: string;   // SPEC-v4.0 §11   // SPEC-v4.2 §11: "spirit", one of SPIRIT's
  pet: PetV | null; room: string | null; recipe: Record<string, unknown> | null; sprite?: string; parts?: Invention["parts"]; pet2?: PetV | null;   // `pet2`: the other of two (a bond, a fight)   // `parts`: a design's, to draw it from   // `sprite`: the picture to show by name (a machine, a dish)
  quiet?: boolean };   // a grey one, with no stars (SPIRIT's `quiet`)

/** SPEC-v4.2 §11 (contracts.MOMENTS): v4.2's moments, each a banner with its headline; `quiet`: a grey one without
 *  stars. Gravely ill takes the page to its room, as every banner does. Only while the engine sends `spirit`. */
export const SPIRIT: Record<string, { head: string; quiet?: boolean }> = {
  "happening": { head: "SOMETHING IS HAPPENING" }, "secret found": { head: "A SECRET IS OUT!" }, "gravely ill": { head: "GRAVELY ILL", quiet: true },
  "poisoned": { head: "TAKEN ILL", quiet: true }, "belief acted": { head: "AS IT WAS TOLD" }, "tale": { head: "A TALE IS TOLD" },
  "taught first": { head: "YOU TAUGHT IT, AND IT DID IT!" }, "visitor back": { head: "YOU CAME BACK!" },
  "hoard found": { head: "A HOARD IS FOUND!" },   // SPEC-v5.3 §1.3 (helper B, habits.found)
  "near fall": { head: "A NEAR FALL!", quiet: true },   // v5.3.1: a hob's first shove by an edge (conflict.near_fall)
};

const HEAD: Record<Ev["kind"], string> = { house: "FIRST IN THE HOUSE!", family: "FIRST IN ITS FAMILY", ambition: "IT DID IT!", works: "THE WORKS BUILT IT!",
  birth: "A NEW ONE!", death: "IN MEMORY", star: "A STAR FROM YOU", find: "FOUND IN THE POND!",
  machine: "A NEW MACHINE!", dish: "THE FIRST COOKED DISH!", clearout: "THE GREAT CLEAR-OUT!", spotlight: "SOMETHING NEW!", design: "THE FIRST DESIGN!",
  bond: "A CLOSE BOND!", fight: "A FIGHT!", killing: "A KILLING", out: "DRIVEN OUT", back: "BACK HOME!", spirit: "" };

/** SPEC-v4.0 §11: a close bond (A's moment "bond"); a fight in which someone was hurt, a killing, a hob driven out and one
 *  coming back are C's bursts (burstEv), with both hobs from the moment of the same tick. */
function v4(s: Snap, m: Moment): Ev | null {
  if (m.kind !== "bond") return null;
  const ids = m.pets ?? (m.pet ? [m.pet] : []), pet = s.pets.find((p) => p.id === ids[0]) ?? null, pet2 = ids[1] ? s.pets.find((p) => p.id === ids[1]) ?? null : null;
  return { n: m.n, kind: "bond", head: HEAD.bond, line: m.text, pet, pet2, room: m.room, recipe: null };
}
const V4: Record<string, Ev["kind"]> = { fight: "fight", killing: "killing", "driven out": "out", "coming back": "back" };
const MACHINES = ["kiln", "loom", "millstone", "forge", "stove"];

/** SPEC-v3.6b: the house's first machine of a kind ("the first kiln in the house: Oya and Lantern built it") or its first
 *  dish ("the first cooked dish in the house: fish stew, by Oya"), from a burst: with the machine's or the dish's picture. */
export function burstEv(s: Snap, b: Burst): Ev | null {
  const k4 = V4[b.kind];
  if (k4) {
    const m = s.moments.find((x) => Math.abs(x.tick - b.tick) <= 1 && x.pets?.includes(b.pet)), ids = m?.pets ?? [b.pet], at = (i: number) => s.pets.find((p) => p.id === ids[i]) ?? null;
    return { n: -b.n, kind: k4, head: HEAD[k4], line: b.text, pet: at(0), pet2: ids.length > 1 ? at(1) : null, room: b.room, recipe: null };
  }
  if (b.kind !== "machine" && b.kind !== "dish") return null;
  const pet = s.pets.find((p) => p.id === b.pet) ?? null, [what, line] = b.text.includes(": ") ? [b.text.slice(0, b.text.indexOf(": ")), b.text.slice(b.text.indexOf(": ") + 2)] : [b.text, ""];
  const dish = b.kind === "dish" ? /^(.+?)(,| by )/.exec(line)?.[1] ?? s.rooms.flatMap((r) => Object.values(r.objects ?? {})).find((o) => o.machine?.pot)?.machine?.pot?.dish : null;
  const kind = MACHINES.find((k) => what.includes(k)), pic = b.kind === "dish" ? `dish.${dish}` : `fix.built.${kind}.working`;
  return { n: -b.n, kind: b.kind, head: b.kind === "machine" && kind ? `THE FIRST ${kind.toUpperCase()}!` : HEAD[b.kind], line: line || b.text, pet, room: b.room, recipe: null,
           sprite: [pic, `fix.built.${kind}`].find((n) => hasSprite(n)) };
}

/** SPEC-v3.6c §1, §3: the great clear-out starting and done, and a season for something new ("SOMETHING NEW: THE KILN",
 *  its title from house.spotlights): with the train's cart, or the new thing's picture. */
function v36c(s: Snap, m: Moment): Ev | null {
  if (m.kind === "clearout" || m.kind === "clearout done") {
    const done = m.kind === "clearout done", c = s.clearout;
    const line = done ? m.text : m.text.replace(/^the great clear-out:\s*/i, "") || "everything lying about goes to the store or the Works";
    return { n: m.n, kind: "clearout", head: done ? "ALL CLEARED OUT!" : HEAD.clearout, line: done && c?.done && !/\d/.test(m.text) ? `${c.to_store} things to the store, ${c.to_works} to the Works` : line,
             pet: null, room: m.room, recipe: null, sprite: ["creature.train.cart", "crate.open"].find((n) => hasSprite(n)) };
  }
  if (m.kind !== "spotlight") return null;
  const all = [...(s.spotlights?.on ?? []), ...(s.spotlights?.queue ?? []), ...(s.spotlights?.done ?? [])], text = m.text.toLowerCase();
  const sp = all.find((x) => x.what && text.includes(x.what.toLowerCase())) ?? all.filter((x) => x.since <= m.tick).sort((a, b) => b.since - a.since)[0];
  const title = sp?.title ?? m.text.replace(/^something new:\s*/i, "").toUpperCase(), where = s.rooms.find((r) => r.id === (sp?.room ?? m.room))?.name;
  const pics = sp ? [`fix.built.${sp.key}.working`, `fix.built.${sp.key}`, `kind.${sp.key}`, `fix.${sp.thing}`, `icon.room.${s.rooms.find((r) => r.id === sp.room)?.type}`] : [];
  return { n: m.n, kind: "spotlight", head: `SOMETHING NEW: ${title}`, line: `${sp?.what ?? m.text.replace(/^something new:\s*/i, "")}${where ? `, in ${where}` : ""}: new to the house, for everyone to try`,
           pet: null, room: sp?.room ?? m.room, recipe: null, sprite: pics.find((n) => hasSprite(n)) };
}

/** What kind of big moment this is, from the engine's own words, or null for an ordinary one. */
export function classify(s: Snap, m: Moment): Ev | null {
  const sp = s.spirit ? SPIRIT[m.kind] : undefined;
  if (sp) {   // SPEC-v4.2 §11
    const pet = s.pets.find((p) => p.id === m.pet) ?? null;
    return { n: m.n, kind: "spirit", head: sp.head, quiet: sp.quiet, line: pet ? m.text.replace(new RegExp(`^${pet.label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*`), "") || m.text : m.text, pet, room: m.room, recipe: null };
  }
  const own = v36c(s, m) ?? v4(s, m);
  if (own) return own;
  if (m.matters === false) return null;   // SPEC-v4.0 §11: a first that does not matter goes in the story only
  const k = m.kind === "first" ? (/ in the house\b/.test(m.text) ? "house" : /\bits family\b/.test(m.text) ? "family" : null)
    : m.kind === "ambition" ? (/did what it (meant|set out) to do/.test(m.text) ? "ambition" : null)
    : m.kind === "works" ? "works" : m.kind === "hatched" ? "birth" : m.kind === "death" ? "death" : m.kind === "star" ? "star" : m.kind === "find" ? "find"
    : m.kind === "first design" || m.kind === "first working design" ? "design" : null;   // SPEC-v3.6d §8
  if (!k) return null;
  const pet = s.pets.find((p) => p.id === m.pet) ?? null;
  // the thing, when the moment is about one: what its maker made in that room within a few ticks of it
  let recipe: Record<string, unknown> | null = null;
  if (pet && k === "find") {   // SPEC-v3.6a §3, §6: a rare find, with its picture: what came out of the pond in its paws then
    for (const r of s.rooms) for (const o of Object.values(r.objects ?? {})) {
      const md = o.made;
      if (md?.found && md.found.by === pet.id && Math.abs(md.found.tick - m.tick) <= 3) recipe = md.recipe as unknown as Record<string, unknown>;
    }
  }
  if (pet && (k === "house" || k === "family" || k === "ambition" || k === "star")) {
    for (const r of s.rooms) for (const o of Object.values(r.objects ?? {})) {
      const md = o.made as { by?: string; tick?: number; recipe?: Record<string, unknown> } | undefined;
      if (md && md.by === pet.id && Math.abs((md.tick ?? -99) - m.tick) <= 3) recipe = md.recipe ?? null;
    }
  }
  let parts: Invention["parts"] | undefined;
  if (pet && k === "design") {   // the design it made, then: its newest in the house
    let at = -1;
    for (const r of s.rooms) for (const o of Object.values(r.objects ?? {})) if (o.made?.design && o.made.by === pet.id && o.made.parts?.length && o.made.tick > at) [parts, at] = [o.made.parts, o.made.tick];
  }
  const line = pet ? m.text.replace(new RegExp(`^${pet.label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*`), "") : m.text;
  const head = k === "find" && /\bnote\b|\bmessage\b/.test(m.text) ? "A MESSAGE IN A BOTTLE!" : m.kind === "first working design" ? "IT WORKS!" : HEAD[k];
  return { n: m.n, kind: k, head, line: line || m.text, pet, room: m.room, recipe, parts };
}

/** A picture made on the page, k times as big, its pixels kept sharp. */
function big(src: HTMLCanvasElement, k: number) {
  const c = Object.assign(document.createElement("canvas"), { className: "px", width: src.width * k, height: src.height * k }), g = c.getContext("2d")!;
  g.imageSmoothingEnabled = false;
  g.drawImage(src, 0, 0, c.width, c.height);
  return c;
}

const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export class Banners {
  private queue: Ev[] = [];
  private up: Ev | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  constructor(private box: HTMLElement, private name: (p: PetV) => string, private go: (ev: Ev) => void, private sound: (kind: string) => void) {
    box.onclick = () => this.next();
  }
  push(ev: Ev) {
    if (this.queue.some((q) => q.n === ev.n) || this.up?.n === ev.n) return;
    this.queue.push(ev);
    if (!this.up) this.next();
  }
  get showing() { return this.up; }
  private next() {
    clearTimeout(this.timer);
    this.up = this.queue.shift() ?? null;
    if (!this.up) { this.box.hidden = true; this.box.replaceChildren(); return; }
    const ev = this.up, small = ev.kind === "family", quiet = ev.quiet || ev.kind === "death" || ev.kind === "killing" || ev.kind === "out";
    this.go(ev);   // (the page goes to the room first)
    const one = (p: PetV) => [face(p, 48), el("span", `title ${fam(p.family)}`, this.name(p).toUpperCase())];
    const who = ev.pet ? el("div", `who ${fam(ev.pet.family)}`, ...one(ev.pet), ...(ev.pet2 ? [el("span", "and", ev.kind === "bond" ? "♥" : "&"), ...one(ev.pet2)] : [])) : null;   // (the line itself names them: the portraits say who is who)
    const pic = ev.sprite ? sprite(ev.sprite, ev.kind === "dish" || ev.sprite.startsWith("icon.") ? 4 : 2) : ev.parts ? big(composeThing({ parts: ev.parts, size: "large" }), 4) : ev.recipe ? thingSprite(ev.recipe as never, 4) : null;
    if (pic) pic.classList.add("thing");
    const stars = quiet ? [] : [[-8, 12, 2], [104, 40, 2], [14, -6, 1], [80, 100, 1], [-4, 96, 2]].map(([x, y, k]) => {
      const st = el("i", `spark k${k}`);
      st.style.left = `${x}%`;
      st.style.top = `${y}%`;
      return st;
    });
    const sign = el("div", "sign", el("div", "big title", ev.head), quiet && ev.kind !== "spirit" ? el("div", "stone", icon(ev.kind === "out" ? "out" : "stone", 24)) : ev.kind === "fight" ? el("div", "stone", icon("fist", 24)) : null, el("div", "sub", ev.line), who);
    this.box.className = `event ${ev.kind}${small ? " small" : ""}${reduce() ? " still" : ""}`;
    this.box.replaceChildren(el("div", "glowring"), ...(pic ? [pic] : []), sign, ...stars);
    this.box.hidden = false;
    this.sound(ev.kind);   // its jingle (sounds.json `banner.<kind>`)
    this.timer = setTimeout(() => this.next(), quiet ? 7000 : small ? 4000 : 5200);
  }
}
