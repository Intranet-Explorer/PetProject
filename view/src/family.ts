// The Family tab (SPEC-v3 §10.4): the tree, a life record for whoever is clicked, the family's sayings and heirlooms.
import { el, face, fold, link, plural, radial } from "./dom";
import type { Ctx, Kid } from "./dom";
import { svg } from "./icons";
import type { Genome } from "./pet";
import { thingPicture } from "./things";
import type { Part, Recipe } from "./things";
import type { PetV } from "./types";

const kept = (() => { try { return JSON.parse(localStorage.getItem("family") ?? "{}"); } catch { return {}; } })();
const keep = () => { try { localStorage.setItem("family", JSON.stringify({ chosen, lineage })); } catch { /* not remembered */ } };
let chosen: string | null = kept.chosen ?? null;    // whose life is open under the tree
let lineage: number | null = kept.lineage ?? null;   // which family's tree is shown: the present one unless another was picked
export function showRecord(id: string | null) {
  chosen = id;
  lineage = null;
  keep();
}

const TRUTH: Record<string, [string, string]> = { true: ["✓ true of this house", "correct"], false: ["✗ not so", "wrong"] };
const [CW, CH] = [96, 148];

function tree(c: Ctx, pets: PetV[], redraw: () => void) {
  const kids = (id: string) => pets.filter((p) => p.parent === id).sort((a, b) => a.laid - b.laid);
  const roots = pets.filter((p) => !pets.some((q) => q.id === p.parent)).sort((a, b) => a.laid - b.laid);
  const X = new Map<string, number>();
  let next = 0;
  const place = (p: PetV) => {   // leaves side by side, each parent over the middle of its children
    const ch = kids(p.id);
    ch.forEach(place);
    X.set(p.id, ch.length ? (X.get(ch[0].id)! + X.get(ch.at(-1)!.id)!) / 2 : next++);
  };
  roots.forEach(place);
  const gens = [...new Set(pets.map((p) => p.gen))].sort((a, b) => a - b);
  const at = (p: PetV) => [X.get(p.id)! * CW, gens.indexOf(p.gen) * CH];
  const lines = svg("svg", { class: "lines", width: next * CW, height: gens.length * CH });
  const box = el("div", "tree", lines);
  box.style.width = `${next * CW}px`;
  box.style.height = `${gens.length * CH}px`;
  for (const p of pets) {
    const [x, y] = at(p), parent = pets.find((q) => q.id === p.parent);
    if (parent) {
      const [px, py] = at(parent), mid = y - 8;
      lines.append(svg("path", { d: `M${px + CW / 2} ${py + CH - 22}V${mid}H${x + CW / 2}V${y + 2}` }));
    }
    const dead = p.stage === "dead", egg = p.stage === "egg";
    const life = dead ? `lived ${plural(Math.round(p.days ?? 0), "day")}` : egg ? "not hatched" : `${p.stage}, day ${Math.floor(p.days ?? 0) + 1}`;
    const node = el("button", `node ${dead ? "dead" : "alive"}${chosen === p.id ? " chosen" : ""}`, face(c, p),
      el("b", "", egg ? p.name ?? "an egg" : p.label), el("span", "", life), p.eggs ? el("span", "", plural(p.eggs, "egg")) : null) as HTMLButtonElement;
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;
    node.title = `${p.label}, generation ${p.gen}`;
    node.onclick = () => { chosen = chosen === p.id ? null : p.id; keep(); redraw(); };
    box.append(node);
  }
  return el("div", "treebox", box);
}

const bodyOf = (c: Ctx, g: Genome, stage: string, caption: string) => {
  const img = el("img", "face") as HTMLImageElement;
  img.src = c.picture(g, stage, { grey: stage === "elder" ? 0.55 : 0 });
  img.alt = "";
  return el("figure", "", img, el("figcaption", "hint", caption));
};

