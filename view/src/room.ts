// The room (SPEC-v3.2 §1.4, §3 to §5): the one room being looked at, as pixel art drawn from data. The world is the
// engine's; this only draws it. The pieces are in px/ (see px/README.md): the art and its recolouring, the still parts
// of a room, light and weather, the pets and creatures and how they move, the small effects, the lettering.
// Whole pixels only: the 14 x 11 tile canvas is shown at the largest whole-number scale that fits its element.
import { Application, Container, Graphics, Sprite } from "pixi.js";
import type { Genome, Look } from "./pet";
import { petPortrait } from "./petsprite";
import { ago, bodyStage, hhmm, tickMs } from "./types";
import type { Act, Hello, Mark, Obj, PetV, Pond, RoomV, Snap, Tile } from "./types";
import { play } from "./px/acts";
import type { Ghost } from "./px/acts";
import { CreatureActor, doing, PetActor } from "./px/actors";
import type { Stage } from "./px/actors";
import { canvasOf, has, kind, layout, loadArt, pick, size, tex } from "./px/assets";
import type { Layout } from "./px/assets";
import { Labels } from "./px/bubbles";
import { display, fishLine, SKY } from "./px/display";
import type { Display } from "./px/display";
import type { Tag, Who } from "./px/bubbles";
import { Fx, fxTexture } from "./px/fx";
import { Hub } from "./px/hub";
import { loadSeasons } from "./px/season";
import { clamp, FX, FY, H, idx, inside, OX, OY, onFloor, tileAt, TILE, W } from "./px/geom";
import { Marks } from "./px/marks";
import { nearestFree } from "./px/path";
import { drawnOf, Still, stock } from "./px/still";
import { paintText, paintTitle } from "./px/built";
import type { Thing } from "./px/still";
import { hslInt } from "./px/tint";
import { Light, REDUCE } from "./px/weather";
import { carLine, TrainActor } from "./px/train";
import { catchPicture, Fishing, pondOf } from "./px/pond";

/** v3.5.10: one part of the room that fails (a new snapshot field an old page does not know, a bad sprite) is skipped,
 *  and said once on the console; everything else goes on being drawn. */
const failed = new Set<string>();
function once(part: string, e: unknown) {
  if (!failed.has(part)) { failed.add(part); console.error(`room: ${part} failed; the rest goes on`, e); }
}
function guard(part: string, fn: () => void) {
  try { fn(); } catch (e) { once(part, e); }
}
import { step as works } from "./px/works";

export type Rect = { x: number; y: number; w: number; h: number };
/** What is under the pointer. */
/** `decor`: a piece of the room's own scenery (its sprite's name), when nothing else is there. `bare`: the bit grows here and has been picked. */
export type Target = { tile: [number, number]; pet?: string; creature?: string; door?: string; object?: string; bit?: string; bare?: boolean; mark?: Mark; decor?: string;
  display?: boolean };   // SPEC-v3.5.9 §4: the room's small display
export type Scene = { snap: Snap; room: RoomV; hello: Hello | null; selected: string | null; picked: string | null; replay: boolean };
/** What a hover card can show about a Target (§3.3): see `Room.describe`. Every field but `title` may be missing. */
export type Card = { what: "pet" | "creature" | "thing" | "fixture" | "stone" | "bit" | "door" | "writing" | "scenery"; title: string; sprite: HTMLCanvasElement | null;
  name?: string | null; kind?: string; color?: string | null; material?: string; maker?: string | null; owner?: string | null; heirloom?: boolean; worn?: string[];
  purpose?: string; does?: string | null; state?: string | null; text?: string; can?: string[];
  /** SPEC-v3.3 §2, plain lines to show as they are: what a thing that keeps things holds ("holds: a red ball, a flute",
   *  "room for 2 more"), where a thing put away is kept, where its home is when it is not there, the place it stands in. */
  notes?: string[];
  /** Where it is drawn, in CSS pixels from the top-left of the element given to `init`: a card can be put right by it. */
  rect?: Rect };

const norm = (s: string | null | undefined) => (s ?? "").trim().toLowerCase();
/** Each need's colour, as on the cards' bars (comfort has none there: gold). */
const NEED: Record<string, number> = { energy: 0x7ccf4e, curiosity: 0x4fa8ec, company: 0xe8545a, comfort: 0xf2c14e };
/** A thing that bends in the wind (SPEC-v3.5.9 §4). */
const leafy = (t: Thing) => !!(t.obj.fix?.plant || t.obj.planted || /plant|vine|bush|reed|flower|fern|herb/.test(t.name));
/** Would two pets on these tiles stand on each other: a pet is wider than a tile and taller than two (SPEC-v3.3 §5). */
const near = (a: Tile, b: Tile) => Math.abs(a[0] - b[0]) <= 1 && Math.abs(a[1] - b[1]) <= (a[0] === b[0] ? 2 : 1);
const recall = (k: string) => { try { return localStorage.getItem(k); } catch { return null; } };
const remember = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* private window */ } };

/** What a piece of scenery is called, from its sprite's own name: "decor.toy blocks" is "toy blocks", "decor.bed.red" a
 *  "red bed", "decor.banner.3" a "banner", "decor.tool.axe" an "axe". */
function sceneryName(sprite: string) {
  const [what, which] = sprite.split(".").slice(1);
  return !which || /^\d+$|^(left|right)$/.test(which) ? what ?? sprite : what === "tool" ? which : `${which} ${what}`;
}

const skies = new WeakMap<Layout, string | null>();
/** Is there sky over this room. ponytail: a layout should say so (`light.sky`: "open" or "glass"); until every one
 *  does, a room with sky among its tiles is open, and one whose north wall is mostly window is under glass. */
function skyOf(l: Layout | null): string | null {
  if (!l) return null;
  if (!skies.has(l)) skies.set(l, l.light?.sky ?? ([...(l.floor ?? []), ...(l.walls ?? [])].flat().some((n) => n?.startsWith("tile.sky")) ? "open" : (l.light?.window?.length ?? 0) >= 6 ? "glass" : null));
  return skies.get(l)!;
}

export class Room {
  onClick: (t: Target) => void = () => {};
  onHover: (t: Target | null, fx: number, fy: number) => void = () => {};
  /** Ids of the page's own elements that lie over the room: plates and bubbles keep out from under them. */
  clear: string[] = ["roomName", "banner"];
  private app = new Application();
  private el: HTMLElement | null = null;
  private world = new Container();      // everything in the art's own pixels, scaled up by K
  private ground = new Container();
  private walls = new Container();
  private flat = new Container();
  private sorted = new Container();     // what stands on the floor, by depth
  private top = new Container();
  private rims = new Container();       // the pets' pale outlines, over the dark
  private mark = new Graphics();        // round the thing the visitor has picked up
  private glow = new Graphics();        // SPEC-v3.5.7 §5: round the thing under the pointer, gold
  private fx = new Fx();
  private over = new Fx();              // SPEC-v3.4 §5: a burst, drawn over the lettering: a caption or bubble that is up does not hide it
  private light = new Light();
  private marks = new Marks();
  private words = new Labels();
  private still: Still | null = null;
  private ghosts = new Map<string, Ghost>();
  private pets = new Map<string, PetActor>();
  private beasts = new Map<string, CreatureActor>();
  private train: TrainActor | null = null;   // SPEC-v3.5.12 §3
  private fishing: Fishing | null = null;    // SPEC-v3.6a: the pond's fish, floats and fishers, kept while the room is looked at
  private heads = new Map<string, Rect>();
  private scene: Scene | null = null;
  private ready = false;
  private K = 0;                        // screen pixels to a pixel of the art
  private F = 1;                        // screen pixels to a pixel of lettering
  private built = "";
  private lit = "";
  private roomId = "";
  private tick = -1;
  private pace = 2000;
  private lastUpdate = 0;
  private last = 0;
  private seenAct: number | null = null;
  private seenMoment = -1;
  private seenEvent = -1;
  private weather = "";
  private pointer: number[] | null = null;
  private tap = 0;                      // the timer that lets go of what a finger tapped
  private aim = [0, 0];                 // the same, in screen pixels
  private next = { note: 0, air: 0, glint: 0, drip: 0, weather: 0, breath: 0 };
  private stage: Stage;
  private avoid: Rect[] = [];
  private avoidAt = -1e9;
  private flashing = false;
  private namesOn = false;              // the names of things show for as long as the page holds them on
  private tagKey = "";
  private beastBox = new Map<string, Rect>();
  private crate: Sprite | null = null;  // what a delivery came in, for a while after it
  private shakeUntil = 0;
  private crateFor = "";
  private hatched = new Map<string, number>();                 // who has just hatched here: its tag shows until then
  private shells = new Map<string, { c: Container; tick: number }>();   // the shell each left where its egg lay
  private hub = new Hub();              // SPEC-v3.5.1: the lit sign, the screens, the statue, the radio set
  private display: Display | null = null;   // SPEC-v3.5.9 §4
  private roomBox: Rect = { x: 0, y: 0, w: W, h: H };
  private felt = new Map<string, { tick: number; needs: Record<string, number> }>();   // SPEC-v3.5.9 §7: each pet's needs as last seen

