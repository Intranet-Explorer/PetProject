// Words over the room (SPEC-v3.2 §5.3): each pet's name plate in its family's colour, a thought caption with what it
// means to do, speech bubbles, the face that shows how it feels, what the box says. Lettering is the room's pixel face
// at a finer scale than the art, so it stays readable. Whose a bubble is must never be in doubt: its tail runs all the
// way to its owner, it carries its owner's name in the plate's colour when there is more than one pet, and it is never
// put nearer to another pet than to its own. Nothing here may cover a pet's body or another bubble, and all of it stays
// inside the room. When the room is crowded the captions that do not fit shrink to three dots and take turns.
import { Container, Graphics, Sprite, Texture } from "pixi.js";
import { canvasOf, def, fromCanvas } from "./assets";
import { draw, LINE, measure, plain, wrap } from "./font";
import { clamp, hit, seeded } from "./geom";
import type { Rect } from "./geom";

export type Label = Rect & { kind: string };
/** What the room wants said about one pet. `caption`: its intention, or null. `say`: its words, with whom they are for. */
/** `mood`: the strong feeling to show as a face by its head (not while it sleeps). `tab`: its name goes on its bubbles (there are others here). */
export type Who = { id: string; name: string; family: number; selected: boolean; faded: boolean; caption: string | null; thinking: boolean;
  say: { key: string; text: string; to: string | null; song: boolean } | null; mood: string | null; tab: boolean };

/** A short plain name for a thing in the room, shown for a moment when the room comes into view (or held on).
 *  `rect`: the thing on screen (kept up to date by the room). `pri`: lower is kept first when there is no room for all.
 *  `always`: it stays, faintly, when the others have gone (a memorial stone). */
export type Tag = { key: string; text: string; rect: Rect; pri: number; always?: boolean; until?: number };   // `until`: it shows until then whatever else (a newcomer's "just hatched")

