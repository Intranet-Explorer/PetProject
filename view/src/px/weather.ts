// Light and weather (SPEC-v3.2 §1.4): day, dusk, night, season and weather as a palette shift over the whole room (a
// light map at the art's own resolution, multiplied over it), lamps lighting what is round them, a power cut as
// darkness with only the windows and lit made things, rain and snow where there is sky, storm flashes. All in whole
// pixels. The page's light and dark theme has no say here.
import { Container, Graphics, Sprite } from "pixi.js";
import type { Texture } from "pixi.js";
import type { Tile } from "../types";
import { anim, fromCanvas, tex } from "./assets";
import { fxTexture } from "./fx";
import { FX, FY, H, OX, OY, TILE, W } from "./geom";
import type { Rect } from "./geom";
import type { Lamp } from "./still";

export type Env = { phase: string; hour: number; weather: string; season: string; power: boolean; lit: boolean; cold: boolean; night: number; day: number; sky: string | null;
  windowTiles: Tile[]; windows: Rect[]; lamps: Lamp[]; sun: number[] | null;
  /** Glass that is part of the walls (a glass-roofed room): weather shows on it as drops and runs, never as rain in the room. */
  panes: Rect[] };

type RGB = number[];
const WHITE: RGB = [255, 255, 255], DEEP: RGB = [22, 34, 112], FLOOR: RGB = [84, 92, 148];
const mix = (a: RGB, b: RGB, k: number): RGB => a.map((v, i) => v + (b[i] - v) * k);
const mul = (a: RGB, b: RGB): RGB => a.map((v, i) => (v * b[i]) / 255);
const css = (c: RGB) => `rgb(${c.map((v) => Math.round(Math.max(0, Math.min(255, v)))).join(",")})`;
const WEATHER: Record<string, RGB> = { cloudy: [232, 236, 242], rain: [204, 214, 230], storm: [158, 168, 198], snow: [238, 245, 255], heat: [255, 242, 208] };
const SEASON: Record<string, RGB> = { spring: [248, 255, 244], summer: [255, 251, 238], autumn: [255, 241, 222], winter: [236, 244, 255] };
/** What is laid over a window's glass to show the sky: a colour and how strongly. By a clear day, the glass as drawn. */
const SKY: Record<string, [number, number]> = { dusk: [0xf5a070, 0.7], night: [0x232c6e, 0.72] };
const DULL: Record<string, [number, number]> = { cloudy: [0xb9c2cc, 0.35], rain: [0x8794a8, 0.5], storm: [0x5e6880, 0.62], snow: [0xe8eef6, 0.45], heat: [0xfff0c0, 0.25] };

/** SPEC-v3.5.9 §3: when the storm's lightning struck last (performance.now() milliseconds): the room and the world
 *  outside (world.ts) flash together, twice in quick succession, from then. */
export const flashAt = (now: number) => { const slot = Math.floor(now / 5200); return slot * 5200 + ((slot * 7919) % 3800); };
export const flashOn = (now: number, at = flashAt(now)) => (now > at && now < at + 90) || (now > at + 170 && now < at + 250);
/** Reduce motion: nothing flashes; lightning is a soft brighten, 0 to 1, over a little under a second. */
export const softFlash = (now: number, at = flashAt(now)) => Math.max(0, 1 - Math.abs(now - at - 350) / 450);
export const REDUCE = matchMedia("(prefers-reduced-motion: reduce)");

let halo: Texture | null = null;
function haloTexture() {
  if (halo) return halo;
  const c = document.createElement("canvas"), R = 32;
  c.width = c.height = 2 * R;
  const x = c.getContext("2d")!;
  for (const [r, a] of [[32, 0.1], [24, 0.14], [16, 0.2], [9, 0.3]]) { x.fillStyle = `rgba(255,255,255,${a})`; disc(x, R, R, r); }
  return (halo = fromCanvas(c));
}
/** A filled circle in whole pixels (the canvas's own arcs are smoothed). */
function disc(x: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  for (let dy = -r; dy < r; dy++) {
    const w = Math.round(Math.sqrt(r * r - (dy + 0.5) * (dy + 0.5)));
    x.fillRect(Math.round(cx) - w, Math.round(cy) + dy, 2 * w, 1);
  }
}

