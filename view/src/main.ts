// Wiring (SPEC-v3 §10, SPEC-v3.2 §7): one websocket to the engine (or a recorded run played back), snapshots in, the
// visitor's actions out. Lays the page out round the room, decides which room is on screen, and keeps that choice
// across a reload.
import { $, el, emoteOf, face, moodWords, stageWord, thoughtOf, when } from "./dom";
import type { Ctx, Kid } from "./dom";
import { showRecord } from "./family";
import { icon } from "./icons";
import { drawMap } from "./minimap";
import { renderDrawer, showMind, sources, truthOf } from "./panels";
import { startReplay } from "./replay";
import type { Replay } from "./replay";
import { Room } from "./room";
import type { Target } from "./room";
import { artReady, aThing, firstSprite, hasSprite, sprite, thingSprite } from "./sprite";
import { momentRow } from "./story";
import { ago, fam, hhmm } from "./types";
import { voiceInput } from "./voice";
import { initVoice } from "./voicelab";
import type { Creature, Hello, Mark, Moment, Note, Obj, PetV, RoomV, Snap } from "./types";

const remember = (key: string, value: string) => { try { localStorage.setItem(key, value); } catch { /* private window */ } };
const recall = (key: string) => { try { return localStorage.getItem(key); } catch { return null; } };

const room = new Room();
const replayId = new URLSearchParams(location.search).get("replay");   // a family's number when a recorded run is being watched
let replay: Replay | null = null;
let raw: Snap | null = null;      // the last snapshot as it came
let snap: Snap | null = null;     // the same with any `tweak` laid over it
let hello: Hello | null = null;
let ready: Promise<unknown> | null = null;
let sock: WebSocket | null = null;
let lastInput = 0;                // presence needs real input, so a tab that was only opened does not count
let tweak: Record<string, unknown> = {};
// What is on screen. `follow` is "auto", a pet's id, or "" to stay in the room chosen by hand.
const view = { room: recall("room") ?? "", follow: recall("follow") ?? "auto", sel: recall("sel"), tab: recall("tab") ?? "family", drawer: recall("drawer") === "1" };
let picked: string | null = null; // a thing clicked, waiting for a tile to be moved to or a name
let autoAt = performance.now();   // when "auto" last changed rooms
const api: Record<string, unknown> = {};

const send = (msg: object) => sock?.readyState === WebSocket.OPEN && sock.send(JSON.stringify(msg));
const presence = () => send({ type: "presence", active: document.hasFocus() && Date.now() - lastInput < 5 * 60_000, room: view.room });
const act = (msg: object) => send({ ...msg, room: view.room });
const found = (s: Snap) => s.rooms.filter((r) => r.type);
const pet = (id: string | null | undefined) => snap?.pets.find((p) => p.id === id);
const cap = (t: string) => t.slice(0, 1).toUpperCase() + t.slice(1);

const ctx = (): Ctx => ({ snap: snap!, hello, sel: view.sel, room: view.room, replay: !!replayId, api, jump, show: openTab, redraw: () => showTab(view.tab), voiceLab, hear });

/** Sound (§10.6): every snapshot that reaches the screen passes through, live or replayed, with the room being
 *  looked at. View-only, like everything in this file: nothing about sound goes back to the engine. */
const { voice, lab: voiceLab } = initVoice(() => { const p = pet(view.sel) ?? snap?.pets.find((q) => q.needs); return p && snap ? { pet: p, snap } : null; });
/** One version of a song, as whoever made it would sing it (SPEC-v3.1 §3.4): a pet in its own voice (the dead keep
 *  theirs: the Family tab knows their bodies), the music box, or a bird. */
function hear(notes: Note[], by: string) {
  const p = pet(by) ?? ((api.family as { pets?: PetV[] } | undefined)?.pets ?? []).find((q) => q.id === by);
  if (!voice.hear(notes, p ? voiceInput(p, snap ?? undefined) : by === "music box" ? "box" : "bird")) flash("Turn sound on, in the header, to hear it.");
}

// ---- the page round the room (SPEC-v3.2 §7) ----

const [SIDE_MIN, SIDE_MAX, GAP, CARD_ROW] = [150, 420, 6, 96];
const BASIS = (p: PetV) => (p.stage === "egg" ? 150 : 220);   // style.css: the least width a card is given before the strip takes another row
let sideWidth = 0;
let tall = 0, tallAt = 0;   // how tall the cards have really been lately, when that is more than a row of them is allowed for
/** The room is drawn at the largest whole-number scale that leaves the header, the cards and the controls all on the
 *  screen: nothing on the page is ever below the fold. Beside the room are the map and what happened lately; on a
 *  narrow window they go underneath. Only what seldom changes decides the scale (the window, the drawer, how many are
 *  alive); cards grown unusually tall can make the room step down, and it steps up again only after they have been
 *  their usual height for a while, so the room never jumps about. */
