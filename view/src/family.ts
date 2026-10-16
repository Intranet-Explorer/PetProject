// The Family tab (SPEC-v3 §10.4): the tree, a life record for whoever is clicked, the family's sayings and heirlooms.
// SPEC-v3.1 adds what a family leaves behind that is not a thing: its animals, its walls and its songs, and a
// second family beside the first, with a line wherever something crossed from one to the other.
import { dayOf, el, face, fold, link, plural, radial, scroller, stageName, stageWord, when, whole } from "./dom";
import type { Ctx, Kid } from "./dom";
import { icon, svg } from "./icons";
import type { Genome } from "./pet";
import { aThing, thingSprite } from "./sprite";
import { thingPicture } from "./things";
import type { Part, Recipe } from "./things";
import { fam } from "./types";
import type { Note, PetV, V31 } from "./types";

const kept = (() => { try { return JSON.parse(localStorage.getItem("family") ?? "{}"); } catch { return {}; } })();
const keep = () => { try { localStorage.setItem("family", JSON.stringify({ chosen, lineage })); } catch { /* not remembered */ } };
let chosen: string | null = kept.chosen ?? null;    // whose life is open under the tree
let lineage: number | null = kept.lineage ?? null;   // which family's tree is shown: the present one unless another was picked
export function showRecord(id: string | null) {
  chosen = id;
  lineage = null;
  keep();
}

const TRUTH: Record<string, [string, string, string]> = {
  true: ["✓ true of this house", "correct", "The engine checked this saying against how the house really works, and it holds."],
  false: ["✗ not so", "wrong", "The engine checked this saying against how the house really works, and it does not hold. The family believes it all the same."] };
const UNCHECKED = "The engine has no test for a saying like this one.";
const [CW, CH] = [96, 124];

/** Whether a saying holds, as the engine tested it; the title says what the mark means. */
function mark(truth: string | null) {
  const [text, cls, title] = TRUTH[truth ?? ""] ?? ["nothing the house can check", "", UNCHECKED], e = el("span", cls, text);
  e.title = title;
  return e;
}

/** Something that went from one family to the other: who had it, who has it now, and what it was. */
type Crossing = { from: string; to: string; what: string };
const NAMES: Record<number, string> = { 1: "First family", 2: "Second family" };

/** The tree, or two side by side once a second family lives here (SPEC-v3.1 §7.4), each in its colour, with a line
 *  wherever something crossed between them. It scrolls in its own box, and is drawn a little smaller to fit. */
