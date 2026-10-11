// Words over the room (SPEC-v3.2 §5.3): each pet's name plate in its family's colour, a thought caption with what it
// means to do, speech bubbles, what the box says. Lettering is the room's pixel face at a finer scale than the art, so
// it stays readable. Nothing here may cover a pet's face or another bubble: each is placed in the nearest clear spot,
// and when the room is crowded the captions that do not fit shrink to three dots and take turns.
import { Container, Sprite, Texture } from "pixi.js";
import { canvasOf, def, fromCanvas, has } from "./assets";
import { draw, LINE, measure, plain, wrap } from "./font";
import { clamp, hit, seeded } from "./geom";
import type { Rect } from "./geom";

export type Label = Rect & { kind: string };
/** What the room wants said about one pet. `caption`: its intention, or null. `say`: its words, with whom they are for. */
export type Who = { id: string; name: string; family: number; selected: boolean; faded: boolean; caption: string | null; thinking: boolean;
  say: { key: string; text: string; to: string | null; song: boolean } | null };

const INK = "#2b2233", PAPER = "#fffdf2", ACCENT = "#ffb347";
const FAMILY: Record<number, string> = { 1: "#1f7a8c", 2: "#a8468a" };   // each family's colour (SPEC-v3.1 §7.4); the page's style has the same two

function canvas(w: number, h: number) {
  const c = document.createElement("canvas");
  [c.width, c.height] = [Math.max(1, w), Math.max(1, h)];
  return [c, c.getContext("2d")!] as const;
}
/** A box with cut corners and a one-pixel outline. */
function frame(x: CanvasRenderingContext2D, w: number, h: number, fill: string, ink: string) {
  x.fillStyle = ink;
  x.fillRect(2, 0, w - 4, h); x.fillRect(0, 2, w, h - 4); x.fillRect(1, 1, w - 2, h - 2);
  x.fillStyle = fill;
  x.fillRect(2, 1, w - 4, h - 2); x.fillRect(1, 2, w - 2, h - 4);
}
/** A frame from the art that stretches to any size (its `slice` says how wide its borders are). False if there is none. */
function nine(x: CanvasRenderingContext2D, name: string, w: number, h: number) {
  const d = def(name);
  if (!d?.slice) return false;
  const src = canvasOf(name), [l, t, r, b] = d.slice, [sw, sh] = [src.width, src.height];
  x.imageSmoothingEnabled = false;
  const xs = [[0, l, 0, l], [l, sw - l - r, l, w - l - r], [sw - r, r, w - r, r]], ys = [[0, t, 0, t], [t, sh - t - b, t, h - t - b], [sh - b, b, h - b, b]];
  for (const [sx, sW, dx, dW] of xs) for (const [sy, sH, dy, dH] of ys) if (dW > 0 && dH > 0) x.drawImage(src, sx, sy, sW, sH, dx, dy, dW, dH);
  return true;
}
function plateCanvas(name: string, color: string, ring: boolean) {
  const text = plain(name), [c, x] = canvas(measure(text) + 6, 12);
  frame(x, c.width, c.height, color, ring ? ACCENT : INK);
  draw(x, [text], 3, 2, { color: "#ffffff" });
  return c;
}
function bubbleCanvas(lines: string[], o: { fill: string; ink: string; text: string; head?: string; headColor?: string; static?: string; art?: string }) {
  const head = o.head ? plain(o.head) : null, art = o.art && def(o.art)?.slice ? o.art : null, px = art ? 6 : 4, py = art ? 4 : 3;
  const w = Math.max(...lines.map(measure), head ? measure(head) : 0, o.static != null ? 46 : 0) + 2 * px;
  const rows = lines.length + (head ? 1 : 0) + (o.static != null ? 1 : 0), [c, x] = canvas(w, rows * LINE + 2 * py - 1 + (art ? 1 : 0));
  if (!art || !nine(x, art, c.width, c.height)) frame(x, c.width, c.height, o.fill, o.ink);
  if (head) draw(x, [head], px, py, { color: o.headColor ?? o.ink });
  const y = py + (head ? LINE : 0);
  draw(x, lines, px, y, { color: o.text });
  if (o.static != null) {   // the box between stations: a jagged line
    const r = seeded(o.static);
    x.fillStyle = o.text;
    for (let i = 0, yy = 3; i < w - 2 * px; i++) { yy = clamp(yy + Math.round(r() * 4 - 2), 0, 6); x.fillRect(px + i, y + lines.length * LINE + yy, 1, 1); }
  }
  return c;
}
function dotsCanvas() {
  const [c, x] = canvas(15, 11);
  if (!nine(x, "ui.bubble.think", 15, 11)) frame(x, 15, 11, PAPER, INK);
  x.fillStyle = INK;
  for (const i of [4, 7, 10]) x.fillRect(i, 4, 1, 2);
  return c;
}
let tails: { say: Texture; think: Texture } | null = null;
function tailTextures() {
  if (tails) return tails;
  const [s, sx] = canvas(7, 4), [t, tx] = canvas(5, 6);
  sx.fillStyle = INK; sx.fillRect(0, 0, 7, 1); sx.fillRect(1, 1, 5, 1); sx.fillRect(2, 2, 3, 1); sx.fillRect(3, 3, 1, 1);
  sx.fillStyle = "#ffffff"; sx.fillRect(1, 0, 5, 1); sx.fillRect(2, 1, 3, 1); sx.fillRect(3, 2, 1, 1);
  tx.fillStyle = INK; tx.fillRect(1, 0, 4, 4); tx.fillRect(0, 4, 2, 2);
  tx.fillStyle = PAPER; tx.fillRect(2, 1, 2, 2);
  // the art's own tails, where it has them
  return (tails = { say: fromCanvas(has("ui.bubble.say.tail") ? canvasOf("ui.bubble.say.tail") : s), think: fromCanvas(has("ui.bubble.think.tail") ? canvasOf("ui.bubble.think.tail") : t) });
}

