// The room canvas (SPEC-v3 §10.2, §10.3). The world is data; this only draws the one room being looked at.
// Things that hold still are rebuilt when the snapshot changes them; pets, creatures, weather and light move every frame.
import { Application, Container, Graphics, Text } from "pixi.js";
import { PetBody } from "./pet";
import type { Genome, Look } from "./pet";
import { bit, creature, door, fixture, heirloomMark, stone, windowRect } from "./props";
import { backdrop, INK, mid, mix, PAD, ROOMS, skyColor, T } from "./rooms";
import { thingSvg } from "./things";
import { bodyStage } from "./types";
import type { Creature, Hello, Obj, PetV, RoomV, Snap } from "./types";

const FONT = "system-ui, -apple-system, sans-serif";
const S = 1.3;        // pets are drawn a little over the genome's size: four fit in a room and each still reads
const FEET = 18;      // a body stands with its feet this far below the middle of its tile
const NIGHT = 0x0b1030, WARM = 0xffd76a, ACCENT = 0xc9650f;

const CRISP = Math.min(4, devicePixelRatio * 2);   // words are drawn finer than the room, since they may be scaled up
export type Rect = { x: number; y: number; w: number; h: number };
const hit = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
/** What is under the pointer. */
export type Target = { tile: [number, number]; pet?: string; creature?: string; door?: string; object?: string; bit?: string };
export type Scene = { snap: Snap; room: RoomV; hello: Hello | null; selected: string | null; picked: string | null; replay: boolean };

/** A name on a small plate, so it reads on any floor. */
class Tag {
  c = new Container();
  w = 0;
  h = 0;
  private bg = new Graphics();
  private text: Text;
  private key = "";
  constructor(size = 12, private faint = false) {
    this.text = new Text({ text: "", resolution: CRISP, style: { fontFamily: FONT, fontSize: size, fontWeight: faint ? "500" : "600", fill: faint ? 0x3d4d47 : INK } });
    this.text.position.set(6, 2);
    this.c.addChild(this.bg, this.text);
  }
  /** `k` makes it bigger when the canvas is shown small, so the words stay a readable size on screen. */
  set(text: string, k: number, ring = false) {
    if (this.key === text + ring + k) return;
    this.key = text + ring + k;
    this.text.text = text;
    const [w, h] = [Math.ceil(this.text.width) + 12, Math.ceil(this.text.height) + 4];
    [this.w, this.h] = [w * k, h * k];
    this.c.scale.set(k);
    this.bg.clear().roundRect(0, 0, w, h, h / 2).fill({ color: 0xfffdf6, alpha: this.faint ? 0.72 : 0.9 });
    if (ring) this.bg.stroke({ width: 2, color: ACCENT });
  }
}

/** One pet on the floor: its body, and the small signs of how it is. */
class Actor {
  c = new Container();
  body = new PetBody();
  ring = new Graphics();
  dots = new Graphics();
  heart = new Graphics();
  bang = new Graphics();
  carry = new Graphics();
  tag = new Tag();
  bubble: Container | null = null;
  bubbleKey = "";
  bubbleSize = [0, 0];
  pet!: PetV;
  from = [0, 0];
  to = [0, 0];
  t0 = 0;
  dur = 1;
  seed = Math.random() * 6;
  drawn = "";
  carried = "";
  half = [20, 20];        // half its width and height on screen
  heartAt = -1e9;
  startleAt = -1e9;

  constructor() {
    for (const x of [-9, 0, 9]) this.dots.circle(x, 0, 3.2).fill(INK);
    this.heart.circle(-3.6, -3, 4.2).circle(3.6, -3, 4.2).poly([-7.4, -1, 7.4, -1, 0, 8.5]).fill(0xe2506a);
    this.bang.roundRect(-2, -12, 4, 10, 2).circle(0, 2.5, 2.2).fill(ACCENT);
    this.c.addChild(this.ring, this.body, this.carry, this.dots, this.heart, this.bang);
    this.heart.visible = this.bang.visible = false;
  }
}

export class Room {
  onClick: (t: Target) => void = () => {};
  onHover: (t: Target | null, fx: number, fy: number) => void = () => {};
  private app = new Application();
  private back = new Graphics();        // walls, floor, doors
  private props = new Container();      // fixtures, made things, bits, stones
  private fx = new Graphics();          // ripples, hums, notes, drips: on the floor, moving
  private actors = new Container();     // pets and creatures
  private shade = new Graphics();       // the dark
  private weather = new Graphics();     // rain, snow, heat in the rooms that have a sky; above the dark, so a wet night shows
  private glow = new Graphics();        // lights, above the dark
  private panes = new Graphics();       // windows: the only light in a power cut
  private flash = new Graphics();
  private tags = new Container();
  private bubbles = new Container();
  private size = [12, 8];
  private px = [0, 0];
  private scene: Scene | null = null;
  private built = "";
  private roomId = "";
  private pets = new Map<string, Actor>();
  private beasts = new Map<string, { g: Graphics; c: Creature; at: number[]; from: number[]; to: number[]; t0: number }>();
  private bouncing: Graphics[] = [];
  private lights: number[][] = [];      // [x, y, radius]
  private hums: number[][] = [];
  private loud: number[][] = [];
  private playing: number[][] = [];
  private water: number[][] = [];
  private windows: Obj[] = [];
  private doors: { rect: number[]; to: string; dir: string }[] = [];
  private things: { tag: Tag; at: number[]; must: boolean }[] = [];
  private placed: (Rect & { kind: string })[] = [];
  private dark = 0;
  private lastUpdate = 0;
  private pace = 2000;
  private tick = -1;
  private seenEvent = -1;
  private seenMoment = -1;
  private pointer: number[] | null = null;
  private k = 1;                        // how much bigger or smaller words are drawn, so they stay a steady size on screen

