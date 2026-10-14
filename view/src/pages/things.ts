// SPEC-v3.5.3 §6: the Things tab, everything made wherever it is now, and a page for each thing (#/thing/<id>): who
// made it, from what, what it does, where it is, and the moments it was part of. main.ts sends both addresses here and
// calls render() on every visit and every 4 s.
import "./things.css";
import { el, plural } from "../dom";
import { svg } from "../icons";
import { href } from "../router";
import { artReady } from "../sprite";
import { hhmm } from "../types";
import { a, button, chip, getJSON, petLink, thingLink, thingPic } from "../ui";
import { loadPets, momentRow, petOf } from "./story";
import type { M } from "./story";

type Thing = {
  id: string; name: string; recipe: Record<string, any>; by: string | null; by_name: string | null; owner: string | null; family: number | null;
  room: string | null; room_name: string | null; where: string; gone: string | null; tick: number | null; day: number | null; bits: string[];
  uses: number; heirloom: boolean; invented: boolean; statue: boolean; keepsake: boolean;
  of?: string; standing?: boolean; raised_day?: number | null; makers?: { id: string; name: string }[];
};
type All = { things: Thing[]; kinds: string[]; rooms: string[] };

let all: All | null = null, allAt = 0;
/** Everything made; asked again at most every 20 s (it is ~200 KB and changes slowly). */
async function loadAll() {
  if (Date.now() - allAt > 20000) {
    const d = await getJSON<All>("/api/allthings");
    if (d) { all = d; allAt = Date.now(); }
  }
  return all;
}
const names = () => Object.fromEntries((all?.things ?? []).map((t) => [t.name, t.id]));

/** A statue has no sprite: a figure on a plinth, in the text's colour. */
const statuePic = (scale: number) => svg("svg", { viewBox: "0 0 16 16", width: 16 * scale, height: 16 * scale, class: "statuepic", "shape-rendering": "crispEdges", "aria-hidden": "true" },
  svg("path", { d: "M7 1h2v2H7ZM6 3h4v5H6ZM5 4h1v3H5ZM10 4h1v3h-1ZM6 8h1v3H6ZM9 8h1v3H9ZM4 11h8v1H4ZM3 12h10v3H3Z", fill: "currentColor" }));
const pic = (t: Thing, scale: number) => (t.statue ? statuePic(scale) : thingPic(t.recipe, scale));
const by = (id: string | null, name: string | null, box = 0) => { const p = petOf(id); return p ? petLink(p, box) : el("span", "hint", name ?? "nobody known"); };
/** The engine keeps a purpose to 80 letters; one cut there trails off. */
const purpose = (s: string | undefined) => (!s ? null : s.length >= 78 && !/[.!?]$/.test(s) ? `${s}…` : s);
const kindLine = (t: Thing) => [t.statue ? "statue" : t.recipe.kind === t.name && t.invented ? null : t.recipe.kind ?? "thing", t.invented ? el("span", "badge gold", "invented") : null,
  t.heirloom ? el("span", "badge", "heirloom") : null, t.gone ? el("span", "tag", "gone") : null];

// ---- the grid ----

const STEP = 60;
let kind = "", fam = 0, place = "", mark = "", shown = STEP, drawn = "", busy = false;

function card(t: Thing) {
  return el("div", `card tcard${t.gone ? " gone" : ""}`,
    a(pic(t, 3), href("thing", t.id), "tpic"),
    el("div", "ttxt", thingLink(t.id, t.name), el("span", "kind", ...kindLine(t)),
      el("span", "", "by ", by(t.by, t.by_name)), el("span", "twhere", t.where)));
}

