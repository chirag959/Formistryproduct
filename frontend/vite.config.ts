import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// VITE_API_BASE points the frontend at the FastAPI backend. In dev we proxy
// /api to localhost:8000 so there are no CORS surprises.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
