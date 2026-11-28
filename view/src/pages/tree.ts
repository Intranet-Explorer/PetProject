// The Family page's tree, placed (SPEC-v3.5.3 §3): no DOM here, so view/check-family.ts runs it under node.
export type TreePet = { id: string; parent: string | null; family: number; gen: number; born_day: number; founder?: boolean; kin?: string | null };

/** One family's column: a slot for every pet, leaves side by side and each parent over the middle of its children;
 *  and how many slots wide it is. A founder egg given to a family has a parent (SPEC-v4.0.5 §3.1), so it is placed
 *  under that parent like any child; only a pet with no parent in the family starts a tree of its own. */
export function place(all: TreePet[], fam: number) {
  const pets = all.filter((p) => p.family === fam), x = new Map<string, number>();
  const kids = (id: string) => pets.filter((p) => p.parent === id).sort((a, b) => a.born_day - b.born_day);
  // (a founder whose kin was a little one is its sibling: no parent when the kin is the family's first, and drawn
  // beside it, in its generation)
  const beside = (p: TreePet) => !p.parent && !!p.founder && pets.some((q) => q.id === p.kin);
  let slots = 0;
  const one = (p: TreePet) => {
    const ch = kids(p.id);
    ch.forEach(one);
    x.set(p.id, ch.length ? (x.get(ch[0].id)! + x.get(ch.at(-1)!.id)!) / 2 : slots++);
    pets.filter((q) => beside(q) && q.kin === p.id).sort((a, b) => a.born_day - b.born_day).forEach(one);
  };
  pets.filter((p) => !pets.some((q) => q.id === p.parent) && !beside(p)).sort((a, b) => a.born_day - b.born_day).forEach(one);
  return { pets, x, slots, kids };
}

/** SPEC-v4.0.5 §3.4: a founder with a parent came as an egg nobody laid, into that parent's family; one with only a
 *  kin (its sibling: the kin was a little one, the family's first), to the kin's family. */
export const foundIn = (p: TreePet, parent: string | undefined, kin: string | undefined) =>
  !p.founder ? null : p.parent && parent ? `came as an egg nobody laid, of ${parent}'s family` : !p.parent && p.kin && kin ? `came as an egg nobody laid, to ${kin}'s family` : null;
/** "Between the families" names as strangers only those who came from nowhere: neither a parent nor a kin. */
export const stranger = (p: TreePet) => !p.parent && !p.kin;
/** SPEC-v4.2 §11.4: a death not of age gets a small mark on the tree, its title the cause in words; null for the living,
 *  a death of age, and a stone the engine says nothing of (v4.2 off). */
export const deathMark = (p: { alive?: boolean; of_age?: boolean; cause_words?: string }) => (p.alive === false && p.of_age === false && p.cause_words ? p.cause_words : null);
