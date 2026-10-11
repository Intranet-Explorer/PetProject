// Writing on the walls (SPEC-v3.1 §2.4): chalky pixel lettering on the wall it names, in the stretch of that wall
// left free by doors, windows and whatever hangs there, near where its writer stood. Chalk is pale with a dark edge
// so it shows on any wall; a scratch is only a shade off the wall and fainter. Both fade with their clarity. What does
// not fit is cut short (the page shows the whole of it on hover). New words appear stroke by stroke.
import { Container, Graphics, Sprite } from "pixi.js";
import type { Mark, RoomV } from "../types";
import { fromCanvas } from "./assets";
import { measure, plain, textCanvas, wrap } from "./font";
import type { Rect } from "./geom";
import type { Still } from "./still";

const SIDES = [{ name: "north", flat: true, turn: 0, lines: 2 }, { name: "south", flat: true, turn: 0, lines: 1 }, { name: "west", flat: false, turn: -1, lines: 1 }, { name: "east", flat: false, turn: 1, lines: 1 }];

export class Marks {
  c = new Container();
  /** Where each inscription is, for the pointer. */
  rects: { rect: Rect; m: Mark }[] = [];
  /** Where each was when last drawn, by id: dust rises there when one is rubbed out. */
  where = new Map<number, number[]>();
  private known: Set<number> | null = null;
  private room = "";
  private showing: { mask: Graphics; s: Sprite; w: number; h: number; t0: number }[] = [];

  /** `px`: the room's pixels to a pixel of lettering. `keep`: a stretch of the south wall the page has covered, in the room's pixels. */
  build(room: RoomV, still: Still, px: number, keep: number[] | null, now: number) {
    for (const ch of this.c.removeChildren()) ch.destroy({ children: true, texture: true, textureSource: true });
    this.rects = [];
    this.showing = [];
    if (room.id !== this.room) [this.room, this.known] = [room.id, null];
    const all = room.marks ?? [], fresh = this.known ? all.filter((m) => !this.known!.has(m.id)) : [];
    this.known = new Set(all.map((m) => m.id));
    this.where.clear();
    const pale = still.wallShade > 0.5;
    for (const sd of SIDES) {
      const band = still.band[sd.name], side = { ...sd, from: sd.flat ? band.x : band.y, len: sd.flat ? band.w : band.h, across: sd.flat ? band.y : band.x, deep: sd.flat ? band.h : band.w };
      const mine = all.filter((m) => m.on === `${side.name} wall`).sort((a, b) => (a.at ?? 0.5) - (b.at ?? 0.5));
      if (!mine.length) continue;
      // what is taken along this wall, as stretches of its length
      const taken = still.wallBusy.filter((r) => r.x < band.x + band.w && band.x < r.x + r.w && r.y < band.y + band.h && band.y < r.y + r.h).map((r) => (side.flat ? [r.x - 3, r.x + r.w + 3] : [r.y - 3, r.y + r.h + 3]));
      if (side.name === "south" && keep) taken.push([keep[0] - 3, keep[1] + 3]);
      taken.sort((a, b) => a[0] - b[0]);
      const gaps: { from: number; to: number; marks: Mark[] }[] = [];
      let at = side.from + 2;
      for (const [a, b] of [...taken, [side.from + side.len - 2, Infinity]]) {
        if (a - at >= 22) gaps.push({ from: at, to: a, marks: [] });
        at = Math.max(at, b);
      }
      for (const m of mine) {   // each into the free stretch nearest to where it was written
        // (a stretch too short for the words costs as much as walking that much further along the wall)
        const x = side.from + (m.at ?? 0.5) * side.len, need = Math.min(side.len * 0.6, (measure(plain(m.text)) * px) / side.lines + 8);
        const far = (g: { from: number; to: number }) => Math.abs(Math.max(g.from, Math.min(g.to, x)) - x) + Math.max(0, need - (g.to - g.from)) * 1.5;
        [...gaps].sort((a, b) => far(a) - far(b))[0]?.marks.push(m);
      }
      for (const g of gaps) g.marks.forEach((m, n) => {
        const slot = (g.to - g.from) / g.marks.length, from = g.from + n * slot, chalk = m.medium !== "scratch", clear = m.clarity ?? 1;
        const lines = wrap(m.text, Math.max(12, (slot - 4) / px), side.name === "north" && slot < 70 ? 3 : side.lines);   // a narrow stretch of the tall north wall takes a third line
        const cv = textCanvas(lines, chalk ? { color: "#f8f4e8", halo: pale ? "rgba(60,46,50,0.42)" : "rgba(20,16,24,0.35)", chalk: `${m.id}`, alpha: 0.5 + 0.5 * clear }
                                           : { color: pale ? "#3a2a26" : "#e6dccb", chalk: `${m.id}`, alpha: 0.35 + 0.4 * clear });
        const s = new Sprite(fromCanvas(cv)), w = cv.width * px, h = cv.height * px;
        const along = Math.round(Math.max(from + 1, Math.min(from + slot - w - 1, side.from + (m.at ?? 0.5) * side.len - w / 2)));
        const across = Math.round(side.across + (side.deep - h) / 2);
        s.scale.set(px);
        const holder = new Container();
        holder.addChild(s);
        // on a side wall the words run along it, turned a quarter (a quarter turn keeps every pixel whole)
        if (side.turn < 0) { holder.rotation = -Math.PI / 2; holder.position.set(across, along + w); }
        else if (side.turn > 0) { holder.rotation = Math.PI / 2; holder.position.set(across + h, along); }
        else holder.position.set(along, across);
        this.c.addChild(holder);
        const rect = side.flat ? { x: along, y: across, w, h } : { x: across, y: along, w: h, h: w };
        this.rects.push({ m, rect });
        this.where.set(m.id, [rect.x + rect.w / 2, rect.y + rect.h / 2]);
        if (fresh.includes(m)) {   // just written: it appears as the hand moves
          const mask = new Graphics();
          holder.addChild(mask);
          s.mask = mask;
          this.showing.push({ mask, s, w: cv.width * px, h: cv.height * px, t0: now });
        }
      });
    }
    for (const m of all) {   // on a thing or a stone: a small scrawl on it
      const t = still.things.get(m.on);
      if (!t) continue;
      const g = new Graphics(), x = Math.round(t.x - 4), y = Math.round(t.y - Math.min(8, t.rect.h / 2));
      g.rect(x, y, 2, 1).rect(x + 2, y - 1, 2, 1).rect(x + 4, y, 3, 1).rect(x + 1, y + 2, 3, 1).rect(x + 4, y + 3, 2, 1).fill({ color: 0xf8f4e8, alpha: 0.45 + 0.5 * (m.clarity ?? 1) });
      g.zIndex = t.s.zIndex + 0.1;
      still.standing.push(g);   // over the thing it is written on (the room sorts it in with what stands on the floor)
      this.where.set(m.id, [t.x, t.y - 6]);
    }
  }

  /** The inscription that has just been written, if one is still appearing: where the chalk is now. */
  step(now: number): number[] | null {
    let tip: number[] | null = null;
    for (let i = this.showing.length - 1; i >= 0; i--) {
      const r = this.showing[i], k = Math.min(1, (now - r.t0) / Math.max(900, r.w * 28));
      r.mask.clear().rect(0, 0, Math.ceil(r.w * k), r.h).fill(0xffffff);
      const p = r.s.parent!.toGlobal({ x: r.w * k, y: r.h / 2 });
      tip = [p.x, p.y];
      if (k >= 1) { r.s.mask = null; r.mask.destroy(); this.showing.splice(i, 1); }
    }
    return tip;
  }
}
