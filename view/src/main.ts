// Wiring (SPEC-v3 §10, SPEC-v3.2 §7): one websocket to the engine (or a recorded run played back), snapshots in, the
// visitor's actions out. Lays the page out round the room, decides which room is on screen, and keeps that choice
// across a reload.
import { $, bar, byname, doingOf, el, emoteOf, eyes, face, goodWord, hatchWords, moodWords, ownLabel, plural, stageWord, wantWords, when, wishOf } from "./dom";
import type { Ctx, Kid } from "./dom";
import { showRecord } from "./family";
import { hubTip, openScreen, radioChoice, radioControl, radioSound, screens } from "./hub";
import { boardRows } from "./px/hub";
import { icon } from "./icons";
import { evening } from "./px/weather";
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
import { world } from "./world";
import type { Target } from "./room";
import { artReady, aThing, firstSprite, hasSprite, sprite, thingSprite } from "./sprite";
import { getJSON, giveStar, live } from "./ui";
import { roomCard, rows, sec, thingCard } from "./thingcard";
import { ago, fam, hhmm } from "./types";
import { voiceInput } from "./voice";
import { initVoice } from "./voicelab";
import { Banners, classify } from "./banner";
import type { Ev } from "./banner";
import { initUiSound, play } from "./uisound";
import { watchVersion } from "./reload";
import type { BoardLine, Burst, Creature, Hello, Mark, Moment, Need, Note, Obj, PetV, RoomV, Snap } from "./types";

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
// What is on screen. `follow` is "auto", a pet's id, or "" to stay in the room chosen by hand. SPEC-v3.5.10 §7: a page
// opens following the hobs, unless the visitor chose otherwise in the follow chip in this browser ("followPick"); a
// room looked into by hand is for this visit only.
const view = { room: recall("room") ?? "", follow: recall("followPick") ?? "auto", sel: recall("sel"), tab: "lab", drawer: false, page: "house" };
let picked: string | null = null; // a thing clicked, waiting for a tile to be moved to or a name
let clicked: string | null = null; // the pet last clicked in the room (to poke or name it)
let autoAt = performance.now();   // when "auto" last changed rooms
let looked = false;               // the page has made its first choice of room
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

/** The room is drawn at the largest whole-number zoom that fits its column and the window's height (SPEC-v3.5.9 §2): a
 *  whole number of the screen's own pixels to each pixel of the art, so on a sharp screen 3.5 as well as 3 and 4
 *  (v3.5.6 §5). What is left round it is its surround (skin.css). On a phone the width alone (the page scrolls down to
 *  the rest); on Small the width and the window's height under the room's header strip (the toolbar follows it down
 *  the page); from Laptop up the space the grid gives the room, and on a short window the toolbar folds into one
 *  "Visit" button when that gives the room a larger zoom, and opens out again when it no longer would. */
const SMALL = 700;   // skin.css: the set layouts (Phone, Small, then Laptop, Large and Huge in three columns)
/** Laptop and up: three columns; from v3.5.10 §8 also a landscape window 1000 wide (1024 x 768: the room at x2, the hobs and the board beside it). */
const desk = () => matchMedia("(min-width: 1200px), (min-width: 1000px) and (orientation: landscape)").matches;
let barH = 0;   // the toolbar's height and the gap above it, when it was last open
function layout(again = true) {
  const [w, h] = snap ? [(snap.size[0] + 2) * 16, (snap.size[1] + 3) * 16] : [224, 176];   // the floor, a wall each side, two rows of wall above and one below
  const dpr = devicePixelRatio || 1, wrap = $("roomwrap"), head = $("roomhead").getBoundingClientRect(), F = parseFloat(getComputedStyle($("frame")).borderTopWidth) || 14;
  const zoom = (fit: number) => Math.max(1, Math.floor(fit * dpr + 0.001) / dpr), W = (wrap.clientWidth - 2 * F) / w;
  let k = zoom(W);
  if (desk()) {
    const foot = document.querySelector("footer")!, fold = document.body.classList.contains("fold");
    const H = wrap.getBoundingClientRect().bottom - head.bottom - 2 * F;
    if (!fold) barH = foot.getBoundingClientRect().height + parseFloat(getComputedStyle($("page-house")).rowGap || "0");
    const open = zoom(Math.min(W, (fold ? H - barH : H) / h)), shut = zoom(Math.min(W, (fold ? H : H + barH) / h));
    const want = shut > open && !foot.hidden && open * dpr < 3;   // (only when the room would otherwise be small: the visitor's buttons stay out where there is room)
    if (want !== fold && again) { document.body.classList.toggle("fold", want); return layout(false); }
    k = fold || want ? shut : open;
  } else if (innerWidth >= SMALL) k = zoom(Math.min(W, (innerHeight - head.bottom - scrollY - 2 * F - 2) / h));
  $("stage").style.width = `${Math.ceil(w * k)}px`;
  $("stage").style.height = `${Math.ceil(h * k)}px`;
  if (snap) drawMap($("map"), snap, view.room, view.sel, (id) => jump({ room: id }), mapWidth());
  consoleFit();
  marquee($("board"));
}
/** SPEC-v3.5.9 §2: on a short desktop the console gives way a section at a time when its sections do not fit the
 *  window's height: first the room's readout (the header strip says its time and weather), then the map, leaving the
 *  board and the Works; and opens again when they fit. Its button folds and opens it by hand, until the window changes. */
let consoleAt = "", byHand = false;
function consoleFit() {
  const side = $("side"), size = `${innerWidth}x${innerHeight}`;
  if (byHand && size === consoleAt) return;
  byHand = false;
  consoleAt = size;
  side.classList.remove("lean");
  foldConsole(false);
  const over = () => desk() && side.scrollHeight > side.clientHeight + 1;
  if (over()) side.classList.add("lean");
  if (over()) foldConsole(true);
  side.classList.toggle("tight", side.classList.contains("lean"));
}
const foldConsole = (on: boolean) => { $("side").classList.toggle("folded", on); $("consoleFold").setAttribute("aria-expanded", String(!on)); };
const mapWidth = () => Math.min($("mapframe").clientWidth, innerWidth >= 2400 ? 250 : desk() ? 170 : 300);   // (two of the art's pixels to one on a desktop: the board has the rest of the column; on Huge one, which its zoom doubles)
const watch = new ResizeObserver(() => layout());   // a new window, or the toolbar wrapping: measure afresh
for (const e of [document.querySelector("header")!, document.querySelector("footer")!, document.querySelector("main")!, $("replayBar"), $("now"), $("side")]) watch.observe(e);
addEventListener("resize", () => layout());   // (Small: the window's height alone can change the room's zoom)

// ---- which room to show ----

const WEIGHT: Record<string, number> = { hatched: 100, death: 100, egg: 90, ended: 90, befriended: 70, nuzzle: 60, gift: 60, mouse: 60, told: 55,
                                         heirloom: 55, took: 55, room: 50, weak: 50, named: 45, words: 45, stage: 40, leak: 40, draught: 40, lost: 35, floated: 35,
                                         // SPEC-v3.1: a discovery is worth looking at wherever it turns up
                                         "arrival writing": 95, "arrival songs": 95, "arrival taming": 95, "arrival radio": 95, "arrival book": 95, "arrival strangers": 95,
                                         tamed: 65, young: 60, "creature died": 60, scrubbed: 55, crossed: 55, wrote: 50, song: 50, read: 45, untamed: 45 };

