// SPEC-v3.5.7 §5: a thing's card, on a Travel Book paper panel (hover_card.png): its picture in a slot (a gold star if
// it was a first), its name, kind and use, its badges and the day it was made, its maker and where it was made, what it
// was made from, how much it has been used and by whom, where it is and whose it is, and what pets said or wrote about
// it. Each line only when the house has recorded it. thingCard() gives the card at once, from what the caller has (the
// room's snapshot), and fills it in when /api/thing/<key> answers (kept 30 s: the room hovers often). The Things tab's
// panel and a thing's page (pages/things.ts) are the same card with its history after it.
import "./thingcard.css";
import { el, thingName } from "./dom";
import type { Kid } from "./dom";
import { loadPets, petOf } from "./pages/story";
import { artReady, hasSprite, kindOf, sprite } from "./sprite";
import { getJSON, petLink, portrait, thingPic } from "./ui";
import { svg } from "./icons";
import STAR from "../assets/third_party/crusenho/UI_TravelBook_IconStar01a.png";

export type Thing = {
  id: string; name: string; recipe: Record<string, any>; by: string | null; by_name: string | null; owner: string | null; family: number | null;
  room: string | null; room_name: string | null; where: string; gone: string | null; tick: number | null; day: number | null; bits: string[];
  uses: number; heirloom: boolean; invented: boolean; statue: boolean; keepsake: boolean;
  of?: string; standing?: boolean; raised_day?: number | null; makers?: { id: string; name: string }[];
  star?: number | null;   // SPEC-v3.5.4 §10: the tick the visitor gave it a star
  first?: "house" | "family" | null;   // a first, from the house's feats (kept from day 61)
  gone_day?: number | null;
  stored?: boolean;   // SPEC-v3.5.12 §1: it is in the store
  found?: { from: string; tier: string; by: string; tick: number } | null;   // SPEC-v3.6a §3: it came up out of the pond
  // SPEC-v3.5.8 §6, each only when recorded (Made in types.ts): the title shows; how it was made; the bits it was made
  // from (a gone thing too); who used it, how often
  title_shown?: boolean; how?: string | null; from?: string[] | null; users?: Record<string, number> | null;
};
/** What a hob said or wrote naming it (`how`), or (SPEC-v3.5.8 §6, `at`) said or thought about it as it made it or set it down. */
type Word = { pet: string; day?: number | null; how?: string; text: string; tick?: number; at?: "made" | "set down" };
export type ThingPage = Thing & {
  moments: import("./pages/story").M[]; does: string | null;
  use?: string | null; material?: string; joined?: string[]; invention?: boolean; made_in?: string | null;
  used_by?: { id: string; n: number }[]; words?: Word[];
};
/** What a caller already has: the room's snapshot gives `made: {recipe, by, owner, uses, heirloom, star, …}` and the name. */
export type Quick = Partial<ThingPage> & { name: string };

const kept = new Map<string, { at: number; p: Promise<ThingPage | null> }>();
/** The thing's page data, asked again at most every 30 s. */
export function loadThing(key: string) {
  const k = kept.get(key);
  if (k && Date.now() - k.at < 30000) return k.p;
  const p = getJSON<ThingPage>(`/api/thing/${encodeURIComponent(key)}`);
  kept.set(key, { at: Date.now(), p });
  return p;
}

/** The card for the thing `key`, at once from `quick`, filled in when the house answers. `hint`: say "click for its page". */
export function thingCard(key: string, quick?: Quick, hint = true): HTMLElement {
  const box = el("div", "thingcard paper");
  if (quick) box.replaceChildren(...cardBody(quick, hint));
  void Promise.all([loadThing(key), loadPets(), artReady]).then(([t]) => { if (t) box.replaceChildren(...cardBody(quick ? fill(t, quick) : t, hint)); });
  return box;
}
/** The house's answer, with what the room's snapshot knows and the answer does not (yet) say kept. */
function fill(t: ThingPage, quick: Quick): ThingPage {
  const out: Record<string, unknown> = { ...t };
  for (const [k, v] of Object.entries(quick)) { const x = out[k]; if (x == null || (Array.isArray(x) && !x.length)) out[k] = v; }
  return out as ThingPage;
}

/** A statue has no sprite: a figure on a plinth, in the text's colour. */
export const statuePic = (scale: number) => svg("svg", { viewBox: "0 0 16 16", width: 16 * scale, height: 16 * scale, class: "statuepic", "shape-rendering": "crispEdges", "aria-hidden": "true" },
  svg("path", { d: "M7 1h2v2H7ZM6 3h4v5H6ZM5 4h1v3H5ZM10 4h1v3h-1ZM6 8h1v3H6ZM9 8h1v3H9ZM4 11h8v1H4ZM3 12h10v3H3Z", fill: "currentColor" }));
