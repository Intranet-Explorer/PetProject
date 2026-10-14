// The page's few shared building blocks (SPEC-v3.5.3 §9): panel, card, tab, button, chip and frame, a pet's portrait,
// and a link to any pet or thing. Every tab is made of these, so a skin (the Crusenho pack, later) replaces them here,
// once. Their look is in style.css under "building blocks"; colours, spacing and the font are variables at its top.
import { el } from "./dom";
import type { Kid } from "./dom";
import type { Genome } from "./pet";
import { petPortrait, petSheet } from "./petsprite";
import { href } from "./router";
import { thingSprite } from "./sprite";
import { fam } from "./types";

export const panel = (cls: string, ...kids: Kid[]) => el("section", `panel ${cls}`.trim(), ...kids);
export const frame = (cls: string, ...kids: Kid[]) => el("div", `frame ${cls}`.trim(), ...kids);
export const card = (cls: string, ...kids: Kid[]) => el("div", `card ${cls}`.trim(), ...kids);

export function button(text: Kid, go: () => void, cls = "") {
  const b = el("button", `button ${cls}`.trim(), text) as HTMLButtonElement;
  b.type = "button";
  b.onclick = go;
  return b;
}

/** A small rounded choice that can be on or off (filters). */
export function chip(text: Kid, on: boolean, go: () => void) {
  const b = button(text, go, "chip");
  b.setAttribute("aria-pressed", String(on));
  return b;
}

/** A link, as an <a> with a real address: the pet's or thing's page. */
export function a(text: Kid, to: string, cls = "") {
  const l = el("a", `link ${cls}`.trim(), text) as HTMLAnchorElement;
  l.href = to;
  return l;
}

/** Any pet as `{id, genome, drawn, stage}`: what a portrait needs. `drawn` is the stage it is drawn at (the dead as they were in life). */
export type Who = { id: string; name?: string; genome: Genome; drawn: string; stage: string; family?: number };

const sent = new Set<string>();
/** SPEC-v3.5.3 §8: its portrait at /portrait/<id>.png (and @4x): drawn here from its genome and given to the engine to
 *  keep, once, if it has none for that stage yet. */
function keep(p: Who) {
  const key = `${p.id}-${p.drawn}`;
  if (sent.has(key)) return;
  sent.add(key);
  fetch(`/portrait/${p.id}.png`).then((r) => {
    if (r.ok) return;
    const look = { grey: p.drawn === "elder" ? 0.55 : 0 };
    for (const [scale, name] of [[1, `${p.id}.png`], [4, `${p.id}@4x.png`]] as const)
      petPortrait(p.genome, p.drawn, scale, look).toBlob((b) => { if (b) fetch(`/portrait/${name}`, { method: "POST", body: b }).catch(() => {}); }, "image/png");
  }).catch(() => {});
}

/** A pet's portrait, as large as fits `box` screen pixels at a whole-number scale, crisp. The dead are greyed. */
export function portrait(p: Who, box = 48) {
  const look = { grey: p.drawn === "elder" ? 0.55 : 0 };
  const c = petPortrait(p.genome, p.drawn, Math.max(1, Math.floor(box / petSheet(p.genome, p.drawn, look).size)), look);
  c.classList.add("px", "face");
  if (p.stage === "dead") c.classList.add("dead");
  c.setAttribute("aria-hidden", "true");
  keep(p);
  return c;
}

/** A pet's name that goes to its page, in its family's colour; with its portrait first if `box` is given. */
export function petLink(p: Who & { name: string }, box = 0) {
  return a(box ? el("span", "who", portrait(p, box), el("span", "", p.name)) : p.name, href("pet", p.id), `pet ${fam(p.family)}`);
}

/** A thing's name that goes to its page. */
export const thingLink = (id: string, name: string) => a(name, href("thing", id), "thinglink");

/** A made thing's picture. */
export const thingPic = (recipe: Record<string, unknown>, scale = 2) => thingSprite(recipe as never, scale);

/** The engine's answer to `url` as JSON, or null if it could not be had. */
export async function getJSON<T = any>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url);
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

/** SPEC-v3.5.4 §10: the visitor gives a thing a star (one to a thing). Returns why it could not be, or null. */
export async function giveStar(id: string): Promise<string | null> {
  try {
    const r = await fetch(`/api/star/${encodeURIComponent(id)}`, { method: "POST" });
    return r.ok ? null : ((await r.json().catch(() => ({}))).error ?? "the star could not be given");
  } catch {
    return "the house is not answering";
  }
}

/** Every pet and thing named in a sentence, linked: a pet's name (longest first, so "Grey Light's Hum" before "Grey
 *  Light"), a thing's name between single quotes. */
export function linked(text: string, pets: Record<string, Who & { name: string; born_day?: number | null }>, things: Record<string, string> = {},
                       at: { day?: number | null; me?: string | null } = {}): Node[] {
  // a name borne twice ("Grey Light", "Grey Light II") goes to `me` if it is one of them, else to whoever bore it on `day`
  const plain = (p: { name: string }) => p.name.replace(/ [IVX]+$/, ""), same = new Map<string, (Who & { name: string; born_day?: number | null })[]>();
  for (const p of Object.values(pets)) same.set(plain(p), [...(same.get(plain(p)) ?? []), p]);
  const byName = [...same.values()].map((ps) => ps.find((p) => p.id === at.me)
    ?? ps.filter((p) => at.day == null || (p.born_day ?? 0) <= at.day).sort((x, y) => (y.born_day ?? 0) - (x.born_day ?? 0))[0] ?? ps[0])
    .sort((x, y) => plain(y).length - plain(x).length);
  const out: Node[] = [];
  let rest = text;
  while (rest) {
    let best: { at: number; len: number; node: Node } | null = null;
    for (const p of byName) {
      const plain = p.name.replace(/ [IVX]+$/, ""), at = rest.indexOf(plain);   // a sentence says "Grey Light", the page shows "Grey Light II"
      if (at >= 0 && (!best || at < best.at)) best = { at, len: plain.length, node: petLink(p) };
    }
    const q = /'([^']+)'/.exec(rest);
    if (q && things[q[1]] && (!best || q.index + 1 < best.at)) best = { at: q.index + 1, len: q[1].length, node: thingLink(things[q[1]], q[1]) };
    if (!best) { out.push(document.createTextNode(rest)); break; }
    if (best.at) out.push(document.createTextNode(rest.slice(0, best.at)));
    out.push(best.node);
    rest = rest.slice(best.at + best.len);
  }
  return out;
}