/** SPEC-v3.5.7 §2: following the action. Each room is scored by what is happening in it now: a pet making or finding
 *  something out (or about to: carrying bits to make with), pets talking or doing something together, the visitor's
 *  doings, any pet awake. At night, when nobody is awake, the room where most of them sleep. The page changes room at
 *  most once every two real minutes (an event, §4, may take it sooner), never within a minute of the visitor clicking
 *  or typing, and only for a clearly better room. Every change is written down with its reason (`petView.follows`). */
const BUSY = new Set(["made", "discovery", "invented", "first", "found", "best", "works", "built", "process", "combined"]);
const TOGETHER = new Set(["nuzzle", "gift", "told", "taught", "words", "song", "befriended", "played"]);
const VISITOR = new Set(["fed", "stocked", "visitor", "named", "poked", "star", "gave"]);
const follows: { at: number; tick: number; from: string; to: string; why: string }[] = [];
let pending: { room: string; why: string } | null = null;   // an event elsewhere: go there when the visitor has been still a minute
let followNow = false;   // the visitor has just asked to follow the house: go at once
function scores(s: Snap) {
  const out = new Map<string, { n: number; why: string }>();
  const add = (id: string | null | undefined, n: number, why: string) => {
    if (!id || !s.rooms.find((r) => r.id === id)?.type) return;
    const was = out.get(id);
    out.set(id, { n: (was?.n ?? 0) + n, why: was && was.n > n ? was.why : why });
  };
  const up = s.pets.filter((p) => p.stage !== "dead" && p.stage !== "egg" && !p.asleep);
  for (const m of s.moments) {
    const age = ago(s, m.tick);
    if (age > 60) continue;
    if (BUSY.has(m.kind)) add(m.room, 40 - age / 3, `${m.kind === "first" ? "a first" : "something made or found out"} there`);
    else if (TOGETHER.has(m.kind)) add(m.room, 25 - age / 4, "hobs together there");
    else if (VISITOR.has(m.kind)) add(m.room, 15 - age / 6, "the visitor's doings");
  }
  for (const p of up) {
    const act = `${p.act?.type ?? ""} ${p.doing ?? ""}`;
    if (/\b(make|making|process|combine|joining|weaving|build)/.test(act) || (p.carrying?.length ?? 0) >= 2) add(p.room, 30, `${p.label} making something`);
    if (p.said && p.said.to && p.said.to !== "visitor") add(p.room, 25, `${p.label} talking`);
    add(p.room, 10, "a hob awake");
  }
  for (const r of new Set(up.map((p) => p.room))) {
    const n = up.filter((p) => p.room === r).length;
    if (n > 1) add(r, 8 * (n - 1), "hobs together there");
  }
  if (!up.length) {   // night: where most of them sleep
    for (const p of s.pets.filter((p) => p.stage !== "dead")) add(p.room, p.stage === "egg" ? 1 : 3, "where they sleep");
  }
  return out;
}
function auto(s: Snap) {
  const sc = scores(s), now = performance.now(), mine = sc.get(view.room)?.n ?? -1;
  const best = [...sc].sort((a, b) => b[1].n - a[1].n)[0];
  const still = followNow || Date.now() - lastInput > 60_000, due = followNow || now - autoAt > 120_000, first = !looked;
  followNow = false;
  looked = true;
  let to: { room: string; why: string } | null = null;
  if (pending && pending.room !== view.room && still) to = pending;
  // (at most once in two minutes, for a clearly better room; but the page's first look goes straight to the best room,
  // whatever room it was left on: SPEC-v3.5.10 §7, a page opens where a hob is awake)
  else if (best && best[0] !== view.room && (first ? best[1].n > mine : still && !banners.showing && due && best[1].n >= mine + 10)) to = { room: best[0], why: best[1].why };
  if (pending && (pending.room === view.room || to)) pending = null;
  if (!to) return view.room;
  follows.push({ at: Date.now(), tick: s.tick, from: view.room, to: to.room, why: to.why });
  autoAt = now;
  return to.room;
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
  raw = live.snap = s;
  noteInvented(s.invented);   // SPEC-v3.5 §3: the kinds the house invented are drawn from their parts
  snap = { ...s, ...tweak, clock: { ...s.clock, ...((tweak.clock as object) ?? {}) }, lineage: { ...s.lineage, ...((tweak.lineage as object) ?? {}) } };
  snap.pets = snap.pets.map((p) => (p.label === "the little one" ? { ...p, label: ownLabel(p) } : p));   // a recording from before unnamed pets had labels of their own
  if (!ready) {
    const id = view.follow === "auto" ? [...scores(s)].sort((a, b) => b[1].n - a[1].n)[0]?.[0] : pet(view.follow)?.room, name = s.rooms.find((r) => r.id === (id ?? view.room) && r.type)?.name;   // (where the first look will go)
    if (name) $("stage").dataset.name = name;
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
  if (!rooms.some((r) => r.id === view.room)) view.room = (s.pets.find((p) => p.stage !== "dead" && p.stage !== "egg" && !p.asleep) ?? s.pets.find((p) => p.stage !== "dead"))?.room ?? s.start;
  if (!pet(view.sel)) view.sel = (view.follow !== "auto" && followed ? followed : s.pets.find((p) => p.stage !== "dead" && p.room === view.room) ?? s.pets.find((p) => p.stage !== "dead"))?.id ?? null;
  const here = rooms.find((r) => r.id === view.room)!;
  if (picked && !here.objects[picked]) picked = null;
  if (sent !== view.room) presence();
  sent = view.room;
  for (const [k, v] of Object.entries({ room: view.room, sel: view.sel ?? "" })) remember(k, v);

  world(s);   // SPEC-v3.5.9 §3: the world outside, behind the page
  voice.update(s, view.room, view.sel);
  radioSound(s, view.room, voice, !!replayId);   // SPEC-v3.5.1 §5: the station plays here while the radio is on
  screens(s, view.room);
  const burst = bursts(s);
  header(s);
  wipe(here.id);
  try {
    try { room.update({ snap: s, room: here, hello, selected: view.sel, picked, replay: !!replayId }); }
    catch (e) { console.error("room: drawing the room failed; the page goes on", e); }   // (v3.5.10: never the whole page for one part)
    for (const b of burst) if (b.room === view.room) room.burst(b.pet, b.kind);
    $("stage").classList.remove("loading");
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
  // SPEC-v3.5.7 §4: the big moments (a house or family first, an ambition reached, the Works building, a birth, a death,
  // the visitor's star) each get a banner of their own, queued; the rest keep the small one
  const big = (m: Moment) => !replayId && !!classify(s, m);
  const say = (m: Moment) => flash(m.kind === "project" ? m.text.split(":")[0] : m.text, false, () => jump(m), m.kind);   // a project's own words are long, and are in the list beside the room
  if (jumped) { $("banner").hidden = true; bannerN = newest?.n ?? 0; }
  else if (newest && newest.n !== bannerN) {
    // (a want met or a thing found out has the top line of the page: the banner does not say it a second time)
    const all = bannerN >= 0 ? s.moments.filter((m) => m.n > bannerN) : [];
    for (const m of all) { const ev = big(m) ? classify(s, m) : null; if (ev) banners.push(ev); }
    const fresh = all.filter((m) => !big(m) && !s.bursts?.some((b) => b.tick === m.tick && b.text === m.text));
    // a death is never old news: one from the last few minutes of the watcher's time is announced even on first load
    const died = bannerN < 0 && !replayId ? [...s.moments].reverse().find((m) => m.kind === "death" && ago(s, m.tick) < 600) : undefined;
    if (died) { const ev = classify(s, died); if (ev) banners.push(ev); }
    const m = [...fresh].sort((a, b) => rank(b) - rank(a))[0];
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
/** SPEC-v3.5.7 §4: an event in another room takes the page there first, when it follows the house and the visitor has
 *  been still a minute (§2); it is written down with the other room changes. */
const banners = new Banners($("event"), (p) => nameOf(p), (ev: Ev) => {
  if (!ev.room || ev.room === view.room || view.follow !== "auto" || Date.now() - lastInput < 60_000) return;
  follows.push({ at: Date.now(), tick: snap?.tick ?? 0, from: view.room, to: ev.room, why: `event: ${ev.head.toLowerCase()}` });
  view.room = ev.room;
  autoAt = performance.now();
  render();
}, (k) => play(k));
initUiSound(() => voice.on, () => voice.volume);
/** SPEC-v3.5.7 §2: a room change is a short pixel wipe, not a cut (none with reduced motion) */
let drawnRoom = "";
function wipe(to: string) {
  if (drawnRoom && drawnRoom !== to && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const st = $("stage");
    st.classList.remove("wipe");
    void st.offsetWidth;
    st.classList.add("wipe");
    setTimeout(() => st.classList.remove("wipe"), 600);
  }
  drawnRoom = to;
}
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
  document.body.dataset.season = s.clock.season ?? "";   // SPEC-v3.5.9 §7: the frames pick up a touch of the season
  const eve = evening(s.clock.hour); document.body.toggleAttribute("data-eve", eve > 0.02); document.body.style.setProperty("--eve", eve.toFixed(2));   // v3.5.10 §1: ... and of the evening (skin.css)
  $("clock").replaceChildren(`day ${s.clock.day} - ${hhmm(s.clock.hour)}`, el("br"), `${s.clock.season ?? ""}${s.clock.phase === "night" ? " night" : ""} - year ${s.clock.year}`);
  const alive = s.pets.filter((p) => p.stage !== "dead");
  // how many families live here and how many are alive in each, each family in its colour (SPEC-v3.1 §7.4)
  const fams = [...new Set(alive.map((p) => p.family ?? 1))].sort(), NTH = ["", "first", "second", "third"];
  const count = (who: PetV[], eggs = who.filter((p) => p.stage === "egg").length) => `${plural(who.length - eggs, "hob")} alive${eggs ? `, ${eggs} in the egg` : ""}`;
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
    // SPEC-v3.5.6 §4: each pet's name in its family's colour
    const who = s.pets.filter((p) => p.stage !== "egg" && p.label).sort((a, b) => b.label.length - a.label.length);
    const names = (t: string): (Node | string)[] => {
      const p = who.find((q) => t.includes(cap(q.label)) || t.includes(q.label));
      if (!p) return [t];
      const said = t.includes(cap(p.label)) ? cap(p.label) : p.label, i = t.indexOf(said);
      return [...names(t.slice(0, i)), el("b", `who ${fam(p.family)}`, said), ...names(t.slice(i + said.length))];
    };
    line.replaceChildren(...(lead ? [...names(here), el("span", "here", ...names(text))] : [...(got?.kind === "find" ? [icon("star")] : []), ...names(text), ...(here ? [el("span", "here", ...names(here))] : [])]));
    now.className = got ? got.kind : "";
    now.classList.toggle("long", line.scrollHeight > now.clientHeight);   // more than the box holds: set smaller
    if (line.scrollHeight > now.clientHeight) line.querySelector(".here")?.remove();   // still more: the engine's sentence alone (SPEC-v3.5.9: and past three lines, cut)
  }
  dj(s);
  stock(s);
  followChip(s);
}

/** Beside the room: where this is and what the sky is doing, the map, what is going on in the house, and the last few moments. */
function side(s: Snap, here: RoomV) {
  const c = s.clock, name = (id: string | null) => s.rooms.find((r) => r.id === id)?.name ?? "the house";
  // SPEC-v3.5.7 §3: THE ROOM, a readout: the time in amber digits, the day, the sky, the light, who is here
  $("roomTitle").firstChild!.textContent = here.name.toUpperCase();
  $("mapNote").textContent = `ON SCREEN: ${here.name.toUpperCase()} - TAP A ROOM TO LOOK IN`;   // (v3.5.8: a phone's map says what it is for; it has no hover)
  const lit = !s.power ? "DARK: THE POWER IS OUT" : c.phase === "night" ? (Object.values(here.objects).some((o) => o.fix?.light && o.state === "on") ? "LAMPLIGHT" : "DARK") : c.phase === "day" ? "BRIGHT" : "DIM";
  const pets = s.pets.filter((p) => p.room === here.id && p.stage !== "dead" && p.stage !== "egg"), beasts = s.creatures.filter((cr) => cr.room === here.id);
  const asleep = pets.filter((p) => p.asleep).length;
  const who = [pets.length ? `${pets.length} ${pets.length === 1 ? "HOB" : "HOBS"}${asleep ? ` (${asleep === pets.length ? "ASLEEP" : `${asleep} ASLEEP`})` : ""}` : "NOBODY",
    ...Object.entries(beasts.reduce<Record<string, number>>((n, b) => ({ ...n, [b.kind]: (n[b.kind] ?? 0) + 1 }), {})).map(([k, n]) => `${n} ${k.toUpperCase()}${n > 1 ? "S" : ""}`)].join(", ");
  const row = (k: string, ...v: (Node | string)[]) => [el("b", "", k), el("span", "", ...v)];
  $("sky").replaceChildren(el("div", "read",
    ...row("TIME", el("span", "digit", hhmm(c.hour)), ` DAY ${c.day}`),
    ...row("SKY", `${c.season}, ${s.weather}`.toUpperCase()),
    ...row("LIGHT", lit),
    ...row("HERE", who),
    // SPEC-v3.3 §2: how the room is kept, in the pets' own words, when things lie about in it
    ...(here.mess === 2 ? row("ROOM", `${(here.mess_says ?? "a mess").toUpperCase()}`) : [])));   // (only a real mess: the readout stays short)
  // SPEC-v3.5.9 §1: the room's header strip: its name, the house time in amber digits, the weather and the season
  if ($("roomName").textContent !== here.name.toUpperCase()) $("roomName").textContent = here.name.toUpperCase();
  const tod = c.hour >= 20 || c.hour < 5 ? "moon" : c.hour < 8 ? "sunrise" : c.hour < 17 ? "sun" : "sunset";   // v3.5.10 §1: the time of day, and the weather beside it when there is any
  const wx = s.weather === "clear" ? "" : s.weather === "fog" ? "cloud" : s.weather, whenKey = `${hhmm(c.hour)}|${tod}|${wx}|${c.season}`;
  if ($("roomWhen").dataset.key !== whenKey) {
    $("roomWhen").dataset.key = whenKey;
    const sky = el("span", "wx", icon(tod, 24), ...(wx ? [icon(wx, 24)] : []));
    sky.title = `${tod === "moon" ? "night" : tod}, ${s.weather}`;
    sky.setAttribute("role", "img");
    sky.setAttribute("aria-label", sky.title);
    $("roomWhen").replaceChildren(el("span", "digit", hhmm(c.hour)), sky, el("span", "season", (c.season ?? "").toUpperCase()));
  }
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
    ...s.creatures.map((cr) => line("", cr.tame ? "paw" : cr.kind === "sweeper" ? "sweeper" : "mouse", `${beast(cr)} in ${name(cr.room)}, ${cr.doing}`, cr.room)),
  );
  board(s);
  consoleFit();   // (the Works' lines come and go: whether the console's sections fit is asked again)
}

/** SPEC-v3.5.7 §3, v3.5.9 §6: THE BOARD, an LED panel in VT323 to be read at a glance: one of its lines at a time, on
 *  at most two rows (it wraps between words), the newest amber with its blinking block cursor and the others a
 *  brighter blue, each in turn every few seconds. A line longer than two rows steps up a row at a time (slower with
 *  reduced motion). A new line types itself in and the panel pulses. And THE WORKS: the
 *  goal, its count and a segmented meter that fills cell by cell, with a chime and a flash when it is reached. */
let boardLines: string[] = [], typing: ReturnType<typeof setInterval> | undefined, paging: ReturnType<typeof setTimeout> | undefined, worksHad: [number, number] | null = null;
const PAGE = 5000, PAUSE = 2500;   // ms a line stays; ms a long line rests on each of its rows
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
function board(s: Snap) {
  const B = s.ticker?.board ?? [], hubRoom = s.ticker?.room ?? null, box = $("board");
  const lines = B.filter((l) => !l.meter).map((l) => boardRows(l).join(": ").toUpperCase()), key = JSON.stringify(lines);   // ("WHAT: WHO")
  box.hidden = !lines.length;
  box.onclick = hubRoom ? () => jump({ room: hubRoom }) : null;
  if (box.dataset.key !== key) {
    const fresh = !!box.dataset.key && lines[0] !== boardLines[0];
    box.dataset.key = key;
    boardLines = lines;
    page(box, 0, fresh && !calm());
  }
  works(s, B.find((l) => l.meter) ?? null, calm());
}
/** Line `i` of the board, for a few seconds or as long as it takes to scroll through once; then the next. */
function page(box: HTMLElement, i: number, typed = false) {
  clearTimeout(paging);
  clearInterval(typing);
  const n = boardLines.length, text = boardLines[i % n];
  if (!n) return box.replaceChildren();
  // (SPEC-v3.5.10 §4: the last word before the colon goes with the name, so a row never ends on "SOAKED A REED:")
  const at = text.lastIndexOf(": "), cut = at < 0 ? 0 : text.lastIndexOf(" ", at - 1) + 1, [what, who] = [text.slice(0, cut), text.slice(cut).replace(": ", ":\u00a0")];
  const p = el("p", i % n ? "" : "a", el("span", "txt", what, el("span", "by", who, i % n ? null : el("i", "cur"))));
  box.replaceChildren(p);
  const next = (pass: number) => { if (n > 1) paging = setTimeout(() => page(box, i + 1), Math.max(PAGE * (calm() ? 2 : 1), pass)); };
  if (!typed) return next(scroll(p));
  box.classList.remove("pulse"); void box.offsetWidth; box.classList.add("pulse");   // a new line types itself in, and the panel pulses
  const [txt, by, cur] = [p.firstElementChild!, p.querySelector(".by")!, p.querySelector(".cur")!];
  txt.replaceChildren(by);
  by.replaceChildren(cur);
  let k = 0;
  typing = setInterval(() => {   // (what it is first, then who, the cursor after the last letter typed)
    k++;
    txt.replaceChildren(what.slice(0, k), by);
    by.replaceChildren(who.slice(0, Math.max(0, k - what.length)), cur);
    if (k >= text.length) { clearInterval(typing); next(scroll(p)); }
  }, 45);
}
/** A line longer than its two rows steps up a whole row at a time (by position: see skin.css), resting on each, and
 *  back to its start, round and round, so no row is ever shown cut (SPEC-v3.5.10 §4); how long one pass takes, in ms
 *  (0 when it fits). */
function scroll(p: HTMLElement) {
  const t = p.querySelector<HTMLElement>(".txt")!, row = parseFloat(getComputedStyle(t).lineHeight), steps = Math.round((t.scrollHeight - p.clientHeight) / row);
  t.getAnimations().forEach((a) => a.cancel());
  if (steps < 1 || !p.clientHeight) return 0;
  const all = (steps + 1) * PAUSE * (calm() ? 2 : 1);
  t.animate([{ top: "0px" }, { top: `${-steps * row}px` }], { duration: all, iterations: Infinity, easing: `steps(${steps + 1}, jump-none)` });
  return all;
}
/** After a layout, and once the LED face is in (before, a line measures short): the line on show measured again. */
function marquee(box: HTMLElement) {
  requestAnimationFrame(() => box.querySelectorAll<HTMLElement>("p").forEach(scroll));
}
void document.fonts.ready.then(() => marquee($("board")));
document.fonts.addEventListener("loadingdone", () => marquee($("board")));   // (the LED face can come in later than `ready`: a line measured in another face scrolled by the wrong rows)
function works(s: Snap, w: BoardLine | null, still: boolean) {
  const box = $("works");
  box.closest<HTMLElement>(".cworks")!.hidden = !w;
  if (!w?.meter) return;
  const [have, of] = w.meter, n = Math.min(of, 30), on = Math.round((Math.min(have, of) / of) * n), key = `${have}/${of}|${w.what}`;
  if (box.dataset.key === key) return;
  const grew = worksHad && worksHad[1] === of && have > worksHad[0], done = worksHad && (have >= of || (worksHad[1] !== of && worksHad[0] > 0));
  const was = worksHad && worksHad[1] === of ? Math.round((Math.min(worksHad[0], of) / of) * n) : on;
  box.dataset.key = key;
  worksHad = [have, of];
  const cells = Array.from({ length: n }, (_, i) => el("i", i < (still ? on : was) ? "on" : ""));
  // SPEC-v3.5.9 §5: the goal, then its count ("18 OF 30 SCRAP"), then the meter
  box.replaceChildren(...(w.what ? [el("p", "goal", w.what.toUpperCase())] : []), el("p", "count", `${have} OF ${of} SCRAP`), el("div", "meter-cells", ...cells));
  if (grew && !still) cells.slice(was, on).forEach((c, i) => setTimeout(() => c.classList.add("on", "new"), 180 * (i + 1)));   // cell by cell
  else cells.slice(0, on).forEach((c) => c.classList.add("on"));
  if (done) { box.classList.remove("reached"); void box.offsetWidth; box.classList.add("reached"); play("chime"); }
}

/** A creature in a few words: "a moth"; once tame, whose it is and what it is called (SPEC-v3.1 §4.4). Never how far it trusts anyone. */
function beast(c: Creature) {
  const owner = pet(c.tame)?.label;
  return c.name ? `${c.name}${owner ? `, ${owner}'s ${c.kind},` : ` the ${c.kind}`}` : `a ${c.kind}${owner ? `, tame to ${owner},` : ""}`;
}

/** A card for every living pet and every egg (SPEC-v3.2 §7, v3.5.6 §4, §5): its portrait, name in its family's colour,
 *  stage, what it is doing, what it wants, and three Wood bars (energy, curiosity, company) in place of the feeling
 *  words; the feeling stays as its small picture. Those in the room on screen first, in full; the rest after, which a
 *  desktop shows as a line each (portrait, name, stage, where and what). A card opens the pet's page. Rebuilt only
 *  when what they show changes. */
/** The names the pages show, numbered where a name was used before ("Grey Light II"), from /api/pets: asked for again
 *  every minute, and at once when someone new turns up. Not in a replay (a recorded family is not this house). */
let numbered: Record<string, string> = {}, numberedAt = 0;
async function renumber() {
  numberedAt = Date.now();
  const d = await getJSON<{ pets: { id: string; name: string }[] }>("/api/pets");
  if (d) { numbered = Object.fromEntries(d.pets.map((p) => [p.id, p.name])); if (snap) cards(snap); }
}
const nameOf = (p: PetV) => (!replayId && numbered[p.id]) || p.label;
const BARS: [Need, string, string][] = [["energy", "energy", ""], ["curiosity", "curious", "blue"], ["company", "company", "red"]];
function cards(s: Snap) {
  const who = s.pets.filter((p) => p.stage !== "dead").sort((a, b) => a.laid - b.laid);
  const where = (p: PetV) => s.rooms.find((r) => r.id === p.room)?.name ?? "";
  // the visitor's naming: what was offered, and whether the pet has taken it (said for a quarter of a day after it does)
  const naming = (p: PetV) => !p.naming ? null : !p.naming.took ? `you called it ${p.naming.offered}; waiting to hear`
    : p.naming.at != null && (s.tick - p.naming.at) * s.tick_seconds < s.day_seconds / 4 ? `it took the name ${p.naming.offered}` : null;
  const level = (p: PetV, n: Need) => Math.round(p.needs?.[n] ?? 0);
  if (!replayId && (Date.now() - numberedAt > 60_000 || who.some((p) => !numbered[p.id] && Date.now() - numberedAt > 5000))) void renumber();
  const wide = desk(), key = JSON.stringify([view.room, wide, who.map((p) => [naming(p), p.id, nameOf(p), p.byname, p.stage, p.room, p.stage === "egg" ? hatchWords(p.hatches_in ?? 0) : [moodWords(p), emoteOf(p), doingOf(p), wishOf(p), p.body?.icon, p.asleep, p.wants?.map((w) => w.text), p.ambition], p.genome, p.id === view.sel, p.family])]);
  // SPEC-v3.5.7 §9: the bars are kept between snapshots and fill smoothly; a jump of a tenth or more flashes
  const bars = () => {
    for (const p of who) for (const [i, [n]] of BARS.entries()) {
      const b = document.querySelectorAll<HTMLElement>(`.cards .card[data-pet="${p.id}"] .wbar > i`)[i];
      if (!b) continue;
      const v = level(p, n), was = Number(b.dataset.v ?? v);
      b.style.width = `${v}%`;
      b.dataset.v = String(v);
      const w = b.parentElement!, jump = Math.abs(v - was) >= 10, up = v - was >= 3;   // (SPEC-v3.5.9 §7: a need that rises ticks its bar up)
      if (jump || up) { w.classList.remove("jump", "up"); void w.offsetWidth; w.classList.toggle("jump", jump); w.classList.toggle("up", up); }
    }
  };
  if ($("cardsHere").dataset.key === key) return bars();
  $("cardsHere").dataset.key = key;
  const one = (p: PetV) => {
    const egg = p.stage === "egg", emote = egg ? null : emoteOf(p), doing = p.asleep ? "asleep" : doingOf(p);
    const feels = emote ? sprite(`emote.${emote}`, 1) : null;
    const sign = !egg && !p.asleep && p.body?.icon && hasSprite(`icon.act.${p.body.icon}`) ? sprite(`icon.act.${p.body.icon}`, 1) : null;   // SPEC-v3.3 §1: the sign of what its body is doing
    const wish = wishOf(p), wants = (p.wants ?? []).map((w) => wantWords(w.text));
    const want = wants[0]?.replace(/^.*\bit wants /, "").replace(/^wants /, "") ?? wish;
    if (feels) feels.title = `feeling ${emote}`;
    const pic = face(p, wide && p.room !== view.room ? 32 : 48);   // (a desktop's line for one elsewhere has a small portrait, drawn at its size)
    if (!egg) { blinks.set(pic, p); pic.style.animationDelay = `${-(Math.random() * 3.4).toFixed(2)}s`; if (p.asleep) eyes(pic, p, true); }   // SPEC-v3.5.9 §7: it lives
    const li = el("li", `card ${fam(p.family)}${p.id === view.sel ? " chosen" : ""}${egg ? " egg" : ""}${p.asleep && !egg ? " asleep" : ""}${p.room === view.room ? " here" : " away"}`,
      el("span", "pic", pic),
      el("span", "wholine", el("span", "n", egg ? p.name ?? "An egg" : nameOf(p)), egg ? null : byname(p) && el("span", "bn", byname(p)), el("span", "s", stageWord(p), feels)),   // (SPEC-v3.5.8 §6: its by-name under its name)
      egg ? el("span", "doing", hatchWords(p.hatches_in ?? 0)) : null,
      naming(p) ? el("span", "naming", naming(p)!) : null,
      !egg && doing ? el("span", "doing", sign, doing) : null,
      !egg ? el("span", "where", `${doing || "awake"} in ${where(p)}`) : null,
      !egg && want ? el("span", "want", `wants: ${want}`) : null,
      egg || !p.needs ? null : el("span", "bars", ...BARS.flatMap(([n, word, cls]) => [el("span", "", word), el("span", `wbar ${cls}`, el("i", "", ""))])));
    li.dataset.pet = p.id;
    li.querySelectorAll<HTMLElement>(".wbar > i").forEach((b, i) => { b.style.width = `${level(p, BARS[i][0])}%`; b.dataset.v = String(level(p, BARS[i][0])); });
    li.tabIndex = 0;
    li.setAttribute("role", "link");
    li.title = `${egg ? "This egg" : nameOf(p)}'s page. It is in ${where(p)}; ${moodWords(p).join(", ") || "content"}` + (wish && !egg ? `\nIt wants: ${wish}` : "")
      + (p.focus?.words && !p.asleep ? `\nIts mind is on: ${p.focus.words}` : "") + wants.map((w) => `\n${w.startsWith("wants ") ? `It ${w}` : cap(w)}`).join("")
      + (p.ambition && !egg ? `\nIt means in its life to ${p.ambition}` : "") + (p.habits?.length ? `\nIts habits: ${p.habits.join("; ")}` : "");
    li.onclick = () => go("pet", p.id);
    li.onkeydown = (e) => { if (e.target === li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); li.click(); } };
    return li;
  };
  const here = who.filter((p) => p.room === view.room), away = who.filter((p) => p.room !== view.room);
  $("cardsHere").replaceChildren(...(here.length ? here.map(one) : [el("li", "empty-house", who.length ? "Nobody is in this room just now." : "Nobody is alive in the house.")]));
  $("cardsElse").replaceChildren(...away.map(one));
  $("cardsElse").previousElementSibling!.toggleAttribute("hidden", !away.length);
}