/** A whole life (§9.3), as the engine put it together when the pet died. */
export function record(c: Ctx, r: Record<string, any>): Kid[] {
  const name = (id: string) => c.snap.pets.find((p) => p.id === id)?.label ?? "someone gone";
  const stages = Object.entries((r.stages ?? {}) as Record<string, number | null>).filter(([, d]) => d != null);
  const things = (r.things ?? []) as { name: string; recipe: Recipe; uses: number; gone: string | null }[];
  const text = (title: string, items: { text: string }[] | undefined) => (items?.length ? el("section", "", el("h3", "", title), ...items.map((m) => el("blockquote", "", m.text))) : null);
  return [
    el("section", "", el("h3", "", "My life"), el("blockquote", "thought", r.my_life),
      r.my_life_by === "the engine" ? el("p", "hint", "It died before it wrote its own; this is the engine's plain account.") : null),
    el("p", "", `${r.name} lived ${r.days} of a possible ${r.span} days, as far as ${r.reached}, and died of ${r.cause}. ` +
      `It made ${plural(r.made, "thing")}, ${r.useful} of them useful, and laid ${plural(r.eggs, "egg")}.`),
    el("p", "hint", [r.parent ? `Child of ${name(r.parent)}.` : "The first of its family.", r.children?.length ? `Parent of ${r.children.map(name).join(", ")}.` : "",
      `Wellbeing over its life ${r.wellbeing} of 100.`, r.meter_talk != null ? `Talked like a meter in ${r.meter_talk}% of its thoughts.` : ""].join(" ")),
    el("div", "row", ...Object.entries((r.bodies ?? {}) as Record<string, Genome>).map(([s, g]) =>
      bodyOf(c, g, s, `${s}${stages.find(([k]) => k === s) ? `, day ${stages.find(([k]) => k === s)![1]}` : ""}`))),
    radial(r.temper ?? {}, 130),
    r.portraits?.length ? el("section", "", el("h3", "", "How it drew itself"),
      el("div", "row", ...(r.portraits as { day: number; parts: Part[] }[]).map((p) => el("figure", "", thingPicture(p), el("figcaption", "hint", `day ${p.day}`))))) : null,
    text(`What its ${r.told?.[0]?.who ?? "parent"} told it`, r.told),
    text("Its message to its children, as it changed", r.messages),
    r.last_words ? el("section", "", el("h3", "", "Last words"), el("blockquote", "", r.last_words)) : null,
    things.length ? el("section", "", el("h3", "", "What it used most"), el("div", "row", ...things.map((t) =>
      el("figure", t.gone ? "gone" : "", thingPicture(t.recipe), el("figcaption", "hint", `${t.name} · ${t.uses}`))))) : null,
    el("p", "hint", [r.heirlooms_given?.length ? `Left behind: ${r.heirlooms_given.join(", ")}.` : "", r.heirlooms_received?.length ? `Was left: ${r.heirlooms_received.join(", ")}.` : "",
      r.rooms?.length ? `Knew ${r.rooms.join(", ")}.` : "", Object.keys(r.creatures ?? {}).length ? `Met ${Object.entries(r.creatures).map(([k, n]) => `the ${k} (${n})`).join(", ")}.` : ""].join(" ")),
    r.projects?.length ? el("section", "", el("h3", "", "Projects"), ...(r.projects as { text: string; how: string }[]).map((p) => el("p", "", `“${p.text}” `, el("span", "hint", p.how)))) : null,
    r.beliefs?.length ? fold(`beliefs-${r.id}`, `What it believed at the end (${r.beliefs.length})`,
      el("ul", "beliefs", ...(r.beliefs as { statement: string; source: string }[]).map((b) => el("li", "", el("div", "", b.statement), el("span", "tag", b.source))))) : null,
    r.diary?.length ? fold(`dreams-${r.id}`, `Its dreams (${r.diary.length})`, ...(r.diary as string[]).map((d) => el("p", "night", d))) : null,
  ];
}

export function family(c: Ctx): Kid[] {
  const d = c.api.family;
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
  return [
    el("p", "hint", `${plural(pets.length, "life", "lives")} over ${plural(new Set(pets.map((p) => p.gen)).size, "generation")}. The living are outlined. Click anyone for their life.`),
    lines.length > 1 ? pick : null,
    tree(c, pets, redraw),
    who ? el("section", "life", el("div", "who", face(c, who), el("div", "", el("h2", "", who.label),
        el("p", "hint", who.stage === "dead" ? `generation ${who.gen}` : `${who.stage} · generation ${who.gen} · alive`),
        who.stage !== "dead" ? link("See its mind", () => c.show("mind", who.id)) : null)),
      rec ? null : radial(who.temper, 130),
      ...(rec ? record(c, rec) : [])) : null,
    el("h3", "", "Family sayings"),
    sayings.length ? el("ul", "sayings", ...sayings.map((s) => el("li", "", el("blockquote", "", s.text),
      el("p", "hint", `${plural(s.gens.length, "generation")}: ${s.pets.map((p) => p.name).join(" → ")} `, el("span", TRUTH[s.truth ?? ""]?.[1] ?? "", TRUTH[s.truth ?? ""]?.[0] ?? "nothing the house can check")),
      s.forms.length ? fold(`forms-${s.text}`, `Said differently ${plural(s.forms.length, "time")}`, ...s.forms.map(([id, t]) => el("p", "", `${name(id)}: “${t}”`))) : null)))
      : el("p", "empty", "Nothing has been handed down a second time yet."),
    el("h3", "", "Heirlooms"),
    heir.length ? el("ul", "shelf", ...heir.map((h) => el("li", "thing", thingPicture(h.recipe), el("div", "", el("b", "", h.name), el("span", "badge gold", "heirloom")),
      el("div", "hint", `in ${h.room}`), el("div", "truth", `${h.line.join(" → ")} → ${h.to.join(", ") || "nobody living"}`))))
      : el("p", "empty", "Nothing has been left to anyone yet."),
  ];
}
