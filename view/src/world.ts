// SPEC-v3.5.9 §3: the world outside the house, behind the whole page: a sky that follows the house's own clock (dawn,
// blue day, golden evening, deep night with stars and the moon), three layers of distant hills and trees in the
// season's colours that drift a little as the page scrolls, and the weather in that sky: clouds, rain in thin streaks,
// snow, low fog in the morning, lightning (with the house's thunder) in a storm. Pixel art drawn here in code, at a
// whole number of screen pixels to each of its pixels, kept dim so the panels stay readable. Reduce motion: all of it
// stays, slower and sparser, and lightning is a soft brighten.
// The sky and each hill layer are drawn once into a canvas of their own and only drawn again when the hour, season,
// weather or size changes; every frame lays them down and draws what moves over them.
import { seeded } from "./px/geom";
import { flashAt, flashOn, REDUCE, softFlash } from "./px/weather";
import type { Snap } from "./types";

type RGB = number[];
const mix = (a: RGB, b: RGB, k: number): RGB => a.map((v, i) => v + (b[i] - v) * Math.max(0, Math.min(1, k)));
const css = (c: RGB, a = 1) => `rgba(${c.map((v) => Math.round(Math.max(0, Math.min(255, v)))).join(",")},${a})`;
const smooth = (a: number, b: number, v: number) => { const k = Math.max(0, Math.min(1, (v - a) / (b - a))); return k * k * (3 - 2 * k); };

/** The sky by the hour: its colour at the top and at the horizon. */
const SKY: [number, RGB, RGB][] = [
  [0, [9, 12, 36], [22, 28, 64]], [4.6, [11, 14, 40], [30, 30, 72]], [6, [48, 54, 112], [214, 132, 104]], [7.4, [74, 118, 184], [196, 204, 214]],
  [10, [58, 110, 184], [150, 190, 226]], [16, [62, 112, 184], [162, 196, 224]], [18.4, [84, 90, 150], [232, 168, 92]], [19.9, [42, 40, 90], [190, 100, 82]],
  [21.4, [13, 17, 46], [32, 34, 76]], [24, [9, 12, 36], [22, 28, 64]],
];
/** What the weather does to the sky: the grey it turns toward, and how far. */
const OVERCAST: Record<string, [RGB, number]> = { cloudy: [[128, 136, 150], 0.4], rain: [[96, 104, 122], 0.6], storm: [[58, 62, 82], 0.75], snow: [[176, 184, 198], 0.5], heat: [[236, 214, 160], 0.15] };
/** The hills by season, far to near, and their trees'. */
const HILLS: Record<string, { hill: RGB[]; tree: RGB[]; snow?: boolean }> = {
  spring: { hill: [[104, 150, 104], [76, 128, 72], [56, 104, 54]], tree: [[54, 108, 60], [232, 160, 186]] },
  summer: { hill: [[176, 160, 88], [150, 138, 64], [116, 114, 50]], tree: [[60, 96, 44], [196, 168, 70]] },
  autumn: { hill: [[170, 120, 82], [178, 104, 52], [140, 80, 42]], tree: [[200, 98, 38], [222, 150, 52]] },
  winter: { hill: [[206, 214, 228], [186, 196, 214], [160, 172, 194]], tree: [[46, 70, 62], [104, 84, 70]], snow: true },
};
const NIGHT: RGB = [14, 18, 44];

let cv: HTMLCanvasElement | null = null;
let ctx: CanvasRenderingContext2D;
let w = 0, h = 0, P = 4;             // the canvas in its own pixels; device pixels to one of them
let sky: HTMLCanvasElement, hills: HTMLCanvasElement[] = [], clouds: HTMLCanvasElement[] = [];
let drawnFor = "";
let state = { hour: 12, season: "spring", weather: "clear" };
let scroll = 0;
let last = 0;
let struck = 0;                      // the last lightning drawn (flashAt), so thunder is asked for once
let stars: number[] = [];

const canvas = (cw: number, ch: number) => Object.assign(document.createElement("canvas"), { width: cw, height: ch });

