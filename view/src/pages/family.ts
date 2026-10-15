// SPEC-v3.5.3 §3: the Family tab. A gallery of every pet that ever lived, filtered and sorted; or the tree, one column
// per family, generations as rows, a line only from a parent to its children; what passed between the families is
// listed under it, never drawn across it. main.ts calls render() on every visit and every few seconds while shown.
import "./family.css";
import { el, stageName } from "../dom";
import type { Kid } from "../dom";
import { icon, svg } from "../icons";
import { href } from "../router";
import { a, chip, getJSON, petLink, portrait } from "../ui";
import type { Who } from "../ui";
import { fam } from "../types";

export type Pet = Who & { name: string; stored_name: string | null; family: number; gen: number; parent: string | null; children: string[];
  alive: boolean; born_day: number; died_day: number | null; cause: string | null; days: number | null };
type Link = { kind: string; tick: number; a: string; b: string | null; text: string };
type Pets = { pets: Pet[]; links: Link[]; day: number };

export const familyName = (n: number) => ["", "First family", "Second family", "Third family"][n] ?? `Family ${n}`;
/** A pet's span in world days: "day 21 – 37" for the dead, "born day 48" for the living. */
export const lifeDays = (p: Pet) => (p.alive ? `born day ${p.born_day}` : `day ${p.born_day} – ${p.died_day}`);
// (one word for a stage everywhere: the cards' own, dom.ts stageName: little one, young one, grown, old one)
export const stageText = (p: Pet) => (p.alive ? (p.stage === "egg" ? "an egg" : stageName(p.stage)) : `lived ${Math.round(p.days ?? 0)} days`);

/** Who to link a name to in a sentence from world day `day`: when a name was used twice, only the one that bore it
 *  then (or `me`), so "Grey Light" in day 30's moment goes to the first Grey Light, not the one born on day 52. */
export function namesOn(pets: Pet[], day: number, me?: string): Record<string, Pet> {
  const plain = (p: Pet) => p.name.replace(/ [IVX]+$/, ""), out: Record<string, Pet> = {};
  const byName = new Map<string, Pet[]>();
  for (const p of pets) byName.set(plain(p), [...(byName.get(plain(p)) ?? []), p]);
  for (const same of byName.values()) {
    const then = same.filter((p) => p.born_day <= day).sort((x, y) => y.born_day - x.born_day);
    const p = same.find((q) => q.id === me) ?? then[0] ?? same[0];
    out[p.id] = p;
  }
  return out;
}

let list: Pets | null = null;
/** The pets, fresh from the engine (the last answer if it is away). */
export async function allPets() {
  list = (await getJSON<Pets>("/api/pets")) ?? list;
  return list;
}

const view = { tree: false, fam: 0, life: "", sort: "birth" };
let drawn = "", treeShown = false;

export async function render(root: HTMLElement, _id: string | null) {
  const data = await allPets();
  if (!data) { if (!root.childElementCount) root.textContent = "The house is not answering yet."; return; }
  const key = JSON.stringify([data, view]);
  if (key === drawn && root.childElementCount) return;
  drawn = key;
  const redraw = () => { drawn = ""; void render(root, _id); };
  const set = (patch: Partial<typeof view>) => () => { Object.assign(view, patch); redraw(); };
  const fams = [...new Set(data.pets.map((p) => p.family))].sort();
  const row = (label: string, ...kids: Kid[]) => el("div", "fbar", el("span", "glabel", label), ...kids);
  const bars = [row("Show", chip("Gallery", !view.tree, set({ tree: false })), chip("Tree", view.tree, set({ tree: true })))];
  if (!view.tree) bars.push(
    row("Family", chip("All", !view.fam, set({ fam: 0 })), ...fams.map((n) => chip(familyName(n), view.fam === n, set({ fam: n })))),
    row("Who", chip("All", !view.life, set({ life: "" })), chip("Living", view.life === "living", set({ life: "living" })), chip("Dead", view.life === "dead", set({ life: "dead" }))),
    row("Sort", chip("By birth", view.sort === "birth", set({ sort: "birth" })), chip("By generation", view.sort === "gen", set({ sort: "gen" }))));
  const opening = view.tree && !treeShown;   // SPEC-v3.5.7 §8: the lines draw themselves in when the tree opens (not on every redraw)
  treeShown = view.tree;
  root.replaceChildren(el("div", "familypage", el("div", "paper fbars", ...bars), view.tree ? tree(data, fams, opening) : gallery(data)));
}

