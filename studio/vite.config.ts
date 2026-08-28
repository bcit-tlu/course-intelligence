import path from "node:path";
import fs from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Inside Docker the backend is at http://api:8000 (Docker service name).
// Outside Docker (standalone dev) it's at http://localhost:8000.
const isDocker = fs.existsSync("/.dockerenv");
const backendUrl = isDocker ? "http://api:8000" : "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    host: true,
    hmr: {
      clientPort: 5173,
    },
    proxy: {
      // Proxy API calls to the FastAPI backend in dev (avoids CORS).
      // The /api prefix is stripped so /api/jobs -> <backendUrl>/jobs
      "/api": {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
