// The art, as data (view/assets/README.md). Everything the room draws is looked up here by a name of ours; no tile,
// file or pack is named in code. A name that is missing draws a small plain box and warns once.
import { Rectangle, Texture, TextureSource } from "pixi.js";
import type { Tile } from "../types";

TextureSource.defaultOptions.scaleMode = "nearest";

/** `flip`: the frames are shown mirrored (a creature drawn facing one way, walking the other). */
export type Anim = { frames: [number, number][]; fps: number; flip?: boolean };
/** `glass` (optional): the part of a window's picture that is sky, as [x, y, w, h] inside the sprite. `slice`: a frame
 *  that stretches, as the widths of its [left, top, right, bottom] borders. */
/** `surface` (optional): where things put away on it stand, as [x, y, w] inside the sprite: a line `w` wide whose left end is at x, y. */
export type SpriteDef = { pack: string; file: string; rect: [number, number, number, number]; anchor?: [number, number]; anims?: Record<string, Anim>;
  tint?: string; fallback?: string; glass?: [number, number, number, number]; slice?: [number, number, number, number]; surface?: [number, number, number] };
export type KindDef = { sprite?: string; wall?: boolean; a?: string; flat?: boolean };
export type Decor = { sprite: string; at: Tile; layer?: string };
/** A room type's layout. `doors`: a kind of door other than the plain one ("gate": sprites door.gate.<dir>.<state>).
 *  A fixture's `wall`: it hangs on the wall (its sprite's anchor says where); `walk`: it can be stood on.
 *  `light.day`: how dim the room is by day. `light.sky` ("open": weather falls in the room; "glass": it shows on a glass roof). */
export type Layout = { type?: string; floor?: (string | null)[][]; walls?: (string | null)[][]; decor?: Decor[]; doors?: string;
  fixtures?: Record<string, { pos: Tile; sprite?: string | null; wall?: boolean; walk?: boolean; layer?: string }>; blocked?: Tile[]; wall_slots?: Tile[];
  bit_spots?: Record<string, Tile[]>; light?: { window?: Tile[]; night?: number; day?: number; sky?: string } };
export type FromParts = { shape?: Record<string, string>; material?: Record<string, Record<string, string>>; many?: { hanging?: string[]; then?: string; else?: string }; pair?: Record<string, string> };

const data = { packs: {} as Record<string, { dir: string; local?: boolean }>, sprites: {} as Record<string, SpriteDef>, kinds: {} as Record<string, KindDef>, fromParts: {} as FromParts };
const images = new Map<string, HTMLImageElement | null>();   // by address; null: it would not load
const sources = new Map<string, TextureSource>();
const textures = new Map<string, Texture>();
const canvases = new Map<string, HTMLCanvasElement>();
const layouts = new Map<string, Layout | null>();
const asked = new Set<string>(), warned = new Set<string>();
let base = "/art";

const json = async <T>(path: string, or: T): Promise<T> => {
  try {
    const r = await fetch(`${base}/${path}`);
    return r.ok ? ((await r.json()) as T) : or;
  } catch { return or; }
};
const address = (d: SpriteDef) => {
  const pack = data.packs[d.pack];
  return pack && !pack.local ? `${base}/${pack.dir}/${d.file}`.replace(/ /g, "%20") : null;   // a local pack is not served: its sprites fall back
};

/** Read the data files and every picture they name. Safe to call again (the page may ask for a reload of the art). */
export async function loadArt(from = "/art") {
  base = from;
  [data.packs, data.sprites, data.kinds, data.fromParts] = await Promise.all([json("packs.json", {}), json("sprites.json", {}), json("kinds.json", {}), json("kinds-from-parts.json", {})]);
  const wanted = new Set(Object.values(data.sprites).map(address).filter((a): a is string => !!a && !images.has(a)));
  await Promise.all([...wanted].map(async (url) => {
    const img = new Image();
    img.src = url;
    try { await img.decode(); images.set(url, img); } catch { images.set(url, null); warn(`picture ${url} would not load`); }
  }));
}

function warn(what: string) {
  if (warned.has(what)) return;
  warned.add(what);
  console.warn(`[room art] ${what}`);
}

