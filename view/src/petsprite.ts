// A pet as pixel art, made from its genome (SPEC-v3.2 §2). Everything else in the view draws pets only through this.
// Each frame is painted pixel by pixel into a 24x24 grid of palette slots, then copied to a canvas: no vector
// drawing, no smoothing, no randomness that is not in the genome, so the same genome always gives the same pixels.
import type { Genome } from "./pet";

export type PetAnim = "idle" | "walk.down" | "walk.up" | "walk.left" | "walk.right" | "sit" | "sleep" | "eat" | "make" | "happy" | "sad" | "startled";
export const PET_ANIMS: PetAnim[] = ["idle", "walk.down", "walk.up", "walk.left", "walk.right", "sit", "sleep", "eat", "make", "happy", "sad", "startled"];
/** `size`: the side of a frame in source pixels (24 or 32). `frames[anim]`: that many canvases, each size x size, the
 *  pet standing on the bottom edge and centred. `fps`: how fast each plays. `egg`: an egg of this genome's colours
 *  (two frames: still, and rocking). `dead`: lying still. */
export type PetSheet = { size: number; frames: Record<PetAnim, HTMLCanvasElement[]>; fps: Record<PetAnim, number>; egg: HTMLCanvasElement[]; dead: HTMLCanvasElement };
/** `grey` 0 to 1: an elder's greying. */
export type PetLook = { grey?: number };

const cache = new Map<string, PetSheet>();   // ponytail: never emptied; a house makes a few new bodies a night, each sheet a few dozen 24x24 canvases

/** The sheet for a body at a stage (hatchling, child, youngling, adult, elder). Cached: call it every frame if you like. */
export function petSheet(g: Genome, stage: string, look: PetLook = {}): PetSheet {
  const grey = Math.round(Math.min(1, Math.max(0, look.grey ?? 0)) * 4) / 4;
  const key = JSON.stringify([g, stage, grey]);
  let sheet = cache.get(key);
  if (!sheet) cache.set(key, (sheet = build(g, stage, grey)));
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

// ---------------------------------------------------------------------------------------------------------------
const S = 24;   // 24, not 32: an adult is 14 pixels across beside the pack's 16-pixel people, with room left to jump
// palette slots
const INK = 1, DARK = 2, MID = 3, LIGHT = 4, SHINE = 5, PAT = 6, WHITE = 7, PALE = 8, RED = 9, TEAR = 10;
type RGB = [number, number, number];

/** Width of the body's colour in pixels (the outline adds one each side); `soft`: how far a young body is pulled
 *  toward round and squat; `face`: how far down the body the eyes sit; `stoop`: an elder's. */
const STAGES: Record<string, { w: number; soft: number; face: number; stoop: number; slow: number }> = {
  hatchling: { w: 7, soft: 0.5, face: 0.5, stoop: 0, slow: 1 },
  child: { w: 9, soft: 0.25, face: 0.44, stoop: 0, slow: 1 },
  youngling: { w: 10, soft: 0.1, face: 0.4, stoop: 0, slow: 1 },
  adult: { w: 12, soft: 0, face: 0.36, stoop: 0, slow: 1 },
  elder: { w: 12, soft: 0, face: 0.36, stoop: 1, slow: 0.75 },
};

type Eyes = "open" | "shut" | "half" | "sad" | "happy" | "wide" | "x" | "sleep";
type Mouth = "flat" | "none" | "smile" | "open" | "frown" | "o";
/** One frame. dy: lifted off the floor. dh, dw: taller, wider (dw on each side). lean: the top pushed sideways.
 *  look: eyes lowered. feet: each foot's sideways step, or 9 for lifted. arms: raised by so many pixels.
 *  paws: 1 or 2, both paws out and busy, which one is up. tear: 1 or 2, how far a tear has run. */
type Pose = { face?: "down" | "up" | "left" | "right"; dy?: number; dh?: number; dw?: number; dx?: number; lean?: number; eyes?: Eyes; mouth?: Mouth;
  look?: number; feet?: [number, number]; arms?: number; paws?: number; sit?: boolean; curl?: boolean; tear?: number };

const at = (x: number, y: number) => (x < 0 || y < 0 || x >= S || y >= S ? -1 : y * S + x);
const has = (b: Uint8Array, x: number, y: number) => { const k = at(x, y); return k >= 0 && b[k] !== 0; };
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

function hsl(h: number, s: number, l: number): RGB {
  h = ((h % 360) + 360) % 360; s = clamp(s, 0, 1); l = clamp(l, 0, 1);
  const a = s * Math.min(l, 1 - l), f = (n: number) => { const k = (n + h / 30) % 12; return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))); };
  return [f(0), f(8), f(4)];
}
/** A hue moved `by` degrees toward another, the short way round: shadows lean blue, lights lean yellow, as the pack's do. */
function toward(h: number, target: number, by: number) {
  const d = ((target - h + 540) % 360) - 180;
  return h + Math.sign(d) * Math.min(Math.abs(d), by);
}