  constructor() {
    this.stage = { now: 0, dt: 16, fx: this.fx, blocked: new Uint8Array(FX * FY), K: 1,
      free: (t, me) => onFloor(t) && !this.stage.blocked[idx(t)] && ![...this.pets.values()].some((a) => a.pet.id !== me && (near(a.home, t) || near(a.w.tile(), t))),
      where: (name, near) => this.where(name, near),
      held: false, dim: 0,
      thing: (name) => this.still?.things.get(norm(name)) ?? this.still?.things.get(name ?? ""),
      book: () => { const t = this.still && [...this.still.things.values()].find((t) => t.obj.fix?.book); return t ? [t.x, t.y - 4] : null; },
      others: () => [...[...this.pets.values()].map((a) => [a.w.x, a.w.y]), ...[...this.beasts.values()].map((b) => [b.w.x, b.w.y])] };
  }

  /** `el`: where the room goes. Give it a width (and, to limit its height, a CSS max-height): the canvas takes the
   *  largest whole-number scale that fits, and is centred in it. The size of the floor is the engine's (12 x 8). */
  async init(el: HTMLElement, _w = FX, _h = FY) {
    await Promise.all([loadArt(), loadSeasons(), this.app.init({ width: W, height: H, backgroundAlpha: 0, antialias: false, roundPixels: true, resolution: 1, autoDensity: false })]);
    this.el = el;
    const cv = this.app.canvas;
    cv.style.display = "block";
    cv.style.margin = "0 auto";
    cv.style.imageRendering = "pixelated";
    el.append(cv);
    this.sorted.sortableChildren = true;
    this.world.addChild(this.ground, this.walls, this.marks.c, this.flat, this.sorted, this.top, this.mark, this.glow, this.light.dark, this.rims, this.light.glow, this.light.panes, this.fx.c, this.light.falling);
    this.app.stage.addChild(this.world, this.words.c, this.over.c);
    const at = (e: PointerEvent) => { const r = cv.getBoundingClientRect(); return [((e.clientX - r.left) / r.width) * W, ((e.clientY - r.top) / r.height) * H]; };
    // a finger has no hover: a tap shows what a hover would (the card, the thing's name) for five seconds, and lifting the finger does not take it away
    const finger = (e: PointerEvent) => e.pointerType !== "mouse";
    cv.addEventListener("pointerdown", (e) => { const p = at(e); this.point(p); clearTimeout(this.tap); if (finger(e)) this.tap = window.setTimeout(() => this.point(null), 5000); this.onClick(this.under(p[0], p[1])); });
    cv.addEventListener("pointermove", (e) => { if (!finger(e)) this.point(at(e)); });
    cv.addEventListener("pointerleave", (e) => { if (!finger(e)) this.point(null); });
    new ResizeObserver(() => this.fit()).observe(el);
    addEventListener("resize", () => this.fit());   // a change of zoom or screen changes the pixel ratio without changing the element
    this.fit();
    this.app.ticker.add(() => this.frame(performance.now()));
    this.ready = true;
    if (this.scene) guard("drawing the room", () => this.update(this.scene!));
  }

  /** The largest whole number of screen pixels to an art pixel that fits the element. */
  private fit() {
    const el = this.el;
    if (!el) return;
    const dpr = devicePixelRatio || 1, tall = parseFloat(getComputedStyle(el).maxHeight) || Infinity;   // the element's width decides, and its max-height if it has one
    const K = Math.max(1, Math.floor(Math.min(((el.clientWidth || W) * dpr) / W, (tall * dpr) / H) + 0.001));
    if (K === this.K) return;
    this.K = this.stage.K = K;
    this.F = Math.max(1, Math.round(K / 2));
    this.app.renderer.resize(W * K, H * K);
    this.app.canvas.style.setProperty("width", `${(W * K) / dpr}px`, "important");
    this.app.canvas.style.setProperty("height", `${(H * K) / dpr}px`, "important");
    this.world.scale.set(K);
    this.over.c.scale.set(K);
    this.built = "";
    if (this.scene && this.ready) guard("drawing the room", () => this.update(this.scene!));
  }

  /** Hold the names of the things in the room on (true), or let them go (false). Each one also shows while the pointer
   *  is on its thing; otherwise they are gone (nothing names itself when a room comes into view). */
  names(on: boolean) {
    this.namesOn = on;
  }

  /** A still picture of a body, for cards, the family tree and the life records (kept for the page; petsprite.ts has more). */
  picture(genome: Genome, stage: string, look: Look = {}): string {
    return petPortrait(genome, stage, 2, { grey: look.grey }).toDataURL();
  }

  /** The name lines, captions and bubbles that show now (CSS pixels within the canvas), for checking that none overlap. */
  labels(): (Rect & { kind: string })[] {
    const dpr = devicePixelRatio || 1;
    return this.words.placed.map((r) => ({ x: r.x / dpr, y: r.y / dpr, w: r.w / dpr, h: r.h / dpr, kind: r.kind }));
  }

  /** SPEC-v3.4 §5: a small burst over a pet, once: it got what it wanted ("want") or found something out ("find").
   *  Just above its name line (twelve lettering pixels high, one above its head), never on it. */
  burst(pet: string, kind: string) {
    const a = this.pets.get(pet);
    if (!a) return;
    const r = a.rect();
    // three in a row over its own body (over its name it read as its neighbour's, and one was gone in a blink)
    for (const [ms, dx, dy] of [[0, 0, 0], [450, -6, 3], [900, 6, -2]]) setTimeout(() => this.over.spawn(`burst.${kind}`, r.x + r.w / 2 + dx, Math.max(this.fx.top + 9, r.y + r.h / 3 + dy), { vy: -5, life: 1100 }), ms);
  }

  // ---- a snapshot arrives ----

  update(sc: Scene) {
    this.scene = sc;
    if (!this.ready) return;
    const now = performance.now(), { snap, room } = sc, fresh = room.id !== this.roomId;
    if (snap.tick !== this.tick) {   // a new moment of the house: how long since the last one sets the walking pace, so a walk is a glide and not a step and a wait
      this.pace = this.tick < 0 || fresh ? tickMs(snap) : clamp(now - this.lastUpdate, 120, Math.max(2600, tickMs(snap) * 1.25));
      [this.tick, this.lastUpdate] = [snap.tick, now];
    }
    // its layout not in yet: the room on screen stays as it was (or nothing, the first time) until it is, rather than a
    // plain floor for a moment or longer; the layout's arrival draws it
    const lay = layout(room.type, () => { this.built = ""; if (this.scene) this.update(this.scene); });
    if (lay === undefined) return;
    this.roomId = room.id;
    if (fresh) { this.fx.clear(); this.over.clear(); this.ghosts.clear(); this.crate?.destroy(); this.crate = null; this.hatched.clear(); this.fishing?.detach(); this.fishing?.destroy(); this.fishing = null; }

    const keep = this.keep();
    const key = JSON.stringify([room.id, room.type, lay === undefined, room.areas, Object.entries(room.objects).map(([n, o]) => [n, o.pos, o.state, o.wall, o.on, o.store?.holds, o.servings === 0, o.grow != null && o.grow < 0.35, o.water, o.planted, o.build,
      o.made && [o.made.recipe, o.made.active, o.made.behavior?.do, o.made.worn, !!o.made.heirloom], !!o.memorial]), room.spots, room.paint, room.painted, room.doors, room.shut, room.wet, snap.power,
      snap.rooms.map((r) => r.type), room.marks, this.K, keep, snap.door_tiles, snap.clock.season, ((r) => r && [r.track, r.platform, r.side, r.buffer])(snap.rail?.rooms?.[room.id]),
      ((p) => p && [p.water, p.dock, p.frozen, p.holes])(snap.pond?.room === room.id ? snap.pond : null)]);
    if (key !== this.built) {
      this.built = key;
      this.rebuild(sc, lay ?? null, keep, now);
    }
    const still = this.still!;
    this.mark.clear();
    const held = sc.picked ? still.things.get(sc.picked) : null;
    if (held) this.mark.rect(Math.round(held.rect.x) - 2, Math.round(held.rect.y) - 2, Math.round(held.rect.w) + 4, Math.round(held.rect.h) + 4).stroke({ width: 1, color: 0xffb347, alignment: 1 });

    // light and weather
    const reading = snap.read_glow ? [...still.things.values()].filter((t) => t.obj.fix?.book).map((t) => ({ x: t.x, y: t.y - 6, r: 24, color: [255, 236, 150], made: true })) : [];
    const env = { phase: snap.clock.phase, hour: Math.round(snap.clock.hour * 10) / 10, weather: snap.weather, season: snap.clock.season, power: snap.power, lit: room.lit, cold: room.cold, night: lay?.light?.night ?? 0.45, day: lay?.light?.day ?? 0,
                  sky: skyOf(lay ?? null), windowTiles: lay?.light?.window ?? [], windows: still.windows.map((w) => w.rect), lamps: snap.power ? [...still.lamps, ...reading] : [], sun: still.sun,   // in a power cut nothing glows
                  panes: skyOf(lay ?? null) === "glass" ? (lay?.light?.window ?? []).map(([tx]) => ({ x: OX + tx * TILE + 1, y: 4, w: TILE - 2, h: OY - 10 })) : [] };
    const lit = JSON.stringify(env);
    if (lit !== this.lit) { this.lit = lit; this.light.set(env); }

    this.cast(sc, fresh, now);
    const pond = pondOf(snap, room);
    if (pond && this.fishing) guard("the pond", () => this.fishing!.update(pond, now));
    for (const t of still.things.values()) {   // what a pet is at just now stirs: a toy bounces, a thing being put away is off the floor and in its paws
      let stir = 0;
      for (const a of this.pets.values()) if (a.stirs && this.stage.thing(a.pet.body?.what) === t) stir = a.stirs;
      if ((stir === 3) !== (t.stir === 3) && !t.s.destroyed) t.s.visible = stir !== 3;
      t.stir = stir;
    }
    this.rises(sc, fresh);
    this.arrived(sc);
    this.say(sc);
    this.tag(sc);
    this.happen(sc, fresh, now);
    if (this.pointer) this.point();
  }