export class Light {
  dark = new Sprite();          // the light map, multiplied over the room
  glow = new Container();       // halos round what is lit, above the dark
  falling = new Container();    // rain, snow, shimmer in the room
  panes = new Graphics();       // rain, snow, stars on the window glass
  /** SPEC-v3.5.9 §4: where the sun through each window falls on the floor just now ([x, y, w, h] each), for dust in it. */
  beams: number[][] = [];
  private bright: number[] = [];   // each halo's own strength, before it flickers
  /** 0 (full day) to 1: how dark the room is just now, for anything that should show more at night. */
  darkness = 0;
  flashing = false;
  private cv = document.createElement("canvas");
  private x: CanvasRenderingContext2D;
  private env: Env | null = null;
  shape: HTMLCanvasElement | null = null;
  /** Where each pet is (x, y of its middle, in the room's pixels), set by the room every frame: in the dark each
   *  carries a little light of its own, so that a sleeper at night can still be found. */
  pools: number[] = [];   // the room's own silhouette (Still.shape), set by the room
  private ambient: RGB = WHITE;
  private drawn = -1e9;
  private dirty = true;
  private wasFlashing = false;
  private glassy: Rect[] = [];
  private dip = 0;
  private dipped = false;
  private vig: CanvasGradient | null = null;
  private vigFor = "";
  private drops: Sprite[] = [];
  private soft = 0;

  constructor() {
    [this.cv.width, this.cv.height] = [W, H];
    this.x = this.cv.getContext("2d")!;
    this.dark.texture = fromCanvas(this.cv);
    this.dark.blendMode = "multiply";
    this.glow.blendMode = "add";
    for (let i = 0; i < 90; i++) {
      const s = new Sprite(fxTexture("drop"));
      s.visible = false;
      this.drops.push(s);
      this.falling.addChild(s);
    }
  }

  set(env: Env) {
    this.env = env;
    this.dirty = true;
    this.glassy = [...env.windows, ...env.panes];
    const night = env.phase === "night", dusk = env.phase === "dusk", d = Math.max(0, Math.min(1, env.night));
    let a: RGB = WHITE;
    if (dusk) a = mix(mix(a, [255, 176, 128], 0.32), DEEP, 0.12 + d * 0.2);
    if (night) a = mix(a, DEEP, 0.5 + d * 0.45);
    if (!night) a = mul(a, WEATHER[env.weather] ?? WHITE);
    if (!night && env.day && !env.lit) a = mix(a, DEEP, Math.min(1, env.day) * 0.6);   // a room with little daylight is dim by day too, unless a light is on
    a = mul(a, SEASON[env.season] ?? WHITE);
    if (night && env.sky === "open" && env.season === "winter") a = mix(a, [180, 215, 255], 0.4);   // snow under the open sky gives the moon back: dim blue-white, its drifts still to be seen, never a flat dark wash
    if (!env.power) a = night || dusk ? mix(a, [8, 10, 34], 0.5) : mul(a, [226, 226, 238]);
    else if (env.lit && (night || dusk)) a = mix(a, [255, 236, 200], 0.14);
    if (env.cold) a = mul(a, [224, 238, 255]);
    a = a.map((v, i) => Math.max(v, FLOOR[i]));   // however dark the room, what lies on its floor can still be made out
    this.ambient = a;
    this.darkness = 1 - (a[0] * 0.3 + a[1] * 0.59 + a[2] * 0.11) / 255;

    for (const c of this.glow.removeChildren()) c.destroy();
    for (const l of env.lamps) {
      const s = new Sprite(haloTexture());
      s.anchor.set(0.5);
      s.position.set(l.x, l.y);
      s.scale.set(l.r / 32);
      s.tint = (l.color[0] << 16) | (l.color[1] << 8) | l.color[2];
      s.alpha = l.color[0] < 128 ? 0 : Math.min(0.4, this.darkness * 0.7);   // by day a lamp hardly shows; by night it must not bleach what it stands on
      this.glow.addChild(s);
    }
    this.bright = this.glow.children.map((c) => c.alpha);
    this.sunbeams(env);
  }

