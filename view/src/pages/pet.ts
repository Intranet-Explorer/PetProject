// SPEC-v3.5.3 §4: a page for every pet (#/pet/<id>): who it is, its family, its body and temperament, its words, what it
// made, its life, and (alive) how it is now. All of it was already recorded; this gathers it in one place.
// main.ts calls render() on every visit to its address, and again every few seconds while it is shown.
import "./pet.css";
import { el, wantWords } from "../dom";
import type { Kid } from "../dom";
import { icon } from "../icons";
import { go, href } from "../router";
import { a, button, getJSON, linked, petLink, portrait, thingLink, thingPic } from "../ui";
import { fam } from "../types";
import { allPets, familyName, lifeDays, namesOn, stageText } from "./family";
import type { Pet } from "./family";
import heart from "../../assets/third_party/crusenho/UI_TravelBook_IconHeart01a.png";
import star from "../../assets/third_party/crusenho/UI_TravelBook_IconStar01a.png";

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
type Thing = { id: string; name: string; recipe: Record<string, unknown>; where: string; gone: string | null; day: number; invented: boolean; statue: boolean };
type Page = {
  pet: Pet; named_after: { id: string; name: string } | null; parent: string | null; siblings: string[]; children: string[];
  traits: { body: { text: string; from: string | null }[]; temper: { text: string; from: string | null }[]; describe: string };
  moments: Moment[]; made: Thing[]; my_life: string | null;
  // SPEC-v3.5.4 §7, §9: its ambition, its bests and its family's (`by`: whose, for the family's)
  bests?: { ambition: { text: string; done: number | null } | null; own: Best[]; family: Best[] };
  words: { message: string[]; last_words: string | null; sayings: string[]; songs: { name: string; how: string }[]; walls: { text: string; place: string }[];
    beliefs: string[]; reads: { question: string; title: string; text: string; day: number }[] };
  now?: { feelings?: string; wants?: { text: string }[]; focus?: { words?: string } | null; doing?: string; asleep?: boolean; project?: { text: string } | null;
    plan?: { intention?: string } | null; carrying?: string[] };
};

/** The moments that make a life story; the rest ("made", "want", "took"…) are behind "show everything". */
const LIFE = new Set(["egg", "hatched", "named", "words", "stage", "room", "entered", "discovery", "invented", "tool", "built", "statue", "heirloom",
  "taught", "song", "wrote", "saying", "mark", "death"]);
const view = { all: false, things: false };
let drawn = "";