function palette(g: Genome, grey: number, egg = false): RGB[] {
  const h = g.hue, s = (0.16 + 0.56 * g.saturation) * (1 - 0.6 * grey);
  const l = 0.55 + 0.05 * Math.cos(((h - 250) * Math.PI) / 180) + 0.06 * grey;      // blues a touch lighter, yellows darker
  const ink: RGB = [0x14, 0x1b, 0x1b], white: RGB = [0xf3, 0xf7, 0xf2], red: RGB = [0xc4, 0x48, 0x4a], tear: RGB = [0x8f, 0xd6, 0xf2];
  if (egg) return [[0, 0, 0], ink, hsl(toward(h, 260, 10), s * 0.6, 0.67), hsl(h, s * 0.6, 0.81), hsl(h, s * 0.5, 0.89), white, hsl(h, s * 0.85, 0.63), white, white, red, tear];
  return [[0, 0, 0], ink, hsl(toward(h, 260, 14), s * 0.92, l - 0.16), hsl(h, s, l), hsl(toward(h, 55, 10), s, l + 0.13), hsl(toward(h, 55, 14), s * 0.5, 0.9),
    hsl(toward(h, 260, 20), s * 0.85, l - 0.29), white, hsl(h, s * 0.4, Math.min(0.88, l + 0.24)), red, tear];
}

/** The body: a box with rounded corners (roundness sets how round), flatter underneath so it sits. With `egg`, an
 *  egg shape instead, widest that fraction of the way down (0.58 an egg, 0.75 a mound). */
function blob(b: Uint8Array, x0: number, bot: number, w: number, h: number, round: number, lean: number, egg = 0) {
  const r = clamp((Math.min(w, h) / 2) * round, Math.min(2, Math.min(w, h) / 2), Math.min(w, h) / 2), rb = Math.max(Math.min(1.5, r), r * 0.6);
  for (let j = 0; j < h; j++) {
    const py = j + 0.5 - h / 2, rr = py > 0 ? rb : r, shift = h > 1 ? Math.round((lean * (h - 1 - j)) / (h - 1)) : 0;
    for (let i = 0; i < w; i++) {
      const px = i + 0.5 - w / 2;
      let inside: boolean;
      if (egg) {
        const cy = j + 0.5 - h * egg, ry = cy < 0 ? h * egg : h * (1 - egg);
        inside = (px / (w / 2)) ** 2 + (cy / ry) ** 2 <= 1;
      } else {
        const qx = Math.max(Math.abs(px) - (w / 2 - rr), 0), qy = Math.max(Math.abs(py) - (h / 2 - rr), 0);
        inside = qx * qx + qy * qy <= rr * rr;
      }
      const k = at(x0 + i + shift, bot - h + 1 + j);
      if (inside && k >= 0) b[k] = MID;
    }
  }
}