/** SPEC-v3.5.9 §7: living cards. A portrait breathes (skin.css) and now and then blinks; asleep, its eyes stay shut. */
const blinks = new WeakMap<HTMLCanvasElement, PetV>();
setInterval(() => {
  for (const c of document.querySelectorAll<HTMLCanvasElement>(".cards .card:not(.asleep, .egg) .pic canvas.face")) {
    const p = blinks.get(c);
    if (!p || Math.random() > 0.07) continue;   // (about once in thirteen seconds each)
    eyes(c, p, true);
    setTimeout(() => eyes(c, p, false), 150);
  }
}, 900);

// ---- the visitor (§7.5): acts only in the room being looked at ----

function controls(s: Snap, here: RoomV) {
  const over = s.lineage.ended != null, objs = Object.values(here.objects);
  $("controls").hidden = !!replayId || over;
  $("ended").hidden = !!replayId || !over;
  document.querySelector("footer")!.hidden = !!replayId;
  $("chosen").hidden = !!replayId || over;   // (v3.5.6: naming sits beside the cards now, not in the footer)
  $("chosen").classList.toggle("asked", !!picked || clicked === view.sel);   // (a desktop shows it once a pet or a thing has been clicked in the room)
  if (replayId || over) return;
  // a control that cannot be used here says why: in its own words where it can, and in its title
  const set = (id: string, off: boolean, why: string, text?: string) => { const b = $<HTMLButtonElement>(id); b.disabled = off; b.title = off ? why : ""; if (text) b.textContent = text; };
  const win = objs.find((o) => o.fix?.window), bowl = objs.some((o) => o.fix && "meal" in o.fix);
  set("feed", !bowl, `There is no bowl in ${here.name} to fill.`, "Feed");   // (v3.5.7: short words on the buttons; a greyed button says why in its title)
  set("window", !win, `There is no window in ${here.name}.`, "Window");
  $("window").setAttribute("aria-pressed", String(win?.state === "open"));
  if (win) $("window").title = win.state === "open" ? "The window is open: close it" : "Open the window";
  const give = $<HTMLSelectElement>("giveBit");
  if (!give.options.length && hello) give.replaceChildren(...Object.keys(hello.bits).sort().map((b) => new Option(b)));
  const p = pet(view.sel), near = p && p.room === here.id && p.stage !== "egg" && p.stage !== "dead" ? p : null;
  const foundling = p && p.room === here.id && p.stage === "egg" && !p.parent && !p.name ? p : null;   // an egg that is nobody's can be given a name (SPEC-v3.1 §7.1)
  const thing = picked ? here.objects[picked] : null, can = thing ? !!thing.made : !!(near || foundling);
  // which hob the buttons act on (the v3.5.7 review): its face and name at the head of the toolbar
  const on = $("actsOn"), onKey = p ? `${p.id}|${nameOf(p)}|${p.stage}|${p.family}|${p.room === here.id}` : "";
  if (on.dataset.key !== onKey || !on.childElementCount) {
    on.dataset.key = onKey;
    on.replaceChildren(...(p ? [face(p, 28), el("b", `who ${fam(p.family)}`, nameOf(p))] : [el("span", "hint", "no hob chosen")]));
    on.title = p ? `${nameOf(p)} is chosen: Poke and Name act on ${p.stage === "egg" ? "it" : nameOf(p)}${p.room === here.id ? "" : ` (in ${s.rooms.find((r) => r.id === p.room)?.name ?? "another room"})`}. Click another hob, or its card, to choose it.`
      : "Click a hob in the room, or its card, to choose it.";
  }
  $("chosenWhat").textContent = thing ? `the ${picked}: click a tile to move it` : near ? near.label : foundling ? (foundling.family === 2 ? "the egg that is nobody's" : "the first egg") : "no one chosen";
  $("chosenWhat").classList.toggle("none", !thing && !near && !foundling);
  $("chosenWhat").title = thing || near || foundling ? "" : "Click a hob in this room, or its card, to poke or name it; click a thing a hob made to move or name it.";
  set("poke", !!thing || !near, thing ? "A thing cannot be poked. Let go of it first (×)." : "Choose a hob in this room first: click it, or its card.");
  set("nameBtn", !can, thing ? "Only a thing a hob has made can be given a name." : "Choose a hob in this room, or a thing a hob made, to name it.");
  $<HTMLInputElement>("nameText").disabled = !can;
  $<HTMLInputElement>("nameText").title = $("nameBtn").title;
  $("chosenDone").hidden = !thing;
  const star = $<HTMLButtonElement>("starBtn");   // SPEC-v3.5.4 §10: the visitor's star, one to a thing
  star.hidden = !thing?.made;
  star.disabled = !!thing?.made?.star;
  star.textContent = thing?.made?.star ? "★ Starred" : "★ Star";
  const page = $<HTMLAnchorElement>("thingPage"), tm = thing?.made as { id?: number; tick?: number } | undefined;   // SPEC-v3.5.7 §5: the picked thing's page
  page.hidden = !tm;
  if (tm && picked) page.href = `#/thing/${encodeURIComponent(tm.id != null ? String(tm.id) : `g${tm.tick}-${picked.replace(/\W+/g, "-")}`)}`;
  $("room").classList.toggle("placing", !!thing);
}

