// The parts library (SPEC-v3.5 §1), read from /art/parts.json and the pictures it names (view/assets/own/parts):
// the pieces a thing a pet invented is put together from, and the parts of a pet's body. Nothing here names a part:
// which parts there are, where each goes on another and how a material looks are all in that file.
import { PALETTE } from "./things";

/** A kind the house invented (the snapshot's `invented`): up to three parts, the first on nothing (`at` null), the
 *  others each on one of its spots, every one in its own material and colour. */
export type Invention = { name: string; a?: string; use?: string; parts: { part: string; at: string | null; material?: string; color?: string }[]; size?: string;
  does?: string; sound?: string | null; glow?: boolean; from?: string[]; by?: string; tick?: number };
/** A body part's picture at one size from one side: `px` is a code for each pixel (0: nothing, or CODES' place + 1). */
export type Stamp = { w: number; h: number; px: Uint8Array; pin: [number, number] };
export type Plan = { w: number; h: number; head?: { w: number; tall: number; round?: number }; overlap?: number };
export type Slot = { layer?: string; pair?: boolean; outline?: boolean; spread?: number; side_at?: string };

export const CODES = ["main0", "main1", "main2", "main3", "trim0", "trim1", "trim2", "trim3", "glow0", "glow1", "glow2", "ink", "white", "red"];
type Px = { file: string; rect: number[]; at?: Record<string, number[]>; pin?: number[] };
type ThingPart = { role: string; spots?: string[]; on?: string[]; glow?: boolean; sound?: string; clip?: boolean; outline?: boolean; to?: Record<string, string>; carries?: string[]; px?: Record<string, Px> };
type Look = { sat?: number; light?: number; add?: number; cap?: number };
type Data = { rules: { max_parts: number; px: Record<string, number>; behind?: string[] }; palette: Record<string, string | string[]>; looks?: Record<string, Look>;
  thing: Record<string, ThingPart>; kinds: Record<string, { base: string; signature: string }>;
  body?: { file: string; small: number; shade?: Record<string, number>; plans: Record<string, Plan>; slots: Record<string, Slot & { values: Record<string, Slot & { frames: Record<string, { rect: number[]; pin: number[] }> }> }> } };

let data: Data | null = null, version = 0;
const sheets = new Map<string, ImageData>(), code = new Map<number, number>(), rgb: number[][] = [[0, 0, 0]], light: number[] = [0];
const stamps = new Map<string, Stamp | null>(), things = new Map<string, HTMLCanvasElement>();
let invented: Record<string, Invention> = {};

/** Read the library. Until it has landed (or if it never does) pets are drawn without parts and nothing is composed. */
export async function loadParts(base = "/art"): Promise<void> {
  try {
    const d = (await (await fetch(`${base}/parts.json`)).json()) as Data;
    const files = new Set([...Object.values(d.thing).flatMap((p) => Object.values(p.px ?? {}).map((x) => x.file)), ...(d.body ? [d.body.file] : [])]);
    await Promise.all([...files].map(async (f) => {
      const img = new Image();
      img.src = `${base}/${f}`;
      await img.decode();
      const c = Object.assign(document.createElement("canvas"), { width: img.width, height: img.height }), x = c.getContext("2d", { willReadFrequently: true })!;
      x.drawImage(img, 0, 0);
      sheets.set(f, x.getImageData(0, 0, c.width, c.height));
    }));
    CODES.forEach((name, i) => {
      const hex = (name in d.palette ? d.palette[name] : (d.palette[name.slice(0, -1)] as string[])?.[+name.slice(-1)]) as string | undefined;
      if (!hex) return;
      const n = parseInt(hex, 16), c = [n >> 16, (n >> 8) & 255, n & 255];
      code.set(n, i + 1);
      rgb[i + 1] = c;
      light[i + 1] = (Math.max(...c) + Math.min(...c)) / 510;
    });
    data = d;
    stamps.clear();
    things.clear();
    version++;
  } catch (e) { console.warn("[parts] the parts library would not load", e); }
}
/** Goes up when the library lands, so what was drawn without it is drawn again. */
export const partsVersion = () => version;
export const partsData = () => data;

/** The pixels of one rectangle of a sheet, as codes. */
function codes(file: string, [x0, y0, w, h]: number[]): Uint8Array {
  const im = sheets.get(file), out = new Uint8Array(w * h);
  if (im) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = ((y0 + y) * im.width + x0 + x) * 4;
    if (im.data[i + 3]) out[y * w + x] = code.get((im.data[i] << 16) | (im.data[i + 1] << 8) | im.data[i + 2]) ?? 0;
  }
  return out;
}

