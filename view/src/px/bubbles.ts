// Words over the room (SPEC-v3.4 §5): over each pet's head one line, the sign of what it is doing and its name in its
// family's colour. What it wants comes up over that line for six seconds when it changes, and while the pointer is on
// the pet; a speech bubble only for words said (and for what the box says). Lettering is the room's pixel face at a
// finer scale than the art, so it stays readable. Everything has one place and keeps it: nothing hunts for room. Where
// two would lie on each other the later one waits its turn (a name line is simply not drawn meanwhile).
import { Container, Graphics, Sprite, Texture } from "pixi.js";
import { canvasOf, def, fromCanvas, has } from "./assets";
import { draw, LINE, measure, plain, wrap } from "./font";
import { clamp, hit, inside, seeded } from "./geom";
import type { Rect } from "./geom";

export type Label = Rect & { kind: string };
/** What the room wants said about one pet. `caption`: what it wants, or null. `say`: its words, with whom they are for.
 *  `icon`: the sign of what it is doing (sprite icon.act.<name>; "" when the art has none for it), null for one that
 *  is doing nothing to speak of (asleep, an egg, dead). `thinking`: its mind is at work: three dots in the sign's place. */
export type Who = { id: string; name: string; family: number; selected: boolean; faded: boolean; caption: string | null; thinking: boolean;
  say: { key: string; text: string; to: string | null; song: boolean } | null; icon: string | null };

/** A short plain name for a thing in the room, shown while the pointer is on it (or while names are held on).
 *  `rect`: the thing on screen (kept up to date by the room). `pri`: lower is kept first when there is no room for all.
 *  Names show while they are held on, and each while the pointer is on its thing; otherwise they are gone. */