/** Called with every snapshot (main.ts): the world follows the house's clock, season and weather. */
export function world(s: Snap) {
  state = { hour: s.clock.hour, season: s.clock.season, weather: s.weather };
  if (cv) return;
  cv = canvas(1, 1);
  cv.id = "world";
  cv.setAttribute("aria-hidden", "true");
  Object.assign(cv.style, { position: "fixed", left: "0", top: "0", zIndex: "-1", pointerEvents: "none", imageRendering: "pixelated" });
  document.body.prepend(cv);
  ctx = cv.getContext("2d")!;
  addEventListener("resize", fit);
  addEventListener("scroll", (e) => { const t = e.target; scroll = t instanceof Element ? t.scrollTop : scrollY; }, { capture: true, passive: true });
  fit();
  requestAnimationFrame(frame);
}

/** The largest whole number of device pixels to a pixel of the world that leaves it about 360 of them wide. */
function fit() {
  const dpr = devicePixelRatio || 1;
  P = Math.max(2, Math.round((innerWidth * dpr) / 360));
  [w, h] = [Math.ceil((innerWidth * dpr) / P), Math.ceil((innerHeight * dpr) / P)];
  [cv!.width, cv!.height] = [w, h];
  cv!.style.width = `${(w * P) / dpr}px`;
  cv!.style.height = `${(h * P) / dpr}px`;
  stars = [];
  const r = seeded("stars");
  for (let i = 0; i < (w * h) / 260; i++) stars.push(Math.floor(r() * w), Math.floor(r() * h * 0.62), r() * 6.3, r() < 0.12 ? 2 : 1);
  drawnFor = "";
}

/** How light the sky is, 0 (deep night) to 1 (full day), and how golden (0 to 1, round sunrise and sunset). */
const daylight = (hr: number) => smooth(4.8, 7.2, hr) * (1 - smooth(18.8, 21.2, hr));
const golden = (hr: number) => Math.max(1 - Math.abs(hr - 6.4) / 1.4, 1 - Math.abs(hr - 19) / 1.6, 0);

function skyAt(hr: number): [RGB, RGB] {
  const i = SKY.findIndex((k) => k[0] > hr), [a, b] = [SKY[Math.max(0, i - 1)], SKY[Math.max(0, i)]], k = (hr - a[0]) / Math.max(0.01, b[0] - a[0]);
  let [top, low] = [mix(a[1], b[1], k), mix(a[2], b[2], k)];
  const o = OVERCAST[state.weather];
  if (o) { const d = o[1] * (0.35 + 0.65 * daylight(hr)); [top, low] = [mix(top, mix(o[0], NIGHT, 1 - daylight(hr)), d), mix(low, mix(o[0], NIGHT, 1 - daylight(hr)), d)]; }
  return [top, low];
}

