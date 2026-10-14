// Small pictures drawn in code (§9.1, §10.1): one for each kind of moment, the weather, and each room on the map.
// Each is a few strokes in a 16 by 16 box, in the colour of the text around it.
const NS = "http://www.w3.org/2000/svg";

export function svg<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, ...kids: (SVGElement | string)[]) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  e.append(...kids);
  return e;
}

export const PATHS: Record<string, string> = {
  egg: "M8 2C5 2 3.5 6.5 3.5 9.5a4.5 4.5 0 0 0 9 0C12.5 6.5 11 2 8 2Z",
  hatch: "M3.5 9.5a4.5 4.5 0 0 0 9 0l-2-2-1.5 2-1.5-2-1.5 2ZM6 5l1-2M8 4.5V2M10 5l1-2",
  heart: "M8 13.5C3 10 2 7.5 2 5.8A3 3 0 0 1 8 4.5 3 3 0 0 1 14 5.8C14 7.5 13 10 8 13.5Z",
  stone: "M4 14V7a4 4 0 0 1 8 0v7ZM2.5 14h11M6.5 8h3M6.5 10.5h3",
  door: "M4 14V2.5h8V14M2.5 14h11M9.8 8.5v.1",
  bolt: "M9 1.5 3.5 9H8l-1 5.5L12.5 7H8Z",
  drop: "M8 2c2.5 3.5 4 5.5 4 7.5a4 4 0 0 1-8 0C4 7.5 5.5 5.5 8 2Z",
  wind: "M2 6h7.5a2 2 0 1 0-2-2M2 9h10.5a2 2 0 1 1-2 2M2 12h5",
  crate: "M2.5 4.5h11v9h-11ZM2.5 4.5l11 9M13.5 4.5l-11 9",
  speech: "M2.5 3.5h11v7H8l-3 3v-3H2.5Z",
  star: "M8 2l1.8 3.8 4.2.5-3.1 2.9.8 4.1L8 11.3l-3.7 2 .8-4.1L2 6.3l4.2-.5Z",
  bowl: "M2 7.5h12a6 6 0 0 1-12 0ZM5 5c0-1 1-1 1-2M8 5c0-1 1-1 1-2M11 5c0-1 1-1 1-2",
  brush: "M10 2l4 4-6 6-4-4ZM4 8l-2 6 6-2",
  mouse: "M2 10c0-3 3-5 6-5s5 2 5 4-1.5 3-4 3H3.5ZM11 5.5a1.8 1.8 0 1 1 2 2M13 11c1.5 0 1.5 2.5 0 2.5H9",
  hammer: "M3 3.5h7l2 2H3ZM6.5 5.5V14",
  leaf: "M3 13C3 6 7 3 13 3c0 6-3 10-10 10ZM3 13l6-6",
  sun: "M8 5a3 3 0 1 0 0 6 3 3 0 0 0 0-6ZM8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.5 1.5M11.5 11.5 13 13M3 13l1.5-1.5M11.5 4.5 13 3",
  cloud: "M4.5 12.5a3 3 0 0 1 .3-6 4 4 0 0 1 7.6 1 2.5 2.5 0 0 1-.4 5Z",
  rain: "M4.5 9.5a3 3 0 0 1 .3-6 4 4 0 0 1 7.6 1 2.5 2.5 0 0 1-.4 5ZM5.5 11.5l-1 2.5M8.5 11.5l-1 2.5M11.5 11.5l-1 2.5",
  storm: "M4.5 9a3 3 0 0 1 .3-6 4 4 0 0 1 7.6 1 2.5 2.5 0 0 1-.4 5ZM8.5 9.5l-2 3h2.5l-1.5 3",
  snow: "M8 2v12M3 5l10 6M13 5 3 11M6.5 2.5 8 4l1.5-1.5M6.5 13.5 8 12l1.5 1.5",
  heat: "M8 6a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5ZM8 2v1.5M3.5 8.5H2M14 8.5h-1.5M4.5 5l-1-1M11.5 5l1-1M3 13.5c1.5-1 2.5 1 4 0s2.5 1 4 0 2 .5 2.5 0",
  moon: "M12.5 10.5A5.5 5.5 0 0 1 6 3a5.5 5.5 0 1 0 6.5 7.5Z",
  // SPEC-v3.1: the six discoveries and what the family does with them
  chalk: "M10.5 2.5l3 3-6.5 6.5-3-3ZM2.5 12.5c1 1.5 2.5 1.5 4 1.5",
  scrub: "M2.5 6c2-2 3.5 2 5.5 0s3.5-1 5.5 0M2.5 10c2-2 3.5 2 5.5 0M3.5 13.5 12.5 2.5",
  radio: "M2.5 6.5h11v7h-11ZM5 6.5 11 2M5.8 11.3a1.3 1.3 0 1 0 0-2.6 1.3 1.3 0 0 0 0 2.6ZM9.5 9h2.5M9.5 11.5h2.5",
  book: "M8 4.5C6.5 3.5 4.5 3.2 2.5 3.5v9c2-.3 4 0 5.5 1 1.5-1 3.5-1.3 5.5-1v-9c-2-.3-4 0-5.5 1ZM8 4.5v9",
  paw: "M8 8.5c-2 0-3.5 1.8-3.5 3.3 0 1.2 1.2 1.5 3.5 1.5s3.5-.3 3.5-1.5C11.5 10.3 10 8.5 8 8.5ZM3.6 7.4a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8ZM6.4 4.9a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8ZM9.6 4.9a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8ZM12.4 7.4a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8Z",
  stranger: "M5.5 4C3.8 4 2.5 6.8 2.5 9a3 3 0 0 0 6 0C8.5 6.8 7.2 4 5.5 4ZM11.2 6.2c-1.2 0-2.2 1.9-2.2 3.6a2.2 2.2 0 0 0 4.4 0c0-1.7-1-3.6-2.2-3.6Z",
  crossed: "M2.5 5.5h10l-2.5-2.5M13.5 10.5h-10l2.5 2.5",
  // rooms
  nursery: "M2 12.5V5M2 9.5h12v3M14 9.5V8a2 2 0 0 0-2-2H7v3.5M4.5 8a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4Z",
  garden: "M8 14V7M8 9C5 9 3.5 7.5 3.5 5 6 5 8 6.5 8 9ZM8 7c0-2.5 1.5-4.5 4.5-4.5C12.5 5 11 7 8 7Z",
  cellar: "M2.5 14V8a5.5 5.5 0 0 1 11 0v6M2.5 14h11M6 14v-4h4v4",
  attic: "M1.5 12 8 3l6.5 9ZM5 12V9.5h6V12",
  pond: "M2 6c2-1.5 4 1.5 6 0s4 1.5 6 0M2 9.5c2-1.5 4 1.5 6 0s4 1.5 6 0M2 13c2-1.5 4 1.5 6 0s4 1.5 6 0",
  workshop: "M3 3.5h7l2 2H3ZM6.5 5.5V14M10.5 9.5l3 3M13.5 9.5l-3 3",
  music: "M6 12.5V3.5l7-1.5v9M6 12.5a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM13 11a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z",
  greenhouse: "M2.5 14V6.5L8 2l5.5 4.5V14ZM2.5 6.5h11M8 2v12M2.5 10.5h11",
  storeroom: "M2.5 5.5h11v8h-11ZM2.5 9.5h11M6.5 7.5h3M6.5 11.5h3M4 5.5v-3h8v3",
  hub: "M2.5 5.5h11v8h-11ZM5 5.5V3h6v2.5M4.5 8h1M7.5 8h1M10.5 8h1M6 11h4",   // SPEC-v3.5.1: the machine room
};

