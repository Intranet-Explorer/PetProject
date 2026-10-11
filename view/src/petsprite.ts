// A pet as pixel art, made from its genome (SPEC-v3.2 §2). This file is the agreed interface; the drawing itself is
// a placeholder until the real generator replaces it. Everything else in the view draws pets only through this.
import type { Genome } from "./pet";

export type PetAnim = "idle" | "walk.down" | "walk.up" | "walk.left" | "walk.right" | "sit" | "sleep" | "eat" | "make" | "happy" | "sad" | "startled";
export const PET_ANIMS: PetAnim[] = ["idle", "walk.down", "walk.up", "walk.left", "walk.right", "sit", "sleep", "eat", "make", "happy", "sad", "startled"];
/** `size`: the side of a frame in source pixels (24 or 32). `frames[anim]`: that many canvases, each size x size, the
 *  pet standing on the bottom edge and centred. `fps`: how fast each plays. `egg`: an egg of this genome's colours
 *  (two frames: still, and rocking). `dead`: lying still. */
export type PetSheet = { size: number; frames: Record<PetAnim, HTMLCanvasElement[]>; fps: Record<PetAnim, number>; egg: HTMLCanvasElement[]; dead: HTMLCanvasElement };
/** `grey` 0 to 1: an elder's greying. */
export type PetLook = { grey?: number };

const cache = new Map<string, PetSheet>();

/** The sheet for a body at a stage (hatchling, child, youngling, adult, elder). Cached: call it every frame if you like. */
export function petSheet(g: Genome, stage: string, look: PetLook = {}): PetSheet {
  const key = JSON.stringify([g, stage, Math.round((look.grey ?? 0) * 4)]);
  let sheet = cache.get(key);
  if (!sheet) cache.set(key, (sheet = build(g, stage, look)));
  return sheet;
}

/** One still picture (the first idle frame) scaled by a whole number, for a card or the family tree. */
export function petPortrait(g: Genome, stage: string, scale = 2, look: PetLook = {}): HTMLCanvasElement {
  const sheet = petSheet(g, stage, look), src = stage === "egg" ? sheet.egg[0] : sheet.frames.idle[0];
  const c = document.createElement("canvas");
  c.width = c.height = sheet.size * scale;
  const x = c.getContext("2d")!;
  x.imageSmoothingEnabled = false;
  x.drawImage(src, 0, 0, c.width, c.height);
  return c;
}

function build(g: Genome, stage: string, _look: PetLook): PetSheet {
  const size = 24, k = { hatchling: 0.55, child: 0.7, youngling: 0.85, adult: 1, elder: 0.95 }[stage] ?? 1;
  const frame = (dy = 0) => {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    const x = c.getContext("2d")!;
    x.fillStyle = `hsl(${g.hue}, ${Math.round(g.saturation * 100)}%, 55%)`;
    const w = Math.round(14 * k), h = Math.round(14 * k * g.stretch);
    x.fillRect((size - w) >> 1, size - h - dy, w, h);
    x.fillStyle = "#16241f";
    x.fillRect((size >> 1) - 3, size - h - dy + 3, 2, 2);
    x.fillRect((size >> 1) + 1, size - h - dy + 3, 2, 2);
    return c;
  };
  const frames = {} as Record<PetAnim, HTMLCanvasElement[]>, fps = {} as Record<PetAnim, number>;
  for (const a of PET_ANIMS) { frames[a] = [frame(0), frame(1)]; fps[a] = a.startsWith("walk") ? 8 : 2; }
  return { size, frames, fps, egg: [frame(0), frame(1)], dead: frame(0) };
}
