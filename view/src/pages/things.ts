// SPEC-v3.5.7 §7: the Things tab as an inventory. Everything made, each its sprite in a slot whose ring says what it is
// (gold a house first, silver a family first, blue an invented kind; gone things faded, and hidden until "Show gone"). Choosing one shows its card
// (thingcard.ts) and its history in a panel to the right; on a phone, in a sheet from the bottom. Filters and sort are
// Travel Book chips. A thing's page (#/thing/<id>) is the same card and history on a book page. main.ts sends both
// addresses here and calls render() on every visit and every 4 s.
import "./things.css";
import { el, plural, thingName } from "../dom";
import { href } from "../router";
import { artReady } from "../sprite";
import { cardBody, fitPic, loadThing } from "../thingcard";
import type { Thing, ThingPage } from "../thingcard";
import { hhmm } from "../types";
import { a, button, chip, getJSON, giveStar } from "../ui";
import { loadPets, momentRow } from "./story";
import { hideTip, showTip } from "./tip";

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
const ring = (t: Thing) => (t.first === "house" ? "gold" : t.first === "family" ? "silver" : t.invented ? "blue" : "");
const phone = matchMedia("(max-width: 899px)");
const history = (t: ThingPage) => [el("h3", "title tchist", "Its story"),
  t.moments.length ? el("ol", "storylist", ...t.moments.map((m) => momentRow(m, names(), `day ${m.day}, ${hhmm(m.hour)}`)))
    : el("p", "empty", "Nothing told of it beyond its making.")];

// ---- the inventory ----

const STEP = 60;
const SORTS: Record<string, [string, (a: Thing, b: Thing) => number]> = {
  new: ["Newest", (a, b) => (b.tick ?? 0) - (a.tick ?? 0)], old: ["Oldest", (a, b) => (a.tick ?? 0) - (b.tick ?? 0)],
  used: ["Most used", (a, b) => b.uses - a.uses], name: ["A to Z", (a, b) => a.name.localeCompare(b.name)],
};
let kind = "", fam = 0, place = "", mark = "", gone = false, sort = "new", shown = STEP, drawn = "", busy = false, sel: string | null = null, auto = false;
let side: HTMLElement | null = null, slots = new Map<string, HTMLElement>();

/** One thing in its slot: a button that chooses it; its name in a tip under a mouse. */
function slot(t: Thing) {
  const s = el("button", `slot tslot ${ring(t)}${t.gone ? " gone" : ""}`, fitPic(t, phone.matches ? 48 : 64));
  s.setAttribute("aria-label", t.name + (t.title_shown && t.recipe.title ? `, ${t.recipe.title}` : "") + (t.gone ? " (gone)" : ""));
  s.setAttribute("aria-pressed", String(t.id === sel));
  s.onclick = () => choose(t.id);
  s.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") showTip(s, [el("div", "ttxt", el("b", "", ...thingName(t.name, t.recipe, t.title_shown)), el("span", "twhere", t.where))]); });
  s.addEventListener("pointerleave", hideTip);
  slots.set(t.id, s);
  return s;
}

function choose(id: string | null) {
  sel = id;
  auto = false;
  hideTip();
  for (const [k, s] of slots) s.setAttribute("aria-pressed", String(k === sel));
  void fillSide();
}

/** The panel (a sheet on a phone): the chosen thing's card and its history. */
async function fillSide() {
  if (!side) return;
  const s = side, id = sel;
  const open = !!id && !(auto && phone.matches);   // (the first thing, chosen for a wide window, is not a sheet when it narrows)
  s.classList.toggle("open", open);
  document.body.classList.toggle("tsheet-open", open && phone.matches);
  if (!id) { s.replaceChildren(el("p", "empty", "Choose a thing to see it.")); return; }
  const quick = all?.things.find((t) => t.id === id);
  const head = (t: Thing) => el("div", "invbar", a("Open its page", href("thing", t.id), "small"), button("Close", () => choose(null), "invclose"));
  if (quick && s.dataset.id !== id) s.replaceChildren(head(quick), el("div", "tccontent", ...cardBody(quick)));
  s.dataset.id = id;
  const t = await loadThing(id);
  if (t && sel === id && side === s) s.replaceChildren(head(t), el("div", "tccontent", ...cardBody(t)), ...history(t));
}

