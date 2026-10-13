// A step a pet has just finished, played once (SPEC-v3.2 §5.2): the made thing pops in, an unmade one breaks into
// bits with a puff, two things slide together and flash, a bit goes to the paws or to the floor, a gift is held out,
// two lean together under a small heart, notes rise, chalk dust falls. A step that turned out not possible (ok false)
// shows nothing. What lasts (walking there, sitting busy, resting, reading) is in actors.ts. The things a body does by
// itself (SPEC-v3.3 §1: `body` is set) end the same way, smaller; a type nobody here has heard of shows nothing.
import type { Texture } from "pixi.js";
import type { Act } from "../types";
import type { PetActor } from "./actors";
import { has, tex } from "./assets";
import type { Fx } from "./fx";
import { OY } from "./geom";
import type { Thing } from "./still";

/** A made thing that was in the room a moment ago: what it looked like and where it stood. */
export type Ghost = { texture: Texture; x: number; y: number; scale: number; h: number };
export type Cast = { pets: Map<string, PetActor>; things: Map<string, Thing>; ghosts: Map<string, Ghost>; fx: Fx; now: number;
  where: (name: string | null | undefined) => number[] | null; petAt: (name: string | null | undefined) => PetActor | null;
  /** The thing a thing is put away on or in just now, if it is. */
  kept: (name: string | null | undefined) => Thing | undefined };

const norm = (s: string | null | undefined) => (s ?? "").trim().toLowerCase();

/** A thing swells into place. */
function pop(fx: Fx, t: Thing, ms = 380) {   // (the room may be built again meanwhile: a sprite that is gone is left alone)
  fx.tween(ms, (k) => t.s.destroyed || t.s.scale.set(t.scale * (k < 0.6 ? (k / 0.6) * 1.25 : 1.25 - ((k - 0.6) / 0.4) * 0.25)), () => t.s.destroyed || t.s.scale.set(t.scale));
}
function wiggle(fx: Fx, t: Thing) {
  fx.tween(420, (k) => t.s.destroyed || t.s.scale.set(t.scale * (1 + Math.sin(k * Math.PI * 3) * 0.1 * (1 - k)), t.scale * (1 - Math.sin(k * Math.PI * 3) * 0.1 * (1 - k))), () => t.s.destroyed || t.s.scale.set(t.scale));
}

