import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '192.168.88.115', // ← Bind to your real LAN IP
    port: 5175,              // ← Optional: set a port
    allowedHosts: [ '192.168.88.115', 'yeet.trazen.org', 'localhost' ]
  },
})