// SPEC-v3.5.9 §4: a small LED display on the wall of every room (the machine room keeps its big board): the weather's
// animation, the house time, then one line about the room, all from the snapshot. It hangs where the north wall is
// clearest (or at a layout's `display`: [x, y] in the room's pixels), lit like the big board (hub.ts `Board`); the
// pointer on it shows the line in words (Room.card).
import { Sprite } from "pixi.js";
import { hhmm } from "../types";
import type { RoomV, Snap } from "../types";
import { addSprite, has, tex } from "./assets";
import { FX, OX, TILE, W } from "./geom";
import type { Rect } from "./geom";
import { Board, skyAnim } from "./hub";
import type { Still } from "./still";

const DW = 40, DH = 13;
const STAGE: Record<string, string> = { planted: "just planted", sprout: "sprouting", leaves: "in leaf", ripe: "ripe" };
export const SKY: Record<string, string> = { clear: "clear skies", heat: "a hot day", cloudy: "cloud", rain: "rain", storm: "a storm", snow: "snow" };   // engine/hub.py SAID
const list = (xs: string[]) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}`);
const overlap = (a: Rect, b: Rect) => Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));

/** The room's one line, in words. */
export function roomLine(s: Snap, room: RoomV): string {
  const objs = Object.entries(room.objects).filter(([, o]) => !o.on || o.planted), sky = SKY[s.weather] ?? s.weather;
  switch (room.type) {
    case "greenhouse": case "garden": {
      const ripe: string[] = [], growing: string[] = [];
      for (const [n, o] of objs) {
        const p = o.planted;
        if (p) (p.stage === "ripe" ? ripe : growing).push(`${p.what === "seed" ? "a seedling" : p.what} in the ${n}${p.wilted ? " (wilted)" : p.stage === "ripe" ? "" : ` (${STAGE[p.stage] ?? p.stage})`}`);
        else if (o.fix?.plant && o.state && o.state !== "bare") (o.state === "ripe" ? ripe : growing).push(`the ${n}`);
      }
      const what = [ripe.length ? `ripe: ${list(ripe)}` : "", growing.length ? `growing: ${list(growing)}` : ""].filter(Boolean).join("; ") || "nothing planted just now";
      return room.type === "garden" ? `${sky}. ${what}` : what;
    }
    case "pond": {
      const ready = [...new Set(room.spots.filter((b) => b.ready !== false && !b.loose).map((b) => b.bit))];
      const water = s.weather === "rain" || s.weather === "storm" ? "rain rippling the water" : s.weather === "snow" ? "snow falling on the water"
        : room.cold || s.clock.season === "winter" ? "the water cold and still" : s.clock.phase === "night" ? "the water dark and still" : "the water clear and still";
      return `${water}${ready.length ? `; ${list(ready)} ready to gather` : ""}`;
    }
    case "music": {
      const r = s.dj?.radio, station = r?.stations.find((x) => x.id === r.station)?.name, playing = objs.filter(([, o]) => o.state === "playing").map(([n]) => `the ${n} is playing`);
      return [r?.on ? `on the radio: ${r.now?.title ?? station ?? "a station"}` : "the radio is off", ...playing].join("; ");
    }
    case "nursery": {
      const eggs = s.pets.filter((p) => p.stage === "egg").map((p) => {
        const sec = p.hatches_in ?? 0, where = p.room === room.id ? "" : ` (in ${s.rooms.find((r) => r.id === p.room)?.name ?? "another room"})`;
        return `${p.name ?? "an egg"}${where} ${sec < 90 ? "about to hatch" : `hatches in about ${Math.round(sec / 60)} min`}`;
      });
      return eggs.length ? list(eggs) : "no eggs just now";
    }
    case "workshop": {
      const bench = objs.find(([, o]) => o.fix?.bench)?.[0], on = bench ? Object.entries(room.objects).filter(([, o]) => o.on === bench).map(([n]) => n) : [];
      const making = s.pets.filter((p) => p.room === room.id && p.act?.type === "make").map((p) => `${p.label} is making ${p.act!.what ? `the ${p.act!.what}` : "something"}`);
      return [...making, bench ? (on.length ? `on the ${bench}: ${list(on)}` : `the ${bench} is clear`) : "no bench here"].join("; ");
    }
    case "attic": {
      const last = s.pets.flatMap((p) => p.read ?? []).sort((a, b) => b.tick - a.tick)[0];
      if (!last) return "the heavy book: nothing read from it yet";
      const text = last.text.replace(/\s+/g, " ").trim(), cut = text.length > 110 ? `${text.slice(0, 110).replace(/\s\S*$/, "")}…` : text;
      return `the heavy book, last read: ${last.title}. ${cut}`;
    }
    case "cellar":
      return [room.wet ? "a leak: water dripping in, damp underfoot" : s.weather === "rain" || s.weather === "storm" ? "damp from the rain, no leak" : "dry, no leak",
        room.cold ? "a cold draught" : s.clock.season === "winter" || s.weather === "snow" ? "cool" : "warm enough"].join("; ");
    case "storeroom": {
      let have = 0, cap = 0;
      for (const [, o] of objs) if (o.store && o.store.cap != null && !o.fix?.keepsake) { have += o.store.holds.length; cap += o.store.cap; }
      return cap ? `the shelves: ${have} of ${cap} places full (${Math.round((100 * have) / cap)}%)` : "no shelves yet";
    }
      default: return sky;
  }
}

export type Display = { board: Board; rect: Rect; line: (s: Snap) => string };

/** Where on the north wall it hangs: the layout's place for it, or the stretch the fewest things already cover, nearest the middle. */
function spot(still: Still): Rect {
  const at = still.layout?.display;
  if (at) return { x: at[0], y: at[1], w: DW, h: DH };
  const busy = [...still.wallBusy, ...[...still.things.values()].map((t) => t.rect), ...still.windows.map((w) => w.rect), ...still.doors.map((d) => d.rect), ...still.scenery.map((s) => s.rect)];
  let best: Rect = { x: (W - DW) >> 1, y: 3, w: DW, h: DH }, cost = Infinity;
  for (const y of [3, 6, 9, 12, 16]) for (let x = OX + 2; x <= OX + FX * TILE - DW - 2; x += 2) {
    const r = { x, y, w: DW, h: DH }, c = busy.reduce((n, b) => n + overlap(r, b), 0) * 4 + Math.abs(x + DW / 2 - W / 2) * 0.2 + y * 0.3;
    if (c < cost) [best, cost] = [r, c];
  }
  return best;
}

/** Its case: a dark frame round a black face, with a highlight along the top (the big board's, smaller). */
function caseName() {
  const name = `display.case.${DW}x${DH}`;
  if (has(name)) return name;
  const c = Object.assign(document.createElement("canvas"), { width: DW, height: DH }), x = c.getContext("2d")!;
  for (const [color, i, top] of [["#141b1b", 0, 0], ["#4e484a", 1, 1], ["#0b0806", 2, 2]] as [string, number, number][]) { x.fillStyle = color; x.fillRect(i, top, DW - 2 * i, DH - 2 * i); }
  x.fillStyle = "#695953"; x.fillRect(1, 1, DW - 2, 1);
  x.fillStyle = "#8a7f78"; x.fillRect(3, 0, 1, 1); x.fillRect(DW - 4, 0, 1, 1);   // the two screws it hangs by
  addSprite(name, c);
  return name;
}

/** The display for a room, hung in its wall layer, or null (the machine room). */
export function display(still: Still, room: RoomV, K: number): Display | null {
  if (!room.type || room.type === "hub") return null;
  const r = spot(still), line = (s: Snap) => roomLine(s, s.rooms.find((x) => x.id === room.id) ?? room);
  const board = new Board(r, K, (s) => [{ anim: skyAnim(s), ms: 1400 }, { rows: [hhmm(s.clock.hour)], ms: 0 }, { rows: [line(s).toUpperCase()], ms: 0 }]);
  const c = new Sprite(tex(caseName()));
  c.position.set(r.x, r.y);
  still.wallLayer.addChild(c, board.s);
  still.wallBusy.push(r);   // chalk on the wall goes round it
  still.lamps.push({ x: r.x + DW / 2, y: r.y + DH / 2, r: 18, color: [255, 170, 80], made: true });   // its glow at night
  return { board, rect: r, line };
}
