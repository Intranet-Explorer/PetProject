// SPEC-v4.0 §5, §11: a conversation shown in the room, one line at a time with a short pause between: each line is up
// for as long as it takes to read (2.6 to 5.2 seconds), then a beat of nothing, then the next, over its speaker's head.
import type { Talk } from "../types";

export const PAUSE = 700;
/** How long a line stays up, in ms. */
export const lineMs = (text: string) => Math.min(5200, Math.max(2600, 1800 + 55 * text.length));
/** Which line is up `ms` after the conversation began, and for how much longer; null between lines and after the last. */
export function lineAt(lines: Talk["lines"], ms: number): { i: number; left: number } | null {
  let t = 0;
  for (const [i, l] of lines.entries()) {
    const d = lineMs(l.text);
    if (ms < t) return null;
    if (ms < t + d) return { i, left: t + d - ms };
    t += d + PAUSE;
  }
  return null;
}
/** The whole of it, in ms. */
export const talkMs = (lines: Talk["lines"]) => lines.reduce((n, l) => n + lineMs(l.text) + PAUSE, 0);
/** SPEC-v5.3 §8: where each round after the first begins, as indexes into its lines (none for a talk of one round). */
export function roundStarts(t: Pick<Talk, "rounds">): number[] {
  const out: number[] = [];
  let n = 0;
  for (const r of (t.rounds ?? []).slice(0, -1)) out.push((n += r.length));
  return out;
}
