import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 8085,
    strictPort: true, // fail if the port is already in use
    proxy: {
      "/health": {
        target: "http://fastapi:8000",
        changeOrigin: true,
      },
      "/score": {
        target: "http://fastapi:8000",
        changeOrigin: true,
      },
      "/classify": {
        target: "http://fastapi:8000",
        changeOrigin: true,
      },
      "/metrics": {
        target: "http://fastapi:8000",
        changeOrigin: true,
      },
      "/api": {
        target: "http://fastapi:8000",
        changeOrigin: true,
      },
    },
  },
});