function layout() {
  const main = document.querySelector("main")!, pad = getComputedStyle(main);
  const W = main.clientWidth - parseFloat(pad.paddingLeft) - parseFloat(pad.paddingRight), H = main.clientHeight - parseFloat(pad.paddingTop) - parseFloat(pad.paddingBottom);
  const [w, h] = snap ? [(snap.size[0] + 2) * 16, (snap.size[1] + 3) * 16] : [224, 176];   // the floor, a wall each side, two rows of wall above and one below
  let rows = 1, used = -8;   // how many rows the cards will take, as the stylesheet wraps them
  for (const p of snap?.pets.filter((p) => p.stage !== "dead") ?? []) {
    if (used + 8 + BASIS(p) > W) [rows, used] = [rows + 1, -8];
    used += 8 + BASIS(p);
  }
  const allowed = rows * CARD_ROW + (rows - 1) * 8, strip = $("cards").offsetHeight, now = performance.now();
  if (strip > allowed) [tall, tallAt] = [Math.max(tall, strip), now];
  else if (now - tallAt > 120_000) tall = 0;
  const stacked = W < 2 * w + SIDE_MIN + GAP, across = stacked ? W : W - SIDE_MIN - GAP;
  // a whole number of the screen's own pixels to each pixel of the art: on a sharp screen that allows 3.5 as well as 3 and 4
  const dpr = devicePixelRatio || 1, k = Math.max(stacked ? 1 : 2, Math.floor(Math.min(across / w, (H - Math.max(allowed, tall) - GAP) / h) * dpr + 0.001) / dpr);
  sideWidth = stacked ? Math.min(W, SIDE_MAX) : Math.min(SIDE_MAX, W - w * k - GAP);
  main.classList.toggle("stacked", stacked);
  const set = (e: HTMLElement, width: number, height: number | null) => { e.style.width = `${width}px`; e.style.height = height ? `${height}px` : ""; };
  set($("stage"), Math.ceil(w * k), Math.ceil(h * k));
  set($("side"), sideWidth, stacked ? null : Math.ceil(h * k));
  $("side").classList.toggle("slim", sideWidth < 250);
  if (snap) drawMap($("map"), snap, view.room, view.sel, (id) => jump({ room: id }), mapWidth());
}
const mapWidth = () => (sideWidth < 250 ? sideWidth : Math.min(190, sideWidth * 0.46));
const watch = new ResizeObserver(() => { tall = 0; layout(); });   // a new window, or the drawer: measure afresh
for (const e of [document.querySelector("header")!, document.querySelector("footer")!, document.querySelector("main")!, $("replayBar")]) watch.observe(e);

// ---- which room to show ----

const WEIGHT: Record<string, number> = { hatched: 100, death: 100, egg: 90, ended: 90, befriended: 70, nuzzle: 60, gift: 60, mouse: 60, told: 55,
                                         heirloom: 55, took: 55, room: 50, weak: 50, named: 45, words: 45, stage: 40, leak: 40, draught: 40, lost: 35, floated: 35,
                                         // SPEC-v3.1: a discovery is worth looking at wherever it turns up
                                         "arrival writing": 95, "arrival songs": 95, "arrival taming": 95, "arrival radio": 95, "arrival book": 95, "arrival strangers": 95,
                                         tamed: 65, young: 60, "creature died": 60, scrubbed: 55, crossed: 55, wrote: 50, song: 50, read: 45, untamed: 45 };

/** "Follow: auto" (§10.1): the room where the most is going on. A birth or a death wins at once; otherwise it
 *  takes a clearly better room, and a few seconds since the last move, to look away. */
function auto(s: Snap) {
  const score = new Map<string, number>();
  const add = (id: string | null, n: number) => { if (id && s.rooms.find((r) => r.id === id)?.type) score.set(id, Math.max(score.get(id) ?? 0, n)); };
  for (const m of s.moments) {
    const age = ago(s, m.tick);
    if (age <= 40) add(m.room, (WEIGHT[m.kind] ?? 0) - age / 4);
  }
  const up = s.pets.filter((p) => p.stage !== "dead" && p.stage !== "egg");
  for (const p of s.pets) {
    if (p.stage === "egg") add(p.room, (p.hatches_in ?? 99) < 20 ? 85 : 6);
    else if (p.stage === "dead") { if (!p.buried) add(p.room, 60); }
    else {
      add(p.room, 10 + 3 * up.filter((q) => q.room === p.room && !q.asleep).length - (p.asleep ? 6 : 0));
      if (p.said) add(p.room, p.said.to && p.said.to !== "visitor" ? 50 : 28);   // pets talking to each other
    }
  }
  for (const c of s.creatures) if (up.some((p) => p.room === c.room)) add(c.room, 45);
  const best = [...score].sort((a, b) => b[1] - a[1])[0], mine = score.get(view.room) ?? -1, now = performance.now();
  if (best && best[0] !== view.room && (mine < 0 || (best[1] >= mine + 15 && (now - autoAt > 6000 || best[1] >= 85)))) {
    autoAt = now;
    return best[0];
  }
  return view.room;
}

function jump(to: { pet?: string | null; room?: string | null }) {
  const p = pet(to.pet);
  if (p) view.sel = p.id;
  if (p && p.stage !== "dead") view.follow = p.id;
  else if (to.room && snap?.rooms.find((r) => r.id === to.room)?.type) [view.follow, view.room] = ["", to.room];
  render();
  poll();
}

// ---- drawing a snapshot ----

async function show(s: Snap) {
  if (s.hello) hello = s.hello;
  raw = s;
  snap = { ...s, ...tweak, clock: { ...s.clock, ...((tweak.clock as object) ?? {}) }, lineage: { ...s.lineage, ...((tweak.lineage as object) ?? {}) } };
  if (!ready) {
    layout();   // the room is given its box before it is made, so it is made the right size
    ready = Promise.all([room.init($("room"), s.size[0], s.size[1]), artReady]);
  }
  await ready;
  render();
  if (!shown) { shown = true; void poll(); }   // the drawer was left open: fill it at once, not at the next poll
}
let shown = false;

