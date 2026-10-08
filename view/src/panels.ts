// The DOM around the room: the header, and the drawer's tabs (SPEC-v2 §9).
// Everything from the engine is set as text, never as HTML.
import type { Rec, Snapshot } from "./main";
import { thingPicture } from "./things";

const NEEDS = ["energy", "comfort", "curiosity"] as const;
const MARK = { correct: "✓ right", wrong: "✗ wrong", unscorable: "not scorable" };
const RULES: [string, string][] = [["lights_night", "Put out the lights for the night"], ["double_feed", "Spaced out its meals"], ["plant_window", "Plant to the window"]];
const LINE: Record<string, string> = { model: "--accent", twin: "--muted" };
const $ = (id: string) => document.getElementById(id)!;

function el(tag: string, cls = "", text = "") {
  const e = document.createElement(tag);
  e.className = cls;
  e.textContent = text;
  return e;
}

/** An action in a few words: "use lamp", "say “hello”", "move (3,4)". */
function actionText(a: unknown) {
  if (!a || typeof a !== "object") return "no action";
  const { type, target, object, tile, text, id } = a as Record<string, unknown>;
  if (type === "speak") return `say “${text}”`;
  if (type === "write_belief") return "write a belief";
  if (type === "revise_belief") return `revise ${id}`;
  return [type, target ?? object, Array.isArray(tile) ? `(${tile})` : null].filter((v) => v != null).join(" ");
}

/** Need changes of half a point or more; smaller ones are background drift. */
function deltas(r: Rec) {
  return NEEDS.filter((n) => Math.abs(r.deltas[n]) >= 0.5).map((n) =>
    el("span", r.deltas[n] > 0 ? "delta up" : "delta down", `${r.deltas[n] > 0 ? "+" : ""}${r.deltas[n].toFixed(1)} ${n}`));
}

const tags = (r: Rec) => r.rule_tags.map((t) => el("span", "tag", t));

function chart(snap: Snapshot) {
  const c = $("chart") as HTMLCanvasElement, g = c.getContext("2d")!;
  const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v);
  const [W, H, L, R, T, B] = [c.width, c.height, 52, 14, 16, 30];
  const all = Object.values(snap.pets).flatMap((p) => p.series);
  g.clearRect(0, 0, W, H);
  g.font = "19px system-ui, sans-serif";
  g.fillStyle = css("--muted");
  if (!all.length) {
    g.textAlign = "center";
    g.fillText("No hidden rule has been predicted yet", W / 2, H / 2);
    return;
  }
  const t0 = Math.min(...all.map((p) => p[0])), t1 = Math.max(t0 + 1, ...all.map((p) => p[0]));
  const x = (t: number) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v: number) => T + (1 - v / 100) * (H - T - B);
  g.textAlign = "right";
  for (const v of [0, 50, 100]) {
    g.fillText(`${v}%`, L - 8, y(v) + 6);
    g.strokeStyle = css("--line");
    g.beginPath(); g.moveTo(L, y(v)); g.lineTo(W - R, y(v)); g.stroke();
  }
  g.textAlign = "left";
  g.fillText(`tick ${t0}`, L, H - 6);
  g.textAlign = "right";
  g.fillText(`tick ${t1}`, W - R, H - 6);
  g.lineWidth = 3;
  g.textAlign = "left";
  Object.entries(snap.pets).forEach(([id, p], i) => {
    g.strokeStyle = g.fillStyle = css(LINE[id] ?? "--ink");
    if (Object.keys(snap.pets).length > 1) g.fillText(id, L + 10 + i * 80, T + 16);
    g.beginPath();
    p.series.forEach(([t, v], k) => (k ? g.lineTo(x(t), y(v)) : g.moveTo(x(t), y(v))));
    g.stroke();
  });
  g.lineWidth = 1;
}

function compare(snap: Snapshot) {
  const ids = Object.keys(snap.pets);
  const line = (label: string, cell: (id: string) => string) => {
    const tr = el("tr");
    tr.append(el("td", "", label), ...ids.map((id) => el("td", "", cell(id))));
    return tr;
  };
  const head = el("tr");
  head.append(el("th"), ...ids.map((id) => el("th", "", ids.length > 1 ? id : "")));
  const thead = el("thead"), body = el("tbody");
  thead.append(head);
  body.append(
    line("Stage", (id) => snap.pets[id].world.pet.stage),
    line("Times it thought in the last hour", (id) => String(snap.pets[id].world.calls.length)),
    line("Hidden-rule predictions right", (id) => snap.pets[id].accuracy == null ? "none yet" : `${snap.pets[id].accuracy}%`),
    ...RULES.map(([rule, label]) => line(label, (id) => `${snap.pets[id].world.exploits[rule]} times`)),
    line("Things made", (id) => String(snap.pets[id].things.length)),
    line("Beliefs held", (id) => String(snap.pets[id].beliefs.filter((b) => b.status === "active").length)),
    line("Marks", (id) => snap.pets[id].world.pet.genome.marks.join(", ") || "none"),
  );
  $("compare").replaceChildren(thead, body);
}

