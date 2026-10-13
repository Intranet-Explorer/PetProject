// Everything in the room that holds still between snapshots, built from the room type's layout and the snapshot
// (SPEC-v3.2 §3, §4): floor, walls, decor in layers, doors, fixtures in their states, made things by kind, bits to
// gather, memorial stones. Rebuilt only when one of them changes.
import { Container, Graphics, Sprite } from "pixi.js";
import type { Texture } from "pixi.js";
import { composeThing, inventedKind } from "../parts";
import { PALETTE } from "../things";
import type { Part, Recipe } from "../things";
import type { Made, Obj, Painted, RoomV, Snap, Tile } from "../types";
import { paintOn, paintRect } from "./built";
import { addSprite, canvasOf, def, fromCanvas, fromParts, has, kind, pick, size, tex } from "./assets";
import type { Layout } from "./assets";
import { FAMILY, tagCanvas } from "./bubbles";
import { fxTexture } from "./fx";
import { COLS, corner, FX, FY, H, idx, OX, OY, onFloor, ROWS, seeded, TILE, W } from "./geom";
import type { Rect } from "./geom";
import { grid } from "./path";
import type { Grid } from "./path";
import { seasonal } from "./season";
import { hslInt, tinted } from "./tint";

/** A made thing as it is drawn: its kind's sprite, its colour, its size (1 to 3). */
export type Drawn = { kind: string; sprite: string; color: string | null; size: number; material: string };
/** One thing standing in the room (a fixture, a made thing, a stone). `x`, `y`: the middle of its foot. */
/** `sprite`: the name of its picture. `stir`: a pet is at it just now (1 playing with it: it bounces; 2 fiddling: it
 *  shakes; 3 it has been picked up to be put away: not shown), set by the room at every snapshot. */
export type Thing = { name: string; obj: Obj; s: Sprite; x: number; y: number; rect: Rect; canvas: HTMLCanvasElement; texture: Texture; drawn: Drawn | null; scale: number; sprite: string;
  wall: boolean; on: boolean; glassy: boolean; bob: boolean; bounce: boolean; noisy: boolean; fragrant: boolean; heirloom: boolean; extra: Sprite[]; stir: number };   // `extra`: what is drawn on it and goes where it goes (a plant in a pot)
/** Where a thing put away on another stands (SPEC-v3.3 §2): its foot, its depth, and whether that is up on the wall. */
type Slot = { x: number; y: number; z: number; wall: boolean };
export type Lamp = { x: number; y: number; r: number; color: number[]; made: boolean };
export type Door = { dir: string; to: string; rect: Rect; tile: Tile };
/** A bit to gather, as drawn. `bare`: this is where the room grows it, and it has been picked: nothing to gather just now. */
export type Spot = { bit: string; pos: Tile; rect: Rect; s: Sprite; bare: boolean };

/** SPEC-v3.2 §3.2: what a thing made before kinds (from parts) is drawn as, by view/assets/kinds-from-parts.json. */
export function kindOf(r: Recipe): { kind: string; color: string | null; size: number } {
  if (r.kind) return { kind: r.kind, color: r.color ?? null, size: r.size ?? 2 };
  const parts = r.parts ?? [], t = fromParts(), big = parts.reduce<Part | null>((a, p) => (!a || p.size > a.size ? p : a), null);
  const shapes = new Set(parts.map((p) => p.shape));
  const k = parts.length >= 3 && t.many ? (t.many.hanging?.includes(r.material) ? t.many.then : t.many.else)
    : parts.length === 2 && shapes.size === 2 && t.pair?.[r.material] ? t.pair[r.material]
    : big ? t.material?.[r.material]?.[big.shape] ?? t.shape?.[big.shape] : undefined;
  return { kind: k ?? "thing", color: big?.color ?? r.color ?? null, size: big?.size ?? 2 };
}
export function drawnOf(m: Made): Drawn {
  const k = kindOf(m.recipe), inv = inventedKind(k.kind);
  if (inv) return { ...k, color: null, sprite: addSprite(`invented.${k.kind}`, composeThing(inv)), material: m.recipe.material };   // SPEC-v3.5 §3: put together from its parts, each in its own colour
  return { ...k, sprite: kind(k.kind)?.sprite ?? `kind.${k.kind}`, material: m.recipe.material };
}