  /** The stretch of the south wall the page's plate with the room's name lies over, in the room's pixels. */
  private keep(): number[] | null {
    const e = document.getElementById(this.clear[0] ?? ""), view = this.app.canvas.getBoundingClientRect();
    if (!e || e.hidden || !view.width) return null;
    const b = e.getBoundingClientRect(), s = W / view.width;
    return b.bottom < view.bottom - view.height * 0.2 ? null : [Math.round((b.left - view.left) * s), Math.round((b.right - view.left) * s)];
  }

  /** Everything that holds still, built again. What made things stood there a moment ago is kept for the effects. */
  private rebuild(sc: Scene, lay: Layout | null, keep: number[] | null, now: number) {
    const old = this.still;
    this.fishing?.detach();   // (kept: the pond's moving life goes on over the room drawn again)
    if (old) {
      this.ghosts.clear();
      for (const [n, t] of old.things) if (t.drawn) this.ghosts.set(n, { texture: t.texture, x: t.x, y: t.y, scale: t.scale, h: t.rect.h });
      old.destroy();
    }
    const s = (this.still = new Still(sc.snap, sc.room, lay, this.K));
    this.light.shape = s.shape;
    this.lit = "";   // a new room: draw its light afresh
    this.ground.addChild(s.ground);
    this.walls.addChild(s.wallLayer);
    this.flat.addChild(s.flat);
    this.top.addChild(s.top);
    this.hub.build(s, this.K);
    this.display = display(s, sc.room, this.K);
    this.marks.build(sc.room, s, this.F / this.K, keep, now);
    for (const c of s.standing) this.sorted.addChild(c);
    if (s.pond) {
      if (!this.fishing) { this.fishing = new Fishing(); this.fishing.onAdd = (c) => this.sorted.addChild(c); }
      this.fishing.attach(s.pond);
    } else if (this.fishing) { this.fishing.destroy(); this.fishing = null; }
  }

  /** Where each pet stands: on the engine's tile, or the nearest free one if that tile has furniture on it or is taken. */
  private cast(sc: Scene, fresh: boolean, now: number) {
    const { snap, room } = sc, still = this.still!;
    const here = snap.pets.filter((p) => p.room === room.id && !(p.stage === "dead" && p.buried));
    for (const [id, a] of this.pets) if (fresh || !here.some((p) => p.id === id)) { a.c.destroy({ children: true }); a.rim.destroy(); this.pets.delete(id); this.heads.delete(id); }
    // nobody on another's tile or right beside it, and nobody straight above or below another (the one in front would stand on the other's head): each whole
    const fixed = (p: PetV) => p.stage === "egg" || p.stage === "dead", claimed: Tile[] = [], apart = (t: Tile) => !claimed.some((c) => near(c, t));
    for (const p of [...here].sort((a, b) => Number(fixed(b)) - Number(fixed(a)) || (a.id < b.id ? -1 : 1))) {
      let a = this.pets.get(p.id);
      const first = !a;
      if (!a) {
        this.pets.set(p.id, (a = new PetActor()));
        this.sorted.addChild(a.c);
        this.rims.addChild(a.rim);
      }
      const was = a.pet, same = was && was.pos[0] === p.pos[0] && was.pos[1] === p.pos[1] && !still.blocked[idx(a.home)] && apart(a.home);
      const want: Tile = [clamp(Math.round(p.pos[0]), 0, FX - 1), clamp(Math.round(p.pos[1]), 0, FY - 1)];
      const home = same ? a.home : nearestFree(want, still.blocked, apart, first ? want : a.w.tile());
      claimed.push(home);
      if (was?.stage === "egg" && p.stage !== "egg" && p.stage !== "dead") this.hatch(p, a.w.x, a.w.y, snap.tick, now);   // out of its shell this moment
      const d = doing(p), o = d ? room.objects[norm(d.what)] ?? room.objects[d.what ?? ""] : null;
      a.eating = d?.type === "eat" || (d?.type === "use" && !!o?.fix && ("meal" in o.fix || !!o.fix.plant));   // (an older engine called eating "use")
      a.update(p, home, this.stage, this.pace, sc.selected === p.id, first, !!snap.activities?.[p.body?.activity ?? ""]?.rest);
      if (first) a.step(this.stage);
    }
    // an egg that hatched here within the hour, before this room was looked at: its shell lies by the newcomer still
    const hour = snap.day_seconds / snap.tick_seconds / 24;
    for (const m of snap.moments) if (m.kind === "hatched" && m.room === room.id && m.pet && snap.tick - m.tick >= 0 && snap.tick - m.tick <= hour && !this.shells.has(m.pet)) {
      const a = this.pets.get(m.pet);
      if (a) this.hatch(a.pet, a.w.x - 9, a.w.y, m.tick, 0);
    }
    for (const [id, s] of this.shells) if (fresh || snap.tick < s.tick || snap.tick - s.tick > hour) { s.c.destroy({ children: true }); this.shells.delete(id); }
    // nobody walks through one who is asleep, an egg, or a body: their tiles are shut to the others' paths
    const walk = (this.stage.blocked = still.blocked.slice());
    for (const a of this.pets.values()) if (fixed(a.pet) || a.pet.asleep) walk[idx(a.home)] = 1;
    const beasts = snap.creatures.filter((c) => c.room === room.id && c.kind !== "train");
    for (const [id, b] of this.beasts) if (fresh || !beasts.some((c) => c.id === id)) { b.c.destroy({ children: true }); this.beasts.delete(id); }
    for (const c of beasts) {
      let b = this.beasts.get(c.id);
      const first = !b;
      if (!b) {
        this.beasts.set(c.id, (b = new CreatureActor()));
        this.sorted.addChild(b.c);
        if (!fresh) for (const a of this.pets.values()) { a.turn(OX + c.pos[0] * TILE, OY + c.pos[1] * TILE, now, 1800); if (Math.random() < 0.3) a.react("happy", now + 300, 800); }   // somebody new on the floor
      }
      const owner = snap.pets.find((p) => p.id === c.tame);
      b.update(c, this.stage, this.pace, first, owner ? hslInt(owner.genome.hue, owner.genome.saturation, 0.55) : null);
    }
    // SPEC-v3.5.12 §3: the train, whichever room its cars are in (one on its way in or out is seen at the door)
    const tr = snap.creatures.find((c) => c.kind === "train");
    if (!tr && this.train) { this.train.destroy(); this.train = null; }
    if (tr) {
      if (!this.train) { this.train = new TrainActor(); for (const v of this.train.cars) this.sorted.addChild(v.c); }
      this.train.update(tr, room, snap, now, this.pace, !sc.replay);
    }
  }

  /** Each pet's line (its name and the sign of what it is doing), what it wants, and its words. */
  private say(sc: Scene) {
    const { snap, room } = sc, who: Who[] = [];
    for (const a of this.pets.values()) {
      const p = a.pet, egg = p.stage === "egg", dead = p.stage === "dead";
      const said = p.said && ago(snap, p.said.tick) <= (sc.replay ? 30 : 16) ? p.said : null;
      who.push({ id: p.id, name: egg ? p.name ?? "egg" : p.label, family: p.family ?? 1, selected: sc.selected === p.id, faded: dead,
                 caption: egg || dead || p.asleep ? null : p.focus?.says || p.plan?.intention || p.focus?.words || null, thinking: !!p.thinking && !p.asleep && !egg && !dead,
                 say: said ? { key: `${said.tick}${said.text}`, text: said.text, to: said.to_name, song: !!said.song } : null,
                 // the sign of what it is doing (SPEC-v3.3 §5): its body's by itself, or the step it decided on
                 icon: egg || dead || p.asleep ? null : p.body?.icon || p.sign?.icon || "" });
    }
    this.words.sync(who, this.F, (W * this.K) / this.F);
  }

