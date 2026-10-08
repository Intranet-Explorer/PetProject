// The room canvas (SPEC §13). The world is data; this only draws it. No art assets: every shape is code.
import { Application, Container, Graphics, Text } from "pixi.js";
import type { World } from "./main";
import { PetBody } from "./pet";
import type { Genome } from "./pet";
import { PALETTE, thingSvg } from "./things";

/** A paint colour laid over the room's plain colour, so a painted room stays a calm stage for the creature. */
function tint(base: number, name: string | null) {
  if (!name || !PALETTE[name]) return base;
  const paint = parseInt(PALETTE[name].slice(1), 16), mix = (shift: number) =>
    Math.round(((base >> shift) & 255) * 0.5 + ((paint >> shift) & 255) * 0.5) << shift;
  return mix(16) | mix(8) | mix(0);
}

const T = 56, PAD = 30;
const INK = 0x16241f, MUTED = 0x586a63, FLOOR = 0xe6dcc8, WALL = 0xcfc3ab;
const SKY: Record<string, number> = { day: 0x9fd3ea, dusk: 0xf0a868, night: 0x1c2550 };
const DARK: Record<string, number> = { day: 0, dusk: 0.2, night: 0.48 };
const mid = (p: number[]) => [PAD + p[0] * T + T / 2, PAD + p[1] * T + T / 2];

type Draw = (g: Graphics, x: number, y: number, state: string | undefined, phase: string) => void;
const DRAW: Record<string, Draw> = {
  lamp(g, x, y, s) {
    if (s === "on") g.circle(x, y - 12, 64).fill({ color: 0xffd76a, alpha: 0.25 });
    g.rect(x - 2, y - 6, 4, 22).fill(INK).rect(x - 9, y + 14, 18, 4).fill(INK);
    g.poly([x - 14, y - 4, x + 14, y - 4, x + 7, y - 22, x - 7, y - 22]).fill(s === "on" ? 0xffc93c : 0x9aa8a2);
  },
  plant(g, x, y) {
    g.poly([x - 10, y + 2, x + 10, y + 2, x + 7, y + 18, x - 7, y + 18]).fill(0xa8623a);
    g.circle(x, y - 10, 10).fill(0x3f9b63).circle(x - 9, y - 2, 8).fill(0x4fae72).circle(x + 9, y - 2, 8).fill(0x2f8553);
  },
  bowl(g, x, y, s) {
    g.ellipse(x, y + 6, 17, 9).fill(0x6f8fa8);
    g.ellipse(x, y + 3, 13, 5).fill(0xdfe7ea);
    if (s !== "empty") g.ellipse(x, y + 3, s === "full" ? 13 : 7, s === "full" ? 5 : 3).fill(0x9a6a3c);
  },
  ball(g, x, y) {
    g.circle(x, y + 4, 11).fill(0xd9483b).circle(x - 4, y, 3).fill({ color: 0xffffff, alpha: 0.7 });
  },
  blanket(g, x, y) {
    g.roundRect(x - 22, y - 12, 44, 28, 5).fill(0x8a6fb0);
    g.rect(x - 22, y - 3, 44, 3).fill(0xc9b8e3).rect(x - 22, y + 6, 44, 3).fill(0xc9b8e3);
  },
  "music box"(g, x, y, s) {
    g.rect(x - 14, y - 2, 28, 18).fill(0x2f8f8a).rect(x - 14, y - 8, 28, 6).fill(0x1f6b67);
    if (s === "playing") g.circle(x + 16, y - 20, 4).fill(INK).rect(x + 19, y - 34, 2, 14).fill(INK).circle(x + 4, y - 26, 3).fill(INK).rect(x + 6, y - 37, 2, 11).fill(INK);
  },
  rock(g, x, y) {
    g.poly([x - 15, y + 14, x - 11, y - 2, x - 1, y - 9, x + 12, y - 3, x + 16, y + 14]).fill(0x8d9793);
  },
  window(g, _x, y, s, phase) {
    g.rect(PAD - 18, y - T / 2 + 4, 14, T - 8).fill(SKY[phase]).stroke({ width: 3, color: INK });
    if (s === "open") g.poly([PAD - 4, y - T / 2 + 4, PAD + 12, y - T / 2 + 12, PAD + 12, y + T / 2 - 12, PAD - 4, y + T / 2 - 4]).fill({ color: 0xffffff, alpha: 0.75 }).stroke({ width: 2, color: INK });
    else g.rect(PAD - 12, y - T / 2 + 4, 2, T - 8).fill(INK);
  },
  bed(g, x, y) {
    g.roundRect(x - 24, y - 16, 48, 34, 5).fill(0x5f86b3);
    g.roundRect(x - 20, y - 12, 16, 26, 4).fill(0xf3f1e8);
  },
  mirror(g, x, y) {
    g.roundRect(x - 11, y - 22, 22, 42, 9).fill(0xcfe3e8).stroke({ width: 3, color: 0x7b6a4a });
    g.poly([x - 5, y - 4, x + 3, y - 14, x + 5, y - 12, x - 3, y - 2]).fill({ color: 0xffffff, alpha: 0.8 });
  },
};