const PLAIN = { floor: 0xd8c39a, wall: 0xa98f6f, trim: 0x6d5a48 };
const SIZES = [0.75, 1, 1.25];
const counts = new Map<string, Texture>();   // the small numbers on chests and crates, made once each
/** The colour a named place in a room is tinted (SPEC-v3.3 §2.3): the same for the same name, in every room. */
export const areaColor = (name: string) => hslInt(seeded(name)() * 360, 0.7, 0.62);

export class Still {
  ground = new Container();     // floor and walls
  wallLayer = new Container();  // what is on the walls, and the doors
  flat = new Container();       // scenery and flat things on the floor: over the walls, under everyone
  top = new Container();        // what hangs over everyone
  standing: Container[] = [];   // to be sorted by depth among the pets (zIndex = how far down the floor)
  things = new Map<string, Thing>();
  doors: Door[] = [];
  spots: Spot[] = [];
  lamps: Lamp[] = [];
  windows: { name: string; rect: Rect; open: boolean }[] = [];
  wallBusy: Rect[] = [];        // what already takes room on the walls, so writing goes round it
  blocked: Grid;
  wallShade = 0.5;              // how light the walls are, 0 to 1: chalk and scratches are drawn to show on it
  /** Where each wall's face is, in the room's pixels (the art may draw a wall thinner than its tiles): writing goes there. */
  band: Record<string, Rect> = { north: { x: OX, y: 2, w: FX * TILE, h: OY - 5 }, south: { x: OX, y: OY + FY * TILE + 2, w: FX * TILE, h: TILE - 4 },
                                 west: { x: 2, y: OY, w: OX - 4, h: FY * TILE }, east: { x: OX + FX * TILE + 2, y: OY, w: OX - 4, h: FY * TILE } };
  sun: number[] | null = null;  // the attic's shaft of sun, if there is one: where it falls
  /** What the room's floor and walls actually paint, as one picture: light and dark fall only there, never on the page beyond the walls. */
  shape: HTMLCanvasElement | null = null;
  /** The part of the canvas the room is drawn in (the art may leave a margin): lettering stays inside it. */
  bounds: Rect = { x: 0, y: 0, w: W, h: H };
  /** The room's scenery (the layout's decor), for the pointer: what each piece is and where. */
  scenery: { sprite: string; rect: Rect }[] = [];
  /** The places the room has grown ("sleeping corner"), each as the part of the floor it covers. */
  areas: { name: string; rect: Rect }[] = [];
  /** SPEC-v3.5 §4.2: each painted place and where it is drawn, for the pointer. */
  paints: { p: Painted; rect: Rect }[] = [];

  /** A sprite's name as this season draws it in this room (SPEC-v3.5 §5, view/assets/seasons.json); null: not there this season. */
  private swap: (name: string | null | undefined, x?: number, y?: number) => string | null | undefined = (n) => n;

