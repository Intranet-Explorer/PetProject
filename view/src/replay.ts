// Replay (SPEC-v3 amendment, 9 Oct): a turbo run is watched afterwards. The engine keeps what it sent the view,
// one gzipped file of lines per world day; this plays them back through the same drawing as the live house.
import { $ } from "./dom";
import { hhmm } from "./types";
import type { Snap } from "./types";

const SPEEDS = [1, 2, 5, 10, 30, 60];
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/** `seek(day, at)`: a world day and how far through it, 0 to 1. `goto(day, tick)`: the first frame of that day at or after a tick. */
export type Replay = { state: () => object; seek: (day: number, at?: number) => Promise<void>; goto: (day: number, tick: number) => Promise<void>; play: (on: boolean) => void };

export async function startReplay(lineage: string, show: (s: Snap) => Promise<void> | void): Promise<Replay> {
  const q = new URLSearchParams(location.search);
  const index = (await (await fetch("/api/replay")).json()) as Record<string, number[]>;
  const days = index[`lineage-${lineage}`] ?? [];
  const cache = new Map<number, string[]>();   // a day's snapshots, still as text; only the one shown is parsed
  let d = Math.max(0, days.indexOf(Number(q.get("day")))), f = Number(q.get("f")) || 0;
  let playing = false, speed = Number(q.get("speed")) || 10, timer = 0, shown: Snap | null = null, busy = false;
  const [bar, play, scrub, when] = [$("replayBar"), $("replayPlay"), $<HTMLInputElement>("replayScrub"), $("replayWhen")];

  bar.hidden = false;
  $<HTMLSelectElement>("replayLineage").replaceChildren(...Object.keys(index).map((k) => new Option(`Family ${k.split("-")[1]}`, k.split("-")[1], false, k === `lineage-${lineage}`)));
  $<HTMLSelectElement>("replayLineage").onchange = (e) => (location.search = `?replay=${(e.target as HTMLSelectElement).value}`);
  $<HTMLSelectElement>("replaySpeed").replaceChildren(...SPEEDS.map((n) => new Option(`${n}×`, String(n), false, n === speed)));
  $<HTMLSelectElement>("replaySpeed").onchange = (e) => { speed = Number((e.target as HTMLSelectElement).value); mark(); };
  $("replayLive").onclick = () => (location.search = "");
  scrub.max = String(days.length * 1000);

  async function load(day: number) {
    if (!cache.has(day)) {
      cache.set(day, (await (await fetch(`/api/replay/${lineage}/${day}`)).text()).split("\n").filter(Boolean));
      if (cache.size > 3) cache.delete(cache.keys().next().value!);
    }
    return cache.get(day)!;
  }
  /** Keep the place in the address, so a reload comes back to the same moment (§10.7). */
  function mark() {
    history.replaceState(null, "", `?replay=${lineage}&day=${days[d]}&f=${f}&speed=${speed}`);
  }
  async function frame() {
    const lines = await load(days[d]);
    f = clamp(f, 0, lines.length - 1);
    shown = JSON.parse(lines[f]) as Snap;
    scrub.value = String(Math.round((d + f / lines.length) * 1000));
    when.textContent = `day ${shown.clock.day} of ${days.at(-1)} - ${hhmm(shown.clock.hour)}`;
    mark();
    await show(shown);
    return shown;
  }
  async function step() {
    if (!playing) return;
    const before = shown, lines = await load(days[d]);
    if (f + 1 < lines.length) f++;
    else if (d + 1 < days.length) [d, f] = [d + 1, 0];
    else return setPlaying(false);
    const s = await frame();
    // as long as it took in the house, divided by the speed
    timer = window.setTimeout(step, clamp((((s.tick - (before?.tick ?? s.tick)) * s.tick_seconds) / speed) * 1000, 30, 20_000));
  }
  function setPlaying(on: boolean) {
    playing = on;
    clearTimeout(timer);
    play.textContent = on ? "Pause" : "Play";
    play.setAttribute("aria-pressed", String(on));
    if (on) {
      if (d === days.length - 1 && f >= (cache.get(days[d])?.length ?? 1) - 1) [d, f] = [0, 0];   // at the end: start over
      step();
    }
  }
  async function seek(day: number, at = 0) {
    [d, f] = [clamp(day, 0, days.length - 1), at];
    await frame();
  }
  play.onclick = () => setPlaying(!playing);
  scrub.oninput = async () => {
    if (busy) return;   // a day is still loading; the next drag event will catch up
    busy = true;
    const v = Number(scrub.value) / 1000, day = clamp(Math.floor(v), 0, days.length - 1);
    const lines = await load(days[day]);
    [d, f] = [day, Math.floor((v - day) * lines.length)];
    await frame();
    busy = false;
  };
  if (days.length) await frame();
  else when.textContent = "nothing was recorded for this family";
  play.toggleAttribute("disabled", !days.length);
  return { state: () => ({ lineage, day: days[d], days: days.length, frame: f, playing, speed }), seek: async (day, at = 0) => seek(days.indexOf(day), Math.floor(clamp(at, 0, 1) * ((await load(day)).length - 1))),
           goto: async (day, tick) => seek(days.indexOf(day), Math.max(0, (await load(day)).findIndex((l) => (JSON.parse(l) as Snap).tick >= tick))), play: setPlaying };
}
