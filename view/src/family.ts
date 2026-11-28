// What is left of the drawer's Family tab (SPEC-v3 §10.4, v3.1): a life record, for the Lab's mind of the dead and its
// "Lives that are over"; and the Songbook and the Walls, which the Lab shows under "The house" (SPEC-v4.0.5 §7.10:
// the tab itself is gone; the Family page is pages/family.ts).
import { dayOf, el, face, fold, link, plural, radial, stageName, when, whole } from "./dom";
import type { Ctx, Kid } from "./dom";
import { svg } from "./icons";
import type { Genome } from "./pet";
import { thingSprite } from "./sprite";
import { thingPicture } from "./things";
import type { Part, Recipe } from "./things";
import { fam } from "./types";
import type { Note, V31 } from "./types";

const bodyOf = (g: Genome, stage: string, caption: string) => el("figure", "", face({ genome: g, stage }, 48), el("figcaption", "hint", caption));

/** A whole life (§9.3), as the engine put it together when the pet died. */
export function record(c: Ctx, r: Record<string, any>): Kid[] {
  const name = (id: string) => c.snap.pets.find((p) => p.id === id)?.label ?? "someone gone";
  const stages = Object.entries((r.stages ?? {}) as Record<string, number | null>).filter(([, d]) => d != null);
  const things = (r.things ?? []) as { name: string; recipe: Recipe; uses: number; gone: string | null }[];
  const text = (title: string, items: { text: string }[] | undefined) => (items?.length ? el("section", "", el("h3", "", title), ...items.map((m) => el("blockquote", "", m.text))) : null);
  return [
    el("section", "", el("h3", "", "My life"), el("blockquote", "thought", r.my_life),
      r.my_life_by === "the engine" ? el("p", "hint", "It died before it wrote its own; this is the engine's plain account.") : null),
    el("p", "", `${r.name} lived ${r.days} of a possible ${r.span} days, as far as ${stageName(r.reached)}, and died of ${r.cause}. ` +
      `It made ${plural(r.made, "thing")}, ${r.useful} of them useful, and laid ${plural(r.eggs, "egg")}.`),
    el("p", "hint", [r.parent ? `Child of ${name(r.parent)}.` : "The first of its family.", r.children?.length ? `Parent of ${r.children.map(name).join(", ")}.` : ""].join(" ")),
    el("div", "row", ...Object.entries((r.bodies ?? {}) as Record<string, Genome>).map(([s, g]) =>
      bodyOf(g, s, `${stageName(s)}${stages.find(([k]) => k === s) ? `, day ${stages.find(([k]) => k === s)![1]}` : ""}`))),
    radial(r.temper ?? {}, 130),
    r.portraits?.length ? el("section", "", el("h3", "", "How it drew itself"),
      el("div", "row", ...(r.portraits as { day: number; parts: Part[] }[]).map((p) => el("figure", "", thingPicture(p), el("figcaption", "hint", `day ${p.day}`))))) : null,
    text(`What its ${r.told?.[0]?.who ?? "parent"} told it`, r.told),
    text("Its message to its children, as it changed", r.messages),
    r.last_words ? el("section", "", el("h3", "", "Last words"), el("blockquote", "", r.last_words)) : null,
    things.length ? el("section", "", el("h3", "", "What it used most"), el("div", "row", ...things.map((t) =>
      el("figure", t.gone ? "gone" : "", thingSprite(t.recipe, 3), el("figcaption", "hint", `“${t.name}” · ${plural(t.uses, "use")}`))))) : null,
    el("p", "hint", [r.heirlooms_given?.length ? `Left behind: ${r.heirlooms_given.join(", ")}.` : "", r.heirlooms_received?.length ? `Was left: ${r.heirlooms_received.join(", ")}.` : "",
      r.rooms?.length ? `Knew ${r.rooms.join(", ")}.` : "", Object.keys(r.creatures ?? {}).length ? `Met ${Object.entries(r.creatures).map(([k, n]) => `the ${k} (${n})`).join(", ")}.` : ""].join(" ")),
    r.habits?.length ? el("section", "", el("h3", "", "Habits"), el("ul", "plain", ...(r.habits as string[]).map((h) => el("li", "", h)))) : null,   // SPEC-v3.3 §1.3
    r.projects?.length ? el("section", "", el("h3", "", "Projects"), ...(r.projects as { text: string; how: string }[]).map((p) => el("p", "", `“${whole(p.text)}” `, el("span", "hint", p.how)))) : null,
    r.beliefs?.length ? fold(`beliefs-${r.id}`, `What it believed at the end (${r.beliefs.length})`,
      el("ul", "beliefs", ...(r.beliefs as { statement: string; source: string }[]).map((b) => el("li", "", el("div", "", b.statement), el("span", "tag", b.source))))) : null,
    r.diary?.length ? fold(`dreams-${r.id}`, `Its dreams (${r.diary.length})`, ...(r.diary as string[]).map((d) => el("p", "night", d))) : null,
  ];
}

/** A tune as dots on five lines' worth of height: higher is higher, a long note is wider. A note that differs
 *  from the version it came from (`was`) is in the accent colour, so a slip of the ear can be seen. */