  constructor(snap: Snap, room: RoomV, readonly layout: Layout | null, readonly K: number) {
    const L = layout ?? {};
    this.swap = (n, x, y) => seasonal(n, snap.clock.season, room.type, x, y);
    this.tiles(L, room);
    this.paint(room, false);   // SPEC-v3.5 §4.2: paint on the wall and the floor, under everything that stands there
    const blocked: Tile[] = [...(L.blocked ?? [])];
    for (const d of L.decor ?? []) this.decor(d.sprite, d.at, d.layer);
    this.puddles(room);
    this.places(room);
    for (const [dir, to] of Object.entries(room.doors)) this.door(snap, room, dir, to, L.doors);

    // what is put away (SPEC-v3.3 §2) comes after what it is put away on: it stands on that, small; in a chest it is not seen
    const flatFirst = (o: Obj) => (o.on && room.objects[o.on]?.store ? 2 : o.fix?.soft ? 0 : 1);
    for (const [name, o] of Object.entries(room.objects).sort(([, a], [, b]) => flatFirst(a) - flatFirst(b) || a.pos[1] - b.pos[1])) {
      const lf = L.fixtures?.[name], store = o.on ? room.objects[o.on]?.store : undefined;
      if (store?.inside) continue;
      const slot = store ? this.slot(o.on!, name) : undefined;
      if (o.made) {
        const t = this.made(name, o, snap.power, FAMILY[snap.pets.find((p) => p.id === o.made!.by)?.family ?? 1] ?? FAMILY[1], slot);
        if (!t.wall && !slot && !kind(t.drawn!.kind)?.flat) blocked.push(o.pos);
      } else if (o.memorial) {
        this.put(name, o, "stone", "sorted");
        blocked.push(o.pos);
      } else {
        if (o.water) blocked.push(...o.water);
        if (o.fix?.sun) this.sun = [OX + o.pos[0] * TILE + 8, OY + o.pos[1] * TILE + 8];
        const base = o.build ? o.build.sprite : lf ? lf.sprite : o.fix?.keepsake ? "fix.keepsake box" : pick(`fix.${name}`, `fix.${name.replace(/ /g, "_")}`, `fix.${name.replace(/ /g, "-")}`);
        if (!base || ((o.fix?.sun || o.water) && !has(base))) continue;   // light and water may be part of the floor's own picture
        // how it looks just now: a bowl by what is left in it, a plant by how far it has grown, anything else by its state
        const dead = !!o.fix?.light && o.state === "on" && !snap.power;   // in a power cut no lamp is lit, whatever its switch says
        const state = dead ? "off" : o.servings != null ? (o.servings <= 0 ? "empty" : o.servings < 2 ? "half" : "full") : o.state === "ripe" ? "ripe" : o.grow != null ? (o.grow >= 0.4 ? "growing" : null) : o.state;
        const plain = pick(o.planted ? `${base}.bare` : null, state ? `${base}.${state}` : null, base), sprite = this.swap(plain) ?? plain, sz = size(sprite);
        const flat = !!o.fix?.soft || !!o.fix?.sun || !!o.water || lf?.walk || lf?.layer === "floor" || !!o.build?.flat, onWall = !!o.wall || !!lf?.wall || lf?.layer === "wall";   // (a recording from before the layouts has its window on a floor tile: it is hung on the wall above all the same)
        const t = this.put(name, o, sprite, slot ? "sorted" : flat ? "ground" : onWall ? "wall" : lf?.layer === "top" ? "top" : "sorted", undefined, undefined, slot ? this.small : 1, slot);
        if (o.fix?.window) this.windows.push({ name, rect: this.glass(sprite, t), open: o.state === "open" });
        else if (!flat && !onWall && !slot && !o.fix?.sun && !o.water) blocked.push(o.pos);
        if (dead) {   // a lamp that should be lit and is not: a small grey bolt over it, so a cut shows by day too
          const out = new Sprite(fxTexture("out"));
          out.anchor.set(0.5, 1);
          out.position.set(Math.round(t.x) + 5, Math.round(t.rect.y) + 5);
          out.zIndex = t.s.zIndex + 0.2;
          (onWall ? this.wallLayer : this.top).addChild(out);
        }
        if (o.fix?.light && o.state === "on" && snap.power) this.lamps.push({ x: t.x, y: t.y - sz.h / 2, r: 50, color: [255, 226, 170], made: false });
        if (o.fix?.radio && o.state === "on" && snap.power) this.lamps.push({ x: t.x, y: t.y - 6, r: 12, color: [255, 214, 130], made: true });
        if (o.build?.glow) this.lamps.push({ x: t.x, y: t.y - sz.h / 2, r: 24, color: [255, 206, 140], made: true });   // SPEC-v3.5 §4.1: a lamp niche's small flame (no power to cut)
        if (o.build?.worn) t.s.tint = 0xb4a898;   // ... and what was built and has worn looks it
        t.on = (o.state === "on" && snap.power) || o.state === "playing";
      }
    }
    for (const s of room.spots) {
      const [cx, cy] = corner(s.pos), bare = s.loose === false && s.ready === false;
      if (s.on || (s.ready === false && !bare)) continue;   // put away in something: that thing says so
      // a bit the room grows is drawn on what it grows on (SPEC-v3.4 §5): `grows.<bit>`, or `grows.<bit>.bare` while it grows back
      const grows = s.loose === false ? `grows.${s.bit}${bare ? ".bare" : ""}` : null, source = has(grows) ? this.swap(grows) : null;
      if (source && has(source)) {
        const sz = size(source), sp = new Sprite(tex(source));
        sp.position.set(cx - sz.ax, cy - sz.ay);
        sp.zIndex = cy + TILE - 4;
        this.standing.push(sp);
        this.spots.push({ bit: s.bit, pos: s.pos, s: sp, bare, rect: { x: sp.x, y: sp.y, w: sz.w, h: sz.h } });
        blocked.push(s.pos);
        continue;
      }
      if (bare) continue;   // no picture of where it grows: only the bit itself is drawn, when it is there
      // a bit lying loose is a small pickup: drawn smaller than anything made, where that keeps its pixels whole
      const sprite = `bit.${s.bit}`, f = K >= 2 ? (K - 1) / K : 1, sp = new Sprite(tex(sprite));
      sp.anchor.set(0.5, 1);
      sp.scale.set(f);
      sp.position.set(cx + 8, cy + 14);
      sp.zIndex = cy + 12;
      this.standing.push(sp);
      this.spots.push({ bit: s.bit, pos: s.pos, s: sp, bare: false, rect: { x: cx + 8 - 8 * f, y: cy + 14 - 16 * f, w: 16 * f, h: 16 * f } });
    }
    this.paint(room, true);   // (and on the rugs, over them)
    for (const t of [...this.things.values()]) {   // what is kept inside a thing is not seen: a small number on it says how many
      const n = t.obj.store?.inside ? t.obj.store.holds.length : 0, F = Math.max(1, Math.round(K / 2));
      if (!n) continue;
      let c = counts.get(`${n}|${F}`);
      if (!c) counts.set(`${n}|${F}`, (c = fromCanvas(tagCanvas(String(n)))));
      const b = new Sprite(c);
      b.scale.set(F / K);
      b.anchor.set(1, 0);
      b.position.set(Math.round(t.rect.x + t.rect.w) + 2, Math.round(t.rect.y) - 2);
      b.zIndex = t.s.zIndex + 0.4;
      if (t.wall) this.wallLayer.addChild(b); else this.standing.push(b);
    }
    this.blocked = grid(blocked.filter(onFloor));
    for (const t of Object.values(snap.door_tiles)) if (onFloor(t)) this.blocked[idx(t)] = 0;   // a doorway is never shut off
  }

