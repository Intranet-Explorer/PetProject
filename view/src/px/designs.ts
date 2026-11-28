// SPEC-v3.6d §9: designs in the room. A finished design whose effect is working (`obj.effect_on`, until a tick) shows
// it: a cone of light (a soft round glow for a soft light or an upright lamp), a warm glow (and steam from a vessel),
// a cold drift, rings for a sound (wider for a signal, notes for music), water poured, ripples under a float, a carried
// stack, chips for a cutter, leaves for a grower. One just built that failed (`obj.sputter`) sputters: smoke, sparks
// and a clunk, for a few seconds. A design being built (a hob's `design`, in this room) stands half made where it is
// being built (at the bench, the machine, or by its builder), on its blueprint, with a pip for each part.
import { Container, Graphics, Sprite } from "pixi.js";
import { composeThing, partsData } from "../parts";
import type { Design, PetV, RoomV, Snap } from "../types";
import { ago } from "../types";
import { fromCanvas } from "./assets";

const OWN = { texture: true, textureSource: true };   // (SPEC-v4.0.5 §7.1: a design at work has a texture of its own)
import type { Fx } from "./fx";
import type { Still, Thing } from "./still";
import { REDUCE } from "./weather";

/** The bases a design lies along (its tip to the right): its light is a cone ahead of it. */
const LYING = new Set(["tube", "plank", "hull"]);
/** How long a failure sputters (real seconds). */
const SPUTTER = 8;

type Wip = { pet: string; key: string; s: Sprite; g: Graphics; d: Design };

export class Designs {
  /** The light a working design gives, over the room's dark (added: it lights what it falls on). */
  light = new Graphics();
  private marks = new Graphics();   // under the effects: ripples, the carried stack, a blueprint
  private wips = new Map<string, Wip>();
  private next = 0;
  private add: ((c: Container) => void) | null = null;

  constructor() { this.light.blendMode = "add"; }

  /** The room was drawn again: what moves on the designs goes in among what stands (`add`). */
  attach(add: (c: Container) => void) {
    this.detach();
    this.add = add;
    this.marks = new Graphics();
    this.marks.zIndex = 1e6;
    add(this.marks);
  }
  detach() {
    for (const w of this.wips.values()) { w.s.destroy(OWN); w.g.destroy(); }
    this.wips.clear();
    this.marks.destroy();
  }

  /** A snapshot: the designs being built in this room, each where it is being built. */
  update(snap: Snap, room: RoomV, still: Still, hob: (id: string) => { x: number; y: number } | null) {
    const here = snap.pets.filter((p) => p.design && p.stage !== "dead" && (p.design.where ?? p.room) === room.id);
    for (const [id, w] of this.wips) if (!here.some((p) => p.id === id)) { w.s.destroy(OWN); w.g.destroy(); this.wips.delete(id); }
    for (const p of here) {
      const d = p.design!, placed = d.parts.filter((x) => x.placed), key = JSON.stringify([placed, d.need, d.placed, d.at]);
      let w = this.wips.get(p.id);
      if (!w || w.key !== key) {
        w?.s.destroy(OWN); w?.g.destroy();
        const parts = placed.map((x, i) => ({ part: x.part, at: i ? designSpot(d, x.part) : null, material: x.material, color: x.color }));
        const s = new Sprite(fromCanvas(composeThing({ parts, size: "large" })));
        s.anchor.set(0.5, 1);
        w = { pet: p.id, key, s, g: new Graphics(), d };
        this.add?.(w.g);
        this.add?.(s);
        this.wips.set(p.id, w);
      }
      w.d = d;
      const at = siteOf(d, still, p, hob);
      w.s.position.set(Math.round(at.x), Math.round(at.y));
      w.s.zIndex = at.y + 0.3;
      w.g.zIndex = at.y + 0.2;
      w.g.clear();
      const x0 = Math.round(at.x - 10), y0 = Math.round(at.y - 2);
      w.g.rect(x0, y0, 20, 5).fill({ color: 0x2f5e9e, alpha: 0.9 }).rect(x0, y0, 20, 5).stroke({ width: 1, color: 0xdbe9ff, alpha: 0.7, alignment: 1 });   // its blueprint
      for (let i = 0; i < d.need; i++) w.g.rect(Math.round(at.x - d.need * 1.5 + i * 3), y0 + 7, 2, 2).fill(i < d.placed ? 0xffd76a : 0x6b6f80);   // parts in place out of parts needed
    }
  }