function render() {
  const s = snap;
  if (!s) return;
  const rooms = found(s), followed = pet(view.follow);
  if (view.follow && view.follow !== "auto" && (!followed || (followed.stage === "dead" && followed.buried))) view.follow = "auto";   // gone: back to auto
  if (view.follow === "auto") view.room = auto(s);
  else if (followed) view.room = followed.room;
  if (!rooms.some((r) => r.id === view.room)) view.room = s.pets.find((p) => p.stage !== "dead")?.room ?? s.start;
  if (!pet(view.sel)) view.sel = (view.follow !== "auto" && followed ? followed : s.pets.find((p) => p.stage !== "dead" && p.room === view.room) ?? s.pets.find((p) => p.stage !== "dead"))?.id ?? null;
  const here = rooms.find((r) => r.id === view.room)!;
  if (picked && !here.objects[picked]) picked = null;
  if (sent !== view.room) presence();
  sent = view.room;
  for (const [k, v] of Object.entries({ room: view.room, follow: view.follow, sel: view.sel ?? "" })) remember(k, v);

  voice.update(s, view.room, view.sel);
  header(s);
  room.update({ snap: s, room: here, hello, selected: view.sel, picked, replay: !!replayId });
  drawMap($("map"), s, view.room, view.sel, (id) => jump({ room: id }), mapWidth());
  side(s, here);
  cards(s);
  controls(s, here);
  if (view.drawer) renderDrawer(view.tab, ctx());

  // Moments (§9.1): a banner when something worth seeing happens. Not on first load: that would announce old news.
  const newest = s.moments.at(-1);
  if (newest && newest.n !== bannerN) {
    // a discovery (SPEC-v3.1 §1) is never passed over for whatever came just after it
    const fresh = bannerN >= 0 ? s.moments.filter((m) => m.n > bannerN) : [], m = fresh.find((m) => m.kind.startsWith("arrival")) ?? fresh.at(-1);
    // a project's own words are long and are in the list beside the room; the banner says whose it is
    if (m) flash(m.kind === "project" ? m.text.split(":")[0] : m.text, false, () => jump(m), m.kind);
    bannerN = newest.n;
  } else if (!newest) bannerN = 0;
}
let sent = "";
let bannerN = -1;
let bannerTimer: ReturnType<typeof setTimeout> | undefined;

function flash(text: string, error = false, go: (() => void) | null = null, kind = "") {
  const b = $("banner"), arrival = kind.startsWith("arrival");   // a discovery has its own picture and stays up longer
  b.replaceChildren(...(arrival ? [icon(kind, 18)] : []), text);
  b.className = error ? "error" : arrival ? "arrival" : "";
  b.hidden = false;
  b.onclick = () => { b.hidden = true; go?.(); };
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => (b.hidden = true), arrival ? 10_000 : error ? 5000 : 4500);
}

/** The one plain sentence about the house (SPEC-v3.2 §5.4). The engine writes it; a recording made before it did
 *  gets a modest one put together here from who is up and what they are doing. */
function nowLine(s: Snap) {
  if (s.now) return s.now;
  const where = (p: PetV) => s.rooms.find((r) => r.id === p.room)?.name ?? "the house";
  const up = s.pets.filter((p) => p.stage !== "dead" && p.stage !== "egg").sort((a, b) => Number(!!a.asleep) - Number(!!b.asleep)), eggs = s.pets.filter((p) => p.stage === "egg");
  if (!up.length) return eggs.length ? `An egg is waiting in ${where(eggs[0])}.` : "The house is quiet. Nobody lives here now.";
  const line = up.slice(0, 2).map((p) => `${cap(p.label)} is ${p.asleep ? "asleep" : p.doing?.split(" (")[0] || "awake"} in ${where(p)}.`).join(" ");
  return up.length > 2 ? `${line} ${up.length === 3 ? "One other is" : `${up.length - 2} others are`} in the house.` : line;
}

function header(s: Snap) {
  const alive = s.pets.filter((p) => p.stage !== "dead");
  $("family").textContent = `Family ${s.lineage.id}: ${alive.filter((p) => p.stage !== "egg").length} alive${alive.some((p) => p.stage === "egg") ? `, ${alive.filter((p) => p.stage === "egg").length} in the egg` : ""}`;
  const chip = (cls: string, ...kids: (Node | string)[]) => el("span", cls, ...kids);
  $("status").replaceChildren(
    ...(s.power ? [] : [chip("chip warn", icon("bolt"), "power cut")]),
    ...(replayId ? [] : [chip(s.visitor ? "chip on" : "chip", s.visitor ? "you are here" : "nobody watching")]),
    ...(s.turbo && !replayId ? [chip("chip", "turbo time")] : []),
  );
  // the sentence sits in the header, in a box two lines high that is always there, so it never moves the room; an unusually long one is set smaller
  const now = $("now"), line = now.firstElementChild as HTMLElement, text = nowLine(s);
  if (line.textContent !== text) {
    line.textContent = text;
    now.classList.remove("long");
    now.classList.toggle("long", line.offsetHeight > 2.5 * parseFloat(getComputedStyle(line).lineHeight));
  }
  const pick = $<HTMLSelectElement>("follow"), options = s.pets.filter((p) => p.stage !== "dead");
  const key = options.map((p) => p.id + p.label + p.stage).join();
  if (pick.dataset.key !== key) {
    pick.dataset.key = key;
    pick.replaceChildren(new Option("the action", "auto"), new Option("no one", ""), ...options.map((p) => new Option(p.stage === "egg" ? `${p.name ?? "an egg"} (egg)` : p.label, p.id)));
  }
  pick.value = view.follow;
}