function grid(root: HTMLElement, d: All) {
  const T = d.things, inv = new Set(T.filter((t) => t.invented).map((t) => t.recipe.kind));
  const list = T.filter((t) => (!kind || (t.statue ? "statue" : t.recipe.kind) === kind) && (!fam || t.family === fam) &&
    (!place || (place === "gone" ? !!t.gone : place === "keepsake" ? t.keepsake : t.room_name === place)) &&
    (!mark || (mark === "invented" ? t.invented : t.statue)));
  const redo = () => { shown = STEP; drawn = ""; grid(root, d); };
  const pick = (label: string, value: string, opts: [string, string][], set: (v: string) => void) => {
    const s = el("select", "", el("option", "", label), ...opts.map(([v, text]) => Object.assign(el("option", "", text), { value: v }))) as HTMLSelectElement;
    (s.options[0] as HTMLOptionElement).value = "";
    s.value = value;
    s.onchange = () => { set(s.value); redo(); };
    s.setAttribute("aria-label", label);
    return s;
  };
  const kinds = [...new Set([...d.kinds.filter((k) => k !== "statue"), ...(T.some((t) => t.statue) ? ["statue"] : [])])].sort();
  const standing = T.filter((t) => !t.gone).length;
  root.replaceChildren(el("div", "things",
    el("p", "hint", `${plural(T.length, "thing")} made in the house: ${standing} still about, ${T.length - standing} gone.`),
    el("div", "tfilters",
      pick("Every kind", kind, kinds.map((k) => [k, inv.has(k) ? `${k} (invented)` : k]), (v) => (kind = v)),
      pick("Everywhere", place, [...d.rooms.map((r): [string, string] => [r, r]), ["keepsake", "in a keepsake box"], ["gone", "gone (taken apart, joined, traded…)"]], (v) => (place = v)),
      el("span", "chips", chip("Both families", !fam, () => { fam = 0; redo(); }), chip("Family 1", fam === 1, () => { fam = 1; redo(); }), chip("Family 2", fam === 2, () => { fam = 2; redo(); }),
        chip("Invented kinds", mark === "invented", () => { mark = mark === "invented" ? "" : "invented"; redo(); }),
        chip("Statues", mark === "statue", () => { mark = mark === "statue" ? "" : "statue"; redo(); }))),
    list.length !== T.length ? el("p", "hint", `${plural(list.length, "thing")} like that.`) : null,
    list.length ? el("div", "tgrid", ...list.slice(0, shown).map(card)) : el("p", "empty", "Nothing made like that."),
    list.length > shown ? el("p", "earlier", button(`Show more (${list.length - shown} left)`, () => { shown += STEP * 2; drawn = ""; grid(root, d); }, "button")) : null));
}

// ---- a thing's page ----

type Page = Thing & { moments: M[]; does: string | null };
let page: Page | null = null;

function facts(t: Page) {
  const r = t.recipe, rows: [string, (Node | string | null)[]][] = [];
  const andList = (xs: Node[]) => xs.flatMap((x, i) => [i ? (i === xs.length - 1 ? " and " : ", ") : "", x]);
  if (t.statue) {
    rows.push(["Of", [t.of ? by(t.of, null) : "someone"]]);
    rows.push(["Begun", [by(t.by, t.by_name), t.day ? `, day ${t.day}` : ""]]);
    if (t.makers?.length) rows.push([t.standing ? "Raised by" : "Worked on by", [...andList(t.makers.map((m) => by(m.id, m.name))), t.raised_day ? `, day ${t.raised_day}` : ""]]);
  } else {
    rows.push(["Made by", [by(t.by, t.by_name, 24), t.day ? `, day ${t.day}` : ""]]);
    if (t.owner && t.owner !== t.by) rows.push(["Belongs to", [by(t.owner, null, 24)]]);
    rows.push(["Made of", [[r.size === 1 ? "small" : r.size === 3 ? "large" : "", r.color, r.material].filter(Boolean).join(", ") + (t.bits.length ? `; from ${t.bits.join(", ")}` : "")]]);
    rows.push(["What it does", [purpose(t.does ?? r.purpose) ?? "nobody said"]]);
    if (t.uses) rows.push(["Used", [`${t.uses === 1 ? "once" : `${t.uses} times`}`]]);
  }
  rows.push([t.gone ? "Gone" : "Where it is", [t.where]]);
  return el("dl", "tfacts", ...rows.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", ...v)]));
}

function thingPage(root: HTMLElement, t: Page) {
  const map = names();
  root.replaceChildren(el("div", "tpage",
    el("p", "back", a("← All things", href("things"), "small")),
    el("div", `thead${t.gone ? " gone" : ""}`, el("div", "tbig", pic(t, 4)),
      el("div", "", el("h2", "", t.name), el("p", "kind", ...kindLine(t)))),
    facts(t),
    el("h3", "", "Its story"),
    t.moments.length ? el("ol", "storylist", ...t.moments.map((m) => momentRow(m, map, `day ${m.day}, ${hhmm(m.hour)}`)))
      : el("p", "empty", "Nothing told of it beyond its making.")));
}

export async function render(root: HTMLElement, id: string | null): Promise<void> {
  if (busy) return;
  busy = true;
  if (!root.childElementCount || (id && page?.id !== id)) root.replaceChildren(el("p", "empty", id ? "Finding it…" : "Gathering everything made…"));
  const [d, p] = await Promise.all([loadAll(), id ? getJSON<Page>(`/api/thing/${encodeURIComponent(id)}`) : null, loadPets(), artReady]);
  busy = false;
  if (id) {
    if (!p) {
      if (page?.id !== id) { root.replaceChildren(el("p", "empty", "There is no such thing.")); drawn = ""; }
      return;
    }
    const key = JSON.stringify(["page", p.id, p.where, p.moments.length, p.uses, !!d]);
    if (key === drawn && root.childElementCount) return;
    page = p;
    drawn = key;
    return thingPage(root, p);
  }
  if (!d) return;
  const key = JSON.stringify(["grid", d.things.length, d.things[0]?.tick, d.things.filter((t) => t.gone).length, kind, fam, place, mark, shown]);
  if (key === drawn) return;
  drawn = key;
  grid(root, d);
}
