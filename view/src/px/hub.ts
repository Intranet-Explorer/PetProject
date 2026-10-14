// SPEC-v3.5.1, the hub's own things as the view draws them: the lit sign (a dot-matrix ticker, all in code), what is
// on each screen's glass (typed, then scrolling, green or amber), the founder's statue (its own body from its genome,
// through petsprite.ts, in a stone ramp, going up while it is built), and the radio set. still.ts asks `hubSprite` what
// to draw a hub thing as; the room calls `Hub.build` after each rebuild and `Hub.step` every frame.
import { Sprite } from "pixi.js";
import { petSheet } from "../petsprite";
import { hhmm } from "../types";
import type { Obj, RoomV, Snap } from "../types";
import { addSprite, canvasOf, def, fromCanvas, has, size } from "./assets";
import type { Layout } from "./assets";
import { textCanvas } from "./font";
import type { Fx } from "./fx";
import { clamp, corner, seeded } from "./geom";
import type { Still, Thing } from "./still";

/** What a hub thing is drawn as (null: as it always is). The terminals and the radio set are pictures of ours
 *  (own/src/hub.py); the sign's case and the statue are drawn here. */
export function hubSprite(o: Obj, type: string | null, L: Layout | null): string | null {
  if (o.statue) return statueSprite(o, L);
  if (o.fix?.sign) return caseSprite();
  if (o.fix?.terminal && has("fix.terminal")) return "fix.terminal";
  if (o.fix?.radio && type === "hub" && has("fix.radio set")) return "fix.radio set";
  return null;
}

// ---- the lit sign ----

/** Its case: the size of the layout's stand-in `fix.lit sign` if the art has one (about four tiles), a dark frame
 *  round a black face. The lights are laid over it at the screen's own pixels (`Ticker`). */
function caseSprite() {
  if (has("hub.sign")) return "hub.sign";
  const stand = def("fix.lit sign"), w = stand ? Math.max(40, stand.rect[2]) : 64, h = stand ? Math.max(13, stand.rect[3]) : 17;
  const c = Object.assign(document.createElement("canvas"), { width: w, height: h }), x = c.getContext("2d")!;
  x.fillStyle = "#141b1b"; x.fillRect(0, 0, w, h);
  x.fillStyle = "#4e484a"; x.fillRect(1, 1, w - 2, h - 2);
  x.fillStyle = "#695953"; x.fillRect(1, 1, w - 2, 1);
  x.fillStyle = "#0b0806"; x.fillRect(2, 2, w - 4, h - 4);
  addSprite("hub.sign", c);
  def("hub.sign")!.anchor = stand?.anchor ?? [0, 27];   // hung on the north wall, its top a few pixels under the ceiling
  return "hub.sign";
}

type Buf = Float32Array;
type Item = { anim?: string; text?: string; ms: number };
const LIT: [number, number, number] = [255, 168, 48], OFF = "#2b1709", GAP = "#0b0806";
const lerp = (a: number, b: number, k: number) => a + (b - a) * clamp(k, 0, 1);

/** The lines the sign runs, in plain words, in the order it runs them: the time, the forecast, the news (newest first). */
export function tickerLines(s: Snap): string[] {
  const t = s.ticker;
  return [`Day ${s.clock.day}, ${hhmm(s.clock.hour)}`, ...(t ? [t.forecast.text, ...[...t.headlines].reverse().map((h) => h.text)] : [])];
}

