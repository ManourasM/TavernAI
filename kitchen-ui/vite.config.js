// vite.config.js (kitchen)
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,   // bind to LAN
    port: 5175,
    hmr: {
      // if HMR fails from phone, replace undefined with your laptop IP string
      host: undefined,
    },
    proxy: {
      // If kitchen UI calls backend endpoints directly (e.g. getOrders, markDone)
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
      // allow forwarding of websocket connections from the browser to uvicorn ws endpoints
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