export function play(a: Act, c: Cast) {
  if (!a.ok) return;
  const { fx, now } = c, me = c.pets.get(a.pet), at = me ? [me.w.x, me.w.y] : null, head = me ? me.tall : 16;
  const thing = c.things.get(norm(a.what)) ?? c.things.get(a.what ?? ""), other = c.petAt(a.to), there = c.where(a.to) ?? c.where(a.what);
  const picture = (what: string | null | undefined): [Texture, number] | null => {
    const t = c.things.get(norm(what)), g = c.ghosts.get(norm(what));
    return what && has(`bit.${what}`) ? [tex(`bit.${what}`), 1] : t ? [t.texture, t.scale * 0.75] : g ? [g.texture, g.scale * 0.75] : null;
  };
  switch (a.type) {
    case "make":
      if (thing) { pop(fx, thing); fx.burst("sparkle", thing.x, thing.y - 8, 7, 26); }
      me?.react("happy", now, 1100);
      break;
    case "combine": {   // the two slide together, a flash, the new thing
      const to = thing ? [thing.x, thing.y - 6] : at;
      if (!to) break;
      if (thing) thing.s.visible = false;
      for (const n of a.from ?? []) {
        const g = c.ghosts.get(norm(n));
        if (g) fx.fly(g.texture, [g.x, g.y - g.h / 2], to, 520, g.scale);
      }
      fx.after(520, () => {
        fx.spawn("flash", to[0], to[1], { life: 430 });
        fx.burst("glint", to[0], to[1], 8, 40);
        if (thing && !thing.s.destroyed) { thing.s.visible = true; pop(fx, thing, 450); }
      });
      me?.react("happy", now + 520, 1000);
      break;
    }
    case "unmake": {   // it breaks into its bits with a puff
      const g = c.ghosts.get(norm(a.what));
      const p = g ? [g.x, g.y - g.h / 2] : at;
      if (!p) break;
      fx.spawn("puff", p[0], p[1], { life: 500 });
      fx.burst("grit", p[0], p[1], 6, 38, { g: 90, life: 700 });
      break;
    }
    case "gather": case "take": {
      const pic = picture(a.what);
      if (pic && at) fx.fly(pic[0], there ?? [at[0] + 7, at[1]], [at[0], at[1] - 7], 380, pic[1]);
      break;
    }
    case "drop":
      if (at && a.what && has(`bit.${a.what}`)) fx.fly(tex(`bit.${a.what}`), [at[0], at[1] - 7], [at[0] + 7, at[1]], 380, 1, () => fx.spawn("dust", at[0] + 7, at[1] - 2, { life: 450 }));
      break;
    case "give": case "show": case "bequeath": {   // held out toward the other
      const pic = picture(a.what);
      if (!at || !there) break;
      me?.leanTo(there[0], there[1], now, 1600);
      const reach = a.type === "give" ? 1 : 0.55, to = [at[0] + (there[0] - at[0]) * reach, at[1] - 8 + (there[1] - at[1]) * reach];
      if (pic) fx.fly(pic[0], [at[0], at[1] - 8], to, a.type === "give" ? 650 : 1300, pic[1]);
      if (a.type !== "show") fx.after(650, () => fx.burst("sparkle", to[0], to[1], 4, 16));
      other?.turn(at[0], at[1], now, 2000);
      break;
    }
    case "nuzzle": case "accept": {   // the two lean together, and a small heart
      if (!at) break;
      const o = other, p = o ? [o.w.x, o.w.y] : there;
      if (!p) break;
      me?.leanTo(p[0], p[1], now, 1700, 5);
      o?.leanTo(at[0], at[1], now, 1700, 5);
      const top = Math.min(at[1], p[1]) - head - 6;
      fx.after(350, () => fx.spawn("heart", (at[0] + p[0]) / 2, top, { vy: -7, life: 1900, sway: 1 }));
      break;
    }
    case "speak": case "tell":
      if (there && me) me.turn(there[0], there[1], now, 3500);
      if (at && other) other.turn(at[0], at[1], now, 3000);
      break;
    case "sing": case "compose": case "teach_song":
      if (at) for (let i = 0; i < 6; i++) fx.after(i * 260, () => fx.spawn("note", at[0] + (i % 2 ? 5 : -4), at[1] - head, { vx: (i % 3 - 1) * 5, vy: -15, life: 1700, sway: 2 }));
      if (at && other) other.turn(at[0], at[1], now, 2500);
      break;
    case "call":   // the creature comes trotting (the engine moves it); the caller hops
      me?.react("happy", now, 1000);
      if (at) { fx.spawn("note", at[0] - 6, at[1] - head - 2, { vy: -12, life: 1100, sway: 2 }); }
      break;
    case "write": {
      const p = there ?? (at && [at[0], Math.max(OY - 10, at[1] - 30)]);
      if (p) fx.burst("grit", p[0], p[1], 6, 16, { g: 60, life: 800 });
      break;
    }
    case "scrub": {
      const p = there ?? (at && [at[0], Math.max(OY - 10, at[1] - 30)]);
      if (p) { fx.spawn("puff", p[0], p[1], { life: 500 }); fx.burst("grit", p[0], p[1], 8, 24, { g: 70, life: 800 }); }
      break;
    }
    case "ask_book":
      if (there) { fx.burst("page", there[0], there[1] - 8, 3, 14); fx.burst("sparkle", there[0], there[1] - 8, 5, 20); }
      break;
    case "use": case "teach": case "arrange": case "name": case "fiddle":
      if (thing) { wiggle(fx, thing); if (a.type !== "use" && a.type !== "fiddle") fx.burst("sparkle", thing.x, thing.y - 8, 4, 18); }
      if (thing && a.loud) for (let i = 0; i < 3; i++) fx.after(i * 180, () => fx.spawn("note", thing.x + (i - 1) * 5, thing.rect.y, { vx: (i - 1) * 5, vy: -14, life: 1300, sway: 2 }));   // it rang
      break;
    case "put_away": case "take_out": case "hang": {   // into its place in a low arc, and a little dust; or out of it, into the paws
      const pic = picture(a.what), kept = c.kept(a.what), place = thing ? [thing.x, thing.y - thing.rect.h / 2] : kept ? [kept.x, kept.y - kept.rect.h / 2] : c.where(a.to);   // where it stands now; in a chest, the chest
      if (!at || !place) break;
      const paws = [at[0], at[1] - head * 0.6], out = a.type === "take_out";
      if (thing && !out) thing.s.visible = false;
      if (pic) fx.fly(pic[0], out ? place : paws, out ? paws : place, 480, pic[1], () => {
        if (out) return;
        if (thing && !thing.s.destroyed) { thing.s.visible = true; pop(fx, thing, 300); }
        else if (kept && !kept.s.destroyed) wiggle(fx, kept);   // gone into it
        fx.spawn("dust", place[0], place[1] + 3, { life: 450 });
        if (a.type === "hang") fx.burst("sparkle", place[0], place[1], 3, 14);
      });
      else if (thing && !thing.s.destroyed) thing.s.visible = true;
      break;
    }
    case "look": case "watch": case "listen":   // it has seen what it wanted to see
      if (there) fx.spawn("glint", there[0], there[1] - 4, { life: 500 });
      break;
    case "tend":
      if (thing) { wiggle(fx, thing); fx.burst("leaf", thing.x, thing.rect.y + 4, 4, 14, { tint: 0x8fd06a, life: 800 }); }
      break;
    case "dance":   // a last hop
      me?.react("happy", now, 700);
      if (at) fx.burst("note", at[0], at[1] - head, 3, 16, { life: 1100 });
      break;
    case "babble":
      if (at && other) other.turn(at[0], at[1], now, 1800);
      break;
    case "nap":   // up again, with a stretch
      me?.react("stretch", now, 1400);
      break;
    case "go":
      if (at) fx.spawn("dust", at[0], at[1] - 2, { life: 400 });
      break;
    case "eat":   // the last mouthful: crumbs, and the bowl or plant gives a little
      if (thing) wiggle(fx, thing);
      if (at) fx.burst("speck", at[0], at[1] - 6, 5, 14, { g: 60, life: 500, tint: 0xd9b36a });
      break;
    case "machine_take": case "machine_feed": {   // SPEC-v3.5 §4.3: what is fed goes in; the machine shakes, and what it gives drops from its tray into the paws
      const m = [...c.things.values()].find((t) => t.obj.fix?.machine), bit = a.type === "machine_take" ? a.what : a.to;
      if (!m || !at) break;
      const tray = [m.x, m.y - 6], paws = [at[0], at[1] - head * 0.6], fed = a.type === "machine_feed" ? picture(a.what) : null;
      if (fed) fx.fly(fed[0], paws, [m.x, m.y - m.rect.h * 0.55], 450, fed[1]);
      fx.after(fed ? 560 : 0, () => {
        if (!m.s.destroyed) wiggle(fx, m);
        fx.burst("glint", m.x, m.rect.y + 5, 4, 20);
        if (bit && has(`bit.${bit}`)) fx.fly(tex(`bit.${bit}`), tray, paws, 560, 1, () => fx.burst("sparkle", paws[0], paws[1], 3, 14));
      });
      break;
    }
    case "lay_egg": case "paint":
      if (at) fx.burst("sparkle", at[0], at[1] - 6, 8, 28);
      break;
  }
}
