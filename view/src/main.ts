// Wiring: one websocket to the engine, snapshots in, visitor actions out (SPEC-v2 §9).
import { renderPanels } from "./panels";
import type { Genome } from "./pet";
import { Room } from "./room";

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
  pet: { pos: [number, number]; stage: string; needs: Needs; said: [number, string] | null; name: string | null; genome: Genome };
  objects: Record<string, { pos: [number, number]; state?: string }>;
  exploits: Record<string, number>;
  sleep: { since: number } | null;
  diary: Night[];
  plan: { thought: string; intention: string; steps: unknown[]; expect: string; i: number } | null;
  last_plan: { intention: string; ended: string; score: Score } | null;
  thinking: string | null;
  calls: number[];
};
export type PetState = { world: World; beliefs: Belief[]; journal: (Rec | { type: string })[]; accuracy: number | null; series: [number, number][] };
export type Snapshot = {
  size: [number, number]; tick_seconds: number; visitor_present: boolean; placeable: string[];
  pets: Record<string, PetState>;
};

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const room = new Room();
let snap: Snapshot | null = null;
let ready: Promise<void> | null = null;
let placing = false;
let sock: WebSocket | null = null;
let lastInput = 0; // presence needs real input, so a tab that was only opened does not count

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

function render() {
  if (!snap) return;
  const world = snap.pets.model.world; // the room shows the pet; a twin, if enabled, only appears in the Lab tab
  room.update(world, snap.tick_seconds);
  renderPanels(snap, "model", $<HTMLInputElement>("ruleOnly").checked);
  $("window").textContent = world.objects.window.state === "open" ? "Close window" : "Open window";
}

function connect() {
  sock = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  sock.onopen = presence;
  sock.onmessage = async (e) => {
    snap = JSON.parse(e.data) as Snapshot;
    ready ??= room.init($("room"), snap.size[0], snap.size[1]).then(() => {
      $("placeObject").replaceChildren(...snap!.placeable.map((o) => new Option(o)));
    });
    await ready;
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
  if (placing) {
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
$("placeBtn").onclick = () => setPlacing(!placing);
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