/** One piece of lettering as a sprite; its texture is made again only when what it says changes. */
class Card {
  s = new Sprite();
  w = 0;
  h = 0;
  alpha = 0;        // eased toward `want` every frame
  want = 0;
  dx = 0;           // where it sits, from the top middle of its pet's head
  dy = 0;
  private key = "";
  set(key: string, F: number, make: () => HTMLCanvasElement) {
    if (key === this.key) return;
    this.key = key;
    if (this.s.texture !== Texture.EMPTY) this.s.texture.destroy(true);
    const c = make();
    this.s.texture = fromCanvas(c);
    this.s.scale.set(F);
    [this.w, this.h] = [c.width * F, c.height * F];
  }
  ease(dt: number) {
    this.alpha += clamp(this.want - this.alpha, -dt / 350, dt / 220);
    this.s.alpha = this.alpha;
    this.s.visible = this.alpha > 0.01;
  }
  destroy() {
    if (this.s.texture !== Texture.EMPTY) this.s.texture.destroy(true);
    this.s.destroy();
  }
}
/** `side`: where the bubble is from its pet: 0 over or under it, -1 to its left, 1 to its right (the tail goes on that edge). */
type Entry = { who: Who; plate: Card; cap: Card; dots: Card; say: Card; tail: Sprite; tailFor: Card | null; tailUp: boolean; side: number; capText: string };
type Spot = Rect & { up: boolean; side: number };

export class Labels {
  c = new Container();
  placed: Label[] = [];
  private tailLayer = new Container();
  private cards = new Container();
  private entries = new Map<string, Entry>();
  private box: { card: Card; tail: Sprite; key: string } | null = null;
  private F = 2;
  private laid = -1e9;

  constructor() {
    this.c.addChild(this.cards, this.tailLayer);
  }