/** The still layers: the sky in dithered bands, and each layer of hills with its trees. */
function build() {
  const hr = state.hour, [top, low] = skyAt(hr), dark = 1 - daylight(hr), horizon = Math.round(h * 0.72);
  sky = canvas(w, h);
  const sx = sky.getContext("2d")!, img = sx.createImageData(w, h), d = img.data, BAYER = [0, 0.5, 0.75, 0.25];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const t = Math.min(1, y / horizon), band = Math.min(1, Math.floor(t * 10 + BAYER[(x & 1) + 2 * (y & 1)]) / 10), c = mix(top, low, band * band * 0.6 + band * 0.4), i = (y * w + x) * 4;
    [d[i], d[i + 1], d[i + 2], d[i + 3]] = [c[0], c[1], c[2], 255];
  }
  sx.putImageData(img, 0, 0);
  const sun = daylight(hr) > 0.05 && state.weather !== "rain" && state.weather !== "storm" && state.weather !== "snow";
  if (sun) {   // the sun on its arc, through cloud a pale disc
    const k = (hr - 5.5) / 15, x = Math.round(w * (0.08 + 0.84 * k)), y = Math.round(horizon - Math.sin(Math.PI * Math.max(0, Math.min(1, k))) * horizon * 0.8 + 4);
    const g = golden(hr), pale = state.weather === "cloudy" ? 0.5 : 1;
    disc(sx, x, y, 7, css(mix([255, 240, 190], [255, 170, 90], g), 0.18 * pale));
    disc(sx, x, y, 5, css(mix([255, 244, 200], [255, 186, 110], g), 0.85 * pale));
    disc(sx, x, y, 3, css([255, 252, 236], 0.9 * pale));
  }
  const tone = (c: RGB, far: number) => mix(mix(mix(c, low, far), [255, 168, 96], golden(hr) * 0.18), NIGHT, dark * 0.72);
  const look = HILLS[state.season] ?? HILLS.spring;
  hills = [0, 1, 2].map((L) => {
    const lay = canvas(w, h + 48), x = lay.getContext("2d")!, r = seeded(`hills${L}`), far = [0.55, 0.3, 0.08][L];
    const base = h * [0.6, 0.7, 0.82][L], amp = h * [0.07, 0.06, 0.05][L], ph = [r() * 6, r() * 6, r() * 6], fq = [0.011, 0.027, 0.06].map((f) => f * (1 + L * 0.4));
    const hill = tone(look.hill[L], far), lit = mix(hill, look.snow ? [250, 252, 255] : [255, 250, 220], 0.25 * (1 - dark)), tops: number[] = [];
    for (let i = 0; i < w; i++) {
      const y = Math.round(base - amp * (Math.sin(i * fq[0] + ph[0]) + 0.5 * Math.sin(i * fq[1] + ph[1]) + 0.25 * Math.sin(i * fq[2] + ph[2])));
      tops.push(y);
      x.fillStyle = css(hill); x.fillRect(i, y, 1, lay.height - y);
      x.fillStyle = css(lit); x.fillRect(i, y, 1, 1);
    }
    if (L > 0) {   // trees along the ridge, bigger nearer
      const leaf = tone(look.tree[0], far), other = tone(look.tree[1], far), trunk = tone([70, 52, 44], far), snow = tone([244, 248, 255], far);
      for (let i = Math.floor(r() * 8); i < w; i += (L === 1 ? 5 : 9) + Math.floor(r() * (L === 1 ? 12 : 22))) tree(x, i, tops[i] + 1 + Math.floor(r() * 3), L === 1 ? 1 : 2, r() < 0.5, { leaf, other, trunk, snow }, r);
    }
    return lay;
  });
  clouds = [];   // the clouds' colour follows the hour and the weather too
  const heavy = state.weather === "rain" || state.weather === "storm", cr = seeded("clouds");
  const body = mix(mix(heavy ? [120, 126, 142] : [236, 238, 244], [244, 168, 140], golden(hr) * 0.6), [44, 50, 84], dark * 0.82), shade = mix(body, [40, 44, 66], 0.25), rim = mix(body, [255, 255, 255], 0.25 * (1 - dark));
  for (let i = 0; i < 6; i++) {
    const cw = 26 + Math.floor(cr() * 34), c = canvas(cw, 18), x = c.getContext("2d")!, lumps = 4 + Math.floor(cw / 12);
    for (let j = 0; j < lumps; j++) { const k = (j + 0.5) / lumps; disc(x, 4 + k * (cw - 8), 13, 2 + Math.sin(k * Math.PI) * (3 + cw / 12) * (0.7 + cr() * 0.5), css(body)); }
    x.clearRect(0, 15, cw, 3);   // a flat underside
    const all = x.getImageData(0, 0, cw, 18).data;
    for (let px = 0; px < cw; px++) {   // a lit top and a shaded bottom, a pixel each
      let top = -1, bottom = -1;
      for (let y = 0; y < 18; y++) if (all[(y * cw + px) * 4 + 3] > 0) { if (top < 0) top = y; bottom = y; }
      if (top >= 0) { x.fillStyle = css(rim); x.fillRect(px, top, 1, 1); x.fillStyle = css(shade); x.fillRect(px, bottom, 1, 1); }
    }
    clouds.push(c);
  }
}

/** A filled circle in whole pixels. */
function disc(x: CanvasRenderingContext2D, cx: number, cy: number, r: number, fill: string) {
  x.fillStyle = fill;
  for (let dy = -Math.floor(r); dy <= r; dy++) { const s = Math.round(Math.sqrt(Math.max(0, r * r - dy * dy))); x.fillRect(Math.round(cx) - s, Math.round(cy) + dy, 2 * s + 1, 1); }
}