/** "Stock the machine" (SPEC-v3.5 §4.3), in the header: what the vending machine holds, a material to a row, and a
 *  button to put one more of it in (or fill it), up to its limit. It works whichever room is on screen. */
function stock(s: Snap) {
  const m = s.machine, btn = $<HTMLButtonElement>("stockBtn"), box = $("stockBox"), key = JSON.stringify(m ?? null);
  btn.hidden = !!replayId || s.lineage.ended != null;
  btn.disabled = !m;
  btn.title = m ? "Put wood, stone, metal, clay, fibre or sand in the vending machine. The hobs take from it, two a day each." : "Nobody has found the machine room yet: the vending machine is in it.";
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
  $("radioWho").parentElement!.title = d.radio.theirs ? "The hobs' own radio: this switches it on or off and says what it plays, wherever it is. They can still switch it themselves."
    : "Your own little radio, set down in the room you are looking at while it is on. Once the hobs have found a radio of their own, this switches theirs.";
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
  } else if (t.pet) { clicked = t.pet; jump({ pet: t.pet }); }
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
  keepsake: "anything kept in it can be taken out again, by any hob",   // (what it is for, its own words say)
  machine: "it gives each hob two materials a day, of its choosing; fed a made thing, or three bits, it gives one back; it never takes an heirloom or what is someone else's",
  radio: "while it is on it plays a real radio station, which you hear too", book: "it answers a question put to it, out of an encyclopedia",
};