  /** Every frame. */
  frame(now: number, fx: Fx, snap: Snap, room: RoomV, still: Still, dark = 0) {
    const g = this.light, m = this.marks, calm = REDUCE.matches ? 3 : 1, due = now > this.next;
    g.clear();
    g.alpha = 0.45 + 0.55 * Math.min(1, dark * 1.5);   // a light shows most in the dark (by day, a faint cone)
    if (!m.destroyed) m.clear();
    if (due) this.next = now + 160 * calm;
    for (const w of this.wips.values()) if (due && Math.random() < 0.08) fx.spawn("wisp", w.s.x + (Math.random() - 0.5) * 10, w.s.y - 6, { vy: -6, life: 900, alpha: 0.6 });   // (a little dust at the work)
    for (const t of still.things.values()) {
      const o = room.objects[t.name];
      if (!o?.made?.design || t.s.destroyed) continue;
      const on = o.effect_on && o.effect_on.until > snap.tick ? o.effect_on.effect : null;
      const sputter = o.sputter != null && ago(snap, o.sputter) < SPUTTER;
      t.bob = on === "float";
      t.bounce = on === "play";
      if (on) guardEffect(on, t, o.made.design.effects, LYING.has(o.made.parts?.[0]?.part ?? ""), g, m, fx, now, due, calm);
      if (sputter) {   // a failure: it shakes in fits, smokes, throws sparks, and now and then clunks down
        const fit = Math.sin(now / 90) > 0.2;
        t.s.x = t.x + (fit ? Math.round(Math.sin(now / 35)) : 0);
        if (Math.floor(now / 1300) % 2 && Math.sin(now / 1300 * Math.PI) > 0.95) t.s.y = t.y + 1;   // the clunk
        if (due && Math.random() < 0.22) fx.spawn("puff", t.x + (Math.random() - 0.5) * 6, t.rect.y - 2, { vy: -10, vx: (Math.random() - 0.5) * 6, life: 1100, sway: 2, tint: 0x5a5560, alpha: 0.55 });
        if (due && fit && Math.random() < 0.3) fx.burst("speck", t.x + (Math.random() - 0.5) * 8, t.rect.y + t.rect.h / 2, 4, 18, { tint: 0xffb040, g: 60, life: 380 });
        if (due && Math.random() < 0.04) fx.spawn("bang", t.x + t.rect.w / 2 + 2, t.rect.y - 2, { vy: -6, life: 700 });
      }
    }
  }

  destroy() { this.detach(); this.light.destroy(); }
}

/** Where a part of a design in hand goes: on the first of its spots that the base has (parts.json); a later one on a spot
 *  already taken is left for the engine's finished `made.parts` to place. */
function designSpot(d: Design, part: string): string | null {
  const D = partsData(), base = d.parts.find((x) => x.placed)?.part;
  return D?.thing[part]?.on?.find((s) => D.thing[base ?? ""]?.spots?.includes(s)) ?? D?.thing[part]?.on?.[0] ?? null;
}

/** Where a design is being built: by the bench (a fixture or thing whose name has "bench" in it), at the machine it names,
 *  or else beside its builder (in the yard, or wherever it is). */
function siteOf(d: Design, still: Still, p: PetV, hob: (id: string) => { x: number; y: number } | null) {
  const at = d.at ?? "";
  const fix = at && at !== "yard" ? [...still.things.values()].find((t) => t.name === at || (at === "bench" && /bench/.test(t.name))) : undefined;
  if (fix) return { x: fix.rect.x + fix.rect.w + 12, y: fix.y };
  const h = hob(p.id);
  return h ? { x: h.x + 13, y: h.y } : { x: 0, y: -100 };
}