  async init(el: HTMLElement, w: number, h: number) {
    const [width, height] = [w * T + 2 * PAD, h * T + 2 * PAD];
    // sharp on a big screen too: the canvas is stretched by CSS, so draw it at about the size it will be shown
    const shown = Math.min(innerWidth - 300, ((innerHeight - 250) * width) / height);
    await this.app.init({ width, height, background: 0xcfc3ab, antialias: true, autoDensity: true,
                          resolution: Math.min(3, devicePixelRatio * Math.max(1, shown / width)) });
    el.append(this.app.canvas);
    this.size = [w, h];
    this.px = [width, height];
    this.shade.rect(0, 0, width, height).fill(NIGHT);
    this.flash.rect(0, 0, width, height).fill(0xffffff);
    this.flash.alpha = 0;
    this.glow.blendMode = "add";
    this.actors.sortableChildren = true;
    const stage = this.app.stage;
    stage.addChild(this.back, this.props, this.fx, this.actors, this.shade, this.weather, this.glow, this.panes, this.flash, this.tags, this.bubbles);
    stage.eventMode = "static";
    stage.hitArea = this.app.screen;
    stage.on("pointerdown", (e) => this.onClick(this.under(e.global.x, e.global.y)));
    stage.on("pointermove", (e) => this.point([e.global.x, e.global.y]));
    stage.on("pointerleave", () => this.point(null));
    this.app.ticker.add(() => this.frame(performance.now()));
    new ResizeObserver(() => {   // shown smaller than drawn (a narrow window, the drawer open): bigger words; on a big screen, smaller
      const k = Math.round(clamp(width / (this.app.canvas.clientWidth || width), 0.62, 1.9) * 10) / 10;
      if (k === this.k) return;
      [this.k, this.built] = [k, ""];
      for (const a of this.pets.values()) a.bubbleKey = "resized";
      if (this.scene) this.update(this.scene);
    }).observe(this.app.canvas);
  }

  /** Say what the pointer is over; again whenever a snapshot changes what is there. */
  private point(at: number[] | null = this.pointer) {
    this.pointer = at;
    const t = at && this.under(at[0], at[1]);
    this.app.canvas.style.cursor = t && (t.pet || t.object || t.door) ? "pointer" : "";
    this.onHover(t, (at?.[0] ?? 0) / this.px[0], (at?.[1] ?? 0) / this.px[1]);
  }

  /** A still picture of a body, for cards, the family tree and the life records. */
  picture(genome: Genome, stage: string, look: Look = {}): string {
    const body = new PetBody();
    body.draw(genome, stage, 70, false, look);
    body.scale.set(2);
    const url = (this.app.renderer.extract.canvas(body) as HTMLCanvasElement).toDataURL();
    body.destroy({ children: true });
    return url;
  }

  /** The name plates and speech bubbles as they are laid out now, for checking that none overlap. */
  labels() {
    return this.placed;
  }

  // ---- a snapshot arrives ----