  /** What to say about whom, from a snapshot. `F`: screen pixels to a pixel of lettering. `wide`: the room's width in lettering pixels. */
  sync(who: Who[], radio: { key: string; text: string; source: string } | null, F: number, wide: number) {
    this.F = F;
    for (const [id, e] of this.entries) if (!who.some((w) => w.id === id)) {
      for (const k of [e.plate, e.cap, e.dots, e.say]) k.destroy();
      e.tail.destroy();
      this.entries.delete(id);
    }
    for (const w of who) {
      let e = this.entries.get(w.id);
      if (!e) {
        e = { who: w, plate: new Card(), cap: new Card(), dots: new Card(), say: new Card(), tail: new Sprite(), tailFor: null, tailUp: false, side: 0, capText: "" };
        this.entries.set(w.id, e);
        this.cards.addChild(e.plate.s, e.dots.s, e.cap.s, e.say.s);
        this.tailLayer.addChild(e.tail);
        e.dots.set("dots" + F, F, dotsCanvas);
      }
      e.who = w;
      e.plate.set(`${w.name}|${w.family}|${w.selected}|${w.faded}|${F}`, F, () => plateCanvas(w.name, w.faded ? "#6d6875" : FAMILY[w.family] ?? FAMILY[1], w.selected));
      e.plate.want = 1;
      if (w.caption) {   // an intention that has ended keeps its words while it fades
        e.capText = w.caption;
        e.cap.set(`${w.caption}|${F}|${wide}`, F, () => bubbleCanvas(wrap(w.caption!, Math.round(wide * 0.32), 2), { fill: PAPER, ink: INK, text: "#3a3350", art: "ui.bubble.think" }));
      }
      if (w.say) {
        const s = w.say, text = s.song ? `♪ ${s.text} ♪` : s.text;
        e.say.set(`${s.key}|${F}|${wide}`, F, () => bubbleCanvas(wrap(text, Math.round(wide * 0.3), 3), { fill: "#ffffff", ink: INK, text: INK, head: s.to ? `→ ${s.to}` : undefined, headColor: "#b3541e", art: "ui.bubble.say" }));
      }
    }
    if (radio?.key !== this.box?.key) {
      this.box?.card.destroy();
      this.box?.tail.destroy();
      this.box = null;
      if (radio) {
        const card = new Card(), tail = new Sprite(tailTextures().say);
        card.set(radio.key + F, F, () => bubbleCanvas(radio.text ? wrap(`"${radio.text}"`, Math.round(wide * 0.34), 3) : ["only static"],
          { fill: "#fbf0cf", ink: "#7a4a1e", text: radio.text ? INK : "#6b5a48", head: radio.text ? `the box - ${radio.source}` : "the box", headColor: "#7a4a1e", static: radio.text ? undefined : radio.key }));
        card.want = 1;
        tail.scale.set(F);
        tail.tint = 0xfbf0cf;
        this.cards.addChild(card.s);
        this.tailLayer.addChild(tail);
        this.box = { card, tail, key: radio.key };
      }
    }
    this.laid = -1e9;
  }

  /** Every frame: put each card by its pet (`heads`: each pet's body on screen), and every so often work out again
   *  where everything goes. `avoid`: parts of the room the page has covered. `boxAt`: where the box stands. */
  step(now: number, dt: number, heads: Map<string, Rect>, W: number, H: number, avoid: Rect[], boxAt: number[] | null) {
    if (now - this.laid > 140) {
      this.laid = now;
      this.lay(now, heads, W, H, avoid, boxAt);
    }
    const F = this.F;
    for (const [id, e] of this.entries) {
      const b = heads.get(id);
      if (!b) continue;
      const cx = b.x + b.w / 2;
      for (const k of [e.plate, e.cap, e.dots, e.say]) {
        k.ease(dt);
        k.s.position.set(Math.round(clamp(cx + k.dx, 1, Math.max(1, W - k.w - 1))), Math.round(clamp(b.y + k.dy, 1, Math.max(1, H - k.h - 1))));
      }
      const t = e.tailFor, tail = e.tail;
      tail.visible = !!t && t.alpha > 0.5 && (!!e.side || !e.tailUp);   // under its pet the name plate lies between: no tail
      if (t && tail.visible) {
        tail.texture = t === e.say ? tailTextures().say : tailTextures().think;
        if (e.side) {   // beside its pet: the tail on the near edge, turned a quarter
          tail.rotation = (e.side * Math.PI) / 2;
          tail.scale.set(F, F);
          tail.position.set(e.side < 0 ? t.s.x + t.w - F : t.s.x + F, Math.round(clamp(b.y + 2 * F, t.s.y + 2 * F, t.s.y + t.h - 8 * F)) + (e.side < 0 ? 0 : 6 * F));
        } else {
          tail.rotation = 0;
          tail.scale.set(F, e.tailUp ? -F : F);
          // a speech tail's top row lies on the bubble's outline; a thought's dots hang a pixel clear of it
          const lap = t === e.say ? -F : F;
          tail.position.set(Math.round(clamp(cx - 3 * F, t.s.x + 4 * F, t.s.x + t.w - 11 * F)), e.tailUp ? t.s.y - lap : t.s.y + t.h + lap);
        }
      }
    }
    if (this.box) this.box.card.ease(dt);
  }

