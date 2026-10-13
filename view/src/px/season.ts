// The seasons' pictures (SPEC-v3.5 §5). view/assets/seasons.json says which picture stands in for which, by season and
// by room type ("*": every room): snow on the garden's grass, blossom on its hedge, what is seen through a window. The
// room asks here for every tile, piece of scenery and fixture it draws; nothing about any season is named in code.
// A stand-in may be a list: one of them is taken by where the tile is, so a floor of one tile is not one picture repeated.
type Swaps = Record<string, Record<string, Record<string, string | string[] | null>>>;
let swaps: Swaps = {};

export async function loadSeasons(from = "/art") {
  try {
    const r = await fetch(`${from}/seasons.json`);
    if (r.ok) swaps = (await r.json()) as Swaps;
  } catch { /* no such file: the art as it stands, all year */ }
}

/** The name to draw for `name` in this season and kind of room: its stand-in, null if it is not there in that season, or itself. */
export function seasonal<T extends string | null | undefined>(name: T, season: string, room: string | null, x = 0, y = 0): T | string | null {
  const s = swaps[season];
  if (!name || !s) return name;
  const to = [s[room ?? ""], s["*"]].find((m) => m && name in m)?.[name];
  return to === undefined ? name : Array.isArray(to) ? to[(((x * 73856093) ^ (y * 19349663)) >>> 0) % to.length] : to;
}
