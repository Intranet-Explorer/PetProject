// Pictures and sounds by our own names (view/assets/README.md). The data in /art/ says where each one lives; nothing
// here, or anywhere else on the page, names a tile, a file or a pack. A name the data does not have gives a visible
// placeholder, never an error.
import { PALETTE } from "./things";
import type { Part } from "./things";

type Pack = { dir: string; local?: boolean; font?: string };
type Sprite = { pack: string; file: string; rect?: number[]; tint?: string; fallback?: string };
type Kind = { sprite?: string; a?: string; wall?: boolean; not?: string[] };
export type Sound = { pack: string; file: string; gain?: number };
/** One layer of a soundscape (README, "ambience"): a file that loops, or a sound the page makes itself (`synth`). */
export type Layer = Partial<Sound> & { synth?: string; rate?: number; pitch?: number; echo?: number; steady?: boolean; when?: "day" | "night"; sfx?: string; says?: string };
type Sounds = { sfx?: Record<string, Sound>; moods?: Record<string, Sound[]>; ambience?: { rooms?: Record<string, Layer[]>; weather?: Record<string, Layer[]> };
  instruments?: Record<string, string | Layer> };
type FromParts = { shape: Record<string, string>; material: Record<string, Record<string, string>>; many: { hanging: string[]; then: string; else: string }; pair?: Record<string, string> };
/** What a made thing is, whichever way it was written down: see kindOf. */
export type Thing = { kind?: string; color?: string; size?: number; material?: string; parts?: Part[] };

const art = {
  packs: {} as Record<string, Pack>, sprites: {} as Record<string, Sprite>, kinds: {} as Record<string, Kind>,
  fromParts: null as FromParts | null, sounds: {} as Sounds,
};
const BASE = "/art/";
const get = async (file: string) => { try { const r = await fetch(BASE + file); return r.ok ? await r.json() : null; } catch { return null; } };

/** Everything is asked for once. Whatever is missing stays empty: the page still draws, with placeholders. */
export const artReady: Promise<void> = Promise.all(["packs.json", "sprites.json", "kinds.json", "kinds-from-parts.json", "sounds.json"].map(get)).then(([packs, sprites, kinds, parts, sounds]) => {
  Object.assign(art, { packs: packs ?? {}, sprites: sprites ?? {}, kinds: kinds ?? {}, fromParts: parts, sounds: sounds ?? {} });
  // a pixel face for the page's headings, if a pack brings one (packs.json: `"font": "<file in the pack>"`)
  const [name, pack] = Object.entries(art.packs).find(([, p]) => p.font && !p.local) ?? [], src = name && fileUrl({ pack: name, file: pack!.font! });
  if (src && typeof FontFace !== "undefined") void new FontFace("PetPixel", `url("${src}")`).load().then((f) => { document.fonts.add(f); document.documentElement.classList.add("pixel"); }, () => {});
});

/** Where a pack's file is served from. A pack kept outside the repository (`local`) cannot be reached from the page. */
function fileUrl(x: { pack: string; file: string }) {
  const pack = art.packs[x.pack];
  return pack && !pack.local ? BASE + encodeURI(`${pack.dir}/${x.file}`) : null;
}
/** A sound file the data names, as its address and how loud; null if it names none, or one that cannot be reached. */
export function clip(s: Partial<Sound> | null | undefined) {
  const url = s?.pack && s.file ? fileUrl({ pack: s.pack, file: s.file }) : null;
  return url ? { url, gain: s!.gain ?? 0.3 } : null;
}
/** A sound effect by our name (pickup, door, bell …), or null. */
export const sound = (name: string) => clip(art.sounds.sfx?.[name]);
/** Everything else the data says the house sounds like (README, "sounds.json"): moods, ambience, instruments. */
export const sounds = () => art.sounds;

const resolve = (name: string, hops = 3): Sprite | null => {
  const s = art.sprites[name];
  if (!s || !s.rect) return null;
  return fileUrl(s) ? s : s.fallback && hops ? resolve(s.fallback, hops - 1) : null;
};
export const hasSprite = (name: string) => !!resolve(name);
/** The first of these names the data has; the last one if it has none (so the placeholder says what is missing). */
export const firstSprite = (...names: string[]) => names.find(hasSprite) ?? names.at(-1)!;

const images = new Map<string, Promise<HTMLImageElement | null>>();
const image = (url: string) => {
  if (!images.has(url)) images.set(url, new Promise((done) => {
    const img = new Image();
    img.onload = () => done(img);
    img.onerror = () => done(null);
    img.src = url;
  }));
  return images.get(url)!;
};

const hsl = (r: number, g: number, b: number) => {
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 510, d = (max - min) / 255;
  if (!d) return [0, 0, l];
  const h = max === r ? ((g - b) / (max - min) + 6) % 6 : max === g ? (b - r) / (max - min) + 2 : (r - g) / (max - min) + 4;
  return [h / 6, d / (1 - Math.abs(2 * l - 1)), l];
};
const rgb = (h: number, s: number, l: number) => {
  const a = s * Math.min(l, 1 - l), f = (n: number) => { const k = (n + h * 12) % 12; return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))); };
  return [f(0), f(8), f(4)];
};
/** Recolour a made thing's picture (README, `tint: "hue"`): hue and saturation become the colour's, lightness stays,
 *  the dark outline and the brightest highlights are left alone. A white or a black thing has to end up pale or dark,
 *  so the colour's own lightness pulls a little (the room does the same: px/tint.ts). `color` is one of our colour
 *  words, or any #rrggbb. */
