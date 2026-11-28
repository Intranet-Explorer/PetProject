// The header's sound controls (the Sound switch, and the five volumes in "More") and the Lab's sound board, where
// every file of view/assets/audio can be heard (AUDIO-BRIEF §4.3, §4.11). Nothing here touches a pet or the engine.
import { $, el } from "./dom";
import { sounds } from "./sprite";
import { schedule, tune, Voice, voiceInput } from "./voice";
import type { Levels } from "./voice";
import { babble, filesOf, levelOf, planSong, voiceOf } from "./voice-plan";
import type { Sounds } from "./voice-plan";
import type { PetV, Snap } from "./types";

const LEVELS: (keyof Levels)[] = ["master", "music", "ambience", "effects", "voices"];

/** `who` gives the pet whose voice the Lab plays with (the selected one) and the snapshot it is in. */
export function initVoice(who: () => { pet: PetV; snap: Snap } | null) {
  const voice = new Voice();
  const hint = el("p", "hint"), heard = el("ol", "heard"), board = el("div", "board"), text = el("input", "") as HTMLInputElement;
  text.value = "hello, what is this? I made it!";
  text.setAttribute("aria-label", "Something to say");
  const button = (label: string, go: () => void, title = "") => Object.assign(el("button", "", label), { onclick: go, title });
  const off = () => (hint.textContent = "Turn sound on in the header to hear this.");

  /** Every sound of ours, by folder, each a button; its file's own words (credits.json) on hover. Built when first opened. */
  const fill = async () => {
    if (board.childElementCount) return;
    const S = sounds() as Sounds, credits = new Map<string, string>();
    try {
      const c = await (await fetch("/art/audio/credits.json")).json() as { files: { file: string; description: string; license: string }[] };
      for (const f of c.files) credits.set(f.file, `${f.description} (${f.license})`);
    } catch { /* the buttons still play */ }
    const names = Object.keys(S.sounds ?? {}), folders = [...new Set(names.map((n) => n.split("/")[0]))];
    board.replaceChildren(...folders.map((f) => el("div", "row", el("h4", "", f),
      ...names.filter((n) => n.startsWith(f + "/")).map((n) => {
        const e = S.sounds[n], lv = levelOf(S, n)!;
        return button(`${n.slice(f.length + 1)}${e.n ? ` ×${e.n}` : ""}${e.loop ? " ⟳" : ""}`, () => { hint.textContent = voice.audition(n) ? "" : "Turn sound on in the header to hear this."; },
          `${credits.get(filesOf(S, n)[0].slice(S.dir.length + 1)) ?? n}\n${e.group}: ${S.groups[e.group] ?? 0} dB, on the ${lv.bus} volume`);
      }))));
  };
  const details = el("details", "", el("summary", "", "Sound board: every sound in the house"), board) as HTMLDetailsElement;
  details.ontoggle = () => details.open && void fill();
  /** One node, built once and handed to the Lab tab each time it draws. */
  const lab = el("section", "voicelab",
    el("h3", "", "Sound"),
    el("p", "hint", "Every sound is a file in view/assets/audio (its credits.json says how each was made, and its licence). Music follows the time of day and the mood, "
      + "and rests between tracks; ambience follows the room on screen; next door is quieter and muffled. A hob's words are babble, pitched to its body."),
    el("div", "row", text, button("Babble it", () => {
      const w = who();
      if (!w || !voice.live) return off();
      const v = voiceInput(w.pet, w.snap);
      voice.babble(babble(text.value, voiceOf(v).base, v.stage));
      hint.textContent = "";
    }, "As the selected hob would say it")),
    details, hint, el("h4", "", "Heard lately"), heard);

  $("soundBtn").onclick = () => voice.setOn(!voice.on);
  for (const k of LEVELS) {   // the five volumes, in "More"; each remembered in this browser
    const r = $<HTMLInputElement>(`vol-${k}`);
    r.value = String(Math.round(voice.levels[k] * 100));
    r.oninput = () => voice.setLevel(k, Number(r.value) / 100);
  }

  let fade: ReturnType<typeof setTimeout> | undefined;
  const show = () => {
    const waiting = voice.on && !voice.live;   // left on from last time; the browser wants a click first
    $("soundBtn").setAttribute("aria-label", !voice.on ? "Sound off" : waiting ? "Sound on (click)" : "Sound on");   // (v3.5.6: the button is the Travel Book's sound icon)
    $("soundBtn").setAttribute("aria-pressed", String(voice.on));
    const lost = voice.missing.size;   // SPEC-v4.0.5 §7.9: the WAVs are not in the repo; with them absent, say so
    $("soundBtn").title = (waiting ? "Sound was left on. A browser plays nothing until the page has been clicked: click anywhere." : voice.on ? "Sound on" : "Sound off")
      + (lost ? `: sound files not installed (${lost} missing)` : "");
    for (const k of LEVELS) $<HTMLInputElement>(`vol-${k}`).disabled = !voice.on;   // (all follow the Sound switch)
    const latest = voice.heard[0];   // say what just played, so silence and "nothing happening" can be told apart
    $("playing").textContent = voice.on && latest && Date.now() - latest.at < 8000 ? `♪ ${latest.what}` : "";
    clearTimeout(fade);
    if (latest) fade = setTimeout(show, 8500);
    heard.replaceChildren(...(voice.heard.length ? voice.heard.map((h) => el("li", "", el("span", "", new Date(h.at).toLocaleTimeString()), " " + h.what))
      : [el("li", "empty", voice.on ? "Nothing yet." : "Sound is off.")]));
  };
  voice.onchange = show;
  show();

  // For checking from the console or a headless browser
  Object.assign(window, { petVoice: { voice, schedule, tune, planSong, babble } });
  return { voice, lab };
}
