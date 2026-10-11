// The drawer (SPEC-v3 §10.1): Mind and Things here; Family, Story and Lab in their own files.
// The numbers shown here are for the visitor. No pet ever sees them.
import { bar, dayOf, el, face, fold, link, plural, radial, refill, when, whole } from "./dom";
import type { Ctx, Kid } from "./dom";
import { family, record } from "./family";
import { lab, story } from "./story";
import { thingPicture } from "./things";
import { NEEDS } from "./types";
import type { Made } from "./types";

const MARK: Record<string, string> = { correct: "✓ as it expected", wrong: "✗ not as it expected", unscorable: "no way to tell" };
const TABS: Record<string, (c: Ctx) => Kid[]> = { mind, things, family, story, lab };
/** Where each tab's extra facts come from. They are asked for only while the tab is open. */
export const SOURCE: Record<string, (c: Ctx) => string | null> = {
  mind: (c) => (c.sel ? `/api/pet/${c.sel}` : null), things: () => "/api/things", family: () => "/api/family", story: () => "/api/story", lab: () => "/api/lab",
};

/** The tabs that also show what SPEC-v3.1 added: the walls, the songbook, the library, the radio, the discoveries. */
export const MORE: Record<string, string> = { family: "/api/v31", story: "/api/v31" };

export function renderDrawer(tab: string, c: Ctx) {
  const panel = document.querySelector<HTMLElement>(`[data-panel="${tab}"]`);
  if (!panel || !TABS[tab]) return;
  const note = c.replay && tab !== "things" ? el("p", "hint note", "This is a replay. What is in the engine's memory here is as the house is now, not as it was then.") : null;
  refill(panel, [note, ...TABS[tab](c)]);
}

const quote = (text: string, cls = "") => el("blockquote", cls, text);
const section = (title: string, ...kids: Kid[]) => (kids.some((k) => k) ? el("section", "", el("h3", "", title), ...kids) : null);
const list = (cls: string, items: Kid[], none: string) => el("ul", cls, ...(items.length ? items : [el("li", "empty", none)]));

function clock(sec: number) {
  return `${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, "0")}`;
}

// ---- Mind: the chosen pet ----