  update(sc: Scene) {
    const now = performance.now(), { snap, room } = sc, fresh = room.id !== this.roomId;
    if (snap.tick !== this.tick) {   // a new moment of the house, not just a click: how long since the last one sets the walking pace
      if (!fresh) this.pace = clamp(now - this.lastUpdate, 120, 2600);
      [this.tick, this.lastUpdate] = [snap.tick, now];
    }
    this.scene = sc;
    this.roomId = room.id;
    const kind = ROOMS[room.type ?? ""] ?? ROOMS.nursery;
    const sky = skyColor(snap.clock.phase, snap.weather);
    const key = JSON.stringify([room.objects, room.spots, room.paint, room.doors, room.shut, room.wet, snap.clock.phase, snap.clock.season, snap.weather,
                                snap.power, sc.picked, snap.rooms.map((r) => r.type)]);
    if (key !== this.built) this.build(sc, sky);
    this.built = key;

    const base = ({ day: 0, dusk: 0.22, night: 0.5 } as Record<string, number>)[snap.clock.phase] ?? 0;
    const murk = snap.clock.phase === "day" ? ({ cloudy: 0.03, rain: 0.06, storm: 0.13, snow: 0.02 } as Record<string, number>)[snap.weather] ?? 0 : 0;
    this.dark = clamp(base + murk + kind.dim - (room.lit ? 0.2 : 0) + (snap.power || snap.clock.phase === "day" ? 0 : 0.2), 0, 0.7);   // a power cut by day changes nothing you can see
    this.shade.alpha = this.dark;

    // startles and hearts come from what just happened (§10.3)
    const event = snap.events.filter((e) => !e.room || e.room === room.id).at(-1);
    const startled = !fresh && this.seenEvent >= 0 && !!event && event.tick > this.seenEvent && event.kind !== "power back";
    this.seenEvent = Math.max(event?.tick ?? 0, fresh ? 0 : this.seenEvent);
    const nuzzlers = snap.moments.filter((m) => m.kind === "nuzzle" && m.n > this.seenMoment && m.room === room.id && (snap.tick - m.tick) * snap.tick_seconds < 20);
    this.seenMoment = snap.moments.at(-1)?.n ?? this.seenMoment;

    const here = snap.pets.filter((p) => p.room === room.id && !(p.stage === "dead" && p.buried));
    for (const [id, a] of this.pets) if (fresh || !here.some((p) => p.id === id)) {
      a.c.destroy({ children: true });
      a.tag.c.destroy({ children: true });
      a.bubble?.destroy({ children: true });
      this.pets.delete(id);
    }
    // The engine lets two pets share a tile; here they stand side by side. ponytail: a sideways nudge for a shared
    // tile or one directly above another, not a packing of the whole room.
    const aside = new Map<string, number>();
    const standing = here.filter((p) => p.stage !== "egg");
    for (const [i, p] of standing.entries()) for (const q of standing.slice(i + 1)) {
      const dx = q.pos[0] - p.pos[0], dy = Math.abs(q.pos[1] - p.pos[1]);
      if (Math.abs(dx) > 1 || dy > 1) continue;
      const d = (dx ? 0.15 : dy ? 0.22 : 0.3) * (dx < 0 ? -1 : 1);   // further apart the way they already are; same column: p left, q right
      aside.set(p.id, (aside.get(p.id) ?? 0) - d);
      aside.set(q.id, (aside.get(q.id) ?? 0) + d);
    }
    for (const p of here) {
      let a = this.pets.get(p.id);
      const goal = mid(p.pos);
      goal[0] += clamp(aside.get(p.id) ?? 0, -0.45, 0.45) * T;
      if (!a) {
        a = new Actor();
        a.c.position.set(goal[0], goal[1]);
        this.pets.set(p.id, a);
        this.actors.addChild(a.c);
        this.tags.addChild(a.tag.c);
      }
      if (goal[0] !== a.to[0] || goal[1] !== a.to[1]) [a.from, a.to, a.t0, a.dur] = [[a.c.x, a.c.y], goal, now, this.pace];
      a.pet = p;
      if (startled && p.stage !== "egg" && p.stage !== "dead" && !p.asleep) a.startleAt = now;
      if (nuzzlers.some((m) => m.pet === p.id || m.text.includes(p.label))) a.heartAt = now;
      this.dress(a, sc);
    }
    const beasts = snap.creatures.filter((c) => c.room === room.id);
    for (const [id, b] of this.beasts) if (fresh || !beasts.some((c) => c.id === id)) {
      b.g.destroy();
      this.beasts.delete(id);
    }
    for (const c of beasts) {
      let b = this.beasts.get(c.id);
      const goal = mid(c.pos);
      if (!b) {
        b = { g: new Graphics(), c, at: [goal[0], goal[1] + 8], from: [goal[0], goal[1] + 8], to: [goal[0], goal[1] + 8], t0: now };
        this.beasts.set(c.id, b);
        this.actors.addChild(b.g);
      }
      if (goal[0] !== b.to[0] || goal[1] + 8 !== b.to[1]) [b.from, b.to, b.t0] = [b.at, [goal[0], goal[1] + 8], now];
      b.c = c;
    }
    if (this.pointer) this.point();
  }

  /** A pet's body, name plate, what it carries and what it is saying, redrawn only when they change. */
  private dress(a: Actor, sc: Scene) {
    const p = a.pet, stage = bodyStage(p), dead = p.stage === "dead", g = p.genome;
    const look: Look = { tired: (p.levels?.energy ?? 0) >= 3, grey: stage === "elder" ? (p.old ? 0.85 : 0.55) : 0, dead };
    const comfort = Math.round((p.needs?.comfort ?? 60) / 10) * 10;
    const key = JSON.stringify([g, stage, comfort, p.asleep, look]);
    if (key !== a.drawn) {
      a.body.draw(g, stage, comfort, !!p.asleep, look);
      a.drawn = key;
      const size = ({ child: 18, youngling: 21, adult: 24, elder: 24 } as Record<string, number>)[stage] ?? 15;
      const [w, h] = stage === "egg" ? [size * 0.85, size * 1.15] : [size, size * g.stretch];
      a.half = dead ? [h * S, w * S] : [w * S, h * S];
    }
    const chosen = sc.selected === p.id;
    a.ring.clear();
    if (chosen) a.ring.ellipse(0, FEET + 1, a.half[0] + 8, 8).stroke({ width: 2.5, color: ACCENT, alpha: 0.9 });
    a.tag.set(p.stage === "egg" ? p.name ?? "an egg" : p.label, this.k, chosen);
    a.tag.c.alpha = dead ? 0.75 : 1;

    const carried = (p.carrying ?? []).join();
    if (carried !== a.carried) {
      a.carried = carried;
      a.carry.clear();
      (p.carrying ?? []).slice(0, 3).forEach((k, i) => bit(a.carry, k, sc.hello?.bits[k]?.looks, a.half[0] + 9, FEET - 12 - i * 14, 0.8));
    }
    const said = p.said && (sc.snap.tick - p.said.tick) * sc.snap.tick_seconds <= (sc.replay ? 30 : 16) ? p.said : null;
    const bubbleKey = said ? `${said.tick}${said.text}` : "";
    if (bubbleKey !== a.bubbleKey) {
      a.bubbleKey = bubbleKey;
      a.bubble?.destroy({ children: true });
      a.bubble = null;
      if (said) {
        const words = new Text({ text: said.text.length > 150 ? said.text.slice(0, 148) + "…" : said.text, resolution: CRISP,
                                 style: { fontFamily: FONT, fontSize: 13, fill: INK, wordWrap: true, wordWrapWidth: 190, lineHeight: 17 } });
        const to = said.to_name ? new Text({ text: `→ ${said.to_name}`, resolution: CRISP, style: { fontFamily: FONT, fontSize: 11, fontWeight: "700", fill: 0xa8500a } }) : null;   // who it is for (§10.3)
        to?.position.set(9, 5);
        words.position.set(9, to ? 20 : 6);
        const [w, h] = [Math.ceil(Math.max(words.width, to?.width ?? 0)) + 18, Math.ceil(words.height) + (to ? 27 : 13)];
        const box = new Graphics().roundRect(0, 0, w, h, 9).fill(0xffffff).stroke({ width: 1.5, color: INK });
        a.bubble = new Container();
        a.bubble.addChild(box, words);
        if (to) a.bubble.addChild(to);
        a.bubble.scale.set(this.k);
        a.bubbleSize = [w * this.k, h * this.k];
        this.bubbles.addChild(a.bubble);
      }
    }
  }