/** One working effect, drawn this frame. `effects`: the design's claimed effects (a vessel that heats steams). */
function guardEffect(on: string, t: Thing, effects: Record<string, { works: boolean }>, lying: boolean, g: Graphics, m: Graphics, fx: Fx, now: number, due: boolean, calm: number) {
  const r = t.rect, cx = t.x, cy = r.y + r.h / 2, top = r.y, pulse = 0.5 + 0.5 * Math.sin(now / 400);
  if (on === "light" && lying) {   // a light lying down throws a cone ahead of it (to its right, where its tip is)
    const x0 = Math.round(cx + r.w * 0.36), L = 46;
    for (const [k, a] of [[1, 0.18], [0.7, 0.16], [0.4, 0.2]] as [number, number][]) g.poly([x0, cy - 1, x0 + L * k, cy - 10 * k - 2, x0 + L * k, cy + 10 * k + 4, x0, cy + 2]).fill({ color: 0xfff0b0, alpha: a });
  } else if (on === "light" || on === "soft light") {   // an upright light, or a soft one: a round glow
    const R = on === "light" ? 26 : 18;
    for (const k of [1, 0.6, 0.3]) g.circle(cx, top + 3, R * k).fill({ color: on === "light" ? 0xffe9a0 : 0xffd6a0, alpha: 0.08 + 0.03 * pulse });
  } else if (on === "heat") {   // a warm glow, and steam off a vessel (a thing that also pours or holds)
    for (const k of [1, 0.6]) g.circle(cx, cy, 16 * k).fill({ color: 0xff9040, alpha: 0.08 + 0.05 * pulse });
    const steam = effects.pour || effects.hold || effects.keep;
    if (due && Math.random() < (steam ? 0.6 : 0.25)) fx.spawn("wisp", cx + (steam ? r.w / 3 : (Math.random() - 0.5) * r.w), top, { vy: -10, vx: steam ? 3 : 0, life: 1600, sway: 2, tint: steam ? 0xf6f8fa : 0xffc890, alpha: 0.7 });
  } else if (on === "cold") {
    g.circle(cx, cy, 14).fill({ color: 0x80c8ff, alpha: 0.07 + 0.03 * pulse });
    if (due && Math.random() < 0.5) fx.spawn("speck", cx + (Math.random() - 0.5) * 16, top, { vy: 6, vx: (Math.random() - 0.5) * 4, life: 1500, sway: 2, tint: 0xdff2ff });
  } else if (on === "sound" || on === "signal") {   // rings going out from it; a signal's go further
    const n = on === "signal" ? 3 : 2, span = on === "signal" ? 30 : 18, period = 1100 * calm;
    for (let i = 0; i < n; i++) {
      const k = ((now / period) + i / n) % 1;
      m.ellipse(cx, cy, 4 + k * span, (4 + k * span) * 0.6).stroke({ width: 1, color: 0xffffff, alpha: 0.7 * (1 - k) });
    }
  } else if (on === "music") {
    if (due && Math.random() < 0.35) fx.spawn("note", cx + (Math.random() - 0.5) * 10, top, { vx: (Math.random() - 0.5) * 6, vy: -14, life: 1600, sway: 2 });
  } else if (on === "pour") {   // water from its right side down to the floor, a splash where it lands
    const x = r.x + r.w, y = cy;
    for (let i = 0; i < 4; i++) { const k = ((now / 380) + i / 4) % 1; m.rect(Math.round(x + 2 + k * 3), Math.round(y + k * (t.y - y + 2)), 1, 2).fill({ color: 0x79b8ce }); }
    m.ellipse(x + 5, t.y + 2, 4, 1.5).fill({ color: 0x3f78a8, alpha: 0.5 });
    if (due && Math.random() < 0.3) fx.spawn("drop", x + 5, t.y, { vy: -12, vx: (Math.random() - 0.5) * 10, g: 50, life: 400, tint: 0xcfeaf6 });
  } else if (on === "float") {   // it rides the water: rings spread from its foot
    for (let i = 0; i < 2; i++) { const k = ((now / (1500 * calm)) + i / 2) % 1; m.ellipse(cx, t.y, r.w / 2 + k * 10, 2 + k * 3).stroke({ width: 1, color: 0xe4f4fa, alpha: 0.8 * (1 - k) }); }
  } else if (on === "carry") {   // a carried stack: three little bundles on it
    const colors = [0xb07a48, 0xd8c8a8, 0x8a9a6a];
    for (let i = 0; i < 3; i++) m.rect(Math.round(cx - 4 + (i % 2)), Math.round(top - 4 - i * 4), 8, 4).fill(colors[i]).rect(Math.round(cx - 4 + (i % 2)), Math.round(top - 4 - i * 4), 8, 4).stroke({ width: 1, color: 0x2b1a10, alignment: 1 });
  } else if (on === "roll") {   // it rolls a little to and fro, kicking up dust
    t.s.x = t.x + Math.round(Math.sin(now / 500) * 3);
    if (due && Math.random() < 0.25) fx.spawn("dust", t.s.x + (Math.random() - 0.5) * r.w, t.y, { life: 500 });
  } else if (on === "cut" || on === "dig" || on === "fasten") {
    if (due && Math.random() < 0.3) fx.burst("grit", cx + r.w / 3, top + 3, 3, 16, { g: 50, life: 400, tint: on === "dig" ? 0x8a6a48 : 0xf4f0e0 });
  } else if (on === "grow") {
    if (due && Math.random() < 0.3) fx.spawn("speck", cx + (Math.random() - 0.5) * r.w, top, { vy: -8, life: 1400, sway: 2, tint: 0x6fcf5f });
  } else if (on === "comfort") {
    if (due && Math.random() < 0.12) fx.spawn("heart", cx, top - 2, { vy: -8, life: 1300, sway: 2 });
  } else if (on === "catch") {
    if (due && Math.random() < 0.2) fx.spawn("drop", r.x + r.w, t.y - 2, { vy: -14, vx: 6, g: 60, life: 500, tint: 0xcfeaf6 });
  } else if (due && Math.random() < 0.15) fx.spawn("sparkle", cx + (Math.random() - 0.5) * r.w, top + Math.random() * r.h, { life: 600 });   // hold, keep, reach, play, lift: it shines when used
}
