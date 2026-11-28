// drawThing: a made thing drawn from its recipe (SPEC-v2 §9). One renderer, as SVG shapes, used both by the
// room (PixiJS reads the SVG) and by the Things shelf (the browser does). Only recipe enums reach the markup.
export type Part = { shape: string; size: number; color: string; at: string };
/** SPEC-v3.2 §3: a made thing is a `kind` from the catalog (view/assets/kinds.json) in a material, a colour and a size
 *  (1 small to 3 large). A recording made before v3.2 has `parts` and no kind: see kindOf. */
export type Recipe = { name: string; material: string; purpose: string; kind?: string; color?: string; size?: number; parts?: Part[];
  title?: string | null };   // SPEC-v3.5.8 §3: its maker's own name for it, shown only where Made.title_shown says

export const PALETTE: Record<string, string> = {
  red: "#d9483b", orange: "#f08a2e", yellow: "#f2c94c", green: "#3f9b63", teal: "#2f8f8a", blue: "#4a7fc1",
  purple: "#8a6fb0", pink: "#e58fb1", brown: "#8a5a36", white: "#f3f1e8", grey: "#8d9793", black: "#26302c",
};
const OFFSET: Record<string, [number, number]> = { center: [0, 0], top: [0, -11], bottom: [0, 11], left: [-11, 0], right: [11, 0] };
const n = (v: number) => v.toFixed(1);

/** The parts as SVG elements, centred on (cx, cy), fitting a box of about 60. `recolor` paints every part one colour. */
export function thingSvg(recipe: { parts?: Part[] }, cx = 0, cy = 0, recolor?: string): string {
  return (recipe.parts ?? []).map((part) => {
    const p = recolor ? { ...part, color: recolor } : part;
    const r = 6 + Math.min(3, Math.max(1, p.size)) * 4.5, [dx, dy] = OFFSET[p.at] ?? [0, 0], [x, y] = [cx + dx, cy + dy];
    const fill = PALETTE[p.color] ?? PALETTE.grey, ink = `fill="${fill}" stroke="#16241f" stroke-width="1.5"`;
    // a path, not a polygon: PixiJS reads path data reliably
    const poly = (pts: number[][]) => `<path d="${pts.map(([a, b], i) => `${i ? "L" : "M"}${n(x + a)} ${n(y + b)}`).join(" ")} Z" ${ink}/>`;
    switch (p.shape) {
      case "circle": return `<circle cx="${n(x)}" cy="${n(y)}" r="${n(r)}" ${ink}/>`;
      case "square": return `<rect x="${n(x - r * 0.85)}" y="${n(y - r * 0.85)}" width="${n(r * 1.7)}" height="${n(r * 1.7)}" ${ink}/>`;
      case "triangle": return poly([[0, -r], [r * 0.95, r * 0.75], [-r * 0.95, r * 0.75]]);
      case "blob": return `<ellipse cx="${n(x)}" cy="${n(y)}" rx="${n(r * 1.2)}" ry="${n(r * 0.8)}" ${ink}/>`;
      case "bar": return `<rect x="${n(x - r * 1.2)}" y="${n(y - r * 0.3)}" width="${n(r * 2.4)}" height="${n(r * 0.6)}" ${ink}/>`;
      case "dot": return `<circle cx="${n(x)}" cy="${n(y)}" r="${n(r * 0.45)}" ${ink}/>`;
      case "ring": return `<circle cx="${n(x)}" cy="${n(y)}" r="${n(r * 0.8)}" fill="none" stroke="${fill}" stroke-width="${n(r * 0.38)}"/>`;
      case "star": return poly(Array.from({ length: 10 }, (_, i) => {
        const a = (Math.PI * i) / 5 - Math.PI / 2, k = i % 2 ? r * 0.45 : r;
        return [Math.cos(a) * k, Math.sin(a) * k];
      }));
      default: return "";
    }
  }).join("");
}

/** A small standalone picture of a thing, for the shelf. */
export function thingPicture(recipe: { parts?: Part[] }): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "-32 -32 64 64");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = thingSvg(recipe);
  return svg;
}
