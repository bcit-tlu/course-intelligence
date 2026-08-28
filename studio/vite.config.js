import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        proxy: {
            // Proxy API calls to the FastAPI backend in dev (avoids CORS).
            // The /api prefix is stripped so /api/jobs -> http://localhost:8000/jobs
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
                rewrite: function (p) { return p.replace(/^\/api/, ""); },
            },
            // Proxy OTel trace exports to the local collector in dev.
            // The /otel prefix is stripped so /otel/v1/traces -> http://localhost:4318/v1/traces
            "/otel": {
                target: "http://localhost:4318",
                changeOrigin: true,
                rewrite: function (p) { return p.replace(/^\/otel/, ""); },
            },
        },
    },
});