/** A sprite's entry, following `fallback` when its own picture is not there. */
export function def(name: string | null | undefined): SpriteDef | null {
  for (let n = name, hops = 0; n && hops < 4; hops++) {
    const d = data.sprites[n];
    if (!d) return null;
    const a = address(d);
    if (a && images.get(a)) return d;
    n = d.fallback;
  }
  return null;
}
export const has = (name: string | null | undefined) => !!def(name);
/** The first of these names that there is a picture for (or the last, the plainest, so that its absence shows). */
export const pick = (...names: (string | null | undefined)[]) => names.find(has) ?? names.filter((n) => !!n).at(-1) ?? "?";
export const kind = (k: string | null | undefined): KindDef | null => (k ? data.kinds[k] ?? null : null);
export const fromParts = () => data.fromParts;

let checks: HTMLCanvasElement | null = null;
function placeholder() {
  if (checks) return checks;
  checks = document.createElement("canvas");   // a small plain box standing on its tile: nothing is ever a hole, or an alarm, for want of a picture
  checks.width = checks.height = 16;
  const x = checks.getContext("2d")!;
  for (const [c, bx, by, w, h] of [["#2b2233", 3, 7, 10, 9], ["#b9a88a", 4, 8, 8, 7], ["#d8cbb0", 4, 8, 8, 2], ["#8f7f66", 4, 14, 8, 1]] as const) { x.fillStyle = c; x.fillRect(bx, by, w, h); }
  return checks;
}

function cell(d: SpriteDef, anim?: string, i = 0): [number, number, number, number] {
  const [x, y, w, h] = d.rect, f = anim ? d.anims?.[anim]?.frames : undefined;
  if (!f?.length) return [x, y, w, h];
  const [col, row] = f[i % f.length];
  return [x + col * w, y + row * h, w, h];
}

/** How many frames an animation has, and how fast it plays; null if the sprite has no such animation. */
export function anim(name: string, a: string): Anim | null {
  return def(name)?.anims?.[a] ?? null;
}
/** Width and height of a sprite, and the pixel of it that sits on the top-left corner of its tile. */
export function size(name: string): { w: number; h: number; ax: number; ay: number } {
  const d = def(name);
  if (!d) return { w: 16, h: 16, ax: 0, ay: 0 };
  return { w: d.rect[2], h: d.rect[3], ax: d.anchor?.[0] ?? 0, ay: d.anchor?.[1] ?? d.rect[3] - 16 };
}

/** The texture for a sprite (or one frame of one of its animations). */
export function tex(name: string, a?: string, i = 0): Texture {
  const key = `${name}|${a ?? ""}|${i}`;
  let t = textures.get(key);
  if (t) return t;
  const d = def(name);
  if (!d) {
    warn(`no sprite "${name}"`);
    t = fromCanvas(placeholder());
  } else {
    const url = address(d)!;
    let src = sources.get(url);
    if (!src) sources.set(url, (src = Texture.from(images.get(url)!).source));
    const [x, y, w, h] = cell(d, a, i);
    t = new Texture({ source: src, frame: new Rectangle(x, y, w, h) });
  }
  textures.set(key, t);
  return t;
}

/** The same picture as a canvas of its own: for recolouring, and for the page's hover card. Do not draw on it. */
export function canvasOf(name: string, a?: string, i = 0): HTMLCanvasElement {
  const key = `${name}|${a ?? ""}|${i}`;
  let c = canvases.get(key);
  if (c) return c;
  const d = def(name);
  if (!d) return placeholder();
  const [x, y, w, h] = cell(d, a, i);
  c = document.createElement("canvas");
  [c.width, c.height] = [w, h];
  c.getContext("2d")!.drawImage(images.get(address(d)!)!, x, y, w, h, 0, 0, w, h);
  canvases.set(key, c);
  return c;
}

export function fromCanvas(c: HTMLCanvasElement): Texture {
  const t = Texture.from(c);
  t.source.scaleMode = "nearest";
  return t;
}

/** A room type's layout: null if it has none, undefined while it is still on its way (`then` is called when it lands). */
export function layout(type: string | null, then: () => void): Layout | null | undefined {
  if (!type) return null;
  if (layouts.has(type)) return layouts.get(type);
  if (!asked.has(type)) {
    asked.add(type);
    json<Layout | null>(`rooms/${encodeURIComponent(type)}.json`, null).then((l) => { layouts.set(type, l); then(); });
  }
  return undefined;
}
