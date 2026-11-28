// Self-check for the Family page's tree (SPEC-v4.0.5 §3.4): node check-family.ts
import assert from "node:assert/strict";
import { foundIn, place, stranger } from "./src/pages/tree.ts";
import type { TreePet } from "./src/pages/tree.ts";

// the first family: Wen, her laid child Fiji, and Paquita, a founder egg that turned up in Wen's family;
// the second: Pansy, a true stranger, and her child
const pets: TreePet[] = [
  { id: "p1", parent: null, family: 1, gen: 1, born_day: 1 },
  { id: "p2", parent: "p1", family: 1, gen: 2, born_day: 5 },
  { id: "p3", parent: "p1", family: 1, gen: 2, born_day: 9, founder: true },
  { id: "p4", parent: null, family: 2, gen: 1, born_day: 7, founder: true },
  { id: "p5", parent: "p4", family: 2, gen: 2, born_day: 12 },
  // the third: Sasha, its first, and Sipho, a founder egg that came while Sasha was little: Sasha's sibling, no parent
  { id: "p6", parent: null, family: 3, gen: 1, born_day: 20 },
  { id: "p7", parent: null, family: 3, gen: 1, born_day: 22, founder: true, kin: "p6" },
  { id: "p8", parent: null, family: 3, gen: 1, born_day: 25 },
];
const one = place(pets, 1), two = place(pets, 2);
assert.equal(one.slots, 2);                                       // the founder child takes a slot beside its sibling, not a tree of its own
assert.deepEqual([one.x.get("p2"), one.x.get("p3")], [0, 1]);
assert.equal(one.x.get("p1"), 0.5);                               // its parent over the middle of both
assert.deepEqual(one.kids("p1").map((p) => p.id), ["p2", "p3"]);
assert.equal(two.slots, 1);
assert.deepEqual([two.x.get("p4"), two.x.get("p5")], [0, 0]);      // the stranger is the root of its own family
const three = place(pets, 3);
assert.deepEqual(["p6", "p7", "p8"].map((id) => three.x.get(id)), [0, 1, 2]);   // the sibling founder beside its kin, before a later root
assert.equal(foundIn(pets[2], "Wen", undefined), "came as an egg nobody laid, of Wen's family");
assert.equal(foundIn(pets[6], undefined, "Sasha"), "came as an egg nobody laid, to Sasha's family");
assert.equal(foundIn(pets[3], undefined, undefined), null);       // a stranger has no such title
assert.equal(foundIn(pets[1], "Wen", undefined), null);           // nor a laid child
assert.deepEqual(pets.filter((p) => p.founder && stranger(p)).map((p) => p.id), ["p4"]);   // between the families: only the true stranger
console.log("family check ok");
