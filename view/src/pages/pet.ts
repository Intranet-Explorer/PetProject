// SPEC-v3.5.3 §4, v3.5.7 §6: a page for every pet (#/pet/<id>), as a character sheet: the Travel Book open across the
// page. The left page is who it is (a big portrait on a lit pedestal, name, family, badges, Watch now, its needs, its
// body and temper, its family); the right page its quest log (ambition, project, wants), what it made and its words.
// The longer sections (its life, all its words, all it made, its bests) go on in the pages further down, and the
// bookmarks on the book's edge turn to them. The dead: the same sheet in sepia, with its stone and last words.
// main.ts calls render() on every visit to its address, and again every few seconds while it is shown.
import "./pet.css";
import { byname, el, wantWords } from "../dom";
import type { Kid } from "../dom";
import { icon } from "../icons";
import { petSheet } from "../petsprite";
import { go, href } from "../router";
import { a, button, getJSON, linked, petLink, portrait, thingLink, thingPic } from "../ui";
import { fam } from "../types";
import { allPets, familyName, namesOn, stageText } from "./family";
import type { Pet } from "./family";
import heart from "../../assets/third_party/crusenho/UI_TravelBook_IconHeart01a.png";
import star from "../../assets/third_party/crusenho/UI_TravelBook_IconStar01a.png";
import star2 from "../../assets/third_party/crusenho/UI_TravelBook_IconStar01b.png";
import tick from "../../assets/third_party/crusenho/UI_TravelBook_IconTick01a.png";
import iNow from "../../assets/third_party/crusenho/UI_Icon_Leaderboard01b.png";
import iBody from "../../assets/third_party/crusenho/UI_Icon_Manual01b.png";
import iHome from "../../assets/third_party/crusenho/UI_Icon_Home01b.png";
import iTrophy from "../../assets/third_party/crusenho/UI_Icon_Trophy01b.png";
import iWords from "../../assets/third_party/crusenho/UI_Icon_Contact01b.png";
import iMusic from "../../assets/third_party/crusenho/UI_Icon_Music01b.png";
import iLife from "../../assets/third_party/crusenho/UI_Icon_Display01b.png";

/** A Travel Book icon at x2 (skin.css img.ticon). */
function ticon(src: string, w: number) {
  const i = el("img", "ticon") as HTMLImageElement;
  i.src = src;
  i.alt = "";
  i.style.setProperty("--w", String(w));
  return i;
}

type Best = { what: string; text: string; by: string | null };
type Moment = { tick: number; day: number; hour: number; kind: string; text: string };
type Thing = { id: string; name: string; recipe: Record<string, unknown>; where: string; gone: string | null; day: number; invented: boolean; statue: boolean;
  heirloom: boolean; first: "house" | "family" | null };
type Page = {
  pet: Pet; named_after: { id: string; name: string } | null; parent: string | null; siblings: string[]; children: string[];
  traits: { body: { text: string; from: string | null }[]; temper: { text: string; from: string | null }[]; describe: string };
  moments: Moment[]; made: Thing[]; my_life: string | null;
  // SPEC-v3.5.4 §7, §9: its ambition, its bests and its family's (`by`: whose, for the family's)
  bests?: { ambition: { text: string; done: number | null } | null; own: Best[]; family: Best[] };
  // SPEC-v3.5.7 §6: its firsts, and the rest of its quest log (pages.pet_page)
  firsts?: { house: number; family: number };
  quest?: { ambition_thing: { id: string; name: string } | null; project: { text: string; day: number | null } | null;
    projects_done: { text: string; day: number | null }[]; wants: string[]; wants_done: { text: string; day: number }[] };
  words: { message: string[]; last_words: string | null; sayings: string[]; songs: { name: string; how: string }[]; walls: { text: string; place: string }[];
    beliefs: string[]; reads: { question: string; title: string; text: string; day: number }[] };
  now?: { feelings?: string; wants?: { text: string }[]; focus?: { words?: string } | null; doing?: string; asleep?: boolean; project?: { text: string } | null;
    plan?: { intention?: string } | null; carrying?: string[]; needs?: Record<string, number>;
    byname?: string | null; progress?: { what: string; have: number; need: number } | null };   // SPEC-v3.5.8 §6
};

