import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // three is by far the largest dependency and changes rarely, so give
        // it its own chunk: app edits then never invalidate it in the cache.
        manualChunks: {
          three: ['three', '@react-three/fiber'],
        },
      },
    },
  },
  server: {
    port: 5173,
    // Same-origin in dev so the session cookie is sent without CORS.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
  },
})