const KIND: Record<string, string> = {
  egg: "egg", hatched: "hatch", stage: "star", death: "stone", ended: "stone", weak: "stone",
  nuzzle: "heart", gift: "heart", befriended: "heart", heirloom: "star", project: "star", made: "hammer", unmade: "hammer", taught: "star",
  room: "door", entered: "door", power: "bolt", "power back": "bolt", storm: "storm", leak: "drop", floated: "drop", draught: "wind", drift: "wind", season: "leaf",
  delivery: "crate", kept: "crate", lost: "crate", took: "crate", told: "speech", message: "speech", named: "speech", saying: "speech", discarded: "speech",
  ate: "bowl", painted: "brush", mouse: "mouse", words: "speech", mark: "star",
  "arrival writing": "chalk", "arrival songs": "music", "arrival taming": "paw", "arrival radio": "radio", "arrival book": "book", "arrival strangers": "stranger",
  wrote: "chalk", scrubbed: "scrub", song: "music", tamed: "paw", untamed: "paw", young: "mouse", "creature died": "stone", read: "book",
  moth: "mouse", beetle: "mouse", bird: "mouse",
  // SPEC-v3.4: a want met, a thing found out, the first tool, growing food, a recipe nobody knows any more, the book carried
  want: "star", discovery: "star", tool: "hammer", harvest: "leaf", planted: "leaf", forgotten: "stone", moved: "crate",
  first: "star", best: "star", ambition: "star", works: "crate", star: "star", noticed: "eye",   // SPEC-v3.5.4: what the house is proud of
  built: "hammer", mended: "hammer", worn: "hammer", held: "drop",   // SPEC-v3.5 §4: a thing built, mended, worn; a leak or a draught kept out
  machine: "crate", fed: "crate", stocked: "crate",   // SPEC-v3.5 §4.3: the vending machine gave, was fed, was stocked
  clear: "sun", cloudy: "cloud", "power cut": "bolt", "lost thing": "crate", "rule drift": "wind", surprise: "crate",
};

/** The picture for a moment kind, a weather, an event or a room type. */
export function icon(name: string, size = 16) {
  const d = PATHS[name] ?? PATHS[KIND[name] ?? ""] ?? "M8 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z";
  return svg("svg", { viewBox: "0 0 16 16", width: size, height: size, class: "icon", "aria-hidden": "true" },
    svg("path", { d, fill: "none", stroke: "currentColor", "stroke-width": 1.4, "stroke-linecap": "round", "stroke-linejoin": "round" }));
}