export function recolor(px: ImageData, color: string) {
  const hex = PALETTE[color] ?? (/^#[0-9a-f]{6}$/i.test(color) ? color : null);
  if (!hex) return px;
  const [h, s, tl] = hsl(parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)), d = px.data;
  for (let i = 0; i < d.length; i += 4) {
    if (!d[i + 3]) continue;
    const [, was, l] = hsl(d[i], d[i + 1], d[i + 2]);
    if (l < 0.2 || (l > 0.9 && was < 0.35)) continue;   // the outline; a highlight
    // a colour with little colour in it (white, grey, black) is mostly a matter of light and dark: less of its tint, more of its lightness
    const pale = s < 0.35;
    [d[i], d[i + 1], d[i + 2]] = rgb(h, pale ? s * 0.3 : s, Math.max(0.08, Math.min(0.96, l + (tl - 0.5) * (pale ? 0.85 : 0.55))));
  }
  return px;
}

function placeholder(c: HTMLCanvasElement, scale: number, name: string) {
  c.width = c.height = 16 * scale;
  c.title = `no picture for “${name}” yet`;
  c.classList.add("missing");
  const x = c.getContext("2d")!;
  x.fillStyle = "#c9bfd6";
  x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = "#5b4a73";
  for (const [px, py, w, h] of [[0, 0, 16, 1], [0, 15, 16, 1], [0, 0, 1, 16], [15, 0, 1, 16], [6, 4, 4, 1], [5, 5, 1, 1], [10, 5, 1, 2], [8, 7, 2, 1], [7, 8, 1, 2], [7, 11, 1, 1]])
    x.fillRect(px * scale, py * scale, w * scale, h * scale);
}

/** The picture called `name`, `scale` screen pixels to each of its own, as a canvas. `color` recolours a picture
 *  the data marks as tintable. It is the right size at once, and is painted as soon as its sheet has loaded. */
export function sprite(name: string, scale = 2, color?: string | null): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.className = "px";
  c.setAttribute("aria-hidden", "true");
  scale = Math.max(1, Math.round(scale));
  const paint = () => {
    const s = resolve(name), url = s && fileUrl(s);
    if (!s || !url) return placeholder(c, scale, name);
    const [sx, sy, w, h] = s.rect!;
    [c.width, c.height] = [w * scale, h * scale];
    void image(url).then((img) => {
      if (!img) return placeholder(c, scale, name);
      const small = document.createElement("canvas");
      [small.width, small.height] = [w, h];
      const sx2 = small.getContext("2d", { willReadFrequently: true })!;
      sx2.drawImage(img, sx, sy, w, h, 0, 0, w, h);
      if (color && s.tint === "hue") sx2.putImageData(recolor(sx2.getImageData(0, 0, w, h), color), 0, 0);
      const x = c.getContext("2d")!;
      x.imageSmoothingEnabled = false;
      x.clearRect(0, 0, c.width, c.height);
      x.drawImage(small, 0, 0, c.width, c.height);
    });
  };
  if (Object.keys(art.sprites).length) paint();
  else { c.width = c.height = 16 * scale; void artReady.then(paint); }
  return c;
}

/** A made thing as a kind, a colour and a size. One made before SPEC-v3.2 was put together from shapes: its largest
 *  part and its material decide, by the same table the engine used on the live house (kinds-from-parts.json). */
export function kindOf(r: Thing): { kind: string; color: string; size: number } {
  if (r.kind) return { kind: r.kind, color: r.color ?? "grey", size: r.size ?? 2 };
  const T = art.fromParts, parts = r.parts ?? [];
  if (!T || !parts.length) return { kind: "sculpture", color: parts[0]?.color ?? "grey", size: 2 };
  const main = parts.reduce((a, b) => (b.size > a.size ? b : a)), m = r.material ?? "";
  let kind = parts.length >= 3 ? (T.many.hanging.includes(m) ? T.many.then : T.many.else)
    : new Set(parts.map((p) => p.shape)).size === 2 && T.pair?.[m] ? T.pair[m] : T.material[m]?.[main.shape] ?? T.shape[main.shape] ?? "sculpture";
  const k = art.kinds[kind];
  if (!k || k.not?.includes(m) || k.wall) kind = T.shape[main.shape] ?? "sculpture";
  return { kind, color: main.color, size: main.size };
}

/** A made thing in plain words: "a blue cushion" (SPEC-v3.2 §6). */
export function aThing(r: Thing) {
  const { kind, color } = kindOf(r), words = `${color} ${kind}`;
  return `${/^[aeiou]/.test(words) ? "an" : "a"} ${words}`;
}

/** A made thing's picture, in its own colour. */
export function thingSprite(r: Thing, scale = 2) {
  const { kind, color } = kindOf(r);
  return sprite(art.kinds[kind]?.sprite ?? `kind.${kind}`, scale, color);
}
