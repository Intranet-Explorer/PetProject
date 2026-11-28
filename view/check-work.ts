// Self-check for the page's v5 work (SPEC-v5.0 §5: the board's rows, ages in words, piles by count; SPEC-v5.1 §7, §8: an
// invented thing drawn from its parts until its sprite is in, a thing's recipe on its card, the header's tier, a hob's
// knowing, a board row's "needs", the Lab's Grammar section): node check-work.ts
import assert from "node:assert/strict";
import { ageWords, pileOf, workRows } from "./src/work.ts";
import { drawSource, grammarRows, inventedLook, recipeRows, spriteUrl, tierChips } from "./src/invent.ts";
import type { Grammar5 } from "./src/invent.ts";
import { cardRows, knowsRows } from "./src/spirit.ts";
import type { Board5, Recipe5 } from "./src/types.ts";

// SPEC-v5.1 §7.2: a v5.1 invention is composited from its `draw` (the compositor's parts) while it has no sprite, and while
// its sprite has not loaded; once the snapshot names it and it has loaded, the sprite; a v3.5 invention from its own parts
const tube = [{ part: "bent pipe", at: null, material: "wood" }, { part: "coil", at: "top", material: "metal" }];
const inv = { parts: [{ part: "tube", at: null }, { part: "spring", at: null }], draw: tube, sprite: null as string | null };
assert.deepEqual(drawSource(inv, () => true), { parts: tube }, "no sprite yet: the compositor draws it");
inv.sprite = "own/invented/6e5776c53515";
assert.deepEqual(drawSource(inv, () => false), { parts: tube }, "named but not loaded: still composited");
assert.deepEqual(drawSource(inv, (u) => u === "/art/own/invented/6e5776c53515/16.png"), { url: spriteUrl(inv.sprite) }, "landed: the view swaps to it");
const old = { parts: [{ part: "stick", at: null }, { part: "flame", at: "tip" }] };
assert.deepEqual(inventedLook(old), old, "a v3.5 invention is drawn from its own parts");

// §8 a thing's card: its recipe in words
const r: Recipe5 = { parts: [{ part: "tube", material: "wood", draw: "bent pipe", icon: "parts16/02-bent-pipe" }, { part: "spring", material: "metal", draw: "coil", icon: "parts16/25-coil-spring" }],
  materials: ["wood", "metal", "pebble"], charge: "pebble", does: ["it throws things", "it pours"], tier: "mechanisms", knows: ["Pansy", "Odo"],
  invented: { by: "Pansy", by_id: "p1", for: "the beetles", how: "a spring behind the tube throws a pebble" }, sprite: null };
assert.deepEqual(recipeRows(r), [["parts", "a tube of wood and a spring of metal"], ["materials", "wood, metal, pebble"], ["charged with", "pebble"],
  ["does", "it throws things; it pours"], ["tier", "mechanisms"], ["can make it", "Pansy and Odo"],
  ["invented", "by Pansy for the beetles: “a spring behind the tube throws a pebble”"]]);
assert.deepEqual(recipeRows({ ...r, charge: null, knows: [], invented: null, does: [] }).map(([k, v]) => `${k}: ${v}`),
  ["parts: a tube of wood and a spring of metal", "materials: wood, metal, pebble", "does: nothing: it is kept for its own sake", "tier: mechanisms", "can make it: nobody living"]);
assert.deepEqual(recipeRows(null), []);

// §8 the header: the house's tier, and its fall while recent; nothing while v5.1's knowledge is off (no `tier` sent)
assert.deepEqual(tierChips({ tier: "the house knows worked things", fall: null }), ["the house knows worked things"]);
assert.deepEqual(tierChips({ tier: "the house knows found things", fall: "nobody left knows the forge" }), ["the house knows found things", "nobody left knows the forge"]);
assert.deepEqual(tierChips(undefined), []);

// §8 a hob's card: its tier, what it knows (and how it came by it) and knows of (B's knows51), its reading list
const k = { tier: 1, tier_words: "worked things", recipes: [{ key: "kind:lantern", words: "how to make a lantern", from: "made", how: "made one" },
  { key: "kind:pebble thrower", words: "how to make a pebble thrower", from: "taught", how: "was shown how" }], of: [{ key: "kind:millstone", words: "how to make a millstone", from: "read", how: "read of it" }] };
assert.deepEqual(knowsRows(k, [{ title: "Catapult" }, { title: "Spring (device)" }]), [["Knows", "worked things"], ["Can make", "a lantern (made one) and a pebble thrower (was shown how)"],
  ["Knows of", "a millstone"], ["Has read", "Catapult; Spring (device)"]]);
assert.deepEqual(knowsRows(null, null), [], "v5.1's knowledge and book off: nothing more on the card");
assert.deepEqual(cardRows({ drive: "to be remembered" }), [["Drive", "to be remembered"]], "v4.2's card as it was");

// §8 the board: a wrong whose make step lacks something says so where its job would be
const nb: Board5 = { deficits: [{ id: "dark|r1|", kind: "dark", words: "the attic is dark at night", urgency: 2, since: 1995, needs: "glass, which nobody has" }], jobs: [], closed: [] };
assert.equal(workRows(nb, { tick: 2000, hour: 20 }, 24, () => null).open[0].job, "needs: glass, which nobody has");

