// SPEC-v4.0 §10.2, §11: the visitor's panel, in the console. The chosen hob (click it in the room, or its card), a box
// to type in, and the tools: talk to it, teach it, suggest an aim, praise or scold it, give it something, and, while a
// fight is on or after a killing, step in. Under them what it last said to you, and the inbox of hobs' questions, each
// with its answer box. It replaces the toolbar's Say (writing on a wall stays there); name and star are as they were.
// Shown only while the engine says the visitor's tools are on (snapshot.v4.visitor4). SPEC-v4.2 §9.4: with spirit on, a
// sick or hurt hob can be tended, and a sick one given a remedy (contracts.VISITOR_TOOLS: every one has its button here).
import { el, face } from "./dom";
import type { Kid } from "./dom";
import { ago } from "./types";
import { thingSprite } from "./sprite";
import { getJSON } from "./ui";
import type { PetV, Snap } from "./types";

/** POST a tool; what the house says back, or why not. */
export async function useTool(tool: string, body: object): Promise<{ ok: boolean; said: string }> {
  try {
    const r = await fetch(`/api/visitor/${tool}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    return r.ok ? { ok: true, said: j.said ?? "" } : { ok: false, said: j.error ?? j.detail ?? "it could not be done" };
  } catch {
    return { ok: false, said: "the house is not answering" };
  }
}

const SKILLS = ["crafting", "building", "cooking", "fishing", "foraging", "healing", "inventing", "music", "reading", "fighting", "talking"];
const BLOWS = new Set(["fight", "harm", "shove"]);
let status = "", drawnKey = "", statusTimer: ReturnType<typeof setTimeout> | undefined;
/** SPEC-v5.3.2 §1: "place" and "remove". The palette is every kind in kinds.toml, drawn with the catalog's own art;
 *  arming one makes the next click on the room the visitor's, not the page's (main.ts asks placeClick first). */
export type Kind = { kind: string; words: string[]; a: string; verbs: string[]; nature: string; wall: boolean; how: string };
let kinds: Kind[] | null = null, open = false, armed: { mode: "place" | "remove"; kind?: string } | null = null;
let redraw: () => void = () => {};
/** A line of what the house said back, for fifteen seconds (the panel's own `say`, from outside a render). */
function note(msg: string) {
  status = msg; clearTimeout(statusTimer); statusTimer = setTimeout(() => { status = ""; redraw(); }, 15_000); redraw();
}
function loadKinds() {
  if (kinds) return;
  void getJSON<{ kinds?: Kind[] }>("/api/visitor/kinds").then((d) => { kinds = d?.kinds ?? []; redraw(); });
}
/** The click on the room while a tool is armed: it is the visitor's, and the page sees nothing. True when consumed. */
export function placeClick(room: string, t: { tile: [number, number]; object?: string }): boolean {
  const arm = armed;   // (a module-level `let`: taken once, so its shape is fixed while the house answers)
  if (!arm) return false;
  const body = arm.mode === "place" ? { room, kind: arm.kind, pos: t.tile } : { room, name: t.object ?? "" };
  void useTool(arm.mode, body).then((r) => {
    note(r.ok ? r.said || "done" : `not done: ${r.said}`);
    armed = null;   // (one click, one thing: arm it again for another)
    redraw();
  });
  return true;
}
/** What the chosen hob can be taught (B-notes: its page's `visitor.can_teach`), asked for when it is chosen and every half minute. */
let teachable: { pid: string; at: number; recipes: { key: string; words: string }[]; skills: string[] } | null = null;
function canTeach(pid: string) {
  if (teachable?.pid === pid && Date.now() - teachable.at < 30_000) return;
  teachable = { pid, at: Date.now(), recipes: teachable?.pid === pid ? teachable.recipes : [], skills: SKILLS };
  void getJSON<{ visitor?: { can_teach?: { recipes: { key: string; words: string }[]; skills: string[] } } }>(`/api/petpage/${encodeURIComponent(pid)}`).then((d) => {
    const c = d?.visitor?.can_teach;
    if (c && teachable?.pid === pid) { teachable = { pid, at: Date.now(), recipes: c.recipes ?? [], skills: c.skills?.length ? c.skills : SKILLS }; drawnKey = ""; }
  });
}

/** The inbox's list, kept: its questions put in afresh. */
const fill = (list: HTMLElement, kids: Node[]) => { list.replaceChildren(...kids); return list; };

/** Draw the panel (only when what it shows has changed). `name`: a hob's name as the page shows it. */
export function visitorPanel(box: HTMLElement, s: Snap, sel: PetV | undefined, name: (p: PetV) => string, bits: string[]) {
  const V = s.visitor4 ?? {}, part = box.closest<HTMLElement>(".cpart")!;
  part.hidden = !(s.v4?.visitor4 && s.visitor4);
  document.body.classList.toggle("visit4", !part.hidden);
  if (part.hidden) return;
  const p = sel && sel.stage !== "egg" && sel.stage !== "dead" ? sel : undefined, pet = (id: string | null | undefined) => s.pets.find((q) => q.id === id);
  // step in: a fight or a killing in the last world hour (who struck first is the moment's own hob)
  const hour = s.day_seconds / s.tick_seconds / 24, recent = [...s.moments].reverse().find((m) => (BLOWS.has(m.kind) || m.kind === "killing") && s.tick - m.tick < hour);
  // (19 October 2026: every question waiting from a living hob, newest first; a dead hob's can't be answered)
  const inbox = (V.inbox ?? []).filter((q) => !q.answer && (pet(q.pet)?.stage ?? "dead") !== "dead").sort((a, b) => b.tick - a.tick), log = (V.log ?? []).filter((l) => p && l.pet === p.id).slice(-2);
  if (p) canTeach(p.id);
  const T = teachable?.pid === p?.id ? teachable : null;
  const key = JSON.stringify([p?.id, p && name(p), p?.mood4, inbox, log, recent?.n, status, Object.keys(V.protect ?? {}), T?.recipes.length, s.spirit && [p?.sick?.level, p?.hurt?.level]]);
  if (key === drawnKey && box.childElementCount) return;
  drawnKey = key;
  const text = box.querySelector<HTMLInputElement>("input.vtext")?.value ?? "", answers = new Map([...box.querySelectorAll<HTMLInputElement>("input.vans")].map((i) => [i.dataset.n, i.value]));
  const again = () => { drawnKey = ""; visitorPanel(box, s, sel, name, bits); };
  // (SPEC-v4.0.5 §7.8: what the house said back stays fifteen seconds, then clears itself)
  redraw = again;
  const say = (msg: string) => note(msg);
  const run = async (tool: string, body: object, clear?: HTMLInputElement) => {
    const r = await useTool(tool, body);
    if (r.ok && clear) clear.value = "";
    say(r.ok ? r.said || "done" : `not done: ${r.said}`);
  };
  const btn = (label: string, go: () => void, title = "", off = false) => { const b = el("button", "cbtn", label) as HTMLButtonElement; b.type = "button"; b.onclick = go; b.title = title; b.disabled = off; return b; };
  const input = el("input", "vtext") as HTMLInputElement;
  Object.assign(input, { maxLength: 200, value: text, placeholder: p ? `say something to ${name(p)}` : "choose a hob first" });
  input.disabled = !p;
  input.setAttribute("aria-label", "What to say, suggest or teach");
  const words = () => input.value.trim();
  const form = el("form", "vtalk", input, btn("TALK", () => form.requestSubmit(), "Say it to the chosen hob: it answers in its own voice, and remembers.", !p)) as HTMLFormElement;
  form.onsubmit = (e) => { e.preventDefault(); if (p && words()) void run("talk", { pet: p.id, text: words() }, input); };
  const teach = el("select", "vsel") as HTMLSelectElement;
  const group = (label: string, opts: HTMLOptionElement[]) => { const g = document.createElement("optgroup"); g.label = label; g.append(...opts); return g; };
  teach.replaceChildren(new Option("teach...", ""), group("a skill", (T?.skills ?? SKILLS).map((k) => new Option(k))),
    ...(T?.recipes.length ? [group("how to make", T.recipes.map((r) => Object.assign(new Option(r.words.length > 48 ? `${r.words.slice(0, 47)}…` : r.words, r.key), { title: r.words })))] : []),
    new Option("my words, as a hint", "hint"));
  teach.setAttribute("aria-label", "What to teach");
  teach.disabled = !p;
  teach.onchange = () => { if (p && teach.value) void run("teach", teach.value === "hint" ? { pet: p.id, what: words(), hint: true } : { pet: p.id, what: teach.value }, teach.value === "hint" ? input : undefined); };
  const give = el("select", "vsel") as HTMLSelectElement;
  give.replaceChildren(new Option("give...", ""), ...bits.map((b) => new Option(b)));
  give.setAttribute("aria-label", "What to give");
  give.disabled = !p;
  give.onchange = () => { if (p && give.value) void run("give", { pet: p.id, what: give.value }); };
  const striker = recent ? pet(recent.pets?.[0] ?? recent.pet) : undefined;
  const step = recent ? el("div", "vstep", el("b", "", recent.kind === "killing" ? "AFTER A KILLING:" : "A FIGHT:"),
    ...(recent.kind === "killing" && striker ? [btn("PARDON", () => void run("stepin", { how: "pardon", pet: striker.id }), `Pardon ${name(striker)}.`),
      btn("SHUN", () => void run("stepin", { how: "shun", pet: striker.id }), `Nobody is to talk to ${name(striker)}.`),
      btn("DRIVE OUT", () => void run("stepin", { how: "drive out", pet: striker.id }), `Drive ${name(striker)} out to the meadow.`)]
      : [btn("STOP IT", () => void run("stepin", { how: "stop", pet: recent.pet }), "They freeze and back off.")]),
    p ? btn("PROTECT", () => void run("stepin", { how: "protect", pet: p.id }), `Nobody can hurt ${name(p)} for a day.`) : null) : null;
  // SPEC-v4.2 §9.4 (D's routes): a sick or hurt hob can be sat with for a world hour, and given a remedy if the house has one
  const ailing = !!s.spirit && !!p && (!!p.sick || !!p.hurt?.level);
  const care = ailing ? el("div", "vtools", btn("TEND", () => void run("tend", { pet: p!.id }), `Sit with ${name(p!)} for a world hour: it mends a stage a day by it.`),
    p!.sick ? btn("REMEDY", () => void run("remedy", { pet: p!.id }), `Give ${name(p!)} a remedy, if the house has one: it moves the sickness back two stages.`) : null) : null;
  /** SPEC-v5.3.2 §1: PLACE opens the palette of every kind; a kind armed, the next click in the room sets it down.
   *  REMOVE arms taking back what the visitor placed. Both are the engine's tools, and refuse when [visitor4] is off. */
  const placeRow = () => {
    loadKinds();
    const arm = (mode: "place" | "remove", kind?: string) => {
      const was = armed;   // (a module-level `let`: taken once, so its shape is fixed inside the arrow)
      armed = was && was.kind === kind && was.mode === mode ? null : { mode, kind };
      redraw();
    };
    const chip = (k: Kind) => {
      const b = el("button", "cbtn vpalchip", thingSprite({ kind: k.kind, color: "brown", size: 2 }, 2), el("span", "", k.kind)) as HTMLButtonElement;
      b.type = "button"; b.title = `${k.a} ${k.kind}${k.how ? ` - ${k.how}` : ""}${k.verbs.length ? ` - ${k.verbs.join(", ")}` : " - no use but meaning"}`;
      b.setAttribute("aria-label", `Place a ${k.kind}`);
      const on = armed !== null && armed.mode === "place" && armed.kind === k.kind;
      b.setAttribute("aria-pressed", String(on));
      b.onclick = () => arm("place", k.kind);
      return b;
    };
    const off = el("button", "cbtn", "STOP") as HTMLButtonElement;
    off.type = "button"; off.onclick = () => { armed = null; open = false; redraw(); };
    off.hidden = !armed;
    const rm = el("button", "cbtn", armed?.mode === "remove" ? "REMOVE: CLICK A THING" : "REMOVE") as HTMLButtonElement;
    rm.type = "button"; rm.title = "Take back a thing you placed. Click it in the room."; rm.onclick = () => arm("remove");
    const removing = armed !== null && armed.mode === "remove";
    rm.textContent = removing ? "REMOVE: CLICK A THING" : "REMOVE";
    rm.setAttribute("aria-pressed", String(removing));
    const go = el("button", "cbtn", open ? "PLACE: HIDE" : "PLACE") as HTMLButtonElement;
    go.type = "button"; go.title = "Set any kind of thing down on a tile you click. The hobs see it appear."; go.onclick = () => { open = !open; redraw(); };
    return el("div", "vplace", el("div", "vtools", go, rm, off),
      open ? el("div", "vpal", ...(kinds ?? [null]).map((k) => (k ? chip(k) : el("p", "cnote", "the kinds are coming")))) : null,
      armed ? el("p", "cnote", armed.mode === "place" ? `CLICK A TILE IN THE ROOM: a ${armed.kind} appears there` : "CLICK A THING YOU PLACED: you take it back") : null);
  };
  const who = p ? el("div", "vwho", face(p, 32), el("b", "", name(p)), p.mood4 ? el("span", "vmood", p.mood4.toUpperCase()) : null, V.protect?.[p.id] != null ? el("span", "vmood", "PROTECTED") : null)
    : el("p", "cnote", "CLICK A HOB IN THE ROOM, OR ITS CARD, TO TALK TO IT");
  // (whoever was typing keeps typing, the caret where it was; SPEC-v4.0.5 §7.8: the inbox's list is the same box, its
  // questions put in it afresh, and it stays scrolled where it was)
  const had = box.contains(document.activeElement) ? (document.activeElement as HTMLElement).dataset.n ?? "text" : null;
  const caret = had ? [(document.activeElement as HTMLInputElement).selectionStart, (document.activeElement as HTMLInputElement).selectionEnd] : null;
  const list = box.querySelector<HTMLElement>(".vinlist") ?? el("div", "vinlist"), scrolled = list.scrollTop;
  box.replaceChildren(...([who, form,
    el("div", "vtools", btn("PRAISE", () => p && void run("praise", { pet: p.id }), "Its pride and its feeling for you go up; what it did becomes likelier.", !p),
      btn("SCOLD", () => p && void run("scold", { pet: p.id }), "What it did becomes less likely; it may feel shame, or resent you.", !p),
      btn("SUGGEST", () => p && words() && void run("suggest", { pet: p.id, text: words() }, input), "Your words as an aim, for its next morning plan (as far as it trusts you).", !p), teach, give),
    placeRow(),   // SPEC-v5.3.2 §1: place and remove
    care, step,
    ...log.map((l) => el("p", "vlog", el("span", "you", `YOU: ${l.text ?? l.tool}`), l.said ? el("span", "", ` ${p ? name(p).toUpperCase() : ""}: ${l.said}`) : el("span", "", " ..."))),
    status ? el("p", "vstatus", status.toUpperCase()) : null,
    inbox.length ? el("div", "vinbox", el("p", "ctitle", `INBOX (${inbox.length})`), fill(list, inbox.map((q) => {
      const h = pet(q.pet), ans = el("input", "vans") as HTMLInputElement;
      Object.assign(ans, { maxLength: 200, value: answers.get(String(q.n)) ?? "", placeholder: "your answer" });
      ans.dataset.n = String(q.n);
      ans.setAttribute("aria-label", `Your answer to ${h ? name(h) : "a hob"}`);
      const f = el("form", "vq", el("p", "", h ? face(h, 24) : null, el("b", "", h ? name(h) : "a hob"), el("span", "q", `${q.kind === "help" ? "asks you for help" : ago(s, q.tick) < 120 ? "asks" : "asked"}: “${q.q}”`)), ans, btn("ANSWER", () => f.requestSubmit())) as HTMLFormElement;
      f.onsubmit = (e) => { e.preventDefault(); if (ans.value.trim()) void run("answer", { n: q.n, text: ans.value.trim() }, ans); };
      return f;
    }))) : null] as Kid[]).filter((k): k is Node => k instanceof Node));
  const typing = had ? (had === "text" ? input : box.querySelector<HTMLInputElement>(`input.vans[data-n="${had}"]`)) : null;
  if (typing) { typing.focus({ preventScroll: true }); if (caret) typing.setSelectionRange(caret[0], caret[1]); }
  list.scrollTop = scrolled;
}
