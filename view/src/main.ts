// Wiring: one websocket to the engine, snapshots in, visitor actions out (SPEC-v2 §9).
import { renderPanels } from "./panels";
import type { Genome } from "./pet";
import type { Part, Recipe } from "./things";
import { Room } from "./room";
import { initVoice } from "./voicelab";

export type Needs = { energy: number; comfort: number; curiosity: number };
export type Belief = { id: string; statement: string; created: number; revised: number; status: string };
export type Score = "correct" | "wrong" | "unscorable";
export type Rec =
  | { type: "step"; tick: number; action: unknown; reason: string | null; feedback: string; deltas: Needs; rule_tags: string[] }
  | { type: "intention"; tick: number; intention: string; expect: string; ended: string; score: Score; deltas: Needs; rule_tags: string[] };
export type Night = { day: number; dream: string; changes: string[]; body: string; reason: string };
export type World = {
  tick: number;
  clock: { phase: string; hour: number; day: number };
  pet: { pos: [number, number]; stage: string; needs: Needs; trend: Partial<Needs>; said: [number, string] | null; name: string | null; genome: Genome };
  events: [number, string][];
  objects: Record<string, { pos: [number, number]; state?: string; active?: boolean;
                            made?: { recipe: Recipe; behavior?: { when: string; do: string } } }>;
  portraits?: { day: number; parts: Part[]; genome: Genome; stage: string }[];
  moments: [number, string][];
  room: { wall: string | null; floor: string | null };
  exploits: Record<string, number>;
  sleep: { since: number } | null;
  diary: Night[];
  plan: { thought: string; intention: string; steps: unknown[]; expect: string; i: number } | null;
  last_plan: { intention: string; ended: string; score: Score } | null;
  thinking: string | null;
  calls: number[];
};
export type Thing = {
  name: string; recipe: Recipe; made: number; by: string; uses: number; effects: Partial<Needs>[];
  gone: [number, string] | null; useful: boolean; behavior?: { when: string; do: string };
};
export type Progress = {
  days: number; useful: number; kept?: number; next: string | null;
  needs: { days: number; useful: number; kept_beliefs?: number } | null;
};
export type PetState = { world: World; beliefs: Belief[]; things: Thing[]; progress: Progress; journal: (Rec | { type: string })[]; accuracy: number | null; series: [number, number][] };
export type Snapshot = {
  size: [number, number]; tick_seconds: number; day_seconds: number; visitor_present: boolean; placeable: string[];
  materials: Record<string, string>;
  give: { shapes: string[]; colors: string[]; materials: string[] };
  pets: Record<string, PetState>;
};

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const room = new Room();
let snap: Snapshot | null = null;
let ready: Promise<void> | null = null;
let placing = false;
let giving = false;
let sock: WebSocket | null = null;
let lastInput = 0; // presence needs real input, so a tab that was only opened does not count
const sound = initVoice(() => snap && { ...snap.pets.model.world.pet });

const send = (msg: object) => sock?.readyState === WebSocket.OPEN && sock.send(JSON.stringify(msg));
const presence = () => send({ type: "presence", active: document.hasFocus() && Date.now() - lastInput < 5 * 60_000 });
const remember = (key: string, value: string) => { try { localStorage.setItem(key, value); } catch { /* private window */ } };
const recall = (key: string) => { try { return localStorage.getItem(key); } catch { return null; } };

function setPlacing(on: boolean) {
  placing = on;
  $("placeBtn").setAttribute("aria-pressed", String(on));
  $("placeBtn").textContent = on ? "Click a tile…" : "Pick a tile";
  $("room").classList.toggle("placing", on);
}

function setGiving(on: boolean) {
  giving = on;
  $("giveBtn").setAttribute("aria-pressed", String(on));
  $("giveBtn").textContent = on ? "Click an empty tile…" : "Pick a tile";
  $("room").classList.toggle("placing", on || placing);
}