function fixture(name: string, o: Obj, here: RoomV, s: Snap, shown: HTMLCanvasElement | null, notes: Kid): Kid[] {
  const pic = [`fix.${name}.${o.state}`, `fix.${name}`].find(hasSprite), fix = o.fix ?? {};
  const state = o.state === "ripe" ? "ripe" : o.grow != null ? (o.grow > 0.7 ? "nearly ripe" : "growing") : o.servings != null ? (o.servings ? `${o.servings} left in it` : "empty") : o.state ?? "";
  const does = Object.keys(FIX).filter((k) => k in fix && fix[k]).map((k) => FIX[k]);
  const slot = o.on && here.objects[o.on]?.fix?.memory && hasSprite("fix.little wooden keepsake box");   // SPEC-v3.5.12 §4: a box on a memory shelf is drawn as a small slot there; its card shows it whole
  return [roomCard(slot ? sprite("fix.little wooden keepsake box", 3) : shown ?? (pic ? sprite(pic, 3) : null), [o.build?.title ?? `the ${name}`], [o.says ? cap(o.says) : "", state ? `${o.says ? " · " : ""}${state}` : ""],
    notes,
    fix.book && s.read_glow ? el("p", "", "Someone is reading it.") : null,
    ...(does.length ? [sec("What it really does"), el("p", "", `${cap(does.join("; "))}.`)] : []),
    ...(here.marks ?? []).filter((m) => m.on === name).flatMap(written),
    fix.movable && !replayId ? el("p", "tchint", "click to move it") : null)];
}

