// SPEC-v5.3 §1.4, §2.3: what habits and projects leave standing in a room, drawn over the room's still layer.
// (Helper A writes the project sites' section; helper B the marks'. The lead merges the two.)
import type { Site5, Snap, Tile } from "./types";

// ---- marks (helper B) ----

/** SPEC-v5.3 §1.4 (habits.view, the snapshot's `v5.marks53`): a pile (bits on one tile, by count), a hoard (its box,
 *  with a lock mark), a mark (scratched on a wall, which walls already draw, or stones stacked at the stones). */
export type Mark53 = { id: string; kind: "pile" | "hoard" | "mark"; room: string; pos: Tile | null; n: number; by: string | null; bits: string[];
  found: boolean; words: string; block: boolean };

/** How each mark is drawn: `layers` sprites of its bit (a pile: its count, which still.ts draws as work.ts's pileOf) or of a pebble (stones); `lock`: a padlock
 *  over the box until it is found; `tag`: its count beside it. */
export type MarkLook = { kind: Mark53["kind"]; pos: Tile; sprite: string | null; layers: number; lock: boolean; tag: string | null; words: string };
export const MARKS53: Record<Mark53["kind"], (m: Mark53) => MarkLook | null> = {
  "pile": (m) => (m.pos && m.n ? { kind: "pile", pos: m.pos, sprite: `bit.${m.bits[m.bits.length - 1] ?? "wood"}`, layers: m.n, lock: false, tag: m.n > 1 ? String(m.n) : null, words: m.words } : null),
  "hoard": (m) => (m.pos ? { kind: "hoard", pos: m.pos, sprite: null, layers: 0, lock: !m.found, tag: null, words: m.words } : null),
  "mark": (m) => (m.pos ? { kind: "mark", pos: m.pos, sprite: "bit.pebble", layers: Math.min(4, 1 + Math.floor(m.n / 2)), lock: false, tag: null, words: m.words } : null),   // (on a wall: marks.ts draws the scratch)
};

/** The marks standing in this room, as they are drawn. */
export function marksIn(snap: Snap, room: string): MarkLook[] {
  return (snap.v5?.marks53 ?? []).filter((m) => m.room === room).map((m) => MARKS53[m.kind]?.(m) ?? null).filter((x): x is MarkLook => !!x);
}

// ---- project sites (helper A): drawn by kind and stage (projects.view sends them as `v5.sites`), stand-ins from
// building.toml's and kinds.toml's sprites; the plots outdoors marked while free; the board's project rows. No DOM or Pixi.

/** What a site looks like at a stage before it is done, whatever its kind: a marked plot, the ground cleared, a frame,
 *  covered over, falling to pieces. */
export const STAGES: Record<string, string> = { bare: "decor.stepping stone", cleared: "decor.rocks", framed: "fix.site", covered: "fix.site.half", done: "", decaying: "decor.planks" };

/** Each kind's stages: its finished look (stand-ins), and where it differs before. */
export const SITES: Record<string, Partial<Record<string, string>>> = {
  shelter: { done: "fix.built.hutch" },
  bridge: { done: "fix.footbridge" },
  hearth: { framed: "decor.rocks", covered: "fix.fire pit.off", done: "fix.fire pit" },
  bed: { done: "fix.bed" },
  "bell post": { done: "station.bell post" },
  lookout: { done: "fix.pixellab.ladder" },
  "garden plot": { cleared: "fix.melon bed", covered: "fix.melon bed.growing", done: "fix.melon bed.growing" },
  "workshop corner": { done: "fix.workbench" },
  statue: { done: "decor.plinth" },
  "library nook": { done: "decor.bookshelf" },
  build: { done: "fix.site.half" },   // (build.py's own are drawn by build.py: fix.site, fix.built.<it>)
};

/** The landmarks outdoors.plots puts up for the model to name: what each is drawn as. */
export const LANDMARKS: Record<string, string> = { willow: "fix.shade tree", "standing stone": "fix.flat stone" };

/** The sprite a site is drawn with now: its kind's for this stage, else the stage's; a free plot is a marked one. */
export function siteSprite(s: Pick<Site5, "kind" | "stage">): string {
  const stage = s.stage in STAGES ? s.stage : "bare";
  return (s.kind && SITES[s.kind]?.[stage]) || STAGES[stage] || STAGES.bare;
}

/** The stand-ins a site draws on the ground (a plot, the cleared earth), the rest stand up. */
export const flatStage = (stage: string) => stage === "bare" || stage === "cleared";

/** A board row for a project. */
export type ProjectRow = { id: string; kind: string; state: string; words: string; owners: string[] };
const ORDER = ["orphaned", "under way", "blocked", "planned", "done", "abandoned"];
/** §8 the board's projects, by state (orphans first, in words: "Spoon's shelter stands half built in the meadow"). */
export function projectRows(rows: ProjectRow[] | null | undefined): { state: string; words: string[] }[] {
  const out: { state: string; words: string[] }[] = [];
  for (const st of ORDER) {
    const w = (rows ?? []).filter((r) => r.state === st).map((r) => r.words);
    if (w.length) out.push({ state: st, words: w });
  }
  return out;
}
