// Wiring: one websocket to the engine, snapshots in, visitor actions out (SPEC §13).
import { renderPanels } from "./panels";
import { Room } from "./room";

export type Needs = { energy: number; comfort: number; curiosity: number };
export type Belief = { id: string; statement: string; created: number; revised: number; status: string };
export type Rec = {
  tick: number; phase: string; thought: string; action: unknown; expect: string; reason: string | null;
  feedback: string; deltas: Needs; score: "correct" | "wrong" | "unscorable"; rule_tags: string[]; rule_scored: boolean;
};
export type World = {
  tick: number;
  clock: { phase: string; hour: number; day: number };
  pet: { pos: [number, number]; stage: string; needs: Needs; said: [number, string] | null };
  objects: Record<string, { pos: [number, number]; state?: string }>;
};
export type PetState = { world: World; beliefs: Belief[]; journal: Rec[]; accuracy: number | null; series: [number, number][] };
export type Snapshot = {
  size: [number, number]; tick_seconds: number; visitor_present: boolean; placeable: string[];
  pets: Record<string, PetState>;
};

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const room = new Room();
let snap: Snapshot | null = null;
let ready: Promise<void> | null = null;
let petId = "";
let placing = false;
let sock: WebSocket | null = null;
let lastInput = 0; // presence needs real input, so a tab that was only opened does not count

const send = (msg: object) => sock?.readyState === WebSocket.OPEN && sock.send(JSON.stringify(msg));
const presence = () => send({ type: "presence", active: document.hasFocus() && Date.now() - lastInput < 5 * 60_000 });

function setPlacing(on: boolean) {
  placing = on;
  $("placeBtn").setAttribute("aria-pressed", String(on));
  $("placeBtn").textContent = on ? "Click a tile…" : "Pick a tile";
  $("room").classList.toggle("placing", on);
}

function render() {
  if (!snap) return;
  if (!snap.pets[petId]) petId = Object.keys(snap.pets)[0];
  const pet = snap.pets[petId];
  room.update(pet.world);
  renderPanels(snap, petId, $<HTMLInputElement>("ruleOnly").checked);
  $("window").textContent = pet.world.objects.window.state === "open" ? "Close window" : "Open window";

  const ids = Object.keys(snap.pets); // the toggle appears once the model pet exists (M2)
  $("pets").replaceChildren(...(ids.length < 2 ? [] : ids.map((id) => {
    const b = document.createElement("button");
    b.textContent = id;
    b.setAttribute("aria-pressed", String(id === petId));
    b.onclick = () => { petId = id; render(); };
    return b;
  })));
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
    $("status").textContent = "engine not reachable, retrying…";
    $("status").className = "down";
    setTimeout(connect, 2000);
  };
}

room.onTile = (x, y) => {
  if (!snap) return;
  if (placing) {
    send({ type: "place", object: $<HTMLSelectElement>("placeObject").value, tile: [x, y] });
    setPlacing(false);
  } else {
    const [px, py] = snap.pets[petId].world.pet.pos;
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
for (const type of ["pointerdown", "keydown"]) {
  addEventListener(type, () => { lastInput = Date.now(); presence(); }, { capture: true });
}
addEventListener("focus", presence);
addEventListener("blur", presence);
setInterval(presence, 15_000);
connect();