// ---- bodies ----------------------------------------------------------------------------------------------------
const BLOB: Plan = { w: 1, h: 1 };
export const bodyPlan = (name: string | undefined): Plan => data?.body?.plans[name ?? ""] ?? BLOB;
/** Under this many pixels wide a body wears the small pictures. */
export const bodySmall = () => data?.body?.small ?? 10;
/** How much lighter (or, below 0, darker) a coat of this shade is. */
export const bodyShade = (name: string | undefined) => data?.body?.shade?.[name ?? ""] ?? 0;
/** How a slot's part is worn (its layer, whether there is one each side …): the slot's own say, then the value's. */
export function bodySlot(slot: string, value: string | undefined): Slot | null {
  const s = data?.body?.slots[slot], v = s?.values[value ?? ""];
  if (!s || !v) return null;
  const { values: _, ...rest } = s, { frames: __, ...own } = v;
  return { ...rest, ...own };
}
export function bodyStamp(slot: string, value: string | undefined, frame: string): Stamp | null {
  const key = `${slot}|${value}|${frame}`;
  if (!stamps.has(key)) {
    const f = data?.body?.slots[slot]?.values[value ?? ""]?.frames[frame];
    stamps.set(key, f ? { w: f.rect[2], h: f.rect[3], px: codes(data!.body!.file, f.rect), pin: [f.pin[0], f.pin[1]] } : null);
  }
  return stamps.get(key)!;
}

