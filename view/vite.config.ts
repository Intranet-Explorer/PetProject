import { defineConfig } from "vite";

// `npm run dev` serves the view on :5173 and forwards the websocket to the engine.
export default defineConfig({
  server: { proxy: { "/ws": { target: "ws://127.0.0.1:8000", ws: true } } },
});