/** A pinball machine's dot display, between the messages: each draws one moment `k` (0 to 1) of itself. */
const ANIMS: Record<string, (b: Pen, k: number) => void> = {
  sun: (b, k) => {
    const cx = b.w / 2, cy = lerp(b.h + 6, b.h / 2, k / 0.35), r = 3.2, turn = k * 3;
    b.disc(cx, cy, r, 1);
    for (let i = 0; i < 8; i++) { const a = turn + (i * Math.PI) / 4; for (let d = r + 2; d < r + 5; d++) b.dot(cx + Math.cos(a) * d, cy + Math.sin(a) * d, 0.7); }
  },
  moon: (b, k) => {
    const cx = lerp(-6, b.w / 2, k / 0.35), cy = b.h / 2;
    b.disc(cx, cy, 5, 1);
    b.disc(cx + 2.5, cy - 1.5, 4.2, 0, true);
    const r = seeded("stars");
    for (let i = 0; i < 14; i++) { const x = r() * b.w, y = r() * b.h, ph = r() * 6; b.dot(x, y, Math.max(0, Math.sin(k * 14 + ph)) * 0.8); }
  },
  cloud: (b, k) => cloud(b, lerp(b.w + 10, -14, k), b.h / 2 + 1, 0.8),
  rain: (b, k) => {
    const r = seeded("rain");
    for (let i = 0; i < 16; i++) { const x = r() * b.w, y = ((k * 3 + r()) % 1) * (b.h + 4) - 2; b.dot(x, y, 0.6); b.dot(x, y - 1, 0.35); }
    cloud(b, b.w / 2, 3, 1);
  },
  snow: (b, k) => {
    const r = seeded("snow");
    for (let i = 0; i < 22; i++) { const x0 = r() * b.w, y = ((k * 1.2 + r()) % 1) * (b.h + 2) - 1; b.dot(x0 + Math.sin(k * 9 + i) * 1.5, y, r() < 0.5 ? 1 : 0.6); }
  },
  fire: (b, k) => {   // flames up from the foot of the sign, a few sparks
    const t = k * 40, r = seeded(`fire${Math.floor(k * 30)}`);
    for (let x = 0; x < b.w; x++) {
      const h = ((Math.sin(x * 0.8 + t) + Math.sin(x * 0.31 - t * 0.7) + 2.4) / 4.4) * b.h * 0.85 + r() * 2;
      for (let y = 0; y < h; y++) b.dot(x, b.h - 1 - y, 1 - (y / h) * 0.75);
    }
    for (let i = 0; i < 5; i++) b.dot(r() * b.w, r() * b.h * 0.4, 0.8);
  },
  star: (b, k) => {   // a burst: a star in the middle, rays thrown outward, sparkles after
    const cx = b.w / 2, cy = b.h / 2;
    for (let i = 0; i < 12; i++) { const a = (i * Math.PI) / 6, d0 = k * 24; for (let d = d0; d < d0 + 3; d++) b.dot(cx + Math.cos(a) * d * 1.4, cy + Math.sin(a) * d * 0.7, 1 - k * 0.5); }
    if (k < 0.5) for (let d = -3; d <= 3; d++) { b.dot(cx + d, cy, 1); b.dot(cx, cy + d * 0.7, 1); }
    const r = seeded(`spark${Math.floor(k * 12)}`);
    if (k > 0.3) for (let i = 0; i < 10; i++) b.dot(r() * b.w, r() * b.h, r());
  },
  wipe: (b, k) => { const x = k * (b.w + 8) - 4; for (let y = 0; y < b.h; y++) for (let d = 0; d < 4; d++) b.dot(x - d, y, 1 - d / 4); },
};
function cloud(b: Pen, x: number, y: number, v: number) {
  for (const [dx, dy, r] of [[-4, 1, 3], [0, -1, 4], [4, 1, 3]]) b.disc(x + dx, y + dy, r, v);
}

/** The lights, one number each (0 dark to 1 full). */
class Pen {
  b: Buf;
  constructor(readonly w: number, readonly h: number) { this.b = new Float32Array(w * h); }
  dot(x: number, y: number, v: number) {
    const [i, j] = [Math.round(x), Math.round(y)];
    if (i >= 0 && j >= 0 && i < this.w && j < this.h) this.b[j * this.w + i] = Math.max(this.b[j * this.w + i], v);
  }
  disc(cx: number, cy: number, r: number, v: number, cut = false) {
    for (let y = Math.floor(cy - r); y <= cy + r; y++) for (let x = Math.floor(cx - r); x <= cx + r; x++) {
      if ((x - cx) ** 2 + (y - cy) ** 2 > r * r || x < 0 || y < 0 || x >= this.w || y >= this.h) continue;
      if (cut) this.b[y * this.w + x] = 0; else this.dot(x, y, v);
    }
  }
}