/** The room's own picture of what is under the pointer, exactly as it is drawn there (its colour, its wear), as large
 *  as the card's picture slot takes it (at most four screen pixels to one). The room offers it through `describe`;
 *  without that, the card looks the picture up itself. */
const told = (t: Target) => room.describe(t);
/** SPEC-v3.3 §2: the room's own lines about how a thing is kept (what it holds, where it is put away, its home, the
 *  corner it stands in), as rows: "holds | a white bowl, …". */
const kept = (t: Target) => rows((told(t)?.notes ?? []).map((n): [string, Kid[]] => { const i = n.indexOf(": "); return i < 0 ? ["", [n]] : [n.slice(0, i), [n.slice(i + 2)]]; }));
function drawn(t: Target): HTMLCanvasElement | null {
  const src = told(t)?.sprite;
  if (!src?.width) return null;
  const c = el("canvas", "px") as HTMLCanvasElement, x = c.getContext("2d")!, k = Math.max(1, Math.min(4, Math.floor(96 / Math.max(src.width, src.height))));
  [c.width, c.height] = [src.width * k, src.height * k];
  x.imageSmoothingEnabled = false;
  x.drawImage(src, 0, 0, c.width, c.height);
  return c;
}

/** SPEC-v3.5.10 §2: every hover card in the room is the Things panel's card (thingcard.ts): a made thing's own, and for
 *  anything else the same paper, slot and lines (roomCard). */
