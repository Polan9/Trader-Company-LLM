import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// W trybie deweloperskim (npm run dev) zapytania /api idą do serwera FastAPI (python -m api).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