/** Light from the upper left: a light crown, a dark underside and right rim. Works from the shape alone. */
function shade(b: Uint8Array) {
  let x1 = S, x2 = -1, y1 = S, y2 = -1;
  for (let k = 0; k < S * S; k++) if (b[k]) { const x = k % S, y = (k / S) | 0; x1 = Math.min(x1, x); x2 = Math.max(x2, x); y1 = Math.min(y1, y); y2 = Math.max(y2, y); }
  for (let y = y1; y <= y2; y++) for (let x = x1; x <= x2; x++) {
    if (!has(b, x, y)) continue;
    const u = (x - x1) / Math.max(1, x2 - x1), v = (y - y1) / Math.max(1, y2 - y1), d = u * 0.6 + v;
    const under = !has(b, x, y + 1), right = !has(b, x + 1, y), over = !has(b, x, y - 1), left = !has(b, x - 1, y);
    b[at(x, y)] = under || (right && v > 0.3) || d > 1.25 ? DARK : d < 0.45 || ((over || left) && u + v < 0.8) ? LIGHT : MID;
  }
  return [x1, y1, x2, y2];
}

/** The same pseudo-random numbers for every pet, so relatives' speckles fall in the same places. */
function fixedRandom(seed: number) {
  return () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);
}
const PATCHES = [[0.82, 0.16], [0.14, 0.72], [0.7, 0.86], [0.2, 0.08]];   // where patches sit, as fractions of the body

/** The pattern's pixels as [column, row] within a body of w x h colour pixels, seen from `view` (0 front, 2 back, -1/1 side). */
function patternCells(g: Genome, w: number, h: number, view: number): [number, number][] {
  const out: [number, number][] = [], d = g.pattern_density, back = view === 2;
  if (g.pattern === "speckle") {
    const rnd = fixedRandom(7), n = Math.max(2, Math.round(((3 + d * 12) * w * h) / 150));
    for (let i = 0; i < n; i++) {
      const x = Math.floor(rnd() * w), y = Math.floor(rnd() * h);
      out.push([x, y]);
      if (i % 3 === 0 && w > 8) out.push([x + 1, y]);
    }
  } else if (g.pattern === "stripe") {
    const n = Math.min(2 + Math.round(d * 4), Math.floor(h / 2.5));
    for (let k = 0; k < n; k++) {
      const y = Math.round(((k + 0.5) * h) / n - 0.5);
      for (let x = 0; x < w; x++) out.push([x, y]);                 // right across; the face is kept clear by the caller
    }
  } else if (g.pattern === "patch") {
    const r = Math.max(1.3, w * 0.24);
    for (const [u, v] of PATCHES.slice(0, 1 + Math.round(d * 3)))
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if ((x + 0.5 - u * w) ** 2 + (y + 0.5 - v * h) ** 2 <= r * r) out.push([x, y]);
  }
  return back ? out.map(([x, y]) => [w - 1 - x, y]) : out;
}

/** A small part stuck on: `c` in a w x h box with ink round it. Soft: the ink only goes where nothing is drawn yet,
 *  so the part reads as growing out of the body. */
function nub(m: Uint8Array, x: number, y: number, w: number, h: number, c: number, hard = false) {
  for (let j = -1; j <= h; j++) for (let i = -1; i <= w; i++) {
    const edge = +(i < 0 || i >= w) + +(j < 0 || j >= h), k = at(x + i, y + j);
    if (edge === 2 || k < 0) continue;
    if (!edge) m[k] = c;
    else if (hard || m[k] === 0) m[k] = INK;
  }
}