function tipFor(t: Target): Kid[] | null {
  const s = snap, here = s?.rooms.find((r) => r.id === view.room);
  if (!s || !here) return null;
  const p = pet(t.pet), c = s.creatures.find((c) => c.id === t.creature), o = t.object ? here.objects[t.object] : null;
  if (p) {
    const egg = p.stage === "egg", gone = p.stage === "dead", good = goodWord(p), mood = egg || gone ? "" : moodWords(p).join(", ");
    // its whole want, wrapped, as its card has it (the plan's own words are cut short by the house)
    const want = egg || gone ? "" : (p.wants?.length ? wantWords(p.wants[0].text).replace(/^.*\bit wants /, "").replace(/^wants /, "") : wishOf(p));
    return [roomCard(face(p, 96), [egg ? p.name ?? "an egg" : nameOf(p)], [stageWord(p), !egg && byname(p) ? ` · ${byname(p)}` : ""],
      egg ? el("p", "", `${cap(hatchWords(p.hatches_in ?? 0))}.`) : gone ? el("p", "", `${cap(p.label)} has died.`) : null,
      rows([["feeling", [mood && `${mood}${good ? `; and ${good}` : ""}`]], ["now", [egg || gone ? "" : p.asleep ? "asleep" : doingOf(p)]], ["wants", [want]],
        ["carrying", [carried(p).join(", ")]], ["following", [pet(p.following) ? nameOf(pet(p.following)!) : ""]]]))];
  }
  if (c) return [roomCard(drawn(t) ?? (hasSprite(`creature.${c.kind}`) ? sprite(`creature.${c.kind}`, 3) : null), [beast(c).replace(/,$/, "")], [`${cap(c.doing)}.`],
    rows([["carrying", [c.carry ?? ""]]]),
    // SPEC-v3.5.8 §4.2: the sweeper's load, and whether it is full or on its dock
    c.kind === "sweeper" ? el("p", "", c.docked ? "On its dock by the Works, charging." : c.full ? "Full: its green light is blinking, and it is going back to the Works."
      : c.load ? `It has picked up ${plural(c.load, "thing")}.` : "Nothing picked up yet.") : null)];
  if (t.mark) return [roomCard(null, [t.mark.medium === "scratch" ? "words scratched on the wall" : "words in chalk"], [], ...written(t.mark))];
  if (t.door) {
    const to = s.rooms.find((r) => r.id === here.doors[t.door!]), shut = here.shut.includes(t.door), pic = firstSprite(`door.${shut ? "shut" : "open"}`, "door");
    return [roomCard(hasSprite(pic) ? sprite(pic, 3) : null, [to?.type ? `the door to ${to.name}` : "a door nobody has been through"], [shut ? "It has blown shut." : ""],
      to?.type ? rows([["in there", [s.pets.filter((p) => p.room === to.id && !(p.stage === "dead" && p.buried)).map((p) => (p.stage === "egg" ? p.name ?? "an egg" : nameOf(p))).join(", ") || "nobody just now"]]]) : null,   // SPEC-v3.5.9 §7
      to?.type ? el("p", "tchint", "click to look in there") : null)];
  }
  if (o?.made) {   // SPEC-v3.5.7 §5: the thing card (thingcard.ts), filled in from the house's record as it arrives
    const m = o.made as typeof o.made & { id?: number; tick?: number }, key = m.id != null ? String(m.id) : `g${m.tick}-${t.object!.replace(/\W+/g, "-")}`;
    const card = thingCard(key, { name: t.object!, recipe: m.recipe as never, by: m.by, owner: m.owner, uses: m.uses, heirloom: !!m.heirloom, star: m.star ?? null,
      title_shown: m.title_shown, how: m.how, made_in: m.made_in, from: m.from, users: m.users, words: m.words } as never, false);   // (SPEC-v3.5.8 §6: what the house now records)
    return [card, replayId ? null : el("p", "hint cardhint", m.star ? "click to move or name it, or open its page" : "click to move, name or star it, or open its page")];
  }
  if (o?.memorial) return [roomCard(drawn(t) ?? (hasSprite("stone") ? sprite("stone", 3) : null), ["a stone"], [o.memorial.text], kept(t),
    (o.words ?? []).length ? el("blockquote", "tcwords", ...(o.words ?? []).map((w) => el("p", "", `“${w.text}” - written by ${pet(w.pet) ? nameOf(pet(w.pet)!) : "a hob"}, ${when(s, w.tick)}`))) : null,   // SPEC-v3.5.8 §6
    ...(here.marks ?? []).filter((x) => x.on === t.object).flatMap(written))];
  const hub = o && t.object ? hubTip(t.object, o, s, drawn(t)) : null;   // SPEC-v3.5.1: the lit sign, a screen, a statue
  if (hub) return hub;
  if (o && t.object) return fixture(t.object, o, here, s, drawn(t), kept(t));
  if (t.bit) {
    const can = hello?.bits[t.bit]?.can ?? [];
    return [roomCard(drawn(t) ?? (hasSprite(`bit.${t.bit}`) ? sprite(`bit.${t.bit}`, 3) : null), [`some ${t.bit}`], [t.bare ? "It grows here. Nothing to gather just now." : "Something to gather and make things from."],
      ...(can.length ? [sec("What it really does"), el("p", "", `A thing made of it can be ${can.join(" or ")}.`)] : []))];
  }
  // anything else the room can say something about: its own scenery (a bookcase, a barrel) is "part of the room"
  const it = told(t);
  return it ? [roomCard(drawn(t), [it.title], [it.text ? `${cap(it.text)}.` : ""])] : null;
}

/** What a hob carries, for its card (SPEC-v3.5.8 §5): the thing its body has picked up, and its bits. */
const carried = (p: PetV) => [...(p.body?.carrying && p.body.what && !p.asleep ? [`the ${p.body.what}`] : []), ...(p.carrying ?? [])];
let tipTimer: ReturnType<typeof setTimeout> | undefined;
/** Show the card for what is at this place in the room (`fx`, `fy` are how far across and down the room's box it is,
 *  0 to 1). The card stands beside what it describes, never on it, with a small point toward it; it stays inside the
 *  room's walls, and of the four sides it takes the one where it covers least of the pets and their captions. */
