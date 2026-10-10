// Wiring (SPEC-v3 §10): one websocket to the engine (or a recorded run played back), snapshots in, the visitor's
// actions out. Decides which room is on screen, and keeps that choice across a reload.
import { $, el, radial } from "./dom";
import type { Ctx } from "./dom";
import { showRecord } from "./family";
import { icon } from "./icons";
import { drawMap } from "./minimap";
import { renderDrawer, SOURCE } from "./panels";
import type { Genome, Look } from "./pet";
import { startReplay } from "./replay";
import type { Replay } from "./replay";
import { Room } from "./room";
import type { Target } from "./room";
import { momentRow } from "./story";
import { bodyStage, hhmm } from "./types";
import type { Hello, Moment, PetV, RoomV, Snap } from "./types";

const remember = (key: string, value: string) => { try { localStorage.setItem(key, value); } catch { /* private window */ } };
const recall = (key: string) => { try { return localStorage.getItem(key); } catch { return null; } };

const room = new Room();
const replayId = new URLSearchParams(location.search).get("replay");   // a family's number when a recorded run is being watched
let replay: Replay | null = null;
let raw: Snap | null = null;      // the last snapshot as it came
let snap: Snap | null = null;     // the same with any `tweak` laid over it
let hello: Hello | null = null;
let ready: Promise<void> | null = null;
let sock: WebSocket | null = null;
let lastInput = 0;                // presence needs real input, so a tab that was only opened does not count
let tweak: Record<string, unknown> = {};
// What is on screen. `follow` is "auto", a pet's id, or "" to stay in the room chosen by hand.
const view = { room: recall("room") ?? "", follow: recall("follow") ?? "auto", sel: recall("sel"), tab: recall("tab") ?? "mind", drawer: recall("drawer") === "1" };
let picked: string | null = null; // a thing clicked, waiting for a tile to be moved to or a name
let autoAt = performance.now();   // when "auto" last changed rooms
const api: Record<string, unknown> = {};
const pictures = new Map<string, string>();

const send = (msg: object) => sock?.readyState === WebSocket.OPEN && sock.send(JSON.stringify(msg));
const presence = () => send({ type: "presence", active: document.hasFocus() && Date.now() - lastInput < 5 * 60_000, room: view.room });
const act = (msg: object) => send({ ...msg, room: view.room });
const found = (s: Snap) => s.rooms.filter((r) => r.type);
const pet = (id: string | null | undefined) => snap?.pets.find((p) => p.id === id);

function picture(g: Genome, stage: string, look: Look = {}) {
  const key = JSON.stringify([g, stage, look]);
  if (!pictures.has(key)) pictures.set(key, room.picture(g, stage, look));
  return pictures.get(key)!;
}

const ctx = (): Ctx => ({ snap: snap!, hello, sel: view.sel, room: view.room, replay: !!replayId, api, picture, jump, show: openTab });

/** VOICE (§10.6, phase 2) plugs in here. Every snapshot that reaches the screen passes through, live or replayed,
 *  with the id of the room being looked at. Nothing is wired yet; the header's sound controls wait in index.html. */
function onSnapshot(_snap: Snap, _room: string) {}

// ---- which room to show ----

const WEIGHT: Record<string, number> = { hatched: 100, death: 100, egg: 90, ended: 90, befriended: 70, nuzzle: 60, gift: 60, mouse: 60, told: 55,
                                         heirloom: 55, took: 55, room: 50, weak: 50, named: 45, words: 45, stage: 40, leak: 40, draught: 40, lost: 35, floated: 35 };

/** "Follow: auto" (§10.1): the room where the most is going on. A birth or a death wins at once; otherwise it
 *  takes a clearly better room, and a few seconds since the last move, to look away. */