export type Tag = { key: string; text: string; rect: Rect; pri: number; until?: number };   // `until`: it shows until then whatever else (a newcomer's "just hatched")

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
/** A pet's one line: a name plate with, at its head, the sign of what the pet is doing (three dots while it thinks). */
function lineCanvas(name: string, color: string, ring: boolean, icon: string | null, thinking: boolean) {
  if (icon == null) return plateCanvas(name, color, ring);
  const text = plain(name), S = 12, [c, x] = canvas(S + measure(text) + 6, 12), art = has(`icon.act.${icon}`) ? canvasOf(`icon.act.${icon}`) : dot();
  frame(x, c.width, c.height, color, ring ? ACCENT : INK);
  frame(x, S + 1, c.height, PAPER, ring ? ACCENT : INK);
  if (thinking) { x.fillStyle = INK; for (const i of [3, 6, 9]) x.fillRect(i, 5, 1, 2); }
  else x.drawImage(art, Math.round((S + 1 - art.width) / 2), Math.round((c.height - art.height) / 2));
  draw(x, [text], S + 3, 2, { color: "#ffffff" });
  return c;
}
export function tagCanvas(text: string) {
  const t = plain(text), [c, x] = canvas(measure(t) + 6, 11);
  frame(x, c.width, c.height, "#2b2233", "#2b2233");
  draw(x, [t], 3, 1, { color: "#f4f0e0" });
  return c;
}
function bubbleCanvas(lines: string[], o: { fill: string; ink: string; text: string; head?: string; headColor?: string; static?: string; art?: string }) {
  const head = o.head ? plain(o.head) : null, art = o.art && def(o.art)?.slice ? o.art : null, px = art ? 6 : 4, py = art ? 4 : 3;
  const w = Math.max(...lines.map(measure), head ? measure(head) : 0, o.static != null ? 46 : 0) + 2 * px;
  const rows = lines.length + (head ? 1 : 0) + (o.static != null ? 1 : 0), high = rows * LINE + 2 * py - 1 + (art ? 1 : 0), [c, x] = canvas(w, high);
  if (!art || !nine(x, art, c.width, high)) frame(x, c.width, high, o.fill, o.ink);
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
/** The colour inside a bubble of the art's, for the tail that runs from it. */
const fills = new Map<string, number>();
function fillOf(art: string, or: number) {
  if (!fills.has(art)) {
    const d = def(art), c = d ? canvasOf(art) : null, p = c?.getContext("2d")!.getImageData(c.width >> 1, c.height >> 1, 1, 1).data;
    fills.set(art, p && p[3] ? (p[0] << 16) | (p[1] << 8) | p[2] : or);
  }
  return fills.get(art)!;
}
/** The sign for a thing a body does when the art has none: a small plain dot. */
function dot() {
  const [c, x] = canvas(7, 7);
  x.fillStyle = INK;
  x.fillRect(2, 2, 3, 3);
  return c;
}
const gap = (a: Rect, b: Rect) => Math.hypot(Math.max(0, a.x - b.x - b.w, b.x - a.x - a.w), Math.max(0, a.y - b.y - b.h, b.y - a.y - a.h));

/** One piece of lettering as a sprite; its texture is made again only when what it says changes. */
class Card {
  s = new Sprite();
  w = 0;
  h = 0;
  alpha = 0;        // eased toward `want` every frame
  want = 0;
  dx = 0;           // where a thing's name sits, from the top middle of its thing
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
/** A pet's words: its line, its caption, its bubble and the tail from whichever is up. `under`: that one came up under its
 *  feet. `capAsk`: when what it wants last changed (0: nothing to show), `capUntil`: when its six seconds end (0: not up
 *  yet). `sayOn`: it has words to show; asked for at `sayAsk`, up until `sayUntil` (0: not up yet) for at least `read` ms. */
type Entry = { who: Who; line: Card; cap: Card; say: Card; link: Graphics; under: boolean; capAsk: number; capUntil: number;
  sayKey: string; sayOn: boolean; sayAsk: number; sayUntil: number; read: number };
const GAP = 4;   // lettering pixels between a line and the bubble over it: its tail shows there

export class Labels {
  c = new Container();
  placed: Label[] = [];
  private links = new Container();   // tails, under the bubbles they come from
  private cards = new Container();
  private entries = new Map<string, Entry>();
  private box: { card: Card; link: Graphics; key: string; read: number } | null = null;   // `read`: until then its words are new
  private tip: { card: Card; at: number[] } | null = null;
  private tags = new Map<string, { tag: Tag; card: Card; fits: boolean; lead: Graphics }>();
  /** Are the things' names showing just now (the room says so every frame). */
  naming = false;
  /** Where the pointer is on screen, or null: the name of the thing under it shows. */
  pointer: number[] | null = null;
  /** The things in the room, on screen: a thing's name sits over bare floor where it can, not on one of these. */
  things: Rect[] = [];
  private F = 2;
  private laid = -1e9;

  constructor() {
    this.c.addChild(this.links, this.cards);
  }

  /** What to say about whom, from a snapshot. `F`: screen pixels to a pixel of lettering. `wide`: the room's width in lettering pixels. */
  sync(who: Who[], radio: { key: string; text: string; source: string } | null, F: number, wide: number) {
    this.F = F;
    const now = performance.now();
    for (const [id, e] of this.entries) if (!who.some((w) => w.id === id)) {
      for (const k of [e.line, e.cap, e.say]) k.destroy();
      e.link.destroy();
      this.entries.delete(id);
    }
    for (const w of who) {
      let e = this.entries.get(w.id);
      if (!e) {   // (one just come into view says nothing of what it wants: only a change does)
        e = { who: w, line: new Card(), cap: new Card(), say: new Card(), link: new Graphics(), under: false, capAsk: 0, capUntil: 0, sayKey: "", sayOn: false, sayAsk: 0, sayUntil: 0, read: 0 };
        this.entries.set(w.id, e);
        this.cards.addChild(e.line.s, e.cap.s, e.say.s);
        this.links.addChild(e.link);
      } else if (w.caption !== e.who.caption) [e.capAsk, e.capUntil] = [w.caption ? now : 0, 0];   // its mind has turned to something else: the caption comes up for six seconds
      e.who = w;
      const color = w.faded ? "#6d6875" : FAMILY[w.family] ?? FAMILY[1];
      e.line.set(`${w.name}|${w.family}|${w.selected}|${w.faded}|${w.icon}|${w.thinking}|${F}`, F, () => lineCanvas(w.name, color, w.selected, w.icon, w.thinking));
      if (w.caption) e.cap.set(`${w.caption}|${F}|${wide}`, F, () => bubbleCanvas(wrap(w.caption!, Math.round(wide * 0.32), 2), { fill: PAPER, ink: INK, text: "#3a3350", art: "ui.bubble.think" }));
      if (w.say) {
        const s = w.say, text = s.song ? `♪ ${s.text} ♪` : s.text;
        // new words: they wait their turn if they must, and are then up long enough to read
        // ponytail: one bubble waiting per pet (its newer words replace older ones); a queue each if words get lost in a crowd
        if (s.key !== e.sayKey) [e.sayKey, e.sayOn, e.sayAsk, e.sayUntil, e.read] = [s.key, true, now, 0, clamp(1500 + 60 * text.length, 4000, 8000)];
        e.say.set(`${s.key}|${F}|${wide}`, F, () => bubbleCanvas(wrap(text, Math.round(wide * 0.3), 3), { fill: "#ffffff", ink: INK, text: INK, head: s.to ? `→ ${s.to}` : undefined, headColor: "#b3541e", art: "ui.bubble.say" }));
      }
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
        this.box = { card, link, key: radio.key, read: now + 8000 };
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

  /** Every frame: put each card at its place by its pet (`bodies`: each pet's body on screen), and every so often work
   *  out again which of them show. `K`: screen pixels to a pixel of the art. `room`: the part of the canvas the room is
   *  drawn in. `avoid`: parts of it the page has covered. `boxAt`: where the box stands. */
  step(now: number, dt: number, bodies: Map<string, Rect>, K: number, room: Rect, avoid: Rect[], boxAt: number[] | null) {
    if (now - this.laid > 140) {
      this.laid = now;
      this.lay(now, bodies, room, avoid, boxAt);
    }
    for (const [id, e] of this.entries) {
      const b = bodies.get(id);
      if (!b) continue;
      const line = this.spot(e.line, e, b, room), g = e.link.clear();
      for (const k of [e.line, e.cap, e.say]) {
        const r = k === e.line ? line : this.spot(k, e, b, room);
        k.ease(dt);
        k.s.position.set(r.x, r.y);
        if (k !== e.line && k.want && k.alpha > 0.5) this.tail(g, r, e.under || !e.line.want ? b : line, k === e.say, k === e.say ? fillOf("ui.bubble.say", 0xffffff) : fillOf("ui.bubble.think", 0xfffdf2));
      }
    }
    if (this.box) {
      const k = this.box.card, g = this.box.link.clear();
      k.ease(dt);
      if (boxAt && k.alpha > 0.5) this.tail(g, { x: k.s.x, y: k.s.y, w: k.w, h: k.h }, { x: boxAt[0] - 5 * K, y: boxAt[1] - 6 * K, w: 10 * K, h: 10 * K }, true, 0xfbf0cf);
    }
    for (const t of this.tags.values()) {   // names: on for a moment, or held; a stone keeps its own, faintly
      const k = t.card, r = t.tag.rect;
      k.want = t.fits && this.shown(t.tag, now) ? 1 : 0;
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

  /** The one place each of a pet's cards has: its line just over its head, its caption or bubble over the line (under
   *  its feet, if it came up where the room's edge left no room above). Kept inside the room, and never anywhere else. */
  private spot(k: Card, e: Entry, b: Rect, room: Rect): Rect {
    const F = this.F, top = b.y - e.line.h - F, y = k === e.line ? top : e.under ? b.y + b.h + 2 * F : top - GAP * F - k.h;
    return { x: Math.round(clamp(b.x + b.w / 2 - k.w / 2, room.x, Math.max(room.x, room.x + room.w - k.w))), y: Math.round(clamp(y, room.y, Math.max(room.y, room.y + room.h - k.h))), w: k.w, h: k.h };
  }

  /** Does this name show just now: all of them while held on, each one while the pointer is on its thing. */
  private shown(t: Tag, now: number) {
    const p = this.pointer, r = t.rect;
    return this.naming || now < (t.until ?? 0) || (!!p && inside(r, p[0], p[1]));
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

  /** Decide what shows (SPEC-v3.4 §5). Every card has its one place (`spot`), so the only question is whose turn it is:
   *  a caption or bubble that would lie on one already up waits until that one has gone, and a name line that would lie
   *  on another line or under a bubble is not drawn meanwhile. Nothing moves to make room. */
  private lay(now: number, bodies: Map<string, Rect>, room: Rect, avoid: Rect[], boxAt: number[] | null) {
    const F = this.F, p = this.pointer, placed: Label[] = avoid.map((r) => ({ ...r, kind: "page" })), up: Label[] = [], lines: Label[] = [];
    const list = [...this.entries.values()].filter((e) => bodies.has(e.who.id)), body = (e: Entry) => bodies.get(e.who.id)!, on = (e: Entry) => !!p && inside(body(e), p[0], p[1]);
    const solid = list.map(body);
    const fitter = (w: number, h: number) => (x: number, y: number) => ({ x: Math.round(clamp(x, room.x, room.x + room.w - w)), y: Math.round(clamp(y, room.y, room.y + room.h - h)), w, h });
    // what each pet has to show over its line: its words, else what it wants (just changed, or the pointer is on it)
    const asks: { e: Entry; k: Card; rank: number; since: number }[] = [];
    for (const e of list) {
      const read = e.sayOn && !!e.sayUntil && now > e.sayUntil;                                              // its words have been up long enough to read
      if (read) e.sayOn = false;                                                                             // and then they go, however lately they were said (a song's name used to hang there for a minute)
      if (e.capAsk && (e.capUntil ? now > e.capUntil : now - e.capAsk > 4000)) e.capAsk = e.capUntil = 0;   // it has had its six seconds, or waited too long to be worth showing
      const hov = on(e) && !!e.who.caption, k = e.sayOn ? e.say : hov || e.capAsk ? e.cap : null;
      for (const o of [e.say, e.cap]) if (o !== k) o.want = 0;
      // whose turn: words that are up, the caption the pointer asks for, captions that are up, words waiting, captions waiting, and last words already read; the longest asked first
      if (k) asks.push({ e, k, rank: k === e.say ? (read ? 5 : k.want ? 0 : 3) : hov ? 1 : k.want ? 2 : 4, since: k === e.say ? e.sayAsk : e.capAsk });
    }
    for (const { e, k, rank } of asks.sort((a, b) => a.rank - b.rank || a.since - b.since)) {
      const b = body(e);
      if (!k.want) e.under = b.y - e.line.h - F - GAP * F - k.h < room.y;   // not up yet: which side it comes up on; it keeps that side while it is up
      const r = this.spot(k, e, b, room);
      if (up.some((q) => hit(q, r))) {   // somebody's is there: it waits (words get their whole time when their turn comes; words already read give way for good)
        k.want = 0;
        if (rank === 5) e.sayOn = false;
        else if (k === e.say) e.sayUntil = 0;
        continue;
      }
      k.want = 1;
      if (k === e.say) e.sayUntil ||= now + e.read;
      else if (e.capAsk) e.capUntil ||= now + 6000;
      up.push({ ...r, kind: k === e.say ? "bubble" : "caption" });
    }
    // the box speaks from where it stands, when no pet's words are in the way. Its words stay up a long while: new, they
    // may lie on a name line like anybody's; after that (`late`) only where they cover no name
    const speak = (late: boolean) => {
      const box = this.box;
      if (!box || late !== now > box.read) return;
      const k = box.card, [x, y] = boxAt ?? [room.x + room.w / 2, room.y + room.h / 2], over = y - 15 * F - k.h, r = fitter(k.w, k.h)(x - k.w / 2, over < room.y ? y + 10 * F : over);
      k.want = up.some((q) => hit(q, r)) || (late && lines.some((q) => hit(q, r))) ? 0 : 1;
      k.s.position.set(r.x, r.y);
      if (k.want) up.push({ ...r, kind: "bubble" });
    };
    speak(false);
    // the name lines: where two would lie on each other, or one under a bubble, the lesser is not drawn for now (first
    // whoever has a caption or bubble up, which is plainly its own over its name; then the one pointed at, the one
    // chosen, whoever stands in front)
    const feet = (e: Entry) => body(e).y + body(e).h, words = (e: Entry) => Number(e.cap.want + e.say.want > 0);
    for (const e of [...list].sort((a, b) => words(b) - words(a) || Number(on(b)) - Number(on(a)) || Number(b.who.selected) - Number(a.who.selected) || feet(b) - feet(a) || (a.who.id < b.who.id ? -1 : 1))) {
      const r = this.spot(e.line, e, body(e), room);
      e.line.want = up.some((q) => hit(q, r)) || lines.some((q) => hit(q, r)) ? 0 : 1;
      if (e.line.want) lines.push({ ...r, kind: "pet" });
    }
    speak(true);
    placed.push(...up, ...lines);
    // the names of things, the most worth knowing first; what finds no clear place by its thing goes without
    // Each sits on bare floor or wall by its own thing, never on another thing or another name; in a cluster it goes to
    // the nearest clear spot and a thin line ties it back. What finds no place goes without, the least important first.
    const others = [...this.tags.values()].map((t) => t.tag.rect), now2 = performance.now();
    for (const t of [...this.tags.values()].sort((a, b) => a.tag.pri - b.tag.pri)) {
      t.fits = false;
      if (!this.shown(t.tag, now2)) continue;
      const r = t.tag.rect, { w, h } = t.card, cx = r.x + r.w / 2, fit = fitter(w, h);
      const free = (q: Rect) => q.x >= room.x && q.y >= room.y && q.x + q.w <= room.x + room.w && q.y + q.h <= room.y + room.h && !placed.some((p) => hit(p, q)) && !solid.some((f) => hit(f, q)) && !others.some((o) => o !== r && hit(o, q)) && !this.things.some((o) => hit(o, q) && !hit(o, { x: r.x + 1, y: r.y + 1, w: r.w - 2, h: r.h - 2 }));
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
