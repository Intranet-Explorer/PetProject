import { defineConfig } from "vite";

// `npm run dev` serves the view on :5173 and forwards the websocket and the pages of JSON to the engine (on PET_PORT, else
// 8000). The fakes and the check pages (main.ts) are in dev only (SPEC-v4.0.5 §7.6).
// Beside the house itself, two pages of pictures only (SPEC-v3.5 §1, §7): /parts.html and /sheet.html.
export default defineConfig({
  server: { proxy: { "/ws": { target: `ws://127.0.0.1:${process.env.PET_PORT ?? 8000}`, ws: true }, "^/(api|portrait|art)/": `http://127.0.0.1:${process.env.PET_PORT ?? 8000}` } },
  build: { rollupOptions: { input: ["index.html", "parts.html", "sheet.html"] } },
});