/** Beside the room: where this is and what the sky is doing, the map, what is going on in the house, and the last few moments. */
function side(s: Snap, here: RoomV) {
  const c = s.clock, name = (id: string | null) => s.rooms.find((r) => r.id === id)?.name ?? "the house";
  $("sky").replaceChildren(el("h2", "", cap(here.name)),
    el("p", "", icon(c.phase === "night" && s.weather === "clear" ? "moon" : s.weather, 18), ` ${cap(c.season)}, ${s.weather}`),
    el("p", "hint", `day ${c.day}, ${hhmm(c.hour)}${c.phase === "day" ? "" : ` · ${c.phase}`} · year ${c.year}`));
  const line = (cls: string, pic: string, text: string, to: string | null) => {
    const li = el("li", cls, icon(pic), el("span", "", text));
    if (to) { li.style.cursor = "pointer"; li.onclick = () => jump({ room: to }); }
    return li;
  };
  $("happening").replaceChildren(
    ...(s.power ? [] : [line("warn", "bolt", "the power is out: every lamp is dark", null)]),
    ...(s.weather === "storm" ? [line("warn", "storm", "a storm is over the house", null)] : []),
    ...found(s).flatMap((r) => [
      ...(r.wet ? [line("warn", "drop", `water is coming into ${r.name}`, r.id)] : []),
      ...(r.cold ? [line("warn", "wind", `a draught in ${r.name}${r.shut.length ? `; its ${r.shut.join(" and ")} door is shut` : ""}`, r.id)] : []),
    ]),
    ...found(s).filter((r) => Object.values(r.objects).some((o) => o.fix?.radio && o.state === "on")).map((r) => line("", "radio", `the box is on in ${r.name}`, r.id)),
    ...s.creatures.map((cr) => line("", cr.tame ? "paw" : "mouse", `${beast(cr)} in ${name(cr.room)}, ${cr.doing}`, cr.room)),
  );
  const key = `${s.moments.at(-1)?.n}`;
  if ($("moments").dataset.key !== key) {
    $("moments").dataset.key = key;
    $("moments").replaceChildren(...[...s.moments].reverse().slice(0, 30).map((m: Moment) => momentRow({ jump }, m, m.day !== c.day)));
  }
}

/** A creature in a few words: "a moth"; once tame, whose it is and what it is called (SPEC-v3.1 §4.4). Never how far it trusts anyone. */
function beast(c: Creature) {
  const owner = pet(c.tame)?.label;
  return c.name ? `${c.name}${owner ? `, ${owner}'s ${c.kind},` : ` the ${c.kind}`}` : `a ${c.kind}${owner ? `, tame to ${owner},` : ""}`;
}

function clockLeft(sec: number) {
  return sec < 60 ? "under a minute" : `about ${Math.round(sec / 60)} min`;
}

/** A card for every living pet and every egg (SPEC-v3.2 §7): its picture, name, stage in a plain word, a small
 *  picture of how it feels when that is strong, at most two feelings in words, and what it is thinking of doing.
 *  Every line wraps; nothing is cut. Rebuilt only when what they show changes. */
function cards(s: Snap) {
  const who = s.pets.filter((p) => p.stage !== "dead").sort((a, b) => a.laid - b.laid);
  const where = (p: PetV) => s.rooms.find((r) => r.id === p.room)?.name ?? "";
  // the visitor's naming: what was offered, and whether the pet has taken it (said for a quarter of a day after it does)
  const naming = (p: PetV) => !p.naming ? null : !p.naming.took ? `you called it ${p.naming.offered}; waiting to hear`
    : p.naming.at != null && (s.tick - p.naming.at) * s.tick_seconds < s.day_seconds / 4 ? `it took the name ${p.naming.offered}` : null;
  const key = JSON.stringify(who.map((p) => [naming(p), p.id, p.label, p.stage, p.room, p.stage === "egg" ? clockLeft(p.hatches_in ?? 0) : [moodWords(p), emoteOf(p), thoughtOf(p)], p.genome, p.id === view.sel, p.family, p.animals]));
  const box = $("cards");
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  box.replaceChildren(...(who.length ? who.map((p) => {
    const egg = p.stage === "egg", emote = egg ? null : emoteOf(p), thought = thoughtOf(p), type = s.rooms.find((r) => r.id === p.room)?.type;
    const animals = (p.animals ?? []).map((a) => a.name ?? `a ${a.kind}`).join(", ");   // SPEC-v3.1 §4.4
    const feels = emote ? sprite(`emote.${emote}`, 2) : null, place = type ? sprite(`icon.room.${type}`, 1) : null;
    if (feels) feels.title = `feeling ${emote}`;
    if (place) place.title = `in ${where(p)}`;
    const mind = el("button", "mind", "mind") as HTMLButtonElement;
    mind.title = egg ? "What it was left" : `${p.label}'s mind: what it believes, its project, what it has just done`;
    mind.onclick = (e) => { e.stopPropagation(); openTab("mind", p.id); };
    const li = el("li", `card ${fam(p.family)}${p.id === view.sel ? " chosen" : ""}${egg ? " egg" : ""}`, el("span", "pic", face(p, 48), el("span", "", feels, place)),
      el("span", "txt", el("span", "name", el("b", "", egg ? p.name ?? "An egg" : p.label), ` ${stageWord(p)} `, mind),
        egg ? el("span", "mood", `hatches in ${clockLeft(p.hatches_in ?? 0).replace("about ", "")}`) : el("span", "mood", moodWords(p).join(", ")),
        naming(p) ? el("span", "naming", naming(p)!) : null,
        thought ? el("span", p.plan && !p.asleep ? "thought" : "doing", thought) : null,
        animals ? el("span", "", icon("paw", 12), ` ${animals}`) : null));
    // the whole card is the button that follows this pet; "mind" inside it is a button of its own
    li.tabIndex = 0;
    li.setAttribute("role", "button");
    li.title = `${egg ? "Look at this egg" : `Follow ${p.label}`}: it is in ${where(p)}`;
    li.onclick = () => jump({ pet: p.id, room: p.room });
    li.onkeydown = (e) => { if (e.target === li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); li.click(); } };
    return li;
  }) : [el("li", "empty-house", "Nobody is alive in the house.")]));
  layout();   // a birth, a death or an unusually long thought may change how much room the cards need
}

