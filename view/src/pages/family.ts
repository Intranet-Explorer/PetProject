// SPEC-v3.5.3 §3: the Family tab. A gallery of every pet that ever lived, filtered and sorted; or the tree, one column
// per family, generations as rows, a line only from a parent to its children; what passed between the families is
// listed under it, never drawn across it. main.ts calls render() on every visit and every few seconds while shown.
import "./family.css";
import { byname, el, stageName } from "../dom";
import type { Kid } from "../dom";
import { icon, svg } from "../icons";
import { href } from "../router";
import { hasSprite, sprite } from "../sprite";
import { a, chip, getJSON, live, petLink, portrait, thingPic } from "../ui";
import type { Who } from "../ui";
import { fam } from "../types";
import { deathMark, foundIn, place, stranger } from "./tree";

export type Pet = Who & { name: string; stored_name: string | null; byname?: string | null; family: number; gen: number; parent: string | null; children: string[]; founder?: boolean; kin?: string | null;
  alive: boolean; born_day: number; died_day: number | null; cause: string | null; days: number | null;
  cause_words?: string; of_age?: boolean };   // SPEC-v4.2 §11.4: the cause on its stone, in words ("died of the cold, untended"), and whether it was age
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
/** SPEC-v3.6b: every recipe the house has found (/api/family `recipes`): its words, who found it, whether it is a dish, whether it is lost. */
type Recipe = { words: string; by: string | null; dish: boolean; lost: boolean };
let recipes: Recipe[] = [], recipesAt = 0;
/** SPEC-v4.2 §10.3, §11.4: a family's tale (contracts.tale), from the same answer. */
type Tale = { id: string; family: number | null; about: string | null; name: string; cause: string; words: string; last_words: string; self_line: string; told: string[] };
let tales: Tale[] = [];
async function allRecipes() {
  if (Date.now() - recipesAt > 30_000) {   // (the whole family's record: not on every redraw)
    recipesAt = Date.now();
    const d = await getJSON<{ recipes?: Recipe[]; tales?: Tale[] }>("/api/family");
    if (d) [recipes, tales] = [d.recipes ?? recipes, d.tales ?? []];
  }
  return recipes;
}
/** The pets, fresh from the engine (the last answer if it is away). */
export async function allPets() {
  list = (await getJSON<Pets>("/api/pets")) ?? list;
  return list;
}

const view = { tree: false, web: false, fam: 0, life: "", sort: "birth" };
let drawn = "", treeShown = false;

export async function render(root: HTMLElement, _id: string | null) {
  const data = await allPets();
  if (!data) { if (!root.childElementCount) root.textContent = "The house is not answering yet."; return; }
  const boxes = shelfBoxes(), found = await allRecipes();
  const S = live.snap, hasWeb = !!S?.pets.some((p) => p.likes) || !!S?.ties?.length;   // SPEC-v4.0 §11: the web, while the engine sends opinions
  if (!hasWeb) view.web = false;
  const web = hasWeb ? S!.pets.filter((p) => p.stage !== "dead" && p.stage !== "egg").map((p) => [p.id, p.likes]) : null;
  const key = JSON.stringify([data, view, boxes.map((b) => [b.pet, b.holds.map((h) => h.name)]), found, web, S?.ties, tales]);
  if (key === drawn && root.childElementCount) return;
  drawn = key;
  const redraw = () => { drawn = ""; void render(root, _id); };
  const set = (patch: Partial<typeof view>) => () => { Object.assign(view, patch); redraw(); };
  const fams = [...new Set(data.pets.map((p) => p.family))].sort();
  const row = (label: string, ...kids: Kid[]) => el("div", "fbar", el("span", "glabel", label), ...kids);
  const bars = [row("Show", chip("Gallery", !view.tree && !view.web, set({ tree: false, web: false })), chip("Tree", view.tree, set({ tree: true, web: false })),
    hasWeb ? chip("Friends and enemies", view.web, set({ web: true, tree: false })) : null)];
  if (!view.tree && !view.web) bars.push(
    row("Family", chip("All", !view.fam, set({ fam: 0 })), ...fams.map((n) => chip(familyName(n), view.fam === n, set({ fam: n })))),
    row("Who", chip("All", !view.life, set({ life: "" })), chip("Living", view.life === "living", set({ life: "living" })), chip("Dead", view.life === "dead", set({ life: "dead" }))),
    row("Sort", chip("By birth", view.sort === "birth", set({ sort: "birth" })), chip("By generation", view.sort === "gen", set({ sort: "gen" }))));
  const opening = view.tree && !treeShown;   // SPEC-v3.5.7 §8: the lines draw themselves in when the tree opens (not on every redraw)
  treeShown = view.tree;
  root.replaceChildren(el("div", "familypage", el("div", "paper fbars", ...bars), view.web ? webOf(data) : view.tree ? tree(data, fams, opening) : gallery(data), taleList(data), memoryShelf(data, boxes), recipeList(data, found)));
}

