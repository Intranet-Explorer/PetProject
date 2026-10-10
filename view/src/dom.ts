// Small helpers for the DOM around the room. Everything from the engine is set as text, never as HTML.
import { svg } from "./icons";
import type { Genome, Look } from "./pet";
import { bodyStage } from "./types";
import type { Hello, PetV, Snap } from "./types";

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
  picture: (g: Genome, stage: string, look?: Look) => string;
  jump: (to: { pet?: string | null; room?: string | null }) => void;
  show: (tab: string, pet?: string) => void;   // open a tab of the drawer, on a pet if one is given
};

export const plural = (n: number, one: string, many = one + "s") => `${n} ${n === 1 ? one : many}`;
/** A tick as a day of the house, for "since day 3". */
export const dayOf = (snap: Snap, tick: number) => 1 + Math.floor((8 + (tick * snap.tick_seconds * 24) / snap.day_seconds) / 24);

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
  const top = panel.scrollTop;
  panel.replaceChildren(...kids.filter((k) => k != null && k !== false).map((k) => (typeof k === "number" ? String(k) : (k as Node | string))));
  for (const d of panel.querySelectorAll<HTMLDetailsElement>("details")) if (open.has(d.dataset.key)) d.open = true;
  panel.scrollTop = top;
}

/** A folding section that remembers by `key` whether it was open. */
export function fold(key: string, summary: Kid, ...kids: Kid[]) {
  const d = el("details", "", el("summary", "", summary), ...kids);
  d.dataset.key = key;
  return d;
}

/** A pet's body as a small still picture: as it is now, or as it was when it died. */
export function face(c: Ctx, p: PetV, cls = "face") {
  const img = el("img", cls) as HTMLImageElement, stage = bodyStage(p);
  img.src = c.picture(p.genome, stage, { grey: stage === "elder" ? 0.55 : 0, dead: p.stage === "dead" });
  img.alt = "";
  return img;
}
