// Wiring (SPEC-v3 §10, SPEC-v3.2 §7): one websocket to the engine (or a recorded run played back), snapshots in, the
// visitor's actions out. Lays the page out round the room, decides which room is on screen, and keeps that choice
// across a reload.
import { $, bar, doingOf, el, emoteOf, face, goodWord, hatchWords, moodWords, ownLabel, stageWord, wantWords, when, wishOf } from "./dom";
import type { Ctx, Kid } from "./dom";
import { showRecord } from "./family";
import { hubTip, openScreen, radioChoice, radioControl, radioSound, screens } from "./hub";
import { boardRows } from "./px/hub";
import { icon } from "./icons";
import { drawMap } from "./minimap";
import { noteInvented } from "./parts";
import { renderDrawer, showMind, sources, truthOf } from "./panels";
import { startReplay } from "./replay";
import { go, onRoute } from "./router";
import type { Route } from "./router";
import * as familyPage from "./pages/family";
import * as petPage from "./pages/pet";
import * as storyPage from "./pages/story";
import * as thingsPage from "./pages/things";
import type { Replay } from "./replay";
import { Room } from "./room";
import type { Target } from "./room";
import { artReady, aThing, firstSprite, hasSprite, sprite, thingSprite } from "./sprite";
import { momentRow } from "./story";
import { giveStar } from "./ui";
import { ago, fam, hhmm } from "./types";
import { voiceInput } from "./voice";
import { initVoice } from "./voicelab";
import type { Burst, Creature, Hello, Mark, Moment, Note, Obj, PetV, RoomV, Snap } from "./types";

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
const view = { room: recall("room") ?? "", follow: recall("follow") ?? "auto", sel: recall("sel"), tab: "lab", drawer: false, page: "house" };
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

const [SIDE_MIN, SIDE_MAX, GAP, CARD_ROW] = [150, 420, 5, 96];
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
  // SPEC-v3.5.3 §2: on a phone the room fills the width, and the page scrolls down to the cards and the rest
  const dpr = devicePixelRatio || 1, phone = innerWidth <= 640;
  const k = phone ? Math.max(1, Math.floor((across / w) * dpr + 0.001) / dpr) : Math.max(stacked ? 1 : 2, Math.floor(Math.min(across / w, (H - Math.max(allowed, tall) - GAP) / h) * dpr + 0.001) / dpr);
  sideWidth = stacked ? Math.min(W, SIDE_MAX) : Math.min(SIDE_MAX, W - w * k - GAP);
  main.classList.toggle("stacked", stacked);
  const set = (e: HTMLElement, width: number, height: number | null) => { e.style.width = `${width}px`; e.style.height = height ? `${height}px` : ""; };
  set($("stage"), Math.ceil(w * k), Math.ceil(h * k));
  set($("side"), sideWidth, stacked ? null : Math.ceil(h * k));
  $("side").classList.toggle("slim", sideWidth < 250);
  if (snap) drawMap($("map"), snap, view.room, view.sel, (id) => jump({ room: id }), mapWidth());
  placeDrawer();
}
function placeDrawer() { /* SPEC-v3.5.3: the drawer is gone; its tabs are pages */ }
const mapWidth = () => (sideWidth < 250 ? sideWidth : Math.min(190, sideWidth * 0.46));
const watch = new ResizeObserver(() => { tall = 0; layout(); });   // a new window, or the drawer: measure afresh
for (const e of [document.querySelector("header")!, document.querySelector("footer")!, document.querySelector("main")!, $("replayBar")]) watch.observe(e);
document.querySelector("main")!.addEventListener("scroll", placeDrawer);

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
  noteInvented(s.invented);   // SPEC-v3.5 §3: the kinds the house invented are drawn from their parts
  snap = { ...s, ...tweak, clock: { ...s.clock, ...((tweak.clock as object) ?? {}) }, lineage: { ...s.lineage, ...((tweak.lineage as object) ?? {}) } };
  snap.pets = snap.pets.map((p) => (p.label === "the little one" ? { ...p, label: ownLabel(p) } : p));   // a recording from before unnamed pets had labels of their own
  if (!ready) {
    layout();   // the room is given its box before it is made, so it is made the right size
    ready = Promise.all([room.init($("room"), s.size[0], s.size[1]), artReady]);
  }
  await ready;
  render();
  if (!shown) { shown = true; void poll(); }   // a page was opened by its address: fill it at once, not at the next poll
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
  radioSound(s, view.room, voice, !!replayId);   // SPEC-v3.5.1 §5: the station plays here while the radio is on
  screens(s, view.room);
  const burst = bursts(s);
  header(s);
  try {
    room.update({ snap: s, room: here, hello, selected: view.sel, picked, replay: !!replayId });
    for (const b of burst) if (b.room === view.room) room.burst(b.pet, b.kind);
  } catch (e) { console.error(e); }   // whatever goes wrong in the room, the page round it still says what is happening
  drawMap($("map"), s, view.room, view.sel, (id) => jump({ room: id }), mapWidth());
  side(s, here);
  cards(s);
  controls(s, here);
  if (view.drawer) renderDrawer(view.tab, ctx());

  // Moments (§9.1): a banner when something worth seeing happens. Not on first load: that would announce old news.
  // Nor after a jump in time (a replay scrubbed, a tab left asleep): a banner is only ever for a moment that belongs
  // to what is on screen, so whatever was up is taken down and nothing old is announced.
  const newest = s.moments.at(-1), jumped = shownTick >= 0 && (s.tick < shownTick || (s.tick - shownTick) * s.tick_seconds > 120);
  const BIG = (m: Moment) => m.kind === "death" || m.kind === "ended" || m.kind === "hatched" || m.kind === "storm" || m.kind.startsWith("arrival");
  // which of several to announce: a death before anything; then a birth, an arrival or a storm before a project or a
  // thing made; then what is about the room on screen, or about the whole house, before another room's news; then the newest
  const rank = (m: Moment) => (m.kind === "death" || m.kind === "ended" ? 100 : 0) + (BIG(m) ? 20 : 0) + (m.room === view.room || !m.room ? 10 : 0) + m.n / 1e9;
  const say = (m: Moment) => flash(m.kind === "project" ? m.text.split(":")[0] : m.text, false, () => jump(m), m.kind);   // a project's own words are long, and are in the list beside the room
  if (jumped) { $("banner").hidden = true; bannerN = newest?.n ?? 0; }
  else if (newest && newest.n !== bannerN) {
    // (a want met or a thing found out has the top line of the page: the banner does not say it a second time)
    const fresh = bannerN >= 0 ? s.moments.filter((m) => m.n > bannerN && !s.bursts?.some((b) => b.tick === m.tick && b.text === m.text)) : [];
    // a death is never old news: one from the last few minutes of the watcher's time is announced even on first load
    const died = bannerN < 0 && !replayId ? [...s.moments].reverse().find((m) => m.kind === "death" && ago(s, m.tick) < 600) : undefined;
    const m = [...fresh].sort((a, b) => rank(b) - rank(a))[0] ?? died;
    // a lesser moment does not push a death, a birth or an arrival off the screen while it is still up
    if (m && !(bannerBig && !$("banner").hidden && !BIG(m))) { say(m); bannerBig = BIG(m); }
    bannerN = newest.n;
  } else if (!newest) bannerN = 0;
  shownTick = s.tick;
}
let sent = "";
let bannerN = -1;
let bannerBig = false;   // the banner that is up is for a death, a birth, an arrival or a storm
let shownTick = -1;   // the tick of the snapshot last drawn
let bannerTimer: ReturnType<typeof setTimeout> | undefined;