/** A message's lit pixels, from the room's 5 x 7 lettering (cached). */
const bitmaps = new Map<string, { w: number; on: Uint8Array }>();
function bitmap(text: string) {
  let m = bitmaps.get(text);
  if (!m) {
    const c = textCanvas([text], { color: "#fff" }), p = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data, on = new Uint8Array(c.width * 9);
    for (let y = 0; y < Math.min(9, c.height); y++) for (let x = 0; x < c.width; x++) on[y * c.width + x] = p[(y * c.width + x) * 4 + 3] > 127 ? 1 : 0;
    bitmaps.set(text, (m = { w: c.width, on }));
    if (bitmaps.size > 60) bitmaps.delete(bitmaps.keys().next().value!);
  }
  return m;
}

/** The sign's lights at the screen's own pixels (one light to a pixel of the art, a dark gap round each), cycling the
 *  time, the forecast and the headlines with an animation before each. */
class Ticker {
  s: Sprite;
  private c: HTMLCanvasElement;
  private pen: Pen;
  private items: Item[] = [];
  private i = -1;
  private at = 0;
  private last = "";
  constructor(readonly t: Thing, readonly K: number) {
    const w = Math.round(t.rect.w) - 4, h = Math.round(t.rect.h) - 4;
    this.pen = new Pen(w, h);
    this.c = Object.assign(document.createElement("canvas"), { width: w * K, height: h * K });
    this.s = new Sprite(fromCanvas(this.c));
    this.s.scale.set(1 / K);
    this.s.position.set(Math.round(t.rect.x) + 2, Math.round(t.rect.y) + 2);
  }
  /** One run through: rebuilt from the latest snapshot each time round, so the time and the news are current. */
  private plan(s: Snap) {
    const t = s.ticker, night = s.clock.phase === "night", lines = tickerLines(s);
    this.items = [{ anim: t?.cold && night ? "fire" : night ? "moon" : "sun", ms: 1800 }, { text: lines[0], ms: 0 }];
    if (t) {
      this.items.push({ anim: t.forecast.anim in ANIMS ? t.forecast.anim : "cloud", ms: 1800 }, { text: t.forecast.text, ms: 0 });
      for (const h of [...t.headlines].reverse()) this.items.push({ anim: h.anim && h.anim in ANIMS ? h.anim : "wipe", ms: h.anim ? 1600 : 500 }, { text: h.text, ms: 0 });
    }
    for (const it of this.items) if (it.text != null) { const w = bitmap(it.text).w; it.ms = w <= this.pen.w ? 3200 : ((this.pen.w + w) / 26) * 1000; }   // what fits stands still; the rest scrolls by
  }
  step(now: number, s: Snap) {
    if (this.i < 0 || now - this.at > this.items[this.i].ms) {
      this.i = this.i < 0 || this.i + 1 >= this.items.length ? 0 : this.i + 1;
      if (this.i === 0) this.plan(s);
      this.at = now;
    }
    const it = this.items[this.i], k = (now - this.at) / it.ms, p = this.pen;
    p.b.fill(0);
    if (it.anim) ANIMS[it.anim](p, k);
    else if (it.text != null) {
      const m = bitmap(it.text), x0 = m.w <= p.w ? Math.floor((p.w - m.w) / 2) : Math.round(p.w - k * (p.w + m.w)), y0 = Math.max(0, Math.floor((p.h - 7) / 2));
      for (let y = 0; y < 9; y++) for (let x = 0; x < m.w; x++) if (m.on[y * m.w + x]) p.dot(x0 + x, y0 + y, 1);
    }
    const key = Array.from(p.b, (v) => Math.ceil(v * 3)).join("");   // four steps of brightness, as such a display has
    if (key === this.last) return;
    this.last = key;
    const x = this.c.getContext("2d")!, K = this.K, d = Math.max(1, K - 1);
    x.fillStyle = GAP;
    x.fillRect(0, 0, this.c.width, this.c.height);
    for (let j = 0; j < p.h; j++) for (let i = 0; i < p.w; i++) {
      const v = Math.ceil(p.b[j * p.w + i] * 3) / 3;
      x.fillStyle = v ? `rgb(${LIT.map((c) => Math.round(c * (0.35 + 0.65 * v))).join(",")})` : OFF;
      x.fillRect(i * K, j * K, d, d);
    }
    this.s.texture.source.update();
  }
}

// ---- the screens ----