let folded = true;
/** The filters and sort: open on a wide window; on a phone folded under one line until opened (they are tall there). */
function filters(...kids: Node[]) {
  const on = [kind, place, fam, mark].filter(Boolean).length + (sort === "new" ? 0 : 1);
  const f = el("details", "tmore", el("summary", "", `Filter and sort${on ? ` (${on} on)` : ""}`), ...kids) as HTMLDetailsElement;
  f.open = !phone.matches || !folded;
  f.ontoggle = () => { if (phone.matches) folded = !f.open; };
  return f;
}

function grid(root: HTMLElement, d: All) {
  const T = d.things;
  // SPEC-v3.5.10 §3: what is gone is hidden until the visitor asks for it ("Show gone", or the gone place)
  const list = T.filter((t) => (gone || place === "gone" || !t.gone) && (!kind || (t.statue ? "statue" : t.recipe.kind) === kind) && (!fam || t.family === fam) &&
    (!place || (place === "gone" ? !!t.gone : place === "keepsake" ? t.keepsake : t.room_name === place)) &&
    (!mark || (mark === "invented" ? t.invented : mark === "star" ? t.star != null : mark === "heirloom" ? t.heirloom : mark === "statue" ? t.statue : t.first === mark)))
    .sort(SORTS[sort][1]);
  const redo = () => { shown = STEP; drawn = ""; grid(root, d); };
  const pick = (label: string, value: string, opts: [string, string][], set: (v: string) => void) => {
    const s = el("select", "", el("option", "", label), ...opts.map(([v, text]) => Object.assign(el("option", "", text), { value: v }))) as HTMLSelectElement;
    (s.options[0] as HTMLOptionElement).value = "";
    s.value = value;
    s.onchange = () => { set(s.value); redo(); };
    s.setAttribute("aria-label", label);
    return s;
  };
  const markChip = (text: string, m: string, sw = "") => chip(el("span", "", sw ? el("i", `sw ${sw}`) : null, text), mark === m, () => { mark = mark === m ? "" : m; redo(); });
  const inv = new Set(T.filter((t) => t.invented).map((t) => t.recipe.kind));
  const kinds = [...new Set([...d.kinds.filter((k) => k !== "statue"), ...(T.some((t) => t.statue) ? ["statue"] : [])])].sort();
  const standing = T.filter((t) => !t.gone).length;
  if (!phone.matches && (!sel || !T.some((t) => t.id === sel))) { sel = list[0]?.id ?? null; auto = true; }
  slots = new Map();
  side = el("aside", "invside paper");
  side.setAttribute("aria-label", "the chosen thing");
  const shade = el("div", "invshade");
  shade.onclick = () => choose(null);
  root.replaceChildren(el("div", "things", el("div", "paper tbar",
    el("div", "tcount", el("p", "hint", `${plural(T.length, "thing")} made in the house: ${standing} still about, ${T.length - standing} gone.`),
      // SPEC-v3.5.8 §6: charms are a filter of their own, out of the fold on a phone
      chip(`Charms (${T.filter((t) => t.recipe.kind === "charm" && (gone || !t.gone)).length})`, kind === "charm", () => { kind = kind === "charm" ? "" : "charm"; redo(); }),
      chip(`Show gone (${T.length - standing})`, gone, () => { gone = !gone; redo(); })),
    filters(el("div", "tfilters",
      pick("Every kind", kind, kinds.map((k) => [k, inv.has(k) ? `${k} (invented)` : k]), (v) => (kind = v)),
      pick("Everywhere", place, [...d.rooms.map((r): [string, string] => [r, r]), ["keepsake", "in a keepsake box"], ["gone", "gone (taken apart, joined, traded…)"]], (v) => (place = v)),
      chip("Both families", !fam, () => { fam = 0; redo(); }), chip("Family 1", fam === 1, () => { fam = 1; redo(); }), chip("Family 2", fam === 2, () => { fam = 2; redo(); })),
    el("div", "chips", markChip("First in the house", "house", "gold"), markChip("First in its family", "family", "silver"), markChip("Invented kinds", "invented", "blue"),
      markChip("Heirlooms", "heirloom"), markChip("★ Starred", "star"), markChip("Statues", "statue"),
      el("span", "hint tsort", "Sort:"), ...Object.entries(SORTS).map(([k, [text]]) => chip(text, sort === k, () => { sort = k; redo(); })))),
    list.length !== (gone ? T.length : standing) ? el("p", "hint", `${plural(list.length, "thing")} like that.`) : null),
    el("div", "inv", el("div", "invlist",
      list.length ? el("div", "tgrid", ...list.slice(0, shown).map(slot)) : el("p", "empty", "Nothing made like that."),
      list.length > shown ? el("p", "earlier", button(`Show more (${list.length - shown} left)`, () => { shown += STEP * 2; drawn = ""; grid(root, d); }, "button")) : null),
    shade, side)));
  void fillSide();
}

