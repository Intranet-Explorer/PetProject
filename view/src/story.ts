// The Lab tab (§11.4): what the house measured out to. (SPEC-v4.0.5 §7.10: the drawer's Story tab that was here is
// gone; the Story page is pages/story.ts.)
import { about, el, fold, GENES, plural } from "./dom";
import type { Ctx, Kid } from "./dom";
import { songbook, walls } from "./family";
import { icon, svg } from "./icons";
import type { V31 } from "./types";
import { grammarRows } from "./invent";
import type { Grammar5 } from "./invent";

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
    const y = (v: number) => i * RH + RH - 5 - v * (RH - 10), has = pets.filter((p) => gene in p.temper);   // a pet from before a gene was added (orderly, SPEC-v3.3) is left out of its row
    out.append(svg("text", { x: L - 8, y: i * RH + RH / 2 + 4, "text-anchor": "end" }, gene), svg("line", { x1: L, x2: L + W, y1: y(0.5), y2: y(0.5), class: "ring" }));
    const means = gens.map((g) => {
      const vs = has.filter((p) => p.gen === g).map((p) => p.temper[gene]);
      return vs.length ? `${x(g).toFixed(1)},${y(vs.reduce((a, b) => a + b, 0) / vs.length).toFixed(1)}` : "";
    });
    out.append(svg("polyline", { points: means.join(" "), class: "shape" }));
    for (const p of has) out.append(svg("circle", { cx: x(p.gen), cy: y(p.temper[gene]), r: 2.6, class: "dot" }));
  });
  for (const g of gens) out.append(svg("text", { x: x(g), y: GENES.length * RH + 13, "text-anchor": "middle" }, `gen ${g}`));
  return out;
}

// SPEC-v4.0.5 §8: "Today" (engine/lab4.py), what to read the morning after: each hob's needs, memories, aims, thoughts
// and talks, and the house's save, model and websocket, each beside yesterday's. A dash: not known (yet).
type Hob4 = { id: string; name: string; needs: Record<string, number | null>; memories: Record<string, number> | null; aims: { done: number; failed: number; open: number; failed_text: string[] };
  thoughts: Record<string, { n: number; seconds: number; wait: number | null; compute: number }>; talks: number; talks_failed: number | null; invalid_json: number | null; cut_off: number | null };