let lastCard: [Target | null, number, number] | null = null;
// a thing's card fills itself in after it is placed: placed again when it grows, so it stays within the window
new ResizeObserver(() => { if (!$("tip").hidden && lastCard && $("tip").classList.contains("holdscard")) card(lastCard[0], lastCard[1], lastCard[2], -1); }).observe($("tip"));   // (-1: placed again only; a tap's timer runs on)
function card(t: Target | null, fx: number, fy: number, forMs = 0) {
  lastCard = [t, fx, fy];
  const tip = $("tip"), kids = t ? tipFor(t) : null;
  if (forMs !== -1) clearTimeout(tipTimer);
  tip.hidden = !kids;
  if (!kids) return;
  const key = JSON.stringify([t, t?.object && snap?.rooms.find((r) => r.id === view.room)?.objects[t.object]?.made ? null : snap?.tick]), nib = el("i", "nib");   // (a thing's card is not rebuilt every tick: it fills itself in)
  if (tip.dataset.key !== key) { tip.dataset.key = key; tip.replaceChildren(...kids.filter((k): k is Node => k instanceof Node), nib); }
  // beside the thing itself where the room says where it is drawn; otherwise beside the pointer
  tip.classList.toggle("holdscard", !!tip.querySelector(".thingcard"));
  const stage = $("stage"), { tile, busy, inner: room0 } = roomBoxes(), drawnAt = t ? told(t)?.rect : null;
  // a thing's card is taller than many rooms: it keeps within the window, not the room (SPEC-v3.5.7 §5)
  const sr = stage.getBoundingClientRect(), inner = tip.classList.contains("holdscard") ? { x: 8 - sr.left, y: 8 - sr.top, w: innerWidth - 16, h: innerHeight - 16 } : room0;
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
  if (forMs > 0) tipTimer = setTimeout(() => (tip.hidden = true), forMs);
}
room.onHover = (t, fx, fy) => card(t, fx, fy);

// "Names": the room's own short labels of what every thing in it is, held on while this is pressed (otherwise
// a thing is named only while the pointer is on it). Off by default, and not remembered.
$("namesBtn").onclick = () => {
  const on = $("namesBtn").getAttribute("aria-pressed") !== "true";
  $("namesBtn").setAttribute("aria-pressed", String(on));
  (room as unknown as { names?: (on: boolean) => void }).names?.(on);
};
$("consoleFold").onclick = () => { byHand = true; foldConsole(!$("side").classList.contains("folded")); };   // SPEC-v3.5.7 §3: a phone's console folds to the board
$("visitBtn").onclick = () => $("visitBtn").setAttribute("aria-expanded", String($("visitBtn").getAttribute("aria-expanded") !== "true"));   // SPEC-v3.5.9 §2: the folded toolbar
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
$("talkForm").addEventListener("toggle", (e) => { if ((e as ToggleEvent).newState === "open") $("talkText").focus(); });   // v3.5.10 §5: the "Say..." pop-up opens ready to type
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
/** SPEC-v3.5.7 §2: the chip says what the page follows; its pop-up picks a pet, the house, or nobody. */
function followChip(s: Snap) {
  const p = pet(view.follow), chip = $("followChip");
  const text = view.follow === "auto" ? "FOLLOWING THE HOUSE" : p ? `FOLLOWING ${nameOf(p).toUpperCase()}` : "NOT FOLLOWING";
  if (chip.textContent !== text) chip.textContent = text;
  chip.classList.toggle("off", !view.follow);
  const box = $("followBox"), who = s.pets.filter((q) => q.stage !== "dead" && q.stage !== "egg"), key = JSON.stringify([view.follow, who.map((q) => q.id + nameOf(q))]);
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  const pick = (to: string, label: string, cls = "") => {
    const b = el("button", `${cls}${view.follow === to ? " on" : ""}`, label) as HTMLButtonElement;
    b.onclick = () => { view.follow = to; remember("followPick", to); if (pet(to)) view.sel = to; followNow = to === "auto"; box.hidePopover?.(); render(); };
    return b;
  };
  box.replaceChildren(el("p", "hint", "Follow"), pick("auto", "the house (wherever the action is)"), ...who.map((q) => pick(q.id, nameOf(q), fam(q.family))), pick("", "nobody: stay in this room"));
}
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
  if (r.page === "house") { layout(); render(); }
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
// the text size (Tyler, 15 October): normal or large, kept in this browser only
const textSize = (large: boolean) => {
  if (large) document.documentElement.dataset.text = "large"; else delete document.documentElement.dataset.text;
  $("textBtn").setAttribute("aria-pressed", String(large));
  remember("text", large ? "large" : "normal");
  layout();
};
$("textBtn").setAttribute("aria-pressed", String(document.documentElement.dataset.text === "large"));
$("textBtn").onclick = () => textSize(document.documentElement.dataset.text !== "large");
$("replayBtn").hidden = !!replayId;
$("replayBtn").onclick = () => (location.search = `?replay=${snap?.lineage.id ?? 1}`);
onRoute(showPage);
// SPEC-v3.5.6 §7: a press plays the Wood button's own four frames, then it springs back
addEventListener("pointerdown", (e) => {
  const b = (e.target as HTMLElement).closest?.("button");
  if (b && !b.disabled) play("click");   // SPEC-v3.5.7 §9
  if (!b || b.disabled || getComputedStyle(b).borderImageSource === "none") return;
  let f = 1;
  const step = () => { b.classList.remove("press1", "press2", "press3", "press4"); if (f <= 4) { b.classList.add(`press${f++}`); setTimeout(step, 45); } };
  step();
});
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
  if (e.id === "moments" || e.id === "happening") return false;
  if (e.closest("#board.led")) return false;   // (SPEC-v3.5.7 §3: a board line too long for the panel runs sideways, to be read whole)   // these two show whole lines only: what does not fit is wrapped out of sight on purpose
  if (e.closest(".cards .card")) return false;   // so does a card, which is one height always (SPEC-v3.2, v3.3): the whole of every line is in its hover and in the pet's mind
  return (o.overflowX !== "visible" && o.overflowX !== "auto" && e.scrollWidth > e.clientWidth + 1) || (o.overflowY !== "visible" && o.overflowY !== "auto" && e.scrollHeight > e.clientHeight + 1);
}).map((e) => `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}.${e.className}: ${e.textContent?.slice(0, 40)}`);
Object.assign(window, { petView: {
  lookAt: (id: string) => jump({ room: id }),
  follow: (who: string | null) => { view.follow = who ?? ""; if (pet(who)) view.sel = who; render(); },
  /** SPEC-v3.5.7 §11: every room the page went to by itself, when and why */
  follows: () => follows,
  /** For checks and screenshots: put a moment the house recorded through the banners again, as if it had just happened. */
  replayMoment: (n: number) => { const m = snap?.moments.find((x) => x.n === n); const ev = m && snap ? classify(snap, m) : null; if (ev) banners.push({ ...ev, n: -Date.now() }); return !!ev; },
  select: (id: string) => { view.sel = id; render(); poll(); },
  openTab: (name: string | null, who?: string) => (name ? openTab(name, who) : go("house")),
  go,
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
    follow: view.follow, selected: view.sel, tab: view.page,
    replay: replay?.state() ?? null, ended: snap.lineage.ended != null, petsHere: snap.pets.filter((p) => p.room === view.room && !(p.stage === "dead" && p.buried)).map((p) => p.id),
    creaturesHere: snap.creatures.filter((c) => c.room === view.room).map((c) => c.kind), rooms: found(snap).map((r) => `${r.id}:${r.type}`),
    labels: room.labels(), overlaps: overlaps(), clipped: clipped(), scrolls: document.querySelector("main")!.scrollHeight - document.querySelector("main")!.clientHeight,
    stage: [$("stage").offsetWidth, $("stage").offsetHeight], scale: $("stage").offsetWidth / ((snap.size[0] + 2) * 16),
  },
} });
watchVersion();   // v3.5.10: a page open across a deploy reloads itself
