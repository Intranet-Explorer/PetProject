// Small helpers for the DOM around the room. Everything from the engine is set as text, never as HTML.
import { svg } from "./icons";
import { petPortrait, petSheet } from "./petsprite";
import { bodyStage, hhmm, NEEDS } from "./types";
import type { Hello, Note, PetV, Snap } from "./types";

export const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
export type Kid = Node | string | number | null | undefined | false;

export function el(tag: string, cls = "", ...kids: Kid[]) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  e.append(...kids.filter((k) => k != null && k !== false).map((k) => (typeof k === "number" ? String(k) : (k as Node | string))));
  return e;
}

/** A button that looks like the text around it. */
export function link(text: string, go: () => void, cls = "link") {
  const b = el("button", cls, text) as HTMLButtonElement;
  b.type = "button";
  b.onclick = go;
  return b;
}

/** What every tab of the drawer is given. `api` holds what the engine last answered for each tab. */
export type Ctx = {
  snap: Snap; hello: Hello | null; sel: string | null; room: string; replay: boolean;
  api: Record<string, any>;
  voiceLab: Node;   // the voice lab, one node kept across redraws of the Lab tab
  jump: (to: { pet?: string | null; room?: string | null }) => void;
  show: (tab: string, pet?: string) => void;   // open a tab of the drawer ("mind": the Lab, on a pet's mind), on a pet if one is given
  redraw: () => void;                          // draw the open tab again, after a choice made inside it
  hear: (notes: Note[], by: string) => void;   // play a song as its singer would sing it
};

export const plural = (n: number, one: string, many = one + "s") => `${n} ${n === 1 ? one : many}`;
/** A tick as a day of the house, for "since day 3". */
export const dayOf = (snap: Snap, tick: number) => 1 + Math.floor((8 + (tick * snap.tick_seconds * 24) / snap.day_seconds) / 24);

/** A tick as a day and an hour: "day 3, 14:20". */
export function when(snap: Snap, tick: number) {
  const m = Math.round((8 + (tick * snap.tick_seconds * 24) / snap.day_seconds) * 60);   // the house starts at 08:00 on day 1
  return `day ${1 + Math.floor(m / 1440)}, ${hhmm(0, m % 1440)}`;
}
/** A length of real time, roughly: "under a minute", "about 20 minutes", "about 3 hours", "about 2 days". */
export function about(seconds: number) {
  const [n, unit] = seconds < 3600 ? [seconds / 60, "minute"] : seconds < 36 * 3600 ? [seconds / 3600, "hour"] : [seconds / 86400, "day"];
  return seconds < 60 ? "under a minute" : `about ${plural(Math.round(n), unit)}`;
}
/** Words the engine had to cut short end on a dash or a comma; shown, they trail off instead. */
export const whole = (text: string) => text.replace(/\s*[,;:—–-]\s*$/, "…");

export const GENES = ["curious", "sensitive", "sociable", "bold", "patient", "playful", "fertile", "hardy"];

/** Temperament as a small radial chart (§8.1): eight genes round a circle, each 0 to 1. */
export function radial(temper: Record<string, number>, size = 120, names = true) {
  const side = names ? 40 : 0, r = size / 2 - (names ? 16 : 2), cx = size / 2 + side, cy = size / 2;   // room at the sides for the long names
  const at = (i: number, k: number) => [cx + Math.sin((i / GENES.length) * 2 * Math.PI) * r * k, cy - Math.cos((i / GENES.length) * 2 * Math.PI) * r * k];
  const ring = (k: number) => GENES.map((_, i) => at(i, k).map((v) => v.toFixed(1)).join(",")).join(" ");
  const out = svg("svg", { viewBox: `0 0 ${size + 2 * side} ${size}`, width: size + 2 * side, height: size, class: "radial", role: "img",
                           "aria-label": "Temperament: " + GENES.map((g) => `${g} ${Math.round((temper[g] ?? 0) * 100)}`).join(", ") });
  out.append(svg("polygon", { points: ring(1), class: "ring" }), svg("polygon", { points: ring(0.5), class: "ring" }));
  GENES.forEach((g, i) => {
    const [x, y] = at(i, 1);
    out.append(svg("line", { x1: cx, y1: cy, x2: x, y2: y, class: "ring" }));
    if (names) {
      const [lx, ly] = at(i, 1.14);
      out.append(svg("text", { x: lx, y: ly + (ly < cy - 4 ? 0 : ly > cy + 4 ? 8 : 3), "text-anchor": Math.abs(lx - cx) < 4 ? "middle" : lx > cx ? "start" : "end" }, g));
    }
  });
  out.append(svg("polygon", { points: GENES.map((g, i) => at(i, Math.max(0.04, temper[g] ?? 0)).map((v) => v.toFixed(1)).join(",")).join(" "), class: "shape" }));
  return out;
}

