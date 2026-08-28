import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.BACKEND_URL || "http://localhost:8000";

  return {
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
      // The /api prefix is stripped so /api/jobs -> <BACKEND_URL>/jobs
      // BACKEND_URL defaults to localhost:8000 for standalone dev; the Docker
      // override sets it to http://api:8000 (the Docker service name).
      "/api": {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
      // OTel proxy disabled in local dev — no collector runs in the dev stack.
      // Re-enable if you run a local OTel collector on port 4318:
      // "/otel": {
      //   target: "http://localhost:4318",
      //   changeOrigin: true,
      //   rewrite: (p) => p.replace(/^\/otel/, ""),
      // },
    },
  },
  };
});
