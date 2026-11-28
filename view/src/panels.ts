// The Lab (SPEC-v3.2 §6): one pet's mind is here, the whole house's numbers in story.ts. (SPEC-v4.0.5 §7.10: the
// drawer's Family, Story and Things tabs are gone; each has its own page.)
// The numbers shown in the Lab are for the visitor. No pet ever sees them.
import { bar, dayOf, el, face, fold, link, plural, radial, refill, when, whole } from "./dom";
import type { Ctx, Kid } from "./dom";
import { record } from "./family";
import { hasSprite, sprite } from "./sprite";
import { lab } from "./story";
import { thingPicture } from "./things";
import { NEEDS } from "./types";

const MARK: Record<string, string> = { correct: "✓ as it expected", wrong: "✗ not as it expected", unscorable: "no way to tell" };
const recall = (key: string, or: string) => { try { return localStorage.getItem(key) ?? or; } catch { return or; } };
const remember = (key: string, v: string) => { try { localStorage.setItem(key, v); } catch { /* not remembered */ } };
let labView = recall("lab", "mind");       // the Lab opens on one pet's mind, or on the whole house's numbers
/** The Lab, turned to one pet's mind: what a pet's card opens. */
export const showMind = () => { labView = "mind"; remember("lab", labView); };

/** Where the Lab's facts come from, by the name they are kept under. Asked for only while it is open. */
export function sources(c: Ctx): Record<string, string | null> {
  return labView === "mind" ? { mind: c.sel ? `/api/pet/${c.sel}` : null } : { lab: "/api/lab", v31: "/api/v31" };   // v31: the Walls and the Songbook, under "The house"
}

export function renderLab(c: Ctx) {
  const panel = document.querySelector<HTMLElement>('[data-panel="lab"]');
  if (!panel) return;
  const note = c.replay ? el("p", "hint note", "This is a replay. What is in the engine's memory here is as the house is now, not as it was then.") : null;
  refill(panel, [note, ...labTab(c)]);
}

const quote = (text: string, cls = "") => el("blockquote", cls, text);
const section = (title: string, ...kids: Kid[]) => (kids.some((k) => k) ? el("section", "", el("h3", "", title), ...kids) : null);
const list = (cls: string, items: Kid[], none: string) => el("ul", cls, ...(items.length ? items : [el("li", "empty", none)]));
/** Two or three choices side by side, one of them pressed. */
function choice(label: string, now: string, options: [string, string][], pick: (v: string) => void) {
  const box = el("div", "choice", ...options.map(([v, text]) => {
    const b = link(text, () => pick(v), "");
    b.setAttribute("aria-pressed", String(v === now));
    return b;
  }));
  box.setAttribute("role", "group");
  box.setAttribute("aria-label", label);
  return box;
}

function clock(sec: number) {
  return `${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, "0")}`;
}

// ---- Lab: one pet's mind, or the whole house's numbers ----

function labTab(c: Ctx): Kid[] {
  const pick = choice("What the Lab shows", labView, [["mind", "One hob's mind"], ["house", "The whole house"]], (v) => { labView = v; remember("lab", v); c.redraw(); });
  if (labView !== "mind") return [pick, ...lab(c)];
  const who = el("select", "") as HTMLSelectElement, pets = c.snap.pets.filter((p) => !(p.stage === "dead" && p.buried) || p.id === c.sel);
  who.setAttribute("aria-label", "Whose mind");
  who.append(...pets.map((p) => new Option(p.stage === "egg" ? `${p.name ?? "an egg"} (egg)` : p.stage === "dead" ? `${p.label} (gone)` : p.label, p.id, false, p.id === c.sel)));
  who.onchange = () => c.show("mind", who.value);
  return [el("div", "labhead", pick, pets.length > 1 ? who : null), ...mind(c)];
}