type Box = { x: number; y: number; w: number; h: number };
const covers = (a: Box, b: Box) => Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
/** The room as the page lays things over it, in the stage's own pixels: how big a floor tile is, the box the room's
 *  walls stand in (the picture leaves half a tile clear at the sides and the foot), and everything words should keep
 *  off: the name plates, captions and bubbles the room has laid out, and whoever is standing or sitting in it. */
function roomBoxes() {
  const stage = $("stage"), at = stage.getBoundingClientRect(), cv = $("room").querySelector("canvas")?.getBoundingClientRect() ?? at;
  const [ox, oy, tile] = [cv.left - at.left, cv.top - at.top, cv.width / ((snap?.size[0] ?? 12) + 2)], edge = tile / 2 + 4;
  const busy: Box[] = [...room.labels().map((r) => ({ x: r.x + ox, y: r.y + oy, w: r.w, h: r.h })),
    ...(snap?.pets ?? []).filter((p) => p.room === view.room && !(p.stage === "dead" && p.buried)).map((p) => ({ x: ox + (p.pos[0] + 0.5) * tile, y: oy + (p.pos[1] + 1) * tile, w: 2 * tile, h: 2.2 * tile })),
    ...(snap?.creatures ?? []).filter((c) => c.room === view.room).map((c) => ({ x: ox + (c.pos[0] + 0.75) * tile, y: oy + (c.pos[1] + 1.75) * tile, w: 1.5 * tile, h: 1.5 * tile }))];
  return { tile, busy, inner: { x: ox + edge, y: oy + 4, w: cv.width - 2 * edge, h: cv.height - edge - 4 } };
}

function flash(text: string, error = false, go: (() => void) | null = null, kind = "") {
  const b = $("banner"), arrival = kind.startsWith("arrival"), death = kind === "death" || kind === "ended";   // a discovery has its own picture and stays up longer; a death longer still
  b.replaceChildren(...(arrival || death ? [icon(kind, 18)] : []), text);
  b.className = error ? "error" : arrival ? "arrival" : death ? "death" : "";
  b.hidden = false;
  b.onclick = () => { b.hidden = true; go?.(); };
  // inside the room's walls, wrapped if it is long; along the foot of the room, or along the top when someone is standing at the foot
  const { inner, busy } = roomBoxes();
  b.style.maxWidth = `${inner.w - 8}px`;
  const [w, h] = [b.offsetWidth, b.offsetHeight], x = inner.x + (inner.w - w) / 2, over = (y: number) => busy.reduce((n, r) => n + covers({ x, y, w, h }, r), 0);
  const [foot, head] = [inner.y + inner.h - h - 4, inner.y + 4];
  b.style.left = `${x}px`;
  b.style.top = `${over(head) < over(foot) ? head : foot}px`;
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => (b.hidden = true), death ? 20_000 : arrival ? 10_000 : error ? 5000 : 4500);
}

/** SPEC-v3.4 §5: a want met or a thing found out. Each is numbered and shown once (the last number is remembered across
 *  a reload, like the finished steps in room.ts; never old news): it takes the top line of the page for a few seconds,
 *  whichever room it was in, and the room plays a small burst over the pet for those in the room on screen. */