  /** SPEC-v3.5.9 §4: by day the sun comes in at each window and lies on the floor in a shaft that swings across it with
   *  the hour, short at noon and long morning and evening, warm toward evening; faint through cloud, none in a storm. */
  private sunbeams(e: Env) {
    this.beams = [];
    const strength = e.phase === "night" ? 0 : ({ clear: 1, heat: 1, cloudy: 0.35, rain: 0.18, snow: 0.25 } as Record<string, number>)[e.weather] ?? 0;
    if (!strength) return;
    const h = e.hour, up = Math.sin((Math.PI * Math.max(0, Math.min(14, h - 6))) / 14), slope = (13 - h) * 0.11, long = Math.round(26 + (1 - up) * 34);
    const warm = mix([255, 246, 214], [255, 178, 104], Math.max(0, Math.min(1, (h - 15.5) / 3))), color = (warm[0] << 16) | (warm[1] << 8) | warm[2];
    const g = new Graphics();
    for (const w of e.windows) {
      if (w.w < 4) continue;
      for (let y = 0; y < long; y++) {
        const k = y / long, x = Math.round(w.x + y * slope - k * 2), ww = Math.round(w.w + k * 4);
        g.rect(x, OY + y, ww, 1).fill({ color, alpha: strength * 0.3 * (1 - k * 0.7) * (e.phase === "dusk" ? 0.6 : 1) });
      }
      this.beams.push([w.x + (long / 2) * slope, OY + long / 2, w.w + 2, long]);
    }
    this.glow.addChildAt(g, 0);
    this.bright.unshift(1);
  }

  step(now: number) {
    const e = this.env;
    if (!e) return;
    const storm = e.weather === "storm", at = flashAt(now), soft = storm && REDUCE.matches ? Math.round(softFlash(now, at) * 8) / 8 : 0;
    this.flashing = storm && !REDUCE.matches && flashOn(now, at);
    if (soft !== this.soft) { this.soft = soft; this.dirty = true; }
    if (this.flashing && !this.wasFlashing) this.dip = now + 260;   // the lamps flicker once at a flash
    this.glow.alpha = now < this.dip ? 0.3 : 1;
    if (!REDUCE.matches) this.glow.children.forEach((c, i) => { if (i || !this.beams.length) c.alpha = this.bright[i] * (0.9 + 0.1 * Math.sin(now / 150 + i * 1.7) * Math.sin(now / 67 + i)); });   // SPEC-v3.5.9 §7: a lamp's glow lives
    if (this.dirty || this.flashing !== this.wasFlashing || (now < this.dip) !== this.dipped || now - this.drawn > (this.pools.length && this.darkness > 0.25 ? 70 : 160)) this.map(now);
    this.wasFlashing = this.flashing;
    this.fall(now);
    this.glass(now);
  }