export class Room {
  onTile: (x: number, y: number) => void = () => {};
  private app = new Application();
  private things = new Container();
  private floor = new Graphics();
  private size = [12, 8];
  private painted = "";
  private bouncing: Graphics[] = [];
  private shade = new Graphics();
  private body = new PetBody();
  private wobble = 0;
  private pet = new Container();
  private bubble = new Container();
  private dots = new Graphics();
  private goal = [0, 0];
  private pace = 2;
  private thinking = false;
  private placed = false;
  private distressed = false;
  private energy = 50;
  private asleep = false;

  async init(el: HTMLElement, w: number, h: number) {
    const [width, height] = [w * T + 2 * PAD, h * T + 2 * PAD];
    await this.app.init({ width, height, background: WALL, antialias: true, resolution: devicePixelRatio, autoDensity: true });
    el.append(this.app.canvas);
    this.size = [w, h];
    this.paint({ wall: null, floor: null });
    this.shade.rect(0, 0, width, height).fill(0x0b1030);
    this.body.scale.set(2);   // the creature is the focus: twice its v1 size
    this.pet.addChild(this.body, this.dots);
    for (const x of [-12, 0, 12]) this.dots.circle(x, -78, 4).fill(INK);
    this.app.stage.addChild(this.floor, this.things, this.shade, this.pet, this.bubble);
    this.app.stage.eventMode = "static";
    this.app.stage.hitArea = this.app.screen;
    this.app.stage.on("pointerdown", (e) => {
      const [x, y] = [Math.floor((e.global.x - PAD) / T), Math.floor((e.global.y - PAD) / T)];
      if (x >= 0 && x < w && y >= 0 && y < h) this.onTile(x, y);
    });
    this.app.ticker.add((t) => {
      // Display only: walk a tile per engine tick, bob faster with more energy, tremble in distress.
      const now = performance.now(), [dx, dy] = [this.goal[0] - this.pet.x, this.goal[1] - this.pet.y];
      const far = Math.hypot(dx, dy), stride = Math.min(far, (T * 1.3 * t.deltaMS) / (this.pace * 1000));
      if (far > 0.5) this.pet.position.set(this.pet.x + (dx / far) * stride, this.pet.y + (dy / far) * stride);
      const hop = far > 2 ? Math.abs(Math.sin(now / 130)) * 5 : 0;
      this.body.y = this.asleep ? 0 : Math.sin(now / (900 - this.energy * 5)) * 3 - hop;
      this.body.x = this.distressed ? Math.sin(now / 35) * 1.5 : 0;
      const squash = this.asleep ? 0 : Math.sin(now / 260) * this.wobble * 0.07;
      this.body.scale.set(2 * (1 + squash), 2 * (1 - squash));
      for (const b of this.bouncing) b.pivot.y = Math.abs(Math.sin(now / 180)) * 9;
      this.dots.visible = this.thinking;
      this.dots.alpha = 0.35 + 0.35 * (1 + Math.sin(now / 250));
      this.bubble.position.set(this.pet.x, this.pet.y - 58);
    });
  }

  /** A still picture of a body, for the portraits gallery (§8). */
  picture(genome: Genome, stage: string): string {
    const body = new PetBody();
    body.draw(genome, stage, 80, false);
    body.scale.set(2);
    const url = (this.app.renderer.extract.canvas(body) as HTMLCanvasElement).toDataURL();
    body.destroy({ children: true });
    return url;
  }

