import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const backendUrl = process.env.VITE_BACKEND_URL || "http://localhost:8000";
const backendWsUrl = process.env.VITE_BACKEND_WS_URL || "ws://localhost:8000";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'notification.mp3'],
      manifest: {
        name: 'Tavern Ordering System',
        short_name: 'Tavern',
        description: 'Complete tavern ordering and management system',
        theme_color: '#667eea',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ],
        categories: ['business', 'food'],
        screenshots: []
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2,mp3}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365 // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            urlPattern: /\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 5 // 5 minutes
              },
              networkTimeoutSeconds: 10
            }
          }
        ]
      },
      devOptions: {
        enabled: true,
        type: 'module'
      }
    })
  ],
  server: {
    host: true,
    port: 5177,
    proxy: {
      '/order': {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      '/config': {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      '/orders': {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      '/table_meta': {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      '/item': {
        target: backendUrl,
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: backendWsUrl,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})