/** A tree in the season's look: a pine (snow on it in winter), or a round tree (blossom in spring, gold in autumn, bare in winter). */
function tree(x: CanvasRenderingContext2D, cx: number, foot: number, k: number, pine: boolean, c: Record<string, RGB>, r: () => number) {
  const winter = state.season === "winter";
  x.fillStyle = css(c.trunk);
  x.fillRect(cx, foot - 2 * k, k, 2 * k);
  if (pine) {
    const tall = (5 + Math.floor(r() * 4)) * k;
    for (let y = 0; y < tall; y++) {
      const half = Math.floor((y * 0.5 + 1) * (k === 1 ? 0.7 : 0.6)) + (y % 3 === 2 ? 0 : 0);
      x.fillStyle = css(c.leaf);
      x.fillRect(cx - half, foot - 2 * k - tall + y, 2 * half + k, 1);
      if (winter && y % 3 === 0) { x.fillStyle = css(c.snow); x.fillRect(cx - half, foot - 2 * k - tall + y, half + 1, 1); }
    }
    return;
  }
  const rad = (2 + r() * 1.5) * k, cy = foot - 2 * k - rad;
  if (winter) {   // bare branches
    x.fillStyle = css(c.trunk);
    x.fillRect(cx, cy - rad, k, rad + 2 * k);
    for (const [dx, dy] of [[-1, 0], [1, -1], [-2, -2], [2, -2]]) x.fillRect(cx + dx * k, cy + dy * k, k, k);
    return;
  }
  disc(x, cx, cy, rad, css(state.season === "autumn" && r() < 0.5 ? c.other : c.leaf));
  if (state.season !== "summer") for (let i = 0; i < 3 * k; i++) { x.fillStyle = css(c.other); x.fillRect(Math.round(cx + (r() - 0.5) * 2 * rad), Math.round(cy + (r() - 0.5) * 2 * rad), 1, 1); }
}

function frame(now: number) {
  requestAnimationFrame(frame);
  const dt = Math.min(100, now - (last || now)) / 1000, slow = REDUCE.matches ? 0.35 : 1;
  last = now;
  const key = `${Math.round(state.hour * 20)}|${state.season}|${state.weather}|${w}x${h}`;
  if (key !== drawnFor) { drawnFor = key; build(); }
  const x = ctx, hr = state.hour, dark = 1 - daylight(hr), t = (now / 1000) * slow, wx = state.weather;
  x.drawImage(sky, 0, 0);
  if (dark > 0.3 && (wx === "clear" || wx === "heat" || wx === "cloudy")) {   // stars, twinkling, and the moon
    const a = (dark - 0.3) / 0.7 * (wx === "cloudy" ? 0.4 : 1);
    for (let i = 0; i < stars.length; i += 4) { x.fillStyle = css([236, 236, 255], a * (0.55 + 0.45 * Math.sin(t * 1.3 + stars[i + 2]))); x.fillRect(stars[i], stars[i + 1], stars[i + 3], stars[i + 3] > 1 ? 1 : 1); }
    const k = ((hr + 24 - 19.5) % 24) / 11, mx = Math.round(w * (0.1 + 0.8 * k)), my = Math.round(h * 0.6 - Math.sin(Math.PI * Math.max(0, Math.min(1, k))) * h * 0.45);
    disc(x, mx, my, 6, css([200, 210, 255], 0.12 * a));
    disc(x, mx, my, 4, css([236, 234, 214], a));
    disc(x, mx + 2, my - 1, 3, css(mix(skyAt(hr)[0], skyAt(hr)[1], 0.3), a));
  }
  const many = ({ clear: 3, heat: 1, cloudy: 9, rain: 11, storm: 13, snow: 9 } as Record<string, number>)[wx] ?? 4, wind = wx === "storm" ? 3 : 1;
  for (let i = 0; i < many; i++) {   // clouds drift; each comes back round the other side
    const c = clouds[i % clouds.length], r = seeded(`cloud${i}`), speed = (1.5 + r() * 3) * wind, span = w + c.width;
    x.drawImage(c, Math.round(((r() * span + t * speed) % span) - c.width), Math.round(h * (0.04 + r() * (wx === "clear" ? 0.25 : 0.4))));
  }
  const px = (devicePixelRatio || 1) / P;   // a CSS pixel of scroll in the world's pixels
  hills.forEach((lay, L) => x.drawImage(lay, 0, -Math.round(Math.min(48, scroll * px * [0.04, 0.08, 0.14][L]))));
  fog(x, hr, t);
  fall(x, t, slow);
  if (wx === "storm") {
    const at = flashAt(now);
    if (REDUCE.matches) { const k = softFlash(now, at); if (k > 0) { x.fillStyle = css([210, 220, 255], k * 0.16); x.fillRect(0, 0, w, h); } }
    else if (flashOn(now, at)) {   // the whole sky lit for a moment, and the bolt
      x.fillStyle = css([226, 232, 255], 0.5);
      x.fillRect(0, 0, w, h);
      const r = seeded(`bolt${at}`);
      let bx = Math.round(w * (0.1 + r() * 0.8)), by = Math.round(h * 0.12);
      x.fillStyle = "#ffffff";
      while (by < h * 0.66) { x.fillRect(bx, by, 1, 3); by += 3; bx += Math.round((r() - 0.5) * 4); }
    }
    if (at !== struck && now > at) { struck = at; dispatchEvent(new CustomEvent("pet:thunder")); }   // voice.ts: the house's thunder, after it
  }
  x.fillStyle = "rgba(10,8,22,0.22)";   // dimmed a little, so the page reads over it
  x.fillRect(0, 0, w, h);
}

