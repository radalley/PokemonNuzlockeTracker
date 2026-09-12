import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        // Override when the backend is not on its default port.
        target: process.env.API_PROXY_TARGET || 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