  /** What has just happened here: each finished step once (never twice, also after a reload), startles, a turn to the window. */
  private happen(sc: Scene, fresh: boolean, now: number) {
    const { snap, room } = sc, house = `${snap.start}|${snap.lineage.id}|${snap.profile}`;
    const cast = { pets: this.pets, things: this.still!.things, ghosts: this.ghosts, fx: this.fx, now, where: (n: string | null | undefined) => this.where(n), petAt: (n: string | null | undefined) => this.petBy(n),
                   kept: (n: string | null | undefined) => { const on = (room.objects[norm(n)] ?? room.objects[n ?? ""])?.on; return on ? this.still!.things.get(on) : undefined; } };
    const acts = snap.acts ?? [], top = acts.reduce((n, a) => Math.max(n, a.n), 0);
    if (this.seenAct == null) {
      const [h, n] = (recall("pet.acts") ?? "").split("#");
      this.seenAct = h === house && Number(n) <= top ? Number(n) : top;
    }
    if (top < this.seenAct) this.seenAct = top;   // a replay wound back, or another house
    for (const a of acts) if (a.n > this.seenAct && a.room === room.id && !fresh && (snap.tick - a.tick) * snap.tick_seconds <= 12) play(a, cast);
    if (top !== this.seenAct) remember("pet.acts", `${house}#${top}`);
    this.seenAct = top;
    // a recording from before the engine sent finished steps: the moments say a little of it
    const moments = snap.moments, last = moments.at(-1)?.n ?? this.seenMoment;
    if (!snap.acts && this.seenMoment >= 0 && !fresh) for (const m of moments) if (m.n > this.seenMoment && m.room === room.id && m.pet && ago(snap, m.tick) < 20) {
      const type = ({ nuzzle: "nuzzle", gift: "give", song: "sing", wrote: "write", scrubbed: "scrub", read: "ask_book" } as Record<string, string>)[m.kind];
      const to = [...this.pets.values()].find((a) => a.pet.id !== m.pet && m.text.includes(a.pet.label))?.pet.id;
      if (type) play({ n: 0, tick: m.tick, pet: m.pet, type, to, room: room.id, ok: true } as Act, cast);
    }
    this.seenMoment = last < this.seenMoment ? last : Math.max(this.seenMoment, last);

    const event = snap.events.filter((e) => !e.room || e.room === room.id).at(-1);
    if (!fresh && this.seenEvent >= 0 && event && event.tick > this.seenEvent && event.kind !== "power back") this.startle(now, 1);
    this.seenEvent = fresh ? event?.tick ?? 0 : Math.max(event?.tick ?? 0, this.seenEvent);
    if (snap.weather !== this.weather && this.weather && (snap.weather === "rain" || snap.weather === "storm" || snap.weather === "snow")) {
      const w = this.still!.windows[0]?.rect;   // the weather has turned: a look toward the window
      if (w) for (const a of this.pets.values()) a.turn(w.x, w.y, now + Math.random() * 600, 2200);
    }
    this.weather = snap.weather;
  }

  /** SPEC-v3.5.9 §7: a need that has just risen (by three or more since the last moment): a tiny "+" in its colour floats up. */
  private rises(sc: Scene, fresh: boolean) {
    const tick = sc.snap.tick;
    for (const a of this.pets.values()) {
      const p = a.pet, was = this.felt.get(p.id);
      if (!p.needs) continue;
      if (was && !fresh && tick > was.tick && tick - was.tick <= 3) {
        let i = 0;
        for (const [n, v] of Object.entries(p.needs)) if (v - (was.needs[n] ?? v) >= 3) {
          const k = i++;
          this.fx.after(k * 260, () => this.fx.spawn("plus", a.w.x + (k % 2 ? 5 : -4), a.w.y - a.tall - 2, { vy: -9, life: 1300, sway: 1, tint: NEED[n] ?? 0xffffff }));
        }
      }
      if (!was || tick !== was.tick) this.felt.set(p.id, { tick, needs: { ...p.needs } });
    }
  }

  /** A delivery or a discovery that came in a crate (SPEC-v3.1 §1): the crate stands open where it landed for a couple of
   *  world hours, then fades. */
  private arrived(sc: Scene) {
    const { snap, room } = sc, hour = snap.day_seconds / snap.tick_seconds / 24, still = this.still!;
    const m = snap.moments.filter((m) => m.room === room.id && (m.kind === "delivery" || m.kind === "arrival writing" || m.kind === "arrival radio") && snap.tick >= m.tick && snap.tick - m.tick <= 2 * hour).at(-1);
    if (!m || this.crateFor !== this.built) { this.crate?.destroy(); this.crate = null; }   // (the room has changed under it: it is set down again)
    if (!m) return;
    this.crateFor = this.built;
    if (!this.crate) {
      const name = pick("crate.open", "crate"), sz = size(name), s = (this.crate = new Sprite(tex(name)));
      const at = nearestFree([6, 4], still.blocked, (t) => !room.spots.some((p) => p.pos[0] === t[0] && p.pos[1] === t[1]) && ![...this.pets.values()].some((a) => a.home[0] === t[0] && a.home[1] === t[1]));
      s.position.set(OX + at[0] * TILE - sz.ax, OY + at[1] * TILE - sz.ay);
      s.zIndex = OY + at[1] * TILE + TILE - 5;
      this.sorted.addChild(s);
      this.fx.spawn("dust", s.x + sz.w / 2, s.y + sz.h - 2, { life: 450 });
    }
    this.crate.alpha = Math.min(1, (2 * hour - (snap.tick - m.tick)) / (0.4 * hour));
  }

  /** The name of every thing in the room, for while the page holds them on (each also shows under the pointer):
   *  a made thing by its kind, a fixture and a piece of scenery by its name, bits and scenery once per kind (the one
   *  nearest the middle), a creature by its kind, a place the room has grown by its name. */
  private tag(sc: Scene) {
    const still = this.still!, K = this.K, key = `${this.built}|${[...this.beasts.keys()].join()}|${!!this.crate}|${[...this.hatched.keys()].join()}`;
    if (key === this.tagKey) return;
    this.tagKey = key;
    const px = (r: Rect): Rect => ({ x: r.x * K, y: r.y * K, w: r.w * K, h: r.h * K }), tags: Tag[] = [], mid = (r: Rect) => Math.hypot(r.x + r.w / 2 - W / 2, r.y + r.h / 2 - (OY + (FY * TILE) / 2));
    const made: Thing[] = [];
    for (const t of still.things.values()) {
      if (t.obj.fix?.sun) continue;
      if (t.drawn) { made.push(t); continue; }
      const stone = t.obj.memorial && (sc.snap.pets.find((p) => p.id === t.obj.memorial!.pet)?.label ?? t.name.replace(/^stone for /, ""));
      tags.push({ key: `t.${t.name}`, text: stone ? `stone for ${stone}` : t.name, rect: px(t.rect), pri: stone ? 0 : 2 });
    }
    while (made.length) {   // made things of one kind standing together share one name: "wind chimes x3"
      const group = [made.pop()!];
      for (let i = 0; i < group.length; i++) for (let j = made.length - 1; j >= 0; j--) {
        if (made[j].drawn!.kind === group[0].drawn!.kind && Math.hypot(made[j].x - group[i].x, made[j].y - group[i].y) < 2.3 * TILE) group.push(...made.splice(j, 1));
      }
      const x0 = Math.min(...group.map((t) => t.rect.x)), y0 = Math.min(...group.map((t) => t.rect.y)), x1 = Math.max(...group.map((t) => t.rect.x + t.rect.w)), y1 = Math.max(...group.map((t) => t.rect.y + t.rect.h));
      const k = group[0].drawn!.kind, many = /(s|x|ch|sh)$/.test(k) ? `${k}es` : `${k}s`;
      tags.push({ key: `m.${group.map((t) => t.name).sort().join("|")}`, text: group.length > 1 ? `${many} ×${group.length}` : k, rect: px({ x: x0, y: y0, w: x1 - x0, h: y1 - y0 }), pri: 0 });
    }
    for (const [id, b] of this.beasts) {
      const box = this.beastBox.get(id) ?? { x: 0, y: 0, w: 0, h: 0 };
      this.beastBox.set(id, box);
      tags.push({ key: `c.${id}`, text: b.cr.kind, rect: box, pri: 0 });
    }
    if (this.crate) tags.push({ key: "crate", text: "crate", rect: px({ x: this.crate.x, y: this.crate.y, w: this.crate.width, h: this.crate.height }), pri: 1 });
    const once = (list: { name: string; rect: Rect }[], pri: number) => {   // one of each kind: the one nearest the middle of the room
      const best = new Map<string, Rect>();
      for (const it of list) if (!best.has(it.name) || mid(it.rect) < mid(best.get(it.name)!)) best.set(it.name, it.rect);
      for (const [name, rect] of best) tags.push({ key: `${pri}.${name}`, text: name, rect: px(rect), pri });
    };
    for (const a of still.areas) tags.push({ key: `a.${a.name}`, text: a.name, rect: px(a.rect), pri: 1 });
    once(still.spots.map((s) => ({ name: s.bit, rect: s.rect })), 3);
    once(still.scenery.map((s) => ({ name: sceneryName(s.sprite), rect: s.rect })), 4);
    for (const [id, until] of this.hatched) if (this.heads.has(id)) tags.push({ key: `h.${id}`, text: "just hatched", rect: this.heads.get(id)!, pri: 0, until });
    this.words.name(tags);
    this.words.things = [...still.things.values()].filter((t) => !t.obj.fix?.soft && !t.obj.fix?.sun).map((t) => px(t.rect));
  }