// ---- the visitor (§7.5): acts only in the room being looked at ----

function controls(s: Snap, here: RoomV) {
  const over = s.lineage.ended != null, objs = Object.values(here.objects);
  $("controls").hidden = !!replayId || over;
  $("ended").hidden = !!replayId || !over;
  document.querySelector("footer")!.hidden = !!replayId;
  if (replayId || over) return;
  const win = objs.find((o) => o.fix?.window);
  $<HTMLButtonElement>("feed").disabled = !objs.some((o) => o.fix && "meal" in o.fix);
  $<HTMLButtonElement>("window").disabled = !win;
  $("window").textContent = win?.state === "open" ? "Close window" : "Open window";
  const give = $<HTMLSelectElement>("giveBit");
  if (!give.options.length && hello) give.replaceChildren(...Object.keys(hello.bits).sort().map((b) => new Option(b)));
  const p = pet(view.sel), near = p && p.room === here.id && p.stage !== "egg" && p.stage !== "dead" ? p : null;
  const foundling = p && p.room === here.id && p.stage === "egg" && !p.parent && !p.name ? p : null;   // an egg that is nobody's can be given a name (SPEC-v3.1 §7.1)
  const thing = picked ? here.objects[picked] : null, can = thing ? !!thing.made : !!(near || foundling);
  $("chosenWhat").textContent = thing ? `the ${picked}: click a tile to move it` : near ? near.label : foundling ? "the egg that is nobody's" : "nobody chosen here";
  $("chosenWhat").classList.toggle("none", !thing && !near && !foundling);
  $<HTMLButtonElement>("poke").disabled = !!thing || !near;
  $<HTMLInputElement>("nameText").disabled = ($("nameForm").querySelector("button") as HTMLButtonElement).disabled = !can;
  $("chosenDone").hidden = !thing;
  $("room").classList.toggle("placing", !!thing);
  // SPEC-v3.1 §5.3: this turns the box off in the house, not only its sound here; only a pet can turn it on again
  const radio = $<HTMLButtonElement>("radioBtn"), on = !!s.radio?.on;
  radio.hidden = !s.radio?.here;
  radio.disabled = !on;
  radio.textContent = on ? "Mute radio" : "Radio is off";
  radio.title = on ? "Switch the box off in the house. A pet can switch it on again." : "The box is switched off. Only a pet can switch it on.";
}

room.onClick = (t: Target) => {
  if (!snap) return;
  lastInput = Date.now();
  const here = snap.rooms.find((r) => r.id === view.room), o = t.object ? here?.objects[t.object] : null;
  const can = !replayId && snap.lineage.ended == null;
  if (picked && !t.pet && t.object !== picked) {
    act({ type: "place", object: picked, tile: t.tile });
    picked = null;
  } else if (t.pet) jump({ pet: t.pet });
  else if (t.door) jump({ room: here?.doors[t.door] });
  else if (can && o && (o.made || o.fix?.movable)) picked = picked === t.object ? null : t.object!;
  else picked = null;
  render();
  // a tap has no pointer hovering: it shows the card where the thing is, for a few seconds
  if ($("tip").hidden && !t.door) card(t, (t.tile[0] + 1.5) / (snap.size[0] + 2), (t.tile[1] + 2.5) / (snap.size[1] + 3), 5000);
};

// ---- the hover card (SPEC-v3.2 §3.3): names are not drawn in the room; pointing at something says what it is ----

/** An inscription in full (SPEC-v3.1 §2.4): the words, whose hand, and when. */
const written = (m: Mark) => [el("blockquote", m.medium === "scratch" ? "scratch" : "chalk", m.text),
  el("p", "hint", `${m.medium === "scratch" ? "scratched" : "chalked"} by ${m.by_name ?? "someone"}, ${snap ? when(snap, m.tick) : ""}${(m.clarity ?? 1) < 0.5 ? "; it is fading" : ""}`)];

