import { defineConfig } from "vite";

// `npm run dev` serves the view on :5173 and forwards the websocket to the engine.
// Beside the house itself, two pages of pictures only (SPEC-v3.5 §1, §7): /parts.html and /sheet.html.
export default defineConfig({
  server: { proxy: { "/ws": { target: "ws://127.0.0.1:8000", ws: true } } },
  build: { rollupOptions: { input: ["index.html", "parts.html", "sheet.html"] } },
});