  /** An egg has hatched (at x, y in the room's pixels): its broken shell lies there for a world hour, and the newcomer
   *  is tagged "just hatched" for a while. The art's `egg.shell` if it has one, else a few shards in the egg's colours. */
  private hatch(p: PetV, x: number, y: number, tick: number, now: number) {
    if (this.shells.has(p.id)) return;
    const c = new Container(), light = hslInt(p.genome.hue, p.genome.saturation * 0.5, 0.84), dark = hslInt(p.genome.hue, p.genome.saturation * 0.6, 0.62);
    if (has("egg.shell")) { const s = new Sprite(tex("egg.shell")); s.anchor.set(0.5, 1); c.addChild(s); }
    else {
      const g = new Graphics();
      for (const [sx, sy, w, h] of [[-6, -4, 5, 4], [2, -3, 4, 3], [-1, -2, 2, 2]]) g.rect(sx - 1, sy - 1, w + 2, h + 2);
      g.fill(0x2b2233);
      for (const [sx, sy, w, h] of [[-6, -4, 5, 4], [2, -3, 4, 3], [-1, -2, 2, 2]]) g.rect(sx, sy, w, h);
      g.fill(light).rect(-6, -1, 5, 1).rect(2, -1, 4, 1).fill(dark).rect(-5, -5, 1, 1).rect(-3, -5, 1, 1).rect(3, -4, 1, 1).rect(5, -4, 1, 1).fill(0x2b2233);   // a shadowed lower edge, a jagged broken one
      c.addChild(g);
    }
    c.position.set(Math.round(x), Math.round(y));
    this.flat.addChild(c);
    this.shells.set(p.id, { c, tick });
    if (now) { this.hatched.set(p.id, now + 8000); this.fx.burst("sparkle", x, y - 6, 5, 20); }
  }

  private startle(now: number, chance: number) {
    for (const a of this.pets.values()) if (Math.random() < chance && !a.pet.asleep && a.pet.stage !== "egg" && a.pet.stage !== "dead") {
      a.react("startled", now, 750);
    }
  }

  private petBy(name: string | null | undefined): PetActor | null {
    const n = norm(name);
    if (!n) return null;
    for (const a of this.pets.values()) if (a.pet.id === name || norm(a.pet.name) === n || norm(a.pet.label) === n) return a;
    return null;
  }
  /** The place of a pet, creature, thing, door or wall by its name, in the room's pixels; a wall, at the point nearest `near`. */
  private where(name: string | null | undefined, near?: number[]): number[] | null {
    const n = norm(name), still = this.still;
    if (!n || !still) return null;
    const a = this.petBy(name);
    if (a) return [a.w.x, a.w.y];
    for (const b of this.beasts.values()) if (b.cr.id === name || norm(b.cr.name) === n || b.cr.kind === n.replace(/^(the|a) /, "")) return [b.w.x, b.w.y];
    const t = still.things.get(n) ?? still.things.get(name ?? "");
    if (t) return [t.x, t.y - Math.min(8, t.rect.h / 2)];
    const sc = this.scene, behind = sc && Object.entries(sc.room.doors).find(([, id]) => norm(sc.snap.rooms.find((r) => r.id === id)?.name) === n)?.[0];   // "the pond room": the door to it
    const side = behind ?? /(north|south|west|east)/.exec(n)?.[1], p = near ?? [W / 2, OY + (FY * TILE) / 2];
    if (!side) return null;
    const d = still.doors.find((d) => d.dir === side);
    if ((n.includes("door") || n === side || behind) && d) return [d.rect.x + d.rect.w / 2, d.rect.y + d.rect.h / 2];
    return side === "north" ? [p[0], OY - 10] : side === "south" ? [p[0], OY + FY * TILE + 6] : side === "west" ? [OX - 6, p[1] - 8] : [OX + FX * TILE + 6, p[1] - 8];
  }

  // ---- every frame ----

  private frame(now: number) {
    try { this.frameParts(now); } catch (e) { once("frame", e); }
  }

  private frameParts(now: number) {
    const sc = this.scene, still = this.still;
    if (!sc || !still || !this.ready) return;
    const dt = Math.min(100, now - (this.last || now)), st = this.stage, K = this.K;
    this.last = now;
    [st.now, st.dt] = [now, dt];
    const pools = this.light.pools;
    pools.length = 0;
    if (this.train) guard("the train", () => this.train!.frame(now, this.fx, this.light.darkness));
    if (still.pond) guard("the pond", () => {
      still.pond!.frame(now);
      this.fishing?.frame(now, dt, sc.snap, this.fx, (id) => { const a = this.pets.get(id); return a ? { x: a.w.x, y: a.w.y, tall: a.tall, coat: hslInt(a.pet.genome.hue, a.pet.genome.saturation, 0.62) } : null; },
                          K, (c) => catchPicture(c, sc.room));
    });
    for (const a of this.pets.values()) {
      a.ride = a.pet.riding ? this.train?.step ?? [] : null;   // SPEC-v3.5.12 §3: on the tram's back step (out of sight with it)
      guard("a hob", () => a.step(st));
      const r = a.rect(), h = this.heads.get(a.pet.id) ?? { x: 0, y: 0, w: 0, h: 0 };
      [h.x, h.y, h.w, h.h] = [r.x * K, r.y * K, r.w * K, r.h * K];
      this.heads.set(a.pet.id, h);
      pools.push(r.x + r.w / 2, r.y + r.h / 2);
    }
    st.held = now - this.lastUpdate > Math.max(6000, this.pace * 3);   // the house has stopped (a replay paused): nobody wanders
    for (const [id, b] of this.beasts) {
      guard("a creature", () => b.step(st));
      const box = this.beastBox.get(id), r = b.rect();
      if (box) [box.x, box.y, box.w, box.h] = [r.x * K, r.y * K, r.w * K, r.h * K];
    }
    this.words.naming = this.namesOn;
    const at = this.pointer;
    if (at) { this.aim[0] = at[0] * K; this.aim[1] = at[1] * K; }
    this.words.pointer = at ? this.aim : null;
    st.dim = this.light.darkness;
    this.fx.top = still.bounds.y + 1;
    guard("the room's small life", () => this.alive(sc, still, now));
    guard("the light", () => this.light.step(now));
    guard("the Works", () => works(still, sc.snap, now));   // SPEC-v3.5.1: the machine room's machine, alive
    if (this.light.flashing && !this.flashing) { this.startle(now, 0.3); this.shakeUntil = now + 130; }   // thunder: some of them jump, and every room feels it
    this.world.y = now < this.shakeUntil ? K : 0;
    this.flashing = this.light.flashing;
    const tip = this.marks.step(now);
    if (tip && Math.random() < 0.3) this.fx.spawn("grit", tip[0] / K, tip[1] / K, { vx: (Math.random() - 0.5) * 10, vy: 8, g: 30, life: 500 });
    guard("effects", () => this.fx.step(now, dt));
    guard("effects", () => this.over.step(now, dt));
    this.mark.alpha = 0.6 + 0.4 * Math.sin(now / 200);
    if (now - this.avoidAt > 500) {   // the page's own plates over the room take their space first
      this.avoidAt = now;
      const view = this.app.canvas.getBoundingClientRect(), s = view.width ? (W * K) / view.width : 1;
      this.avoid = this.clear.map((id) => document.getElementById(id)).filter((e): e is HTMLElement => !!e && !e.hidden && e.offsetParent !== null).map((e) => e.getBoundingClientRect())
        .map((b) => ({ x: (b.left - view.left) * s, y: (b.top - view.top) * s, w: b.width * s, h: b.height * s }));
    }
    guard("the machine room", () => this.hub.step(now, sc.snap, sc.room, this.fx));
    guard("the room's display", () => this.display?.board.step(now, sc.snap));
    const b = still.bounds, rm = this.roomBox;
    [rm.x, rm.y, rm.w, rm.h] = [(b.x + 2) * K, (b.y + 1) * K, (b.w - 4) * K, (b.h - 3) * K];   // a little inside the room's edge: nothing hangs over its border
    guard("the words", () => this.words.step(now, dt, this.heads, K, rm, this.avoid));
  }

