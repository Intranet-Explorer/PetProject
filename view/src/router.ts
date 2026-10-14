// The page's addresses (SPEC-v3.5.3 §1): #/house, #/house/<pet> (watching it), #/family, #/pet/<id>, #/story,
// #/things, #/thing/<id>, #/lab. Each tab and page has its own, so the back button works and a page can be kept.
export type Route = { page: string; id: string | null };

export const PAGES = ["house", "family", "pet", "story", "things", "thing", "lab"];

export function route(hash = location.hash): Route {
  const [page, ...rest] = hash.replace(/^#\/?/, "").split("/");
  return PAGES.includes(page) ? { page, id: rest.length ? decodeURIComponent(rest.join("/")) : null } : { page: "house", id: null };
}

export const href = (page: string, id?: string | null) => `#/${page}${id ? `/${encodeURIComponent(id)}` : ""}`;
export const go = (page: string, id?: string | null) => { location.hash = href(page, id); };

/** Call `fn` now and on every change of address. */
export function onRoute(fn: (r: Route) => void) {
  addEventListener("hashchange", () => fn(route()));
  fn(route());
}