/** What the house's own furniture really does, for whoever is looking at the page. */
const FIX: Record<string, string> = {
  light: "a light: using it switches it on or off", meal: "food; it is filled again at dawn", soft: "a comfort to use", rest: "a place to rest: it gives back energy",
  toy: "something to play with", loud: "it is loud", cozy: "it is a comfort to be near", window: "a window: it can be opened and closed", mirror: "a mirror",
  plant: "it grows, and when it is ripe it is a meal", water: "water: things put in it drift off", bench: "a bench: a place to work at", sun: "a patch of sun that moves with the hour",
  radio: "when it is on it speaks scraps of the real world outside", book: "it answers a question put to it, out of an encyclopedia",
};

function fixture(name: string, o: Obj, here: RoomV, s: Snap, shown: HTMLCanvasElement | null): Kid[] {
  const pic = [`fix.${name}.${o.state}`, `fix.${name}`].find(hasSprite), fix = o.fix ?? {};
  const state = o.state === "ripe" ? "ripe" : o.grow != null ? (o.grow > 0.7 ? "nearly ripe" : "growing") : o.servings != null ? (o.servings ? `${o.servings} left in it` : "empty") : o.state ?? "";
  const does = Object.keys(FIX).filter((k) => k in fix && fix[k]).map((k) => FIX[k]);
  const said = fix.radio ? s.radio?.said.at(-1) : null;
  return [shown ?? (pic ? sprite(pic, 3) : null), el("div", "",
    el("b", "", `the ${name}`), state ? el("span", "hint", ` · ${state}`) : null,
    said ? el("p", "", said.text ? `It just said: “${said.text}”` : "Only static just now.") : null,
    fix.book && s.read_glow ? el("p", "", "Someone is reading it.") : null,
    does.length ? el("p", "truth", el("b", "", "What it really does: "), `${does.join("; ")}.`) : null,
    fix.movable && !replayId ? el("p", "hint", "Click to move it.") : null,
    ...(here.marks ?? []).filter((m) => m.on === name).flatMap(written))];
}

/** The room's own picture of what is under the pointer, exactly as it is drawn there (its colour, its wear), three
 *  screen pixels to one. The room offers it through `describe`; without that, the card looks the picture up itself. */
function drawn(t: Target): HTMLCanvasElement | null {
  const src = (room as unknown as { describe?: (t: Target) => { sprite?: HTMLCanvasElement | null } | null }).describe?.(t)?.sprite;
  if (!src?.width) return null;
  const c = el("canvas", "px") as HTMLCanvasElement, x = c.getContext("2d")!;
  [c.width, c.height] = [src.width * 3, src.height * 3];
  x.imageSmoothingEnabled = false;
  x.drawImage(src, 0, 0, c.width, c.height);
  return c;
}

function tipFor(t: Target): Kid[] | null {
  const s = snap, here = s?.rooms.find((r) => r.id === view.room);
  if (!s || !here) return null;
  const p = pet(t.pet), c = s.creatures.find((c) => c.id === t.creature), o = t.object ? here.objects[t.object] : null;
  if (p) {
    const egg = p.stage === "egg", gone = p.stage === "dead", thought = thoughtOf(p), mood = egg || gone ? "" : moodWords(p).join(", ");
    return [face(p, 64), el("div", "",
      el("b", "", egg ? p.name ?? "an egg" : p.label), el("span", "hint", ` · ${stageWord(p)}`),
      egg ? el("p", "", `It will hatch in ${clockLeft(p.hatches_in ?? 0)}.`) : gone ? el("p", "", `${cap(p.label)} has died.`) : null,
      mood ? el("p", "", `Feeling ${mood}.`) : null,
      thought && !egg && !gone ? el("p", p.plan && !p.asleep ? "thought" : "", p.plan && !p.asleep ? thought : `${cap(thought)}.`) : null,
      p.carrying?.length ? el("p", "hint", `Carrying ${p.carrying.join(", ")}.`) : null,
      pet(p.following) ? el("p", "hint", `Following ${pet(p.following)!.label}.`) : null)];
  }
  if (c) return [drawn(t) ?? (hasSprite(`creature.${c.kind}`) ? sprite(`creature.${c.kind}`, 3) : null), el("div", "", el("b", "", beast(c).replace(/,$/, "")), el("p", "", cap(c.doing) + "."),
    c.carry ? el("p", "hint", `It is carrying ${c.carry}.`) : null)];
  if (t.mark) return [el("div", "", ...written(t.mark))];
  if (t.door) {
    const to = s.rooms.find((r) => r.id === here.doors[t.door!]), shut = here.shut.includes(t.door), pic = firstSprite(`door.${shut ? "shut" : "open"}`, "door");
    return [hasSprite(pic) ? sprite(pic, 3) : null, el("div", "", el("b", "", to?.type ? `the door to ${to.name}` : "a door nobody has been through"),
      shut ? el("p", "", "It has blown shut.") : null, to?.type ? el("p", "hint", "Click to look in there.") : null)];
  }
  if (o?.made) {
    const m = o.made, maker = m.by === "visitor" ? "the visitor" : pet(m.by)?.label ?? "someone gone";
    return [drawn(t) ?? thingSprite(m.recipe, 3), el("div", "",
      el("b", "", aThing(m.recipe)), el("p", "", `“${m.called ?? t.object}”`),
      el("p", "hint", [`made by ${maker}`, m.owner_name && m.owner_name !== maker ? `${m.owner_name}'s now` : !m.owner_name ? "nobody's now" : null, m.heirloom ? "an heirloom" : null].filter(Boolean).join(" · ")),
      el("p", "hint", `${m.recipe.material}${m.recipe.purpose ? ` · for “${m.recipe.purpose}”` : ""}`),
      el("p", "truth", el("b", "", "What it really does: "), `${truthOf({ hello }, m).join("; ")}.`),
      replayId ? null : el("p", "hint", "Click to move or name it."),
      ...(here.marks ?? []).filter((x) => x.on === t.object).flatMap(written))];
  }
  if (o?.memorial) return [drawn(t) ?? (hasSprite("stone") ? sprite("stone", 3) : null), el("div", "", el("b", "", "a stone"), el("p", "", o.memorial.text),
    ...(here.marks ?? []).filter((x) => x.on === t.object).flatMap(written))];
  if (o && t.object) return fixture(t.object, o, here, s, drawn(t));
  if (t.bit) {
    const can = hello?.bits[t.bit]?.can ?? [];
    return [drawn(t) ?? (hasSprite(`bit.${t.bit}`) ? sprite(`bit.${t.bit}`, 3) : null), el("div", "", el("b", "", `some ${t.bit}`), el("p", "hint", "Something to gather and make things from."),
      can.length ? el("p", "truth", el("b", "", "What it really does: "), `a thing made of it can be ${can.join(" or ")}.`) : null)];
  }
  return null;
}