addEventListener("keydown", (e) => { if (e.key === "Escape" && sel && phone.matches && side?.isConnected) choose(null); });
addEventListener("hashchange", () => document.body.classList.remove("tsheet-open"));

// ---- a thing's page ----

let page: ThingPage | null = null;

function thingPage(root: HTMLElement, t: ThingPage) {
  root.replaceChildren(el("div", "book tpage",
    el("p", "back", a("← All things", href("things"), "small")),
    el("div", "tccontent", ...cardBody(t)),
    starButton(root, t),
    ...history(t)));
}

/** SPEC-v3.5.4 §10: the visitor's star, one to a thing, for a thing still about the house (not a statue). */
function starButton(root: HTMLElement, t: ThingPage) {
  if (t.gone || t.statue || t.star != null) return null;
  const why = el("span", "hint", ""), b = button("★ Give it a star", async () => {
    b.disabled = true;
    const err = await giveStar(t.id);
    if (err) { why.textContent = ` ${err}`; b.disabled = false; return; }
    t.star = 0;
    allAt = 0;
    thingPage(root, t);
  }, "button") as HTMLButtonElement;
  b.title = "Its maker will feel it the next time it is awake, and it goes on the board in the machine room";
  return el("p", "starit", b, why);
}

export async function render(root: HTMLElement, id: string | null): Promise<void> {
  if (busy) return;
  busy = true;
  if (!root.childElementCount || (id && page?.id !== id)) root.replaceChildren(el("p", "empty", id ? "Finding it…" : "Gathering everything made…"));
  const [d, p] = await Promise.all([loadAll(), id ? getJSON<ThingPage>(`/api/thing/${encodeURIComponent(id)}`) : null, loadPets(), artReady]);
  busy = false;
  if (id) {
    if (!p) {
      if (page?.id !== id) { root.replaceChildren(el("p", "empty", "There is no such thing.")); drawn = ""; }
      return;
    }
    const key = JSON.stringify(["page", p.id, p.where, p.moments.length, p.uses, p.star, !!d]);
    if (key === drawn && root.childElementCount) return;
    page = p;
    drawn = key;
    return thingPage(root, p);
  }
  if (!d) return;
  const key = JSON.stringify(["grid", d.things.length, d.things[0]?.tick, d.things.filter((t) => t.gone).length, d.things.filter((t) => t.star != null).length, kind, fam, place, mark, gone, sort, shown, phone.matches]);
  if (key === drawn && root.contains(side)) return;
  drawn = key;
  grid(root, d);
}