  /** Everything in the room that holds still between snapshots. */
  private build(sc: Scene, sky: number) {
    const { snap, room, hello } = sc, [w, h] = this.size, type = room.type ?? "nursery";
    const env = { phase: snap.clock.phase, power: snap.power, season: snap.clock.season };
    backdrop(this.back, type, room.id, w, h, { ...room.paint, season: snap.clock.season, sky, snow: snap.weather === "snow" });
    this.app.renderer.background.color = ROOMS[type]?.wall ?? 0xcfc3ab;
    this.doors = Object.entries(room.doors).map(([dir, to]) => {
      const there = snap.rooms.find((r) => r.id === to);
      const how = room.shut.includes(dir) ? "shut" : there?.type ? "open" : "unknown";
      return { rect: door(this.back, dir, snap.door_tiles[dir], how, ROOMS[there?.type ?? ""]?.floor ?? 0, w, h), to, dir };
    });

    for (const c of this.props.removeChildren()) c.destroy({ children: true });
    for (const t of this.things) t.tag.c.destroy({ children: true });
    [this.bouncing, this.lights, this.hums, this.loud, this.playing, this.water, this.windows, this.things] = [[], [], [], [], [], [], [], []];
    const under = new Graphics(), over = new Graphics(), made: Container[] = [];
    const flat = (n: string, o: Obj) => (o.fix?.water || o.fix?.sun || /rug|blanket/.test(n) ? 0 : 1);
    const all = Object.entries(room.objects).sort(([an, a], [bn, b]) => flat(an, a) - flat(bn, b) || a.pos[1] - b.pos[1]);
    if (room.wet) {   // a leak: water standing on the floor
      const r = this.rnd(room.id);
      for (let i = 0; i < 7; i++) under.ellipse(PAD + 30 + r() * (w * T - 60), PAD + 20 + r() * (h * T - 40), 26 + r() * 30, 9 + r() * 9).fill({ color: 0x5f9fc4, alpha: 0.42 });
    }
    for (const [name, o] of all) {
      const [x, y] = mid(o.pos);
      if (name === sc.picked) under.roundRect(x - T / 2 + 2, y - T / 2 + 2, T - 4, T - 4, 10).stroke({ width: 3, color: ACCENT });
      if (o.made) {   // something a pet made: drawn from its recipe, showing what it has been taught to do (§7)
        const m = o.made, doing = m.active ? m.behavior?.do ?? "" : "", worn = m.worn;
        if ((o.state === "on" || doing === "glow") && snap.power) this.lights.push([x, y, 58]);
        if (doing === "dim") under.circle(x, y, 46).fill({ color: NIGHT, alpha: 0.22 });
        if (doing === "hum") this.hums.push([x, y]);
        const recolor = doing.startsWith("change_color:") ? doing.split(":")[1] : undefined;
        const drawn = new Graphics().svg(`<svg xmlns="http://www.w3.org/2000/svg">${thingSvg(m.recipe, 0, 0, recolor)}</svg>`);
        drawn.position.set(x, y);
        drawn.alpha = worn.length ? 0.82 : 1;
        if (doing === "bounce") this.bouncing.push(drawn);
        made.push(drawn);
        // how it has worn (§6.1): damp from the cellar floor, dust from the attic, the moth's holes
        if (worn.includes("damp")) for (const dx of [-12, 0, 11]) over.moveTo(x + dx, y + 12).quadraticCurveTo(x + dx + 4, y + 20, x + dx, y + 21).quadraticCurveTo(x + dx - 4, y + 20, x + dx, y + 12).fill({ color: 0x5f9fc4, alpha: 0.85 });
        if (worn.includes("dusty")) { const r = this.rnd(name); for (let i = 0; i < 12; i++) over.circle(x - 20 + r() * 40, y - 20 + r() * 34, 1.6).fill({ color: 0xd9d4c6, alpha: 0.9 }); }
        if (worn.includes("eaten")) for (const [dx, dy] of [[-9, -6], [7, 3], [-2, 9]]) over.circle(x + dx, y + dy, 3).fill(ROOMS[type]?.floor ?? 0xe6dcc8).stroke({ width: 1, color: INK, alpha: 0.5 });
        if (m.heirloom) heirloomMark(over, x + 19, y - 24);
        const tag = new Tag(10, true);
        tag.set(m.called ?? name, this.k);
        this.things.push({ tag, at: [x, y + 25], must: false });
      } else if (o.memorial) {
        stone(over, x, y);
        const tag = new Tag(11, true);
        tag.set(snap.pets.find((p) => p.id === o.memorial!.pet)?.label ?? name.replace(/^stone for (.)/, (_, c: string) => c.toUpperCase()), this.k);
        this.things.push({ tag, at: [x, y + 21], must: true });
      } else if (o.fix?.window) {
        this.windows.push(o);
      } else if (o.water) {
        for (const [tx, ty] of o.water) under.roundRect(PAD + tx * T - 3, PAD + ty * T - 3, T + 6, T + 6, 16).fill(0x9fb5ad);
        for (const [tx, ty] of o.water) under.roundRect(PAD + tx * T + 3, PAD + ty * T + 3, T - 6, T - 6, 14).fill(mix(0x4f9fc0, sky, 0.3));
        const r = this.rnd(room.id + name);
        for (let i = 0; i < 4; i++) {
          const [tx, ty] = o.water[Math.floor(r() * o.water.length)], [lx, ly] = [PAD + tx * T + 14 + r() * 28, PAD + ty * T + 14 + r() * 28];
          under.circle(lx, ly, 8).fill(0x4f9b63).stroke({ width: 1, color: INK, alpha: 0.5 }).poly([lx, ly, lx + 8, ly - 3, lx + 8, ly + 3]).fill(mix(0x4f9fc0, sky, 0.3));
        }
        this.water = o.water;
      } else if (o.fix?.sun) {   // the attic's shaft of sun (§6.1): a warm patch that crosses the floor with the hour
        const clear = snap.weather === "clear" || snap.weather === "heat";
        const [col, a] = snap.clock.phase === "night" ? [0xbfd0ff, 0.1] : [0xfff0b0, snap.clock.phase === "dusk" ? 0.25 : clear ? 0.62 : 0.22];
        const top = windowRect(this.windows[0] ?? { pos: [5, 0] });
        under.poly([top[0] + 8, PAD, top[0] + top[2] - 8, PAD, x + 40, y + 6, x - 34, y + 6]).fill({ color: col, alpha: a * 0.3 });
        under.poly([x - 30, y - 22, x + 44, y - 22, x + 30, y + 24, x - 44, y + 24]).fill({ color: col, alpha: a });
      } else {
        fixture(under, name, x, y, o, env);
        if (o.fix?.light && o.state === "on" && snap.power) this.lights.push([x, y - 8, 96]);
        if (o.fix?.loud) this.loud.push([x, y]);
        if (o.state === "playing") this.playing.push([x, y]);
      }
    }
    for (const s of room.spots) {
      const [x, y] = mid(s.pos);
      over.ellipse(x, y + 16, 9, 2.5).fill({ color: INK, alpha: 0.12 });
      bit(over, s.bit, hello?.bits[s.bit]?.looks, x, y + 8);
    }
    this.props.addChild(under, ...made, over);
    for (const t of this.things) this.tags.addChildAt(t.tag.c, 0);
  }

