// The Story tab (SPEC-v3 §10.5) and the Lab tab (§11.4): what happened, and what it measured out to.
import { about, dayOf, el, fold, GENES, plural, when, whole } from "./dom";
import type { Ctx, Kid } from "./dom";
import { record } from "./family";
import { icon, svg } from "./icons";
import { hhmm, tickMs } from "./types";
import type { Chronicle, Heard, Moment, V31 } from "./types";

/** One moment (§9.1): a small picture, when, and what; a click goes to who and where it was. */
export function momentRow(c: Pick<Ctx, "jump">, m: Moment, day = false) {
  const b = el("button", "moment", icon(m.kind), el("span", "t", day ? `day ${m.day}, ${hhmm(m.hour)}` : hhmm(m.hour)), el("span", "", whole(m.text))) as HTMLButtonElement;
  b.type = "button";
  b.onclick = () => c.jump({ pet: m.pet, room: m.room });
  return el("li", "", b);
}

/** What the box said (SPEC-v3.1 §5.3), set out like the moments it sits beside. Nothing to say was static. */
const heardRow = (c: Ctx, h: Heard) => el("li", "", el("div", "moment", icon("radio"), el("span", "t", when(c.snap, h.tick).split(", ")[1]),
  h.text ? el("span", "", `“${h.text}” `, el("span", "hint", h.source)) : el("span", "hint", "only static")));

const FOUND: Record<string, string> = { writing: "Writing", songs: "Songs", taming: "Taming", radio: "The radio", book: "The book", strangers: "Strangers" };
/** The six discoveries (SPEC-v3.1 §1): which have come, and roughly how long until each of the rest, in real time. */
function discoveries(c: Ctx, v: V31) {
  const all = Object.entries(v.arrivals ?? {}).filter(([n]) => FOUND[n]), s = c.snap;
  if (!all.length) return null;
  const wait = (n: string, due: number) => {
    const left = due - s.tick, third = n === "strangers" ? ", and not before the family's third generation" : "";
    if (left <= 0) return `any time now${s.pets.some((p) => p.needs && !p.asleep) ? "" : ", once someone is awake to meet it"}${third}`;
    return `in ${s.turbo && v.ticks_per_day ? plural(Math.max(1, Math.round(left / v.ticks_per_day)), "day") + " of the house" : about((left * tickMs(s)) / 1000)}${third}`;
  };
  const next = all.find(([, a]) => a.arrived == null), come = all.filter(([, a]) => a.arrived != null).length;
  const list = el("ul", "arrivals", ...all.map(([n, a]) => el("li", a.arrived == null ? "" : "come", icon(`arrival ${n}`), el("b", "", FOUND[n]),
    el("span", "hint", a.arrived == null ? wait(n, a.due) : `came on ${when(s, a.arrived)}`))));
  // while something is still to come the list is in plain sight; once all six are here it folds away
  return next ? el("section", "", el("h3", "", `Discoveries (${come} of ${all.length} have come)`), list) : fold("discoveries", `Discoveries: all ${all.length} have come`, list);
}