function auto(s: Snap) {
  const score = new Map<string, number>();
  const add = (id: string | null, n: number) => { if (id && s.rooms.find((r) => r.id === id)?.type) score.set(id, Math.max(score.get(id) ?? 0, n)); };
  for (const m of s.moments) {
    const age = (s.tick - m.tick) * s.tick_seconds;
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
  ready ??= room.init($("room"), s.size[0], s.size[1]);
  await ready;
  render();
}

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

  onSnapshot(s, view.room);
  room.update({ snap: s, room: here, hello, selected: view.sel, picked, replay: !!replayId });
  header(s, here);
  drawMap($("map"), s, view.room, view.sel, (id) => jump({ room: id }));
  side(s);
  cards(s);
  controls(s, here);
  if (view.drawer) renderDrawer(view.tab, ctx());

  // Moments (§9.1): a banner when something worth seeing happens. Not on first load: that would announce old news.
  const newest = s.moments.at(-1);
  if (newest && newest.n !== bannerN) {
    if (bannerN >= 0 && newest.n > bannerN) flash(newest.text, false, () => jump(newest));
    bannerN = newest.n;
  } else if (!newest) bannerN = 0;
}
let sent = "";
let bannerN = -1;
let bannerTimer: ReturnType<typeof setTimeout> | undefined;

function flash(text: string, error = false, go: (() => void) | null = null) {
  const b = $("banner");
  b.textContent = text;
  b.className = error ? "error" : "";
  b.hidden = false;
  b.onclick = () => { b.hidden = true; go?.(); };
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => (b.hidden = true), error ? 5000 : 8000);
}

function header(s: Snap, here: RoomV) {
  const alive = s.pets.filter((p) => p.stage !== "dead"), c = s.clock;
  $("family").textContent = `family ${s.lineage.id} · ${alive.filter((p) => p.stage !== "egg").length} alive${alive.some((p) => p.stage === "egg") ? `, ${alive.filter((p) => p.stage === "egg").length} in the egg` : ""}`;
  const chip = (cls: string, ...kids: (Node | string)[]) => el("span", cls, ...kids);
  $("status").replaceChildren(
    chip("chip", `day ${c.day} · ${hhmm(c.hour)}`),
    ...(s.power ? [] : [chip("chip warn", icon("bolt"), "power cut")]),
    ...(replayId ? [] : [chip(s.visitor ? "chip on" : "chip", s.visitor ? "you are here" : "nobody watching")]),
    ...(s.turbo && !replayId ? [chip("chip", "turbo time")] : []),
  );
  $("roomName").textContent = here.name;
  const pick = $<HTMLSelectElement>("follow"), options = s.pets.filter((p) => p.stage !== "dead");
  const key = options.map((p) => p.id + p.label + p.stage).join();
  if (pick.dataset.key !== key) {
    pick.dataset.key = key;
    pick.replaceChildren(new Option("whatever is happening", "auto"), new Option("nobody: stay in this room", ""), ...options.map((p) => new Option(p.stage === "egg" ? `${p.name ?? "an egg"} (in the egg)` : p.label, p.id)));
  }
  pick.value = view.follow;
}

/** Beside the room: the sky, what is going on in the house, and the last few moments. */
function side(s: Snap) {
  const c = s.clock, name = (id: string | null) => s.rooms.find((r) => r.id === id)?.name ?? "the house";
  $("sky").replaceChildren(icon(c.phase === "night" && s.weather === "clear" ? "moon" : s.weather, 30),
    el("div", "", el("b", "", `${c.season[0].toUpperCase()}${c.season.slice(1)}, ${s.weather}`), el("span", "", `day ${c.day}, ${hhmm(c.hour)}${c.phase === "day" ? "" : ` · ${c.phase}`} · year ${c.year}`)));
  const line = (cls: string, pic: string, text: string, to: string | null) => {
    const li = el("li", cls, icon(pic), text);
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
    ...s.creatures.map((cr) => line("", "mouse", `a ${cr.kind} in ${name(cr.room)}, ${cr.doing}`, cr.room)),
  );
  const key = `${s.moments.at(-1)?.n}`;
  if ($("moments").dataset.key !== key) {
    $("moments").dataset.key = key;
    $("moments").replaceChildren(...[...s.moments].reverse().slice(0, 30).map((m: Moment) => momentRow({ jump }, m, m.day !== c.day)));
  }
}

