// vite.config.js (waiter)
import { defineConfig } from "vite";

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
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/config": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/orders": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/table_meta": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/item": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      // proxy websocket endpoint(s)
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
