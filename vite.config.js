import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(), 
    tailwindcss()
  ],
  server: {
    // These settings are for when you run `npm run dev`
    host: '0.0.0.0', // Listen on all interfaces for k8s
    port: 5175,
    allowedHosts: ['192.168.88.115', 'yeet.trazen.org', 'localhost'],
    proxy: {
      '/api': {
        target: 'https://yeet.trazen.org',
        changeOrigin: true,
        secure: true,
        headers: {
          'Origin': 'https://yeet.trazen.org'
        }
      }
      // Removed socket.io proxy - not needed for polling approach
    }
  },
})