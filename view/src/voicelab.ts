// The header's sound controls and the Lab tab's voice lab (VOICE.md). Nothing here touches a pet or the engine.
import { $, el } from "./dom";
import { ambient, effect, schedule, Voice, voiceInput } from "./voice";
import { planSound, planSpeech, planVox, VOX } from "./voice-plan";
import type { VoiceInput } from "./voice-plan";
import type { PetV, Snap } from "./types";

const STAGES = ["as it is", "hatchling", "child", "youngling", "adult", "elder"];
const SOUNDS: [Parameters<Voice["sample"]>[0], string][] = [
  ["heartbeat", "Heartbeat (egg)"], ["cry", "First cry"], ["chirp", "Made a thing"], ["blip", "Took one apart"], ["trill", "A nuzzle taken"],
  ["stageup", "New stage"], ["hm", "“Hm?”"], ["whimper", "Whimper"], ["last", "A death"], ["breath", "A breath (asleep)"], ["hum", "A thing humming"],
  ...VOX.map((k): [`vox ${typeof k}`, string] => [`vox ${k}`, `By itself: ${k}`]),   // SPEC-v3.3 §4: the small sounds its body makes
  ["moth", "Moth"], ["beetle", "Beetle"], ["mouse", "Mouse"], ["bird", "Bird"], ["rain", "Rain"], ["thunder", "Thunder"],
  ["powerdown", "Power cut"], ["drip", "Leak"], ["whoosh", "Draught"], ["thud", "Delivery"],
  ["chalk", "Writing arrives"], ["chime", "Songs arrive"], ["patter", "Taming arrives"], ["tuning", "The radio arrives"], ["pages", "The book arrives"], ["knock", "A stranger arrives"],
];

/** `who` gives the pet whose voice the lab plays with (the selected one) and the snapshot it is in. */
export function initVoice(who: () => { pet: PetV; snap: Snap } | null) {
  const voice = new Voice();
  const stage = el("select", "") as HTMLSelectElement, text = el("input", "") as HTMLInputElement, hint = el("p", "hint"), heard = el("ol", "heard");
  stage.append(...STAGES.map((s) => new Option(s)));
  stage.setAttribute("aria-label", "Stage to hear");
  text.value = "hello, what is this? I made it!";
  text.setAttribute("aria-label", "Something to say");

  /** The voice the lab plays with: the selected pet's, at its own stage or one chosen to hear how a voice grows. */
  const input = (): VoiceInput | null => {
    const w = who();
    if (!w) return null;
    const v = voiceInput(w.pet, w.snap);
    return stage.selectedIndex ? { ...v, stage: stage.value } : v;
  };
  const play = (what: Parameters<Voice["sample"]>[0]) => {
    const v = input();
    hint.textContent = v && voice.sample(what, v, text.value) ? "" : "Turn sound on in the header to hear this.";
  };
  const button = (label: string, go: () => void) => Object.assign(el("button", "", label), { onclick: go });
  /** One node, built once and handed to the Lab tab each time it draws, so what is typed and chosen stays. */
  const lab = el("section", "voicelab",
    el("h3", "", "Voice"),
    el("p", "hint", "Every voice comes from a body: taller is lower, rounder is purer, paler is more muffled, so a child sounds like its parent. "
      + "A hatchling chirps, a child babbles, and from youngling on real words come through."),
    el("div", "row", stage, text, button("Say it", () => play("say"))),
    el("div", "sounds", ...SOUNDS.map(([what, label]) => button(label, () => play(what)))),
    hint, el("h4", "", "Heard lately"), heard);

  $("soundBtn").onclick = () => voice.setOn(!voice.on);
  $("ambBtn").onclick = () => voice.setAmbience(!(voice.on && voice.ambience));
  const volume = $<HTMLInputElement>("volume");
  volume.oninput = () => voice.setVolume(Number(volume.value) / 100);
  volume.value = String(Math.round(voice.volume * 100));

  let fade: ReturnType<typeof setTimeout> | undefined;
  const show = () => {
    const waiting = voice.on && !voice.live;   // left on from last time; the browser wants a click first
    $("soundBtn").setAttribute("aria-label", !voice.on ? "Sound off" : waiting ? "Sound on (click)" : "Sound on");   // (v3.5.6: the button is the Travel Book's sound icon)
    $("soundBtn").setAttribute("aria-pressed", String(voice.on));
    $("soundBtn").title = waiting ? "Sound was left on. A browser plays nothing until the page has been clicked: click anywhere." : voice.on ? "Sound on" : "Sound off";
    $("ambBtn").textContent = voice.on && voice.ambience ? "Ambience on" : "Ambience off";
    $("ambBtn").setAttribute("aria-pressed", String(voice.on && voice.ambience));
    const latest = voice.heard[0];   // say what just played, so silence and "nothing happening" can be told apart
    $("playing").textContent = voice.on && latest && Date.now() - latest.at < 8000 ? `♪ ${latest.what}` : "";
    clearTimeout(fade);
    if (latest) fade = setTimeout(show, 8500);
    heard.replaceChildren(...(voice.heard.length ? voice.heard.map((h) => el("li", "", el("span", "", new Date(h.at).toLocaleTimeString()), " " + h.what))
      : [el("li", "empty", voice.on ? "Nothing yet." : "Sound is off.")]));
  };
  voice.onchange = show;
  show();

  // For checking from the console or a headless browser: render a plan without playing it.
  Object.assign(window, { petVoice: { voice, schedule, effect, ambient, planSpeech, planSound, planVox, input } });
  return { voice, lab };
}