function mind(c: Ctx): Kid[] {
  const p = c.snap.pets.find((p) => p.id === c.sel);
  if (!p) return [el("p", "empty", "Nobody is chosen. Click a pet in the room or on a card.")];
  const d = c.api.mind?.pet?.id === p.id ? c.api.mind : {};
  const where = c.snap.rooms.find((r) => r.id === p.room)?.name ?? "the house";
  const parent = c.snap.pets.find((q) => q.id === p.parent);
  const stage = p.stage === "dead" ? `died of ${p.cause}` : p.stage;
  const head = el("div", "who", face(c, p),
    el("div", "", el("h2", "", p.stage === "egg" ? p.name ?? "An egg" : p.label),
      el("p", "hint", `${stage} · generation ${p.gen}${p.days != null ? ` · ${plural(Math.round(p.days * 10) / 10, "day")}` : ""}`),
      el("p", "hint", `in ${where}${parent ? ` · ${parent.label}'s child` : ""}${c.snap.pets.some((q) => (q.family ?? 1) !== (p.family ?? 1)) ? ` · of the ${p.family === 2 ? "second" : "first"} family` : ""}`),
      p.seems ? el("p", "", `Seems ${p.seems}; ${p.asleep ? "asleep" : p.doing}.`) : null,
      p.animals?.length ? el("p", "hint", `Its ${p.animals.length > 1 ? "animals" : "animal"}: ${p.animals.map((a) => (a.name ? `${a.name} the ${a.kind}` : `a ${a.kind}`)).join(", ")}.`) : null,
      p.weak ? el("p", "bad", "It has grown weak.") : null));
  const told = (d.told ?? []) as { who: string; kind: string; text: string }[];
  const words = told.filter((t) => t.kind !== "tell"), tells = told.filter((t) => t.kind === "tell");
  const toldBy = section(`What its ${words[0]?.who ?? parent?.word ?? "parent"} told it`,
    ...words.map((t) => el("div", "", t.kind === "last words" ? el("p", "hint", "Last words") : null, quote(t.text))));
  if (p.stage === "egg") return [head, el("p", "", `Not hatched yet. It should hatch in about ${clock(p.hatches_in ?? 0)}.`), toldBy,
    !p.parent && d.told && !words.length ? el("p", "hint", "It is nobody's egg: no one left it any words.") : null];   // a foundling (SPEC-v3.1 §7.1)
  if (p.stage === "dead") return [head, ...(d.life ? record(c, d.life) : [el("p", "empty", "Its life record is being fetched.")])];

  const needs = el("div", "needs", ...NEEDS.map((n) => {   // the word is what the pet feels; the number is only ever shown here
    const v = p.needs?.[n] ?? 0, low = (p.levels?.[n] ?? 0) >= 3;
    return el("div", low ? "need low" : "need", el("span", "", n), el("b", "", p.felt?.[n] ?? ""), bar(v), el("span", "num", Math.round(v)));
  }));
  const plan = p.plan, last = p.last_plan;
  const now = el("section", "",
    el("h3", "", p.asleep ? "Asleep" : plan ? plan.intention : p.thinking ? "Thinking about what to do…" : "Between intentions"),
    plan && !p.asleep ? quote(plan.thought, "thought") : null,
    plan && !p.asleep ? el("ol", "steps", ...plan.steps.map((s, i) => el("li", i < plan.i ? "done" : i === plan.i ? "now" : "",
      el("span", "", i < plan.i ? "✓" : i === plan.i ? "▸" : "·"), el("span", "", s)))) : null,
    plan && !p.asleep ? el("p", "hint", `It expects: ${plan.expect || "nothing in particular"}. It thought because: ${plan.why}.`) : null,
    last ? el("p", "hint", `Before that: ${last.intention} `, el("span", last.score, last.ended === "done" ? MARK[last.score] : `${last.ended.split(":")[0]}, ${MARK[last.score]}`)) : null);
  const senses = ((d.senses ?? []) as unknown[]).map((s) => (typeof s === "string" ? s : Array.isArray(s) ? String(s.at(-1)) : JSON.stringify(s)));
  const project = section("Its project",
    p.project ? el("p", "", `“${whole(p.project.text)}” `, el("span", "hint", `since day ${dayOf(c.snap, p.project.since)}`)) : el("p", "empty", "None just now."),
    ...((d.projects ?? []) as { text: string; how: string }[]).map((x) => el("p", "hint", `${x.how}: “${whole(x.text)}”`)));
  // SPEC-v3.1: what it last asked the book and what it read there (§6.3), and the songs it carries (§3)
  const read = section("What it read in the book", ...(p.read ?? []).map((r) => el("div", "", el("p", "hint", `It asked: “${r.question}” · ${when(c.snap, r.tick)}`),
    r.text ? el("blockquote", "", el("b", "", `${r.title}. `), r.text) : el("p", "hint", "The book had nothing to say to that."))));
  const songs = (p.songs ?? []).map((id) => c.snap.songs?.[id]).filter((s) => !!s);
  const sings = section(`Songs it knows (${songs.length})`, songs.length ? el("ul", "plain", ...songs.map((s) => {
    const play = link("▶", () => c.hear(s.notes, p.id), "play");
    play.setAttribute("aria-label", `Hear ${p.label} sing “${s.name}”`);
    return el("li", "", play, ` ${s.name} `, el("span", "hint", s.by === p.id ? (s.from ? "as it heard it" : "its own") : ""));
  })) : null);
  const beliefs = (d.beliefs ?? []) as { id: string; statement: string; source?: string; status: string }[];
  const held = beliefs.filter((b) => b.status === "active"), dropped = beliefs.filter((b) => b.status !== "active");
  const belief = (b: (typeof beliefs)[number]) => el("li", "", el("div", "", b.statement), el("span", "tag", b.source ?? "lived"));
  const journal = ((d.journal ?? []) as Record<string, any>[]).filter((r) => r.type === "step" || r.type === "intention").slice(-14).reverse();
  const diary = [...((d.diary ?? []) as Record<string, any>[])].reverse();
  const known = (d.known ?? []) as { name: string; relation: string | null; line: string }[];
  const own = (d.message ?? []) as { text: string }[];
  return [
    head, needs,
    senses.length ? section("What it notices", list("plain", senses.map((s) => el("li", "", s)), "")) : null,
    now, project, read, sings, toldBy,
    section("What others told it", ...tells.map((t) => el("div", "", el("p", "hint", t.who), quote(t.text)))),
    own.length ? section("Its message for its children", quote(own.at(-1)!.text), own.length > 1 ? el("p", "hint", `Rewritten ${plural(own.length - 1, "time")}.`) : null) : null,
    section(`Beliefs (${held.length})`, list("beliefs", held.map(belief), d.beliefs ? "None yet." : "…"),
      dropped.length ? fold("dropped", `Given up (${dropped.length})`, el("ul", "beliefs gone", ...dropped.map(belief))) : null),
    section("Just now", list("journal", journal.map((r) => r.type === "intention"
      ? el("li", "plan", el("span", "", r.intention), el("span", r.score, r.ended === "done" ? MARK[r.score]?.slice(0, 1) : "–"))
      : el("li", r.reason ? "rejected" : "", el("span", "", r.feedback || r.reason), el("span", "hint", r.reason ? "could not" : ""))), "Nothing yet.")),
    section("Dreams", ...(diary.length ? diary.map((n) => el("div", "night",
      el("p", "hint", `Night of day ${n.day}`), el("p", "", n.dream || "No dream it could tell."),
      n.body ? el("p", "hint", `Its body changed: ${n.body}. ${n.reason ? `“${n.reason}”` : ""}`) : null,
      n.review ? el("p", "hint", `Looked again at “${n.review.was}”: ${n.review.decision === "revise" ? `now “${n.review.now}”` : n.review.decision === "discard" ? "gave it up" : "kept it"}.`) : null,
      ...(n.changes ?? []).map((ch: string) => el("p", "hint", ch)))) : [el("p", "empty", "It has not slept yet.")])),
    section("Who and where it knows",
      known.length ? list("plain", known.map((k) => el("li", "", el("b", "", k.name), k.relation ? ` (its ${k.relation})` : "", k.line ? `: ${k.line}` : "")), "") : null,
      d.rooms ? el("p", "hint", `Rooms: ${(d.rooms as string[]).join(", ") || "none yet"}.`) : null,
      d.met && Object.keys(d.met).length ? el("p", "hint", `Creatures met: ${Object.entries(d.met as Record<string, number>).map(([k, n]) => `${k} (${n})`).join(", ")}.`) : null),
    d.portraits?.length ? section("How it draws itself", el("div", "row", ...(d.portraits as { day: number; parts: [] }[]).map((s) => el("figure", "", thingPicture(s), el("figcaption", "hint", `day ${s.day}`))))) : null,
    section("Temperament", el("p", "hint", "What it was born with. It is never told; it only shows in how it feels and acts."), radial(p.temper, 130)),
    d.packet ? fold("packet", "The page it was last shown", el("p", "hint", "Everything it knew when it last thought, word for word. No numbers reach it."), el("pre", "packet", d.packet)) : null,
    link("Its place in the family", () => c.show("family", p.id)),
  ];
}

// ---- Things: what has been made, here and through the house ----

export function thingCard(c: Ctx, name: string, m: Pick<Made, "recipe" | "uses"> & Partial<Made>, extra: Kid[] = []) {
  const names = (ids: string[]) => ids.map((id) => c.snap.pets.find((p) => p.id === id)?.label ?? "someone gone").join(" → ");
  const maker = c.snap.pets.find((p) => p.id === m.by)?.label;
  const whose = m.owner_name ? `${m.owner_name}'s` : m.owner === "visitor" ? "a gift from the visitor" : null;
  const b = m.behavior;
  return el("li", "thing", thingPicture(m.recipe),
    el("div", "", el("b", "", m.called ? `${m.called} ` : name), m.called ? el("span", "hint", `(${name}) `) : null,
      m.useful ? el("span", "badge", "useful") : null, m.heirloom ? el("span", "badge gold", "heirloom") : null),
    el("div", "hint", [whose, maker && maker !== m.owner_name ? `made by ${maker}` : null, plural(m.uses, "use")].filter(Boolean).join(" · ")),
    m.recipe.purpose ? el("div", "", `“${m.recipe.purpose}”`) : null,
    el("div", "truth", `${m.recipe.material}: ${c.hello?.properties[m.recipe.material] ?? "nobody knows yet"}.`),
    b ? el("div", "truth", `Taught: when ${b.when.replace("_", " ")}, ${b.do.replace(/_/g, " ").replace(":", " to ")}.`) : null,
    m.worn?.length ? el("div", "truth", `It is ${m.worn.join(" and ").replace("eaten", "moth-eaten")}.`) : null,
    m.heirloom ? el("div", "truth", `Handed down: ${names(m.heirloom.line)} → ${names(m.heirloom.to) || "nobody living"}.`) : null,
    ...extra);
}

function things(c: Ctx): Kid[] {
  const rooms = c.snap.rooms.filter((r) => r.type);
  const made = (id: string) => Object.entries(rooms.find((r) => r.id === id)?.objects ?? {}).filter(([, o]) => o.made);
  const here = made(c.room), there = rooms.filter((r) => r.id !== c.room && made(r.id).length);
  const gone = (c.api.things?.gone ?? []) as { name: string; recipe: Made["recipe"]; by: string; uses: number; gone: [number, string] }[];
  const name = rooms.find((r) => r.id === c.room)?.name ?? "this room";
  return [
    el("p", "hint", "What the pets have made, with the name and purpose they gave. The grey line under each is for you, not for them: what the stuff it is made of really does."),
    el("h3", "", `In ${name} (${here.length})`),
    list("shelf", here.map(([n, o]) => thingCard(c, n, o.made!)), "Nothing made is in this room."),
    ...there.flatMap((r) => [
      el("h3", "", `In ${r.name} (${made(r.id).length}) `, link("look", () => c.jump({ room: r.id }))),
      el("ul", "shelf", ...made(r.id).map(([n, o]) => thingCard(c, n, o.made!)))]),
    gone.length ? fold("gone", `Gone (${gone.length})`, el("ul", "shelf gone", ...gone.map((g) =>
      thingCard(c, g.name, { recipe: g.recipe, uses: g.uses, by: g.by }, [el("div", "truth", `${g.gone[1]}, day ${dayOf(c.snap, g.gone[0])}.`)])))) : null,
  ];
}
