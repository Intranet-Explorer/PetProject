// SPEC-v3.5.3 §5: the Story tab. The house's history by world day, newest first (today and yesterday on top), each
// day headed with its season and weather and the chronicle's paragraph for it; filter chips by kind of moment; every
// pet and thing in a sentence a link. Older days come on demand. main.ts calls render() on every visit and every 4 s.
import "./story.css";
import { el, whole } from "../dom";
import { icon } from "../icons";
import { artReady } from "../sprite";
import { hhmm } from "../types";
import { button, chip, getJSON, linked, petLink, portrait } from "../ui";
import type { Who } from "../ui";

export type Pet = Who & { name: string; family: number; parent: string | null; laid_day: number | null; born_day: number | null; died_day: number | null; alive: boolean };
export type M = { tick: number; day: number; hour: number; kind: string; text: string; pet: string | null; room: string | null };
type Day = { day: number; season: string; weather: string | null; summary: string | null; moments: M[] };
type Page = { days: Day[]; more: boolean; today: number; things: Record<string, string> };

// ---- the pets, and a sentence with each of them linked (shared with the Things tab) ----

let pets: Record<string, Pet> = {}, petsAt = 0;
/** Every pet that ever lived, by id; asked again at most every 20 s. */
export async function loadPets() {
  if (Date.now() - petsAt > 20000) {
    const d = await getJSON<{ pets: Pet[] }>("/api/pets");
    if (d) { pets = Object.fromEntries(d.pets.map((p) => [p.id, p])); petsAt = Date.now(); }
  }
  return pets;
}
export const petOf = (id: string | null | undefined) => (id ? pets[id] : undefined);

const plain = (n: string) => n.replace(/ [IVX]+$/, "");
/** A moment's sentence with every pet and thing in it linked. A name two pets have had ("Grey Light") goes to the one
 *  who did it (the moment's `pet`), else the one born last by that day (ui.ts linked). A pet named in the sentence
 *  by what it was called before it had a name ("the seventh one") is the one who did it; one not named at all ("an egg
 *  hatched") is put after the sentence. */