/** Its picture at the largest whole-number scale that fits `box` px. */
export function fitPic(t: Pick<Thing, "recipe"> & { statue?: boolean; from?: string[] | null; bits?: string[] }, box: number) {
  if (t.statue) return statuePic(Math.floor(box / 16));
  const one = thingPic(t.recipe, 1), bit = t.from?.[0] ?? t.bits?.[0];   // (SPEC-v3.5.10 §3: a charm shows what it is made of)
  return thingPic(t.recipe, Math.max(1, Math.floor(box / Math.max(one.width, one.height, 1))), bit);
}

const who = (id: string | null | undefined, box = 0) => { const p = petOf(id); return p ? petLink(p, box) : null; };
const icon = (src: string, cls = "") => Object.assign(el("img", `px ${cls}`.trim()) as HTMLImageElement, { src, alt: "" });
const badge = (kids: Kid[], cls = "") => el("span", `tcbadge ${cls}`.trim(), ...kids);
const andList = (xs: Kid[]) => xs.flatMap((x, i) => [i ? (i === xs.length - 1 ? " and " : ", ") : "", x]);
/** The engine keeps a purpose to 80 letters; one cut there trails off. */
const whole = (s: string) => (s.length >= 78 && !/[.!?]$/.test(s) ? `${s}…` : s);

/** SPEC-v3.5.10 §2: whatever else the room's hover shows (a hob, a fixture, a creature, a door, a stone) on the same
 *  paper as a thing's card: its picture in the slot, its name, what it is, then its lines (`rows` and `sec` make them
 *  as the thing card does). Nothing in it is cut: it wraps. */
export const roomCard = (pic: Node | null, name: Kid[], kind: Kid[], ...lines: Kid[]) => el("div", "thingcard paper roomcard",
  el("div", "tctop", pic ? el("div", "tcslot slot dark", pic) : null, el("div", "tchead", el("h3", "title tcname", ...name), kind.some(Boolean) ? el("p", "tckind", ...kind) : null)), ...lines);
