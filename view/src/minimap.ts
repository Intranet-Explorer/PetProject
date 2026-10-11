// The map of the house (SPEC-v3 §10.1): every room someone has found, blanks behind the doors nobody has been
// through, who is where, and what is going on in each room. Click a room to look at it.
import { PATHS, svg } from "./icons";
import { ROOMS } from "./rooms";
import type { Snap } from "./types";

const [CW, CH, GAP] = [70, 48, 13];
const STEP: Record<string, [number, number]> = { north: [0, -1], south: [0, 1], west: [-1, 0], east: [1, 0] };

export function drawMap(box: HTMLElement, s: Snap, viewed: string, chosen: string | null, look: (room: string) => void) {
  const [gx, gy] = [Math.max(...s.rooms.map((r) => r.cell[0])) + 1, Math.max(...s.rooms.map((r) => r.cell[1])) + 1];
  const at = (cell: number[]) => [cell[0] * (CW + GAP) + 2, cell[1] * (CH + GAP) + 2];
  const map = svg("svg", { viewBox: `0 0 ${gx * (CW + GAP) - GAP + 4} ${gy * (CH + GAP) - GAP + 4}` });
  const dark = s.clock.phase === "night" || (!s.power && s.clock.phase !== "day"), shut: SVGElement[] = [];   // a door blown shut is drawn last, over the open one from its other side
  for (const r of s.rooms) {
    const [x, y] = at(r.cell);
    if (!r.type) {   // only a blank, and only if a door of a found room leads to it
      if (!Object.values(r.doors).some((id) => s.rooms.find((q) => q.id === id)?.type)) continue;
      map.append(svg("g", { class: "unfound" }, svg("rect", { x, y, width: CW, height: CH, rx: 7 }), svg("text", { x: x + CW / 2, y: y + CH / 2 + 5, "text-anchor": "middle" }, "?"),
        svg("title", {}, "Nobody has been through this door yet")));
      continue;
    }
    for (const [dir, to] of Object.entries(r.doors)) {   // doors: a short bar across the gap
      const there = s.rooms.find((q) => q.id === to), [dx, dy] = STEP[dir];
      const [cx, cy] = [x + CW / 2 + (dx * (CW + GAP)) / 2, y + CH / 2 + (dy * (CH + GAP)) / 2];
      const way = svg("line", { x1: cx - dx * 5, y1: cy - dy * 5, x2: cx + dx * 5, y2: cy + dy * 5, class: `way${r.shut.includes(dir) ? " shut" : there?.type ? "" : " unknown"}` });
      r.shut.includes(dir) ? shut.push(way) : map.append(way);
    }
    const g = svg("g", { class: `room${r.id === viewed ? " viewed" : ""}`, role: "button", tabindex: 0, "aria-label": `Look at ${r.name}` },
      svg("rect", { x, y, width: CW, height: CH, rx: 7, fill: ROOMS[r.type]?.css ?? "#ccc" }),
      svg("path", { d: PATHS[r.type] ?? "", class: "glyph", transform: `translate(${x + 4} ${y + 3})` }),
      svg("title", {}, [r.name, r.wet ? "water is coming in" : "", r.cold ? "a draught" : "", r.sounding ? "something is sounding" : ""].filter(Boolean).join(" · ")));
    if (dark && !r.lit) g.append(svg("rect", { x, y, width: CW, height: CH, rx: 7, class: "dim", opacity: s.power ? 0.3 : 0.5 }));
    if (r.wet) g.append(svg("path", { d: PATHS.drop, class: "mark", transform: `translate(${x + CW - 18} ${y + 3})` }));
    if (r.cold) g.append(svg("path", { d: PATHS.wind, class: "mark", transform: `translate(${x + CW - (r.wet ? 34 : 18)} ${y + 3})` }));
    if (r.sounding) g.append(svg("path", { d: PATHS.music, class: "mark", transform: `translate(${x + 22} ${y + 3}) scale(0.8)` }));
    const spot = (pos: number[]) => [x + 9 + (pos[0] / (s.size[0] - 1)) * (CW - 18), y + 22 + (pos[1] / (s.size[1] - 1)) * (CH - 29)];
    for (const c of s.creatures.filter((c) => c.room === r.id)) {
      const [px, py] = spot(c.pos);
      const owner = s.pets.find((p) => p.id === c.tame);   // somebody's animal is in its pet's colour (SPEC-v3.1 §4.4)
      g.append(svg("path", { d: `M${px} ${py - 4}l4 4-4 4-4-4Z`, fill: owner ? `hsl(${owner.genome.hue} ${Math.round(owner.genome.saturation * 100)}% 52%)` : "#17231f", stroke: "#17231f", "stroke-width": owner ? 1 : 0 },
        svg("title", {}, c.name ?? `a ${c.kind}`)));
    }
    for (const p of s.pets.filter((p) => p.room === r.id && !(p.stage === "dead" && p.buried))) {
      const [px, py] = spot(p.pos), cls = `pet${p.id === chosen ? " chosen" : ""}`;
      const fill = p.stage === "dead" ? "#b9c0bd" : `hsl(${p.genome.hue} ${Math.round(p.genome.saturation * 100)}% 52%)`;
      g.append(p.stage === "egg" ? svg("ellipse", { cx: px, cy: py, rx: 3.6, ry: 4.8, fill: "#fbfaf4", class: cls }, svg("title", {}, p.name ?? "an egg"))
        : svg("circle", { cx: px, cy: py, r: p.stage === "dead" ? 4 : 5.5, fill, class: cls }, svg("title", {}, p.label)));
    }
    g.onclick = () => look(r.id);
    g.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") look(r.id); };
    map.append(g);
  }
  map.append(...shut);
  box.replaceChildren(map);
}