type Day4 = { day: number; pets: Hob4[]; house: Record<string, number | null> };
const n4 = (v: number | null | undefined, unit = "") => (v == null ? "–" : `${v}${unit}`);
const share = (v: number | null | undefined) => (v == null ? "–" : `${Math.round(v * 1000) / 10}%`);
function today(t: Day4 & { yesterday: Day4 }): Kid[] {
  const y = (id: string) => t.yesterday.pets.find((p) => p.id === id);
  const both = (now: string, was: string | null) => (was == null ? now : `${now} (yesterday ${was})`);
  const mem = (m: Hob4["memories"]) => (m ? `${m["1-3"]} / ${m["4"]} / ${m["5"]}` : "–");
  const aims = (a: Hob4["aims"]) => `${a.done} / ${a.failed} / ${a.open}`;
  const thought = (h: Hob4) => Object.entries(h.thoughts).map(([k, x]) => `${k} ${x.n}: ${x.seconds} s (waited ${n4(x.wait)}, computed ${x.compute})`).join("; ") || "none";
  const hob = (h: Hob4) => {
    const w = y(h.id), rows: [string, string][] = [
      ...(["pride", "hunger", "safety"].map((k) => [k[0].toUpperCase() + k.slice(1), both(n4(h.needs[k]), w ? n4(w.needs[k]) : null)]) as [string, string][]),
      ["Memories by weight, 1–3 / 4 / 5", both(mem(h.memories), w ? mem(w.memories) : null)],
      ["Aims done / failed / open", both(aims(h.aims), w ? aims(w.aims) : null)],
      ["Thoughts by kind", thought(h)], ...(w ? [["… yesterday", thought(w)] as [string, string]] : []),
      ["Talks, failed", both(`${h.talks}, ${n4(h.talks_failed)}`, w ? `${w.talks}, ${n4(w.talks_failed)}` : null)],
      ["Replies not JSON, cut off", both(`${n4(h.invalid_json)}, ${n4(h.cut_off)}`, w ? `${n4(w.invalid_json)}, ${n4(w.cut_off)}` : null)],
    ];
    return fold(`today-${h.id}`, el("span", "", el("b", "", h.name), ` · pride ${n4(h.needs.pride)}, hunger ${n4(h.needs.hunger)}, safety ${n4(h.needs.safety)} · aims ${aims(h.aims)}`),
      el("dl", "facts", ...rows.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", v)])),
      h.aims.failed_text.length ? el("ul", "plain", ...h.aims.failed_text.map((x) => el("li", "", `failed: “${x}”`))) : null);
  };
  const H = t.house, Y = t.yesterday.house;
  const house: [string, string][] = [
    ["Since the last good save", H.save_age == null ? "–" : about(H.save_age)],
    ["The model busy: last world hour, last real hour, today", `${share(H.busy_world_hour)}, ${share(H.busy_real_hour)}, ${share(H.busy_day)} (yesterday ${share(Y.busy_day)})`],
    ["Calls in the last hour", `${n4(H.calls_hour)} of ${n4(H.budget)}`],
    ["Eggs laid, found (this family)", `${n4(H.eggs_laid)}, ${n4(H.eggs_found)}`],
    ["Founder eggs re-parented", n4(H.reparented)],
    ["Talks that failed", `${n4(H.talks_failed)} (yesterday ${n4(Y.talks_failed)})`],
    ["Pages watching, last message", `${n4(H.ws_clients)}, ${H.ws_bytes == null ? "–" : `${Math.round(H.ws_bytes / 1024)} KB`}`],
  ];
  return [el("h3", "", `Today, day ${t.day}`),
    el("p", "hint", "Each hob's day so far, and the house's, with yesterday's beside it. A dash is a number the engine does not keep (yet)."),
    el("dl", "facts", ...house.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", v)])),
    el("div", "each", ...t.pets.map(hob))];
}

// SPEC-v4.2 §11.5: "Spirit" (engine/lab4.py spirit): whether any of v4.2 is working, per hob and for the house.
type HobS = { id: string; name: string; memories: { model: number; engine: number; heavy_model: number; heavy: number }; beliefs: { hooked: number; acted_today: number };
  talks: number; knows: number; wants_holds: number; thinking_seconds: number | null };
type Spirit = { day: number; pets: HobS[]; house: { deaths: Record<string, number>; happenings: { day: number; name: string; target: string | null }[];
  unwell: { name: string; sick: string | null; hurt: string | null }[]; tales: { kept: number; told_week: number }; theories: { name: string; theory: string }[];
  thinking_share: number | null; ledger: Record<string, { says?: string; today: number; week: number }>; missed_fields: Record<string, number> } };
function spirit(s: Spirit): Kid[] {
  const H = s.house, rows = (r: [string, string][]) => el("dl", "facts", ...r.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", v)]));
  const hob = (h: HobS) => fold(`spirit-${h.id}`, el("span", "", el("b", "", h.name), ` · memories ${h.memories.model} the model's, ${h.memories.engine} the engine's · talks ${h.talks}, knows ${h.knows}`),
    rows([["Memories: the model's / the engine's", `${h.memories.model} / ${h.memories.engine}`], ["… the heavy ones, the model's of all", `${h.memories.heavy_model} of ${h.memories.heavy}`],
      ["Beliefs with a hook, acted on today", `${h.beliefs.hooked}, ${h.beliefs.acted_today}`], ["Talks today; with knows, with wants and holds", `${h.talks}; ${h.knows}, ${h.wants_holds}`],
      ["Thinking today", n4(h.thinking_seconds, " s")]]));
  const deaths = Object.entries(H.deaths).filter(([, n]) => n).map(([k, n]) => `${k} ${n}`).join(", ") || "none";
  return [el("h3", "", `Spirit, day ${s.day}`),
    el("p", "hint", "Whether v4.2 is working: what the hobs remember and believe, what their talks leave, and the house's deaths, happenings and tales."),
    rows([["Deaths by cause, this family", deaths], ["Thinking's share of the model's time today", share(H.thinking_share)],
      ["Sick or hurt now", H.unwell.map((u) => `${u.name} (${[u.sick, u.hurt].filter(Boolean).join(", ")})`).join("; ") || "nobody"],
      ["This week's happenings", H.happenings.map((x) => `day ${x.day}: ${x.name}${x.target ? ` (${x.target})` : ""}`).join("; ") || "none"],
      ["Tales kept, told this week", `${H.tales.kept}, ${H.tales.told_week}`],
      ["Replies lacking a field, this week", pairs(H.missed_fields)],
      ...Object.entries(H.ledger).map(([k, v]) => [`${v.says ?? k}, today / this week`, `${v.today} / ${v.week}`] as [string, string])]),
    el("h3", "", "What each thinks the visitor is"),
    el("ul", "plain", ...H.theories.map((t) => el("li", "", el("b", "", t.name), `: ${t.theory || "no thought of him yet"}`))),
    el("div", "each", ...s.pets.map(hob))];
}

// SPEC-v5.0 §5: "Jobs" (engine/lab4.py jobs): whether the house's wrongs are seen to, by whom, and why things are made.
type Jobs5 = { day: number; deficits: { kind: string; says: string; open: number; opened: number; closed: number; taken: number }[];
  pets: { id: string; name: string; taken: number; idle: number; awake: number; idle_share: number | null; scrap: number; earned: number; spent: number }[];
  idle_share: number | null; made_for: Record<string, number>; economy: { earned: number; spent: number; held: number };
  broke: Record<string, number>; mended: Record<string, number>; verbs: Record<string, number>; board: { open: number; jobs: number; taken: number; closed: number } };
function jobs(j: Jobs5): Kid[] {
  const rows = (r: [string, string][]) => el("dl", "facts", ...r.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", v)]));
  const B = j.board, M = j.made_for, E = j.economy, used = Object.fromEntries(Object.entries(j.verbs).filter(([, n]) => n));
  return [el("h3", "", `Jobs, day ${j.day}`),
    el("p", "hint", "Whether v5 is working: what is wrong with the house and whether it is seen to, who idles while there is work it fits (under 10%), why things are made (for nothing should read 0), and the scrap."),
    rows([["On the board now", `${B.open} wrong, ${plural(B.jobs, "job")} (${B.taken} taken), ${B.closed} seen to today`],
      ["Idle while a job it fits was open", share(j.idle_share)],
      ["Made for a job / a plan / taught / nothing", `${M.job} / ${M.plan} / ${M.taught} / ${M.nothing}`],
      ["Scrap earned, spent, held", `${E.earned}, ${E.spent}, ${E.held}`],
      ["Broken; mended", `${pairs(j.broke)}; ${pairs(j.mended)}`], ["Verbs used", pairs(used)]]),
    el("h3", "", "What was wrong today, by kind"),
    el("p", "hint", "On the board now · opened today · closed today · jobs taken today."),
    rows(j.deficits.map((d) => [d.says, `${d.open} · ${d.opened} · ${d.closed} · ${d.taken}`])),
    el("h3", "", "Each hob's work"),
    rows(j.pets.map((p) => [p.name, `${plural(p.taken, "job")} taken · idle ${share(p.idle_share)}${p.awake ? ` (${p.idle} of ${p.awake} ticks awake)` : ""} · scrap ${p.scrap} (earned ${p.earned}, spent ${p.spent})`]))];
}

// SPEC-v5.1 §8: "Grammar" (engine/lab4.py grammar): whether hobs invent, what the parser says to them, what they know and read.
function grammar5(g: Grammar5): Kid[] {
  const R = grammarRows(g), rows = (r: [string, string][]) => el("dl", "facts", ...r.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", v)]));
  return [el("h3", "", `Grammar, the last ${plural(g.days, "day")}`),
    el("p", "hint", "Whether v5.1 is working: what the hobs try to make that nobody has, what the parser tells them when it can't be made, what they know how to make, and what they read."),
    rows(R.house), el("h3", "", "What the parser said, and how often"), R.refused.length ? rows(R.refused) : el("p", "hint", "Nothing refused yet."),
    el("h3", "", "What each hob knows"), rows(R.pets)];
}

// SPEC-v5.3 §8: "Life" (engine/lab4.py life): habits, marks, projects, talks that go on, idleness, and §6's scenes.
type Life53 = { day: number; days: number; habit: Record<string, number>; marks: Record<string, number>; noticed: Record<string, number>;
  pets: { id: string; name: string; habits: { name: string; count: number; fading: boolean }[]; steps_today: number; third: number; threads: number; idle53: number; idle_share: number | null }[];
  projects: Record<string, Record<string, number>>; changes: Record<string, number>; steps: number; orphans: number; taken_up: number;
  rounds: Record<string, number>; threads: { left: number; picked: number; open: number }; third: number; idle_share: number | null;
  scenes: { scene: string; says: string; n: number; last: string | null }[]; events: { event: string; says: string; n: number }[] };
function life53(l: Life53): Kid[] {
  const rows = (r: [string, string][]) => el("dl", "facts", ...r.flatMap(([k, v]) => [el("dt", "", k), el("dd", "", v)]));
  const nz = (o: Record<string, number>) => pairs(Object.fromEntries(Object.entries(o).filter(([, n]) => n)));
  const by = Object.entries(l.projects).filter(([, k]) => Object.keys(k).length).map(([st, k]) => `${st}: ${pairs(k)}`).join("; ") || "none";
  return [el("h3", "", `Life, the last ${plural(l.days, "day")}`),
    el("p", "hint", "Whether v5.3 is working: habits and the marks they leave, projects that take days, talks that go on, nobody sitting about, and the scenes of §6 coming about with nobody writing them."),
    rows([["Habits' goes, by habit", nz(l.habit)], ["Marks left; noticed", `${nz(l.marks)}; ${nz(l.noticed)}`],
      ["Projects now, by state", by], ["Project steps today", String(l.steps)], ["Orphans now; taken up", `${l.orphans}; ${l.taken_up}`],
      ["Talks of 1 / 2 / 3 rounds", `${l.rounds["1"]} / ${l.rounds["2"]} / ${l.rounds["3"]}`],
      ["Threads left / picked up / open now", `${l.threads.left} / ${l.threads.picked} / ${l.threads.open}`], ["A third hob's lines", String(l.third)],
      ["Idle, the reading hour out", share(l.idle_share)]]),
    el("h3", "", "The scenes (§6)"), rows(l.scenes.map((s) => [s.says, s.n ? `${s.n}: ${s.last}` : "not yet"])),
    el("h3", "", "Each hob's life"),
    rows(l.pets.map((p) => [p.name, `${p.habits.map((h) => `${h.name} ${h.fading ? "(fading)" : `×${h.count}`}`).join(", ") || "no habits"} · steps today ${p.steps_today} · threads ${p.threads} · lines as the third ${p.third} · idle ${share(p.idle_share)}`])),
    el("h3", "", "What was recorded"), rows(l.events.map((e) => [e.says, String(e.n)]))];
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
    ["Creatures", (p) => pairs(p.creatures)], ["To other hobs", (p) => pairs(p.social)], ["Replies it got", (p) => String(p.replies)],
    ["Time with a need at the bottom", (p) => Object.entries(p.low as Record<string, number | null>).filter(([, v]) => v).map(([k, v]) => `${k} ${v}%`).join(", ") || "none"],
    ["What it does most", (p) => Object.entries(p.actions as Record<string, number>).slice(0, 5).map(([k, n]) => `${k} ${n}`).join(", ")],
    ["Why it thought", (p) => pairs(p.why)],
  ];
  // one block a pet, its headline numbers always in sight and the rest a click away: however many pets, nothing is off to the side
  const each = pets.map((p) => fold(`lab-${p.id ?? p.name}`, el("span", "", el("b", "", p.name), ` · generation ${p.gen}, ${p.stage} · ${p.days} days · wellbeing ${p.wellbeing ?? "–"} · ${p.intentions} thoughts`),
    el("dl", "facts", ...rows.flatMap(([label, cell]) => [el("dt", "", label), el("dd", "", cell(p))]))));
  const claims = d.claims as { text: string; first: string; pets: string[]; gens: number[]; forms: [string, string][]; truth: string | null }[];
  return [
    ...(d.today ? today(d.today) : []),
    ...(d.spirit ? spirit(d.spirit as Spirit) : []),
    ...(d.jobs ? jobs(d.jobs as Jobs5) : []),   // SPEC-v5.0 §5: only while v5 is on
    ...(d.grammar ? grammar5(d.grammar as Grammar5) : []),   // SPEC-v5.1 §8: only while v5.1 is on
    ...(d.life ? life53(d.life as Life53) : []),   // SPEC-v5.3 §8: only while v5.3 is on
    el("h3", "", "Does it read like a creature?"),
    el("p", "hint", `Share of each hob's thoughts that talk mechanics (numbers, costs, "efficient"), after its first day. The bar to clear is 10%; the last v2 life was at ${v25.meter_thoughts}%, and ${v25.meter_beliefs}% of its beliefs.`),
    el("div", "meters", ...pets.flatMap((p) => [el("span", "", p.name), meter(p.meter_after_day1 ?? p.meter_all, v25.meter_thoughts),
      el("span", "num", `${pct(p.meter_after_day1 ?? p.meter_all)} · beliefs ${pct(p.meter_beliefs)}`)]),
      el("span", "hint", "v2.5"), meter(v25.meter_thoughts, v25.meter_thoughts), el("span", "num hint", `${v25.meter_thoughts}% · beliefs ${v25.meter_beliefs}%`)),
    el("h3", "", "Model calls"),
    el("div", "meters", el("span", "", "last hour"), (() => { const m = el("div", "meter"), f = el("b", d.calls_last_hour > d.budget ? "over" : ""); f.style.width = `${Math.min(100, (d.calls_last_hour / d.budget) * 100)}%`; m.append(f); return m; })(),
      el("span", "num", `${d.calls_last_hour} of ${d.budget}`)),
    el("p", "hint", `By kind, over the whole family: ${pairs(d.calls_by_kind)}.`),
    el("h3", "", "Each hob"),
    el("p", "hint", "Click a hob for all its numbers."),
    el("div", "each", ...each),
    el("h3", "", "Temperament over the generations"),
    drift(d.temper),
    el("h3", "", `What they have claimed (${claims.length})`),
    el("p", "hint", `Every sentence of a message or belief, tied to earlier ones like it: ${pairs(d.claim_rows)}.`),
    el("ul", "sayings", ...claims.slice(0, 12).map((s) => el("li", "", el("div", "", `“${s.text}”`),
      el("p", "hint", `${[...new Set(s.pets)].map(name).join(" → ")} · ${s.gens.length ? plural(s.gens.length, "generation") : "not passed on"} · ${s.truth ?? "unchecked"}${s.forms.length ? ` · reworded ${s.forms.length}×` : ""}`)))),
    claims.length > 12 ? fold("claims", `${claims.length - 12} more`, el("ul", "sayings", ...claims.slice(12).map((s) => el("li", "", `“${s.text}” `, el("span", "hint", `${plural(s.pets.length, "hob")}, ${s.truth ?? "unchecked"}`))))) : null,
    el("h3", "", "The rooms"),
    el("ul", "plain", ...(d.rooms as { type: string; tick: number; by: string | null }[]).map((r) =>
      el("li", "", icon(r.type), ` ${c.hello?.rooms[r.type]?.name ?? r.type} `, el("span", "hint", r.by ? `found by ${name(r.by)}` : "where the family began")))),
    el("p", "hint", `Things that happened on their own: ${pairs(d.events)}.`),
    d.drift ? el("p", "hint", `One rule has drifted: ${d.drift.type}, ${JSON.stringify(d.drift.rule).replace(/[{}"]/g, "")}. The hobs were not told.`) : el("p", "hint", "No rule has drifted yet in this family."),
    (d.deaths as { name: string; cause: string; days: number | null }[]).length
      ? el("p", "hint", `Deaths: ${(d.deaths as { name: string; cause: string; days: number | null }[]).map((x) => `${x.name} (${x.cause}${x.days != null ? `, ${x.days} days` : ""})`).join("; ")}.`) : null,
    // SPEC-v4.0.5 §7.10: the Walls and the Songbook (/api/v31), which had their screen in the drawer's Family tab
    el("h2", "", "The house"),
    ...songbook(c, ((c.api.v31 ?? {}) as V31).songs ?? []),
    ...walls(c, ((c.api.v31 ?? {}) as V31).walls ?? []),
    c.voiceLab,
  ];
}