  private rnd(key: string) {
    let seed = [...key].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) % 4294967296, 7);
    return () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);
  }

  // ---- every frame ----

  private frame(now: number) {
    const sc = this.scene;
    if (!sc) return;
    const { snap, room } = sc, [w, h] = this.size, [W, H] = [w * T, h * T];
    const storm = snap.weather === "storm", slot = Math.floor(now / 5200), at = slot * 5200 + ((slot * 7919) % 3800);
    const flashing = storm && ((now > at && now < at + 90) || (now > at + 170 && now < at + 250));
    const sky = ROOMS[room.type ?? ""]?.sky;

    for (const a of this.pets.values()) this.animate(a, now);   // each sets its zIndex to its y: whoever is lower on the floor is in front
    for (const b of this.beasts.values()) {
      const k = Math.min(1, (now - b.t0) / this.pace), moth = b.c.kind === "moth";
      const [x, y] = (b.at = [b.from[0] + (b.to[0] - b.from[0]) * k, b.from[1] + (b.to[1] - b.from[1]) * k]);   // a moth flutters about where it is
      b.g.position.set(x + (moth ? Math.sin(now / 210) * 7 : 0), y + (moth ? Math.cos(now / 170) * 6 - 22 : 0));
      b.g.zIndex = y;
      if (Math.abs(b.to[0] - b.from[0]) > 1) b.g.scale.x = b.to[0] > b.from[0] && !moth ? -1 : 1;
      creature(b.g, b.c.kind, now, k < 1 && (b.to[0] !== b.from[0] || b.to[1] !== b.from[1]));
      if (b.c.carry) bit(b.g, b.c.carry, sc.hello?.bits[b.c.carry]?.looks, 0, -14, 0.75);
    }
    for (const b of this.bouncing) b.pivot.y = Math.abs(Math.sin(now / 180)) * 9;

    // on the floor: water moving, things humming, notes in the air, a draught, drips
    const f = this.fx.clear();
    this.water.slice(0, 5).forEach(([tx, ty], i) => {
      const k = ((now / 2600 + i * 0.37) % 1), [x, y] = [PAD + tx * T + T / 2 + Math.sin(i * 5) * 12, PAD + ty * T + T / 2 + Math.cos(i * 3) * 10];
      f.ellipse(x, y, 4 + k * 16, 2 + k * 7).stroke({ width: 1.5, color: 0xffffff, alpha: 0.5 * (1 - k) });
    });
    for (const [x, y] of this.hums) for (const i of [0, 1, 2]) {
      const k = (now / 1800 + i / 3) % 1;
      f.circle(x, y, 26 + k * 22).stroke({ width: 1.5, color: INK, alpha: 0.3 * (1 - k) });
    }
    {   // notes rise from whatever is playing, and from the instruments while the room still rings (§6.1)
      const from = [...this.playing, ...(room.sounding ? (this.loud.length ? this.loud : [[PAD + W / 2, PAD + H / 2]]) : [])];
      from.forEach(([x, y], n) => [0, 1].forEach((i) => {
        const k = (now / 2200 + i / 2 + n * 0.3) % 1, [nx, ny] = [x + 14 + i * 12 + Math.sin(k * 6) * 5, y - 22 - k * 34];
        f.circle(nx, ny, 3.5).rect(nx + 2.2, ny - 13, 1.6, 13).fill({ color: INK, alpha: 0.75 * (1 - k) });
      }));
    }
    if (room.cold) for (let i = 0; i < 4; i++) {   // a draught: pale wisps crossing the floor
      const k = (now / 3400 + i / 4) % 1, x = PAD + k * W, y = PAD + H * (0.2 + i * 0.2);
      f.moveTo(x - 40, y).bezierCurveTo(x - 20, y - 12, x - 10, y + 12, x + 10, y).stroke({ width: 2.5, color: 0xdfeeff, alpha: 0.6 * Math.sin(k * Math.PI) });
    }
    if (room.wet) for (const i of [0, 1]) {
      const k = (now / 1300 + i * 0.5) % 1, x = PAD + W * (0.3 + i * 0.37);
      f.ellipse(x, PAD + k * k * H * 0.5, 2, 4).fill({ color: 0x5f9fc4, alpha: 0.8 });
    }
    if (room.type === "attic") {   // dust in the air
      for (let i = 0; i < 16; i++) f.circle(PAD + ((i * 0.618 * W + now * 0.004 * (1 + (i % 3))) % W), PAD + ((i * 0.37 * H + Math.sin(now / 1900 + i) * 14 + H) % H), 1.4);
      f.fill({ color: 0xfff6d8, alpha: 0.5 });
    }

    // weather where there is a sky: all of it in the garden, on the roof under glass (§10.2)
    const wx = this.weather.clear(), wet = snap.weather === "rain" || storm;
    if (sky && wet) {
      const n = (sky === "open" ? 70 : 34) * (storm ? 1.5 : 1), len = sky === "open" ? 15 : 8;
      for (let i = 0; i < n; i++) {
        const x = PAD + ((i * 0.618034 * W + now * 0.06) % W), y = PAD + ((i * 0.3779 * H + now * (0.55 + (i % 5) * 0.04)) % H);
        wx.moveTo(x, y).lineTo(x - len * 0.3, y + len);
      }
      wx.stroke({ width: 1.5, color: sky === "open" ? 0xdcebf5 : 0xffffff, alpha: (sky === "open" ? 0.6 : 0.34) * (1 - this.dark * 0.5) });
    } else if (sky && snap.weather === "snow") {
      for (let i = 0; i < (sky === "open" ? 60 : 28); i++) wx.circle(PAD + ((i * 0.618034 * W + Math.sin(now / 900 + i) * 9 + W) % W), PAD + ((i * 0.3779 * H + now * (0.03 + (i % 4) * 0.006)) % H), 1.5 + (i % 3) * 0.6);
      wx.fill({ color: 0xffffff, alpha: (sky === "open" ? 0.95 : 0.55) * (1 - this.dark * 0.4) });
    } else if (sky && snap.weather === "heat" && snap.clock.phase === "day") {
      for (let j = 0; j < 6; j++) {
        const y = PAD + H - ((now * 0.012 + (j * H) / 6) % H);
        wx.moveTo(PAD, y);
        for (let x = 0; x <= W; x += 24) wx.lineTo(PAD + x, y + Math.sin(x / 38 + now / 500 + j) * 4);
      }
      wx.stroke({ width: 4, color: 0xfff3c4, alpha: 0.2 });
    }

    // light: lamps glow above the dark; windows show the sky whatever the power is doing
    const gl = this.glow.clear();
    for (const [x, y, r] of this.lights) {
      const flick = 1 + Math.sin(now / 130 + x) * 0.015;
      for (let i = 0; i < 9; i++) gl.circle(x, y, r * (1 - i / 10) * flick).fill({ color: WARM, alpha: 0.045 * (0.25 + this.dark * 1.4) });   // rings, for a soft edge
    }
    const pn = this.panes.clear(), pane = flashing ? 0xffffff : skyColor(snap.clock.phase, snap.weather);
    for (const o of this.windows) {
      const [x, y, ww, hh] = windowRect(o), roof = ww > hh;
      pn.rect(x, y, ww, hh).fill(pane);
      if (snap.clock.phase === "night" && !wet && snap.weather !== "snow") pn.circle(x + ww * 0.7, y + hh * 0.3, 2.5).fill(0xf6f0d0).circle(x + ww * 0.25, y + hh * 0.6, 1).circle(x + ww * 0.5, y + hh * 0.2, 1).fill(0xffffff);
      if (wet) {
        for (let i = 0; i < 5; i++) { const k = (now / 420 + i * 0.23) % 1, px = x + ((i * 0.4 + 0.1) % 1) * ww, py = y + k * (hh - 7); pn.moveTo(px, py).lineTo(px - 2, py + 7); }
        pn.stroke({ width: 1.3, color: 0xffffff, alpha: 0.75 });
      } else if (snap.weather === "snow") {
        for (let i = 0; i < 5; i++) pn.circle(x + 3 + ((i * 0.37) % 1) * (ww - 6), y + 2 + ((now / 2600 + i * 0.21) % 1) * (hh - 4), 1.4);
        pn.fill(0xffffff);
      } else if (snap.weather === "heat" && snap.clock.phase === "day") {
        pn.circle(x + ww * 0.5, y + hh * 0.35, 4 + Math.sin(now / 300) * 0.6).fill(0xfff3b0);
      }
      roof ? pn.rect(x + ww / 2 - 1, y, 2, hh).fill(INK) : pn.rect(x, y + hh / 2 - 1, ww, 2).fill(INK);
      pn.rect(x, y, ww, hh).stroke({ width: 3, color: INK });
      if (o.state === "open") {   // pushed open into the room
        roof ? pn.poly([x, y + hh, x + ww, y + hh, x + ww - 8, y + hh + 12, x + 8, y + hh + 12]).fill({ color: 0xffffff, alpha: 0.7 }).stroke({ width: 2, color: INK })
             : pn.poly([x + ww, y, x + ww + 14, y + 8, x + ww + 14, y + hh - 8, x + ww, y + hh]).fill({ color: 0xffffff, alpha: 0.7 }).stroke({ width: 2, color: INK });
      }
    }
    this.flash.alpha = flashing ? (sky ? 0.38 : this.windows.length ? 0.1 : 0) : 0;
    this.layout();
  }

  /** Display only: walk between where the last two snapshots put it, and show how it is in how it holds itself. */
  private animate(a: Actor, now: number) {
    const p = a.pet, egg = p.stage === "egg", dead = p.stage === "dead", elder = p.stage === "elder";
    let k = Math.min(1, (now - a.t0) / a.dur);
    const far = Math.hypot(a.to[0] - a.from[0], a.to[1] - a.from[1]), moving = k < 1 && far > 2;
    if (elder) k = k * k * (3 - 2 * k);   // an elder shuffles: slow to start, slow to stop
    a.c.position.set(a.from[0] + (a.to[0] - a.from[0]) * k, a.from[1] + (a.to[1] - a.from[1]) * k);
    a.c.zIndex = a.c.y;
    const b = a.body, levels = p.levels, energy = p.needs?.energy ?? 50;
    const still = dead || egg || !!p.asleep;
    const content = !!levels && Math.max(...Object.values(levels)) <= 1;
    const uneasy = !!levels && (levels.comfort >= 3 || !!p.weak);
    const slow = elder ? 1.6 : 1;
    const hop = moving && !still ? Math.abs(Math.sin(now / (130 * slow))) * (elder ? 2.5 : 5) : 0;
    const bob = still ? 0 : Math.sin(now / ((900 - energy * 5) * slow) + a.seed) * (content ? 4.5 : 2.5);
    const jump = now - a.startleAt < 520 ? Math.sin(((now - a.startleAt) / 520) * Math.PI) * 16 : 0;
    const lift = Math.max(a.half[1] - FEET, a.half[1] - a.c.y + 3);   // feet on the tile, and never out through the top wall
    b.position.set(uneasy && !still ? Math.sin(now / 35) * 1.5 : 0, -lift + bob - hop - jump);
    const squash = still ? 0 : Math.sin(now / 260 + a.seed) * p.genome.wobble * 0.07;
    b.scale.set(S * (1 + squash), S * (1 - squash));
    b.rotation = dead ? Math.PI / 2 : egg ? Math.sin(now / ((p.hatches_in ?? 99) < 20 ? 90 : 420) + a.seed) * ((p.hatches_in ?? 99) < 20 ? 0.16 : 0.07)
      : elder ? (p.old ? 0.11 : 0.07) : 0;   // an elder stoops a little
    a.c.alpha = dead ? 1 - 0.8 * (p.fade ?? 0) : 1;
    const top = b.y - (dead ? a.half[0] : a.half[1]);
    a.dots.visible = !!p.thinking && !p.asleep && !dead;
    a.dots.position.set(a.half[0] + 16, top + 8);   // by its head, clear of where a name plate or a bubble may go
    a.dots.alpha = 0.35 + 0.35 * (1 + Math.sin(now / 250));
    const hk = (now - a.heartAt) / 5000;
    a.heart.visible = hk < 1;
    a.heart.position.set(a.half[0] * 0.6, top - 6 - hk * 22);
    a.heart.alpha = Math.min(1, 3 * (1 - hk));
    a.heart.scale.set(1 + Math.sin(now / 160) * 0.1);
    a.bang.visible = now - a.startleAt < 1400;
    a.bang.position.set(-a.half[0] * 0.5, top - 8 - jump);
  }

  /** Name plates and speech bubbles, placed so none sits on another (§10.7). A pet's plate always shows and moves
   *  out of the way; a made thing's small plate gives way and hides. */
  private layout() {
    const [W, H] = this.px, placed: (Rect & { kind: string })[] = [];
    // the page's own plates over the room (its name, the moment banner) take their space first
    const view = this.app.canvas.getBoundingClientRect(), s = view.width ? W / view.width : 1;
    for (const id of ["roomName", "banner"]) {
      const e = document.getElementById(id);
      if (!e || e.hidden) continue;
      const b = e.getBoundingClientRect();
      placed.push({ x: (b.left - view.left) * s, y: (b.top - view.top) * s, w: b.width * s, h: b.height * s, kind: "page" });
    }
    const actors = [...this.pets.values()].sort((a, b) => a.c.y - b.c.y || a.c.x - b.c.x);
    const bodies = actors.map((a) => ({ x: a.c.x - a.half[0], y: a.c.y + a.body.y - a.half[1], w: 2 * a.half[0], h: 2 * a.half[1], a }));
    const free = (r: Rect, me?: Actor) => !placed.some((q) => hit(q, r)) && !bodies.some((q) => q.a !== me && hit(q, r));
    const put = (c: Container, r: Rect, kind: string) => {
      c.position.set(Math.round(r.x), Math.round(r.y));
      placed.push({ ...r, kind });
    };
    for (const t of this.things.filter((t) => t.must)) put(t.tag.c, { x: clamp(t.at[0] - t.tag.w / 2, 2, W - t.tag.w - 2), y: t.at[1], w: t.tag.w, h: t.tag.h }, "stone");
    for (const a of actors) {
      const { w, h } = a.tag, x = clamp(a.c.x - w / 2, 2, W - w - 2);
      const below = { x, y: Math.min(a.c.y + FEET + 5, H - h - 2), w, h }, above = { x, y: Math.max(2, a.c.y + a.body.y - a.half[1] - h - 4), w, h };
      const r = free(below, a) ? below : free(above, a) ? above : below;
      for (let n = 0; n < 8 && placed.some((q) => hit(q, r)); n++) {   // nowhere clear: step down past whatever plate is in the way
        const q = placed.find((q) => hit(q, r))!;
        r.y = q.y + q.h + 2 + r.h > H ? q.y - r.h - 2 : q.y + q.h + 2;
      }
      put(a.tag.c, r, "pet");
    }
    for (const t of this.things.filter((t) => !t.must)) {
      const r = { x: clamp(t.at[0] - t.tag.w / 2, 2, W - t.tag.w - 2), y: Math.min(t.at[1], H - t.tag.h - 2), w: t.tag.w, h: t.tag.h };
      t.tag.c.visible = free(r);
      if (t.tag.c.visible) put(t.tag.c, r, "thing");
    }
    for (const a of actors) if (a.bubble) {
      const [w, h] = a.bubbleSize;
      const r = { x: clamp(a.c.x - w / 2, 3, W - w - 3), y: a.c.y + a.body.y - a.half[1] - h - 10, w, h };
      const others = () => placed.find((q) => q.kind !== "thing" && hit(q, r));
      for (let n = 0; n < 6 && others(); n++) r.y = others()!.y - h - 4;   // up, out of the way of plates and other bubbles
      if (r.y < 3) {   // no room above: beside it instead
        r.y = clamp(a.c.y + a.body.y - h / 2, 3, H - h - 3);
        r.x = a.c.x + a.half[0] + 12 + w < W ? a.c.x + a.half[0] + 12 : a.c.x - a.half[0] - 12 - w;
        for (let n = 0; n < 6 && others(); n++) r.y = others()!.y + others()!.h + 4;
      }
      put(a.bubble, r, "bubble");
    }
    this.placed = placed;
  }

  // ---- the pointer ----

  private under(x: number, y: number): Target {
    const [w, h] = this.size, room = this.scene?.room;
    const tile: [number, number] = [clamp(Math.floor((x - PAD) / T), 0, w - 1), clamp(Math.floor((y - PAD) / T), 0, h - 1)];
    const out: Target = { tile };
    if (!room) return out;
    const inside = (r: number[]) => x >= r[0] && x <= r[0] + r[2] && y >= r[1] && y <= r[1] + r[3];
    for (const [id, a] of this.pets) if (Math.abs(x - a.c.x) < a.half[0] + 3 && y > a.c.y + a.body.y - a.half[1] - 3 && y < a.c.y + FEET + 4) out.pet = id;
    for (const [id, b] of this.beasts) if (Math.hypot(x - b.g.x, y - b.g.y) < 20) out.creature = id;
    const d = this.doors.find((d) => inside(d.rect));
    if (d) out.door = d.dir;
    const win = Object.entries(room.objects).find(([, o]) => o.fix?.window && inside(windowRect(o)));
    const obj = win ?? Object.entries(room.objects).reverse().find(([, o]) => !o.fix?.sun && (o.water ?? [o.pos]).some((t) => t[0] === tile[0] && t[1] === tile[1]));
    if (obj && (win || (x >= PAD && y >= PAD && x <= PAD + w * T && y <= PAD + h * T))) out.object = obj[0];
    out.bit = room.spots.find((s) => s.pos[0] === tile[0] && s.pos[1] === tile[1])?.bit;
    return out;
  }
}
