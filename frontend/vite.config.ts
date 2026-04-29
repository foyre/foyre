import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev server is intentionally reachable from other machines (see
    // `make front` which binds to 0.0.0.0). Accept any Host header so
    // requests via hostnames like "ledger" aren't rejected.
    allowedHosts: true,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