let tipTimer: ReturnType<typeof setTimeout> | undefined;
/** Show the card for what is at this place in the room (`fx`, `fy` are how far across and down it, 0 to 1). */
function card(t: Target | null, fx: number, fy: number, forMs = 0) {
  const tip = $("tip"), kids = t ? tipFor(t) : null;
  clearTimeout(tipTimer);
  tip.hidden = !kids;
  if (!kids) return;
  const key = JSON.stringify([t, snap?.tick]);
  if (tip.dataset.key !== key) { tip.dataset.key = key; tip.replaceChildren(...kids.filter((k): k is Node => k instanceof Node)); }
  tip.style.left = `${fx * 100}%`;
  tip.style.top = `${fy * 100}%`;
  tip.className = `${fx > 0.55 ? "left" : ""} ${fy > 0.5 ? "up" : ""}`;
  if (forMs) tipTimer = setTimeout(() => (tip.hidden = true), forMs);
}
room.onHover = (t, fx, fy) => card(t, fx, fy);

$("feed").onclick = () => act({ type: "feed" });
$("window").onclick = () => act({ type: "window" });
$("giveBtn").onclick = () => act({ type: "give", bit: $<HTMLSelectElement>("giveBit").value });
$("poke").onclick = () => act({ type: "poke", pet: view.sel });
$("chosenDone").onclick = () => { picked = null; render(); };
$("newLineage").onclick = () => send({ type: "new_lineage" });
$("talkForm").onsubmit = (e) => {
  e.preventDefault();
  const input = $<HTMLInputElement>("talkText");
  if (input.value.trim()) act({ type: "talk", text: input.value });
  input.value = "";
};
$("writeBtn").onclick = () => {   // SPEC-v3.1 §2.3: the visitor's hand, in chalk, on a wall of the room being looked at
  const input = $<HTMLInputElement>("talkText");
  if (input.value.trim()) act({ type: "write", text: input.value, on: $<HTMLSelectElement>("writeOn").value });
  else input.focus();
  input.value = "";
};
$("radioBtn").onclick = () => act({ type: "radio_off" });
$("nameForm").onsubmit = (e) => {
  e.preventDefault();
  const input = $<HTMLInputElement>("nameText");
  if (input.value.trim()) act(picked ? { type: "name", object: picked, name: input.value } : { type: "name", pet: view.sel, name: input.value });
  input.value = "";
  picked = null;
};
$<HTMLSelectElement>("follow").onchange = (e) => {
  view.follow = (e.target as HTMLSelectElement).value;
  if (pet(view.follow)) view.sel = view.follow;
  render();
};
addEventListener("keydown", (e) => { if (e.key === "Escape" && picked) { picked = null; render(); } });

// ---- the engine ----

function connect() {
  sock = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  sock.onopen = presence;
  sock.onmessage = (e) => {
    const data = JSON.parse(e.data) as Snap;
    if (data.error) return flash(data.error, true);
    if (replayId) {   // a replay needs the engine only for what the bits and materials are
      hello = data.hello ?? hello;
      sock!.onclose = null;
      sock!.close();
      return render();
    }
    show(data);
  };
  sock.onclose = () => {
    $("status").replaceChildren(el("span", "chip down", "engine not reachable, retrying…"));
    setTimeout(connect, 2000);
  };
}

// ---- the drawer: closed by default, so the room and the cards are the page ----

