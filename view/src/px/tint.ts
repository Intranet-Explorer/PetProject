// Recolouring (SPEC-v3.2 §3.1): a made thing's sprite takes the colour its maker chose, and shows what it is made of
// and how it has worn. Hue and saturation are replaced, lightness kept; the dark outline and the brightest highlights
// are left alone. Every result is kept, so a thing is recoloured once.
import type { Texture } from "pixi.js";
import { PALETTE } from "../things";
import { canvasOf, fromCanvas } from "./assets";
import { seeded } from "./geom";

/** What a thing's material and wear do to its picture. */
export type Look = { soft?: boolean; dark?: boolean; damp?: boolean; dusty?: boolean; eaten?: boolean; faint?: number };

const made = new Map<string, { canvas: HTMLCanvasElement; texture: Texture }>();

export function hexOf(color: string | null | undefined): string | null {
  if (!color) return null;
  return PALETTE[color] ?? (/^#[0-9a-f]{6}$/i.test(color) ? color : null);
}

function toHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
  if (!d) return [0, 0, l];
  const s = d / (1 - Math.abs(2 * l - 1));
  const h = max === r ? ((g - b) / d + 6) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}
function toRgb(h: number, s: number, l: number): [number, number, number] {
  const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = l - c / 2;
  const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}
export function hslOfHex(hex: string) {
  const n = parseInt(hex.slice(1), 16);
  return toHsl(n >> 16, (n >> 8) & 255, n & 255);
}

/** A copy of `src` in another colour. `strength` below 1 keeps some of its own colour (painted walls stay calm). */
export function recolor(src: HTMLCanvasElement, hex: string | null, look: Look = {}, key = "", strength = 1): HTMLCanvasElement {
  const c = document.createElement("canvas");
  [c.width, c.height] = [src.width, src.height];
  const x = c.getContext("2d")!;
  x.drawImage(src, 0, 0);
  const im = x.getImageData(0, 0, c.width, c.height), p = im.data, rnd = seeded(key + "wear");
  let [th, ts, tl] = hex ? hslOfHex(hex) : [0, 0, 0.5];
  if (ts < 0.35 || tl > 0.85) ts *= 0.2;   // white, grey and black are not colours: left as they are they come out beige or green
  for (let i = 0; i < p.length; i += 4) {
    if (!p[i + 3]) continue;
    let [h, s, l] = toHsl(p[i], p[i + 1], p[i + 2]);
    const outline = l < 0.2, shine = l > 0.9 && s < 0.35;
    if (hex && !outline && !(shine && !look.soft)) {
      // a white or black thing must end up pale or dark, so the target's own lightness pulls a little
      [h, s, l] = [th, ts * strength + s * (1 - strength), Math.max(0.08, Math.min(0.96, l + (tl - 0.5) * 0.55 * strength))];
    }
    if (look.soft && l > 0.78) l = 0.78 + (l - 0.78) * 0.3;          // nothing soft has a hard highlight
    if (look.dark && !outline) [s, l] = [s * 0.7, l * 0.62];           // shadowed
    const row = Math.floor(i / 4 / c.width) / c.height;
    if (look.damp && row > 0.55 && !outline) [h, s, l] = [h * 0.5 + 105, Math.min(1, s * 0.8 + 0.1), l * 0.72];   // dark and bluish where it sat in the wet
    if (look.dusty && !outline) [s, l] = [s * 0.55, l * 0.9 + 0.07];
    const [r, g, b] = toRgb(((h % 360) + 360) % 360, Math.max(0, Math.min(1, s)), l);
    [p[i], p[i + 1], p[i + 2]] = [r, g, b];
    if (look.dusty && row < 0.6 && rnd() < 0.16) [p[i], p[i + 1], p[i + 2]] = [214, 208, 194];   // specks of dust on top
    if (look.faint != null) p[i + 3] = Math.round(p[i + 3] * look.faint);
  }
  if (look.eaten) {   // the moth's holes
    const r = seeded(key + "moth");
    for (let n = 0; n < 3; n++) {
      const [hx, hy] = [2 + Math.floor(r() * (c.width - 5)), 3 + Math.floor(r() * (c.height - 6))];
      for (const [dx, dy] of [[0, 0], [1, 0], [0, 1], [1, 1], [2, 1]]) p[((hy + dy) * c.width + hx + dx) * 4 + 3] = 0;
    }
  }
  x.putImageData(im, 0, 0);
  return c;
}

/** A sprite in a made thing's colour and condition: the canvas (for a hover card) and its texture. */
export function tinted(sprite: string, color: string | null | undefined, look: Look = {}, strength = 1) {
  const hex = hexOf(color), key = `${sprite}|${hex}|${JSON.stringify(look)}|${strength}`;
  let t = made.get(key);
  if (!t) {
    const canvas = recolor(canvasOf(sprite), hex, look, key, strength);
    made.set(key, (t = { canvas, texture: fromCanvas(canvas) }));
  }
  return t;
}

/** A colour as one number, from hue (degrees), saturation and lightness (0 to 1): a pet's own colour, for what its animal wears. */
export function hslInt(h: number, s: number, l: number) {
  const [r, g, b] = toRgb(((h % 360) + 360) % 360, s, l);
  return (r << 16) | (g << 8) | b;
}
