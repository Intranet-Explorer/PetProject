// SPEC-v4.0 §11: "While you were away". On opening the page, a card with the three or four biggest things that happened
// since the visitor's last visit (a conversation that mattered, a fight, a bond, a death, a first), each with portraits.
// The last visit is kept in this browser (the house's tick, every few seconds while the page is open); the events come
// from /api/away, or the snapshot's own moments when the engine has no such address. Only while the engine sends v4.
import { el, face } from "./dom";
import { icon } from "./icons";
import { headOf, talkLines } from "./pages/story";
import { getJSON } from "./ui";
import type { Moment, PetV, Snap } from "./types";

const KEY = "pet.visit";
const recall = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
const remember = (v: string) => { try { localStorage.setItem(KEY, v); } catch { /* private window */ } };

/** How much each kind of moment is worth telling first; anything not here is not told. */
const WORTH: Record<string, number> = { killing: 100, death: 95, "driven out": 90, "came back": 85, bond: 80, hatched: 75, harm: 72, fight: 70, justice: 68, ended: 99,
  "arrival writing": 65, "arrival songs": 65, "arrival taming": 65, "arrival radio": 65, "arrival book": 65, "arrival strangers": 65, first: 60, "first design": 58, works: 55, talk: 45, gift: 30, "making up": 40 };
const HEAD: Record<string, string> = { killing: "a killing", death: "a death", "driven out": "driven out", "came back": "back home", bond: "a close bond", hatched: "a birth", harm: "a fight",
  fight: "a fight", justice: "justice", first: "a first", talk: "a conversation", gift: "a gift", "making up": "making up", ended: "the family's end" };
export function worth(m: Moment) {
  if (m.kind === "first" && m.matters === false) return 0;
  if (m.kind === "fight" && !m.hurt) return 35;
  if (m.kind === "talk") return m.came_of ? (m.came_of.some((c) => c !== "nothing" && c !== "snub") ? 50 : 10) : (m.lines?.length ?? 0) >= 4 ? 50 : 20;   // one that mattered: something came of it (or, while moments do not say, a longer one)
  return WORTH[m.kind] ?? (m.kind.startsWith("arrival") ? 65 : 0);
}
/** The three or four biggest, told in the order they happened. */
export function biggest(ms: Moment[], n = 4) {
  return [...ms].filter((m) => worth(m) > 0).sort((a, b) => worth(b) - worth(a) || b.n - a.n).slice(0, n).sort((a, b) => a.tick - b.tick);
}

let since: { house: string; tick: number } | null | undefined, savedAt = 0;
/** Every snapshot: the first time, whether to tell what happened since the last visit; then the visit is kept. */
export function away(s: Snap, show: (since: number, ms: Moment[]) => void) {
  const house = `${s.start}|${s.lineage.id}`;
  if (since === undefined) {
    const [h, t] = (recall() ?? "").split("#");
    since = h === house && Number(t) < s.tick ? { house, tick: Number(t) } : null;
    const hour = s.day_seconds / s.tick_seconds / 24;
    if (since && s.v4 && Object.values(s.v4).some(Boolean) && s.tick - since.tick > hour) void tell(s, since.tick, show);
  }
  if (Date.now() - savedAt > 10_000 && document.visibilityState === "visible") { savedAt = Date.now(); remember(`${house}#${s.tick}`); }
}
export async function tell(s: Snap, from: number, show: (since: number, ms: Moment[]) => void) {
  const got = await getJSON<{ moments: Moment[] }>(`/api/away?since=${from}`);
  const all = got?.moments ?? [], ns = new Set(all.map((m) => m.n));   // (and the snapshot's own, which can be newer)
  const ms = biggest([...all, ...s.moments.filter((m) => !ns.has(m.n))].filter((m) => m.tick > from));
  if (ms.length) show(from, ms);
}

/** The card itself, over the page; `name` gives a hob's name as the page shows it. */
export function awayCard(s: Snap, from: number, ms: Moment[], name: (p: PetV) => string, go: (m: Moment) => void) {
  const pet = (id: string | null | undefined) => s.pets.find((p) => p.id === id);
  const hours = Math.round(((s.tick - from) * s.tick_seconds) / (s.day_seconds / 24));
  const box = el("div", "away paper", el("h2", "title", "While you were away"),
    el("p", "hint", hours >= 48 ? `${Math.round(hours / 24)} world days have gone by.` : `${hours} world hour${hours === 1 ? " has" : "s have"} gone by.`),
    el("ol", "", ...ms.map((m) => {
      const who = [...new Set([m.pet, ...(m.pets ?? [])])].map(pet).filter((p): p is PetV => !!p).slice(0, 2);
      const li = el("li", `aw k-${m.kind.replace(/\W+/g, "-")}`, el("span", "pics", ...who.map((p) => face(p, 48))),
        el("span", "txt", el("b", "", icon(m.kind, 14), ` ${HEAD[m.kind] ?? m.kind}`, el("span", "hint", ` - day ${m.day}`)), el("span", "", headOf(m)),
          m.lines ? talkLines({ lines: m.lines.slice(0, 2) }) : null));
      li.title = who.map(name).join(" and ");
      li.onclick = () => { box.remove(); go(m); };
      return li;
    })),
    el("button", "", "Back to the house"));
  box.querySelector("button")!.onclick = () => box.remove();
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-label", "While you were away");
  document.getElementById("away")?.remove();
  box.id = "away";
  document.body.append(box);
  return box;
}