/** The moments that make a life story; the rest ("made", "want", "took"…) are behind "show everything". */
const LIFE = new Set(["egg", "hatched", "named", "words", "stage", "room", "entered", "discovery", "invented", "tool", "built", "statue", "heirloom",
  "taught", "song", "wrote", "saying", "mark", "death"]);
const NEEDS: [string, string][] = [["energy", ""], ["comfort", ""], ["curiosity", "blue"], ["company", "red"]];   // (the mockup's fillers)
const view = { all: false, things: false };
let drawn = "";
const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const flip = () => dispatchEvent(new CustomEvent("pet:sound", { detail: "flip" }));
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// ---- the portrait's idle: its own breathing and blinking frames, slowly; a bob is in pet.css (neither with reduce motion) ----
let idle: { canvas: HTMLCanvasElement; p: Pet; i: number } | null = null;
setInterval(() => {
  if (!idle || !idle.canvas.isConnected || still()) return;
  const x = idle.canvas.getContext("2d")!, p = idle.p;
  const frames = petSheet(p.genome, p.drawn, { grey: p.drawn === "elder" ? 0.55 : 0 }).frames.idle;   // (asked each time: the body's parts may load after the page is drawn)
  idle.i = (idle.i + 1) % frames.length;
  x.clearRect(0, 0, idle.canvas.width, idle.canvas.height);
  x.drawImage(frames[idle.i], 0, 0, idle.canvas.width, idle.canvas.height);
}, 260);

// ---- the need bars fill smoothly from where they were, and flash when a value jumps (§9) ----
const was = new Map<string, number>();
function needBar(key: string, v: number, cls: string) {
  const i = el("i", ""), from = was.get(key);
  i.style.width = `${from ?? v}%`;
  if (from != null && from !== v) requestAnimationFrame(() => requestAnimationFrame(() => { i.style.width = `${v}%`; }));
  was.set(key, v);
  return el("span", `wbar ${cls}${from != null && Math.abs(from - v) >= 10 ? " jump" : ""}`, i);
}