function clockLeft(sec: number) {
  return sec < 60 ? "under a minute" : `about ${Math.round(sec / 60)} min`;
}

/** A card for every living pet and every egg (§10.1). Rebuilt only when what they show changes. */
function cards(s: Snap) {
  const who = s.pets.filter((p) => p.stage !== "dead").sort((a, b) => a.laid - b.laid);
  const state = (p: PetV) => (p.stage === "egg" ? `hatches in ${clockLeft(p.hatches_in ?? 0)}` : p.asleep ? "asleep" : `seems ${p.seems}`);
  const key = JSON.stringify(who.map((p) => [p.id, p.label, p.stage, p.room, state(p), p.project?.text, p.genome, p.id === view.sel, p.stage === "elder"]));
  const box = $("cards");
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  box.replaceChildren(...(who.length ? who.map((p) => {
    const stage = bodyStage(p), img = el("img", "face") as HTMLImageElement;
    img.src = picture(p.genome, stage, { grey: stage === "elder" ? 0.55 : 0 });
    img.alt = "";
    const b = el("button", `card${p.id === view.sel ? " chosen" : ""}`, img,
      el("div", "", el("b", "", p.stage === "egg" ? p.name ?? "An egg" : p.label, el("small", "", ` ${p.stage} · ${s.rooms.find((r) => r.id === p.room)?.name?.replace(/^the /, "") ?? ""}`)),
        el("span", "seems", state(p)),
        el("span", "", p.stage === "egg" ? `generation ${p.gen}` : p.project ? `“${p.project.text}”` : "no project")),
      radial(p.temper, 34, false)) as HTMLButtonElement;
    b.title = p.project?.text ?? "";
    b.onclick = () => jump({ pet: p.id, room: p.room });
    return el("li", "", b);
  }) : [el("li", "empty-house", "Nobody is alive in the house.")]));
}

// ---- the visitor (§7.5): acts only in the room being looked at ----

function controls(s: Snap, here: RoomV) {
  const over = s.lineage.ended != null, objs = Object.values(here.objects);
  $("controls").hidden = !!replayId || over;
  $("ended").hidden = !!replayId || !over;
  if (replayId || over) return;
  const win = objs.find((o) => o.fix?.window);
  $<HTMLButtonElement>("feed").disabled = !objs.some((o) => o.fix && "meal" in o.fix);
  $<HTMLButtonElement>("window").disabled = !win;
  $("window").textContent = win?.state === "open" ? "Close window" : "Open window";
  const give = $<HTMLSelectElement>("giveBit");
  if (!give.options.length && hello) give.replaceChildren(...Object.keys(hello.bits).sort().map((b) => new Option(b)));
  const p = pet(view.sel), near = p && p.room === here.id && p.stage !== "egg" && p.stage !== "dead" ? p : null;
  const thing = picked ? here.objects[picked] : null;
  $("chosen").hidden = !thing && !near;
  $("chosenWhat").textContent = thing ? `the ${picked}: click a tile to move it` : near ? near.label : "";
  $("poke").hidden = !!thing || !near;
  $("nameForm").hidden = !!thing && !thing.made;
  $("chosenDone").hidden = !thing;
  $("room").classList.toggle("placing", !!thing);
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
};