function staff(notes: Note[], was?: Note[]) {
  const [DX, H] = [9, 30], y = (pitch: string) => {
    const [a, b] = pitch.split(" "), i = ["do", "re", "mi", "so", "la"].indexOf(b ?? a) + (b ? (a === "low" ? -5 : 5) : 0);
    return H - 6 - (i + 5) * 1.35;
  };
  let x = 4;
  const out = svg("svg", { class: "staff", width: notes.reduce((w, n) => w + (n[1] ? DX * 1.7 : DX), 8), height: H, role: "img", "aria-label": notes.map(([p, l]) => `${p}${l ? ", long" : ""}`).join("; ") });
  notes.forEach(([pitch, long], i) => {
    const w = long ? DX * 1.7 : DX, changed = !!was && (was[i]?.[0] !== pitch || was[i]?.[1] !== long);
    out.append(svg("rect", { x, y: y(pitch) - 2.5, width: w - 3, height: 5, rx: 2.5, class: changed ? "changed" : "" }));
    x += w;
  });
  return out;
}

/** The Songbook (SPEC-v3.1 §3.4): every song, and under each every version of it, set in under the one it came from. */
export function songbook(c: Ctx, songs: NonNullable<V31["songs"]>): Kid[] {
  const HOW: Record<string, string> = { "made up": "made up by", "by ear": "picked up by ear by", "the music box": "played by", "the bird": "sung by" };
  const version = (s: (typeof songs)[number], from?: (typeof songs)[number]): HTMLElement => {
    const play = link("▶", () => c.hear(s.notes, s.by), "play");
    play.title = `Hear it as ${s.by_name} sings it`;
    play.setAttribute("aria-label", `Hear “${s.name}” as ${s.by_name} sings it`);
    const crossed = !!from?.family && !!s.family && from.family !== s.family;   // the music box and the birds are nobody's family
    const later = songs.filter((x) => x.parent === s.id);
    return el("li", "", el("div", `version ${s.family ? fam(s.family) : ""}`, play, el("div", "",
        el("div", "", from ? null : el("b", "", `${s.name} `), `${HOW[s.how ?? ""] ?? s.how ?? "from"} ${s.by_name}`, crossed ? el("span", "badge gold", "crossed over") : null),
        staff(s.notes, from?.notes),
        el("div", "hint", `${s.sounds} · ${when(c.snap, s.tick)} · ${s.known_by.length ? `${s.known_by.join(", ")} ${s.known_by.length > 1 ? "sing" : "sings"} it now` : "nobody sings it now"}`))),
      later.length ? el("ul", "", ...later.map((x) => version(x, s))) : null);
  };
  const first = songs.filter((s) => !s.parent || !songs.some((x) => x.id === s.parent));
  return [
    el("h3", "", `Songbook (${first.length})`),
    first.length ? el("p", "hint", "Every tune, and under it each way it has been sung since. A song taught is kept note for note; one picked up by ear may slip a note, shown in colour. ▶ plays a version in the voice of whoever made it.") : null,
    first.length ? el("ul", "songtree", ...first.map((s) => version(s))) : el("p", "empty", c.snap.arrived?.songs == null ? "Nobody in the house has heard a tune yet." : "Nobody has made up a song yet."),
  ];
}

/** Walls (SPEC-v3.1 §2.4): every inscription ever written, by room, whose hand, and what became of it. */
export function walls(c: Ctx, all: NonNullable<V31["walls"]>): Kid[] {
  const rooms = [...new Set(all.map((w) => w.room))];
  const one = (w: (typeof all)[number]) => el("li", w.fate === "there" ? "" : "gone", el("blockquote", w.medium === "scratch" ? "scratch" : "chalk", w.text),
    el("p", "hint", `${w.medium === "scratch" ? "scratched" : "chalked"} on the ${w.place} by ${w.by_name}, ${when(c.snap, w.tick)} · `,
      w.fate === "there" ? el("span", "correct", "still there") : el("span", "wrong", `${w.fate}${w.gone_by && w.fate !== "faded away" ? ` by ${w.gone_by}${w.fate === "worn away" ? ", writing over it" : ""}` : ""}${w.gone != null ? `, day ${dayOf(c.snap, w.gone)}` : ""}`)));
  return [
    el("h3", "", `Walls (${all.length})`),
    all.length ? null : el("p", "empty", c.snap.arrived?.writing == null ? "Nobody in the house can write yet." : "Nothing has been written on a wall yet."),
    ...rooms.flatMap((id) => {
      const here = all.filter((w) => w.room === id).reverse(), there = here.filter((w) => w.fate === "there"), gone = here.filter((w) => w.fate !== "there");
      return [el("h4", "", `${here[0].room_name[0].toUpperCase()}${here[0].room_name.slice(1)} `, link("look", () => c.jump({ room: id }))),
        el("ul", "sayings walls", ...there.map(one), ...gone.slice(0, 3).map(one)),
        gone.length > 3 ? fold(`walls-${id}`, `${gone.length - 3} more that are gone`, el("ul", "sayings walls", ...gone.slice(3).map(one))) : null];
    }),
  ];
}