export async function render(root: HTMLElement, id: string | null) {
  const [data, page] = await Promise.all([allPets(), id ? getJSON<Page>(`/api/petpage/${encodeURIComponent(id)}`) : null]);
  if (!data || !page) {   // the engine away: keep what is shown; a pet it does not know: say so
    if (!drawn.startsWith(`${id}|`)) root.replaceChildren(el("p", "hint", id ? `No hob "${id}" here.` : "No hob chosen."));
    return;
  }
  const key = `${id}|${JSON.stringify([data, page, view, innerWidth < 640])}`;
  if (key === drawn) return;
  if (!drawn.startsWith(`${id}|`)) Object.assign(view, { all: false, things: false });   // another pet: start folded
  drawn = key;
  const redraw = () => { drawn = `${id}|`; void render(root, id); };
  const by = new Map(data.pets.map((p) => [p.id, p])), p = by.get(page.pet.id) ?? page.pet;
  const today = p.died_day ?? data.day, things = Object.fromEntries(page.made.map((t) => [t.name, t.id]));
  const say = (text: string, day = today) => linked(text, namesOn(data.pets, day, p.id), things);
  const sec = (cls: string, title: string, src: string, ...kids: (Kid | Kid[])[]) =>
    el("section", `psec ${cls}`, el("h2", "shead", Object.assign(el("img", "sicon px") as HTMLImageElement, { src, alt: "" }), title), ...kids.flat());
  const w = page.words, lastSaid = w.last_words?.trim(), message = w.message.at(-1)?.trim();
  const phone = innerWidth < 640;

  // ---- the left page: who it is ----
  const ped = el("div", "ped slot", portrait(p, phone ? 144 : 192));
  const face = ped.querySelector("canvas")!;
  if (p.alive && p.stage !== "egg") {
    face.classList.add("bob");
    idle = { canvas: face, p, i: 0 };
  }
  const B = page.bests, F = page.firsts, heirlooms = page.made.filter((t) => t.heirloom).length;
  const badge = (text: string, gold = false) => el("span", `badge chip${gold ? " gold" : ""}`, gold ? ticon(star, 7) : null, text);
  const badges = el("div", "badges",
    B?.ambition?.done ? badge("ambition reached", true) : null,
    F?.house ? badge(`${F.house} house first${F.house === 1 ? "" : "s"}`) : null,
    F?.family ? badge(`${F.family} family first${F.family === 1 ? "" : "s"}`) : null,
    heirlooms ? badge(`${heirlooms} heirloom${heirlooms === 1 ? "" : "s"}`) : null);
  const hero = el("div", "hero", ped,
    el("div", "pwho",
      el("h1", "pname", p.name),
      byname({ byname: p.byname ?? page.now?.byname }) ? el("p", "bn", byname({ byname: p.byname ?? page.now?.byname })!) : null,   // SPEC-v3.5.8 §6
      page.named_after ? el("p", "", "named after ", petLink(by.get(page.named_after.id) ?? { ...p, ...page.named_after })) : null,
      el("p", "", `${familyName(p.family).toLowerCase()} - generation ${p.gen}`),
      el("p", "", p.alive ? `${stageText(p)} - born day ${p.born_day}` : `born day ${p.born_day} - died day ${p.died_day}${p.cause ? `, of ${p.cause}` : ""}`),
      badges.childElementCount ? badges : null,
      p.alive ? button("Watch now", () => go("house", p.id), "watch") : null));

  const n = page.now;
  const now = n?.needs && sec("now", "Now", iNow,
    el("div", "needs", ...NEEDS.flatMap(([k, cls]) => {
      const v = Math.round(n.needs![k] ?? 0);
      return [el("span", "", k), needBar(`${p.id}.${k}`, v, cls), el("span", "num", String(v))];
    })),
    el("dl", "", ...([
      n.feelings ? [el("dt", "", "Feels"), el("dd", "", n.feelings)] : null,
      n.doing ? [el("dt", "", "Doing"), el("dd", "", n.asleep ? "asleep" : n.doing)] : null,
      n.focus?.words || n.plan?.intention ? [el("dt", "", "Mind on"), el("dd", "", ...say(n.focus?.words || n.plan?.intention || ""))] : null,
    ].flat() as Kid[])));

  const from = (f: string | null) => (f && by.get(f) ? [" - from ", petLink(by.get(f)!)] : []);
  const body = sec("body", "Body and temper", iBody,
    el("div", "traits", ...[...page.traits.body, ...page.traits.temper].map((t) => el("span", "chip", t.text, ...from(t.from)))),
    el("p", "describe", ...say(`It is ${page.traits.describe}.`)));

  const kin = (ids: (string | null)[], role: string) => ids.map((i) => (i ? by.get(i) : null)).filter((q): q is Pet => !!q)
    .map((q) => el("div", "kin", petLink(q, 48), el("span", "role", role)));
  const kins = [...kin([page.parent], "parent"), ...kin(page.siblings, "sibling"), ...kin(page.children, "child")];
  const family = sec("fam", "Family", iHome,
    kins.length ? el("div", "kins", ...kins) : null,
    !page.parent ? el("p", "hint", p.gen === 1 ? "No parent: it began a family." : "Its parent is not known.") : null);

  // ---- the right page: its quest log, what it made, its words ----
  const Q = page.quest, quest = (tag: string, done: boolean, text: Kid[], ...more: Kid[]) =>
    el("li", `quest${done ? " done" : ""}`, el("span", "box", done ? ticon(tick, 9) : null), el("div", "",
      el("span", "qtag", tag), el("p", "", ...text), ...more));
  const self = new RegExp(`^(?:${[p.stored_name, p.name.replace(/ [IVX]+$/, "")].filter(Boolean).map((s) => s!.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")}) `);
  const quests = [
    B?.ambition ? quest("ambition", !!B.ambition.done, say(cap(B.ambition.text)), B.ambition.done
      ? el("span", "qwhen", `reached day ${B.ambition.done}`, ...(Q?.ambition_thing ? [" - ", thingLink(Q.ambition_thing.id, Q.ambition_thing.name)] : [])) : null) : null,
    Q?.project ? quest("project", false, say(Q.project.text), Q.project.day ? el("span", "qwhen", `since day ${Q.project.day}`) : null) : null,
    ...(Q?.wants ?? []).map((t) => quest("want", false, say(cap(wantWords(t))))),
    ...(Q?.projects_done ?? []).map((x) => quest("project", true, say(x.text), x.day ? el("span", "qwhen", `finished day ${x.day}`) : null)),
    ...(Q?.wants_done ?? []).map((x) => quest("want", true, say(cap(x.text.replace(self, "")), x.day), el("span", "qwhen", `done day ${x.day}`))),
  ].filter(Boolean) as HTMLElement[];
  // SPEC-v3.5.8 §6: a project's measurable progress, as a small bar under it ("3 of 5 planks")
  const G = page.now?.progress, gauge = G && G.need > 0 ? el("span", "qprog", el("span", "wbar", Object.assign(el("i"), { style: `width:${Math.round((100 * Math.min(G.have, G.need)) / G.need)}%` })),
    el("span", "qwhen", `${G.have} of ${G.need} ${G.what}`)) : null;
  if (gauge) { const pq = quests.find((q) => q.querySelector(".qtag")?.textContent === "project" && !q.classList.contains("done")); if (pq) pq.lastElementChild!.append(gauge); else quests.splice(B?.ambition ? 1 : 0, 0, quest("project", false, [cap(G!.what)], gauge)); }
  const questLog = sec("quests", "Quest log", iTrophy, quests.length ? el("ol", "qlist", ...quests) : el("p", "hint", "No ambition, project or wants recorded."));

  const slot = (t: Thing) => {
    const s = Object.assign(el("a", `islot slot dark${t.gone ? " gone" : ""}`, thingPic(t.recipe, 2),
      t.first ? ticon(t.first === "house" ? star : star2, 6) : null), { href: href("thing", t.id), title: t.name }) as HTMLAnchorElement;
    s.setAttribute("aria-label", `${t.name}${t.first ? `, first in the ${t.first === "house" ? "house" : "family"}` : ""}`);
    return s;
  };
  const best = [...page.made].sort((x, y) => Number(!!y.first) - Number(!!x.first) || (y.first === "house" ? 1 : 0) - (x.first === "house" ? 1 : 0));
  const SLOTS = 12;
  const madeTop = sec("made", `Made: ${page.made.length}`, iTrophy,   /* (Toriko draws brackets like C and J) */
    page.made.length ? el("div", "islots", ...best.slice(0, SLOTS).map(slot)) : el("p", "hint", "Nothing yet."),
    page.made.length > SLOTS ? button(`All ${page.made.length}, further on`, () => turnTo("more-made"), "link small") : null);

  const quote = (text: string, day?: number) => el("blockquote", "", ...say(text, day));
  const stone = !p.alive ? el("section", "psec stone",
    el("div", "grave", icon("stone", 32), el("p", "", `${p.name}, day ${p.born_day} - ${p.died_day}`)),
    lastSaid ? el("h3", "lw", "Its last words") : null, lastSaid ? quote(lastSaid) : null) : null;
  const wordsTop = sec("words", "Its words", iWords,
    message && message !== lastSaid ? [quote(message), el("p", "hint", p.alive ? "its message to its children, so far" : "the message it left its children")]
      : message ? el("p", "hint", "Its message to its children was its last words.") : el("p", "hint", "No message to its children yet."));

  // ---- the further pages: its life, its words, all it made, its bests ----
  const words = sec("more-words", "Its words, all", iWords,
    w.beliefs.length ? [el("h3", "", "What it believed"), el("ul", "bul", ...[...w.beliefs].reverse().map((b) => el("li", "", ...say(b))))] : null,
    w.sayings.length ? [el("h3", "", "Sayings"), el("ul", "bul", ...w.sayings.map((s) => el("li", "", ...say(s))))] : null,
    w.songs.length ? [el("h3", "", "Songs"), el("ul", "bul", ...w.songs.map((s) => el("li", "", `“${s.name}”`, el("span", "hint", ` ${s.how === "by ear" ? "picked up by ear" : s.how}`))))] : null,
    w.walls.length ? [el("h3", "", "Written on walls"), el("ul", "bul", ...w.walls.map((s) => el("li", "", `“${s.text}”`, el("span", "hint", ` ${s.place}`))))] : null,
    w.reads.length ? [el("h3", "", "Asked of the book"), el("ul", "bul", ...w.reads.map((r) =>
      el("li", "", `“${r.question}”`, el("span", "hint", ` day ${r.day} - read about ${r.title}`), el("p", "read", r.text.length > 160 ? `${r.text.slice(0, 160).replace(/\s+\S*$/, "")}…` : r.text))))] : null,
    page.my_life ? [el("h3", "", "Its life, in its own words"), quote(page.my_life)] : null,
    !w.beliefs.length && !w.sayings.length && !w.songs.length && !w.walls.length && !w.reads.length && !page.my_life ? el("p", "hint", "Nothing more yet.") : null);

  const MANY = 24, shown = view.things ? page.made : page.made.slice(0, MANY);
  const made = sec("more-made", `What it made (${page.made.length})`, iTrophy,
    page.made.length ? el("div", "pthings", ...shown.map((t) => el("div", `pthing${t.gone ? " gone" : ""}`,
      slot(t),
      el("span", "", thingLink(t.id, t.name), t.invented ? " (invented)" : "", t.statue ? " (statue)" : "", t.heirloom ? " (heirloom)" : ""),
      el("span", "hint", t.gone ?? t.where)))) : el("p", "hint", "Nothing yet."),
    page.made.length > MANY ? button(view.things ? "Show fewer" : `Show all ${page.made.length}`, () => { view.things = !view.things; redraw(); }, "chip") : null);

  const bestList = (bs: Best[]) => el("ul", "iconed", ...bs.map((b) => el("li", "", ticon(heart, 13),
    el("span", "", `${b.what}: `, b.text, ...(b.by && by.get(b.by) ? [" - ", petLink(by.get(b.by)!)] : [])))));
  const bests = B && (B.own.length || B.family.length) ? sec("bests", "Bests", iMusic,
    B.own.length ? [el("h3", "", "Its own"), bestList(B.own)] : null,
    B.family.length ? [el("h3", "", "Its family's"), bestList(B.family)] : null) : null;

  const moments = view.all ? page.moments : page.moments.filter((m) => LIFE.has(m.kind));
  const life = sec("more-life", "Its life", iLife,
    el("ol", "timeline", ...moments.map((m) => el("li", `k-${m.kind}`, icon(m.kind, 14), el("span", "when", `day ${m.day}`), el("span", "", ...say(m.text, m.day)))),
      !p.alive && lastSaid ? el("li", "k-death", icon("speech", 14), el("span", "when", `day ${p.died_day}`), el("span", "", "its last words: ", el("i", "", `“${lastSaid.split(/(?<=[.!?])\s/)[0]}”`))) : null),
    button(view.all ? "Show only the big moments" : `Show everything (${page.moments.length})`, () => { view.all = !view.all; redraw(); }, "chip"));

  // the bookmarks: turn to the long sections further on
  const turnTo = (cls: string) => {
    const t = root.querySelector<HTMLElement>(`.psec.${cls}`);
    if (!t) return;
    flip();
    t.scrollIntoView({ behavior: still() ? "auto" : "smooth", block: "start" });
    if (!still()) { t.classList.remove("turned"); void t.offsetWidth; t.classList.add("turned"); }
  };
  const marks = el("nav", "marks", a("everyone", href("family"), "mark back"),
    ...([["more-life", "Life"], ["more-words", "Words"], ["more-made", "Made"]] as const).map(([k, t]) => button(t, () => turnTo(k), "mark")));

  root.replaceChildren(el("div", `sheet ${fam(p.family)} ${p.alive ? "alive" : "dead"}`,
    marks,
    el("div", "spread",
      el("div", "pg left", hero, now, body, family),
      el("div", "pg right", stone, questLog, madeTop, wordsTop)),
    el("div", "spread further",
      el("div", "pg left", life, bests),
      el("div", "pg right", words, made))));
}
