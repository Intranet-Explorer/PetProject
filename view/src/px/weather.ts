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

export type Env = { phase: string; weather: string; season: string; power: boolean; lit: boolean; cold: boolean; night: number; day: number; sky: string | null;
  windowTiles: Tile[]; windows: Rect[]; lamps: Lamp[]; sun: number[] | null };

type RGB = number[];
const WHITE: RGB = [255, 255, 255], DEEP: RGB = [22, 34, 112];
const mix = (a: RGB, b: RGB, k: number): RGB => a.map((v, i) => v + (b[i] - v) * k);
const mul = (a: RGB, b: RGB): RGB => a.map((v, i) => (v * b[i]) / 255);
const css = (c: RGB) => `rgb(${c.map((v) => Math.round(Math.max(0, Math.min(255, v)))).join(",")})`;
const WEATHER: Record<string, RGB> = { cloudy: [232, 236, 242], rain: [204, 214, 230], storm: [158, 168, 198], snow: [238, 245, 255], heat: [255, 242, 208] };
const SEASON: Record<string, RGB> = { spring: [248, 255, 244], summer: [255, 251, 238], autumn: [255, 241, 222], winter: [236, 244, 255] };
/** What is laid over a window's glass to show the sky: a colour and how strongly. By a clear day, the glass as drawn. */
const SKY: Record<string, [number, number]> = { dusk: [0xf5a070, 0.7], night: [0x232c6e, 0.72] };
const DULL: Record<string, [number, number]> = { cloudy: [0xb9c2cc, 0.35], rain: [0x8794a8, 0.5], storm: [0x5e6880, 0.62], snow: [0xe8eef6, 0.45], heat: [0xfff0c0, 0.25] };

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
  /** 0 (full day) to 1: how dark the room is just now, for anything that should show more at night. */
  darkness = 0;
  flashing = false;
  private cv = document.createElement("canvas");
  private x: CanvasRenderingContext2D;
  private env: Env | null = null;
  shape: HTMLCanvasElement | null = null;   // the room's own silhouette (Still.shape), set by the room
  private ambient: RGB = WHITE;
  private drawn = -1e9;
  private dirty = true;
  private wasFlashing = false;
  private drops: Sprite[] = [];

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
    const night = env.phase === "night", dusk = env.phase === "dusk", d = Math.max(0, Math.min(1, env.night));
    let a: RGB = WHITE;
    if (dusk) a = mix(mix(a, [255, 176, 128], 0.32), DEEP, 0.12 + d * 0.2);
    if (night) a = mix(a, DEEP, 0.5 + d * 0.45);
    if (!night) a = mul(a, WEATHER[env.weather] ?? WHITE);
    if (!night && env.day && !env.lit) a = mix(a, DEEP, Math.min(1, env.day) * 0.6);   // a room with little daylight is dim by day too, unless a light is on
    a = mul(a, SEASON[env.season] ?? WHITE);
    if (!env.power) a = night || dusk ? mix(a, [8, 10, 34], 0.5) : mul(a, [226, 226, 238]);
    else if (env.lit && (night || dusk)) a = mix(a, [255, 236, 200], 0.14);
    if (env.cold) a = mul(a, [224, 238, 255]);
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
  }

  step(now: number) {
    const e = this.env;
    if (!e) return;
    const storm = e.weather === "storm", slot = Math.floor(now / 5200), at = slot * 5200 + ((slot * 7919) % 3800);
    this.flashing = storm && ((now > at && now < at + 90) || (now > at + 170 && now < at + 250));
    if (this.dirty || this.flashing !== this.wasFlashing || now - this.drawn > 160) this.map(now);
    this.wasFlashing = this.flashing;
    this.fall(now);
    this.glass(now);
  }

  /** The light map: the room's own light, the windows, each lamp in stepped rings. */
  private map(now: number) {
    const e = this.env!, x = this.x, night = e.phase === "night";
    let a = this.ambient;
    if (this.flashing) a = mix(a, WHITE, e.sky === "open" ? 0.75 : e.sky === "glass" ? 0.6 : e.windows.length ? 0.22 : 0);
    x.globalCompositeOperation = "source-over";
    x.fillStyle = css(a);
    x.fillRect(0, 0, W, H);
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
      const flick = Math.round(Math.sin(now / 190 + l.x) * 0.8), dim = l.color[0] < 128;
      if (dim) x.globalCompositeOperation = "darken";
      [[1, 0.22], [0.76, 0.45], [0.52, 0.7], [0.3, 0.92]].forEach(([k, t]) => {
        x.fillStyle = css(mix(a, dim ? mul(a, [150, 150, 190]) : mix(l.color, WHITE, 0.2), t * (dim ? 1 : Math.min(1, this.darkness * 2.4))));
        disc(x, l.x, l.y, Math.round(l.r * k) + flick);
      });
      x.globalCompositeOperation = "lighten";
    }
    x.globalCompositeOperation = "source-over";
    x.fillStyle = "#ffffff";
    for (const w of e.windows) x.fillRect(Math.round(w.x), Math.round(w.y), Math.round(w.w), Math.round(w.h));   // the glass keeps its own light: the sky is painted on it (see glass)
    if (this.shape) {   // light and dark fall on the room only: beyond its walls the page shows through
      x.globalCompositeOperation = "destination-in";
      x.drawImage(this.shape, 0, 0);
      x.globalCompositeOperation = "source-over";
    }
    this.dark.texture.source.update();
    this.drawn = now;
    this.dirty = false;
  }

  /** Rain, snow or heat in a room that has sky over it: all of it in the open, a little of it on a glass roof. */
  private fall(now: number) {
    const e = this.env!, wet = e.weather === "rain" || e.weather === "storm", snow = e.weather === "snow", heat = e.weather === "heat" && e.phase === "day";
    const n = !e.sky || !(wet || snow || heat) ? 0 : Math.round((e.sky === "open" ? 60 : 26) * (e.weather === "storm" ? 1.4 : heat ? 0.3 : 1));
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
    for (const w of e.windows) {
      const [x, y, ww, hh] = [Math.round(w.x), Math.round(w.y), Math.round(w.w), Math.round(w.h)];
      if (ww < 3 || hh < 3) continue;
      const [color, alpha] = this.flashing ? [0xffffff, 0.9] : SKY[e.phase] ?? DULL[e.weather] ?? [0, 0];
      if (alpha) g.rect(x, y, ww, hh).fill({ color, alpha });
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