export function story(c: Ctx): Kid[] {
  const d = c.replay ? null : c.api.story, today = c.snap.clock.day;
  const moments = (d?.moments ?? [...c.snap.moments].reverse()) as Moment[];
  const chron = (d?.chronicle ?? [...c.snap.chronicle].reverse()) as Chronicle[];
  // a day as it was written up; where nobody wrote it up, what happened as a short list, never one long run of semicolons
  const told = (e: Chronicle) => (e.text ? el("p", "", e.text) : e.lines.length ? el("ul", "dayline", ...e.lines.map((l) => el("li", "", `${l[0].toUpperCase()}${l.slice(1)}.`))) : el("p", "", "A quiet day."));
  const v = (c.api.v31 ?? {}) as V31, lib = v.library ?? [];
  const days = [...new Set([...moments.map((m) => m.day), ...(v.radio ?? []).map((h) => dayOf(c.snap, h.tick))])].filter((n) => n !== today).sort((a, b) => b - a);
  const latest = chron[0], records = (c.api.story?.records ?? []) as Record<string, any>[];
  const now = moments.filter((m) => m.day === today);
  const box = (n: number) => (v.radio ?? []).filter((h) => dayOf(c.snap, h.tick) === n), boxToday = box(today);   // newest first, like the moments
  const read = (b: (typeof lib)[number]) => el("li", "", el("p", "", el("b", "", b.name), ` asked the book: “${b.question}” `, el("span", "hint", when(c.snap, b.tick))),
    b.text ? el("blockquote", "", el("b", "", `${b.title}. `), b.text) : el("p", "hint", "The book had nothing to say to that."));
  return [
    latest ? el("section", "chronicle", el("h3", "", `Day ${latest.day}, ${latest.season}`), told(latest))
      : el("p", "empty", "The first day is not over yet; the chronicle is written each night."),
    discoveries(c, v),
    el("h3", "", `Today, day ${today}`),
    el("ol", "moments", ...(now.length ? now.map((m) => momentRow(c, m)) : [el("li", "empty", "Nothing worth the name yet today.")])),
    // what the box said that day, beside what the pets did (SPEC-v3.1 §5.3)
    boxToday.length ? el("h4", "", `What the box said today (${boxToday.length})`) : null,
    boxToday.length ? el("ol", "moments", ...boxToday.slice(0, 4).map((h) => heardRow(c, h))) : null,
    boxToday.length > 4 ? fold("box-today", `${boxToday.length - 4} earlier today`, el("ol", "moments", ...boxToday.slice(4).map((h) => heardRow(c, h)))) : null,
    days.length ? el("h3", "", "Earlier") : null,
    ...days.map((n) => {
      const e = chron.find((x) => x.day === n), list = moments.filter((m) => m.day === n), said = box(n);
      return fold(`day-${n}`, `Day ${n}${e ? `, ${e.season}` : ""} · ${plural(list.length, "moment")}${said.length ? ` · the box spoke ${said.length === 1 ? "once" : `${said.length} times`}` : ""}`,
        e && e !== latest ? told(e) : null, el("ol", "moments", ...list.map((m) => momentRow(c, m))),
        said.length ? el("h4", "", "What the box said that day") : null, said.length ? el("ol", "moments", ...said.map((h) => heardRow(c, h))) : null);
    }),
    // SPEC-v3.1 §6.3: every question put to the book, by whom, and what it answered
    el("h3", "", `Library (${lib.length})`),
    lib.length ? el("ul", "sayings", ...lib.slice(0, 4).map(read)) : el("p", "empty", c.snap.arrived?.book == null ? "There is no book in the house yet." : "Nobody has asked the book anything yet."),
    lib.length > 4 ? fold("library", `${lib.length - 4} earlier questions`, el("ul", "sayings", ...lib.slice(4).map(read))) : null,
    records.length ? el("h3", "", "Lives that are over") : null,
    ...records.map((r) => fold(`life-${r.id}`, `${r.name}, generation ${r.gen}: ${r.days} days, ${r.cause}`, ...record(c, r))),
  ];
}

// ---- Lab ----

const pct = (v: number | null | undefined) => (v == null ? "–" : `${v}%`);
const pairs = (o: Record<string, number> | undefined) => Object.entries(o ?? {}).map(([k, n]) => `${k} ${n}`).join(", ") || "none";

/** A share as a bar on a 0–60% scale, with the bar it has to stay under and the last v2 life's figure marked on it. */
function meter(value: number | null, v25: number) {
  const scale = 60, m = el("div", "meter"), fill = el("b", value != null && value >= 10 ? "over" : "");
  fill.style.width = `${Math.min(100, ((value ?? 0) / scale) * 100)}%`;
  const mark = (v: number, cls: string, title: string) => {
    const i = el("i", cls);
    i.style.left = `${(v / scale) * 100}%`;
    i.title = title;
    return i;
  };
  m.append(fill, mark(10, "goal", "the bar: under 10%"), mark(v25, "old", `v2.5: ${v25}%`));
  return m;
}