function gallery(data: Pets) {
  const pets = data.pets
    .filter((p) => (!view.fam || p.family === view.fam) && (!view.life || p.alive === (view.life === "living")))
    .sort((x, y) => (view.sort === "gen" ? x.gen - y.gen : 0) || x.born_day - y.born_day || Number(x.id.slice(1)) - Number(y.id.slice(1)));
  if (!pets.length) return el("p", "hint", "No pet like that.");
  return el("div", "gallery", ...pets.map((p) => {
    const c = el("a", `card gcard ${fam(p.family)} ${p.alive ? "alive" : "dead"}`, el("span", "gcard-in",   // (not a.link: that has no frame)
      el("span", "gface", portrait(p, 112)),
      el("b", "gname", p.name),
      el("span", "gfam", familyName(p.family), ` · gen ${p.gen}`),
      el("span", "gdays", p.alive ? null : icon("stone", 14), lifeDays(p)),
      el("span", "gstage", p.alive ? stageText(p) : p.cause ? `died of ${p.cause}` : "dead"))) as HTMLAnchorElement;
    c.href = href("pet", p.id);
    return c;
  }));
}

// a generation's row and a pet's column, in pixels: room for a name at 32 px on two lines under the portrait (v3.5.7)
const CH = 196, SW = 176, FOOT = 152;   // FOOT: below a node's name and days, where the line to its children starts
/** The tree: each family its own column, so no line ever crosses into another family; each parent's children under it. */
function tree(data: Pets, fams: number[], opening = false) {
  const rows = Math.max(...data.pets.map((p) => p.gen));
  const gens = el("div", "tgens", el("div", "thead"), el("div", "tgen-in", ...Array.from({ length: rows }, (_, i) => el("div", "tgen", `gen ${i + 1}`))));
  const cols = fams.map((n) => {
    const pets = data.pets.filter((p) => p.family === n), x = new Map<string, number>();
    const kids = (id: string) => pets.filter((p) => p.parent === id).sort((a, b) => a.born_day - b.born_day);
    let slots = 0;
    const place = (p: Pet) => {   // leaves side by side, each parent over the middle of its children
      const ch = kids(p.id);
      ch.forEach(place);
      x.set(p.id, ch.length ? (x.get(ch[0].id)! + x.get(ch.at(-1)!.id)!) / 2 : slots++);
    };
    pets.filter((p) => !pets.some((q) => q.id === p.parent)).sort((a, b) => a.born_day - b.born_day).forEach(place);
    const W = slots * SW, X = (p: Pet) => (x.get(p.id)! + 0.5) * SW, Y = (p: Pet) => (p.gen - 1) * CH;
    const lines = svg("svg", { class: "tlines", viewBox: `0 0 ${W} ${rows * CH}`, preserveAspectRatio: "none", height: rows * CH });
    for (const p of pets) for (const c of kids(p.id)) {
      const mid = Y(c) - 14;
      const line = svg("path", { d: `M${X(p)} ${Y(p) + FOOT}V${mid}H${X(c)}V${Y(c) + 2}`, "vector-effect": "non-scaling-stroke", pathLength: 1, "data-p": p.id, "data-c": c.id });
      line.style.animationDelay = `${(p.gen - 1) * 0.18}s`;   // (a generation after another)
      lines.append(line);
    }
    const box = el("div", "tbox", lines, ...pets.map((p) => {
      const n = a(el("span", "tnode-in", portrait(p, 56), el("span", "tname", p.name), el("span", "tdays", p.alive ? null : icon("stone", 12), lifeDays(p))),
        href("pet", p.id), `tnode ${fam(p.family)} ${p.alive ? "alive" : "dead"}`);
      n.style.cssText = `left:${X(p) / W * 100}%;top:${Y(p)}px`;
      n.dataset.pet = p.id;
      return n;
    }));
    box.style.height = `${rows * CH}px`;
    const col = el("div", `tcol ${fam(n)}`, el("div", "thead", familyName(n)), box);
    col.style.flex = `${slots} 0 ${slots * SW}px`;
    return col;
  });
  const page = el("div", `treepage${opening ? " tdraw" : ""}`, el("div", "tscroll paper", el("div", "trow", gens, ...cols)), between(data));
  // hovering (or focusing) a pet lights its line: everyone it came from, and everyone who came from it
  const byId = new Map(data.pets.map((p) => [p.id, p]));
  const light = (id: string | null) => {
    const line = new Set<string>();
    for (let q = id ? byId.get(id) : undefined; q; q = q.parent ? byId.get(q.parent) : undefined) line.add(q.id);
    const down = id ? [id] : [];
    while (down.length) for (const k of byId.get(down.pop()!)?.children ?? []) if (!line.has(k)) { line.add(k); down.push(k); }
    page.classList.toggle("lighting", !!id);
    page.querySelectorAll<HTMLElement>("a.tnode").forEach((n) => n.classList.toggle("lit", line.has(n.dataset.pet!)));
    page.querySelectorAll<SVGPathElement>(".tlines path").forEach((l) => l.classList.toggle("lit", line.has(l.dataset.p!) && line.has(l.dataset.c!)));
  };
  page.addEventListener("pointerover", (e) => light((e.target as Element).closest<HTMLElement>("a.tnode")?.dataset.pet ?? null));
  page.addEventListener("pointerleave", () => light(null));
  page.addEventListener("focusin", (e) => light((e.target as Element).closest<HTMLElement>("a.tnode")?.dataset.pet ?? null));
  page.addEventListener("focusout", () => light(null));
  return page;
}