  /** The light map: the room's own light, the windows, each lamp in stepped rings. */
  private map(now: number) {
    const e = this.env!, x = this.x, night = e.phase === "night";
    let a = this.ambient;
    if (this.flashing) a = mix(a, WHITE, e.sky === "open" ? 0.75 : e.sky === "glass" ? 0.6 : e.windows.length ? 0.22 : 0);
    else if (this.soft) a = mix(a, WHITE, this.soft * (e.sky ? 0.3 : e.windows.length ? 0.12 : 0));
    x.globalCompositeOperation = "source-over";
    // the dark gathers at the edges of the room and leaves its middle, where everyone is, plain to see (SPEC-v3.3 §5):
    // the darker the hour or the weather, the more the middle is lifted out of it
    const dk = this.darkness, key = a.join();
    if (dk > 0.08 && !this.flashing) {
      if (key !== this.vigFor) {
        const g = (this.vig = x.createRadialGradient(0, 0, 0.25, 0, 0, 1)), mid = mix(a, WHITE, Math.min(0.4, dk * 0.9)), edge = a.map((v) => v * (1 - Math.min(0.25, dk * 0.5)));
        g.addColorStop(0, css(mid));
        g.addColorStop(0.55, css(mix(mid, a, 0.6)));
        g.addColorStop(1, css(edge));
        this.vigFor = key;
      }
      x.save();
      x.translate(W / 2, OY + (FY * TILE) / 2);
      x.scale(W * 0.66, H * 0.7);
      x.fillStyle = this.vig!;
      x.fillRect(-1, -1, 2, 2);
      x.restore();
    } else {
      x.fillStyle = css(a);
      x.fillRect(0, 0, W, H);
    }
    x.globalCompositeOperation = "lighten";
    // what comes in at the windows: by night the moon, in a storm the flash; it is all there is in a power cut
    const pool = this.flashing ? WHITE : night ? mix(a, [150, 168, 236], e.power ? 0.3 : 0.5) : a;
    if (night || this.flashing) for (const [tx, ty] of e.windowTiles) {
      const [cx, cy] = [OX + tx * TILE + 8, OY + ty * TILE + 8];
      [[24, 0.3], [17, 0.6], [10, 1]].forEach(([r, k]) => { x.fillStyle = css(mix(a, pool, k)); disc(x, cx, cy, r); });
    }
    if (e.sun && !night) {   // the attic's shaft of sun: a warm patch that moves with the hour
      x.fillStyle = css(mix(a, [255, 244, 190], e.weather === "clear" || e.weather === "heat" ? 1 : 0.4));
      x.fillRect(e.sun[0] - 14, e.sun[1] - 9, 28, 18);
    }
    for (const l of e.lamps) {
      const flick = Math.round(Math.sin(now / 190 + l.x) * 0.8), dim = l.color[0] < 128, weak = now < this.dip && !dim ? 0.35 : 1;
      if (dim) x.globalCompositeOperation = "darken";
      [[1, 0.22], [0.76, 0.45], [0.52, 0.7], [0.3, 0.92]].forEach(([k, t]) => {
        x.fillStyle = css(mix(a, dim ? mul(a, [150, 150, 190]) : mix(l.color, WHITE, 0.2), t * weak * (dim ? 1 : Math.min(1, this.darkness * 2.4))));
        disc(x, l.x, l.y, Math.round(l.r * k) + flick);
      });
      x.globalCompositeOperation = "lighten";
    }
    if (this.darkness > 0.25) for (let i = 0; i < this.pools.length; i += 2) {   // a pet is never lost in the dark
      [[19, 0.2], [13, 0.4], [8, 0.6]].forEach(([r, k]) => { x.fillStyle = css(mix(a, [226, 232, 255], k)); disc(x, this.pools[i], this.pools[i + 1], r); });
    }
    x.globalCompositeOperation = "source-over";
    x.fillStyle = "#ffffff";
    for (const w of e.windows) x.fillRect(Math.round(w.x), Math.round(w.y), Math.round(w.w), Math.round(w.h));   // the glass keeps its own light: the sky is painted on it (see glass)
    if (this.shape) {   // light and dark fall on the room only: beyond its walls the page shows through
      x.globalCompositeOperation = "destination-in";
      x.drawImage(this.shape, 0, 0);
      x.globalCompositeOperation = "source-over";
    }
    this.dipped = now < this.dip;
    this.dark.texture.source.update();
    this.drawn = now;
    this.dirty = false;
  }