/** SPEC-v4.2 §10.3, §11.4: the family's tales, newest first: whose, how it died, its last words, a line of its own page,
 *  and who has heard it told. */
function taleList(data: Pets) {
  const by = new Map(data.pets.map((p) => [p.id, p])), shown = tales.filter((t) => !view.fam || t.family === view.fam);
  if (!tales.length) return null;
  return el("section", "paper between tales", el("h2", "", "The family's tales"),
    el("p", "hint", "What is told of the dead: how each died, its last words, and what it said of itself. The old tell them to the little ones."),
    shown.length ? el("ul", "", ...shown.map((t) => {
      const p = t.about ? by.get(t.about) : undefined, heard = t.told.map((id) => by.get(id)).filter((q): q is Pet => !!q);
      return el("li", "", p ? petLink(p, 24) : el("b", "", t.name), ` ${t.words}.`,
        t.last_words ? el("blockquote", "", `“${t.last_words}”`) : null,
        t.self_line ? el("p", "hint", `It said of itself: ${t.self_line}`) : null,
        el("p", "hint", heard.length ? `Told to ${heard.map((q) => q.name).join(", ")}.` : "Not told yet."));
    })) : el("p", "hint", "No tale from this family yet."));
}

function gallery(data: Pets) {
  const pets = data.pets
    .filter((p) => (!view.fam || p.family === view.fam) && (!view.life || p.alive === (view.life === "living")))
    .sort((x, y) => (view.sort === "gen" ? x.gen - y.gen : 0) || x.born_day - y.born_day || Number(x.id.slice(1)) - Number(y.id.slice(1)));
  if (!pets.length) return el("p", "hint", "No hob like that.");
  return el("div", "gallery", ...pets.map((p) => {
    const c = el("a", `card gcard ${fam(p.family)} ${p.alive ? "alive" : "dead"}`, el("span", "gcard-in",   // (not a.link: that has no frame)
      el("span", "gface", portrait(p, 112)),
      el("b", "gname", p.name),
      byname(p) ? el("span", "bn", byname(p)!) : null,   // SPEC-v3.5.8 §6
      el("span", "gfam", familyName(p.family), ` · gen ${p.gen}`),
      el("span", "gdays", p.alive ? null : icon("stone", 14), lifeDays(p)),
      el("span", "gstage", p.alive ? stageText(p) : p.cause_words || (p.cause ? `died of ${p.cause}` : "dead")))) as HTMLAnchorElement;   // (SPEC-v4.2 §11.4: the cause on every stone, in words)
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
    const { x, slots } = place(data.pets, n), pets = data.pets.filter((p) => p.family === n);   // (tree.ts: leaves side by side, each parent over the middle of its children)
    const kids = (id: string) => pets.filter((p) => p.parent === id).sort((a, b) => a.born_day - b.born_day);
    const W = slots * SW, X = (p: Pet) => (x.get(p.id)! + 0.5) * SW, Y = (p: Pet) => (p.gen - 1) * CH;
    const lines = svg("svg", { class: "tlines", viewBox: `0 0 ${W} ${rows * CH}`, preserveAspectRatio: "none", height: rows * CH });
    for (const p of pets) for (const c of kids(p.id)) {
      const mid = Y(c) - 14;
      const line = svg("path", { d: `M${X(p)} ${Y(p) + FOOT}V${mid}H${X(c)}V${Y(c) + 2}`, "vector-effect": "non-scaling-stroke", pathLength: 1, "data-p": p.id, "data-c": c.id });
      line.style.animationDelay = `${(p.gen - 1) * 0.18}s`;   // (a generation after another)
      lines.append(line);
    }
    const box = el("div", "tbox", lines, ...pets.map((p) => {
      const came = foundIn(p, pets.find((q) => q.id === p.parent)?.name, pets.find((q) => q.id === p.kin)?.name);   // SPEC-v4.0.5 §3.4: a founder egg given to a family, under its parent with a small mark
      const mark = deathMark(p);   // SPEC-v4.2 §11.4: a death not of age, marked, its cause the title
      const n = a(el("span", "tnode-in", portrait(p, 56), el("span", "tname", came ? icon("egg", 12) : null, p.name), byname(p) ? el("span", "bn tbn", byname(p)!) : null, el("span", "tdays", p.alive ? null : icon("stone", 12), lifeDays(p), mark ? icon("broken", 12) : null)),
        href("pet", p.id), `tnode ${fam(p.family)} ${p.alive ? "alive" : "dead"}${came ? " found" : ""}${mark ? " untimely" : ""}`);
      if (came || mark) n.title = [came && `${p.name} ${came}`, mark && `${p.name} ${mark}`].filter(Boolean).join("; ");
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

/** SPEC-v4.0 §6.3, §11: the relationship web. The living hobs in a ring; between two who feel anything for each other a
 *  line, each half in the colour of its own end's feeling (green liking, red dislike, darker and thicker the stronger),
 *  thick for a close bond, dashed for rivals. Pointing at a hob lights its own lines. */
function webOf(data: Pets) {
  const S = live.snap!, hobs = S.pets.filter((p) => p.stage !== "dead" && p.stage !== "egg"), by = new Map(data.pets.map((p) => [p.id, p])), n = hobs.length;
  const W = 640, R = 250, at = new Map(hobs.map((p, i) => [p.id, [W / 2 + R * Math.sin((2 * Math.PI * i) / n), W / 2 - R * Math.cos((2 * Math.PI * i) / n)]]));
  const lines = svg("svg", { class: "wlines", viewBox: `0 0 ${W} ${W}` });
  const colour = (v: number | undefined) => (v == null ? "#9b8466" : v >= 6 ? "#2f7d32" : v >= 1 ? "#5aa04a" : v > -1 ? "#9b8466" : v > -6 ? "#c8504a" : "#8e1f24");
  const ties = S.ties ?? [], bonded = (a: string, b: string) => ties.find((t) => (t.a === a && t.b === b) || (t.a === b && t.b === a))?.kind ?? (S.bonds ?? []).find((t) => (t.a === a && t.b === b) || (t.a === b && t.b === a))?.kind;
  for (const [i, A] of hobs.entries()) for (const B of hobs.slice(i + 1)) {
    const la = A.likes?.[B.id], lb = B.likes?.[A.id], kind = bonded(A.id, B.id);
    if (!kind && Math.abs(la ?? 0) < 2 && Math.abs(lb ?? 0) < 2) continue;   // (nothing much either way: no line)
    const [ax, ay] = at.get(A.id)!, [bx, by2] = at.get(B.id)!, [mx, my] = [(ax + bx) / 2, (ay + by2) / 2];
    const w = kind === "close" ? 8 : 2 + Math.round(Math.max(Math.abs(la ?? 0), Math.abs(lb ?? 0)) / 3);
    const sign = (v: number | undefined) => v ?? (kind === "enemy" ? -6 : kind === "friend" || kind === "close" ? 6 : undefined);
    for (const [x1, y1, v] of [[ax, ay, sign(la)], [bx, by2, sign(lb)]] as [number, number, number | undefined][]) {
      const l = svg("line", { x1, y1, x2: mx, y2: my, stroke: colour(v), "stroke-width": w, "stroke-linecap": "butt", "data-a": A.id, "data-b": B.id, class: kind ?? "" });
      if (kind === "rival") l.setAttribute("stroke-dasharray", "10 6");
      lines.append(l);
    }
    if (kind === "close") lines.append(svg("circle", { cx: mx, cy: my, r: 7, fill: "#e8506e", stroke: "#2b2233", "stroke-width": 2, "data-a": A.id, "data-b": B.id }));   // (a heart's place: the bond)
  }
  const box = el("div", "wbox", lines, ...hobs.map((p) => {
    const q = by.get(p.id), [x, y] = at.get(p.id)!;
    const node = q ? a(el("span", "tnode-in", portrait(q, 72), el("span", "tname", q.name), p.mood4 ? el("span", "bn", p.mood4) : null), href("pet", p.id), `tnode ${fam(q.family)} alive`) : el("span", "tnode");
    node.style.cssText = `left:${(x / W) * 100}%;top:${(y / W) * 100}%`;
    node.dataset.pet = p.id;
    return node;
  }));
  const page = el("div", "webpage paper", box, el("p", "wkey", el("i", "k like"), "liking ", el("i", "k dislike"), "dislike ", el("i", "k close"), "close bond ", el("i", "k rival"), "rivals",
    el("span", "hint", " - each half of a line is how that hob feels about the other; thicker is stronger")));
  const light = (id: string | null) => {
    page.classList.toggle("lighting", !!id);
    page.querySelectorAll<SVGElement>(".wlines [data-a]").forEach((l) => l.classList.toggle("lit", l.dataset.a === id || l.dataset.b === id));
    page.querySelectorAll<HTMLElement>(".tnode").forEach((t) => t.classList.toggle("lit", t.dataset.pet === id));
  };
  page.addEventListener("pointerover", (e) => light((e.target as Element).closest<HTMLElement>(".tnode")?.dataset.pet ?? null));
  page.addEventListener("pointerleave", () => light(null));
  return page;
}

/** SPEC-v3.5.12 §4: every keepsake box on a memory shelf in the attic (from the house as the last snapshot had it):
 *  whose it is and what it holds, in the order the boxes stand. */
function shelfBoxes() {
  const out: { pet: string; shelf: string; holds: { name: string; recipe: Record<string, unknown> }[] }[] = [];
  for (const r of live.snap?.rooms ?? []) for (const [name, o] of Object.entries(r.objects ?? {})) {
    if (!o.fix?.memory) continue;
    for (const box of o.store?.holds ?? []) {
      const b = r.objects[box];
      if (b?.fix?.keepsake) out.push({ pet: String(b.fix.keepsake), shelf: name, holds: (b.store?.holds ?? []).slice(0, 3).map((n) => ({ name: n, recipe: (r.objects[n]?.made?.recipe ?? {}) as Record<string, unknown> })) });
    }
  }
  return out;
}

/** The family's memory shelf: each box, whose it is, and what it holds. */
function memoryShelf(data: Pets, boxes: ReturnType<typeof shelfBoxes>) {
  const by = new Map(data.pets.map((p) => [p.id, p])), shown = boxes.filter((b) => !view.fam || by.get(b.pet)?.family === view.fam);
  if (!boxes.length) return null;
  const box = hasSprite("fix.little wooden keepsake box") ? () => sprite("fix.little wooden keepsake box", 1) : () => null;
  return el("section", "paper between memshelf", el("h2", "", "The memory shelf"),
    el("p", "hint", "In the attic, one shelf for each family: a keepsake box for every hob that has died, with up to three things it left."),
    shown.length ? el("ul", "mboxes", ...shown.map((b) => {
      const p = by.get(b.pet);
      return el("li", `mbox ${fam(p?.family)}`, el("span", "mpic", box()), el("span", "mwho", p ? petLink(p, 32) : "someone gone"),
        el("span", "mholds", ...(b.holds.length ? b.holds.map((h) => el("span", "mthing", thingPic(h.recipe, 1), h.name)) : [el("span", "hint", "empty")])));
    })) : el("p", "hint", "No box on the shelf from this family."));
}

/** SPEC-v3.6b §4: the family's recipes, dishes first, each with who found it; one the family has lost, greyed. */
function recipeList(data: Pets, found: Recipe[]) {
  if (!found.length) return null;
  const by = (who: string | null) => { const p = data.pets.find((q) => q.id === who || q.name === who || q.stored_name === who); return p ? petLink(p, 24) : who ?? "someone"; };
  const sorted = [...found].sort((a, b) => Number(b.dish) - Number(a.dish) || Number(a.lost) - Number(b.lost));
  return el("section", "paper between recipes", el("h2", "", "The family's recipes"),
    el("p", "hint", "What the hobs have found out how to make, and taught each other: the dishes cooked at the stove first."),
    el("ul", "", ...sorted.map((r) => el("li", r.lost ? "hint" : "", r.dish ? icon("bowl", 14) : null, ` ${r.words}`, " · found by ", by(r.by), r.lost ? " (lost: nobody knows it now)" : ""))));
}

const DID: Record<string, string> = { nuzzle: "nuzzled", give: "gave things", "teach song": "taught songs", tell: "told things" };
/** What passed between the families, by pair: who, and what they did, how often. */
function between(data: Pets) {
  const by = new Map(data.pets.map((p) => [p.id, p])), pairs = new Map<string, { a: Pet; b: Pet; kinds: Map<string, number> }>();
  const lines: Node[] = [];
  for (const l of data.links) {
    const pa = by.get(l.a), pb = l.b ? by.get(l.b) : null;
    if (!pa) continue;
    if (!pb) { if (stranger(pa)) lines.push(el("li", "", petLink(pa, 24), ` ${l.text.replace(pa.stored_name ?? pa.name, "").trim()}`)); continue; }
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
