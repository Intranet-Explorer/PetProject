// SPEC-v4.2 §11.1, §11.2: what the page shows of a hob's inner life, worked out with no DOM or Pixi so that
// view/check-spirit.ts runs it under node: the thought of its last plan or reaction (a cloud bubble, apart from its
// speech), a talk's wants and holds (clouds over both, when the talk is clicked), and the card's lines.
import type { PetV, Talk } from "./types";

const andList = (xs: string[]) => (xs.length > 1 ? `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}` : xs.join(""));
/** SPEC-v5.1 §8 a hob's knowing on its card (B's knowledge.card, the pet page's `knows51`): its tier, each recipe it
 *  knows and how it came by it, what it knows of; and its reading list (the page's `words.reading`, newest first). */
type Known = { key: string; words: string; from: string; how: string };
export type Knows51 = { tier: number; tier_words: string; recipes: Known[]; of: Known[] };
export type Read51 = { title: string; question?: string; source?: string; chain?: number; day?: number | null };
export function knowsRows(k: Knows51 | null | undefined, reading?: Read51[] | null): [string, string][] {
  const cut = (w: string) => w.replace(/^how to make /, "");
  const rows: [string, string][] = k ? [["Knows", k.tier_words], ["Can make", andList(k.recipes.map((r) => `${cut(r.words)} (${r.how})`))],
    ["Knows of", andList(k.of.map((r) => cut(r.words)))]] : [];
  rows.push(["Has read", (reading ?? []).slice(0, 8).map((r) => r.title).filter(Boolean).join("; ")]);
  return rows.filter(([, v]) => v);
}

/** §11.1: the thought of its last plan or reaction, for a cloud: a new thought has a new key; null when there is none
 *  to show (v4.2 off, asleep, an egg or the dead, a thought of another kind, or no words). */
export function thoughtOf(p: Pick<PetV, "stage" | "asleep" | "plan">, on: boolean): { key: string; text: string } | null {
  const pl = p.plan, text = pl?.thought?.trim();
  if (!on || !pl || !text || p.asleep || p.stage === "egg" || p.stage === "dead" || (pl.why !== "plan" && pl.why !== "react")) return null;
  return { key: `${pl.why}|${text}`, text };
}

/** §11.1, §7.2: a talk's minds as each speaker's cloud, by hob id (lab4.talk_view sends them so): what it wanted from
 *  the talk and what it kept back. A side with neither has no cloud. */
export function mindsOf(t: Pick<Talk, "a" | "b" | "minds">): Record<string, string> {
  const out: Record<string, string> = {};
  for (const id of [t.a, t.b]) {
    const m = t.minds?.[id], bits = [m?.wants ? `wants: ${m.wants}` : "", m?.holds ? `keeps back: ${m.holds}` : ""].filter(Boolean);
    if (bits.length) out[id] = bits.join(" / ");
  }
  return out;
}

/** The talk a click on this hob opens: its latest in this room that left minds, or null. */
export function talkOf(talks: Talk[] | undefined, room: string, pet: string): Talk | null {
  return [...(talks ?? [])].reverse().find((t) => t.room === room && (t.a === pet || t.b === pet) && Object.keys(mindsOf(t)).length > 0) ?? null;
}

/** The card's v4.2 part (pages.pet_page's `spirit`, with lab4.card's lines). */
export type SpiritCard = { self?: string[]; taught?: string; theory?: string; leave?: { what?: string; to?: string } | null;
  drive?: string; flaw?: string; voice?: string; secret?: { found: boolean; text?: string }; threads?: string[] };   // (SPEC-v5.3 §8: its open threads, in words)

/** §11.2: the card's rows, [what, words], each only when there is something to say. A secret is "keeps something to
 *  itself" until it is found out; its own words only then. */
export function cardRows(c: SpiritCard | null | undefined): [string, string][] {
  if (!c) return [];
  const s = c.secret, rows: [string, string][] = [
    ["Drive", c.drive ?? ""], ["Flaw", c.flaw ?? ""], ["Voice", c.voice ?? ""], ["Of you", c.theory ?? ""],
    ["Taught", (c.taught ?? "").replace(/^taught: /, "")],
    ["Secret", !s ? "" : s.found ? (s.text ? `found out: ${s.text}` : "found out") : "keeps something to itself"],
    ["Would leave", c.leave?.what ? `${c.leave.what}${c.leave.to ? ` to ${c.leave.to}` : ""}` : ""],
    ["Left open", (c.threads ?? []).join("; ")],
  ];
  return rows.filter(([, v]) => v);
}
