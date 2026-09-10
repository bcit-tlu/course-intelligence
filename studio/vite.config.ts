import path from "node:path";
import fs from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Inside Docker the backend is at http://api:8000 (Docker service name).
// Outside Docker (standalone dev) it's at http://localhost:8000.
const isDocker = fs.existsSync("/.dockerenv");
const backendUrl = isDocker ? "http://api:8000" : "http://localhost:8000";

export default defineConfig({
  plugins: [
    react(),
    // Serve /runtime-config.js in dev so the browser gets
    // window.__OTEL_ENDPOINT__ and window.__TENANT_ID__ without nginx.
    {
      name: "runtime-config",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === "/runtime-config.js") {
            const otel = process.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT || "";
            const tenant = process.env.VITE_TENANT_ID || "";
            res.setHeader("Content-Type", "application/javascript");
            res.setHeader("Cache-Control", "no-cache");
            res.end(
              `window.__OTEL_ENDPOINT__=${otel ? `"${otel}"` : '""'};` +
              `window.__TENANT_ID__="${tenant}";`,
            );
            return;
          }
          next();
        });
      },
    },
  ],
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
      // Proxy OTel trace exports to the collector in dev.
      // OTEL_ENDPOINT is the collector address (same var nginx uses in prod).
      "/otel": {
        target: process.env.OTEL_ENDPOINT || "http://localhost:4318",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/otel/, ""),
      },
    },
  },
});
