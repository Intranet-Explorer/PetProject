// The Works (SPEC-v3.5.1 §1): the machine room's vending machine, alive. Its sheet (own/src/works.py) has a row for
// each of idle, take, work, drop; the sprite's `works` field says where its windows, hopper and belt are. Between acts
// it runs its idle frames (its `.lit` sprite's while the engine has it lit) and dims the window of anything it is out
// of. On `machine_feed` what is fed goes into the hopper, which gulps; on either act it works (light runs up its
// tubes), the window of what it gives lights, and the belt carries that out and throws it into the pet's paws.
import { Graphics, Sprite } from "pixi.js";
import type { Texture } from "pixi.js";
import type { Act, Snap } from "../types";
import type { Cast } from "./acts";
import { def, has, tex } from "./assets";
import type { Still, Thing } from "./still";

type Works = { windows: [number, number, number, number][]; materials: string[]; hopper: [number, number]; belt: [number, number, number, number]; fps: Record<string, number> };
type Show = { t0: number; feed: boolean; pick: number };

const LINGER = 1600;   // how long the window of what it gave stays lit after the belt stops
const base = (sprite: string) => sprite.replace(/\.lit$/, "");
const works = (t: Thing) => (def(base(t.sprite)) as { works?: Works } | null)?.works ?? null;
const frames = (name: string, mode: string) => def(name)?.anims?.[mode]?.frames.length ?? 1;

let show: Show | null = null;
let snap: Snap | null = null;
let over: { g: Graphics; on: Sprite; key: string } | null = null;
let shown = "";
const carried = new Map<string, string[]>();   // what each pet carried at the last snapshot this has seen (fed bits leave its paws before the act is played)

/** How long each part of a show lasts, in ms, from the sheet's frames and their pace. */
function plan(name: string, w: Works, feed: boolean): [string, number][] {
  return (feed ? ["take", "work", "drop"] : ["work", "drop"]).map((m) => [m, (frames(name, m) / (w.fps[m] ?? 8)) * 1000]);
}
/** Where a show is at `now`: the part and the frame of it, or null once it is over. */
function at(name: string, w: Works, s: Show, now: number): [string, number] | null {
  let t = now - s.t0;
  if (t < 0) return null;
  for (const [m, ms] of plan(name, w, s.feed)) {
    if (t < ms) return [m, Math.floor((t / ms) * frames(name, m))];
    t -= ms;
  }
  return null;
}
const span = (name: string, w: Works, feed: boolean) => plan(name, w, feed).reduce((n, [, ms]) => n + ms, 0);

/** Every frame (room.ts): the machine's picture for now, and what is laid over its windows. */
export function step(still: Still, sn: Snap, now: number) {
  if (sn !== snap) {
    snap = sn;
    carried.clear();
    for (const p of sn.pets) if (p.carrying?.length) carried.set(p.id, p.carrying);
  }
  const t = [...still.things.values()].find((t) => t.obj.fix?.machine && works(t));
  if (!t || t.s.destroyed) { if (over) { over.g.destroy(); over = null; } return; }
  const w = works(t)!, name = base(t.sprite);
  const playing = show ? at(name, w, show, now) : null;
  const [mode, i] = playing ?? ["idle", Math.floor((now / 1000) * (def(t.sprite)?.anims?.idle?.fps ?? 3)) % frames(t.sprite, "idle")];
  const key = `${t.sprite}|${mode}|${i}`;
  if (key !== shown || t.s.texture.destroyed) { shown = key; t.s.texture = tex(mode === "idle" ? t.sprite : name, mode, i); }
  // the window of what it gives, lit from halfway through its work until a little after the belt stops; dim where it is out
  const lit = show && show.pick >= 0 && now - show.t0 > span(name, w, show.feed) - (frames(name, "drop") / (w.fps.drop ?? 8)) * 1000 - 500 && now - show.t0 < span(name, w, show.feed) + LINGER ? show.pick : -1;
  const out = (sn.machine?.materials ?? w.materials).map((m) => (sn.machine?.stock?.[m] ?? 1) <= 0);
  const blink = lit >= 0 ? Math.floor(now / 160) % 2 : 0, look = `${out.join()}|${lit}|${blink}`;
  if (!over || over.on !== t.s) {
    over?.g.destroy();
    over = { g: new Graphics(), on: t.s, key: "" };
    t.s.parent?.addChild(over.g);
  }
  over.g.zIndex = t.s.zIndex + 0.01;
  over.g.position.set(t.s.x - t.rect.w / 2, t.s.y - t.rect.h);
  if (look === over.key) return;
  over.key = look;
  const g = over.g.clear();
  w.windows.forEach(([x, y, ww, hh], n) => { if (out[n] && n !== lit) g.rect(x, y, ww, hh).fill({ color: 0x06101c, alpha: 0.62 }); });
  if (lit >= 0) {
    const [x, y, ww, hh] = w.windows[lit];
    g.rect(x, y, ww, hh).fill({ color: 0xddfffc, alpha: 0.28 });
    g.rect(x, y, ww, hh).stroke({ width: 1, color: blink ? 0xefaf19 : 0xfdfdb5, alignment: 1 });   // (outside the glass: on its frame, and a faint ring past it)
    g.rect(x - 1, y - 1, ww + 2, hh + 2).stroke({ width: 1, color: 0xfdfdb5, alpha: 0.3, alignment: 1 });
  }
}