function drawPet(g: Genome, stage: string, p: Pose): Uint8Array {
  const st = STAGES[stage] ?? STAGES.hatchling, m = new Uint8Array(S * S), b = new Uint8Array(S * S);
  const face = p.face ?? "down", side = face === "left" ? -1 : face === "right" ? 1 : 0, back = face === "up", view = back ? 2 : side;
  const stretch = 1 + (g.stretch - 1) * (1 - st.soft), round0 = g.roundness + (1 - g.roundness) * st.soft;
  const w0 = st.w, h0 = Math.max(5, Math.round(w0 * (0.3 + 0.7 * stretch))) - st.stoop;
  const curl = !!p.curl;
  const w = curl ? w0 + 2 * Math.max(1, Math.round(w0 * 0.14)) : w0 + 2 * (w0 < 9 ? 0 : (p.dw ?? 0));       // a hatchling is too small to spread
  const h = curl ? Math.max(5, Math.round(w * 0.56)) + (p.dh ?? 0) : Math.max(3, h0 + (p.dh ?? 0));
  const feet = curl || p.sit ? 0 : Math.min(g.limbs, 2), arms = curl ? 0 : p.paws ? 2 : clamp(g.limbs - 2, 0, 2);   // busy paws come out even of an armless body
  const dy = clamp(p.dy ?? 0, 0, S - 2 - (feet ? 1 : 0) - h - 1);
  const bot = S - 2 - (feet ? 1 : 0) - dy, top = bot - h + 1, x0 = ((S - w) >> 1) + (p.dx ?? 0);
  const lean = w0 < 9 ? 0 : clamp((p.lean ?? 0) + side * st.stoop, -2, 2);                 // a hatchling is too small to lean and keep its shape
  const shift = (y: number) => (h > 1 ? Math.round((lean * (bot - y)) / (h - 1)) : 0);      // how far a row is pushed over
  const mx = (x: number) => (back ? 2 * x0 + w - 1 - x : x);                                 // seen from behind, left is right

  blob(b, x0, bot, w, h, round0, lean, curl ? 0.75 : 0);

  if (g.marks.some((k) => k.includes("notch"))) {                // a nick out of the top edge
    const nx = mx(x0 + Math.round(w * 0.68)), step = back ? -1 : 1;
    for (const [x, deep] of [[nx, 2], [nx + step, 1]]) for (let y = top, n = 0; y <= bot && n < deep; y++) { const k = at(x + shift(y), y); if (k >= 0 && b[k]) { b[k] = 0; n++; } else if (n) break; }
  }
  const box = shade(b);
  const set = (x: number, y: number, c: number, row = y) => { const k = at(x + shift(row), y); if (k >= 0 && b[k]) b[k] = c; };   // only ever on the body; `row`: lean as that row leans, so an eye stays square

  // where the face is, so the pattern keeps off it
  const es = g.eye_size;
  let ew = clamp(Math.round(0.7 + es * 2.3), 1, 3);
  const eh = Math.min(clamp(Math.round(1.5 + es * 2.5), 2, 4), Math.max(1, Math.floor(h0 * 0.36)));
  const gapMin = w0 % 2 ? 1 : 2;
  let gap = Math.round(w0 * (0.2 + 0.58 * g.eye_spacing) - ew);
  if ((w0 - gap) % 2) gap += 1;
  while (ew > 1 && gapMin + 2 * ew > w0 - (w0 > 7 ? 2 : 0)) ew--;
  gap = clamp(gap, gapMin, Math.max(gapMin, w0 - 2 - 2 * ew));
  const xc = x0 + (w - w0) / 2;                                   // the unwidened body's left edge: the face does not stretch
  const turn = side * Math.round(w0 / 4) - (curl ? Math.max(1, Math.round(w0 * 0.15)) : 0);
  const ey = curl ? Math.max(top + 1, bot - 2 - Math.min(eh, 2)) : clamp(top + Math.round(h0 * st.face - eh / 2) + (p.look ?? 0), top + 1, Math.max(top + 1, bot - eh - 1));
  const eyeH = curl ? 2 : eh;
  const eyesAt = [xc + (w0 - gap) / 2 - ew + turn, xc + (w0 + gap) / 2 + turn];
  const cl = xc + ((w0 - 1) >> 1) + turn, cr = xc + (w0 >> 1) + turn;    // the middle column(s) of the face
  const my = Math.min(ey + eyeH + (h0 - (ey - top) - eyeH >= 5 ? 1 : 0), bot - 1);

  for (const [px, py] of patternCells(g, w0, h0, view)) {
    const x = xc + px, y = top + py;
    if (!back && x >= eyesAt[0] - 1 && x <= eyesAt[1] + ew && y >= ey - 1 && y <= my + 1) continue;
    set(x, y, PAT);
  }
  if (g.marks.some((k) => k.includes("patch"))) {                // faded where the sun fell: a pale place low on one side
    const cx = mx(xc + Math.round(w0 * 0.74)), cy = top + Math.round(h0 * 0.7), r = Math.max(1.2, w0 * 0.2);
    for (let y = -3; y <= 3; y++) for (let x = -3; x <= 3; x++) if (x * x + y * y <= r * r) set(cx + x, cy + y, PALE);
  }
  if (g.marks.some((k) => k.includes("streak"))) for (let i = 0; i < Math.max(2, Math.round(h0 * 0.35)); i++) set(mx(xc + Math.round(w0 * 0.22) + (i >> 1)), top + 1 + i, PALE);
  if (g.marks.some((k) => k.includes("scar"))) for (let i = 0; i < 3; i++) set(mx(xc + 1 + i), bot - 2 - i, RED);

  if (!back) {
    const eyes = p.eyes ?? "open", lo = x0 + (w > 7 ? 1 : 0), hi = x0 + w - 1 - (w > 7 ? 1 : 0);
    eyesAt.forEach((ex0, n) => {
      const out = n ? 1 : -1, inner = n ? ex0 : ex0 + ew - 1;                       // which way is outward; the column nearest the nose
      const xa = Math.max(ex0, lo), xb = Math.min(ex0 + ew - 1, hi);
      if (xb - xa + 1 < Math.max(1, ew - 1)) return;                                // turned out of sight
      const mid = ey + (eyeH >> 1), dot = (x: number, y: number, c: number) => set(x, y, c, mid);
      if (eyes === "open") {
        for (let y = ey; y < ey + eyeH; y++) for (let x = xa; x <= xb; x++) dot(x, y, INK);
        if (xb > xa) dot(xa, ey, WHITE);
      } else if (eyes === "half" || eyes === "sad") {                                // the lid half down: only the lower half shows
        const from = ey + ((eyeH + 1) >> 1);
        for (let y = from; y < ey + eyeH; y++) for (let x = xa; x <= xb; x++) dot(x, y, INK);
        if (eyes === "sad") dot(inner, from - 1, INK);                               // and the inner corner drawn up
      } else if (eyes === "shut" || eyes === "sleep") {
        for (let x = Math.min(xa, inner + out); x <= Math.max(xb, inner + out); x++) dot(x, mid, INK);
        if (eyes === "sleep") dot(inner + out * Math.max(2, ew), mid - 1, INK);       // a lash turned up at the outer end
      } else if (eyes === "happy") {                                                 // a little caret
        const c = ew === 2 ? (n ? ex0 + 1 : ex0) : ex0 + (ew >> 1);
        dot(c, mid - 1, INK); dot(c - 1, mid, INK); dot(c + 1, mid, INK);
      } else if (eyes === "wide") {                                                  // white all round a small pupil
        const x1 = n ? xa : xa - 1, x2 = n ? xb + 1 : xb;
        for (let y = ey - 1; y < ey + eyeH; y++) for (let x = Math.max(x1, lo); x <= Math.min(x2, hi); x++) dot(x, y, WHITE);
        dot(inner, mid, INK);
        if (eyeH > 2) dot(inner, mid - 1, INK);
      } else if (eyes === "x") {
        const c = n ? ex0 + (ew >> 1) : ex0 + ((ew - 1) >> 1);
        if (w0 >= 9 && gap >= 2) for (const [x, y] of [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]]) dot(c + x, mid + y, INK);
        else for (let x = xa; x <= Math.max(xb, xa + 1); x++) dot(x, mid, INK);
      }
      if (p.tear && n === 0) dot(xa, Math.min(ey + eyeH + p.tear - 1, bot - 1), TEAR);
    });
    const mouth = curl ? "none" : (p.mouth ?? "flat"), ml = side > 0 ? cr : cl, mr = side < 0 ? cl : cr;   // in profile the mouth is one pixel
    if (mouth === "flat") for (let x = ml; x <= mr; x++) set(x, my, INK, my);
    else if (mouth === "smile") { set(ml - 1, my, INK, my); set(mr + 1, my, INK, my); for (let x = ml; x <= mr; x++) set(x, my + 1, INK, my); }
    else if (mouth === "frown") { set(ml - 1, my + 1, INK, my); set(mr + 1, my + 1, INK, my); for (let x = ml; x <= mr; x++) set(x, my, INK, my); }
    else if (mouth === "open" || mouth === "o") {
      const a = ml - (ml === mr && w0 >= 9 ? 1 : 0), z = mr + (ml === mr && w0 >= 9 ? 1 : 0);
      for (let x = a; x <= z; x++) { set(x, my, INK, my); set(x, my + 1, mouth === "open" ? RED : INK, my); }
      if (mouth === "open" && w0 >= 9) for (let x = a; x <= z; x++) set(x, my + 2, INK, my);
    }
  }
  // a glint on the crown
  const sx = box[0] + Math.round((box[2] - box[0]) * 0.24), sy = box[1] + Math.max(1, Math.round((box[3] - box[1]) * 0.12));
  for (let i = 0; i < (w0 >= 10 ? 2 : 1); i++) { const k = at(sx + i, sy); if (k >= 0 && (b[k] === LIGHT || b[k] === MID)) b[k] = SHINE; }

  if (curl && w0 >= 9) {                                         // its tail wrapped round in front of it
    const xs = x0 + Math.round(w * 0.42);
    for (let x = xs; x < x0 + w; x++) { set(x, bot - 1, INK); set(x, bot, x < xs + 2 ? LIGHT : MID); }
    set(xs - 1, bot, INK);
  }

  // the body goes down first, inked all round; then what sticks out of it
  for (let k = 0; k < S * S; k++) if (b[k]) {
    m[k] = b[k];
    const x = k % S, y = (k / S) | 0;
    for (const [i, j] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const n = at(x + i, y + j); if (n >= 0 && !b[n]) m[n] = INK; }
  }
  const edge = (y: number, dir: number) => { for (let x = dir < 0 ? 0 : S - 1; x >= 0 && x < S; x -= dir) if (has(b, x, y)) return x; return dir < 0 ? x0 : x0 + w - 1; };

  if (feet) {
    const a = Math.max(1, Math.round(w0 * 0.17)), where = feet === 1 ? [xc + (w0 >> 1) - 1] : [xc + a, xc + w0 - a - 2];
    where.forEach((fx, n) => {
      const step = (p.feet ?? [0, 0])[feet === 1 ? 0 : n];
      if (step === 9) return;
      for (let y = bot; y > bot - 3; y--) if (has(b, fx + step, y) || has(b, fx + step + 1, y)) { nub(m, fx + step, y + 1, 2, bot + 1 - y, DARK); break; }
    });
  }
  if (p.sit && g.limbs) {                                        // sitting: its feet out in front of it
    const a = Math.max(1, Math.round(w0 * 0.17));
    for (const fx of g.limbs === 1 ? [xc + (w0 >> 1) - 1] : [xc + a, xc + w0 - a - 2]) nub(m, fx, bot, 2, 1, DARK, true);
  }
  const ay = clamp(top + Math.round(h * 0.55) - (p.arms ?? 0), top + 1, bot - 1), aw = w0 >= 10 ? 2 : 1, ah = (p.arms ?? 0) > 0 ? 3 : 2;
  if (side) {
    if (arms > (side > 0 ? 0 : 1)) { const ax = x0 + (w >> 1) - 1 + shift(ay) - ((p.arms ?? 0) ? side : 0); nub(m, ax, ay, 2, 2, DARK); for (const i of [0, 1]) { const k = at(ax + i, ay + 2); if (k >= 0) m[k] = INK; } }   // the arm on the side we can see
    const ty = Math.max(top + 1, bot - 2), tx = edge(ty, -side);                                                              // a tuft of tail behind
    nub(m, tx - side - (side < 0 ? 0 : aw - 1), ty, aw, 2, LIGHT);
  } else {
    for (let n = 0; n < arms; n++) {
      const left = (n === 0) !== back, y = p.paws ? clamp(ay + (p.paws === n + 1 ? -2 : 1), top + 1, bot - 1) : ay, x = edge(y, left ? -1 : 1);
      nub(m, left ? x - aw : x + 1, y, aw, ah, DARK);
    }
    if (back) { const tx = xc + (w0 >> 1) - 1; for (const [i, j] of [[0, 0], [1, 0], [0, -1], [1, -1]]) { const k = at(tx + i, bot + j); if (k >= 0 && b[k]) m[k] = LIGHT; } }
  }
  return m;
}