  /** The room's colours follow what the pet has painted (SPEC-v2 §6). */
  private paint(room: { wall: string | null; floor: string | null }) {
    const [w, h] = this.size, f = this.floor.clear();
    this.app.renderer.background.color = tint(WALL, room.wall);
    f.rect(PAD, PAD, w * T, h * T).fill(tint(FLOOR, room.floor));
    for (let i = 1; i < w; i++) f.rect(PAD + i * T, PAD, 1, h * T).fill({ color: INK, alpha: 0.07 });
    for (let j = 1; j < h; j++) f.rect(PAD, PAD + j * T, w * T, 1).fill({ color: INK, alpha: 0.07 });
    f.rect(w * T + PAD + 4, PAD + 4 * T + 4, 14, T - 8).fill(0x8a5a36).stroke({ width: 3, color: INK }); // the door
    this.painted = `${room.wall}/${room.floor}`;
  }

  update(w: World, tickSeconds: number) {
    if (this.painted !== `${w.room.wall}/${w.room.floor}`) this.paint(w.room);
    this.pace = tickSeconds;
    this.thinking = !!w.thinking && !w.sleep;
    for (const c of this.things.removeChildren()) c.destroy();
    this.bouncing = [];
    const g = new Graphics();
    this.things.addChild(g);
    for (const [name, o] of Object.entries(w.objects)) {
      const [x, y] = mid(o.pos);
      if (o.made) {   // something it made: drawn from its recipe, and showing what it has been taught to do (§7)
        const doing = o.active ? o.made.behavior?.do ?? "" : "";
        if (o.state === "on" || doing === "glow") g.circle(x, y, 46).fill({ color: 0xffd76a, alpha: 0.28 });
        if (doing === "dim") g.circle(x, y, 46).fill({ color: 0x0b1030, alpha: 0.22 });
        if (doing === "hum") for (const r of [30, 38, 46]) g.circle(x, y, r).stroke({ width: 1.5, color: INK, alpha: 0.25 });
        const recolor = doing.startsWith("change_color:") ? doing.split(":")[1] : undefined;
        const drawn = new Graphics().svg(`<svg xmlns="http://www.w3.org/2000/svg">${thingSvg(o.made.recipe, 0, 0, recolor)}</svg>`);
        drawn.position.set(x, y);
        if (doing === "bounce") this.bouncing.push(drawn);
        this.things.addChild(drawn);
      } else DRAW[name]?.(g, x, y, o.state, w.clock.phase);
      const label = new Text({ text: name, style: { fontFamily: "ui-monospace, Menlo, monospace", fontSize: 10, fill: MUTED } });
      label.anchor.set(name === "window" ? 0 : 0.5, 0);
      label.position.set(name === "window" ? 2 : x, y + (name === "window" ? T / 2 - 2 : o.made ? 24 : 19));
      this.things.addChild(label);
    }
    this.shade.alpha = Math.max(0, DARK[w.clock.phase] - (w.objects.lamp.state === "on" ? 0.18 : 0));

    this.goal = mid(w.pet.pos);
    if (!this.placed) this.pet.position.set(this.goal[0], this.goal[1]);
    this.placed = true;
    this.energy = w.pet.needs.energy;
    this.asleep = !!w.sleep;
    this.distressed = Object.values(w.pet.needs).some((v) => v < 20);
    this.wobble = w.pet.genome.wobble;
    this.body.draw(w.pet.genome, w.pet.stage, w.pet.needs.comfort, !!w.sleep);

    for (const c of this.bubble.removeChildren()) c.destroy();
    if (w.pet.said && (w.tick - w.pet.said[0]) * tickSeconds <= 12) {
      const text = new Text({ text: w.pet.said[1], style: { fontFamily: "system-ui, sans-serif", fontSize: 13, fill: INK, wordWrap: true, wordWrapWidth: 200 } });
      text.anchor.set(0.5, 1);
      const box = new Graphics().roundRect(-text.width / 2 - 8, -text.height - 6, text.width + 16, text.height + 12, 8).fill(0xffffff).stroke({ width: 2, color: INK });
      this.bubble.addChild(box, text);
    }
  }
}