  /** The small life of the room's things: glints on glass, a springy thing's bob, notes from what sounds, drips, a draught, dust in the sun. */
  private alive(sc: Scene, still: Still, now: number) {
    const { snap, room } = sc, fx = this.fx, K = this.K, n = this.next, sky = skyOf(still.layout);
    const windy = (snap.weather === "storm" && !!sky) || room.cold, gust = REDUCE.matches ? 900 : 380;   // a storm under the sky, or a draught
    for (const t of still.things.values()) {
      if (t.s.destroyed) continue;
      if (t.bob || t.bounce || t.stir === 1) t.s.y = t.y - Math.round((t.bounce ? Math.abs(Math.sin(now / 190 + t.x)) * 5 : t.stir === 1 ? Math.abs(Math.sin(now / 215)) * 4 : (Math.sin(now / 700 + t.x) + 1) * 1) * K) / K;
      else if (t.s.y !== t.y) t.s.y = t.y;
      t.s.x = t.stir === 2 ? t.x + Math.round(Math.sin(now / 70) * K * Math.max(0, Math.sin(now / 450))) / K : t.x;   // fiddled with: it shakes, in fits
      if (windy && leafy(t)) t.s.x += Math.round(Math.sin(now / gust + t.x) * 1.4 + Math.sin(now / (gust * 0.37) + t.y) * 0.5);   // and it bends in the wind
      for (const e of t.extra) { e.position.copyFrom(t.s.position); e.visible = t.s.visible; }   // what grows in it goes with it
    }
    if (now > n.glint) {
      n.glint = now + 700;
      for (const t of still.things.values()) {
        if ((t.glassy && Math.random() < 0.3) || (t.heirloom && Math.random() < 0.2)) fx.spawn("glint", t.rect.x + 2 + Math.random() * (t.rect.w - 4), t.rect.y + 2 + Math.random() * (t.rect.h / 2), { life: 450 });
        if (t.noisy && Math.random() < 0.7) fx.spawn("tick", t.x + (Math.random() < 0.5 ? -1 : 1) * (t.rect.w / 2 + 3), t.y - t.rect.h / 2, { life: 420, vx: 0 });
        if (t.fragrant && Math.random() < 0.3) fx.spawn("speck", t.x + (Math.random() - 0.5) * 6, t.rect.y, { vy: -6, life: 1500, sway: 2, tint: 0xf5a8c8 });
        if (t.obj.fix?.book && snap.read_glow) fx.spawn("sparkle", t.x + (Math.random() - 0.5) * 10, t.y - 8, { vy: -10, life: 800 });
      }
    }
    if (now > n.note) {   // notes over whoever is singing, whatever is playing, and the instruments while the room still rings
      n.note = now + 480;
      const up = (x: number, y: number) => fx.spawn("note", x + (Math.random() - 0.5) * 8, y, { vx: (Math.random() - 0.5) * 6, vy: -14, life: 1600, sway: 2 });
      for (const s of snap.sung ?? []) if (s.room === room.id && ago(snap, s.tick) <= 10) {
        const p = this.pets.get(s.by), b = this.beasts.get(s.by), t = still.things.get(s.by);
        if (p) up(p.w.x, p.w.y - p.tall - 2); else if (b) up(b.w.x, b.w.y - 12); else if (t) up(t.x, t.rect.y);
      }
      for (const t of still.things.values()) if (t.obj.state === "playing" || (room.sounding && t.obj.fix?.loud)) up(t.x, t.rect.y);
    }
    this.weatherLife(sc, still, now, sky);
    if (now > n.drip && (room.wet || room.cold || (still.sun && snap.clock.phase !== "night"))) {
      n.drip = now + 240;
      if (room.wet && still.drip && Math.random() < 0.2) {   // a leak drips in one place: a drop down from the top of the wall, a ring where it lands in the puddle
        const [x, from, to] = still.drip;
        fx.fly(fxTexture("drop"), [x, from], [x, to], 480, 1, () => fx.spawn("rain.splash", x, to, { life: 340, tint: 0xcfeaf6 }));
      }
      if (room.cold) fx.spawn("speck", OX, OY + Math.random() * FY * TILE, { vx: 34, life: 3000, sway: 2, tint: 0xdcecff, alpha: 0.7 });   // a draught: pale wisps crossing the floor
      if (still.sun && snap.clock.phase !== "night" && Math.random() < 0.4) fx.spawn("speck", still.sun[0] + (Math.random() - 0.5) * 24, still.sun[1] + (Math.random() - 0.5) * 16, { vy: -3, life: 2600, sway: 2, tint: 0xfff2c0, alpha: 0.7 });
    }
  }

  /** SPEC-v3.5.9 §4: the weather and the hour inside: dust in a sunbeam, fireflies in the garden at night, breath in
   *  the cold. (Rain rippling the pond, and its glints: px/pond.ts.) */
  private weatherLife(sc: Scene, still: Still, now: number, sky: string | null) {
    const { snap, room } = sc, fx = this.fx, n = this.next, night = snap.clock.phase === "night", w = snap.weather, calm = REDUCE.matches ? 2 : 1;
    if (now < n.weather) return;
    n.weather = now + 300 * calm;
    for (const [x, y, bw, bh] of this.light.beams) if (Math.random() < 0.5) fx.spawn("speck", x + (Math.random() - 0.5) * bw, y + (Math.random() - 0.5) * bh, { vy: -2, vx: 1, life: 2800, sway: 2, tint: 0xfff2c0, alpha: 0.65 });
    if (sky === "open" && night && snap.clock.season !== "winter" && (w === "clear" || w === "cloudy" || w === "heat") && Math.random() < 0.55)
      fx.spawn("speck", OX + Math.random() * FX * TILE, OY + TILE + Math.random() * (FY - 1) * TILE, { vx: (Math.random() - 0.5) * 8, vy: (Math.random() - 0.5) * 6, life: 3600, sway: 3, tint: 0xe4ff7a });
    const cold = room.cold || ((sky === "open" || w === "snow") && snap.clock.season === "winter");
    if (cold && now > n.breath) {   // every so often each one breathes out a little cloud
      n.breath = now + 900;
      for (const a of this.pets.values()) if (a.pet.stage !== "egg" && a.pet.stage !== "dead" && Math.random() < 0.4) {
        const side = a.w.dir === "left" ? -1 : a.w.dir === "right" ? 1 : Math.random() < 0.5 ? -1 : 1;
        fx.spawn("wisp", a.w.x + side * 5, a.w.y - a.tall * 0.6, { vx: side * 7, vy: -3, life: 1100, tint: 0xeef6ff, alpha: 0.7 });
      }
    }
  }

  // ---- the pointer ----

  /** Say what the pointer is over; again whenever a snapshot changes what is there. */
  private point(at: number[] | null = this.pointer) {
    this.pointer = at;
    const t = at && this.under(at[0], at[1]), cv = this.app.canvas;
    for (const a of this.pets.values()) a.hovered = a.pet.id === t?.pet;   // SPEC-v3.5.8 §5: its sack's count shows
    const lit = t?.object && !t.pet ? this.still?.things.get(t.object) : null;
    this.glow.clear();
    if (lit && this.scene?.room.objects[t!.object!]?.made) {   // a made thing glows gold while it is pointed at
      const r = lit.rect, [x, y, w, h] = [Math.round(r.x) - 2, Math.round(r.y) - 2, Math.round(r.w) + 4, Math.round(r.h) + 4];
      this.glow.rect(x - 2, y - 2, w + 4, h + 4).stroke({ width: 2, color: 0xffc84a, alpha: 0.35, alignment: 1 })
        .rect(x, y, w, h).stroke({ width: 1, color: 0xffd76a, alignment: 1 }).rect(x, y, w, h).fill({ color: 0xffd76a, alpha: 0.12 });
    }
    const door = t?.door && !t.pet ? this.still?.doors.find((d) => d.dir === t.door) : null;
    if (door) {   // SPEC-v3.5.9 §7: a door lights up while it is pointed at (where it leads, and who is there, is on its card)
      const r = door.rect, [x, y, w, h] = [Math.round(r.x), Math.round(r.y), Math.round(r.w), Math.round(r.h)];
      this.glow.rect(x - 1, y - 1, w + 2, h + 2).stroke({ width: 1, color: 0xffe08a, alignment: 1 }).rect(x, y, w, h).fill({ color: 0xffe9a8, alpha: 0.28 });
    }
    cv.style.cursor = t?.pet ? "var(--hand, pointer)" : t?.object || t?.door || t?.display ? "var(--arrow, pointer)" : "";   // (skin.css, SPEC-v3.5.6 §8: the hand over a pet; inline, as the canvas sets its own)
    const beast = t?.creature && !t.pet ? this.beasts.get(t.creature) : null;   // a creature wears its name only while it is pointed at
    if (beast) { const r = beast.rect(); this.words.hover(beast.cr.name ?? `a ${beast.cr.kind}`, (r.x + r.w / 2) * this.K, (r.y + r.h + 1) * this.K); }
    else this.words.hover(null);
    const box = (this.el ?? cv).getBoundingClientRect(), view = cv.getBoundingClientRect();
    const [x, y] = at ? [view.left + (at[0] / W) * view.width, view.top + (at[1] / H) * view.height] : [box.left, box.top];
    this.onHover(t, box.width ? (x - box.left) / box.width : 0, box.height ? (y - box.top) / box.height : 0);
  }

