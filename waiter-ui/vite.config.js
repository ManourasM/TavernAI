// vite.config.js (waiter)
import { defineConfig } from "vite";

// Use environment variable for backend URL, default to localhost
const backendUrl = process.env.VITE_BACKEND_URL || "http://localhost:8000";
const backendWsUrl = process.env.VITE_BACKEND_WS_URL || "ws://localhost:8000";

export default defineConfig({
  server: {
    host: true,        // bind to 0.0.0.0 so other devices (phone) can reach it
    port: 5173,
    hmr: {
      // helpful when loading from other device; replace with laptop IP if HMR client fails
      host: undefined, // leave undefined -> Vite will try to infer; set to "192.168.x.y" if needed
    },
    proxy: {
      // proxy REST API calls to backend
      "/order": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      "/config": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      "/orders": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      "/table_meta": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      "/item": {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      // proxy websocket endpoint(s)
      "/ws": {
        target: backendWsUrl,
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
