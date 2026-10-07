// The DOM panels: mind, metrics, beliefs, journal. Everything from the engine is set as text, never as HTML.
import type { Rec, Snapshot } from "./main";

const NEEDS = ["energy", "comfort", "curiosity"] as const;
const MARK = { correct: "✓ correct", wrong: "✗ wrong", unscorable: "– unscorable" };
const LINE: Record<string, string> = { twin: "--muted", model: "--accent" };
const $ = (id: string) => document.getElementById(id)!;

function el(tag: string, cls = "", text = "") {
  const e = document.createElement(tag);
  e.className = cls;
  e.textContent = text;
  return e;
}

function actionText(a: unknown) {
  if (!a || typeof a !== "object") return "(no action)";
  const { type, ...rest } = a as Record<string, unknown>;
  return [type, ...Object.values(rest).map((v) => (Array.isArray(v) ? `(${v})` : String(v)))].join(" ");
}

function outcome(r: Rec) {
  const changes = NEEDS.filter((n) => r.deltas[n]).map((n) => `${n} ${r.deltas[n] > 0 ? "+" : ""}${r.deltas[n].toFixed(1)}`);
  const e = el("span", "", [r.feedback, ...changes].join(" · "));
  for (const t of r.rule_tags) e.append(el("span", "tag", t));
  return e;
}

function row(dl: HTMLElement, term: string, ...value: (Node | string)[]) {
  const dd = el("dd");
  dd.append(...value);
  dl.append(el("dt", "", term), dd);
}

function chart(snap: Snapshot) {
  const c = $("chart") as HTMLCanvasElement, g = c.getContext("2d")!;
  const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v);
  const [W, H, L, R, T, B] = [c.width, c.height, 44, 12, 14, 28];
  const all = Object.values(snap.pets).flatMap((p) => p.series);
  g.clearRect(0, 0, W, H);
  g.font = "20px ui-monospace, Menlo, monospace";
  g.fillStyle = css("--muted");
  if (!all.length) {
    g.textAlign = "center";
    g.fillText("no rule-tagged predictions yet", W / 2, H / 2);
    return;
  }
  const t0 = Math.min(...all.map((p) => p[0])), t1 = Math.max(t0 + 1, ...all.map((p) => p[0]));
  const x = (t: number) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v: number) => T + (1 - v / 100) * (H - T - B);
  g.textAlign = "right";
  for (const v of [0, 50, 100]) {
    g.fillText(String(v), L - 8, y(v) + 7);
    g.strokeStyle = css("--line");
    g.beginPath(); g.moveTo(L, y(v)); g.lineTo(W - R, y(v)); g.stroke();
  }
  g.textAlign = "left";
  g.fillText(`t${t0}`, L, H - 4);
  g.textAlign = "right";
  g.fillText(`t${t1}`, W - R, H - 4);
  g.setLineDash([8, 6]);
  g.strokeStyle = css("--accent");
  g.beginPath(); g.moveTo(L, y(60)); g.lineTo(W - R, y(60)); g.stroke();
  g.setLineDash([]);
  g.lineWidth = 3;
  Object.entries(snap.pets).forEach(([id, p], i) => {
    if (!p.series.length) return;
    g.strokeStyle = g.fillStyle = css(LINE[id] ?? "--ink");
    g.beginPath();
    p.series.forEach(([t, v], k) => (k ? g.lineTo(x(t), y(v)) : g.moveTo(x(t), y(v))));
    g.stroke();
    g.textAlign = "left";
    g.fillText(id, L + 10 + i * 90, T + 18);
  });
  g.lineWidth = 1;
}

export function renderPanels(snap: Snapshot, petId: string, ruleOnly: boolean) {
  const pet = snap.pets[petId], w = pet.world, last = pet.journal.at(-1);
  const hh = Math.floor(w.clock.hour), mm = String(Math.floor((w.clock.hour % 1) * 60)).padStart(2, "0");
  $("status").className = "";
  $("status").textContent =
    `tick ${w.tick} · day ${w.clock.day}, ${hh}:${mm} (${w.clock.phase}) · ${w.sleep ? "asleep" : "awake"} · visitor ${snap.visitor_present ? "present" : "away"}`;

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
  if (last) {
    row(mind, "thought", last.thought || "—");
    row(mind, "action", el("span", last.reason ? "mono wrong" : "mono", actionText(last.action) + (last.reason ? ` (rejected: ${last.reason})` : "")));
    row(mind, "expect", last.expect || "—", " ", el("span", last.score, MARK[last.score]));
    row(mind, "outcome", outcome(last));
  }

  const facts = $("facts");
  facts.replaceChildren(...(w.pet.name ? ["Name ", el("b", "", w.pet.name), " · "] : []),
    "Stage ", el("b", "", w.pet.stage), ` · day ${w.clock.day} · rule-tagged accuracy `,
    el("b", "", pet.accuracy == null ? "n/a" : `${pet.accuracy}%`));
  chart(snap);

  const night = w.last_night, box = $("lastNight");
  if (!night) box.replaceChildren(el("p", "empty", "It has not slept yet."));
  else {
    const changes = el("ul");
    changes.append(...night.changes.map((c) => el("li", "", c)));
    const body = el("p", "", night.body ? `Its body changed: ${night.body}. ` : "Its body did not change.");
    if (night.reason) body.append(el("span", "hint", `“${night.reason}”`));
    box.replaceChildren(el("p", "hint", `Night of day ${night.day}`), el("p", "", night.dream || "No dream summary."), body,
      ...(night.changes.length ? [el("p", "hint", "Belief changes while asleep"), changes] : []));
  }

  const active = pet.beliefs.filter((b) => b.status === "active").sort((a, b) => b.revised - a.revised);
  const gone = pet.beliefs.filter((b) => b.status !== "active");
  const item = (b: (typeof active)[number]) => {
    const li = el("li");
    li.append(el("span", "", `${b.id} t${b.revised}`), b.statement);
    return li;
  };
  $("beliefs").replaceChildren(...(active.length ? active.map(item) : [el("li", "empty", "No beliefs yet.")]));
  $("discarded").replaceChildren(...gone.map(item));
  $("discardedLabel").textContent = `Discarded (${gone.length})`;

  const rows = pet.journal.filter((r) => !ruleOnly || r.rule_tags.length).reverse();
  $("journal").replaceChildren(...(rows.length ? rows.map((r) => {
    const li = el("li", r.reason ? "rejected" : "");
    li.append(el("span", "t", `t${r.tick} ${r.phase}`), el("span", "mono", actionText(r.action)), " → ", outcome(r), " ",
      el("span", r.score, MARK[r.score][0]));
    return li;
  }) : [el("li", "empty", ruleOnly ? "No rule-tagged entries in the last 30 ticks." : "Nothing yet.")]));
}