const INK = "#2b2233", PAPER = "#fffdf2", ACCENT = "#ffb347";
export const FAMILY: Record<number, string> = { 1: "#1f7a8c", 2: "#a8468a" };   // each family's colour (SPEC-v3.1 §7.4); the page's style has the same two

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
/** `tab`: the owner's name on a small plate of its colour, set into the bubble's top edge. */
function tagCanvas(text: string) {
  const t = plain(text), [c, x] = canvas(measure(t) + 6, 11);
  frame(x, c.width, c.height, "#2b2233", "#2b2233");
  draw(x, [t], 3, 1, { color: "#f4f0e0" });
  return c;
}
function bubbleCanvas(lines: string[], o: { fill: string; ink: string; text: string; head?: string; headColor?: string; static?: string; art?: string; tab?: { name: string; color: string } }) {
  const head = o.head ? plain(o.head) : null, art = o.art && def(o.art)?.slice ? o.art : null, px = art ? 6 : 4, tab = o.tab ? plateCanvas(o.tab.name, o.tab.color, false) : null;
  const top = tab ? 7 : 0, py = (art ? 4 : 3) + (tab ? 2 : 0);
  const w = Math.max(...lines.map(measure), head ? measure(head) : 0, o.static != null ? 46 : 0, tab ? tab.width - 2 : 0) + 2 * px;
  const rows = lines.length + (head ? 1 : 0) + (o.static != null ? 1 : 0), high = rows * LINE + 2 * py - 1 + (art ? 1 : 0) - (tab ? 2 : 0), [c, x] = canvas(w, top + high);
  x.translate(0, top);
  if (!art || !nine(x, art, c.width, high)) frame(x, c.width, high, o.fill, o.ink);
  if (tab) x.drawImage(tab, 5, -top);
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
/** The colour inside a bubble of the art's, for the tail that runs from it. */
const fills = new Map<string, number>();
function fillOf(art: string, or: number) {
  if (!fills.has(art)) {
    const d = def(art), c = d ? canvasOf(art) : null, p = c?.getContext("2d")!.getImageData(c.width >> 1, c.height >> 1, 1, 1).data;
    fills.set(art, p && p[3] ? (p[0] << 16) | (p[1] << 8) | p[2] : or);
  }
  return fills.get(art)!;
}
/** A face from the art with a dark edge round it, so it shows on any floor by day or night. */
const faces = new Map<string, Texture>();
function faceTexture(mood: string) {
  let t = faces.get(mood);
  if (t) return t;
  const src = canvasOf(`emote.${mood}`), [c, x] = canvas(src.width + 2, src.height + 2);
  for (const [dx, dy] of [[0, 1], [2, 1], [1, 0], [1, 2], [0, 0], [2, 0], [0, 2], [2, 2]]) x.drawImage(src, dx, dy);
  x.globalCompositeOperation = "source-in";
  x.fillStyle = INK;
  x.fillRect(0, 0, c.width, c.height);
  x.globalCompositeOperation = "source-over";
  x.drawImage(src, 1, 1);
  faces.set(mood, (t = fromCanvas(c)));
  return t;
}
const gap = (a: Rect, b: Rect) => Math.hypot(Math.max(0, a.x - b.x - b.w, b.x - a.x - a.w), Math.max(0, a.y - b.y - b.h, b.y - a.y - a.h));

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
type Entry = { who: Who; plate: Card; cap: Card; dots: Card; say: Card; link: Graphics; linkFor: Card | null; mood: Sprite; face: Rect; nub: Graphics; word: Card; wordUntil: number };
type Body = Rect & { id: string };

export class Labels {
  c = new Container();
  placed: Label[] = [];
  private links = new Container();   // tails, under the bubbles they come from
  private cards = new Container();
  private entries = new Map<string, Entry>();
  private box: { card: Card; link: Graphics; key: string } | null = null;
  private tip: { card: Card; at: number[] } | null = null;
  private tags = new Map<string, { tag: Tag; card: Card; fits: boolean; lead: Graphics }>();
  /** Are the things' names showing just now (the room says so every frame). */
  naming = false;
  /** Places on screen that plates, bubbles and faces keep off (memorial stones). */
  keepOff: Rect[] = [];
  /** The things in the room, on screen: a face by a pet's head sits over bare floor where it can, not on one of these. */
  things: Rect[] = [];
  private F = 2;
  private laid = -1e9;

  constructor() {
    this.c.addChild(this.links, this.cards);
  }

  /** What to say about whom, from a snapshot. `F`: screen pixels to a pixel of lettering. `wide`: the room's width in lettering pixels. */
  sync(who: Who[], radio: { key: string; text: string; source: string } | null, F: number, wide: number) {
    this.F = F;
    for (const [id, e] of this.entries) if (!who.some((w) => w.id === id)) {
      for (const k of [e.plate, e.cap, e.dots, e.say]) k.destroy();
      e.link.destroy();
      e.nub.destroy();
      e.word.destroy();
      e.mood.destroy();
      this.entries.delete(id);
    }
    for (const w of who) {
      let e = this.entries.get(w.id);
      if (!e) {
        e = { who: { ...w, mood: null }, plate: new Card(), cap: new Card(), dots: new Card(), say: new Card(), link: new Graphics(), linkFor: null, mood: new Sprite(), face: { x: 0, y: 0, w: 0, h: 0 }, nub: new Graphics(), word: new Card(), wordUntil: 0 };
        this.cards.addChild(e.word.s);
        this.entries.set(w.id, e);
        this.cards.addChild(e.mood, e.plate.s, e.dots.s, e.cap.s, e.say.s);
        this.links.addChild(e.link, e.nub);
        e.dots.set("dots" + F, F, dotsCanvas);
      }
      if (w.mood && w.mood !== e.who.mood) {   // a sign that has just appeared says in a word what it means, for a few seconds
        e.word.set(w.mood + F, F, () => { const t = plain(w.mood!), [c, x] = canvas(measure(t) + 6, 11); frame(x, c.width, c.height, PAPER, INK); draw(x, [t], 3, 1, { color: INK }); return c; });
        e.wordUntil = performance.now() + 6000;
      }
      e.who = w;
      const color = w.faded ? "#6d6875" : FAMILY[w.family] ?? FAMILY[1], tab = w.tab ? { name: w.name, color } : undefined;
      e.plate.set(`${w.name}|${w.family}|${w.selected}|${w.faded}|${F}`, F, () => plateCanvas(w.name, color, w.selected));
      e.plate.want = 1;
      if (w.caption) e.cap.set(`${w.caption}|${F}|${wide}|${w.tab && w.name}`, F, () => bubbleCanvas(wrap(w.caption!, Math.round(wide * 0.32), 2), { fill: PAPER, ink: INK, text: "#3a3350", art: "ui.bubble.think", tab }));
      if (w.say) {
        const s = w.say, text = s.song ? `♪ ${s.text} ♪` : s.text;
        e.say.set(`${s.key}|${F}|${wide}|${w.tab && w.name}`, F, () => bubbleCanvas(wrap(text, Math.round(wide * 0.3), 3), { fill: "#ffffff", ink: INK, text: INK, head: s.to ? `→ ${s.to}` : undefined, headColor: "#b3541e", art: "ui.bubble.say", tab }));
      }
      if (w.mood) e.mood.texture = faceTexture(w.mood);
      else e.mood.visible = false;
    }
    if (radio?.key !== this.box?.key) {
      this.box?.card.destroy();
      this.box?.link.destroy();
      this.box = null;
      if (radio) {
        const card = new Card(), link = new Graphics();
        card.set(radio.key + F, F, () => bubbleCanvas(radio.text ? wrap(`"${radio.text}"`, Math.round(wide * 0.34), 3) : ["only static"],
          { fill: "#fbf0cf", ink: "#7a4a1e", text: radio.text ? INK : "#6b5a48", head: radio.text ? `the box - ${radio.source}` : "the box", headColor: "#7a4a1e", static: radio.text ? undefined : radio.key }));
        card.want = 1;
        this.cards.addChild(card.s);
        this.links.addChild(link);
        this.box = { card, link, key: radio.key };
      }
    }
    this.laid = -1e9;
  }

  /** The names of the things in the room (see Tag). Call again whenever the set of things changes. */
  name(list: Tag[]) {
    for (const [key, t] of this.tags) if (!list.some((n) => n.key === key)) { t.card.destroy(); t.lead.destroy(); this.tags.delete(key); }
    for (const tag of list) {
      let t = this.tags.get(tag.key);
      if (!t) { this.tags.set(tag.key, (t = { tag, card: new Card(), fits: false, lead: new Graphics() })); this.cards.addChildAt(t.card.s, 0); this.links.addChild(t.lead); }
      t.tag = tag;
      t.card.set(tag.text + this.F, this.F, () => tagCanvas(tag.text));
    }
    this.laid = -1e9;
  }

  /** A small plate for what the pointer is on (a creature's name), at a point on screen; null takes it away. */
  hover(text: string | null, x = 0, y = 0) {
    if (!text) { if (this.tip) this.tip.card.want = 0; return; }
    if (!this.tip) { this.tip = { card: new Card(), at: [0, 0] }; this.cards.addChild(this.tip.card.s); }
    this.tip.card.set(text + this.F, this.F, () => plateCanvas(text, "#4a4458", false));
    [this.tip.card.want, this.tip.at] = [1, [x, y]];
  }

  /** Every frame: put each card by its pet (`bodies`: each pet's body on screen), and every so often work out again
   *  where everything goes. `K`: screen pixels to a pixel of the art. `room`: the part of the canvas the room is drawn
   *  in. `avoid`: parts of it the page has covered. `boxAt`: where the box stands. */
  step(now: number, dt: number, bodies: Map<string, Rect>, K: number, room: Rect, avoid: Rect[], boxAt: number[] | null) {
    // the face by its head: to one side or above, wherever it covers nobody (its own body included); if nowhere, its
    // bearing has to say it alone. It nods a little.
    for (const [id, e] of this.entries) {
      const b = bodies.get(id), w = (e.mood.texture.width || 16) * K, h = (e.mood.texture.height || 15) * K, nub = e.nub.clear();
      const said = !!e.who.mood && now < e.wordUntil, extra = said ? e.word.w + this.F : 0, W = w + extra;   // the sign, and for a moment its word beside it
      let left = false;
      e.face.w = 0;
      if (b && e.who.mood) for (const bare of [true, false]) {   // over bare floor if there is such a place; else over a thing rather than not at all
        for (const [x, y, onLeft] of [[b.x + b.w - K, b.y - 7 * K, 0], [b.x + K - W, b.y - 7 * K, 1], [b.x + b.w / 2 - w / 2, b.y - h - K, 0], [b.x + b.w, b.y + b.h - h, 0], [b.x - W, b.y + b.h - h, 1]]) {
          const r = { x, y: Math.max(room.y, y), w: W, h };
          if (r.x < room.x || r.x + W > room.x + room.w || hit(r, { x: b.x + K, y: b.y + K, w: b.w - 2 * K, h: b.h - 2 * K }) || this.keepOff.some((k) => hit(k, r))) continue;
          let free = !bare || !this.things.some((t) => hit(t, r));
          for (const [other, ob] of bodies) if (other !== id && hit(r, ob)) free = false;
          for (const o of this.entries.values()) if (o !== e && o.face.w && hit(r, o.face)) free = false;
          if (free) { [e.face.x, e.face.y, e.face.w, e.face.h, left] = [r.x, r.y, W, h, !!onLeft]; break; }
        }
        if (e.face.w) break;
      }
      const fx0 = e.face.x + (left ? extra : 0);   // where the sign itself is, within the room it and its word take
      e.mood.visible = e.face.w > 0;
      e.mood.scale.set(K);
      e.mood.position.set(Math.round(fx0), Math.round(e.face.y));
      e.word.want = said && e.face.w ? 1 : 0;
      e.word.ease(dt);
      e.word.s.position.set(Math.round(left ? e.face.x : fx0 + w + this.F), Math.round(e.face.y + (h - e.word.h) / 2));
      if (b && e.face.w) {   // a small tail from the sign to the head it belongs to
        const hx = b.x + b.w / 2, hy = b.y + 2 * K, fx = clamp(hx, fx0 + 2 * K, fx0 + w - 2 * K), fy = clamp(hy, e.face.y + 2 * K, e.face.y + h - K);
        for (const k of [0.45, 0.8]) nub.rect(Math.round((fx + (hx - fx) * k) / K) * K - K, Math.round((fy + (hy - fy) * k) / K) * K - K, 2 * K, 2 * K);
        nub.fill(0x2b2233);
      }
    }
    if (now - this.laid > 140) {
      this.laid = now;
      this.lay(now, bodies, room, avoid, boxAt);
    }
    for (const [id, e] of this.entries) {
      const b = bodies.get(id);
      if (!b) continue;
      const cx = b.x + b.w / 2;
      for (const k of [e.plate, e.cap, e.dots, e.say]) {
        k.ease(dt);
        k.s.position.set(Math.round(clamp(cx + k.dx, room.x, Math.max(room.x, room.x + room.w - k.w))), Math.round(clamp(b.y + k.dy, room.y, Math.max(room.y, room.y + room.h - k.h))));
      }
      const t = e.linkFor, g = e.link.clear();
      if (t && t.alpha > 0.5) this.tail(g, { x: t.s.x, y: t.s.y, w: t.w, h: t.h }, b, t === e.say, t === e.say ? fillOf("ui.bubble.say", 0xffffff) : fillOf("ui.bubble.think", 0xfffdf2));
    }
    if (this.box) {
      const k = this.box.card, g = this.box.link.clear();
      k.ease(dt);
      if (boxAt && k.alpha > 0.5) this.tail(g, { x: k.s.x, y: k.s.y, w: k.w, h: k.h }, { x: boxAt[0] - 5 * K, y: boxAt[1] - 6 * K, w: 10 * K, h: 10 * K }, true, 0xfbf0cf);
    }
    for (const t of this.tags.values()) {   // names: on for a moment, or held; a stone keeps its own, faintly
      const k = t.card, r = t.tag.rect;
      k.want = !t.fits ? 0 : this.naming || now < (t.tag.until ?? 0) ? 1 : t.tag.always ? 0.72 : 0;
      k.ease(dt);
      k.s.position.set(Math.round(clamp(r.x + r.w / 2 + k.dx, room.x, Math.max(room.x, room.x + room.w - k.w))), Math.round(clamp(r.y + k.dy, room.y, Math.max(room.y, room.y + room.h - k.h))));
      const lead = t.lead.clear(), at = { x: k.s.x, y: k.s.y, w: k.w, h: k.h };
      if (k.alpha > 0.3 && gap(at, r) > 3 * this.F) {   // set a little way off: a thin line back to the thing it names
        const F = this.F, tx = clamp(at.x + at.w / 2, r.x + r.w * 0.25, r.x + r.w * 0.75), ty = clamp(at.y + at.h / 2, r.y + r.h * 0.25, r.y + r.h * 0.75), ax = clamp(tx, at.x, at.x + at.w), ay = clamp(ty, at.y, at.y + at.h);
        for (let i = 0, n = Math.max(1, Math.ceil(Math.hypot(tx - ax, ty - ay) / F)); i <= n; i++) lead.rect(Math.round((ax + ((tx - ax) * i) / n) / F) * F, Math.round((ay + ((ty - ay) * i) / n) / F) * F, F, F);
        lead.fill({ color: 0x2b2233, alpha: k.alpha });
      }
    }
    if (this.tip) {
      const k = this.tip.card;
      k.ease(dt);
      k.s.position.set(Math.round(clamp(this.tip.at[0] - k.w / 2, room.x, room.x + room.w - k.w)), Math.round(clamp(this.tip.at[1], room.y, room.y + room.h - k.h)));
    }
  }

  /** A bubble's tail, all the way to its owner: a wedge for speech, a string of dots for a thought, in lettering pixels. */
  private tail(g: Graphics, r: Rect, b: Rect, speech: boolean, fill: number) {
    const F = this.F, snap = (v: number) => Math.round(v / F) * F;
    const tx = clamp(r.x + r.w / 2, b.x + b.w * 0.3, b.x + b.w * 0.7), ty = clamp(r.y + r.h / 2, b.y + 2 * F, b.y + b.h - 2 * F);   // a point on the owner
    const ax = clamp(tx, r.x + 6 * F, r.x + r.w - 6 * F), ay = clamp(ty, r.y + 4 * F, r.y + r.h - 4 * F);                           // and one just inside the bubble
    const d = Math.hypot(tx - ax, ty - ay);
    if (d < 5 * F) return;
    const blocks: number[] = [];   // x, y, half a side
    if (speech) for (let i = 0, n = Math.ceil(d / F); i <= n; i++) blocks.push(snap(ax + ((tx - ax) * i) / n), snap(ay + ((ty - ay) * i) / n), Math.max(F / 2, (3 - (2.5 * i) / n) * F));
    else for (let k0 = Math.min(0.6, (7 * F) / d), m = Math.max(2, Math.round((d * (1 - k0)) / (7 * F))), j = 0; j < m; j++) {
      const k = k0 + ((1 - k0) * (j + 0.5)) / m;
      blocks.push(snap(ax + (tx - ax) * k), snap(ay + (ty - ay) * k), j < m / 2 ? 1.5 * F : F);
    }
    for (let i = 0; i < blocks.length; i += 3) g.rect(blocks[i] - blocks[i + 2] - F, blocks[i + 1] - blocks[i + 2] - F, 2 * blocks[i + 2] + 2 * F, 2 * blocks[i + 2] + 2 * F);
    g.fill(0x2b2233);
    for (let i = 0; i < blocks.length; i += 3) g.rect(blocks[i] - blocks[i + 2], blocks[i + 1] - blocks[i + 2], 2 * blocks[i + 2], 2 * blocks[i + 2]);
    g.fill(fill);
  }

  /** Decide where everything goes (§10.7): no plate, caption or bubble on another or on anybody's body or face, all of
   *  it inside the room, and no bubble nearer to another pet than to its own. */
  private lay(now: number, bodies: Map<string, Rect>, room: Rect, avoid: Rect[], boxAt: number[] | null) {
    const F = this.F, placed: Label[] = avoid.map((r) => ({ ...r, kind: "page" }));
    const list = [...this.entries.values()].filter((e) => bodies.has(e.who.id)).sort((a, b) => bodies.get(a.who.id)!.y - bodies.get(b.who.id)!.y);
    const solid: Body[] = list.flatMap((e) => [{ ...bodies.get(e.who.id)!, id: e.who.id }, ...(e.face.w ? [{ ...e.face, id: e.who.id }] : [])]);   // bodies, and the faces by their heads
    const inside = (r: Rect) => r.x >= room.x && r.y >= room.y && r.x + r.w <= room.x + room.w && r.y + r.h <= room.y + room.h;
    const clear = (r: Rect) => inside(r) && !placed.some((q) => hit(q, r)) && !solid.some((f) => hit(f, r)) && !this.keepOff.some((k) => hit(k, r));
    const plates = new Map<string, Rect>();
    /** Is this place plainly its owner's: no other pet's body is nearer to it. */
    const own = (r: Rect, id: string) => { const mine = gap(r, bodies.get(id)!); return !list.some((e) => e.who.id !== id && gap(r, bodies.get(e.who.id)!) < mine * 0.75 - F); };
    const put = (k: Card, b: Rect, r: Rect, kind: string) => {
      [k.dx, k.dy] = [r.x - (b.x + b.w / 2), r.y - b.y];
      placed.push({ ...r, kind });
    };
    // a tail runs from its bubble to its owner: it may not cross another pet or pass under another bubble, or it would seem to be theirs
    const ropes: Body[] = [];
    const rope = (r: Rect, b: Rect): Rect => {
      const tx = clamp(r.x + r.w / 2, b.x + b.w * 0.3, b.x + b.w * 0.7), ty = clamp(r.y + r.h / 2, b.y + 2 * F, b.y + b.h - 2 * F), ax = clamp(tx, r.x, r.x + r.w), ay = clamp(ty, r.y, r.y + r.h);
      return { x: Math.min(ax, tx) - 2 * F, y: Math.min(ay, ty) - 2 * F, w: Math.abs(ax - tx) + 4 * F, h: Math.abs(ay - ty) + 4 * F };
    };
    const reach = (r: Rect, b: Rect, id: string) => {
      const line = rope(r, b);
      const mine = this.entries.get(id)?.who.tab ? plates.get(id) : null;   // a bubble that carries its owner's name is not stacked right against the name plate
      if (mine && hit({ x: mine.x - 2 * F, y: mine.y - 6 * F, w: mine.w + 4 * F, h: mine.h + 12 * F }, r)) return false;
      return !ropes.some((q) => q.id !== id && hit(q, r)) && !placed.some((q) => (q.kind === "bubble" || q.kind === "caption") && hit(q, line)) && !solid.some((f) => f.id !== id && hit(f, line));
    };
    const fitter = (w: number, h: number) => (x: number, y: number) => ({ x: Math.round(clamp(x, room.x, room.x + room.w - w)), y: Math.round(clamp(y, room.y, room.y + room.h - h)), w, h });
    // name plates: under the feet; else over the head, to a side, or further off; never on a body, its own included
    const shared = (a: Rect, b: Rect) => Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
    for (const e of list) {
      const b = bodies.get(e.who.id)!, { w, h } = e.plate, cx = b.x + b.w / 2, under = b.y + b.h + F, over = b.y - h - F, fit = fitter(w, h);
      const tries = [fit(cx - w / 2, under), fit(cx - w / 2, over), fit(cx - w, under), fit(cx, under), fit(cx - w, over), fit(cx, over), fit(b.x - w - F, b.y + b.h - h), fit(b.x + b.w + F, b.y + b.h - h),
                     fit(cx - w / 2, under + h + F), fit(cx - w / 2, over - h - F), fit(b.x - w - F, b.y), fit(b.x + b.w + F, b.y), fit(cx - w / 2, under + 2 * (h + F)), fit(cx - w / 2, over - 2 * (h + F))];
      const cost = (r: Rect) => placed.reduce((n, q) => n + shared(q, r) * 3, 0) + solid.reduce((n, f) => n + shared(f, r) * 2, 0) + gap(r, b);
      let at = tries.find((r) => clear(r)) ?? null;
      if (!at) for (let gy = 0, far = Infinity; gy < 10; gy++) for (let gx = 0; gx < 10; gx++) {   // nowhere near: the nearest clear place in the room (two plates never lie on each other)
        const r = fit(room.x + (gx / 9) * (room.w - w), room.y + (gy / 9) * (room.h - h)), d = gap(r, b);
        if (d < far && clear(r)) [at, far] = [r, d];
      }
      at ??= tries.reduce((best, r) => (cost(r) < cost(best) ? r : best));
      put(e.plate, b, at, "pet");
      plates.set(e.who.id, at);
    }
    /** The clear spot for a bubble nearest its owner: over it, to a side, higher, under its plate; `anywhere`: failing those, wherever in the room is clear. */
    const spot = (b: Rect, w: number, h: number, id: string, anywhere: boolean): Rect | null => {
      const cx = b.x + b.w / 2, g = 5 * F, over = b.y - g - h, fit = fitter(w, h);
      const tries = [fit(cx - w / 2, over), fit(cx - w * 0.25, over), fit(cx - w * 0.75, over), fit(b.x - g - w, b.y - h / 2), fit(b.x + b.w + g, b.y - h / 2), fit(b.x - g - w, b.y - h), fit(b.x + b.w + g, b.y - h),
                     fit(cx - w / 2, over - h - F), fit(cx - w * 0.2, over - h - F), fit(cx - w * 0.8, over - h - F), fit(b.x - g - w, b.y + b.h - h), fit(b.x + b.w + g, b.y + b.h - h), fit(cx - w / 2, over - 2 * (h + F)),
                     fit(cx - w / 2, b.y + b.h + 14 * F), fit(cx - w * 0.25, b.y + b.h + 14 * F), fit(cx - w * 0.75, b.y + b.h + 14 * F)];
      const near = tries.find((r) => clear(r) && (!id || (own(r, id) && reach(r, b, id))));
      if (near || !anywhere) return near ?? null;
      let best: Rect | null = null, far = Infinity;   // wherever is clear: its owner's side of the room first
      for (const strict of [true, false]) {
        for (let gy = 0; gy < 8; gy++) for (let gx = 0; gx < 8; gx++) {
          const r = fit(room.x + (gx / 7) * (room.w - w), room.y + (gy / 7) * (room.h - h)), d = gap(r, b);
          if (d < far && clear(r) && (!strict || !id || (own(r, id) && reach(r, b, id)))) [best, far] = [r, d];
        }
        if (best) break;
      }
      return best;
    };
    /** A caption that found no room by its owner may sit a little way off, if it is still plainly its owner's (its tail and its name say so). */
    const far = (b: Rect, w: number, h: number, id: string): Rect | null => {
      const r = spot(b, w, h, id, true);
      return r && own(r, id) && gap(r, b) < 40 * F ? r : null;
    };
    for (const e of list) {   // speech first: it is the thing most worth reading, and it does not last
      const b = bodies.get(e.who.id)!;
      e.linkFor = null;
      e.say.want = 0;
      if (!e.who.say) continue;
      const r = spot(b, e.say.w, e.say.h, e.who.id, true);
      if (!r) continue;
      put(e.say, b, r, "bubble");
      ropes.push({ ...rope(r, b), id: e.who.id });
      [e.say.want, e.linkFor] = [1, e.say];
    }
    // the box speaks from where it stands
    if (this.box) {
      const k = this.box.card, [x, y] = boxAt ?? [room.x + room.w / 2, room.y + room.h / 2], r = spot({ x: x - 6 * F, y: y - 10 * F, w: 12 * F, h: 12 * F }, k.w, k.h, "", true);
      k.want = r ? 1 : 0;
      if (r) { k.s.position.set(r.x, r.y); placed.push({ ...r, kind: "bubble" }); }
    }
    // thoughts: whoever is chosen first, the rest in turn, so that in a crowd each gets its time in full
    const turn = Math.floor(now / 5000), thinkers = list.filter((e) => !e.who.say);
    const order = [...thinkers].sort((a, b) => Number(b.who.selected) - Number(a.who.selected) || ((thinkers.indexOf(a) + turn) % thinkers.length) - ((thinkers.indexOf(b) + turn) % thinkers.length));
    for (const e of list) if (e.who.say) e.cap.want = e.dots.want = 0;
    for (const e of order) {
      const b = bodies.get(e.who.id)!, has = !!e.who.caption;
      const full = has ? spot(b, e.cap.w, e.cap.h, e.who.id, false) ?? far(b, e.cap.w, e.cap.h, e.who.id) : null;
      const small = !full && (has || e.who.thinking) ? spot(b, e.dots.w, e.dots.h, e.who.id, false) : null;
      [e.cap.want, e.dots.want] = [full ? 1 : 0, small ? 1 : 0];
      if (full) put(e.cap, b, full, "caption");
      if (small) put(e.dots, b, small, "caption");
      if (full ?? small) ropes.push({ ...rope((full ?? small)!, b), id: e.who.id });
      e.linkFor = full ? e.cap : small ? e.dots : null;
    }
    // the names of things, the most worth knowing first; what finds no clear place by its thing goes without
    // Each sits on bare floor or wall by its own thing, never on another thing or another name; in a cluster it goes to
    // the nearest clear spot and a thin line ties it back. What finds no place goes without, the least important first.
    const others = [...this.tags.values()].map((t) => t.tag.rect), now2 = performance.now();
    for (const t of [...this.tags.values()].sort((a, b) => a.tag.pri - b.tag.pri)) {
      t.fits = false;
      if (!this.naming && !t.tag.always && now2 >= (t.tag.until ?? 0)) continue;
      const r = t.tag.rect, { w, h } = t.card, cx = r.x + r.w / 2, fit = fitter(w, h);
      const free = (q: Rect) => inside(q) && !placed.some((p) => hit(p, q)) && !solid.some((f) => hit(f, q)) && !others.some((o) => o !== r && hit(o, q)) && !this.things.some((o) => hit(o, q) && !hit(o, { x: r.x + 1, y: r.y + 1, w: r.w - 2, h: r.h - 2 }));
      let at: Rect | null = null;
      for (let ring = 0; ring < 5 && !at; ring++) {   // by the thing first, then further out
        const dx = ring * (h + 2 * F), dy = ring * (h + F);
        at = [fit(cx - w / 2, r.y + r.h + F + dy), fit(cx - w / 2, r.y - h - F - dy), fit(r.x + r.w + F + dx, r.y + r.h - h), fit(r.x - w - F - dx, r.y + r.h - h), fit(r.x + r.w + F + dx, r.y - dy), fit(r.x - w - F - dx, r.y - dy),
              fit(r.x + r.w + F + dx, r.y + r.h + dy), fit(r.x - w - F - dx, r.y + r.h + dy), fit(r.x, r.y + r.h + F + dy), fit(r.x + r.w - w, r.y - h - F - dy)].find(free) ?? null;
      }
      if (!at) continue;
      t.fits = true;
      [t.card.dx, t.card.dy] = [at.x - cx, at.y - r.y];
      placed.push({ ...at, kind: "name" });
    }
    this.placed = placed;
  }
}