function bursts(s: Snap): Burst[] {
  const all = s.bursts ?? [], top = all.reduce((n, b) => Math.max(n, b.n), 0), house = `${s.start}|${s.lineage.id}|${s.profile}`;
  if (seenBurst == null) {
    const [h, n] = (recall("pet.bursts") ?? "").split("#");
    seenBurst = h === house && Number(n) <= top ? Number(n) : top;
  }
  const fresh = all.filter((b) => b.n > seenBurst! && ago(s, b.tick) <= 15);
  if (top !== seenBurst) remember("pet.bursts", `${house}#${top}`);
  seenBurst = top;   // (also when it is lower: a replay wound back, or another house)
  // ponytail: one at a time, the newest (a thing found out before a want met); a queue if they ever come in clumps
  const b = fresh.filter((x) => x.kind === "find").at(-1) ?? fresh.at(-1);
  if (b) {
    const ms = b.kind === "find" ? 11_000 : 8000;
    taken = { b, until: performance.now() + ms };
    clearTimeout(takenTimer);
    takenTimer = setTimeout(() => snap && header(snap), ms + 20);   // then the usual line again
  }
  return fresh;
}
let seenBurst: number | null = null;
let taken: { b: Burst; until: number } | null = null;   // what has the top line just now
let takenTimer: ReturnType<typeof setTimeout> | undefined;

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
  // SPEC-v3.5.3 §1: the world's time and season, in the slim header
  $("clock").textContent = `day ${s.clock.day} · ${hhmm(s.clock.hour)} · ${s.clock.season ?? ""}${s.clock.phase === "night" ? " night" : ""}`;
  const alive = s.pets.filter((p) => p.stage !== "dead");
  // how many families live here and how many are alive in each, each family in its colour (SPEC-v3.1 §7.4)
  const fams = [...new Set(alive.map((p) => p.family ?? 1))].sort(), NTH = ["", "first", "second", "third"];
  const count = (who: PetV[], eggs = who.filter((p) => p.stage === "egg").length) => `${who.length - eggs} alive${eggs ? `, ${eggs} in the egg` : ""}`;
  const said = fams.length > 1 ? fams.map((f) => `${f}:${count(alive.filter((p) => (p.family ?? 1) === f))}`).join("|") : count(alive);
  if ($("family").dataset.key !== said) {
    $("family").dataset.key = said;
    $("family").replaceChildren(...(!alive.length ? ["Nobody is alive in the house."] : fams.length < 2 ? [`One family: ${count(alive)}`]
      // (each family a line of its own that never breaks, so neither is ever cut in two at the panel's edge)
      : [`${fams.length === 2 ? "Two" : fams.length} families:`, ...fams.map((f) => el("span", "fline", el("b", fam(f), `the ${NTH[f] ?? `${f}th`}`), `, ${count(alive.filter((p) => (p.family ?? 1) === f))}`))]));
  }
  const chip = (cls: string, ...kids: (Node | string)[]) => el("span", cls, ...kids);
  $("status").replaceChildren(
    ...(s.power ? [] : [chip("chip warn", icon("bolt"), "power cut")]),
    ...(replayId ? [] : [chip(s.visitor ? "chip on" : "chip", s.visitor ? "you are here" : "nobody watching")]),
    ...(s.turbo && !replayId ? [chip("chip", "turbo time")] : []),
  );
  // the sentence sits in the header, in a box two lines high that is always there, so it never moves the room; an unusually long one is set smaller
  // The engine's sentence is about whoever acted last, which may be in another room. Whoever is in the room on screen
  // and is not named in it gets a short second line: who is here and what each is doing.
  // SPEC-v3.4 §5: a want met or a thing found out has the line to itself while it is up (a thing found out with a star)
  const got = taken && performance.now() < taken.until ? taken.b : null;
  const now = $("now"), line = now.firstElementChild as HTMLElement, text = got ? got.text : nowLine(s);
  const unsaid = got ? [] : s.pets.filter((p) => p.room === view.room && p.needs && !text.toLowerCase().includes(p.label.toLowerCase()));
  const here = got ? "" : unsaid.length ? `Here: ${unsaid.map((p) => `${p.label} is ${doingOf(p) || "here"}`).join("; ")}.` : s.pets.some((p) => p.room === view.room && p.stage !== "dead" && p.stage !== "egg") ? "" : "Here: nobody just now.";
  if (now.dataset.key !== text + here) {
    now.dataset.key = text + here;
    const mine = s.pets.filter((p) => p.room === view.room && p.needs);
    const lead = !!unsaid.length && unsaid.length === mine.length;   // the sentence is all about other rooms: this room's own line leads
    line.replaceChildren(...(lead ? [here, el("span", "here", text)] : [...(got?.kind === "find" ? [icon("star")] : []), text, ...(here ? [el("span", "here", here)] : [])]));
    now.className = got ? got.kind : "";
    now.classList.toggle("long", line.offsetHeight > now.clientHeight);   // more than the box holds: set smaller
    if (line.offsetHeight > now.clientHeight) line.querySelector(".here")?.remove();   // still more: the engine's sentence alone
  }
  dj(s);
  stock(s);
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
    // SPEC-v3.3 §2: how the room is kept, in the pets' own words, when things lie about in it
    ...(here.mess != null ? [el("p", `hint mess${here.mess === 2 ? " much" : ""}`, here.mess && here.mess_says ? `${cap(here.mess_says)}.` : "")] : []),
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
    ...found(s).filter((r) => Object.values(r.objects).some((o) => o.fix?.radio && o.state === "on")).map((r) => line("", "radio", `the radio is on in ${r.name}${s.dj?.radio.now ? `: ${s.dj.radio.now.title}` : ""}`, r.id)),
    ...s.creatures.map((cr) => line("", cr.tame ? "paw" : "mouse", `${beast(cr)} in ${name(cr.room)}, ${cr.doing}`, cr.room)),
  );
  const B = (s.ticker?.board ?? []).slice(0, 4), hubRoom = s.ticker?.room ?? null;   // SPEC-v3.5.4 §11: the board's lines, seen from any room
  $("board").hidden = !B.length;
  $("board").replaceChildren(...B.map((l) => {
    const li = el("li", l.kind, el("span", "", boardRows(l)[0]), l.meter ? bar(l.meter[0], l.meter[1]) : null, el("span", "who", l.meter ? `${l.meter[0]} of ${l.meter[1]} scrap` : boardRows(l)[1] ?? ""));
    if (hubRoom) li.onclick = () => jump({ room: hubRoom });
    return li;
  }));
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