/** A machine act (px/acts.ts): played out on The Works, if this room has it. False: no such machine here (an older
 *  room, an older recording), and acts.ts plays it its own way. */
export function playMachine(a: Act, c: Cast, picture: (what: string | null | undefined) => [Texture, number] | null): boolean {
  const m = [...c.things.values()].find((t) => t.obj.fix?.machine && works(t));
  if (!m) return false;
  const w = works(m)!, name = base(m.sprite), feed = a.type === "machine_feed", bit = feed ? a.to : a.what;
  const box = (p: number[]) => [m.rect.x + p[0], m.rect.y + p[1]];
  const paws = () => { const me = c.pets.get(a.pet); return me ? [me.w.x, me.w.y - me.tall * 0.6] : null; };
  const pick = (snap?.machine?.materials ?? w.materials).indexOf(bit ?? "");
  const lead = feed ? 450 : 0;
  if (feed) {   // what goes in: from its paws (or from where it stood, if it never had it in them), or the bits it carried
    const hop = box(w.hopper), p = paws(), g = c.ghosts.get((a.what ?? "").trim().toLowerCase());
    const from = g && p && Math.hypot(g.x - p[0], g.y - p[1]) > 36 ? [g.x, g.y - g.h / 2] : p;
    const fed: [Texture, number][] = a.what === "bits" ? (carried.get(a.pet) ?? []).slice(0, 3).filter((b) => has(`bit.${b}`)).map((b) => [tex(`bit.${b}`), 1]) : [picture(a.what)].filter((x): x is [Texture, number] => !!x);
    if (from) fed.forEach(([t, s], i) => c.fx.after(i * 120, () => c.fx.fly(t, from, hop, lead - i * 60, s)));
  }
  show = { t0: c.now + lead, feed, pick };
  if (!bit || !has(`bit.${bit}`)) return true;   // it gave nothing back (left it in the machine for whoever comes next)
  // the belt: out of the mouth along to the end in the drop's first frames, then off the end into the paws
  const drop = (frames(name, "drop") / (w.fps.drop ?? 8)) * 1000, start = lead + span(name, w, feed) - drop;
  const [x0, y0, x1, y1] = w.belt, from = box([x0, y0]), end = box([x1, y1]);
  c.fx.after(start, () => {
    if (m.s.destroyed || !m.s.parent) return;
    const s = new Sprite(tex(`bit.${bit}`));
    s.anchor.set(0.5, 1);
    s.zIndex = m.s.zIndex + 0.02;
    m.s.parent.addChild(s);
    c.fx.tween(drop * 0.66, (k) => s.position.set(Math.round(from[0] + (end[0] - from[0]) * k), Math.round(from[1] + (end[1] - from[1]) * k)), () => {
      s.destroy();
      const p = paws() ?? [end[0] + 12, end[1] + 14];
      c.fx.fly(tex(`bit.${bit}`), [end[0], end[1] - 6], p, 520, 1, () => c.fx.burst("sparkle", p[0], p[1], 3, 14));
    });
  });
  return true;
}