// §8 the Lab's Grammar section
const g: Grammar5 = { day: 9, days: 10, invent: { proposed: 12, accepted: 7, refused: 5 }, refused: [{ words: "a reed tube won't take a metal spring: wood, metal or plank would", n: 3 }],
  made_by: { recipe: 40, invention: 6 }, recipes: { house: 14 }, pets: [{ id: "p1", name: "Pansy", tier: "worked things", recipes: 9, of: 2, read: 4, studied: 1, taught: 0, chains: 1 }],
  tier: [{ day: 8, tier: 1, words: "worked things" }, { day: 9, tier: 2, words: "mechanisms" }], studied: 3, taught: 1, read: { material: 4, death: 1, own: 0 }, chains: 1,
  sprites: { generated: 0, composited: 6, failed: 0 } };
const G = grammarRows(g);
assert.deepEqual(G.house.slice(0, 4), [["Inventions proposed / accepted / refused", "12 / 7 / 5"], ["Made by a recipe / by inventing it", "40 / 6"], ["Recipes the house knows", "14"],
  ["The house's tier by day", "day 8: worked things; day 9: mechanisms"]]);
assert.equal(G.house[5][1], "material 4, death 1");
assert.deepEqual(G.refused, [["“a reed tube won't take a metal spring: wood, metal or plank would”", "3"]]);
assert.equal(G.pets[0][1], "worked things · 9 recipes, knows of 2 · read 4, chains 1 · studied 1, taught 0");

// §5 piles: 1, 2–3, 4–7, 8 and more bits draw 1, 2, 3, 4 sprites; none, none
assert.deepEqual([0, 1, 2, 3, 4, 7, 8, 30].map(pileOf), [0, 1, 2, 2, 3, 3, 4, 4]);

// ages in words: the clock is at 20:00 on a day of 24 ticks an hour (it began 480 ticks ago, at tick 1520)
const H = 24, now = { tick: 2000, hour: 20 };
assert.equal(ageWords(now, 1990, H), "just now");
assert.equal(ageWords(now, 1520 + 3 * H, H), "since the night");
assert.equal(ageWords(now, 1520 + 9 * H, H), "since this morning");
assert.equal(ageWords(now, 1520 + 14 * H, H), "since this afternoon");
assert.equal(ageWords(now, 1520 + 18 * H, H), "since this evening");
assert.equal(ageWords(now, 1520 - 5 * H, H), "since yesterday");
assert.equal(ageWords(now, 1520 - 30 * H, H), "for two days");
assert.equal(ageWords(now, 1520 - 24 * 12 * H, H), "for 12 days");

// §5 the board: each deficit with its age and its job's taker; what closed today, newest first, with whom
const b: Board5 = {
  deficits: [{ id: "leak|r2|", kind: "leak", words: "water is coming into the storeroom", urgency: 3, since: 1520 + 9 * H },
    { id: "mess|r1|", kind: "mess", words: "the attic is a mess", urgency: 1, since: 1995 }],
  jobs: [{ deficit: "leak|r2|", taker: "p1", words: "a patch for the storeroom's leak" }, { deficit: "mess|r1|", taker: null, words: "" }],
  closed: [{ kind: "dark", words: "the music room is lit", by: "p2", tick: 1600 }, { kind: "cold", words: "the attic is warm", by: null, tick: 1900 }],
};
const names: Record<string, string> = { p1: "Pansy", p2: "Odo" };
const R = workRows(b, now, H, (id) => names[id] ?? null);
assert.deepEqual(R.open, [
  { kind: "leak", text: "water is coming into the storeroom", age: "since this morning", who: "Pansy is seeing to it", job: "a patch for the storeroom's leak", urgent: true },
  { kind: "mess", text: "the attic is a mess", age: "just now", who: null, job: "", urgent: false }]);
assert.deepEqual(R.closed.map((r) => [r.text, r.who]), [["the attic is warm", null], ["the music room is lit", "seen to by Odo"]]);
assert.equal(workRows(b, now, H, () => null).open[0].who, null, "a taker gone from the house is nobody");
assert.deepEqual(workRows(null, now, H, () => null), { open: [], closed: [] });   // (v5 off, or the board not yet in)
console.log("work check ok");

// SPEC-v5.1 §4.4 (the lead, the fix of 21 October 2026): an invention of its own is a row of the board, and a
// blocked one says what it waits on
const ib = { deficits: [], jobs: [{ deficit: "invent|rain hood#9", taker: "p1", words: "the rain hood, a thing nobody has made", invent: true, blocked: "needs reed; the garden has none" }], closed: [] };
const ir = workRows(ib as never, { tick: 2000, hour: 20 }, 24, () => "Pansy").open;
assert.equal(ir.length, 1);
assert.equal(ir[0].job, "needs reed; the garden has none");
assert.equal(ir[0].who, "Pansy is making it");
console.log("work check: a blocked invention is on the board in words");

// SPEC-v5.3 §2.3, §8 (helper A): a site by kind and stage; the board's projects by state, orphans first
import { projectRows, siteSprite, SITES, STAGES } from "./src/sites.ts";
assert.equal(siteSprite({ kind: "shelter", stage: "done" }), "fix.built.hutch");
assert.equal(siteSprite({ kind: "shelter", stage: "framed" }), "fix.site");
assert.equal(siteSprite({ kind: null, stage: "bare" }), STAGES.bare, "a free plot is marked");
for (const k of Object.keys(SITES)) for (const st of Object.keys(STAGES)) assert.ok(siteSprite({ kind: k, stage: st }), `${k} ${st}`);
assert.deepEqual(projectRows([{ id: "p1", kind: "shelter", state: "under way", words: "a", owners: [] }, { id: "p2", kind: "shelter", state: "orphaned", words: "Spoon's shelter stands half built", owners: [] }]),
  [{ state: "orphaned", words: ["Spoon's shelter stands half built"] }, { state: "under way", words: ["a"] }]);
console.log("check-work: sites and project rows");
