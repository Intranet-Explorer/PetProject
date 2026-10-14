// SPEC-v3.5.1 on the page round the room: the hover cards of the hub's own things (the lit sign's lines, a screen,
// the founder's statue), a large CRT panel to read a screen by, and the radio as a real station: the header's control
// lists the stations and what is playing, and an <audio> element plays the chosen stream while the radio is on.
import { $, el, when } from "./dom";
import type { Kid } from "./dom";
import { screenInk, screenKey, tickerLines } from "./px/hub";
import type { Obj, Snap } from "./types";

const cap = (t: string) => t.slice(0, 1).toUpperCase() + t.slice(1);

/** The hover card of a hub thing (null: not one of them). `pic`: its picture as the room draws it. */
export function hubTip(name: string, o: Obj, s: Snap, pic: HTMLCanvasElement | null): Kid[] | null {
  if (o.statue) {   // its name (the founder's own label until the family gives it one), who it was, its last words
    const st = o.statue, p = o.build?.progress ?? 1, up = !o.fix?.built && p < 1, small = pic && el("canvas", "px") as HTMLCanvasElement;
    if (pic && small) { [small.width, small.height] = [pic.width / 3, pic.height / 3]; const g = small.getContext("2d")!; g.imageSmoothingEnabled = false; g.drawImage(pic, 0, 0, small.width, small.height); }   // (it is twice a pet's size already)
    return [small, el("div", "",
      el("p", "", el("b", "", st.name ?? s.pets.find((q) => q.id === st.of)?.label ?? "the first one"), el("span", "hint", ` · ${up ? `a statue going up, ${Math.round(p * 100)}% done` : "a statue"}`)),
      el("p", "", "the first of the family"),
      st.words ? el("blockquote", "chalk", st.words) : el("p", "hint", "Its last words are not known."),
      o.build?.title ? el("p", "hint", cap(o.build.title) + ".") : null)];
  }
  if (o.fix?.sign) return [el("div", "", el("p", "", el("b", "", "the lit sign"), el("span", "hint", " · it runs, over and over:")),
    el("ul", "", ...tickerLines(s).map((l) => el("li", "", l))))];
  if (o.fix?.terminal) {
    const sc = o.screen, who = sc && (sc.by ?? s.pets.find((p) => p.id === sc.pet)?.label ?? "someone");
    return [pic, el("div", "", el("p", "", el("b", "", `the ${name}`), el("span", "hint", " · an old computer: it looks things up in an encyclopedia")),
      sc ? el("p", "", `${cap(who!)} asked: `, el("q", "", sc.asked)) : el("p", "hint", "Nobody has used it yet."),
      sc ? el("p", "hint", sc.title ? `It found “${sc.title}”, ${when(s, sc.tick)}.` : `It found nothing, ${when(s, sc.tick)}.`) : null,
      el("p", "hint", "Click it to read the screen."))];
  }
  return null;
}

// ---- the big screen: what a pet read, typed and scrolling as on the glass, large enough to read ----

let open: { room: string; name: string; key: string; at: number } | null = null;
let timer: ReturnType<typeof setInterval> | undefined;
const panel = el("div", "crt");
panel.hidden = true;
panel.setAttribute("role", "dialog");
const head = el("p", "crthead"), glass = el("pre", "crtglass"), shut = el("button", "crtshut", "×") as HTMLButtonElement;
shut.type = "button";
shut.setAttribute("aria-label", "Close the screen");
shut.onclick = () => closeScreen();
panel.append(head, shut, glass);
addEventListener("keydown", (e) => { if (e.key === "Escape" && open) closeScreen(); });

export function closeScreen() {
  open = null;
  panel.hidden = true;
  clearInterval(timer);
}
/** Show a screen of the room on screen (`name`: its fixture's name) in the large panel; it types afresh. */
export function openScreen(s: Snap, room: string, name: string) {
  if (!panel.isConnected) $("tip").before(panel);   // (before the hover card: while it is open, the card keeps out of its way)
  open = { room, name, key: "", at: 0 };
  panel.hidden = false;
  screens(s, room);
}
/** Every snapshot: the panel follows its screen (a new question types out afresh), and shuts when another room is
 *  looked at or the screen is gone. */