  /** Floor and walls: from the layout, or plain ones if this room type has none. A painted room is recoloured. */
  private tiles(L: Layout, room: RoomV) {
    const paint = room.paint ?? { wall: null, floor: null };
    if (!L.floor || !L.walls) {   // a room type with no layout (or half of one) still has a plain floor and walls
      const g = new Graphics();
      const mixc = (base: number, name: string | null) => {
        const hex = name ? PALETTE[name] : null;
        if (!hex) return base;
        const n = parseInt(hex.slice(1), 16);
        return [16, 8, 0].reduce((c, s) => c | (Math.round((((base >> s) & 255) + ((n >> s) & 255)) / 2) << s), 0);
      };
      g.rect(0, 0, W, H).fill(mixc(PLAIN.wall, paint.wall));
      g.rect(OX, OY, FX * TILE, FY * TILE).fill(mixc(PLAIN.floor, paint.floor));
      g.rect(OX, OY - 3, FX * TILE, 3).fill(PLAIN.trim).rect(OX - 1, OY, 1, FY * TILE).rect(OX + FX * TILE, OY, 1, FY * TILE).rect(OX - 1, OY + FY * TILE, FX * TILE + 2, 1).fill(PLAIN.trim);
      this.ground.addChild(g);
    }
    let light = 0, n = 0;
    const shape = L.floor || L.walls ? Object.assign(document.createElement("canvas"), { width: W, height: H }) : null, sx = shape?.getContext("2d");
    this.shape = shape;
    for (const [rows, color] of [[L.floor, paint.floor], [L.walls, paint.wall]] as const) {
      for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) {
        const name = this.swap(rows?.[y]?.[x], x, y);
        if (!name) continue;
        // paint is a light wash (walls more than floors), and never on grass, soil, water, sky or glass: a painted room must not look flooded or dark
        const wash = color && has(name) && !/grass|soil|water|sky|glass|fence|path|hedge/.test(name) ? tinted(name, color, {}, rows === L.walls ? 0.3 : 0.2) : null;
        const s = new Sprite(wash ? wash.texture : tex(name)), sz = size(name);
        s.position.set(x * TILE - sz.ax, y * TILE - sz.ay);
        if (has(name)) sx?.drawImage(canvasOf(name), x * TILE - sz.ax, y * TILE - sz.ay);
        this.ground.addChild(s);
        if (rows === L.walls && y < 2 && has(name)) { light += lightness(wash ? wash.canvas : canvasOf(name)); n++; }
      }
    }
    if (n) this.wallShade = light / n;
    if (shape && sx) {   // how far the room's own picture reaches
      const p = sx.getImageData(0, 0, W, H).data;
      let [x0, y0, x1, y1] = [W, H, -1, -1];
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (p[(y * W + x) * 4 + 3] > 127) [x0, y0, x1, y1] = [Math.min(x0, x), Math.min(y0, y), Math.max(x1, x), Math.max(y1, y)];
      if (x1 >= x0) this.bounds = { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
    }
    if (L.walls) {   // the face of each wall: what its tiles actually paint along the middle of that side
      const span = (name: string | null | undefined, across: boolean): [number, number] | null => {
        if (!name || !has(name)) return null;
        const c = canvasOf(name), p = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data;
        let [lo, hi] = [99, -1];
        for (let i = 0; i < 16; i++) for (let j = 0; j < 16; j++) {   // (the dark outside of the house and the outline are not the wall's face)
          const at = ((across ? j : i) * c.width + (across ? i : j)) * 4;
          if (p[at + 3] > 200 && p[at] * 0.3 + p[at + 1] * 0.59 + p[at + 2] * 0.11 > 70) [lo, hi] = [Math.min(lo, i), Math.max(hi, i)];
        }
        return hi < 0 ? null : [lo, hi + 1];
      };
      const [w, e, so] = [span(L.walls[5]?.[0], true), span(L.walls[5]?.[COLS - 1], true), span(L.walls[ROWS - 1]?.[6], false)];
      if (w) this.band.west = { x: w[0], y: OY, w: w[1] - w[0], h: FY * TILE };
      if (e) this.band.east = { x: (COLS - 1) * TILE + e[0], y: OY, w: e[1] - e[0], h: FY * TILE };
      if (so) this.band.south = { x: OX, y: (ROWS - 1) * TILE + so[0], w: FX * TILE, h: so[1] - so[0] };
    }
  }