export function told(text: string, day: number, actor: string | null, things: Record<string, string>): Node[] {
  const one: Record<string, Pet> = { ...pets };
  const me = petOf(actor);
  const was = me && (/^(.+?) took the name /.exec(text)?.[1] ?? (text.includes(plain(me.name)) ? null : /\bthe (?:little|[a-z]+(?:st|nd|rd|th)) one\b(?!'s)/.exec(text)?.[0]));
  if (me && was) one[" was"] = { ...me, name: was };
  const out = linked(whole(text), one, things, { day, me: actor });
  if (me && !out.some((n) => n instanceof HTMLAnchorElement && n.hash === `#/pet/${me.id}`)) out.push(document.createTextNode(" · "), petLink(me));
  return out;
}

/** One moment as a row: its small picture, the time, the sentence. Births, deaths and a family's start stand out, with
 *  the pet's portrait. `at` is how the time is put ("14:20", or "day 3, 14:20"). */
export function momentRow(m: M, things: Record<string, string>, at = hhmm(m.hour)) {
  const p = petOf(m.pet), first = !!p && !p.parent && (m.kind === "arrival strangers" || (m.kind === "egg" && !/ laid an egg/.test(m.text)));   // an egg nobody laid
  const big = m.kind === "death" ? "death" : first ? "founding" : m.kind === "hatched" ? "birth" : "";
  const text = m.kind === "invented" && /: [^:]{78,}$/.test(m.text) ? `${m.text}…` : m.text;   // the engine keeps the purpose to 80 letters
  return el("li", `m ${big}`.trim(), icon(m.kind === "invented" ? "discovery" : m.kind === "statue" ? "built" : m.kind), el("span", "t", at),
    el("span", "s", big && p ? portrait(p, 48) : null, ...told(text, m.day, m.pet, things),
      first && p ? el("span", "badge", `family ${p.family} begins`) : null));
}

// ---- which moments each chip shows ----

const LIFE = new Set(["egg", "hatched", "death", "ended", "weak", "named", "stage", "heirloom", "arrival strangers"]);
const FINDS = new Set(["first", "best", "ambition", "works", "discovery", "invented", "forgotten", "tool", "room", "taught", "read", "drift", "arrival writing", "arrival songs", "arrival taming", "arrival radio", "arrival book"]);
const BUILD = new Set(["built", "statue", "mended", "worn", "held", "moved"]);
const WORDS = new Set(["saying", "crossed", "message", "words", "wrote", "song", "discarded", "scrubbed"]);
/** The many small comings and goings: in "Everything", not in the main story. */
const SMALL = new Set(["made", "unmade", "want", "entered", "nuzzle", "took", "machine", "fed", "stored", "told", "lost", "kept", "draught", "leak",
  "power", "power back", "delivery", "stocked", "mark", "planted", "harvest", "project", "message", "song", "noticed"]);
const visitor = (m: M) => /\bvisitor/i.test(m.text);
const notable = (m: M) => (m.kind === "project" && /\bbegan an? /.test(m.text)) || (m.kind === "song" && /made up a song/.test(m.text)) || (m.kind === "message" && !/rewrote/.test(m.text));

const FILTERS: [string, string, (m: M) => boolean][] = [
  ["main", "The main things", (m) => !SMALL.has(m.kind) || notable(m) || visitor(m)],
  ["life", "Births and deaths", (m) => LIFE.has(m.kind)],
  ["finds", "Discoveries and inventions", (m) => FINDS.has(m.kind)],
  ["build", "Building and statues", (m) => BUILD.has(m.kind) || (m.kind === "project" && /\bbegan an? /.test(m.text))],
  ["words", "Sayings and messages", (m) => WORDS.has(m.kind) && !(m.kind === "message" && /rewrote/.test(m.text)) && !(m.kind === "song" && /taught|by ear/.test(m.text))],
  ["visitor", "The visitor", visitor],
  ["all", "Everything", () => true],
];

// ---- the page ----

// ---- the page: a book, a world day to a page (SPEC-v3.5.7 §8). On a desktop two pages side by side (yesterday and
// today, to begin with), on a phone one. Arrows or a swipe turn the pages; a strip of day markers jumps to any day. ----

const days = new Map<number, Day>();
let today = 0, things: Record<string, string> = {}, at = 0;   // `at`: the day on the right-hand page (a phone's one page)
let filter = "main", drawn = "", busy = false, turning = "";

const ago = (d: number) => (d === today ? "Today" : d === today - 1 ? "Yesterday" : `Day ${d}`);
const wide = () => innerWidth >= 900;
const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** The day's paragraph as short points: a sentence each, and a long sentence cut where it turns to another pet or
 *  another thing ("; ", and ", and " before a name or "it"). */
export function points(text: string): string[] {
  return text.split(/(?<=[.!?])\s+(?=["“A-Z])/)
    .flatMap((s) => s.split(/;\s+|,\s+and\s+(?=(?:it|its|they)\b|[A-Z])/))
    .map((s) => s.trim().replace(/[,;:]$/, ""))
    .filter((s) => s.length > 1)
    .map((s) => s[0].toUpperCase() + s.slice(1) + (/[.!?”"]$/.test(s) ? "" : "."));
}

function dayPage(n: number, keep: (m: M) => boolean, side: string) {
  const d = days.get(n);
  if (n < 1) return el("section", `book sday ${side}`, el("p", "empty", "That is the start of the house."));
  if (!d) return el("section", `book sday ${side}`, el("h3", "", ago(n)), el("p", "empty", "Turning to it…"));
  const shown = d.moments.filter(keep), rest = d.moments.length - shown.length;
  return el("section", `book sday ${side}`,
    el("h3", "", ago(d.day)),
    el("p", "sline", d.day >= today - 1 ? `day ${d.day} - ` : "", d.season, ...(d.weather ? [" - ", el("span", "sky", icon(d.weather, 20), d.weather)] : [])),
    d.summary && (filter === "main" || filter === "all") ? el("ul", "chron", ...points(d.summary).map((t) => el("li", "", ...told(t, d.day, null, things)))) : null,
    shown.length ? el("ol", "storylist", ...shown.map((m) => momentRow(m, things)))
      : el("p", "empty", d.day === today ? "Nothing worth telling yet today." : filter === "main" ? "A quiet day." : "Nothing of this kind."),
    filter === "main" && rest ? el("p", "rest", `and ${rest} smaller moment${rest === 1 ? "" : "s"} (making, wanting, comings and goings) `,
      button("show everything", () => setFilter("all"), "link small")) : null);
}

function setFilter(f: string) { filter = f; drawn = ""; draw(document.getElementById("page-story")!); }

/** The week of days up to `n`, if it is not here yet. */
async function fetchUpTo(n: number) {
  if (n < 1 || days.has(n)) return;
  const d = await getJSON<Page>(`/api/days?before=${n + 1}`);
  for (const x of d?.days ?? []) days.set(x.day, x);
}

/** Turn to the spread (or page) whose right-hand day is `n`: the page turns, and the book says so (§9 "flip"). */
async function turnTo(n: number, root: HTMLElement) {
  n = Math.max(wide() ? 2 : 1, Math.min(today, n));
  if (n === at) return;
  turning = n < at ? "back" : "on";
  at = n;
  dispatchEvent(new CustomEvent("pet:sound", { detail: "flip" }));
  drawn = "";
  draw(root);
  await Promise.all([fetchUpTo(n), wide() ? fetchUpTo(n - 1) : null]);
  drawn = "";
  draw(root);
}

function draw(root: HTMLElement) {
  const keep = FILTERS.find((f) => f[0] === filter)![2], two = wide(), step = two ? 2 : 1;
  const shown = two ? [at - 1, at] : [at];
  const pages = el("div", `sspread${turning && !still() ? ` turn-${turning}` : ""}`, ...shown.map((n, i) => dayPage(n, keep, two && i === 0 ? "left" : "right")));
  turning = "";
  const back = Math.max(step, at - step), on = Math.min(today, at + step);
  const prev = button(`‹ ${ago(two ? back - 1 : back)}`, () => void turnTo(back, root), "turn prev");
  const next = button(`${ago(on)} ›`, () => void turnTo(on, root), "turn next");
  prev.disabled = shown[0] <= 1;
  next.disabled = at >= today;
  prev.setAttribute("aria-label", "Turn back a page");
  next.setAttribute("aria-label", "Turn on a page");
  const strip = el("nav", "daystrip", ...Array.from({ length: today }, (_, i) => {
    const n = i + 1, b = button(String(n), () => void turnTo(two && n < today ? n + 1 : n, root), `dmark${shown.includes(n) ? " on" : ""}`);
    b.setAttribute("aria-label", ago(n));
    if (shown.includes(n)) b.setAttribute("aria-current", "page");
    return b;
  }));
  strip.setAttribute("aria-label", "Turn to a day");
  const book = el("div", "sbook", pages);
  // a swipe across the book turns its pages (sideways only: up and down still scroll the page)
  let x0 = 0, y0 = 0;
  book.onpointerdown = (e) => { x0 = e.clientX; y0 = e.clientY; };
  book.onpointerup = (e) => {
    const dx = e.clientX - x0, dy = e.clientY - y0;
    if (e.pointerType !== "mouse" && Math.abs(dx) > 60 && Math.abs(dx) > 2 * Math.abs(dy)) void turnTo(dx > 0 ? back : on, root);
  };
  root.replaceChildren(el("div", "story",
    el("div", "paper chips filters", ...FILTERS.map(([k, label]) => chip(label, filter === k, () => setFilter(k)))),
    el("div", "turns", prev, next), book, strip));
  const cur = strip.querySelector<HTMLElement>(".dmark.on:last-of-type") ?? strip.querySelector<HTMLElement>(".dmark.on");
  if (cur) strip.scrollLeft = cur.offsetLeft - strip.clientWidth / 2;
}

export async function render(root: HTMLElement, _id: string | null): Promise<void> {
  if (busy) return;
  busy = true;
  if (!root.childElementCount) root.replaceChildren(el("p", "empty", "Reading the story…"));
  const [d] = await Promise.all([getJSON<Page>("/api/days"), loadPets(), artReady]);
  busy = false;
  if (!d) return;
  for (const x of d.days) days.set(x.day, x);   // the newest week replaces what we had of those days
  if (!at || at === today) at = d.today;   // (reading today's page: a new day turns to it)
  today = d.today;
  things = d.things;
  const shown = wide() ? [at - 1, at] : [at];
  const key = JSON.stringify([filter, at, wide(), today, Object.values(pets).map((p) => p.stage), shown.map((n) => days.get(n)).map((x) => x && [x.moments.length, x.weather, !!x.summary])]);
  if (key === drawn) return;
  drawn = key;
  draw(root);
}