/** A tab's extra facts are asked for only while it is open, every few seconds (not every tick). */
async function poll() {
  if (!view.drawer || !snap || document.hidden) return;
  const tab = view.tab;
  try {
    await Promise.all(Object.entries(sources(tab, ctx())).map(async ([key, url]) => {
      const r = url ? await fetch(url) : null;
      if (r?.ok) api[key] = await r.json();
    }));
    if (view.drawer && view.tab === tab) renderDrawer(tab, ctx());
  } catch { /* the engine is away; the socket says so */ }
}
function setDrawer(open: boolean) {
  view.drawer = open;
  $("drawer").hidden = !open;
  $("drawerBtn").setAttribute("aria-expanded", String(open));
  document.body.classList.toggle("open", open);
  remember("drawer", open ? "1" : "0");
  if (open) showTab(view.tab);
}
function showTab(name: string) {
  view.tab = document.querySelector(`[data-tab="${name}"]`) ? name : "family";
  for (const b of document.querySelectorAll<HTMLElement>("[data-tab]")) b.setAttribute("aria-selected", String(b.dataset.tab === view.tab));
  for (const p of document.querySelectorAll<HTMLElement>("[data-panel]")) p.hidden = p.dataset.panel !== view.tab;
  remember("tab", view.tab);
  if (snap && view.drawer) renderDrawer(view.tab, ctx());
  poll();
}
/** Open a tab of the drawer. "mind" is the Lab turned to one pet's mind (what a card's button opens). */
function openTab(name: string, who?: string) {
  if (who) view.sel = who;
  if (who && name === "family") showRecord(who);
  if (name === "mind") showMind();
  view.tab = name === "mind" ? "lab" : name;
  setDrawer(true);
  render();
}
function theme(to?: string) {
  const now = document.documentElement.dataset.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = to ?? (now === "dark" ? "light" : "dark");
  document.documentElement.dataset.theme = next;
  $("themeBtn").textContent = next === "dark" ? "Light" : "Dark";
  remember("theme", next);
}
$("themeBtn").onclick = () => theme();
$("themeBtn").textContent = (document.documentElement.dataset.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark" ? "Light" : "Dark";
$("drawerBtn").onclick = () => setDrawer(!view.drawer);
$("drawerClose").onclick = () => setDrawer(false);
$("replayBtn").hidden = !!replayId;
$("replayBtn").onclick = () => (location.search = `?replay=${snap?.lineage.id ?? 1}`);
for (const b of document.querySelectorAll<HTMLElement>("[data-tab]")) b.onclick = () => showTab(b.dataset.tab!);
setDrawer(view.drawer);
setInterval(poll, 4000);

for (const type of ["pointerdown", "keydown"]) {
  addEventListener(type, () => { lastInput = Date.now(); presence(); }, { capture: true });
}
addEventListener("focus", presence);
addEventListener("blur", presence);
setInterval(presence, 15_000);
connect();
if (replayId) startReplay(replayId, show).then((r) => (replay = r));

// For checks and scripted screenshots: say what to look at, and read back what is on screen.
const overlaps = () => {
  const r = room.labels();
  return r.reduce((n, a, i) => n + r.slice(i + 1).filter((b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h).length, 0);
};
/** Everything on the page whose words do not fit the box they are in: there must be none (SPEC-v3 §10.7). */
const clipped = () => [...document.querySelectorAll<HTMLElement>("header *, #now, main *, footer *, #drawer *")].filter((e) => {
  if (!e.offsetParent || e.closest("#room") || e instanceof HTMLSelectElement || e instanceof HTMLInputElement || e instanceof SVGElement) return false;
  const o = getComputedStyle(e);
  if (e.id === "moments" || e.id === "happening") return false;   // these two show whole lines only: what does not fit is wrapped out of sight on purpose
  return (o.overflowX !== "visible" && o.overflowX !== "auto" && e.scrollWidth > e.clientWidth + 1) || (o.overflowY !== "visible" && o.overflowY !== "auto" && e.scrollHeight > e.clientHeight + 1);
}).map((e) => `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}.${e.className}: ${e.textContent?.slice(0, 40)}`);
Object.assign(window, { petView: {
  lookAt: (id: string) => jump({ room: id }),
  follow: (who: string | null) => { view.follow = who ?? ""; if (pet(who)) view.sel = who; render(); },
  select: (id: string) => { view.sel = id; render(); poll(); },
  openTab: (name: string | null, who?: string) => (name ? openTab(name, who) : setDrawer(false)),
  theme,
  /** Lay something over every snapshot before it is drawn, e.g. {weather: "storm", power: false, clock: {phase: "night"}}. */
  tweak: (over: Record<string, unknown> | null) => { tweak = over ?? {}; if (raw) show(raw); },
  /** The hover card for whatever is at a floor tile, as if the pointer were there. */
  hover: (t: Target | null) => (t ? card(t, (t.tile[0] + 1.5) / ((snap?.size[0] ?? 12) + 2), (t.tile[1] + 2.5) / ((snap?.size[1] ?? 8) + 3)) : card(null, 0, 0)),
  replay: () => replay,
  snap: () => raw,
  state: () => snap && {
    tick: snap.tick, clock: snap.clock, weather: snap.weather, power: snap.power, room: view.room, roomType: snap.rooms.find((r) => r.id === view.room)?.type,
    follow: view.follow, selected: view.sel, tab: view.drawer ? view.tab : null, theme: document.documentElement.dataset.theme ?? "system",
    replay: replay?.state() ?? null, ended: snap.lineage.ended != null, petsHere: snap.pets.filter((p) => p.room === view.room && !(p.stage === "dead" && p.buried)).map((p) => p.id),
    creaturesHere: snap.creatures.filter((c) => c.room === view.room).map((c) => c.kind), rooms: found(snap).map((r) => `${r.id}:${r.type}`),
    labels: room.labels(), overlaps: overlaps(), clipped: clipped(), scrolls: document.querySelector("main")!.scrollHeight - document.querySelector("main")!.clientHeight,
    stage: [$("stage").offsetWidth, $("stage").offsetHeight], scale: $("stage").offsetWidth / ((snap.size[0] + 2) * 16),
  },
} });