/** A number as a small bar, 0 to `max`. */
export function bar(value: number, max = 100, cls = "") {
  const b = el("div", "bar " + cls), fill = el("b");
  fill.style.width = `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
  b.append(fill);
  return b;
}

/** Fill a panel again without shutting the sections the visitor has opened. */
export function refill(panel: HTMLElement, kids: Kid[]) {
  const open = new Set([...panel.querySelectorAll<HTMLElement>("details[open]")].map((d) => d.dataset.key));
  const top = panel.scrollTop, inner = new Map([...panel.querySelectorAll<HTMLElement>("[data-scroll]")].map((e) => [e.dataset.scroll, [e.scrollLeft, e.scrollTop]]));
  panel.replaceChildren(...kids.filter((k) => k != null && k !== false).map((k) => (typeof k === "number" ? String(k) : (k as Node | string))));
  for (const d of panel.querySelectorAll<HTMLDetailsElement>("details")) if (open.has(d.dataset.key)) d.open = true;
  panel.scrollTop = top;
  for (const e of panel.querySelectorAll<HTMLElement>("[data-scroll]")) {   // a box that scrolls by itself (the tree, a wide table) stays where it was scrolled to
    const at = inner.get(e.dataset.scroll);
    if (at) [e.scrollLeft, e.scrollTop] = at;
    else if (e.dataset.scroll === "tree") e.scrollTop = e.scrollHeight;   // first shown: the living, at the foot of the tree
  }
}

/** A folding section that remembers by `key` whether it was open. */
export function fold(key: string, summary: Kid, ...kids: Kid[]) {
  const d = el("details", "", el("summary", "", summary), ...kids);
  d.dataset.key = key;
  return d;
}

/** A box that scrolls by itself, and keeps its place by `key` when the panel is filled again. */
export function scroller(key: string, cls: string, ...kids: Kid[]) {
  const box = el("div", cls, ...kids);
  box.dataset.scroll = key;
  box.tabIndex = 0;   // so the keyboard can scroll it too
  return box;
}

/** A pet's body as a small still picture, pixel for pixel: as it is now, or as it was when it died. It is drawn at
 *  the largest whole-number scale that fits a square of `box` screen pixels. */
export function face(p: Pick<PetV, "genome" | "stage" | "stage_before">, box = 48, stage = bodyStage(p)) {
  const look = { grey: stage === "elder" ? 0.55 : 0 };
  const c = petPortrait(p.genome, stage, Math.max(1, Math.floor(box / petSheet(p.genome, stage, look).size)), look);
  c.classList.add("px", "face");
  if (p.stage === "dead") c.classList.add("dead");
  c.setAttribute("aria-hidden", "true");
  return c;
}

// ---- plain words (SPEC-v3.2 §6): the engine sends them; a recording made before it did has to be read into them ----

const STAGE: Record<string, string> = { egg: "egg", hatchling: "little one", child: "little one", youngling: "young one", adult: "grown", elder: "old one" };
/** A stage in plain words: little one, young one, grown, old one. */
export const stageWord = (p: Pick<PetV, "stage" | "stage_word" | "stage_before">) =>
  p.stage === "dead" ? "gone" : p.stage_word ?? STAGE[p.stage] ?? p.stage;
/** The same for a stage's name on its own (a life record says "as far as elder"). */
export const stageName = (stage: string) => STAGE[stage] ?? stage;

const FINE = ["not lonely", "awake", "fine", "interested"];   // the engine's words for a need that is merely met: said alone, each reads oddly
/** How a pet feels, in at most two plain words, the worst first. Never a number. When nothing is wrong it is the best
 *  of how it feels ("at ease", "fascinated"), or simply "content". */
export function moodWords(p: PetV): string[] {
  const plain = (words: string[]) => (words.length === 1 && FINE.includes(words[0]) ? ["content"] : words);
  if (p.mood) return plain(p.mood.slice(0, 2));
  if (!p.levels || !p.felt) return [];
  const low = NEEDS.filter((n) => p.levels![n] >= 2).sort((a, b) => p.levels![b] - p.levels![a]).slice(0, 2).map((n) => p.felt![n]);
  return low.length ? low : plain([p.felt[[...NEEDS].sort((a, b) => p.levels![a] - p.levels![b])[0]]]);
}

const ORDINAL = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth",
  "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth"];
const TENS: Record<number, string[]> = { 2: ["twentieth", "twenty"], 3: ["thirtieth", "thirty"], 4: ["fortieth", "forty"], 5: ["fiftieth", "fifty"], 6: ["sixtieth", "sixty"],
  7: ["seventieth", "seventy"], 8: ["eightieth", "eighty"], 9: ["ninetieth", "ninety"] };
/** A pet with no name is "the first one", "the third one", by the order it came into the house (the number in its
 *  id), as the engine now labels it. A recording made before that calls every one of them "the little one": this
 *  gives each its own label back. */
export function ownLabel(p: Pick<PetV, "id" | "label">): string {
  const n = Number(p.id.slice(1));
  if (p.label !== "the little one" || !Number.isInteger(n) || n < 1) return p.label;
  return `the ${n < 20 ? ORDINAL[n] : n < 100 ? (n % 10 ? `${TENS[Math.floor(n / 10)][1]}-${ORDINAL[n % 10]}` : TENS[n / 10][0]) : "latest"} one`;
}
const EMOTE: Record<string, string> = { energy: "tired", comfort: "uneasy", curiosity: "bored", company: "lonely" };
/** The one strong feeling that shows as a small picture beside a pet (§5.3), or null. */
export function emoteOf(p: PetV): string | null {
  if (p.emote !== undefined) return p.emote;
  if (!p.levels || p.asleep) return null;
  const worst = [...NEEDS].sort((a, b) => p.levels![b] - p.levels![a])[0];
  return p.levels[worst] >= 3 ? EMOTE[worst] : NEEDS.every((n) => p.levels![n] <= 1) ? "content" : null;
}
/** What a pet is doing this moment, as plain words: "asleep", "resting", "walking", "using the lamp". Never its plan. */
export function doingOf(p: PetV): string {
  if (p.stage === "egg" || p.stage === "dead") return "";
  if (p.asleep) return "asleep";
  const d = p.doing ?? "", about = / \((the .+)\)$/.exec(d);   // the engine says "using something (the lamp)"
  return about ? (d.includes("something") ? d.replace(about[0], "").replace("something", about[1]) : d.replace(about[0], ` ${about[1]}`)) : d || (p.thinking ? "thinking what to do" : "");
}
/** What a pet means to do: the intention it is on, which is a wish, not what it is doing. None while it sleeps. */
export const wishOf = (p: PetV): string => (p.stage === "egg" || p.stage === "dead" || p.asleep ? "" : p.plan?.intention ?? "");
/** One clearly good feeling (a need at its best), to say beside whatever is wrong; "" if there is none or it is already said. */
export function goodWord(p: PetV): string {
  const said = moodWords(p);
  return (p.levels && p.felt ? NEEDS.filter((n) => p.levels![n] === 0).map((n) => p.felt![n]) : []).find((w) => !said.includes(w)) ?? "";
}
/** How long until an egg hatches, for whoever is watching: the minutes are the watcher's own, not the house's. */
export const hatchWords = (sec: number) => (sec < 90 ? "about to hatch" : `hatches in about ${Math.round(sec / 60)} of your minutes`);