/** What the pointer is over, in a few words. */
room.onHover = (t, fx, fy) => {
  const tip = $("tip"), here = snap?.rooms.find((r) => r.id === view.room);
  let text = "";
  if (t && snap && here) {
    const p = pet(t.pet), c = snap.creatures.find((c) => c.id === t.creature), o = t.object ? here.objects[t.object] : null;
    if (p) text = p.stage === "egg" ? `${p.name ?? "an egg"}: hatches in ${clockLeft(p.hatches_in ?? 0)}` : p.stage === "dead" ? `${p.label} has died` :
      `${p.label}, ${p.stage}: seems ${p.seems}; ${p.asleep ? "asleep" : p.doing}${p.carrying?.length ? `\ncarrying ${p.carrying.join(", ")}` : ""}${pet(p.following) ? `\nfollowing ${pet(p.following)!.label}` : ""}`;
    else if (c) text = `a ${c.kind}, ${c.doing}`;
    else if (t.door) {
      const to = snap.rooms.find((r) => r.id === here.doors[t.door!]);
      text = (to?.type ? `the door to ${to.name}` : "a door nobody has been through") + (here.shut.includes(t.door) ? ", blown shut" : "");
    } else if (o?.made) text = `${o.made.called ?? t.object}: ${o.made.owner_name ? `${o.made.owner_name}'s` : "nobody's now"}${o.made.heirloom ? ", an heirloom" : ""}\n“${o.made.recipe.purpose}”${replayId ? "" : "\nclick to move or name it"}`;
    else if (o?.memorial) text = o.memorial.text;
    else if (o) text = `${t.object}${o.state === "ripe" ? ", ripe" : o.grow != null ? `, ${Math.round(Math.min(1, o.grow) * 100)}% grown` : o.state ? `, ${o.state}` : ""}${o.fix?.movable && !replayId ? "\nclick to move it" : ""}`;
    else if (t.bit) text = `some ${t.bit}`;
  }
  tip.hidden = !text;
  tip.textContent = text;
  tip.style.left = `${fx * 100}%`;
  tip.style.top = `${fy * 100}%`;
  tip.className = `${fx > 0.66 ? "left" : ""} ${fy > 0.7 ? "up" : ""}`;
};

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

// ---- the drawer: closed by default, so what a pet means to do stays a surprise unless you look ----

/** A tab's extra facts are asked for only while it is open, every few seconds (not every tick). */
async function poll() {
  if (!view.drawer || !snap || document.hidden) return;
  const tab = view.tab, url = SOURCE[tab]?.(ctx());
  if (!url) return;
  try {
    const r = await fetch(url);
    if (r.ok) api[tab] = await r.json();
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
  view.tab = document.querySelector(`[data-tab="${name}"]`) ? name : "mind";
  for (const b of document.querySelectorAll<HTMLElement>("[data-tab]")) b.setAttribute("aria-selected", String(b.dataset.tab === view.tab));
  for (const p of document.querySelectorAll<HTMLElement>("[data-panel]")) p.hidden = p.dataset.panel !== view.tab;
  remember("tab", view.tab);
  if (snap && view.drawer) renderDrawer(view.tab, ctx());
  poll();
}
function openTab(name: string, who?: string) {
  if (who) view.sel = who;
  if (who && name === "family") showRecord(who);
  view.tab = name;
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
Object.assign(window, { petView: {
  lookAt: (id: string) => jump({ room: id }),
  follow: (who: string | null) => { view.follow = who ?? ""; if (pet(who)) view.sel = who; render(); },
  select: (id: string) => { view.sel = id; render(); poll(); },
  openTab: (name: string | null, who?: string) => (name ? openTab(name, who) : setDrawer(false)),
  theme,
  /** Lay something over every snapshot before it is drawn, e.g. {weather: "storm", power: false, clock: {phase: "night"}}. */
  tweak: (over: Record<string, unknown> | null) => { tweak = over ?? {}; if (raw) show(raw); },
  replay: () => replay,
  state: () => snap && {
    tick: snap.tick, clock: snap.clock, weather: snap.weather, power: snap.power, room: view.room, roomType: snap.rooms.find((r) => r.id === view.room)?.type,
    follow: view.follow, selected: view.sel, tab: view.drawer ? view.tab : null, theme: document.documentElement.dataset.theme ?? "system",
    replay: replay?.state() ?? null, ended: snap.lineage.ended != null, petsHere: snap.pets.filter((p) => p.room === view.room && !(p.stage === "dead" && p.buried)).map((p) => p.id),
    creaturesHere: snap.creatures.filter((c) => c.room === view.room).map((c) => c.kind), rooms: found(snap).map((r) => `${r.id}:${r.type}`),
    labels: room.labels(), overlaps: overlaps(),
  },
} });