/** A card for every living pet and every egg (SPEC-v3.2 §7): its picture, name, stage in a plain word, a small
 *  picture of how it feels when that is strong, at most two feelings in words, and what it is thinking of doing.
 *  Every line wraps; nothing is cut. Rebuilt only when what they show changes. */
function cards(s: Snap) {
  const who = s.pets.filter((p) => p.stage !== "dead").sort((a, b) => a.laid - b.laid);
  const where = (p: PetV) => s.rooms.find((r) => r.id === p.room)?.name ?? "";
  // the visitor's naming: what was offered, and whether the pet has taken it (said for a quarter of a day after it does)
  const naming = (p: PetV) => !p.naming ? null : !p.naming.took ? `you called it ${p.naming.offered}; waiting to hear`
    : p.naming.at != null && (s.tick - p.naming.at) * s.tick_seconds < s.day_seconds / 4 ? `it took the name ${p.naming.offered}` : null;
  const key = JSON.stringify(who.map((p) => [naming(p), p.id, p.label, p.stage, p.room, p.stage === "egg" ? hatchWords(p.hatches_in ?? 0) : [moodWords(p), goodWord(p), emoteOf(p), doingOf(p), wishOf(p), p.body?.icon, p.asleep || p.focus?.words, p.habits, p.wants?.map((w) => w.text), p.skills, p.recipes], p.genome, p.id === view.sel, p.family, p.animals]));
  const box = $("cards");
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  box.replaceChildren(...(who.length ? who.map((p) => {
    const egg = p.stage === "egg", emote = egg ? null : emoteOf(p), doing = doingOf(p), good = goodWord(p), type = s.rooms.find((r) => r.id === p.room)?.type;
    const animals = (p.animals ?? []).map((a) => a.name ?? `a ${a.kind}`).join(", ");   // SPEC-v3.1 §4.4
    const feels = emote ? sprite(`emote.${emote}`, 2) : null, place = type ? sprite(`icon.room.${type}`, 1) : null;
    // SPEC-v3.3 §1: the sign of what its body is doing by itself (the one over its head in the room), what its mind is on, and its habits
    const sign = !egg && p.body?.icon && hasSprite(`icon.act.${p.body.icon}`) ? sprite(`icon.act.${p.body.icon}`, 1) : null;
    const focus = egg || p.asleep ? "" : p.focus?.words ?? "", habits = egg ? [] : p.habits ?? [];
    const wish = wishOf(p) === focus ? "" : wishOf(p);   // since v3.3 what it means to do is what its mind is on, in the same words: said once
    // SPEC-v3.4 §2: its wants, said of it ("wants to know what is behind the north door"). The card has a line for the newest; all of them are in its hover
    const wants = (p.wants ?? []).map((w) => wantWords(w.text));
    if (feels) feels.title = `feeling ${emote}`;
    if (place) place.title = `in ${where(p)}`;
    // SPEC-v3.5.3 §2: a short card: portrait, name, stage, one line for what it is doing and one for what it wants, a
    // feeling as a small picture. The whole card goes to its page; the long words are there (and in the card's title).
    const li = el("li", `card ${fam(p.family)}${p.id === view.sel ? " chosen" : ""}${egg ? " egg" : ""}`, el("span", "pic", face(p, 48), el("span", "", feels ? el("span", "plate", feels) : null, place)),
      el("span", "txt", el("span", "name", el("b", "", egg ? p.name ?? "An egg" : p.label), ` ${stageWord(p)}`),
        egg ? el("span", "mood", hatchWords(p.hatches_in ?? 0)) : null,
        naming(p) ? el("span", "naming", naming(p)!) : null,
        doing ? el("span", "doing", el("i", "", "now "), sign, doing) : null,
        wants.length || wish ? el("span", "want", el("i", "", "wants "), wants[0]?.replace(/^wants /, "") ?? wish) : null));
    li.tabIndex = 0;
    li.setAttribute("role", "link");
    li.title = `${egg ? "This egg" : p.label}'s page. It is in ${where(p)}; ${moodWords(p).join(", ") || "content"}` + (wish && !egg ? `\nIt wants: ${wish}` : "")
      + (focus ? `\nIts mind is on: ${focus}` : "") + wants.map((w) => `\n${w.startsWith("wants ") ? `It ${w}` : cap(w)}`).join("")
      + (habits.length ? `\nIts habits: ${habits.join("; ")}` : "") + (animals ? `\nIts animals: ${animals}` : "");
    li.onclick = () => go("pet", p.id);
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
  // a control that cannot be used here says why: in its own words where it can, and in its title
  const set = (id: string, off: boolean, why: string, text?: string) => { const b = $<HTMLButtonElement>(id); b.disabled = off; b.title = off ? why : ""; if (text) b.textContent = text; };
  const win = objs.find((o) => o.fix?.window), bowl = objs.some((o) => o.fix && "meal" in o.fix);
  set("feed", !bowl, `There is no bowl in ${here.name} to fill.`, bowl ? "Feed" : "No bowl");
  set("window", !win, `There is no window in ${here.name}.`, !win ? "No window" : win.state === "open" ? "Close window" : "Open window");
  const give = $<HTMLSelectElement>("giveBit");
  if (!give.options.length && hello) give.replaceChildren(...Object.keys(hello.bits).sort().map((b) => new Option(b)));
  const p = pet(view.sel), near = p && p.room === here.id && p.stage !== "egg" && p.stage !== "dead" ? p : null;
  const foundling = p && p.room === here.id && p.stage === "egg" && !p.parent && !p.name ? p : null;   // an egg that is nobody's can be given a name (SPEC-v3.1 §7.1)
  const thing = picked ? here.objects[picked] : null, can = thing ? !!thing.made : !!(near || foundling);
  $("chosenWhat").textContent = thing ? `the ${picked}: click a tile to move it` : near ? near.label : foundling ? (foundling.family === 2 ? "the egg that is nobody's" : "the first egg") : "no one chosen";
  $("chosenWhat").classList.toggle("none", !thing && !near && !foundling);
  $("chosenWhat").title = thing || near || foundling ? "" : "Click a pet in this room, or its card, to poke or name it; click a thing a pet made to move or name it.";
  set("poke", !!thing || !near, thing ? "A thing cannot be poked. Let go of it first (×)." : "Choose a pet in this room first: click it, or its card.");
  set("nameBtn", !can, thing ? "Only a thing a pet has made can be given a name." : "Choose a pet in this room, or a thing a pet made, to name it.");
  $<HTMLInputElement>("nameText").disabled = !can;
  $<HTMLInputElement>("nameText").title = $("nameBtn").title;
  $("chosenDone").hidden = !thing;
  const star = $<HTMLButtonElement>("starBtn");   // SPEC-v3.5.4 §10: the visitor's star, one to a thing
  star.hidden = !thing?.made;
  star.disabled = !!thing?.made?.star;
  star.textContent = thing?.made?.star ? "★ Starred" : "★ Star";
  $("room").classList.toggle("placing", !!thing);
}

/** "Stock the machine" (SPEC-v3.5 §4.3), in the header: what the vending machine holds, a material to a row, and a
 *  button to put one more of it in (or fill it), up to its limit. It works whichever room is on screen. */
function stock(s: Snap) {
  const m = s.machine, btn = $<HTMLButtonElement>("stockBtn"), box = $("stockBox"), key = JSON.stringify(m ?? null);
  btn.hidden = !!replayId || s.lineage.ended != null;
  btn.disabled = !m;
  btn.title = m ? "Put wood, stone, metal, clay, fibre or sand in the vending machine. The pets take from it, two a day each." : "Nobody has found the machine room yet: the vending machine is in it.";
  if (!m || box.dataset.key === key) return;
  box.dataset.key = key;
  const put = (what: string, text: string, off: boolean) => { const b = el("button", "", text) as HTMLButtonElement; b.disabled = off; b.onclick = () => send({ type: "stock", what, n: 1 }); return b; };
  box.replaceChildren(el("h2", "", "The vending machine"), el("p", "hint", `in ${s.rooms.find((r) => r.id === m.room)?.name ?? "the machine room"} · it holds ${m.limit} of each`),
    el("ul", "", ...m.materials.map((x) => el("li", "", hasSprite(`bit.${x}`) ? sprite(`bit.${x}`, 2) : null, el("b", "", x), bar(m.stock[x] ?? 0, m.limit), el("span", "n", `${m.stock[x] ?? 0}`),
      put(x, "+1", (m.stock[x] ?? 0) >= m.limit)))),
    put("all", "Fill it", m.materials.every((x) => (m.stock[x] ?? 0) >= m.limit)));
}

/** The visitor's music and radio (SPEC-v3.3 §3), in the header. They show what the engine says is playing, so a
 *  reload or a second window agrees, and send what is chosen. Music plays in one room or through the house; the radio
 *  is the visitor's own little one, set down in the room on screen, until the pets have found theirs. */
let musicIn = recall("musicIn") ?? "room";   // where the music is to play when it is next turned on
function dj(s: Snap) {
  const d = s.dj, m = d?.music, box = $("dj"), key = JSON.stringify([d, view.room]);
  box.hidden = !d || !!replayId || s.lineage.ended != null;
  if (!d || box.hidden || box.dataset.key === key) return;
  box.dataset.key = key;
  const there = m && m.scope !== "house" && m.scope !== view.room ? s.rooms.find((r) => r.id === m.scope)?.name ?? "another room" : null;   // it plays in a room that is not the one on screen
  const [mood, scope] = [$<HTMLSelectElement>("musicMood"), $<HTMLSelectElement>("musicScope")];
  mood.replaceChildren(new Option("off"), ...d.moods.map((x) => new Option(x)));
  mood.value = m?.mood ?? "off";
  scope.replaceChildren(new Option("in this room", "room"), new Option("through the house", "house"), ...(there ? [new Option(`in ${there}`, "there")] : []));
  scope.value = !m ? musicIn : m.scope === "house" ? "house" : there ? "there" : "room";
  $("radioWho").textContent = d.radio.theirs ? "Their radio" : "Your little radio";
  $("radioWho").parentElement!.title = d.radio.theirs ? "The pets' own radio: this switches it on or off and says what it plays, wherever it is. They can still switch it themselves."
    : "Your own little radio, set down in the room you are looking at while it is on. Once the pets have found a radio of their own, this switches theirs.";
  radioControl(s);
}
$("musicMood").onchange = $("musicScope").onchange = () => {
  const scope = $<HTMLSelectElement>("musicScope").value, at = snap?.dj?.music?.scope;
  if (scope !== "there") remember("musicIn", (musicIn = scope));
  // "there": it goes on playing in the room it is in, whatever is on screen
  send({ type: "music", mood: $<HTMLSelectElement>("musicMood").value, scope: scope === "house" ? "house" : "room", room: scope === "there" && at ? at : view.room });
};
$("radioPlays").onchange = () => act(radioChoice(snap, $<HTMLSelectElement>("radioPlays").value));

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
  else if (o?.fix?.terminal) openScreen(snap, view.room, t.object!);   // SPEC-v3.5.1 §3: read what is on its screen
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
  keepsake: "a keepsake box: what someone who has died left lying about is kept in it, and can be taken out again",
  machine: "it gives each pet two materials a day, of its choosing; fed a made thing, or three bits, it gives one back; it never takes an heirloom or what is someone else's",
  radio: "while it is on it plays a real radio station, which you hear too", book: "it answers a question put to it, out of an encyclopedia",
};

function fixture(name: string, o: Obj, here: RoomV, s: Snap, shown: HTMLCanvasElement | null, notes: Kid[]): Kid[] {
  const pic = [`fix.${name}.${o.state}`, `fix.${name}`].find(hasSprite), fix = o.fix ?? {};
  const state = o.state === "ripe" ? "ripe" : o.grow != null ? (o.grow > 0.7 ? "nearly ripe" : "growing") : o.servings != null ? (o.servings ? `${o.servings} left in it` : "empty") : o.state ?? "";
  const does = Object.keys(FIX).filter((k) => k in fix && fix[k]).map((k) => FIX[k]);
  return [shown ?? (pic ? sprite(pic, 3) : null), el("div", "",
    el("p", "", el("b", "", o.build?.title ?? `the ${name}`), state ? el("span", "hint", ` · ${state}`) : null),
    o.says ? el("p", "", `${cap(o.says)}.`) : null,
    fix.book && s.read_glow ? el("p", "", "Someone is reading it.") : null,
    ...notes,
    does.length ? el("p", "truth", el("b", "", "What it really does: "), `${does.join("; ")}.`) : null,
    fix.movable && !replayId ? el("p", "hint", "Click to move it.") : null,
    ...(here.marks ?? []).filter((m) => m.on === name).flatMap(written))];
}

/** The room's own picture of what is under the pointer, exactly as it is drawn there (its colour, its wear), three
 *  screen pixels to one. The room offers it through `describe`; without that, the card looks the picture up itself. */
const told = (t: Target) => room.describe(t);
/** SPEC-v3.3 §2: the room's own lines about how a thing is kept (what it holds, where it is put away, its home, the corner it stands in), as they are. */
const kept = (t: Target) => (told(t)?.notes ?? []).map((n) => el("p", "", n));
function drawn(t: Target): HTMLCanvasElement | null {
  const src = told(t)?.sprite;
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
    const egg = p.stage === "egg", gone = p.stage === "dead", doing = doingOf(p), wish = wishOf(p), good = goodWord(p), mood = egg || gone ? "" : moodWords(p).join(", ");
    return [face(p, 64), el("div", "",
      el("p", "", el("b", "", egg ? p.name ?? "an egg" : p.label), el("span", "hint", ` · ${stageWord(p)}`)),
      egg ? el("p", "", `${cap(hatchWords(p.hatches_in ?? 0))}.`) : gone ? el("p", "", `${cap(p.label)} has died.`) : null,
      mood ? el("p", "", `Feeling ${mood}${good ? `; and ${good}` : ""}.`) : null,
      doing ? el("p", "", `Now: ${doing}.`) : null,
      wish ? el("p", "", "Wants: ", el("q", "", wish)) : null,
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
      m.star ? el("p", "star", "★ The visitor gave it a star.") : null,
      ...kept(t),
      el("p", "truth", el("b", "", "What it really does: "), `${truthOf({ hello }, m).join("; ")}.`),
      replayId ? null : el("p", "hint", m.star ? "Click to move or name it." : "Click to move, name or star it."),
      ...(here.marks ?? []).filter((x) => x.on === t.object).flatMap(written))];
  }
  if (o?.memorial) return [drawn(t) ?? (hasSprite("stone") ? sprite("stone", 3) : null), el("div", "", el("b", "", "a stone"), el("p", "", o.memorial.text), ...kept(t),
    ...(here.marks ?? []).filter((x) => x.on === t.object).flatMap(written))];
  const hub = o && t.object ? hubTip(t.object, o, s, drawn(t)) : null;   // SPEC-v3.5.1: the lit sign, a screen, a statue
  if (hub) return hub;
  if (o && t.object) return fixture(t.object, o, here, s, drawn(t), kept(t));
  if (t.bit) {
    const can = hello?.bits[t.bit]?.can ?? [];
    return [drawn(t) ?? (hasSprite(`bit.${t.bit}`) ? sprite(`bit.${t.bit}`, 3) : null), el("div", "", el("b", "", `some ${t.bit}`), el("p", "hint", t.bare ? "It grows here. Nothing to gather just now." : "Something to gather and make things from."),
      can.length ? el("p", "truth", el("b", "", "What it really does: "), `a thing made of it can be ${can.join(" or ")}.`) : null)];
  }
  // anything else the room can say something about: its own scenery (a bookcase, a barrel) is "part of the room"
  const it = told(t);
  return it ? [drawn(t), el("div", "", el("p", "", el("b", "", it.title)), it.text ? el("p", "hint", `${cap(it.text)}.`) : null)] : null;
}

let tipTimer: ReturnType<typeof setTimeout> | undefined;
/** Show the card for what is at this place in the room (`fx`, `fy` are how far across and down the room's box it is,
 *  0 to 1). The card stands beside what it describes, never on it, with a small point toward it; it stays inside the
 *  room's walls, and of the four sides it takes the one where it covers least of the pets and their captions. */
function card(t: Target | null, fx: number, fy: number, forMs = 0) {
  const tip = $("tip"), kids = t ? tipFor(t) : null;
  clearTimeout(tipTimer);
  tip.hidden = !kids;
  if (!kids) return;
  const key = JSON.stringify([t, snap?.tick]), nib = el("i", "nib");
  if (tip.dataset.key !== key) { tip.dataset.key = key; tip.replaceChildren(...kids.filter((k): k is Node => k instanceof Node), nib); }
  // beside the thing itself where the room says where it is drawn; otherwise beside the pointer
  const stage = $("stage"), { tile, busy, inner } = roomBoxes(), drawnAt = t ? told(t)?.rect : null;
  const at = drawnAt && drawnAt.w <= 5 * tile && drawnAt.h <= 4 * tile ? drawnAt : null;   // a wall, a floor or a big rug is everywhere: the pointer says which part is meant
  const [px, py] = at ? [at.x + at.w / 2, at.y + at.h / 2] : [fx * stage.clientWidth, fy * stage.clientHeight];
  const target = at ? { x: at.x - 2, y: at.y - 2, w: at.w + 4, h: at.h + 4 } : { x: px - tile * 0.8, y: py - tile * 0.9, w: tile * 1.6, h: tile * 1.7 }, [w, h] = [tip.offsetWidth, tip.offsetHeight], gap = 12;
  const within = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(Math.max(lo, hi), v));
  const spots = ([["right", target.x + target.w + gap, py - h / 2], ["left", target.x - gap - w, py - h / 2], ["below", px - w / 2, target.y + target.h + gap], ["above", px - w / 2, target.y - gap - h]] as [string, number, number][])
    .map(([side, x, y]) => ({ side, x: within(x, inner.x, inner.x + inner.w - w), y: within(y, inner.y, inner.y + inner.h - h) }))
    .map((p) => ({ ...p, cost: 20 * covers({ ...p, w, h }, target) + busy.reduce((n, r) => n + covers({ ...p, w, h }, r), 0) }));
  const best = spots.reduce((a, b) => (b.cost < a.cost ? b : a));
  tip.style.left = `${best.x}px`;
  tip.style.top = `${best.y}px`;
  const point = tip.querySelector<HTMLElement>(".nib")!, across = best.side === "below" || best.side === "above";
  point.className = `nib ${best.side}`;
  point.style.cssText = across ? `left:${within(px - best.x - 6, 6, w - 18)}px` : `top:${within(py - best.y - 6, 6, h - 18)}px`;
  if (forMs) tipTimer = setTimeout(() => (tip.hidden = true), forMs);
}
room.onHover = (t, fx, fy) => card(t, fx, fy);

// "Names": the room's own short labels of what every thing in it is, held on while this is pressed (otherwise
// a thing is named only while the pointer is on it). Off by default, and not remembered.
$("namesBtn").onclick = () => {
  const on = $("namesBtn").getAttribute("aria-pressed") !== "true";
  $("namesBtn").setAttribute("aria-pressed", String(on));
  (room as unknown as { names?: (on: boolean) => void }).names?.(on);
};
$("feed").onclick = () => act({ type: "feed" });
$("window").onclick = () => act({ type: "window" });
$("giveBtn").onclick = () => act({ type: "give", bit: $<HTMLSelectElement>("giveBit").value });
$("poke").onclick = () => act({ type: "poke", pet: view.sel });
$("chosenDone").onclick = () => { picked = null; render(); };
$("starBtn").onclick = async () => {
  const m = picked ? snap?.rooms.find((r) => r.id === view.room)?.objects[picked]?.made : null;
  const why = m ? await giveStar(String(m.id)) : null;
  if (why) flash(why, true);
};
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

// ---- the pages (SPEC-v3.5.3 §1): one is shown at a time, by the address ----

const PAGES: Record<string, { render: (root: HTMLElement, id: string | null) => void }> = { family: familyPage, pet: petPage, story: storyPage, things: thingsPage, thing: thingsPage };
let at: Route = { page: "house", id: null };
/** The Lab's facts are asked for only while it is shown, every few seconds; another page draws itself again as often. */
async function poll() {
  if (!snap || document.hidden) return;
  if (PAGES[at.page]) return PAGES[at.page].render($(`page-${at.page}`), at.id);
  if (!view.drawer) return;
  const tab = view.tab;
  try {
    await Promise.all(Object.entries(sources(tab, ctx())).map(async ([key, url]) => {
      const r = url ? await fetch(url) : null;
      if (r?.ok) api[key] = await r.json();
    }));
    if (view.drawer && view.tab === tab) renderDrawer(tab, ctx());
  } catch { /* the engine is away; the socket says so */ }
}
function showPage(r: Route) {
  at = r;
  view.page = r.page;
  view.drawer = r.page === "lab";
  document.body.dataset.page = r.page;
  for (const e of document.querySelectorAll<HTMLElement>(".page")) e.hidden = e.id !== `page-${r.page}`;
  for (const t of document.querySelectorAll<HTMLElement>("#tabs [data-page]")) {
    const on = t.dataset.page === r.page || (t.dataset.page === "family" && r.page === "pet") || (t.dataset.page === "things" && r.page === "thing");
    t.classList.toggle("on", on);
    if (on) t.setAttribute("aria-current", "page"); else t.removeAttribute("aria-current");
  }
  if (r.page === "house" && r.id) jump({ pet: r.id });   // #/house/<pet>: watching it (a pet page's "Watch now")
  if (r.page === "house") { tall = 0; layout(); render(); }
  else $(`page-${r.page}`).scrollTop = 0;
  void poll();
}
const showTab = (name: string) => { view.tab = name; void poll(); };
/** What used to open a tab of the drawer: a pet's page for a pet ("mind" or "family"), else that tab. */
function openTab(name: string, who?: string) {
  if (who) view.sel = who;
  if (who && (name === "mind" || name === "family")) return go("pet", who);
  if (name === "mind") showMind();
  go(name === "mind" ? "lab" : name);
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
$("replayBtn").hidden = !!replayId;
$("replayBtn").onclick = () => (location.search = `?replay=${snap?.lineage.id ?? 1}`);
onRoute(showPage);
$("visitBtn").onclick = () => $("visitBtn").setAttribute("aria-expanded", String(document.querySelector("footer")!.classList.toggle("open")));
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
const clipped = () => [...document.querySelectorAll<HTMLElement>("header *, #now, main *, footer *, .page:not([hidden]) *")].filter((e) => {
  if (!e.offsetParent || e.closest("#room") || e instanceof HTMLSelectElement || e instanceof HTMLInputElement || e instanceof SVGElement) return false;
  const o = getComputedStyle(e);
  if (e.id === "moments" || e.id === "happening") return false;   // these two show whole lines only: what does not fit is wrapped out of sight on purpose
  if (e.closest("#cards .card .txt")) return false;   // so does a card, which is one height always (SPEC-v3.2, v3.3): the whole of every line is in its hover and in the pet's mind
  return (o.overflowX !== "visible" && o.overflowX !== "auto" && e.scrollWidth > e.clientWidth + 1) || (o.overflowY !== "visible" && o.overflowY !== "auto" && e.scrollHeight > e.clientHeight + 1);
}).map((e) => `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}.${e.className}: ${e.textContent?.slice(0, 40)}`);
Object.assign(window, { petView: {
  lookAt: (id: string) => jump({ room: id }),
  follow: (who: string | null) => { view.follow = who ?? ""; if (pet(who)) view.sel = who; render(); },
  select: (id: string) => { view.sel = id; render(); poll(); },
  openTab: (name: string | null, who?: string) => (name ? openTab(name, who) : go("house")),
  go,
  theme,
  /** Lay something over every snapshot before it is drawn, e.g. {weather: "storm", power: false, clock: {phase: "night"}}. */
  tweak: (over: Record<string, unknown> | null) => { tweak = over ?? {}; if (raw) show(raw); },
  /** The hover card for whatever is at a floor tile, as if the pointer were there. */
  hover: (t: Target | null) => (t ? card(t, (t.tile[0] + 1.5) / ((snap?.size[0] ?? 12) + 2), (t.tile[1] + 2.5) / ((snap?.size[1] ?? 8) + 3)) : card(null, 0, 0)),
  replay: () => replay,
  snap: () => raw,
  /** SPEC-v3.3 §4: every sound the page has begun (the last 500), for checking without ears. */
  audioLog: voice.log,
  state: () => snap && {
    tick: snap.tick, clock: snap.clock, weather: snap.weather, power: snap.power, room: view.room, roomType: snap.rooms.find((r) => r.id === view.room)?.type,
    follow: view.follow, selected: view.sel, tab: view.page, theme: document.documentElement.dataset.theme ?? "system",
    replay: replay?.state() ?? null, ended: snap.lineage.ended != null, petsHere: snap.pets.filter((p) => p.room === view.room && !(p.stage === "dead" && p.buried)).map((p) => p.id),
    creaturesHere: snap.creatures.filter((c) => c.room === view.room).map((c) => c.kind), rooms: found(snap).map((r) => `${r.id}:${r.type}`),
    labels: room.labels(), overlaps: overlaps(), clipped: clipped(), scrolls: document.querySelector("main")!.scrollHeight - document.querySelector("main")!.clientHeight,
    stage: [$("stage").offsetWidth, $("stage").offsetHeight], scale: $("stage").offsetWidth / ((snap.size[0] + 2) * 16),
  },
} });
