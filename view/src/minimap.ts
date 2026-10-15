// The map of the house (SPEC-v3.2 §7): a small pixel picture for every room someone has found, a blank behind each
// door nobody has been through, a dot for everyone, and a mark where something is going on. Click a room to look at it.
import { el } from "./dom";
import { icon } from "./icons";
import { hasSprite, sprite } from "./sprite";
import { fam } from "./types";
import type { Snap } from "./types";

const STEP: Record<string, [number, number]> = { north: [0, -1], south: [0, 1], west: [-1, 0], east: [1, 0] };

/** Drawn again only when what it shows has changed. `width` is the room there is for it, in screen pixels. */
export function drawMap(box: HTMLElement, s: Snap, viewed: string, chosen: string | null, look: (room: string) => void, width: number) {
  const [x0, y0] = [Math.min(...s.rooms.map((r) => r.cell[0])), Math.min(...s.rooms.map((r) => r.cell[1]))];   // SPEC-v3.5.1: the hub hangs outside the 3 x 3 grid (a cell of -1 or 3)
  const [gx, gy] = [Math.max(...s.rooms.map((r) => r.cell[0])) + 1 - x0, Math.max(...s.rooms.map((r) => r.cell[1])) + 1 - y0];
  const scale = Math.max(1, Math.min(3, Math.floor((width / gx - 22) / 16))), cell = 16 * scale + 16, gap = scale > 1 ? 6 : 4;   // (v3.5.6: a slot round each room, 8 px a side)
  const key = JSON.stringify([scale, viewed, chosen, s.rooms.map((r) => [r.type, r.wet, r.cold, r.sounding, r.shut, r.name]),
    s.pets.map((p) => [p.id, p.room, p.stage, p.buried, p.label]), s.creatures.map((c) => [c.id, c.room, c.tame, c.name])]);
  if (box.dataset.key === key) return void dots(box, s, chosen, x0, y0, cell, gap);
  box.dataset.key = key;
  const map = el("div", "map");
  map.style.cssText = `width:${gx * (cell + gap) - gap}px;height:${gy * (cell + gap) - gap}px;--cell:${cell}px`;
  const at = (c: number[]) => [(c[0] - x0) * (cell + gap), (c[1] - y0) * (cell + gap)];
  const put = (e: HTMLElement, x: number, y: number) => { e.style.left = `${x}px`; e.style.top = `${y}px`; return e; };
  for (const r of s.rooms) {
    const [x, y] = at(r.cell);
    if (!r.type) {   // only a blank, and only if a door of a found room leads to it
      if (!Object.values(r.doors).some((id) => s.rooms.find((q) => q.id === id)?.type)) continue;
      const blank = put(el("span", "maproom unfound", hasSprite("icon.room.unknown") ? sprite("icon.room.unknown", scale) : "?"), x, y);
      blank.title = "Nobody has been through this door yet";
      map.append(blank);
      continue;
    }
    for (const [dir, to] of Object.entries(r.doors)) {   // a door: a short bar across the gap; red when it has blown shut
      const [dx, dy] = STEP[dir], there = s.rooms.find((q) => q.id === to);
      const way = put(el("i", `way${dx ? "" : " down"}${r.shut.includes(dir) ? " shut" : there?.type ? "" : " unknown"}`), x + cell / 2 + (dx * (cell + gap)) / 2, y + cell / 2 + (dy * (cell + gap)) / 2);
      map.append(way);
    }
    const here = s.pets.filter((p) => p.room === r.id && !(p.stage === "dead" && p.buried)), beasts = s.creatures.filter((c) => c.room === r.id);
    const b = put(el("button", `maproom${r.id === viewed ? " viewed" : ""}`, sprite(`icon.room.${r.type}`, scale),
      r.wet || r.cold || r.sounding ? el("span", "signs", r.wet ? icon("drop", 10) : null, r.cold ? icon("wind", 10) : null, r.sounding ? icon("music", 10) : null) : null), x, y) as HTMLButtonElement;
    b.type = "button";
    b.title = [r.name, ...here.map((p) => (p.stage === "egg" ? p.name ?? "an egg" : p.label)), ...beasts.map((c) => c.name ?? `a ${c.kind}`),
      r.wet ? "water is coming in" : "", r.cold ? "a draught" : "", r.sounding ? "something is sounding" : ""].filter(Boolean).join(" · ");
    b.setAttribute("aria-label", `Look at ${r.name}`);
    b.onclick = () => look(r.id);
    map.append(b);
  }
  map.append(el("div", "dotlayer"));
  box.replaceChildren(map);
  dots(box, s, chosen, x0, y0, cell, gap);
}

/** SPEC-v3.5.7 §3: everyone as a dot in its family's colour where it is in its room, moving as it walks (the dots are
 *  kept, and glide from place to place); an animal is a smaller dot, in its pet's colour if it is somebody's. */
function dots(box: HTMLElement, s: Snap, chosen: string | null, x0: number, y0: number, cell: number, gap: number) {
  const layer = box.querySelector<HTMLElement>(".dotlayer");
  if (!layer) return;
  const [W, H] = s.size, seen = new Set<string>();
  const place = (id: string, cls: string, roomId: string, pos: number[]) => {
    const r = s.rooms.find((q) => q.id === roomId);
    if (!r?.type) return;
    let d = layer.querySelector<HTMLElement>(`[data-id="${id}"]`);
    if (!d) { d = el("i", ""); d.dataset.id = id; layer.append(d); }
    d.className = cls;
    d.style.left = `${(r.cell[0] - x0) * (cell + gap) + 8 + ((pos[0] + 0.5) / W) * (cell - 16)}px`;
    d.style.top = `${(r.cell[1] - y0) * (cell + gap) + 8 + ((pos[1] + 0.5) / H) * (cell - 16)}px`;
    seen.add(id);
  };
  for (const p of s.pets) if (!(p.stage === "dead" && p.buried)) place(p.id, `dot ${fam(p.family)}${p.stage === "egg" ? " egg" : p.stage === "dead" ? " dead" : ""}${p.asleep ? " asleep" : ""}${p.id === chosen ? " chosen" : ""}`, p.room, p.pos);
  for (const c of s.creatures) { const owner = s.pets.find((p) => p.id === c.tame); place(`c${c.id}`, `dot beast${owner ? ` ${fam(owner.family)}` : ""}`, c.room, c.pos); }
  for (const d of [...layer.children] as HTMLElement[]) if (!seen.has(d.dataset.id!)) d.remove();
}