/** Each temperament gene over the generations (§12.2): a dot a pet, a line through each generation's middle. */
function drift(pets: { gen: number; temper: Record<string, number> }[]) {
  const gens = [...new Set(pets.map((p) => p.gen))].sort((a, b) => a - b);
  const [L, W, RH] = [70, 300, 30], x = (g: number) => L + 14 + (gens.length > 1 ? (gens.indexOf(g) / (gens.length - 1)) * (W - 28) : (W - 28) / 2);
  const out = svg("svg", { viewBox: `0 0 ${L + W} ${GENES.length * RH + 18}`, class: "drift", role: "img", "aria-label": "Temperament by generation" });
  GENES.forEach((gene, i) => {
    const y = (v: number) => i * RH + RH - 5 - v * (RH - 10);
    out.append(svg("text", { x: L - 8, y: i * RH + RH / 2 + 4, "text-anchor": "end" }, gene), svg("line", { x1: L, x2: L + W, y1: y(0.5), y2: y(0.5), class: "ring" }));
    const means = gens.map((g) => {
      const vs = pets.filter((p) => p.gen === g).map((p) => p.temper[gene] ?? 0);
      return `${x(g).toFixed(1)},${y(vs.reduce((a, b) => a + b, 0) / vs.length).toFixed(1)}`;
    });
    out.append(svg("polyline", { points: means.join(" "), class: "shape" }));
    for (const p of pets) out.append(svg("circle", { cx: x(p.gen), cy: y(p.temper[gene] ?? 0), r: 2.6, class: "dot" }));
  });
  for (const g of gens) out.append(svg("text", { x: x(g), y: GENES.length * RH + 13, "text-anchor": "middle" }, `gen ${g}`));
  return out;
}

