// SPEC-v5.1 §7, §8 (helper C): what the page shows of the grammar, worked out with no DOM or Pixi so that
// view/check-work.ts runs it under node: what an invented thing is drawn from (its own sprite, once it is there, else
// the compositor's parts), a thing's recipe on its card, the header's tier, and the Lab's Grammar section (a hob's
// knowing is spirit.ts knowsRows, a board row's "needs" work.ts jobWords). The engine sends the words (lab4.recipe_view, header, knows_card, grammar).
import type { Recipe5, Tier5 } from "./types";

type Part = { part: string; at: string | null; material?: string; color?: string };
type Drawn = { parts: Part[]; size?: string; glow?: boolean; draw?: Part[] | null; sprite?: string | null };

/** §7.2 the folder's picture at 16 or 24 px (tools/sprites/invent.py leaves both). */
export const spriteUrl = (sprite: string, px = 16) => `/art/${sprite}/${px}.png`;
/** A v5.1 invention is composited from `draw` (its parts as the compositor's); a v3.5 one from its own parts. */
export const inventedLook = (inv: Drawn) => (inv.draw?.length ? { parts: inv.draw, size: inv.size ?? "small", glow: inv.glow } : inv);
/** §7.2 what an invented kind is drawn from: its own sprite when the snapshot names it and it has loaded; until then, and
 *  if it never comes, the compositor's parts. */
export function drawSource(inv: Drawn, loaded: (url: string) => boolean): { url: string } | { parts: Part[] } {
  const url = inv.sprite ? spriteUrl(inv.sprite) : null;
  return url && loaded(url) ? { url } : { parts: inventedLook(inv).parts };
}

const andList = (xs: string[]) => (xs.length > 1 ? `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}` : xs.join(""));
const an = (w: string) => (/^[aeiou]/.test(w) ? "an" : "a");

/** §8 a thing's recipe as its card's rows, [what, words]: its parts and materials, what it does, its tier, who can make
 *  it, and "invented by X for Y" with how it works in the inventor's words. */
export function recipeRows(r: Recipe5 | null | undefined): [string, string][] {
  if (!r) return [];
  const rows: [string, string][] = [
    ["parts", andList(r.parts.map((p) => `${an(p.part)} ${p.part} of ${p.material}`))],
    ["materials", r.materials.join(", ")],
    ["charged with", r.charge ?? ""],
    ["does", r.does.length ? r.does.join("; ") : "nothing: it is kept for its own sake"],
    ["tier", r.tier],
    ["can make it", r.knows.length ? andList(r.knows) : "nobody living"],
    ["invented", r.invented ? `by ${r.invented.by}${r.invented.for ? ` for ${r.invented.for}` : ""}${r.invented.how ? `: “${r.invented.how}”` : ""}` : ""],
  ];
  return rows.filter(([, v]) => v);
}

/** §8 the header's words: the house's tier, and its fall while it is recent. */
export const tierChips = (t: Tier5 | null | undefined) => [t?.tier ?? "", t?.fall ?? ""].filter(Boolean);

/** §8 the Lab's Grammar section (lab4.grammar). */
export type Grammar5 = { day: number; days: number; invent: { proposed: number; accepted: number; refused: number }; refused: { words: string; n: number }[];
  made_by: { recipe: number; invention: number }; recipes: { house: number };
  pets: { id: string; name: string; tier: string; recipes: number; of: number; read: number; studied: number; taught: number; chains: number }[];
  tier: { day: number; tier: number; words: string }[]; studied: number; taught: number; read: Record<string, number>; chains: number;
  sprites: { generated: number; composited: number; failed: number } };
const pairs = (r: Record<string, number>) => Object.entries(r).filter(([, n]) => n).map(([k, n]) => `${k} ${n}`).join(", ") || "none";
export function grammarRows(g: Grammar5): { house: [string, string][]; refused: [string, string][]; pets: [string, string][] } {
  return {
    house: [["Inventions proposed / accepted / refused", `${g.invent.proposed} / ${g.invent.accepted} / ${g.invent.refused}`],
      ["Made by a recipe / by inventing it", `${g.made_by.recipe} / ${g.made_by.invention}`],
      ["Recipes the house knows", String(g.recipes.house)],
      ["The house's tier by day", g.tier.map((t) => `day ${t.day}: ${t.words}`).join("; ") || "not yet kept"],
      ["Study sessions, teachings", `${g.studied}, ${g.taught}`],
      ["Reads by where the question came from", pairs(g.read)], ["Chains of three read on", String(g.chains)],
      ["Sprites drawn / composited / failed", `${g.sprites.generated} / ${g.sprites.composited} / ${g.sprites.failed}`]],
    refused: g.refused.map((r) => [`“${r.words}”`, String(r.n)]),
    pets: g.pets.map((p) => [p.name, `${p.tier} · ${p.recipes} recipes, knows of ${p.of} · read ${p.read}, chains ${p.chains} · studied ${p.studied}, taught ${p.taught}`]),
  };
}