  /** Decide where everything goes (§10.7: no plate, caption or bubble on another, none over a face). */
  private lay(now: number, heads: Map<string, Rect>, W: number, H: number, avoid: Rect[], boxAt: number[] | null) {
    const F = this.F, placed: Label[] = avoid.map((r) => ({ ...r, kind: "page" }));
    const list = [...this.entries.values()].filter((e) => heads.has(e.who.id)).sort((a, b) => heads.get(a.who.id)!.y - heads.get(b.who.id)!.y);
    const faces = list.map((e) => ({ ...heads.get(e.who.id)!, id: e.who.id }));
    const clear = (r: Rect, but?: string) => r.x >= 0 && r.y >= 0 && r.x + r.w <= W && r.y + r.h <= H && !placed.some((q) => hit(q, r)) && !faces.some((f) => f.id !== but && hit(f, r));
    const put = (k: Card, b: Rect, r: Rect, kind: string) => {
      [k.dx, k.dy] = [r.x - (b.x + b.w / 2), r.y - b.y];
      placed.push({ ...r, kind });
    };
    // name plates: under the feet; else over the head or to a side; never on a face if there is any way round
    const shared = (a: Rect, b: Rect) => Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
    for (const e of list) {
      const b = heads.get(e.who.id)!, { w, h } = e.plate, cx = b.x + b.w / 2, under = b.y + b.h + F, over = b.y - h - F;
      const fit = (x: number, y: number) => ({ x: Math.round(clamp(x, 1, W - w - 1)), y: Math.round(clamp(y, 1, H - h - 1)), w, h });
      const tries = [fit(cx - w / 2, under), fit(cx - w / 2, over), fit(cx - w, under), fit(cx, under), fit(cx - w, over), fit(cx, over), fit(cx - w / 2, under + h + F), fit(b.x - w - F, b.y + b.h - h), fit(b.x + b.w + F, b.y + b.h - h),
                     fit(cx - w / 2, under + 2 * (h + F)), fit(cx - w / 2, over - h - F)];
      const cost = (r: Rect) => placed.reduce((n, q) => n + shared(q, r) * 3, 0) + faces.reduce((n, f) => n + (f.id === e.who.id ? 0 : shared(f, r)), 0);
      put(e.plate, b, tries.find((r) => clear(r, e.who.id)) ?? tries.reduce((best, r) => (cost(r) < cost(best) ? r : best)), "pet");
    }
    /** The clear spot for a bubble nearest its pet: over it, to a side, higher, under its plate; `anywhere`: failing those, wherever in the room is clear. */
    const spot = (b: Rect, w: number, h: number, anywhere: boolean): Spot | null => {
      const cx = b.x + b.w / 2, gap = 4 * F, over = b.y - gap - h, fit = (x: number, y: number) => ({ x: Math.round(clamp(x, 1, W - w - 1)), y: Math.round(clamp(y, 1, H - h - 1)), w, h });
      const tries = [fit(cx - w / 2, over), fit(cx - w * 0.25, over), fit(cx - w * 0.75, over), fit(cx - w / 2, over - h - F), fit(cx - w * 0.2, over - h - F), fit(cx - w * 0.8, over - h - F),
                     fit(cx - w / 2, b.y + b.h + 14 * F), fit(cx - w * 0.25, b.y + b.h + 14 * F), fit(cx - w * 0.75, b.y + b.h + 14 * F), fit(cx - w / 2, over - 2 * (h + F)),
                     fit(b.x - gap - w, b.y - h / 4), fit(b.x + b.w + gap, b.y - h / 4), fit(b.x - gap - w, b.y - h), fit(b.x + b.w + gap, b.y - h), fit(b.x - gap - w, b.y + b.h - h), fit(b.x + b.w + gap, b.y + b.h - h)];
      const near = tries.length;
      if (anywhere) for (let gy = 0; gy < 7; gy++) for (let gx = 0; gx < 7; gx++) tries.push(fit((gx / 6) * (W - w), (gy / 6) * (H - h)));
      let best: Rect | null = null, far = Infinity;
      for (const [i, r] of tries.entries()) {
        if (!clear(r)) continue;
        if (i < near) { best = r; break; }
        const d = Math.hypot(r.x + w / 2 - cx, r.y + h / 2 - b.y);
        if (d < far) [best, far] = [r, d];
      }
      return best && { ...best, up: best.y > b.y + b.h / 2, side: best.x + w <= b.x ? -1 : best.x >= b.x + b.w ? 1 : 0 };
    };
    for (const e of list) {   // speech first: it is the thing most worth reading, and it does not last
      const b = heads.get(e.who.id)!;
      e.tailFor = null;
      e.say.want = 0;
      if (!e.who.say) continue;
      const r = spot(b, e.say.w, e.say.h, true);
      if (!r) continue;
      put(e.say, b, r, "bubble");
      const close = r.side ? r.y < b.y + b.h && r.y + r.h > b.y && Math.min(Math.abs(r.x - b.x - b.w), Math.abs(b.x - r.x - r.w)) < 8 * F : Math.abs(r.x + r.w / 2 - (b.x + b.w / 2)) < r.w / 2 + 8 * F;
      [e.say.want, e.tailFor, e.tailUp, e.side] = [1, close ? e.say : null, r.up, r.side];
    }
    // the box speaks from where it stands
    if (this.box) {
      const k = this.box.card, [x, y] = boxAt ?? [W / 2, H / 2], b = { x: x - 6 * F, y: y - 10 * F, w: 12 * F, h: 12 * F }, r = spot(b, k.w, k.h, true);
      k.want = r ? 1 : 0;
      this.box.tail.visible = !!r && !!boxAt && !r.side && Math.abs(r.x + r.w / 2 - x) < r.w / 2 && Math.min(Math.abs(r.y + r.h - b.y), Math.abs(r.y - b.y - b.h)) < 10 * F;   // only when it is right by the box
      if (r) {
        k.s.position.set(r.x, r.y);
        placed.push({ ...r, kind: "bubble" });
        this.box.tail.scale.set(F, r.up ? -F : F);
        this.box.tail.position.set(Math.round(clamp(x - 3 * F, r.x + 2 * F, r.x + r.w - 9 * F)), r.up ? r.y + F : r.y + r.h - F);
      }
    }
    // thoughts: whoever is chosen first, the rest in turn, so that in a crowd each gets its time in full
    const turn = Math.floor(now / 5000), thinkers = list.filter((e) => !e.who.say);
    const order = [...thinkers].sort((a, b) => Number(b.who.selected) - Number(a.who.selected) || ((thinkers.indexOf(a) + turn) % thinkers.length) - ((thinkers.indexOf(b) + turn) % thinkers.length));
    for (const e of list) if (e.who.say) e.cap.want = e.dots.want = 0;
    for (const e of order) {
      const b = heads.get(e.who.id)!, has = !!e.who.caption;
      const full = has ? spot(b, e.cap.w, e.cap.h, false) : null;
      const small = !full && (has || e.who.thinking) ? spot(b, e.dots.w, e.dots.h, false) : null;
      [e.cap.want, e.dots.want] = [full ? 1 : 0, small ? 1 : 0];
      if (full) put(e.cap, b, full, "caption");
      if (small) put(e.dots, b, small, "caption");
      const r = full ?? small;
      if (r) [e.tailFor, e.tailUp, e.side] = [full ? e.cap : e.dots, r.up, r.side];
    }
    this.placed = placed;
  }
}