export function lab(c: Ctx): Kid[] {
  const d = c.api.lab;
  if (!d) return [el("p", "empty", "Asking the engine for its numbers…")];
  const pets = d.pets as Record<string, any>[], v25 = d.v25 as { meter_thoughts: number; meter_beliefs: number };
  const name = (id: string | null) => c.snap.pets.find((p) => p.id === id)?.label ?? (id ? "someone gone" : "nobody");
  const rows: [string, (p: Record<string, any>) => string][] = [
    ["Generation, stage", (p) => `${p.gen}, ${p.stage}`], ["Days lived", (p) => String(p.days)], ["Died of", (p) => p.cause ?? "–"],
    ["Wellbeing, of 100", (p) => String(p.wellbeing ?? "–")],
    ["Thoughts, steps", (p) => `${p.intentions}, ${p.steps}`], ["Steps that were not possible", (p) => pct(p.not_possible)],
    ["Expectations that came true", (p) => (p.scorable ? `${pct(p.predictions_right)} of ${p.scorable}` : "–")],
    ["…about the hidden physics", (p) => (p.rule_scored ? `${pct(p.rule_right)} of ${p.rule_scored}` : "–")],
    ["Model calls, per hour", (p) => `${p.calls}, ${p.calls_per_hour}`], ["Calls in the last hour", (p) => String(p.calls_last_hour)],
    ["Seconds a call, median", (p) => String(p.call_seconds ?? "–")], ["Calls that failed", (p) => String(p.failed)],
    ["Made, of them useful", (p) => `${p.made}, ${p.useful}`], ["Rooms it has been in", (p) => String(p.rooms.length)],
    ["Creatures", (p) => pairs(p.creatures)], ["To other pets", (p) => pairs(p.social)], ["Replies it got", (p) => String(p.replies)],
    ["Time with a need at the bottom", (p) => Object.entries(p.low as Record<string, number | null>).filter(([, v]) => v).map(([k, v]) => `${k} ${v}%`).join(", ") || "none"],
    ["What it does most", (p) => Object.entries(p.actions as Record<string, number>).slice(0, 5).map(([k, n]) => `${k} ${n}`).join(", ")],
    ["Why it thought", (p) => pairs(p.why)],
  ];
  // one block a pet, its headline numbers always in sight and the rest a click away: however many pets, nothing is off to the side
  const each = pets.map((p) => fold(`lab-${p.id ?? p.name}`, el("span", "", el("b", "", p.name), ` · generation ${p.gen}, ${p.stage} · ${p.days} days · wellbeing ${p.wellbeing ?? "–"} · ${p.intentions} thoughts`),
    el("dl", "facts", ...rows.flatMap(([label, cell]) => [el("dt", "", label), el("dd", "", cell(p))]))));
  const claims = d.claims as { text: string; first: string; pets: string[]; gens: number[]; forms: [string, string][]; truth: string | null }[];
  return [
    el("h3", "", "Does it read like a creature?"),
    el("p", "hint", `Share of each pet's thoughts that talk mechanics (numbers, costs, "efficient"), after its first day. The bar to clear is 10%; the last v2 life was at ${v25.meter_thoughts}%, and ${v25.meter_beliefs}% of its beliefs.`),
    el("div", "meters", ...pets.flatMap((p) => [el("span", "", p.name), meter(p.meter_after_day1 ?? p.meter_all, v25.meter_thoughts),
      el("span", "num", `${pct(p.meter_after_day1 ?? p.meter_all)} · beliefs ${pct(p.meter_beliefs)}`)]),
      el("span", "hint", "v2.5"), meter(v25.meter_thoughts, v25.meter_thoughts), el("span", "num hint", `${v25.meter_thoughts}% · beliefs ${v25.meter_beliefs}%`)),
    el("h3", "", "Model calls"),
    el("div", "meters", el("span", "", "last hour"), (() => { const m = el("div", "meter"), f = el("b", d.calls_last_hour > d.budget ? "over" : ""); f.style.width = `${Math.min(100, (d.calls_last_hour / d.budget) * 100)}%`; m.append(f); return m; })(),
      el("span", "num", `${d.calls_last_hour} of ${d.budget}`)),
    el("p", "hint", `By kind, over the whole family: ${pairs(d.calls_by_kind)}.`),
    el("h3", "", "Each pet"),
    el("p", "hint", "Click a pet for all its numbers."),
    el("div", "each", ...each),
    el("h3", "", "Temperament over the generations"),
    drift(d.temper),
    el("h3", "", `What they have claimed (${claims.length})`),
    el("p", "hint", `Every sentence of a message or belief, tied to earlier ones like it: ${pairs(d.claim_rows)}.`),
    el("ul", "sayings", ...claims.slice(0, 12).map((s) => el("li", "", el("div", "", `“${s.text}”`),
      el("p", "hint", `${[...new Set(s.pets)].map(name).join(" → ")} · ${s.gens.length ? plural(s.gens.length, "generation") : "not passed on"} · ${s.truth ?? "unchecked"}${s.forms.length ? ` · reworded ${s.forms.length}×` : ""}`)))),
    claims.length > 12 ? fold("claims", `${claims.length - 12} more`, el("ul", "sayings", ...claims.slice(12).map((s) => el("li", "", `“${s.text}” `, el("span", "hint", `${plural(s.pets.length, "pet")}, ${s.truth ?? "unchecked"}`))))) : null,
    el("h3", "", "The house"),
    el("ul", "plain", ...(d.rooms as { type: string; tick: number; by: string | null }[]).map((r) =>
      el("li", "", icon(r.type), ` ${c.hello?.rooms[r.type]?.name ?? r.type} `, el("span", "hint", r.by ? `found by ${name(r.by)}` : "where the family began")))),
    el("p", "hint", `Things that happened on their own: ${pairs(d.events)}.`),
    d.drift ? el("p", "hint", `One rule has drifted: ${d.drift.type}, ${JSON.stringify(d.drift.rule).replace(/[{}"]/g, "")}. The pets were not told.`) : el("p", "hint", "No rule has drifted yet in this family."),
    (d.deaths as { name: string; cause: string; days: number | null }[]).length
      ? el("p", "hint", `Deaths: ${(d.deaths as { name: string; cause: string; days: number | null }[]).map((x) => `${x.name} (${x.cause}${x.days != null ? `, ${x.days} days` : ""})`).join("; ")}.`) : null,
    c.voiceLab,
  ];
}