// ---- things ----------------------------------------------------------------------------------------------------
const toHsl = (r: number, g: number, b: number) => {
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 510, d = (max - min) / 255;
  if (!d) return [0, 0, l];
  const h = max === r ? ((g - b) / (max - min) + 6) % 6 : max === g ? (b - r) / (max - min) + 2 : (r - g) / (max - min) + 4;
  return [h * 60, d / (1 - Math.abs(2 * l - 1)), l];
};
const toRgb = (h: number, s: number, l: number) => {
  const a = s * Math.min(l, 1 - l), f = (n: number) => { const k = (n + h / 30) % 12; return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))); };
  return [f(0), f(8), f(4)];
};
const within = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** The colour of one pixel of a part in a colour and a material: `main` takes the colour (its hue, with the picture's
 *  own light and dark, as the catalog's sprites are recoloured: px/tint.ts), `trim` a duller tone of it, the rest
 *  (line, glow, white) stay as drawn. */
function paint(c: number, hex: string | null, look: Look): number[] {
  const name = CODES[c - 1], main = name.startsWith("main");
  if (!hex || !(main || name.startsWith("trim"))) return rgb[c];
  const n = parseInt(hex.slice(1), 16);
  let [h, s, tl] = toHsl(n >> 16, (n >> 8) & 255, n & 255), l = within(light[c] + (tl - 0.5) * (main ? 0.55 : 0.3), 0.1, 0.96);
  if (s < 0.35 || tl > 0.85) s *= 0.2;   // white, grey and black are not colours
  if (!main) s *= 0.45;
  if (look.cap != null && l > look.cap) l = look.cap + (l - look.cap) * 0.3;
  return toRgb(h, within(s * (look.sat ?? 1), 0, 1), within(l * (look.light ?? 1) + (look.add ?? 0), 0.1, 0.96));
}

/** A thing put together from its parts (SPEC-v3.5 §1): the first part is what the others sit on, each with its pin on
 *  the spot it was given (or on a part already there that `carries` that spot: a flame in a fork); a part put inside
 *  goes behind, a wrap only where the base's body is. The whole stands in
 *  the middle of the bottom edge of a square of the size's pixels. Anything that glows has a soft halo. */
export function composeThing(rec: Pick<Invention, "parts" | "size" | "glow">): HTMLCanvasElement {
  const key = JSON.stringify([rec.parts, rec.size, rec.glow]);
  let out = things.get(key);
  if (out) return out;
  const D = data, S = D?.rules.px[rec.size ?? "small"] ?? 16, W = S * 3;
  out = Object.assign(document.createElement("canvas"), { width: S, height: S });
  if (!D) return out;   // (not kept: it is made again once the library has landed)
  const col = new Int32Array(W * W).fill(-1), what = new Uint8Array(W * W);   // what: 1 line, 2 body, +4 it glows
  const list = rec.parts.slice(0, D.rules.max_parts).filter((p) => D.thing[p.part]?.px?.[S]);
  const base = list.find((p) => D.thing[p.part].role === "base" && !p.at) ?? list[0];
  if (!base) return out;
  const B: Px = D.thing[base.part].px![S];
  const order = (p: (typeof list)[number]) => (p !== base && (D.rules.behind ?? []).includes(p.at ?? "") ? 0 : p === base ? 1 : D.thing[p.part].clip ? 2 : 3);
  const where = new Map<(typeof list)[number], number[]>(), held: Record<string, number[]> = {};   // where each part goes, in the order they were given: a later one may stand on an earlier
  for (const p of list) {
    const T: ThingPart = D.thing[p.part], P: Px = T.px![S], point = T.to?.[p.at ?? ""] ?? p.at ?? "", spot = p === base ? [0, 0] : held[point] ?? B.at?.[point] ?? held.tip ?? B.at?.tip ?? B.at?.top, pin = p === base ? [0, 0] : P.pin ?? [0, 0];
    if (!spot) continue;   // a spot the base does not have, and no top to fall back on: the part is left off, never drawn loose
    where.set(p, [S + spot[0] - pin[0], S + spot[1] - pin[1]]);
    if (p !== base && T.carries?.includes(point) && P.at?.[point]) held[point] = [spot[0] - pin[0] + P.at[point][0], spot[1] - pin[1] + P.at[point][1]];
  }
  for (const p of [...list].sort((a, b) => order(a) - order(b))) {
    const T: ThingPart = D.thing[p.part], P: Px = T.px![S], hex = PALETTE[p.color ?? ""] ?? (/^#[0-9a-f]{6}$/i.test(p.color ?? "") ? p.color! : null), look = D.looks?.[p.material ?? ""] ?? {};
    const at = where.get(p);
    if (!at) continue;
    const [dx, dy] = at, px = codes(P.file, P.rect);
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      const c = px[y * S + x], k = (y + dy) * W + x + dx;
      if (!c || (T.clip && p !== base && what[k] !== 2 && what[k] !== 6)) continue;
      const [r, g, b] = paint(c, hex, look);
      col[k] = (r << 16) | (g << 8) | b;
      what[k] = (CODES[c - 1] === "ink" ? 1 : 2) | (T.glow ? 4 : 0);
    }
  }
  let [x0, y0, x1, y1] = [W, W, -1, -1];
  for (let k = 0; k < W * W; k++) if (col[k] >= 0) { const x = k % W, y = (k / W) | 0; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  if (x1 < 0) return out;
  const ox = x0 - ((S - (x1 - x0 + 1)) >> 1), oy = y1 - (S - 1), ctx = out.getContext("2d")!, im = ctx.createImageData(S, S);
  const glows = rec.glow || [...what].some((w) => w & 4), lit = (x: number, y: number) => { const k = (y + oy) * W + x + ox; return x + ox >= 0 && y + oy >= 0 && x + ox < W && y + oy < W && col[k] >= 0 && (what[k] & 4 || !list.some((p) => D.thing[p.part].glow)); };
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const k = (y + oy) * W + x + ox, i = (y * S + x) * 4;
    if (k >= 0 && k < W * W && x + ox >= 0 && x + ox < W && col[k] >= 0) im.data.set([col[k] >> 16, (col[k] >> 8) & 255, col[k] & 255, 255], i);
    else if (glows) {   // the halo: warm light on the two pixels round whatever glows, fainter further out
      let near = 9;
      for (let j = -2; j <= 2; j++) for (let n = -2; n <= 2; n++) if (lit(x + n, y + j)) near = Math.min(near, Math.hypot(n, j));
      if (near < 2.9) im.data.set([255, 222, 130, near < 1.5 ? 150 : 70], i);
    }
  }
  ctx.putImageData(im, 0, 0);
  things.set(key, out);
  return out;
}

/** The kinds the house has invented, as the last snapshot gave them. */
export function noteInvented(all: Record<string, Invention> | undefined) { invented = all ?? {}; }
export const inventedKind = (kind: string | null | undefined): Invention | null => (kind && data ? invented[kind] ?? null : null);
/** The sound an invented thing makes when it is used (sounds.json, `instruments`, by this name), if it makes one. */
export const inventedSound = (kind: string | null | undefined) => (kind ? invented[kind]?.sound ?? null : null);