function tree(c: Ctx, pets: PetV[], crossings: Crossing[], sayings: number, redraw: () => void) {
  const kids = (id: string) => pets.filter((p) => p.parent === id).sort((a, b) => a.laid - b.laid);
  const of = (p: PetV) => p.family ?? 1;
  const roots = pets.filter((p) => !pets.some((q) => q.id === p.parent)).sort((a, b) => of(a) - of(b) || a.laid - b.laid);
  const X = new Map<string, number>(), two = new Set(pets.map(of)).size > 1, span = new Map<number, number[]>(), TOP = two ? 44 : 0;
  let next = 0;
  const place = (p: PetV) => {   // leaves side by side, each parent over the middle of its children
    const ch = kids(p.id);
    ch.forEach(place);
    X.set(p.id, ch.length ? (X.get(ch[0].id)! + X.get(ch.at(-1)!.id)!) / 2 : next++);
  };
  for (const r of roots) {
    if (span.size && !span.has(of(r))) next += 0.4;   // a gap between the families
    const from = next;
    place(r);
    span.set(of(r), [span.get(of(r))?.[0] ?? from, next]);
  }
  const gens = [...new Set(pets.map((p) => p.gen))].sort((a, b) => a - b);
  const at = (p: PetV) => [X.get(p.id)! * CW, gens.indexOf(p.gen) * CH];
  const [W, H] = [next * CW, gens.length * CH];
  const lines = svg("svg", { class: "lines", width: W, height: H }), over = svg("svg", { class: "lines over", width: W, height: H });
  const box = el("div", "tree", lines);
  box.style.width = `${W}px`;
  box.style.height = `${H}px`;
  // The tree has all the height the drawer can give it. It is drawn smaller (never so small that a name cannot be read)
  // when that lets every generation, or one more, be seen whole; past that it scrolls inside its own box, which is a
  // whole number of generations high and stops only on whole rows, so no row of faces is ever cut through. The families'
  // names stand above the box and stay put.
  const panel = document.querySelector<HTMLElement>('[data-panel="family"]'), room = (panel?.clientWidth || 440) - 36, tall = (panel?.clientHeight || innerHeight - 60) - 130;
  let rows = gens.length, zoom = Math.min(1, room / W);
  while (rows > 1 && tall / (TOP + rows * CH) < 0.8) rows--;
  zoom = Math.max(0.8, Math.min(zoom, tall / (TOP + rows * CH)));
  box.style.zoom = String(zoom);
  const head = el("div", "tree");
  head.style.cssText = `width:${W}px;height:${TOP}px;zoom:${zoom}`;
  if (two) for (const [n, [a, b]] of span) {
    const name = el("span", `treename ${fam(n)}`, NAMES[n] ?? `Family ${n}`);
    name.style.left = `${a * CW}px`;
    name.style.width = `${(b - a) * CW}px`;
    head.append(name);
  }
  for (const p of pets) {
    const [x, y] = at(p), parent = pets.find((q) => q.id === p.parent);
    if (parent) {   // (SPEC-v3.5 §2.2: the branch to one born with something new is marked)
      const [px, py] = at(parent), mid = y - 8;
      lines.append(svg("path", { class: p.mutation ? "new" : "", d: `M${px + CW / 2} ${py + CH - 12}V${mid}H${x + CW / 2}V${y + 2}` }));
    }
    const dead = p.stage === "dead", egg = p.stage === "egg";
    const life = dead ? `lived ${plural(Math.round(p.days ?? 0), "day")}` : egg ? "not hatched" : (p.days ?? 0) < 1 ? "born today" : `${plural(Math.floor(p.days ?? 0), "day")} old`;
    const node = el("button", `node ${fam(of(p))} ${dead ? "dead" : "alive"}${chosen === p.id ? " chosen" : ""}`, face(p, 48),
      el("b", "", egg ? p.name ?? "an egg" : p.label),
      dead || egg ? (p.eggs ? el("span", "", plural(p.eggs, "egg")) : null) : el("span", "", `${stageWord(p)}${p.eggs ? ` · ${plural(p.eggs, "egg")}` : ""}`), el("span", "", life)) as HTMLButtonElement;
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;
    node.title = `${p.label}, generation ${p.gen}${two ? `, of the ${(NAMES[of(p)] ?? "other family").toLowerCase()}` : ""}`;
    if (p.mutation) {
      const was = p.mutation.from === "none" || p.mutation.from === "no" ? "" : `, where its parent had ${p.mutation.from}`, star = el("span", "newpart", `✦ ${p.mutation.slot}`);
      star.title = `Born with something new: ${p.mutation.slot} ${p.mutation.to}${was}.`;
      node.title += `. ${star.title}`;
      node.classList.add("mutant");
      node.append(star);
    }
    node.onclick = () => { chosen = chosen === p.id ? null : p.id; keep(); redraw(); };
    box.append(node);
  }
  // a dashed line from who had it to who has it now, under the faces, and where it crosses the gap between the trees a mark that says what it was
  const gap = ([...span.values()].sort((a, b) => a[0] - b[0])[0]?.[1] ?? 0) * CW + 0.2 * CW, seen = new Set<string>(), marks: number[] = [];
  for (const x of crossings) {
    const [a, b] = [pets.find((p) => p.id === x.from), pets.find((p) => p.id === x.to)];
    if (!a || !b || seen.has(a.id + b.id)) continue;
    seen.add(a.id + b.id);
    const [[ax, ay], [bx, by]] = [at(a), at(b)], right = bx > ax, [x1, y1, x2, y2] = [ax + (right ? CW - 8 : 8), ay + 34, bx + (right ? 8 : CW - 8), by + 34];
    let my = x2 === x1 ? (y1 + y2) / 2 : y1 + ((gap - x1) / (x2 - x1)) * (y2 - y1);
    while (marks.some((m) => Math.abs(m - my) < 20)) my += 20;   // two that cross at the same height: one under the other
    marks.push(my);
    lines.append(svg("path", { class: "cross", d: `M${x1} ${y1}L${gap} ${my}L${x2} ${y2}` }));
    over.append(svg("g", { class: "crossmark" }, svg("circle", { cx: gap, cy: my, r: 9 }), svg("text", { x: gap, y: my + 4, "text-anchor": "middle" }, "♪"),
      svg("title", {}, crossings.filter((y) => y.from === x.from && y.to === x.to).map((y) => y.what).join("; "))));
  }
  if (two && sayings && span.size > 1) {   // sayings cross too, but the house does not say between whom: a mark between the trees' names
    const mark = el("span", "treecross", `⇄ ${plural(sayings, "saying")} crossed`);
    mark.style.left = `${gap}px`;
    mark.title = `${plural(sayings, "saying")} crossed between the families: said first in one, now said in both. They are listed under the tree.`;
    head.append(mark);
  }
  box.append(over);
  const frame = scroller("tree", "treebox", box), more = gens.length - rows, names = el("div", "treehead", head);
  frame.style.maxHeight = `${rows * CH * zoom}px`;
  frame.onscroll = () => (names.scrollLeft = frame.scrollLeft);   // the names keep over their own trees when the box is moved sideways
  return el("div", "treewrap", more > 0 ? el("p", "hint", `The tree shows ${rows} of ${gens.length} generations at a time, the latest first. Scroll up inside it for the ${more === 1 ? "one" : more} before.`) : null, two ? names : null, frame);
}

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
function songbook(c: Ctx, songs: NonNullable<V31["songs"]>): Kid[] {
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
function walls(c: Ctx, all: NonNullable<V31["walls"]>): Kid[] {
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

export function family(c: Ctx): Kid[] {
  const d = c.api.family, v = (c.api.v31 ?? {}) as V31;
  if (!d) return [el("p", "empty", "Asking the house about its family…")];
  const all = d.pets as PetV[], now = d.lineage?.id as number;
  const which = (chosen && all.find((p) => p.id === chosen)?.lineage) || lineage || now;
  const pets = all.filter((p) => p.lineage === which);
  const redraw = () => c.show("family");
  const lines = [...new Set(all.map((p) => p.lineage))].sort((a, b) => b - a);
  const pick = el("select", "") as HTMLSelectElement;
  pick.append(...lines.map((n) => new Option(n === now ? `Family ${n} (living now)` : `Family ${n}`, String(n), false, n === which)));
  pick.onchange = () => { lineage = Number(pick.value); chosen = null; keep(); redraw(); };
  const who = pets.find((p) => p.id === chosen), rec = who && d.records?.[who.id];
  const sayings = (d.sayings ?? []) as { text: string; gens: number[]; truth: string | null; forms: [string, string][]; pets: { id: string; name: string }[] }[];
  const heir = (d.heirlooms ?? []) as { name: string; room: string; recipe: Recipe; line: string[]; to: string[] }[];
  const name = (id: string) => all.find((p) => p.id === id)?.label ?? id;
  // What crossed between the families (SPEC-v3.1 §7.2): a song one family made that the other now sings (a new version
  // by ear, or the same one sung by someone of the other family), and the sayings the house has heard in both.
  const songs = v.songs ?? [], crossed = v.crossed ?? [], living = pets.filter((p) => p.stage !== "dead");
  const crossings: Crossing[] = which !== now ? [] : songs.flatMap((s) => {
    const from = songs.find((x) => x.id === s.parent);
    const byEar = from?.family && s.family && from.family !== s.family ? [{ from: from.by, to: s.by, what: `“${s.name}”, picked up by ear` }] : [];
    const sung = living.filter((p) => s.family && (p.family ?? 1) !== s.family && p.id !== s.by && s.known_by.includes(p.label) && living.filter((q) => q.label === p.label).length === 1);
    return [...byEar, ...sung.map((p) => ({ from: s.by, to: p.id, what: `“${s.name}”, sung by ${p.label}` }))];
  });
  const families = new Set(pets.map((p) => p.family ?? 1)).size, keepers = living.filter((p) => p.animals?.length);
  return [
    el("p", "hint", `${plural(pets.length, "life", "lives")} over ${plural(new Set(pets.map((p) => p.gen)).size, "generation")}${families > 1 ? `, in ${families} families` : ""}. The living are outlined. Click anyone for their life.`),
    lines.length > 1 ? pick : null,
    tree(c, pets, crossings, crossed.length, redraw),
    who ? el("section", "life", el("div", "who", face(who, 96), el("div", "", el("h2", "", who.label),
        el("p", "hint", who.stage === "dead" ? `generation ${who.gen}` : `${stageWord(who)} · generation ${who.gen} · alive`),
        who.stage !== "dead" ? link("See its mind", () => c.show("mind", who.id)) : null)),
      rec ? null : radial(who.temper, 130),
      ...(rec ? record(c, rec) : [])) : null,
    families > 1 && which === now ? el("section", "", el("h3", "", "Between the families"),
      crossings.length || crossed.length ? el("ul", "plain", ...crossings.map((x) => el("li", "", icon("music"), ` ${name(x.from)} → ${name(x.to)}: ${x.what}`)),
        ...crossed.map((x) => el("li", "", icon("crossed"), ` “${x.text}” `, el("span", "hint", "said in both families"))))
        : el("p", "empty", "Nothing has passed from one family to the other yet: no song, no saying.")) : null,
    which === now ? el("section", "", el("h3", "", "Animals"),
      keepers.length ? el("ul", "plain", ...keepers.map((p) => el("li", `owner ${fam(p.family)}`, el("b", "", p.label), ": ",
        p.animals!.map((a) => `${a.name ? `${a.name} the ${a.kind}` : `a ${a.kind}`} (${c.snap.rooms.find((r) => r.id === a.room)?.name ?? "somewhere"})`).join(", "))))
        : el("p", "empty", c.snap.arrived?.taming == null ? "The creatures of the house are nobody's yet." : "No creature has taken to anyone yet.")) : null,
    el("h3", "", "Family sayings"),
    sayings.length ? el("p", "hint", "What one generation told the next. After each: ", el("span", "correct", "✓ true of this house"), ", ", el("span", "wrong", "✗ not so"),
      ", or nothing the house can check. That is the engine's own test of the saying against how the house really works; the hobs are never told.") : null,
    sayings.length ? el("ul", "sayings", ...sayings.map((s) => el("li", "", el("blockquote", "", s.text),
      el("p", "hint", `${plural(s.gens.length, "generation")}: ${s.pets.map((p) => p.name).join(" → ")} `, mark(s.truth)),
      s.forms.length ? fold(`forms-${s.text}`, `Said differently ${plural(s.forms.length, "time")}`, ...s.forms.map(([id, t]) => el("p", "", `${name(id)}: “${t}”`))) : null)))
      : el("p", "empty", "Nothing has been handed down a second time yet."),
    el("h3", "", "Heirlooms"),
    heir.length ? el("ul", "shelf", ...heir.map((h) => el("li", "thing", thingSprite(h.recipe, 3), el("div", "what", el("b", "", aThing(h.recipe)), ` “${h.name}” `, el("span", "badge gold", "heirloom")),
      el("div", "hint", `in ${h.room}`), el("div", "truth", `${h.line.join(" → ")} → ${h.to.join(", ") || "nobody living"}`))))
      : el("p", "empty", "Nothing has been left to anyone yet."),
    ...(which === now ? [...songbook(c, songs), ...walls(c, v.walls ?? [])] : []),
  ];
}