  /** SPEC-v3.5 §4.2: what is painted here (px/built.ts): on the wall and the floor, or (`rugs`) on the rugs. */
  private paint(room: RoomV, rugs: boolean) {
    for (const p of room.painted ?? []) {
      if ((p.where === "rug") !== rugs) continue;
      const t = rugs ? this.things.get(p.at as string) : undefined, r = paintRect(p, this.band.north, t?.rect);
      if (!r) continue;
      const g = new Graphics();
      paintOn(g, r, p);
      if (!t) this.ground.addChild(g);
      else if (t.s.parent) t.s.parent.addChild(g);
      else { g.zIndex = t.s.zIndex + 0.05; this.standing.push(g); }
      this.paints.push({ p, rect: r });
    }
  }

  private decor(named: string, at: Tile, layer?: string) {
    const sprite = this.swap(named);
    if (!sprite) return;
    const s = new Sprite(tex(sprite)), sz = size(sprite), [cx, cy] = corner(at);
    s.position.set(cx - sz.ax, cy - sz.ay);
    if (layer === "floor") this.flat.addChild(s);
    else if (layer === "top") this.top.addChild(s);
    else if (layer === "wall" || at[1] < 0) this.wallLayer.addChild(s);
    else { s.zIndex = cy + TILE - 4; this.standing.push(s); }
    if (layer === "wall" || s.y < OY - 4) this.wallBusy.push({ x: s.x, y: s.y, w: sz.w, h: sz.h });   // on the wall, or tall enough to stand in front of it
    this.scenery.push({ sprite: named, rect: { x: s.x, y: s.y, w: sz.w, h: sz.h } });
  }