export function renderPanels(snap: Snapshot, petId: string, ruleOnly: boolean) {
  const pet = snap.pets[petId], w = pet.world, plan = w.plan;
  const hh = Math.floor(w.clock.hour), mm = String(Math.floor((w.clock.hour % 1) * 60)).padStart(2, "0");
  const state = w.pet.stage === "egg" ? "not hatched yet" : w.sleep ? "asleep" : w.thinking ? "thinking" : plan ? "busy" : "idle";

  $("petName").textContent = w.pet.name ?? "Pet";
  $("petStage").textContent = `${w.pet.stage}, day ${w.clock.day}`;
  $("status").replaceChildren(
    el("span", "chip", `${hh}:${mm} · ${w.clock.phase}`),
    el("span", "chip", state),
    el("span", snap.visitor_present ? "chip on" : "chip", snap.visitor_present ? "you are here" : "nobody watching"),
  );

  // Mind: what it means to do, why, and where it is in doing it
  $("needs").replaceChildren(...NEEDS.map((n) => {
    const v = w.pet.needs[n], r = el("div", v < 20 ? "need low" : "need");
    const bar = el("div", "bar"), fill = el("b");
    fill.style.width = `${v}%`;
    bar.append(fill);
    r.append(el("span", "", n), bar, el("span", "", String(Math.round(v))));
    return r;
  }));
  $("doing").textContent = w.pet.stage === "egg" ? "Still an egg." : w.sleep ? "Asleep." : plan ? plan.intention
    : w.thinking ? "Thinking about what to do…" : "Idle, between intentions.";
  $("thought").textContent = plan && !w.sleep ? plan.thought : "";
  $("steps").replaceChildren(...(plan && !w.sleep ? plan.steps.map((s, i) => {
    const li = el("li", i < plan.i ? "done" : i === plan.i ? "now" : "");
    li.append(el("span", "", i < plan.i ? "✓" : i === plan.i ? "▸" : "·"), el("span", "", actionText(s)));
    return li;
  }) : []));
  $("expecting").textContent = plan && !w.sleep ? `It expects: ${plan.expect || "nothing in particular"}` : "";
  const last = w.last_plan;
  $("before").replaceChildren(...(last ? [`Before that: ${last.intention} `,
    el("span", last.score, last.ended === "done" ? MARK[last.score] : `${last.ended}, ${MARK[last.score]}`)] : []));

  // Things: the shelf of everything it ever made. The pet's own words first; the truth underneath is for the visitor.
  $("shelf").replaceChildren(...(pet.things.length ? [...pet.things].reverse().map((t) => {
    const li = el("li", t.gone ? "gone" : ""), sums: Record<string, number> = {};
    for (const e of t.effects) for (const n of NEEDS) sums[n] = (sums[n] ?? 0) + (e[n] ?? 0);
    const seen = NEEDS.filter((n) => t.effects.length && Math.abs(sums[n]) >= 0.05 * t.effects.length)
      .map((n) => `${sums[n] > 0 ? "+" : ""}${(sums[n] / t.effects.length).toFixed(1)} ${n}`).join(", ");
    const title = el("div");
    title.append(el("b", "", t.name), t.gone ? ` (${t.gone[1]})` : "");
    li.append(thingPicture(t.recipe), title, el("div", "", `“${t.recipe.purpose}”`),
      el("div", "truth", `${t.recipe.material}: ${snap.materials[t.recipe.material] ?? ""}. Used ${t.uses} time${t.uses === 1 ? "" : "s"}${seen ? `, on average ${seen}` : ""}.`));
    return li;
  }) : [el("li", "empty", "It has not made anything yet.")]));
  document.querySelector('[data-tab="things"]')!.textContent = `Things (${pet.things.filter((t) => !t.gone).length})`;

  // Diary: every night so far, newest first
  $("diary").replaceChildren(...(w.diary.length ? [...w.diary].reverse().map((night) => {
    const box = el("div", "night"), changes = el("ul");
    changes.append(...night.changes.map((c) => el("li", "", c)));
    const body = el("p", "", night.body ? `Its body changed: ${night.body}. ` : "Its body did not change. ");
    if (night.reason) body.append(el("span", "hint", `“${night.reason}”`));
    box.append(el("p", "hint", `Night of day ${night.day}`), el("p", "", night.dream || "No dream summary."), body,
      ...(night.changes.length ? [el("p", "hint", "Beliefs changed while asleep"), changes] : []));
    return box;
  }) : [el("p", "empty", "It has not slept yet.")]));

  const active = pet.beliefs.filter((b) => b.status === "active").sort((a, b) => b.revised - a.revised);
  const gone = pet.beliefs.filter((b) => b.status !== "active");
  const item = (b: (typeof active)[number]) => {
    const li = el("li");
    li.append(el("span", "", b.id), el("div", "", b.statement));
    return li;
  };
  document.querySelector('[data-tab="beliefs"]')!.textContent = `Beliefs (${active.length})`;
  $("beliefs").replaceChildren(...(active.length ? active.map(item) : [el("li", "empty", "No beliefs yet.")]));
  $("discarded").replaceChildren(...gone.map(item));
  $("discardedLabel").textContent = `Discarded (${gone.length})`;

  // Lab: the measurements, and the journal of steps and intentions
  compare(snap);
  chart(snap);
  const rows = (pet.journal.filter((r) => r.type === "step" || r.type === "intention") as Rec[])
    .filter((r) => !ruleOnly || r.rule_tags.length > 0).reverse();
  $("journal").replaceChildren(...(rows.length ? rows.map((r) => {
    const li = el("li", r.type === "intention" ? "plan" : ""), what = el("span", "what");
    if (r.type === "intention") {
      li.title = `expected: ${r.expect}\nended: ${r.ended}`;
      what.textContent = r.intention;
      what.append(...deltas(r), ...tags(r));
      li.append(el("span", "t", `t${r.tick}`), what, el("span", r.score, r.ended === "done" ? MARK[r.score] : r.ended.split(":")[0]));
    } else {
      li.title = r.feedback;
      what.textContent = actionText(r.action);
      what.className = r.reason ? "what rejected" : "what";
      what.append(...deltas(r), ...tags(r));
      li.append(el("span", "t", `t${r.tick}`), what, el("span", "rejected", r.reason ? "not possible" : ""));
    }
    return li;
  }) : [el("li", "empty", ruleOnly ? "No hidden rule fired in what is shown." : "Nothing yet.")]));
}
