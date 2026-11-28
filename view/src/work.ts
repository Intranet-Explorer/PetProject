// SPEC-v5.0 §5 (helper C): the work board and piles (of bits, and of a hob's scrap), worked out with no DOM or Pixi so that
// view/check-work.ts runs them under node. The engine sends the words (pages.board_view, pages.item_view); what is
// worked out here is only what changes with the clock (how long a deficit has been open) and how many sprites a pile draws.
import type { Board5 } from "./types";

/** SPEC-v5.1 §8 a board row's job: the job's words, else what its make step lacks ("needs: glass, which nobody has"). */
export const jobWords = (job: string | undefined, needs: string | undefined) => job || (needs ? `needs: ${needs}` : "");

/** §5: how many sprites a stack of `n` bits draws, of the same bit: 1, 2–3, 4–7, 8 and more are 1, 2, 3 and 4. */
export const pileOf = (n: number) => (n >= 8 ? 4 : n >= 4 ? 3 : n >= 2 ? 2 : n >= 1 ? 1 : 0);

const NUM = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
const num = (n: number) => NUM[n] ?? String(n);

/** How long something on the board has been open, in words: "just now", "since this morning", "since yesterday",
 *  "for three days". `now`: the snapshot's tick and hour; `perHour`: ticks in a world hour (the day began `hour` hours ago). */
export function ageWords(now: { tick: number; hour: number }, since: number, perHour: number): string {
  if (now.tick - since < perHour) return "just now";
  const dayStart = now.tick - now.hour * perHour;
  if (since >= dayStart) {
    const h = (since - dayStart) / perHour;
    return h < 5 ? "since the night" : h < 12 ? "since this morning" : h < 17 ? "since this afternoon" : "since this evening";
  }
  const days = Math.ceil((dayStart - since) / (24 * perHour));   // (whole days before today it began)
  return days <= 1 ? "since yesterday" : `for ${num(days)} days`;
}

/** A line of the board: what is wrong, how long, and who is seeing to it (with what, in the job's words). */
export type WorkRow = { kind: string; text: string; age: string; who: string | null; job: string; urgent: boolean };
/** §5 the board's rows, most urgent first as the engine ranks them: each open deficit with its age and its job's taker
 *  ("Pansy is seeing to it"), then what closed today, newest first ("the music room is lit tonight: Odo"). */
export function workRows(b: Board5 | null | undefined, now: { tick: number; hour: number }, perHour: number, name: (id: string) => string | null): { open: WorkRow[]; closed: WorkRow[] } {
  if (!b) return { open: [], closed: [] };
  const open: WorkRow[] = b.deficits.map((d) => {
    const j = b.jobs.find((x) => x.deficit === d.id), who = j?.taker ? name(j.taker) : null;
    return { kind: d.kind, text: d.words, age: ageWords(now, d.since, perHour), who: who ? `${who} is seeing to it` : null, job: jobWords(j?.words, d.needs), urgent: d.urgency >= 3 };   // (SPEC-v5.1 §8: or what its make step lacks)
  });
  const ids = new Set(b.deficits.map((d) => d.id));
  for (const j of b.jobs.filter((x) => x.invent && !ids.has(x.deficit))) {   // SPEC-v5.1 §4.4: an invention of its own, and what it waits on ("needs reed; the garden has none")
    const who = j.taker ? name(j.taker) : null;
    open.push({ kind: "invention", text: j.words, age: "", who: who ? `${who} is making it` : null, job: j.blocked ?? "", urgent: false });
  }
  const closed = [...b.closed].sort((x, y) => y.tick - x.tick).map((c) => {
    const by = c.by ? name(c.by) : null;
    return { kind: c.kind, text: c.words, age: ageWords(now, c.tick, perHour), who: by ? `seen to by ${by}` : null, job: "", urgent: false };
  });
  return { open, closed };
}
