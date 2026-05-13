import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 15173,
    proxy: {
      "/papers": "http://localhost:18000",
      "/illustrations": "http://localhost:18000",
      "/chat": "http://localhost:18000",
      "/literature": "http://localhost:18000",
      "/health": "http://localhost:18000",
    },
  },
});