function render() {
  if (!snap) return;
  const world = snap.pets.model.world; // the room shows the pet; a twin, if enabled, only appears in the Lab tab
  sound.voice.update(world, snap.pets.model.journal as Parameters<typeof sound.voice.update>[1], snap.pets.model.things, snap.visitor_present);
  sound.follow();
  room.update(world, snap.tick_seconds);
  renderPanels(snap, "model", $<HTMLInputElement>("ruleOnly").checked, (genome, stage) => room.picture(genome, stage));
  $("window").textContent = world.objects.window.state === "open" ? "Close window" : "Open window";

  // Moments (§9): a banner when something worth seeing happens, and the list of them under the room.
  const newest = world.moments.at(-1);
  if (newest && newest[0] > bannerTick) {
    if (bannerTick >= 0) {   // not on first load: that would announce old news
      $("banner").textContent = newest[1];
      $("banner").hidden = false;
      clearTimeout(bannerTimer);
      bannerTimer = setTimeout(() => ($("banner").hidden = true), 9000);
    }
    bannerTick = newest[0];
  } else if (!newest) bannerTick = Math.max(bannerTick, 0);
  $("moments").replaceChildren(...[...world.moments].reverse().map(([tick, text]) => {
    const li = document.createElement("li"), when = document.createElement("span");
    const hour = 8 + (tick * snap!.tick_seconds * 24) / snap!.day_seconds, day = 1 + Math.floor(hour / 24);
    when.textContent = `day ${day}, ${Math.floor(hour % 24)}:${String(Math.floor((hour % 1) * 60)).padStart(2, "0")}`;
    li.append(when, text);
    return li;
  }));
}
let bannerTick = -1;
let bannerTimer: ReturnType<typeof setTimeout> | undefined;

function connect() {
  sock = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  sock.onopen = presence;
  sock.onmessage = async (e) => {
    snap = JSON.parse(e.data) as Snapshot;
    ready ??= room.init($("room"), snap.size[0], snap.size[1]).then(() => {
      for (const [id, key] of [["giveColor", "colors"], ["giveShape", "shapes"], ["giveMaterial", "materials"]] as const) {
        $(id).replaceChildren(...snap!.give[key].map((o) => new Option(o)));
      }
    });
    await ready;
    const pick = $<HTMLSelectElement>("placeObject");   // what can be moved grows as it makes things
    if (pick.options.length !== snap.placeable.length) {
      const chosen = pick.value;
      pick.replaceChildren(...snap.placeable.map((o) => new Option(o)));
      if (snap.placeable.includes(chosen)) pick.value = chosen;
    }
    render();
  };
  sock.onclose = () => {
    const chip = document.createElement("span");
    chip.className = "chip down";
    chip.textContent = "engine not reachable, retrying…";
    $("status").replaceChildren(chip);
    setTimeout(connect, 2000);
  };
}

room.onTile = (x, y) => {
  if (!snap) return;
  if (giving) {
    const pick = (id: string) => $<HTMLSelectElement>(id).value;
    send({ type: "give", shape: pick("giveShape"), color: pick("giveColor"), material: pick("giveMaterial"), tile: [x, y] });
    setGiving(false);
  } else if (placing) {
    send({ type: "place", object: $<HTMLSelectElement>("placeObject").value, tile: [x, y] });
    setPlacing(false);
  } else {
    const [px, py] = snap.pets.model.world.pet.pos;
    if (px === x && py === y) send({ type: "poke" });
  }
};
$("feed").onclick = () => send({ type: "feed" });
$("poke").onclick = () => send({ type: "poke" });
$("window").onclick = () => send({ type: "window" });
$("placeBtn").onclick = () => { setGiving(false); setPlacing(!placing); };
$("giveBtn").onclick = () => { setPlacing(false); setGiving(!giving); };
$("ruleOnly").onchange = render;
$("talkForm").onsubmit = (e) => {
  e.preventDefault();
  const input = $<HTMLInputElement>("talkText");
  if (input.value.trim()) send({ type: "talk", text: input.value });
  input.value = "";
};

// The drawer is closed by default: what the pet means to do stays a surprise unless you look.
function setDrawer(open: boolean) {
  $("drawer").hidden = !open;
  $("drawerBtn").setAttribute("aria-expanded", String(open));
  document.body.classList.toggle("open", open);
}
function showTab(name: string) {
  for (const b of document.querySelectorAll<HTMLElement>("[data-tab]")) b.setAttribute("aria-selected", String(b.dataset.tab === name));
  for (const p of document.querySelectorAll<HTMLElement>("[data-panel]")) p.hidden = p.dataset.panel !== name;
  remember("tab", name);
}
$("drawerBtn").onclick = () => setDrawer($("drawer").hasAttribute("hidden"));
$("drawerClose").onclick = () => setDrawer(false);
for (const b of document.querySelectorAll<HTMLElement>("[data-tab]")) b.onclick = () => showTab(b.dataset.tab!);
showTab(document.querySelector(`[data-tab="${recall("tab")}"]`) ? recall("tab")! : "mind");

for (const type of ["pointerdown", "keydown"]) {
  addEventListener(type, () => { lastInput = Date.now(); presence(); }, { capture: true });
}
addEventListener("focus", presence);
addEventListener("blur", presence);
setInterval(presence, 15_000);
connect();
