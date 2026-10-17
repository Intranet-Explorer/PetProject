// SPEC-v3.5.7 §4: the house's big moments land. A house first, an ambition reached, the Works building something, a
// birth, a death and the visitor's star each drop in over the room on a hanging wood sign (Wood_Banner_02), swinging to
// rest: a headline, one line saying what, the pet's portrait and name, the thing's picture when there is one, pixel
// stars and a warm glow. A family first gets a smaller one; a birth a soft glowing one; a death a quiet grey one with
// the stone and no stars. One at a time, about five seconds each, a click takes one down. The caller takes the page to
// the room first.
import { el, face } from "./dom";
import { icon } from "./icons";
import { thingSprite } from "./sprite";
import { fam } from "./types";
import type { Moment, PetV, Snap } from "./types";

export type Ev = { n: number; kind: "house" | "family" | "ambition" | "works" | "birth" | "death" | "star" | "find"; head: string; line: string;
  pet: PetV | null; room: string | null; recipe: Record<string, unknown> | null };

const HEAD: Record<Ev["kind"], string> = { house: "FIRST IN THE HOUSE!", family: "FIRST IN ITS FAMILY", ambition: "IT DID IT!", works: "THE WORKS BUILT IT!",
  birth: "A NEW ONE!", death: "IN MEMORY", star: "A STAR FROM YOU", find: "FOUND IN THE POND!" };

/** What kind of big moment this is, from the engine's own words, or null for an ordinary one. */
export function classify(s: Snap, m: Moment): Ev | null {
  const k = m.kind === "first" ? (/ in the house\b/.test(m.text) ? "house" : /\bits family\b/.test(m.text) ? "family" : null)
    : m.kind === "ambition" ? (/did what it (meant|set out) to do/.test(m.text) ? "ambition" : null)
    : m.kind === "works" ? "works" : m.kind === "hatched" ? "birth" : m.kind === "death" ? "death" : m.kind === "star" ? "star" : m.kind === "find" ? "find" : null;
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
  const line = pet ? m.text.replace(new RegExp(`^${pet.label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*`), "") : m.text;
  const head = k === "find" && /\bnote\b|\bmessage\b/.test(m.text) ? "A MESSAGE IN A BOTTLE!" : HEAD[k];
  return { n: m.n, kind: k, head, line: line || m.text, pet, room: m.room, recipe };
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
    const ev = this.up, small = ev.kind === "family", quiet = ev.kind === "death", soft = ev.kind === "birth";
    this.go(ev);   // (the page goes to the room first)
    const who = ev.pet ? el("div", `who ${fam(ev.pet.family)}`, face(ev.pet, 48), el("span", "title", this.name(ev.pet).toUpperCase())) : null;
    const pic = ev.recipe ? thingSprite(ev.recipe as never, 4) : null;
    if (pic) pic.classList.add("thing");
    const stars = quiet ? [] : [[-8, 12, 2], [104, 40, 2], [14, -6, 1], [80, 100, 1], [-4, 96, 2]].map(([x, y, k]) => {
      const st = el("i", `spark k${k}`);
      st.style.left = `${x}%`;
      st.style.top = `${y}%`;
      return st;
    });
    const sign = el("div", "sign", el("div", "big title", ev.head), quiet ? el("div", "stone", icon("stone", 24)) : null, el("div", "sub", ev.line), who);
    this.box.className = `event ${ev.kind}${small ? " small" : ""}${reduce() ? " still" : ""}`;
    this.box.replaceChildren(el("div", "glowring"), ...(pic ? [pic] : []), sign, ...stars);
    this.box.hidden = false;
    this.sound(quiet ? "low" : soft ? "soft" : "chime");
    this.timer = setTimeout(() => this.next(), quiet ? 7000 : small ? 4000 : 5200);
  }
}