function mind(c: Ctx): Kid[] {
  const p = c.snap.pets.find((p) => p.id === c.sel);
  if (!p) return [el("p", "empty", "Nobody is chosen. Click a hob in the room or on a card.")];
  const d = c.api.mind?.pet?.id === p.id ? c.api.mind : {};
  const where = c.snap.rooms.find((r) => r.id === p.room)?.name ?? "the house";
  const parent = c.snap.pets.find((q) => q.id === p.parent);
  const stage = p.stage === "dead" ? `died of ${p.cause}` : p.stage;
  const head = el("div", "who", face(p, 96),
    el("div", "", el("h2", "", p.stage === "egg" ? p.name ?? "An egg" : p.label),
      el("p", "hint", `${stage} · generation ${p.gen}${p.days != null ? ` · ${plural(Math.round(p.days * 10) / 10, "day")}` : ""}`),
      el("p", "hint", `in ${where}${parent ? ` · ${parent.label}'s child` : ""}${c.snap.pets.some((q) => (q.family ?? 1) !== (p.family ?? 1)) ? ` · of the ${p.family === 2 ? "second" : "first"} family` : ""}`),
      p.seems ? el("p", "", `Seems ${p.seems}${p.body ? "" : `; ${p.asleep ? "asleep" : p.doing}`}.`) : null,   // what its body is at has the next line to itself
      // SPEC-v3.3 §1: what its body is at by itself just now (with the sign it wears in the room), and what its mind wants to be about
      p.body ? el("p", "", p.body.icon && hasSprite(`icon.act.${p.body.icon}`) ? sprite(`icon.act.${p.body.icon}`, 1) : null,
        `Its body, by itself: ${p.body.doing}${p.body.walking ? " (on its way there)" : ""}.`) : null,
      p.focus && !p.asleep ? el("p", "", "Its mind is on: ", el("q", "", p.focus.words),
        el("span", "hint", ` (${[p.focus.type, c.snap.pets.find((q) => q.id === p.focus!.who)?.label ?? p.focus.who ?? p.focus.what].filter(Boolean).join(": ")})`)) : null,
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
  // SPEC-v3.4 §2, §3.3: what it wants and how practised it feels, as its own mind is told them, and what it has found out
  const plain = (items: string[]) => (items.length ? list("plain", items.map((x) => el("li", "", x)), "") : null);
  const wants = section("What it wants", plain((p.wants ?? []).map((w) => w.text)));
  const knows = section("What it can do", p.skills ? el("p", "", `How practised it feels: “${p.skills}”`) : null,
    p.recipes?.length ? el("p", "hint", "It has found out:") : null, plain(p.recipes ?? []));
  const beliefs = (d.beliefs ?? []) as { id: string; statement: string; source?: string; status: string; hook_words?: string; acted?: number | null; doubted?: boolean }[];
  const held = beliefs.filter((b) => b.status === "active"), dropped = beliefs.filter((b) => b.status !== "active");
  const belief = (b: (typeof beliefs)[number]) => el("li", "", el("div", "", b.statement), el("span", "tag", b.source ?? "lived"),
    b.hook_words ? el("span", "tag", `${b.hook_words}${b.acted != null ? ", acted on" : ""}${b.doubted ? ", not sure of it" : ""}`) : null);   // SPEC-v4.2 §5.1: its hook, in words
  const journal = ((d.journal ?? []) as Record<string, any>[]).filter((r) => r.type === "step" || r.type === "intention").slice(-14).reverse();
  const diary = [...((d.diary ?? []) as Record<string, any>[])].reverse();
  const known = (d.known ?? []) as { name: string; relation: string | null; line: string }[];
  const own = (d.message ?? []) as { text: string }[];
  return [
    head, needs,
    senses.length ? section("What it notices", list("plain", senses.map((s) => el("li", "", s)), "")) : null,
    now, wants, project, knows,
    p.habits ? section("Habits", p.habits.length ? list("plain", p.habits.map((h) => el("li", "", h)), "")
      : el("p", "empty", "None yet. A habit is something it has done again and again, in the same place at the same time of day.")) : null,
    read, sings, toldBy,
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