  /** Water standing on the floor after a leak. */
  private puddles(room: RoomV) {
    if (!room.wet) return;
    const g = new Graphics(), r = seeded(room.id + "wet");
    for (let i = 0; i < 7; i++) {
      const [x, y, w] = [OX + 6 + Math.floor(r() * (FX * TILE - 40)), OY + 8 + Math.floor(r() * (FY * TILE - 20)), 10 + Math.floor(r() * 16)];
      g.rect(x + 2, y, w - 4, 1).rect(x, y + 1, w, 3).rect(x + 3, y + 4, w - 5, 1).fill({ color: 0x4f9fe0, alpha: 0.72 });
      g.rect(x + 1, y + 4, 2, 1).rect(x + 3, y + 5, w - 5, 1).fill({ color: 0x2f6fb0, alpha: 0.6 });   // its darker near edge
      g.rect(x + 3, y + 1, Math.floor(w / 3), 1).rect(x + w - 5, y + 2, 2, 1).fill({ color: 0xffffff, alpha: 0.8 });
    }
    this.flat.addChild(g);
  }

  /** The places a room has grown (SPEC-v3.3 §2.3): a faint tint on their tiles, with a line round the whole of each. */
  private places(room: RoomV) {
    if (!room.areas?.length) return;
    const g = new Graphics();
    for (const a of room.areas) {
      const color = areaColor(a.name), tiles = a.tiles.filter(onFloor), at = (x: number, y: number) => tiles.some((t) => t[0] === x && t[1] === y);
      if (!tiles.length) continue;
      for (const t of tiles) g.rect(OX + t[0] * TILE, OY + t[1] * TILE, TILE, TILE);
      g.fill({ color, alpha: 0.16 });
      for (const [tx, ty] of tiles) {   // its edge, wherever the next tile is not part of it
        const [x, y] = corner([tx, ty]);
        if (!at(tx, ty - 1)) g.rect(x, y, TILE, 1);
        if (!at(tx, ty + 1)) g.rect(x, y + TILE - 1, TILE, 1);
        if (!at(tx - 1, ty)) g.rect(x, y, 1, TILE);
        if (!at(tx + 1, ty)) g.rect(x + TILE - 1, y, 1, TILE);
      }
      g.fill({ color, alpha: 0.4 });
      const xs = tiles.map((t) => t[0]), ys = tiles.map((t) => t[1]), [x0, y0] = corner([Math.min(...xs), Math.min(...ys)]);
      this.areas.push({ name: a.name, rect: { x: x0, y: y0, w: (Math.max(...xs) - Math.min(...xs) + 1) * TILE, h: (Math.max(...ys) - Math.min(...ys) + 1) * TILE } });
    }
    this.flat.addChild(g);
  }

  /** Things put away on a thing are small: about half their size, on whole pixels. */
  private get small() { return Math.max(1, Math.round(this.K * 0.6)) / this.K; }
  /** Where the thing called `name` stands on the thing it is put away on: side by side along its surface (the
   *  sprite's `surface`, or across its middle). */
  private slot(on: string, name: string): Slot | undefined {
    const t = this.things.get(on), holds = t?.obj.store?.holds ?? [];
    if (!t) return undefined;
    const sz = size(t.sprite), [sx, sy, sw] = def(t.sprite)?.surface ?? [2, Math.round(sz.h * 0.5), sz.w - 4], i = Math.max(0, holds.indexOf(name)), n = Math.max(1, holds.length);
    return { x: Math.round(t.rect.x + (sx + (sw * (i + 0.5)) / n) * t.scale), y: Math.round(t.rect.y + sy * t.scale), z: t.s.zIndex + 0.3 + i * 0.01, wall: t.wall };
  }