const DID: Record<string, string> = { nuzzle: "nuzzled", give: "gave things", "teach song": "taught songs", tell: "told things" };
/** What passed between the families, by pair: who, and what they did, how often. */
function between(data: Pets) {
  const by = new Map(data.pets.map((p) => [p.id, p])), pairs = new Map<string, { a: Pet; b: Pet; kinds: Map<string, number> }>();
  const lines: Node[] = [];
  for (const l of data.links) {
    const pa = by.get(l.a), pb = l.b ? by.get(l.b) : null;
    if (!pa) continue;
    if (!pb) { lines.push(el("li", "", petLink(pa, 24), ` ${l.text.replace(pa.stored_name ?? pa.name, "").trim()}`)); continue; }
    const [x, y] = [pa, pb].sort((m, n) => m.family - n.family), k = `${x.id}-${y.id}`;
    const pair = pairs.get(k) ?? { a: x, b: y, kinds: new Map() };
    pair.kinds.set(l.kind, (pair.kinds.get(l.kind) ?? 0) + 1);
    pairs.set(k, pair);
  }
  for (const { a: x, b: y, kinds } of pairs.values())
    lines.push(el("li", "", petLink(x, 24), " and ", petLink(y, 24), ": ",
      [...kinds].map(([kind, n]) => `${DID[kind] ?? kind}${n > 1 ? ` ×${n}` : ""}`).join(", ")));
  return el("section", "paper between", el("h2", "", "Between the families"),
    lines.length ? el("ul", "", ...lines) : el("p", "hint", "Nothing has passed between the families yet."));
}