export const rows = (rs: ([string, Kid[]] | null)[]) => {
  const ok = rs.filter((r): r is [string, Kid[]] => !!r && r[1].some((k) => k != null && k !== ""));
  return ok.length ? el("dl", "tcrows", ...ok.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", ...v)])) : null;
};
export const sec = (title: string) => el("h4", "title tcsec", title);

/** "a small soft grey cushion", "a statue". */
function kindWords(t: Quick) {
  if (t.statue) return "a statue";
  const { kind, color, size } = kindOf(t.recipe as never);
  const words = [size === 1 ? "small" : size === 3 ? "large" : "", t.invented ? "" : t.recipe?.material ?? t.material, color, kind].filter(Boolean).join(" ");
  return `${/^[aeiou]/.test(words) ? "an" : "a"} ${words}`;
}

/** The card's lines for `t`: what is not recorded is left out. */
export function cardBody(t: Quick, hint = false): Node[] {
  const out: Node[] = [];
  const pic = el("div", "tcslot slot dark", fitPic(t as Thing, 80), t.first ? icon(STAR, "tcstar") : null);
  if (t.first) pic.title = t.first === "house" ? "the first in the house" : "the first in its family";
  const maker = t.by ? petOf(t.by) : undefined;
  const badges = [
    t.first === "house" ? badge([icon(STAR), "FIRST IN THE HOUSE"], "gold") : t.first === "family" ? badge(["FIRST IN ITS FAMILY"], "silver") : null,
    t.invention ? badge(["INVENTED"], "blue") : null,
    t.heirloom ? badge(["HEIRLOOM"]) : null,
    t.found?.from === "pond" ? badge([t.found.tier && t.found.tier !== "common" ? `FROM THE POND · ${t.found.tier.toUpperCase()}` : "FROM THE POND"], "pond") : null,   // SPEC-v3.6a §6
    t.star != null ? badge([icon(STAR), "STAR FROM THE VISITOR"], "gold") : null,
    t.day != null ? badge([`day ${t.day}`], "day") : null,
  ].filter(Boolean) as Node[];
  out.push(el("div", "tctop", pic, el("div", "tchead",
    el("h3", "title tcname", ...thingName(t.name, t.recipe, t.title_shown)),
    el("p", "tckind", kindWords(t), ...(t.statue && t.of ? [" of ", who(t.of) ?? "someone"] : []), t.use ? ` - ${t.use}` : null),
    badges.length ? el("p", "tcbadges", ...badges) : null,
    maker || t.made_in ? el("div", "tcmaker", maker ? portrait(maker, 48) : null, el("div", "",
      maker ? el("div", "", t.statue ? "begun by " : t.found ? "pulled up out of the pond by " : "made by ", petLink(maker)) : null,
      t.how ? el("div", "tcwhere", t.how) : null,   // SPEC-v3.5.8 §6: "woven at the loom"
      t.made_in ? el("div", "tcwhere", `in ${t.made_in}`) : null)) : null)));

  // made from: the bits (the house keeps them on a standing thing, not on a gone one), and what it was joined from
  const bits = new Map<string, number>();
  for (const b of t.from?.length ? t.from : t.bits ?? []) bits.set(b, (bits.get(b) ?? 0) + 1);   // (SPEC-v3.5.8 §6: `from` is kept for a gone thing too)
  const mats: Node[] = [...bits].map(([b, n]) => el("span", "tcmat slot", hasSprite(`bit.${b}`) ? sprite(`bit.${b}`, 2) : null, n > 1 ? `${b} x${n}` : b));
  if (t.joined?.length) mats.push(el("span", "tcmat slot", "joined from ", ...andList(t.joined.map((n) => `'${n}'`))));
  if (mats.length) out.push(el("h4", "title tcsec", "Made from"), el("div", "tcmats", ...mats));

  // lately
  const rows: [string, Kid[]][] = [];
  if (t.statue) {
    if (t.makers?.length) rows.push([t.standing ? "raised by" : "worked on by", [...andList(t.makers.map((m) => who(m.id) ?? m.name)), t.raised_day ? `, day ${t.raised_day}` : ""]]);
  } else if (t.users && Object.keys(t.users).length) {   // SPEC-v3.5.8 §6: "used most by Pim (5), Odo (2)"
    const top = Object.entries(t.users).sort((a, b) => b[1] - a[1]).map(([id, n]) => [who(id), n] as const).filter(([w]) => w).slice(0, 3);
    if (top.length) rows.push(["used", [t.uses ? `${t.uses === 1 ? "once" : `${t.uses} times`}, ` : "", "most by ", ...top.flatMap(([w, n], i) => [i ? ", " : "", w, ` (${n})`])]]);
  } else if (t.uses != null) {
    const top = t.used_by?.[0], seen = (t.used_by ?? []).reduce((s, u) => s + u.n, 0);
    const most = top && top.n >= 3 && who(top.id);
    // (the house counts a use when the thing did something for a pet; the log also sees a pet sit on it or play with it)
    rows.push(["used", [el("span", "", t.uses ? (t.uses === 1 ? "once" : `${t.uses} times`) : most ? null : "not yet", ...(most ? [t.uses ? ", most often by " : "most often by ", most] : []),
      most ? el("span", "tcbar", el("span", "wbar", Object.assign(el("i"), { style: `width:${Math.round((100 * top.n) / seen)}%` })),
        el("span", "tcsmall", `${top.n} of the ${seen} times the house saw it used`)) : null)]]);
  }
  if (t.where) rows.push([t.gone ? "gone" : "where", [`${t.where}${t.gone && t.gone_day ? `, day ${t.gone_day}` : ""}`]]);
  const owner = t.owner && who(t.owner);
  if (owner) rows.push(["owner", [owner]]);
  if (rows.length) out.push(el("h4", "title tcsec", "Lately"), el("dl", "tcrows", ...rows.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", ...v)])));

  // words: its maker's purpose when it made it, then anything pets said or wrote naming it
  const purpose = t.does ?? t.recipe?.purpose;
  const words: Node[] = [];
  if (purpose && !t.statue) words.push(el("p", "", `“${whole(purpose)}” - `, maker ? petLink(maker) : t.by_name ?? "its maker", ", when it made it"));
  // SPEC-v3.5.8 §6: the last one or two things said or thought as it was made or set down, then words naming it
  for (const w of (t.words ?? []).filter((w) => w.at).slice(-2)) words.push(el("p", "", `“${w.text}” - `, who(w.pet) ?? "a hob", w.at === "made" ? ", as it made it" : ", as it set it down"));
  for (const w of (t.words ?? []).filter((w) => !w.at)) words.push(el("p", "", `“${w.text}” - `, who(w.pet) ?? "a hob", `, ${w.how}${w.day ? `, day ${w.day}` : ""}`));
  if (words.length) out.push(el("blockquote", "tcwords", ...words));
  if (hint) out.push(el("p", "tchint", "click for its page"));
  return out;
}