  private under(x: number, y: number): Target {
    const out: Target = { tile: tileAt(x, y) }, still = this.still, room = this.scene?.room;
    if (!still || !room) return out;
    const grown = (r: Rect, by: number) => ({ x: r.x - by, y: r.y - by, w: r.w + 2 * by, h: r.h + 2 * by });
    let front = -Infinity;
    for (const [id, a] of this.pets) if (inside(grown(a.rect(), 2), x, y) && a.c.y > front) [out.pet, front] = [id, a.c.y];
    for (const [id, b] of this.beasts) if (inside(grown(b.rect(), 3), x, y)) out.creature = id;
    if (this.train?.rects().some((r) => inside(r, x, y))) out.creature = this.train.cr.id;
    out.mark = this.marks.rects.find((m) => inside(grown(m.rect, 1), x, y))?.m;
    out.door = still.doors.find((d) => inside(d.rect, x, y))?.dir;
    if (this.display && inside(this.display.rect, x, y)) out.display = true;
    let best: Thing | null = null;
    for (const t of still.things.values()) if (inside(grown(t.rect, 1), x, y) && (!best || t.rect.w * t.rect.h < best.rect.w * best.rect.h)) best = t;   // the smallest thing under the pointer: a cup on a rug, not the rug
    const onTile = x >= OX && y >= OY && x < OX + FX * TILE && y < OY + FY * TILE;
    out.object = best?.name ?? (onTile ? Object.entries(room.objects).reverse().find(([, o]) => !o.fix?.sun && !o.wall && !o.on && (o.water ?? [o.pos]).some((t) => t[0] === out.tile[0] && t[1] === out.tile[1]))?.[0] : undefined);
    const spot = still.spots.find((s) => inside(grown(s.rect, 2), x, y)) ?? (onTile && !out.object ? still.spots.find((s) => s.pos[0] === out.tile[0] && s.pos[1] === out.tile[1]) : undefined);
    if (spot) [out.bit, out.bare] = [spot.bit, spot.bare || undefined];
    if (!out.object && !out.bit && !out.door) {   // nothing of the house's own there: a piece of the room's scenery, the smallest under the pointer
      let piece: Still["scenery"][number] | null = null;
      for (const s of still.scenery) if (inside(s.rect, x, y) && (!piece || s.rect.w * s.rect.h <= piece.rect.w * piece.rect.h)) piece = s;
      out.decor = piece?.sprite ?? (!out.pet && !out.creature && !out.mark ? (onTile ? room.paint?.floor && "room.floor" : room.paint?.wall && "room.wall") || undefined : undefined);   // a painted wall or floor says so
      const pt = out.decor || out.pet || out.creature || out.mark ? -1 : still.paints.findIndex((q) => inside(q.rect, x, y));   // SPEC-v3.5 §4.2: and what the pets painted, by whom
      if (pt >= 0) out.decor = `paint.${pt}`;
    }
    return out;
  }

