// The DOM around the room: header, mind card, and the tabbed panels.
// Everything from the engine is set as text, never as HTML.
import type { Rec, Snapshot } from "./main";

const NEEDS = ["energy", "comfort", "curiosity"] as const;
const MARK = { correct: "✓ right", wrong: "✗ wrong", unscorable: "not scorable" };
const RULES: [string, string][] = [["lamp_night", "Lamp off for the night"], ["double_feed", "Spaced out its meals"], ["plant_window", "Plant to the window"]];
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

function row(dl: HTMLElement, term: string, ...value: (Node | string)[]) {
  const dd = el("dd");
  dd.append(...value);
  dl.append(el("dt", "", term), dd);
}

function chart(snap: Snapshot) {
  const c = $("chart") as HTMLCanvasElement, g = c.getContext("2d")!;
  const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v);
  const [W, H, L, R, T, B] = [c.width, c.height, 44, 14, 16, 30];
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
  g.setLineDash([8, 6]);
  g.strokeStyle = css("--accent");
  g.beginPath(); g.moveTo(L, y(snap.growth.accuracy)); g.lineTo(W - R, y(snap.growth.accuracy)); g.stroke();
  g.setLineDash([]);
  g.lineWidth = 3;
  g.textAlign = "left";
  Object.entries(snap.pets).forEach(([id, p], i) => {
    g.strokeStyle = g.fillStyle = css(LINE[id] ?? "--ink");
    g.fillText(id, L + 10 + i * 80, T + 16);
    g.beginPath();
    p.series.forEach(([t, v], k) => (k ? g.lineTo(x(t), y(v)) : g.moveTo(x(t), y(v))));
    g.stroke();
  });
  g.lineWidth = 1;
}

function compare(snap: Snapshot) {
  const ids = Object.keys(snap.pets), need = snap.growth;
  const line = (label: string, cell: (id: string) => string) => {
    const tr = el("tr");
    tr.append(el("td", "", label), ...ids.map((id) => el("td", "", cell(id))));
    return tr;
  };
  const head = el("tr");
  head.append(el("th"), ...ids.map((id) => el("th", "", id)));
  const thead = el("thead"), body = el("tbody");
  thead.append(head);
  body.append(
    line("Stage", (id) => snap.pets[id].world.pet.stage),
    line(`Hidden-rule predictions right (Child needs ${need.accuracy}%)`, (id) => snap.pets[id].accuracy == null ? "none yet" : `${snap.pets[id].accuracy}%`),
    ...RULES.map(([rule, label]) => line(label, (id) => `${snap.pets[id].world.exploits[rule]} of ${need.exploit_times}`)),
    line("Beliefs held", (id) => String(snap.pets[id].beliefs.filter((b) => b.status === "active").length)),
    line("Marks", (id) => snap.pets[id].world.pet.genome.marks.join(", ") || "none"),
  );
  $("compare").replaceChildren(thead, body);
}

export function renderPanels(snap: Snapshot, petId: string, ruleOnly: boolean) {
  const pet = snap.pets[petId], w = pet.world, last = pet.journal.at(-1);
  const hh = Math.floor(w.clock.hour), mm = String(Math.floor((w.clock.hour % 1) * 60)).padStart(2, "0");

  $("petName").textContent = w.pet.name ?? "Pet";
  $("petStage").textContent = `${w.pet.stage}, day ${w.clock.day}`;
  $("status").replaceChildren(
    el("span", "chip", `${hh}:${mm} · ${w.clock.phase}`),
    el("span", "chip", w.sleep ? "asleep" : "awake"),
    el("span", snap.visitor_present ? "chip on" : "chip", snap.visitor_present ? "you are here" : "nobody watching"),
  );

  $("needs").replaceChildren(...NEEDS.map((n) => {
    const v = w.pet.needs[n], r = el("div", v < 20 ? "need low" : "need");
    const bar = el("div", "bar"), fill = el("b");
    fill.style.width = `${v}%`;
    bar.append(fill);
    r.append(el("span", "", n), bar, el("span", "", String(Math.round(v))));
    return r;
  }));

  const mind = $("mind");
  mind.replaceChildren();
  $("thought").textContent = w.sleep ? "Asleep." : last?.thought ?? "";
  if (last && !w.sleep) {
    row(mind, "Did", actionText(last.action), ...(last.reason ? [el("span", "delta down", `not possible: ${last.reason}`)] : []));
    row(mind, "Expected", last.expect || "nothing", " ", el("span", last.score, MARK[last.score]));
    row(mind, "Happened", last.feedback, ...deltas(last), ...tags(last));
  }

  const rows = pet.journal.filter((r) => !ruleOnly || r.rule_tags.length).reverse();
  $("journal").replaceChildren(...(rows.length ? rows.map((r) => {
    const li = el("li"), what = el("span", r.reason ? "what rejected" : "what", actionText(r.action));
    li.title = `${r.feedback}\nexpected: ${r.expect}`;
    what.append(...deltas(r), ...tags(r));
    li.append(el("span", "t", `t${r.tick}`), what, el("span", r.reason ? "rejected" : r.score, r.reason ? "✗ not possible" : MARK[r.score][0] === "n" ? "" : MARK[r.score][0]));
    return li;
  }) : [el("li", "empty", ruleOnly ? "No hidden rule fired in the last 30 turns." : "Nothing yet.")]));

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

  const night = w.last_night, box = $("lastNight");
  if (!night) box.replaceChildren(el("p", "empty", "It has not slept yet."));
  else {
    const body = el("p", "", night.body ? `Its body changed: ${night.body}. ` : "Its body did not change. ");
    if (night.reason) body.append(el("span", "hint", `“${night.reason}”`));
    const changes = el("ul");
    changes.append(...night.changes.map((c) => el("li", "", c)));
    box.replaceChildren(el("p", "hint", `Night of day ${night.day}`), el("p", "", night.dream || "No dream summary."), body,
      ...(night.changes.length ? [el("p", "hint", "Beliefs changed while asleep"), changes] : []));
  }

  compare(snap);
  chart(snap);
}