  private door(snap: Snap, room: RoomV, dir: string, to: string, style?: string) {
    const tile = snap.door_tiles[dir];
    if (!tile) return;
    const there = snap.rooms.find((r) => r.id === to), stuck = room.shut.includes(dir), state = stuck ? "stuck" : there?.type ? "open" : "unknown";
    const order = stuck ? ["stuck", "shut"] : state === "unknown" ? ["unknown", "shut"] : ["open"];
    const sprite = pick(...(style ? order.map((s) => `door.${style}.${dir}.${s}`) : []), ...order.flatMap((s) => [`door.${dir}.${s}`, `door.${s}.${dir}`]), ...order.map((s) => `door.${s}`));
    // a door's sprite is anchored to its floor tile; the anchor says how far into the wall it goes
    const sz = size(sprite), at = tile;
    const s = new Sprite(tex(sprite)), [cx, cy] = corner(at);
    s.position.set(cx - sz.ax, cy - sz.ay);
    this.wallLayer.addChild(s);
    const rect = { x: s.x, y: s.y, w: sz.w, h: sz.h };
    if (stuck && !sprite.includes("stuck")) {   // no picture of its own: a bar across it
      const bar = new Graphics().rect(rect.x + 1, rect.y + rect.h - 9, rect.w - 2, 3).fill(0x4a3526).rect(rect.x + 1, rect.y + rect.h - 9, rect.w - 2, 1).fill(0x8a6a45);
      this.wallLayer.addChild(bar);
    }
    this.doors.push({ dir, to, rect, tile });
    this.wallBusy.push(rect);
  }

  /** One sprite standing on (or hanging above) a tile. */
  private put(name: string, o: Obj, sprite: string, where: "ground" | "wall" | "top" | "sorted", texture: Texture = tex(sprite), canvas = canvasOf(sprite), scale = 1, slot?: Slot): Thing {
    const hung = slot ? slot.wall : !!o.wall || where === "wall";
    // what hangs on the wall hangs on the north wall above its tile: its sprite's anchor lifts it there (a thing not
    // drawn for a wall, hung up all the same, goes just above the floor line)
    const sz = size(sprite), [cx, cy] = corner(hung ? [o.pos[0], 0] : o.pos), s = new Sprite(texture);
    const [x, y] = slot ? [slot.x, slot.y] : [cx - sz.ax + sz.w / 2, hung && o.made && cy - sz.ay + sz.h > OY - 2 ? OY - 5 : cy - sz.ay + sz.h];
    s.anchor.set(0.5, 1);
    s.scale.set(scale);
    s.position.set(x, y);
    const rect = { x: x - (sz.w * scale) / 2, y: y - sz.h * scale, w: sz.w * scale, h: sz.h * scale };
    if (where === "ground") this.flat.addChild(s);
    else if (where === "top") this.top.addChild(s);
    else if (hung) this.wallLayer.addChild(s);
    else { s.zIndex = slot?.z ?? cy + TILE - 4; this.standing.push(s); }
    if (hung || rect.y < OY - 4) this.wallBusy.push(rect);
    const t: Thing = { name, obj: o, s, x, y, rect, canvas, texture, drawn: null, scale, sprite, wall: hung, on: false, glassy: false, bob: false, bounce: false, noisy: false,
                       fragrant: false, heirloom: false, extra: [], stir: 0 };
    this.things.set(name, t);
    // Something planted in it (SPEC-v3.4 §3.5): the picture for how far it has grown (or for a plant that has wilted)
    // goes over it, foot on foot, at its size. An art pack with no such picture shows nothing.
    const stage = o.planted && (o.planted.wilted ? "wilted" : o.planted.stage), plant = o.planted && [`plant.${o.planted.what}.${stage}`, `plant.${stage}`].find(has);
    if (plant) {
      const p = new Sprite(tex(plant));
      p.anchor.set(0.5, 1);
      p.scale.set(scale);
      p.position.set(x, y);
      p.zIndex = s.zIndex + 0.05;
      if (s.parent) s.parent.addChild(p); else this.standing.push(p);
      t.extra.push(p);
    }
    return t;
  }

