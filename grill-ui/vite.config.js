// vite.config.js (grill)
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,   // bind to LAN
    port: 5174,
    hmr: {
      // set your laptop IP here only if HMR client cannot connect automatically
      host: undefined,
    },
    proxy: {
      "/orders": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/config": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/order": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/item": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