const INKS = [{ on: "#8dff9a", dim: "#2f7a3a", bg: "#0d1a10" }, { on: "#ffc94a", dim: "#8a5a14", bg: "#1a1206" }];   // green on one, amber on the next
/** When each screen's question was first seen here: its typing starts then (kept across rebuilds of the room). */
const since = new Map<string, number>();
export const screenKey = (o: Obj) => (o.screen ? `${o.screen.tick}|${o.screen.asked}` : "");
/** A screen's colour: green or amber, taking turns from left to right among the screens of its room. */
export function screenInk(room: { objects: Record<string, Obj> }, name: string) {
  const all = Object.entries(room.objects).filter(([, o]) => o.fix?.terminal).sort(([, a], [, b]) => a.pos[0] - b.pos[0] || a.pos[1] - b.pos[1]).map(([n]) => n);
  return INKS[Math.max(0, all.indexOf(name)) % 2];
}

/** A screen's glass at the art's pixels: too small to read, so each letter is a lit pixel and each word a dash. The
 *  question is typed after a prompt, then what it read scrolls up a line at a time; idle, a cursor blinks. */
class Glass {
  s: Sprite;
  private c: HTMLCanvasElement;
  private last = "";
  constructor(readonly t: Thing, readonly r: number[], readonly ink: (typeof INKS)[number]) {
    this.c = Object.assign(document.createElement("canvas"), { width: r[2], height: r[3] });
    this.s = new Sprite(fromCanvas(this.c));
    this.s.position.set(Math.round(t.rect.x) + r[0], Math.round(t.rect.y) + r[1]);
    this.s.zIndex = t.s.zIndex + 0.1;
  }
  step(now: number, o: Obj) {
    const [w, h] = [this.r[2], this.r[3]], sc = o.screen, key = screenKey(o), blink = Math.floor(now / 500) % 2 === 0;
    if (key && !since.has(key)) since.set(key, now);
    const ms = key ? now - since.get(key)! : 0, typed = sc ? Math.min(sc.asked.length, Math.floor(ms / 90)) : 0;
    const body = sc ? (sc.text ? `${sc.title ?? ""} ${sc.text}` : "nothing found") : "", rows = Math.ceil(h / 2);
    const lines: string[] = [`>${sc?.asked.slice(0, typed) ?? ""}`];   // the prompt line wraps like any other
    if (sc && typed >= sc.asked.length && ms > sc.asked.length * 90 + 600) {
      let line = "";
      for (const word of body.split(/\s+/)) { if (line && line.length + 1 + word.length > w) { lines.push(line); line = ""; } line += (line ? " " : "") + word.slice(0, w); }
      if (line) lines.push(line);
    }
    const flat = lines.flatMap((l) => l.match(new RegExp(`.{1,${w}}`, "g")) ?? [""]);
    const shown = sc ? Math.min(flat.length, 1 + Math.max(0, Math.floor((ms - sc.asked.length * 90 - 600) / 260))) : 1;   // a new line every quarter second
    const view = flat.slice(Math.max(0, shown - rows), shown), cur = view.at(-1)?.length ?? 0, done = !sc || shown >= flat.length;
    const k = `${view.join("|")}|${done && blink}`;
    if (k === this.last) return;
    this.last = k;
    const x = this.c.getContext("2d")!;
    x.fillStyle = this.ink.bg;
    x.fillRect(0, 0, w, h);
    view.forEach((l, j) => [...l].forEach((ch, i) => { if (ch !== " ") { x.fillStyle = i === 0 && l.startsWith(">") ? this.ink.dim : this.ink.on; x.fillRect(i, j * 2, 1, 1); } }));
    if (done && blink) { x.fillStyle = this.ink.on; x.fillRect(Math.min(w - 1, cur), (view.length - 1) * 2, 1, 1); }
    this.s.texture.source.update();
  }
}

// ---- the statue ----

const STONE = ["#2a282e", "#4d4b52", "#6f6d72", "#938f8b", "#b9b4ab", "#dcd7cc"];   // its line, then dark to light
const WOOD = ["#141b1b", "#965340", "#c8966b"];
const ink = (x: CanvasRenderingContext2D, color: string, X: number, Y: number, w = 1, h = 1) => { x.fillStyle = color; x.fillRect(X, Y, w, h); };