  /** Rain, snow or heat in a room that has sky over it: all of it in the open, a little of it on a glass roof. */
  private fall(now: number) {
    const e = this.env!, wet = e.weather === "rain" || e.weather === "storm", snow = e.weather === "snow", heat = e.weather === "heat" && e.phase === "day";
    const n = e.sky !== "open" || !(wet || snow || heat) ? 0 : Math.round(60 * (e.weather === "storm" ? 1.4 : heat ? 0.3 : 1));   // only under the open sky: under glass it would read as raining indoors
    const [x0, y0, w, h] = e.sky === "open" ? [0, 0, W, H] : [OX, 0, FX * TILE, OY + FY * TILE];
    const rain = anim("fx.rain", "kinds")?.frames.length ?? 0, snowy = anim("fx.snow", "kinds")?.frames.length ?? 0;   // the art's own drops and flakes, if it has them
    for (let i = 0; i < this.drops.length; i++) {
      const s = this.drops[i];
      s.visible = i < n;
      if (i >= n) continue;
      const u = (i * 0.618034) % 1, v = (i * 0.3779) % 1;
      if (wet) {
        const t = now * (0.09 + (i % 5) * 0.012);
        s.texture = rain ? tex("fx.rain", "kinds", i % rain) : fxTexture("drop");
        s.position.set(x0 + ((u * w - t * 0.25 + w * 1000) % w), y0 + ((v * h + t) % h));
        s.tint = 0xffffff;
        s.alpha = e.sky === "open" ? 0.75 : 0.4;
      } else if (snow) {
        s.texture = snowy ? tex("fx.snow", "kinds", i % snowy) : fxTexture(i % 3 ? "speck" : "grit");
        s.position.set(x0 + ((u * w + Math.sin(now / 900 + i) * 5 + w) % w), y0 + ((v * h + now * (0.008 + (i % 4) * 0.002)) % h));
        s.tint = 0xffffff;
        s.alpha = e.sky === "open" ? 0.95 : 0.5;
      } else {   // heat: a few pale motes rising, wavering
        s.texture = fxTexture("speck");
        s.position.set(x0 + ((u * w + Math.sin(now / 400 + i * 2) * 3 + w) % w), y0 + h - ((v * h + now * 0.006) % h));
        s.tint = 0xfff0b8;
        s.alpha = 0.45;
      }
    }
  }

  /** On the window glass: stars and a moon on a clear night, rain running down, snow passing. */
  private glass(now: number) {
    const e = this.env!, g = this.panes.clear(), wet = e.weather === "rain" || e.weather === "storm";
    for (const [i, w] of this.glassy.entries()) {
      const [x, y, ww, hh] = [Math.round(w.x), Math.round(w.y), Math.round(w.w), Math.round(w.h)], wall = i >= e.windows.length;   // a pane of a glass wall keeps its own picture of the sky
      if (ww < 3 || hh < 3) continue;
      const [color, alpha] = this.flashing ? [0xffffff, wall ? 0.5 : 0.9] : wall ? [0, 0] : SKY[e.phase] ?? DULL[e.weather] ?? [0, 0];
      if (alpha) g.rect(x, y, ww, hh).fill({ color, alpha });
      if (e.season === "winter" && !wall) {   // SPEC-v3.5.9 §4: frost creeping in from the corners and along the edges
        for (const [cx, sx] of [[x, 1], [x + ww - 1, -1]]) for (const [cy, sy] of [[y, 1], [y + hh - 1, -1]]) g.rect(cx, cy, 1, 1).rect(cx + sx, cy, 1, 1).rect(cx, cy + sy, 1, 1).rect(cx + 2 * sx, cy, 1, 1).rect(cx, cy + 2 * sy, 1, 1).rect(cx + sx, cy + sy, 1, 1);
        for (let i = 3; i < ww - 3; i += 3 + (i % 2)) g.rect(x + i, y + hh - 1, 1, 1);
        for (let j = 3; j < hh - 3; j += 4) g.rect(x, y + j, 1, 1).rect(x + ww - 1, y + j + 1, 1, 1);
        g.fill({ color: 0xf2f8ff, alpha: 0.85 });
      }
      if (wet) {
        for (let i = 0; i < Math.max(2, ww >> 2); i++) {
          const k = (now / 500 + i * 0.37) % 1;
          g.rect(x + ((i * 5 + 1) % ww), y + Math.floor(k * (hh - 2)), 1, 2);
        }
        g.fill({ color: 0xffffff, alpha: 0.8 });
      } else if (e.weather === "snow") {
        for (let i = 0; i < Math.max(2, ww >> 2); i++) g.rect(x + ((i * 5 + 2 + Math.floor(now / 700)) % ww), y + Math.floor(((now / 2400 + i * 0.29) % 1) * (hh - 1)), 1, 1);
        g.fill(0xffffff);
      } else if (e.phase === "night" && !this.flashing) {
        g.rect(x + 1, y + 1, 1, 1).rect(x + ((ww * 2) / 3 | 0), y + (hh >> 1), 1, 1).fill({ color: 0xffffff, alpha: 0.6 + 0.4 * Math.sin(now / 700) });
        if (ww >= 6 && hh >= 5) g.rect(x + ww - 4, y + 1, 2, 2).fill(0xf6f0c8);
      }
    }
  }
}
