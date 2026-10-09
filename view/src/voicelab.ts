// The header's sound controls and the Lab tab's voice lab (VOICE.md). Nothing here touches the pet or the engine.
import { schedule, Voice } from "./voice";
import { planSound, planSpeech } from "./voice-plan";
import type { SoundKind, VoiceInput } from "./voice-plan";

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const SOUNDS: [SoundKind | "heartbeat" | "breath" | "hum", string][] = [
  ["heartbeat", "Heartbeat (egg)"], ["cry", "First cry"], ["chirp", "Made a thing"], ["blip", "Took one apart"],
  ["trill", "Used one that helped"], ["stageup", "New stage"], ["hm", "“Hm?”"], ["whimper", "Whimper"],
  ["breath", "A breath (asleep)"], ["hum", "A taught thing's hum"],
];

export function initVoice(pet: () => VoiceInput | null) {
  const voice = new Voice(), num = (id: string) => Number($<HTMLInputElement>(id).value);
  const own = () => !$<HTMLInputElement>("labOwn").checked;

  /** The voice the lab plays with: the pet's own, or the sliders'. */
  const input = (): VoiceInput | null => {
    const p = pet();
    if (!p || own()) return p;
    return {
      stage: $<HTMLSelectElement>("labStage").value,
      genome: { ...p.genome, roundness: num("labRound") / 100, wobble: num("labWobble") / 100 },
      needs: { ...p.needs, energy: num("labEnergy"), comfort: num("labComfort") },
    };
  };
  const play = (what: Parameters<Voice["sample"]>[0]) => {
    const v = input();
    const played = v && voice.sample(what, v, $<HTMLInputElement>("labText").value);
    $("labHint").textContent = played ? "" : "Turn sound on in the header to hear this.";
  };

  $("labSounds").replaceChildren(...SOUNDS.map(([what, label]) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.onclick = () => play(what);
    return b;
  }));
  $("labSay").onclick = () => play("say");
  $("soundBtn").onclick = () => voice.setOn(!voice.on);
  $<HTMLInputElement>("volume").oninput = () => voice.setVolume(num("volume") / 100);
  $<HTMLInputElement>("volume").value = String(Math.round(voice.volume * 100));

  const show = () => {
    const waiting = voice.on && !voice.live;   // left on from last time; the browser wants a click first
    $("soundBtn").textContent = !voice.on ? "Sound off" : waiting ? "Sound on (click anywhere)" : "Sound on";
    $("soundBtn").setAttribute("aria-pressed", String(voice.on));
    $("heard").replaceChildren(...(voice.heard.length ? voice.heard.map((h) => {
      const li = document.createElement("li"), when = document.createElement("span");
      when.textContent = new Date(h.at).toLocaleTimeString();
      li.append(when, h.what);
      return li;
    }) : [Object.assign(document.createElement("li"), { className: "empty", textContent: voice.on ? "Nothing yet." : "Sound is off." })]));
  };
  voice.onchange = show;
  show();

  /** While the sliders are not in use they follow the pet, so switching them on starts from its own voice. */
  const follow = () => {
    const p = pet();
    for (const id of ["labStage", "labRound", "labWobble", "labEnergy", "labComfort"]) $<HTMLInputElement>(id).disabled = own();
    if (!p || !own()) return;
    $<HTMLSelectElement>("labStage").value = p.stage === "egg" ? "hatchling" : p.stage;
    $<HTMLInputElement>("labRound").value = String(Math.round(p.genome.roundness * 100));
    $<HTMLInputElement>("labWobble").value = String(Math.round(p.genome.wobble * 100));
    $<HTMLInputElement>("labEnergy").value = String(Math.round(p.needs.energy));
    $<HTMLInputElement>("labComfort").value = String(Math.round(p.needs.comfort));
  };
  $("labOwn").onchange = follow;

  // For checking from the console or a headless browser: render a plan without playing it.
  Object.assign(window, { petVoice: { voice, schedule, planSpeech, planSound, input } });
  return { voice, follow };
}