  /** Something a pet made (§3): its kind's sprite in its colour, a little smaller or larger, looking like what it is made of. */
  private made(name: string, o: Obj, power: boolean, maker: string, slot?: Slot): Thing {
    const m = o.made!, d = drawnOf(m), doing = m.active ? m.behavior?.do ?? "" : "", mat = d.material;
    const color = doing.startsWith("change_color:") ? doing.split(":")[1] : d.color;
    const look = { soft: mat === "soft" || undefined, dark: mat === "dark" || undefined, damp: m.worn.includes("damp") || undefined, dusty: m.worn.includes("dusty") || undefined,
                   eaten: m.worn.includes("eaten") || undefined };
    const sprite = o.planted ? pick(`${d.sprite}.bare`, d.sprite) : d.sprite;   // a pot drawn with a plant of its own is bare under what is planted in it
    const pic = has(sprite) ? tinted(sprite, color, look) : { texture: tex(sprite), canvas: canvasOf(sprite) };
    const scale = slot ? this.small : Math.max(1, Math.round(this.K * (SIZES[Math.round(d.size) - 1] ?? 1))) / this.K;
    const t = this.put(name, o, sprite, "sorted", pic.texture, pic.canvas, scale, slot);
    t.drawn = { ...d, color };
    t.on = power && (o.state === "on" || doing === "glow" || ((mat === "bright" || mat === "warm") && m.active) || !!inventedKind(d.kind)?.glow);   // a power cut is dark for made lights too
    if (!t.wall && !slot) {   // a made thing sits on a small soft shadow: that, and its size, tell it from a bit lying loose
      const hw = Math.max(3, Math.round(t.rect.w / 2) - 1), g = new Graphics();
      g.rect(Math.round(t.x) - hw, Math.round(t.y) - 2, 2 * hw, 3).rect(Math.round(t.x) - hw + 2, Math.round(t.y) - 3, 2 * hw - 4, 1).rect(Math.round(t.x) - hw + 2, Math.round(t.y) + 1, 2 * hw - 4, 1).fill({ color: 0x1a1420, alpha: 0.22 });
      this.flat.addChild(g);
      // and a small pip at its foot in its maker's plate colour: the pets made these, and this is whose
      const pip = new Sprite(fxTexture("pip"));
      pip.tint = parseInt(maker.slice(1), 16);
      pip.anchor.set(0.5, 1);
      pip.position.set(Math.round(t.x - t.rect.w / 2) + 1, Math.round(t.y) + 1);
      pip.zIndex = t.s.zIndex + 0.2;
      this.standing.push(pip);
    }
    t.glassy = mat === "glassy";
    t.bob = mat === "springy";
    t.bounce = doing === "bounce" || (mat === "bouncy" && m.active);
    t.noisy = (mat === "noisy" && m.active) || doing === "hum";
    t.fragrant = mat === "fragrant";
    t.heirloom = !!m.heirloom;
    if (t.on) this.lamps.push({ x: t.x, y: t.y - t.rect.h / 2, r: 26, color: mat === "warm" ? [255, 196, 140] : [255, 232, 170], made: true });
    if (doing === "dim") this.lamps.push({ x: t.x, y: t.y - 6, r: 30, color: [70, 70, 110], made: true });
    if (m.heirloom) {   // an heirloom wears a small ribbon
      const r = new Sprite(fxTexture("ribbon"));
      r.anchor.set(0.5);
      r.position.set(Math.round(t.rect.x + t.rect.w - 2), Math.round(t.rect.y + 3));
      r.zIndex = t.s.zIndex + 0.1;
      this.standing.push(r);
    }
    return t;
  }

  /** The part of a window's picture that is sky, in the room's pixels. */
  private glass(sprite: string, t: Thing): Rect {
    const d = def(sprite)?.glass;
    return d ? { x: t.rect.x + d[0], y: t.rect.y + d[1], w: d[2], h: d[3] } : { x: t.rect.x + 3, y: t.rect.y + 3, w: Math.max(2, t.rect.w - 6), h: Math.max(2, t.rect.h - 6) };
  }

  destroy() {
    for (const c of [this.ground, this.wallLayer, this.flat, this.top, ...this.standing]) c.destroy({ children: true });
  }
}

/** How light a picture is on the whole, 0 to 1. */
function lightness(c: HTMLCanvasElement) {
  const p = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data;
  let sum = 0, n = 0;
  for (let i = 0; i < p.length; i += 4) if (p[i + 3]) { sum += (p[i] * 0.3 + p[i + 1] * 0.59 + p[i + 2] * 0.11) / 255; n++; }
  return n ? sum / n : 0.5;
}