export async function render(root: HTMLElement, id: string | null) {
  const [data, page] = await Promise.all([allPets(), id ? getJSON<Page>(`/api/petpage/${encodeURIComponent(id)}`) : null]);
  if (!data || !page) {   // the engine away: keep what is shown; a pet it does not know: say so
    if (!drawn.startsWith(`${id}|`)) root.replaceChildren(el("p", "hint", id ? `No pet "${id}" here.` : "No pet chosen."));
    return;
  }
  const key = `${id}|${JSON.stringify([data, page, view])}`;
  if (key === drawn) return;
  if (!drawn.startsWith(`${id}|`)) Object.assign(view, { all: false, things: false });   // another pet: start folded
  drawn = key;
  const redraw = () => { drawn = `${id}|`; void render(root, id); };
  const by = new Map(data.pets.map((p) => [p.id, p])), p = by.get(page.pet.id) ?? page.pet;
  const today = p.died_day ?? data.day, things = Object.fromEntries(page.made.map((t) => [t.name, t.id]));
  const say = (text: string, day = today) => linked(text, namesOn(data.pets, day, p.id), things);
  const chips = (ids: (string | null)[]) => ids.map((i) => (i ? by.get(i) : null)).filter((q): q is Pet => !!q).map((q) => petLink(q, 64));
  const section = (cls: string, title: string, ...kids: (Kid | Kid[])[]) => el("section", `psec ${cls}`, el("h2", "", title), ...kids.flat());
  const w = page.words, lastSaid = w.last_words?.trim();

  // the header
  const head = el("div", `phead ${fam(p.family)} ${p.alive ? "alive" : "dead"}`,
    el("div", "pface", portrait(p, innerWidth < 640 ? 112 : 168)),
    el("div", "pwho",
      el("h1", "", p.name),
      page.named_after ? el("p", "", "Named after ", petLink(by.get(page.named_after.id) ?? { ...p, ...page.named_after }), ", who lived before it.") : null,
      el("p", "pfam", familyName(p.family), ` · generation ${p.gen}`),
      el("p", "", p.alive ? stageText(p) : el("span", "", icon("stone", 14), ` ${stageText(p)}`)),
      el("p", "", `born day ${p.born_day}`, p.alive ? "" : ` · died day ${p.died_day}${p.cause ? `, of ${p.cause}` : ""}`),
      p.alive ? button("Watch now", () => go("house", p.id), "watch") : null));

  // the jumps: on a phone the sections are a long way down
  const parts: [string, string][] = [["fam", "Family"], ["body", "Body"], ["words", "Words"], ["made", `Made (${page.made.length})`], ["life", "Life"]];   // (in the order of the page)
  if (page.bests) parts.splice(parts.length - 2, 0, ["bests", "Bests"]);
  if (page.now) parts.splice(1, 0, ["now", "Now"]);
  const jumps = el("nav", "pjump", a("← everyone", href("family"), "small"),
    ...parts.map(([k, t]) => button(t, () => root.querySelector(`.psec.${k}`)?.scrollIntoView({ behavior: "smooth" }), "chip")));

  const n = page.now, wants = (n?.wants ?? []).map((x) => wantWords(x.text)).slice(0, 4);
  const now = n && section("now", "Now",
    el("dl", "", ...([
      n.feelings ? [el("dt", "", "Feels"), el("dd", "", n.feelings)] : null,
      n.doing ? [el("dt", "", "Doing"), el("dd", "", n.asleep ? "asleep" : n.doing)] : null,
      n.focus?.words || n.plan?.intention ? [el("dt", "", "Mind on"), el("dd", "", ...say(n.focus?.words || n.plan?.intention || ""))] : null,
      n.project?.text ? [el("dt", "", "Project"), el("dd", "", ...say(n.project.text))] : null,
      wants.length ? [el("dt", "", "Wants"), el("dd", "", el("ul", "", ...wants.map((t) => el("li", "", ...say(t)))))] : null,
    ].flat() as Kid[])));

  const parent = chips([page.parent]), sibs = chips(page.siblings), kids = chips(page.children);
  const family = section("fam", "Family",
    el("dl", "",
      el("dt", "", "Parent"), el("dd", "chipsrow", ...(parent.length ? parent : [p.gen === 1 ? "none: it began a family" : "unknown"])),
      el("dt", "", "Siblings"), el("dd", "chipsrow", ...(sibs.length ? sibs : ["none"])),
      el("dt", "", "Children"), el("dd", "chipsrow", ...(kids.length ? kids : ["none"]))));

  const from = (f: string | null) => (f && by.get(f) ? [" (from ", petLink(by.get(f)!), ")"] : []);
  const body = section("body", "Body and temperament",
    el("p", "", ...say(`It is ${page.traits.describe}.`)),
    el("dl", "",
      el("dt", "", "Body"), el("dd", "", el("ul", "", ...page.traits.body.map((t) => el("li", "", t.text, ...from(t.from))))),
      el("dt", "", "Temper"), el("dd", "", el("ul", "", ...page.traits.temper.map((t) => el("li", "", t.text, ...from(t.from)))))));

  const quote = (text: string, day?: number) => el("blockquote", "", ...say(text, day));
  const message = w.message.at(-1)?.trim();
  const words = section("words", "Its words",
    lastSaid ? [el("h3", "", message === lastSaid ? "Last words (the same words as the message it left its children)" : "Last words"), quote(lastSaid)] : null,
    message && message !== lastSaid ? [el("h3", "", "The message it left its children"), quote(message)] : null,
    w.beliefs.length ? [el("h3", "", "What it believed (latest first)"), el("ul", "bul", ...[...w.beliefs].reverse().map((b) => el("li", "", ...say(b))))] : null,
    w.sayings.length ? [el("h3", "", "Sayings"), el("ul", "bul", ...w.sayings.map((s) => el("li", "", ...say(s))))] : null,
    w.songs.length ? [el("h3", "", "Songs"), el("ul", "bul", ...w.songs.map((s) => el("li", "", `“${s.name}”`, el("span", "hint", ` ${s.how === "by ear" ? "picked up by ear" : s.how}`))))] : null,
    w.walls.length ? [el("h3", "", "Written on walls"), el("ul", "bul", ...w.walls.map((s) => el("li", "", `“${s.text}”`, el("span", "hint", ` ${s.place}`))))] : null,
    w.reads.length ? [el("h3", "", "What it asked the book and the screens"), el("ul", "bul", ...w.reads.map((r) =>
      el("li", "", el("b", "", `“${r.question}”`), el("span", "hint", ` day ${r.day} · read about ${r.title}`), el("p", "read", r.text))))] : null,
    page.my_life ? [el("h3", "", "Its life, in its own words"), quote(page.my_life)] : null,
    !lastSaid && !message && !w.beliefs.length && !w.sayings.length && !w.songs.length && !w.walls.length && !w.reads.length && !page.my_life
      ? el("p", "hint", "Nothing yet.") : null);

  const MANY = 24, shown = view.things ? page.made : page.made.slice(0, MANY);
  const made = section("made", `What it made (${page.made.length})`,
    page.made.length ? el("div", "pthings", ...shown.map((t) => el("div", `pthing${t.gone ? " gone" : ""}`,
      Object.assign(el("a", "pic slot", thingPic(t.recipe, 2)), { href: href("thing", t.id) }),
      el("span", "", thingLink(t.id, t.name), t.invented ? " (invented)" : "", t.statue ? " (statue)" : ""),
      el("span", "hint", t.gone ?? t.where)))) : el("p", "hint", "Nothing yet."),
    page.made.length > MANY ? button(view.things ? "Show fewer" : `Show all ${page.made.length}`, () => { view.things = !view.things; redraw(); }, "chip") : null);

  // SPEC-v3.5.4 §7, §9: what it means to do with its life, and the best it and its family have done
  const B = page.bests, bestList = (bs: Best[]) => el("ul", "iconed", ...bs.map((b) => el("li", "", ticon(heart, 13),
    el("span", "", `${b.what}: `, b.text, ...(b.by && by.get(b.by) ? [" · ", petLink(by.get(b.by)!)] : [])))));
  const bests = B && section("bests", "Ambition and bests",
    el("h3", "", "Its ambition"), B.ambition ? el("p", "iconed", ticon(star, 12), el("span", "", ...say(B.ambition.text), B.ambition.done ? el("span", "hint", ` · done, day ${B.ambition.done}`) : null)) : el("p", "hint", "None yet."),
    el("h3", "", "Its bests"), B.own.length ? bestList(B.own) : el("p", "hint", "Nothing yet."),
    B.family.length ? [el("h3", "", `Its family's bests`), bestList(B.family)] : null);

  const moments = view.all ? page.moments : page.moments.filter((m) => LIFE.has(m.kind));
  const life = section("life", "Its life",
    el("ol", "timeline", ...moments.map((m) => el("li", `k-${m.kind}`, icon(m.kind, 14), el("span", "when", `day ${m.day}`), el("span", "", ...say(m.text, m.day)))),
      !p.alive && lastSaid ? el("li", "k-death", icon("speech", 14), el("span", "when", `day ${p.died_day}`), el("span", "", "its last words: ", el("i", "", `“${lastSaid.split(/(?<=[.!?])\s/)[0]}”`))) : null),
    button(view.all ? "Show only the big moments" : `Show everything (${page.moments.length})`, () => { view.all = !view.all; redraw(); }, "chip"));

  root.replaceChildren(el("div", "book petpage", head, jumps, el("div", "pcols", family, now, body, words, bests, made, life)));
}