export function screens(s: Snap, room: string) {
  if (!open) return;
  const r = s.rooms.find((x) => x.id === open!.room), o = r?.objects[open.name];
  if (!r || !o || room !== open.room) return closeScreen();
  const key = screenKey(o);
  if (key !== open.key || !open.at) [open.key, open.at] = [key, performance.now()];
  const ink = screenInk(r, open.name), sc = o.screen, who = sc && (sc.by ?? s.pets.find((p) => p.id === sc.pet)?.label ?? "someone");
  panel.style.setProperty("--crt", ink.on);
  head.textContent = `${r.name}: the ${open.name}${sc ? ` · ${who}, ${when(s, sc.tick)}` : ""}`;
  clearInterval(timer);
  const asked = sc ? `> ${sc.asked}\n\n` : "", body = sc ? (sc.text ? `${sc.title ? sc.title.toUpperCase() + "\n\n" : ""}${sc.text}` : "NOTHING FOUND.") : "READY.";
  const draw = () => {
    if (!open) return;
    const ms = performance.now() - open.at, typed = Math.min(asked.length, Math.floor(ms / 70)), read = typed < asked.length ? 0 : Math.min(body.length, Math.floor((ms - asked.length * 70 - 500) / 18));
    const done = typed >= asked.length && read >= body.length, blink = Math.floor(performance.now() / 500) % 2 === 0;
    glass.textContent = asked.slice(0, typed) + body.slice(0, Math.max(0, read)) + (done ? (blink ? "█" : " ") : "█");
    glass.scrollTop = glass.scrollHeight;   // the text scrolls up as it comes
  };
  draw();
  timer = setInterval(draw, 40);
}

// ---- the radio: a real station, played on this page while it is on ----

const audio = Object.assign(document.createElement("audio"), { id: "radioAudio", preload: "none" });
let blocked = false, failed = "";   // the browser wants a click first; the station did not answer
audio.onerror = () => { if (audio.getAttribute("src")) failed = audio.getAttribute("src")!; };

/** The header's control: "off" or one of the stations, by name and how it sounds. */
export function radioControl(s: Snap) {
  const r = s.dj!.radio, pick = $<HTMLSelectElement>("radioPlays");
  pick.replaceChildren(new Option("off", "off"), ...r.stations.map((st) => Object.assign(new Option(`${st.name}: ${st.sound}`, st.id), { title: `${st.mood}. ${st.home}` })));
  pick.value = r.on ? r.station : "off";
}
/** What the visitor chose in the header, as the visitor command (`plays` is the station; off keeps the last one). */
export const radioChoice = (s: Snap | null, v: string) => ({ type: "radio", on: v !== "off", plays: v === "off" ? s?.dj?.radio.station : v });

/** Every snapshot: the stream plays while the radio is on and the page's sound is on, quieter from a room it is not
 *  heard in; it stops when the radio goes off or the sound is turned off. The header says what is playing, or why not. */
export function radioSound(s: Snap, room: string, voice: { on: boolean; volume: number }, replay: boolean) {
  const r = s.dj?.radio, st = r?.on ? r.stations.find((x) => x.id === r.station) : undefined, src = audio.getAttribute("src");
  if (!audio.isConnected) document.body.append(audio);
  if (!st || !voice.on || replay) {
    if (src) { audio.pause(); audio.removeAttribute("src"); audio.load(); }   // (a stream left paused would go on downloading)
    blocked = false;
  } else {
    if (src !== st.stream) { audio.src = st.stream; failed = ""; play(); }
    else if (audio.paused && !blocked && failed !== st.stream) play();
    audio.volume = Math.min(1, voice.volume * (r!.rooms.includes(room) ? 1 : 0.4));
  }
  const now = $("radioNow");
  if (now) now.textContent = !st ? "" : !voice.on ? "(turn sound on to hear it)" : failed === st.stream ? "(the station is not answering)" : blocked ? "(click anywhere to listen)" : r!.now ? `♪ ${r!.now.title}` : `♪ ${st.name}`;
}
function play() {
  audio.play().then(() => (blocked = false), (e: DOMException) => {
    if (e.name !== "NotAllowedError") return;
    blocked = true;   // a browser plays nothing until the page has been clicked: the next click starts it
    addEventListener("pointerdown", () => { blocked = false; if (audio.getAttribute("src")) void audio.play().catch(() => {}); }, { once: true, capture: true });
  });
}