/** Low fog in the morning, lying in the hollows of the hills and drifting. */
function fog(x: CanvasRenderingContext2D, hr: number, t: number) {
  const wx = state.weather, k = wx === "storm" || wx === "heat" ? 0 : smooth(4.8, 6.4, hr) * (1 - smooth(8.6, 10.6, hr)) * (wx === "clear" ? 0.7 : 1);
  if (k <= 0.02) return;
  const color = mix([226, 230, 236], NIGHT, (1 - daylight(hr)) * 0.6);
  for (let b = 0; b < 3; b++) {
    const y0 = Math.round(h * (0.62 + b * 0.08)), r = seeded(`fog${b}`);
    for (let i = 0; i < 7; i++) {
      const len = Math.round(w * (0.18 + r() * 0.25)), xo = Math.round(((r() * w * 1.5 + t * (1.2 + b * 0.6)) % (w * 1.5)) - len * 0.5), y = y0 + Math.round(r() * h * 0.05);
      x.fillStyle = css(color, k * 0.22);
      x.fillRect(xo, y, len, 2);
      x.fillRect(xo + 3, y - 1, len - 6, 1);
      x.fillRect(xo + 2, y + 2, len - 4, 1);
    }
  }
}

/** Rain in thin slanting streaks, or snow drifting down. */
function fall(x: CanvasRenderingContext2D, t: number, slow: number) {
  const wx = state.weather, wet = wx === "rain" || wx === "storm";
  if (!wet && wx !== "snow") return;
  const n = Math.round(((w * h) / (wet ? 300 : 360)) * (wx === "storm" ? 1.5 : 1) * (slow < 1 ? 0.5 : 1)), r = seeded("fall");
  if (wet) {
    const slant = wx === "storm" ? 0.45 : 0.22;
    x.fillStyle = css([176, 196, 230], 0.42);
    for (let i = 0; i < n; i++) {
      const sp = 110 + r() * 70, x0 = r() * (w + 40), y0 = r() * h, len = 3 + Math.floor(r() * 3), y = (y0 + t * sp) % (h + 8) - 8, xx = (x0 - (t * sp) * slant) % (w + 40);
      const bx = xx < 0 ? xx + w + 40 : xx;
      for (let j = 0; j < len; j++) x.fillRect(Math.round(bx - j * slant), Math.round(y + j), 1, 1);
    }
  } else {
    x.fillStyle = css([244, 246, 255], 0.85);
    for (let i = 0; i < n; i++) {
      const sp = 7 + r() * 9, x0 = r() * w, y0 = r() * h, big = r() < 0.18 ? 2 : 1, ph = r() * 6.3;
      x.fillRect(Math.round((x0 + Math.sin(t * 0.8 + ph) * 3 + w) % w), Math.round((y0 + t * sp) % h), big, big);
    }
  }
}