/** The founder in stone on its plinth: its own body (the elder it was) at twice a pet's pixels, lightness kept and turned
 *  to grey. While it is built (`build.progress` under 1) it goes up as a rough block, then is carved from the foot up,
 *  in a scaffold. It stands on the layout's plinth on its tile, if there is one, or on a plinth of its own. */
function statueSprite(o: Obj, L: Layout | null): string {
  const st = o.statue!, p = o.fix?.built || o.build?.progress == null ? 1 : clamp(o.build.progress, 0, 1), q = Math.floor(p * 16) / 16;
  const plinth = L?.decor?.find((d) => d.at[0] === o.pos[0] && d.at[1] === o.pos[1])?.sprite ?? null;
  const name = `statue.${st.of}.${q}.${plinth}`;
  if (has(name)) return name;
  // the body, in stone
  const src = st.genome ? petSheet(st.genome, "elder").frames.idle[0] : null, S = src?.width ?? 24, Z = 2, PAD = 6, own = plinth ? 0 : 7;
  const W = S * Z + 2 * PAD, H = S * Z + own, c = Object.assign(document.createElement("canvas"), { width: W, height: H }), x = c.getContext("2d")!;
  const px = src ? src.getContext("2d")!.getImageData(0, 0, S, S).data : new Uint8ClampedArray(S * S * 4), lum = (i: number) => px[i] * 0.3 + px[i + 1] * 0.59 + px[i + 2] * 0.11;
  let [lo, hi, bx0, by0, bx1, by1] = [255, 0, S, S, -1, -1];
  for (let y = 0; y < S; y++) for (let i = 0; i < S; i++) {
    const k = (y * S + i) * 4;
    if (px[k + 3] < 128) continue;
    [bx0, by0, bx1, by1] = [Math.min(bx0, i), Math.min(by0, y), Math.max(bx1, i), Math.max(by1, y)];
    if (lum(k) > 45) [lo, hi] = [Math.min(lo, lum(k)), Math.max(hi, lum(k))];
  }
  if (bx1 < 0) [bx0, by0, bx1, by1] = [6, 4, 17, 23];   // no genome: a plain block of the size of a body
  const top = by0 * Z, foot = (by1 + 1) * Z, left = PAD + bx0 * Z - 1, right = PAD + (bx1 + 1) * Z + 1;
  const block = foot - (foot - top) * clamp(src ? p / 0.3 : 1, 0, 1), carved = src ? foot - (foot - top) * clamp((p - 0.3) / 0.7, 0, 1) : top, r = seeded(name);
  for (let y = 0; y < S; y++) for (let i = 0; i < S; i++) {   // carved: the body, from the foot up as far as the carving has come
    const k = (y * S + i) * 4;
    if (px[k + 3] < 128 || (y + 1) * Z <= carved) continue;
    const v = lum(k), tone = v <= 45 ? 0 : 1 + Math.round(((v - lo) / Math.max(1, hi - lo)) * 4);
    for (let dy = 0; dy < Z; dy++) for (let dx = 0; dx < Z; dx++) {
      const t = tone && r() < 0.12 ? clamp(tone + (r() < 0.5 ? -1 : 1), 1, 5) : tone;   // a little grain, as stone has
      if ((y * Z + dy) >= carved) ink(x, STONE[t], PAD + i * Z + dx, y * Z + dy);
    }
  }
  for (let X = left; X < right; X++) {   // what is still rough block above the carving, with a ragged top
    const from = Math.round(block + (X === left || X === right - 1 ? 1 : r() < 0.3 ? 1 : 0));
    for (let Y = from; Y < (src ? carved : foot); Y++) ink(x, X === left || X === right - 1 || Y === from ? STONE[0] : STONE[2 + Math.floor(r() * 2.2)], X, Y);
  }
  if (p < 1) {   // and the scaffold round it
    const poleTop = Math.max(0, Math.round(block) - 6);
    for (const X of [left - 3, right + 1]) { ink(x, WOOD[0], X - 1, poleTop, 4, foot - poleTop); ink(x, WOOD[1], X, poleTop, 2, foot - poleTop); ink(x, WOOD[2], X, poleTop, 1, foot - poleTop); }
    for (const Y of [Math.round(block) - 2, Math.round((block + foot) / 2)]) if (Y > 0 && Y < foot - 2) { ink(x, WOOD[0], left - 4, Y - 1, right - left + 8, 4); ink(x, WOOD[1], left - 3, Y, right - left + 6, 2); ink(x, WOOD[2], left - 3, Y, right - left + 6, 1); }
  }
  if (own) {   // no plinth in the layout: a plain one of its own
    const pl = Math.max(PAD, left - 3), pr = Math.min(W - PAD, right + 3);
    ink(x, STONE[0], pl, foot, pr - pl, own);
    ink(x, STONE[3], pl + 1, foot + 1, pr - pl - 2, 2);
    ink(x, STONE[2], pl + 1, foot + 3, pr - pl - 2, own - 4);
  }
  addSprite(name, c);
  // where it stands: its feet in the middle of the top of the plinth on its tile (or its own plinth on the floor)
  const [cx, cy] = corner(o.pos);
  let [mid, feet] = [cx + 8, cy + 14 - own];
  if (plinth && has(plinth)) {
    const sz = size(plinth), pc = canvasOf(plinth), d = pc.getContext("2d")!.getImageData(0, 0, pc.width, pc.height).data;
    let row = 0;
    while (row < pc.height - 1 && ![...Array(pc.width).keys()].some((i) => d[(row * pc.width + i) * 4 + 3] > 127)) row++;
    [mid, feet] = [cx - sz.ax + sz.w / 2, cy - sz.ay + row + 3];
  }
  def(name)!.anchor = [Math.round(W / 2 - (mid - cx)), Math.round(cy + foot - feet)];
  return name;
}

