// SPEC-v3.5.3 §5: the Story tab. The house's history by world day, newest first (today and yesterday on top), each
// day headed with its season and weather and the chronicle's paragraph for it; filter chips by kind of moment; every
// pet and thing in a sentence a link. Older days come on demand. main.ts calls render() on every visit and every 4 s.
import "./story.css";
import { el, whole } from "../dom";
import { icon, PATHS } from "../icons";
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
const FINDS = new Set(["discovery", "invented", "forgotten", "tool", "room", "taught", "read", "drift", "arrival writing", "arrival songs", "arrival taming", "arrival radio", "arrival book"]);
const BUILD = new Set(["built", "statue", "mended", "worn", "held", "moved"]);
const WORDS = new Set(["saying", "crossed", "message", "words", "wrote", "song", "discarded", "scrubbed"]);
/** The many small comings and goings: in "Everything", not in the main story. */
const SMALL = new Set(["made", "unmade", "want", "entered", "nuzzle", "took", "machine", "fed", "stored", "told", "lost", "kept", "draught", "leak",
  "power", "power back", "delivery", "stocked", "mark", "planted", "harvest", "project", "message", "song"]);
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

let days: Day[] = [], more = false, today = 0, things: Record<string, string> = {};
let filter = "main", drawn = "", busy = false;

const ago = (d: number) => (d === today ? "Today" : d === today - 1 ? "Yesterday" : `Day ${d}`);

function dayBlock(d: Day, keep: (m: M) => boolean) {
  const shown = d.moments.filter(keep), rest = d.moments.length - shown.length;
  const sky = d.weather ? el("span", "sky", PATHS[d.weather] ? icon(d.weather) : null, d.weather) : null;
  return el("section", "sday",
    el("h3", "", ago(d.day), " ", el("span", "hint", d.day >= today - 1 ? `day ${d.day} · ` : "", d.season, sky ? " · " : "", sky)),
    d.summary && (filter === "main" || filter === "all") ? el("p", "chron", ...told(d.summary, d.day, null, things)) : null,
    shown.length ? el("ol", "storylist", ...shown.map((m) => momentRow(m, things)))
      : el("p", "empty", d.day === today ? "Nothing worth telling yet today." : filter === "main" ? "A quiet day." : "Nothing of this kind."),
    filter === "main" && rest ? el("p", "rest", `and ${rest} smaller moment${rest === 1 ? "" : "s"} (making, wanting, comings and goings) `,
      button("show everything", () => setFilter("all"), "link small")) : null);
}

function setFilter(f: string) { filter = f; drawn = ""; draw(document.getElementById("page-story")!); }

function draw(root: HTMLElement) {
  const keep = FILTERS.find((f) => f[0] === filter)![2];
  // under a chip, a day with nothing of that kind is left out (today and yesterday are always there)
  const list = days.filter((d) => filter === "main" || filter === "all" || d.day >= today - 1 || d.moments.some(keep));
  root.replaceChildren(el("div", "story",
    el("div", "chips filters", ...FILTERS.map(([k, label]) => chip(label, filter === k, () => setFilter(k)))),
    ...list.map((d) => dayBlock(d, keep)),
    more ? el("p", "earlier", button(`Earlier days (before day ${days.at(-1)!.day})`, () => void earlier(root), "button")) : el("p", "hint earlier", "That is the start of the house.")));
}

async function earlier(root: HTMLElement) {
  if (busy || !more) return;
  busy = true;
  // under a chip, a week can hold nothing of that kind: go back four at a time
  for (let i = 0; i < (filter === "main" || filter === "all" ? 1 : 4) && more; i++) {
    const d = await getJSON<Page>(`/api/days?before=${days.at(-1)!.day}`);
    if (!d) break;
    days.push(...d.days.filter((x) => x.day < days.at(-1)!.day));
    more = d.more;
  }
  busy = false;
  drawn = "";
  draw(root);
}

export async function render(root: HTMLElement, _id: string | null): Promise<void> {
  if (busy) return;
  busy = true;
  if (!root.childElementCount) root.replaceChildren(el("p", "empty", "Reading the story…"));
  const [d] = await Promise.all([getJSON<Page>("/api/days"), loadPets(), artReady]);
  busy = false;
  if (!d) return;
  // the newest week replaces what we had of those days; older weeks fetched earlier stay
  const low = d.days.at(-1)!.day;
  days = [...d.days, ...days.filter((x) => x.day < low)];
  if (days.length === d.days.length) more = d.more;
  today = d.today;
  things = d.things;
  const key = JSON.stringify([filter, Object.values(pets).map((p) => p.stage), days.map((x) => [x.day, x.moments.length, x.weather, !!x.summary])]);
  if (key === drawn) return;
  drawn = key;
  draw(root);
}