function drawEgg(g: Genome, rock: number): Uint8Array {
  const m = new Uint8Array(S * S), b = new Uint8Array(S * S), w = 10, h = 12, x0 = (S - w) >> 1, bot = S - 2;
  blob(b, x0, bot, w, h, 1, rock, 0.58);
  shade(b);
  for (const [px, py] of patternCells(g, w, h, 2)) { const y = bot - h + 1 + py, k = at(x0 + px + Math.round((rock * (bot - y)) / (h - 1)), y); if (k >= 0 && b[k]) b[k] = PAT; }
  for (let k = 0; k < S * S; k++) if (b[k]) {
    m[k] = b[k];
    for (const [i, j] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const n = at((k % S) + i, ((k / S) | 0) + j); if (n >= 0 && !b[n]) m[n] = INK; }
  }
  const k = at(x0 + 3 + rock, bot - h + 3);
  if (m[k] !== PAT) m[k] = SHINE;
  return m;
}

/** Dead: tipped over onto its side if it is tall, onto its back if it is squat; resting on the floor, centred. */
function lying(src: Uint8Array, onBack: boolean): Uint8Array {
  const t = new Uint8Array(S * S), out = new Uint8Array(S * S);
  let x1 = S, x2 = -1, y2 = -1;
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) if (src[y * S + x]) {
    const nx = onBack ? x : S - 1 - y, ny = onBack ? S - 1 - y : x;
    t[ny * S + nx] = src[y * S + x]; x1 = Math.min(x1, nx); x2 = Math.max(x2, nx); y2 = Math.max(y2, ny);
  }
  const dx = ((S - (x2 - x1 + 1)) >> 1) - x1, dy = S - 1 - y2;
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) { const k = at(x + dx, y + dy); if (t[y * S + x] && k >= 0) out[k] = t[y * S + x]; }
  return out;
}