// ---- the room's part ----

/** What the hub's things do between snapshots. One per room view; built again with the room's still parts. */
export class Hub {
  private signs: Ticker[] = [];
  private glass: Glass[] = [];
  private sites: Thing[] = [];
  private radio: Thing | null = null;
  private next = 0;

  /** After the room's still parts are made: lights over the sign, writing on each screen's glass. What is added goes
   *  into `still` so it is cleared with it. */
  build(still: Still, K: number) {
    [this.signs, this.glass, this.sites, this.radio] = [[], [], [], null];
    const things = [...still.things.values()], objects = Object.fromEntries(things.map((t) => [t.name, t.obj]));
    for (const t of things) {
      if (t.obj.fix?.sign) {
        const s = new Ticker(t, K);
        (t.s.parent ?? still.wallLayer).addChild(s.s);
        this.signs.push(s);
        still.lamps.push({ x: t.x, y: t.rect.y + t.rect.h / 2, r: Math.max(30, t.rect.w * 0.6), color: [255, 170, 80], made: true });
      } else if (t.obj.fix?.terminal) {
        const g = def(t.sprite)?.glass ?? [3, 3, Math.max(2, t.rect.w - 6), Math.max(2, Math.round(t.rect.h / 3))], ink = screenInk({ objects }, t.name), s = new Glass(t, g, ink);
        still.standing.push(s.s);
        this.glass.push(s);
        still.lamps.push({ x: t.rect.x + g[0] + g[2] / 2, y: t.rect.y + g[1] + g[3] / 2, r: 12, color: ink === INKS[0] ? [140, 255, 150] : [255, 200, 90], made: true });
      } else if (t.obj.statue && (t.obj.build?.progress ?? 1) < 1 && !t.obj.fix?.built) this.sites.push(t);
      else if (t.obj.fix?.radio) this.radio = t;
    }
  }

  step(now: number, snap: Snap, room: RoomV, fx: Fx) {
    for (const s of this.signs) s.step(now, snap);
    for (const g of this.glass) g.step(now, room.objects[g.t.name] ?? g.t.obj);   // (what is on a screen changes without the room being built again)
    if (now < this.next) return;
    this.next = now + 700;
    for (const t of this.sites) if (Math.random() < 0.6) fx.spawn("dust", t.rect.x + 6 + Math.random() * (t.rect.w - 12), t.y - 2 - Math.random() * t.rect.h * 0.5, { vy: 4, life: 600 });   // chips and dust while it is carved
    const r = this.radio;
    if (r && r.obj.state === "on" && snap.dj?.radio.on) fx.spawn("note", r.x + (Math.random() - 0.5) * 8, r.rect.y, { vx: (Math.random() - 0.5) * 6, vy: -14, life: 1600, sway: 2 });   // the station plays
  }
}
