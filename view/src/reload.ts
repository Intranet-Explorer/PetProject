// v3.5.10: a page left open across a deploy loads the new one by itself. The build names its script by a hash of what
// is in it (index-<hash>.js); every half minute, and when the window comes back into view, the page asks for its own
// front page again, and if that names another script, a new view has been deployed: it reloads.
export function watchVersion() {
  const mine = [...document.scripts].map((s) => s.src).find((s) => /\/assets\/index-[^/]+\.js$/.test(s));
  if (!mine) return;   // (the dev server: no hashed build to compare)
  const check = async () => {
    try {
      const html = await (await fetch("/", { cache: "no-store" })).text();
      const now = html.match(/\/assets\/index-[^"']+\.js/)?.[0];
      if (now && !mine.endsWith(now)) location.reload();
    } catch { /* the server is restarting: ask again next time */ }
  };
  setInterval(check, 30000);
  addEventListener("visibilitychange", () => { if (!document.hidden) check(); });
}