function toCanvas(m: Uint8Array, pal: RGB[]): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = c.height = S;
  const x = c.getContext("2d")!, img = x.createImageData(S, S);
  for (let k = 0; k < S * S; k++) if (m[k]) { const [r, g, b] = pal[m[k]]; img.data.set([r, g, b, 255], k * 4); }
  x.putImageData(img, 0, 0);
  return c;
}

function build(g: Genome, stage: string, grey: number): PetSheet {
  const pal = palette(g, grey), st = STAGES[stage] ?? STAGES.hatchling, made = new Map<string, HTMLCanvasElement>();
  const f = (p: Pose = {}) => {                                  // the same pose is the same canvas
    const key = JSON.stringify(p);
    let c = made.get(key);
    if (!c) made.set(key, (c = toCanvas(drawPet(g, stage, p), pal)));
    return c;
  };
  const amp = g.wobble < 0.34 ? 0 : g.wobble < 0.67 ? 1 : 2;     // wobble: how much it moves when it breathes and walks
  const sway = amp ? 1 : 0, wide = amp === 2 ? 1 : 0, steps = g.limbs >= 2;
  const walk = (face: Pose["face"]): HTMLCanvasElement[] => {
    const side = face === "left" ? -1 : face === "right" ? 1 : 0, lean = side;
    if (!steps) return [                                         // no two feet to step with: it hops
      f({ face, dh: -1, dw: wide, lean }), f({ face, dy: 1, dh: 1, lean: lean * 2 || 0 }), f({ face, dy: 2 + sway, lean }), f({ face, dy: 1, lean }),
    ];
    return side
      ? [f({ face, feet: [-1, 1], lean, dh: -wide }), f({ face, feet: side < 0 ? [1, 9] : [9, -1], lean, dh: 1 }), f({ face, feet: [-1, 1], lean, dh: -wide, arms: 1 }), f({ face, feet: side < 0 ? [9, -1] : [1, 9], lean, dh: 1, arms: 1 })]
      : [f({ face, dh: -wide }), f({ face, feet: [9, 0], dh: 1, lean: -sway }), f({ face, dh: -wide }), f({ face, feet: [0, 9], dh: 1, lean: sway })];
  };
  const a = f(), b1 = f({ dh: -1, dw: sway, lean: -wide }), b2 = f({ dh: -1, dw: sway, lean: wide });   // breathing: steady, then spreading, then swaying too
  const frames: Record<PetAnim, HTMLCanvasElement[]> = {
    idle: [a, a, b1, b1, a, a, b2, b2, a, f({ eyes: "shut" }), b1, b1, a, a, b2, b2],
    "walk.down": walk("down"), "walk.up": walk("up"), "walk.left": walk("left"), "walk.right": walk("right"),
    sit: [f({ sit: true, dh: -1, dw: 1, eyes: "half" }), f({ sit: true, dw: 1, eyes: "half" })],
    sleep: [f({ curl: true, eyes: "sleep" }), f({ curl: true, eyes: "sleep", dh: 1 })],
    eat: [f({ mouth: "open", sit: true }), f({ mouth: "open", sit: true, dh: -2, look: 1 }), f({ sit: true, dh: -1, dw: 1, eyes: "happy" }), f({ sit: true, dw: 1, eyes: "happy", mouth: "o" })],
    make: [f({ sit: true, paws: 1, look: 1 }), f({ sit: true, paws: 2, look: 1, dh: -1 }), f({ sit: true, paws: 1, look: 1 }), f({ sit: true, paws: 2, look: 1, dh: -1, lean: sway })],
    happy: [f({ dh: -1, dw: 1, eyes: "happy", mouth: "smile" }), f({ dy: 2, dh: 1, eyes: "happy", mouth: "open", arms: 2 }), f({ dy: 4, eyes: "happy", mouth: "open", arms: 3 }), f({ dy: 2, eyes: "happy", mouth: "smile", arms: 2 })],
    sad: [f({ dh: -1, look: 1, eyes: "sad", mouth: "frown", arms: -1 }), f({ dh: -2, look: 1, eyes: "sad", mouth: "frown", arms: -1, tear: 1 }),
      f({ dh: -2, look: 1, eyes: "sad", mouth: "frown", arms: -1, tear: 2 }), f({ dh: -1, look: 1, eyes: "sad", mouth: "frown", arms: -1 })],
    startled: [f({ dy: 3, dh: 2, eyes: "wide", mouth: "o", arms: 3 }), f({ dy: 1, dh: 1, eyes: "wide", mouth: "o", arms: 3 }), f({ dx: -1, eyes: "wide", mouth: "o", arms: 2 }), f({ dx: 1, eyes: "wide", mouth: "o", arms: 2 })],
  };
  const k = st.slow, fps: Record<PetAnim, number> = { idle: 4 * k, "walk.down": 8 * k, "walk.up": 8 * k, "walk.left": 8 * k, "walk.right": 8 * k, sit: 1.5 * k, sleep: 1, eat: 5 * k, make: 8 * k, happy: 8 * k, sad: 2 * k, startled: 8 };
  const eggPal = palette(g, 0, true);
  return { size: S, frames, fps, egg: [toCanvas(drawEgg(g, 0), eggPal), toCanvas(drawEgg(g, 1), eggPal)],
    dead: toCanvas(lying(drawPet(g, stage, { eyes: "x", mouth: "none" }), g.stretch * (1 - st.soft) + st.soft < 1), palette(g, Math.max(grey, 0.7))) };
}
