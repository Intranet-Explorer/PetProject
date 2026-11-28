// SPEC-v4.0 §11: a hob's character as the page shows it: its ten axes as short sliders between their pole words, its
// quirks and values, its mood and why, its hurt and sickness, its day's aims, its two best friends and worst enemy, and
// how it feels about you. Each part only when the engine sends it (a v4 switch off: none of it).
import { el } from "./dom";
import type { Kid } from "./dom";
import type { PetV } from "./types";

/** The axes, the + pole first (engine/character.py AXES). */
export const POLES: [string, string, string][] = [["brave", "brave", "timid"], ["tidy", "tidy", "messy"], ["generous", "generous", "greedy"], ["curious", "curious", "cautious"],
  ["social", "social", "solitary"], ["honest", "honest", "sly"], ["patient", "patient", "hasty"], ["playful", "playful", "serious"], ["ambitious", "ambitious", "content"], ["kind", "kind", "prickly"]];

/** A liking (-10 to 10) as how the one liked is held: "loved", "disliked". */
export function feels(v: number | null | undefined) {
  if (v == null) return "unknown";
  return v >= 7 ? "loved" : v >= 4 ? "much liked" : v >= 1 ? "liked" : v > -1 ? "neither liked nor disliked" : v > -4 ? "disliked" : v > -7 ? "much disliked" : "hated";
}
/** How it feels about `whom`, as a sentence's end: "loves you", "likes you a lot". */
export function feelsAbout(v: number, whom: string) {
  return v >= 7 ? `loves ${whom}` : v >= 4 ? `likes ${whom} a lot` : v >= 1 ? `likes ${whom}` : v > -1 ? `is neither warm nor cold to ${whom}` : v > -4 ? `dislikes ${whom}` : v > -7 ? `dislikes ${whom} a lot` : `hates ${whom}`;
}
/** Its hurt and its sickness in words, or "". */
export function ailing(p: Pick<PetV, "hurt" | "sick">) {
  return [p.hurt ? (p.hurt.level ? `${p.hurt.level}${p.hurt.lasting === "limp" ? ", with a limp that will stay" : ""}` : p.hurt.lasting === "limp" ? "walks with a limp" : "") : "", p.sick ? `sick (${p.sick.level}${p.sick.from ? `, from ${p.sick.from}` : ""})` : ""].filter(Boolean).join("; ");
}
/** Its mood and why, in words, or "". */
export const moodOf = (p: Pick<PetV, "mood4" | "mood4_why">) => (p.mood4 ? `${p.mood4}${p.mood4_why ? `: ${p.mood4_why}` : ""}` : "");

/** One axis: the + pole word, a short track with a marker where it stands, the - pole word. */
function slider(axis: string, plus: string, minus: string, v: number) {
  const at = Math.round(((1 - Math.max(-1, Math.min(1, v))) / 2) * 100), m = el("i", "mark");
  m.style.left = `${at}%`;
  const row = el("div", `axis${v >= 0.5 ? " plus" : v <= -0.5 ? " minus" : ""}`, el("span", "pole p", plus), el("span", "track", m), el("span", "pole m", minus));
  row.title = `${axis}: ${v >= 0.5 ? `very ${plus}` : v >= 0.15 ? `rather ${plus}` : v <= -0.5 ? `very ${minus}` : v <= -0.15 ? `rather ${minus}` : `between ${plus} and ${minus}`}`;
  return row;
}

/** The whole of it for a pet's page; `link` makes a hob's name a link to its page. Null when the engine sends none of it. */
export function character(p: PetV, link: (id: string) => Kid): HTMLElement | null {
  const T = p.traits, top = p.top, sick = ailing(p), friends = (top?.friends ?? []).filter((id) => (p.likes?.[id] ?? 1) >= 1);   // (the engine's two best may be only the least disliked)
  if (!T && !top && !p.mood4 && !sick && !p.aims?.length) return null;
  const row = (k: string, ...v: Kid[]) => [el("dt", "", k), el("dd", "", ...v)];
  const liking = (id: string) => (p.likes?.[id] != null ? el("span", "hint", ` (${feels(p.likes[id])})`) : null);
  return el("div", "character",
    el("dl", "", ...([
      p.mood4 ? row("Mood", el("b", `mood m-${p.mood4}`, p.mood4), p.mood4_why ? ` - ${p.mood4_why}` : "") : null,
      sick ? row("Health", sick) : null,
      p.outcast ? row("Lives", `outcast in the meadow since it was driven out: ${p.outcast.why}`) : null,
      p.shunned != null ? row("Shunned", "nobody talks to it, and it eats alone") : null,
      p.quirks?.length ? row("Quirks", ...p.quirks.map((q) => el("span", "chip", q))) : null,
      p.values?.length ? row("Cares for", ...p.values.map((q) => el("span", "chip", q))) : null,
      p.ambition ? row("Ambition", p.ambition) : null,
      friends.length ? row("Friends", ...friends.flatMap((id, i) => [i ? ", " : "", link(id), liking(id)])) : null,
      top?.enemy ? row("Enemy", link(top.enemy), liking(top.enemy)) : null,
      top && !friends.length ? row("Friends", "none yet") : null,
      top ? row("You", top.visitor == null ? "it has not made up its mind about you" : `it ${feelsAbout(top.visitor, "you")}`) : null,
    ].filter(Boolean).flat() as Kid[])),
    T ? el("div", "axes", ...POLES.filter(([a]) => T[a] != null).map(([a, plus, minus]) => slider(a, plus, minus, T[a]))) : null,
    p.aims?.length ? el("div", "aims", el("h3", "", "Today it means to"), el("ul", "bul", ...p.aims.map((a) => el("li", a.done ? "done" : "", a.text, a.why ? el("span", "hint", `, because ${a.why}`) : null)))) : null);
}