  /** What a hover card can show about what is under the pointer (SPEC-v3.2 §3.3): its picture as a canvas (16 pixels
   *  or so: scale it up with `image-rendering: pixelated`), and in plain words what it is. Null if there is nothing to say. */
  describe(t: Target | null): Card | null {
    const card = this.card(t), at = card && t ? this.rectOf(t) : null;
    if (card && at) {   // where it is drawn, for whoever puts a card beside it
      const view = this.app.canvas.getBoundingClientRect(), box = (this.el ?? this.app.canvas).getBoundingClientRect(), k = view.width / W;
      card.rect = { x: view.left - box.left + at.x * k, y: view.top - box.top + at.y * k, w: at.w * k, h: at.h * k };
    }
    return card;
  }
  /** What a Target is drawn as, in the room's pixels. */
  private rectOf(t: Target): Rect | null {
    const still = this.still;
    return (t.pet && this.pets.get(t.pet)?.rect()) || (t.creature && (this.beasts.get(t.creature)?.rect() ?? (this.train?.cr.id === t.creature ? this.train.rects()[0] : null))) || (t.mark && this.marks.rects.find((m) => m.m === t.mark)?.rect) || (t.object && still?.things.get(t.object)?.rect)
      || (t.bit && still?.spots.find((s) => s.bit === t.bit && s.pos[0] === t.tile[0] && s.pos[1] === t.tile[1])?.rect) || (t.door && still?.doors.find((d) => d.dir === t.door)?.rect)
      || (t.display && this.display?.rect) || (t.decor && still?.scenery.find((s) => s.sprite === t.decor && inside(s.rect, OX + t.tile[0] * TILE + 8, OY + t.tile[1] * TILE + 8))?.rect) || null;
  }
  /** Order (SPEC-v3.3 §2), as plain lines for a hover card: what a thing that keeps things holds and how much room is
   *  left, where a thing put away is kept, where its home is when it is not there, and the named place it stands in. */
  private order(name: string, o: Obj): string[] | undefined {
    const { snap, room } = this.scene!, out: string[] = [], at = (p: Tile | undefined, q: Tile) => !!p && p[0] === q[0] && p[1] === q[1];
    const called = (n: string) => { const m = room.objects[n]?.made, d = m && drawnOf(m); return m?.called ? `“${m.called}”` : d ? `a ${d.color ? `${d.color} ` : ""}${d.kind}` : n; };
    const into = (n: string) => `${room.objects[n]?.store?.inside ? "in" : "on"} the ${n}`, place = (pos: Tile) => room.areas?.find((a) => a.tiles.some((t) => at(t, pos)))?.name;
    const whose = (id: unknown) => { const p = snap.pets.find((q) => q.id === id); return p ? p.label : "someone gone"; };
    const f = o.made?.found;   // SPEC-v3.6a §3: a find
    if (f) out.push(`from the ${f.from}: pulled up by ${whose(f.by)}${f.tier && f.tier !== "common" ? ` (${f.tier})` : ""}`);
    if (o.fix?.keepsake) out.push(`whose: ${whose(o.fix.keepsake)}'s`);   // SPEC-v3.5.12 §4
    if (o.fix?.memory) {   // a family's memory shelf: whose boxes stand on it
      const boxes = (o.store?.holds ?? []).map((n) => room.objects[n]?.fix?.keepsake).filter(Boolean).map(whose);
      out.push(boxes.length ? `keepsake boxes: ${boxes.slice(0, 8).join(", ")}${boxes.length > 8 ? ` and ${boxes.length - 8} more` : ""}` : "no keepsake box yet");
    } else if (o.fix?.shelf && o.store) {   // SPEC-v3.5.12 §1: a store fixture counts what it holds, by kind ("4 cushions, 2 blankets"), then names the ones on show
      const kinds = new Map<string, number>(), holds = o.store.holds;
      for (const n of holds) { const m = room.objects[n]?.made, k = m ? drawnOf(m).kind : n; kinds.set(k, (kinds.get(k) ?? 0) + 1); }
      const many = (k: string) => (/(s|x|ch|sh)$/.test(k) ? `${k}es` : /[^aeiou]y$/.test(k) ? `${k.slice(0, -1)}ies` : `${k}s`);
      const left = o.store.cap == null || o.fix.bits ? null : o.store.cap - holds.length;   // (a material crate keeps bits, not things)
      out.push(holds.length ? `holds: ${[...kinds].sort((a, b) => b[1] - a[1]).map(([k, n]) => (n > 1 ? `${n} ${many(k)}` : `1 ${k}`)).join(", ")}` : o.store.bits?.length || o.fix.bits ? "" : "holds nothing yet",
        ...(holds.length ? [`${o.store.inside ? "among them" : "on show"}: ${holds.slice(0, 3).map((n) => room.objects[n]?.made?.called ?? n).join(", ")}${holds.length > 3 && o.store.inside ? "…" : ""}`] : []),
        ...(left == null ? [] : [left > 0 ? `room for ${left} more` : "full"]));
    } else if (o.store) {
      const left = o.store.cap == null ? null : o.store.cap - o.store.holds.length;   // (a keepsake box has no limit)
      out.push(o.store.holds.length ? `holds: ${o.store.holds.map(called).join(", ")}` : "holds nothing yet", ...(left == null ? [] : [left > 0 ? `room for ${left} more` : "full"]));
    }
    if (stock(snap, o)) out.push(`stock: ${stock(snap, o)} ${o.fix!.bits} in the machine's stock`);   // SPEC-v3.5.12 §1: a material crate shows the house's stock
    if (o.store) {
      const bits = new Map<string, number>();   // loose bits tidied into it, counted: "bits: string x3, bell" (from the room as it is now: `o` is as old as the last redraw)
      for (const b of room.objects[name]?.store?.bits ?? []) bits.set(b, (bits.get(b) ?? 0) + 1);
      if (bits.size) out.push(`bits: ${[...bits].map(([b, n]) => (n > 1 ? `${b} x${n}` : b)).join(", ")}`);
    }
    const p = o.planted;   // SPEC-v3.4 §3.5: what is growing in it, and how it is doing ("a bean plant, in leaf")
    if (p) {
      const a = /^[aeiou]/.test(p.what) ? "an" : "a", ripe = "ripe: ready to pick";
      const plant = p.stage === "planted" ? `${a} ${p.what}` : /seed$/.test(p.what) ? "a plant" : `${a} ${p.what} plant`;
      const how = { planted: "just planted", sprout: "sprouting", leaves: "in leaf", ripe }[p.stage] ?? p.stage;
      out.push(`${plant}, ${p.wilted ? (p.stage === "ripe" ? `wilted, but ${ripe}` : "wilted") : how}`);
    }
    if (o.on) out.push(`kept ${into(o.on)}`);
    const h = o.home, there = h && h.room === room.id && (h.on ? o.on === h.on : !o.on && at(h.pos, o.pos));
    if (h && !there) {
      const spot = h.pos && place(h.pos);
      out.push(`its home is ${h.room !== room.id ? `in ${snap.rooms.find((r) => r.id === h.room)?.name ?? "another room"}` : h.on ? into(h.on) : spot ? `in the ${spot}` : "a place of its own on the floor here"}`);
    } else if (h) out.push("this is its home");
    const area = room.areas?.find((a) => (a.on ? a.on === name || a.on === o.on : !o.wall && a.tiles.some((t) => at(t, o.pos))));
    if (area) out.push(`part of the ${area.name}`);
    return out.length ? out : undefined;
  }
  /** SPEC-v3.6a §6: the pond's card: how many fish it has in words, today's catches, who is fishing; on the dock, the dock. */
  private pondCard(p: Pond, tile: Tile): Card {
    const snap = this.scene!.snap, name = (id: string) => snap.pets.find((q) => q.id === id)?.label ?? "someone";
    const an = (w: string) => (/^(a|an|the|some) /.test(w) ? w : `${/^[aeiou]/.test(w) ? "an" : "a"} ${w}`);
    const dock = p.dock?.tiles.some((d) => d[0] === tile[0] && d[1] === tile[1]);
    return { what: "fixture", title: dock ? "the dock" : "the pond", sprite: canvasOf(dock ? "pond.dock.end" : "bit.fish"), name: "pond", state: p.frozen ? "frozen over" : null,
             text: p.frozen ? `frozen over${p.holes.length ? `; ${p.holes.length > 1 ? `${p.holes.length} holes` : "a hole"} cut in the ice` : ""}` : p.says || "the water",
             notes: [...(p.says ? [`fish: ${p.says}`] : []), `catches today: ${p.today}`,
                     ...p.catches.slice(-4).reverse().map((c) => `${name(c.pet)} caught ${an(c.what)}${c.tier !== "common" ? ` (${c.tier})` : ""}`),
                     ...(p.fishers.length ? [`fishing now: ${p.fishers.map((f) => `${name(f.pet)} (${f.rod ? "with a rod" : "by paw"})`).join(", ")}`] : [])] };
  }
  private card(t: Target | null): Card | null {
    const sc = this.scene, still = this.still;
    if (!t || !sc || !still) return null;
    const { snap, room } = sc;
    const p = t.pet ? this.pets.get(t.pet) : null, b = t.creature ? this.beasts.get(t.creature) : null, th = t.object ? still.things.get(t.object) : null;
    if (p) return { what: "pet", title: p.pet.stage === "egg" ? p.pet.name ?? "an egg" : p.pet.label, sprite: petPortrait(p.pet.genome, p.pet.stage === "egg" ? "egg" : bodyStage(p.pet), 1), name: p.pet.name };
    if (b) {
      const owner = snap.pets.find((q) => q.id === b.cr.tame);
      return { what: "creature", title: b.cr.name ?? `a ${b.cr.kind}`, sprite: canvasOf(`creature.${b.cr.kind}`), name: b.cr.name ?? null, kind: b.cr.kind, owner: owner?.label ?? null, state: b.cr.doing,
               text: `${owner ? `${owner.label}'s ${b.cr.kind}` : `a ${b.cr.kind} of the house, nobody's`}: ${b.cr.doing}` };
    }
    if (t.creature && this.train?.cr.id === t.creature) {   // SPEC-v3.5.12 §5: the train: what it is doing, what is in its cart, who rides
      const cr = this.train.cr, n = new Map<string, number>(), rider = snap.pets.find((q) => q.id === cr.rider);
      for (const c of cr.cargo ?? []) n.set(c, (n.get(c) ?? 0) + 1);
      return { what: "creature", title: cr.name ?? "the train", sprite: TrainActor.picture(), name: cr.name ?? null, kind: "train", state: cr.doing, text: cr.doing,
               notes: [n.size ? `in the cart: ${[...n].map(([c, k]) => (k > 1 ? `${c} x${k}` : c)).join(", ")}` : "the cart is empty", ...(rider ? [`riding in the tram: ${rider.label}`] : [])] };
    }
    if (t.mark) return { what: "writing", title: t.mark.medium === "scratch" ? "words scratched on the wall" : "words in chalk", sprite: null, text: t.mark.text, maker: t.mark.by_name ?? null };
    if (th?.drawn) {
      const m = th.obj.made!, d = th.drawn, a = kind(d.kind)?.a ?? (/^[aeiou]/.test(d.color ?? d.kind) ? "an" : "a");
      return { what: "thing", title: `${d.color ? (/^[aeiou]/.test(d.color) ? "an" : "a") : a} ${d.color ? `${d.color} ` : ""}${d.kind}`, sprite: th.canvas, name: m.called ?? th.name, kind: d.kind, color: d.color, material: d.material,
               maker: snap.pets.find((q) => q.id === m.by)?.label ?? null, owner: m.owner_name, heirloom: !!m.heirloom, worn: m.worn, purpose: m.recipe.purpose,
               does: m.behavior ? `${m.behavior.do} when ${m.behavior.when}` : null, state: th.obj.state ?? null, notes: this.order(th.name, th.obj) };
    }
    if (th) return { what: th.obj.memorial ? "stone" : "fixture", title: th.obj.memorial ? "a memorial stone" : th.obj.build?.title ?? `the ${th.name}`, sprite: th.canvas, name: th.name, text: th.obj.memorial?.text, does: th.obj.says ?? null,
                     state: th.obj.fix?.light && !snap.power ? "dark: the power is out" : th.obj.state ?? null, notes: this.order(th.name, th.obj) };
    const pond = t.object && room.objects[t.object]?.water ? pondOf(snap, room) : null;
    if (pond) return this.pondCard(pond, t.tile);
    if (t.object && room.objects[t.object]) return { what: "fixture", title: `the ${t.object}`, sprite: null, name: t.object, state: room.objects[t.object].state ?? null, does: room.objects[t.object].says ?? null,
                                                     notes: this.order(t.object, room.objects[t.object]) };
    if (t.bit) {   // something to gather: what it is, and what a thing made of it can be
      const can = sc.hello?.bits[t.bit]?.can ?? [];
      return { what: "bit", title: `some ${t.bit}`, sprite: canvasOf(`bit.${t.bit}`), kind: t.bit, can, text: `${t.bare ? "it grows here: nothing to gather just now" : "a bit to gather"}${can.length ? `: something made of it can be ${can.join(" or ")}` : ""}` };
    }
    if (t.door) {
      const to = snap.rooms.find((r) => r.id === room.doors[t.door!]);
      return { what: "door", title: to?.type ? `the door to ${to.name}` : "a door nobody has been through", sprite: null, state: room.shut.includes(t.door) ? "stuck shut" : to?.type ? "open" : "shut",
               text: to?.type ? `it leads to ${to.name}` : "nobody knows yet what is behind it" };
    }
    if (t.display && this.display) {
      const more = [fishLine(snap, room.id), carLine(snap, room.id)].filter((l): l is string => !!l).map((l) => l.toLowerCase());
      return { what: "scenery", title: `the display: ${hhmm(snap.clock.hour)}, ${SKY[snap.weather] ?? snap.weather}`, sprite: null, text: this.display.line(snap), notes: more.length ? more : undefined };
    }
    const pt = t.decor?.startsWith("paint.") ? still.paints[Number(t.decor.slice(6))] : null;
    if (t.decor?.startsWith("paint.")) return pt ? { what: "scenery", title: paintTitle(pt.p), sprite: null, text: paintText(pt.p), rect: undefined } : null;
    if (t.decor === "room.wall" || t.decor === "room.floor") { const wall = t.decor === "room.wall"; return { what: "scenery", title: wall ? "the wall" : "the floor", sprite: null, text: `painted ${wall ? room.paint.wall : room.paint.floor}` }; }
    if (t.decor) return { what: "scenery", title: sceneryName(t.decor), sprite: canvasOf(t.decor), text: "part of the room" };
    return null;
  }
}
